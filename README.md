# Azure AD Inactive User Management Tool

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/your-repo/azure-ad-inactive-user-tool/test.yml)

A secure GUI tool for identifying and managing inactive users in Azure Active Directory.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Features
### Secure Credential Management
- 🔒 AES-256 encrypted API keys
- 🔑 System-specific key storage (`~/.config/secure_store` or `%APPDATA%`)

### User Management
- 🔍 Scan for inactive users (1-365 days threshold)
- ⚡ Bulk disable accounts with confirmation
- 📊 Export to CSV/Email reports

### Professional GUI
- 🖥️ PySide6-based interface
- ⚙️ Built-in configuration editor
- 📈 Progress tracking

## Installation
```bash
git clone https://github.com/your-repo/azure-ad-inactive-user-tool.git
cd azure-ad-inactive-user-tool
pip install -r requirements.txt


