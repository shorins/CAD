# Определение главного окна QMainWindow

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStatusBar
from PySide6.QtGui import QAction

from.core.scene import Scene
from.canvas_widget import CanvasWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Примитивная 2D САПР")
        self.setGeometry(100, 100, 800, 600)

        # Создаем экземпляр нашей Модели
        self.scene = Scene()

        # Создаем Представление/Контроллер и передаем ему Модель
        self.canvas = CanvasWidget(self.scene)
        self.setCentralWidget(self.canvas)

        # Настраиваем меню
        self._create_menus()
        
        # Настраиваем статус-бар
        self.setStatusBar(QStatusBar(self))

    def _create_menus(self):
        # Меню "Файл"
        file_menu = self.menuBar().addMenu("&Файл")
        
        new_action = QAction("&Новый", self)
        new_action.triggered.connect(self.scene.clear)
        file_menu.addAction(new_action)

        # TODO: Добавить действия "Сохранить" и "Загрузить"

        exit_action = QAction("&Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)