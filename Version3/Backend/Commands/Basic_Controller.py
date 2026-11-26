import subprocess
import webbrowser
import datetime

from AI_Chart_Data_Manager import record_skill


def open_application(app_name: str):
    app_name = app_name.lower().strip()
    try:
        if "notepad" in app_name:
            subprocess.Popen(["notepad.exe"])
            return "Notepad opened successfully."
        elif "chrome" in app_name or "browser" in app_name:
            subprocess.Popen(["cmd", "/c", "start", "", "chrome"])
            return "Google Chrome opened successfully."
        elif "code" in app_name or "vs code" in app_name:
            subprocess.Popen(["cmd", "/c", "start", "", "code"])
            return "Visual Studio Code opened successfully."
        elif "whatsapp" in app_name:
            subprocess.Popen(["cmd", "/c", "start", "", "whatsapp:"])
            return "WhatsApp opened successfully."
        return f"Sorry, I don't know how to open {app_name}."
    except Exception as e:
        return f"Error opening application: {str(e)}"

def search_google(query: str):
    query = query.strip()
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searched Google for {query}."

def open_website(url: str):
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
    webbrowser.open(url)
    return f"Opened website {url} successfully."

def get_system_time():
    current_time = datetime.datetime.now().strftime("%I:%M %p, %A, %B %d, %Y")
    return f"The current date and time is {current_time}."


# --- SKILLS_TOOL ---

def save_skill_tool(
    skill_id: str,
    title: str,
    triggers: list[str],
    steps: list[str],
    fix_notes: str = "",
) -> str:
    try:
        saved = record_skill(
            skill_id=skill_id,
            title=title,
            triggers=triggers,
            steps=steps,
            fix_notes=fix_notes,
        )
        return f"Saved procedural skill '{saved['id']}' ({saved['title']}) to skills_memory.json."
    except Exception as e:
        return f"Failed to save skill: {e}"