import akshare as ak

# For bulk fetching, does akshare have a way to download all stocks for a specific date?
try:
    df = ak.stock_zh_a_spot_em()
    print("spot ok")
except Exception as e:
    print(e)
