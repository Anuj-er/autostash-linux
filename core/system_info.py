# system_info.py
import platform
import psutil
import os

def get_system_info():
    """Get essential system information"""
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'hostname': platform.node(),
        'cpu_count': psutil.cpu_count(),
        'total_memory': psutil.virtual_memory().total,
        'disk_usage': psutil.disk_usage('/').percent,
        'username': os.getenv('USER')
    }

def get_os_info():
    try:
        return platform.system()
    except:
        return "Unknown"

def get_cpu_info():
    try:
        cpu_info = platform.processor()
        return cpu_info
    except:
        return f"{psutil.cpu_count(logical=True)} cores"

def get_memory_info():
    try:
        mem = psutil.virtual_memory()
        return f"{round(mem.total / (1024**3), 2)} GB Total"
    except:
        return "Unknown"

def get_disk_info():
    try:
        disk = psutil.disk_usage('/')
        return f"{round(disk.total / (1024**3), 2)} GB Total, {round(disk.free / (1024**3), 2)} GB Free"
    except:
        return "Unknown"