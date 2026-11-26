import subprocess
import time
import threading
import webbrowser
import pydirectinput
import pygetwindow as gw

# Track background automation threads
automation_active = False

def launch_roblox(game_id: str = ""):
    """Launches the Roblox client or opens a specific game experience by Place ID."""
    try:
        if game_id.strip():
            # Opens a specific Roblox game directly via URL protocol
            url = f"roblox://placeId={game_id.strip()}"
            webbrowser.open(url)
            return f"Launching Roblox experience ID {game_id}..."
        else:
            # Opens the main Roblox desktop player
            subprocess.Popen(["cmd", "/c", "start", "roblox:"], shell=True)
            return "Roblox client launched successfully."
    except Exception as e:
        return f"Failed to launch Roblox: {str(e)}"

def focus_roblox_window():
    """Finds and brings the Roblox window to the foreground."""
    windows = gw.getWindowsWithTitle("Roblox")
    if windows:
        win = windows[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.5)
        return True
    return False

def perform_game_action(action: str, duration: float = 2.0):
    """Performs hardware-level inputs inside the active Roblox window."""
    if not focus_roblox_window():
        return "Roblox is not currently running or couldn't be found."

    action = action.lower().strip()
    try:
        if action in ["walk forward", "move forward", "forward"]:
            pydirectinput.keyDown('w')
            time.sleep(duration)
            pydirectinput.keyUp('w')
            return f"Walked forward for {duration} seconds."

        elif action in ["walk back", "backward", "back"]:
            pydirectinput.keyDown('s')
            time.sleep(duration)
            pydirectinput.keyUp('s')
            return f"Walked backward for {duration} seconds."

        elif action == "jump":
            pydirectinput.press('space')
            return "Jumped in-game."

        elif action == "spin":
            pydirectinput.keyDown('right')
            time.sleep(duration)
            pydirectinput.keyUp('right')
            return f"Spun camera for {duration} seconds."

        else:
            return f"Unknown game action: {action}"
    except Exception as e:
        return f"Game input error: {str(e)}"

def _anti_afk_worker():
    """Background loop that jumps every 60 seconds to prevent idle kick."""
    global automation_active
    while automation_active:
        if focus_roblox_window():
            pydirectinput.press('space')
        # Sleep in 1-second chunks so it stops quickly when toggled off
        for _ in range(60):
            if not automation_active:
                break
            time.sleep(1)

def toggle_anti_afk(state: str):
    """Starts or stops the background Anti-AFK thread."""
    global automation_active
    state = state.lower().strip()

    if state in ["start", "on", "enable"]:
        if automation_active:
            return "Anti-AFK mode is already running."
        automation_active = True
        threading.Thread(target=_anti_afk_worker, daemon=True).start()
        return "Anti-AFK mode enabled. Jarvis will keep your character active."

    elif state in ["stop", "off", "disable"]:
        automation_active = False
        return "Anti-AFK mode stopped."

    return "Specify 'start' or 'stop' for Anti-AFK mode."