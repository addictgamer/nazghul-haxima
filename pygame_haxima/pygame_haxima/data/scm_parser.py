from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Symbol:
    name: str

    def __str__(self) -> str:
        return self.name


Expr = list["Expr"] | Symbol | str | int | float | bool | None


class ScmParseError(ValueError):
    pass


class ScmParser:
    def parse_text(self, text: str) -> list[Expr]:
        tokens = self._tokenize(text)
        expressions: list[Expr] = []
        idx = 0
        while idx < len(tokens):
            expr, idx = self._parse_expr(tokens, idx)
            expressions.append(expr)
        return expressions

    def parse_file(self, content: str) -> list[Expr]:
        return self.parse_text(content)

    def _tokenize(self, text: str) -> list[str]:
        tokens: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c in {" ", "\t", "\r", "\n"}:
                i += 1
                continue
            if c == ";":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            if c in {"(", ")", "'"}:
                tokens.append(c)
                i += 1
                continue
            if c == '"':
                i += 1
                out: list[str] = []
                while i < n:
                    ch = text[i]
                    if ch == "\\" and i + 1 < n:
                        out.append(text[i + 1])
                        i += 2
                        continue
                    if ch == '"':
                        i += 1
                        break
                    out.append(ch)
                    i += 1
                else:
                    raise ScmParseError("Unterminated string literal")
                tokens.append('"' + "".join(out) + '"')
                continue
            start = i
            while i < n and text[i] not in {" ", "\t", "\r", "\n", "(", ")", ";", "'"}:
                i += 1
            tokens.append(text[start:i])
        return tokens

    def _parse_expr(self, tokens: list[str], idx: int) -> tuple[Expr, int]:
        if idx >= len(tokens):
            raise ScmParseError("Unexpected EOF")
        token = tokens[idx]
        if token == "(":
            idx += 1
            out: list[Expr] = []
            while idx < len(tokens) and tokens[idx] != ")":
                expr, idx = self._parse_expr(tokens, idx)
                out.append(expr)
            if idx >= len(tokens):
                raise ScmParseError("Missing closing ')'")
            return out, idx + 1
        if token == ")":
            raise ScmParseError("Unexpected ')'")
        if token == "'":
            quoted, next_idx = self._parse_expr(tokens, idx + 1)
            return [Symbol("quote"), quoted], next_idx
        return self._parse_atom(token), idx + 1

    def _parse_atom(self, token: str) -> Expr:
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1]
        if token == "#t":
            return True
        if token == "#f":
            return False
        if token == "nil":
            return None
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        return Symbol(token)
