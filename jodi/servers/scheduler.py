import datetime
from rq_scheduler import Scheduler

from jodi.config import QUEUE_NAME, SCHEDULE_INTERVAL_SECONDS, CACHE_HOST, CACHE_PORT
from jodi.models import cache
from jodi.servers.tasks import process_log_batch

def main():
    """
    Connects to Redis and schedules the process_log_batch task.
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
    print("Checking for existing scheduled jobs for 'process_log_batch'...")
    jobs_to_cancel = []
    for job in scheduler.get_jobs():
        # job.func_name might be fully qualified like 'module.submodule.tasks.process_log_batch'
        # or just 'tasks.process_log_batch'. Be flexible or specific.
        if 'tasks.process_log_batch' in job.func_name:
            jobs_to_cancel.append(job)
            
    if jobs_to_cancel:
        print(f"Found {len(jobs_to_cancel)} existing scheduled job(s) for 'process_log_batch'. Canceling them...")
        for job in jobs_to_cancel:
            print(f"  Canceling job: {job.id} ({job.func_name}) scheduled for {job.scheduled_at}")
            scheduler.cancel(job)
        print("Existing jobs canceled.")
    else:
        print("No existing scheduled jobs found for 'process_log_batch'.")

    # --- Schedule the job ---
    print(f"Scheduling 'process_log_batch' to run every {SCHEDULE_INTERVAL_SECONDS} seconds.")
    try:
        job = scheduler.schedule(
            scheduled_time=datetime.datetime.now(datetime.timezone.utc),  # Start as soon as possible
            func=process_log_batch,                  # The function to schedule
            args=None,                               # No arguments for process_log_batch
            kwargs=None,                             # No keyword arguments
            interval=SCHEDULE_INTERVAL_SECONDS,      # Time interval in seconds
            repeat=None,                             # Repeat indefinitely (None means infinite repeats)
            meta={'description': 'Periodic log batch processing'} # Optional metadata
        )
        print(f"Job 'process_log_batch' successfully scheduled with ID: {job.id}")
        print(f"It will be enqueued to queue '{QUEUE_NAME}' every {SCHEDULE_INTERVAL_SECONDS} seconds.")
        print("Ensure an `rq-scheduler` daemon and `rq worker` are running to process these jobs.")

    except Exception as e:
        print(f"Error scheduling job: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()