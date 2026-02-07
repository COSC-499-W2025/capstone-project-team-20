from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class ResumeVariantManager:
    """
    Stores base resume snapshot + edited variants in ConfigManager.

    Config key:
      resume_variants -> List[{
        report_id, title, created_at,
        base_context: {...},
        variants: [{ variant_id, label, created_at, context }]
      }]
    """

    KEY = "resume_variants"

    def __init__(self, config_manager):
        self.config = config_manager

    def _load(self) -> List[Dict[str, Any]]:
        data = self.config.get(self.KEY, [])
        return data if isinstance(data, list) else []

    def _save(self, data: List[Dict[str, Any]]) -> None:
        self.config.set(self.KEY, data)

    def get_resume_entry(self, report_id: int) -> Optional[Dict[str, Any]]:
        data = self._load()
        return next((r for r in data if r.get("report_id") == report_id), None)

    def ensure_base_snapshot(
        self,
        report_id: int,
        title: str,
        base_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        data = self._load()
        existing = next((r for r in data if r.get("report_id") == report_id), None)
        if existing:
            return existing

        entry = {
            "report_id": report_id,
            "title": title,
            "created_at": _now_str(),
            "base_context": base_context,
            "variants": [],
        }
        data.append(entry)
        self._save(data)
        return entry

    def list_variants(self, report_id: int) -> List[Dict[str, Any]]:
        entry = self.get_resume_entry(report_id)
        if not entry:
            return []
        variants = entry.get("variants", [])
        return variants if isinstance(variants, list) else []

    def create_variant(
        self,
        report_id: int,
        label: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        data = self._load()
        entry = next((r for r in data if r.get("report_id") == report_id), None)
        if not entry:
            raise ValueError(f"No base resume snapshot exists for report_id={report_id}")

        variants = entry.get("variants", [])
        if not isinstance(variants, list):
            variants = []

        next_id = max((v.get("variant_id", 0) for v in variants), default=0) + 1
        variant = {
            "variant_id": next_id,
            "label": label,
            "created_at": _now_str(),
            "context": context,
        }
        variants.append(variant)
        entry["variants"] = variants
        self._save(data)
        return variant

    def get_variant(self, report_id: int, variant_id: int) -> Optional[Dict[str, Any]]:
        variants = self.list_variants(report_id)
        return next((v for v in variants if v.get("variant_id") == variant_id), None)
