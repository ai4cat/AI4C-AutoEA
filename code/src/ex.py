# Qt相关导入
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QFormLayout,QGridLayout,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,QFileDialog,
    QMessageBox, QMenu, QColorDialog, QInputDialog, QDialog,QSizePolicy
)
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QPalette, QColor,QFont


# 系统相关导入
import sys
import os
import shutil
from datetime import datetime
import csv
import re
from collections import defaultdict
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# matplotlib相关导入
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, NullLocator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()


        # 创建主widget和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        # 创建左侧区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(20, 0, 10, 10)

        # 设置左侧区域宽度
        left_widget.setFixedWidth(800)

        # 创建右半部分的容器
        right_container = QWidget()
        right_container_layout = QVBoxLayout(right_container)
        right_container_layout.setSpacing(15)

        # 创建中右布局的上半部分容器
        upper_container = QWidget()
        upper_layout = QHBoxLayout(upper_container)
        upper_layout.setSpacing(15)

        # 创建中间和右侧区域
        center_widget = QWidget()
        right_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        right_layout = QVBoxLayout(right_widget)

        # 先创建参数设置组（包含test_combo）
        self.create_parameter_group(center_layout)
        self.create_data_group(center_layout)

        # 添加按钮区域
        self.create_button_group(right_layout)

        # 设置区域宽度
        center_widget.setFixedWidth(350)
        right_widget.setFixedWidth(170)

        # 将中间和右侧区域添加到上半部分
        upper_layout.addWidget(center_widget)
        upper_layout.addWidget(right_widget)

        # 创建注释说明区域（放在下方）
        note_container = QWidget()
        note_layout = QHBoxLayout(note_container)
        self.create_note_area(note_layout)

        # 将所有部分添加到右容器
        right_container_layout.addWidget(upper_container)
        right_container_layout.addWidget(note_container)

        # 创建LSV图表区域（现在test_combo已经创建好了）
        plot_container = QWidget()
        plot_container.setFixedHeight(750)
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.create_plot_area(plot_layout)
        left_layout.addWidget(plot_container)
        self.legend_visible = True  # 默认显示图例

        # 添加到主布局
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_container)

        # 连接换算按钮信号
        self.area_btn.clicked.connect(self.change_current)

        # 根据当前测试类型选择参数
        current_test_type = self.defaults.get('test_options0', 'UOR')
        self.test_combo.setCurrentText(current_test_type)
        # 初始化参数
        self.update_parameters(current_test_type)  # 初始加载参数
        self.update_interface_settings()
        self.update_button_visibility(current_test_type)  # 确保按钮可见性正确

        self.test_combo.currentTextChanged.connect(
            lambda: self.update_button_visibility(self.test_combo.currentText()))






