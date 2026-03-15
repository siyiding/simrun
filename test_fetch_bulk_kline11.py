import akshare as ak

print("Testing stock_info_sh_name_code...")
try:
    df = ak.stock_info_sh_name_code(indicator="主板A股")
    print("row count:", len(df))
    print(df.head())
except Exception as e:
    print("error:", e)

print("Testing stock_info_sz_name_code...")
try:
    df = ak.stock_info_sz_name_code(indicator="A股列表")
    print("row count:", len(df))
except Exception as e:
    print("error:", e)
