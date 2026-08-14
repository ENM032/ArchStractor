import logging
from datetime import date
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

def validate_draw_data(
    draw_date: Optional[date], 
    main_balls: List[int], 
    powerball: Optional[int],
    num_main_balls: int = 5,
    num_power_balls: int = 1
) -> Tuple[bool, str]:
    """
    Validates a single draw against schema constraints.
    Returns (is_valid, error_message).
    """
    # 1. Date existence
    if not draw_date:
        return False, "Draw date is missing or invalid"
        
    # 2. Date in the future check
    current_today = date.today()
    if draw_date > current_today:
        return False, f"Draw date {draw_date} is in the future (today is {current_today})"
        
    # 3. Main balls count validation (dynamic schema)
    if len(main_balls) != num_main_balls:
        return False, f"Expected exactly {num_main_balls} main numbers, got {len(main_balls)}: {main_balls}"
        
    # 4. Main balls types and ranges
    max_main = 58 if num_main_balls == 6 else 50
    for ball in main_balls:
        if not isinstance(ball, int):
            return False, f"Main number '{ball}' is not an integer"
        if not (1 <= ball <= max_main):
            return False, f"Main number {ball} is out of valid range [1, {max_main}]"
            
    # 5. Main balls uniqueness
    if len(set(main_balls)) != num_main_balls:
        return False, f"Duplicate numbers found in main numbers: {main_balls}"
        
    # 6. Powerball validation
    if num_power_balls > 0:
        if powerball is None:
            return False, "PowerBall/Bonus number is missing"
        if not isinstance(powerball, int):
            return False, f"PowerBall/Bonus '{powerball}' is not an integer"
        max_pb = 58 if num_main_balls == 6 else 20
        if not (1 <= powerball <= max_pb):
            return False, f"PowerBall/Bonus {powerball} is out of valid range [1, {max_pb}]"
            
    return True, ""
