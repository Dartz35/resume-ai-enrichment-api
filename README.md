# Resume AI Enrichment API

A production-ready REST API that uses **Google Gemini 2.0 Flash** to parse resumes, score candidates against job descriptions, rewrite bullet points, and surface trending skills.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 |
| AI Model | Google Gemini 2.0 Flash (`gemini-2.0-flash`) |
| Auth | `X-API-Key` request header |
| Runtime | Python 3.11 + Uvicorn |
| Container | Docker |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A [Google Gemini API key](https://aistudio.google.com/apikey) (free)

### 2. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/resume-ai-enrichment-api.git
cd resume-ai-enrichment-api

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Set the API key

```bash
# macOS / Linux
export GEMINI_API_KEY="your-key-here"

# Windows PowerShell
$env:GEMINI_API_KEY="your-key-here"
```

### 4. Run locally

```bash
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Docker

```bash
# Build
docker build -t resume-ai-api .

# Run
docker run -p 8000:8000 \
  -e GEMINI_API_KEY="your-key-here" \
  resume-ai-api
```

---

## Rate Limits

| Plan | Limit | Price |
|------|-------|-------|
| BASIC | 7 req/day (~200/month) | Free |
| PRO | 500 req/day (~15,000/month) | $9.99/mo |
| ULTRA | 2,000 req/day (~60,000/month) | $29.99/mo |
| MEGA | 10,000 req/day (~300,000/month) | $99.99/mo |

Exceeding the limit returns HTTP **429**.

---

## Endpoints

### `GET /health`

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "version": "1.0.0"}
```

---

### `POST /resume/parse`

Parse a resume into structured fields.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | ✓ or `file_url` | Raw resume text |
| `file_url` | string | ✓ or `text` | Publicly accessible plain-text URL |
| `language` | string | No | ISO language code, default `"en"` |

```bash
curl -X POST http://localhost:8000/resume/parse \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-key" \
  -d '{
    "text": "Jane Doe\njane@example.com\nSoftware Engineer at Acme (2020-2023)\nSkills: Python, Docker, PostgreSQL"
  }'
```

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": null,
  "skills": ["Python", "Docker", "PostgreSQL"],
  "experience_years": 3,
  "experience": [{"company": "Acme", "title": "Software Engineer", "duration": "2020-2023"}],
  "education": [],
  "languages": ["English"]
}
```

---

### `POST /resume/score`

Score a resume against a job description.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `resume_text` | string | ✓ | |
| `job_description` | string | ✓ | |
| `weights` | object | No | `{skills, experience, education}` — must sum to 1.0 |

```bash
curl -X POST http://localhost:8000/resume/score \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-key" \
  -d '{
    "resume_text": "Jane Doe — 5 years Python, Django, PostgreSQL",
    "job_description": "Senior Python engineer with FastAPI, Docker, Kubernetes."
  }'
```

```json
{
  "overall_score": 62,
  "skill_match": 70,
  "experience_match": 75,
  "education_match": 30,
  "missing_skills": ["FastAPI", "Docker", "Kubernetes"],
  "verdict": "Solid Python background but missing key infrastructure skills."
}
```

---

### `POST /resume/rewrite`

Rewrite resume bullets with stronger action verbs and metrics.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `bullets` | string[] | ✓ | 1–20 bullets |
| `target_role` | string | ✓ | e.g. `"Senior Backend Engineer"` |
| `tone` | string | ✓ | `"formal"` \| `"concise"` \| `"impact"` |

```bash
curl -X POST http://localhost:8000/resume/rewrite \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-key" \
  -d '{
    "bullets": ["worked on improving the checkout flow"],
    "target_role": "Senior Product Engineer",
    "tone": "impact"
  }'
```

```json
{
  "rewritten_bullets": [
    "Reduced cart abandonment 18% by redesigning checkout UX flow."
  ]
}
```

---

### `GET /resume/skills/trending`

Return trending skills for a category and region.

| Param | Required | Default | Example |
|-------|----------|---------|---------|
| `category` | ✓ | — | `backend`, `devops`, `data science`, `mobile` |
| `region` | No | `US` | `US`, `GB`, `CA` |

```bash
curl "http://localhost:8000/resume/skills/trending?category=devops&region=US" \
  -H "X-API-Key: my-key"
```

```json
{
  "category": "devops",
  "top_skills": ["Kubernetes", "Terraform", "Docker", "AWS", "Helm", "ArgoCD", "Prometheus", "GitHub Actions", "Ansible", "Datadog"],
  "rising": ["Platform Engineering", "eBPF", "OpenTelemetry", "Crossplane", "Backstage"]
}
```

---

## Error Responses

| HTTP | When |
|------|------|
| 400 | Invalid `file_url` (unreachable) |
| 415 | PDF URL provided (not supported) |
| 422 | Validation failure or AI parse error |
| 429 | Rate limit exceeded |
