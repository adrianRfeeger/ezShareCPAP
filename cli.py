import argparse
import logging
import pathlib
import platform
import shutil
import subprocess
import sys

from config_manager import ConfigManager, get_default_config_file


DEFAULT_RETRIES = 3
DEFAULT_CONNECTION_DELAY = 5
ezShare = None


def build_parser():
    parser = argparse.ArgumentParser(
        prog='ezShareCPAP sync',
        description='Synchronize files from an ez Share Wi-Fi SD card without launching the GUI.',
    )
    parser.add_argument('--config', type=pathlib.Path, help='Path to the ezShareCPAP JSON config file.')
    parser.add_argument('--path', help='Local directory where downloaded files are saved.')
    parser.add_argument('--url', help='ez Share directory URL. Defaults to the saved config value.')
    parser.add_argument('--ssid', help='ez Share Wi-Fi SSID. Defaults to the saved config value.')
    parser.add_argument('--psk', help='ez Share Wi-Fi password. Defaults to the saved config value.')
    parser.add_argument('--overwrite', action='store_true', help='Download files even when a local copy exists.')
    parser.add_argument(
        '--ignore',
        action='append',
        default=[],
        help='File or directory name to ignore. Repeat the flag or use comma-separated values.',
    )
    parser.add_argument('--retries', type=int, default=DEFAULT_RETRIES, help='Wi-Fi/download retry count.')
    parser.add_argument(
        '--connection-delay',
        type=float,
        default=DEFAULT_CONNECTION_DELAY,
        help='Seconds to wait between retry attempts.',
    )
    parser.add_argument(
        '--save-config',
        action='store_true',
        help='Persist the provided path, URL, SSID, and PSK to the config file before running.',
    )
    parser.add_argument(
        '--open-oscar',
        action='store_true',
        help='Open OSCAR after a successful sync. macOS attempts import automation; Windows/Linux launch OSCAR.',
    )
    parser.add_argument('--quiet', action='store_true', help='Only print errors.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging.')
    return parser


def run_cli(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_sync(args, parser)


def run_sync(args, parser=None):
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

    config_file = args.config.expanduser() if args.config else get_default_config_file()
    config_manager = ConfigManager(config_file)

    path = pathlib.Path(args.path or config_manager.get_setting('Settings', 'path')).expanduser()
    url = args.url or config_manager.get_setting('Settings', 'url')
    ssid = args.ssid or config_manager.get_setting('WiFi', 'ssid')
    psk = args.psk if args.psk is not None else config_manager.get_setting('WiFi', 'psk')

    if not path or not url or not ssid:
        message = 'path, url, and ssid are required. Provide them as arguments or save them in the config.'
        if parser:
            parser.error(message)
        print(f'Error: {message}', file=sys.stderr)
        return 2

    if args.retries < 1:
        message = '--retries must be at least 1.'
        if parser:
            parser.error(message)
        print(f'Error: {message}', file=sys.stderr)
        return 2

    if args.connection_delay < 0:
        message = '--connection-delay must be 0 or greater.'
        if parser:
            parser.error(message)
        print(f'Error: {message}', file=sys.stderr)
        return 2

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f'Error: cannot create local directory {path}: {e}', file=sys.stderr)
        return 1

    if args.save_config:
        config_manager.set_setting('Settings', 'path', str(path))
        config_manager.set_setting('Settings', 'url', url)
        config_manager.set_setting('WiFi', 'ssid', ssid)
        config_manager.set_setting('WiFi', 'psk', psk)

    syncer = _get_ezshare_class()()
    syncer.set_status_callback(_build_status_callback(args.quiet))
    syncer.set_progress_callback(_build_progress_callback(args.quiet))
    syncer.set_params(
        path=path,
        url=url,
        start_time=None,
        show_progress=not args.quiet,
        verbose=not args.quiet,
        overwrite=args.overwrite,
        keep_old=False,
        ssid=ssid,
        psk=psk,
        ignore=_parse_ignore_values(args.ignore),
        retries=args.retries,
        connection_delay=args.connection_delay,
        debug=args.debug,
    )

    try:
        success = bool(syncer.run())
    except KeyboardInterrupt:
        print('Interrupted. Disconnecting from Wi-Fi if needed...', file=sys.stderr)
        syncer.stop()
        return 130

    if not success:
        return 1

    if args.open_oscar and not open_oscar_for_platform(_build_status_callback(args.quiet)):
        return 1

    return 0


