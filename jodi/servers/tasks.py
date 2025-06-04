import json
import os
import asyncio

from rq import get_current_job
import numpy as np

from jodi.config import LOG_BATCH_KEY, AUDIT_SERVER_URL, TEST_ISK, TEST_ICERT
from jodi.models import cache, persistence
from jodi.helpers import http
from jodi.crypto import audit_logging
from jodi.prototype.stirshaken import certs

def _get_job_details():
    """
    Retrieves the current RQ job and constructs a job ID string 
    and a unique processing key for Redis.
    """
    job = get_current_job()
    if not job:
        # This case should ideally not happen if scheduled via RQ.
        # Useful for direct invocation during testing, but logs might not be retryable by RQ then.
        job_id_str = f"standalone_{os.getpid()}"
        print(f"Worker: Warning - Running outside RQ job context. Using PID for job_id_str: {job_id_str}")
    else:
        job_id_str = str(job.id)
    processing_key = f"{LOG_BATCH_KEY}_processing:{job_id_str}"
    return job_id_str, processing_key

def _load_logs_from_redis_key(redis_conn, key_to_load_from, job_id_str):
    """
    Loads all log entries (bytes) from a given Redis list key.
    Returns a list of bytes, or None if the key is empty or doesn't exist.
    """
    print(f"Worker (Job ID: {job_id_str}): Attempting to load logs from Redis key '{key_to_load_from}'.")
    if not redis_conn.exists(key_to_load_from): # Explicit check for non-existence
        print(f"Worker (Job ID: {job_id_str}): Key '{key_to_load_from}' does not exist.")
        return None
        
    logs_bytes = redis_conn.lrange(key_to_load_from, 0, -1)
    if not logs_bytes:
        print(f"Worker (Job ID: {job_id_str}): Key '{key_to_load_from}' was found but is empty.")
        return None # Indicate key was present but empty
    
    print(f"Worker (Job ID: {job_id_str}): Loaded {len(logs_bytes)} log entries (bytes) from '{key_to_load_from}'.")
    return logs_bytes

def _try_claim_new_logs_from_main_key(redis_conn, main_log_key, processing_key, job_id_str):
    """
    Atomically renames the main_log_key to processing_key to claim new logs.
    Then loads logs from the processing_key.
    Returns a list of log bytes, or None if no logs were claimed or key was empty.
    """
    print(f"Worker (Job ID: {job_id_str}): Attempting to claim new logs by renaming '{main_log_key}' to '{processing_key}'.")
    try:
        # The RENAME command is atomic.
        if redis_conn.rename(main_log_key, processing_key): # Returns True on success in redis-py
            print(f"Worker (Job ID: {job_id_str}): Successfully renamed '{main_log_key}' to '{processing_key}'.")
            # Now load the logs from the processing_key
            return _load_logs_from_redis_key(redis_conn, processing_key, job_id_str)
        else:
            # This path might not be commonly hit with redis-py's rename, 
            # as it tends to raise an error for "no such key".
            print(f"Worker (Job ID: {job_id_str}): Rename command for '{main_log_key}' did not indicate success (unexpected).")
            return None
    except cache.redis.exceptions.ResponseError as e: # Assuming cache.redis.exceptions for redis-py
        if "no such key" in str(e).lower():
            print(f"Worker (Job ID: {job_id_str}): Main log key '{main_log_key}' does not exist. No new logs to claim.")
            return None # No logs to claim
        print(f"Worker (Job ID: {job_id_str}): Redis error during rename: {e}")
        raise # Re-raise other Redis errors
    except Exception as e:
        print(f"Worker (Job ID: {job_id_str}): Unexpected error during rename: {e}")
        raise

def _deserialize_log_entries(logs_bytes_list):
    """
    Converts a list of log bytes (from Redis) into a list of Python dictionaries.
    """
    if not logs_bytes_list:
        return []
    
    deserialized_logs = []
    for i, log_bytes in enumerate(logs_bytes_list):
        try:
            deserialized_logs.append(json.loads(log_bytes.decode('utf-8')))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # Consider how to handle individual bad entries: skip, log error, move to dead-letter, etc.
            print(f"Worker: Error deserializing log entry #{i}: {e}. Log data (bytes): {log_bytes[:100]}...") 
    return deserialized_logs

def _chunk_logs(logs_list, chunk_size=1000):
    return [logs_list[i:i + chunk_size] for i in range(0, len(logs_list), chunk_size)]

async def _handle_server_logs(chunks):
    public_key = certs.get_public_key_from_cert(TEST_ICERT)
    logs = []
    for chunk in chunks:
        for log in chunk['logs']:
            if audit_logging.ecdsa_verify(public_key=public_key, data=log['payload'], sigma=log['sigma']):
                logs.append(log)
    persistence.save_logs(logs)
    print(f"\n\n{len(logs)} Saved to DB", flush=True)

