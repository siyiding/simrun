# ML 量化交易系统 - 数据获取模块

本项目是量化交易系统的第一阶段：**数据获取与清洗模块**。

## 环境要求
- Python 3.9+
- 依赖库安装：
  ```bash
  pip install akshare pandas pyarrow loguru tqdm
  ```

## 核心功能
1. **获取全A股列表**：对接东方财富行情接口，拉取全量 A 股代码。
2. **数据清洗**：
   - 剔除 ST 股（包括 *ST）
   - 剔除退市股
   - 剔除停牌股票（基于当日成交量过滤）
3. **历史数据拉取**：获取指定日期以来的前复权日 K 线数据（开、高、低、收、成交量、成交额等）。
4. **高效存储**：默认采用 `Parquet` 格式存储（基于 PyArrow），相较于 CSV，读取速度极快，且占用空间更小。也支持 SQLite。

## 使用方法
执行主程序即可开始拉取数据：
```bash
python data_fetcher.py
```

默认会将数据保存在当前目录下的 `stock_data_parquet/` 文件夹中，每只股票一个 `.parquet` 文件。

### 配置参数
在 `data_fetcher.py` 底部可以修改配置：
```python
# data_dir: 存储目录
# use_parquet: True 为使用 Parquet(推荐)，False 为使用 SQLite
fetcher = DataFetcher(data_dir="stock_data_parquet", use_parquet=True)

# start_date: 历史数据起始日期
fetcher.run(start_date="20200101")
```

## 数据验证
脚本在拉取完成后，会自动调用 `verify_data()` 方法，打印出成功保存的文件数量及抽样文件的字段信息，确保数据格式完整。
\n## 阶段2：特征工程\n执行 `python feature_engineering.py` 进行技术指标计算、标准化与特征筛选。\n依赖 `ta`, `scikit-learn`, `xgboost`。
\n## 阶段3：XGBoost 模型训练\n执行 `python xgboost_trainer.py` 进行模型超参数调优、训练及评估，同时生成特征重要性分析报告。
\n## 阶段4：LSTM 模型训练\n执行 `python lstm_trainer.py` 进行基于滑动窗口的时序数据构建及LSTM深度学习模型的训练与评估。\n依赖 `tensorflow`, `keras`。
