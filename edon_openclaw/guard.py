"""EdonOpenClawGuard — EDON governance for OpenClaw tools and skills."""

from __future__ import annotations

import functools
import inspect
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from edon import EdonClient
from edon.exceptions import EdonBlockedError, EdonEscalatedError


def governed_skill(
    action_type: Optional[str] = None,
    *,
    agent_id: Optional[str] = None,
    intent_id: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    raise_on_block: bool = True,
) -> Callable:
    """Decorator: add EDON governance to an OpenClaw skill function.

    The decorated function only executes if EDON allows it. Blocked actions
    raise ``EdonBlockedError`` (or return an error string if raise_on_block=False).

    Usage::

        from edon_openclaw import governed_skill

        @governed_skill(action_type="email.send")
        def send_email(to: str, subject: str, body: str) -> str:
            return smtp_send(to, subject, body)

        # Configure once via env vars or pass directly:
        #   EDON_API_KEY=your-key
        #   EDON_AGENT_ID=clawdbot-agent

    Args:
        action_type:    EDON action type (e.g. "email.send"). Defaults to
                        "skill.<function_name>".
        agent_id:       Agent identifier in the audit trail. Defaults to
                        ``EDON_AGENT_ID`` env var or "clawdbot-agent".
        intent_id:      Pin to a specific intent contract.
        api_key:        EDON API key. Defaults to ``EDON_API_KEY`` env var.
        base_url:       EDON gateway URL. Defaults to cloud or ``EDON_BASE_URL``.
        raise_on_block: Raise on BLOCK (True) or return error string (False).
    """
    def decorator(fn: Callable) -> Callable:
        _action = action_type or f"skill.{fn.__name__}"
        _agent = agent_id or os.environ.get("EDON_AGENT_ID", "clawdbot-agent")
        _client = EdonClient(
            api_key=api_key,
            base_url=base_url,
            agent_id=_agent,
            intent_id=intent_id,
            raise_on_block=False,
        )

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build payload from function signature
            sig = inspect.signature(fn)
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                payload = dict(bound.arguments)
            except TypeError:
                payload = {"args": list(args), **kwargs}

            decision = _client.evaluate(
                _action,
                payload,
                agent_id=_agent,
                intent_id=intent_id,
                raise_on_block=False,
            )

            if decision.blocked:
                if raise_on_block:
                    raise EdonBlockedError(
                        decision.decision_reason,
                        action_id=decision.action_id,
                        reason_code=decision.reason_code,
                    )
                return f"[EDON BLOCKED] {decision.decision_reason}"

            if decision.needs_human:
                if raise_on_block:
                    raise EdonEscalatedError(
                        decision.decision_reason,
                        action_id=decision.action_id,
                        question=decision.escalation_question,
                    )
                return f"[EDON ESCALATED] {decision.decision_reason}"

            return fn(*args, **kwargs)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            sig = inspect.signature(fn)
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                payload = dict(bound.arguments)
            except TypeError:
                payload = {"args": list(args), **kwargs}

            decision = _client.evaluate(
                _action,
                payload,
                agent_id=_agent,
                intent_id=intent_id,
                raise_on_block=False,
            )

            if decision.blocked:
                if raise_on_block:
                    raise EdonBlockedError(
                        decision.decision_reason,
                        action_id=decision.action_id,
                        reason_code=decision.reason_code,
                    )
                return f"[EDON BLOCKED] {decision.decision_reason}"

            if decision.needs_human:
                if raise_on_block:
                    raise EdonEscalatedError(
                        decision.decision_reason,
                        action_id=decision.action_id,
                        question=decision.escalation_question,
                    )
                return f"[EDON ESCALATED] {decision.decision_reason}"

            return await fn(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(fn) else wrapper

    return decorator


class EdonOpenClawGuard:
    """Factory for adding EDON governance to OpenClaw tool registries.

    Usage::

        from edon_openclaw import EdonOpenClawGuard

        # Wrap a dict of {name: callable} tool registry
        governed = EdonOpenClawGuard.wrap_tools(
            tools={"send_email": send_email, "search_web": search_web},
            api_key=os.environ["EDON_API_KEY"],
            agent_id="clawdbot-agent",
        )

        # Or wrap a list of callables
        governed_list = EdonOpenClawGuard.wrap_tools(
            tools=[send_email, search_web],
            api_key=os.environ["EDON_API_KEY"],
        )
    """

    @staticmethod
    def wrap_tools(
        tools: Any,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        intent_id: Optional[str] = None,
        raise_on_block: bool = True,
    ) -> Any:
        """Wrap OpenClaw tools with EDON governance.

        Accepts either a list of callables or a dict mapping name -> callable.
        Returns the same type (list or dict) with governed versions.

        Args:
            tools:          List[callable] or Dict[str, callable].
            api_key:        EDON API key (default: ``EDON_API_KEY`` env var).
            base_url:       EDON gateway URL.
            agent_id:       Agent identifier (default: ``EDON_AGENT_ID`` env var).
            intent_id:      Active intent contract ID.
            raise_on_block: Raise on BLOCK or return error string.

        Returns:
            Governed tools in the same format as input.
        """
        _agent = agent_id or os.environ.get("EDON_AGENT_ID", "clawdbot-agent")

        def _wrap_fn(fn: Callable, name: Optional[str] = None) -> Callable:
            action = f"skill.{name or fn.__name__}"
            return governed_skill(
                action_type=action,
                agent_id=_agent,
                intent_id=intent_id,
                api_key=api_key,
                base_url=base_url,
                raise_on_block=raise_on_block,
            )(fn)

        if isinstance(tools, dict):
            return {name: _wrap_fn(fn, name) for name, fn in tools.items()}

        if isinstance(tools, list):
            return [_wrap_fn(fn) for fn in tools]

        # Single callable
        return _wrap_fn(tools)
