import math
from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtGui import QPainter, QColor, QPen, QAction, QContextMenuEvent, QIcon
from PySide6.QtCore import Qt, QPointF, Signal, QTimer

from .core.scene import Scene
from .core.geometry import Point, Line
from .core.algorithms import bresenham
from .core.math_utils import (distance_point_to_segment_sq, get_distance, 
                             cartesian_to_polar, get_angle_between_points,
                             radians_to_degrees, degrees_to_radians, polar_to_cartesian)
from .settings import settings
from .icon_utils import load_svg_icon

class CanvasWidget(QWidget):
    cursor_pos_changed = Signal(QPointF)
    line_info_changed = Signal(str)  # Сигнал для передачи информации о линии

    def __init__(self, scene: Scene, line_tool_action: QAction, delete_tool_action: QAction, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.scene.scene_changed.connect(self.update)
        settings.settings_changed.connect(self.on_settings_changed)

        self.line_tool_action = line_tool_action
        self.delete_tool_action = delete_tool_action
        
        # Сбрасываем выделение при выходе из режима удаления
        self.delete_tool_action.changed.connect(self._on_delete_tool_changed)
        
        self.setMouseTracking(True)
        self.setAutoFillBackground(True) # Это свойство нужно для setStyleSheet
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Разрешаем получать фокус клавиатуры
        
        # Инициализируем переменные до вызова on_settings_changed
        self.start_pos = None
        self.current_pos = None
        self.pan_start_pos = None
        self.camera_pos = QPointF(0, 0)
        self._initial_center_done = False
        
        # Для режима удаления
        self.highlighted_line = None  # Линия, которая выделена при наведении
        self.selection_threshold = 10.0  # Пороговое расстояние в пикселях для выделения
        
        # Для режима построения линии
        self._current_construction_mode = settings.get("line_construction_mode") or "cartesian"
        
        # Zoom state variables
        self.zoom_factor = 1.0  # Текущий коэффициент масштабирования
        self.target_zoom_factor = 1.0  # Целевой zoom для анимации
        self.zoom_min = 0.1  # Минимальный zoom (10%)
        self.zoom_max = 10.0  # Максимальный zoom (1000%)
        self.zoom_step = 1.15  # Множитель изменения zoom при прокрутке колеса
        self.zoom_animation_speed = 0.15  # Скорость интерполяции (0-1)
        self.zoom_cursor_pos = None  # Позиция курсора для сохранения при zoom
        
        # QTimer for zoom animation with 16ms interval (~60 FPS)
        self.zoom_animation_timer = QTimer(self)
        self.zoom_animation_timer.setInterval(16)
        self.zoom_animation_timer.timeout.connect(self._animate_zoom)
        
        # Rotation state variables
        self.rotation_angle = 0.0  # Угол поворота вида в градусах (0-360)
        self.rotation_step = 90.0  # Шаг поворота при нажатии клавиш
        self.r_key_pressed = False  # Флаг нажатия клавиши R
        
        # Rotation animation state variables
        self.target_rotation_angle = 0.0  # Целевой угол для анимации
        self.rotation_animation_duration = 50  # Длительность анимации в миллисекундах
        self.rotation_animation_start_time = 0  # Время начала анимации
        self.rotation_animation_start_angle = 0.0  # Начальный угол анимации
        self.is_rotating = False  # Флаг активной анимации поворота
        
        # QTimer for rotation animation with 16ms interval (~60 FPS)
        self.rotation_animation_timer = QTimer(self)
        self.rotation_animation_timer.setInterval(16)
        self.rotation_animation_timer.timeout.connect(self._animate_rotation)
        
        # Rotation indicator state variables
        self.show_rotation_indicator = False  # Показывать ли индикатор поворота
        self.rotation_indicator_timer = QTimer(self)  # Таймер для скрытия индикатора
        self.rotation_indicator_timer.setInterval(2000)  # 2 секунды
        self.rotation_indicator_timer.setSingleShot(True)  # Одноразовый таймер
        self.rotation_indicator_timer.timeout.connect(self._hide_rotation_indicator)
        
        # Pan tool state variables
        self.pan_tool_active = False  # Флаг активности инструмента панорамирования
        self.is_panning = False  # Флаг активного панорамирования (зажата кнопка мыши)
        self.pan_start_pos = None  # Начальная позиция мыши при начале панорамирования
        self.pan_start_camera = None  # Начальная позиция камеры при начале панорамирования
        
        self.on_settings_changed() # Вызываем при старте, чтобы установить фон

    def on_settings_changed(self):
        """Слот, который вызывается при изменении настроек."""
        # Получаем настройки с "защитой" от их отсутствия
        colors = settings.get("colors") or settings.defaults["colors"]
        bg_color = colors.get("canvas_bg", "#2D2D2D")
        
        # Устанавливаем фон через прямое указание стиля. Это надежнее.
        self.setStyleSheet(f"background-color: {bg_color};")
        
        # Обновляем информацию о линии при изменении настроек (например, единиц углов)
        if self.start_pos and self.current_pos:
            self._update_line_info()
        
        self.update() # Запросить полную перерисовку
    
    def _on_delete_tool_changed(self):
        """Обработчик изменения состояния инструмента удаления."""
        if not self.delete_tool_action.isChecked():
            # Выходим из режима удаления - сбрасываем выделение
            self.highlighted_line = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
    
    def on_construction_mode_changed(self):
        """Обработчик изменения режима построения."""
        self._current_construction_mode = settings.get("line_construction_mode") or "cartesian"
        # Если мы в процессе построения линии, обновляем информацию
        if self.start_pos:
            self._update_line_info()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initial_center_done:
            # Инициализируем камеру так, чтобы центр экрана соответствовал (0, 0) в сцене
            # С учетом инверсии Y: 
            # center_screen = (width/2, height/2)
            # map_to_scene(center_screen) должно быть (0, 0)
            # scene_y = height/2 - height/2 + camera_y = camera_y = 0
            # Значит camera_y должен быть 0, а не -height/2
            self.camera_pos = QPointF(-self.width() / 2, 0)
            self._initial_center_done = True
            
    # ... (map_to_scene, map_from_scene и другие обработчики мыши остаются без изменений)
    def map_to_scene(self, screen_pos: QPointF) -> QPointF:
        """Преобразует экранные координаты в сценовые координаты с инверсией Y, учетом zoom и rotation.
        В математической системе координат Y увеличивается вверх."""
        # 1. Центрируем относительно экрана
        centered_x = screen_pos.x() - self.width() / 2
        centered_y = self.height() / 2 - screen_pos.y()
        
        # 2. Применяем обратный поворот (разворачиваем вид обратно)
        angle_rad = -math.radians(self.rotation_angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        rotated_x = centered_x * cos_angle - centered_y * sin_angle
        rotated_y = centered_x * sin_angle + centered_y * cos_angle
        
        # 3. Применяем масштаб и смещение камеры
        scene_x = rotated_x / self.zoom_factor + self.camera_pos.x()
        scene_y = rotated_y / self.zoom_factor + self.camera_pos.y()
        
        return QPointF(scene_x, scene_y)

    def map_from_scene(self, scene_pos: QPointF) -> QPointF:
        """Преобразует сценовые координаты в экранные координаты с инверсией Y, учетом zoom и rotation."""
        # 1. Применяем смещение камеры и масштаб (умножаем на zoom_factor)
        scaled_x = (scene_pos.x() - self.camera_pos.x()) * self.zoom_factor
        scaled_y = (scene_pos.y() - self.camera_pos.y()) * self.zoom_factor
        
        # 2. Применяем поворот
        angle_rad = math.radians(self.rotation_angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        rotated_x = scaled_x * cos_angle - scaled_y * sin_angle
        rotated_y = scaled_x * sin_angle + scaled_y * cos_angle
        
        # 3. Переводим в экранные координаты
        screen_x = rotated_x + self.width() / 2
        screen_y = self.height() / 2 - rotated_y
        
        return QPointF(screen_x, screen_y)

    def keyPressEvent(self, event):
        # Обработка клавиши R для поворота
        if event.key() == Qt.Key.Key_R:
            self.r_key_pressed = True
            event.accept()
            return
        
        # Обработка комбинаций R + Arrow keys для поворота
        if self.r_key_pressed:
            if event.key() == Qt.Key.Key_Left:
                # R + Left Arrow: поворот по часовой стрелке
                self._apply_rotation(clockwise=True)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Right:
                # R + Right Arrow: поворот против часовой стрелки
                self._apply_rotation(clockwise=False)
                event.accept()
                return
        
        # Обработка Escape для отмены построения линии
        if event.key() == Qt.Key.Key_Escape and self.start_pos:
            self.start_pos = None
            self.current_pos = None
            self.update()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Обрабатывает отпускание клавиш."""
        if event.key() == Qt.Key.Key_R:
            self.r_key_pressed = False
            event.accept()
        else:
            super().keyReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Обрабатывает события колеса мыши для масштабирования."""
        # Получаем направление прокрутки
        delta = event.angleDelta().y()
        
        if delta == 0:
            return
        
        # Сохраняем позицию курсора для использования в анимации
        self.zoom_cursor_pos = event.position()
        
        # Вычисляем новый target_zoom_factor
        if delta > 0:
            # Прокрутка вперед - увеличиваем zoom
            new_target = self.target_zoom_factor * self.zoom_step
        else:
            # Прокрутка назад - уменьшаем zoom
            new_target = self.target_zoom_factor / self.zoom_step
        
        # Ограничиваем zoom
        self.target_zoom_factor = max(self.zoom_min, min(self.zoom_max, new_target))
        
        # Запускаем анимацию, если она еще не активна
        if not self.zoom_animation_timer.isActive():
            self.zoom_animation_timer.start()
        
        event.accept()
    
    def _animate_zoom(self):
        """Выполняет один шаг анимации zoom с сохранением позиции курсора."""
        # Проверяем, достигли ли мы целевого zoom
        if abs(self.zoom_factor - self.target_zoom_factor) < 0.001:
            self.zoom_factor = self.target_zoom_factor
            self.zoom_animation_timer.stop()
            self.update()
            return
        
        # Сохраняем сценовую позицию под курсором до изменения zoom
        if self.zoom_cursor_pos:
            before_zoom_scene_pos = self.map_to_scene(self.zoom_cursor_pos)
        
        # Интерполируем zoom_factor к target_zoom_factor
        self.zoom_factor += (self.target_zoom_factor - self.zoom_factor) * self.zoom_animation_speed
        
        # Корректируем camera_pos так, чтобы точка под курсором осталась на месте
        if self.zoom_cursor_pos:
            after_zoom_scene_pos = self.map_to_scene(self.zoom_cursor_pos)
            # Вычисляем разницу и корректируем позицию камеры
            delta = after_zoom_scene_pos - before_zoom_scene_pos
            self.camera_pos -= delta
        
        self.update()
    
    def _apply_rotation(self, clockwise: bool):
        """
        Запускает анимацию поворота вида на rotation_step градусов.
        
        Args:
            clockwise: True для поворота по часовой стрелке, False для поворота против часовой стрелки
        """
        # Игнорируем новые команды поворота во время анимации
        if self.is_rotating:
            return
        
        # Сохраняем начальный угол
        self.rotation_animation_start_angle = self.rotation_angle
        
        # Вычисляем целевой угол
        if clockwise:
            # Поворот по часовой стрелке (+90°)
            self.target_rotation_angle = self.rotation_angle + self.rotation_step
        else:
            # Поворот против часовой стрелки (-90°)
            self.target_rotation_angle = self.rotation_angle - self.rotation_step
        
        # Нормализуем целевой угол к диапазону [0, 360)
        self.target_rotation_angle = self.target_rotation_angle % 360.0
        
        # Устанавливаем флаг активной анимации
        self.is_rotating = True
        
        # Сохраняем время начала анимации
        from PySide6.QtCore import QTime
        self.rotation_animation_start_time = QTime.currentTime().msecsSinceStartOfDay()
        
        # Показываем индикатор поворота и запускаем таймер для его скрытия
        self.show_rotation_indicator = True
        self.rotation_indicator_timer.start()
        
        # Запускаем таймер анимации
        if not self.rotation_animation_timer.isActive():
            self.rotation_animation_timer.start()
    
    def _animate_rotation(self):
        """
        Выполняет один шаг анимации поворота.
        Вызывается таймером с интервалом ~16ms (60 FPS).
        
        Алгоритм:
        1. Вычислить прогресс анимации (0.0 - 1.0) на основе времени
        2. Применить easing function для плавности (ease-in-out cubic)
        3. Интерполировать rotation_angle между start и target
        4. Обработать переход через 0°/360° (выбрать кратчайший путь)
        5. Если анимация завершена, установить точное значение и остановить таймер
        6. Вызвать update() для перерисовки
        """
        from PySide6.QtCore import QTime
        
        # Вычисляем прошедшее время
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        elapsed = current_time - self.rotation_animation_start_time
        
        # Вычисляем прогресс (0.0 - 1.0)
        progress = min(1.0, elapsed / self.rotation_animation_duration)
        
        # Применяем easing function (ease-in-out cubic)
        # Формула: t < 0.5 ? 4*t^3 : 1 - (-2*t + 2)^3 / 2
        if progress < 0.5:
            eased_progress = 4 * progress * progress * progress
        else:
            eased_progress = 1 - pow(-2 * progress + 2, 3) / 2
        
        # Вычисляем разницу углов с учетом кратчайшего пути
        angle_diff = self.target_rotation_angle - self.rotation_animation_start_angle
        
        # Нормализуем разницу к диапазону [-180, 180] для кратчайшего пути
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        
        # Интерполируем угол
        self.rotation_angle = self.rotation_animation_start_angle + angle_diff * eased_progress
        
        # Нормализуем к диапазону [0, 360)
        self.rotation_angle = self.rotation_angle % 360.0
        
        # Проверяем завершение анимации
        if progress >= 1.0:
            # Устанавливаем точное значение
            self.rotation_angle = self.target_rotation_angle
            self.is_rotating = False
            self.rotation_animation_timer.stop()
        
        # Перерисовываем холст
        self.update()
    
    def _hide_rotation_indicator(self):
        """Скрывает индикатор поворота после таймаута."""
        self.show_rotation_indicator = False
        self.update()
    
    def set_pan_tool_active(self, active: bool):
        """
        Активирует или деактивирует инструмент панорамирования.
        
        Args:
            active: True для активации, False для деактивации
        """
        self.pan_tool_active = active
        
        if active:
            # Устанавливаем курсор открытой руки
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            # Восстанавливаем обычный курсор
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Сбрасываем состояние панорамирования
            self.is_panning = False
            self.pan_start_pos = None
            self.pan_start_camera = None

    def mousePressEvent(self, event):
        # Обработка pan tool с левой кнопкой мыши
        if self.pan_tool_active and event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = True
            self.pan_start_pos = event.position()
            self.pan_start_camera = QPointF(self.camera_pos.x(), self.camera_pos.y())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        
        # Панорамирование средней кнопкой недоступно во время построения линии
        if event.button() == Qt.MouseButton.MiddleButton:
            # Если идет процесс построения линии, игнорируем панорамирование
            if self.start_pos is not None:
                return
            self.pan_start_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            return  # Прерываем выполнение, чтобы не обрабатывать другие события
        
        if self.line_tool_action.isChecked():
            if event.button() == Qt.MouseButton.LeftButton:
                if self.start_pos is None:
                    # Первый клик: начинаем рисовать линию
                    # Сбрасываем панорамирование, если оно было активно
                    if self.pan_start_pos is not None:
                        self.pan_start_pos = None
                        self.setCursor(Qt.CursorShape.ArrowCursor)
                    self.start_pos = event.position()
                    self.current_pos = self.start_pos
                    self._update_line_info()  # Обновляем информацию о линии
                else:
                    # Второй клик: завершаем линию
                    start_scene_pos = self.map_to_scene(self.start_pos)
                    
                    if self._current_construction_mode == "polar":
                        # В полярном режиме используем текущую позицию курсора для вычисления полярных координат
                        # Используем self.current_pos если оно есть, иначе event.position()
                        cursor_pos = self.current_pos if self.current_pos else event.position()
                        current_scene_pos = self.map_to_scene(cursor_pos)
                        end_point_qpoint = self._calculate_end_point_polar(start_scene_pos, current_scene_pos)
                        end_point = Point(end_point_qpoint.x(), end_point_qpoint.y())
                    else:
                        # В декартовом режиме используем позицию клика напрямую
                        end_scene_pos = self.map_to_scene(event.position())
                        end_point = Point(end_scene_pos.x(), end_scene_pos.y())
                    
                    start_point = Point(start_scene_pos.x(), start_scene_pos.y())
                    line = Line(start_point, end_point)
                    self.scene.add_object(line)
                    self.start_pos = None
                    self.current_pos = None
                    self.line_info_changed.emit("")  # Очищаем информацию
            elif event.button() == Qt.MouseButton.RightButton and self.start_pos:
                # Отмена рисования правой кнопкой мыши
                self.start_pos = None
                self.current_pos = None
                self.line_info_changed.emit("")  # Очищаем информацию
        elif self.delete_tool_action.isChecked():
            if event.button() == Qt.MouseButton.LeftButton and self.highlighted_line:
                # Удаляем выделенную линию
                self.scene.remove_object(self.highlighted_line)
                self.highlighted_line = None
        self.update()

    def mouseMoveEvent(self, event):
        self.cursor_pos_changed.emit(event.position())
        
        # Обработка панорамирования с pan tool (левая кнопка)
        if self.is_panning:
            # Вычисляем смещение в экранных координатах
            screen_delta_x = event.position().x() - self.pan_start_pos.x()
            screen_delta_y = event.position().y() - self.pan_start_pos.y()
            
            # Преобразуем в сценовые координаты с учетом zoom
            # (без учета camera_pos, так как мы вычисляем относительное смещение)
            scene_delta_x = screen_delta_x / self.zoom_factor
            scene_delta_y = -screen_delta_y / self.zoom_factor  # Инверсия Y
            
            # Применяем обратный поворот к delta
            angle_rad = -math.radians(self.rotation_angle)
            cos_angle = math.cos(angle_rad)
            sin_angle = math.sin(angle_rad)
            rotated_delta_x = scene_delta_x * cos_angle - scene_delta_y * sin_angle
            rotated_delta_y = scene_delta_x * sin_angle + scene_delta_y * cos_angle
            
            # Обновляем позицию камеры
            self.camera_pos = QPointF(
                self.pan_start_camera.x() - rotated_delta_x,
                self.pan_start_camera.y() - rotated_delta_y
            )
            
            self.update()
            return
        
        # Панорамирование средней кнопкой недоступно во время построения линии
        if self.pan_start_pos and event.buttons() & Qt.MouseButton.MiddleButton:
            # Если идет процесс построения линии, прерываем панорамирование
            if self.start_pos is not None:
                self.pan_start_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                # Панорамирование - перемещаем камеру с учетом поворота
                # Вычисляем сценовые позиции до и после движения мыши
                scene_pos_before = self.map_to_scene(self.pan_start_pos)
                scene_pos_after = self.map_to_scene(event.position())
                
                # Разница в сценовых координатах показывает, насколько нужно сдвинуть камеру
                scene_delta = scene_pos_after - scene_pos_before
                
                # Сдвигаем камеру в противоположном направлении
                self.camera_pos -= scene_delta
                
                self.pan_start_pos = event.position()
                self.update()
                return  # Прерываем выполнение, чтобы не обрабатывать другие события
        
        # Обработка режима удаления
        if self.delete_tool_action.isChecked():
            # В режиме удаления ищем ближайшую линию
            self._find_nearest_line(event.position())
            # Меняем курсор на крестик в режиме удаления
            if self.highlighted_line:
                self.setCursor(Qt.CursorShape.PointingHandCursor)  # Рука указывающая
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)  # Крестик
        else:
            # Выходим из режима удаления - сбрасываем выделение и курсор
            if self.highlighted_line is not None:
                self.highlighted_line = None
                self.update()
            self.setCursor(Qt.CursorShape.ArrowCursor)  # Обычная стрелка
        
        # Обработка построения линии
        if self.start_pos:
            self.current_pos = event.position()
            self._update_line_info()  # Обновляем информацию о линии при движении
            self.update()

    def mouseReleaseEvent(self, event):
        # Обработка отпускания левой кнопки при pan tool
        if self.is_panning and event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.pan_start_pos = None
            self.pan_start_camera = None
            # Восстанавливаем курсор открытой руки (pan tool все еще активен)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        
        if event.button() == Qt.MouseButton.MiddleButton:
            self.pan_start_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        self._draw_grid(painter)
        self._draw_axes(painter)
        self._draw_scene_objects(painter)
        self._draw_highlighted_line(painter)
        self._draw_preview(painter)
        
        # Отрисовываем индикатор поворота поверх всего остального
        if self.show_rotation_indicator:
            self._draw_rotation_indicator(painter)
        
        painter.end()

    def _draw_grid(self, painter: QPainter):
        colors = settings.get("colors") or settings.defaults["colors"]
        pen_minor = QPen(QColor(colors.get("grid_minor", "#000000")), 0.5)
        pen_major = QPen(QColor(colors.get("grid_major", "#000000")), 1)
        grid_size = settings.get("grid_step") or settings.defaults["grid_step"]
        major_grid_interval = 5

        width, height = self.width(), self.height()
        
        # При повороте нужно проверить все 4 угла экрана, чтобы найти правильный диапазон сетки
        corners = [
            self.map_to_scene(QPointF(0, 0)),           # Верхний левый
            self.map_to_scene(QPointF(width, 0)),       # Верхний правый
            self.map_to_scene(QPointF(0, height)),      # Нижний левый
            self.map_to_scene(QPointF(width, height))   # Нижний правый
        ]
        
        # Находим минимальные и максимальные координаты сцены
        scene_x_min = min(corner.x() for corner in corners)
        scene_x_max = max(corner.x() for corner in corners)
        scene_y_min = min(corner.y() for corner in corners)
        scene_y_max = max(corner.y() for corner in corners)
        
        start_x_index = math.floor(scene_x_min / grid_size)
        end_x_index = math.ceil(scene_x_max / grid_size)
        start_y_index = math.floor(scene_y_min / grid_size)
        end_y_index = math.ceil(scene_y_max / grid_size)

        # Определяем, нужно ли рисовать minor линии на основе zoom_factor
        # При zoom < 0.5 скрываем minor линии для улучшения производительности и читаемости
        show_minor_lines = self.zoom_factor >= 0.5

        # Рисуем вертикальные линии сетки (постоянный X в сцене)
        for i in range(start_x_index, end_x_index + 1):
            is_major = (i % major_grid_interval == 0)
            
            # Пропускаем minor линии, если zoom слишком мал
            if not is_major and not show_minor_lines:
                continue
            
            painter.setPen(pen_major if is_major else pen_minor)
            line_scene_x = i * grid_size
            
            # Линия от минимального Y до максимального Y в сцене
            start_screen = self.map_from_scene(QPointF(line_scene_x, scene_y_min))
            end_screen = self.map_from_scene(QPointF(line_scene_x, scene_y_max))
            painter.drawLine(start_screen.toPoint(), end_screen.toPoint())

        # Рисуем горизонтальные линии сетки (постоянный Y в сцене)
        for i in range(start_y_index, end_y_index + 1):
            is_major = (i % major_grid_interval == 0)
            
            # Пропускаем minor линии, если zoom слишком мал
            if not is_major and not show_minor_lines:
                continue
            
            painter.setPen(pen_major if is_major else pen_minor)
            line_scene_y = i * grid_size
            
            # Линия от минимального X до максимального X в сцене
            start_screen = self.map_from_scene(QPointF(scene_x_min, line_scene_y))
            end_screen = self.map_from_scene(QPointF(scene_x_max, line_scene_y))
            painter.drawLine(start_screen.toPoint(), end_screen.toPoint())

    def _draw_axes(self, painter: QPainter):
        # Рисуем оси координат с учетом поворота
        # Ось X (красная) - горизонтальная линия через начало координат
        # Ось Y (зеленая) - вертикальная линия через начало координат
        
        width, height = self.width(), self.height()
        
        # Находим диапазон для осей, проверяя все углы экрана
        corners = [
            self.map_to_scene(QPointF(0, 0)),
            self.map_to_scene(QPointF(width, 0)),
            self.map_to_scene(QPointF(0, height)),
            self.map_to_scene(QPointF(width, height))
        ]
        
        scene_x_min = min(corner.x() for corner in corners)
        scene_x_max = max(corner.x() for corner in corners)
        scene_y_min = min(corner.y() for corner in corners)
        scene_y_max = max(corner.y() for corner in corners)
        
        # Рисуем ось Y (вертикальная в сцене, X=0)
        painter.setPen(QPen(QColor("#CC7A7A"), 1.5))
        y_axis_start = self.map_from_scene(QPointF(0, scene_y_min))
        y_axis_end = self.map_from_scene(QPointF(0, scene_y_max))
        painter.drawLine(y_axis_start.toPoint(), y_axis_end.toPoint())
        
        # Рисуем ось X (горизонтальная в сцене, Y=0)
        painter.setPen(QPen(QColor("#7ACC7A"), 1.5))
        x_axis_start = self.map_from_scene(QPointF(scene_x_min, 0))
        x_axis_end = self.map_from_scene(QPointF(scene_x_max, 0))
        painter.drawLine(x_axis_start.toPoint(), x_axis_end.toPoint())

    def _draw_scene_objects(self, painter: QPainter):
        colors = settings.get("colors") or settings.defaults["colors"]
        pen = QPen(QColor(colors.get("line_object", "#FFFFFF")), 2)
        painter.setPen(pen)

        for obj in self.scene.objects:
            if isinstance(obj, Line):
                # Пропускаем выделенную линию - она будет отрисована отдельно красным
                if obj == self.highlighted_line and self.delete_tool_action.isChecked():
                    continue
                    
                start_screen = self.map_from_scene(QPointF(obj.start.x, obj.start.y))
                end_screen = self.map_from_scene(QPointF(obj.end.x, obj.end.y))
                points_generator = bresenham(
                    int(start_screen.x()), int(start_screen.y()),
                    int(end_screen.x()), int(end_screen.y())
                )
                for point in points_generator:
                    painter.drawPoint(*point)
    
    def _draw_preview(self, painter: QPainter):
        if self.start_pos and self.current_pos:
            pen = QPen(QColor("#7A86CC"), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            
            if self._current_construction_mode == "polar":
                # В полярном режиме вычисляем конечную точку из полярных координат
                start_scene_pos = self.map_to_scene(self.start_pos)
                current_scene_pos = self.map_to_scene(self.current_pos)
                end_point = self._calculate_end_point_polar(start_scene_pos, current_scene_pos)
                end_screen = self.map_from_scene(end_point)
                painter.drawLine(self.start_pos.toPoint(), end_screen.toPoint())
            else:
                # В декартовом режиме рисуем прямую линию
                painter.drawLine(self.start_pos.toPoint(), self.current_pos.toPoint())
    
    def _calculate_end_point_polar(self, start_scene: QPointF, cursor_scene: QPointF) -> QPointF:
        """
        Вычисляет конечную точку линии в полярных координатах.
        Использует полярные координаты курсора относительно начальной точки.
        """
        # Вычисляем полярные координаты курсора относительно начальной точки
        r, theta = cartesian_to_polar(start_scene, cursor_scene)
        
        # Конвертируем обратно в декартовы координаты для построения линии
        end_point = polar_to_cartesian(start_scene, r, theta)
        return end_point
    
    def _update_line_info(self):
        """Обновляет информацию о линии в статус-баре."""
        if not self.start_pos or not self.current_pos:
            self.line_info_changed.emit("")
            return
        
        start_scene_pos = self.map_to_scene(self.start_pos)
        current_scene_pos = self.map_to_scene(self.current_pos)
        
        # Вычисляем расстояние (длину линии)
        length = get_distance(start_scene_pos, current_scene_pos)
        
        # Вычисляем угол
        angle_rad = get_angle_between_points(start_scene_pos, current_scene_pos)
        
        # Получаем единицы измерения углов из настроек
        angle_units = settings.get("angle_units") or "degrees"
        
        if self._current_construction_mode == "polar":
            # В полярном режиме показываем полярные координаты
            r, theta = cartesian_to_polar(start_scene_pos, current_scene_pos)
            
            if angle_units == "degrees":
                angle_display = radians_to_degrees(theta)
                angle_unit_str = "°"
            else:
                angle_display = theta
                angle_unit_str = " rad"
            
            info = f"r: {r:.2f}, θ: {angle_display:.2f}{angle_unit_str} | Длина: {length:.2f}"
        else:
            # В декартовом режиме показываем декартовы координаты и угол
            if angle_units == "degrees":
                angle_display = radians_to_degrees(angle_rad)
                angle_unit_str = "°"
            else:
                angle_display = angle_rad
                angle_unit_str = " rad"
            
            info = f"Длина: {length:.2f} | Угол: {angle_display:.2f}{angle_unit_str}"
        
        self.line_info_changed.emit(info)
    
    def _find_nearest_line(self, cursor_pos: QPointF):
        """
        Находит ближайшую линию к курсору и устанавливает её как выделенную.
        """
        scene_cursor_pos = self.map_to_scene(cursor_pos)
        cursor_qpoint = QPointF(scene_cursor_pos.x(), scene_cursor_pos.y())
        
        nearest_line = None
        min_distance_sq = self.selection_threshold ** 2  # Квадрат порогового расстояния
        
        for obj in self.scene.objects:
            if isinstance(obj, Line):
                start_qpoint = QPointF(obj.start.x, obj.start.y)
                end_qpoint = QPointF(obj.end.x, obj.end.y)
                
                # Вычисляем расстояние от курсора до отрезка
                distance_sq = distance_point_to_segment_sq(cursor_qpoint, start_qpoint, end_qpoint)
                
                if distance_sq < min_distance_sq:
                    min_distance_sq = distance_sq
                    nearest_line = obj
        
        # Обновляем выделенную линию только если она изменилась
        if nearest_line != self.highlighted_line:
            self.highlighted_line = nearest_line
            self.update()
    
    def _draw_highlighted_line(self, painter: QPainter):
        """
        Отрисовывает выделенную линию красным цветом.
        """
        if self.highlighted_line and self.delete_tool_action.isChecked():
            # Отрисовываем выделенную линию красным цветом
            pen = QPen(QColor("#FF4444"), 3)  # Красный цвет, немного толще
            painter.setPen(pen)
            
            start_screen = self.map_from_scene(QPointF(self.highlighted_line.start.x, self.highlighted_line.start.y))
            end_screen = self.map_from_scene(QPointF(self.highlighted_line.end.x, self.highlighted_line.end.y))
            
            points_generator = bresenham(
                int(start_screen.x()), int(start_screen.y()),
                int(end_screen.x()), int(end_screen.y())
            )
            for point in points_generator:
                painter.drawPoint(*point)
    
    def _draw_rotation_indicator(self, painter: QPainter):
        """
        Отрисовывает визуальный индикатор текущего угла поворота.
        Отображается в правом верхнем углу холста.
        
        Элементы индикатора:
        - Круговая диаграмма с отметками 0°, 90°, 180°, 270°
        - Стрелка, указывающая текущий угол поворота
        - Текстовое значение угла
        - Полупрозрачный фон для читаемости
        """
        # Размеры и позиция индикатора
        indicator_size = 80  # Размер круга индикатора
        margin = 20  # Отступ от края экрана
        center_x = self.width() - margin - indicator_size // 2
        center_y = margin + indicator_size // 2
        center = QPointF(center_x, center_y)
        radius = indicator_size // 2 - 10  # Радиус круга
        
        # Сохраняем состояние painter
        painter.save()
        
        # Рисуем полупрозрачный фон
        bg_color = QColor("#2D2D2D")
        bg_color.setAlphaF(0.8)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, indicator_size // 2, indicator_size // 2)
        
        # Рисуем круг индикатора
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)
        
        # Рисуем отметки для 0°, 90°, 180°, 270°
        tick_angles = [0, 90, 180, 270]
        tick_labels = ["0°", "90°", "180°", "270°"]
        
        for angle, label in zip(tick_angles, tick_labels):
            # Конвертируем угол в радианы (0° вверху, по часовой стрелке)
            angle_rad = math.radians(angle - 90)  # -90 чтобы 0° был вверху
            
            # Внешняя точка отметки
            outer_x = center_x + radius * math.cos(angle_rad)
            outer_y = center_y + radius * math.sin(angle_rad)
            
            # Внутренняя точка отметки
            inner_radius = radius - 8
            inner_x = center_x + inner_radius * math.cos(angle_rad)
            inner_y = center_y + inner_radius * math.sin(angle_rad)
            
            # Рисуем отметку
            painter.setPen(QPen(QColor("#AAAAAA"), 2))
            painter.drawLine(QPointF(inner_x, inner_y), QPointF(outer_x, outer_y))
        
        # Рисуем стрелку, указывающую текущий угол поворота
        # Угол поворота в нашей системе: 0° = нет поворота, 90° = поворот по часовой на 90°
        # В индикаторе: 0° вверху, инвертируем направление для соответствия визуальному повороту
        arrow_angle_rad = math.radians(-self.rotation_angle - 90)  # Инвертируем и -90 чтобы 0° был вверху
        arrow_length = radius - 5
        arrow_x = center_x + arrow_length * math.cos(arrow_angle_rad)
        arrow_y = center_y + arrow_length * math.sin(arrow_angle_rad)
        
        # Рисуем стрелку
        painter.setPen(QPen(QColor("#7ACC7A"), 3))  # Зеленый цвет как ось X
        painter.drawLine(center, QPointF(arrow_x, arrow_y))
        
        # Рисуем наконечник стрелки
        arrow_head_length = 8
        arrow_head_angle = math.radians(30)  # Угол наконечника
        
        # Левая часть наконечника
        left_angle = arrow_angle_rad + math.pi - arrow_head_angle
        left_x = arrow_x + arrow_head_length * math.cos(left_angle)
        left_y = arrow_y + arrow_head_length * math.sin(left_angle)
        painter.drawLine(QPointF(arrow_x, arrow_y), QPointF(left_x, left_y))
        
        # Правая часть наконечника
        right_angle = arrow_angle_rad + math.pi + arrow_head_angle
        right_x = arrow_x + arrow_head_length * math.cos(right_angle)
        right_y = arrow_y + arrow_head_length * math.sin(right_angle)
        painter.drawLine(QPointF(arrow_x, arrow_y), QPointF(right_x, right_y))
        
        # Рисуем текстовое значение угла в центре
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.setFont(painter.font())
        # Инвертируем угол для отображения (360 - angle), чтобы соответствовать визуальному направлению
        display_angle = (360 - int(self.rotation_angle)) % 360
        text = f"{display_angle}°"
        text_rect = painter.fontMetrics().boundingRect(text)
        text_x = center_x - text_rect.width() // 2
        text_y = center_y + text_rect.height() // 4
        painter.drawText(int(text_x), int(text_y), text)
        
        # Восстанавливаем состояние painter
        painter.restore()
    
    def _calculate_scene_bounds(self):
        """
        Вычисляет bounding box всех объектов в сцене.
        
        Returns:
            tuple[QPointF, QPointF] | None: (min_point, max_point) - углы bounding box в сценовых координатах
                                            None если объектов нет в сцене
        """
        if not self.scene.objects:
            return None
        
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for obj in self.scene.objects:
            if isinstance(obj, Line):
                # Для линии проверяем обе точки
                min_x = min(min_x, obj.start.x, obj.end.x)
                min_y = min(min_y, obj.start.y, obj.end.y)
                max_x = max(max_x, obj.start.x, obj.end.x)
                max_y = max(max_y, obj.start.y, obj.end.y)
            # TODO: Добавить обработку других типов объектов (круги, дуги)
        
        return (QPointF(min_x, min_y), QPointF(max_x, max_y))
    
    def zoom_to_fit(self):
        """
        Автоматически масштабирует и центрирует вид для отображения всех объектов.
        Добавляет 10% padding вокруг bounding box.
        """
        bounds = self._calculate_scene_bounds()
        
        if bounds is None:
            # Нет объектов - возвращаемся к начальному виду
            self.target_zoom_factor = 1.0
            self.camera_pos = QPointF(-self.width() / 2, 0)
            if not self.zoom_animation_timer.isActive():
                self.zoom_animation_timer.start()
            return
        
        min_point, max_point = bounds
        
        # Вычисляем размеры bounding box
        bbox_width = max_point.x() - min_point.x()
        bbox_height = max_point.y() - min_point.y()
        
        # Добавляем отступы 10%
        padding = 0.1
        bbox_width *= (1 + padding * 2)
        bbox_height *= (1 + padding * 2)
        
        # Защита от деления на ноль для очень маленьких объектов
        if bbox_width < 0.01:
            bbox_width = 10.0
        if bbox_height < 0.01:
            bbox_height = 10.0
        
        # Вычисляем необходимый zoom для вмещения bbox
        # Учитываем, что нужно вместить и по ширине, и по высоте
        zoom_x = self.width() / bbox_width if bbox_width > 0 else 1.0
        zoom_y = self.height() / bbox_height if bbox_height > 0 else 1.0
        
        # Выбираем меньший zoom, чтобы все поместилось
        new_zoom = min(zoom_x, zoom_y)
        
        # Ограничиваем zoom
        self.target_zoom_factor = max(self.zoom_min, min(self.zoom_max, new_zoom))
        
        # Центрируем камеру на центре bounding box
        center_x = (min_point.x() + max_point.x()) / 2
        center_y = (min_point.y() + max_point.y()) / 2
        
        # Устанавливаем camera_pos так, чтобы центр bbox был в центре экрана
        self.camera_pos = QPointF(center_x, center_y)
        
        # Сбрасываем zoom_cursor_pos, чтобы анимация не пыталась сохранить позицию курсора
        self.zoom_cursor_pos = None
        
        # Запускаем анимацию zoom
        if not self.zoom_animation_timer.isActive():
            self.zoom_animation_timer.start()
    
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Обрабатывает событие вызова контекстного меню (правая кнопка мыши).
        
        Args:
            event: Событие контекстного меню с позицией курсора
        """
        menu = self._create_context_menu(event.pos())
        menu.exec(event.globalPos())
    
    def _create_context_menu(self, cursor_pos: QPointF) -> QMenu:
        """
        Создает контекстное меню в зависимости от контекста.
        
        Args:
            cursor_pos: Позиция курсора в экранных координатах
        
        Returns:
            QMenu: Настроенное контекстное меню
        """
        menu = QMenu(self)
        
        # Проверяем, есть ли объект под курсором
        obj = self._get_object_at_cursor(cursor_pos)
        
        # Добавляем подменю "Вид" (всегда присутствует)
        view_submenu = self._create_view_submenu()
        menu.addMenu(view_submenu)
        
        # Если есть объект под курсором, добавляем команды для работы с объектами
        if obj:
            # Добавляем разделитель перед командами объекта
            menu.addSeparator()
            
            # ===== Место для будущих команд работы с объектами =====
            # Примеры команд, которые можно добавить:
            # - Изменить... (редактирование свойств объекта)
            # - Удалить (удаление выбранного объекта)
            # - Копировать (копирование объекта)
            # - Свойства... (диалог со свойствами объекта)
            # 
            # Пример добавления команды:
            # edit_action = menu.addAction("Изменить...")
            # edit_action.setIcon(load_svg_icon("public/edit.svg"))
            # edit_action.triggered.connect(lambda: self._on_edit_object(obj))
        
        return menu
    
    def _create_view_submenu(self) -> QMenu:
        """
        Создает подменю "Вид" с командами управления видом.
        
        Returns:
            QMenu: Подменю с командами управления видом
        """
        view_menu = QMenu("Вид", self)
        
        # Добавляем команду "Панорамирование" с иконкой и чекбоксом
        pan_action = view_menu.addAction("Панорамирование")
        pan_action.setIcon(load_svg_icon("public/move.svg"))
        pan_action.setCheckable(True)
        pan_action.setChecked(self.pan_tool_active)
        pan_action.triggered.connect(self._on_context_menu_pan_tool)
        
        # Добавляем команду "Показать всё" с иконкой
        zoom_fit_action = view_menu.addAction("Показать всё")
        zoom_fit_action.setIcon(QIcon.fromTheme("zoom-fit-best"))
        zoom_fit_action.triggered.connect(self.zoom_to_fit)
        
        # Добавляем разделитель
        view_menu.addSeparator()
        
        # Добавляем команду "Повернуть сцену налево 90°" с иконкой
        rotate_left_action = view_menu.addAction("Повернуть сцену направо 90°")
        rotate_left_action.setIcon(load_svg_icon("public/rotate.svg"))
        rotate_left_action.triggered.connect(lambda: self._apply_rotation(clockwise=False))
        
        # Добавляем команду "Повернуть сцену направо 90°" с иконкой
        rotate_right_action = view_menu.addAction("Повернуть сцену налево 90°")
        rotate_right_action.setIcon(load_svg_icon("public/rotate_right.svg"))
        rotate_right_action.triggered.connect(lambda: self._apply_rotation(clockwise=True))
        
        return view_menu
    
    def _on_context_menu_pan_tool(self, checked: bool):
        """
        Обработчик активации pan tool из контекстного меню.
        Синхронизирует состояние с toolbar в MainWindow.
        
        Args:
            checked: True для активации, False для деактивации
        """
        # Активируем pan tool в canvas
        self.set_pan_tool_active(checked)
        
        # Находим parent MainWindow, проходя по иерархии родителей
        parent = self.parent()
        while parent is not None:
            # Проверяем, является ли parent экземпляром QMainWindow
            if parent.__class__.__name__ == 'MainWindow':
                # Синхронизируем состояние pan_tool_action в toolbar
                if hasattr(parent, 'pan_tool_action'):
                    parent.pan_tool_action.setChecked(checked)
                
                # Деактивируем другие инструменты, если pan tool активирован
                if checked:
                    if hasattr(parent, 'line_tool_action'):
                        parent.line_tool_action.setChecked(False)
                    if hasattr(parent, 'delete_tool_action'):
                        parent.delete_tool_action.setChecked(False)
                break
            parent = parent.parent()
    
    def _get_object_at_cursor(self, cursor_pos: QPointF) -> object | None:
        """
        Определяет, есть ли объект под курсором.
        
        Args:
            cursor_pos: Позиция курсора в экранных координатах
        
        Returns:
            object | None: Объект под курсором или None
        """
        # Преобразуем cursor_pos в сценовые координаты
        scene_cursor_pos = self.map_to_scene(cursor_pos)
        cursor_qpoint = QPointF(scene_cursor_pos.x(), scene_cursor_pos.y())
        
        # Проверяем все объекты сцены на попадание
        nearest_object = None
        min_distance_sq = self.selection_threshold ** 2  # Квадрат порогового расстояния
        
        for obj in self.scene.objects:
            if isinstance(obj, Line):
                start_qpoint = QPointF(obj.start.x, obj.start.y)
                end_qpoint = QPointF(obj.end.x, obj.end.y)
                
                # Используем существующую логику distance_point_to_segment_sq
                distance_sq = distance_point_to_segment_sq(cursor_qpoint, start_qpoint, end_qpoint)
                
                if distance_sq < min_distance_sq:
                    min_distance_sq = distance_sq
                    nearest_object = obj
        
        return nearest_object
    
    def get_view_state(self):
        """Возвращает текущее состояние вида для сохранения."""
        return {
            "camera_pos": {"x": self.camera_pos.x(), "y": self.camera_pos.y()},
            "zoom_factor": self.zoom_factor,
            "rotation_angle": self.rotation_angle
        }
    
    def set_view_state(self, state):
        """Восстанавливает состояние вида из сохраненных данных."""
        if "camera_pos" in state:
            self.camera_pos = QPointF(state["camera_pos"]["x"], state["camera_pos"]["y"])
        self.zoom_factor = state.get("zoom_factor", 1.0)
        self.target_zoom_factor = self.zoom_factor  # Синхронизируем target с текущим значением
        self.rotation_angle = state.get("rotation_angle", 0.0)
        self.update()