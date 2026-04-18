"""
Сопоставления DXF-атрибутов и внутренней модели приложения.
"""

from __future__ import annotations

from typing import Iterable

from ..core.layers import LayerRecord

DEFAULT_DXF_VERSION = "R2010"
DEFAULT_LAYER_NAME = "0"
MIXED_VALUE = "__MIXED__"

DXF_LINETYPE_TO_STYLE = {
    "CONTINUOUS": "Сплошная основная",
    "THIN": "Сплошная тонкая",
    "BYLAYER": "Сплошная основная",
    "BYBLOCK": "Сплошная основная",
    "DASHED": "Штриховая",
    "HIDDEN": "Штриховая",
    "CENTER": "Штрихпунктирная тонкая",
    "CENTER2": "Штрихпунктирная тонкая",
    "CENTERX2": "Штрихпунктирная тонкая",
    "PHANTOM": "Штрихпунктирная с двумя точками",
    "PHANTOM2": "Штрихпунктирная с двумя точками",
    "BATTING": "Сплошная волнистая",
    "WAVES": "Сплошная волнистая",
    "ZIGZAG": "Сплошная с изломами",
}

STYLE_TO_DXF_LINETYPE = {
    "Сплошная основная": "CONTINUOUS",
    "Сплошная тонкая": "CONTINUOUS",
    "Сплошная волнистая": "CONTINUOUS",
    "Сплошная с изломами": "ZIGZAG",
    "Штриховая": "HIDDEN",
    "Штрихпунктирная тонкая": "CENTER",
    "Штрихпунктирная утолщенная": "CENTER",
    "Штрихпунктирная с двумя точками": "PHANTOM",
    "Разомкнутая": "CONTINUOUS",
}


def map_linetype_to_style(linetype_name: str | None, fallback_style: str = "Сплошная основная") -> str:
    """Сопоставляет DXF linetype внутреннему стилю."""
    if not linetype_name:
        return fallback_style
    normalized = _normalize_linetype_name(linetype_name)
    return DXF_LINETYPE_TO_STYLE.get(normalized, fallback_style)


def map_style_to_linetype(style_name: str | None) -> str:
    """Сопоставляет внутренний стиль DXF linetype."""
    if not style_name:
        return "CONTINUOUS"
    return STYLE_TO_DXF_LINETYPE.get(style_name, "CONTINUOUS")


def display_style_for_layer(layer: LayerRecord | None) -> str:
    """Возвращает style_name для отображения объектов слоя."""
    if layer and layer.display_style_name:
        return layer.display_style_name
    if layer:
        return map_linetype_to_style(layer.linetype_name)
    return "Сплошная основная"


def effective_linetype_name(entity_linetype: str | None, layer: LayerRecord | None) -> str:
    """Возвращает эффективный linetype с учетом BYLAYER/BYBLOCK."""
    name = _normalize_linetype_name(entity_linetype or "BYLAYER")
    if name == "BYLAYER":
        return layer.linetype_name if layer else "CONTINUOUS"
    if name == "BYBLOCK":
        return layer.linetype_name if layer else "CONTINUOUS"
    return entity_linetype or "CONTINUOUS"


def rgb_int_to_hex(rgb_value: int | None) -> str | None:
    """Преобразует DXF TrueColor integer в HEX."""
    if rgb_value is None:
        return None
    try:
        from ezdxf import colors

        rgb = colors.int2rgb(int(rgb_value))
        return "#{:02X}{:02X}{:02X}".format(rgb.r, rgb.g, rgb.b)
    except Exception:
        return None


def aci_to_hex(aci_value: int | None) -> str | None:
    """Преобразует ACI цвет в HEX."""
    if aci_value is None:
        return None
    try:
        aci = int(aci_value)
    except (TypeError, ValueError):
        return None

    if aci <= 0 or aci in {256, 257}:
        return None

    try:
        from ezdxf import colors

        rgb = colors.aci2rgb(aci)
        return "#{:02X}{:02X}{:02X}".format(rgb.r, rgb.g, rgb.b)
    except Exception:
        fallback = {
            1: "#FF0000",
            2: "#FFFF00",
            3: "#00FF00",
            4: "#00FFFF",
            5: "#0000FF",
            6: "#FF00FF",
            7: "#FFFFFF",
        }
        return fallback.get(aci, None)


