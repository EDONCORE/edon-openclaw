"""
EDON + OpenClaw/Clawdbot — governed agent skills.

This example shows how to add EDON governance to Clawdbot skills,
so every tool call your Telegram bot makes is evaluated before it runs.

Setup:
    1. pip install edon-openclaw
    2. export EDON_API_KEY=your-key
    3. export EDON_AGENT_ID=clawdbot-agent

The skills below integrate into your Clawdbot skill system — replace the
stub implementations with real ones.
"""

import os
from edon_openclaw import governed_skill, EdonOpenClawGuard, EdonClawdProxy
from edon.exceptions import EdonBlockedError, EdonEscalatedError


# ── Pattern 1: @governed_skill decorator ─────────────────────────────────────
# Cleanest approach for individual skills — one line to add governance.

@governed_skill(action_type="email.send")
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email. Only executes if EDON allows it."""
    # Replace with real email implementation
    print(f"  Sending email to {to}: {subject}")
    return f"Email sent to {to}"


@governed_skill(action_type="web.search")
def search_web(query: str) -> str:
    """Search the web. Usually ALLOWED by default policy."""
    return f"Search results for: {query}"


@governed_skill(action_type="shell.exec")
def run_command(command: str) -> str:
    """Run a shell command. Likely BLOCKED by default policy."""
    import subprocess
    return subprocess.check_output(command, shell=True).decode()


@governed_skill(action_type="database.delete")
def delete_records(table: str, condition: str) -> str:
    """Delete DB records. BLOCKED by default policy."""
    return f"Deleted from {table}"


# ── Pattern 2: EdonOpenClawGuard for tool registries ─────────────────────────
# If Clawdbot uses a dict registry to dispatch tools, wrap the whole registry.

TOOLS = {
    "send_email": send_email,
    "search_web": search_web,
}

governed_tools = EdonOpenClawGuard.wrap_tools(
    tools=TOOLS,
    api_key=os.environ.get("EDON_API_KEY"),
    agent_id=os.environ.get("EDON_AGENT_ID", "clawdbot-agent"),
    raise_on_block=False,  # Return error string instead of raising
)


# ── Pattern 3: EdonClawdProxy for gateway-level governance ───────────────────
# Use when you want to govern at the dispatch level, not per-function.

proxy = EdonClawdProxy(
    api_key=os.environ.get("EDON_API_KEY"),
    agent_id=os.environ.get("EDON_AGENT_ID", "clawdbot-agent"),
    raise_on_block=False,
)


def dispatch_tool(tool_name: str, **kwargs) -> str:
    """Dispatch a tool call through EDON before execution."""
    tool_fn = TOOLS.get(tool_name)
    if not tool_fn:
        return f"Unknown tool: {tool_name}"

    return proxy.execute(
        action_type=f"tool.{tool_name}",
        payload=kwargs,
        fn=tool_fn,
        fn_kwargs=kwargs,
    )


# ── Demo ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n--- EDON + OpenClaw Governance Demo ---\n")

    # Test with @governed_skill decorator
    print("Pattern 1: @governed_skill")

    try:
        print("  web.search...")
        result = search_web("latest AI news")
        print(f"  ALLOWED: {result}\n")
    except EdonBlockedError as e:
        print(f"  BLOCKED: {e.reason}\n")

    try:
        print("  shell.exec...")
        result = run_command("ls /tmp")
        print(f"  ALLOWED: {result}\n")
    except EdonBlockedError as e:
        print(f"  BLOCKED ({e.reason_code}): {e.reason}\n")

    # Test with gateway proxy
    print("Pattern 3: EdonClawdProxy")
    result = dispatch_tool("send_email", to="team@company.com", subject="Update", body="...")
    print(f"  send_email: {result}\n")

    print("All decisions logged to EDON audit trail.")
    print("View at: https://edoncore.com/console")
