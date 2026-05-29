"""Shared Streamlit theme: dark starry gradient background."""

from __future__ import annotations

import streamlit as st


def apply_starry_theme() -> None:
    st.markdown(
        """
<style>
:root {
  --bg-start: #11284f;
  --bg-mid: #27456f;
  --bg-end: #344f79;
  --card: rgba(24, 44, 96, 0.68);
  --card-border: rgba(148, 184, 255, 0.35);
  --text: #e8eeff;
  --muted: #b8c8f0;
  --accent: #6ea6ff;
  --accent-2: #8a7bff;
  --primary-color: #9ad8ff;
}

.stApp {
  color: var(--text);
  background:
    radial-gradient(ellipse 58% 42% at -4% 104%, rgba(222, 239, 255, 0.52), transparent 66%),
    radial-gradient(ellipse 65% 48% at 12% 88%, rgba(173, 208, 245, 0.26), transparent 72%),
    radial-gradient(ellipse 92% 70% at 50% -18%, rgba(104, 148, 210, 0.17), transparent 74%),
    radial-gradient(1.7px 1.7px at 9% 17%, rgba(255,255,255,0.72), transparent 62%),
    radial-gradient(1.4px 1.4px at 21% 35%, rgba(236,245,255,0.62), transparent 62%),
    radial-gradient(1.6px 1.6px at 33% 13%, rgba(241,248,255,0.66), transparent 62%),
    radial-gradient(1.3px 1.3px at 48% 28%, rgba(232,242,255,0.58), transparent 62%),
    radial-gradient(1.5px 1.5px at 62% 18%, rgba(244,250,255,0.64), transparent 62%),
    radial-gradient(1.3px 1.3px at 79% 30%, rgba(230,242,255,0.56), transparent 62%),
    radial-gradient(1.4px 1.4px at 87% 14%, rgba(250,252,255,0.67), transparent 62%),
    radial-gradient(1.2px 1.2px at 74% 58%, rgba(233,244,255,0.48), transparent 62%),
    radial-gradient(1.1px 1.1px at 56% 72%, rgba(224,238,255,0.42), transparent 62%),
    radial-gradient(1.1px 1.1px at 41% 60%, rgba(236,246,255,0.44), transparent 62%),
    linear-gradient(166deg, var(--bg-start) 0%, var(--bg-mid) 54%, var(--bg-end) 100%);
  background-attachment: fixed;
}

[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main > div {
  background: transparent;
}

h1, h2, h3, h4, h5, h6, p, label, span, li, div {
  color: var(--text);
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(14, 32, 72, 0.92) 0%, rgba(18, 42, 88, 0.88) 100%);
  border-right: 1px solid rgba(148, 184, 255, 0.28);
}

[data-testid="stForm"], .stAlert, [data-testid="stExpander"] {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
}

[data-testid="stDataFrame"],
.stDataFrame {
  background: rgba(18, 36, 78, 0.55) !important;
  border: 1.5px solid rgba(154, 216, 255, 0.58) !important;
  border-radius: 12px !important;
  padding: 0.4rem !important;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(48, 82, 160, 0.22);
}

[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
[data-testid="stDataFrame"] [data-testid="glideDataEditor"] {
  border-radius: 8px;
}

[data-testid="stImage"] {
  background: rgba(18, 36, 78, 0.45);
  border: 1.5px solid rgba(154, 216, 255, 0.58) !important;
  border-radius: 12px;
  padding: 0.55rem;
  box-sizing: border-box;
  box-shadow: 0 4px 16px rgba(48, 82, 160, 0.2);
}

[data-testid="stImage"] img {
  border-radius: 8px;
  border: 1px solid rgba(154, 216, 255, 0.38);
  display: block;
  width: 100%;
}

.plot-explanation-card {
  background: rgba(18, 36, 78, 0.55);
  border: 1.5px solid rgba(154, 216, 255, 0.5);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin: 0.5rem 0 0.85rem 0;
  color: #d8e4ff !important;
  font-size: 0.95rem;
  line-height: 1.55;
}

.plot-explanation-card strong {
  color: #eef4ff !important;
}

.physical-conditions-card {
  background: rgba(18, 36, 78, 0.55);
  border: 1.5px solid rgba(154, 216, 255, 0.45);
  border-radius: 10px;
  padding: 0.85rem 1.1rem 0.95rem 1rem;
  margin: 0.35rem 0 1rem 0;
}

.physical-conditions-list {
  list-style-type: disc;
  margin: 0;
  padding: 0 0 0 1.35rem;
  color: #d8e4ff;
  font-size: 0.94rem;
  line-height: 1.5;
}

.physical-conditions-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.35rem 1rem;
  margin-bottom: 0.65rem;
  padding-left: 0.15rem;
}

.physical-conditions-list li:last-child {
  margin-bottom: 0;
}

.physical-conditions-list .pc-label {
  flex: 0 0 13.5rem;
  max-width: 100%;
  color: rgba(168, 198, 240, 0.82);
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.physical-conditions-list .pc-label::after {
  content: ":";
  margin-left: 0.12rem;
  color: rgba(154, 216, 255, 0.55);
  font-weight: 400;
  text-transform: none;
}

.physical-conditions-list .pc-value {
  flex: 1 1 12rem;
  min-width: 0;
  color: #f0f7ff;
  font-size: 0.96rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

[data-testid="stMetric"] {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  box-sizing: border-box;
  padding: 0.9rem 1.1rem 1rem !important;
  min-height: 5.6rem;
  overflow: visible;
}

[data-testid="stMetricLabel"] {
  padding: 0 !important;
  margin: 0 0 0.45rem 0 !important;
  line-height: 1.35 !important;
  white-space: normal;
}

[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div {
  padding: 0 !important;
  margin: 0 !important;
}

[data-testid="stMetricValue"] {
  padding: 0 !important;
  margin: 0 !important;
  line-height: 1.15 !important;
}

[data-testid="stMetricValue"] div {
  padding: 0 !important;
  margin: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div[data-testid="column"] {
  align-self: stretch;
}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot),
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) {
  gap: 0.75rem !important;
}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) > div[data-testid="column"] {
  flex: 1 1 0 !important;
  width: auto !important;
  min-width: 0 !important;
  align-self: auto !important;
}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot) .stButton > button,
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) .stButton > button {
  width: 100% !important;
  white-space: nowrap !important;
  font-size: 1.05rem !important;
  min-height: 3rem !important;
  padding: 0.75rem 1rem !important;
  letter-spacing: 0.02em !important;
}

[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
textarea {
  background: rgba(34, 56, 112, 0.88) !important;
  color: var(--text) !important;
  border: 1px solid rgba(156, 186, 255, 0.6) !important;
}

.stTextInput input, .stTextArea textarea {
  color: var(--text) !important;
}

.stButton > button {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #f8fbff;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(85, 118, 214, 0.32);
}

.stButton > button[kind="primary"] {
  padding: 0.95rem 2.3rem !important;
  min-height: 3.25rem;
  font-size: 1.36rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  border-radius: 12px;
}

.stButton > button:hover {
  filter: brightness(1.08);
}

.stButton > button[kind="secondary"] {
  background: rgba(72, 92, 132, 0.55) !important;
  color: #b8c8f0 !important;
  border: 1px solid rgba(140, 165, 210, 0.45) !important;
  box-shadow: none !important;
}

.stButton > button[kind="secondary"]:hover:not(:disabled) {
  filter: brightness(1.06);
}

.stButton > button:disabled {
  opacity: 0.55 !important;
  cursor: not-allowed !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.55rem;
}

.stTabs [data-baseweb="tab"] {
  position: relative;
  height: 3rem;
  padding: 0.5rem 1.2rem;
  font-size: 1.2rem;
  border: 1.4px solid rgba(156, 200, 255, 0.6);
  border-radius: 10px 10px 0 0;
  box-sizing: border-box;
}

.stTabs [data-baseweb="tab"]:hover {
  background: rgba(45, 74, 148, 0.5);
}

.stTabs [aria-selected="true"] {
  border-bottom: none !important;
  background: rgba(45, 74, 148, 0.55);
}

.stTabs [aria-selected="true"]::after {
  content: "";
  position: absolute;
  left: -1.4px;
  right: -1.4px;
  bottom: -1.4px;
  height: 4px;
  background-color: #9ad8ff;
  border-radius: 0 0 8px 8px;
  pointer-events: none;
}

.stTabs [data-baseweb="tab-highlight"] {
  display: none !important;
}

.stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child {
  background: rgba(34, 56, 112, 0.65) !important;
  border-color: rgba(154, 216, 255, 0.85) !important;
}

[data-testid="stCheckbox"] label[data-baseweb="checkbox"][aria-checked="true"] > div:first-child {
  background: linear-gradient(135deg, #5b9aff, #7a8dff) !important;
  border-color: #9ad8ff !important;
}

[data-testid="stCheckbox"] svg {
  fill: #f8fbff !important;
}

[data-testid="stTooltipIcon"] {
  background: rgba(28, 48, 92, 0.85) !important;
  border: 1.5px solid rgba(154, 180, 220, 0.55) !important;
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
}

[data-testid="stTooltipIcon"] svg {
  display: none !important;
}

[data-testid="stTooltipIcon"]::after {
  content: "?";
  color: #9aa8c8;
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1;
  font-family: Georgia, "Times New Roman", serif;
}

.birds-header {
  margin: 0 0 0.85rem 0;
}

.birds-header-inner {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: flex-start;
  gap: 0.2rem 0.45rem;
  max-width: 100%;
}

.birds-title {
  margin: 0 !important;
  padding: 0 !important;
  font-size: 3.35rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.04em;
  color: #eef4ff !important;
  line-height: 1.05 !important;
  white-space: nowrap;
}

.birds-subtitle {
  margin: 0 0 0.18rem 0 !important;
  padding: 0 !important;
  font-size: 1.65rem !important;
  font-weight: 400 !important;
  line-height: 1.2 !important;
  color: #b8c8f0 !important;
  text-align: left;
  white-space: nowrap;
}

.stCaption, .stMarkdown small {
  color: var(--muted) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )
