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

    def scale_features(self, df):
        """
        特征标准化：
        技术指标采用Z-Score (StandardScaler)
        价格数据采用Robust方法 (RobustScaler)
        """
        price_cols = ['开盘', '收盘', '最高', '最低']
        feature_cols = [c for c in df.columns if c not in price_cols + ['日期', '股票代码', 'code', 'target_5d_return']]
        
        if not feature_cols:
            return df

        # 价格类特征使用 RobustScaler
        robust_scaler = RobustScaler()
        df[price_cols] = robust_scaler.fit_transform(df[price_cols])

        # 技术指标类使用 Z-Score (StandardScaler)
        std_scaler = StandardScaler()
        df[feature_cols] = std_scaler.fit_transform(df[feature_cols])

        return df

    def select_features(self, df, top_n=20):
        """特征筛选：通过XGBoost重要性评估及递归消除(RFE)实现"""
        # 准备特征与目标
        feature_cols = [c for c in df.columns if c not in ['日期', '股票代码', 'code', 'target_5d_return']]
        X = df[feature_cols]
        y = df['target_5d_return']
        
        if len(X) < 100:
            # 样本量太小，跳过筛选直接返回
            return df

        # 使用 XGBoost 作为评估器
        estimator = XGBRegressor(n_estimators=50, random_state=42, n_jobs=-1)
        
        # 递归特征消除 (RFE)
        # 为了速度，step设为0.1(每次剔除10%)
        selector = RFE(estimator, n_features_to_select=top_n, step=0.1)
        selector = selector.fit(X, y)
        
        # 获取筛选出的特征名
        selected_features = [feature_cols[i] for i, selected in enumerate(selector.support_) if selected]
        
        # 返回仅包含重要特征的 DataFrame
        keep_cols = ['日期', '股票代码', 'code', 'target_5d_return'] + selected_features
        # 保证不丢失基础价格列（哪怕没被选上，为了后续回测可能需要）
        for p in ['开盘', '收盘', '最高', '最低', '成交量']:
            if p not in keep_cols and p in df.columns:
                keep_cols.append(p)
                
        return df[keep_cols], selected_features

    def process_stock(self, code):
        """处理单只股票的完整特征工程链路"""
        df = self.load_data(code)
        if df is None or df.empty:
            return False
            
        # 1. 计算技术指标
        df = self.calculate_technical_indicators(df)
        if df is None or df.empty:
            return False
            
        # 2. 数据标准化
        df = self.scale_features(df)
        
        # 3. 特征筛选 (针对每只股票选出20个重要特征)
        df, selected_features = self.select_features(df, top_n=20)
        
        # 4. 存储
        file_path = os.path.join(self.output_dir, f"{code}_features.parquet")
        table = pa.Table.from_pandas(df)
        pq.write_table(table, file_path)
        
        return True

    def run(self):
        logger.info("=== 开始特征工程与筛选流程 ===")
        files = [f for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
        codes = [f.split('.')[0] for f in files]
        
        if not codes:
            logger.error("未找到第一阶段的数据，请先运行数据获取脚本。")
            return
            
        success_count = 0
        logger.info(f"待处理股票数量: {len(codes)}")
        
        for code in tqdm(codes, desc="特征工程处理"):
            if self.process_stock(code):
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
