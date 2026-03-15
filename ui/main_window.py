"""
Nova 股票预测软件 - 整体 UI 框架
基于 Pixel 设计文档 v1.0
开发优先级：第一阶段 - 入口框架
"""

import re
import os
import sys
import json
import subprocess
import datetime
import shutil
import pandas as pd
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTabWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QFormLayout, 
    QLineEdit, QComboBox, QGroupBox, QSplitter,
    QTextEdit, QMessageBox, QProgressBar, QApplication,
    QDialog, QDialogButtonBox, QScrollArea, QSizePolicy,
    QStackedWidget, QFrame, QDateEdit
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QDate
from PySide6.QtGui import QFont
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import time

# Import data fetcher
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data_fetcher import DataFetcher

# ==================== 配色方案 ====================
COLORS = {
    'bg_primary': '#1E1E2E',
    'bg_secondary': '#2A2A3E',
    'bg_card': '#363650',
    'text_primary': '#FFFFFF',
    'text_secondary': '#A0A0B0',
    'accent': '#4A90D9',
    'success': '#4CAF50',
    'warning': '#FF9800',
    'error': '#F44336',
    'sidebar_bg': '#181825',
    'sidebar_hover': '#313244',
    'sidebar_active': '#45475A',
}

class DownloadThread(QThread):
    """后台数据下载线程"""
    progress = Signal(int, int, str)
    finished = Signal(bool, str, int, int)
    log_signal = Signal(str)
    
    def __init__(self, data_fetcher, stock_pool, start_date, parent=None):
        super().__init__(parent)
        self.data_fetcher = data_fetcher
        self.stock_pool = stock_pool
        self.start_date = start_date
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        success_count = 0
        fail_count = 0
        total = len(self.stock_pool)
        
        self.log_signal.emit(f"开始下载 {total} 只股票的数据...")
        
        for i, code in enumerate(self.stock_pool):
            if self._is_cancelled:
                self.log_signal.emit("下载已取消")
                break
            
            self.progress.emit(i + 1, total, f"正在下载 {code}...")
            
            try:
                df = self.data_fetcher.fetch_daily_data(code, start_date=self.start_date)
                if df is not None and not df.empty:
                    self.data_fetcher.save_data(df, code)
                    success_count += 1
                    self.log_signal.emit(f"✓ {code} 下载成功 ({len(df)} 条记录)")
                else:
                    fail_count += 1
                    self.log_signal.emit(f"✗ {code} 无数据")
            except Exception as e:
                fail_count += 1
                self.log_signal.emit(f"✗ {code} 下载失败: {str(e)}")
            
            time.sleep(0.3)
        
        self.finished.emit(True, f"下载完成！成功: {success_count} 只, 失败: {fail_count} 只", success_count, fail_count)





