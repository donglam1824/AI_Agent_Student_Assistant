import unittest

from core.llm_manager import FallbackChatModel


class FakeModel:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.bound_tools = None

    def invoke(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.value

    def bind_tools(self, tools, **kwargs):
        bound = FakeModel(value=self.value, error=self.error)
        bound.bound_tools = tools
        return bound


class FallbackChatModelTest(unittest.TestCase):
    def setUp(self):
        FallbackChatModel._cooldowns.clear()

    def test_invoke_falls_back_on_quota_error(self):
        primary = FakeModel(
            error=Exception("429 RESOURCE_EXHAUSTED quota exceeded. retryDelay: '30s'")
        )
        fallback = FakeModel(value="fallback response")
        llm = FallbackChatModel(
            [
                ("gemini-2.5-flash", primary),
                ("gemini-3.1-flash-lite", fallback),
            ]
        )

        self.assertEqual(llm.invoke("hello"), "fallback response")

    def test_invoke_does_not_fall_back_on_non_quota_error(self):
        primary = FakeModel(error=Exception("invalid prompt"))
        fallback = FakeModel(value="fallback response")
        llm = FallbackChatModel(
            [
                ("gemini-2.5-flash", primary),
                ("gemini-3.1-flash-lite", fallback),
            ]
        )

        with self.assertRaisesRegex(Exception, "invalid prompt"):
            llm.invoke("hello")

    def test_bind_tools_preserves_fallback_chain(self):
        primary = FakeModel(
            error=Exception("429 RESOURCE_EXHAUSTED quota exceeded. retryDelay: '30s'")
        )
        fallback = FakeModel(value="fallback response")
        llm = FallbackChatModel(
            [
                ("gemini-2.5-flash", primary),
                ("gemini-3.1-flash-lite", fallback),
            ]
        )

        bound_llm = llm.bind_tools(["tool"])

        self.assertEqual(bound_llm.invoke("hello"), "fallback response")


if __name__ == "__main__":
    unittest.main()
