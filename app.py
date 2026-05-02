import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
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

html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
    background-color: #060c18;
    color: #c8d8f0;
}
.stApp {
    background: radial-gradient(ellipse at 20% 0%, #0e1f14 0%, #060c18 45%, #070c1a 100%);
}

/* Hide streamlit defaults */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1100px; }

/* Title */
.run-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3.2rem;
    letter-spacing: 6px;
    background: linear-gradient(90deg, #00FF87, #00d4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
    margin-bottom: 0;
}
.run-subtitle {
    color: #2d4a3a;
    font-size: 0.75rem;
    letter-spacing: 3px;
    margin-top: 2px;
    margin-bottom: 1.5rem;
}

/* Rank cards */
.rank-card {
    background: #0a101f;
    border: 1px solid #141e33;
    border-radius: 16px;
    padding: 18px 20px;
    text-align: left;
    transition: transform .2s;
}
.rank-card.first {
    background: linear-gradient(145deg, #0c1f15, #0d1e2a);
    border-color: #00FF8755;
}
.rank-card:hover { transform: translateY(-3px); }
.rank-icon   { font-size: 1.3rem; }
.rank-name   { font-family: 'Bebas Neue', sans-serif; font-size: 1.5rem; letter-spacing: 2px; color: #e8f0ff; margin-top: 6px; }
.rank-km     { font-family: 'Bebas Neue', sans-serif; font-size: 2rem; letter-spacing: 1px; }
.rank-sub    { font-size: 0.65rem; letter-spacing: 1.5px; color: #2d4a3a; margin-top: 2px; }
.dot-live    { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-left: 6px; vertical-align: middle; }

/* Member list row */
.member-row {
    background: #080e1d;
    border: 1px solid #141e33;
    border-radius: 14px;
    padding: 14px 20px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Section label */
.section-label {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem;
    letter-spacing: 3px;
    color: #2d4a3a;
    margin-bottom: 10px;
    margin-top: 10px;
}

/* Stat box */
.stat-box {
    background: #0c1425;
    border: 1px solid #1a2540;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: left;
}
.stat-label { font-size: 0.65rem; letter-spacing: 1.5px; color: #3d5270; text-transform: uppercase; margin-bottom: 4px; }
.stat-value { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; letter-spacing: 1px; }

/* Detail table */
.detail-table th {
    color: #3d5270 !important;
    font-size: 0.75rem;
    letter-spacing: 1px;
    font-weight: 600;
}
.stDataFrame { border-radius: 12px; overflow: hidden; }

/* Selectbox / buttons */
div[data-testid="stSelectbox"] > div { border-radius: 10px; background: #0c1425; border-color: #1a2540; }
.stButton > button {
    background: #00FF8720;
    border: 1px solid #00FF8755;
    color: #00FF87;
    border-radius: 10px;
    font-family: 'Sora', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.4rem 1.2rem;
    transition: all .2s;
}
.stButton > button:hover { background: #00FF8733; border-color: #00FF87; }

div[data-testid="stExpander"] {
    background: #080e1d;
    border: 1px solid #141e33 !important;
    border-radius: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
MEMBER_COLORS = {
    "김병희": "#00FF87",
    "이재훈": "#FF6B6B",
    "이효민": "#38BDF8",
    "이종현": "#FFD93D",
    "조윤래": "#C084FC",
    "임정우": "#FB923C",
}
RANK_ICONS = ["🥇", "🥈", "🥉", "4위", "5위", "☕"]

# ─── Load secrets ─────────────────────────────────────────────────────────────
def load_members():
    """Load member tokens from st.secrets"""
    try:
        members_cfg = st.secrets["members"]
        return {name: token for name, token in members_cfg.items()}
    except Exception:
        # Fallback for local dev without secrets
        return {"병희": "f82e663c3debe6d882d74aee8a22228a"}

# ─── Runalyze API ─────────────────────────────────────────────────────────────
def fetch_activities(token: str, year: int, month: int) -> list:
    last_day = calendar.monthrange(year, month)[1]
    # sport 파라미터 제거 — 전체 가져온 뒤 러닝만 필터링
    params = {
        "token":  token,
        "after":  f"{year}-{month:02d}-01",
        "before": f"{year}-{month:02d}-{last_day:02d}",
        "limit":  200,
    }
    try:
        r = requests.get("https://runalyze.com/api/v1/activities", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        raw = data if isinstance(data, list) else (data.get("data") or data.get("activities") or [])
        # sport 필드가 있으면 러닝(1)만, 없으면 전체 반환
        running = [a for a in raw if a.get("sport") in (1, "1", None, "running", "")]
        return running if running else raw
    except requests.exceptions.RequestException as e:
        st.warning(f"API 오류: {e}")
        return []

def parse_activities(raw: list) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    rows = []
    for a in raw:
        dist_km = (a.get("distance") or 0) / 1000
        dur_s   = a.get("duration") or 0
        pace_s  = a.get("pace") or 0
        cad     = a.get("avgCadence") or 0
        rows.append({
            "date":       a.get("date", ""),
            "dist_km":    round(dist_km, 2),
            "duration":   dur_s,
            "pace_s":     pace_s,
            "avg_hr":     a.get("avgHeartRate") or 0,
            "max_hr":     a.get("maxHeartRate") or 0,
            "cadence":    round(cad * 2) if cad > 0 else 0,
            "elevation":  a.get("elevation") or 0,
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    return df

def fmt_pace(s):
    if not s or s <= 0: return "—"
    return f"{int(s//60)}'{int(s%60):02d}\""

def fmt_dur(s):
    if not s: return "—"
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

# ─── App ──────────────────────────────────────────────────────────────────────
def main():
    members = load_members()
    now = datetime.now()

    # ── Header ──
    col_title, col_ctrl = st.columns([2, 1])
    with col_title:
        st.markdown('<div class="run-title">RUN CREW</div>', unsafe_allow_html=True)
        st.markdown('<div class="run-subtitle">꼴등이 커피 쏜다 ☕</div>', unsafe_allow_html=True)

    with col_ctrl:
        st.markdown("<br>", unsafe_allow_html=True)
        month_options = []
        for i in range(13):
            d = date(now.year, now.month, 1)
            mo = now.month - i
            yr = now.year
            while mo <= 0:
                mo += 12; yr -= 1
            month_options.append((yr, mo, f"{yr}년 {mo}월"))

        selected = st.selectbox(
            "월 선택",
            options=[(y, m) for y, m, _ in month_options],
            format_func=lambda x: f"{x[0]}년 {x[1]}월",
            label_visibility="collapsed",
        )
        sel_year, sel_month = selected

    # ── Fetch all members ──
    if "data_cache" not in st.session_state:
        st.session_state.data_cache = {}

    cache_key = f"{sel_year}-{sel_month}"
    refresh = st.button("↻ 새로고침", key="refresh_btn")

    if cache_key not in st.session_state.data_cache or refresh:
        with st.spinner("러널라이즈에서 데이터 불러오는 중..."):
            result = {}
            for name, token in members.items():
                raw  = fetch_activities(token, sel_year, sel_month)
                result[name] = parse_activities(raw)
            st.session_state.data_cache[cache_key] = result

    member_data = st.session_state.data_cache[cache_key]

    # ── Build totals ──
    totals = []
    for name in members:
        df = member_data.get(name, pd.DataFrame())
        km   = df["dist_km"].sum() if not df.empty else 0
        runs = len(df)
        totals.append({"name": name, "km": round(km, 1), "runs": runs})

    # Add placeholder for members not yet in secrets
    for name in MEMBER_COLORS:
        if name not in members:
            totals.append({"name": name, "km": 0, "runs": 0, "placeholder": True})

    totals.sort(key=lambda x: x["km"], reverse=True)

    # ── Ranking cards ──
    st.markdown('<div class="section-label">이번달 순위</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, t in enumerate(totals):
        color    = MEMBER_COLORS.get(t["name"], "#888")
        live_txt = "🔗 RUNALYZE LIVE" if t["name"] in members else "미연동"
        border   = f"2px solid {color}" if i == 0 else "1px solid #1a2540"
        bg       = "linear-gradient(145deg,#0c1f15,#0d1e2a)" if i == 0 else "#0a101f"
        with cols[i % 3]:
            st.markdown(
                f'<div style="background:{bg};border:{border};border-radius:16px;padding:18px 20px;margin-bottom:8px">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<span style="font-size:1.3rem">{RANK_ICONS[i]}</span>'
                f'<span style="width:8px;height:8px;border-radius:50%;background:{color};box-shadow:0 0 8px {color};display:inline-block;margin-top:4px"></span>'
                f'</div>'
                f'<div style="font-family:Bebas Neue,sans-serif;font-size:1.5rem;letter-spacing:2px;color:#e8f0ff;margin-top:8px">{t["name"]}</div>'
                f'<div style="font-family:Bebas Neue,sans-serif;font-size:2rem;letter-spacing:1px;color:{color}">{t["km"]:.1f}'
                f'<span style="font-size:0.75rem;color:#3d5270;margin-left:4px">km</span></div>'
                f'<div style="font-size:0.62rem;letter-spacing:1.5px;color:#2d4a3a;margin-top:3px">{t["runs"]}회 활동 · {live_txt}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ──
    st.markdown('<div class="section-label">누적 거리 현황</div>', unsafe_allow_html=True)
    chart_tab1, chart_tab2 = st.tabs(["📊 멤버 비교 막대", "📈 일별 추이 (내 데이터)"])

    with chart_tab1:
        bar_df = pd.DataFrame(totals)
        bar_df = bar_df.sort_values("km", ascending=False)
        colors = [MEMBER_COLORS.get(n, "#888") for n in bar_df["name"]]

        fig = go.Figure(go.Bar(
            x=bar_df["name"], y=bar_df["km"],
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:.1f}" for v in bar_df["km"]],
            textposition="outside",
            textfont=dict(color="#c8d8f0", size=13),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sora", color="#c8d8f0"),
            xaxis=dict(showgrid=False, tickfont=dict(size=14)),
            yaxis=dict(showgrid=True, gridcolor="#141e33", title="km", tickfont=dict(size=11)),
            margin=dict(t=30, b=10, l=0, r=0),
            height=300,
            bargap=0.35,
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart_tab2:
        # Show line chart for members with data
        fig2 = go.Figure()
        last_day_of_month = calendar.monthrange(sel_year, sel_month)[1]
        today_day = now.day if (sel_year == now.year and sel_month == now.month) else last_day_of_month

        for name, df in member_data.items():
            if df.empty:
                continue
            color = MEMBER_COLORS.get(name, "#888")
            daily = {}
            for _, row in df.iterrows():
                if pd.notna(row["date"]):
                    d = row["date"].day
                    daily[d] = daily.get(d, 0) + row["dist_km"]

            days = list(range(1, today_day + 1))
            vals = [round(daily.get(d, 0), 2) for d in days]
            fig2.add_trace(go.Scatter(
                x=[f"{d}일" for d in days], y=vals,
                mode="lines+markers", name=name,
                line=dict(color=color, width=2.5),
                marker=dict(size=5, color=color),
                fill="tozeroy",
                fillcolor=color.replace("#", "rgba(").rstrip(")") + ",0.06)" if color.startswith("#") else color,
            ))

        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sora", color="#c8d8f0"),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor="#141e33", title="km"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
            margin=dict(t=10, b=10, l=0, r=0),
            height=300,
        )
        if not any(not df.empty for df in member_data.values()):
            st.info("연동된 멤버 데이터가 없습니다.")
        else:
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Member detail expanders ──
    st.markdown('<div class="section-label">멤버 상세 기록</div>', unsafe_allow_html=True)

    for i, t in enumerate(totals):
        name  = t["name"]
        color = MEMBER_COLORS.get(name, "#888")
        df    = member_data.get(name, pd.DataFrame())

        avg_hr  = df[df["avg_hr"]  > 0]["avg_hr"].mean()  if not df.empty else 0
        avg_cad = df[df["cadence"] > 0]["cadence"].mean() if not df.empty else 0
        avg_pace= df[df["pace_s"]  > 0]["pace_s"].mean()  if not df.empty else 0

        with st.expander(f"{RANK_ICONS[i]}  {name}  —  {t['km']:.1f} km  ({t['runs']}회)", expanded=(i == 0)):
            # stat boxes
            s1, s2, s3, s4, s5 = st.columns(5)
            boxes = [
                (s1, "총 거리",     f"{t['km']:.1f} km",                  color),
                (s2, "활동 횟수",   f"{t['runs']} 회",                     color),
                (s3, "평균 심박",   f"{avg_hr:.0f} bpm" if avg_hr else "—", "#FF6B6B"),
                (s4, "평균 케이던스", f"{avg_cad:.0f} spm" if avg_cad else "—", "#38BDF8"),
                (s5, "평균 페이스", fmt_pace(avg_pace) if avg_pace else "—", "#FFD93D"),
            ]
            for col, label, val, c in boxes:
                with col:
                    st.markdown(f"""
                    <div class="stat-box">
                        <div class="stat-label">{label}</div>
                        <div class="stat-value" style="color:{c}">{val}</div>
                    </div>""", unsafe_allow_html=True)

            if not df.empty:
                st.markdown("<br>", unsafe_allow_html=True)

                # Cumulative area chart
                daily_map = {}
                for _, row in df.iterrows():
                    if pd.notna(row["date"]):
                        d = row["date"].day
                        daily_map[d] = daily_map.get(d, 0) + row["dist_km"]

                last_day = calendar.monthrange(sel_year, sel_month)[1]
                today_d  = now.day if (sel_year == now.year and sel_month == now.month) else last_day
                days  = list(range(1, today_d + 1))
                daily_vals = [round(daily_map.get(d, 0), 2) for d in days]
                cum_vals   = []
                running = 0
                for v in daily_vals:
                    running += v
                    cum_vals.append(round(running, 2))

                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=[f"{d}일" for d in days], y=cum_vals,
                    mode="lines+markers", name="누적거리",
                    line=dict(color=color, width=2.5),
                    marker=dict(size=4, color=color),
                    fill="tozeroy",
                    fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.12)",
                ))
                fig3.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Sora", color="#c8d8f0"),
                    xaxis=dict(showgrid=False, tickfont=dict(size=10)),
                    yaxis=dict(showgrid=True, gridcolor="#141e33", title="km"),
                    margin=dict(t=10, b=10, l=0, r=0),
                    height=220,
                    showlegend=False,
                )
                st.plotly_chart(fig3, use_container_width=True)

                # Detail table
                display_df = df.copy()
                display_df["날짜"]    = display_df["date"].dt.strftime("%Y-%m-%d")
                display_df["거리(km)"] = display_df["dist_km"]
                display_df["시간"]     = display_df["duration"].apply(fmt_dur)
                display_df["페이스"]   = display_df["pace_s"].apply(fmt_pace)
                display_df["평균심박"] = display_df["avg_hr"].apply(lambda x: f"{x} bpm" if x > 0 else "—")
                display_df["최대심박"] = display_df["max_hr"].apply(lambda x: f"{x} bpm" if x > 0 else "—")
                display_df["케이던스"] = display_df["cadence"].apply(lambda x: f"{x} spm" if x > 0 else "—")
                display_df["고도"]    = display_df["elevation"].apply(lambda x: f"+{x}m" if x > 0 else "—")

                st.dataframe(
                    display_df[["날짜","거리(km)","시간","페이스","평균심박","최대심박","케이던스","고도"]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                if name in members:
                    st.info("이 달 기록이 없습니다.")
                else:
                    st.warning("토큰이 등록되지 않은 멤버입니다. secrets.toml에 추가해주세요.")

    # Footer
    st.markdown(f"""
    <div style="text-align:center;color:#141e33;font-size:0.65rem;letter-spacing:2px;margin-top:3rem">
        POWERED BY RUNALYZE · {sel_year}년 {sel_month}월 · RUN CREW
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
