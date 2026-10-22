"""Shared AutoKey visual system for every secondary surface.

The main panel is a modern analog/digital instrument: deep teal anodised
metal, fitted graphite modules, restrained cyan telemetry and a very small
amount of warm metal. Dialogs use the same materials instead of the older
brown rack-drawer skin or native desktop controls.
"""

from html import escape

from PyQt6.QtCore import Qt


ANALOG_DIALOG_QSS = """
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #173033, stop:.16 #12272a, stop:1 #0b1719);
    color: #e9ece8;
    border: 1px solid #526568;
    font-family: "SF Pro Display", "Segoe UI", "Arial", sans-serif;
    font-size: 12px;
}
QWidget { color: #e9ece8; }
QWidget#SettingsWrap, QWidget#DialogTransparentWrap { background: transparent; }
QLabel { color: #e4e8e4; background: transparent; font-size: 12px; font-weight: 600; }
QLabel#DialogTitle {
    color: #f2f3ed; font-size: 18px; font-weight: 800; letter-spacing: 2px;
}
QLabel#DialogCaption, QLabel#SettingsHelpLabel {
    color: #9fb2b2; font-size: 11px; font-weight: 500;
}
QLabel#SettingsValueLabel, QLabel#InsetReadout {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #071215, stop:1 #0b1b1e);
    color: #dce5e2;
    border: 1px solid #405457;
    border-top-color: #26383b;
    border-radius: 6px;
    padding: 7px 9px;
    min-height: 18px;
}
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, QPlainTextEdit {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #071316, stop:1 #0b1b1e);
    color: #eef2ee;
    border: 1px solid #40575a;
    border-top-color: #263a3d;
    border-radius: 6px;
    padding: 7px 10px;
    min-height: 22px;
    selection-background-color: #167a7b;
    selection-color: #ffffff;
}
QLineEdit:hover, QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover { border-color: #587174; }
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #22c9c5;
    background: #0a1d20;
}
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {
    color: #667779; border-color: #29383a; background: #0b1315;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {
    width: 18px; background: #15282b; border-left: 1px solid #40575a;
}
QComboBox::drop-down { border: none; width: 28px; background: #132629; }
QComboBox QAbstractItemView {
    background: #0c1a1c; color: #e7ece8; border: 1px solid #52686a;
    outline: 0; padding: 5px; selection-background-color: #15585a; selection-color: #ffffff;
}
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #273336, stop:.12 #1b2527, stop:.76 #101719, stop:1 #080d0e);
    color: #e5e8e4;
    border: 1px solid #536164;
    border-bottom-color: #202a2c;
    border-radius: 6px;
    padding: 7px 14px;
    min-height: 22px;
    font-size: 12px;
    font-weight: 750;
}
QPushButton:hover {
    border-color: #24c8c4;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #24484a, stop:1 #102224);
    color: #f7fbf8;
}
QPushButton:pressed {
    background: #071214; border-color: #157e7d; padding-top: 9px; padding-bottom: 5px;
}
QPushButton:disabled { color: #617073; border-color: #2b383a; background: #101719; }
QPushButton[primary="true"], QPushButton#SaveMode, QPushButton#AssignButton,
QPushButton#ActivateButton {
    color: #061415;
    border-color: #68eee7;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #6be8e1, stop:.12 #27c9c4, stop:1 #148486);
}
QPushButton[primary="true"]:hover, QPushButton#SaveMode:hover,
QPushButton#AssignButton:hover, QPushButton#ActivateButton:hover {
    color: #021011; border-color: #a4fff8; background: #55ddd7;
}
QPushButton[destructive="true"], QPushButton#SettingsDangerButton {
    color: #ffb4aa; border-color: #81504c; background: #291716;
}
QPushButton[destructive="true"]:hover, QPushButton#SettingsDangerButton:hover {
    background: #3a1e1c; border-color: #db7368;
}
QGroupBox {
    color: #dfe6e2;
    font-size: 12px;
    font-weight: 800;
    border: 1px solid #3f5355;
    border-top-color: #617174;
    border-radius: 8px;
    margin-top: 14px;
    padding: 13px 10px 10px 10px;
    background: rgba(5, 14, 16, 118);
}
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 0 7px;
    color: #bfcac6; background: #122629;
}
QTableWidget, QListWidget, QTreeWidget {
    background: #071416;
    alternate-background-color: #0b1c1f;
    color: #e5e9e5;
    gridline-color: #223638;
    border: 1px solid #43575a;
    border-radius: 7px;
    selection-background-color: #14585b;
    selection-color: #ffffff;
    outline: 0;
}
QTableWidget::item, QListWidget::item, QTreeWidget::item {
    padding: 7px; border-bottom: 1px solid #1d3032;
}
QTableWidget::item:hover, QListWidget::item:hover, QTreeWidget::item:hover { background: #102a2d; }
QHeaderView::section {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #273538, stop:1 #152326);
    color: #d8dfdb;
    padding: 8px;
    border: none;
    border-right: 1px solid #35494b;
    border-bottom: 1px solid #59686a;
    font-size: 11px;
    font-weight: 800;
}
QCheckBox { color: #dfe5e1; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #526568;
    border-radius: 4px; background: #071214;
}
QCheckBox::indicator:hover { border-color: #2dd4cf; }
QCheckBox::indicator:checked { background: #1db9b6; border-color: #68eee7; }
QScrollArea { background: transparent; border: 0; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: #081315; width: 10px; margin: 3px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #3c5658; min-height: 28px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #258d8d; }
QScrollBar:horizontal { background: #081315; height: 10px; margin: 3px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #3c5658; min-width: 28px; border-radius: 4px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QProgressBar {
    background: #071214; border: 1px solid #405457; border-radius: 5px;
    color: #e7efeb; text-align: center;
}
QProgressBar::chunk { background: #1fc4c0; border-radius: 4px; }
QToolTip {
    color: #eef3ef; background: #0c1b1d; border: 1px solid #4e6668;
    padding: 6px; border-radius: 4px;
}
"""


ANALOG_MESSAGE_BOX_QSS = ANALOG_DIALOG_QSS + """
QMessageBox {
    border: 1px solid #5f7274;
    border-radius: 10px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #173033, stop:.20 #102326, stop:1 #091719);
}
QMessageBox QLabel {
    min-width: 350px;
    color: #e8ede9;
    font-size: 13px;
    font-weight: 600;
    padding: 12px 8px;
}
QMessageBox QPushButton { min-width: 96px; }
"""


def apply_analog_dialog_theme(widget):
    """Apply the shared AutoKey instrument appearance to a secondary view."""
    widget.setStyleSheet(ANALOG_DIALOG_QSS)


def apply_analog_message_theme(message_box):
    """Keep information, warning and confirmation boxes on the same chassis."""
    title = escape(str(message_box.property("analogTitle") or message_box.windowTitle()).strip())
    text = escape(message_box.text()).replace("\n", "<br>")
    if title:
        message_box.setText(
            "<span style='color:#64e8e2;font-size:10px;font-weight:800;letter-spacing:2px'>"
            "AUTOKEY • SYSTEM</span><br>"
            f"<b style='font-size:16px'>{title}</b><br><span>{text}</span>"
        )
    message_box.setWindowFlags(message_box.windowFlags() | Qt.WindowType.FramelessWindowHint)
    message_box.setStyleSheet(ANALOG_MESSAGE_BOX_QSS)
