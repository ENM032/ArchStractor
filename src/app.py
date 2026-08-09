import os
import sys
import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import math
from typing import List, Tuple

# Set up page configurations
st.set_page_config(
    page_title="ArcStractor SA Lottery Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .reportview-container {
        background: #f0f2f6
    }
    .metric-card {
        padding: 15px;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #1f77b4;
    }
    .metric-pass {
        border-left: 5px solid #2ca02c;
    }
    .metric-fail {
        border-left: 5px solid #d62728;
    }
    </style>
""", unsafe_allow_html=True)

# Cache data loading
@st.cache_data
def load_game_data(filepath: str) -> pd.DataFrame:
    """Loads cleaned CSV dataset and parses date fields."""
    if not os.path.exists(filepath):
        return pd.DataFrame()
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df

# Helper runs test calculation
def calculate_runs_test(sequence: List[int]) -> Tuple[int, float, float]:
    """Wald-Wolfowitz Runs Test for sequence independence."""
    if len(sequence) < 2:
        return 0, 0.0, 1.0
    sorted_seq = sorted(sequence)
    median_val = sorted_seq[len(sorted_seq) // 2]
    
    binary_seq = [1 if x > median_val else 0 for x in sequence]
    n1 = sum(binary_seq)
    n2 = len(binary_seq) - n1
    
    if n1 == 0 or n2 == 0:
        return 1, 0.0, 1.0
        
    runs = 1
    for i in range(1, len(binary_seq)):
        if binary_seq[i] != binary_seq[i-1]:
            runs += 1
            
    expected_runs = (2.0 * n1 * n2) / (n1 + n2) + 1.0
    variance = (2.0 * n1 * n2 * (2.0 * n1 * n2 - n1 - n2)) / (((n1 + n2) ** 2) * (n1 + n2 - 1))
    
    if variance == 0:
        return runs, 0.0, 1.0
        
    z_stat = (runs - expected_runs) / math.sqrt(variance)
    p_val = stats.norm.sf(abs(z_stat)) * 2.0
    
    return runs, z_stat, p_val

# Helper Chi-Square Uniformity calculation
def calculate_uniformity_test(numbers: List[int], max_val: int) -> Tuple[float, float]:
    num_bins = max_val
    observed = [0] * num_bins
    for num in numbers:
        if 1 <= num <= max_val:
            observed[num - 1] += 1
    expected = [len(numbers) / num_bins] * num_bins
    chi2, p_val = stats.chisquare(f_obs=observed, f_exp=expected)
    return chi2, p_val

# Helper Parity Binomial calculation
def calculate_parity_test(odd_counts: List[int], num_main: int) -> Tuple[float, float, List[int], List[float]]:
    total = len(odd_counts)
    observed = [0] * (num_main + 1)
    for k in odd_counts:
        if 0 <= k <= num_main:
            observed[k] += 1
    expected = []
    for k in range(num_main + 1):
        pmf_val = stats.binom.pmf(k, num_main, 0.5)
        expected.append(total * pmf_val)
    chi2, p_val = stats.chisquare(f_obs=observed, f_exp=expected)
    return chi2, p_val, observed, expected

def main():
    st.title("📊 SA National Lottery Data Analytics Dashboard")
    st.markdown("Interactive analysis of historical results, statistical checks, and ML feature distributions.")
    st.markdown("---")
    
    # Sidebar Configuration
    st.sidebar.header("🔧 Configuration Preset")
    game_preset = st.sidebar.selectbox(
        "Select Game Preset:",
        ["PowerBall", "PowerBall Xtra", "Lotto"]
    )
    
    # Map presets to clean files
    cleaned_dir = "data/cleaned"
    if game_preset == "PowerBall":
        filepath = os.path.join(cleaned_dir, "powerball_clean.csv")
    elif game_preset == "PowerBall Xtra":
        filepath = os.path.join(cleaned_dir, "powerball_xtra_clean.csv")
    else:
        filepath = os.path.join(cleaned_dir, "lotto_clean.csv")
        
    # Load dataset
    df = load_game_data(filepath)
    if df.empty:
        st.error(f"Cleaned dataset for {game_preset} not found. Please run the preparation pipeline first: `python src/prepare.py`")
        return
        
    # Extract years and show timeline range slider
    min_year = int(df['year'].min())
    max_year = int(df['year'].max())
    
    st.sidebar.markdown("### 📅 Date Filters")
    year_range = st.sidebar.slider(
        "Select Year Range:",
        min_year, max_year, (min_year, max_year)
    )
    
    # Filter dataset
    df_filtered = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
    total_draws = len(df_filtered)
    
    if total_draws == 0:
        st.warning("No draws found in the selected year range. Please widen your filter.")
        return
        
    # Inferred parameters
    ball_cols = [c for c in df_filtered.columns if c.startswith("ball_")]
    num_main = len(ball_cols)
    all_balls = df_filtered[ball_cols].values.flatten()
    max_ball_val = int(np.max(all_balls))
    
    # Global metrics display
    st.sidebar.markdown("### 📈 Dataset Statistics")
    st.sidebar.metric("Total Draws in Filter", f"{total_draws}")
    st.sidebar.metric("Time Span", f"{year_range[0]} - {year_range[1]}")
    st.sidebar.metric("Main Ball Schema Range", f"1 - {max_ball_val}")
    
    # Setup tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎱 Number Frequencies & Highlights",
        "🧮 Live Randomness Tests",
        "⚖️ Parity (Odd/Even splits)",
        "🔍 History Search Table"
    ])
    
    # ==================== TAB 1: FREQUENCIES ====================
    with tab1:
        st.header("🎱 Number Frequency Distribution")
        st.markdown("Highlights standard frequency counts. The **Top 5 Hot Numbers** are highlighted in **red** and the **Bottom 5 Cold Numbers** in **yellow**.")
        
        freq_series = pd.Series(all_balls).value_counts().reindex(range(1, max_ball_val + 1), fill_value=0)
        sorted_freqs = freq_series.sort_values(ascending=False)
        
        # Plot frequency distribution
        try:
            fig_freq, ax_freq = plt.subplots(figsize=(12, 5))
            colors = ['#1f77b4' for _ in range(max_ball_val)]
            for idx, num in enumerate(freq_series.index):
                if num in sorted_freqs.head(5).index:
                    colors[idx] = '#d62728'
                elif num in sorted_freqs.tail(5).index:
                    colors[idx] = '#bcbd22'
                    
            ax_freq.bar(freq_series.index, freq_series.values, color=colors, edgecolor='black', alpha=0.8)
            ax_freq.axhline(y=len(all_balls)/max_ball_val, color='#2ca02c', linestyle='--', label=f'Expected Mean ({len(all_balls)/max_ball_val:.1f})')
            ax_freq.set_title(f"{game_preset} Draw Frequency Distribution")
            ax_freq.set_xlabel("Ball Number")
            ax_freq.set_ylabel("Occurrences")
            ax_freq.set_xticks(range(1, max_ball_val + 1, 2 if max_ball_val > 40 else 1))
            ax_freq.legend()
            st.pyplot(fig_freq)
        except Exception as e:
            st.error(f"Error rendering frequency distribution plot: {e}")
            plt.close()
        
        # Display Hot & Cold Metrics side-by-side
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🔥 Top 5 Hot Numbers")
                hot_df = pd.DataFrame({
                    "Number": sorted_freqs.head(5).index,
                    "Draws Count": sorted_freqs.head(5).values,
                    "Percentage (%)": [round((val / total_draws) * 100, 2) for val in sorted_freqs.head(5).values]
                })
                st.dataframe(hot_df, width="stretch")
                
            with col2:
                st.subheader("❄️ Bottom 5 Cold Numbers")
                cold_df = pd.DataFrame({
                    "Number": sorted_freqs.tail(5).index,
                    "Draws Count": sorted_freqs.tail(5).values,
                    "Percentage (%)": [round((val / total_draws) * 100, 2) for val in sorted_freqs.tail(5).values]
                })
                st.dataframe(cold_df, width="stretch")
        except Exception as e:
            st.error(f"Error listing hot and cold statistics: {e}")
            
    # ==================== TAB 2: LIVE STATS SUITE ====================
    with tab2:
        st.header("🧮 Live Randomness & Independence Tests")
        st.markdown("Run standard mathematical tests dynamically over the selected date range.")
        st.markdown("---")
        
        # Execute tests on filtered subset
        try:
            chi2_main, p_main = calculate_uniformity_test(all_balls, max_ball_val)
        except Exception as e:
            chi2_main, p_main = 0.0, 1.0
            st.warning(f"Could not calculate uniformity stats for main balls: {e}")
            
        try:
            chi2_pb, p_pb = calculate_uniformity_test(df_filtered['powerball'].values, int(df_filtered['powerball'].max()))
        except Exception as e:
            chi2_pb, p_pb = 0.0, 1.0
            st.warning(f"Could not calculate uniformity stats for PowerBall: {e}")
            
        try:
            runs_count, z_stat, p_runs = calculate_runs_test(df_filtered['sum_main_balls'].values)
        except Exception as e:
            runs_count, z_stat, p_runs = 0, 0.0, 1.0
            st.warning(f"Could not calculate runs test for draw sums: {e}")
        
        col1, col2, col3 = st.columns(3)
        
        # Card 1: Uniformity of Main Numbers
        with col1:
            status_cls = "metric-pass" if p_main >= 0.05 else "metric-fail"
            st.markdown(f"""
                <div class="metric-card {status_cls}">
                    <h4>1. Chi-Square Uniformity (Main Balls)</h4>
                    <p>Tests if ball numbers are drawn with equal frequencies.</p>
                    <h2>{"PASS" if p_main >= 0.05 else "FAIL"}</h2>
                    <p><b>p-value:</b> {p_main:.5f}</p>
                    <p><b>Interpretation:</b> {"Uniform occurrences" if p_main >= 0.05 else "Biased frequency counts"}</p>
                </div>
            """, unsafe_allow_html=True)
            
        # Card 2: Uniformity of PowerBall
        with col2:
            status_cls = "metric-pass" if p_pb >= 0.05 else "metric-fail"
            st.markdown(f"""
                <div class="metric-card {status_cls}">
                    <h4>2. Chi-Square Uniformity (PowerBall)</h4>
                    <p>Tests if PowerBall values are drawn uniformly.</p>
                    <h2>{"PASS" if p_pb >= 0.05 else "FAIL"}</h2>
                    <p><b>p-value:</b> {p_pb:.5f}</p>
                    <p><b>Interpretation:</b> {"Uniform occurrences" if p_pb >= 0.05 else "Biased frequency counts"}</p>
                </div>
            """, unsafe_allow_html=True)
            
        # Card 3: Independence check
        with col3:
            status_cls = "metric-pass" if p_runs >= 0.05 else "metric-fail"
            st.markdown(f"""
                <div class="metric-card {status_cls}">
                    <h4>3. WW Runs Test (Draw Sums)</h4>
                    <p>Tests if consecutive draw results are independent over time.</p>
                    <h2>{"PASS" if p_runs >= 0.05 else "FAIL"}</h2>
                    <p><b>p-value:</b> {p_runs:.5f}</p>
                    <p><b>Interpretation:</b> {"Draws are independent" if p_runs >= 0.05 else "Draw sums are dependent (pattern detected)"}</p>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("### 📊 Draw Sum Normality Trend")
        # Histogram of draw sums
        try:
            fig_sums, ax_sums = plt.subplots(figsize=(8, 4))
            sns.histplot(df_filtered['sum_main_balls'], kde=True, color='#9467bd', stat="density", bins=20, ax=ax_sums)
            mu_sum = np.mean(df_filtered['sum_main_balls'])
            sigma_sum = np.std(df_filtered['sum_main_balls'])
            x_range = np.linspace(df_filtered['sum_main_balls'].min(), df_filtered['sum_main_balls'].max(), 200)
            ax_sums.plot(x_range, stats.norm.pdf(x_range, mu_sum, sigma_sum), color='#d62728', linewidth=2, label='Fitted Normal')
            ax_sums.set_title(f"Distribution of Draw Sums (Mean={mu_sum:.1f}, Std={sigma_sum:.1f})")
            ax_sums.legend()
            st.pyplot(fig_sums)
        except Exception as e:
            st.error(f"Error rendering draw sum normality trend: {e}")
            plt.close()
        
    # ==================== TAB 3: PARITY SPLITS ====================
    with tab3:
        st.header("⚖️ Parity Distributions (Odd vs. Even)")
        st.markdown(f"Evaluates if odd/even ball ratios match binomial expectations $B({num_main}, 0.5)$.")
        
        try:
            chi2_parity, p_parity, obs, exp = calculate_parity_test(df_filtered['odd_count'].values, num_main)
            
            fig_parity, ax_parity = plt.subplots(figsize=(8, 4.5))
            x = np.arange(num_main + 1)
            width = 0.35
            
            ax_parity.bar(x - width/2, obs, width, label='Observed Counts', color='#2ca02c', alpha=0.8)
            ax_parity.bar(x + width/2, exp, width, label='Binomial Projection', color='#ff7f0e', alpha=0.8)
            ax_parity.set_title("Odd Balls Counts per Draw vs. Binomial Projections")
            ax_parity.set_xlabel("Number of Odd Balls")
            ax_parity.set_ylabel("Occurrences")
            ax_parity.set_xticks(x)
            ax_parity.legend()
            st.pyplot(fig_parity)
            
            st.subheader("📊 Observed Parity Counts Table")
            parity_df = pd.DataFrame({
                "Odd Balls Count": [f"{i} Odd / {num_main - i} Even" for i in range(num_main + 1)],
                "Observed Draws": obs,
                "Expected Draws": [round(val, 1) for val in exp],
                "Percentage (%)": [round((val / total_draws) * 100, 2) for val in obs]
            })
            st.dataframe(parity_df, width="stretch")
        except Exception as e:
            st.error(f"Error calculating or rendering parity distributions: {e}")
            plt.close()
        
    # ==================== TAB 4: HISTORY SEARCH ====================
    with tab4:
        st.header("🔍 Historical Draws Database Search")
        st.markdown("Search past draw records, winning numbers, and generated features.")
        
        # User search queries
        search_query = st.text_input("Filter by date (YYYY-MM-DD) or search draws details:")
        
        try:
            history_df = df_filtered.copy()
            
            # Format draw numbers column for easy reading
            history_df['winning_numbers'] = history_df[ball_cols].values.tolist()
            history_df['winning_numbers'] = history_df['winning_numbers'].apply(lambda lst: ", ".join(map(str, lst)))
            
            display_cols = ["day", "date", "winning_numbers", "powerball", "sum_main_balls", "odd_count", "even_count"]
            
            if search_query:
                # Query match
                mask_date = history_df['date'].astype(str).str.contains(search_query)
                mask_num = history_df['winning_numbers'].str.contains(search_query)
                history_df = history_df[mask_date | mask_num]
                
            st.dataframe(history_df[display_cols], width="stretch")
        except Exception as e:
            st.error(f"Error displaying historical database search: {e}")

if __name__ == "__main__":
    main()
