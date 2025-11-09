"""Action manager for creating and managing QActions."""

from PySide6.QtGui import QAction, QIcon, QActionGroup
from PySide6.QtWidgets import QWidget

from ..icon_utils import load_svg_icon


class ActionManager:
    """Manages all QActions for the application."""
    
    def __init__(self, parent: QWidget):
        """Initialize the action manager.
        
        Args:
            parent: Parent widget (usually MainWindow)
        """
        self.parent = parent
        self.actions = {}
        self.tool_group = None
        
        # Создаем все actions
        self._create_all_actions()
    
    def _create_all_actions(self) -> None:
        """Создает все actions приложения."""
        self.create_file_actions()
        self.create_tool_actions()
        self.create_view_actions()
    
    def create_file_actions(self) -> dict[str, QAction]:
        """Создает actions для меню File.
        
        Returns:
            Словарь с file actions
        """
        # New action
        self.actions['new'] = QAction(QIcon.fromTheme("document-new"), "&Новый", self.parent)
        
        # Open action
        self.actions['open'] = QAction(QIcon.fromTheme("document-open"), "&Открыть...", self.parent)
        
        # Save action
        self.actions['save'] = QAction(QIcon.fromTheme("document-save"), "&Сохранить", self.parent)
        
        # Settings action
        self.actions['settings'] = QAction(
            QIcon.fromTheme("preferences-system"), "Настройки...", self.parent
        )
        
        # Exit action
        self.actions['exit'] = QAction(QIcon.fromTheme("application-exit"), "&Выход", self.parent)
        
        return {
            'new': self.actions['new'],
            'open': self.actions['open'],
            'save': self.actions['save'],
            'settings': self.actions['settings'],
            'exit': self.actions['exit']
        }
    
    def create_tool_actions(self) -> dict[str, QAction]:
        """Создает actions для инструментов.
        
        Returns:
            Словарь с tool actions
        """
        # Line tool action
        self.actions['line_tool'] = QAction(load_svg_icon("public/line.svg"), "Линия", self.parent)
        self.actions['line_tool'].setCheckable(True)
        self.actions['line_tool'].setChecked(True)  # Активен по умолчанию
        
        # Delete tool action
        self.actions['delete_tool'] = QAction(
            load_svg_icon("public/delete.svg"), "Удалить", self.parent
        )
        self.actions['delete_tool'].setCheckable(True)
        
        # Pan tool action
        self.actions['pan_tool'] = QAction(load_svg_icon("public/move.svg"), "Рука", self.parent)
        self.actions['pan_tool'].setToolTip("Инструмент панорамирования (H)")
        self.actions['pan_tool'].setShortcut("H")
        self.actions['pan_tool'].setCheckable(True)
        
        # Создаем группу для взаимоисключающих инструментов
        self.tool_group = QActionGroup(self.parent)
        self.tool_group.addAction(self.actions['line_tool'])
        self.tool_group.addAction(self.actions['delete_tool'])
        self.tool_group.addAction(self.actions['pan_tool'])
        
        return {
            'line_tool': self.actions['line_tool'],
            'delete_tool': self.actions['delete_tool'],
            'pan_tool': self.actions['pan_tool']
        }
    
    def create_view_actions(self) -> dict[str, QAction]:
        """Создает actions для управления видом.
        
        Returns:
            Словарь с view actions
        """
        # Zoom to fit action
        self.actions['zoom_fit'] = QAction(
            QIcon.fromTheme("zoom-fit-best"), "По размеру", self.parent
        )
        self.actions['zoom_fit'].setToolTip("Показать все объекты (Ctrl+0)")
        self.actions['zoom_fit'].setShortcut("Ctrl+0")
        
        # Rotate left action
        self.actions['rotate_left'] = QAction(
            load_svg_icon("public/rotate.svg"), "Повернуть влево", self.parent
        )
        self.actions['rotate_left'].setToolTip("Повернуть вид по часовой стрелке (R + Left)")
        
        # Rotate right action
        self.actions['rotate_right'] = QAction(
            load_svg_icon("public/rotate_right.svg"), "Повернуть вправо", self.parent
        )
        self.actions['rotate_right'].setToolTip("Повернуть вид против часовой стрелки (R + Right)")
        
        # Polar mode action
        self.actions['polar_mode'] = QAction(load_svg_icon("public/polar.svg"), "θ", self.parent)
        self.actions['polar_mode'].setCheckable(True)
        self.actions['polar_mode'].setToolTip(
            "Полярные координаты (активировано: полярные, неактивировано: декартовы)"
        )
        
        return {
            'zoom_fit': self.actions['zoom_fit'],
            'rotate_left': self.actions['rotate_left'],
            'rotate_right': self.actions['rotate_right'],
            'polar_mode': self.actions['polar_mode']
        }
    
    def get_action(self, name: str) -> QAction:
        """Получает action по имени.
        
        Args:
            name: Имя action
            
        Returns:
            QAction или None если не найден
        """
        return self.actions.get(name)
    
    def get_tool_group(self) -> QActionGroup:
        """Получает группу инструментов.
        
        Returns:
            QActionGroup с tool actions
        """
        return self.tool_group
