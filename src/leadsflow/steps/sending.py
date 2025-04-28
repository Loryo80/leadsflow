"""
Step 3: Email Sending via SMTP
=============================

This module handles:
1. Loading generated email content
2. Sending emails via SMTP in batches
3. Tracking sending status and results
"""

import streamlit as st
import pandas as pd
import os
import time
import json
from datetime import datetime, timedelta
import random
from concurrent.futures import ThreadPoolExecutor
import logging # Import logging

# Import SMTP sender instead of Outlook
from leadsflow.core.email.smtp_sender import SMTPSender, is_smtp_available
from leadsflow.core.config.env_loader import get_smtp_config, load_env_file
from leadsflow.utils import logger # Import logger from utils

# Function to send a single email via SMTP
def send_email_via_smtp(to_email, subject, body, config=None, tracking=True, delay_range=(1, 5)):
    """
    Send an email using SMTP
    
    Parameters:
    - to_email: Recipient email address
    - subject: Email subject
    - body: Email body content
    - config: SMTP configuration dictionary
    - tracking: Whether to enable read receipt
    - delay_range: Tuple with min and max seconds to delay (for rate limiting)
    
    Returns:
    - Dictionary with status and details
    """
    try:
        # Initialize SMTP sender
        smtp_sender = SMTPSender(delay_range=delay_range, config=config)
        
        # Send the email
        result = smtp_sender.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            tracking=tracking
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error in send_email_via_smtp for {to_email}: {str(e)}") # Log error
        return {
            "status": "failed",
            "details": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Function to send emails in batches
def send_emails_batch(df_batch, settings, max_workers=3):
    """
    Send emails for a batch of recipients
    
    Parameters:
    - df_batch: DataFrame with email content
    - settings: Dictionary with sending settings
    - max_workers: Number of parallel senders
    
    Returns:
    - List of results
    """
    results = []
    
    # Get SMTP config from settings or environment
    smtp_config = settings.get('smtp_config', get_smtp_config())
    
    # Use ThreadPoolExecutor for parallel sending
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        for _, row in df_batch.iterrows():
            # Skip if missing data or invalid email
            # Use .get with default False for valid_email
            if (not row.get('valid_email', False) or
                pd.isna(row.get('email_subject', '')) or
                pd.isna(row.get('email_content', ''))):
                results.append({
                    "status": "skipped",
                    "details": "Invalid email or missing content",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                continue
            
            # Submit task to thread pool
            future = executor.submit(
                send_email_via_smtp,
                row['email'],
                row['email_subject'],
                row['email_content'],
                smtp_config,
                settings.get('tracking', True),
                settings.get('delay_range', (1, 5))
            )
            # Store future and the original index for accurate updates
            futures.append((future, row.name))

        # Collect results using the original index
        batch_results_dict = {}
        for future, idx in futures:
            try:
                result = future.result()
                batch_results_dict[idx] = result
            except Exception as e:
                logger.error(f"Error collecting result for index {idx}: {str(e)}")
                batch_results_dict[idx] = {
                    "status": "error",
                    "details": str(e),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

    # Ensure results are in the same order as the input batch_df indices
    ordered_results = [batch_results_dict.get(idx, {
        "status": "error",
        "details": "Result not found",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }) for idx in df_batch.index]

    return ordered_results

# Function to group emails by company
def group_by_company(df):
    """Group emails by company name"""
    if 'company_name' not in df.columns:
        return {}
    
    groups = {}
    for company in df['company_name'].unique():
        if pd.isna(company):
            continue
        company_df = df[df['company_name'] == company]
        groups[company] = company_df
    
    return groups

def send_emails_step(get_cache_path, save_progress, get_available_caches):
    """Main function for step 3: Email sending"""
    st.header("Step 3: Email Sending (SMTP)")
    
    # Load environment variables from .env file
    env_vars = load_env_file()
    
    # First, check for generated content from Step 2
    step2_caches = get_available_caches(2)
    
    if not step2_caches:
        st.warning("No generated email content found. Please complete Step 2 first.")
        return
    
    # Check for previous sending results
    previous_caches = get_available_caches(3)
    if previous_caches:
        st.info(f"Found {len(previous_caches)} previous sending results")
        
        # Option to view previous results
        view_previous = st.expander("View previous sending results", expanded=False)
        with view_previous:
            # Display available caches in a table
            cache_df = pd.DataFrame(previous_caches)
            st.dataframe(cache_df[['timestamp', 'rows', 'description']])
            
            selected_cache = st.selectbox(
                "Select a result to view", 
                options=cache_df['filepath'].tolist(),
                format_func=lambda x: f"{os.path.basename(x)} - {cache_df[cache_df['filepath']==x]['description'].iloc[0]}"
            )
            
            if st.button("Load Selected Result"):
                with st.spinner("Loading results..."):
                    result_df = pd.read_excel(selected_cache)
                    
                    # Display summary
                    if 'sending_status' in result_df.columns:
                        sent_count = (result_df['sending_status'] == 'sent').sum()
                        failed_count = (result_df['sending_status'] == 'failed').sum()
                        skipped_count = (result_df['sending_status'] == 'skipped').sum()
                        
                        st.subheader("Sending Summary")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Sent", sent_count)
                        col2.metric("Failed", failed_count)
                        col3.metric("Skipped", skipped_count)
                        
                        # Display detailed results
                        st.subheader("Sending Results")
                        st.dataframe(result_df[['email', 'company_name', 'sending_status', 'sending_details', 'sending_timestamp']].head(20))
    
    # Start new sending process
    st.subheader("Send New Emails")
    
    # SMTP configuration section
    st.markdown("### SMTP Configuration")
    
    # Get current SMTP config
    smtp_config = get_smtp_config()
    
    # Display SMTP settings with option to modify
    smtp_settings = st.expander("SMTP Settings", expanded=not is_smtp_available())
    
    with smtp_settings:
        # Email provider selection for preset configurations
        email_provider = st.selectbox(
            "Email Provider",
            options=["Gmail", "Outlook/Microsoft 365", "Yahoo Mail", "Other/Custom"],
            index=0,
            help="Select your email provider for automatic settings"
        )
        
        # Apply preset configurations based on provider
        if email_provider == "Gmail":
            default_server = "smtp.gmail.com"
            default_port = 587
            default_ssl = False
            st.info("Gmail requires an App Password for SMTP. Enable 2-Step Verification and create an App Password in your Google Account security settings.")
        elif email_provider == "Outlook/Microsoft 365":
            default_server = "smtp.office365.com"
            default_port = 587
            default_ssl = False
        elif email_provider == "Yahoo Mail":
            default_server = "smtp.mail.yahoo.com"
            default_port = 587
            default_ssl = False
            st.info("Yahoo Mail requires an App Password for SMTP.")
        else:
            default_server = smtp_config.get('smtp_server', '')
            default_port = int(smtp_config.get('smtp_port', 587))
            default_ssl = smtp_config.get('use_ssl', False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            smtp_server = st.text_input("SMTP Server", value=default_server)
            smtp_port = st.number_input("SMTP Port", value=default_port, min_value=1, max_value=65535)
            use_ssl = st.checkbox("Use SSL", value=default_ssl, 
                                help="Usually OFF for port 587 (TLS), ON for port 465 (SSL)")
        
        with col2:
            smtp_username = st.text_input("SMTP Username/Email", value=smtp_config.get('smtp_username', ''))
            smtp_password = st.text_input("SMTP Password", value=smtp_config.get('smtp_password', ''), type="password", 
                                        help="For Gmail and Yahoo, use an App Password")
            from_email = st.text_input("From Email", value=smtp_config.get('from_email', smtp_username))
        
        # SMTP Help & Troubleshooting as markdown text (non-expandable to avoid nesting)
        st.markdown("""
        **Gmail Setup Help:**
        1. Enable 2-Step Verification in your Google Account
        2. Create an App Password at https://myaccount.google.com/security
        3. Use that 16-character code as your password here
        
        **Connection Issues:**
        - For Gmail, try port 587 with SSL OFF first
        - If that fails, try port 465 with SSL ON
        - Check that your account allows "less secure apps" or uses app passwords
        - Some providers block SMTP access from unknown locations
        
        **Test Connection:**
        Use the Test button below to verify your settings before sending emails
        """)
        
        if st.button("Test SMTP Connection"):
            with st.spinner("Testing SMTP connection..."):
                test_config = {
                    'smtp_server': smtp_server,
                    'smtp_port': smtp_port,
                    'smtp_username': smtp_username,
                    'smtp_password': smtp_password,
                    'from_email': from_email,
                    'use_ssl': use_ssl
                }
                
                # Create sender with test config
                sender = SMTPSender(config=test_config)
                
                # Try to send a test email to self
                try:
                    result = sender.send_email(
                        to_email=smtp_username,
                        subject="SMTP Test Email",
                        body="This is a test email to verify SMTP settings."
                    )
                    
                    if result['status'] == 'sent':
                        st.success("SMTP connection successful! Test email sent.")
                    else:
                        st.error(f"SMTP test failed: {result['details']}")
                except Exception as e:
                    st.error(f"Error testing SMTP: {str(e)}")
                    st.info("Check your settings and try again. See Help section for troubleshooting.")
        
        # Save SMTP settings to session state
        st.session_state['smtp_config'] = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'smtp_username': smtp_username,
            'smtp_password': smtp_password,
            'from_email': from_email,
            'use_ssl': use_ssl
        }
    
    # Select input data from Step 2
    st.markdown("### Select Email Content Data")
    step2_df = pd.DataFrame(step2_caches)
    selected_input = st.selectbox(
        "Select generated email content to use", 
        options=step2_df['filepath'].tolist(),
        format_func=lambda x: f"{os.path.basename(x)} - {step2_df[step2_df['filepath']==x]['description'].iloc[0]}"
    )
    
    # Load the selected data
    if selected_input:
        with st.spinner("Loading email content..."):
            input_df = pd.read_excel(selected_input)
            
            # Check if we have the necessary columns
            required_columns = ['email', 'email_subject', 'email_content']
            missing_columns = [col for col in required_columns if col not in input_df.columns]
            
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                return
            
            # Count valid emails with content
            valid_emails = (
                (input_df['valid_email'] == True if 'valid_email' in input_df.columns else True) & 
                input_df['email_subject'].notna() & 
                input_df['email_content'].notna()
            ).sum()
            
            st.success(f"Loaded {len(input_df)} records ({valid_emails} valid emails with content)")
            
            # Show a preview
            preview_cols = ['email', 'company_name', 'valid_email', 'email_subject']
            st.dataframe(input_df[preview_cols].head(5))
    
    # Sending options
    st.markdown("### Sending Options")
    
    sending_method = st.radio(
        "Sending Method",
        options=["Send All", "Send by Company", "Send by Batch Size"]
    )
    
    # Common settings
    col1, col2 = st.columns(2)
    
    with col1:
        batch_size = st.slider(
            "Batch size", 
            min_value=5, 
            max_value=100, 
            value=20,
            help="Number of emails to send in each batch"
        )
        
        min_delay = st.slider(
            "Min delay between emails (seconds)", 
            min_value=1, 
            max_value=30, 
            value=2
        )
    
    with col2:
        max_workers = st.slider(
            "Parallel senders", 
            min_value=1, 
            max_value=5, 
            value=1,
            help="Higher values may trigger spam detection"
        )
        
        max_delay = st.slider(
            "Max delay between emails (seconds)", 
            min_value=min_delay, 
            max_value=60, 
            value=min_delay + 3
        )
    
    # Additional settings
    enable_tracking = st.checkbox("Enable read receipts", value=False)
    
    daily_limit = st.slider(
        "Daily sending limit", 
        min_value=50, 
        max_value=1000, 
        value=200,
        help="Limit total emails sent per day to avoid triggering spam filters"
    )
    
    # Description for this run
    description = st.text_input(
        "Description for this sending run",
        value=f"Email sending using {sending_method.lower()} method via SMTP"
    )
    
    # Special options based on sending method
    if sending_method == "Send by Company":
        st.markdown("### Company Selection")
        
        # Group data by company
        company_groups = group_by_company(input_df)
        companies = list(company_groups.keys())
        
        if not companies:
            st.warning("No company information found in the data")
            # Disable company selection if none found
            selected_companies = []
        else:
            selected_companies = st.multiselect(
                "Select companies to send emails to",
                options=companies,
                format_func=lambda x: f"{x} ({len(company_groups[x])} contacts)"
            )
            
            if selected_companies:
                total_selected = sum(len(company_groups[company]) for company in selected_companies)
                st.info(f"Selected {len(selected_companies)} companies with {total_selected} total contacts")
            else:
                # Handle case where Send by Company is selected but no companies chosen
                st.warning("No companies selected. If you proceed, no emails will be sent.")

    # Initialize session state variables if they don't exist
    if 'ready_to_confirm_sending' not in st.session_state:
        st.session_state.ready_to_confirm_sending = False
    if 'final_confirmation_checked' not in st.session_state:
        st.session_state.final_confirmation_checked = False
    if 'send_in_progress' not in st.session_state:
        st.session_state.send_in_progress = False

    # Button to initiate the checks and prepare for confirmation
    if st.button("Prepare to Send Emails", key="prepare_sending", disabled=st.session_state.get('send_in_progress', False)):
        # Reset confirmation state
        st.session_state.final_confirmation_checked = False
        st.session_state.ready_to_confirm_sending = False
        st.session_state.send_in_progress = False # Ensure sending doesn't start immediately

        # --- Perform Checks ---
        smtp_config = st.session_state.get('smtp_config', get_smtp_config())
        required_fields = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
        missing_fields = [field for field in required_fields if not smtp_config.get(field)]

        if missing_fields:
            st.error(f"Missing SMTP configuration: {', '.join(missing_fields)}")
            st.info("Please fill in all SMTP settings before sending emails")
            return # Stop processing

        # Test SMTP connection
        with st.spinner("Testing SMTP connection..."):
            try:
                # Use SMTPSender's logic for testing connection
                sender = SMTPSender(config=smtp_config)
                # Simple connection validation without sending email
                if smtp_config.get('use_ssl', True): # Default to True if not specified
                    import smtplib
                    server = smtplib.SMTP_SSL(smtp_config['smtp_server'], smtp_config['smtp_port'], timeout=10)
                else:
                    import smtplib
                    server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'], timeout=10)
                    server.starttls()

                server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
                server.quit()
                st.success("SMTP connection successful!")
                st.session_state.ready_to_confirm_sending = True # Ready for confirmation prompt

            except Exception as e:
                st.error(f"Error connecting to SMTP server: {str(e)}")
                st.info("Please check your SMTP settings and try again. If using Gmail, ensure you're using an App Password.")
                st.session_state.ready_to_confirm_sending = False # Not ready
                return # Stop processing

        # --- Prepare Data (only if connection successful) ---
        if st.session_state.ready_to_confirm_sending:
             # Store prepared data in session state to avoid recalculating after rerun
             # Ensure input_df is loaded before this button is clicked
             if 'input_df' not in locals() or input_df is None or input_df.empty:
                 st.error("Input data not loaded. Please select data source first.")
                 st.session_state.ready_to_confirm_sending = False
                 return

             working_df = input_df.copy() # Assuming input_df is loaded correctly earlier
             if 'sending_status' not in working_df.columns: working_df['sending_status'] = ""
             if 'sending_details' not in working_df.columns: working_df['sending_details'] = ""
             if 'sending_timestamp' not in working_df.columns: working_df['sending_timestamp'] = pd.NaT # Use NaT for timestamp


             to_send_df = working_df.copy()
             # Apply filters based on sending_method
             if sending_method == "Send All":
                 to_send_df = to_send_df[
                     (to_send_df.get('valid_email', True)) & # Handle missing column gracefully
                     to_send_df['email_subject'].notna() &
                     to_send_df['email_content'].notna()
                 ].copy() # Add copy to avoid SettingWithCopyWarning
             elif sending_method == "Send by Company":
                 if 'company_name' not in to_send_df.columns:
                     st.error("Company name column missing in the data.")
                     st.session_state.ready_to_confirm_sending = False
                     return
                 if not selected_companies:
                     st.warning("Sending method is 'Send by Company' but no companies were selected. No emails will be sent.")
                     to_send_df = pd.DataFrame(columns=to_send_df.columns) # Empty DataFrame
                 else:
                     to_send_df = to_send_df[to_send_df['company_name'].isin(selected_companies)].copy()
                     to_send_df = to_send_df[
                         (to_send_df.get('valid_email', True)) &
                         to_send_df['email_subject'].notna() &
                         to_send_df['email_content'].notna()
                     ].copy()
             elif sending_method == "Send by Batch Size": # Assuming this means send all valid, just process in batches
                  to_send_df = to_send_df[
                     (to_send_df.get('valid_email', True)) &
                     to_send_df['email_subject'].notna() &
                     to_send_df['email_content'].notna()
                 ].copy()

             if len(to_send_df) == 0:
                 st.error("No valid emails to send based on your selection and data filters.")
                 st.session_state.ready_to_confirm_sending = False # Not ready
                 return # Stop processing

             st.session_state.to_send_df = to_send_df # Store the df to be sent
             st.session_state.working_df = working_df # Store the df to update


    # --- Confirmation Prompt and Sending Execution ---
    # This block runs if checks passed in the previous run
    if st.session_state.get('ready_to_confirm_sending', False) and not st.session_state.get('send_in_progress', False):
        to_send_df = st.session_state.get('to_send_df')

        # Double-check if data is available in session state
        if to_send_df is None or to_send_df.empty:
             st.warning("Data to send not found in session state or is empty. Please 'Prepare to Send Emails' again.")
             st.session_state.ready_to_confirm_sending = False # Reset state
             # Don't return here, allow rerun to clear the prompt
        else:
            st.warning(f"You are about to send {len(to_send_df)} emails via SMTP. This action cannot be undone.")

            # Use checkbox state directly
            # Use a unique key to avoid conflicts if checkbox is used elsewhere
            confirmed = st.checkbox("I understand and want to proceed", key="final_smtp_confirmation")
            st.session_state.final_confirmation_checked = confirmed # Update session state

            if st.session_state.final_confirmation_checked:
                st.session_state.send_in_progress = True # Set flag to start sending
                st.session_state.ready_to_confirm_sending = False # Move out of confirmation phase
                # Use st.rerun() to immediately start the sending block below
                st.rerun()
            else:
                 st.info("Check the box above to confirm and enable sending.")


    # --- Actual Sending Block ---
    # This block runs only after confirmation and rerun
    if st.session_state.get('send_in_progress', False):
        # Retrieve data from session state
        to_send_df = st.session_state.get('to_send_df')
        working_df = st.session_state.get('working_df')
        smtp_config = st.session_state.get('smtp_config', get_smtp_config()) # Ensure config is available


        if to_send_df is None or working_df is None:
             st.error("Session state lost. Cannot proceed with sending. Please start over by preparing emails again.")
             st.session_state.send_in_progress = False # Reset flag
             st.session_state.ready_to_confirm_sending = False
             st.session_state.final_confirmation_checked = False
             st.rerun() # Rerun to clear state
             return

        st.info("Sending emails in progress...") # Indicate sending has started

        # Settings for sending
        settings = {
            'tracking': enable_tracking,
            'delay_range': (min_delay, max_delay),
            'daily_limit': daily_limit,
            'smtp_config': smtp_config
        }

        # Create batches
        batches = []
        total_to_send = len(to_send_df)
        for i in range(0, total_to_send, batch_size):
            end_idx = min(i + batch_size, total_to_send)
            # Ensure we are slicing correctly based on iloc for batches
            batches.append(to_send_df.iloc[i:end_idx])

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        st.markdown("### Sending Progress")
        sent_count = 0
        failed_count = 0
        skipped_count = 0 # Count skipped in the initial filtering
        error_count = 0 # Count errors during sending

        # Process each batch
        try: # Wrap batch processing in try/finally to reset state
            total_processed_in_run = 0
            for i, batch_df in enumerate(batches):
                # Check if we've hit the daily limit based on actual sends
                if sent_count >= daily_limit:
                    st.warning(f"Daily sending limit of {daily_limit} reached. Stopping.")
                    break

                # Check if batch is empty (can happen with filtering)
                if batch_df.empty:
                    logger.info(f"Batch {i+1} is empty, skipping.")
                    continue

                status_text.text(f"Processing batch {i+1}/{len(batches)} (Size: {len(batch_df)})...")

                try:
                    # Send emails for this batch
                    batch_results = send_emails_batch(
                        batch_df,
                        settings,
                        max_workers
                    )

                    # Update the main working_df with results using original indices
                    current_batch_indices = batch_df.index
                    if len(batch_results) != len(current_batch_indices):
                         logger.error(f"Mismatch between results ({len(batch_results)}) and batch size ({len(current_batch_indices)}) for batch {i+1}. Skipping updates for this batch.")
                         error_count += len(current_batch_indices) # Count all as errors for this batch
                    else:
                        for j, result in enumerate(batch_results):
                            idx = current_batch_indices[j]
                            # Ensure index exists in working_df before updating
                            if idx in working_df.index:
                                working_df.loc[idx, 'sending_status'] = result['status']
                                working_df.loc[idx, 'sending_details'] = result.get('details', '') # Handle missing details key
                                working_df.loc[idx, 'sending_timestamp'] = pd.to_datetime(result.get('timestamp', pd.NaT)) # Convert to datetime


                                # Update counts based on results
                                if result['status'] == 'sent':
                                    sent_count += 1
                                elif result['status'] == 'failed':
                                    failed_count += 1
                                elif result['status'] == 'error':
                                     error_count += 1
                                # 'skipped' status is handled before sending, not here
                            else:
                                logger.warning(f"Index {idx} from batch not found in working_df. Skipping update.")
                                error_count += 1

                    # Update progress based on batches processed
                    progress = (i + 1) / len(batches)
                    progress_bar.progress(progress)

                    status_text.text(
                        f"Batch {i+1}/{len(batches)} done - "
                        f"Sent: {sent_count}, Failed: {failed_count}, Errors: {error_count}"
                    )

                    # Save intermediate results (using the potentially updated working_df)
                    # Use the session state working_df for saving
                    st.session_state.working_df = working_df
                    if i % 5 == 0 or i == len(batches) - 1:
                        temp_path = save_progress(3, st.session_state.working_df, f"{description} (in progress - {i+1}/{len(batches)} batches)")

                    # Add a delay between batches
                    # Ensure delay range is valid
                    actual_min_delay = max(0.1, min_delay) # Min delay of 0.1s
                    actual_max_delay = max(actual_min_delay, max_delay)
                    inter_batch_delay = random.uniform(actual_min_delay * 2, actual_max_delay * 2) # Longer delay between batches
                    logger.info(f"Waiting {inter_batch_delay:.1f}s before next batch.")
                    time.sleep(inter_batch_delay)


                except Exception as e:
                    st.error(f"Critical error processing batch {i+1}: {str(e)}")
                    logger.exception(f"Unhandled exception in batch {i+1}") # Log full traceback
                    error_count += len(batch_df) # Count all in batch as errors
                    # Consider stopping or continuing based on error type

            # Final save (using the final state of working_df)
            final_path = save_progress(3, working_df, description)

            # Calculate final skipped count from the initial filter applied before sending
            initial_rows = len(st.session_state.get('working_df', pd.DataFrame()))
            final_skipped_count = initial_rows - (sent_count + failed_count + error_count)


            # Show completion
            st.success(f"Email sending complete! Status: Sent: {sent_count}, Failed: {failed_count}, Errors: {error_count}, Skipped (before send): {final_skipped_count}")

            # Show results preview
            st.subheader("Sending Results Preview")
            result_cols = ['email', 'company_name', 'valid_email', 'sending_status', 'sending_details', 'sending_timestamp']
            # Ensure columns exist before trying to display them
            display_cols = [col for col in result_cols if col in working_df.columns]
            st.dataframe(working_df[display_cols].head(20))


            # Provide download button for the final working_df
            csv_data = working_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Full Results CSV",
                data=csv_data,
                file_name=f"email_sending_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        finally:
             # Reset state variables regardless of success or failure inside the sending block
             st.session_state.send_in_progress = False
             st.session_state.ready_to_confirm_sending = False
             st.session_state.final_confirmation_checked = False
             # Clear stored dataframes from session state to free memory
             if 'to_send_df' in st.session_state: del st.session_state.to_send_df
             if 'working_df' in st.session_state: del st.session_state.working_df
             logger.info("Sending process finished, resetting state.")
             # Rerun one last time to clear the sending UI elements and reflect final state
             st.rerun() 