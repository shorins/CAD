import copy
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

class LineStyle:
    """
    Структура данных, описывающая стиль линии согласно ГОСТ 2.303-68.
    """
    def __init__(self, name, width_mult=2.0, pattern=None, is_default=False, description="", params=None):
        self.name = name
        # Множитель толщины относительно базовой S (4.0 для основной, 2.0 для тонкой и т.д.)
        self.width_mult = width_mult
        # Паттерн штриховки для Qt (список длин штрихов и пробелов)
        # Если None - линия сплошная (SolidLine)
        self.pattern = pattern
        # Флаг защиты от удаления (для стандартных стилей ГОСТ)
        self.is_default = is_default
        self.description = description
        # params хранит настройки в мм: {'dash': 6.0, 'gap': 2.0} и т.д.
        # Если None - стиль не настраивается по длине штрихов
        self.params = params if params else {}

    def to_dict(self):
        """Сериализация в словарь для сохранения в JSON."""
        return {
            "name": self.name,
            "width_mult": self.width_mult,
            "pattern": self.pattern,
            "is_default": self.is_default,
            "description": self.description,
            "params": self.params
        }

    @staticmethod
    def from_dict(data):
        """Десериализация из словаря."""
        return LineStyle(
            data["name"],
            data.get("width_mult", 1.0),
            data.get("pattern"),
            data.get("is_default", False),
            data.get("description", ""),
            data.get("params", {})
        )

