"""
全局样式与轻量 UI 辅助函数。

设计目标（沉稳 / 专业 / 适合长期办公）：
    - 仅使用系统字体，不引用任何外部 CDN 字体。
    - 低饱和、护眼的中性色系 + 单一克制的钢蓝点缀色。
    - 排版宽松透气，靠留白和发丝线分隔，而非密集边框。
    - 班次配色统一为低饱和柔和色，长时间盯屏不刺眼。

维护说明：
    所有视觉只在本文件里调。颜色集中在 COLORS 与 :root CSS 变量。
    页面通过 page_header / section_title / kpi_row 等辅助函数复用版式，
    避免在各页面里散落内联 HTML。
"""

import streamlit as st


# ═══════════════════════════════════════════════
# 配色（同时供 Python 侧引用）
# ═══════════════════════════════════════════════

COLORS = {
    "accent":        "#3e6291",   # 钢蓝，主点缀
    "accent_strong": "#314f76",
    "accent_soft":   "#eaeff5",

    "bg":            "#f4f5f7",
    "surface":       "#ffffff",
    "surface_soft":  "#f9fafb",

    "ink":           "#232a31",
    "text":          "#5a636c",
    "muted":         "#98a1a9",

    "border":        "#e3e6ea",
    "border_soft":   "#eef0f2",

    "good":          "#4f6f56",
    "warn":          "#8a6d3b",
    "bad":           "#9c4a44",

    # 班次柔和底色（仅展示用，导出/存库仍用 config 里的原色）
    "shift_rest":     "#f0f1f3",
    "shift_early":    "#f6efe2",
    "shift_mid":      "#e8eef4",
    "shift_late":     "#efeaf2",
    "shift_office":   "#e9efe9",
    "shift_external": "#f4ece5",
}


# ═══════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════

