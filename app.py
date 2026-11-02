import os
import json
import ast
from ddgs import DDGS
import operator
import sqlite3
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==========================================================
# RAMSES V1 — GENERAL PURPOSE AI AGENT
# ==========================================================

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
WORKSPACE = APP_DIR / "workspace"
WORKSPACE.mkdir(exist_ok=True)

DB_PATH = APP_DIR / "ramses_memory.db"

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_STEPS = 5

SYSTEM_PROMPT = """
You are RAMSES, a general-purpose autonomous AI agent.

Your mission:
Help the user think, research, plan, create, organize and solve tasks.

You can use tools. You must decide when a tool is useful.
You may execute several safe tool actions to complete a task.

IMPORTANT RULES:
- Be honest. Never claim an action succeeded unless its tool confirms it.
- Never invent information, sources, credentials or results.
- Use the memory tools when the user asks you to remember something.
- Use tools when they are more useful than merely describing what to do.
- You can create and read files only inside your workspace.
- Never access files outside the workspace.
- Never reveal API keys, environment variables or secrets.
- Never delete files.
- Never make purchases, send applications, send messages, accept contracts,
  publish content or perform irreversible external actions.
- If an action needs external access or could have significant consequences,
  explain what is needed and ask the user.
- Do not pretend you have internet access. You currently have only the tools
  explicitly listed below.

AVAILABLE TOOLS:
1. calculator: Evaluate a mathematical expression.
   Args: {"expression": "2 * (5 + 3)"}

2. remember: Save a useful fact in persistent memory.
   Args: {"key": "user_preference", "value": "Prefers Spanish"}

3. recall: Search persistent memory.
   Args: {"query": "language preference"}

4. list_files: List files in your workspace.
   Args: {}

5. read_file: Read a text file in your workspace.
   Args: {"filename": "notes.txt"}

6. write_file: Create or overwrite a text file in your workspace.
   Args: {"filename": "notes.txt", "content": "Text"}

7. current_time: Get the current date and time.
   Args: {}

RESPONSE FORMAT:
Always return valid JSON, with this structure:

{
  "message": "Your response to the user",
  "actions": [
    {
      "tool": "tool_name",
      "args": {}
    }
  ],
  "done": false
}

If you have finished, set done to true.
If no tool is needed, return an empty actions list and done=true.

You can use the results of previous tools to decide what to do next.
Do not repeat an action that has already failed.
"""

