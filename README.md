# ezShareCPAP

## Overview

ezShareCPAP is a macOS application designed to download files from an [ez Share SD card/adapter](https://www.youtube.com/watch?v=ANz8pNDHAPo) when used in CPAP devices (such as the ResMed AirSense 10 Elite) to a local directory. These files can then be imported into applications such as [OSCAR](https://www.sleepfiles.com/OSCAR/) and [SleepHQ](https://home.sleephq.com/) for data analysis and visualization.

## Features

- **Wi-Fi Connectivity:** Connects to the ez Share SD card's Wi-Fi network.
- **File Synchronization:** Downloads files from the SD card to a specified local directory.
- **User Interface:** Provides a graphical user interface (GUI) for ease of use.
- **Configuration:** Handles configuration settings directly through the GUI.
- **Real-time Updates:** Displays status updates during the file synchronization process.
- **Import with OSCAR:** Option to automatically import data with OSCAR after completion.
- **Quit After Completion:** Option to automatically quit the application after completion.
- **ez Share Configuration:** Allows configuring the ez Share SD card settings via the application.
- **Folder Selection:** Browse and select folders on the ez Share SD card to specify which files to sync.

## Prerequisites

- **macOS Operating System:** The application is macOS-specific due to dependencies on macOS system utilities.
- **Python 3.8 or Higher:** Required if installing from source.
- **Required Python Packages:** Listed in `requirements.txt` (for source installation).

## Installation

### From Release Version (arm64/Apple Silicon Only)

1. **Download the Release Version:**

   - Download the latest release compiled with PyInstaller from the https://github.com/adrianRfeeger/ezShareCPAP---tkinter-version/releases.
2. **Extract the ZIP File:**

   - Unzip the downloaded file.

3. **Move to Applications Folder:**

   - Drag the `ezShareCPAP` application into your `Applications` folder.

4. **Run the Application:**

   - Double-click the `ezShareCPAP` application to launch it.
   - **Note:** You might need to adjust your security settings to allow running applications from unidentified developers:
     - Go to **System Preferences** > **Security & Privacy** > **General** tab.
     - Click **Open Anyway** next to the message about ezShareCPAP being blocked.

### From Source

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/adrianrfeeger/ezShareCPAP.git
   cd ezShareCPAP
   ```

2. **Create and Activate a Virtual Environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install the Required Packages:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Program:**

   ```bash
   python main.py
   ```

## Compiling Standalone Using PyInstaller

1. **Activate the Virtual Environment:**

   ```bash
   cd ezShareCPAP
   source venv/bin/activate
   ```

2. **Install PyInstaller:**

   ```bash
   pip install pyinstaller
   ```

3. **Compile the Application:**

   ```bash
   pyinstaller ezShareCPAP.spec
   ```

   - This will create a standalone executable in the `dist` folder. Move the generated application to your `Applications` folder.

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

- **Import With OSCAR:**
  - Automatically imports data into OSCAR after the synchronization process is completed.
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
   - If **Import With OSCAR** is checked, the application will attempt to import the data into OSCAR after synchronization.

6. **Completion:**
   - The application will display a completion message.
   - If **Quit After Completion** is checked, the application will close automatically.

## File Structure

- `README.md`: This file, containing documentation for the project.
- `ezShareCPAP.spec`: PyInstaller specification file for building the standalone application.
- `icon.icns`: Icon file for the macOS application.
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
- `wifi_utils.py`: Handles Wi-Fi connections specific to macOS.
- `worker.py`: Background worker thread for performing the synchronization process.
- `ezsharecpap.ui`: PyGubu UI definition file for the GUI.
- `icon.png`: Icon image used in the application.
- `folder.png`, `file.png`, `sdcard.png`: Icons used in the folder selector dialog.

## Troubleshooting

### Wi-Fi Connection Issues

- **Verify SSID and PSK:**
  - Ensure the SSID and PSK in the GUI match your ez Share SD card settings.
  - Default SSID: `ez Share`
  - Default PSK: `88888888`

- **Device Power and Proximity:**
  - Ensure the ez Share SD card is inserted into a powered-on device (e.g., CPAP machine).
  - The device should be within close range (5-10 meters) of your computer.

- **Interference:**
  - Minimize interference by turning off other Wi-Fi devices during the connection process.

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

- **Application Permissions:**
  - **Grant Accessibility Permissions:**
    1. Open **System Preferences** > **Security & Privacy** > **Privacy** tab.
    2. Select **Accessibility** from the left pane.
    3. Click the lock icon to make changes and enter your password.
    4. Ensure **ezShareCPAP** is listed and checked. If not, click the **'+'** button and add the ezShareCPAP application.
    5. If ezShareCPAP is already listed and enabled, try removing it and re-adding it.

    ![Accessibility Settings](path/to/your/image.png)

### Application Crashes or Unresponsiveness

- **Check Log Files:**
  - Review the `application.log` file in the application's directory for error messages.

- **Update the Application:**
  - Ensure you're using the latest version of ezShareCPAP from the [GitHub repository](https://github.com/adrianrfeeger/ezShareCPAP).

- **Reinstall Dependencies:**
  - If running from source, reinstall the required Python packages:

    ```bash
    pip install --force-reinstall -r requirements.txt
    ```

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

If you encounter issues not covered in this guide, please open an issue on the [GitHub repository](https://github.com/adrianrfeeger/ezShareCPAP/issues) with details of the problem.

## License

This project is licensed under the [MIT License](LICENSE).
