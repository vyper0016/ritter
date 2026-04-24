CREATE OR REPLACE VIEW user_outstanding_totals AS
SELECT user_id, payer_id, SUM(total_owed) AS grand_total
FROM unsettled_summary
GROUP BY user_id, payer_id;
