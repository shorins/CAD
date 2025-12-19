"""
Менеджер объектных привязок (Object Snap Manager).

Обеспечивает:
- Поиск точек привязки по курсору
- Настройку активных типов привязок
- Визуализацию привязок
"""

import math
from typing import List, Optional, Set
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal

from .geometry import SnapPoint, SnapType, GeometricPrimitive


@dataclass
class SnapResult:
    """Результат поиска привязки."""
    point: SnapPoint
    screen_x: float  # Экранные координаты для отображения
    screen_y: float
    distance: float  # Расстояние до курсора (в сценовых единицах)


class SnapManager(QObject):
    """
    Менеджер объектных привязок.
    
    Отвечает за:
    - Хранение активных типов привязок
    - Поиск ближайшей привязки к курсору
    - Сигналы об изменении настроек привязок
    """
    
    # Сигнал при изменении настроек привязок
    snap_settings_changed = Signal()
    
    # Сигнал при нахождении точки привязки (x, y, snap_type)
    snap_found = Signal(float, float, str)
    
    def __init__(self):
        super().__init__()
        
        # Активные типы привязок
        self._active_snaps: Set[SnapType] = {
            SnapType.ENDPOINT,
            SnapType.MIDPOINT,
            SnapType.CENTER,
        }
        
        # Радиус захвата привязки в пикселях экрана
        self.snap_radius = 15.0
        
        # Глобальное включение/выключение привязок
        self.enabled = True
        
        # Последняя найденная привязка (для отображения)
        self._current_snap: Optional[SnapResult] = None

    # ==================== Настройки привязок ====================
    
    def is_snap_active(self, snap_type: SnapType) -> bool:
        """Проверяет, активен ли тип привязки."""
        return snap_type in self._active_snaps
    
    def set_snap_active(self, snap_type: SnapType, active: bool):
        """Включает или выключает тип привязки."""
        if active:
            self._active_snaps.add(snap_type)
        else:
            self._active_snaps.discard(snap_type)
        self.snap_settings_changed.emit()
    
    def toggle_snap(self, snap_type: SnapType):
        """Переключает тип привязки."""
        if snap_type in self._active_snaps:
            self._active_snaps.discard(snap_type)
        else:
            self._active_snaps.add(snap_type)
        self.snap_settings_changed.emit()
    
    def get_active_snaps(self) -> Set[SnapType]:
        """Возвращает множество активных типов привязок."""
        return self._active_snaps.copy()
    
    def set_active_snaps(self, snap_types: Set[SnapType]):
        """Устанавливает активные типы привязок."""
        self._active_snaps = snap_types.copy()
        self.snap_settings_changed.emit()
    
    def enable_all(self):
        """Включает все типы привязок."""
        self._active_snaps = set(SnapType)
        self.snap_settings_changed.emit()
    
    def disable_all(self):
        """Выключает все типы привязок."""
        self._active_snaps.clear()
        self.snap_settings_changed.emit()
    
    def set_enabled(self, enabled: bool):
        """Глобальное включение/выключение привязок."""
        self.enabled = enabled
        self.snap_settings_changed.emit()

    # ==================== Поиск привязок ====================
    
    def find_snap(self, scene_x: float, scene_y: float, 
                  objects: List[GeometricPrimitive],
                  tolerance: float = 10.0,
                  exclude_object: Optional[GeometricPrimitive] = None) -> Optional[SnapPoint]:
        """
        Ищет ближайшую точку привязки к заданным координатам.
        
        Args:
            scene_x, scene_y: Координаты в сцене
            objects: Список геометрических объектов для поиска
            tolerance: Максимальное расстояние в сценовых единицах
            exclude_object: Объект, который нужно исключить из поиска
            
        Returns:
            Ближайшая точка привязки или None
        """
        if not self.enabled or not self._active_snaps:
            self._current_snap = None
            return None
        
        best_snap: Optional[SnapPoint] = None
        best_distance = tolerance
        
        for obj in objects:
            if obj is exclude_object:
                continue
            
            snap_points = obj.get_snap_points()
            
            for sp in snap_points:
                if sp.snap_type not in self._active_snaps:
                    continue
                
                dist = sp.distance_to(scene_x, scene_y)
                
                if dist < best_distance:
                    best_distance = dist
                    best_snap = sp
        
        return best_snap
    
    def find_snap_screen(self, screen_x: float, screen_y: float,
                         objects: List[GeometricPrimitive],
                         map_to_scene_func,
                         zoom_factor: float = 1.0,
                         exclude_object: Optional[GeometricPrimitive] = None) -> Optional[SnapResult]:
        """
        Ищет привязку по экранным координатам.
        
        Args:
            screen_x, screen_y: Экранные координаты курсора
            objects: Список объектов
            map_to_scene_func: Функция преобразования экранных координат в сценовые
            zoom_factor: Текущий масштаб (для корректного расчёта tolerance)
            exclude_object: Объект для исключения из поиска
            
        Returns:
            SnapResult или None
        """
        if not self.enabled:
            self._current_snap = None
            return None
        
        from PySide6.QtCore import QPointF
        
        # Преобразуем экранные координаты в сценовые
        scene_pos = map_to_scene_func(QPointF(screen_x, screen_y))
        
        # Tolerance в сценовых единицах = snap_radius / zoom_factor
        tolerance = self.snap_radius / zoom_factor
        
        snap_point = self.find_snap(scene_pos.x(), scene_pos.y(), 
                                    objects, tolerance, exclude_object)
        
        if snap_point:
            result = SnapResult(
                point=snap_point,
                screen_x=screen_x,
                screen_y=screen_y,
                distance=snap_point.distance_to(scene_pos.x(), scene_pos.y())
            )
            self._current_snap = result
            return result
        
        self._current_snap = None
        return None
    
    def get_current_snap(self) -> Optional[SnapResult]:
        """Возвращает последнюю найденную привязку."""
        return self._current_snap
    
    def clear_current_snap(self):
        """Очищает текущую привязку."""
        self._current_snap = None

    # ==================== Вспомогательные методы ====================
    
    def find_intersection(self, obj1: GeometricPrimitive, 
                          obj2: GeometricPrimitive) -> List[SnapPoint]:
        """
        Находит точки пересечения двух объектов.
        
        TODO: Реализовать для разных комбинаций примитивов.
        """
        intersections = []
        
        # Здесь будет логика поиска пересечений
        # Пока возвращаем пустой список
        
        return intersections
    
    def find_perpendicular(self, from_point: tuple, 
                           to_object: GeometricPrimitive) -> Optional[SnapPoint]:
        """
        Находит точку перпендикуляра от точки к объекту.
        
        TODO: Реализовать для разных примитивов.
        """
        from .geometry import Line
        
        if isinstance(to_object, Line):
            from .geometry import Point
            perp = to_object.get_perpendicular_point(Point(from_point[0], from_point[1]))
            return SnapPoint(perp.x, perp.y, SnapType.PERPENDICULAR, to_object)
        
        return None

    # ==================== Сериализация ====================
    
    def to_dict(self) -> dict:
        """Сохраняет настройки привязок."""
        return {
            "enabled": self.enabled,
            "snap_radius": self.snap_radius,
            "active_snaps": [st.name for st in self._active_snaps],
        }
    
    def from_dict(self, data: dict):
        """Загружает настройки привязок."""
        self.enabled = data.get("enabled", True)
        self.snap_radius = data.get("snap_radius", 15.0)
        
        active_names = data.get("active_snaps", [])
        self._active_snaps = set()
        for name in active_names:
            try:
                self._active_snaps.add(SnapType[name])
            except KeyError:
                pass  # Игнорируем неизвестные типы
        
        self.snap_settings_changed.emit()


# Глобальный экземпляр менеджера привязок
snap_manager = SnapManager()
