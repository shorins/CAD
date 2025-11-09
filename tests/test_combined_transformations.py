"""
Тесты для проверки комбинированных преобразований координат с zoom и rotation.
Этот файл проверяет требования 3.4 и 3.5 из спецификации.
"""
import sys
import os
import math
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction

# Добавляем путь к модулю cad_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cad_app.canvas_widget import CanvasWidget
from cad_app.core.scene import Scene
from cad_app.core.geometry import Point, Line


def test_inverse_transformations():
    """
    Тест 1: Проверка, что map_to_scene() и map_from_scene() являются обратными операциями
    при различных комбинациях zoom и rotation.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тестовые конфигурации: (zoom, rotation, camera_x, camera_y)
    test_configs = [
        (1.0, 0.0, 0, 0),       # Базовая конфигурация
        (2.0, 0.0, 0, 0),       # Только zoom
        (1.0, 90.0, 0, 0),      # Только rotation
        (2.0, 90.0, 0, 0),      # Zoom + rotation 90°
        (0.5, 180.0, 0, 0),     # Zoom out + rotation 180°
        (1.5, 270.0, 0, 0),     # Zoom + rotation 270°
        (2.0, 45.0, 0, 0),      # Zoom + произвольный угол
        (1.0, 0.0, 100, 50),    # Camera offset
        (2.0, 90.0, 100, 50),   # Все вместе
    ]
    
    # Тестовые точки на экране
    test_points = [
        QPointF(400, 300),  # Центр
        QPointF(0, 0),      # Верхний левый угол
        QPointF(800, 600),  # Нижний правый угол
        QPointF(500, 300),  # Справа от центра
        QPointF(400, 200),  # Выше центра
    ]
    
    for zoom, rotation, cam_x, cam_y in test_configs:
        canvas.zoom_factor = zoom
        canvas.rotation_angle = rotation
        canvas.camera_pos = QPointF(cam_x, cam_y)
        
        for screen_point in test_points:
            # Screen -> Scene -> Screen
            scene_point = canvas.map_to_scene(screen_point)
            back_to_screen = canvas.map_from_scene(scene_point)
            
            # Проверяем, что вернулись к исходной точке
            dx = abs(back_to_screen.x() - screen_point.x())
            dy = abs(back_to_screen.y() - screen_point.y())
            
            assert dx < 0.01, (
                f"X mismatch: zoom={zoom}, rot={rotation}, cam=({cam_x},{cam_y}), "
                f"screen={screen_point}, dx={dx}"
            )
            assert dy < 0.01, (
                f"Y mismatch: zoom={zoom}, rot={rotation}, cam=({cam_x},{cam_y}), "
                f"screen={screen_point}, dy={dy}"
            )
    
    print("✓ Тест 1 пройден: map_to_scene() и map_from_scene() являются обратными операциями")


def test_line_drawing_with_zoom():
    """
    Тест 2: Проверка, что рисование линий работает корректно с примененным zoom.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест с zoom = 2.0
    canvas.zoom_factor = 2.0
    canvas.rotation_angle = 0.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Симулируем рисование линии от центра экрана вправо на 100 пикселей
    start_screen = QPointF(400, 300)
    end_screen = QPointF(500, 300)
    
    # Преобразуем в сценовые координаты
    start_scene = canvas.map_to_scene(start_screen)
    end_scene = canvas.map_to_scene(end_screen)
    
    # Создаем линию
    line = Line(
        Point(start_scene.x(), start_scene.y()),
        Point(end_scene.x(), end_scene.y())
    )
    scene.add_object(line)
    
    # Проверяем, что линия имеет правильную длину в сценовых координатах
    # При zoom=2.0, 100 пикселей = 50 единиц в сцене
    expected_length = 50.0
    actual_length = math.sqrt(
        (line.end.x - line.start.x)**2 + (line.end.y - line.start.y)**2
    )
    
    assert abs(actual_length - expected_length) < 0.01, (
        f"Expected length={expected_length}, got {actual_length}"
    )
    
    # Проверяем, что при преобразовании обратно в экранные координаты
    # линия отображается в правильном месте
    start_back = canvas.map_from_scene(QPointF(line.start.x, line.start.y))
    end_back = canvas.map_from_scene(QPointF(line.end.x, line.end.y))
    
    assert abs(start_back.x() - start_screen.x()) < 0.01
    assert abs(start_back.y() - start_screen.y()) < 0.01
    assert abs(end_back.x() - end_screen.x()) < 0.01
    assert abs(end_back.y() - end_screen.y()) < 0.01
    
    print("✓ Тест 2 пройден: рисование линий работает корректно с zoom")


