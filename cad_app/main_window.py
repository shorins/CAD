# Определение главного окна QMainWindow

import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QStatusBar, 
                               QToolBar, QLabel, QFileDialog)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

from .core.scene import Scene
from .core.geometry import Line, Point
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

        self.save_action.triggered.connect(self.save_project)
        self.open_action.triggered.connect(self.open_project)
        self.new_action.triggered.connect(self.new_project)
        self.exit_action.triggered.connect(self.close)

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

    def new_project(self):
        """Очищает сцену для создания нового проекта."""
        self.scene.clear()

    def save_project(self):
        """Сохраняет текущую сцену в JSON файл."""
        # Открываем стандартное диалоговое окно сохранения файла
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить проект", 
            "", # Начальная директория
            "JSON Files (*.json);;All Files (*)"
        )

        # Если пользователь выбрал файл, а не нажал "Отмена"
        if file_path:
            # Готовим данные для сохранения
            project_data = {
                "version": "1.0",
                "objects": [obj.to_dict() for obj in self.scene.objects]
            }

            # Открываем файл для записи
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Используем json.dump для красивой записи с отступами
                    json.dump(project_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                # TODO: Показать пользователю красивое окно с ошибкой
                print(f"Ошибка сохранения файла: {e}")

    def open_project(self):
        """Загружает сцену из JSON файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть проект",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                
                # Перед загрузкой очищаем текущую сцену
                self.scene.clear()

                # Воссоздаем объекты из файла
                new_objects = []
                for obj_data in project_data.get("objects", []):
                    obj_type = obj_data.get("type")
                    if obj_type == "line":
                        # Используем ваш метод from_dict для создания объекта
                        line_obj = Line.from_dict(obj_data)
                        new_objects.append(line_obj)
                    # TODO: Добавить обработку других типов объектов (круги, дуги и т.д.)
                
                # Добавляем все объекты в сцену одним махом (более эффективно)
                for obj in new_objects:
                    self.scene.add_object(obj)

            except Exception as e:
                print(f"Ошибка открытия файла: {e}")

def run():
    app = QApplication(sys.argv)
    
    # Применяем нашу темную тему ко всему приложению
    app.setStyleSheet(get_stylesheet())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())