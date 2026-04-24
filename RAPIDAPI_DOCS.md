# Resume AI Enrichment API — Documentation

## Overview

This API gives you AI-powered resume analysis in five endpoints. All responses are JSON. All endpoints are rate-limited per plan.

Supply your RapidAPI key via the `X-RapidAPI-Key` header — this is added automatically by RapidAPI's code snippets.

---

## Endpoints

### 1. Health Check — GET /health

Returns `{"status": "ok"}` when the service is running. No authentication required.

No headers, query params, or body needed.

**Response**

```
{"status": "ok", "version": "1.0.0"}
```

---

### 2. Parse Resume — POST /resume/parse

Extract structured data (name, email, skills, experience, education) from raw resume text or a public URL.

**Request body**

```
{
  "text": "Alice Smith\nalice@example.com\nSenior Engineer at Acme Corp 2019-2024\nSkills: Python, Go, Kubernetes",
  "language": "en"
}
```

**Request fields**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| text | string | one of text/file_url | Raw resume text |
| file_url | string | one of text/file_url | Public URL to a plain-text resume |
| language | string | No | Language hint, default "en" |

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| name | string or null | Candidate full name |
| email | string or null | Email address |
| phone | string or null | Phone number |
| skills | array | List of technical and soft skills |
| experience_years | number or null | Estimated total years of experience |
| experience | array | List of {company, title, duration, description} |
| education | array | List of {institution, degree, field, year} |
| languages | array | Spoken/written languages |

---

### 3. Score Resume — POST /resume/score

Compare a resume against a job description. Returns match scores (0–100) for skills, experience, and education, plus missing skills and a hiring verdict.

**Request body**

```
{
  "resume_text": "Alice Smith. 5 years Python, Go, Kubernetes.",
  "job_description": "Staff Backend Engineer. 6+ years Python, AWS, distributed systems."
}
```

**Request fields**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| resume_text | string | Yes | Full plain-text resume |
| job_description | string | Yes | Full plain-text job description |
| weights | object | No | {skills, experience, education} — must sum to 1.0. Default: 0.4 / 0.4 / 0.2 |

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| overall_score | number | Weighted composite score (0–100) |
| skill_match | number | Skill overlap score (0–100) |
| experience_match | number | Experience alignment score (0–100) |
| education_match | number | Education alignment score (0–100) |
| missing_skills | array | Skills in JD not found in resume |
| verdict | string | 1–2 sentence hiring recommendation |

---

### 4. Rewrite Bullets — POST /resume/rewrite

Rewrite resume bullet points with stronger action verbs and metrics, tailored to a target role. Returns the same number of bullets in the same order.

**Request body**

```
{
  "bullets": ["worked on improving the checkout flow", "helped with customer support tickets"],
  "target_role": "Senior Product Engineer",
  "tone": "impact"
}
```

**Request fields**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| bullets | array | Yes | 1 to 20 bullet point strings |
| target_role | string | Yes | Job title being targeted |
| tone | string | Yes | "formal", "concise", or "impact" |

**Tone options**

| Tone | Description |
|------|-------------|
| formal | Polished, professional language |
| concise | Short and punchy, max ~12 words per bullet |
| impact | Leads with achievement, includes metrics, uses power verbs |

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| rewritten_bullets | array | Rewritten bullets in same order and count as input |

---

### 5. Trending Skills — GET /resume/skills/trending

Get the top 10 in-demand and 5 rising skills for a job category and region.

**Query parameters**

| Name | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| category | STRING | backend | Yes | Job category e.g. backend, frontend, devops, data science, mobile, security |
| region | STRING | US | No | ISO country code e.g. US, GB, CA |

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| category | string | Normalised category name |
| top_skills | array | Top 10 most in-demand skills |
| rising | array | 5 rapidly growing skills to watch |

---

## Error Codes

| Code | Error | Description |
|------|-------|-------------|
| 400 | — | Could not fetch the provided file_url |
| 415 | — | PDF URL provided — extract text first |
| 422 | claude_parse_error | Invalid request body or AI returned malformed response |
| 429 | rate_limit_exceeded | Daily quota exceeded for your plan |

**429 response body example**

```
{
  "detail": {
    "error": "rate_limit_exceeded",
    "tier": "basic",
    "limit": 7,
    "count": 8
  }
}
```

---

## Pricing Plans

| Plan | Requests/day | Requests/month | Price |
|------|-------------|----------------|-------|
| BASIC | 7 | 200 | Free |
| PRO | 500 | 15,000 | $9.99/mo |
| ULTRA | 2,000 | 60,000 | $29.99/mo |
| MEGA | 10,000 | 300,000 | $99.99/mo |
