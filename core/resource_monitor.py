import psutil
import time
import threading
import os
from datetime import datetime

class ResourceMonitor:
    def __init__(self):
        self.monitoring = False
        self.thread = None
        self.cpu_usage = 0
        self.memory_usage = 0
        self.disk_usage = 0
        self.callbacks = []
        
    def start_monitoring(self, interval=1.0):
        """Start monitoring system resources in a separate thread"""
        if self.monitoring:
            return

        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.thread.daemon = True
        self.thread.start()

    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _monitor_loop(self, interval):
        """Internal monitoring loop that runs in a separate thread"""
        while self.monitoring:
            self.cpu_usage = psutil.cpu_percent(interval=0.5)
            self.memory_usage = psutil.virtual_memory().percent
            self.disk_usage = psutil.disk_usage('/').percent
            
            # Call all registered callbacks with current usage
            for callback in self.callbacks:
                try:
                    callback(
                        cpu=self.cpu_usage,
                        memory=self.memory_usage,
                        disk=self.disk_usage
                    )
                except Exception as e:
                    print(f"Error in resource monitor callback: {e}")
            
            time.sleep(interval)

    def register_callback(self, callback):
        """Register a callback function to receive resource updates"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def unregister_callback(self, callback):
        """Remove a previously registered callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def get_current_usage(self):
        """Get the current resource usage as a dictionary"""
        return {
            'cpu': self.cpu_usage,
            'memory': self.memory_usage,
            'disk': self.disk_usage
        }
