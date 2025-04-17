import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import datetime
import logging

class ReportGenerator:
    @staticmethod
    def generate_csv_report(inactive_users: list, days_threshold: int) -> str:
        """Generates CSV report using accountEnabled status from user data."""
        # Add date to filename for uniqueness
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"InactiveUsersReport_{timestamp}.csv"
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days_threshold)).strftime('%Y-%m-%d')

        with open(filename, 'w', newline='', encoding='utf-8') as file:  # Added encoding
            writer = csv.writer(file)
            writer.writerow([f"Inactive users report (Sign-in older than {days_threshold} days - as of {today})"])
            writer.writerow(['User Principal Name', 'Status', 'Last Sign-In (UTC)'])  # Clarified header

            for user in inactive_users:
                if not isinstance(user, dict):
                    # Log this issue instead of raising, skip the user
                    logging.warning(f"Skipping invalid user entry in report generation: {type(user)}: {user}")
                    continue

                upn = user.get('userPrincipalName', 'N/A')
                # Determine status from the user object itself
                status = "Disabled" if not user.get('accountEnabled', True) else "Enabled"

                # Consistent check for last sign-in date
                sign_in_activity = user.get('signInActivity', {})
                last_sign_in = sign_in_activity.get('lastSignInDateTime') or \
                               sign_in_activity.get('lastNonInteractiveSignInDateTime') or \
                               'Never or No Data'

                writer.writerow([upn, status, last_sign_in])

        logging.info(f"Generated CSV report: {filename}")
        return filename

    @staticmethod
    def send_email(config: dict, attachment_path: str):
        """Sends report via email."""
        try:
            msg = MIMEMultipart()
            msg['From'] = config['sender_email']
            msg['To'] = config['receiver_email']
            msg['Subject'] = config.get('email_subject', 'Inactive Users Report')
            
            body = config.get('email_body', 'Please find attached inactive users report.')
            msg.attach(MIMEText(body, 'plain'))
            
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
            msg.attach(part)
            
            # Check if we should authenticate
            should_authenticate = 'smtp_password' in config and config['smtp_password']

            with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
                server.starttls()

                if should_authenticate:
                    password = config['smtp_password']
                    if config.get('smtp_password_encrypted', False):
                        from security import SecurityManager
                        password = SecurityManager().decrypt(password)
                    server.login(config['sender_email'], password)

                server.send_message(msg)
                logging.info(f"Email sent successfully to {config['receiver_email']}.")
        except Exception as e:
            logging.error(f"Email failed: {str(e)}")
            if not should_authenticate:
                raise Exception("Email failed. Server requires authentication but no password was configured.")
            raise Exception(f"Email failed: {str(e)}")