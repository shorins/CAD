import math
from PySide6.QtGui import QPainterPath
from PySide6.QtCore import QPointF

def create_wavy_path(start: QPointF, end: QPointF, amplitude=3.0, period=10.0) -> QPainterPath:
    """
    Генерирует путь синусоиды (волнистой линии) между двумя точками.
    """
    path = QPainterPath()
    path.moveTo(start)
    
    # Вектор линии
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = math.sqrt(dx*dx + dy*dy)
    
    if length < 0.001:
        return path

    # Единичный вектор направления (U) и нормали (N)
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    
    # Рисуем синусоиду
    # period - длина одной волны в пикселях
    steps = int(length)
    # Используем range(1, ...), чтобы начать отрисовку сразу после start
    for i in range(1, steps + 1):
        t = i  # текущее расстояние от начала
        # Формула волны: смещение по нормали = sin(...)
        offset = amplitude * math.sin(2 * math.pi * t / period)
        
        # Координата точки: Начало + Вдоль линии + Смещение вбок
        px = start.x() + ux * t + nx * offset
        py = start.y() + uy * t + ny * offset
        
        path.lineTo(px, py)
        
    # Обязательно соединяем с конечной точкой, чтобы не было разрыва
    path.lineTo(end)
    return path