# python 3.13
# -*- coding: utf-8 -*-
# 封装命令：pyinstaller -D -i t.ico --exclude-module tkinter --exclude-module unittest --upx-dir ~/upx-3.96 --add-data "t.ico;." --hidden-import "pandas_libs.tslibs.timedeltas" --clean Calculate_LSV-3.0.py
# 版权：北航-吴凯

from PySide6.QtWidgets import QApplication, QMainWindow
import sys
from sc.ex import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())
