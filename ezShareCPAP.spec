# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('icon.icns', '.'), 
        ('config.ini', '.'),
        ('ezshare.ui', '.')
        ],
    hiddenimports=['ttkwidgets'],
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
    exclude_binaries=True,
    name='ezShareCPAP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    icon='icon.icns',
    upx_args='--best --lzma'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    name='ezShareCPAP',
    upx_args='--best --lzma'
)

app = BUNDLE(
    coll,
    name='ezShareCPAP.app',
    icon='icon.icns',
    bundle_identifier='com.ezsharecpap',
    info_plist={
        'CFBundleName': 'ezShareCPAP',
        'CFBundleDisplayName': 'ezShareCPAP',
        'CFBundleGetInfoString': 'ezShareCPAP',
        'CFBundleIdentifier': 'com.ezsharecpap',
        'CFBundleVersion': '1.0.1',
        'CFBundleShortVersionString': '1.x.x',
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True,
        },
        'NSDocumentsFolderUsageDescription': 'This application requires access to the Documents folder.',
        'NSLocalNetworkUsageDescription': 'This application requires access to the local network to find and communicate with the ez Share WiFi.',
        'NSLocationWhenInUseUsageDescription': 'This application requires access to location information for to manage the WiFi network switching.',
        'NSAppleEventsUsageDescription': 'This application requires access to AppleEvents to automate OSCAR import.',
        'NSAccessibilityUsageDescription': 'This application requires access to Accessibility to automate OSCAR import.',
    }
)
