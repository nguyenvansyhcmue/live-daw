import unittest
from unittest.mock import patch

from core.services.browser_monitor_service import BrowserMonitorService


class BrowserMonitorTests(unittest.TestCase):
    def test_selects_playing_youtube_tab_instead_of_stale_first_tab(self):
        monitor = BrowserMonitorService()
        monitor.get_tabs = lambda: [
            {"type": "page", "url": "https://www.youtube.com/watch?v=OLDVIDEO001",
             "title": "Old paused tab", "webSocketDebuggerUrl": "ws://old"},
            {"type": "page", "url": "https://www.youtube.com/watch?v=NEWVIDEO002",
             "title": "Song playing now", "webSocketDebuggerUrl": "ws://playing"},
        ]
        with patch.object(monitor, "_playback_priority",
                          side_effect=lambda tab: 3 if tab["title"] == "Song playing now" else 1):
            selected = monitor.get_current_youtube_video()
        self.assertEqual(selected["video_id"], "NEWVIDEO002")
        self.assertEqual(selected["title"], "Song playing now")
        self.assertNotIn("_tab", selected)

    def test_single_tab_does_not_require_websocket_probe(self):
        monitor = BrowserMonitorService()
        monitor.get_tabs = lambda: [
            {"type": "page", "url": "https://youtu.be/SONGVIDEO01",
             "title": "Only song"},
        ]
        with patch.object(monitor, "_playback_priority") as priority:
            selected = monitor.get_current_youtube_video()
        priority.assert_not_called()
        self.assertEqual(selected["url"], "https://www.youtube.com/watch?v=SONGVIDEO01")

