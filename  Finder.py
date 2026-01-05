import streamlit as st
import pandas as pd
from thefuzz import fuzz
from itertools import combinations

st.set_page_config(page_title="Company Name Duplicate Finder", layout="wide")

st.title("🔍 Company Name Duplicate Finder")
st.markdown("Upload a CSV file to identify potential duplicate company names using fuzzy matching")

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

# Similarity threshold slider
threshold = st.slider("Similarity Threshold (%)", min_value=50, max_value=100, value=80, step=5)
st.caption(f"Only pairs with similarity ≥ {threshold}% will be shown")

if uploaded_file is not None:
    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)
        
        # Check if 'Company Name' column exists
        if 'Company Name' not in df.columns:
            st.error("❌ CSV must contain a column named 'Company Name'")
            st.info(f"Available columns: {', '.join(df.columns)}")
        else:
            st.success(f"✅ Loaded {len(df)} companies")
            
            # Show preview
            with st.expander("Preview Data"):
                st.dataframe(df.head(10))
            
            # Extract company names and remove nulls
            company_names = df['Company Name'].dropna().unique()
            st.info(f"Found {len(company_names)} unique company names (after removing nulls)")
            
            # Find duplicates
            with st.spinner("Finding duplicates..."):
                duplicates = []
                
                # Compare all pairs
                for name1, name2 in combinations(company_names, 2):
                    similarity = fuzz.ratio(str(name1), str(name2))
                    if similarity >= threshold:
                        duplicates.append({
                            'Company Name 1': name1,
                            'Company Name 2': name2,
                            'Similarity Score': similarity
                        })
                
                # Create results dataframe
                if duplicates:
                    results_df = pd.DataFrame(duplicates)
                    results_df = results_df.sort_values('Similarity Score', ascending=False).reset_index(drop=True)
                    
                    st.success(f"🎯 Found {len(results_df)} potential duplicate pairs")
                    
                    # Display results
                    st.subheader("Potential Duplicates")
                    
                    # Color code by similarity
                    def highlight_similarity(val):
                        if val >= 95:
                            color = '#ff4b4b'  # Red for very high similarity
                        elif val >= 85:
                            color = '#ffa500'  # Orange for high similarity
                        else:
                            color = '#ffd700'  # Yellow for moderate similarity
                        return f'background-color: {color}; color: white; font-weight: bold'
                    
                    styled_df = results_df.style.applymap(
                        highlight_similarity, 
                        subset=['Similarity Score']
                    )
                    
                    st.dataframe(styled_df, use_container_width=True, height=400)
                    
                    # Download results
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv,
                        file_name="duplicate_companies.csv",
                        mime="text/csv"
                    )
                    
                    # Statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Pairs Found", len(results_df))
                    with col2:
                        st.metric("Avg Similarity", f"{results_df['Similarity Score'].mean():.1f}%")
                    with col3:
                        high_confidence = len(results_df[results_df['Similarity Score'] >= 95])
                        st.metric("High Confidence (≥95%)", high_confidence)
                    
                else:
                    st.warning(f"No duplicates found with similarity ≥ {threshold}%")
                    st.info("Try lowering the similarity threshold to find more potential matches")
    
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
else:
    st.info("👆 Please upload a CSV file to get started")
    




    
