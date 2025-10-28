
# Spoverlay - Spotify Overlay

A lightweight QT6 overlay that displays your currently playing Spotify tracks on your desktop.

# Requirements

- Python 3.8+
- Spotify Developer API Credentials

# Dependencies

- PySide6 [Use Qt6 APIs in Python]
- python-dotenv [Environment Variables]
- spotipy [Library for Spotify's Web API]

## Setup for development
Venv for local project dependencies
```bash
python -m venv venv
```

Source/Activate the venv (choose the script that matches your system)
```bash
source venv/bin/activate
```

Install all the dependencies using pip
```bash
pip install python-dotenv spotipy PySide6 PySide6-stubs python-xlib types-python-xlib pyinstaller Pillow
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

# Usage

The overlay will automatically appear when you play music on Spotify and hide when playback is stopped.

# Keybindings

F2: Toggle overlay visibility
