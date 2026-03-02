import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.calculator.expression_parser import parse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(expr):
    """Thin wrapper so tests read cleanly."""
    return parse(expr)


# ---------------------------------------------------------------------------
# Parametrize fixtures for the two flag states so every test runs under both
# ---------------------------------------------------------------------------

@pytest.fixture(params=["false", "true"], ids=["flag_off", "flag_on"])
def any_flag_state(request, monkeypatch):
    """
    Ensure every test in this module executes with the feature flag both
    disabled and enabled.  Group A (always-rejected) behaviour must be
    identical in both states.
    """
    monkeypatch.setenv("CALC_EXTENDED_OPERATORS", request.param)
    # Re-import so the module-level constant is re-evaluated.
    import importlib
    import src.calculator.expression_parser as _mod
    importlib.reload(_mod)
    # Patch the module-level reference used by parse()
    monkeypatch.setattr(_mod, "ENABLE_EXTENDED_OPERATORS",
                        request.param == "true")
    yield request.param
    importlib.reload(_mod)


# ---------------------------------------------------------------------------
# Group A – Malformed syntax
# ---------------------------------------------------------------------------

class TestMalformedSyntax:
    """Expressions that are syntactically broken must always raise."""

    @pytest.mark.parametrize("expr", [
        "",                    # empty string
        "   ",                 # whitespace only
        "1 +",                 # trailing operator, missing right operand
        "+ 1",                 # leading operator, missing left operand
        "1 + + 2",             # consecutive operators
        "1 + * 2",             # consecutive different operators
        "* 2",                 # operator at start
        "1 *",                 # operator at end
        "()",                  # empty parentheses
        "(1 +)",               # incomplete expression inside parens
        "1 + (2 *)",           # incomplete sub-expression
        "((1 + 2)",            # unmatched opening paren
        "(1 + 2))",            # unmatched closing paren
        "1 + (2 + (3 * 4)",    # deeply nested unmatched paren
        "1 2",                 # two operands without operator
        "1 2 + 3",             # operand collision
        "1 + 2 3",             # trailing operand
        ".",                   # lone decimal point
        "1 + .e5",             # malformed float
        "1e",                  # incomplete scientific notation
        "1e+",                 # incomplete exponent
        "--1",                 # double negation (not supported)
        "1 + 2 +",             # trailing operator after valid sub-expr
        "( 1 + 2",             # unclosed paren
        "1 + 2 )",             # extra closing paren
    ])
    def test_malformed_syntax_always_rejected(self, any_flag_state, expr):
        with pytest.raises((SyntaxError, ValueError, TypeError)):
            _parse(expr)


# ---------------------------------------------------------------------------
# Group A – Missing operands
# ---------------------------------------------------------------------------

class TestMissingOperands:
    """Operators present but one or both operands are absent."""

    @pytest.mark.parametrize("expr", [
        "+",
        "-",
        "*",
        "/",
        "/ 5",
        "5 /",
        "* 5",
        "5 *",
        "5 + * 3",
        "5 - / 3",
        "(+)",
        "(-)",
        "(*)",
        "(/)",
        "5 + ()",
        "() + 5",
        "(5 +) * 3",
        "3 * (/ 2)",
    ])
    def test_missing_operands_always_rejected(self, any_flag_state, expr):
        with pytest.raises((SyntaxError, ValueError, TypeError)):
            _parse(expr)


# ---------------------------------------------------------------------------
# Group A – Unknown / unsupported symbols
# ---------------------------------------------------------------------------

class TestUnknownSymbols:
    """
    Symbols that are not part of the defined grammar must always be rejected.
    Note: % and ** are *extended* operators gated by the feature flag and are
    tested separately in the extended-operators SLT.  The symbols below are
    never valid regardless of any flag.
    """

    @pytest.mark.parametrize("expr", [
        "1 @ 2",               # matrix-multiply operator
        "1 & 2",               # bitwise AND
        "1 | 2",               # bitwise OR
        "1 ^ 2",               # bitwise XOR
        "1 ~ 2",               # bitwise NOT (binary usage)
        "1 << 2",              # left shift
        "1 >> 2",              # right shift
        "1 // 2",              # floor-division (not in grammar)
        "1 != 2",              # comparison operator
        "1 == 2",              # equality operator
        "1 < 2",               # less-than
        "1 > 2",               # greater-than
        "1 <= 2",              # less-than-or-equal
        "1 >= 2",              # greater-than-or-equal
        "1 and 2",             # logical keyword
        "1 or 2",              # logical keyword
        "not 1",               # logical keyword
        "sqrt(4)",             # function call syntax not in grammar
        "abs(-1)",             # function call syntax not in grammar
        "1 + $2",              # dollar sign
        "1 + #2",              # hash / comment char
        "1 + @var",            # decorator-like symbol
        "1 + 2!",              # factorial (not supported)
        "1 + 2j",              # complex literal
        "0b1010",              # binary literal
        "0o17",                # octal literal
        "0x1F",                # hex literal
        "1 + 2; 3 + 4",        # statement separator
        "lambda x: x",         # Python keyword
        "import os",           # Python keyword
        "1 + None",            # Python keyword / None literal
        "1 + True",            # boolean literal
        "1 + False",           # boolean literal
        "1 + inf",             # symbolic constant (not in grammar)
        "1 + nan",             # symbolic constant (not in grammar)
        "1 + pi",              # symbolic constant (not in grammar)
        "1 + e",               # symbolic constant (not in grammar)
        "x + 1",               # undefined variable
        "foo",                 # bare identifier
        "foo()",               # call with no args
        "1 + 2 # comment",     # inline comment
    ])
    def test_unknown_symbols_always_rejected(self, any_flag_state, expr):
        with pytest.raises((SyntaxError, ValueError, TypeError, NameError)):
            _parse(expr)


# ---------------------------------------------------------------------------
# Sanity-check: valid baseline expressions still work under both flag states
# ---------------------------------------------------------------------------

class TestBaselineExpressionsAlwaysAccepted:
    """
    Core arithmetic that has always been supported must continue to work
    regardless of the feature flag.  These are the Group A happy-path cases.
    """

    @pytest.mark.parametrize("expr,expected", [
        ("1 + 2", 3),
        ("10 - 4", 6),
        ("3 * 4", 12),
        ("8 / 2", 4.0),
        ("(1 + 2) * 3", 9),
        ("10 / (2 + 3)", 2.0),
        ("100 - 50 + 25", 75),
        ("2 * 3 + 4 *