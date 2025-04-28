"""
Lead Processing Application - Main Entry Point
=============================================

This Streamlit application orchestrates a three-step workflow:
1. Email Validation & Company Extraction
2. Email Content Generation 
3. Email Sending via Outlook

Each step can be run independently and uses cached results from previous runs.
"""

import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import json
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import step modules
from src.leadsflow.steps.validation import validate_emails_step
from src.leadsflow.steps.generation import generate_email_content_step  
from src.leadsflow.steps.sending import send_emails_step

# Set page config
st.set_page_config(
    page_title="Lead Processing Workflow",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("Lead Processing Workflow")
st.markdown("""
This application helps you process large lead lists through a three-step workflow:
1. **Email Validation & Company Extraction**: Clean data and extract company information
2. **Email Content Generation**: Create personalized email content for each lead
3. **Email Sending**: Send emails via Outlook in batches
""")

# Cache directory setup
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(step_number, filename=None):
    """Generate path for cache files"""
    if filename:
        return os.path.join(CACHE_DIR, f"step{step_number}_{filename}")
    # If no filename is provided, return the latest cache file for that step
    files = [f for f in os.listdir(CACHE_DIR) if f.startswith(f"step{step_number}_")]
    if not files:
        return None
    # Get the most recent file
    files.sort(reverse=True)
    return os.path.join(CACHE_DIR, files[0])

def save_progress(step_number, df, description=""):
    """Save progress to cache with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"step{step_number}_{timestamp}.xlsx"
    filepath = os.path.join(CACHE_DIR, filename)
    
    # Save the dataframe
    df.to_excel(filepath, index=False)
    
    # Save metadata
    metadata = {
        "timestamp": timestamp,
        "rows": len(df),
        "description": description,
        "columns": df.columns.tolist()
    }
    with open(f"{filepath}.meta", "w") as f:
        json.dump(metadata, f)
    
    return filepath

def get_available_caches(step_number):
    """Get available cache files for a step"""
    files = [f for f in os.listdir(CACHE_DIR) 
             if f.startswith(f"step{step_number}_") and f.endswith(".xlsx")]
    files.sort(reverse=True)  # Most recent first
    
    result = []
    for f in files:
        filepath = os.path.join(CACHE_DIR, f)
        meta_path = f"{filepath}.meta"
        
        if os.path.exists(meta_path):
            with open(meta_path, "r") as mf:
                meta = json.load(mf)
                result.append({
                    "filename": f,
                    "filepath": filepath,
                    "timestamp": meta.get("timestamp", "Unknown"),
                    "rows": meta.get("rows", 0),
                    "description": meta.get("description", "")
                })
        else:
            # Create basic metadata if missing
            result.append({
                "filename": f,
                "filepath": filepath,
                "timestamp": f.split("_")[1].split(".")[0],
                "rows": 0,
                "description": "No metadata available"
            })
    
    return result

# Sidebar for workflow navigation
st.sidebar.title("Workflow Navigation")
step = st.sidebar.radio(
    "Select Step",
    options=["1. Email Validation", "2. Email Generation", "3. Email Sending"]
)

# Main workflow logic
if step == "1. Email Validation":
    validate_emails_step(get_cache_path, save_progress, get_available_caches)
    
elif step == "2. Email Generation":
    generate_email_content_step(get_cache_path, save_progress, get_available_caches)
    
elif step == "3. Email Sending":
    send_emails_step(get_cache_path, save_progress, get_available_caches)