def test_line_drawing_with_rotation():
    """
    Тест 3: Проверка, что рисование линий работает корректно с примененным rotation.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест с rotation = 90°
    canvas.zoom_factor = 1.0
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Симулируем рисование линии от центра экрана вправо на 100 пикселей
    start_screen = QPointF(400, 300)
    end_screen = QPointF(500, 300)
    
    # Преобразуем в сценовые координаты
    start_scene = canvas.map_to_scene(start_screen)
    end_scene = canvas.map_to_scene(end_screen)
    
    # При повороте на 90°, движение вправо на экране соответствует движению вниз в сцене
    # Проверяем, что Y координата уменьшилась (движение вниз)
    assert end_scene.y() < start_scene.y(), (
        f"Expected end_y < start_y, got start_y={start_scene.y()}, end_y={end_scene.y()}"
    )
    
    # Проверяем, что X координата осталась примерно той же
    assert abs(end_scene.x() - start_scene.x()) < 0.01, (
        f"Expected x to stay same, got start_x={start_scene.x()}, end_x={end_scene.x()}"
    )
    
    # Создаем линию
    line = Line(
        Point(start_scene.x(), start_scene.y()),
        Point(end_scene.x(), end_scene.y())
    )
    scene.add_object(line)
    
    # Проверяем, что линия имеет правильную длину в сценовых координатах
    expected_length = 100.0
    actual_length = math.sqrt(
        (line.end.x - line.start.x)**2 + (line.end.y - line.start.y)**2
    )
    
    assert abs(actual_length - expected_length) < 0.01, (
        f"Expected length={expected_length}, got {actual_length}"
    )
    
    print("✓ Тест 3 пройден: рисование линий работает корректно с rotation")


def test_line_drawing_with_zoom_and_rotation():
    """
    Тест 4: Проверка, что рисование линий работает корректно с одновременным
    применением zoom и rotation.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест с zoom = 2.0 и rotation = 90°
    canvas.zoom_factor = 2.0
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Симулируем рисование линии от центра экрана вправо на 100 пикселей
    start_screen = QPointF(400, 300)
    end_screen = QPointF(500, 300)
    
    # Преобразуем в сценовые координаты
    start_scene = canvas.map_to_scene(start_screen)
    end_scene = canvas.map_to_scene(end_screen)
    
    # Создаем линию
    line = Line(
        Point(start_scene.x(), start_scene.y()),
        Point(end_scene.x(), end_scene.y())
    )
    scene.add_object(line)
    
    # Проверяем, что линия имеет правильную длину в сценовых координатах
    # При zoom=2.0, 100 пикселей = 50 единиц в сцене
    expected_length = 50.0
    actual_length = math.sqrt(
        (line.end.x - line.start.x)**2 + (line.end.y - line.start.y)**2
    )
    
    assert abs(actual_length - expected_length) < 0.01, (
        f"Expected length={expected_length}, got {actual_length}"
    )
    
    # Проверяем, что при преобразовании обратно в экранные координаты
    # линия отображается в правильном месте
    start_back = canvas.map_from_scene(QPointF(line.start.x, line.start.y))
    end_back = canvas.map_from_scene(QPointF(line.end.x, line.end.y))
    
    assert abs(start_back.x() - start_screen.x()) < 0.01
    assert abs(start_back.y() - start_screen.y()) < 0.01
    assert abs(end_back.x() - end_screen.x()) < 0.01
    assert abs(end_back.y() - end_screen.y()) < 0.01
    
    # Тест с другой комбинацией: zoom = 0.5 и rotation = 180°
    canvas.zoom_factor = 0.5
    canvas.rotation_angle = 180.0
    canvas.camera_pos = QPointF(0, 0)
    scene.objects.clear()
    
    # Симулируем рисование линии
    start_screen = QPointF(400, 300)
    end_screen = QPointF(500, 300)
    
    start_scene = canvas.map_to_scene(start_screen)
    end_scene = canvas.map_to_scene(end_screen)
    
    line = Line(
        Point(start_scene.x(), start_scene.y()),
        Point(end_scene.x(), end_scene.y())
    )
    scene.add_object(line)
    
    # При zoom=0.5, 100 пикселей = 200 единиц в сцене
    expected_length = 200.0
    actual_length = math.sqrt(
        (line.end.x - line.start.x)**2 + (line.end.y - line.start.y)**2
    )
    
    assert abs(actual_length - expected_length) < 0.01, (
        f"Expected length={expected_length}, got {actual_length}"
    )
    
    print("✓ Тест 4 пройден: рисование линий работает корректно с zoom и rotation")


