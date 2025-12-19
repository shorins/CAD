"""
Виджет панели ввода для построения многоугольника.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame, QSpinBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator

from .core.geometry import Point, Polygon


class PolygonInputPanel(QWidget):
    """Панель для ввода параметров многоугольника."""
    
    polygon_requested = Signal(Polygon)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        self.coord_inputs = {}  # Инициализируем ДО создания групп ввода
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(15)
        
        # Количество сторон
        sides_container = QWidget()
        sides_layout = QVBoxLayout(sides_container)
        sides_layout.setContentsMargins(0, 0, 0, 0)
        sides_layout.setSpacing(6)
        
        sides_label = QLabel("Сторон:")
        sides_label.setStyleSheet("color: #99FFFFFF; font-size: 12px;")
        sides_layout.addWidget(sides_label)
        
        self.sides_spinbox = QSpinBox()
        self.sides_spinbox.setRange(3, 100)
        self.sides_spinbox.setValue(6)
        self.sides_spinbox.setMinimumWidth(70)
        sides_layout.addWidget(self.sides_spinbox)
        
        main_layout.addWidget(sides_container)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #1EFFFFFF;")
        separator.setMaximumWidth(1)
        main_layout.addWidget(separator)
        
        # Центр
        center_group = self._create_input_group("Центр:", ["Xc", "Yc"])
        main_layout.addWidget(center_group)
        
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setStyleSheet("color: #1EFFFFFF;")
        separator2.setMaximumWidth(1)
        main_layout.addWidget(separator2)
        
        # Радиус
        radius_group = self._create_input_group("Радиус:", ["R"])
        main_layout.addWidget(radius_group)
        
        main_layout.addStretch()
        
        self.build_button = QPushButton("Построить")
        self.build_button.setMinimumWidth(120)
        self.build_button.setMinimumHeight(32)
        self.build_button.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.build_button)
        
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; border-top: 1px solid #1EFFFFFF; }
            QLabel { color: #99FFFFFF; font-size: 13px; font-weight: 500; }
            QLineEdit, QSpinBox {
                background-color: #2D2D2D; border: 1px solid #1EFFFFFF;
                border-radius: 4px; padding: 6px 10px; color: #DDFFFFFF;
                font-size: 13px; min-width: 70px;
            }
            QLineEdit:focus, QSpinBox:focus { border: 1px solid #7A86CC; }
            QPushButton {
                background-color: #7A86CC; color: white; border: none;
                border-radius: 6px; font-size: 13px; font-weight: 600; padding: 8px 20px;
            }
            QPushButton:hover { background-color: #98A3E0; }
        """)
    
    def _connect_signals(self):
        self.build_button.clicked.connect(self._on_build_clicked)
    
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
            r = self._parse_float(self.coord_inputs["R"].text())
            num_sides = self.sides_spinbox.value()
            
            if any(v is None for v in [xc, yc, r]) or r <= 0:
                return
            
            polygon = Polygon(Point(xc, yc), r, num_sides=num_sides)
            self.polygon_requested.emit(polygon)
            self._clear_inputs()
                
        except Exception as e:
            print(f"Ошибка при построении многоугольника: {e}")
    
    def _clear_inputs(self):
        for line_edit in self.coord_inputs.values():
            line_edit.clear()
    
    def get_num_sides(self):
        """Возвращает количество сторон."""
        return self.sides_spinbox.value()
