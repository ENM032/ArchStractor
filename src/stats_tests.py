import os
import sys
import csv
import math
import argparse
import logging
from typing import List, Dict, Any, Tuple
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

def load_cleaned_data(filepath: str) -> Tuple[List[List[int]], List[int], List[int], List[int], int]:
    """
    Loads draw results from a cleaned CSV file.
    Returns:
        - main_draws: List of list of integers (main numbers)
        - powerballs: List of integers (PowerBall/Bonus values)
        - draw_sums: List of integers (sums of main numbers)
        - odd_counts: List of integers (counts of odd main balls per draw)
        - num_main_balls: Number of main balls in the game schema
    """
    main_draws = []
    powerballs = []
    draw_sums = []
    odd_counts = []
    num_main_balls = 5  # default fallback
    
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        # Determine number of main balls from columns
        cols = reader.fieldnames or []
        ball_cols = [c for c in cols if c.startswith("ball_")]
        num_main_balls = len(ball_cols)
        
        for row in reader:
            main = [int(row[f"ball_{i}"]) for i in range(1, num_main_balls + 1)]
            pb = int(row["powerball"])
            d_sum = int(row["sum_main_balls"])
            odds = int(row["odd_count"])
            
            main_draws.append(main)
            powerballs.append(pb)
            draw_sums.append(d_sum)
            odd_counts.append(odds)
            
    return main_draws, powerballs, draw_sums, odd_counts, num_main_balls

# ==================== STATISTICAL TESTS ====================

def run_uniformity_test(numbers: List[int], min_val: int, max_val: int) -> Tuple[float, float]:
    """
    Performs Chi-Square Goodness-of-Fit test against uniform expected frequencies.
    Returns: (chi2_statistic, p_value)
    """
    total_count = len(numbers)
    num_bins = max_val - min_val + 1
    
    # Calculate observed frequencies
    observed = [0] * num_bins
    for num in numbers:
        if min_val <= num <= max_val:
            observed[num - min_val] += 1
            
    # Expected frequency under uniform distribution
    expected = [total_count / num_bins] * num_bins
    
    chi2, p_val = stats.chisquare(f_obs=observed, f_exp=expected)
    return chi2, p_val

