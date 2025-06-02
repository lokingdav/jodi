import logging
from io import StringIO

mylogger = None

def init_mylogger(name:str, filename:str, level:int=logging.DEBUG) -> logging.Logger:
    global mylogger
    
    mylogger = init_logger(name, filename, level)

def init_logger(name:str, filename: str, level:int=logging.DEBUG, formatter:str="%(asctime)s - %(levelname)s - %(message)s") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    file_handler = logging.FileHandler(filename)

    if formatter:
        file_handler.setFormatter(logging.Formatter(formatter))

    logger.addHandler(file_handler)

    return logger

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