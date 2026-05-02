import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import calendar

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RUN CREW",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Sora:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; background-color: #060c18; color: #c8d8f0; }
.stApp { background: radial-gradient(ellipse at 20% 0%, #0e1f14 0%, #060c18 45%, #070c1a 100%); }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1100px; }
.run-title {
    font-family: 'Bebas Neue', sans-serif; font-size: 3.2rem; letter-spacing: 6px;
    background: linear-gradient(90deg, #00FF87, #00d4ff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1;
}
.run-subtitle { color: #2d4a3a; font-size: 0.75rem; letter-spacing: 3px; margin-top: 2px; margin-bottom: 1.5rem; }
.section-label {
    font-family: 'Bebas Neue', sans-serif; font-size: 1rem;
    letter-spacing: 3px; color: #2d4a3a; margin-bottom: 10px; margin-top: 10px;
}
.stat-box { background: #0c1425; border: 1px solid #1a2540; border-radius: 12px; padding: 14px 16px; }
.stat-label { font-size: 0.65rem; letter-spacing: 1.5px; color: #3d5270; text-transform: uppercase; margin-bottom: 4px; }
.stat-value { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; letter-spacing: 1px; }
.stDataFrame { border-radius: 12px; overflow: hidden; }
.stButton > button {
    background: #00FF8720; border: 1px solid #00FF8755; color: #00FF87;
    border-radius: 10px; font-family: 'Sora', sans-serif; font-weight: 600;
    font-size: 0.85rem; padding: 0.4rem 1.2rem;
}
.stButton > button:hover { background: #00FF8733; border-color: #00FF87; }
div[data-testid="stExpander"] { background: #080e1d; border: 1px solid #141e33 !important; border-radius: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
DEFAULT_COLORS = [
    "#00FF87", "#FF6B6B", "#38BDF8", "#FFD93D",
    "#C084FC", "#FB923C", "#34D399", "#F472B6",
    "#60A5FA", "#FBBF24",
]
FIXED_COLORS = {
    "병희": "#00FF87", "지현": "#FF6B6B", "민준": "#38BDF8",
    "서연": "#FFD93D", "태양": "#C084FC", "현우": "#FB923C",
}

def get_rank_icon(i: int, total: int) -> str:
    if i == 0: return "🥇"
    if i == 1: return "🥈"
    if i == 2: return "🥉"
    if i == total - 1: return "☕"
    return f"{i+1}위"

def get_color(name: str, idx: int) -> str:
    return FIXED_COLORS.get(name, DEFAULT_COLORS[idx % len(DEFAULT_COLORS)])

# ─── Load secrets ─────────────────────────────────────────────────────────────
def load_members() -> dict:
    try:
        return {name: token for name, token in st.secrets["members"].items()}
    except Exception:
        return {"병희": "f82e663c3debe6d882d74aee8a22228a"}

# ─── Runalyze API ─────────────────────────────────────────────────────────────
def fetch_activities(token: str, year: int, month: int) -> list:
    last_day = calendar.monthrange(year, month)[1]
    date_params = {
        "after":  f"{year}-{month:02d}-01",
        "before": f"{year}-{month:02d}-{last_day:02d}",
        "limit":  200,
    }

    # 방법 1: token을 쿼리 파라미터로
    endpoints = [
        "https://runalyze.com/api/v1/activities",
        "https://runalyze.com/api/v1/training",
    ]
    for ep in endpoints:
        try:
            r = requests.get(ep, params={"token": token, **date_params}, timeout=15)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            data = r.json()
            raw = data if isinstance(data, list) else (
                data.get("data") or data.get("activities") or
                data.get("trainings") or []
            )
            return raw or []
        except Exception:
            continue

    # 방법 2: Authorization 헤더로
    try:
        r = requests.get(
            "https://runalyze.com/api/v1/activities",
            headers={"Authorization": f"Token {token}"},
            params=date_params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        raw = data if isinstance(data, list) else (data.get("data") or data.get("activities") or [])
        return raw or []
    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ Runalyze API 연결 실패: {e}")
        return []

def parse_activities(raw: list) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    rows = []
    for a in raw:
        cad = a.get("avgCadence") or 0
        rows.append({
            "date":      a.get("date", ""),
            "dist_km":   round((a.get("distance") or 0) / 1000, 2),
            "duration":  a.get("duration") or 0,
            "pace_s":    a.get("pace") or 0,
            "avg_hr":    a.get("avgHeartRate") or 0,
            "max_hr":    a.get("maxHeartRate") or 0,
            "cadence":   round(cad * 2) if cad > 0 else 0,
            "elevation": a.get("elevation") or 0,
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date", ascending=False).reset_index(drop=True)
    return df

def fmt_pace(s):
    if not s or s <= 0: return "—"
    return f"{int(s//60)}'{int(s%60):02d}\""

def fmt_dur(s):
    if not s: return "—"
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def render_card(icon, name, km, runs, color, is_live, is_first):
    border = f"2px solid {color}" if is_first else "1px solid #1a2540"
    bg     = "linear-gradient(145deg,#0c1f15,#0d1e2a)" if is_first else "#0a101f"
    live   = "🔗 LIVE" if is_live else "미연동"
    st.markdown(
        f'<div style="background:{bg};border:{border};border-radius:16px;padding:18px 20px;margin-bottom:8px;">'
        f'<div style="display:flex;justify-content:space-between;">'
        f'<span style="font-size:1.3rem;">{icon}</span>'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{color};'
        f'box-shadow:0 0 8px {color};display:inline-block;margin-top:4px;"></span>'
        f'</div>'
        f'<div style="font-weight:700;font-size:1.3rem;color:#e8f0ff;margin-top:8px;">{name}</div>'
        f'<div style="font-size:1.8rem;font-weight:800;color:{color};margin-top:2px;">'
        f'{km:.1f}<span style="font-size:0.75rem;color:#3d5270;margin-left:4px;">km</span></div>'
        f'<div style="font-size:0.62rem;letter-spacing:1px;color:#2d4a3a;margin-top:3px;">'
        f'{runs}회 활동 · {live}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    members = load_members()
    member_names = list(members.keys())
    now = datetime.now()

    # Header
    col_title, col_ctrl = st.columns([2, 1])
    with col_title:
        st.markdown('<div class="run-title">RUN CREW</div>', unsafe_allow_html=True)
        st.markdown('<div class="run-subtitle">꼴등이 커피 쏜다 ☕</div>', unsafe_allow_html=True)
    with col_ctrl:
        st.markdown("<br>", unsafe_allow_html=True)
        opts = []
        for i in range(13):
            mo, yr = now.month - i, now.year
            while mo <= 0: mo += 12; yr -= 1
            opts.append((yr, mo))
        sel_year, sel_month = st.selectbox(
            "월", opts, format_func=lambda x: f"{x[0]}년 {x[1]}월",
            label_visibility="collapsed"
        )

    # Fetch
    if "cache" not in st.session_state:
        st.session_state.cache = {}
    cache_key = f"{sel_year}-{sel_month}"

    if st.button("↻ 새로고침") or cache_key not in st.session_state.cache:
        with st.spinner("데이터 불러오는 중..."):
            result = {}
            for name, token in members.items():
                result[name] = parse_activities(fetch_activities(token, sel_year, sel_month))
            st.session_state.cache[cache_key] = result

    data = st.session_state.cache.get(cache_key, {})

    # Totals
    totals = sorted([
        {"name": n, "km": round(data.get(n, pd.DataFrame()).get("dist_km", pd.Series()).sum(), 1) if not data.get(n, pd.DataFrame()).empty else 0.0,
         "runs": len(data.get(n, pd.DataFrame())), "idx": i}
        for i, n in enumerate(member_names)
    ], key=lambda x: x["km"], reverse=True)
    N = len(totals)

    # Ranking cards
    st.markdown('<div class="section-label">이번달 순위</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, t in enumerate(totals):
        with cols[i % 3]:
            render_card(get_rank_icon(i, N), t["name"], t["km"], t["runs"],
                        get_color(t["name"], t["idx"]), t["name"] in members, i == 0)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts
    st.markdown('<div class="section-label">누적 거리 현황</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📊 멤버 비교 막대", "📈 일별 추이"])

    with tab1:
        fig = go.Figure(go.Bar(
            x=[t["name"] for t in totals],
            y=[t["km"] for t in totals],
            marker=dict(color=[get_color(t["name"], t["idx"]) for t in totals], line=dict(width=0)),
            text=[f"{t['km']:.1f}" for t in totals],
            textposition="outside", textfont=dict(color="#c8d8f0", size=13),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c8d8f0"),
            xaxis=dict(showgrid=False, tickfont=dict(size=14)),
            yaxis=dict(showgrid=True, gridcolor="#141e33", title="km"),
            margin=dict(t=30, b=10, l=0, r=0), height=300, bargap=0.35,
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        last_day = calendar.monthrange(sel_year, sel_month)[1]
        today_d  = now.day if (sel_year == now.year and sel_month == now.month) else last_day
        has_data = False
        for idx, name in enumerate(member_names):
            df = data.get(name, pd.DataFrame())
            if df.empty: continue
            has_data = True
            color = get_color(name, idx)
            daily = {}
            for _, row in df.iterrows():
                if pd.notna(row["date"]):
                    daily[row["date"].day] = daily.get(row["date"].day, 0) + row["dist_km"]
            days = list(range(1, today_d + 1))
            r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
            fig2.add_trace(go.Scatter(
                x=[f"{d}일" for d in days],
                y=[round(daily.get(d, 0), 2) for d in days],
                mode="lines+markers", name=name,
                line=dict(color=color, width=2.5), marker=dict(size=5, color=color),
                fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.07)",
            ))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c8d8f0"),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor="#141e33", title="km"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=10, b=10, l=0, r=0), height=300,
        )
        if has_data:
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("연동된 데이터가 없습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Detail expanders
    st.markdown('<div class="section-label">멤버 상세 기록</div>', unsafe_allow_html=True)
    for i, t in enumerate(totals):
        name  = t["name"]
        color = get_color(name, t["idx"])
        df    = data.get(name, pd.DataFrame())
        icon  = get_rank_icon(i, N)

        avg_hr   = df[df["avg_hr"]  > 0]["avg_hr"].mean()  if not df.empty else 0
        avg_cad  = df[df["cadence"] > 0]["cadence"].mean() if not df.empty else 0
        avg_pace = df[df["pace_s"]  > 0]["pace_s"].mean()  if not df.empty else 0

        with st.expander(f"{icon}  {name}  —  {t['km']:.1f} km  ({t['runs']}회)", expanded=(i == 0)):
            c1, c2, c3, c4, c5 = st.columns(5)
            for col, lbl, val, clr in [
                (c1, "총 거리",       f"{t['km']:.1f} km",                      color),
                (c2, "활동 횟수",     f"{t['runs']} 회",                         color),
                (c3, "평균 심박",     f"{avg_hr:.0f} bpm" if avg_hr else "—",    "#FF6B6B"),
                (c4, "평균 케이던스", f"{avg_cad:.0f} spm" if avg_cad else "—",  "#38BDF8"),
                (c5, "평균 페이스",   fmt_pace(avg_pace) if avg_pace else "—",   "#FFD93D"),
            ]:
                with col:
                    st.markdown(
                        f'<div class="stat-box"><div class="stat-label">{lbl}</div>'
                        f'<div class="stat-value" style="color:{clr};">{val}</div></div>',
                        unsafe_allow_html=True
                    )

            if not df.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                last_d = calendar.monthrange(sel_year, sel_month)[1]
                today_d2 = now.day if (sel_year == now.year and sel_month == now.month) else last_d
                daily_map = {}
                for _, row in df.iterrows():
                    if pd.notna(row["date"]):
                        daily_map[row["date"].day] = daily_map.get(row["date"].day, 0) + row["dist_km"]
                days2 = list(range(1, today_d2 + 1))
                cum, s = [], 0
                for d in days2:
                    s += daily_map.get(d, 0); cum.append(round(s, 2))
                r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
                fig3 = go.Figure(go.Scatter(
                    x=[f"{d}일" for d in days2], y=cum,
                    mode="lines+markers", line=dict(color=color, width=2.5),
                    marker=dict(size=4, color=color), fill="tozeroy",
                    fillcolor=f"rgba({r},{g},{b},0.12)",
                ))
                fig3.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#c8d8f0"),
                    xaxis=dict(showgrid=False, tickfont=dict(size=10)),
                    yaxis=dict(showgrid=True, gridcolor="#141e33", title="km"),
                    margin=dict(t=10, b=10, l=0, r=0), height=220, showlegend=False,
                )
                st.plotly_chart(fig3, use_container_width=True)

                disp = df.copy()
                disp["날짜"]     = disp["date"].dt.strftime("%Y-%m-%d")
                disp["거리(km)"] = disp["dist_km"]
                disp["시간"]     = disp["duration"].apply(fmt_dur)
                disp["페이스"]   = disp["pace_s"].apply(fmt_pace)
                disp["평균심박"] = disp["avg_hr"].apply(lambda x: f"{x} bpm" if x > 0 else "—")
                disp["최대심박"] = disp["max_hr"].apply(lambda x: f"{x} bpm" if x > 0 else "—")
                disp["케이던스"] = disp["cadence"].apply(lambda x: f"{x} spm" if x > 0 else "—")
                disp["고도"]     = disp["elevation"].apply(lambda x: f"+{x}m" if x > 0 else "—")
                st.dataframe(
                    disp[["날짜","거리(km)","시간","페이스","평균심박","최대심박","케이던스","고도"]],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.info("이 달 기록이 없습니다.")

    st.markdown(
        f'<div style="text-align:center;color:#141e33;font-size:0.65rem;letter-spacing:2px;margin-top:3rem;">'
        f'POWERED BY RUNALYZE · {sel_year}년 {sel_month}월 · RUN CREW</div>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
