import akshare as ak

# Find any method that fetches all history at once
print("Testing stock_zh_a_hist_min_em...")
try:
    df = ak.stock_zh_a_hist_min_em(symbol="000001", period="1", adjust="qfq")
    print("row count:", len(df) if df is not None else 0)
except Exception as e:
    print("error:", e)
