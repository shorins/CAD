"""Base tool interface for canvas tools."""

from abc import ABC, abstractmethod
from PySide6.QtGui import QPainter, QMouseEvent, QKeyEvent


class BaseTool(ABC):
    """Abstract base class for canvas tools.
    
    All tools must implement this interface to work with the canvas.
    """
    
    def __init__(self, canvas_widget):
        """Initialize the tool.
        
        Args:
            canvas_widget: Reference to the CanvasWidget
        """
        self.canvas = canvas_widget
        self.active = False
    
    @abstractmethod
    def activate(self) -> None:
        """Активирует инструмент.
        
        Вызывается когда инструмент становится активным.
        Используется для установки курсора, инициализации состояния и т.д.
        """
        pass
    
    @abstractmethod
    def deactivate(self) -> None:
        """Деактивирует инструмент.
        
        Вызывается когда инструмент перестает быть активным.
        Используется для очистки состояния, сброса курсора и т.д.
        """
        pass
    
    @abstractmethod
    def mouse_press(self, event: QMouseEvent) -> bool:
        """Обрабатывает нажатие кнопки мыши.
        
        Args:
            event: Событие мыши
            
        Returns:
            True если событие было обработано и требуется перерисовка
        """
        pass
    
    @abstractmethod
    def mouse_move(self, event: QMouseEvent) -> bool:
        """Обрабатывает движение мыши.
        
        Args:
            event: Событие мыши
            
        Returns:
            True если событие было обработано и требуется перерисовка
        """
        pass
    
    @abstractmethod
    def mouse_release(self, event: QMouseEvent) -> bool:
        """Обрабатывает отпускание кнопки мыши.
        
        Args:
            event: Событие мыши
            
        Returns:
            True если событие было обработано и требуется перерисовка
        """
        pass
    
    @abstractmethod
    def key_press(self, event: QKeyEvent) -> bool:
        """Обрабатывает нажатие клавиши.
        
        Args:
            event: Событие клавиатуры
            
        Returns:
            True если событие было обработано и требуется перерисовка
        """
        pass
    
    @abstractmethod
    def paint(self, painter: QPainter) -> None:
        """Рисует специфичные для инструмента элементы.
        
        Например, preview линии, выделение объектов и т.д.
        
        Args:
            painter: QPainter для рисования
        """
        pass
