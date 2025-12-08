from PySide6.QtWidgets import QToolBar, QComboBox, QLabel, QWidget, QHBoxLayout
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QAction
from PySide6.QtCore import Qt, QSize, Signal

from .core.style_manager import style_manager, LineStyle
from .settings import settings

class PropertiesPanel(QToolBar):
    """
    Панель свойств.
    Содержит элементы управления для выбора стиля линии.
    """
    # Сигнал: пользователь выбрал стиль из списка (передаем имя стиля)
    style_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__("Свойства", parent)
        self.setMovable(False)
        
        # Контейнер для виджетов
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        # Подпись
        label = QLabel("Стиль:")
        layout.addWidget(label)
        
        # Выпадающий список стилей
        self.style_combo = QComboBox()
        self.style_combo.setMinimumWidth(200)
        self.style_combo.setIconSize(QSize(64, 16)) # Широкие иконки для линий
        
        # Подключаем сигнал изменения выбора
        # activated используется, чтобы ловить именно действия пользователя, 
        # а не программные изменения индекса
        self.style_combo.activated.connect(self._on_combo_activated)
        
        layout.addWidget(self.style_combo)
        
        self.addWidget(container)
        
        # Инициализация
        self._init_styles()
        
        # Подписываемся на изменения в менеджере стилей (если добавят новый стиль)
        style_manager.style_changed.connect(self._init_styles)

    def _init_styles(self):
        """Заполняет комбобокс стилями из StyleManager."""
        # Сохраняем текущий выбор перед очисткой
        current_data = self.style_combo.currentData()
        
        self.style_combo.clear()
        
        for name, style in style_manager.styles.items():
            icon = self._create_line_icon(style)
            self.style_combo.addItem(icon, name, name) # user_data = name
            
        # Восстанавливаем выбор или ставим текущий по умолчанию
        self.update_selection_state(None) # None означает "нет выделенных объектов" -> показать дефолтный

    def _create_line_icon(self, style: LineStyle, width=64, height=16) -> QIcon:
        """Генерирует иконку-превью для стиля линии."""
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        # Цвет линий в UI (делаем контрастным для темной темы)
        color = QColor("#DDFFFFFF") 
        
        pen = QPen(color)
        pen.setWidthF(2)
        
        if style.pattern:
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern(style.pattern)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)
            
        painter.setPen(pen)
        # Рисуем линию посередине иконки
        painter.drawLine(0, height // 2, width, height // 2)
        painter.end()
        
        return QIcon(pixmap)

    def _on_combo_activated(self, index):
        """Обработчик выбора пользователем."""
        style_name = self.style_combo.itemData(index)
        # Игнорируем выбор "Разные стили" (__MIXED__)
        if style_name and style_name != "__MIXED__":
            self.style_selected.emit(style_name)

    def update_selection_state(self, selected_objects):
        """
        Обновляет состояние панели в зависимости от выделенных объектов.
        
        Args:
            selected_objects (list): Список выделенных объектов или None
        """
        # Блокируем сигналы, чтобы не вызывать _on_combo_activated при обновлении UI
        self.style_combo.blockSignals(True)
        
        if not selected_objects:
            # Ничего не выделено -> показываем текущий глобальный стиль
            current_style = style_manager.current_style_name
            index = self.style_combo.findData(current_style)
            if index >= 0:
                self.style_combo.setCurrentIndex(index)
        else:
            # Есть выделение. Проверяем стили объектов.
            # Берем стиль первого объекта
            first_style = selected_objects[0].style_name
            
            # Проверяем, у всех ли объектов такой же стиль
            all_same = all(obj.style_name == first_style for obj in selected_objects)
            
            if all_same:
                index = self.style_combo.findData(first_style)
                if index >= 0:
                    self.style_combo.setCurrentIndex(index)
            else:
                # Стили разные. Добавляем временный пункт "Разные стили" если его еще нет
                mixed_index = self.style_combo.findData("__MIXED__")
                if mixed_index < 0:
                    # Добавляем временный пункт в начало
                    self.style_combo.insertItem(0, "Разные стили", "__MIXED__")
                self.style_combo.setCurrentIndex(0)  # Выбираем "Разные стили"

        self.style_combo.blockSignals(False)