"""Compact selector for the DAW EQ rendered on the performance surface.

This dialog deliberately exposes only rack and plug-in identity. Band creation,
editing and removal belong on the graph itself; users should never need to
navigate hundreds of raw automation parameters for normal EQ work.
"""
from PyQt6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout,
                             QLabel, QPushButton, QVBoxLayout)

from ui.analog_dialog_theme import ANALOG_DIALOG_QSS
from ui.window_chrome import AnalogDialog


class EqParameterDialog(AnalogDialog):
    def __init__(self, snapshot, surface, parent=None):
        super().__init__(parent)
        self.surface = surface
        self.eq_descriptor = None
        self.setWindowTitle("Chọn EQ cho waveform")
        self.setStyleSheet(ANALOG_DIALOG_QSS)
        self.resize(520, 245)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, self.TITLE_HEIGHT + 16, 22, 20)
        layout.setSpacing(12)
        self.status = QLabel(
            "Chọn rack và EQ. Sau đó nhấp trực tiếp lên waveform để tạo band.", self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        form = QFormLayout()
        self.bus = QComboBox(self)
        self.plugin = QComboBox(self)
        form.addRow("Nguồn / rack", self.bus)
        form.addRow("Plug-in EQ", self.plugin)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.activate_button = QPushButton("Dùng trên waveform", self)
        self.activate_button.setObjectName("ActivateButton")
        self.activate_button.setProperty("primary", True)
        refresh = QPushButton("Quét lại", self)
        close = QPushButton("Hủy", self)
        buttons.addWidget(self.activate_button)
        buttons.addWidget(refresh)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self.bus.currentIndexChanged.connect(self._plugins_changed)
        self.plugin.currentIndexChanged.connect(self._load_descriptor)
        self.activate_button.clicked.connect(self._activate)
        refresh.clicked.connect(self._load_descriptor)
        close.clicked.connect(self.reject)

        targets = snapshot.get("eqTargets", snapshot.get("buses", [])) if isinstance(snapshot, dict) else []
        for target in targets if isinstance(targets, list) else []:
            if isinstance(target, dict):
                self.bus.addItem(str(target.get("name") or "Rack"), target)

        analysis = snapshot.get("audioAnalysis", {}) if isinstance(snapshot, dict) else {}
        if isinstance(analysis, dict):
            kind = str(analysis.get("sourceKind", "master"))
            source_id = str(analysis.get("sourceId", "master"))
            wanted = "master" if kind == "master" else (
                f"track:{source_id}" if kind == "track" else source_id)
            for index in range(self.bus.count()):
                target = self.bus.itemData(index)
                if isinstance(target, dict) and str(target.get("id")) == wanted:
                    self.bus.setCurrentIndex(index)
                    break
        self._plugins_changed()

    def _plugins_changed(self):
        self.plugin.blockSignals(True)
        self.plugin.clear()
        target = self.bus.currentData()
        plugins = target.get("plugins", []) if isinstance(target, dict) else []
        for plugin in plugins if isinstance(plugins, list) else []:
            if isinstance(plugin, dict):
                self.plugin.addItem(str(plugin.get("name") or "Plug-in"), plugin)
        self.plugin.blockSignals(False)
        self._load_descriptor()

    def _target(self):
        bus, plugin = self.bus.currentData(), self.plugin.currentData()
        if not isinstance(bus, dict) or not isinstance(plugin, dict):
            return None
        if not bus.get("id") or not plugin.get("instanceId") or not isinstance(plugin.get("slot"), int):
            return None
        return str(bus["id"]), plugin["slot"], str(plugin["instanceId"])

    def _load_descriptor(self):
        target = self._target()
        descriptor = self.surface.get_eq_surface(*target) if target else None
        self.eq_descriptor = descriptor if isinstance(descriptor, dict) and descriptor.get("ok") else None
        interactive = bool(self.eq_descriptor and
                           self.eq_descriptor.get("capability") == "eq_interactive")
        self.activate_button.setEnabled(interactive)
        if interactive:
            plugin_name = str(self.eq_descriptor.get("pluginName") or self.plugin.currentText())
            self.status.setText(
                f"{plugin_name} đã sẵn sàng. Nhấp vùng trống để tạo band · "
                "kéo để chỉnh · lăn chuột để đổi Q · nhấp đúp để xóa.")
        elif target and self.eq_descriptor:
            self.status.setText(
                "Plug-in này chưa cung cấp mô hình Frequency/Gain/Q đã xác minh để kéo trực tiếp.")
        else:
            error = descriptor.get("error") if isinstance(descriptor, dict) else getattr(self.surface, "last_error", "")
            self.status.setText(str(error or "Không tìm thấy EQ trong rack đã chọn."))

    def _activate(self):
        if not self.activate_button.isEnabled() or not isinstance(self.eq_descriptor, dict):
            return
        bus = self.bus.currentData()
        if isinstance(bus, dict) and hasattr(self.surface, "set_analysis_source"):
            scope, target_id = str(bus.get("scope", "bus")), str(bus.get("id", ""))
            source_id = target_id.split(":", 1)[1] if scope == "track" and ":" in target_id else target_id
            self.surface.set_analysis_source(scope, source_id)
        self.accept()
