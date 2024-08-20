import os
import subprocess
import logging
import threading

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
            # First, try to remove the specific SSID from the preferred networks
            remove_command = [
                "networksetup", "-removepreferredwirelessnetwork", interface, ssid
            ]
            result = subprocess.run(remove_command, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Failed to remove SSID {ssid} from preferred networks: {result.stderr}")
                return False

            # Now explicitly disconnect from the current Wi-Fi network
            disconnect_command = [
                "networksetup", "-setairportpower", interface, "off"
            ]
            result = subprocess.run(disconnect_command, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to turn off Wi-Fi: {result.stderr}")
                return False
            
            # Optionally turn Wi-Fi back on if you want to reset the state
            turn_on_command = [
                "networksetup", "-setairportpower", interface, "on"
            ]
            result = subprocess.run(turn_on_command, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to turn Wi-Fi back on: {result.stderr}")
                return False

            logger.info(f"Wi-Fi disconnected successfully from SSID={ssid} on interface={interface}.")
            return True

        except Exception as e:
            logger.exception(f"Exception during Wi-Fi disconnection: {e}")
            return False

def reset_wifi_configuration(interface):
    with connection_lock:
        logger.debug(f"Resetting Wi-Fi configuration for interface {interface}.")
        if not interface:
            logger.error("No Wi-Fi interface provided. Cannot reset Wi-Fi configuration.")
            raise RuntimeError("Cannot reset Wi-Fi configuration: No interface provided.")

        try:
            subprocess.run(["networksetup", "-setairportpower", interface, "off"])
            subprocess.run(["networksetup", "-setairportpower", interface, "on"])
            logger.info(f"Wi-Fi configuration reset successfully on interface {interface}.")
        except Exception as e:
            logger.exception(f"Exception during Wi-Fi reset: {e}")
            raise RuntimeError(f"Exception during Wi-Fi reset: {e}")