def _parse_ignore_values(values):
    ignored = []
    for value in values:
        ignored.extend(part.strip() for part in value.split(',') if part.strip())
    return ignored


def _get_ezshare_class():
    global ezShare
    if ezShare is None:
        from ezshare import ezShare as ezshare_class
        ezShare = ezshare_class
    return ezShare


def _build_status_callback(quiet=False):
    def callback(message, message_type='info'):
        if quiet and message_type != 'error':
            return
        stream = sys.stderr if message_type == 'error' else sys.stdout
        print(message, file=stream)

    return callback


def _build_progress_callback(quiet=False):
    def callback(value):
        if quiet:
            return
        if value == 'no_files':
            print('No new files to sync.')

    return callback


def open_oscar_for_platform(status_callback=None):
    system = platform.system()
    callback = status_callback or _build_status_callback(False)

    if system == 'Darwin':
        return _open_oscar_macos(callback)
    if system == 'Windows':
        return _open_oscar_windows(callback)
    return _open_oscar_linux(callback)


def _open_oscar_macos(status_callback):
    script_20 = '''
    tell application "OSCAR"
        activate
        delay 2
        tell application "System Events"
            tell process "OSCAR"
                try
                    click menu item "Import" of menu "File" of menu bar 1
                    delay 1
                    click button "CPAP Card" of window 1
                on error
                    click menu item "Import CPAP Card Data" of menu "File" of menu bar 1
                end try
            end tell
        end tell
    end tell
    '''
    script_1x = '''
    tell application "OSCAR"
        activate
        delay 2
        tell application "System Events"
            tell process "OSCAR"
                click menu item "Import CPAP Card Data" of menu "File" of menu bar 1
            end tell
        end tell
    end tell
    '''

    try:
        result = subprocess.run(["osascript", "-e", script_20], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            status_callback('Opened OSCAR and attempted CPAP import.')
            return True

        result = subprocess.run(["osascript", "-e", script_1x], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            status_callback('Opened OSCAR and attempted legacy CPAP import.')
            return True

        error = result.stderr.strip() or result.stdout.strip()
        status_callback(f'Error opening OSCAR: {error}', 'error')
        return False
    except subprocess.TimeoutExpired:
        status_callback('Error opening OSCAR: timed out.', 'error')
        return False
    except OSError as e:
        status_callback(f'Error opening OSCAR: {e}', 'error')
        return False


def _open_oscar_windows(status_callback):
    oscar_path = shutil.which('OSCAR') or r'C:\Program Files\OSCAR\OSCAR.exe'
    if not pathlib.Path(oscar_path).exists():
        status_callback('OSCAR not found. Install OSCAR or add it to PATH.', 'error')
        return False

    try:
        subprocess.Popen([oscar_path])
        status_callback('OSCAR launched. Import your CPAP data manually from OSCAR.')
        return True
    except OSError as e:
        status_callback(f'Error launching OSCAR: {e}', 'error')
        return False


def _open_oscar_linux(status_callback):
    oscar_path = shutil.which('OSCAR')
    if not oscar_path:
        status_callback('OSCAR not found in PATH.', 'error')
        return False

    try:
        subprocess.Popen([oscar_path])
        status_callback('OSCAR launched. Import your CPAP data manually from OSCAR.')
        return True
    except OSError as e:
        status_callback(f'Error launching OSCAR: {e}', 'error')
        return False


if __name__ == '__main__':
    raise SystemExit(run_cli())
