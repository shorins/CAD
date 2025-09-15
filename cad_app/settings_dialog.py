from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QSpinBox, 
                               QPushButton, QDialogButtonBox, QColorDialog, QLabel)
from PySide6.QtGui import QColor
from .settings import settings

class ColorPickerButton(QPushButton):
    """Кастомная кнопка для выбора цвета с предпросмотром."""
    def __init__(self, initial_color, parent=None):
        super().__init__(parent)
        # Устанавливаем стиль и текст при инициализации
        self.set_color(QColor(initial_color))
        self.clicked.connect(self.pick_color)

    def pick_color(self):
        new_color = QColorDialog.getColor(self.color, self, "Выберите цвет")
        if new_color.isValid():
            self.set_color(new_color)

    def set_color(self, color):
        """Обновляет цвет и внешний вид кнопки."""
        self.color = QColor(color)
        self.setText(self.color.name(QColor.NameFormat.HexArgb))
        self.setStyleSheet(f"background-color: {self.color.name()}; color: white; border: 1px solid white;")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # 1. Настройка шага сетки
        self.grid_step_input = QSpinBox()
        self.grid_step_input.setRange(10, 500)
        form_layout.addRow("Шаг сетки (пиксели):", self.grid_step_input)

        # 2. Настройка цветов
        form_layout.addRow(QLabel("<b>Цвета:</b>"))
        self.canvas_bg_picker = ColorPickerButton("#000000")
        self.grid_minor_picker = ColorPickerButton("#000000")
        self.grid_major_picker = ColorPickerButton("#000000")
        self.line_object_picker = ColorPickerButton("#000000")

        form_layout.addRow("Фон холста:", self.canvas_bg_picker)
        form_layout.addRow("Сетка (второстепенная):", self.grid_minor_picker)
        form_layout.addRow("Сетка (основная):", self.grid_major_picker)
        form_layout.addRow("Объект (линия):", self.line_object_picker)
        
        layout.addLayout(form_layout)

        # Кнопки OK, Отмена и Сбросить
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(button_box)
        
        self.load_settings_to_ui()

    def load_settings_to_ui(self):
        """Загружает настройки из объекта settings в элементы UI с проверками."""
        grid_step = settings.get("grid_step") or settings.defaults["grid_step"]
        self.grid_step_input.setValue(grid_step)
        
        colors = settings.get("colors") or settings.defaults["colors"]
        self.canvas_bg_picker.set_color(colors.get("canvas_bg", "#000000"))
        self.grid_minor_picker.set_color(colors.get("grid_minor", "#000000"))
        self.grid_major_picker.set_color(colors.get("grid_major", "#000000"))
        self.line_object_picker.set_color(colors.get("line_object", "#000000"))
        
    def restore_defaults(self):
        """Сбрасывает настройки в UI к значениям по умолчанию."""
        # Мы не меняем глобальный объект settings, а только отображение в окне
        self.grid_step_input.setValue(settings.defaults["grid_step"])
        colors = settings.defaults["colors"]
        self.canvas_bg_picker.set_color(colors["canvas_bg"])
        self.grid_minor_picker.set_color(colors["grid_minor"])
        self.grid_major_picker.set_color(colors["grid_major"])
        self.line_object_picker.set_color(colors["line_object"])

    def accept(self):
        """Применяет и сохраняет настройки."""
        settings.set("grid_step", self.grid_step_input.value())
        colors = {
            "canvas_bg": self.canvas_bg_picker.color.name(QColor.NameFormat.HexArgb),
            "grid_minor": self.grid_minor_picker.color.name(QColor.NameFormat.HexArgb),
            "grid_major": self.grid_major_picker.color.name(QColor.NameFormat.HexArgb),
            "line_object": self.line_object_picker.color.name(QColor.NameFormat.HexArgb)
        }
        settings.set("colors", colors)
        settings.save()
        super().accept()