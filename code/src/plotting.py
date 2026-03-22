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

class Plot_GUI(QMainWindow):
    def __init__(self):
        super().__init__()

    def create_plot_area(self, layout):

        """创建LSV图表区域"""
        # 设置全局字体为 Times New Roman/Arial
        #plt.rcParams['font.family'] = ['Times New Roman', 'SimHei']  # 添加中文字体
        plt.rcParams['font.family'] = ['Arial']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        plt.rcParams['text.usetex'] = False
        plt.rcParams['mathtext.fontset'] = 'stix'

        # 创建matplotlib图形
        self.figure = Figure(figsize=(8, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # 修改工具栏创建部分
        toolbar_container = QWidget()
        toolbar_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(2)  # 控制按钮间距

        # 添加工具栏
        toolbar = NavigationToolbar(self.canvas, None)
        toolbar.setStyleSheet(
            "QToolButton { min-width: 18px; max-width: 18px; min-height: 20px; max-height: 20px; padding: 1px; }")
        toolbar.setIconSize(QSize(19, 19))

        # 调整工具栏布局间距
        toolbar.layout().setSpacing(2)

        # 修改工具栏提示文本
        for action in toolbar.actions():
            if action.text() == 'Home':
                action.setToolTip('Reset original view')
            elif action.text() == 'Back':
                action.setToolTip('Back to previous view')
            elif action.text() == 'Forward':
                action.setToolTip('Forward to next view')
            elif action.text() == 'Pan':
                action.setToolTip('Pan axes with left mouse, zoom with right')
            elif action.text() == 'Zoom':
                action.setToolTip('Zoom to rectangle')
            elif action.text() == 'Subplots':
                action.setToolTip('Configure subplots')
            elif action.text() == 'Customize':
                action.setToolTip('Edit axis, curve parameters')
            elif action.text() == 'Save':
                action.setToolTip('Save the figure')

        # 设置工具栏样式
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
            }
            QToolBar::separator {
                width: 0;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)

        # 创建重置视图按钮
        reset_button = QPushButton("Reset View")
        reset_button.clicked.connect(self.reset_view)
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #2c313c;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3c424f;
            }
        """)

        # 创建保存按钮
        save_button = QPushButton("Save Table")
        save_button.setStyleSheet("""
                QPushButton {
                    background-color: #2c313c;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #3c424f;
                }
            """)
        # 暂时不连接任何功能
        save_button.clicked.connect(self.save_selected_curves)

        # 创建清空按钮
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_all)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #2c313c;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3c424f;
            }
        """)

        # 创建网格切换按钮
        grid_button = QPushButton("Grid")
        grid_button.setCheckable(True)
        grid_button.setChecked(True)
        grid_button.clicked.connect(self.toggle_grid)
        grid_button.setStyleSheet("""
               QPushButton {
                   background-color: #2c313c;
                   color: white;
                   border: none;
                   padding: 5px 10px;
                   border-radius: 3px;
                   min-width: 20px;
               }
               QPushButton:checked {
                   background-color: #3c424f;
               }
               QPushButton:hover {
                   background-color: #3c424f;
               }
           """)
        self.grid_button = grid_button

        # 创建ALL按钮并添加到工具栏
        self.all_button = QPushButton("ALL")
        #self.all_button.setFixedSize(10, 25)
        self.all_button.setStyleSheet("""
            QPushButton {
                background-color: #FF4444;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                min-width: 20px;
            }
            QPushButton:hover {
                background-color: #3c424f;
            }
        """)

        # 创建标签切换按钮
        label_button = QPushButton("Legend")
        label_button.setCheckable(True)
        label_button.setChecked(True)
        label_button.clicked.connect(self.toggle_legend)
        label_button.setStyleSheet("""
               QPushButton {
                   background-color: #2c313c;
                   color: white;
                   border: none;
                   padding: 5px 10px;
                   border-radius: 3px;
                   min-width: 35px;
               }
               QPushButton:checked {
                   background-color: #3c424f;
               }
               QPushButton:hover {
                   background-color: #3c424f;
               }
           """)
        self.label_button = label_button  # 保存按钮引用

        # 创建工具栏组件
        toolbar_layout.addWidget(toolbar)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.all_button) # ALL按钮
        toolbar_layout.addWidget(label_button)  # 标签按钮
        toolbar_layout.addWidget(grid_button)  # 网格按钮
        toolbar_layout.addWidget(clear_button)  # 清空按钮
        toolbar_layout.addWidget(reset_button)  # 重置按钮
        toolbar_layout.addWidget(save_button)  # 保存按钮

        # 创建表格
        self.curve_table = QTableWidget()
        self.curve_table.setMinimumHeight(130)
        self.curve_table.setMaximumHeight(150)
        self.curve_table.setColumnCount(7)

        # 创建表头
        header = self.curve_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setStretchLastSection(False)
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

        # 创建表头小部件
        header_widget = QWidget()
        header_widget.setFixedHeight(40)  # 设置固定高度
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)  # 部件间距为0
        self.all_button.clicked.connect(self.show_all_data)

        # 添加按钮到布局
        header_layout.setAlignment(Qt.AlignCenter)

        # 使用代理部件
        proxy = QWidget()
        proxy.setFixedHeight(25)
        proxy_layout = QHBoxLayout(proxy)
        proxy_layout.setContentsMargins(0, 0, 0, 0)
        proxy_layout.setSpacing(0)
        proxy_layout.addWidget(header_widget)

        # 设置代理部件为表头
        header = self.curve_table.horizontalHeader()
        header.viewport().stackUnder(proxy)
        proxy.setParent(header)
        proxy.setGeometry(header.sectionPosition(0), 0, header.sectionSize(0), header.height())
        proxy.show()

        # 设置表头标签
        # 直接调用更新方法
        self.update_table_headers()

        # 设置列宽
        self.curve_table.setColumnWidth(0, 70)  # 显示按钮列
        self.curve_table.setColumnWidth(1, 80)  # 颜色列
        self.curve_table.setColumnWidth(2, 150)  # 样品原名称列
        self.curve_table.setColumnWidth(3, 150)  # 标签名称列
        self.curve_table.setColumnWidth(4, 95)  # E10/η10列 起始电位
        self.curve_table.setColumnWidth(5, 95)  # E100/η100列 半波电位
        self.curve_table.setColumnWidth(6, 80)  # 测试类型列

        # 设置表格样式
        self.curve_table.setStyleSheet("""
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
                    QHeaderView::section {
                        background-color: #f0f0f0;
                        color: black;
                        padding: 5px;
                        border: 1px solid #d0d0d0;
                    }
                """)


        # 设置初始图表属性
        self.update_plot_settings()
        # 表头点击事件
        self.curve_table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

        # 修改曲线点击事件处理
        def on_pick(event):
            if event.artist in self.ax.lines:
                selected_line = event.artist
                # 遍历所有曲线
                for line in self.ax.lines:
                    # 跳过参考线
                    if line.get_linestyle() == '--':
                        continue

                    if line == selected_line:
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(3)
                    else:
                        line.set_linewidth(1)
                        line.set_alpha(0.3)
                        line.set_zorder(1)

                self.canvas.draw()
                # 阻止事件继续传播
                event.canvas.stop_event_loop()

        # 修改画布点击事件处理
        def on_canvas_click(event):
            if event.inaxes:  # 点击在图表区域内
                clicked_line = None
                for line in self.ax.lines:
                    if line.get_linestyle() == '--':  # 跳过参考线
                        line.set_linewidth(1)  # 确保参考线始终保持宽度为1
                        continue

                    # 获取曲线数据点
                    xdata = line.get_xdata()
                    ydata = line.get_ydata()

                    # 检查点击位置是否接近曲线
                    for i in range(len(xdata) - 1):
                        dist = point_to_line_distance(event.xdata, event.ydata,
                                                      xdata[i], ydata[i],
                                                      xdata[i + 1], ydata[i + 1])
                        if dist < 0.01:  # 可调整判定灵敏度
                            clicked_line = line
                            break
                    if clicked_line:
                        break

                if clicked_line:  # 点击到了曲线
                    # 高亮被点击的曲线
                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            line.set_linewidth(1)  # 保持参考线宽度为1
                            continue

                        if line == clicked_line:
                            line.set_linewidth(2)
                            line.set_alpha(1.0)
                            line.set_zorder(3)

                            # 查找对应的表格行
                            for row in range(self.curve_table.rowCount()):
                                if self.plot_lines[row]['line'] == line:
                                    # 直接从表格读取性能数据
                                    label = self.curve_table.item(row, 3).text()  # 标签名称
                                    e10 = self.curve_table.item(row, 4).text()  # E10/η10
                                    e100 = self.curve_table.item(row, 5).text()  # E100/η100

                                    # 显示信息
                                    self.update_data_display(
                                        label,
                                        float(e10) if e10 not in ["N/A", ""] else None,
                                        float(e100) if e100 not in ["N/A", ""] else None
                                    )
                                    break

                        else:
                            line.set_linewidth(1)
                            line.set_alpha(0.3)
                            line.set_zorder(1)
                else:  # 点击空白区域
                    # 恢复所有曲线状态
                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            line.set_linewidth(1)  # 保持参考线宽度为1
                            continue
                        line.set_linewidth(1)
                        line.set_alpha(1.0)
                        line.set_zorder(2)
                    self.ax.set_title('')

            else:  # 点击图表外
                # 恢复所有曲线状态
                for line in self.ax.lines:
                    if line.get_linestyle() == '--':
                        line.set_linewidth(1)  # 保持参考线宽度为1
                        continue
                    line.set_linewidth(1)
                    line.set_alpha(1.0)
                    line.set_zorder(2)
                self.ax.set_title('')

            self.canvas.draw()

            # 添加辅助函数：计算点到线段的距离

        def point_to_line_distance(px, py, x1, y1, x2, y2):
            # 计算线段长度的平方
            l2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
            if l2 == 0:
                return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5

            # 计算投影点参数 t
            t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2))

            # 计算投影点坐标
            proj_x = x1 + t * (x2 - x1)
            proj_y = y1 + t * (y2 - y1)

            # 返回点到投影点的距离
            return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

        # 修改表格点击事件处理
        def on_table_clicked(row, column):
            if column == 2:  # 样品原名称列
                # 获取曲线数据
                curve_info = self.plot_lines[row]
                # 遍历所有曲线
                for line in self.ax.lines:
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
                        label = self.curve_table.item(row, 3).text()
                        e10 = self.curve_table.item(row, 4).text()
                        e100 = self.curve_table.item(row, 5).text()

                        # 显示信息
                        self.update_data_display(
                            label,
                            float(e10) if e10 not in ["N/A", ""] else None,
                            float(e100) if e100 not in ["N/A", ""] else None
                        )

                    else:
                        line.set_linewidth(1)
                        line.set_alpha(0.3)
                        line.set_zorder(1)

                self.canvas.draw()
            else:
                # 点击其他列时恢复所有曲线状态
                for line in self.ax.lines:
                    if line.get_linestyle() == '--':
                        continue

                    line.set_linewidth(1)
                    line.set_alpha(1.0)
                    line.set_zorder(2)
                    self.ax.set_title('')

                self.canvas.draw()

        # 连接事件
        self.canvas.mpl_connect('pick_event', on_pick)
        self.canvas.mpl_connect('button_press_event', on_canvas_click)
        self.curve_table.cellClicked.connect(on_table_clicked)

        # 添加状态标志和当前高亮曲线索引
        self.zoom_enabled = False
        self.current_highlight_index = None

        def on_mouse_middle_click(event):
            if event.button == 2:  # 中键点击
                self.zoom_enabled = not self.zoom_enabled
                if not self.zoom_enabled:
                    # 退出缩放模式时重置当前高亮索引
                    self.current_highlight_index = None
                    # 恢复所有曲线状态
                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            continue
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(2)
                    self.canvas.draw()

        def on_scroll(event):
            if self.zoom_enabled:
                # 缩放模式下的处理逻辑保持不变
                if not event.inaxes:
                    return

                cur_xlim = self.ax.get_xlim()
                cur_ylim = self.ax.get_ylim()
                xdata = event.xdata
                ydata = event.ydata
                base_scale = 1.1
                scale = base_scale if event.button == 'up' else 1 / base_scale

                x_left = xdata - (xdata - cur_xlim[0]) * scale
                x_right = xdata + (cur_xlim[1] - xdata) * scale
                y_bottom = ydata - (ydata - cur_ylim[0]) * scale
                y_top = ydata + (cur_ylim[1] - ydata) * scale

                self.ax.set_xlim(x_left, x_right)
                self.ax.set_ylim(y_bottom, y_top)

            else:
                # 非缩放模式下切换高亮曲线
                data_lines = [line for line in self.ax.lines if line.get_linestyle() != '--']
                if not data_lines:
                    return

                # 确定下一个要高亮的曲线索引
                if self.current_highlight_index is None:
                    self.current_highlight_index = 0 if event.button == 'up' else len(data_lines) - 1
                else:
                    if event.button == 'up':
                        self.current_highlight_index = (self.current_highlight_index + 1) % len(data_lines)
                    else:
                        self.current_highlight_index = (self.current_highlight_index - 1) % len(data_lines)

                # 更新曲线显示状态
                for i, line in enumerate(data_lines):
                    if i == self.current_highlight_index:
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(3)

                        # 在表格中查找对应的性能数据
                        for row in range(self.curve_table.rowCount()):
                            if self.plot_lines[row]['line'] == line:
                                label = self.curve_table.item(row, 3).text()
                                e10 = self.curve_table.item(row, 4).text()
                                e100 = self.curve_table.item(row, 5).text()

                                # 显示信息
                                self.update_data_display(
                                    label,
                                    float(e10) if e10 not in ["N/A", ""] else None,
                                    float(e100) if e100 not in ["N/A", ""] else None
                                )

                                break
                    else:
                        line.set_linewidth(1)
                        line.set_alpha(0.3)
                        line.set_zorder(1)

            self.canvas.draw()

        # 连接事件
        self.canvas.mpl_connect('button_press_event', on_mouse_middle_click)
        self.canvas.mpl_connect('scroll_event', on_scroll)


        # 将组件添加到布局
        layout.addWidget(self.canvas)
        layout.addWidget(toolbar_container)
        layout.addWidget(self.curve_table)

        # 连接表格双击事件
        self.curve_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.curve_table.cellChanged.connect(self.on_cell_changed)

        # 添加右键菜单事件
        self.curve_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.curve_table.customContextMenuRequested.connect(self.show_context_menu)

    def update_chart_title(self, label, e10, e100):
        """根据当前测试类型更新图表标题"""
        current_test_type = self.test_combo.currentText()
        if current_test_type == "ORR":
            title = f'{label}\nOnset Potential: {e10}   Half-wave Potential: {e100}'
        else:
            title = f'{label}\nE10/η10: {e10}   E100/η100: {e100}'

        self.ax.set_title(title, pad=10, fontsize=12)
        self.canvas.draw_idle()  # 触发画布更新

    def update_table_headers(self):
        """动态更新表格列头并保持样式"""
        current_test_type = self.test_combo.currentText()

        # 保存当前滚动条位置
        scroll_pos = self.curve_table.verticalScrollBar().value()

        if current_test_type == "ORR":
            headers = ['ShowAll', 'Color', 'Original Name', 'Label Name', 'Onset\nPotential', 'Half-wave\nPotential', 'Test Type']
            # 清除原有数据
            for row in range(self.curve_table.rowCount()):
                self.curve_table.item(row, 4).setText("")
                self.curve_table.item(row, 5).setText("")
        else:
            headers = ['ShowAll', 'Color', 'Original Name', 'Label Name', 'E10/η10', 'E100/η100', 'Test Type']

        self.curve_table.setHorizontalHeaderLabels(headers)

        # 恢复滚动条位置
        self.curve_table.verticalScrollBar().setValue(scroll_pos)

        # 强制刷新表格
        self.curve_table.blockSignals(False)
        self.curve_table.viewport().update()