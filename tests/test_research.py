import unittest
from unittest.mock import patch

from zexa.research import DuckDuckGoSearch, SearchResult, _canonical_result_url, summarize_research


SAMPLE_HTML = """
<div class="result">
  <a class="result__a" href="https://example.org/page">Example Result</a>
  <a class="result__snippet">A useful summary from the result.</a>
</div>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.net%2Fstory">Second Result</a>
  <div class="result__snippet">Another snippet.</div>
</div>
"""


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.body[:size]


class FakeReply:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def chat(self, messages):
        self.messages = messages
        return FakeReply("Summary [1].")


class ResearchTests(unittest.TestCase):
    def test_search_parses_results_and_unwraps_redirects(self):
        with patch("zexa.research.urlopen", return_value=FakeResponse(SAMPLE_HTML)):
            results = DuckDuckGoSearch().search("Zexa assistant")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Example Result")
        self.assertEqual(results[0].url, "https://example.org/page")
        self.assertEqual(results[1].url, "https://example.net/story")

    def test_rejects_non_http_and_credential_urls(self):
        self.assertIsNone(_canonical_result_url("javascript:alert(1)"))
        self.assertIsNone(_canonical_result_url("https://user:pass@example.com/"))

    def test_validates_query_and_limit(self):
        with self.assertRaises(ValueError):
            DuckDuckGoSearch().search(" ")
        with self.assertRaises(ValueError):
            DuckDuckGoSearch().search("hello", 11)

    def test_summary_uses_numbered_sources_and_untrusted_content_warning(self):
        brain = FakeBrain()
        result = summarize_research(
            brain, "test query",
            [SearchResult("Example", "https://example.org", "Snippet")],
        )
        self.assertEqual(result, "Summary [1].")
        self.assertIn("untrusted data", brain.messages[0]["content"])
        self.assertIn("https://example.org", brain.messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
