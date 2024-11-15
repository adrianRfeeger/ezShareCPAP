import subprocess
import logging
import threading

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.connection_lock = threading.Lock()
        self.interface = None
        self.connected = False

    def find_wifi_interface(self):
        logger.debug("Finding Wi-Fi interface.")
        try:
            result = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True
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
            logger.exception(f"Exception during Wi-Fi interface lookup: {e}")
            return False

    def connect(self, ssid, psk):
        with self.connection_lock:
            logger.debug(f"Starting Wi-Fi connection process: SSID={ssid}")
            if not self.interface and not self.find_wifi_interface():
                logger.error("No Wi-Fi interface found. Cannot connect to Wi-Fi.")
                raise RuntimeError("Failed to find a Wi-Fi interface for connection.")

            try:
                command = [
                    "networksetup", "-setairportnetwork", self.interface, ssid, psk
                ]
                result = subprocess.run(command, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Wi-Fi connected successfully to SSID={ssid} on interface={self.interface}.")
                    self.connected = True
                else:
                    logger.error(f"Wi-Fi connection failed: {result.stderr}")
                    raise RuntimeError(f"Wi-Fi connection failed: {result.stderr}")
            except Exception as e:
                logger.exception(f"Exception during Wi-Fi connection: {e}")
                raise RuntimeError(f"Exception during Wi-Fi connection: {e}")

    def disconnect(self, ssid):
        with self.connection_lock:
            logger.debug(f"Attempting to disconnect from Wi-Fi SSID={ssid} on interface={self.interface}")
            if not self.interface:
                logger.error("No Wi-Fi interface provided. Cannot disconnect from Wi-Fi.")
                return False

            try:
                # Remove the specific SSID from the preferred networks
                remove_command = [
                    "networksetup", "-removepreferredwirelessnetwork", self.interface, ssid
                ]
                subprocess.run(remove_command, capture_output=True, text=True)

                # Turn off Wi-Fi to disconnect
                disconnect_command = [
                    "networksetup", "-setairportpower", self.interface, "off"
                ]
                subprocess.run(disconnect_command, capture_output=True, text=True)

                # Turn Wi-Fi back on to reconnect to the previous network
                turn_on_command = [
                    "networksetup", "-setairportpower", self.interface, "on"
                ]
                subprocess.run(turn_on_command, capture_output=True, text=True)

                logger.info(f"Wi-Fi disconnected and reconnected successfully from SSID={ssid} on interface={self.interface}.")
                self.connected = False
                return True
            except Exception as e:
                logger.exception(f"Exception during Wi-Fi disconnection: {e}")
                return False

    def verify_connection(self, max_attempts=10):
        logger.debug(f"Verifying Wi-Fi connection on interface {self.interface} by pinging 192.168.4.1.")
        attempt_count = 0
        while attempt_count < max_attempts:
            try:
                ping_command = ["ping", "-c", "2", "192.168.4.1"]
                result = subprocess.run(ping_command, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Ping successful on interface {self.interface}. Connection verified.")
                    return True
                else:
                    logger.warning(f"Ping failed (attempt {attempt_count + 1}/{max_attempts}): {result.stderr}")
                    attempt_count += 1
                    continue
            except Exception as e:
                logger.exception(f"Exception during ping (attempt {attempt_count + 1}/{max_attempts}): {e}")
                attempt_count += 1
                continue

        logger.error(f"Failed to verify connection after {max_attempts} attempts.")
        return False

