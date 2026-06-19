import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from datetime import datetime
import io, math

st.set_page_config(page_title="SmartFare-AI", page_icon="🛺", layout="centered")

# ── Global CSS ─────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] { font-family:'Inter',sans-serif !important; }
.stApp { background:#111318 !important; }
.block-container { padding-top:1.5rem !important; max-width:780px !important; }
#MainMenu, footer, header { visibility:hidden; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; color:#F5F5F5 !important; }
p,li { color:#9CA3AF; }

div[data-testid="stHorizontalBlock"] button[kind="primary"] {
    background:#F5C842 !important; color:#111318 !important; border:none !important;
    font-family:'Space Grotesk',sans-serif !important; font-weight:700 !important; border-radius:8px !important;
}
div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
    background:#1A1D24 !important; color:#6B7280 !important;
    border:1px solid #1F2937 !important; border-radius:8px !important;
}
div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
    color:#E5E7EB !important; border-color:#374151 !important;
}
div[data-testid="stVerticalBlock"] button[kind="primary"] {
    background:#F5C842 !important; color:#111318 !important; border:none !important;
    border-radius:10px !important; font-family:'Space Grotesk',sans-serif !important;
    font-weight:700 !important; font-size:1rem !important;
    box-shadow:0 4px 20px rgba(245,200,66,0.3) !important;
}
label { color:#9CA3AF !important; font-size:0.82rem !important; font-weight:500 !important; }
.stNumberInput input {
    background:#1A1D24 !important; border:1px solid #374151 !important;
    color:#F5F5F5 !important; border-radius:8px !important;
    font-family:'JetBrains Mono',monospace !important;
}
.stNumberInput input:focus { border-color:#F5C842 !important; }
.stRadio > div > label {
    background:#1A1D24 !important; border:1px solid #374151 !important;
    border-radius:8px !important; padding:5px 12px !important; color:#9CA3AF !important;
}
.stRadio > div > label:has(input:checked) {
    border-color:#F5C842 !important; background:rgba(245,200,66,0.08) !important; color:#F5C842 !important;
}
[data-testid="stMetric"] {
    background:#1A1D24 !important; border:1px solid #1F2937 !important;
    border-radius:12px !important; padding:16px !important;
}
[data-testid="stMetricLabel"] {
    color:#6B7280 !important; font-size:0.72rem !important;
    font-weight:600 !important; letter-spacing:0.06em !important; text-transform:uppercase !important;
}
[data-testid="stMetricValue"] {
    font-family:'JetBrains Mono',monospace !important; color:#F5F5F5 !important; font-size:1.3rem !important;
}
[data-testid="stExpander"] {
    background:#1A1D24 !important; border:1px solid #1F2937 !important; border-radius:12px !important;
}
.stCode pre {
    background:#1A1D24 !important; border:1px solid #374151 !important;
    border-radius:10px !important; font-family:'JetBrains Mono',monospace !important;
    font-size:0.78rem !important; color:#9CA3AF !important;
}
.stSuccess,.stInfo,.stWarning,.stError { border-radius:10px !important; }
hr { border-color:#1F2937 !important; margin:1rem 0 !important; }
.eyebrow {
    font-family:'Space Grotesk',sans-serif; font-size:0.68rem; font-weight:700;
    letter-spacing:0.12em; text-transform:uppercase; color:#F5C842;
    margin-bottom:10px; display:block;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
for k, v in [("page","analyzer"),("checked",False),("analysis_complete",False),
              ("fare_data",None),("last_trip",{}),("history",[]),
              ("receipt_ts",None),("receipt_ref",None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ────────────────────────────────────────────────────────────────────
RISK_COLOR_HEX = {"High":"#EF4444","Medium":"#F59E0B","Low":"#22C55E"}
RISK_LABEL     = {"High":"🔴 High Risk — Fare appears inflated",
                  "Medium":"🟡 Medium Risk — Slightly above expected",
                  "Low":"🟢 Low Risk — Fare looks reasonable"}
RISK_CLASS     = {"High":"high","Medium":"medium","Low":"low"}

def fmt_diff(diff):
    if diff > 0:  return f"+₹{diff:.2f} above govt fare", "#EF4444", "over"
    if diff < 0:  return f"-₹{abs(diff):.2f} below govt fare", "#22C55E", "under"
    return "Matches govt fare exactly", "#22C55E", "exact"


# ── Thermal Receipt HTML builder ───────────────────────────────────────────────
def build_receipt_html(data, submitted, ts, ref_id):
    """
    Returns a fully self-contained HTML string for the thermal receipt.
    Rendered via st.components.v1.html() — CSS works properly here.
    """
    diff    = data["quoted_fare"] - data["government_expected_fare"]
    typical = data.get("typical_fare", 0)
    diff_str, diff_color, diff_cls = fmt_diff(diff)
    risk    = data["overcharge_risk"]
    rc      = RISK_CLASS[risk]
    period  = "Night (10 PM – 5 AM)" if data["time_of_day"].lower()=="night" else "Day (5 AM – 10 PM)"
    deviation = ((data["quoted_fare"] - data["government_expected_fare"]) / data["government_expected_fare"]) * 100

    RISK_BG    = {"high":"#FEE2E2","medium":"#FEF3C7","low":"#DCFCE7"}
    RISK_FG    = {"high":"#991B1B","medium":"#92400E","low":"#166534"}
    RISK_BORDER= {"high":"#FCA5A5","medium":"#FCD34D","low":"#86EFAC"}

    # Build breakdown rows
    comp_rows = ""
    items = [
        ("Minimum Fare",      "1.5 km",                   data["minimum_fare"]),
        ("Distance Charge",   f"{data['distance_km']} km",data["distance_charge"]),
        ("Waiting Charge",    f"{submitted['waiting_minutes']} min", data["waiting_charge"]),
        ("One-Way Surcharge", "Non-major city",            data["return_charge"]),
        ("Night Surcharge",   "10 PM – 5 AM",             data["night_charge"]),
    ]
    for label, note, amt in items:
        if amt > 0:
            comp_rows += f"""
            <div class="rct-row">
              <span>{label} <span class="rct-note">({note})</span></span>
              <span>&#8377;{amt:.2f}</span>
            </div>"""
        else:
            comp_rows += f"""
            <div class="rct-row rct-zero">
              <span>{label}</span><span>&#8212;</span>
            </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:transparent; font-family:'Courier Prime',Courier,monospace; }}

  .wrap {{ filter:drop-shadow(0 8px 32px rgba(0,0,0,0.5)); max-width:520px; margin:0 auto; }}

  /* Zigzag top */
  .zig-top {{
    width:100%; height:20px;
    background:
      linear-gradient(135deg,#F5F0E8 25%,transparent 25%) -10px 0,
      linear-gradient(225deg,#F5F0E8 25%,transparent 25%) -10px 0,
      linear-gradient(315deg,#F5F0E8 25%,transparent 25%),
      linear-gradient(45deg, #F5F0E8 25%,transparent 25%);
    background-size:20px 20px;
    background-color:transparent;
  }}

  /* Paper body */
  .body {{ background:#F5F0E8; padding:18px 28px 22px; }}

  /* Zigzag bottom */
  .zig-bot {{
    width:100%; height:20px;
    background:
      linear-gradient(315deg,#F5F0E8 25%,transparent 25%) -10px 0,
      linear-gradient(45deg, #F5F0E8 25%,transparent 25%) -10px 0,
      linear-gradient(135deg,#F5F0E8 25%,transparent 25%),
      linear-gradient(225deg,#F5F0E8 25%,transparent 25%);
    background-size:20px 20px;
    background-color:transparent;
  }}

  .meta {{ display:flex; justify-content:space-between; font-size:0.7rem; color:#6B5B45; margin-bottom:14px; }}
  .title {{ font-size:1.35rem; font-weight:700; color:#1A1207; text-align:center; letter-spacing:0.15em; text-transform:uppercase; margin-bottom:3px; }}
  .subtitle {{ font-size:0.7rem; color:#8C7B6A; text-align:center; letter-spacing:0.06em; margin-bottom:14px; }}

  .div-solid {{ border:none; border-top:2px solid #2A1F14; margin:10px 0; }}
  .div-dash  {{ border:none; border-top:1px dashed #C4B49A; margin:8px 0; }}
  .div-dots  {{ border:none; border-top:1px dotted #C4B49A; margin:6px 0; }}

  .section {{ font-size:0.65rem; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#8C7B6A; margin:10px 0 6px; }}

  .rct-row {{ display:flex; justify-content:space-between; align-items:baseline; font-size:0.82rem; color:#2A1F14; margin:3px 0; }}
  .rct-zero {{ color:#C4B49A; }}
  .rct-note {{ font-size:0.67rem; color:#8C7B6A; }}

  .total-row {{ display:flex; justify-content:space-between; font-size:1.05rem; font-weight:700; color:#1A1207; margin:6px 0; }}

  .fare-grid {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin:10px 0; }}
  .fare-cell {{ text-align:center; padding:9px 6px; border:1px dashed #C4B49A; border-radius:4px; background:#EDE8DF; }}
  .fare-lbl  {{ font-size:0.6rem; color:#8C7B6A; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:4px; }}
  .fare-val  {{ font-size:1.05rem; font-weight:700; color:#1A1207; }}
  .fare-val.govt {{ color:#7A5200; }}
  .fare-sub  {{ font-size:0.58rem; color:#8C7B6A; margin-top:2px; }}

  .diff {{ text-align:center; font-size:0.82rem; font-weight:700; margin:6px 0; color:{diff_color}; }}

  .risk {{
    text-align:center; font-size:0.92rem; font-weight:700; letter-spacing:0.02em;
    padding:9px 12px; border-radius:4px; margin:8px 0;
    background:{RISK_BG[rc]}; color:{RISK_FG[rc]}; border:1px dashed {RISK_BORDER[rc]};
  }}
  .risk-sub {{ text-align:center; font-size:0.7rem; color:#8C7B6A; margin-top:3px; }}

  .typical-note {{
    font-size:0.65rem; color:#8C7B6A; text-align:center;
    border:1px dotted #C4B49A; border-radius:4px; padding:5px 8px; margin:6px 0;
    font-style:italic;
  }}

  .footer {{ font-size:0.67rem; color:#8C7B6A; text-align:center; margin-top:14px; line-height:1.7; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="zig-top"></div>
  <div class="body">

    <div class="meta"><span>{ts}</span><span>{ref_id}</span></div>
    <div class="title">Auto Fare</div>
    <div class="subtitle">Kerala G.O.(P) No.14/2022/TRANS</div>

    <div class="div-solid"></div>

    <div class="section">Trip Details</div>
    <div class="rct-row"><span>Distance</span><span>{data['distance_km']} km</span></div>
    <div class="rct-row"><span>Period</span><span>{period}</span></div>
    <div class="rct-row"><span>Waiting</span><span>{submitted['waiting_minutes']} min</span></div>
    <div class="rct-row"><span>Return Journey</span><span>{submitted['return_journey_choice']}</span></div>
    <div class="rct-row"><span>Journey Area</span><span>{submitted['journey_area']}</span></div>

    <div class="div-dash"></div>

    <div class="section">Fare Breakdown</div>
    {comp_rows}

    <div class="div-dash"></div>
    <div class="total-row">
      <span>Govt Fare (Legal Max)</span>
      <span>&#8377;{data['government_expected_fare']:.2f}</span>
    </div>
    <div class="div-solid"></div>

    <div class="section">Fare Comparison</div>
    <div class="fare-grid">
      <div class="fare-cell">
        <div class="fare-lbl">Govt Fare</div>
        <div class="fare-val govt">&#8377;{data['government_expected_fare']:.2f}</div>
        <div class="fare-sub">Legal max</div>
      </div>
      <div class="fare-cell">
        <div class="fare-lbl">Typical Fare</div>
        <div class="fare-val">&#8377;{typical:.2f}</div>
        <div class="fare-sub">Kerala market</div>
      </div>
      <div class="fare-cell">
        <div class="fare-lbl">Quoted Fare</div>
        <div class="fare-val">&#8377;{data['quoted_fare']:.2f}</div>
        <div class="fare-sub">Driver asked</div>
      </div>
    </div>

    <div class="typical-note">
      &#9432; Typical fare is estimated from Kerala real-world observations and may not be 100% accurate
    </div>

    <div class="diff">{diff_str}</div>

    <div class="div-dash"></div>

    <div class="section">Verdict</div>
    <div class="risk">{RISK_LABEL[risk]}</div>
    <div class="risk-sub">Quoted fare is {abs(deviation):.1f}% {'above' if deviation>0 else 'below'} the government rate</div>

    <div class="footer">
      . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .<br>
      Thank you for using SmartFare&#183;AI<br>
      Know your rights as a passenger<br>
      Kerala MVD &#183; mvd.kerala.gov.in
    </div>

  </div>
  <div class="zig-bot"></div>
</div>
</body>
</html>"""


# ── PDF Generator ──────────────────────────────────────────────────────────────
def generate_pdf(data, submitted, timestamp):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors as rc
        from reportlab.lib.units import mm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
    except ImportError:
        return None

    YELLOW = rc.HexColor("#F5C842")
    DARK   = rc.HexColor("#111318")
    CARD   = rc.HexColor("#1A1D24")
    BORDER = rc.HexColor("#2D3748")
    MUTED  = rc.HexColor("#6B7280")
    LIGHT  = rc.HexColor("#E5E7EB")
    GREEN  = rc.HexColor("#22C55E")
    RED    = rc.HexColor("#EF4444")
    AMBER  = rc.HexColor("#F59E0B")
    BLUE   = rc.HexColor("#60A5FA")
    WHITE  = rc.white
    RISK_C = {"High":RED,"Medium":AMBER,"Low":GREEN}

    diff      = data["quoted_fare"] - data["government_expected_fare"]
    typical   = data.get("typical_fare", 0)
    risk      = data["overcharge_risk"]
    period    = "Night (10 PM – 5 AM)" if data["time_of_day"].lower()=="night" else "Day (5 AM – 10 PM)"
    deviation = ((data["quoted_fare"]-data["government_expected_fare"])/data["government_expected_fare"])*100
    diff_str, diff_hex, _ = fmt_diff(diff)
    diff_color = rc.HexColor(diff_hex)
    ref_id = f"#{timestamp.replace(' ','').replace(':','').replace('·','')[-8:].upper()}"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=28*mm, bottomMargin=18*mm,
                            title="SmartFare-AI Fare Report")

    def hf(c, d):
        w, h = A4
        c.saveState()
        c.setFillColor(DARK); c.rect(0, h-22*mm, w, 22*mm, fill=1, stroke=0)
        c.setFont("Helvetica-Bold",14); c.setFillColor(WHITE)
        c.drawString(15*mm, h-13*mm, "SmartFare")
        c.setFillColor(YELLOW)
        c.drawString(15*mm+c.stringWidth("SmartFare","Helvetica-Bold",14), h-13*mm, "·AI")
        c.setFont("Helvetica",7); c.setFillColor(MUTED)
        c.drawString(15*mm, h-18*mm, "Kerala Auto Fare Transparency Tool")
        c.setFont("Courier",8); c.setFillColor(YELLOW)
        c.drawRightString(w-15*mm, h-12*mm, "GO 14/2022")
        c.setFillColor(MUTED); c.drawRightString(w-15*mm, h-17*mm, f"Ref: {ref_id}")
        c.setFillColor(DARK); c.rect(0, 0, w, 12*mm, fill=1, stroke=0)
        c.setFont("Helvetica",7); c.setFillColor(MUTED)
        c.drawString(15*mm, 4*mm,
            "Kerala G.O.(P) No.14/2022/TRANS · Effective 1 May 2022 · Generated by SmartFare-AI")
        c.drawRightString(w-15*mm, 4*mm, f"Page {d.page}  ·  {timestamp}")
        c.restoreState()

    def sec(t):
        return Paragraph(f"<font color='#F5C842' size='8'><b>{t.upper()}</b></font>",
            ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=8,
                           textColor=YELLOW, spaceBefore=4, spaceAfter=6, leading=10))

    s = [Spacer(1,6*mm)]

    # Title block — clearly separated, dark text on white PDF background
    s.append(Paragraph(
        "Fare Transparency Report",
        ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22,
                       textColor=rc.HexColor("#111318"),
                       leading=26, spaceAfter=6, spaceBefore=0)))
    s.append(Paragraph(
        f"Generated: {timestamp}    ·    Ref: {ref_id}",
        ParagraphStyle("sub", fontName="Helvetica", fontSize=9,
                       textColor=rc.HexColor("#6B7280"),
                       leading=12, spaceAfter=10)))
    s.append(HRFlowable(width="100%", thickness=1.5,
                        color=rc.HexColor("#111318"), spaceAfter=12))

    # 1. Trip Details
    s.append(sec("1. Trip Details"))
    td = [["Distance",f"{data['distance_km']} km","Journey Period",period],
          ["Waiting Time",f"{submitted['waiting_minutes']} min","Return Journey",submitted["return_journey_choice"]],
          ["Journey Area",submitted["journey_area"],"",""]]
    tt = Table(td, colWidths=[38*mm,52*mm,38*mm,52*mm])
    tt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),CARD),("TEXTCOLOR",(0,0),(-1,-1),MUTED),
        ("TEXTCOLOR",(1,0),(1,-1),LIGHT),("TEXTCOLOR",(3,0),(3,-1),LIGHT),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTNAME",(1,0),(1,-1),"Courier-Bold"),
        ("FONTNAME",(3,0),(3,-1),"Courier-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
        ("FONTSIZE",(1,0),(1,-1),10),("FONTSIZE",(3,0),(3,-1),10),
        ("PADDING",(0,0),(-1,-1),7),("GRID",(0,0),(-1,-1),0.5,BORDER),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[CARD,rc.HexColor("#1F2937")]),
    ]))
    s += [tt, Spacer(1,8*mm)]

    # 2. Fare Summary
    s.append(sec("2. Fare Summary"))
    fd = [["Fare Type","Amount","Description"],
          ["Govt Fare",   f"Rs.{data['government_expected_fare']:.2f}","Maximum legally permitted — Kerala GO 14/2022"],
          ["Typical Fare",f"Rs.{typical:.2f}",               "Estimated from Kerala real-world observations*"],
          ["Quoted Fare", f"Rs.{data['quoted_fare']:.2f}",   "Amount the driver asked for"]]
    ft = Table(fd, colWidths=[45*mm,30*mm,105*mm])
    ft.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),DARK),("TEXTCOLOR",(0,0),(-1,0),MUTED),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7),
        ("BACKGROUND",(0,1),(-1,-1),CARD),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[CARD,rc.HexColor("#1F2937")]),
        ("TEXTCOLOR",(0,1),(-1,-1),LIGHT),("FONTNAME",(0,1),(-1,-1),"Helvetica"),
        ("FONTNAME",(1,1),(1,-1),"Courier-Bold"),("FONTSIZE",(0,1),(-1,-1),9),
        ("FONTSIZE",(1,1),(1,-1),11),("TEXTCOLOR",(1,1),(1,1),YELLOW),
        ("TEXTCOLOR",(1,2),(1,2),BLUE),("PADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.5,BORDER),("ALIGN",(1,0),(1,-1),"RIGHT"),
    ]))
    s.append(ft); s.append(Spacer(1,3*mm))

    # Typical fare disclaimer
    s.append(Paragraph(
        "<font color='#6B7280' size='7'>* Typical fare is estimated from Kerala real-world observations "
        "and may not be 100% accurate. It will improve as more trip data is collected.</font>",
        ParagraphStyle("disc2", fontName="Helvetica", fontSize=7, textColor=MUTED,
                       leading=9, spaceAfter=4)))

    dt_tbl = Table([["Difference from Govt Fare", diff_str]], colWidths=[130*mm,50*mm])
    dt_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),DARK),("TEXTCOLOR",(0,0),(0,0),MUTED),
        ("TEXTCOLOR",(1,0),(1,0),diff_color),("FONTNAME",(0,0),(0,0),"Helvetica"),
        ("FONTNAME",(1,0),(1,0),"Courier-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
        ("PADDING",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),0.5,BORDER),
        ("ALIGN",(1,0),(1,0),"RIGHT"),
    ]))
    s += [dt_tbl, Spacer(1,8*mm)]

    # 3. Breakdown
    s.append(sec("3. Government Fare Breakdown"))
    comps = [["Component","Applies To","Amount"],
             ["Minimum Fare","First 1.5 km",f"Rs.{data['minimum_fare']:.2f}"],
             ["Distance Charge",f"{data['distance_km']} km — Rs.15/km",
              f"Rs.{data['distance_charge']:.2f}" if data['distance_charge']>0 else "—"],
             ["Waiting Charge",f"{submitted['waiting_minutes']} min — Rs.10/15 min",
              f"Rs.{data['waiting_charge']:.2f}" if data['waiting_charge']>0 else "—"],
             ["One-Way Surcharge","50% above min, non-major city, one-way",
              f"Rs.{data['return_charge']:.2f}" if data['return_charge']>0 else "—"],
             ["Night Surcharge","50% of total, 10 PM – 5 AM",
              f"Rs.{data['night_charge']:.2f}" if data['night_charge']>0 else "—"],
             ["Total Govt Fare","",f"Rs.{data['government_expected_fare']:.2f}"]]
    bk = Table(comps, colWidths=[45*mm,100*mm,35*mm])
    bk.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),DARK),("TEXTCOLOR",(0,0),(-1,0),MUTED),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7),
        ("BACKGROUND",(0,1),(-1,-2),CARD),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[CARD,rc.HexColor("#1F2937")]),
        ("TEXTCOLOR",(0,1),(-1,-2),LIGHT),("TEXTCOLOR",(1,1),(1,-2),MUTED),
        ("FONTNAME",(0,1),(-1,-1),"Helvetica"),("FONTNAME",(2,1),(2,-1),"Courier-Bold"),
        ("FONTSIZE",(0,1),(-1,-1),9),
        ("BACKGROUND",(0,-1),(-1,-1),DARK),("TEXTCOLOR",(0,-1),(-1,-1),YELLOW),
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),("FONTSIZE",(0,-1),(-1,-1),10),
        ("PADDING",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),0.5,BORDER),
        ("ALIGN",(2,0),(2,-1),"RIGHT"),
    ]))
    s += [bk, Spacer(1,8*mm)]

    # 4. Risk
    s.append(sec("4. Risk Assessment"))
    rsk_label = {"High":"High Risk — Fare appears inflated",
                 "Medium":"Medium Risk — Slightly above expected",
                 "Low":"Low Risk — Fare looks reasonable"}[risk]
    rsk = Table([[rsk_label, f"{deviation:+.1f}% vs govt rate"]], colWidths=[130*mm,50*mm])
    rsk.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),DARK),("TEXTCOLOR",(0,0),(0,0),RISK_C[risk]),
        ("TEXTCOLOR",(1,0),(1,0),MUTED),("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(0,0),11),("FONTSIZE",(1,0),(1,0),9),
        ("PADDING",(0,0),(-1,-1),10),("GRID",(0,0),(-1,-1),0.5,BORDER),
        ("ALIGN",(1,0),(1,0),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    s.append(rsk); s.append(Spacer(1,4*mm))
    lgd = Table([["Low — Within typical range","Medium — Up to 20% above typical","High — More than 20% above typical"]],
                colWidths=[60*mm,66*mm,54*mm])
    lgd.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),CARD),("TEXTCOLOR",(0,0),(-1,-1),MUTED),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8),
        ("PADDING",(0,0),(-1,-1),7),("GRID",(0,0),(-1,-1),0.5,BORDER),
    ]))
    s += [lgd, Spacer(1,8*mm)]

    s.append(HRFlowable(width="100%",thickness=0.5,color=rc.HexColor("#CBD5E0"),spaceAfter=6))
    s.append(Paragraph(
        "<font color='#6B7280' size='7'>This report is generated by SmartFare-AI for informational purposes. "
        "Fare calculations are based on Kerala G.O.(P) No.14/2022/TRANS effective 1 May 2022. "
        "Typical fare is estimated from Kerala real-world observations and may not be 100% accurate. "
        "For official complaints, contact Kerala Motor Vehicles Department.</font>",
        ParagraphStyle("d", fontName="Helvetica", fontSize=7,
                       textColor=MUTED, leading=10)))

    doc.build(s, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


# ── Hero ───────────────────────────────────────────────────────────────────────
col_logo, col_badge = st.columns([5,1])
with col_logo:
    st.markdown("<h1 style='margin:0;font-size:1.7rem;letter-spacing:-0.03em;'>"
                "🛺 Smart<span style='color:#F5C842'>Fare</span>·AI</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='margin:2px 0 0;font-size:0.75rem;color:#4B5563;"
                "text-transform:uppercase;letter-spacing:0.06em;'>"
                "Kerala Auto Fare Transparency Tool</p>", unsafe_allow_html=True)
with col_badge:
    st.markdown("<div style='background:#F5C842;border:1px solid #D4A900;"
                "color:#111318;font-size:0.7rem;font-weight:800;padding:5px 10px;border-radius:20px;"
                "text-align:center;margin-top:8px;letter-spacing:0.06em;'>GO 14/2022</div>",
                unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ── Nav ────────────────────────────────────────────────────────────────────────
page = st.session_state["page"]
n1,n2,n3,n4 = st.columns(4)
for col,(pg,label) in zip([n1,n2,n3,n4],[
    ("analyzer","🏠 Analyzer"),("breakdown","📋 Breakdown"),
    ("history","🕘 History"),("about","ℹ️ About")]):
    with col:
        if st.button(label, use_container_width=True,
                     type="primary" if page==pg else "secondary",
                     key=f"nav_{pg}"):
            st.session_state["page"] = pg
            st.rerun()

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

data              = st.session_state.get("fare_data")
analysis_complete = st.session_state.get("analysis_complete", False)


# ════════════════════════════════════════════════════════════════════════════════
# ANALYZER
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "analyzer":
    last = st.session_state.get("last_trip", {})

    st.markdown("<span class='eyebrow'>Trip Details</span>", unsafe_allow_html=True)
    with st.container(border=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            distance = st.number_input("Distance (km)", min_value=0.5, step=0.1,
                value=last.get("distance",0.5))
        with c2:
            journey_time = st.radio("Journey Time",
                ["Day  (5 AM – 10 PM)","Night  (10 PM – 5 AM)"],
                index=0 if last.get("journey_time","Day  (5 AM – 10 PM)").startswith("Day") else 1)
        with c3:
            quoted_fare = st.number_input("Quoted Fare (₹)", min_value=0.0, step=1.0,
                value=last.get("quoted_fare",0.0))
            if 0 < quoted_fare < 30:
                st.warning("Minimum fare is ₹30.")
        c4,c5,c6 = st.columns(3)
        with c4:
            waiting_minutes = st.number_input("Waiting Time (min)", min_value=0, step=5,
                value=last.get("waiting_minutes",0))
        with c5:
            return_journey_choice = st.radio("Return Journey",["No","Yes"],
                index=0 if last.get("return_journey_choice","No")=="No" else 1,
                horizontal=True)
        with c6:
            journey_area = st.radio("Journey Area",["Major City","Non-Major City"],
                index=0 if last.get("journey_area","Non-Major City")=="Major City" else 1,
                horizontal=True)
        st.caption("📜 Kerala G.O.(P) No.14/2022/TRANS · Effective 1 May 2022")

    if journey_area=="Non-Major City" and return_journey_choice=="No":
        st.info("ℹ️ One-way trip outside a major city — 50% surcharge on metered fare above minimum may apply.")

    current_trip = {"distance":distance,"quoted_fare":quoted_fare,
                    "waiting_minutes":waiting_minutes,"journey_time":journey_time,
                    "return_journey_choice":return_journey_choice,"journey_area":journey_area}
    if st.session_state["last_trip"] and current_trip != st.session_state["last_trip"]:
        st.session_state["analysis_complete"] = False
        st.session_state["fare_data"] = None
        data, analysis_complete = None, False

    if st.button("🔍  Analyze Fare", use_container_width=True, type="primary"):
        if quoted_fare <= 0:
            st.warning("⚠️ Enter the fare the driver quoted before analyzing.")
            st.stop()
        st.session_state["last_trip"] = current_trip
        st.session_state.checked = True

    analysis_complete = st.session_state.get("analysis_complete", False)
    data = st.session_state.get("fare_data")

    # ── Thermal Receipt via components.html ───────────────────────────────────
    if analysis_complete and data:
        submitted = st.session_state["last_trip"]

        ts     = st.session_state.get("receipt_ts") or datetime.now().strftime("%d %b %Y, %I:%M %p")
        ref_id = st.session_state.get("receipt_ref") or f"#{ts.replace(' ','').replace(':','').replace(',','')[-8:].upper()}"

        diff   = data["quoted_fare"] - data["government_expected_fare"]
        diff_str, diff_color_hex, _ = fmt_diff(diff)
        typical = data.get("typical_fare", 0)
        deviation = ((data["quoted_fare"]-data["government_expected_fare"])/data["government_expected_fare"])*100

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("<span class='eyebrow'>Fare Transparency Receipt</span>", unsafe_allow_html=True)

        receipt_html = build_receipt_html(data, submitted, ts, ref_id)
        components.html(receipt_html, height=860, scrolling=True)

        # ── Export & Share ────────────────────────────────────────────────────
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("<span class='eyebrow'>Export &amp; Share</span>", unsafe_allow_html=True)

        pdf_col, share_col = st.columns(2)
        with pdf_col:
            pdf_bytes = generate_pdf(data, submitted, ts)
            if pdf_bytes:
                st.download_button(
                    label="📄  Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"SmartFare_Report_{ref_id.strip('#')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.info("Install `reportlab` to enable PDF export.")

        with share_col:
            with st.expander("📱 Share on WhatsApp"):
                period = "Night (10 PM – 5 AM)" if data["time_of_day"].lower()=="night" else "Day (5 AM – 10 PM)"
                share_text = (
                    f"🛺 SmartFare-AI Fare Check\n"
                    f"{'━'*28}\n"
                    f"📅 {ts}  {ref_id}\n"
                    f"{'━'*28}\n"
                    f"Distance       : {data['distance_km']} km\n"
                    f"Period         : {period}\n"
                    f"Waiting Time   : {submitted['waiting_minutes']} min\n"
                    f"Return Journey : {submitted['return_journey_choice']}\n"
                    f"Journey Area   : {submitted['journey_area']}\n"
                    f"{'━'*28}\n"
                    f"🏛 Govt Fare   : ₹{data['government_expected_fare']:.2f}\n"
                    f"📊 Typical Fare: ₹{typical:.2f} (Kerala est.)\n"
                    f"💰 Quoted Fare : ₹{data['quoted_fare']:.2f}\n"
                    f"Difference    : {diff_str}\n"
                    f"{'━'*28}\n"
                    f"Verdict: {RISK_LABEL[data['overcharge_risk']]}\n"
                    f"{'━'*28}\n"
                    f"SmartFare-AI · GO 14/2022\n"
                    f"* Typical fare estimated from Kerala observations"
                )
                st.code(share_text, language=None)
                st.caption("Copy and paste into WhatsApp.")

    else:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center;padding:40px 20px;'>"
            "<div style='font-size:2.5rem;margin-bottom:12px;opacity:0.5;'>🛺</div>"
            "<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;"
            "font-weight:600;color:#6B7280;margin-bottom:6px;'>Enter your trip details above</div>"
            "<div style='font-size:0.8rem;color:#4B5563;'>Fill in the distance, quoted fare, "
            "and trip conditions — then hit Analyze Fare.</div></div>",
            unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# BREAKDOWN
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "breakdown":
    if analysis_complete and data:
        submitted = st.session_state["last_trip"]
        typical   = data.get("typical_fare",0)
        diff      = data["quoted_fare"] - data["government_expected_fare"]
        diff_str, diff_color_hex, _ = fmt_diff(diff)
        deviation = ((data["quoted_fare"]-data["government_expected_fare"])/data["government_expected_fare"])*100

        st.markdown("<span class='eyebrow'>Kerala Government Fare Breakdown</span>", unsafe_allow_html=True)

        bdf = pd.DataFrame([
            {"Component":"Minimum Fare",     "Note":"₹30 for first 1.5 km",                      "Amount (₹)":data["minimum_fare"]},
            {"Component":"Distance Charge",  "Note":f"{data['distance_km']} km · ₹15/km",        "Amount (₹)":data["distance_charge"]},
            {"Component":"Waiting Charge",   "Note":f"{submitted['waiting_minutes']} min · ₹10/15 min","Amount (₹)":data["waiting_charge"]},
            {"Component":"One-Way Surcharge","Note":"50% above min · non-major city one-way",     "Amount (₹)":data["return_charge"]},
            {"Component":"Night Surcharge",  "Note":"50% of total · 10 PM – 5 AM",              "Amount (₹)":data["night_charge"]},
        ])
        st.dataframe(
            bdf.style.format({"Amount (₹)":"₹{:.2f}"})
               .applymap(lambda v:"color:#4B5563" if v==0.0 else "", subset=["Amount (₹)"]),
            use_container_width=True, hide_index=True)

        st.markdown(
            f"<div style='background:#1A1D24;border:1px solid #F5C842;border-radius:10px;"
            f"padding:14px 20px;display:flex;justify-content:space-between;margin-top:4px;'>"
            f"<span style='font-family:Space Grotesk,sans-serif;font-weight:700;color:#F5C842;'>Total Government Fare</span>"
            f"<span style='font-family:JetBrains Mono,monospace;font-weight:700;color:#F5C842;font-size:1.1rem;'>"
            f"₹{data['government_expected_fare']:.2f}</span></div>",
            unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("<span class='eyebrow'>Fare Comparison</span>", unsafe_allow_html=True)

        # Correct order: Govt → Typical → Quoted
        chart_df = pd.DataFrame({
            "Fare Type":["Govt Fare","Typical Fare","Quoted Fare"],
            "Amount (₹)":[data["government_expected_fare"], typical, data["quoted_fare"]]
        }).set_index("Fare Type")
        st.bar_chart(chart_df, color="#F5C842")
        st.caption("Left to right: Govt Fare (legal max) → Quoted Fare (driver asked) → Typical Fare (Kerala est.)")

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("<span class='eyebrow'>What Do These Amounts Mean?</span>", unsafe_allow_html=True)

        parts = [f"₹{data['minimum_fare']:.0f} minimum"]
        if data["distance_charge"]>0: parts.append(f"₹{data['distance_charge']:.2f} distance")
        if data["waiting_charge"]>0:  parts.append(f"₹{data['waiting_charge']:.2f} waiting")
        if data["return_charge"]>0:   parts.append(f"₹{data['return_charge']:.2f} one-way surcharge")
        if data["night_charge"]>0:    parts.append(f"₹{data['night_charge']:.2f} night surcharge")
        breakdown_str = " + ".join(parts)

        typical_diff = data["quoted_fare"] - typical
        typical_compare = (f"₹{typical_diff:.2f} above typical" if typical_diff>0
                           else f"₹{abs(typical_diff):.2f} below typical" if typical_diff<0
                           else "exactly at the typical rate")

        with st.container(border=True):
            st.markdown(
                f"**🏛️ Government Fare — ₹{data['government_expected_fare']:.2f}**\n\n"
                f"The maximum legally permitted fare per Kerala GO 14/2022. "
                f"No driver can legally charge more than this.\n\n"
                f"*For this trip: {breakdown_str} = ₹{data['government_expected_fare']:.2f}*")
        with st.container(border=True):
            st.markdown(
                f"**📊 Typical Fare — ₹{typical:.2f}**\n\n"
                f"What drivers across Kerala commonly charge for this distance and time. "
                f"Not the legal maximum — the market reality based on real-world observations.\n\n"
                f"*⚠️ This is an estimate based on Kerala real-world observations and may not be 100% accurate. "
                f"Accuracy improves as more trip data is collected.*")
        with st.container(border=True):
            st.markdown(
                f"**💰 Quoted Fare — ₹{data['quoted_fare']:.2f}**\n\n"
                f"What your driver asked for. This is {diff_str.lower()} and {typical_compare}.\n\n"
                f"*That is {abs(deviation):.1f}% {'above' if deviation>0 else 'below'} the government permitted rate.*")
        with st.container(border=True):
            st.markdown("**🚦 Risk Levels Explained**")
            r1,r2,r3 = st.columns(3)
            with r1:
                st.markdown("<span style='color:#22C55E;'>🟢 **Low**</span><br>"
                            "<span style='color:#6B7280;font-size:0.78rem;'>Within typical range</span>",
                            unsafe_allow_html=True)
            with r2:
                st.markdown("<span style='color:#F59E0B;'>🟡 **Medium**</span><br>"
                            "<span style='color:#6B7280;font-size:0.78rem;'>Up to 20% above typical</span>",
                            unsafe_allow_html=True)
            with r3:
                st.markdown("<span style='color:#EF4444;'>🔴 **High**</span><br>"
                            "<span style='color:#6B7280;font-size:0.78rem;'>More than 20% above typical</span>",
                            unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center;padding:40px 24px 16px;'>"
                    "<div style='font-size:2.5rem;margin-bottom:12px;opacity:0.5;'>📋</div>"
                    "<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;"
                    "font-weight:600;color:#6B7280;margin-bottom:6px;'>No analysis yet</div>"
                    "<div style='font-size:0.8rem;color:#4B5563;'>Run a fare analysis first to see the breakdown.</div>"
                    "</div>", unsafe_allow_html=True)
        bcol1, bcol2, bcol3 = st.columns([1,1,1])
        with bcol2:
            if st.button("🏠  Go to Analyzer", use_container_width=True, type="primary"):
                st.session_state["page"] = "analyzer"
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# HISTORY
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "history":
    history = st.session_state.get("history",[])
    st.markdown("<span class='eyebrow'>Last 5 Fare Checks</span>", unsafe_allow_html=True)

    if not history:
        st.markdown("<div style='text-align:center;padding:40px 24px 16px;'>"
                    "<div style='font-size:2.5rem;margin-bottom:12px;opacity:0.5;'>🕘</div>"
                    "<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;"
                    "font-weight:600;color:#6B7280;margin-bottom:6px;'>No history yet</div>"
                    "<div style='font-size:0.8rem;color:#4B5563;'>Your last 5 fare checks will appear here.</div>"
                    "</div>", unsafe_allow_html=True)
        hcol1, hcol2, hcol3 = st.columns([1,1,1])
        with hcol2:
            if st.button("🏠  Go to Analyzer", use_container_width=True, type="primary", key="hist_go"):
                st.session_state["page"] = "analyzer"
                st.rerun()
    else:
        for record in reversed(history):
            d=record["data"]; sub=record["submitted"]; ts=record["timestamp"]
            typical=d.get("typical_fare",0)
            diff=d["quoted_fare"]-d["government_expected_fare"]
            diff_str,diff_color_hex,_=fmt_diff(diff)
            risk=d["overcharge_risk"]; rc_hex=RISK_COLOR_HEX[risk]
            period="Night" if d["time_of_day"].lower()=="night" else "Day"

            with st.container(border=True):
                h1,h2=st.columns([3,2])
                with h1:
                    st.markdown(f"<span style='font-family:Space Grotesk,sans-serif;"
                                f"font-weight:700;font-size:0.9rem;color:{rc_hex};'>"
                                f"{RISK_LABEL[risk]}</span>", unsafe_allow_html=True)
                with h2:
                    st.markdown(f"<span style='font-family:JetBrains Mono,monospace;"
                                f"font-size:0.72rem;color:#F5C842;font-weight:700;float:right;'>"
                                f"📅 {ts}</span>", unsafe_allow_html=True)

                st.markdown("<hr style='margin:8px 0;border-color:#1F2937;'>", unsafe_allow_html=True)

                g1,g2,g3,g4,g5 = st.columns(5)
                for col,lbl,val in [
                    (g1,"Distance",f"{d['distance_km']} km"),
                    (g2,"Period",period),
                    (g3,"Waiting",f"{sub['waiting_minutes']} min"),
                    (g4,"Return Journey",sub['return_journey_choice']),
                    (g5,"Journey Area",sub['journey_area']),
                ]:
                    with col:
                        st.markdown(f"<span style='font-size:0.64rem;color:#6B7280;"
                                    f"text-transform:uppercase;letter-spacing:0.04em;'>{lbl}</span><br>"
                                    f"<span style='font-size:0.82rem;font-weight:600;color:#E5E7EB;'>{val}</span>",
                                    unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                f1,f2,f3=st.columns(3)
                for col,lbl,val,color in [
                    (f1,"🏛️ Govt Fare",   f"₹{d['government_expected_fare']:.2f}","#F5C842"),
                    (f2,"📊 Typical Fare", f"₹{typical:.2f}",                      "#60A5FA"),
                    (f3,"💰 Quoted Fare",  f"₹{d['quoted_fare']:.2f}",             "#E5E7EB"),
                ]:
                    with col:
                        sub_label = {"#F5C842":"Legal max","#60A5FA":"Kerala est.","#E5E7EB":"Driver asked"}[color]
                        st.markdown(
                            f"<div style='background:#111318;border:1px solid #1F2937;"
                            f"border-radius:8px;padding:10px 12px;'>"
                            f"<div style='font-size:0.63rem;color:#6B7280;font-weight:600;"
                            f"letter-spacing:0.05em;text-transform:uppercase;margin-bottom:4px;'>{lbl}</div>"
                            f"<div style='font-family:JetBrains Mono,monospace;font-size:1rem;"
                            f"font-weight:700;color:{color};'>{val}</div>"
                            f"<div style='font-size:0.6rem;color:#4B5563;margin-top:2px;'>{sub_label}</div>"
                            f"</div>", unsafe_allow_html=True)

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div style='background:#1F2937;border-radius:6px;padding:8px 12px;"
                    f"font-family:JetBrains Mono,monospace;font-size:0.82rem;"
                    f"font-weight:600;color:{diff_color_hex};'>{diff_str}</div>",
                    unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state["history"]=[]
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# ABOUT
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "about":

    # ── What is SmartFare-AI ──────────────────────────────────────────────────
    st.markdown("<span class='eyebrow'>What is SmartFare-AI?</span>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            "Auto-rickshaw fares in Kerala are regulated by the state government, but most "
            "passengers don't know the rules or the permitted rates — making it difficult to "
            "judge whether a quoted fare is reasonable.\n\n"
            "**SmartFare-AI solves this** by computing the exact government-permitted fare "
            "from Kerala G.O.(P) No.14/2022/TRANS, estimating a typical real-world fare from "
            "observed trip data, and generating a timestamped transparency receipt — all in seconds."
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── How it works ─────────────────────────────────────────────────────────
    st.markdown("<span class='eyebrow'>How It Works</span>", unsafe_allow_html=True)
    h1, h2, h3 = st.columns(3)
    with h1:
        with st.container(border=True):
            st.markdown(
                "**1 · Enter Trip Details**\n\n"
                "Distance, journey time, waiting time, return journey, and area type."
            )
    with h2:
        with st.container(border=True):
            st.markdown(
                "**2 · Fare is Analysed**\n\n"
                "Government fare calculated from GO rules. Typical fare predicted by an ML model."
            )
    with h3:
        with st.container(border=True):
            st.markdown(
                "**3 · Receipt Generated**\n\n"
                "A timestamped receipt and downloadable PDF report with full fare breakdown."
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Project stats ─────────────────────────────────────────────────────────
    st.markdown("<span class='eyebrow'>Project Stats</span>", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    for col, num, lbl, note in [
        (s1, "200",  "Training Samples",    "Synthetic dataset anchored to real trips"),
        (s2, "6",    "Fare Components",     "Rules from Kerala GO 14/2022"),
        (s3, "5",    "Real Anchor Trips",   "Observed Kerala fares used as ground truth"),
        (s4, "2",    "ML Models Trained",   "Ridge + Gradient Boosting, best selected"),
    ]:
        with col:
            st.metric(lbl, num)
            st.caption(note)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Tech Stack ────────────────────────────────────────────────────────────
    st.markdown("<span class='eyebrow'>Tech Stack</span>", unsafe_allow_html=True)
    with st.container(border=True):
        t1, t2 = st.columns(2)
        with t1:
            st.markdown(
                "**Frontend**\n"
                "- Streamlit 1.31.1\n"
                "- Custom thermal receipt UI via `st.components.v1.html`\n"
                "- PDF generation with ReportLab\n\n"
                "**Backend**\n"
                "- FastAPI + Uvicorn\n"
                "- Pydantic input validation\n"
                "- REST API with auto-generated docs"
            )
        with t2:
            st.markdown(
                "**Machine Learning**\n"
                "- Scikit-learn (Ridge, Gradient Boosting)\n"
                "- Pandas, NumPy for feature engineering\n"
                "- Joblib for model serialisation\n\n"
                "**Deployment**\n"
                "- Frontend: Streamlit Community Cloud\n"
                "- Backend: Render\n"
                "- Language: Python 3.11"
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Data & Model Transparency ─────────────────────────────────────────────
    st.markdown("<span class='eyebrow'>Data & Model Transparency</span>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            "The **government fare** is calculated entirely from the Kerala GO rules — no model "
            "is involved. It is deterministic and auditable.\n\n"
            "The **typical fare** is predicted by a Gradient Boosting model trained on a "
            "synthetic dataset anchored to 5 real trip observations across Kerala. "
            "Features include distance, time of day, government fare (as a predictive signal), "
            "and a night × distance interaction term.\n\n"
            "⚠️ Typical fare estimates are based on real-world observations and may not be "
            "100% accurate. The model is designed to be retrained when sufficient real user "
            "trip data is collected."
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Fare Rules ────────────────────────────────────────────────────────────
    with st.expander("📜 Kerala Fare Rules — G.O.(P) No.14/2022/TRANS"):
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        rules = [
            ("Minimum Fare",       "₹30 for the first 1.5 km, regardless of shorter distance."),
            ("Distance Charge",    "₹15 per km (₹1.50 per 100 m) for every metre beyond 1.5 km."),
            ("Night Surcharge",    "50% of total hire charge for journeys between 10 PM and 5 AM."),
            ("Waiting / Detention","₹10 per 15 minutes or part thereof. Maximum ₹250 per day."),
            ("One-Way Surcharge",  "50% of the metered fare above the minimum for one-way trips "
                                   "outside major city areas — applied because the driver returns empty."),
            ("Major City Exemption","No one-way surcharge in: Thiruvananthapuram · Kollam · Kochi · "
                                    "Thrissur · Kozhikode · Kannur · Palakkad · Kottayam"),
        ]
        for title, desc in rules:
            r1, r2 = st.columns([1, 2])
            with r1:
                st.markdown(f"**{title}**")
            with r2:
                st.markdown(desc)
            st.markdown("<hr style='margin:6px 0;border-color:#1F2937;'>", unsafe_allow_html=True)
        st.caption("📜 Kerala Gazette Extraordinary No. 1381 · 26 April 2022 · Effective 1 May 2022")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Links ─────────────────────────────────────────────────────────────────
    st.markdown("<span class='eyebrow'>Links</span>", unsafe_allow_html=True)
    with st.container(border=True):
        lk1, lk2 = st.columns(2)
        with lk1:
            st.markdown(
                "<div style='text-align:center;padding:8px;'>"
                "<div style='font-size:1.4rem;margin-bottom:6px;'>📡</div>"
                "<div style='font-size:0.78rem;color:#6B7280;margin-bottom:6px;'>Backend API Docs</div>"
                "<a href='https://smartfare-ai-backend.onrender.com/docs' target='_blank' "
                "style='color:#F5C842;text-decoration:none;font-size:0.82rem;font-weight:600;'>"
                "View Docs ↗</a>"
                "<div style='font-size:0.68rem;color:#4B5563;margin-top:4px;'>"
                "Interactive FastAPI docs — try the API directly</div>"
                "</div>",
                unsafe_allow_html=True)
        with lk2:
            st.markdown(
                "<div style='text-align:center;padding:8px;'>"
                "<div style='font-size:1.4rem;margin-bottom:6px;'>💻</div>"
                "<div style='font-size:0.78rem;color:#6B7280;margin-bottom:6px;'>Source Code</div>"
                "<a href='https://github.com/rinorobert' target='_blank' "
                "style='color:#F5C842;text-decoration:none;font-size:0.82rem;font-weight:600;'>"
                "GitHub ↗</a>"
                "<div style='font-size:0.68rem;color:#4B5563;margin-top:4px;'>"
                "Full source — frontend, backend, notebook, dataset</div>"
                "</div>",
                unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Built By ──────────────────────────────────────────────────────────────
    st.markdown("<span class='eyebrow'>Built By</span>", unsafe_allow_html=True)
    with st.container(border=True):
        b1, b2 = st.columns([3, 1])
        with b1:
            st.markdown(
                "**Rino Robert**  \n"
                "B.Tech — Artificial Intelligence & Data Science\n\n"
                "Built SmartFare-AI as a personal project to address a real problem "
                "experienced using auto-rickshaws across Kerala. The project demonstrates "
                "end-to-end ML product development — from data collection and model training "
                "to API design, frontend development, and cloud deployment."
            )
        with b2:
            st.markdown(
                "<div style='display:flex;flex-direction:column;gap:10px;padding-top:4px;'>"
                "<a href='https://linkedin.com/in/rino-robert' target='_blank' "
                "style='color:#F5C842;text-decoration:none;font-size:0.82rem;font-weight:600;'>"
                "LinkedIn ↗</a>"
                "<a href='https://github.com/rinorobert' target='_blank' "
                "style='color:#F5C842;text-decoration:none;font-size:0.82rem;font-weight:600;'>"
                "GitHub ↗</a>"
                "<a href='mailto:rinorobert710@gmail.com' "
                "style='color:#F5C842;text-decoration:none;font-size:0.82rem;font-weight:600;'>"
                "Email ↗</a>"
                "</div>",
                unsafe_allow_html=True
            )


# ════════════════════════════════════════════════════════════════════════════════
# API CALL
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state.checked:
    trip=st.session_state["last_trip"]
    payload={"distance_km":trip["distance"],
             "time_of_day":"night" if trip["journey_time"].startswith("Night") else "day",
             "quoted_fare":trip["quoted_fare"],"waiting_minutes":trip["waiting_minutes"],
             "return_journey":trip["return_journey_choice"]=="Yes",
             "major_city":trip["journey_area"]=="Major City"}
    try:
        with st.spinner("Calculating fare..."):
            response=requests.post("https://smartfare-ai-backend.onrender.com/predict",
                                   json=payload,timeout=35)
        if response.status_code==200:
            result=response.json()

            fixed_ts = datetime.now().strftime("%d %b %Y, %I:%M %p")
            fixed_ref = f"#{fixed_ts.replace(' ','').replace(':','').replace(',','')[-8:].upper()}"

            st.session_state["fare_data"]=result
            st.session_state["analysis_complete"]=True
            st.session_state["receipt_ts"]=fixed_ts
            st.session_state["receipt_ref"]=fixed_ref
            st.session_state.checked=False

            entry={"data":result,"submitted":trip,"timestamp":fixed_ts,"ref_id":fixed_ref}
            h=st.session_state.get("history",[])
            h.append(entry)
            st.session_state["history"]=h[-5:]
            st.rerun()
        else:
            st.error(f"Backend error — Status {response.status_code}")
    except requests.exceptions.Timeout:
        st.warning("⏳ Backend waking up (free-tier hosting). Please retry in 30–60 seconds.")
    except requests.exceptions.ConnectionError:
        st.warning("🔌 Unable to reach the backend.")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;font-size:0.75rem;color:#374151;'>"
            "© Rino Robert · 2026 · <span style='color:#F5C842;'>SmartFare·AI</span> · Educational Project"
            "</p>", unsafe_allow_html=True)
