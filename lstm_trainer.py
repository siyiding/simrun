import pandas as pd
import numpy as np
import os
import pyarrow.parquet as pq
from loguru import logger
from tqdm import tqdm
import tensorflow as tf
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout, BatchNormalization
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import json

class LSTMTrainer:
    def __init__(self, data_dir="stock_features_parquet", model_dir="models", seq_length=20):
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.seq_length = seq_length  # 时间步长(滑窗大小)，例如使用过去20天的数据
        os.makedirs(self.model_dir, exist_ok=True)
        logger.add(os.path.join(self.model_dir, "lstm_training.log"), rotation="10 MB")

    def create_sequences(self, df, feature_cols):
        """将2D的DataFrame转换为3D的滑动窗口时序数据"""
        # 注意：这里需要按单只股票分别处理以避免把上一只股票的数据混进下一只股票
        X, y = [], []
        
        features = df[feature_cols].values
        targets = df['target_5d_return'].values
        
        if len(df) <= self.seq_length:
            return np.array([]), np.array([])
            
        for i in range(len(df) - self.seq_length):
            X.append(features[i : (i + self.seq_length)])
            # 预测的是窗口最后一天之后(shift处理过)的目标
            y.append(targets[i + self.seq_length - 1])
            
        return np.array(X), np.array(y)

    def load_and_prepare_data(self):
        """加载数据并生成滑动窗口时序集"""
        logger.info("开始加载所有特征数据并生成时序窗口...")
        files = [f for f in os.listdir(self.data_dir) if f.endswith('_features.parquet')]
        
        if not files:
            logger.error("未找到特征数据。")
            return None, None, None
            
        X_list, y_list = [], []
        feature_cols = None
        
        for file in tqdm(files, desc="处理时序滑窗数据"):
            file_path = os.path.join(self.data_dir, file)
            df = pd.read_parquet(file_path)
            
            # 按日期严格排序
            df = df.sort_values(by="日期").reset_index(drop=True)
            
            if feature_cols is None:
                feature_cols = [c for c in df.columns if c not in ['日期', '股票代码', 'code', 'target_5d_return']]
                
            X_seq, y_seq = self.create_sequences(df, feature_cols)
            if len(X_seq) > 0:
                X_list.append(X_seq)
                y_list.append(y_seq)
                
        if not X_list:
            return None, None, None
            
        X_all = np.concatenate(X_list, axis=0)
        y_all = np.concatenate(y_list, axis=0)
        
        logger.info(f"生成 3D 时序特征矩阵 X_all.shape = {X_all.shape}")
        return X_all, y_all, feature_cols

    def build_model(self, input_shape):
        """构建 LSTM 神经网络"""
        model = Sequential([
            LSTM(units=64, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            BatchNormalization(),
            
            LSTM(units=32, return_sequences=False),
            Dropout(0.2),
            BatchNormalization(),
            
            Dense(units=16, activation='relu'),
            Dense(units=1)  # 预测单个收益率
        ])
        
        optimizer = Adam(learning_rate=0.001)
        model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        return model

    def evaluate_model(self, model, X_test, y_test):
        """评估 LSTM 模型表现"""
        logger.info("开始评估 LSTM 模型...")
        y_pred = model.predict(X_test).flatten()
        
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
        logger.info(f"LSTM 模型评估结果: {metrics}")
        return metrics

    def run(self):
        logger.info("=== 开始 LSTM 模型训练流程 ===")
        
        X_all, y_all, feature_cols = self.load_and_prepare_data()
        if X_all is None:
            return
            
        # 时序切分: 前 80% 训练，后 20% 测试
        split_idx = int(len(X_all) * 0.8)
        X_train, X_test = X_all[:split_idx], X_all[split_idx:]
        y_train, y_test = y_all[:split_idx], y_all[split_idx:]
        
        logger.info(f"训练集 X_train: {X_train.shape}, 测试集 X_test: {X_test.shape}")
        
        # 构建模型
        model = self.build_model((X_train.shape[1], X_train.shape[2]))
        model.summary(print_fn=logger.info)
        
        # 回调函数
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ModelCheckpoint(filepath=os.path.join(self.model_dir, 'best_lstm_model.keras'),
                            monitor='val_loss', save_best_only=True)
        ]
        
        # 训练模型
        logger.info("开始拟合 LSTM 模型...")
        history = model.fit(
            X_train, y_train,
            epochs=50,
            batch_size=128,
            validation_split=0.2, # 从训练集中再划分20%作为验证集用于早停
            callbacks=callbacks,
            verbose=1
        )
        
        # 加载最佳权重并评估
        model.load_weights(os.path.join(self.model_dir, 'best_lstm_model.keras'))
        metrics = self.evaluate_model(model, X_test, y_test)
        
        # 保存元数据
        metadata = {
            "model_type": "LSTM",
            "seq_length": self.seq_length,
            "metrics": metrics,
            "features_used": feature_cols
        }
        with open(os.path.join(self.model_dir, "lstm_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        logger.info("=== LSTM 训练流程完成 ===")

if __name__ == "__main__":
    trainer = LSTMTrainer()
    trainer.run()
