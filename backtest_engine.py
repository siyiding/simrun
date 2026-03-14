import os
import json
import logging
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from tensorflow.keras.models import load_model

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s')

class ModelPredictor:
    def __init__(self, models_dir='models'):
        self.models_dir = models_dir
        self.xgb_model = None
        self.lstm_model = None
        self.meta_learner = None
        self.fusion_config = None
        self.feature_cols = []
        self._load_models()
        
    def _load_models(self):
        logging.info("Loading models for backtesting...")
        
        with open(f'{self.models_dir}/fusion_metadata.json', 'r') as f:
            self.fusion_config = json.load(f)
            
        with open(f'{self.models_dir}/xgboost_metadata.json', 'r') as f:
            xgb_meta = json.load(f)
            self.feature_cols = xgb_meta.get('features_used', [])
            
        self.xgb_model = joblib.load(f'{self.models_dir}/xgboost_model.pkl')
        self.lstm_model = load_model(f'{self.models_dir}/best_lstm_model.keras')
        self.meta_learner = joblib.load(f'{self.models_dir}/meta_learner.pkl')
        
    def predict(self, df_window):
        seq_length = 20
        features = df_window[self.feature_cols].values
        xgb_input = features[-1].reshape(1, -1)
        lstm_input = features.reshape(1, seq_length, -1)
        xgb_pred = self.xgb_model.predict(xgb_input)[0]
        lstm_pred = self.lstm_model.predict(lstm_input, verbose=0).flatten()[0]
        meta_input = np.array([[xgb_pred, lstm_pred]])
        fusion_pred = self.meta_learner.predict(meta_input)[0]
        return fusion_pred

def compute_drawdown(cum_returns):
    rolling_max = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns - rolling_max) / rolling_max
    return drawdowns.min()

