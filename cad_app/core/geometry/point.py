"""
Класс точки в двумерном пространстве.
Используется как вспомогательная структура для всех примитивов.
"""

import math
from typing import Tuple


class Point:
    """
    Класс точки в двумерном пространстве.
    Не наследуется от GeometricPrimitive, так как является вспомогательной структурой.
    """
    
    __slots__ = ('x', 'y')  # Оптимизация памяти
    
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def to_dict(self) -> dict:
        """Сериализация в словарь."""
        return {"x": self.x, "y": self.y}

    @staticmethod
    def from_dict(data: dict) -> 'Point':
        """Десериализация из словаря."""
        return Point(data["x"], data["y"])
    
    def to_tuple(self) -> Tuple[float, float]:
        """Возвращает координаты как кортеж."""
        return (self.x, self.y)
    
    def copy(self) -> 'Point':
        """Возвращает копию точки."""
        return Point(self.x, self.y)
    
    # ==================== Математические операции ====================
    
    def distance_to(self, other: 'Point') -> float:
        """Вычисляет расстояние до другой точки."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def midpoint(self, other: 'Point') -> 'Point':
        """Возвращает середину между двумя точками."""
        return Point((self.x + other.x) / 2, (self.y + other.y) / 2)
    
    def angle_to(self, other: 'Point') -> float:
        """Возвращает угол направления на другую точку в радианах (-π, π]."""
        return math.atan2(other.y - self.y, other.x - self.x)
    
    def move_polar(self, distance: float, angle: float) -> 'Point':
        """
        Возвращает новую точку, смещённую на расстояние в заданном направлении.
        
        Args:
            distance: Расстояние
            angle: Угол в радианах
        """
        return Point(
            self.x + distance * math.cos(angle),
            self.y + distance * math.sin(angle)
        )
    
    def rotate_around(self, center: 'Point', angle: float) -> 'Point':
        """
        Поворачивает точку вокруг центра на заданный угол.
        
        Args:
            center: Центр поворота
            angle: Угол в радианах (положительный - против часовой стрелки)
        """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Translate to origin
        dx = self.x - center.x
        dy = self.y - center.y
        
        # Rotate
        new_x = dx * cos_a - dy * sin_a
        new_y = dx * sin_a + dy * cos_a
        
        # Translate back
        return Point(new_x + center.x, new_y + center.y)
    
    # ==================== Операторы ====================
    
    def __add__(self, other: 'Point') -> 'Point':
        """Сложение как векторов."""
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point') -> 'Point':
        """Вычитание как векторов."""
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Point':
        """Умножение на скаляр."""
        return Point(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar: float) -> 'Point':
        """Умножение на скаляр (правое)."""
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: float) -> 'Point':
        """Деление на скаляр."""
        return Point(self.x / scalar, self.y / scalar)
    
    def __neg__(self) -> 'Point':
        """Унарный минус."""
        return Point(-self.x, -self.y)

    def __eq__(self, other) -> bool:
        """Сравнение с допуском на погрешность."""
        if not isinstance(other, Point):
            return False
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)
    
    def __hash__(self) -> int:
        """Хэш для использования в множествах и словарях."""
        return hash((round(self.x, 6), round(self.y, 6)))

    def __repr__(self) -> str:
        return f"Point({self.x:.2f}, {self.y:.2f})"
    
    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f})"
