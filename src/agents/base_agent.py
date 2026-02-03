from abc import ABC, abstractmethod
from datetime import datetime


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logs = []
    
    def log(self, msg: str, level: str = "INFO"):
        entry = f"[{datetime.now():%H:%M:%S}] [{self.name}] [{level}] {msg}"
        self.logs.append(entry)
        print(entry)
    
    @abstractmethod
    def process(self, input_data):
        pass
