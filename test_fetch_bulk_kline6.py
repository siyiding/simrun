import akshare as ak

# Attempt stock_zh_a_hist again without adjust to see if it makes a difference, or different timeout
print("\nTesting stock_zh_a_hist with different timeout...")
try:
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20230101", end_date="20230110", adjust="qfq", timeout=30)
    print("EM row count for 000001:", len(df))
except Exception as e:
    print("Error EM:", e)

