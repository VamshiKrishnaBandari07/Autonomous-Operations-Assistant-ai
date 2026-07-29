"""Shared Streamlit styling for OpsFlow AI."""

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', sans-serif;
}

.block-container {
  padding-top: 1.5rem;
  padding-bottom: 2rem;
  max-width: 1200px;
}

h1, h2, h3 {
  font-family: 'DM Sans', sans-serif !important;
  letter-spacing: -0.02em;
}

div[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0B1F33 0%, #12324F 55%, #0E2740 100%);
}

div[data-testid="stSidebar"] * {
  color: #E8F1F8 !important;
}

.ops-hero {
  background: linear-gradient(135deg, #0B1F33 0%, #1A4A6E 45%, #2A6F8F 100%);
  border-radius: 18px;
  padding: 1.6rem 1.8rem;
  color: #F4FAFF;
  margin-bottom: 1.2rem;
  box-shadow: 0 10px 30px rgba(11, 31, 51, 0.25);
}

.ops-hero h1 {
  margin: 0;
  font-size: 1.9rem;
  color: #FFFFFF !important;
}

.ops-hero p {
  margin: 0.45rem 0 0 0;
  opacity: 0.9;
  font-size: 0.98rem;
}

.metric-card {
  background: #F7FBFE;
  border: 1px solid #D5E6F2;
  border-radius: 14px;
  padding: 1rem 1.1rem;
}

.citation {
  background: #F3F8FC;
  border-left: 3px solid #2A6F8F;
  padding: 0.65rem 0.85rem;
  margin: 0.4rem 0;
  border-radius: 0 8px 8px 0;
  font-size: 0.9rem;
}

.confidence-pill {
  display: inline-block;
  background: #E4F4EC;
  color: #1E6B45;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
}

.demo-banner {
  background: linear-gradient(90deg, #FFF6E5, #F3F8FC);
  border: 1px solid #E6D5B8;
  color: #5C4A28;
  padding: 0.65rem 0.9rem;
  border-radius: 10px;
  margin-bottom: 0.9rem;
  font-size: 0.9rem;
  font-weight: 600;
}

.ops-hero.landing h1 {
  font-size: 2.6rem;
  line-height: 1.05;
}

.ops-hero.landing h2 {
  margin: 0.35rem 0 0.6rem 0;
  font-size: 1.25rem;
  font-weight: 500;
  color: #D7EAF5 !important;
}

.ops-hero.landing .eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  opacity: 0.8;
  margin: 0;
}

.ops-hero.landing .lead {
  max-width: 46rem;
  font-size: 1.05rem;
}
</style>
"""


def inject_styles() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="ops-hero">
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
