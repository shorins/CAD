import math
from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtGui import QPainter, QColor, QPen, QAction, QContextMenuEvent, QIcon, QMouseEvent, QBrush, QPainterPath
from PySide6.QtCore import Qt, QPointF, Signal, QTimer, QRectF

from .core.scene import Scene
from .core.geometry import (
    Point, Line, Circle, Arc, Rectangle, Ellipse, Polygon, Spline,
    GeometricPrimitive, SnapType
)
from .core.snap_manager import snap_manager
# from .core.algorithms import bresenham
from .core.math_utils import (distance_point_to_segment_sq, get_distance, 
                             cartesian_to_polar, get_angle_between_points,
                             radians_to_degrees, degrees_to_radians, polar_to_cartesian)
from .settings import settings
from .icon_utils import load_svg_icon
from .core.style_manager import style_manager
from .core.render_utils import create_wavy_path, create_zigzag_path

class CanvasWidget(QWidget):
    cursor_pos_changed = Signal(QPointF)
    line_info_changed = Signal(str)  # Сигнал для передачи информации о линии
    zoom_changed = Signal(float)  # Сигнал для передачи текущего zoom_factor
    rotation_changed = Signal(float)  # Сигнал для передачи текущего rotation_angle
    selection_changed = Signal(list) # Сигнал об изменении выделения (передает список выделенных объектов)

    def __init__(self, scene: Scene, tool_actions: dict, parent=None):
        """
        Args:
            scene: Сцена с объектами
            tool_actions: Словарь с actions инструментов:
                'select', 'line', 'circle', 'arc', 'rectangle', 
                'ellipse', 'polygon', 'spline', 'delete'
        """
        super().__init__(parent)
        self.scene = scene
        self.scene.scene_changed.connect(self.update)
        settings.settings_changed.connect(self.on_settings_changed)

        # Сохраняем все tool actions
        self.tool_actions = tool_actions
        self.select_tool_action = tool_actions.get('select')
        self.line_tool_action = tool_actions.get('line')
        self.circle_tool_action = tool_actions.get('circle')
        self.arc_tool_action = tool_actions.get('arc')
        self.rectangle_tool_action = tool_actions.get('rectangle')
        self.ellipse_tool_action = tool_actions.get('ellipse')
        self.polygon_tool_action = tool_actions.get('polygon')
        self.spline_tool_action = tool_actions.get('spline')
        self.delete_tool_action = tool_actions.get('delete')
        
        # Сбрасываем выделение при выходе из режима удаления
        self.delete_tool_action.changed.connect(self._on_delete_tool_changed)
        
        self.setMouseTracking(True)
        self.setAutoFillBackground(True) # Это свойство нужно для setStyleSheet
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Разрешаем получать фокус клавиатуры

        self.selected_objects = [] # <-- Список выделенных объектов
        
        # Инициализируем переменные до вызова on_settings_changed
        self.start_pos = None
        self.current_pos = None
        self.pan_start_pos = None
        self.camera_pos = QPointF(0, 0)
        self._initial_center_done = False
        
        # Для режима удаления
        self.highlighted_line = None  # Линия, которая выделена при наведении (красная, для удаления)
        self.hover_highlighted_line = None  # Линия, подсвеченная при наведении (голубая)
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
        
        # Snap point state
        self.current_snap_point = None  # Текущая точка привязки (SnapPoint или None)
        
        # Состояние построения примитивов (для многокликовых методов)
        self.construction_points = []  # Накопленные точки (Point)
        self.construction_method = None  # Текущий метод построения (строка)
        
        # Ссылки на панели ввода (устанавливаются из MainWindow)
        self.circle_input_panel = None
        self.arc_input_panel = None
        self.rectangle_input_panel = None
        self.ellipse_input_panel = None
        self.polygon_input_panel = None
        self.spline_input_panel = None
        
        self.on_settings_changed() # Вызываем при старте, чтобы установить фон
        
        # Отправляем начальные значения zoom и rotation
        self.zoom_changed.emit(self.zoom_factor)
        self.rotation_changed.emit(self.rotation_angle)
    
    def get_active_drawing_tool(self) -> str | None:
        """
        Возвращает имя активного инструмента рисования.
        Returns:
            'line', 'circle', 'arc', 'rectangle', 'ellipse', 'polygon', 'spline' или None
        """
        if self.line_tool_action and self.line_tool_action.isChecked():
            return 'line'
        if self.circle_tool_action and self.circle_tool_action.isChecked():
            return 'circle'
        if self.arc_tool_action and self.arc_tool_action.isChecked():
            return 'arc'
        if self.rectangle_tool_action and self.rectangle_tool_action.isChecked():
            return 'rectangle'
        if self.ellipse_tool_action and self.ellipse_tool_action.isChecked():
            return 'ellipse'
        if self.polygon_tool_action and self.polygon_tool_action.isChecked():
            return 'polygon'
        if self.spline_tool_action and self.spline_tool_action.isChecked():
            return 'spline'
        return None
    
    def is_drawing_tool_active(self) -> bool:
        """Проверяет, активен ли какой-либо инструмент рисования."""
        return self.get_active_drawing_tool() is not None
    
    def finish_spline(self):
        """Завершает построение текущего сплайна."""
        from .core.style_manager import style_manager
        
        if hasattr(self, '_spline_points') and len(self._spline_points) >= 2:
            current_style = style_manager.get_current_style().name
            obj = Spline(self._spline_points, style_name=current_style)
            self.scene.add_object(obj)
        
        # Сбрасываем состояние
        self._spline_points = []
        self.start_pos = None
        self.current_pos = None
        
        # Обновляем панель
        if self.spline_input_panel:
            self.spline_input_panel.reset()
        
        self.update()

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
            self.zoom_changed.emit(self.zoom_factor)
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
        
        self.zoom_changed.emit(self.zoom_factor)
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
        
        # Отправляем сигнал об изменении угла поворота
        self.rotation_changed.emit(self.rotation_angle)
        
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

    def mousePressEvent(self, event: QMouseEvent):
        if self.pan_tool_active and event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = True
            self.pan_start_pos = event.position()
            self.pan_start_camera = QPointF(self.camera_pos.x(), self.camera_pos.y())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.start_pos is not None: return
            self.pan_start_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            return
        
        current_style = style_manager.current_style_name
        active_tool = self.get_active_drawing_tool()
        
        # Обработка инструментов рисования (ЛКМ)
        if active_tool and event.button() == Qt.MouseButton.LeftButton:
            # Сбрасываем выделение при начале рисования
            if self.selected_objects:
                self.selected_objects = []
                self.selection_changed.emit(self.selected_objects)
            
            # Сбрасываем панорамирование если было активно
            if self.pan_start_pos is not None:
                self.pan_start_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
            
            # Получаем позицию клика с учётом привязок
            if self.current_snap_point:
                click_scene_pos = QPointF(self.current_snap_point.x, self.current_snap_point.y)
            else:
                click_scene_pos = self.map_to_scene(event.position())
            
            if self.start_pos is None:
                # Первый клик - начало построения
                self.start_pos = event.position()
                self.current_pos = self.start_pos
                
                # Для методов с 3+ точками - сохраняем первую точку
                if active_tool == 'circle':
                    circle_method = "center_radius"
                    if self.circle_input_panel:
                        circle_method = self.circle_input_panel.get_current_method()
                    if circle_method == "three_points":
                        self.construction_points = [Point(click_scene_pos.x(), click_scene_pos.y())]
                
                elif active_tool == 'arc':
                    arc_method = "three_points"
                    if self.arc_input_panel:
                        arc_method = self.arc_input_panel.get_current_method()
                    if arc_method == "three_points":
                        # Для three_points: первая точка = начало дуги
                        self.construction_points = [Point(click_scene_pos.x(), click_scene_pos.y())]
                    elif arc_method == "center_angles":
                        # Для center_angles: первая точка = центр
                        self._arc_center = Point(click_scene_pos.x(), click_scene_pos.y())
                        self.construction_points = []
                
                self._update_line_info()
            else:
                # Второй клик - завершение построения
                start_scene_pos = self.map_to_scene(self.start_pos)
                
                if active_tool == 'line':
                    # Линия: от start до end
                    if self._current_construction_mode == "polar":
                        cursor_pos = self.current_pos if self.current_pos else event.position()
                        current_scene_pos = self.map_to_scene(cursor_pos)
                        end_point_qpoint = self._calculate_end_point_polar(start_scene_pos, current_scene_pos)
                        end_point = Point(end_point_qpoint.x(), end_point_qpoint.y())
                    else:
                        end_point = Point(click_scene_pos.x(), click_scene_pos.y())
                    
                    start_point = Point(start_scene_pos.x(), start_scene_pos.y())
                    obj = Line(start_point, end_point, style_name=current_style)
                    self.scene.add_object(obj)
                
                elif active_tool == 'circle':
                    # Получаем метод построения из панели
                    circle_method = "center_radius"
                    if self.circle_input_panel:
                        circle_method = self.circle_input_panel.get_current_method()
                    
                    click_point = Point(click_scene_pos.x(), click_scene_pos.y())
                    
                    if circle_method == "center_radius" or circle_method == "center_diameter":
                        # Центр и радиус/диаметр: первый клик = центр, второй = точка на окружности
                        center = Point(start_scene_pos.x(), start_scene_pos.y())
                        radius = center.distance_to(click_point)
                        if circle_method == "center_diameter":
                            # Второй клик - точка на окружности, но интерпретируем как точку на краю диаметра
                            radius = radius  # то же самое
                        if radius > 0:
                            obj = Circle(center, radius, style_name=current_style)
                            self.scene.add_object(obj)
                    
                    elif circle_method == "two_points":
                        # Две точки на диаметре
                        p1 = Point(start_scene_pos.x(), start_scene_pos.y())
                        p2 = click_point
                        obj = Circle.from_two_points(p1, p2, style_name=current_style)
                        self.scene.add_object(obj)
                    
                    elif circle_method == "three_points":
                        # Три точки: накапливаем
                        self.construction_points.append(click_point)
                        
                        if len(self.construction_points) < 3:
                            # Ещё не все точки
                            self.start_pos = event.position()
                            self.update()
                            return  # Не сбрасываем start_pos
                        else:
                            # Все 3 точки собраны
                            p1, p2, p3 = self.construction_points
                            try:
                                obj = Circle.from_three_points(p1, p2, p3, style_name=current_style)
                                self.scene.add_object(obj)
                            except ValueError as e:
                                print(f"Невозможно построить окружность: {e}")
                            self.construction_points = []
                
                elif active_tool == 'rectangle':
                    # Получаем метод построения из панели
                    rect_method = "two_points"
                    if self.rectangle_input_panel:
                        rect_method = self.rectangle_input_panel.get_current_method()
                    
                    click_point = Point(click_scene_pos.x(), click_scene_pos.y())
                    
                    if rect_method == "two_points":
                        # Две противоположные точки
                        p1 = Point(start_scene_pos.x(), start_scene_pos.y())
                        if p1.x != click_point.x and p1.y != click_point.y:
                            obj = Rectangle(p1, click_point, style_name=current_style)
                            self.scene.add_object(obj)
                    
                    elif rect_method == "center_size":
                        # Центр + размер (расстояние до курсора = полуширина/полувысота)
                        center = Point(start_scene_pos.x(), start_scene_pos.y())
                        half_w = abs(click_point.x - center.x)
                        half_h = abs(click_point.y - center.y)
                        if half_w > 0 and half_h > 0:
                            p1 = Point(center.x - half_w, center.y - half_h)
                            p2 = Point(center.x + half_w, center.y + half_h)
                            obj = Rectangle(p1, p2, style_name=current_style)
                            self.scene.add_object(obj)
                    
                    elif rect_method == "point_size":
                        # Точка + размер (курсор определяет размеры)
                        p1 = Point(start_scene_pos.x(), start_scene_pos.y())
                        width = click_point.x - p1.x
                        height = click_point.y - p1.y
                        if width != 0 and height != 0:
                            p2 = Point(p1.x + width, p1.y + height)
                            obj = Rectangle(p1, p2, style_name=current_style)
                            self.scene.add_object(obj)
                
                elif active_tool == 'ellipse':
                    # Получаем метод построения из панели
                    ellipse_method = "center_radii"
                    if self.ellipse_input_panel:
                        ellipse_method = self.ellipse_input_panel.get_current_method()
                    
                    center = Point(start_scene_pos.x(), start_scene_pos.y())
                    
                    if ellipse_method == "center_radii":
                        # Центр + радиусы определяются по смещению курсора
                        radius_x = abs(click_scene_pos.x() - center.x)
                        radius_y = abs(click_scene_pos.y() - center.y)
                        if radius_x > 0 and radius_y > 0:
                            obj = Ellipse(center, radius_x, radius_y, style_name=current_style)
                            self.scene.add_object(obj)
                    
                    elif ellipse_method == "center_axes":
                        # Центр и точки на осях: первый клик = X ось, второй = Y ось
                        if len(self.construction_points) == 0:
                            # Сохраняем радиус X
                            radius_x = abs(click_scene_pos.x() - center.x)
                            if radius_x > 0:
                                self._ellipse_radius_x = radius_x
                                self.construction_points.append(Point(click_scene_pos.x(), click_scene_pos.y()))
                                self.start_pos = event.position()
                                self.update()
                                return
                        else:
                            # Второй клик = радиус Y
                            radius_y = abs(click_scene_pos.y() - center.y)
                            if radius_y > 0:
                                obj = Ellipse(center, self._ellipse_radius_x, radius_y, style_name=current_style)
                                self.scene.add_object(obj)
                                self.construction_points = []
                
                elif active_tool == 'polygon':
                    # Многоугольник: center + radius
                    center = Point(start_scene_pos.x(), start_scene_pos.y())
                    radius = center.distance_to(Point(click_scene_pos.x(), click_scene_pos.y()))
                    if radius > 0:
                        # Получаем количество сторон из панели ввода
                        num_sides = 6
                        if self.polygon_input_panel:
                            num_sides = self.polygon_input_panel.get_num_sides()
                        obj = Polygon(center, radius, num_sides=num_sides, style_name=current_style)
                        self.scene.add_object(obj)
                
                elif active_tool == 'arc':
                    # Получаем метод построения из панели
                    arc_method = "three_points"
                    if self.arc_input_panel:
                        arc_method = self.arc_input_panel.get_current_method()
                    
                    click_point = Point(click_scene_pos.x(), click_scene_pos.y())
                    
                    if arc_method == "three_points":
                        # Три точки: Start -> End -> Point on Arc
                        # construction_points[0] = Start
                        # construction_points[1] = End
                        # click_point = Point on Arc
                        self.construction_points.append(click_point)
                        
                        if len(self.construction_points) < 3:
                            # Ещё не все точки
                            self.start_pos = event.position()
                            self.update()
                            return  # Не сбрасываем start_pos
                        else:
                            # Все 3 точки собраны: Start, End, Point_on_arc
                            p_start = self.construction_points[0]
                            p_end = self.construction_points[1]
                            p_on_arc = self.construction_points[2]
                            # Порядок для from_three_points: start, point_on_arc, end
                            arc = Arc.from_three_points(p_start, p_on_arc, p_end, style_name=current_style)
                            if arc:
                                self.scene.add_object(arc)
                            else:
                                print("Точки коллинеарны, невозможно построить дугу")
                            self.construction_points = []
                    
                    elif arc_method == "center_angles":
                        # Центр и углы:
                        # Первый клик = центр (уже сохранён в _arc_center)
                        # Второй клик = точка на окружности (радиус + начальный угол)
                        # Третий клик = конечная точка (конечный угол)
                        
                        if not hasattr(self, '_arc_center'):
                            return
                        
                        center = self._arc_center
                        radius = center.distance_to(click_point)
                        
                        import math
                        # Вычисляем угол от центра к точке клика
                        angle = math.degrees(math.atan2(
                            click_point.y - center.y, click_point.x - center.x
                        ))
                        
                        if len(self.construction_points) == 0:
                            # Второй клик - сохраняем начальный угол и радиус
                            self.construction_points.append(click_point)
                            self._arc_start_angle = angle
                            self._arc_radius = radius
                            self.start_pos = event.position()
                            self.update()
                            return
                        else:
                            # Третий клик - создаём дугу
                            start_angle = self._arc_start_angle
                            end_angle = angle
                            arc = Arc.from_center_and_angles(
                                self._arc_center,
                                self._arc_radius, start_angle, end_angle,
                                style_name=current_style,
                                shortest_path=True
                            )
                            self.scene.add_object(arc)
                            self.construction_points = []
                
                elif active_tool == 'spline':
                    # Сплайн: накапливаем точки. Завершение по ПКМ или Enter
                    if not hasattr(self, '_spline_points'):
                        self._spline_points = []
                    
                    self._spline_points.append(Point(click_scene_pos.x(), click_scene_pos.y()))
                    
                    # Обновляем счётчик точек в панели
                    if self.spline_input_panel:
                        self.spline_input_panel.update_points_count(len(self._spline_points))
                    
                    # Не сбрасываем start_pos для сплайна - продолжаем добавлять точки
                    self.start_pos = event.position()  # Обновляем для preview
                    self.update()
                    return  # Не сбрасываем start_pos
                
                # Сбрасываем состояние построения
                self.start_pos = None
                self.current_pos = None
                self.line_info_changed.emit("")
        
        # Отмена построения правой кнопкой мыши
        elif active_tool and event.button() == Qt.MouseButton.RightButton:
            if active_tool == 'spline' and hasattr(self, '_spline_points') and len(self._spline_points) >= 2:
                # Завершаем сплайн
                obj = Spline(self._spline_points, style_name=current_style)
                self.scene.add_object(obj)
                self._spline_points = []
            
            self.start_pos = None
            self.current_pos = None
            self.construction_points = []  # Сбрасываем накопленные точки
            self.line_info_changed.emit("")
            if hasattr(self, '_spline_points'):
                self._spline_points = []
            # Сбрасываем атрибуты дуги
            if hasattr(self, '_arc_center'):
                delattr(self, '_arc_center')
            if hasattr(self, '_arc_start_angle'):
                delattr(self, '_arc_start_angle')
            if hasattr(self, '_arc_radius'):
                delattr(self, '_arc_radius')
            # Сбрасываем атрибуты эллипса
            if hasattr(self, '_ellipse_radius_x'):
                delattr(self, '_ellipse_radius_x')
            # Обновляем панель сплайна
            if self.spline_input_panel:
                self.spline_input_panel.reset()
                
        # 2. Инструмент УДАЛЕНИЕ
        elif self.delete_tool_action.isChecked():
            if event.button() == Qt.MouseButton.LeftButton and self.highlighted_line:
                self.scene.remove_object(self.highlighted_line)
                self.highlighted_line = None
                
        # 3. Инструмент ВЫДЕЛЕНИЕ (если активен select_tool_action или никакой другой не активен)
        elif self.select_tool_action.isChecked() or (not self.pan_tool_active and not self.is_drawing_tool_active() and not self.delete_tool_action.isChecked()):
            if event.button() == Qt.MouseButton.LeftButton:
                clicked_object = self._get_object_at_cursor(event.position())
                
                is_ctrl_pressed = event.modifiers() & Qt.KeyboardModifier.ControlModifier
                
                if clicked_object:
                    if is_ctrl_pressed:
                        # Если нажат Ctrl - инвертируем выделение (добавляем/убираем)
                        if clicked_object in self.selected_objects:
                            self.selected_objects.remove(clicked_object)
                        else:
                            self.selected_objects.append(clicked_object)
                    else:
                        # Обычный клик - сбрасываем всё и выделяем один объект
                        self.selected_objects = [clicked_object]
                else:
                    # Клик по пустому месту - снимаем выделение
                    if not is_ctrl_pressed:
                        self.selected_objects = []
                
                # Сообщаем всем (в том числе Панели свойств), что выделение изменилось
                self.selection_changed.emit(self.selected_objects)
                
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
        
        # Всегда ищем линию под курсором для hover подсветки (независимо от инструмента)
        self._find_hover_line(event.position())
        
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
        
        # Обработка построения примитивов
        if self.start_pos:
            self.current_pos = event.position()
            
            # Поиск точки привязки
            self._update_snap_point(event.position())
            
            self._update_line_info()  # Обновляем информацию о линии при движении
            self.update()
        elif self.is_drawing_tool_active():
            # Если инструмент рисования активен, но построение ещё не начато - ищем привязки
            self._update_snap_point(event.position())

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
        painter.setRenderHint(QPainter.Antialiasing)  # Включаем сглаживание для красивых линий
        self._draw_grid(painter)
        self._draw_axes(painter)
        self._draw_scene_objects(painter)
        self._draw_selection(painter) # выделение объектов
        self._draw_hover_highlighted_line(painter)  # Рисуем hover подсветку (голубая)
        self._draw_highlighted_line(painter)  # Рисуем delete подсветку (красная)
        self._draw_preview(painter)
        self._draw_snap_indicator(painter)  # Рисуем индикатор привязки
        
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
        """
        Отрисовывает объекты сцены с учетом их стилей.
        """
        colors = settings.get("colors") or settings.defaults["colors"]
        # Цвет по умолчанию, если вдруг пригодится
        default_color = QColor(colors.get("line_object", "#FFFFFF"))
        
        # Получаем базовую толщину S из менеджера стилей
        base_width = style_manager.base_width

        for obj in self.scene.objects:
            # Пропускаем объекты для специальной отрисовки
            if obj == self.hover_highlighted_line:
                continue
            if obj == self.highlighted_line and self.delete_tool_action.isChecked():
                continue
            
            # Получаем стиль объекта
            style = style_manager.get_style(obj.style_name)
            
            # Создаем перо
            pen = QPen(default_color)
            pen_width = base_width * style.width_mult
            pen.setWidthF(pen_width)
            pen.setCosmetic(True)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            
            # Настраиваем паттерн
            if style.pattern and style.name not in ["Сплошная волнистая", "Сплошная с изломами"]:
                pen.setStyle(Qt.PenStyle.CustomDashLine)
                pen.setDashPattern(style.pattern)
            else:
                pen.setStyle(Qt.PenStyle.SolidLine)
            
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Отрисовка в зависимости от типа примитива
            if isinstance(obj, Line):
                self._draw_line(painter, obj, pen, pen_width)
            elif isinstance(obj, Circle):
                self._draw_circle(painter, obj, pen)
            elif isinstance(obj, Arc):
                self._draw_arc(painter, obj, pen)
            elif isinstance(obj, Rectangle):
                self._draw_rectangle(painter, obj, pen)
            elif isinstance(obj, Ellipse):
                self._draw_ellipse(painter, obj, pen)
            elif isinstance(obj, Polygon):
                self._draw_polygon(painter, obj, pen)
            elif isinstance(obj, Spline):
                self._draw_spline(painter, obj, pen)
    
    def _draw_line(self, painter: QPainter, obj: Line, pen: QPen, pen_width: float):
        """Отрисовывает отрезок."""
        style = style_manager.get_style(obj.style_name)
        start_screen = self.map_from_scene(QPointF(obj.start.x, obj.start.y))
        end_screen = self.map_from_scene(QPointF(obj.end.x, obj.end.y))

        if style.name == "Сплошная волнистая":
            amp = pen_width * 1.5 
            path = create_wavy_path(start_screen, end_screen, amplitude=amp, period=10)
            pen.setStyle(Qt.PenStyle.SolidLine) 
            painter.setPen(pen)
            painter.drawPath(path)
        elif style.name == "Сплошная с изломами":
            z_height = max(5.0, pen_width * 3.0) 
            z_width = z_height * 0.8
            path = create_zigzag_path(start_screen, end_screen, 
                                    zigzag_height=z_height, 
                                    zigzag_width=z_width, 
                                    period=150)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawPath(path)
        else:
            painter.drawLine(start_screen, end_screen)
    
    def _draw_circle(self, painter: QPainter, obj: Circle, pen: QPen):
        """Отрисовывает окружность."""
        center_screen = self.map_from_scene(QPointF(obj.center.x, obj.center.y))
        # Для радиуса нужно учесть zoom
        radius_screen = obj.radius * self.zoom_factor
        
        rect = QRectF(
            center_screen.x() - radius_screen,
            center_screen.y() - radius_screen,
            radius_screen * 2,
            radius_screen * 2
        )
        painter.drawEllipse(rect)
    
    def _draw_arc(self, painter: QPainter, obj: Arc, pen: QPen):
        """
        Отрисовывает дугу.
        
        Qt drawArc использует углы в 1/16 градуса.
        В Qt система координат Y направлена вниз, поэтому углы инвертируются.
        """
        center_screen = self.map_from_scene(QPointF(obj.center.x, obj.center.y))
        radius_screen = obj.radius * self.zoom_factor
        
        
        rect = QRectF(
            center_screen.x() - radius_screen,
            center_screen.y() - radius_screen,
            radius_screen * 2,
            radius_screen * 2
        )
        
        # Qt использует 1/16 градуса
        # Углы в obj уже математические (90 = 12ч), drawArc понимает их правильно в текущем контексте
        start_angle_qt = int(obj.start_angle * 16)
        span_angle_qt = int(obj.span_angle * 16)
        
        painter.drawArc(rect, start_angle_qt, span_angle_qt)
    
    def _draw_rectangle(self, painter: QPainter, obj: Rectangle, pen: QPen):
        """Отрисовывает прямоугольник."""
        # Преобразуем все 4 угла в экранные координаты
        corners = obj.corners
        screen_corners = [self.map_from_scene(QPointF(c.x, c.y)) for c in corners]
        
        # Рисуем 4 стороны
        for i in range(4):
            painter.drawLine(screen_corners[i], screen_corners[(i + 1) % 4])
    
    def _draw_ellipse(self, painter: QPainter, obj: Ellipse, pen: QPen):
        """Отрисовывает эллипс."""
        center_screen = self.map_from_scene(QPointF(obj.center.x, obj.center.y))
        radius_x_screen = obj.radius_x * self.zoom_factor
        radius_y_screen = obj.radius_y * self.zoom_factor
        
        rect = QRectF(
            center_screen.x() - radius_x_screen,
            center_screen.y() - radius_y_screen,
            radius_x_screen * 2,
            radius_y_screen * 2
        )
        painter.drawEllipse(rect)
    
    def _draw_polygon(self, painter: QPainter, obj: Polygon, pen: QPen):
        """Отрисовывает многоугольник."""
        vertices = obj.vertices
        screen_vertices = [self.map_from_scene(QPointF(v.x, v.y)) for v in vertices]
        
        # Рисуем все стороны
        for i in range(len(screen_vertices)):
            painter.drawLine(screen_vertices[i], screen_vertices[(i + 1) % len(screen_vertices)])
    
    def _draw_spline(self, painter: QPainter, obj: Spline, pen: QPen):
        """Отрисовывает сплайн."""
        curve_points = obj.get_curve_points()
        
        if len(curve_points) < 2:
            return
        
        # Создаём путь для плавной кривой
        path = QPainterPath()
        first_screen = self.map_from_scene(QPointF(curve_points[0].x, curve_points[0].y))
        path.moveTo(first_screen)
        
        for point in curve_points[1:]:
            screen_point = self.map_from_scene(QPointF(point.x, point.y))
            path.lineTo(screen_point)
        
        painter.drawPath(path)
    
    def _draw_selection(self, painter: QPainter):
        """Отрисовывает выделенные объекты поверх основных."""
        if not self.selected_objects:
            return

        # Перо для выделения: Оранжевый пунктир, рисуется поверх
        pen = QPen(QColor("#FFA500"))  # Orange
        pen.setWidth(2)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine) 

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        handle_size = 4
        handle_color = QColor("#FFA500")
        
        for obj in self.selected_objects:
            # Рисуем контур объекта пунктиром
            if isinstance(obj, Line):
                start_screen = self.map_from_scene(QPointF(obj.start.x, obj.start.y))
                end_screen = self.map_from_scene(QPointF(obj.end.x, obj.end.y))
                painter.drawLine(start_screen, end_screen)
            elif isinstance(obj, Circle):
                center_screen = self.map_from_scene(QPointF(obj.center.x, obj.center.y))
                radius_screen = obj.radius * self.zoom_factor
                rect = QRectF(
                    center_screen.x() - radius_screen,
                    center_screen.y() - radius_screen,
                    radius_screen * 2,
                    radius_screen * 2
                )
                painter.drawEllipse(rect)
            elif isinstance(obj, Arc):
                center_screen = self.map_from_scene(QPointF(obj.center.x, obj.center.y))
                radius_screen = obj.radius * self.zoom_factor
                rect = QRectF(
                    center_screen.x() - radius_screen,
                    center_screen.y() - radius_screen,
                    radius_screen * 2,
                    radius_screen * 2
                )
                start_angle_qt = int(obj.start_angle * 16)
                span_angle_qt = int(obj.span_angle * 16)
                painter.drawArc(rect, start_angle_qt, span_angle_qt)
            elif isinstance(obj, Rectangle):
                corners = obj.corners
                screen_corners = [self.map_from_scene(QPointF(c.x, c.y)) for c in corners]
                for i in range(4):
                    painter.drawLine(screen_corners[i], screen_corners[(i + 1) % 4])
            elif isinstance(obj, Ellipse):
                center_screen = self.map_from_scene(QPointF(obj.center.x, obj.center.y))
                radius_x_screen = obj.radius_x * self.zoom_factor
                radius_y_screen = obj.radius_y * self.zoom_factor
                rect = QRectF(
                    center_screen.x() - radius_x_screen,
                    center_screen.y() - radius_y_screen,
                    radius_x_screen * 2,
                    radius_y_screen * 2
                )
                painter.drawEllipse(rect)
            elif isinstance(obj, Polygon):
                vertices = obj.vertices
                screen_vertices = [self.map_from_scene(QPointF(v.x, v.y)) for v in vertices]
                for i in range(len(screen_vertices)):
                    painter.drawLine(screen_vertices[i], screen_vertices[(i + 1) % len(screen_vertices)])
            elif isinstance(obj, Spline):
                curve_points = obj.get_curve_points()
                if len(curve_points) >= 2:
                    path = QPainterPath()
                    first_screen = self.map_from_scene(QPointF(curve_points[0].x, curve_points[0].y))
                    path.moveTo(first_screen)
                    for point in curve_points[1:]:
                        screen_point = self.map_from_scene(QPointF(point.x, point.y))
                        path.lineTo(screen_point)
                    painter.drawPath(path)
            
            # Рисуем контрольные точки (ручки) для редактирования
            control_points = obj.get_control_points()
            for cp in control_points:
                cp_screen = self.map_from_scene(QPointF(cp.x, cp.y))
                painter.fillRect(
                    int(cp_screen.x() - handle_size), 
                    int(cp_screen.y() - handle_size), 
                    handle_size * 2, 
                    handle_size * 2, 
                    handle_color
                )

    def _draw_preview(self, painter: QPainter):
        """Отрисовывает превью примитива при построении."""
        if not self.start_pos or not self.current_pos:
            return
        
        pen = QPen(QColor("#7A86CC"), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        active_tool = self.get_active_drawing_tool()
        
        start_scene_pos = self.map_to_scene(self.start_pos)
        current_scene_pos = self.map_to_scene(self.current_pos)
        
        if active_tool == 'line':
            if self._current_construction_mode == "polar":
                end_point = self._calculate_end_point_polar(start_scene_pos, current_scene_pos)
                end_screen = self.map_from_scene(end_point)
                painter.drawLine(self.start_pos.toPoint(), end_screen.toPoint())
            else:
                painter.drawLine(self.start_pos.toPoint(), self.current_pos.toPoint())
        
        elif active_tool == 'circle':
            # Получаем метод построения
            circle_method = "center_radius"
            if self.circle_input_panel:
                circle_method = self.circle_input_panel.get_current_method()
            
            if circle_method in ("center_radius", "center_diameter"):
                # Окружность: start = центр, current = точка на окружности
                center_screen = self.start_pos
                radius = math.sqrt(
                    (self.current_pos.x() - self.start_pos.x()) ** 2 +
                    (self.current_pos.y() - self.start_pos.y()) ** 2
                )
                rect = QRectF(
                    center_screen.x() - radius,
                    center_screen.y() - radius,
                    radius * 2,
                    radius * 2
                )
                painter.drawEllipse(rect)
                painter.drawLine(self.start_pos.toPoint(), self.current_pos.toPoint())
            
            elif circle_method == "two_points":
                # Две точки = диаметр
                p1_screen = self.start_pos
                p2_screen = self.current_pos
                center_x = (p1_screen.x() + p2_screen.x()) / 2
                center_y = (p1_screen.y() + p2_screen.y()) / 2
                radius = math.sqrt(
                    (p2_screen.x() - p1_screen.x()) ** 2 +
                    (p2_screen.y() - p1_screen.y()) ** 2
                ) / 2
                rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
                painter.drawEllipse(rect)
                painter.drawLine(p1_screen.toPoint(), p2_screen.toPoint())
            
            elif circle_method == "three_points":
                # Рисуем уже собранные точки и линии между ними
                all_points = list(self.construction_points)
                if len(all_points) > 0:
                    # Добавляем текущую позицию курсора
                    current_pt = Point(current_scene_pos.x(), current_scene_pos.y())
                    all_points.append(current_pt)
                    
                    # Рисуем точки
                    for pt in all_points:
                        screen_pt = self.map_from_scene(QPointF(pt.x, pt.y))
                        painter.drawEllipse(screen_pt, 4, 4)
                    
                    # Если есть 3 точки - пытаемся нарисовать окружность
                    if len(all_points) >= 3:
                        try:
                            temp_circle = Circle.from_three_points(all_points[0], all_points[1], all_points[2])
                            center_screen = self.map_from_scene(QPointF(temp_circle.center.x, temp_circle.center.y))
                            radius_screen = temp_circle.radius * self.zoom_factor
                            rect = QRectF(
                                center_screen.x() - radius_screen,
                                center_screen.y() - radius_screen,
                                radius_screen * 2,
                                radius_screen * 2
                            )
                            painter.drawEllipse(rect)
                        except:
                            # Если точки на одной прямой - просто рисуем линии между ними
                            for i in range(len(all_points) - 1):
                                p1_screen = self.map_from_scene(QPointF(all_points[i].x, all_points[i].y))
                                p2_screen = self.map_from_scene(QPointF(all_points[i+1].x, all_points[i+1].y))
                                painter.drawLine(p1_screen.toPoint(), p2_screen.toPoint())
        
        elif active_tool == 'rectangle':
            # Получаем метод построения
            rect_method = "two_points"
            if self.rectangle_input_panel:
                rect_method = self.rectangle_input_panel.get_current_method()
            
            if rect_method == "two_points" or rect_method == "point_size":
                # Две противоположные точки или точка+размер
                x1, y1 = self.start_pos.x(), self.start_pos.y()
                x2, y2 = self.current_pos.x(), self.current_pos.y()
                rect = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                painter.drawRect(rect)
            
            elif rect_method == "center_size":
                # Центр + размер
                cx, cy = self.start_pos.x(), self.start_pos.y()
                half_w = abs(self.current_pos.x() - cx)
                half_h = abs(self.current_pos.y() - cy)
                rect = QRectF(cx - half_w, cy - half_h, half_w * 2, half_h * 2)
                painter.drawRect(rect)
                # Рисуем центр
                painter.drawEllipse(self.start_pos, 3, 3)
        
        elif active_tool == 'ellipse':
            # Получаем метод построения
            ellipse_method = "center_radii"
            if self.ellipse_input_panel:
                ellipse_method = self.ellipse_input_panel.get_current_method()
            
            center_screen = self.start_pos
            
            if ellipse_method == "center_radii":
                # Эллипс: start = центр, current определяет радиусы
                radius_x = abs(self.current_pos.x() - center_screen.x())
                radius_y = abs(self.current_pos.y() - center_screen.y())
                rect = QRectF(
                    center_screen.x() - radius_x,
                    center_screen.y() - radius_y,
                    radius_x * 2,
                    radius_y * 2
                )
                painter.drawEllipse(rect)
            
            elif ellipse_method == "center_axes":
                # Центр и точки на осях
                if len(self.construction_points) == 0:
                    # Первый этап: рисуем радиус X
                    radius_x = abs(self.current_pos.x() - center_screen.x())
                    painter.drawLine(center_screen.toPoint(), self.current_pos.toPoint())
                    # Рисуем круг с текущим радиусом X
                    rect = QRectF(
                        center_screen.x() - radius_x,
                        center_screen.y() - radius_x,
                        radius_x * 2,
                        radius_x * 2
                    )
                    painter.drawEllipse(rect)
                else:
                    # Второй этап: рисуем эллипс
                    radius_x = getattr(self, '_ellipse_radius_x', 50) * self.zoom_factor
                    radius_y = abs(self.current_pos.y() - center_screen.y())
                    rect = QRectF(
                        center_screen.x() - radius_x,
                        center_screen.y() - radius_y,
                        radius_x * 2,
                        radius_y * 2
                    )
                    painter.drawEllipse(rect)
        
        elif active_tool == 'polygon':
            # Многоугольник: start = центр, current определяет радиус
            center = Point(start_scene_pos.x(), start_scene_pos.y())
            current_pt = Point(current_scene_pos.x(), current_scene_pos.y())
            radius = center.distance_to(current_pt)
            if radius > 0:
                # Получаем количество сторон из панели
                num_sides = 6
                if self.polygon_input_panel:
                    num_sides = self.polygon_input_panel.get_num_sides()
                
                temp_polygon = Polygon(center, radius, num_sides=num_sides)
                vertices = temp_polygon.vertices
                screen_vertices = [self.map_from_scene(QPointF(v.x, v.y)) for v in vertices]
                for i in range(len(screen_vertices)):
                    painter.drawLine(screen_vertices[i], screen_vertices[(i + 1) % len(screen_vertices)])
        
        elif active_tool == 'arc':
            # Получаем метод построения
            arc_method = "three_points"
            if self.arc_input_panel:
                arc_method = self.arc_input_panel.get_current_method()
            
            if arc_method == "three_points":
                # Логика построения по ТЗ: P_start -> P_end -> P_on_arc
                # Этап 1 (1 точка): рисуем линию-резинку от Start к курсору (это превью хорды)
                # Этап 2 (2 точки): прямая исчезает, рисуем дугу через Start, End и курсор
                #                   курсор = точка НА дуге (дуга "приклеена" к курсору)
                
                current_pt = Point(current_scene_pos.x(), current_scene_pos.y())
                
                if len(self.construction_points) == 1:
                    # Этап 1: Определение хорды
                    # Пользователь видит прямую линию от Start к курсору
                    p_start = self.construction_points[0]
                    p_start_screen = self.map_from_scene(QPointF(p_start.x, p_start.y))
                    
                    # Маркер начальной точки (Start) - красный квадрат
                    marker_pen = QPen(QColor("#FF6B6B"), 2)
                    marker_pen.setCosmetic(True)
                    painter.setPen(marker_pen)
                    painter.drawRect(int(p_start_screen.x()) - 4, int(p_start_screen.y()) - 4, 8, 8)
                    
                    # Линия-резинка до курсора (сплошная тонкая)
                    line_pen = QPen(QColor("#7A86CC"), 1, Qt.PenStyle.SolidLine)
                    line_pen.setCosmetic(True)
                    painter.setPen(line_pen)
                    painter.drawLine(p_start_screen.toPoint(), self.current_pos.toPoint())
                
                elif len(self.construction_points) == 2:
                    # Этап 2: Изгиб дуги
                    # Отрезок P1-P2 фиксирован, курсор "оттягивает" дугу как тетиву лука
                    p_start = self.construction_points[0]  # Start (первый клик)
                    p_end = self.construction_points[1]    # End (второй клик)
                    p_on_arc = current_pt                  # Точка НА дуге = курсор
                    
                    # Экранные координаты фиксированных точек
                    p_start_screen = self.map_from_scene(QPointF(p_start.x, p_start.y))
                    p_end_screen = self.map_from_scene(QPointF(p_end.x, p_end.y))
                    
                    # Маркеры фиксированных точек (Start и End)
                    marker_pen = QPen(QColor("#FF6B6B"), 2)
                    marker_pen.setCosmetic(True)
                    painter.setPen(marker_pen)
                    painter.drawRect(int(p_start_screen.x()) - 4, int(p_start_screen.y()) - 4, 8, 8)
                    painter.drawRect(int(p_end_screen.x()) - 4, int(p_end_screen.y()) - 4, 8, 8)
                    
                    # Пробуем построить дугу через 3 точки: Start, Point_on_arc, End
                    # Порядок аргументов: p1=Start, p2=PointOnArc, p3=End
                    temp_arc = Arc.from_three_points(p_start, p_on_arc, p_end)
                    
                    if temp_arc:
                        # Дуга успешно построена - рисуем её
                        # Устанавливаем перо для preview дуги
                        arc_pen = QPen(QColor("#7A86CC"), 2, Qt.PenStyle.SolidLine)
                        arc_pen.setCosmetic(True)
                        painter.setPen(arc_pen)
                        self._draw_arc_preview(painter, temp_arc)
                    else:
                        # Точки коллинеарны (радиус = бесконечность)
                        # Рисуем прямую линию вместо дуги
                        line_pen = QPen(QColor("#7A86CC"), 1, Qt.PenStyle.SolidLine)
                        line_pen.setCosmetic(True)
                        painter.setPen(line_pen)
                        painter.drawLine(p_start_screen.toPoint(), p_end_screen.toPoint())
            
            elif arc_method == "center_angles":
                # Центр + радиус + углы
                # Используем сохранённый центр
                if not hasattr(self, '_arc_center'):
                    return
                
                center = self._arc_center
                center_screen = self.map_from_scene(QPointF(center.x, center.y))
                current_pt = Point(current_scene_pos.x(), current_scene_pos.y())
                
                # Рисуем центр
                painter.drawEllipse(center_screen, 4, 4)
                
                if len(self.construction_points) == 0:
                    # Первый этап: показываем окружность и радиус к курсору
                    radius = center.distance_to(current_pt)
                    if radius > 0:
                        radius_screen = radius * self.zoom_factor
                        rect = QRectF(
                            center_screen.x() - radius_screen,
                            center_screen.y() - radius_screen,
                            radius_screen * 2,
                            radius_screen * 2
                        )
                        painter.drawEllipse(rect)
                        painter.drawLine(center_screen.toPoint(), self.current_pos.toPoint())
                else:
                    # Второй этап: показываем дугу от начальной точки до курсора
                    start_angle = getattr(self, '_arc_start_angle', 0)
                    radius = getattr(self, '_arc_radius', 0)
                    
                    if radius > 0:
                        # Угол к текущей позиции курсора
                        current_angle = math.degrees(math.atan2(
                            current_pt.y - center.y, current_pt.x - center.x
                        ))
                        
                        # Создаём временную дугу для превью
                        temp_arc = Arc.from_center_and_angles(center, radius, start_angle, current_angle, shortest_path=True)
                        self._draw_arc_preview(painter, temp_arc)
                        
                        # Рисуем радиус к начальной точке
                        start_pt = self.construction_points[0]
                        start_screen = self.map_from_scene(QPointF(start_pt.x, start_pt.y))
                        painter.drawLine(center_screen.toPoint(), start_screen.toPoint())
                        painter.drawEllipse(start_screen, 4, 4)
                        
                        # Рисуем радиус к текущей позиции
                        painter.drawLine(center_screen.toPoint(), self.current_pos.toPoint())
        
        elif active_tool == 'spline':
            # Сплайн: рисуем накопленные точки и текущую
            if hasattr(self, '_spline_points') and self._spline_points:
                # Рисуем уже добавленные точки
                for i, pt in enumerate(self._spline_points):
                    screen_pt = self.map_from_scene(QPointF(pt.x, pt.y))
                    painter.drawEllipse(screen_pt, 3, 3)
                    if i > 0:
                        prev_pt = self._spline_points[i - 1]
                        prev_screen = self.map_from_scene(QPointF(prev_pt.x, prev_pt.y))
                        painter.drawLine(prev_screen.toPoint(), screen_pt.toPoint())
                
                # Рисуем линию от последней точки к курсору
                last_pt = self._spline_points[-1]
                last_screen = self.map_from_scene(QPointF(last_pt.x, last_pt.y))
                painter.drawLine(last_screen.toPoint(), self.current_pos.toPoint())
    
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
    
    def _draw_arc_preview(self, painter: QPainter, arc: Arc):
        """Рисует превью дуги."""
        center_screen = self.map_from_scene(QPointF(arc.center.x, arc.center.y))
        radius_screen = arc.radius * self.zoom_factor
        rect = QRectF(
            center_screen.x() - radius_screen,
            center_screen.y() - radius_screen,
            radius_screen * 2,
            radius_screen * 2
        )
        # Qt drawArc: углы в 1/16 градуса
        start_angle_qt = int(arc.start_angle * 16)
        span_angle_qt = int(arc.span_angle * 16)
        painter.drawArc(rect, start_angle_qt, span_angle_qt)
    
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
        Находит ближайшую линию к курсору и устанавливает её как выделенную (для режима удаления).
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
    
    def _find_hover_line(self, cursor_pos: QPointF):
        """
        Находит ближайшую линию к курсору для hover подсветки (голубая).
        Работает независимо от активного инструмента.
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
        
        # Обновляем hover линию только если она изменилась
        if nearest_line != self.hover_highlighted_line:
            self.hover_highlighted_line = nearest_line
            self.update()
    
    def _draw_hover_highlighted_line(self, painter: QPainter):
        """Отрисовывает линию с hover подсветкой голубым цветом."""
        if self.hover_highlighted_line:
            pen = QPen(QColor("#7ACCCC"), 3)  # Голубой цвет, толщина 3
            pen.setCosmetic(True)           # Корректная толщина при зуме
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            
            start_screen = self.map_from_scene(QPointF(self.hover_highlighted_line.start.x, 
                                                        self.hover_highlighted_line.start.y))
            end_screen = self.map_from_scene(QPointF(self.hover_highlighted_line.end.x, 
                                                      self.hover_highlighted_line.end.y))
            # Рисуем одной командой вместо цикла Брезенхэма
            painter.drawLine(start_screen, end_screen)
    
    def _draw_highlighted_line(self, painter: QPainter):
        """Отрисовывает выделенную линию красным цветом."""
        if self.highlighted_line and self.delete_tool_action.isChecked():
            pen = QPen(QColor("#FF4444"), 3)
            pen.setCosmetic(True)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            
            start_screen = self.map_from_scene(QPointF(self.highlighted_line.start.x, 
                                                       self.highlighted_line.start.y))
            end_screen = self.map_from_scene(QPointF(self.highlighted_line.end.x, 
                                                     self.highlighted_line.end.y))
            painter.drawLine(start_screen, end_screen)
    
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
        Учитывает текущий поворот вида при вычислении zoom.
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
        
        # Вычисляем размеры bounding box в сценовых координатах
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
        
        # Вычисляем эффективные размеры экрана в сценовых координатах с учетом поворота
        # При повороте на 90° или 270° ширина и высота экрана меняются местами
        angle_rad = math.radians(self.rotation_angle)
        cos_angle = abs(math.cos(angle_rad))
        sin_angle = abs(math.sin(angle_rad))
        
        # Эффективная ширина и высота экрана в сценовых координатах
        # Используем формулу для вращающегося прямоугольника:
        # effective_width = width * |cos(angle)| + height * |sin(angle)|
        # effective_height = width * |sin(angle)| + height * |cos(angle)|
        effective_screen_width = self.width() * cos_angle + self.height() * sin_angle
        effective_screen_height = self.width() * sin_angle + self.height() * cos_angle
        
        # Вычисляем необходимый zoom для вмещения bbox
        zoom_x = effective_screen_width / bbox_width
        zoom_y = effective_screen_height / bbox_height
        
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
        
        # Отправляем сигнал об изменении zoom (будет обновляться во время анимации)
        self.zoom_changed.emit(self.target_zoom_factor)
    
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
        
        # Добавляем подменю "Вид" (всегда присутствует)
        view_submenu = self._create_view_submenu()
        menu.addMenu(view_submenu)
        
        # Проверяем, есть ли объект под курсором (используем hover_highlighted_line)
        if self.hover_highlighted_line:
            # Добавляем разделитель перед командами объекта
            menu.addSeparator()
            
            # Добавляем команду "Удалить"
            delete_action = menu.addAction("Удалить")
            delete_action.setIcon(load_svg_icon("public/delete.svg"))
            delete_action.triggered.connect(self._on_context_menu_delete)
            
            # ===== Место для будущих команд работы с объектами =====
            # Примеры команд, которые можно добавить:
            # - Изменить... (редактирование свойств объекта)
            # - Копировать (копирование объекта)
            # - Свойства... (диалог со свойствами объекта)
            # 
            # Пример добавления команды:
            # edit_action = menu.addAction("Изменить...")
            # edit_action.setIcon(load_svg_icon("public/edit.svg"))
            # edit_action.triggered.connect(lambda: self._on_edit_object(self.hover_highlighted_line))
        
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
    
    def _on_context_menu_delete(self):
        """
        Обработчик удаления объекта из контекстного меню.
        Удаляет hover_highlighted_line из сцены.
        """
        if self.hover_highlighted_line:
            self.scene.remove_object(self.hover_highlighted_line)
            self.hover_highlighted_line = None
            self.update()
    
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
        
        # Проверяем все объекты сцены на попадание
        nearest_object = None
        # Толерантность в сценовых координатах (учитываем zoom)
        tolerance = self.selection_threshold / self.zoom_factor
        min_distance = tolerance
        
        for obj in self.scene.objects:
            # Используем унифицированный метод distance_to_point из GeometricPrimitive
            distance = obj.distance_to_point(scene_cursor_pos.x(), scene_cursor_pos.y())
            
            if distance < min_distance:
                min_distance = distance
                nearest_object = obj
        
        return nearest_object
    
    def _update_snap_point(self, screen_pos: QPointF):
        """
        Ищет ближайшую точку привязки к позиции курсора.
        Обновляет self.current_snap_point.
        """
        if not snap_manager.enabled:
            self.current_snap_point = None
            return
        
        scene_pos = self.map_to_scene(screen_pos)
        tolerance = snap_manager.snap_radius / self.zoom_factor
        
        snap_point = snap_manager.find_snap(
            scene_pos.x(), scene_pos.y(),
            self.scene.objects,
            tolerance
        )
        
        # Обновляем только если изменилось
        if snap_point != self.current_snap_point:
            self.current_snap_point = snap_point
            self.update()
    
    def _draw_snap_indicator(self, painter: QPainter):
        """
        Отрисовывает индикатор текущей точки привязки.
        Разные типы привязок отображаются разными символами.
        """
        if not self.current_snap_point or not snap_manager.enabled:
            return
        
        sp = self.current_snap_point
        screen_pos = self.map_from_scene(QPointF(sp.x, sp.y))
        x, y = int(screen_pos.x()), int(screen_pos.y())
        size = 8  # Размер индикатора в пикселях
        
        # Цвет индикатора - яркий жёлтый/золотой
        snap_color = QColor("#FFD700")
        pen = QPen(snap_color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Рисуем разные символы в зависимости от типа привязки
        if sp.snap_type == SnapType.ENDPOINT:
            # Квадрат для конечных точек
            painter.drawRect(x - size, y - size, size * 2, size * 2)
        elif sp.snap_type == SnapType.MIDPOINT:
            # Треугольник для середины
            from PySide6.QtGui import QPolygonF
            triangle = QPolygonF([
                QPointF(x, y - size),
                QPointF(x - size, y + size),
                QPointF(x + size, y + size)
            ])
            painter.drawPolygon(triangle)
        elif sp.snap_type == SnapType.CENTER:
            # Круг с крестом для центра
            painter.drawEllipse(x - size, y - size, size * 2, size * 2)
            painter.drawLine(x - size//2, y, x + size//2, y)
            painter.drawLine(x, y - size//2, x, y + size//2)
        elif sp.snap_type == SnapType.QUADRANT:
            # Ромб для квадрантов
            from PySide6.QtGui import QPolygonF
            diamond = QPolygonF([
                QPointF(x, y - size),
                QPointF(x + size, y),
                QPointF(x, y + size),
                QPointF(x - size, y)
            ])
            painter.drawPolygon(diamond)
        elif sp.snap_type == SnapType.NODE:
            # Крест для узлов (сплайн)
            painter.drawLine(x - size, y - size, x + size, y + size)
            painter.drawLine(x - size, y + size, x + size, y - size)
        elif sp.snap_type == SnapType.INTERSECTION:
            # X для пересечений
            painter.drawLine(x - size, y - size, x + size, y + size)
            painter.drawLine(x - size, y + size, x + size, y - size)
        elif sp.snap_type == SnapType.PERPENDICULAR:
            # Перпендикуляр (угол 90°)
            painter.drawLine(x - size, y, x, y)
            painter.drawLine(x, y, x, y - size)
        elif sp.snap_type == SnapType.TANGENT:
            # Касательная (круг с линией)
            painter.drawEllipse(x - size//2, y - size//2, size, size)
            painter.drawLine(x - size, y + size//2, x + size, y + size//2)
        else:
            # По умолчанию - круг
            painter.drawEllipse(x - size, y - size, size * 2, size * 2)
    
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
        
        # Отправляем сигналы об изменении zoom и rotation
        self.zoom_changed.emit(self.zoom_factor)
        self.rotation_changed.emit(self.rotation_angle)
        
        self.update()