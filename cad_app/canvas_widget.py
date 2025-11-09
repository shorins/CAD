"""Refactored canvas widget using modular components."""

import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QMouseEvent, QKeyEvent, QContextMenuEvent
from PySide6.QtCore import Qt, QPointF, Signal

from .core.scene import Scene
from .canvas.view_transform import ViewTransform
from .canvas.animations.zoom_animation import ZoomAnimation
from .canvas.animations.rotation_animation import RotationAnimation
from .canvas.renderers.grid_renderer import GridRenderer
from .canvas.renderers.axes_renderer import AxesRenderer
from .canvas.renderers.object_renderer import ObjectRenderer
from .canvas.renderers.indicator_renderer import IndicatorRenderer
from .canvas.tools.line_tool import LineTool
from .canvas.tools.delete_tool import DeleteTool
from .canvas.tools.pan_tool import PanTool
from .canvas.selection import SelectionManager
from .canvas.context_menu import ContextMenuBuilder
from .settings import settings


class CanvasWidget(QWidget):
    """Refactored canvas widget using modular components."""
    
    cursor_pos_changed = Signal(QPointF)
    line_info_changed = Signal(str)
    zoom_changed = Signal(float)
    rotation_changed = Signal(float)

    def __init__(self, scene: Scene, action_manager, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.scene.scene_changed.connect(self.update)
        settings.settings_changed.connect(self.on_settings_changed)
        
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Create core components
        self.view_transform = ViewTransform(self.size())
        self.zoom_animation = ZoomAnimation(self.view_transform, self)
        self.rotation_animation = RotationAnimation(self.view_transform, self)
        self.selection_manager = SelectionManager(self.view_transform)
        self.context_menu_builder = ContextMenuBuilder(self)
        
        # Create renderers
        self.grid_renderer = GridRenderer(self.view_transform)
        self.axes_renderer = AxesRenderer(self.view_transform)
        self.object_renderer = ObjectRenderer(self.view_transform)
        self.indicator_renderer = IndicatorRenderer()
        
        # Create tools
        self.tools = {
            'line': LineTool(self),
            'delete': DeleteTool(self),
            'pan': PanTool(self)
        }
        self.current_tool = self.tools['line']
        self.current_tool.activate()
        
        # Store action references for tool switching
        self.action_manager = action_manager
        self.line_tool_action = action_manager.get_action('line_tool')
        self.delete_tool_action = action_manager.get_action('delete_tool')
        self.pan_tool_action = action_manager.get_action('pan_tool')
        
        # Connect tool actions to tool switching
        self.line_tool_action.toggled.connect(lambda checked: self._switch_tool('line') if checked else None)
        self.delete_tool_action.toggled.connect(lambda checked: self._switch_tool('delete') if checked else None)
        self.pan_tool_action.toggled.connect(lambda checked: self._switch_tool('pan') if checked else None)
        
        # Connect animation signals
        self.zoom_animation.zoom_changed.connect(self.zoom_changed.emit)
        self.zoom_animation.zoom_changed.connect(lambda: self.update())
        self.rotation_animation.rotation_changed.connect(self.rotation_changed.emit)
        self.rotation_animation.rotation_changed.connect(lambda: self.update())
        
        # Keyboard state
        self.r_key_pressed = False
        
        # Zoom parameters
        self.zoom_step = 1.15
        
        self.on_settings_changed()
        
        # Emit initial values
        self.zoom_changed.emit(self.view_transform.zoom_factor)
        self.rotation_changed.emit(self.view_transform.rotation_angle)
    
    def _switch_tool(self, tool_name: str) -> None:
        """Переключает активный инструмент."""
        if self.current_tool:
            self.current_tool.deactivate()
        
        self.current_tool = self.tools.get(tool_name)
        if self.current_tool:
            self.current_tool.activate()
        
        self.update()
    
    def on_settings_changed(self) -> None:
        """Обработчик изменения настроек."""
        colors = settings.get("colors") or settings.defaults["colors"]
        bg_color = colors.get("canvas_bg", "#2D2D2D")
        self.setStyleSheet(f"background-color: {bg_color};")
        
        # Уведомляем line tool об изменении режима построения
        if isinstance(self.current_tool, LineTool):
            self.current_tool.on_construction_mode_changed()
        
        self.update()
    
    def on_construction_mode_changed(self) -> None:
        """Обработчик изменения режима построения линии."""
        if isinstance(self.current_tool, LineTool):
            self.current_tool.on_construction_mode_changed()
    
    def resizeEvent(self, event) -> None:
        """Обработчик изменения размера виджета."""
        super().resizeEvent(event)
        self.view_transform.update_widget_size(self.size())
    
    def map_to_scene(self, screen_pos: QPointF) -> QPointF:
        """Делегирует преобразование координат в ViewTransform."""
        return self.view_transform.map_to_scene(screen_pos)
    
    def map_from_scene(self, scene_pos: QPointF) -> QPointF:
        """Делегирует преобразование координат в ViewTransform."""
        return self.view_transform.map_from_scene(scene_pos)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Обрабатывает нажатие клавиш."""
        # Обработка клавиши R для поворота
        if event.key() == Qt.Key.Key_R:
            self.r_key_pressed = True
            event.accept()
            return
        
        # Обработка комбинаций R + Arrow keys для поворота
        if self.r_key_pressed:
            if event.key() == Qt.Key.Key_Left:
                self.rotation_animation.start_rotation(clockwise=True)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Right:
                self.rotation_animation.start_rotation(clockwise=False)
                event.accept()
                return
        
        # Делегируем обработку текущему инструменту
        if self.current_tool and self.current_tool.key_press(event):
            self.update()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """Обрабатывает отпускание клавиш."""
        if event.key() == Qt.Key.Key_R:
            self.r_key_pressed = False
            event.accept()
        else:
            super().keyReleaseEvent(event)
    
    def wheelEvent(self, event) -> None:
        """Обрабатывает события колеса мыши для масштабирования."""
        delta = event.angleDelta().y()
        
        if delta == 0:
            return
        
        # Вычисляем новый target zoom
        current_target = self.zoom_animation.target_zoom
        if delta > 0:
            new_target = current_target * self.zoom_step
        else:
            new_target = current_target / self.zoom_step
        
        # Запускаем анимацию zoom
        self.zoom_animation.start_zoom(new_target, event.position())
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Обрабатывает нажатие кнопки мыши."""
        # Панорамирование средней кнопкой (независимо от инструмента)
        if event.button() == Qt.MouseButton.MiddleButton:
            # Временно активируем pan для средней кнопки
            if not isinstance(self.current_tool, PanTool):
                self._temp_pan_active = True
                # Сохраняем текущий курсор
                self._saved_cursor = self.cursor()
                # Создаем временный MouseEvent с левой кнопкой для pan tool
                from PySide6.QtGui import QMouseEvent as QME
                from PySide6.QtCore import QEvent
                temp_event = QME(
                    QEvent.Type.MouseButtonPress,
                    event.position(),
                    event.globalPosition(),
                    Qt.MouseButton.LeftButton,  # Pan tool ожидает левую кнопку
                    Qt.MouseButton.LeftButton,
                    event.modifiers()
                )
                self.tools['pan'].mouse_press(temp_event)
                # Устанавливаем курсор зажатой руки
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                return
        
        # Делегируем обработку текущему инструменту
        if self.current_tool and self.current_tool.mouse_press(event):
            self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Обрабатывает движение мыши."""
        # Отправляем сигнал об изменении позиции курсора
        self.cursor_pos_changed.emit(event.position())
        
        # Обработка временного pan средней кнопкой
        if hasattr(self, '_temp_pan_active') and self._temp_pan_active:
            if self.tools['pan'].mouse_move(event):
                self.update()
            return
        
        # Обновляем hover объект
        if self.selection_manager.update_hover(event.position(), self.scene):
            self.update()
        
        # Делегируем обработку текущему инструменту
        if self.current_tool and self.current_tool.mouse_move(event):
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Обрабатывает отпускание кнопки мыши."""
        # Обработка временного pan средней кнопкой
        if event.button() == Qt.MouseButton.MiddleButton:
            if hasattr(self, '_temp_pan_active') and self._temp_pan_active:
                # Создаем временный MouseEvent с левой кнопкой для pan tool
                from PySide6.QtGui import QMouseEvent as QME
                from PySide6.QtCore import QEvent
                temp_event = QME(
                    QEvent.Type.MouseButtonRelease,
                    event.position(),
                    event.globalPosition(),
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.NoButton,
                    event.modifiers()
                )
                self.tools['pan'].mouse_release(temp_event)
                self._temp_pan_active = False
                # Восстанавливаем сохранённый курсор
                if hasattr(self, '_saved_cursor'):
                    self.setCursor(self._saved_cursor)
                else:
                    # Если курсор не был сохранён, восстанавливаем курсор текущего инструмента
                    if self.current_tool:
                        self.current_tool.deactivate()
                        self.current_tool.activate()
                return
        
        # Делегируем обработку текущему инструменту
        if self.current_tool and self.current_tool.mouse_release(event):
            self.update()
    
    def paintEvent(self, event) -> None:
        """Отрисовывает canvas."""
        painter = QPainter(self)
        
        # Рисуем сетку
        self.grid_renderer.render(painter, self.size())
        
        # Рисуем оси
        self.axes_renderer.render(painter, self.size())
        
        # Рисуем объекты сцены (исключая hover объект)
        excluded = []
        if self.selection_manager.hover_object:
            excluded.append(self.selection_manager.hover_object)
        self.object_renderer.render(painter, self.scene, excluded)
        
        # Рисуем hover объект голубым
        if self.selection_manager.hover_object:
            self.object_renderer.render_line_with_color(
                painter, self.selection_manager.hover_object, "#7ACCCC", 3
            )
        
        # Рисуем элементы текущего инструмента
        if self.current_tool:
            self.current_tool.paint(painter)
        
        # Рисуем индикатор поворота
        if self.rotation_animation.show_indicator:
            self.indicator_renderer.render_rotation_indicator(
                painter, self.view_transform.rotation_angle, self.size()
            )
        
        painter.end()
    
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Обрабатывает вызов контекстного меню."""
        menu = self.context_menu_builder.create_menu(event.pos())
        menu.exec(event.globalPos())
    
    def zoom_to_fit(self) -> None:
        """Автоматически масштабирует и центрирует вид для отображения всех объектов."""
        bounds = self._calculate_scene_bounds()
        
        if bounds is None:
            # Нет объектов - возвращаемся к начальному виду
            self.zoom_animation.start_zoom(1.0)
            self.view_transform.camera_pos = QPointF(-self.width() / 2, 0)
            return
        
        min_point, max_point = bounds
        
        # Вычисляем размеры bounding box
        bbox_width = max_point.x() - min_point.x()
        bbox_height = max_point.y() - min_point.y()
        
        # Добавляем отступы 10%
        padding = 0.1
        bbox_width *= (1 + padding * 2)
        bbox_height *= (1 + padding * 2)
        
        # Защита от деления на ноль
        if bbox_width < 0.01:
            bbox_width = 10.0
        if bbox_height < 0.01:
            bbox_height = 10.0
        
        # Вычисляем эффективные размеры экрана с учетом поворота
        angle_rad = math.radians(self.view_transform.rotation_angle)
        cos_angle = abs(math.cos(angle_rad))
        sin_angle = abs(math.sin(angle_rad))
        
        effective_screen_width = self.width() * cos_angle + self.height() * sin_angle
        effective_screen_height = self.width() * sin_angle + self.height() * cos_angle
        
        # Вычисляем необходимый zoom
        zoom_x = effective_screen_width / bbox_width
        zoom_y = effective_screen_height / bbox_height
        new_zoom = min(zoom_x, zoom_y)
        
        # Ограничиваем zoom
        new_zoom = max(0.1, min(10.0, new_zoom))
        
        # Центрируем камеру на центре bounding box
        center_x = (min_point.x() + max_point.x()) / 2
        center_y = (min_point.y() + max_point.y()) / 2
        self.view_transform.camera_pos = QPointF(center_x, center_y)
        
        # Запускаем анимацию zoom
        self.zoom_animation.start_zoom(new_zoom)
    
    def _calculate_scene_bounds(self):
        """Вычисляет bounding box всех объектов в сцене."""
        if not self.scene.objects:
            return None
        
        from .core.geometry import Line
        
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for obj in self.scene.objects:
            if isinstance(obj, Line):
                min_x = min(min_x, obj.start.x, obj.end.x)
                min_y = min(min_y, obj.start.y, obj.end.y)
                max_x = max(max_x, obj.start.x, obj.end.x)
                max_y = max(max_y, obj.start.y, obj.end.y)
        
        return (QPointF(min_x, min_y), QPointF(max_x, max_y))
    
    def set_pan_tool_active(self, active: bool) -> None:
        """Активирует или деактивирует pan tool (для совместимости с MainWindow)."""
        if active:
            self.pan_tool_action.setChecked(True)
        else:
            # Возвращаемся к line tool
            self.line_tool_action.setChecked(True)
    
    def get_view_state(self) -> dict:
        """Возвращает текущее состояние вида для сохранения."""
        return self.view_transform.get_view_state()
    
    def set_view_state(self, state: dict) -> None:
        """Восстанавливает состояние вида из сохраненных данных."""
        self.view_transform.set_view_state(state)
        
        # Отправляем сигналы об изменении
        self.zoom_changed.emit(self.view_transform.zoom_factor)
        self.rotation_changed.emit(self.view_transform.rotation_angle)
        
        self.update()
