"""
Панель редактирования выделенных объектов.
Динамически показывает элементы управления в зависимости от типа объекта.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, 
    QSpinBox, QComboBox, QPushButton, QGroupBox, QScrollArea,
    QFormLayout, QFrame
)
from PySide6.QtCore import Signal, Qt

from .core.geometry import (
    Line, Circle, Arc, Rectangle, Ellipse, Polygon, Spline,
    Point, GeometricPrimitive
)
from .core.geometry.polygon import PolygonType


class EditPanel(QWidget):
    """
    Панель редактирования свойств выделенных объектов.
    Появляется динамически при выделении объекта.
    """
    
    # Сигнал: объект был изменён (для перерисовки canvas)
    object_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_object = None
        self._blocking_signals = False
        self._init_ui()
        
    def _init_ui(self):
        """Инициализация UI."""
        self.setMinimumWidth(250)
        self.setMaximumWidth(300)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Заголовок
        self.title_label = QLabel("Свойства объекта")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(self.title_label)
        
        # Область прокрутки для контента
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        
        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area)
        
        # Изначально скрываем панель
        self.hide()
    
    def update_for_selection(self, selected_objects: list):
        """
        Обновляет панель для текущего выделения.
        
        Args:
            selected_objects: Список выделенных объектов
        """
        # Очищаем текущий контент
        self._clear_content()
        
        if not selected_objects:
            self.current_object = None
            self.hide()
            return
        
        # Пока поддерживаем редактирование только одного объекта
        if len(selected_objects) > 1:
            self.title_label.setText(f"Выделено объектов: {len(selected_objects)}")
            self._show_multi_selection_info(selected_objects)
            self.show()
            return
        
        obj = selected_objects[0]
        self.current_object = obj
        
        # Создаём редактор в зависимости от типа
        if isinstance(obj, Line):
            self._create_line_editor(obj)
        elif isinstance(obj, Circle):
            self._create_circle_editor(obj)
        elif isinstance(obj, Arc):
            self._create_arc_editor(obj)
        elif isinstance(obj, Rectangle):
            self._create_rectangle_editor(obj)
        elif isinstance(obj, Ellipse):
            self._create_ellipse_editor(obj)
        elif isinstance(obj, Polygon):
            self._create_polygon_editor(obj)
        elif isinstance(obj, Spline):
            self._create_spline_editor(obj)
        else:
            self.title_label.setText("Неизвестный тип объекта")
            self.hide()
            return
        
        self.show()
    
    def _clear_content(self):
        """Очищает содержимое панели."""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _show_multi_selection_info(self, objects: list):
        """Показывает информацию о мультивыделении."""
        info_label = QLabel("Выберите один объект для редактирования свойств")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        self.content_layout.addWidget(info_label)
        self.content_layout.addStretch()
    
    def _create_coordinate_input(self, label: str, x: float, y: float, 
                                  on_change_x, on_change_y) -> QGroupBox:
        """Создаёт группу ввода координат."""
        group = QGroupBox(label)
        layout = QFormLayout(group)
        
        spin_x = QDoubleSpinBox()
        spin_x.setRange(-99999, 99999)
        spin_x.setDecimals(2)
        spin_x.setValue(x)
        spin_x.valueChanged.connect(on_change_x)
        
        spin_y = QDoubleSpinBox()
        spin_y.setRange(-99999, 99999)
        spin_y.setDecimals(2)
        spin_y.setValue(y)
        spin_y.valueChanged.connect(on_change_y)
        
        layout.addRow("X:", spin_x)
        layout.addRow("Y:", spin_y)
        
        return group
    
    def _create_value_input(self, label: str, value: float, 
                            on_change, min_val=0.01, max_val=99999,
                            decimals=2) -> QWidget:
        """Создаёт поле ввода значения."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(label)
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setValue(value)
        spin.valueChanged.connect(on_change)
        
        layout.addWidget(lbl)
        layout.addWidget(spin)
        
        return widget
    
    def _emit_change(self):
        """Уведомляет об изменении объекта."""
        if not self._blocking_signals:
            self.object_changed.emit()
    
    # ==================== Редакторы для каждого типа ====================
    
    def _create_line_editor(self, line: Line):
        """Редактор для линии."""
        self.title_label.setText("Линия")
        
        # Начальная точка
        start_group = QGroupBox("Начальная точка")
        start_layout = QFormLayout(start_group)
        
        self.line_start_x = QDoubleSpinBox()
        self.line_start_x.setRange(-99999, 99999)
        self.line_start_x.setDecimals(2)
        self.line_start_x.setValue(line.start.x)
        self.line_start_x.valueChanged.connect(self._on_line_start_x_changed)
        
        self.line_start_y = QDoubleSpinBox()
        self.line_start_y.setRange(-99999, 99999)
        self.line_start_y.setDecimals(2)
        self.line_start_y.setValue(line.start.y)
        self.line_start_y.valueChanged.connect(self._on_line_start_y_changed)
        
        start_layout.addRow("X:", self.line_start_x)
        start_layout.addRow("Y:", self.line_start_y)
        self.content_layout.addWidget(start_group)
        
        # Конечная точка
        end_group = QGroupBox("Конечная точка")
        end_layout = QFormLayout(end_group)
        
        self.line_end_x = QDoubleSpinBox()
        self.line_end_x.setRange(-99999, 99999)
        self.line_end_x.setDecimals(2)
        self.line_end_x.setValue(line.end.x)
        self.line_end_x.valueChanged.connect(self._on_line_end_x_changed)
        
        self.line_end_y = QDoubleSpinBox()
        self.line_end_y.setRange(-99999, 99999)
        self.line_end_y.setDecimals(2)
        self.line_end_y.setValue(line.end.y)
        self.line_end_y.valueChanged.connect(self._on_line_end_y_changed)
        
        end_layout.addRow("X:", self.line_end_x)
        end_layout.addRow("Y:", self.line_end_y)
        self.content_layout.addWidget(end_group)
        
        # Информация
        info_label = QLabel(f"Длина: {line.length:.2f}")
        self.content_layout.addWidget(info_label)
        
        self.content_layout.addStretch()
    
    def _on_line_start_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Line):
            self.current_object.start = Point(value, self.current_object.start.y)
            self._emit_change()
    
    def _on_line_start_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Line):
            self.current_object.start = Point(self.current_object.start.x, value)
            self._emit_change()
    
    def _on_line_end_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Line):
            self.current_object.end = Point(value, self.current_object.end.y)
            self._emit_change()
    
    def _on_line_end_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Line):
            self.current_object.end = Point(self.current_object.end.x, value)
            self._emit_change()
    
    def _create_circle_editor(self, circle: Circle):
        """Редактор для окружности."""
        self.title_label.setText("Окружность")
        
        # Центр
        center_group = QGroupBox("Центр")
        center_layout = QFormLayout(center_group)
        
        self.circle_cx = QDoubleSpinBox()
        self.circle_cx.setRange(-99999, 99999)
        self.circle_cx.setDecimals(2)
        self.circle_cx.setValue(circle.center.x)
        self.circle_cx.valueChanged.connect(self._on_circle_center_x_changed)
        
        self.circle_cy = QDoubleSpinBox()
        self.circle_cy.setRange(-99999, 99999)
        self.circle_cy.setDecimals(2)
        self.circle_cy.setValue(circle.center.y)
        self.circle_cy.valueChanged.connect(self._on_circle_center_y_changed)
        
        center_layout.addRow("X:", self.circle_cx)
        center_layout.addRow("Y:", self.circle_cy)
        self.content_layout.addWidget(center_group)
        
        # Радиус
        radius_group = QGroupBox("Размеры")
        radius_layout = QFormLayout(radius_group)
        
        self.circle_radius = QDoubleSpinBox()
        self.circle_radius.setRange(0.01, 99999)
        self.circle_radius.setDecimals(2)
        self.circle_radius.setValue(circle.radius)
        self.circle_radius.valueChanged.connect(self._on_circle_radius_changed)
        
        radius_layout.addRow("Радиус:", self.circle_radius)
        self.content_layout.addWidget(radius_group)
        
        self.content_layout.addStretch()
    
    def _on_circle_center_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Circle):
            self.current_object.center = Point(value, self.current_object.center.y)
            self._emit_change()
    
    def _on_circle_center_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Circle):
            self.current_object.center = Point(self.current_object.center.x, value)
            self._emit_change()
    
    def _on_circle_radius_changed(self, value):
        if self.current_object and isinstance(self.current_object, Circle):
            self.current_object.radius = value
            self._emit_change()
    
    def _create_arc_editor(self, arc: Arc):
        """Редактор для дуги."""
        self.title_label.setText("Дуга")
        
        # Центр
        center_group = QGroupBox("Центр")
        center_layout = QFormLayout(center_group)
        
        self.arc_cx = QDoubleSpinBox()
        self.arc_cx.setRange(-99999, 99999)
        self.arc_cx.setDecimals(2)
        self.arc_cx.setValue(arc.center.x)
        self.arc_cx.valueChanged.connect(self._on_arc_center_x_changed)
        
        self.arc_cy = QDoubleSpinBox()
        self.arc_cy.setRange(-99999, 99999)
        self.arc_cy.setDecimals(2)
        self.arc_cy.setValue(arc.center.y)
        self.arc_cy.valueChanged.connect(self._on_arc_center_y_changed)
        
        center_layout.addRow("X:", self.arc_cx)
        center_layout.addRow("Y:", self.arc_cy)
        self.content_layout.addWidget(center_group)
        
        # Радиус и углы
        params_group = QGroupBox("Параметры")
        params_layout = QFormLayout(params_group)
        
        self.arc_radius = QDoubleSpinBox()
        self.arc_radius.setRange(0.01, 99999)
        self.arc_radius.setDecimals(2)
        self.arc_radius.setValue(arc.radius)
        self.arc_radius.valueChanged.connect(self._on_arc_radius_changed)
        
        self.arc_start_angle = QDoubleSpinBox()
        self.arc_start_angle.setRange(-360, 360)
        self.arc_start_angle.setDecimals(1)
        self.arc_start_angle.setSuffix("°")
        self.arc_start_angle.setValue(arc.start_angle)
        self.arc_start_angle.valueChanged.connect(self._on_arc_start_angle_changed)
        
        self.arc_span_angle = QDoubleSpinBox()
        self.arc_span_angle.setRange(-360, 360)
        self.arc_span_angle.setDecimals(1)
        self.arc_span_angle.setSuffix("°")
        self.arc_span_angle.setValue(arc.span_angle)
        self.arc_span_angle.valueChanged.connect(self._on_arc_span_angle_changed)
        
        params_layout.addRow("Радиус:", self.arc_radius)
        params_layout.addRow("Начальный угол:", self.arc_start_angle)
        params_layout.addRow("Угол развёртки:", self.arc_span_angle)
        self.content_layout.addWidget(params_group)
        
        self.content_layout.addStretch()
    
    def _on_arc_center_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Arc):
            self.current_object.center = Point(value, self.current_object.center.y)
            self._emit_change()
    
    def _on_arc_center_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Arc):
            self.current_object.center = Point(self.current_object.center.x, value)
            self._emit_change()
    
    def _on_arc_radius_changed(self, value):
        if self.current_object and isinstance(self.current_object, Arc):
            self.current_object.radius = value
            self._emit_change()
    
    def _on_arc_start_angle_changed(self, value):
        if self.current_object and isinstance(self.current_object, Arc):
            self.current_object.start_angle = value
            self._emit_change()
    
    def _on_arc_span_angle_changed(self, value):
        if self.current_object and isinstance(self.current_object, Arc):
            self.current_object.span_angle = value
            self._emit_change()
    
    def _create_rectangle_editor(self, rect: Rectangle):
        """Редактор для прямоугольника."""
        self.title_label.setText("Прямоугольник")
        
        # Первая точка (левый нижний угол)
        p1_group = QGroupBox("Точка 1")
        p1_layout = QFormLayout(p1_group)
        
        self.rect_p1_x = QDoubleSpinBox()
        self.rect_p1_x.setRange(-99999, 99999)
        self.rect_p1_x.setDecimals(2)
        self.rect_p1_x.setValue(rect.p1.x)
        self.rect_p1_x.valueChanged.connect(self._on_rect_p1_x_changed)
        
        self.rect_p1_y = QDoubleSpinBox()
        self.rect_p1_y.setRange(-99999, 99999)
        self.rect_p1_y.setDecimals(2)
        self.rect_p1_y.setValue(rect.p1.y)
        self.rect_p1_y.valueChanged.connect(self._on_rect_p1_y_changed)
        
        p1_layout.addRow("X:", self.rect_p1_x)
        p1_layout.addRow("Y:", self.rect_p1_y)
        self.content_layout.addWidget(p1_group)
        
        # Вторая точка
        p2_group = QGroupBox("Точка 2")
        p2_layout = QFormLayout(p2_group)
        
        self.rect_p2_x = QDoubleSpinBox()
        self.rect_p2_x.setRange(-99999, 99999)
        self.rect_p2_x.setDecimals(2)
        self.rect_p2_x.setValue(rect.p2.x)
        self.rect_p2_x.valueChanged.connect(self._on_rect_p2_x_changed)
        
        self.rect_p2_y = QDoubleSpinBox()
        self.rect_p2_y.setRange(-99999, 99999)
        self.rect_p2_y.setDecimals(2)
        self.rect_p2_y.setValue(rect.p2.y)
        self.rect_p2_y.valueChanged.connect(self._on_rect_p2_y_changed)
        
        p2_layout.addRow("X:", self.rect_p2_x)
        p2_layout.addRow("Y:", self.rect_p2_y)
        self.content_layout.addWidget(p2_group)
        
        # Углы (скругление/фаска)
        corners_group = QGroupBox("Углы")
        corners_layout = QFormLayout(corners_group)
        
        self.rect_corner_radius = QDoubleSpinBox()
        self.rect_corner_radius.setRange(0, 99999)
        self.rect_corner_radius.setDecimals(2)
        self.rect_corner_radius.setValue(rect.corner_radius)
        self.rect_corner_radius.valueChanged.connect(self._on_rect_corner_radius_changed)
        
        self.rect_chamfer_size = QDoubleSpinBox()
        self.rect_chamfer_size.setRange(0, 99999)
        self.rect_chamfer_size.setDecimals(2)
        self.rect_chamfer_size.setValue(rect.chamfer_size)
        self.rect_chamfer_size.valueChanged.connect(self._on_rect_chamfer_size_changed)
        
        corners_layout.addRow("Скругление:", self.rect_corner_radius)
        corners_layout.addRow("Фаска:", self.rect_chamfer_size)
        self.content_layout.addWidget(corners_group)
        
        # Информация
        info_label = QLabel(f"Размер: {rect.width:.2f} × {rect.height:.2f}")
        self.content_layout.addWidget(info_label)
        
        self.content_layout.addStretch()
    
    def _on_rect_p1_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Rectangle):
            self.current_object.p1 = Point(value, self.current_object.p1.y)
            self._emit_change()
    
    def _on_rect_p1_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Rectangle):
            self.current_object.p1 = Point(self.current_object.p1.x, value)
            self._emit_change()
    
    def _on_rect_p2_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Rectangle):
            self.current_object.p2 = Point(value, self.current_object.p2.y)
            self._emit_change()
    
    def _on_rect_p2_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Rectangle):
            self.current_object.p2 = Point(self.current_object.p2.x, value)
            self._emit_change()
    
    def _on_rect_corner_radius_changed(self, value):
        if self.current_object and isinstance(self.current_object, Rectangle):
            self.current_object.corner_radius = value
            # При изменении radius сбрасываем chamfer
            if value > 0:
                self.current_object.chamfer_size = 0
                self._blocking_signals = True
                self.rect_chamfer_size.setValue(0)
                self._blocking_signals = False
            self._emit_change()
    
    def _on_rect_chamfer_size_changed(self, value):
        if self.current_object and isinstance(self.current_object, Rectangle):
            self.current_object.chamfer_size = value
            # При изменении chamfer сбрасываем radius
            if value > 0:
                self.current_object.corner_radius = 0
                self._blocking_signals = True
                self.rect_corner_radius.setValue(0)
                self._blocking_signals = False
            self._emit_change()
    
    def _create_ellipse_editor(self, ellipse: Ellipse):
        """Редактор для эллипса."""
        self.title_label.setText("Эллипс")
        
        # Центр
        center_group = QGroupBox("Центр")
        center_layout = QFormLayout(center_group)
        
        self.ellipse_cx = QDoubleSpinBox()
        self.ellipse_cx.setRange(-99999, 99999)
        self.ellipse_cx.setDecimals(2)
        self.ellipse_cx.setValue(ellipse.center.x)
        self.ellipse_cx.valueChanged.connect(self._on_ellipse_center_x_changed)
        
        self.ellipse_cy = QDoubleSpinBox()
        self.ellipse_cy.setRange(-99999, 99999)
        self.ellipse_cy.setDecimals(2)
        self.ellipse_cy.setValue(ellipse.center.y)
        self.ellipse_cy.valueChanged.connect(self._on_ellipse_center_y_changed)
        
        center_layout.addRow("X:", self.ellipse_cx)
        center_layout.addRow("Y:", self.ellipse_cy)
        self.content_layout.addWidget(center_group)
        
        # Оси
        axes_group = QGroupBox("Полуоси")
        axes_layout = QFormLayout(axes_group)
        
        self.ellipse_rx = QDoubleSpinBox()
        self.ellipse_rx.setRange(0.01, 99999)
        self.ellipse_rx.setDecimals(2)
        self.ellipse_rx.setValue(ellipse.radius_x)
        self.ellipse_rx.valueChanged.connect(self._on_ellipse_rx_changed)
        
        self.ellipse_ry = QDoubleSpinBox()
        self.ellipse_ry.setRange(0.01, 99999)
        self.ellipse_ry.setDecimals(2)
        self.ellipse_ry.setValue(ellipse.radius_y)
        self.ellipse_ry.valueChanged.connect(self._on_ellipse_ry_changed)
        
        axes_layout.addRow("Радиус X:", self.ellipse_rx)
        axes_layout.addRow("Радиус Y:", self.ellipse_ry)
        self.content_layout.addWidget(axes_group)
        
        self.content_layout.addStretch()
    
    def _on_ellipse_center_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Ellipse):
            self.current_object.center = Point(value, self.current_object.center.y)
            self._emit_change()
    
    def _on_ellipse_center_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Ellipse):
            self.current_object.center = Point(self.current_object.center.x, value)
            self._emit_change()
    
    def _on_ellipse_rx_changed(self, value):
        if self.current_object and isinstance(self.current_object, Ellipse):
            self.current_object.radius_x = value
            self._emit_change()
    
    def _on_ellipse_ry_changed(self, value):
        if self.current_object and isinstance(self.current_object, Ellipse):
            self.current_object.radius_y = value
            self._emit_change()
    
    def _create_polygon_editor(self, polygon: Polygon):
        """Редактор для многоугольника."""
        self.title_label.setText("Многоугольник")
        
        # Центр
        center_group = QGroupBox("Центр")
        center_layout = QFormLayout(center_group)
        
        self.polygon_cx = QDoubleSpinBox()
        self.polygon_cx.setRange(-99999, 99999)
        self.polygon_cx.setDecimals(2)
        self.polygon_cx.setValue(polygon.center.x)
        self.polygon_cx.valueChanged.connect(self._on_polygon_center_x_changed)
        
        self.polygon_cy = QDoubleSpinBox()
        self.polygon_cy.setRange(-99999, 99999)
        self.polygon_cy.setDecimals(2)
        self.polygon_cy.setValue(polygon.center.y)
        self.polygon_cy.valueChanged.connect(self._on_polygon_center_y_changed)
        
        center_layout.addRow("X:", self.polygon_cx)
        center_layout.addRow("Y:", self.polygon_cy)
        self.content_layout.addWidget(center_group)
        
        # Параметры
        params_group = QGroupBox("Параметры")
        params_layout = QFormLayout(params_group)
        
        self.polygon_radius = QDoubleSpinBox()
        self.polygon_radius.setRange(0.01, 99999)
        self.polygon_radius.setDecimals(2)
        self.polygon_radius.setValue(polygon.radius)
        self.polygon_radius.valueChanged.connect(self._on_polygon_radius_changed)
        
        self.polygon_num_sides = QSpinBox()
        self.polygon_num_sides.setRange(3, 100)
        self.polygon_num_sides.setValue(polygon.num_sides)
        self.polygon_num_sides.valueChanged.connect(self._on_polygon_num_sides_changed)
        
        self.polygon_type_combo = QComboBox()
        self.polygon_type_combo.addItem("Вписанный", PolygonType.INSCRIBED)
        self.polygon_type_combo.addItem("Описанный", PolygonType.CIRCUMSCRIBED)
        # Устанавливаем текущий тип
        if polygon.polygon_type == PolygonType.CIRCUMSCRIBED:
            self.polygon_type_combo.setCurrentIndex(1)
        self.polygon_type_combo.currentIndexChanged.connect(self._on_polygon_type_changed)
        
        self.polygon_rotation = QDoubleSpinBox()
        self.polygon_rotation.setRange(-360, 360)
        self.polygon_rotation.setDecimals(1)
        self.polygon_rotation.setSuffix("°")
        self.polygon_rotation.setValue(polygon.rotation)
        self.polygon_rotation.valueChanged.connect(self._on_polygon_rotation_changed)
        
        params_layout.addRow("Радиус:", self.polygon_radius)
        params_layout.addRow("Кол-во сторон:", self.polygon_num_sides)
        params_layout.addRow("Тип:", self.polygon_type_combo)
        params_layout.addRow("Поворот:", self.polygon_rotation)
        self.content_layout.addWidget(params_group)
        
        self.content_layout.addStretch()
    
    def _on_polygon_center_x_changed(self, value):
        if self.current_object and isinstance(self.current_object, Polygon):
            self.current_object.center = Point(value, self.current_object.center.y)
            self._emit_change()
    
    def _on_polygon_center_y_changed(self, value):
        if self.current_object and isinstance(self.current_object, Polygon):
            self.current_object.center = Point(self.current_object.center.x, value)
            self._emit_change()
    
    def _on_polygon_radius_changed(self, value):
        if self.current_object and isinstance(self.current_object, Polygon):
            self.current_object.radius = value
            self._emit_change()
    
    def _on_polygon_num_sides_changed(self, value):
        if self.current_object and isinstance(self.current_object, Polygon):
            self.current_object.num_sides = value
            self._emit_change()
    
    def _on_polygon_type_changed(self, index):
        if self.current_object and isinstance(self.current_object, Polygon):
            self.current_object.polygon_type = self.polygon_type_combo.itemData(index)
            self._emit_change()
    
    def _on_polygon_rotation_changed(self, value):
        if self.current_object and isinstance(self.current_object, Polygon):
            self.current_object.rotation = value
            self._emit_change()
    
    def _create_spline_editor(self, spline: Spline):
        """Редактор для сплайна."""
        self.title_label.setText("Сплайн")
        
        # Информация
        info_group = QGroupBox("Информация")
        info_layout = QFormLayout(info_group)
        
        self.spline_points_label = QLabel(str(spline.num_points))
        info_layout.addRow("Точек:", self.spline_points_label)
        
        length_label = QLabel(f"{spline.approximate_length:.2f}")
        info_layout.addRow("Длина (прибл.):", length_label)
        
        self.content_layout.addWidget(info_group)
        
        # Контрольные точки
        points_group = QGroupBox("Контрольные точки")
        points_layout = QVBoxLayout(points_group)
        
        for i, cp in enumerate(spline.control_points):
            point_widget = QWidget()
            point_layout = QHBoxLayout(point_widget)
            point_layout.setContentsMargins(0, 0, 0, 0)
            
            point_label = QLabel(f"#{i+1}")
            point_label.setFixedWidth(25)
            
            spin_x = QDoubleSpinBox()
            spin_x.setRange(-99999, 99999)
            spin_x.setDecimals(2)
            spin_x.setValue(cp.x)
            spin_x.setProperty("point_index", i)
            spin_x.valueChanged.connect(lambda val, idx=i: self._on_spline_point_x_changed(idx, val))
            
            spin_y = QDoubleSpinBox()
            spin_y.setRange(-99999, 99999)
            spin_y.setDecimals(2)
            spin_y.setValue(cp.y)
            spin_y.setProperty("point_index", i)
            spin_y.valueChanged.connect(lambda val, idx=i: self._on_spline_point_y_changed(idx, val))
            
            # Кнопка удаления точки
            del_btn = QPushButton("×")
            del_btn.setFixedSize(20, 20)
            del_btn.setEnabled(spline.num_points > 2)
            del_btn.clicked.connect(lambda checked, idx=i: self._on_spline_delete_point(idx))
            
            point_layout.addWidget(point_label)
            point_layout.addWidget(QLabel("X:"))
            point_layout.addWidget(spin_x)
            point_layout.addWidget(QLabel("Y:"))
            point_layout.addWidget(spin_y)
            point_layout.addWidget(del_btn)
            
            points_layout.addWidget(point_widget)
        
        self.content_layout.addWidget(points_group)
        
        # Кнопка добавления точки
        add_btn = QPushButton("Добавить точку")
        add_btn.clicked.connect(self._on_spline_add_point)
        self.content_layout.addWidget(add_btn)
        
        self.content_layout.addStretch()
    
    def _on_spline_point_x_changed(self, index: int, value: float):
        if self.current_object and isinstance(self.current_object, Spline):
            if 0 <= index < len(self.current_object.control_points):
                old_point = self.current_object.control_points[index]
                self.current_object.control_points[index] = Point(value, old_point.y)
                self.current_object._cached_curve_points = None
                self._emit_change()
    
    def _on_spline_point_y_changed(self, index: int, value: float):
        if self.current_object and isinstance(self.current_object, Spline):
            if 0 <= index < len(self.current_object.control_points):
                old_point = self.current_object.control_points[index]
                self.current_object.control_points[index] = Point(old_point.x, value)
                self.current_object._cached_curve_points = None
                self._emit_change()
    
    def _on_spline_delete_point(self, index: int):
        if self.current_object and isinstance(self.current_object, Spline):
            if self.current_object.remove_point(index):
                self._emit_change()
                # Перестраиваем панель
                self.update_for_selection([self.current_object])
    
    def _on_spline_add_point(self):
        if self.current_object and isinstance(self.current_object, Spline):
            # Добавляем точку в конец, сдвинутую относительно последней
            if len(self.current_object.control_points) > 0:
                last = self.current_object.control_points[-1]
                new_point = Point(last.x + 20, last.y + 20)
            else:
                new_point = Point(0, 0)
            
            self.current_object.add_point(new_point)
            self._emit_change()
            # Перестраиваем панель
            self.update_for_selection([self.current_object])
