# Centralized game preset settings and constants

GAME_PRESETS = {
    "powerball": {
        "num_main_balls": 5,
        "max_main_ball": 50,
        "max_powerball": 20,
        "url_template": "https://za.national-lottery.com/powerball/results/{year}-archive"
    },
    "powerball-xtra": {
        "num_main_balls": 5,
        "max_main_ball": 50,
        "max_powerball": 20,
        "url_template": "https://za.national-lottery.com/powerball-xtra/results/{year}-archive"
    },
    "lotto": {
        "num_main_balls": 6,
        "max_main_ball": 52,
        "max_powerball": 52,
        "url_template": "https://za.national-lottery.com/lotto/results/{year}-archive"
    }
}

DEFAULT_GAME = "powerball"
MAX_PAGE_SIZE = 5 * 1024 * 1024  # 5MB safety limit for fetched pages
