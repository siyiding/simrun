import os
import sys
import json
import pandas as pd
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QTabWidget, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QFormLayout, 
                               QLineEdit, QComboBox, QGroupBox, QSplitter,
                               QTextEdit, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Mock Worker Thread for running background processes without freezing UI
class WorkerThread(QThread):
    update_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, command_func, *args, **kwargs):
        super().__init__()
        self.command_func = command_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.update_signal.emit(f"Running task...")
            # Execute the actual logic (could be calling sub-scripts or imported functions)
            result = self.command_func(*self.args, **self.kwargs)
            self.finished_signal.emit(True, "Task completed successfully!")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimRun Quant - XGBoost+LSTM AI Trading")
        self.resize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Setup Tabs
        self._setup_training_tab()
        self._setup_backtest_tab()
        self._setup_results_tab()
        
        # Status Bar
        self.statusBar().showMessage("Ready. System waiting for commands.")

    def _setup_training_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Config Group
        config_group = QGroupBox("Model Training Configuration")
        config_layout = QFormLayout()
        
        self.cb_model_type = QComboBox()
        self.cb_model_type.addItems(["XGBoost (Phase 3)", "LSTM (Phase 4)", "Model Fusion (Phase 5)"])
        config_layout.addRow("Select Model Task:", self.cb_model_type)
        
        self.le_data_dir = QLineEdit("stock_features_parquet")
        config_layout.addRow("Data Directory:", self.le_data_dir)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Action Group
        btn_layout = QHBoxLayout()
        self.btn_train = QPushButton("Start Training")
        self.btn_train.clicked.connect(self.on_start_training)
        self.btn_train.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_train)
        layout.addLayout(btn_layout)
        
        # Log Output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("Training Logs:"))
        layout.addWidget(self.log_output)
        
        self.tabs.addTab(tab, "⚙️ Model Training")

    def _setup_backtest_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        config_group = QGroupBox("Backtest Engine Settings (Phase 6)")
        config_layout = QFormLayout()
        
        self.le_capital = QLineEdit("1000000")
        config_layout.addRow("Initial Capital (¥):", self.le_capital)
        
        self.le_fee = QLineEdit("0.0003")
        config_layout.addRow("Transaction Fee Rate:", self.le_fee)
        
        self.le_buy_th = QLineEdit("0.01")
        config_layout.addRow("Buy Threshold (+%):", self.le_buy_th)
        
        self.le_sell_th = QLineEdit("-0.01")
        config_layout.addRow("Sell Threshold (-%):", self.le_sell_th)
        
        self.le_stop_loss = QLineEdit("-0.05")
        config_layout.addRow("Hard Stop Loss (-%):", self.le_stop_loss)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Action Group
        btn_layout = QHBoxLayout()
        self.btn_run_bt = QPushButton("Run Backtest")
        self.btn_run_bt.clicked.connect(self.on_run_backtest)
        self.btn_run_bt.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_run_bt)
        layout.addLayout(btn_layout)
        
        self.bt_log_output = QTextEdit()
        self.bt_log_output.setReadOnly(True)
        layout.addWidget(QLabel("Backtest Logs:"))
        layout.addWidget(self.bt_log_output)
        
        self.tabs.addTab(tab, "📈 Run Backtest")

    def _setup_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        top_layout = QHBoxLayout()
        self.btn_load_results = QPushButton("Load Latest Results")
        self.btn_load_results.clicked.connect(self.load_results)
        top_layout.addWidget(self.btn_load_results)
        layout.addLayout(top_layout)
        
        splitter = QSplitter(Qt.Vertical)
        
        # Top half: Metrics & Chart
        top_splitter = QSplitter(Qt.Horizontal)
        
        # Metrics Panel
        self.metrics_text = QTextEdit()
        self.metrics_text.setReadOnly(True)
        top_splitter.addWidget(self.metrics_text)
        
        # Chart Panel
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        top_splitter.addWidget(self.canvas)
        
        top_splitter.setSizes([300, 700])
        splitter.addWidget(top_splitter)
        
        # Bottom half: Trade Records Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Date", "Stock", "Action", "Reason", "Price", "Qty", "Profit", "Profit %"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.table)
        
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        self.tabs.addTab(tab, "📊 Results & Analytics")

    # --- Actions ---

    def append_log(self, widget, msg):
        widget.append(msg)
        widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())

    def on_start_training(self):
        task = self.cb_model_type.currentText()
        self.append_log(self.log_output, f">>> Initiating Task: {task}")
        self.btn_train.setEnabled(False)
        
        # In a real app, we would import the module and run it in the worker thread.
        # Here we mock the delay for demonstration.
        def mock_train():
            import time
            time.sleep(2)
            if "XGBoost" in task:
                os.system("python3 xgboost_trainer.py" if os.path.exists("xgboost_trainer.py") else "echo 'Mock XGBoost Training Done'")
            elif "LSTM" in task:
                os.system("python3 lstm_trainer.py" if os.path.exists("lstm_trainer.py") else "echo 'Mock LSTM Training Done'")
            elif "Fusion" in task:
                os.system("python3 model_fusion.py" if os.path.exists("model_fusion.py") else "echo 'Mock Fusion Done'")
                
        self.worker = WorkerThread(mock_train)
        self.worker.update_signal.connect(lambda msg: self.append_log(self.log_output, msg))
        self.worker.finished_signal.connect(self._on_training_finished)
        self.worker.start()

    def _on_training_finished(self, success, msg):
        self.btn_train.setEnabled(True)
        if success:
            self.append_log(self.log_output, "✅ " + msg)
            QMessageBox.information(self, "Success", "Training execution completed!")
        else:
            self.append_log(self.log_output, "❌ Error: " + msg)
            QMessageBox.critical(self, "Error", msg)

    def on_run_backtest(self):
        self.append_log(self.bt_log_output, ">>> Starting Backtest Engine...")
        self.btn_run_bt.setEnabled(False)
        
        def mock_bt():
            import time
            time.sleep(2)
            # Just calls the existing script
            os.system("python3 backtest_engine.py" if os.path.exists("backtest_engine.py") else "echo 'Mock BT Done'")
            
        self.worker_bt = WorkerThread(mock_bt)
        self.worker_bt.update_signal.connect(lambda msg: self.append_log(self.bt_log_output, msg))
        self.worker_bt.finished_signal.connect(self._on_bt_finished)
        self.worker_bt.start()

    def _on_bt_finished(self, success, msg):
        self.btn_run_bt.setEnabled(True)
        if success:
            self.append_log(self.bt_log_output, "✅ Backtest completed! Go to Results tab.")
            QMessageBox.information(self, "Success", "Backtest finished. Artifacts saved.")
            self.tabs.setCurrentIndex(2)
            self.load_results()
        else:
            self.append_log(self.bt_log_output, "❌ Error: " + msg)

    def load_results(self):
        reports_dir = "reports"
        metrics_file = os.path.join(reports_dir, "backtest_metrics.json")
        curve_file = os.path.join(reports_dir, "portfolio_curve.csv")
        trades_file = os.path.join(reports_dir, "trade_records.csv")
        
        # Load Metrics
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            
            m = metrics.get('metrics', {})
            display_text = f"=== Performance Metrics ===\n\n"
            display_text += f"Total Return:  {m.get('total_return', 0)*100:.2f}%\n"
            display_text += f"Max Drawdown:  {m.get('max_drawdown', 0)*100:.2f}%\n"
            display_text += f"Sharpe Ratio:  {m.get('sharpe_ratio', 0):.2f}\n"
            display_text += f"Win Rate:      {m.get('win_rate', 0)*100:.2f}%\n"
            display_text += f"P/L Ratio:     {m.get('pl_ratio', 0):.2f}\n"
            display_text += f"Total Trades:  {m.get('total_trades', 0)}\n"
            
            self.metrics_text.setPlainText(display_text)
        else:
            self.metrics_text.setPlainText("No metrics file found. Run backtest first.")

        # Load Curve
        if os.path.exists(curve_file):
            df = pd.read_csv(curve_file)
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            # Assuming 'date' and 'value' columns
            if 'date' in df.columns and 'value' in df.columns:
                ax.plot(pd.to_datetime(df['date']), df['value'], color='blue', linewidth=1.5)
                ax.set_title("Portfolio Equity Curve")
                ax.set_ylabel("Capital (¥)")
                ax.grid(True, linestyle='--', alpha=0.6)
                self.figure.autofmt_xdate()
                self.canvas.draw()

        # Load Trades
        if os.path.exists(trades_file):
            df_trades = pd.read_csv(trades_file)
            self.table.setRowCount(len(df_trades))
            for row in range(len(df_trades)):
                self.table.setItem(row, 0, QTableWidgetItem(str(df_trades.iloc[row].get('date', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(str(df_trades.iloc[row].get('stock', ''))))
                action = str(df_trades.iloc[row].get('action', ''))
                item_action = QTableWidgetItem(action)
                if action == "BUY":
                    item_action.setForeground(Qt.red) # Red for buy in CN market context, or green
                else:
                    item_action.setForeground(Qt.darkGreen)
                self.table.setItem(row, 2, item_action)
                self.table.setItem(row, 3, QTableWidgetItem(str(df_trades.iloc[row].get('reason', ''))))
                self.table.setItem(row, 4, QTableWidgetItem(f"{df_trades.iloc[row].get('price', 0):.2f}"))
                self.table.setItem(row, 5, QTableWidgetItem(str(df_trades.iloc[row].get('qty', 0))))
                
                profit = df_trades.iloc[row].get('profit', 0)
                item_profit = QTableWidgetItem(f"{profit:.2f}")
                if profit > 0: item_profit.setForeground(Qt.red)
                elif profit < 0: item_profit.setForeground(Qt.darkGreen)
                self.table.setItem(row, 6, item_profit)
                
                profit_pct = df_trades.iloc[row].get('profit_pct', 0) * 100
                item_pct = QTableWidgetItem(f"{profit_pct:.2f}%")
                if profit_pct > 0: item_pct.setForeground(Qt.red)
                elif profit_pct < 0: item_pct.setForeground(Qt.darkGreen)
                self.table.setItem(row, 7, item_pct)
        else:
            self.table.setRowCount(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set modern style
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
