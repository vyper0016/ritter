CREATE OR REPLACE VIEW unsettled_summary AS
SELECT r.id, r.vendor_name, r.date, r.total, r.payer_id,
       rb.user_id, rb.total_owed,
       CASE WHEN r.total IS NOT NULL
            THEN ABS(r.total - COALESCE(li_sum.items_total, 0)) > 0.01
            ELSE false END AS ocr_mismatch,
       COALESCE(li_sum.items_total, 0) AS line_items_total
FROM receipts r
JOIN receipt_balances rb ON r.id = rb.receipt_id
LEFT JOIN (
    SELECT receipt_id, SUM(total) AS items_total
    FROM line_items
    GROUP BY receipt_id
) li_sum ON r.id = li_sum.receipt_id
WHERE r.settled = false;