def test_object_selection_with_zoom_and_rotation():
    """
    Тест 5: Проверка, что выделение объектов работает корректно с примененными
    zoom и rotation.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Создаем линию в сцене
    line = Line(Point(0, 0), Point(100, 0))
    scene.add_object(line)
    
    # Тест 1: Выделение с zoom = 2.0
    canvas.zoom_factor = 2.0
    canvas.rotation_angle = 0.0
    canvas.camera_pos = QPointF(50, 0)  # Центрируем на середине линии
    
    # Точка на экране, которая должна быть рядом с линией
    # Центр экрана (400, 300) должен соответствовать (50, 0) в сцене (середина линии)
    test_screen_point = QPointF(400, 300)
    scene_point = canvas.map_to_scene(test_screen_point)
    
    # Проверяем, что мы действительно около линии
    assert abs(scene_point.x() - 50) < 1.0
    assert abs(scene_point.y()) < 1.0
    
    # Симулируем поиск ближайшей линии
    canvas._find_nearest_line(test_screen_point)
    
    # Линия должна быть выделена
    assert canvas.highlighted_line == line, "Line should be highlighted with zoom"
    
    # Тест 2: Выделение с rotation = 90°
    canvas.zoom_factor = 1.0
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(50, 0)
    canvas.highlighted_line = None
    
    # При повороте на 90°, линия (0,0)-(100,0) будет отображаться вертикально
    # Центр экрана должен быть около середины линии
    test_screen_point = QPointF(400, 300)
    scene_point = canvas.map_to_scene(test_screen_point)
    
    # Симулируем поиск ближайшей линии
    canvas._find_nearest_line(test_screen_point)
    
    # Линия должна быть выделена
    assert canvas.highlighted_line == line, "Line should be highlighted with rotation"
    
    # Тест 3: Выделение с zoom и rotation
    canvas.zoom_factor = 2.0
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(50, 0)
    canvas.highlighted_line = None
    
    test_screen_point = QPointF(400, 300)
    canvas._find_nearest_line(test_screen_point)
    
    # Линия должна быть выделена
    assert canvas.highlighted_line == line, "Line should be highlighted with zoom and rotation"
    
    print("✓ Тест 5 пройден: выделение объектов работает корректно с zoom и rotation")


def test_pan_with_zoom_and_rotation():
    """
    Тест 6: Проверка, что панорамирование работает корректно с примененными
    zoom и rotation.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест 1: Панорамирование с zoom = 2.0
    canvas.zoom_factor = 2.0
    canvas.rotation_angle = 0.0
    canvas.camera_pos = QPointF(0, 0)
    
    # Запоминаем, что видно в центре экрана
    center_before = canvas.map_to_scene(QPointF(400, 300))
    
    # Симулируем панорамирование вправо на 100 пикселей
    pan_start = QPointF(400, 300)
    pan_end = QPointF(500, 300)
    
    scene_pos_before = canvas.map_to_scene(pan_start)
    scene_pos_after = canvas.map_to_scene(pan_end)
    scene_delta = scene_pos_after - scene_pos_before
    canvas.camera_pos -= scene_delta
    
    # После панорамирования, центр экрана должен показывать другую точку
    center_after = canvas.map_to_scene(QPointF(400, 300))
    
    # При zoom=2.0, движение на 100 пикселей = 50 единиц в сцене
    # Панорамирование вправо должно сдвинуть камеру влево
    assert center_after.x() < center_before.x() - 40, (
        f"Expected camera to move left, before={center_before.x()}, after={center_after.x()}"
    )
    
    # Тест 2: Панорамирование с rotation = 90°
    canvas.zoom_factor = 1.0
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(0, 0)
    
    center_before = canvas.map_to_scene(QPointF(400, 300))
    
    # Симулируем панорамирование вправо на 100 пикселей
    pan_start = QPointF(400, 300)
    pan_end = QPointF(500, 300)
    
    scene_pos_before = canvas.map_to_scene(pan_start)
    scene_pos_after = canvas.map_to_scene(pan_end)
    scene_delta = scene_pos_after - scene_pos_before
    canvas.camera_pos -= scene_delta
    
    center_after = canvas.map_to_scene(QPointF(400, 300))
    
    # При повороте на 90°, движение вправо на экране соответствует движению вниз в сцене
    # Панорамирование должно сдвинуть камеру вверх (положительный Y)
    assert center_after.y() > center_before.y() + 90, (
        f"Expected camera to move up, before={center_before.y()}, after={center_after.y()}"
    )
    
    # Тест 3: Панорамирование с zoom = 2.0 и rotation = 90°
    canvas.zoom_factor = 2.0
    canvas.rotation_angle = 90.0
    canvas.camera_pos = QPointF(0, 0)
    
    center_before = canvas.map_to_scene(QPointF(400, 300))
    
    # Симулируем панорамирование вправо на 100 пикселей
    pan_start = QPointF(400, 300)
    pan_end = QPointF(500, 300)
    
    scene_pos_before = canvas.map_to_scene(pan_start)
    scene_pos_after = canvas.map_to_scene(pan_end)
    scene_delta = scene_pos_after - scene_pos_before
    canvas.camera_pos -= scene_delta
    
    center_after = canvas.map_to_scene(QPointF(400, 300))
    
    # При zoom=2.0 и rotation=90°, движение на 100 пикселей = 50 единиц в сцене
    # и направление вверх (положительный Y)
    assert center_after.y() > center_before.y() + 40, (
        f"Expected camera to move up, before={center_before.y()}, after={center_after.y()}"
    )
    
    print("✓ Тест 6 пройден: панорамирование работает корректно с zoom и rotation")


def run_all_tests():
    """Запускает все тесты."""
    print("=" * 70)
    print("Запуск тестов комбинированных преобразований (zoom + rotation)")
    print("=" * 70)
    print()
    
    test_inverse_transformations()
    test_line_drawing_with_zoom()
    test_line_drawing_with_rotation()
    test_line_drawing_with_zoom_and_rotation()
    test_object_selection_with_zoom_and_rotation()
    test_pan_with_zoom_and_rotation()
    
    print()
    print("=" * 70)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
