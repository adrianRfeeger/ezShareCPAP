# wifi_utils.py
import os
import subprocess
import logging
import threading
import time
import platform
import tempfile
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.connection_lock = threading.Lock()
        self.interface = None
        self.connected = False
        self.system = platform.system()
        self.windows_profile_name = None
        self.windows_host_route = None

    def find_wifi_interface(self):
        logger.debug(f"Finding Wi-Fi interface on {self.system}.")
        try:
            if self.system == 'Darwin':  # macOS
                return self._find_wifi_interface_macos()
            elif self.system == 'Windows':
                return self._find_wifi_interface_windows()
            else:  # Linux
                return self._find_wifi_interface_linux()
        except Exception as e:
            logger.exception(f"Exception during Wi-Fi interface lookup: {e}")
            return False

    def _find_wifi_interface_macos(self):
        """Find Wi-Fi interface on macOS."""
        try:
            result = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            lines = iter(output.splitlines())
            for line in lines:
                if "Wi-Fi" in line:
                    next_line = next(lines)
                    self.interface = next_line.split(": ")[1]
                    logger.info(f"Wi-Fi interface found: {self.interface}")
                    return True
            logger.error("Wi-Fi interface not found.")
            return False
        except Exception as e:
            logger.exception(f"Error finding macOS Wi-Fi interface: {e}")
            return False

    def _find_wifi_interface_windows(self):
        """Find Wi-Fi interface on Windows."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    "Get-NetAdapter -Physical | "
                    "Where-Object {"
                    "$_.Status -ne 'Disabled' -and "
                    "($_.NdisPhysicalMedium -eq 'Native 802.11' -or "
                    "$_.InterfaceDescription -match 'Wireless|Wi-Fi|WiFi|802.11' -or "
                    "$_.Name -match 'Wireless|Wi-Fi|WiFi')"
                    "} | Select-Object -First 1 -ExpandProperty Name",
                ],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.interface = result.stdout.strip()
                logger.info(f"Wi-Fi interface found: {self.interface}")
                return True
            if result.stderr.strip():
                logger.debug(f"PowerShell Wi-Fi interface lookup failed: {result.stderr.strip()}")
        except Exception as e:
            logger.debug(f"PowerShell Wi-Fi interface lookup failed: {e}")

        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.strip().lower().startswith("name"):
                        self.interface = line.split(":", 1)[1].strip()
                        logger.info(f"Wi-Fi interface found: {self.interface}")
                        return True
            else:
                error = (result.stderr or result.stdout).strip()
                if error:
                    logger.debug(f"netsh wlan show interfaces failed: {error}")
        except Exception as e:
            logger.debug(f"netsh wlan show interfaces failed: {e}")

        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "drivers"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.strip().lower().startswith("interface name"):
                        self.interface = line.split(":", 1)[1].strip()
                        logger.info(f"Wi-Fi interface found: {self.interface}")
                        return True
            else:
                error = (result.stderr or result.stdout).strip()
                if error:
                    logger.debug(f"netsh wlan show drivers failed: {error}")
        except Exception as e:
            logger.debug(f"netsh wlan show drivers failed: {e}")

        logger.error("Wi-Fi interface not found on Windows.")
        return False

    def _find_wifi_interface_linux(self):
        """Find Wi-Fi interface on Linux."""
        try:
            # Prefer NetworkManager because the connect path uses nmcli.
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        parts = line.split(":")
                        if len(parts) >= 2 and parts[1] == "wifi":
                            self.interface = parts[0]
                            logger.info(f"Wi-Fi interface found: {self.interface}")
                            return True
            except FileNotFoundError:
                logger.debug("nmcli not found while looking up Linux Wi-Fi interface.")

            # Try to find wireless interface using iwconfig.
            result = subprocess.run(
                ["bash", "-c", "iwconfig 2>/dev/null | awk '/IEEE 802.11/ {print $1; exit}'"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.interface = result.stdout.strip()
                logger.info(f"Wi-Fi interface found: {self.interface}")
                return True
            
            # Fallback: try ip command
            result = subprocess.run(
                ["bash", "-c", "ip link show | grep -E 'wl[a-z0-9]+' | awk '{print $2}' | tr -d ':' | head -1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.interface = result.stdout.strip()
                logger.info(f"Wi-Fi interface found: {self.interface}")
                return True
            
            logger.error("Wi-Fi interface not found on Linux.")
            return False
        except Exception as e:
            logger.exception(f"Error finding Linux Wi-Fi interface: {e}")
            return False

    def connect(self, ssid, psk, target_host="192.168.4.1"):
        with self.connection_lock:
            logger.debug(f"Starting Wi-Fi connection process on {self.system}: SSID={ssid}")
            if not self.interface and not self.find_wifi_interface():
                logger.error("No Wi-Fi interface found. Cannot connect to Wi-Fi.")
                raise RuntimeError("Failed to find a Wi-Fi interface for connection.")

            try:
                if self.system == 'Darwin':  # macOS
                    self._connect_macos(ssid, psk)
                elif self.system == 'Windows':
                    self._connect_windows(ssid, psk)
                    self._ensure_windows_host_route(target_host)
                else:  # Linux
                    self._connect_linux(ssid, psk)
                
                logger.info(f"Wi-Fi connected successfully to SSID={ssid} on interface={self.interface}.")
                self.connected = True
            except Exception as e:
                logger.exception(f"Exception during Wi-Fi connection: {e}")
                raise RuntimeError(f"Wi-Fi connection failed: {e}")

    def _connect_macos(self, ssid, psk):
        """Connect to Wi-Fi on macOS."""
        command = [
            "networksetup", "-setairportnetwork", self.interface, ssid, psk
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise RuntimeError(f"macOS Wi-Fi connection failed: {result.stderr}")

    def _connect_windows(self, ssid, psk):
        """Connect to Wi-Fi on Windows."""
        if self._windows_profile_exists(ssid):
            result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={ssid}", f"ssid={ssid}", f"interface={self.interface}"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                self.windows_profile_name = None
                return
            raise RuntimeError(
                f"Failed to connect with existing Windows WLAN profile '{ssid}': {self._command_error(result)}"
            )

        profile_name = f"ezShareCPAP-{ssid}"
        escaped_profile_name = escape(profile_name)
        escaped_ssid = escape(ssid)
        escaped_psk = escape(psk)
        ssid_hex = ssid.encode("utf-8").hex().upper()
        if psk:
            security_xml = f"""            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{escaped_psk}</keyMaterial>
            </sharedKey>"""
        else:
            security_xml = """            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>"""

        # Create a temporary WLAN XML profile compatible with netsh.
        profile_xml = f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{escaped_profile_name}</name>
    <SSIDConfig>
        <SSID>
            <hex>{ssid_hex}</hex>
            <name>{escaped_ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
{security_xml}
        </security>
    </MSM>
</WLANProfile>'''
        
        profile_path = None
        profile_added = False
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                f.write(profile_xml)
                profile_path = f.name
            
            # Add WLAN profile
            result = subprocess.run(
                [
                    "netsh",
                    "wlan",
                    "add",
                    "profile",
                    f"filename={profile_path}",
                    f"interface={self.interface}",
                    "user=current",
                ],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to add profile: {self._command_error(result)}")
            self.windows_profile_name = profile_name
            profile_added = True
            
            # Connect to network
            result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={profile_name}", f"ssid={ssid}", f"interface={self.interface}"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to connect: {self._command_error(result)}")
        except Exception as e:
            if profile_added:
                self._delete_windows_profile(profile_name)
                self.windows_profile_name = None
            raise RuntimeError(f"Windows Wi-Fi connection failed: {e}")
        finally:
            if profile_path:
                try:
                    os.unlink(profile_path)
                except OSError:
                    logger.warning("Could not remove temporary Windows WLAN profile file.")

    def _windows_profile_exists(self, profile_name):
        result = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            logger.debug(f"Could not list Windows WLAN profiles: {self._command_error(result)}")
            return False

        for line in result.stdout.splitlines():
            if ":" in line and line.split(":", 1)[1].strip() == profile_name:
                return True
        return False

    def _ensure_windows_host_route(self, target_host):
        """Force ez Share card traffic over Wi-Fi when Ethernet has the preferred default route."""
        if not target_host or not self.interface:
            return

        escaped_interface = self.interface.replace("'", "''")
        escaped_target = target_host.replace("'", "''")
        command = f"""
