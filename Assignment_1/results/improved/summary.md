# Results: variant `improved`

- model: `hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M`
- questions: 18, trials each: 3
- **pass@1 = 0.704**  (average success of a single run)
- **pass^3 = 0.500**  (question solved in ALL 3 runs)
- pass@3 (any of 3) = 0.833
- mean tokens per run: 2971; mean time per run: 8.5s
- run statuses: {'ok': 52, 'step_cap': 2}

| id | category | passes | question |
|---|---|---|---|
| q01 | simple | 3/3 | How many customers are there? |
| q02 | simple | 1/3 | How many products are in the Books category? |
| q03 | simple | 2/3 | What is the average product price? |
| q04 | simple | 3/3 | How many orders have the status 'cancelled'? |
| q05 | join | 3/3 | What is the total revenue for customer 12? |
| q06 | join | 3/3 | How many orders did customer 7 place? |
| q07 | join | 3/3 | How many units (total quantity) of products in the Toys category were  |
| q08 | grouping | 2/3 | Which product category earned the most revenue? |
| q09 | grouping | 2/3 | Which city has the most customers? |
| q10 | grouping | 0/3 | What is the name of the most expensive product? |
| q11 | calculation | 3/3 | What is the price difference between the most expensive and the cheape |
| q12 | calculation | 2/3 | What percent of all orders have the status 'cancelled'? |
| q13 | calculation | 0/3 | What is the average order value, and what percent above the minimum or |
| q14 | calculation | 0/3 | What is the total revenue of the Electronics category, and what percen |
| q15 | calculation | 3/3 | By what percent did total revenue grow from 2024 to 2025? (use the ord |
| q16 | join | 3/3 | How many different customers have placed at least one order? |
| q17 | cannot_answer | 3/3 | What is the average age of our customers? |
| q18 | cannot_answer | 2/3 | What was our total profit margin last year? |

## Failure types (most common first)

- **wrong_refusal**: 9 runs. Example: "How many products are in the Books category?" -> SQL ["SELECT COUNT(p.id) FROM products p JOIN categories cg ON p.category_id = cg.id WHERE cg.name = 'Books'", "SELECT COUNT(p.id) FROM products p JOIN categories ca ON p.category_id = ca.id WHERE ca.name = 'Books'"] -> answer "The Books category does not exist in the database." (expected [6])
- **wrong_sql_logic**: 2 runs. Example: "What percent of all orders have the status 'cancelled'?" -> SQL ["SELECT SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) * 100 / COUNT(*) FROM orders"] -> answer "15% of all orders have the status 'cancelled'" (expected [15.75])
- **sql_error_then_wrong**: 2 runs. Example: "What is the average order value, and what percent above the minimum or" -> SQL ['SELECT AVG(total_value/order_id.quantity), AVG(total_value)/MIN(total_value) FROM (SELECT o.id AS order_id, SUM(oi.quantity*oi.unit_price) AS total_value FROM orders o JOIN order_items oi ON oi.order_id = o.id GROUP BY o.id)', 'SELECT AVG(oi.quantity * oi.unit_price) AS avg_order_value, \nCASE WHEN MAX(oi.quantity * oi.unit_price) IS NOT NULL THEN ((AVG(oi.quantity * oi.unit_price) - MIN(oi.quantity * oi.unit_price)) / MIN(oi.quantity * oi.unit_price)) * 100 ELSE 0 END AS percent_above_min FROM orders o JOIN order_items oi ON oi.order_id = o.id'] -> answer "The average order value is approximately $213.40 and it is about 2745% above the minimum order value" (expected [532.97, 7006.21])
- **step_cap**: 2 runs. Example: "What is the average order value, and what percent above the minimum or" -> SQL ['SELECT AVG(total_value/order_id.quantity), AVG(total_value)/MIN(total_value) FROM (SELECT o.id AS order_id, SUM(oi.quantity*oi.unit_price) AS total_value FROM orders o JOIN order_items oi ON oi.order_id = o.id GROUP BY o.id)', 'SELECT AVG(total_value/order_items.quantity) AS avg_order_value, \nCASE WHEN MAX(total_value)/MIN(total_value)>1 THEN ((MAX(total_value)-MIN(total_value))/MIN(total_value))*100 ELSE 0 END AS pct_above_min FROM (SELECT o.id, SUM(oi.quantity*oi.unit_price) as total_value FROM orders o JOIN order_items oi ON oi.order_id = o.id GROUP BY o.id)', 'SELECT AVG(total_value/order_id.quantity) AS avg_order_value, \nCASE WHEN AVG(total_value/order_id.quantity) > MIN(order_value) THEN ((AVG(total_value/order_id.quantity) - MIN(order_value)) / MIN(order_value)) * 100 ELSE 0 END AS percent_above_min FROM (SELECT o.id AS order_id, SUM(oi.quantity * oi.unit_price) AS total_value FROM orders o JOIN order_items oi ON oi.order_id = o.id GROUP BY o.id)', 'SELECT AVG(total_value/order_id.quantity) AS avg_order_value, \nCASE WHEN AVG(total_value/order_id.quantity) > MIN(total_value/order_id.quantity) THEN ((AVG(total_value/order_id.quantity)-MIN(total_value/order_id.quantity))/MIN(total_value/order_id.quantity))*100 ELSE 0 END AS percent_above_min\nFROM (SELECT o.id AS order_id, SUM(oi.quantity*oi.unit_price) AS total_value FROM orders o JOIN order_items oi ON oi.order_id = o.id GROUP BY o.id)'] -> answer "" (expected [532.97, 7006.21])
- **no_tool_use**: 1 runs. Example: "What is the total revenue of the Electronics category, and what percen" -> SQL ["SELECT SUM(p.price * oi.quantity) AS electronics_revenue, (SUM(p.price * oi.quantity) * 100 / SUM(o.products.sum_quantity * o.products.unit_price)) AS percentage FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id WHERE p.category = 'Electronics' GROUP BY electronics_revenue", "SELECT SUM(p.price * oi.quantity) AS electronics_revenue, (SUM(p.price * oi.quantity) * 100 / SUM(o.quantity * o.unit_price)) AS electronics_percent FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id WHERE p.category = 'Electronics'", "SELECT SUM(p.price * oi.quantity) AS electronics_revenue, (SUM(p.price * oi.quantity) * 100 / SUM(o.products.sum_revenue)) AS percentage FROM orders o JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id WHERE p.category = 'Electronics' GROUP BY p.category"] -> answer "The total revenue of the Electronics category is [calculated value] and it constitutes [percentage v" (expected [46081.42, 21.62])
