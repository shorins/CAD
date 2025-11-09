"""
Тесты для проверки сетки и панорамирования с учетом rotation.
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


def test_pan_with_rotation():
    """Тест панорамирования с учетом поворота."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест 1: Панорамирование без поворота
    canvas.zoom_factor = 1.0
    canvas.rotation_angle = 0.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Центр экрана должен быть в (0, 0)
    center_before = canvas.map_to_scene(QPointF(400, 300))
    assert abs(center_before.x()) < 0.01
    assert abs(center_before.y()) < 0.01
    
    # Симулируем панорамирование вправо на 100 пикселей используя новую логику
    # (как будто мышь двигается вправо)
    # Это должно сдвинуть камеру влево, чтобы мы видели больше справа
    pan_start = QPointF(400, 300)
    pan_end = QPointF(500, 300)  # Движение вправо на 100 пикселей
    
    scene_pos_before = canvas.map_to_scene(pan_start)
    scene_pos_after = canvas.map_to_scene(pan_end)
    scene_delta = scene_pos_after - scene_pos_before
    canvas.camera_pos -= scene_delta
    
    # После панорамирования вправо, центр экрана должен показывать точку левее (0, 0)
    center_after = canvas.map_to_scene(QPointF(400, 300))
    assert center_after.x() < -90, f"Expected x < -90, got {center_after.x()}"
    
    print("✓ Тест 1 пройден: панорамирование без поворота работает")
    
    # Тест 2: Панорамирование с поворотом на 90°
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Симулируем панорамирование вправо на 100 пикселей используя новую логику
    # При повороте на 90°, движение мыши вправо означает, что мы "тащим" вид вправо,
    # поэтому видим то, что было слева. В сценовых координатах это означает
    # движение вверх (положительный Y)
    pan_start = QPointF(400, 300)
    pan_end = QPointF(500, 300)  # Движение вправо на 100 пикселей
    
    scene_pos_before = canvas.map_to_scene(pan_start)
    scene_pos_after = canvas.map_to_scene(pan_end)
    scene_delta = scene_pos_after - scene_pos_before
    canvas.camera_pos -= scene_delta
    
    # После панорамирования вправо при повороте 90°, 
    # центр экрана должен показывать точку выше (0, 0) в сценовых координатах
    center_after = canvas.map_to_scene(QPointF(400, 300))
    assert center_after.y() > 90, f"Expected y > 90, got {center_after.y()}"
    
    print("✓ Тест 2 пройден: панорамирование с поворотом 90° работает")
    
    # Тест 3: Панорамирование с поворотом на 180°
    canvas.rotation_angle = 180.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Симулируем панорамирование вправо на 100 пикселей используя новую логику
    # При повороте на 180°, движение вправо должно сдвигать камеру вправо
    pan_start = QPointF(400, 300)
    pan_end = QPointF(500, 300)  # Движение вправо на 100 пикселей
    
    scene_pos_before = canvas.map_to_scene(pan_start)
    scene_pos_after = canvas.map_to_scene(pan_end)
    scene_delta = scene_pos_after - scene_pos_before
    canvas.camera_pos -= scene_delta
    
    # После панорамирования вправо при повороте 180°, 
    # центр экрана должен показывать точку правее (0, 0)
    center_after = canvas.map_to_scene(QPointF(400, 300))
    assert center_after.x() > 90, f"Expected x > 90, got {center_after.x()}"
    
    print("✓ Тест 3 пройден: панорамирование с поворотом 180° работает")
    
    print("\n✅ Все тесты панорамирования с rotation пройдены успешно!")


if __name__ == "__main__":
    test_pan_with_rotation()
