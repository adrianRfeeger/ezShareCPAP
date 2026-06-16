import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

import file_ops
from ezshare import ezShare


class DirectoryListingTests(unittest.TestCase):
    def test_list_dir_returns_none_on_connection_failure(self):
        ezshare = SimpleNamespace(
            session=SimpleNamespace(
                get=lambda *args, **kwargs: (_ for _ in ()).throw(requests.ConnectTimeout("timeout"))
            )
        )

        self.assertEqual(file_ops.list_dir(ezshare, "http://192.168.4.1/dir?dir=A:"), (None, None))

    def test_run_after_connection_delay_retries_before_counting_files(self):
        app = ezShare()
        statuses = []
        with tempfile.TemporaryDirectory() as directory:
            app.path = pathlib.Path(directory)
            app.url = "http://192.168.4.1/dir?dir=A:"
            app.overwrite = False
            app.connected = True
            app.retries = 2
            app.connection_delay = 0
            app.update_status = lambda message, message_type="info": statuses.append((message, message_type))

            with patch("ezshare.list_dir", side_effect=[(None, None), ([], [])]) as list_dir, \
                    patch.object(app, "calculate_total_files", return_value=0), \
                    patch("ezshare.time.sleep"):
                app.run_after_connection_delay()

        self.assertEqual(list_dir.call_count, 2)
        self.assertIn(("Waiting for ez Share web server... attempt 1/2", "info"), statuses)
        self.assertIn(("Total files to sync: 0", "info"), statuses)

    def test_calculate_total_files_returns_none_when_listing_fails(self):
        app = ezShare()

        with tempfile.TemporaryDirectory() as directory:
            with patch("ezshare.list_dir", return_value=(None, None)):
                self.assertIsNone(app.calculate_total_files("http://192.168.4.1/dir?dir=A:", pathlib.Path(directory), False))


if __name__ == "__main__":
    unittest.main()
