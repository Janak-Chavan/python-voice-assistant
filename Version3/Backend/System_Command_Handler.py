from Commands.Basic_Controller import save_skill_tool, open_application, search_google, open_website, get_system_time

from Commands.File_Controller import create_and_write_file, read_file, run_script

from Commands.Chart_Controller import generate_chart

from Commands.Game_Controller import launch_roblox, perform_game_action, toggle_anti_afk

# 1. Master map of all executable functions
available_tools = {
    "save_skill_tool" : save_skill_tool,
    "open_application": open_application,
    "search_google": search_google,
    "open_website": open_website,
    "get_system_time": get_system_time,
    "create_and_write_file": create_and_write_file,
    "read_file": read_file,
    "run_script": run_script,
    "generate_chart": generate_chart,
    "launch_roblox": launch_roblox,
    "perform_game_action": perform_game_action,
    "toggle_anti_afk": toggle_anti_afk
}

# 2. Categorized schemas (only loaded when selected)
TOOL_CATEGORIES = {
    "basic": [
        {
            "type": "function",
            "function": {
                "name": "save_skill_tool",
                "description": (
                    "Save a reusable multi-step workflow or error fix to procedural memory "
                    "(skills_memory.json) so it can be reused later."
                    "do not add the same tool again in it"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "Short snake_case identifier, e.g. 'csv_to_pie_chart'.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Clear short name for the workflow or fix.",
                        },
                        "triggers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Phrases or tasks that should trigger this skill.",
                        },
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Ordered steps or tool sequence that worked.",
                        },
                        "fix_notes": {
                            "type": "string",
                            "description": "Optional note on an error or edge case that was fixed.",
                        },
                    },
                    "required": ["skill_id", "title", "triggers", "steps"],
                },
            },
        },
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
                "description": "Open a specific website or URL directly in the browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The website domain or URL to open."}
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
        }
    ],
    "files": [
        {
            "type": "function",
            "function": {
                "name": "create_and_write_file",
                "description": "Create or overwrite a local file with fresh content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of file with extension (e.g., test.py)."},
                        "content": {"type": "string", "description": "Content to write into the file."}
                    },
                    "required": ["filename", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a local file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name or path of the file to read."}
                    },
                    "required": ["filename"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_script",
                "description": "Execute Python/JS/C++ scripts, or open/view local HTML/PNG/image files using 'filename'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Exact path or file name to execute or open (e.g., chart.png or script.py)."
                        }
                    },
                    "required": ["filename"]
                }
            }
        }
    ],
    "charts": [
        {
            "type": "function",
            "function": {
                "name": "generate_chart",
                "description": "Generate and display a visual chart (bar, line, or pie).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {"type": "string", "description": "'bar', 'line', or 'pie'"},
                        "title": {"type": "string", "description": "Title of the chart."},
                        "labels_json": {"type": "string", "description": "JSON array of labels as string."},
                        "values_json": {"type": "string", "description": "JSON array of numeric values as string."}
                    },
                    "required": ["chart_type", "title", "labels_json", "values_json"]
                }
            }
        }
    ],
    "gaming": [
        {
            "type": "function",
            "function": {
                "name": "launch_roblox",
                "description": "Launch Roblox or join a specific experience by Place ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "game_id": {"type": "string", "description": "Optional numeric Roblox Place ID."}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "perform_game_action",
                "description": "Control character movement in Roblox ('walk forward', 'walk back', 'jump', 'spin').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action to perform."},
                        "duration": {"type": "number", "description": "Seconds to hold action."}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "toggle_anti_afk",
                "description": "Start or stop background Anti-AFK mode in Roblox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "description": "'start' or 'stop'"}
                    },
                    "required": ["state"]
                }
            }
        }
    ]
}

# 3. Initial lightweight router schema shown on Turn 1

ROUTER_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "select_tool_category",
            "description": (
                "Meta-router that unlocks or switches active tool sets on demand. "
                "Jarvis HAS local system tools—never claim you lack file access or cannot read local paths. "
                "Use 'files' (read_file, create_and_write_file, run_script) to inspect/edit/run local files; "
                "'charts' (generate_chart) to render UI bar/line/pie charts (never hand-code plotting scripts); "
                "'basic' (save_skill_tool, open_application, search_google, open_website, get_system_time) to "
                "persist skills or run everyday actions; and 'gaming' (launch_roblox, perform_game_action, "
                "toggle_anti_afk) for Roblox. Call this repeatedly across turns to chain multi-step workflows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["basic", "files", "charts", "gaming"],
                        "description": "Target capability group to activate now."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief 3-8 word note on what tool you will run next in this category."
                    }
                },
                "required": ["category"]
            }
        }
    }
]
