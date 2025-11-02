import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QAction
from PySide6.QtCore import Qt, QPointF, Signal

from .core.scene import Scene
from .core.geometry import Point, Line
from .core.algorithms import bresenham
from .core.math_utils import distance_point_to_segment_sq
from .settings import settings

class CanvasWidget(QWidget):
    cursor_pos_changed = Signal(QPointF)

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
        
        self.on_settings_changed() # Вызываем при старте, чтобы установить фон

        self.start_pos = None
        self.current_pos = None
        self.pan_start_pos = None
        self.camera_pos = QPointF(0, 0)
        self._initial_center_done = False
        
        # Для режима удаления
        self.highlighted_line = None  # Линия, которая выделена при наведении
        self.selection_threshold = 10.0  # Пороговое расстояние в пикселях для выделения

    def on_settings_changed(self):
        """Слот, который вызывается при изменении настроек."""
        # Получаем настройки с "защитой" от их отсутствия
        colors = settings.get("colors") or settings.defaults["colors"]
        bg_color = colors.get("canvas_bg", "#2D2D2D")
        
        # Устанавливаем фон через прямое указание стиля. Это надежнее.
        self.setStyleSheet(f"background-color: {bg_color};")
        
        self.update() # Запросить полную перерисовку
    
    def _on_delete_tool_changed(self):
        """Обработчик изменения состояния инструмента удаления."""
        if not self.delete_tool_action.isChecked():
            # Выходим из режима удаления - сбрасываем выделение
            self.highlighted_line = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initial_center_done:
            self.camera_pos = QPointF(-self.width() / 2, -self.height() / 2)
            self._initial_center_done = True
            
    # ... (map_to_scene, map_from_scene и другие обработчики мыши остаются без изменений)
    def map_to_scene(self, screen_pos: QPointF) -> QPointF:
        return screen_pos + self.camera_pos

    def map_from_scene(self, scene_pos: QPointF) -> QPointF:
        return scene_pos - self.camera_pos

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.start_pos:
            self.start_pos = None
            self.current_pos = None
            self.update()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.line_tool_action.isChecked():
            if event.button() == Qt.MouseButton.LeftButton:
                if self.start_pos is None:
                    # Первый клик: начинаем рисовать линию
                    self.start_pos = event.position()
                    self.current_pos = self.start_pos
                else:
                    # Второй клик: завершаем линию
                    start_scene_pos = self.map_to_scene(self.start_pos)
                    end_scene_pos = self.map_to_scene(event.position())
                    start_point = Point(start_scene_pos.x(), start_scene_pos.y())
                    end_point = Point(end_scene_pos.x(), end_scene_pos.y())
                    line = Line(start_point, end_point)
                    self.scene.add_object(line)
                    self.start_pos = None
                    self.current_pos = None
            elif event.button() == Qt.MouseButton.RightButton and self.start_pos:
                # Отмена рисования правой кнопкой мыши
                self.start_pos = None
                self.current_pos = None
        elif self.delete_tool_action.isChecked():
            if event.button() == Qt.MouseButton.LeftButton and self.highlighted_line:
                # Удаляем выделенную линию
                self.scene.remove_object(self.highlighted_line)
                self.highlighted_line = None
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.pan_start_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.update()

    def mouseMoveEvent(self, event):
        self.cursor_pos_changed.emit(event.position())
        
        if self.delete_tool_action.isChecked() and not (event.buttons() & Qt.MouseButton.MiddleButton):
            # В режиме удаления ищем ближайшую линию
            self._find_nearest_line(event.position())
            # Меняем курсор на крестик в режиме удаления
            if self.highlighted_line:
                self.setCursor(Qt.CursorShape.PointingHandCursor)  # Рука указывающая
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)  # Крестик
        elif not self.delete_tool_action.isChecked():
            # Выходим из режима удаления - сбрасываем выделение и курсор
            if self.highlighted_line is not None:
                self.highlighted_line = None
                self.update()
            if not (event.buttons() & Qt.MouseButton.MiddleButton):
                self.setCursor(Qt.CursorShape.ArrowCursor)  # Обычная стрелка
        
        if self.start_pos:
            self.current_pos = event.position()
            self.update()
        elif self.pan_start_pos and event.buttons() & Qt.MouseButton.MiddleButton:
            delta = event.position() - self.pan_start_pos
            self.camera_pos -= delta
            self.pan_start_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
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
        painter.end()

    def _draw_grid(self, painter: QPainter):
        colors = settings.get("colors") or settings.defaults["colors"]
        pen_minor = QPen(QColor(colors.get("grid_minor", "#000000")), 0.5)
        pen_major = QPen(QColor(colors.get("grid_major", "#000000")), 1)
        grid_size = settings.get("grid_step") or settings.defaults["grid_step"]
        major_grid_interval = 5

        width, height = self.width(), self.height()
        scene_top_left = self.map_to_scene(QPointF(0, 0))
        scene_bottom_right = self.map_to_scene(QPointF(width, height))

        start_x_index = math.floor(scene_top_left.x() / grid_size)
        end_x_index = math.ceil(scene_bottom_right.x() / grid_size)
        start_y_index = math.floor(scene_top_left.y() / grid_size)
        end_y_index = math.ceil(scene_bottom_right.y() / grid_size)

        for i in range(start_x_index, end_x_index + 1):
            is_major = (i % major_grid_interval == 0)
            painter.setPen(pen_major if is_major else pen_minor)
            line_scene_x = i * grid_size
            line_screen_x = self.map_from_scene(QPointF(line_scene_x, 0)).x()
            painter.drawLine(int(line_screen_x), 0, int(line_screen_x), height)

        for i in range(start_y_index, end_y_index + 1):
            is_major = (i % major_grid_interval == 0)
            painter.setPen(pen_major if is_major else pen_minor)
            line_scene_y = i * grid_size
            line_screen_y = self.map_from_scene(QPointF(0, line_scene_y)).y()
            painter.drawLine(0, int(line_screen_y), width, int(line_screen_y))

    def _draw_axes(self, painter: QPainter):
        origin_screen = self.map_from_scene(QPointF(0, 0))
        painter.setPen(QPen(QColor("#CC7A7A"), 1.5))
        painter.drawLine(int(origin_screen.x()), 0, int(origin_screen.x()), self.height())
        painter.setPen(QPen(QColor("#7ACC7A"), 1.5))
        painter.drawLine(0, int(origin_screen.y()), self.width(), int(origin_screen.y()))

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
            painter.drawLine(self.start_pos.toPoint(), self.current_pos.toPoint())
    
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