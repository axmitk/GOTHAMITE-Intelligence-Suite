import unittest
from unittest.mock import Mock, patch
from scripts.demo_viewer import rewrite_links, ViewerHandler
from client.onion_client import OnionClientError

class DummyRequest:
    def makefile(self, *args, **kwargs):
        from io import BytesIO
        return BytesIO(b"")

class DummyServer:
    client = Mock()

class TestDemoViewer(unittest.TestCase):
    def test_link_rewriting(self):
        html = b'<a href="/thread/12">Post</a> and <a href="/">Back</a>'
        mock_host = "alpha7fq2mx9k.onion.mock"
        rewritten = rewrite_links(html, mock_host)
        expected = b'<a href="/alpha7fq2mx9k.onion.mock/thread/12">Post</a> and <a href="/alpha7fq2mx9k.onion.mock/">Back</a>'
        self.assertEqual(rewritten, expected)

    def test_link_rewriting_handles_multiple(self):
        html = b'<li><a href="/user/nightjar">n</a></li><li><a href="/user/quill">q</a></li>'
        mock_host = "beta4np8vz3wc.onion.mock"
        rewritten = rewrite_links(html, mock_host)
        self.assertIn(b'href="/beta4np8vz3wc.onion.mock/user/nightjar"', rewritten)
        self.assertIn(b'href="/beta4np8vz3wc.onion.mock/user/quill"', rewritten)

    def setUp(self):
        self.client_mock = Mock()
        self.server = DummyServer()
        self.server.client = self.client_mock
        
        self.handler = ViewerHandler(DummyRequest(), ("127.0.0.1", 1234), self.server)
        self.handler.client = self.client_mock
        self.handler.send_response = Mock()
        self.handler.send_header = Mock()
        self.handler.end_headers = Mock()
        self.handler.wfile = Mock()

    def test_routing_landing_page(self):
        self.handler.path = "/"
        self.handler.do_GET()
        self.handler.send_response.assert_called_with(200)
        self.client_mock.get_path.assert_not_called()

    def test_routing_health(self):
        self.handler.path = "/health"
        self.handler.do_GET()
        self.handler.send_response.assert_called_with(200)
        self.client_mock.get_path.assert_not_called()

    def test_host_allowlisting_rejects_unknown(self):
        self.handler.path = "/evil.onion.mock/thread/1"
        self.handler.do_GET()
        self.handler.send_response.assert_called_with(403)
        self.client_mock.get_path.assert_not_called()

    def test_host_allowlisting_accepts_known(self):
        self.handler.path = "/alpha7fq2mx9k.onion.mock/thread/12"
        hop_mock = Mock()
        hop_mock.relay_id = "relay-1"
        self.client_mock.get_path.return_value = [hop_mock]
        self.client_mock.get.return_value = b"<html>Content</html>"
        
        self.handler.do_GET()
        
        self.handler.send_response.assert_called_with(200)
        self.client_mock.get_path.assert_called_once_with(3)
        self.client_mock.get.assert_called_once_with([hop_mock], "alpha7fq2mx9k.onion.mock", "/thread/12")
        self.handler.wfile.write.assert_called_once()
        
    def test_isolation_handles_onion_error(self):
        self.handler.path = "/alpha7fq2mx9k.onion.mock/thread/12"
        hop_mock = Mock()
        hop_mock.relay_id = "relay-1"
        self.client_mock.get_path.return_value = [hop_mock]
        self.client_mock.get.side_effect = OnionClientError("Mock unreachable")
        
        self.handler.do_GET()
        
        self.handler.send_response.assert_called_with(502)

if __name__ == "__main__":
    unittest.main()
