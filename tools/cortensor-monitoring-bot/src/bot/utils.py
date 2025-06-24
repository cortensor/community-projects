# bot/utils.py
import re
from datetime import datetime, timezone
from typing import Optional

# A regular expression for validating Ethereum-style addresses.
ETH_ADDR_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

def shorten_address(address: str) -> str:
    """
    Shortens a long Ethereum address into a more readable '0x...xxxx' format.

    :param address: The full Ethereum address string.
    :return: The shortened address string.
    """
    if not isinstance(address, str) or len(address) < 10:
        return "Invalid Address"
    return f"{address[:6]}...{address[-4:]}"

def time_ago(ts: Optional[int]) -> str:
    """
    Converts a Unix timestamp into a human-readable relative time string (e.g., "5 minutes ago").

    :param ts: The Unix timestamp (integer).
    :return: A string representing the time elapsed.
    """
    if not ts:
        return "N/A"
        
    now = datetime.now(timezone.utc)
    dt_obj = datetime.fromtimestamp(ts, tz=timezone.utc)
    seconds = (now - dt_obj).total_seconds()

    if seconds < 0:
        return "In the future"
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)} minutes ago"
        
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)} hours ago"
        
    days = hours / 24
    return f"{int(days)} days ago"

def calculate_success_rate(points: Optional[int], counter: Optional[int]) -> float:
    """
    Safely calculates a success rate percentage from points and counters.
    Handles cases where the counter is zero or None to prevent division errors.

    :param points: The number of success points.
    :param counter: The total number of attempts (counters).
    :return: The calculated success rate as a float (e.g., 99.5).
    """
    if not counter or points is None:
        return 0.0
    return (max(0, points) / counter) * 100

def get_change_str(current_rate: Optional[float], old_rate: Optional[float], 
                   current_points: Optional[int], old_points: Optional[int]) -> str:
    """
    Formats a string describing the change in points and success rate, including a trend emoji.

    :param current_rate: The current success rate percentage.
    :param old_rate: The historical success rate percentage.
    :param current_points: The current number of points.
    :param old_points: The historical number of points.
    :return: A formatted string like "+10 pts (+1.25% 📈)" or "N/A".
    """
    if any(v is None for v in [current_rate, old_rate, current_points, old_points]):
        return "N/A"
    
    rate_diff = current_rate - old_rate
    point_diff = current_points - old_points

    # Format the point difference string
    point_str = f"+{point_diff}" if point_diff >= 0 else str(point_diff)
    
    # Format the rate difference string with a trend emoji
    if rate_diff > 0.1:
        rate_str = f"+{rate_diff:.2f}% 📈"
    elif rate_diff < -0.1:
        rate_str = f"{rate_diff:.2f}% 📉"
    else:
        rate_str = f"~0.00% ➖"
        
    return f"{point_str} pts ({rate_str})"
