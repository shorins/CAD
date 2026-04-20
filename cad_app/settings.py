import json
import copy
from PySide6.QtCore import QObject, Signal
from .font_manager import DIMENSION_FONT_MODE_GOST_ITALIC

class AppSettings(QObject):
    settings_changed = Signal()

    def __init__(self):
        super().__init__()
        self.defaults = {
            "grid_step": 50,
            "line_construction_mode": "cartesian",  # "cartesian" или "polar"
            "angle_units": "degrees",  # "degrees" или "radians"
            "dimensions": {
                "text_height_mm": 3.5,
                "arrow_size_mm": 3.5,
                "font_mode": DIMENSION_FONT_MODE_GOST_ITALIC,
            },
            "colors": {
                "canvas_bg": "#2D2D2D",
                "grid_minor": "#1EFFFFFF",
                "grid_major": "#61FFFFFF",
                "line_object": "#DDFFFFFF"
            }
        }
        # Используем deepcopy, чтобы вложенный словарь colors не изменялся
        self.settings = copy.deepcopy(self.defaults)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.settings_changed.emit()

    def save(self):
        # This method is no longer needed as settings are not saved to a global file
        pass

    def load():
        # This method is no longer needed as settings are not loaded from a global file
        pass

    def reset_to_defaults(self):
        """Сбрасывает текущие настройки к значениям по умолчанию."""
        self.settings = copy.deepcopy(self.defaults)
        self.settings_changed.emit()

settings = AppSettings()
