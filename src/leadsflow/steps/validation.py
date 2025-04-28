"""
Step 1: Email Validation & Company Extraction
=============================================

This module handles:
1. Email format validation
2. Domain MX record verification
3. Company name extraction from email domains
4. Caching of validation results for efficient processing
"""

import streamlit as st
import pandas as pd
import re
import dns.resolver
import time
import os
from concurrent.futures import ThreadPoolExecutor
import tldextract

# Function to validate email format
def is_valid_email_format(email):
    if not isinstance(email, str):
        return False
    # Comprehensive email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Function to check if domain has MX records
def has_mx_records(domain):
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return len(mx_records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.exception.Timeout):
        return False
    except Exception as e:
        st.error(f"Error checking MX records for {domain}: {str(e)}")
        return False

# Function to check if username seems valid
def is_likely_valid_username(username):
    # Common patterns for invalid or generic email addresses
    suspicious_patterns = [
        r'^(admin|info|contact|support|service|sales|marketing|help|test)$',
        r'^(noreply|no-reply|donotreply|do-not-reply)$',
        r'^(webmaster|postmaster|hostmaster)$',
        r'^(abuse|spam|security|root)$'
    ]
    
    for pattern in suspicious_patterns:
        if re.match(pattern, username, re.IGNORECASE):
            return False
    return True

# Function to extract company name from domain
def extract_company_name(domain):
    """Extract company name from domain and format it nicely"""
    # Use tldextract to parse the domain properly
    extract_result = tldextract.extract(domain)
    domain_name = extract_result.domain
    
    # Clean up and format the domain name as a company name
    if domain_name:
        # Remove numbers
        company_name = re.sub(r'\d+', '', domain_name)
        
        # Replace hyphens, underscores with spaces
        company_name = re.sub(r'[-_]', ' ', company_name)
        
        # Title case and strip
        company_name = company_name.title().strip()
        
        # Handle common TLDs that might be part of company name
        common_domains = {
            'gmail': 'Google',
            'yahoo': 'Yahoo',
            'hotmail': 'Microsoft',
            'outlook': 'Microsoft',
            'aol': 'AOL',
            'protonmail': 'Proton',
            'icloud': 'Apple'
        }
        
        if domain_name.lower() in common_domains:
            return common_domains[domain_name.lower()]
            
        return company_name
    return "Unknown"

# Main validation function with company extraction
def validate_email(email, show_details=False):
    if not email or not isinstance(email, str):
        return False, "Invalid input", "Unknown"
    
    # Check email format
    if not is_valid_email_format(email):
        return False, "Invalid format", "Unknown"
    
    # Extract username and domain
    try:
        username, domain = email.split('@')
    except ValueError:
        return False, "Invalid format", "Unknown"
    
    # Extract company name
    company_name = extract_company_name(domain)
    
    # Check domain MX records
    if not has_mx_records(domain):
        return False, "No valid MX records", company_name
    
    # Check if username seems valid
    if not is_likely_valid_username(username):
        return False, "Generic address", company_name
    
    return True, "Valid", company_name

# Function to process a dataframe with email validation and company extraction
def process_dataframe(df, email_column, max_workers=5):
    if email_column not in df.columns:
        st.error(f"Column '{email_column}' not found in the dataframe")
        return None
    
    # Create a copy to avoid modifying the original
    result_df = df.copy()
    
    # Add result columns if they don't exist
    if 'valid_email' not in result_df.columns:
        result_df['valid_email'] = False
    if 'validation_details' not in result_df.columns:
        result_df['validation_details'] = ""
    if 'company_name' not in result_df.columns:
        result_df['company_name'] = ""
    
    # Get emails to validate
    emails = df[email_column].tolist()
    total = len(emails)
    
    # Create a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Function to process a batch of emails
    def process_batch(batch_emails, batch_indices):
        results = []
        for email in batch_emails:
            is_valid, details, company = validate_email(email)
            results.append((is_valid, details, company))
        return results, batch_indices
    
    # Process emails in batches with caching of domain results
    batch_size = 10
    num_batches = (total + batch_size - 1) // batch_size
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        for i in range(0, total, batch_size):
            batch_emails = emails[i:i+batch_size]
            batch_indices = list(range(i, min(i+batch_size, total)))
            futures.append(executor.submit(process_batch, batch_emails, batch_indices))
        
        completed = 0
        for future in executor.map(lambda f: f.result(), futures):
            results, indices = future
            
            for (is_valid, details, company), idx in zip(results, indices):
                result_df.loc[idx, 'valid_email'] = is_valid
                result_df.loc[idx, 'validation_details'] = details
                result_df.loc[idx, 'company_name'] = company
            
            completed += len(indices)
            progress = completed / total
            progress_bar.progress(progress)
            status_text.text(f"Processed {completed}/{total} emails ({progress:.1%})")
            
            # Small delay to avoid overloading DNS servers
            time.sleep(0.1)
    
    # Clear the status text and show completion
    status_text.text(f"Completed! Validated {total} emails.")
    
    # Return the result
    return result_df

