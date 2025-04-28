"""
Template Variable Checker
========================

Utility for checking and replacing template variables in generated content
"""

import re
import logging

logger = logging.getLogger("leadsflow.placeholder_checker")

def find_template_variables(text):
    """Find all template variables in text (anything between {{ and }})"""
    if not text:
        return []
    
    pattern = r'{{(.*?)}}'
    matches = re.findall(pattern, text)
    return matches

def has_template_variables(text):
    """Check if text contains any template variables"""
    if not text:
        return False
    
    return '{{' in text and '}}' in text

def replace_variables(text, data_dict):
    """
    Replace template variables in text with values from data_dict
    
    Parameters:
    - text: Text containing template variables like {{variable}}
    - data_dict: Dictionary with variable values
    
    Returns:
    - Text with variables replaced
    """
    if not text:
        return ""
    
    result = text
    
    # Find all template variables
    variables = find_template_variables(text)
    
    # Replace each variable
    for var in variables:
        var_name = var.strip()
        placeholder = f"{{{{{var_name}}}}}"
        
        # Get value from data_dict
        if var_name in data_dict:
            value = str(data_dict[var_name])
        else:
            # If variable not found, replace with a placeholder
            value = f"[{var_name}]"
            logger.warning(f"Variable '{var_name}' not found in data")
        
        # Replace in text
        result = result.replace(placeholder, value)
    
    return result

def clean_generation(subject, body, data):
    """
    Clean generated content by replacing any remaining template variables
    
    Parameters:
    - subject: Subject line that might contain template variables
    - body: Email body that might contain template variables
    - data: Dictionary with data to replace variables
    
    Returns:
    - Tuple of (cleaned_subject, cleaned_body)
    """
    # Check and log if variables are found
    subject_vars = find_template_variables(subject)
    body_vars = find_template_variables(body)
    
    if subject_vars:
        logger.warning(f"Template variables found in subject: {subject_vars}")
    
    if body_vars:
        logger.warning(f"Template variables found in body: {body_vars}")
    
    # Replace variables
    cleaned_subject = replace_variables(subject, data)
    cleaned_body = replace_variables(body, data)
    
    return cleaned_subject, cleaned_body 