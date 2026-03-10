"""EDON governance for OpenClaw/Clawdbot agents.

Wraps OpenClaw tools and skills so every call is evaluated by EDON
before execution. Works with Clawdbot Telegram bots and any agent
running on the OpenClaw platform.

Quick start::

    from edon_openclaw import EdonOpenClawGuard, governed_skill

    # Wrap a skill function
    @governed_skill(action_type="email.send")
    def send_email(to: str, subject: str, body: str) -> str:
        return smtp_send(to, subject, body)

    # Or wrap all tools in a registry
    governed = EdonOpenClawGuard.wrap_tools(
        tools=my_tools,
        api_key=os.environ["EDON_API_KEY"],
        agent_id="clawdbot-agent",
    )
"""

from edon_openclaw.guard import EdonOpenClawGuard, governed_skill
from edon_openclaw.proxy import EdonClawdProxy

__all__ = ["EdonOpenClawGuard", "governed_skill", "EdonClawdProxy"]
__version__ = "0.1.0"