$adapter = Get-NetAdapter -Name '{escaped_interface}' -ErrorAction Stop
$ip = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction Stop |
    Where-Object {{ $_.IPAddress -ne '169.254.0.0' }} |
    Select-Object -First 1
if (-not $ip) {{
    throw 'No IPv4 address found on Wi-Fi adapter.'
}}
$destination = '{escaped_target}/32'
$existing = Get-NetRoute -DestinationPrefix $destination -ErrorAction SilentlyContinue |
    Where-Object {{ $_.InterfaceIndex -eq $adapter.ifIndex -and $_.NextHop -eq '0.0.0.0' }} |
    Select-Object -First 1
if (-not $existing) {{
    New-NetRoute -DestinationPrefix $destination -InterfaceIndex $adapter.ifIndex -NextHop '0.0.0.0' -RouteMetric 1 -PolicyStore ActiveStore | Out-Null
    'added'
}} else {{
    'exists'
}}
"""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode != 0:
            logger.warning(f"Could not add Windows Wi-Fi host route for {target_host}: {self._command_error(result)}")
            return

        self.windows_host_route = target_host if "added" in result.stdout else None
        logger.info(f"Windows Wi-Fi host route for {target_host}: {result.stdout.strip()}")

    def _remove_windows_host_route(self):
        if not self.windows_host_route:
            return

        escaped_interface = self.interface.replace("'", "''")
        escaped_target = self.windows_host_route.replace("'", "''")
        command = f"""
