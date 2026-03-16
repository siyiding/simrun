import sys

import matplotlib
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

# 全局设置 Matplotlib 中文字体，避免中文乱码/缺字
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
