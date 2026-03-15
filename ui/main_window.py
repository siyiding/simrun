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
    QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
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


class SidebarButton(QPushButton):
    """侧边栏导航按钮"""
    def __init__(self, text, icon, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self._set_style()
        
    def _set_style(self):
        style = f"""
            QPushButton {
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: {COLORS['sidebar_hover']};
                color: {COLORS['text_primary']};
            }
        """
        self.setStyleSheet(style)


class MainWindow(QMainWindow):
    """主窗口 - 侧边栏 + 主内容区布局"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🍀 股票预测助手")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 600)
        
        self._apply_dark_theme()
        self._init_ui()
        self.statusBar().showMessage("✅ 系统就绪 | 📊 模型未加载 | 💰 账户: ¥1,000,000")
    
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
        content_widget.setStyleSheet(f"background-color: {COLORS['bg_primary']};")
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
        sidebar.setStyleSheet(f"QWidget {{ background-color: {COLORS['sidebar_bg']}; }}")
        
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
        self.nav_buttons[0].setStyleSheet(f"QPushButton {{ background-color: {COLORS['sidebar_active']}; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; text-align: left; font-weight: 600; }}")
        
        layout.addStretch()
        
        # 版本
        status_label = QLabel("v1.0.0")
        status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; padding: 8px 12px;")
        layout.addWidget(status_label)
        
        return sidebar
    
    def _on_nav_clicked(self, page_name):
        page_map = {"首页": 0, "数据": 1, "模型": 2, "回测": 3, "设置": 4}
        idx = page_map.get(page_name, 0)
        
        for i, btn in enumerate(self.nav_buttons):
            if i == idx:
                btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['sidebar_active']}; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; text-align: left; font-weight: 600; }}")
            else:
                btn.setStyleSheet(f"QPushButton {{ background-color: transparent; color: {COLORS['text_secondary']}; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; text-align: left; }} QPushButton:hover {{ background-color: {COLORS['sidebar_hover']}; color: white; }}")
        
        self.content_stack.setCurrentIndex(idx)
    
    def _create_card(self, title=""):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 16px; }}")
        
        if title:
            layout = QVBoxLayout(card)
            title_label = QLabel(title)
            title_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS['accent']}; margin-bottom: 12px;")
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
        
        # 快速操作
        quick_card = self._create_card("⚡ 快速操作")
        quick_layout = QHBoxLayout(quick_card)
        quick_layout.setSpacing(12)
        
        for text, target in [("📥 获取数据", "数据"), ("🧠 训练模型", "模型"), ("📈 开始回测", "回测")]:
            btn = QPushButton(text)
            btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['accent']}; border-radius: 8px; padding: 10px 20px; font-weight: 600; }} QPushButton:hover {{ background-color: {COLORS['accent']}; }}")
            btn.clicked.connect(lambda checked, n=target: self._on_nav_clicked(n))
            quick_layout.addWidget(btn)
        
        quick_layout.addStretch()
        layout.addWidget(quick_card)
        
        layout.addStretch()
        self.content_stack.addWidget(page)
    
    def _create_metric_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 20px; min-width: 180px; }}")
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700;")
        layout.addWidget(value_label)
        
        return card
    
    def _create_signal_row(self, code, action, conf, t):
        widget = QWidget()
        widget.setStyleSheet(f"background-color: #2A2A3E; border-radius: 8px; padding: 12px;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        
        code_label = QLabel(code)
        code_label.setStyleSheet("font-weight: 600; min-width: 80px;")
        layout.addWidget(code_label)
        
        action_label = QLabel(action)
        action_color = COLORS['success'] if action == "买入" else (COLORS['error'] if action == "卖出" else COLORS['warning'])
        action_label.setStyleSheet(f"color: {action_color}; font-weight: 600; min-width: 50px;")
        layout.addWidget(action_label)
        
        conf_label = QLabel(conf)
        conf_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(conf_label)
        
        layout.addStretch()
        
        time_label = QLabel(t)
        time_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
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
        train_info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        train_layout.addWidget(train_info)
        
        self.train_progress = QProgressBar()
        self.train_progress.setValue(80)
        train_layout.addWidget(self.train_progress)
        
        progress_label = QLabel("训练进度：████████████░░░░░░ 80%")
        progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        train_layout.addWidget(progress_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        start_btn = QPushButton("▶️ 开始训练")
        start_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['success']}; }}")
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
        start_bt_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['success']}; }}")
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
            m_card.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_secondary']}; border-radius: 8px; padding: 12px; min-width: 100px; }}")
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
