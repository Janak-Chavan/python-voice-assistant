from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import re
import threading

from AI_Chart_Data_Manager import load_history, history_lock, run_with_history
from Core import start_voice_loop, Command_processer
import System_Configuration as System_Configuration

def extract_display_content(role: str, content: str) -> str:
    if not isinstance(content, str):
        return ""
    if role != "user":
        return content

    # Grab text after "[Current Request]:" if present
    match = re.search(r"\[Current Request\]:\s*(.+)$", content, flags=re.DOTALL)
    clean_text = match.group(1).strip() if match else content.strip()

    # Optional: strip leading "[Janak]: " prefix for UI bubbles
    clean_text = re.sub(r"^\[[^\]]+\]:\s*", "", clean_text)
    return clean_text


app = FastAPI(title="Jarvis V3 Dual-Engine")

os.makedirs("Frontend", exist_ok=True)
os.makedirs(System_Configuration.TEMPORARY_FOLDER_PATH, exist_ok=True)

temp_mount_path = "/" + System_Configuration.TEMPORARY_FOLDER_PATH.strip("/\\").replace("\\", "/")
app.mount("/Frontend", StaticFiles(directory="Frontend"), name="Frontend")
app.mount(temp_mount_path, StaticFiles(directory=System_Configuration.TEMPORARY_FOLDER_PATH), name="Temporary")


class CommandRequest(BaseModel):
    prompt: str
    speaker: str = "Janak"


@app.get("/", response_class=HTMLResponse)
def read_root():
    html_path = "Frontend/index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Jarvis UI template not found in Frontend/index.html</h1>"


@app.get("/api/history")
def get_history():
    try:
        with history_lock:
            history = load_history()
        
        clean_history = [
            {
                "role": msg["role"],
                "content": extract_display_content(msg["role"], msg["content"]),
                "attachment": msg.get("attachment"),
            }
            for msg in history
            if msg.get("role") in ["user", "assistant"]
            and msg.get("entry_type") != "tool_log"
            and msg.get("content")
        ]   
        return {"status": "success", "history": clean_history}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/command")
def handle_command(req: CommandRequest):
    try:
        reply = run_with_history(
            lambda history: Command_processer(req.prompt, history, req.speaker)
        )
        return {"status": "success", "response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
def start_voice_assistant_thread():
    print(">>> Starting Jarvis Local Voice Loop in background thread...")
    voice_thread = threading.Thread(target=start_voice_loop, daemon=True)
    voice_thread.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)