import os
from tinydb import TinyDB, Query
from datetime import datetime
from src.config import (
    DEFAULT_TIMEZONE, 
    DEFAULT_CURRENCY, 
    CACHE_EXPIRATION_MINUTES,
    DEFAULT_ALERTS_THRESHOLD,
    DEFAULT_DATA_RETENTION_DAYS
)

# Ensure the data directory exists when this module is imported
os.makedirs("data", exist_ok=True)

db = TinyDB('data/tasks.db')
schedules_db = TinyDB('data/schedules.db')
portfolio_db = TinyDB('data/portfolio.db') # Tambahkan ini: Database untuk portofolio
dca_db = TinyDB('data/dca.db') # Database untuk DCA schedules
user_settings_db = TinyDB('data/user_settings.db') # Database untuk user settings

Task = Query()
Schedule = Query()
Portfolio = Query() # Tambahkan ini: Query object untuk portofolio
DCA = Query() # Query object untuk DCA
UserSettings = Query() # Query object untuk user settings

# --- FUNGSI YANG HILANG DIKEMBALIKAN DI SINI ---
def setup_database():
    """
    Ensures that the database directory exists.
    This function is called once at startup.
    """
    # The directory is already created when the module is loaded,
    # but this function provides a clear entry point called from main.py.
    pass

# --- Fungsi untuk Tugas Sekali Jalan (One-Time Jobs) ---

def add_task_to_queue(request_id: str, user_id: int, topic: str, ack_message_id: int = None, analysis_type: str = "manual"):
    """Adds a new analysis task to the database queue."""
    db.insert({
        'request_id': request_id,
        'user_id': user_id,
        'topic': topic,
        'status': 'PENDING',
        'result_text': None,
        'attempts': 0,
        'ack_message_id': ack_message_id,
        'analysis_type': analysis_type  # "manual" or "scheduled"
    })

def get_pending_task():
    """Retrieves the oldest pending task."""
    return db.get(Task.status == 'PENDING')

def get_all_user_tasks(user_id: int) -> list:
    """Gets all one-time tasks for a specific user."""
    return db.search(Task.user_id == user_id)

def get_task_by_id(request_id: str, user_id: int) -> dict | None:
    """
    Gets a specific task by its request_id, ensuring it belongs to the user.
    """
    return db.get((Task.request_id == request_id) & (Task.user_id == user_id))

def update_task_status(request_id: str, status: str):
    """Updates the status of a task."""
    db.update({'status': status}, Task.request_id == request_id)

def update_task_result(request_id: str, status: str, result_text: str):
    """Updates a task with the final result."""
    db.update({'status': status, 'result_text': result_text}, Task.request_id == request_id)

def increment_task_attempts(request_id: str):
    """Increments the retry attempt count for a task."""
    task = db.get(Task.request_id == request_id)
    if task:
        current_attempts = task.get('attempts', 0)
        db.update({'attempts': current_attempts + 1}, Task.request_id == request_id)
        return current_attempts + 1
    return 0

def delete_task_by_id(request_id: str, user_id: int) -> int:
    """Deletes a one-time task by its request_id and user_id."""
    return len(db.remove((Task.request_id == request_id) & (Task.user_id == user_id)))

# --- Fungsi untuk Jadwal (Schedules) ---

def add_schedule(job_id: str, user_id: int, topic: str, hour: int, minute: int):
    """Saves schedule metadata."""
    schedules_db.upsert(
        {'job_id': job_id, 'user_id': user_id, 'topic': topic, 'hour': hour, 'minute': minute},
        Schedule.job_id == job_id
    )

def get_all_schedules(user_id: int = None) -> list:
    """Gets all schedules, optionally filtered by user_id."""
    if user_id:
        return schedules_db.search(Schedule.user_id == user_id)
    return schedules_db.all()

def delete_schedule(job_id: str) -> int:
    """Deletes a schedule metadata."""
    return schedules_db.remove(Schedule.job_id == job_id)

# --- Fungsi untuk Portofolio (Portfolio) ---
def add_portfolio_asset(user_id: int, symbol: str, quantity: float) -> bool:
    """Adds or updates an asset in a user's portfolio."""
    # Simbol disimpan dalam huruf kecil untuk konsistensi
    return portfolio_db.upsert(
        {'user_id': user_id, 'symbol': symbol.upper(), 'quantity': quantity},
        (Portfolio.user_id == user_id) & (Portfolio.symbol == symbol.upper())
    )

def get_user_portfolio(user_id: int) -> list:
    """Retrieves all assets for a specific user's portfolio."""
    return portfolio_db.search(Portfolio.user_id == user_id)

def remove_portfolio_asset(user_id: int, symbol: str) -> int:
    """Removes an asset from a user's portfolio."""
    return len(portfolio_db.remove((Portfolio.user_id == user_id) & (Portfolio.symbol == symbol.upper())))

