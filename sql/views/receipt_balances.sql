CREATE OR REPLACE VIEW receipt_balances AS
SELECT li.receipt_id, ia.user_id, SUM(ia.amount) AS total_owed
FROM item_allocations ia
JOIN line_items li ON ia.line_item_id = li.id
GROUP BY li.receipt_id, ia.user_id;
