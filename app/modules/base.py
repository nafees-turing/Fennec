from dataclasses import dataclass, field


@dataclass
class Finding:
    kind: str
    value: str
    source: str
    confidence: str
    evidence: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class ModuleResult:
    status: str
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class ModuleSpec:
    id: str
    title: str
    milestone: str
    summary: str
    input_label: str
    placeholder: str
    available: bool
    reason: str = ""
    input_kind: str = "text"
    network: bool = False

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "milestone": self.milestone,
            "summary": self.summary,
            "input_label": self.input_label,
            "placeholder": self.placeholder,
            "available": self.available,
            "reason": self.reason,
            "input_kind": self.input_kind,
            "network": self.network,
        }
