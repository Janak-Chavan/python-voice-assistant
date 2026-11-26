import os
import re
import json
from PIL import Image
from dotenv import load_dotenv
from google import genai
from groq import Groq
import ollama
import threading
from AI_Chart_Data_Manager import (
    history_lock,
    build_active_memory,
    load_concentrated_memory,
    save_concentrated_memory,
    record_artifacts_from_text,
    save_active_history,
)
from System_Command_Handler import available_tools, TOOL_CATEGORIES, ROUTER_SCHEMA
from Speech_System import speak

load_dotenv()

LOCAL_VISION_MODEL = "Nac/smolvlm"
# LOCAL_VISION_MODEL = "ahmadwaqar/smolvlm2-256m-video:q8_0"
LOCAL_FALLBACK_MODEL = "qwen2.5:0.5b"


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# 1. Initialize Clients
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
groq_client = Groq(api_key=GROK_API_KEY)


def _build_active_schemas(category: str | None = None) -> list:
    meta_tools = [
        t for t in ROUTER_SCHEMA
        if isinstance(t, dict) and t.get("function", {}).get("name") == "select_tool_category"
    ]
    if not category or category == "router":
        return list(ROUTER_SCHEMA)

    cat_tools = TOOL_CATEGORIES.get(category)
    if not cat_tools:
        return list(ROUTER_SCHEMA)

    existing_names = {
        t.get("function", {}).get("name")
        for t in cat_tools
        if isinstance(t, dict)
    }
    extra_meta = [
        m for m in meta_tools
        if m.get("function", {}).get("name") not in existing_names
    ]
    return list(cat_tools) + extra_meta