class SidebarButton(QPushButton):
    """侧边栏导航按钮"""
    def __init__(self, text, icon, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self._set_style()
        
    def _set_style(self):
        style = f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {COLORS['sidebar_hover']};
                color: {COLORS['text_primary']};
            }}
        """
        self.setStyleSheet(style)


class MainWindow(QMainWindow):
    """主窗口 - 侧边栏 + 主内容区布局"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🍀 股票预测助手")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 600)
        
        # 数据下载相关
        self.data_fetcher = None
        self.download_thread = None
        
        # 数据状态
        self.data_status = {
            'stock_count': 0,
            'last_update': '未知',
            'data_path': 'stock_data_parquet'
        }
        
        self._apply_dark_theme()
        self._init_ui()
        self.statusBar().showMessage("✅ 系统就绪 | 📊 模型未加载 | 💰 账户: ¥1,000,000")
    
    def _load_data_status(self):
        """加载数据状态"""
        data_path = self.data_status.get('data_path', 'stock_data_parquet')
        if os.path.exists(data_path):
            files = [f for f in os.listdir(data_path) if f.endswith('.parquet')]
            self.data_status['stock_count'] = len(files)
            
            if files:
                latest_file = max([os.path.join(data_path, f) for f in files], key=os.path.getmtime)
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file))
                self.data_status['last_update'] = mod_time.strftime("%Y-%m-%d %H:%M")
            
            if hasattr(self, 'data_count_label'):
                self.data_count_label.setText(f"📊 已下载: {self.data_status['stock_count']} 只股票")
            if hasattr(self, 'last_update_label'):
                self.last_update_label.setText(f"🕐 最后更新: {self.data_status['last_update']}")
    
    def _apply_dark_theme(self):
        style = f"""
            QMainWindow, QWidget {{ background-color: {COLORS['bg_primary']}; }}
            QWidget {{ font-family: "Microsoft YaHei", sans-serif; font-size: 14px; color: {COLORS['text_primary']}; }}
            QLabel {{ color: {COLORS['text_primary']}; background: transparent; }}
            QPushButton {{ background-color: {COLORS['accent']}; color: white; border: none; border-radius: 8px; padding: 10px 20px; font-weight: 600; }}
            QPushButton:hover {{ background-color: #5A9DE9; }}
            QLineEdit, QComboBox {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 6px; padding: 8px; }}
            QTextEdit {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 8px; }}
            QProgressBar {{ border: 2px solid {COLORS['bg_secondary']}; border-radius: 8px; text-align: center; background: {COLORS['bg_secondary']}; color: white; font-weight: 600; }}
            QProgressBar::chunk {{ border-radius: 6px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {COLORS['accent']},stop:1 {COLORS['success']}); }}
            QGroupBox {{ border: 1px solid #404060; border-radius: 12px; margin-top: 16px; padding: 16px; background: {COLORS['bg_card']}; font-weight: 600; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 16px; padding: 4px 12px; color: {COLORS['accent']}; }}
            QTableWidget {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 8px; gridline-color: #404060; }}
            QHeaderView::section {{ background: {COLORS['bg_card']}; color: white; padding: 8px; border: none; border-bottom: 2px solid {COLORS['accent']}; }}
            QStatusBar {{ background: {COLORS['bg_secondary']}; color: {COLORS['text_secondary']}; padding: 6px 12px; border-top: 1px solid #404060; font-size: 12px; }}
            QDateEdit {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 6px; padding: 8px; }}
        """
        self.setStyleSheet(style)
    
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar, stretch=1)
        
        # 主内容区
        content_widget = QWidget()
        content_style = f"background-color: {COLORS['bg_primary']};"
        content_widget.setStyleSheet(content_style)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)
        
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack, stretch=1)
        
        main_layout.addWidget(content_widget, stretch=5)
        
        # 添加页面
        self._add_home_page()
        self._add_data_page()
        self._add_model_page()
        self._add_backtest_page()
        self._add_settings_page()
    
    def _create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar_style = f"QWidget {{ background-color: {COLORS['sidebar_bg']}; }}"
        sidebar.setStyleSheet(sidebar_style)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(8)
        
        # 标题
        title_label = QLabel("🍀 股票预测助手")
        title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: white; padding: 8px 12px;")
        layout.addWidget(title_label)
        layout.addSpacing(20)
        
        # 导航按钮
        nav_items = [("📊", "首页"), ("📁", "数据"), ("🧠", "模型"), ("📈", "回测"), ("⚙️", "设置")]
        
        self.nav_buttons = []
        for icon, name in nav_items:
            btn = SidebarButton(f"  {icon}  {name}", icon)
            btn.clicked.connect(lambda checked, n=name: self._on_nav_clicked(n))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)
        
        # 激活第一个
        active_style = f"QPushButton {{ background-color: {COLORS['sidebar_active']}; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; text-align: left; font-weight: 600; }}"
        self.nav_buttons[0].setStyleSheet(active_style)
        
        layout.addStretch()
        
        # 版本
        status_label = QLabel("v1.0.0")
        status_label_style = f"color: {COLORS['text_secondary']}; font-size: 12px; padding: 8px 12px;"
        status_label.setStyleSheet(status_label_style)
        layout.addWidget(status_label)
        
        return sidebar
    
    def _on_nav_clicked(self, page_name):
        page_map = {"首页": 0, "数据": 1, "模型": 2, "回测": 3, "设置": 4}
        idx = page_map.get(page_name, 0)
        
        for i, btn in enumerate(self.nav_buttons):
            if i == idx:
                active_btn_style = f"QPushButton {{ background-color: {COLORS['sidebar_active']}; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; text-align: left; font-weight: 600; }}"
                btn.setStyleSheet(active_btn_style)
            else:
                inactive_btn_style = f"QPushButton {{ background-color: transparent; color: {COLORS['text_secondary']}; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; text-align: left; }} QPushButton:hover {{ background-color: {COLORS['sidebar_hover']}; color: white; }}"
                btn.setStyleSheet(inactive_btn_style)
        
        self.content_stack.setCurrentIndex(idx)
    
    def _create_card(self, title=""):
        card = QFrame()
        card_style = f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 16px; }}"
        card.setStyleSheet(card_style)
        
        if title:
            layout = QVBoxLayout(card)
            title_label = QLabel(title)
            title_label_style = f"font-size: 16px; font-weight: 600; color: {COLORS['accent']}; margin-bottom: 12px;"
            title_label.setStyleSheet(title_label_style)
            layout.addWidget(title_label)
            return card
        return card
    
    # ==================== 首页 ====================
    def _add_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        
        title = QLabel("📊 仪表盘")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        
        # ==================== 数据获取区域 ====================
        fetch_card = self._create_card("📥 数据获取")
        fetch_layout = QVBoxLayout(fetch_card)
        
        config_layout = QHBoxLayout()
        config_layout.setSpacing(16)
        
        # 股票池选择
        stock_pool_layout = QVBoxLayout()
        stock_pool_layout.setSpacing(4)
        stock_pool_layout.addWidget(QLabel("股票池"))
        self.home_stock_pool = QComboBox()
        self.home_stock_pool.addItems(["全A股", "沪深300", "中证500", "创业板", "科创板", "北证50"])
        self.home_stock_pool.setStyleSheet(f"QComboBox {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 6px; padding: 8px; }}")
        stock_pool_layout.addWidget(self.home_stock_pool)
        config_layout.addLayout(stock_pool_layout)
        
        # 数据类型
        data_type_layout = QVBoxLayout()
        data_type_layout.setSpacing(4)
        data_type_layout.addWidget(QLabel("数据类型"))
        self.home_data_type = QComboBox()
        self.home_data_type.addItems(["日K线数据", "周K线数据", "月K线数据", "分钟K线数据"])
        self.home_data_type.setStyleSheet(f"QComboBox {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 6px; padding: 8px; }}")
        data_type_layout.addWidget(self.home_data_type)
        config_layout.addLayout(data_type_layout)
        
        # 日期范围
        date_layout = QVBoxLayout()
        date_layout.setSpacing(4)
        date_layout.addWidget(QLabel("日期范围"))
        
        date_range_layout = QHBoxLayout()
        date_range_layout.setSpacing(8)
        
        self.home_start_date = QDateEdit()
        self.home_start_date.setCalendarPopup(True)
        self.home_start_date.setDate(QDate(2025, 1, 1))
        self.home_start_date.setStyleSheet(f"QDateEdit {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 6px; padding: 8px; }}")
        date_range_layout.addWidget(self.home_start_date)
        
        date_range_layout.addWidget(QLabel("至"))
        
        self.home_end_date = QDateEdit()
        self.home_end_date.setCalendarPopup(True)
        self.home_end_date.setDate(QDate.currentDate())
        self.home_end_date.setStyleSheet(f"QDateEdit {{ background: {COLORS['bg_secondary']}; color: white; border: 1px solid #404060; border-radius: 6px; padding: 8px; }}")
        date_range_layout.addWidget(self.home_end_date)
        
        date_layout.addLayout(date_range_layout)
        config_layout.addLayout(date_layout)
        
        # 下载按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)
        btn_layout.addWidget(QLabel(""))
        self.home_download_btn = QPushButton("🚀 开始下载")
        self.home_download_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['success']}; color: white; border: none; border-radius: 8px; padding: 12px 24px; font-weight: 600; font-size: 14px; }} QPushButton:hover {{ background-color: #5DC460; }}")
        self.home_download_btn.clicked.connect(self._on_home_download_clicked)
        btn_layout.addWidget(self.home_download_btn)
        
        config_layout.addLayout(btn_layout)
        
        fetch_layout.addLayout(config_layout)
        
        # 下载进度条
        self.home_progress = QProgressBar()
        self.home_progress.setValue(0)
        self.home_progress.setVisible(False)
        fetch_layout.addWidget(self.home_progress)
        
        # 下载状态标签
        self.home_status_label = QLabel("")
        self.home_status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        fetch_layout.addWidget(self.home_status_label)
        
        layout.addWidget(fetch_card)
        
        # ==================== 快捷操作区域 ====================
        quick_card = self._create_card("⚡ 快捷操作")
        quick_layout = QHBoxLayout(quick_card)
        quick_layout.setSpacing(12)
        
        # 快速下载
        quick_download_group = QVBoxLayout()
        quick_download_group.setSpacing(8)
        quick_download_group.addWidget(QLabel("快速下载"))
        
        quick_dl_btns_layout = QHBoxLayout()
        quick_dl_btns_layout.setSpacing(8)
        
        qd1 = QPushButton("📊 今日行情")
        qd1.setToolTip("下载今日实时行情数据")
        qd1.clicked.connect(lambda: self._quick_download("today"))
        qd1.setStyleSheet(f"QPushButton {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['accent']}; border-radius: 6px; padding: 8px 12px; }} QPushButton:hover {{ background-color: {COLORS['accent']}; }}")
        quick_dl_btns_layout.addWidget(qd1)
        
        qd2 = QPushButton("📈 最近一周")
        qd2.setToolTip("下载最近一周的数据")
        qd2.clicked.connect(lambda: self._quick_download("week"))
        qd2.setStyleSheet(f"QPushButton {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['accent']}; border-radius: 6px; padding: 8px 12px; }} QPushButton:hover {{ background-color: {COLORS['accent']}; }}")
        quick_dl_btns_layout.addWidget(qd2)
        
        qd3 = QPushButton("📅 最近一月")
        qd3.setToolTip("下载最近一个月的数据")
        qd3.clicked.connect(lambda: self._quick_download("month"))
        qd3.setStyleSheet(f"QPushButton {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['accent']}; border-radius: 6px; padding: 8px 12px; }} QPushButton:hover {{ background-color: {COLORS['accent']}; }}")
        quick_dl_btns_layout.addWidget(qd3)
        
        qd4 = QPushButton("📆 最近一年")
        qd4.setToolTip("下载最近一年的数据")
        qd4.clicked.connect(lambda: self._quick_download("year"))
        qd4.setStyleSheet(f"QPushButton {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['accent']}; border-radius: 6px; padding: 8px 12px; }} QPushButton:hover {{ background-color: {COLORS['accent']}; }}")
        quick_dl_btns_layout.addWidget(qd4)
        
        quick_dl_btns_layout.addStretch()
        quick_download_group.addLayout(quick_dl_btns_layout)
        quick_layout.addLayout(quick_download_group)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet(f"QFrame {{ color: #404060; }}")
        quick_layout.addWidget(separator)
        
        # 快速训练
        train_group = QVBoxLayout()
        train_group.setSpacing(8)
        train_group.addWidget(QLabel("快速训练"))
        
        train_btn = QPushButton("🧠 一键训练")
        train_btn.setToolTip("使用默认配置开始训练模型")
        train_btn.clicked.connect(lambda: self._on_nav_clicked("模型"))
        train_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['warning']}; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600; }} QPushButton:hover {{ background-color: #FFAB2E; }}")
        train_group.addWidget(train_btn)
        quick_layout.addLayout(train_group)
        
        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setStyleSheet(f"QFrame {{ color: #404060; }}")
        quick_layout.addWidget(separator2)
        
        # 快速回测
        backtest_group = QVBoxLayout()
        backtest_group.setSpacing(8)
        backtest_group.addWidget(QLabel("快速回测"))
        
        bt_btn = QPushButton("📈 开始回测")
        bt_btn.setToolTip("使用最新模型进行回测")
        bt_btn.clicked.connect(lambda: self._on_nav_clicked("回测"))
        bt_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['accent']}; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600; }} QPushButton:hover {{ background-color: #5A9DE9; }}")
        backtest_group.addWidget(bt_btn)
        quick_layout.addLayout(backtest_group)
        
        quick_layout.addStretch()
        layout.addWidget(quick_card)
        
        # ==================== 状态显示区域 ====================
        status_card = self._create_card("📊 数据状态")
        status_layout = QHBoxLayout(status_card)
        status_layout.setSpacing(20)
        
        self.data_count_label = QLabel(f"📊 已下载: {self.data_status.get('stock_count', 0)} 只股票")
        self.data_count_label.setStyleSheet(f"font-size: 16px; font-weight: 600;")
        status_layout.addWidget(self.data_count_label)
        
        self.last_update_label = QLabel(f"🕐 最后更新: {self.data_status.get('last_update', '未知')}")
        self.last_update_label.setStyleSheet(f"font-size: 16px; font-weight: 600;")
        status_layout.addWidget(self.last_update_label)
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._refresh_data_status)
        refresh_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['accent']}; border-radius: 6px; padding: 8px 16px; }} QPushButton:hover {{ background-color: {COLORS['accent']}; }}")
        status_layout.addWidget(refresh_btn)
        
        status_layout.addStretch()
        layout.addWidget(status_card)
        
        # 核心指标
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)
        
        asset_card = self._create_metric_card("💰 账户总资产", "¥1,250,000", COLORS['accent'])
        metrics_layout.addWidget(asset_card)
        
        profit_card = self._create_metric_card("📈 今日收益", "+2.35%", COLORS['success'])
        metrics_layout.addWidget(profit_card)
        
        accuracy_card = self._create_metric_card("🎯 预测准确率", "67.8%", COLORS['warning'])
        metrics_layout.addWidget(accuracy_card)
        
        layout.addLayout(metrics_layout)
        
        # 信号
        signal_card = self._create_card("📢 最新预测信号")
        signal_layout = QVBoxLayout(signal_card)
        
        signals = [("600519", "买入", "85%", "12:25"), ("000858", "卖出", "72%", "11:50"), ("300750", "持有", "68%", "10:30")]
        for code, action, conf, t in signals:
            signal_layout.addWidget(self._create_signal_row(code, action, conf, t))
        
        layout.addWidget(signal_card)
        
        layout.addStretch()
        self.content_stack.addWidget(page)
    
    def _refresh_data_status(self):
        """刷新数据状态"""
        self._load_data_status()
        QMessageBox.information(self, "刷新成功", f"数据状态已刷新！\n已下载: {self.data_status['stock_count']} 只股票\n最后更新: {self.data_status['last_update']}")
    
    def _quick_download(self, period):
        """快速下载"""
        today = datetime.datetime.now()
        
        if period == "today":
            start_date = today.strftime("%Y%m%d")
        elif period == "week":
            start_date = (today - datetime.timedelta(days=7)).strftime("%Y%m%d")
        elif period == "month":
            start_date = (today - datetime.timedelta(days=30)).strftime("%Y%m%d")
        elif period == "year":
            start_date = (today - datetime.timedelta(days=365)).strftime("%Y%m%d")
        else:
            start_date = "20250101"
        
        self._start_download(stock_pool_type="全A股", start_date=start_date)
    
    def _on_home_download_clicked(self):
        """首页下载按钮点击"""
        stock_pool_type = self.home_stock_pool.currentText()
        start_date = self.home_start_date.date().toString("yyyyMMdd")
        end_date = self.home_end_date.date().toString("yyyyMMdd")
        
        if start_date > end_date:
            QMessageBox.warning(self, "日期错误", "开始日期不能晚于结束日期！")
            return
        
        self._start_download(stock_pool_type, start_date)
    
    def _start_download(self, stock_pool_type, start_date):
        """开始数据下载"""
        self.home_download_btn.setEnabled(False)
        self.home_progress.setVisible(True)
        self.home_progress.setValue(0)
        
        if self.data_fetcher is None:
            self.data_fetcher = DataFetcher(data_dir=self.data_status.get('data_path', 'stock_data_parquet'), use_parquet=True)
        
        self.home_status_label.setText("正在获取股票列表...")
        
        try:
            if stock_pool_type == "全A股":
                stock_pool = self.data_fetcher.get_stock_pool()
            elif stock_pool_type == "沪深300":
                stock_pool = self.data_fetcher.get_stock_pool()[:300]
            elif stock_pool_type == "中证500":
                stock_pool = self.data_fetcher.get_stock_pool()[:500]
            elif stock_pool_type == "创业板":
                stock_pool = self.data_fetcher.get_stock_pool()[:100]
            elif stock_pool_type == "科创板":
                stock_pool = []
                QMessageBox.information(self, "提示", "科创板功能开发中")
            elif stock_pool_type == "北证50":
                stock_pool = []
                QMessageBox.information(self, "提示", "北证50功能开发中")
            else:
                stock_pool = self.data_fetcher.get_stock_pool()
            
            if not stock_pool:
                QMessageBox.warning(self, "股票池为空", "无法获取股票列表，请检查网络连接！")
                self.home_download_btn.setEnabled(True)
                return
            
            stock_pool = stock_pool[:100]
            
            self.download_thread = DownloadThread(self.data_fetcher, stock_pool, start_date)
            self.download_thread.progress.connect(self._on_download_progress)
            self.download_thread.finished.connect(self._on_download_finished)
            self.download_thread.log_signal.connect(lambda msg: self.home_status_label.setText(msg))
            self.download_thread.start()
            
            self.home_status_label.setText(f"准备下载 {len(stock_pool)} 只股票...")
            
        except Exception as e:
            QMessageBox.critical(self, "下载失败", f"获取股票列表失败：{str(e)}")
            self.home_download_btn.setEnabled(True)
            self.home_progress.setVisible(False)
    
    def _on_download_progress(self, current, total, status):
        """下载进度更新"""
        progress = int(current / total * 100)
        self.home_progress.setValue(progress)
        self.home_status_label.setText(f"{status} ({current}/{total})")
    
    def _on_download_finished(self, success, message, success_count, fail_count):
        """下载完成"""
        self.home_download_btn.setEnabled(True)
        self.home_progress.setVisible(False)
        
        self._load_data_status()
        
        if success:
            QMessageBox.information(self, "下载完成", message)
        else:
            QMessageBox.warning(self, "下载失败", message)
        
        self.home_status_label.setText(message)
    
    def _create_metric_card(self, title, value, color):
        card = QFrame()
        card_style = f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 20px; min-width: 180px; }}"
        card.setStyleSheet(card_style)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label_style = f"color: {COLORS['text_secondary']}; font-size: 14px;"
        title_label.setStyleSheet(title_label_style)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label_style = f"color: {color}; font-size: 28px; font-weight: 700;"
        value_label.setStyleSheet(value_label_style)
        layout.addWidget(value_label)
        
        return card
    
    def _create_signal_row(self, code, action, conf, t):
        widget = QWidget()
        widget_style = f"background-color: #2A2A3E; border-radius: 8px; padding: 12px;"
        widget.setStyleSheet(widget_style)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        
        code_label = QLabel(code)
        code_label.setStyleSheet("font-weight: 600; min-width: 80px;")
        layout.addWidget(code_label)
        
        action_label = QLabel(action)
        action_color = COLORS['success'] if action == "买入" else (COLORS['error'] if action == "卖出" else COLORS['warning'])
        action_label_style = f"color: {action_color}; font-weight: 600; min-width: 50px;"
        action_label.setStyleSheet(action_label_style)
        layout.addWidget(action_label)
        
        conf_label = QLabel(conf)
        conf_label_style = f"color: {COLORS['text_secondary']};"
        conf_label.setStyleSheet(conf_label_style)
        layout.addWidget(conf_label)
        
        layout.addStretch()
        
        time_label = QLabel(t)
        time_label_style = f"color: {COLORS['text_secondary']};"
        time_label.setStyleSheet(time_label_style)
        layout.addWidget(time_label)
        
        return widget
    
    # ==================== 数据页面 ====================
    def _add_data_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        
        title = QLabel("📁 数据管理")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        
        # 数据获取
        fetch_card = self._create_card("📥 数据获取")
        fetch_layout = QFormLayout(fetch_card)
        fetch_layout.setSpacing(12)
        
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["AShare", "Tushare", "自建"])
        fetch_layout.addRow("数据源：", self.data_source_combo)
        
        self.stock_pool_combo = QComboBox()
        self.stock_pool_combo.addItems(["全市场", "沪深300", "自定义"])
        fetch_layout.addRow("股票池：", self.stock_pool_combo)
        
        date_layout = QHBoxLayout()
        self.start_date_input = QLineEdit("2023-03-15")
        self.end_date_input = QLineEdit("2026-03-15")
        date_layout.addWidget(self.start_date_input)
        date_layout.addWidget(QLabel(" ~ "))
        date_layout.addWidget(self.end_date_input)
        fetch_layout.addRow("时间范围：", date_layout)
        
        fetch_btn = QPushButton("📥 获取最新数据")
        fetch_layout.addRow("", fetch_btn)
        
        layout.addWidget(fetch_card)
        
        # 数据概览
        overview_card = self._create_card("📋 数据概览")
        overview_layout = QVBoxLayout(overview_card)
        overview_layout.addWidget(QLabel("总记录数: 1,250,000"))
        overview_layout.addWidget(QLabel("股票数量: 5,200"))
        overview_layout.addWidget(QLabel("最后更新: 12:30"))
        layout.addWidget(overview_card)
        
        self.content_stack.addWidget(page)
    
    # ==================== 模型页面 ====================
    def _add_model_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        
        title = QLabel("🧠 模型训练")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        
        # 特征配置
        feature_card = self._create_card("🎛️ 特征配置")
        feature_layout = QFormLayout(feature_card)
        feature_layout.setSpacing(12)
        
        tech_layout = QHBoxLayout()
        for name in ["MA5", "MA10", "MA20", "RSI", "MACD"]:
            tech_layout.addWidget(QPushButton(f"☑ {name}"))
        tech_layout.addStretch()
        feature_layout.addRow("技术指标：", tech_layout)
        
        fund_layout = QHBoxLayout()
        for name in ["市值", "PE", "PB", "ROE"]:
            fund_layout.addWidget(QPushButton(f"☑ {name}"))
        fund_layout.addStretch()
        feature_layout.addRow("基本面：", fund_layout)
        
        layout.addWidget(feature_card)
        
        # 模型选择
        model_card = self._create_card("🤖 模型选择")
        model_layout = QFormLayout(model_card)
        model_layout.setSpacing(12)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["LightGBM", "XGBoost", "LSTM", "集成学习"])
        model_layout.addRow("选择模型：", self.model_combo)
        
        param_layout = QHBoxLayout()
        self.learning_rate = QLineEdit("0.05")
        self.tree_depth = QLineEdit("6")
        self.iterations = QLineEdit("500")
        param_layout.addWidget(QLabel("学习率:"))
        param_layout.addWidget(self.learning_rate)
        param_layout.addWidget(QLabel("树深度:"))
        param_layout.addWidget(self.tree_depth)
        param_layout.addWidget(QLabel("迭代次数:"))
        param_layout.addWidget(self.iterations)
        param_layout.addStretch()
        model_layout.addRow("参数：", param_layout)
        
        layout.addWidget(model_card)
        
        # 训练执行
        train_card = self._create_card("🚀 训练执行")
        train_layout = QVBoxLayout(train_card)
        
        train_info = QLabel("当前模型：LightGBM_v3")
        train_info_style = f"color: {COLORS['text_secondary']};"
        train_info.setStyleSheet(train_info_style)
        train_layout.addWidget(train_info)
        
        self.train_progress = QProgressBar()
        self.train_progress.setValue(80)
        train_layout.addWidget(self.train_progress)
        
        progress_label = QLabel("训练进度：████████████░░░░░░ 80%")
        progress_label_style = f"color: {COLORS['text_secondary']};"
        progress_label.setStyleSheet(progress_label_style)
        train_layout.addWidget(progress_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        start_btn = QPushButton("▶️ 开始训练")
        start_btn_style = f"QPushButton {{ background-color: {COLORS['success']}; }}"
        start_btn.setStyleSheet(start_btn_style)
        stop_btn = QPushButton("⏹️ 停止")
        save_btn = QPushButton("💾 保存模型")
        
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(stop_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        
        train_layout.addLayout(btn_layout)
        layout.addWidget(train_card)
        
        # 训练记录
        record_card = self._create_card("📜 训练记录")
        record_layout = QVBoxLayout(record_card)
        
        self.train_table = QTableWidget(3, 4)
        self.train_table.setHorizontalHeaderLabels(["模型名称", "准确率", "训练时间", "操作"])
        items = [("LightGBM_v3", "67.8%", "10分钟"), ("LightGBM_v2", "65.2%", "8分钟"), ("XGBoost_v1", "63.5%", "12分钟")]
        for i, (name, acc, t) in enumerate(items):
            self.train_table.setItem(i, 0, QTableWidgetItem(name))
            self.train_table.setItem(i, 1, QTableWidgetItem(acc))
            self.train_table.setItem(i, 2, QTableWidgetItem(t))
        
        record_layout.addWidget(self.train_table)
        layout.addWidget(record_card)
        
        layout.addStretch()
        self.content_stack.addWidget(page)
    
    # ==================== 回测页面 ====================
    def _add_backtest_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        
        title = QLabel("📈 策略回测")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        
        # 策略配置
        strategy_card = self._create_card("⚙️ 策略配置")
        strategy_layout = QFormLayout(strategy_card)
        strategy_layout.setSpacing(12)
        
        self.backtest_model = QComboBox()
        self.backtest_model.addItems(["LightGBM_v3", "LightGBM_v2", "XGBoost_v1"])
        strategy_layout.addRow("选择模型：", self.backtest_model)
        
        bt_date_layout = QHBoxLayout()
        self.bt_start = QLineEdit("2023-03-15")
        self.bt_end = QLineEdit("2026-03-15")
        bt_date_layout.addWidget(self.bt_start)
        bt_date_layout.addWidget(QLabel(" ~ "))
        bt_date_layout.addWidget(self.bt_end)
        strategy_layout.addRow("回测区间：", bt_date_layout)
        
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("初始资金:"))
        param_layout.addWidget(QLineEdit("100,000"))
        param_layout.addWidget(QLabel("手续费:"))
        param_layout.addWidget(QLineEdit("0.1%"))
        param_layout.addWidget(QLabel("滑点:"))
        param_layout.addWidget(QLineEdit("0.05%"))
        param_layout.addStretch()
        strategy_layout.addRow("交易参数：", param_layout)
        
        layout.addWidget(strategy_card)
        
        # 执行回测
        exec_card = self._create_card("🚀 执行回测")
        exec_layout = QVBoxLayout(exec_card)
        
        btn_layout = QHBoxLayout()
        start_bt_btn = QPushButton("▶️ 开始回测")
        start_bt_btn_style = f"QPushButton {{ background-color: {COLORS['success']}; }}"
        start_bt_btn.setStyleSheet(start_bt_btn_style)
        stop_bt_btn = QPushButton("⏹️ 停止")
        btn_layout.addWidget(start_bt_btn)
        btn_layout.addWidget(stop_bt_btn)
        btn_layout.addStretch()
        exec_layout.addLayout(btn_layout)
        
        self.bt_progress = QProgressBar()
        self.bt_progress.setValue(45)
        exec_layout.addWidget(self.bt_progress)
        
        layout.addWidget(exec_card)
        
        # 绩效分析
        perf_card = self._create_card("📈 绩效分析")
        perf_layout = QVBoxLayout(perf_card)
        
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(20)
        
        perf_items = [("总收益率", "+85.6%", COLORS['success']), ("年化收益", "+28.5%", COLORS['success']), ("夏普比率", "1.82", COLORS['accent']), ("最大回撤", "-12.3%", COLORS['error']), ("胜率", "58.6%", COLORS['success'])]
        
        for label, value, color in perf_items:
            m_card = QFrame()
            m_card_style = f"QFrame {{ background-color: {COLORS['bg_secondary']}; border-radius: 8px; padding: 12px; min-width: 100px; }}"
            m_card.setStyleSheet(m_card_style)
            m_layout = QVBoxLayout(m_card)
            m_layout.setSpacing(4)
            m_layout.addWidget(QLabel(label))
            m_layout.addWidget(QLabel(value))
            m_layout.addWidget(QLabel(""))
            metrics_layout.addWidget(m_card)
        
        perf_layout.addLayout(metrics_layout)
        layout.addWidget(perf_card)
        
        layout.addStretch()
        self.content_stack.addWidget(page)
    
    # ==================== 设置页面 ====================
    def _add_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        
        title = QLabel("⚙️ 参数配置")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        
        # 数据源设置
        data_card = self._create_card("📡 数据源设置")
        data_layout = QFormLayout(data_card)
        data_layout.setSpacing(12)
        
        self.main_source = QComboBox()
        self.main_source.addItems(["AShare"])
        data_layout.addRow("主数据源：", self.main_source)
        
        backup_source = QComboBox()
        backup_source.addItems(["Tushare（仅在主数据源失败时启用）"])
        data_layout.addRow("备用数据源：", backup_source)
        
        save_btn = QPushButton("💾 保存设置")
        data_layout.addRow("", save_btn)
        
        layout.addWidget(data_card)
        
        # 模型参数
        model_card = self._create_card("🤖 模型参数")
        model_layout = QFormLayout(model_card)
        model_layout.setSpacing(12)
        
        default_model = QComboBox()
        default_model.addItems(["LightGBM"])
        model_layout.addRow("默认模型：", default_model)
        
        train_ratio = QLineEdit("80%")
        val_ratio = QLineEdit("20%")
        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(QLabel("训练数据比例:"))
        ratio_layout.addWidget(train_ratio)
        ratio_layout.addWidget(QLabel("验证数据比例:"))
        ratio_layout.addWidget(val_ratio)
        model_layout.addRow("", ratio_layout)
        
        save_btn2 = QPushButton("💾 保存设置")
        model_layout.addRow("", save_btn2)
        
        layout.addWidget(model_card)
        
        # 关于
        about_card = self._create_card("ℹ️ 关于")
        about_layout = QVBoxLayout(about_card)
        about_layout.addWidget(QLabel("版本：v1.0.0"))
        about_layout.addWidget(QLabel("构建时间：2026-03-15"))
        
        layout.addWidget(about_card)
        
        layout.addStretch()
        self.content_stack.addWidget(page)
