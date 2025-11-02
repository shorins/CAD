from PySide6.QtCore import QPointF

def get_distance_sq(p1: QPointF, p2: QPointF) -> float:
    """Возвращает квадрат расстояния между двумя QPointF."""
    return (p1.x() - p2.x())**2 + (p1.y() - p2.y())**2

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