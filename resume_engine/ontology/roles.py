from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, Field

class Competency(BaseModel):
    name: str
    weight: float
    description: str

class RoleGraph(BaseModel):
    role_id: str
    label: str
    competencies: list[Competency]


def load_role_graphs(config_dir: str | Path | None=None) -> dict[str,RoleGraph]:
    root=Path(config_dir) if config_dir else Path(__file__).resolve().parents[1]/"config"
    raw=yaml.safe_load((root/"roles.yaml").read_text())["roles"]
    out={}
    for rid,spec in raw.items():
        comps=[Competency(name=k,weight=float(v["weight"]),description=v["description"]) for k,v in spec["competencies"].items()]
        total=sum(c.weight for c in comps)
        if abs(total-1)>1e-6: raise ValueError(f"Role {rid} weights sum to {total}, expected 1.0")
        out[rid]=RoleGraph(role_id=rid,label=spec["label"],competencies=comps)
    return out
