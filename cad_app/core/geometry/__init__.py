"""
Пакет геометрических примитивов CAD-системы.

Экспортирует все классы примитивов и вспомогательные типы.
"""

# Базовые классы и типы
from .base import (
    GeometricPrimitive,
    SnapType,
    SnapPoint,
    ControlPoint,
)

# Вспомогательные классы
from .point import Point

# Геометрические примитивы
from .line import Line
from .circle import Circle
from .arc import Arc
from .rectangle import Rectangle
from .ellipse import Ellipse
from .polygon import Polygon, PolygonType
from .spline import Spline

# Для удобства импорта всех примитивов одним списком
ALL_PRIMITIVES = [Line, Circle, Arc, Rectangle, Ellipse, Polygon, Spline]

__all__ = [
    # Базовые
    'GeometricPrimitive',
    'SnapType',
    'SnapPoint', 
    'ControlPoint',
    # Вспомогательные
    'Point',
    # Примитивы
    'Line',
    'Circle',
    'Arc',
    'Rectangle',
    'Ellipse',
    'Polygon',
    'PolygonType',
    'Spline',
    # Списки
    'ALL_PRIMITIVES',
]
