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

class Calculation(QMainWindow):
    def __init__(self):
        super().__init__()

    def batch_file(self):
        """批量处理函数"""
        if self.test_combo.currentText() == "ORR":
            self.batch_process_ORR() # ORR处理逻辑
        else:
            self.batch_process_U_O_H() # UOR/OER/HER处理逻辑

    def batch_process_ORR(self):
        """ORR专用批量处理函数（向量化优化版）"""
        # 获取电极活性面积
        try:
            area = float(self.area_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid active area!")
            return

        # 创建处理结果文件夹
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select ORR Raw Data Folder",
            os.getcwd()
        )
        # 更新文件夹显示
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        processed_folder = os.path.join(folder_path, "Processed_ORR")
        os.makedirs(processed_folder, exist_ok=True)

        # 预编译正则表达式提升性能
        file_pattern = re.compile(r'^(.*?)_LSV_([24])\.csv$', re.IGNORECASE)
        data_pattern = re.compile(r'^-?\d+\.?\d*([eE][+-]?\d+)?,')

        # 优化数据结构：使用字典存储预处理结果
        sample_data = defaultdict(lambda: {'2': None, '4': None})

        # 第一阶段：并行预处理文件
        with ThreadPoolExecutor() as executor:
            futures = []
            for filename in os.listdir(folder_path):
                if match := file_pattern.match(filename):
                    sample, lsv_num = match.groups()
                    filepath = os.path.join(folder_path, filename)
                    futures.append(
                        executor.submit(self.process_orr_file, filepath, data_pattern)
                    )
                    sample_data[sample][lsv_num] = futures[-1]

        # 第二阶段：向量化计算
        processed_count = 0
        error_log = []
        for sample, data_dict in sample_data.items():
            try:
                # 获取异步处理结果
                data_2 = data_dict['2'].result()
                data_4 = data_dict['4'].result()

                # 数据对齐验证
                if not self.validate_data_alignment(data_2, data_4):
                    error_log.append(f"Sample {sample} data alignment failed")
                    continue

                # 向量化计算核心
                processed_data = self.vectorized_calculation(data_2, data_4, area)

                # 保存结果
                self.save_processed_ORRdata(processed_data, sample, processed_folder)
                processed_count += 1

            except Exception as e:
                error_log.append(f"Processing sample {sample} failed: {str(e)}")
                continue

        # 生成错误报告
        if error_log:
            self.generate_error_report(error_log, processed_folder)

        if processed_count > 0:
            self.load_and_plot_orr_data(processed_folder) # 调用绘图方法

        # 显示处理结果
        result_msg = f"Successfully processed {processed_count} samples\nErrors: {len(error_log)}"
        QMessageBox.information(self, "Processing Complete", result_msg)

    def calculate_onset_potential(self, df):
        """ORR性能计算核心方法-起始电位"""
        try:
            current_series = df['Disk-Density'].astype(float)
            potential_series = df['Potential_RHE'].astype(float)
            # from here to add filtered data, delete the unaffordable data(!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!)

            # 寻找第一个电流密度 > -0.0001 的索引
            condition = current_series > -0.0001
            first_match_index = condition.idxmax() if condition.any() else None

            if first_match_index is not None:
                return potential_series.loc[first_match_index]
            return None
        except Exception as e:
            print(f"Error calculating onset potential: {str(e)}")
            return None

    def calculate_half_potential(self, df):
        """ORR性能计算核心方法-半波电位"""
        try:
            # 找到ABS列的最小值的索引
            abs_min_idx = df['ABS'].idxmin()
            # 获取对应的Potential_RHE值
            half_potential = df.at[abs_min_idx, 'Potential_RHE']
            return half_potential
        except Exception as e:
            print(f"Error calculating half-wave potential: {str(e)}")
            return None

    def vectorized_calculation(self, data_2, data_4, area):
        """执行向量化计算"""
        # 基础数据堆叠
        base_columns = np.column_stack((
            data_2[:, 0],  # Potential
            data_2[:, 1],  # Disk-O2
            data_2[:, 2],  # Ring-O2
            data_4[:, 1],  # Disk-N2
            data_4[:, 2]  # Ring-N2
        ))

        # 预计算公共分母
        area_factor = 1000 / area

        # 向量化密度计算
        disk_density = (base_columns[:, 1] - base_columns[:, 3]) * area_factor + 1e-8
        ring_density = (base_columns[:, 2] - base_columns[:, 4]) * area_factor

        # 异常值处理
        disk_density = np.nan_to_num(disk_density, nan=0.0, posinf=0.0, neginf=0.0)
        ring_density = np.nan_to_num(ring_density, nan=0.0, posinf=0.0, neginf=0.0)

        return np.column_stack((base_columns, disk_density, ring_density))

    def process_orr_file(self, filepath, data_pattern):
        """优化后的文件处理（支持并行）"""
        # 使用生成器表达式减少内存占用
        with open(filepath, 'r', encoding='utf-8') as f:
            skip_rows = 0
            for line in f:
                if data_pattern.match(line):
                    break
                skip_rows += 1
            else:  # 未找到数据行
                return np.empty((0, 3))

        # 使用pandas的low_memory模式提升大文件读取性能
        df = pd.read_csv(filepath,
                         skiprows=skip_rows,
                         header=None,
                         usecols=[0, 1, 2],
                         engine='c',
                         dtype=np.float32,
                         memory_map=True)

        # 使用numpy进行向量化排序
        sorted_idx = np.argsort(df.values[:, 0])
        return df.values[sorted_idx]

    def validate_data_alignment(self, data_2, data_4):
        """向量化数据验证"""
        if len(data_2) != len(data_4):
            return False
        return np.allclose(data_2[:, 0], data_4[:, 0], atol=0.001, rtol=0)

    def save_processed_ORRdata(self, data, sample, folder):
        """优化后的数据保存"""
        # 获取当前参数
        re_type = self.re_combo.currentText()
        try:
            ph = float(self.ph_input.text())
        except ValueError:
            ph = 0.0  # 默认值
            QMessageBox.warning(self, "Warning", "Invalid pH value, using default")

        # 计算RHE电势
        potentials = data[:, 0]  # 第一列为原始电势
        rhe_potentials = potentials + (0.199 if re_type == "Ag/AgCl" else 0.098) + 0.0591 * ph
        # 添加新列Potential_RHE到数据矩阵
        full_data = np.hstack((data, rhe_potentials.reshape(-1, 1)))

        # 列索引定义（根据实际数据结构调整）,计算ABS从而计算半波电位
        POTENTIAL_RHE_COL = 7  # 第8列
        DISK_DENSITY_COL = 5  # 第6列

        # 查找第一个Potential_RHE > 0.2V的Disk-Density值
        P02V = 0.0
        for row in full_data:
            if row[POTENTIAL_RHE_COL] > 0.2:
                P02V = row[DISK_DENSITY_COL]
                break

        # 计算ABS列并追加到数据
        abs_values = np.abs(full_data[:, DISK_DENSITY_COL] - P02V / 2).reshape(-1, 1)
        full_data = np.hstack((full_data, abs_values))

        header = "Potential,Disk-O2,Ring-O2,Disk-N2,Ring-N2,Disk-Density,Ring-Density,Potential_RHE,ABS"
        formats = ['%.4f', '%.7f', '%.7f', '%.8f', '%.8f', '%.10e', '%.10e', '%.4f', '%.10e']

        output_path = os.path.join(folder, f"Processed_{sample}_LSV_ORR.csv")
        np.savetxt(output_path, full_data,
                   fmt=formats,
                   delimiter=',',
                   header=header,
                   comments='')

    def generate_error_report(self, error_log, folder):
        """生成错误报告"""
        error_path = os.path.join(folder, "Processing_Errors.log")
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(f"[{datetime.now():%Y-%m-%d %H:%M}] {msg}" for msg in error_log))

    def load_and_plot_orr_data(self, folder_path):
        """加载处理后的ORR数据并绘图"""
        # 清空现有数据
        self.clear_all()

        # 获取所有处理后的CSV文件
        csv_files = [f for f in os.listdir(folder_path) if f.startswith("Processed_") and f.endswith(".csv")]

        # 确保当前测试类型为ORR
        self.test_combo.setCurrentText("ORR")  # 强制设置测试类型为ORR

        # 更新图表设置前先清空
        self.ax.clear()

        # 重新初始化图表设置
        self.update_plot_settings()

        for filename in csv_files:
            try:
                filepath = os.path.join(folder_path, filename)
                df = pd.read_csv(filepath)

                # 提取数据列（使用更健壮的列名匹配）
                x_col = [col for col in df.columns if 'Potential_RHE' in col][0]
                y_col = [col for col in df.columns if 'Disk-Density' in col][0]

                x_data = df[x_col].values
                y_data = df[y_col].values

                # 生成样品名称
                sample_name = filename.split('_')[1]

                # 绘制曲线（直接使用当前颜色循环）
                line, = self.ax.plot(
                    x_data,
                    y_data,
                    label=sample_name,
                    linewidth=1,
                    picker=5
                )

                # 添加到表格
                self.add_curve_to_table(
                    sample_name=sample_name,
                    color=line.get_color(),
                    line_ref=line
                )

                # 计算性能参数 起始电位 半波电位
                onset_potential = self.calculate_onset_potential(df)
                half_potential = self.calculate_half_potential(df)

                # 保存性能数据
                self.save_performance_data(folder_path, "ORR", sample_name, onset_potential, half_potential)

                # 更新表格数据（使用实际计算结果）
                row = self.curve_table.rowCount() - 1  # 获取最新添加的行
                self.curve_table.item(row, 4).setText(f"{onset_potential:.3f}" if onset_potential else "N/A")
                self.curve_table.item(row, 5).setText(f"{half_potential:.3f}" if half_potential else "N/A")

            except Exception as e:
                    print(f"加载{filename}失败: {str(e)}")

        # 自动调整坐标轴范围
        self.ax.relim()
        self.ax.autoscale_view()

        # 强制刷新图表
        self.ax.legend()  # 确保图例被创建
        self.canvas.draw_idle()
        self.canvas.flush_events()

        # 添加参考线（在数据绘制后添加）
        self.ax.axhline(0, color='gray', linestyle='--', linewidth=1, zorder=1)

    def batch_process_U_O_H(self):
        """批量处理文件夹中的文件-UOR/OER/HER"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )
        # 更新文件夹显示
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        try:
            # 获取文件夹中的所有txt文件
            txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]

            if not txt_files:
                QMessageBox.warning(self, "Warning", "No TXT files found in selected folder")
                return

            # 记录处理结果
            processed_count = 0
            failed_files = []

            # 批量处理每个文件
            for filename in txt_files:
                try:
                    full_path = os.path.join(folder_path, filename)
                    self.process_single_file(full_path)
                    processed_count += 1

                    # 确保参考线保持原始宽度
                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            continue
                except Exception as e:
                    failed_files.append(f"{filename}: {str(e)}")
                    continue

            # 显示处理结果
            result_message = f"Successfully processed {processed_count} files"
            if failed_files:
                result_message += f"\n\nFailed files:\n" + "\n".join(failed_files)

            QMessageBox.information(self, "Processing Complete", result_message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error occurred during batch processing: {str(e)}")

    def batch_ORR_LSV(self):
        """专用ORR LSV绘制方法"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing Processed ORR CSV Files",
            os.getcwd()
        )
        # 更新文件夹显示
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        try:
            # 获取所有处理后的CSV文件
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv') and "Processed_" in f]

            # 清空现有数据
            self.clear_all()

            # 设置当前为ORR模式
            self.test_combo.setCurrentText("ORR")
            self.update_plot_settings()

            for filename in csv_files:
                try:
                    filepath = os.path.join(folder_path, filename)
                    df = pd.read_csv(filepath)

                    # 动态匹配列名
                    x_col = [col for col in df.columns if 'Potential_RHE' in col][0]
                    y_col = [col for col in df.columns if 'Disk-Density' in col][0]

                    x_data = df[x_col].values
                    y_data = df[y_col].values

                    # 生成样品名称
                    sample_name = filename.split('_')[1]

                    # 绘制曲线
                    line, = self.ax.plot(
                        x_data,
                        y_data,
                        label=sample_name,
                        linewidth=1,
                        picker=5
                    )

                    # 添加到表格
                    self.add_curve_to_table(
                        sample_name=sample_name,
                        color=line.get_color(),
                        line_ref=line
                    )

                    # 计算性能参数
                    row = self.curve_table.rowCount() - 1

                    # 使用标准计算方法
                    onset_potential = self.calculate_onset_potential(df)
                    half_potential = self.calculate_half_potential(df)

                    # 更新表格数据
                    self.curve_table.item(row, 4).setText(f"{onset_potential:.3f}" if onset_potential else "N/A")
                    self.curve_table.item(row, 5).setText(f"{half_potential:.3f}" if half_potential else "N/A")

                except Exception as e:
                    print(f"Failed to process {filename}: {str(e)}")
                    continue

            # 设置ORR图表属性
            self.ax.axhline(0, color='gray', linestyle='--', linewidth=1)
            self.ax.legend()
            self.canvas.draw()

            QMessageBox.information(self, "Processing Complete", f"Successfully loaded {len(csv_files)} ORR data files")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"ORR data processing failed: {str(e)}")

    def batch_LSV(self):
        """批量处理CSV文件并绘制LSV图像"""
        if self.test_combo.currentText() == "ORR":
            self.batch_ORR_LSV()  # ORR使用专用方法
            return

        # 选择文件夹
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select folder containing CSV files",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )
        # 更新文件夹显示
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        try:
            # 获取文件夹中的所有CSV文件
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

            if not csv_files:
                QMessageBox.warning(self, "Warning", "No CSV files found in the selected folder.")
                return

            # 获取电极面积
            try:
                area = float(self.area_input.text())
            except ValueError:
                area = 1.0

            # 处理每个CSV文件
            for filename in csv_files:
                try:
                    full_path = os.path.join(folder_path, filename)

                    # 读取CSV文件数据
                    potential_data = []
                    current_data = []

                    with open(full_path, 'r', encoding='utf-8') as file:
                        csv_reader = csv.reader(file)
                        next(csv_reader)  # 跳过表头
                        for row in csv_reader:
                            try:
                                potential = float(row[0])  # 电势值已经是RHE
                                current = float(row[1])  # 电流密度值
                                potential_data.append(potential)
                                current_data.append(current)
                            except (ValueError, IndexError):
                                continue

                    if not potential_data or not current_data:
                        continue

                    # 计算E10和E100
                    test_type = self.test_combo.currentText()
                    target_current_10 = 10
                    target_current_100 = 100

                    # 将数据点按电势排序
                    sorted_data = sorted(zip(potential_data, current_data))
                    potential_data = [p for p, c in sorted_data]
                    current_data = [c for p, c in sorted_data]

                    # 查找E10和E100对应的电势值
                    e10 = self.find_potential_at_current(list(zip(potential_data, current_data)),
                                                         target_current_10, test_type)
                    e100 = self.find_potential_at_current(list(zip(potential_data, current_data)),
                                                          target_current_100, test_type)

                    # 绘制曲线
                    line, = self.ax.plot(potential_data, current_data,
                                         label=os.path.splitext(filename)[0],
                                         linewidth=1,
                                         picker=5)

                    # 添加到表格
                    self.add_curve_to_table(
                        sample_name=os.path.splitext(filename)[0],
                        color=line.get_color(),
                        line_ref=line
                    )

                    # 更新表格中的性能数据
                    row = self.curve_table.rowCount() - 1
                    if e10 != "N/A":
                        if test_type == "UOR":
                            self.curve_table.item(row, 4).setText(f"{float(e10):.3f}")
                        else:  # OER或HER
                            eta10 = (float(e10) - 1.23) * 1000 if test_type == "OER" else abs(float(e10)) * 1000
                            self.curve_table.item(row, 4).setText(f"{eta10:.1f}")

                    if e100 != "N/A":
                        if test_type == "UOR":
                            self.curve_table.item(row, 5).setText(f"{float(e100):.3f}")
                        else:  # OER或HER
                            eta100 = (float(e100) - 1.23) * 1000 if test_type == "OER" else abs(float(e100)) * 1000
                            self.curve_table.item(row, 5).setText(f"{eta100:.1f}")

                except Exception as e:
                    print(f"Error processing file {filename}: {str(e)}")
                    continue

            # 所有曲线保持正常状态
            for line in self.ax.lines:
                if line.get_linestyle() == '--':
                    continue
                line.set_linewidth(1)
                line.set_alpha(1.0)
                line.set_zorder(2)

            # 清除标题
            self.ax.set_title('')

            # 更新图表设置
            if test_type in ["OER", "UOR"]:
                self.ax.set_xlim(1.2, 2.0)
                self.ax.set_ylim(-10, 300)
                self.ax.axhline(y=10, color='gray', linestyle='--', linewidth=1)
                self.ax.axhline(y=100, color='gray', linestyle='--', linewidth=1)
                self.ax.text(1.25, 15, '10 mA cm$^{-2}$', fontsize=10, verticalalignment='bottom')
                self.ax.text(1.25, 105, '100 mA cm$^{-2}$', fontsize=10, verticalalignment='bottom')
            elif test_type == "HER":
                self.ax.set_xlim(-0.4, 0)
                self.ax.set_ylim(-300, 10)
                self.ax.axhline(y=-10, color='gray', linestyle='--', linewidth=1)
                self.ax.axhline(y=-100, color='gray', linestyle='--', linewidth=1)
                self.ax.text(-0.08, -20, '10 mA cm$^{-2}$', fontsize=10, verticalalignment='top')
                self.ax.text(-0.08, -110, '100 mA cm$^{-2}$', fontsize=10, verticalalignment='top')

            # 设置图表属性
            self.ax.set_xlabel('Potential (V vs. RHE)', fontsize=16, fontweight='bold')
            self.ax.set_ylabel('Current density (mA cm$^{-2}$)', fontsize=16, fontweight='bold')
            self.ax.grid(True, linestyle='--', alpha=0.7)
            self.ax.legend()
            self.canvas.draw()

            QMessageBox.information(self, "Processing Complete", f"Successfully processed {len(csv_files)} CSV files")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error occurred during batch processing: {str(e)}")

    def process_single_file(self, filename):
        try:
            # 获取文件夹名和样品名称
            folder_name = os.path.basename(os.path.dirname(filename))
            self.file_path_label.setText(folder_name)
            basename = os.path.basename(filename)
            sample_name = os.path.splitext(basename)[0]
            self.name_input.setText(sample_name)

            # 读取和处理数据
            data_rows = []
            with open(filename, 'r') as file:
                for line in file:
                    processed_line = line.strip().replace(", ", ",").replace("\t", ",").replace(";", ",").split(',')
                    if len(processed_line) < 2:
                        continue
                    try:
                        potential = float(processed_line[0])
                        current = float(processed_line[1])
                        if self.software_combo.currentText() == "CHI760e":
                            current *= 1000
                        data_rows.append([potential, current])
                    except ValueError:
                        continue

            if not data_rows:
                raise ValueError(f"Failed to read valid data from the file")

            # 按电势值排序
            data_rows.sort(key=lambda x: x[0])

            # 计算性能参数
            area = float(self.area_input.text())
            target_current_10 = 10 * area
            target_current_100 = 100 * area
            test_type = self.test_combo.currentText()

            # 查找对应电势值
            e10 = self.find_potential_at_current(data_rows, target_current_10, test_type)
            e100 = self.find_potential_at_current(data_rows, target_current_100, test_type)

            # 更新测量值显示
            self.e10_input.setText(str(e10) if e10 != "N/A" else "N/A")
            self.e100_input.setText(str(e100) if e100 != "N/A" else "N/A")

            # 计算RHE电势
            e10_rhe = None
            e100_rhe = None
            if e10 != "N/A":
                e10_rhe = self.calculate_rhe_potential(float(e10))
                self.e10_result.setText(f"{e10_rhe:.3f}")
            if e100 != "N/A":
                e100_rhe = self.calculate_rhe_potential(float(e100))
                self.e100_result.setText(f"{e100_rhe:.3f}")

            # 处理绘图数据
            potential_data = []
            current_data = []
            for potential, current in data_rows:
                potential_rhe = self.calculate_rhe_potential(potential)
                current_density = current / area
                potential_data.append(potential_rhe)
                current_data.append(current_density)

            # 绘制曲线
            line, = self.ax.plot(potential_data, current_data,
                                 label=sample_name,
                                 linewidth=1,
                                 picker=5)

            # 添加到表格并更新性能数据
            self.add_curve_to_table(
                sample_name=sample_name,
                color=line.get_color(),
                line_ref=line
            )

            # 更新表格中的性能数据
            if hasattr(self, 'plot_lines'):
                row = self.curve_table.rowCount() - 1
                if e10_rhe is not None:
                    if test_type == "UOR":
                        self.curve_table.item(row, 4).setText(f"{e10_rhe:.3f}")
                    elif test_type == "OER":
                        eta10 = (e10_rhe - 1.23) * 1000
                        self.curve_table.item(row, 4).setText(f"{eta10:.1f}")
                    else:  # HER
                        eta10 = abs(e10_rhe) * 1000  # 取绝对值并转换为mV
                        self.curve_table.item(row, 4).setText(f"{eta10:.1f}")

                if e100_rhe is not None:
                    if test_type == "UOR":
                        self.curve_table.item(row, 5).setText(f"{e100_rhe:.3f}")
                    elif test_type == "OER":
                        eta100 = (e100_rhe - 1.23) * 1000
                        self.curve_table.item(row, 5).setText(f"{eta100:.1f}")
                    else:  # HER
                        eta100 = abs(e100_rhe) * 1000  # 取绝对值并转换为mV
                        self.curve_table.item(row, 5).setText(f"{eta100:.1f}")

            # 保存数据
            self.save_processed_data(data_rows, filename)
            self.save_performance_data(filename, test_type, sample_name, e10_rhe, e100_rhe)

            # 更新图表设置
            if test_type in ["OER", "UOR"]:
                self.ax.set_xlim(1.2, 2.0)
                self.ax.set_ylim(-10, 300)
            elif test_type == "HER":
                self.ax.set_xlim(-0.4, 0)
                self.ax.set_ylim(-300, 10)

            # 设置图表属性
            self.ax.set_xlabel('Potential (V vs. RHE)', fontsize=16, fontweight='bold')
            self.ax.set_ylabel('Current density (mA cm$^{-2}$)', fontsize=16, fontweight='bold')
            self.ax.grid(True, linestyle='--', alpha=0.7)
            self.ax.legend()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"File processing error: {str(e)}")

    def find_potential_at_current(self, data, target_current, test_type):
        """查找特定电流值对应的电势
        对于OER/UOR: 找第一个大于目标电流的值
        对于HER: 找第一个小于目标电流(负值)的值
        """
        if not data:
            return "N/A"

        if test_type == "HER":
            target_current = -abs(target_current)  # 确保目标电流为负值
            # 按电流密度从大到小排序（因为是负值）
            sorted_data = sorted(data, key=lambda x: x[1], reverse=True)

            # 查找第一个小于等于目标电流的点
            for potential, current in sorted_data:
                if current <= target_current:  # 找到第一个小于等于目标电流的点
                    return f"{potential:.3f}"
        else:
            # OER/UOR: 按电流密度从小到大排序
            sorted_data = sorted(data, key=lambda x: x[1])

            # 查找第一个大于等于目标电流的点
            for potential, current in sorted_data:
                if current >= target_current:
                    return f"{potential:.3f}"

        return "N/A"

    def calculate_rhe_potential(self, potential):
        """计算RHE电势"""
        try:
            ph = float(self.ph_input.text())
            ref_electrode = self.re_combo.currentText()

            if ref_electrode == "Ag/AgCl":
                return potential + 0.199 + 0.0591 * ph
            else:  # Hg/HgO
                return potential + 0.098 + 0.0591 * ph
        except ValueError:
            raise ValueError("Invalid pH value")

