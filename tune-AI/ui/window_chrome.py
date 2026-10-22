"""Small, reusable dark chrome for secondary modal surfaces.

The main window deliberately keeps native OS chrome. Dialogs use this lighter
custom chrome so they remain on-brand without pretending to be a full window.
"""

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QDialog, QWidget


class _DialogChrome(QWidget):
    """Separate paint layer; reliable with Qt style sheets on every platform."""

    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        header = QLinearGradient(0, 0, self.width(), 0)
        header.setColorAt(0.0, QColor("#18383b"))
        header.setColorAt(0.46, QColor("#10282b"))
        header.setColorAt(1.0, QColor("#0a1b1e"))
        painter.fillRect(self.rect(), header)
        painter.setPen(QPen(QColor("#405b5e"), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        painter.setPen(QColor("#18c8c1"))
        painter.drawLine(15, 31, 43, 31)
        painter.setPen(QColor("#eef1ec"))
        painter.drawText(15, 25, self.dialog.windowTitle().upper())
        if self.width() >= 360:
            painter.setPen(QColor("#769091"))
            painter.drawText(self.width() - 166, 25, "THM  •  AUTOKEY")

        close_rect = self.dialog._close_rect()
        painter.setBrush(QColor("#101a1c"))
        painter.setPen(QPen(QColor("#5b6c6e"), 1))
        painter.drawRoundedRect(close_rect, 7, 7)
        painter.setPen(QPen(QColor("#d8e0dc"), 1.2))
        painter.drawLine(close_rect.left() + 7, close_rect.top() + 7,
                         close_rect.right() - 7, close_rect.bottom() - 7)
        painter.drawLine(close_rect.right() - 7, close_rect.top() + 7,
                         close_rect.left() + 7, close_rect.bottom() - 7)


class AnalogDialog(QDialog):
    """Fitted modern-instrument chrome shared by all AutoKey dialogs."""

    TITLE_HEIGHT = 42

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self._drag_origin: QPoint | None = None
        self._chrome = _DialogChrome(self)
        self._chrome.setGeometry(1, 1, max(0, self.width() - 2), self.TITLE_HEIGHT - 1)
        self._chrome.show()

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "_chrome"):
            self._chrome.update()

    def resizeEvent(self, event):
        self._chrome.setGeometry(1, 1, max(0, self.width() - 2), self.TITLE_HEIGHT - 1)
        self._chrome.raise_()
        super().resizeEvent(event)

    def _close_rect(self):
        return QRect(self.width() - 34, 8, 25, 25)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < self.TITLE_HEIGHT:
            if self._close_rect().contains(event.position().toPoint()):
                self.reject()
                return
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_origin = None
        super().mouseReleaseEvent(event)
