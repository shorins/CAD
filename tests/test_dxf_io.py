"""
Сценарные тесты DXF import/export.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ezdxf

from cad_app.core.geometry import Arc, Circle, Ellipse, Line, Point, PointEntity, Polygon, Rectangle, Spline
from cad_app.core.layers import LayerRecord
from cad_app.core.scene import Scene
from cad_app.dxf import export_dxf_file, import_dxf_file


def test_dxf_export_import_roundtrip_basic():
    scene = Scene()
    scene.ensure_layer("DXF")
    scene.set_current_layer("DXF")

    scene.add_object(PointEntity(Point(2, 3)))
    scene.add_object(Line(Point(0, 0), Point(10, 0)))
    scene.add_object(Circle(Point(5, 5), 2))
    scene.add_object(Arc(Point(0, 0), 3, 0, 90))
    scene.add_object(Ellipse(Point(0, 0), 4, 2))
    scene.add_object(Spline([Point(0, 0), Point(1, 2), Point(2, 0)]))

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "basic_roundtrip.dxf"
        export_report = export_dxf_file(scene, path)
        result = import_dxf_file(path)

    imported_types = {type(obj).__name__ for obj in result["objects"]}
    assert export_report["written_entities"] == 6
    assert result["report"]["skipped_count"] == 0
    assert {"PointEntity", "Line", "Circle", "Arc", "Ellipse", "Spline"} <= imported_types
    print("✓ test_dxf_export_import_roundtrip_basic passed")


def test_dxf_export_import_roundtrip_native_shapes():
    scene = Scene()
    scene.ensure_layer("DXF")
    scene.set_current_layer("DXF")

    rectangle = Rectangle(Point(0, 0), Point(10, 5))
    polygon = Polygon(Point(20, 10), 6, num_sides=7, rotation=15)
    wave = Line(Point(0, 10), Point(12, 10), style_name="Сплошная волнистая")
    zigzag = Line(Point(0, 14), Point(12, 14), style_name="Сплошная с изломами")
    scene.add_object(rectangle)
    scene.add_object(polygon)
    scene.add_object(wave)
    scene.add_object(zigzag)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "native_shapes_roundtrip.dxf"
        export_dxf_file(scene, path)
        result = import_dxf_file(path)
        doc = ezdxf.readfile(path)
        entity_types = [entity.dxftype() for entity in doc.modelspace()]

    imported_rectangles = [obj for obj in result["objects"] if isinstance(obj, Rectangle)]
    imported_polygons = [obj for obj in result["objects"] if isinstance(obj, Polygon)]
    imported_wave_splines = [obj for obj in result["objects"] if isinstance(obj, Spline)]
    imported_zigzags = [obj for obj in result["objects"] if isinstance(obj, Line) and obj.style_name == "Сплошная с изломами"]

    assert imported_rectangles, "Ожидался импорт Rectangle после roundtrip"
    assert imported_polygons, "Ожидался импорт Polygon после roundtrip"
    assert "SPLINE" in entity_types, "Волнистая линия должна экспортироваться как DXF SPLINE"
    assert imported_wave_splines, "Волнистая линия должна импортироваться обратно как Spline"
    assert imported_zigzags, "Ожидалась изломанная LINE через ZIGZAG mapping"
    assert imported_rectangles[0].promotion_kind == "exact_promotion"
    assert imported_polygons[0].promotion_kind == "exact_promotion"
    print("✓ test_dxf_export_import_roundtrip_native_shapes passed")


def test_dxf_import_layers_and_overrides():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "layers_overrides.dxf"
        doc = ezdxf.new("R2010", setup=True)
        layer = doc.layers.new("A", dxfattribs={"color": 3, "linetype": "DASHED"})
        layer.rgb = (10, 20, 30)

        msp = doc.modelspace()
        line = msp.add_line((0, 0), (5, 0), dxfattribs={"layer": "A"})
        circle = msp.add_circle((0, 0), 2, dxfattribs={"layer": "A", "linetype": "CENTER"})
        circle.rgb = (200, 100, 50)
        doc.saveas(path)

        result = import_dxf_file(path)

    imported_line = next(obj for obj in result["objects"] if isinstance(obj, Line))
    imported_circle = next(obj for obj in result["objects"] if isinstance(obj, Circle))

    assert imported_line.layer_name == "A"
    assert imported_line.style_name == "Штриховая"
    assert imported_line.aci_color is None
    assert imported_circle.true_color is not None
    assert imported_circle.linetype_name == "CENTER"
    print("✓ test_dxf_import_layers_and_overrides passed")


def test_dxf_import_blocks_and_unsupported_entities():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "blocks_and_unsupported.dxf"
        doc = ezdxf.new("R2010", setup=True)
        block = doc.blocks.new(name="TEST_BLOCK")
        block.add_line((0, 0), (2, 0))
        msp = doc.modelspace()
        msp.add_blockref("TEST_BLOCK", (10, 10))
        msp.add_text("unsupported")
        doc.saveas(path)

        result = import_dxf_file(path)

    imported_lines = [obj for obj in result["objects"] if isinstance(obj, Line)]
    assert imported_lines, "Ожидался импорт линии из INSERT"
    assert result["report"]["skipped_count"] >= 1
    assert result["report"]["skipped_summary"]
    print("✓ test_dxf_import_blocks_and_unsupported_entities passed")


def test_dxf_binary_import():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "binary_test.dxf"
        doc = ezdxf.new("R2010", setup=True)
        doc.modelspace().add_line((0, 0), (1, 1))
        doc.saveas(path, fmt="bin")

        result = import_dxf_file(path)

    assert result["report"]["binary"] is True
    assert result["report"]["imported_count"] == 1
    print("✓ test_dxf_binary_import passed")


def test_json_preserves_dxf_metadata():
    scene = Scene()
    scene.set_current_layer("LayerA")
    scene.ensure_layer("LayerA", LayerRecord(name="LayerA", aci_color=5, linetype_name="CENTER"))

    obj = Line(Point(0, 0), Point(1, 1))
    obj.layer_name = "LayerA"
    obj.aci_color = 1
    obj.true_color = 0x112233
    obj.linetype_name = "CENTER"
    obj.lineweight = 25
    obj.imported_from_dxf = True
    obj.source_handle = "ABCD"
    obj.source_entity_type = "LINE"
    obj.source_linetype_name = "CENTER"
    obj.promotion_kind = "direct"
    obj.import_flags = ["imported"]
    scene.add_object(obj)

    payload = {
        "scene": {
            "layers": [layer.to_dict() for layer in scene.layers.values()],
            "current_layer_name": scene.current_layer_name,
            "document_meta": scene.document_meta,
        },
        "objects": [obj.to_dict() for obj in scene.objects],
    }

    restored_layer = LayerRecord.from_dict(payload["scene"]["layers"][1])
    restored_obj = Line.from_dict(payload["objects"][0])

    assert restored_layer.name == "LayerA"
    assert restored_obj.layer_name == "LayerA"
    assert restored_obj.true_color == 0x112233
    assert restored_obj.imported_from_dxf is True
    assert restored_obj.source_handle == "ABCD"
    assert restored_obj.source_linetype_name == "CENTER"
    assert restored_obj.promotion_kind == "direct"
    assert restored_obj.import_flags == ["imported"]
    print("✓ test_json_preserves_dxf_metadata passed")


def test_dxf_import_real_fixture_promotions():
    fixture_path = Path(__file__).resolve().parent.parent / "todo" / "импорт17.dxf"
    assert fixture_path.exists(), "Ожидался fixture todo/импорт17.dxf"

    result = import_dxf_file(fixture_path)

    rectangles = [obj for obj in result["objects"] if isinstance(obj, Rectangle)]
    polygons = [obj for obj in result["objects"] if isinstance(obj, Polygon)]
    zigzags = [obj for obj in result["objects"] if isinstance(obj, Line) and obj.style_name == "Сплошная с изломами"]
    splines = [obj for obj in result["objects"] if isinstance(obj, Spline)]

    assert rectangles, "Прямоугольник из fixture должен распознаваться"
    assert polygons, "Многоугольник из fixture должен распознаваться"
    assert zigzags, "LINE с linetype=ZIGZAG должен импортироваться как изломанная"
    assert result["report"]["promoted_count"] >= 2

    if splines:
        assert all(spline.promotion_kind in {"heuristic_promotion", "direct"} for spline in splines)

    print("✓ test_dxf_import_real_fixture_promotions passed")


def test_dxf_export_autocad_linetype_names():
    scene = Scene()
    scene.add_object(Line(Point(0, 0), Point(10, 0), style_name="Сплошная основная"))
    scene.add_object(Line(Point(0, 1), Point(10, 1), style_name="Штриховая"))
    scene.add_object(Line(Point(0, 2), Point(10, 2), style_name="Штрихпунктирная тонкая"))
    scene.add_object(Line(Point(0, 3), Point(10, 3), style_name="Штрихпунктирная с двумя точками"))
    scene.add_object(Line(Point(0, 4), Point(10, 4), style_name="Сплошная волнистая"))
    scene.add_object(Line(Point(0, 5), Point(10, 5), style_name="Сплошная с изломами"))

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "linetype_names.dxf"
        export_report = export_dxf_file(scene, path)
        doc = ezdxf.readfile(path)
        entities = list(doc.modelspace())
        names = [entity.dxf.linetype for entity in entities]
        types = [entity.dxftype() for entity in entities]

    assert types == ["LINE", "LINE", "LINE", "LINE", "SPLINE", "LINE"]
    assert names == ["CONTINUOUS", "HIDDEN", "CENTER", "PHANTOM", "CONTINUOUS", "ZIGZAG"]
    assert "ZIGZAG" in export_report["created_linetypes"]
    print("✓ test_dxf_export_autocad_linetype_names passed")


if __name__ == "__main__":
    test_dxf_export_import_roundtrip_basic()
    test_dxf_export_import_roundtrip_native_shapes()
    test_dxf_import_layers_and_overrides()
    test_dxf_import_blocks_and_unsupported_entities()
    test_dxf_binary_import()
    test_json_preserves_dxf_metadata()
    test_dxf_import_real_fixture_promotions()
    test_dxf_export_autocad_linetype_names()
    print("\n✅ Все DXF тесты пройдены успешно!")
