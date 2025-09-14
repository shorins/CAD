# Наш кастомный виджет для рисования

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt

from.core.scene import Scene
from.core.geometry import Point, Line
from.core.algorithms import bresenham

class CanvasWidget(QWidget):
    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        # Подписываемся на сигнал от Модели
        self.scene.scene_changed.connect(self.update)
        
        self.setMouseTracking(True) # Включаем отслеживание мыши
        self.setAutoFillBackground(True)
        
        # Устанавливаем белый фон
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.GlobalColor.white)
        self.setPalette(p)

        self.start_pos = None
        self.current_pos = None
        self.drawing_mode = "line" # TODO: добавить смену режимов рисования

    def mousePressEvent(self, event):
        """Вызывается при нажатии кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.position().toPoint()
            self.current_pos = self.start_pos
            self.update() # перерисовка
        super().mousePressEvent(event) 

    def mouseMoveEvent(self, event):
        """Вызывается при движении мыши."""
        # Мы обновляем current_pos, только если левая кнопка зажата (т.е. self.start_pos установлен)
        if self.start_pos:
            self.current_pos = event.position().toPoint()
            self.update() # Запрашиваем перерисовку, чтобы показать "резиновую ленту"
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        """Вызывается при отпускании кнопки мыши."""
        if event.button() == Qt.MouseButton.LeftButton and self.start_pos:
            start_point = Point(self.start_pos.x(), self.start_pos.y())
            end_point = Point(event.position().x(), event.position().y())
            
            # Создаем объект Line и добавляем его в Модель (сцену)
            line = Line(start_point, end_point)
            self.scene.add_object(line)
            
            # Сбрасываем временные точки
            self.start_pos = None
            self.current_pos = None
            self.update() # Запросить финальную перерисовку
        super().mouseReleaseEvent(event) # [48]


    def paintEvent(self, event):
        """Этот метод вызывается автоматически для перерисовки виджета."""
        painter = QPainter(self)
        
        # Устанавливаем перо для рисования
        pen = QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        # Проходим по всем объектам в сцене (Модели) и отрисовываем их
        for obj in self.scene.objects:
            if isinstance(obj, Line):
                # Получаем генератор точек от нашего алгоритма
                points_generator = bresenham(
                    int(obj.start.x), int(obj.start.y),
                    int(obj.end.x), int(obj.end.y)
                )
                # Рисуем линию точка за точкой
                for point in points_generator:
                    painter.drawPoint(*point)
            # TODO: Добавить отрисовку других типов объектов

        # Динамическая отрисовка ("резиновая лента")
        if self.start_pos and self.current_pos:
            preview_pen = QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashLine)
            painter.setPen(preview_pen)
            
            # Для превью можно использовать стандартный drawLine для плавности,
            # но можно и Брезенхэм, если нужна пиксельная точность превью.
            painter.drawLine(self.start_pos, self.current_pos)


        painter.end()