import akshare as ak

print("Testing get_stock_pool with tx...")
from data_fetcher import DataFetcher
import pandas as pd
fetcher = DataFetcher(data_dir="test", use_parquet=False)

df = fetcher.fetch_daily_data("000001")
print(len(df) if df is not None else 0)
