import subprocess
import logging

logger = logging.getLogger(__name__)

def connect_to_wifi(ezshare):
    """
    Connect to the specified Wi-Fi network.
    """
    get_interface_cmd = 'networksetup -listallhardwareports'
    try:
        get_interface_result = subprocess.run(get_interface_cmd,
                                              shell=True,
                                              capture_output=True,
                                              text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'Error getting Wi-Fi interface name. Return code: {e.returncode}, error: {e.stderr}') from e

    interface_lines = get_interface_result.stdout.split('\n')
    for index, line in enumerate(interface_lines):
        if 'Wi-Fi' in line:
            ezshare.interface_name = interface_lines[index + 1].split(':')[1].strip()
            break
    if not ezshare.interface_name:
        raise RuntimeError('No Wi-Fi interface found')

    connect_cmd = f'networksetup -setairportnetwork {ezshare.interface_name} "{ezshare.ssid}" "{ezshare.psk}"'
    try:
        connect_result = subprocess.run(connect_cmd, shell=True,
                                        capture_output=True,
                                        text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'Error connecting to {ezshare.ssid}. Return code: {e.returncode}, error: {e.stderr}') from e
    if 'Failed' in connect_result.stdout:
        raise RuntimeError(f'Error connecting to {ezshare.ssid}. Error: {connect_result.stdout}')
    ezshare.connection_id = ezshare.ssid
    ezshare.connected = True

def wifi_connected(ezshare):
    """
    Check if the Wi-Fi is connected.
    """
    return ezshare.connected

def disconnect_from_wifi(ezshare):
    """
    Disconnect from the Wi-Fi network.
    """
    if ezshare.connection_id:
        ezshare.print(f'Disconnecting from {ezshare.connection_id}...')

        ezshare.print(f'Removing profile for {ezshare.connection_id}...')
        profile_cmd = f'networksetup -removepreferredwirelessnetwork {ezshare.interface_name} "{ezshare.connection_id}"'
        try:
            subprocess.run(profile_cmd, shell=True,
                           capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Error removing network profile for {ezshare.ssid}. Return code: {e.returncode}, error: {e.stderr}') from e
        try:
            subprocess.run(f'networksetup -setairportpower {ezshare.interface_name} off',
                           shell=True, check=True)
            logger.info('Wi-Fi interface %s turned off', ezshare.interface_name)
            subprocess.run(f'networksetup -setairportpower {ezshare.interface_name} on',
                           shell=True, check=True)
            logger.info('Wi-Fi interface %s turned on', ezshare.interface_name)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Error toggling Wi-Fi interface power. Return code: {e.returncode}, error: {e.stderr}') from e
        finally:
            ezshare.connected = False
            ezshare.connection_id = None

def reconnect_to_original_wifi(ezshare):
    """
    Reconnect to the original Wi-Fi network.
    """
    if ezshare.previous_ssid and ezshare.previous_psk:
        try:
            ezshare.print(f'Reconnecting to {ezshare.previous_ssid}...')
            connect_cmd = f'networksetup -setairportnetwork {ezshare.interface_name} "{ezshare.previous_ssid}" "{ezshare.previous_psk}"'
            connect_result = subprocess.run(connect_cmd, shell=True,
                                            capture_output=True,
                                            text=True, check=True)
            if 'Failed' in connect_result.stdout:
                raise RuntimeError(f'Error reconnecting to {ezshare.previous_ssid}. Error: {connect_result.stdout}')
            ezshare.print(f'Reconnected to {ezshare.previous_ssid}.')
            return True
        except subprocess.CalledProcessError as e:
            ezshare.print(f'Error reconnecting to {ezshare.previous_ssid}. Return code: {e.returncode}, error: {e.stderr}')
            return False
    else:
        ezshare.print('No previous Wi-Fi credentials stored.')
        return False