# --- GROQ (Basic Chart / Tool Calling) ---
def ask_groq(prompt, history, Speaker_name="unknown"):
    formatted_message = f"[{Speaker_name.capitalize()}]: {prompt}"
    history.append({"role": "user", "content": formatted_message})

    # Active Memory = System prompt + Concentrated Memory + Episodes Memory + Skill Memory + recent turns
    active_messages = build_active_memory(
        history,
        max_recent=3
    )

    last_tool_sig = None
    saved_skill_count = 0
    max_turns = 8
    turn = 0
    active_schemas = _build_active_schemas("router")

    try:
        while turn < max_turns:
            turn += 1
            switched_this_turn = False

            def call_api(messages):
                return groq_client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=messages,
                    tools=active_schemas,
                    tool_choice="auto",
                    max_tokens=2048,
                )

            try:
                completion = call_api(active_messages)
            except Exception as api_err:
                err_str = str(api_err)
                if "413" in err_str or "rate_limit_exceeded" in err_str or "tokens" in err_str:
                    print("[Token limit (TPM) reached. Trimming active messages and retrying...]")
                    sys_msgs = [m for m in active_messages if m.get("role") == "system"][:4]
                    tail_msgs = [m for m in active_messages if m.get("role") != "system"][-4:]
                    active_messages = sys_msgs + tail_msgs
                    completion = call_api(active_messages)
                else:
                    save_active_history(active_messages)
                    raise api_err

            response_message = completion.choices[0].message

            if not response_message.tool_calls:
                reply_preview = (response_message.content or "").lower()
                cant_read = any(
                    phrase in reply_preview
                    for phrase in ("can't read", "cannot read", "don't have a way to read", "no direct access to files")
                )
                if turn <= 2 and "[Tool Hint]:" in prompt and cant_read:
                    active_messages.append({
                        "role": "user",
                        "content": (
                            "You DO have a read_file tool under category 'files'. "
                            "Call select_tool_category with category='files' now."
                        ),
                    })
                    continue

                ai_reply = response_message.content.strip() if response_message.content else "Done!"
                history.append({"role": "assistant", "content": ai_reply})
                maybe_summarize_history(history)
                record_artifacts_from_text(ai_reply)
                save_active_history(active_messages)
                return ai_reply

            tool_calls_serialized = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response_message.tool_calls
            ]

            active_messages.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": tool_calls_serialized,
            })

            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                try:
                    raw_args = tool_call.function.arguments.replace("\u00a0", " ")
                    function_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    function_args = {}

                if function_name == "select_tool_category":
                    chosen_cat = str(function_args.get("category", "basic")).strip().lower()
                    if switched_this_turn:
                        tool_result = (
                            f"Already switched category in this step. Execute a tool in the active category "
                            f"first before switching to '{chosen_cat}'."
                        )
                    elif chosen_cat == "router":
                        switched_this_turn = True
                        active_schemas = _build_active_schemas("router")
                        tool_result = "Returned to router. Select the next category directly."
                        print("[Switched Active Tools -> ROUTER]")
                    elif chosen_cat in TOOL_CATEGORIES:
                        switched_this_turn = True
                        active_schemas = _build_active_schemas(chosen_cat)
                        tool_names = [
                            t.get("function", {}).get("name")
                            for t in TOOL_CATEGORIES[chosen_cat]
                            if isinstance(t, dict)
                        ]
                        tool_result = (
                            f"Category '{chosen_cat}' unlocked. Active tools: {', '.join(tool_names)}. "
                            f"Call one of these tools now before switching categories."
                        )
                        print(f"[Switched Active Tools -> {chosen_cat.upper()}]")
                    else:
                        avail = ", ".join(list(TOOL_CATEGORIES.keys()) + ["router"])
                        tool_result = f"Invalid category '{chosen_cat}'. Available: {avail}."
                
                elif function_name == "save_skill_tool":
                    if saved_skill_count >= 1:
                        tool_result = (
                            "Skill already saved during this turn. Do NOT call save_skill_tool again—"
                            "give your final response to the user if task is complet."
                        )
                    else:
                        saved_skill_count += 1
                        print(f"[Executing Tool: {function_name}]")
                        try:
                            tool_result = available_tools[function_name](**function_args)
                        except Exception as e:
                            tool_result = f"Error executing tool: {str(e)}"

                elif function_name in available_tools:
                    call_sig = (function_name, json.dumps(function_args, sort_keys=True))
                    if call_sig == last_tool_sig:
                        tool_result = (
                            f"Already executed {function_name} with these exact arguments. "
                            "Do not repeat it—switch categories or give your final answer."
                        )
                    else:
                        last_tool_sig = call_sig
                        print(f"[Executing Tool: {function_name}]")
                        tool_function = available_tools[function_name]
                        try:
                            tool_result = tool_function(**function_args)
                            args_str = json.dumps(function_args, ensure_ascii=False)
                            record_artifacts_from_text(f"{args_str} {tool_result}", source_tool=function_name)
                        except Exception as e:
                            tool_result = f"Error executing tool: {str(e)}"

                    if function_name == "generate_chart" and "[CHART_IMG:" in str(tool_result):
                        chart_tag = str(tool_result).split("]")[0] + "]"
                        response_message.content = (response_message.content or "") + f" {chart_tag}"

                else:
                    tool_result = f"Tool '{function_name}' not found."

                history.append({
                    "role": "assistant",
                    "entry_type": "tool_log",
                    "tool_name": function_name,
                    "arguments": function_args,
                    "content": f"[Tool: {function_name}] {str(tool_result)[:250]}",
                })

                active_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": str(tool_result),
                })

        return "Reached maximum execution turns without finishing."
    except Exception as e:
        print(f"Tool API Error Details: {e}")
        print("[Switching to last-resort offline local model...]")
        speak("offline local model Activated... it can take some time")
        if history and history[-1].get("role") == "user" and history[-1].get("content") == formatted_message:
            history.pop()
        return ask_local_fallback(prompt, history, Speaker_name)

