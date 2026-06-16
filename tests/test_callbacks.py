import unittest
from types import SimpleNamespace
from unittest.mock import patch

from callbacks import Callbacks


class OscarDownloadLinkTests(unittest.TestCase):
    def test_download_oscar_link_opens_when_link_state_is_enabled(self):
        callbacks = Callbacks.__new__(Callbacks)
        callbacks.app = SimpleNamespace(
            button_states={
                "download_oscar_link": {"enabled": True, "default": True, "visible": True}
            }
        )

        with patch("callbacks.webbrowser.open") as browser_open:
            callbacks.open_oscar_download_page()

        browser_open.assert_called_once_with("https://www.sleepfiles.com/OSCAR/")

    def test_download_oscar_link_does_not_use_missing_open_oscar_state(self):
        callbacks = Callbacks.__new__(Callbacks)
        callbacks.app = SimpleNamespace(
            button_states={
                "download_oscar_link": {"enabled": True, "default": True, "visible": True},
                "open_oscar": {"enabled": False, "default": False, "visible": True},
            }
        )

        with patch("callbacks.webbrowser.open") as browser_open:
            callbacks.open_oscar_download_page()

        browser_open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
