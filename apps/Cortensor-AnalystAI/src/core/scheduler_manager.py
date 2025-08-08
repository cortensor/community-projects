import logging
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pytz import timezone
from src.config import SCHEDULER_DB_PATH, DEFAULT_TIMEZONE
from src.utils.database import add_task_to_queue, add_schedule, get_all_schedules, delete_schedule

logger = logging.getLogger(__name__)

# --- FUNGSI INI SEKARANG BERDIRI SENDIRI ---
def add_task_to_queue_job(topic: str, user_id: int):
    """
    This is the function the scheduler calls. It is self-contained.
    It simply adds a task to the database queue for the worker to pick up.
    """
    request_id = f"sched_{uuid.uuid4().hex[:10]}"
    logger.info(f"Scheduled job running: Adding task for topic '{topic}' to queue (Request ID: {request_id}).")
    # Fungsi ini hanya berinteraksi dengan database, tidak dengan objek bot.
    add_task_to_queue(request_id, user_id, topic, analysis_type="scheduled")

class SchedulerManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SchedulerManager, cls).__new__(cls)
        return cls._instance

    # --- __init__ TIDAK LAGI MEMERLUKAN `bot` ---
    def __init__(self):
        if not hasattr(self, 'scheduler'):
            jobstores = {
                'default': SQLAlchemyJobStore(url=f'sqlite:///{SCHEDULER_DB_PATH}')
            }
            self.scheduler = BackgroundScheduler(jobstores=jobstores, timezone=timezone(DEFAULT_TIMEZONE))
            self.tz = timezone(DEFAULT_TIMEZONE)
            logger.info(f"Scheduler initialized with timezone {DEFAULT_TIMEZONE}.")

    def start(self):
        """Starts the scheduler and re-adds any jobs from our custom DB."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started.")
            self._reload_jobs_from_db()

    def _reload_jobs_from_db(self):
        """Loads schedules from our custom DB and ensures they are in the scheduler."""
        logger.info("Reloading jobs from database...")
        schedules = get_all_schedules()
        for schedule in schedules:
            job_id = schedule['job_id']
            if not self.scheduler.get_job(job_id):
                logger.info(f"Re-adding missing job {job_id} to scheduler.")
                self.scheduler.add_job(
                    add_task_to_queue_job,  # <-- Memanggil fungsi mandiri
                    'cron',
                    hour=schedule['hour'],
                    minute=schedule['minute'],
                    id=job_id,
                    args=[schedule['topic'], schedule['user_id']]
                )

    def schedule_daily_analysis(self, user_id: int, topic: str, hour: int, minute: int) -> str | None:
        """Creates a new daily scheduled job."""
        job_id = f"user_{user_id}_topic_{topic.lower().replace(' ','_')}"
        
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            delete_schedule(job_id)

        try:
            self.scheduler.add_job(
                add_task_to_queue_job,  # <-- Memanggil fungsi mandiri
                'cron',
                hour=hour,
                minute=minute,
                id=job_id,
                args=[topic, user_id]
            )
            add_schedule(job_id, user_id, topic, hour, minute)
            logger.info(f"Successfully scheduled job {job_id} for {hour:02d}:{minute:02d} daily.")
            return job_id
        except Exception as e:
            logger.error(f"Failed to schedule job {job_id}: {e}", exc_info=True)
            return None

    def delete_scheduled_job(self, job_id: str, user_id: int) -> bool:
        """Deletes a scheduled job."""
        schedules = get_all_schedules(user_id)
        job_ids = [s['job_id'] for s in schedules]

        if job_id not in job_ids:
            logger.warning(f"User {user_id} attempted to delete job {job_id} they don't own.")
            return False

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        delete_schedule(job_id)
        logger.info(f"User {user_id} successfully deleted scheduled job {job_id}.")
        return True
