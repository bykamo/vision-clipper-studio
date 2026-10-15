import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from backend.transcriber import fetch_youtube_transcript


@dataclass
class DummySnippet:
    text: str
    start: float
    duration: float


class DummyFetchedTranscript:
    def __init__(self, snippets):
        self.snippets = snippets

    def to_raw_data(self):
        return [
            {"text": s.text, "start": s.start, "duration": s.duration}
            for s in self.snippets
        ]

    def __iter__(self):
        return iter(self.snippets)


class TranscriberSnippetCompatibilityTest(unittest.TestCase):
    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_fetches_transcript_using_to_raw_data(self, mock_api_cls):
        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        
        mock_list = MagicMock()
        mock_api.list.return_value = mock_list

        mock_obj = MagicMock()
        dummy_fetched = DummyFetchedTranscript([
            DummySnippet(text="Halo\ndunia", start=1.5, duration=3.0),
            DummySnippet(text="Clip kedua", start=4.5, duration=2.0)
        ])
        mock_obj.fetch.return_value = dummy_fetched
        mock_list.find_transcript.return_value = mock_obj

        segments = fetch_youtube_transcript("dummy_video_123")
        self.assertIsNotNone(segments)
        self.assertEqual(len(segments), 2)
        
        first = segments[0]
        self.assertEqual(first["start"], 1.5)
        self.assertEqual(first["end"], 4.5)
        self.assertEqual(first["text"], "Halo dunia")
        self.assertTrue(len(first["words"]) >= 2)

    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_fetches_transcript_using_object_attributes_fallback(self, mock_api_cls):
        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        
        mock_list = MagicMock()
        mock_api.list.return_value = mock_list

        mock_obj = MagicMock()
        # Objek tanpa metode to_raw_data
        class RawSnippetsList(list):
            pass

        snippets = RawSnippetsList([
            DummySnippet(text="Baris satu", start=0.0, duration=2.5)
        ])
        mock_obj.fetch.return_value = snippets
        mock_list.find_transcript.return_value = mock_obj

        segments = fetch_youtube_transcript("dummy_video_456")
        self.assertIsNotNone(segments)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "Baris satu")
        self.assertEqual(segments[0]["end"], 2.5)

    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_fetches_legacy_dict_list(self, mock_api_cls):
        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        
        mock_list = MagicMock()
        mock_api.list.return_value = mock_list

        mock_obj = MagicMock()
        mock_obj.fetch.return_value = [
            {"text": "Format lama", "start": 2.0, "duration": 4.0}
        ]
        mock_list.find_transcript.return_value = mock_obj

        segments = fetch_youtube_transcript("dummy_video_789")
        self.assertIsNotNone(segments)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "Format lama")
        self.assertEqual(segments[0]["start"], 2.0)
        self.assertEqual(segments[0]["end"], 6.0)

    @patch("youtube_transcript_api.YouTubeTranscriptApi")
    def test_fetch_youtube_transcript_with_english_language(self, mock_api_cls):
        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        mock_list = MagicMock()
        mock_api.list.return_value = mock_list

        mock_obj = MagicMock()
        mock_obj.fetch.return_value = [{"text": "Hello world", "start": 0.0, "duration": 3.0}]
        mock_list.find_transcript.return_value = mock_obj

        segments = fetch_youtube_transcript("dummy_en_vid", source_lang="en")
        self.assertIsNotNone(segments)
        self.assertEqual(segments[0]["text"], "Hello world")
        mock_list.find_transcript.assert_called_with(['en', 'en-US', 'en-GB'])

    @patch("requests.post")
    @patch("backend.utils.get_groq_api_keys", return_value=["gsk_test1234567890"])
    def test_transcribe_with_groq_language_payload(self, mock_keys, mock_post):
        from backend.transcriber import transcribe_with_groq
        import tempfile
        import os

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test"}],
            "words": [{"word": "Test", "start": 0.0, "end": 2.0}]
        }
        mock_post.return_value = mock_resp

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"dummy audio")
            temp_path = f.name

        try:
            # 1. Test language="en"
            transcribe_with_groq(temp_path, language="en")
            call_files = mock_post.call_args[1]["files"]
            lang_entry = next((item for item in call_files if item[0] == "language"), None)
            self.assertIsNotNone(lang_entry)
            self.assertEqual(lang_entry[1][1], "en")

            # 2. Test language="auto" (should NOT include language param to allow Whisper auto-detect)
            transcribe_with_groq(temp_path, language="auto")
            call_files_auto = mock_post.call_args[1]["files"]
            lang_entry_auto = next((item for item in call_files_auto if item[0] == "language"), None)
            self.assertIsNone(lang_entry_auto)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch("backend.analyzer.call_llm_api")
    def test_translate_segments_to_indonesian_preserves_boundaries_and_words(self, mock_call_llm):
        from backend.transcriber import translate_segments_to_indonesian
        mock_call_llm.return_value = '```json\n[{"id": 0, "text": "Halo semuanya"}, {"id": 1, "text": "Selamat datang kembali"}]\n```'

        input_segments = [
            {"start": 1.0, "end": 3.0, "text": "Hello everyone", "words": []},
            {"start": 3.5, "end": 6.0, "text": "Welcome back", "words": []}
        ]

        result = translate_segments_to_indonesian(input_segments)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "Halo semuanya")
        self.assertEqual(result[0]["start"], 1.0)
        self.assertEqual(result[0]["end"], 3.0)
        self.assertEqual(len(result[0]["words"]), 2)
        self.assertEqual(result[0]["words"][0]["word"], "Halo")
        self.assertAlmostEqual(result[0]["words"][0]["start"], 1.0)

        self.assertEqual(result[1]["text"], "Selamat datang kembali")
        self.assertEqual(result[1]["start"], 3.5)
        self.assertEqual(result[1]["end"], 6.0)
        self.assertEqual(len(result[1]["words"]), 3)

    @patch("uuid.uuid4")
    @patch("yt_dlp.YoutubeDL")
    @patch("webvtt.read")
    @patch("os.listdir")
    def test_fetch_ytdlp_subs_supports_two_part_and_three_part_vtt_timestamps(self, mock_listdir, mock_webvtt_read, mock_ytdlp, mock_uuid):
        from backend.transcriber import fetch_ytdlp_subs
        mock_uuid.return_value.hex = "12345678abcdef"
        mock_listdir.return_value = ["temp_sub_12345678.en.vtt"]

        class DummyCaption:
            def __init__(self, start, end, text):
                self.start = start
                self.end = end
                self.text = text

        # Test both 2-part (MM:SS.mmm) and 3-part (HH:MM:SS.mmm) timestamps
        mock_webvtt_read.return_value = [
            DummyCaption(start="04:15.200", end="04:18.500", text="Two-part MM:SS format"),
            DummyCaption(start="01:02:03.400", end="01:02:06.000", text="Three-part HH:MM:SS format")
        ]

        segments = fetch_ytdlp_subs("https://youtube.com/watch?v=dummy", source_lang="en")
        self.assertIsNotNone(segments)
        self.assertEqual(len(segments), 2)

        # 04:15.200 = 4 * 60 + 15.2 = 255.2
        self.assertAlmostEqual(segments[0]["start"], 255.2, places=2)
        self.assertAlmostEqual(segments[0]["end"], 258.5, places=2)

        # 01:02:03.400 = 3600 + 120 + 3.4 = 3723.4
        self.assertAlmostEqual(segments[1]["start"], 3723.4, places=2)
        self.assertAlmostEqual(segments[1]["end"], 3726.0, places=2)


if __name__ == "__main__":
    unittest.main()
