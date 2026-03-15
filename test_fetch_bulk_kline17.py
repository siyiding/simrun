import akshare as ak

print("Testing stock_zh_a_daily with 000001 (sz)...")
try:
    df = ak.stock_zh_a_daily(symbol="sz000001", start_date="20230101", end_date="20230110", adjust="qfq")
    print("daily length sz:", len(df))
except Exception as e:
    print("daily error:", e)

