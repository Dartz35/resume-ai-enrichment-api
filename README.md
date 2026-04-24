# Resume AI Enrichment API

A production-ready REST API that uses **Claude** (Anthropic) to parse resumes, score candidates against job descriptions, rewrite bullet points, and surface trending skills.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 |
| LLM | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Auth | `X-API-Key` request header |
| Runtime | Python 3.11 + Uvicorn |
| Container | Docker (single-stage build) |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/keys)

### 2. Clone & install

```bash
git clone <your-repo>
cd resume-ai-api

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Set the API key

**Option A — .env file (recommended for local dev)**

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-api03-...
```

Then load it before starting the server:

```bash
# macOS / Linux
export $(cat .env | xargs)

# Windows PowerShell
Get-Content .env | ForEach-Object { $k,$v = $_ -split '=',2; [System.Environment]::SetEnvironmentVariable($k,$v) }
```

**Option B — shell export**

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."   # macOS / Linux
$env:ANTHROPIC_API_KEY="sk-ant-api03-..."     # Windows PowerShell
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
  -e ANTHROPIC_API_KEY="sk-ant-api03-..." \
  resume-ai-api
```

---

## Rate Limits

| Tier | Header required | Limit |
|------|----------------|-------|
| Free | None | 50 req / day (keyed by IP) |
| Paid | `X-API-Key: <any-non-empty-value>` | 2000 req / day (keyed by key) |

Exceeding the limit returns HTTP **429**.

---

## Endpoints

### `GET /health`

```bash
curl http://localhost:8000/health
```

```json
{"status":"ok","version":"1.0.0"}
```

---

### `POST /resume/parse`

Parse a resume into structured fields.

**Request body**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | ✓ or `file_url` | Raw resume text |
| `file_url` | string | ✓ or `text` | Publicly accessible plain-text URL |
| `language` | string | No | ISO language code, default `"en"` |

```bash
curl -X POST http://localhost:8000/resume/parse \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{
    "text": "Jane Doe\njane@example.com\n\nSoftware Engineer at Acme Corp (2020-2023)\n- Built REST APIs in Python\n- Led team of 4 engineers\n\nB.Sc. Computer Science, McGill University 2019"
  }'
```

**Response**

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": null,
  "skills": ["Python", "REST APIs", "Team Leadership"],
  "experience_years": 3,
  "experience": [
    {"company":"Acme Corp","title":"Software Engineer","duration":"2020-2023","description":"Built REST APIs in Python. Led team of 4 engineers."}
  ],
  "education": [
    {"institution":"McGill University","degree":"B.Sc.","field":"Computer Science","year":"2019"}
  ],
  "languages": ["English"]
}
```

---

### `POST /resume/score`

Score a resume against a job description.

**Request body**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `resume_text` | string | ✓ | |
| `job_description` | string | ✓ | |
| `weights` | object | No | `{skills, experience, education}` — must sum to 1.0, default `0.4/0.4/0.2` |

```bash
curl -X POST http://localhost:8000/resume/score \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{
    "resume_text": "Jane Doe — 5 years Python, Django, PostgreSQL, AWS",
    "job_description": "We need a senior Python engineer with FastAPI, Docker, and Kubernetes experience.",
    "weights": {"skills": 0.5, "experience": 0.3, "education": 0.2}
  }'
```

**Response**

```json
{
  "overall_score": 62,
  "skill_match": 70,
  "experience_match": 75,
  "education_match": 30,
  "missing_skills": ["FastAPI", "Docker", "Kubernetes"],
  "verdict": "Solid Python background but missing key infrastructure skills. Consider for a junior-senior role with upskilling in container orchestration."
}
```

---

### `POST /resume/rewrite`

Rewrite resume bullets with stronger action verbs and metrics.

**Request body**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `bullets` | string[] | ✓ | 1–20 bullets |
| `target_role` | string | ✓ | e.g. `"Senior Backend Engineer"` |
| `tone` | string | ✓ | `"formal"` \| `"concise"` \| `"impact"` |

```bash
curl -X POST http://localhost:8000/resume/rewrite \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{
    "bullets": [
      "worked on improving the checkout flow",
      "helped with customer support tickets",
      "made the dashboard faster"
    ],
    "target_role": "Senior Product Engineer",
    "tone": "impact"
  }'
```

**Response**

```json
{
  "rewritten_bullets": [
    "Redesigned checkout flow, reducing cart abandonment by 18% and increasing conversion rate by 12%.",
    "Resolved 200+ customer support tickets monthly, achieving a 95% satisfaction score.",
    "Optimized dashboard query performance by 40%, cutting average load time from 3.2s to 1.9s."
  ]
}
```

---

### `GET /resume/skills/trending`

Return trending skills for a category and region.

**Query parameters**

| Param | Required | Default | Notes |
|-------|----------|---------|-------|
| `category` | ✓ | — | e.g. `backend`, `data science`, `devops`, `mobile` |
| `region` | No | `US` | ISO country code |

```bash
curl "http://localhost:8000/resume/skills/trending?category=devops&region=CA" \
  -H "X-API-Key: my-secret-key"
```

**Response**

```json
{
  "category": "devops",
  "top_skills": [
    "Kubernetes","Terraform","Docker","GitHub Actions","AWS","Ansible",
    "Prometheus","Helm","ArgoCD","Datadog"
  ],
  "rising": ["Platform Engineering","eBPF","OpenTelemetry","Crossplane","Backstage"]
}
```

---

## Error responses

All errors follow a consistent JSON envelope:

| HTTP | When |
|------|------|
| 400 | Invalid `file_url` (unreachable or wrong type) |
| 415 | Unsupported media type at `file_url` (e.g. PDF) |
| 422 | Input validation failure **or** Claude returned unparseable JSON |
| 429 | Daily rate limit exceeded |
| 500 | Unexpected server error |

---

## RapidAPI Publishing Checklist

- [ ] **API is live and reachable** — deploy to Railway / Render / EC2 / GCP Run and confirm `GET /health` returns 200.
- [ ] **HTTPS only** — ensure your hosting provider terminates TLS (most do by default).
- [ ] **Base URL set in RapidAPI** — paste your deployed base URL (e.g. `https://resume-ai-api.up.railway.app`).
- [ ] **Security scheme configured** — in RapidAPI dashboard set header auth: `X-API-Key` (RapidAPI injects `X-RapidAPI-Key` automatically; add a proxy header mapping or accept `X-RapidAPI-Key` as the key name).
- [ ] **Pricing tiers defined** — map your Free (50/day) and Basic/Pro (2000/day) quotas to RapidAPI subscription plans.
- [ ] **OpenAPI spec imported** — export from `http://your-api/openapi.json` and upload to RapidAPI for auto-generated docs.
- [ ] **Test each endpoint** from the RapidAPI "Test" tab before publishing.
- [ ] **Add a description + logo** in the RapidAPI listing page.
- [ ] **Set rate-limit headers** — optionally expose `X-RateLimit-Remaining` and `X-RateLimit-Limit` response headers for transparency.
- [ ] **Monitor logs** after going live — watch for 422 spikes (Claude JSON parse errors) which indicate prompts need hardening.
