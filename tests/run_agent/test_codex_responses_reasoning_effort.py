"""Regression tests for gpt-5.5 reasoning.effort normalization.

Evidence (OST-1575, 2026-07-13):
  - daemon.log shows `reasoning.effort=max` rejected by the OpenAI Responses
    API 20+ times with HTTP 400: "Invalid value: 'max'. Supported values are:
    'none', 'minimal', 'low', 'medium', 'high', and 'xhigh'."
  - Zero occurrences of "Invalid value: 'xhigh'" in the same log window.
  - The supported-values list in the error payload explicitly includes 'xhigh'.

AC1: gpt-5.5 never sends reasoning.effort=max.
AC2: Explicit xhigh is preserved for gpt-5.5 (not downgraded to high).
"""

import pytest


@pytest.fixture
def transport():
    import agent.transports.codex  # noqa: F401 — registers on import
    from agent.transports import get_transport
    return get_transport("codex_responses")


MESSAGES = [{"role": "user", "content": "hi"}]


class TestGpt55ReasoningEffortNormalization:
    """AC1 + AC2: gpt-5.5 effort normalization matches observed API behavior."""

    def test_max_is_not_sent_to_api(self, transport):
        """AC1: reasoning.effort='max' must never reach the Responses API for gpt-5.5.

        The API returns HTTP 400 "Invalid value: 'max'" for gpt-5.5.
        The transport must remap it to a supported wire value.
        """
        kw = transport.build_kwargs(
            model="gpt-5.5",
            messages=MESSAGES,
            tools=[],
            reasoning_config={"enabled": True, "effort": "max"},
        )
        effort = kw.get("reasoning", {}).get("effort")
        assert effort != "max", (
            f"gpt-5.5 must NOT send reasoning.effort=max (API rejects it); "
            f"got {effort!r}"
        )

    def test_max_remaps_to_xhigh(self, transport):
        """AC1: 'max' remaps to 'xhigh' (the verified API-supported maximum)."""
        kw = transport.build_kwargs(
            model="gpt-5.5",
            messages=MESSAGES,
            tools=[],
            reasoning_config={"enabled": True, "effort": "max"},
        )
        assert kw.get("reasoning", {}).get("effort") == "xhigh", (
            "gpt-5.5 should remap 'max' -> 'xhigh' (observed supported maximum)"
        )

    def test_ultra_remaps_to_xhigh(self, transport):
        """'ultra' (product alias for max reasoning) must not be sent as-is."""
        kw = transport.build_kwargs(
            model="gpt-5.5",
            messages=MESSAGES,
            tools=[],
            reasoning_config={"enabled": True, "effort": "ultra"},
        )
        assert kw.get("reasoning", {}).get("effort") == "xhigh", (
            "gpt-5.5 should remap 'ultra' -> 'xhigh'"
        )

    def test_xhigh_is_preserved(self, transport):
        """AC2: explicit 'xhigh' must NOT be downgraded.

        The observed API error payload lists 'xhigh' as a supported value.
        Zero 'Invalid value: xhigh' rejections were found in the daemon log.
        Downgrading xhigh -> high would silently cap reasoning below the
        observed and documented maximum.
        """
        kw = transport.build_kwargs(
            model="gpt-5.5",
            messages=MESSAGES,
            tools=[],
            reasoning_config={"enabled": True, "effort": "xhigh"},
        )
        assert kw.get("reasoning", {}).get("effort") == "xhigh", (
            "gpt-5.5 must preserve explicit 'xhigh' — it is API-supported "
            "(confirmed by error payload listing, 0 rejection logs)"
        )

    @pytest.mark.parametrize("effort", ["low", "medium", "high"])
    def test_standard_efforts_pass_through_unchanged(self, transport, effort):
        """Standard efforts below xhigh must not be altered for gpt-5.5."""
        kw = transport.build_kwargs(
            model="gpt-5.5",
            messages=MESSAGES,
            tools=[],
            reasoning_config={"enabled": True, "effort": effort},
        )
        assert kw.get("reasoning", {}).get("effort") == effort, (
            f"gpt-5.5 must pass through '{effort}' unchanged"
        )

    def test_gpt56_max_is_preserved(self, transport):
        """Regression: gpt-5.6 'max' mapping must be unaffected by gpt-5.5 branch.

        gpt-5.6 accepts 'max' as the wire value for ultra-tier reasoning.
        """
        kw = transport.build_kwargs(
            model="gpt-5.6",
            messages=MESSAGES,
            tools=[],
            reasoning_config={"enabled": True, "effort": "ultra"},
        )
        assert kw.get("reasoning", {}).get("effort") == "max", (
            "gpt-5.6 'ultra' -> 'max' mapping must remain intact"
        )

    def test_generic_model_unaffected(self, transport):
        """gpt-5.4 and other models must not be affected by gpt-5.5 normalization."""
        kw = transport.build_kwargs(
            model="gpt-5.4",
            messages=MESSAGES,
            tools=[],
            reasoning_config={"enabled": True, "effort": "max"},
        )
        assert kw.get("reasoning", {}).get("effort") == "max", (
            "Non-gpt-5.5 models must not be affected by the gpt-5.5 clamp"
        )
