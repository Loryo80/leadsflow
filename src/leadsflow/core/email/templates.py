"""
Email Template Manager
=====================

This module manages email templates for content generation:
1. Predefined templates
2. Template loading and saving
3. Template parameter management
"""

import os
import json
import streamlit as st
from datetime import datetime

# Directory for template storage
TEMPLATES_DIR = "templates"
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR)

# Default templates
DEFAULT_TEMPLATES = {
    "introduction": {
        "name": "Introduction",
        "description": "First contact with a potential lead",
        "subject": "Connecting with {{firstName}} from {{company}}",
        "body": """
Dear {{firstName}},

I hope this email finds you well. My name is {{senderName}} from {{senderCompany}}, and I noticed your role as {{jobTitle}} at {{company}}.

{{companyIntro}}

I'd love to connect and explore how we might be able to help {{company}} with {{valueProposition}}.

Would you be available for a quick 15-minute call next week to discuss this further?

Best regards,
{{senderName}}
{{senderTitle}}
{{senderCompany}}
{{senderPhone}}
"""
    },
    
    "follow_up": {
        "name": "Follow-up",
        "description": "Follow up on a previous contact",
        "subject": "Following up on {{topic}}",
        "body": """
Hello {{firstName}},

I wanted to follow up on my previous email regarding {{topic}}. 

{{company}} is in a perfect position to benefit from our {{offering}} based on your role as {{jobTitle}}.

{{valueProposition}}

I'd be happy to provide more information or schedule a brief call if you're interested.

Best regards,
{{senderName}}
{{senderTitle}}
{{senderCompany}}
{{senderPhone}}
"""
    },
    
    "event_invitation": {
        "name": "Event Invitation",
        "description": "Invite contact to an event or webinar",
        "subject": "Invitation: {{eventName}} on {{eventDate}}",
        "body": """
Dear {{firstName}},

I'm reaching out because we're hosting {{eventName}} on {{eventDate}} that I think would be valuable for someone in your position as {{jobTitle}} at {{company}}.

{{eventDescription}}

Would you be interested in attending? I'd be happy to send you the registration details.

Best regards,
{{senderName}}
{{senderTitle}}
{{senderCompany}}
{{senderPhone}}
"""
    },
    
    "case_study": {
        "name": "Case Study",
        "description": "Share a relevant case study",
        "subject": "How we helped a {{industry}} company improve {{metricName}}",
        "body": """
Dear {{firstName}},

I thought you might be interested in a recent case study about how we helped a company similar to {{company}} in the {{industry}} industry.

Our client was facing challenges with {{painPoint}}, which I understand is common in your industry. Through our collaboration, they were able to {{achievement}}.

I'd be happy to share the complete case study and discuss how we might be able to achieve similar results for {{company}}.

Best regards,
{{senderName}}
{{senderTitle}}
{{senderCompany}}
{{senderPhone}}
"""
    }
}

def load_templates():
    """Load all templates from file or use defaults"""
    templates = DEFAULT_TEMPLATES.copy()
    
    # Check for user templates
    template_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith('.json')]
    
    for file in template_files:
        try:
            with open(os.path.join(TEMPLATES_DIR, file), 'r') as f:
                template_data = json.load(f)
                template_id = os.path.splitext(file)[0]
                templates[template_id] = template_data
        except Exception as e:
            print(f"Error loading template {file}: {str(e)}")
    
    return templates

def save_template(template_id, template_data):
    """Save a template to file"""
    filepath = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
    
    with open(filepath, 'w') as f:
        json.dump(template_data, f, indent=2)
    
    return filepath

def extract_template_variables(template_text):
    """Extract all variables from a template (text between {{ and }})"""
    import re
    pattern = r'{{(.*?)}}'
    variables = re.findall(pattern, template_text)
    return sorted(list(set(variables)))

def render_template(template_text, params):
    """
    Render a template with the given parameters
    Simple implementation - for more complex needs, consider using a proper template engine
    """
    result = template_text
    for key, value in params.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    return result

