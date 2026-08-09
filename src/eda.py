import os
import sys
import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import scipy.stats as stats

# Configure logging
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger(__name__)

# Configure plotting aesthetics
sns.set_theme(style="darkgrid")
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 13,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.titlesize": 15,
    "figure.dpi": 100
})

def generate_eda_reports(filepath: str, output_dir: str):
    """Generates visual charts and reports for a cleaned CSV dataset."""
    file_name = os.path.basename(filepath)
    game_name = file_name.replace("_clean.csv", "")
    logger.info(f"Generating EDA visual reports for: {file_name}")
    
    # Load data using pandas
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return
        
    total_draws = len(df)
    if total_draws == 0:
        logger.warning(f"No records in {file_name}. Skipping.")
        return
        
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    
    # Identify ball columns
    ball_cols = [c for c in df.columns if c.startswith("ball_")]
    num_main = len(ball_cols)
    
    # 1. NUMBER FREQUENCY ANALYSIS
    try:
        # Flatten main numbers to count occurrences
        all_numbers = df[ball_cols].values.flatten()
        max_num = int(np.max(all_numbers))
        
        freq_series = pd.Series(all_numbers).value_counts().reindex(range(1, max_num + 1), fill_value=0)
        
        # Sort frequencies to highlight hot and cold numbers
        sorted_freqs = freq_series.sort_values(ascending=False)
        hot_numbers = sorted_freqs.head(5)
        cold_numbers = sorted_freqs.tail(5)
        
        # Plot frequency distribution
        plt.figure(figsize=(12, 5))
        colors = ['#1f77b4' for _ in range(max_num)]
        # Color hot numbers red, cold numbers yellow
        for idx, num in enumerate(freq_series.index):
            if num in hot_numbers.index:
                colors[idx] = '#d62728'  # Red for hot
            elif num in cold_numbers.index:
                colors[idx] = '#bcbd22'  # Olive/Yellow for cold
                
        plt.bar(freq_series.index, freq_series.values, color=colors, edgecolor='black', alpha=0.85)
        plt.axhline(y=len(all_numbers)/max_num, color='#2ca02c', linestyle='--', label=f'Expected Mean ({len(all_numbers)/max_num:.1f})')
        
        # Custom legends for highlights
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#d62728', label='Top 5 Hot Numbers'),
            Patch(facecolor='#1f77b4', label='Standard Frequencies'),
            Patch(facecolor='#bcbd22', label='Bottom 5 Cold Numbers'),
            plt.Line2D([0], [0], color='#2ca02c', linestyle='--', label='Theoretical Expected Mean')
        ]
        
        plt.title(f"{game_name.upper()} Main Number Frequency Distribution (Total draws: {total_draws})")
        plt.xlabel("Ball Number")
        plt.ylabel("Occurrences")
        plt.xticks(range(1, max_num + 1, 2 if max_num > 40 else 1))
        plt.legend(handles=legend_elements, loc="upper right")
        plt.tight_layout()
        
        freq_plot_path = os.path.join(output_dir, f"{game_name}_frequency.png")
        plt.savefig(freq_plot_path, dpi=120)
        plt.close()
        logger.info(f"Saved frequency plot: {freq_plot_path}")
    except Exception as e:
        logger.error(f"Failed to generate frequency plot for {game_name}: {e}")
        plt.close()
        
    # 2. DRAW SUM DISTRIBUTION
    try:
        plt.figure(figsize=(8, 5))
        sns.histplot(df['sum_main_balls'], kde=True, color='#9467bd', stat="density", bins=20, alpha=0.6)
        
        # Overlay theoretical normal distribution if applicable
        mu_sum = np.mean(df['sum_main_balls'])
        sigma_sum = np.std(df['sum_main_balls'])
        x_range = np.linspace(df['sum_main_balls'].min(), df['sum_main_balls'].max(), 200)
        plt.plot(x_range, stats.norm.pdf(x_range, mu_sum, sigma_sum), color='#d62728', linewidth=2, label='Fitted Normal Curve')
        
        plt.title(f"{game_name.upper()} Draw Sum Distribution ($\\mu$={mu_sum:.1f}, $\\sigma$={sigma_sum:.1f})")
        plt.xlabel("Sum of Main Balls")
        plt.ylabel("Probability Density")
        plt.legend()
        plt.tight_layout()
        
        sums_plot_path = os.path.join(output_dir, f"{game_name}_sums.png")
        plt.savefig(sums_plot_path, dpi=120)
        plt.close()
        logger.info(f"Saved draw sums plot: {sums_plot_path}")
    except Exception as e:
        logger.error(f"Failed to generate draw sums plot for {game_name}: {e}")
        plt.close()
        
    # 3. CORRELATION HEATMAP
    try:
        # Select analytical variables
        corr_cols = [
            "year", "month", "day_of_month", "day_of_week", "is_weekend",
            "sum_main_balls", "mean_main_balls", "min_main_ball", "max_main_ball",
            "range_main_balls", "odd_count", "even_count", "is_powerball_even"
        ]
        # Filter variables present in dataset
        corr_cols = [c for c in corr_cols if c in df.columns]
        
        plt.figure(figsize=(10, 8))
        corr_matrix = df[corr_cols].corr()
        
        # Mask to show only lower triangle
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        
        sns.heatmap(corr_matrix, mask=mask, annot=True, cmap="coolwarm", fmt=".2f", vmin=-1.0, vmax=1.0, square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
        plt.title(f"{game_name.upper()} Analytical Correlation Matrix")
        plt.tight_layout()
        
        corr_plot_path = os.path.join(output_dir, f"{game_name}_correlation.png")
        plt.savefig(corr_plot_path, dpi=120)
        plt.close()
        logger.info(f"Saved correlation plot: {corr_plot_path}")
    except Exception as e:
        logger.error(f"Failed to generate correlation heatmap for {game_name}: {e}")
        plt.close()
        
    # 4. PARITY BINOMIAL DISTRIBUTION COMPARISON
    try:
        plt.figure(figsize=(8, 5))
        obs_counts = df['odd_count'].value_counts().reindex(range(0, num_main + 1), fill_value=0)
        
        expected_freqs = []
        for k in range(num_main + 1):
            pmf_val = stats.binom.pmf(k, num_main, 0.5)
            expected_freqs.append(total_draws * pmf_val)
            
        x = np.arange(num_main + 1)
        width = 0.35
        
        plt.bar(x - width/2, obs_counts.values, width, label='Observed Count', color='#2ca02c', alpha=0.8)
        plt.bar(x + width/2, expected_freqs, width, label='Binomial Expectation B(N, 0.5)', color='#ff7f0e', alpha=0.8)
        
        plt.title(f"{game_name.upper()} Odd Balls Distribution vs. Binomial Projections")
        plt.xlabel("Odd Balls per Draw")
        plt.ylabel("Number of Draws")
        plt.xticks(x)
        plt.legend()
        plt.tight_layout()
        
        parity_plot_path = os.path.join(output_dir, f"{game_name}_odd_even.png")
        plt.savefig(parity_plot_path, dpi=120)
        plt.close()
        logger.info(f"Saved odd-even parity plot: {parity_plot_path}\n" + "-"*45)
    except Exception as e:
        logger.error(f"Failed to generate parity plot for {game_name}: {e}")
        plt.close()

def main():
    parser = argparse.ArgumentParser(description="SA National Lottery Exploratory Data Analysis suite")
    parser.add_argument("--input", "-i", type=str, default=None, help="Input cleaned CSV file path")
    parser.add_argument("--output-dir", "-o", type=str, default="docs/images", help="Output images directory")
    args = parser.parse_args()
    
    # Auto-resolve cleaned CSVs if not input
    if args.input:
        if os.path.exists(args.input):
            generate_eda_reports(args.input, args.output_dir)
        else:
            logger.error(f"Input file not found: {args.input}")
            sys.exit(1)
    else:
        cleaned_dir = "data/cleaned"
        if not os.path.exists(cleaned_dir):
            logger.error(f"Cleaned datasets folder '{cleaned_dir}' not found. Please run src/prepare.py first.")
            sys.exit(1)
            
        csv_files = [
            os.path.join(cleaned_dir, f)
            for f in os.listdir(cleaned_dir)
            if f.endswith("_clean.csv")
        ]
        
        if not csv_files:
            logger.warning(f"No cleaned CSV datasets found in '{cleaned_dir}'.")
            sys.exit(0)
            
        logger.info(f"Discovered {len(csv_files)} cleaned datasets. Generating visual reports...")
        for f in csv_files:
            generate_eda_reports(f, args.output_dir)
            
    logger.info("All exploratory data analysis visualization reports generated successfully!")

if __name__ == "__main__":
    main()
