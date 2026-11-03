"""Streamlit interface for the fuzzy duplicate finder.

Run:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from dedup import cluster, find_duplicate_pairs

st.set_page_config(page_title="Company Name Duplicate Finder", layout="wide")
st.title("Company Name Duplicate Finder")
st.markdown("Upload a CSV to flag near-duplicate names (typos, abbreviations, reordered words).")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
threshold = st.slider("Similarity threshold", min_value=50, max_value=100, value=90, step=1)
st.caption(f"Pairs scoring at least {threshold} out of 100 are shown. "
           "Lower values catch more variants but add false positives.")

if uploaded_file is None:
    st.info("Upload a CSV to get started, or try data/sample_companies.csv from this repo.")
    st.stop()

try:
    df = pd.read_csv(uploaded_file)
except Exception as e:  # malformed upload
    st.error(f"Could not read the file: {e}")
    st.stop()

default_col = list(df.columns).index("Company Name") if "Company Name" in df.columns else 0
column = st.selectbox("Column to deduplicate", df.columns, index=default_col)

with st.expander("Preview data"):
    st.dataframe(df.head(10))

names = df[column].tolist()
with st.spinner("Scoring candidate pairs..."):
    pairs = find_duplicate_pairs(names, threshold)
    clusters = cluster(names, pairs)

multi = clusters[clusters.cluster_size > 1]
c1, c2, c3 = st.columns(3)
c1.metric("Unique names", len(clusters))
c2.metric("Matched pairs", len(pairs))
c3.metric("Duplicate clusters", multi.cluster_id.nunique())

if pairs.empty:
    st.warning("No pairs at this threshold. Try lowering it.")
    st.stop()

st.subheader("Matched pairs")
st.dataframe(pairs, use_container_width=True, height=360)
st.download_button("Download pairs as CSV", pairs.to_csv(index=False),
                   file_name="duplicate_pairs.csv", mime="text/csv")

st.subheader("Clusters with suggested canonical name")
st.dataframe(multi.sort_values(["cluster_id", "name"]), use_container_width=True, height=360)

mapping = clusters.set_index("name")["canonical_name"]
cleaned = df.assign(canonical_name=df[column].astype(str).map(mapping))
st.download_button("Download original data with canonical_name column", cleaned.to_csv(index=False),
                   file_name="deduplicated.csv", mime="text/csv")
