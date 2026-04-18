"""
Сопоставления DXF-атрибутов и внутренней модели приложения.
"""

from __future__ import annotations

import math
from typing import Iterable

from ..core.layers import LayerRecord

DEFAULT_DXF_VERSION = "R2010"
DEFAULT_LAYER_NAME = "0"
MIXED_VALUE = "__MIXED__"

ACI_PALETTE = {
    1: ("Красный", "#FF0000"),
    2: ("Жёлтый", "#FFFF00"),
    3: ("Зелёный", "#00FF00"),
    4: ("Голубой", "#00FFFF"),
    5: ("Синий", "#0000FF"),
    6: ("Пурпурный", "#FF00FF"),
    7: ("Белый/Чёрный", "#FFFFFF"),
}

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

    if aci in ACI_PALETTE:
        return ACI_PALETTE[aci][1]

    try:
        from ezdxf import colors

        rgb = colors.aci2rgb(aci)
        return "#{:02X}{:02X}{:02X}".format(rgb.r, rgb.g, rgb.b)
    except Exception:
        return None


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
    aci_color = _normalize_aci(getattr(entity.dxf, "color", None))
    true_color = getattr(entity.dxf, "true_color", None)
    normalized_aci, normalized_true_color = normalize_imported_dxf_color(aci_color, true_color)
    return {
        "layer_name": getattr(entity.dxf, "layer", DEFAULT_LAYER_NAME) or DEFAULT_LAYER_NAME,
        "aci_color": normalized_aci,
        "true_color": normalized_true_color,
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

    object_aci = normalize_object_aci(getattr(obj, "aci_color", None))
    object_true_color = getattr(obj, "true_color", None)

    if object_true_color is not None and object_aci is None:
        dxf_entity.dxf.true_color = int(obj.true_color)
    elif object_aci is not None:
        dxf_entity.dxf.color = int(object_aci)
        if hasattr(dxf_entity.dxf, "true_color"):
            try:
                del dxf_entity.dxf.true_color
            except Exception:
                pass
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


def normalize_object_aci(value: int | None) -> int | None:
    """Оставляет только 7 поддерживаемых ACI-цветов объекта."""
    try:
        aci = int(value)
    except (TypeError, ValueError):
        return None
    return aci if aci in ACI_PALETTE else None


def nearest_supported_aci_from_rgb(rgb: tuple[int, int, int] | None) -> int | None:
    """Возвращает ближайший ACI из 7 стандартных цветов по RGB-дистанции."""
    if not rgb or len(rgb) != 3:
        return None

    best_aci = None
    best_distance = None
    for aci, (_, hex_color) in ACI_PALETTE.items():
        palette_rgb = hex_to_rgb(hex_color)
        distance = math.sqrt(sum((channel - target) ** 2 for channel, target in zip(palette_rgb, rgb)))
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_aci = aci
    return best_aci


def normalize_imported_dxf_color(aci_color: int | None, true_color: int | None) -> tuple[int | None, int | None]:
    """Нормализует импортированный DXF-цвет к 7 поддерживаемым ACI-цветам."""
    if true_color is not None:
        rgb_hex = rgb_int_to_hex(true_color)
        normalized = nearest_supported_aci_from_rgb(hex_to_rgb(rgb_hex) if rgb_hex else None)
        return normalized, None

    normalized_aci = normalize_object_aci(aci_color)
    if normalized_aci is not None:
        return normalized_aci, None

    if aci_color is not None:
        rgb_hex = aci_to_hex(aci_color)
        normalized = nearest_supported_aci_from_rgb(hex_to_rgb(rgb_hex) if rgb_hex else None)
        return normalized, None

    return None, None


def hex_to_rgb(color_hex: str | None) -> tuple[int, int, int] | None:
    """Преобразует HEX в RGB tuple."""
    if not color_hex:
        return None
    value = color_hex.lstrip("#")
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[index:index + 2], 16) for index in range(0, 6, 2))
    except ValueError:
        return None


def aci_color_choices() -> list[tuple[str, int | None]]:
    """Возвращает список вариантов цвета для UI."""
    return [("По умолчанию", None)] + [(label, aci) for aci, (label, _) in ACI_PALETTE.items()]


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
