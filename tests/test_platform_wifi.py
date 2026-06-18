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
    def test_macos_disconnect_forgets_network_power_cycles_and_verifies_ssid(self):
        manager = ConnectionManager()
        manager.interface = "en0"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if command == ["networksetup", "-getairportnetwork", "en0"]:
                return completed(command, stdout="You are not associated with an AirPort network.\n")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run), patch("wifi_utils.time.sleep"):
            manager._disconnect_macos("ez Share")

        self.assertEqual(
            commands,
            [
                ["networksetup", "-removepreferredwirelessnetwork", "en0", "ez Share"],
                ["networksetup", "-setairportpower", "en0", "off"],
                ["networksetup", "-setairportpower", "en0", "on"],
                ["networksetup", "-getairportnetwork", "en0"],
            ],
        )

    def test_macos_disconnect_fails_when_wifi_rejoins_target_ssid(self):
        manager = ConnectionManager()
        manager.interface = "en0"

        def fake_run(command, **kwargs):
            if command == ["networksetup", "-getairportnetwork", "en0"]:
                return completed(command, stdout="Current Wi-Fi Network: ez Share\n")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run), patch("wifi_utils.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "still connected to SSID 'ez Share'"):
                manager._disconnect_macos("ez Share")

    def test_macos_disconnect_treats_authorization_error_as_failure(self):
        manager = ConnectionManager()
        manager.interface = "en0"

        def fake_run(command, **kwargs):
            if command == ["networksetup", "-setairportpower", "en0", "off"]:
                return completed(command, stdout="AuthorizationCreate() failed: -60008\n")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run), patch("wifi_utils.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "power-off failed"):
                manager._disconnect_macos("ez Share")

    def test_macos_current_ssid_parses_legacy_airport_label(self):
        manager = ConnectionManager()
        manager.interface = "en0"

        with patch(
            "wifi_utils.subprocess.run",
            return_value=completed(["networksetup"], stdout="Current AirPort Network: ez Share\n"),
        ):
            self.assertEqual(manager._macos_current_ssid(), "ez Share")

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

        self.assertEqual(commands[0], ["netsh", "wlan", "show", "profiles"])
        self.assertEqual(commands[1][:4], ["netsh", "wlan", "add", "profile"])
        self.assertIn("interface=Wi-Fi", commands[1])
        self.assertIn("user=current", commands[1])
        self.assertEqual(
            commands[2],
            [
                "netsh",
                "wlan",
                "connect",
                "name=ezShareCPAP-ez Share & Test",
                "ssid=ez Share & Test",
                "interface=Wi-Fi",
            ],
        )
        self.assertIn("<MSM>", profile_xml["content"])
        self.assertIn("<encryption>AES</encryption>", profile_xml["content"])
        self.assertIn("<name>ezShareCPAP-ez Share &amp; Test</name>", profile_xml["content"])
        self.assertIn("<name>ez Share &amp; Test</name>", profile_xml["content"])
        self.assertIn("<keyMaterial>pass&lt;word&gt;&amp;</keyMaterial>", profile_xml["content"])
        self.assertFalse(profile_path["path"].exists())

    def test_windows_connect_uses_existing_profile_when_available(self):
        manager = ConnectionManager()
        manager.interface = "Wi-Fi"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if command == ["netsh", "wlan", "show", "profiles"]:
                return completed(command, stdout="All User Profile     : ez Share\n")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            manager._connect_windows("ez Share", "88888888")

        self.assertEqual(
            commands,
            [
                ["netsh", "wlan", "show", "profiles"],
                ["netsh", "wlan", "connect", "name=ez Share", "ssid=ez Share", "interface=Wi-Fi"],
            ],
        )
        self.assertIsNone(manager.windows_profile_name)

    def test_windows_connect_adds_host_route_for_target_host(self):
        manager = ConnectionManager()
        manager.interface = "Wi-Fi"
        manager.system = "Windows"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if command == ["netsh", "wlan", "show", "profiles"]:
                return completed(command, stdout="All User Profile     : ez Share\n")
            if command[:4] == ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass"]:
                return completed(command, stdout="added\n")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            manager.connect("ez Share", "88888888", target_host="192.168.4.1")

        self.assertTrue(any("New-NetRoute" in command[-1] for command in commands if command[0] == "powershell"))
        self.assertEqual(manager.windows_host_route, "192.168.4.1")

    def test_windows_disconnect_removes_added_host_route(self):
        manager = ConnectionManager()
        manager.interface = "Wi-Fi"
        manager.windows_host_route = "192.168.4.1"
        commands = []

        with patch("wifi_utils.subprocess.run", side_effect=lambda command, **kwargs: commands.append(command) or completed(command)):
            manager._disconnect_windows("ez Share")

        self.assertTrue(any("Remove-NetRoute" in command[-1] for command in commands if command[0] == "powershell"))
        self.assertIsNone(manager.windows_host_route)

    def test_windows_existing_profile_failure_does_not_try_to_create_profile(self):
        manager = ConnectionManager()
        manager.interface = "Wi-Fi"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if command == ["netsh", "wlan", "show", "profiles"]:
                return completed(command, stdout="All User Profile     : ez Share\n")
            return completed(command, returncode=1, stdout="network not available")

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError, "existing Windows WLAN profile"):
                manager._connect_windows("ez Share", "88888888")

        self.assertEqual(
            commands,
            [
                ["netsh", "wlan", "show", "profiles"],
                ["netsh", "wlan", "connect", "name=ez Share", "ssid=ez Share", "interface=Wi-Fi"],
            ],
        )

    def test_windows_disconnect_removes_only_app_profile(self):
        manager = ConnectionManager()
        manager.interface = "Wi-Fi"
        manager.windows_profile_name = "ezShareCPAP-ez Share"
        commands = []

        with patch("wifi_utils.subprocess.run", side_effect=lambda command, **kwargs: commands.append(command) or completed(command)):
            manager._disconnect_windows("ez Share")

        self.assertEqual(
            commands,
            [
                ["netsh", "wlan", "disconnect", "interface=Wi-Fi"],
                ["netsh", "wlan", "delete", "profile", "name=ezShareCPAP-ez Share", "interface=Wi-Fi"],
            ],
        )
        self.assertIsNone(manager.windows_profile_name)

    def test_windows_connect_failure_removes_app_profile(self):
        manager = ConnectionManager()
        manager.interface = "Wi-Fi"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if command[:4] == ["netsh", "wlan", "connect", "name=ezShareCPAP-ez Share"]:
                return completed(command, returncode=1, stderr="network not available")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError, "Windows Wi-Fi connection failed"):
                manager._connect_windows("ez Share", "88888888")

        self.assertIn(
            ["netsh", "wlan", "delete", "profile", "name=ezShareCPAP-ez Share", "interface=Wi-Fi"],
            commands,
        )
        self.assertIsNone(manager.windows_profile_name)

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

    def test_windows_find_wifi_interface_falls_back_to_netsh_drivers(self):
        manager = ConnectionManager()

        with patch(
            "wifi_utils.subprocess.run",
            side_effect=[
                completed(["powershell"], returncode=1, stderr="Access denied"),
                completed(["netsh"], returncode=1, stdout="requires elevation"),
                completed(
                    ["netsh"],
                    stdout="""
Interface name: Wi-Fi

    Driver                    : Realtek Wireless LAN 802.11ac PCI-E NIC
    Type                      : Native Wi-Fi Driver
""",
                ),
            ],
        ) as run:
            self.assertTrue(manager._find_wifi_interface_windows())

        self.assertEqual(manager.interface, "Wi-Fi")
        self.assertIn("-NoProfile", run.call_args_list[0].args[0])
        self.assertIn("-ExecutionPolicy", run.call_args_list[0].args[0])

    def test_windows_find_wifi_interface_continues_after_powershell_timeout(self):
        manager = ConnectionManager()

        with patch(
            "wifi_utils.subprocess.run",
            side_effect=[
                subprocess.TimeoutExpired(["powershell"], timeout=5),
                completed(["netsh"], returncode=1, stdout="requires elevation"),
                completed(["netsh"], stdout="Interface name: Wi-Fi\n"),
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

    def test_linux_connect_creates_explicit_wpa_profile_with_interface(self):
        manager = ConnectionManager()
        manager.interface = "wlan0"
        commands = []

        with patch("wifi_utils.subprocess.run", side_effect=lambda command, **kwargs: commands.append(command) or completed(command)):
            manager._connect_linux("ez Share", "88888888")

        self.assertEqual(
            commands,
            [
                ["nmcli", "con", "delete", "id", "ezShareCPAP-ez Share"],
                [
                    "nmcli",
                    "con",
                    "add",
                    "type",
                    "wifi",
                    "ifname",
                    "wlan0",
                    "con-name",
                    "ezShareCPAP-ez Share",
                    "ssid",
                    "ez Share",
                ],
                [
                    "nmcli",
                    "con",
                    "modify",
                    "ezShareCPAP-ez Share",
                    "connection.autoconnect",
                    "no",
                    "ipv4.method",
                    "auto",
                    "ipv6.method",
                    "ignore",
                    "wifi-sec.key-mgmt",
                    "wpa-psk",
                    "wifi-sec.psk",
                    "88888888",
                ],
                ["nmcli", "con", "up", "ezShareCPAP-ez Share"],
            ],
        )
        self.assertEqual(manager.linux_profile_name, "ezShareCPAP-ez Share")

    def test_linux_connect_removes_app_profile_on_failure(self):
        manager = ConnectionManager()
        manager.interface = "wlan0"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if command == ["nmcli", "con", "up", "ezShareCPAP-ez Share"]:
                return completed(command, returncode=1, stderr="key-mgmt missing")
            return completed(command)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError, "key-mgmt missing"):
                manager._connect_linux("ez Share", "88888888")

        self.assertEqual(commands[-1], ["nmcli", "con", "delete", "id", "ezShareCPAP-ez Share"])
        self.assertIsNone(manager.linux_profile_name)

    def test_linux_disconnect_falls_back_to_device_disconnect(self):
        manager = ConnectionManager()
        manager.interface = "wlan0"
        manager.linux_profile_name = "ezShareCPAP-ez Share"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            return completed(command, returncode=1 if len(commands) < 3 else 0)

        with patch("wifi_utils.subprocess.run", side_effect=fake_run):
            manager._disconnect_linux("ez Share")

        self.assertEqual(
            commands,
            [
                ["nmcli", "con", "down", "id", "ezShareCPAP-ez Share"],
                ["nmcli", "con", "delete", "id", "ezShareCPAP-ez Share"],
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
