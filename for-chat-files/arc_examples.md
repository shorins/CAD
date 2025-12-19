# Примеры использования: Arc3Points для вашего CAD

## Быстрый старт

### Установка зависимостей
```bash
# Только встроенные модули!
# math, dataclasses, concurrent.futures - все в стандартной библиотеке
```

### Базовый пример

```python
from arc_implementation import Point, Arc3Points

# Определяем три точки
start = Point(0, 5)
middle = Point(5, 5)
end = Point(5, 0)

# Вычисляем дугу
arc = Arc3Points.calculate(start, middle, end)

print(f"Центр окружности: ({arc.center.x:.2f}, {arc.center.y:.2f})")
print(f"Радиус: {arc.radius:.2f}")
print(f"Длина дуги: {arc.length():.2f}")

# Получаем точки для отрисовки
points = Arc3Points.generate_arc_points(arc, num_segments=50)
for i, p in enumerate(points[:5]):
    print(f"Точка {i}: ({p.x:.2f}, {p.y:.2f})")
```

---

## Примеры для различных CAD-операций

### Пример 1: Дуга в окружности

```python
# Построение дуги, проходящей через 3 точки на окружности
import math

# Три точки на окружности радиуса 10 с центром в (0, 0)
p1 = Point(10, 0)          # 0°
p2 = Point(0, 10)          # 90°
p3 = Point(-10, 0)         # 180°

arc = Arc3Points.calculate(p1, p2, p3)

# Проверка: должна быть полукруг
assert abs(arc.radius - 10) < 0.01
assert abs(arc.center.x) < 0.01
assert abs(arc.center.y) < 0.01

print(f"✓ Полукруг радиуса {arc.radius:.2f}")
```

### Пример 2: Интерактивное рисование (как в AutoCAD)

```python
class SimpleCADEditor:
    """Минималистичный CAD-редактор с поддержкой дуг"""
    
    def __init__(self):
        self.points = []
        self.arc_data = None
    
    def add_point(self, x, y):
        """Добавить точку при клике"""
        p = Point(x, y)
        self.points.append(p)
        
        # После 3 точек - рисуем дугу
        if len(self.points) == 3:
            try:
                self.arc_data = Arc3Points.calculate(
                    self.points[0],
                    self.points[1],
                    self.points[2]
                )
                print(f"Дуга построена: радиус={self.arc_data.radius:.2f}, "
                      f"центр=({self.arc_data.center.x:.2f}, {self.arc_data.center.y:.2f})")
            except ValueError as e:
                print(f"Ошибка: {e} - выберите другие точки")
            
            # Сброс для новой дуги
            self.points = []
    
    def get_preview_points(self, current_x, current_y):
        """Получить точки превью для текущей позиции мыши"""
        if len(self.points) == 0:
            return None
        elif len(self.points) == 1:
            return [self.points[0], Point(current_x, current_y)]
        elif len(self.points) == 2:
            try:
                arc = Arc3Points.calculate(
                    self.points[0],
                    self.points[1],
                    Point(current_x, current_y)
                )
                return Arc3Points.generate_arc_points(arc, num_segments=50)
            except ValueError:
                # Коллинеарные точки - показываем линию
                return [self.points[0], self.points[1], Point(current_x, current_y)]

# Использование:
editor = SimpleCADEditor()
editor.add_point(0, 0)
editor.add_point(5, 5)
editor.add_point(10, 0)

# Получить превью при движении мыши
preview = editor.get_preview_points(7, 3)
```

### Пример 3: Импорт/экспорт в различные форматы

