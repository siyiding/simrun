import akshare as ak

print("Testing stock_zh_a_spot_em...")
try:
    # Just to get codes again
    df = ak.stock_zh_a_spot_em()
    print("Found rows:", len(df))
except Exception as e:
    print("Error:", e)

# Test batch K line endpoints
print("Testing stock_zh_a_daily...")
try:
    df2 = ak.stock_zh_a_daily(symbol='sh600000', start_date='20230101', end_date='20230110')
    print("stock_zh_a_daily row count for sh600000:", len(df2))
except Exception as e:
    print("Error stock_zh_a_daily:", e)

