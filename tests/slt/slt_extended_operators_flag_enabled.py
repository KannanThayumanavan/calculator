import os
import pytest
from calculator.expression_parser import parse, ENABLE_EXTENDED_OPERATORS
from calculator.evaluator import evaluate


EXTENDED_OPERATORS_ENABLED = os.getenv("CALC_EXTENDED_OPERATORS", "false").lower() == "true"

pytestmark = pytest.mark.skipif(
    not EXTENDED_OPERATORS_ENABLED,
    reason="ENABLE_EXTENDED_OPERATORS is not enabled; set CALC_EXTENDED_OPERATORS=true to run these tests",
)


class TestModuloOperatorHappyPath:
    """Service-level tests for the modulo (%) operator when extended operators are enabled."""

    def test_modulo_basic(self):
        """10 % 3 should evaluate to 1."""
        expression = "10 % 3"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 1, f"Expected 1, got {result}"

    def test_modulo_zero_remainder(self):
        """9 % 3 should evaluate to 0."""
        expression = "9 % 3"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 0, f"Expected 0, got {result}"

    def test_modulo_larger_divisor(self):
        """3 % 10 should evaluate to 3."""
        expression = "3 % 10"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 3, f"Expected 3, got {result}"

    def test_modulo_negative_dividend(self):
        """-10 % 3 should evaluate consistently with Python semantics."""
        expression = "-10 % 3"
        ast = parse(expression)
        result = evaluate(ast)
        expected = -10 % 3
        assert result == expected, f"Expected {expected}, got {result}"

    def test_modulo_negative_divisor(self):
        """10 % -3 should evaluate consistently with Python semantics."""
        expression = "10 % -3"
        ast = parse(expression)
        result = evaluate(ast)
        expected = 10 % -3
        assert result == expected, f"Expected {expected}, got {result}"

    def test_modulo_with_addition(self):
        """(10 + 5) % 4 should evaluate to 3."""
        expression = "(10 + 5) % 4"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 3, f"Expected 3, got {result}"

    def test_modulo_with_multiplication(self):
        """10 % (2 * 3) should evaluate to 4."""
        expression = "10 % (2 * 3)"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 4, f"Expected 4, got {result}"

    def test_modulo_chained(self):
        """17 % 5 % 2 should evaluate left-to-right: (17 % 5) % 2 = 2 % 2 = 0."""
        expression = "17 % 5 % 2"
        ast = parse(expression)
        result = evaluate(ast)
        expected = 17 % 5 % 2
        assert result == expected, f"Expected {expected}, got {result}"

    def test_modulo_float_operands(self):
        """10.5 % 3.0 should evaluate to 1.5."""
        expression = "10.5 % 3.0"
        ast = parse(expression)
        result = evaluate(ast)
        expected = 10.5 % 3.0
        assert abs(result - expected) < 1e-9, f"Expected {expected}, got {result}"

    def test_modulo_precedence_over_addition(self):
        """10 % 3 + 1 should evaluate as (10 % 3) + 1 = 2."""
        expression = "10 % 3 + 1"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 2, f"Expected 2, got {result}"

    def test_modulo_precedence_with_multiplication(self):
        """2 * 10 % 3 should evaluate as (2 * 10) % 3 = 20 % 3 = 2."""
        expression = "2 * 10 % 3"
        ast = parse(expression)
        result = evaluate(ast)
        expected = 2 * 10 % 3
        assert result == expected, f"Expected {expected}, got {result}"


class TestExponentiationOperatorHappyPath:
    """Service-level tests for the exponentiation (**) operator when extended operators are enabled."""

    def test_exponentiation_basic(self):
        """2 ** 8 should evaluate to 256."""
        expression = "2 ** 8"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 256, f"Expected 256, got {result}"

    def test_exponentiation_zero_exponent(self):
        """5 ** 0 should evaluate to 1."""
        expression = "5 ** 0"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 1, f"Expected 1, got {result}"

    def test_exponentiation_one_exponent(self):
        """7 ** 1 should evaluate to 7."""
        expression = "7 ** 1"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 7, f"Expected 7, got {result}"

    def test_exponentiation_zero_base(self):
        """0 ** 5 should evaluate to 0."""
        expression = "0 ** 5"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 0, f"Expected 0, got {result}"

    def test_exponentiation_one_base(self):
        """1 ** 100 should evaluate to 1."""
        expression = "1 ** 100"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == 1, f"Expected 1, got {result}"

    def test_exponentiation_fractional_exponent(self):
        """4 ** 0.5 should evaluate to 2.0."""
        expression = "4 ** 0.5"
        ast = parse(expression)
        result = evaluate(ast)
        assert abs(result - 2.0) < 1e-9, f"Expected 2.0, got {result}"

    def test_exponentiation_negative_base(self):
        """(-2) ** 3 should evaluate to -8."""
        expression = "(-2) ** 3"
        ast = parse(expression)
        result = evaluate(ast)
        assert result == -8, f"Expected -8, got {result}"

    def test_exponentiation_negative_exponent(self):
        """2 ** -1 should evaluate to 0.5."""
        expression = "2 ** -1"
        ast = parse(expression)
        result = evaluate(ast)
        assert abs(result - 0.5) < 1e-9, f"Expected 0.5, got {result}"

    def test_exponentiation_right_associativity(self):
        """2 ** 3 ** 2 should evaluate right-to-left: 2 ** (3 ** 2) = 2 ** 9 = 512."""
        expression = "2 ** 3 ** 2"
        ast = parse(expression)
        result = evaluate(ast)
        expected = 2 ** 3 ** 2
        assert result == expected, f"Expected {expected}, got {result}"

    def test_exponentiation_with_addition(self):
        """2 ** 8 + 1 should evaluate as (2 ** 8) + 1 = 257."""