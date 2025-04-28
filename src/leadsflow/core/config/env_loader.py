"""
Environment Variables Loader
===========================

Utility for loading environment variables from .env file
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger("leadsflow.env")

def load_env_file(env_file='.env'):
    """
    Load environment variables from .env file
    
    Parameters:
    - env_file: Path to .env file
    
    Returns:
    - Dictionary with loaded environment variables
    """
    env_vars = {}
    
    # Check if file exists
    env_path = Path(env_file)
    if not env_path.exists():
        logger.warning(f".env file not found at {env_path.absolute()}")
        return env_vars
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    # Store in dictionary and set in environment
                    env_vars[key] = value
                    os.environ[key] = value
        
        logger.info(f"Loaded {len(env_vars)} environment variables from {env_path}")
        return env_vars
    
    except Exception as e:
        logger.error(f"Error loading .env file: {str(e)}")
        return env_vars

def get_env_value(key, default=None):
    """
    Get environment variable value
    
    Parameters:
    - key: Environment variable name
    - default: Default value if not found
    
    Returns:
    - Variable value or default
    """
    # Try to get from os.environ first
    value = os.environ.get(key)
    
    # If not found and .env exists, try to load it
    if value is None and Path('.env').exists() and not hasattr(get_env_value, '_env_loaded'):
        load_env_file()
        get_env_value._env_loaded = True
        value = os.environ.get(key)
    
    # Return value or default
    return value if value is not None else default

def get_smtp_config():
    """
    Get SMTP configuration from environment variables
    
    Returns:
    - Dictionary with SMTP configuration
    """
    # Load .env file if needed
    if not os.environ.get('SMTP_SERVER') and Path('.env').exists():
        load_env_file()
    
    # Get SMTP configuration
    config = {
        'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.environ.get('SMTP_PORT', 465)),
        'smtp_username': os.environ.get('SMTP_USERNAME', ''),
        'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
        'from_email': os.environ.get('SMTP_FROM_EMAIL', os.environ.get('SMTP_USERNAME', '')),
        'use_ssl': os.environ.get('SMTP_USE_SSL', 'True').lower() in ('true', '1', 'yes')
    }
    
    return config 