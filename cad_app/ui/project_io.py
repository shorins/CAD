"""Project I/O manager for saving and loading projects."""

import json
from PySide6.QtWidgets import QMainWindow, QFileDialog

from ..core.geometry import Line
from ..settings import settings


class ProjectIO:
    """Handles project file operations (save, open, new)."""
    
    def __init__(self, main_window: QMainWindow):
        """Initialize the project I/O manager.
        
        Args:
            main_window: Reference to MainWindow
        """
        self.main_window = main_window
    
    def new_project(self) -> None:
        """Создает новый проект (очищает сцену и сбрасывает настройки)."""
        self.main_window.scene.clear()
        settings.reset_to_defaults()
    
    def save_project(self) -> None:
        """Сохраняет текущий проект в JSON файл."""
        # Открываем диалог сохранения файла
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Сохранить проект",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            # Сериализуем проект
            project_data = self._serialize_project()
            
            # Сохраняем в файл
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                # TODO: Показать пользователю красивое окно с ошибкой
                print(f"Ошибка сохранения файла: {e}")
    
    def open_project(self) -> None:
        """Загружает проект из JSON файла."""
        # Открываем диалог открытия файла
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Открыть проект",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                
                # Десериализуем проект
                self._deserialize_project(project_data)
                
            except Exception as e:
                # TODO: Показать пользователю красивое окно с ошибкой
                print(f"Ошибка открытия файла: {e}")
    
    def _serialize_project(self) -> dict:
        """Сериализует текущий проект в словарь.
        
        Returns:
            Словарь с данными проекта
        """
        return {
            "version": "1.0",
            "settings": settings.settings,
            "view_state": self.main_window.canvas.get_view_state(),
            "objects": [obj.to_dict() for obj in self.main_window.scene.objects]
        }
    
    def _deserialize_project(self, data: dict) -> None:
        """Десериализует проект из словаря.
        
        Args:
            data: Словарь с данными проекта
        """
        # Очищаем текущую сцену и сбрасываем настройки
        self.main_window.scene.clear()
        settings.reset_to_defaults()
        
        # Загружаем настройки проекта
        if "settings" in data:
            for key, value in data["settings"].items():
                settings.set(key, value)
        
        # Загружаем состояние вида
        if "view_state" in data:
            self.main_window.canvas.set_view_state(data["view_state"])
        
        # Воссоздаем объекты из файла
        new_objects = []
        for obj_data in data.get("objects", []):
            obj_type = obj_data.get("type")
            if obj_type == "line":
                line_obj = Line.from_dict(obj_data)
                new_objects.append(line_obj)
            # TODO: Добавить обработку других типов объектов
        
        # Добавляем все объекты в сцену
        for obj in new_objects:
            self.main_window.scene.add_object(obj)
