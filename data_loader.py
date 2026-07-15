from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


FLOW_METRICS = [
    "营业收入",
    "营业成本",
    "销售费用",
    "管理费用",
    "研发费用",
    "财务费用",
    "其他收益",
    "利润总额",
    "净利润",
    "经营活动现金流",
    "预算营业收入",
    "预算利润总额",
]

BALANCE_METRICS = ["应收账款", "存货", "资产总额", "负债总额", "所有者权益"]


@st.cache_data(show_spinner=False)
def load_data(data_dir: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    folder = Path(data_dir)
    monthly = pd.read_csv(folder / "financial_monthly.csv", parse_dates=["日期"])
    benchmark = pd.read_csv(folder / "industry_benchmark_monthly.csv", parse_dates=["日期"])
    definitions = pd.read_csv(folder / "metric_definitions.csv")
    return monthly, benchmark, definitions


def aggregate_period(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=group_cols + FLOW_METRICS + BALANCE_METRICS)
    ordered = df.sort_values("日期")
    flow = ordered.groupby(group_cols, as_index=False)[FLOW_METRICS].sum()
    balances = ordered.groupby(group_cols, as_index=False)[BALANCE_METRICS].last()
    result = flow.merge(balances, on=group_cols, how="left")
    result["利润率"] = result["利润总额"] / result["营业收入"].replace(0, pd.NA)
    result["收入预算完成率"] = result["营业收入"] / result["预算营业收入"].replace(0, pd.NA)
    result["利润预算完成率"] = result["利润总额"] / result["预算利润总额"].replace(0, pd.NA)
    result["经营现金质量"] = result["经营活动现金流"] / result["净利润"].replace(0, pd.NA)
    result["资产负债率"] = result["负债总额"] / result["资产总额"].replace(0, pd.NA)
    result["净资产收益率"] = result["净利润"] / result["所有者权益"].replace(0, pd.NA)
    return result


def comparison_delta(current: float, previous: float) -> float:
    if previous == 0 or pd.isna(previous):
        return 0.0
    return current / previous - 1
