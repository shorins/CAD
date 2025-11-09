"""Menu manager for creating and managing menus."""

from PySide6.QtWidgets import QMainWindow, QMenu

from .actions import ActionManager


class MenuManager:
    """Manages menu bar creation and updates."""
    
    def __init__(self, main_window: QMainWindow, action_manager: ActionManager):
        """Initialize the menu manager.
        
        Args:
            main_window: Reference to MainWindow
            action_manager: ActionManager instance
        """
        self.main_window = main_window
        self.action_manager = action_manager
        self.menus = {}
    
    def create_menus(self) -> None:
        """Создает все меню приложения."""
        self._create_file_menu()
    
    def _create_file_menu(self) -> QMenu:
        """Создает меню File.
        
        Returns:
            QMenu для File
        """
        file_menu = self.main_window.menuBar().addMenu("&Файл")
        
        # Добавляем actions
        file_menu.addAction(self.action_manager.get_action('new'))
        file_menu.addAction(self.action_manager.get_action('open'))
        file_menu.addAction(self.action_manager.get_action('save'))
        file_menu.addSeparator()
        file_menu.addAction(self.action_manager.get_action('settings'))
        file_menu.addAction(self.action_manager.get_action('exit'))
        
        self.menus['file'] = file_menu
        return file_menu
    
    def get_menu(self, name: str) -> QMenu:
        """Получает меню по имени.
        
        Args:
            name: Имя меню
            
        Returns:
            QMenu или None если не найдено
        """
        return self.menus.get(name)
