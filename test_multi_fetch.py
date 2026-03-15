import akshare as ak

print("Testing tool_trade_date_hist_sina...")
try:
    df_dates = ak.tool_trade_date_hist_sina()
    print("Trade dates fetched:", len(df_dates))
except Exception as e:
    print("Error fetching dates:", e)

# Test an interface that might support batch fetching
print("\nTesting stock_zh_a_spot_em...")
try:
    df_spot = ak.stock_zh_a_spot_em()
    print("Spot data columns:", df_spot.columns.tolist() if df_spot is not None else None)
    print("Spot data row count:", len(df_spot) if df_spot is not None else 0)
except Exception as e:
    print("Error:", e)

