from PySide6.QtCore import QTimer, QDateTime
import datetime
import threading
from api_client import APIClient
from report_generator import ReportGenerator

class ScanScheduler:
    def __init__(self, config):
        self.config = config
        self.timer = QTimer()
        self.timer.timeout.connect(self.perform_scan)
        self.scan_thread = None
        self.scan_frequency = "daily"  # Default frequency
        self.scan_time = "09:00"  # Default time
        self.auto_email = False

    def set_frequency(self, frequency: str):
        """Set the scan frequency (daily, weekly, monthly, etc.)"""
        self.scan_frequency = frequency.lower()

    def set_scan_time(self, time: str):
        """Set the specific time for the scan (HH:mm format)"""
        self.scan_time = time

    def toggle_auto_email(self, enabled: bool):
        """Enable or disable automatic email of reports"""
        self.auto_email = enabled

    def start(self):
        """Start the scheduler based on the configured frequency and time"""
        try:
            self.stop()  # Stop any existing timer
            next_scan = self.calculate_next_scan()
            if next_scan:
                delay = (next_scan - datetime.datetime.now()).total_seconds()
                self.timer.start(int(delay * 1000))  # Convert seconds to milliseconds
                print(f"Scheduled scanning enabled. Next scan at {next_scan}.")
            else:
                raise ValueError("Failed to calculate the next scan time.")
        except Exception as e:
            print(f"Error starting scheduled scanning: {str(e)}")
            self.timer.stop()

    def stop(self):
        """Stop the scheduler"""
        self.timer.stop()
        print("Scheduled scanning disabled.")

    def calculate_next_scan(self) -> datetime.datetime:
        """Calculate the next scan time based on frequency and time"""
        try:
            now = datetime.datetime.now()
            scan_time = datetime.datetime.strptime(self.scan_time, "%H:%M").time()
            next_scan = datetime.datetime.combine(now.date(), scan_time)

            if self.scan_frequency == "daily":
                if next_scan <= now:
                    next_scan += datetime.timedelta(days=1)
            elif self.scan_frequency == "weekly":
                if next_scan <= now:
                    next_scan += datetime.timedelta(weeks=1)
            elif self.scan_frequency == "monthly":
                next_month = (now.month % 12) + 1
                year = now.year + (now.month // 12)
                next_scan = datetime.datetime(year, next_month, 1, scan_time.hour, scan_time.minute)
            elif self.scan_frequency == "bi-annually":
                next_month = now.month + 6 if now.month <= 6 else now.month - 6
                year = now.year + (1 if now.month > 6 else 0)
                next_scan = datetime.datetime(year, next_month, 1, scan_time.hour, scan_time.minute)
            elif self.scan_frequency == "annually":
                next_scan = datetime.datetime(now.year + 1, 1, 1, scan_time.hour, scan_time.minute)
            elif self.scan_frequency == "custom":
                # Custom logic can be added here if needed
                pass

            return next_scan if next_scan > now else None
        except Exception as e:
            print(f"Error calculating next scan time: {str(e)}")
            return None

    def perform_scan(self):
        """Perform the scan and optionally email the report"""
        self.timer.stop()  # Stop the timer to avoid overlapping scans

        def scan_task():
            try:
                print("Performing scheduled scan...")
                api = APIClient(self.config)
                inactive_users = api.find_inactive_users(self.config['DAYS_TO_SEARCH_BEYOND'])
                
                if inactive_users:
                    report_file = ReportGenerator.generate_csv_report(
                        inactive_users,
                        self.config['DAYS_TO_SEARCH_BEYOND']
                    )
                    
                    if self.auto_email:
                        print("Automatically emailing the report...")
                        ReportGenerator.send_email(self.config, report_file)
                else:
                    print("No inactive users found during the scan.")
            except Exception as e:
                print(f"Scheduled scan failed: {str(e)}")
            finally:
                # Restart the scheduler for the next scan
                self.start()

        # Run the scan in a separate thread to avoid blocking the UI
        try:
            self.scan_thread = threading.Thread(target=scan_task)
            self.scan_thread.start()
        except Exception as e:
            print(f"Error starting scan thread: {str(e)}")