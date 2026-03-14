import os
import json
import logging
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import load_model

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s')

def load_data(parquet_dir="stock_features_parquet"):
    logging.info(f"Loading data from {parquet_dir}...")
    files = [os.path.join(parquet_dir, f) for f in os.listdir(parquet_dir) if f.endswith('.parquet')]
    dfs = []
    for file in files:
        df = pd.read_parquet(file)
        dfs.append(df)
    
    data = pd.concat(dfs, ignore_index=True)
    
    # Check if target exists
    if 'target_5d_return' not in data.columns:
        raise ValueError("Target column 'target_5d_return' not found in data.")
    
    # Sort by date and stock_code to ensure temporal split is correct
    if 'date' in data.columns and 'stock_code' in data.columns:
         data = data.sort_values(by=['stock_code', 'date']).reset_index(drop=True)
    
    return data

def evaluate_predictions(y_true, y_pred, model_name):
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    
    logging.info(f"--- {model_name} Evaluation ---")
    logging.info(f"MAE:  {mae:.4f}")
    logging.info(f"RMSE: {rmse:.4f}")
    logging.info(f"R2:   {r2:.4f}")
    
    return {"MAE": mae, "RMSE": rmse, "R2": r2}

def run_fusion():
    logging.info("=== Starting Phase 5: Model Fusion ===")
    
    # 1. Load Data & Features
    data = load_data()
    
    # Load XGB features
    try:
        with open('models/xgboost_metadata.json', 'r') as f:
            xgb_meta = json.load(f)
            feature_cols = xgb_meta.get('features_used', [])
    except Exception as e:
        logging.warning(f"Could not load XGB metadata, extracting from data... {e}")
        exclude_cols = ['date', 'stock_code', 'target_5d_return']
        feature_cols = [c for c in data.columns if c not in exclude_cols]
        
    if not feature_cols:
        raise ValueError("No feature columns identified.")
        
    logging.info(f"Using {len(feature_cols)} features.")

    # 2. Prepare Data (need to align samples for both models)
    seq_length = 20
    
    aligned_features_lstm = []
    aligned_features_xgb = []
    aligned_targets = []
    
    # Use fallback block if stock_code not in columns since previous script returned size 0
    if 'stock_code' in data.columns:
        grouped = data.groupby('stock_code')
        for _, group in grouped:
            group = group.sort_values(by='date')
            vals = group[feature_cols].values
            targets = group['target_5d_return'].values
            
            for i in range(len(group) - seq_length):
                aligned_features_lstm.append(vals[i:i+seq_length])
                # Note: vals is 2D, vals[i+seq_length-1] gets the features of the last day in the window 
                aligned_features_xgb.append(vals[i+seq_length-1])
                aligned_targets.append(targets[i+seq_length-1])
    else:
        # Fallback if no stock_code, assume single continuous sequence (less safe)
        vals = data[feature_cols].values
        targets = data['target_5d_return'].values
        for i in range(len(data) - seq_length):
            aligned_features_lstm.append(vals[i:i+seq_length])
            aligned_features_xgb.append(vals[i+seq_length-1])
            aligned_targets.append(targets[i+seq_length-1])
                
    X_lstm_all = np.array(aligned_features_lstm)
    X_xgb_all = np.array(aligned_features_xgb)
    y_all = np.array(aligned_targets)
    
    test_size = int(len(y_all) * 0.2)
    train_size = len(y_all) - test_size
    
    X_lstm_test = X_lstm_all[train_size:]
    X_xgb_test = X_xgb_all[train_size:]
    y_test = y_all[train_size:]
    
    X_xgb_train = X_xgb_all[:train_size]
    y_train = y_all[:train_size]
    X_lstm_train = X_lstm_all[:train_size]

    logging.info(f"Aligned Test Set Size: {len(y_test)}")
    
    # 3. Load Models
    logging.info("Loading XGBoost model...")
    xgb_model = joblib.load('models/xgboost_model.pkl')
    
    logging.info("Loading LSTM model...")
    lstm_model = load_model('models/best_lstm_model.keras')
    
    # 4. Generate Predictions on Test Set
    logging.info("Generating predictions...")
    xgb_preds = xgb_model.predict(X_xgb_test)
    lstm_preds = lstm_model.predict(X_lstm_test).flatten()
    
    xgb_metrics = evaluate_predictions(y_test, xgb_preds, "XGBoost")
    lstm_metrics = evaluate_predictions(y_test, lstm_preds, "LSTM")
    
    # 5. Fusion Strategies
    logging.info("Testing Fusion Strategies...")
    
    fusion_avg_preds = 0.5 * xgb_preds + 0.5 * lstm_preds
    avg_metrics = evaluate_predictions(y_test, fusion_avg_preds, "Fusion (Simple Average)")
    
    w_xgb = 0.3
    w_lstm = 0.7
    fusion_weighted_preds = w_xgb * xgb_preds + w_lstm * lstm_preds
    weighted_metrics = evaluate_predictions(y_test, fusion_weighted_preds, f"Fusion (Weighted XGB:{w_xgb}/LSTM:{w_lstm})")
    
    from sklearn.linear_model import LinearRegression
    logging.info("Training Stacking model (Linear Regression)...")
    
    meta_train_size = int(len(y_train) * 0.8)
    X_xgb_val2 = X_xgb_train[meta_train_size:]
    X_lstm_val2 = X_lstm_train[meta_train_size:]
    y_val2 = y_train[meta_train_size:]
    
    xgb_val2_preds = xgb_model.predict(X_xgb_val2)
    lstm_val2_preds = lstm_model.predict(X_lstm_val2).flatten()
    
    meta_features_train = np.column_stack((xgb_val2_preds, lstm_val2_preds))
    meta_learner = LinearRegression()
    meta_learner.fit(meta_features_train, y_val2)
    
    logging.info(f"Stacking Meta-Learner Coefficients: XGB={meta_learner.coef_[0]:.4f}, LSTM={meta_learner.coef_[1]:.4f}, Intercept={meta_learner.intercept_:.4f}")
    
    meta_features_test = np.column_stack((xgb_preds, lstm_preds))
    fusion_stacking_preds = meta_learner.predict(meta_features_test)
    stacking_metrics = evaluate_predictions(y_test, fusion_stacking_preds, "Fusion (Linear Stacking)")
    
    # 6. Select Best Strategy and Save
    best_strategy = "Weighted Average (30/70)"
    best_metrics = weighted_metrics
    best_preds = fusion_weighted_preds
    
    if stacking_metrics['MAE'] < best_metrics['MAE']:
        best_strategy = "Linear Stacking"
        best_metrics = stacking_metrics
        best_preds = fusion_stacking_preds
        
    logging.info(f"Best Strategy selected: {best_strategy}")
    
    fusion_config = {
        "strategy": best_strategy,
        "base_models": {
            "xgboost": "models/xgboost_model.pkl",
            "lstm": "models/best_lstm_model.keras"
        },
        "performance": {
            "XGBoost": xgb_metrics,
            "LSTM": lstm_metrics,
            "Fusion_Simple_Avg": avg_metrics,
            "Fusion_Weighted": weighted_metrics,
            "Fusion_Stacking": stacking_metrics,
            "Best": best_metrics
        }
    }
    
    if best_strategy == "Linear Stacking":
        fusion_config["stacking_meta_learner"] = "models/meta_learner.pkl"
        joblib.dump(meta_learner, 'models/meta_learner.pkl')
    else:
        fusion_config["weights"] = {"xgb": w_xgb, "lstm": w_lstm}
        
    with open('models/fusion_metadata.json', 'w') as f:
        json.dump(fusion_config, f, indent=4)
        
    logging.info("=== Phase 5 Completed ===")

if __name__ == "__main__":
    os.makedirs('models', exist_ok=True)
    run_fusion()
