import os
import subprocess
import webbrowser

def create_and_write_file(filename: str, content: str):
    try:
        parent_dir = os.path.dirname(filename)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filename}"
    except Exception as e:
        return f"Something went wrong while creating or writing. error:- {e}"

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
        elif file_ext == "png":
            os.system(f"start {filename}" if os.name == "nt" else f"xdg-open {filename}")
            return f"successfully open/run the {filename}"
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