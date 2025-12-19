# arc_implementation.py
# Полная реализация отрисовки дуги по трём точкам для CAD

import math
from dataclasses import dataclass
from typing import Tuple, Optional, List
import concurrent.futures

# ============================================================================
# БАЗОВЫЕ СТРУКТУРЫ ДАННЫХ
# ============================================================================

@dataclass
class Point:
    """Точка в 2D пространстве"""
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        """Расстояние до другой точки"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __repr__(self):
        return f"Point({self.x:.4f}, {self.y:.4f})"


@dataclass
class ArcData:
    """Полные данные о дуге"""
    center: Point
    radius: float
    start_angle: float  # в радианах
    end_angle: float    # в радианах
    start_point: Point
    end_point: Point
    is_large_arc: bool  # флаг большой дуги для SVG
    
    def length(self) -> float:
        """Длина дуги"""
        angle_diff = self.end_angle - self.start_angle
        if angle_diff < 0:
            angle_diff += 2 * math.pi
        return self.radius * angle_diff
    
    def __repr__(self):
        return (f"ArcData(center={self.center}, radius={self.radius:.4f}, "
                f"start_angle={math.degrees(self.start_angle):.2f}°, "
                f"end_angle={math.degrees(self.end_angle):.2f}°)")


# ============================================================================
# ОСНОВНОЙ КЛАСС ДЛЯ РАСЧЁТА ДУГ
# ============================================================================

class Arc3Points:
    """Расчёт и отрисовка дуги по трём точкам"""
    
    EPSILON = 1e-10  # для проверки коллинеарности
    
    @staticmethod
    def calculate_center_and_radius(
        p1: Point, 
        p2: Point, 
        p3: Point
    ) -> Tuple[Point, float]:
        """
        Вычисление центра и радиуса окружности через три точки.
        Метод: определители (формула Крамера).
        
        Args:
            p1, p2, p3: Три точки на окружности
            
        Returns:
            (center_point, radius)
            
        Raises:
            ValueError: если точки коллинеарны
        """
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y
        
        # Вычисление определителя
        delta = 2 * (x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
        
        # Проверка коллинеарности
        if abs(delta) < Arc3Points.EPSILON:
            raise ValueError("Три точки коллинеарны! Невозможно построить окружность.")
        
        # Расчёт квадратов координат
        x1_sq_y1_sq = x1**2 + y1**2
        x2_sq_y2_sq = x2**2 + y2**2
        x3_sq_y3_sq = x3**2 + y3**2
        
        # Формулы для центра
        x_center = (x1_sq_y1_sq * (y2-y3) + 
                   x2_sq_y2_sq * (y3-y1) + 
                   x3_sq_y3_sq * (y1-y2)) / delta
        
        y_center = (x1_sq_y1_sq * (x3-x2) + 
                   x2_sq_y2_sq * (x1-x3) + 
                   x3_sq_y3_sq * (x2-x1)) / delta
        
        center = Point(x_center, y_center)
        
        # Расчёт радиуса
        radius = p1.distance_to(center)
        
        return center, radius
    
    @staticmethod
    def normalize_angle(angle: float) -> float:
        """Нормализация угла к диапазону [0, 2π)"""
        while angle < 0:
            angle += 2 * math.pi
        while angle >= 2 * math.pi:
            angle -= 2 * math.pi
        return angle
    
    @staticmethod
    def calculate_angles(
        center: Point,
        p1: Point,
        p2: Point,
        p3: Point
    ) -> Tuple[float, float]:
        """
        Вычисление углов начала и конца дуги относительно центра.
        
        Args:
            center: Центр окружности
            p1: Начальная точка
            p2: Промежуточная точка
            p3: Конечная точка
            
        Returns:
            (start_angle, end_angle) в радианах
        """
        # Вычисление углов каждой точки
        theta1 = math.atan2(p1.y - center.y, p1.x - center.x)
        theta2 = math.atan2(p2.y - center.y, p2.x - center.x)
        theta3 = math.atan2(p3.y - center.y, p3.x - center.x)
        
        # Нормализация к [0, 2π)
        theta1 = Arc3Points.normalize_angle(theta1)
        theta2 = Arc3Points.normalize_angle(theta2)
        theta3 = Arc3Points.normalize_angle(theta3)
        
        # Определение направления дуги
        eps = Arc3Points.EPSILON
        
        # Случай 1: θ1 < θ2 < θ3
        if (theta1 < theta2 + eps and theta2 < theta3 + eps):
            return theta1, theta3
        
        # Случай 2: θ1 < θ3 < θ2
        elif (theta1 < theta3 + eps and theta3 < theta2 + eps):
            return theta3, theta1 + 2*math.pi
        
        # Случай 3: θ2 < θ1 < θ3
        elif (theta2 < theta1 + eps and theta1 < theta3 + eps):
            return theta3, theta1 + 2*math.pi
        
        # Случай 4: θ2 < θ3 < θ1
        elif (theta2 < theta3 + eps and theta3 < theta1 + eps):
            return theta1, theta3 + 2*math.pi
        
        # Случай 5: θ3 < θ1 < θ2
        elif (theta3 < theta1 + eps and theta1 < theta2 + eps):
            return theta1, theta3 + 2*math.pi
        
        # Случай 6: θ3 < θ2 < θ1
        else:
            return theta3, theta1
    
    @classmethod
    def calculate(cls, p1: Point, p2: Point, p3: Point) -> ArcData:
        """
        Полный расчёт дуги по трём точкам.
        
        Args:
            p1: Начальная точка дуги
            p2: Точка, через которую должна пройти дуга
            p3: Конечная точка дуги
            
        Returns:
            ArcData с полной информацией о дуге
        """
        # Расчёт центра и радиуса
        center, radius = cls.calculate_center_and_radius(p1, p2, p3)
        
        # Расчёт углов
        start_angle, end_angle = cls.calculate_angles(center, p1, p2, p3)
        
        # Определение большой дуги (для SVG format)
        angle_diff = end_angle - start_angle
        is_large_arc = angle_diff > math.pi
        
        return ArcData(
            center=center,
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            start_point=p1,
            end_point=p3,
            is_large_arc=is_large_arc
        )
    
    @staticmethod
    def generate_arc_points(
        arc_data: ArcData,
        num_segments: int = 100
    ) -> List[Point]:
        """
        Генерация точек для отрисовки дуги.
        
        Args:
            arc_data: Данные о дуге
            num_segments: Количество линейных сегментов для аппроксимации
            
        Returns:
            Список точек, образующих полилинию дуги
        """
        points = []
        
        # Определение направления и размера углового шага
        angle_diff = arc_data.end_angle - arc_data.start_angle
        
        for i in range(num_segments + 1):
            t = i / num_segments  # параметр от 0 до 1
            angle = arc_data.start_angle + t * angle_diff
            
            # Параметрическое уравнение окружности
            x = arc_data.center.x + arc_data.radius * math.cos(angle)
            y = arc_data.center.y + arc_data.radius * math.sin(angle)
            
            points.append(Point(x, y))
        
        return points


# ============================================================================
# СИСТЕМА ПРЕВЬЮ
# ============================================================================

class ArcPreview:
    """Система превью для интерактивного отображения дуги при рисовании"""
    
    @staticmethod
    def create_preview_polyline(
        start_point: Point,
        middle_point: Point,
        end_point: Optional[Point] = None
    ) -> List[Point]:
        """
        Создание временного превью дуги во время рисования.
        
        Args:
            start_point: Первая указанная точка
            middle_point: Вторая указанная точка
            end_point: Третья указанная точка (опционально)
            
        Returns:
            Список точек для отрисовки превью
        """
        if end_point is None:
            # Показываем только линию от start к middle
            return [start_point, middle_point]
        
        try:
            # Попытка построить полную дугу
            arc_data = Arc3Points.calculate(start_point, middle_point, end_point)
            
            # Адаптивное количество сегментов
            num_segments = max(20, int(arc_data.radius / 10))
            
            points = Arc3Points.generate_arc_points(arc_data, num_segments)
            return points
            
        except ValueError:
            # Если точки коллинеарны, показываем прямую линию
            return [start_point, middle_point, end_point]


class InteractiveArcEditor:
    """
    Интерактивный редактор дуги с реальным превью.
    Симулирует поведение AutoCAD/SOLIDWORKS
    """
    
    def __init__(self):
        self.p1: Optional[Point] = None
        self.p2: Optional[Point] = None
        self.p3: Optional[Point] = None
        self.arc_data: Optional[ArcData] = None
        self.stage = 0  # 0: ждём P1, 1: ждём P2, 2: ждём P3
    
    def on_mouse_move(self, current_point: Point) -> Optional[List[Point]]:
        """
        Обработка движения мыши для обновления превью.
        
        Returns:
            Точки для отрисовки превью или None
        """
        if self.stage == 0:
            return [Point(0, 0), current_point]
        
        elif self.stage == 1:
            return [self.p1, current_point]
        
        elif self.stage == 2:
            try:
                arc_data = Arc3Points.calculate(self.p1, self.p2, current_point)
                self.arc_data = arc_data
                return Arc3Points.generate_arc_points(arc_data, num_segments=100)
            except ValueError:
                return [self.p1, self.p2, current_point]
        
        return None
    
    def on_click(self, point: Point):
        """Обработка клика мыши"""
        if self.stage == 0:
            self.p1 = point
            self.stage = 1
            print(f"Точка 1: {point}")
        
        elif self.stage == 1:
            self.p2 = point
            self.stage = 2
            print(f"Точка 2: {point}")
        
        elif self.stage == 2:
            self.p3 = point
            self.arc_data = Arc3Points.calculate(self.p1, self.p2, self.p3)
            print(f"Точка 3: {point}")
            print(f"Дуга завершена: {self.arc_data}")
            self.reset()
    
    def reset(self):
        """Сброс редактора для новой дуги"""
        self.stage = 0
        self.p1 = None
        self.p2 = None
        self.p3 = None


# ============================================================================
# ОПТИМИЗАЦИЯ И АДАПТИВНАЯ ОТРИСОВКА
# ============================================================================

class AdaptiveArcRenderer:
    """Адаптивная отрисовка в зависимости от уровня масштабирования"""
    
    @staticmethod
    def calculate_optimal_segments(
        arc_data: ArcData,
        screen_width: float,
        view_bounds: Tuple[float, float, float, float],
        min_pixel_distance: float = 2.0
    ) -> int:
        """
        Вычисление оптимального числа сегментов для отрисовки.
        
        Args:
            arc_data: Данные о дуге
            screen_width: Ширина экрана в пикселях
            view_bounds: Границы видимой области (x_min, y_min, x_max, y_max)
            min_pixel_distance: Минимальное расстояние между вершинами в пиксели
            
        Returns:
            Оптимальное число сегментов
        """
        x_min, y_min, x_max, y_max = view_bounds
        view_width = x_max - x_min
        
        # Масштаб: сколько единиц чертежа на пиксель
        scale = view_width / screen_width
        
        # Длина дуги в единицах чертежа
        arc_length = arc_data.length()
        
        # Сколько пикселей занимает дуга на экране
        arc_pixels = arc_length / scale
        
        # Требуемое число сегментов
        num_segments = max(
            10,
            int(arc_pixels / min_pixel_distance)
        )
        
        return min(num_segments, 1000)
    
    @staticmethod
    def render_with_lod(
        arc_data: ArcData,
        screen_width: float,
        view_bounds: Tuple[float, float, float, float],
        lod_level: int = 1
    ) -> List[Point]:
        """
        Отрисовка с контролем уровня детализации (LOD).
        
        LOD 1: Быстрая отрисовка (10-20 сегментов)
        LOD 2: Нормальная отрисовка (50-100 сегментов)
        LOD 3: Высокое качество (200+ сегментов)
        """
        if lod_level == 1:
            return Arc3Points.generate_arc_points(arc_data, num_segments=15)
        
        elif lod_level == 2:
            num_segments = AdaptiveArcRenderer.calculate_optimal_segments(
                arc_data, screen_width, view_bounds
            )
            return Arc3Points.generate_arc_points(arc_data, num_segments)
        
        else:
            num_segments = AdaptiveArcRenderer.calculate_optimal_segments(
                arc_data, screen_width, view_bounds, min_pixel_distance=1.0
            )
            return Arc3Points.generate_arc_points(arc_data, num_segments)


class CachedArc:
    """Кэширование вычисленных дуг"""
    
    def __init__(self, arc_data: ArcData):
        self.arc_data = arc_data
        self._cached_points = {}
    
    def get_points(self, num_segments: int) -> List[Point]:
        """Получить точки дуги с кэшированием"""
        if num_segments not in self._cached_points:
            self._cached_points[num_segments] = (
                Arc3Points.generate_arc_points(self.arc_data, num_segments)
            )
        
        return self._cached_points[num_segments]
    
    def clear_cache(self):
        """Очистить кэш"""
        self._cached_points.clear()


class ThreadedArcRenderer:
    """Многопоточная отрисовка для больших наборов дуг"""
    
    @staticmethod
    def render_multiple_arcs(
        arc_list: List[ArcData],
        num_segments: int = 100,
        num_threads: int = 4
    ) -> List[List[Point]]:
        """Параллельный расчёт нескольких дуг"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(Arc3Points.generate_arc_points, arc, num_segments)
                for arc in arc_list
            ]
            
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        return results


