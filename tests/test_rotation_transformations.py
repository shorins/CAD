"""
Тесты для проверки преобразований координат с учетом rotation.
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


def test_rotation_transformations():
    """Тест преобразований координат с различными углами поворота."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест 1: rotation = 0° (без поворота)
    canvas.zoom_factor = 1.0
    canvas.rotation_angle = 0.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Точка справа от центра
    test_screen = QPointF(500, 300)  # 100 пикселей вправо от центра
    scene_pos = canvas.map_to_scene(test_screen)
    assert abs(scene_pos.x() - 100) < 0.01, f"Expected x=100, got {scene_pos.x()}"
    assert abs(scene_pos.y()) < 0.01, f"Expected y=0, got {scene_pos.y()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - test_screen.x()) < 0.01
    assert abs(back_to_screen.y() - test_screen.y()) < 0.01
    
    print("✓ Тест 1 пройден: rotation=0°, преобразования обратимы")
    
    # Тест 2: rotation = 90° (поворот по часовой стрелке)
    canvas.rotation_angle = 90.0
    
    # При повороте на 90° по часовой стрелке:
    # Точка справа от центра экрана должна соответствовать точке внизу в сцене
    test_screen = QPointF(500, 300)  # 100 пикселей вправо от центра
    scene_pos = canvas.map_to_scene(test_screen)
    # После поворота на 90°: (100, 0) -> (0, -100)
    assert abs(scene_pos.x()) < 0.01, f"Expected x=0, got {scene_pos.x()}"
    assert abs(scene_pos.y() - (-100)) < 0.01, f"Expected y=-100, got {scene_pos.y()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - test_screen.x()) < 0.01
    assert abs(back_to_screen.y() - test_screen.y()) < 0.01
    
    print("✓ Тест 2 пройден: rotation=90°, преобразования корректны")
    
    # Тест 3: rotation = 180°
    canvas.rotation_angle = 180.0
    
    # При повороте на 180°:
    # Точка справа от центра экрана должна соответствовать точке слева в сцене
    test_screen = QPointF(500, 300)  # 100 пикселей вправо от центра
    scene_pos = canvas.map_to_scene(test_screen)
    # После поворота на 180°: (100, 0) -> (-100, 0)
    assert abs(scene_pos.x() - (-100)) < 0.01, f"Expected x=-100, got {scene_pos.x()}"
    assert abs(scene_pos.y()) < 0.01, f"Expected y=0, got {scene_pos.y()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - test_screen.x()) < 0.01
    assert abs(back_to_screen.y() - test_screen.y()) < 0.01
    
    print("✓ Тест 3 пройден: rotation=180°, преобразования корректны")
    
    # Тест 4: rotation = 270°
    canvas.rotation_angle = 270.0
    
    # При повороте на 270°:
    # Точка справа от центра экрана должна соответствовать точке вверху в сцене
    test_screen = QPointF(500, 300)  # 100 пикселей вправо от центра
    scene_pos = canvas.map_to_scene(test_screen)
    # После поворота на 270°: (100, 0) -> (0, 100)
    assert abs(scene_pos.x()) < 0.01, f"Expected x=0, got {scene_pos.x()}"
    assert abs(scene_pos.y() - 100) < 0.01, f"Expected y=100, got {scene_pos.y()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - test_screen.x()) < 0.01
    assert abs(back_to_screen.y() - test_screen.y()) < 0.01
    
    print("✓ Тест 4 пройден: rotation=270°, преобразования корректны")
    
    # Тест 5: 4 поворота на 90° должны вернуть к исходному состоянию
    canvas.rotation_angle = 0.0
    for i in range(4):
        canvas._apply_rotation(clockwise=True)
    
    assert abs(canvas.rotation_angle) < 0.01, f"Expected angle=0, got {canvas.rotation_angle}"
    print("✓ Тест 5 пройден: 4 поворота на 90° возвращают к исходному состоянию")
    
    # Тест 6: Комбинация zoom и rotation
    canvas.zoom_factor = 2.0
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(0, 0)
    
    test_screen = QPointF(500, 300)  # 100 пикселей вправо от центра
    scene_pos = canvas.map_to_scene(test_screen)
    # С zoom=2.0: 100 пикселей = 50 единиц
    # После поворота на 90°: (50, 0) -> (0, -50)
    assert abs(scene_pos.x()) < 0.01, f"Expected x=0, got {scene_pos.x()}"
    assert abs(scene_pos.y() - (-50)) < 0.01, f"Expected y=-50, got {scene_pos.y()}"
    
    # Обратное преобразование
    back_to_screen = canvas.map_from_scene(scene_pos)
    assert abs(back_to_screen.x() - test_screen.x()) < 0.01
    assert abs(back_to_screen.y() - test_screen.y()) < 0.01
    
    print("✓ Тест 6 пройден: комбинация zoom и rotation работает корректно")
    
    print("\n✅ Все тесты rotation пройдены успешно!")


if __name__ == "__main__":
    test_rotation_transformations()
