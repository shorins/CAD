"""
Простой менеджер слоев.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
    QInputDialog,
)


class LayerManagerDialog(QDialog):
    """Минимальный менеджер слоев: добавление и удаление."""

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.layer_names = list(scene.layers.keys())
        self.setWindowTitle("Менеджер слоев")
        self.resize(320, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.layers_list = QListWidget(self)
        for name in self.layer_names:
            self.layers_list.addItem(name)
        self.layers_list.setCurrentRow(max(0, self.layer_names.index(self.scene.current_layer_name)))
        layout.addWidget(self.layers_list)

        actions_layout = QHBoxLayout()
        add_button = QPushButton("Добавить")
        remove_button = QPushButton("Удалить")
        add_button.clicked.connect(self._add_layer)
        remove_button.clicked.connect(self._remove_layer)
        actions_layout.addWidget(add_button)
        actions_layout.addWidget(remove_button)
        layout.addLayout(actions_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_layer(self):
        layer_name, accepted = QInputDialog.getText(self, "Новый слой", "Имя слоя:")
        if not accepted or not layer_name.strip():
            return
        name = layer_name.strip()
        if name in self.layer_names:
            QMessageBox.warning(self, "Слой уже существует", f"Слой '{name}' уже есть в документе.")
            return
        self.layer_names.append(name)
        self.layers_list.addItem(name)

    def _remove_layer(self):
        current_item = self.layers_list.currentItem()
        if current_item is None:
            return

        layer_name = current_item.text()
        if layer_name == "0":
            QMessageBox.warning(self, "Нельзя удалить слой", "Слой '0' является обязательным.")
            return

        if any(getattr(obj, "layer_name", "0") == layer_name for obj in self.scene.objects):
            QMessageBox.warning(
                self,
                "Слой используется",
                f"Слой '{layer_name}' нельзя удалить, пока на нем есть объекты.",
            )
            return

        self.layer_names.remove(layer_name)
        self.layers_list.takeItem(self.layers_list.currentRow())

    def accept(self):
        existing = set(self.scene.layers.keys())
        desired = set(self.layer_names)

        for layer_name in existing - desired:
            if layer_name != "0":
                self.scene.layers.pop(layer_name, None)

        for layer_name in self.layer_names:
            self.scene.ensure_layer(layer_name)

        if self.scene.current_layer_name not in self.scene.layers:
            self.scene.set_current_layer("0")

        super().accept()
