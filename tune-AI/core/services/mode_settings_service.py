import json
import sys
from copy import deepcopy
from pathlib import Path
from core.constants import DATA_DIR, MODE_PRESETS


DEFAULT_MODE_LABELS = {
    "natural": "Natural", "lofi": "Lofi", "nhac_tre": "Pop",
    "bolero": "Bolero", "rnb": "R&B", "remix": "Remix",
}


class ModeSettingsService:
    def __init__(self, file_path=None):
        if file_path is not None:
            self.file_path = Path(file_path)
        elif sys.platform == "darwin":
            self.file_path = (Path.home() / "Library" / "Application Support" /
                              "THM Vocal Panel" / "mode_settings.json")
        else:
            self.file_path = DATA_DIR / "mode_settings.json"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.file_path.exists():
            legacy_path = DATA_DIR / "mode_settings.json"
            try:
                legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                legacy = deepcopy(MODE_PRESETS)
            self._write_json(legacy if isinstance(legacy, dict) else deepcopy(MODE_PRESETS))

    def _read_json(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return deepcopy(MODE_PRESETS)

    def _write_json(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all_modes(self):
        data = self._read_json()
        for mode_name, defaults in MODE_PRESETS.items():
            if mode_name not in data:
                data[mode_name] = deepcopy(defaults)
        return data

    def get_mode(self, mode_name: str):
        data = self.get_all_modes()
        if mode_name not in data:
            data[mode_name] = deepcopy(MODE_PRESETS.get(mode_name, {}))
            self._write_json(data)
        return data[mode_name]

    def update_mode_value(self, mode_name: str, field: str, value):
        data = self.get_all_modes()
        if mode_name not in data:
            data[mode_name] = deepcopy(MODE_PRESETS.get(mode_name, {}))
        data[mode_name][field] = value
        self._write_json(data)

    def set_mode_values(self, mode_name: str, values: dict):
        data = self.get_all_modes()
        data[mode_name] = values
        self._write_json(data)

    def get_mode_label(self, mode_name: str) -> str:
        mode = self.get_mode(mode_name)
        label = str(mode.get("_display_name") or DEFAULT_MODE_LABELS.get(mode_name, mode_name))
        return label.strip()[:24] or DEFAULT_MODE_LABELS.get(mode_name, "Mode")

    def set_mode_label(self, mode_name: str, label: str) -> str:
        clean = " ".join(str(label or "").split())[:24]
        if not clean:
            clean = DEFAULT_MODE_LABELS.get(mode_name, "Mode")
        self.update_mode_value(mode_name, "_display_name", clean)
        return clean

    @staticmethod
    def macro_profile_from_snapshot(snapshot: dict) -> list[dict]:
        """Keep only stable DAW identities required to rebuild each mapping."""
        result = []
        macros = snapshot.get("macros", []) if isinstance(snapshot, dict) else []
        for macro in macros if isinstance(macros, list) else []:
            if not isinstance(macro, dict):
                continue
            target_id = str(macro.get("targetId") or macro.get("busId") or "").strip()
            plugin_id = str(macro.get("pluginInstanceId") or "").strip()
            try:
                macro_id, plugin_slot = int(macro.get("macroId")), int(macro.get("pluginSlot"))
            except (TypeError, ValueError):
                continue
            if not (0 <= macro_id < 6 and target_id and plugin_id and plugin_slot >= 0):
                continue
            targets = macro.get("targets", [])
            safe_targets = []
            for target in targets if isinstance(targets, list) else []:
                if not isinstance(target, dict) or not target.get("parameterId"):
                    continue
                safe_targets.append({
                    "parameterId": str(target["parameterId"]),
                    "minimum": float(target.get("minimum", 0.0)),
                    "maximum": float(target.get("maximum", 1.0)),
                    "curve": int(target.get("curve", 0)),
                    "invert": bool(target.get("invert", False)),
                    "smoothingMs": float(target.get("smoothingMs", 15.0)),
                })
            result.append({
                "macroId": macro_id,
                "targetId": target_id,
                "pluginSlot": plugin_slot,
                "pluginInstanceId": plugin_id,
                "targets": safe_targets,
            })
        return result

    def save_mode_macro_profile(self, mode_name: str, snapshot: dict) -> list[dict]:
        profile = self.macro_profile_from_snapshot(snapshot)
        self.update_mode_value(mode_name, "_macro_profile", profile)
        return profile

    def get_mode_macro_profile(self, mode_name: str) -> list[dict]:
        value = self.get_mode(mode_name).get("_macro_profile", [])
        return deepcopy(value) if isinstance(value, list) else []