$adapter = Get-NetAdapter -Name '{escaped_interface}' -ErrorAction Stop
$route = Get-NetRoute -DestinationPrefix '{escaped_target}/32' -ErrorAction SilentlyContinue |
    Where-Object {{ $_.InterfaceIndex -eq $adapter.ifIndex -and $_.NextHop -eq '0.0.0.0' }}
if ($route) {{
    $route | Remove-NetRoute -Confirm:$false
}}
"""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode != 0:
            logger.warning(f"Could not remove Windows Wi-Fi host route for {self.windows_host_route}: {self._command_error(result)}")
        self.windows_host_route = None

    def _connect_linux(self, ssid, psk):
        """Connect to Wi-Fi on Linux using NetworkManager."""
        try:
            command = ["nmcli", "dev", "wifi", "connect", ssid]
            if psk:
                command.extend(["password", psk])
            if self.interface:
                command.extend(["ifname", self.interface])

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                return
            
            error = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(
                f"nmcli connection failed: {error}. Ensure NetworkManager is installed and running."
            )
        except FileNotFoundError:
            raise RuntimeError("nmcli not found. Please install NetworkManager (sudo apt install network-manager on Debian/Ubuntu)")
        except Exception as e:
            raise RuntimeError(f"Linux Wi-Fi connection failed: {e}")

    def disconnect(self, ssid):
        with self.connection_lock:
            logger.debug(f"Attempting to disconnect from Wi-Fi SSID={ssid} on {self.system}")
            if not self.interface:
                logger.error("No Wi-Fi interface provided. Cannot disconnect from Wi-Fi.")
                return False

            try:
                if self.system == 'Darwin':  # macOS
                    self._disconnect_macos()
                elif self.system == 'Windows':
                    self._disconnect_windows(ssid)
                else:  # Linux
                    self._disconnect_linux(ssid)
                
                logger.info(f"Wi-Fi disconnected successfully from SSID={ssid} on interface={self.interface}.")
                self.connected = False
                return True
            except Exception as e:
                logger.exception(f"Exception during Wi-Fi disconnection: {e}")
                return False

    def _disconnect_macos(self):
        """Disconnect Wi-Fi on macOS."""
        disconnect_command = ["networksetup", "-setairportpower", self.interface, "off"]
        subprocess.run(disconnect_command, capture_output=True, text=True, timeout=10)
        
        turn_on_command = ["networksetup", "-setairportpower", self.interface, "on"]
        subprocess.run(turn_on_command, capture_output=True, text=True, timeout=10)

    def _disconnect_windows(self, ssid):
        """Disconnect Wi-Fi on Windows."""
        self._remove_windows_host_route()
        subprocess.run(
            ["netsh", "wlan", "disconnect", f"interface={self.interface}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        profile_name = self.windows_profile_name or f"ezShareCPAP-{ssid}"
        self._delete_windows_profile(profile_name)
        self.windows_profile_name = None

    def _delete_windows_profile(self, profile_name):
        """Delete the temporary app-managed Windows WLAN profile."""
        subprocess.run(
            ["netsh", "wlan", "delete", "profile", f"name={profile_name}", f"interface={self.interface}"],
            capture_output=True,
            text=True,
            timeout=10
        )

    @staticmethod
    def _command_error(result):
        return result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"

    def _disconnect_linux(self, ssid):
        """Disconnect Wi-Fi on Linux."""
        commands = [
            ["nmcli", "con", "down", "id", ssid],
            ["nmcli", "dev", "disconnect", self.interface],
        ]
        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return
            except FileNotFoundError:
                logger.warning("nmcli not found while disconnecting.")
                return
            except Exception as e:
                logger.warning(f"Could not disconnect using {' '.join(command)}: {e}")

    def verify_connection(self, max_attempts=10):
        logger.debug(f"Verifying Wi-Fi connection on {self.system} by pinging 192.168.4.1.")
        attempt_count = 0
        while attempt_count < max_attempts:
            # Wait briefly before each attempt
            time.sleep(1)
            try:
                if self.system == 'Windows':
                    ping_command = ["ping", "-n", "2", "192.168.4.1"]
                else:  # macOS and Linux
                    ping_command = ["ping", "-c", "2", "192.168.4.1"]
                
                result = subprocess.run(ping_command, capture_output=True, text=True, timeout=5)

                if result.returncode == 0:
                    logger.info(f"Ping successful on interface {self.interface}. Connection verified.")
                    return True
                else:
                    logger.warning(f"Ping failed (attempt {attempt_count + 1}/{max_attempts}): {result.stderr}")
                    attempt_count += 1
                    continue
            except subprocess.TimeoutExpired:
                logger.warning(f"Ping timed out (attempt {attempt_count + 1}/{max_attempts}).")
                attempt_count += 1
                continue
            except Exception as e:
                logger.warning(f"Ping failed with exception (attempt {attempt_count + 1}/{max_attempts}): {e}")
                attempt_count += 1
                continue

        logger.error(f"Failed to verify connection after {max_attempts} attempts.")
        return False
