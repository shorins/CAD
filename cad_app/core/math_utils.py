import math
from PySide6.QtCore import QPointF

def get_distance_sq(p1: QPointF, p2: QPointF) -> float:
    """Возвращает квадрат расстояния между двумя QPointF."""
    return (p1.x() - p2.x())**2 + (p1.y() - p2.y())**2

def get_distance(p1: QPointF, p2: QPointF) -> float:
    """Возвращает расстояние между двумя QPointF."""
    return math.sqrt(get_distance_sq(p1, p2))

def distance_point_to_segment_sq(p: QPointF, a: QPointF, b: QPointF) -> float:
    """
    Вычисляет квадрат минимального расстояния от точки P до отрезка AB.
    """
    # Длина отрезка в квадрате
    l2 = get_distance_sq(a, b)
    if l2 == 0:
        # A и B - одна и та же точка
        return get_distance_sq(p, a)

    # Проекция точки P на прямую, содержащую отрезок AB
    # t = dot(P-A, B-A) / |B-A|^2
    t = ((p.x() - a.x()) * (b.x() - a.x()) + (p.y() - a.y()) * (b.y() - a.y())) / l2
    
    # Ограничиваем t диапазоном [0, 1], чтобы оставаться в пределах отрезка
    t = max(0, min(1, t))

    # Находим точку проекции
    projection = QPointF(a.x() + t * (b.x() - a.x()),
                         a.y() + t * (b.y() - a.y()))

    # Возвращаем квадрат расстояния от P до проекции
    return get_distance_sq(p, projection)

def cartesian_to_polar(origin: QPointF, point: QPointF) -> tuple[float, float]:
    """
    Конвертирует декартовы координаты в полярные относительно origin.
    Возвращает (r, theta) где theta в радианах.
    """
    dx = point.x() - origin.x()
    dy = point.y() - origin.y()
    r = math.sqrt(dx*dx + dy*dy)
    theta = math.atan2(dy, dx)
    return (r, theta)

def polar_to_cartesian(origin: QPointF, r: float, theta: float) -> QPointF:
    """
    Конвертирует полярные координаты в декартовы относительно origin.
    theta должен быть в радианах.
    """
    x = origin.x() + r * math.cos(theta)
    y = origin.y() + r * math.sin(theta)
    return QPointF(x, y)

def radians_to_degrees(radians: float) -> float:
    """Конвертирует радианы в градусы."""
    return radians * 180.0 / math.pi

def degrees_to_radians(degrees: float) -> float:
    """Конвертирует градусы в радианы."""
    return degrees * math.pi / 180.0

def get_angle_between_points(p1: QPointF, p2: QPointF) -> float:
    """
    Вычисляет угол между двумя точками в радианах.
    Угол измеряется от положительной оси X против часовой стрелки.
    """
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    return math.atan2(dy, dx)