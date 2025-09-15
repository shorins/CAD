import json
import copy
from PySide6.QtCore import QObject, Signal

class AppSettings(QObject):
    settings_changed = Signal()

    def __init__(self, filename="settings.json"):
        super().__init__()
        self.filename = filename
        self.defaults = {
            "grid_step": 50,
            "colors": {
                "canvas_bg": "#2D2D2D",
                "grid_minor": "#1EFFFFFF",
                "grid_major": "#61FFFFFF",
                "line_object": "#DDFFFFFF"
            }
        }
        # Используем deepcopy, чтобы вложенный словарь colors не изменялся
        self.settings = copy.deepcopy(self.defaults)
        self.load()

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.settings_changed.emit()

    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def load(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                self.settings.update(loaded_settings)
        except (FileNotFoundError, json.JSONDecodeError):
            pass # Если файла нет или он пустой, используем defaults
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def reset_to_defaults(self):
        """Сбрасывает текущие настройки к значениям по умолчанию."""
        self.settings = copy.deepcopy(self.defaults)
        self.settings_changed.emit()
        self.save() # Сразу сохраняем сброшенные настройки

settings = AppSettings()