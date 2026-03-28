# Pacca PINE

**AI-powered clinical intelligence for modern healthcare.**

Pacca PINE brings agentic AI and next-best-action (NBA) recommendations to [OpenEMR](https://open-emr.org) — surfacing the right clinical action at the right time for providers, patients, and care teams.

Every screen shows what to do next, not just what happened.

## Why

Providers spend too much time navigating EHRs and not enough time with patients. Pacca PINE adds an AI layer that reads the chart, identifies gaps, and recommends actions — so clinicians can focus on care.

## Capabilities

| Capability | Status |
|---|---|
| AI Patient Summary — auto-generated clinical briefing on the patient page | Done |
| Next-Best-Action Engine — contextual recommendations for care gaps, screenings, and follow-ups | Done |
| Care Gap Agent — continuously scans patient populations for missed interventions | Done |
| Chart Summarizer Agent — pre-visit briefing from full patient history | Done |
| Coding Agent — ICD/CPT suggestions from visit notes | Done |
| Modern Clinical UI — lavender theme with contextual highlights | Active |

## Architecture

```
┌─────────────────────────────────┐
│         Pacca PINE UI           │
│   (Bootstrap 4 + PINE Theme)   │
├─────────────────────────────────┤
│        OpenEMR (EHR)            │
│  PHP · MySQL · FHIR · Billing  │
├────────────┬────────────────────┤
│            │  AI Sidecar        │
│  REST API  │  FastAPI · Python  │
│  FHIR R4   │  LLM Agents       │
│            │  NBA Engine        │
└────────────┴────────────────────┘
```

- **EHR Layer:** OpenEMR — scheduling, billing, clinical workflows, FHIR R4
- **AI Sidecar:** FastAPI service with LLM-powered agents for summarization, recommendations, and decision support
- **Frontend:** Custom PINE theme with AI-aware components (summary cards, NBA widgets, inline suggestions)

## Quick Start

```shell
cd docker/development-easy
docker compose up --detach --wait
```

- **App:** http://localhost:8300/
- **Login:** `admin` / `pass`

### Building the Theme

```shell
npm install
npm run gulp-build
```

## For Developers

```shell
composer install --no-dev
npm install
npm run build
composer dump-autoload -o
```

Node.js 22.x required.

## API & Integration

- [REST API](API_README.md)
- [FHIR R4](FHIR_README.md)
- [Docker](DOCKER_README.md)

## License

[GNU GPL v3](LICENSE)

---

Built on [OpenEMR](https://open-emr.org) · Made by [Virtuosity AI](https://github.com/virtuousityai)
