"""
Тесты для проверки плавной анимации поворота.
"""
import sys
import os
import time
from PySide6.QtCore import QPointF, QTime
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest

# Добавляем путь к модулю cad_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cad_app.canvas_widget import CanvasWidget
from cad_app.core.scene import Scene


def test_rotation_animation():
    """Тест плавной анимации поворота."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    scene = Scene()
    line_action = QAction()
    delete_action = QAction()
    canvas = CanvasWidget(scene, line_action, delete_action)
    canvas.resize(800, 600)
    
    # Тест 1: Проверка начального состояния
    assert canvas.rotation_angle == 0.0, "Начальный угол должен быть 0"
    assert canvas.is_rotating == False, "Анимация не должна быть активна"
    assert canvas.target_rotation_angle == 0.0, "Целевой угол должен быть 0"
    print("✓ Тест 1 пройден: начальное состояние корректно")
    
    # Тест 2: Запуск анимации поворота по часовой стрелке
    canvas._apply_rotation(clockwise=True)
    assert canvas.is_rotating == True, "Анимация должна быть активна"
    assert canvas.target_rotation_angle == 90.0, f"Целевой угол должен быть 90, получен {canvas.target_rotation_angle}"
    assert canvas.rotation_animation_start_angle == 0.0, "Начальный угол анимации должен быть 0"
    assert canvas.rotation_animation_timer.isActive(), "Таймер анимации должен быть активен"
    print("✓ Тест 2 пройден: анимация запущена корректно")
    
    # Тест 3: Проверка блокировки новых команд во время анимации
    initial_target = canvas.target_rotation_angle
    canvas._apply_rotation(clockwise=False)  # Попытка повернуть в другую сторону
    assert canvas.target_rotation_angle == initial_target, "Целевой угол не должен измениться во время анимации"
    print("✓ Тест 3 пройден: новые команды блокируются во время анимации")
    
    # Тест 4: Ожидание завершения анимации и проверка финального состояния
    # Ждем немного больше, чем длительность анимации (50ms)
    QTest.qWait(100)
    
    assert canvas.is_rotating == False, "Анимация должна завершиться"
    assert abs(canvas.rotation_angle - 90.0) < 0.01, f"Финальный угол должен быть 90, получен {canvas.rotation_angle}"
    assert not canvas.rotation_animation_timer.isActive(), "Таймер анимации должен остановиться"
    print("✓ Тест 4 пройден: анимация завершается корректно")
    
    # Тест 5: Проверка последовательных поворотов
    canvas._apply_rotation(clockwise=True)  # 90 -> 180
    QTest.qWait(100)
    assert abs(canvas.rotation_angle - 180.0) < 0.01, f"Угол должен быть 180, получен {canvas.rotation_angle}"
    
    canvas._apply_rotation(clockwise=True)  # 180 -> 270
    QTest.qWait(100)
    assert abs(canvas.rotation_angle - 270.0) < 0.01, f"Угол должен быть 270, получен {canvas.rotation_angle}"
    
    canvas._apply_rotation(clockwise=True)  # 270 -> 360 (0)
    QTest.qWait(100)
    assert abs(canvas.rotation_angle) < 0.01 or abs(canvas.rotation_angle - 360.0) < 0.01, \
        f"Угол должен быть 0 или 360, получен {canvas.rotation_angle}"
    print("✓ Тест 5 пройден: последовательные повороты работают корректно")
    
    # Тест 6: Проверка поворота против часовой стрелки
    canvas.rotation_angle = 0.0
    canvas.target_rotation_angle = 0.0
    canvas.is_rotating = False
    
    canvas._apply_rotation(clockwise=False)  # 0 -> 270 (или -90)
    QTest.qWait(100)
    assert abs(canvas.rotation_angle - 270.0) < 0.01, f"Угол должен быть 270, получен {canvas.rotation_angle}"
    print("✓ Тест 6 пройден: поворот против часовой стрелки работает корректно")
    
    # Тест 7: Проверка кратчайшего пути (350° -> 10° должен идти через 0°)
    canvas.rotation_angle = 350.0
    canvas.target_rotation_angle = 350.0
    canvas.is_rotating = False
    
    # Устанавливаем целевой угол напрямую для теста
    canvas.rotation_animation_start_angle = 350.0
    canvas.target_rotation_angle = 10.0
    canvas.is_rotating = True
    canvas.rotation_animation_start_time = QTime.currentTime().msecsSinceStartOfDay()
    canvas.rotation_animation_timer.start()
    
    # Проверяем промежуточное значение (должно быть больше 350 или меньше 10)
    QTest.qWait(25)  # Половина анимации
    intermediate_angle = canvas.rotation_angle
    # Угол должен быть близок к 0 (либо ~360, либо ~0-5)
    assert intermediate_angle > 355 or intermediate_angle < 5, \
        f"Промежуточный угол должен быть около 0, получен {intermediate_angle}"
    
    QTest.qWait(50)  # Дожидаемся завершения
    assert abs(canvas.rotation_angle - 10.0) < 0.01, f"Финальный угол должен быть 10, получен {canvas.rotation_angle}"
    print("✓ Тест 7 пройден: кратчайший путь работает корректно")
    
    # Тест 8: Проверка длительности анимации
    canvas.rotation_angle = 0.0
    canvas.target_rotation_angle = 0.0
    canvas.is_rotating = False
    
    start_time = time.time()
    canvas._apply_rotation(clockwise=True)
    
    # Ждем завершения анимации
    while canvas.is_rotating and (time.time() - start_time) < 0.2:  # Максимум 200ms
        QTest.qWait(10)
    
    elapsed_time = (time.time() - start_time) * 1000  # В миллисекундах
    # Анимация должна занять примерно 50ms (±30ms для погрешности)
    assert 30 < elapsed_time < 120, f"Анимация должна занять ~50ms, заняла {elapsed_time:.1f}ms"
    print(f"✓ Тест 8 пройден: длительность анимации ~{elapsed_time:.1f}ms (ожидалось ~50ms)")
    
    print("\n✅ Все тесты анимации поворота пройдены успешно!")


if __name__ == "__main__":
    test_rotation_animation()
