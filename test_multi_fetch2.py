import akshare as ak

print("\nTesting stock_zh_a_spot...")
try:
    df_spot = ak.stock_zh_a_spot()
    print("Spot data columns:", df_spot.columns.tolist() if df_spot is not None else None)
    print("Spot data row count:", len(df_spot) if df_spot is not None else 0)
except Exception as e:
    print("Error:", e)

