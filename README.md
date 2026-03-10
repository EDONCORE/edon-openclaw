# edon-openclaw · [![PyPI](https://img.shields.io/pypi/v/edon-openclaw)](https://pypi.org/project/edon-openclaw) [![Python](https://img.shields.io/pypi/pyversions/edon-openclaw)](https://pypi.org/project/edon-openclaw) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**EDON governance for OpenClaw/Clawdbot agents.** Every tool call your Telegram bot makes is evaluated by EDON before it executes.

```bash
pip install edon-openclaw
```

---

## Architecture

```
Telegram User
      ↓
Clawdbot / OpenClaw agent
      ↓
edon-openclaw  ← intercepts tool calls
      ↓
EDON Gateway evaluates the action
      ↓
ALLOW  → tool executes
BLOCK  → blocked, reason logged
HUMAN  → escalated for approval
```

---

## Quickstart (2 minutes)

```bash
pip install edon-openclaw
export EDON_API_KEY=your-key
export EDON_AGENT_ID=clawdbot-agent
```

### @governed_skill decorator

The fastest way to add governance to any Clawdbot skill:

```python
from edon_openclaw import governed_skill
from edon.exceptions import EdonBlockedError

@governed_skill(action_type="email.send")
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email — only runs if EDON allows it."""
    return smtp_send(to, subject, body)

@governed_skill(action_type="web.search")
def search_web(query: str) -> str:
    """Search the web — usually ALLOWED."""
    return brave_search(query)

@governed_skill(action_type="shell.exec")
def run_command(command: str) -> str:
    """Run a shell command — BLOCKED by default policy."""
    ...

# Works with async skills too
@governed_skill(action_type="calendar.write")
async def create_event(title: str, date: str) -> str:
    return await calendar_api.create(title, date)
```

---

## Three integration patterns

### 1. `@governed_skill` — per-function

Best for decorating individual skill functions. One line per skill.

```python
from edon_openclaw import governed_skill

@governed_skill(
    action_type="email.send",
    agent_id="my-bot",                  # optional, defaults to EDON_AGENT_ID
    raise_on_block=True,                # raise EdonBlockedError on BLOCK
)
def send_email(to: str, subject: str, body: str) -> str:
    return smtp_send(to, subject, body)
```

### 2. `EdonOpenClawGuard` — tool registries

Best when Clawdbot dispatches from a dict or list of tools.

```python
from edon_openclaw import EdonOpenClawGuard

# Dict registry
TOOLS = {
    "send_email": send_email,
    "search_web": search_web,
    "create_event": create_event,
}

governed = EdonOpenClawGuard.wrap_tools(
    tools=TOOLS,
    api_key=os.environ["EDON_API_KEY"],
    agent_id="clawdbot-agent",
    raise_on_block=False,  # Return error string to LLM instead of raising
)

# Use exactly like before — governance is transparent
result = governed["send_email"](to="user@example.com", subject="Hi", body="...")
```

### 3. `EdonClawdProxy` — gateway-level

Best for governing at the dispatch layer, not per-function.

```python
from edon_openclaw import EdonClawdProxy

proxy = EdonClawdProxy(
    api_key=os.environ["EDON_API_KEY"],
    agent_id="clawdbot-agent",
)

def dispatch(tool_name: str, **kwargs) -> str:
    tool_fn = TOOLS[tool_name]
    return proxy.execute(
        action_type=f"tool.{tool_name}",
        payload=kwargs,
        fn=tool_fn,
        fn_kwargs=kwargs,
    )

# Check without executing
verdict = proxy.check("tool.send_email", {"to": "user@example.com"})
print(verdict["decision"])  # "ALLOW" or "BLOCK"
```

---

## Handling blocked actions

```python
from edon.exceptions import EdonBlockedError, EdonEscalatedError

try:
    send_email(to="all@company.com", subject="Blast", body="...")
except EdonBlockedError as e:
    print(f"Blocked: {e.reason}")
    print(f"Code:    {e.reason_code}")    # e.g. "OUT_OF_SCOPE"
    print(f"Audit:   {e.action_id}")      # trace the decision
except EdonEscalatedError as e:
    print(f"Needs human approval: {e.question}")
    # Route e.question to your human-in-the-loop queue
```

---

## Environment variables

```bash
EDON_API_KEY=your-key          # required
EDON_BASE_URL=https://...      # optional: self-hosted gateway URL
EDON_AGENT_ID=clawdbot-agent   # optional: default agent identifier
```

---

## Self-hosting

Point at your own EDON gateway:

```python
@governed_skill(
    action_type="email.send",
    api_key="your-token",
    base_url="http://localhost:8000",
)
def send_email(...):
    ...
```

---

## Links

- **Core SDK**: [github.com/EDONCORE/edon-python](https://github.com/EDONCORE/edon-python)
- **Console**: [edoncore.com/console](https://edoncore.com/console)
- **Docs**: [docs.edoncore.com](https://docs.edoncore.com)
- **Issues**: [github.com/EDONCORE/edon-openclaw/issues](https://github.com/EDONCORE/edon-openclaw/issues)

---

## License

MIT © EDON Core