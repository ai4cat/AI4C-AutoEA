from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QFormLayout,QGridLayout,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,QFileDialog,
    QMessageBox, QMenu, QColorDialog, QInputDialog, QDialog,QSizePolicy
)
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QPalette, QColor,QFont
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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, NullLocator

class CurveLSV(QMainWindow):
    def __init__(self):
        super().__init__()

    def clear_all(self):
        """清空所有曲线和表格数据"""
        # 清空图表
        self.ax.clear()

        # 重置图表设置
        self.update_plot_settings()

        # 清空表格
        self.curve_table.setRowCount(0)

        # 清空曲线数据
        if hasattr(self, 'plot_lines'):
            self.plot_lines = []

        # 重绘画布
        self.canvas.draw()

    def add_curve_to_table(self, sample_name, color, line_ref):
        """添加曲线到表格并处理显示"""
        row = self.curve_table.rowCount()
        self.curve_table.insertRow(row)

        # 创建显示按钮
        toggle_button = QPushButton()
        toggle_button.setCheckable(True)
        toggle_button.setChecked(True)
        toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border-radius: 10px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
            QPushButton:!checked {
                background-color: #808080;
            }
        """)

        # 创建按钮容器
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(toggle_button)

        # 添加到表格
        self.curve_table.setCellWidget(row, 0, button_container)  # 显示按钮列

        # 添加颜色显示
        color_widget = QWidget()
        color_widget.setStyleSheet(f"background-color: {color};")
        self.curve_table.setCellWidget(row, 1, color_widget)  # 颜色列

        # 添加样品原名称（不可编辑）
        original_name_item = QTableWidgetItem(sample_name)
        original_name_item.setFlags(original_name_item.flags() & ~Qt.ItemIsEditable)
        self.curve_table.setItem(row, 2, original_name_item)  # 样品原名称列

        # 添加标签名称（可编辑）
        label_name_item = QTableWidgetItem(sample_name)
        self.curve_table.setItem(row, 3, label_name_item)  # 标签名称列

        # 添加E10/η10和E100/η100列（初始为空）
        e10_item = QTableWidgetItem("")
        e10_item.setTextAlignment(Qt.AlignCenter)  # 居中设置
        self.curve_table.setItem(row, 4, e10_item)
        e100_item = QTableWidgetItem("")
        e100_item.setTextAlignment(Qt.AlignCenter)  # 居中设置
        self.curve_table.setItem(row, 5, e100_item)

        # 添加测试类型（不可编辑）
        test_type_item = QTableWidgetItem(self.test_combo.currentText())
        test_type_item.setTextAlignment(Qt.AlignCenter)  # 居中设置
        test_type_item.setFlags(test_type_item.flags() & ~Qt.ItemIsEditable)
        self.curve_table.setItem(row, 6, test_type_item)  # 测试类型列

        # 保存曲线信息
        if not hasattr(self, 'plot_lines'):
            self.plot_lines = []

        self.plot_lines.append({
            'line': line_ref,
            'toggle_button': toggle_button,
            'color': color,
            'original_name': sample_name,
            'label_name': sample_name,
            'visible': True,
            'x_data': line_ref.get_xdata(),
            'y_data': line_ref.get_ydata(),
            'linewidth': line_ref.get_linewidth(),
            'test_type': self.test_combo.currentText()  # 添加测试类型信息
        })

        # 连接按钮事件
        toggle_button.toggled.connect(lambda checked, r=row: self.toggle_curve_visibility(r, checked))

