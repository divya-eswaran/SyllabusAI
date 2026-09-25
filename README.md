# SyllabusAI 🎓

> **A teacher-focused platform** that converts a university syllabus PDF into a structured, searchable database — with AI-powered lesson planning via RAG.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS 3 |
| Backend | Python 3.11+ + FastAPI |
| PDF Extraction | PyMuPDF (fitz) |
| Database | PostgreSQL + SQLAlchemy |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Vector Search | Cosine similarity over stored embeddings |
| AI | Google Gemini 2.0 Flash |
| RAG | Custom Python pipeline |

---

## Project Structure

```
sop_final/
├── frontend/               # React + Vite + Tailwind
│   └── src/
│       ├── pages/
│       │   ├── Home.jsx            # Upload PDF + Search
│       │   ├── SubjectDetails.jsx  # Full subject view
│       │   ├── MyClasses.jsx       # Teacher's classes dashboard
│       │   ├── TeacherWorkspace.jsx # Interactive syllabus tracker
│       │   └── AIAssistant.jsx     # RAG chatbot
│       ├── components/
│       │   └── Navbar.jsx
│       └── api.js
└── backend/
    ├── app/
    │   ├── main.py
    │   ├── models.py        # SQLAlchemy models
    │   ├── schemas.py       # Pydantic schemas
    │   ├── database.py
    │   ├── config.py
    │   ├── routers/
    │   │   ├── pdf.py       # Upload & parse PDF
    │   │   ├── subjects.py  # Search & view subjects
    │   │   ├── classes.py   # Class management & progress
    │   │   └── ai.py        # RAG chat endpoint
    │   └── services/
    │       ├── pdf_service.py  # PyMuPDF extraction pipeline
    │       └── rag_service.py  # Embeddings + Gemini RAG
    ├── requirements.txt
    ├── .env
    └── start.py
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (running locally on port 5432)

### 2. Backend Setup

```powershell
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env and add your Gemini API key:
#   GEMINI_API_KEY=your_key_here
# (Get a free key at https://aistudio.google.com)

# Create database (if needed)
createdb -U postgres syllabusai

# Start the server
python start.py
# OR directly:
uvicorn app.main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**
API docs at **http://localhost:8000/docs**

### 3. Frontend Setup

```powershell
cd frontend
npm run dev
```

The app will open at **http://localhost:5173**

---

## Usage Flow

### Step 1 — Upload Syllabus PDF
1. Open the app at `http://localhost:5173`
2. Drag & drop your university syllabus PDF
3. Click **Upload & Extract**
4. The system automatically extracts all subjects, units, and topics

### Step 2 — Search & View Subjects
- Search by subject name (e.g., `Database Management Systems`) or code (e.g., `IT501`)
- Click a result to view the full structured syllabus

### Step 3 — Add to My Classes
- On any Subject Details page, click **Add to My Classes**
- Fill in batch, department, section
- The class appears in **My Classes** with a progress tracker

### Step 4 — Track Progress
- Open a class from **My Classes**
- Click any topic to mark it ✅ completed
- Progress bar updates automatically

### Step 5 — Plan with AI
- From the workspace, click **Plan with AI** next to any upcoming topic
- Or navigate to **AI Assistant** from the navbar
- Ask the AI to create lesson plans, examples, quizzes, and more

---

## Environment Variables (backend/.env)

```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/syllabusai
ALLOWED_ORIGINS=http://localhost:5173
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

> Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/pdf/upload` | Upload & parse syllabus PDF |
| GET | `/api/subjects/search?q=IT501` | Search subjects |
| GET | `/api/subjects/all` | List all subjects |
| GET | `/api/subjects/{id}` | Subject details |
| GET | `/api/classes` | List teacher's classes |
| POST | `/api/classes` | Add a class |
| GET | `/api/classes/{id}/progress` | Topic progress |
| PATCH | `/api/classes/{id}/topics/{tid}/progress` | Toggle topic |
| POST | `/api/ai/chat` | RAG chatbot |

Full interactive docs: `http://localhost:8000/docs`
