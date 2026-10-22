import unittest

from core.services.tone_source_coordinator import ToneSourceCoordinator


class ToneSourceCoordinatorTests(unittest.TestCase):
    def test_only_current_source_session_is_accepted(self):
        coordinator = ToneSourceCoordinator("daw")
        daw = coordinator.session
        self.assertTrue(coordinator.accepts(daw.source, daw.generation))

        youtube = coordinator.switch("youtube")
        self.assertFalse(coordinator.accepts(daw.source, daw.generation))
        self.assertTrue(coordinator.accepts(youtube.source, youtube.generation))

        microphone = coordinator.switch("microphone")
        self.assertFalse(coordinator.accepts(youtube.source, youtube.generation))
        self.assertTrue(coordinator.accepts(microphone.source, microphone.generation))

    def test_reselecting_source_invalidates_old_callbacks(self):
        coordinator = ToneSourceCoordinator("microphone")
        old = coordinator.session
        new = coordinator.switch("microphone")
        self.assertNotEqual(old.generation, new.generation)
        self.assertFalse(coordinator.accepts(old.source, old.generation))

    def test_unknown_source_is_rejected(self):
        with self.assertRaises(ValueError):
            ToneSourceCoordinator("browser-tab")


if __name__ == "__main__":
    unittest.main()
