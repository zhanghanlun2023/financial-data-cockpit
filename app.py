from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SUMMARY_FILE = DATA_DIR / "tb_summary.csv"
DETAIL_FILE = DATA_DIR / "tb_detail.csv"
QUALITY_FILE = DATA_DIR / "tb_quality.json"

NAV = ["集团总览", "年度趋势", "公司对标", "科目结构", "明细查询"]
BLUE = "#2C6BED"
CYAN = "#25B8A6"
ORANGE = "#F28E2B"
RED = "#E15759"
INK = "#172033"
MUTED = "#6B778C"
GRID = "#DDE3ED"

st.set_page_config(page_title="财务数据驾驶舱｜TB", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      .stApp {background: #F3F6FB; color: #172033;}
      [data-testid="stSidebar"] {background: #101A2D;}
      [data-testid="stSidebar"] * {color: #E8EEF8;}
      [data-testid="stSidebar"] [data-baseweb="select"] * {color: #172033;}
      .hero {padding: 1.35rem 1.55rem; border-radius: 20px; margin-bottom: 1rem;
             color: white; background: linear-gradient(120deg,#101A2D 0%,#1C3764 60%,#2C6BED 100%);
             box-shadow: 0 14px 32px rgba(23,42,76,.18);}
      .hero h1 {font-size: 2rem; margin: 0; font-weight: 700;}
      .hero p {margin: .45rem 0 0; color: #D7E3F8;}
      [data-testid="stMetric"] {background:#FFF; border:1px solid #E1E6EF; border-radius:16px;
             padding:.82rem 1rem; box-shadow:0 5px 16px rgba(31,52,86,.055);}
      [data-testid="stMetricLabel"] {color:#6B778C;}
      [data-testid="stMetricValue"] {color:#172033;}
      .section-kicker {color:#2C6BED; font-size:.78rem; letter-spacing:.12em; font-weight:700; margin-top:.4rem;}
      .source-note {color:#6B778C; font-size:.82rem;}
      .positive {color:#18856F;} .negative {color:#C74547;}
      div[data-testid="stDataFrame"] {border:1px solid #E1E6EF; border-radius:14px; overflow:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_tb() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if not SUMMARY_FILE.exists() or not DETAIL_FILE.exists():
        st.error("尚未生成 TB 看板数据，请先运行 tb_parser.py。")
        st.stop()
    summary = pd.read_csv(SUMMARY_FILE)
    detail = pd.read_csv(DETAIL_FILE)
    quality = json.loads(QUALITY_FILE.read_text(encoding="utf-8")) if QUALITY_FILE.exists() else {}
    return summary, detail, quality


def cn_money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    if abs(value) >= 10000:
        return f"{value / 10000:,.2f} 亿元"
    return f"{value:,.0f} 万元"


def cn_pct(value: float | None) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:.1%}"


def delta_text(current: float, previous: float, percentage: bool = False) -> str | None:
    if pd.isna(current) or pd.isna(previous):
        return None
    if percentage:
        return f"{current - previous:+.1%} vs 上年"
    if previous == 0:
        return None
    return f"{current / previous - 1:+.1%} vs 上年"


def polish(fig: go.Figure, height: int = 400) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=58, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Microsoft YaHei, Arial", color=INK),
        title_font=dict(size=17, color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(font_family="Microsoft YaHei"),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, showline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showline=False)
    return fig


def metric_bar(frame: pd.DataFrame, metric: str, title: str) -> go.Figure:
    data = frame.sort_values(metric, ascending=True).dropna(subset=[metric])
    colors = [RED if x < 0 else BLUE for x in data[metric]]
    fig = go.Figure(go.Bar(
        x=data[metric], y=data["entity"], orientation="h", marker_color=colors,
        text=[cn_money(x) for x in data[metric]], textposition="outside",
        hovertemplate="%{y}<br>%{x:,.0f} 万元<extra></extra>",
    ))
    fig.update_layout(title=title, showlegend=False)
    fig.update_xaxes(title="万元")
    return polish(fig, max(360, min(620, 70 + len(data) * 34)))


summary, detail, quality = load_tb()
years = sorted(summary["year"].dropna().astype(int).unique().tolist())
latest_year = max(years)

with st.sidebar:
    st.markdown("## 财务驾驶舱")
    st.caption("TB 审定口径 · 2020—2025")
    page = st.radio("分析主题", NAV, label_visibility="collapsed")
    st.divider()
    selected_year = st.selectbox("分析年度", years, index=len(years) - 1)
    st.caption("金额单位：万元；比率按审定数计算")

st.markdown(
    f"""<div class="hero"><h1>财务数据驾驶舱</h1>
    <p>年度 TB 全景分析 · 集团审定口径 · 当前分析年度 {selected_year}</p></div>""",
    unsafe_allow_html=True,
)

group = summary[summary["scope"].eq("集团")].sort_values("year")
current = group[group["year"].eq(selected_year)].iloc[0]
previous_rows = group[group["year"].eq(selected_year - 1)]
previous = previous_rows.iloc[0] if not previous_rows.empty else None
companies = summary[(summary["year"].eq(selected_year)) & (summary["scope"].eq("公司"))].copy()

if page == "集团总览":
    st.markdown('<div class="section-kicker">EXECUTIVE OVERVIEW</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    cards = [
        ("资产总额", cn_money(current["资产总额"]), delta_text(current["资产总额"], previous["资产总额"]) if previous is not None else None),
        ("营业收入", cn_money(current["营业收入"]), delta_text(current["营业收入"], previous["营业收入"]) if previous is not None else None),
        ("利润总额", cn_money(current["利润总额"]), delta_text(current["利润总额"], previous["利润总额"]) if previous is not None else None),
        ("净利润", cn_money(current["净利润"]), delta_text(current["净利润"], previous["净利润"]) if previous is not None else None),
        ("资产负债率", cn_pct(current["资产负债率"]), delta_text(current["资产负债率"], previous["资产负债率"], True) if previous is not None else None),
    ]
    for col, (label, value, delta) in zip(cols, cards):
        col.metric(label, value, delta)

    left, right = st.columns([1.15, 1])
    with left:
        balance = group.melt(
            id_vars="year", value_vars=["资产总额", "负债总额", "所有者权益"],
            var_name="指标", value_name="金额",
        )
        fig = px.bar(balance, x="year", y="金额", color="指标", barmode="group",
                     color_discrete_map={"资产总额": BLUE, "负债总额": ORANGE, "所有者权益": CYAN},
                     title="集团资产负债规模（审定口径）")
        fig.update_traces(hovertemplate="%{x}年<br>%{fullData.name}：%{y:,.0f} 万元<extra></extra>")
        fig.update_xaxes(dtick=1, title=None)
        fig.update_yaxes(title="万元")
        st.plotly_chart(polish(fig), use_container_width=True)
    with right:
        operations = group.melt(
            id_vars="year", value_vars=["营业收入", "利润总额", "净利润"],
            var_name="指标", value_name="金额",
        )
        fig = px.bar(operations, x="year", y="金额", color="指标", barmode="group",
                     color_discrete_map={"营业收入": BLUE, "利润总额": ORANGE, "净利润": CYAN},
                     title="集团经营成果（审定口径）")
        fig.update_traces(hovertemplate="%{x}年<br>%{fullData.name}：%{y:,.0f} 万元<extra></extra>")
        fig.update_xaxes(dtick=1, title=None)
        fig.update_yaxes(title="万元")
        st.plotly_chart(polish(fig), use_container_width=True)

    ranking_metric = st.selectbox("公司排名指标", ["资产总额", "营业收入", "利润总额", "净利润"], index=1)
    st.plotly_chart(metric_bar(companies, ranking_metric, f"{selected_year} 年公司{ranking_metric}对标"), use_container_width=True)

elif page == "年度趋势":
    st.markdown('<div class="section-kicker">ANNUAL PERFORMANCE</div>', unsafe_allow_html=True)
    metric = st.selectbox("趋势指标", ["资产总额", "负债总额", "所有者权益", "营业收入", "利润总额", "净利润", "经营现金净额"])
    data = group[["year", metric]].dropna().copy()
    data["同比"] = data[metric].pct_change()
    fig = go.Figure()
    fig.add_bar(x=data["year"], y=data[metric], name=metric, marker_color=BLUE,
                text=[cn_money(v) for v in data[metric]], textposition="outside",
                hovertemplate="%{x}年<br>%{y:,.0f} 万元<extra></extra>")
    fig.update_layout(title=f"集团{metric}年度变化", showlegend=False)
    fig.update_xaxes(dtick=1, title=None)
    fig.update_yaxes(title="万元")
    st.plotly_chart(polish(fig, 470), use_container_width=True)

    yoy = data.dropna(subset=["同比"])
    if not yoy.empty:
        fig2 = go.Figure(go.Bar(
            x=yoy["year"], y=yoy["同比"], marker_color=[RED if x < 0 else CYAN for x in yoy["同比"]],
            text=[f"{x:+.1%}" for x in yoy["同比"]], textposition="outside",
            hovertemplate="%{x}年<br>同比：%{y:.1%}<extra></extra>",
        ))
        fig2.update_layout(title=f"{metric}同比增速", showlegend=False)
        fig2.update_xaxes(dtick=1, title=None)
        fig2.update_yaxes(title="同比", tickformat=".0%")
        st.plotly_chart(polish(fig2, 330), use_container_width=True)

elif page == "公司对标":
    st.markdown('<div class="section-kicker">ENTITY BENCHMARK</div>', unsafe_allow_html=True)
    x_metric = st.selectbox("横轴", ["资产总额", "营业收入", "负债总额"], index=0)
    y_metric = st.selectbox("纵轴", ["净利润", "利润总额", "经营现金净额"], index=0)
    bubble = companies.dropna(subset=[x_metric, y_metric, "营业收入"]).copy()
    bubble["经营状态"] = bubble[y_metric].ge(0).map({True: "正值", False: "负值"})
    bubble["气泡"] = bubble["营业收入"].abs().clip(lower=1)
    fig = px.scatter(
        bubble, x=x_metric, y=y_metric, size="气泡", color="经营状态", text="entity",
        color_discrete_map={"正值": CYAN, "负值": RED}, size_max=55,
        title=f"{selected_year} 年公司经营矩阵（气泡大小＝营业收入）",
    )
    fig.update_traces(textposition="top center", hovertemplate="%{text}<br>横轴：%{x:,.0f} 万元<br>纵轴：%{y:,.0f} 万元<extra></extra>")
    fig.update_xaxes(title=f"{x_metric}（万元）")
    fig.update_yaxes(title=f"{y_metric}（万元）", zeroline=True, zerolinecolor=MUTED)
    st.plotly_chart(polish(fig, 520), use_container_width=True)

    rank_metric = st.selectbox("查看排名", ["资产总额", "营业收入", "利润总额", "净利润", "经营现金净额"], index=3)
    st.plotly_chart(metric_bar(companies, rank_metric, f"{selected_year} 年公司{rank_metric}排名"), use_container_width=True)

elif page == "科目结构":
    st.markdown('<div class="section-kicker">ACCOUNT COMPOSITION</div>', unsafe_allow_html=True)
    entity_options = ["集团审定口径"] + sorted(companies["entity"].unique().tolist())
    entity = st.selectbox("分析主体", entity_options)
    section = st.selectbox("报表", ["资产负债表", "利润表", "现金流量表"])
    part = detail[(detail["year"].eq(selected_year)) & (detail["entity"].eq(entity)) & (detail["section"].eq(section))].copy()
    part = part[
        ~part["account_key"].str.contains("合计|总计|核对|正确|其中|减：|附表|项目", regex=True, na=False)
        & part["value_wan"].ne(0)
    ]
    part["绝对值"] = part["value_wan"].abs()
    top = part.nlargest(15, "绝对值").sort_values("value_wan")
    fig = go.Figure(go.Bar(
        x=top["value_wan"], y=top["account"], orientation="h",
        marker_color=[RED if x < 0 else BLUE for x in top["value_wan"]],
        text=[cn_money(x) for x in top["value_wan"]], textposition="outside",
        hovertemplate="%{y}<br>%{x:,.0f} 万元<extra></extra>",
    ))
    fig.update_layout(title=f"{entity}｜{section}绝对额前 15 项", showlegend=False)
    fig.update_xaxes(title="万元")
    st.plotly_chart(polish(fig, 560), use_container_width=True)
    st.caption("按 TB 原始科目余额展示；科目存在层级关系，本图用于识别大额项目，不代表可直接相加的构成比例。")

elif page == "明细查询":
    st.markdown('<div class="section-kicker">ACCOUNT DETAIL</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        years_filter = st.multiselect("年度", years, default=[selected_year])
    with c2:
        sections_filter = st.multiselect("报表", ["资产负债表", "利润表", "现金流量表"], default=["资产负债表"])
    with c3:
        entities_filter = st.multiselect("主体", sorted(detail["entity"].unique()), default=["集团审定口径"])
    keyword = st.text_input("科目关键词", placeholder="例如：应收账款、营业收入、现金流")
    view = detail[
        detail["year"].isin(years_filter)
        & detail["section"].isin(sections_filter)
        & detail["entity"].isin(entities_filter)
    ].copy()
    if keyword:
        view = view[view["account"].str.contains(keyword, case=False, na=False)]
    view = view[["year", "section", "account", "entity", "value_wan"]].rename(
        columns={"year": "年度", "section": "报表", "account": "科目", "entity": "主体", "value_wan": "金额（万元）"}
    )
    st.dataframe(view, use_container_width=True, hide_index=True, height=520,
                 column_config={"金额（万元）": st.column_config.NumberColumn(format="%.2f")})
    st.download_button("下载筛选结果 CSV", view.to_csv(index=False).encode("utf-8-sig"),
                       file_name="TB明细筛选结果.csv", mime="text/csv")

with st.expander("数据口径与质量检查"):
    source_map = {x["year"]: x["group_source"] for x in quality.get("sheet_audit", [])}
    st.write(
        f"数据源：{quality.get('source_file', 'TB 工作簿')}；覆盖 {min(years)}—{max(years)} 年；"
        f"共 {quality.get('detail_records', len(detail)):,} 条数值记录、{quality.get('accounts', detail['account_key'].nunique()):,} 个标准化科目。"
    )
    st.write("集团口径来源：" + "；".join(f"{year}年＝{source_map.get(year, '审定/调整后数')}" for year in years))
    st.write("所有者权益＝资产总额－负债总额；资产负债率＝负债总额÷资产总额；金额由元换算为万元。")
    st.caption("不同年度公司范围和 TB 模板存在变化，公司对标默认限定在所选年度内，不将名称变化误判为同比趋势。")

st.markdown(
    f'<p class="source-note">数据截至 {latest_year} 年 · 来源：年度 TB 审定/调整后口径 · 原始文件未修改</p>',
    unsafe_allow_html=True,
)
