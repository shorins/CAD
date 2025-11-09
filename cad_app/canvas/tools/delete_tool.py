"""Delete tool implementation."""

from PySide6.QtGui import QPainter, QMouseEvent, QKeyEvent
from PySide6.QtCore import Qt, QPointF

from .base_tool import BaseTool
from ...core.geometry import Line
from ...core.math_utils import distance_point_to_segment_sq


class DeleteTool(BaseTool):
    """Tool for deleting objects from the canvas."""
    
    def __init__(self, canvas_widget):
        """Initialize the delete tool.
        
        Args:
            canvas_widget: Reference to the CanvasWidget
        """
        super().__init__(canvas_widget)
        self.highlighted_line = None  # Линия, выделенная для удаления (красная)
        self.selection_threshold = 10.0  # Пороговое расстояние в пикселях
    
    def activate(self) -> None:
        """Активирует инструмент удаления."""
        self.active = True
        self.highlighted_line = None
        self.canvas.setCursor(Qt.CursorShape.CrossCursor)
    
    def deactivate(self) -> None:
        """Деактивирует инструмент удаления."""
        self.active = False
        self.highlighted_line = None
        self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
    
    def mouse_press(self, event: QMouseEvent) -> bool:
        """Обрабатывает нажатие кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self.highlighted_line:
            # Удаляем выделенную линию
            self.canvas.scene.remove_object(self.highlighted_line)
            self.highlighted_line = None
            return True
        return False
    
    def mouse_move(self, event: QMouseEvent) -> bool:
        """Обрабатывает движение мыши."""
        # Ищем ближайшую линию к курсору
        old_highlighted = self.highlighted_line
        self._find_nearest_line(event.position())
        
        # Меняем курсор в зависимости от наличия выделенной линии
        if self.highlighted_line:
            self.canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        
        # Возвращаем True если выделение изменилось
        return old_highlighted != self.highlighted_line
    
    def mouse_release(self, event: QMouseEvent) -> bool:
        """Обрабатывает отпускание кнопки мыши."""
        return False
    
    def key_press(self, event: QKeyEvent) -> bool:
        """Обрабатывает нажатие клавиши."""
        return False
    
    def paint(self, painter: QPainter) -> None:
        """Рисует выделенную линию красным цветом."""
        if self.highlighted_line:
            # Используем object_renderer для отрисовки с красным цветом
            self.canvas.object_renderer.render_line_with_color(
                painter, self.highlighted_line, "#FF4444", 3
            )
    
    def _find_nearest_line(self, cursor_pos: QPointF) -> None:
        """Находит ближайшую линию к курсору."""
        scene_cursor_pos = self.canvas.view_transform.map_to_scene(cursor_pos)
        cursor_qpoint = QPointF(scene_cursor_pos.x(), scene_cursor_pos.y())
        
        nearest_line = None
        min_distance_sq = self.selection_threshold ** 2
        
        for obj in self.canvas.scene.objects:
            if isinstance(obj, Line):
                start_qpoint = QPointF(obj.start.x, obj.start.y)
                end_qpoint = QPointF(obj.end.x, obj.end.y)
                
                # Вычисляем расстояние от курсора до отрезка
                distance_sq = distance_point_to_segment_sq(cursor_qpoint, start_qpoint, end_qpoint)
                
                if distance_sq < min_distance_sq:
                    min_distance_sq = distance_sq
                    nearest_line = obj
        
        self.highlighted_line = nearest_line
