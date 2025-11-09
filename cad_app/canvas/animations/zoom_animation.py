"""Zoom animation module for smooth zoom transitions."""

from PySide6.QtCore import QTimer, QPointF, Signal, QObject


class ZoomAnimation(QObject):
    """Manages smooth zoom animations with cursor position preservation.
    
    Signals:
        zoom_changed: Emitted when zoom factor changes during animation
        animation_finished: Emitted when animation completes
    """
    
    zoom_changed = Signal(float)
    animation_finished = Signal()
    
    def __init__(self, view_transform, parent=None):
        """Initialize the zoom animation.
        
        Args:
            view_transform: ViewTransform instance to animate
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.view_transform = view_transform
        self.target_zoom = 1.0
        self.zoom_cursor_pos = None
        self.zoom_min = 0.1
        self.zoom_max = 10.0
        self.zoom_animation_speed = 0.15  # Скорость интерполяции (0-1)
        
        # QTimer for animation with 16ms interval (~60 FPS)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._animate_step)
    
    def start_zoom(self, target: float, cursor_pos: QPointF = None) -> None:
        """Начинает анимацию zoom к целевому значению.
        
        Args:
            target: Целевой zoom factor
            cursor_pos: Позиция курсора для сохранения при zoom (опционально)
        """
        # Ограничиваем target
        self.target_zoom = max(self.zoom_min, min(self.zoom_max, target))
        self.zoom_cursor_pos = cursor_pos
        
        # Запускаем анимацию, если она еще не активна
        if not self.timer.isActive():
            self.timer.start()
    
    def _animate_step(self) -> None:
        """Выполняет один шаг анимации zoom."""
        # Проверяем, достигли ли мы целевого zoom
        if abs(self.view_transform.zoom_factor - self.target_zoom) < 0.001:
            self.view_transform.zoom_factor = self.target_zoom
            self.timer.stop()
            self.zoom_changed.emit(self.view_transform.zoom_factor)
            self.animation_finished.emit()
            return
        
        # Сохраняем сценовую позицию под курсором до изменения zoom
        before_zoom_scene_pos = None
        if self.zoom_cursor_pos:
            before_zoom_scene_pos = self.view_transform.map_to_scene(self.zoom_cursor_pos)
        
        # Интерполируем zoom_factor к target_zoom
        self.view_transform.zoom_factor += (
            (self.target_zoom - self.view_transform.zoom_factor) * self.zoom_animation_speed
        )
        
        # Корректируем camera_pos так, чтобы точка под курсором осталась на месте
        if self.zoom_cursor_pos and before_zoom_scene_pos:
            after_zoom_scene_pos = self.view_transform.map_to_scene(self.zoom_cursor_pos)
            # Вычисляем разницу и корректируем позицию камеры
            delta = after_zoom_scene_pos - before_zoom_scene_pos
            self.view_transform.camera_pos -= delta
        
        self.zoom_changed.emit(self.view_transform.zoom_factor)
    
    def is_active(self) -> bool:
        """Проверяет, активна ли анимация.
        
        Returns:
            True если анимация выполняется
        """
        return self.timer.isActive()
    
    def stop(self) -> None:
        """Останавливает анимацию."""
        if self.timer.isActive():
            self.timer.stop()
            self.animation_finished.emit()
