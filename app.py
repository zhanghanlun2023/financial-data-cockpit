from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SUMMARY_FILE = DATA_DIR / "tb_summary.csv"
DETAIL_FILE = DATA_DIR / "tb_detail.csv"
QUALITY_FILE = DATA_DIR / "tb_quality.json"

BG = "#F3F2EE"
PANEL = "#E9E8E3"
GRID = "#D8D6CF"
TEXT = "#24313A"
MUTED = "#7B8288"
CYAN = "#376F77"
PURPLE = "#6C688A"
AMBER = "#9A7B43"
MAGENTA = "#985E72"
BLUE = "#4F7087"
RED = "#A45F64"

st.set_page_config(page_title="现代投资｜财务数智驾驶舱", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {font-family: Inter, "Microsoft YaHei", sans-serif;}
    .stApp {background:#0B0D12; color:#E5E7EB;}
    [data-testid="stHeader"] {background:#0B0D12;}
    [data-testid="stSidebar"] {background:#0F131A; border-right:0;}
    [data-testid="stSidebar"] * {color:#D2D5DA;}
    [data-testid="stSidebar"] [data-baseweb="select"] * {color:#DCEBFA;}
    [data-baseweb="select"] > div, [data-baseweb="input"] > div {background:#171C24; border:0; box-shadow:none;}
    .block-container {padding-top:1.25rem; padding-bottom:3rem; max-width:1550px;}
    .topbar {display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin-bottom:1rem;}
    .brand-eyebrow {color:#76B9C8; letter-spacing:.18em; font-size:.72rem; font-weight:700;}
    .brand-title {font-size:2rem; font-weight:700; color:#F1F2F4; margin:.2rem 0;}
    .brand-sub {color:#8A919C; font-size:.9rem;}
    .live-pill {display:inline-flex; align-items:center; gap:.5rem; border:0;
      background:#171C24; color:#B9C5CB; padding:.45rem .75rem; border-radius:999px; font-size:.78rem;}
    .live-dot {width:.48rem; height:.48rem; background:#76B9C8; border-radius:50%;}
    .kpi-grid {display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.75rem; margin:.8rem 0 1.1rem;}
    .kpi-card {position:relative; overflow:hidden; min-height:112px; padding:1rem 1rem .85rem;
      background:#141922; border:0; border-radius:10px; box-shadow:none;}
    .kpi-card:before {display:none;}
    .kpi-label {color:#8A919C; font-size:.76rem; letter-spacing:.04em;}
    .kpi-value {color:#F1F2F4; font-size:1.42rem; font-weight:700; margin-top:.4rem; white-space:nowrap;}
    .kpi-foot {color:#8A919C; font-size:.72rem; margin-top:.25rem;}
    .kpi-foot.up {color:#83B7A6;} .kpi-foot.down {color:#C98288;}
    .section-head {display:flex; align-items:center; gap:.65rem; margin:.8rem 0 .55rem;}
    .section-index {color:#76B9C8; font-size:.72rem; font-family:monospace;}
    .section-title {color:#E5E7EB; font-weight:600; font-size:1.03rem;}
    .section-line {height:1px; flex:1; background:#272D36;}
    .link-grid {display:grid; grid-template-columns:1fr 52px 1fr 52px 1fr; align-items:stretch; margin:.55rem 0 1rem;}
    .statement-panel {background:#141922; border:0; border-radius:10px; padding:1rem 1.05rem; min-height:205px;}
    .statement-panel.profit .statement-tag {color:#8F8AB5;}
    .statement-panel.cash .statement-tag {color:#76B9C8;}
    .statement-panel.balance .statement-tag {color:#C6A66A;}
    .statement-tag {font-size:.69rem; letter-spacing:.14em; color:#8A919C;}
    .statement-name {font-size:1.08rem; font-weight:600; color:#E7E9EC; margin:.25rem 0 .7rem;}
    .statement-row {display:flex; justify-content:space-between; gap:.6rem; padding:.36rem 0;
      border-bottom:1px solid #232932; color:#9CA3AD; font-size:.82rem;}
    .statement-row b {color:#E5E7EB; font-weight:600;}
    .statement-foot {margin-top:.65rem; color:#8A919C; font-size:.72rem;}
    .flow-arrow {display:flex; flex-direction:column; align-items:center; justify-content:center; color:#76B9C8;}
    .flow-arrow .arrow-line {height:1px; width:34px; background:#566E77; box-shadow:none; position:relative;}
    .flow-arrow .arrow-line:after {content:""; position:absolute; right:-1px; top:-4px; width:8px; height:8px;
      border-top:1px solid #566E77; border-right:1px solid #566E77; transform:rotate(45deg);}
    .flow-arrow span {font-size:.63rem; color:#8A919C; margin-top:.55rem; text-align:center;}
    .formula-card {padding:1rem 1.1rem; border:0; background:#141922;
      color:#AEB4BD; margin:.55rem 0 1rem; border-radius:10px;}
    .formula-card b {color:#E5E7EB;}.formula-op {color:#76B9C8; padding:0 .35rem;}
    .formula-result {color:#C6A66A; font-size:1.08rem; font-weight:700;}
    .mini-note {color:#8A919C; font-size:.76rem;}
    [data-testid="stPlotlyChart"] {background:#11161E; border:0; border-radius:10px; padding:.25rem; box-shadow:none;}
    div[data-testid="stDataFrame"] {border:0; border-radius:10px; overflow:hidden; box-shadow:none;}
    hr {border-color:#272D36!important;}
    @media(max-width:1100px){.kpi-grid{grid-template-columns:repeat(3,1fr)}.link-grid{grid-template-columns:1fr}.flow-arrow{height:38px;transform:rotate(90deg)}}
    @media(max-width:700px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.topbar{flex-direction:column}.brand-title{font-size:1.55rem}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    .stApp {background:#F3F2EE; color:#24313A;}
    [data-testid="stHeader"] {background:rgba(243,242,238,.94);}
    [data-testid="stSidebar"] {display:none;}
    .block-container {max-width:1460px; padding-top:1.1rem;}
    .topbar {align-items:center; margin:.55rem 0 1.15rem;}
    .brand-eyebrow {color:#376F77; font-weight:600;}
    .brand-title {color:#1E2A32; font-size:1.85rem; font-weight:600; letter-spacing:-.02em;}
    .brand-sub {color:#7B8288;}
    .live-pill {background:#E5E4DF; color:#56636A; border:0; border-radius:4px;}
    .live-dot {background:#376F77;}
    [data-baseweb="select"] > div, [data-baseweb="input"] > div {
      background:#E8E7E2; color:#24313A; border:0; box-shadow:none; border-radius:4px;
    }
    [data-testid="stWidgetLabel"] p {color:#6F777D; font-size:.78rem; letter-spacing:.03em;}
    div[data-testid="stSegmentedControl"] {margin:.15rem 0 .55rem;}
    div[data-testid="stSegmentedControl"] div[role="radiogroup"] {background:#E8E7E2; border:0; box-shadow:none; border-radius:4px;}
    div[data-testid="stSegmentedControl"] button {border:0!important; box-shadow:none!important; border-radius:3px!important;}
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {background:#DCE5E3!important; color:#294F55!important;}
    .kpi-grid {gap:0; margin:.65rem 0 1.45rem; background:#E9E8E3; border-radius:4px;}
    .kpi-card {background:transparent; min-height:104px; border:0; border-radius:0; box-shadow:none; padding:1rem 1.15rem;}
    .kpi-label {color:#777F85;}
    .kpi-value {color:#1E2A32; font-weight:600;}
    .kpi-foot {color:#858C91;}
    .kpi-foot.up {color:#477967;} .kpi-foot.down {color:#A45F64;}
    .section-index {color:#376F77;}
    .section-title {color:#24313A; font-weight:600;}
    .section-line {background:#D7D5CE;}
    .statement-panel {border:0; border-radius:4px; box-shadow:none; color:#24313A;}
    .statement-panel.profit {background:#E8E6E1;}
    .statement-panel.cash {background:#E3E9E8;}
    .statement-panel.balance {background:#ECE8DE;}
    .statement-panel.profit .statement-tag {color:#6C688A;}
    .statement-panel.cash .statement-tag {color:#376F77;}
    .statement-panel.balance .statement-tag {color:#8A7040;}
    .statement-name,.statement-row b {color:#26323A;}
    .statement-row {color:#657077; border-bottom:1px solid rgba(62,75,83,.08);}
    .statement-foot,.flow-arrow span {color:#7B8288;}
    .flow-arrow .arrow-line {background:#789198;}
    .flow-arrow .arrow-line:after {border-color:#789198;}
    .formula-card {background:#E8E7E2; color:#58646B; border:0; border-radius:4px;}
    .formula-card b {color:#24313A;}.formula-op {color:#376F77;}.formula-result {color:#8A7040;}
    .mini-note {color:#7B8288;}
    [data-testid="stPlotlyChart"] {background:transparent; border:0; border-radius:0; box-shadow:none; padding:0;}
    div[data-testid="stDataFrame"] {border:0; border-radius:4px; box-shadow:none;}
    hr {border-color:#D7D5CE!important;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_tb() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if not SUMMARY_FILE.exists() or not DETAIL_FILE.exists():
        st.error("未找到 TB 标准化数据。")
        st.stop()
    summary = pd.read_csv(SUMMARY_FILE)
    detail = pd.read_csv(DETAIL_FILE)
    quality = json.loads(QUALITY_FILE.read_text(encoding="utf-8")) if QUALITY_FILE.exists() else {}
    return summary, detail, quality


def enrich(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["净利率"] = out["净利润"] / out["营业收入"].replace(0, np.nan)
    out["总资产周转率"] = out["营业收入"] / out["资产总额"].replace(0, np.nan)
    out["ROA"] = out["净利润"] / out["资产总额"].replace(0, np.nan)
    out["ROE"] = out["净利润"] / out["所有者权益"].replace(0, np.nan)
    out["权益乘数"] = out["资产总额"] / out["所有者权益"].replace(0, np.nan)
    out["现金质量"] = out["经营现金净额"] / out["净利润"].replace(0, np.nan)
    out["现金转化差额"] = out["经营现金净额"] - out["净利润"]
    return out.replace([np.inf, -np.inf], np.nan)


def money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    return f"{value / 10000:,.2f}亿" if abs(value) >= 10000 else f"{value:,.0f}万"


def pct(value: float | None) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:.1%}"


def multiple(value: float | None) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:.2f}×"


def yoy_text(current: float, previous: float | None) -> tuple[str, str]:
    if previous is None or pd.isna(previous) or previous == 0 or pd.isna(current):
        return "无可比上年数据", ""
    delta = current / previous - 1
    return f"{delta:+.1%} 较上年", "up" if delta >= 0 else "down"


def kpi_card(label: str, value: str, foot: str, accent: str, cls: str = "") -> str:
    return (
        f'<div class="kpi-card" style="--accent:{accent}">'
        f'<div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-foot {cls}">{html.escape(foot)}</div></div>'
    )


def section_head(index: str, title: str) -> None:
    st.markdown(
        f'<div class="section-head"><span class="section-index">{index}</span>'
        f'<span class="section-title">{html.escape(title)}</span><span class="section-line"></span></div>',
        unsafe_allow_html=True,
    )


def style_chart(fig: go.Figure, height: int = 410) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=62, b=34),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Microsoft YaHei", color=TEXT),
        title=dict(font=dict(size=16, color="#EDF7FF"), x=0.025),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=MUTED)),
        hoverlabel=dict(bgcolor="#10263A", bordercolor="#2E5570", font_color=TEXT),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, tickfont_color=MUTED, title_font_color=MUTED, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, tickfont_color=MUTED, title_font_color=MUTED, zeroline=False)
    return fig


def statement_linkage(row: pd.Series) -> None:
    st.markdown(
        f"""
        <div class="link-grid">
          <div class="statement-panel profit">
            <div class="statement-tag">INCOME STATEMENT</div><div class="statement-name">利润表｜经营成果</div>
            <div class="statement-row"><span>营业总收入</span><b>{money(row['营业收入'])}</b></div>
            <div class="statement-row"><span>利润总额</span><b>{money(row['利润总额'])}</b></div>
            <div class="statement-row"><span>净利润</span><b>{money(row['净利润'])}</b></div>
            <div class="statement-foot">营业总收入 × 净利率 → 净利润</div>
          </div>
          <div class="flow-arrow"><div class="arrow-line"></div><span>利润<br>转化</span></div>
          <div class="statement-panel cash">
            <div class="statement-tag">CASH FLOW STATEMENT</div><div class="statement-name">现金流量表｜现金含量</div>
            <div class="statement-row"><span>净利润</span><b>{money(row['净利润'])}</b></div>
            <div class="statement-row"><span>经营现金净额</span><b>{money(row['经营现金净额'])}</b></div>
            <div class="statement-row"><span>现金净增加额</span><b>{money(row['现金净增加额'])}</b></div>
            <div class="statement-foot">净利润 × 现金质量 → 经营现金</div>
          </div>
          <div class="flow-arrow"><div class="arrow-line"></div><span>现金<br>沉淀</span></div>
          <div class="statement-panel balance">
            <div class="statement-tag">BALANCE SHEET</div><div class="statement-name">资产负债表｜资源结构</div>
            <div class="statement-row"><span>资产总额</span><b>{money(row['资产总额'])}</b></div>
            <div class="statement-row"><span>负债总额</span><b>{money(row['负债总额'])}</b></div>
            <div class="statement-row"><span>所有者权益</span><b>{money(row['所有者权益'])}</b></div>
            <div class="statement-foot">资产 = 负债 + 所有者权益</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


summary_raw, detail, quality = load_tb()
summary = enrich(summary_raw)
years = sorted(summary["year"].astype(int).unique().tolist())

header_slot = st.empty()
page = st.segmented_control(
    "导航",
    ["联动总览", "三表趋势", "经营效能", "公司矩阵", "科目穿透"],
    default="联动总览",
    label_visibility="collapsed",
)
filter_year, filter_entity = st.columns([0.75, 1.65], vertical_alignment="bottom")
with filter_year:
    selected_year = st.selectbox("分析年度", years, index=len(years) - 1)
year_entities = summary[summary["year"].eq(selected_year)].sort_values(["scope", "entity"])["entity"].tolist()
year_entities = ["集团审定口径"] + [x for x in year_entities if x != "集团审定口径"]
with filter_entity:
    selected_entity = st.selectbox("分析主体", year_entities)
st.caption("年度和主体筛选同步驱动三张主表、杜邦指标及科目穿透。")

current_rows = summary[(summary["year"].eq(selected_year)) & (summary["entity"].eq(selected_entity))]
if current_rows.empty:
    st.warning("当前年度没有该主体数据。")
    st.stop()
current = current_rows.iloc[0]
previous_rows = summary[(summary["year"].eq(selected_year - 1)) & (summary["entity"].eq(selected_entity))]
previous = previous_rows.iloc[0] if not previous_rows.empty else None
entity_history = summary[summary["entity"].eq(selected_entity)].sort_values("year")

header_slot.markdown(
    f"""
    <div class="topbar">
      <div><div class="brand-eyebrow">MODERN INVESTMENT · FINANCIAL INTELLIGENCE</div>
      <div class="brand-title">财务数智驾驶舱</div>
      <div class="brand-sub">{html.escape(selected_entity)} · {selected_year} 年 · 三表一体化分析</div></div>
      <div class="live-pill"><span class="live-dot"></span> TB 审定口径已连接</div>
    </div>
    """,
    unsafe_allow_html=True,
)


if page == "联动总览":
    cards = []
    for label, field, formatter, accent in [
        ("营业总收入", "营业收入", money, PURPLE), ("净利润", "净利润", money, MAGENTA),
        ("经营现金净额", "经营现金净额", money, CYAN), ("资产总额", "资产总额", money, BLUE),
        ("资产负债率", "资产负债率", pct, AMBER), ("现金质量", "现金质量", multiple, CYAN),
    ]:
        prev_val = previous[field] if previous is not None and field in previous else None
        foot, cls = yoy_text(current[field], prev_val) if field != "现金质量" else ("经营现金净额 ÷ 净利润", "")
        cards.append(kpi_card(label, formatter(current[field]), foot, accent, cls))
    st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    section_head("01", "三张主表联动链")
    statement_linkage(current)

    section_head("02", "核心指标传导")
    st.markdown(
        f"""
        <div class="formula-card">
          <b>ROE 传导</b><span class="formula-op">=</span>净利率 {pct(current['净利率'])}
          <span class="formula-op">×</span>总资产周转率 {multiple(current['总资产周转率'])}
          <span class="formula-op">×</span>权益乘数 {multiple(current['权益乘数'])}
          <span class="formula-op">=</span><span class="formula-result">{pct(current['ROE'])}</span>
          <div class="mini-note">基于期末资产与权益的简化杜邦关系，用于识别盈利、效率和杠杆的共同作用。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        bridge = pd.DataFrame({
            "环节": ["净利润", "现金转换调整", "经营现金净额"],
            "金额": [current["净利润"], current["现金转化差额"], current["经营现金净额"]],
            "measure": ["absolute", "relative", "total"],
        })
        fig = go.Figure(go.Waterfall(
            x=bridge["环节"], y=bridge["金额"], measure=bridge["measure"],
            connector={"line": {"color": GRID}},
            increasing={"marker": {"color": CYAN}}, decreasing={"marker": {"color": MAGENTA}},
            totals={"marker": {"color": BLUE}},
            text=[money(x) for x in bridge["金额"]], textposition="outside",
            hovertemplate="%{x}<br>%{y:,.0f} 万元<extra></extra>",
        ))
        fig.update_layout(title="利润到经营现金的转化桥", showlegend=False)
        fig.update_yaxes(title="万元")
        st.plotly_chart(style_chart(fig, 390), use_container_width=True)
    with c2:
        balance = pd.DataFrame({"构成": ["负债", "所有者权益"], "金额": [current["负债总额"], current["所有者权益"]]})
        fig = go.Figure()
        for idx, row in balance.iterrows():
            fig.add_bar(x=["资产来源"], y=[row["金额"]], name=row["构成"], marker_color=[AMBER, PURPLE][idx],
                        text=money(row["金额"]), textposition="inside",
                        hovertemplate=f"{row['构成']}<br>%{{y:,.0f}} 万元<extra></extra>")
        fig.update_layout(title="资产来源：负债与权益", barmode="stack")
        fig.update_yaxes(title="万元")
        st.plotly_chart(style_chart(fig, 390), use_container_width=True)

elif page == "三表趋势":
    section_head("01", f"{selected_entity}｜经营成果与现金协同")
    flow = entity_history.melt(id_vars="year", value_vars=["营业收入", "净利润", "经营现金净额"], var_name="指标", value_name="金额")
    fig = px.bar(flow, x="year", y="金额", color="指标", barmode="group",
                 color_discrete_map={"营业收入": PURPLE, "净利润": MAGENTA, "经营现金净额": CYAN})
    fig.update_layout(title="利润表与现金流量表年度联动")
    fig.update_xaxes(title=None, dtick=1)
    fig.update_yaxes(title="万元")
    fig.update_traces(hovertemplate="%{x}年<br>%{fullData.name}：%{y:,.0f} 万元<extra></extra>")
    st.plotly_chart(style_chart(fig, 455), use_container_width=True)

    section_head("02", "资产规模与资本结构")
    balance_long = entity_history.melt(id_vars="year", value_vars=["资产总额", "负债总额", "所有者权益"], var_name="指标", value_name="金额")
    fig2 = px.bar(balance_long, x="year", y="金额", color="指标", barmode="group",
                  color_discrete_map={"资产总额": BLUE, "负债总额": AMBER, "所有者权益": PURPLE})
    fig2.update_layout(title="资产负债表年度结构")
    fig2.update_xaxes(title=None, dtick=1)
    fig2.update_yaxes(title="万元")
    fig2.update_traces(hovertemplate="%{x}年<br>%{fullData.name}：%{y:,.0f} 万元<extra></extra>")
    st.plotly_chart(style_chart(fig2, 455), use_container_width=True)

    section_head("03", "联动效率矩阵")
    ratio_cols = ["净利率", "ROA", "ROE", "资产负债率", "总资产周转率", "现金质量"]
    heat = entity_history.set_index("year")[ratio_cols].T
    row_medians = heat.abs().median(axis=1).replace(0, 1)
    normalized = heat.div(row_medians, axis=0).clip(-3, 3)
    fig3 = go.Figure(go.Heatmap(
        z=normalized.values, x=[str(x) for x in normalized.columns], y=normalized.index,
        customdata=heat.values,
        colorscale=[[0, "#A77A88"], [.5, "#EEECE7"], [1, "#5C8588"]], zmid=0,
        hovertemplate="%{y}｜%{x}年<br>原值：%{customdata:.2f}<extra></extra>", colorbar_title="相对强度",
    ))
    fig3.update_layout(title="六项联动指标相对强度（按指标自身尺度标准化）")
    st.plotly_chart(style_chart(fig3, 410), use_container_width=True)

elif page == "经营效能":
    section_head("01", "杜邦驱动分解")
    dupont_cards = [
        kpi_card("净利率｜盈利能力", pct(current["净利率"]), "净利润 ÷ 营业收入", PURPLE),
        kpi_card("总资产周转率｜运营效率", multiple(current["总资产周转率"]), "营业收入 ÷ 资产总额", CYAN),
        kpi_card("权益乘数｜财务杠杆", multiple(current["权益乘数"]), "资产总额 ÷ 所有者权益", AMBER),
        kpi_card("ROE｜股东回报", pct(current["ROE"]), "三项驱动共同结果", MAGENTA),
        kpi_card("ROA｜资产回报", pct(current["ROA"]), "净利润 ÷ 资产总额", BLUE),
        kpi_card("现金质量｜利润含金量", multiple(current["现金质量"]), "经营现金 ÷ 净利润", CYAN),
    ]
    st.markdown('<div class="kpi-grid">' + "".join(dupont_cards) + "</div>", unsafe_allow_html=True)

    peers = summary[(summary["year"].eq(selected_year)) & (summary["scope"].eq("公司"))].copy()
    ratio_metric = st.selectbox("公司效能指标", ["净利率", "ROA", "ROE", "总资产周转率", "现金质量", "资产负债率"])
    rank = peers.dropna(subset=[ratio_metric]).sort_values(ratio_metric)
    fig = go.Figure(go.Bar(
        x=rank[ratio_metric], y=rank["entity"], orientation="h",
        marker_color=[CYAN if x >= 0 else MAGENTA for x in rank[ratio_metric]],
        text=[pct(x) if ratio_metric in ["净利率", "ROA", "ROE", "资产负债率"] else multiple(x) for x in rank[ratio_metric]],
        textposition="outside", hovertemplate="%{y}<br>%{x:.2f}<extra></extra>",
    ))
    fig.update_layout(title=f"{selected_year} 年公司{ratio_metric}对标", showlegend=False)
    fig.update_xaxes(title=ratio_metric)
    st.plotly_chart(style_chart(fig, max(420, 95 + len(rank) * 31)), use_container_width=True)

elif page == "公司矩阵":
    section_head("01", "公司盈利—效率—现金矩阵")
    peers = summary[(summary["year"].eq(selected_year)) & (summary["scope"].eq("公司"))].dropna(
        subset=["总资产周转率", "净利率", "资产总额", "现金质量"]
    ).copy()
    peers["气泡"] = peers["资产总额"].abs().clip(lower=1)
    peers["现金状态"] = np.where(peers["现金质量"] >= 1, "现金覆盖利润", "现金低于利润")
    fig = px.scatter(
        peers, x="总资产周转率", y="净利率", size="气泡", color="现金状态", text="entity",
        color_discrete_map={"现金覆盖利润": CYAN, "现金低于利润": MAGENTA}, size_max=58,
    )
    fig.update_layout(title=f"{selected_year} 年公司经营质量矩阵｜气泡大小代表资产总额")
    fig.update_traces(textposition="top center",
                      hovertemplate="%{text}<br>周转率：%{x:.2f}×<br>净利率：%{y:.1%}<extra></extra>")
    fig.update_xaxes(title="总资产周转率", tickformat=".2f")
    fig.update_yaxes(title="净利率", tickformat=".0%", zeroline=True, zerolinecolor=MUTED)
    st.plotly_chart(style_chart(fig, 560), use_container_width=True)

    section_head("02", "公司三表核心指标")
    table = peers[["entity", "营业收入", "净利润", "经营现金净额", "资产总额", "资产负债率", "ROE", "现金质量"]].copy()
    table = table.sort_values("净利润", ascending=False).rename(columns={"entity": "公司"})
    st.dataframe(table, use_container_width=True, hide_index=True, height=430, column_config={
        "营业收入": st.column_config.NumberColumn(format="%.0f 万"), "净利润": st.column_config.NumberColumn(format="%.0f 万"),
        "经营现金净额": st.column_config.NumberColumn(format="%.0f 万"), "资产总额": st.column_config.NumberColumn(format="%.0f 万"),
        "资产负债率": st.column_config.NumberColumn(format="%.1%%"), "ROE": st.column_config.NumberColumn(format="%.1%%"),
        "现金质量": st.column_config.NumberColumn(format="%.2f×"),
    })

elif page == "科目穿透":
    section_head("01", "TB 科目穿透分析")
    statement = st.segmented_control("报表", ["资产负债表", "利润表", "现金流量表"], default="资产负债表")
    part = detail[(detail["year"].eq(selected_year)) & (detail["entity"].eq(selected_entity)) & (detail["section"].eq(statement))].copy()
    part = part[~part["account_key"].str.contains("核对|正确|附表|项目", regex=True, na=False)]
    top = part[part["value_wan"].ne(0)].assign(abs_value=lambda x: x["value_wan"].abs()).nlargest(18, "abs_value").sort_values("value_wan")
    fig = go.Figure(go.Bar(
        x=top["value_wan"], y=top["account"], orientation="h",
        marker_color=[CYAN if x >= 0 else MAGENTA for x in top["value_wan"]],
        text=[money(x) for x in top["value_wan"]], textposition="outside",
        hovertemplate="%{y}<br>%{x:,.0f} 万元<extra></extra>",
    ))
    fig.update_layout(title=f"{selected_entity}｜{statement}绝对额前 18 项", showlegend=False)
    fig.update_xaxes(title="万元")
    st.plotly_chart(style_chart(fig, 610), use_container_width=True)

    keyword = st.text_input("科目搜索", placeholder="输入应收账款、营业收入、现金流等")
    view = part.copy()
    if keyword:
        view = view[view["account"].str.contains(keyword, case=False, na=False)]
    view = view[["row_no", "account", "value_wan"]].rename(columns={"row_no": "TB行号", "account": "科目", "value_wan": "金额（万元）"})
    st.dataframe(view, use_container_width=True, hide_index=True, height=420,
                 column_config={"金额（万元）": st.column_config.NumberColumn(format="%.2f")})
    st.download_button("导出当前科目明细", view.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{selected_year}_{selected_entity}_{statement}.csv", mime="text/csv")

with st.expander("指标口径与数据说明"):
    st.write("集团口径取各年度 TB 的审定数或抵销/调整后金额；金额统一由元换算为万元。")
    st.write("净利率＝净利润÷营业总收入；所有者权益＝资产总额－负债总额；现金质量＝经营现金净额÷净利润；简化杜邦 ROE＝净利率×总资产周转率×权益乘数。")
    st.caption("杜邦指标使用期末资产和期末权益，适合驾驶舱联动观察；正式财务分析可在取得期初数后改用平均资产、平均权益。")

st.markdown(
    f'<div class="mini-note">DATA SOURCE · {html.escape(quality.get("source_file", "年度TB"))} · '
    f'{min(years)}—{max(years)} · {quality.get("detail_records", len(detail)):,} 条数值记录</div>',
    unsafe_allow_html=True,
)
