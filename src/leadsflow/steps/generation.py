"""
Step 2: Email Content Generation
===============================

This module handles:
1. Loading validated email data
2. Generating personalized email content using templates and LLM
3. Storing generated content for future use
"""

import streamlit as st
import pandas as pd
import os
import time
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
import sys

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import LLM generator
from leadsflow.core.llm.generator import LLMGenerator, is_openai_available, get_available_models
from leadsflow.core.email.templates import load_templates, render_template, extract_template_variables
from leadsflow.core.email.placeholder_checker import clean_generation

# Function to generate emails for a batch of rows
def generate_emails_batch(df_batch, sender_info, template_data, max_workers=3):
    """
    Generate personalized emails for a batch of recipients
    
    Parameters:
    - df_batch: DataFrame with recipient data
    - sender_info: Dict with sender information
    - template_data: Template data (dict with subject, body, etc.)
    - max_workers: Number of parallel workers
    
    Returns:
    - List of dicts with generation results
    """
    try:
        # Initialize LLM generator
        generator = LLMGenerator(
            model=st.session_state.get('model', 'gpt-3.5-turbo'),
            temperature=st.session_state.get('temperature', 0.7)
        )
        
        # Extract rows from dataframe
        rows = df_batch.to_dict('records')
        
        # Get language from session state
        language = st.session_state.get('language', 'en')
        
        # Generate emails using the LLM generator
        results = generator.batch_generate(rows, template_data, sender_info, language=language)
        
        return results
    except Exception as e:
        st.error(f"Error generating emails: {str(e)}")
        # Return empty results as fallback
        return [{"subject": "", "body": "", "status": f"error - {str(e)}"}] * len(df_batch)

