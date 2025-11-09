"""Grid renderer module for drawing the canvas grid."""

import math
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import QPointF, QSize

from ...settings import settings


class GridRenderer:
    """Renders the grid on the canvas with major and minor lines."""
    
    def __init__(self, view_transform):
        """Initialize the grid renderer.
        
        Args:
            view_transform: ViewTransform instance for coordinate conversion
        """
        self.view_transform = view_transform
        self.major_grid_interval = 5  # Каждая 5-я линия - major
    
    def render(self, painter: QPainter, widget_size: QSize) -> None:
        """Рисует сетку на canvas.
        
        Args:
            painter: QPainter для рисования
            widget_size: Размер виджета
        """
        colors = settings.get("colors") or settings.defaults["colors"]
        pen_minor = QPen(QColor(colors.get("grid_minor", "#000000")), 0.5)
        pen_major = QPen(QColor(colors.get("grid_major", "#000000")), 1)
        grid_size = settings.get("grid_step") or settings.defaults["grid_step"]
        
        width, height = widget_size.width(), widget_size.height()
        
        # При повороте нужно проверить все 4 угла экрана
        corners = [
            self.view_transform.map_to_scene(QPointF(0, 0)),           # Верхний левый
            self.view_transform.map_to_scene(QPointF(width, 0)),       # Верхний правый
            self.view_transform.map_to_scene(QPointF(0, height)),      # Нижний левый
            self.view_transform.map_to_scene(QPointF(width, height))   # Нижний правый
        ]
        
        # Находим минимальные и максимальные координаты сцены
        scene_x_min = min(corner.x() for corner in corners)
        scene_x_max = max(corner.x() for corner in corners)
        scene_y_min = min(corner.y() for corner in corners)
        scene_y_max = max(corner.y() for corner in corners)
        
        start_x_index = math.floor(scene_x_min / grid_size)
        end_x_index = math.ceil(scene_x_max / grid_size)
        start_y_index = math.floor(scene_y_min / grid_size)
        end_y_index = math.ceil(scene_y_max / grid_size)
        
        # Определяем, нужно ли рисовать minor линии на основе zoom_factor
        # При zoom < 0.5 скрываем minor линии для улучшения производительности
        show_minor_lines = self.view_transform.zoom_factor >= 0.5
        
        # Рисуем вертикальные линии сетки (постоянный X в сцене)
        for i in range(start_x_index, end_x_index + 1):
            is_major = (i % self.major_grid_interval == 0)
            
            # Пропускаем minor линии, если zoom слишком мал
            if not is_major and not show_minor_lines:
                continue
            
            painter.setPen(pen_major if is_major else pen_minor)
            line_scene_x = i * grid_size
            
            # Линия от минимального Y до максимального Y в сцене
            start_screen = self.view_transform.map_from_scene(QPointF(line_scene_x, scene_y_min))
            end_screen = self.view_transform.map_from_scene(QPointF(line_scene_x, scene_y_max))
            painter.drawLine(start_screen.toPoint(), end_screen.toPoint())
        
        # Рисуем горизонтальные линии сетки (постоянный Y в сцене)
        for i in range(start_y_index, end_y_index + 1):
            is_major = (i % self.major_grid_interval == 0)
            
            # Пропускаем minor линии, если zoom слишком мал
            if not is_major and not show_minor_lines:
                continue
            
            painter.setPen(pen_major if is_major else pen_minor)
            line_scene_y = i * grid_size
            
            # Линия от минимального X до максимального X в сцене
            start_screen = self.view_transform.map_from_scene(QPointF(scene_x_min, line_scene_y))
            end_screen = self.view_transform.map_from_scene(QPointF(scene_x_max, line_scene_y))
            painter.drawLine(start_screen.toPoint(), end_screen.toPoint())
