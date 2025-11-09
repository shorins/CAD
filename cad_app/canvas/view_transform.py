"""View transformation module for coordinate conversions and camera management."""

import math
from PySide6.QtCore import QPointF, QSize


class ViewTransform:
    """Manages coordinate transformations between screen and scene space.
    
    Handles zoom, pan, and rotation transformations for the canvas view.
    """
    
    def __init__(self, widget_size: QSize):
        """Initialize the view transform.
        
        Args:
            widget_size: Initial size of the widget
        """
        self.camera_pos = QPointF(0, 0)
        self.zoom_factor = 1.0
        self.rotation_angle = 0.0  # В градусах (0-360)
        self.widget_size = widget_size
        self._initial_center_done = False
    
    def map_to_scene(self, screen_pos: QPointF) -> QPointF:
        """Преобразует экранные координаты в сценовые координаты.
        
        Применяет инверсию Y, zoom и rotation. В математической системе 
        координат Y увеличивается вверх.
        
        Args:
            screen_pos: Позиция в экранных координатах
            
        Returns:
            Позиция в сценовых координатах
        """
        # 1. Центрируем относительно экрана
        centered_x = screen_pos.x() - self.widget_size.width() / 2
        centered_y = self.widget_size.height() / 2 - screen_pos.y()
        
        # 2. Применяем обратный поворот (разворачиваем вид обратно)
        angle_rad = -math.radians(self.rotation_angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        rotated_x = centered_x * cos_angle - centered_y * sin_angle
        rotated_y = centered_x * sin_angle + centered_y * cos_angle
        
        # 3. Применяем масштаб и смещение камеры
        scene_x = rotated_x / self.zoom_factor + self.camera_pos.x()
        scene_y = rotated_y / self.zoom_factor + self.camera_pos.y()
        
        return QPointF(scene_x, scene_y)
    
    def map_from_scene(self, scene_pos: QPointF) -> QPointF:
        """Преобразует сценовые координаты в экранные координаты.
        
        Применяет инверсию Y, zoom и rotation.
        
        Args:
            scene_pos: Позиция в сценовых координатах
            
        Returns:
            Позиция в экранных координатах
        """
        # 1. Применяем смещение камеры и масштаб (умножаем на zoom_factor)
        scaled_x = (scene_pos.x() - self.camera_pos.x()) * self.zoom_factor
        scaled_y = (scene_pos.y() - self.camera_pos.y()) * self.zoom_factor
        
        # 2. Применяем поворот
        angle_rad = math.radians(self.rotation_angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        rotated_x = scaled_x * cos_angle - scaled_y * sin_angle
        rotated_y = scaled_x * sin_angle + scaled_y * cos_angle
        
        # 3. Переводим в экранные координаты
        screen_x = rotated_x + self.widget_size.width() / 2
        screen_y = self.widget_size.height() / 2 - rotated_y
        
        return QPointF(screen_x, screen_y)
    
    def update_widget_size(self, size: QSize) -> None:
        """Обновляет размер виджета для корректных преобразований.
        
        Args:
            size: Новый размер виджета
        """
        self.widget_size = size
        
        # Инициализируем камеру при первом изменении размера
        if not self._initial_center_done:
            self.camera_pos = QPointF(-self.widget_size.width() / 2, 0)
            self._initial_center_done = True
    
    def get_view_state(self) -> dict:
        """Возвращает текущее состояние вида для сохранения.
        
        Returns:
            Словарь с camera_pos, zoom_factor, rotation_angle
        """
        return {
            "camera_pos": {"x": self.camera_pos.x(), "y": self.camera_pos.y()},
            "zoom_factor": self.zoom_factor,
            "rotation_angle": self.rotation_angle
        }
    
    def set_view_state(self, state: dict) -> None:
        """Восстанавливает состояние вида из сохраненных данных.
        
        Args:
            state: Словарь с camera_pos, zoom_factor, rotation_angle
        """
        if "camera_pos" in state:
            self.camera_pos = QPointF(state["camera_pos"]["x"], state["camera_pos"]["y"])
        self.zoom_factor = state.get("zoom_factor", 1.0)
        self.rotation_angle = state.get("rotation_angle", 0.0)
    
    def calculate_scene_bounds_for_screen(self) -> tuple[QPointF, QPointF, QPointF, QPointF]:
        """Вычисляет углы экрана в сценовых координатах.
        
        При повороте нужно проверить все 4 угла экрана, чтобы найти 
        правильный диапазон для отрисовки сетки и осей.
        
        Returns:
            Кортеж из 4 точек: (top_left, top_right, bottom_left, bottom_right)
        """
        width = self.widget_size.width()
        height = self.widget_size.height()
        
        top_left = self.map_to_scene(QPointF(0, 0))
        top_right = self.map_to_scene(QPointF(width, 0))
        bottom_left = self.map_to_scene(QPointF(0, height))
        bottom_right = self.map_to_scene(QPointF(width, height))
        
        return (top_left, top_right, bottom_left, bottom_right)
