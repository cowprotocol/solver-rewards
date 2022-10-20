select concat(
    to_char('{{StartTime}}'::timestamptz, 'YYYYMMDD'),
    to_char('{{EndTime}}'::timestamptz, 'YYYYMMDD')
) as accounting_period_hash