import unittest
from unittest.mock import Mock, patch

from zexa.research import (
    DuckDuckGoSearch, SearchResult, _PageTextParser, _canonical_result_url,
    _validate_public_https_url, fetch_public_page, summarize_research,
)


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
        return self.body[:size] if isinstance(self.body, bytes) else self.body[:size].encode('utf-8')


class FakeReply:
    def __init__(self, text):
        self.text = text


class FakeBrain:
    def chat(self, messages):
        self.messages = messages
        return FakeReply("Summary [1].")


class ResearchTests(unittest.TestCase):
    def test_search_parses_results_and_unwraps_redirects(self):
        with patch("zexa.research.urlopen", return_value=FakeResponse(SAMPLE_HTML.encode('utf-8'))):
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

    def test_public_page_url_rejects_local_credentials_and_nonstandard_ports(self):
        for url in (
            "http://example.com/page",
            "https://user:pass@example.com/page",
            "https://localhost/page",
            "https://127.0.0.1/page",
            "https://example.com:8443/page",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _validate_public_https_url(url)

    def test_public_page_url_accepts_global_ipv6_literal(self):
        parsed, host = _validate_public_https_url("https://[2606:4700:4700::1111]/guide")
        self.assertEqual(parsed.hostname, "2606:4700:4700::1111")
        self.assertEqual(host, "2606:4700:4700::1111")

    def test_public_connection_rejects_private_dns_answers(self):
        import socket
        with (
            patch(
                "zexa.research.socket.getaddrinfo",
                return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
            ),
            patch("zexa.research.socket.create_connection") as connect,
            self.assertRaises(PermissionError),
        ):
            from zexa.research import _connect_public_https
            _connect_public_https("public.example", 3.0)
        connect.assert_not_called()

    def test_public_https_connection_requires_tls_12(self):
        import socket
        import ssl

        raw_socket = Mock()
        wrapped_socket = Mock()
        context = Mock()
        context.wrap_socket.return_value = wrapped_socket
        with (
            patch(
                "zexa.research.socket.getaddrinfo",
                return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
            ),
            patch("zexa.research.socket.create_connection", return_value=raw_socket),
            patch("zexa.research.ssl.create_default_context", return_value=context),
        ):
            from zexa.research import _connect_public_https
            result = _connect_public_https("public.example", 3.0)

        self.assertIs(result, wrapped_socket)
        self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
        context.wrap_socket.assert_called_once_with(raw_socket, server_hostname="public.example")

    def test_page_parser_omits_scripts_and_extracts_title_and_text(self):
        parser = _PageTextParser()
        parser.feed(
            "<html><head><title>Study Guide</title><script>ignore this</script></head>"
            "<body><h1>Photosynthesis</h1><p>Plants use sunlight.</p>"
            "<style>hidden style</style></body></html>"
        )
        title, text = parser.result()
        self.assertEqual(title, "Study Guide")
        self.assertIn("Photosynthesis", text)
        self.assertIn("Plants use sunlight.", text)
        self.assertNotIn("ignore this", text)
        self.assertNotIn("hidden style", text)

    def test_fetch_public_page_reads_bounded_https_html(self):
        class FakeSocket:
            def __init__(self):
                self.request = b""
                self.closed = False

            def sendall(self, data):
                self.request = data

            def close(self):
                self.closed = True

        class Response:
            status = 200

            def __init__(self):
                self.closed = False

            def begin(self):
                return None

            def getheader(self, name, default=""):
                return {
                    "Content-Type": "text/html; charset=utf-8",
                    "Location": "",
                }.get(name, default)

            def read(self, limit):
                return b"<title>Public Guide</title><p>Safe learning content.</p>"[:limit]

            def close(self):
                self.closed = True

        connection = FakeSocket()
        response = Response()
        with (
            patch("zexa.research._connect_public_https", return_value=connection),
            patch("zexa.research.http.client.HTTPResponse", return_value=response),
        ):
            page = fetch_public_page("https://example.com/guide")
        self.assertEqual(page.title, "Public Guide")
        self.assertIn("Safe learning content.", page.text)
        self.assertEqual(len(page.content_sha256), 64)
        self.assertIn(b"GET /guide HTTP/1.1", connection.request)
        self.assertIn(b"\r\nHost: example.com\r\n", connection.request)
        self.assertIn(b"\r\n\r\n", connection.request)
        self.assertTrue(connection.closed)
        self.assertTrue(response.closed)

    def test_fetch_public_page_brackets_ipv6_host_header(self):
        class FakeSocket:
            def __init__(self):
                self.request = b""
            def sendall(self, data):
                self.request = data
            def close(self):
                return None
        class Response:
            status = 200
            def begin(self):
                return None
            def getheader(self, name, default=""):
                return "text/plain" if name == "Content-Type" else default
            def read(self, limit):
                return b"IPv6 page text"
            def close(self):
                return None
        connection = FakeSocket()
        with (
            patch("zexa.research._connect_public_https", return_value=connection),
            patch("zexa.research.http.client.HTTPResponse", return_value=Response()),
        ):
            page = fetch_public_page("https://[2606:4700:4700::1111]/guide")
        self.assertIn("IPv6 page text", page.text)
        self.assertIn(b"Host: [2606:4700:4700::1111]\r\n", connection.request)

    def test_fetch_public_page_revalidates_redirect_target(self):
        class FakeSocket:
            def sendall(self, data):
                return None

            def close(self):
                return None

        class Redirect:
            status = 302

            def begin(self):
                return None

            def getheader(self, name, default=""):
                return "https://127.0.0.1/private" if name == "Location" else default

            def read(self, limit):
                return b""

            def close(self):
                return None

        with (
            patch("zexa.research._connect_public_https", return_value=FakeSocket()) as connect,
            patch("zexa.research.http.client.HTTPResponse", return_value=Redirect()),
            self.assertRaises(ValueError),
        ):
            fetch_public_page("https://example.com/redirect")
        connect.assert_called_once()

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