# --- GEMINI (Vision / Screen Sharing Assistant) with Fallback ---
def ask_gemini_vision(prompt, history, Speaker_name="unknown", screenshot_path=None):
    formatted_message = f"[{Speaker_name.capitalize()}]: {prompt}"
    
    # Keep history lean for vision calls to reduce payload weight
    current_payload = [formatted_message]
    
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            img = Image.open(screenshot_path)
            current_payload.append(img)
        except Exception as e:
            print(f"Error loading image into payload: {e}")

    # Use the fastest available flash model identifier
    # Use the correct current model identifier
    models_to_try = ['gemini-3.8-flash', 'gemini-3.6-flash']
    
    for model_name in models_to_try:
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=current_payload,
            )
                
            ai_reply = response.text.strip()
            history.append({"role": "user", "content": formatted_message})
            history.append({"role": "assistant", "content": ai_reply})
            return ai_reply
        except Exception as e:
            print(f"Gemini API Error with {model_name}: {e}")
            continue
            
    return "I encountered a high-demand server error with vision processing. Please try again."

# --- LOCAL VISION (SmolVLM) PROMPTS ---
VISION_TASKS = {
    "default": {
        "prompt": "In 1-2 short sentences, state what app or screen is open and the key visible elements like animal etc.",
        "num_predict": 70,
        "temperature": 0.1,
    },
    "gaming": {
        "prompt": "Briefly list in 20 to 30 words only game state, obstacles, players, and UI buttons.",
        "num_predict": 40,
        "temperature": 0.1,
    },
    "read_text": {
        "prompt": "Summarize the main visible text, errors, or labels clearly.",
        "num_predict": 100,
        "temperature": 0.1,
    },
}

# --- LOCAL VISION (SmolVLM) ---
def ask_local_vision(screenshot_path, task="default", custom_prompt=None, num_predict=None, temperature=None, keep_alive="2m"):
    screen_summary = "Screen capture unavailable."
    task_cfg = VISION_TASKS.get(task, VISION_TASKS["default"])

    prompt_text = custom_prompt if custom_prompt is not None else task_cfg["prompt"]
    predict_limit = num_predict if num_predict is not None else task_cfg["num_predict"]
    temp_value = temperature if temperature is not None else task_cfg["temperature"]

    if screenshot_path and os.path.exists(screenshot_path):
        try:
            local_res = ollama.chat(
                model=LOCAL_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt_text,
                        "images": [screenshot_path],
                    }
                ],
                options={
                    "num_predict": predict_limit,
                    "temperature": temp_value,
                },
                keep_alive=keep_alive,
            )
            extracted = (local_res.get("message", {}).get("content") or "").strip()
            if extracted:
                screen_summary = extracted
                print(f"[Local Vision ({LOCAL_VISION_MODEL} | {task})]: {screen_summary}")
        except Exception as e:
            print(f"[Local Vision Error]: {e}")

    return screen_summary

# -- LOCAL TEXT AI --
def ask_local_fallback(prompt, history, Speaker_name="unknown", keep_alive="3m"):
    """Last-resort offline text reply using qwen2.5:0.5b when Groq is unreachable."""
    formatted_message = f"[{Speaker_name.capitalize()}]: {prompt}"
    recent_turns = [
        m for m in history[-4:]
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    ]
    messages = [
        {
            "role": "system",
            "content": "You are Jarvis. Reply briefly, directly, and clearly in 1-3 short sentences.",
        },
        *recent_turns,
        {"role": "user", "content": formatted_message},
    ]

    try:
        res = ollama.chat(
            model=LOCAL_FALLBACK_MODEL,
            messages=messages,
            options={
                "num_ctx": 512,
                "num_predict": 90,
                "temperature": 0.2,
            },
            keep_alive=keep_alive,
        )
        reply = (res.get("message", {}).get("content") or "").strip()
        if reply:
            history.append({"role": "user", "content": formatted_message})
            history.append({"role": "assistant", "content": reply})
            return reply
    except Exception as local_err:
        print(f"[Offline Fallback Model Error]: {local_err}")

    return "I can't reach the cloud right now, and my offline model couldn't generate a reply."

