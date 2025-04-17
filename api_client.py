import logging
import requests
import datetime
from typing import List, Dict
from PySide6.QtWidgets import QMessageBox
from urllib.parse import urlencode, quote  # Import quote for URL encoding
import os
import json  # Add json import
import time  # Add this import

class APIClient:
    def __init__(self, config):
        self.config = config
        self.access_token = None

    def get_access_token(self):
        """Add encryption check before authentication"""
        if not self.config.get('CLIENT_SECRET_ENCRYPTED'):
            QMessageBox.warning(
                None,
                "Security Warning",
                "Using unencrypted credentials - consider encrypting in settings"
            )
        
        """Authenticates with Microsoft Graph"""
        from security import SecurityManager  # Import at method level to avoid circular imports
        
        # Add pre-flight validation
        if not self.validate_credentials():
            raise ValueError("Invalid credentials configuration")
        
        # Debug logging for configuration
        print("Current Configuration:")
        print(f"Tenant ID: {self.config.get('TENANT_ID')}")
        print(f"Client ID: {self.config.get('CLIENT_ID')}")
        print(f"Client Secret exists: {'CLIENT_SECRET' in self.config}")
        print(f"Client Secret encrypted: {self.config.get('CLIENT_SECRET_ENCRYPTED', False)}")
        
        # Handle client secret decryption
        if 'CLIENT_SECRET_ENCRYPTED' in self.config:
            try:
                security_manager = SecurityManager()
                decrypted_secret = security_manager.decrypt(self.config['CLIENT_SECRET'])
                print("Successfully decrypted client secret")
                client_secret = decrypted_secret
            except Exception as e:
                print(f"Decryption failed: {str(e)}")
                raise Exception(f"Failed to decrypt client secret: {str(e)}")
        else:
            print("Using unencrypted client secret")
            client_secret = self.config.get('CLIENT_SECRET')

        # Validate client secret
        if not client_secret:
            raise ValueError("Client secret is empty or invalid")
        if len(client_secret) < 10:  # Azure client secrets are typically longer
            raise ValueError("Client secret appears to be invalid")

        # Prepare token request with proper URL encoding
        url = f"https://login.microsoftonline.com/{self.config['TENANT_ID']}/oauth2/v2.0/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        body = urlencode({
            'client_id': self.config['CLIENT_ID'],
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        })

        # Debug logging for request
        print(f"Client ID: {self.config['CLIENT_ID']} (length: {len(self.config['CLIENT_ID'])})")
        print("Client Secret: [REDACTED] (encrypted)" if self.config.get('CLIENT_SECRET_ENCRYPTED') else "Client Secret: [REDACTED]")
        print(f"Tenant ID: {self.config['TENANT_ID']} (length: {len(self.config['TENANT_ID'])})")

        if os.getenv("DEBUG_CREDENTIALS"):
            print(f"Request Body: {body}")  # Only show full details in debug mode
        else:
            print("Request Body: [REDACTED]")
            print(f"Client ID: {self.config['CLIENT_ID']}")
            print("Client Secret: [present but redacted]")

        # Send request and log response
        response = requests.post(url, headers=headers, data=body)
        print("Response Status:", response.status_code)
        print("Response Body:", response.text)  # This will show Azure AD's error message
        response.raise_for_status()

        return response.json()['access_token']

    def validate_credentials(self):
        """Validate credential format before attempting authentication"""
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

        if not uuid_pattern.match(self.config['CLIENT_ID']):
            print(f"Invalid Client ID format: {self.config['CLIENT_ID']}")
            return False

        if not uuid_pattern.match(self.config['TENANT_ID']):
            print(f"Invalid Tenant ID format: {self.config['TENANT_ID']}")
            return False

        if not self.config.get('CLIENT_SECRET'):
            print("Client Secret is missing")
            return False

        return True

    def get_all_users(self) -> List[Dict]:
        """Fetches all enabled users with sign-in activity and a last interactive sign-in time"""
        users = []
        url = f"{self.config['GRAPH_API_URL']}/users?$select=userPrincipalName,signInActivity,accountEnabled"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        while url:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            if response.status_code == 200:
                # Filter only enabled accounts with a last interactive sign-in time
                filtered_users = [
                    user for user in data.get('value', [])
                    if user.get('accountEnabled', False) and user.get('signInActivity', {}).get('lastNonInteractiveSignInDateTime')
                ]
                users.extend(filtered_users)
                url = data.get('@odata.nextLink')
            elif response.status_code == 429:
                datetime.time.sleep(int(response.headers.get('Retry-After', 30)))
            else:
                response.raise_for_status()
        
        return users

    def find_inactive_users(self, days_threshold: int) -> List[Dict]:
        """
        Identifies inactive users by fetching enabled users and filtering locally.
        Workaround for API filter limitations.
        """
        if not self.access_token:
            self.access_token = self.get_access_token()  # Ensure token exists

        all_enabled_users = []
        url = f"{self.config['GRAPH_API_URL']}/users?$filter=accountEnabled eq true&$select=userPrincipalName,signInActivity,accountEnabled,id"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        logging.info(f"Fetching enabled users from: {url}")

        while url:
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 429:  # Handle rate limiting
                    retry_after = int(response.headers.get('Retry-After', 30))
                    logging.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                all_enabled_users.extend(data.get('value', []))
                url = data.get('@odata.nextLink')  # Get next page link

            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Error fetching users: {e.response.status_code} - {e.response.text}")
                if e.response.status_code in [401, 403]:
                    raise Exception(f"Authentication/Authorization error: {e.response.text}") from e
                break
            except Exception as e:
                logging.exception("An unexpected error occurred during user fetching.")
                raise

        logging.info(f"Fetched {len(all_enabled_users)} enabled users. Now filtering locally.")
        inactive_users = []
        current_date = datetime.datetime.now(datetime.timezone.utc)
        threshold_delta = datetime.timedelta(days=days_threshold)

        for user in all_enabled_users:
            if not isinstance(user, dict):
                logging.warning(f"Skipping invalid user entry: {user}")
                continue

            sign_in_activity = user.get('signInActivity', {})
            last_sign_in_str = sign_in_activity.get('lastSignInDateTime') or \
                               sign_in_activity.get('lastNonInteractiveSignInDateTime')

            is_inactive = False
            if not last_sign_in_str:
                is_inactive = True
                logging.debug(f"User {user.get('userPrincipalName')} marked inactive (no sign-in data).")
            else:
                try:
                    last_sign_in_date = datetime.datetime.strptime(last_sign_in_str, "%Y-%m-%dT%H:%M:%SZ")
                    last_sign_in_date = last_sign_in_date.replace(tzinfo=datetime.timezone.utc)
                    if (current_date - last_sign_in_date) > threshold_delta:
                        is_inactive = True
                        logging.debug(f"User {user.get('userPrincipalName')} marked inactive (last sign-in {last_sign_in_str} > {days_threshold} days ago).")
                except ValueError:
                    logging.warning(f"Could not parse sign-in date '{last_sign_in_str}' for user {user.get('userPrincipalName')}")

            if is_inactive:
                inactive_users.append(user)

        logging.info(f"Found {len(inactive_users)} inactive users after local filtering.")
        return inactive_users

    def disable_user(self, user_principal_name: str) -> bool:
        """Disables an Azure AD user account"""
        if not self.access_token:
            self.access_token = self.get_access_token()
    
        # First get the user's object ID
        user_id = self._get_user_id(user_principal_name)
        if not user_id:
            return False
        
        # Prepare the update payload to disable the account
        url = f"{self.config['GRAPH_API_URL']}/users/{user_id}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "accountEnabled": False
        }
        
        try:
            response = requests.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error disabling user {user_principal_name}: {str(e)}")
            return False
    
    def _get_user_id(self, user_principal_name: str) -> str:
        """Gets the object ID for a user principal name"""
        url = f"{self.config['GRAPH_API_URL']}/users/{user_principal_name}?$select=id"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get('id')
        except Exception as e:
            print(f"Error getting user ID for {user_principal_name}: {str(e)}")
            return None

    def _perform_batch_action(self, user_ids: List[str], action_payload: Dict) -> Dict[str, bool]:
        """Performs a batch action (e.g., disable, enable) on multiple users."""
        if not self.access_token:
            self.access_token = self.get_access_token()

        batch_url = f"{self.config['GRAPH_API_URL']}/$batch"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        results = {}
        batch_limit = 20  # Graph API batch limit

        for i in range(0, len(user_ids), batch_limit):
            batch_requests = []
            current_batch_ids = user_ids[i:i + batch_limit]

            for user_id in current_batch_ids:
                request_id = user_id  # Use user_id as a unique identifier for the request within the batch
                batch_requests.append({
                    "id": request_id,
                    "method": "PATCH",
                    "url": f"/users/{user_id}",
                    "headers": {"Content-Type": "application/json"},
                    "body": action_payload
                })

            batch_payload = {"requests": batch_requests}

            try:
                response = requests.post(batch_url, headers=headers, json=batch_payload)
                response.raise_for_status()
                batch_response = response.json()

                for resp in batch_response.get('responses', []):
                    original_request_id = resp.get('id')  # This matches the user_id we set
                    status_code = resp.get('status')
                    # Assume success if status is 200-299 (specifically 204 No Content for PATCH)
                    results[original_request_id] = 200 <= status_code < 300
                    if not (200 <= status_code < 300):
                        print(f"Batch Error for user ID {original_request_id}: Status {status_code}, Body: {resp.get('body')}")

            except requests.exceptions.RequestException as e:
                print(f"Batch request failed: {str(e)}")
                # Mark all users in this failed batch as unsuccessful
                for user_id in current_batch_ids:
                    results[user_id] = False
            except Exception as e:
                print(f"Unexpected error during batch processing: {str(e)}")
                for user_id in current_batch_ids:
                    results[user_id] = False

        return results

    def disable_users_batch(self, user_principal_names: List[str]) -> Dict[str, bool]:
        """Disables multiple users using batch requests and returns status for each UPN."""
        upn_to_id_map = {}
        user_ids_to_disable = []
        results_by_upn = {upn: False for upn in user_principal_names}  # Default to False

        # 1. Get User IDs
        for upn in user_principal_names:
            user_id = self._get_user_id(upn)
            if user_id:
                upn_to_id_map[user_id] = upn
                user_ids_to_disable.append(user_id)
            else:
                results_by_upn[upn] = False  # Failed to get ID

        if not user_ids_to_disable:
            return results_by_upn

        # 2. Perform Batch Disable
        disable_payload = {"accountEnabled": False}
        batch_results_by_id = self._perform_batch_action(user_ids_to_disable, disable_payload)

        # 3. Map results back to UPNs
        for user_id, success in batch_results_by_id.items():
            upn = upn_to_id_map.get(user_id)
            if upn:
                results_by_upn[upn] = success

        return results_by_upn

    def enable_users_batch(self, user_principal_names: List[str]) -> Dict[str, bool]:
        """Enables multiple users using batch requests and returns status for each UPN."""
        upn_to_id_map = {}
        user_ids_to_enable = []
        results_by_upn = {upn: False for upn in user_principal_names}

        # 1. Get User IDs
        for upn in user_principal_names:
            user_id = self._get_user_id(upn)
            if user_id:
                upn_to_id_map[user_id] = upn
                user_ids_to_enable.append(user_id)
            else:
                results_by_upn[upn] = False

        if not user_ids_to_enable:
            return results_by_upn

        # 2. Perform Batch Enable
        enable_payload = {"accountEnabled": True}
        batch_results_by_id = self._perform_batch_action(user_ids_to_enable, enable_payload)

        # 3. Map results back to UPNs
        for user_id, success in batch_results_by_id.items():
            upn = upn_to_id_map.get(user_id)
            if upn:
                results_by_upn[upn] = success

        return results_by_upn

    def enable_user(self, user_principal_name: str) -> bool:
        """Re-enables a disabled Azure AD user account"""
        if not self.access_token:
            self.access_token = self.get_access_token()
        
        user_id = self._get_user_id(user_principal_name)
        if not user_id:
            return False
        
        url = f"{self.config['GRAPH_API_URL']}/users/{user_id}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        payload = {"accountEnabled": True}
        
        try:
            response = requests.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error enabling user {user_principal_name}: {str(e)}")
            return False

    def get_account_status(self, user_principal_name: str) -> bool:
        """Checks if a user account is enabled"""
        user_id = self._get_user_id(user_principal_name)
        if not user_id:
            return False
            
        url = f"{self.config['GRAPH_API_URL']}/users/{user_id}?$select=accountEnabled"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            return response.json().get('accountEnabled', False)
        except Exception as e:
            print(f"Error getting status for {user_principal_name}: {str(e)}")
            return False