"""
Тесты для функциональности zoom to fit.
"""
import sys
import math
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from PySide6.QtGui import QAction

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cad_app.core.scene import Scene
from cad_app.core.geometry import Point, Line
from cad_app.canvas_widget import CanvasWidget

# Создаем QApplication один раз для всех тестов
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


def test_calculate_scene_bounds_empty():
    """Тест вычисления границ для пустой сцены."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    
    bounds = canvas._calculate_scene_bounds()
    assert bounds is None, "Границы пустой сцены должны быть None"
    print("✓ test_calculate_scene_bounds_empty passed")


def test_calculate_scene_bounds_single_line():
    """Тест вычисления границ для одной линии."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    
    # Добавляем линию от (0, 0) до (10, 10)
    line = Line(Point(0, 0), Point(10, 10))
    scene.add_object(line)
    
    bounds = canvas._calculate_scene_bounds()
    assert bounds is not None, "Границы должны быть определены"
    
    min_point, max_point = bounds
    assert min_point.x() == 0, f"min_x должен быть 0, получен {min_point.x()}"
    assert min_point.y() == 0, f"min_y должен быть 0, получен {min_point.y()}"
    assert max_point.x() == 10, f"max_x должен быть 10, получен {max_point.x()}"
    assert max_point.y() == 10, f"max_y должен быть 10, получен {max_point.y()}"
    print("✓ test_calculate_scene_bounds_single_line passed")


def test_calculate_scene_bounds_multiple_lines():
    """Тест вычисления границ для нескольких линий."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    
    # Добавляем несколько линий
    line1 = Line(Point(-5, -5), Point(5, 5))
    line2 = Line(Point(10, 0), Point(20, 10))
    line3 = Line(Point(0, -10), Point(0, 0))
    
    scene.add_object(line1)
    scene.add_object(line2)
    scene.add_object(line3)
    
    bounds = canvas._calculate_scene_bounds()
    assert bounds is not None, "Границы должны быть определены"
    
    min_point, max_point = bounds
    assert min_point.x() == -5, f"min_x должен быть -5, получен {min_point.x()}"
    assert min_point.y() == -10, f"min_y должен быть -10, получен {min_point.y()}"
    assert max_point.x() == 20, f"max_x должен быть 20, получен {max_point.x()}"
    assert max_point.y() == 10, f"max_y должен быть 10, получен {max_point.y()}"
    print("✓ test_calculate_scene_bounds_multiple_lines passed")


def test_zoom_to_fit_empty_scene():
    """Тест zoom to fit для пустой сцены."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Вызываем zoom_to_fit для пустой сцены
    canvas.zoom_to_fit()
    
    # Проверяем, что zoom сброшен к 1.0
    assert canvas.target_zoom_factor == 1.0, f"target_zoom_factor должен быть 1.0, получен {canvas.target_zoom_factor}"
    print("✓ test_zoom_to_fit_empty_scene passed")