def clear_user_portfolio(user_id: int) -> int:
    """Clears all assets from a user's portfolio."""
    return len(portfolio_db.remove(Portfolio.user_id == user_id))

# --- Fungsi untuk User Settings ---
def get_user_settings(user_id: int) -> dict:
    """Retrieves user settings, returns default settings if not found."""
    settings = user_settings_db.get(UserSettings.user_id == user_id)
    if not settings:
        # Default settings from config
        default_settings = {
            'user_id': user_id,
            'timezone': DEFAULT_TIMEZONE,
            'currency': DEFAULT_CURRENCY,
            'language': 'en',
            'notifications': True,
            'alerts_threshold': DEFAULT_ALERTS_THRESHOLD,
            'charts_enabled': True,
            'cache_duration': CACHE_EXPIRATION_MINUTES,
            'export_format': 'HTML',
            'data_retention_days': DEFAULT_DATA_RETENTION_DAYS,
            'privacy_mode': False,
            'created_at': datetime.now().isoformat()
        }
        user_settings_db.insert(default_settings)
        return default_settings
    return settings

def update_user_setting(user_id: int, setting_key: str, setting_value) -> bool:
    """Updates a specific user setting."""
    try:
        # Ensure user settings exist
        get_user_settings(user_id)
        
        update_data = {setting_key: setting_value, 'updated_at': datetime.now().isoformat()}
        user_settings_db.update(update_data, UserSettings.user_id == user_id)
        return True
    except Exception as e:
        print(f"Error updating user setting: {e}")
        return False

def reset_user_settings(user_id: int) -> bool:
    """Resets user settings to default values."""
    try:
        user_settings_db.remove(UserSettings.user_id == user_id)
        get_user_settings(user_id)  # This will create default settings
        return True
    except Exception as e:
        print(f"Error resetting user settings: {e}")
        return False

# --- Fungsi untuk DCA (Dollar Cost Averaging) ---
def add_dca_schedule(user_id: int, symbol: str, amount: float, currency: str, frequency: str, time: str, is_active: bool = True) -> str:
    """Adds a new DCA schedule."""
    import uuid
    dca_id = f"dca_{uuid.uuid4().hex[:10]}"
    
    dca_schedule = {
        'dca_id': dca_id,
        'user_id': user_id,
        'symbol': symbol.upper(),
        'amount': amount,
        'currency': currency.upper(),
        'frequency': frequency,  # 'daily', 'weekly', 'monthly'
        'time': time,  # HH:MM format
        'is_active': is_active,
        'created_at': datetime.now().isoformat(),
        'last_executed': None,
        'total_invested': 0.0,
        'total_quantity': 0.0,
        'execution_count': 0
    }
    
    dca_db.insert(dca_schedule)
    return dca_id

def get_user_dca_schedules(user_id: int) -> list:
    """Retrieves all DCA schedules for a user."""
    return dca_db.search(DCA.user_id == user_id)

def get_active_dca_schedules() -> list:
    """Retrieves all active DCA schedules."""
    return dca_db.search(DCA.is_active == True)

def update_dca_execution(dca_id: str, quantity_purchased: float, amount_spent: float, execution_price: float) -> bool:
    """Updates DCA schedule after execution."""
    try:
        dca_schedule = dca_db.get(DCA.dca_id == dca_id)
        if not dca_schedule:
            return False
        
        new_total_invested = dca_schedule['total_invested'] + amount_spent
        new_total_quantity = dca_schedule['total_quantity'] + quantity_purchased
        new_execution_count = dca_schedule['execution_count'] + 1
        
        update_data = {
            'last_executed': datetime.now().isoformat(),
            'total_invested': new_total_invested,
            'total_quantity': new_total_quantity,
            'execution_count': new_execution_count,
            'last_execution_price': execution_price,
            'last_quantity_purchased': quantity_purchased
        }
        
        dca_db.update(update_data, DCA.dca_id == dca_id)
        return True
    except Exception as e:
        print(f"Error updating DCA execution: {e}")
        return False

def toggle_dca_schedule(dca_id: str, user_id: int, is_active: bool) -> bool:
    """Activates or deactivates a DCA schedule."""
    try:
        result = dca_db.update(
            {'is_active': is_active, 'updated_at': datetime.now().isoformat()},
            (DCA.dca_id == dca_id) & (DCA.user_id == user_id)
        )
        return len(result) > 0
    except Exception as e:
        print(f"Error toggling DCA schedule: {e}")
        return False

def delete_dca_schedule(dca_id: str, user_id: int) -> bool:
    """Deletes a DCA schedule."""
    try:
        result = dca_db.remove((DCA.dca_id == dca_id) & (DCA.user_id == user_id))
        return len(result) > 0
    except Exception as e:
        print(f"Error deleting DCA schedule: {e}")
        return False

def get_dca_schedule_by_id(dca_id: str, user_id: int) -> dict:
    """Retrieves a specific DCA schedule."""
    return dca_db.get((DCA.dca_id == dca_id) & (DCA.user_id == user_id))