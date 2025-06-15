import sys
import re
import json
import sqlite3
import threading
import tkinter as tk
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage
import smtplib
import ctypes
import time
import requests

BASE_DIR = Path(r"C:\AIAgent")
MEMORY_DIR = BASE_DIR / "memory"
SCRIPT_DIR = BASE_DIR / "scripts"
LOG_DIR = BASE_DIR / "logs"

# --- Hugging Face API interaction ---
def hf_infer(model_info, prompt):
    """
    model_info: dict with keys 'model', 'api_url', 'api_token'
    prompt: str
    Returns: str (model response)
    """
    headers = {
        "Authorization": f"Bearer {model_info['api_token']}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": model_info.get("parameters", {}),
        "options": model_info.get("options", {})
    }
    response = requests.post(model_info["api_url"], headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    # Hugging Face text-generation endpoints return a list of dicts with 'generated_text'
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"]
    # Some endpoints return just 'data' or 'text'
    if isinstance(data, dict):
        return data.get("generated_text") or data.get("text") or str(data)
    return str(data)

def openrouter_infer(model_info, prompt):
    """
    model_info: dict with keys 'model', 'api_url', 'api_token'
    prompt: str
    Returns: str (model response)
    """
    url = f"{model_info['api_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_info['api_token']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_info["model"],
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    # OpenRouter returns OpenAI-compatible response
    return data["choices"][0]["message"]["content"]

def check_llm_connections(api_config, ui=None):
    results = {}
    for llm_name, model_info in api_config.items():
        provider = model_info.get("provider", "huggingface").lower()
        try:
            if provider == "openrouter":
                response = openrouter_infer(model_info, "ping")
            else:
                response = hf_infer(model_info, "ping")
            results[llm_name] = None
            if ui:
                ui.log(f"LLM '{llm_name}' ({provider}) connection OK.")
        except Exception as e:
            msg = f"LLM '{llm_name}' ({provider}) connection failed: {str(e)}"
            results[llm_name] = msg
            if ui:
                ui.log(msg)
    return results

class AgentUI:
    def __init__(self, config: dict, api_config: dict):
        self.config = config
        self.api_config = api_config
        self.paused = True  # Start in paused state
        self.timeout_event = threading.Event()
        self.timeout_event.clear()
        self.awaiting_command = False

        # Detect screen size (Windows)
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)

        # Set the GUI as a horizontal strip near the top
        gui_height = 400
        gui_y = 40
        self.root = tk.Tk()
        self.root.geometry(f"{self.screen_width}x{gui_height}+0+{gui_y}")
        self.root.title("Aiden Agent")

        # Status and pause/resume
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, anchor="nw")
        self.status_label = tk.Label(top_frame, text="Aiden: Paused")
        self.status_label.pack(side=tk.LEFT, anchor="nw")
        self.pause_button = tk.Button(top_frame, text="Resume", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, anchor="nw")

        # User input for right LLM (enabled only when paused)
        user_input_frame = tk.Frame(self.root)
        user_input_frame.pack(fill=tk.X, anchor="nw")
        tk.Label(user_input_frame, text="User Input to Right LLM:").pack(side=tk.LEFT)
        self.user_input_entry = tk.Entry(user_input_frame, width=100)
        self.user_input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.user_input_entry.config(state=tk.NORMAL)
        self.send_user_input_btn = tk.Button(user_input_frame, text="Send", command=self.send_user_input)
        self.send_user_input_btn.pack(side=tk.LEFT)

        # Requests and responses
        io_frame = tk.Frame(self.root)
        io_frame.pack(fill=tk.BOTH, expand=True)

        # Left Request/Response
        left_frame = tk.Frame(io_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(left_frame, text="Left Request").pack()
        left_request_frame = tk.Frame(left_frame)
        left_request_frame.pack(fill=tk.X)
        left_request_scroll = tk.Scrollbar(left_request_frame)
        left_request_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_request_text = tk.Text(left_request_frame, height=4, width=60, bg="#e0f7fa", yscrollcommand=left_request_scroll.set)
        self.left_request_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        left_request_scroll.config(command=self.left_request_text.yview)

        tk.Label(left_frame, text="Left Response").pack()
        left_response_frame = tk.Frame(left_frame)
        left_response_frame.pack(fill=tk.X)
        left_response_scroll = tk.Scrollbar(left_response_frame)
        left_response_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_response_text = tk.Text(left_response_frame, height=4, width=60, bg="#f1f8e9", yscrollcommand=left_response_scroll.set)
        self.left_response_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        left_response_scroll.config(command=self.left_response_text.yview)

        # Right Request/Response
        right_frame = tk.Frame(io_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(right_frame, text="Right Request").pack()
        right_request_frame = tk.Frame(right_frame)
        right_request_frame.pack(fill=tk.X)
        right_request_scroll = tk.Scrollbar(right_request_frame)
        right_request_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_request_text = tk.Text(right_request_frame, height=4, width=60, bg="#fffde7", yscrollcommand=right_request_scroll.set)
        self.right_request_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        right_request_scroll.config(command=self.right_request_text.yview)

        tk.Label(right_frame, text="Right Response").pack()
        right_response_frame = tk.Frame(right_frame)
        right_response_frame.pack(fill=tk.X)
        right_response_scroll = tk.Scrollbar(right_response_frame)
        right_response_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_response_text = tk.Text(right_response_frame, height=4, width=60, bg="#fce4ec", yscrollcommand=right_response_scroll.set)
        self.right_response_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        right_response_scroll.config(command=self.right_response_text.yview)

        # Log and last command
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(bottom_frame, text="Active Log").pack(anchor="w")
        log_frame = tk.Frame(bottom_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text = tk.Text(log_frame, height=6, width=120, yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

        tk.Label(bottom_frame, text="Last Command from LLM").pack(anchor="w")
        command_frame = tk.Frame(bottom_frame)
        command_frame.pack(fill=tk.X)
        command_scroll = tk.Scrollbar(command_frame)
        command_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.command_text = tk.Text(command_frame, height=2, width=120, bg="#f0f0f0", yscrollcommand=command_scroll.set)
        self.command_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        command_scroll.config(command=self.command_text.yview)

        # DB and email
        self.conn = sqlite3.connect(MEMORY_DIR / "memory.db")
        self.init_db()
        self.email_user = ""
        self.email_password = ""
        try:
            with open(MEMORY_DIR / "EmailCred.txt", "r") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    self.email_user = lines[0].strip()
                    self.email_password = lines[1].strip()
                    self.smtp_host = lines[2].strip()
                    self.smtp_port = int(lines[3].strip())
                else:
                    self.log("Error: EmailCred.txt must have at least 2 lines (user, password)")
        except FileNotFoundError:
            self.log(r"Error: EmailCred.txt not found in C:\AIAgent\memory")
        self.last_command_time = None  # Do not start timer yet
        self.initial_prompt_sent = False  # Track if initial prompt has been sent

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        with open(LOG_DIR / "agent.log", "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def toggle_pause(self):
        self.paused = not self.paused
        self.status_label.config(text=f"Aiden: {'Paused' if self.paused else 'Running'}")
        self.pause_button.config(text="Resume" if self.paused else "Pause")
        if not self.paused:
            self.timeout_event.set()
            self.last_command_time = datetime.now()
            if not self.initial_prompt_sent:
                threading.Thread(target=self.send_initial_prompt, daemon=True).start()
            self.user_input_entry.config(state=tk.DISABLED)
            self.send_user_input_btn.config(state=tk.DISABLED)
        else:
            self.timeout_event.clear()
            self.user_input_entry.config(state=tk.NORMAL)
            self.send_user_input_btn.config(state=tk.NORMAL)

    def send_initial_prompt(self):
        global right_response, command, args
        self.awaiting_command = True
        right_response = interact_with_llm(self, "right", self.init_prompt)
        self.right_request_text.delete(1.0, tk.END)
        self.right_request_text.insert(tk.END, self.init_prompt)
        self.right_response_text.delete(1.0, tk.END)
        self.right_response_text.insert(tk.END, right_response)
        self.initial_prompt_sent = True  # Set here, after sending

    def send_user_input(self):
        # Only allowed in pause mode
        if not self.paused:
            return
        user_input = self.user_input_entry.get()
        if not user_input.strip():
            return
        self.right_request_text.delete(1.0, tk.END)
        self.right_request_text.insert(tk.END, user_input)
        response = interact_with_llm(self, "right", user_input)
        self.right_response_text.delete(1.0, tk.END)
        self.right_response_text.insert(tk.END, response)
        global right_response
        right_response = response

    def init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                category TEXT,
                content TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def show_command(self, command, args):
        self.command_text.delete(1.0, tk.END)
        self.command_text.insert(tk.END, f"Last Command:\n{command or ''}\nArgs:\n{args or ''}")

def read_flat_file(filename: Path) -> str:
    try:
        return filename.read_text()
    except FileNotFoundError:
        return f"Error: File {filename} not found"

def write_flat_file(filename: Path, content: str, append: bool):
    mode = "a" if append else "w"
    with open(filename, mode) as f:
        f.write(content + "\n")

def run_command(ui: AgentUI, command: str, args: str) -> str:
    if command == "filewrite":
        type_, filename, content = args.split("|")
        if type_ == "script":
            path = SCRIPT_DIR / filename
        elif type_ == "memory":
            path = MEMORY_DIR / filename
        else:
            return "Error: Invalid file type"
        write_flat_file(path, content, False)
        return f"Wrote to {path}"
    elif command == "creatememoryentry":
        category, content = args.split("|", 1)
        timestamp = datetime.now().isoformat()
        id_ = f"{timestamp}-{hash(content) % 1000}"
        cursor = ui.conn.cursor()
        cursor.execute("INSERT INTO memories (id, category, content, timestamp) VALUES (?, ?, ?, ?)",
                       (id_, category, content, timestamp))
        ui.conn.commit()
        return f"Memory entry created: {id_}"
    elif command == "writeflatfile":
        filename, content, append = args.split("|")
        append = append.lower() == "true"
        path = MEMORY_DIR / filename
        write_flat_file(path, content, append)
        return f"Wrote to {path}"
    elif command == "getfilecontent":
        filename = args
        path = MEMORY_DIR / filename
        return read_flat_file(path)
    elif command == "listmemoryfiles":
        files = [f.name for f in MEMORY_DIR.iterdir() if f.is_file()]
        return "\n".join(files)
    elif command == "searchmemory":
        filename, search = args.split("|")
        if filename == "ALL":
            cursor = ui.conn.cursor()
            cursor.execute("SELECT id, content FROM memories WHERE content LIKE ?", (f"%{search}%",))
            results = [f"{row[0]}: {row[1]}" for row in cursor.fetchall()]
            return "\n".join(results) or "No matches found"
        else:
            path = MEMORY_DIR / filename
            content = read_flat_file(path)
            if search in content:
                return content
            return "No matches found"
    elif command == "sendemail":
        from_addr, to_addr, subject, body = args.split("|")
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        try:
            with smtplib.SMTP(ui.smtp_host, ui.smtp_port) as server:
                server.starttls()
                server.login(ui.email_user, ui.email_password)
                server.send_message(msg)
            return "Email sent successfully"
        except Exception as e:
            return f"Email error: {str(e)}"
    elif command == "runcommand":
        path, cmd, cmd_args = args.split("|")
        if path == ".":
            path = BASE_DIR
        elif path == "scripts":
            path = SCRIPT_DIR
        elif path == "tools":
            path = BASE_DIR / "tools"
        else:
            return "Error: Invalid path"
        import subprocess
        try:
            result = subprocess.run([path / cmd] + cmd_args.split(), capture_output=True, text=True)
            return result.stdout or result.stderr
        except Exception as e:
            return f"Command error: {str(e)}"
    elif command == "browseweb":
        url = args
        return f"Browse web not supported in API mode. (URL: {url})"
    return "Unknown command"

def process_response(ui: AgentUI, response: str) -> tuple:
    if not isinstance(response, str) or not response:
        ui.log("process_response: Received empty or non-string response")
        return None, None
    match = re.search(r"\{\{?#(.+?)(?:#|\})\}\s*(.*?)(?:\{|\[)END_CMD(?:\}|\])", response)
    if not match:
        return None, None
    command, args = match.groups()
    return command, args

def interact_with_llm(ui: AgentUI, hemisphere: str, user_input: str):
    """
    hemisphere: "left" or "right" or any node name
    user_input: prompt string
    """
    model_info = ui.api_config[hemisphere]
    provider = model_info.get("provider", "huggingface").lower()
    try:
        ui.log(f"Sending to {hemisphere} ({provider}) LLM: {user_input}")
        if hemisphere == "left":
            ui.left_request_text.delete(1.0, tk.END)
            ui.left_request_text.insert(tk.END, user_input)
        else:
            ui.right_request_text.delete(1.0, tk.END)
            ui.right_request_text.insert(tk.END, user_input)
        if provider == "openrouter":
            response = openrouter_infer(model_info, user_input)
        else:
            response = hf_infer(model_info, user_input)
        if hemisphere == "left":
            ui.left_response_text.delete(1.0, tk.END)
            ui.left_response_text.insert(tk.END, response)
        else:
            ui.right_response_text.delete(1.0, tk.END)
            ui.right_response_text.insert(tk.END, response)
        ui.log(f"Received from {hemisphere} ({provider}) LLM: {response}")
        return response
    except Exception as e:
        ui.log(f"Error interacting with {hemisphere} ({provider}) LLM: {str(e)}")
        return f"Error: {str(e)}"

def agent_loop(ui, get_right_response, get_command, get_args, agent2_prompt):
    global right_response, command, args
    while True:
        if ui.paused or not ui.initial_prompt_sent or not ui.awaiting_command:
            time.sleep(0.01)
            continue

        if right_response is None:
            time.sleep(0.01)
            continue

        command, args = process_response(ui, right_response)
        ui.show_command(command, args)
        if not command:
            llm_message = (
                "Bad command received. Please reply with ONLY a single valid command in the following format, and nothing else:\n"
                "{{#command#}args[END_CMD]\n"
                "For example: {{#filewrite#}script|myscript.py|print('hello')[END_CMD]"
            )
            right_response = interact_with_llm(ui, "right", llm_message)
            ui.log("Sent bad command prompt to right LLM")
            continue

        ui.awaiting_command = False

        if not command or not args:
            ui.log("No valid command/args to send to left LLM.")
            llm_message = (
                "Bad command received. Please reply with ONLY a single valid command in the following format, and nothing else:\n"
                "{{#command#}args[END_CMD]\n"
                "For example: {{#filewrite#}script|myscript.py|print('hello')[END_CMD]"
            )
            right_response = interact_with_llm(ui, "right", llm_message)
            ui.awaiting_command = True
            continue

        left_input = f"{agent2_prompt}\nCommand from right LLM: {{#{command}#}}{args}{{END_CMD}}"
        ui.log(f"Sending to left LLM for agreement: {left_input}")

        agreement_count = 0
        max_loops = 5
        agreed = False
        left_response = ""

        while agreement_count < max_loops:
            left_response = interact_with_llm(ui, "left", left_input)
            left_command, left_args = process_response(ui, left_response)
            if left_command == command and left_args == args:
                ui.log(f"Agreement reached with left LLM on command: {command} | {args}")
                agreed = True
                break
            agreement_count += 1
            ui.log(f"No agreement, loop {agreement_count}/{max_loops}")
            left_input = f"{agent2_prompt}\nRetry command: {{#{command}#}}{args}{{END_CMD}}"

        if not agreed:
            ui.log("No agreement after 5 loops, sending left response to right LLM")
            llm_message = f"No agreement from left LLM. Response: {left_response}. Refactor command."
            right_response = interact_with_llm(ui, "right", llm_message)
            command, args = process_response(ui, right_response)
            ui.show_command(command, args)
            if command:
                ui.last_command_time = datetime.now()
            continue

        # Run agreed command
        result = run_command(ui, command, args)
        ui.log(f"Command result: {result}")
        ui.last_command_time = datetime.now()

        # Send result back to right LLM
        llm_message = f"Command executed: {{#{command}#}}{args}{{END_CMD}}. Result: {result}"
        right_response = interact_with_llm(ui, "right", llm_message)
        command, args = process_response(ui, right_response)
        ui.show_command(command, args)
        if command:
            ui.last_command_time = datetime.now()

        right_response = None
        ui.awaiting_command = True

def main():
    # Load hemisphere_api.json for LLM API config
    try:
        with open(BASE_DIR / "hemisphere_api.json") as f:
            api_config = json.load(f)
    except FileNotFoundError:
        print(r"Error: hemisphere_api.json not found in C:\AIAgent")
        sys.exit(1)
    except json.JSONDecodeError:
        print(r"Error: hemisphere_api.json has invalid JSON format")
        sys.exit(1)

    # Check LLM connections before starting UI/agent loop
    connection_results = check_llm_connections(api_config)
    failed = [k for k, v in connection_results.items() if v]
    if failed:
        print("One or more LLM endpoints failed to connect:")
        for k in failed:
            print(f"  {k}: {connection_results[k]}")
        print("Please check your hemisphere_api.json and network connectivity.")
        sys.exit(1)


    with open(MEMORY_DIR / "agent_init.txt", encoding="utf-8") as f:
        init_prompt = f.read()
    with open(MEMORY_DIR / "agent2.txt", encoding="utf-8") as f:
        agent2_prompt = f.read()

    # Initialize UI
    ui = AgentUI(config, api_config)
    ui.init_prompt = init_prompt  # Store for later use
    ui.agent2_prompt = agent2_prompt

    ui.log("Agent initialized")

    # Do NOT send initial prompt here; wait for resume

    # Start agent loop in a background thread
    global right_response, command, args
    right_response, command, args = None, None, None
    threading.Thread(target=agent_loop, args=(ui, lambda: right_response, lambda: command, lambda: args, agent2_prompt), daemon=True).start()

    # Start the Tkinter event loop
    ui.root.mainloop()

if __name__ == "__main__":
    main()