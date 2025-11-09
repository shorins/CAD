"""Status bar manager for creating and managing status bar widgets."""

from PySide6.QtWidgets import QMainWindow, QLabel


class StatusBarManager:
    """Manages status bar widgets and updates."""
    
    def __init__(self, main_window: QMainWindow):
        """Initialize the status bar manager.
        
        Args:
            main_window: Reference to MainWindow
        """
        self.main_window = main_window
        self.labels = {}
    
    def create_status_bar(self) -> None:
        """Создает status bar с виджетами."""
        status_bar = self.main_window.statusBar()
        
        # Создаем виджеты для отображения информации
        self.labels['cursor_pos'] = QLabel("X: 0.00, Y: 0.00")
        self.labels['line_info'] = QLabel("")
        self.labels['zoom'] = QLabel("Масштаб: 100%")
        self.labels['rotation'] = QLabel("Поворот: 0°")
        self.labels['tool'] = QLabel("Инструмент: Линия")
        
        # Добавляем виджеты на status bar
        status_bar.addPermanentWidget(self.labels['cursor_pos'])
        status_bar.addPermanentWidget(self.labels['line_info'])
        status_bar.addPermanentWidget(self.labels['zoom'])
        status_bar.addPermanentWidget(self.labels['rotation'])
        status_bar.addPermanentWidget(self.labels['tool'])
    
    def update_cursor_pos(self, x: float, y: float) -> None:
        """Обновляет отображение позиции курсора.
        
        Args:
            x: X координата
            y: Y координата
        """
        self.labels['cursor_pos'].setText(f"X: {x:.2f}, Y: {y:.2f}")
    
    def update_line_info(self, info: str) -> None:
        """Обновляет информацию о линии.
        
        Args:
            info: Текст информации о линии
        """
        self.labels['line_info'].setText(info)
    
    def update_zoom(self, zoom_factor: float) -> None:
        """Обновляет отображение масштаба.
        
        Args:
            zoom_factor: Коэффициент масштабирования
        """
        zoom_percent = int(zoom_factor * 100)
        self.labels['zoom'].setText(f"Масштаб: {zoom_percent}%")
    
    def update_rotation(self, rotation_angle: float) -> None:
        """Обновляет отображение угла поворота.
        
        Args:
            rotation_angle: Угол поворота в градусах
        """
        # Инвертируем угол для отображения (360 - angle)
        display_angle = (360 - int(rotation_angle)) % 360
        self.labels['rotation'].setText(f"Поворот: {display_angle}°")
    
    def update_tool(self, tool_name: str) -> None:
        """Обновляет отображение активного инструмента.
        
        Args:
            tool_name: Имя инструмента
        """
        tool_names = {
            'line': 'Линия',
            'delete': 'Удаление',
            'pan': 'Панорамирование'
        }
        display_name = tool_names.get(tool_name, tool_name)
        self.labels['tool'].setText(f"Инструмент: {display_name}")
