from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

COMPANIES = [
    {"公司": "长永高速", "板块": "高速运营", "规模": 1.18, "利润率": 0.32},
    {"公司": "怀芷高速", "板块": "高速运营", "规模": 0.96, "利润率": 0.29},
    {"公司": "现代财富", "板块": "金融服务", "规模": 0.72, "利润率": 0.22},
    {"公司": "大有期货", "板块": "金融服务", "规模": 0.83, "利润率": 0.18},
    {"公司": "现代新能源", "板块": "新能源", "规模": 0.58, "利润率": 0.16},
    {"公司": "现代资产", "板块": "资产经营", "规模": 0.66, "利润率": 0.20},
]


def build_monthly(seed: int = 20260715) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = pd.date_range("2023-01-01", "2026-06-01", freq="MS")
    rows: list[dict] = []

    for company_index, company in enumerate(COMPANIES):
        asset_base = 170_000 * company["规模"] + 22_000 * company_index
        equity_base = asset_base * (0.48 + 0.03 * rng.random())
        receivable_base = 8_500 * company["规模"]
        inventory_base = 4_500 * company["规模"]

        for month_index, date in enumerate(months):
            year_no = date.year - 2023
            seasonality = 1 + 0.10 * np.sin((date.month - 2) / 12 * 2 * np.pi)
            year_growth = (1.055 + company_index * 0.003) ** year_no
            shock = 1 + rng.normal(0, 0.045)
            base_revenue = 8_800 * company["规模"]
            revenue = base_revenue * seasonality * year_growth * shock
            budget_revenue = base_revenue * seasonality * (1.06**year_no) * (1.02 + 0.008 * year_no)

            gross_margin = np.clip(0.52 + company["利润率"] * 0.28 + rng.normal(0, 0.018), 0.42, 0.69)
            operating_cost = revenue * (1 - gross_margin)
            selling_expense = revenue * np.clip(0.032 + rng.normal(0, 0.004), 0.02, 0.05)
            admin_expense = revenue * np.clip(0.095 + rng.normal(0, 0.008), 0.07, 0.13)
            rd_expense = revenue * np.clip(0.020 + (0.025 if company["板块"] == "新能源" else 0) + rng.normal(0, 0.004), 0.01, 0.06)
            finance_expense = revenue * np.clip(0.027 + 0.004 * company_index + rng.normal(0, 0.005), 0.012, 0.055)
            other_income = revenue * np.clip(0.018 + rng.normal(0, 0.006), 0.003, 0.04)
            total_profit = revenue - operating_cost - selling_expense - admin_expense - rd_expense - finance_expense + other_income
            net_profit = total_profit * np.clip(0.78 + rng.normal(0, 0.018), 0.72, 0.83)
            budget_profit = budget_revenue * company["利润率"] * (1.00 + 0.012 * year_no)
            operating_cash_flow = net_profit * np.clip(1.03 + rng.normal(0, 0.24), 0.42, 1.55)

            asset_growth = (1.045**year_no) * (1 + 0.0025 * month_index)
            total_assets = asset_base * asset_growth * (1 + rng.normal(0, 0.009))
            debt_ratio = np.clip(0.50 + 0.025 * company_index - 0.008 * year_no + rng.normal(0, 0.008), 0.42, 0.68)
            total_liabilities = total_assets * debt_ratio
            equity = max(total_assets - total_liabilities, equity_base)
            accounts_receivable = receivable_base * year_growth * np.clip(1 + rng.normal(0, 0.11), 0.72, 1.35)
            inventory = inventory_base * year_growth * np.clip(1 + rng.normal(0, 0.10), 0.75, 1.30)

            rows.append(
                {
                    "日期": date.strftime("%Y-%m-%d"),
                    "年度": date.year,
                    "月份": date.month,
                    "季度": f"Q{(date.month - 1) // 3 + 1}",
                    "公司": company["公司"],
                    "板块": company["板块"],
                    "营业收入": round(revenue, 2),
                    "营业成本": round(operating_cost, 2),
                    "销售费用": round(selling_expense, 2),
                    "管理费用": round(admin_expense, 2),
                    "研发费用": round(rd_expense, 2),
                    "财务费用": round(finance_expense, 2),
                    "其他收益": round(other_income, 2),
                    "利润总额": round(total_profit, 2),
                    "净利润": round(net_profit, 2),
                    "经营活动现金流": round(operating_cash_flow, 2),
                    "预算营业收入": round(budget_revenue, 2),
                    "预算利润总额": round(budget_profit, 2),
                    "应收账款": round(accounts_receivable, 2),
                    "存货": round(inventory, 2),
                    "资产总额": round(total_assets, 2),
                    "负债总额": round(total_liabilities, 2),
                    "所有者权益": round(equity, 2),
                }
            )
    return pd.DataFrame(rows)


