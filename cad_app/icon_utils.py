"""Утилиты для работы с иконками."""

import re
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer


def load_svg_icon(svg_path: str, color: str = "#FFFFFF") -> QIcon:
    """
    Загружает SVG иконку и перекрашивает её в указанный цвет.
    
    Args:
        svg_path: Путь к SVG файлу
        color: Цвет для перекраски (hex формат)
    
    Returns:
        QIcon: Иконка с перекрашенным SVG
    """
    # Читаем SVG файл
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    # Заменяем fill и stroke на нужный цвет
    svg_content = re.sub(r'fill="[^"]*"', '', svg_content)
    svg_content = re.sub(r'stroke="[^"]*"', '', svg_content)
    
    # Добавляем fill к path элементам
    svg_content = svg_content.replace('<path', f'<path fill="{color}"')
    
    # Создаем QPixmap из модифицированного SVG
    renderer = QSvgRenderer(svg_content.encode('utf-8'))
    pixmap = QPixmap(64, 64)  # Размер иконки
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)
