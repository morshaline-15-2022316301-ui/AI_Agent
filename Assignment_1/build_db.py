"""Create and fill the dummy shop database. Fixed seed => same data every time.

    python3 build_db.py            # writes data/shop.db
"""
import os
import random
import sqlite3
import sys

SEED = 42
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "shop.db")

SCHEMA = """
CREATE TABLE customers (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    signup_date TEXT NOT NULL            -- 'YYYY-MM-DD'
);
CREATE TABLE products (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    price    REAL NOT NULL               -- current list price in USD
);
CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date  TEXT NOT NULL,           -- 'YYYY-MM-DD', years 2024 and 2025
    status      TEXT NOT NULL            -- 'completed', 'cancelled' or 'pending'
);
CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL,
    unit_price REAL NOT NULL             -- price paid per unit
);
"""

FIRST = ["Aisha", "Bilal", "Chitra", "Dev", "Eshita", "Farhan", "Gita", "Hasan", "Ishrat", "Jamal",
         "Kabir", "Laila", "Mahir", "Nabila", "Omar", "Priya", "Rafi", "Sadia", "Tanvir", "Umme"]
LAST = ["Ahmed", "Banik", "Chowdhury", "Das", "Elahi", "Farooq"]
CITIES = ["Dhaka", "Chattogram", "Khulna", "Rajshahi", "Sylhet", "Barishal", "Rangpur", "Mymensingh"]
CATEGORIES = {
    "Electronics": ["Headphones", "Phone Charger", "Power Bank", "Webcam", "Keyboard", "Mouse"],
    "Books": ["Novel", "Cookbook", "Atlas", "Dictionary", "Biography", "Poetry Book"],
    "Clothing": ["T-Shirt", "Jeans", "Jacket", "Scarf", "Socks", "Cap"],
    "Home": ["Lamp", "Cushion", "Mug Set", "Clock", "Vase", "Towel Set"],
    "Toys": ["Puzzle", "Toy Car", "Board Game", "Doll", "Building Blocks", "Kite"],
}
N_CUSTOMERS, N_ORDERS = 120, 400


def build(path=DB_PATH, seed=SEED):
    rng = random.Random(seed)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    for i in range(1, N_CUSTOMERS + 1):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        date = f"{rng.choice([2023, 2024])}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        con.execute("INSERT INTO customers VALUES (?,?,?,?)", (i, name, rng.choice(CITIES), date))

    pid = 0
    for cat, names in CATEGORIES.items():
        for n in names:
            pid += 1
            con.execute("INSERT INTO products VALUES (?,?,?,?)",
                        (pid, n, cat, round(rng.uniform(5, 150), 2)))
    prices = dict(con.execute("SELECT id, price FROM products"))

    item_id = 0
    for oid in range(1, N_ORDERS + 1):
        date = f"{rng.choice([2024, 2025])}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        status = rng.choices(["completed", "cancelled", "pending"], weights=[75, 15, 10])[0]
        con.execute("INSERT INTO orders VALUES (?,?,?,?)",
                    (oid, rng.randint(1, N_CUSTOMERS), date, status))
        for p in rng.sample(sorted(prices), rng.randint(1, 4)):
            item_id += 1
            con.execute("INSERT INTO order_items VALUES (?,?,?,?,?)",
                        (item_id, oid, p, rng.randint(1, 5), prices[p]))
    con.commit()
    con.close()
    return path


if __name__ == "__main__":
    out = build(sys.argv[1] if len(sys.argv) > 1 else DB_PATH)
    con = sqlite3.connect(out)
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        print(f"{t:12s} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]} rows")
