from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class TextContent:
    type: str = "text"
    text: str = ""


@dataclass
class Paragraph:
    type: str = "paragraph"
    content: List[TextContent] = field(default_factory=list)


@dataclass
class Description:
    type: str = "doc"
    version: int = 1
    content: List[Paragraph] = field(default_factory=list)


@dataclass
class JiraIssue:
    project: Dict[str, str]
    summary: str
    description: Description
    issueType: Dict[str, str] = field(default_factory=lambda: {"name": "Task"})
    priority: Dict[str, str] = field(default_factory=lambda: {"name": "Medium"})

    def to_json(self) -> Dict[str, Any]:
        return {"fields": asdict(self)}
