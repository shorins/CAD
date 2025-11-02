"""
Виджет панели ввода координат для построения линии.
Позволяет вводить координаты вручную для точного построения линий.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDoubleValidator

from .settings import settings
from .core.geometry import Point, Line


class LineInputPanel(QWidget):
    """Панель для ввода координат линии."""
    
    # Сигнал для построения линии (передаем начальную и конечную точки)
    line_requested = Signal(Point, Point)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._update_mode()
        
    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        # Основной горизонтальный layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(15)
        
        # Создаем контейнер для полей ввода (будет обновляться в зависимости от режима)
        self.input_container = QWidget()
        self.input_layout = QHBoxLayout(self.input_container)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        self.input_layout.setSpacing(12)
        
        # Создаем поля ввода (будут добавлены в _create_cartesian_inputs или _create_polar_inputs)
        self.coord_inputs = {}
        
        # Кнопка построить
        self.build_button = QPushButton("Построить")
        self.build_button.setMinimumWidth(120)
        self.build_button.setMinimumHeight(32)
        self.build_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.build_button.setDefault(True)  # Enter активирует эту кнопку
        
        # Добавляем виджеты в основной layout
        main_layout.addWidget(self.input_container)
        main_layout.addStretch()  # Растягиваем пространство между полями и кнопкой
        main_layout.addWidget(self.build_button)
        
        # Устанавливаем стиль для панели
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
                min-width: 90px;
            }
            QLineEdit:focus {
                border: 1px solid #7A86CC;
                background-color: #2D2D2D;
            }
            QLineEdit:hover {
                border: 1px solid #61FFFFFF;
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
        self.build_button.clicked.connect(self._on_build_clicked)
        
        # Слушаем изменения режима координат
        settings.settings_changed.connect(self._on_settings_changed)
    
    def _on_settings_changed(self):
        """Обработчик изменения настроек (режим координат)."""
        self._update_mode()
    
    def _update_mode(self):
        """Обновляет интерфейс в зависимости от режима координат."""
        # Очищаем старые поля ввода
        while self.input_layout.count():
            item = self.input_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.coord_inputs.clear()
        
        # Получаем текущий режим
        mode = settings.get("line_construction_mode") or "cartesian"
        
        if mode == "polar":
            self._create_polar_inputs()
        else:
            self._create_cartesian_inputs()
    
    def _create_cartesian_inputs(self):
        """Создает поля ввода для декартовых координат."""
        # Группа для начальной точки
        start_group = self._create_input_group("Начало:", ["X₁", "Y₁"])
        self.input_layout.addWidget(start_group)
        
        # Разделитель
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setStyleSheet("color: #1EFFFFFF;")
        separator1.setMaximumWidth(1)
        self.input_layout.addWidget(separator1)
        
        # Группа для конечной точки
        end_group = self._create_input_group("Конец:", ["X₂", "Y₂"])
        self.input_layout.addWidget(end_group)
    
    def _create_polar_inputs(self):
        """Создает поля ввода для полярных координат."""
        # Группа для начальной точки (декартовы координаты)
        start_group = self._create_input_group("Начало:", ["X", "Y"])
        self.input_layout.addWidget(start_group)
        
        # Разделитель
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setStyleSheet("color: #1EFFFFFF;")
        separator1.setMaximumWidth(1)
        self.input_layout.addWidget(separator1)
        
        # Группа для полярных координат
        polar_group = self._create_input_group("Полярные:", ["r", "θ"])
        self.input_layout.addWidget(polar_group)
        
        # Настраиваем поля полярных координат после их создания
        # Радиус должен быть положительным (или 0)
        if "r" in self.coord_inputs:
            # Обновляем валидатор для радиуса (только положительные значения)
            validator = QDoubleValidator()
            validator.setRange(0, 1000000)
            validator.setDecimals(2)
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.coord_inputs["r"].setValidator(validator)
            self.coord_inputs["r"].setPlaceholderText("0.00")
            self.coord_inputs["r"].setMinimumWidth(90)
        
        # Определяем единицы измерения углов
        angle_units = settings.get("angle_units") or "degrees"
        if "θ" in self.coord_inputs:
            validator = QDoubleValidator()
            if angle_units == "degrees":
                validator.setRange(-360, 360)
                validator.setDecimals(2)
                self.coord_inputs["θ"].setPlaceholderText("0.00 °")
            else:
                validator.setRange(-6.28, 6.28)
                validator.setDecimals(3)
                self.coord_inputs["θ"].setPlaceholderText("0.000 rad")
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.coord_inputs["θ"].setValidator(validator)
    
    def _create_input_group(self, group_label, field_labels):
        """Создает группу полей ввода с подписью."""
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(6)
        
        # Заголовок группы
        group_title = QLabel(group_label)
        group_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        group_layout.addWidget(group_title)
        
        # Контейнер для полей ввода
        fields_container = QWidget()
        fields_layout = QHBoxLayout(fields_container)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(8)
        
        # Создаем поля ввода
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
        
        # Подпись
        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_widget.setStyleSheet("color: #99FFFFFF; font-size: 12px;")
        container_layout.addWidget(label_widget)
        
        # Поле ввода текста с валидатором для чисел
        line_edit = QLineEdit()
        line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        line_edit.setPlaceholderText("0.00")  # Подсказка при пустом поле
        
        # Устанавливаем валидатор для чисел с плавающей точкой
        validator = QDoubleValidator()
        validator.setRange(-1000000, 1000000)
        validator.setDecimals(2)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        line_edit.setValidator(validator)
        
        container_layout.addWidget(line_edit)
        
        # Сохраняем ссылку на поле ввода
        self.coord_inputs[label] = line_edit
        
        return container
    
    def _parse_float(self, text, label=""):
        """Парсит текст в число с плавающей точкой. Возвращает None если пусто или невалидно."""
        if not text or text.strip() == "":
            return None
        try:
            # Удаляем единицы измерения если есть (для угла)
            cleaned_text = text.replace("°", "").replace(" rad", "").strip()
            value = float(cleaned_text)
            return value
        except (ValueError, AttributeError):
            return None
    
    def _on_build_clicked(self):
        """Обработчик нажатия кнопки 'Построить'."""
        mode = settings.get("line_construction_mode") or "cartesian"
        
        try:
            if mode == "polar":
                # Полярные координаты
                start_x_text = self.coord_inputs["X"].text()
                start_y_text = self.coord_inputs["Y"].text()
                r_text = self.coord_inputs["r"].text()
                theta_text = self.coord_inputs["θ"].text()
                
                # Парсим значения
                start_x = self._parse_float(start_x_text)
                start_y = self._parse_float(start_y_text)
                r = self._parse_float(r_text)
                theta = self._parse_float(theta_text)
                
                # Проверяем, что все поля заполнены
                if (start_x is None or start_y is None or r is None or theta is None):
                    return  # Не все поля заполнены
                
                # Конвертируем угол в радианы, если он в градусах
                angle_units = settings.get("angle_units") or "degrees"
                if angle_units == "degrees":
                    from .core.math_utils import degrees_to_radians
                    theta = degrees_to_radians(theta)
                
                # Вычисляем конечную точку из полярных координат
                from .core.math_utils import polar_to_cartesian
                from PySide6.QtCore import QPointF
                start_point_q = QPointF(start_x, start_y)
                end_point_q = polar_to_cartesian(start_point_q, r, theta)
                
                start_point = Point(start_x, start_y)
                end_point = Point(end_point_q.x(), end_point_q.y())
            else:
                # Декартовы координаты
                start_x_text = self.coord_inputs["X₁"].text()
                start_y_text = self.coord_inputs["Y₁"].text()
                end_x_text = self.coord_inputs["X₂"].text()
                end_y_text = self.coord_inputs["Y₂"].text()
                
                # Парсим значения
                start_x = self._parse_float(start_x_text)
                start_y = self._parse_float(start_y_text)
                end_x = self._parse_float(end_x_text)
                end_y = self._parse_float(end_y_text)
                
                # Проверяем, что все поля заполнены
                if (start_x is None or start_y is None or 
                    end_x is None or end_y is None):
                    return  # Не все поля заполнены
                
                start_point = Point(start_x, start_y)
                end_point = Point(end_x, end_y)
            
            # Проверяем, что точки не совпадают
            if abs(start_point.x - end_point.x) < 0.001 and abs(start_point.y - end_point.y) < 0.001:
                return  # Игнорируем построение нулевой длины
            
            # Отправляем сигнал для построения линии
            self.line_requested.emit(start_point, end_point)
            
            # Не очищаем поля ввода - пользователь может построить еще одну линию с теми же координатами
            
        except (ValueError, KeyError) as e:
            # Игнорируем ошибки валидации
            print(f"Ошибка при построении линии: {e}")
    
    def _clear_inputs(self):
        """Очищает все поля ввода."""
        for line_edit in self.coord_inputs.values():
            line_edit.clear()
    
    def show_panel(self):
        """Показывает панель."""
        self.show()
    
    def hide_panel(self):
        """Скрывает панель."""
        self.hide()

