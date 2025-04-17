from email.mime import application
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QProgressBar,
    QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QToolButton, QApplication, QComboBox, QCheckBox, QTimeEdit, QDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QCoreApplication, QTime
from PySide6.QtGui import QIntValidator, QIcon, QBrush, QColor
from config_editor import ConfigEditor
from config_manager import ConfigManager
from api_client import APIClient
from report_generator import ReportGenerator
from dialogs import ConfirmationDialog
from scheduler import ScanScheduler
import json
import sys
import os
import datetime

class WorkerThread(QThread):
    progress = Signal(int)
    result = Signal(list)
    error = Signal(str)

    def __init__(self, config, days_threshold):
        super().__init__()
        self.config = config
        self.days_threshold = days_threshold

    def run(self):
        try:
            api = APIClient(self.config)
            inactive_users = api.find_inactive_users(self.days_threshold)
            self.result.emit(inactive_users)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, config_manager=None):
        super().__init__()
        self.setWindowTitle("Azure AD Inactive User Scanner")
        self.setMinimumSize(800, 600)
        
        # Accept config manager instance or create new
        self.config_manager = config_manager if config_manager else ConfigManager()
        self.scheduler = None
        
        # Initialize with safe defaults if config fails
        self.config = self.initialize_config()
        self.setup_ui()

    def initialize_config(self):
        """Safely initialize configuration with multiple fallbacks"""
        try:
            # First attempt to load config
            config = self.config_manager.load_config()
            
            # If config is invalid, show warning and create default
            if not self.config_manager.is_config_valid():
                self.show_config_warning(initial_setup=True)
                config = self.config_manager.create_default_config()
                
            return config
            
        except Exception as e:
            # If everything fails, use bare minimum defaults
            QMessageBox.warning(
                self, 
                "Configuration Error",
                f"Failed to load configuration:\n{str(e)}\n\n"
                "Using minimal default configuration."
            )
            return {
                "GRAPH_API_URL": "https://graph.microsoft.com/v1.0",
                "DAYS_TO_SEARCH_BEYOND": 90
            }

    def show_config_warning(self, initial_setup=False):
        """Show configuration warning with appropriate options"""
        warning = QMessageBox(self)
        warning.setIcon(QMessageBox.Warning)
        warning.setWindowTitle("Configuration Required")
        
        if initial_setup:
            warning.setText(
                "No valid configuration found.\n"
                "Would you like to create a default config file\n"
                "and open the configuration editor?"
            )
        else:
            warning.setText(
                "Current configuration is invalid.\n"
                "Some features may not work properly.\n"
                "Would you like to edit the configuration now?"
            )
        
        warning.addButton("Edit Config", QMessageBox.AcceptRole)
        ignore_btn = warning.addButton("Continue Anyway", QMessageBox.RejectRole)
        warning.setDefaultButton(ignore_btn)
        
        if warning.exec() == QMessageBox.AcceptRole:
            # Create default config if needed
            if initial_setup and not self.config_manager.config_exists():
                self.config_manager.create_default_config()
                
            self.edit_config()
            # Reload config after editing
            self.config = self.config_manager.load_config()

    def setup_ui(self):
        """Sets up the main window UI with safe defaults"""
        try:
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout()
            central_widget.setLayout(layout)
            
            # Config Group - now with status indicator
            config_group = QGroupBox("Configuration Status")
            config_layout = QVBoxLayout()
            
            status_layout = QHBoxLayout()
            self.config_status_label = QLabel()
            self.update_config_status()
            status_layout.addWidget(self.config_status_label)
            
            config_buttons_layout = QHBoxLayout()
            
            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(self.browse_config)
            config_buttons_layout.addWidget(browse_btn)
            
            load_btn = QPushButton("Reload Config")
            load_btn.clicked.connect(self.load_config)
            config_buttons_layout.addWidget(load_btn)
            
            encrypt_btn = QPushButton("Encrypt Credentials")
            encrypt_btn.clicked.connect(self.encrypt_credentials)
            config_buttons_layout.addWidget(encrypt_btn)
            
            edit_btn = QPushButton("Edit Configuration")
            edit_btn.clicked.connect(self.edit_config)
            config_buttons_layout.addWidget(edit_btn)
            
            config_layout.addLayout(status_layout)
            config_layout.addLayout(config_buttons_layout)
            config_group.setLayout(config_layout)
            layout.addWidget(config_group)
            
            # Schedule Group
            schedule_group = QGroupBox("Scheduled Scanning")
            schedule_layout = QVBoxLayout()

            self.schedule_check = QCheckBox("Enable Scheduled Scans")
            self.schedule_check.stateChanged.connect(self.toggle_scheduling)
            schedule_layout.addWidget(self.schedule_check)

            # Frequency selection
            frequency_layout = QHBoxLayout()
            frequency_layout.addWidget(QLabel("Frequency:"))
            self.frequency_combo = QComboBox()
            self.frequency_combo.addItems(["Daily", "Weekly", "Monthly", "Bi-Annually", "Annually", "Custom"])
            self.frequency_combo.currentTextChanged.connect(self.update_scan_frequency)
            frequency_layout.addWidget(self.frequency_combo)
            schedule_layout.addLayout(frequency_layout)

            # Time selection
            time_layout = QHBoxLayout()
            time_layout.addWidget(QLabel("Scan Time:"))
            self.schedule_time = QTimeEdit()
            self.schedule_time.setDisplayFormat("HH:mm")
            self.schedule_time.setTime(QTime.fromString(self.config.get("schedule_time", "09:00"), "HH:mm"))
            self.schedule_time.timeChanged.connect(self.update_scan_time)
            time_layout.addWidget(self.schedule_time)
            schedule_layout.addLayout(time_layout)

            # Auto-email toggle
            self.auto_email_check = QCheckBox("Automatically Email Reports")
            self.auto_email_check.setChecked(self.config.get("auto_email", False))
            self.auto_email_check.stateChanged.connect(self.toggle_auto_email)
            schedule_layout.addWidget(self.auto_email_check)

            schedule_group.setLayout(schedule_layout)
            layout.addWidget(schedule_group)
            
            # Scan Group
            scan_group = QGroupBox("Scan Settings")
            scan_layout = QVBoxLayout()
            
            self.days_threshold_edit = QLineEdit("90")
            self.days_threshold_edit.setValidator(QIntValidator(1, 365))
            scan_layout.addWidget(QLabel("Inactivity Threshold (days):"))
            scan_layout.addWidget(self.days_threshold_edit)
            
            self.scan_btn = QPushButton("Scan for Inactive Users")
            self.scan_btn.clicked.connect(self.start_scan)
            scan_layout.addWidget(self.scan_btn)
            
            self.progress_bar = QProgressBar()
            scan_layout.addWidget(self.progress_bar)
            
            scan_group.setLayout(scan_layout)
            layout.addWidget(scan_group)
            
            # Results Group - Use QTableWidget for columns
            results_group = QGroupBox("Results")
            results_layout = QVBoxLayout()

            # Filter input
            filter_layout = QHBoxLayout()
            filter_layout.addWidget(QLabel("Filter:"))
            self.filter_edit = QLineEdit()
            self.filter_edit.setPlaceholderText("Filter by UPN or Last Sign-in...")
            self.filter_edit.textChanged.connect(self.filter_results_table)
            filter_layout.addWidget(self.filter_edit)
            results_layout.addLayout(filter_layout)

            # Selection controls
            selection_controls = QHBoxLayout()
            self.select_all_btn = QToolButton()
            self.select_all_btn.setText("Select All")
            self.select_all_btn.clicked.connect(self.select_all_users)
            selection_controls.addWidget(self.select_all_btn)

            self.deselect_all_btn = QToolButton()
            self.deselect_all_btn.setText("Deselect All")
            self.deselect_all_btn.clicked.connect(self.deselect_all_users)
            selection_controls.addWidget(self.deselect_all_btn)

            selection_controls.addStretch()
            results_layout.addLayout(selection_controls)

            # User table
            self.user_table = QTableWidget()
            self.user_table.setColumnCount(3)  # UPN, Last Sign-in, Status
            self.user_table.setHorizontalHeaderLabels(["User Principal Name", "Last Sign-In", "Status"])
            self.user_table.setSelectionMode(QAbstractItemView.ExtendedSelection) # Select rows
            self.user_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make read-only
            self.user_table.horizontalHeader().setStretchLastSection(True)  # Stretch last column
            results_layout.addWidget(self.user_table)

            # Action buttons
            action_buttons = QHBoxLayout()
            self.enable_btn = QPushButton("Enable Selected")
            self.enable_btn.clicked.connect(self.enable_users)
            action_buttons.addWidget(self.enable_btn)

            self.disable_btn = QPushButton("Disable Selected")
            self.disable_btn.clicked.connect(self.disable_users)
            action_buttons.addWidget(self.disable_btn)
            results_layout.addLayout(action_buttons)

            # Export buttons
            export_buttons = QHBoxLayout()
            self.export_btn = QPushButton("Export to CSV")
            self.export_btn.clicked.connect(self.export_results)
            export_buttons.addWidget(self.export_btn)

            self.email_btn = QPushButton("Email Report")
            self.email_btn.clicked.connect(self.email_report)
            export_buttons.addWidget(self.email_btn)
            results_layout.addLayout(export_buttons)

            results_group.setLayout(results_layout)
            layout.addWidget(results_group)

            # Status Bar
            self.statusBar().showMessage("Ready")
            
            # Disable buttons until scan completes
            self.toggle_action_buttons(False)

            # Initialize scheduler only if config is valid
            if self.config_manager.is_config_valid():
                self.scheduler = ScanScheduler(self.config)
            
            self.update_column_widths()

        except Exception as e:
            QMessageBox.critical(
                None, 
                "UI Setup Failed", 
                f"Failed to initialize UI:\n{str(e)}"
            )
            raise

    def update_column_widths(self):
        """Adjust column widths as needed"""
        self.user_table.setColumnWidth(0, 300)  # UPN
        self.user_table.setColumnWidth(1, 180)  # Last Sign-in
        self.user_table.setColumnWidth(2, 80)   # Status

    def update_config_status(self):
        """Update configuration status with encryption state"""
        config = self.config_manager.load_config()
        encrypted = config.get('CLIENT_SECRET_ENCRYPTED', False)
        
        status_text = "✔ Configuration valid"
        status_text += " (Encrypted)" if encrypted else " (Unencrypted)"
        
        self.config_status_label.setText(status_text)
        self.config_status_label.setStyleSheet(
            "color: #2ecc71" if encrypted else "color: #e67e22"
        )
        
        # Update tooltip with more details
        tooltip = "Credential security: "
        tooltip += "Encrypted" if encrypted else "Unencrypted - recommend encryption"
        self.config_status_label.setToolTip(tooltip)

    def select_all_users(self):
        """Select all rows in the results table."""
        self.user_table.selectAll()

    def deselect_all_users(self):
        """Deselect all rows in the results table."""
        self.user_table.clearSelection()

    def toggle_action_buttons(self, enabled):
        """Enable/disable action buttons based on scan state"""
        buttons = [
            self.select_all_btn,
            self.deselect_all_btn,
            self.enable_btn,
            self.disable_btn,
            self.export_btn,
            self.email_btn
        ]
        for button in buttons:
            button.setEnabled(enabled)

    def browse_config(self):
        """Open file dialog to select config file with validation"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Config File", "", "JSON Files (*.json)"
        )
        if filename:
            old_path = self.config_manager.config_path
            self.config_manager.config_path = filename
            
            try:
                self.config = self.config_manager.load_config()
                if not self.config_manager.is_config_valid():
                    QMessageBox.warning(
                        self,
                        "Invalid Configuration",
                        "The selected file is missing required fields.\n"
                        "Please edit the configuration."
                    )
                self.update_config_status()
            except Exception as e:
                self.config_manager.config_path = old_path  # Revert on failure
                QMessageBox.critical(
                    self,
                    "Invalid File",
                    f"Could not load config file:\n{str(e)}"
                )

    def load_config(self):
        """Reload configuration with error handling"""
        try:
            self.config = self.config_manager.load_config()
            self.update_config_status()
            
            if not self.config_manager.is_config_valid():
                self.show_config_warning()
            
            # Update UI elements from config
            self.days_threshold_edit.setText(str(self.config.get('DAYS_TO_SEARCH_BEYOND', 90)))
            
            # Only update scheduler if config is valid
            if self.config_manager.is_config_valid():
                if self.scheduler:
                    self.scheduler.stop()
                self.scheduler = ScanScheduler(self.config)
                
            self.statusBar().showMessage("Configuration reloaded")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Failed to reload config:\n{str(e)}"
            )

    def encrypt_credentials(self):
        """Handle encryption from main GUI button"""
        try:
            if self.config_manager.encrypt_credentials():
                QMessageBox.information(
                    self, 
                    "Success", 
                    "Credentials encrypted successfully!\n"
                    "The client secret has been secured."
                )
                self.config = self.config_manager.load_config()
                self.update_config_status()
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "No unencrypted credentials found to encrypt"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Encryption Error",
                f"Could not encrypt credentials:\n{str(e)}"
            )

    def edit_config(self, first_run=False):
        """Open configuration editor"""
        try:
            editor = ConfigEditor(self.config)
            if editor.exec() == QDialog.Accepted:
                new_config = editor.get_config()
                self.config_manager.save_config(new_config)
                self.config = self.config_manager.load_config()
                self.update_config_status()
                
                # Update dependent components
                if self.scheduler:
                    self.scheduler.stop()
                    self.scheduler = ScanScheduler(self.config)
                    
                self.statusBar().showMessage("Configuration updated")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Configuration error: {str(e)}")

    def toggle_scheduling(self, state):
        """Enable or disable scheduled scanning"""
        if state == Qt.Checked:
            self.scheduler.start()
            self.statusBar().showMessage("Scheduled scanning enabled")
        else:
            self.scheduler.stop()
            self.statusBar().showMessage("Scheduled scanning disabled")

    def update_scan_frequency(self, frequency):
        """Update the scan frequency in the scheduler"""
        self.scheduler.set_frequency(frequency)
        self.scheduler.start()  # Restart scheduler with updated frequency

    def update_scan_time(self, time):
        """Update the scan time in the scheduler"""
        self.scheduler.set_scan_time(time.toString("HH:mm"))
        self.scheduler.start()  # Restart scheduler with updated time

    def toggle_auto_email(self, state):
        """Enable or disable automatic email of reports"""
        self.scheduler.toggle_auto_email(state == Qt.Checked)

    def start_scan(self):
        """Start scanning for inactive users"""
        try:
            days = int(self.days_threshold_edit.text())
            self.worker = WorkerThread(self.config, days)
            self.worker.result.connect(self.scan_complete)
            self.worker.error.connect(self.scan_error)
            self.worker.start()
            
            self.scan_btn.setEnabled(False)
            self.progress_bar.setRange(0, 0)  # Indeterminate mode
            self.statusBar().showMessage("Scanning for inactive users...")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start scan: {str(e)}")

    def scan_complete(self, users):
        """Handles the completion of the scan and populates the table widget"""
        self.user_table.setRowCount(0)  # Clear table rows
        self.user_table.setSortingEnabled(False)  # Disable sorting during population

        for user in users:
            if isinstance(user, dict):
                upn = user.get('userPrincipalName', 'Unknown User')
                sign_in_activity = user.get('signInActivity', {})
                last_sign_in_raw = sign_in_activity.get('lastSignInDateTime') or \
                                   sign_in_activity.get('lastNonInteractiveSignInDateTime') or \
                                   "Never or No Data"

                last_sign_in_display = last_sign_in_raw
                if last_sign_in_raw and last_sign_in_raw != "Never or No Data":
                    try:
                        dt = datetime.datetime.strptime(last_sign_in_raw, "%Y-%m-%dT%H:%M:%SZ")
                        last_sign_in_display = dt.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
                    except ValueError:
                        last_sign_in_display = last_sign_in_raw

                account_enabled = user.get('accountEnabled', False)
                status = "Enabled" if account_enabled else "Disabled"

                row_position = self.user_table.rowCount()
                self.user_table.insertRow(row_position)

                # Create QTableWidgetItems
                upn_item = QTableWidgetItem(upn)
                signin_item = QTableWidgetItem(last_sign_in_display)
                status_item = QTableWidgetItem(status)

                # Store full user data in the row's first item (UPN) for later retrieval
                upn_item.setData(Qt.UserRole, user)

                # Apply styling for disabled users
                if not account_enabled:
                    disabled_color = QColor(Qt.gray)
                    upn_item.setForeground(QBrush(disabled_color))
                    signin_item.setForeground(QBrush(disabled_color))
                    status_item.setForeground(QBrush(disabled_color))

                # Add items to table
                self.user_table.setItem(row_position, 0, upn_item)
                self.user_table.setItem(row_position, 1, signin_item)
                self.user_table.setItem(row_position, 2, status_item)

        self.user_table.setSortingEnabled(True)  # Re-enable sorting
        self.update_column_widths()  # Adjust widths after populating

        # Stop progress bar, enable buttons, etc.
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.scan_btn.setEnabled(True)
        self.statusBar().showMessage(f"Scan complete. Found {len(users)} inactive users.")
        self.toggle_action_buttons(True)

    def scan_error(self, error):
        """Handle scan errors"""
        self.scan_btn.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Scan Error", error)
        self.statusBar().showMessage("Scan failed")

    def get_selected_users(self):
        """Get list of selected user principal names from the table."""
        selected_users = []
        selected_rows = set(index.row() for index in self.user_table.selectedIndexes())  # Get unique selected rows

        for row in selected_rows:
            upn_item = self.user_table.item(row, 0)  # UPN is in the first column
            if upn_item:
                selected_users.append(upn_item.text())
        return selected_users

    def enable_users(self):
        """Enable selected user accounts using batch processing."""
        users_to_enable = self.get_selected_users()  # Get UPNs
        if not users_to_enable:
            QMessageBox.warning(self, "Warning", "No users selected")
            return

        if QMessageBox.question(
            self, "Confirm Enable", f"Enable {len(users_to_enable)} selected accounts?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.No:
            return

        self.statusBar().showMessage(f"Attempting to enable {len(users_to_enable)} users...")
        self.progress_bar.setRange(0, 0)  # Indeterminate progress for batch
        QApplication.processEvents()  # Update UI

        try:
            api = APIClient(self.config)
            results = api.enable_users_batch(users_to_enable)  # Use batch method

            enabled_count = sum(1 for success in results.values() if success)
            failed_users = [upn for upn, success in results.items() if not success]

            # Update UI based on results
            for upn, success in results.items():
                items = self.user_table.findItems(upn, Qt.MatchExactly)
                if items:
                    item = items[0]
                    if success:
                        item.setForeground(Qt.black)  # Or your 'enabled' style
                    else:
                        item.setForeground(Qt.red)  # Indicate failure

            self.statusBar().showMessage(f"Enable operation complete. Successfully enabled {enabled_count}/{len(users_to_enable)} users.")
            if failed_users:
                QMessageBox.warning(self, "Enable Issues", f"Failed to enable the following users:\n" + "\n".join(failed_users))
            else:
                QMessageBox.information(self, "Complete", f"Successfully enabled {enabled_count} accounts.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to enable users: {str(e)}")
            self.statusBar().showMessage("Enable operation failed.")
        finally:
            self.progress_bar.setRange(0, 1)  # Reset progress bar
            self.progress_bar.setValue(1)

    def disable_users(self):
        """Disable selected user accounts using batch processing."""
        users_to_disable = self.get_selected_users()  # Get UPNs
        if not users_to_disable:
            QMessageBox.warning(self, "Warning", "No users selected")
            return

        if QMessageBox.question(
            self, "Confirm Disable", f"Disable {len(users_to_disable)} selected accounts?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.No:
            return

        self.statusBar().showMessage(f"Attempting to disable {len(users_to_disable)} users...")
        self.progress_bar.setRange(0, 0)  # Indeterminate progress for batch
        QApplication.processEvents()  # Update UI

        try:
            api = APIClient(self.config)
            results = api.disable_users_batch(users_to_disable)  # Use batch method

            disabled_count = sum(1 for success in results.values() if success)
            failed_users = [upn for upn, success in results.items() if not success]

            # Update UI based on results
            for upn, success in results.items():
                items = self.user_table.findItems(upn, Qt.MatchExactly)
                if items:
                    item = items[0]
                    if success:
                        item.setForeground(Qt.gray)  # Or your 'disabled' style
                    else:
                        item.setForeground(Qt.red)  # Indicate failure

            self.statusBar().showMessage(f"Disable operation complete. Successfully disabled {disabled_count}/{len(users_to_disable)} users.")
            if failed_users:
                QMessageBox.warning(self, "Disable Issues", f"Failed to disable the following users:\n" + "\n".join(failed_users))
            else:
                QMessageBox.information(self, "Complete", f"Successfully disabled {disabled_count} accounts.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to disable users: {str(e)}")
            self.statusBar().showMessage("Disable operation failed.")
        finally:
            self.progress_bar.setRange(0, 1)  # Reset progress bar
            self.progress_bar.setValue(1)

    def export_results(self):
        """Export results (all rows currently in the table) to CSV file"""
        users_data = []
        for row in range(self.user_table.rowCount()):
            upn_item = self.user_table.item(row, 0)
            if upn_item:
                user_data = upn_item.data(Qt.UserRole)
                if isinstance(user_data, dict):
                    users_data.append(user_data)
                else:
                    signin_item = self.user_table.item(row, 1)
                    status_item = self.user_table.item(row, 2)
                    users_data.append({
                        'userPrincipalName': upn_item.text(),
                        'signInActivity': {'lastSignInDateTime': signin_item.text() if signin_item else 'N/A'},
                        'accountEnabled': status_item.text() == 'Enabled' if status_item else False
                    })

        if not users_data:
            QMessageBox.warning(self, "No Data", "No results to export.")
            return

        try:
            days = int(self.days_threshold_edit.text())
            filename = ReportGenerator.generate_csv_report(users_data, days)
            QMessageBox.information(self, "Success", f"Report saved to {filename}")
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid Days Threshold value for report.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def email_report(self):
        """Email the scan results report containing all users currently listed."""
        logging.info("Attempting to email report...")
        users_data_for_report = []  # List to hold user dictionaries

        # --- CORRECT DATA COLLECTION ---
        logging.debug(f"Collecting user data from table with {self.user_table.rowCount()} rows.")
        for row in range(self.user_table.rowCount()):
            # Get the item from the first column (where user data should be stored)
            upn_item = self.user_table.item(row, 0)
            if upn_item:
                # Retrieve the full user dictionary stored in the item's data
                user_data = upn_item.data(Qt.UserRole)
                if isinstance(user_data, dict):
                    users_data_for_report.append(user_data)
                    logging.debug(f"Added user {user_data.get('userPrincipalName')} to email report list.")
                else:
                    logging.warning(f"Could not retrieve valid user data dictionary from row {row}, item data: {user_data}")
            else:
                logging.warning(f"Could not retrieve item from row {row}, column 0.")

        # --- CHECK IF DATA WAS COLLECTED ---
        if not users_data_for_report:
            logging.warning("No user data collected from the table to email.")
            QMessageBox.warning(self, "No Data", "No user data found in the results table to email.")
            return  # Stop here if no users were found in the table

        logging.info(f"Collected {len(users_data_for_report)} users from table for email report.")

        try:
            # Get the threshold value from the UI
            days = int(self.days_threshold_edit.text())

            # Generate the report using the collected list of dictionaries
            logging.debug("Generating CSV report for email...")
            report_file_path = ReportGenerator.generate_csv_report(users_data_for_report, days)
            logging.info(f"CSV report generated at: {report_file_path}")

            # Send the email with the generated report as an attachment
            logging.debug("Sending email...")
            ReportGenerator.send_email(self.config, report_file_path)
            logging.info("Email sent successfully.")
            QMessageBox.information(self, "Success", "Report emailed successfully!")

        except ValueError:
            logging.error(f"Invalid Days Threshold value: {self.days_threshold_edit.text()}")
            QMessageBox.critical(self, "Error", "Invalid 'Days Threshold' value entered.")
        except Exception as e:
            logging.exception("Failed to generate or email the report.")
            QMessageBox.critical(self, "Error", f"Email failed: {str(e)}")

    def filter_results_table(self, text):
        """Hide rows that do not match the filter text in UPN or Last Sign-in columns."""
        filter_text = text.lower()
        for row in range(self.user_table.rowCount()):
            upn_item = self.user_table.item(row, 0)
            signin_item = self.user_table.item(row, 1)
            match = False
            if upn_item and filter_text in upn_item.text().lower():
                match = True
            if not match and signin_item and filter_text in signin_item.text().lower():
                match = True

            self.user_table.setRowHidden(row, not match)

    def closeEvent(self, event):
        """Clean up when window closes"""
        if self.scheduler:
            self.scheduler.stop()
        event.accept()