# -- MEMORY_STUFF --
def _summarize_chunk_worker(chunk, new_index):
    """Updates per-user personal summaries, per-project summaries, and chunk summary."""
    transcript = "\n".join(
    f"{m.get('role', '').upper()}: {m.get('content', '')}"
        for m in chunk
        if m.get("role") in ("user", "assistant")
        and m.get("entry_type") != "tool_log"
        and isinstance(m.get("content"), str)
    )
    if not transcript.strip():
        return

    with history_lock:
        existing_conc = load_concentrated_memory()

    existing_snapshot = {
        "user_data": existing_conc.get("user_data", {}),
        "project_data": existing_conc.get("project_data", {}),
    }

    extraction_prompt = (
        "You maintain structured memory for an AI assistant.\n"
        "Look at EXISTING_MEMORY and the NEW_CONVERSATION chunk (around 8 turns).\n"
        "1. 'user_data': For each speaker/user mentioned or present, write/update a brief personal summary "
        "(enough detail to capture who they are, their preferences, and key context without losing prior points).\n"
        "2. 'project_data': For each project discussed, map project_name -> brief summary of the project "
        "(capturing architecture, goals, and key updates).\n"
        "3. 'summary': Write a concise summary of this conversation chunk (around 5-8 short lines / key points).\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"user_data": {"speaker_name": "brief personal summary"}, '
        '"project_data": {"project_name": "brief project summary"}, '
        '"summary": "concise summary of this conversation chunk"}\n\n'
        f"EXISTING_MEMORY:\n{json.dumps(existing_snapshot, ensure_ascii=False)}\n\n"
        f"NEW_CONVERSATION:\n{transcript}"
    )

    try:
        res = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": extraction_prompt}],
            max_tokens=700,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        raw = (res.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end + 1]

        # Strip raw control characters outside standard whitespace so json.loads doesn't choke
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", raw)

        try:
            parsed = json.loads(sanitized, strict=False)
        except json.JSONDecodeError:
            # Last-resort repair for trailing commas before } or ]
            repaired = re.sub(r",\s*([}\]])", r"\1", sanitized)
            parsed = json.loads(repaired, strict=False)

        with history_lock:
            conc = load_concentrated_memory()

            if isinstance(parsed.get("user_data"), dict):
                for u_key, u_val in parsed["user_data"].items():
                    clean_key = str(u_key).strip().lower()
                    clean_val = str(u_val).strip()
                    if clean_key and clean_val:
                        conc["user_data"][clean_key] = clean_val

            if isinstance(parsed.get("project_data"), dict):
                for p_key, p_val in parsed["project_data"].items():
                    clean_key = str(p_key).strip()
                    clean_val = str(p_val).strip()
                    if clean_key and clean_val:
                        conc["project_data"][clean_key] = clean_val

            summary_text = str(parsed.get("summary") or "").strip()
            if summary_text and summary_text not in conc["summaries"]:
                conc["summaries"].append(summary_text)

            conc["summaries"] = conc["summaries"][-10:]
            conc["last_summarized_index"] = max(conc.get("last_summarized_index", 1), new_index)
            save_concentrated_memory(conc)
            print("[Concentrated Memory Updated]")
    except Exception as e:
        print(f"[Memory Summarization Skipped]: {e}")

def maybe_summarize_history(full_history, keep_recent=8, batch_size=8):
    """Triggers background summarization when enough messages have rolled out of active memory."""
    conc = load_concentrated_memory()
    start_idx = min(conc["last_summarized_index"], len(full_history))
    cutoff_idx = len(full_history) - keep_recent

    if cutoff_idx - start_idx >= batch_size:
        chunk = list(full_history[start_idx:cutoff_idx])
        threading.Thread(
            target=_summarize_chunk_worker,
            args=(chunk, cutoff_idx),
            daemon=True,
        ).start()
