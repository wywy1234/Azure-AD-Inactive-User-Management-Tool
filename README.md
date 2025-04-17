# Azure AD Inactive User Scanner & Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) <!-- Update License if needed -->
<!-- Add other badges if applicable (e.g., build status) -->

A desktop application built with Python and PySide6 (Qt) to scan Microsoft Azure Active Directory (Azure AD) for inactive user accounts based on their last sign-in date. It provides a graphical user interface (GUI) to view, manage (enable/disable), and report on these users.

<!-- Add a screenshot of the main application window -->
<!-- ![App Screenshot](path/to/screenshot.png) -->

## Overview

Managing stale user accounts is crucial for security and license optimization. This tool helps administrators identify users who haven't signed in for a configurable period, allowing for review and potential disabling or deletion. It utilizes the Microsoft Graph API for querying user data and performing actions.

## Features

*   **Inactive User Detection:** Scans Azure AD for users whose last sign-in (interactive or non-interactive) exceeds a specified number of days.
*   **Graphical User Interface (GUI):** Easy-to-use interface built with PySide6.
*   **Configuration Management:**
    *   Securely stores Azure AD App credentials (Tenant ID, Client ID, Client Secret).
    *   **Credential Encryption:** Encrypts the Client Secret (and optional SMTP password) using AES for enhanced security, storing the key securely based on the operating system.
    *   Built-in configuration editor to manage settings.
    *   Supports loading configuration from `config.json`.
*   **User Management:**
    *   Displays inactive users in a filterable and sortable table (UPN, Last Sign-in, Status).
    *   **Batch Actions:** Select multiple users to enable or disable their accounts directly from the application.
*   **Reporting:**
    *   Export the list of inactive users to a CSV file.
    *   Optionally email the CSV report via SMTP (supports authentication and TLS).
*   **Scheduling:**
    *   Schedule automatic scans (daily, weekly, monthly, etc.) at a specific time.
    *   Optionally configure automatic emailing of reports after scheduled scans.
*   **Security Focused:**
    *   Warns if using unencrypted credentials.
    *   Provides options to encrypt sensitive data.
    *   Uses Microsoft Graph API with secure OAuth 2.0 authentication (Client Credentials Flow).
*   **Logging:** Logs application activity and errors to `app.log` for troubleshooting.

## Requirements

*   **Python:** 3.8 or higher
*   **Pip:** Python package installer
*   **Azure AD Tenant:** Access to an Azure Active Directory tenant.
*   **Azure AD App Registration:** An application registered in your Azure AD tenant with the necessary permissions.

### Required Microsoft Graph API Permissions (Application Permissions)

You need to create an App Registration in Azure AD and grant it the following *Application permissions* for Microsoft Graph:

*   `User.Read.All`: To read user profiles and properties, including `signInActivity`.
*   `AuditLog.Read.All`: Required to read the `signInActivity` property which contains last sign-in information.
*   `User.ReadWrite.All`: To enable/disable user accounts (PATCH operation on user objects).

**Important:** After adding these permissions in the Azure portal, make sure to click the **"Grant admin consent for [Your Tenant Name]"** button.

## Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/wywy1234/Azure-AD-Inactive-User-Management-Tool
    cd Azure-AD-Inactive-User-Management-Tool
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Make sure you have a `requirements.txt` file (see note below).
    ```bash
    pip install -r requirements.txt
    ```
    *Note:* If `requirements.txt` doesn't exist, you can create it after installing the packages manually or list the core dependencies:
    ```bash
    pip install PySide6 requests pycryptodome
    # Then generate the requirements file:
    pip freeze > requirements.txt
    ```

4.  **Azure AD App Registration:**
    *   Go to your Azure Portal -> Azure Active Directory -> App registrations -> New registration.
    *   Give it a name (e.g., "InactiveUserScannerApp").
    *   Choose "Accounts in this organizational directory only".
    *   Register the application.
    *   Note down the **Application (client) ID** and **Directory (tenant) ID**.
    *   Go to "Certificates & secrets" -> "Client secrets" -> "New client secret".
    *   Add a description, choose an expiry, and click "Add". **Immediately copy the secret *Value* - you won't see it again.**
    *   Go to "API permissions" -> "Add a permission" -> "Microsoft Graph" -> "Application permissions".
    *   Search for and add `User.Read.All`, `AuditLog.Read.All`, and `User.ReadWrite.All`.
    *   Click **"Grant admin consent for [Your Tenant Name]"**. The status for the permissions should show green checkmarks.