def test_zoom_to_fit_single_line():
    """Тест zoom to fit для одной линии."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Добавляем линию от (0, 0) до (100, 100)
    line = Line(Point(0, 0), Point(100, 100))
    scene.add_object(line)
    
    # Вызываем zoom_to_fit
    canvas.zoom_to_fit()
    
    # Проверяем, что zoom был установлен (не равен 1.0)
    # и камера центрирована на центре линии
    assert canvas.target_zoom_factor > 0, "target_zoom_factor должен быть положительным"
    
    # Центр линии должен быть в (50, 50)
    expected_center_x = 50.0
    expected_center_y = 50.0
    assert abs(canvas.camera_pos.x() - expected_center_x) < 0.1, \
        f"camera_pos.x должен быть ~{expected_center_x}, получен {canvas.camera_pos.x()}"
    assert abs(canvas.camera_pos.y() - expected_center_y) < 0.1, \
        f"camera_pos.y должен быть ~{expected_center_y}, получен {canvas.camera_pos.y()}"
    print("✓ test_zoom_to_fit_single_line passed")


def test_zoom_to_fit_multiple_lines():
    """Тест zoom to fit для нескольких линий."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Добавляем несколько линий
    line1 = Line(Point(-50, -50), Point(50, 50))
    line2 = Line(Point(100, 0), Point(200, 100))
    
    scene.add_object(line1)
    scene.add_object(line2)
    
    # Вызываем zoom_to_fit
    canvas.zoom_to_fit()
    
    # Проверяем, что zoom был установлен
    assert canvas.target_zoom_factor > 0, "target_zoom_factor должен быть положительным"
    
    # Центр должен быть между всеми линиями
    # min: (-50, -50), max: (200, 100)
    # center: (75, 25)
    expected_center_x = 75.0
    expected_center_y = 25.0
    assert abs(canvas.camera_pos.x() - expected_center_x) < 0.1, \
        f"camera_pos.x должен быть ~{expected_center_x}, получен {canvas.camera_pos.x()}"
    assert abs(canvas.camera_pos.y() - expected_center_y) < 0.1, \
        f"camera_pos.y должен быть ~{expected_center_y}, получен {canvas.camera_pos.y()}"
    print("✓ test_zoom_to_fit_multiple_lines passed")


def test_zoom_to_fit_with_rotation_0():
    """Тест zoom to fit с поворотом 0° (без поворота)."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Добавляем горизонтальную линию
    line = Line(Point(0, 0), Point(100, 0))
    scene.add_object(line)
    
    # Устанавливаем поворот 0°
    canvas.rotation_angle = 0.0
    
    # Вызываем zoom_to_fit
    canvas.zoom_to_fit()
    
    # Сохраняем zoom для сравнения
    zoom_0 = canvas.target_zoom_factor
    
    # Проверяем, что zoom был установлен
    assert zoom_0 > 0, "target_zoom_factor должен быть положительным"
    print(f"✓ test_zoom_to_fit_with_rotation_0 passed (zoom={zoom_0:.2f})")


def test_zoom_to_fit_with_rotation_90():
    """Тест zoom to fit с поворотом 90°."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Добавляем горизонтальную линию
    line = Line(Point(0, 0), Point(100, 0))
    scene.add_object(line)
    
    # Устанавливаем поворот 90°
    canvas.rotation_angle = 90.0
    
    # Вызываем zoom_to_fit
    canvas.zoom_to_fit()
    
    # Сохраняем zoom для сравнения
    zoom_90 = canvas.target_zoom_factor
    
    # Проверяем, что zoom был установлен
    assert zoom_90 > 0, "target_zoom_factor должен быть положительным"
    
    # При повороте на 90° горизонтальная линия становится вертикальной
    # Поэтому zoom должен учитывать высоту экрана вместо ширины
    print(f"✓ test_zoom_to_fit_with_rotation_90 passed (zoom={zoom_90:.2f})")


def test_zoom_to_fit_with_rotation_180():
    """Тест zoom to fit с поворотом 180°."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Добавляем горизонтальную линию
    line = Line(Point(0, 0), Point(100, 0))
    scene.add_object(line)
    
    # Устанавливаем поворот 180°
    canvas.rotation_angle = 180.0
    
    # Вызываем zoom_to_fit
    canvas.zoom_to_fit()
    
    # Сохраняем zoom для сравнения
    zoom_180 = canvas.target_zoom_factor
    
    # Проверяем, что zoom был установлен
    assert zoom_180 > 0, "target_zoom_factor должен быть положительным"
    
    # При повороте на 180° размеры экрана не меняются (как при 0°)
    print(f"✓ test_zoom_to_fit_with_rotation_180 passed (zoom={zoom_180:.2f})")


def test_zoom_to_fit_with_rotation_270():
    """Тест zoom to fit с поворотом 270°."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Добавляем горизонтальную линию
    line = Line(Point(0, 0), Point(100, 0))
    scene.add_object(line)
    
    # Устанавливаем поворот 270°
    canvas.rotation_angle = 270.0
    
    # Вызываем zoom_to_fit
    canvas.zoom_to_fit()
    
    # Сохраняем zoom для сравнения
    zoom_270 = canvas.target_zoom_factor
    
    # Проверяем, что zoom был установлен
    assert zoom_270 > 0, "target_zoom_factor должен быть положительным"
    
    # При повороте на 270° горизонтальная линия становится вертикальной (как при 90°)
    print(f"✓ test_zoom_to_fit_with_rotation_270 passed (zoom={zoom_270:.2f})")


