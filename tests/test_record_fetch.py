"""Recorder fetch: CelesTrak outages are retried and never crash the run (7 Oct 2026 timeout)."""
import os
import sys
import unittest
import unittest.mock
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "recorder"))
import record  # noqa: E402


class _Resp:
    status = 200
    headers = {}

    def read(self):
        return b"[]"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.p = unittest.mock.patch.object(record, "RETRY_WAIT", (0, 0, 0))
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_timeout_then_success(self):
        calls = [TimeoutError("timed out"), urllib.error.URLError("timed out"), _Resp()]
        with unittest.mock.patch("urllib.request.urlopen", side_effect=calls):
            self.assertEqual(record.fetch("https://example.invalid/x"), (200, b"[]"))

    def test_every_attempt_fails_gives_status_0(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            self.assertEqual(record.fetch("https://example.invalid/x"), (0, b""))

    def test_404_is_returned_without_retry(self):
        err = urllib.error.HTTPError("u", 404, "nf", {}, None)
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as m:
            self.assertEqual(record.fetch("https://example.invalid/x"), (404, b""))
            self.assertEqual(m.call_count, 1)


if __name__ == "__main__":
    unittest.main()
