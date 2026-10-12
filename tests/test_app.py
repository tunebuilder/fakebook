import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from openai import APIConnectionError
from PyPDF2 import PdfReader, PdfWriter
from streamlit.testing.v1 import AppTest

import config
from test_song_agents import fake_client, entry


APP_PATH = config.PROJECT_DIR / "app.py"


class AppTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.folder.cleanup)
        self.project = Path(self.folder.name)
        bank = self.project / "song-bank"
        bank.mkdir()
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with (bank / "034.pdf").open("wb") as output:
            writer.write(output)
        self.path_patch = patch.object(config, "PROJECT_DIR", self.project)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.key_patch = patch.object(config, "get_api_key", return_value="offline-test")
        self.key_mock = self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def generate(self, client, text="Wagon Wheel"):
        with patch("openai.OpenAI", return_value=client):
            client.__enter__.return_value = client
            at = AppTest.from_file(str(APP_PATH), default_timeout=10).run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual([widget.label for widget in at.sidebar.text_input], ["Gig Name"])
            self.assertEqual(at.sidebar.selectbox[0].value, "medium")
            self.assertEqual(at.sidebar.selectbox[0].options, list(config.REASONING_LEVELS))
            at.sidebar.text_input[0].set_value("Test Gig")
            at.text_area[0].set_value(text)
            next(button for button in at.button if button.label == "Generate PDF").click().run()
        self.assertEqual(len(at.exception), 0)
        return at

    def test_success_pdf_links_and_result_survives_sidebar_change(self):
        client = fake_client("034", json.dumps({"entries": [entry(1, ["034"])]}))
        at = self.generate(client)
        self.assertTrue(any("Verified 1" in element.value for element in at.success))
        self.assertEqual(len(at.get("download_button")), 1)
        result = at.session_state["setlist_result"]
        from io import BytesIO
        pdf = PdfReader(BytesIO(result["pdf"]))
        self.assertEqual(len(pdf.pages), 3)
        self.assertIn("Wagon Wheel", pdf.pages[1].extract_text())
        link = pdf.pages[1]["/Annots"][0].get_object()
        self.assertEqual(link["/Dest"][0], pdf.pages[2].indirect_reference)
        at.sidebar.selectbox[0].set_value("max").run()
        self.assertEqual(len(at.get("download_button")), 1)
        self.assertTrue(any("previous result" in element.value for element in at.info))
        self.assertEqual(client.responses.create.call_count, 2)

    def test_all_missing_produces_report_without_pdf(self):
        client = fake_client("NONE", json.dumps({"entries": [entry(1, missing=["Missing Song"])]}))
        at = self.generate(client, "Missing Song")
        self.assertEqual(len(at.get("download_button")), 0)
        self.assertTrue(any("Missing from song bank" in element.value for element in at.markdown))
        self.assertTrue(any("Missing Song" in element.value for element in at.markdown))
        self.assertEqual(client.responses.create.call_count, 2)

    def test_missing_file_is_reported_without_empty_pdf(self):
        client = fake_client("027", json.dumps({"entries": [entry(1, ["027"])]}))
        at = self.generate(client, "Pretty Woman")
        self.assertEqual(len(at.get("download_button")), 0)
        self.assertTrue(any("Missing chart PDFs" in element.value for element in at.markdown))
        self.assertFalse(any("Verified" in element.value for element in at.success))

    def test_failed_review_preserves_unverified_download(self):
        client = fake_client("034")
        first_response = client.responses.create.side_effect
        client.responses.create.side_effect = [next(first_response), APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com/v1/responses"))]
        at = self.generate(client)
        self.assertTrue(any("Verification unavailable" in element.value for element in at.error))
        self.assertEqual(at.get("download_button")[0].label, "📥 Download PDF with review issues")
        self.assertFalse(any("Verified" in element.value for element in at.success))

    def test_incorrect_selection_is_not_confirmed(self):
        client = fake_client("034", json.dumps({"entries": [entry(1, ["027"])]}))
        at = self.generate(client, "Pretty Woman")
        self.assertTrue(any("Unexpected selections" in element.value for element in at.markdown))
        self.assertTrue(any("omitted" in element.value for element in at.markdown))
        self.assertEqual(at.get("download_button")[0].label, "📥 Download PDF with review issues")

    def test_missing_key_explains_env_setup_without_api_call(self):
        self.key_mock.return_value = ""
        client = fake_client("034")
        at = self.generate(client)
        self.assertTrue(any(".env" in element.value for element in at.error))
        client.responses.create.assert_not_called()

    def test_unreadable_pdf_keeps_report_and_shows_error(self):
        (self.project / "song-bank" / "034.pdf").write_bytes(b"invalid pdf")
        client = fake_client("034", json.dumps({"entries": [entry(1, ["034"])]}))
        at = self.generate(client)
        self.assertTrue(any("Could not build the PDF" in element.value for element in at.error))
        self.assertEqual(len(at.get("download_button")), 0)
        self.assertFalse(any("Verified" in element.value for element in at.success))


if __name__ == "__main__":
    unittest.main()
