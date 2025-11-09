"""Refactored main window using UI manager modules."""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar
from PySide6.QtCore import Qt

from .core.scene import Scene
from .core.geometry import Point, Line
from .canvas_widget import CanvasWidget
from .theme import get_stylesheet
from .settings_dialog import SettingsDialog
from .settings import settings
from .line_input_panel import LineInputPanel
from .ui.actions import ActionManager
from .ui.menus import MenuManager
from .ui.toolbars import ToolbarManager
from .ui.status_bar import StatusBarManager
from .ui.project_io import ProjectIO


class MainWindow(QMainWindow):
    """Refactored main window using modular UI managers."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("shorins CAD")
        self.setGeometry(100, 100, 800, 600)
        self.showMaximized()
        
        # Create scene
        self.scene = Scene()
        
        # Create UI managers
        self.action_manager = ActionManager(self)
        self.menu_manager = MenuManager(self, self.action_manager)
        self.toolbar_manager = ToolbarManager(self, self.action_manager)
        self.status_bar_manager = StatusBarManager(self)
        self.project_io = ProjectIO(self)
        
        # Create canvas
        self.canvas = CanvasWidget(self.scene, self.action_manager, self)
        self.setCentralWidget(self.canvas)
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Настраивает UI компоненты."""
        # Create menus
        self.menu_manager.create_menus()
        
        # Create toolbars
        self.toolbar_manager.create_toolbars()
        
        # Create status bar
        self.status_bar_manager.create_status_bar()
        
        # Create line input panel
        self._create_line_input_panel()
    
    def _connect_signals(self) -> None:
        """Подключает сигналы к слотам."""
        # Connect file actions
        self.action_manager.get_action('new').triggered.connect(self.project_io.new_project)
        self.action_manager.get_action('open').triggered.connect(self.project_io.open_project)
        self.action_manager.get_action('save').triggered.connect(self.project_io.save_project)
        self.action_manager.get_action('exit').triggered.connect(self.close)
        self.action_manager.get_action('settings').triggered.connect(self._open_settings)
        
        # Connect view actions
        self.action_manager.get_action('zoom_fit').triggered.connect(self.canvas.zoom_to_fit)
        self.action_manager.get_action('rotate_left').triggered.connect(
            lambda: self.canvas.rotation_animation.start_rotation(clockwise=True)
        )
        self.action_manager.get_action('rotate_right').triggered.connect(
            lambda: self.canvas.rotation_animation.start_rotation(clockwise=False)
        )
        self.action_manager.get_action('polar_mode').toggled.connect(self._on_polar_mode_toggled)
        
        # Connect canvas signals to status bar
        self.canvas.cursor_pos_changed.connect(self._update_cursor_pos)
        self.canvas.line_info_changed.connect(self.status_bar_manager.update_line_info)
        self.canvas.zoom_changed.connect(self.status_bar_manager.update_zoom)
        self.canvas.rotation_changed.connect(self.status_bar_manager.update_rotation)
        
        # Connect tool actions to status bar updates
        self.action_manager.get_action('line_tool').toggled.connect(
            lambda checked: self.status_bar_manager.update_tool('line') if checked else None
        )
        self.action_manager.get_action('delete_tool').toggled.connect(
            lambda checked: self.status_bar_manager.update_tool('delete') if checked else None
        )
        self.action_manager.get_action('pan_tool').toggled.connect(
            lambda checked: self.status_bar_manager.update_tool('pan') if checked else None
        )
        
        # Connect line tool to line input panel visibility
        self.action_manager.get_action('line_tool').toggled.connect(self._on_line_tool_toggled)
        
        # Set initial tool label
        self.status_bar_manager.update_tool('line')
    
    def _update_cursor_pos(self, pos) -> None:
        """Обновляет отображение позиции курсора."""
        scene_pos = self.canvas.map_to_scene(pos)
        self.status_bar_manager.update_cursor_pos(scene_pos.x(), scene_pos.y())
    
    def _on_polar_mode_toggled(self, checked: bool) -> None:
        """Обработчик переключения режима построения линии."""
        mode = "polar" if checked else "cartesian"
        settings.set("line_construction_mode", mode)
        # Уведомляем canvas о изменении режима
        self.canvas.on_construction_mode_changed()
    
    def _on_line_tool_toggled(self, checked: bool) -> None:
        """Обработчик переключения инструмента линии."""
        if hasattr(self, 'line_input_toolbar'):
            if checked:
                self.line_input_toolbar.show()
            else:
                self.line_input_toolbar.hide()
    
    def _create_line_input_panel(self) -> None:
        """Создает панель ввода координат для линии."""
        self.line_input_panel = LineInputPanel(self)
        
        # Подключаем сигнал построения линии
        self.line_input_panel.line_requested.connect(self._on_line_build_requested)
        
        # Добавляем панель в нижнюю часть окна
        self.line_input_toolbar = QToolBar("Ввод координат")
        self.line_input_toolbar.addWidget(self.line_input_panel)
        self.line_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.line_input_toolbar)
        
        # Показываем панель, если инструмент "линия" активен
        line_tool_action = self.action_manager.get_action('line_tool')
        if line_tool_action and line_tool_action.isChecked():
            self.line_input_toolbar.show()
        else:
            self.line_input_toolbar.hide()
    
    def _on_line_build_requested(self, start_point: Point, end_point: Point) -> None:
        """Обработчик запроса на построение линии из панели ввода."""
        line = Line(start_point, end_point)
        self.scene.add_object(line)
    
    def _open_settings(self) -> None:
        """Открывает диалог настроек."""
        dialog = SettingsDialog(self)
        dialog.exec()


def run():
    """Запускает приложение."""
    app = QApplication(sys.argv)
    
    # Применяем темную тему
    app.setStyleSheet(get_stylesheet())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
