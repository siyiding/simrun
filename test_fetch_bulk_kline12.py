import akshare as ak

print("Testing stock_info_sh_name_code...")
try:
    df1 = ak.stock_info_sh_name_code(symbol="主板A股")
    print("SH row count:", len(df1))
except Exception as e:
    print("error:", e)

print("Testing stock_info_sz_name_code...")
try:
    df2 = ak.stock_info_sz_name_code(symbol="A股列表")
    print("SZ row count:", len(df2))
except Exception as e:
    print("error:", e)
