import akshare as ak

# Try tencent daily
print("\nTesting stock_zh_a_hist_tx...")
try:
    df = ak.stock_zh_a_hist_tx(symbol="sz000001", start_date="20230101", end_date="20230110", adjust="qfq")
    print("tx row count for sz000001:", len(df))
    print(df.columns.tolist() if df is not None else None)
except Exception as e:
    print("Error tx:", e)

