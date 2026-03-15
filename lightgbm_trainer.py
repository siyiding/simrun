import pandas as pd
import numpy as np
import os
import pyarrow.parquet as pq
from loguru import logger
from tqdm import tqdm
from lightgbm import LGBMRegressor
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import json
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings("ignore")

class LightGBMTrainer:
    def __init__(self, data_dir="stock_features_parquet", model_dir="models"):
        self.data_dir = data_dir
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        logger.add(os.path.join(self.model_dir, "lightgbm_training.log"), rotation="10 MB")
        self.model = None

    def load_all_data(self):
        """加载所有股票的特征数据并合并，进行时间排序"""
        logger.info("开始加载所有特征数据...")
        files = [f for f in os.listdir(self.data_dir) if f.endswith('_features.parquet')]
        
        if not files:
            logger.error("未找到特征数据，请先运行特征工程脚本。")
            return None
            
        dfs = []
        for file in tqdm(files, desc="加载 Parquet 数据"):
            file_path = os.path.join(self.data_dir, file)
            df = pd.read_parquet(file_path)
            # 确保存在所需的列
            if 'target_5d_return' in df.columns:
                dfs.append(df)
                
        if not dfs:
            return None
            
        all_df = pd.concat(dfs, ignore_index=True)
        
        # 按照日期排序（对于时序模型非常重要）
        all_df = all_df.sort_values(by="日期").reset_index(drop=True)
        logger.info(f"成功加载并合并 {len(all_df)} 条数据。")
        return all_df

    def prepare_train_test_split(self, df, test_size=0.2):
        """
        按时序进行训练集和测试集的划分 (不能随机打乱)
        """
        logger.info("开始划分训练集与测试集 (按时间序列)...")
        # 移除标识列和目标列来获取特征X
        feature_cols = [c for c in df.columns if c not in ['日期', '股票代码', 'code', 'target_5d_return']]
        X = df[feature_cols]
        y = df['target_5d_return']
        
        # 简单时序划分
        split_idx = int(len(df) * (1 - test_size))
        
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        logger.info(f"训练集形状: {X_train.shape}, 测试集形状: {X_test.shape}")
        return X_train, X_test, y_train, y_test, feature_cols

    def tune_hyperparameters(self, X_train, y_train):
        """使用随机搜索进行超参数调优 (结合时序交叉验证)"""
        logger.info("开始进行超参数调优 (RandomizedSearchCV)...")
        
        # 基础模型
        base_model = LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1)
        
        # 参数网格
        param_dist = {
            'n_estimators': [100, 200, 300, 500],
            'learning_rate': [0.01, 0.05, 0.1, 0.2],
            'max_depth': [3, 5, 7, 10, -1],
            'num_leaves': [15, 31, 63, 127],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
            'min_child_samples': [5, 10, 20, 30],
            'reg_alpha': [0, 0.1, 0.5],
            'reg_lambda': [0, 0.1, 0.5]
        }
        
        # 时序交叉验证 (TimeSeriesSplit) - 避免未来数据泄露到过去
        tscv = TimeSeriesSplit(n_splits=3)
        
        # 为了加速演示，n_iter=10，实际使用可以调高
        random_search = RandomizedSearchCV(
            estimator=base_model,
            param_distributions=param_dist,
            n_iter=10, 
            scoring='neg_mean_squared_error',
            cv=tscv,
            verbose=1,
            random_state=42,
            n_jobs=-1
        )
        
        random_search.fit(X_train, y_train)
        
        best_params = random_search.best_params_
        logger.info(f"超参数调优完成。最佳参数: {best_params}")
        
        return random_search.best_estimator_, best_params

    def evaluate_model(self, model, X_test, y_test):
        """评估模型表现"""
        logger.info("开始在测试集上评估模型...")
        y_pred = model.predict(X_test)
        
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        metrics = {
            "MSE": float(mse),
            "RMSE": float(rmse),
            "MAE": float(mae),
            "R2": float(r2)
        }
        
        logger.info(f"模型评估结果: {metrics}")
        return metrics

    def plot_feature_importance(self, model, feature_cols):
        """分析并保存特征重要性"""
        logger.info("分析特征重要性...")
        importance = model.feature_importances_
        
        # 排序
        feat_imp = pd.DataFrame({
            'Feature': feature_cols,
            'Importance': importance
        }).sort_values(by='Importance', ascending=False)
        
        # 保存为 CSV 供查阅
        feat_imp_path = os.path.join(self.model_dir, "lightgbm_feature_importance.csv")
        feat_imp.to_csv(feat_imp_path, index=False)
        logger.info(f"特征重要性已保存至 {feat_imp_path}")
        
        # 取 Top 15 画图
        top_15 = feat_imp.head(15)
        
        plt.figure(figsize=(10, 6))
        plt.barh(top_15['Feature'][::-1], top_15['Importance'][::-1], color='lightgreen')
        plt.xlabel('LightGBM Feature Importance')
        plt.title('Top 15 Most Important Features')
        plt.tight_layout()
        
        plot_path = os.path.join(self.model_dir, "lightgbm_feature_importance.png")
        plt.savefig(plot_path)
        plt.close()

    def run(self):
        logger.info("=== 开始 LightGBM 训练流程 ===")
        
        df = self.load_all_data()
        if df is None or df.empty:
            return
            
        X_train, X_test, y_train, y_test, feature_cols = self.prepare_train_test_split(df)
        
        # 模型调优与训练
        self.model, best_params = self.tune_hyperparameters(X_train, y_train)
        
        # 评估
        metrics = self.evaluate_model(self.model, X_test, y_test)
        
        # 特征重要性
        self.plot_feature_importance(self.model, feature_cols)
        
        # 序列化保存模型与参数
        model_path = os.path.join(self.model_dir, "lightgbm_model.pkl")
        joblib.dump(self.model, model_path)
        logger.info(f"模型已序列化保存至 {model_path}")
        
        # 保存元数据
        metadata = {
            "best_params": best_params,
            "metrics": metrics,
            "features_used": feature_cols
        }
        with open(os.path.join(self.model_dir, "lightgbm_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        logger.info("=== LightGBM 训练流程完成 ===")

if __name__ == "__main__":
    trainer = LightGBMTrainer(data_dir="stock_features_parquet", model_dir="models")
    trainer.run()
