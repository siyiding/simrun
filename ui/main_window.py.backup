import re
import os
import sys
import json
import subprocess
import datetime
import shutil
import pandas as pd
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QTabWidget, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QFormLayout, 
                               QLineEdit, QComboBox, QGroupBox, QSplitter,
                               QTextEdit, QMessageBox, QProgressBar, QApplication,
                               QDialog, QDialogButtonBox, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import time
from datetime import datetime

# Import data fetcher
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data_fetcher import DataFetcher

# Global task state to prevent duplicate runs
_task_running = False


class DownloadWorkerThread(QThread):
    """后台下载线程"""
    log_signal = Signal(str, str)  # 日志内容, 日志级别 (info/warning/error)
    progress_signal = Signal(int, str)  # 进度百分比, 当前股票名称
    finished_signal = Signal(bool, str, list)  # 是否成功, 消息, 失败股票列表
    cancelled = False
    
    def __init__(self, full=True, data_dir=None):
        super().__init__()
        self.full = full
        self.data_dir = data_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stock_data"))
        self.failed_stocks = []
        
    def run(self):
        """执行下载"""
        try:
            self.log_signal.emit(">>> 初始化下载任务...", "info")
            self.log_signal.emit(f">>> 数据目录: {self.data_dir}", "info")
            
            # 创建数据获取器
            fetcher = DataFetcher(data_dir=self.data_dir, use_parquet=True)
            
            # 获取股票池
            self.log_signal.emit(">>> 正在获取股票列表...", "info")
            stock_pool = fetcher.get_stock_pool()
            
            if not stock_pool:
                self.log_signal.emit(">>> 获取股票列表失败", "error")
                self.finished_signal.emit(False, "获取股票列表失败", [])
                return
            
            self.log_signal.emit(f">>> 已获取 {len(stock_pool)} 只股票", "info")
            
            # 为了演示，先下载前20只股票（可配置）
            download_count = min(20, len(stock_pool))
            stocks_to_download = stock_pool[:download_count]
            
            self.log_signal.emit(f">>> 开始下载数据 (全量模式: {self.full})", "info")
            
            success_count = 0
            for idx, code in enumerate(stocks_to_download):
                if self.cancelled:
                    self.log_signal.emit(">>> 用户取消下载", "warning")
                    break
                
                try:
                    progress = int((idx + 1) / len(stocks_to_download) * 100)
                    self.progress_signal.emit(progress, code)
                    self.log_signal.emit(f">>> [{idx+1}/{len(stocks_to_download)}] 正在下载: {code}", "info")
                    
                    # 获取数据
                    df = fetcher.fetch_daily_data(code, start_date="20230101")
                    
                    if df is not None and not df.empty:
                        fetcher.save_data(df, code)
                        self.log_signal.emit(f">>> [{idx+1}/{len(stocks_to_download)}] 下载成功: {code}", "info")
                        success_count += 1
                    else:
                        self.log_signal.emit(f">>> [{idx+1}/{len(stocks_to_download)}] 无数据: {code}", "warning")
                        self.failed_stocks.append(code)
                    
                    # 防止被封IP
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.log_signal.emit(f">>> [{idx+1}/{len(stocks_to_download)}] 下载失败: {code} - {str(e)}", "error")
                    self.failed_stocks.append(code)
            
            fetcher.close()
            
            # 发送完成信号
            if self.cancelled:
                self.finished_signal.emit(True, f"已取消下载 ({success_count}/{len(stocks_to_download)}) 成功", self.failed_stocks)
            elif self.failed_stocks:
                self.finished_signal.emit(True, f"下载完成: {success_count} 成功, {len(self.failed_stocks)} 失败", self.failed_stocks)
            else:
                self.finished_signal.emit(True, f"下载完成: {success_count} 成功", [])
                
        except Exception as e:
            self.log_signal.emit(f">>> 下载异常: {str(e)}", "error")
            self.finished_signal.emit(False, f"下载异常: {str(e)}", [])
    
    def cancel(self):
        """取消下载"""
        self.cancelled = True

