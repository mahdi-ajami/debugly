<div align="center">
  <img src="assets/icon.png" alt="Debugly Logo" width="100" />
</div>

<h1 align="center">🐞 Debugly</h1>
<h3 align="center">Intelligent Screenshot-powered Error Debugger with Self-Learning AI</h3>

<p align="center">
  Take a screenshot of any error → AI understands it → Finds the best solution → Gets smarter over time.
  <br/>
  <strong>100% offline · Privacy-first · Self-improving</strong>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python 3.10+" /></a>
  <a href="#"><img src="https://img.shields.io/badge/UI-Flet-14B8FF?logo=flet&logoColor=white&style=flat-square" alt="Flet" /></a>
  <a href="#"><img src="https://img.shields.io/badge/LLM-Ollama-000000?logo=ollama&logoColor=white&style=flat-square" alt="Ollama" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Vector_ChromaDB-EA5E2E?logo=chromadb&logoColor=white&style=flat-square" alt="ChromaDB" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Orchestration-LangChain-1C3C5C?logo=langchain&logoColor=white&style=flat-square" alt="LangChain" /></a>
  <a href="#"><img src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white&style=flat-square" alt="FastAPI" /></a>
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-6CB4EE?style=flat-square" alt="MIT" /></a>
  <a href="#"><img src="https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square" alt="PRs Welcome" /></a>
</p>

<br/>

---

## ✨ Key Features

<table>
  <tr>
    <td width="50" align="center">📸</td>
    <td width="200"><strong>Screenshot OCR</strong></td>
    <td>Upload any error screenshot — LLaVA extracts the error message automatically, whether from terminal, IDE, browser, or log file.</td>
  </tr>
  <tr>
    <td align="center">🧠</td>
    <td><strong>RAG-Powered Answers</strong></td>
    <td>Retrieves the most relevant solutions from your local knowledge base using ChromaDB + LangChain for accurate, contextual answers.</td>
  </tr>
  <tr>
    <td align="center">⚡</td>
    <td><strong>Streaming Responses</strong></td>
    <td>Watch answers appear word-by-word in real time — no waiting for the full response.</td>
  </tr>
  <tr>
    <td align="center">🔄</td>
    <td><strong>Self-Learning RL</strong></td>
    <td>Every 👍 / 👎 trains a Multi-Armed Bandit algorithm to favor strategies that historically deliver better solutions.</td>
  </tr>
  <tr>
    <td align="center">🔒</td>
    <td><strong>Fully Offline</strong></td>
    <td>Everything runs locally on your machine. Zero data leaves your computer. No API keys, no cloud, no tracking.</td>
  </tr>
  <tr>
    <td align="center">🎨</td>
    <td><strong>Modern Desktop UI</strong></td>
    <td>Clean, responsive interface built with Flet — familiar, fast, and visually polished.</td>
  </tr>
  <tr>
    <td align="center">📦</td>
    <td><strong>Extensible KB</strong></td>
    <td>Preloaded with solutions for Python, Docker, FastAPI, JavaScript, and more. Add your own knowledge base anytime.</td>
  </tr>
</table>

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology | Purpose |
|-------|-----------|---------|
| 🖥️ **Desktop UI** | <img src="https://img.shields.io/badge/Flet-14B8FF?logo=flet&logoColor=white" /> | Python-based Flutter UI framework |
| ⚙️ **Backend** | <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" /> | Internal asynchronous API server |
| 👁️ **Vision** | <img src="https://img.shields.io/badge/LLaVA-000000?logo=ollama&logoColor=white" /> | Screenshot → error text extraction |
| 🧠 **LLM** | <img src="https://img.shields.io/badge/Llama_3.1-000000?logo=ollama&logoColor=white" /> | Solution generation & reasoning |
| 📊 **Vector DB** | <img src="https://img.shields.io/badge/ChromaDB-EA5E2E" /> | Persistent semantic search |
| 🔗 **Orchestration** | <img src="https://img.shields.io/badge/LangChain-1C3C5C" /> | RAG pipeline & chain management |
| 🎯 **RL Engine** | ε-Greedy Bandit | Epsilon-Greedy Multi-Armed Bandit |
| 🚀 **Packaging** | PyInstaller | Standalone executable builds |

