"""
Settings Management
=================

This module handles application settings:
1. UI for configuring application settings
2. Loading and saving configuration
3. Template management
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from pathlib import Path
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app_settings import load_config, save_config, DEFAULT_CONFIG
from src.leadsflow.core.email.templates import load_templates, save_template, template_editor, create_new_template

def settings_page():
    """Render the settings page"""
    st.title("Application Settings")
    
    # Load current config
    config = load_config()
    
    # Tabs for different settings categories
    tab1, tab2, tab3, tab4 = st.tabs([
        "General Settings", 
        "Validation Settings", 
        "Email Generation", 
        "Email Sending"
    ])
    
    # General Settings
    with tab1:
        st.header("General Settings")
        
        app_name = st.text_input("Application Name", value=config.get("app_name", ""))
        
        debug_mode = st.checkbox("Debug Mode", value=config.get("debug_mode", False))
        
        st.subheader("Cached Data")
        
        if st.button("Clear All Cached Data"):
            confirm = st.checkbox("I understand this will delete all cached files")
            if confirm:
                cache_dir = "cache"
                if os.path.exists(cache_dir):
                    files = os.listdir(cache_dir)
                    for file in files:
                        try:
                            os.remove(os.path.join(cache_dir, file))
                        except Exception as e:
                            st.error(f"Error deleting {file}: {str(e)}")
                    st.success(f"Deleted {len(files)} cached files")
                else:
                    st.info("No cache directory found")
    
    # Validation Settings
    with tab2:
        st.header("Email Validation Settings")
        
        validation_config = config.get("validation", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_workers = st.slider(
                "Max Worker Threads", 
                min_value=1, 
                max_value=10, 
                value=validation_config.get("max_workers", 5)
            )
            
            batch_size = st.slider(
                "Batch Size", 
                min_value=10, 
                max_value=100, 
                value=validation_config.get("batch_size", 50)
            )
        
        with col2:
            validate_mx = st.checkbox(
                "Validate MX Records", 
                value=validation_config.get("validate_mx", True),
                help="Check if domain can receive email"
            )
            
            check_username = st.checkbox(
                "Check for Generic Usernames", 
                value=validation_config.get("check_username", True),
                help="Detect common patterns like info@, admin@, etc."
            )
        
        # Column mapping settings
        st.subheader("Default Column Mapping")
        st.markdown("Set default column names to look for in uploaded Excel files")
        
        default_columns = validation_config.get("default_columns", {})
        
        col_map = {
            "email": st.text_input(
                "Email Columns", 
                value=", ".join(default_columns.get("email", [])),
                help="Comma-separated list of possible email column names"
            ),
            "first_name": st.text_input(
                "First Name Columns", 
                value=", ".join(default_columns.get("first_name", [])),
                help="Comma-separated list of possible first name column names"
            ),
            "last_name": st.text_input(
                "Last Name Columns", 
                value=", ".join(default_columns.get("last_name", [])),
                help="Comma-separated list of possible last name column names"
            ),
            "job_title": st.text_input(
                "Job Title Columns", 
                value=", ".join(default_columns.get("job_title", [])),
                help="Comma-separated list of possible job title column names"
            ),
            "company": st.text_input(
                "Company Columns", 
                value=", ".join(default_columns.get("company", [])),
                help="Comma-separated list of possible company column names"
            ),
        }
        
        # Convert comma-separated strings to lists
        for key, value in col_map.items():
            if value:
                col_map[key] = [item.strip() for item in value.split(",") if item.strip()]
    
    # Email Generation Settings
    with tab3:
        st.header("Email Generation Settings")
        
        generation_config = config.get("generation", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_workers_gen = st.slider(
                "Max Parallel Generation", 
                min_value=1, 
                max_value=5, 
                value=generation_config.get("max_workers", 3),
                help="Number of parallel LLM API calls"
            )
            
            batch_size_gen = st.slider(
                "Batch Size", 
                min_value=5, 
                max_value=50, 
                value=generation_config.get("batch_size", 20)
            )
        
        with col2:
            model = st.selectbox(
                "Default Model",
                options=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                index=0 if generation_config.get("default_model") == "gpt-3.5-turbo" else 
                      1 if generation_config.get("default_model") == "gpt-4" else 
                      2,
                help="OpenAI model to use for generation"
            )
            
            temperature = st.slider(
                "Temperature", 
                min_value=0.0, 
                max_value=1.0, 
                value=generation_config.get("temperature", 0.7),
                step=0.1,
                help="Controls randomness (0=deterministic, 1=creative)"
            )
        
        # Default sender information
        st.subheader("Default Sender Information")
        
        default_sender = generation_config.get("default_sender", {})
        
        sender_name = st.text_input("Sender Name", value=default_sender.get("name", ""))
        sender_title = st.text_input("Sender Title", value=default_sender.get("title", ""))
        sender_company = st.text_input("Sender Company", value=default_sender.get("company", ""))
        sender_phone = st.text_input("Sender Phone", value=default_sender.get("phone", ""))
        sender_signature = st.text_area("Default Signature", value=default_sender.get("signature", ""))
        
        # Email templates section
        st.subheader("Email Templates")
        
        template_option = st.radio(
            "Template Management",
            options=["Edit Existing Templates", "Create New Template"]
        )
        
        if template_option == "Edit Existing Templates":
            templates = load_templates()
            template_editor(templates)
        else:
            create_new_template()
    
    # Email Sending Settings
    with tab4:
        st.header("Email Sending Settings")
        
        sending_config = config.get("sending", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_workers_send = st.slider(
                "Max Parallel Senders", 
                min_value=1, 
                max_value=5, 
                value=sending_config.get("max_workers", 1),
                help="Higher values may trigger spam filters"
            )
            
            batch_size_send = st.slider(
                "Sending Batch Size", 
                min_value=5, 
                max_value=100, 
                value=sending_config.get("batch_size", 20)
            )
            
            min_delay = st.slider(
                "Min Delay Between Emails (seconds)", 
                min_value=1, 
                max_value=30, 
                value=sending_config.get("min_delay", 3)
            )
            
            max_delay = st.slider(
                "Max Delay Between Emails (seconds)", 
                min_value=min_delay, 
                max_value=60, 
                value=sending_config.get("max_delay", 10)
            )
        
        with col2:
            daily_limit = st.slider(
                "Daily Sending Limit", 
                min_value=50, 
                max_value=1000, 
                value=sending_config.get("daily_limit", 200),
                help="Limit total emails sent per day"
            )
            
            enable_tracking = st.checkbox(
                "Enable Read Tracking", 
                value=sending_config.get("enable_tracking", False),
                help="Request read receipts"
            )
            
            test_mode = st.checkbox(
                "Test Mode", 
                value=sending_config.get("test_mode", True),
                help="Save to drafts instead of sending"
            )
        
        # Test email recipients
        st.subheader("Test Recipients")
        st.markdown("Add email addresses for testing. In test mode, emails will only be sent to these addresses.")
        
        test_recipients = sending_config.get("test_recipients", [])
        test_recipients_str = st.text_area(
            "Test Email Addresses (one per line)",
            value="\n".join(test_recipients)
        )
        
        # Convert string to list
        if test_recipients_str:
            test_recipients = [email.strip() for email in test_recipients_str.split("\n") if email.strip()]
    
    # Save button for all settings
    if st.button("Save Settings", type="primary"):
        # Update config with new values
        config["app_name"] = app_name
        config["debug_mode"] = debug_mode
        
        # Validation settings
        config["validation"] = {
            "max_workers": max_workers,
            "batch_size": batch_size,
            "validate_mx": validate_mx,
            "check_username": check_username,
            "default_columns": col_map
        }
        
        # Generation settings
        config["generation"] = {
            "max_workers": max_workers_gen,
            "batch_size": batch_size_gen,
            "default_model": model,
            "temperature": temperature,
            "default_sender": {
                "name": sender_name,
                "title": sender_title,
                "company": sender_company,
                "phone": sender_phone,
                "signature": sender_signature
            }
        }
        
        # Sending settings
        config["sending"] = {
            "max_workers": max_workers_send,
            "batch_size": batch_size_send,
            "min_delay": min_delay,
            "max_delay": max_delay,
            "daily_limit": daily_limit,
            "enable_tracking": enable_tracking,
            "test_mode": test_mode,
            "test_recipients": test_recipients
        }
        
        # Save the updated config
        if save_config(config):
            st.success("Settings saved successfully!")
        else:
            st.error("Error saving settings")
    
    # Reset button
    if st.button("Reset to Defaults"):
        confirm_reset = st.checkbox("I understand this will reset all settings to defaults")
        if confirm_reset:
            if save_config(DEFAULT_CONFIG):
                st.success("Settings reset to defaults")
                st.rerun()
            else:
                st.error("Error resetting settings")