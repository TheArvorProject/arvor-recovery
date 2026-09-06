"""
PyQt6 and PySide6 compatibility layer for Arvor Recovery Mode.
Works on Debian/Arvor (PyQt6) and Arch/CachyOS (PySide6) seamlessly.
"""

import sys

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt, QThread, Signal, QTimer, QByteArray
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QStackedWidget, QMessageBox, QTextEdit,
        QListWidget, QListWidgetItem, QFrame, QProgressBar, QDialog
    )
    from PySide6.QtSvgWidgets import QSvgWidget
    from PySide6.QtSvg import QSvgRenderer
    QT_LIB = "PySide6"
except ImportError:
    try:
        from PyQt6 import QtWidgets, QtCore, QtGui
        from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal, QTimer, QByteArray
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QPushButton, QStackedWidget, QMessageBox, QTextEdit,
            QListWidget, QListWidgetItem, QFrame, QProgressBar, QDialog
        )
        from PyQt6.QtSvgWidgets import QSvgWidget
        from PyQt6.QtSvg import QSvgRenderer
        QT_LIB = "PyQt6"
    except ImportError as e:
        QT_LIB = None
