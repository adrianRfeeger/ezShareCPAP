import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cli
import main


class FakeEzShare:
    instances = []

    def __init__(self):
        self.params = None
        self.status_callback = None
        self.progress_callback = None
        FakeEzShare.instances.append(self)

    def set_status_callback(self, callback):
        self.status_callback = callback

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def set_params(self, **kwargs):
        self.params = kwargs

    def run(self):
        if self.status_callback:
            self.status_callback("fake sync complete")
        return True

    def stop(self):
        pass


class CliTests(unittest.TestCase):
    def setUp(self):
        FakeEzShare.instances = []

    def test_main_dispatches_to_gui_by_default(self):
        with patch("main.run_gui", return_value=0) as run_gui:
            self.assertEqual(main.main([]), 0)

        run_gui.assert_called_once_with()

    def test_main_dispatches_sync_to_cli(self):
        with patch("cli.run_cli", return_value=0) as run_cli:
            self.assertEqual(main.main(["sync", "--quiet"]), 0)

        run_cli.assert_called_once_with(["--quiet"])

    def test_main_dispatches_cli_alias_to_cli(self):
        with patch("cli.run_cli", return_value=0) as run_cli:
            self.assertEqual(main.main(["--cli", "--quiet"]), 0)

        run_cli.assert_called_once_with(["--quiet"])

    def test_cli_uses_config_and_argument_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_path = tmpdir_path / "config.json"
            output_path = tmpdir_path / "output"
            config_path.write_text(
                json.dumps(
                    {
                        "Settings": {
                            "path": str(tmpdir_path / "configured"),
                            "url": "http://configured.example/dir?dir=A:",
                            "import_oscar": False,
                            "quit_after_completion": False,
                        },
                        "WiFi": {
                            "ssid": "configured ssid",
                            "psk": "configured psk",
                        },
                        "Window": {
                            "x": 100,
                            "y": 100,
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch("cli.ezShare", FakeEzShare):
                exit_code = cli.run_cli(
                    [
                        "--config",
                        str(config_path),
                        "--path",
                        str(output_path),
                        "--ssid",
                        "cli ssid",
                        "--ignore",
                        "A,B",
                        "--ignore",
                        "C",
                        "--retries",
                        "2",
                        "--connection-delay",
                        "0",
                        "--quiet",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(FakeEzShare.instances), 1)
        params = FakeEzShare.instances[0].params
        self.assertEqual(params["path"], output_path)
        self.assertEqual(params["url"], "http://configured.example/dir?dir=A:")
        self.assertEqual(params["ssid"], "cli ssid")
        self.assertEqual(params["psk"], "configured psk")
        self.assertEqual(params["ignore"], ["A", "B", "C"])
        self.assertEqual(params["retries"], 2)
        self.assertEqual(params["connection_delay"], 0)
        self.assertFalse(params["overwrite"])

    def test_cli_save_config_persists_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_path = tmpdir_path / "config.json"
            output_path = tmpdir_path / "output"

            with patch("cli.ezShare", FakeEzShare):
                exit_code = cli.run_cli(
                    [
                        "--config",
                        str(config_path),
                        "--path",
                        str(output_path),
                        "--url",
                        "http://192.168.4.1/dir?dir=B:",
                        "--ssid",
                        "new ssid",
                        "--psk",
                        "new psk",
                        "--save-config",
                        "--quiet",
                    ]
                )

            saved = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(saved["Settings"]["path"], str(output_path))
        self.assertEqual(saved["Settings"]["url"], "http://192.168.4.1/dir?dir=B:")
        self.assertEqual(saved["WiFi"]["ssid"], "new ssid")
        self.assertEqual(saved["WiFi"]["psk"], "new psk")


if __name__ == "__main__":
    unittest.main()