</div>

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.10 or higher
- **Ollama** — [Download & install](https://ollama.com) (available for macOS, Linux, Windows)
- **Git**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/debugly.git
cd debugly

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
# .venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull the required AI models
ollama pull llama3.1
ollama pull llava
ollama pull nomic-embed-text

# 5. Seed the knowledge base
python scripts/seed_kb.py

# 6. Launch Debugly
python main.py
```

> 🎉 The app will start the internal FastAPI server, initialize ChromaDB, and open the Debugly desktop window. You're ready to debug!

---

## 📁 Project Structure

```
debugly/
├── main.py                      # Application entry point
│
├── core/                        # Core AI & ML logic
│   ├── agent.py                 # LangChain orchestrator agent
│   ├── rag_pipeline.py          # Retrieval-Augmented Generation pipeline
│   ├── vlm_handler.py           # LLaVA integration for screenshot OCR
│   ├── reward_system.py         # Multi-Armed Bandit RL engine
│   └── config.py                # Central configuration & constants
│
├── app/                         # Desktop UI
│   ├── main_view.py             # Main window layout & event handling
│   └── components/              # Reusable UI widgets
│       ├── chat_bubble.py       # Message bubble component
│       ├── feedback_bar.py      # 👍 / 👎 feedback controls
│       └── solution_card.py     # Sources & references panel
│
├── db/                          # Vector database
│   └── chroma.py                # ChromaDB client & collection management
│
├── models/                      # Data models
│   └── schemas.py               # Pydantic schemas (ErrorQuery, Feedback, etc.)
│
├── utils/                       # Utility functions
│   └── helpers.py               # ID generation, text helpers
│
├── knowledge_base/              # Seed data & ingested documents
│   └── seed.py                  # 12 common error-solution pairs
│
├── scripts/                     # Maintenance & automation
│   ├── seed_kb.py               # CLI to populate ChromaDB
│   └── ...
│
├── assets/                      # Icons, images, static resources
├── requirements.txt             # Python dependencies
├── .gitignore
└── README.md
```

---

## 🧠 How It Works

```mermaid
flowchart TB
    A["📸 Upload Screenshot"] --> B["👁️ LLaVA extracts error text"]
    B --> C["📊 ChromaDB searches knowledge base"]
    C --> D["🧠 Llama 3.1 generates solution"]
    D --> E["⚡ Stream response to UI"]
    E --> F["👍 / 👎 User feedback"]
    F --> G["🎯 Bandit updates arm weights"]
    G -.-> B
```

### The 4-Step Debug Loop

| Step | What Happens |
|------|-------------|
| **1. Capture** | Drop a screenshot of any error — terminal, VS Code, browser console, or log viewer |
| **2. Extract** | LLaVA (Vision-Language Model) reads the image and extracts the exact error text |
| **3. Retrieve** | ChromaDB finds the most semantically similar solutions from the knowledge base |
| **4. Learn** | Your 👍 / 👎 feedback trains the Multi-Armed Bandit to prioritize what works best |

---

## 📌 Roadmap

| Status | Feature |
|--------|---------|
| ✅ | Screenshot → text extraction with LLaVA |
| ✅ | Local RAG pipeline with ChromaDB |
| ✅ | Streaming response UI |
| ✅ | Multi-Armed Bandit reinforcement learning |
| 🔄 | Multi-image / multi-error support |
| 🔄 | Side-by-side diff view (before / after fix) |
| 🔄 | Plugin system for custom knowledge sources |
| 🔄 | One-click installer (Windows / macOS / Linux) |

---

## 🤝 Contributing

Contributions of all sizes are welcome — whether it's a typo fix, a new knowledge base entry, or a major feature.

1. **Fork** the project
2. **Create** your feature branch (`git checkout -b feat/awesome-idea`)
3. **Commit** your changes (`git commit -m 'feat: add awesome idea'`)
4. **Push** to the branch (`git push origin feat/awesome-idea`)
5. **Open** a Pull Request

> Please ensure your code is clean, well-documented, and passes existing checks before submitting.

---

<p align="center">
  Made with ❤️ for developers<br/>
  <sub>Built with Python · Flet · Ollama · ChromaDB · LangChain</sub>
  <br/><br/>
  <a href="#">⭐ Star this project</a> · 
  <a href="https://github.com/yourusername/debugly/issues">🐛 Report a bug</a> · 
  <a href="https://github.com/yourusername/debugly/discussions">💬 Join discussion</a>
</p>
