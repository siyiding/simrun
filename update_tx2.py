with open('data_fetcher.py', 'r') as f:
    content = f.read()

# Replace tx function logic properly
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

import re
content = re.sub(r'    def _fetch_kline_tx.*?return df', tx_func, content, flags=re.DOTALL)

with open('data_fetcher.py', 'w') as f:
    f.write(content)
