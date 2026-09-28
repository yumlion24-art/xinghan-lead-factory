from __future__ import annotations

from urllib.robotparser import RobotFileParser


class RobotsPolicy:
    def __init__(self, parser: RobotFileParser) -> None:
        self._parser = parser

    @classmethod
    def from_text(cls, text: str) -> RobotsPolicy:
        parser = RobotFileParser()
        parser.parse(text.splitlines())
        return cls(parser)

    def allowed(self, user_agent: str, url: str) -> bool:
        return self._parser.can_fetch(user_agent, url)