class DataManagerDialog(QDialog):
    """数据管理弹窗对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("🎯 数据管理")
        self.setFixedSize(480, 600)
        self.setModal(True)
        self._apply_theme()
        
        # 数据状态
        self.data_status = "已就绪"  # 已就绪/下载中/警告/错误
        self.stock_count = 0
        self.date_range = "无数据"
        self.storage_size = "0 MB"
        self.last_update = "从未"
        self.error_stocks = []
        self.download_progress = 0
        self.current_stock = ""
        
        self._init_ui()
        self._load_data_info()
    
    def _apply_theme(self):
        """应用深海蓝主题"""
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
            }
            QPushButton {
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
            }
            QPushButton:hover {
                brightness: 110%;
            }
            QProgressBar {
                border: 2px solid #333333;
                border-radius: 4px;
                text-align: center;
                background-color: #333333;
                color: #FFFFFF;
                font-weight: 600;
            }
            QProgressBar::chunk {
                border-radius: 2px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2196F3, stop:1 #4CAF50);
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#card {
                background-color: #1E1E1E;
                border-radius: 8px;
                padding: 12px;
            }
        """)
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # ===== 标题栏 =====
        title_layout = QHBoxLayout()
        title_label = QLabel("🎯 数据管理")
        title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1A237E;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #B0B0B0;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: #333333;
                border-radius: 15px;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        layout.addLayout(title_layout)
        
        # ===== 状态区 =====
        status_card = self._create_card()
        status_layout = QVBoxLayout(status_card)
        
        self.status_label = QLabel("🟢 已就绪")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        status_layout.addWidget(self.status_label)
        
        self.last_update_label = QLabel("最后更新: 从未")
        self.last_update_label.setStyleSheet("color: #B0B0B0; font-size: 13px;")
        status_layout.addWidget(self.last_update_label)
        
        layout.addWidget(status_card)
        
        # ===== 核心数据区 =====
        data_card = self._create_card()
        data_layout = QVBoxLayout(data_card)
        
        self.stock_count_label = QLabel("📈 股票数量: 0只")
        self.stock_count_label.setStyleSheet("font-size: 14px;")
        data_layout.addWidget(self.stock_count_label)
        
        self.date_range_label = QLabel("📅 时间范围: 无数据")
        self.date_range_label.setStyleSheet("font-size: 14px;")
        data_layout.addWidget(self.date_range_label)
        
        self.storage_size_label = QLabel("💾 存储大小: 0 MB")
        self.storage_size_label.setStyleSheet("font-size: 14px;")
        data_layout.addWidget(self.storage_size_label)
        
        layout.addWidget(data_card)
        
        # ===== 下载进度区 =====
        progress_card = self._create_card()
        progress_layout = QVBoxLayout(progress_card)
        
        progress_text_layout = QHBoxLayout()
        progress_text_layout.addWidget(QLabel("下载进度:"))
        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet("color: #2196F3; font-weight: 600;")
        progress_text_layout.addWidget(self.progress_label)
        progress_text_layout.addStretch()
        progress_layout.addLayout(progress_text_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        progress_layout.addWidget(self.progress_bar)
        
        self.current_stock_label = QLabel("等待中...")
        self.current_stock_label.setStyleSheet("color: #B0B0B0; font-size: 12px;")
        progress_layout.addWidget(self.current_stock_label)
        
        layout.addWidget(progress_card)
        
        # ===== 日志输出区 =====
        log_card = self._create_card()
        log_layout = QVBoxLayout(log_card)
        
        log_header = QLabel("▼ 📜 下载日志")
        log_header.setStyleSheet("color: #B0B0B0; font-size: 13px; font-weight: 600;")
        log_layout.addWidget(log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(120)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0D0D0D;
                color: #FFFFFF;
                font-family: Consolas, monospace;
                font-size: 11px;
                border: 1px solid #333333;
                border-radius: 4px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_card)
        
        # ===== 异常记录区 =====
        self.error_card = self._create_card()
        error_layout = QVBoxLayout(self.error_card)
        
        self.error_header = QPushButton("⚠️ 异常股票 (0只) ▼")
        self.error_header.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FF9800;
                text-align: left;
                border: none;
                padding: 0;
                font-weight: 600;
            }
        """)
        self.error_header.clicked.connect(self._toggle_error_list)
        error_layout.addWidget(self.error_header)
        
        self.error_list_widget = QWidget()
        self.error_list_layout = QVBoxLayout(self.error_list_widget)
        self.error_list_widget.setVisible(False)
        error_layout.addWidget(self.error_list_widget)
        
        layout.addWidget(self.error_card)
        
        # ===== 操作按钮区 =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_full_download = QPushButton("全量下载")
        self.btn_full_download.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #FFFFFF;
            }
            QPushButton:hover { background-color: #66BB6A; }
            QPushButton:disabled { background-color: #757575; }
        """)
        self.btn_full_download.clicked.connect(self._on_full_download)
        btn_layout.addWidget(self.btn_full_download)
        
        self.btn_incremental = QPushButton("增量更新")
        self.btn_incremental.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #FFFFFF;
            }
            QPushButton:hover { background-color: #42A5F5; }
            QPushButton:disabled { background-color: #757575; }
        """)
        self.btn_incremental.clicked.connect(self._on_incremental_update)
        btn_layout.addWidget(self.btn_incremental)
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: #FFFFFF;
            }
            QPushButton:hover { background-color: #9E9E9E; }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_clear_cache = QPushButton("清除缓存")
        self.btn_clear_cache.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: #FFFFFF;
            }
            QPushButton:hover { background-color: #EF5350; }
        """)
        self.btn_clear_cache.clicked.connect(self._on_clear_cache)
        btn_layout.addWidget(self.btn_clear_cache)
        
        layout.addLayout(btn_layout)
    
    def _create_card(self):
        """创建卡片容器"""
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet("""
            QWidget#card {
                background-color: #1E1E1E;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        return card
    
    def _load_data_info(self):
        """加载本地数据信息"""
        try:
            # 获取数据目录
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stock_data"))
            feature_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stock_features_parquet"))
            
            # 检查数据目录
            if os.path.exists(data_dir):
                # 统计股票数量
                files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
                self.stock_count = len(files)
                
                # 计算存储大小
                total_size = 0
                for root, dirs, files in os.walk(data_dir):
                    for f in files:
                        total_size += os.path.getsize(os.path.join(root, f))
                if os.path.exists(feature_dir):
                    for root, dirs, files in os.walk(feature_dir):
                        for f in files:
                            total_size += os.path.getsize(os.path.join(root, f))
                
                self.storage_size = self._format_size(total_size)
                
                # 获取时间范围和最后更新时间
                dates = set()
                latest_mtime = 0
                for f in files:
                    filepath = os.path.join(data_dir, f)
                    mtime = os.path.getmtime(filepath)
                    latest_mtime = max(latest_mtime, mtime)
                    # 从文件名提取日期
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', f)
                    if match:
                        dates.add(match.group(1))
                
                if dates:
                    sorted_dates = sorted(dates)
                    self.date_range = f"{sorted_dates[0]} ~ {sorted_dates[-1]}"
                
                if latest_mtime > 0:
                    self.last_update = datetime.datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M")
                
                # 更新UI
                self._update_display()
                self._set_status("已就绪")
            else:
                self._set_status("警告")
                self.status_label.setText("⚠️ 数据未找到")
        except Exception as e:
            self._set_status("错误")
            self.status_label.setText(f"❌ 加载失败: {str(e)}")
    
    def _format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _update_display(self):
        """更新数据显示"""
        self.stock_count_label.setText(f"📈 股票数量: {self.stock_count}只")
        self.date_range_label.setText(f"📅 时间范围: {self.date_range}")
        self.storage_size_label.setText(f"💾 存储大小: {self.storage_size}")
        self.last_update_label.setText(f"最后更新: {self.last_update}")
    
    def _set_status(self, status):
        """设置状态标签"""
        self.data_status = status
        status_config = {
            "已就绪": ("🟢 已就绪", "#4CAF50"),
            "下载中": ("⏳ 下载中", "#2196F3"),
            "警告": ("⚠️ 警告", "#FF9800"),
            "错误": ("❌ 错误", "#F44336")
        }
        text, color = status_config.get(status, ("🟢 已就绪", "#4CAF50"))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {color};")
    
    def _toggle_error_list(self):
        """切换异常列表显示"""
        is_visible = self.error_list_widget.isVisible()
        self.error_list_widget.setVisible(not is_visible)
        arrow = "▲" if not is_visible else "▼"
        self.error_header.setText(f"⚠️ 异常股票 ({len(self.error_stocks)}只) {arrow}")
    
    def _update_error_list(self):
        """更新异常股票列表显示"""
        # 清除旧内容
        while self.error_list_layout.count():
            item = self.error_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加新的失败股票
        if self.error_stocks:
            for stock in self.error_stocks[:10]:  # 最多显示10个
                label = QLabel(f"• {stock}")
                label.setStyleSheet("color: #FF9800; font-size: 12px;")
                self.error_list_layout.addWidget(label)
            
            if len(self.error_stocks) > 10:
                more_label = QLabel(f"... 等共 {len(self.error_stocks)} 只")
                more_label.setStyleSheet("color: #B0B0B0; font-size: 11px;")
                self.error_list_layout.addWidget(more_label)
        else:
            no_error_label = QLabel("无异常")
            no_error_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
            self.error_list_layout.addWidget(no_error_label)
    
    def _update_progress(self, progress, current_stock=""):
        """更新下载进度"""
        self.download_progress = progress
        self.current_stock = current_stock
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"{progress}%")
        if current_stock:
            self.current_stock_label.setText(f"正在获取: {current_stock}")
    
    def _on_full_download(self):
        """全量下载"""
        reply = QMessageBox.question(
            self, "确认全量下载",
            "全量下载将重新下载所有数据，确定继续吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._start_download(full=True)
    
    def _on_incremental_update(self):
        """增量更新"""
        # 检查本地数据
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stock_data"))
        if not os.path.exists(data_dir) or self.stock_count == 0:
            QMessageBox.information(self, "提示", "本地暂无数据，将执行全量下载。")
            self._start_download(full=True)
            return
        
        # 计算缺失日期
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if self.date_range != "无数据":
            end_date = self.date_range.split(" ~ ")[-1]
            if end_date < today:
                missing_days = (datetime.datetime.strptime(today, "%Y-%m-%d") - 
                              datetime.datetime.strptime(end_date, "%Y-%m-%d")).days
                
                msg = f"本地数据至 {end_date}\n将补充 {end_date} ~ {today} 共{missing_days}天数据"
                reply = QMessageBox.question(
                    self, "确认增量更新", msg,
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._start_download(full=False)
            else:
                QMessageBox.information(self, "提示", "数据已是最新，无需更新。")
        else:
            QMessageBox.information(self, "提示", "本地暂无数据，将执行全量下载。")
            self._start_download(full=True)
    
    def _start_download(self, full=True):
        """开始下载"""
        self._set_status("下载中")
        self.btn_full_download.setEnabled(False)
        self.btn_incremental.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        
        # 清空日志
        self.log_text.clear()
        
        # 获取数据目录
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stock_data"))
        
        # 创建并启动下载线程
        self.download_worker = DownloadWorkerThread(full=full, data_dir=data_dir)
        self.download_worker.log_signal.connect(self._append_log)
        self.download_worker.progress_signal.connect(self._update_progress)
        self.download_worker.finished_signal.connect(self._on_download_complete)
        self.download_worker.start()
    
    def _append_log(self, message, level="info"):
        """追加日志到日志区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        # 设置颜色
        color = "#FFFFFF"  # 默认白色
        if level == "warning":
            color = "#FFB300"  # 黄色
        elif level == "error":
            color = "#F44336"  # 红色
        
        # 追加文本
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertHtml(f'<span style="color: {color};">{formatted_msg}</span><br>')
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
    
    def _on_download_complete(self, success, message, failed_stocks):
        """下载完成"""
        self._set_status("已就绪")
        self.btn_full_download.setEnabled(True)
        self.btn_incremental.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        
        # 更新失败股票列表
        self.error_stocks = failed_stocks
        self._update_error_list()
        
        # 更新错误区标题
        self.error_header.setText(f"⚠️ 异常股票 ({len(failed_stocks)}只) ▼")
        
        # 重新加载数据信息
        self._load_data_info()
        
        # 显示完成消息
        if failed_stocks:
            self._set_status("警告")
            self.log_signal.emit(f">>> 部分失败: {len(failed_stocks)} 只股票", "warning")
            QMessageBox.warning(self, "部分完成", message)
        else:
            self._update_progress(100, "下载完成")
            self.log_signal.emit(">>> 下载任务完成", "info")
            QMessageBox.information(self, "完成", message)
    
    def _on_cancel(self):
        """取消下载"""
        if hasattr(self, 'download_worker') and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.download_worker.wait()
        self._set_status("已就绪")
        self.btn_full_download.setEnabled(True)
        self.btn_incremental.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self._update_progress(0, "已取消")
        self.log_signal.emit(">>> 下载已取消", "warning")
    
    def _on_clear_cache(self):
        """清除缓存"""
        reply = QMessageBox.question(
            self, "确认清除缓存",
            "确定要清除所有本地数据吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stock_data"))
                feature_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stock_features_parquet"))
                
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir)
                if os.path.exists(feature_dir):
                    shutil.rmtree(feature_dir)
                
                self.stock_count = 0
                self.date_range = "无数据"
                self.storage_size = "0 MB"
                self.last_update = "从未"
                self._update_display()
                self._set_status("警告")
                
                QMessageBox.information(self, "完成", "缓存已清除！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清除缓存失败: {str(e)}")


