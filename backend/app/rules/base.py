from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class Finding:
    def __init__(
        self,
        rule_id: str,
        severity: int,
        category: str,
        title: str,
        description: str,
        location_start: Optional[int] = None,
        location_end: Optional[int] = None,
        auto_fixable: bool = False
    ):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.description = description
        self.location_start = location_start
        self.location_end = location_end
        self.auto_fixable = auto_fixable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "location_start": self.location_start,
            "location_end": self.location_end,
            "auto_fixable": self.auto_fixable
        }

class BaseRule(ABC):
    rule_id: str = ""
    severity: int = 1
    category: str = ""
    title: str = ""
    description: str = ""
    auto_fixable: bool = False

    @abstractmethod
    def analyze(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> Optional[List[Finding]]:
        """Run analysis on sqlglot AST and return list of findings."""
        pass

    def create_finding(self, description: str, location_start: Optional[int] = None, location_end: Optional[int] = None) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            category=self.category,
            title=self.title,
            description=description or self.description,
            location_start=location_start,
            location_end=location_end,
            auto_fixable=self.auto_fixable
        )

class RuleRegistry:
    def __init__(self):
        self.rules: List[BaseRule] = []

    def register(self, rule: BaseRule):
        self.rules.append(rule)

    def run_all(self, ast: Any, schema_context: Optional[Dict[str, Any]] = None) -> List[Finding]:
        all_findings = []
        for rule in self.rules:
            try:
                findings = rule.analyze(ast, schema_context)
                if findings:
                    all_findings.extend(findings)
            except Exception:
                # Silently ignore rule failures to ensure pipeline robustness
                pass
        return all_findings

# Global rule registry
registry = RuleRegistry()
