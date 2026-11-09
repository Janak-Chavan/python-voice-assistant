import subprocess
import webbrowser
import datetime
import os

def open_application(app_name: str):
    app_name = app_name.lower().strip()
    try:
        if "notepad" in app_name:
            subprocess.Popen(["notepad.exe"])
            return "Notepad opened successfully."
        elif "chrome" in app_name or "browser" in app_name:
            # Use shell=True carefully or direct executable path to avoid shell injection risks
            subprocess.Popen(["cmd", "/c", "start", "chrome"], shell=True)
            return "Google Chrome opened successfully."
        elif "code" in app_name or "vs code" in app_name:
            subprocess.Popen(["code"], shell=True)
            return "Visual Studio Code opened successfully."
        elif "whatsapp" in app_name:
            subprocess.Popen(["cmd", "/c", "start", "whatsapp:"], shell=True)
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

def create_and_write_file(filename: str, content: str):
    try:
        # Save inside a safe workspace folder or current directory
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created and wrote to {filename}."
    except Exception as e:
        return f"Error writing file: {str(e)}"

def read_file(filename: str):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        return f"Content of {filename}:\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def run_script(filename: str):
    try:
        file_ext = filename.split('.')[-1].lower()
        
        # 1. Handle HTML directly in browser
        if file_ext == "html":
            file_path = os.path.abspath(filename)
            webbrowser.open(f"file://{file_path}")
            return f"Successfully opened {filename} in your default web browser."

        # 2. Handle executable scripts via command line
        if file_ext == "py":
            cmd = ["python", filename]
        elif file_ext == "js":
            cmd = ["node", filename]
        elif file_ext == "cpp":
            exe_name = filename.rsplit('.', 1)[0] + (".exe" if os.name == "nt" else "")
            compile_result = subprocess.run(["g++", filename, "-o", exe_name], capture_output=True, text=True)
            if compile_result.returncode != 0:
                return f"C++ Compilation Failed:\n{compile_result.stderr}"
            cmd = [exe_name]
        else:
            return f"Unsupported file type: .{file_ext}"

        # 3. Execute script tools
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            return f"Script executed successfully.\nOutput:\n{result.stdout}"
        else:
            return f"Script failed with errors.\nError Traceback:\n{result.stderr}"
            
    except Exception as e:
        return f"Execution error: {str(e)}"

# Map tool names to actual Python functions
available_tools = {
    "open_application": open_application,
    "search_google": search_google,
    "open_website": open_website,
    "get_system_time": get_system_time,
    "create_and_write_file": create_and_write_file,
    "read_file": read_file,
    "run_script": run_script
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open a local desktop application like Notepad, Chrome, or VS Code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "The name of the application to open."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Search Google for information, queries, or topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query keywords."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Open a specific website or URL directly in the browser, such as youtube.com, github.com, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The website domain or URL to open (e.g., youtube.com)."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_time",
            "description": "Get the current local date and time.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_and_write_file",
            "description": "Create a new file or completely overwrite an existing file with fresh content. Always use this to write or recreate code files when requested.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename":{"type": "string", "description": "name of file with file type ex:- index.html , test.py"},
                    "content":{"type": "string", "description": "content to write or overwrite in the file"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a local file (like a python script or text file etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The name or path of the file to read."}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_script",
            "description": "Execute Python/JS/C++ scripts, or open HTML pages directly in the web browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the file to execute or view (e.g., test.py, index.html)."}
                },
                "required": ["filename"]
            }
        }
    }
]