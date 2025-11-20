
# Spoverlay - Spotify Overlay

A lightweight Qt6 overlay that displays the currently playing Spotify Track.

<img width="357" height="102" alt="image" src="https://github.com/user-attachments/assets/13a355cd-a9e6-4bef-b193-ade4c7344857" />

# Requirements

- Python 3.8+
- Spotify Developer API Credentials

# Dependencies

- PySide6
- python-dotenv
- spotipy
- python-xlib
- pyinstaller
- Pillow
- pywin32
- pynput

> Notes:
> Both of these dependencies are needed on Windows
> - **pywin32** - responsible for click-through support. <br>
> - **pynput** - is only listening for a target key you can configure with an environment variable. <br>
>
> Check for yourself: `overlay/core/hotkey_manager.py` and `overlay/ui/overlay_window.py`.

## Setup for development
Venv for local project dependencies
```bash
python -m venv venv
```

### Source/Activate the venv (choose the script that matches your system) </br>
Linux:
```bash
source venv/bin/activate
```

Windows:
```bash
venv\Scripts\Activate.ps1
```

### Install all the dependencies using pip
```bash
pip install python-dotenv spotipy PySide6 PySide6-stubs pynput python-xlib types-python-xlib pyinstaller Pillow
```

## Install pywin32 separately if you're on Windows
```bash
pip install pywin32
```

# Configuration

- Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Create a new application
- Add a redirect URI: http://127.0.0.1:8080/callback
- Check Web API in the planning to use section
- Copy your Client ID and Client Secret
- Create a .env file in the project root
- Replace variables with your Client ID and Secret

# Template for the .env

### Spotify API Credentials
```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback
```

### UI Settings (optional, just copy these if unsure)
```env
OVERLAY_POSITION=top-right  # Options: top-left, top-right, bottom-left, bottom-right
OVERLAY_HOTKEY=f7
OVERLAY_MARGIN=16
OVERLAY_ART_SIZE=64
OVERLAY_CLICK_THROUGH=1     # 0 to disable click-through
OVERLAY_DEBUG=0             # 1 to enable debug mode
```

# Running the Application

Execute the main script (don't forget to active the venv):
```bash
python main.py
```

On first run, the app will open a browser window for Spotify Authentication. </br>
Log in and authorize the application. After that it should just start right away. </br>

# Building with PyInstaller
```bash
pyinstaller spoverlay.spec
```

You should be able to find the executable in the parent directory followed by /dist/spoverlay/

# Usage

The overlay will automatically appear when you play music on Spotify and hide when playback is stopped. </br>
Left-clicking the tray icon should behave like a toggle as well or you can right click to open the tray menu. </br>

# Wayland
This is the main environment for which the overlay is being developed. </br>

### Window Rules
```
windowrulev2 = float, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = nofocus, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = noinitialfocus, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = pin, class:^(spoverlay)$, title:^(spoverlay)$
windowrulev2 = noborder, class:^(spoverlay)$
windowrulev2 = noshadow, class:^(spoverlay)$
windowrulev2 = move 81% 48, class:^(spoverlay)$
```

You can play around with **move 81% 48** until it is to your liking. </br>

### Environment Variables
```
env = SPOTIFY_CLIENT_ID,<your_client_id>
env = SPOTIFY_CLIENT_SECRET,<your_client_secret>
env = SPOTIFY_REDIRECT_URI,http://127.0.0.1:8080/callback
env = OVERLAY_ART_SIZE,63
env = POLL_INTERVAL_MS,700
```

You can decrease the poll interval to make the overlay "quicker", but don't go crazy low with it. 500-1000 should be good enough of a range. <br>

I wouldn't play with the art size beyond this range 60-64 since a lot of stuff like padding and spacing is hard-coded at the moment.

# Keybindings
Most probably broken though. Too lazy to fix it since I don't need it. <br>
But on Windows the keybind definitely works. <br>

> F7: Toggle overlay visibility
