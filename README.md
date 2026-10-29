# 🤖 Multimodal AI Personal Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-red.svg)](https://streamlit.io)
[![Gemini API](https://img.shields.io/badge/Google%20Gemini-3.5%20Flash-orange.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade, modular, and beginner-friendly **Multimodal AI Personal Assistant** developed as a 2nd-year B.Tech CSE (AI/ML) Capstone Project.

The application features a decoupled architecture with a high-performance **FastAPI backend** and a ChatGPT-styled **Streamlit frontend**, integrating Grounded RAG, live web retrieval, watermark-free image generation, and emotional support triage.

---

## ✨ Key Features

1. **💬 ChatGPT-Style Unified Chat Interface**:
   - Pinned bottom input panel (`stBottom`) that stays fixed as messages stream.
   - Clean UI without default Streamlit headers or telemetry bars.

2. **📄 Universal Document Understanding & RAG**:
   - Accepts **PDF** (`.pdf`), **Word** (`.docx`), **PowerPoint** (`.pptx`), **Excel** (`.xlsx`), **CSV** (`.csv`), **Text** (`.txt`), and **Markdown** (`.md`).
   - Automated semantic chunking preserving `[Page X]` and `[Slide X]` citation markers.
   - Grounded Q&A with direct citation accordions referencing specific slides and page excerpts.

3. **🖼️ Multimodal Vision & Watermark-Free Image Generation**:
   - **Vision**: Upload images (PNG, JPG, WEBP) for instant visual scene understanding and analysis.
   - **Generation**: Automated prompt intent detection (`"draw a..."`, `"generate an image of..."`) triggering neural Stable Diffusion generation. 
   - **Clean & Compact**: 100% watermark-free, displayed in a compact card (`width=420`) with direct JPEG download buttons.

4. **🛡️ 503-Resilient Gemini Model Cascade**:
   - Automatically handles peak-hour load spikes with an in-memory fallback chain:
     $$\text{gemini-3.5-flash} \longrightarrow \text{gemini-3.5-flash-lite} \longrightarrow \text{gemini-3.8-flash}$$
   - Prevents server-side 500/503 errors and keeps conversations responsive without wasting token quotas.

5. **💾 Dual-Engine Database Architecture**:
   - Production mode: **PostgreSQL 16** with native `pgvector` for vector similarity search.
   - Zero-setup fallback: Automatically detects if PostgreSQL is offline and switches seamlessly to local **SQLite** (`local_assistant.db`), ensuring the app runs out-of-the-box anywhere.

6. **🌐 Live Web Search Integration**:
   - Integrated Tavily search fetching verified live sources, URLs, and real-time facts with clickable citations.

7. **💚 Emotional Support Space**:
   - Empathetic active listening mode with built-in safety checks that detect crisis phrases and immediately present verified emergency helpline resources.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | Pure Python chat interface, file uploaders, and session management. |
| **Backend API** | FastAPI + Uvicorn | Async REST API with automated OpenAPI docs and multipart handling. |
| **LLM Reasoning** | Google Gemini (`google-genai` SDK) | Multimodal vision, text generation, and RAG synthesis. |
| **Image Generation** | Stable Diffusion (AI Horde) | Watermark-free, free-tier image generation. |
| **Embeddings** | `sentence-transformers` | `all-MiniLM-L6-v2` dense 384-dimensional vector embeddings. |
| **Database** | PostgreSQL (pgvector) / SQLite | Session history, document chunks, and embeddings. |
| **Document Parsers** | `pypdf`, `python-docx`, `python-pptx`, `openpyxl` | Deep text and structure extraction across formats. |
| **Search Engine** | Tavily Search API | Live web search and citation verification. |

---

## 📂 Project Structure

```
MM Chatbot/
│
├── .env.example                       # Environment variables template (safe to commit)
├── .gitignore                         # Excludes secrets, databases, and caches
├── requirements.txt                   # Project dependencies
├── pytest.ini                         # Automated test runner configuration
├── README.md                          # Project documentation
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint, middleware, CORS
│   │   ├── core/
│   │   │   └── config.py              # Configuration & environment variables
│   │   ├── db/
│   │   │   └── session.py             # SQLAlchemy engine with SQLite auto-fallback
│   │   ├── models/
│   │   │   ├── conversation.py        # Conversation and Message ORM models
│   │   │   └── document.py            # Document and DocumentChunk ORM models
│   │   ├── schemas/
│   │   │   ├── chat.py                # Pydantic schemas for chat endpoints
│   │   │   └── document.py            # Document & RAG schemas
│   │   ├── services/
│   │   │   ├── llm_service.py         # Gemini SDK client with auto-cascade
│   │   │   ├── rag_service.py         # Embedding computation & chunk retrieval
│   │   │   ├── image_service.py       # Dual-engine watermark-free image generator
│   │   │   ├── document_service.py    # Document parsing (PDF, DOCX, PPTX, XLSX)
│   │   │   ├── search_service.py      # Tavily search integration
│   │   │   └── emotional_service.py   # Emotional support & crisis triage
│   │   └── api/
│   │       ├── chat.py                # /api/chat endpoints (multimodal + RAG)
│   │       └── documents.py           # /api/documents upload & query endpoints
│   └── tests/
│       ├── test_chat.py               # Chat endpoint & crisis triage tests
│       ├── test_documents.py          # Document parser & RAG verification
│       └── test_health.py             # Health check tests
│
└── frontend/
    ├── streamlit_app.py               # Streamlit application entrypoint
    ├── components/
    │   ├── chat_view.py               # ChatGPT-like chat view & media cards
    │   └── sidebar.py                 # Sidebar session manager & mode toggles
    └── utils/
        └── api_client.py              # HTTP client communicating with backend
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed.
- Free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).
- *(Optional)* Free Tavily API Key from [Tavily](https://tavily.com/) for live web search.

### 2. Installation
Clone your repository and install dependencies:
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd "MM Chatbot"

python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Credentials
Copy the example environment file and add your keys:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
TAVILY_API_KEY=your_tavily_api_key_here
BACKEND_URL=http://localhost:8000
```

### 4. Running the Application

Open two terminal tabs:

**Terminal 1 — Start the FastAPI Backend**:
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Backend Swagger API Docs will be available at: `http://127.0.0.1:8000/docs`

**Terminal 2 — Start the Streamlit Frontend**:
```bash
python -m streamlit run frontend/streamlit_app.py --server.port 8501
```
The Chatbot UI will open in your browser at: **`http://localhost:8501`**

---

## 🧪 Running Automated Tests

Run the test suite with `pytest`:
```bash
python -m pytest -v
```
All 6 automated tests verify:
- Document extraction and vector chunk indexing.
- Standard chat and Gemini fallback response synthesis.
- Emotional support crisis triage safeguards.
- System diagnostic health checks.

---

## 🔒 Security & Privacy Notice
- Never commit your `.env` file or API keys to any public GitHub repository.
- Uploaded files in chat are strictly isolated per conversation session and are not shared across conversations.

---

## 📜 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
