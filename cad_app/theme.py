# ======================================================================================
# 1. ДИЗАЙН-ТОКЕНЫ
# Qt понимает цвета только в HEX формате
# ======================================================================================
class DarkThemeColors:
    surface_default = "#121212"
    surface_elevated = "#1E1E1E"
    surface_canvas = "#2D2D2D"
    text_high_emphasis = "#DDFFFFFF"
    text_medium_emphasis = "#99FFFFFF"
    text_disabled = "#61FFFFFF"
    accent_primary_default = "#7A86CC"
    accent_primary_hover = "#98A3E0"
    border_subtle = "#1EFFFFFF"

# ======================================================================================
# 2. ТАБЛИЦА СТИЛЕЙ (QSS)
# Этот код остается без изменений, он просто будет использовать новые HEX-значения
# ======================================================================================
def get_stylesheet():
    colors = DarkThemeColors
    return f"""
        /* Общий стиль для всего приложения */
        QWidget {{
            background-color: {colors.surface_default};
            color: {colors.text_medium_emphasis};
            font-family: -apple-system, "Helvetica Neue", "Segoe UI", sans-serif;
            font-size: 14px;
        }}

        /* Стилизация главного окна */
        QMainWindow {{
            border: 1px solid {colors.border_subtle};
        }}

        /* Меню-бар */
        QMenuBar {{
            background-color: {colors.surface_default};
            border-bottom: 1px solid {colors.border_subtle};
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 5px 10px;
        }}
        QMenuBar::item:selected {{
            background-color: {colors.surface_elevated};
            color: {colors.text_high_emphasis};
        }}
        
        /* Выпадающее меню */
        QMenu {{
            background-color: {colors.surface_elevated};
            border: 1px solid {colors.border_subtle};
            padding: 5px;
        }}
        QMenu::item {{
            padding: 5px 15px;
        }}
        QMenu::item:selected {{
            background-color: {colors.accent_primary_default};
            color: {colors.text_high_emphasis};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {colors.border_subtle};
            margin: 5px 0;
        }}
        
        /* Панель инструментов (ToolBar) */
        QToolBar {{
            background-color: {colors.surface_default};
            border-bottom: 1px solid {colors.border_subtle};
            padding: 5px;
        }}
        QToolButton {{
            background-color: transparent;
            padding: 4px;
            border-radius: 4px;
        }}
        QToolButton:hover {{
            background-color: {colors.surface_elevated};
        }}
        QToolButton:checked {{
            background-color: {colors.accent_primary_default};
        }}
        QToolButton:disabled {{
            color: {colors.text_disabled};
        }}

        /* Строка состояния (StatusBar) */
        QStatusBar {{
            background-color: {colors.surface_default};
            border-top: 1px solid {colors.border_subtle};
        }}
        QStatusBar::item {{
            border: none;
        }}
    """