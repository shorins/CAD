from PySide6.QtCore import QObject, Signal

from .layers import LayerRecord, default_layer
from .geometry import DimensionBase

class Scene(QObject):
    # Сигнал, который будет испускаться при любом изменении в сцене
    scene_changed = Signal()

    def __init__(self):
        super().__init__()
        self.objects = []  # Список геометрических объектов
        self.layers = {"0": default_layer()}
        self.current_layer_name = "0"
        self.document_meta = {
            "source_format": "internal",
            "dxf_version": None,
            "insunits": None,
            "extmin": None,
            "extmax": None,
        }
        self.last_import_report = None

    def add_object(self, obj):
        if not getattr(obj, "layer_name", None):
            obj.layer_name = self.current_layer_name
        self.ensure_layer(obj.layer_name)
        self.objects.append(obj)
        self.recompute_dimensions()
        self.scene_changed.emit() # Уведомляем о изменении

    def remove_object(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
            self.recompute_dimensions()
            self.scene_changed.emit()

    def clear(self):
        self.objects.clear()
        self.layers = {"0": default_layer()}
        self.current_layer_name = "0"
        self.document_meta = {
            "source_format": "internal",
            "dxf_version": None,
            "insunits": None,
            "extmin": None,
            "extmax": None,
        }
        self.last_import_report = None
        self.scene_changed.emit()

    def get_object_by_id(self, object_id: str):
        for obj in self.objects:
            if getattr(obj, "object_id", None) == object_id:
                return obj
        return None

    def recompute_dimensions(self):
        for obj in self.objects:
            if isinstance(obj, DimensionBase):
                obj.recompute(self)

    def ensure_layer(self, name: str, layer: LayerRecord | None = None) -> LayerRecord:
        layer_name = name or "0"
        if layer_name not in self.layers:
            self.layers[layer_name] = layer or LayerRecord(name=layer_name)
        return self.layers[layer_name]

    def set_layers(self, layers: dict[str, LayerRecord]):
        self.layers = layers or {"0": default_layer()}
        if "0" not in self.layers:
            self.layers["0"] = default_layer()
        if self.current_layer_name not in self.layers:
            self.current_layer_name = "0"
        self.scene_changed.emit()

    def set_current_layer(self, name: str):
        self.ensure_layer(name)
        self.current_layer_name = name
        self.scene_changed.emit()
