from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QListWidgetItem, QWidget, QLabel, QDoubleSpinBox, 
                               QGroupBox, QFormLayout, QFrame, QSplitter, QPushButton,
                               QSlider, QStackedWidget)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor

from .core.style_manager import style_manager

class StyleEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Менеджер стилей линий (ГОСТ 2.303-68)")
        self.resize(800, 500)
        
        # Основной Layout
        main_layout = QVBoxLayout(self)

        # === ВЕРХНЯЯ ПАНЕЛЬ: Настройка S ===
        top_panel = QGroupBox("Глобальные настройки")
        top_layout = QHBoxLayout(top_panel)
        
        lbl_s = QLabel("Базовая толщина (S):")
        self.spin_s = QDoubleSpinBox()
        self.spin_s.setRange(0.1, 5.0)
        self.spin_s.setSingleStep(0.1)
        self.spin_s.setSuffix(" мм")
        self.spin_s.setValue(style_manager.base_s_mm)
        self.spin_s.valueChanged.connect(self._on_s_changed)
        
        top_layout.addWidget(lbl_s)
        top_layout.addWidget(self.spin_s)
        top_layout.addStretch()
        
        main_layout.addWidget(top_panel)

        # === ЦЕНТРАЛЬНАЯ ЧАСТЬ: Splitter (Список | Настройки) ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ЛЕВАЯ ЧАСТЬ: Список стилей
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(64, 32))
        self.list_widget.currentItemChanged.connect(self._on_style_selected)
        splitter.addWidget(self.list_widget)
        
        # ПРАВАЯ ЧАСТЬ: Панель настроек
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        
        # Инфо о стиле
        self.lbl_name = QLabel("<h2>Название стиля</h2>")
        self.lbl_desc = QLabel("Описание")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #888;")
        
        self.settings_layout.addWidget(self.lbl_name)
        self.settings_layout.addWidget(self.lbl_desc)
        
        # Динамические настройки (Dash/Gap)
        self.params_group = QGroupBox("Параметры паттерна (в мм)")
        self.params_layout = QFormLayout(self.params_group)
        self.settings_layout.addWidget(self.params_group)
        
        # Виджеты для Dash
        self.spin_dash = QDoubleSpinBox()
        self.spin_dash.setSuffix(" мм")
        self.spin_dash.valueChanged.connect(self._on_params_changed)
        
        # Виджеты для Gap
        self.spin_gap = QDoubleSpinBox()
        self.spin_gap.setSuffix(" мм")
        self.spin_gap.valueChanged.connect(self._on_params_changed)

        self.params_layout.addRow("Длина штриха:", self.spin_dash)
        self.params_layout.addRow("Длина пробела:", self.spin_gap)
        
        # Placeholder, когда настройки недоступны
        self.lbl_no_params = QLabel("Для этого стиля настройки размеров недоступны\n(фиксированный или спец. рендеринг)")
        self.lbl_no_params.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_params.setStyleSheet("color: #666; padding: 20px; border: 1px dashed #444;")
        self.settings_layout.addWidget(self.lbl_no_params)

        self.settings_layout.addStretch()
        
        splitter.addWidget(self.settings_container)
        splitter.setSizes([250, 550])
        main_layout.addWidget(splitter)
        
        # === НИЖНЯЯ ПАНЕЛЬ: Кнопки ===
        btn_layout = QHBoxLayout()
        btn_create = QPushButton("Создать новый стиль")
        btn_create.setDisabled(True) # Пока заглушка
        btn_create.setToolTip("Функция в разработке")
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_create)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)

        # Инициализация
        self._load_styles()
        
        # Если стили обновятся извне
        style_manager.style_changed.connect(self._refresh_icons)

    def _load_styles(self):
        """Загружает стили в список."""
        self.list_widget.clear()
        
        # Сортируем: сначала стандартные, потом пользовательские
        styles = sorted(style_manager.styles.values(), key=lambda s: (not s.is_default, s.name))
        
        for style in styles:
            item = QListWidgetItem(style.name)
            item.setData(Qt.ItemDataRole.UserRole, style.name)
            self._update_item_icon(item, style)
            self.list_widget.addItem(item)
            
        # Выбираем первый
        self.list_widget.setCurrentRow(0)

    def _update_item_icon(self, item, style):
        """Рисует превью линии для иконки."""
        pixmap = QPixmap(128, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        
        # Цвет линий (для превью белый/светлый)
        pen_color = QColor("#DDFFFFFF")
        pen = QPen(pen_color)
        
        # Толщина для превью (немного утрированная, чтобы было видно)
        preview_width = 2.0 * style.width_mult
        pen.setWidthF(max(1.5, preview_width))
        
        if style.pattern:
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern(style.pattern)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)
            
        painter.setPen(pen)
        
        # Рисуем линию (прямую, даже для волнистой в превью пока прямая)
        # Можно доработать render_utils для генерации превью
        painter.drawLine(0, 16, 128, 16)
        painter.end()
        
        item.setIcon(QIcon(pixmap))

    def _refresh_icons(self):
        """Обновляет иконки (например, если S изменилась)."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            style = style_manager.get_style(name)
            self._update_item_icon(item, style)

    def _on_s_changed(self, val):
        """Обработчик изменения глобальной S."""
        # Обновляем менеджер (он сам пересчитает пиксели через DPI, т.к. мы в main_window это настроили)
        # Но нам нужно дернуть пересчет пикселей.
        # В StyleManager мы храним base_width_px. 
        # Нам нужно получить текущий DPI, чтобы корректно обновить base_width_px.
        
        # Получаем DPI (можно сохранить в self при init)
        screen = self.screen()
        dpi = screen.logicalDotsPerInch()
        
        style_manager.base_s_mm = val
        style_manager.set_base_width_px_from_dpi(dpi)
        
        # Также нужно пересчитать паттерны, т.к. коэффициенты зависят от S
        style_manager._recalculate_all_patterns()
        
        # Принудительно обновляем вид
        style_manager.style_changed.emit()

    def _on_style_selected(self, current, previous):
        if not current:
            return
            
        name = current.data(Qt.ItemDataRole.UserRole)
        style = style_manager.get_style(name)
        
        self.lbl_name.setText(f"<h2>{style.name}</h2>")
        self.lbl_desc.setText(style.description)
        
        # Блокируем сигналы, чтобы установка значений не вызывала update
        self.spin_dash.blockSignals(True)
        self.spin_gap.blockSignals(True)
        
        if style.params:
            self.params_group.show()
            self.lbl_no_params.hide()
            
            # Настройка диапазонов согласно ГОСТ (хардкод правил валидации)
            self._setup_limits(style.name)
            
            self.spin_dash.setValue(style.params.get('dash', 0))
            self.spin_gap.setValue(style.params.get('gap', 0))
        else:
            self.params_group.hide()
            self.lbl_no_params.show()
            
        self.spin_dash.blockSignals(False)
        self.spin_gap.blockSignals(False)

    def _setup_limits(self, name):
        """Устанавливает min/max для спинбоксов по ГОСТу."""
        # Дефолтные широкие границы
        d_min, d_max = 1.0, 50.0
        g_min, g_max = 1.0, 20.0
        
        if name == "Штриховая":
            d_min, d_max = 2.0, 8.0
            g_min, g_max = 1.0, 2.0
        elif name == "Штрихпунктирная тонкая":
            d_min, d_max = 5.0, 30.0
            g_min, g_max = 3.0, 5.0
        elif name == "Штрихпунктирная утолщенная":
            d_min, d_max = 3.0, 8.0
            g_min, g_max = 3.0, 4.0
        elif name == "Штрихпунктирная с двумя точками":
            d_min, d_max = 5.0, 30.0
            g_min, g_max = 4.0, 6.0
            
        self.spin_dash.setRange(d_min, d_max)
        self.spin_dash.setToolTip(f"ГОСТ: {d_min} ... {d_max} мм")
        
        self.spin_gap.setRange(g_min, g_max)
        self.spin_gap.setToolTip(f"ГОСТ: {g_min} ... {g_max} мм")

    def _on_params_changed(self):
        """Пользователь подвигал значения."""
        current_item = self.list_widget.currentItem()
        if not current_item: return
        
        name = current_item.data(Qt.ItemDataRole.UserRole)
        
        new_params = {
            'dash': self.spin_dash.value(),
            'gap': self.spin_gap.value()
        }
        
        style_manager.update_style_params(name, new_params)