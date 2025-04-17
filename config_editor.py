from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QSpinBox, QPushButton, QMessageBox,
    QTabWidget, QWidget, QTextEdit, QCheckBox, QLabel
)
from PySide6.QtCore import Qt
import json

class ConfigEditor(QDialog):
    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration Editor")
        self.setMinimumSize(600, 400)
        
        self.config_data = config_data.copy()
        self.original_config = config_data.copy()
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Tab widget for different sections
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Main Configuration Tab
        main_tab = QWidget()
        main_layout = QFormLayout()
        main_tab.setLayout(main_layout)
        tabs.addTab(main_tab, "Main Settings")

        # Azure AD Settings
        self.tenant_id_edit = QLineEdit(self.config_data.get('TENANT_ID', ''))
        self.tenant_id_edit.setToolTip("The Azure AD Tenant ID (GUID format).")
        self.client_id_edit = QLineEdit(self.config_data.get('CLIENT_ID', ''))
        self.client_id_edit.setToolTip("The Azure AD Application (Client) ID.")

        # Only show secret field if not encrypted or if we want to change its
        if 'CLIENT_SECRET_ENCRYPTED' not in self.config_data or not self.config_data.get('CLIENT_SECRET_ENCRYPTED'):
            self.client_secret_edit = QLineEdit(self.config_data.get('CLIENT_SECRET', ''))
            self.client_secret_edit.setEchoMode(QLineEdit.Password)
            self.client_secret_edit.setToolTip("The Azure AD Application Client Secret.")
            main_layout.addRow("Client Secret:", self.client_secret_edit)
        else:
            # Initialize with empty QLineEdit but don't add to layout
            self.client_secret_edit = QLineEdit()
            self.client_secret_edit.setEchoMode(QLineEdit.Password)

        secret_status = "✔ Encrypted" if 'CLIENT_SECRET_ENCRYPTED' in self.config_data else "✖ Not Encrypted"
        self.secret_status_label = QLabel(secret_status)
        self.secret_status_label.setToolTip("Indicates if the Client Secret is stored encrypted.")

        main_layout.addRow("Tenant ID:", self.tenant_id_edit)
        main_layout.addRow("Client ID:", self.client_id_edit)
        main_layout.addRow("Client Secret Status:", self.secret_status_label)
        
        # API Settings
        self.graph_url_edit = QLineEdit(self.config_data.get('GRAPH_API_URL', 'https://graph.microsoft.com/v1.0'))
        self.graph_url_edit.setToolTip("The Microsoft Graph API base URL.")
        self.days_threshold_edit = QSpinBox()
        self.days_threshold_edit.setRange(1, 365)
        self.days_threshold_edit.setValue(self.config_data.get('DAYS_TO_SEARCH_BEYOND', 90))
        self.days_threshold_edit.setToolTip("Number of days of inactivity before a user is listed.")
        
        main_layout.addRow("Graph API URL:", self.graph_url_edit)
        main_layout.addRow("Inactivity Threshold (days):", self.days_threshold_edit)
        
        # Email Settings Tab
        email_tab = QWidget()
        email_layout = QFormLayout()
        email_tab.setLayout(email_layout)
        tabs.addTab(email_tab, "Email Settings")
        
        self.sender_email_edit = QLineEdit(self.config_data.get('sender_email', ''))
        self.sender_email_edit.setToolTip("The email address used to send reports (e.g., service_account@example.com).")
        self.receiver_email_edit = QLineEdit(self.config_data.get('receiver_email', ''))
        self.receiver_email_edit.setToolTip("The email address where reports will be sent (e.g., admin@example.com).")
        self.smtp_server_edit = QLineEdit(self.config_data.get('smtp_server', 'smtp.office365.com'))
        self.smtp_server_edit.setToolTip("The SMTP server address (e.g., smtp.office365.com).")
        self.smtp_port_edit = QSpinBox()
        self.smtp_port_edit.setRange(1, 65535)
        self.smtp_port_edit.setValue(self.config_data.get('smtp_port', 587))
        self.smtp_port_edit.setToolTip("The SMTP server port (e.g., 587 for TLS, 465 for SSL).")
        self.email_subject_edit = QLineEdit(self.config_data.get('email_subject', 'Inactive Users Report'))
        self.email_subject_edit.setToolTip("The subject line for the email report.")
        
        email_layout.addRow("Sender Email:", self.sender_email_edit)
        email_layout.addRow("Receiver Email:", self.receiver_email_edit)
        email_layout.addRow("SMTP Server:", self.smtp_server_edit)
        email_layout.addRow("SMTP Port:", self.smtp_port_edit)
        email_layout.addRow("Email Subject:", self.email_subject_edit)
        
        # Add SMTP password field
        self.smtp_password_edit = QLineEdit()
        self.smtp_password_edit.setEchoMode(QLineEdit.Password)
        self.smtp_password_edit.setPlaceholderText("(optional)")
        self.smtp_password_edit.setToolTip("Password for the Sender Email account if SMTP server requires authentication. Can be encrypted.")
        if 'smtp_password' in self.config_data:
            if self.config_data.get('smtp_password_encrypted', False):
                self.smtp_password_edit.setPlaceholderText("(encrypted - enter new value to change)")
            else:
                self.smtp_password_edit.setText(self.config_data['smtp_password'])
        email_layout.addRow("SMTP Password (optional):", self.smtp_password_edit)
        
        # Add encryption button for SMTP password
        self.encrypt_smtp_btn = QPushButton("Encrypt SMTP Password")
        self.encrypt_smtp_btn.clicked.connect(self._encrypt_smtp_password)
        self.encrypt_smtp_btn.setToolTip("Encrypt the entered SMTP password before saving.")
        email_layout.addRow(self.encrypt_smtp_btn)
        
        # Advanced Tab
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout()
        advanced_tab.setLayout(advanced_layout)
        tabs.addTab(advanced_tab, "Advanced")
        
        # Add warning label
        warning_label = QLabel(
            "Warning: Editing sensitive fields here will overwrite existing values.\n"
            "For security, encrypted fields will be shown as empty."
        )
        warning_label.setStyleSheet("color: red;")
        advanced_layout.addWidget(warning_label)

        # Create a sanitized version for display
        display_config = self.config_data.copy()
        if 'CLIENT_SECRET' in display_config:
            display_config['CLIENT_SECRET'] = '' if display_config.get('CLIENT_SECRET_ENCRYPTED') else display_config['CLIENT_SECRET']
        if 'smtp_password' in display_config:
            display_config['smtp_password'] = '' if display_config.get('smtp_password_encrypted') else display_config['smtp_password']
        if 'smtp_password' in display_config and not display_config['smtp_password']:
            del display_config['smtp_password']
            display_config.pop('smtp_password_encrypted', None)

        self.raw_config_edit = QTextEdit()
        self.raw_config_edit.setPlainText(json.dumps(display_config, indent=2))
        advanced_layout.addWidget(self.raw_config_edit)

        # Add button to reveal/hide secrets
        self.toggle_secrets_btn = QPushButton("Show Encrypted Fields")
        self.toggle_secrets_btn.setCheckable(True)
        self.toggle_secrets_btn.toggled.connect(self.toggle_secret_display)
        advanced_layout.addWidget(self.toggle_secrets_btn)

        # Warning label for raw editor
        self.raw_warning = QLabel("Note: Sensitive fields are not shown in raw editor")
        self.raw_warning.setStyleSheet("color: orange;")
        advanced_layout.addWidget(self.raw_warning)

        # Test encryption button
        self.test_encryption_btn = QPushButton("Test Encryption")
        self.test_encryption_btn.clicked.connect(self._test_encryption)
        advanced_layout.addWidget(self.test_encryption_btn)

        # Button Row
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
            
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        # Add encryption button for client secret
        self.encrypt_btn = QPushButton("Encrypt Client Secret")
        self.encrypt_btn.clicked.connect(lambda: self._encrypt_secret(self.config_data))
        button_layout.addWidget(self.encrypt_btn)
    
    def toggle_secret_display(self, show):
        """Toggle display of sensitive fields"""
        current_text = self.raw_config_edit.toPlainText()
        try:
            config = json.loads(current_text)
            if show:
                # Show actual values
                if 'CLIENT_SECRET' in self.config_data:
                    config['CLIENT_SECRET'] = self.config_data['CLIENT_SECRET']
                if 'smtp_password' in self.config_data:
                    config['smtp_password'] = self.config_data['smtp_password']
                self.toggle_secrets_btn.setText("Hide Encrypted Fields")
            else:
                # Hide sensitive values
                if 'CLIENT_SECRET' in config:
                    config['CLIENT_SECRET'] = '[ENCRYPTED]' if self.config_data.get('CLIENT_SECRET_ENCRYPTED') else ''
                if 'smtp_password' in config:
                    config['smtp_password'] = '[ENCRYPTED]' if self.config_data.get('smtp_password_encrypted') else ''
                self.toggle_secrets_btn.setText("Show Encrypted Fields")

            self.raw_config_edit.setPlainText(json.dumps(config, indent=2))
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "Invalid JSON content")

    def save_config(self):
        """Saves configuration with robust field handling."""
        try:
            # Strip ALL non-alphanumeric characters from Client ID (except hyphens for UUID)
            client_id = self.client_id_edit.text().strip()
            client_id = ''.join(c for c in client_id if c.isalnum() or c == '-')

            new_config = {
                'TENANT_ID': self.tenant_id_edit.text().strip(),
                'CLIENT_ID': client_id,  # Use sanitized Client ID
                'GRAPH_API_URL': self.graph_url_edit.text().strip(),
                'DAYS_TO_SEARCH_BEYOND': self.days_threshold_edit.value(),
                'sender_email': self.sender_email_edit.text().strip(),
                'receiver_email': self.receiver_email_edit.text().strip(),
                'smtp_server': self.smtp_server_edit.text().strip(),
                'smtp_port': self.smtp_port_edit.value(),
                'email_subject': self.email_subject_edit.text().strip()
            }

            # Preserve existing encrypted secret if not being changed
            if 'CLIENT_SECRET_ENCRYPTED' in self.config_data and self.config_data['CLIENT_SECRET_ENCRYPTED']:
                new_config['CLIENT_SECRET'] = self.config_data['CLIENT_SECRET']
                new_config['CLIENT_SECRET_ENCRYPTED'] = True
            # Handle new secret if entered
            elif self.client_secret_edit.text():
                new_config['CLIENT_SECRET'] = self.client_secret_edit.text()
                if 'CLIENT_SECRET_ENCRYPTED' in new_config:
                    del new_config['CLIENT_SECRET_ENCRYPTED']

            # Add validation specifically for Client ID format
            if not self.validate_client_id(client_id):
                QMessageBox.critical(self, "Invalid Client ID", 
                                     "Client ID must be a valid UUID format")
                return

            # Handle SMTP password
            if hasattr(self, '_temp_encrypted_smtp') and self._temp_encrypted_smtp:
                new_config['smtp_password'] = self._temp_encrypted_smtp
                new_config['smtp_password_encrypted'] = True
                del self._temp_encrypted_smtp  # Clear temporary attribute
            elif self.smtp_password_edit.isEnabled() and self.smtp_password_edit.text():
                smtp_pass = self.smtp_password_edit.text()
                new_config['smtp_password'] = smtp_pass
                if 'smtp_password_encrypted' in new_config:
                    del new_config['smtp_password_encrypted']  # Save as plain text
            elif 'smtp_password' in self.config_data and 'smtp_password_encrypted' in self.config_data:
                # Preserve existing encrypted password if field wasn't touched
                new_config['smtp_password'] = self.config_data['smtp_password']
                new_config['smtp_password_encrypted'] = True
            else:
                # No password provided or existing, remove keys
                new_config.pop('smtp_password', None)
                new_config.pop('smtp_password_encrypted', None)

            # Handle raw JSON edits carefully
            if self.raw_config_edit.isVisible():
                try:
                    raw_config = json.loads(self.raw_config_edit.toPlainText())
                    # Only update non-sensitive fields from raw edit
                    for k, v in raw_config.items():
                        if k not in ['CLIENT_SECRET', 'smtp_password', 
                                     'CLIENT_SECRET_ENCRYPTED', 'smtp_password_encrypted']:
                            new_config[k] = v
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "Invalid JSON", "Using form values instead")

            # Validate before saving
            if not self.validate_before_save(new_config):
                return

            # Handle encryption state consistently
            if (new_config.get('CLIENT_SECRET') and 
                not new_config.get('CLIENT_SECRET_ENCRYPTED') and
                'CLIENT_SECRET_ENCRYPTED' not in self.config_data):
                
                response = QMessageBox.question(
                    self, "Encrypt Secret?",
                    "Would you like to encrypt the client secret?\n\n"
                    "Recommended for security. No will save in plain text.",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if response == QMessageBox.Yes:
                    if not self._encrypt_secret(new_config):
                        return
                elif response == QMessageBox.Cancel:
                    return

            # Update and accept
            self.config_data.update(new_config)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")
            if hasattr(self, '_temp_encrypted_smtp'):
                del self._temp_encrypted_smtp  # Clear temp state on error

    def validate_client_id(self, client_id):
        """Validate Client ID is proper UUID format"""
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        return bool(uuid_pattern.match(client_id))

    def validate_before_save(self, config):
        """Validate critical configuration fields"""
        errors = []

        if not config.get('TENANT_ID'):
            errors.append("Tenant ID is required")
        if not config.get('CLIENT_ID'):
            errors.append("Client ID is required")

        # Only require client secret if not encrypted
        if 'CLIENT_SECRET' not in config and not config.get('CLIENT_SECRET_ENCRYPTED'):
            errors.append("Client Secret is required")

        if errors:
            QMessageBox.critical(self, "Validation Error", "\n".join(errors))
            return False
        return True

    def _encrypt_secret(self, config):
        """Handles actual encryption process"""
        from security import SecurityManager
        try:
            security_manager = SecurityManager()
            encrypted = security_manager.encrypt(config['CLIENT_SECRET'])
            
            # Update both the secret and encryption flag
            config['CLIENT_SECRET'] = encrypted
            config['CLIENT_SECRET_ENCRYPTED'] = True
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Encryption Failed", 
                                 f"Could not encrypt secret: {str(e)}\n"
                                 "Save without encryption?")
            return False

    def _encrypt_smtp_password(self):
        """Prepare SMTP password for encryption without immediate saving."""
        password = self.smtp_password_edit.text()
        if not password:
            QMessageBox.warning(self, "No Password", "Enter an SMTP password to encrypt.")
            return
        try:
            from security import SecurityManager
            security_manager = SecurityManager()
            encrypted_password = security_manager.encrypt(password)

            # Temporarily store the encrypted password
            self._temp_encrypted_smtp = encrypted_password

            self.smtp_password_edit.setPlaceholderText("✔ Will be saved encrypted")
            self.smtp_password_edit.clear()
            self.smtp_password_edit.setEnabled(False)  # Prevent further editing
            self.encrypt_smtp_btn.setEnabled(False)  # Disable button after use

            QMessageBox.information(self, "Ready to Encrypt",
                                    "SMTP password will be encrypted when you click Save.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to prepare encryption: {str(e)}")
            self._temp_encrypted_smtp = None  # Clear temp value on error

    def _test_encryption(self):
        """Test encryption/decryption roundtrip"""
        from security import SecurityManager
        try:
            if SecurityManager().test_encryption():
                QMessageBox.information(self, "Success", "Encryption/decryption working correctly")
            else:
                QMessageBox.critical(self, "Error", "Encryption test failed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Encryption test failed: {str(e)}")

    def showEvent(self, event):
        """Reset temporary state when dialog is shown."""
        super().showEvent(event)
        if hasattr(self, '_temp_encrypted_smtp'):
            del self._temp_encrypted_smtp  # Clear temp state on show

        # Reset password field state based on loaded config
        self.smtp_password_edit.setEnabled(True)
        self.encrypt_smtp_btn.setEnabled(True)
        if self.config_data.get('smtp_password_encrypted'):
            self.smtp_password_edit.setPlaceholderText("(encrypted - enter new value to change)")
            self.smtp_password_edit.clear()
        else:
            self.smtp_password_edit.setText(self.config_data.get('smtp_password', ''))
            self.smtp_password_edit.setPlaceholderText("(optional)")

        # Refresh encryption button state
        if 'CLIENT_SECRET' in self.config_data or 'CLIENT_SECRET_ENCRYPTED' in self.config_data:
            self.encrypt_btn.setEnabled(True)
        else:
            self.encrypt_btn.setEnabled(False)
        # Update secret status
        secret_status = "✔ Encrypted" if 'CLIENT_SECRET_ENCRYPTED' in self.config_data else "✖ Not Encrypted"
        self.secret_status_label.setText(secret_status)

    def get_config(self):
        """Returns the edited configuration"""
        return self.config_data

    def is_config_valid(self) -> bool:
        """Validate configuration including secret state"""
        try:
            config = self.load_config()
            has_valid_creds = all(key in config for key in ["TENANT_ID", "CLIENT_ID"])
            has_valid_secret = ('CLIENT_SECRET' in config) ^ ('CLIENT_SECRET_ENCRYPTED' in config)
            return has_valid_creds and has_valid_secret
        except Exception:
            return False

    def update_config_status(self):
        """Update the UI to reflect the current configuration status"""
        # Update SMTP authentication status
        smtp_status = "✔ Configured" if 'smtp_password' in self.config_data else "✖ No auth"
        self.smtp_status_label.setText(f"SMTP: {smtp_status}")