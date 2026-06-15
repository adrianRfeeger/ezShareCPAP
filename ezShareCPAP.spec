# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path


APP_NAME = 'ezShareCPAP'
BUNDLE_ID = 'com.ezsharecpap'
IS_MACOS = sys.platform == 'darwin'
IS_WINDOWS = sys.platform.startswith('win')

block_cipher = None

datas = [
    ('ezShareCPAP.ui', '.'),
    ('file.png', '.'),
    ('folder.png', '.'),
    ('icon.png', '.'),
    ('sdcard.png', '.'),
]

for optional_data in ('icon.icns', 'icon.ico'):
    if Path(optional_data).exists():
        datas.append((optional_data, '.'))

exe_options = {
    'exclude_binaries': True,
    'name': APP_NAME,
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': not IS_WINDOWS,
    'upx': True,
    'console': False,
}

if IS_MACOS and Path('icon.icns').exists():
    exe_options['icon'] = 'icon.icns'
elif IS_WINDOWS and Path('icon.ico').exists():
    exe_options['icon'] = 'icon.ico'

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    **exe_options
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=not IS_WINDOWS,
    upx=True,
    name=APP_NAME
)

if IS_MACOS:
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon='icon.icns' if Path('icon.icns').exists() else None,
        bundle_identifier=BUNDLE_ID,
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleGetInfoString': APP_NAME,
            'CFBundleIdentifier': BUNDLE_ID,
            'CFBundleVersion': '1.0.1',
            'CFBundleShortVersionString': '1.0.1',
            'NSAppTransportSecurity': {
                'NSAllowsArbitraryLoads': True,
            },
            'NSDocumentsFolderUsageDescription': 'This application requires access to the Documents folder.',
            'NSLocalNetworkUsageDescription': 'This application requires access to the local network to find and communicate with the ez Share WiFi.',
            'NSLocationWhenInUseUsageDescription': 'This application requires access to location information to manage the WiFi network switching.',
            'NSAppleEventsUsageDescription': 'This application requires access to AppleEvents to automate OSCAR import.',
            'NSAccessibilityUsageDescription': 'This application requires access to Accessibility to automate OSCAR import.',
        }
    )