def hex_to_true_color_int(color_hex: str | None) -> int | None:
    """Преобразует HEX цвет в DXF TrueColor integer."""
    if not color_hex:
        return None
    value = color_hex.lstrip("#")
    if len(value) != 6:
        return None
    try:
        rgb = tuple(int(value[i:i + 2], 16) for i in range(0, 6, 2))
        from ezdxf import colors

        return colors.rgb2int(rgb)
    except Exception:
        return None


def resolve_object_color_hex(obj, layer: LayerRecord | None, fallback_hex: str) -> str:
    """Определяет цвет отображения объекта."""
    return (
        rgb_int_to_hex(getattr(obj, "true_color", None))
        or aci_to_hex(getattr(obj, "aci_color", None))
        or rgb_int_to_hex(layer.true_color if layer else None)
        or aci_to_hex(layer.aci_color if layer else None)
        or fallback_hex
    )


def entity_metadata_to_dict(entity) -> dict:
    """Извлекает DXF-метаданные сущности в dict."""
    return {
        "layer_name": getattr(entity.dxf, "layer", DEFAULT_LAYER_NAME) or DEFAULT_LAYER_NAME,
        "aci_color": _normalize_aci(getattr(entity.dxf, "color", None)),
        "true_color": getattr(entity.dxf, "true_color", None),
        "linetype_name": getattr(entity.dxf, "linetype", "BYLAYER") or "BYLAYER",
        "lineweight": getattr(entity.dxf, "lineweight", None),
        "source_handle": getattr(entity.dxf, "handle", None),
        "source_entity_type": entity.dxftype(),
        "import_flags": [],
    }


def apply_common_entity_attributes(dxf_entity, obj, layer: LayerRecord | None):
    """Применяет базовые DXF атрибуты объекта к сущности DXF."""
    dxf_entity.dxf.layer = getattr(obj, "layer_name", DEFAULT_LAYER_NAME) or DEFAULT_LAYER_NAME
    linetype_name = getattr(obj, "linetype_name", None)
    if linetype_name and linetype_name not in {"BYLAYER", MIXED_VALUE}:
        dxf_entity.dxf.linetype = linetype_name
    elif getattr(obj, "style_name", None):
        dxf_entity.dxf.linetype = map_style_to_linetype(obj.style_name)

    if getattr(obj, "true_color", None) is not None:
        dxf_entity.dxf.true_color = int(obj.true_color)
    elif getattr(obj, "aci_color", None) is not None:
        dxf_entity.dxf.color = int(obj.aci_color)
    elif layer and layer.true_color is not None:
        dxf_entity.dxf.true_color = int(layer.true_color)
    elif layer and layer.aci_color is not None:
        dxf_entity.dxf.color = int(layer.aci_color)

    if getattr(obj, "lineweight", None) is not None:
        dxf_entity.dxf.lineweight = int(obj.lineweight)
    elif layer and layer.lineweight is not None:
        dxf_entity.dxf.lineweight = int(layer.lineweight)


def _normalize_aci(value) -> int | None:
    """Нормализует ACI-код, отбрасывая BYLAYER/BYBLOCK."""
    try:
        color = int(value)
    except (TypeError, ValueError):
        return None
    return None if color in {0, 256, 257} else color


def _normalize_linetype_name(name: str | None) -> str:
    """Нормализует имя типа линии, сохраняя совместимость с DXF-суффиксами."""
    if not name:
        return "CONTINUOUS"

    normalized = str(name).strip().upper()
    if normalized in DXF_LINETYPE_TO_STYLE:
        return normalized

    base = normalized.split("_", 1)[0]
    if base in DXF_LINETYPE_TO_STYLE:
        return base

    for prefix in ("CENTER", "HIDDEN", "PHANTOM", "DASHED", "BATTING", "WAVES", "ZIGZAG"):
        if normalized.startswith(prefix):
            return prefix

    return normalized
