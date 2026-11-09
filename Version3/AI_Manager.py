import os
import json
from PIL import Image
from dotenv import load_dotenv
from google import genai
from groq import Groq
from System_Command_Handler import available_tools, tools_schema

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# 1. Initialize Clients
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
groq_client = Groq(api_key=GROK_API_KEY)

# --- GROQ (Standard Text & Tool Calling) ---
def ask_groq(prompt, history, Speaker_name="unknown"):
    formatted_message = f"[{Speaker_name.capitalize()}]: {prompt}"
    history.append({"role": "user", "content": formatted_message})
    
    max_turns = 5  # Prevents infinite loops
    turn = 0
    
    try:
        while turn < max_turns:
            turn += 1
            completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=history,
                tools=tools_schema,
                tool_choice="auto",
                max_tokens=1024,
            )
            
            response_message = completion.choices[0].message
            
            # If Groq didn't call any tools, it's giving the final text answer
            if not response_message.tool_calls:
                ai_reply = response_message.content.strip() if response_message.content else "Done!"
                history.append({"role": "assistant", "content": ai_reply})
                return ai_reply
                
            # Serialize and append tool calls
            tool_calls_serialized = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in response_message.tool_calls
            ]
            
            history.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": tool_calls_serialized
            })
            
            # Execute each requested tool
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    function_args = {}
                
                print(f"[Executing Tool: {function_name} with args {function_args}]")
                
                if function_name in available_tools:
                    tool_function = available_tools[function_name]
                    try:
                        tool_result = tool_function(**function_args)
                    except Exception as e:
                        tool_result = f"Error executing tool: {str(e)}"
                    
                    history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(tool_result)
                    })
                    
        return "Reached maximum execution turns without finishing."

    except Exception as e:
        print(f"Tool API Error Details: {e}")
        return "Sorry, I ran into an error processing that command."

# --- GEMINI (Vision / Screen Sharing Assistant) with Fallback ---
def ask_gemini_vision(prompt, history, Speaker_name="unknown", screenshot_path=None):
    formatted_message = f"[{Speaker_name.capitalize()}]: {prompt}"
    history.append({"role": "user", "content": formatted_message})
    
    models_to_try = ['gemini-3.8-flash', 'gemini-3.6-flash']
    
    for model_name in models_to_try:
        try:
            if screenshot_path:
                img = Image.open(screenshot_path)
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=[prompt, img],
                )
            else:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=str(history),
                )
                
            ai_reply = response.text.strip()
            history.append({"role": "assistant", "content": ai_reply})
            return ai_reply
        except Exception as e:
            print(f"Gemini API Error with {model_name}: {e}")
            continue
            
    return "I encountered a temporary high-demand server error. Please try asking again."