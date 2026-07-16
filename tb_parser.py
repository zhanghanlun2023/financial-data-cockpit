from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
import xlrd


LAYOUTS = {
    2020: {"item_col": 0, "entity_cols": range(4, 23), "group_col": 25},
    2021: {"item_col": 0, "entity_cols": range(4, 17), "group_col": 19},
    2022: {"item_col": 0, "entity_cols": range(1, 15), "group_col": 17},
    2023: {"item_col": 0, "entity_cols": range(2, 17), "group_col": 19},
    2024: {"item_col": 2, "entity_cols": range(3, 15), "group_col": 17},
    2025: {"item_col": 0, "entity_cols": range(1, 12), "group_col": 14},
}

ENTITY_ALIASES = {
    "母公司合并": "母公司",
    "环科合并": "现代环投",
    "资产合并": "现代资产",
    "财富合并": "现代财富",
    "大有合并": "大有期货",
    "怀芷": "怀芷公司",
    "房地产合并": "现代房产",
    "房产合并": "现代房产",
    "农商行": "巴陵农商行",
    "湘衡": "湘衡高速",
    "新能源": "现代新能源",
    "弘远创投": "现代弘远",
    "长韶娄": "长韶娄公司",
    "溆怀": "溆怀公司",
    "小贷": "安迅小贷",
    "担保公司": "现代担保",
    "资产公司": "现代资产",
    "房产公司": "现代房产",
    "新能源公司": "现代新能源",
}

METRICS = {
    "资产总额": ("资产负债表", ["资产总计"]),
    "负债总额": ("资产负债表", ["负债合计"]),
    "营业收入": ("利润表", ["其中：营业收入"]),
    "营业成本": ("利润表", ["其中：营业成本"]),
    "利润总额": ("利润表", ["利润总额"]),
    "净利润": ("利润表", ["净利润"]),
    "经营现金净额": ("现金流量表", ["经营活动产生的现金流量净额"]),
    "现金净增加额": ("现金流量表", ["现金及现金等价物净增加额"]),
}


def clean_item(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", "", text)


def clean_entity(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^\d+[-—]", "", text)
    return ENTITY_ALIASES.get(text, text)


def as_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def section_for(item: str, current: str) -> str:
    if "利润表" in item:
        return "利润表"
    if "现金流量表" in item and "核对" not in item:
        return "现金流量表"
    if "资产负债表" in item or "负债和所有者权益表" in item:
        return "资产负债表"
    return current


def parse_tb(source: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    book = xlrd.open_workbook(str(source))
    records: list[dict] = []
    sheet_audit: list[dict] = []

    for sheet in book.sheets():
        year_match = re.search(r"20\d{2}", sheet.name)
        if not year_match:
            continue
        year = int(year_match.group())
        if year not in LAYOUTS:
            continue
        cfg = LAYOUTS[year]
        item_col = cfg["item_col"]
        group_col = cfg["group_col"]
        entity_columns = [(c, clean_entity(sheet.cell_value(0, c))) for c in cfg["entity_cols"]]
        entity_columns = [(c, name) for c, name in entity_columns if name]
        entity_columns.append((group_col, "集团审定口径"))

        current_section = "资产负债表"
        numeric_rows = 0
        for row in range(1, sheet.nrows):
            raw_item = str(sheet.cell_value(row, item_col) or "").strip()
            item = clean_item(raw_item)
            current_section = section_for(item, current_section)
            if not item or item in {"资产负债表", "利润表", "利润表：", "现金流量表", "现金流量表："}:
                continue
            for col, entity in entity_columns:
                value = as_number(sheet.cell_value(row, col))
                if value is None:
                    continue
                numeric_rows += 1
                records.append(
                    {
                        "year": year,
                        "section": current_section,
                        "row_no": row + 1,
                        "account": raw_item.strip(),
                        "account_key": item,
                        "entity": entity,
                        "scope": "集团" if entity == "集团审定口径" else "公司",
                        "value_yuan": value,
                        "value_wan": value / 10000,
                    }
                )
        sheet_audit.append(
            {
                "year": year,
                "sheet": sheet.name,
                "entities": len(entity_columns) - 1,
                "numeric_records": numeric_rows,
                "group_source": str(sheet.cell_value(0, group_col)).strip(),
            }
        )

    detail = pd.DataFrame(records)
    summary_rows: list[dict] = []
    for (year, entity), part in detail.groupby(["year", "entity"], sort=True):
        row = {"year": year, "entity": entity, "scope": "集团" if entity == "集团审定口径" else "公司"}
        for metric, (section, patterns) in METRICS.items():
            candidates = part[part["section"].eq(section)]
            match = pd.Series(False, index=candidates.index)
            for pattern in patterns:
                match |= candidates["account_key"].str.contains(pattern, regex=False)
            values = candidates.loc[match, "value_wan"]
            row[metric] = float(values.iloc[0]) if not values.empty else float("nan")
        if pd.notna(row.get("资产总额")) and pd.notna(row.get("负债总额")):
            row["所有者权益"] = row["资产总额"] - row["负债总额"]
            row["资产负债率"] = row["负债总额"] / row["资产总额"] if row["资产总额"] else float("nan")
        else:
            row["所有者权益"] = float("nan")
            row["资产负债率"] = float("nan")
        row["销售净利率"] = row["净利润"] / row["营业收入"] if row.get("营业收入") else float("nan")
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    group = summary[summary["scope"].eq("集团")].sort_values("year")
    audit = {
        "source_file": source.name,
        "years": sorted(detail["year"].unique().tolist()),
        "detail_records": int(len(detail)),
        "accounts": int(detail["account_key"].nunique()),
        "sheet_audit": sheet_audit,
        "group_metric_coverage": {
            col: int(group[col].notna().sum()) for col in METRICS
        },
        "balance_check_max_abs_wan": float(
            (group["资产总额"] - group["负债总额"] - group["所有者权益"]).abs().max()
        ),
    }
    return detail, summary, audit


def main() -> None:
    parser = argparse.ArgumentParser(description="将年度 TB 工作簿整理为财务驾驶舱数据集")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    detail, summary, audit = parse_tb(args.source)
    detail.to_csv(args.output / "tb_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(args.output / "tb_summary.csv", index=False, encoding="utf-8-sig")
    (args.output / "tb_quality.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
