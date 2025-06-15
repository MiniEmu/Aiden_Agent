# 🧠 Aiden API Agent

Aiden is a dual-LLM agent framework with GUI control and validation logic. It allows two large language models ("Left" and "Right") to interact intelligently, validate each other's commands, and execute them in a sandboxed environment. Inspired by cognitive architectures and inner-monologue agents.

![Aiden Screenshot](screenshot.png) <!-- Optional: Include GUI screenshot -->

## 🚀 Features

- ✅ Dual LLM setup with agreement-checking logic
- 🖥️ Tkinter GUI for interaction, status, logging, and command visibility
- 📡 Supports both Hugging Face and OpenRouter API endpoints
- 💬 Custom command parsing and safe execution layer
- 💾 SQLite memory system + file I/O commands
- 📧 Built-in email sending via SMTP
- 🛠 Command set includes file writing, subprocesses, memory logging, and more
- 🧪 Easy to extend with new command handlers or LLM backends

---

## 📂 Project Structure

C:\AIAgent
│
├── memory
│ ├── EmailCred.txt # Email user + password (line 1, line 2)
│ ├── memory.db # SQLite database of memory entries
│ ├── agent_init.txt # Initial prompt for the "right" LLM
│ └── agent2.txt # Prompt used by the "left" LLM to verify commands
│
├── scripts\ # Folder for dynamically written scripts
├── logs\ # Logs written by the agent
│ └── agent.log
│
├── hemisphere_api.json # API config for Hugging Face/OpenRouter
├── hemisphere.json # General config (email, SMTP, etc.)
└── Aiden_API.py # Main agent application

---

## 🛠️ Installation

> **Note:** Currently Windows-only due to screen size detection via `ctypes.windll.user32`.

### Prerequisites

- Python 3.8+
- `requests`, `tkinter` (comes with most Python installs), `sqlite3`

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/aiden-agent.git
   cd aiden-agent

   Set up the directory structure in C:\AIAgent and place:

agent_init.txt and agent2.txt in memory\

Email credentials in memory\EmailCred.txt

hemisphere.json and hemisphere_api.json in root

Install dependencies (if needed):

bash
Copy
Edit
pip install requests
Run the agent:

bash
Copy
Edit
python Aiden_API.py
⚙️ Config Files
hemisphere_api.json
json
Copy
Edit
{
  "left": {
    "provider": "huggingface",
    "model": "gpt2",
    "api_url": "https://api-inference.huggingface.co/models/gpt2",
    "api_token": "hf_your_token_here"
  },
  "right": {
    "provider": "openrouter",
    "model": "openai/gpt-3.5-turbo",
    "api_url": "https://openrouter.ai/api/v1",
    "api_token": "your_openrouter_key"
  }
}
hemisphere.json
json
Copy
Edit
{
  "smtp": {
    "host": "smtp.gmail.com",
    "port": 587
  }
}
💡 How It Works
You click "Resume" in the GUI.

The right LLM generates a command in this format:

less
Copy
Edit
{{#command#}arg1|arg2|arg3[END_CMD]
The left LLM verifies and agrees (or disagrees).

If both agree, the command is run.

The result is shown in the GUI and sent back to the right LLM.

📜 Supported Commands
filewrite – Write content to a file in scripts or memory

creatememoryentry – Insert memory into the SQLite DB

getfilecontent – Read memory files

searchmemory – Keyword search memory or database

sendemail – Send emails via SMTP

runcommand – Run a shell script

browseweb – Stubbed; not supported in API mode

🧱 To-Do & Future Ideas
 Add cross-platform screen detection

 Queue-based thread-safe communication

 Command sandboxing and validation layer

 Optional CLI mode without GUI

 Web-based control panel

