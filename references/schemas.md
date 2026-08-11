# Codex Debate packet schemas

The runtime currently validates packet version `1`.

## Task Packet

Required fields: `packet_version`, `task_id`, `role`, `objective`, `relevant_context`, `constraints`, `evidence`, `artifacts`, `required_output`, `acceptance_criteria`, and `privacy`.

Limits are enforced in `scripts/packets.py`: 24,000 total characters, 8 context items, 6,000 characters per context item, 12 evidence items, and 12 artifacts.

## Result Packet

Required fields: `packet_version`, `task_id`, `expert_id`, `status`, `result`, `key_evidence`, `disagreements`, `risks`, `confidence`, `validation`, and `degraded`.

Raw transcripts are intentionally rejected. Use evidence and artifact references instead.

## Discovery Result

Each candidate must contain `model_id`, `label`, `capabilities`, `evidence`, and `access_claims`. Access claims become Provider records only after deterministic validation.

## Browser Observation

The state must be one of `READY`, `AUTH_REQUIRED`, `RATE_LIMITED`, `MODEL_UNAVAILABLE`, `SITE_ERROR`, `AUTOMATION_BLOCKED`, or `UNKNOWN_FAILURE`.
