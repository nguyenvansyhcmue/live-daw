import unittest

from ui.macro_surface_state import macro_at, macro_is_assigned, macro_value_text


class MacroSurfaceStateTests(unittest.TestCase):
    def test_lookup_uses_stable_slot_id_not_array_position(self):
        snapshot = {"macros": [{"macroId": 5, "state": 2}, {"macroId": 0, "state": 0}]}
        self.assertEqual(macro_at(snapshot, 5)["state"], 2)
        self.assertIsNone(macro_at(snapshot, 4))

    def test_review_and_bypass_are_still_owned_by_daw(self):
        for state in (1, 2, 3):
            self.assertTrue(macro_is_assigned({"state": state}))
        self.assertFalse(macro_is_assigned({"state": 0}))
        self.assertFalse(macro_is_assigned(None))

    def test_text_comes_from_single_actual_target(self):
        self.assertEqual(macro_value_text({"targets": [{"valueText": "42 ms"}]}), "42 ms")
        self.assertEqual(macro_value_text({"targets": [{}, {}]}), "")


if __name__ == "__main__":
    unittest.main()
