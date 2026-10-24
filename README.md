# MediConnect

**AI-Assisted Healthcare & Telemedicine Platform**

MediConnect is a Django-based healthcare management platform designed to connect patients with healthcare professionals through a centralized digital system.

The project aims to simplify appointment scheduling, improve access to medical services, and explore how artificial intelligence can assist healthcare workflows.

## Project Overview

MediConnect brings together patient management, doctor discovery, appointment scheduling, and telemedicine services in a single web application.

The platform is being developed with a modular architecture to support future integrations, including AI-assisted symptom triage and remote consultations.

## Core Features

### Patient Services
- Patient registration and profile management
- Doctor discovery and specialty-based search
- Appointment booking and scheduling
- Access to medical records and prescriptions
- Patient reviews and follow-up management

### Healthcare Professional Services
- Doctor profiles and specialty management
- Appointment and availability management
- Patient consultation history
- Prescription and medical record management

### Administration
- Administrative dashboard
- Patient and healthcare professional management
- Doctor verification and approval workflows
- Platform activity monitoring

### Planned AI & Telemedicine Features
- AI-assisted symptom triage
- Machine learning integration using scikit-learn
- Video consultations using Jitsi Meet
- Intelligent healthcare service recommendations

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, Django |
| API | Django REST Framework |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Database | SQLite (development) |
| AI / ML (planned) | scikit-learn |
| Telemedicine (planned) | Jitsi Meet |
| Version Control | Git, GitHub |

## Project Architecture

The application follows Django's Model-View-Template (MVT) architecture, with a modular design separating core healthcare functionalities.

Future development will introduce REST APIs, machine learning services, and telemedicine integrations.

## Development Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install the project dependencies.
4. Apply database migrations.
5. Start the Django development server.

Example commands:

```bash
git clone https://github.com/zied3332/MediConnect.git
cd MediConnect

python -m venv .venv
```

Activate the environment on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies and start the server:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The development server will be available at:

`http://127.0.0.1:8000/`

## Development Roadmap

- [ ] Complete authentication and role-based access control
- [ ] Implement patient and doctor profile management
- [ ] Develop appointment scheduling workflows
- [ ] Build administration and reporting features
- [ ] Integrate telemedicine functionality
- [ ] Develop and evaluate AI-assisted symptom triage
- [ ] Add automated testing and deployment configuration

## Project Status

**Early Development**

MediConnect is currently under active development. Features listed

---

## Module: Appointments + Notifications

Two Django apps: `appointments` (booking, status workflow, AI no-show risk) and
`notifications` (in-app notifications, reusable by every module).

### What it does

**Patients**
- Book in 3 steps: specialty → approved doctor → free 30-minute slot (radio buttons grouped by day), consultation type (in-office / video) and reason. The request starts as *pending* and the doctor is notified.
- *My appointments* with **Upcoming** / **Past & cancelled** tabs and status badges.
- Detail page, **reschedule** (pick a new free slot, goes back to *pending*) and **cancel** (confirmation page, only more than 24h before).

**Doctors** (approved only)
- Appointment list with filters (period, status, day) and an **AI no-show risk badge**: Low < 30 %, Medium < 60 %, High, with the percentage and the tooltip "AI estimate, you decide".
- Confirm / Reject (optional reason) / Completed / No-show buttons. Each change notifies the patient.

**Admins**
- All appointments with filters (doctor, patient, status, day) and delete.
- *AI model* page: metrics of the trained model (classification report, confusion matrix, ROC-AUC, inference time, compared models).

**Notifications**
- Bell with unread count in the dashboard topbar, list page (newest first, paginated), open (marks read), mark all read, delete.
- Other modules must create notifications only through the service:

  ```python
  from notifications.services import notify
  notify(user, "Your prescription is ready.", "system", link="/prescriptions/4/")
  ```
  Types: `appointment`, `reminder`, `system`.

**Business rules** (`appointments/models.py` `clean()` and `appointments/services.py`)
- The slot must be in the future, inside one of the doctor's free weekly `Availability` blocks, and must not overlap another active appointment of the doctor or of the patient. A database `UniqueConstraint` also prevents two active appointments for the same doctor at the same start time.
- `get_free_slots(doctor, days=14)` = availability − taken appointments − past times.
- Status changes go through `confirm_appointment`, `reject_appointment`, `cancel_appointment`, `complete_appointment`, `mark_no_show`: they check who is allowed and notify the other side.