async def _handle_client_logs(logs_list):
    priv_key = certs.get_private_key(TEST_ISK)
    signed_logs = []
    
    # Sign each log entry with the private key
    for log in logs_list:
        signed_logs.append({
            'payload': log, 
            'sigma': audit_logging.ecdsa_sign(private_key=priv_key, data=log)
        })
    
    # Chunk the signed logs into manageable sizes for HTTP requests
    chunks = _chunk_logs(signed_logs)
    reqs = []
    for chunk in chunks:
        reqs.append({
            'url': AUDIT_SERVER_URL,
            'data': {
                'auth_token': audit_logging.ecdsa_sign(private_key=priv_key, data=chunk),
                'logs': signed_logs,
            }
        })
        
    # Send HTTP Requests to the audit server
    http.set_session(http.create_session())
    res = await http.posts(reqs)
    await http.async_destroy_session()
    print("\n\nResponse from audit server:", res, "\n\n", flush=True)

async def _process_logs(logs_list, is_client=True):
    """
    Asynchronously sends the batch of deserialized logs to the audit server
    using your jodi.helpers.http (aiohttp-based) module.
    """
    if not logs_list:
        print("Worker (_process_logs): No logs provided to send.")
        return

    print(f"Worker (_process_logs): Preparing to send {len(logs_list)} logs to {AUDIT_SERVER_URL}.")

    if is_client:
        await _handle_client_logs(logs_list)
    else:
        await _handle_server_logs(logs_list)

def process_log_batch(is_client):
    """
    This is the main RQ job. It orchestrates:
    1. Claiming a batch of logs atomically from Redis.
    2. Deserializing them.
    3. Sending them to a remote audit server using an async HTTP client.
    4. Cleaning up processed logs from Redis.
    It's designed to be retryable by RQ if sending fails.
    """
    job_id_str, processing_key = _get_job_details()
    # Connect to Redis, ensuring byte responses for raw log data
    redis_conn = cache.connect(decode_responses=False)
    
    logs_to_process_bytes = None
    
    try:
        # Stage 1: Determine if we are processing an existing batch (retry) or claiming a new one.
        # Check if a processing key for this job_id already exists (implies a retry)
        logs_to_process_bytes = _load_logs_from_redis_key(redis_conn, processing_key, job_id_str)
        
        if logs_to_process_bytes is None: 
            # If processing_key didn't exist or was empty, try to claim a new batch.
            if not redis_conn.exists(processing_key): # Only try to claim if processing_key truly didn't exist
                print(f"Worker (Job ID: {job_id_str}): No existing data in '{processing_key}'. Attempting to claim new batch from '{LOG_BATCH_KEY}'.")
                logs_to_process_bytes = _try_claim_new_logs_from_main_key(redis_conn, LOG_BATCH_KEY, processing_key, job_id_str)
            # If _load_logs_from_redis_key returned None because processing_key *was* empty, logs_to_process_bytes is still None.
        
        # Check if any logs were actually loaded/claimed
        if not logs_to_process_bytes:
            # If processing_key exists at this point but we have no logs, it means it was an empty list.
            if redis_conn.exists(processing_key):
                print(f"Worker (Job ID: {job_id_str}): '{processing_key}' is empty. Deleting it.")
                redis_conn.delete(processing_key)
            print(f"Worker (Job ID: {job_id_str}): No logs found to process after all checks.")
            return "No logs to process."

        # Stage 2: Deserialize the raw log data
        logs_to_process = _deserialize_log_entries(logs_to_process_bytes)
        if not logs_to_process:
            # This could happen if all entries were malformed or logs_to_process_bytes was non-empty but yielded nothing.
            print(f"Worker (Job ID: {job_id_str}): Deserialization resulted in no usable logs from {len(logs_to_process_bytes)} byte entries. Deleting '{processing_key}'.")
            redis_conn.delete(processing_key) 
            return "Deserialization yielded no usable logs; batch discarded."

        print(f"Worker (Job ID: {job_id_str}): Processing batch of {len(logs_to_process)} deserialized logs from '{processing_key}'.")

        # Stage 3: Send the logs using the async helper
        # asyncio.run() is used to call the async function from this sync RQ task.
        asyncio.run(_process_logs(logs_to_process, is_client))

        # Stage 4: Success - cleanup the processing key from Redis
        redis_conn.delete(processing_key)
        result_message = f"Successfully sent batch of {len(logs_to_process)} logs. Deleted '{processing_key}'."
        print(f"Worker (Job ID: {job_id_str}): {result_message}")
        return result_message

    except http.aiohttp.ClientError as e: # Catching ClientError from aiohttp (or your http module)
        # Logs remain in `processing_key` for the next retry by RQ if configured.
        error_message = f"Worker (Job ID: {job_id_str}): HTTP CLIENT ERROR - Could not send to audit server: {e}. Logs remain in '{processing_key}' for potential retry."
        print(error_message)
        raise # Re-raise the exception for RQ to handle (e.g., retry or move to failed queue)
    except Exception as e:
        # Catch any other unexpected errors. Logs in `processing_key` are preserved if claimed.
        error_message = f"Worker (Job ID: {job_id_str}): UNEXPECTED ERROR - {type(e).__name__}: {e}. Data (if claimed) remains in '{processing_key}'."
        print(error_message)
        # You might want to add more specific error logging here, e.g., traceback.
        import traceback
        traceback.print_exc()
        raise # Re-raise for RQ
    
def client_handler():
    process_log_batch(is_client=True)
    
def server_handler():
    process_log_batch(is_client=False)