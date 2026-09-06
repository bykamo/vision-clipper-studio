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


if __name__ == "__main__":
    unittest.main()
