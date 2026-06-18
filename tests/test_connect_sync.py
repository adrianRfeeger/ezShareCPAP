import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ezshare import ezShare


class FakeConnectionManager:
    def __init__(self):
        self.connected = False
        self.connect_calls = []
        self.disconnect_calls = []

    def connect(self, ssid, psk, target_host=None):
        self.connect_calls.append((ssid, psk, target_host))
        self.connected = True

    def verify_connection(self):
        return True

    def disconnect(self, ssid):
        self.disconnect_calls.append(ssid)
        self.connected = False
        return True


class FakeResponse:
    def __init__(self, text="", chunks=None):
        self.text = text
        self.chunks = chunks or []
        self.headers = {"content-length": str(sum(len(chunk) for chunk in self.chunks))}

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield from self.chunks


class FakeSession:
    def __init__(self):
        self.get_urls = []

    def mount(self, *args, **kwargs):
        pass

    def get(self, url, **kwargs):
        self.get_urls.append(url)
        if "download?" in url:
            return FakeResponse(chunks=[b"edf-data"])

        return FakeResponse(
            text=(
                "<html><body><pre>"
                '2026-06-18 10:00:00 <a href="/download?file=STR.EDF">STR.EDF</a>\n'
                "</pre></body></html>"
            )
        )


class ConnectAndSyncTests(unittest.TestCase):
    def test_run_connects_syncs_file_and_disconnects(self):
        app = ezShare()
        fake_connection = FakeConnectionManager()
        fake_session = FakeSession()
        statuses = []
        progress = []

        app.connection_manager = fake_connection
        app.set_status_callback(lambda message, message_type="info": statuses.append((message, message_type)))
        app.set_progress_callback(progress.append)

        with tempfile.TemporaryDirectory() as tmpdir:
            app.set_params(
                path=tmpdir,
                url="http://192.168.4.1/dir?dir=A:",
                start_time=None,
                show_progress=False,
                verbose=False,
                overwrite=False,
                keep_old=False,
                ssid="ez Share",
                psk="88888888",
                ignore=[],
                retries=1,
                connection_delay=0,
                debug=False,
            )

            with patch("ezshare.requests.Session", return_value=fake_session), patch("ezshare.time.sleep"):
                self.assertTrue(app.run())

            downloaded_file = Path(tmpdir) / "STR.EDF"
            self.assertEqual(downloaded_file.read_bytes(), b"edf-data")

        self.assertEqual(fake_connection.connect_calls, [("ez Share", "88888888", "192.168.4.1")])
        self.assertEqual(fake_connection.disconnect_calls, ["ez Share"])
        self.assertFalse(app.connected)
        self.assertIn(100, progress)
        self.assertIn(("Connected to ez Share.", "info"), statuses)
        self.assertIn(("File transfer completed successfully.", "info"), statuses)


if __name__ == "__main__":
    unittest.main()
