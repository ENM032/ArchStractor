import logging
from datetime import date
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

def validate_draw_data(
    draw_date: Optional[date], 
    main_balls: List[int], 
    powerball: Optional[int]
) -> Tuple[bool, str]:
    """
    Validates a single PowerBall draw.
    Returns (is_valid, error_message).
    
    Validation rules:
    1. Draw date must exist and be a valid datetime.date object.
    2. Draw date must not be in the future (compared to current local date).
    3. main_balls must have exactly 5 numbers.
    4. All main numbers must be unique.
    5. Main numbers must be integers in the range [1, 50] (covers historical [1, 45] and current [1, 50]).
    6. Powerball must be a single integer in the range [1, 20] (covers historical [1, 20] and current [1, 16]).
    """
    # 1. Date existence
    if not draw_date:
        return False, "Draw date is missing or invalid"
        
    # 2. Date in the future check
    current_today = date.today()
    if draw_date > current_today:
        return False, f"Draw date {draw_date} is in the future (today is {current_today})"
        
    # 3. Main balls count
    if len(main_balls) != 5:
        return False, f"Expected exactly 5 main numbers, got {len(main_balls)}: {main_balls}"
        
    # 4. Main balls types and ranges
    for ball in main_balls:
        if not isinstance(ball, int):
            return False, f"Main number '{ball}' is not an integer"
        if not (1 <= ball <= 50):
            return False, f"Main number {ball} is out of valid range [1, 50]"
            
    # 5. Main balls uniqueness
    if len(set(main_balls)) != 5:
        return False, f"Duplicate numbers found in main numbers: {main_balls}"
        
    # 6. Powerball validation
    if powerball is None:
        return False, "PowerBall number is missing"
    if not isinstance(powerball, int):
        return False, f"PowerBall '{powerball}' is not an integer"
    if not (1 <= powerball <= 20):
        return False, f"PowerBall {powerball} is out of valid range [1, 20]"
        
    return True, ""
