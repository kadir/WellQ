from abc import ABC, abstractmethod

class BaseScanner(ABC):
    """
    The Blueprint. All 30+ scanners must look like this.
    """
    
    @abstractmethod
    def parse(self, scan_instance, json_file):
        """
        Must return the number of findings created (int).
        """
        pass