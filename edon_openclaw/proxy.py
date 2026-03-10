"""EdonClawdProxy — proxies OpenClaw gateway requests through EDON governance.

This module lets you run EDON governance as a transparent proxy between
Clawdbot's internal gateway (port 18789) and the actual tool execution.
Every tool call Clawdbot makes is evaluated by EDON before it runs.

Architecture::

    Telegram User
         ↓
    Clawdbot (port 18789)
         ↓
    EdonClawdProxy          ← this module
         ↓
    EDON Gateway (/v1/action)
         ↓
    ALLOW → tool executes
    BLOCK → blocked, reason returned
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from edon import EdonClient
from edon.exceptions import EdonBlockedError, EdonEscalatedError


class EdonClawdProxy:
    """Proxy that evaluates OpenClaw tool calls through EDON before execution.

    This is useful when you want governance at the gateway level rather than
    wrapping individual tool functions. It acts as middleware: your tool
    executes normally, but EDON is consulted first.

    Usage::

        from edon_openclaw import EdonClawdProxy

        proxy = EdonClawdProxy(
            api_key=os.environ["EDON_API_KEY"],
            agent_id="clawdbot-agent",
        )

        # In your tool dispatch loop:
        result = proxy.execute(
            action_type="tool.send_email",
            payload={"to": "user@example.com", "subject": "Hello"},
            fn=send_email,
            fn_kwargs={"to": "user@example.com", "subject": "Hello", "body": "..."},
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        intent_id: Optional[str] = None,
        raise_on_block: bool = False,
    ):
        self._agent_id = agent_id or os.environ.get("EDON_AGENT_ID", "clawdbot-agent")
        self._intent_id = intent_id
        self._raise_on_block = raise_on_block
        self._client = EdonClient(
            api_key=api_key,
            base_url=base_url,
            agent_id=self._agent_id,
            intent_id=intent_id,
            raise_on_block=False,
        )

    def execute(
        self,
        action_type: str,
        payload: Dict[str, Any],
        fn: Any,
        fn_args: tuple = (),
        fn_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Evaluate via EDON, then execute fn if allowed.

        Args:
            action_type: EDON action type (e.g. "tool.send_email").
            payload:     Action payload for governance evaluation.
            fn:          The tool function to execute if allowed.
            fn_args:     Positional args for fn.
            fn_kwargs:   Keyword args for fn.

        Returns:
            Tool output on ALLOW, error string on BLOCK (unless raise_on_block=True).

        Raises:
            EdonBlockedError: If blocked and raise_on_block=True.
            EdonEscalatedError: If HUMAN_REQUIRED and raise_on_block=True.
        """
        fn_kwargs = fn_kwargs or {}

        decision = self._client.evaluate(
            action_type,
            payload,
            agent_id=self._agent_id,
            intent_id=self._intent_id,
            raise_on_block=False,
        )

        if decision.blocked:
            if self._raise_on_block:
                raise EdonBlockedError(
                    decision.decision_reason,
                    action_id=decision.action_id,
                    reason_code=decision.reason_code,
                )
            return f"[EDON BLOCKED] {decision.decision_reason}"

        if decision.needs_human:
            if self._raise_on_block:
                raise EdonEscalatedError(
                    decision.decision_reason,
                    action_id=decision.action_id,
                    question=decision.escalation_question,
                )
            return f"[EDON ESCALATED] Human approval required: {decision.escalation_question}"

        return fn(*fn_args, **fn_kwargs)

    def check(
        self,
        action_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate an action without executing it.

        Returns:
            Dict with keys: allowed, blocked, needs_human, decision,
            decision_reason, reason_code, action_id.
        """
        decision = self._client.evaluate(
            action_type,
            payload,
            agent_id=self._agent_id,
            intent_id=self._intent_id,
            raise_on_block=False,
        )
        return {
            "allowed": decision.allowed,
            "blocked": decision.blocked,
            "needs_human": decision.needs_human,
            "decision": decision.decision,
            "decision_reason": decision.decision_reason,
            "reason_code": decision.reason_code,
            "action_id": decision.action_id,
        }
