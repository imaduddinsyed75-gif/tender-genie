from typing import Literal

from pydantic import BaseModel, model_validator


class ComplianceItem(BaseModel):
    clause: str
    category: str
    risk_level: Literal["RED", "YELLOW", "GREEN"]
    mitigation: str
    page: int
    excerpt: str


class BOQItem(BaseModel):
    item: str
    qty: float
    unit_cost: float
    margin_pct: float
    total: float

    @model_validator(mode="after")
    def compute_total(self) -> "BOQItem":
        self.total = self.qty * self.unit_cost * (1 + self.margin_pct / 100)
        return self
