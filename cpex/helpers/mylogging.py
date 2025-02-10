import logging
from io import StringIO

mylogger = None

def init_mylogger(name:str, filename:str, level:int=logging.DEBUG) -> logging.Logger:
    global mylogger
    
    mylogger = logging.getLogger(name)
    mylogger.setLevel(level)

    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    mylogger.addHandler(file_handler)

def create_stream_logger(name:str, level:int=logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    log_stream = StringIO()
    stream_handler = logging.StreamHandler(log_stream)
    stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.addHandler(stream_handler)
    
    logger.log_stream = log_stream

    return logger

def print_logs(logger:logging.Logger):
    print("\n\n==== Logs from Execution ====")
    log_contents = logger.log_stream.getvalue()
    print(log_contents)
    print("==== End of Logs ====\n\n")

def close_logger(logger:logging.Logger):
    logger.log_stream.close()
    logger.handlers.clear()