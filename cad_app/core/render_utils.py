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


def create_zigzag_path(start: QPointF, end: QPointF, zigzag_height=5.0, zigzag_width=10.0, period=200.0) -> QPainterPath:
    """
    Генерирует путь для 'Сплошной тонкой с изломами' (длинная линия обрыва).
    Рисует прямую линию с периодическими зигзагами.
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
    
    # Если линия короче одного периода, рисуем один зигзаг посередине
    if length < period:
        num_zigzags = 1
        effective_period = length
        start_offset = (length - zigzag_width) / 2
    else:
        num_zigzags = int(length / period)
        # Равномерно распределяем зигзаги
        start_offset = (length - (num_zigzags * period)) / 2 + (period - zigzag_width) / 2

    current_dist = 0.0
    
    # Рисуем сегменты
    # Форма зигзага: Вверх -> Вниз (пересекая ось) -> Вверх (возврат)
    
    path.moveTo(start)
    
    for i in range(num_zigzags):
        # 1. Прямая линия до начала зигзага
        # Определяем центр текущего периода
        if length < period:
             dist_to_zigzag = start_offset
        else:
             dist_to_zigzag = start_offset + i * period
             
        # Рисуем прямую часть до зигзага, если мы еще не там
        if dist_to_zigzag > current_dist:
             px = start.x() + ux * dist_to_zigzag
             py = start.y() + uy * dist_to_zigzag
             path.lineTo(px, py)
             current_dist = dist_to_zigzag
             
        # 2. Рисуем Зигзаг
        # Точка 1: Чуть вперед и ВВЕРХ
        p1_dist = current_dist + zigzag_width * 0.25
        p1x = start.x() + ux * p1_dist + nx * zigzag_height
        p1y = start.y() + uy * p1_dist + ny * zigzag_height
        path.lineTo(p1x, p1y)
        
        # Точка 2: Чуть вперед и ВНИЗ (пересекая ось)
        p2_dist = current_dist + zigzag_width * 0.75
        p2x = start.x() + ux * p2_dist - nx * zigzag_height
        p2y = start.y() + uy * p2_dist - ny * zigzag_height
        path.lineTo(p2x, p2y)
        
        # Точка 3: Возврат на ось
        p3_dist = current_dist + zigzag_width
        p3x = start.x() + ux * p3_dist
        p3y = start.y() + uy * p3_dist
        path.lineTo(p3x, p3y)
        
        current_dist = p3_dist

    # 3. Дорисовываем остаток прямой до конца
    path.lineTo(end)
    
    return path