def template_editor(templates=None, selected_template=None):
    """Streamlit interface for template editing"""
    if templates is None:
        templates = load_templates()
    
    st.subheader("Email Template Editor")
    
    # Template selection
    template_options = list(templates.keys())
    template_id = st.selectbox(
        "Select template to edit",
        options=template_options,
        index=template_options.index(selected_template) if selected_template in template_options else 0,
        format_func=lambda x: templates[x]["name"]
    )
    
    template = templates[template_id]
    
    # Edit form
    with st.form("template_editor_form"):
        name = st.text_input("Template Name", value=template.get("name", ""))
        description = st.text_input("Description", value=template.get("description", ""))
        subject = st.text_input("Subject Line", value=template.get("subject", ""))
        body = st.text_area("Email Body", value=template.get("body", ""), height=300)
        
        # Extract variables for reference
        all_variables = extract_template_variables(subject + " " + body)
        
        # Save button
        submit = st.form_submit_button("Save Template")
        
        if submit:
            new_template = {
                "name": name,
                "description": description,
                "subject": subject,
                "body": body,
                "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            templates[template_id] = new_template
            filepath = save_template(template_id, new_template)
            st.success(f"Template saved to {filepath}")
    
    # Show template variables
    if all_variables:
        st.subheader("Template Variables")
        st.write("The following variables are used in this template:")
        for var in all_variables:
            st.write(f"- `{{{{{var}}}}}`")
    
    # Preview section
    with st.expander("Template Preview", expanded=False):
        # Sample data for preview
        sample_data = {
            "firstName": "John",
            "lastName": "Smith",
            "company": "Acme Inc",
            "jobTitle": "Marketing Director",
            "senderName": "Sarah Johnson",
            "senderTitle": "Account Executive",
            "senderCompany": "Your Company",
            "senderPhone": "(555) 123-4567",
            "companyIntro": "We specialize in helping businesses like yours improve their marketing ROI through data-driven strategies.",
            "valueProposition": "optimizing your marketing campaigns for better ROI",
            "topic": "improving your marketing analytics",
            "offering": "marketing analytics platform",
            "eventName": "Digital Marketing Optimization Webinar",
            "eventDate": "June 15th at 2pm EST",
            "eventDescription": "Our experts will share proven strategies for improving conversion rates in the current market.",
            "industry": "retail",
            "metricName": "customer retention",
            "painPoint": "declining customer retention rates",
            "achievement": "increased customer retention by 27% in just 3 months"
        }
        
        # Fill in any missing variables
        for var in all_variables:
            if var not in sample_data:
                sample_data[var] = f"[{var}]"
        
        # Render preview
        preview_subject = render_template(subject, sample_data)
        preview_body = render_template(body, sample_data)
        
        st.markdown(f"**Subject:** {preview_subject}")
        st.markdown("**Body:**")
        st.text(preview_body)
    
    return templates, template_id

def create_new_template():
    """Create a new template"""
    templates = load_templates()
    
    st.subheader("Create New Template")
    
    new_id = st.text_input(
        "Template ID (no spaces, lowercase)",
        value=f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    if new_id in templates:
        st.error("Template ID already exists. Please choose another.")
        return
    
    # Create basic template
    new_template = {
        "name": "New Template",
        "description": "Description of this template",
        "subject": "Subject line with {{variable}}",
        "body": "Dear {{firstName}},\n\nYour email body here.\n\nRegards,\n{{senderName}}",
        "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add to templates dict
    templates[new_id] = new_template
    
    # Save
    filepath = save_template(new_id, new_template)
    st.success(f"New template created: {new_id}")
    
    # Open editor
    templates, _ = template_editor(templates, new_id)
    
    return templates, new_id

def get_template_parameters(template_id, custom_params=None):
    """Get parameters with descriptions for a template"""
    templates = load_templates()
    template = templates.get(template_id, {})
    
    # Extract variables
    all_variables = extract_template_variables(
        template.get("subject", "") + " " + template.get("body", "")
    )
    
    # Common parameter descriptions
    param_descriptions = {
        "firstName": "Recipient's first name",
        "lastName": "Recipient's last name",
        "company": "Recipient's company name",
        "jobTitle": "Recipient's job title",
        "senderName": "Your full name",
        "senderTitle": "Your job title",
        "senderCompany": "Your company name",
        "senderPhone": "Your phone number",
        "companyIntro": "Brief description of your company",
        "valueProposition": "Value you can provide to the recipient",
        "topic": "Main topic of the email",
        "offering": "Your product or service offering",
        "eventName": "Name of the event or webinar",
        "eventDate": "Date and time of the event",
        "eventDescription": "Description of the event",
        "industry": "Recipient's industry",
        "metricName": "Metric you helped improve",
        "painPoint": "Common pain point in recipient's industry",
        "achievement": "Achievement or result from your solution"
    }
    
    # Override with custom parameter descriptions if provided
    if custom_params:
        param_descriptions.update(custom_params)
    
    # Create parameter dict with descriptions
    parameters = {}
    for var in all_variables:
        parameters[var] = {
            "name": var,
            "description": param_descriptions.get(var, f"Value for {var}"),
            "required": True
        }
    
    return parameters 