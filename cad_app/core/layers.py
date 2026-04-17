"""
Модель слоя чертежа.
"""

from dataclasses import dataclass, field


@dataclass
class LayerRecord:
    """Описание DXF-совместимого слоя внутри сцены."""

    name: str
    aci_color: int = 7
    true_color: int | None = None
    linetype_name: str = "CONTINUOUS"
    lineweight: int | None = None
    flags: int = 0
    display_style_name: str = "Сплошная основная"
    plot: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "aci_color": self.aci_color,
            "true_color": self.true_color,
            "linetype_name": self.linetype_name,
            "lineweight": self.lineweight,
            "flags": self.flags,
            "display_style_name": self.display_style_name,
            "plot": self.plot,
        }

    @staticmethod
    def from_dict(data: dict) -> "LayerRecord":
        return LayerRecord(
            name=data.get("name", "0"),
            aci_color=int(data.get("aci_color", 7)),
            true_color=data.get("true_color"),
            linetype_name=data.get("linetype_name", "CONTINUOUS"),
            lineweight=data.get("lineweight"),
            flags=int(data.get("flags", 0)),
            display_style_name=data.get("display_style_name", "Сплошная основная"),
            plot=bool(data.get("plot", True)),
        )


def default_layer() -> LayerRecord:
    """Возвращает слой по умолчанию."""
    return LayerRecord(name="0")
