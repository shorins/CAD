"""Selection manager for object selection and highlighting."""

from PySide6.QtCore import QPointF

from ..core.scene import Scene
from ..core.geometry import Line
from ..core.math_utils import distance_point_to_segment_sq


class SelectionManager:
    """Manages object selection and hover highlighting."""
    
    def __init__(self, view_transform):
        """Initialize the selection manager.
        
        Args:
            view_transform: ViewTransform instance for coordinate conversion
        """
        self.view_transform = view_transform
        self.hover_object = None  # Объект под курсором (голубая подсветка)
        self.selected_object = None  # Выбранный объект
        self.selection_threshold = 10.0  # Пороговое расстояние в пикселях
    
    def find_object_at_cursor(self, cursor_pos: QPointF, scene: Scene) -> object | None:
        """Находит объект под курсором.
        
        Args:
            cursor_pos: Позиция курсора в экранных координатах
            scene: Scene с объектами
            
        Returns:
            Объект под курсором или None
        """
        scene_cursor_pos = self.view_transform.map_to_scene(cursor_pos)
        cursor_qpoint = QPointF(scene_cursor_pos.x(), scene_cursor_pos.y())
        
        nearest_object = None
        min_distance_sq = self.selection_threshold ** 2
        
        for obj in scene.objects:
            if isinstance(obj, Line):
                start_qpoint = QPointF(obj.start.x, obj.start.y)
                end_qpoint = QPointF(obj.end.x, obj.end.y)
                
                distance_sq = distance_point_to_segment_sq(cursor_qpoint, start_qpoint, end_qpoint)
                
                if distance_sq < min_distance_sq:
                    min_distance_sq = distance_sq
                    nearest_object = obj
        
        return nearest_object
    
    def update_hover(self, cursor_pos: QPointF, scene: Scene) -> bool:
        """Обновляет hover объект.
        
        Args:
            cursor_pos: Позиция курсора в экранных координатах
            scene: Scene с объектами
            
        Returns:
            True если hover объект изменился
        """
        old_hover = self.hover_object
        self.hover_object = self.find_object_at_cursor(cursor_pos, scene)
        return old_hover != self.hover_object
    
    def update_selection(self, cursor_pos: QPointF, scene: Scene) -> bool:
        """Обновляет выбранный объект.
        
        Args:
            cursor_pos: Позиция курсора в экранных координатах
            scene: Scene с объектами
            
        Returns:
            True если выбранный объект изменился
        """
        old_selection = self.selected_object
        self.selected_object = self.find_object_at_cursor(cursor_pos, scene)
        return old_selection != self.selected_object
    
    def clear_hover(self) -> None:
        """Очищает hover объект."""
        self.hover_object = None
    
    def clear_selection(self) -> None:
        """Очищает выбранный объект."""
        self.selected_object = None
