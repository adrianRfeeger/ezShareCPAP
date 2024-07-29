# ezShareCPAP


## Overview

ezShareCPAP is a macOS program designed to download files from an [ez Share SD card/adapter](https://www.youtube.com/watch?v=ANz8pNDHAPo) when used in CPAP devices (such as the ResMed AirSense 10 Elite) to a local directory. These files can then be imported with applications such as [OSCAR](https://www.sleepfiles.com/OSCAR/) and [SleepHQ](https://home.sleephq.com/) for data analysis and visualisation.

## Features

- **Wi-Fi Connectivity:** Connects to the ez Share SD card's Wi-Fi network.
- **File Synchronisation:** Downloads files from the SD card to a specified local directory.
- **User Interface:** Provides a graphical user interface (GUI) for ease of use.
- **Configuration:** Handles configuration settings directly through the GUI.
- **Real-time Updates:** Displays status updates during the file synchronisation process.
- **Import with OSCAR:** Option to automatically import data with OSCAR after completion.
- **Quit After Completion:** Option to automatically quit the application after completion.

## Prerequisites

- macOS operating system.
- Python 3.x installed on your system (for source installation).
- Required Python packages: `requests`, `beautifulsoup4`, `PyQt6` (for source installation).

## Installation

### From Release Version (arm64/silicon only, for Intel use the source version)

1. **Download the release version:**

   - Download the release version compiled with PyInstaller from [here](https://github.com/adrianrfeeger/ezShareCPAP/releases).

2. **Extract the ZIP file:**

   - Unzip the downloaded file and move the program to the Applications folder.

### From Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adrianrfeeger/ezShareCPAP.git
   cd ezShareCPAP
   ```   
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the program:**
   ```bash
   python main.py
   ```
## Compiling Standalone Using PyInstaller

1. **Activate the virtual environment:**
   ```bash
   cd ezShareCPAP
   source venv/bin/activate
   ```
2. **Install PyInstaller:**

   ```bash
   pip install pyinstaller
   ```

3. **Compile the application:**

   ```bash
   pyinstaller ezShareCPAP.spec
   ```

   - This will create a standalone executable in the `dist` folder, drag it into the Applications folder.

## Usage

### Graphical User Interface (GUI)

The GUI provides an easy way to configure and run the file synchronisation process.

**Text:**
- **Path:**  The local directory where the files will be downloaded.
- **URL:**  The URL of the ez Share SD card.
- **Wi-Fi SSID:** The SSID of the ez Share Wi-Fi network. The default SSID is `ez Share`.
- **Wi-Fi PSK:**  The PSK (password) for the ez Share Wi-Fi network. The default PSK is `88888888`.

**Checkboxes:**
- **Import With OSCAR:** Automatically imports data into OSCAR after the synchronisation process is completed.
- **Quit:** Automatically quits the application after the synchronisation process is completed.

**Buttons:**
- **Browse:** Selects the directory to download the files to.
- **ez Share Config:** Opens the configuration web page for the ez Share SD card.
- **Start:** Initiates the synchronisation process.
- **Save:** Saves the current settings to `config.ini`.
- **Defaults:** Restores the default settings.
- **Cancel:** Cancels the current operation.
- **Quit:** Closes the application.

**Status Bar:** Displays the current status of the application.

**Progress Bar:** Displays the progress of the file synchronisation process.

**Menu:**
-   **Settings:**
    -   **Load Default:** Restores the default settings.
    -   **Change Path:** Opens a dialog to change the directory path.
    -   **Save:** Saves the current settings to `config.ini`.
-   **Tools:**
    -   **ez Share Config:** Opens the configuration web page for the ez Share SD card.
    -   **Check access to Oscar:** Opens the settings for Privacy & Secuirty - Accessibility.
-   **Quit ezShareCPAP:** Closes the application.
  
## File Structure

- `README.md`: This file, containing documentation for the project.
- `ezShareCPAP.spec`: PyInstaller specification file for building the standalone application.
- `icon.icns`: Icon file for the macOS application.
- `requirements.txt`: Lists required Python packages for the project.
- `config.ini`: Stores settings.
- `style_light.qss`: Light mode styling.
- `style_dark.qss`: Dark mode styling.
- `main.py`: Entry point for the program.
- `gui.py`: Handles the graphical user interface and configuration settings.
- `ui_main.py`: Defines the gui styling.
- `ezshare.py`: Manages Wi-Fi connection and file synchronisation.
- `file_ops.py`: Manages file operations, including directory traversal and file downloading.
- `wifi.py`: Handles Wi-Fi connections specific to macOS.
- `utils.py`: Utility functions for resource paths and permission checks.
- `worker.py`: Background worker thread for performing the sync process.

## Troubleshooting

### Wi-Fi Connection Issues:

- Verify the SSID and PSK in the GUI are correct. Default SSID is `ez Share`, and the default PSK is `88888888`.
- Ensure the ezShare SD card/adapter is inserted into a powered-on device (e.g., CPAP) and within range of your computer (5-10 metres).

### File Download Issues:

- Confirm the URL in the GUI points to the correct ezShare SD card address.
- Ensure sufficient space is available in the local directory for file downloads.

### Importing To Oscar:
If you encounter issues with automating OSCAR imports, ensure that ezShareCPAP has the necessary permissions enabled to interact with OSCAR.

   1. Choose **Tools** from the menu.
   2. Select **Check Access To OSCAR**.
   3. Ensure that ezShareCPAP is listed and enabled. If it is not listed, you can add it by clicking the '**+**' button and navigating to the ezShareCPAP application.
   4. If ezShareCPAP is already listed and enabled then remove it by selecting it and then clicking the '**-**' button, then re-add and enable it (as per 3.). 
![image](https://github.com/user-attachments/assets/1bca6df9-86c6-4bf0-9b41-74687e1a5d5c)
