# Spoverlay - Spotify Overlay

<p align="center">
  <img width="330" height="82" alt="image" src="https://github.com/user-attachments/assets/0b6a1611-8d55-4858-a710-89cf322ddb86" />

  <img width="330" height="82" alt="image" src="https://github.com/user-attachments/assets/9b7a1394-65ad-455c-810f-b87d3ed0b2fc" />

</p>

A lightweight desktop overlay for Spotify that displays the currently playing track. Built with Python and Qt6.

## Core Functionality

- Displays the current track's album art, title, and artist.
- Automatically shows on playback start and hides on pause/stop.
- System tray icon to toggle visibility and exit the application.
- Configurable through **environment variables** or via `.env` file for position, size, and polling rate.
- Keybinding support:
    - **Windows:** Global hotkey via `pynput`.
    - **Linux:** IPC-based command via `socat`.
- (Windows) Option for a click-through (transparent) window.

## Requirements

- Python 3.8+
- A Spotify Developer application for API credentials.
- **Linux/Wayland:** `socat` for the keybinding feature.

---

## Installation and Setup

Follow these steps to get Spoverlay running on your machine.

### 1. Clone the Repository
First, clone the project to your local machine:
```bash
git clone https://github.com/edryal/spoverlay.git
cd spoverlay
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
# Create the virtual environment
python -m venv venv

# Activate it (choose the command for your OS)
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Linux
source venv/bin/activate
```

### 3. Install Dependencies
Install the required packages for your operating system.

```bash
# Install core Python dependencies
pip install python-dotenv spotipy PySide6 PySide6-stubs pynput Pillow pyinstaller

# Install platform-specific Python packages
# On Linux (X11):
pip install python-xlib types-python-xlib

# On Windows:
pip install pywin32
```

> **Linux/Wayland Users:** For the keybinding feature, you must also install `socat`.
> ```bash
> # Example for Arch Linux
> sudo pacman -S socat
>
> # Example for Debian/Ubuntu
> sudo apt install socat
> ```

---

## Configuration

### 1. Spotify API Setup
Spoverlay needs a Spotify Client ID to fetch track information.

1.  Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in.
2.  Click **"Create app"**.
3.  Give your application a name and description.
4.  Add `http://127.0.0.1:8080/callback` as a **Redirect URI** in the app settings.
5.  Save the changes and copy your **Client ID**.

### 2. Environment Variables
Create a file named `.env` in the root of the project directory. Add your Spotify Client ID and any other customizations from the table below.

**`.env` File Template:**
```env
# Spotify API Credentials
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8080/callback

# UI & Behavior Settings (Optional)
OVERLAY_POSITION=top-right
OVERLAY_HOTKEY=F7
OVERLAY_MARGIN=24
# Note: UI may not scale well beyond 60-64px
OVERLAY_ART_SIZE=64
```

**All Configuration Options:**

| Variable | Default | Description |
|---|---|---|
| `SPOTIPY_CLIENT_ID` | (None) | **Required.** Your Spotify application Client ID. |
| `SPOTIPY_REDIRECT_URI`| (None) | **Required.** Must match the URI in your Spotify app settings. |
| `OVERLAY_POSITION` | `top-right` | The corner where the overlay appears. (`top-left`, `top-right`, `bottom-left`, `bottom-right`) |
| `OVERLAY_HOTKEY` | `F7` | (Windows) The global hotkey to toggle the overlay. |
| `OVERLAY_MARGIN` | `24` | The distance in pixels from the screen edges. |
| `OVERLAY_ART_SIZE` | `64` | The size of the album art in pixels. |
| `OVERLAY_CLICK_THROUGH` | `1` | (Windows) `1` enables click-through, `0` disables it. |
| `POLL_INTERVAL_MS` | `1000` | How often (in ms) to check Spotify for changes. 500-1000 is a safe range. |
| `OVERLAY_DEBUG` | `0` | `1` enables debug logging to the console. Though it doesn't do much. |

---

## Running the Application

With your virtual environment activated and `.env` file configured, start the application:

```bash
python main.py
```

On first launch, a browser window will open for Spotify authentication. Log in to grant permission.

## Keybindings

You can toggle the overlay's visibility using a keybinding. The implementation differs by OS.

### Windows
The global toggle hotkey is managed by `pynput` and is defined by `OVERLAY_HOTKEY` (default: `F7`).

### Linux (Wayland/Hyprland)
Toggling is handled by an IPC command. Configure your window manager or hotkey daemon to execute:
```sh
socat - unix-connect:/tmp/spoverlay.sock
```
**Example for Hyprland (`hyprland.conf`):**
```
# Bind F7 to toggle the Spoverlay visibility
bind = , F7, exec, socat - unix-connect:/tmp/spoverlay.sock
```

You can change `F7` to any key combination you prefer.

## Building an Executable

A `spoverlay.spec` file is included for building with PyInstaller.

```bash
pyinstaller spoverlay.spec
```

The executable will be located in the `dist/spoverlay` directory.

## Wayland Window Rules
For compositors like Hyprland, add window rules to manage the overlay's behavior.

**Example for Hyprland (`hyprland.conf`):**
```
windowrulev2 = float, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = nofocus, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = noinitialfocus, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = pin, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = noborder, class:^(spoverlay)$
windowrulev2 = noshadow, class:^(spoverlay)$

# For OVERLAY_POSITION=top-left
# windowrulev2 = move 30 48, class:^(spoverlay)$
# For OVERLAY_POSITION=top-right
windowrulev2 = move 81% 48, class:^(spoverlay)$

# Example of minimal env variables
env = SPOTIFY_CLIENT_ID,your_client_id_here
env = SPOTIFY_REDIRECT_URI,http://127.0.0.1:8080/callback
env = POLL_INTERVAL_MS,700
```
