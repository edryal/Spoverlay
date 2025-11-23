# Spoverlay - Spotify Overlay

<p align="center">
  <img width="330" height="82" alt="Overlay Showcase #1" src="https://github.com/user-attachments/assets/0b6a1611-8d55-4858-a710-89cf322ddb86" />

  <img width="330" height="82" alt="Overlay Showcase #2" src="https://github.com/user-attachments/assets/9b7a1394-65ad-455c-810f-b87d3ed0b2fc" />
</p>

A lightweight overlay for Spotify that displays the currently playing track. Built with Python and Qt6, it offers a simple, one-time setup and a graphical interface for all configuration settings.

## Core Features

- Displays the current track's album art, title, and artist.
- Automatically shows on playback start and hides on pause/stop.
- GUI Configuration: All settings are managed through a simple "Configure" window.
- System Tray Control: A tray icon to toggle visibility, open settings, or quit.
- Customizable Keybindings:
    - **Windows:** Configurable global hotkey support.
    - **Linux/Wayland:** IPC-based command for integration with any hotkey daemon.
- Click-Through: Option to make the overlay non-interactive.

## Requirements

- Python 3.12+
- **Linux Users:** `socat` for the keybinding feature.

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/edryal/spoverlay.git
cd spoverlay
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
# Create the virtual environment
python -m venv venv
```

Activate based on your platform:
```bash
# On Windows:
venv\Scripts\activate
```
```bash
# On Linux:
source venv/bin/activate
```

### 3. Install Dependencies
Install the required packages for your operating system.

```bash
# Install core dependencies
pip install toml spotipy PySide6 pynput Pillow qt-material qt-material-stubs
```
```bash
# For Windows, also install pywin32 for click-through support
pip install pywin32
```

> **Note for Linux/Wayland Users:** The keybinding feature requires `socat`.
> ```bash
> # Example for Arch Linux
> sudo pacman -S socat
> ```
>
> ```bash
> # Example for Debian/Ubuntu
> sudo apt install socat
> ```

### 4. Create Spotify App
1. Navigate to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Click on ```Create App```.
3. Give it a ```name``` and ```description```.
4. Add this local Redirect URI ```http://127.0.0.1:8080/callback``` and click ```Add```.
<img width="258" height="202" alt="image" src="https://github.com/user-attachments/assets/7f04b37f-39a5-4553-923d-16da39c3a36d" />

5. Check this box to allow the app to use the Spotify API to fetch data for the currently playing track.
<img width="255" height="84" alt="image" src="https://github.com/user-attachments/assets/46b43616-2d8f-4ca4-a4c8-0798cdbc4bed" />

6. Accept Spotify ToS and ```Save```.
7. Open the App you just created and copy the ```Client ID```.
8. Paste the ```Client ID``` in the configuration.

---

## Running the Application

With the virtual environment activated, start the application:

```bash
python main.py
```

On the first launch, a browser window will open for a one-time Spotify authentication.

## Configuration

All settings are managed through a graphical interface.

1.  **Right-click** the Spoverlay icon in your system tray.
2.  Select **"Configure"**.

<p align="left">
  <img width="431" height="278" alt="image" src="https://github.com/user-attachments/assets/71b99450-6dd6-4d29-9862-a5277397519b" />
</p>

Changes are applied instantly upon clicking **"Save & Apply"**.

Settings are stored in `config.toml` in your user's configuration directory (e.g., `~/.config/Spoverlay/` on Linux, `%APPDATA%\Spoverlay\` on Windows).

| Setting | Description |
|---|---|
| **Overlay Position** | The corner where the overlay appears. (`top-right`, `top-left`, `bottom-right`, `bottom-left`). |
| **Screen Margin (px)** | The distance in pixels from the screen edges. |
| **Album Art Size (px)**| The size of the album art in pixels (e.g., 64, 96, 128). |
| **Update Interval (ms)**| How often to check Spotify for changes. 500-1000ms is a safe range. |
| **Global Hotkey** | (Windows) The global key combination to toggle the overlay (e.g., `F7`, `ctrl+shift+h`). |
| **Overlay Click-Through**| If checked, makes the overlay non-interactive. |

---

## Keybindings

Toggle the overlay's visibility using a keybinding.

### Windows
Set your desired key combination in the **Configure** window. The feature is managed by `pynput`.

### Linux (Wayland)
Toggling is handled via an IPC command. Configure your window manager or hotkey daemon to execute:
```sh
socat - unix-connect:/tmp/Spoverlay.sock
```
**Example for Hyprland (`hyprland.conf`):**
```ini
# Bind F7 to toggle the Spoverlay visibility
bind = , F7, exec, socat - unix-connect:/tmp/Spoverlay.sock
```

## Building an Executable

A `spoverlay.spec` file is included for use with PyInstaller.

First, install PyInstaller: `pip install pyinstaller`. Then, run the build command:
```bash
pyinstaller spoverlay.spec
```
The executable will be located in the `dist/spoverlay` directory.

## Wayland Window Rules
For tiling compositors like Hyprland, it is recommended to add window rules to manage the overlay's behavior.

**Example for Hyprland (`hyprland.conf`):**
```ini
# Rules to make Spoverlay float, stay on top, and not steal focus
# Troubleshoot 'class' and 'title' by using `hyprctl clients`
windowrulev2 = float, class:^(spoverlay)$, title:^(spoverlay — Spoverlay)$
windowrulev2 = nofocus, title:^(spoverlay — Spoverlay)$
windowrulev2 = noinitialfocus, title:^(spoverlay — Spoverlay)$
windowrulev2 = pin, title:^(spoverlay — Spoverlay)$
windowrulev2 = noborder, title:^(spoverlay — Spoverlay)$
windowrulev2 = noshadow, title:^(spoverlay — Spoverlay)$
windowrulev2 = move 81% 48, title:^(spoverlay — Spoverlay)$     # top-right
# windowrulev2 = move 30 48, title:^(spoverlay — Spoverlay)$      # top-left
# windowrulev2 = move 81% 90%, title:^(spoverlay — Spoverlay)$    # bottom-right
# windowrulev2 = move 30 90%, title:^(spoverlay — Spoverlay)$     # bottom-left
```
