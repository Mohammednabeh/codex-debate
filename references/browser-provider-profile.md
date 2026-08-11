# Browser provider profile

Profiles are semantic hints for the generic browser workflow. They are not a large selector framework.

```json
{
  "provider_id": "discovered-provider",
  "home_url": "https://example.com/chat",
  "login_url": "https://example.com/login",
  "browser_target": "browser_or_chrome",
  "chat_ready_signals": ["new chat", "message input"],
  "auth_required_signals": ["sign in"],
  "rate_limit_signals": ["limit reached"],
  "model_unavailable_signals": ["model unavailable"],
  "completion_signals": ["stop generating"]
}
```

Use accessible labels, visible text, and rendered state first. Add provider-specific hints only when generic interaction is insufficient. If the page changes, classify the failure and use fallback rather than guessing.
