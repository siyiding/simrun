with open('data_fetcher.py', 'r') as f:
    content = f.read()

# Fix netease timeout error
if 'timeout=10)' in content and 'stock_zh_a_daily' in content:
    content = content.replace('df = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date, end_date=end_date, timeout=10)', 
                              'df = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date, end_date=end_date)')

with open('data_fetcher.py', 'w') as f:
    f.write(content)
