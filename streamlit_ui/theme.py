"""Shared Streamlit theme: light astrochemistry background + adaptive text."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).resolve().parent / "assets"
_BG_PATH = _ASSETS / "background.png"


def _background_layer() -> str:
    if not _BG_PATH.exists():
        return "linear-gradient(165deg, #f4f8ff 0%, #e8f0fa 48%, #dfeaf8 100%)"
    encoded = base64.b64encode(_BG_PATH.read_bytes()).decode("ascii")
    return (
        "linear-gradient(rgba(255, 255, 255, 0.68), rgba(248, 252, 255, 0.58)), "
        f"url('data:image/png;base64,{encoded}') center center / cover no-repeat fixed"
    )


def apply_starry_theme() -> None:
    bg = _background_layer()
    st.markdown(
        f"""
<style>
:root {{
  color-scheme: light;
  --bg-image: {bg};
  --card: rgba(255, 255, 255, 0.82);
  --card-border: rgba(72, 118, 178, 0.28);
  --text: #152238;
  --text-soft: #2a3f5c;
  --muted: #4a627f;
  --accent: #3d7ee8;
  --accent-2: #5b6adf;
  --primary-color: #2f6fd4;
  --on-accent: #ffffff;
  --input-bg: rgba(255, 255, 255, 0.92);
  --shadow: rgba(36, 72, 128, 0.12);
}}

.stApp {{
  color: var(--text);
  background: var(--bg-image);
}}

[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main > div {{
  background: transparent;
}}

h1, h2, h3, h4, h5, h6, p, label, span, li, div {{
  color: var(--text);
}}

[data-testid="stSidebar"] {{
  background: rgba(255, 255, 255, 0.88);
  border-right: 1px solid var(--card-border);
  backdrop-filter: blur(8px);
}}

[data-testid="stSidebar"] * {{
  color: var(--text-soft);
}}

[data-testid="stForm"], .stAlert, [data-testid="stExpander"] {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  backdrop-filter: blur(6px);
  box-shadow: 0 4px 18px var(--shadow);
}}

[data-testid="stDataFrame"],
.stDataFrame {{
  background: var(--card) !important;
  border: 1.5px solid var(--card-border) !important;
  border-radius: 12px !important;
  padding: 0.4rem !important;
  overflow: hidden;
  box-shadow: 0 4px 16px var(--shadow);
}}

[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
[data-testid="stDataFrame"] [data-testid="glideDataEditor"] {{
  border-radius: 8px;
}}

[data-testid="stImage"] {{
  background: var(--card);
  border: 1.5px solid var(--card-border) !important;
  border-radius: 12px;
  padding: 0.55rem;
  box-sizing: border-box;
  box-shadow: 0 4px 16px var(--shadow);
}}

[data-testid="stImage"] img {{
  border-radius: 8px;
  border: 1px solid rgba(72, 118, 178, 0.2);
  display: block;
  width: 100%;
}}

.plot-explanation-card {{
  background: var(--card);
  border: 1.5px solid var(--card-border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin: 0.5rem 0 0.85rem 0;
  color: var(--text-soft) !important;
  font-size: 0.95rem;
  line-height: 1.55;
  backdrop-filter: blur(6px);
  box-shadow: 0 4px 14px var(--shadow);
}}

.plot-explanation-card strong {{
  color: var(--text) !important;
}}

.physical-conditions-card {{
  background: var(--card);
  border: 1.5px solid var(--card-border);
  border-radius: 10px;
  padding: 0.85rem 1.1rem 0.95rem 1rem;
  margin: 0.35rem 0 1rem 0;
  backdrop-filter: blur(6px);
  box-shadow: 0 4px 14px var(--shadow);
}}

.physical-conditions-list {{
  list-style-type: disc;
  margin: 0;
  padding: 0 0 0 1.35rem;
  color: var(--text-soft);
  font-size: 0.94rem;
  line-height: 1.5;
}}

.physical-conditions-list li {{
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.35rem 1rem;
  margin-bottom: 0.65rem;
  padding-left: 0.15rem;
}}

.physical-conditions-list li:last-child {{
  margin-bottom: 0;
}}

.physical-conditions-list .pc-label {{
  flex: 0 0 13.5rem;
  max-width: 100%;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}}

.physical-conditions-list .pc-label::after {{
  content: ":";
  margin-left: 0.12rem;
  color: rgba(74, 98, 127, 0.65);
  font-weight: 400;
  text-transform: none;
}}

.physical-conditions-list .pc-value {{
  flex: 1 1 12rem;
  min-width: 0;
  color: var(--text);
  font-size: 0.96rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}}

[data-testid="stMetric"] {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  box-sizing: border-box;
  padding: 0.9rem 1.1rem 1rem !important;
  min-height: 5.6rem;
  overflow: visible;
  box-shadow: 0 4px 14px var(--shadow);
}}

[data-testid="stMetricLabel"] {{
  padding: 0 !important;
  margin: 0 0 0.45rem 0 !important;
  line-height: 1.35 !important;
  white-space: normal;
  color: var(--muted) !important;
}}

[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div {{
  padding: 0 !important;
  margin: 0 !important;
  color: var(--muted) !important;
}}

[data-testid="stMetricValue"] {{
  padding: 0 !important;
  margin: 0 !important;
  line-height: 1.15 !important;
  color: var(--text) !important;
}}

[data-testid="stMetricValue"] div {{
  padding: 0 !important;
  margin: 0 !important;
  color: var(--text) !important;
}}

div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div[data-testid="column"] {{
  align-self: stretch;
}}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot),
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) {{
  gap: 0.75rem !important;
}}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) > div[data-testid="column"] {{
  flex: 1 1 0 !important;
  width: auto !important;
  min-width: 0 !important;
  align-self: auto !important;
}}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot) .stButton > button,
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) .stButton > button {{
  width: 100% !important;
  white-space: nowrap !important;
  font-size: 1.05rem !important;
  min-height: 3rem !important;
  padding: 0.75rem 1rem !important;
  letter-spacing: 0.02em !important;
}}

