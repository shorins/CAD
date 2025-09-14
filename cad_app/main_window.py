# Определение главного окна QMainWindow

import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QStatusBar, 
                               QToolBar, QLabel)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

from .core.scene import Scene
from .canvas_widget import CanvasWidget
from .theme import get_stylesheet

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("shorins CAD")
        self.setGeometry(100, 100, 800, 600)
        self.showMaximized() # во весь экран на macOS

        # Создаем экземпляр нашей Модели
        self.scene = Scene()

        self._create_actions()
        
        # Создаем Представление/Контроллер и передаем ему Модель
        # Теперь line_tool_action уже определен
        self.canvas = CanvasWidget(self.scene, self.line_tool_action)
        self.setCentralWidget(self.canvas)

        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        
        # Связываем сигнал из Canvas с методом в StatusBar
        self.canvas.cursor_pos_changed.connect(self.update_cursor_pos_label)

    def _create_actions(self):
        # Используем стандартные иконки Qt для простоты
        # Для реального проекта лучше использовать SVG-иконки
        self.new_action = QAction(QIcon.fromTheme("document-new"), "&Новый", self)
        self.open_action = QAction(QIcon.fromTheme("document-open"), "&Открыть...", self)
        self.save_action = QAction(QIcon.fromTheme("document-save"), "&Сохранить", self)
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "&Выход", self)
        
        self.line_tool_action = QAction(QIcon.fromTheme("draw-path"), "Линия", self)
        self.line_tool_action.setCheckable(True)
        self.line_tool_action.setChecked(True) # Активен по умолчанию

    def _create_menus(self):
        file_menu = self.menuBar().addMenu("&Файл")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        self.exit_action.triggered.connect(self.close)

    def _create_toolbars(self):
        # Палитра инструментов
        edit_toolbar = QToolBar("Инструменты")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, edit_toolbar)
        edit_toolbar.addAction(self.line_tool_action)
        # TODO: Добавить другие инструменты и сгруппировать их

    def _create_status_bar(self):
        # Строка состояния
        # Вызываем метод statusBar(), который возвращает объект QStatusBar.
        # Если его нет, он автоматически создается и устанавливается для окна.
        status_bar = self.statusBar()
        
        # Создаем постоянный виджет для отображения координат
        self.cursor_pos_label = QLabel("X: 0.00, Y: 0.00")
        
        # Добавляем виджет на ПОЛУЧЕННЫЙ объект строки состояния
        status_bar.addPermanentWidget(self.cursor_pos_label)

    def update_cursor_pos_label(self, pos):
        # Слот, который обновляет текст с координатами
        scene_pos = self.canvas.map_to_scene(pos)
        self.cursor_pos_label.setText(f"X: {scene_pos.x():.2f}, Y: {scene_pos.y():.2f}")


def run():
    app = QApplication(sys.argv)
    
    # Применяем нашу темную тему ко всему приложению
    app.setStyleSheet(get_stylesheet())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())