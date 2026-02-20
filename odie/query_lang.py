"""
Mini query language (advanced filtering)
=======================================

ODIE supports a small SQL-like boolean expression language for the `where` command.
Examples:
- where year >= 2000 and deaths > 1000
- where country == "India" and subtype == "Ground movement"

This file provides:
- Tokenizer (turns text into tokens)
- Parser (builds an AST = abstract syntax tree)
- AST node classes (And/Or/Cmp)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional
import re

# Simple expression language:
# expr := term (OR term)*
# term := factor (AND factor)*
# factor := comparison | "(" expr ")"
# comparison := IDENT (OP | contains) VALUE
# OP := == != >= <= > <
# VALUE := number | quoted string | bareword

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<LPAREN>\() |
        (?P<RPAREN>\)) |
        (?P<OP>==|!=|>=|<=|>|<) |
        (?P<KW>\bAND\b|\bOR\b|\bcontains\b) |
        (?P<NUMBER>-?\d+(?:\.\d+)?) |
        (?P<STRING>"([^"\\]|\\.)*"|'([^'\\]|\\.)*') |
        (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    )\s*
    """,
    re.VERBOSE | re.IGNORECASE
)

@dataclass(frozen=True)
class Token:
    kind: str
    value: str

class ParseError(ValueError):
    pass

def tokenize(s: str) -> List[Token]:
    """Tokenize an input string into Token objects.

    This is the first step of parsing: it recognizes numbers, identifiers,
    operators, parentheses, and quoted strings.
    """
    pos = 0
    out: List[Token] = []
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            raise ParseError(f"Unexpected character near: {s[pos:pos+20]!r}")
        pos = m.end()
        kind = None
        val = None
        for k, v in m.groupdict().items():
            if v is not None and k not in ("STRING",):
                kind = k
                val = v
                break
        if m.group("STRING") is not None:
            kind = "STRING"
            val = m.group("STRING")
        if kind is None:
            raise ParseError("Tokenizer error.")
        if kind == "KW":
            vnorm = val.lower()
            if vnorm in ("and", "or"):
                kind = vnorm.upper()
                val = vnorm.upper()
            else:
                kind = "CONTAINS"
                val = "contains"
        out.append(Token(kind=kind, value=val))
    return out

# AST nodes
@dataclass(frozen=True)
class Node: ...

@dataclass(frozen=True)
class And(Node):
    left: Node
    right: Node

@dataclass(frozen=True)
class Or(Node):
    left: Node
    right: Node

@dataclass(frozen=True)
class Cmp(Node):
    field: str
    op: str
    value: Any

def parse(expr: str) -> Node:
    toks = tokenize(expr)
    p = _Parser(toks)
    node = p.parse_expr()
    if not p.at_end():
        raise ParseError(f"Unexpected token: {p.peek().value}")
    return node

class _Parser:
    def __init__(self, toks: List[Token]) -> None:
        self.toks = toks
        self.i = 0

    def at_end(self) -> bool:
        return self.i >= len(self.toks)

    def peek(self) -> Token:
        return self.toks[self.i]

    def take(self, kind: str) -> Token:
        if self.at_end():
            raise ParseError(f"Expected {kind}, got end of input")
        t = self.peek()
        if t.kind != kind:
            raise ParseError(f"Expected {kind}, got {t.kind} ({t.value})")
        self.i += 1
        return t

    def match(self, *kinds: str) -> Optional[Token]:
        if self.at_end():
            return None
        if self.peek().kind in kinds:
            t = self.peek()
            self.i += 1
            return t
        return None

    def parse_expr(self) -> Node:
        node = self.parse_term()
        while self.match("OR"):
            rhs = self.parse_term()
            node = Or(node, rhs)
        return node

    def parse_term(self) -> Node:
        node = self.parse_factor()
        while self.match("AND"):
            rhs = self.parse_factor()
            node = And(node, rhs)
        return node

    def parse_factor(self) -> Node:
        if self.match("LPAREN"):
            node = self.parse_expr()
            self.take("RPAREN")
            return node
        return self.parse_comparison()

    def parse_comparison(self) -> Node:
        field = self.take("IDENT").value
        if self.match("CONTAINS"):
            op = "contains"
        else:
            op = self.take("OP").value
        val_tok = self.match("NUMBER", "STRING", "IDENT")
        if not val_tok:
            raise ParseError("Expected a value after operator")
        val = _coerce_value(val_tok)
        return Cmp(field=field, op=op, value=val)

def _coerce_value(tok: Token) -> Any:
    if tok.kind == "NUMBER":
        return float(tok.value) if "." in tok.value else int(tok.value)
    if tok.kind == "STRING":
        s = tok.value
        if s[0] == s[-1] and s[0] in ("'", '"'):
            s = s[1:-1]
        s = s.encode("utf-8").decode("unicode_escape")
        return s
    return tok.value