def test_zoom_to_fit_rotation_consistency():
    """Тест согласованности zoom to fit при разных поворотах."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Добавляем квадратную область (линии образуют квадрат)
    line1 = Line(Point(0, 0), Point(100, 0))
    line2 = Line(Point(100, 0), Point(100, 100))
    line3 = Line(Point(100, 100), Point(0, 100))
    line4 = Line(Point(0, 100), Point(0, 0))
    
    scene.add_object(line1)
    scene.add_object(line2)
    scene.add_object(line3)
    scene.add_object(line4)
    
    # Тестируем zoom для квадрата при разных поворотах
    zooms = {}
    for angle in [0, 90, 180, 270]:
        canvas.rotation_angle = float(angle)
        canvas.zoom_to_fit()
        zooms[angle] = canvas.target_zoom_factor
    
    # Для квадрата zoom должен быть примерно одинаковым при всех поворотах
    # (с небольшой погрешностью из-за округления)
    zoom_values = list(zooms.values())
    max_zoom = max(zoom_values)
    min_zoom = min(zoom_values)
    
    # Разница не должна превышать 10%
    tolerance = 0.1
    assert (max_zoom - min_zoom) / max_zoom < tolerance, \
        f"Zoom для квадрата должен быть примерно одинаковым при всех поворотах: {zooms}"
    
    print(f"✓ test_zoom_to_fit_rotation_consistency passed (zooms={zooms})")


def test_zoom_to_fit_rotation_effective_dimensions():
    """Тест эффективных размеров экрана при повороте."""
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)  # Ширина > Высота
    
    # Добавляем горизонтальную линию (длинная по X)
    line = Line(Point(0, 0), Point(200, 0))
    scene.add_object(line)
    
    # Тест 1: При 0° горизонтальная линия использует ширину экрана
    canvas.rotation_angle = 0.0
    canvas.zoom_to_fit()
    zoom_0 = canvas.target_zoom_factor
    
    # Тест 2: При 90° горизонтальная линия становится вертикальной и использует высоту экрана
    canvas.rotation_angle = 90.0
    canvas.zoom_to_fit()
    zoom_90 = canvas.target_zoom_factor
    
    # При повороте на 90° zoom должен быть меньше (т.к. высота < ширины)
    # Это означает, что алгоритм правильно учитывает поворот
    assert zoom_90 < zoom_0, \
        f"При повороте на 90° zoom должен быть меньше для горизонтальной линии: zoom_0={zoom_0:.2f}, zoom_90={zoom_90:.2f}"
    
    print(f"✓ test_zoom_to_fit_rotation_effective_dimensions passed (zoom_0={zoom_0:.2f}, zoom_90={zoom_90:.2f})")


if __name__ == "__main__":
    print("Запуск тестов zoom to fit...")
    print()
    
    # Базовые тесты
    test_calculate_scene_bounds_empty()
    test_calculate_scene_bounds_single_line()
    test_calculate_scene_bounds_multiple_lines()
    test_zoom_to_fit_empty_scene()
    test_zoom_to_fit_single_line()
    test_zoom_to_fit_multiple_lines()
    
    print()
    print("Тесты с поворотом вида:")
    print()
    
    # Тесты с поворотом
    test_zoom_to_fit_with_rotation_0()
    test_zoom_to_fit_with_rotation_90()
    test_zoom_to_fit_with_rotation_180()
    test_zoom_to_fit_with_rotation_270()
    test_zoom_to_fit_rotation_consistency()
    test_zoom_to_fit_rotation_effective_dimensions()
    
    print()
    print("Все тесты пройдены успешно! ✓")
