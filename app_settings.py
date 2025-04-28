"""
Application Configuration
========================

This module stores application-wide settings, defaults, and configuration
"""

import os
import json
from pathlib import Path

# Application paths
APP_DIR = Path(__file__).parent
CACHE_DIR = APP_DIR / "cache"
TEMPLATES_DIR = APP_DIR / "templates"
CONFIG_FILE = APP_DIR / "app_config.json"

# Create directories if they don't exist
CACHE_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    # General settings
    "app_name": "Lead Processing Workflow",
    "app_version": "1.0.0",
    "debug_mode": False,
    
    # Step 1: Email validation settings
    "validation": {
        "max_workers": 5,
        "batch_size": 50,
        "validate_mx": True,
        "check_username": True,
        "default_columns": {
            "email": ["email", "Email", "email_address", "Email Address"],
            "first_name": ["first_name", "firstName", "First Name", "fname"],
            "last_name": ["last_name", "lastName", "Last Name", "lname"],
            "job_title": ["job_title", "jobTitle", "Job Title", "title", "position"],
            "company": ["company", "Company", "company_name", "organization"]
        }
    },
    
    # Step 2: Email generation settings
    "generation": {
        "max_workers": 3,
        "batch_size": 20,
        "default_model": "gpt-3.5-turbo",
        "advanced_model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 500,
        "default_sender": {
            "name": "",
            "title": "",
            "company": "",
            "phone": "",
            "signature": ""
        }
    },
    
    # Step 3: Email sending settings
    "sending": {
        "max_workers": 1,
        "batch_size": 20,
        "min_delay": 3,
        "max_delay": 10,
        "daily_limit": 200,
        "enable_tracking": False,
        "test_mode": True,
        "test_recipients": []
    }
}

def load_config():
    """Load application configuration from file or return defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
            # Merge with defaults to ensure all keys exist
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(config)
            return merged_config
        except Exception as e:
            print(f"Error loading config: {str(e)}")
    
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {str(e)}")
        return False

# Helper functions to get specific config sections
def get_validation_config():
    """Get validation step configuration"""
    config = load_config()
    return config.get("validation", DEFAULT_CONFIG["validation"])

def get_generation_config():
    """Get generation step configuration"""
    config = load_config()
    return config.get("generation", DEFAULT_CONFIG["generation"])

def get_sending_config():
    """Get sending step configuration"""
    config = load_config()
    return config.get("sending", DEFAULT_CONFIG["sending"])

def update_config_section(section, updates):
    """Update a specific section of the configuration"""
    config = load_config()
    
    if section in config:
        # Merge updates with existing section
        config[section].update(updates)
    else:
        # Create new section
        config[section] = updates
    
    return save_config(config)

def reset_config():
    """Reset configuration to defaults"""
    return save_config(DEFAULT_CONFIG)

# Global application configuration
CONFIG = load_config() 