# ==========================================================
# DATABASE — PERSISTENT MEMORY
# ==========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def remember(key, value):
    conn = db()
    conn.execute(
        "INSERT INTO memories (key, value, created_at) VALUES (?, ?, ?)",
        (str(key), str(value), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return "Memory saved successfully."


def recall(query):
    conn = db()
    rows = conn.execute(
        """
        SELECT key, value, created_at
        FROM memories
        WHERE key LIKE ? OR value LIKE ?
        ORDER BY id DESC LIMIT 20
        """,
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()

    if not rows:
        return "No matching memories found."

    return json.dumps(rows, ensure_ascii=False)


# ==========================================================
# SAFE CALCULATOR
# ==========================================================

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}


def calculate(expression):
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large.")

            result = OPERATORS[type(node.op)](left, right)

            if abs(result) > 1e100:
                raise ValueError("Result too large.")

            return result

        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](evaluate(node.operand))

        raise ValueError("Expression not allowed.")

    tree = ast.parse(expression, mode="eval")
    return str(evaluate(tree.body))


# ==========================================================
# WORKSPACE FILE TOOLS
# ==========================================================

def safe_path(filename):
    path = (WORKSPACE / filename).resolve()

    if path != WORKSPACE.resolve() and WORKSPACE.resolve() not in path.parents:
        raise ValueError("Access outside workspace is forbidden.")

    return path


def list_files():
    files = [
        str(p.relative_to(WORKSPACE))
        for p in WORKSPACE.rglob("*")
        if p.is_file()
    ]
    return json.dumps(files, ensure_ascii=False)


def read_file(filename):
    path = safe_path(filename)

    if not path.exists() or not path.is_file():
        return "File not found."

    if path.stat().st_size > 200_000:
        return "File is too large to read."

    return path.read_text(encoding="utf-8")


def write_file(filename, content):
    path = safe_path(filename)

    if len(content) > 100_000:
        raise ValueError("File content is too large.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return f"File created or updated: {filename}"


# ==========================================================
# TOOL EXECUTION
# ==========================================================
import os
import json
import ast
import operator
import sqlite3
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==========================================================
# RAMSES V1 — GENERAL PURPOSE AI AGENT
# ==========================================================

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
WORKSPACE = APP_DIR / "workspace"
WORKSPACE.mkdir(exist_ok=True)

DB_PATH = APP_DIR / "ramses_memory.db"

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_STEPS = 5

SYSTEM_PROMPT = """
You are RAMSES, a general-purpose autonomous AI agent.

Your mission:
Help the user think, research, plan, create, organize and solve tasks.

You can use tools. You must decide when a tool is useful.
You may execute several safe tool actions to complete a task.

IMPORTANT RULES:
- Be honest. Never claim an action succeeded unless its tool confirms it.
- Never invent information, sources, credentials or results.
- Use the memory tools when the user asks you to remember something.
- Use tools when they are more useful than merely describing what to do.
- You can create and read files only inside your workspace.
- Never access files outside the workspace.
- Never reveal API keys, environment variables or secrets.
- Never delete files.
- Never make purchases, send applications, send messages, accept contracts,
  publish content or perform irreversible external actions.
- If an action needs external access or could have significant consequences,
  explain what is needed and ask the user.
- Do not pretend you have internet access. You currently have only the tools
  explicitly listed below.

AVAILABLE TOOLS:
1. calculator: Evaluate a mathematical expression.
   Args: {"expression": "2 * (5 + 3)"}

2. remember: Save a useful fact in persistent memory.
   Args: {"key": "user_preference", "value": "Prefers Spanish"}

3. recall: Search persistent memory.
   Args: {"query": "language preference"}

4. list_files: List files in your workspace.
   Args: {}

5. read_file: Read a text file in your workspace.
   Args: {"filename": "notes.txt"}

6. write_file: Create or overwrite a text file in your workspace.
   Args: {"filename": "notes.txt", "content": "Text"}

7. current_time: Get the current date and time.
   Args: {}

RESPONSE FORMAT:
Always return valid JSON, with this structure:

{
  "message": "Your response to the user",
  "actions": [
    {
      "tool": "tool_name",
      "args": {}
    }
  ],
  "done": false
}

If you have finished, set done to true.
If no tool is needed, return an empty actions list and done=true.

You can use the results of previous tools to decide what to do next.
Do not repeat an action that has already failed.
"""

# ==========================================================
# DATABASE — PERSISTENT MEMORY
# ==========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def remember(key, value):
    conn = db()
    conn.execute(
        "INSERT INTO memories (key, value, created_at) VALUES (?, ?, ?)",
        (str(key), str(value), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return "Memory saved successfully."


def recall(query):
    conn = db()
    rows = conn.execute(
        """
        SELECT key, value, created_at
        FROM memories
        WHERE key LIKE ? OR value LIKE ?
        ORDER BY id DESC LIMIT 20
        """,
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()

    if not rows:
        return "No matching memories found."

    return json.dumps(rows, ensure_ascii=False)


# ==========================================================
# SAFE CALCULATOR
# ==========================================================

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}


def calculate(expression):
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large.")

            result = OPERATORS[type(node.op)](left, right)

            if abs(result) > 1e100:
                raise ValueError("Result too large.")

            return result

        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](evaluate(node.operand))

        raise ValueError("Expression not allowed.")

    tree = ast.parse(expression, mode="eval")
    return str(evaluate(tree.body))


# ==========================================================
# WORKSPACE FILE TOOLS
# ==========================================================

def safe_path(filename):
    path = (WORKSPACE / filename).resolve()

    if path != WORKSPACE.resolve() and WORKSPACE.resolve() not in path.parents:
        raise ValueError("Access outside workspace is forbidden.")

    return path


def list_files():
    files = [
        str(p.relative_to(WORKSPACE))
        for p in WORKSPACE.rglob("*")
        if p.is_file()
    ]
    return json.dumps(files, ensure_ascii=False)


def read_file(filename):
    path = safe_path(filename)

    if not path.exists() or not path.is_file():
        return "File not found."

    if path.stat().st_size > 200_000:
        return "File is too large to read."

    return path.read_text(encoding="utf-8")


def write_file(filename, content):
    path = safe_path(filename)

    if len(content) > 100_000:
        raise ValueError("File content is too large.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return f"File created or updated: {filename}"


# ==========================================================
# TOOL EXECUTION
# ==========================================================

def execute_tool(name, args):
    try:
        if name == "calculator":
            return calculate(args["expression"])

        if name == "remember":
            return remember(args["key"], args["value"])

        if name == "recall":
            return recall(args["query"])

        if name == "list_files":
            return list_files()

        if name == "read_file":
            return read_file(args["filename"])

        if name == "write_file":
            return write_file(args["filename"], args["content"])

        if name == "current_time":
            return datetime.now().astimezone().isoformat()

        return f"Unknown tool: {name}"

    except Exception as error:
        return f"Tool error: {type(error).__name__}: {error}"


# ==========================================================
# GEMINI CONNECTION
# ==========================================================

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(api_key=api_key)


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)


# ==========================================================
# AUTONOMOUS AGENT LOOP
# ==========================================================

def run_ramses(user_message, history):
    client = get_client()

    if client is None:
        return "Falta configurar GEMINI_API_KEY. Revisá el archivo .env."

    conversation = list(history)
    conversation.append({
        "role": "user",
        "content": user_message
    })

    tool_log = []

    for step in range(MAX_STEPS):
        prompt = SYSTEM_PROMPT + "\n\nCONVERSATION:\n"
        prompt += json.dumps(conversation, ensure_ascii=False)

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )

            decision = parse_json(response.text)

        except Exception as error:
            return (
                "Tuve un problema al comunicarme con Gemini: "
                f"{type(error).__name__}: {error}"
            )

        message = str(decision.get("message", ""))
        actions = decision.get("actions", [])
        done = decision.get("done", True)

        if not actions:
            return message or "Tarea finalizada."

        results = []

        for action in actions:
            name = action.get("tool")
            args = action.get("args", {})

            result = execute_tool(name, args)

            results.append({
                "tool": name,
                "result": result
            })

            tool_log.append({
                "step": step + 1,
                "tool": name,
                "result": result
            })

        conversation.append({
            "role": "assistant",
            "content": json.dumps(decision, ensure_ascii=False)
        })

        conversation.append({
            "role": "user",
            "content": (
                "TOOL RESULTS:\n"
                + json.dumps(results, ensure_ascii=False)
                + "\nContinue the task. Return JSON."
            )
        })

        if done:
            return message or "Tarea finalizada."

    # Una última respuesta sin ejecutar más herramientas.
    conversation.append({
        "role": "user",
        "content": (
            "You have reached the tool execution limit. "
            "Summarize what you accomplished and what remains."
        )
    })

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=SYSTEM_PROMPT + "\n\n" +
            json.dumps(conversation, ensure_ascii=False),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        return str(parse_json(response.text).get("message", "Tarea detenida."))

    except Exception:
        return "Alcancé el límite de pasos. Revisá los resultados de las herramientas."


# ==========================================================
# STREAMLIT INTERFACE
# ==========================================================

st.set_page_config(
    page_title="Ramsés AI",
    page_icon="𓂀",
    layout="centered"
)

st.title("𓂀 Ramsés")
st.caption("Agente de inteligencia artificial · Versión 1.0")

with st.sidebar:
    st.header("Panel de Ramsés")
    st.write("Modelo:", MODEL)
    st.write("Memoria: SQLite persistente")
    st.write("Autonomía: ejecución de herramientas locales")

    if st.button("Ver archivos del espacio de trabajo"):
        st.write(list_files())

    if st.button("Ver recuerdos guardados"):
        st.write(recall(""))

    st.divider()
    st.caption("Ramsés v1 · Proyecto en desarrollo")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("¿Qué necesitás que haga Ramsés?")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    previous_history = st.session_state.messages[:-1]

    with st.chat_message("assistant"):
        with st.spinner("Ramsés está pensando y trabajando..."):
            answer = run_ramses(user_input, previous_history)
            st.markdown(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
def execute_tool(name, args):
    try:
        if name == "calculator":
            return calculate(args["expression"])

        if name == "remember":
            return remember(args["key"], args["value"])

        if name == "recall":
            return recall(args["query"])import os
import json
import ast
import operator
import sqlite3
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==========================================================
# RAMSES V1 — GENERAL PURPOSE AI AGENT
# ==========================================================

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
WORKSPACE = APP_DIR / "workspace"
WORKSPACE.mkdir(exist_ok=True)

DB_PATH = APP_DIR / "ramses_memory.db"

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_STEPS = 5

SYSTEM_PROMPT = """
You are RAMSES, a general-purpose autonomous AI agent.

Your mission:
Help the user think, research, plan, create, organize and solve tasks.

You can use tools. You must decide when a tool is useful.
You may execute several safe tool actions to complete a task.

IMPORTANT RULES:
- Be honest. Never claim an action succeeded unless its tool confirms it.
- Never invent information, sources, credentials or results.
- Use the memory tools when the user asks you to remember something.
- Use tools when they are more useful than merely describing what to do.
- You can create and read files only inside your workspace.
- Never access files outside the workspace.
- Never reveal API keys, environment variables or secrets.
- Never delete files.
- Never make purchases, send applications, send messages, accept contracts,
  publish content or perform irreversible external actions.
- If an action needs external access or could have significant consequences,
  explain what is needed and ask the user.
- Do not pretend you have internet access. You currently have only the tools
  explicitly listed below.

AVAILABLE TOOLS:
1. calculator: Evaluate a mathematical expression.
   Args: {"expression": "2 * (5 + 3)"}

2. remember: Save a useful fact in persistent memory.
   Args: {"key": "user_preference", "value": "Prefers Spanish"}

3. recall: Search persistent memory.
   Args: {"query": "language preference"}

4. list_files: List files in your workspace.
   Args: {}

5. read_file: Read a text file in your workspace.
   Args: {"filename": "notes.txt"}

6. write_file: Create or overwrite a text file in your workspace.
   Args: {"filename": "notes.txt", "content": "Text"}

7. current_time: Get the current date and time.
   Args: {}

RESPONSE FORMAT:
Always return valid JSON, with this structure:

{
  "message": "Your response to the user",
  "actions": [
    {
      "tool": "tool_name",
      "args": {}
    }
  ],
  "done": false
}

If you have finished, set done to true.
If no tool is needed, return an empty actions list and done=true.

You can use the results of previous tools to decide what to do next.
Do not repeat an action that has already failed.
"""

# ==========================================================
# DATABASE — PERSISTENT MEMORY
# ==========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def remember(key, value):
    conn = db()
    conn.execute(
        "INSERT INTO memories (key, value, created_at) VALUES (?, ?, ?)",
        (str(key), str(value), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return "Memory saved successfully."


def recall(query):
    conn = db()
    rows = conn.execute(
        """
        SELECT key, value, created_at
        FROM memories
        WHERE key LIKE ? OR value LIKE ?
        ORDER BY id DESC LIMIT 20
        """,
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()

    if not rows:
        return "No matching memories found."

    return json.dumps(rows, ensure_ascii=False)


# ==========================================================
# SAFE CALCULATOR
# ==========================================================

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}


def calculate(expression):
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large.")

            result = OPERATORS[type(node.op)](left, right)

            if abs(result) > 1e100:
                raise ValueError("Result too large.")

            return result

        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](evaluate(node.operand))

        raise ValueError("Expression not allowed.")

    tree = ast.parse(expression, mode="eval")
    return str(evaluate(tree.body))


# ==========================================================
# WORKSPACE FILE TOOLS
# ==========================================================

def safe_path(filename):
    path = (WORKSPACE / filename).resolve()

    if path != WORKSPACE.resolve() and WORKSPACE.resolve() not in path.parents:
        raise ValueError("Access outside workspace is forbidden.")

    return path


def list_files():
    files = [
        str(p.relative_to(WORKSPACE))
        for p in WORKSPACE.rglob("*")
        if p.is_file()
    ]
    return json.dumps(files, ensure_ascii=False)


def read_file(filename):
    path = safe_path(filename)

    if not path.exists() or not path.is_file():
        return "File not found."

    if path.stat().st_size > 200_000:
        return "File is too large to read."

    return path.read_text(encoding="utf-8")


def write_file(filename, content):
    path = safe_path(filename)

    if len(content) > 100_000:
        raise ValueError("File content is too large.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return f"File created or updated: {filename}"


# ==========================================================
# TOOL EXECUTION
# ==========================================================

def execute_tool(name, args):
    try:
        if name == "calculator":
            return calculate(args["expression"])

        if name == "remember":
            return remember(args["key"], args["value"])

        if name == "recall":
            return recall(args["query"])

        if name == "list_files":
            return list_files()

        if name == "read_file":
            return read_file(args["filename"])

        if name == "write_file":
            return write_file(args["filename"], args["content"])

        if name == "current_time":
            return datetime.now().astimezone().isoformat()

        return f"Unknown tool: {name}"

    except Exception as error:
        return f"Tool error: {type(error).__name__}: {error}"


# ==========================================================
# GEMINI CONNECTION
# ==========================================================

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(api_key=api_key)


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)


# ==========================================================
# AUTONOMOUS AGENT LOOP
# ==========================================================

def run_ramses(user_message, history):
    client = get_client()

    if client is None:
        return "Falta configurar GEMINI_API_KEY. Revisá el archivo .env."

    conversation = list(history)
    conversation.append({
        "role": "user",
        "content": user_message
    })

    tool_log = []

    for step in range(MAX_STEPS):
        prompt = SYSTEM_PROMPT + "\n\nCONVERSATION:\n"
        prompt += json.dumps(conversation, ensure_ascii=False)

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )

            decision = parse_json(response.text)

        except Exception as error:
            return (
                "Tuve un problema al comunicarme con Gemini: "
                f"{type(error).__name__}: {error}"
            )

        message = str(decision.get("message", ""))
        actions = decision.get("actions", [])
        done = decision.get("done", True)

        if not actions:
            return message or "Tarea finalizada."

        results = []

        for action in actions:
            name = action.get("tool")
            args = action.get("args", {})

            result = execute_tool(name, args)

            results.append({
                "tool": name,
                "result": result
            })

            tool_log.append({
                "step": step + 1,
                "tool": name,
                "result": result
            })

        conversation.append({
            "role": "assistant",
            "content": json.dumps(decision, ensure_ascii=False)
        })

        conversation.append({
            "role": "user",
            "content": (
                "TOOL RESULTS:\n"
                + json.dumps(results, ensure_ascii=False)
                + "\nContinue the task. Return JSON."
            )
        })

        if done:
            return message or "Tarea finalizada."

    # Una última respuesta sin ejecutar más herramientas.
    conversation.append({
        "role": "user",
        "content": (
            "You have reached the tool execution limit. "
            "Summarize what you accomplished and what remains."
        )
    })

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=SYSTEM_PROMPT + "\n\n" +
            json.dumps(conversation, ensure_ascii=False),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        return str(parse_json(response.text).get("message", "Tarea detenida."))

    except Exception:
        return "Alcancé el límite de pasos. Revisá los resultados de las herramientas."


# ==========================================================
# STREAMLIT INTERFACE
# ==========================================================

st.set_page_config(
    page_title="Ramsés AI",
    page_icon="𓂀",
    layout="centered"
)

st.title("𓂀 Ramsés")
st.caption("Agente de inteligencia artificial · Versión 1.0")

with st.sidebar:
    st.header("Panel de Ramsés")
    st.write("Modelo:", MODEL)
    st.write("Memoria: SQLite persistente")
    st.write("Autonomía: ejecución de herramientas locales")

    if st.button("Ver archivos del espacio de trabajo"):
        st.write(list_files())

    if st.button("Ver recuerdos guardados"):
        st.write(recall(""))

    st.divider()
    st.caption("Ramsés v1 · Proyecto en desarrollo")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("¿Qué necesitás que haga Ramsés?")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    previous_history = st.session_state.messages[:-1]

    with st.chat_message("assistant"):
        with st.spinner("Ramsés está pensando y trabajando..."):
            answer = run_ramses(user_input, previous_history)
            st.markdown(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

        if name == "list_files":
            return list_files()

        if name == "read_file":
            return read_file(args["filename"])

        if name == "write_file":
            return write_file(args["filename"], args["content"])

        if name == "current_time":
            return datetime.now().astimezone().isoformat()

        return f"Unknown tool: {name}"

    except Exception as error:
        return f"Tool error: {type(error).__name__}: {error}"


# ==========================================================
# GEMINI CONNECTION
# ==========================================================

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(api_key=api_key)


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)


# ==========================================================
# AUTONOMOUS AGENT LOOP
# ==========================================================

def run_ramses(user_message, history):
    client = get_client()

    if client is None:
        return "Falta configurar GEMINI_API_KEY. Revisá el archivo .env."

    conversation = list(history)
    conversation.append({
        "role": "user",
        "content": user_message
    })

    tool_log = []

    for step in range(MAX_STEPS):
        prompt = SYSTEM_PROMPT + "\n\nCONVERSATION:\n"
        prompt += json.dumps(conversation, ensure_ascii=False)

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )

            decision = parse_json(response.text)

        except Exception as error:
            return (
                "Tuve un problema al comunicarme con Gemini: "
                f"{type(error).__name__}: {error}"
            )

        message = str(decision.get("message", ""))
        actions = decision.get("actions", [])
        done = decision.get("done", True)

        if not actions:
            return message or "Tarea finalizada."

        results = []

        for action in actions:
            name = action.get("tool")
            args = action.get("args", {})

            result = execute_tool(name, args)

            results.append({
                "tool": name,
                "result": result
            })

            tool_log.append({
                "step": step + 1,
                "tool": name,
                "result": result
            })

        conversation.append({
            "role": "assistant",
            "content": json.dumps(decision, ensure_ascii=False)
        })

        conversation.append({
            "role": "user",
            "content": (
                "TOOL RESULTS:\n"
                + json.dumps(results, ensure_ascii=False)
                + "\nContinue the task. Return JSON."
            )
        })

        if done:
            return message or "Tarea finalizada."

    # Una última respuesta sin ejecutar más herramientas.
    conversation.append({
        "role": "user",
        "content": (
            "You have reached the tool execution limit. "
            "Summarize what you accomplished and what remains."
        )
    })

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=SYSTEM_PROMPT + "\n\n" +
            json.dumps(conversation, ensure_ascii=False),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        return str(parse_json(response.text).get("message", "Tarea detenida."))

    except Exception:
        return "Alcancé el límite de pasos. Revisá los resultados de las herramientas."


# ==========================================================
# STREAMLIT INTERFACE
# ==========================================================

st.set_page_config(
    page_title="Ramsés AI",
    page_icon="𓂀",
    layout="centered"
)

st.title("𓂀 Ramsés")
st.caption("Agente de inteligencia artificial · Versión 1.0")

with st.sidebar:
    st.header("Panel de Ramsés")
    st.write("Modelo:", MODEL)
    st.write("Memoria: SQLite persistente")
    st.write("Autonomía: ejecución de herramientas locales")

    if st.button("Ver archivos del espacio de trabajo"):
        st.write(list_files())

    if st.button("Ver recuerdos guardados"):
        st.write(recall(""))

    st.divider()
    st.caption("Ramsés v1 · Proyecto en desarrollo")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("¿Qué necesitás que haga Ramsés?")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    previous_history = st.session_state.messages[:-1]

    with st.chat_message("assistant"):
        with st.spinner("Ramsés está pensando y trabajando..."):
            answer = run_ramses(user_input, previous_history)
            st.markdown(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })