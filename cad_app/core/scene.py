from PySide6.QtCore import QObject, Signal
from.geometry import Line # и другие примитивы

class Scene(QObject):
    # Сигнал, который будет испускаться при любом изменении в сцене
    scene_changed = Signal()

    def __init__(self):
        super().__init__()
        self.objects = []  # Список геометрических объектов

    def add_object(self, obj):
        self.objects.append(obj)
        self.scene_changed.emit() # Уведомляем о изменении

    def remove_object(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
            self.scene_changed.emit()

    def clear(self):
        self.objects.clear()
        self.scene_changed.emit()