class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def to_dict(self):
        return {"x": self.x, "y": self.y}

    @staticmethod
    def from_dict(data):
        return Point(data["x"], data["y"])


class Line:
    def __init__(self, start_point: Point, end_point: Point, style_name: str = "Сплошная основная"):
        self.start = start_point
        self.end = end_point
        self.style_name = style_name

    def to_dict(self):
        return {
            "type": "line",
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "style": self.style_name
        }

    @staticmethod
    def from_dict(data):
        start = Point.from_dict(data["start"])
        end = Point.from_dict(data["end"])
        style_name = data.get("style", "Сплошная основная") # по умолчанию сплошная основная для совместимости с старыми проектами
        return Line(start, end, style_name)