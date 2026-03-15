with open('data_fetcher.py', 'r') as f:
    content = f.read()

# Add tx strategy inside get_stock_pool? There's no tx stock pool.
# We will disable the tqdm print for tx which happens inside `akshare/stock/stock_zh_a_hist_tx.py`.
import re

tx_func = '''    def _fetch_kline_tx(self, code, start_date, end_date):
        """腾讯日线 (主用)"""
        prefix = 'sh' if code.startswith(('6', '9')) else 'sz' 
        symbol = prefix + code
        df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
        if df is not None and not df.empty:
            df = df.rename(columns={
                'date': '日期', 'open': '开盘', 'close': '收盘', 
                'high': '最高', 'low': '最低', 'amount': '成交额'
            })
            if '成交量' not in df.columns:
                df['成交量'] = df['成交额'] / df['收盘'] if '收盘' in df.columns else 0.0
            if '换手率' not in df.columns:
                df['换手率'] = 0.0
        return df'''

if 'akshare(腾讯)' not in content:
    content = content.replace('(self._fetch_kline_em, "akshare(东方财富)"),', '(self._fetch_kline_tx, "akshare(腾讯)"),\n            (self._fetch_kline_em, "akshare(东方财富)"),')

if 'def _fetch_kline_tx' not in content:
    content = content.replace('def _fetch_kline_em', tx_func + '\n\n    def _fetch_kline_em')

# We need a robust way to get pool if all others fail. Just return a hardcoded list of standard index components if we really can't get it? No, Tushare Pro works. We can use index components from szse/sse as fallback.
with open('data_fetcher.py', 'w') as f:
    f.write(content)
