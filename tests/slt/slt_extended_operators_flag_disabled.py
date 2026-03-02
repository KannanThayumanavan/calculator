import os
import pytest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Ensure the flag is explicitly disabled for every test in this module.
# We patch at import-time via autouse fixture so individual tests never have
# to worry about environment leakage.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def disable_extended_operators(monkeypatch):
    """Force CALC_EXTENDED_OPERATORS=false for every test in this module."""
    monkeypatch.setenv("CALC_EXTENDED_OPERATORS", "false")
    # Re-import the module so the module-level constant is re-evaluated.
    import importlib
    import src.calculator.expression_parser as ep
    importlib.reload(ep)
    yield
    # Reload again on teardown so we leave the module in a clean state.
    importlib.reload(ep)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(expression: str):
    """Import (already reloaded) parser and call parse()."""
    import src.calculator.expression_parser as ep
    return ep.parse(expression)


def _get_flag() -> bool:
    import src.calculator.expression_parser as ep
    return ep.ENABLE_EXTENDED_OPERATORS


# ---------------------------------------------------------------------------
# 1. Verify the feature flag is actually False in this environment
# ---------------------------------------------------------------------------

class TestFeatureFlagState:
    def test_flag_is_false_when_env_var_is_false(self):
        assert _get_flag() is False

    def test_flag_is_false_when_env_var_is_missing(self, monkeypatch):
        monkeypatch.delenv("CALC_EXTENDED_OPERATORS", raising=False)
        import importlib
        import src.calculator.expression_parser as ep
        importlib.reload(ep)
        assert ep.ENABLE_EXTENDED_OPERATORS is False

    def test_flag_is_false_when_env_var_is_FALSE_uppercase(self, monkeypatch):
        monkeypatch.setenv("CALC_EXTENDED_OPERATORS", "FALSE")
        import importlib
        import src.calculator.expression_parser as ep
        importlib.reload(ep)
        assert ep.ENABLE_EXTENDED_OPERATORS is False

    def test_flag_is_false_when_env_var_is_0(self, monkeypatch):
        monkeypatch.setenv("CALC_EXTENDED_OPERATORS", "0")
        import importlib
        import src.calculator.expression_parser as ep
        importlib.reload(ep)
        assert ep.ENABLE_EXTENDED_OPERATORS is False


# ---------------------------------------------------------------------------
# 2. Extended operators MUST raise UnsupportedOperatorError when flag is off
# ---------------------------------------------------------------------------

class TestModuloRaisesWhenFlagDisabled:
    """Modulo (%) expressions must raise UnsupportedOperatorError."""

    def _assert_raises(self, expression: str):
        from src.calculator.expression_parser import UnsupportedOperatorError
        with pytest.raises(UnsupportedOperatorError):
            _parse(expression)

    def test_simple_modulo(self):
        self._assert_raises("10 % 3")

    def test_modulo_with_floats(self):
        self._assert_raises("10.5 % 3.2")

    def test_modulo_result_would_be_zero(self):
        self._assert_raises("9 % 3")

    def test_modulo_with_negative_dividend(self):
        self._assert_raises("-10 % 3")

    def test_modulo_with_negative_divisor(self):
        self._assert_raises("10 % -3")

    def test_modulo_both_negative(self):
        self._assert_raises("-10 % -3")

    def test_modulo_chained(self):
        self._assert_raises("10 % 3 % 2")

    def test_modulo_combined_with_addition(self):
        self._assert_raises("10 + 5 % 3")

    def test_modulo_combined_with_multiplication(self):
        self._assert_raises("4 * 5 % 3")

    def test_modulo_with_parentheses(self):
        self._assert_raises("(10 + 2) % 4")

    def test_modulo_zero_divisor(self):
        """Even a zero-divisor modulo must raise UnsupportedOperatorError, not ZeroDivisionError."""
        from src.calculator.expression_parser import UnsupportedOperatorError
        with pytest.raises(UnsupportedOperatorError):
            _parse("5 % 0")

    def test_modulo_large_numbers(self):
        self._assert_raises("1000000 % 7")

    def test_modulo_whitespace_variants(self):
        self._assert_raises("10%3")

    def test_modulo_whitespace_variants_extra_spaces(self):
        self._assert_raises("10  %  3")


class TestExponentiationRaisesWhenFlagDisabled:
    """Exponentiation (**) expressions must raise UnsupportedOperatorError."""

    def _assert_raises(self, expression: str):
        from src.calculator.expression_parser import UnsupportedOperatorError
        with pytest.raises(UnsupportedOperatorError):
            _parse(expression)

    def test_simple_exponentiation(self):
        self._assert_raises("2 ** 3")

    def test_exponentiation_with_floats(self):
        self._assert_raises("2.5 ** 2")

    def test_exponentiation_result_is_one(self):
        self._assert_raises("5 ** 0")

    def test_exponentiation_result_is_base(self):
        self._assert_raises("5 ** 1")

    def test_exponentiation_negative_exponent(self):
        self._assert_raises("2 ** -3")

    def test_exponentiation_negative_base(self):
        self._assert_raises("-2 ** 3")

    def test_exponentiation_fractional_exponent(self):
        self._assert_raises("4 ** 0.5")

    def test_exponentiation_chained(self):
        self._assert_raises("2 ** 3 ** 2")

    def test_exponentiation_combined_with_addition(self):
        self._assert_raises("1 + 2 ** 3")

    def test_exponentiation_combined_with_multiplication(self):
        self._assert_raises("3 * 2 ** 4")

    def test_exponentiation_with_parentheses(self):
        self._assert_raises("(1 + 1) ** 8")

    def test_exponentiation_large_numbers(self):
        self._assert_raises("10 ** 10")

    def test_exponentiation_whitespace_variants(self):
        self._assert_raises("2**3")

    def test_exponentiation_whitespace_variants_extra_spaces(self):
        self._assert_raises("2  **  3")

    def test_exponentiation_zero_base(self):
        self._assert_raises("0 ** 5")

    def test_exponentiation_zero_base_zero_exp(self):
        self._assert_raises("0 ** 0")


class TestUnsupportedOperatorErrorProperties:
    """Verify the exception carries useful diagnostic information."""

    def test_modulo_error_message_contains_operator(self):
        from src.calculator.expression_parser import UnsupportedOperatorError
        with pytest.raises(UnsupportedOperatorError) as exc_info:
            _parse("10 % 3")
        assert "%" in str(exc_info.value)

    def test_exponentiation_error_message_contains_operator(self):
        from src.calculator.expression_parser import UnsupportedOperatorError
        with pytest.raises(Unsupported