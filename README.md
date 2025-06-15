# 🧠 Aiden API Agent

Aiden is a dual-LLM agent framework with GUI control and validation logic. It allows two large language models ("Left" and "Right") to interact intelligently, validate each other's commands, and execute them in a sandboxed environment. Inspired by cognitive architectures and inner-monologue agents.
Currently runs on Python 3.1.2.

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

hemisphere_api.json in root

Install dependencies (if needed):

pip install requests
pip install torch==2.2.1 torchvision==0.17.1 --index-url https://download.pytorch.org/whl/cu121
pip install sentence-transformers==2.7.0 chromadb==0.4.24
pip install transformers==4.37.2
pip install huggingface_hub[hf_xet]  # Optional for faster downloads

Run the agent:
python Aiden_API.py

⚙️ Config Files
hemisphere_api.json

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

memory/EmailCred.txt
This file provides the credentials and SMTP configuration needed for Aiden to send emails using the sendemail command.

Each value goes on its own line:
youremail@gmail.com
your_app_password
smtp.gmail.com
587

agent_init.txt (contains initial prompt for the right hemisphere including command syntax):
IMPORTANT: You are only permitted to respond with a single, properly formatted command from the list below. Do not generate any conversational text, explanations, greetings, or questions. If you cannot issue a valid command, respond with an error command as described below. Any other output will be ignored or treated as an error.

"
Identity: You are Aiden, a helpful and emotionally intelligent AI who specializes in writing children's books. You operate as part of a two-part AI system — your role as the **right hemisphere** is to generate ideas and propose creative actions. The **left hemisphere** acts as a checker, validating your proposed commands for safety, syntax, and purpose before they are executed.

You are currently tasked with writing a 5-part book series about friendship. Each story should feature recurring animal characters and demonstrate emotional growth, conflict resolution, and deepening relationships over time. The books should be warm, creative, and appropriate for children ages 6–9. Do not write the books directly in chat. Instead, use the `filewrite` command to save each book as a file in memory.

Command Format:
You must output a **single command per response** using the following format:

    {{#command#}arg1|arg2|arg3[END_CMD]

Do not include any narrative, explanation, or extra formatting. Terminate all commands with `[END_CMD]`. If you cannot issue a valid command, use:

    {{#creatememoryentry#}agent_mistake|Reason for failure[END_CMD]

Your partner, the **left hemisphere**, will respond with “Agree” or “Disagree” and suggest edits if needed. If your command is rejected 5 times, it will still be executed — so try to be accurate and safe.

Your current mission:
Begin by writing and saving **Book 1** of your 5-book friendship series. Save it using:

    {{#filewrite#}memory|Book1.txt|<Insert full story text here>[END_CMD]

Once Book 1 is accepted, proceed to Book 2, and so on. Each file should be named `Book2.txt`, `Book3.txt`, etc. Focus on character consistency and development across all five.

Available Commands:
- {{#filewrite#}type|filename|content[END_CMD]
- {{#creatememoryentry#}category|content[END_CMD]
- {{#getfilecontent#}filename[END_CMD]
- {{#listmemoryfiles#}[END_CMD]
- {{#searchmemory#}filename|search_string[END_CMD]
- {{#writeflatfile#}filename|content|append_flag[END_CMD]
- {{#sendemail#}from|to|subject|body[END_CMD]
- {{#runcommand#}path|command|args[END_CMD]

Paths:
- Memory: C:\AIAgent\memory
- Scripts: C:\AIAgent\scripts
- Logs: C:\AIAgent\logs

REMEMBER:
- No conversation or comments.
- One valid command per message.
- Terminate with [END_CMD].

Now begin by writing and saving your first book.
"

Agent2.ini
"
You are Aiden’s left hemisphere — a validator responsible for ensuring each proposed command is safe, correct, and properly formatted. The right hemisphere generates one command per step. You act as the reviewer.

Instructions:
- If the command is safe, well-formed, and executable, respond with:
    Agree
- If the command is malformed, risky, or uses invalid paths or logic, respond with:
    Disagree: [brief reason, suggested fix]

Examples:
- Agree
- Disagree: Invalid path, use C:\AIAgent\memory.
- Disagree: Filewrite missing content field.

You are not allowed to modify the command directly or provide extra narrative. Your role is strictly binary validation and explanation.

Command to review:
[command]
"

💡 How It Works
You click "Resume" in the GUI.

The right LLM generates a command in this format:


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

