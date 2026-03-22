# pyinstaller -D -i t.ico --exclude-module tkinter --exclude-module unittest --upx-dir ~/upx-3.96 --add-data "t.ico;." --hidden-import "pandas_libs.tslibs.timedeltas" --clean AutoEchemAnalyzer.py

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

class AllDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Full Data Display")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ['ShowAll', 'Color', 'Original Name', 'Label Name', 'E10/η10', 'E100/η100', 'Test Type'])

        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 85)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 90)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setStretchLastSection(False)

        header = self.table.horizontalHeader()
        header.sectionClicked.connect(self.on_header_clicked) 
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #2c313c;
                color: white;
                padding: 5px;
                border: none;
            }
            QHeaderView::section:first {
                background-color: #4CAF50;  
                border-radius: 3px;
                margin: 2px;
            }
            QHeaderView::section:first:hover {
                background-color: #45a049;
            }
        """)

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

        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

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
        """Toggle visibility for all curves."""
        checked = self.header_toggle_button.isChecked()

        for row in range(self.table.rowCount()):
            button_container = self.table.cellWidget(row, 0)
            if button_container:
                button = button_container.findChild(QPushButton)
                if button:
                    button.setChecked(checked)
                    main_button = self.parent().curve_table.cellWidget(row, 0).findChild(QPushButton)
                    if main_button:
                        main_button.setChecked(checked)

        self.parent.header_toggle_button.setChecked(checked)

    def show_all_data(self):
        """Handle the ALL button click event."""
        pass

    def populate_data(self, main_table):
        """Copy data from the main window table."""
        current_test_type = self.parent().test_combo.currentText()

        if current_test_type == "ORR":
            headers = ['ShowAll', 'Color', 'Original Name', 'Label', 'Onset\nPotential', 'Half-wave\nPotential', 'Test Type']
        else:
            headers = ['ShowAll', 'Color', 'Original Name', 'Label', 'E10/η10', 'E100/η100', 'Test Type']

        self.table.setHorizontalHeaderLabels(headers)

        self.table.setRowCount(0)
        self.plot_lines = []

        self.table.cellChanged.disconnect(self.on_cell_changed)

        for row in range(main_table.rowCount()):
            self.table.insertRow(row)

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

            color_widget = main_table.cellWidget(row, 1)
            if color_widget:
                new_color_widget = QWidget()
                new_color_widget.setStyleSheet(color_widget.styleSheet())
                self.table.setCellWidget(row, 1, new_color_widget)

            for col in range(2, main_table.columnCount()):
                item = main_table.item(row, col)
                if item:
                    new_item = QTableWidgetItem(item.text())
                    if col == 3:
                        new_item.setFlags(item.flags())
                    else:
                        new_item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row, col, new_item)

            e10_item = QTableWidgetItem(main_table.item(row, 4).text())
            e10_item.setTextAlignment(Qt.AlignCenter)
            e10_item.setFlags(e10_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, e10_item)

            e100_item = QTableWidgetItem(main_table.item(row, 5).text())
            e100_item.setTextAlignment(Qt.AlignCenter)
            e100_item.setFlags(e100_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, e100_item)

            test_type_item = QTableWidgetItem(main_table.item(row, 6).text())
            test_type_item.setTextAlignment(Qt.AlignCenter)
            test_type_item.setFlags(test_type_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 6, test_type_item)

            if hasattr(self.parent(), 'plot_lines') and row < len(self.parent().plot_lines):
                self.plot_lines.append(self.parent().plot_lines[row].copy())

        self.table.cellChanged.connect(self.on_cell_changed)

    def on_cell_double_clicked(self, row, column):
        """Handle table cell double-clicks."""
        if column == 1:
            color = QColorDialog.getColor()
            if color.isValid() and hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                color_name = color.name()

                color_widget = QWidget()
                color_widget.setFixedHeight(40)
                color_widget.setStyleSheet(f"background-color: {color_name};")
                self.table.setCellWidget(row, 1, color_widget)

                self.parent().curve_table.cellWidget(row, 1).setStyleSheet(f"background-color: {color_name};")

                self.parent().plot_lines[row]['color'] = color_name
                line = self.parent().plot_lines[row]['line']
                if line.get_visible():
                    line.set_color(color_name)
                    self.parent().canvas.draw()

    def on_cell_changed(self, row, column):
        """Handle table cell content changes."""
        if column == 3:
            if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                new_label = self.table.item(row, column).text()

                self.parent().curve_table.item(row, column).setText(new_label)

                curve_info = self.parent().plot_lines[row]
                curve_info['label_name'] = new_label

                line = curve_info['line']
                if line.get_visible():
                    line.set_label(new_label)
                    self.parent().ax.legend()
                    self.parent().canvas.draw()

    def on_cell_clicked(self, row, column):
        """Handle table cell clicks."""
        if column == 2:
            self.parent().update_data_display(
                self.table.item(row, 3).text(),
                float(self.table.item(row, 4).text()) if self.table.item(row, 4).text() not in ["N/A", ""] else None,
                float(self.table.item(row, 5).text()) if self.table.item(row, 5).text() not in ["N/A", ""] else None
            )

            if hasattr(self.parent(), 'plot_lines') and row < len(self.parent().plot_lines):
                curve_info = self.parent().plot_lines[row]

                for line in self.parent().ax.lines:
                    if line.get_linestyle() == '--':
                        line.set_linewidth(1)
                        continue

                    if line == curve_info['line']:
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(3)

                        label = self.table.item(row, 3).text()
                        e10 = self.table.item(row, 4).text()
                        e100 = self.table.item(row, 5).text()

                    else:
                        line.set_linewidth(1)
                        line.set_alpha(0.3)
                        line.set_zorder(1)

                self.parent().canvas.draw()

    def toggle_curve_visibility(self, row, checked):
        """Toggle curve visibility."""
        main_window = self.parent()
        main_button = main_window.curve_table.cellWidget(row, 0).findChild(QPushButton)
        if main_button.isChecked() != checked:
            main_button.setChecked(checked)
            main_window.toggle_curve_visibility(row, checked)

        all_checked = all(
            self.table.cellWidget(r, 0).findChild(QPushButton).isChecked()
            for r in range(self.table.rowCount())
        )
        header = self.table.horizontalHeader()

    def on_header_clicked(self, logical_index):
        if logical_index == 0:
            current_state = all(
                self.table.cellWidget(r, 0).findChild(QPushButton).isChecked()
                for r in range(self.table.rowCount()))
            new_state = not current_state

            for row in range(self.table.rowCount()):
                button = self.table.cellWidget(row, 0).findChild(QPushButton)
                button.setChecked(new_state)

            main_window = self.parent()
            for row in range(main_window.curve_table.rowCount()):
                main_button = main_window.curve_table.cellWidget(row, 0).findChild(QPushButton)
                main_button.setChecked(new_state)

    def show_context_menu(self, position):
        """Show the context menu."""
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        column = self.table.columnAt(position.x())

        if column == 3:
            menu = QMenu(self)

            font_menu = menu.addMenu("Font Settings")

            reset_action = font_menu.addAction("Reset Default")
            reset_action.triggered.connect(lambda: self.parent().reset_label_font(row))
            font_menu.addSeparator()

            font_size_menu = font_menu.addMenu("Font Size")
            for size in [8, 10, 12, 14, 16, 18, 20]:
                action = font_size_menu.addAction(f"{size}pt")
                action.triggered.connect(lambda checked, s=size: self.parent().set_label_font_size(row, s))

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

            script_menu = menu.addMenu("Superscript/Subscript")
            superscript_action = script_menu.addAction("Add Superscript")
            superscript_action.triggered.connect(lambda: self.parent().add_script(row, "super"))
            subscript_action = script_menu.addAction("Add Subscript")
            subscript_action.triggered.connect(lambda: self.parent().add_script(row, "sub"))

            menu.exec(self.table.viewport().mapToGlobal(position))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        font = QFont("Arial",10)
        QApplication.instance().setFont(font)
        self.defaults = self.load_defaults()

        self.setWindowTitle('AutoEchemAnalyzer')
        self.setFixedSize(1400, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(20, 0, 10, 10)

        left_widget.setFixedWidth(800)

        right_container = QWidget()
        right_container_layout = QVBoxLayout(right_container)
        right_container_layout.setSpacing(15)

        upper_container = QWidget()
        upper_layout = QHBoxLayout(upper_container)
        upper_layout.setSpacing(15)

        center_widget = QWidget()
        right_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        right_layout = QVBoxLayout(right_widget)

        self.create_parameter_group(center_layout)
        self.create_data_group(center_layout)

        self.create_button_group(right_layout)

        center_widget.setFixedWidth(350)
        right_widget.setFixedWidth(170)

        upper_layout.addWidget(center_widget)
        upper_layout.addWidget(right_widget)

        note_container = QWidget()
        note_layout = QHBoxLayout(note_container)
        self.create_note_area(note_layout)

        right_container_layout.addWidget(upper_container)
        right_container_layout.addWidget(note_container)

        plot_container = QWidget()
        plot_container.setFixedHeight(750)
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.create_plot_area(plot_layout)
        left_layout.addWidget(plot_container)
        self.legend_visible = True

        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_container)

        self.area_btn.clicked.connect(self.change_current)

        current_test_type = self.defaults.get('test_options0', 'UOR')
        self.test_combo.setCurrentText(current_test_type)
        self.update_parameters(current_test_type)
        self.update_interface_settings()
        self.update_button_visibility(current_test_type)

        self.test_combo.currentTextChanged.connect(
            lambda: self.update_button_visibility(self.test_combo.currentText()))

    def update_parameters(self, test_type):
        """Switch parameters based on the selected test type."""
        if test_type == "ORR":
            re_value = self.defaults.get('orr_RE_options0', 'Ag/AgCl')
            area_value = self.defaults.get('orr_inputs_area', '0.2475')
            ph_value = self.defaults.get('orr_inputs_pH', '13')
            self.area_btn.setVisible(False)
        else:
            re_value = self.defaults.get('RE_options0', 'Hg/HgO')
            area_value = self.defaults.get('inputs_area', '1')
            ph_value = self.defaults.get('inputs_pH', '14')
            self.area_btn.setVisible(True)

        self.re_combo.setCurrentText(re_value)
        self.area_input.setText(area_value)
        self.ph_input.setText(ph_value)

        self.update_table_headers()

        self.update_button_visibility(test_type)
        if test_type == "ORR":
            self.update_table_headers()

        self.test_combo.currentTextChanged.connect(self.update_parameters)

    def on_header_clicked(self, logical_index):
        """Handle main table header clicks."""
        if logical_index == 0:
            current_state = all(
                self.curve_table.cellWidget(row, 0).findChild(QPushButton).isChecked()
                for row in range(self.curve_table.rowCount()))

            new_state = not current_state
            for row in range(self.curve_table.rowCount()):
                button = self.curve_table.cellWidget(row, 0).findChild(QPushButton)
                button.setChecked(new_state)

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
        param_layout.setLabelAlignment(Qt.AlignLeft)
        param_layout.setFormAlignment(Qt.AlignLeft)

        input_width = 150

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
        param_layout.addRow("Select UOR/OER/HER/ORR:", self.test_combo)

        self.re_combo = QComboBox()
        self.re_combo.setStyleSheet("""QComboBox {font: 14px Arial;}""")
        self.re_combo.addItems(["Ag/AgCl", "Hg/HgO"])
        self.re_combo.setCurrentText("Hg/HgO")
        self.re_combo.setFixedWidth(input_width- 10)
        param_layout.addRow("Reference Electrode:", self.re_combo)

        self.comp_combo = QComboBox()
        self.comp_combo.setStyleSheet("""QComboBox {font: 14px Arial;}""")
        self.comp_combo.addItems(["Manual", "Auto"])
        comp_value = self.defaults.get('iR_options0', 'Auto')
        self.comp_combo.setCurrentText(comp_value)
        self.comp_combo.setFixedWidth(input_width- 10)
        self.comp_combo.currentTextChanged.connect(self.on_comp_method_changed)
        param_layout.addRow("Compensation Method:", self.comp_combo)

        self.ohm_input = QLineEdit()
        self.ohm_input.setFixedWidth(input_width- 10)
        self.ohm_input.setEnabled(False)
        param_layout.addRow("Manual R (Ω):", self.ohm_input)

        self.percentage_input = QLineEdit("100")
        self.percentage_input.setFixedWidth(input_width- 10)
        self.percentage_input.setEnabled(False)
        param_layout.addRow("Compensation (%):", self.percentage_input)

        area_widget = QWidget()
        area_layout = QHBoxLayout(area_widget)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_layout.setSpacing(5)
        self.area_input = QLineEdit("1")
        self.area_input.setFixedWidth(input_width-10)
        self.area_btn = QPushButton("Convert")
        self.area_btn.setFixedWidth(60)
        self.area_btn.setVisible(False)
        area_layout.addWidget(self.area_input)
        area_layout.addWidget(self.area_btn)
        area_layout.addStretch()
        param_layout.addRow("Active Area (cm²):", area_widget)

        self.ph_input = QLineEdit("14")
        self.ph_input.setFixedWidth(input_width - 10)
        param_layout.addRow("Solution pH:", self.ph_input)

        param_group.setFixedSize(340, 220)
        layout.addWidget(param_group)

    def create_plot_area(self, layout):
        """Create the LSV plot area."""
        plt.rcParams['font.family'] = ['Arial']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['text.usetex'] = False
        plt.rcParams['mathtext.fontset'] = 'stix'

        self.figure = Figure(figsize=(8, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        toolbar_container = QWidget()
        toolbar_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(2)

        toolbar = NavigationToolbar(self.canvas, None)
        toolbar.setStyleSheet(
            "QToolButton { min-width: 18px; max-width: 18px; min-height: 20px; max-height: 20px; padding: 1px; }")
        toolbar.setIconSize(QSize(19, 19))

        toolbar.layout().setSpacing(2)

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
        save_button.clicked.connect(self.save_selected_curves)

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

        self.all_button = QPushButton("ALL")
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
        self.label_button = label_button

        toolbar_layout.addWidget(toolbar)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.all_button)
        toolbar_layout.addWidget(label_button)
        toolbar_layout.addWidget(grid_button)
        toolbar_layout.addWidget(clear_button)
        toolbar_layout.addWidget(reset_button)
        toolbar_layout.addWidget(save_button)

        self.curve_table = QTableWidget()
        self.curve_table.setMinimumHeight(130)
        self.curve_table.setMaximumHeight(150)
        self.curve_table.setColumnCount(7)

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
                background-color: #4CAF50;  
                border-radius: 3px;
                margin: 2px;
            }
            QHeaderView::section:first:hover {
                background-color: #45a049;
            }
        """)

        header_widget = QWidget()
        header_widget.setFixedHeight(40)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        self.all_button.clicked.connect(self.show_all_data)

        header_layout.setAlignment(Qt.AlignCenter)

        proxy = QWidget()
        proxy.setFixedHeight(25)
        proxy_layout = QHBoxLayout(proxy)
        proxy_layout.setContentsMargins(0, 0, 0, 0)
        proxy_layout.setSpacing(0)
        proxy_layout.addWidget(header_widget)

        header = self.curve_table.horizontalHeader()
        header.viewport().stackUnder(proxy)
        proxy.setParent(header)
        proxy.setGeometry(header.sectionPosition(0), 0, header.sectionSize(0), header.height())
        proxy.show()

        self.update_table_headers()

        self.curve_table.setColumnWidth(0, 70)
        self.curve_table.setColumnWidth(1, 80)
        self.curve_table.setColumnWidth(2, 150)
        self.curve_table.setColumnWidth(3, 150)
        self.curve_table.setColumnWidth(4, 95)
        self.curve_table.setColumnWidth(5, 95)
        self.curve_table.setColumnWidth(6, 80)

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

        self.update_plot_settings()
        self.curve_table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

        def on_pick(event):
            if event.artist in self.ax.lines:
                selected_line = event.artist
                for line in self.ax.lines:
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
                event.canvas.stop_event_loop()

        def on_canvas_click(event):
            if event.inaxes:
                clicked_line = None
                for line in self.ax.lines:
                    if line.get_linestyle() == '--':
                        line.set_linewidth(1)
                        continue

                    xdata = line.get_xdata()
                    ydata = line.get_ydata()

                    for i in range(len(xdata) - 1):
                        dist = point_to_line_distance(event.xdata, event.ydata,
                                                      xdata[i], ydata[i],
                                                      xdata[i + 1], ydata[i + 1])
                        if dist < 0.01:
                            clicked_line = line
                            break
                    if clicked_line:
                        break

                if clicked_line:
                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            line.set_linewidth(1)
                            continue

                        if line == clicked_line:
                            line.set_linewidth(2)
                            line.set_alpha(1.0)
                            line.set_zorder(3)

                            for row in range(self.curve_table.rowCount()):
                                if self.plot_lines[row]['line'] == line:
                                    label = self.curve_table.item(row, 3).text()
                                    e10 = self.curve_table.item(row, 4).text()
                                    e100 = self.curve_table.item(row, 5).text()

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
                else:
                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            line.set_linewidth(1)
                            continue
                        line.set_linewidth(1)
                        line.set_alpha(1.0)
                        line.set_zorder(2)
                    self.ax.set_title('')

            else:
                for line in self.ax.lines:
                    if line.get_linestyle() == '--':
                        line.set_linewidth(1)
                        continue
                    line.set_linewidth(1)
                    line.set_alpha(1.0)
                    line.set_zorder(2)
                self.ax.set_title('')

            self.canvas.draw()

        def point_to_line_distance(px, py, x1, y1, x2, y2):
            l2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
            if l2 == 0:
                return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5

            t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2))

            proj_x = x1 + t * (x2 - x1)
            proj_y = y1 + t * (y2 - y1)

            return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

        def on_table_clicked(row, column):
            if column == 2:
                curve_info = self.plot_lines[row]
                for line in self.ax.lines:
                    if line.get_linestyle() == '--':
                        line.set_linewidth(1)
                        continue

                    if line == curve_info['line']:
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(3)

                        label = self.curve_table.item(row, 3).text()
                        e10 = self.curve_table.item(row, 4).text()
                        e100 = self.curve_table.item(row, 5).text()

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
                for line in self.ax.lines:
                    if line.get_linestyle() == '--':
                        continue

                    line.set_linewidth(1)
                    line.set_alpha(1.0)
                    line.set_zorder(2)
                    self.ax.set_title('')

                self.canvas.draw()

        self.canvas.mpl_connect('pick_event', on_pick)
        self.canvas.mpl_connect('button_press_event', on_canvas_click)
        self.curve_table.cellClicked.connect(on_table_clicked)

        self.zoom_enabled = False
        self.current_highlight_index = None

        def on_mouse_middle_click(event):
            if event.button == 2:
                self.zoom_enabled = not self.zoom_enabled
                if not self.zoom_enabled:
                    self.current_highlight_index = None
                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            continue
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(2)
                    self.canvas.draw()

        def on_scroll(event):
            if self.zoom_enabled:
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
                data_lines = [line for line in self.ax.lines if line.get_linestyle() != '--']
                if not data_lines:
                    return

                if self.current_highlight_index is None:
                    self.current_highlight_index = 0 if event.button == 'up' else len(data_lines) - 1
                else:
                    if event.button == 'up':
                        self.current_highlight_index = (self.current_highlight_index + 1) % len(data_lines)
                    else:
                        self.current_highlight_index = (self.current_highlight_index - 1) % len(data_lines)

                for i, line in enumerate(data_lines):
                    if i == self.current_highlight_index:
                        line.set_linewidth(2)
                        line.set_alpha(1.0)
                        line.set_zorder(3)

                        for row in range(self.curve_table.rowCount()):
                            if self.plot_lines[row]['line'] == line:
                                label = self.curve_table.item(row, 3).text()
                                e10 = self.curve_table.item(row, 4).text()
                                e100 = self.curve_table.item(row, 5).text()

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

        self.canvas.mpl_connect('button_press_event', on_mouse_middle_click)
        self.canvas.mpl_connect('scroll_event', on_scroll)

        layout.addWidget(self.canvas)
        layout.addWidget(toolbar_container)
        layout.addWidget(self.curve_table)

        self.curve_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.curve_table.cellChanged.connect(self.on_cell_changed)

        self.curve_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.curve_table.customContextMenuRequested.connect(self.show_context_menu)

    def update_chart_title(self, label, e10, e100):
        """Update the plot title based on the current test type."""
        current_test_type = self.test_combo.currentText()
        if current_test_type == "ORR":
            title = f'{label}\nOnset Potential: {e10}   Half-wave Potential: {e100}'
        else:
            title = f'{label}\nE10/η10: {e10}   E100/η100: {e100}'

        self.ax.set_title(title, pad=10, fontsize=12)
        self.canvas.draw_idle()

    def update_table_headers(self):
        """Update table headers dynamically while preserving style."""
        current_test_type = self.test_combo.currentText()

        scroll_pos = self.curve_table.verticalScrollBar().value()

        if current_test_type == "ORR":
            headers = ['ShowAll', 'Color', 'Original Name', 'Label Name', 'Onset\nPotential', 'Half-wave\nPotential', 'Test Type']
            for row in range(self.curve_table.rowCount()):
                self.curve_table.item(row, 4).setText("")
                self.curve_table.item(row, 5).setText("")
        else:
            headers = ['ShowAll', 'Color', 'Original Name', 'Label Name', 'E10/η10', 'E100/η100', 'Test Type']

        self.curve_table.setHorizontalHeaderLabels(headers)

        self.curve_table.verticalScrollBar().setValue(scroll_pos)

        self.curve_table.blockSignals(False)
        self.curve_table.viewport().update()

    def show_all_data(self):
        """Show the full data dialog."""
        dialog = AllDataDialog(self)
        dialog.populate_data(self.curve_table)
        dialog.exec()

    def toggle_legend(self):
        """Toggle legend visibility."""
        is_checked = self.label_button.isChecked()
        self.legend_visible = is_checked

        legend = self.ax.get_legend()
        if legend:
            legend.set_visible(is_checked)

        if is_checked:
            visible_lines = [line for line in self.ax.lines
                             if line.get_visible() and line.get_linestyle() != '--']
            if visible_lines:
                if legend:
                    legend.set_visible(True)
                else:
                    self.ax.legend()
        else:
            if legend:
                legend.set_visible(False)

        self.canvas.draw()

    def toggle_grid(self):
        """Toggle plot grid visibility."""
        is_checked = self.grid_button.isChecked()
        if is_checked:
            self.ax.grid(True, linestyle='--', alpha=0.7)
        else:
            self.ax.grid(False)
        self.canvas.draw()

    def toggle_all_curves(self):
        """Toggle visibility for all curves."""
        checked = self.header_toggle_button.isChecked()

        for row in range(self.table.rowCount()):
            button_container = self.table.cellWidget(row, 0)
            if button_container:
                button = button_container.findChild(QPushButton)
                if button:
                    button.setChecked(checked)
                    main_button = self.parent.curve_table.cellWidget(row, 0).findChild(QPushButton)
                    if main_button:
                        main_button.setChecked(checked)

        self.parent.header_toggle_button.setChecked(checked)

    def clear_all(self):
        """Clear all curves and table data."""
        self.ax.clear()

        self.update_plot_settings()

        self.curve_table.setRowCount(0)

        if hasattr(self, 'plot_lines'):
            self.plot_lines = []

        self.canvas.draw()

    def save_selected_curves(self):
        """Save selected curve data to a CSV file."""
        if not hasattr(self, 'plot_lines') or not self.plot_lines:
            QMessageBox.warning(self, "Warning", "No data to save!")
            return

        selected_curves = []
        for row in range(self.curve_table.rowCount()):
            button_container = self.curve_table.cellWidget(row, 0)
            if button_container:
                button = button_container.findChild(QPushButton)
                if button and button.isChecked():
                    curve_info = self.plot_lines[row]
                    selected_curves.append({
                        'original_name': curve_info['original_name'],
                        'label_name': curve_info['label_name'],
                        'x_data': curve_info['x_data'],
                        'y_data': curve_info['y_data']
                    })

        if not selected_curves:
            QMessageBox.warning(self, "Warning", "Please select at least one curve!")
            return

        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Data",
                "",
                "CSV files (*.csv);;All files (*.*)"
            )

            if not file_path:
                return

            if not file_path.endswith('.csv'):
                file_path += '.csv'

            max_length = max(len(curve['x_data']) for curve in selected_curves)

            name_headers = []
            for curve in selected_curves:
                name_headers.extend([curve['original_name'], curve['label_name']])

            data_type_headers = ['Potential (V vs. RHE)', 'Current density (mA/cm²)'] * len(selected_curves)

            data_rows = []
            for i in range(max_length):
                row = []
                for curve in selected_curves:
                    if i < len(curve['x_data']):
                        row.extend([curve['x_data'][i], curve['y_data'][i]])
                    else:
                        row.extend(['', ''])
                data_rows.append(row)

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(name_headers)
                writer.writerow(data_type_headers)
                writer.writerows(data_rows)

            QMessageBox.information(self, "Success", "Data saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving data: {str(e)}")

    def add_curve_to_table(self, sample_name, color, line_ref):
        """Add a curve to the table and initialize its display state."""
        row = self.curve_table.rowCount()
        self.curve_table.insertRow(row)

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

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(toggle_button)

        self.curve_table.setCellWidget(row, 0, button_container)

        color_widget = QWidget()
        color_widget.setStyleSheet(f"background-color: {color};")
        self.curve_table.setCellWidget(row, 1, color_widget)

        original_name_item = QTableWidgetItem(sample_name)
        original_name_item.setFlags(original_name_item.flags() & ~Qt.ItemIsEditable)
        self.curve_table.setItem(row, 2, original_name_item)

        label_name_item = QTableWidgetItem(sample_name)
        self.curve_table.setItem(row, 3, label_name_item)

        e10_item = QTableWidgetItem("")
        e10_item.setTextAlignment(Qt.AlignCenter)
        self.curve_table.setItem(row, 4, e10_item)
        e100_item = QTableWidgetItem("")
        e100_item.setTextAlignment(Qt.AlignCenter)
        self.curve_table.setItem(row, 5, e100_item)

        test_type_item = QTableWidgetItem(self.test_combo.currentText())
        test_type_item.setTextAlignment(Qt.AlignCenter)
        test_type_item.setFlags(test_type_item.flags() & ~Qt.ItemIsEditable)
        self.curve_table.setItem(row, 6, test_type_item)

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
            'test_type': self.test_combo.currentText()
        })

        toggle_button.toggled.connect(lambda checked, r=row: self.toggle_curve_visibility(r, checked))

    def on_cell_double_clicked(self, row, column):
        """Handle table cell double-clicks."""
        if column == 1:
            color = QColorDialog.getColor()
            if color.isValid() and hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                color_name = color.name()
                curve_info = self.plot_lines[row]

                color_widget = QWidget()
                color_widget.setStyleSheet(f"background-color: {color_name};")
                self.curve_table.setCellWidget(row, 1, color_widget)

                curve_info['color'] = color_name

                line = curve_info['line']
                if line.get_visible():
                    line.remove()
                    new_line, = self.ax.plot(
                        curve_info['x_data'],
                        curve_info['y_data'],
                        color=color_name,
                        label=curve_info['label_name'],
                        linewidth=curve_info['linewidth']
                    )
                    curve_info['line'] = new_line
                    self.plot_lines[row]['line'] = new_line

                    self.ax.legend()

                    self.canvas.draw()

    def on_cell_changed(self, row, column):
        """Handle table cell content changes."""
        if column == 3:
            if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
                new_label = self.curve_table.item(row, column).text()
                curve_info = self.plot_lines[row]

                curve_info['label_name'] = new_label

                line = curve_info['line']
                if line.get_visible():
                    line.remove()
                    new_line, = self.ax.plot(
                        curve_info['x_data'],
                        curve_info['y_data'],
                        color=curve_info['color'],
                        label=new_label,
                        linewidth=curve_info['linewidth']
                    )
                    curve_info['line'] = new_line
                    self.plot_lines[row]['line'] = new_line

                    self.ax.legend()

                    self.canvas.draw()

    def toggle_curve_visibility(self, row, checked):
        """Toggle curve visibility."""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]

            current_legend_state = self.legend_visible

            if checked:
                curve_info['line'].set_alpha(1.0)
                curve_info['line'].set_label(curve_info['label_name'])
                curve_info['visible'] = True
                for info in self.plot_lines:
                    if info.get('visible', False):
                        info['line'].set_alpha(1.0)
            else:
                curve_info['line'].set_alpha(0.0)
                curve_info['line'].set_label('_' + curve_info['label_name'])
                curve_info['visible'] = False

            handles = []
            labels = []
            for info in self.plot_lines:
                if info.get('visible', False):
                    handles.append(info['line'])
                    labels.append(info['label_name'])

            if handles:
                legend = self.ax.legend(handles, labels)
                legend.set_visible(current_legend_state)
            else:
                if self.ax.get_legend():
                    self.ax.get_legend().remove()

            self.label_button.setChecked(current_legend_state)

            self.canvas.draw()

    def show_context_menu(self, position):
        """Show the context menu."""
        item = self.curve_table.itemAt(position)
        if not item:
            return

        row = item.row()
        column = self.curve_table.columnAt(position.x())

        if column == 3:
            menu = QMenu(self)

            font_menu = menu.addMenu("Font Settings")

            reset_action = font_menu.addAction("Reset Default")
            reset_action.triggered.connect(lambda: self.reset_label_font(row))
            font_menu.addSeparator()

            font_size_menu = font_menu.addMenu("Font Size")
            for size in [8, 10, 12, 14, 16, 18, 20]:
                action = font_size_menu.addAction(f"{size}pt")
                action.triggered.connect(lambda checked, s=size: self.set_label_font_size(row, s))

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

            script_menu = menu.addMenu("Superscript/Subscript")
            superscript_action = script_menu.addAction("Add Superscript")
            superscript_action.triggered.connect(lambda: self.add_script(row, "super"))
            subscript_action = script_menu.addAction("Add Subscript")
            subscript_action.triggered.connect(lambda: self.add_script(row, "sub"))

            menu.exec(self.curve_table.viewport().mapToGlobal(position))

    def reset_label_font(self, row):
        """Reset label font to default while keeping superscript/subscript markers."""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]
            current_text = curve_info['label_name']

            import re

            superscripts = re.findall(r'\$\^{([^}]+)}\$', current_text)
            subscripts = re.findall(r'\$_{([^}]+)}\$', current_text)

            base_text = curve_info['original_name']

            new_text = base_text
            for sup in superscripts:
                new_text += f'$^{{{sup}}}$'
            for sub in subscripts:
                new_text += f'$_{{{sub}}}$'

            self.curve_table.item(row, 3).setText(new_text)
            curve_info['line'].set_label(new_text)
            curve_info['label_name'] = new_text

            self.ax.legend(prop={'size': 'medium'})
            self.canvas.draw()

    def set_label_font_size(self, row, size):
        """Set label font size."""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]
            current_text = curve_info['label_name']

            self.curve_table.item(row, 3).setText(current_text)
            curve_info['line'].set_label(current_text)
            curve_info['label_name'] = current_text

            self.ax.legend(prop={'size': size})

            legend = self.ax.get_legend()
            if legend:
                was_visible = legend.get_visible()
                self.ax.legend(prop={'size': size})
                self.ax.get_legend().set_visible(was_visible)

            self.canvas.draw()

    def set_label_font_style(self, row, style):
        """Set label font style."""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            curve_info = self.plot_lines[row]
            current_text = curve_info['label_name']

            text = current_text.replace('\\bf', '').replace('\\it', '') \
                .replace('\\rm', '').replace('$', '')

            if 'bold' in style and 'italic' in style:
                new_text = f"$\\bf\\it{{{text}}}$"
            elif 'bold' in style:
                new_text = f"$\\bf{{{text}}}$"
            elif 'italic' in style:
                new_text = f"$\\it{{{text}}}$"
            else:
                new_text = f"$\\rm{{{text}}}$"

            self.curve_table.item(row, 3).setText(new_text)
            curve_info['line'].set_label(new_text)
            curve_info['label_name'] = new_text

            legend = self.ax.get_legend()
            if legend:
                was_visible = legend.get_visible()
                self.ax.legend()
                self.ax.get_legend().set_visible(was_visible)

            self.canvas.draw()

    def add_script(self, row, script_type):
        """Add superscript or subscript to the label."""
        if hasattr(self, 'plot_lines') and row < len(self.plot_lines):
            current_text = self.curve_table.item(row, 3).text()

            text, ok = QInputDialog.getText(self,
                                            "Add " + ("Superscript" if script_type == "super" else "Subscript"),
                                            "Please enter " + ("superscript" if script_type == "super" else "subscript") + " text:")

            if ok and text:
                if script_type == "super":
                    new_text = f"{current_text}$^{text}$"
                else:
                    new_text = f"{current_text}$_{text}$"

                self.curve_table.item(row, 3).setText(new_text)
                curve_info = self.plot_lines[row]
                curve_info['line'].set_label(new_text)
                curve_info['label_name'] = new_text

                plt.rcParams['text.usetex'] = False
                plt.rcParams['mathtext.default'] = 'regular'
                self.ax.legend()
                self.canvas.draw()

    def update_coordinates(self, event):
        """Update coordinate display."""
        if event.inaxes:
            self.coord_label.setText(f"Coordinates: x={event.xdata:.3f}, y={event.ydata:.3f}")
        else:
            self.coord_label.setText("")

    def reset_view(self):
        """Reset the view to the initial limits."""
        if self.init_xlim is not None and self.init_ylim is not None:
            self.ax.set_xlim(self.init_xlim)
            self.ax.set_ylim(self.init_ylim)
            self.canvas.draw()

    def on_mouse_press(self, event):
        """Handle mouse press events."""
        if event.button == 1:
            self.dragging = True
            self.last_x = event.xdata
            self.last_y = event.ydata

    def on_mouse_release(self, event):
        """Handle mouse release events."""
        self.dragging = False

    def on_mouse_move(self, event):
        """Handle mouse move events."""
        if self.dragging and event.xdata is not None and event.ydata is not None:
            dx = event.xdata - self.last_x
            dy = event.ydata - self.last_y

            x1, x2 = self.ax.get_xlim()
            y1, y2 = self.ax.get_ylim()

            self.ax.set_xlim(x1 - dx, x2 - dx)
            self.ax.set_ylim(y1 - dy, y2 - dy)

            self.last_x = event.xdata
            self.last_y = event.ydata
            self.canvas.draw()

    def on_scroll(self, event):
        """Handle mouse wheel events."""
        x1, x2 = self.ax.get_xlim()
        y1, y2 = self.ax.get_ylim()

        center_x = event.xdata if event.xdata else (x1 + x2) / 2
        center_y = event.ydata if event.ydata else (y1 + y2) / 2

        scale_factor = 1.1 if event.button == 'up' else 0.9

        dx = (x2 - x1) * scale_factor
        dy = (y2 - y1) * scale_factor

        self.ax.set_xlim(center_x - dx / 2, center_x + dx / 2)
        self.ax.set_ylim(center_y - dy / 2, center_y + dy / 2)

        self.canvas.draw()

    def update_interface_settings(self):
        """Update both plot and table settings."""
        self.update_plot_settings()
        self.update_table_headers()
        self.update_parameters(self.test_combo.currentText())
        self.update_button_visibility(self.test_combo.currentText())

        test_type = self.test_combo.currentText()

        self.area_btn.setVisible(test_type != "ORR")

        if test_type == "ORR":
            self.result_label.setText("Characteristic Potential (V vs. RHE)")
            self.e10_label.setText("Onset Potential:")
            self.e100_label.setText("Half-wave Potential:")
            self.e10_label.setFixedWidth(120)
            self.e100_label.setFixedWidth(120)
            self.e10_result.setVisible(True)
            self.e100_result.setVisible(True)
        else:
            self.result_label.setText("Results (V vs. RHE)")
            self.e10_label.setText("10 mA/cm²:")
            self.e100_label.setText("100 mA/cm²:")

    def update_plot_settings(self):
        """Update plot settings based on the selected test type."""
        self.ax.clear()
        test_type = self.test_combo.currentText()

        from matplotlib.transforms import blended_transform_factory
        transform = blended_transform_factory(self.ax.transAxes, self.ax.transData)

        x_relative_position = 0.01

        if test_type in ["OER", "UOR"]:
            self.ax.set_xlim(1.2, 2.0)
            self.ax.set_ylim(-10, 300)
            self.ax.set_yticks(range(0, 301, 100))

            self.ax.axhline(y=10, color='gray', linestyle='--', linewidth=1, zorder=1)
            self.ax.axhline(y=100, color='gray', linestyle='--', linewidth=1, zorder=1)

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

            self.ax.axhline(y=-10, color='gray', linestyle='--', linewidth=1, zorder=1)
            self.ax.axhline(y=-100, color='gray', linestyle='--', linewidth=1, zorder=1)

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

        self.ax.set_xlabel('Potential (V vs. RHE)', fontsize=16, fontweight='bold')
        self.ax.set_ylabel('Current density (mA cm$^{-2}$)', fontsize=16, fontweight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.7)

        self.init_xlim = self.ax.get_xlim()
        self.init_ylim = self.ax.get_ylim()

        self.ax.tick_params(axis='both', which='major', labelsize=12)

        if test_type == "ORR":
            self.ax.yaxis.set_major_locator(MultipleLocator(1))
        else:
            self.ax.yaxis.set_major_locator(MultipleLocator(100))
        self.ax.yaxis.set_minor_locator(NullLocator())

        self.figure.patch.set_facecolor('white')
        self.ax.set_facecolor('white')

        self.canvas.draw()
        self.update_table_headers()

    def create_note_area(self, layout):
        note_group = QGroupBox()
        note_group.setStyleSheet("""
            QGroupBox {
                margin:0;
                padding:5px;
            }
        """)

        main_layout = QVBoxLayout(note_group)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

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

        formula1 = QLabel("Ag/AgCl: E(RHE) = E(test) + 0.199 + 0.0591 × pH")
        formula1.setStyleSheet("""
                QLabel {
                    font: 14px Arial;
                }
            """)
        formula2 = QLabel("Hg/HgO: E(RHE) = E(test) + 0.098 + 0.0591 × pH")
        formula2.setStyleSheet("""
                QLabel {
                    font: 14px Arial;
                }
            """)
        main_layout.addWidget(formula1)
        main_layout.addWidget(formula2)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(10)

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
        hbox.addWidget(output_container, 5)

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
        remarks.setWordWrap(True)
        remark_layout.addWidget(remark_label)
        remark_layout.addWidget(remarks)
        hbox.addWidget(remark_container, 5)

        main_layout.addLayout(hbox)

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

        input_width = 150

        self.software_combo = QComboBox()
        self.software_combo.setStyleSheet("""QComboBox {font: 14px Arial;}""")
        self.software_combo.addItems(["CHI760e", "EC-lab", "DHElecChem"])
        self.software_combo.setFixedWidth(input_width + 25)
        data_layout.addRow("Software:", self.software_combo)

        self.file_path_label = QLabel("----------")
        self.file_path_label.setFixedWidth(input_width + 25)
        data_layout.addRow("Folder:", self.file_path_label)

        self.name_input = QLineEdit()
        self.name_input.setFixedWidth(input_width + 25)
        data_layout.addRow("Sample Name:", self.name_input)

        self.result_label = QLabel("Results (V vs. RHE)")
        data_layout.addRow(self.result_label)
        self.e10_label = QLabel("10 mA/cm²:")
        self.e100_label = QLabel("100 mA/cm²:")

        self.e10_result = QLineEdit()
        self.e100_result = QLineEdit()

        data_layout.addRow(self.e10_label, self.e10_result)
        data_layout.addRow(self.e100_label, self.e100_result)
        data_group.setFixedSize(340, 150)
        layout.addWidget(data_group)

    def update_folder_display(self, folder_path):
        """Update the folder name shown in the interface."""
        if folder_path:
            folder_name = os.path.basename(folder_path)
            self.file_path_label.setText(folder_name)
        else:
            self.file_path_label.setText("No folder selected")

    def update_data_display(self, label, e10_value, e100_value):
        """Update the data display panel based on the selected test type."""
        current_test = self.test_combo.currentText()

        self.name_input.setText(label)

        if current_test == "ORR":
            self.e10_label.setText("Onset Potential:")
            self.e100_label.setText("Half-wave Potential:")
        else:
            self.e10_label.setText("10 mA/cm²:")
            self.e100_label.setText("100 mA/cm²:")

        self.e10_result.setText(f"{e10_value:.3f}" if e10_value else "N/A")
        self.e100_result.setText(f"{e100_value:.3f}" if e100_value else "N/A")

        self.update_chart_title(label, e10_value, e100_value)

    def update_button_visibility(self, test_type):
        """Update button visibility based on the selected test type."""
        if test_type == "ORR":
            self.button_container_layout.setContentsMargins(0, 80, 0, 0)
        else:
            self.button_container_layout.setContentsMargins(0, 10, 0, 0)

        keep_buttons = [
            "Rebuild\nFolders",
            "Default\nSettings",
            "Batch\nProcess",
            "Plot\nLSV",
            "Classify\nFiles"
        ]

        for btn in self.right_buttons:
            btn_text = btn.text().replace('\n', '')
            if test_type == "ORR":
                btn.setVisible(btn.text() in keep_buttons)
            else:
                btn.setVisible(True)

    def create_button_group(self, layout):
        """Create the vertically arranged button group."""
        self.right_buttons = []

        button_config = [
            ("Rebuild\nFolders", self.re_folders, False),
            ("Default\nSettings", self.open_defaults, False),
            ("Load\nFile", self.open_file, True),
            ("Batch\nProcess", self.batch_file, False),
            ("Plot\nLSV", self.batch_LSV, False),
            ("CSV to\nTXT", self.csv_to_txt, True),
            ("Classify\nFiles", self.txt_classify, False),
        ]

        self.button_container = QWidget()
        self.button_container_layout = QVBoxLayout(self.button_container)
        self.button_container_layout.setContentsMargins(0, 0, 0, 0)
        self.button_container_layout.setSpacing(5)

        for text, func, _ in button_config:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            self.right_buttons.append(btn)
            btn.setFixedSize(130, 70)

            size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setSizePolicy(size_policy)

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

        self.button_container_layout.addStretch()

        layout.addWidget(self.button_container)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.test_combo.currentTextChanged.connect(self.adjust_button_layout)

    def adjust_button_layout(self):
        """Adjust the button layout."""
        self.right_buttons[0].parent().layout().activate()
        self.right_buttons[0].parent().updateGeometry()

    def on_comp_method_changed(self, text):
        """Handle compensation method changes."""
        is_manual = text == "Manual"
        self.ohm_input.setEnabled(is_manual)
        self.percentage_input.setEnabled(is_manual)

        if not is_manual:
            self.ohm_input.clear()
            self.percentage_input.setText("100")

    def change_current(self):
        """Handle Convert button clicks."""
        current_test = self.test_combo.currentText()

        if current_test == "ORR":
            return

        """Handle Convert button clicks."""
        try:
            area_value = float(self.area_input.text())
            self.e10_label.setText(f"{area_value * 10} mA:")
            self.e100_label.setText(f"{area_value * 100} mA:")
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid area value!")

    def re_folders(self):
        """Rebuild the working folders."""
        current_dir = os.getcwd()

        folders = ['HER', 'UOR', 'OER','ORR', 'CSV_to_TXT']

        for folder in folders:
            folder_path = os.path.join(current_dir, folder)

            if os.path.exists(folder_path):
                try:
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
                try:
                    os.makedirs(folder_path)
                    print(f"Creating folder: {folder}")
                except Exception as e:
                    print(f"Failed to create folder {folder}: {e}")

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

    def batch_file(self):
        """Batch processing entry point."""
        if self.test_combo.currentText() == "ORR":
            self.batch_process_ORR()
        else:
            self.batch_process_U_O_H()

    def batch_process_ORR(self):
        """ORR-specific batch processing function with vectorized optimization."""
        try:
            area = float(self.area_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid active area!")
            return

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select ORR Raw Data Folder",
            os.getcwd()
        )
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        processed_folder = os.path.join(folder_path, "Processed_ORR")
        os.makedirs(processed_folder, exist_ok=True)

        file_pattern = re.compile(r'^(.*?)_LSV_([24])\.csv$', re.IGNORECASE)
        data_pattern = re.compile(r'^-?\d+\.?\d*([eE][+-]?\d+)?,')

        sample_data = defaultdict(lambda: {'2': None, '4': None})

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

        processed_count = 0
        error_log = []
        for sample, data_dict in sample_data.items():
            try:
                data_2 = data_dict['2'].result()
                data_4 = data_dict['4'].result()

                if not self.validate_data_alignment(data_2, data_4):
                    error_log.append(f"Sample {sample} data alignment failed")
                    continue

                processed_data = self.vectorized_calculation(data_2, data_4, area)

                self.save_processed_ORRdata(processed_data, sample, processed_folder)
                processed_count += 1

            except Exception as e:
                error_log.append(f"Processing sample {sample} failed: {str(e)}")
                continue

        if error_log:
            self.generate_error_report(error_log, processed_folder)

        if processed_count > 0:
            self.load_and_plot_orr_data(processed_folder)

        result_msg = f"Successfully processed {processed_count} samples\nErrors: {len(error_log)}"
        QMessageBox.information(self, "Processing Complete", result_msg)

    def calculate_onset_potential(self,df):
        """Calculate the ORR onset potential."""
        try:
            current_series = df['Disk-Density'].astype(float)
            potential_series = df['Potential_RHE'].astype(float)

            condition = current_series > -0.0001
            first_match_index = condition.idxmax() if condition.any() else None

            if first_match_index is not None:
                return potential_series.loc[first_match_index]
            return None
        except Exception as e:
            print(f"Error calculating onset potential: {str(e)}")
            return None

    def calculate_half_potential(self, df):
        """Calculate the ORR half-wave potential."""
        try:
            abs_min_idx = df['ABS'].idxmin()
            half_potential = df.at[abs_min_idx, 'Potential_RHE']
            return half_potential
        except Exception as e:
            print(f"Error calculating half-wave potential: {str(e)}")
            return None

    def vectorized_calculation(self, data_2, data_4, area):
        """Run the vectorized calculation."""
        base_columns = np.column_stack((
            data_2[:, 0],
            data_2[:, 1],
            data_2[:, 2],
            data_4[:, 1],
            data_4[:, 2]
        ))

        area_factor = 1000 / area

        disk_density = (base_columns[:, 1] - base_columns[:, 3]) * area_factor + 1e-8
        ring_density = (base_columns[:, 2] - base_columns[:, 4]) * area_factor

        disk_density = np.nan_to_num(disk_density, nan=0.0, posinf=0.0, neginf=0.0)
        ring_density = np.nan_to_num(ring_density, nan=0.0, posinf=0.0, neginf=0.0)

        return np.column_stack((base_columns, disk_density, ring_density))

    def process_orr_file(self, filepath, data_pattern):
        """Optimized file processing with parallel support."""
        with open(filepath, 'r', encoding='utf-8') as f:
            skip_rows = 0
            for line in f:
                if data_pattern.match(line):
                    break
                skip_rows += 1
            else:
                return np.empty((0, 3))

        df = pd.read_csv(filepath,
                         skiprows=skip_rows,
                         header=None,
                         usecols=[0, 1, 2],
                         engine='c',
                         dtype=np.float32,
                         memory_map=True)

        sorted_idx = np.argsort(df.values[:, 0])
        return df.values[sorted_idx]

    def validate_data_alignment(self, data_2, data_4):
        """Validate data alignment with vectorized checks."""
        if len(data_2) != len(data_4):
            return False
        return np.allclose(data_2[:, 0], data_4[:, 0], atol=0.001, rtol=0)

    def save_processed_ORRdata(self, data, sample, folder):
        """Save processed ORR data."""
        re_type = self.re_combo.currentText()
        try:
            ph = float(self.ph_input.text())
        except ValueError:
            ph = 0.0
            QMessageBox.warning(self, "Warning", "Invalid pH value, using default")

        potentials = data[:, 0]
        rhe_potentials = potentials + (0.199 if re_type == "Ag/AgCl" else 0.098) + 0.0591 * ph
        full_data = np.hstack((data, rhe_potentials.reshape(-1, 1)))

        POTENTIAL_RHE_COL = 7
        DISK_DENSITY_COL = 5

        P02V = 0.0
        for row in full_data:
            if row[POTENTIAL_RHE_COL] > 0.2:
                P02V = row[DISK_DENSITY_COL]
                break

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
        """Generate an error report."""
        error_path = os.path.join(folder, "Processing_Errors.log")
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(f"[{datetime.now():%Y-%m-%d %H:%M}] {msg}" for msg in error_log))

    def load_and_plot_orr_data(self, folder_path):
        """Load processed ORR data and plot it."""
        self.clear_all()

        csv_files = [f for f in os.listdir(folder_path) if f.startswith("Processed_") and f.endswith(".csv")]

        self.test_combo.setCurrentText("ORR")

        self.ax.clear()

        self.update_plot_settings()

        for filename in csv_files:
            try:
                filepath = os.path.join(folder_path, filename)
                df = pd.read_csv(filepath)

                x_col = [col for col in df.columns if 'Potential_RHE' in col][0]
                y_col = [col for col in df.columns if 'Disk-Density' in col][0]

                x_data = df[x_col].values
                y_data = df[y_col].values

                sample_name = filename.split('_')[1]

                line, = self.ax.plot(
                    x_data,
                    y_data,
                    label=sample_name,
                    linewidth=1,
                    picker=5
                )

                self.add_curve_to_table(
                    sample_name=sample_name,
                    color=line.get_color(),
                    line_ref=line
                )

                onset_potential = self.calculate_onset_potential(df)
                half_potential = self.calculate_half_potential(df)

                self.save_performance_data(folder_path, "ORR", sample_name, onset_potential, half_potential)

                row = self.curve_table.rowCount() - 1
                self.curve_table.item(row, 4).setText(f"{onset_potential:.3f}" if onset_potential else "N/A")
                self.curve_table.item(row, 5).setText(f"{half_potential:.3f}" if half_potential else "N/A")

            except Exception as e:
                    print(f"Failed to load {filename}: {str(e)}")

        self.ax.relim()
        self.ax.autoscale_view()

        self.ax.legend()
        self.canvas.draw_idle()
        self.canvas.flush_events()

        self.ax.axhline(0, color='gray', linestyle='--', linewidth=1, zorder=1)

    def batch_process_U_O_H(self):
        """Batch-process files in a folder for UOR/OER/HER."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        try:
            txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]

            if not txt_files:
                QMessageBox.warning(self, "Warning", "No TXT files found in selected folder")
                return

            processed_count = 0
            failed_files = []

            for filename in txt_files:
                try:
                    full_path = os.path.join(folder_path, filename)
                    self.process_single_file(full_path)
                    processed_count += 1

                    for line in self.ax.lines:
                        if line.get_linestyle() == '--':
                            continue
                except Exception as e:
                    failed_files.append(f"{filename}: {str(e)}")
                    continue

            result_message = f"Successfully processed {processed_count} files"
            if failed_files:
                result_message += f"\n\nFailed files:\n" + "\n".join(failed_files)

            QMessageBox.information(self, "Processing Complete", result_message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error occurred during batch processing: {str(e)}")

    def batch_ORR_LSV(self):
        """Dedicated ORR LSV plotting method."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing Processed ORR CSV Files",
            os.getcwd()
        )
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        try:
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv') and "Processed_" in f]

            self.clear_all()

            self.test_combo.setCurrentText("ORR")
            self.update_plot_settings()

            for filename in csv_files:
                try:
                    filepath = os.path.join(folder_path, filename)
                    df = pd.read_csv(filepath)

                    x_col = [col for col in df.columns if 'Potential_RHE' in col][0]
                    y_col = [col for col in df.columns if 'Disk-Density' in col][0]

                    x_data = df[x_col].values
                    y_data = df[y_col].values

                    sample_name = filename.split('_')[1]

                    line, = self.ax.plot(
                        x_data,
                        y_data,
                        label=sample_name,
                        linewidth=1,
                        picker=5
                    )

                    self.add_curve_to_table(
                        sample_name=sample_name,
                        color=line.get_color(),
                        line_ref=line
                    )

                    row = self.curve_table.rowCount() - 1

                    onset_potential = self.calculate_onset_potential(df)
                    half_potential = self.calculate_half_potential(df)

                    self.curve_table.item(row, 4).setText(f"{onset_potential:.3f}" if onset_potential else "N/A")
                    self.curve_table.item(row, 5).setText(f"{half_potential:.3f}" if half_potential else "N/A")

                except Exception as e:
                    print(f"Failed to process {filename}: {str(e)}")
                    continue

            self.ax.axhline(0, color='gray', linestyle='--', linewidth=1)
            self.ax.legend()
            self.canvas.draw()

            QMessageBox.information(self, "Processing Complete", f"Successfully loaded {len(csv_files)} ORR data files")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"ORR data processing failed: {str(e)}")

    def batch_LSV(self):
        """Batch-process CSV files and plot LSV curves."""
        if self.test_combo.currentText() == "ORR":
            self.batch_ORR_LSV()
            return

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select folder containing CSV files",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )
        self.update_folder_display(folder_path)
        if not folder_path:
            return

        try:
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

            if not csv_files:
                QMessageBox.warning(self, "Warning", "No CSV files found in the selected folder.")
                return

            try:
                area = float(self.area_input.text())
            except ValueError:
                area = 1.0

            for filename in csv_files:
                try:
                    full_path = os.path.join(folder_path, filename)

                    potential_data = []
                    current_data = []

                    with open(full_path, 'r', encoding='utf-8') as file:
                        csv_reader = csv.reader(file)
                        next(csv_reader)
                        for row in csv_reader:
                            try:
                                potential = float(row[0])
                                current = float(row[1])
                                potential_data.append(potential)
                                current_data.append(current)
                            except (ValueError, IndexError):
                                continue

                    if not potential_data or not current_data:
                        continue

                    test_type = self.test_combo.currentText()
                    target_current_10 = 10
                    target_current_100 = 100

                    sorted_data = sorted(zip(potential_data, current_data))
                    potential_data = [p for p, c in sorted_data]
                    current_data = [c for p, c in sorted_data]

                    e10 = self.find_potential_at_current(list(zip(potential_data, current_data)),
                                                         target_current_10, test_type)
                    e100 = self.find_potential_at_current(list(zip(potential_data, current_data)),
                                                          target_current_100, test_type)

                    line, = self.ax.plot(potential_data, current_data,
                                         label=os.path.splitext(filename)[0],
                                         linewidth=1,
                                         picker=5)

                    self.add_curve_to_table(
                        sample_name=os.path.splitext(filename)[0],
                        color=line.get_color(),
                        line_ref=line
                    )

                    row = self.curve_table.rowCount() - 1
                    if e10 != "N/A":
                        if test_type == "UOR":
                            self.curve_table.item(row, 4).setText(f"{float(e10):.3f}")
                        else:
                            eta10 = (float(e10) - 1.23) * 1000 if test_type == "OER" else abs(float(e10)) * 1000
                            self.curve_table.item(row, 4).setText(f"{eta10:.1f}")

                    if e100 != "N/A":
                        if test_type == "UOR":
                            self.curve_table.item(row, 5).setText(f"{float(e100):.3f}")
                        else:
                            eta100 = (float(e100) - 1.23) * 1000 if test_type == "OER" else abs(float(e100)) * 1000
                            self.curve_table.item(row, 5).setText(f"{eta100:.1f}")

                except Exception as e:
                    print(f"Error processing file {filename}: {str(e)}")
                    continue

            for line in self.ax.lines:
                if line.get_linestyle() == '--':
                    continue
                line.set_linewidth(1)
                line.set_alpha(1.0)
                line.set_zorder(2)

            self.ax.set_title('')

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
            folder_name = os.path.basename(os.path.dirname(filename))
            self.file_path_label.setText(folder_name)
            basename = os.path.basename(filename)
            sample_name = os.path.splitext(basename)[0]
            self.name_input.setText(sample_name)

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

            data_rows.sort(key=lambda x: x[0])

            area = float(self.area_input.text())
            target_current_10 = 10 * area
            target_current_100 = 100 * area
            test_type = self.test_combo.currentText()

            e10 = self.find_potential_at_current(data_rows, target_current_10, test_type)
            e100 = self.find_potential_at_current(data_rows, target_current_100, test_type)

            self.e10_input = QLineEdit()
            self.e100_input = QLineEdit()
            self.e10_input.setText(str(e10) if e10 != "N/A" else "N/A")
            self.e100_input.setText(str(e100) if e100 != "N/A" else "N/A")

            e10_rhe = None
            e100_rhe = None
            if e10 != "N/A":
                e10_rhe = self.calculate_rhe_potential(float(e10))
                self.e10_result.setText(f"{e10_rhe:.3f}")
            if e100 != "N/A":
                e100_rhe = self.calculate_rhe_potential(float(e100))
                self.e100_result.setText(f"{e100_rhe:.3f}")

            potential_data = []
            current_data = []
            for potential, current in data_rows:
                potential_rhe = self.calculate_rhe_potential(potential)
                current_density = current / area
                potential_data.append(potential_rhe)
                current_data.append(current_density)

            line, = self.ax.plot(potential_data, current_data,
                                 label=sample_name,
                                 linewidth=1,
                                 picker=5)

            self.add_curve_to_table(
                sample_name=sample_name,
                color=line.get_color(),
                line_ref=line
            )

            if hasattr(self, 'plot_lines'):
                row = self.curve_table.rowCount() - 1
                if e10_rhe is not None:
                    if test_type == "UOR":
                        self.curve_table.item(row, 4).setText(f"{e10_rhe:.3f}")
                    elif test_type == "OER":
                        eta10 = (e10_rhe - 1.23) * 1000
                        self.curve_table.item(row, 4).setText(f"{eta10:.1f}")
                    else:
                        eta10 = abs(e10_rhe) * 1000
                        self.curve_table.item(row, 4).setText(f"{eta10:.1f}")

                if e100_rhe is not None:
                    if test_type == "UOR":
                        self.curve_table.item(row, 5).setText(f"{e100_rhe:.3f}")
                    elif test_type == "OER":
                        eta100 = (e100_rhe - 1.23) * 1000
                        self.curve_table.item(row, 5).setText(f"{eta100:.1f}")
                    else:
                        eta100 = abs(e100_rhe) * 1000
                        self.curve_table.item(row, 5).setText(f"{eta100:.1f}")

            self.save_processed_data(data_rows, filename)
            self.save_performance_data(filename, test_type, sample_name, e10_rhe, e100_rhe)

            if test_type in ["OER", "UOR"]:
                self.ax.set_xlim(1.2, 2.0)
                self.ax.set_ylim(-10, 300)
            elif test_type == "HER":
                self.ax.set_xlim(-0.4, 0)
                self.ax.set_ylim(-300, 10)

            self.ax.set_xlabel('Potential (V vs. RHE)', fontsize=16, fontweight='bold')
            self.ax.set_ylabel('Current density (mA cm$^{-2}$)', fontsize=16, fontweight='bold')
            self.ax.grid(True, linestyle='--', alpha=0.7)
            self.ax.legend()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"File processing error: {str(e)}")

    def find_potential_at_current(self, data, target_current, test_type):
        """Find the potential corresponding to a target current.
        For OER/UOR, find the first value above the target current.
        For HER, find the first value below the target current (negative current).
        """
        if not data:
            return "N/A"

        if test_type == "HER":
            target_current = -abs(target_current)
            sorted_data = sorted(data, key=lambda x: x[1], reverse=True)

            for potential, current in sorted_data:
                if current <= target_current:
                    return f"{potential:.3f}"
        else:
            sorted_data = sorted(data, key=lambda x: x[1])

            for potential, current in sorted_data:
                if current >= target_current:
                    return f"{potential:.3f}"

        return "N/A"

    def calculate_rhe_potential(self, potential):
        """Calculate the RHE potential."""
        try:
            ph = float(self.ph_input.text())
            ref_electrode = self.re_combo.currentText()

            if ref_electrode == "Ag/AgCl":
                return potential + 0.199 + 0.0591 * ph
            else:
                return potential + 0.098 + 0.0591 * ph
        except ValueError:
            raise ValueError("Invalid pH value")

    def save_processed_data(self, data, source_filename, test_type=None):
        """Save processed data to a CSV file."""
        try:
            if test_type is None:
                test_type = self.test_combo.currentText()

            save_folder = os.path.join(os.path.dirname(source_filename),
                                       f"Processed_{test_type}_LSV")
            os.makedirs(save_folder, exist_ok=True)

            basename = os.path.basename(source_filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"Processed_{os.path.splitext(basename)[0]}.csv"
            save_path = os.path.join(save_folder, new_filename)

            processed_data = []

            processed_data.append(['Potential (V vs. RHE)', 'Current density (mA/cm²)'])

            try:
                area = float(self.area_input.text())
            except ValueError:
                area = 1.0

            for potential, current in data:
                current_density = current / area
                potential_rhe = self.calculate_rhe_potential(potential)
                processed_data.append([f"{potential_rhe:.4f}", f"{current_density:.4f}"])

            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(processed_data)

            print(f"Data saved to: {save_path}")
            return save_path

        except Exception as e:
            print(f"Error saving processed data: {str(e)}")
            return None

    def save_performance_data(self, filename, test_type, sample_name, e10, e100):
        """Save performance summary data to TXT and CSV files."""
        try:
            perf_folder = os.path.join(os.path.dirname(filename),
                                       f"{test_type}_Performance_Data_Summary")
            os.makedirs(perf_folder, exist_ok=True)

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if test_type == "UOR":
                header_txt = "Reaction,Reference,IR Compensation,Resistance,Percentage,Area(cm²),pH,Sample,Potential E10,E100"
                header_csv = ["Reaction", "Reference", "IR Compensation", "Resistance(ohm)", "Percentage(%)",
                              "Area(cm²)", "pH", "Sample", "Potential E10(V)", "Potential E100(V)"]
                e10_formatted = f"{e10:.4f}" if isinstance(e10, float) else "N/A"
                e100_formatted = f"{e100:.4f}" if isinstance(e100, float) else "N/A"
            elif test_type == "ORR":
                header_txt = "Reaction,Reference,IR Compensation,Area(cm²),pH,Sample,Onset Potential,Half-wave Potential"
                header_csv = ["Reaction", "Reference", "IR Compensation", "Area(cm²)", "pH", "Sample", "Onset Potential(V)", "Half-wave Potential(V)"]
                e10_formatted = f"{e10:.3f}" if isinstance(e10, float) else "N/A"
                e100_formatted = f"{e100:.3f}" if isinstance(e100, float) else "N/A"

            else:
                header_txt = "Reaction,Reference,IR Compensation,Resistance,Percentage,Area(cm²),pH,Sample,Overpotential n10,n100"
                header_csv = ["Reaction", "Reference", "IR Compensation", "Resistance(ohm)", "Percentage(%)",
                              "Area(cm²)", "pH", "Sample", "Overpotential n10(mV)", "Overpotential n100(mV)"]

                if isinstance(e10, float) and isinstance(e100, float):
                    if test_type == "OER":
                        e10_formatted = f"{(e10 - 1.23) * 1000:.2f}"
                        e100_formatted = f"{(e100 - 1.23) * 1000:.2f}"
                    else:
                        e10_formatted = f"{abs(e10) * 1000:.2f}"
                        e100_formatted = f"{abs(e100) * 1000:.2f}"
                else:
                    e10_formatted = "N/A"
                    e100_formatted = "N/A"

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

            txt_path = os.path.join(perf_folder, f"{test_type}_Data_Statistics.txt")
            if not os.path.exists(txt_path):
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(header_txt + '\n')

            with open(txt_path, 'a', encoding='utf-8') as f:
                line = f"{','.join(str(v) for v in data.values())}\n"
                f.write(line)

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

    def open_defaults(self):
        """Open the default parameter settings file."""
        filename = 'Default parameter settings.txt'
        filepath = os.path.join(os.getcwd(), filename)

        if not os.path.exists(filepath):
            if not self.create_default_config(filepath):
                return

        try:
            os.startfile(filepath) if os.name == 'nt' else os.system(f'open {filepath}')
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open file: {str(e)}")

    def csv_to_txt(self):
        """Convert CSV files to TXT in batch and delete non-LSV files."""
        source_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing CSV Files",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )

        if not source_folder:
            return

        converted_count = 0
        deleted_count = 0

        for filename in os.listdir(source_folder):
            if filename.endswith('.csv'):
                if "LSV" not in filename:
                    os.remove(os.path.join(source_folder, filename))
                    deleted_count += 1
                    continue

                csv_file_path = os.path.join(source_folder, filename)
                txt_file_path = os.path.join(source_folder, filename.replace('.csv', '.txt'))

                try:
                    with open(csv_file_path, mode='r', newline='', encoding='utf-8') as file:
                        reader = csv.reader(file)
                        with open(txt_file_path, mode='w', encoding='utf-8') as output_file:
                            for row in reader:
                                output_file.write(' '.join(row) + '\n')
                    converted_count += 1
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Error converting file {filename}: {str(e)}")

        QMessageBox.information(
            self,
            "Conversion Complete",
            f"Successfully converted {converted_count} CSV files to TXT format.\nDeleted {deleted_count} non-LSV files."
        )

    def txt_classify(self):
        """File classification entry point that routes by test type."""
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing TXT/CSV Files",
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        )

        if not selected_folder:
            QMessageBox.information(self, "Operation Cancelled", "No folder was selected.")
            return

        test_type = self.test_combo.currentText()
        if test_type == "ORR":
            self.txt_classify_ORR(selected_folder)
        else:
            self.txt_classify_U_O_H(selected_folder)

    def txt_classify_ORR(self, folder_path):
        """ORR-specific file classification: keep sample_LSV_2 and _LSV_4 files, delete other CSV files, and record missing pairs."""
        pattern = re.compile(r'^(.*?)_LSV_(\d+)\.csv$', re.IGNORECASE)
        error_folder = os.path.join(folder_path, "Incomplete_Samples")

        try:
            stats = {
                'total': 0,
                'preserved': 0,
                'deleted': 0,
                'moved': 0,
                'missing_samples': set()
            }

            all_csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
            sample_data = defaultdict(set)

            for filename in all_csv_files:
                stats['total'] += 1
                match = pattern.match(filename)
                if not match:
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
                    try:
                        os.remove(os.path.join(folder_path, filename))
                        stats['deleted'] += 1
                    except Exception as e:
                        print(f"Failed to delete file {filename}: {str(e)}")

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

            if stats['missing_samples']:
                os.makedirs(error_folder, exist_ok=True)

                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if any(filename.startswith(sample) for sample in stats['missing_samples']):
                        try:
                            shutil.move(file_path, os.path.join(error_folder, filename))
                            stats['moved'] += 1
                        except Exception as e:
                            print(f"Failed to move file {filename}: {str(e)}")

                error_file = os.path.join(error_folder, "Incomplete_Samples.txt")
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(missing_entries))

                stats['moved'] += 1

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
            if os.path.exists(error_folder) and not os.listdir(error_folder):
                os.rmdir(error_folder)

    def txt_classify_U_O_H(self, selected_folder):
        """Classify UOR/OER/HER files and create folders only when needed."""
        try:
            current_test = self.test_combo.currentText().upper()
            move_counts = defaultdict(int)
            created_folders = set()

            defaults = self.load_defaults()
            oer_tags = {tag.lower() for tag in eval(defaults.get('oer_tags', '["02_LSV","04_LSV","05_LSV","06_LSV"]'))}
            her_tags = {tag.lower() for tag in eval(defaults.get('her_tags', '["08_LSV","09_LSV","10_LSV"]'))}

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

                reaction_match = reaction_pattern.search(filename_lower)
                if reaction_match:
                    reaction = reaction_match.group(1).upper()
                    if reaction not in created_folders:
                        os.makedirs(os.path.join(selected_folder, reaction), exist_ok=True)
                        created_folders.add(reaction)
                    dest_folder = os.path.join(selected_folder, reaction)

                if not dest_folder:
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

                    if 'dest_folder_name' in locals():
                        if dest_folder_name not in created_folders:
                            os.makedirs(os.path.join(selected_folder, dest_folder_name), exist_ok=True)
                            created_folders.add(dest_folder_name)
                        dest_folder = os.path.join(selected_folder, dest_folder_name)

                if dest_folder:
                    try:
                        shutil.move(src_path, os.path.join(dest_folder, filename))
                        folder_name = os.path.basename(dest_folder)
                        move_counts[folder_name] += 1
                    except Exception as e:
                        print(f"Failed to move file {filename}: {str(e)}")

            report_msg = "File classification completed:\n"
            for folder, count in move_counts.items():
                report_msg += f"• {folder}: {count} files\n"

            if created_folders:
                report_msg += "\nCreated folders:\n" + "\n".join([f"• {f}" for f in created_folders])

            QMessageBox.information(self, "Classification Complete", report_msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Classification process error: {str(e)}")

    def load_defaults(self, filepath=None):
        """Load default parameters."""
        if filepath is None:
            filepath = os.path.join(os.getcwd(), 'Default parameter settings.txt')
        defaults = {}

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
                if self.create_default_config(filepath):
                    return self.load_defaults(filepath)
                return {}

        QMessageBox.warning(self, "Error", "Failed to read default config file. Using built-in defaults.")
        return {}

    def create_default_config(self, filepath):
        """Create a configuration file with all default parameters."""
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.black)
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, Qt.black)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())