def validate_emails_step(get_cache_path, save_progress, get_available_caches):
    """Main function for step 1: Email validation and company extraction"""
    st.header("Step 1: Email Validation & Company Extraction")
    
    # Check for previous results
    previous_caches = get_available_caches(1)
    if previous_caches:
        st.info(f"Found {len(previous_caches)} previous validation results")
        
        # Option to use previous results
        use_previous = st.expander("Use previous validation results", expanded=True)
        with use_previous:
            # Display available caches in a table
            cache_df = pd.DataFrame(previous_caches)
            st.dataframe(cache_df[['timestamp', 'rows', 'description']])
            
            selected_cache = st.selectbox(
                "Select a previous result to continue with", 
                options=cache_df['filepath'].tolist(),
                format_func=lambda x: f"{os.path.basename(x)} - {cache_df[cache_df['filepath']==x]['description'].iloc[0]}"
            )
            
            if st.button("Load Selected Result"):
                with st.spinner("Loading previous results..."):
                    previous_df = pd.read_excel(selected_cache)
                    st.session_state.current_df = previous_df
                    st.success(f"Loaded {len(previous_df)} records from previous validation")
                    
                    # Display preview of the data
                    st.subheader("Preview of Loaded Data")
                    st.dataframe(previous_df.head(10))
                    
                    # Display validation summary
                    if 'valid_email' in previous_df.columns:
                        valid_count = previous_df['valid_email'].sum()
                        total_count = len(previous_df)
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Total Emails", total_count)
                        col2.metric("Valid Emails", int(valid_count))
                        col3.metric("Invalid Emails", total_count - int(valid_count))
                    
                    return
    
    # Or start a new validation
    st.subheader("Start New Validation")
    
    # File upload section
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            # Read the Excel file
            df = pd.read_excel(uploaded_file)
            st.session_state.original_df = df.copy()
            
            # Display file info
            st.success(f"File loaded successfully: {uploaded_file.name}")
            st.info(f"Total rows: {len(df)}, Total columns: {len(df.columns)}")
            
            # Data preview
            st.subheader("Data Preview (First 10 Rows)")
            st.dataframe(df.head(10))
            
            # Column selection for email
            email_column = st.selectbox(
                "Which column contains email addresses?",
                options=df.columns.tolist()
            )
            
            # Validation options
            col1, col2 = st.columns(2)
            with col1:
                max_workers = st.slider(
                    "Parallel validation threads", 
                    1, 10, 5, 
                    help="Higher values are faster but may hit rate limits"
                )
            
            with col2:
                description = st.text_input(
                    "Description for this validation run",
                    value=f"Validation of {uploaded_file.name}"
                )
            
            # Start validation
            if st.button("Start Validation", type="primary"):
                with st.spinner("Validating emails and extracting company names..."):
                    result_df = process_dataframe(df, email_column, max_workers)
                
                if result_df is not None:
                    # Save to cache
                    cache_path = save_progress(1, result_df, description)
                    st.session_state.current_df = result_df
                    
                    # Display validation results
                    valid_count = result_df['valid_email'].sum()
                    total_count = len(result_df)
                    
                    st.subheader("Validation Results")
                    
                    # Create metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Emails", total_count)
                    col2.metric("Valid Emails", int(valid_count))
                    col3.metric("Invalid Emails", total_count - int(valid_count))
                    
                    # Show validation results
                    st.subheader("Preview of Validated Data")
                    st.dataframe(result_df.head(10))
                    
                    # Display company names extracted
                    st.subheader("Companies Extracted")
                    company_counts = result_df['company_name'].value_counts().head(20)
                    st.bar_chart(company_counts)
                    
                    # Success message
                    st.success(f"Validation complete! Results saved to cache: {os.path.basename(cache_path)}")
                    
                    # Next steps guidance
                    st.info("You can now proceed to Step 2: Email Generation")
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    else:
        # Instructions when no file is uploaded
        st.info("Please upload an Excel file to begin validation or select a previous result.")
        
        # Sample format
        with st.expander("Expected file format", expanded=False):
            sample_df = pd.DataFrame({
                'firstName': ['John', 'Jane', 'Eric'],
                'lastName': ['Doe', 'Smith', 'Johnson'],
                'email': ['john.doe@company.com', 'jane.smith@example.com', 'eric.johnson@domain.com'],
                'jobTitle': ['Manager', 'Director', 'Analyst']
            })
            st.dataframe(sample_df) 