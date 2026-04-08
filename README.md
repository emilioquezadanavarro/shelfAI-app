# 🏪 ShelfAI

> ⚠️ **This project is currently under active development.** Features may change without notice.

**ShelfAI** is an AI-powered retail shelf auditing application that uses computer vision to evaluate in-store product displays against brand compliance rules. Field workers upload shelf photos, and a GPT-4o-mini Vision Agent instantly grades the display — providing an overall compliance score and itemized rule-by-rule feedback.

---

## 🏗️ Architecture

```
Frontend (Jinja2 + CSS)  →  FastAPI Backend  →  LangChain Vision Agent (GPT-4o-mini)
                                    ↕
                              Supabase (PostgreSQL)
```

### Tech Stack
| Layer        | Technology                          |
|--------------|--------------------------------------|
| **Backend**  | FastAPI, Uvicorn, Python 3.13       |
| **AI Engine**| LangChain, OpenAI GPT-4o-mini       |
| **Database** | Supabase (PostgreSQL)                |
| **Frontend** | Jinja2, HTML, Vanilla CSS, JavaScript|
| **Schemas**  | Pydantic v2 (Structured AI Output)   |

---

## 📁 Project Structure

```
shelfAI-app/
├── run.py                          # Application entry point
├── app/
│   ├── __init__.py                 # FastAPI app factory
│   ├── ai_agents/
│   │   └── evaluation_agent.py     # GPT-4o-mini Vision Agent (EvaluationAgent class)
│   ├── database/
│   │   ├── database_setup.py       # Supabase client initialization
│   │   └── database_schema.py      # Pydantic models for AI output + profiles
│   ├── routes/
│   │   └── routes.py               # All API endpoints and page routes
│   ├── services/                   # (Reserved for future business logic)
│   └── templates/
│       ├── index.html              # Profile selection page
│       ├── profile_dashboard.html  # Photo upload dashboard
│       ├── evaluation_dashboard.html # AI score results page
│       └── static/
│           └── styles.css          # Glassmorphism design system
├── .env                            # Environment variables (not committed)
├── requirements.txt                # Python dependencies
└── README.md
```

---

## 🗄️ Database Schema (Supabase)

| Table                      | Purpose                                    |
|----------------------------|--------------------------------------------|
| `profiles`                 | Field worker accounts                      |
| `stores`                   | Physical retail locations                  |
| `providers`                | Brand/product providers                    |
| `campaigns`                | Campaign rules + reference images          |
| `ai_evaluation`            | Parent audit record (score, image, worker) |
| `ai_evaluation_feedback`   | Itemized pass/fail feedback per rule       |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- A Supabase project with tables created
- An OpenAI API key
- Supabase credentials

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/shelfAI-app.git
cd shelfAI-app

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### Run the Application

```bash
python run.py
```

The app will be available at `http://localhost:8000`.

---

## 🔄 Application Flow

1. **Login** → Field worker selects their profile on the home page.
2. **Upload** → Worker uploads a shelf photo from the dashboard.
3. **AI Analysis** → The `EvaluationAgent` encodes the image to Base64 and sends it to GPT-4o-mini with strict campaign rules.
4. **Structured Output** → LangChain forces the AI response into a Pydantic schema (`AIEvaluation` + `AIEvaluationFeedback`).
5. **Database Save** → The score is saved to `ai_evaluation`, and each itemized feedback is bulk-inserted into `ai_evaluation_feedback`.
6. **Results** → The browser redirects (POST-Redirect-GET) to a beautiful scorecard dashboard showing the grade and rule breakdown.

---

## 📝 License

This is a proprietary project built to solve a real-world retail compliance challenge. All rights reserved.