```python
class ArcFormat:
    """Конвертирование дуги в различные форматы"""
    
    @staticmethod
    def to_svg_path(arc_data):
        """Экспорт в SVG format (для веб-отображения)"""
        # SVG arc command: A rx ry x-axis-rotation large-arc-flag sweep-flag x y
        
        path = f"M {arc_data.start_point.x} {arc_data.start_point.y} "
        path += f"A {arc_data.radius} {arc_data.radius} 0 "
        path += f"{int(arc_data.is_large_arc)} 1 "  # sweep=1 (по часовой)
        path += f"{arc_data.end_point.x} {arc_data.end_point.y}"
        
        return path
    
    @staticmethod
    def to_dxf(arc_data):
        """Экспорт в DXF format (для AutoCAD)"""
        # Упрощённый DXF arc
        dxf_code = f"""
0
ARC
8
0
10
{arc_data.center.x}
20
{arc_data.center.y}
40
{arc_data.radius}
50
{math.degrees(arc_data.start_angle)}
51
{math.degrees(arc_data.end_angle)}
"""
        return dxf_code.strip()
    
    @staticmethod
    def to_parametric(arc_data, num_segments=100):
        """Экспорт как параметрическая кривая"""
        points = Arc3Points.generate_arc_points(arc_data, num_segments)
        
        data = {
            'center': (arc_data.center.x, arc_data.center.y),
            'radius': arc_data.radius,
            'start_angle': math.degrees(arc_data.start_angle),
            'end_angle': math.degrees(arc_data.end_angle),
            'points': [(p.x, p.y) for p in points]
        }
        
        return data

# Использование:
import math

p1 = Point(1, 0)
p2 = Point(0, 1)
p3 = Point(-1, 0)
arc = Arc3Points.calculate(p1, p2, p3)

print("SVG:", ArcFormat.to_svg_path(arc))
print("DXF:", ArcFormat.to_dxf(arc))
print("Параметрический:", ArcFormat.to_parametric(arc))
```

### Пример 4: Работа с экраном/зумом

```python
class ViewportArcRenderer:
    """Отрисовка дуг с учётом масштабирования и видимости"""
    
    def __init__(self, screen_width=800, screen_height=600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.pan_x = 0
        self.pan_y = 0
        self.zoom = 1.0
    
    def world_to_screen(self, world_x, world_y):
        """Преобразование из мировых координат в экранные"""
        screen_x = (world_x + self.pan_x) * self.zoom
        screen_y = (world_y + self.pan_y) * self.zoom
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x, screen_y):
        """Преобразование из экранных координат в мировые"""
        world_x = (screen_x / self.zoom) - self.pan_x
        world_y = (screen_y / self.zoom) - self.pan_y
        return world_x, world_y
    
    def render_arc(self, arc_data):
        """Отрисовка дуги с адаптивной детализацией"""
        # Определяем видимую область
        view_x_min = -self.pan_x / self.zoom
        view_y_min = -self.pan_y / self.zoom
        view_x_max = view_x_min + self.screen_width / self.zoom
        view_y_max = view_y_min + self.screen_height / self.zoom
        
        # Проверка: находится ли дуга в видимой области
        arc_x_min = arc_data.center.x - arc_data.radius
        arc_y_min = arc_data.center.y - arc_data.radius
        arc_x_max = arc_data.center.x + arc_data.radius
        arc_y_max = arc_data.center.y + arc_data.radius
        
        if (arc_x_max < view_x_min or arc_x_min > view_x_max or
            arc_y_max < view_y_min or arc_y_min > view_y_max):
            return []  # Дуга вне экрана
        
        # Адаптивное число сегментов
        visible_radius = arc_data.radius * self.zoom
        num_segments = max(10, int(visible_radius / 5))
        
        # Генерируем точки дуги
        world_points = Arc3Points.generate_arc_points(arc_data, num_segments)
        
        # Преобразуем в экранные координаты
        screen_points = [
            self.world_to_screen(p.x, p.y)
            for p in world_points
        ]
        
        return screen_points
    
    def zoom_fit_arc(self, arc_data, padding=50):
        """Автоматический зум так, чтобы дуга заняла весь экран"""
        diameter = arc_data.radius * 2
        
        self.zoom = min(
            (self.screen_width - 2*padding) / diameter,
            (self.screen_height - 2*padding) / diameter
        )
        
        self.pan_x = -arc_data.center.x
        self.pan_y = -arc_data.center.y

# Использование:
renderer = ViewportArcRenderer(screen_width=1024, screen_height=768)

arc = Arc3Points.calculate(Point(0, 0), Point(100, 100), Point(200, 0))
renderer.zoom_fit_arc(arc)

screen_points = renderer.render_arc(arc)
print(f"Экранные координаты дуги: {screen_points[:5]}")
```

### Пример 5: Анализ геометрии дуги

