"""Context menu builder for canvas."""

from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import QPointF

from ..icon_utils import load_svg_icon


class ContextMenuBuilder:
    """Builds context menus based on canvas context."""
    
    def __init__(self, canvas_widget):
        """Initialize the context menu builder.
        
        Args:
            canvas_widget: Reference to the CanvasWidget
        """
        self.canvas = canvas_widget
    
    def create_menu(self, cursor_pos: QPointF) -> QMenu:
        """Создает контекстное меню в зависимости от контекста.
        
        Args:
            cursor_pos: Позиция курсора в экранных координатах
            
        Returns:
            Настроенное контекстное меню
        """
        menu = QMenu(self.canvas)
        
        # Добавляем подменю "Вид" (всегда присутствует)
        view_submenu = self._create_view_submenu()
        menu.addMenu(view_submenu)
        
        # Проверяем, есть ли объект под курсором
        if self.canvas.selection_manager.hover_object:
            # Добавляем разделитель перед командами объекта
            menu.addSeparator()
            
            # Добавляем команду "Удалить"
            delete_action = menu.addAction("Удалить")
            delete_action.setIcon(load_svg_icon("public/delete.svg"))
            delete_action.triggered.connect(self._on_delete_object)
        
        return menu
    
    def _create_view_submenu(self) -> QMenu:
        """Создает подменю "Вид" с командами управления видом.
        
        Returns:
            Подменю с командами управления видом
        """
        view_menu = QMenu("Вид", self.canvas)
        
        # Добавляем команду "Панорамирование" с иконкой и чекбоксом
        pan_action = view_menu.addAction("Панорамирование")
        pan_action.setIcon(load_svg_icon("public/move.svg"))
        pan_action.setCheckable(True)
        
        # Проверяем, активен ли pan tool
        pan_tool = self.canvas.tools.get('pan')
        if pan_tool:
            pan_action.setChecked(pan_tool.active)
        
        pan_action.triggered.connect(self._on_pan_tool_toggle)
        
        # Добавляем команду "Показать всё" с иконкой
        zoom_fit_action = view_menu.addAction("Показать всё")
        zoom_fit_action.setIcon(QIcon.fromTheme("zoom-fit-best"))
        zoom_fit_action.triggered.connect(self.canvas.zoom_to_fit)
        
        # Добавляем разделитель
        view_menu.addSeparator()
        
        # Добавляем команду "Повернуть сцену направо 90°" с иконкой
        rotate_left_action = view_menu.addAction("Повернуть сцену направо 90°")
        rotate_left_action.setIcon(load_svg_icon("public/rotate.svg"))
        rotate_left_action.triggered.connect(lambda: self.canvas.rotation_animation.start_rotation(False))
        
        # Добавляем команду "Повернуть сцену налево 90°" с иконкой
        rotate_right_action = view_menu.addAction("Повернуть сцену налево 90°")
        rotate_right_action.setIcon(load_svg_icon("public/rotate_right.svg"))
        rotate_right_action.triggered.connect(lambda: self.canvas.rotation_animation.start_rotation(True))
        
        return view_menu
    
    def _on_pan_tool_toggle(self, checked: bool) -> None:
        """Обработчик активации pan tool из контекстного меню.
        
        Args:
            checked: True для активации, False для деактивации
        """
        # Используем action_manager из canvas для переключения инструмента
        if hasattr(self.canvas, 'action_manager'):
            pan_action = self.canvas.action_manager.get_action('pan_tool')
            if pan_action:
                pan_action.setChecked(checked)
    
    def _on_delete_object(self) -> None:
        """Обработчик удаления объекта из контекстного меню."""
        if self.canvas.selection_manager.hover_object:
            self.canvas.scene.remove_object(self.canvas.selection_manager.hover_object)
            self.canvas.selection_manager.clear_hover()
            self.canvas.update()
