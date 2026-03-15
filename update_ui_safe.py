with open('ui/main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add QProgressBar import if not there
if 'QProgressBar' not in content:
    content = content.replace('QTextEdit, QMessageBox)', 'QTextEdit, QMessageBox, QProgressBar)')

worker_original = '''class ScriptWorkerThread(QThread):
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
            _task_running = False'''

worker_replacement = '''class ScriptWorkerThread(QThread):
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
            _task_running = False'''

content = content.replace(worker_original, worker_replacement)

# Add progress bar to data tab
content = content.replace('''        self.btn_download.clicked.connect(self.on_start_data)
        self.btn_download.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_download)
        layout.addLayout(btn_layout)
        
        self.data_log_output = QTextEdit()''', '''        self.btn_download.clicked.connect(self.on_start_data)
        self.btn_download.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_download)
        layout.addLayout(btn_layout)
        
        self.data_progress = QProgressBar()
        self.data_progress.setRange(0, 100)
        self.data_progress.setValue(0)
        self.data_progress.setTextVisible(True)
        self.data_progress.setStyleSheet("QProgressBar { border: 1px solid grey; border-radius: 3px; text-align: center; } QProgressBar::chunk { background-color: #4CAF50; width: 10px; }")
        layout.addWidget(self.data_progress)
        
        self.data_log_output = QTextEdit()''')


# Add progress bar to training tab
content = content.replace('''        self.btn_train.clicked.connect(self.on_start_training)
        self.btn_train.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_train)
        layout.addLayout(btn_layout)
        
        self.log_output = QTextEdit()''', '''        self.btn_train.clicked.connect(self.on_start_training)
        self.btn_train.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_train)
        layout.addLayout(btn_layout)
        
        self.train_progress = QProgressBar()
        self.train_progress.setRange(0, 100)
        self.train_progress.setValue(0)
        self.train_progress.setTextVisible(True)
        self.train_progress.setStyleSheet("QProgressBar { border: 1px solid grey; border-radius: 3px; text-align: center; } QProgressBar::chunk { background-color: #2196F3; width: 10px; }")
        layout.addWidget(self.train_progress)
        
        self.log_output = QTextEdit()''')


# Add progress bar to backtest tab
content = content.replace('''        self.btn_run_bt.clicked.connect(self.on_run_backtest)
        self.btn_run_bt.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_run_bt)
        layout.addLayout(btn_layout)
        
        self.bt_log_output = QTextEdit()''', '''        self.btn_run_bt.clicked.connect(self.on_run_backtest)
        self.btn_run_bt.setMinimumHeight(40)
        btn_layout.addWidget(self.btn_run_bt)
        layout.addLayout(btn_layout)
        
        self.bt_progress = QProgressBar()
        self.bt_progress.setRange(0, 100)
        self.bt_progress.setValue(0)
        self.bt_progress.setTextVisible(True)
        self.bt_progress.setStyleSheet("QProgressBar { border: 1px solid grey; border-radius: 3px; text-align: center; } QProgressBar::chunk { background-color: #FF9800; width: 10px; }")
        layout.addWidget(self.bt_progress)
        
        self.bt_log_output = QTextEdit()''')


# Update signal connections in actions
content = content.replace('''        self.data_worker = ScriptWorkerThread(script)
        self.data_worker.update_signal.connect(lambda msg: self.append_log(self.data_log_output, msg))
        self.data_worker.finished_signal.connect(self._on_data_finished)''', '''        self.data_progress.setValue(0)
        self.data_worker = ScriptWorkerThread(script)
        self.data_worker.update_signal.connect(lambda msg: self.append_log(self.data_log_output, msg))
        self.data_worker.progress_signal.connect(self.data_progress.setValue)
        self.data_worker.finished_signal.connect(self._on_data_finished)''')

content = content.replace('''        self.train_worker = ScriptWorkerThread(script)
        self.train_worker.update_signal.connect(lambda msg: self.append_log(self.log_output, msg))
        self.train_worker.finished_signal.connect(self._on_training_finished)''', '''        self.train_progress.setValue(0)
        self.train_worker = ScriptWorkerThread(script)
        self.train_worker.update_signal.connect(lambda msg: self.append_log(self.log_output, msg))
        self.train_worker.progress_signal.connect(self.train_progress.setValue)
        self.train_worker.finished_signal.connect(self._on_training_finished)''')

content = content.replace('''        self.bt_worker = ScriptWorkerThread("backtest_engine.py")
        self.bt_worker.update_signal.connect(lambda msg: self.append_log(self.bt_log_output, msg))
        self.bt_worker.finished_signal.connect(self._on_bt_finished)''', '''        self.bt_progress.setValue(0)
        self.bt_worker = ScriptWorkerThread("backtest_engine.py")
        self.bt_worker.update_signal.connect(lambda msg: self.append_log(self.bt_log_output, msg))
        self.bt_worker.progress_signal.connect(self.bt_progress.setValue)
        self.bt_worker.finished_signal.connect(self._on_bt_finished)''')

with open('ui/main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)
