"""Writes questions.json. The expected answers are computed by OUR OWN SQL
here (never by the agent), straight from data/shop.db."""
import json
import os
import sqlite3
import sys

import build_db

HERE = os.path.dirname(os.path.abspath(__file__))
REV = "oi.quantity * oi.unit_price"


def build_questions(db_path):
    con = sqlite3.connect(db_path)
    one = lambda sql: con.execute(sql).fetchone()[0]
    r2 = lambda x: round(x, 2)

    order_values = "SELECT SUM(quantity*unit_price) v FROM order_items GROUP BY order_id"
    avg_ov = one(f"SELECT AVG(v) FROM ({order_values})")
    min_ov = one(f"SELECT MIN(v) FROM ({order_values})")
    total_rev = one(f"SELECT SUM({REV}) FROM order_items oi")
    elec_rev = one(f"SELECT SUM({REV}) FROM order_items oi JOIN products p ON p.id=oi.product_id "
                   "WHERE p.category='Electronics'")
    rev_y = lambda y: one(f"SELECT SUM({REV}) FROM order_items oi JOIN orders o ON o.id=oi.order_id "
                          f"WHERE substr(o.order_date,1,4)='{y}'")
    top_cat = con.execute(f"SELECT p.category, SUM({REV}) s FROM order_items oi JOIN products p "
                          "ON p.id=oi.product_id GROUP BY p.category ORDER BY s DESC LIMIT 2").fetchall()
    top_city = con.execute("SELECT city, COUNT(*) n FROM customers GROUP BY city ORDER BY n DESC LIMIT 2").fetchall()
    top_prod = con.execute("SELECT name, price FROM products ORDER BY price DESC LIMIT 2").fetchall()
    assert top_cat[0][1] != top_cat[1][1] and top_city[0][1] != top_city[1][1] and top_prod[0][1] != top_prod[1][1]
    prices = one("SELECT MAX(price) - MIN(price) FROM products")

    Q = []
    def add(qid, text, kind, expected, cat, multi=False):
        Q.append({"id": qid, "question": text, "type": kind, "expected": expected,
                  "category": cat, "needs_multiple_tool_calls": multi})

    add("q01", "How many customers are there?", "answer", [one("SELECT COUNT(*) FROM customers")], "simple")
    add("q02", "How many products are in the Books category?", "answer",
        [one("SELECT COUNT(*) FROM products WHERE category='Books'")], "simple")
    add("q03", "What is the average product price?", "answer", [r2(one("SELECT AVG(price) FROM products"))], "simple")
    add("q04", "How many orders have the status 'cancelled'?", "answer",
        [one("SELECT COUNT(*) FROM orders WHERE status='cancelled'")], "simple")
    add("q05", "What is the total revenue for customer 12?", "answer",
        [r2(one(f"SELECT SUM({REV}) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.customer_id=12"))], "join")
    add("q06", "How many orders did customer 7 place?", "answer",
        [one("SELECT COUNT(*) FROM orders WHERE customer_id=7")], "join")
    add("q07", "How many units (total quantity) of products in the Toys category were sold?", "answer",
        [one("SELECT SUM(oi.quantity) FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE p.category='Toys'")], "join")
    add("q08", "Which product category earned the most revenue?", "answer", [top_cat[0][0]], "grouping")
    add("q09", "Which city has the most customers?", "answer", [top_city[0][0]], "grouping")
    add("q10", "What is the name of the most expensive product?", "answer", [top_prod[0][0]], "grouping")
    add("q11", "What is the price difference between the most expensive and the cheapest product?", "answer",
        [r2(prices)], "calculation", True)
    add("q12", "What percent of all orders have the status 'cancelled'?", "answer",
        [r2(100.0 * one("SELECT COUNT(*) FROM orders WHERE status='cancelled'") / one("SELECT COUNT(*) FROM orders"))],
        "calculation", True)
    add("q13", "What is the average order value, and what percent above the minimum order value is it? "
        "(order value = sum of quantity * unit_price of its items)", "answer",
        [r2(avg_ov), r2((avg_ov - min_ov) / min_ov * 100)], "calculation", True)
    add("q14", "What is the total revenue of the Electronics category, and what percent of the overall revenue is that?",
        "answer", [r2(elec_rev), r2(elec_rev / total_rev * 100)], "calculation", True)
    add("q15", "By what percent did total revenue grow from 2024 to 2025? (use the order year)", "answer",
        [r2((rev_y(2025) - rev_y(2024)) / rev_y(2024) * 100)], "calculation", True)
    add("q16", "How many different customers have placed at least one order?", "answer",
        [one("SELECT COUNT(DISTINCT customer_id) FROM orders")], "join")
    add("q17", "What is the average age of our customers?", "refuse", [], "cannot_answer")
    add("q18", "What was our total profit margin last year?", "refuse", [], "cannot_answer")
    con.close()
    return Q


if __name__ == "__main__":
    db = os.path.join(HERE, "data", "shop.db")
    if not os.path.exists(db):
        build_db.build(db)
    qs = build_questions(db)
    path = os.path.join(HERE, "questions.json")
    with open(path, "w") as f:
        json.dump(qs, f, indent=2)
    print(f"wrote {len(qs)} questions to {path}")
    for q in qs:
        print(q["id"], q["expected"], "-", q["question"])
