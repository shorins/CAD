"""Toolbar manager for creating and managing toolbars."""

from PySide6.QtWidgets import QMainWindow, QToolBar
from PySide6.QtCore import Qt

from .actions import ActionManager
from ..settings import settings


class ToolbarManager:
    """Manages toolbar creation and updates."""
    
    def __init__(self, main_window: QMainWindow, action_manager: ActionManager):
        """Initialize the toolbar manager.
        
        Args:
            main_window: Reference to MainWindow
            action_manager: ActionManager instance
        """
        self.main_window = main_window
        self.action_manager = action_manager
        self.toolbars = {}
    
    def create_toolbars(self) -> None:
        """Создает все toolbars приложения."""
        self._create_tools_toolbar()
    
    def _create_tools_toolbar(self) -> QToolBar:
        """Создает toolbar с инструментами.
        
        Returns:
            QToolBar с инструментами
        """
        edit_toolbar = QToolBar("Инструменты")
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, edit_toolbar)
        
        # Добавляем tool actions
        edit_toolbar.addAction(self.action_manager.get_action('line_tool'))
        edit_toolbar.addAction(self.action_manager.get_action('delete_tool'))
        edit_toolbar.addAction(self.action_manager.get_action('pan_tool'))
        
        # Zoom to fit
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.action_manager.get_action('zoom_fit'))
        
        # Кнопки поворота вида
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.action_manager.get_action('rotate_left'))
        edit_toolbar.addAction(self.action_manager.get_action('rotate_right'))
        
        # Переключатель режима построения линии
        edit_toolbar.addSeparator()
        polar_action = self.action_manager.get_action('polar_mode')
        edit_toolbar.addAction(polar_action)
        
        # Загружаем текущий режим из настроек
        current_mode = settings.get("line_construction_mode") or "cartesian"
        polar_action.setChecked(current_mode == "polar")
        
        self.toolbars['tools'] = edit_toolbar
        return edit_toolbar
    
    def get_toolbar(self, name: str) -> QToolBar:
        """Получает toolbar по имени.
        
        Args:
            name: Имя toolbar
            
        Returns:
            QToolBar или None если не найден
        """
        return self.toolbars.get(name)