def build_benchmark(monthly: pd.DataFrame, seed: int = 20260716) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    grouped = (
        monthly.groupby(["日期", "年度", "月份", "季度", "板块"], as_index=False)
        .agg(
            营业收入=("营业收入", "mean"),
            利润总额=("利润总额", "mean"),
            净利润=("净利润", "mean"),
            经营活动现金流=("经营活动现金流", "mean"),
            资产总额=("资产总额", "mean"),
            负债总额=("负债总额", "mean"),
        )
    )
    multiplier = rng.normal(1.03, 0.035, len(grouped))
    grouped["行业营业收入中位数"] = grouped["营业收入"] * multiplier
    grouped["行业利润率中位数"] = (grouped["利润总额"] / grouped["营业收入"]).clip(0.08, 0.38) * rng.normal(0.98, 0.035, len(grouped))
    grouped["行业现金质量中位数"] = (grouped["经营活动现金流"] / grouped["净利润"]).clip(0.45, 1.65) * rng.normal(1.0, 0.04, len(grouped))
    grouped["行业资产负债率中位数"] = (grouped["负债总额"] / grouped["资产总额"]).clip(0.35, 0.72) * rng.normal(1.0, 0.025, len(grouped))
    return grouped[
        [
            "日期",
            "年度",
            "月份",
            "季度",
            "板块",
            "行业营业收入中位数",
            "行业利润率中位数",
            "行业现金质量中位数",
            "行业资产负债率中位数",
        ]
    ].round(4)


def build_metric_definitions() -> pd.DataFrame:
    rows = [
        ("营业收入", "流量指标", "各公司选定期间营业收入之和", "万元"),
        ("利润总额", "流量指标", "营业收入减成本费用并加其他收益", "万元"),
        ("利润率", "派生指标", "利润总额÷营业收入", "%"),
        ("预算完成率", "派生指标", "实际值÷预算值", "%"),
        ("经营现金质量", "派生指标", "经营活动现金流÷净利润", "倍"),
        ("资产负债率", "时点指标", "期末负债总额÷期末资产总额", "%"),
        ("应收账款", "时点指标", "选定期间最后一个月期末余额", "万元"),
        ("存货", "时点指标", "选定期间最后一个月期末余额", "万元"),
    ]
    return pd.DataFrame(rows, columns=["指标", "指标类型", "口径", "单位"])


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    monthly = build_monthly()
    benchmark = build_benchmark(monthly)
    definitions = build_metric_definitions()
    monthly.to_csv(DATA_DIR / "financial_monthly.csv", index=False, encoding="utf-8-sig")
    benchmark.to_csv(DATA_DIR / "industry_benchmark_monthly.csv", index=False, encoding="utf-8-sig")
    definitions.to_csv(DATA_DIR / "metric_definitions.csv", index=False, encoding="utf-8-sig")
    print(f"generated {len(monthly)} financial rows and {len(benchmark)} benchmark rows")


if __name__ == "__main__":
    main()
