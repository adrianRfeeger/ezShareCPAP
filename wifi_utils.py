# wifi_utils.py
import subprocess
import logging
import threading
from status_manager import update_status

logger = logging.getLogger(__name__)
connection_lock = threading.Lock()

def find_wifi_interface():
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
                interface = next_line.split(": ")[1]
                logger.info(f"Wi-Fi interface found: {interface}")
                return interface
        logger.error("Wi-Fi interface not found.")
        return None
    except Exception as e:
        logger.exception(f"Exception during Wi-Fi interface lookup: {e}")
        return None

def connect_to_wifi(ssid, psk, interface=None):
    with connection_lock:
        logger.debug(f"Starting Wi-Fi connection process: SSID={ssid}, Interface={interface}")
        
        if interface is None:
            interface = find_wifi_interface()
        
        if not interface:
            logger.error("No Wi-Fi interface found. Cannot connect to Wi-Fi.")
            raise RuntimeError("Failed to find a Wi-Fi interface for connection.")

        try:
            command = [
                "networksetup", "-setairportnetwork", interface, ssid, psk
            ]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Wi-Fi connected successfully to SSID={ssid} on interface={interface}.")
                return interface  # Return the interface used for connection
            else:
                logger.error(f"Wi-Fi connection failed: {result.stderr}")
                raise RuntimeError(f"Wi-Fi connection failed: {result.stderr}")
        except Exception as e:
            logger.exception(f"Exception during Wi-Fi connection: {e}")
            raise RuntimeError(f"Exception during Wi-Fi connection: {e}")

def disconnect_wifi(ssid, interface):
    with connection_lock:
        logger.debug(f"Attempting to disconnect from Wi-Fi SSID={ssid} on interface={interface}.")
        
        if not interface:
            logger.error("No Wi-Fi interface provided. Cannot disconnect from Wi-Fi.")
            return False

        try:
            # Remove the specific SSID from the preferred networks
            remove_command = [
                "networksetup", "-removepreferredwirelessnetwork", interface, ssid
            ]
            result = subprocess.run(remove_command, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Failed to remove SSID {ssid} from preferred networks: {result.stderr}")
                return False

            # Turn off Wi-Fi to disconnect
            disconnect_command = [
                "networksetup", "-setairportpower", interface, "off"
            ]
            result = subprocess.run(disconnect_command, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to turn off Wi-Fi: {result.stderr}")
                return False
            
            # Turn Wi-Fi back on to reconnect to the previous network
            turn_on_command = [
                "networksetup", "-setairportpower", interface, "on"
            ]
            result = subprocess.run(turn_on_command, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to turn Wi-Fi back on: {result.stderr}")
                return False

            logger.info(f"Wi-Fi disconnected and reconnected successfully from SSID={ssid} on interface={interface}.")
            return True

        except Exception as e:
            logger.exception(f"Exception during Wi-Fi disconnection: {e}")
            return False

def verify_wifi_connection(interface):
    logger.debug(f"Verifying Wi-Fi connection on interface {interface} by pinging 192.168.4.1.")
    try:
        # Remove the interface specification from the ping command
        ping_command = ["ping", "-c", "2", "192.168.4.1"]
        result = subprocess.run(ping_command, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"Ping successful on interface {interface}. Connection verified.")
            return True
        else:
            logger.error(f"Ping failed: {result.stderr}")
            return False
    except Exception as e:
        logger.exception(f"Exception during ping: {e}")
        return False

def connect_and_verify_wifi(ssid, psk):
    """
    Centralised function to connect to Wi-Fi, verify the connection, and handle errors.
    
    :param ssid: SSID of the Wi-Fi network.
    :param psk: Pre-shared key for the Wi-Fi network.
    :return: Interface name if connected and verified, None otherwise.
    """
    update_status(None, 'Connecting to Wi-Fi...', 'info')
    interface = find_wifi_interface()
    if not interface:
        update_status(None, 'No Wi-Fi interface found. Cannot connect.', 'error')
        return None

    try:
        connect_to_wifi(ssid, psk, interface)
        update_status(None, f'Connected to {ssid}. Verifying connection...', 'info')

        # Verify the connection using ping
        if verify_wifi_connection(interface):
            update_status(None, f'Wi-Fi connection to {ssid} verified successfully.', 'info')
            return interface
        else:
            update_status(None, 'Wi-Fi connection verification failed.', 'error')
            disconnect_wifi(ssid, interface)
            return None
    except RuntimeError as e:
        update_status(None, f'Error connecting to {ssid}: {e}', 'error')
        return None
    except Exception as e:
        logger.exception(f"Unexpected error during Wi-Fi connection: {e}")
        update_status(None, f'Unexpected error: {e}', 'error')
        return None

def reset_wifi_configuration(interface):
    """
    Reset the Wi-Fi configuration by toggling the Wi-Fi off and on again.

    :param interface: The interface used for the Wi-Fi connection.
    :return: None
    """
    with connection_lock:
        logger.debug(f"Resetting Wi-Fi configuration for interface {interface}.")
        if not interface:
            logger.error("No Wi-Fi interface provided. Cannot reset Wi-Fi configuration.")
            raise RuntimeError("Cannot reset Wi-Fi configuration: No interface provided.")

        try:
            # Turn off Wi-Fi
            subprocess.run(["networksetup", "-setairportpower", interface, "off"])
            
            # Turn Wi-Fi back on to reconnect to the previous network
            subprocess.run(["networksetup", "-setairportpower", interface, "on"])
            
            logger.info(f"Wi-Fi configuration reset successfully on interface {interface}.")
        except Exception as e:
            logger.exception(f"Exception during Wi-Fi reset: {e}")
            raise RuntimeError(f"Exception during Wi-Fi reset: {e}")