def run_backtest(data_dir="stock_features_parquet"):
    logging.info("=== Starting Phase 6: Backtest Engine ===")
    predictor = ModelPredictor()
    
    # Adjusted Config to trigger trades
    INITIAL_CAPITAL = 1000000.0
    TRANSACTION_FEE_RATE = 0.0003
    BUY_THRESHOLD = 0.01  # Lowered to 1% to generate trades
    SELL_THRESHOLD = -0.01 
    HOLDING_PERIOD = 5
    
    logging.info(f"Backtest Config: Capital={INITIAL_CAPITAL}, Fee={TRANSACTION_FEE_RATE}, BuyThreshold={BUY_THRESHOLD}")
    
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.parquet') and "features.parquet" in f]
    dfs = [pd.read_parquet(file) for file in files]
    data = pd.concat(dfs, ignore_index=True)
    
    date_col = 'date' if 'date' in data.columns else '日期'
    code_col = 'stock_code' if 'stock_code' in data.columns else '股票代码'
    
    data = data.sort_values(by=[code_col, date_col]).reset_index(drop=True)
    unique_dates = sorted(data[date_col].unique())
    test_dates_start = unique_dates[int(len(unique_dates) * 0.8)]
    test_dates = [d for d in unique_dates if d >= test_dates_start]
    
    capital = INITIAL_CAPITAL
    portfolio = {} 
    portfolio_history = []
    trade_records = []
    stock_groups = {code: group.set_index(date_col) for code, group in data.groupby(code_col)}
    
    for current_date in test_dates:
        daily_portfolio_value = capital
        stocks_to_sell = []
        for code, pos in list(portfolio.items()):
            pos['days_held'] += 1
            if code in stock_groups and current_date in stock_groups[code].index:
                current_price = stock_groups[code].loc[current_date, '收盘']
                daily_portfolio_value += pos['qty'] * current_price
                past_data = stock_groups[code].loc[:current_date]
                signal_exit = False
                if len(past_data) >= 20:
                    window = past_data.iloc[-20:]
                    pred_return = predictor.predict(window)
                    if pred_return < SELL_THRESHOLD:
                        signal_exit = True
                if pos['days_held'] >= HOLDING_PERIOD or signal_exit:
                    stocks_to_sell.append((code, current_price, "TIME_EXIT" if pos['days_held'] >= HOLDING_PERIOD else "SIGNAL_EXIT"))
            else:
                daily_portfolio_value += pos['qty'] * pos['buy_price']
                
        for code, price, reason in stocks_to_sell:
            pos = portfolio.pop(code)
            proceeds = pos['qty'] * price
            fee = proceeds * TRANSACTION_FEE_RATE
            net_proceeds = proceeds - fee
            capital += net_proceeds
            profit = net_proceeds - (pos['qty'] * pos['buy_price'])
            profit_pct = profit / (pos['qty'] * pos['buy_price'])
            trade_records.append({
                'date': current_date, 'stock': code, 'action': 'SELL',
                'reason': reason, 'price': price, 'qty': pos['qty'],
                'profit': profit, 'profit_pct': profit_pct
            })
            logging.debug(f"{current_date} SELL {code} @ {price:.2f} | Profit: {profit:.2f} ({profit_pct:.2%})")

        buy_candidates = []
        for code, group in stock_groups.items():
            if current_date in group.index and code not in portfolio:
                past_data = group.loc[:current_date]
                if len(past_data) >= 20:
                    window = past_data.iloc[-20:]
                    try:
                        pred_return = predictor.predict(window)
                        if pred_return > BUY_THRESHOLD:
                            buy_candidates.append({'code': code, 'pred': pred_return, 'price': group.loc[current_date, '收盘']})
                    except Exception as e:
                        pass
                        
        buy_candidates.sort(key=lambda x: x['pred'], reverse=True)
        available_slots = 5 - len(portfolio)
        
        for candidate in buy_candidates[:available_slots]:
            if capital < 10000: break
            code = candidate['code']
            price = candidate['price']
            allocation = capital / available_slots
            qty = int(allocation / price / 100) * 100
            
            if qty > 0:
                cost = qty * price
                fee = cost * TRANSACTION_FEE_RATE
                total_cost = cost + fee
                capital -= total_cost
                portfolio[code] = {'qty': qty, 'buy_price': price, 'days_held': 0}
                trade_records.append({
                    'date': current_date, 'stock': code, 'action': 'BUY',
                    'reason': f"PRED: {candidate['pred']:.4f}", 'price': price,
                    'qty': qty, 'profit': 0, 'profit_pct': 0
                })
                logging.debug(f"{current_date} BUY {code} @ {price:.2f} | Pred: {candidate['pred']:.2%}")
                
        portfolio_history.append({'date': current_date, 'value': daily_portfolio_value + (capital if len(portfolio)==0 else 0)})
            
    df_history = pd.DataFrame(portfolio_history)
    df_history['return'] = df_history['value'].pct_change()
    total_return = (df_history['value'].iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL
    drawdown = compute_drawdown(df_history['value'].values)
    
    daily_rf = 0.03 / 252
    sharpe_ratio = np.sqrt(252) * (df_history['return'].mean() - daily_rf) / df_history['return'].std() if df_history['return'].std() != 0 else 0.0
        
    df_trades = pd.DataFrame(trade_records)
    if len(df_trades) > 0:
        sells = df_trades[df_trades['action'] == 'SELL']
        winning_trades = len(sells[sells['profit'] > 0])
        total_trades = len(sells)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        avg_win = sells[sells['profit'] > 0]['profit'].mean() if winning_trades > 0 else 0.0
        avg_loss = abs(sells[sells['profit'] <= 0]['profit'].mean()) if (total_trades - winning_trades) > 0 else 1.0
        pl_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
    else:
        total_trades, winning_trades, win_rate, pl_ratio = 0, 0, 0.0, 0.0
    
    logging.info("=== Backtest Results ===")
    logging.info(f"Total Return: {total_return:.2%}")
    logging.info(f"Max Drawdown: {drawdown:.2%}")
    logging.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    logging.info(f"Win Rate:     {win_rate:.2%} ({winning_trades}/{total_trades})")
    logging.info(f"P/L Ratio:    {pl_ratio:.2f}")
    
    results = {
        "config": {
            "initial_capital": INITIAL_CAPITAL, "fee_rate": TRANSACTION_FEE_RATE,
            "buy_threshold": BUY_THRESHOLD, "sell_threshold": SELL_THRESHOLD, "holding_period": HOLDING_PERIOD
        },
        "metrics": {
            "total_return": total_return, "max_drawdown": drawdown,
            "sharpe_ratio": sharpe_ratio, "win_rate": win_rate, "pl_ratio": pl_ratio, "total_trades": total_trades
        }
    }
    
    with open('reports/backtest_metrics.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    if len(df_trades) > 0:
        df_trades.to_csv('reports/trade_records.csv', index=False)
    df_history.to_csv('reports/portfolio_curve.csv', index=False)
    
    logging.info("Phase 6 Backtest complete.")

if __name__ == "__main__":
    os.makedirs('reports', exist_ok=True)
    run_backtest()
