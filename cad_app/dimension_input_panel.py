"""
Панель ввода для инструментов размеров.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox


class DimensionInputPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_tool = "linear_dimension"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)

        self.mode_label = QLabel("Тип линейного:")
        layout.addWidget(self.mode_label)

        self.linear_mode_combo = QComboBox()
        self.linear_mode_combo.addItem("Горизонтальный", "horizontal")
        self.linear_mode_combo.addItem("Вертикальный", "vertical")
        self.linear_mode_combo.addItem("Выровненный", "aligned")
        self.linear_mode_combo.setCurrentIndex(2)
        layout.addWidget(self.linear_mode_combo)

        self.hint_label = QLabel("")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.hint_label, 1)
        self.set_active_tool(self._active_tool)

    def get_linear_mode(self) -> str:
        return self.linear_mode_combo.currentData()

    def set_active_tool(self, tool_name: str):
        self._active_tool = tool_name
        # Комбобокс типа линейного размера показываем только для generic linear_dimension.
        # Для horizontal/vertical отдельных инструментов он не нужен — mode уже задан кнопкой.
        is_linear_generic = tool_name == "linear_dimension"
        self.mode_label.setVisible(is_linear_generic)
        self.linear_mode_combo.setVisible(is_linear_generic)

        hints = {
            "linear_dimension": "Шаги: первая точка, вторая точка, положение размерной линии.",
            "horizontal_dimension": "Горизонтальный размер: первая точка → вторая точка → положение.",
            "vertical_dimension": "Вертикальный размер: первая точка → вторая точка → положение.",
            "radial_dimension": "Шаги: выберите окружность/дугу, затем положение размерной линии.",
            "diameter_dimension": "Шаги: выберите окружность/дугу, затем положение диаметрального размера.",
            "angular_dimension": "Шаги: две линии или три точки угла, затем положение дуги/текста.",
        }
        self.hint_label.setText(hints.get(tool_name, ""))
