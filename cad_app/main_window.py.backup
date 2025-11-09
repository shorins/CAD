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
from .icon_utils import load_svg_icon

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
        
        # Подключаем zoom_fit_action после создания canvas
        self.zoom_fit_action.triggered.connect(self.canvas.zoom_to_fit)

        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        self._create_line_input_panel()
        
        # Связываем сигнал из Canvas с методом в StatusBar
        self.canvas.cursor_pos_changed.connect(self.update_cursor_pos_label)
        self.canvas.line_info_changed.connect(self.update_line_info_label)
        
        # Подключаем сигналы для обновления масштаба и поворота
        self.canvas.zoom_changed.connect(self.update_zoom_label)
        self.canvas.rotation_changed.connect(self.update_rotation_label)
        
        # Подключаем сигналы для обновления метки инструмента
        self.line_tool_action.toggled.connect(self._update_tool_label)
        self.delete_tool_action.toggled.connect(self._update_tool_label)
        self.pan_tool_action.toggled.connect(self._update_tool_label)
        
        # Устанавливаем начальное значение метки инструмента
        self._update_tool_label()
        
        # Связываем выбор инструмента "линия" с показом/скрытием панели ввода
        self.line_tool_action.toggled.connect(self._on_line_tool_toggled)

    def _create_actions(self):
        # Используем SVG иконки из папки public с белым цветом
        self.new_action = QAction(QIcon.fromTheme("document-new"), "&Новый", self)
        self.open_action = QAction(QIcon.fromTheme("document-open"), "&Открыть...", self)
        self.save_action = QAction(QIcon.fromTheme("document-save"), "&Сохранить", self)
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "&Выход", self)
        
        self.line_tool_action = QAction(load_svg_icon("public/line.svg"), "Линия", self)
        self.line_tool_action.setCheckable(True)
        self.line_tool_action.setChecked(True) # Активен по умолчанию

        self.delete_tool_action = QAction(load_svg_icon("public/delete.svg"), "Удалить", self)
        self.delete_tool_action.setCheckable(True)
        self.delete_tool_action.triggered.connect(self._on_delete_tool_toggled)

        # Pan tool action
        self.pan_tool_action = QAction(load_svg_icon("public/move.svg"), "Рука", self)
        self.pan_tool_action.setToolTip("Инструмент панорамирования (H)")
        self.pan_tool_action.setShortcut("H")
        self.pan_tool_action.setCheckable(True)
        self.pan_tool_action.triggered.connect(self._on_pan_tool_toggled)

        # Кнопка zoom to fit - оставляем стандартную иконку
        self.zoom_fit_action = QAction(QIcon.fromTheme("zoom-fit-best"), "По размеру", self)
        self.zoom_fit_action.setToolTip("Показать все объекты (Ctrl+0)")
        self.zoom_fit_action.setShortcut("Ctrl+0")

        # Кнопки поворота вида
        self.rotate_left_action = QAction(load_svg_icon("public/rotate.svg"), "Повернуть влево", self)
        self.rotate_left_action.setToolTip("Повернуть вид по часовой стрелке (R + Left)")
        self.rotate_left_action.triggered.connect(self._on_rotate_left)

        self.rotate_right_action = QAction(load_svg_icon("public/rotate_right.svg"), "Повернуть вправо", self)
        self.rotate_right_action.setToolTip("Повернуть вид против часовой стрелки (R + Right)")
        self.rotate_right_action.triggered.connect(self._on_rotate_right)

        # Кнопка переключения режима построения линии (θ - полярные координаты)
        self.polar_mode_action = QAction(load_svg_icon("public/polar.svg"), "θ", self)
        self.polar_mode_action.setCheckable(True)
        self.polar_mode_action.setToolTip("Полярные координаты (активировано: полярные, неактивировано: декартовы)")
        self.polar_mode_action.toggled.connect(self._on_polar_mode_toggled)

        self.settings_action = QAction(QIcon.fromTheme("preferences-system"), "Настройки...", self)

        self.save_action.triggered.connect(self.save_project)
        self.open_action.triggered.connect(self.open_project)
        self.new_action.triggered.connect(self.new_project)
        self.exit_action.triggered.connect(self.close)
        self.settings_action.triggered.connect(self.open_settings)
        # Note: zoom_fit_action will be connected after canvas is created

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
        tool_group.addAction(self.pan_tool_action)
        
        edit_toolbar.addAction(self.line_tool_action)
        edit_toolbar.addAction(self.delete_tool_action)
        edit_toolbar.addAction(self.pan_tool_action)
        
        # Zoom to fit
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.zoom_fit_action)
        
        # Кнопки поворота вида
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.rotate_left_action)
        edit_toolbar.addAction(self.rotate_right_action)
        
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
    
    def _deactivate_all_tools(self):
        """Деактивирует все инструменты."""
        self.line_tool_action.setChecked(False)
        self.delete_tool_action.setChecked(False)
        self.pan_tool_action.setChecked(False)
        self.canvas.set_pan_tool_active(False)
    
    def _on_line_tool_toggled(self, checked):
        """Обработчик переключения инструмента 'линия'."""
        if checked:
            # Деактивируем другие инструменты
            self.delete_tool_action.setChecked(False)
            self.pan_tool_action.setChecked(False)
            self.canvas.set_pan_tool_active(False)
        
        if hasattr(self, 'line_input_toolbar'):
            if checked:
                self.line_input_toolbar.show()
            else:
                self.line_input_toolbar.hide()
    
    def _on_delete_tool_toggled(self, checked):
        """Обработчик переключения инструмента удаления."""
        if checked:
            # Деактивируем другие инструменты
            self.line_tool_action.setChecked(False)
            self.pan_tool_action.setChecked(False)
            self.canvas.set_pan_tool_active(False)
    
    def _on_pan_tool_toggled(self, checked):
        """Обрабатывает переключение инструмента панорамирования."""
        if checked:
            # Деактивируем другие инструменты
            self.line_tool_action.setChecked(False)
            self.delete_tool_action.setChecked(False)
        
        # Активируем/деактивируем pan tool в canvas
        self.canvas.set_pan_tool_active(checked)
    
    def _on_rotate_left(self):
        """Обработчик кнопки поворота влево (по часовой стрелке)."""
        self.canvas._apply_rotation(clockwise=True)
    
    def _on_rotate_right(self):
        """Обработчик кнопки поворота вправо (против часовой стрелки)."""
        self.canvas._apply_rotation(clockwise=False)
    
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
        
        # Создаем новые виджеты для отображения масштаба, поворота и инструмента
        self.zoom_label = QLabel("Масштаб: 100%")
        self.rotation_label = QLabel("Поворот: 0°")
        self.tool_label = QLabel("Инструмент: Линия")
        
        # Добавляем виджеты на ПОЛУЧЕННЫЙ объект строки состояния
        status_bar.addPermanentWidget(self.cursor_pos_label)
        status_bar.addPermanentWidget(self.line_info_label)
        status_bar.addPermanentWidget(self.zoom_label)
        status_bar.addPermanentWidget(self.rotation_label)
        status_bar.addPermanentWidget(self.tool_label)
    
    def _create_line_input_panel(self):
        """Создает панель ввода координат для линии."""
        # Создаем панель ввода
        self.line_input_panel = LineInputPanel(self)
        
        # Подключаем сигнал построения линии
        self.line_input_panel.line_requested.connect(self._on_line_build_requested)
        
        # Добавляем панель в нижнюю часть окна (BottomToolBarArea)
        # Используем addToolBar, чтобы панель вела себя как toolbar
        self.line_input_toolbar = QToolBar("Ввод координат")
        self.line_input_toolbar.addWidget(self.line_input_panel)
        self.line_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.line_input_toolbar)
        
        # Показываем панель, если инструмент "линия" активен (он активен по умолчанию)
        if self.line_tool_action.isChecked():
            self.line_input_toolbar.show()
        else:
            self.line_input_toolbar.hide()

    def update_cursor_pos_label(self, pos):
        # Слот, который обновляет текст с координатами
        # map_to_scene уже возвращает координаты в математической системе (Y вверх)
        scene_pos = self.canvas.map_to_scene(pos)
        self.cursor_pos_label.setText(f"X: {scene_pos.x():.2f}, Y: {scene_pos.y():.2f}")
    
    def update_line_info_label(self, info_text):
        # Слот, который обновляет информацию о линии
        self.line_info_label.setText(info_text)
    
    def update_zoom_label(self, zoom_factor: float):
        """Обновляет метку масштаба."""
        zoom_percent = int(zoom_factor * 100)
        self.zoom_label.setText(f"Масштаб: {zoom_percent}%")
    
    def update_rotation_label(self, rotation_angle: float):
        """Обновляет метку угла поворота."""
        # Инвертируем угол для отображения (360 - angle), чтобы соответствовать визуальному направлению
        # При повороте по часовой стрелке угол увеличивается: 0 -> 90 -> 180 -> 270
        display_angle = (360 - int(rotation_angle)) % 360
        self.rotation_label.setText(f"Поворот: {display_angle}°")
    
    def _update_tool_label(self):
        """Обновляет метку активного инструмента."""
        if self.line_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Линия")
        elif self.delete_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Удаление")
        elif self.pan_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Панорамирование")

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
                "view_state": self.canvas.get_view_state(),
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
                
                # Загружаем состояние вида, если оно есть
                if "view_state" in project_data:
                    self.canvas.set_view_state(project_data["view_state"])

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