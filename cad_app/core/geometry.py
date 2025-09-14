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
    def __init__(self, start_point: Point, end_point: Point):
        self.start = start_point
        self.end = end_point

    def to_dict(self):
        return {
            "type": "line",
            "start": self.start.to_dict(),
            "end": self.end.to_dict()
        }

    @staticmethod
    def from_dict(data):
        start = Point.from_dict(data["start"])
        end = Point.from_dict(data["end"])
        return Line(start, end)