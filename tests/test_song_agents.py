import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from openai import OpenAI

import config
from song_agents import (select_songs, review_selection, validate_review,
                         compare_selection, check_chart_files)


BANK = {
    "014": {"title": "I Think We're Alone Now", "type": "single"},
    "027": {"title": "Pretty Woman", "type": "single"},
    "034": {"title": "Wagon Wheel", "type": "single"},
}


def entry(number, indices=(), missing=(), uncertainties=(), heading=False):
    return {"line_number": number, "expected_indices": list(indices),
            "missing_songs": list(missing), "uncertainties": list(uncertainties),
            "is_heading": heading}


def fake_client(*outputs):
    client = MagicMock()
    client.responses.create.side_effect = [
        SimpleNamespace(status="completed", output_text=output) for output in outputs
    ]
    return client


class SongAgentTests(unittest.TestCase):
    def test_two_independent_passes_and_medley_order(self):
        rows = [entry(1, ["014", "027"]), entry(2, ["034"])]
        client = fake_client("014, 027, 034", json.dumps({"entries": rows}))
        text = "I Think We're Alone Now/Pretty Woman\nWagon Wheel"
        indices = select_songs(client, text, BANK, "medium")
        report = review_selection(client, text, indices, BANK, "medium")
        self.assertTrue(report["matches"])
        self.assertEqual(report["song_lines"], 2)
        self.assertEqual(client.responses.create.call_count, 2)
        review_call = client.responses.create.call_args.kwargs
        self.assertNotIn("selected_indices", json.loads(review_call["input"]))
        self.assertTrue(review_call["text"]["format"]["strict"])

    def test_sdk_serializes_all_supported_efforts(self):
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "resp_test", "object": "response", "created_at": 1,
                "status": "completed", "model": config.MODEL,
                "output": [{"id": "msg_test", "type": "message", "role": "assistant",
                            "status": "completed", "content": [
                                {"type": "output_text", "text": "034", "annotations": []}]}],
            })

        with OpenAI(api_key="offline-test", http_client=httpx.Client(
            transport=httpx.MockTransport(respond)
        )) as client:
            for effort in config.REASONING_LEVELS:
                self.assertEqual(select_songs(client, "Wagon Wheel", BANK, effort), ["034"])
        self.assertEqual([request["reasoning"]["effort"] for request in requests],
                         list(config.REASONING_LEVELS))
        for request in requests:
            self.assertEqual(request["model"], "gpt-6.1-sol")
            self.assertFalse(request["store"])
            self.assertNotIn("temperature", request)
            self.assertNotIn("max_tokens", request)

    def test_missing_medley_component_and_omitted_available_song(self):
        rows = validate_review({"entries": [entry(1, ["014", "027"], ["Missing Song"])]},
                               ["Alone Now/Pretty Woman/Missing Song"], BANK)
        report = compare_selection(["014"], rows, BANK)
        self.assertFalse(report["matches"])
        self.assertEqual(report["omitted"], ["027 — Pretty Woman"])
        self.assertEqual(report["missing_songs"], ["Line 1: Missing Song"])

    def test_order_and_repetition_are_checked(self):
        rows = validate_review({"entries": [entry(1, ["034"]), entry(2, ["014"]),
                                             entry(3, ["034"])]}, ["A", "B", "A"], BANK)
        self.assertTrue(compare_selection(["014", "034", "034"], rows, BANK)["order_issue"])
        self.assertEqual(compare_selection(["034", "014"], rows, BANK)["omitted"],
                         ["034 — Wagon Wheel"])
        self.assertTrue(compare_selection(["034", "014", "034"], rows, BANK)["matches"])

    def test_wrong_selection_is_reported(self):
        rows = validate_review({"entries": [entry(1, ["034"])]}, ["Wagon Wheel"], BANK)
        report = compare_selection(["014"], rows, BANK)
        self.assertEqual(report["unexpected"], ["014 — I Think We're Alone Now"])
        self.assertEqual(report["omitted"], ["034 — Wagon Wheel"])

    def test_all_missing_is_reviewed_without_a_selection(self):
        client = fake_client("NONE", json.dumps({"entries": [entry(1, missing=["Missing"])]}))
        selected = select_songs(client, "Missing", BANK, "medium")
        report = review_selection(client, "Missing", selected, BANK, "medium")
        self.assertEqual(selected, [])
        self.assertTrue(report["missing_songs"])
        self.assertEqual(client.responses.create.call_count, 2)

    def test_heading_and_ambiguity(self):
        rows = validate_review({"entries": [entry(1, heading=True), entry(2, uncertainties=[
            "Choose the requested arrangement."])]}, ["Set 1", "Song"], BANK)
        report = compare_selection([], rows, BANK)
        self.assertEqual(report["song_lines"], 1)
        self.assertEqual(report["uncertainties"], ["Line 2: Choose the requested arrangement."])

    def test_invalid_review_cannot_confirm(self):
        bad_reviews = [
            {}, {"entries": []}, {"entries": [entry(2, ["034"])]},
            {"entries": [entry(1, ["999"])]}, {"entries": [entry(1)]},
            {"entries": [entry(1, ["034"], heading=True)]},
            {"entries": [entry(1, missing=[""])]},
        ]
        for review in bad_reviews:
            with self.subTest(review=review), self.assertRaises(ValueError):
                validate_review(copy.deepcopy(review), ["Wagon Wheel"], BANK)

    def test_malformed_and_incomplete_selection(self):
        for reply in ("Reason: 034", "34", "034, 027 some text", ""):
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                select_songs(fake_client(reply), "Wagon Wheel", BANK, "medium")
        client = fake_client("034")
        client.responses.create.side_effect = None
        client.responses.create.return_value = SimpleNamespace(status="incomplete", output_text="034")
        with self.assertRaises(ValueError):
            select_songs(client, "Wagon Wheel", BANK, "medium")

    def test_chart_inventory_includes_unknowns_and_missing_files(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            (Path(folder) / "034.pdf").write_bytes(b"test")
            result = check_chart_files(["034", "027", "027", "999"], folder, BANK)
        self.assertEqual(result["unknown_indices"], ["999"])
        self.assertEqual(result["missing_files"], ["027 — Pretty Woman", "999 — Unknown chart"])

    def test_environment_file_is_reloaded_and_takes_precedence(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder) / ".env"
            with patch.object(config, "ENV_FILE", path), patch.dict(
                "os.environ", {"OPENAI_API_KEY": "environment-test"}
            ):
                self.assertEqual(config.get_api_key(), "environment-test")
                path.write_text('OPENAI_API_KEY="local-test"\n', encoding="utf-8")
                self.assertEqual(config.get_api_key(), "local-test")
                path.write_text("OPENAI_API_KEY=updated-test\n", encoding="utf-8")
                self.assertEqual(config.get_api_key(), "updated-test")
                path.write_text("OPENAI_API_KEY=\n", encoding="utf-8")
                self.assertEqual(config.get_api_key(), "environment-test")


if __name__ == "__main__":
    unittest.main()
