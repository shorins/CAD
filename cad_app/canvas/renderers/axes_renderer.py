"""Axes renderer module for drawing coordinate axes."""

from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import QPointF, QSize


class AxesRenderer:
    """Renders the X and Y coordinate axes on the canvas."""
    
    def __init__(self, view_transform):
        """Initialize the axes renderer.
        
        Args:
            view_transform: ViewTransform instance for coordinate conversion
        """
        self.view_transform = view_transform
    
    def render(self, painter: QPainter, widget_size: QSize) -> None:
        """Рисует оси координат с учетом поворота.
        
        Ось X (зеленая) - горизонтальная линия через начало координат
        Ось Y (красная) - вертикальная линия через начало координат
        
        Args:
            painter: QPainter для рисования
            widget_size: Размер виджета
        """
        width, height = widget_size.width(), widget_size.height()
        
        # Находим диапазон для осей, проверяя все углы экрана
        corners = [
            self.view_transform.map_to_scene(QPointF(0, 0)),
            self.view_transform.map_to_scene(QPointF(width, 0)),
            self.view_transform.map_to_scene(QPointF(0, height)),
            self.view_transform.map_to_scene(QPointF(width, height))
        ]
        
        scene_x_min = min(corner.x() for corner in corners)
        scene_x_max = max(corner.x() for corner in corners)
        scene_y_min = min(corner.y() for corner in corners)
        scene_y_max = max(corner.y() for corner in corners)
        
        # Рисуем ось Y (вертикальная в сцене, X=0)
        painter.setPen(QPen(QColor("#CC7A7A"), 1.5))
        y_axis_start = self.view_transform.map_from_scene(QPointF(0, scene_y_min))
        y_axis_end = self.view_transform.map_from_scene(QPointF(0, scene_y_max))
        painter.drawLine(y_axis_start.toPoint(), y_axis_end.toPoint())
        
        # Рисуем ось X (горизонтальная в сцене, Y=0)
        painter.setPen(QPen(QColor("#7ACC7A"), 1.5))
        x_axis_start = self.view_transform.map_from_scene(QPointF(scene_x_min, 0))
        x_axis_end = self.view_transform.map_from_scene(QPointF(scene_x_max, 0))
        painter.drawLine(x_axis_start.toPoint(), x_axis_end.toPoint())
