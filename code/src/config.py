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
from dialogs import AllDataDialog

class Configurator(QMainWindow):
    def __init__(self):
        super().__init__()

    def create_default_config(self, filepath):
        """创建包含所有默认参数的配置文件"""
        try:
            with open(filepath, 'w', encoding='utf-8-sig') as file:
                file.writelines([
                    "# Default parameter settings\n\n",
                    "# General Parameters\n",
                    "test_options0=UOR\n",
                    "RE_options0=Hg/HgO\n",
                    "iR_options0=Auto\n",
                    "softw_options0=CHI760e\n",
                    "inputs_percentage=100\n",
                    "inputs_area=1\n",
                    "inputs_pH=14\n\n",

                    "\n# ORR Parameters\n",
                    "orr_RE_options0=Ag/AgCl\n",
                    "orr_inputs_area=0.2475\n",
                    "orr_inputs_pH=13\n\n",

                    "\n# File Tags\n",
                    "oer_tags=[\"02_LSV\",\"04_LSV\",\"05_LSV\",\"06_LSV\"]\n",
                    "her_tags=[\"08_LSV\",\"09_LSV\",\"10_LSV\"]\n\n"
                ])
                file.writelines("\n\n")
                file.writelines([
                    "# Test type dropdown options [\"UOR\", \"OER\", \"HER\", \"ORR\"]\n",
                    "# Reference Electrode options [\"Ag/AgCl\", \"Hg/HgO\"]\n",
                    "# IR Compensation method options[\"Manual\", \"Auto\"]\n",
                    "# Files generation software options[\"CHI760e\", \"EC-lab\", \"DHElecChem\"]\n",
                    "# Compensation percentage % - Default 100%, Auto compensation doesn't require input\n",
                    "# Electrode active area - Default 1cm^2, ORR 0.2475cm^2\n",
                    "# Solution pH - Default 14, ORR 13\n",
                    "# ORR parameters only take effect when ORR test is selected\n",
                    "# UOR/OER file classification method - Based on TXT filename\n",
                    "# HER file classification method - Based on TXT filename\n",
                    "# Author - Kai Wu\n"
                ])
            QMessageBox.information(self, "Info", "Default config file created.")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create config file: {str(e)}")
            return False
    
    def show_all_data(self):
        """显示完整数据对话框"""
        dialog = AllDataDialog(self)
        dialog.populate_data(self.curve_table)
        dialog.exec()
    

    def on_mouse_press(self, event):
        """鼠标按下事件"""
        if event.button == 1:  # 左键
            self.dragging = True
            self.last_x = event.xdata
            self.last_y = event.ydata

    def on_mouse_release(self, event):
        """鼠标释放事件"""
        self.dragging = False

    def on_mouse_move(self, event):
        """鼠标移动事件"""
        if self.dragging and event.xdata is not None and event.ydata is not None:
            dx = event.xdata - self.last_x
            dy = event.ydata - self.last_y

            # 获取当前的视图限制
            x1, x2 = self.ax.get_xlim()
            y1, y2 = self.ax.get_ylim()

            # 更新视图限制
            self.ax.set_xlim(x1 - dx, x2 - dx)
            self.ax.set_ylim(y1 - dy, y2 - dy)

            self.last_x = event.xdata
            self.last_y = event.ydata
            self.canvas.draw()

    def on_scroll(self, event):
        """鼠标滚轮事件"""
        # 获取当前视图限制
        x1, x2 = self.ax.get_xlim()
        y1, y2 = self.ax.get_ylim()

        # 计算缩放中心
        center_x = event.xdata if event.xdata else (x1 + x2) / 2
        center_y = event.ydata if event.ydata else (y1 + y2) / 2

        # 设置缩放因子
        scale_factor = 1.1 if event.button == 'up' else 0.9

        # 计算新的限制
        dx = (x2 - x1) * scale_factor
        dy = (y2 - y1) * scale_factor

        # 更新视图限制
        self.ax.set_xlim(center_x - dx / 2, center_x + dx / 2)
        self.ax.set_ylim(center_y - dy / 2, center_y + dy / 2)

        self.canvas.draw()

    def txt_classify(self):
        """文件分类主入口，根据测试类型路由到不同处理逻辑"""
        # 选择文件夹
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing TXT/CSV Files",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )

        if not selected_folder:
            QMessageBox.information(self, "Operation Cancelled", "No folder was selected.")
            return

        # 根据当前测试类型路由处理逻辑
        test_type = self.test_combo.currentText()
        if test_type == "ORR":
            self.txt_classify_ORR(selected_folder)
        else:
            self.txt_classify_U_O_H(selected_folder)

    def txt_classify_ORR(self, folder_path):
        """ORR专用文件分类：保留样品名_LSV_2和_LSV_4文件，删除其他CSV文件，并记录缺失情况"""
        pattern = re.compile(r'^(.*?)_LSV_(\d+)\.csv$', re.IGNORECASE)
        error_folder = os.path.join(folder_path, "Incomplete_Samples")

        try:
            # 初始化统计信息
            stats = {
                'total': 0,
                'preserved': 0,
                'deleted': 0,
                'moved': 0,
                'missing_samples': set()
            }

            # 第一阶段：处理所有CSV文件
            all_csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
            sample_data = defaultdict(set)

            for filename in all_csv_files:
                stats['total'] += 1
                match = pattern.match(filename)
                if not match:
                    # 删除非标准文件
                    try:
                        os.remove(os.path.join(folder_path, filename))
                        stats['deleted'] += 1
                    except Exception as e:
                        print(f"Failed to delete non-standard file {filename}: {str(e)}")
                    continue

                sample_name, lsv_num = match.groups()
                if lsv_num in {'2', '4'}:
                    sample_data[sample_name].add(lsv_num)
                    stats['preserved'] += 1
                else:
                    # 删除其他LSV编号文件
                    try:
                        os.remove(os.path.join(folder_path, filename))
                        stats['deleted'] += 1
                    except Exception as e:
                        print(f"Failed to delete file {filename}: {str(e)}")

            # 第二阶段：识别数据不全的样品
            missing_entries = []
            for sample, nums in sample_data.items():
                missing = []
                if '2' not in nums:
                    missing.append("LSV_2")
                if '4' not in nums:
                    missing.append("LSV_4")
                if missing:
                    stats['missing_samples'].add(sample)
                    missing_entries.append(f"{sample} missing: {', '.join(missing)}")

            # 第三阶段：移动不完整样品文件
            if stats['missing_samples']:
                # 创建数据不全文件夹
                os.makedirs(error_folder, exist_ok=True)

                # 移动相关文件
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    # 匹配属于不完整样品的文件
                    if any(filename.startswith(sample) for sample in stats['missing_samples']):
                        try:
                            shutil.move(file_path, os.path.join(error_folder, filename))
                            stats['moved'] += 1
                        except Exception as e:
                            print(f"Failed to move file {filename}: {str(e)}")

                # 生成并移动错误报告
                error_file = os.path.join(error_folder, "Incomplete_Samples.txt")
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(missing_entries))

                stats['moved'] += 1  # 统计错误文件

            # 生成统计报告
            report = [
                "═══ ORR File Classification Report ═══",
                f"Total files processed: {stats['total']}",
                f"Valid files preserved: {stats['preserved']}",
                f"Invalid files deleted: {stats['deleted']}",
                f"Incomplete files moved: {stats['moved']}",
                f"Samples with missing data: {len(stats['missing_samples'])}"
                ]

            if stats['missing_samples']:
                report.append("\nSamples with missing data:")
                report.extend([f"• {sample}" for sample in stats['missing_samples']])

            QMessageBox.information(self, "Classification Complete", "\n".join(report))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"File processing failed: {str(e)}")
            # 清理可能创建的错误文件夹
            if os.path.exists(error_folder) and not os.listdir(error_folder):
                os.rmdir(error_folder)

    def txt_classify_U_O_H(self, selected_folder):
        """按需创建文件夹的UOR/OER/HER文件分类方法"""
        try:
            current_test = self.test_combo.currentText().upper()
            move_counts = defaultdict(int)
            created_folders = set()  # 记录已创建的文件夹

            # 加载标签配置（转为小写集合）
            defaults = self.load_defaults()
            oer_tags = {tag.lower() for tag in eval(defaults.get('oer_tags', '["02_LSV","04_LSV","05_LSV","06_LSV"]'))}
            her_tags = {tag.lower() for tag in eval(defaults.get('her_tags', '["08_LSV","09_LSV","10_LSV"]'))}

            # 定义反应类型匹配模式（精确单词匹配）
            reaction_pattern = re.compile(
                r'\b(uor|oer|her)\b',
                re.IGNORECASE
            )

            for filename in os.listdir(selected_folder):
                if not filename.lower().endswith('.txt'):
                    continue

                src_path = os.path.join(selected_folder, filename)
                filename_lower = filename.lower()
                dest_folder = None

                # 阶段1：文件名反应类型检测（最高优先级）
                reaction_match = reaction_pattern.search(filename_lower)
                if reaction_match:
                    reaction = reaction_match.group(1).upper()
                    # 创建对应文件夹（如果尚未创建）
                    if reaction not in created_folders:
                        os.makedirs(os.path.join(selected_folder, reaction), exist_ok=True)
                        created_folders.add(reaction)
                    dest_folder = os.path.join(selected_folder, reaction)

                # 阶段2：标签分类（仅在未检测到文件名反应类型时）
                if not dest_folder:
                    # 根据当前测试类型处理
                    if current_test == "UOR":
                        if any(tag in filename_lower for tag in oer_tags):
                            dest_folder_name = "UOR"
                        elif any(tag in filename_lower for tag in her_tags):
                            dest_folder_name = "HER"
                    elif current_test == "OER":
                        if any(tag in filename_lower for tag in oer_tags):
                            dest_folder_name = "OER"
                        elif any(tag in filename_lower for tag in her_tags):
                            dest_folder_name = "HER"
                    elif current_test == "HER":
                        if any(tag in filename_lower for tag in her_tags):
                            dest_folder_name = "HER"

                    # 创建目标文件夹（如果需要）
                    if 'dest_folder_name' in locals():
                        if dest_folder_name not in created_folders:
                            os.makedirs(os.path.join(selected_folder, dest_folder_name), exist_ok=True)
                            created_folders.add(dest_folder_name)
                        dest_folder = os.path.join(selected_folder, dest_folder_name)

                # 执行移动操作
                if dest_folder:
                    try:
                        shutil.move(src_path, os.path.join(dest_folder, filename))
                        folder_name = os.path.basename(dest_folder)
                        move_counts[folder_name] += 1
                    except Exception as e:
                        print(f"Failed to move file {filename}: {str(e)}")

            # 生成分类报告
            report_msg = "File classification completed:\n"
            for folder, count in move_counts.items():
                report_msg += f"• {folder}: {count} files\n"

            if created_folders:
                report_msg += "\nCreated folders:\n" + "\n".join([f"• {f}" for f in created_folders])

            QMessageBox.information(self, "Classification Complete", report_msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Classification process error:：{str(e)}")

    def load_defaults(self, filepath=None):
        """加载默认参数"""
        if filepath is None:
            filepath = os.path.join(os.getcwd(), 'Default parameter settings.txt')
        defaults = {}

        # 尝试不同的编码方式
        encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'ansi']

        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as file:
                    for line in file:
                        if '=' in line:
                            key, value = line.strip().split('=',1)
                            defaults[key.strip()] = value.strip()
                    return defaults
            except UnicodeDecodeError:
                continue
            except FileNotFoundError:
                # 文件不存在时调用公共方法创建
                if self.create_default_config(filepath):
                    return self.load_defaults(filepath)  # 递归加载
                return {}

        # 如果所有编码都失败了，返回空字典并显示警告
        QMessageBox.warning(self, "Error", "Failed to read default config file. Using built-in defaults.")
        return {}

