import akshare as ak

# Attempt to see if there is any other interface for batch downloading
print("Testing stock_zh_a_spot...")
try:
    df_spot = ak.stock_zh_a_spot()
    print("spot length:", len(df_spot))
except Exception as e:
    print("spot error:", e)

