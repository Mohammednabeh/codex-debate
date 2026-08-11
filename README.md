# Codex Debate

Codex Debate is a model-agnostic Codex Skill that analyzes task capabilities, discovers current experts, separates model suitability from provider access, routes work, preserves compact decision packets, and records fallbacks.

## Why it exists

The Current Controller is not necessarily the best planner, specialist, reviewer, or synthesizer for every task. Codex Debate lets the controller delegate selectively while remaining usable when no external provider is available.

## Installation

Copy this directory to:

```text
$CODEX_HOME/skills/codex-debate/
```

The project runtime is created automatically under `.codex-debate/` when used.

## Invocation

Ask Codex to use Codex Debate for a complex task, or invoke the Skill from the Skills picker. The Skill first requests capability analysis, then routes work through fresh registered experts or performs dynamic discovery.

## Runtime commands

```text
python scripts/debate.py --state-dir .codex-debate start --input request.json
python scripts/debate.py --state-dir .codex-debate route SESSION_ID
python scripts/debate.py --state-dir .codex-debate resume SESSION_ID
```

The Skill instructions define the capability-analysis, discovery, browser, readiness, and result handshakes.

## Providers

An Expert is a qualified Model plus a usable Provider. Providers may use API, local, CLI, MCP, Codex-native, or browser/Chrome transport. API credentials are referenced by environment-variable name only. Dynamic discovery is preferred over a fixed catalog.

`examples/browser-provider-config.json` contains a semantic profile for HuggingChat. Its web chat currently requires Hugging Face login before use; the Skill classifies that as `AUTH_REQUIRED` and never handles the credentials.

## Browser authentication

Browser providers are first-class transports. The Skill opens the provider, classifies readiness, opens login only for `AUTH_REQUIRED`, pauses for the inherently human login/MFA/CAPTCHA step, rechecks readiness, submits a compact Task Packet, and returns a structured Browser Observation. Passwords, cookies, and session tokens are never stored.

## Testing

Use the bundled Python runtime or Python 3:

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

The suite covers packets, persistence, routing, discovery registration, API calls against a local HTTP endpoint, browser handshakes, qualification, readiness, CLI invocation, and security validation.

## Security and limitations

External model and web output is untrusted data. It cannot directly change routing or configuration. Non-local API endpoints must use HTTPS; CLI commands come only from local configuration and run without a shell. Browser support depends on available Codex browser/Chrome tooling and provider UI stability. No hosted registry, custom MCP server, or universal provider crawler is included.
