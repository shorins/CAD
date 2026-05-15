"""
Тесты размерных объектов.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cad_app.core.geometry import (
    AngularDimension,
    Arc,
    Circle,
    DiameterDimension,
    DimensionAnchor,
    Line,
    LinearDimension,
    Point,
    RadialDimension,
    Rectangle,
)
from cad_app.core.scene import Scene
from cad_app.dxf import export_dxf_file


def test_linear_dimension_recomputes_from_line():
    scene = Scene()
    line = Line(Point(0, 0), Point(10, 0))
    scene.add_object(line)

    dim = LinearDimension(
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="start", cached_point=line.start.copy()),
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="end", cached_point=line.end.copy()),
        mode="aligned",
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(0, 5))
    scene.add_object(dim)
    assert abs(dim.measured_value_cache - 10.0) < 1e-6

    line.end = Point(15, 0)
    scene.recompute_dimensions()
    assert abs(dim.measured_value_cache - 15.0) < 1e-6
    print("✓ test_linear_dimension_recomputes_from_line passed")


def test_radial_dimension_recomputes_from_circle():
    scene = Scene()
    circle = Circle(Point(5, 5), 8)
    scene.add_object(circle)

    dim = DiameterDimension(
        DimensionAnchor(mode="object_snap", object_id=circle.object_id, selector="center", cached_point=circle.center.copy()),
        DimensionAnchor(mode="object_snap", object_id=circle.object_id, selector="radius_point", cached_point=Point(circle.center.x + circle.radius, circle.center.y)),
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(20, 5))
    scene.add_object(dim)
    assert abs(dim.measured_value_cache - 16.0) < 1e-6

    circle.radius = 10
    scene.recompute_dimensions()
    assert abs(dim.measured_value_cache - 20.0) < 1e-6
    print("✓ test_radial_dimension_recomputes_from_circle passed")


def test_angular_dimension_manual_points():
    scene = Scene()
    vertex = DimensionAnchor(mode="fixed", cached_point=Point(0, 0))
    ray1 = DimensionAnchor(mode="fixed", cached_point=Point(10, 0))
    ray2 = DimensionAnchor(mode="fixed", cached_point=Point(0, 10))
    dim = AngularDimension(vertex, ray1, ray2)
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(4, 4))
    scene.add_object(dim)

    assert abs(dim.measured_value_cache - 90.0) < 1e-6
    assert dim.display_text.endswith("°")
    print("✓ test_angular_dimension_manual_points passed")


def test_angular_dimension_can_measure_reflex_angle_by_placement():
    scene = Scene()
    vertex = DimensionAnchor(mode="fixed", cached_point=Point(0, 0))
    ray1 = DimensionAnchor(mode="fixed", cached_point=Point(10, 0))
    ray2 = DimensionAnchor(mode="fixed", cached_point=Point(0, 10))
    dim = AngularDimension(vertex, ray1, ray2)
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(8, -8))
    scene.add_object(dim)

    assert abs(dim.measured_value_cache - 270.0) < 1e-6
    print("✓ test_angular_dimension_can_measure_reflex_angle_by_placement passed")


def test_dimension_orphaned_after_base_object_removed():
    scene = Scene()
    line = Line(Point(0, 0), Point(10, 0))
    scene.add_object(line)
    dim = LinearDimension(
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="start", cached_point=line.start.copy()),
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="end", cached_point=line.end.copy()),
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(0, 3))
    scene.add_object(dim)

    scene.remove_object(line)
    assert dim.is_orphaned is True
    print("✓ test_dimension_orphaned_after_base_object_removed passed")


def test_dimension_json_roundtrip_keeps_ids_and_anchors():
    scene = Scene()
    line = Line(Point(0, 0), Point(10, 0))
    scene.add_object(line)
    dim = LinearDimension(
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="start", cached_point=line.start.copy()),
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="end", cached_point=line.end.copy()),
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(0, 4))
    dim.text_position_override = Point(5, 6)
    scene.add_object(dim)

    line_payload = line.to_dict()
    dim_payload = dim.to_dict()

    restored_line = Line.from_dict(line_payload)
    restored_dim = LinearDimension.from_dict(dim_payload)
    restored_scene = Scene()
    restored_scene.add_object(restored_line)
    restored_scene.add_object(restored_dim)

    assert restored_line.object_id == line.object_id
    assert restored_dim.anchor1.object_id == restored_line.object_id
    assert restored_dim.text_position_override == Point(5, 6)
    print("✓ test_dimension_json_roundtrip_keeps_ids_and_anchors passed")


def test_linear_dimension_resolves_rectangle_vertex_anchors():
    scene = Scene()
    rect = Rectangle(Point(0, 0), Point(20, 10))
    scene.add_object(rect)

    dim = LinearDimension(
        DimensionAnchor(mode="object_snap", object_id=rect.object_id, selector="vertex:0", cached_point=Point(0, 0)),
        DimensionAnchor(mode="object_snap", object_id=rect.object_id, selector="vertex:1", cached_point=Point(20, 0)),
        mode="horizontal",
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(0, 15))
    scene.add_object(dim)

    assert abs(dim.measured_value_cache - 20.0) < 1e-6
    assert dim.get_render_data()["segments"]
    print("✓ test_linear_dimension_resolves_rectangle_vertex_anchors passed")


def test_diameter_dimension_supports_arc_with_single_arrow():
    scene = Scene()
    arc = Arc(Point(0, 0), 10, 0, 180)
    scene.add_object(arc)

    dim = DiameterDimension(
        DimensionAnchor(mode="object_snap", object_id=arc.object_id, selector="center", cached_point=arc.center.copy()),
        DimensionAnchor(mode="object_snap", object_id=arc.object_id, selector="arc_mid", cached_point=arc.mid_point.copy()),
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(0, 18))
    scene.add_object(dim)

    data = dim.get_render_data()
    assert abs(dim.measured_value_cache - 20.0) < 1e-6
    assert len(data["arrows"]) == 1
    assert data["text"].startswith("Ø")
    print("✓ test_diameter_dimension_supports_arc_with_single_arrow passed")


def test_manual_text_override_uses_horizontal_text_and_landing():
    scene = Scene()
    line = Line(Point(0, 0), Point(20, 0))
    scene.add_object(line)

    dim = LinearDimension(
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="start", cached_point=line.start.copy()),
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="end", cached_point=line.end.copy()),
        mode="aligned",
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(0, 6))
    dim.text_position_override = Point(30, 12)
    scene.add_object(dim)

    data = dim.get_render_data()
    assert data["text_angle"] == 0.0
    landing = data["landing_points"]
    assert len(landing) == 2
    assert abs(landing[0].y - landing[1].y) < 1e-6
    assert data["has_leader"] is True
    print("✓ test_manual_text_override_uses_horizontal_text_and_landing passed")


def test_flip_arrows_changes_radial_arrow_direction():
    scene = Scene()
    circle = Circle(Point(0, 0), 10)
    scene.add_object(circle)

    dim = RadialDimension(
        DimensionAnchor(mode="object_snap", object_id=circle.object_id, selector="center", cached_point=circle.center.copy()),
        DimensionAnchor(mode="object_snap", object_id=circle.object_id, selector="radius_point", cached_point=Point(circle.center.x + circle.radius, circle.center.y)),
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(20, 0))
    scene.add_object(dim)
    tail_before = dim.get_render_data()["arrows"][0]["tail"]

    dim.flip_arrows()
    scene.recompute_dimensions()
    tail_after = dim.get_render_data()["arrows"][0]["tail"]

    assert tail_before.x != tail_after.x or tail_before.y != tail_after.y
    print("✓ test_flip_arrows_changes_radial_arrow_direction passed")


def test_flip_arrows_changes_diameter_arrow_direction_when_outside():
    scene = Scene()
    circle = Circle(Point(0, 0), 10)
    scene.add_object(circle)

    dim = DiameterDimension(
        DimensionAnchor(mode="object_snap", object_id=circle.object_id, selector="center", cached_point=circle.center.copy()),
        DimensionAnchor(mode="object_snap", object_id=circle.object_id, selector="radius_point", cached_point=Point(circle.center.x + circle.radius, circle.center.y)),
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(25, 0))
    scene.add_object(dim)
    tails_before = [(arrow["tail"].x, arrow["tail"].y) for arrow in dim.get_render_data()["arrows"]]

    dim.flip_arrows()
    scene.recompute_dimensions()
    tails_after = [(arrow["tail"].x, arrow["tail"].y) for arrow in dim.get_render_data()["arrows"]]

    assert tails_before != tails_after
    assert dim.get_render_data()["arrows_are_outside"] is False
    print("✓ test_flip_arrows_changes_diameter_arrow_direction_when_outside passed")


def test_dxf_export_warns_and_skips_dimensions():
    scene = Scene()
    line = Line(Point(0, 0), Point(10, 0))
    scene.add_object(line)
    dim = LinearDimension(
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="start", cached_point=line.start.copy()),
        DimensionAnchor(mode="object_snap", object_id=line.object_id, selector="end", cached_point=line.end.copy()),
    )
    dim.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=Point(0, 3))
    scene.add_object(dim)

    with tempfile.TemporaryDirectory() as tmp:
        report = export_dxf_file(scene, Path(tmp) / "dim_skip.dxf")

    assert report["written_entities"] == 1
    assert any("DXF DIMENSION" in warning for warning in report["warnings"])
    print("✓ test_dxf_export_warns_and_skips_dimensions passed")


if __name__ == "__main__":
    test_linear_dimension_recomputes_from_line()
    test_radial_dimension_recomputes_from_circle()
    test_angular_dimension_manual_points()
    test_angular_dimension_can_measure_reflex_angle_by_placement()
    test_dimension_orphaned_after_base_object_removed()
    test_dimension_json_roundtrip_keeps_ids_and_anchors()
    test_linear_dimension_resolves_rectangle_vertex_anchors()
    test_diameter_dimension_supports_arc_with_single_arrow()
    test_manual_text_override_uses_horizontal_text_and_landing()
    test_flip_arrows_changes_radial_arrow_direction()
    test_flip_arrows_changes_diameter_arrow_direction_when_outside()
    test_dxf_export_warns_and_skips_dimensions()
    print("\n✅ Все dimension-тесты пройдены успешно!")
