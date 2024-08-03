import subprocess
import logging
import time

logger = logging.getLogger(__name__)

def get_interface_name():
    get_interface_cmd = 'networksetup -listallhardwareports'
    try:
        result = subprocess.run(get_interface_cmd, shell=True, capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        for index, line in enumerate(lines):
            if 'Wi-Fi' in line and (index + 1 < len(lines)):
                next_line_parts = lines[index + 1].split(':')
                if len(next_line_parts) == 2:
                    return next_line_parts[1].strip()
        logger.error("No Wi-Fi interface found or incorrect parsing.")
        raise RuntimeError("No Wi-Fi interface found or incorrect parsing.")
    except subprocess.CalledProcessError as e:
        logger.error(f'Failed to list hardware ports. Error: {e.stderr}')
        raise RuntimeError(f'Failed to list hardware ports. Error: {e.stderr}')

def connect_to_wifi(ezshare):
    interface_name = get_interface_name()
    if not interface_name:
        raise RuntimeError("Unable to obtain Wi-Fi interface name.")
    
    connect_cmd = f'networksetup -setairportnetwork {interface_name} "{ezshare.ssid}" "{ezshare.psk}"'
    try:
        result = subprocess.run(connect_cmd, shell=True, capture_output=True, text=True, check=True)
        if 'Failed' in result.stdout or result.returncode != 0:
            raise RuntimeError(f'Error connecting to {ezshare.ssid}. Message: {result.stdout}')
        ezshare.interface_name = interface_name
        ezshare.connection_id = ezshare.ssid
        ezshare.connected = True
    except subprocess.CalledProcessError as e:
        logger.error(f'Failed to connect to Wi-Fi {ezshare.ssid}. Error: {e.stderr}')
        raise RuntimeError(f'Failed to connect to Wi-Fi {ezshare.ssid}. Error: {e.stderr}')

def disconnect_from_wifi(ezshare):
    if not ezshare.connected:
        logger.debug("No active connection to disconnect.")
        return  # If there's no active connection, exit early

    if not ezshare.connection_id or not ezshare.interface_name:
        logger.error("Attempt to disconnect without a valid connection ID or interface name.")
        return  # Early exit if there's no connection ID or interface name

    logger.debug(f"Attempting to disconnect: Interface: {ezshare.interface_name}, Connection ID: {ezshare.connection_id}")

    profile_cmd = f'networksetup -removepreferredwirelessnetwork {ezshare.interface_name} "{ezshare.connection_id}"'
    try:
        subprocess.run(profile_cmd, shell=True, capture_output=True, text=True, check=True)
        subprocess.run(f'networksetup -setairportpower {ezshare.interface_name} off', shell=True, check=True)
        time.sleep(0.5)  # Delay to ensure the interface is powered down properly
        subprocess.run(f'networksetup -setairportpower {ezshare.interface_name} on', shell=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f'Error toggling Wi-Fi interface power. Return code: {e.returncode}, error: {e.stderr}')
        raise RuntimeError(f'Error toggling Wi-Fi interface power. Return code: {e.returncode}, error: {e.stderr}')
    finally:
        ezshare.connected = False
        ezshare.connection_id = None  # Reset connection ID only after successful disconnect

    logger.info("Disconnected successfully from Wi-Fi.")

def wifi_connected(ezshare):
    return ezshare.connected
