import akshare as ak

print("Testing stock_zh_a_spot...")
try:
    df_spot = ak.stock_zh_a_spot()
    print("spot length:", len(df_spot))
except Exception as e:
    print("spot error:", e)

