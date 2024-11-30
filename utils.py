from enum import Enum
import streamlit as st
from pathlib import Path

ROOT_DIR = Path(__file__).parent

def load_styles():
    with open(ROOT_DIR / 'static/style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    with open(ROOT_DIR / f'static/library_styles.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


#ENUMS
class AllureLaunches(Enum):
    #   MustPass      = "CI_Sanity-ppr"
    #   PreMustPass   = "PPR_PRE_MP-ppr"
    #   DailyRun      = "CI_Sanity_daily_run-ppr"
      PrBuild       = "CI_SFA-ppr"