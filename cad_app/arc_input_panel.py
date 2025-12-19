"""
Виджет панели ввода для построения дуги.
Позволяет выбирать способ построения и вводить координаты.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator

from .core.geometry import Point, Arc


class ArcInputPanel(QWidget):
    """Панель для ввода параметров дуги."""
    
    # Сигнал для построения дуги
    arc_requested = Signal(Arc)
    
    # Способы построения
    CONSTRUCTION_METHODS = [
        ("three_points", "Три точки (начало, точка на дуге, конец)"),
        ("center_angles", "Центр, радиус, углы"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_method = "three_points"
        self._setup_ui()
        self._connect_signals()
        self._update_inputs_for_method()
        
    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(15)
        
        # Выбор способа построения
        method_container = QWidget()
        method_layout = QVBoxLayout(method_container)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.setSpacing(4)
        
        method_label = QLabel("Способ:")
        method_label.setStyleSheet("color: #99FFFFFF; font-size: 12px;")
        method_layout.addWidget(method_label)
        
        self.method_combo = QComboBox()
        self.method_combo.setMinimumWidth(250)
        for method_id, method_name in self.CONSTRUCTION_METHODS:
            self.method_combo.addItem(method_name, method_id)
        method_layout.addWidget(self.method_combo)
        
        main_layout.addWidget(method_container)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #1EFFFFFF;")
        separator.setMaximumWidth(1)
        main_layout.addWidget(separator)
        
        # Контейнер для полей ввода
        self.input_container = QWidget()
        self.input_layout = QHBoxLayout(self.input_container)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        self.input_layout.setSpacing(12)
        main_layout.addWidget(self.input_container)
        
        # Кнопка построить
        main_layout.addStretch()
        
        self.build_button = QPushButton("Построить")
        self.build_button.setMinimumWidth(120)
        self.build_button.setMinimumHeight(32)
        self.build_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.build_button.setDefault(True)
        main_layout.addWidget(self.build_button)
        
        # Хранилище полей ввода
        self.coord_inputs = {}
        
        # Устанавливаем стиль
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                border-top: 1px solid #1EFFFFFF;
            }
            QLabel {
                color: #99FFFFFF;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #1EFFFFFF;
                border-radius: 4px;
                padding: 6px 10px;
                color: #DDFFFFFF;
                font-size: 13px;
                min-width: 70px;
            }
            QLineEdit:focus {
                border: 1px solid #7A86CC;
            }
            QLineEdit:hover {
                border: 1px solid #61FFFFFF;
            }
            QComboBox {
                background-color: #2D2D2D;
                border: 1px solid #1EFFFFFF;
                border-radius: 4px;
                padding: 6px 10px;
                color: #DDFFFFFF;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #61FFFFFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #99FFFFFF;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2D2D;
                border: 1px solid #1EFFFFFF;
                selection-background-color: #7A86CC;
                color: #DDFFFFFF;
            }
            QPushButton {
                background-color: #7A86CC;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #98A3E0;
            }
            QPushButton:pressed {
                background-color: #6A76BC;
            }
        """)
    
    def _connect_signals(self):
        """Подключение сигналов."""
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        self.build_button.clicked.connect(self._on_build_clicked)
    
    def _on_method_changed(self, index):
        """Обработчик изменения способа построения."""
        self._current_method = self.method_combo.currentData()
        self._update_inputs_for_method()
    
    def _update_inputs_for_method(self):
        """Обновляет поля ввода для текущего способа."""
        # Очищаем старые поля
        while self.input_layout.count():
            item = self.input_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.coord_inputs.clear()
        
        if self._current_method == "three_points":
            self._create_three_points_inputs()
        elif self._current_method == "center_angles":
            self._create_center_angles_inputs()
    
    def _create_three_points_inputs(self):
        """Три точки: начало, точка на дуге, конец."""
        p1_group = self._create_input_group("Начало:", ["X₁", "Y₁"])
        self.input_layout.addWidget(p1_group)
        self._add_separator()
        p2_group = self._create_input_group("На дуге:", ["X₂", "Y₂"])
        self.input_layout.addWidget(p2_group)
        self._add_separator()
        p3_group = self._create_input_group("Конец:", ["X₃", "Y₃"])
        self.input_layout.addWidget(p3_group)
    
    def _create_center_angles_inputs(self):
        """Центр, радиус, начальный угол, конечный угол."""
        center_group = self._create_input_group("Центр:", ["Xc", "Yc"])
        self.input_layout.addWidget(center_group)
        self._add_separator()
        radius_group = self._create_input_group("Радиус:", ["R"])
        self.input_layout.addWidget(radius_group)
        self._add_separator()
        angles_group = self._create_input_group("Углы (°):", ["Начало", "Конец"])
        self.input_layout.addWidget(angles_group)
    
    def _add_separator(self):
        """Добавляет вертикальный разделитель."""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #1EFFFFFF;")
        separator.setMaximumWidth(1)
        self.input_layout.addWidget(separator)
    
    def _create_input_group(self, group_label, field_labels):
        """Создает группу полей ввода с подписью."""
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(6)
        
        group_title = QLabel(group_label)
        group_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
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
        """Создает поле ввода для координаты."""
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
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        line_edit.setValidator(validator)
        
        container_layout.addWidget(line_edit)
        self.coord_inputs[label] = line_edit
        
        return container
    
    def _parse_float(self, text):
        """Парсит текст в число."""
        if not text or text.strip() == "":
            return None
        try:
            return float(text.strip())
        except ValueError:
            return None
    
    def _on_build_clicked(self):
        """Обработчик построения дуги."""
        try:
            arc = None
            
            if self._current_method == "three_points":
                x1 = self._parse_float(self.coord_inputs["X₁"].text())
                y1 = self._parse_float(self.coord_inputs["Y₁"].text())
                x2 = self._parse_float(self.coord_inputs["X₂"].text())
                y2 = self._parse_float(self.coord_inputs["Y₂"].text())
                x3 = self._parse_float(self.coord_inputs["X₃"].text())
                y3 = self._parse_float(self.coord_inputs["Y₃"].text())
                
                if any(v is None for v in [x1, y1, x2, y2, x3, y3]):
                    return
                
                p1 = Point(x1, y1)
                p2 = Point(x2, y2)
                p3 = Point(x3, y3)
                arc = Arc.from_three_points(p1, p2, p3)
            
            elif self._current_method == "center_angles":
                xc = self._parse_float(self.coord_inputs["Xc"].text())
                yc = self._parse_float(self.coord_inputs["Yc"].text())
                r = self._parse_float(self.coord_inputs["R"].text())
                start_angle = self._parse_float(self.coord_inputs["Начало"].text())
                end_angle = self._parse_float(self.coord_inputs["Конец"].text())
                
                if any(v is None for v in [xc, yc, r, start_angle, end_angle]):
                    return
                
                if r <= 0:
                    return
                
                arc = Arc.from_center_and_angles(
                    Point(xc, yc), r, start_angle, end_angle
                )
            
            if arc:
                self.arc_requested.emit(arc)
                self._clear_inputs()
                
        except Exception as e:
            print(f"Ошибка при построении дуги: {e}")
    
    def _clear_inputs(self):
        """Очищает все поля ввода."""
        for line_edit in self.coord_inputs.values():
            line_edit.clear()
    
    def get_current_method(self):
        """Возвращает текущий способ построения."""
        return self._current_method
    
    def get_required_clicks(self):
        """Возвращает количество кликов для текущего метода."""
        if self._current_method == "three_points":
            return 3
        elif self._current_method == "center_angles":
            return 2  # Центр + точка для радиуса и начального угла
        return 3
