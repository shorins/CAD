"""Утилиты для работы с иконками."""

import os
import sys
import re
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer


def get_resource_path(relative_path: str) -> str:
    """
    Получает абсолютный путь к ресурсу, работает как в dev, так и в PyInstaller.
    
    Args:
        relative_path: Относительный путь к ресурсу
    
    Returns:
        str: Абсолютный путь к ресурсу
    """
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # В режиме разработки используем текущую директорию
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def load_svg_icon(svg_path: str, color: str = "#FFFFFF") -> QIcon:
    """
    Загружает SVG иконку и перекрашивает её в указанный цвет.
    
    Args:
        svg_path: Путь к SVG файлу (относительный)
        color: Цвет для перекраски (hex формат)
    
    Returns:
        QIcon: Иконка с перекрашенным SVG
    """
    # Получаем абсолютный путь к ресурсу
    absolute_path = get_resource_path(svg_path)
    
    # Читаем SVG файл
    with open(absolute_path, 'r', encoding='utf-8') as f:
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