def generate_email_content_step(get_cache_path, save_progress, get_available_caches):
    """Main function for step 2: Email content generation"""
    st.header("Step 2: Email Content Generation")
    
    # First, check for validated data from Step 1
    step1_caches = get_available_caches(1)
    
    if not step1_caches:
        st.warning("No validated email data found. Please complete Step 1 first.")
        return
    
    # Check for previous results from Step 2
    previous_caches = get_available_caches(2)
    if previous_caches:
        st.info(f"Found {len(previous_caches)} previous content generation results")
        
        # Option to use previous results
        use_previous = st.expander("Use previous generated content", expanded=False)
        with use_previous:
            # Display available caches in a table
            cache_df = pd.DataFrame(previous_caches)
            st.dataframe(cache_df[['timestamp', 'rows', 'description']])
            
            selected_cache = st.selectbox(
                "Select a previous result to continue with", 
                options=cache_df['filepath'].tolist(),
                format_func=lambda x: f"{os.path.basename(x)} - {cache_df[cache_df['filepath']==x]['description'].iloc[0]}"
            )
            
            if st.button("Load Selected Content"):
                with st.spinner("Loading previous content..."):
                    previous_df = pd.read_excel(selected_cache)
                    st.session_state.current_df = previous_df
                    st.success(f"Loaded {len(previous_df)} records with generated content")
                    
                    # Display preview
                    st.subheader("Preview of Generated Content")
                    preview_df = previous_df[['email', 'company_name', 'valid_email', 'email_subject', 'email_content']].head(5)
                    st.dataframe(preview_df)
                    
                    # Sample email
                    if len(previous_df) > 0 and 'email_content' in previous_df.columns:
                        st.subheader("Sample Email")
                        sample_idx = 0
                        for idx, row in previous_df.iterrows():
                            if row.get('valid_email', False) and row.get('email_content', ''):
                                sample_idx = idx
                                break
                                
                        st.markdown(f"**Subject:** {previous_df.loc[sample_idx, 'email_subject']}")
                        st.markdown(f"**Body:**\n```\n{previous_df.loc[sample_idx, 'email_content']}\n```")
                    
                    return
    
    # Start new content generation
    st.subheader("Generate New Email Content")
    
    # Select input data from Step 1
    st.markdown("### Select Validated Data")
    step1_df = pd.DataFrame(step1_caches)
    selected_input = st.selectbox(
        "Select validated data to use", 
        options=step1_df['filepath'].tolist(),
        format_func=lambda x: f"{os.path.basename(x)} - {step1_df[step1_df['filepath']==x]['description'].iloc[0]}"
    )
    
    # Load the selected data
    if selected_input:
        with st.spinner("Loading validated data..."):
            input_df = pd.read_excel(selected_input)
            valid_count = input_df['valid_email'].sum() if 'valid_email' in input_df.columns else 0
            st.success(f"Loaded {len(input_df)} records ({valid_count} valid emails)")
            
            # Show a preview
            st.dataframe(input_df.head(5))
    
    # Check if OpenAI is available
    if not is_openai_available():
        st.warning("OpenAI API key not found. LLM-powered email generation will not be available until you set an API key.")
        
        # Add option to set API key
        with st.expander("Set OpenAI API Key", expanded=True):
            api_key = st.text_input("OpenAI API Key", type="password", 
                                    help="Get a key from https://platform.openai.com/account/api-keys")
            if api_key and st.button("Save API Key"):
                os.environ['OPENAI_API_KEY'] = api_key
                st.session_state['openai_key'] = api_key
                st.success("API key set successfully!")
                st.experimental_rerun()
    
    # Email configuration section
    st.markdown("### Email Configuration")
    
    # Get available templates
    templates = load_templates()
    template_options = list(templates.keys())
    
    template_id = st.selectbox(
        "Select email template", 
        options=template_options,
        format_func=lambda x: templates[x]["name"]
    )
    
    selected_template = templates[template_id]
    
    with st.expander("Template Preview", expanded=False):
        st.code(selected_template.get("body", ""), language="text")
    
    # LLM model selection (if available)
    if is_openai_available():
        st.markdown("### LLM Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            available_models = get_available_models()
            default_model = 'gpt-3.5-turbo'
            
            if available_models:
                model = st.selectbox(
                    "Select AI model", 
                    options=available_models,
                    index=available_models.index(default_model) if default_model in available_models else 0
                )
            else:
                model = st.selectbox(
                    "Select AI model", 
                    options=["gpt-3.5-turbo", "gpt-4"],
                    index=0
                )
            
            st.session_state['model'] = model
        
        with col2:
            temperature = st.slider(
                "Creativity level", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.7, 
                step=0.1,
                help="Higher values make output more creative and diverse, lower values more focused and deterministic"
            )
            st.session_state['temperature'] = temperature
            
        # Add language selection
        language = st.selectbox(
            "Email Language",
            options=["en", "fr", "ar", "es", "de", "zh"],
            format_func=lambda x: {
                "en": "English",
                "fr": "French (Français)",
                "ar": "Arabic (العربية)",
                "es": "Spanish (Español)",
                "de": "German (Deutsch)",
                "zh": "Chinese (中文)"
            }.get(x, x)
        )
        st.session_state['language'] = language
    
    # Sender information
    st.markdown("### Sender Information")
    col1, col2 = st.columns(2)
    
    with col1:
        sender_name = st.text_input("Your Name", value="John Doe")
        sender_title = st.text_input("Your Title", value="Sales Representative")
        sender_company = st.text_input("Your Company", value="ABC Solutions")
    
    with col2:
        sender_phone = st.text_input("Your Phone", value="+1 (555) 123-4567")
        subject_line = st.text_input("Default Subject Line", value="Opportunity for collaboration")
        
    # Additional content for templates
    st.markdown("### Email Content Elements")
    company_intro = st.text_area(
        "Company Introduction", 
        value="We help businesses like yours increase efficiency and reduce costs through our innovative solutions."
    )
    
    value_proposition = st.text_area(
        "Value Proposition", 
        value="our proven approach that has helped similar companies in your industry increase productivity by 30%"
    )
    
    # Collect all sender info
    sender_info = {
        "name": sender_name,
        "title": sender_title,
        "company": sender_company,
        "phone": sender_phone,
        "subject_line": subject_line,
        "company_intro": company_intro,
        "value_proposition": value_proposition
    }
    
    # Generation options
    st.markdown("### Generation Options")
    
    col1, col2 = st.columns(2)
    with col1:
        batch_size = st.slider(
            "Batch size", 
            min_value=5, 
            max_value=100, 
            value=20,
            help="Number of emails to generate in each batch"
        )
        
    with col2:
        max_workers = st.slider(
            "Parallel workers", 
            min_value=1, 
            max_value=5, 
            value=3,
            help="Number of concurrent API calls to the LLM"
        )
    
    # Option to process only valid emails
    valid_only = st.checkbox("Process only valid emails", value=True)
    
    # Description for this run
    description = st.text_input(
        "Description for this generation run",
        value=f"Email generation using {selected_template.get('name', template_id)} template"
    )
    
    # Start generation
    if st.button("Generate Email Content", type="primary"):
        # First, check if OpenAI API key is available
        openai_key = os.environ.get('OPENAI_API_KEY', '')
        
        if not openai_key:
            # If not in environment, check streamlit secrets
            if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
                openai_key = st.secrets['OPENAI_API_KEY']
            
            # If still not available, ask the user
            if not openai_key:
                openai_key = st.text_input("OpenAI API Key (required for LLM generation)", type="password")
                if openai_key:
                    os.environ['OPENAI_API_KEY'] = openai_key
                    st.success("API key set for this session")
                else:
                    st.error("OpenAI API key is required for email generation")
                    st.info("You can get an API key from https://platform.openai.com/account/api-keys")
                    return
        
        # Filter data if needed
        working_df = input_df.copy()
        if valid_only and 'valid_email' in working_df.columns:
            working_df = working_df[working_df['valid_email'] == True].copy()
            st.info(f"Processing only {len(working_df)} valid emails out of {len(input_df)} total records")
        
        # Add columns for content if they don't exist
        if 'email_subject' not in working_df.columns:
            working_df['email_subject'] = ""
        if 'email_content' not in working_df.columns:
            working_df['email_content'] = ""
        if 'generation_status' not in working_df.columns:
            working_df['generation_status'] = ""
        
        # Processing status
        st.subheader("LLM Generation Status")
        processing_status = st.empty()
        processing_status.info("Processing only valid emails...")
        
        # Process in batches
        total_rows = len(working_df)
        processed = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        start_time = time.time()
        
        # Create batches
        batches = []
        for i in range(0, total_rows, batch_size):
            end_idx = min(i + batch_size, total_rows)
            batches.append(working_df.iloc[i:end_idx])
        
        # Process each batch
        for i, batch_df in enumerate(batches):
            status_text.text(f"Processing batch {i+1}/{len(batches)}...")
            
            try:
                # Generate emails for this batch
                batch_results = generate_emails_batch(
                    batch_df, 
                    sender_info,
                    selected_template,
                    max_workers
                )
                
                # Update the dataframe with results
                for j, result in enumerate(batch_results):
                    idx = batch_df.index[j]
                    
                    # Get row data
                    row_data = batch_df.iloc[j].to_dict()
                    
                    # Clean any remaining template variables
                    subject, body = clean_generation(
                        result['subject'], 
                        result['body'], 
                        row_data
                    )
                    
                    # Save the cleaned content
                    working_df.loc[idx, 'email_subject'] = subject
                    working_df.loc[idx, 'email_content'] = body
                    working_df.loc[idx, 'generation_status'] = result['status']
                
                # Update progress
                processed += len(batch_df)
                progress = processed / total_rows
                progress_bar.progress(progress)
                
                # Calculate ETA
                elapsed = time.time() - start_time
                emails_per_second = processed / elapsed if elapsed > 0 else 0
                eta_seconds = (total_rows - processed) / emails_per_second if emails_per_second > 0 else 0
                
                status_text.text(
                    f"Processed {processed}/{total_rows} emails ({progress:.1%}) - "
                    f"Speed: {emails_per_second:.2f} emails/sec - "
                    f"ETA: {eta_seconds/60:.1f} minutes"
                )
                
                # Save intermediate results every batch
                if i % 5 == 0 or i == len(batches) - 1:
                    temp_path = save_progress(2, working_df, f"{description} (in progress - {processed}/{total_rows})")
            
            except Exception as e:
                st.error(f"Error processing batch {i+1}: {str(e)}")
                # Continue with the next batch
        
        # Final save
        final_path = save_progress(2, working_df, description)
        
        # Update original dataframe with generated content
        merged_df = input_df.copy()
        # Only copy email content columns from working_df to merged_df where emails match
        if 'email' in merged_df.columns and 'email' in working_df.columns:
            email_map = working_df.set_index('email')
            for idx, row in merged_df.iterrows():
                email = row['email']
                if email in email_map.index:
                    merged_df.loc[idx, 'email_subject'] = email_map.loc[email, 'email_subject']
                    merged_df.loc[idx, 'email_content'] = email_map.loc[email, 'email_content']
                    merged_df.loc[idx, 'generation_status'] = email_map.loc[email, 'generation_status']
        
        # Save the complete dataset
        complete_path = save_progress(2, merged_df, f"{description} (complete dataset)")
        
        # Show completion
        st.success(f"Email generation complete! Generated content for {processed} emails")
        
        # Show results
        st.subheader("Results Preview")
        preview_cols = ['email', 'company_name', 'valid_email', 'email_subject', 'generation_status']
        st.dataframe(working_df[preview_cols].head(10))
        
        # Sample generated email
        st.subheader("Sample Generated Email")
        if processed > 0:
            sample_idx = working_df[working_df['generation_status'] == 'generated'].index[0] \
                if not working_df[working_df['generation_status'] == 'generated'].empty else working_df.index[0]
            
            st.markdown(f"**To:** {working_df.loc[sample_idx, 'email']}")
            st.markdown(f"**Subject:** {working_df.loc[sample_idx, 'email_subject']}")
            st.markdown("**Body:**")
            st.text(working_df.loc[sample_idx, 'email_content'])
            
        # Next steps guidance
        st.info("You can now proceed to Step 3: Email Sending") 