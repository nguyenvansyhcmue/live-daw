import os
import unittest
from unittest.mock import patch

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from ui.atomic_surface import AtomicSurface, TactileButton
from ui.performance_macro_dialog import PerformanceMacroDialog
from ui.autokey_visual_tokens import (CHASSIS_SCREWS, EQ_CONTROL_POCKET,
                                      EQ_GRAPH, EQ_SECTION, HEADER, KEY_DISPLAY,
                                      MACRO_CENTERS, MACRO_DIAMETER, MACRO_GROOVES,
                                      MAPPING,
                                      OUTPUT_METER, OUTPUT_MODULE, TONE_SHIFT,
                                      REFERENCE_HEIGHT, REFERENCE_WIDTH)
from ui.main_window import MainWindow


class AtomicSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_atomic_assets_and_six_independent_macro_slots(self):
        view = AtomicSurface()
        view.resize(1080, 810)
        view.show()
        self.app.processEvents()
        # This is the clean Blender chassis only; all data-bearing controls
        # remain live widgets/paint layers above it.
        self.assertFalse(view._background.isNull())
        self.assertEqual(view._background.width(), REFERENCE_WIDTH * 2)
        self.assertEqual(view._background.height(), REFERENCE_HEIGHT * 2)
        self.assertFalse(view._grid.isNull())
        self.assertEqual(len(view.knobs), 6)
        self.assertTrue(all(not knob.isEnabled() for knob in view.knobs))
        self.assertTrue(all(not pixmap.isNull() for knob in view.knobs for pixmap in knob._assets))
        view.set_snapshot({"macros": [{"macroId": 5, "state": 2, "value": .75,
                                      "macroName": "Mix", "targets": [{"valueText": "75 %"}]}],
                           "audioAnalysis": {"sourceName": "Vocal Bus Post-FX"},
                           "analysisSources": [{"kind": "master", "id": "master",
                                                "name": "Master Post-FX"},
                                               {"kind": "bus", "id": "7",
                                                "name": "Vocal Bus Post-FX"}]})
        self.assertTrue(view.knobs[5].isEnabled())
        self.assertEqual(view.knobs[5].value(), 750)
        self.assertEqual(view.knobs[5]._text, "75 %")
        self.assertFalse(view.knobs[0].isEnabled())
        self.assertEqual(view._analysis_source_name, "Vocal Bus Post-FX")
        self.assertEqual(len(view._analysis_sources), 2)
        view.set_active_mode("nhac_tre")
        self.assertTrue(view._mode_buttons["nhac_tre"].property("selected"))
        self.assertFalse(view._mode_buttons["natural"].property("selected"))
        self.assertTrue(view._mode_buttons["natural"].isEnabled())
        self.assertTrue(view._mode_buttons["rnb"].isEnabled())
        view.set_spectrum(np.linspace(0, 1, 72, dtype=np.float32))
        self.assertEqual(len(view._spectrum), 72)
        view.set_waveform([0.0] * 96)
        view.set_waveform([1.0] * 96)
        view._advance_analysis_animation()
        self.assertGreater(view._waveform[0], 0.0)
        self.assertLess(view._waveform[0], 1.0)
        view.set_eq_surface({"capability": "eq_interactive",
                             "parameterModel": {"frequencyMinHz": 10, "frequencyMaxHz": 30000,
                                                "gainMinDb": -30, "gainMaxDb": 30},
                             "bands": [{"bandId": "band:1", "index": 1,
                                        "used": {"parameterId": "used1", "normalizedValue": 1},
                                        "enabled": {"normalizedValue": 1},
                                        "frequency": {"parameterId": "f", "normalizedValue": .5},
                                        "gain": {"parameterId": "g", "normalizedValue": .5},
                                        "q": {"parameterId": "q", "normalizedValue": .3,
                                              "displayValue": "1.00"}},
                                       {"bandId": "band:2", "index": 2,
                                        "used": {"parameterId": "used2", "normalizedValue": 0},
                                        "enabled": {"parameterId": "enabled2", "normalizedValue": 0},
                                        "frequency": {"parameterId": "f2", "normalizedValue": .5},
                                        "gain": {"parameterId": "g2", "normalizedValue": .5},
                                        "q": {"parameterId": "q2", "normalizedValue": .3,
                                              "displayValue": "1.00"}}]})
        self.assertEqual(len(view._eq_nodes()), 1)
        self.assertEqual(view._eq_button.text(), "EQ ON")
        x, y = view._eq_node_position(view._eq_nodes()[0][1], view._eq_nodes()[0][2])
        self.assertAlmostEqual(x, EQ_GRAPH.x + EQ_GRAPH.width *
                               (np.log(547.7225575 / 20) / np.log(1000)), places=2)
        self.assertEqual(y, EQ_GRAPH.y + EQ_GRAPH.height / 2)
        writes = []
        view.eqParameterChanged.connect(lambda parameter, value: writes.append((parameter, value)))
        view._eq_drag = view._eq_nodes()[0]
        view._emit_eq_drag_values(force=True)
        self.assertEqual([item[0] for item in writes], ["f", "g"])
        self.assertTrue(view.eq_gesture_active)
        view._eq_drag = None
        writes.clear()
        self.assertTrue(view._create_eq_band((EQ_GRAPH.x + 100, EQ_GRAPH.y + 100)))
        self.assertEqual([item[0] for item in writes], ["used2", "enabled2", "f2", "g2"])
        self.assertEqual(len(view._eq_nodes()), 2)
        view._eq_drag = None
        view.set_snapshot(None)
        self.assertFalse(view.knobs[5].isEnabled())
        view.close()

    def test_reference_geometry_and_idle_state_are_truthful(self):
        view = AtomicSurface()
        view.resize(REFERENCE_WIDTH, REFERENCE_HEIGHT)
        view.show()
        self.app.processEvents()
        self.assertEqual(view._preset_name, "—")
        self.assertEqual(view._spectrum, ())
        self.assertEqual(view._waveform, ())
        self.assertEqual(view._eq_button.text(), "EQ OFF")
        for knob, (center_x, center_y) in zip(view.knobs, MACRO_CENTERS):
            self.assertEqual(knob.width(), MACRO_DIAMETER)
            self.assertEqual(knob.height(), MACRO_DIAMETER)
            self.assertEqual(knob.x() + knob.width() / 2, center_x)
            self.assertEqual(knob.y() + knob.height() / 2, center_y)
        view.resize(REFERENCE_WIDTH * 2, REFERENCE_HEIGHT * 2)
        self.app.processEvents()
        self.assertEqual(view.knobs[0].width(), MACRO_DIAMETER * 2)
        self.assertEqual(view.knobs[0].height(), MACRO_DIAMETER * 2)
        self.assertEqual((EQ_GRAPH.x, EQ_GRAPH.y, EQ_GRAPH.width, EQ_GRAPH.height),
                         (75, 185, 770, 460))
        self.assertEqual(HEADER.tuple(), (36, 22, 1336, 70))
        self.assertEqual(KEY_DISPLAY.tuple(), (935, 135, 300, 255))
        self.assertEqual(OUTPUT_MODULE.tuple(), (1255, 135, 110, 255))
        self.assertEqual(OUTPUT_METER.tuple(), (1272, 184, 76, 164))
        self.assertEqual(TONE_SHIFT.tuple(), (920, 404, 445, 116))
        self.assertGreaterEqual(MACRO_CENTERS[0][1] - MACRO_DIAMETER / 2, 810)
        self.assertEqual(MAPPING.tuple(), (642, 800, 124, 145))
        self.assertEqual(MACRO_CENTERS[:3], ((105, 864), (285, 864), (465, 864)))
        self.assertEqual(MACRO_CENTERS[3:], ((943, 864), (1123, 864), (1303, 864)))
        self.assertEqual(MACRO_GROOVES, (195, 375, 554, 854, 1033, 1213))
        self.assertGreaterEqual(EQ_GRAPH.x - 68, 7)  # dedicated dB-label gutter
        self.assertGreaterEqual(EQ_GRAPH.y - EQ_SECTION.y, 50)
        self.assertGreaterEqual(HEADER.y, 20)
        self.assertEqual(CHASSIS_SCREWS,
                         ((22, 26, .18), (1386, 26, .72),
                          (22, 978, 1.30), (1386, 978, .68)))
        view.close()

    def test_hardware_controls_expose_tactile_and_precision_interaction(self):
        view = AtomicSurface()
        view.set_snapshot({"macros": [{"macroId": 0, "state": 2, "value": .5,
                                        "macroName": "Tightness", "busName": "Vocal 1",
                                        "pluginName": "Pro-Q 3", "targets": []}]})
        knob = view.knobs[0]
        self.assertTrue(knob.isEnabled())
        self.assertEqual(knob.singleStep(), 5)
        self.assertEqual(knob.pageStep(), 50)
        self.assertEqual(knob.cursor().shape(), Qt.CursorShape.SizeVerCursor)
        self.assertIn("Shift: tinh chỉnh", knob.toolTip())
        self.assertIn("Alt: siêu mịn", knob.toolTip())

        button = view._mode_buttons["natural"]
        self.assertIsInstance(button, TactileButton)
        self.assertEqual(button.cursor().shape(), Qt.CursorShape.PointingHandCursor)
        button._set_press_depth(9)
        self.assertAlmostEqual(button._press_depth, 1.65)
        button._set_press_depth(-9)
        self.assertAlmostEqual(button._press_depth, -.22)
        view.close()

    def test_new_surface_controls_emit_their_product_actions(self):
        view = AtomicSurface()
        emitted = []
        view.karaokeRequested.connect(lambda: emitted.append("karaoke"))
        view.songListRequested.connect(lambda: emitted.append("library"))
        view.contactRequested.connect(lambda: emitted.append("contact"))
        view.settingsRequested.connect(lambda: emitted.append("settings"))
        view.saveRequested.connect(lambda: emitted.append("save"))
        view.micToggleRequested.connect(lambda: emitted.append("mic"))
        view.closeRequested.connect(lambda: emitted.append("close"))
        view.eqControlRequested.connect(lambda: emitted.append("eq"))
        view.modeProfileRequested.connect(lambda: emitted.append("profile"))
        view.modeRequested.connect(lambda mode: emitted.append(f"mode:{mode}"))
        view.toneShiftRequested.connect(lambda amount: emitted.append(f"shift:{amount}"))
        view.modeStepRequested.connect(lambda amount: emitted.append(f"step:{amount}"))
        view.toneInputSourceRequested.connect(lambda source: emitted.append(f"source:{source}"))

        for key in ("karaoke", "library", "contact", "settings"):
            view._utility_buttons[key].click()
        view._save_button.click()
        view._mic_button.click()
        view._power_button.click()
        view._eq_button.click()
        view._mode_profile_button.click()
        view._mode_buttons["rnb"].click()
        view._tone_minus_button.click()
        view._tone_plus_button.click()
        view._mode_previous_button.click()
        view._mode_next_button.click()
        view._tone_source_buttons["microphone"].click()
        self.assertEqual(emitted, ["karaoke", "library", "contact", "settings", "save",
                                   "mic", "close", "eq", "profile", "mode:rnb",
                                   "shift:-1", "shift:1", "step:-1", "step:1",
                                   "source:microphone"])
        self.assertTrue(view._mic_button.isChecked())
        view.close()

    def test_macro_rescan_uses_stable_macro_id_instead_of_array_position(self):
        class Surface:
            last_error = ""

            @staticmethod
            def poll_state():
                return {"macros": [{"macroId": 5, "macroName": "Six"},
                                    {"macroId": 0, "macroName": "One"}],
                        "buses": [], "macroTargets": []}

        dialog = PerformanceMacroDialog(0, {}, Surface())
        self.assertEqual(dialog.snapshot.get("macroId"), 0)
        self.assertEqual(dialog.snapshot.get("macroName"), "One")
        dialog.close()

    def test_existing_main_window_hosts_surface_and_can_return_to_legacy(self):
        methods = ("_apply_theme", "_startup", "_load_default_singing_mode_on_startup",
                   "_update_transposed_tone_label", "_start_external_browser_auto_detect",
                   "_start_live_audio_after_consent", "_load_saved_end_modulation_for_current_video")
        patches = [patch.object(MainWindow, name) for name in methods]
        for item in patches:
            item.start()
        try:
            window = MainWindow(object())
            self.app.processEvents()
            self.assertFalse(bool(window.windowFlags() & Qt.WindowType.FramelessWindowHint))
            self.assertTrue(bool(window.windowFlags() & Qt.WindowType.WindowCloseButtonHint))
            self.assertTrue(bool(window.windowFlags() & Qt.WindowType.WindowMinMaxButtonsHint))
            self.assertTrue(window._atomic_surface.isVisible())
            for signal in (window._atomic_surface.mappingRequested,
                           window._atomic_surface.eqControlRequested,
                           window._atomic_surface.eqParameterChanged,
                           window._atomic_surface.analysisSourceRequested,
                           window._atomic_surface.macroChanged,
                           window._atomic_surface.toneShiftRequested,
                           window._atomic_surface.modeRequested,
                           window._atomic_surface.modeProfileRequested,
                           window._atomic_surface.modeStepRequested,
                           window._atomic_surface.karaokeRequested,
                           window._atomic_surface.songListRequested,
                           window._atomic_surface.contactRequested,
                           window._atomic_surface.settingsRequested,
                           window._atomic_surface.micToggleRequested,
                           window._atomic_surface.closeRequested,
                           window._atomic_surface.saveRequested):
                self.assertGreater(window._atomic_surface.receivers(signal), 0)
            window._show_legacy_surface()
            self.assertFalse(window._atomic_surface.isVisible())
            self.assertTrue(window._atomic_return_button.isVisible())
            window._show_atomic_surface()
            self.assertTrue(window._atomic_surface.isVisible())
            window.external_last_video_id = ""
            window._handle_external_browser_tone_result({
                "video_id": "abcdefghijk", "url": "https://www.youtube.com/watch?v=abcdefghijk",
                "title": "Test", "error": "temporary YouTube failure",
            })
            self.assertEqual(window.external_last_video_id, "")
            self.assertEqual(window.external_detect_retry_video_id, "abcdefghijk")
            self.assertGreater(window.external_detect_retry_after, 0)
            self.assertEqual(window._atomic_surface._tone, "Chưa dò được — đang thử lại")
            window.performance_surface_timer.stop()
            window.shutdown_services()
            window.hide()
            window.deleteLater()
            self.app.processEvents()
        finally:
            for item in reversed(patches):
                item.stop()
