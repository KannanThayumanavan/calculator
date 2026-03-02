import os
import sys
import unittest
import importlib
import subprocess
import time
import threading
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_parser(env_value: str):
    """
    Reload expression_parser with CALC_EXTENDED_OPERATORS set to *env_value*.
    Returns the freshly-imported module so tests can call parse() on it.
    """
    with patch.dict(os.environ, {"CALC_EXTENDED_OPERATORS": env_value}, clear=False):
        # Remove cached module so importlib picks up the new env value
        for key in list(sys.modules.keys()):
            if "expression_parser" in key or "calculator" in key:
                del sys.modules[key]
        import importlib
        import src.calculator.expression_parser as parser_mod
        importlib.reload(parser_mod)
        return parser_mod


def _parse(parser_mod, expression: str):
    """Thin wrapper so tests read cleanly."""
    return parser_mod.parse(expression)


# ---------------------------------------------------------------------------
# Base class shared by all SLT groups
# ---------------------------------------------------------------------------

class _SLTBase(unittest.TestCase):
    """Common assertion helpers."""

    def assertParseEqual(self, parser_mod, expr, expected):
        result = _parse(parser_mod, expr)
        self.assertEqual(
            result,
            expected,
            msg=f"parse({expr!r}) expected {expected!r}, got {result!r}",
        )

    def assertParseRaises(self, parser_mod, expr, exc_type=Exception):
        with self.assertRaises(exc_type, msg=f"Expected {exc_type} for parse({expr!r})"):
            _parse(parser_mod, expr)


# ===========================================================================
# SLT-1  Flag starts FALSE — extended operators must be rejected
# ===========================================================================

class SLT_FlagFalse_BaselineOperators(_SLTBase):
    """When ENABLE_EXTENDED_OPERATORS is false the parser handles only the
    baseline operator set (+, -, *, /) and rejects extended ones."""

    @classmethod
    def setUpClass(cls):
        cls.parser = _reload_parser("false")

    # --- happy paths (baseline operators always work) ---

    def test_addition(self):
        self.assertParseEqual(self.parser, "3 + 4", 7)

    def test_subtraction(self):
        self.assertParseEqual(self.parser, "10 - 6", 4)

    def test_multiplication(self):
        self.assertParseEqual(self.parser, "3 * 5", 15)

    def test_division(self):
        self.assertParseEqual(self.parser, "10 / 4", 2.5)

    def test_nested_baseline(self):
        self.assertParseEqual(self.parser, "(2 + 3) * 4", 20)

    def test_negative_numbers(self):
        self.assertParseEqual(self.parser, "-3 + 7", 4)

    def test_float_operands(self):
        self.assertParseEqual(self.parser, "1.5 + 2.5", 4.0)

    # --- error paths (extended operators must be rejected) ---

    def test_modulo_rejected(self):
        self.assertParseRaises(self.parser, "10 % 3")

    def test_exponentiation_rejected(self):
        self.assertParseRaises(self.parser, "2 ** 8")

    def test_modulo_in_expression_rejected(self):
        self.assertParseRaises(self.parser, "5 + 10 % 3")

    def test_exponentiation_in_expression_rejected(self):
        self.assertParseRaises(self.parser, "1 + 2 ** 3")

    def test_chained_extended_rejected(self):
        self.assertParseRaises(self.parser, "2 ** 3 % 5")

    # --- error paths (always-invalid input) ---

    def test_empty_string_raises(self):
        self.assertParseRaises(self.parser, "")

    def test_division_by_zero_raises(self):
        self.assertParseRaises(self.parser, "1 / 0", ZeroDivisionError)

    def test_unbalanced_parens_raises(self):
        self.assertParseRaises(self.parser, "(3 + 4")

    def test_invalid_token_raises(self):
        self.assertParseRaises(self.parser, "3 @ 4")


# ===========================================================================
# SLT-2  Flag starts TRUE — extended operators must be accepted
# ===========================================================================

class SLT_FlagTrue_ExtendedOperators(_SLTBase):
    """When ENABLE_EXTENDED_OPERATORS is true the parser accepts % and **."""

    @classmethod
    def setUpClass(cls):
        cls.parser = _reload_parser("true")

    # --- happy paths (baseline still works) ---

    def test_addition(self):
        self.assertParseEqual(self.parser, "3 + 4", 7)

    def test_subtraction(self):
        self.assertParseEqual(self.parser, "10 - 6", 4)

    def test_multiplication(self):
        self.assertParseEqual(self.parser, "3 * 5", 15)

    def test_division(self):
        self.assertParseEqual(self.parser, "10 / 4", 2.5)

    # --- happy paths (extended operators) ---

    def test_modulo_basic(self):
        self.assertParseEqual(self.parser, "10 % 3", 1)

    def test_modulo_zero_remainder(self):
        self.assertParseEqual(self.parser, "9 % 3", 0)

    def test_exponentiation_basic(self):
        self.assertParseEqual(self.parser, "2 ** 8", 256)

    def test_exponentiation_zero_power(self):
        self.assertParseEqual(self.parser, "5 ** 0", 1)

    def test_exponentiation_one_power(self):
        self.assertParseEqual(self.parser, "7 ** 1", 7)

    def test_modulo_in_compound_expression(self):
        self.assertParseEqual(self.parser, "5 + 10 % 3", 6)

    def test_exponentiation_in_compound_expression(self):
        self.assertParseEqual(self.parser, "1 + 2 ** 3", 9)

    def test_chained_extended(self):
        self.assertParseEqual(self.parser, "2 ** 3 % 5", 3)

    def test_nested_with_parens(self):
        self.assertParseEqual(self.parser, "(2 + 3) ** 2", 25)

    def test_modulo_with_float(self):
        result = _parse(self.parser, "10.5 % 3")
        self.assertAlmostEqual(result, 1.5, places=9)

    def test_large_exponent(self):
        self.assertParseEqual(self.parser, "2 ** 10", 1024)

    # --- error paths (always-invalid input) ---

    def test_empty_string_raises(self):
        self.assertParseRaises(self.parser, "")

    def test_division_by_zero_raises(self):
        self.assertParseRaises(self.parser, "1 / 0", ZeroDivisionError)

    def test_modulo_by_zero_raises(self):
        self.assertParseRaises(self.parser, "5 % 0", ZeroDivisionError)

    def test_unbalanced_parens_raises(self):