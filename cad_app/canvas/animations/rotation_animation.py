"""Rotation animation module for smooth rotation transitions."""

from PySide6.QtCore import QTimer, QTime, Signal, QObject


class RotationAnimation(QObject):
    """Manages smooth rotation animations with easing.
    
    Signals:
        rotation_changed: Emitted when rotation angle changes during animation
        animation_finished: Emitted when animation completes
    """
    
    rotation_changed = Signal(float)
    animation_finished = Signal()
    
    def __init__(self, view_transform, parent=None):
        """Initialize the rotation animation.
        
        Args:
            view_transform: ViewTransform instance to animate
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.view_transform = view_transform
        self.target_angle = 0.0
        self.start_angle = 0.0
        self.start_time = 0
        self.duration = 50  # Длительность анимации в миллисекундах
        self.rotation_step = 90.0  # Шаг поворота в градусах
        self.show_indicator = False  # Показывать ли индикатор поворота
        
        # QTimer for animation with 16ms interval (~60 FPS)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._animate_step)
        
        # Таймер для скрытия индикатора
        self.indicator_timer = QTimer(self)
        self.indicator_timer.setInterval(2000)  # 2 секунды
        self.indicator_timer.setSingleShot(True)
        self.indicator_timer.timeout.connect(self._hide_indicator)
    
    def start_rotation(self, clockwise: bool) -> None:
        """Начинает анимацию поворота на rotation_step градусов.
        
        Args:
            clockwise: True для поворота по часовой стрелке, 
                      False для поворота против часовой стрелки
        """
        # Игнорируем новые команды поворота во время анимации
        if self.is_active():
            return
        
        # Сохраняем начальный угол
        self.start_angle = self.view_transform.rotation_angle
        
        # Вычисляем целевой угол
        if clockwise:
            # Поворот по часовой стрелке (+90°)
            self.target_angle = self.view_transform.rotation_angle + self.rotation_step
        else:
            # Поворот против часовой стрелки (-90°)
            self.target_angle = self.view_transform.rotation_angle - self.rotation_step
        
        # Нормализуем целевой угол к диапазону [0, 360)
        self.target_angle = self.target_angle % 360.0
        
        # Сохраняем время начала анимации
        self.start_time = QTime.currentTime().msecsSinceStartOfDay()
        
        # Показываем индикатор поворота и запускаем таймер для его скрытия
        self.show_indicator = True
        self.indicator_timer.start()
        
        # Запускаем таймер анимации
        if not self.timer.isActive():
            self.timer.start()
    
    def _animate_step(self) -> None:
        """Выполняет один шаг анимации поворота с easing."""
        # Вычисляем прошедшее время
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        elapsed = current_time - self.start_time
        
        # Вычисляем прогресс (0.0 - 1.0)
        progress = min(1.0, elapsed / self.duration)
        
        # Применяем easing function (ease-in-out cubic)
        # Формула: t < 0.5 ? 4*t^3 : 1 - (-2*t + 2)^3 / 2
        if progress < 0.5:
            eased_progress = 4 * progress * progress * progress
        else:
            eased_progress = 1 - pow(-2 * progress + 2, 3) / 2
        
        # Вычисляем разницу углов с учетом кратчайшего пути
        angle_diff = self.target_angle - self.start_angle
        
        # Нормализуем разницу к диапазону [-180, 180] для кратчайшего пути
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        
        # Интерполируем угол
        self.view_transform.rotation_angle = self.start_angle + angle_diff * eased_progress
        
        # Нормализуем к диапазону [0, 360)
        self.view_transform.rotation_angle = self.view_transform.rotation_angle % 360.0
        
        # Проверяем завершение анимации
        if progress >= 1.0:
            # Устанавливаем точное значение
            self.view_transform.rotation_angle = self.target_angle
            self.timer.stop()
            self.rotation_changed.emit(self.view_transform.rotation_angle)
            self.animation_finished.emit()
            return
        
        # Отправляем сигнал об изменении угла поворота
        self.rotation_changed.emit(self.view_transform.rotation_angle)
    
    def _hide_indicator(self) -> None:
        """Скрывает индикатор поворота после таймаута."""
        self.show_indicator = False
    
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
