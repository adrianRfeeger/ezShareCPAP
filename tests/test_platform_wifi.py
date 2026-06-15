import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ez_share_config import EzShareConfig
from wifi_utils import ConnectionManager


def completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


class ConnectionManagerCommandTests(unittest.TestCase):
    def test_windows_connect_uses_valid_wlan_profile_and_interface(self):
        manager = ConnectionManager()
        manager.interface = "Wi-Fi"
        commands = []
        profile_xml = {}
        profile_path = {}

        def fake_run(command, **kwargs):
            commands.append(command)
            if command[:4] == ["netsh", "wlan", "add", "profile"]:
                filename_arg = next(arg for arg in command if arg.startswith("filename="))
                profile_path["path"] = Path(filename_arg[len("filename="):])
                profile_xml["content"] = profile_path["path"].read_text(encoding="utf-8")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            manager._connect_windows("ez Share & Test", "pass<word>&")

        self.assertEqual(commands[0][:4], ["netsh", "wlan", "add", "profile"])
        self.assertIn("interface=Wi-Fi", commands[0])
        self.assertEqual(
            commands[1],
            [
                "netsh",
                "wlan",
                "connect",
                "name=ez Share & Test",
                "ssid=ez Share & Test",
                "interface=Wi-Fi",
            ],
        )
        self.assertIn("<MSM>", profile_xml["content"])
        self.assertIn("<encryption>AES</encryption>", profile_xml["content"])
        self.assertIn("<name>ez Share &amp; Test</name>", profile_xml["content"])
        self.assertIn("<keyMaterial>pass&lt;word&gt;&amp;</keyMaterial>", profile_xml["content"])
        self.assertFalse(profile_path["path"].exists())

    def test_linux_find_wifi_interface_prefers_networkmanager(self):
        manager = ConnectionManager()

        with patch(
            "wifi_utils.subprocess.run",
            return_value=completed(
                ["nmcli"],
                stdout="lo:loopback:unmanaged\nwlan0:wifi:disconnected\n",
            ),
        ):
            self.assertTrue(manager._find_wifi_interface_linux())

        self.assertEqual(manager.interface, "wlan0")

    def test_windows_find_wifi_interface_falls_back_to_netsh(self):
        manager = ConnectionManager()

        with patch(
            "wifi_utils.subprocess.run",
            side_effect=[
                completed(["powershell"], returncode=1),
                completed(
                    ["netsh"],
                    stdout="""
There is 1 interface on the system:

    Name                   : Wi-Fi
    Description            : Wireless Adapter
""",
                ),
            ],
        ):
            self.assertTrue(manager._find_wifi_interface_windows())

        self.assertEqual(manager.interface, "Wi-Fi")

    def test_linux_find_wifi_interface_falls_back_when_nmcli_is_missing(self):
        manager = ConnectionManager()

        def fake_run(command, **kwargs):
            if command[0] == "nmcli":
                raise FileNotFoundError("nmcli")
            return completed(command, stdout="wlan1\n")

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            self.assertTrue(manager._find_wifi_interface_linux())

        self.assertEqual(manager.interface, "wlan1")

    def test_linux_connect_uses_nmcli_with_interface(self):
        manager = ConnectionManager()
        manager.interface = "wlan0"

        with patch("wifi_utils.subprocess.run", return_value=completed(["nmcli"])) as run:
            manager._connect_linux("ez Share", "88888888")

        run.assert_called_once_with(
            [
                "nmcli",
                "dev",
                "wifi",
                "connect",
                "ez Share",
                "password",
                "88888888",
                "ifname",
                "wlan0",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_linux_disconnect_falls_back_to_device_disconnect(self):
        manager = ConnectionManager()
        manager.interface = "wlan0"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            return completed(command, returncode=1 if len(commands) == 1 else 0)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            manager._disconnect_linux("ez Share")

        self.assertEqual(
            commands,
            [
                ["nmcli", "con", "down", "id", "ez Share"],
                ["nmcli", "dev", "disconnect", "wlan0"],
            ],
        )


class EzShareConfigTests(unittest.TestCase):
    def test_config_page_uses_cross_platform_browser_open(self):
        config = EzShareConfig(SimpleNamespace())

        with patch("ez_share_config.requests.get", return_value=SimpleNamespace(status_code=200)), \
                patch("ez_share_config.update_status"), \
                patch("ez_share_config.webbrowser.open") as browser_open:
            config._open_configuration_page()

        browser_open.assert_called_once_with(
            "http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356"
        )


if __name__ == "__main__":
    unittest.main()
