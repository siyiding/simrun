with open('data_fetcher.py', 'r') as f:
    content = f.read()

tx_func = '''    def _fetch_kline_tx(self, code, start_date, end_date):
        """腾讯日线"""
        # 腾讯接口通常需要带前缀
        prefix = 'sh' if code.startswith(('6', '9')) else 'sz' 
        symbol = prefix + code
        df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
        if df is not None and not df.empty:
            df = df.rename(columns={
                'date': '日期', 'open': '开盘', 'close': '收盘', 
                'high': '最高', 'low': '最低', 'amount': '成交额'
            })
            # 腾讯接口没有成交量和换手率，但为了兼容，我们把成交量设为 0 或者用成交额凑合
            if '成交量' not in df.columns:
                df['成交量'] = 0.0
            if '换手率' not in df.columns:
                df['换手率'] = 0.0
        return df

    def _fetch_kline_em'''

content = content.replace('    def _fetch_kline_em', tx_func)

with open('data_fetcher.py', 'w') as f:
    f.write(content)