STYLES = """
<style>
    :root {
        --bg:            #f4f5f7;
        --surface:       #ffffff;
        --surface-soft:  #f9fafb;

        --ink:           #232a31;
        --text:          #5a636c;
        --muted:         #98a1a9;

        --border:        #e3e6ea;
        --border-soft:   #eef0f2;

        --accent:        #3e6291;
        --accent-strong: #314f76;
        --accent-soft:   #eaeff5;

        --good: #4f6f56;
        --warn: #8a6d3b;
        --bad:  #9c4a44;

        --r-sm: 6px;
        --r-md: 8px;
        --r-lg: 12px;

        --shadow: 0 1px 2px rgba(20,28,40,.04), 0 2px 6px -2px rgba(20,28,40,.05);

        --font: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC",
                "WenQuanYi Micro Hei", sans-serif;
    }

    /* ===== 全局 ===== */
    html, body, .stApp, [class*="css"] {
        font-family: var(--font);
        -webkit-font-smoothing: antialiased;
    }
    .stApp { background: var(--bg); color: var(--ink); }

    /* 留白更宽松，内容居中限宽，长期阅读更舒服 */
    .main .block-container,
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1240px;
    }

    /* 默认标题不用，改用自定义 page-head；隐藏 streamlit 锚点 */
    h1 a, h2 a, h3 a { display: none !important; }

    /* ===== 侧边栏（仅导航，保持干净） ===== */
    section[data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.6rem; }
    [data-testid="stSidebarNav"] { padding-top: .4rem; }
    [data-testid="stSidebarNav"] ul { gap: 2px; }
    [data-testid="stSidebarNav"] a {
        border-radius: var(--r-sm);
        padding: 7px 12px !important;
    }

    /* ===== 页头 ===== */
    .page-head { margin-bottom: 1.6rem; }
    .page-head h1 {
        font-size: 1.55rem;
        font-weight: 700;
        letter-spacing: -.02em;
        color: var(--ink);
        margin: 0 0 .25rem;
        padding: 0;
    }
    .page-head p {
        font-size: .92rem;
        color: var(--text);
        margin: 0;
        line-height: 1.5;
    }
    .page-head .rule {
        height: 1px; background: var(--border);
        margin-top: 1.1rem;
    }

    /* ===== 区块标题 ===== */
    .sec {
        display: flex; align-items: baseline; gap: .6rem;
        margin: 2rem 0 .9rem;
    }
    .sec::before {
        content: ""; align-self: stretch; flex: none;
        width: 3px; border-radius: 2px;
        background: var(--accent);
    }
    .sec .t {
        font-size: 1.06rem; font-weight: 650; letter-spacing: -.01em;
        color: var(--ink);
    }
    .sec .s {
        font-size: .82rem; color: var(--muted);
    }

    /* ===== KPI 磁贴 ===== */
    .kpi {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-md);
        padding: 16px 18px;
        box-shadow: var(--shadow);
    }
    .kpi .lab {
        font-size: .72rem; font-weight: 600; color: var(--muted);
        text-transform: uppercase; letter-spacing: .07em;
    }
    .kpi .val {
        font-size: 1.65rem; font-weight: 750; letter-spacing: -.02em;
        color: var(--ink); margin-top: 3px;
        font-variant-numeric: tabular-nums;
    }
    .kpi .val.good { color: var(--good); }
    .kpi .val.warn { color: var(--warn); }
    .kpi .val.bad  { color: var(--bad); }
    .kpi .sub { font-size: .76rem; color: var(--muted); margin-top: 2px; }

    /* ===== 排班矩阵 ===== */
    .schedule-table {
        width: 100%;
        border-collapse: separate; border-spacing: 0;
        font-size: .9rem; font-variant-numeric: tabular-nums;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-lg);
        overflow: hidden;
        box-shadow: var(--shadow);
    }
    .schedule-table th {
        background: var(--surface-soft);
        color: var(--text); font-weight: 600;
        padding: 12px 10px;
        border-bottom: 1px solid var(--border);
        white-space: nowrap; line-height: 1.25;
    }
    .schedule-table th .th-day  { font-size: .82rem; }
    .schedule-table th .th-date { font-size: .7rem; color: var(--muted); font-weight: 500; margin-top: 1px; }
    .schedule-table td {
        padding: 11px 10px; text-align: center; font-weight: 550;
        border-bottom: 1px solid var(--border-soft);
        transition: filter .15s ease;
    }
    .schedule-table tbody tr:last-child td { border-bottom: none; }
    .schedule-table tbody tr:hover td { filter: brightness(.985); }

    /* 班次底色（低饱和） */
    .cell-rest     { background: #f0f1f3 !important; color: #8a929b !important; font-weight: 500 !important; }
    .cell-early    { background: #f6efe2 !important; color: #8a6d3b !important; }
    .cell-mid      { background: #e8eef4 !important; color: #3f6088 !important; }
    .cell-late     { background: #efeaf2 !important; color: #6f5688 !important; }
    .cell-office   { background: #e9efe9 !important; color: #4f6f56 !important; }
    .cell-external { background: #f4ece5 !important; color: #93613f !important; }

    /* 姓名列：左对齐、固定、发丝分隔 */
    .schedule-table th:first-child,
    .schedule-table td:first-child {
        position: sticky; left: 0; z-index: 1;
        text-align: left; padding-left: 16px;
        background: var(--surface) !important;
        color: var(--ink) !important; font-weight: 650;
        white-space: nowrap;
        box-shadow: 1px 0 0 var(--border-soft);
    }
    .schedule-table th:first-child { background: var(--surface-soft) !important; }

    /* ===== 人员小卡片（工时对账） ===== */
    .staff-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-md);
        padding: 14px 16px;
        margin: 6px 0;
        box-shadow: var(--shadow);
        height: 100%;
    }
    .staff-card-name {
        font-size: .98rem; font-weight: 650; color: var(--ink);
        margin-bottom: 6px; letter-spacing: -.01em;
    }
    .staff-card-stats { font-size: .82rem; color: var(--text); line-height: 1.55; }
    .staff-card-workdays { font-weight: 650; color: var(--accent); font-variant-numeric: tabular-nums; }
    .staff-card-rest { color: var(--muted); }
    .staff-card-badge {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        font-size: .73rem; font-weight: 600; line-height: 1.5;
        margin: 3px 3px 0 0; border: 1px solid transparent;
        font-variant-numeric: tabular-nums;
    }
    .badge-rest     { background: #f0f1f3; color: #8a929b; border-color: #e4e6ea; }
    .badge-early    { background: #f6efe2; color: #8a6d3b; border-color: #e9ddc6; }
    .badge-mid      { background: #e8eef4; color: #3f6088; border-color: #d3deeb; }
    .badge-late     { background: #efeaf2; color: #6f5688; border-color: #ddd2e6; }
    .badge-office   { background: #e9efe9; color: #4f6f56; border-color: #d4e1d4; }
    .badge-external { background: #f4ece5; color: #93613f; border-color: #ead8cb; }

    /* ===== 校验结果 ===== */
    .vbar {
        display: flex; align-items: center; gap: 10px;
        padding: 12px 16px; border-radius: var(--r-md);
        font-weight: 600; font-size: .9rem; margin: 4px 0;
    }
    .vbar.pass { background: #eef3ee; color: var(--good); border: 1px solid #d4e1d4; }
    .vbar.fail { background: #f6ecea; color: var(--bad);  border: 1px solid #e7d0cd; }
    .vbar .ico {
        display: inline-flex; align-items: center; justify-content: center;
        width: 20px; height: 20px; border-radius: 999px; flex: none;
        color: #fff; font-size: .72rem; font-weight: 700;
    }
    .vbar.pass .ico { background: var(--good); }
    .vbar.fail .ico { background: var(--bad); }
    .vlist {
        margin: 6px 0 0; padding: 12px 16px;
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--r-md); font-size: .85rem; color: var(--text);
    }
    .vlist li { margin: 3px 0; }

    /* ===== 信息条 / 提示 ===== */
    .note {
        background: var(--accent-soft);
        border-left: 3px solid var(--accent);
        padding: 12px 16px; border-radius: 0 var(--r-sm) var(--r-sm) 0;
        margin: 10px 0; font-size: .88rem; line-height: 1.55; color: var(--accent-strong);
    }
    .tip { font-size: .8rem; color: var(--muted); }
    .rule { height: 1px; background: var(--border); margin: 1.6rem 0; }

    /* ===== Streamlit 控件微调 ===== */
    /* 按钮 */
    .stButton > button, .stDownloadButton > button {
        border-radius: var(--r-sm); font-weight: 600;
        border: 1px solid var(--border); background: var(--surface); color: var(--ink);
        transition: border-color .15s ease, box-shadow .15s ease, background .15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: #cfd4da; box-shadow: var(--shadow);
    }
    .stButton > button[kind="primary"] {
        background: var(--accent); border-color: var(--accent); color: #fff;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--accent-strong); border-color: var(--accent-strong);
    }

    /* 输入类控件 */
    [data-baseweb="input"], [data-baseweb="select"] > div,
    .stNumberInput input, .stTextInput input {
        border-radius: var(--r-sm) !important;
    }

    /* 表格容器 */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border: 1px solid var(--border); border-radius: var(--r-md);
        overflow: hidden; box-shadow: var(--shadow);
    }

    /* 折叠面板 */
    [data-testid="stExpander"] {
        border: 1px solid var(--border); border-radius: var(--r-md);
        background: var(--surface); box-shadow: var(--shadow);
    }
    [data-testid="stExpander"] summary { font-weight: 600; }

    /* 带边框容器（st.container(border=True)） */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--r-lg) !important;
    }

    /* 单选（班次模式）横排间距 */
    [role="radiogroup"] { gap: 1.2rem; }

    /* 减少默认 alert 的视觉噪音 */
    [data-testid="stAlert"] { border-radius: var(--r-md); }

    /* ===== 响应式 ===== */
    @media (max-width: 820px) {
        .block-container { padding-top: 1.4rem; }
        .schedule-table { font-size: .76rem; }
        .schedule-table th, .schedule-table td { padding: 7px 6px; }
        .kpi .val { font-size: 1.35rem; }
    }

    /* ===== 主播排班线上版风格覆盖 ===== */
    :root {
        --bg: #0f0f13;
        --surface: #17171e;
        --surface-soft: #1e1e28;
        --ink: #f0f0f5;
        --text: #c7c7d8;
        --muted: #9090a8;
        --border: rgba(255,255,255,.08);
        --border-soft: rgba(255,255,255,.055);
        --accent: #6c63ff;
        --accent-strong: #8b84ff;
        --accent-soft: rgba(108,99,255,.12);
        --gold: #f0b429;
        --gold-soft: rgba(240,180,41,.1);
        --good: #34d399;
        --warn: #f0b429;
        --bad: #f87171;
        --blue: #60a5fa;
        --r-sm: 8px;
        --r-md: 8px;
        --r-lg: 8px;
        --shadow: none;
    }

    html, body, .stApp, [class*="css"] {
        letter-spacing: 0 !important;
    }
    .stApp {
        background: var(--bg);
        color: var(--ink);
    }
    .main .block-container,
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] .block-container {
        padding: 0 10px 1rem;
    }
    .sidebar-brand {
        padding: 22px 10px 18px;
        border-bottom: 1px solid var(--border);
        margin: 0 -10px 10px;
    }
    .sidebar-brand-title {
        font-size: 15px;
        font-weight: 750;
        line-height: 1.3;
        background: linear-gradient(135deg, var(--accent-strong), var(--gold));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sidebar-brand-sub {
        color: #5a5a72;
        font-size: 11px;
        margin-top: 3px;
    }
    .sidebar-foot {
        color: #5a5a72;
        font-size: 11px;
        padding: 12px 8px 4px;
        border-top: 1px solid var(--border);
        margin-top: 12px;
    }
    [data-testid="stSidebarNav"] ul {
        gap: 2px;
    }
    [data-testid="stSidebarNav"] a {
        color: var(--muted) !important;
        border-radius: var(--r-sm);
        padding: 10px 12px !important;
        border: 1px solid transparent;
    }
    [data-testid="stSidebarNav"] a:hover {
        background: var(--surface-soft);
        color: var(--ink) !important;
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: var(--accent-soft);
        color: var(--accent-strong) !important;
        border-color: rgba(108,99,255,.25);
    }

    .page-head {
        margin-bottom: 1.8rem;
    }
    .page-head h1 {
        color: var(--ink);
        font-size: 22px;
        font-weight: 750;
        letter-spacing: 0;
        margin-bottom: 6px;
    }
    .page-head p {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.6;
    }
    .page-head .rule,
    .rule {
        background: var(--border);
    }

    .sec {
        align-items: center;
        gap: 8px;
        margin: 1.7rem 0 .9rem;
    }
    .sec::before {
        display: none;
    }
    .sec::after {
        content: "";
        height: 1px;
        flex: 1;
        background: var(--border);
    }
    .sec .t {
        color: var(--muted);
        font-size: 13px;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: .06em;
    }
    .sec .s {
        color: #5a5a72;
        font-size: 12px;
        text-transform: none;
        letter-spacing: 0;
    }

    .kpi,
    .staff-card,
    [data-testid="stExpander"],
    [data-testid="stDataFrame"],
    [data-testid="stDataEditor"],
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        box-shadow: none !important;
    }
    .kpi {
        padding: 14px 16px;
    }
    .kpi .lab {
        color: #5a5a72;
        letter-spacing: .06em;
    }
    .kpi .val {
        color: var(--ink);
        font-size: 24px;
        letter-spacing: 0;
    }
    .kpi .val.good,
    .staff-card-workdays {
        color: var(--good);
    }
    .kpi .val.warn {
        color: var(--warn);
    }
    .kpi .val.bad {
        color: var(--bad);
    }
    .kpi .sub,
    .staff-card-stats,
    .staff-card-rest,
    .tip {
        color: var(--muted);
    }
    .staff-card-name {
        color: var(--ink);
    }

    .note {
        background: var(--accent-soft);
        border: 1px solid rgba(108,99,255,.25);
        border-left-width: 1px;
        color: var(--accent-strong);
        border-radius: var(--r-sm);
    }
    [data-testid="stAlert"] {
        background: var(--surface-soft);
        color: var(--text);
        border-color: var(--border);
    }

    .stButton > button,
    .stDownloadButton > button {
        background: transparent;
        border: 1px solid rgba(255,255,255,.14);
        border-radius: var(--r-sm);
        color: var(--text);
        font-weight: 650;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: var(--surface-soft);
        border-color: rgba(108,99,255,.45);
        color: var(--ink);
        box-shadow: none;
    }
    .stButton > button[kind="primary"] {
        background: var(--accent);
        border-color: var(--accent);
        color: #fff;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--accent-strong);
        border-color: var(--accent-strong);
    }

    label,
    [data-testid="stWidgetLabel"],
    [data-testid="stMarkdownContainer"],
    [data-testid="stText"] {
        color: var(--text);
    }
    [data-baseweb="input"],
    [data-baseweb="select"] > div,
    .stNumberInput input,
    .stTextInput input,
    textarea,
    div[data-baseweb="textarea"] textarea {
        background: var(--surface-soft) !important;
        border-color: var(--border) !important;
        color: var(--ink) !important;
        border-radius: var(--r-sm) !important;
    }
    [data-baseweb="input"]:focus-within,
    [data-baseweb="select"] > div:focus-within,
    div[data-baseweb="textarea"]:focus-within {
        border-color: var(--accent) !important;
    }
    [role="radiogroup"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label {
        color: var(--text);
    }

    [data-testid="stExpander"] summary {
        color: var(--ink);
        font-weight: 650;
    }
    [data-testid="stExpander"] details {
        color: var(--text);
    }

    .schedule-table {
        background: var(--surface);
        border-color: var(--border);
        border-radius: var(--r-md);
        color: var(--text);
        box-shadow: none;
    }
    .schedule-table th {
        background: var(--surface-soft);
        color: var(--muted);
        border-bottom-color: rgba(255,255,255,.14);
        font-size: 11px;
        letter-spacing: 0;
    }
    .schedule-table td {
        border-bottom-color: var(--border);
        color: var(--text);
    }
    .schedule-table th:first-child,
    .schedule-table td:first-child {
        background: var(--surface) !important;
        color: var(--ink) !important;
        box-shadow: 1px 0 0 var(--border);
    }
    .schedule-table th:first-child {
        background: var(--surface-soft) !important;
    }
    .schedule-table th .th-date {
        color: #5a5a72;
    }
    .cell-rest     { background: rgba(255,255,255,.045) !important; color: #9090a8 !important; }
    .cell-early    { background: rgba(240,180,41,.1) !important; color: #f0b429 !important; }
    .cell-mid      { background: rgba(96,165,250,.1) !important; color: #60a5fa !important; }
    .cell-late     { background: rgba(108,99,255,.12) !important; color: #8b84ff !important; }
    .cell-office   { background: rgba(52,211,153,.1) !important; color: #34d399 !important; }
    .cell-external { background: rgba(251,146,60,.1) !important; color: #fb923c !important; }
    .badge-rest     { background: rgba(255,255,255,.055); color: #9090a8; border-color: var(--border); }
    .badge-early    { background: rgba(240,180,41,.1); color: #f0b429; border-color: rgba(240,180,41,.2); }
    .badge-mid      { background: rgba(96,165,250,.1); color: #60a5fa; border-color: rgba(96,165,250,.2); }
    .badge-late     { background: rgba(108,99,255,.12); color: #8b84ff; border-color: rgba(108,99,255,.25); }
    .badge-office   { background: rgba(52,211,153,.1); color: #34d399; border-color: rgba(52,211,153,.2); }
    .badge-external { background: rgba(251,146,60,.1); color: #fb923c; border-color: rgba(251,146,60,.2); }

    .vbar.pass {
        background: rgba(52,211,153,.1);
        color: var(--good);
        border: 1px solid rgba(52,211,153,.2);
    }
    .vbar.fail {
        background: rgba(248,113,113,.1);
        color: var(--bad);
        border: 1px solid rgba(248,113,113,.2);
    }
    .vlist {
        background: var(--surface);
        border-color: var(--border);
        color: var(--text);
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,.14); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #5a5a72; }
</style>
"""


