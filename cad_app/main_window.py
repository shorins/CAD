# Определение главного окна QMainWindow

import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QStatusBar, 
                               QToolBar, QLabel, QFileDialog)
from PySide6.QtGui import QAction, QIcon, QActionGroup
from PySide6.QtCore import Qt

from .core.scene import Scene
from .core.geometry import Line, Point
from .canvas_widget import CanvasWidget
from .theme import get_stylesheet
from .settings_dialog import SettingsDialog
from .settings import settings
from .line_input_panel import LineInputPanel

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
        # Теперь line_tool_action и delete_tool_action уже определены
        self.canvas = CanvasWidget(self.scene, self.line_tool_action, self.delete_tool_action)
        self.setCentralWidget(self.canvas)

        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        self._create_line_input_panel()
        
        # Связываем сигнал из Canvas с методом в StatusBar
        self.canvas.cursor_pos_changed.connect(self.update_cursor_pos_label)
        self.canvas.line_info_changed.connect(self.update_line_info_label)
        
        # Связываем выбор инструмента "линия" с показом/скрытием панели ввода
        self.line_tool_action.toggled.connect(self._on_line_tool_toggled)

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

        self.delete_tool_action = QAction(QIcon.fromTheme("edit-delete"), "Удалить", self)
        self.delete_tool_action.setCheckable(True)

        # Кнопка переключения режима построения линии (θ - полярные координаты)
        self.polar_mode_action = QAction("θ", self)
        self.polar_mode_action.setCheckable(True)
        self.polar_mode_action.setToolTip("Полярные координаты (активировано: полярные, неактивировано: декартовы)")
        self.polar_mode_action.toggled.connect(self._on_polar_mode_toggled)

        self.settings_action = QAction(QIcon.fromTheme("preferences-system"), "Настройки...", self)

        self.save_action.triggered.connect(self.save_project)
        self.open_action.triggered.connect(self.open_project)
        self.new_action.triggered.connect(self.new_project)
        self.exit_action.triggered.connect(self.close)
        self.settings_action.triggered.connect(self.open_settings)

    def _create_menus(self):
        file_menu = self.menuBar().addMenu("&Файл")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addAction(self.exit_action)
        self.exit_action.triggered.connect(self.close)

    def _create_toolbars(self):
        # Палитра инструментов
        edit_toolbar = QToolBar("Инструменты")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, edit_toolbar)
        
        # Группируем инструменты, чтобы одновременно был активен только один
        tool_group = QActionGroup(self)
        tool_group.addAction(self.line_tool_action)
        tool_group.addAction(self.delete_tool_action)
        
        edit_toolbar.addAction(self.line_tool_action)
        edit_toolbar.addAction(self.delete_tool_action)
        
        # Переключатель режима построения линии
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.polar_mode_action)
        
        # Загружаем текущий режим из настроек
        current_mode = settings.get("line_construction_mode") or "cartesian"
        # Если режим полярный, кнопка должна быть активирована
        self.polar_mode_action.setChecked(current_mode == "polar")
        
    def _on_polar_mode_toggled(self, checked):
        """Обработчик переключения режима построения линии."""
        # checked = True -> полярные координаты
        # checked = False -> декартовы координаты
        mode = "polar" if checked else "cartesian"
        settings.set("line_construction_mode", mode)
        # Уведомляем canvas о изменении режима
        if hasattr(self, 'canvas'):
            self.canvas.on_construction_mode_changed()
    
    def _on_line_tool_toggled(self, checked):
        """Обработчик переключения инструмента 'линия'."""
        if hasattr(self, 'line_input_panel'):
            if checked:
                self.line_input_panel.show_panel()
            else:
                self.line_input_panel.hide_panel()
    
    def _on_line_build_requested(self, start_point: Point, end_point: Point):
        """Обработчик запроса на построение линии из панели ввода."""
        # Создаем линию из переданных точек
        line = Line(start_point, end_point)
        self.scene.add_object(line)

    def _create_status_bar(self):
        # Строка состояния
        # Вызываем метод statusBar(), который возвращает объект QStatusBar.
        # Если его нет, он автоматически создается и устанавливается для окна.
        status_bar = self.statusBar()
        
        # Создаем постоянный виджет для отображения координат
        self.cursor_pos_label = QLabel("X: 0.00, Y: 0.00")
        
        # Создаем виджет для отображения информации о линии (длина, угол)
        self.line_info_label = QLabel("")
        
        # Добавляем виджеты на ПОЛУЧЕННЫЙ объект строки состояния
        status_bar.addPermanentWidget(self.cursor_pos_label)
        status_bar.addPermanentWidget(self.line_info_label)
    
    def _create_line_input_panel(self):
        """Создает панель ввода координат для линии."""
        # Создаем панель ввода
        self.line_input_panel = LineInputPanel(self)
        
        # Подключаем сигнал построения линии
        self.line_input_panel.line_requested.connect(self._on_line_build_requested)
        
        # Добавляем панель в нижнюю часть окна (BottomToolBarArea)
        # Используем addToolBar, чтобы панель вела себя как toolbar
        input_toolbar = QToolBar("Ввод координат")
        input_toolbar.addWidget(self.line_input_panel)
        input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, input_toolbar)
        
        # Показываем панель, если инструмент "линия" активен (он активен по умолчанию)
        if self.line_tool_action.isChecked():
            self.line_input_panel.show_panel()
        else:
            self.line_input_panel.hide_panel()

    def update_cursor_pos_label(self, pos):
        # Слот, который обновляет текст с координатами
        scene_pos = self.canvas.map_to_scene(pos)
        self.cursor_pos_label.setText(f"X: {scene_pos.x():.2f}, Y: {scene_pos.y():.2f}")
    
    def update_line_info_label(self, info_text):
        # Слот, который обновляет информацию о линии
        self.line_info_label.setText(info_text)

    def new_project(self):
        """Очищает сцену и сбрасывает настройки для создания нового проекта."""
        self.scene.clear()
        settings.reset_to_defaults()

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
                "settings": settings.settings,
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
                
                # Перед загрузкой очищаем текущую сцену и сбрасываем настройки
                self.scene.clear()
                settings.reset_to_defaults()

                # Загружаем настройки проекта, если они есть
                if "settings" in project_data:
                    for key, value in project_data["settings"].items():
                        settings.set(key, value)

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

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec() # exec() открывает модальное окно

def run():
    app = QApplication(sys.argv)
    
    # Применяем нашу темную тему ко всему приложению
    app.setStyleSheet(get_stylesheet())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())