# Точка входа в приложение

import sys
from PySide6.QtWidgets import QApplication
from .main_window import MainWindow

def main():
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        return app.exec()
    except Exception as e:
        print(f"Ошибка запуска приложения: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
