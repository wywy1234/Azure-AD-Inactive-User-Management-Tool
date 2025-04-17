import json
import os
import logging
from typing import Dict, Optional
from PySide6.QtWidgets import QMessageBox

logging.basicConfig(filename='app.log', level=logging.INFO)

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.default_config = {
            "TENANT_ID": "",
            "CLIENT_ID": "",
            "GRAPH_API_URL": "https://graph.microsoft.com/v1.0",
            "DAYS_TO_SEARCH_BEYOND": 90,
            "sender_email": "",
            "receiver_email": "",
            "smtp_server": "smtp.office365.com",
            "smtp_port": 587,
            "email_subject": "Inactive Users Report",
            "auto_schedule": False,
            "schedule_time": "09:00",
            "auto_email": False
        }

    def load_config(self) -> Dict:
        """Load configuration with comprehensive error handling"""
        try:
            # Create default config if missing
            if not os.path.exists(self.config_path):
                self.create_default_config()
                return self.default_config

            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Validate critical fields
            if not isinstance(config, dict):
                raise ValueError("Config must be a JSON object")

            # Merge with defaults but preserve existing sensitive values
            merged_config = self.default_config.copy()
            for key, value in config.items():
                # Preserve existing encrypted values
                if key in ['CLIENT_SECRET', 'smtp_password']:
                    merged_config[key] = value
                # Preserve encryption flags
                elif key in ['CLIENT_SECRET_ENCRYPTED', 'smtp_password_encrypted']:
                    merged_config[key] = value
                # Merge other values
                else:
                    merged_config[key] = value

            # Clean up SMTP password if empty
            if 'smtp_password' in merged_config and not merged_config['smtp_password']:
                del merged_config['smtp_password']
                merged_config.pop('smtp_password_encrypted', None)

            # Sanitize Client ID on load
            if 'CLIENT_ID' in merged_config:
                client_id = merged_config['CLIENT_ID']
                # Remove all non-UUID characters
                merged_config['CLIENT_ID'] = ''.join(c for c in client_id if c.isalnum() or c == '-')

            logging.info(f"Config loaded from {self.config_path}")
            logging.info(f"Client secret {'encrypted' if 'CLIENT_SECRET_ENCRYPTED' in config else 'unencrypted'}")
            logging.info(f"Loaded Client ID: '{merged_config.get('CLIENT_ID')}'")
            logging.info(f"Client ID length: {len(merged_config.get('CLIENT_ID', ''))}")
            return merged_config
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in {self.config_path}, using defaults")
            return self.default_config
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            raise

    def create_default_config(self) -> None:
        """Create a new config file with default values"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.default_config, f, indent=2)
            print(f"Created new config file at {self.config_path}")
        except Exception as e:
            print(f"Failed to create config: {str(e)}")

    def save_config(self, config_data: Dict) -> bool:
        """Save configuration to file with error handling"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save config: {str(e)}")
            return False

    def config_exists(self) -> bool:
        """Check if config file exists"""
        return os.path.exists(self.config_path)

    def is_config_valid(self) -> bool:
        """Basic validation of required fields"""
        try:
            config = self.load_config()
            return all(key in config for key in ["TENANT_ID", "CLIENT_ID"])
        except Exception:
            return False

    def encrypt_credentials(self) -> bool:
        """Encrypt credentials if unencrypted secret exists"""
        from security import SecurityManager
        
        try:
            config = self.load_config()
            
            # Check if already encrypted
            if config.get('CLIENT_SECRET_ENCRYPTED'):
                raise ValueError("Credentials are already encrypted")
                
            if not config.get('CLIENT_SECRET'):
                raise ValueError("No client secret to encrypt")

            # Perform actual encryption
            security_manager = SecurityManager()    
            encrypted_secret = security_manager.encrypt(config['CLIENT_SECRET'])
            
            # Update configuration
            config['CLIENT_SECRET_ENCRYPTED'] = True
            config['CLIENT_SECRET'] = encrypted_secret
            
            return self.save_config(config)
            
        except Exception as e:
            raise RuntimeError(f"Encryption failed: {str(e)}")