class StyleManager(QObject):
    """
    Централизованный менеджер стилей линий.
    Управляет списком стилей и текущим активным стилем.
    """
    # Сигнал испускается при любом изменении в стилях (добавление, выбор текущего, изменение S)
    style_changed = Signal()

    def __init__(self):
        super().__init__()
        # Глобальная толщина S в МИЛЛИМЕТРАХ (по умолчанию 0.8)
        self.base_s_mm = 0.8

        # Базовая толщина линии S в пикселях
        self.base_width_px = 4.0 # вычисляется и заменяется при старте программы
        
        self.styles = {}
        self.current_style_name = "Сплошная основная"
        
        # Инициализируем стандартные стили ГОСТ
        self._init_default_styles()

    def to_dict(self):
        """Сериализует состояние менеджера стилей."""
        return {
            "base_s_mm": self.base_s_mm,
            # Сохраняем все стили. Если в будущем добавим создание своих стилей,
            # это позволит их тоже сохранять циклом
            "styles": [s.to_dict() for s in self.styles.values()]
        }

    def load_from_dict(self, data):
        """Восстанавливает состояние из словаря."""
        if not data:
            return

        # 1. Восстанавливаем глобальную толщину
        if "base_s_mm" in data:
            self.base_s_mm = float(data["base_s_mm"])
            # пересчитаем dpi заново
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                dpi = screen.logicalDotsPerInch()
                self.set_base_width_px_from_dpi(dpi)

        # 2. Восстанавливаем стили
        if "styles" in data:
            for style_data in data["styles"]:
                # Создаем объект стиля из данных
                loaded_style = LineStyle.from_dict(style_data)
                
                # Обновляем существующий стиль или добавляем новый
                # (params тоже загрузятся внутри from_dict)
                self.styles[loaded_style.name] = loaded_style

        # 3. Пересчитываем паттерны (Qt коэффициенты) на основе загруженных мм
        self._recalculate_all_patterns()
        
        # Уведомляем всех об изменениях
        self.style_changed.emit()

    def set_base_s_mm(self, mm: float):
        """Изменяет глобальную S (в мм) и пересчитывает паттерны."""
        self.base_s_mm = mm
        self._recalculate_all_patterns()
        self.style_changed.emit()

    def set_base_width_px_from_dpi(self, dpi):
        """Вычисляет пиксельный размер S исходя из заданных мм и DPI."""
        # pixel = mm * (dpi / 25.4)
        px = self.base_s_mm * (dpi / 25.4)
        self.base_width_px = max(1.5, px)
        self.style_changed.emit()

    def update_style_params(self, style_name, new_params):
        """Обновляет параметры конкретного стиля (в мм) и пересчитывает его паттерн."""
        style = self.styles.get(style_name)
        if style:
            style.params.update(new_params)
            self._recalculate_style_pattern(style)
            self.style_changed.emit()

    def _recalculate_all_patterns(self):
        for style in self.styles.values():
            self._recalculate_style_pattern(style)

    def _recalculate_style_pattern(self, style: LineStyle):
        """
        Магия перевода мм в коэффициенты Qt.
        Формула: Coeff = Length_mm / (S_mm * width_mult)
        """
        if not style.params or not style.pattern:
            return

        # Реальная толщина линии в мм
        line_width_mm = self.base_s_mm * style.width_mult
        if line_width_mm == 0: return

        # Извлекаем параметры (с дефолтными значениями на всякий случай)
        dash = style.params.get('dash', 0)
        gap = style.params.get('gap', 0)
        
        # Пересчитываем в коэффициенты Qt
        # k = Value_mm / Line_Width_mm
        k_dash = dash / line_width_mm
        k_gap = gap / line_width_mm
        
        # Размер точки (dot) фиксируем, например 0.5 мм или 1.0 от толщины
        k_dot = 1.0 # Точка = толщине линии (квадратная)

        if style.name == "Штриховая":
            style.pattern = [k_dash, k_gap]
            
        elif style.name in ["Штрихпунктирная тонкая", "Штрихпунктирная утолщенная"]:
            style.pattern = [k_dash, k_gap, k_dot, k_gap]
            
        elif style.name == "Штрихпунктирная с двумя точками":
            style.pattern = [k_dash, k_gap, k_dot, k_gap, k_dot, k_gap]

    def _init_default_styles(self):
        """Создает стандартные стили согласно ГОСТ 2.303-68."""
        # Очищаем текущие стили
        self.styles.clear()

        # 1. Сплошная толстая основная
        # Толщина S. 
        self.add_style(LineStyle(
            "Сплошная основная", 
            width_mult=1.0, 
            pattern=None, 
            is_default=True, 
            description="Линии видимого контура"
        ))
        
        # 2. Сплошная тонкая
        # Толщина от S/3 до S/2. Берем 0.5.
        self.add_style(LineStyle(
            "Сплошная тонкая", 
            width_mult=0.5, 
            pattern=None, 
            is_default=True, 
            description="Размерные и выносные линии"
        ))
        
        # 3. Сплошная волнистая
        # Технически сложно реализуется через QPen (нужен QPainterPath), 
        # пока оставляем как сплошную тонкую с пометкой.
        self.add_style(LineStyle(
            "Сплошная волнистая", 
            width_mult=0.5, 
            pattern=None, # Требует спец. рендеринга, пока заглушка
            is_default=True, 
            description="Линии обрыва"
        ))
        
        # 4. Штриховая (Настраиваемая!)
        # ГОСТ: Штрих 2-8, Пробел 1-2. Дефолт: 4, 1.5
        s4 = LineStyle("Штриховая", 0.5, [1, 1], True, "Линии невидимого контура", 
                       params={'dash': 4.0, 'gap': 1.5})
        self.add_style(s4)
        
        # 5. Штрихпунктирная тонкая (Настраиваемая!)
        # ГОСТ: Штрих 5-30, Пробел 3-5. Дефолт: 12, 4
        s5 = LineStyle("Штрихпунктирная тонкая", 0.5, [1, 1], True, "Осевые и центровые линии",
                       params={'dash': 12.0, 'gap': 4.0})
        self.add_style(s5)
        
        # 6. Штрихпунктирная утолщенная (Настраиваемая!)
        # ГОСТ: Штрих 3-8, Пробел 3-4. Дефолт: 6, 3
        s6 = LineStyle("Штрихпунктирная утолщенная", 0.8, [1, 1], True, description="",
                       params={'dash': 6.0, 'gap': 3.0})
        self.add_style(s6)
        
        # 7. Разомкнутая
        # Толщина 1.5S.
        self.add_style(LineStyle(
            "Разомкнутая", 
            width_mult=1.5, 
            pattern=None, 
            is_default=True, 
            description="Линии сечений"
        ))

        # 8. Сплошная тонкая с изломами
        # ГОСТ: Толщина S/3 ... S/2.
        # Длинные линии обрыва.
        self.add_style(LineStyle(
            "Сплошная с изломами", 
            width_mult=0.5, 
            pattern=None, # Спец. рендеринг (как у волнистой)
            is_default=True, 
            description="Длинные линии обрыва"
        ))

        # 9. Штрихпунктирная с двумя точками (Настраиваемая!)
        # ГОСТ: Штрих 5-30, Пробел 4-6. Дефолт: 15, 4
        s9 = LineStyle("Штрихпунктирная с двумя точками", 0.5, [1, 1], True, "Линии сгиба",
                       params={'dash': 15.0, 'gap': 4.0})
        self.add_style(s9)

        # Первичный пересчет всех паттернов на основе дефолтного base_s_mm=0.8
        self._recalculate_all_patterns()

    def add_style(self, style: LineStyle):
        """Добавляет новый стиль или обновляет существующий."""
        self.styles[style.name] = style
        self.style_changed.emit()

    def get_style(self, name: str) -> LineStyle:
        """Возвращает объект стиля по имени. Если не найден - возвращает основной."""
        return self.styles.get(name, self.styles["Сплошная основная"])

    def set_current_style(self, name: str):
        """Устанавливает текущий активный стиль для новых линий."""
        if name in self.styles:
            self.current_style_name = name
            self.style_changed.emit()
            
    def get_current_style(self) -> LineStyle:
        """Возвращает объект текущего активного стиля."""
        return self.get_style(self.current_style_name)

    def set_base_width(self, width: float):
        """Устанавливает базовую толщину линий S."""
        if 0.5 <= width <= 50.0: # Разумные пределы в пикселях
            self.base_width_px = width
            self.style_changed.emit()

    @property
    def base_width(self):
        """Свойство для совместимости с кодом CanvasWidget"""
        return self.base_width_px

# Глобальный экземпляр, который будем импортировать в других файлах
style_manager = StyleManager()