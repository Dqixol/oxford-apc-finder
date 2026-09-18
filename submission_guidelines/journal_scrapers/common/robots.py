"""A correct, spec-compliant robots.txt matcher.

Python's stdlib `urllib.robotparser` does NOT implement wildcard ('*') or
end-anchor ('$') patterns -- it treats '*' as a literal character. This is a
real, silent correctness bug: `Disallow: /` followed by `Allow: /journal*`
(a very common real-world pattern -- e.g. link.springer.com's robots.txt)
gets misread as "everything disallowed", when the actual RFC 9309 / Google
robots.txt spec says the more specific `Allow: /journal*` should win for any
path starting with /journal. We hit this directly: it caused three genuinely
open Springer journal pages to be wrongly skipped as "disallowed".

This module implements the real algorithm: for a given path, find every
Allow/Disallow rule whose pattern matches, and the longest matching pattern
wins (ties go to Allow).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


def _compile_pattern(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
    if not anchored:
        regex += ".*"
    return re.compile("^" + regex + "$")


@dataclass
class _Rule:
    directive: str  # "allow" | "disallow"
    pattern: str
    regex: re.Pattern

    def matches(self, path: str) -> bool:
        return bool(self.regex.match(path))


def _parse_groups(text: str) -> dict[str, list[_Rule]]:
    """user-agent product token (lowercased) -> ordered list of rules."""
    groups: dict[str, list[_Rule]] = {}
    current_agents: list[str] = []
    group_open = False  # True while we're still accepting more User-agent lines into the current group

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            ua = value.lower()
            if not group_open:
                current_agents = []
            current_agents.append(ua)
            groups.setdefault(ua, [])
            group_open = True
        elif field in ("allow", "disallow") and current_agents:
            # An empty Disallow value is specifically defined (RFC 9309 / the
            # original robots.txt draft) to mean "no restrictions", not "match
            # the empty string" -- skip it rather than compiling a catch-all
            # pattern that would (wrongly) match every path.
            if field == "disallow" and value == "":
                group_open = False
                continue
            rule = _Rule(field, value, _compile_pattern(value))
            for ua in current_agents:
                groups[ua].append(rule)
            group_open = False
        else:
            group_open = False

    return groups


class Robots:
    def __init__(self, text: str):
        self._groups = _parse_groups(text)

    @classmethod
    def unreachable(cls) -> "Robots":
        """No robots.txt could be fetched -- default to allow, per RFC 9309."""
        return cls("")

    def _rules_for(self, product_token: str) -> list[_Rule]:
        token = product_token.lower()
        if token in self._groups:
            return self._groups[token]
        return self._groups.get("*", [])

    def can_fetch(self, user_agent: str, url: str) -> bool:
        product_token = user_agent.split("/")[0].strip()
        rules = self._rules_for(product_token)
        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        best: _Rule | None = None
        for rule in rules:
            if not rule.matches(path):
                continue
            if best is None or len(rule.pattern) > len(best.pattern):
                best = rule
            elif len(rule.pattern) == len(best.pattern) and rule.directive == "allow":
                best = rule  # ties go to Allow

        if best is None:
            return True
        return best.directive == "allow"
