"""
Pacca PINE AI Sidecar — Patient Summary Service

FastAPI service that fetches patient data from OpenEMR's FHIR R4 API,
sends it to an LLM via OpenRouter, and returns a structured clinical summary.
"""

import asyncio
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Pacca PINE AI Sidecar", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8300",
        "https://localhost:9300",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Configuration -----------------------------------------------------------

FHIR_BASE = os.environ.get("FHIR_BASE_URL", "https://openemr:443/apis/default/fhir")
OAUTH_TOKEN_URL = os.environ.get("OAUTH_TOKEN_URL", "https://openemr:443/oauth2/default/token")
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")
OAUTH_USERNAME = os.environ.get("OAUTH_USERNAME", "admin")
OAUTH_PASSWORD = os.environ.get("OAUTH_PASSWORD", "pass")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Token cache -------------------------------------------------------------

_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


async def get_fhir_token(client: httpx.AsyncClient) -> str:
    """Get a cached or fresh OAuth2 access token for the FHIR API."""
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    resp = await client.post(
        OAUTH_TOKEN_URL,
        data={
            "grant_type": "password",
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
            "username": OAUTH_USERNAME,
            "password": OAUTH_PASSWORD,
            "scope": (
                "openid "
                "user/Patient.read "
                "user/Condition.read "
                "user/Observation.read "
                "user/Encounter.read "
                "user/AllergyIntolerance.read "
                "user/MedicationRequest.read"
            ),
            "user_role": "users",
        },
    )
    if resp.status_code != 200:
        raise HTTPException(502, f"OAuth token request failed: {resp.text}")

    body = resp.json()
    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = time.time() + body.get("expires_in", 3600)
    return body["access_token"]


# --- FHIR helpers ------------------------------------------------------------

