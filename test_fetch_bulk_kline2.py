import akshare as ak
try:
    print("\nTesting tool_trade_date_hist_sina...")
    df = ak.tool_trade_date_hist_sina()
    print("trade date count:", len(df))
except Exception as e:
    print("Error:", e)

try:
    print("\nTesting stock_zh_a_hist (EM)...")
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20230101", end_date="20230110", adjust="qfq")
    print("EM row count for 000001:", len(df))
except Exception as e:
    print("Error EM:", e)
