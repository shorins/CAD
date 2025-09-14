# Наш кастомный виджет для рисования

import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QAction
from PySide6.QtCore import Qt, QPointF, Signal

from .core.scene import Scene
from .core.geometry import Point, Line
from .core.algorithms import bresenham
from .theme import DarkThemeColors # Импортируем цвета

class CanvasWidget(QWidget):
    # Сигнал для передачи координат в StatusBar
    cursor_pos_changed = Signal(QPointF)

    def __init__(self, scene: Scene, line_tool_action: QAction, parent=None):
        super().__init__(parent)
        self.scene = scene
        # Подписываемся на сигнал от Модели
        self.scene.scene_changed.connect(self.update)

        # Сохраняем экшен, чтобы проверять его состояние
        self.line_tool_action = line_tool_action
        
        self.setMouseTracking(True) # Включаем отслеживание мыши
        self.setAutoFillBackground(True)
        
        # Устанавливаем белый фон
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(DarkThemeColors.surface_canvas))
        self.setPalette(p)

        self.start_pos = None
        self.current_pos = None
        self.drawing_mode = "line" # TODO: добавить смену режимов рисования

        # --- Камера и навигация ---
        self.pan_start_pos = None
        self.camera_pos = QPointF(0, 0) # Позиция "камеры"

        # Флаг для однократной первоначальной центровки
        self._initial_center_done = False

    # Этот метод вызывается при изменении размера виджета, включая первый показ.
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Центрируем камеру на начале координат (0,0) только один раз
        if not self._initial_center_done:
            self.camera_pos = QPointF(-self.width() / 2, -self.height() / 2)
            self._initial_center_done = True

    def map_to_scene(self, screen_pos: QPointF) -> QPointF:
        """Преобразует экранные координаты в координаты сцены."""
        return screen_pos + self.camera_pos

    def map_from_scene(self, scene_pos: QPointF) -> QPointF:
        """Преобразует координаты сцены в экранные."""
        return scene_pos - self.camera_pos

    def mousePressEvent(self, event):
        """Вызывается при нажатии кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self.line_tool_action.isChecked():
            self.start_pos = event.position()
            self.current_pos = self.start_pos
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Начало панорамирования (перемещения)
            self.pan_start_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Вызывается при движении мыши."""

        # Всегда испускаем сигнал для обновления координат в статус-баре
        self.cursor_pos_changed.emit(event.position())

        # Мы обновляем current_pos, только если левая кнопка зажата (т.е. self.start_pos установлен)
        if self.start_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.current_pos = event.position()
            self.update() # Запрашиваем перерисовку, чтобы показать "резиновую ленту"
        elif self.pan_start_pos and event.buttons() & Qt.MouseButton.MiddleButton:
            delta = event.position() - self.pan_start_pos
            self.camera_pos -= delta
            self.pan_start_pos = event.position()
            self.update()
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        """Вызывается при отпускании кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self.start_pos:
            # 1. Берем начальную и конечную точки в ЭКРАННЫХ координатах.
            start_screen_pos = self.start_pos
            end_screen_pos = event.position()

            # 2. Преобразуем их в координаты СЦЕНЫ.
            start_scene_pos = self.map_to_scene(start_screen_pos)
            end_scene_pos = self.map_to_scene(end_screen_pos)

            # 3. Создаем геометрический объект с правильными, мировыми координатами.
            start_point = Point(start_scene_pos.x(), start_scene_pos.y())
            end_point = Point(end_scene_pos.x(), end_scene_pos.y())
            
            # Создаем объект Line и добавляем его в Модель (сцену)
            line = Line(start_point, end_point)
            self.scene.add_object(line)
            
            # Сбрасываем временные точки
            self.start_pos = None
            self.current_pos = None
            self.update() # Запросить финальную перерисовку
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Конец панорамирования
            self.pan_start_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        self._draw_grid(painter)
        self._draw_axes(painter)
        self._draw_scene_objects(painter)
        self._draw_preview(painter)

        painter.end()

    def _draw_grid(self, painter: QPainter):
        pen_minor = QPen(QColor(DarkThemeColors.border_subtle), 0.5)
        pen_major = QPen(QColor(DarkThemeColors.text_disabled), 1)

        width, height = self.width(), self.height()
        grid_size = 50
        major_grid_interval = 5

        # 1. Определяем видимую область в координатах сцены
        scene_top_left = self.map_to_scene(QPointF(0, 0))
        scene_bottom_right = self.map_to_scene(QPointF(width, height))

        # 2. Находим индексы линий сетки, которые попадают в видимую область
        start_x_index = math.floor(scene_top_left.x() / grid_size)
        end_x_index = math.ceil(scene_bottom_right.x() / grid_size)
        start_y_index = math.floor(scene_top_left.y() / grid_size)
        end_y_index = math.ceil(scene_bottom_right.y() / grid_size)

        # 3. Рисуем вертикальные линии
        for i in range(start_x_index, end_x_index + 1):
            # Проверяем индекс линии, а не ее экранную координату
            is_major = (i % major_grid_interval == 0)
            painter.setPen(pen_major if is_major else pen_minor)

            # Преобразуем мировую координату линии в экранную
            line_scene_x = i * grid_size
            line_screen_x = self.map_from_scene(QPointF(line_scene_x, 0)).x()
            
            painter.drawLine(int(line_screen_x), 0, int(line_screen_x), height)

        # 4. Рисуем горизонтальные линии
        for i in range(start_y_index, end_y_index + 1):
            is_major = (i % major_grid_interval == 0)
            painter.setPen(pen_major if is_major else pen_minor)
            
            line_scene_y = i * grid_size
            line_screen_y = self.map_from_scene(QPointF(0, line_scene_y)).y()

            painter.drawLine(0, int(line_screen_y), width, int(line_screen_y))

    def _draw_axes(self, painter: QPainter):
        # Отрисовка осей координат (начало 0,0)
        origin_screen = self.map_from_scene(QPointF(0, 0))
        
        # Ось X (красная)
        painter.setPen(QPen(QColor("#CC7A7A"), 1.5))
        painter.drawLine(int(origin_screen.x()), 0, int(origin_screen.x()), self.height())
        # Ось Y (зеленая)
        painter.setPen(QPen(QColor("#7ACC7A"), 1.5))
        painter.drawLine(0, int(origin_screen.y()), self.width(), int(origin_screen.y()))

    def _draw_scene_objects(self, painter: QPainter):
        # Устанавливаем перо для рисования
        pen = QPen(QColor(DarkThemeColors.text_high_emphasis), 2)
        painter.setPen(pen)

        # Проходим по всем объектам в сцене (Модели) и отрисовываем их
        for obj in self.scene.objects:
            if isinstance(obj, Line):
                start_screen = self.map_from_scene(QPointF(obj.start.x, obj.start.y))
                end_screen = self.map_from_scene(QPointF(obj.end.x, obj.end.y))
                # Получаем генератор точек от нашего алгоритма
                points_generator = bresenham(
                    int(start_screen.x()), int(start_screen.y()),
                    int(end_screen.x()), int(end_screen.y())
                )
                # Рисуем линию точка за точкой
                for point in points_generator:
                    painter.drawPoint(*point)
            # TODO: Добавить отрисовку других типов объектов
    
    def _draw_preview(self, painter: QPainter):
        # "Резиновая лента" при рисовании
        if self.start_pos and self.current_pos:
            pen = QPen(QColor(DarkThemeColors.accent_primary_default), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(self.start_pos, self.current_pos)