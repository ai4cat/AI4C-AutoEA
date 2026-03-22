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

class AllDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Full Data Display")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ['ShowAll', 'Color', 'Original Name', 'Label Name', 'E10/η10', 'E100/η100', 'Test Type'])

        # 在表格初始化时设置行高
        self.table.verticalHeader().setDefaultSectionSize(40)
        # 设置列宽
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 85)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 90)

        # 创建表头小部件
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setStretchLastSection(False)

        header = self.table.horizontalHeader()
        header.sectionClicked.connect(self.on_header_clicked)  # 添加列头点击事件
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #2c313c;
                color: white;
                padding: 5px;
                border: none;
            }
            QHeaderView::section:first {
                background-color: #4CAF50;  /* 初始绿色表示全部显示 */
                border-radius: 3px;
                margin: 2px;
            }
            QHeaderView::section:first:hover {
                background-color: #45a049;
            }
        """)

        # 设置表格样式
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: black;
                border: 1px solid #d0d0d0;
                gridline-color: #d0d0d0;
            }
            QTableWidget::item {
                border: 1px solid #d0d0d0;
                padding: 1px;
            }
            QTableWidget::item:selected {
                background-color: #42a5f5;
                color: white;
            }
        """)

        # 连接表格事件
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # 添加到布局
        layout.addWidget(self.table)

        # 添加关闭按钮
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: black;
                border: 1px solid #d0d0d0;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def toggle_all_curves(self):
        """切换所有曲线的显示状态"""
        checked = self.header_toggle_button.isChecked()

        # 更新所有行的按钮状态
        for row in range(self.table.rowCount()):
            button_container = self.table.cellWidget(row, 0)
            if button_container:
                button = button_container.findChild(QPushButton)
                if button:
                    button.setChecked(checked)
                    # 同步更新主窗口的显示状态
                    main_button = self.parent().curve_table.cellWidget(row, 0).findChild(QPushButton)
                    if main_button:
                        main_button.setChecked(checked)

        # 同步更新主窗口的显示按钮状态
        self.parent.header_toggle_button.setChecked(checked)

    def show_all_data(self):
        """处理ALL按钮点击事件"""
        # 这里可以添加额外的功能，如果需要的话
        pass

    def populate_data(self, main_table):
        """从主窗口的表格复制数据"""
        # 获取主窗口当前测试类型
        current_test_type = self.parent().test_combo.currentText()

        # 动态设置列头
        if current_test_type == "ORR":
            headers = ['ShowAll', 'Color', 'Original Name', 'Label', 'Onset\nPotential', 'Half-wave\nPotential', 'Test Type']
        else:
            headers = ['ShowAll', 'Color', 'Original Name', 'Label', 'E10/η10', 'E100/η100', 'Test Type']

        self.table.setHorizontalHeaderLabels(headers)

        self.table.setRowCount(0)
        self.plot_lines = []  # 存储曲线信息

        # 暂时断开 cellChanged 信号连接，避免触发不必要的更新
        self.table.cellChanged.disconnect(self.on_cell_changed)

        for row in range(main_table.rowCount()):
            self.table.insertRow(row)

            # 复制显示按钮
            button_container = main_table.cellWidget(row, 0)
            if button_container:
                new_container = QWidget()
                new_layout = QHBoxLayout(new_container)
                new_layout.setContentsMargins(0, 0, 0, 0)
                new_layout.setAlignment(Qt.AlignCenter)

                toggle_button = QPushButton()
                toggle_button.setCheckable(True)
                toggle_button.setChecked(button_container.findChild(QPushButton).isChecked())
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
                toggle_button.toggled.connect(lambda checked, r=row: self.toggle_curve_visibility(r, checked))
                new_layout.addWidget(toggle_button)
                self.table.setCellWidget(row, 0, new_container)

            # 复制颜色显示
            color_widget = main_table.cellWidget(row, 1)
            if color_widget:
                new_color_widget = QWidget()
                new_color_widget.setStyleSheet(color_widget.styleSheet())
                self.table.setCellWidget(row, 1, new_color_widget)

            # 复制其他列的数据
            for col in range(2, main_table.columnCount()):
                item = main_table.item(row, col)
                if item:
                    new_item = QTableWidgetItem(item.text())
                    # 只有标签名称列可编辑
                    if col == 3:
                        new_item.setFlags(item.flags())
                    else:
                        new_item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row, col, new_item)

            # E10/η10列
            e10_item = QTableWidgetItem(main_table.item(row, 4).text())
            e10_item.setTextAlignment(Qt.AlignCenter)  # 新增居中
            e10_item.setFlags(e10_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, e10_item)

            # E100/η100列
            e100_item = QTableWidgetItem(main_table.item(row, 5).text())
            e100_item.setTextAlignment(Qt.AlignCenter)  # 新增居中
            e100_item.setFlags(e100_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, e100_item)

            # Test Type列
            test_type_item = QTableWidgetItem(main_table.item(row, 6).text())
            test_type_item.setTextAlignment(Qt.AlignCenter)  # 新增居中
            test_type_item.setFlags(test_type_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 6, test_type_item)

            # 保存曲线信息
            if hasattr(self.parent(), 'plot_lines') and row < len(self.parent().plot_lines):
                self.plot_lines.append(self.parent().plot_lines[row].copy())

        # 重新连接 cellChanged 信号
        self.table.cellChanged.connect(self.on_cell_changed)

    def on_cell_double_clicked(self, row, column):
        """处理单元格双击事件"""
        if column == 1:  # 颜色列
            color = QColorDialog.getColor()
            if color.isValid() and hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                color_name = color.name()

                # 更新表格中的颜色显示
                color_widget = QWidget()
                color_widget.setFixedHeight(40)
                color_widget.setStyleSheet(f"background-color: {color_name};")
                self.table.setCellWidget(row, 1, color_widget)

                # 更新主窗口的颜色显示
                self.parent().curve_table.cellWidget(row, 1).setStyleSheet(f"background-color: {color_name};")

                # 更新曲线颜色
                self.parent().plot_lines[row]['color'] = color_name
                line = self.parent().plot_lines[row]['line']
                if line.get_visible():
                    line.set_color(color_name)
                    self.parent().canvas.draw()

    def on_cell_changed(self, row, column):
        """处理单元格内容改变事件"""
        if column == 3:  # 标签名称列
            if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                # 获取新的标签名称
                new_label = self.table.item(row, column).text()

                # 更新主窗口的标签名称
                self.parent().curve_table.item(row, column).setText(new_label)

                # 更新曲线标签
                curve_info = self.parent().plot_lines[row]
                curve_info['label_name'] = new_label

                # 更新曲线标签和图例
                line = curve_info['line']
                if line.get_visible():
                    line.set_label(new_label)
                    self.parent().ax.legend()
                    self.parent().canvas.draw()

    def on_cell_clicked(self, row, column):
        """处理单元格点击事件"""
        if column == 2:  # 样品原名称列
            # 通过父窗口引用调用主窗口方法
            self.parent().update_data_display(
                self.table.item(row, 3).text(),
                float(self.table.item(row, 4).text()) if self.table.item(row, 4).text() not in ["N/A", ""] else None,
                float(self.table.item(row, 5).text()) if self.table.item(row, 5).text() not in ["N/A", ""] else None
            )

            # 高亮显示对应的曲线
            if hasattr(self.parent(), 'plot_lines') and row < len(self.parent().plot_lines):
                curve_info = self.parent().plot_lines[row]

                # 遍历所有曲线
                for line in self.parent().ax.lines:
                    # 跳过参考线
                    if line.get_linestyle() == '--':
                        line.set_linewidth(1)  # 确保参考线始终保持宽度为1
                        continue

                    # 使用曲线对象直接比较
                    if line == curve_info['line']:
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(3)

                        # 获取曲线标签和性能数据
                        label = self.table.item(row, 3).text()
                        e10 = self.table.item(row, 4).text()
                        e100 = self.table.item(row, 5).text()

                    else:
                        line.set_linewidth(1)
                        line.set_alpha(0.3)
                        line.set_zorder(1)

                self.parent().canvas.draw()

    def toggle_curve_visibility(self, row, checked):
        """切换曲线显示状态"""
        # 获取主窗口引用
        main_window = self.parent()
        # 同步更新主窗口的显示状态
        main_button = main_window.curve_table.cellWidget(row, 0).findChild(QPushButton)
        if main_button.isChecked() != checked:
            main_button.setChecked(checked)
            main_window.toggle_curve_visibility(row, checked)

        # 更新表头状态
        all_checked = all(
            self.table.cellWidget(r, 0).findChild(QPushButton).isChecked()
            for r in range(self.table.rowCount())
        )
        header = self.table.horizontalHeader()

    def on_header_clicked(self, logical_index):
        if logical_index == 0:  # 点击"ShowAll"列头
            current_state = all(
                self.table.cellWidget(r, 0).findChild(QPushButton).isChecked()
                for r in range(self.table.rowCount()))
            new_state = not current_state

            # 更新所有行的按钮状态
            for row in range(self.table.rowCount()):
                button = self.table.cellWidget(row, 0).findChild(QPushButton)
                button.setChecked(new_state)

            # 同步到主窗口
            main_window = self.parent()
            for row in range(main_window.curve_table.rowCount()):
                main_button = main_window.curve_table.cellWidget(row, 0).findChild(QPushButton)
                main_button.setChecked(new_state)

    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        column = self.table.columnAt(position.x())

        if column == 3:  # 标签名称列
            menu = QMenu(self)

            # 字体设置子菜单
            font_menu = menu.addMenu("Font Settings")

            # 添加恢复默认选项
            reset_action = font_menu.addAction("Reset Default")
            reset_action.triggered.connect(lambda: self.parent().reset_label_font(row))
            font_menu.addSeparator()

            # 字体大小子菜单
            font_size_menu = font_menu.addMenu("Font Size")
            for size in [8, 10, 12, 14, 16, 18, 20]:
                action = font_size_menu.addAction(f"{size}pt")
                action.triggered.connect(lambda checked, s=size: self.parent().set_label_font_size(row, s))

            # 字体样式子菜单
            font_style_menu = font_menu.addMenu("Font Style")
            styles = {
                "Normal": "normal",
                "Bold": "bold",
                "Italic": "italic",
                "Bold Italic": "bold italic"
            }
            for style_name, style in styles.items():
                action = font_style_menu.addAction(style_name)
                action.triggered.connect(lambda checked, s=style: self.parent().set_label_font_style(row, s))

            # 上下标子菜单
            script_menu = menu.addMenu("Superscript/Subscript")
            superscript_action = script_menu.addAction("Add Superscript")
            superscript_action.triggered.connect(lambda: self.parent().add_script(row, "super"))
            subscript_action = script_menu.addAction("Add Subscript")
            subscript_action.triggered.connect(lambda: self.parent().add_script(row, "sub"))

            menu.exec(self.table.viewport().mapToGlobal(position))