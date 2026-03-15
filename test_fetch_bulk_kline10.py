import akshare as ak

print("Testing stock_zh_a_spot_em...")
try:
    df = ak.stock_zh_a_spot_em()
    print("spot_em count:", len(df))
except Exception as e:
    print("error:", e)
