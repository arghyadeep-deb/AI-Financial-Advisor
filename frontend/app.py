import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import json

# ─── Config ───────────────────────────────────────────────────────────────────

API_URL = "https://ai-financial-advisor-1-fac2.onrender.com"

st.set_page_config(
    page_title            = "FinAdvisor AI",
    page_icon             = "💰",
    layout                = "wide",
    initial_sidebar_state = "expanded"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg: #090f1a;
    --surface: #0f1726;
    --surface-2: #131d2f;
    --text-1: #e6edf7;
    --text-2: #93a4bc;
    --border: #223149;
    --accent: #14b8a6;
    --accent-2: #3b82f6;
    --warn: #f59e0b;
    --danger: #fb7185;
}

html, body, [class*="css"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {
    font-family:      'Inter', sans-serif !important;
    background:
        radial-gradient(1200px 450px at 8% -10%, rgba(20, 184, 166, 0.16), transparent 58%),
        radial-gradient(1200px 500px at 95% -25%, rgba(59, 130, 246, 0.16), transparent 60%),
        var(--bg) !important;
    color: var(--text-1) !important;
}

/* ── Hide menu and footer but keep header for sidebar toggle ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* Minimal transparent header — only shows sidebar toggle */
header {
    background:  transparent !important;
    box-shadow:  none !important;
    height:      2.5rem !important;
}
[data-testid="stHeader"] {
    background:  transparent !important;
    box-shadow:  none !important;
}

/* Style the sidebar collapse/expand toggle button */
[data-testid="collapsedControl"] {
    visibility:    visible !important;
    display:       flex !important;
    background:    #0f1726 !important;
    border:        1px solid #223149 !important;
    border-radius: 8px !important;
    color:         #e6edf7 !important;
    margin-top:    0.4rem !important;
    margin-left:   0.4rem !important;
}
[data-testid="collapsedControl"]:hover {
    background:    #1c2b44 !important;
    border-color:  #2f4668 !important;
}

/* ── Main container ── */
.main .block-container {
    padding-top:    0.65rem !important;
    padding-bottom: 2rem;
    max-width:      1280px;
}

p, span, div, label, h1, h2, h3, h4, h5, h6 {
    color: var(--text-1) !important;
}

[data-testid="column"] > div {
    height: 100%;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(185deg, #0b1220 0%, #101a2d 100%) !important;
    min-width: 238px !important;
    max-width: 238px !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * {
    color: #9fb1c9 !important;
}
section[data-testid="stSidebar"] .stButton button {
    background:     transparent !important;
    border:         none !important;
    color:          #94a3b8 !important;
    text-align:     left !important;
    font-size:      0.88rem !important;
    padding:        0.45rem 1rem !important;
    border-radius:  8px !important;
    width:          100% !important;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(20, 184, 166, 0.15) !important;
    color:      #dff8f5 !important;
}

/* ── Navbar ── */
.navbar {
    background:      var(--surface);
    border:          1px solid var(--border);
    border-radius:   12px;
    padding:         0.8rem 1.5rem;
    display:         flex;
    justify-content: space-between;
    align-items:     center;
    margin-bottom:   1.5rem;
    box-shadow:      0 8px 24px rgba(2, 6, 23, 0.42);
}
.navbar-logo {
    font-size:   1.25rem;
    font-weight: 800;
    background:  linear-gradient(135deg, var(--accent), var(--accent-2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.navbar-user {
    color:     var(--text-2) !important;
    font-size: 0.83rem;
}

/* ── Metric cards ── */
.metric-card {
    background:     var(--surface);
    border:         1px solid var(--border);
    border-radius:  16px;
    padding:        1rem 1.1rem;
    min-height:     130px;
    display:        flex;
    flex-direction: column;
    justify-content:space-between;
    box-shadow:     0 10px 24px rgba(2, 6, 23, 0.35);
}
.metric-value {
    font-size:   1.75rem;
    font-weight: 800;
    color:       var(--text-1) !important;
    line-height: 1.2;
}
.metric-label {
    font-size:      0.75rem;
    color:          var(--text-2) !important;
    font-weight:    500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top:     0.25rem;
}
.metric-delta {
    font-size:   0.75rem;
    color:       var(--accent) !important;
    font-weight: 600;
    margin-top:  0.3rem;
}

/* ── Section header ── */
.section-header {
    font-size:    1.06rem;
    font-weight:  700;
    color:        var(--text-1) !important;
    border-left:  3px solid var(--accent);
    padding-left: 0.7rem;
    margin:       1.35rem 0 0.9rem;
}

/* ── Cards ── */
.card {
    background:    var(--surface);
    border:        1px solid var(--border);
    border-radius: 12px;
    padding:       1.1rem 1.2rem;
    margin-bottom: 0.7rem;
    box-shadow:    0 8px 18px rgba(2, 6, 23, 0.3);
}
.card p, .card div, .card span { color: var(--text-1) !important; }
.card-green  { border-left: 3px solid var(--accent); }
.card-blue   { border-left: 3px solid var(--accent-2); }
.card-orange { border-left: 3px solid #f59e0b; }

/* ── Badge ── */
.badge {
    display:        inline-block;
    padding:        3px 10px;
    border-radius:  20px;
    font-size:      0.72rem;
    font-weight:    700;
    letter-spacing: 0.01em;
    background:     rgba(20, 184, 166, 0.22);
    border:         1px solid rgba(20, 184, 166, 0.45);
    color:          #c9fffa !important;
    margin-bottom:  0.3rem;
}
.card .badge {
    color:       #c9fffa !important;
    background:  rgba(20, 184, 166, 0.22) !important;
    border:      1px solid rgba(20, 184, 166, 0.45) !important;
}

/* ── Alerts ── */
.alert {
    padding:       0.75rem 1rem;
    border-radius: 10px;
    margin-bottom: 0.6rem;
    font-size:     0.87rem;
}
.alert * { color: inherit !important; }
.alert-success {
    background: rgba(16, 185, 129, 0.12);
    border:     1px solid rgba(16, 185, 129, 0.35);
    color:      #8bf3cf !important;
}
.alert-warning {
    background: rgba(245, 158, 11, 0.12);
    border:     1px solid rgba(245, 158, 11, 0.35);
    color:      #ffd58a !important;
}
.alert-info {
    background: rgba(59, 130, 246, 0.14);
    border:     1px solid rgba(59, 130, 246, 0.38);
    color:      #c7dfff !important;
}
.alert-error {
    background: rgba(251, 113, 133, 0.14);
    border:     1px solid rgba(251, 113, 133, 0.35);
    color:      #ffc2cf !important;
}

/* ── Hero ── */
.hero {
    background:    linear-gradient(135deg, #0b1220 0%, #1e3a8a 45%, #0f766e 100%);
    border-radius: 20px;
    padding:       4rem 3rem;
    text-align:    center;
    color:         white !important;
    margin-bottom: 2rem;
}
.hero * { color: white !important; }
.hero h1 {
    font-size:   2.8rem;
    font-weight: 800;
    margin:      0 0 1rem;
    color:       white !important;
}
.hero p {
    color:         #d5deea !important;
    font-size:     1.05rem;
    margin-bottom: 2rem;
}

/* ── Progress bar ── */
.prog-row { margin-bottom: 0.55rem; }
.prog-label {
    display:         flex;
    justify-content: space-between;
    font-size:       0.8rem;
    color:           var(--text-2) !important;
    margin-bottom:   0.2rem;
}

/* ── SIP row ── */
.sip-row {
    background:      var(--surface);
    border:          1px solid var(--border);
    border-left:     3px solid var(--accent);
    border-radius:   10px;
    padding:         0.8rem 1.1rem;
    margin-bottom:   0.5rem;
    display:         flex;
    justify-content: space-between;
    align-items:     center;
}
.sip-name { font-weight: 600; font-size: 0.88rem; color: var(--text-1) !important; }
.sip-cat  { font-size: 0.75rem; color: var(--text-2) !important; margin-top: 1px; }
.sip-amt  { font-size: 1.05rem; font-weight: 700; color: var(--accent) !important; }

/* ── Credit card widget ── */
.cc-card {
    border-radius: 16px;
    padding:       1.4rem;
    position:      relative;
    overflow:      hidden;
    min-height:    155px;
    box-shadow:    0 4px 20px rgba(0,0,0,0.15);
    margin-bottom: 0.5rem;
}
.cc-card * { color: white !important; }
.cc-circle-1 {
    position:      absolute; right: -25px; top: -25px;
    width: 110px; height: 110px; border-radius: 50%;
    background:    rgba(255,255,255,0.06);
}
.cc-circle-2 {
    position:      absolute; right: 20px; bottom: -35px;
    width: 90px; height: 90px; border-radius: 50%;
    background:    rgba(255,255,255,0.06);
}

/* ── Chat messages ── */
.chat-msg-user {
    background:    linear-gradient(135deg, var(--accent), var(--accent-2));
    padding:       0.6rem 0.9rem;
    border-radius: 16px 16px 4px 16px;
    margin:        0.3rem 0 0.3rem auto;
    max-width:     80%;
    font-size:     0.85rem;
    width:         fit-content;
    word-wrap:     break-word;
}
.chat-msg-user * { color: white !important; }
.chat-msg-bot {
    background:    #16243a;
    border:        1px solid var(--border);
    padding:       0.6rem 0.9rem;
    border-radius: 16px 16px 16px 4px;
    margin:        0.3rem auto 0.3rem 0;
    max-width:     80%;
    font-size:     0.85rem;
    width:         fit-content;
    word-wrap:     break-word;
}
.chat-msg-bot * { color: #e9f0fb !important; }

/* ── Typing animation ── */
.typing-indicator {
    display:       flex;
    gap:           4px;
    padding:       0.6rem 0.9rem;
    background:    #16243a;
    border:        1px solid var(--border);
    border-radius: 16px;
    width:         fit-content;
    margin:        0.3rem 0;
}
.typing-dot {
    width:         6px; height: 6px;
    border-radius: 50%;
    background:    #94a3b8;
    animation:     typing 1.4s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
    0%, 100% { opacity: 0.3; transform: scale(0.85); }
    50%       { opacity: 1;   transform: scale(1.1); }
}

/* ── Buttons ── */
.stButton button {
    border-radius: 10px !important;
    font-weight:   600 !important;
    color:         var(--text-1) !important;
    border:        1px solid var(--border) !important;
    background:    #162238 !important;
    min-height:    46px !important;
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
    border:     none !important;
    color:      white !important;
}
.stButton button[kind="primary"] * { color: white !important; }
.stButton button:not([kind="primary"]) {
    background: var(--surface) !important;
    color:      var(--text-1) !important;
}
.stButton button:not([kind="primary"]):hover {
    background:   #1c2c45 !important;
    border-color: #2f4668 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background:    #132136;
    border-radius: 10px;
    padding:       4px;
    gap:           4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight:   500;
    font-size:     0.86rem;
    color:         var(--text-2) !important;
}
.stTabs [aria-selected="true"] {
    background:  #1c2b44 !important;
    box-shadow:  0 2px 8px rgba(0,0,0,0.25) !important;
    font-weight: 600 !important;
    color:       var(--text-1) !important;
}

/* ── Form inputs ── */
.stTextInput input,
.stNumberInput input,
.stSelectbox select {
    background:    #16243a !important;
    color:         var(--text-1) !important;
    border:        1px solid var(--border) !important;
    border-radius: 8px !important;
}
.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stSlider label,
.stMultiSelect label {
    color:       var(--text-2) !important;
    font-weight: 500 !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background:    #16243a !important;
    color:         var(--text-1) !important;
    border-radius: 8px !important;
    font-weight:   600 !important;
}
.streamlit-expanderContent {
    background: #131f33 !important;
    color:      var(--text-1) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow:      hidden !important;
}

/* ── Metric widget ── */
[data-testid="metric-container"] {
    background:    var(--surface);
    border:        1px solid var(--border);
    border-radius: 12px;
    padding:       0.8rem 1rem;
}
[data-testid="metric-container"] label {
    color: var(--text-2) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text-1) !important;
}
section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #d9e7fb !important;
}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: #93a4bc !important;
}

@media (max-width: 900px) {
    .main .block-container {
        padding-top:   0.4rem !important;
        padding-left:  0.9rem !important;
        padding-right: 0.9rem !important;
    }
    .hero { padding: 2.1rem 1.4rem; }
    .hero h1 { font-size: 2rem; }
}
</style>
""", unsafe_allow_html=True)


# ─── Session State ────────────────────────────────────────────────────────────

def init_session():
    defaults = {
        "token":           None,
        "user_id":         None,
        "user_name":       None,
        "user_email":      None,
        "page":            "landing",
        "chat_open":       False,
        "chat_messages":   [],
        "chat_thread_id":  None,
        "cached_health":   None,
        "cached_invest":   None,
        "cached_credit":   None,
        "cached_summary":  None,
        "cached_sim":      None,
        "cached_opt":      None,
        "cached_rebalance":None,
        "profile_cache":   None,
        "analysis_ran":    False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()


# ─── API Helpers ──────────────────────────────────────────────────────────────

def api_post(endpoint: str, data: dict, auth: bool = False) -> dict:
    headers = {"Content-Type": "application/json"}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        resp = requests.post(
            f"{API_URL}{endpoint}",
            json=data, headers=headers, timeout=180
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def api_get(endpoint: str) -> dict:
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        resp = requests.get(
            f"{API_URL}{endpoint}",
            headers=headers, timeout=30
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def is_logged_in() -> bool:
    return st.session_state.token is not None


def go_to(page: str):
    st.session_state.page = page
    st.rerun()


def fmt_inr(amount) -> str:
    try:
        amount = float(amount)
        if amount >= 10000000: return f"₹{amount/10000000:.1f}Cr"
        elif amount >= 100000: return f"₹{amount/100000:.1f}L"
        elif amount >= 1000:   return f"₹{amount/1000:.1f}K"
        else:                  return f"₹{amount:,.0f}"
    except Exception:
        return "₹0"


def _queue_chat_message(message: str):
    clean = (message or "").strip()
    if not clean:
        return
    st.session_state.chat_messages.append({"role": "user", "content": clean})
    st.session_state["pending_chat"]      = clean
    st.session_state["chat_input_draft"]  = ""


def _submit_chat_from_draft():
    _queue_chat_message(st.session_state.get("chat_input_draft", ""))


# ─── Analysis Cache ───────────────────────────────────────────────────────────

def load_and_cache_analysis():
    if st.session_state.analysis_ran:
        return
    last = api_get("/analysis/last")
    if last.get("found") and last.get("results"):
        r = last["results"]
        st.session_state.cached_health    = r.get("health",     {})
        st.session_state.cached_invest    = r.get("investment", {})
        st.session_state.cached_credit    = r.get("credit",     {})
        st.session_state.cached_summary   = r.get("summary",    {})
        st.session_state.cached_sim       = r.get("simulation", {})
        st.session_state.cached_opt       = r.get("optimizer",  {})
        st.session_state.cached_rebalance = r.get("rebalance",  {})
        st.session_state.analysis_ran     = True


def refresh_analysis():
    st.session_state.analysis_ran     = False
    st.session_state.cached_health    = None
    st.session_state.cached_invest    = None
    st.session_state.cached_credit    = None
    st.session_state.cached_summary   = None
    st.session_state.cached_sim       = None
    st.session_state.cached_opt       = None
    st.session_state.cached_rebalance = None
    load_and_cache_analysis()


# ─── Charts ───────────────────────────────────────────────────────────────────

def pie_chart(labels, values, title="", height=300):
    colors = ["#0ea5a4","#2563eb","#f59e0b","#be185d","#7c3aed","#0891b2"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker_colors=colors[:len(labels)],
        textinfo="label+percent", textfont_size=12
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#d9e7fb")),
        height=height, margin=dict(t=40,b=10,l=10,r=10),
        paper_bgcolor="#0f1726", plot_bgcolor="#0f1726",
        showlegend=True, legend=dict(font=dict(size=11, color="#c3d5ef"))
    )
    return fig


def bar_chart(labels, values, title="", height=300, color="#0ea5a4"):
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=color,
        text=[fmt_inr(v) for v in values],
        textposition="outside", textfont=dict(size=11, color="#d9e7fb")
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#d9e7fb")),
        height=height, margin=dict(t=40,b=10,l=10,r=10),
        paper_bgcolor="#0f1726", plot_bgcolor="#0f1726",
        yaxis=dict(showgrid=True, gridcolor="#223149", showticklabels=False),
        xaxis=dict(showgrid=False, tickfont=dict(color="#c3d5ef"))
    )
    return fig


def line_chart(x, y1, y2, name1, name2, title="", height=300):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y1, name=name1,
        line=dict(color="#cbd5e1", width=2, dash="dash"),
        mode="lines+markers", marker=dict(size=6)
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y2, name=name2,
        line=dict(color="#0ea5a4", width=3),
        mode="lines+markers", fill="tonexty",
        fillcolor="rgba(14,165,164,0.10)",
        marker=dict(size=8)
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#d9e7fb")),
        height=height, margin=dict(t=40,b=10,l=10,r=10),
        paper_bgcolor="#0f1726", plot_bgcolor="#0f1726",
        yaxis=dict(showgrid=True, gridcolor="#223149",
                   tickfont=dict(color="#c3d5ef")),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=-0.18,
                    font=dict(size=11, color="#c3d5ef"))
    )
    return fig


def gauge_chart(value, title="", height=270):
    color = "#0ea5a4" if value>=70 else "#f59e0b" if value>=50 else "#ef4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={"text": title, "font": {"size": 14, "color": "#d9e7fb"}},
        number={"font": {"size": 38, "color": color}},
        gauge={
            "axis":  {"range": [0,100], "tickwidth":1, "tickcolor":"#3d4f6c"},
            "bar":   {"color": color, "thickness": 0.6},
            "bgcolor": "#0f1726", "borderwidth": 0,
            "steps": [
                {"range": [0,  50], "color": "#3b1220"},
                {"range": [50, 70], "color": "#3f2a10"},
                {"range": [70,100], "color": "#0f2e2c"}
            ]
        }
    ))
    fig.update_layout(
        height=height, margin=dict(t=30,b=10,l=20,r=20),
        paper_bgcolor="#0f1726"
    )
    return fig


# ─── Bank Logos & Card Colors ─────────────────────────────────────────────────

BANK_LOGOS = {
    "hdfc":     "https://logo.clearbit.com/hdfcbank.com",
    "sbi":      "https://logo.clearbit.com/onlinesbi.sbi.co.in",
    "icici":    "https://logo.clearbit.com/icicibank.com",
    "axis":     "https://logo.clearbit.com/axisbank.com",
    "kotak":    "https://logo.clearbit.com/kotak.com",
    "amex":     "https://logo.clearbit.com/americanexpress.com",
    "american": "https://logo.clearbit.com/americanexpress.com",
    "idfc":     "https://logo.clearbit.com/idfcfirstbank.com",
    "yes":      "https://logo.clearbit.com/yesbank.in",
    "rbl":      "https://logo.clearbit.com/rblbank.com",
    "au":       "https://logo.clearbit.com/aubank.in",
    "indusind": "https://logo.clearbit.com/indusind.com",
    "federal":  "https://logo.clearbit.com/federalbank.co.in",
    "citi":     "https://logo.clearbit.com/citibank.com",
    "hsbc":     "https://logo.clearbit.com/hsbc.co.in"
}

CARD_COLORS = {
    "infinia":   "#0f172a", "diners":    "#1e3a5f",
    "regalia":   "#1e1b4b", "millennia": "#1d4ed8",
    "moneyback": "#065f46", "amazon":    "#c2410c",
    "flipkart":  "#6d28d9", "magnus":    "#0c1445",
    "atlas":     "#0f3460", "ace":       "#14532d",
    "simplyone": "#1e293b", "platinum":  "#374151",
    "cashback":  "#134e4a", "default":   "#0f172a"
}


def get_bank_logo(bank_name: str) -> str:
    for key, url in BANK_LOGOS.items():
        if key in bank_name.lower():
            return url
    return ""


def get_card_color(card_name: str) -> str:
    for key, color in CARD_COLORS.items():
        if key in card_name.lower():
            return color
    return CARD_COLORS["default"]


# ─── Credit Card Widget ───────────────────────────────────────────────────────

def render_credit_card_widget(card: dict, rank: int):
    card_name  = card.get("card_name", "")
    bank       = card.get("bank", "")
    annual_fee = card.get("annual_fee", 0)
    savings    = card.get("estimated_annual_savings", 0)
    why        = card.get("why_recommended", "")
    benefits   = card.get("key_benefits", [])
    watch_out  = card.get("watch_out", "")
    card_color = get_card_color(card_name)
    bank_logo  = get_bank_logo(bank)
    rank_emoji = "🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else "💳"

    logo_html = (
        f'<img src="{bank_logo}" style="height:22px;width:auto;'
        f'filter:brightness(0) invert(1);" onerror="this.style.display=\'none\'">'
        if bank_logo else "💳"
    )

    st.markdown(f"""
    <div class="cc-card"
         style="background:linear-gradient(135deg,{card_color} 0%,{card_color}dd 100%);">
        <div class="cc-circle-1"></div>
        <div class="cc-circle-2"></div>
        <div style="display:flex;justify-content:space-between;
                    align-items:center;margin-bottom:1rem;">
            <div style="background:rgba(255,255,255,0.15);padding:4px 10px;
                        border-radius:6px;display:inline-flex;align-items:center;">
                {logo_html}
            </div>
            <span style="font-size:1.3rem;">{rank_emoji}</span>
        </div>
        <div style="font-size:1rem;font-weight:700;margin-bottom:2px;">
            {card_name}
        </div>
        <div style="font-size:0.75rem;color:rgba(255,255,255,0.65);
                    margin-bottom:1rem;">{bank}</div>
        <div style="display:flex;gap:2rem;">
            <div>
                <div style="font-size:0.62rem;color:rgba(255,255,255,0.5);
                            text-transform:uppercase;letter-spacing:0.08em;">
                    Annual Fee
                </div>
                <div style="font-size:0.95rem;font-weight:700;">
                    {"FREE" if annual_fee==0 else fmt_inr(annual_fee)}
                </div>
            </div>
            <div>
                <div style="font-size:0.62rem;color:rgba(255,255,255,0.5);
                            text-transform:uppercase;letter-spacing:0.08em;">
                    Est. Savings
                </div>
                <div style="font-size:0.95rem;font-weight:700;color:#5eead4;">
                    {fmt_inr(savings)}/yr
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"📋 {card_name} — Details", expanded=(rank==1)):
        if why:
            st.markdown(f"**Why Recommended:** {why}")
        if benefits:
            st.markdown("**Key Benefits:**")
            for b in benefits:
                st.markdown(f"✅ {b}")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Annual Fee",
                      "Lifetime Free" if annual_fee==0 else fmt_inr(annual_fee))
        with c2:
            st.metric("Est. Annual Savings", fmt_inr(savings))
        if watch_out:
            st.markdown(f"""
            <div class="alert alert-warning">
                ⚠️ <b>Watch Out:</b> {watch_out}
            </div>""", unsafe_allow_html=True)


# ─── Navbar ───────────────────────────────────────────────────────────────────

def render_navbar():
    st.markdown(f"""
    <div class="navbar">
        <div class="navbar-logo">💰 FinAdvisor AI</div>
        <div class="navbar-user">
            👤 <b style="color:var(--text-1)">
                {st.session_state.user_name or 'User'}
            </b>
            &nbsp;|&nbsp; {st.session_state.user_email or ''}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:1.2rem 1rem 0.8rem;border-bottom:1px solid #1e293b;">
            <div style="font-size:1.2rem;font-weight:800;
                        background:linear-gradient(135deg,#0ea5a4,#2563eb);
                        -webkit-background-clip:text;
                        -webkit-text-fill-color:transparent;">
                💰 FinAdvisor AI
            </div>
            <div style="font-size:0.68rem;color:#9fb2ca;margin-top:2px;">
                Your Personal Finance AI
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

        pages = [
            ("🏠", "Dashboard",       "dashboard"),
            ("📊", "Portfolio",        "portfolio"),
            ("📈", "Stocks",           "stocks"),
            ("💳", "Credit Cards",     "credit"),
            ("❤️", "Financial Health", "health"),
            ("📋", "Reports",          "reports"),
            ("👤", "Profile",          "profile"),
        ]

        current = st.session_state.page

        for icon, label, page_key in pages:
            is_active = current == page_key
            if is_active:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,
                    rgba(14,165,164,0.20),rgba(37,99,235,0.14));
                    border-left:3px solid #0ea5a4;border-radius:0 8px 8px 0;
                    padding:0.45rem 1rem;font-weight:600;font-size:0.88rem;
                    margin-bottom:2px;color:#5eead4 !important;">
                    {icon}  {label}
                </div>
                """, unsafe_allow_html=True)
            else:
                if st.button(
                    f"{icon}  {label}",
                    key=f"nav_{page_key}",
                    use_container_width=True
                ):
                    st.session_state.page = page_key
                    st.rerun()

        st.markdown(
            "<hr style='border-color:#1e293b;margin:0.6rem 0'>",
            unsafe_allow_html=True
        )

        if st.button("🚪  Logout", use_container_width=True, key="logout_btn"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session()
            st.rerun()

        if st.session_state.cached_health:
            score = st.session_state.cached_health.get("overall_score", 0)
            grade = st.session_state.cached_health.get("grade", "N/A")
            if score > 0:
                color = (
                    "#00d4aa" if score>=70 else
                    "#f59e0b" if score>=50 else "#ef4444"
                )
                st.markdown(f"""
                <div style="margin:0.8rem 0.6rem 0;padding:0.8rem;
                            background:#1e293b;border-radius:10px;
                            text-align:center;">
                    <div style="font-size:0.62rem;color:#64748b;
                                text-transform:uppercase;letter-spacing:0.1em;">
                        Health Score
                    </div>
                    <div style="font-size:1.8rem;font-weight:800;
                                color:{color};line-height:1.2;margin:0.2rem 0;">
                        {score:.0f}
                    </div>
                    <div style="font-size:0.68rem;color:#64748b;">
                        Grade {grade} · out of 100
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ─── Chat Overlay ─────────────────────────────────────────────────────────────

def render_chat_overlay():
    chat_label = "💬 Chat" if not st.session_state.chat_open else "✕ Close"
    cols = st.columns([1, 1, 1, 1, 1])
    with cols[4]:
        if st.button(
            chat_label,
            key="chat_toggle_btn",
            type="primary",
            use_container_width=True
        ):
            st.session_state.chat_open = not st.session_state.chat_open
            st.rerun()

    if not st.session_state.chat_open:
        return

    st.markdown("---")

    with st.container():
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);
                    padding:0.9rem 1.2rem;border-radius:12px 12px 0 0;
                    display:flex;align-items:center;gap:0.8rem;">
            <div style="width:32px;height:32px;border-radius:50%;
                        background:linear-gradient(135deg,#0ea5a4,#2563eb);
                        display:flex;align-items:center;justify-content:center;
                        font-size:0.9rem;flex-shrink:0;">🤖</div>
            <div>
                <div style="font-weight:700;font-size:0.9rem;color:white;">
                    AI Financial Advisor
                </div>
                <div style="font-size:0.65rem;color:#94a3b8;">
                    Knows your complete profile
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("💡 Quick Questions", expanded=False):
            suggestions = [
                "Explain my health score",
                "Why this credit card?",
                "How to start a SIP?",
                "What is ELSS?",
                "My 10 year corpus?",
                "Which stock first?",
                "How to improve credit score?",
                "Explain my SIP plan"
            ]
            cols = st.columns(2)
            for i, q in enumerate(suggestions):
                with cols[i % 2]:
                    if st.button(q, key=f"sugg_{i}", use_container_width=True):
                        _queue_chat_message(q)
                        st.rerun()

        if not st.session_state.chat_messages:
            st.markdown(f"""
            <div class="chat-msg-bot">
                👋 Hi {st.session_state.user_name or 'there'}!
                I know your complete financial profile.
                Ask me anything!
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.chat_messages:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="chat-msg-user">{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="chat-msg-bot">🤖 {msg["content"]}</div>',
                        unsafe_allow_html=True
                    )

        c1, c2 = st.columns([5, 1])
        with c1:
            st.text_input(
                "msg",
                key             = "chat_input_draft",
                placeholder     = "Ask about your finances...",
                label_visibility= "collapsed",
                on_change       = _submit_chat_from_draft
            )
        with c2:
            if st.button("→", key="chat_send_btn", use_container_width=True):
                _queue_chat_message(st.session_state.get("chat_input_draft", ""))
                st.rerun()

    pending = st.session_state.pop("pending_chat", None)
    if pending:
        typing_ph = st.empty()
        typing_ph.markdown("""
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        """, unsafe_allow_html=True)

        reply_ph   = st.empty()
        full_reply = ""
        stream_ok  = False

        try:
            with requests.post(
                f"{API_URL}/chat/stream",
                json={
                    "message":   pending,
                    "thread_id": st.session_state.chat_thread_id
                },
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                stream=True, timeout=90
            ) as response:
                if response.status_code == 200:
                    typing_ph.empty()
                    stream_ok = True
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode("utf-8")
                            if line_str.startswith("data: "):
                                try:
                                    data = json.loads(line_str[6:])
                                    if "chunk" in data:
                                        full_reply += data["chunk"]
                                        reply_ph.markdown(
                                            f'<div class="chat-msg-bot">'
                                            f'🤖 {full_reply}▌</div>',
                                            unsafe_allow_html=True
                                        )
                                    elif data.get("done"):
                                        if data.get("thread_id"):
                                            st.session_state.chat_thread_id = (
                                                data["thread_id"]
                                            )
                                except json.JSONDecodeError:
                                    pass
        except Exception:
            stream_ok = False

        if not stream_ok or not full_reply:
            typing_ph.empty()
            reply_ph.empty()
            resp = api_post(
                "/chat",
                {
                    "message":   pending,
                    "thread_id": st.session_state.chat_thread_id
                },
                auth=True
            )
            full_reply = resp.get("reply", "Sorry, I had trouble. Please try again.")
            if "thread_id" in resp:
                st.session_state.chat_thread_id = resp["thread_id"]

        typing_ph.empty()
        reply_ph.empty()

        if full_reply:
            st.session_state.chat_messages.append({
                "role": "assistant", "content": full_reply
            })

        st.rerun()


# ─── PAGE: Landing ────────────────────────────────────────────────────────────

def page_landing():
    st.markdown("""
    <div class="hero">
        <h1>💰 FinAdvisor AI</h1>
        <p>Personalised investment plans, credit card recommendations,<br>
           and financial health analysis — built for India</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    features = [
        ("📊", "Portfolio Planning",
         "Complete SIP plan, stock picks, and tax strategies for your income."),
        ("💳", "Credit Card Advisor",
         "Best cards for your spend from 38 cards across all Indian banks."),
        ("❤️", "Health Score",
         "Score across 5 parameters — savings, emergency, debt, investment, credit.")
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3], features):
        with col:
            st.markdown(f"""
            <div class="card card-green" style="text-align:center;padding:1.5rem;">
                <div style="font-size:1.8rem;margin-bottom:0.7rem;">{icon}</div>
                <div style="font-weight:700;font-size:0.95rem;
                            margin-bottom:0.4rem;">{title}</div>
                <div style="color:#9fb2ca;font-size:0.83rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        if st.button("🚀 Get Started", use_container_width=True, type="primary"):
            go_to("signup")

    st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        if st.button("Login →", use_container_width=True):
            go_to("login")

    st.markdown("""
    <div style="text-align:center;margin-top:3rem;
                color:#94a3b8;font-size:0.75rem;">
        Powered by Groq · LangSmith · Graph RAG · Indian Knowledge Base
    </div>
    """, unsafe_allow_html=True)


# ─── PAGE: Login ──────────────────────────────────────────────────────────────

def page_login():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem;">
            <div style="font-size:2.2rem;">💰</div>
            <div style="font-size:1.4rem;font-weight:800;">Welcome Back</div>
            <div style="color:#9fb2ca;font-size:0.85rem;">
                Login to your FinAdvisor account
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email    = st.text_input("Email",    placeholder="you@email.com")
            password = st.text_input("Password", type="password")
            submit   = st.form_submit_button(
                "Login →", use_container_width=True, type="primary"
            )

        if submit:
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Signing in..."):
                    resp = api_post("/auth/login", {
                        "email": email, "password": password
                    })
                if "access_token" in resp:
                    st.session_state.token      = resp["access_token"]
                    st.session_state.user_id    = resp["user_id"]
                    st.session_state.user_name  = resp["full_name"]
                    st.session_state.user_email = resp["email"]
                    go_to("dashboard")
                else:
                    st.error(resp.get("detail", "Login failed."))

        ca, cb = st.columns(2)
        with ca:
            if st.button("← Home", use_container_width=True):
                go_to("landing")
        with cb:
            if st.button("Create Account", use_container_width=True):
                go_to("signup")


# ─── PAGE: Signup ─────────────────────────────────────────────────────────────

def page_signup():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem;">
            <div style="font-size:2.2rem;">💰</div>
            <div style="font-size:1.4rem;font-weight:800;">Create Account</div>
            <div style="color:#9fb2ca;font-size:0.85rem;">
                Start your financial journey
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("signup_form"):
            full_name = st.text_input("Full Name", placeholder="Raj Sharma")
            email     = st.text_input("Email",     placeholder="raj@email.com")
            password  = st.text_input("Password",  type="password",
                                      placeholder="Min 6 characters")
            confirm   = st.text_input("Confirm Password", type="password")
            submit    = st.form_submit_button(
                "Create Account →", use_container_width=True, type="primary"
            )

        if submit:
            if not all([full_name, email, password, confirm]):
                st.error("Please fill in all fields.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                with st.spinner("Creating your account..."):
                    resp = api_post("/auth/signup", {
                        "email": email, "full_name": full_name,
                        "password": password
                    })
                if "access_token" in resp:
                    st.session_state.token      = resp["access_token"]
                    st.session_state.user_id    = resp["user_id"]
                    st.session_state.user_name  = resp["full_name"]
                    st.session_state.user_email = resp["email"]
                    st.success("Account created! Complete your profile.")
                    go_to("profile")
                else:
                    st.error(resp.get("detail", "Signup failed."))

        if st.button("← Already have account? Login", use_container_width=True):
            go_to("login")


# ─── PAGE: Dashboard ──────────────────────────────────────────────────────────

def page_dashboard():
    render_navbar()
    load_and_cache_analysis()

    health  = st.session_state.cached_health  or {}
    invest  = st.session_state.cached_invest  or {}
    credit  = st.session_state.cached_credit  or {}
    summary = st.session_state.cached_summary or {}
    sim     = st.session_state.cached_sim     or {}

    health_score = health.get("overall_score", 0)
    health_grade = health.get("grade", "N/A")
    total_sip    = invest.get("total_monthly_investment", 0)
    corpus_10yr  = invest.get("projected_corpus_10yr", 0)
    top_card     = (
        credit.get("recommendations", [{}])[0].get("card_name", "—")
        if credit.get("recommendations") else "—"
    )

    if not health and not invest:
        st.markdown(f"""
        <div class="alert alert-info">
            👋 Welcome, <b>{st.session_state.user_name}</b>!
            Complete your profile and run your first analysis.
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("📊 Run Full Analysis Now",
                         use_container_width=True, type="primary"):
                with st.spinner("AI analysing your finances — ~30 seconds..."):
                    resp = api_post(
                        "/analysis", {"analysis_type": "full"}, auth=True
                    )
                if "results" in resp:
                    refresh_analysis()
                    st.success("Analysis complete!")
                    st.rerun()
                else:
                    st.error(resp.get("detail",
                             "Complete your profile first at the Profile page."))
        render_chat_overlay()
        return

    st.markdown(
        '<div class="section-header">📊 Financial Overview</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    score_color = (
        "#0ea5a4" if health_score>=70 else
        "#f59e0b" if health_score>=50 else "#ef4444"
    )
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{score_color};">
                {health_score:.0f}
            </div>
            <div class="metric-label">Health Score</div>
            <div class="metric-delta">Grade {health_grade}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{fmt_inr(total_sip)}</div>
            <div class="metric-label">Monthly SIP</div>
            <div class="metric-delta">recommended</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{fmt_inr(corpus_10yr)}</div>
            <div class="metric-label">10 Year Corpus</div>
            <div class="metric-delta">projected</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value"
                 style="font-size:0.9rem;padding-top:0.5rem;">
                {top_card[:22] if top_card else "—"}
            </div>
            <div class="metric-label">Best Credit Card</div>
            <div class="metric-delta">recommended</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    cl, cr = st.columns(2)
    with cl:
        alloc = invest.get("portfolio_allocation", {})
        if alloc:
            st.plotly_chart(
                pie_chart(
                    [k.capitalize() for k in alloc.keys()],
                    list(alloc.values()), "Portfolio Allocation"
                ), use_container_width=True
            )
    with cr:
        sim_c = sim.get("current_trajectory",   {})
        sim_o = sim.get("optimized_trajectory", {})
        if sim_c and sim_o:
            st.plotly_chart(
                line_chart(
                    ["5yr","10yr","20yr"],
                    [sim_c.get("corpus_5yr",  0),
                     sim_c.get("corpus_10yr", 0),
                     sim_c.get("corpus_20yr", 0)],
                    [sim_o.get("corpus_5yr",  0),
                     sim_o.get("corpus_10yr", 0),
                     sim_o.get("corpus_20yr", 0)],
                    "Current Path", "Optimized Path", "Wealth Projection"
                ), use_container_width=True
            )

    priorities = summary.get("top_priorities", [])
    if priorities:
        st.markdown(
            '<div class="section-header">🎯 Priority Actions</div>',
            unsafe_allow_html=True
        )
        for p in priorities[:3]:
            ic = "#0ea5a4" if p.get("impact")=="high" else "#f59e0b"
            st.markdown(f"""
            <div class="card card-green">
                <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;">
                    <div>
                        <span class="badge">Priority {p.get('priority','')}</span>
                        <div style="font-weight:600;font-size:0.9rem;
                                    margin-top:2px;">
                            {p.get('action','')}
                        </div>
                    </div>
                    <span style="color:{ic};font-size:0.78rem;font-weight:600;
                                 white-space:nowrap;margin-left:1rem;">
                        {p.get('timeline','')}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)

    quick_wins = summary.get("quick_wins", [])
    if quick_wins:
        st.markdown(
            '<div class="section-header">⚡ Quick Wins</div>',
            unsafe_allow_html=True
        )
        cols = st.columns(3)
        for i, win in enumerate(quick_wins[:3]):
            with cols[i]:
                st.markdown(
                    f'<div class="alert alert-success">✅ {win}</div>',
                    unsafe_allow_html=True
                )

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        if st.button("🔄 Refresh Analysis", use_container_width=True):
            with st.spinner("Running..."):
                api_post("/analysis", {"analysis_type": "full"}, auth=True)
            refresh_analysis()
            st.rerun()

    render_chat_overlay()


# ─── PAGE: Portfolio ──────────────────────────────────────────────────────────

def page_portfolio():
    render_navbar()
    st.markdown(
        '<div class="section-header">📊 Portfolio Planner</div>',
        unsafe_allow_html=True
    )

    load_and_cache_analysis()
    invest  = st.session_state.cached_invest or {}
    profile = st.session_state.profile_cache or api_get("/profile")
    st.session_state.profile_cache = profile

    with st.expander("⚙️ Adjust Preferences", expanded=not bool(invest)):
        with st.form("portfolio_form"):
            c1, c2 = st.columns(2)
            with c1:
                risk = st.selectbox(
                    "Risk Tolerance",
                    ["low","moderate","high","very_high"],
                    index=(
                        ["low","moderate","high","very_high"].index(
                            profile.get("risk_tolerance","moderate")
                        ) if "risk_tolerance" in profile else 1
                    )
                )
                horizon = st.selectbox(
                    "Investment Horizon",
                    ["short","medium","long"],
                    index=(
                        ["short","medium","long"].index(
                            profile.get("investment_horizon","long")
                        ) if "investment_horizon" in profile else 2
                    )
                )
            with c2:
                goals = st.multiselect(
                    "Financial Goals",
                    ["retirement","house","car","education",
                     "wedding","travel","business"],
                    default=profile.get("financial_goals",[])
                )

            if st.form_submit_button(
                "📊 Generate Plan", use_container_width=True, type="primary"
            ):
                with st.spinner("Building your investment plan..."):
                    resp = api_post(
                        "/analysis", {"analysis_type": "investment"}, auth=True
                    )
                if "results" in resp:
                    st.session_state.cached_invest = (
                        resp["results"].get("investment", {})
                    )
                    invest = st.session_state.cached_invest
                    st.success("Plan generated!")
                    st.rerun()
                else:
                    st.error(resp.get("detail", str(resp)))

    if invest:
        _render_investment_results(invest)
    else:
        st.markdown("""
        <div class="alert alert-info">
            📊 Click Generate Plan above or run a full analysis
            from the Dashboard.
        </div>""", unsafe_allow_html=True)

    render_chat_overlay()


def _render_investment_results(inv: dict):
    if not inv:
        return

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("Monthly SIP",    fmt_inr(inv.get("total_monthly_investment", 0))),
        ("5 Year Corpus",  fmt_inr(inv.get("projected_corpus_5yr",     0))),
        ("10 Year Corpus", fmt_inr(inv.get("projected_corpus_10yr",    0))),
        ("20 Year Corpus", fmt_inr(inv.get("projected_corpus_20yr",    0))),
    ]
    for col, (label, val) in zip([c1,c2,c3,c4], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    cl, cr = st.columns([1, 2])
    with cl:
        alloc = inv.get("portfolio_allocation", {})
        if alloc:
            st.plotly_chart(
                pie_chart(
                    [k.capitalize() for k in alloc.keys()],
                    list(alloc.values()), "Allocation"
                ), use_container_width=True
            )
    with cr:
        st.plotly_chart(
            bar_chart(
                ["5 Years","10 Years","20 Years"],
                [inv.get("projected_corpus_5yr",  0),
                 inv.get("projected_corpus_10yr", 0),
                 inv.get("projected_corpus_20yr", 0)],
                "Corpus Growth"
            ), use_container_width=True
        )

    ef = inv.get("emergency_fund_status", {})
    if ef.get("gap_amount", 0) > 0:
        st.markdown(f"""
        <div class="alert alert-warning">
            ⚠️ <b>Emergency Fund Gap:</b> {fmt_inr(ef.get('gap_amount',0))}
            — {ef.get('action','Build emergency fund first')}
        </div>""", unsafe_allow_html=True)
    elif ef:
        st.markdown(
            '<div class="alert alert-success">✅ Emergency fund fully funded</div>',
            unsafe_allow_html=True
        )

    sip_plan = inv.get("monthly_sip_plan", [])
    if sip_plan:
        st.markdown(
            '<div class="section-header">💰 Monthly SIP Breakdown</div>',
            unsafe_allow_html=True
        )
        for s in sip_plan:
            st.markdown(f"""
            <div class="sip-row">
                <div>
                    <div class="sip-name">{s.get('instrument','')}</div>
                    <div class="sip-cat">
                        {s.get('category','')}
                        {' · ' + s.get('expected_return','')
                         if s.get('expected_return') else ''}
                    </div>
                </div>
                <div class="sip-amt">
                    {fmt_inr(s.get('monthly_amount',0))}/mo
                </div>
            </div>""", unsafe_allow_html=True)

    tax = inv.get("tax_saving_plan", {})
    if tax and tax.get("total_tax_saved_annually", 0) > 0:
        st.markdown(
            '<div class="section-header">💸 Tax Saving</div>',
            unsafe_allow_html=True
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("80C",
                      fmt_inr(tax.get("section_80C",{}).get("amount",0)))
        with c2:
            st.metric("NPS 80CCD(1B)",
                      fmt_inr(tax.get("section_80CCD_1B",{}).get("amount",0)))
        with c3:
            st.metric("Total Saved/Year",
                      fmt_inr(tax.get("total_tax_saved_annually",0)),
                      delta="✅")

    if inv.get("key_advice"):
        st.markdown(f"""
        <div class="alert alert-info" style="margin-top:0.8rem;">
            💡 {inv.get('key_advice')}
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="color:#64748b;font-size:0.7rem;margin-top:0.8rem;">
        ⚠️ Investments are subject to market risk.
        Please read all scheme documents carefully.
    </div>""", unsafe_allow_html=True)


# ─── PAGE: Stocks ─────────────────────────────────────────────────────────────

def page_stocks():
    render_navbar()
    st.markdown(
        '<div class="section-header">📈 Stock Advisor</div>',
        unsafe_allow_html=True
    )

    profile = st.session_state.profile_cache or api_get("/profile")
    st.session_state.profile_cache = profile

    with st.expander("⚙️ Update Stock Inputs", expanded=False):
        with st.form("stocks_update_form"):
            c1, c2 = st.columns(2)
            with c1:
                risk = st.selectbox(
                    "Risk Tolerance",
                    ["low","moderate","high","very_high"],
                    index=(
                        ["low","moderate","high","very_high"].index(
                            profile.get("risk_tolerance","moderate")
                        ) if profile.get("risk_tolerance") in
                        ["low","moderate","high","very_high"] else 1
                    )
                )
                horizon = st.selectbox(
                    "Investment Horizon",
                    ["short","medium","long"],
                    index=(
                        ["short","medium","long"].index(
                            profile.get("investment_horizon","long")
                        ) if profile.get("investment_horizon") in
                        ["short","medium","long"] else 2
                    )
                )
                goals = st.multiselect(
                    "Financial Goals",
                    ["retirement","house","car","education",
                     "wedding","travel","business"],
                    default=profile.get("financial_goals",[])
                )
            with c2:
                monthly_income = st.number_input(
                    "Monthly Income (₹)", min_value=0,
                    value=int(profile.get("monthly_income",50000))
                )
                monthly_expenses = st.number_input(
                    "Monthly Expenses (₹)", min_value=0,
                    value=int(profile.get("monthly_expenses",30000))
                )
                existing_investments = st.number_input(
                    "Existing Investments (₹)", min_value=0,
                    value=int(profile.get("existing_investments",0))
                )

            if st.form_submit_button(
                "Save & Re-run Stock Analysis",
                use_container_width=True, type="primary"
            ):
                payload = {
                    "age":                  int(profile.get("age",25)),
                    "employment_type":      profile.get("employment_type","salaried"),
                    "monthly_income":       int(monthly_income),
                    "monthly_expenses":     int(monthly_expenses),
                    "existing_savings":     int(profile.get("existing_savings",0)),
                    "existing_investments": int(existing_investments),
                    "existing_debts":       int(profile.get("existing_debts",0)),
                    "risk_tolerance":       risk,
                    "investment_horizon":   horizon,
                    "financial_goals":      goals,
                    "credit_score":         int(profile.get("credit_score",700)),
                    "monthly_credit_spend": int(profile.get("monthly_credit_spend",0)),
                    "top_spend_categories": profile.get("top_spend_categories",[])
                }
                with st.spinner("Saving and refreshing stock picks..."):
                    save_resp = api_post("/profile", payload, auth=True)
                    run_resp  = api_post(
                        "/analysis",
                        {"analysis_type": "investment"}, auth=True
                    )
                if "id" in save_resp and "results" in run_resp:
                    st.session_state.profile_cache = None
                    st.session_state.cached_invest = (
                        run_resp["results"].get("investment",{})
                    )
                    st.success("Stock picks refreshed.")
                    st.rerun()
                else:
                    st.error(
                        save_resp.get("detail")
                        or run_resp.get("detail")
                        or "Could not refresh stock analysis."
                    )

    load_and_cache_analysis()
    invest = st.session_state.cached_invest or {}
    stocks = invest.get("stock_recommendations", [])

    if not stocks:
        st.markdown("""
        <div class="alert alert-info">
            📈 Stock picks are part of your investment analysis.
        </div>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("📊 Run Analysis", use_container_width=True, type="primary"):
                with st.spinner("Running..."):
                    resp = api_post(
                        "/analysis",
                        {"analysis_type": "investment"}, auth=True
                    )
                if "results" in resp:
                    st.session_state.cached_invest = (
                        resp["results"].get("investment",{})
                    )
                    st.rerun()
                else:
                    st.error(resp.get("detail", str(resp)))
        render_chat_overlay()
        return

    st.markdown(
        '<div class="section-header">📋 Your Stock Picks</div>',
        unsafe_allow_html=True
    )

    custom_alloc = [float(s.get("allocation_percent",10)) for s in stocks]
    with st.expander("🎚️ Adjust Allocation Preview", expanded=False):
        raw_vals = []
        for i, stock in enumerate(stocks):
            label = f"{stock.get('company','')} ({stock.get('symbol','')})"
            raw_vals.append(st.slider(
                label, 0, 100,
                value=int(custom_alloc[i]),
                key=f"stock_alloc_slider_{i}"
            ))
        total_raw = sum(raw_vals)
        if total_raw > 0:
            custom_alloc = [round((v/total_raw)*100,1) for v in raw_vals]
        else:
            st.warning("Allocation cannot be all zeros.")

    df = pd.DataFrame([{
        "Company":     s.get("company",""),
        "Symbol":      s.get("symbol",""),
        "Sector":      s.get("sector",""),
        "Allocation":  f"{custom_alloc[i]}%",
        "Style":       s.get("investment_style",""),
        "Hold Period": s.get("ideal_holding_period","")
    } for i, s in enumerate(stocks)])
    st.dataframe(df, use_container_width=True, hide_index=True)

    cl, cr = st.columns([1, 2])
    with cl:
        st.plotly_chart(
            pie_chart(
                [s.get("company","") for s in stocks],
                custom_alloc,
                "Stock Allocation"
            ), use_container_width=True
        )
    with cr:
        st.markdown(
            '<div class="section-header">📊 Stock Details</div>',
            unsafe_allow_html=True
        )
        for i, stock in enumerate(stocks):
            with st.expander(
                f"{stock.get('company','')} ({stock.get('symbol','')}) "
                f"— {stock.get('sector','')}",
                expanded=False
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    <div class="card card-green" style="padding:0.8rem;">
                        <div style="font-size:0.72rem;color:#64748b;">
                            Allocation
                        </div>
                        <div style="font-size:1.3rem;font-weight:800;
                                    color:#0ea5a4;">
                            {custom_alloc[i]}%
                        </div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"**Style:** {stock.get('investment_style','')}")
                    st.markdown(f"**Hold:** {stock.get('ideal_holding_period','')}")
                with c2:
                    why = stock.get("why_now","")
                    if why:
                        st.markdown(
                            f'<div class="alert alert-info">💡 {why}</div>',
                            unsafe_allow_html=True
                        )

    st.markdown("""
    <div style="color:#64748b;font-size:0.7rem;margin-top:1rem;">
        ⚠️ Stocks are subject to market risk.
        This is not SEBI registered investment advice.
    </div>""", unsafe_allow_html=True)

    render_chat_overlay()


# ─── PAGE: Credit Cards ───────────────────────────────────────────────────────

def page_credit():
    render_navbar()
    st.markdown(
        '<div class="section-header">💳 Credit Card Advisor</div>',
        unsafe_allow_html=True
    )

    load_and_cache_analysis()
    credit  = st.session_state.cached_credit or {}
    profile = st.session_state.profile_cache or api_get("/profile")
    st.session_state.profile_cache = profile

    with st.expander("⚙️ Update Spending Details", expanded=not bool(credit)):
        with st.form("credit_form"):
            c1, c2 = st.columns(2)
            with c1:
                monthly_income = st.number_input(
                    "Monthly Income (₹)", min_value=0,
                    value=int(profile.get("monthly_income",50000))
                )
                credit_spend = st.number_input(
                    "Monthly Credit Spend (₹)", min_value=0,
                    value=int(profile.get("monthly_credit_spend",10000))
                )
            with c2:
                credit_score = st.slider(
                    "Credit Score", 300, 900,
                    value=int(profile.get("credit_score",700))
                )
                categories = st.multiselect(
                    "Top Spend Categories",
                    ["online shopping","dining","travel","fuel","movies",
                     "grocery","upi","food delivery","amazon","flipkart",
                     "international travel"],
                    default=profile.get("top_spend_categories",[])
                )

            if st.form_submit_button(
                "💳 Get Recommendations",
                use_container_width=True, type="primary"
            ):
                with st.spinner("Finding best cards..."):
                    resp = api_post(
                        "/analysis", {"analysis_type": "credit"}, auth=True
                    )
                if "results" in resp:
                    st.session_state.cached_credit = (
                        resp["results"].get("credit",{})
                    )
                    credit = st.session_state.cached_credit
                    st.success("Recommendations ready!")
                    st.rerun()
                else:
                    st.error(resp.get("detail", str(resp)))

    if credit:
        _render_credit_results(credit)
    else:
        st.markdown("""
        <div class="alert alert-info">
            💳 Fill in your spending details above to get
            personalised credit card recommendations.
        </div>""", unsafe_allow_html=True)

    render_chat_overlay()


def _render_credit_results(credit: dict):
    if not credit:
        return
    recs = credit.get("recommendations", [])
    if not recs:
        return

    st.markdown(
        '<div class="section-header">💳 Your Card Recommendations</div>',
        unsafe_allow_html=True
    )

    top_recs = recs[:3]
    cols     = st.columns(len(top_recs))
    for i, rec in enumerate(top_recs):
        with cols[i]:
            render_credit_card_widget(rec, rec.get("rank", i+1))

    for rec in recs[3:]:
        render_credit_card_widget(rec, rec.get("rank", 4))

    if credit.get("strategy_note"):
        st.markdown(f"""
        <div class="alert alert-info" style="margin-top:1rem;">
            💡 <b>Strategy:</b> {credit.get('strategy_note')}
        </div>""", unsafe_allow_html=True)

    for p in credit.get("avoid_pitfalls", []):
        st.markdown(
            f'<div class="alert alert-warning">❌ {p}</div>',
            unsafe_allow_html=True
        )


# ─── PAGE: Health ─────────────────────────────────────────────────────────────

def page_health():
    render_navbar()
    st.markdown(
        '<div class="section-header">❤️ Financial Health</div>',
        unsafe_allow_html=True
    )

    load_and_cache_analysis()
    health  = st.session_state.cached_health or {}
    profile = st.session_state.profile_cache or api_get("/profile")
    st.session_state.profile_cache = profile

    with st.expander("⚙️ Update Financial Data", expanded=not bool(health)):
        with st.form("health_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                monthly_income   = st.number_input(
                    "Monthly Income (₹)",
                    value=int(profile.get("monthly_income",50000))
                )
                existing_savings = st.number_input(
                    "Existing Savings (₹)",
                    value=int(profile.get("existing_savings",0))
                )
            with c2:
                monthly_expenses = st.number_input(
                    "Monthly Expenses (₹)",
                    value=int(profile.get("monthly_expenses",30000))
                )
                existing_invest  = st.number_input(
                    "Existing Investments (₹)",
                    value=int(profile.get("existing_investments",0))
                )
            with c3:
                credit_score   = st.slider(
                    "Credit Score", 300, 900,
                    value=int(profile.get("credit_score",700))
                )
                existing_debts = st.number_input(
                    "Existing Debts (₹)",
                    value=int(profile.get("existing_debts",0))
                )

            if st.form_submit_button(
                "❤️ Calculate Score",
                use_container_width=True, type="primary"
            ):
                with st.spinner("Calculating health score..."):
                    resp = api_post(
                        "/analysis", {"analysis_type": "health"}, auth=True
                    )
                if "results" in resp:
                    st.session_state.cached_health = (
                        resp["results"].get("health",{})
                    )
                    health = st.session_state.cached_health
                    st.success("Health score calculated!")
                    st.rerun()
                else:
                    st.error(resp.get("detail", str(resp)))

    if health:
        _render_health_results(health)
    else:
        st.markdown("""
        <div class="alert alert-info">
            ❤️ Submit your financial data above to calculate
            your health score.
        </div>""", unsafe_allow_html=True)

    render_chat_overlay()


def _render_health_results(health: dict):
    if not health:
        return

    score = health.get("overall_score", 0)
    grade = health.get("grade", "N/A")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.plotly_chart(gauge_chart(score, "Health Score"),
                        use_container_width=True)
        grade_color = (
            "#0ea5a4" if score>=70 else
            "#f59e0b" if score>=50 else "#ef4444"
        )
        st.markdown(f"""
        <div style="text-align:center;margin-top:-0.5rem;">
            <div style="font-size:2.5rem;font-weight:800;
                        color:{grade_color};">{grade}</div>
            <div style="color:#9fb2ca;font-size:0.78rem;">Overall Grade</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<p style="font-weight:600;">Score Breakdown:</p>',
            unsafe_allow_html=True
        )
        component_labels = {
            "savings_rate":    "💰 Savings Rate",
            "emergency_fund":  "🛡️ Emergency Fund",
            "debt_ratio":      "💳 Debt Ratio",
            "investment_rate": "📈 Investment Rate",
            "credit_score":    "⭐ Credit Score"
        }
        for key, label in component_labels.items():
            comp     = health.get("components", {}).get(key, {})
            c_score  = comp.get("score",     0)
            c_max    = comp.get("max",       25)
            c_val    = comp.get("value",     "N/A")
            c_bench  = comp.get("benchmark", "")
            c_status = comp.get("status",    "")
            pct      = (c_score / c_max) if c_max > 0 else 0
            vc = "#0ea5a4" if c_status in ["good","excellent"] else "#f59e0b"

            st.markdown(f"""
            <div class="prog-row">
                <div class="prog-label">
                    <span>
                        {label}: <b style="color:{vc};">{c_val}</b>
                    </span>
                    <span style="color:#64748b;">
                        {c_score}/{c_max} · {c_bench}
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)
            st.progress(pct)

    budget = health.get("monthly_budget_suggestion", {})
    if budget:
        st.markdown(
            '<div class="section-header">💵 Recommended Budget</div>',
            unsafe_allow_html=True
        )
        c1, c2, c3 = st.columns(3)
        for col, (label, key) in zip(
            [c1, c2, c3],
            [("Needs (50%)", "needs"),
             ("Wants (20%)", "wants"),
             ("Savings (30%)", "savings_investments")]
        ):
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{fmt_inr(budget.get(key,0))}</div>
                    <div class="metric-label">{label}</div>
                </div>""", unsafe_allow_html=True)

    for s in health.get("strengths", []):
        st.markdown(
            f'<div class="alert alert-success">✅ {s}</div>',
            unsafe_allow_html=True
        )

    improvements = health.get("improvement_areas", [])
    if improvements:
        st.markdown(
            '<div class="section-header">🎯 Improvement Areas</div>',
            unsafe_allow_html=True
        )
        for imp in improvements:
            with st.expander(
                f"📌 {imp.get('area','')} — "
                f"{imp.get('current','')} → {imp.get('target','')}",
                expanded=False
            ):
                for step in imp.get("action_steps", []):
                    st.markdown(f"→ {step}")

    actions = health.get("priority_actions", [])
    if actions:
        st.markdown(
            '<div class="section-header">🚀 Priority Actions</div>',
            unsafe_allow_html=True
        )
        for i, action in enumerate(actions, 1):
            st.markdown(f"""
            <div class="card card-green">
                <span class="badge">{i}</span>
                <span style="font-size:0.88rem;"> {action}</span>
            </div>""", unsafe_allow_html=True)


# ─── PAGE: Reports ────────────────────────────────────────────────────────────

def page_reports():
    render_navbar()
    st.markdown(
        '<div class="section-header">📋 Reports</div>',
        unsafe_allow_html=True
    )

    load_and_cache_analysis()

    health  = st.session_state.cached_health  or {}
    invest  = st.session_state.cached_invest  or {}
    credit  = st.session_state.cached_credit  or {}
    summary = st.session_state.cached_summary or {}
    opt     = st.session_state.cached_opt     or {}

    if not health and not invest:
        st.markdown("""
        <div class="alert alert-info">
            📭 No reports yet. Run a full analysis first.
        </div>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("📊 Run Full Analysis",
                         use_container_width=True, type="primary"):
                with st.spinner("Running..."):
                    resp = api_post(
                        "/analysis", {"analysis_type":"full"}, auth=True
                    )
                if "results" in resp:
                    refresh_analysis()
                    st.rerun()
                else:
                    st.error(resp.get("detail", str(resp)))
        render_chat_overlay()
        return

    st.markdown(f"""
    <div class="card card-blue">
        <div style="font-weight:700;font-size:1rem;">
            📊 Full Financial Report — {st.session_state.user_name}
        </div>
        <div style="color:#9fb2ca;font-size:0.8rem;margin-top:3px;">
            Health: {health.get('overall_score',0):.0f}/100
            ({health.get('grade','N/A')}) &nbsp;·&nbsp;
            SIP: {fmt_inr(invest.get('total_monthly_investment',0))}/mo
            &nbsp;·&nbsp;
            10yr: {fmt_inr(invest.get('projected_corpus_10yr',0))}
            &nbsp;·&nbsp; {st.session_state.user_email}
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Summary","❤️ Health","💰 Investment",
        "💳 Credit Cards","🔧 Optimization"
    ])

    with tab1:
        exec_sum = summary.get("executive_summary","")
        if exec_sum:
            st.markdown(
                f'<div class="alert alert-info">📝 {exec_sum}</div>',
                unsafe_allow_html=True
            )
        key_nums = summary.get("key_numbers",{})
        if key_nums:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Monthly Surplus",
                          fmt_inr(key_nums.get("monthly_surplus",0)))
                st.metric("Recommended SIP",
                          fmt_inr(key_nums.get("recommended_sip",0)))
            with c2:
                st.metric("Emergency Gap",
                          fmt_inr(key_nums.get("emergency_fund_gap",0)))
                st.metric("Annual Tax Saving",
                          fmt_inr(key_nums.get("annual_tax_saving",0)))
            with c3:
                st.metric("Best Card", key_nums.get("best_credit_card","—"))
                st.metric("10yr Corpus",
                          fmt_inr(key_nums.get("projected_corpus_10yr",0)))
        msg = summary.get("personalized_message","")
        if msg:
            st.markdown(
                f'<div class="alert alert-success">💬 {msg}</div>',
                unsafe_allow_html=True
            )

    with tab2:
        _render_health_results(health)

    with tab3:
        _render_investment_results(invest)

    with tab4:
        _render_credit_results(credit)

    with tab5:
        opps = opt.get("optimization_opportunities", [])
        if opps:
            total = sum(o.get("annual_benefit_rupees",0) for o in opps)
            st.metric("Total Annual Benefit", fmt_inr(total),
                      delta="potential saving ✅")
            for opp in opps:
                with st.expander(
                    f"💡 {opp.get('area','')} — "
                    f"{fmt_inr(opp.get('annual_benefit_rupees',0))}/year",
                    expanded=False
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(
                            f"**Current:** {opp.get('current_state','')}"
                        )
                    with c2:
                        st.markdown(
                            f"**Optimized:** {opp.get('optimized_state','')}"
                        )
                    for step in opp.get("steps",[]):
                        st.markdown(f"→ {step}")
        else:
            st.info("Run full analysis to see optimization opportunities.")

    render_chat_overlay()


# ─── PAGE: Profile ────────────────────────────────────────────────────────────

def page_profile():
    render_navbar()
    st.markdown(
        f'<div class="section-header">👤 {st.session_state.user_name}\'s Profile</div>',
        unsafe_allow_html=True
    )

    profile = st.session_state.profile_cache or api_get("/profile")
    st.session_state.profile_cache = profile

    tab1, tab2 = st.tabs(["📋 Edit Profile","📊 Quick Stats"])

    with tab1:
        with st.form("profile_form"):
            st.markdown("#### 👤 Personal")
            c1, c2 = st.columns(2)
            with c1:
                age = st.number_input(
                    "Age", 18, 80, value=int(profile.get("age",25))
                )
            with c2:
                employment = st.selectbox(
                    "Employment Type",
                    ["salaried","self_employed","business"],
                    index=(
                        ["salaried","self_employed","business"].index(
                            profile.get("employment_type","salaried")
                        ) if "employment_type" in profile else 0
                    )
                )

            st.markdown("#### 💰 Income & Expenses")
            c1, c2 = st.columns(2)
            with c1:
                monthly_income   = st.number_input(
                    "Monthly Income (₹)", min_value=0,
                    value=int(profile.get("monthly_income",50000))
                )
                existing_savings = st.number_input(
                    "Existing Savings (₹)", min_value=0,
                    value=int(profile.get("existing_savings",0))
                )
                existing_debts   = st.number_input(
                    "Existing Debts (₹)", min_value=0,
                    value=int(profile.get("existing_debts",0))
                )
            with c2:
                monthly_expenses = st.number_input(
                    "Monthly Expenses (₹)", min_value=0,
                    value=int(profile.get("monthly_expenses",30000))
                )
                existing_invest  = st.number_input(
                    "Existing Investments (₹)", min_value=0,
                    value=int(profile.get("existing_investments",0))
                )

            st.markdown("#### 📊 Investment Preferences")
            c1, c2 = st.columns(2)
            with c1:
                risk = st.selectbox(
                    "Risk Tolerance",
                    ["low","moderate","high","very_high"],
                    index=(
                        ["low","moderate","high","very_high"].index(
                            profile.get("risk_tolerance","moderate")
                        ) if "risk_tolerance" in profile else 1
                    )
                )
                goals = st.multiselect(
                    "Financial Goals",
                    ["retirement","house","car","education",
                     "wedding","travel","business"],
                    default=profile.get("financial_goals",[])
                )
            with c2:
                horizon = st.selectbox(
                    "Investment Horizon",
                    ["short","medium","long"],
                    index=(
                        ["short","medium","long"].index(
                            profile.get("investment_horizon","long")
                        ) if "investment_horizon" in profile else 2
                    )
                )

            st.markdown("#### 💳 Credit Card")
            c1, c2 = st.columns(2)
            with c1:
                credit_score = st.slider(
                    "Credit Score", 300, 900,
                    value=int(profile.get("credit_score",700))
                )
            with c2:
                monthly_credit = st.number_input(
                    "Monthly Credit Spend (₹)", min_value=0,
                    value=int(profile.get("monthly_credit_spend",0))
                )

            categories = st.multiselect(
                "Top Spend Categories",
                ["online shopping","dining","travel","fuel","movies",
                 "grocery","upi","food delivery","amazon","flipkart",
                 "international travel"],
                default=profile.get("top_spend_categories",[])
            )

            submit = st.form_submit_button(
                "💾 Save Profile", use_container_width=True, type="primary"
            )

        if submit:
            payload = {
                "age":                  age,
                "employment_type":      employment,
                "monthly_income":       monthly_income,
                "monthly_expenses":     monthly_expenses,
                "existing_savings":     existing_savings,
                "existing_investments": existing_invest,
                "existing_debts":       existing_debts,
                "risk_tolerance":       risk,
                "investment_horizon":   horizon,
                "financial_goals":      goals,
                "credit_score":         credit_score,
                "monthly_credit_spend": monthly_credit,
                "top_spend_categories": categories
            }
            with st.spinner("Saving..."):
                resp = api_post("/profile", payload, auth=True)
            if "id" in resp:
                st.session_state.profile_cache = None
                st.session_state.analysis_ran  = False
                st.success(
                    "✅ Profile saved! "
                    "Go to Dashboard → Refresh Analysis to update."
                )
            else:
                st.error(resp.get("detail", f"Save failed: {resp}"))

    with tab2:
        state = api_get("/analysis/state")
        if state and state.get("health_score", 0) > 0:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Health Score",
                          f"{state.get('health_score',0):.0f}/100")
            with c2:
                st.metric("Portfolio Value",
                          fmt_inr(state.get("portfolio_value",0)))
            with c3:
                st.metric("Savings Rate",
                          f"{state.get('monthly_savings_rate',0):.1f}%")
            if state.get("last_updated"):
                st.caption(f"Last analysis: {state['last_updated']}")
        else:
            st.info("Run an analysis to see your financial stats.")

    render_chat_overlay()


# ─── Router ───────────────────────────────────────────────────────────────────

def main():
    if not is_logged_in():
        if st.session_state.page not in ["landing","login","signup"]:
            st.session_state.page = "landing"

    page = st.session_state.page

    if page == "landing":
        page_landing()
        return
    if page == "login":
        page_login()
        return
    if page == "signup":
        page_signup()
        return

    if not is_logged_in():
        page_login()
        return

    render_sidebar()

    page_map = {
        "dashboard": page_dashboard,
        "portfolio":  page_portfolio,
        "stocks":     page_stocks,
        "credit":     page_credit,
        "health":     page_health,
        "reports":    page_reports,
        "profile":    page_profile,
    }

    page_map.get(page, page_dashboard)()


if __name__ == "__main__":
    main()