# Singularium-Assignment

# Task Analyzer — Smart Task Prioritization (Intern Assignment)

## Overview
This project implements a Smart Task Analyzer (Django backend + simple frontend).
It scores tasks using urgency, importance, effort, and dependency impact and exposes:
- `POST /api/tasks/analyze/` — analyze array of tasks, return sorted tasks with scores
- `GET /api/tasks/suggest/` — returns top-N suggestions (allows strategy selection)

## Quick start (local)
1. Create virtualenv and install:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
API
POST /api/tasks/analyze/

Body:

{
  "tasks": [
     {"id":"1","title":"Fix bug","due_date":"2025-11-30","estimated_hours":3,"importance":8,"dependencies":[]}
  ],
  "weights": {"urgency":0.3,"importance":0.4,"effort":0.2,"dependencies":0.1}
}


Response: { "tasks": [...sorted...], "meta": {...} }

GET /api/tasks/suggest/

Accepts tasks in body (JSON) or URL param tasks (JSON string), strategy param (smart|fastest|highimpact|deadline), top param.
Returns top suggestions with suggestion_reason.

Tests

Run:

cd backend
source .venv/bin/activate
python manage.py test tasks

Notes

The scoring algorithm is in tasks/scoring.py.

Circular dependencies are detected and returned in meta -> cycles.

Weights are configurable in the request.


---

## 5) Important implementation details & how it addresses assignment concerns

- **Past-due tasks**: these receive urgency boost and extra bonus proportional to days overdue (capped). Appear higher in ranking.
- **Missing/invalid data**: serializer validates fields; API returns helpful error messages. For missing due_date we treat urgency as neutral (0.5).
- **Circular dependencies**: detected via `detect_cycles`; cycles are returned in API meta. Algorithm still scores tasks but you should surface cycles to users to fix dependencies.
- **Configurable algorithm**: via `weights` in POST to analyze or via `strategy` param to suggest endpoint.
- **Balancing priorities**: default "smart" weights balance urgency & importance equally; other strategies concentrate weight on effort or deadline.
- **Edge cases**: normalized scales avoid division by zero; horizon chosen conservatively; capping bonuses to avoid runaway scores.
- **Frontend**: shows score, explanation, and visual indicators. Basic validation & error handling present.

---

## 6) Example payload you can paste in frontend textarea

```json
[
  {"id":"1","title":"Fix login bug","due_date":"2025-11-30","estimated_hours":3,"importance":8,"dependencies":[]},
  {"id":"2","title":"Create pricing page","due_date":"2025-12-10","estimated_hours":12,"importance":9,"dependencies":["1"]},
  {"id":"3","title":"Update docs","due_date":null,"estimated_hours":2,"importance":4,"dependencies":[]},
  {"id":"4","title":"Hotfix payment","due_date":"2025-11-20","estimated_hours":1,"importance":10,"dependencies":[]}
]

7) Tests included

tasks/tests.py contains at least 3 test cases:

basic scoring validity

cycle detection

analyze API endpoint

Run tests with python manage.py test tasks.
