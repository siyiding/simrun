import akshare as ak

print("Testing stock_zh_a_daily with ne ...")
try:
    df = ak.stock_zh_a_daily(symbol="sz000001", start_date="20230101", end_date="20230110")
    print(df.head() if df is not None else None)
except Exception as e:
    print(e)
