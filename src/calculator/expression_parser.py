import os
from typing import List, Union

ENABLE_EXTENDED_OPERATORS = os.getenv('CALC_EXTENDED_OPERATORS', 'false').lower() == 'true'


class UnsupportedOperatorError(Exception):
    """Raised when an unsupported operator is encountered during parsing."""
    pass


class ExpressionParserError(Exception):
    """Raised when an expression cannot be parsed."""
    pass


Token = Union[str, float, int]


def _tokenize(expression: str) -> List[Token]:
    """Tokenize a mathematical expression string into a list of tokens."""
    tokens = []
    i = 0
    expression = expression.strip()

    while i < len(expression):
        char = expression[i]

        if char.isspace():
            i += 1
            continue

        if char.isdigit() or (char == '.' and i + 1 < len(expression) and expression[i + 1].isdigit()):
            j = i
            while j < len(expression) and (expression[j].isdigit() or expression[j] == '.'):
                j += 1
            token_str = expression[i:j]
            try:
                if '.' in token_str:
                    tokens.append(float(token_str))
                else:
                    tokens.append(int(token_str))
            except ValueError:
                raise ExpressionParserError(f'Invalid number token: {token_str}')
            i = j
            continue

        if char == '*' and i + 1 < len(expression) and expression[i + 1] == '*':
            tokens.append('**')
            i += 2
            continue

        if char in ('+', '-', '*', '/', '%', '(', ')'):
            tokens.append(char)
            i += 1
            continue

        raise ExpressionParserError(f'Unexpected character: {char!r}')

    return tokens


def _parse_extended_operators(tokens: List[Token]) -> float:
    """
    Parse and evaluate a token list that may include '%' (modulo)
    and '**' (exponentiation) operators, in addition to the standard
    +, -, *, / operators.

    Operator precedence (lowest to highest):
      1. + and -
      2. * and / and %
      3. ** (right-associative)
      4. Unary + and -
      5. Parentheses and literals
    """
    pos = [0]

    def peek() -> Union[Token, None]:
        if pos[0] < len(tokens):
            return tokens[pos[0]]
        return None

    def consume() -> Token:
        token = tokens[pos[0]]
        pos[0] += 1
        return token

    def parse_expression() -> float:
        return parse_additive()

    def parse_additive() -> float:
        left = parse_multiplicative()
        while peek() in ('+', '-'):
            op = consume()
            right = parse_multiplicative()
            if op == '+':
                left = left + right
            else:
                left = left - right
        return left

    def parse_multiplicative() -> float:
        left = parse_exponentiation()
        while peek() in ('*', '/', '%'):
            op = consume()
            right = parse_exponentiation()
            if op == '*':
                left = left * right
            elif op == '/':
                if right == 0:
                    raise ExpressionParserError('Division by zero')
                left = left / right
            elif op == '%':
                if right == 0:
                    raise ExpressionParserError('Modulo by zero')
                left = left % right
        return left

    def parse_exponentiation() -> float:
        base = parse_unary()
        if peek() == '**':
            consume()
            exponent = parse_exponentiation()
            return base ** exponent
        return base

    def parse_unary() -> float:
        if peek() == '-':
            consume()
            return -parse_primary()
        if peek() == '+':
            consume()
            return parse_primary()
        return parse_primary()

    def parse_primary() -> float:
        token = peek()

        if token == '(':
            consume()
            value = parse_expression()
            if peek() != ')':
                raise ExpressionParserError('Expected closing parenthesis')
            consume()
            return value

        if isinstance(token, (int, float)):
            consume()
            return float(token)

        raise ExpressionParserError(f'Unexpected token: {token!r}')

    result = parse_expression()

    if pos[0] != len(tokens):
        raise ExpressionParserError(
            f'Unexpected token at position {pos[0]}: {tokens[pos[0]]!r}'
        )

    return result


def _parse_standard(tokens: List[Token]) -> float:
    """
    Parse and evaluate a token list using only standard operators:
    +, -, *, / with proper precedence and parentheses support.

    Raises UnsupportedOperatorError if '%' or '**' tokens are encountered.
    """
    pos = [0]

    def peek() -> Union[Token, None]:
        if pos[0] < len(tokens):
            return tokens[pos[0]]
        return None

    def consume() -> Token:
        token = tokens[pos[0]]
        pos[0] += 1
        return token

    def parse_expression() -> float:
        return parse_additive()

    def parse_additive() -> float:
        left = parse_multiplicative()
        while peek() in ('+', '-'):
            op = consume()
            right = parse_multiplicative()
            if op == '+':
                left = left + right
            else:
                left = left - right
        return left

    def parse_multiplicative() -> float:
        left = parse_unary()
        while peek() in ('*', '/', '%', '**'):
            op = consume()
            if op in ('%', '**'):
                raise UnsupportedOperatorError(f'Operator not supported: {op}')
            right = parse_unary()
            if op == '*':
                left = left * right
            elif op == '/':
                if right == 0:
                    raise ExpressionParserError('Division by zero')
                left = left / right
        return left

    def parse_unary() -> float:
        if peek() == '-':
            consume()
            return -parse_primary()
        if peek() == '+':
            consume()
            return parse_primary()
        return parse_primary()

    def parse_primary() -> float:
        token = peek()

        if token == '(':
            consume()
            value = parse_expression()
            if peek() != ')':
                raise ExpressionParserError('Expected closing parenthesis')
            consume()
            return value

        if isinstance(token, (int, float)):
            consume()
            return float(token)

        if token in ('%', '**'):
            raise UnsupportedOperatorError(f'Operator not supported: {token}')

        raise ExpressionParserError(f'Unexpected token: {token!r}')

    result = parse_expression()

    if pos[0] != len(tokens):
        remaining_token = tokens[pos[0]]
        if remaining_token in ('%', '**'):
            raise UnsupportedOperatorError(f'Operator not supported: {remaining_token}')
        raise ExpressionParserError(
            f'Unexpected token at position {pos[0]}: {remaining_token!r}'
        )

    return result


def parse(expression: str) -> float:
    """
    Parse and evaluate a mathematical expression string.

    Supports standard operators (+, -, *, /) always.
    Supports extended operators (%, **) only when ENABLE_EXTENDED_OPERATORS is True.

    Args:
        expression: A string containing a mathematical expression.

    Returns:
        The evaluated result as a float.

    Raises:
        ExpressionParserError: If