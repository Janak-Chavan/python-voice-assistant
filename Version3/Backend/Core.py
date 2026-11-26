#Core.py
#--------------------------------------------------------------------------------
#IMPORTS
import time

#Import AI_Chart_Data_Manager functions
import AI_Chart_Data_Manager as AI_Chart_Data_Manager

#Import configuration variables from Configuration.py
import System_Configuration as System_Configuration

#Import System_Command_Handle variables from System_Command_Handle.py
import System_Command_Handler as System_Command_Handle

#Import Listen_Manager functions
from Listen_System import listen

#Import Speech_Manager functions
from Speech_System import speak, stop_speaking, is_speaking

#Import AI_Manager functions
from AI_Manager import ask_groq, ask_local_vision

#------------------------------------------------------------------------------------

# wake up words varient so it takes when local STT is working
wake_words = [
    System_Configuration.AI_NAME.lower(),
    "jervis",
    "travis",
    "jarvis's",
    "jarvis.",
    "jarvis,",
    "jardis"
]

# Requests

def _is_screen_request(cmd_lower: str) -> bool:
    screen_triggers = [
        "look at",
        "check my",
        "what's on",
        "whats on",
        "what is on",
        "read what",
        "read the",
    ]
    return any(phrase in cmd_lower for phrase in screen_triggers)

"""
def _is_recall_request(cmd_lower: str) -> bool:
    recall_triggers = [
        "remember when",
        "earlier we",
        "last time",
        "what did we",
        "did we talk about",
        "past chat",
        "previous conversation",
        "earlier chat",
        "what happened earlier",
    ]
    return any(phrase in cmd_lower for phrase in recall_triggers)
"""

# Handels basic local command e.g:- open notepad etc.
def local_intent_router(command):
    #Lower Caseing the command
    lower_case_command = str.lower(command)

    #First Check for all WH type command
    if "what" in lower_case_command:
        if "time" in lower_case_command or "date" in lower_case_command:
            return System_Command_Handle.get_system_time()
    
    if "what" in lower_case_command or "how" in lower_case_command:
        return None
    
    #Non-WH command
    #All application open command
    if "open" in lower_case_command or "run" in lower_case_command:
        if "notepad" in lower_case_command or "note pad" in lower_case_command:
            return System_Command_Handle.open_application("notepad")
        elif "chrome" in lower_case_command or "browser" in lower_case_command:
            return System_Command_Handle.open_application("chrome")
        elif "code" in lower_case_command or "vs code" in lower_case_command:
            return System_Command_Handle.open_application("vs code")
        elif "whatsapp" in lower_case_command:
            return System_Command_Handle.open_application("whatsapp")
        elif "chart interface" in lower_case_command:
            return System_Command_Handle.open_website("http://localhost:8000/")
    #If nothing match then return none
    return None

# Core command process here
def Command_processer(command, conversation_history, speaker):
    cmd_lower = command.lower()
    router_output = local_intent_router(cmd_lower)

    if router_output:
        return router_output

    elif _is_screen_request(cmd_lower):
        image_path = AI_Chart_Data_Manager.Get_Optimized_Screenshot(640)
        screen_summary = ask_local_vision(image_path)
        vision_prompt = (
            f"[Local Screen Analysis]: {screen_summary}\n"
            f"[User Request]: {command}\n"
            "Use the screen analysis to answer or call any relevant tool (such as gaming controls)."
        )

        return ask_groq(vision_prompt, conversation_history, speaker)

    else:
        return ask_groq(command, conversation_history, speaker)

# Voice loop
def start_voice_loop():
    speak("Voice system started.")

    while True:
        command, speaker = listen()

        if not command:
            time.sleep(0.1)
            continue

        cmd_lower = command.lower()

        if System_Configuration.SYSTEM_COMMANDS_ACCESS_KEY in cmd_lower:
            if any(k in cmd_lower for k in ("end", "shutdown", "exit", "close", "stop")):
                speak("Shutting down. Goodbye!")
                time.sleep(1.5)
                break

        if any(w in cmd_lower for w in wake_words):
            if is_speaking():
                stop_speaking()

            # Pre-capture screenshot/vision outside lock so slow vision doesn't block web requests
            pre_vision_prompt = None
            if _is_screen_request(cmd_lower) and not local_intent_router(cmd_lower):
                image_path = AI_Chart_Data_Manager.Get_Optimized_Screenshot(640)
                speak("Let me take a look.")
                screen_summary = ask_local_vision(image_path)
                pre_vision_prompt = (
                    f"[Local Screen Analysis]: {screen_summary}\n"
                    f"[User Request]: {command}\n"
                    "Use the screen analysis to answer or call any relevant tool (such as gaming controls)."
                )

            def _turn(history):
                if pre_vision_prompt is not None:
                    return ask_groq(pre_vision_prompt, history, speaker)
                return Command_processer(command, history, speaker)

            result = AI_Chart_Data_Manager.run_with_history(_turn)

            speak(result)

# This lines are Just for testing
if __name__ == "__main__":
    start_voice_loop()