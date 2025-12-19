"""
Виджет панели ввода для построения эллипса.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator

from .core.geometry import Point, Ellipse


class EllipseInputPanel(QWidget):
    """Панель для ввода параметров эллипса."""
    
    ellipse_requested = Signal(Ellipse)
    
    CONSTRUCTION_METHODS = [
        ("center_radii", "Центр и радиусы"),
        ("center_axes", "Центр и точки на осях"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_method = "center_radii"
        self._setup_ui()
        self._connect_signals()
        self._update_inputs_for_method()
        
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(15)
        
        # Выбор способа
        method_container = QWidget()
        method_layout = QVBoxLayout(method_container)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.setSpacing(4)
        
        method_label = QLabel("Способ:")
        method_label.setStyleSheet("color: #99FFFFFF; font-size: 12px;")
        method_layout.addWidget(method_label)
        
        self.method_combo = QComboBox()
        self.method_combo.setMinimumWidth(180)
        for method_id, method_name in self.CONSTRUCTION_METHODS:
            self.method_combo.addItem(method_name, method_id)
        method_layout.addWidget(self.method_combo)
        
        main_layout.addWidget(method_container)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #1EFFFFFF;")
        separator.setMaximumWidth(1)
        main_layout.addWidget(separator)
        
        self.input_container = QWidget()
        self.input_layout = QHBoxLayout(self.input_container)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        self.input_layout.setSpacing(12)
        main_layout.addWidget(self.input_container)
        
        main_layout.addStretch()
        
        self.build_button = QPushButton("Построить")
        self.build_button.setMinimumWidth(120)
        self.build_button.setMinimumHeight(32)
        self.build_button.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.build_button)
        
        self.coord_inputs = {}
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; border-top: 1px solid #1EFFFFFF; }
            QLabel { color: #99FFFFFF; font-size: 13px; font-weight: 500; }
            QLineEdit {
                background-color: #2D2D2D; border: 1px solid #1EFFFFFF;
                border-radius: 4px; padding: 6px 10px; color: #DDFFFFFF;
                font-size: 13px; min-width: 70px;
            }
            QLineEdit:focus { border: 1px solid #7A86CC; }
            QComboBox {
                background-color: #2D2D2D; border: 1px solid #1EFFFFFF;
                border-radius: 4px; padding: 6px 10px; color: #DDFFFFFF; font-size: 13px;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox::down-arrow {
                border-left: 5px solid transparent; border-right: 5px solid transparent;
                border-top: 5px solid #99FFFFFF; margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2D2D; selection-background-color: #7A86CC; color: #DDFFFFFF;
            }
            QPushButton {
                background-color: #7A86CC; color: white; border: none;
                border-radius: 6px; font-size: 13px; font-weight: 600; padding: 8px 20px;
            }
            QPushButton:hover { background-color: #98A3E0; }
        """)
    
    def _connect_signals(self):
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        self.build_button.clicked.connect(self._on_build_clicked)
    
    def _on_method_changed(self, index):
        self._current_method = self.method_combo.currentData()
        self._update_inputs_for_method()
    
    def _update_inputs_for_method(self):
        while self.input_layout.count():
            item = self.input_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.coord_inputs.clear()
        
        if self._current_method == "center_radii":
            self._create_center_radii_inputs()
        elif self._current_method == "center_axes":
            self._create_center_axes_inputs()
    
    def _create_center_radii_inputs(self):
        """Центр и радиусы: Xc, Yc, Rx, Ry"""
        c_group = self._create_input_group("Центр:", ["Xc", "Yc"])
        self.input_layout.addWidget(c_group)
        self._add_separator()
        r_group = self._create_input_group("Радиусы:", ["Rx", "Ry"])
        self.input_layout.addWidget(r_group)
    
    def _create_center_axes_inputs(self):
        """Центр и точки на осях (для интерактивного построения)"""
        c_group = self._create_input_group("Центр:", ["Xc", "Yc"])
        self.input_layout.addWidget(c_group)
        self._add_separator()
        r_group = self._create_input_group("Радиусы:", ["Rx", "Ry"])
        self.input_layout.addWidget(r_group)
    
    def _add_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #1EFFFFFF;")
        separator.setMaximumWidth(1)
        self.input_layout.addWidget(separator)
    
    def _create_input_group(self, group_label, field_labels):
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(6)
        
        group_title = QLabel(group_label)
        group_layout.addWidget(group_title)
        
        fields_container = QWidget()
        fields_layout = QHBoxLayout(fields_container)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(8)
        
        for label in field_labels:
            field_widget = self._create_coord_input(label)
            fields_layout.addWidget(field_widget)
        
        group_layout.addWidget(fields_container)
        return group_widget
    
    def _create_coord_input(self, label):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)
        
        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_widget.setStyleSheet("color: #99FFFFFF; font-size: 12px;")
        container_layout.addWidget(label_widget)
        
        line_edit = QLineEdit()
        line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        line_edit.setPlaceholderText("0.00")
        
        validator = QDoubleValidator()
        validator.setRange(-1000000, 1000000)
        validator.setDecimals(2)
        line_edit.setValidator(validator)
        
        container_layout.addWidget(line_edit)
        self.coord_inputs[label] = line_edit
        return container
    
    def _parse_float(self, text):
        if not text or text.strip() == "":
            return None
        try:
            return float(text.strip())
        except ValueError:
            return None
    
    def _on_build_clicked(self):
        try:
            xc = self._parse_float(self.coord_inputs["Xc"].text())
            yc = self._parse_float(self.coord_inputs["Yc"].text())
            rx = self._parse_float(self.coord_inputs["Rx"].text())
            ry = self._parse_float(self.coord_inputs["Ry"].text())
            
            if any(v is None for v in [xc, yc, rx, ry]) or rx <= 0 or ry <= 0:
                return
            
            ellipse = Ellipse(Point(xc, yc), rx, ry)
            self.ellipse_requested.emit(ellipse)
            self._clear_inputs()
                
        except Exception as e:
            print(f"Ошибка при построении эллипса: {e}")
    
    def _clear_inputs(self):
        for line_edit in self.coord_inputs.values():
            line_edit.clear()
    
    def get_current_method(self):
        return self._current_method
