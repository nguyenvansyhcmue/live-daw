import unittest

from core.services.performance_surface_service import PerformanceSurfaceService


class ParameterPaginationTests(unittest.TestCase):
    def setUp(self):
        self.service = PerformanceSurfaceService()
        self.service._project_revision = "42"

    def test_large_plugin_keeps_every_parameter_in_order(self):
        values = [{"parameterId": str(i)} for i in range(737)]

        def request(payload):
            start = payload["offset"]
            end = min(start + payload["limit"], len(values))
            return {"ok": True, "parameters": values[start:end], "total": len(values),
                    "nextOffset": end if end < len(values) else -1}

        self.service._request = request
        result = self.service.get_plugin_parameters("1", 0, "instance")
        self.assertEqual(result["parameters"], values)

    def test_rejects_changed_project_and_bad_continuation(self):
        def changed(_payload):
            self.service._project_revision = "43"
            return {"ok": True, "parameters": []}

        self.service._request = changed
        self.assertIsNone(self.service.get_plugin_parameters("1", 0, "instance"))
        self.service._project_revision = "42"
        self.service._request = lambda _: {"ok": True, "parameters": [1], "total": 10,
                                          "nextOffset": 8}
        self.assertIsNone(self.service.get_plugin_parameters("1", 0, "instance"))

    def test_preserves_old_daw_response(self):
        self.service._request = lambda _: {"ok": True, "parameters": [{"name": "Gain"}]}
        self.assertEqual(self.service.get_plugin_parameters("1", 0, "instance")["parameters"],
                         [{"name": "Gain"}])

    def test_recommended_parameters_use_separate_lazy_endpoint(self):
        captured = []

        def request(payload):
            captured.append(dict(payload))
            return {"ok": True, "parameters": [{"parameterId": "mix", "recommended": True}],
                    "allParameterCount": 346, "total": 1, "nextOffset": -1}

        self.service._request = request
        result = self.service.get_recommended_plugin_parameters("track:7", 2, "instance")
        self.assertEqual(result["allParameterCount"], 346)
        self.assertEqual(result["parameters"][0]["parameterId"], "mix")
        self.assertEqual(captured[0]["command"], "getRecommendedPluginParameters")
        self.assertEqual(captured[0]["limit"], 100)

    def test_analysis_source_selection_uses_stable_scope_and_id(self):
        captured = {}
        self.service._request = lambda payload: captured.update(payload) or {"ok": True}
        self.service.set_analysis_source("bus", "7")
        self.assertEqual(captured, {"command": "setAudioAnalysisSource",
                                    "sourceKind": "bus", "sourceId": "7"})

    def test_lightweight_analysis_poll_does_not_request_full_state(self):
        captured = {}
        self.service._request = lambda payload, mutating=True: (
            captured.update(payload) or {
                "type": "audioAnalysisFrame",
                "audioAnalysis": {"revision": "9", "waveform": [0.1, 0.2], "spectrum": [0.3]},
            })
        analysis = self.service.poll_audio_analysis()
        self.assertEqual(captured, {"command": "getAudioAnalysis"})
        self.assertEqual(analysis["revision"], "9")

    def test_transport_toggle_is_session_scoped_not_revision_gated(self):
        captured = {}

        def request(payload, mutating=True):
            captured.update(payload)
            captured["mutating"] = mutating
            return {"ok": True, "type": "transportState", "playing": True}

        self.service._request = request
        reply = self.service.toggle_transport()
        self.assertTrue(reply["playing"])
        self.assertEqual(captured, {"command": "toggleTransport", "mutating": False})

    def test_macro_mapping_uses_stable_daw_target_and_parameter_ids(self):
        captured = {}
        self.service._request = lambda payload: captured.update(payload) or {"ok": True}
        self.service.apply_mapping(
            4, "track:lead", 2, "plugin-instance-9", True,
            parameter_id="eq.band.3.gain", minimum=.15, maximum=.85,
            curve=3, invert=True, smoothing_ms=24,
        )
        self.assertEqual(captured, {
            "command": "applyMacroMapping", "macroId": 4,
            "targetId": "track:lead", "busId": "track:lead",
            "pluginSlot": 2, "pluginInstanceId": "plugin-instance-9",
            "confirmNeedsReview": True, "parameterId": "eq.band.3.gain",
            "minNormalized": .15, "maxNormalized": .85,
            "invert": True, "curve": 3, "smoothingMs": 24.0,
        })

    def test_live_controls_clamp_values_and_address_exact_ids(self):
        commands = []
        self.service._request = lambda payload: commands.append(dict(payload)) or {"ok": True}
        self.service.set_value(5, 1.75)
        self.service.set_eq_parameter("master", 1, "pro-q", "band.1.freq", -.4)
        self.service.clear_mapping(5)
        self.assertEqual(commands, [
            {"command": "setMacroValue", "macroId": 5, "value": 1.0},
            {"command": "setEqParameter", "busId": "master", "pluginSlot": 1,
             "pluginInstanceId": "pro-q", "parameterId": "band.1.freq", "value": 0.0},
            {"command": "clearMacroMapping", "macroId": 5},
        ])

    def test_detected_key_is_one_semantic_daw_command(self):
        captured = {}
        self.service._request = lambda payload: captured.update(payload) or {
            "ok": True, "type": "detectedKeyApplied",
            "targets": [{"trackName": "Vocal 1", "ok": True}],
        }
        reply = self.service.apply_detected_key(
            "F#", "Natural Minor", .873, "Live browser song")
        self.assertTrue(reply["ok"])
        self.assertEqual(captured, {
            "command": "applyDetectedKey", "key": "F#",
            "scale": "Natural Minor", "confidence": .873,
            "title": "Live browser song",
        })

    def test_detected_key_confidence_is_bounded_before_ipc(self):
        commands = []
        self.service._request = lambda payload: commands.append(payload) or {"ok": True}
        self.service.apply_detected_key("C", "Major", 4.2)
        self.service.apply_detected_key("D", "Minor", -1.0)
        self.assertEqual([item["confidence"] for item in commands], [1.0, 0.0])
