
# ❀˖° HerHealth

### A Smarter Way to Access Women's Healthcare

## 🚀 Live Demo

**Live Application:** [https://your-frontend-url.vercel.app](https://anon-care-ej1c.vercel.app)

**Backend API:** [https://your-backend-url.vercel.app](https://anon-care-omega.vercel.app/)

**API Documentation:** [https://your-backend-url.vercel.app/docs](https://anon-care-omega.vercel.app/docs)

> **Your health. Your privacy. Your choice.**

HerHealth is a privacy-first women's healthcare companion that helps users track menstrual health, wellness, and access general health information through an AI-powered assistant.

## ✨ Features

- 🔐 **Private Onboarding** — Start without name, email, phone number, or password.
- 🩸 **Cycle Tracker** — Track periods, flow, pain, symptoms, mood, and cycle history.
- 🌿 **Wellness Tracker** — Track mood, energy, sleep, appetite, and daily wellness.
- 📊 **Insights** — View descriptive trends across cycle and wellness data.
- 🤖 **AI Health Assistant** — Ask general women's health questions with trusted-source grounding.
- 🚨 **Safety Checks** — Identifies potentially urgent situations and recommends appropriate medical care.
- 🔒 **Local-First Privacy** — Cycle and wellness data stays in the browser and is not automatically sent to the AI.

## 🛠️ Tech Stack

**Frontend:** React, Vite, TypeScript, React Router, CSS  
**Backend:** Python, FastAPI, Uvicorn  
**AI:** Google Gemini API, Retrieval-based Knowledge Base  
**Storage:** Browser localStorage  
**Tools:** Git, GitHub, VS Code, GitHub Copilot

## 🧠 AI Architecture

```text
User Question
     ↓
React Frontend
     ↓
FastAPI /api/ask
     ↓
Safety Check
     ↓
Knowledge Base Retrieval
     ↓
Google Gemini
     ↓
Answer + Sources + Safety Information
```

The AI provides general health information only. It does not diagnose conditions, prescribe medication, or provide treatment plans.

## 🔒 Privacy

HerHealth follows a privacy-first approach.

The AI request contains only the user's question:

```json
{
  "question": "What is PCOS?"
}
```

Cycle history, wellness history, mood, sleep, and other local tracking data are not automatically sent to the AI.

API keys are stored only on the backend and are never exposed in the frontend.

### Doctor registration lookup

The Doctors page can search a configured Apify actor through the backend. Configure `APIFY_API_TOKEN`, `APIFY_ACTOR_ID`, and the actor-specific `APIFY_INPUT_*_FIELD` and `APIFY_OUTPUT_*_FIELD` mappings in `backend/.env`. See `backend/.env.example` for the full list. A search input mapping is required for each supplied search value; map at least the actor's name or registration-number output to display usable results.

No actor is preconfigured: an advertised NMC/IMR actor was found, but its live input/output schema, current register coverage, and official-source behavior could not be verified. Confirm the chosen actor's documentation and sample dataset first, then set field mappings to its exact schema. The integration does not treat scraped results as official verification; missing results do not establish that a doctor is unregistered. Actor executions use the Apify API asynchronously and read paginated dataset results.

## 🚀 Getting Started

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at:

```text
http://localhost:5173
```

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install google-genai python-dotenv
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_api_key
ALLOWED_ORIGINS=http://localhost:5173
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## 📸 Screenshots

<img width="1470" height="803" alt="image" src="https://github.com/user-attachments/assets/7f2d6341-6cb1-4e62-8ad2-161515cc4a95" />

<img width="1470" height="791" alt="image" src="https://github.com/user-attachments/assets/95435fbf-fa99-4aaa-a7d6-7a30fbb5d464" />

<img width="1470" height="807" alt="image" src="https://github.com/user-attachments/assets/ce8736b8-7a2d-4390-82f0-0642046c810c" />

<img width="1470" height="810" alt="image" src="https://github.com/user-attachments/assets/52739ec4-2bae-41fb-aec0-97c28c81c192" />

<img width="1470" height="796" alt="image" src="https://github.com/user-attachments/assets/11899d88-397a-4a22-a96d-080bcbe22bc4" />

<img width="1470" height="799" alt="image" src="https://github.com/user-attachments/assets/e52a2638-a4ce-4f4f-884b-e721e18fa897" />

## ⚠️ Disclaimer

HerHealth provides general health information for educational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Users experiencing severe or urgent symptoms should seek appropriate medical care.

## 🔮 Future Scope

- Trusted doctor network
- Secure doctor consultations
- Medical report sharing
- Improved medical RAG
- Secure authentication and consent management
- Mobile application
- Healthcare payments and appointments

## 👥 Team

| Member | Role |
|---|---|
| Sharayu | Frontend Development |
| Tanishka | Connecting Frontend & Backend |
| Sanchita | AI Integration |
| Mukta | Backend Development |

---

### 🌸 HerHealth

**Your health. Your privacy. Your choice.**
