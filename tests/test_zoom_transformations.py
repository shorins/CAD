"""
Тесты для проверки преобразований координат с учетом zoom.
"""
import sys
import os
import math
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction

# Добавляем путь к модулю cad_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cad_app.canvas_widget import CanvasWidget
from cad_app.core.scene import Scene


def test_coordinate_transformations_with_zoom():
    """Тест преобразований координат с различными zoom_factor."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест 1: zoom = 1.0 (без масштабирования)
    canvas.zoom_factor = 1.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Центр экрана должен соответствовать (0, 0) в сцене
    center_screen = QPointF(400, 300)
    scene_pos = canvas.map_to_scene(center_screen)
    assert abs(scene_pos.x()) < 0.01, f"Expected x=0, got {scene_pos.x()}"
    assert abs(scene_pos.y()) < 0.01, f"Expected y=0, got {scene_pos.y()}"
    
    # Обратное преобразование должно вернуть исходную точку
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - center_screen.x()) < 0.01
    assert abs(back_to_screen.y() - center_screen.y()) < 0.01
    
    print("✓ Тест 1 пройден: zoom=1.0, преобразования обратимы")
    
    # Тест 2: zoom = 2.0 (увеличение)
    canvas.zoom_factor = 2.0
    canvas.camera_pos = QPointF(0, 0)
    
    # При zoom=2.0, точка на расстоянии 100 пикселей от центра
    # должна соответствовать 50 единицам в сцене
    test_screen = QPointF(500, 300)  # 100 пикселей вправо от центра
    scene_pos = canvas.map_to_scene(test_screen)
    expected_x = 50.0  # (500 - 400) / 2.0 = 50
    assert abs(scene_pos.x() - expected_x) < 0.01, f"Expected x={expected_x}, got {scene_pos.x()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - test_screen.x()) < 0.01
    assert abs(back_to_screen.y() - test_screen.y()) < 0.01
    
    print("✓ Тест 2 пройден: zoom=2.0, преобразования корректны")
    
    # Тест 3: zoom = 0.5 (уменьшение)
    canvas.zoom_factor = 0.5
    canvas.camera_pos = QPointF(0, 0)
    
    # При zoom=0.5, точка на расстоянии 100 пикселей от центра
    # должна соответствовать 200 единицам в сцене
    test_screen = QPointF(500, 300)  # 100 пикселей вправо от центра
    scene_pos = canvas.map_to_scene(test_screen)
    expected_x = 200.0  # (500 - 400) / 0.5 = 200
    assert abs(scene_pos.x() - expected_x) < 0.01, f"Expected x={expected_x}, got {scene_pos.x()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - test_screen.x()) < 0.01
    assert abs(back_to_screen.y() - test_screen.y()) < 0.01
    
    print("✓ Тест 3 пройден: zoom=0.5, преобразования корректны")
    
    # Тест 4: zoom с camera offset
    canvas.zoom_factor = 1.0
    canvas.camera_pos = QPointF(100, 50)
    
    center_screen = QPointF(400, 300)
    scene_pos = canvas.map_to_scene(center_screen)
    assert abs(scene_pos.x() - 100) < 0.01, f"Expected x=100, got {scene_pos.x()}"
    assert abs(scene_pos.y() - 50) < 0.01, f"Expected y=50, got {scene_pos.y()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - center_screen.x()) < 0.01
    assert abs(back_to_screen.y() - center_screen.y()) < 0.01
    
    print("✓ Тест 4 пройден: zoom с camera offset, преобразования корректны")
    
    print("\n✅ Все тесты пройдены успешно!")


if __name__ == "__main__":
    test_coordinate_transformations_with_zoom()
