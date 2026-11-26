import json
import os
import re
import mss
import threading
from pathlib import Path
from PIL import Image
import System_Configuration as System_Configuration

history_lock = threading.Lock()

# -- AI_MEMORY_FILE --

def run_with_history(fn):
    """Loads latest history from disk, runs fn(history), and saves under history_lock."""
    with history_lock:
        history = load_history()
        result = fn(history)
        save_history(history)
        return result

def load_history():
    if os.path.exists(System_Configuration.HISTORY_FILE):
        try:
            with open(System_Configuration.HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [
        {
            "role": "system",
            "content": f"You are {System_Configuration.AI_NAME}, a helpful AI assistant and voice agent made by Janak Amol Chavan. Keep your answers conversational, concise, and complete. You will get the speaker name in the prompt, so you can address them by name. If unknown, address them as 'User'. Your chart interface is runing on http://localhost:8000/"
        }
    ]

def save_history(history):
    try:
        with open(System_Configuration.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False

def append_chat_message(history, role, content, attachment=None):
    """Clean helper to add messages with optional attachments (like charts) to memory."""
    msg = {"role": role, "content": content}
    if attachment:
        msg["attachment"] = attachment
    history.append(msg)
    save_history(history)

def Get_Optimized_Screenshot(max_width=1280):
    """Captures screen instantly using mss (no disk I/O) and resizes for fast Gemini vision processing."""
    temp_dir = Path(System_Configuration.TEMPORARY_FOLDER_PATH)
    temp_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = temp_dir / "screen_capture.png"

    with mss.mss() as sct:
        # Grab the primary monitor monitor[0] or bounding box
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        
        # Convert raw mss pixels to a PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Downscale if wider than max_width to eliminate latency bottlenecks
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        img.save(screenshot_path, "PNG", optimize=True)
        return str(screenshot_path)

# -- CONCENTRATED_MEMORY_FILE --

def load_concentrated_memory():
    if os.path.exists(System_Configuration.CONCENTRATED_MEMORY_FILE):
        try:
            with open(System_Configuration.CONCENTRATED_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    raw_users = data.get("user_data")
                    raw_projects = data.get("project_data")

                    user_map = raw_users if isinstance(raw_users, dict) else {}
                    project_map = raw_projects if isinstance(raw_projects, dict) else {}

                    raw_artifacts = data.get("artifacts")
                    artifacts_map = raw_artifacts if isinstance(raw_artifacts, dict) else {}

                    return {
                        "user_data": user_map,
                        "project_data": project_map,
                        "summaries": list(data.get("summaries") or []),
                        "last_summarized_index": int(data.get("last_summarized_index") or 1),
                        "artifacts": {
                            "last_chart": artifacts_map.get("last_chart"),
                            "charts": list(artifacts_map.get("charts") or [])[-15:],
                            "files": list(artifacts_map.get("files") or [])[-20:],
                        },
                    }
        except Exception as e:
            print(f"Error loading concentrated memory: {e}")
    return {
        "user_data": {},
        "project_data": {},
        "summaries": [],
        "last_summarized_index": 1,  # index 0 is the system prompt
        "artifacts": {}
    }

def save_concentrated_memory(data):
    try:
        with open(System_Configuration.CONCENTRATED_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving concentrated memory: {e}")
        return False

# -- Episodes History --

def _tokenize_query(query: str) -> list[str]:
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "to", "for", "of",
        "in", "on", "at", "with", "and", "or", "about", "what", "when",
        "where", "who", "how", "did", "do", "does", "my", "me", "we", "our",
    }
    tokens = re.findall(r"[a-z0-9_]+", (query or "").lower())
    return [t for t in tokens if len(t) > 1 and t not in stop_words]

def search_episodes(query: str, history: list[dict] | None = None, top_k: int = 3, include_tool_logs: bool = False) -> list[dict]:
    """
    Lightweight keyword + phrase search over AI_MEMORY.json episodes.
    Skips the system prompt (index 0) and optionally skips tool_log entries.
    """
    keywords = _tokenize_query(query)
    if not keywords:
        return []

    source = history if history is not None else load_history()
    scored_matches = []
    q_lower = (query or "").strip().lower()

    for idx, msg in enumerate(source[1:], start=1):
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        if not include_tool_logs and msg.get("entry_type") == "tool_log":
            continue

        content = msg.get("content")
        if not isinstance(content, str) or not content.strip():
            continue

        text_lower = content.lower()
        score = 0

        # Exact phrase bonus
        if len(q_lower) >= 4 and q_lower in text_lower:
            score += 5

        # Keyword overlap score
        for kw in keywords:
            count = text_lower.count(kw)
            if count:
                score += min(count, 3) * 2

        if score > 0:
            # Slight recency tie-breaker
            recency_bonus = (idx / max(len(source), 1)) * 0.5
            scored_matches.append((score + recency_bonus, idx, msg))

    scored_matches.sort(key=lambda item: item[0], reverse=True)

    results = []
    for _, idx, msg in scored_matches[:top_k]:
        snippet = msg["content"].strip().replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        results.append({
            "index": idx,
            "role": msg.get("role"),
            "entry_type": msg.get("entry_type", "chat"),
            "content": snippet,
        })

    return results

def format_episode_context(episodes: list[dict]) -> str:
    if not episodes:
        return ""
    lines = [f"- [{ep['role']} #{ep['index']}]: {ep['content']}" for ep in episodes]
    return "[Recalled Past Episodes]\n" + "\n".join(lines)

# -- Skill History --

def load_skills_memory() -> dict:
    skill_path = System_Configuration.SKILLS_MEMORY_FILE
    if os.path.exists(skill_path):
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("skills"), list):
                    return {"skills": data["skills"]}
        except Exception as e:
            print(f"Error loading skills memory: {e}")
    return {"skills": []}

def save_skills_memory(data: dict) -> bool:
    skill_path = System_Configuration.SKILLS_MEMORY_FILE
    try:
        with open(skill_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving skills memory: {e}")
        return False

def record_skill(
    skill_id: str,
    title: str,
    triggers: list[str],
    steps: list[str],
    fix_notes: str = "",
) -> dict:
    """Adds or updates a reusable workflow/fix playbook in skills_memory.json."""
    clean_id = (skill_id or "").strip().lower().replace(" ", "_")
    if not clean_id:
        raise ValueError("skill_id is required")

    store = load_skills_memory()
    skills = store["skills"]

    clean_triggers = [t.strip().lower() for t in triggers if isinstance(t, str) and t.strip()]
    clean_steps = [s.strip() for s in steps if isinstance(s, str) and s.strip()]

    existing = next((item for item in skills if item.get("id") == clean_id), None)
    if existing:
        existing["title"] = title.strip() or existing.get("title", clean_id)
        if clean_triggers:
            existing["triggers"] = sorted(set(existing.get("triggers", []) + clean_triggers))
        if clean_steps:
            existing["steps"] = clean_steps
        if fix_notes.strip():
            existing["fix_notes"] = fix_notes.strip()
        existing["uses"] = int(existing.get("uses", 0)) + 1
        entry = existing
    else:
        entry = {
            "id": clean_id,
            "title": title.strip() or clean_id,
            "triggers": clean_triggers,
            "steps": clean_steps,
            "fix_notes": fix_notes.strip(),
            "uses": 1,
        }
        skills.append(entry)

    save_skills_memory({"skills": skills})
    return entry

def search_skills(query: str, top_k: int = 1) -> list[dict]:
    """Matches a request against saved triggers, IDs, titles, steps, and fix notes, returning the highest-scored matches first."""
    keywords = set(_tokenize_query(query))
    q_lower = (query or "").strip().lower()
    if not keywords and not q_lower:
        return []

    store = load_skills_memory()
    scored = []

    for skill in store.get("skills", []):
        if not isinstance(skill, dict):
            continue
        score = 0.0
        skill_id = str(skill.get("id", "")).lower()
        title = str(skill.get("title", "")).lower()
        triggers = [str(t).lower() for t in skill.get("triggers", [])]
        blob = " ".join([
            skill_id,
            title,
            " ".join(triggers),
            " ".join(str(s) for s in skill.get("steps", [])),
            str(skill.get("fix_notes", "")),
        ]).lower()

        # Strong boost if exact skill ID or full trigger phrase appears in query
        if skill_id and skill_id in q_lower:
            score += 10
        for trig in triggers:
            if trig and trig in q_lower:
                score += 6 + len(trig.split())  # longer/more specific trigger wins

        for kw in keywords:
            if kw in title or kw in skill_id:
                score += 3
            elif kw in blob:
                score += 1.5

        if score > 0:
            scored.append((score + int(skill.get("uses", 0)) * 0.25, skill))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:top_k]]

def format_skills_context(skills: list[dict]) -> str:
    if not skills:
        return ""
    top_skill = skills[0]
    steps_txt = " -> ".join(top_skill.get("steps", []))
    line = f"- **{top_skill.get('title')}** (`{top_skill.get('id')}`): {steps_txt}"
    if top_skill.get("fix_notes") and str(top_skill.get("fix_notes")).lower() != "none":
        line += f" | Fix note: {top_skill['fix_notes']}"
    return (
        "[Best Matched Skill — Execute These Steps Directly if needed]\n"
        + line
    )


FILE_PATH_PATTERN = re.compile(
    r"(?:[A-Za-z]:\\|/)?(?:[\w.\-]+[/\\])+[\w.\-]+\.(?:png|jpg|jpeg|txt|csv|json|py|js|html|md)",
    re.IGNORECASE,
)
BARE_CHART_PATTERN = re.compile(
    r"\b(chart_[\w.\-]+\.png|[\w.\-]+\.png)\b",
    re.IGNORECASE,
)

def extract_paths(text: str) -> list[str]:
    if not isinstance(text, str) or not text:
        return []

    cleaned: list[str] = []

    for p in FILE_PATH_PATTERN.findall(text):
        norm = os.path.normpath(p.strip().strip("\"'`"))
        if norm and norm not in cleaned:
            cleaned.append(norm)

    temp_dir = getattr(System_Configuration, "TEMPORARY_FOLDER_PATH", "Backend/Core/Temporary")
    for fname in BARE_CHART_PATTERN.findall(text):
        clean_name = fname.strip().strip("\"'`")
        if any(clean_name.lower() == os.path.basename(existing).lower() for existing in cleaned):
            continue
        resolved = os.path.normpath(os.path.join(temp_dir, clean_name))
        if resolved not in cleaned:
            cleaned.append(resolved)

    return cleaned

def record_artifacts_from_text(text: str, source_tool: str | None = None):
    """Records exact file paths and .png chart paths into Concentrated Memory."""
    paths = extract_paths(text)
    if not paths:
        return

    conc = load_concentrated_memory()
    artifacts = conc.setdefault("artifacts", {
        "last_chart": None,
        "charts": [],
        "files": [],
    })

    for path in paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".png" or "chart_" in os.path.basename(path).lower() or source_tool == "generate_chart":
            if path in artifacts["charts"]:
                artifacts["charts"].remove(path)
            artifacts["charts"].append(path)
            artifacts["charts"] = artifacts["charts"][-15:]
            artifacts["last_chart"] = path
        else:
            if path in artifacts["files"]:
                artifacts["files"].remove(path)
            artifacts["files"].append(path)
            artifacts["files"] = artifacts["files"][-20:]

    save_concentrated_memory(conc)

# -- Memory Builder --

def build_active_memory(full_history, max_recent=7, max_users=10, max_projects=10, max_episodes=3, max_skill=1):
    """Assembles System Prompt + Concentrated Memory (capped at 10 users & 10 projects in active prompt)+ Recent Turns without mutating full_history or deleting stored concentrated memory."""
    messages = []
    if full_history and full_history[0].get("role") == "system":
        messages.append(full_history[0])

    conc = load_concentrated_memory()
    sections = []

    # Concentrate Memory
    if conc.get("user_data"):
        user_lines = [
            f"- {name.capitalize()}: {summary}"
            for name, summary in list(conc["user_data"].items())[-max_users:]
            if summary
        ]
        if user_lines:
            sections.append("Personal Summaries:\n" + "\n".join(user_lines))
    if conc.get("project_data"):
        proj_lines = [
            f"- {proj}: {summary}"
            for proj, summary in list(conc["project_data"].items())[-max_projects:]
            if summary
        ]
        if proj_lines:
            sections.append("Project Summaries:\n" + "\n".join(proj_lines))
    if conc.get("summaries"):
        sections.append(
            "Recent Conversation Summaries (up to 5):\n- " + "\n- ".join(conc["summaries"][-5:])
        )

    # Artifacts
    artifacts = conc.get("artifacts") or {}
    art_lines = []
    if artifacts.get("last_chart"):
        art_lines.append(f"- Latest chart PNG: {artifacts['last_chart']}")
    if artifacts.get("charts"):
        art_lines.append("- Recent charts: " + ", ".join(artifacts["charts"][-5:]))
    if artifacts.get("files"):
        art_lines.append("- Recent files: " + ", ".join(artifacts["files"][-8:]))
    if art_lines:
        sections.append("Tracked Files & Charts:\n" + "\n".join(art_lines))

    if sections:
        messages.append({
            "role": "system",
            "content": "[Concentrated Memory]\n" + "\n\n".join(sections),
        })

    # User Command (only run episode/skill search if there is an actual user turn)
    if len(full_history) > 1:
        raw_cmd = str(full_history[-1].get("content") or "")
        user_command = re.sub(r"^\[[^\]]+\]:\s*", "", raw_cmd).strip()

        # Episodes (exclude the current turn at index -1)
        episodes = search_episodes(
            user_command,
            history=full_history[:-1],
            top_k=max_episodes,
            include_tool_logs=False,
        )
        episode_block = format_episode_context(episodes)
        if episode_block:
            messages.append({
                "role": "system",
                "content": episode_block
            })

        # Skill
        matched_skills = search_skills(
            user_command,
            top_k=max_skill
        )
        skills_block = format_skills_context(matched_skills)
        if skills_block:
            messages.append({
                "role": "system",
                "content": skills_block
            })

    # Recent
    recent = [
        m for m in full_history[1:]
        if m.get("role") in ("user", "assistant")
        and m.get("entry_type") != "tool_log"
        and isinstance(m.get("content"), str)
    ][-max_recent:]

    messages.extend(recent)
    return messages

# -- Active History for analisy --

def load_active_history():
    active_history_path = System_Configuration.FILE_SYS_BASE_FILE + "/Active_History_Backlog.json"
    if os.path.exists(active_history_path):
        try:
            with open(active_history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_active_history(history):
    active_history_path = System_Configuration.FILE_SYS_BASE_FILE + "/Active_History_Backlog.json"
    try:
        with open(active_history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False 

