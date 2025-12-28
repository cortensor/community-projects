"""
Xea Governance Oracle - RQ Worker

Redis Queue worker process for background jobs.
"""

import os
import sys
import logging

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from redis import Redis
from rq import Worker, Queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_redis_connection() -> Redis:
    """Get Redis connection from environment."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url)


def main():
    """Run the RQ worker."""
    logger.info("Starting Xea RQ Worker...")

    redis_conn = get_redis_connection()

    # Define queues to listen on
    queues = [
        Queue("validation", connection=redis_conn),
        Queue("aggregation", connection=redis_conn),
        Queue("attestation", connection=redis_conn),
        Queue("default", connection=redis_conn),
    ]

    # Create and start worker
    worker = Worker(queues, connection=redis_conn)
    logger.info(f"Worker listening on queues: {[q.name for q in queues]}")
    worker.work()


if __name__ == "__main__":
    main()
