import akshare as ak

# The issue is the user encountered a data limit or ban on EM. 
# There is stock_zh_a_daily (netease) or stock_zh_a_hist_tx (tencent).
# Tencent works. Wait, what about getting the stock pool? Em is timing out, Ths is failing with `<` (blocked by firewall or returns HTML).
# What about netease spot? No such thing.
print("Testing stock_info_a_code_name...")
try:
    df = ak.stock_info_a_code_name()
    print("row count:", len(df))
except Exception as e:
    print("error:", e)