def apply_styles():
    """注入全局 CSS。每个页面开头调用一次。"""
    st.markdown(STYLES, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 版式辅助函数（页面复用，避免散落内联 HTML）
# ─────────────────────────────────────────────

def page_header(title: str, subtitle: str = "", rule: bool = True):
    """页面顶部标题区。"""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    line = '<div class="rule"></div>' if rule else ""
    st.markdown(
        f'<div class="page-head"><h1>{title}</h1>{sub}{line}</div>',
        unsafe_allow_html=True,
    )


def section_title(text: str, sub: str = ""):
    """区块小标题（左侧钢蓝竖条）。"""
    s = f'<span class="s">{sub}</span>' if sub else ""
    st.markdown(f'<div class="sec"><span class="t">{text}</span>{s}</div>',
                unsafe_allow_html=True)


def kpi_row(items):
    """一行 KPI 磁贴。

    Args:
        items: [(label, value, tone), ...]，tone ∈ {'', 'good', 'warn', 'bad'}，
               或 (label, value, tone, sub) 带副标题。
    """
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, tone = item[0], item[1], (item[2] if len(item) > 2 else "")
        sub = item[3] if len(item) > 3 else ""
        sub_html = f'<div class="sub">{sub}</div>' if sub else ""
        with col:
            st.markdown(
                f'<div class="kpi"><div class="lab">{label}</div>'
                f'<div class="val {tone}">{value}</div>{sub_html}</div>',
                unsafe_allow_html=True,
            )


def note(text: str):
    """钢蓝信息条。"""
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def divider():
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 班次 → CSS class 映射（组件使用，接口保持稳定）
# ─────────────────────────────────────────────

def get_cell_class(assignment_label: str) -> str:
    """根据班次中文名返回单元格 CSS class。"""
    return {
        "休息": "cell-rest",
        "早班": "cell-early",
        "中班": "cell-mid",
        "晚班": "cell-late",
        "坐班": "cell-office",
        "外派": "cell-external",
        "白班": "cell-early",
        "午班": "cell-late",
    }.get(assignment_label, "")


def get_badge_class(assignment_label: str) -> str:
    """根据班次中文名返回徽章 CSS class。"""
    return {
        "休息": "badge-rest",
        "早班": "badge-early",
        "中班": "badge-mid",
        "晚班": "badge-late",
        "坐班": "badge-office",
        "外派": "badge-external",
        "白班": "badge-early",
        "午班": "badge-late",
    }.get(assignment_label, "")