# ============================================================================
# ЭКСПОРТ И КОНВЕРТИРОВАНИЕ
# ============================================================================

class ArcFormat:
    """Конвертирование дуги в различные форматы"""
    
    @staticmethod
    def to_svg_path(arc_data: ArcData) -> str:
        """Экспорт в SVG format"""
        path = f"M {arc_data.start_point.x} {arc_data.start_point.y} "
        path += f"A {arc_data.radius} {arc_data.radius} 0 "
        path += f"{int(arc_data.is_large_arc)} 1 "
        path += f"{arc_data.end_point.x} {arc_data.end_point.y}"
        return path
    
    @staticmethod
    def to_dxf(arc_data: ArcData) -> str:
        """Экспорт в DXF format"""
        dxf_code = f"""0
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
{math.degrees(arc_data.end_angle)}"""
        return dxf_code
    
    @staticmethod
    def to_parametric(arc_data: ArcData, num_segments: int = 100) -> dict:
        """Экспорт как параметрическая кривая"""
        points = Arc3Points.generate_arc_points(arc_data, num_segments)
        
        return {
            'center': (arc_data.center.x, arc_data.center.y),
            'radius': arc_data.radius,
            'start_angle': math.degrees(arc_data.start_angle),
            'end_angle': math.degrees(arc_data.end_angle),
            'points': [(p.x, p.y) for p in points]
        }


# ============================================================================
# АНАЛИЗ И ПРОВЕРКА
# ============================================================================

class ArcAnalyzer:
    """Анализ и проверка свойств дуги"""
    
    @staticmethod
    def get_bounding_box(arc_data: ArcData) -> dict:
        """Получить bounding box дуги"""
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
    def point_on_arc(arc_data: ArcData, point: Point, tolerance: float = 0.01) -> bool:
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
        
        in_range = (arc_data.start_angle <= theta <= arc_data.start_angle + angle_diff or
                   arc_data.start_angle <= theta + 2*math.pi <= arc_data.start_angle + angle_diff)
        
        return in_range
    
    @staticmethod
    def intersect_with_line(
        arc_data: ArcData,
        line_start: Point,
        line_end: Point
    ) -> List[Point]:
        """Найти точки пересечения дуги с прямой линией"""
        x1, y1 = line_start.x, line_start.y
        x2, y2 = line_end.x, line_end.y
        xc, yc = arc_data.center.x, arc_data.center.y
        r = arc_data.radius
        
        dx = x2 - x1
        dy = y2 - y1
        
        a = dx*dx + dy*dy
        b = 2 * ((x1 - xc)*dx + (y1 - yc)*dy)
        c = (x1 - xc)**2 + (y1 - yc)**2 - r**2
        
        discriminant = b*b - 4*a*c
        
        if discriminant < 0:
            return []
        
        intersections = []
        t1 = (-b + math.sqrt(discriminant)) / (2*a)
        t2 = (-b - math.sqrt(discriminant)) / (2*a)
        
        for t in [t1, t2]:
            if 0 <= t <= 1:
                x = x1 + t * dx
                y = y1 + t * dy
                p = Point(x, y)
                
                if ArcAnalyzer.point_on_arc(arc_data, p):
                    intersections.append(p)
        
        return intersections


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

if __name__ == "__main__":
    print("=== Демонстрация Arc3Points ===\n")
    
    # Пример 1: Базовая дуга
    print("Пример 1: Базовая дуга")
    p1 = Point(0, 5)
    p2 = Point(5, 5)
    p3 = Point(5, 0)
    
    arc = Arc3Points.calculate(p1, p2, p3)
    print(f"  Центр: {arc.center}")
    print(f"  Радиус: {arc.radius:.4f}")
    print(f"  Длина дуги: {arc.length():.4f}\n")
    
    # Пример 2: Интерактивный редактор
    print("Пример 2: Интерактивный редактор")
    editor = InteractiveArcEditor()
    editor.on_click(Point(1, 2))
    editor.on_click(Point(4, 5))
    editor.on_click(Point(7, 2))
    print()
    
    # Пример 3: Анализ
    print("Пример 3: Анализ дуги")
    bbox = ArcAnalyzer.get_bounding_box(arc)
    print(f"  Bounding box: {bbox}\n")
    
    # Пример 4: Экспорт
    print("Пример 4: Экспорт")
    svg = ArcFormat.to_svg_path(arc)
    print(f"  SVG: {svg}\n")
    
    print("✓ Готово!")
