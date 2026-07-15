from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data_loader import BALANCE_METRICS, FLOW_METRICS, aggregate_period, comparison_delta, load_data


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

BLUE = "#2563EB"
BLUE_LIGHT = "#93B4F6"
ORANGE = "#E8792E"
GOLD = "#D7A61D"
INK = "#263247"
MUTED = "#758197"
GRID = "#DDE4EE"
PALETTE = [BLUE, ORANGE, GOLD, "#6B7A99", "#9A6FB0", "#4F8A8B"]


st.set_page_config(page_title="财务数据驾驶舱", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #F5F7FB; }
    [data-testid="stSidebar"] { background: #EAF0F8; border-right: 1px solid #D6DFEC; }
    .hero {
        padding: 1.45rem 1.55rem; border-radius: 18px;
        background: linear-gradient(120deg, #17233D 0%, #243C6B 70%, #2D5796 100%);
        color: white; margin-bottom: 1rem; box-shadow: 0 10px 28px rgba(29, 52, 91, .16);
    }
    .hero h1 { margin: 0; font-size: 2rem; font-weight: 700; }
    .hero p { margin: .45rem 0 0; color: #D9E4F5; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #E0E6EF; border-radius: 14px;
        padding: .8rem 1rem; box-shadow: 0 4px 14px rgba(35, 55, 90, .05);
    }
    [data-testid="stMetricLabel"] { color: #66738A; }
    [data-testid="stMetricValue"] { color: #1D2B45; }
    .section-label { color:#65738A; font-size:.82rem; letter-spacing:.08em; text-transform:uppercase; margin-top:.7rem; }
    .source-note { color:#6F7C91; font-size:.82rem; }
    div[data-testid="stTabs"] button { font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    if abs(value) >= 100_000:
        return f"{value / 10_000:,.2f} 亿元"
    return f"{value:,.0f} 万元"


def pct(value: float) -> str:
    return f"{value:.1%}" if pd.notna(value) else "—"


def times(value: float) -> str:
    return f"{value:.2f} 倍" if pd.notna(value) else "—"


def signed_pct(value: float) -> str:
    return f"{value:+.1%}"


def style_figure(fig: go.Figure, height: int = 390) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=55, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, family="Arial, Microsoft YaHei, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_color=INK),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=MUTED))
    return fig


def portfolio_summary(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {metric: 0.0 for metric in FLOW_METRICS + BALANCE_METRICS}
    result = {metric: float(frame[metric].sum()) for metric in FLOW_METRICS}
    latest_balances = frame.sort_values("日期").groupby("公司", as_index=False)[BALANCE_METRICS].last()
    result.update({metric: float(latest_balances[metric].sum()) for metric in BALANCE_METRICS})
    result["利润率"] = result["利润总额"] / result["营业收入"] if result["营业收入"] else 0
    result["收入预算完成率"] = result["营业收入"] / result["预算营业收入"] if result["预算营业收入"] else 0
    result["利润预算完成率"] = result["利润总额"] / result["预算利润总额"] if result["预算利润总额"] else 0
    result["经营现金质量"] = result["经营活动现金流"] / result["净利润"] if result["净利润"] else 0
    result["资产负债率"] = result["负债总额"] / result["资产总额"] if result["资产总额"] else 0
    return result


def filtered_frame(source: pd.DataFrame, companies: list[str], sectors: list[str]) -> pd.DataFrame:
    return source[source["公司"].isin(companies) & source["板块"].isin(sectors)].copy()


try:
    monthly, benchmark, definitions = load_data(str(DATA_DIR))
except FileNotFoundError:
    st.error("未找到数据文件。请先运行 generate_mock_data.py 生成 data 目录中的 CSV 文件。")
    st.stop()

all_years = sorted(monthly["年度"].unique().tolist())
all_companies = sorted(monthly["公司"].unique().tolist())
all_sectors = sorted(monthly["板块"].unique().tolist())

with st.sidebar:
    st.header("全局筛选")
    year_range = st.select_slider("分析年度范围", options=all_years, value=(all_years[0], all_years[-1]))
    selected_sectors = st.multiselect("业务板块", all_sectors, default=all_sectors)
    available_companies = sorted(monthly[monthly["板块"].isin(selected_sectors)]["公司"].unique().tolist())
    selected_companies = st.multiselect("公司", available_companies, default=available_companies)
    comparison = st.selectbox("默认比较口径", ["预算", "上年同期", "行业中位数"])
    st.divider()
    st.caption("数据口径：金额单位为万元；资产负债类指标取期末余额。")
    st.caption("当前为确定性模拟数据，可直接替换 CSV 文件。")

if not selected_sectors or not selected_companies:
    st.warning("请至少选择一个业务板块和一家公司。")
    st.stop()

base = filtered_frame(monthly, selected_companies, selected_sectors)
in_range = base[base["年度"].between(year_range[0], year_range[1])].copy()
latest_year = int(in_range["年度"].max())
latest_month = int(in_range[in_range["年度"] == latest_year]["月份"].max())

current_ytd = base[(base["年度"] == latest_year) & (base["月份"] <= latest_month)]
previous_ytd = base[(base["年度"] == latest_year - 1) & (base["月份"] <= latest_month)]
current = portfolio_summary(current_ytd)
previous = portfolio_summary(previous_ytd)

st.markdown(
    f"""
    <div class="hero">
      <h1>财务数据驾驶舱</h1>
      <p>月度经营监测 · 季度复盘 · 年度趋势 · 预算与行业对标｜模拟数据截至 {latest_year} 年 {latest_month} 月</p>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3 = st.columns(3)
k1.metric("营业收入（年累计）", money(current["营业收入"]), signed_pct(comparison_delta(current["营业收入"], previous["营业收入"])))
k2.metric("利润总额（年累计）", money(current["利润总额"]), signed_pct(comparison_delta(current["利润总额"], previous["利润总额"])))
k3.metric("利润率", pct(current["利润率"]), f"同比 {comparison_delta(current['利润率'], previous['利润率']):+.1%}")
k4, k5, k6 = st.columns(3)
k4.metric("收入预算完成率", pct(current["收入预算完成率"]), f"预算 {money(current['预算营业收入'])}")
k5.metric("经营现金质量", times(current["经营现金质量"]), "经营现金流 / 净利润")
k6.metric("资产负债率", pct(current["资产负债率"]), f"同比 {current['资产负债率'] - previous['资产负债率']:+.1%}", delta_color="inverse")

overview_tab, month_tab, quarter_tab, annual_tab, benchmark_tab = st.tabs(
    ["经营总览", "月度分析", "季度分析", "年度分析", "对标分析"]
)

with overview_tab:
    st.markdown('<div class="section-label">趋势与经营质量</div>', unsafe_allow_html=True)
    trend = aggregate_period(in_range, ["日期"]).sort_values("日期")
    left, right = st.columns([1.5, 1])
    with left:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend["日期"], y=trend["营业收入"], name="营业收入", mode="lines+markers", line=dict(color=BLUE, width=3)))
        fig.add_trace(go.Scatter(x=trend["日期"], y=trend["预算营业收入"], name="收入预算", mode="lines", line=dict(color=INK, width=2, dash="dot")))
        fig.update_layout(title="月度营业收入与预算", yaxis_title="万元")
        st.plotly_chart(style_figure(fig, 400), use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend["日期"], y=trend["利润率"], name="利润率", mode="lines+markers", line=dict(color=ORANGE, width=3)))
        fig.add_hline(y=float(trend["利润率"].median()), line_dash="dot", line_color=INK, annotation_text="期间中位数")
        fig.update_layout(title="月度利润率", yaxis_title="利润率", yaxis_tickformat=".0%")
        st.plotly_chart(style_figure(fig, 400), use_container_width=True, config={"displayModeBar": False})

    ytd_company = aggregate_period(current_ytd, ["公司", "板块"])
    ytd_company["预算差额"] = ytd_company["营业收入"] - ytd_company["预算营业收入"]
    ytd_company["预算差异率"] = ytd_company["预算差额"] / ytd_company["预算营业收入"]
    left, right = st.columns([1.15, 1])
    with left:
        ranked = ytd_company.sort_values("预算差异率")
        fig = go.Figure(go.Bar(
            x=ranked["预算差异率"], y=ranked["公司"], orientation="h",
            marker_color=[ORANGE if value < 0 else BLUE for value in ranked["预算差异率"]],
            text=[f"{value:+.1%}" for value in ranked["预算差异率"]], textposition="outside",
            hovertemplate="%{y}<br>预算差异率 %{x:.1%}<extra></extra>",
        ))
        fig.add_vline(x=0, line_color=INK, line_width=1)
        fig.update_layout(title=f"{latest_year} 年累计收入预算差异", xaxis_tickformat=".0%")
        st.plotly_chart(style_figure(fig, 390), use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = px.scatter(
            ytd_company,
            x="利润率",
            y="经营现金质量",
            size="营业收入",
            color="板块",
            hover_name="公司",
            text="公司",
            color_discrete_sequence=PALETTE,
        )
        fig.update_traces(textposition="top center", marker=dict(line=dict(color="white", width=1)))
        fig.add_hline(y=1, line_dash="dot", line_color=INK)
        fig.update_layout(title="公司盈利能力与现金质量", xaxis_tickformat=".0%", xaxis_title="利润率", yaxis_title="经营现金流 / 净利润")
        st.plotly_chart(style_figure(fig, 390), use_container_width=True, config={"displayModeBar": False})

with month_tab:
    selected_month_year = st.selectbox("月度分析年度", sorted(in_range["年度"].unique(), reverse=True), key="month_year")
    month_view = in_range[in_range["年度"] == selected_month_year]
    month_total = aggregate_period(month_view, ["日期", "月份"]).sort_values("日期")
    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=month_total["月份"], y=month_total["营业收入"], name="营业收入", marker_color=BLUE))
        fig.add_trace(go.Scatter(x=month_total["月份"], y=month_total["预算营业收入"], name="预算", line=dict(color=INK, dash="dot", width=2), mode="lines+markers"))
        fig.update_layout(title=f"{selected_month_year} 年月度收入", xaxis_title="月份", yaxis_title="万元")
        st.plotly_chart(style_figure(fig), use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=month_total["月份"], y=month_total["利润总额"], name="利润总额", marker_color=ORANGE))
        fig.add_trace(go.Scatter(x=month_total["月份"], y=month_total["预算利润总额"], name="利润预算", line=dict(color=INK, dash="dot", width=2), mode="lines+markers"))
        fig.update_layout(title=f"{selected_month_year} 年月度利润", xaxis_title="月份", yaxis_title="万元")
        st.plotly_chart(style_figure(fig), use_container_width=True, config={"displayModeBar": False})

    cost_cols = ["营业成本", "销售费用", "管理费用", "研发费用", "财务费用"]
    cost_long = month_total.melt(id_vars=["月份"], value_vars=cost_cols, var_name="成本费用", value_name="金额")
    fig = px.bar(cost_long, x="月份", y="金额", color="成本费用", color_discrete_sequence=PALETTE, barmode="stack")
    fig.update_layout(title="月度成本费用构成", xaxis_title="月份", yaxis_title="万元")
    st.plotly_chart(style_figure(fig, 410), use_container_width=True, config={"displayModeBar": False})

    detail = aggregate_period(month_view, ["日期", "公司", "板块"])
    detail["日期"] = detail["日期"].dt.strftime("%Y-%m")
    detail["预算差异率"] = detail["营业收入"] / detail["预算营业收入"] - 1
    st.dataframe(
        detail[["日期", "公司", "板块", "营业收入", "利润总额", "利润率", "经营活动现金流", "预算差异率"]].sort_values(["日期", "营业收入"], ascending=[False, False]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "营业收入": st.column_config.NumberColumn(format="%,.0f"),
            "利润总额": st.column_config.NumberColumn(format="%,.0f"),
            "经营活动现金流": st.column_config.NumberColumn(format="%,.0f"),
            "利润率": st.column_config.NumberColumn(format="%.1f%%"),
            "预算差异率": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

with quarter_tab:
    quarter_view = in_range.copy()
    quarter_view["期间"] = quarter_view["年度"].astype(str) + " " + quarter_view["季度"]
    quarter_total = aggregate_period(quarter_view, ["年度", "季度", "期间"])
    quarter_total["季度序号"] = quarter_total["季度"].str[-1].astype(int)
    quarter_total = quarter_total.sort_values(["年度", "季度序号"])
    left, right = st.columns([1.4, 1])
    with left:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=quarter_total["期间"], y=quarter_total["营业收入"], name="营业收入", marker_color=BLUE), secondary_y=False)
        fig.add_trace(go.Scatter(x=quarter_total["期间"], y=quarter_total["利润率"], name="利润率", mode="lines+markers", line=dict(color=ORANGE, width=3)), secondary_y=True)
        fig.update_yaxes(title_text="营业收入（万元）", secondary_y=False)
        fig.update_yaxes(title_text="利润率", tickformat=".0%", secondary_y=True)
        fig.update_layout(title="季度收入与利润率")
        st.plotly_chart(style_figure(fig, 420), use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=quarter_total["期间"], y=quarter_total["收入预算完成率"], name="收入完成率", marker_color=BLUE))
        fig.add_trace(go.Bar(x=quarter_total["期间"], y=quarter_total["利润预算完成率"], name="利润完成率", marker_color=ORANGE))
        fig.add_hline(y=1, line_dash="dot", line_color=INK)
        fig.update_layout(title="季度预算完成率", barmode="group", yaxis_tickformat=".0%")
        st.plotly_chart(style_figure(fig, 420), use_container_width=True, config={"displayModeBar": False})

    quarter_company = aggregate_period(quarter_view, ["年度", "季度", "期间", "公司", "板块"])
    selected_quarter = st.selectbox("查看季度公司表现", quarter_total["期间"].tolist()[::-1], key="quarter_period")
    quarter_rank = quarter_company[quarter_company["期间"] == selected_quarter].sort_values("利润总额", ascending=False)
    fig = px.bar(quarter_rank, x="公司", y="利润总额", color="板块", text_auto=".3s", color_discrete_sequence=PALETTE)
    fig.update_layout(title=f"{selected_quarter} 公司利润贡献", xaxis_title="", yaxis_title="万元")
    st.plotly_chart(style_figure(fig, 380), use_container_width=True, config={"displayModeBar": False})

with annual_tab:
    annual = aggregate_period(in_range, ["年度"]).sort_values("年度")
    annual["收入同比"] = annual["营业收入"].pct_change()
    annual["利润同比"] = annual["利润总额"].pct_change()
    left, right = st.columns([1.4, 1])
    with left:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=annual["年度"], y=annual["营业收入"], name="营业收入", marker_color=BLUE), secondary_y=False)
        fig.add_trace(go.Bar(x=annual["年度"], y=annual["利润总额"], name="利润总额", marker_color=ORANGE), secondary_y=False)
        fig.add_trace(go.Scatter(x=annual["年度"], y=annual["利润率"], name="利润率", mode="lines+markers", line=dict(color=INK, width=2)), secondary_y=True)
        fig.update_yaxes(title_text="万元", secondary_y=False)
        fig.update_yaxes(title_text="利润率", tickformat=".0%", secondary_y=True)
        fig.update_layout(title="年度收入、利润与利润率", barmode="group")
        st.plotly_chart(style_figure(fig, 420), use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annual["年度"], y=annual["资产总额"], name="资产总额", mode="lines+markers", line=dict(color=BLUE, width=3)))
        fig.add_trace(go.Scatter(x=annual["年度"], y=annual["负债总额"], name="负债总额", mode="lines+markers", line=dict(color=ORANGE, width=3)))
        fig.update_layout(title="年度资产负债规模", yaxis_title="万元")
        st.plotly_chart(style_figure(fig, 420), use_container_width=True, config={"displayModeBar": False})

    annual_company = aggregate_period(in_range, ["年度", "公司", "板块"])
    annual_company["净利润贡献率"] = annual_company["净利润"] / annual_company.groupby("年度")["净利润"].transform("sum")
    fig = px.area(annual_company, x="年度", y="净利润", color="公司", groupnorm="fraction", color_discrete_sequence=PALETTE)
    fig.update_layout(title="年度净利润贡献结构", yaxis_title="贡献占比", yaxis_tickformat=".0%", xaxis_title="年度")
    st.plotly_chart(style_figure(fig, 400), use_container_width=True, config={"displayModeBar": False})

with benchmark_tab:
    benchmark_year = st.selectbox("对标年度", sorted(in_range["年度"].unique(), reverse=True), key="benchmark_year")
    max_benchmark_month = int(in_range[in_range["年度"] == benchmark_year]["月份"].max())
    company_ytd = aggregate_period(
        in_range[(in_range["年度"] == benchmark_year) & (in_range["月份"] <= max_benchmark_month)],
        ["公司", "板块"],
    )
    peer = benchmark[
        (benchmark["年度"] == benchmark_year)
        & (benchmark["月份"] <= max_benchmark_month)
        & (benchmark["板块"].isin(selected_sectors))
    ].copy()
    peer_summary = peer.groupby("板块", as_index=False).agg(
        行业营业收入中位数=("行业营业收入中位数", "sum"),
        行业利润率中位数=("行业利润率中位数", "mean"),
        行业现金质量中位数=("行业现金质量中位数", "mean"),
        行业资产负债率中位数=("行业资产负债率中位数", "last"),
    )
    comparison_table = company_ytd.merge(peer_summary, on="板块", how="left")
    comparison_table["收入指数"] = comparison_table["营业收入"] / comparison_table["行业营业收入中位数"] * 100
    comparison_table["利润率指数"] = comparison_table["利润率"] / comparison_table["行业利润率中位数"] * 100
    comparison_table["现金质量指数"] = comparison_table["经营现金质量"] / comparison_table["行业现金质量中位数"] * 100
    comparison_table["负债健康指数"] = comparison_table["行业资产负债率中位数"] / comparison_table["资产负债率"] * 100
    comparison_table["预算执行指数"] = comparison_table["收入预算完成率"] * 100
    index_cols = ["收入指数", "利润率指数", "现金质量指数", "负债健康指数", "预算执行指数"]
    comparison_table["综合对标指数"] = comparison_table[index_cols].mean(axis=1)

    index_long = comparison_table.melt(id_vars=["公司", "板块"], value_vars=index_cols, var_name="维度", value_name="指数")
    fig = px.bar(index_long, x="维度", y="指数", color="公司", barmode="group", color_discrete_sequence=PALETTE)
    fig.add_hline(y=100, line_dash="dot", line_color=INK, annotation_text="基准 100")
    fig.update_layout(title=f"{benchmark_year} 年多维对标指数", xaxis_title="", yaxis_title="指数（100=基准）")
    st.plotly_chart(style_figure(fig, 440), use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns([1, 1.25])
    with left:
        ranked = comparison_table.sort_values("综合对标指数")
        fig = go.Figure(go.Bar(
            x=ranked["综合对标指数"], y=ranked["公司"], orientation="h", marker_color=BLUE,
            text=[f"{value:.1f}" for value in ranked["综合对标指数"]], textposition="outside",
        ))
        fig.add_vline(x=100, line_dash="dot", line_color=INK)
        fig.update_layout(title="公司综合对标排名", xaxis_title="综合指数")
        st.plotly_chart(style_figure(fig, 390), use_container_width=True, config={"displayModeBar": False})
    with right:
        display_cols = ["公司", "板块", "营业收入", "利润率", "经营现金质量", "资产负债率", "收入预算完成率", "综合对标指数"]
        st.subheader("对标明细")
        st.dataframe(
            comparison_table[display_cols].sort_values("综合对标指数", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "营业收入": st.column_config.NumberColumn(format="%,.0f"),
                "利润率": st.column_config.NumberColumn(format="%.1f%%"),
                "经营现金质量": st.column_config.NumberColumn(format="%.2f"),
                "资产负债率": st.column_config.NumberColumn(format="%.1f%%"),
                "收入预算完成率": st.column_config.NumberColumn(format="%.1f%%"),
                "综合对标指数": st.column_config.NumberColumn(format="%.1f"),
            },
        )

with st.expander("数据文件与指标口径"):
    st.markdown(
        "将真实数据按相同字段替换 `data/financial_monthly.csv`，并替换行业基准文件后，页面即可自动读取。"
    )
    st.dataframe(definitions, use_container_width=True, hide_index=True)
    st.download_button(
        "下载当前筛选数据",
        data=in_range.to_csv(index=False).encode("utf-8-sig"),
        file_name="财务驾驶舱_当前筛选数据.csv",
        mime="text/csv",
    )

st.markdown(
    '<p class="source-note">数据来源：确定性模拟数据｜金额单位：万元｜流量指标期间累计，资产负债类指标取期末余额</p>',
    unsafe_allow_html=True,
)
