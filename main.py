import logging
import sys
from PySide6.QtWidgets import QApplication
from gui import MainWindow
from config_manager import ConfigManager

def setup_logging():
    """Configure logging for the application."""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    log_file = 'app.log'

    # File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)  # Log INFO and above to file

    # Console Handler (optional)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.WARNING)  # Log WARNING and above to console

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Set root level to lowest level used by handlers
    root_logger.addHandler(file_handler)
    # root_logger.addHandler(console_handler)  # Uncomment to add console logging

    logging.info("Logging initialized.")

def main():
    try:
        setup_logging()  # Setup logging first
        app = QApplication(sys.argv)

        # Initialize configuration first
        config_manager = ConfigManager()
        logging.info("Configuration manager initialized.")

        # Check if config exists and is valid
        if not config_manager.config_exists() or not config_manager.is_config_valid():
            logging.warning("Configuration is missing or invalid. Starting first-run setup.")
            if not config_manager.config_exists():
                config_manager.create_default_config()
                logging.info("Default configuration created.")

            # Show the main window which will handle config editing
            window = MainWindow(config_manager)
            window.show()

            # Immediately open config editor for first-run setup
            window.edit_config()
        else:
            logging.info("Configuration is valid. Proceeding with normal startup.")
            window = MainWindow(config_manager)
            window.show()

        sys.exit(app.exec())

    except Exception as e:
        logging.exception("Fatal error during application startup.")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"Application failed to start:\n{str(e)}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()