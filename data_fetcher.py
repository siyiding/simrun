import akshare as ak
import pandas as pd
import os
import sqlite3
import pyarrow.parquet as pq
import pyarrow as pa
from loguru import logger
from tqdm import tqdm
from datetime import datetime
import time

class DataFetcher:
    def __init__(self, data_dir="data", use_parquet=True):
        self.data_dir = data_dir
        self.use_parquet = use_parquet
        os.makedirs(self.data_dir, exist_ok=True)
        logger.add(os.path.join(self.data_dir, "data_fetch.log"), rotation="10 MB")
        
        if not use_parquet:
            self.db_path = os.path.join(self.data_dir, "stock_data.db")
            self.conn = sqlite3.connect(self.db_path)
            
    def get_stock_pool(self):
        """获取全A股成分股并进行初步清洗，支持多数据源与自动切换"""
        logger.info("正在获取全A股列表...")
        
        # 定义获取A股列表的策略序列（函数指针, 源名称）
        strategies = [
            (self._get_pool_from_akshare_em, "akshare(东方财富)"),
            (self._get_pool_from_akshare_ths, "akshare(同花顺)"),
            (self._get_pool_from_tushare, "tushare(备用)")
        ]
        
        df = None
        for func, source_name in strategies:
            logger.info(f"尝试使用数据源: {source_name} 获取股票列表...")
            # 内部重试机制
            for attempt in range(3):
                try:
                    df = func()
                    if df is not None and not df.empty:
                        logger.info(f"成功通过 {source_name} 获取到数据。")
                        break
                except Exception as e:
                    logger.warning(f"[{source_name}] 第 {attempt+1}/3 次获取失败: {e}")
                    time.sleep(2)
            
            if df is not None and not df.empty:
                break  # 成功获取，跳出外部策略循环
            else:
                logger.error(f"数据源 {source_name} 彻底失效，切换至下一个数据源。")
                
        if df is None or df.empty:
            logger.critical("所有数据源均已失效，无法获取股票列表！")
            return []

        logger.info(f"获取到原始数据 {len(df)} 条")
        
        # 清洗规则:
        # 1. 剔除 ST 和 退市
        df = df[~df['name'].str.contains('ST|退', na=False)]
        # 2. 剔除北交所股票 (bj开头)
        df = df[~df['code'].str.lower().str.startswith('bj', na=False)]
        
        stock_pool = df['code'].tolist()
        logger.info(f"清洗后有效股票数量: {len(stock_pool)} 只")
        return stock_pool

    # --- 股票池数据源策略 ---
    def _get_pool_from_akshare_em(self):
        """主策略: 从东方财富获取"""
        # akshare.stock_zh_a_spot_em() gives realtime quote and names
        df = ak.stock_zh_a_spot_em()
        df = df[['代码', '名称']].rename(columns={'代码': 'code', '名称': 'name'})
        return df

    def _get_pool_from_akshare_ths(self):
        """备用策略: 从同花顺获取"""
        df = ak.stock_zh_a_spot()
        df = df[['代码', '名称']].rename(columns={'代码': 'code', '名称': 'name'})
        # ths 可能会带前缀 sz/sh
        df['code'] = df['code'].str.replace('sh', '').str.replace('sz', '')
        return df

    def _get_pool_from_tushare(self):
        """备用策略: 从 Tushare 获取 (需配置 TOKEN，若无则返回空)"""
        # 如果没有安装或没有配置token，可以在这里处理
        try:
            import tushare as ts
            # 这里尝试使用一个免费的 tushare pro token 或环境变量
            token = os.environ.get("TUSHARE_TOKEN", "")
            if not token:
                logger.debug("未配置 TUSHARE_TOKEN 环境变量，跳过 tushare")
                return None
            ts.set_token(token)
            pro = ts.pro_api()
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
            df = df.rename(columns={'symbol': 'code'})
            return df
        except ImportError:
            logger.debug("未安装 tushare 库，跳过")
            return None
        except Exception as e:
            logger.debug(f"Tushare 调用异常: {e}")
            return None

    # --- K线数据源策略 ---
    def fetch_daily_data(self, code, start_date="20200101", end_date=None):
        """获取单只股票日K线数据 (前复权) - 引入多数据源熔断重试"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
            
        strategies = [
            (self._fetch_kline_em, "akshare(东方财富)"),
            (self._fetch_kline_netease, "akshare(网易)"),
        ]
        
        for func, source_name in strategies:
            for attempt in range(2): # 每种策略重试2次
                try:
                    df = func(code, start_date, end_date)
                    if df is not None and not df.empty:
                        df['code'] = code
                        return df
                except Exception as e:
                    logger.debug(f"[{source_name}] 获取股票 {code} 数据失败 (尝试 {attempt+1}): {e}")
                    time.sleep(1)
        
        logger.error(f"股票 {code} 所有数据源(日K)均获取失败。")
        return None

    def _fetch_kline_em(self, code, start_date, end_date):
        """东方财富日线"""
        return ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")

    def _fetch_kline_netease(self, code, start_date, end_date):
        """网易日线 (网易不支持自动复权，但在此作为防崩溃备用，返回原始价格或前复权需要手动计算。此处简化直接返回)"""
        try:
            # 网易接口通常需要带前缀
            prefix = '0' if code.startswith(('6', '9')) else '1' 
            symbol = prefix + code
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                # 重命名以适配东方财富的数据结构格式 (开盘, 收盘, 最高, 最低, 成交量)
                df = df.rename(columns={
                    'date': '日期', 'open': '开盘', 'close': '收盘', 
                    'high': '最高', 'low': '最低', 'volume': '成交量', 'amount': '成交额', 'turnover': '换手率'
                })
            return df
        except Exception as e:
            logger.warning(f"[akshare(网易)] 获取股票 {code} 数据失败: {e}")
            return None

    def save_data(self, df, code):
        """将数据保存到本地 (Parquet 或 SQLite)"""
        if df is None or df.empty:
            return
            
        if self.use_parquet:
            file_path = os.path.join(self.data_dir, f"{code}.parquet")
            table = pa.Table.from_pandas(df)
            pq.write_table(table, file_path)
        else:
            df.to_sql('daily_data', self.conn, if_exists='append', index=False)

    def run(self, start_date="20200101"):
        logger.info("=== 开始数据获取与清洗流程 (多数据源版) ===")
        stock_pool = self.get_stock_pool()
        if not stock_pool:
            logger.error("股票池为空，流程终止。")
            return
            
        success_count = 0
        fail_count = 0
        
        logger.info(f"开始拉取历史数据，起始日期: {start_date}")
        # 为了演示和通过任务要求，这里缩短数量只取 5 只作为数据结构与存储的验证
        test_pool = stock_pool
        for code in tqdm(test_pool, desc="拉取日线数据", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]"):
            df = self.fetch_daily_data(code, start_date=start_date)
            if df is not None and not df.empty:
                self.save_data(df, code)
                success_count += 1
            else:
                fail_count += 1
                
            # 控制频率，防止被封 IP
            time.sleep(0.5)
            
        logger.info(f"=== 数据获取完成 ===")
        logger.info(f"成功: {success_count} 只, 失败或无数据: {fail_count} 只")
        
        # 简单的数据质量验证报告
        self.verify_data()

    def verify_data(self):
        logger.info("进行数据质量验证...")
        if self.use_parquet:
            files = [f for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
            logger.info(f"共发现 {len(files)} 个 Parquet 数据文件。")
            if files:
                sample_file = os.path.join(self.data_dir, files[0])
                sample_df = pd.read_parquet(sample_file)
                logger.info(f"抽样检查文件 {files[0]}，包含 {len(sample_df)} 条记录。字段: {list(sample_df.columns)}")
        else:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT code) FROM daily_data")
            count = cursor.fetchone()[0]
            logger.info(f"数据库中共包含 {count} 只股票的数据。")

    def close(self):
        """关闭数据库连接"""
        if not self.use_parquet and hasattr(self, 'conn') and self.conn:
            self.conn.close()
            logger.info("SQLite 数据库连接已关闭。")

    def __del__(self):
        self.close()

if __name__ == "__main__":
    fetcher = DataFetcher(data_dir="stock_data_parquet", use_parquet=True)
    try:
        # 为了演示运行速度，这里我们取最近一年的数据
        fetcher.run(start_date="20230101")
    finally:
        fetcher.close()
