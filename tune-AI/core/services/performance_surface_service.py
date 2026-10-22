"""Local-only client for StudioForge Adaptive Performance Macros.

The DAW owns every macro assignment and parameter value.  This service only
reads the short-lived local-socket configuration published by the DAW, then
sends semantic JSON commands. It never moves audio through Python.
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
from pathlib import Path
from typing import Any


class PerformanceSurfaceService:
    CONFIG_NAME = "studioforge-performance-surface.json"
    MAX_MESSAGE_BYTES = 64 * 1024

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._project_revision = ""
        self._last_error = ""

    @property
    def connected(self) -> bool:
        return bool(self._config.get("token") and
                    (self._config.get("socketPath") or self._config.get("loopbackPort")))

    @property
    def project_revision(self) -> str:
        return self._project_revision

    @property
    def last_error(self) -> str:
        """A concise local-transport diagnostic for the setup UI."""
        return self._last_error

    def refresh_configuration(self) -> bool:
        # The DAW and packaged Python panel are separate macOS processes.  A
        # per-process tempfile directory can differ between them, so their
        # shared discovery file has one explicit local location.  Keep the
        # legacy tempfile lookup as a migration fallback for panels/DAWs from
        # a previous release.
        locations = [Path("/tmp") / self.CONFIG_NAME]
        legacy = Path(tempfile.gettempdir()) / self.CONFIG_NAME
        if legacy not in locations:
            locations.append(legacy)

        for path in locations:
            try:
                if path.stat().st_mode & 0o077:
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                loopback_port = data.get("loopbackPort")
                has_unix = isinstance(data.get("socketPath"), str) and bool(data.get("socketPath"))
                has_loopback = isinstance(loopback_port, int) and 1 <= loopback_port <= 65535
                if (data.get("schema") != 1 or data.get("transport") != "unix"
                        or not isinstance(data.get("token"), str)
                        or not (has_unix or has_loopback)):
                    continue
                self._config = data
                self._last_error = ""
                return True
            except (OSError, ValueError, TypeError) as error:
                self._last_error = f"Không đọc được cấu hình StudioForge: {error}"
                continue

        self._config = {}
        if not self._last_error:
            self._last_error = "DAW chưa công bố kênh điều khiển cục bộ."
        return False

    def poll_state(self) -> dict[str, Any] | None:
        if not self.connected and not self.refresh_configuration():
            return None
        response = self._request({"command": "getState"}, mutating=False)
        if response and response.get("type") == "performanceMacroState":
            self._project_revision = str(response.get("projectRevision", ""))
            return response
        return None

    def poll_audio_analysis(self) -> dict[str, Any] | None:
        """Read one lightweight DAW analyzer frame.

        Macro/plug-in inventory stays on the slower control poll. Keeping this
        response small allows a smooth display cadence without moving PCM or
        blocking on a full project snapshot.
        """
        response = self._request({"command": "getAudioAnalysis"}, mutating=False)
        if response and response.get("type") == "audioAnalysisFrame":
            analysis = response.get("audioAnalysis")
            return analysis if isinstance(analysis, dict) else None
        return None

    def toggle_transport(self) -> dict[str, Any] | None:
        """Toggle the paired DAW transport without changing project content."""
        return self._request({"command": "toggleTransport"}, mutating=False)

    def preview_mapping(self, macro_id: int, bus_id: str, plugin_slot: int,
                        plugin_instance_id: str) -> dict[str, Any] | None:
        return self._request({
            "command": "previewMacroMapping", "macroId": int(macro_id),
            "targetId": str(bus_id), "busId": str(bus_id), "pluginSlot": int(plugin_slot),
            "pluginInstanceId": str(plugin_instance_id),
        })

    def get_plugin_parameters(self, bus_id: str, plugin_slot: int,
                              plugin_instance_id: str) -> dict[str, Any] | None:
        return self._get_parameter_pages("getPluginParameters", bus_id, plugin_slot,
                                         plugin_instance_id)

    def get_recommended_plugin_parameters(self, bus_id: str, plugin_slot: int,
                                          plugin_instance_id: str) -> dict[str, Any] | None:
        """Fetch only DAW-ranked performer controls; the full list stays lazy."""
        return self._get_parameter_pages("getRecommendedPluginParameters", bus_id,
                                         plugin_slot, plugin_instance_id)

    def _get_parameter_pages(self, command: str, bus_id: str, plugin_slot: int,
                             plugin_instance_id: str) -> dict[str, Any] | None:
        # Large EQs can expose hundreds of parameters; a single JSON reply can
        # exceed the transport's bounded response size. Never silently return
        # a partial list if the project changes while pages are being read.
        revision = self._project_revision
        offset = 0
        parameters: list[Any] = []
        expected_total: int | None = None
        while True:
            reply = self._request({
                "command": command, "busId": str(bus_id),
                "pluginSlot": int(plugin_slot), "pluginInstanceId": str(plugin_instance_id),
                "offset": offset, "limit": 100,
            })
            if not reply or not reply.get("ok"):
                return reply
            page = reply.get("parameters")
            if not isinstance(page, list) or self._project_revision != revision:
                self._last_error = "Danh sách tham số đã thay đổi; hãy quét lại."
                return None
            parameters.extend(page)
            # Compatibility with DAWs predating pagination.
            if "nextOffset" not in reply:
                reply["parameters"] = parameters
                return reply
            total, next_offset = reply.get("total"), reply.get("nextOffset")
            if (not isinstance(total, int) or not isinstance(next_offset, int)
                    or total < 0 or (expected_total is not None and total != expected_total)
                    or len(parameters) > total):
                self._last_error = "DAW trả về danh sách tham số không hợp lệ."
                return None
            expected_total = total
            if next_offset == -1 and len(parameters) == total:
                reply["parameters"] = parameters
                return reply
            if next_offset != offset + len(page) or not page or next_offset >= total:
                self._last_error = "DAW trả về trang tham số không hợp lệ."
                return None
            offset = next_offset

    def get_eq_surface(self, bus_id: str, plugin_slot: int,
                       plugin_instance_id: str) -> dict[str, Any] | None:
        """Return a DAW-verified EQ band descriptor, never guessed from UI text."""
        return self._request({
            "command": "getEqSurface", "busId": str(bus_id),
            "pluginSlot": int(plugin_slot), "pluginInstanceId": str(plugin_instance_id),
        })

    def get_plugin_parameter(self, bus_id: str, plugin_slot: int,
                             plugin_instance_id: str, parameter_id: str) -> dict[str, Any] | None:
        """Read one current DAW-owned parameter, without transferring the full list."""
        return self._request({"command": "getPluginParameter", "busId": str(bus_id),
                              "pluginSlot": int(plugin_slot), "pluginInstanceId": str(plugin_instance_id),
                              "parameterId": str(parameter_id)})

    def set_eq_parameter(self, bus_id: str, plugin_slot: int,
                         plugin_instance_id: str, parameter_id: str,
                         normalized_value: float) -> dict[str, Any] | None:
        """Control one DAW-confirmed automatable EQ parameter.

        The DAW validates bus, slot, plug-in instance and parameter identity
        again; Python never addresses a parameter by a display name.
        """
        return self._request({
            "command": "setEqParameter", "busId": str(bus_id),
            "pluginSlot": int(plugin_slot), "pluginInstanceId": str(plugin_instance_id),
            "parameterId": str(parameter_id),
            "value": max(0.0, min(1.0, float(normalized_value))),
        })

    def set_analysis_source(self, kind: str, source_id: str) -> dict[str, Any] | None:
        """Select a DAW-owned display tap; PCM never crosses this control call."""
        return self._request({"command": "setAudioAnalysisSource",
                              "sourceKind": str(kind), "sourceId": str(source_id)})

    def apply_detected_key(self, key: str, scale: str, confidence: float,
                           title: str = "") -> dict[str, Any] | None:
        """Ask the DAW to apply key/scale to every compatible pitch corrector.

        This is intentionally one semantic command rather than two guessed
        parameter writes. StudioForge validates the project revision, discovers
        user-loaded Auto-Tune/Vibe/Waves Tune Real-Time instances,
        resolves their stable root and scale identifiers, performs both writes,
        then reports every track and plug-in that actually accepted the result.
        """
        if not self._project_revision and self.poll_state() is None:
            return None
        return self._request({
            "command": "applyDetectedKey",
            "key": str(key or "").strip(),
            "scale": str(scale or "").strip(),
            "confidence": max(0.0, min(1.0, float(confidence))),
            "title": str(title or "").strip(),
        })

    def apply_mapping(self, macro_id: int, bus_id: str, plugin_slot: int,
                      plugin_instance_id: str, confirm_needs_review: bool,
                      parameter_id: str = "", minimum: float = 0.0, maximum: float = 1.0,
                      curve: int = 0, invert: bool = False, smoothing_ms: float = 15.0) -> dict[str, Any] | None:
        payload = {
            "command": "applyMacroMapping", "macroId": int(macro_id),
            "targetId": str(bus_id), "busId": str(bus_id), "pluginSlot": int(plugin_slot),
            "pluginInstanceId": str(plugin_instance_id),
            "confirmNeedsReview": bool(confirm_needs_review),
        }
        if parameter_id:
            payload.update({"parameterId": str(parameter_id), "minNormalized": float(minimum),
                            "maxNormalized": float(maximum), "invert": bool(invert),
                            "curve": int(curve), "smoothingMs": float(smoothing_ms)})
        return self._request(payload)

    def clear_mapping(self, macro_id: int) -> dict[str, Any] | None:
        return self._request({"command": "clearMacroMapping", "macroId": int(macro_id)})

    def set_value(self, macro_id: int, value: float) -> dict[str, Any] | None:
        return self._request({"command": "setMacroValue", "macroId": int(macro_id),
                              "value": max(0.0, min(1.0, float(value)))})

    def _request(self, payload: dict[str, Any], mutating: bool = True) -> dict[str, Any] | None:
        if not self.connected and not self.refresh_configuration():
            return None
        if mutating and not self._project_revision:
            return None
        payload["token"] = self._config["token"]
        if mutating:
            payload["projectRevision"] = self._project_revision
        errors: list[str] = []
        # A connection can succeed yet the first I/O can still be denied by a
        # packaged macOS process. Retry the *entire* exchange over the other
        # DAW-published local transport instead of treating connect() as proof.
        for transport, connection in self._local_transports():
            try:
                with connection:
                    connection.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
                    chunks: list[bytes] = []
                    size = 0
                    while size < self.MAX_MESSAGE_BYTES:
                        part = connection.recv(min(4096, self.MAX_MESSAGE_BYTES - size))
                        if not part:
                            break
                        chunks.append(part)
                        size += len(part)
                        if b"\n" in part:
                            break
                result = json.loads(b"".join(chunks).split(b"\n", 1)[0].decode("utf-8"))
                if isinstance(result, dict):
                    revision = result.get("projectRevision")
                    if revision is not None:
                        self._project_revision = str(revision)
                    self._last_error = ""
                    return result
                errors.append(f"{transport}: phản hồi không hợp lệ")
            except (OSError, ValueError, TypeError, KeyError) as error:
                errors.append(f"{transport}: {error}")
        self._last_error = " ; ".join(errors) or "DAW không phản hồi kênh điều khiển."
        return None

    def _local_transports(self):
        """Yield every usable local endpoint, with loopback first on macOS."""
        port = self._config.get("loopbackPort")
        if isinstance(port, int) and 1 <= port <= 65535:
            try:
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                connection.settimeout(1.5)
                connection.connect(("127.0.0.1", port))
                yield "loopback", connection
            except OSError as error:
                yield "loopback", _FailedConnection(error)

        socket_path = self._config.get("socketPath")
        if isinstance(socket_path, str) and socket_path:
            try:
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.settimeout(1.5)
                connection.connect(socket_path)
                yield "unix", connection
            except OSError as error:
                yield "unix", _FailedConnection(error)


class _FailedConnection:
    """Defers endpoint-open errors so both transports are attempted."""

    def __init__(self, error: OSError) -> None:
        self._error = error

    def __enter__(self):
        raise self._error

    def __exit__(self, *_args) -> bool:
        return False
