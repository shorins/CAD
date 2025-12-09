import copy
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

class LineStyle:
    """
    Структура данных, описывающая стиль линии согласно ГОСТ 2.303-68.
    """
    def __init__(self, name, width_mult=2.0, pattern=None, is_default=False, description=""):
        self.name = name
        # Множитель толщины относительно базовой S (4.0 для основной, 2.0 для тонкой и т.д.)
        self.width_mult = width_mult
        # Паттерн штриховки для Qt (список длин штрихов и пробелов)
        # Если None - линия сплошная (SolidLine)
        self.pattern = pattern
        # Флаг защиты от удаления (для стандартных стилей ГОСТ)
        self.is_default = is_default
        self.description = description

    def to_dict(self):
        """Сериализация в словарь для сохранения в JSON."""
        return {
            "name": self.name,
            "width_mult": self.width_mult,
            "pattern": self.pattern,
            "is_default": self.is_default,
            "description": self.description
        }

    @staticmethod
    def from_dict(data):
        """Десериализация из словаря."""
        return LineStyle(
            data["name"],
            data.get("width_mult", 1.0),
            data.get("pattern"),
            data.get("is_default", False),
            data.get("description", "")
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
        # Базовая толщина линии S в пикселях (по умолчанию для экрана ~2px визуально приятно)
        self.base_width = 4.0
        
        self.styles = {}
        self.current_style_name = "Сплошная основная"
        
        # Инициализируем стандартные стили ГОСТ
        self._init_default_styles()

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
        
        # 4. Штриховая
        # Толщина S/2 ... S/3. Паттерн: штрих 2-8мм, просвет 1-2мм.
        self.add_style(LineStyle(
            "Штриховая", 
            width_mult=0.5, 
            pattern=[12.0, 4.0], # 6мм штрих, 2мм просвет
            is_default=True, 
            description="Линии невидимого контура"
        ))
        
        # 5. Штрихпунктирная тонкая
        # ГОСТ: Штрихи 5-30 мм, просветы 3-5 мм.
        # Цель: ~10 мм штрих, ~3 мм просвет.
        # Расчет: 10/0.4 = 25. 3/0.4 = 7.5.
        # Оптимально для экрана (чтобы не было слишком редко):
        self.add_style(LineStyle(
            "Штрихпунктирная тонкая", 
            width_mult=0.5, 
            pattern=[20.0, 6.0, 1.0, 6.0], 
            is_default=True, 
            description="Осевые и центровые линии"
        ))
        
        # 6. Штрихпунктирная утолщенная
        # Она толще (0.8 от S), значит линия ~0.6-0.7 мм.
        # Чтобы штрихи визуально были такой же длины как у тонкой, коэффициенты должны быть меньше!
        # 10 мм / 0.7 мм ≈ 14.
        self.add_style(LineStyle(
            "Штрихпунктирная утолщенная", 
            width_mult=0.8, 
            pattern=[14.0, 4.0, 1.0, 4.0], # Коэффициенты меньше, потому что сама линия толще
            is_default=True
        ))
        
        # 7. Разомкнутая
        # Толщина 1.5S.
        self.add_style(LineStyle(
            "Разомкнутая", 
            width_mult=1.5, 
            pattern=None, 
            is_default=True, 
            description="Линии сечений"
        ))

        # 9. Штрихпунктирная с двумя точками
        # ГОСТ: Штрихи 5-30 мм, просветы 4-6 мм (шире, чем у осевой).
        # Расчет для S=0.8мм (тонкая=0.4мм):
        # Штрих 12мм -> к=30. Просвет 4мм -> к=10. Точка -> к=1.
        self.add_style(LineStyle(
            "Штрихпунктирная с двумя точками", 
            width_mult=0.5, 
            pattern=[30.0, 10.0, 1.0, 10.0, 1.0, 10.0], 
            is_default=True, 
            description="Линии сгиба, крайние положения"
        ))

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
            self.base_width = width
            self.style_changed.emit()

# Глобальный экземпляр, который будем импортировать в других файлах
style_manager = StyleManager()