### AI: no-show risk (scikit-learn)

- Dataset: Kaggle **"Medical Appointment No Shows"** (`KaggleV2-May-2016.csv`, about 110,000 appointments). It is not committed: download it from <https://www.kaggle.com/datasets/joniarroba/noshowappointments>, rename it to `noshow.csv` and put it in `appointments/ml/data/`.
- Features available both in the dataset and in our model: `lead_days`, `weekday`, `prior_appointments`, `prior_no_shows` (only appointments that happened before the booking day, so the model never sees the future) and `reminder_sent`.
- `python manage.py train_noshow_model` does a stratified 80/20 split and compares `LogisticRegression(class_weight="balanced")` with a `RandomForest`. It keeps the best F1 on the no-show class, saves `appointments/ml/model.joblib` and `appointments/ml/metrics.json`, and prints the metrics.
- After each booking, `compute_no_show_risk` runs in Celery (`transaction.on_commit`). If the model is missing or fails, the error is logged and the doctor sees "Risk not available" (with a Retry button). The page never crashes.
- `send_reminders` runs every hour (Celery beat). It sends a reminder 24h before each confirmed appointment, plus an extra one 48h before when the risk is High.
- The model only assists: it never confirms, rejects or cancels anything. The doctor decides.

### Install on Windows (cmd)

```bat
cd MediConnect
python --version
:: Python 3.12+ is required by Django 6.1

:: 1. Database (PostgreSQL 18)
set PGPASSWORD=your-postgres-password
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE mediconnect;"
set PGPASSWORD=

:: 2. Virtual environment and packages
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

:: 3. Settings: copy the example, then edit DB_PASSWORD and SECRET_KEY
copy .env.example .env

:: 4. Database tables, demo data, tests
python manage.py migrate
python manage.py seed_appointments
python manage.py test
python manage.py runserver
```

Open <http://127.0.0.1:8000/accounts/login/>. `seed_appointments` prints the demo accounts
(password `Demo1234!` for all of them):

| Role | Email |
|---|---|
| Admin | admin@mediconnect.demo |
| Doctor (Cardiology) | amara.diallo@mediconnect.demo |
| Doctor (Dermatology) | lucas.petit@mediconnect.demo |
| Doctor (General Medicine) | sofia.benali@mediconnect.demo |
| Patient | marie.dupont@mediconnect.demo |
| Patient | jean.martin@mediconnect.demo |
| Patient | sophie.bernard@mediconnect.demo |

The command can be run again at any time: it resets the demo appointments.

### Settings (`.env`)

| Variable | Example | Meaning |
|---|---|---|
| `SECRET_KEY` | long random string | Django secret key |
| `DEBUG` | `True` | development mode |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | `mediconnect`, `postgres`, …, `localhost`, `5432` | PostgreSQL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis used by Celery |
| `CELERY_TASK_ALWAYS_EAGER` | `True` | `True`: tasks run directly in the web process, no Redis needed (simplest on Windows) |

`.env` is git-ignored. Never commit it.

### Celery and Redis (optional, for real background tasks)

1. Start Redis, either with Docker: `docker run -p 6379:6379 redis`, or by installing
   [Memurai](https://www.memurai.com/) (a Redis-compatible server for Windows).
2. Set `CELERY_TASK_ALWAYS_EAGER=False` in `.env`.
3. Open two more terminals (with `venv\Scripts\activate`):

```bat
celery -A config worker --pool=solo -l info
celery -A config beat -l info
```

`--pool=solo` is required on Windows. If Redis is down while eager mode is off, bookings still
work: the risk is just marked "not available" and can be retried from the doctor page.

### Train the model

```bat
:: after putting noshow.csv in appointments\ml\data\
python manage.py train_noshow_model
:: options: --data path\to\file.csv  --rf-trees 200  --seed 42
```

A trained `model.joblib` and its `metrics.json` are committed, so the demo works without the dataset.

### Tests and coverage

```bat
python manage.py test
coverage run manage.py test
coverage report
```

Tests live in `appointments/tests/` and `notifications/tests.py`. They cover validation rules,
free slots, every status change and its notification, permissions (404 / 403), Celery tasks,
the predictor with a tiny trained model, the training command and the demo seed.
