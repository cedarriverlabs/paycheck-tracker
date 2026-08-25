BEGIN;
DELETE FROM transactions;
DELETE FROM paycheck_periods;

WITH inserted AS (
  INSERT INTO paycheck_periods (start_date, end_date, label, is_current) VALUES
    ('2026-01-02', '2026-01-15', 'Jan 02 – Jan 15', false),
    ('2026-01-16', '2026-01-29', 'Jan 16 – Jan 29', false),
    ('2026-01-30', '2026-02-12', 'Jan 30 – Feb 12', false),
    ('2026-02-13', '2026-02-26', 'Feb 13 – Feb 26', false),
    ('2026-02-27', '2026-03-12', 'Feb 27 – Mar 12', false),
    ('2026-03-13', '2026-03-26', 'Mar 13 – Mar 26', false),
    ('2026-03-27', '2026-04-09', 'Mar 27 – Apr 09', false),
    ('2026-04-10', '2026-04-23', 'Apr 10 – Apr 23', false),
    ('2026-04-24', '2026-05-07', 'Apr 24 – May 07', false),
    ('2026-05-08', '2026-05-21', 'May 08 – May 21', false),
    ('2026-05-22', '2026-06-04', 'May 22 – Jun 04', false),
    ('2026-06-05', '2026-06-18', 'Jun 05 – Jun 18', false),
    ('2026-06-19', '2026-07-02', 'Jun 19 – Jul 02', false),
    ('2026-07-03', '2026-07-16', 'Jul 03 – Jul 16', false),
    ('2026-07-17', '2026-07-30', 'Jul 17 – Jul 30', false),
    ('2026-07-31', '2026-08-13', 'Jul 31 – Aug 13', false),
    ('2026-08-14', '2026-08-27', 'Aug 14 – Aug 27', true),
    ('2026-08-28', '2026-09-10', 'Aug 28 – Sep 10', false)
  RETURNING id, start_date
),
ordered AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY start_date) - 1 AS idx FROM inserted
)
INSERT INTO transactions (period_id, date, amount, category, subcategory, description, method, status)
SELECT o.id, t.date::date, t.amount, t.category, t.subcategory, t.description, t.method, t.status
FROM (VALUES
  (0, '2026-01-02', 3518.87, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (0, '2026-01-02', 1282.31, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (1, '2026-01-16', 3473.08, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (1, '2026-01-16', 1283.88, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (2, '2026-01-30', 3521.39, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (2, '2026-01-30', 1283.09, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (3, '2026-02-13', 3639.45, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (3, '2026-02-13', 1295.65, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (4, '2026-02-27', 3639.45, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (4, '2026-02-27', 1295.65, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (5, '2026-03-13', 3647.93, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (5, '2026-03-13', 1295.65, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (6, '2026-03-27', 3639.45, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (6, '2026-03-27', 1295.65, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (7, '2026-04-10', 3647.92, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (7, '2026-04-10', 1244.38, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (8, '2026-04-24', 3639.45, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (8, '2026-04-24', 1295.65, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (9, '2026-05-08', 3647.92, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (9, '2026-05-08', 1330.28, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (10, '2026-05-22', 3599.62, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (10, '2026-05-22', 1330.29, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (11, '2026-06-05', 3647.92, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (11, '2026-06-05', 1330.28, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (12, '2026-06-19', 3599.63, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (12, '2026-06-19', 1330.28, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (13, '2026-07-03', 3639.45, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (13, '2026-07-03', 1295.65, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (14, '2026-07-17', 3599.62, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (14, '2026-07-17', 1330.29, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (15, '2026-07-31', 3599.62, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (15, '2026-07-31', 1330.29, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (16, '2026-08-14', 3647.93, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (16, '2026-08-14', 1330.28, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid'),
  (17, '2026-08-28', 3639.45, 'Income', 'Doug Paycheck', NULL, 'Manual', 'Paid'),
  (17, '2026-08-28', 1295.65, 'Income', 'Amanda Paycheck', NULL, 'Manual', 'Paid')
) AS t(period_idx, date, amount, category, subcategory, description, method, status)
JOIN ordered o ON o.idx = t.period_idx;
COMMIT;
