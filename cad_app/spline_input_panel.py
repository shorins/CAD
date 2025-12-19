"""
Виджет панели ввода для построения сплайна.
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal

from .core.geometry import Point, Spline


class SplineInputPanel(QWidget):
    """Панель для ввода параметров сплайна."""
    
    spline_requested = Signal(Spline)
    spline_finish_requested = Signal()  # Сигнал для завершения текущего сплайна
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._points_count = 0
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(15)
        
        # Инструкция
        instruction_label = QLabel(
            "Кликайте для добавления точек. ПКМ или Enter для завершения."
        )
        instruction_label.setStyleSheet("color: #99FFFFFF; font-size: 13px;")
        main_layout.addWidget(instruction_label)
        
        # Счётчик точек
        self.points_label = QLabel("Точек: 0")
        self.points_label.setStyleSheet("color: #7A86CC; font-size: 13px; font-weight: 600;")
        main_layout.addWidget(self.points_label)
        
        main_layout.addStretch()
        
        # Кнопка завершить
        self.finish_button = QPushButton("Завершить (Enter)")
        self.finish_button.setMinimumWidth(150)
        self.finish_button.setMinimumHeight(32)
        self.finish_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.finish_button.setEnabled(False)
        main_layout.addWidget(self.finish_button)
        
        # Кнопка отмена
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setMinimumHeight(32)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.cancel_button)
        
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; border-top: 1px solid #1EFFFFFF; }
            QLabel { color: #99FFFFFF; font-size: 13px; font-weight: 500; }
            QPushButton {
                background-color: #7A86CC; color: white; border: none;
                border-radius: 6px; font-size: 13px; font-weight: 600; padding: 8px 20px;
            }
            QPushButton:hover { background-color: #98A3E0; }
            QPushButton:disabled { background-color: #555555; color: #888888; }
        """)
    
    def _connect_signals(self):
        self.finish_button.clicked.connect(self._on_finish_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
    
    def _on_finish_clicked(self):
        """Завершить сплайн."""
        self.spline_finish_requested.emit()
    
    def _on_cancel_clicked(self):
        """Отменить сплайн."""
        self.reset()
        self.spline_finish_requested.emit()  # Также вызовет сброс в canvas
    
    def update_points_count(self, count: int):
        """Обновляет счётчик точек."""
        self._points_count = count
        self.points_label.setText(f"Точек: {count}")
        self.finish_button.setEnabled(count >= 2)
    
    def reset(self):
        """Сбрасывает панель."""
        self._points_count = 0
        self.points_label.setText("Точек: 0")
        self.finish_button.setEnabled(False)
