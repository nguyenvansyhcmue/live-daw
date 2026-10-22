"""Focused, performer-first setup surface for StudioForge macro knobs."""

from __future__ import annotations

from typing import Any
from html import escape

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
                             QVBoxLayout, QWidget)

from ui.analog_dialog_theme import ANALOG_DIALOG_QSS
from ui.macro_surface_state import macro_at
from ui.window_chrome import AnalogDialog


class PerformanceMacroDialog(AnalogDialog):
    """A single, truthful path from effect return to one physical knob."""
    TITLE_HEIGHT = 48

    def __init__(self, macro_index: int, snapshot: dict[str, Any], surface, parent=None):
        super().__init__(parent)
        self.macro_index = macro_index
        self.snapshot = snapshot if isinstance(snapshot, dict) else {}
        self.surface = surface
        self._parameter_cache: list[dict[str, Any]] = []
        self._all_parameter_count = 0
        self._smart_proposal: dict[str, Any] | None = None

        self.setWindowTitle(f"Gán núm {macro_index + 1}")
        self.setStyleSheet(ANALOG_DIALOG_QSS + """
            QLabel#MacroSetupTitle { color:#f0f2ed; font-size:18px; font-weight:800; letter-spacing:2px; }
            QLabel#ConnectionBadge { color:#74efb1; background:#0b2921; border:1px solid #2d765a;
                border-radius:13px; padding:5px 11px; font-size:10px; font-weight:800; }
            QLabel#MacroFieldLabel { color:#dde6e2; font-size:12px; font-weight:700; }
            QLabel#MacroPreview { color:#d9e4df; background:#071517; border:1px solid #40575a;
                border-radius:8px; padding:12px 14px; font-size:11px; }
            QLabel#MacroHint { color:#91a6a6; font-size:10px; font-weight:500; }
            QLabel#ParameterCount { color:#8fa5a3; font-size:10px; font-weight:700; }
            QPushButton#SuggestButton { color:#72eee7; border-color:#247b7b; background:#10292b; }
            QPushButton#AdvancedButton { color:#aebfbb; text-align:left; padding:7px 10px; }
        """)
        available_width = parent.width() if parent is not None else 720
        self.setFixedWidth(max(320, min(720, available_width - 24)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, self.TITLE_HEIGHT + 14, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(f"MACRO {macro_index + 1}  •  ROUTING", self)
        title.setObjectName("MacroSetupTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.connection_badge = QLabel("ĐANG KẾT NỐI...", self)
        self.connection_badge.setObjectName("ConnectionBadge")
        header.addWidget(self.connection_badge)
        layout.addLayout(header)

        self.caption = QLabel("Chọn hiệu ứng bạn muốn điều khiển.", self)
        self.caption.setObjectName("DialogCaption")
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)

        fields = QGridLayout()
        fields.setContentsMargins(6, 5, 6, 0)
        fields.setHorizontalSpacing(12)
        fields.setVerticalSpacing(11)
        fields.setColumnStretch(1, 1)
        self.bus_picker = QComboBox(self)
        self.plugin_picker = QComboBox(self)
        self.function_picker = QComboBox(self)
        self.field_labels = [self._add_field(fields, 0, "Đích trong DAW", self.bus_picker),
                             self._add_field(fields, 1, "Plug-in", self.plugin_picker),
                             self._add_field(fields, 2, "Thông số", self.function_picker)]
        self.suggest_button = QPushButton("✦  TỰ ĐỀ XUẤT", self)
        self.suggest_button.setObjectName("SuggestButton")
        self.rescan_button = QPushButton("↻  QUÉT LẠI", self)
        fields.addWidget(self.suggest_button, 0, 2)
        fields.addWidget(self.rescan_button, 1, 2)
        layout.addLayout(fields)

        parameter_tools = QHBoxLayout()
        parameter_tools.setContentsMargins(6, 0, 6, 0)
        self.parameter_mode_picker = QComboBox(self)
        self.parameter_mode_picker.addItem("★  THÔNG SỐ CHÍNH", "recommended")
        self.parameter_mode_picker.addItem("TẤT CẢ THÔNG SỐ", "all")
        self.parameter_search = QLineEdit(self)
        self.parameter_search.setPlaceholderText("Tìm tên, nhóm hoặc chức năng…")
        self.parameter_search.setClearButtonEnabled(True)
        self.parameter_search.setVisible(False)
        self.parameter_count = QLabel(self)
        self.parameter_count.setObjectName("ParameterCount")
        parameter_tools.addWidget(self.parameter_mode_picker)
        parameter_tools.addWidget(self.parameter_search, 1)
        parameter_tools.addWidget(self.parameter_count)
        layout.addLayout(parameter_tools)

        self.advanced_button = QPushButton("▸  TINH CHỈNH PHẠM VI NÚM", self)
        self.advanced_button.setObjectName("AdvancedButton")
        self.advanced_button.setCheckable(True)
        layout.addWidget(self.advanced_button)

        self.mapping_options = QWidget(self)
        options = QHBoxLayout(self.mapping_options)
        options.setContentsMargins(6, 0, 6, 0)
        options.setSpacing(8)
        self.minimum_picker = QDoubleSpinBox(self.mapping_options)
        self.maximum_picker = QDoubleSpinBox(self.mapping_options)
        for picker, value in ((self.minimum_picker, 0.0), (self.maximum_picker, 1.0)):
            picker.setRange(0.0, 1.0)
            picker.setDecimals(2)
            picker.setSingleStep(0.05)
            picker.setValue(value)
        self.smoothing_picker = QSpinBox(self.mapping_options)
        self.smoothing_picker.setRange(0, 250)
        self.smoothing_picker.setSuffix(" ms")
        self.smoothing_picker.setValue(15)
        self.curve_picker = QComboBox(self.mapping_options)
        self.curve_picker.addItem("Tuyến tính", 0)
        self.curve_picker.addItem("Log", 1)
        self.curve_picker.addItem("Mũ", 2)
        self.curve_picker.addItem("S-curve", 3)
        self.invert_picker = QCheckBox("Đảo chiều", self.mapping_options)
        for text, control in (("Min", self.minimum_picker), ("Max", self.maximum_picker),
                              ("Mượt", self.smoothing_picker)):
            label = QLabel(text, self.mapping_options)
            label.setObjectName("MacroFieldLabel")
            options.addWidget(label)
            options.addWidget(control)
        curve_label = QLabel("Curve", self.mapping_options)
        curve_label.setObjectName("MacroFieldLabel")
        options.addWidget(curve_label)
        options.addWidget(self.curve_picker)
        options.addWidget(self.invert_picker)
        options.addStretch(1)
        layout.addWidget(self.mapping_options)
        self.mapping_options.setVisible(False)

        self.preview = QLabel(self)
        self.preview.setObjectName("MacroPreview")
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(78)
        layout.addWidget(self.preview)

        footer = QHBoxLayout()
        self.hint = QLabel("ⓘ  Danh sách được đọc trực tiếp từ Master, track/line và bus đang có trong DAW.", self)
        self.hint.setObjectName("MacroHint")
        self.hint.setWordWrap(True)
        footer.addWidget(self.hint, 1)
        cancel = QPushButton("Hủy", self)
        self.assign_button = QPushButton("Gán núm", self)
        self.assign_button.setObjectName("AssignButton")
        self.assign_button.setProperty("primary", True)
        footer.addWidget(cancel)
        footer.addWidget(self.assign_button)
        layout.addLayout(footer)

        self.bus_picker.currentIndexChanged.connect(lambda _index: self._populate_plugins())
        self.plugin_picker.currentIndexChanged.connect(self._plugin_changed)
        self.function_picker.currentIndexChanged.connect(self._manual_parameter_changed)
        self.parameter_mode_picker.currentIndexChanged.connect(self._populate_parameters)
        self.parameter_search.textChanged.connect(self._filter_parameters)
        self.suggest_button.clicked.connect(self._request_smart_suggestion)
        self.advanced_button.toggled.connect(self._toggle_advanced)
        self.rescan_button.clicked.connect(self._refresh_from_daw)
        cancel.clicked.connect(self.reject)
        self.assign_button.clicked.connect(self._apply)
        self._refresh_from_daw()

    def showEvent(self, event):
        super().showEvent(event)
        if self.parentWidget() is not None:
            self.adjustSize()
            parent = self.parentWidget()
            self.move(parent.mapToGlobal(parent.rect().center()) - self.rect().center())

    @staticmethod
    def _add_field(grid: QGridLayout, row: int, label: str, picker: QComboBox) -> QLabel:
        text = QLabel(label)
        text.setObjectName("MacroFieldLabel")
        text.setWordWrap(True)
        text.setMinimumWidth(122)
        grid.addWidget(text, row, 0)
        grid.addWidget(picker, row, 1)
        return text

    def _available_buses(self) -> list[dict[str, Any]]:
        buses = self.snapshot.get("macroTargets", self.snapshot.get("buses", []))
        return [bus for bus in buses if isinstance(bus, dict)] if isinstance(buses, list) else []

    def _populate_targets(self) -> None:
        selected_bus = str(self.snapshot.get("targetId") or self.snapshot.get("busId") or "")
        selected_plugin = str(self.snapshot.get("pluginInstanceId") or "")
        self.bus_picker.blockSignals(True)
        self.bus_picker.clear()
        for bus in self._available_buses():
            scope = {"master": "MASTER", "track": "TRACK", "bus": "BUS"}.get(str(bus.get("scope") or "bus"), "BUS")
            self.bus_picker.addItem(f"{scope}  ·  {str(bus.get('name') or 'Chưa đặt tên')}", bus)
        self.bus_picker.blockSignals(False)
        for index in range(self.bus_picker.count()):
            bus = self.bus_picker.itemData(index)
            if isinstance(bus, dict) and str(bus.get("id") or "") == selected_bus:
                self.bus_picker.setCurrentIndex(index)
                break
        self._populate_plugins(selected_plugin)

    def _populate_plugins(self, selected_plugin: str = "") -> None:
        bus = self.bus_picker.currentData()
        plugins = bus.get("plugins", []) if isinstance(bus, dict) else []
        self.plugin_picker.blockSignals(True)
        self.plugin_picker.clear()
        for plugin in plugins:
            if isinstance(plugin, dict):
                suffix = " · Bypassed" if plugin.get("bypassed") else ""
                self.plugin_picker.addItem(str(plugin.get("name") or "Plug-in chưa đặt tên") + suffix, plugin)
        self.plugin_picker.blockSignals(False)
        for index in range(self.plugin_picker.count()):
            plugin = self.plugin_picker.itemData(index)
            if isinstance(plugin, dict) and str(plugin.get("instanceId") or "") == selected_plugin:
                self.plugin_picker.setCurrentIndex(index)
                break
        has_target = any(isinstance(bus.get("plugins"), list) and bus["plugins"] for bus in self._available_buses())
        self._set_setup_visibility(has_target)
        if self.plugin_picker.count() > 0:
            self._populate_parameters()
        elif has_target:
            self.function_picker.clear()
            self.assign_button.setEnabled(False)
            self.preview.setText("Đích này chưa có plug-in. Hãy chọn đích khác hoặc thêm plug-in trong StudioForge.")

    def _plugin_changed(self, _index: int = -1) -> None:
        self._smart_proposal = None
        self._parameter_cache = []
        self._all_parameter_count = 0
        self.parameter_mode_picker.blockSignals(True)
        self.parameter_mode_picker.setCurrentIndex(0)
        self.parameter_mode_picker.blockSignals(False)
        self.parameter_search.clear()
        self._populate_parameters()

    def _populate_parameters(self, _index: int = -1) -> None:
        self._smart_proposal = None
        target = self._selected_target()
        self.function_picker.blockSignals(True)
        self.function_picker.clear()
        if target is None:
            self.function_picker.blockSignals(False)
            self.assign_button.setEnabled(False)
            return
        bus, plugin = target
        recommended_only = self.parameter_mode_picker.currentData() != "all"
        getter = (self.surface.get_recommended_plugin_parameters if recommended_only
                  else self.surface.get_plugin_parameters)
        reply = getter(str(bus["id"]), int(plugin["slot"]), str(plugin["instanceId"]))
        parameters = reply.get("parameters", []) if isinstance(reply, dict) and reply.get("ok") else []
        self.function_picker.blockSignals(False)
        self._parameter_cache = [value for value in parameters if isinstance(value, dict)]
        self._all_parameter_count = int(reply.get("allParameterCount", len(self._parameter_cache))) if isinstance(reply, dict) else 0
        self.parameter_search.setVisible(not recommended_only)
        self._render_parameters()
        if self.function_picker.count() == 0:
            self.assign_button.setEnabled(False)
            if recommended_only and self._all_parameter_count:
                self.preview.setText("<b>Chưa có thông số chính đủ độ tin cậy.</b><br>"
                                     "Chọn “Tất cả thông số” để tìm thủ công; StudioForge sẽ vẫn kiểm tra an toàn trước khi gán.")
            else:
                self.preview.setText("<b>Plug-in này không công bố parameter an toàn để automation.</b>")
            return
        self._preview_mapping()

    def _filter_parameters(self, _text: str = "") -> None:
        self._smart_proposal = None
        self._render_parameters()

    def _render_parameters(self, _text: str = "") -> None:
        selected_id = ""
        current = self.function_picker.currentData()
        if isinstance(current, dict):
            selected_id = str(current.get("parameterId") or "")
        query = " ".join(self.parameter_search.text().lower().split())
        self.function_picker.blockSignals(True)
        self.function_picker.clear()
        visible = 0
        for parameter in self._parameter_cache:
            if (not parameter.get("stableIdentifier") or not parameter.get("automatable")
                    or parameter.get("readOnly") or not parameter.get("safeForMacro", True)):
                continue
            searchable = " ".join(str(parameter.get(key) or "") for key in
                                  ("name", "groupPath", "category", "role")).lower()
            if query and query not in searchable:
                continue
            group = str(parameter.get("groupPath") or parameter.get("category") or "")
            value = str(parameter.get("displayValue") or "")
            prefix = "★  " if parameter.get("recommended") else ""
            warning = "  ⚠" if int(parameter.get("dangerLevel") or 0) > 0 else ""
            label = prefix + ((group + " › ") if group else "") + str(parameter.get("name") or "Thông số")
            if value:
                label += f"  ({value})"
            self.function_picker.addItem(label + warning, parameter)
            visible += 1
        self.function_picker.blockSignals(False)
        for index in range(self.function_picker.count()):
            item = self.function_picker.itemData(index)
            if isinstance(item, dict) and str(item.get("parameterId") or "") == selected_id:
                self.function_picker.setCurrentIndex(index)
                break
        if self.parameter_mode_picker.currentData() == "all":
            self.parameter_count.setText(f"{visible}/{self._all_parameter_count}")
        else:
            self.parameter_count.setText(f"{visible} chính · {self._all_parameter_count} tổng")
        if self.function_picker.count() > 0:
            self._preview_mapping()

    def _set_setup_visibility(self, has_target: bool) -> None:
        for widget in (self.bus_picker, self.plugin_picker, self.function_picker,
                       self.suggest_button, self.assign_button, self.caption, *self.field_labels):
            widget.setVisible(has_target)
        self.parameter_mode_picker.setVisible(has_target)
        self.parameter_count.setVisible(has_target)
        self.advanced_button.setVisible(has_target)
        if not has_target:
            self.parameter_search.setVisible(False)
        self.mapping_options.setVisible(has_target and self.advanced_button.isChecked())
        if not has_target:
            self.assign_button.setEnabled(False)
            self.preview.setText(
                "<b>Chưa có hiệu ứng để gán núm.</b><br><br>"
                "Thêm plug-in vào Master, track/line hoặc bus trong StudioForge, sau đó quét lại."
            )
            self.rescan_button.setText("Quét lại")
            self.hint.setVisible(False)
        else:
            self.rescan_button.setText("↻  QUÉT LẠI")
            self.hint.setVisible(True)

    def _selected_target(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        bus, plugin = self.bus_picker.currentData(), self.plugin_picker.currentData()
        return (bus, plugin) if isinstance(bus, dict) and isinstance(plugin, dict) else None

    def _toggle_advanced(self, checked: bool) -> None:
        self.advanced_button.setText(("▾" if checked else "▸") + "  TINH CHỈNH PHẠM VI NÚM")
        self.mapping_options.setVisible(checked and self.bus_picker.isVisible())
        self.adjustSize()

    def _manual_parameter_changed(self, _index: int = -1) -> None:
        self._smart_proposal = None
        self._preview_mapping()

    def _preview_mapping(self) -> None:
        target = self._selected_target()
        parameter = self.function_picker.currentData()
        if target is None or not isinstance(parameter, dict):
            return
        if self.minimum_picker.value() > self.maximum_picker.value():
            self.preview.setText("<b>Khoảng điều khiển chưa hợp lệ.</b><br>Min phải nhỏ hơn hoặc bằng Max.")
            return
        bus, plugin = target
        bus_name, plugin_name = escape(str(bus.get("name") or "FX Bus")), escape(str(plugin.get("name") or "Plug-in"))
        function_name = escape(str(parameter.get("name") or "Thông số"))
        reason = escape(str(parameter.get("reason") or "Thông số automation do plug-in công bố."))
        category = escape(str(parameter.get("category") or "Other"))
        warning = "<br><span style='color:#f0bf69'>⚠ Nên giới hạn phạm vi để tránh thay đổi mức âm quá lớn.</span>" if int(parameter.get("dangerLevel") or 0) else ""
        self.preview.setText("<b>◉ &nbsp; Xem trước</b><br><br>"
                             f"Núm {self.macro_index + 1} sẽ điều khiển:<br>"
                             f"<span style='color:#f0bf69; font-weight:700'>{bus_name} &nbsp;•&nbsp; {plugin_name} &nbsp;•&nbsp; {function_name}</span><br>"
                             f"<small>{category} · {reason}</small>{warning}")
        self.assign_button.setEnabled(True)

    def _request_smart_suggestion(self) -> None:
        target = self._selected_target()
        if target is None:
            return
        bus, plugin = target
        reply = self.surface.preview_mapping(self.macro_index, str(bus["id"]), int(plugin["slot"]),
                                             str(plugin["instanceId"]))
        macro = reply.get("macro") if isinstance(reply, dict) and reply.get("ok") else None
        targets = macro.get("targets", []) if isinstance(macro, dict) else []
        if not targets:
            self._smart_proposal = None
            self.preview.setText("<b>Chưa đủ dữ liệu để tự đề xuất an toàn.</b><br>"
                                 "Hãy chọn một thông số chính hoặc mở danh sách đầy đủ.")
            return
        self._smart_proposal = macro
        names = " · ".join(escape(str(item.get("name") or "Thông số"))
                            for item in targets if isinstance(item, dict))
        confidence = int(round(float(macro.get("confidence") or 0.0) * 100.0))
        review = " · Cần xác nhận" if macro.get("needsReview") else ""
        self.preview.setText("<b>✦ &nbsp; ĐỀ XUẤT TỪ STUDIOFORGE</b><br><br>"
                             f"<span style='color:#72eee7; font-weight:700'>{names}</span><br>"
                             f"<small>Độ tin cậy {confidence}%{review}. Có thể gán nhiều thông số vào cùng một macro.</small>")
        self.assign_button.setEnabled(True)

    def _apply(self) -> None:
        target = self._selected_target()
        parameter = self.function_picker.currentData()
        if target is None or (self._smart_proposal is None and not isinstance(parameter, dict)):
            return
        if self.minimum_picker.value() > self.maximum_picker.value():
            self.preview.setText("<b>Khoảng điều khiển chưa hợp lệ.</b><br>Min phải nhỏ hơn hoặc bằng Max.")
            return
        bus, plugin = target
        if self._smart_proposal is not None:
            reply = self.surface.apply_mapping(self.macro_index, str(bus["id"]), int(plugin["slot"]),
                                               str(plugin["instanceId"]), True)
        else:
            reply = self.surface.apply_mapping(self.macro_index, str(bus["id"]), int(plugin["slot"]),
                                               str(plugin["instanceId"]), True,
                                               parameter_id=str(parameter.get("parameterId") or ""),
                                               minimum=self.minimum_picker.value(), maximum=self.maximum_picker.value(),
                                               curve=int(self.curve_picker.currentData() or 0),
                                               invert=self.invert_picker.isChecked(),
                                               smoothing_ms=float(self.smoothing_picker.value()))
        if isinstance(reply, dict) and reply.get("ok"):
            self.accept()
        else:
            self.preview.setText("<b>StudioForge không thể gán núm này.</b><br>Hãy bấm Quét lại để đồng bộ project rồi thử lại.")

    def _refresh_from_daw(self) -> None:
        state = self.surface.poll_state()
        if not isinstance(state, dict):
            diagnostic = str(getattr(self.surface, "last_error", "") or "").strip()
            detail = f"<br><br><small>{escape(diagnostic)}</small>" if diagnostic else ""
            self.connection_badge.setText("!  KHÔNG THỂ KẾT NỐI STUDIOFORGE")
            self.connection_badge.setStyleSheet("color:#ffb1a6; background:#301918; border:1px solid #92524c; border-radius:13px; padding:5px 11px; font-size:10px; font-weight:800;")
            self._set_setup_visibility(False)
            self.preview.setText("<b>Chưa kết nối được StudioForge.</b><br><br>"
                                 "Kiểm tra DAW rồi bấm Quét lại." + detail)
            return
        self.connection_badge.setText("⌁  STUDIOFORGE ĐÃ KẾT NỐI")
        self.connection_badge.setStyleSheet("")
        # The DAW may omit unassigned slots or publish snapshots in another
        # order. macroId, not array position, is the hardware slot identity.
        macro = macro_at(state, self.macro_index) or {}
        self.snapshot = dict(macro) if isinstance(macro, dict) else {}
        self.snapshot["buses"] = state.get("buses", [])
        self.snapshot["macroTargets"] = state.get("macroTargets", state.get("buses", []))
        self._populate_targets()
