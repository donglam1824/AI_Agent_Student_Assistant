import unittest
from unittest.mock import patch, MagicMock
from services.intent_router import IntentRouter, IntentResult

class TestIntentRouter(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_keyword_signals_note(self):
        signals = self.router._get_keyword_signals("lưu ghi chú bài giảng hôm nay")
        self.assertIn("note", signals)
        
        signals = self.router._get_keyword_signals("ghi chu cho tôi")
        self.assertIn("note", signals)

    def test_keyword_signals_calendar(self):
        signals = self.router._get_keyword_signals("xem lịch học tuần sau")
        self.assertIn("calendar", signals)

        signals = self.router._get_keyword_signals("deadline nộp bài ngày mai")
        self.assertIn("calendar", signals)

    def test_keyword_signals_email(self):
        signals = self.router._get_keyword_signals("kiểm tra gmail của tôi")
        self.assertIn("email", signals)

    def test_keyword_signals_teams(self):
        signals = self.router._get_keyword_signals("học microsoft teams lớp nào")
        self.assertIn("teams", signals)

    def test_keyword_signals_docsearch(self):
        signals = self.router._get_keyword_signals("tóm tắt chương 2 môn oop")
        self.assertIn("docsearch", signals)

    def test_overlapping_intents(self):
        # "note" (note keyword) + "lịch" (calendar keyword) -> should have both
        signals = self.router._get_keyword_signals("note cho tôi những mục này vào lịch học")
        self.assertIn("note", signals)
        self.assertIn("calendar", signals)

    def test_no_keywords(self):
        signals = self.router._get_keyword_signals("xin chào bạn khỏe không")
        self.assertEqual(len(signals), 0)

    def test_word_boundaries(self):
        # "khen" contains substring "hen" but should NOT match calendar
        signals = self.router._get_keyword_signals("thầy khen em hôm nay")
        self.assertNotIn("calendar", signals)

    def test_lich_exclusions(self):
        # "lịch sử" should be excluded and NOT match calendar
        signals = self.router._get_keyword_signals("lịch sử hình thành của hệ điều hành là gì")
        self.assertNotIn("calendar", signals)
        
        # If both "lịch sử" and "lịch học" exist, it should still match "lịch học" -> calendar
        signals = self.router._get_keyword_signals("xem lịch sử và lịch học hôm nay")
        self.assertIn("calendar", signals)

    @patch('services.intent_router.llm_manager.get_model')
    def test_classify_llm_high_confidence(self, mock_get_model):
        # Setup mock
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_get_model.return_value = mock_llm
        
        # LLM returns high confidence for docsearch, despite no keywords
        mock_structured.invoke.return_value = IntentResult(
            intent="docsearch",
            confidence=0.9,
            reasoning="Hỏi định lý"
        )
        
        result = self.router.classify("Định lý pytago là gì")
        self.assertEqual(result.intent, "docsearch")
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(result.reasoning, "Hỏi định lý")

    @patch('services.intent_router.llm_manager.get_model')
    def test_classify_llm_low_confidence_keyword_boost(self, mock_get_model):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_get_model.return_value = mock_llm
        
        # LLM returns mid confidence for calendar
        mock_structured.invoke.return_value = IntentResult(
            intent="calendar",
            confidence=0.6,
            reasoning="Có nhắc đến thời gian"
        )
        
        result = self.router.classify("Lịch học ngày mai là gì")
        self.assertEqual(result.intent, "calendar")
        self.assertEqual(result.confidence, 0.85) # Boosted
        self.assertIn("Boosted by keyword", result.reasoning)

    @patch('services.intent_router.llm_manager.get_model')
    def test_classify_llm_fails_fallback_to_keyword(self, mock_get_model):
        mock_get_model.side_effect = Exception("API Error")
        
        # Should fallback to keyword
        result = self.router.classify("Ghi chú bài giảng")
        self.assertEqual(result.intent, "note")
        self.assertEqual(result.confidence, 0.9)
        self.assertIn("Fallback", result.reasoning)

if __name__ == "__main__":
    unittest.main()
