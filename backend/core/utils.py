from datetime import datetime, time, date
import pytz

def get_vietnam_time() -> datetime:
    """Returns the current time in Asia/Ho_Chi_Minh timezone."""
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    return datetime.now(vn_tz)

def is_trading_hours() -> bool:
    """
    Checks if the current Vietnam time is within trading hours.
    Mon-Fri, 9:00 AM - 3:05 PM (15:05) including a small buffer for session close.
    """
    now = get_vietnam_time()
    # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
    if now.weekday() >= 5:
        return False
    
    current_time = now.time()
    morning_start = time(9, 0)
    afternoon_end = time(15, 5) 
    
    return morning_start <= current_time <= afternoon_end