def run_wald_wolfowitz_runs_test(sequence: List[int]) -> Tuple[int, float, float]:
    """
    Wald-Wolfowitz Runs Test for independence over time.
    Calculates if sequence of values fluctuates randomly above/below median.
    Returns: (runs_count, z_statistic, p_value)
    """
    if not sequence:
        return 0, 0.0, 1.0
        
    median_val = sorted(sequence)[len(sequence) // 2]
    
    # Classify elements as above (1) or below/equal (0) median
    binary_seq = [1 if x > median_val else 0 for x in sequence]
    
    # Count runs and runs parameters
    n1 = sum(binary_seq)
    n2 = len(binary_seq) - n1
    
    if n1 == 0 or n2 == 0:
        return 1, 0.0, 1.0
        
    runs = 1
    for i in range(1, len(binary_seq)):
        if binary_seq[i] != binary_seq[i-1]:
            runs += 1
            
    # Calculate expected runs and variance
    expected_runs = (2.0 * n1 * n2) / (n1 + n2) + 1.0
    variance = (2.0 * n1 * n2 * (2.0 * n1 * n2 - n1 - n2)) / (((n1 + n2) ** 2) * (n1 + n2 - 1))
    
    # Z-statistic
    z_stat = (runs - expected_runs) / math.sqrt(variance)
    
    # Two-tailed p-value
    p_val = stats.norm.sf(abs(z_stat)) * 2.0
    
    return runs, z_stat, p_val

def run_parity_binomial_test(odd_counts: List[int], num_main_balls: int) -> Tuple[float, float, List[float], List[float]]:
    """
    Tests if the distribution of odd balls per draw conforms to binomial distribution B(N, 0.5).
    Returns: (chi2_statistic, p_value, observed_freqs, expected_freqs)
    """
    total_draws = len(odd_counts)
    
    # Observed frequencies of draws containing k odd balls (0 to N)
    observed = [0] * (num_main_balls + 1)
    for k in odd_counts:
        if 0 <= k <= num_main_balls:
            observed[k] += 1
            
    # Expected frequencies using binomial PMF
    expected = []
    for k in range(num_main_balls + 1):
        # binom.pmf(k, N, 0.5)
        pmf_val = stats.binom.pmf(k, num_main_balls, 0.5)
        expected.append(total_draws * pmf_val)
        
    chi2, p_val = stats.chisquare(f_obs=observed, f_exp=expected)
    return chi2, p_val, observed, expected

# ==================== MAIN RUNNER ====================

def analyze_dataset(filepath: str):
    """Loads a cleaned dataset, runs all statistical tests, and prints a formatted report."""
    file_name = os.path.basename(filepath)
    print("\n" + "="*70)
    print(f"  RANDOMNESS ANALYSIS REPORT: {file_name.upper()}")
    print("="*70)
    
    try:
        main_draws, powerballs, draw_sums, odd_counts, num_main = load_cleaned_data(filepath)
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return
        
    total_draws = len(main_draws)
    print(f"Total draws analyzed: {total_draws}")
    print(f"Main balls per draw:  {num_main}")
    print("-"*70)
    
    # Flat lists for number frequency tests
    all_main_balls = [b for draw in main_draws for b in draw]
    max_main_ball = max(all_main_balls) if all_main_balls else 50
    max_pb_ball = max(powerballs) if powerballs else 20
    
    # 1. Uniformity Test (Main Balls)
    chi2_main, p_main = run_uniformity_test(all_main_balls, 1, max_main_ball)
    main_result = "PASS" if p_main >= 0.05 else "FAIL (Rejected Randomness)"
    print(f"1. Chi-Square Uniformity Test (Main Balls 1-{max_main_ball}):")
    print(f"   - Chi-Square Stat:  {chi2_main:.4f}")
    print(f"   - p-value:          {p_main:.4f}")
    print(f"   - Result:           {main_result} (Frequencies are {'uniformly distributed' if p_main >= 0.05 else 'biased'})")
    print()
    
    # 2. Uniformity Test (PowerBall/Bonus Ball)
    chi2_pb, p_pb = run_uniformity_test(powerballs, 1, max_pb_ball)
    pb_result = "PASS" if p_pb >= 0.05 else "FAIL (Rejected Randomness)"
    print(f"2. Chi-Square Uniformity Test (PowerBall/Bonus 1-{max_pb_ball}):")
    print(f"   - Chi-Square Stat:  {chi2_pb:.4f}")
    print(f"   - p-value:          {p_pb:.4f}")
    print(f"   - Result:           {pb_result} (Frequencies are {'uniformly distributed' if p_pb >= 0.05 else 'biased'})")
    print()
    
    # 3. Runs Test for Independence (Draw Sums)
    runs_count, z_stat, p_runs = run_wald_wolfowitz_runs_test(draw_sums)
    runs_result = "PASS" if p_runs >= 0.05 else "FAIL (Rejected Randomness)"
    print("3. Wald-Wolfowitz Runs Test for Independence (Draw Sums):")
    print(f"   - Total Runs:       {runs_count}")
    print(f"   - Z-statistic:      {z_stat:.4f}")
    print(f"   - p-value:          {p_runs:.4f}")
    print(f"   - Result:           {runs_result} (Consecutive draws are {'independent' if p_runs >= 0.05 else 'dependent'})")
    print()
    
    # 4. Parity Binomial Test (Odd/Even Distribution)
    chi2_parity, p_parity, obs, exp = run_parity_binomial_test(odd_counts, num_main)
    parity_result = "PASS" if p_parity >= 0.05 else "FAIL (Rejected Randomness)"
    print(f"4. Parity Binomial Distribution Test B({num_main}, 0.5):")
    print(f"   - Observed counts (0 to {num_main} odd balls): {obs}")
    print(f"   - Expected counts (0 to {num_main} odd balls): {[round(x, 1) for x in exp]}")
    print(f"   - Chi-Square Stat:  {chi2_parity:.4f}")
    print(f"   - p-value:          {p_parity:.4f}")
    print(f"   - Result:           {parity_result} (Odd/Even splits match {'theoretical expectations' if p_parity >= 0.05 else 'biased distributions'})")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="SA National Lottery randomness and statistical testing suite")
    parser.add_argument("--input", "-i", type=str, default=None, help="Input cleaned CSV file path")
    args = parser.parse_args()
    
    if args.input:
        if os.path.exists(args.input):
            analyze_dataset(args.input)
        else:
            logger.error(f"Specified input file not found: {args.input}")
            sys.exit(1)
    else:
        # Auto-detect all cleaned datasets
        cleaned_dir = "data/cleaned"
        if not os.path.exists(cleaned_dir):
            logger.error(f"Cleaned datasets directory '{cleaned_dir}' not found. Please run src/prepare.py first.")
            sys.exit(1)
            
        csv_files = [
            os.path.join(cleaned_dir, f)
            for f in os.listdir(cleaned_dir)
            if f.endswith("_clean.csv")
        ]
        
        if not csv_files:
            logger.warning(f"No cleaned CSV datasets found in '{cleaned_dir}'.")
            sys.exit(0)
            
        logger.info(f"Discovered {len(csv_files)} cleaned datasets. Running randomness checks...")
        for f in csv_files:
            analyze_dataset(f)

if __name__ == "__main__":
    main()