[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
textarea {{
  background: var(--input-bg) !important;
  color: var(--text) !important;
  border: 1px solid rgba(72, 118, 178, 0.35) !important;
}}

.stTextInput input, .stTextArea textarea {{
  color: var(--text) !important;
}}

.stButton > button {{
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: var(--on-accent);
  border: none;
  border-radius: 10px;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(61, 126, 232, 0.28);
}}

.stButton > button[kind="primary"] {{
  padding: 0.95rem 2.3rem !important;
  min-height: 3.25rem;
  font-size: 1.36rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  border-radius: 12px;
}}

.stButton > button:hover {{
  filter: brightness(1.06);
}}

.stButton > button[kind="secondary"] {{
  background: rgba(255, 255, 255, 0.75) !important;
  color: var(--muted) !important;
  border: 1px solid rgba(72, 118, 178, 0.35) !important;
  box-shadow: none !important;
}}

.stButton > button[kind="secondary"]:hover:not(:disabled) {{
  background: rgba(255, 255, 255, 0.92) !important;
  color: var(--text-soft) !important;
}}

.stButton > button:disabled {{
  opacity: 0.55 !important;
  cursor: not-allowed !important;
}}

.stTabs [data-baseweb="tab-list"] {{
  gap: 0.55rem;
}}

.stTabs [data-baseweb="tab"] {{
  position: relative;
  height: 3rem;
  padding: 0.5rem 1.2rem;
  font-size: 1.2rem;
  color: var(--text-soft) !important;
  border: 1.4px solid rgba(72, 118, 178, 0.28);
  border-radius: 10px 10px 0 0;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.55);
}}

.stTabs [data-baseweb="tab"]:hover {{
  background: rgba(255, 255, 255, 0.82);
}}

.stTabs [aria-selected="true"] {{
  color: var(--text) !important;
  border-bottom: none !important;
  background: rgba(255, 255, 255, 0.9);
}}

.stTabs [aria-selected="true"]::after {{
  content: "";
  position: absolute;
  left: -1.4px;
  right: -1.4px;
  bottom: -1.4px;
  height: 4px;
  background-color: var(--accent);
  border-radius: 0 0 8px 8px;
  pointer-events: none;
}}

.stTabs [data-baseweb="tab-highlight"] {{
  display: none !important;
}}

.stTabs [data-baseweb="tab-border"] {{
  display: none !important;
}}

[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child {{
  background: var(--input-bg) !important;
  border-color: rgba(72, 118, 178, 0.45) !important;
}}

[data-testid="stCheckbox"] label[data-baseweb="checkbox"][aria-checked="true"] > div:first-child {{
  background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
  border-color: var(--accent) !important;
}}

[data-testid="stCheckbox"] svg {{
  fill: var(--on-accent) !important;
}}

[data-testid="stTooltipIcon"] {{
  background: rgba(255, 255, 255, 0.9) !important;
  border: 1.5px solid rgba(72, 118, 178, 0.35) !important;
  border-radius: 50% !important;
  width: 1.15rem !important;
  height: 1.15rem !important;
  min-width: 1.15rem !important;
  min-height: 1.15rem !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: none !important;
}}

[data-testid="stTooltipIcon"] svg {{
  display: none !important;
}}

[data-testid="stTooltipIcon"]::after {{
  content: "?";
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1;
  font-family: Georgia, "Times New Roman", serif;
}}

.birds-header {{
  margin: 0 0 0.85rem 0;
}}

.birds-header-inner {{
  display: inline-flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: flex-start;
  gap: 0.2rem 0.45rem;
  max-width: 100%;
}}

.birds-title {{
  margin: 0 !important;
  padding: 0 !important;
  font-size: 3.35rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.04em;
  color: #0f2744 !important;
  line-height: 1.05 !important;
  white-space: nowrap;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.65);
}}

.birds-subtitle {{
  margin: 0 0 0.18rem 0 !important;
  padding: 0 !important;
  font-size: 1.65rem !important;
  font-weight: 400 !important;
  line-height: 1.2 !important;
  color: #3d5270 !important;
  text-align: left;
  white-space: nowrap;
}}

.stCaption, .stMarkdown small {{
  color: var(--muted) !important;
}}

[data-testid="stMarkdownContainer"] code {{
  color: #1e3a5f;
  background: rgba(255, 255, 255, 0.75);
}}
</style>
        """,
        unsafe_allow_html=True,
    )
