from data_fetcher import DataFetcher
fetcher = DataFetcher("test_bulk", False)
df = fetcher._fetch_kline_netease("000001", "20230101", "20230110")
print("netease 000001:", len(df) if df is not None else 0)

df2 = fetcher._fetch_kline_tx("000001", "20230101", "20230110")
print("tx 000001:", len(df2) if df2 is not None else 0)

