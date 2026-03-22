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

class FileIO(QMainWindow):
    def __init__(self):
        super().__init__()

    def re_folders(self):
        """重建文件夹"""
        # 获取当前工作目录
        current_dir = os.getcwd()

        # 定义需要创建的文件夹
        folders = ['HER', 'UOR', 'OER','ORR', 'CSV_to_TXT']

        for folder in folders:
            folder_path = os.path.join(current_dir, folder)

            # 如果文件夹存在，清空它
            if os.path.exists(folder_path):
                try:
                    # 删除文件夹中的所有文件和子文件夹
                    for filename in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, filename)
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    print(f"Clearing folder: {folder}")
                except Exception as e:
                    print(f"Failed to clear folder {folder}: {e}")
            else:
                # 如果文件夹不存在，创建它
                try:
                    os.makedirs(folder_path)
                    print(f"Creating folder: {folder}")
                except Exception as e:
                    print(f"Failed to create folder {folder}: {e}")

        # 显示操作完成的消息
        QMessageBox.information(self, "Complete", "Folders rebuilt successfully")

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Text File",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd(),
            "Text files (*.txt);;All files (*.*)"
        )
        if filename:
            self.process_single_file(filename)
    
    def save_processed_data(self, data, source_filename, test_type=None):
        """保存处理后的数据到CSV文件"""
        try:
            if test_type is None:
                test_type = self.test_combo.currentText()

            # 创建保存目录
            save_folder = os.path.join(os.path.dirname(source_filename),
                                       f"Processed_{test_type}_LSV")
            os.makedirs(save_folder, exist_ok=True)

            # 构建新文件名
            basename = os.path.basename(source_filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"Processed_{os.path.splitext(basename)[0]}.csv"
            save_path = os.path.join(save_folder, new_filename)

            # 准备数据
            processed_data = []

            # 添加表头
            processed_data.append(['Potential (V vs. RHE)', 'Current density (mA/cm²)'])

            # 获取电极面积用于电流密度计算
            try:
                area = float(self.area_input.text())
            except ValueError:
                area = 1.0

            # 添加数据行
            for potential, current in data:
                # 计算电流密度
                current_density = current / area
                # 计算RHE电势
                potential_rhe = self.calculate_rhe_potential(potential)
                processed_data.append([f"{potential_rhe:.4f}", f"{current_density:.4f}"])

            # 保存到CSV文件
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(processed_data)

            print(f"Data saved to: {save_path}")
            return save_path

        except Exception as e:
            print(f"Error saving processed data: {str(e)}")
            return None

    def save_performance_data(self, filename, test_type, sample_name, e10, e100):
        """保存性能统计数据到txt和csv文件"""
        try:
            # 创建性能数据文件夹
            perf_folder = os.path.join(os.path.dirname(filename),
                                       f"{test_type}_Performance_Data_Summary")
            os.makedirs(perf_folder, exist_ok=True)

            # 获取当前时间
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 根据测试类型准备数据
            if test_type == "UOR":
                # UOR输出为电势
                header_txt = "Reaction,Reference,IR Compensation,Resistance,Percentage,Area(cm²),pH,Sample,Potential E10,E100"
                header_csv = ["Reaction", "Reference", "IR Compensation", "Resistance(ohm)", "Percentage(%)",
                              "Area(cm²)", "pH", "Sample", "Potential E10(V)", "Potential E100(V)"]
                e10_formatted = f"{e10:.4f}" if isinstance(e10, float) else "N/A"
                e100_formatted = f"{e100:.4f}" if isinstance(e100, float) else "N/A"
            elif test_type == "ORR":
                # ORR输出为起始电位和半波电位
                header_txt = "Reaction,Reference,IR Compensation,Area(cm²),pH,Sample,Onset Potential,Half-wave Potential"
                header_csv = ["Reaction", "Reference", "IR Compensation", "Area(cm²)", "pH", "Sample", "Onset Potential(V)", "Half-wave Potential(V)"]
                e10_formatted = f"{e10:.3f}" if isinstance(e10, float) else "N/A"
                e100_formatted = f"{e100:.3f}" if isinstance(e100, float) else "N/A"

            else:  # OER 和 HER
                header_txt = "Reaction,Reference,IR Compensation,Resistance,Percentage,Area(cm²),pH,Sample,Overpotential n10,n100"
                header_csv = ["Reaction", "Reference", "IR Compensation", "Resistance(ohm)", "Percentage(%)",
                              "Area(cm²)", "pH", "Sample", "Overpotential n10(mV)", "Overpotential n100(mV)"]

                if isinstance(e10, float) and isinstance(e100, float):
                    if test_type == "OER":
                        # OER过电势 = E - 1.23V
                        e10_formatted = f"{(e10 - 1.23) * 1000:.2f}"
                        e100_formatted = f"{(e100 - 1.23) * 1000:.2f}"
                    else:  # HER
                        # HER过电势 = |E|
                        e10_formatted = f"{abs(e10) * 1000:.2f}"
                        e100_formatted = f"{abs(e100) * 1000:.2f}"
                else:
                    e10_formatted = "N/A"
                    e100_formatted = "N/A"

            # 准备数据行
            if test_type == "ORR":
                data = {
                    'Reaction': test_type,
                    'Reference': self.re_combo.currentText(),
                    'IR Compensation': self.comp_combo.currentText(),
                    'Area(cm²)': self.area_input.text(),
                    'pH': self.ph_input.text(),
                    'Sample': sample_name,
                    'E10': e10_formatted,
                    'E100': e100_formatted
                }
            else:
                data = {
                    'Reaction': test_type,
                    'Reference': self.re_combo.currentText(),
                    'IR Compensation': self.comp_combo.currentText(),
                    'Resistance': self.ohm_input.text() or "0",
                    'Percentage': f"{self.percentage_input.text()}%",
                    'Area(cm²)': self.area_input.text(),
                    'pH': self.ph_input.text(),
                    'Sample': sample_name,
                    'E10': e10_formatted,
                    'E100': e100_formatted
                }

            # 保存TXT文件
            txt_path = os.path.join(perf_folder, f"{test_type}_Data_Statistics.txt")
            if not os.path.exists(txt_path):
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(header_txt + '\n')

            with open(txt_path, 'a', encoding='utf-8') as f:
                line = f"{','.join(str(v) for v in data.values())}\n"
                f.write(line)

            # 保存CSV文件
            csv_path = os.path.join(perf_folder, f"{test_type}_Data_Statistics.csv")
            if not os.path.exists(csv_path):
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(header_csv)

            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                row = list(data.values())
                writer.writerow(row)

        except Exception as e:
            print(f"Error saving performance data: {str(e)}")

    def csv_to_txt(self):
        """批量将CSV文件转换为TXT文件，并删除非LSV文件"""
        # 选择文件夹
        source_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing CSV Files",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )

        if not source_folder:
            return

        converted_count = 0
        deleted_count = 0

        # 遍历文件夹中的所有文件
        for filename in os.listdir(source_folder):
            if filename.endswith('.csv'):
                if "LSV" not in filename:
                    # 如果文件名中不包含"LSV"，删除文件
                    os.remove(os.path.join(source_folder, filename))
                    deleted_count += 1
                    continue

                # 构建完整的文件路径
                csv_file_path = os.path.join(source_folder, filename)
                txt_file_path = os.path.join(source_folder, filename.replace('.csv', '.txt'))

                try:
                    # 读取CSV文件并写入TXT文件
                    with open(csv_file_path, mode='r', newline='', encoding='utf-8') as file:
                        reader = csv.reader(file)
                        with open(txt_file_path, mode='w', encoding='utf-8') as output_file:
                            for row in reader:
                                # 将每行数据用空格连接并写入
                                output_file.write(' '.join(row) + '\n')
                    converted_count += 1
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Error converting file {filename}: {str(e)}")

        # 显示处理结果
        QMessageBox.information(
            self,
            "Conversion Complete",
            f"Successfully converted {converted_count} CSV files to TXT format.\nDeleted {deleted_count} non-LSV files."
        )

    def save_selected_curves(self):
        """保存选中曲线的数据到CSV文件"""
        # 检查是否有数据可以保存
        if not hasattr(self, 'plot_lines') or not self.plot_lines:
            QMessageBox.warning(self, "Warning", "No data to save!")
            return

        # 获取所有选中的曲线数据
        selected_curves = []
        for row in range(self.curve_table.rowCount()):
            # 获取显示列的按钮状态
            button_container = self.curve_table.cellWidget(row, 0)
            if button_container:
                button = button_container.findChild(QPushButton)
                if button and button.isChecked():  # 如果曲线是选中状态
                    curve_info = self.plot_lines[row]
                    selected_curves.append({
                        'original_name': curve_info['original_name'],
                        'label_name': curve_info['label_name'],
                        'x_data': curve_info['x_data'],
                        'y_data': curve_info['y_data']
                    })

        if not selected_curves:
            QMessageBox.warning(self, "Warning", "Please select at least one curve！")
            return

        try:
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Data",
                "",
                "CSV files (*.csv);;All files (*.*)"
            )

            if not file_path:
                return

            # 确保文件扩展名为.csv
            if not file_path.endswith('.csv'):
                file_path += '.csv'

            # 准备数据
            # 找出最长的数据长度
            max_length = max(len(curve['x_data']) for curve in selected_curves)

            # 创建名称行
            name_headers = []
            for curve in selected_curves:
                name_headers.extend([curve['original_name'], curve['label_name']])

            # 创建数据类型行
            data_type_headers = ['Potential (V vs. RHE)', 'Current density (mA/cm²)'] * len(selected_curves)

            # 准备数据行
            data_rows = []
            for i in range(max_length):
                row = []
                for curve in selected_curves:
                    # 如果该索引存在数据，则添加数据，否则添加空值
                    if i < len(curve['x_data']):
                        row.extend([curve['x_data'][i], curve['y_data'][i]])
                    else:
                        row.extend(['', ''])
                data_rows.append(row)

            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(name_headers)  # 写入样品名和标签名
                writer.writerow(data_type_headers)  # 写入数据类型行
                writer.writerows(data_rows)  # 写入数据

            QMessageBox.information(self, "Success", "Data saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving data: {str(e)}")