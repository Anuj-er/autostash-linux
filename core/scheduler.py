#!/usr/bin/env python3
import os
import sys
import time
import threading
import datetime
import json
import subprocess

class Scheduler:
    def __init__(self):
        self.schedule_thread = None
        self.running = False
        self.current_schedule = None

    def setup_schedule(self, schedule_config, script_path):
        """Set up automated backup schedule"""
        try:
            self.current_schedule = schedule_config
            self.script_path = script_path
            
            # Stop existing schedule if running
            if self.schedule_thread and self.schedule_thread.is_alive():
                self.running = False
                self.schedule_thread.join()
            
            # Start new schedule
            self.running = True
            self.schedule_thread = threading.Thread(target=self._run_schedule)
            self.schedule_thread.daemon = True
            self.schedule_thread.start()
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to set up schedule: {str(e)}")

    def remove_schedule(self):
        """Remove scheduled backup"""
        try:
            if self.schedule_thread and self.schedule_thread.is_alive():
                self.running = False
                self.schedule_thread.join()
            self.current_schedule = None
            return True
        except Exception as e:
            raise Exception(f"Failed to remove schedule: {str(e)}")

    def get_schedule(self):
        """Get current schedule configuration"""
        return self.current_schedule

    def get_schedule_status(self):
        """Get the current schedule status"""
        if self.current_schedule and self.schedule_thread and self.schedule_thread.is_alive():
            return {
                "scheduler": "thread",
                "status": "active",
                "schedule": self.current_schedule
            }
        return {"status": "not_scheduled"}

    def _run_schedule(self):
        """Run the scheduled backup"""
        while self.running:
            try:
                now = datetime.datetime.now()
                hour = int(self.current_schedule['hour'])
                minute = int(self.current_schedule['minute'])
                
                # Calculate next run time
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    if self.current_schedule['frequency'].lower() == 'daily':
                        next_run += datetime.timedelta(days=1)
                    elif self.current_schedule['frequency'].lower() == 'weekly':
                        next_run += datetime.timedelta(days=7)
                    elif self.current_schedule['frequency'].lower() == 'monthly':
                        if now.month == 12:
                            next_run = next_run.replace(year=now.year + 1, month=1)
                        else:
                            next_run = next_run.replace(month=now.month + 1)
                
                # Sleep until next run
                sleep_seconds = (next_run - now).total_seconds()
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
                
                # Run backup if still running
                if self.running:
                    python_path = sys.executable
                    subprocess.run([python_path, self.script_path, "--backup"])
                
            except Exception as e:
                print(f"Schedule error: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying

# Create global scheduler instance
scheduler = Scheduler()

def setup_schedule(schedule_config, script_path):
    """Set up automated backup schedule"""
    return scheduler.setup_schedule(schedule_config, script_path)

def remove_schedule():
    """Remove scheduled backup"""
    return scheduler.remove_schedule()

def get_schedule():
    """Get current schedule configuration"""
    return scheduler.get_schedule()

def get_schedule_status():
    """Get the current schedule status"""
    return scheduler.get_schedule_status()

# If run directly (by scheduler)
if __name__ == "__main__":
    # This allows the script to be called by scheduler
    # It will perform backup with default options
    from backup_logic import BackupManager
    from config_manager import ConfigManager
    import keyring
    
    # Load configuration
    config = ConfigManager()
    settings = config.get_settings()
    folders = config.get_folders()
    
    # Get GitHub token
    token = keyring.get_password("autostash", "github_token")
    if not token:
        sys.exit("No GitHub token found")
    
    # Run backup with settings
    backup = BackupManager()
    try:
        backup.run(
            folders,
            "default_repo",
            backup_system=settings.get("backup_system", False),
            encrypt=settings.get("encrypt", False),
            compress=settings.get("compress", False),
            incremental=settings.get("incremental", True)
        )
    except Exception as e:
        # Log error
        error_log = os.path.expanduser("~/.autostash/error.log")
        os.makedirs(os.path.dirname(error_log), exist_ok=True)
        with open(error_log, "a") as f:
            f.write(f"{datetime.datetime.now()}: {str(e)}\n")
        sys.exit(1)


