import json, time, hashlib, secrets, base64, random

class Benchmark:
    def __init__(self, name: str, filename: str = None):
        self.name = name.lower()
        self.entries: list = []
        self.start_time: float = 0
        self.filename: str = None
        
        if filename:
            self.filename = f"experiments/results/{filename.lower()}.csv"
            create_csv(self.filename, "test,duration_ms")

    def start(self):
        self.start_time = time.perf_counter()
        
    def resume(self):
        """Just an alias for start()"""
        self.start()
        
    def pause(self):
        dur_ms: float = self.get_duration_in_ms()
        self.entries.append(dur_ms)
        self.start_time = 0
        return self
    
    def add_entry(self, entry: float):
        self.entries.append(entry)

    def end(self):
        """Just an alias for pause()"""
        self.pause()
        return self
    
    def to_string(self):
        return f"{self.name},{self.total()}"
    
    def save(self):
        if self.filename:
            update_csv(self.filename, self.to_string())
        return self
    
    def get_duration_in_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000
    
    def total(self, short=True) -> float:
        total = sum(self.entries)
        return round(total, 3) if short else total
    
    def reset(self):
        self.entries = []
        self.start_time = 0
        return self

def hash256(data: str):
    if type(data) == dict or type(data) == list:
        data = stringify(data)
    data = data.encode() if type(data) == str else data
    return hashlib.sha256(data).hexdigest()

def base64encode(data: str):
    if type(data) == dict:
        data = stringify(data)
        
    data = data.encode() if type(data) == str else data
    return base64.b64encode(data).decode()

def base64decode(data: str):
    if type(data) == dict:
        data = stringify(data)
        
    data = data.encode() if type(data) == str else data
    return base64.b64decode(data).decode('utf-8', errors='ignore')  # Decode bytes to string

def stringify(data):
    if type(data) == str:
        return data
    return json.dumps(data, sort_keys=True, separators=(',', ':'))

def parse_json(data):
    if type(data) == str:
        return json.loads(data)
    return data

def startStopwatch():
    return time.perf_counter()

def endStopwatch(test_name, start, numIters, silent=False):
    end_time = time.perf_counter()
    total_dur_ms = (end_time - start) * 1000
    avg_dur_ms = total_dur_ms / numIters

    if not silent:
        print("\n%s\nTotal: %d runs in %0.1f ms\nAvg: %fms"
            % (test_name, numIters, total_dur_ms, avg_dur_ms))
        
    return test_name, total_dur_ms, avg_dur_ms

def stopStopwatch(start, secs=False):
    end_time = time.perf_counter()
    
    if secs:
        return end_time - start
    
    return (end_time - start) * 1000

def random_bytes(n, hex=False):
    d = secrets.token_bytes(n)
    if hex:
        return d.hex()
    return d

def update_csv(file, line, header = None):
    with open(file, 'a') as f:
        # Write header if file is empty
        if f.tell() == 0 and header:
            f.write(header + '\n')
            
        f.write(line + '\n')
        
def create_csv(file, header, mode = 'a'):
    with open(file, mode) as f:
        if f.tell() == 0:
            f.write(header + '\n')
            
def get_number(prompt, default):
    while True:
        try:
            return int(input(prompt) or default)
        except ValueError:
            print("Invalid input. Please enter a number.")


def wait(seconds):
    for i in range(seconds, 0, -1):
        print(f"\rWaiting {i} seconds...", end='')
        time.sleep(1)
        
def print_human_readable_json(data: dict):
    print(json.dumps(data, indent=2, sort_keys=True))
    
def fake_number(cc: str = None):
    cc = random.randint(1, 999) if not cc else cc
    npa = random.randint(200, 999)
    nxx = random.randint(100, 999)
    num = str(random.randint(0, 9999)).zfill(4)
    return f"{cc}{npa}{nxx}{num}"

def toMs(seconds):
    return round(seconds * 1000, 3)