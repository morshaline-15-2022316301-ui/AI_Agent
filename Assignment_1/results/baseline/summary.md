# Results: variant `baseline`

- model: `hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M`
- questions: 18, trials each: 3
- **pass@1 = 0.741**  (average success of a single run)
- **pass^3 = 0.556**  (question solved in ALL 3 runs)
- pass@3 (any of 3) = 0.889
- mean tokens per run: 2538; mean time per run: 7.6s
- run statuses: {'ok': 54}

| id | category | passes | question |
|---|---|---|---|
| q01 | simple | 3/3 | How many customers are there? |
| q02 | simple | 3/3 | How many products are in the Books category? |
| q03 | simple | 3/3 | What is the average product price? |
| q04 | simple | 3/3 | How many orders have the status 'cancelled'? |
| q05 | join | 3/3 | What is the total revenue for customer 12? |
| q06 | join | 3/3 | How many orders did customer 7 place? |
| q07 | join | 3/3 | How many units (total quantity) of products in the Toys category were  |
| q08 | grouping | 2/3 | Which product category earned the most revenue? |
| q09 | grouping | 1/3 | Which city has the most customers? |
| q10 | grouping | 3/3 | What is the name of the most expensive product? |
| q11 | calculation | 3/3 | What is the price difference between the most expensive and the cheape |
| q12 | calculation | 0/3 | What percent of all orders have the status 'cancelled'? |
| q13 | calculation | 2/3 | What is the average order value, and what percent above the minimum or |
| q14 | calculation | 0/3 | What is the total revenue of the Electronics category, and what percen |
| q15 | calculation | 1/3 | By what percent did total revenue grow from 2024 to 2025? (use the ord |
| q16 | join | 3/3 | How many different customers have placed at least one order? |
| q17 | cannot_answer | 2/3 | What is the average age of our customers? |
| q18 | cannot_answer | 2/3 | What was our total profit margin last year? |

## Failure types (most common first)

- **wrong_refusal**: 5 runs. Example: "Which city has the most customers?" -> SQL [] -> answer "address_city column is missing from the customers table" (expected ['Dhaka'])
- **wrong_sql_logic**: 5 runs. Example: "What percent of all orders have the status 'cancelled'?" -> SQL ["SELECT CAST(COUNT(*) AS REAL) * 100 / (SELECT COUNT(*) FROM orders WHERE status = 'completed' OR status = 'pending') FROM orders WHERE status = 'cancelled'"] -> answer "About 18.69% of all orders have the status 'cancelled'." (expected [15.75])
- **sql_error_then_wrong**: 2 runs. Example: "Which product category earned the most revenue?" -> SQL ['SELECT p.category, SUM(p.price * oi.quantity) AS Total_Revenue FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.category'] -> answer "The Electronics category earned the most revenue with a total of $46,081.42." (expected ['Clothing'])
- **hallucinated_answer**: 2 runs. Example: "What is the average age of our customers?" -> SQL ['SELECT AVG(EXTRACT(YEAR FROM AGE(signup_date))) AS avg_age FROM customers', "SELECT AVG(julianday(signup_date) - julianday('1900-01-01')) AS avg_age FROM customers"] -> answer "The average age of our customers is approximately 45279 years." (expected [])
