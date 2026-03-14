import os
import sys
import json
import subprocess
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

# Global task state to prevent duplicate runs
_task_running = False

# Worker Thread for running actual background processes
class ScriptWorkerThread(QThread):
    update_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, script_path, *args):
        super().__init__()
        self.script_path = script_path
        self.args = args

    def run(self):
        global _task_running
        _task_running = True
        try:
            self.update_signal.emit(f"正在执行脚本: {self.script_path}...")
            cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            process = subprocess.Popen(
                [sys.executable, self.script_path] + list(self.args),
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                self.update_signal.emit(line.strip())
                
            process.wait()
            if process.returncode == 0:
                self.finished_signal.emit(True, "执行成功！")
            else:
                self.finished_signal.emit(False, f"执行失败，退出码: {process.returncode}")
        except Exception as e:
            self.finished_signal.emit(False, str(e))
        finally:
            _task_running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimRun Quant - AI量化交易系统")
        self.resize(1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self._setup_data_tab()
        self._setup_training_tab()
        self._setup_backtest_tab()
        self._setup_results_tab()
        
        self.statusBar().showMessage("就绪。等待执行指令...")

    def check_task_running(self):
        global _task_running
        if _task_running:
            QMessageBox.warning(self, "警告", "当前有任务正在运行中，请等待结束后再启动新任务！")
            return True
        return False

    def validate_float(self, text, field_name):
        try:
            return float(text)
        except ValueError:
            QMessageBox.warning(self, "参数错误", f"'{field_name}' 必须是有效的数字！")
            return None

    def _setup_data_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        config_group = QGroupBox("第一步：数据源配置与下载")
        config_layout = QFormLayout()
        
        self.cb_data_source = QComboBox()
        self.cb_data_source.addItems(["本地离线数据优先 (复用避免重复下载)", "强制重新从Tushare/AKShare下载"])
        config_layout.addRow("数据获取策略:", self.cb_data_source)
        
        self.le_local_dir = QLineEdit("stock_data")
        config_layout.addRow("本地原始数据目录:", self.le_local_dir)
        
        self.le_feature_dir = QLineEdit("stock_features_parquet")
        config_layout.addRow("特征工程输出目录:", self.le_feature_dir)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        btn_layout = QHBoxLayout()
        self.btn_download = QPushButton("开始获取与清洗数据 (阶段1&2)")
        self.btn_download.clicked.connect(self.on_start_data)
        self.btn_download.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_download)
        layout.addLayout(btn_layout)
        
        self.data_log_output = QTextEdit()
        self.data_log_output.setReadOnly(True)
        layout.addWidget(QLabel("数据处理日志:"))
        layout.addWidget(self.data_log_output)
        
        self.tabs.addTab(tab, "📂 步骤1: 数据准备")

    def _setup_training_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        config_group = QGroupBox("第二步：模型训练配置")
        config_layout = QFormLayout()
        
        self.cb_model_type = QComboBox()
        self.cb_model_type.addItems(["XGBoost 截面模型 (阶段3)", "LSTM 时序模型 (阶段4)", "Stacking 融合模型 (阶段5)"])
        config_layout.addRow("选择训练目标:", self.cb_model_type)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        btn_layout = QHBoxLayout()
        self.btn_train = QPushButton("开始训练")
        self.btn_train.clicked.connect(self.on_start_training)
        self.btn_train.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_train)
        layout.addLayout(btn_layout)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("训练实时日志:"))
        layout.addWidget(self.log_output)
        
        self.tabs.addTab(tab, "⚙️ 步骤2: 模型训练")

    def _setup_backtest_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        config_group = QGroupBox("第三步：回测引擎参数配置 (阶段6)")
        config_layout = QFormLayout()
        
        self.le_capital = QLineEdit("1000000")
        config_layout.addRow("初始资金 (¥):", self.le_capital)
        
        self.le_fee = QLineEdit("0.0003")
        config_layout.addRow("交易手续费率:", self.le_fee)
        
        self.le_buy_th = QLineEdit("0.01")
        config_layout.addRow("预测买入阈值 (+%):", self.le_buy_th)
        
        self.le_sell_th = QLineEdit("-0.01")
        config_layout.addRow("预测卖出阈值 (-%):", self.le_sell_th)
        
        self.le_stop_loss = QLineEdit("-0.05")
        config_layout.addRow("硬止损红线 (-%):", self.le_stop_loss)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        btn_layout = QHBoxLayout()
        self.btn_run_bt = QPushButton("执行历史回测")
        self.btn_run_bt.clicked.connect(self.on_run_backtest)
        self.btn_run_bt.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_run_bt)
        layout.addLayout(btn_layout)
        
        self.bt_log_output = QTextEdit()
        self.bt_log_output.setReadOnly(True)
        layout.addWidget(QLabel("回测执行日志:"))
        layout.addWidget(self.bt_log_output)
        
        self.tabs.addTab(tab, "📈 步骤3: 执行回测")

    def _setup_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        top_layout = QHBoxLayout()
        self.btn_load_results = QPushButton("加载最新回测结果")
        self.btn_load_results.clicked.connect(self.load_results)
        top_layout.addWidget(self.btn_load_results)
        layout.addLayout(top_layout)
        
        splitter = QSplitter(Qt.Vertical)
        
        top_splitter = QSplitter(Qt.Horizontal)
        
        self.metrics_text = QTextEdit()
        self.metrics_text.setReadOnly(True)
        self.metrics_text.setStyleSheet("font-family: 'Microsoft YaHei', 'SimHei'; font-size: 14px;")
        top_splitter.addWidget(self.metrics_text)
        
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        top_splitter.addWidget(self.canvas)
        
        top_splitter.setSizes([300, 700])
        splitter.addWidget(top_splitter)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["交易日期", "股票代码", "交易动作", "触发原因", "成交价格", "成交数量", "盈亏金额", "盈亏比例"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.table)
        
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        self.tabs.addTab(tab, "📊 结果大屏")

    # --- Actions ---

    def append_log(self, widget, msg):
        widget.append(msg)
        widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())

    def on_start_data(self):
        if self.check_task_running(): return
        self.append_log(self.data_log_output, ">>> 开始执行数据准备任务...")
        self.btn_download.setEnabled(False)
        
        cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script = "data_fetcher.py" if self.cb_data_source.currentIndex() == 1 else "feature_engineering.py"
        
        self.data_worker = ScriptWorkerThread(script)
        self.data_worker.update_signal.connect(lambda msg: self.append_log(self.data_log_output, msg))
        self.data_worker.finished_signal.connect(self._on_data_finished)
        self.data_worker.start()
        
    def _on_data_finished(self, success, msg):
        self.btn_download.setEnabled(True)
        if success:
            self.append_log(self.data_log_output, "✅ 数据准备完毕，您可以前往【步骤2】进行模型训练。")
            QMessageBox.information(self, "成功", "数据拉取与特征工程已完成！")
        else:
            self.append_log(self.data_log_output, "❌ 错误: " + msg)
            QMessageBox.critical(self, "错误", "数据处理失败，详情请看日志。")

    def on_start_training(self):
        if self.check_task_running(): return
        task = self.cb_model_type.currentText()
        self.append_log(self.log_output, f">>> 正在启动任务: {task}")
        self.btn_train.setEnabled(False)
        
        if "XGBoost" in task:
            script = "xgboost_trainer.py"
        elif "LSTM" in task:
            script = "lstm_trainer.py"
        else:
            script = "model_fusion.py"
            
        self.train_worker = ScriptWorkerThread(script)
        self.train_worker.update_signal.connect(lambda msg: self.append_log(self.log_output, msg))
        self.train_worker.finished_signal.connect(self._on_training_finished)
        self.train_worker.start()

    def _on_training_finished(self, success, msg):
        self.btn_train.setEnabled(True)
        if success:
            self.append_log(self.log_output, "✅ " + msg)
            QMessageBox.information(self, "成功", "模型训练完成！")
        else:
            self.append_log(self.log_output, "❌ 错误: " + msg)
            QMessageBox.critical(self, "错误", "训练过程中发生错误，详情请看日志。")

    def on_run_backtest(self):
        # Validate inputs
        if self.validate_float(self.le_capital.text(), "初始资金") is None: return
        if self.validate_float(self.le_fee.text(), "交易手续费率") is None: return
        if self.validate_float(self.le_buy_th.text(), "预测买入阈值") is None: return
        if self.validate_float(self.le_sell_th.text(), "预测卖出阈值") is None: return
        if self.validate_float(self.le_stop_loss.text(), "硬止损红线") is None: return

        if self.check_task_running(): return
        
        self.append_log(self.bt_log_output, ">>> 正在启动回测引擎 (加载风控拦截与硬止损规则)...")
        self.btn_run_bt.setEnabled(False)
        
        self.bt_worker = ScriptWorkerThread("backtest_engine.py")
        self.bt_worker.update_signal.connect(lambda msg: self.append_log(self.bt_log_output, msg))
        self.bt_worker.finished_signal.connect(self._on_bt_finished)
        self.bt_worker.start()

    def _on_bt_finished(self, success, msg):
        self.btn_run_bt.setEnabled(True)
        if success:
            self.append_log(self.bt_log_output, "✅ 回测执行完毕！请前往【结果大屏】查看详细报告。")
            QMessageBox.information(self, "成功", "历史数据回测完成，绩效报告已生成。")
            self.tabs.setCurrentIndex(3)
            self.load_results()
        else:
            self.append_log(self.bt_log_output, "❌ 错误: " + msg)

    def load_results(self):
        reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
        metrics_file = os.path.join(reports_dir, "backtest_metrics.json")
        curve_file = os.path.join(reports_dir, "portfolio_curve.csv")
        trades_file = os.path.join(reports_dir, "trade_records.csv")
        
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            
            m = metrics.get('metrics', {})
            display_text = f"=== 核心绩效指标 ===\n\n"
            display_text += f"总收益率 (Total Return):  {m.get('total_return', 0)*100:.2f}%\n"
            display_text += f"最大回撤 (Max Drawdown):  {m.get('max_drawdown', 0)*100:.2f}%\n"
            display_text += f"夏普比率 (Sharpe Ratio):  {m.get('sharpe_ratio', 0):.2f}\n"
            display_text += f"交易胜率 (Win Rate):      {m.get('win_rate', 0)*100:.2f}%\n"
            display_text += f"盈亏比 (P/L Ratio):       {m.get('pl_ratio', 0):.2f}\n"
            display_text += f"总交易笔数 (Total Trades): {m.get('total_trades', 0)}\n"
            
            self.metrics_text.setPlainText(display_text)
        else:
            self.metrics_text.setPlainText("未找到回测指标文件，请先执行步骤3进行回测。")

        if os.path.exists(curve_file):
            df = pd.read_csv(curve_file)
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            if 'date' in df.columns and 'value' in df.columns:
                ax.plot(pd.to_datetime(df['date']), df['value'], color='#d62728', linewidth=1.5)
                matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
                matplotlib.rcParams['axes.unicode_minus'] = False
                ax.set_title("模拟资金净值走势曲线")
                ax.set_ylabel("账户总资金 (元)")
                ax.grid(True, linestyle='--', alpha=0.6)
                self.figure.autofmt_xdate()
                self.canvas.draw()

        if os.path.exists(trades_file):
            df_trades = pd.read_csv(trades_file)
            self.table.setRowCount(len(df_trades))
            for row in range(len(df_trades)):
                self.table.setItem(row, 0, QTableWidgetItem(str(df_trades.iloc[row].get('date', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(str(df_trades.iloc[row].get('stock', ''))))
                action = str(df_trades.iloc[row].get('action', ''))
                
                action_zh = "买入" if action == "BUY" else "卖出"
                item_action = QTableWidgetItem(action_zh)
                if action == "BUY":
                    item_action.setForeground(Qt.red) 
                else:
                    item_action.setForeground(Qt.darkGreen)
                self.table.setItem(row, 2, item_action)
                
                reason_map = {"HARD_STOP_LOSS": "-5%硬止损触发", "MARKET_RISK_EXIT": "大盘MA20破位避险", "TIME_EXIT": "周期到期退出", "SIGNAL_EXIT": "预测转跌信号退出"}
                raw_reason = str(df_trades.iloc[row].get('reason', ''))
                reason_zh = reason_map.get(raw_reason, raw_reason)
                
                self.table.setItem(row, 3, QTableWidgetItem(reason_zh))
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
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
