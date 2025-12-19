# Определение главного окна QMainWindow

import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QStatusBar, 
                               QToolBar, QLabel, QFileDialog, QComboBox, QWidget)
from PySide6.QtGui import QAction, QIcon, QActionGroup, QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt, QSize

from .core.scene import Scene
from .core.geometry import (
    Point, Line, Circle, Arc, Rectangle, Ellipse, Polygon, Spline,
    GeometricPrimitive
)
from .core.style_manager import style_manager
from .canvas_widget import CanvasWidget
from .theme import get_stylesheet
from .settings_dialog import SettingsDialog
from .settings import settings
from .line_input_panel import LineInputPanel
from .circle_input_panel import CircleInputPanel
from .arc_input_panel import ArcInputPanel
from .rectangle_input_panel import RectangleInputPanel
from .ellipse_input_panel import EllipseInputPanel
from .polygon_input_panel import PolygonInputPanel
from .spline_input_panel import SplineInputPanel
from .icon_utils import load_svg_icon

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("shorins CAD")
        self.setGeometry(100, 100, 1000, 700)
        self.showMaximized() # во весь экран на macOS

        # Создаем экземпляр нашей Модели
        self.scene = Scene()

        self.style_combo = None

        self._create_actions()
        
        # Создаем словарь с actions инструментов для передачи в CanvasWidget
        tool_actions = {
            'select': self.select_tool_action,
            'line': self.line_tool_action,
            'circle': self.circle_tool_action,
            'arc': self.arc_tool_action,
            'rectangle': self.rectangle_tool_action,
            'ellipse': self.ellipse_tool_action,
            'polygon': self.polygon_tool_action,
            'spline': self.spline_tool_action,
            'delete': self.delete_tool_action,
        }
        
        # Создаем Представление/Контроллер и передаем ему Модель
        self.canvas = CanvasWidget(self.scene, tool_actions)
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
        self.circle_tool_action.toggled.connect(self._update_tool_label)
        self.arc_tool_action.toggled.connect(self._update_tool_label)
        self.rectangle_tool_action.toggled.connect(self._update_tool_label)
        self.ellipse_tool_action.toggled.connect(self._update_tool_label)
        self.polygon_tool_action.toggled.connect(self._update_tool_label)
        self.spline_tool_action.toggled.connect(self._update_tool_label)
        self.delete_tool_action.toggled.connect(self._update_tool_label)
        self.pan_tool_action.toggled.connect(self._update_tool_label)
        self.select_tool_action.toggled.connect(self._update_tool_label)
        
        # Устанавливаем начальное значение метки инструмента
        self._update_tool_label()
        
        # Связываем выбор инструментов с показом/скрытием панелей ввода
        self.line_tool_action.toggled.connect(self._on_line_tool_toggled)
        self.circle_tool_action.toggled.connect(self._on_circle_tool_toggled)
        self.arc_tool_action.toggled.connect(self._on_arc_tool_toggled)
        self.rectangle_tool_action.toggled.connect(self._on_tool_toggled)
        self.ellipse_tool_action.toggled.connect(self._on_tool_toggled)
        self.polygon_tool_action.toggled.connect(self._on_tool_toggled)
        self.spline_tool_action.toggled.connect(self._on_tool_toggled)

        # Связываем выделение с комбобоксом стилей
        self.canvas.selection_changed.connect(self._update_style_combo_by_selection)
        # Обновляем список стилей при изменении менеджера
        style_manager.style_changed.connect(self._reload_styles_into_combo)

        # === АВТОНАСТРОЙКА ТОЛЩИНЫ (DPI AWARE) ===
        self._setup_adaptive_line_width()

    def _create_actions(self):
        # Используем SVG иконки из папки public с белым цветом
        self.new_action = QAction(QIcon.fromTheme("document-new"), "&Новый", self)
        self.open_action = QAction(QIcon.fromTheme("document-open"), "&Открыть...", self)
        self.save_action = QAction(QIcon.fromTheme("document-save"), "&Сохранить", self)
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "&Выход", self)

        # Инструмент выделения (Стрелка)
        self.select_tool_action = QAction(QIcon.fromTheme("edit-select"), "Выделение", self)
        self.select_tool_action.setCheckable(True)
        self.select_tool_action.setChecked(True) # Делаем активным по умолчанию
        self.select_tool_action.setToolTip("Выделение объектов (Esc)")
        self.select_tool_action.setShortcut("Esc")
        self.select_tool_action.triggered.connect(self._on_select_tool_toggled)
        
        self.line_tool_action = QAction(load_svg_icon("public/line.svg"), "Линия", self)
        self.line_tool_action.setCheckable(True)
        self.line_tool_action.setToolTip("Линия (L)")
        self.line_tool_action.setShortcut("L")
        
        # Инструменты для других примитивов
        self.circle_tool_action = QAction(load_svg_icon("public/circle.svg"), "Окружность", self)
        self.circle_tool_action.setCheckable(True)
        self.circle_tool_action.setToolTip("Окружность (C)")
        self.circle_tool_action.setShortcut("C")
        
        self.arc_tool_action = QAction(load_svg_icon("public/arc.svg"), "Дуга", self)
        self.arc_tool_action.setCheckable(True)
        self.arc_tool_action.setToolTip("Дуга (A)")
        self.arc_tool_action.setShortcut("A")
        
        self.rectangle_tool_action = QAction(load_svg_icon("public/rectangle.svg"), "Прямоугольник", self)
        self.rectangle_tool_action.setCheckable(True)
        self.rectangle_tool_action.setToolTip("Прямоугольник (R)")
        # R уже занят для поворота, используем Shift+R
        self.rectangle_tool_action.setShortcut("Shift+R")
        
        self.ellipse_tool_action = QAction(load_svg_icon("public/ellipse.svg"), "Эллипс", self)
        self.ellipse_tool_action.setCheckable(True)
        self.ellipse_tool_action.setToolTip("Эллипс (E)")
        self.ellipse_tool_action.setShortcut("E")
        
        self.polygon_tool_action = QAction(load_svg_icon("public/polygon.svg"), "Многоугольник", self)
        self.polygon_tool_action.setCheckable(True)
        self.polygon_tool_action.setToolTip("Многоугольник (P)")
        self.polygon_tool_action.setShortcut("P")
        
        self.spline_tool_action = QAction(load_svg_icon("public/spline.svg"), "Сплайн", self)
        self.spline_tool_action.setCheckable(True)
        self.spline_tool_action.setToolTip("Сплайн (S)")
        self.spline_tool_action.setShortcut("S")

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

        self.style_manager_action = QAction("Менеджер стилей...", self)
        self.style_manager_action.triggered.connect(self.open_style_manager)

    def _create_menus(self):
        file_menu = self.menuBar().addMenu("&Файл")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.style_manager_action)
        file_menu.addAction(self.settings_action)
        file_menu.addAction(self.exit_action)
        self.exit_action.triggered.connect(self.close)

    def _create_toolbars(self):
        # Палитра инструментов
        edit_toolbar = QToolBar("Инструменты")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, edit_toolbar)
        
        # Группируем инструменты, чтобы одновременно был активен только один
        tool_group = QActionGroup(self)
        tool_group.addAction(self.select_tool_action)
        tool_group.addAction(self.line_tool_action)
        tool_group.addAction(self.circle_tool_action)
        tool_group.addAction(self.arc_tool_action)
        tool_group.addAction(self.rectangle_tool_action)
        tool_group.addAction(self.ellipse_tool_action)
        tool_group.addAction(self.polygon_tool_action)
        tool_group.addAction(self.spline_tool_action)
        tool_group.addAction(self.delete_tool_action)
        tool_group.addAction(self.pan_tool_action)
        
        # Добавляем инструменты в toolbar
        edit_toolbar.addAction(self.select_tool_action)
        
        edit_toolbar.addSeparator()  # Разделитель перед примитивами
        
        # Инструменты рисования примитивов
        edit_toolbar.addAction(self.line_tool_action)
        edit_toolbar.addAction(self.circle_tool_action)
        edit_toolbar.addAction(self.arc_tool_action)
        edit_toolbar.addAction(self.rectangle_tool_action)
        edit_toolbar.addAction(self.ellipse_tool_action)
        edit_toolbar.addAction(self.polygon_tool_action)
        edit_toolbar.addAction(self.spline_tool_action)
        
        edit_toolbar.addSeparator()  # Разделитель после примитивов
        
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

        # Комбобокс выбора стиля линии
        edit_toolbar.addSeparator()
        style_combo_widget = self._create_style_combo()
        edit_toolbar.addWidget(style_combo_widget)
        
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
    
    def _update_input_panels_visibility(self):
        """Обновляет видимость панелей ввода в зависимости от активного инструмента."""
        # Скрываем все панели
        for toolbar_name in ['line_input_toolbar', 'circle_input_toolbar', 'arc_input_toolbar',
                            'rectangle_input_toolbar', 'ellipse_input_toolbar', 
                            'polygon_input_toolbar', 'spline_input_toolbar']:
            if hasattr(self, toolbar_name):
                getattr(self, toolbar_name).hide()
        
        # Показываем панель для активного инструмента
        if self.line_tool_action.isChecked() and hasattr(self, 'line_input_toolbar'):
            self.line_input_toolbar.show()
        elif self.circle_tool_action.isChecked() and hasattr(self, 'circle_input_toolbar'):
            self.circle_input_toolbar.show()
        elif self.arc_tool_action.isChecked() and hasattr(self, 'arc_input_toolbar'):
            self.arc_input_toolbar.show()
        elif self.rectangle_tool_action.isChecked() and hasattr(self, 'rectangle_input_toolbar'):
            self.rectangle_input_toolbar.show()
        elif self.ellipse_tool_action.isChecked() and hasattr(self, 'ellipse_input_toolbar'):
            self.ellipse_input_toolbar.show()
        elif self.polygon_tool_action.isChecked() and hasattr(self, 'polygon_input_toolbar'):
            self.polygon_input_toolbar.show()
        elif self.spline_tool_action.isChecked() and hasattr(self, 'spline_input_toolbar'):
            self.spline_input_toolbar.show()
    
    def _on_line_tool_toggled(self, checked):
        """Обработчик переключения инструмента 'линия'."""
        if checked:
            self.delete_tool_action.setChecked(False)
            self.pan_tool_action.setChecked(False)
            self.canvas.set_pan_tool_active(False)
        self._update_input_panels_visibility()
    
    def _on_circle_tool_toggled(self, checked):
        """Обработчик переключения инструмента 'окружность'."""
        if checked:
            self.delete_tool_action.setChecked(False)
            self.pan_tool_action.setChecked(False)
            self.canvas.set_pan_tool_active(False)
        self._update_input_panels_visibility()
    
    def _on_arc_tool_toggled(self, checked):
        """Обработчик переключения инструмента 'дуга'."""
        if checked:
            self.delete_tool_action.setChecked(False)
            self.pan_tool_action.setChecked(False)
            self.canvas.set_pan_tool_active(False)
        self._update_input_panels_visibility()
    
    def _on_tool_toggled(self, checked):
        """Универсальный обработчик переключения инструмента рисования."""
        if checked:
            self.delete_tool_action.setChecked(False)
            self.pan_tool_action.setChecked(False)
            self.canvas.set_pan_tool_active(False)
        self._update_input_panels_visibility()
    
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
        line = Line(start_point, end_point)
        self.scene.add_object(line)
    
    def _on_circle_build_requested(self, circle: Circle):
        """Обработчик запроса на построение окружности из панели ввода."""
        self.scene.add_object(circle)
    
    def _on_arc_build_requested(self, arc: Arc):
        """Обработчик запроса на построение дуги из панели ввода."""
        self.scene.add_object(arc)
    
    def _on_rectangle_build_requested(self, rect: Rectangle):
        """Обработчик запроса на построение прямоугольника из панели ввода."""
        self.scene.add_object(rect)
    
    def _on_ellipse_build_requested(self, ellipse: Ellipse):
        """Обработчик запроса на построение эллипса из панели ввода."""
        self.scene.add_object(ellipse)
    
    def _on_polygon_build_requested(self, polygon: Polygon):
        """Обработчик запроса на построение многоугольника из панели ввода."""
        self.scene.add_object(polygon)
    
    def _on_spline_build_requested(self, spline: Spline):
        """Обработчик запроса на построение сплайна из панели ввода."""
        self.scene.add_object(spline)
    
    def _on_spline_finish_requested(self):
        """Обработчик завершения сплайна."""
        self.canvas.finish_spline()

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
        self.tool_label = QLabel("Инструмент: Выделение")
        
        # Добавляем виджеты на ПОЛУЧЕННЫЙ объект строки состояния
        status_bar.addPermanentWidget(self.cursor_pos_label)
        status_bar.addPermanentWidget(self.line_info_label)
        status_bar.addPermanentWidget(self.zoom_label)
        status_bar.addPermanentWidget(self.rotation_label)
        status_bar.addPermanentWidget(self.tool_label)
    
    def _on_select_tool_toggled(self, checked):
        """Обработчик включения инструмента выделения."""
        if checked:
            # Скрываем панель ввода координат, если она была открыта для линии
            if hasattr(self, 'line_input_toolbar'):
                self.line_input_toolbar.hide()

    def _on_style_selected(self, style_name):
        """Обработчик выбора стиля (для обратной совместимости)."""
        self._apply_style_selection(style_name)

    def _create_line_input_panel(self):
        """Создает панель ввода координат для линии."""
        # Создаем панель ввода
        self.line_input_panel = LineInputPanel(self)
        
        # Подключаем сигнал построения линии
        self.line_input_panel.line_requested.connect(self._on_line_build_requested)
        
        # Добавляем панель в нижнюю часть окна (BottomToolBarArea)
        # Используем addToolBar, чтобы панель вела себя как toolbar
        self.line_input_toolbar = QToolBar("Ввод координат линии")
        self.line_input_toolbar.addWidget(self.line_input_panel)
        self.line_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.line_input_toolbar)
        
        # Создаём панель ввода для окружности
        self.circle_input_panel = CircleInputPanel(self)
        self.circle_input_panel.circle_requested.connect(self._on_circle_build_requested)
        
        self.circle_input_toolbar = QToolBar("Ввод параметров окружности")
        self.circle_input_toolbar.addWidget(self.circle_input_panel)
        self.circle_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.circle_input_toolbar)
        
        # Создаём панель ввода для дуги
        self.arc_input_panel = ArcInputPanel(self)
        self.arc_input_panel.arc_requested.connect(self._on_arc_build_requested)
        
        self.arc_input_toolbar = QToolBar("Ввод параметров дуги")
        self.arc_input_toolbar.addWidget(self.arc_input_panel)
        self.arc_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.arc_input_toolbar)
        
        # Создаём панель ввода для прямоугольника
        self.rectangle_input_panel = RectangleInputPanel(self)
        self.rectangle_input_panel.rectangle_requested.connect(self._on_rectangle_build_requested)
        
        self.rectangle_input_toolbar = QToolBar("Ввод параметров прямоугольника")
        self.rectangle_input_toolbar.addWidget(self.rectangle_input_panel)
        self.rectangle_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.rectangle_input_toolbar)
        
        # Создаём панель ввода для эллипса
        self.ellipse_input_panel = EllipseInputPanel(self)
        self.ellipse_input_panel.ellipse_requested.connect(self._on_ellipse_build_requested)
        
        self.ellipse_input_toolbar = QToolBar("Ввод параметров эллипса")
        self.ellipse_input_toolbar.addWidget(self.ellipse_input_panel)
        self.ellipse_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.ellipse_input_toolbar)
        
        # Создаём панель ввода для многоугольника
        self.polygon_input_panel = PolygonInputPanel(self)
        self.polygon_input_panel.polygon_requested.connect(self._on_polygon_build_requested)
        
        self.polygon_input_toolbar = QToolBar("Ввод параметров многоугольника")
        self.polygon_input_toolbar.addWidget(self.polygon_input_panel)
        self.polygon_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.polygon_input_toolbar)
        
        # Создаём панель ввода для сплайна
        self.spline_input_panel = SplineInputPanel(self)
        self.spline_input_panel.spline_finish_requested.connect(self._on_spline_finish_requested)
        
        self.spline_input_toolbar = QToolBar("Ввод параметров сплайна")
        self.spline_input_toolbar.addWidget(self.spline_input_panel)
        self.spline_input_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.spline_input_toolbar)
        
        # Передаём ссылки на панели в canvas для получения метода построения
        self.canvas.circle_input_panel = self.circle_input_panel
        self.canvas.arc_input_panel = self.arc_input_panel
        self.canvas.rectangle_input_panel = self.rectangle_input_panel
        self.canvas.ellipse_input_panel = self.ellipse_input_panel
        self.canvas.polygon_input_panel = self.polygon_input_panel
        self.canvas.spline_input_panel = self.spline_input_panel
        
        # Показываем панель для активного инструмента
        self._update_input_panels_visibility()

    def _create_style_combo(self) -> QWidget:
        """
        Создает выпадающий список стилей линий для верхней панели инструментов.
        """
        self.style_combo = QComboBox()
        self.style_combo.setMinimumWidth(200)
        self.style_combo.setIconSize(QSize(64, 16))
        self._reload_styles_into_combo()
        self.style_combo.activated.connect(self._on_style_combo_activated)
        return self.style_combo

    def _reload_styles_into_combo(self):
        """Перезаполняет комбобокс из style_manager, сохраняя выбор."""
        if not self.style_combo:
            return

        current_data = self.style_combo.currentData()
        self.style_combo.blockSignals(True)
        self.style_combo.clear()

        # Заполняем стилями
        for name, style in style_manager.styles.items():
            icon = self._create_line_icon(style)
            self.style_combo.addItem(icon, name, name)

        # Ставим текущий стиль (глобальный) по умолчанию
        default_style = style_manager.current_style_name
        index = self.style_combo.findData(current_data or default_style)
        if index < 0:
            index = self.style_combo.findData(default_style)
        if index >= 0:
            self.style_combo.setCurrentIndex(index)

        self.style_combo.blockSignals(False)

    def _create_line_icon(self, style, width=64, height=16) -> QIcon:
        """Локальное создание иконки превью стиля (как в PropertiesPanel)."""
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        color = QColor("#DDFFFFFF")

        pen = QPen(color)
        pen.setWidthF(2)

        if style.pattern:
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern(style.pattern)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)

        painter.setPen(pen)
        painter.drawLine(0, height // 2, width, height // 2)
        painter.end()

        return QIcon(pixmap)

    def _on_style_combo_activated(self, index):
        """Обработчик выбора стиля из комбобокса."""
        style_name = self.style_combo.itemData(index)
        # Игнорируем спец-значение смешанных стилей
        if not style_name or style_name == "__MIXED__":
            return
        self._apply_style_selection(style_name)

    def _apply_style_selection(self, style_name: str):
        """
        Применяет выбранный стиль: к выделенным объектам или глобально.
        """
        selected = self.canvas.selected_objects

        if selected:
            for obj in selected:
                if isinstance(obj, Line):
                    obj.style_name = style_name
            self.scene.scene_changed.emit()
            # Обновляем комбобокс после применения, чтобы отображать текущий стиль выделения
            self._update_style_combo_by_selection(selected)
        else:
            style_manager.set_current_style(style_name)
            # Когда ничего не выделено, просто показываем глобальный стиль
            index = self.style_combo.findData(style_name)
            if index >= 0:
                self.style_combo.setCurrentIndex(index)

    def _update_style_combo_by_selection(self, selected_objects):
        """
        Синхронизирует комбобокс с текущим выделением.
        """
        if not self.style_combo:
            return

        self.style_combo.blockSignals(True)

        if not selected_objects:
            # Нет выделения -> показываем глобальный стиль
            style_name = style_manager.current_style_name
            index = self.style_combo.findData(style_name)
            if index >= 0:
                self.style_combo.setCurrentIndex(index)
        else:
            first_style = selected_objects[0].style_name
            all_same = all(obj.style_name == first_style for obj in selected_objects if isinstance(obj, Line))

            if all_same:
                index = self.style_combo.findData(first_style)
                if index >= 0:
                    self.style_combo.setCurrentIndex(index)
            else:
                mixed_index = self.style_combo.findData("__MIXED__")
                if mixed_index < 0:
                    self.style_combo.insertItem(0, "Разные стили", "__MIXED__")
                    mixed_index = 0
                self.style_combo.setCurrentIndex(mixed_index)

        self.style_combo.blockSignals(False)

    def _setup_adaptive_line_width(self):
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()
        
        # Просто передаем DPI в менеджер. 
        # Менеджер сам возьмет свою дефолтную base_s_mm (0.8) и посчитает пиксели.
        style_manager.set_base_width_px_from_dpi(dpi)
        
        # И сразу пересчитаем паттерны, так как пиксели обновились
        style_manager._recalculate_all_patterns()
        
        print(f"DPI: {dpi}. S_mm: {style_manager.base_s_mm}. S_px: {style_manager.base_width_px}")
    
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
        elif self.circle_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Окружность")
        elif self.arc_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Дуга")
        elif self.rectangle_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Прямоугольник")
        elif self.ellipse_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Эллипс")
        elif self.polygon_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Многоугольник")
        elif self.spline_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Сплайн")
        elif self.delete_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Удаление")
        elif self.pan_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Панорамирование")
        elif self.select_tool_action.isChecked():
            self.tool_label.setText("Инструмент: Выделение")

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
                "version": "1.1",
                "settings": settings.settings,
                "style_manager": style_manager.to_dict(),
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

                if "style_manager" in project_data:
                    style_manager.load_from_dict(project_data["style_manager"])
                else:
                    # Если открываем старый проект без стилей - сбрасываем на дефолт
                    # (можно добавить метод reset_to_defaults в StyleManager, 
                    # по сути это вызов _init_default_styles)
                    style_manager._init_default_styles()

                # Загружаем настройки проекта, если они есть
                if "settings" in project_data:
                    for key, value in project_data["settings"].items():
                        settings.set(key, value)
                
                # Загружаем состояние вида, если оно есть
                if "view_state" in project_data:
                    self.canvas.set_view_state(project_data["view_state"])

                # Воссоздаем объекты из файла
                # Для всех примитивов используем соответствующие from_dict методы
                PRIMITIVE_TYPES = {
                    "line": Line,
                    "circle": Circle,
                    "arc": Arc,
                    "rectangle": Rectangle,
                    "ellipse": Ellipse,
                    "polygon": Polygon,
                    "spline": Spline,
                }
                
                new_objects = []
                for obj_data in project_data.get("objects", []):
                    obj_type = obj_data.get("type")
                    if obj_type in PRIMITIVE_TYPES:
                        primitive_class = PRIMITIVE_TYPES[obj_type]
                        obj = primitive_class.from_dict(obj_data)
                        new_objects.append(obj)
                    else:
                        print(f"Неизвестный тип объекта: {obj_type}")
                
                # Добавляем все объекты в сцену
                for obj in new_objects:
                    self.scene.add_object(obj)

            except Exception as e:
                print(f"Ошибка открытия файла: {e}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec() # exec() открывает модальное окно

    def open_style_manager(self):
        from .style_editor_dialog import StyleEditorDialog
        dialog = StyleEditorDialog(self)
        dialog.exec()

def run():
    app = QApplication(sys.argv)
    
    # Применяем нашу темную тему ко всему приложению
    app.setStyleSheet(get_stylesheet())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())