import os
import sys
import json
import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import math
from typing import List, Tuple
from stats_tests import run_wald_wolfowitz_runs_test, run_uniformity_test, run_parity_binomial_test
from user_db import save_user_guess, get_user_history, clear_user_history, create_user, authenticate_user

# Set up page configurations
st.set_page_config(
    page_title="ArcStractor SA Lottery Dashboard",
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
        color: #111111;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #1f77b4;
    }
    .metric-card h2, .metric-card h4, .metric-card p {
        color: #111111 !important;
    }
    .metric-pass {
        border-left: 5px solid #2ca02c;
    }
    .metric-fail {
        border-left: 5px solid #d62728;
    }
    @media (max-width: 768px) {
        .metric-card {
            padding: 10px;
            margin-bottom: 10px;
        }
        .metric-card h4 {
            font-size: 0.95rem !important;
        }
        .metric-card h2 {
            font-size: 1.3rem !important;
        }
        .metric-card p {
            font-size: 0.8rem !important;
        }
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
@st.cache_data
def calculate_runs_test(sequence: Tuple[int, ...]) -> Tuple[int, float, float]:
    """Wald-Wolfowitz Runs Test for sequence independence (delegated)."""
    return run_wald_wolfowitz_runs_test(list(sequence))

# Helper Chi-Square Uniformity calculation
@st.cache_data
def calculate_uniformity_test(numbers: Tuple[int, ...], max_val: int) -> Tuple[float, float]:
    """Chi-Square Goodness-of-Fit uniformity test (delegated)."""
    return run_uniformity_test(list(numbers), 1, max_val)

# Helper Parity Binomial calculation
@st.cache_data
def calculate_parity_test(odd_counts: Tuple[int, ...], num_main: int) -> Tuple[float, float, List[int], List[float]]:
    """Chi-Square Parity Binomial distribution test (delegated)."""
    return run_parity_binomial_test(list(odd_counts), num_main)

SESSION_FILE = "data/.session.json"

def load_session_user() -> str:
    """Reads the saved login session, returning the username or 'Guest'."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("username", "Guest")
        except Exception:
            pass
    return "Guest"

def save_session_user(username: str):
    """Saves the login session to a local JSON file."""
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({"username": username}, f)
    except Exception:
        pass

def clear_session_user():
    """Removes the login session file."""
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass

def main():
    # Initialize session username if not present
    if "username" not in st.session_state:
        st.session_state["username"] = load_session_user()
        
    st.title("SA National Lottery Data Analytics Dashboard")
    st.markdown("Interactive analysis of historical results, statistical checks, and ML feature distributions.")
    st.markdown("---")
    
    # Sidebar Configuration
    st.sidebar.markdown("### 👤 User Profile")
    current_user = st.session_state["username"]
    
    if current_user != "Guest":
        st.sidebar.write(f"Logged in as: **{current_user}**")
        if st.sidebar.button("Log Out"):
            clear_session_user()
            st.session_state["username"] = "Guest"
            if "analyzed_guess" in st.session_state:
                del st.session_state["analyzed_guess"]
            st.success("Logged out successfully!")
            st.rerun()
    else:
        auth_mode = st.sidebar.radio("Profile Account:", ["Login", "Register"], label_visibility="collapsed")
        
        username_input = st.sidebar.text_input("Username:", key="auth_username").strip()
        password_input = st.sidebar.text_input("Password:", type="password", key="auth_password")
        
        if auth_mode == "Login":
            if st.sidebar.button("Login"):
                if authenticate_user(username_input, password_input):
                    save_session_user(username_input)
                    st.session_state["username"] = username_input
                    if "analyzed_guess" in st.session_state:
                        del st.session_state["analyzed_guess"]
                    st.sidebar.success(f"Welcome back, {username_input}!")
                    st.rerun()
                else:
                    st.sidebar.error("Invalid username or password.")
        else:
            if st.sidebar.button("Register"):
                if not username_input or not password_input:
                    st.sidebar.error("Please fill in all fields.")
                else:
                    success, msg = create_user(username_input, password_input)
                    if success:
                        save_session_user(username_input)
                        st.session_state["username"] = username_input
                        if "analyzed_guess" in st.session_state:
                            del st.session_state["analyzed_guess"]
                        st.sidebar.success(f"Account created! Welcome, {username_input}!")
                        st.rerun()
                    else:
                        st.sidebar.error(msg)
                        
    st.sidebar.markdown("---")
    st.sidebar.header("Configuration Preset")
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
    
    st.sidebar.markdown("### Date Filters")
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
    
    st.sidebar.markdown("### Dataset Statistics")
    st.sidebar.metric("Total Draws in Filter", f"{total_draws}")
    st.sidebar.metric("Time Span", f"{year_range[0]} - {year_range[1]}")
    st.sidebar.metric("Main Ball Schema Range", f"1 - {max_ball_val}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Admin Controls")
    if st.sidebar.button("Shutdown Dashboard", help="Terminates the Streamlit web server process"):
        st.sidebar.success("Dashboard server shutting down... You can now close this tab.")
        import time
        import signal
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)
        
    
    # Setup tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Number Frequencies & Highlights",
        "Live Randomness Tests",
        "Parity (Odd/Even splits)",
        "History Search Table",
        "Guess Analyzer & Play Simulator"
    ])
    
    # ==================== TAB 1: FREQUENCIES ====================
    with tab1:
        st.header("Number Frequency Distribution")
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
            st.pyplot(fig_freq, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering frequency distribution plot: {e}")
            plt.close()
        
        # Display Hot & Cold Metrics side-by-side
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Top 5 Hot Numbers")
                hot_df = pd.DataFrame({
                    "Number": sorted_freqs.head(5).index,
                    "Draws Count": sorted_freqs.head(5).values,
                    "Percentage (%)": [round((val / total_draws) * 100, 2) for val in sorted_freqs.head(5).values]
                })
                st.dataframe(hot_df, width="stretch")
                
            with col2:
                st.subheader("Bottom 5 Cold Numbers")
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
        st.header("Live Randomness & Independence Tests")
        st.markdown("Run standard mathematical tests dynamically over the selected date range.")
        st.markdown("---")
        
        try:
            chi2_main, p_main = calculate_uniformity_test(tuple(all_balls), max_ball_val)
        except Exception as e:
            chi2_main, p_main = 0.0, 1.0
            st.warning(f"Could not calculate uniformity stats for main balls: {e}")
            
        try:
            chi2_pb, p_pb = calculate_uniformity_test(tuple(df_filtered['powerball'].values), int(df_filtered['powerball'].max()))
        except Exception as e:
            chi2_pb, p_pb = 0.0, 1.0
            st.warning(f"Could not calculate uniformity stats for PowerBall: {e}")
            
        try:
            runs_count, z_stat, p_runs = calculate_runs_test(tuple(df_filtered['sum_main_balls'].values))
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
            
        st.markdown("### Draw Sum Normality Trend")
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
            st.pyplot(fig_sums, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering draw sum normality trend: {e}")
            plt.close()
        
    # ==================== TAB 3: PARITY SPLITS ====================
    with tab3:
        st.header("Parity Distributions (Odd vs. Even)")
        st.markdown(f"Evaluates if odd/even ball ratios match binomial expectations $B({num_main}, 0.5)$.")
        
        try:
            chi2_parity, p_parity, obs, exp = calculate_parity_test(tuple(df_filtered['odd_count'].values), num_main)
            
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
            st.pyplot(fig_parity, use_container_width=True)
            
            st.subheader("Observed Parity Counts Table")
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
        st.header("Historical Draws Database Search")
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
            
    # ==================== TAB 5: GUESS ANALYZER & SIMULATOR ====================
    with tab5:
        st.header("Interactive Guess Analyzer & Simulator")
        st.markdown("Enter your lucky numbers to check compliance, statistical likelihood, and simulate gameplay outcomes!")
        
        # Load preset parameters dynamically
        from config import GAME_PRESETS
        game_key = game_preset.lower().replace(" ", "-")
        preset = GAME_PRESETS.get(game_key, GAME_PRESETS["powerball"])
        num_main_balls = preset["num_main_balls"]
        max_main_ball = preset["max_main_ball"]
        max_pb = preset.get("max_powerball", 0)
        
        # Generate random guess option
        if st.button("Generate Random Guess", help="Pre-fills input fields with a randomized compliant ticket"):
            import random
            random_main = sorted(random.sample(range(1, max_main_ball + 1), num_main_balls))
            st.session_state["random_guess_main"] = ",".join(map(str, random_main))
            if max_pb > 0:
                random_pb = random.randint(1, max_pb)
                st.session_state["random_guess_pb"] = random_pb
        
        # Inputs setup
        default_text = st.session_state.get("random_guess_main", "")
        guess_text = st.text_input(
            f"Enter your {num_main_balls} main numbers (1 to {max_main_ball}), separated by commas:",
            value=default_text,
            placeholder=f"e.g. {','.join(map(str, range(1, num_main_balls + 1)))}"
        )
        
        guess_pb = None
        if max_pb > 0:
            default_pb = st.session_state.get("random_guess_pb", 1)
            guess_pb = st.number_input(
                f"Enter your PowerBall number (1 to {max_pb}):",
                min_value=1,
                max_value=max_pb,
                step=1,
                value=int(default_pb)
            )
            
        # Parse inputs
        guess_main = []
        is_valid = False
        val_msg = ""
        
        if guess_text:
            try:
                guess_main = [int(x.strip()) for x in guess_text.split(",") if x.strip()]
                is_valid = True
            except ValueError:
                is_valid = False
                val_msg = "Main numbers must be integers separated by commas."
                
            if is_valid:
                # Validation checks
                if len(guess_main) != num_main_balls:
                    is_valid = False
                    val_msg = f"Must enter exactly {num_main_balls} main numbers (entered {len(guess_main)})."
                elif len(set(guess_main)) != len(guess_main):
                    is_valid = False
                    val_msg = "Duplicate main numbers detected."
                else:
                    for val in guess_main:
                        if not (1 <= val <= max_main_ball):
                            is_valid = False
                            val_msg = f"Number {val} is outside valid range [1, {max_main_ball}]."
                            break
                            
        # Visual compliance indicators
        if guess_text:
            if is_valid:
                st.success("✔ Compliance: Your guess complies with the game rules and logic!")
            else:
                st.error(f"❌ Compliance Error: {val_msg}")
                
        # Analyze and Save Button
        if guess_text and is_valid:
            # Perform calculations
            odds_count = sum(1 for x in guess_main if x % 2 != 0)
            evens_count = num_main_balls - odds_count
            
            # Historical split occurrence
            parity_match_ratio = df_filtered['odd_count'] == odds_count
            parity_percentage = (sum(parity_match_ratio) / len(df_filtered)) * 100
            
            # Sum percentile
            guess_sum = sum(guess_main)
            historical_sums = df_filtered['sum_main_balls'].values
            sum_percentile = stats.percentileofscore(historical_sums, guess_sum)
            
            # Number hotness
            all_numbers = df_filtered[ball_cols].values.flatten()
            freq_map = pd.Series(all_numbers).value_counts().to_dict()
            guess_freqs = [freq_map.get(n, 0) / total_draws * 100 for n in guess_main]
            avg_freq = float(np.mean(guess_freqs))
            
            # Historical Match
            guess_sorted = sorted(guess_main)
            match_query = df_filtered[
                (df_filtered['ball_1'] == guess_sorted[0]) &
                (df_filtered['ball_2'] == guess_sorted[1]) &
                (df_filtered['ball_3'] == guess_sorted[2]) &
                (df_filtered['ball_4'] == guess_sorted[3]) &
                (df_filtered['ball_5'] == guess_sorted[4])
            ]
            if num_main_balls == 6:
                match_query = match_query[df_filtered['ball_6'] == guess_sorted[5]]
            if max_pb > 0:
                match_query = match_query[df_filtered['powerball'] == guess_pb]
                
            if not match_query.empty:
                match_date = match_query.iloc[0]['date']
                match_msg = f"Match found! Won jackpot on {match_date}."
            else:
                match_msg = "No Match"
                
            if st.button("Analyze & Save Guess"):
                save_user_guess(
                    game=game_preset,
                    main_numbers=guess_main,
                    powerball=guess_pb,
                    is_valid=True,
                    validation_message="Valid",
                    username=st.session_state["username"],
                    odd_even_ratio=f"{odds_count}O:{evens_count}E",
                    draw_sum=guess_sum,
                    average_frequency=round(avg_freq, 2),
                    historic_match=match_msg
                )
                st.session_state["analyzed_guess"] = {
                    "main": guess_main,
                    "pb": guess_pb,
                    "odds": odds_count,
                    "evens": evens_count,
                    "parity_pct": parity_percentage,
                    "sum": guess_sum,
                    "sum_percentile": sum_percentile,
                    "avg_freq": avg_freq,
                    "match_msg": match_msg
                }
                st.success("Guess analysis completed and saved to database!")
                
        # Display insights
        analysis = st.session_state.get("analyzed_guess")
        # Check if the guess in session state matches current inputs
        if analysis and is_valid and analysis["main"] == guess_main and (max_pb == 0 or analysis["pb"] == guess_pb):
            st.markdown("### Likelihood & Intelligence Insights")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label="Odd / Even Ratio",
                    value=f"{analysis['odds']} Odd : {analysis['evens']} Even",
                    delta=f"{analysis['parity_pct']:.1f}% frequency in history",
                    delta_color="off"
                )
            with col2:
                st.metric(
                    label="Main Balls Sum",
                    value=f"{analysis['sum']}",
                    delta=f"Percentile: {analysis['sum_percentile']:.1f}%",
                    delta_color="off"
                )
            with col3:
                st.metric(
                    label="Average Occurrence Rate",
                    value=f"{analysis['avg_freq']:.2f}%",
                    delta="Mean ball frequency",
                    delta_color="off"
                )
                
            # History Match Alert
            if analysis['match_msg'] != "No Match":
                st.warning(f"🚨 **Jackpot History**: {analysis['match_msg']}")
            else:
                st.info("ℹ **Jackpot History**: This combination has never won the jackpot historically.")
                
            # Monte Carlo Simulator Section
            st.markdown("---")
            st.subheader("Play Simulator (Monte Carlo)")
            st.markdown("Simulate drawing random games to see how long it takes to win the jackpot using your guess.")
            
            sim_runs = st.number_input(
                "Select simulation runs:",
                min_value=10000,
                max_value=1000000,
                value=100000,
                step=50000,
                help="Higher runs take slightly longer but provide more accurate estimates."
            )
            
            if st.button("Run Simulator"):
                import random
                import time
                
                st.write(f"Running {sim_runs:,} iterations...")
                
                match_counts = {i: 0 for i in range(num_main_balls + 1)}
                jackpot_won = False
                jackpot_index = -1
                
                guess_main_set = set(guess_main)
                
                t_start = time.time()
                
                if max_pb > 0:
                    for idx in range(1, sim_runs + 1):
                        draw = random.sample(range(1, max_main_ball + 1), num_main_balls)
                        draw_pb = random.randint(1, max_pb)
                        
                        hits = len(guess_main_set.intersection(draw))
                        
                        if hits == num_main_balls and draw_pb == guess_pb:
                            jackpot_won = True
                            jackpot_index = idx
                            
                        match_counts[hits] += 1
                else:
                    for idx in range(1, sim_runs + 1):
                        draw = random.sample(range(1, max_main_ball + 1), num_main_balls)
                        
                        hits = len(guess_main_set.intersection(draw))
                        
                        if hits == num_main_balls:
                            jackpot_won = True
                            jackpot_index = idx
                            
                        match_counts[hits] += 1
                        
                t_end = time.time()
                
                st.success(f"Simulation completed in {t_end - t_start:.2f} seconds!")
                
                col_sim1, col_sim2 = st.columns(2)
                with col_sim1:
                    st.markdown("**Draw Outcomes Map:**")
                    for hits, count in match_counts.items():
                        pct = (count / sim_runs) * 100
                        st.write(f"- Match {hits} numbers: **{count:,}** times ({pct:.4f}%)")
                        
                with col_sim2:
                    if jackpot_won:
                        st.balloons()
                        st.success(f"🎉 **JACKPOT WON!** hit at draw #{jackpot_index:,}!")
                        years = jackpot_index / 104
                        st.write(f"It took equivalent to playing this ticket for **{years:.1f} years** (assuming 2 draws/week).")
                    else:
                        st.warning("❌ **Jackpot not hit in this simulation run.**")
                        # Theoretical calculations
                        theoretical_odds = 20358520
                        estimated_years = theoretical_odds / 104
                        st.write(f"At SA Lottery probability, matching this jackpot expects **1 in 20.3 million** draws.")
                        st.write(f"Playing this ticket twice a week would take on average **{estimated_years:,.0f} years** of drawings.")
                        
        else:
            if not guess_text:
                st.info("Enter your lucky numbers above or click 'Generate Random Guess' to start analyzing.")
                
        # History Table Section
        st.markdown("---")
        st.subheader("Your Guess History")
        
        # Load history from DB
        history = get_user_history(game_preset, username=st.session_state["username"])
        if history:
            col_clear, _ = st.columns([1, 4])
            with col_clear:
                if st.button("Clear Saved Guesses"):
                    clear_user_history(game_preset, username=st.session_state["username"])
                    st.success("Guess history deleted!")
                    st.rerun()
                    
            history_df = pd.DataFrame(history)
            if not history_df.empty:
                history_df = history_df.drop(columns=["id", "game"])
                history_df = history_df.rename(columns={
                    "timestamp": "Timestamp",
                    "main_numbers": "Guessed Main Balls",
                    "powerball": "Guessed PowerBall",
                    "is_valid": "Compliant?",
                    "validation_message": "Validation Status",
                    "odd_even_ratio": "Odd/Even Split",
                    "draw_sum": "Draw Sum",
                    "average_frequency": "Mean Frequency (%)",
                    "historic_match": "Historical Match Outcome"
                })
                history_df['Compliant?'] = history_df['Compliant?'].map({1: "Yes", 0: "No"})
                st.dataframe(history_df, use_container_width=True)
        else:
            st.write("No guess logs saved in history database yet.")

if __name__ == "__main__":
    main()
