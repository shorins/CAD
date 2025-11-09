"""Object renderer module for drawing scene objects."""

from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import QPointF

from ...core.scene import Scene
from ...core.geometry import Line
from ...core.algorithms import bresenham
from ...settings import settings


class ObjectRenderer:
    """Renders scene objects on the canvas."""
    
    def __init__(self, view_transform):
        """Initialize the object renderer.
        
        Args:
            view_transform: ViewTransform instance for coordinate conversion
        """
        self.view_transform = view_transform
    
    def render(self, painter: QPainter, scene: Scene, 
               excluded_objects: list = None) -> None:
        """Рисует объекты сцены.
        
        Args:
            painter: QPainter для рисования
            scene: Scene с объектами для отрисовки
            excluded_objects: Список объектов, которые не нужно рисовать 
                            (например, выделенные линии)
        """
        if excluded_objects is None:
            excluded_objects = []
        
        colors = settings.get("colors") or settings.defaults["colors"]
        pen = QPen(QColor(colors.get("line_object", "#FFFFFF")), 2)
        painter.setPen(pen)
        
        for obj in scene.objects:
            if isinstance(obj, Line):
                # Пропускаем исключенные объекты
                if obj in excluded_objects:
                    continue
                
                start_screen = self.view_transform.map_from_scene(
                    QPointF(obj.start.x, obj.start.y)
                )
                end_screen = self.view_transform.map_from_scene(
                    QPointF(obj.end.x, obj.end.y)
                )
                
                points_generator = bresenham(
                    int(start_screen.x()), int(start_screen.y()),
                    int(end_screen.x()), int(end_screen.y())
                )
                
                for point in points_generator:
                    painter.drawPoint(*point)
    
    def render_line_with_color(self, painter: QPainter, line: Line, 
                               color: str, width: int = 3) -> None:
        """Рисует линию с заданным цветом и толщиной.
        
        Используется для отрисовки выделенных или подсвеченных линий.
        
        Args:
            painter: QPainter для рисования
            line: Линия для отрисовки
            color: Цвет в формате hex (например, "#FF4444")
            width: Толщина линии в пикселях
        """
        pen = QPen(QColor(color), width)
        painter.setPen(pen)
        
        start_screen = self.view_transform.map_from_scene(
            QPointF(line.start.x, line.start.y)
        )
        end_screen = self.view_transform.map_from_scene(
            QPointF(line.end.x, line.end.y)
        )
        
        points_generator = bresenham(
            int(start_screen.x()), int(start_screen.y()),
            int(end_screen.x()), int(end_screen.y())
        )
        
        for point in points_generator:
            painter.drawPoint(*point)
