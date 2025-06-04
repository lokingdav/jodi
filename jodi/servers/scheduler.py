import datetime, argparse
from rq_scheduler import Scheduler

from jodi.config import QUEUE_NAME, SCHEDULE_INTERVAL_SECONDS, CACHE_HOST, CACHE_PORT
from jodi.models import cache
from jodi.servers.tasks import client_handler, server_handler

def main(is_client: bool = False):
    handler_name = "client_handler" if is_client else "server_handler"
    """
    Connects to Redis and schedules the client_handler or server_handler task.
    """
    print(f"Connecting to Redis at {CACHE_HOST}:{CACHE_PORT}...")
    try:
        redis_conn = cache.connect(decode_responses=False)
        redis_conn.ping() # Verify connection
        print("Successfully connected to Redis.")
    except cache.redis.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to Redis: {e}")
        print("Please ensure Redis is running and accessible.")
        return

    scheduler = Scheduler(queue_name=QUEUE_NAME, connection=redis_conn)
    print(f"Scheduler initialized for queue '{QUEUE_NAME}'.")

    # --- Optional: Clear existing scheduled jobs for this function ---
    # This prevents duplicate scheduled jobs if you run this script multiple times.
    # Be cautious if you have other jobs scheduled programmatically that you don't want to remove.
    print(f"Checking for existing scheduled jobs for '{handler_name}'...")
    jobs_to_cancel = []
    for job in scheduler.get_jobs():
        if f'tasks.{handler_name}' in job.func_name:
            jobs_to_cancel.append(job)
            
    if jobs_to_cancel:
        print(f"Found {len(jobs_to_cancel)} existing scheduled job(s) for '{handler_name}'. Canceling them...")
        for job in jobs_to_cancel:
            print(f"  Canceling job: {job.id} ({job.func_name}) scheduled for {job.scheduled_at}")
            scheduler.cancel(job)
        print("Existing jobs canceled.")
    else:
        print(f"No existing scheduled jobs found for '{handler_name}'.")

    # --- Schedule the job ---
    print(f"Scheduling '{handler_name}' to run every {SCHEDULE_INTERVAL_SECONDS} seconds.")
    try:
        job = scheduler.schedule(
            scheduled_time=datetime.datetime.now(datetime.timezone.utc),
            func=client_handler if is_client else server_handler,
            args=None,
            kwargs=None,
            interval=SCHEDULE_INTERVAL_SECONDS,
            repeat=None,
            meta={'description': 'Periodic log batch processing'}
        )
        print(f"Job '{handler_name}' successfully scheduled with ID: {job.id}")
        print(f"It will be enqueued to queue '{QUEUE_NAME}' every {SCHEDULE_INTERVAL_SECONDS} seconds.")
        print("Ensure an `rq-scheduler` daemon and `rq worker` are running to process these jobs.")

    except Exception as e:
        print(f"Error scheduling job: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schedule periodic tasks for Jodi.")
    parser.add_argument(
        "--client",
        action="store_true",
        default=False,
        help="Schedule the client_handler task instead of the server_handler."
    )
    args = parser.parse_args()
    main(is_client=args.client)