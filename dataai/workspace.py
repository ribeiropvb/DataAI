"""Pasta da análise e manifesto (specs 16.3 P-009, skills/README.md).

Estrutura::

    analyses/<analysis_id>/
      manifest.json  originals/  working/  results/  charts/
      deliverables/v<N>/  review/  execution_summary.md
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

SUBDIRS = ("originals", "working", "results", "charts", "deliverables", "review", "skill_outputs")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _json_default(o: Any):
    try:
        import numpy as np
        import pandas as pd
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (pd.Timestamp, _dt.date, _dt.datetime)):
            return o.isoformat()
        if isinstance(o, pd.Period):
            return str(o)
        if o is pd.NaT:
            return None
    except ImportError:  # pragma: no cover
        pass
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def dump_json(obj: Any, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(_clean_nan(obj), ensure_ascii=False, indent=2, default=_json_default)
    Path(path).write_text(text, encoding="utf-8")


def _clean_nan(obj: Any):
    import math
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_nan(v) for v in obj]
    try:
        import numpy as np
        if isinstance(obj, np.floating) and not np.isfinite(obj):
            return None
    except ImportError:  # pragma: no cover
        pass
    return obj


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Workspace:
    """Uma análise = uma pasta. Tudo o que a análise usa ou produz fica associado no manifesto."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.manifest_path = self.root / "manifest.json"
        self.manifest: dict = load_json(self.manifest_path) if self.manifest_path.exists() else {}

    # ---------- criação ----------
    @classmethod
    def create(cls, base_dir: str | Path, files: list[str | Path], question: str | None = None,
               output_mode: str = "both", analysis_id: str | None = None,
               source_labels: dict[str, str] | None = None) -> "Workspace":
        analysis_id = analysis_id or _dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        root = Path(base_dir) / analysis_id
        if root.exists():
            raise FileExistsError(root)
        for d in SUBDIRS:
            (root / d).mkdir(parents=True, exist_ok=True)
        ws = cls(root)
        ws.manifest = {
            "analysis_id": analysis_id,
            "created_at": now_iso(),
            "request": {
                "question": question,
                "analysis_mode": "directed" if question else "exploratory",
                "output_mode": output_mode,
                "clarifications": [],
            },
            "files": [],
            "datasets": [],
            "treatments": [],
            "metrics": [],
            "results": {},
            "charts": {},
            "deliverables": [],
            "reviews": [],
            "assumptions": [],
            "warnings": [],
            "llm_usage": [],
            "status": "created",
        }
        source_labels = source_labels or {}
        for f in files:
            src = Path(f)
            dst = root / "originals" / src.name
            if dst.exists():
                dst = root / "originals" / f"{src.stem}_{uuid.uuid4().hex[:4]}{src.suffix}"
            shutil.copy2(src, dst)
            ws.manifest["files"].append({
                "file": f"originals/{dst.name}",
                "original_name": src.name,
                "sha256": sha256_file(dst),
                "bytes": dst.stat().st_size,
                "source_label": source_labels.get(src.name, src.stem),
                "received_at": now_iso(),
            })
        ws.save()
        return ws

    # ---------- utilidades ----------
    def path(self, rel: str | Path) -> Path:
        return self.root / rel

    def rel(self, p: str | Path) -> str:
        return str(Path(p).resolve().relative_to(self.root.resolve())).replace("\\", "/")

    def save(self) -> None:
        dump_json(self.manifest, self.manifest_path)

    def write_json(self, rel: str, obj: Any) -> str:
        dump_json(obj, self.root / rel)
        return rel

    def read_json(self, rel: str) -> Any:
        return load_json(self.root / rel)

    # ---------- histórico ----------
    def add_treatment(self, kind: str, description: str, dataset_ids: list[str],
                      details: dict | None = None, requires_authorization: bool = False,
                      authorized_by: str | None = None) -> dict:
        t = {
            "treatment_id": f"t{len(self.manifest['treatments']) + 1:03d}",
            "kind": kind,
            "description": description,
            "dataset_ids": dataset_ids,
            "details": details or {},
            "requires_authorization": requires_authorization,
            "authorized_by": authorized_by,
            "executed_at": now_iso(),
        }
        self.manifest["treatments"].append(t)
        self.save()
        return t

    def register_dataset(self, meta: dict) -> None:
        self.manifest["datasets"] = [d for d in self.manifest["datasets"]
                                     if d["dataset_id"] != meta["dataset_id"]] + [meta]
        self.save()

    def dataset_meta(self, dataset_id: str) -> dict:
        for d in self.manifest["datasets"]:
            if d["dataset_id"] == dataset_id:
                return d
        raise KeyError(f"dataset desconhecido: {dataset_id}")

    def load_dataset(self, dataset_id: str):
        import pandas as pd
        return pd.read_parquet(self.root / self.dataset_meta(dataset_id)["working_path"])

    def save_result(self, result: dict) -> str:
        rid = result["result_id"]
        versions = self.manifest["results"].setdefault(rid, [])
        version = len(versions) + 1
        result["version"] = version
        rel = f"results/{rid}.v{version}.json"
        dump_json(result, self.root / rel)
        dump_json(result, self.root / f"results/{rid}.json")  # cópia "atual"
        versions.append({"version": version, "path": rel, "created_at": now_iso()})
        self.save()
        return rel

    def load_result(self, result_id: str) -> dict:
        return load_json(self.root / f"results/{result_id}.json")

    def list_results(self) -> list[str]:
        return sorted(self.manifest["results"])

    def save_chart(self, spec: dict) -> str:
        cid = spec["chart_id"]
        versions = self.manifest["charts"].setdefault(cid, [])
        spec["version"] = len(versions) + 1
        rel = f"charts/{cid}.json"
        dump_json(spec, self.root / rel)
        dump_json(spec, self.root / f"charts/{cid}.v{spec['version']}.json")
        versions.append({"version": spec["version"], "path": rel})
        self.save()
        return rel

    def deliverable_dir(self, version: int) -> Path:
        d = self.root / "deliverables" / f"v{version}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def next_deliverable_version(self) -> int:
        vs = [d["version"] for d in self.manifest["deliverables"]]
        return (max(vs) + 1) if vs else 1

    def add_deliverable(self, kind: str, path: str | Path, version: int, extra: dict | None = None) -> dict:
        p = Path(path)
        rec = {"kind": kind, "artifact_ref": self.rel(p), "version": version,
               "sha256": sha256_file(p), "created_at": now_iso(), **(extra or {})}
        # regerar a mesma entrega na mesma versão substitui o registro (o arquivo foi sobrescrito)
        self.manifest["deliverables"] = [d for d in self.manifest["deliverables"]
                                         if not (d["kind"] == kind and d["version"] == version)] + [rec]
        self.save()
        return rec

    def latest_deliverable(self, kind: str) -> dict | None:
        items = [d for d in self.manifest["deliverables"] if d["kind"] == kind]
        return max(items, key=lambda d: d["version"]) if items else None

    def save_skill_output(self, env: dict, tag: str | None = None) -> str:
        name = env.get("skill_name", "unknown")
        n = len(list((self.root / "skill_outputs").glob(f"{name}*.json"))) + 1
        rel = f"skill_outputs/{name}{'_' + tag if tag else ''}.{n}.json"
        dump_json(env, self.root / rel)
        for w in env.get("warnings", []):
            self.manifest["warnings"].append({**w, "skill": name})
        self.save()
        return rel

    def add_usage(self, agent: str, usage: dict) -> None:
        self.manifest["llm_usage"].append({"agent": agent, **usage, "at": now_iso()})
        self.save()
