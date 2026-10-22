import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication, QDialog

from ui.eq_parameter_dialog import EqParameterDialog


class FakeSurface:
    last_error = ""

    def __init__(self):
        self.calls = []

    def get_eq_surface(self, bus_id, slot, instance_id):
        return {"ok": True, "capability": "eq_interactive", "bands": [],
                "busId": bus_id, "pluginSlot": slot,
                "pluginInstanceId": instance_id, "pluginName": "Pro-Q 3",
                "parameterModel": {"family": "test"}}

    def set_analysis_source(self, *args):
        self.calls.append(args)
        return {"ok": True}


class EqParameterDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selector_exposes_no_raw_parameter_setup(self):
        surface = FakeSurface()
        snapshot = {"eqTargets": [{
            "id": "track:17", "scope": "track", "name": "Vocal",
            "plugins": [{"slot": 2, "name": "Pro-Q 3", "instanceId": "instance-2"}],
        }]}
        dialog = EqParameterDialog(snapshot, surface)
        self.assertEqual(dialog.eq_descriptor["capability"], "eq_interactive")
        self.assertFalse(hasattr(dialog, "parameter"))
        self.assertFalse(hasattr(dialog, "slider"))
        dialog._activate()
        self.assertEqual(surface.calls, [("track", "17")])
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        dialog.close()

    def test_missing_target_cannot_activate(self):
        surface = FakeSurface()
        dialog = EqParameterDialog({}, surface)
        self.assertFalse(dialog.activate_button.isEnabled())
        dialog._activate()
        self.assertEqual(surface.calls, [])
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)
        dialog.close()


if __name__ == "__main__":
    unittest.main()
