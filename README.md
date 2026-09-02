# SKILLARC — From Training to Livelihood

SKILLARC is a Python-first Smart India Hackathon 2026 concept prototype for **SIH26135**. It follows a synthetic Maharashtra trainee journey from training and certification to placement, employment, retention, wage growth, skill gaps and policy action.

It addresses the limitation of counting only training completions: decision-makers need to know what happens after training. This is not an official government system; all records are synthetic demonstration data.

## Architecture and features

- Python 3.14.5, Flask, Jinja2, SQLite and SQLAlchemy
- 140+ synthetic trainee records across Maharashtra districts, programs, providers, employers and skills
- Database-calculated dashboard, employment funnel, retention, wage progression, district/program/provider comparisons and reports
- Trainee longitudinal profiles, employer verification, follow-up and consent workflows, all persisted to SQLite with audit records
- Local rule-based early-warning and policy intelligence assistant; no API key, internet connection or external AI is used
- Role-specific stakeholder navigation and deterministic local CSS avatars; no real photographs or external avatar service

## Setup and running

Use the included environment where available:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Or create a Python 3.14.5 virtual environment first:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The SQLite database is stored at `instance/skillarc.db` and is seeded automatically.

## Six demo accounts — synthetic environment

Every account uses the same demonstration password: `Skillarc@2026`.

| Team member | Role | Email |
|---|---|---|
| Praveen | State Administrator | `praveen@skillarc.demo` |
| Nidhi | District Officer | `nidhi@skillarc.demo` |
| Tanishq | Training Provider Manager | `tanishq@skillarc.demo` |
| Aditya | Employer Partner | `aditya@skillarc.demo` |
| Srishti | Outcome & Follow-up Officer | `shristi@skillarc.demo` |
| Jayant | Data & Intelligence Officer | `jayant@skillarc.demo` |

The State Administrator has the full platform view. Other roles receive focused navigation: district work, provider performance, employer outcomes, follow-up work, or intelligence/reporting.

## Testing

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Tests run against an isolated in-memory SQLite database. They verify changing KPI values, login/logout, all six named demo accounts, role restrictions, database persistence, filtering, skill-gap answers, early-warning rules, empty data and 404 behavior.

## Project structure

- `app.py` — models, routes, calculations, access control and seed data
- `templates/` — Jinja pages
- `static/css/style.css` — institutional layout; `static/css/avatars.css` — local reusable avatar component
- `tests/test_app.py` — behavior-driven tests

## SIH demonstration flow

1. Start at Home and explain the post-training outcome challenge.
2. Sign in as Praveen and open the dashboard.
3. Open a trainee profile to show the longitudinal journey, assessments and follow-ups.
4. Show employer verification and follow-up updates.
5. Open Skill Gap Intelligence, District Intelligence and Early Warning.
6. Ask Policy Intelligence Assistant: “Which skill gap should we prioritize?”
7. Finish in Reports: SKILLARC follows the journey from training to livelihood.

## Configuration and troubleshooting

Set `SECRET_KEY` outside source for a non-demo environment. `SKILLARC_DATABASE_URI` may point to another SQLite database. To deliberately regenerate the synthetic data, stop the app, delete only `instance/skillarc.db`, then run it again.

Any real deployment would require formal legal, privacy, security and departmental review; official methodology calibration; CSRF protection; verified integrations; and production-grade ownership controls.
