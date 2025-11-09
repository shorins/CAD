"""Pan tool implementation."""

import math
from PySide6.QtGui import QPainter, QMouseEvent, QKeyEvent
from PySide6.QtCore import Qt, QPointF

from .base_tool import BaseTool


class PanTool(BaseTool):
    """Tool for panning the canvas view."""
    
    def __init__(self, canvas_widget):
        """Initialize the pan tool.
        
        Args:
            canvas_widget: Reference to the CanvasWidget
        """
        super().__init__(canvas_widget)
        self.is_panning = False  # Флаг активного панорамирования
        self.pan_start_pos = None  # Начальная позиция мыши
        self.pan_start_camera = None  # Начальная позиция камеры
    
    def activate(self) -> None:
        """Активирует инструмент панорамирования."""
        self.active = True
        self.is_panning = False
        self.pan_start_pos = None
        self.pan_start_camera = None
        self.canvas.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def deactivate(self) -> None:
        """Деактивирует инструмент панорамирования."""
        self.active = False
        self.is_panning = False
        self.pan_start_pos = None
        self.pan_start_camera = None
        self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
    
    def mouse_press(self, event: QMouseEvent) -> bool:
        """Обрабатывает нажатие кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = True
            self.pan_start_pos = event.position()
            self.pan_start_camera = QPointF(
                self.canvas.view_transform.camera_pos.x(),
                self.canvas.view_transform.camera_pos.y()
            )
            self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
            return False  # Не требуется перерисовка
        return False
    
    def mouse_move(self, event: QMouseEvent) -> bool:
        """Обрабатывает движение мыши."""
        if self.is_panning:
            # Вычисляем смещение в экранных координатах
            screen_delta_x = event.position().x() - self.pan_start_pos.x()
            screen_delta_y = event.position().y() - self.pan_start_pos.y()
            
            # Преобразуем в сценовые координаты с учетом zoom
            scene_delta_x = screen_delta_x / self.canvas.view_transform.zoom_factor
            scene_delta_y = -screen_delta_y / self.canvas.view_transform.zoom_factor  # Инверсия Y
            
            # Применяем обратный поворот к delta
            angle_rad = -math.radians(self.canvas.view_transform.rotation_angle)
            cos_angle = math.cos(angle_rad)
            sin_angle = math.sin(angle_rad)
            rotated_delta_x = scene_delta_x * cos_angle - scene_delta_y * sin_angle
            rotated_delta_y = scene_delta_x * sin_angle + scene_delta_y * cos_angle
            
            # Обновляем позицию камеры
            self.canvas.view_transform.camera_pos = QPointF(
                self.pan_start_camera.x() - rotated_delta_x,
                self.pan_start_camera.y() - rotated_delta_y
            )
            
            return True  # Требуется перерисовка
        return False
    
    def mouse_release(self, event: QMouseEvent) -> bool:
        """Обрабатывает отпускание кнопки мыши."""
        if self.is_panning and event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.pan_start_pos = None
            self.pan_start_camera = None
            # Восстанавливаем курсор открытой руки только если pan tool активен
            if self.active:
                self.canvas.setCursor(Qt.CursorShape.OpenHandCursor)
            return False  # Не требуется перерисовка
        return False
    
    def key_press(self, event: QKeyEvent) -> bool:
        """Обрабатывает нажатие клавиши."""
        return False
    
    def paint(self, painter: QPainter) -> None:
        """Pan tool не рисует ничего дополнительного."""
        pass