5.  **Configuration (`config.json`):**
    *   The application will attempt to create a default `config.json` file in the same directory as `main.py` on its first run if one doesn't exist.
    *   You will be prompted to edit the configuration on the first run or if the existing configuration is invalid.
    *   Alternatively, create `config.json` manually with the following structure:
        ```json
        {
          "TENANT_ID": "YOUR_AZURE_AD_TENANT_ID",
          "CLIENT_ID": "YOUR_APP_REGISTRATION_CLIENT_ID",
          "CLIENT_SECRET": "YOUR_APP_REGISTRATION_CLIENT_SECRET_VALUE", // Plain text initially
          "GRAPH_API_URL": "https://graph.microsoft.com/v1.0",
          "DAYS_TO_SEARCH_BEYOND": 90,
          "sender_email": "your_sender_email@example.com", // For sending reports
          "receiver_email": "admin_email@example.com",   // Where reports are sent
          "smtp_server": "smtp.office365.com",        // e.g., smtp.office365.com or smtp.gmail.com
          "smtp_port": 587,                           // e.g., 587 (TLS) or 465 (SSL)
          "email_subject": "Inactive Azure AD Users Report",
          "smtp_password": "",                        // Optional: Password for sender_email if needed
          "auto_schedule": false,                     // Enable/disable scheduled scans
          "schedule_time": "09:00",                   // Time for scheduled scans (HH:mm)
          "auto_email": false                         // Enable/disable auto-emailing on scheduled scans
        }
        ```
    *   **Important:** Use the "Encrypt Credentials" button in the application's Configuration section or the "Encrypt Client Secret" / "Encrypt SMTP Password" buttons in the Config Editor to secure your `CLIENT_SECRET` and `smtp_password`. Once encrypted, the `CLIENT_SECRET` field will be replaced/updated, and a `CLIENT_SECRET_ENCRYPTED: true` flag will be added (similarly for `smtp_password_encrypted`).

## Usage

1.  **Activate Virtual Environment:**
    ```bash
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
2.  **Run the Application:**
    ```bash
    python main.py
    ```
3.  **First Run:** If `config.json` is missing or invalid, you'll be prompted to edit the configuration. Fill in your Azure AD details and optionally configure email/scheduling settings. Use the encryption buttons for sensitive fields.
4.  **Main Window:**
    *   **Configuration:** View status, reload, edit, or encrypt credentials.
    *   **Scheduling:** Enable/configure automated scans and email reports.
    *   **Scan Settings:** Set the inactivity threshold (days) and start a manual scan.
    *   **Results:** View scan results. Filter the table, select users using Shift/Ctrl keys.
5.  **Actions:**
    *   **Enable/Disable Selected:** Select users in the table and click the corresponding button. You will be asked for confirmation.
    *   **Export to CSV:** Saves the currently displayed results to a timestamped CSV file.
    *   **Email Report:** Sends the currently displayed results as a CSV attachment using the configured email settings.

<!-- Add screenshots of the config editor, results table -->
<!-- ![Config Editor Screenshot](path/to/config_editor.png) -->
<!-- ![Results Screenshot](path/to/results.png) -->

## Security

*   **Credential Encryption:** The application uses AES (CBC mode) to encrypt the Azure AD Client Secret and the optional SMTP password stored in `config.json`.
*   **Key Storage:** The encryption key is generated automatically and stored in a semi-obfuscated, permissions-restricted location within the user's profile directory (`AppData\Local` on Windows, `.config` on Linux/macOS).
*   **Warning:** While credentials in the file are encrypted, the security of the application still relies on the security of the machine it runs on and the user account executing it. Protect the machine appropriately.
*   **Encryption Test:** The Config Editor includes a "Test Encryption" button to verify the encryption/decryption mechanism is working correctly.

## Configuration Details (`config.json`)

*   `TENANT_ID`: Your Azure AD Directory (tenant) ID.
*   `CLIENT_ID`: The Application (client) ID of your registered Azure AD application.
*   `CLIENT_SECRET`: The client secret value for your registered application. **Encrypt this using the application.**
*   `CLIENT_SECRET_ENCRYPTED` (boolean): Added automatically when the secret is encrypted.
*   `GRAPH_API_URL`: Base URL for Microsoft Graph API (default: `https://graph.microsoft.com/v1.0`).
*   `DAYS_TO_SEARCH_BEYOND`: The number of days of inactivity to trigger inclusion in the report.
*   `sender_email`: Email address to send reports from.
*   `receiver_email`: Email address to send reports to.
*   `smtp_server`: SMTP server hostname or IP address.
*   `smtp_port`: SMTP server port.
*   `email_subject`: Subject line for the report emails.
*   `smtp_password`: Password for the `sender_email` account (if required by the SMTP server). **Encrypt this using the application.**
*   `smtp_password_encrypted` (boolean): Added automatically when the SMTP password is encrypted.
*   `auto_schedule` (boolean): Master toggle for enabling scheduled scans.
*   `schedule_time` (string): Time in "HH:mm" format for daily/scheduled scans.
*   `auto_email` (boolean): If true, automatically emails the report after a scheduled scan completes successfully.

## Troubleshooting

*   Check the `app.log` file in the application directory for detailed error messages and activity logs.
*   Ensure the Azure AD App Registration has the correct API permissions and that **admin consent was granted**.
*   Verify that the `TENANT_ID`, `CLIENT_ID`, and `CLIENT_SECRET` in `config.json` are correct. If the secret is encrypted, ensure the key file hasn't been deleted or corrupted.
*   If email fails, double-check SMTP server, port, sender/receiver emails, and credentials (including encryption status). Ensure the sender account allows SMTP access or use an App Password if required (e.g., with Gmail/MFA).
*   Ensure the machine running the application has network connectivity to `login.microsoftonline.com`, `graph.microsoft.com`, and your SMTP server.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/YourFeature`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add some feature'`).
5.  Push to the branch (`git push origin feature/YourFeature`).
6.  Open a Pull Request.

## License

This project is licensed under the [MIT License](LICENSE). <!-- Make sure LICENSE file exists -->
