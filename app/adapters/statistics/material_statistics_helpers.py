from __future__ import annotations

from typing import Any

MATERIAL_SUMMARY_FIELDS = (
    "project_material_quantity",
    "project_material_summ",
    "shift_report_material_quantity",
    "shift_report_material_summ_by_estimate",
)


def summarize_material_stats(stats: dict[str, dict[str, Any]]) -> dict[str, float]:
    return {
        field: sum(float(item.get(field, 0) or 0) for item in stats.values())
        for field in MATERIAL_SUMMARY_FIELDS
    }


def merge_material_stats(
    total: dict[str, dict[str, Any]], stats: dict[str, dict[str, Any]]
) -> None:
    for material_id, item in stats.items():
        if material_id not in total:
            total[material_id] = dict(item)
            continue
        for field in MATERIAL_SUMMARY_FIELDS:
            total[material_id][field] = float(total[material_id].get(field, 0) or 0) + float(
                item.get(field, 0) or 0
            )
        if total[material_id].get("material_name") is None:
            total[material_id]["material_name"] = item.get("material_name")
