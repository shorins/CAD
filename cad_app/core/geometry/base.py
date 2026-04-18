"""
Базовый класс для всех геометрических примитивов САПР.
Обеспечивает единый интерфейс для стилизации, сериализации,
объектных привязок и контрольных точек редактирования.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .point import Point


class SnapType(Enum):
    """Типы объектных привязок."""
    ENDPOINT = auto()       # Конец (конечные точки отрезков, дуг)
    MIDPOINT = auto()       # Середина (середина отрезка, дуги)
    CENTER = auto()         # Центр (центр окружности, дуги, эллипса)
    INTERSECTION = auto()   # Пересечение (пересечение двух объектов)
    PERPENDICULAR = auto()  # Перпендикуляр
    TANGENT = auto()        # Касательная
    QUADRANT = auto()       # Квадрант (точки на окружности в 0°, 90°, 180°, 270°)
    NODE = auto()           # Узел (контрольные точки сплайна)
    NEAREST = auto()        # Ближайшая точка на объекте
    GRID = auto()           # Привязка к сетке


@dataclass
class SnapPoint:
    """Точка привязки с типом и координатами."""
    x: float
    y: float
    snap_type: SnapType
    source_object: 'GeometricPrimitive'
    
    def distance_to(self, x: float, y: float) -> float:
        """Вычисляет расстояние до заданной точки."""
        import math
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)


@dataclass  
class ControlPoint:
    """
    Контрольная точка для редактирования примитива.
    При перемещении контрольной точки вызывается callback с новыми координатами.
    """
    x: float
    y: float
    name: str  # Имя точки для отображения (например, "Центр", "Начало", "Радиус")
    index: int  # Индекс точки в примитиве для идентификации
    
    def distance_to(self, x: float, y: float) -> float:
        """Вычисляет расстояние до заданной точки."""
        import math
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)


class GeometricPrimitive(ABC):
    """
    Базовый абстрактный класс для всех геометрических примитивов.
    Обеспечивает единый интерфейс для:
    - Стилизации (style_name)
    - Сериализации (to_dict, from_dict)
    - Объектных привязок (get_snap_points)
    - Контрольных точек редактирования (get_control_points, move_control_point)
    - Геометрических расчётов (get_bounding_box, contains_point, distance_to_point)
    """
    
    def __init__(self, style_name: str = "Сплошная основная"):
        self.style_name = style_name
        self.layer_name: Optional[str] = None
        self.aci_color: Optional[int] = None
        self.true_color: Optional[int] = None
        self.linetype_name = "BYLAYER"
        self.lineweight: Optional[int] = None
        self.imported_from_dxf: bool = False
        self.source_handle: Optional[str] = None
        self.source_entity_type: Optional[str] = None
        self.source_linetype_name: Optional[str] = None
        self.promotion_kind: Optional[str] = None
        self.import_flags: List[str] = []

    def _serialize_common(self) -> dict:
        """Сериализация общих атрибутов примитива."""
        return {
            "style": self.style_name,
            "dxf": {
                "layer_name": self.layer_name,
                "aci_color": self.aci_color,
                "true_color": self.true_color,
                "linetype_name": self.linetype_name,
                "lineweight": self.lineweight,
                "imported_from_dxf": self.imported_from_dxf,
                "source_handle": self.source_handle,
                "source_entity_type": self.source_entity_type,
                "source_linetype_name": self.source_linetype_name,
                "promotion_kind": self.promotion_kind,
                "import_flags": list(self.import_flags),
            },
        }

    def _load_common(self, data: dict):
        """Восстанавливает общие атрибуты примитива."""
        self.style_name = data.get("style", self.style_name)
        dxf_data = data.get("dxf", {})
        if not isinstance(dxf_data, dict):
            return

        self.layer_name = dxf_data.get("layer_name", self.layer_name or "0") or "0"
        self.aci_color = dxf_data.get("aci_color")
        self.true_color = dxf_data.get("true_color")
        self.linetype_name = dxf_data.get("linetype_name", self.linetype_name or "BYLAYER") or "BYLAYER"
        self.lineweight = dxf_data.get("lineweight")
        self.imported_from_dxf = bool(dxf_data.get("imported_from_dxf", self.imported_from_dxf))
        self.source_handle = dxf_data.get("source_handle")
        self.source_entity_type = dxf_data.get("source_entity_type")
        self.source_linetype_name = dxf_data.get("source_linetype_name")
        self.promotion_kind = dxf_data.get("promotion_kind")
        self.import_flags = list(dxf_data.get("import_flags", []))

    # ==================== Сериализация ====================
    
    @abstractmethod
    def to_dict(self) -> dict:
        """Сериализация объекта в словарь для сохранения в JSON."""
        pass
    
    @staticmethod
    @abstractmethod
    def from_dict(data: dict) -> 'GeometricPrimitive':
        """Десериализация объекта из словаря."""
        pass

    # ==================== Объектные привязки ====================
    
    @abstractmethod
    def get_snap_points(self) -> List[SnapPoint]:
        """
        Возвращает список точек привязки для данного примитива.
        
        Returns:
            List[SnapPoint]: Список точек привязки с их типами
        """
        pass
    
    def get_snap_point_at(self, x: float, y: float, snap_types: List[SnapType], tolerance: float = 10.0) -> Optional[SnapPoint]:
        """
        Ищет ближайшую точку привязки заданных типов в пределах tolerance.
        
        Args:
            x, y: Координаты для поиска
            snap_types: Список типов привязок для поиска
            tolerance: Максимальное расстояние в единицах сцены
            
        Returns:
            Ближайшая точка привязки или None
        """
        snap_points = self.get_snap_points()
        best_point = None
        best_distance = tolerance
        
        for sp in snap_points:
            if sp.snap_type in snap_types:
                dist = sp.distance_to(x, y)
                if dist < best_distance:
                    best_distance = dist
                    best_point = sp
        
        return best_point

    # ==================== Контрольные точки ====================
    
    @abstractmethod
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает список контрольных точек для редактирования примитива.
        
        Returns:
            List[ControlPoint]: Список контрольных точек
        """
        pass
    
    @abstractmethod
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку с заданным индексом.
        
        Args:
            index: Индекс контрольной точки
            new_x, new_y: Новые координаты
            
        Returns:
            True если перемещение успешно, False иначе
        """
        pass
    
    # ==================== Геометрические расчёты ====================
    
    @abstractmethod
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """
        Возвращает ограничивающий прямоугольник примитива.
        
        Returns:
            Tuple (min_x, min_y, max_x, max_y)
        """
        pass
    
    @abstractmethod
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет минимальное расстояние от точки до примитива.
        
        Args:
            x, y: Координаты точки
            
        Returns:
            Расстояние до ближайшей точки на примитиве
        """
        pass
    
    def contains_point(self, x: float, y: float, tolerance: float = 5.0) -> bool:
        """
        Проверяет, находится ли точка на примитиве (в пределах tolerance).
        
        Args:
            x, y: Координаты точки
            tolerance: Допустимое отклонение
            
        Returns:
            True если точка на примитиве
        """
        return self.distance_to_point(x, y) <= tolerance
    
    # ==================== Трансформации ====================
    
    def translate(self, dx: float, dy: float):
        """
        Перемещает примитив на заданное смещение.
        Базовая реализация через перемещение всех контрольных точек.
        """
        control_points = self.get_control_points()
        for cp in control_points:
            self.move_control_point(cp.index, cp.x + dx, cp.y + dy)
