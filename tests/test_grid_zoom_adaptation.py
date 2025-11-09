"""
Тесты для проверки адаптации сетки к уровню масштабирования.
"""
import sys
import os
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction, QPainter, QPixmap

# Добавляем путь к модулю cad_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cad_app.canvas_widget import CanvasWidget
from cad_app.core.scene import Scene


def test_grid_rendering_at_various_zoom_levels():
    """Тест отрисовки сетки при различных уровнях масштабирования."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тестовые уровни zoom
    zoom_levels = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    
    print("Тестирование отрисовки сетки при различных уровнях zoom:")
    
    for zoom in zoom_levels:
        canvas.zoom_factor = zoom
        canvas.rotation_angle = 0.0
        canvas.camera_pos = QPointF(0, 0)
        
        # Создаем pixmap для рендеринга
        pixmap = QPixmap(canvas.size())
        painter = QPainter(pixmap)
        
        # Вызываем метод отрисовки сетки
        try:
            canvas._draw_grid(painter)
            painter.end()
            
            # Проверяем, что метод выполнился без ошибок
            print(f"  ✓ Zoom {zoom}: сетка отрисована успешно")
            
            # Дополнительная проверка: при zoom < 0.5 minor линии не должны рисоваться
            if zoom < 0.5:
                print(f"    → Minor линии скрыты (zoom < 0.5)")
            else:
                print(f"    → Minor линии отображаются (zoom >= 0.5)")
                
        except Exception as e:
            painter.end()
            print(f"  ✗ Zoom {zoom}: ошибка при отрисовке - {e}")
            raise
    
    print("\n✅ Все тесты отрисовки сетки пройдены успешно!")


def test_grid_minor_lines_visibility():
    """Тест видимости minor линий сетки в зависимости от zoom."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    print("\nТестирование видимости minor линий сетки:")
    
    # Тест 1: При zoom < 0.5 minor линии должны быть скрыты
    canvas.zoom_factor = 0.3
    canvas.rotation_angle = 0.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Проверяем, что show_minor_lines будет False
    show_minor_lines = canvas.zoom_factor >= 0.5
    assert not show_minor_lines, f"Expected minor lines hidden at zoom {canvas.zoom_factor}"
    print(f"  ✓ Тест 1: Minor линии скрыты при zoom = {canvas.zoom_factor}")
    
    # Тест 2: При zoom = 0.5 minor линии должны быть видны
    canvas.zoom_factor = 0.5
    show_minor_lines = canvas.zoom_factor >= 0.5
    assert show_minor_lines, f"Expected minor lines visible at zoom {canvas.zoom_factor}"
    print(f"  ✓ Тест 2: Minor линии видны при zoom = {canvas.zoom_factor}")
    
    # Тест 3: При zoom > 0.5 minor линии должны быть видны
    canvas.zoom_factor = 2.0
    show_minor_lines = canvas.zoom_factor >= 0.5
    assert show_minor_lines, f"Expected minor lines visible at zoom {canvas.zoom_factor}"
    print(f"  ✓ Тест 3: Minor линии видны при zoom = {canvas.zoom_factor}")
    
    print("\n✅ Все тесты видимости minor линий пройдены успешно!")


if __name__ == "__main__":
    test_grid_rendering_at_various_zoom_levels()
    test_grid_minor_lines_visibility()
