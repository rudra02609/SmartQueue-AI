# 🏥 SmartQueue AI

An AI-powered queue management system for Healthcare & Banking. Reduces patient/customer wait times using intelligent priority scheduling, real-time WebSocket updates, and predictive wait-time estimation.

---

## 📁 Project Structure

```
SmartQueue-AI/
├── app/                    ← FastAPI backend
│   ├── main.py             ← App entry point
│   ├── models.py           ← SQLAlchemy models
│   ├── schemas.py          ← Pydantic schemas
│   ├── ai/                 ← ML wait-time predictor
│   ├── auth/               ← JWT authentication
│   ├── database/           ← DB connection & session
│   ├── routers/            ← API route handlers
│   ├── services/           ← Business logic (queue engine, notifications, etc.)
│   └── utils/              ← Utility helpers
├── frontend/               ← Static HTML/CSS/JS frontend
│   ├── index.html          ← Landing page
│   ├── admin.html          ← Admin dashboard
│   ├── healthcare.html     ← Healthcare queue registration
│   ├── banking.html        ← Banking queue registration
│   ├── token.html          ← Token display
│   ├── tracking.html       ← Queue tracking
│   ├── grievance.html      ← Patient grievance form
│   ├── admin-grievance.html← Admin grievance dashboard
│   ├── css/                ← Stylesheets
│   └── js/                 ← JavaScript modules
├── scripts/                ← Helper scripts
│   ├── start-backend.bat
│   ├── start-frontend.bat
│   ├── open-browser.bat
│   ├── start-all.bat
│   ├── check-setup.bat
│   └── reset-database.bat
└── requirements.txt
```

---

## ⚙️ Setup & Run

### Prerequisites
- Python 3.9+
- pip

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
cd SmartQueue-AI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the batch script:
```
scripts\start-backend.bat
```

### 3. Open the Frontend

Open `frontend/index.html` in your browser, or use:
```
scripts\start-frontend.bat
```

> The frontend connects to the backend at `http://localhost:8000`. Configure the API URL in `frontend/js/config.js`.

---

## 🌐 API Docs

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔑 Key Features

| Feature | Description |
|---|---|
| 🤖 AI Wait-Time Prediction | ML model estimates queue wait times dynamically |
| 🏥 Healthcare Queue | OPD, emergency, specialist appointment booking |
| 🏦 Banking Queue | Branch queue management with priority routing |
| 📲 Real-time Updates | WebSocket-based live queue status |
| 🚨 Grievance System | Patient appeals with OTP verification & admin review |
| 📊 Analytics Dashboard | Queue performance, wait-time trends |
| 🔐 JWT Authentication | Secure admin & patient login |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, APScheduler |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI/ML | Scikit-learn (wait-time predictor) |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Real-time | WebSockets |

---

## 📝 Environment Variables

Create a `.env` file in the root (never commit this):

```env
SECRET_KEY=your_jwt_secret_key
DATABASE_URL=sqlite:///./smartqueue.db
TWILIO_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE=+1234567890
```

---

## 👩‍💻 Author

**Jiya Sadaria** — 24AIML054
**Rudra Prajapati** — 24AIML053
