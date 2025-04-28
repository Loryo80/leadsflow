"""
Utility functions for the Lead Processing Workflow
================================================

This module provides helper functions for:
1. Logging with timestamps
2. Optimized file handling
3. Email address validation and normalization
"""

import os
import logging
import time
import pandas as pd
from datetime import datetime
import re
import hashlib
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("leadsflow")

# Cache directory
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_timestamp():
    """Return formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log_step_start(step_name, total_items=None):
    """Log the start of a processing step"""
    message = f"Starting {step_name}"
    if total_items:
        message += f" for {total_items} items"
    logger.info(message)
    return time.time()

def log_step_end(step_name, start_time):
    """Log the end of a processing step with elapsed time"""
    elapsed = time.time() - start_time
    logger.info(f"Completed {step_name} in {elapsed:.2f} seconds")
    return elapsed

def batch_generator(items, batch_size):
    """Generate batches of items with specified size"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

def read_excel_optimized(file_path, usecols=None):
    """Read Excel file with optimized memory usage"""
    logger.info(f"Reading Excel file: {file_path}")
    
    # Use memory-efficient parameters for large files
    try:
        # Try to determine if file is large to optimize loading
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        
        if file_size > 100:  # Over 100MB
            logger.info(f"Large file detected ({file_size:.1f}MB). Using chunksize.")
            # For very large files, use chunking
            chunks = []
            chunk_size = 10000  # Adjust based on your available memory
            
            for chunk in pd.read_excel(
                file_path, 
                usecols=usecols,
                engine='openpyxl',
                chunksize=chunk_size
            ):
                chunks.append(chunk)
            
            df = pd.concat(chunks)
            logger.info(f"Successfully read {len(df)} rows in chunks")
            return df
        else:
            # For smaller files, read in one go
            df = pd.read_excel(
                file_path,
                usecols=usecols,
                engine='openpyxl'
            )
            logger.info(f"Successfully read {len(df)} rows")
            return df
    
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        # Fall back to standard reading
        df = pd.read_excel(file_path, usecols=usecols)
        logger.info(f"Read {len(df)} rows with fallback method")
        return df

@lru_cache(maxsize=1024)
def normalize_email(email):
    """
    Normalize email address for consistent comparison
    - Convert to lowercase
    - Remove leading/trailing spaces
    - Handle common patterns
    """
    if not email or not isinstance(email, str):
        return ""
    
    # Trim and lowercase
    email = email.strip().lower()
    
    # Remove any spaces
    email = email.replace(" ", "")
    
    # Check basic format
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return email  # Return as is if not valid format
    
    # Split into username and domain
    username, domain = email.split('@')
    
    # Normalize gmail addresses (remove dots, handle plus addressing)
    if domain == 'gmail.com':
        # Remove dots from username (gmail ignores them)
        username = username.replace('.', '')
        
        # Handle plus addressing (everything after + is ignored)
        if '+' in username:
            username = username.split('+')[0]
    
    return f"{username}@{domain}"

def generate_email_hash(email):
    """Generate a hash of an email address for tracking"""
    normalized = normalize_email(email)
    if not normalized:
        return ""
    return hashlib.md5(normalized.encode()).hexdigest()

def detect_duplicate_emails(df, email_column='email'):
    """Detect duplicate emails in a dataframe after normalization"""
    if email_column not in df.columns:
        logger.warning(f"Email column '{email_column}' not found in dataframe")
        return df
    
    # Create normalized email column
    df['normalized_email'] = df[email_column].apply(normalize_email)
    
    # Find duplicates
    duplicate_mask = df.duplicated(subset=['normalized_email'], keep='first')
    duplicates = df[duplicate_mask]
    
    if len(duplicates) > 0:
        logger.warning(f"Found {len(duplicates)} duplicate emails after normalization")
    
    return duplicates

def optimize_dataframe_memory(df):
    """Optimize dataframe memory usage for large datasets"""
    start_memory = df.memory_usage().sum() / 1024**2
    
    # Optimize numeric columns
    for col in df.select_dtypes(include=['int']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
        
    for col in df.select_dtypes(include=['float']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    
    # Convert object columns to categories if they have few unique values
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].nunique() < 50:  # Arbitrary threshold
            df[col] = df[col].astype('category')
    
    end_memory = df.memory_usage().sum() / 1024**2
    reduction = (start_memory - end_memory) / start_memory * 100
    
    logger.info(f"Memory usage reduced from {start_memory:.2f}MB to {end_memory:.2f}MB ({reduction:.1f}% reduction)")
    
    return df 