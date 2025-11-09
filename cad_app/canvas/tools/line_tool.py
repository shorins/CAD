"""Line drawing tool implementation."""

from PySide6.QtGui import QPainter, QMouseEvent, QKeyEvent, QPen, QColor
from PySide6.QtCore import Qt, QPointF

from .base_tool import BaseTool
from ...core.geometry import Line, Point
from ...core.math_utils import (cartesian_to_polar, get_distance, 
                                get_angle_between_points, radians_to_degrees,
                                polar_to_cartesian)
from ...settings import settings


class LineTool(BaseTool):
    """Tool for drawing lines on the canvas."""
    
    def __init__(self, canvas_widget):
        """Initialize the line tool.
        
        Args:
            canvas_widget: Reference to the CanvasWidget
        """
        super().__init__(canvas_widget)
        self.start_pos = None  # Начальная позиция в экранных координатах
        self.current_pos = None  # Текущая позиция курсора
        self._current_construction_mode = settings.get("line_construction_mode") or "cartesian"
    
    def activate(self) -> None:
        """Активирует инструмент линии."""
        self.active = True
        self.start_pos = None
        self.current_pos = None
        self._current_construction_mode = settings.get("line_construction_mode") or "cartesian"
    
    def deactivate(self) -> None:
        """Деактивирует инструмент линии."""
        self.active = False
        self.start_pos = None
        self.current_pos = None
        # Очищаем информацию о линии
        self.canvas.line_info_changed.emit("")
    
    def mouse_press(self, event: QMouseEvent) -> bool:
        """Обрабатывает нажатие кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.start_pos is None:
                # Первый клик: начинаем рисовать линию
                self.start_pos = event.position()
                self.current_pos = self.start_pos
                self._update_line_info()
                return True
            else:
                # Второй клик: завершаем линию
                start_scene_pos = self.canvas.view_transform.map_to_scene(self.start_pos)
                
                if self._current_construction_mode == "polar":
                    # В полярном режиме используем текущую позицию курсора
                    cursor_pos = self.current_pos if self.current_pos else event.position()
                    current_scene_pos = self.canvas.view_transform.map_to_scene(cursor_pos)
                    end_point_qpoint = self._calculate_end_point_polar(start_scene_pos, current_scene_pos)
                    end_point = Point(end_point_qpoint.x(), end_point_qpoint.y())
                else:
                    # В декартовом режиме используем позицию клика напрямую
                    end_scene_pos = self.canvas.view_transform.map_to_scene(event.position())
                    end_point = Point(end_scene_pos.x(), end_scene_pos.y())
                
                start_point = Point(start_scene_pos.x(), start_scene_pos.y())
                line = Line(start_point, end_point)
                self.canvas.scene.add_object(line)
                
                self.start_pos = None
                self.current_pos = None
                self.canvas.line_info_changed.emit("")
                return True
        
        elif event.button() == Qt.MouseButton.RightButton and self.start_pos:
            # Отмена рисования правой кнопкой мыши
            self.start_pos = None
            self.current_pos = None
            self.canvas.line_info_changed.emit("")
            return True
        
        return False
    
    def mouse_move(self, event: QMouseEvent) -> bool:
        """Обрабатывает движение мыши."""
        if self.start_pos:
            self.current_pos = event.position()
            self._update_line_info()
            return True
        return False
    
    def mouse_release(self, event: QMouseEvent) -> bool:
        """Обрабатывает отпускание кнопки мыши."""
        return False
    
    def key_press(self, event: QKeyEvent) -> bool:
        """Обрабатывает нажатие клавиши."""
        # Обработка Escape для отмены построения линии
        if event.key() == Qt.Key.Key_Escape and self.start_pos:
            self.start_pos = None
            self.current_pos = None
            self.canvas.line_info_changed.emit("")
            return True
        return False
    
    def paint(self, painter: QPainter) -> None:
        """Рисует preview линии."""
        if self.start_pos and self.current_pos:
            pen = QPen(QColor("#7A86CC"), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            
            if self._current_construction_mode == "polar":
                # В полярном режиме вычисляем конечную точку из полярных координат
                start_scene_pos = self.canvas.view_transform.map_to_scene(self.start_pos)
                current_scene_pos = self.canvas.view_transform.map_to_scene(self.current_pos)
                end_point = self._calculate_end_point_polar(start_scene_pos, current_scene_pos)
                end_screen = self.canvas.view_transform.map_from_scene(end_point)
                painter.drawLine(self.start_pos.toPoint(), end_screen.toPoint())
            else:
                # В декартовом режиме рисуем прямую линию
                painter.drawLine(self.start_pos.toPoint(), self.current_pos.toPoint())
    
    def on_construction_mode_changed(self) -> None:
        """Обработчик изменения режима построения."""
        self._current_construction_mode = settings.get("line_construction_mode") or "cartesian"
        # Если мы в процессе построения линии, обновляем информацию
        if self.start_pos:
            self._update_line_info()
    
    def _calculate_end_point_polar(self, start_scene: QPointF, cursor_scene: QPointF) -> QPointF:
        """Вычисляет конечную точку линии в полярных координатах."""
        r, theta = cartesian_to_polar(start_scene, cursor_scene)
        end_point = polar_to_cartesian(start_scene, r, theta)
        return end_point
    
    def _update_line_info(self) -> None:
        """Обновляет информацию о линии в статус-баре."""
        if not self.start_pos or not self.current_pos:
            self.canvas.line_info_changed.emit("")
            return
        
        start_scene_pos = self.canvas.view_transform.map_to_scene(self.start_pos)
        current_scene_pos = self.canvas.view_transform.map_to_scene(self.current_pos)
        
        # Вычисляем расстояние (длину линии)
        length = get_distance(start_scene_pos, current_scene_pos)
        
        # Вычисляем угол
        angle_rad = get_angle_between_points(start_scene_pos, current_scene_pos)
        
        # Получаем единицы измерения углов из настроек
        angle_units = settings.get("angle_units") or "degrees"
        
        if self._current_construction_mode == "polar":
            # В полярном режиме показываем полярные координаты
            r, theta = cartesian_to_polar(start_scene_pos, current_scene_pos)
            
            if angle_units == "degrees":
                angle_display = radians_to_degrees(theta)
                angle_unit_str = "°"
            else:
                angle_display = theta
                angle_unit_str = " rad"
            
            info = f"r: {r:.2f}, θ: {angle_display:.2f}{angle_unit_str} | Длина: {length:.2f}"
        else:
            # В декартовом режиме показываем декартовы координаты и угол
            if angle_units == "degrees":
                angle_display = radians_to_degrees(angle_rad)
                angle_unit_str = "°"
            else:
                angle_display = angle_rad
                angle_unit_str = " rad"
            
            info = f"Длина: {length:.2f} | Угол: {angle_display:.2f}{angle_unit_str}"
        
        self.canvas.line_info_changed.emit(info)