```python
class ArcAnalyzer:
    """Анализ и проверка свойств дуги"""
    
    @staticmethod
    def get_bounding_box(arc_data):
        """Получить bounding box (прямоугольник) дуги"""
        points = Arc3Points.generate_arc_points(arc_data, num_segments=100)
        
        x_coords = [p.x for p in points]
        y_coords = [p.y for p in points]
        
        return {
            'x_min': min(x_coords),
            'x_max': max(x_coords),
            'y_min': min(y_coords),
            'y_max': max(y_coords),
            'width': max(x_coords) - min(x_coords),
            'height': max(y_coords) - min(y_coords)
        }
    
    @staticmethod
    def point_on_arc(arc_data, point, tolerance=0.01):
        """Проверить, находится ли точка на дуге"""
        # Расстояние до центра должно быть равно радиусу
        dist_to_center = arc_data.center.distance_to(point)
        
        if abs(dist_to_center - arc_data.radius) > tolerance:
            return False
        
        # Угол точки должен быть между start и end
        theta = math.atan2(point.y - arc_data.center.y, 
                          point.x - arc_data.center.x)
        theta = Arc3Points.normalize_angle(theta)
        
        angle_diff = arc_data.end_angle - arc_data.start_angle
        
        # Проверка нахождения в диапазоне углов
        in_range = (arc_data.start_angle <= theta <= arc_data.start_angle + angle_diff or
                   arc_data.start_angle <= theta + 2*math.pi <= arc_data.start_angle + angle_diff)
        
        return in_range
    
    @staticmethod
    def intersect_with_line(arc_data, line_start, line_end):
        """
        Найти точки пересечения дуги с прямой линией.
        Решение квадратного уравнения: (x-xc)² + (y-yc)² = r²
        """
        x1, y1 = line_start.x, line_start.y
        x2, y2 = line_end.x, line_end.y
        xc, yc = arc_data.center.x, arc_data.center.y
        r = arc_data.radius
        
        # Параметрическое уравнение линии: P(t) = (1-t)*P1 + t*P2
        dx = x2 - x1
        dy = y2 - y1
        
        # Подставляем в уравнение окружности
        a = dx*dx + dy*dy
        b = 2 * ((x1 - xc)*dx + (y1 - yc)*dy)
        c = (x1 - xc)**2 + (y1 - yc)**2 - r**2
        
        discriminant = b*b - 4*a*c
        
        if discriminant < 0:
            return []  # Нет пересечений
        
        intersections = []
        t1 = (-b + math.sqrt(discriminant)) / (2*a)
        t2 = (-b - math.sqrt(discriminant)) / (2*a)
        
        for t in [t1, t2]:
            if 0 <= t <= 1:  # Пересечение в пределах линии
                x = x1 + t * dx
                y = y1 + t * dy
                p = Point(x, y)
                
                # Проверить, на ли точка на дуге (не только на окружности)
                if ArcAnalyzer.point_on_arc(arc_data, p):
                    intersections.append(p)
        
        return intersections

# Использование:
import math

arc = Arc3Points.calculate(Point(0, 5), Point(5, 5), Point(5, 0))
bbox = ArcAnalyzer.get_bounding_box(arc)
print(f"Bounding box: {bbox}")

# Проверить точку на дуге
test_point = Point(0, 0)
on_arc = ArcAnalyzer.point_on_arc(arc, test_point)
print(f"Точка на дуге: {on_arc}")

# Найти пересечение с линией
line_start = Point(-1, 0)
line_end = Point(6, 0)
intersections = ArcAnalyzer.intersect_with_line(arc, line_start, line_end)
print(f"Пересечения: {intersections}")
```

### Пример 6: Реальное приложение - трассировка пути

