import os
import pytest
from unittest.mock import patch

from calculator.expression_parser import (
    ENABLE_EXTENDED_OPERATORS,
    UnsupportedOperatorError,
    parse,
)


# ---------------------------------------------------------------------------
# Group A – Always-rejected malformed expressions
# These must raise parse errors regardless of the ENABLE_EXTENDED_OPERATORS flag.
# ---------------------------------------------------------------------------

class TestIntentionallyInvalidExpressionsAlwaysRejected:
    """SCRUM-24 – Group A: malformed expressions that are never valid."""

    @pytest.mark.parametrize("expression", [
        "+ 5",
        "3 +",
        "@@",
    ])
    def test_malformed_expressions_raise_parse_error(self, expression):
        """Malformed expressions must raise a parse error regardless of flag state."""
        with pytest.raises(Exception):  # ParseError or ValueError or similar
            parse(expression)

    @pytest.mark.parametrize("expression", [
        "+ 5",
        "3 +",
        "@@",
    ])
    def test_malformed_expressions_raise_parse_error_with_flag_enabled(self, expression):
        """Malformed expressions must raise a parse error even when extended operators are on."""
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "true"}):
            # Re-import or call parse directly; the flag is module-level but parse()
            # reads it at call time via the conditional, so patching env and reloading
            # is the safest approach.
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)
            with pytest.raises(Exception):
                ep.parse(expression)

    def test_intentionally_invalid_expressions_always_rejected(self):
        """Explicit single test asserting all three bad expressions raise regardless of flag."""
        bad_expressions = ["+ 5", "3 +", "@@"]

        # With flag disabled (default)
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "false"}):
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)
            for expr in bad_expressions:
                with pytest.raises(Exception, match=r".*"):
                    ep.parse(expr)

        # With flag enabled
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "true"}):
            importlib.reload(ep)
            for expr in bad_expressions:
                with pytest.raises(Exception, match=r".*"):
                    ep.parse(expr)


# ---------------------------------------------------------------------------
# Group B – Not-yet-supported operators (extended operators)
# Skipped unless ENABLE_EXTENDED_OPERATORS is True.
# ---------------------------------------------------------------------------

class TestExtendedOperators:
    """SCRUM-24 – Group B: extended operator tests, skipped when flag is disabled."""

    @pytest.mark.skipif(
        not ENABLE_EXTENDED_OPERATORS,
        reason="Extended operators not enabled",
    )
    def test_modulo_operator_with_flag_enabled(self):
        """'10 % 3' must evaluate to 1 when ENABLE_EXTENDED_OPERATORS is True."""
        result = parse("10 % 3")
        assert result == 1, f"Expected 1 but got {result}"

    @pytest.mark.skipif(
        not ENABLE_EXTENDED_OPERATORS,
        reason="Extended operators not enabled",
    )
    def test_exponentiation_operator_with_flag_enabled(self):
        """'2 ** 8' must evaluate to 256 when ENABLE_EXTENDED_OPERATORS is True."""
        result = parse("2 ** 8")
        assert result == 256, f"Expected 256 but got {result}"


# ---------------------------------------------------------------------------
# Explicit flag-enabled tests (reload module to pick up env override)
# ---------------------------------------------------------------------------

class TestExtendedOperatorsWithFlagForced:
    """SCRUM-24 – Tests that force the flag on via env var and reload the module."""

    def test_modulo_operator_with_flag_enabled(self):
        """'10 % 3' evaluates to 1 when CALC_EXTENDED_OPERATORS=true."""
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "true"}):
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)
            assert ep.ENABLE_EXTENDED_OPERATORS is True
            result = ep.parse("10 % 3")
            assert result == 1, f"Expected 1 but got {result}"

    def test_exponentiation_operator_with_flag_enabled(self):
        """'2 ** 8' evaluates to 256 when CALC_EXTENDED_OPERATORS=true."""
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "true"}):
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)
            assert ep.ENABLE_EXTENDED_OPERATORS is True
            result = ep.parse("2 ** 8")
            assert result == 256, f"Expected 256 but got {result}"


# ---------------------------------------------------------------------------
# Flag-disabled rejection tests
# ---------------------------------------------------------------------------

class TestExtendedOperatorsRejectedWhenFlagDisabled:
    """SCRUM-24 – Extended operators must raise UnsupportedOperatorError when flag is False."""

    def test_extended_operators_rejected_when_flag_disabled(self):
        """'10 % 3' and '2 ** 8' raise UnsupportedOperatorError when flag is False."""
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "false"}):
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)

            assert ep.ENABLE_EXTENDED_OPERATORS is False

            with pytest.raises(ep.UnsupportedOperatorError):
                ep.parse("10 % 3")

            with pytest.raises(ep.UnsupportedOperatorError):
                ep.parse("2 ** 8")

    def test_modulo_rejected_when_flag_disabled(self):
        """'10 % 3' raises UnsupportedOperatorError when CALC_EXTENDED_OPERATORS is unset/false."""
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "false"}):
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)
            with pytest.raises(ep.UnsupportedOperatorError):
                ep.parse("10 % 3")

    def test_exponentiation_rejected_when_flag_disabled(self):
        """'2 ** 8' raises UnsupportedOperatorError when CALC_EXTENDED_OPERATORS is unset/false."""
        with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": "false"}):
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)
            with pytest.raises(ep.UnsupportedOperatorError):
                ep.parse("2 ** 8")


# ---------------------------------------------------------------------------
# Feature flag default value test
# ---------------------------------------------------------------------------

class TestFeatureFlagDefault:
    """SCRUM-24 – The feature flag must default to False when env var is unset."""

    def test_feature_flag_defaults_to_false(self):
        """ENABLE_EXTENDED_OPERATORS is False when CALC_EXTENDED_OPERATORS env var is unset."""
        # Remove the env var entirely to simulate an unset environment.
        env_without_flag = {
            k: v for k, v in os.environ.items() if k != "CALC_EXTENDED_OPERATORS"
        }
        with patch.dict(os.environ, env_without_flag, clear=True):
            import importlib
            import calculator.expression_parser as ep
            importlib.reload(ep)
            assert ep.ENABLE_EXTENDED_OPERATORS is False, (
                f"Expected ENABLE_EXTENDED_OPERATORS to be