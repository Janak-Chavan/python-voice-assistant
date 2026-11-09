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

#Import Speech_Manager functions
from Speech_System import speak, stop_speaking, is_speaking

#Import Listen_Manager functions
from Listen_System import listen

#Import AI_Manager functions
from AI_Manager import ask_groq, ask_gemini_vision

#Import AI_Data_Manager functions
from AI_Chart_Data_Manager import load_history, save_history

#------------------------------------------------------------------------------------

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
    if "notepad" in lower_case_command:
        return System_Command_Handle.open_application("notepad")
    elif "chrome" in lower_case_command or "browser" in lower_case_command:
        return System_Command_Handle.open_application("chrome")
    elif "code" in lower_case_command or "vs code" in lower_case_command:
        return System_Command_Handle.open_application("vs code")
    elif "whatsapp" in lower_case_command:
        return System_Command_Handle.open_application("whatsapp")
    #If nothing match then return none
    return None

if __name__ == "__main__":
    speak("Jarvis is started.")

    # Load past memory from file
    conversation_history = load_history()
    
    while True:
        command, speaker = listen()
        #command = input(">>>>>") #for testing
        # Skip if no speech was detected or speaker wasn't recognized
        if not command :
            time.sleep(0.1)
            continue
        
        if command:
            if System_Configuration.SYSTEM_COMMANDS_ACCESS_KEY in command:
                # Handle system commands
                if "end" in command or "shutdown" in command or "exit" in command or "close" in command or "stop" in command:
                    speak("Shutting down. Goodbye!")
                    time.sleep(1.5)
                    break

            if System_Configuration.AI_NAME in command:
                if is_speaking():
                    stop_speaking()  # Stop any ongoing speech before processing new command

                router_output = local_intent_router(command)
                
                if router_output:
                    # 1. Local command handled instantly
                    speak(router_output)
                    
                elif "look at my screen" in command or "what's on my screen" in command or "check my screen" in command:
                    # 2. Screen vision handled by Gemini
                    speak("Let me take a look.")
                    image_path = AI_Chart_Data_Manager.Get_Screenshot()
                    prompt_text = "Analyze what is visible on my screen and answer: " + command
                    ai_reply = ask_gemini_vision(prompt_text, conversation_history, speaker, image_path)
                    speak(ai_reply)
                    
                else:
                    # 3. Default fallback to Groq
                    ai_reply = ask_groq(command, conversation_history, speaker)
                    speak(ai_reply)

                # Save updated history to disk after every turn
                save_history(conversation_history)