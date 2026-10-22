import tempfile
import unittest
from pathlib import Path

from core.constants import MODE_PRESETS
from core.services.control_surface_service import ControlSurfaceService
from core.services.mode_settings_service import ModeSettingsService


class _MidiSpy:
    def __init__(self):
        self.messages = []

    def send_cc(self, controller, value):
        self.messages.append((controller, value))


class ModePresetTests(unittest.TestCase):
    def test_every_visible_atomic_mode_has_a_real_preset_or_action(self):
        self.assertTrue({"natural", "nhac_tre", "bolero", "remix", "rnb"}.issubset(MODE_PRESETS))

    def test_new_modes_apply_through_existing_control_service(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings = ModeSettingsService(Path(temporary) / "modes.json")
            midi = _MidiSpy()
            controls = ControlSurfaceService(midi, settings)
            for mode in ("natural", "rnb"):
                preset = controls.apply_mode(mode)
                self.assertEqual(controls.current_mode, mode)
                self.assertEqual(preset, MODE_PRESETS[mode])
            # Five existing MIDI-backed values are emitted per preset.
            self.assertEqual(len(midi.messages), 10)

    def test_mode_name_and_stable_macro_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings = ModeSettingsService(Path(temporary) / "modes.json")
            self.assertEqual(settings.set_mode_label("nhac_tre", "  Live   Pop  "), "Live Pop")
            snapshot = {"macros": [{
                "macroId": 2, "state": 2, "targetId": "track:17", "pluginSlot": 1,
                "pluginInstanceId": "track:17:1:pro-q", "targets": [{
                    "parameterId": "gain3", "minimum": .2, "maximum": .8,
                    "curve": 3, "invert": True, "smoothingMs": 28.0,
                }],
            }]}
            saved = settings.save_mode_macro_profile("nhac_tre", snapshot)
            self.assertEqual(saved[0]["targetId"], "track:17")
            self.assertEqual(saved[0]["targets"][0]["parameterId"], "gain3")
            self.assertEqual(settings.get_mode_label("nhac_tre"), "Live Pop")
            self.assertEqual(settings.get_mode_macro_profile("nhac_tre"), saved)

