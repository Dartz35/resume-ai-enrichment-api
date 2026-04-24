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

### Health Check — `GET /health`

Returns `{"status": "ok"}` when the service is running. No authentication required.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "version": "1.0.0"}
```

---

### Parse Resume — `POST /resume/parse`

Extract structured data (name, email, skills, experience, education) from raw resume text or a public URL.

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
    "text": "Alice Smith\nalice@example.com\nSenior Engineer at Acme Corp 2019-2024\nSkills: Python, Go, Kubernetes",
    "language": "en"
  }'
```

```json
{
  "name": "Alice Smith",
  "email": "alice@example.com",
  "phone": null,
  "skills": ["Python", "Go", "Kubernetes"],
  "experience_years": 5,
  "experience": [{"company": "Acme Corp", "title": "Senior Engineer", "duration": "2019-2024"}],
  "education": [],
  "languages": ["English"]
}
```

---

### Score Resume — `POST /resume/score`

Compare a resume against a job description. Returns match scores (0–100) for skills, experience, and education, plus missing skills and a hiring verdict.

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
    "resume_text": "Alice Smith. 5 years Python, Go, Kubernetes.",
    "job_description": "Staff Backend Engineer. 6+ years Python, AWS, distributed systems."
  }'
```

```json
{
  "overall_score": 74,
  "skill_match": 85,
  "experience_match": 70,
  "education_match": 60,
  "missing_skills": ["AWS", "distributed systems"],
  "verdict": "Strong match on technical skills; gaps in cloud infrastructure experience."
}
```

---

### Rewrite Bullets — `POST /resume/rewrite`

Rewrite resume bullet points with stronger action verbs and metrics, tailored to a target role. Returns the same number of bullets in the same order.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `bullets` | string[] | ✓ | 1–20 bullets |
| `target_role` | string | ✓ | e.g. `"Senior Product Engineer"` |
| `tone` | string | ✓ | `"formal"` \| `"concise"` \| `"impact"` |

```bash
curl -X POST http://localhost:8000/resume/rewrite \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-key" \
  -d '{
    "bullets": ["worked on improving the checkout flow", "helped with customer support tickets"],
    "target_role": "Senior Product Engineer",
    "tone": "impact"
  }'
```

```json
{
  "rewritten_bullets": [
    "Reduced cart abandonment 18% by redesigning checkout UX flow.",
    "Resolved 95% of tier-1 support tickets within SLA, improving CSAT scores."
  ]
}
```

---

### Trending Skills — `GET /resume/skills/trending`

Get the top 10 in-demand and 5 rising skills for a job category and region.

| Param | Required | Default | Example values |
|-------|----------|---------|----------------|
| `category` | ✓ | — | `backend`, `frontend`, `devops`, `data science`, `mobile`, `security` |
| `region` | No | `US` | `US`, `GB`, `CA` |

```bash
curl "http://localhost:8000/resume/skills/trending?category=backend&region=US" \
  -H "X-API-Key: my-key"
```

```json
{
  "category": "backend",
  "top_skills": ["Python", "Go", "Kubernetes", "PostgreSQL", "Redis", "Docker", "REST APIs", "GraphQL", "AWS", "Terraform"],
  "rising": ["Rust", "WASM", "eBPF", "OpenTelemetry", "Dagger"]
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