# Worker Thread for running actual background processes
class ScriptWorkerThread(QThread):
    update_signal = Signal(str)
    progress_signal = Signal(int)
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
            
            import re
            tqdm_pattern = re.compile(r'\s*(\d{1,3})%\|')
            
            for line in process.stdout:
                line_stripped = line.strip()
                if line_stripped:
                    match = tqdm_pattern.search(line_stripped)
                    if match:
                        try:
                            self.progress_signal.emit(int(match.group(1)))
                        except:
                            pass
                    else:
                        self.update_signal.emit(line_stripped)
                
            process.wait()
            self.progress_signal.emit(100)
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
        
        # 应用深海蓝主题样式
        self._apply_ocean_blue_theme()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self._setup_status_bar_custom()
        self._setup_data_tab()
        self._setup_training_tab()
        self._setup_backtest_tab()
        self._setup_results_tab()
        
        # 自定义状态栏
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1A73E8;
                color: white;
                padding: 8px;
                font-weight: 600;
            }
        """)
        self.statusBar().showMessage("✅ 系统就绪 | 📊 模型未加载 | 💰 账户: ¥1,000,000")

    def _apply_ocean_blue_theme(self):
        """应用深海蓝主题样式"""
        theme_style = """
        /* 全局字体设置 */
        QWidget {
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            font-size: 14px;
            color: #202124;
        }
        
        /* 主窗口背景 */
        QMainWindow {
            background-color: #F8F9FA;
        }
        
        /* 标签页容器 */
        QTabWidget::pane {
            border: 1px solid #E8EAED;
            border-radius: 8px;
            background-color: white;
        }
        
        /* 标签页头部 */
        QTabBar::tab {
            background-color: #F8F9FA;
            padding: 12px 20px;
            margin-right: 4px;
            border-radius: 8px 8px 0 0;
            color: #5F6368;
            font-weight: 500;
        }
        
        QTabBar::tab:hover {
            background-color: #E8EAED;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            color: #1A73E8;
            font-weight: 600;
            border-bottom: 3px solid #1A73E8;
        }
        
        /* 卡片容器 - QGroupBox */
        QGroupBox {
            border: 1px solid #E8EAED;
            border-radius: 12px;
            margin-top: 16px;
            padding: 16px;
            background-color: white;
            font-weight: 600;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 16px;
            padding: 4px 12px;
            background-color: #F8F9FA;
            border-radius: 4px;
            color: #1A73E8;
        }
        
        /* 主要按钮 - 圆角 + 深海蓝 */
        QPushButton {
            background-color: #1A73E8;
            color: white;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            border: none;
        }
        
        QPushButton:hover {
            background-color: #1557B0;
        }
        
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        
        QPushButton:disabled {
            background-color: #BDBDBD;
            color: #757575;
        }
        
        /* 进度条 - 渐变效果 */
        QProgressBar {
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            text-align: center;
            background-color: #F5F5F5;
            height: 24px;
            font-weight: 600;
        }
        
        QProgressBar::chunk {
            border-radius: 6px;
        }
        
        /* 数据准备进度条 - 静谧蓝 #4285F4 */
        #data_progress::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4285F4, stop:1 #00D4AA);
        }
        
        /* 模型训练进度条 - 活力橙 #FB8C00 */
        #train_progress::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FB8C00, stop:1 #FFB74D);
        }
        
        /* 回测进度条 - 魅力紫 #9C27B0 */
        #bt_progress::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9C27B0, stop:1 #BA68C8);
        }
        
        /* 输入框样式 */
        QLineEdit {
            border: 1px solid #DADCE0;
            border-radius: 6px;
            padding: 8px 12px;
            background-color: white;
        }
        
        QLineEdit:focus {
            border: 2px solid #1A73E8;
            background-color: #FAFCFE;
        }
        
        /* 下拉框样式 */
        QComboBox {
            border: 1px solid #DADCE0;
            border-radius: 6px;
            padding: 8px 12px;
            background-color: white;
        }
        
        QComboBox:hover {
            border: 1px solid #1A73E8;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        
        /* 日志输出区域 */
        QTextEdit {
            border: 1px solid #E8EAED;
            border-radius: 8px;
            background-color: #FAFBFC;
            padding: 8px;
        }
        
        /* 表格样式 - 斑马纹 */
        QTableWidget {
            border: 1px solid #E8EAED;
            border-radius: 8px;
            background-color: white;
            gridline-color: #E8EAED;
        }
        
        QTableWidget::item {
            padding: 8px;
        }
        
        QTableWidget::item:alternate {
            background-color: #FAFAFA;
        }
        
        QTableWidget::item:selected {
            background-color: #E8F0FE;
            color: #1A73E8;
        }
        
        QHeaderView::section {
            background-color: #F8F9FA;
            color: #1A73E8;
            padding: 10px;
            border: none;
            border-bottom: 2px solid #1A73E8;
            font-weight: 600;
        }
        
        /* 表格斑马纹 */
        QTableWidget QTableCornerButton::section {
            background-color: #F8F9FA;
        }
        
        /* 标签页选中高亮 - 各步骤专属色 */
        /* 步骤1: 数据准备 - 静谧蓝 */
        QTabBar::tab:nth(0):selected {
            border-bottom: 3px solid #4285F4;
        }
        
        /* 步骤2: 模型训练 - 活力橙 */
        QTabBar::tab:nth(1):selected {
            border-bottom: 3px solid #FB8C00;
        }
        
        /* 步骤3: 执行回测 - 魅力紫 */
        QTabBar::tab:nth(2):selected {
            border-bottom: 3px solid #9C27B0;
        }
        
        /* 步骤4: 结果大屏 - 翡翠绿 */
        QTabBar::tab:nth(3):selected {
            border-bottom: 3px solid #00A86B;
        }
        """
        self.setStyleSheet(theme_style)

    def _setup_status_bar_custom(self):
        """设置顶部自定义状态栏"""
        # 创建顶部状态栏 widget
        self.status_widget = QWidget()
        self.status_layout = QHBoxLayout(self.status_widget)
        self.status_layout.setContentsMargins(16, 8, 16, 8)
        
        # 系统状态指示
        self.status_indicator = QLabel("✅ 系统就绪")
        self.status_indicator.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: 600;
                font-size: 13px;
            }
        """)
        
        # 分隔线
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: rgba(255,255,255,0.5);")
        
        # 模型状态
        self.model_status = QLabel("📊 模型未加载")
        self.model_status.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: 600;
                font-size: 13px;
            }
        """)
        
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: rgba(255,255,255,0.5);")
        
        # 账户余额
        self.account_balance = QLabel("💰 账户: ¥1,000,000")
        self.account_balance.setStyleSheet("""
            QLabel {
                color: #00D4AA;
                font-weight: 700;
                font-size: 13px;
            }
        """)
        
        # 拉伸使标签靠右
        self.status_layout.addWidget(self.status_indicator)
        self.status_layout.addWidget(sep1)
        self.status_layout.addWidget(self.model_status)
        self.status_layout.addWidget(sep2)
        self.status_layout.addWidget(self.account_balance)
        self.status_layout.addStretch()
        
        # 设置顶部状态栏样式
        self.status_widget.setStyleSheet("""
            QWidget {
                background-color: #1A73E8;
            }
        """)
        
        # 获取主布局并插入顶部状态栏
        central_widget = self.centralWidget()
        if central_widget:
            main_layout = central_widget.layout()
            if main_layout:
                main_layout.insertWidget(0, self.status_widget)

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
        
        # 顶部操作栏
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        
        self.btn_data_manager = QPushButton("🎯 数据管理")
        self.btn_data_manager.setStyleSheet("""
            QPushButton {
                background-color: #1A237E;
                color: #FFFFFF;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3949AB;
            }
        """)
        self.btn_data_manager.clicked.connect(self._open_data_manager)
        top_layout.addWidget(self.btn_data_manager)
        
        layout.addLayout(top_layout)
        
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
        self.btn_download = QPushButton("▶ 开始获取与清洗数据 (阶段1&2)")
        self.btn_download.clicked.connect(self.on_start_data)
        self.btn_download.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_download)
        layout.addLayout(btn_layout)
        
        self.data_progress = QProgressBar()
        self.data_progress.setObjectName("data_progress")
        self.data_progress.setRange(0, 100)
        self.data_progress.setValue(0)
        self.data_progress.setTextVisible(True)
        layout.addWidget(self.data_progress)
        
        # 日志输出区域
        log_label = QLabel("📝 数据处理日志:")
        log_label.setStyleSheet("font-weight: 600; color: #4285F4;")
        layout.addWidget(log_label)
        
        self.data_log_output = QTextEdit()
        self.data_log_output.setReadOnly(True)
        self.data_log_output.setMaximumHeight(150)
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
        self.btn_train = QPushButton("▶ 开始训练")
        self.btn_train.clicked.connect(self.on_start_training)
        self.btn_train.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_train)
        layout.addLayout(btn_layout)
        
        self.train_progress = QProgressBar()
        self.train_progress.setObjectName("train_progress")
        self.train_progress.setRange(0, 100)
        self.train_progress.setValue(0)
        self.train_progress.setTextVisible(True)
        layout.addWidget(self.train_progress)
        
        log_label = QLabel("📝 训练实时日志:")
        log_label.setStyleSheet("font-weight: 600; color: #FB8C00;")
        layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
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
        self.btn_run_bt = QPushButton("📈 执行历史回测")
        self.btn_run_bt.clicked.connect(self.on_run_backtest)
        self.btn_run_bt.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_run_bt)
        layout.addLayout(btn_layout)
        
        self.bt_progress = QProgressBar()
        self.bt_progress.setObjectName("bt_progress")
        self.bt_progress.setRange(0, 100)
        self.bt_progress.setValue(0)
        self.bt_progress.setTextVisible(True)
        layout.addWidget(self.bt_progress)
        
        log_label = QLabel("📝 回测执行日志:")
        log_label.setStyleSheet("font-weight: 600; color: #9C27B0;")
        layout.addWidget(log_label)
        
        self.bt_log_output = QTextEdit()
        self.bt_log_output.setReadOnly(True)
        self.bt_log_output.setMaximumHeight(150)
        layout.addWidget(self.bt_log_output)
        
        self.tabs.addTab(tab, "📈 步骤3: 执行回测")

    def _setup_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 顶部按钮区域
        top_layout = QHBoxLayout()
        self.btn_load_results = QPushButton("📊 加载最新回测结果")
        self.btn_load_results.clicked.connect(self.load_results)
        top_layout.addWidget(self.btn_load_results)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 核心指标卡片区域
        metrics_group = QGroupBox("📊 核心绩效指标")
        metrics_layout = QHBoxLayout(metrics_group)
        
        # 总收益率卡片
        self.card_return = self._create_metric_card("📈 总收益率", "+0.00%", "#00D4AA")
        metrics_layout.addWidget(self.card_return)
        
        # 最大回撤卡片
        self.card_drawdown = self._create_metric_card("📉 最大回撤", "-0.00%", "#EA4335")
        metrics_layout.addWidget(self.card_drawdown)
        
        # 夏普比率卡片
        self.card_sharpe = self._create_metric_card("⚡ 夏普比率", "0.00", "#1A73E8")
        metrics_layout.addWidget(self.card_sharpe)
        
        # 胜率卡片
        self.card_winrate = self._create_metric_card("🎯 交易胜率", "0.0%", "#00A86B")
        metrics_layout.addWidget(self.card_winrate)
        
        layout.addWidget(metrics_group)
        
        # 收益曲线图区域
        chart_group = QGroupBox("💹 模拟资金净值走势")
        chart_layout = QVBoxLayout(chart_group)
        
        self.figure = Figure(figsize=(8, 4))
        self.figure.patch.set_facecolor('#FAFBFC')
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        layout.addWidget(chart_group)
        
        # 交易记录表格 - 斑马纹
        table_group = QGroupBox("📋 交易记录明细")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["交易日期", "股票代码", "交易动作", "触发原因", "成交价格", "成交数量", "盈亏金额", "盈亏比例"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)  # 斑马纹
        self.table.setShowGrid(True)
        self.table.setGridStyle(Qt.SolidLine)
        
        # 设置表格样式 - 斑马纹
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E8EAED;
                border-radius: 8px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F0F0F0;
            }
            QTableWidget::item:alternate {
                background-color: #FAFAFA;
            }
            QTableWidget::item:selected {
                background-color: #E8F0FE;
            }
        """)
        
        table_layout.addWidget(self.table)
        
        layout.addWidget(table_group)
        
        self.tabs.addTab(tab, "📊 步骤4: 结果大屏")

    def _create_metric_card(self, title, value, color):
        """创建指标卡片"""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border: 1px solid #E8EAED;
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #5F6368; font-size: 13px; font-weight: 500;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 700;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card

    def _update_metric_card(self, card, value, is_positive=None):
        """更新指标卡片值"""
        layout = card.layout()
        if layout and layout.count() > 1:
            value_label = layout.itemAt(1).widget()
            if value_label:
                # 根据正负自动设置颜色
                if is_positive is None:
                    try:
                        val = float(str(value).replace('%', '').replace('+', ''))
                        color = "#00D4AA" if val >= 0 else "#EA4335"
                    except:
                        color = "#1A73E8"
                elif is_positive:
                    color = "#00D4AA"
                else:
                    color = "#EA4335"
                
                value_label.setText(value)
                value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 700;")

    # --- Actions ---

    def append_log(self, widget, msg):
        widget.append(msg)
        widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())

    def on_start_data(self):
        if self.check_task_running(): return
        self.append_log(self.data_log_output, ">>> 开始执行数据准备任务...")
        self.btn_download.setEnabled(False)
        
        # 更新状态栏
        self.status_indicator.setText("⏳ 数据处理中...")
        
        cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script = "data_fetcher.py" if self.cb_data_source.currentIndex() == 1 else "feature_engineering.py"
        
        self.data_progress.setValue(0)
        self.data_worker = ScriptWorkerThread(script)
        self.data_worker.update_signal.connect(lambda msg: self.append_log(self.data_log_output, msg))
        self.data_worker.progress_signal.connect(self.data_progress.setValue)
        self.data_worker.finished_signal.connect(self._on_data_finished)
        self.data_worker.start()
        
    def _on_data_finished(self, success, msg):
        self.btn_download.setEnabled(True)
        if success:
            self.append_log(self.data_log_output, "✅ 数据准备完毕，您可以前往【步骤2】进行模型训练。")
            self.status_indicator.setText("✅ 数据已就绪")
            self.status_indicator.setStyleSheet("color: #00D4AA; font-weight: 600;")
            QMessageBox.information(self, "成功", "数据拉取与特征工程已完成！")
        else:
            self.append_log(self.data_log_output, "❌ 错误: " + msg)
            self.status_indicator.setText("❌ 数据处理失败")
            self.status_indicator.setStyleSheet("color: #EA4335; font-weight: 600;")
            QMessageBox.critical(self, "错误", "数据处理失败，详情请看日志。")

    def _open_data_manager(self):
        """打开数据管理对话框"""
        dialog = DataManagerDialog(self)
        dialog.exec()

    def on_start_training(self):
        if self.check_task_running(): return
        task = self.cb_model_type.currentText()
        self.append_log(self.log_output, f">>> 正在启动任务: {task}")
        self.btn_train.setEnabled(False)
        
        # 更新状态栏
        self.status_indicator.setText("⏳ 模型训练中...")
        
        if "XGBoost" in task:
            script = "xgboost_trainer.py"
        elif "LSTM" in task:
            script = "lstm_trainer.py"
        else:
            script = "model_fusion.py"
            
        self.train_progress.setValue(0)
        self.train_worker = ScriptWorkerThread(script)
        self.train_worker.update_signal.connect(lambda msg: self.append_log(self.log_output, msg))
        self.train_worker.progress_signal.connect(self.train_progress.setValue)
        self.train_worker.finished_signal.connect(self._on_training_finished)
        self.train_worker.start()

    def _on_training_finished(self, success, msg):
        self.btn_train.setEnabled(True)
        if success:
            self.append_log(self.log_output, "✅ " + msg)
            self.status_indicator.setText("✅ 模型已就绪")
            self.model_status.setText("📊 模型已加载")
            self.model_status.setStyleSheet("color: #00D4AA; font-weight: 600; font-size: 13px;")
            QMessageBox.information(self, "成功", "模型训练完成！")
        else:
            self.append_log(self.log_output, "❌ 错误: " + msg)
            self.status_indicator.setText("❌ 训练失败")
            self.status_indicator.setStyleSheet("color: #EA4335; font-weight: 600;")
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
        
        # 更新状态栏
        self.status_indicator.setText("⏳ 回测执行中...")
        
        self.bt_progress.setValue(0)
        self.bt_worker = ScriptWorkerThread("backtest_engine.py")
        self.bt_worker.update_signal.connect(lambda msg: self.append_log(self.bt_log_output, msg))
        self.bt_worker.progress_signal.connect(self.bt_progress.setValue)
        self.bt_worker.finished_signal.connect(self._on_bt_finished)
        self.bt_worker.start()

    def _on_bt_finished(self, success, msg):
        self.btn_run_bt.setEnabled(True)
        if success:
            self.append_log(self.bt_log_output, "✅ 回测执行完毕！请前往【结果大屏】查看详细报告。")
            self.status_indicator.setText("✅ 回测完成")
            self.status_indicator.setStyleSheet("color: #00D4AA; font-weight: 600;")
            QMessageBox.information(self, "成功", "历史数据回测完成，绩效报告已生成。")
            self.tabs.setCurrentIndex(3)
            self.load_results()
        else:
            self.append_log(self.bt_log_output, "❌ 错误: " + msg)
            self.status_indicator.setText("❌ 回测失败")
            self.status_indicator.setStyleSheet("color: #EA4335; font-weight: 600;")

    def load_results(self):
        reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
        metrics_file = os.path.join(reports_dir, "backtest_metrics.json")
        curve_file = os.path.join(reports_dir, "portfolio_curve.csv")
        trades_file = os.path.join(reports_dir, "trade_records.csv")
        
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            
            m = metrics.get('metrics', {})
            
            # 更新指标卡片
            total_return = m.get('total_return', 0) * 100
            self._update_metric_card(self.card_return, f"{total_return:+.2f}%")
            
            max_drawdown = m.get('max_drawdown', 0) * 100
            self._update_metric_card(self.card_drawdown, f"{max_drawdown:.2f}%", False)
            
            sharpe = m.get('sharpe_ratio', 0)
            self._update_metric_card(self.card_sharpe, f"{sharpe:.2f}")
            
            win_rate = m.get('win_rate', 0) * 100
            self._update_metric_card(self.card_winrate, f"{win_rate:.1f}%")
            
            # 同时更新文本显示
            display_text = f"=== 核心绩效指标 ===\n\n"
            display_text += f"总收益率 (Total Return):  {m.get('total_return', 0)*100:+.2f}%\n"
            display_text += f"最大回撤 (Max Drawdown):  {m.get('max_drawdown', 0)*100:.2f}%\n"
            display_text += f"夏普比率 (Sharpe Ratio):  {m.get('sharpe_ratio', 0):.2f}\n"
            display_text += f"交易胜率 (Win Rate):      {m.get('win_rate', 0)*100:.1f}%\n"
            display_text += f"盈亏比 (P/L Ratio):       {m.get('pl_ratio', 0):.2f}\n"
            display_text += f"总交易笔数 (Total Trades): {m.get('total_trades', 0)}\n"
            
            self.metrics_text.setPlainText(display_text)
        else:
            self.metrics_text.setPlainText("未找到回测指标文件，请先执行步骤3进行回测。")
            # 重置卡片
            self._update_metric_card(self.card_return, "+0.00%")
            self._update_metric_card(self.card_drawdown, "-0.00%", False)
            self._update_metric_card(self.card_sharpe, "0.00")
            self._update_metric_card(self.card_winrate, "0.0%")

        if os.path.exists(curve_file):
            df = pd.read_csv(curve_file)
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # 设置背景色
            ax.set_facecolor('#FAFBFC')
            self.figure.patch.set_facecolor('#FAFBFC')
            
            if 'date' in df.columns and 'value' in df.columns:
                dates = pd.to_datetime(df['date'])
                values = df['value']
                
                # 绘制收益曲线 - 渐变填充
                ax.plot(dates, values, color='#1A73E8', linewidth=2, label='账户净值')
                ax.fill_between(dates, values, alpha=0.3, color='#1A73E8')
                
                # 添加基准线
                ax.axhline(y=values.iloc[0] if len(values) > 0 else 1000000, 
                          color='#EA4335', linestyle='--', linewidth=1, alpha=0.7, label='起始资金')
                
                matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
                matplotlib.rcParams['axes.unicode_minus'] = False
                
                ax.set_title("模拟资金净值走势曲线", fontsize=14, fontweight='600', color='#1A73E8')
                ax.set_ylabel("账户总资金 (元)", fontsize=11)
                ax.set_xlabel("交易日期", fontsize=11)
                ax.grid(True, linestyle='--', alpha=0.6, color='#E8EAED')
                ax.legend(loc='upper left', framealpha=0.9)
                
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