async def fhir_search(
    client: httpx.AsyncClient, token: str, resource: str, params: dict[str, str]
) -> list[dict]:
    """Search a FHIR resource and return the list of entries."""
    resp = await client.get(
        f"{FHIR_BASE}/{resource}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 200:
        return []
    bundle = resp.json()
    return [e.get("resource", e) for e in bundle.get("entry", [])]


async def fetch_patient_context(client: httpx.AsyncClient, token: str, uuid: str) -> dict:
    """Fetch all relevant FHIR resources for a patient in parallel."""
    patient_resp = client.get(
        f"{FHIR_BASE}/Patient/{uuid}",
        headers={"Authorization": f"Bearer {token}"},
    )

    conditions, observations, encounters, allergies, medications, patient = await asyncio.gather(
        fhir_search(client, token, "Condition", {"patient": uuid}),
        fhir_search(client, token, "Observation", {"patient": uuid, "_count": "20", "_sort": "-date"}),
        fhir_search(client, token, "Encounter", {"patient": uuid, "_count": "10", "_sort": "-date"}),
        fhir_search(client, token, "AllergyIntolerance", {"patient": uuid}),
        fhir_search(client, token, "MedicationRequest", {"patient": uuid}),
        patient_resp,
    )

    patient_data = patient.json() if patient.status_code == 200 else {}

    return {
        "patient": patient_data,
        "conditions": conditions,
        "observations": observations,
        "encounters": encounters,
        "allergies": allergies,
        "medications": medications,
    }


# --- LLM call ----------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a clinical AI assistant for Pacca PINE, an AI-powered EHR platform.
Given a patient's FHIR data, produce a concise clinical summary in JSON format.

Return ONLY valid JSON with these keys:
{
  "synopsis": "2-3 sentence clinical overview of the patient",
  "care_gaps": ["list of identified care gaps or missing screenings"],
  "recent_changes": ["notable recent clinical events or changes"],
  "suggested_actions": ["recommended next-best-actions for the provider"]
}

Be concise, clinically relevant, and actionable. If data is sparse, say so.
Do not fabricate clinical information not present in the data.\
"""


async def call_llm(patient_context: dict) -> dict:
    """Send patient context to OpenRouter LLM and parse the response."""
    user_message = f"Patient FHIR data:\n{_summarize_context(patient_context)}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.3,
                "max_tokens": 2048,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(502, f"LLM request failed: {resp.status_code} {resp.text}")

    resp_json = resp.json()
    choices = resp_json.get("choices", [])
    if not choices:
        raise HTTPException(502, f"LLM returned no choices: {resp_json}")

    content = choices[0].get("message", {}).get("content")
    if not content:
        raise HTTPException(502, f"LLM returned empty content: {resp_json}")

    # Strip markdown fences if present
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    import json
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "synopsis": content,
            "care_gaps": [],
            "recent_changes": [],
            "suggested_actions": [],
        }


def _summarize_context(ctx: dict) -> str:
    """Build a compact text representation of patient data for the LLM."""
    parts = []

    p = ctx.get("patient", {})
    if p:
        name = ""
        names = p.get("name", [])
        if names:
            n = names[0]
            name = f"{' '.join(n.get('given', []))} {n.get('family', '')}"
        parts.append(f"Patient: {name}, DOB: {p.get('birthDate', 'unknown')}, Gender: {p.get('gender', 'unknown')}")

    # Conditions — extract display text
    conditions = ctx.get("conditions", [])
    if conditions:
        names = []
        for c in conditions[:20]:
            code = c.get("code", {})
            text = code.get("text") or (code.get("coding", [{}])[0].get("display") if code.get("coding") else None) or "unknown"
            status = c.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
            names.append(f"{text} ({status})" if status else text)
        parts.append(f"\nConditions: {', '.join(names)}")
    else:
        parts.append("\nConditions: none recorded")

    # Allergies
    allergies = ctx.get("allergies", [])
    if allergies:
        names = []
        for a in allergies[:10]:
            code = a.get("code", {})
            text = code.get("text") or (code.get("coding", [{}])[0].get("display") if code.get("coding") else None) or "unknown"
            names.append(text)
        parts.append(f"Allergies: {', '.join(names)}")
    else:
        parts.append("Allergies: none recorded")

    # Medications
    meds = ctx.get("medications", [])
    if meds:
        names = []
        for m in meds[:15]:
            med = m.get("medicationCodeableConcept", {})
            text = med.get("text") or (med.get("coding", [{}])[0].get("display") if med.get("coding") else None) or "unknown"
            dosage = m.get("dosageInstruction", [])
            dose_text = ""
            if dosage and isinstance(dosage[0], dict):
                dose_text = dosage[0].get("text", "")
            names.append(f"{text} {dose_text}".strip())
        parts.append(f"Medications: {', '.join(names)}")
    else:
        parts.append("Medications: none recorded")

    # Observations — compact
    obs = ctx.get("observations", [])
    if obs:
        parts.append(f"\nRecent Observations ({len(obs)}):")
        for o in obs[:15]:
            code = o.get("code", {})
            text = code.get("text") or (code.get("coding", [{}])[0].get("display") if code.get("coding") else None) or "unknown"
            val = o.get("valueQuantity", {})
            val_str = f"{val.get('value', '')} {val.get('unit', '')}".strip() if val else o.get("valueString", "")
            date = o.get("effectiveDateTime", "")[:10]
            parts.append(f"  - {text}: {val_str} ({date})")
    else:
        parts.append("\nObservations: none recorded")

    # Encounters — compact
    encounters = ctx.get("encounters", [])
    if encounters:
        parts.append(f"\nRecent Encounters ({len(encounters)}):")
        for e in encounters[:10]:
            etype = e.get("class", {})
            type_display = etype.get("display") or etype.get("code", "unknown")
            period = e.get("period", {})
            start = period.get("start", "")[:10]
            reason = ""
            reason_codes = e.get("reasonCode", [])
            if reason_codes:
                reason = reason_codes[0].get("text", "")
            parts.append(f"  - {type_display} on {start}" + (f": {reason}" if reason else ""))
    else:
        parts.append("\nEncounters: none recorded")

    return "\n".join(parts)


# --- API endpoints -----------------------------------------------------------

class SummaryResponse(BaseModel):
    synopsis: str
    care_gaps: list[str]
    recent_changes: list[str]
    suggested_actions: list[str]


@app.get("/api/summary/{patient_uuid}", response_model=SummaryResponse)
async def get_patient_summary(patient_uuid: str):
    """Generate an AI-powered clinical summary for a patient."""
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        token = await get_fhir_token(client)
        context = await fetch_patient_context(client, token, patient_uuid)

    if not context.get("patient"):
        raise HTTPException(404, "Patient not found")

    summary = await call_llm(context)
    return SummaryResponse(**summary)


class CodingSuggestion(BaseModel):
    code: str
    code_type: str  # "ICD10" or "CPT4"
    description: str
    confidence: str  # "high", "medium", "low"


class CodingResponse(BaseModel):
    soap_note: dict
    suggested_icd10: list[CodingSuggestion]
    suggested_cpt: list[CodingSuggestion]


CODING_SYSTEM_PROMPT = """\
Medical coding assistant. Given SOAP note, return JSON only:
{"icd10":[{"code":"X00.0","description":"desc","confidence":"high"}],"cpt":[{"code":"99214","description":"desc","confidence":"high"}]}
2-5 ICD-10 codes, 1-3 CPT E&M codes (99211-99215 established, 99202-99205 new). Valid codes only. No markdown.\
"""


@app.get("/api/coding/{encounter_id}", response_model=CodingResponse)
async def get_coding_suggestions(encounter_id: int):
    """Suggest ICD-10 and CPT codes for an encounter based on SOAP notes."""
    import json as json_mod

    # Fetch SOAP note and patient conditions from the database via FHIR isn't ideal here,
    # so we'll query the OpenEMR database directly through a helper endpoint.
    # For now, we use the FHIR API to get patient context and a direct DB query for SOAP.

    # First, get the encounter's SOAP note and patient info via internal API
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        token = await get_fhir_token(client)

        # Get encounter to find patient
        enc_resp = await client.get(
            f"{FHIR_BASE}/Encounter/{encounter_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    # If we can't get the encounter via FHIR by encounter_id, we need a different approach.
    # The sidecar will accept SOAP note content and conditions as POST body instead.
    raise HTTPException(501, "Use POST /api/coding endpoint instead")


class CodingRequest(BaseModel):
    pid: int
    encounter: int
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    conditions: str = ""


@app.post("/api/coding", response_model=CodingResponse)
async def suggest_codes(req: CodingRequest):
    """Suggest ICD-10 and CPT codes from SOAP note content."""
    subjective = req.subjective
    objective = req.objective
    assessment = req.assessment
    plan = req.plan
    conditions = req.conditions

    soap = {
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan,
    }

    soap_text = f"S: {subjective}\nO: {objective}\nA: {assessment}\nP: {plan}"
    if not soap_text.strip("SOAP: \n"):
        raise HTTPException(400, "No SOAP note content provided")

    user_msg = f"SOAP Note:\n{soap_text}"
    if conditions:
        user_msg += f"\n\nActive conditions: {conditions}"

    # Retry up to 3 times — free LLM tier is flaky
    content = ""
    for attempt in range(3):
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": CODING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 2048,
                },
            )

        if resp.status_code != 200:
            if attempt < 2:
                await asyncio.sleep(2)
                continue
            raise HTTPException(502, f"LLM request failed: {resp.status_code}")

        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if content:
            break
        if attempt < 2:
            await asyncio.sleep(2)

    if not content:
        raise HTTPException(502, "LLM returned empty content after retries")

    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    import json as json_mod
    try:
        data = json_mod.loads(text)
    except json_mod.JSONDecodeError:
        # Try to recover
        import re
        data = {"icd10": [], "cpt": []}
        for match in re.finditer(r'"code"\s*:\s*"([^"]+)".*?"description"\s*:\s*"([^"]+)"', text):
            code, desc = match.groups()
            if code[0].isdigit() and len(code) == 5:
                data["cpt"].append({"code": code, "description": desc, "confidence": "medium"})
            else:
                data["icd10"].append({"code": code, "description": desc, "confidence": "medium"})

    icd10_suggestions = [
        CodingSuggestion(
            code=item.get("code", ""),
            code_type="ICD10",
            description=item.get("description", ""),
            confidence=item.get("confidence", "medium"),
        )
        for item in data.get("icd10", [])
        if item.get("code")
    ]

    cpt_suggestions = [
        CodingSuggestion(
            code=item.get("code", ""),
            code_type="CPT4",
            description=item.get("description", ""),
            confidence=item.get("confidence", "medium"),
        )
        for item in data.get("cpt", [])
        if item.get("code")
    ]

    return CodingResponse(
        soap_note=soap,
        suggested_icd10=icd10_suggestions,
        suggested_cpt=cpt_suggestions,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pacca-pine-ai-sidecar"}
