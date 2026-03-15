import akshare as ak

print("Testing stock_zh_a_spot_em...")
try:
    df_spot = ak.stock_zh_a_spot_em()
    print("spot_em ok")
except Exception as e:
    print("error:", e)
