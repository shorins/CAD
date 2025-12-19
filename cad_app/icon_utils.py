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
    try:
        with open(absolute_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
    except Exception as e:
        print(f"Error loading SVG {svg_path}: {e}")
        return QIcon()
    
    def repl_tag(match):
        tag = match.group(0)
        
        # 1. Обработка fill
        if 'fill="' in tag:
            def repl_fill(m):
                if m.group(1).lower() == 'none':
                    return m.group(0)
                return f'fill="{color}"'
            tag = re.sub(r'fill="([^"]*)"', repl_fill, tag)
        else:
            # Если fill отсутствует, по стандарту SVG он черный.
            # Мы хотим перекрасить в наш цвет, поэтому добавляем атрибут.
            if '/>' in tag:
                tag = tag.replace('/>', f' fill="{color}" />')
            elif '>' in tag:
                tag = tag.replace('>', f' fill="{color}">')

        # 2. Обработка stroke
        if 'stroke="' in tag:
            def repl_stroke(m):
                if m.group(1).lower() == 'none':
                    return m.group(0)
                return f'stroke="{color}"'
            tag = re.sub(r'stroke="([^"]*)"', repl_stroke, tag)
            
        return tag

    # Применяем замену ко всем основным графическим примитивам
    pattern = r'<(path|circle|rect|ellipse|line|polyline|polygon)[^>]*>'
    svg_content = re.sub(pattern, repl_tag, svg_content)
    
    # Создаем QPixmap из модифицированного SVG
    renderer = QSvgRenderer(svg_content.encode('utf-8'))
    pixmap = QPixmap(64, 64)  # Размер иконки
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)
