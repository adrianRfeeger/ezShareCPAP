# ezShareCPAP
<img width="532" alt="image" src="https://github.com/user-attachments/assets/6ed446ef-5753-4165-b092-e6e2f059e696">

## Overview

ezShareCPAP is a cross-platform application designed to download files from an [ez Share SD card/adapter](https://www.youtube.com/watch?v=ANz8pNDHAPo) when used in CPAP devices (such as the ResMed AirSense 10 Elite) to a local directory. These files can then be imported into applications such as [OSCAR](https://www.sleepfiles.com/OSCAR/) for data analysis and visualisation. On macOS, ezShareCPAP can attempt to automate OSCAR's import flow; on Windows and Linux, it launches OSCAR so you can import the downloaded data manually.

### Supported Platforms
- **macOS** (Intel and Apple Silicon)
- **Windows** (10 and later)
- **Linux** (Ubuntu, Debian, Fedora, and other distributions)

PyInstaller builds are native to the operating system used to build them. Build Windows releases on Windows, Linux releases on Linux, and macOS releases on macOS.

## OSCAR Compatibility

This application downloads CPAP files in a structure that can be imported into:
- **OSCAR 1.x** (legacy versions 1.7.0 and earlier)
- **OSCAR 2.0.0+** (current release with SQL database backend)

### Open OSCAR Behavior

- **macOS:** Attempts to activate OSCAR and trigger the CPAP card import flow with AppleScript/System Events. It tries the OSCAR 2.x menu flow first and falls back to the OSCAR 1.x menu item.
- **Windows:** Launches OSCAR if it is installed, then prompts you to import manually from OSCAR.
- **Linux:** Launches OSCAR from `PATH`, then prompts you to import manually from OSCAR.

### Version Detection
The app attempts to detect your installed OSCAR version and displays it in the **Help > About** dialog. Version detection is informational on Windows and Linux because import automation is macOS-only.

### Troubleshooting OSCAR Integration
- On macOS, if automatic import fails, ensure OSCAR is running and in focus.
- On macOS, grant Accessibility and Automation permissions to ezShareCPAP (see Permissions section).
- Check that OSCAR is installed in the default location:
  - **macOS:** `/Applications/OSCAR.app`
  - **Windows:** `C:\Program Files\OSCAR\OSCAR.exe`
  - **Linux:** Available in PATH
- Verify your OSCAR version by opening OSCAR and checking Help → About

## Features

- **Wi-Fi Connectivity:** Connects to the ez Share SD card's Wi-Fi network.
- **File Synchronization:** Downloads files from the SD card to a specified local directory.
- **User Interface:** Provides a graphical user interface (GUI) for ease of use.
- **Configuration:** Handles configuration settings directly through the GUI.
- **Real-time Updates:** Displays status updates during the file synchronization process.
- **Open OSCAR:** Option to open OSCAR after completion. macOS can attempt automatic import; Windows and Linux require manual import from OSCAR.
- **Quit:** Option to automatically quit the application after completion.
- **ez Share Configuration:** Allows configuring the ez Share SD card settings via the application.
- **Folder Selection:** Browse and select folders on the ez Share SD card to specify which files to sync.

## Prerequisites

- **Operating System:** macOS (10.13+), Windows (10+), or Linux (Ubuntu 18.04+, Debian 9+, Fedora 30+, or equivalent)
- **Python 3.8 or Higher:** Required if installing from source.
- **Required Python Packages:** Listed in `requirements.txt` (for source installation).
- **Platform-Specific Tools:**
  - **macOS:** AppleScript (built-in)
  - **Windows:** PowerShell 5.0+ and `netsh` (built into Windows 10+)
  - **Linux:** NetworkManager/`nmcli` (for Wi-Fi connectivity)

## Installation

### From Release Version

#### macOS
1. **Download the Release Version:**
   - Download the latest macOS release for your processor (`arm64` for Apple Silicon, `x86_64` for Intel) from the [Releases Page](https://github.com/adrianRfeeger/ezShareCPAP).
2. **Extract and Move to Applications:**
   - Unzip the downloaded file.
   - Drag `ezShareCPAP.app` into your `Applications` folder.
3. **First Run Security:**
   - Double-click `ezShareCPAP` to launch it.
   - If blocked, go to **System Preferences** > **Security & Privacy** > **General** and click **Open Anyway**.
4. **Grant Accessibility Permissions:**
   - Open **System Preferences** > **Security & Privacy** > **Privacy** > **Accessibility**.
   - Click the lock icon, enter your password, and add `ezShareCPAP` to the allowed list.

#### Windows
1. **Download the Release Version:**
   - Download the latest Windows release archive from the [Releases Page](https://github.com/adrianRfeeger/ezShareCPAP).
2. **Extract:**
   - Extract the archive to your desired location.
3. **First Run:**
   - Double-click `ezShareCPAP.exe` to launch.
   - Windows may show a security warning; click **More info** → **Run anyway** to proceed.

#### Linux
1. **Download the Release Version:**
   - Download the latest Linux release archive from the [Releases Page](https://github.com/adrianRfeeger/ezShareCPAP).
2. **Extract and Make Executable:**
   - `tar -xzf ezShareCPAP*.tar.gz && cd ezShareCPAP && chmod +x ezShareCPAP && ./ezShareCPAP`
3. **Install NetworkManager (if needed):**
   - **Ubuntu/Debian:** `sudo apt install network-manager`
   - **Fedora:** `sudo dnf install NetworkManager`

### From Source (All Platforms)

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/adrianRfeeger/ezShareCPAP.git
   cd ezShareCPAP
   ```

2. **Create and Activate a Virtual Environment:**

   **macOS & Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   **Windows:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install the Required Packages:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Program:**

   ```bash
   python main.py
   ```

## Building Standalone Executable

### Using PyInstaller

PyInstaller does not cross-compile this application. Run the build on each target operating system.

1. **Activate the Virtual Environment:**

   **macOS & Linux:**
   ```bash
   source venv/bin/activate
   ```

   **Windows:**
   ```bash
   venv\Scripts\activate
   ```

2. **Install PyInstaller:**

   ```bash
   pip install pyinstaller
   ```

3. **Build the Application:**

   ```bash
   pyinstaller ezShareCPAP.spec
   ```

4. **Find Your Build Output:**
   - **macOS:** `dist/ezShareCPAP.app` (move to `/Applications`)
   - **Windows:** `dist/ezShareCPAP/ezShareCPAP.exe`
   - **Linux:** `dist/ezShareCPAP/ezShareCPAP`

The spec uses `icon.icns` for macOS and `icon.ico` for Windows when those files are present.

## Usage

### Graphical User Interface (GUI)

The GUI provides an intuitive way to configure and run the file synchronization process.

**Fields:**

- **Local Directory Path:**
  - The local directory where the files will be downloaded.
  - Use the **Select Folder** button to choose the directory.
- **URL:**
  - The URL of the ez Share SD card directory to sync.
  - Default: `http://192.168.4.1/dir?dir=A:`
- **Wi-Fi SSID:**
  - The SSID of the ez Share Wi-Fi network.
  - Default: `ez Share`
- **Wi-Fi PSK:**
  - The password for the ez Share Wi-Fi network.
  - Default: `88888888`

**Checkboxes:**

- **Open OSCAR:**
  - Opens OSCAR after synchronization. On macOS, ezShareCPAP attempts to start the import flow automatically. On Windows and Linux, open OSCAR and import manually.
- **Quit After Completion:**
  - Automatically quits the application after the synchronization process is completed.

**Buttons:**

- **Select Folder:**
  - Opens a dialog to select the local directory where files will be downloaded.
- **ez Share Config:**
  - Opens the configuration web page for the ez Share SD card.
- **Start:**
  - Initiates the synchronization process.
- **Cancel:**
  - Cancels the current operation.
- **Save:**
  - Saves the current settings to the configuration file.
- **Defaults:**
  - Restores the default settings.
- **Quit:**
  - Closes the application.

**Status Bar:**

- Displays the current status of the application.

**Progress Bar:**

- Shows the progress of the file synchronization process.

**Additional Links:**

- **Download OSCAR:**
  - If OSCAR is not detected on your system, a link will appear to download it.

### Steps to Synchronize Files:

1. **Configure Settings:**
   - Ensure the **Wi-Fi SSID** and **Wi-Fi PSK** match your ez Share SD card settings.
   - Specify the **Local Directory Path** where you want the files saved.

2. **Select Folder on SD Card (Optional):**
   - Click **Select Folder** to browse and select a specific folder on the SD card to synchronize.

3. **Start Synchronization:**
   - Click **Start** to begin the file synchronization process.

4. **Monitor Progress:**
   - Observe the **Progress Bar** and **Status Bar** for updates.

5. **Import Data with OSCAR (Optional):**
   - If **Open OSCAR** is checked, the application will open OSCAR after synchronization.
   - On macOS, it attempts to start OSCAR's CPAP card import flow automatically.
   - On Windows and Linux, manually import the downloaded folder from OSCAR.

6. **Completion:**
   - The application will display a completion message.
   - If **Quit** is checked, the application will close automatically.

## File Structure

- `README.md`: This file, containing documentation for the project.
- `ezShareCPAP.spec`: PyInstaller specification file for building the standalone application.
- `icon.icns`: Icon file for the macOS application.
- `icon.ico`: Icon file for the Windows application.
- `requirements.txt`: Lists required Python packages for the project.
- `main.py`: Entry point for the program.
- `callbacks.py`: Handles callback functions for UI events.
- `config_manager.py`: Manages configuration settings.
- `ez_share_config.py`: Manages configuration of the ez Share SD card.
- `ezshare.py`: Manages Wi-Fi connection and file synchronization.
- `file_ops.py`: Manages file operations, including directory traversal and file downloading.
- `folder_selector.py`: Provides a GUI for selecting folders on the ez Share SD card.
- `status_manager.py`: Manages status updates and the status bar.
- `utils.py`: Utility functions for resource paths and permission checks.
- `wifi_utils.py`: Handles Wi-Fi connections for macOS, Windows, and Linux.
- `worker.py`: Background worker thread for performing the synchronization process.
- `ezShareCPAP.ui`: PyGubu UI definition file for the GUI.
- `icon.png`: Icon image used in the application.
- `folder.png`, `file.png`, `sdcard.png`: Icons used in the folder selector dialog.
- `tests/test_platform_wifi.py`: Unit tests for platform-specific Wi-Fi command generation and config-page launching.

## Troubleshooting

### Platform-Specific Issues

#### macOS
- **Wi-Fi Connection:**
  - If connection fails, ensure you've granted Full Disk Access permissions (System Preferences > Security & Privacy > Privacy > Full Disk Access).
  - Try turning Wi-Fi off and back on in System Preferences if connection is unstable.
  
- **Accessibility Permissions:**
  - If OSCAR import doesn't work, ensure ezShareCPAP is listed in System Preferences > Security & Privacy > Privacy > Accessibility.

#### Windows
- **Wi-Fi Connection:**
  - Ensure you're running the application with adequate permissions (Administrator may be required).
  - If `netsh` commands fail, try running the application as Administrator.
  - The app uses PowerShell to locate the Wi-Fi adapter and falls back to `netsh wlan show interfaces`.
  
- **OSCAR Detection:**
  - If OSCAR isn't detected, ensure it's installed in `C:\Program Files\OSCAR\OSCAR.exe`.
  - Manually import after file download: File → Import in OSCAR.

#### Linux
- **NetworkManager Installation:**
  - If Wi-Fi connection fails, install NetworkManager: `sudo apt install network-manager` (Ubuntu/Debian) or `sudo dnf install NetworkManager` (Fedora).
  - Ensure NetworkManager is running: `sudo systemctl start NetworkManager`.
  - The app uses `nmcli` to connect and disconnect. It can detect interfaces with `nmcli`, `iwconfig`, or `ip`, but NetworkManager is still required for connection.
  
- **OSCAR Path:**
  - Ensure OSCAR is in your PATH. You can verify with: `which OSCAR`.
  - If installed in a non-standard location, add the directory to PATH or create a symlink.

### Wi-Fi Connection Issues

- **Verify SSID and PSK:**
  - Ensure the SSID and PSK in the GUI match your ez Share SD card settings.
  - Default SSID: `ez Share`
  - Default PSK: `88888888`

- **Device Power and Proximity:**
  - Ensure the ez Share SD card is inserted into a powered-on device (e.g., CPAP machine).
  - The device should be within close range (5-10 meters) of your computer.

### File Download Issues

- **Check the URL:**
  - Ensure the URL in the GUI points to the correct ez Share SD card address.
  - Default URL: `http://192.168.4.1/dir?dir=A:`

- **Local Directory Access:**
  - Verify you have read/write permissions for the specified local directory.
  - Change the directory if necessary.

- **Disk Space:**
  - Ensure there is sufficient space available in the local directory.

### Importing to OSCAR

- **OSCAR Installation:**
  - Download and install OSCAR from the [official website](https://www.sleepfiles.com/OSCAR/).
- **Import Behavior:**
  - macOS can attempt automatic import through OSCAR's menu.
  - Windows and Linux launch OSCAR only; use OSCAR's import menu manually.

- **macOS Application Permissions:**
  - **Grant Accessibility Permissions:**
    1. Open **System Preferences** > **Security & Privacy** > **Privacy** tab.
    2. Select **Accessibility** from the left pane.
    3. Click the lock icon to make changes and enter your password.
    4. Ensure **ezShareCPAP** is listed and checked. If not, click the **'+'** button and add the ezShareCPAP application.
    5. If ezShareCPAP is already listed and enabled, try removing it and re-adding it.
![image](https://github.com/user-attachments/assets/046be7ac-c767-4325-8c6c-f3b30778b2d0)

### Permissions Issues

- **Full Disk Access:**
  - Grant Full Disk Access to ezShareCPAP:
    1. Open **System Preferences** > **Security & Privacy** > **Privacy** tab.
    2. Select **Full Disk Access** from the left pane.
    3. Click the lock icon to make changes and enter your password.
    4. Click the **'+'** button and add the ezShareCPAP application.

- **Firewall Settings:**
  - Ensure that your firewall settings are not blocking ezShareCPAP or OSCAR.

## Support

If you encounter issues not covered in this guide, please open an issue on the [GitHub repository](https://github.com/adrianRfeeger/ezShareCPAP/issues) with details of the problem.

## Changelog

### Version 0.2.0 (Cross-Platform)
- **New:** Full cross-platform support (macOS, Windows, Linux)
- **New:** Platform-specific Wi-Fi connectivity (networksetup for macOS, netsh for Windows, nmcli for Linux)
- **New:** Cross-platform configuration file format (JSON instead of macOS plist)
- **New:** Platform-specific config directories (Preferences on macOS, AppData on Windows, XDG_CONFIG_HOME on Linux)
- **Improved:** OSCAR handling on Windows and Linux launches OSCAR for manual import
- **Improved:** OSCAR version detection for all platforms
- **Improved:** Comprehensive cross-platform documentation and troubleshooting guides
- **Updated:** Application version display shows detected platform
- **Updated:** PyInstaller spec supports macOS, Windows, and Linux native builds with platform-specific icons
- **Updated:** ez Share configuration page opens through the default browser on all platforms
- Bumped version from 0.1.0 to 0.2.0 to reflect cross-platform support

### Version 0.1.0 (OSCAR 2.0.0 Compatible)
- **New:** Compatibility with OSCAR 2.0.0 import menu changes on macOS
- **New:** Automatic OSCAR version detection
- **New:** Display detected OSCAR version in About dialog
- **Improved:** Dual macOS import method support for OSCAR 1.x and OSCAR 2.0.0+
- **Improved:** Better error handling and fallback mechanisms for OSCAR import
- **Fixed:** AppleScript compatibility with OSCAR's updated menu structure
- Bumped version from 0.0.9 to 0.1.0 to reflect OSCAR 2.0.0 support

## License

This project is licensed under the [MIT License](LICENSE).
