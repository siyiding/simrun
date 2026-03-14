import pandas as pd
import numpy as np
import os
import pyarrow.parquet as pq
import pyarrow as pa
from loguru import logger
from tqdm import tqdm
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.feature_selection import RFE
from xgboost import XGBRegressor
import warnings
warnings.filterwarnings("ignore")

class FeatureEngineer:
    def __init__(self, data_dir="stock_data_parquet", output_dir="stock_features_parquet"):
        self.data_dir = data_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.add(os.path.join(self.output_dir, "feature_engineering.log"), rotation="10 MB")
        
        # 全局缩放器，避免不同股票之间的特征值不可比
        self.robust_scaler = RobustScaler()
        self.std_scaler = StandardScaler()
        self.is_scaler_fitted = False
        
        # 全局选中的特征子集
        self.global_selected_features = None

    def load_data(self, code):
        """加载阶段1处理好的 parquet 数据"""
        file_path = os.path.join(self.data_dir, f"{code}.parquet")
        if not os.path.exists(file_path):
            return None
        return pd.read_parquet(file_path)

    def calculate_technical_indicators(self, df):
        """计算技术指标 (MACD, RSI, OBV, 布林带, 均线等)"""
        # 确保数据按日期排序
        df = df.sort_values(by="日期").reset_index(drop=True)
        
        # 转换列名以适配 ta 库
        # 假设阶段1包含：'日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额'
        ta_df = df.copy()
        
        # 使用 ta 库一键添加所有特征 (约 80+ 个特征)
        try:
            ta_df = add_all_ta_features(
                ta_df, open="开盘", high="最高", low="最低", close="收盘", volume="成交量", fillna=True
            )
        except Exception as e:
            logger.error(f"TA库计算异常: {e}")
            return None

        # 额外添加自定义均线特征 (时序窗口设定为20日和60日)
        ta_df['ma20'] = ta_df['收盘'].rolling(window=20).mean()
        ta_df['ma60'] = ta_df['收盘'].rolling(window=60).mean()
        ta_df['ma20_60_diff'] = ta_df['ma20'] - ta_df['ma60'] # 多头排列特征

        # 目标变量 (Target): 预测未来 5 天的收益率
        ta_df['target_5d_return'] = ta_df['收盘'].shift(-5) / ta_df['收盘'] - 1.0
        
        # 剔除因为计算滚动窗口产生的 NaN
        ta_df = ta_df.dropna().reset_index(drop=True)
        return ta_df

    def scale_features_global_fit(self, all_df):
        """对全市场数据 fit 全局缩放器"""
        logger.info("开始计算全局标准化参数...")
        price_cols = ['开盘', '收盘', '最高', '最低']
        feature_cols = [c for c in all_df.columns if c not in price_cols + ['日期', '股票代码', 'code', 'target_5d_return']]
        
        if not feature_cols:
            return
            
        self.robust_scaler.fit(all_df[price_cols])
        self.std_scaler.fit(all_df[feature_cols])
        self.is_scaler_fitted = True
        
        # 将 scaler 保存到本地以供复用
        import joblib
        joblib.dump(self.robust_scaler, os.path.join(self.output_dir, 'robust_scaler.pkl'))
        joblib.dump(self.std_scaler, os.path.join(self.output_dir, 'std_scaler.pkl'))
        logger.info("全局标准化参数已保存。")

    def scale_features(self, df):
        """使用全局缩放器进行 transform"""
        price_cols = ['开盘', '收盘', '最高', '最低']
        feature_cols = [c for c in df.columns if c not in price_cols + ['日期', '股票代码', 'code', 'target_5d_return']]
        
        if not feature_cols or not self.is_scaler_fitted:
            return df

        df[price_cols] = self.robust_scaler.transform(df[price_cols])
        df[feature_cols] = self.std_scaler.transform(df[feature_cols])

        return df

    def select_features_global(self, all_df, top_n=20):
        """全局特征筛选：基于全市场数据，选出统一特征子集"""
        logger.info("开始全局特征筛选 (RFE)...")
        feature_cols = [c for c in all_df.columns if c not in ['日期', '股票代码', 'code', 'target_5d_return']]
        
        # 为加快速度，如果全市场数据太大，可以进行抽样
        sample_df = all_df.sample(n=min(len(all_df), 100000), random_state=42)
        X = sample_df[feature_cols]
        y = sample_df['target_5d_return']
        
        estimator = XGBRegressor(n_estimators=50, random_state=42, n_jobs=-1)
        selector = RFE(estimator, n_features_to_select=top_n, step=0.1)
        selector = selector.fit(X, y)
        
        self.global_selected_features = [feature_cols[i] for i, selected in enumerate(selector.support_) if selected]
        logger.info(f"全局筛选出的 Top {top_n} 特征为: {self.global_selected_features}")
        
        # 保存全局特征列表
        import json
        with open(os.path.join(self.output_dir, 'selected_features.json'), 'w') as f:
            json.dump(self.global_selected_features, f)

    def select_features(self, df):
        """应用全局特征子集"""
        if not self.global_selected_features:
            return df
            
        keep_cols = ['日期', '股票代码', 'code', 'target_5d_return'] + self.global_selected_features
        for p in ['开盘', '收盘', '最高', '最低', '成交量']:
            if p not in keep_cols and p in df.columns:
                keep_cols.append(p)
                
        return df[[c for c in keep_cols if c in df.columns]]

    def process_stock(self, df):
        """处理单只股票的特征生成（不包含标准化和筛选）"""
        if df is None or df.empty:
            return None
            
        # 1. 计算技术指标
        df = self.calculate_technical_indicators(df)
        return df

    def run(self):
        logger.info("=== 开始特征工程与筛选流程 ===")
        files = [f for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
        codes = [f.split('.')[0] for f in files]
        
        if not codes:
            logger.error("未找到第一阶段的数据，请先运行数据获取脚本。")
            return
            
        logger.info(f"待处理股票数量: {len(codes)}")
        
        # 第一阶段：计算所有股票的技术指标并汇总
        all_dfs = []
        for code in tqdm(codes, desc="计算技术指标"):
            df = self.load_data(code)
            processed_df = self.process_stock(df)
            if processed_df is not None and not processed_df.empty:
                all_dfs.append(processed_df)
                
        if not all_dfs:
            logger.error("没有任何有效股票数据进行特征工程。")
            return
            
        # 合并全市场数据
        all_market_df = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"汇总全市场数据，共计 {len(all_market_df)} 条记录")
        
        # 第二阶段：全局 fit 标准化器
        self.scale_features_global_fit(all_market_df)
        
        # 第三阶段：全局特征筛选
        self.select_features_global(all_market_df, top_n=20)
        
        # 第四阶段：应用全局规则，单独保存各股票的 parquet
        success_count = 0
        for df in tqdm(all_dfs, desc="特征转换与存储"):
            code = df['code'].iloc[0]
            # 标准化
            scaled_df = self.scale_features(df)
            # 筛选特征
            final_df = self.select_features(scaled_df)
            
            # 存储
            file_path = os.path.join(self.output_dir, f"{code}_features.parquet")
            table = pa.Table.from_pandas(final_df)
            pq.write_table(table, file_path)
            success_count += 1
                
        logger.info(f"=== 特征工程完成 ===")
        logger.info(f"成功处理并保存: {success_count} 只股票的特征数据。")
        self.verify_features()

    def verify_features(self):
        logger.info("进行特征质量验证...")
        files = [f for f in os.listdir(self.output_dir) if f.endswith('.parquet')]
        if files:
            sample_file = os.path.join(self.output_dir, files[0])
            sample_df = pd.read_parquet(sample_file)
            logger.info(f"抽样检查文件 {files[0]}，包含 {len(sample_df)} 条记录。")
            logger.info(f"最终保留字段数: {len(sample_df.columns)}")
            logger.info(f"字段样例: {list(sample_df.columns)[:15]}")

if __name__ == "__main__":
    engineer = FeatureEngineer(data_dir="stock_data_parquet", output_dir="stock_features_parquet")
    engineer.run()
