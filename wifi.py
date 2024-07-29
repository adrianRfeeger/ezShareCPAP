import subprocess
import logging

logger = logging.getLogger(__name__)

def connect_to_wifi(ezshare):
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
    return ezshare.connected

def disconnect_from_wifi(ezshare):
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
