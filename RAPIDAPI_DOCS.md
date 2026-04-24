# Resume AI Enrichment API — Documentation

## Overview

This API gives you AI-powered resume analysis in four endpoints. All responses are JSON. All endpoints are rate-limited per plan.

Supply your RapidAPI key via the `X-RapidAPI-Key` header — this is added automatically by RapidAPI's code snippets.

---

## Endpoints

### GET /health

Check if the API is running. No authentication required. Use this to verify connectivity before making other calls.

**Response**

```
{"status": "ok", "version": "1.0.0"}
```

---

### POST /resume/parse

Extract structured data from a resume. Supply either `text` (raw string) or `file_url` (public URL to a plain-text file).

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

### POST /resume/score

Compare a resume against a job description and get numeric match scores.

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

### POST /resume/rewrite

Rewrite up to 20 resume bullet points with stronger action verbs and quantifiable metrics.

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

### GET /resume/skills/trending

Get the top 10 in-demand and 5 rising skills for a job category and region.

**Query parameters**

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| category | Yes | — | Job category: backend, frontend, devops, data science, mobile, security |
| region | No | US | ISO country code: US, GB, CA, AU, DE, etc. |

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
