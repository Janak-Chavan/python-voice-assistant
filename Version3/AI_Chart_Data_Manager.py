import json
import os
import pyautogui
from pathlib import Path

#Import configuration variables from Configuration.py
import System_Configuration as System_Configuration

# Data structure for storing conversation history
def load_history():
    if os.path.exists(System_Configuration.HISTORY_FILE):
        try:
            with open(System_Configuration.HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Default initial state if no file exists
    return [
        {
            "role": "system",
            "content": f"You are {System_Configuration.AI_NAME}, a helpful AI assistant and voice agent. Keep your answers conversational, concise, and complete.You will get the speaker name in the prompt, so you can address them by name. If the speaker name is unknown, address them as 'User'."
        }
    ]

def save_history(history):
    try:
        with open(System_Configuration.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False

def Get_Screenshot():
    """Captures the primary monitor screen and returns the file path."""
    # Ensure temporary folder exists
    temp_dir = Path(System_Configuration.TEMPORARY_FOLDER_PATH)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    screenshot_path = temp_dir / "screen_capture.png"
    
    # Take screenshot and save
    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    
    print(f"Screen captured successfully at {screenshot_path}")
    return str(screenshot_path)