```python
class PathTracer:
    """Трассировка пути из дуг и линий (как в CAD-системах)"""
    
    def __init__(self):
        self.segments = []  # Список объектов (Arc или Line)
    
    def add_arc(self, p1, p2, p3):
        """Добавить дугу к пути"""
        try:
            arc = Arc3Points.calculate(p1, p2, p3)
            self.segments.append(('arc', arc))
            return True
        except ValueError as e:
            print(f"Ошибка добавления дуги: {e}")
            return False
    
    def add_line(self, p1, p2):
        """Добавить линию к пути"""
        self.segments.append(('line', (p1, p2)))
    
    def get_path_length(self):
        """Получить общую длину пути"""
        total_length = 0
        for seg_type, seg_data in self.segments:
            if seg_type == 'arc':
                total_length += seg_data.length()
            else:
                p1, p2 = seg_data
                total_length += p1.distance_to(p2)
        return total_length
    
    def get_all_points(self, resolution=50):
        """Получить все точки пути для отрисовки"""
        all_points = []
        for seg_type, seg_data in self.segments:
            if seg_type == 'arc':
                points = Arc3Points.generate_arc_points(seg_data, resolution)
                all_points.extend(points)
            else:
                p1, p2 = seg_data
                all_points.extend([p1, p2])
        return all_points
    
    def sample_point_at_distance(self, distance):
        """Получить точку на пути на расстоянии distance от начала"""
        current_distance = 0
        
        for seg_type, seg_data in self.segments:
            if seg_type == 'arc':
                seg_length = seg_data.length()
            else:
                p1, p2 = seg_data
                seg_length = p1.distance_to(p2)
            
            if current_distance + seg_length >= distance:
                # Нужная точка в этом сегменте
                remaining = distance - current_distance
                progress = remaining / seg_length if seg_length > 0 else 0
                
                if seg_type == 'arc':
                    points = Arc3Points.generate_arc_points(seg_data, 100)
                    idx = min(int(progress * 100), len(points) - 1)
                    return points[idx]
                else:
                    p1, p2 = seg_data
                    x = p1.x + progress * (p2.x - p1.x)
                    y = p1.y + progress * (p2.y - p1.y)
                    return Point(x, y)
            
            current_distance += seg_length
        
        return None  # Расстояние больше длины пути

# Использование:
path = PathTracer()
path.add_arc(Point(0, 0), Point(5, 5), Point(10, 0))
path.add_line(Point(10, 0), Point(10, -5))
path.add_arc(Point(10, -5), Point(7, -8), Point(5, -5))

print(f"Длина пути: {path.get_path_length():.2f}")
point_at_halfway = path.sample_point_at_distance(path.get_path_length() / 2)
print(f"Середина пути: ({point_at_halfway.x:.2f}, {point_at_halfway.y:.2f})")
```

---

## Производительность: Бенчмарки

```python
import time

def benchmark():
    """Бенчмарк производительности"""
    
    print("=== Бенчмарк Arc3Points ===\n")
    
    # Генерация случайных точек
    import random
    random.seed(42)
    
    points = [
        [Point(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(3)]
        for _ in range(1000)
    ]
    
    # Тест 1: Расчёт центра и радиуса
    start = time.time()
    for p1, p2, p3 in points:
        Arc3Points.calculate_center_and_radius(p1, p2, p3)
    elapsed = time.time() - start
    
    print(f"Расчёт 1000 центров/радиусов: {elapsed:.4f} сек")
    print(f"  Средний расчёт: {elapsed/1000*1000:.2f} мс")
    
    # Тест 2: Полный расчёт дуги
    start = time.time()
    for p1, p2, p3 in points:
        Arc3Points.calculate(p1, p2, p3)
    elapsed = time.time() - start
    
    print(f"\nПолный расчёт 1000 дуг: {elapsed:.4f} сек")
    print(f"  Средний расчёт: {elapsed/1000*1000:.2f} мс")
    
    # Тест 3: Генерация точек
    arc = Arc3Points.calculate(Point(0, 0), Point(10, 10), Point(20, 0))
    
    start = time.time()
    for _ in range(1000):
        Arc3Points.generate_arc_points(arc, num_segments=100)
    elapsed = time.time() - start
    
    print(f"\nГенерация 1000 х 100-сегментных дуг: {elapsed:.4f} сек")
    print(f"  Средний расчёт: {elapsed/1000*1000:.2f} мс")
    
    # Тест 4: Отрисовка с адаптивной детализацией
    arcs = [Arc3Points.calculate(p1, p2, p3) for p1, p2, p3 in points[:100]]
    
    start = time.time()
    for arc in arcs:
        Arc3Points.generate_arc_points(arc, num_segments=200)
    elapsed = time.time() - start
    
    print(f"\nОтрисовка 100 дуг (200 сегментов): {elapsed:.4f} сек")
    print(f"  Средняя дуга: {elapsed/100*1000:.2f} мс")

if __name__ == "__main__":
    benchmark()
```

---

## Интеграция в существующий CAD

Для интеграции в ваш CAD достаточно:

```python
# 1. Импортировать основной класс
from arc_implementation import Arc3Points, Point, ArcData

# 2. В обработчике клика мыши:
def on_arc_command_start():
    editor = InteractiveArcEditor()
    # ... привязать обработчики событий

# 3. При отрисовке:
def render_scene():
    for arc in scene.arcs:
        points = Arc3Points.generate_arc_points(arc, num_segments=100)
        draw_polyline(points)  # ваша функция отрисовки
```

**Готово к использованию!** 🚀
