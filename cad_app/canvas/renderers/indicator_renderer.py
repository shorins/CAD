"""Indicator renderer module for visual indicators."""

import math
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPointF, QSize


class IndicatorRenderer:
    """Renders visual indicators on the canvas."""
    
    def render_rotation_indicator(self, painter: QPainter, 
                                  rotation_angle: float,
                                  widget_size: QSize) -> None:
        """Отрисовывает визуальный индикатор текущего угла поворота.
        
        Отображается в правом верхнем углу холста.
        
        Элементы индикатора:
        - Круговая диаграмма с отметками 0°, 90°, 180°, 270°
        - Стрелка, указывающая текущий угол поворота
        - Текстовое значение угла
        - Полупрозрачный фон для читаемости
        
        Args:
            painter: QPainter для рисования
            rotation_angle: Текущий угол поворота в градусах
            widget_size: Размер виджета
        """
        # Размеры и позиция индикатора
        indicator_size = 80  # Размер круга индикатора
        margin = 20  # Отступ от края экрана
        center_x = widget_size.width() - margin - indicator_size // 2
        center_y = margin + indicator_size // 2
        center = QPointF(center_x, center_y)
        radius = indicator_size // 2 - 10  # Радиус круга
        
        # Сохраняем состояние painter
        painter.save()
        
        # Рисуем полупрозрачный фон
        bg_color = QColor("#2D2D2D")
        bg_color.setAlphaF(0.8)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, indicator_size // 2, indicator_size // 2)
        
        # Рисуем круг индикатора
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)
        
        # Рисуем отметки для 0°, 90°, 180°, 270°
        tick_angles = [0, 90, 180, 270]
        
        for angle in tick_angles:
            # Конвертируем угол в радианы (0° вверху, по часовой стрелке)
            angle_rad = math.radians(angle - 90)  # -90 чтобы 0° был вверху
            
            # Внешняя точка отметки
            outer_x = center_x + radius * math.cos(angle_rad)
            outer_y = center_y + radius * math.sin(angle_rad)
            
            # Внутренняя точка отметки
            inner_radius = radius - 8
            inner_x = center_x + inner_radius * math.cos(angle_rad)
            inner_y = center_y + inner_radius * math.sin(angle_rad)
            
            # Рисуем отметку
            painter.setPen(QPen(QColor("#AAAAAA"), 2))
            painter.drawLine(QPointF(inner_x, inner_y), QPointF(outer_x, outer_y))
        
        # Рисуем стрелку, указывающую текущий угол поворота
        # Инвертируем направление для соответствия визуальному повороту
        arrow_angle_rad = math.radians(-rotation_angle - 90)
        arrow_length = radius - 5
        arrow_x = center_x + arrow_length * math.cos(arrow_angle_rad)
        arrow_y = center_y + arrow_length * math.sin(arrow_angle_rad)
        
        # Рисуем стрелку
        painter.setPen(QPen(QColor("#7ACC7A"), 3))  # Зеленый цвет как ось X
        painter.drawLine(center, QPointF(arrow_x, arrow_y))
        
        # Рисуем наконечник стрелки
        arrow_head_length = 8
        arrow_head_angle = math.radians(30)  # Угол наконечника
        
        # Левая часть наконечника
        left_angle = arrow_angle_rad + math.pi - arrow_head_angle
        left_x = arrow_x + arrow_head_length * math.cos(left_angle)
        left_y = arrow_y + arrow_head_length * math.sin(left_angle)
        painter.drawLine(QPointF(arrow_x, arrow_y), QPointF(left_x, left_y))
        
        # Правая часть наконечника
        right_angle = arrow_angle_rad + math.pi + arrow_head_angle
        right_x = arrow_x + arrow_head_length * math.cos(right_angle)
        right_y = arrow_y + arrow_head_length * math.sin(right_angle)
        painter.drawLine(QPointF(arrow_x, arrow_y), QPointF(right_x, right_y))
        
        # Рисуем текстовое значение угла в центре
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.setFont(painter.font())
        # Инвертируем угол для отображения (360 - angle)
        display_angle = (360 - int(rotation_angle)) % 360
        text = f"{display_angle}°"
        text_rect = painter.fontMetrics().boundingRect(text)
        text_x = center_x - text_rect.width() // 2
        text_y = center_y + text_rect.height() // 4
        painter.drawText(int(text_x), int(text_y), text)
        
        # Восстанавливаем состояние painter
        painter.restore()
