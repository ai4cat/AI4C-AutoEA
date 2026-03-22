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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        font = QFont("Arial",10)
        QApplication.instance().setFont(font)
        # 加载默认参数
        self.defaults = self.load_defaults()

        # 设置窗口基本属性
        self.setWindowTitle('AutoEchemAnalyzer')
        self.setFixedSize(1400, 800)

    def update_parameters(self, test_type):
        """根据测试类型切换参数"""
        if test_type == "ORR":
            # ORR专用参数
            re_value = self.defaults.get('orr_RE_options0', 'Ag/AgCl')
            area_value = self.defaults.get('orr_inputs_area', '0.2475')
            ph_value = self.defaults.get('orr_inputs_pH', '13')
            self.area_btn.setVisible(False)
        else:
            # 通用参数
            re_value = self.defaults.get('RE_options0', 'Hg/HgO')
            area_value = self.defaults.get('inputs_area', '1')
            ph_value = self.defaults.get('inputs_pH', '14')
            self.area_btn.setVisible(True)

        # 更新界面控件
        self.re_combo.setCurrentText(re_value)
        self.area_input.setText(area_value)
        self.ph_input.setText(ph_value)

        # 更新测量值和结果标签
        self.update_table_headers()

        # 按钮可见性控制
        self.update_button_visibility(test_type)
        # 如果是ORR测试类型，调整表格列头
        if test_type == "ORR":
            self.update_table_headers()

        # 连接信号（确保切换测试类型时更新参数）
        self.test_combo.currentTextChanged.connect(self.update_parameters)

    def on_header_clicked(self, logical_index):
        """处理主窗口表头点击事件"""
        if logical_index == 0:  # 点击"ShowAll"列
            # 获取当前所有按钮状态
            current_state = all(
                self.curve_table.cellWidget(row, 0).findChild(QPushButton).isChecked()
                for row in range(self.curve_table.rowCount()))

            # 切换所有按钮状态
            new_state = not current_state
            for row in range(self.curve_table.rowCount()):
                button = self.curve_table.cellWidget(row, 0).findChild(QPushButton)
                button.setChecked(new_state)

            # 同步到AllDataDialog
            if hasattr(self, 'all_data_dialog') and self.all_data_dialog.isVisible():
                self.all_data_dialog.sync_states_from_main(new_state)

    def create_parameter_group(self, layout):
        param_group = QGroupBox("Parameter Settings")
        param_group.setStyleSheet("""
                QGroupBox {
                    font: 14px Arial;
                    margin-top: 14px;
                }
            """)
        param_layout = QFormLayout(param_group)
        param_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        param_layout.setLabelAlignment(Qt.AlignLeft)  # 标签左对齐
        param_layout.setFormAlignment(Qt.AlignLeft)  # 表单左对齐

        # 统一的输入框宽度
        input_width = 150

        # 测试类型选择
        self.test_combo = QComboBox()
        self.test_combo.setStyleSheet("""
                QComboBox {
                    font: 14px Arial;
                }
            """)
        self.test_combo.addItems(["UOR", "OER", "HER", "ORR"])
        self.test_combo.setCurrentText("ORR")
        self.test_combo.setFixedWidth(input_width - 10)
        self.test_combo.currentTextChanged.connect(self.update_interface_settings)
        param_layout.addRow("Select-UOR/OER/HER/ORR:", self.test_combo)

        # 参比电极选择
        self.re_combo = QComboBox()
        self.re_combo.setStyleSheet("""QComboBox {font: 14px Arial;}""")
        self.re_combo.addItems(["Ag/AgCl", "Hg/HgO"])
        self.re_combo.setCurrentText("Hg/HgO")
        self.re_combo.setFixedWidth(input_width- 10)
        param_layout.addRow("Reference Electrode:", self.re_combo)

        # 补偿方式选择
        self.comp_combo = QComboBox()
        self.comp_combo.setStyleSheet("""QComboBox {font: 14px Arial;}""")
        self.comp_combo.addItems(["Manual", "Auto"])
        # 从默认参数获取补偿方式设置
        comp_value = self.defaults.get('iR_options0', 'Auto')
        self.comp_combo.setCurrentText(comp_value)
        self.comp_combo.setFixedWidth(input_width- 10)
        self.comp_combo.currentTextChanged.connect(self.on_comp_method_changed)  # 添加信号连接
        param_layout.addRow("Compensation Method:", self.comp_combo)

        # 溶液电阻输入
        self.ohm_input = QLineEdit()
        self.ohm_input.setFixedWidth(input_width- 10)
        self.ohm_input.setEnabled(False)  # 初始状态禁用
        param_layout.addRow("Manual R (Ω):", self.ohm_input)

        # 补偿百分比输入
        self.percentage_input = QLineEdit("100")
        self.percentage_input.setFixedWidth(input_width- 10)
        self.percentage_input.setEnabled(False)  # 初始状态禁用
        param_layout.addRow("Compensation (%):", self.percentage_input)

        # 面积输入和换算按钮
        area_widget = QWidget()
        area_layout = QHBoxLayout(area_widget)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_layout.setSpacing(5)
        self.area_input = QLineEdit("1")
        self.area_input.setFixedWidth(input_width-10)  # 减去按钮宽度和间距
        self.area_btn = QPushButton("Convert")
        self.area_btn.setFixedWidth(60)
        self.area_btn.setVisible(False)
        area_layout.addWidget(self.area_input)
        area_layout.addWidget(self.area_btn)
        area_layout.addStretch()  # 添加弹性空间确保左对齐
        param_layout.addRow("Active Area (cm²):", area_widget)

        # pH输入
        self.ph_input = QLineEdit("14")
        self.ph_input.setFixedWidth(input_width - 10)
        param_layout.addRow("Solution pH:", self.ph_input)

        param_group.setFixedSize(340, 220)
        layout.addWidget(param_group)

    def toggle_legend(self):
        """切换图例的显示状态"""
        is_checked = self.label_button.isChecked()
        self.legend_visible = is_checked  # 更新状态跟踪

        legend = self.ax.get_legend()
        if legend:
            legend.set_visible(is_checked)

        if is_checked:
            # 如果有可见的曲线，显示图例
            visible_lines = [line for line in self.ax.lines
                             if line.get_visible() and line.get_linestyle() != '--']
            if visible_lines:
                if legend:
                    legend.set_visible(True)
                else:
                    self.ax.legend()
        else:
            # 隐藏图例
            if legend:
                legend.set_visible(False)

        self.canvas.draw()

    def toggle_grid(self):
        """切换图表网格的显示状态"""
        is_checked = self.grid_button.isChecked()
        if is_checked:
            self.ax.grid(True, linestyle='--', alpha=0.7)
        else:
            self.ax.grid(False)
        self.canvas.draw()

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
                    main_button = self.parent.curve_table.cellWidget(row, 0).findChild(QPushButton)
                    if main_button:
                        main_button.setChecked(checked)

        # 同步更新主窗口的显示按钮状态
        self.parent.header_toggle_button.setChecked(checked)

    def on_cell_double_clicked(self, row, column):
        """处理单元格双击事件"""
        if column == 1:  # 颜色列
            color = QColorDialog.getColor()
            if color.isValid() and hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                color_name = color.name()
                curve_info = self.plot_lines[row]

                # 更新表格中的颜色显示
                color_widget = QWidget()
                color_widget.setStyleSheet(f"background-color: {color_name};")
                self.curve_table.setCellWidget(row, 1, color_widget)

                # 更新保存的颜色信息
                curve_info['color'] = color_name

                # 更新曲线颜色
                line = curve_info['line']
                if line.get_visible():
                    # 重新创建曲线以更新颜色
                    line.remove()
                    new_line, = self.ax.plot(
                        curve_info['x_data'],
                        curve_info['y_data'],
                        color=color_name,
                        label=curve_info['label_name'],  # 使用 label_name 而不是 sample_name
                        linewidth=curve_info['linewidth']
                    )
                    # 更新曲线引用
                    curve_info['line'] = new_line
                    self.plot_lines[row]['line'] = new_line

                    # 更新图例
                    self.ax.legend()

                    # 重绘画布
                    self.canvas.draw()

    def on_cell_changed(self, row, column):
        """处理单元格内容改变事件"""
        if column == 3:  # 标签名称列
            if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                new_label = self.curve_table.item(row, column).text()
                curve_info = self.plot_lines[row]

                # 更新保存的标签名称
                curve_info['label_name'] = new_label

                # 更新曲线标签和颜色
                line = curve_info['line']
                if line.get_visible():
                    # 重新创建曲线以更新标签和颜色
                    line.remove()
                    new_line, = self.ax.plot(
                        curve_info['x_data'],
                        curve_info['y_data'],
                        color=curve_info['color'],
                        label=new_label,
                        linewidth=curve_info['linewidth']
                    )
                    # 更新曲线引用
                    curve_info['line'] = new_line
                    self.plot_lines[row]['line'] = new_line

                    # 更新图例
                    self.ax.legend()

                    # 重绘画布
                    self.canvas.draw()

    def toggle_curve_visibility(self, row, checked):
        """切换曲线显示状态"""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]

            # 获取当前图例状态
            current_legend_state = self.legend_visible

            if checked:
                # 显示曲线
                curve_info['line'].set_alpha(1.0)
                curve_info['line'].set_label(curve_info['label_name'])
                curve_info['visible'] = True
                # 重置所有曲线的透明度
                for info in self.plot_lines:
                    if info.get('visible', False):
                        info['line'].set_alpha(1.0)
            else:
                # 隐藏曲线
                curve_info['line'].set_alpha(0.0)
                curve_info['line'].set_label('_' + curve_info['label_name'])
                curve_info['visible'] = False

            # 更新图例
            handles = []
            labels = []
            for info in self.plot_lines:
                if info.get('visible', False):
                    handles.append(info['line'])
                    labels.append(info['label_name'])

            # 更新图例（保持原有可见状态）
            if handles:
                legend = self.ax.legend(handles, labels)
                legend.set_visible(current_legend_state)
            else:
                if self.ax.get_legend():
                    self.ax.get_legend().remove()

            # 保持按钮的选中状态同步
            self.label_button.setChecked(current_legend_state)

            self.canvas.draw()

    def show_context_menu(self, position):
        """显示右键菜单"""
        # 获取点击的单元格
        item = self.curve_table.itemAt(position)
        if not item:
            return

        row = item.row()
        column = self.curve_table.columnAt(position.x())

        # 只在标签名称列显示右键菜单
        if column == 3:  # 标签名称列
            menu = QMenu(self)

            # 字体设置子菜单
            font_menu = menu.addMenu("Font Settings")

            # 添加恢复默认选项
            reset_action = font_menu.addAction("Reset Default")
            reset_action.triggered.connect(lambda: self.reset_label_font(row))
            font_menu.addSeparator()

            # 字体大小子菜单
            font_size_menu = font_menu.addMenu("Font Size")
            for size in [8, 10, 12, 14, 16, 18, 20]:
                action = font_size_menu.addAction(f"{size}pt")
                action.triggered.connect(lambda checked, s=size: self.set_label_font_size(row, s))

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
                action.triggered.connect(lambda checked, s=style: self.set_label_font_style(row, s))

            # 上下标子菜单
            script_menu = menu.addMenu("Superscript/Subscript")
            superscript_action = script_menu.addAction("Add Superscript")
            superscript_action.triggered.connect(lambda: self.add_script(row, "super"))
            subscript_action = script_menu.addAction("Add Subscript")
            subscript_action.triggered.connect(lambda: self.add_script(row, "sub"))

            # 显示菜单 - 使用 exec 替代 exec_
            menu.exec(self.curve_table.viewport().mapToGlobal(position))

    def reset_label_font(self, row):
        """恢复标签字体到默认设置，保留上下标标记"""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]
            current_text = curve_info['label_name']

            # 保留上下标标记
            import re

            # 提取所有上下标
            superscripts = re.findall(r'\$\^{([^}]+)}\$', current_text)
            subscripts = re.findall(r'\$_{([^}]+)}\$', current_text)

            # 获取基础文本
            base_text = curve_info['original_name']

            # 重新添加上下标
            new_text = base_text
            for sup in superscripts:
                new_text += f'$^{{{sup}}}$'
            for sub in subscripts:
                new_text += f'$_{{{sub}}}$'

            # 更新表格和曲线标签
            self.curve_table.item(row, 3).setText(new_text)
            curve_info['line'].set_label(new_text)
            curve_info['label_name'] = new_text

            # 重置图例字体设置
            self.ax.legend(prop={'size': 'medium'})  # 使用默认大小
            self.canvas.draw()

    def set_label_font_size(self, row, size):
        """设置标签字体大小"""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]
            current_text = curve_info['label_name']

            # 更新表格和曲线标签
            self.curve_table.item(row, 3).setText(current_text)
            curve_info['line'].set_label(current_text)
            curve_info['label_name'] = current_text

            # 更新图例，直接设置字体大小
            self.ax.legend(prop={'size': size})

            legend = self.ax.get_legend()
            if legend:
                was_visible = legend.get_visible()
                self.ax.legend(prop={'size': size})
                self.ax.get_legend().set_visible(was_visible)

            self.canvas.draw()
    
    def set_label_font_style(self, row, style):
        """设置标签字体样式"""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]
            current_text = curve_info['label_name']

            # 移除现有的样式标记（如果有）
            text = current_text.replace('\\bf', '').replace('\\it', '') \
                .replace('\\rm', '').replace('$', '')

            # 添加新的样式标记
            if 'bold' in style and 'italic' in style:
                new_text = f"$\\bf\\it{{{text}}}$"
            elif 'bold' in style:
                new_text = f"$\\bf{{{text}}}$"
            elif 'italic' in style:
                new_text = f"$\\it{{{text}}}$"
            else:
                new_text = f"$\\rm{{{text}}}$"

            # 更新表格和曲线标签
            self.curve_table.item(row, 3).setText(new_text)
            curve_info['line'].set_label(new_text)
            curve_info['label_name'] = new_text

            # 更新图例时保持可见性
            legend = self.ax.get_legend()
            if legend:
                was_visible = legend.get_visible()
                self.ax.legend()
                self.ax.get_legend().set_visible(was_visible)

            self.canvas.draw()

    def add_script(self, row, script_type):
        """添加上标或下标"""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            # 获取当前标签文本
            current_text = self.curve_table.item(row, 3).text()

            # 创建输入对话框
            text, ok = QInputDialog.getText(self,
                                            "Add " + ("Superscript" if script_type == "super" else "Subscript"),
                                            "Please enter " + ("superscript" if script_type == "super" else "subscript") + "文本：")

            if ok and text:
                # 使用 matplotlib 的数学文本语法
                if script_type == "super":
                    new_text = f"{current_text}$^{text}$"
                else:
                    new_text = f"{current_text}$_{text}$"

                # 更新表格和曲线标签
                self.curve_table.item(row, 3).setText(new_text)
                curve_info = self.plot_lines[row]
                curve_info['line'].set_label(new_text)
                curve_info['label_name'] = new_text

                # 更新图例，使用内置数学文本渲染器
                plt.rcParams['text.usetex'] = False  # 禁用 LaTeX
                plt.rcParams['mathtext.default'] = 'regular'
                self.ax.legend()
                self.canvas.draw()
    
    def update_coordinates(self, event):
        """更新坐标显示"""
        if event.inaxes:
            self.coord_label.setText(f"Coordinates: x={event.xdata:.3f}, y={event.ydata:.3f}")
        else:
            self.coord_label.setText("")

    def reset_view(self):
        """重置视图到初始状态"""
        if self.init_xlim is not None and self.init_ylim is not None:
            self.ax.set_xlim(self.init_xlim)
            self.ax.set_ylim(self.init_ylim)
            self.canvas.draw()




    # 信号处理方法
    def update_interface_settings(self):
        """同时更新图表和表格设置"""
        self.update_plot_settings()
        self.update_table_headers()
        self.update_parameters(self.test_combo.currentText())
        self.update_button_visibility(self.test_combo.currentText())

        test_type = self.test_combo.currentText()

        # 按钮可见性同步
        self.area_btn.setVisible(test_type != "ORR")

        if test_type == "ORR":
            self.result_label.setText("Characteristic Potential (V vs. RHE)")
            self.e10_label.setText("Onset Potential：")
            self.e100_label.setText("Half-wave Potential：")
            self.e10_label.setFixedWidth(120)
            self.e100_label.setFixedWidth(120)
            self.e10_result.setVisible(True)
            self.e100_result.setVisible(True)
        else:
            self.result_label.setText("Results (V vs RHE)")
            self.e10_label.setText("10mA/cm²：")
            self.e100_label.setText("100mA/cm²：")

    def update_plot_settings(self):
        """根据测试类型更新图表设置"""
        self.ax.clear()
        test_type = self.test_combo.currentText()

        # 创建混合变换
        from matplotlib.transforms import blended_transform_factory
        transform = blended_transform_factory(self.ax.transAxes, self.ax.transData)

        # 设置固定的相对位置
        x_relative_position = 0.01  # x轴1%位置

        if test_type in ["OER", "UOR"]:
            self.ax.set_xlim(1.2, 2.0)
            self.ax.set_ylim(-10, 300)
            self.ax.set_yticks(range(0, 301, 100))

            # 参考线
            self.ax.axhline(y=10, color='gray', linestyle='--', linewidth=1, zorder=1)
            self.ax.axhline(y=100, color='gray', linestyle='--', linewidth=1, zorder=1)

            # 放置标签 - 使用混合变换
            self.ax.text(x_relative_position, 10, '10 mA cm$^{-2}$',
                         fontsize=10,
                         verticalalignment='bottom',
                         transform=transform)
            self.ax.text(x_relative_position, 100, '100 mA cm$^{-2}$',
                         fontsize=10,
                         verticalalignment='bottom',
                         transform=transform)

        elif test_type == "HER":
            self.ax.set_xlim(-0.4, 0)
            self.ax.set_ylim(-300, 10)

            # 参考线
            self.ax.axhline(y=-10, color='gray', linestyle='--', linewidth=1, zorder=1)
            self.ax.axhline(y=-100, color='gray', linestyle='--', linewidth=1, zorder=1)

            # 放置标签 - 使用混合变换
            self.ax.text(x_relative_position+0.85, -15, '10 mA cm$^{-2}$',
                         fontsize=10,
                         verticalalignment='top',
                         transform=transform)
            self.ax.text(x_relative_position+0.85, -105, '100 mA cm$^{-2}$',
                         fontsize=10,
                         verticalalignment='top',
                         transform=transform)
        elif test_type == "ORR":
            self.ax.set_xlim(0.2, 1.2)
            self.ax.set_ylim(-6, 1)
            self.ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, zorder=1)
            self.ax.text(0.25, 0.5, '0 mA cm$^{-2}$', fontsize=10, verticalalignment='top')

        # 设置标签和网格
        self.ax.set_xlabel('Potential (V vs. RHE)', fontsize=16, fontweight='bold')
        self.ax.set_ylabel('Current density (mA cm$^{-2}$)', fontsize=16, fontweight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.7)

        # 保存初始视图限制
        self.init_xlim = self.ax.get_xlim()
        self.init_ylim = self.ax.get_ylim()

        # 设置刻度标签字体和大小
        self.ax.tick_params(axis='both', which='major', labelsize=12)

        # 设置固定间隔的主刻度（每100一个）
        if test_type == "ORR":
            self.ax.yaxis.set_major_locator(MultipleLocator(1))
        else:
            self.ax.yaxis.set_major_locator(MultipleLocator(100))
        # 移除小刻度
        self.ax.yaxis.set_minor_locator(NullLocator())

        self.figure.patch.set_facecolor('white')  # 设置图表背景为白色
        self.ax.set_facecolor('white')  # 设置坐标轴区域背景为白色

        # 更新画布
        self.canvas.draw()
        # 更新表格列头
        self.update_table_headers()

    def create_note_area(self, layout):
        note_group = QGroupBox()
        note_group.setStyleSheet("""
            QGroupBox {
                margin:0;
                padding:5px;
            }
        """)

        # 主垂直布局
        main_layout = QVBoxLayout(note_group)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # Calculation Method部分（保持原样）
        calc_label = QLabel("Calculation Method:")
        calc_label.setStyleSheet("""
                                QGroupBox {
                    font: 14px Arial;
                    margin-top: 14px;
                }
                QLabel {
                    font: 14px Arial;
                }
            """)
        main_layout.addWidget(calc_label)

        formula1 = QLabel("Ag/AgCl：E(RHE)=E(test)+0.199+0.0591*pH")
        formula1.setStyleSheet("""
                QLabel {
                    font: 14px Arial;
                }
            """)
        formula2 = QLabel("Hg/HgO：E(RHE)=E(test)+0.098+0.0591*pH")
        formula2.setStyleSheet("""
                QLabel {
                    font: 14px Arial;
                }
            """)
        main_layout.addWidget(formula1)
        main_layout.addWidget(formula2)

        # 创建水平容器放置Output和Remarks
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(10)  # 控制两个区域的间距

        # Output Notes部分（左侧）
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_label = QLabel("Output Notes:")
        output_label.setStyleSheet("""
                QGroupBox {
                    font: 14px Arial;
                    margin-top: 14px;
                }
                QLabel {
                    font: 14px Arial;
                }
            """)
        output_notes = QLabel(
            "• UOR - Potential\n"
            "• OER - Overpotential\n"
            "• HER - Overpotential\n"
            "• ORR - Half-wave potential"
        )
        output_notes.setStyleSheet("""
                QLabel {
                    font: 14px Arial;
                }
            """)
        output_layout.addWidget(output_label)
        output_layout.addWidget(output_notes)
        hbox.addWidget(output_container, 5)  # 占5份宽度

        # Remarks部分（右侧）
        remark_container = QWidget()
        remark_layout = QVBoxLayout(remark_container)
        remark_layout.setContentsMargins(0, 0, 0, 0)
        remark_label = QLabel("Remarks:")
        remark_label.setStyleSheet("""
                QLabel {
                    font: 14px Arial;
                }
            """)
        remarks = QLabel(
            "• Batch processing:\n   For auto-compensated files\n"
            "• Manual files:\n   Set parameters first"
        )
        remarks.setStyleSheet("""
                        QLabel {
                            font: 14px Arial;
                        }
                    """)
        remarks.setWordWrap(True)  # 启用自动换行
        remark_layout.addWidget(remark_label)
        remark_layout.addWidget(remarks)
        hbox.addWidget(remark_container, 5)  # 占5份宽度

        # 将水平布局添加到主布局
        main_layout.addLayout(hbox)

        # 最终添加到父布局
        layout.addWidget(note_group)

    def create_data_group(self, layout):
        data_group = QGroupBox("Data Display")
        data_group.setStyleSheet("""
                QGroupBox {
                    font: 14px Arial;
                    margin-top: 14px;
                }
            """)

        data_layout = QFormLayout(data_group)
        data_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        data_layout.setLabelAlignment(Qt.AlignLeft)
        data_layout.setFormAlignment(Qt.AlignLeft)

        # 统一的输入框宽度
        input_width = 150

        # 软件选择
        #self.software_combo = QComboBox()
        #self.software_combo.setStyleSheet("""QComboBox {font: 14px Arial;}""")
        #self.software_combo.addItems(["CHI760e", "EC-lab", "DHElecChem"])
        #self.software_combo.setFixedWidth(input_width + 25)
        #data_layout.addRow("Software:", self.software_combo)

        # 文件夹名显示
        self.file_path_label = QLabel("----------")  # 保持变量名为 file_path_label
        self.file_path_label.setFixedWidth(input_width + 25)
        data_layout.addRow("Folder:", self.file_path_label)

        # 样品名称
        self.name_input = QLineEdit()
        self.name_input.setFixedWidth(input_width + 25)
        data_layout.addRow("Sample Name:", self.name_input)

        # 动态结果标签
        self.result_label = QLabel("Results（V .vs RHE）")
        data_layout.addRow(self.result_label)
        # 动态参数标签
        self.e10_label = QLabel("10mA/cm²：")
        self.e100_label = QLabel("100mA/cm²：")

        # 动态结果显示
        self.e10_result = QLineEdit()
        self.e100_result = QLineEdit()

        data_layout.addRow(self.e10_label, self.e10_result)
        data_layout.addRow(self.e100_label, self.e100_result)
        data_group.setFixedSize(340, 150)
        layout.addWidget(data_group)

    def update_folder_display(self, folder_path):
        """更新界面中的文件夹名显示"""
        if folder_path:
            folder_name = os.path.basename(folder_path)
            self.file_path_label.setText(folder_name)
        else:
            self.file_path_label.setText("No folder selected")

    def update_data_display(self, label, e10_value, e100_value):
        """根据测试类型更新数据显示区域"""
        current_test = self.test_combo.currentText()

        # 更新样品名称
        self.name_input.setText(label)

        # 更新标签文本
        if current_test == "ORR":
            self.e10_label.setText("Onset Potential:")
            self.e100_label.setText("Half-wave Potential:")
        else:
            self.e10_label.setText("10mA/cm²：")
            self.e100_label.setText("100mA/cm²：")

        # 更新数值显示（保留两位小数）
        self.e10_result.setText(f"{e10_value:.3f}" if e10_value else "N/A")
        self.e100_result.setText(f"{e100_value:.3f}" if e100_value else "N/A")

        # 同步更新图表标题（已实现部分）
        self.update_chart_title(label, e10_value, e100_value)

    def update_button_visibility(self, test_type):
        """根据测试类型更新按钮可见性"""
        # 设置边距
        if test_type == "ORR":
            # ORR时设置上边距30
            self.button_container_layout.setContentsMargins(0, 80, 0, 0)
        else:
            # 其他情况恢复默认边距
            self.button_container_layout.setContentsMargins(0, 10, 0, 0)

        # 定义需要保留的按钮文本列表
        keep_buttons = [
            "Rebuild\nFolders",
            "Default\nSettings",
            "Batch\nProcess",
            "Plot\nLSV",
            "Classify\nFiles"
        ]

        # 遍历所有按钮
        for btn in self.right_buttons:
            btn_text = btn.text().replace('\n', '')  # 移除换行符比较
            if test_type == "ORR":
                btn.setVisible(btn.text() in keep_buttons)
            else:
                btn.setVisible(True)

    def create_button_group(self, layout):
        """创建垂直排列的按钮组"""
        # 存储按钮引用
        self.right_buttons = []

        # 创建功能按钮
        button_config = [
            ("Rebuild\nFolders", self.re_folders, False),
            ("Default\nSettings", self.open_defaults, False),
            ("Load\nFile", self.open_file, True),
            ("Batch\nProcess", self.batch_file, False),
            ("Plot\nLSV", self.batch_LSV, False),
            ("CSV to\nTXT", self.csv_to_txt, True),
            ("Classify\nFiles", self.txt_classify, False),
        ]

        # 创建按钮容器
        self.button_container = QWidget()
        self.button_container_layout = QVBoxLayout(self.button_container)
        self.button_container_layout.setContentsMargins(0, 0, 0, 0)  # 移除容器边距
        self.button_container_layout.setSpacing(5)  # 设置按钮间距为0

        # 创建按钮并设置样式
        for text, func, _ in button_config:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            self.right_buttons.append(btn)
            # 统一尺寸设置
            btn.setFixedSize(130, 70)  # 固定所有按钮尺寸

            # 设置尺寸策略
            size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setSizePolicy(size_policy)

            # 设置通用样式
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2c313c;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 5px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #3c424f;
                }
                QPushButton:pressed {
                    background-color: #1e2228;
                }
            """)

            self.button_container_layout.addWidget(btn)
            self.right_buttons.append(btn)

        # 添加弹性空间
        self.button_container_layout.addStretch()

        # 将按钮容器添加到布局
        layout.addWidget(self.button_container)

        # 设置右侧布局参数
        layout.setContentsMargins(0, 0, 0, 0)  # 移除布局边距
        layout.setSpacing(0)  # 设置布局间距为0

        # 连接测试类型变化信号
        self.test_combo.currentTextChanged.connect(self.adjust_button_layout)

    def adjust_button_layout(self):
        """调整按钮布局"""
        # 强制更新布局
        self.right_buttons[0].parent().layout().activate()
        self.right_buttons[0].parent().updateGeometry()

    def on_comp_method_changed(self, text):
        """处理补偿方式改变的事件"""
        is_manual = text == "Manual"
        self.ohm_input.setEnabled(is_manual)
        self.percentage_input.setEnabled(is_manual)

        # 如果切换到自动补偿，清空输入框
        if not is_manual:
            self.ohm_input.clear()
            self.percentage_input.setText("100")

    def change_current(self):
        """处理Convert按钮点击"""
        current_test = self.test_combo.currentText()

        if current_test == "ORR":
            return

        """换算按钮点击处理函数"""
        try:
            area_value = float(self.area_input.text())
            self.e10_label.setText(f"{area_value * 10}mA：")
            self.e100_label.setText(f"{area_value * 100}mA：")
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid area value!")

    def open_defaults(self):
        """打开默认参数设置"""
        filename = 'Default parameter settings.txt'
        filepath = os.path.join(os.getcwd(), filename)

        # 检查文件是否存在，不存在则创建
        if not os.path.exists(filepath):
            if not self.create_default_config(filepath):
                return

        # 打开文件供用户编辑
        try:
            os.startfile(filepath) if os.name == 'nt' else os.system(f'open {filepath}')
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open file: {str(e)}")
