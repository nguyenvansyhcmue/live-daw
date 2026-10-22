"""Editable vocal-mode profile backed by the existing DAW macro protocol."""

from html import escape

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ui.analog_dialog_theme import ANALOG_DIALOG_QSS
from ui.macro_surface_state import macro_at
from ui.window_chrome import AnalogDialog


class ModeProfileDialog(AnalogDialog):
    def __init__(self, mode_key, settings, snapshot_provider, mapping_editor, parent=None):
        super().__init__(parent)
        self.mode_key = str(mode_key)
        self.settings = settings
        self.snapshot_provider = snapshot_provider
        self.mapping_editor = mapping_editor
        self.saved_label = settings.get_mode_label(self.mode_key)
        self.setWindowTitle("Thiết lập Vocal Mode")
        self.setMinimumSize(660, 590)
        self.setStyleSheet(ANALOG_DIALOG_QSS + """
            QLabel#ModeEyebrow { color:#57e4de; font-size:10px; font-weight:800; letter-spacing:3px; }
            QLabel#ModeTitle { color:#f0eadf; font-size:23px; font-weight:800; }
            QLabel#MacroSummary { color:#dce5e1; background:#081517; border:1px solid #3e5557;
                                  border-radius:7px; padding:10px 12px; }
            QLineEdit { min-height:38px; padding:0 12px; font-size:15px; }
            QPushButton { min-height:36px; padding:0 16px; }
        """)
        self._build()
        self._refresh_rows()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, self.TITLE_HEIGHT + 16, 24, 22)
        root.setSpacing(12)
        eyebrow = QLabel("VOCAL MODE • USER PROFILE", self)
        eyebrow.setObjectName("ModeEyebrow")
        root.addWidget(eyebrow)
        title = QLabel("Tên và bộ điều khiển riêng cho mode", self)
        title.setObjectName("ModeTitle")
        root.addWidget(title)
        hint = QLabel("Tên mới xuất hiện ngay trên header. Sáu núm bên dưới lưu đúng track/bus, "
                      "plug-in và parameter mà StudioForge đang công bố.", self)
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.name_edit = QLineEdit(self.saved_label, self)
        self.name_edit.setMaxLength(24)
        self.name_edit.setPlaceholderText("Tên Vocal Mode")
        root.addWidget(self.name_edit)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget(scroll)
        self.rows_layout = QVBoxLayout(body)
        self.rows_layout.setContentsMargins(0, 4, 0, 4)
        self.rows_layout.setSpacing(8)
        self._summaries = []
        for index in range(6):
            row = QWidget(body)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(row)
            label.setObjectName("MacroSummary")
            label.setWordWrap(True)
            button = QPushButton(f"GÁN / CHỈNH NÚM {index + 1}", row)
            button.clicked.connect(lambda _checked=False, i=index: self._edit_macro(i))
            layout.addWidget(label, 1)
            layout.addWidget(button)
            self.rows_layout.addWidget(row)
            self._summaries.append(label)
        self.rows_layout.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        close = QPushButton("ĐÓNG", self)
        close.clicked.connect(self.reject)
        save = QPushButton("LƯU MODE HIỆN TẠI", self)
        save.setObjectName("SaveMode")
        save.setProperty("primary", True)
        save.clicked.connect(self._save)
        actions.addWidget(close)
        actions.addStretch(1)
        actions.addWidget(save)
        root.addLayout(actions)

    def _snapshot(self):
        value = self.snapshot_provider()
        return value if isinstance(value, dict) else {}

    def _refresh_rows(self):
        snapshot = self._snapshot()
        for index, label in enumerate(self._summaries):
            macro = macro_at(snapshot, index) or {}
            if int(macro.get("state", 0) or 0) in (1, 2, 3) and macro.get("pluginInstanceId"):
                target = escape(str(macro.get("targetName") or macro.get("busName") or "Đích DAW"))
                plugin = escape(str(macro.get("pluginName") or "Plug-in"))
                name = escape(str(macro.get("macroName") or "Parameter"))
                label.setText(f"<b>NÚM {index + 1} · {name}</b><br><small>{target}  ›  {plugin}</small>")
            else:
                label.setText(f"<b>NÚM {index + 1} · CHƯA GÁN</b><br><small>Chọn track/bus, plug-in và parameter.</small>")

    def _edit_macro(self, index):
        self.mapping_editor(index)
        self._refresh_rows()

    def _save(self):
        self.saved_label = self.settings.set_mode_label(self.mode_key, self.name_edit.text())
        self.settings.save_mode_macro_profile(self.mode_key, self._snapshot())
        self.accept()
