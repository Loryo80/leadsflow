"""
LLM Email Content Generator
==========================

This module handles generating personalized email content using OpenAI's API:
1. Structured content generation with clear parameters
2. Error handling and fallbacks
3. Template rendering with LLM-generated content
"""

import os
import openai
import json
import time
import logging
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import streamlit as st

logger = logging.getLogger("leadsflow.llm")

# Email content model
class EmailContent(BaseModel):
    subject: str = Field(..., description="Attention-grabbing subject line relevant to the recipient's role and company")
    body: str = Field(..., description="Personalized email body that provides value and includes a clear CTA")
    
    class Config:
        schema_extra = {
            "example": {
                "subject": "Improving Customer Engagement at Acme Inc",
                "body": "Dear John,\n\nI noticed your role as Marketing Director at Acme Inc and wanted to connect about improving customer engagement metrics...",
            }
        }

class LLMGenerator:
    """Class to handle LLM email content generation"""
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo", temperature=0.7, max_tokens=500, timeout=30):
        """
        Initialize the LLM generator
        
        Parameters:
        - api_key: OpenAI API key (will use os.environ['OPENAI_API_KEY'] if None)
        - model: Model to use for generation
        - temperature: Controls randomness (0=deterministic, 1=creative)
        - max_tokens: Maximum tokens to generate
        - timeout: Timeout for API calls in seconds
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Set API key
        if api_key:
            openai.api_key = api_key
        elif 'OPENAI_API_KEY' in os.environ:
            openai.api_key = os.environ['OPENAI_API_KEY']
        elif hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            openai.api_key = st.secrets['OPENAI_API_KEY']
        else:
            raise ValueError("OpenAI API key not found. Please provide it or set OPENAI_API_KEY environment variable.")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI()
    
    def generate_email(self, template, params, company_context=None, language="en"):
        """
        Generate personalized email content using LLM
        
        Parameters:
        - template: Template string or dict with template properties
        - params: Dict of parameters to fill in the template
        - company_context: Additional context about the company
        - language: Target language code (en, fr, ar, etc.)
        
        Returns:
        - EmailContent object with subject and body
        """
        # Get template content
        if isinstance(template, dict):
            template_subject = template.get('subject', '')
            template_body = template.get('body', '')
            template_name = template.get('name', 'custom template')
        else:
            template_subject = ''
            template_body = template
            template_name = 'custom template'
        
        # Pre-process the params to ensure all values are strings and replace None values
        processed_params = {}
        for key, value in params.items():
            if value is None:
                processed_params[key] = f"[{key}]"  # Placeholder for missing values
            else:
                processed_params[key] = str(value)
        
        # Pre-fill the template with actual values before sending to LLM
        for key, value in processed_params.items():
            placeholder = f"{{{{{key}}}}}"
            template_subject = template_subject.replace(placeholder, value)
            template_body = template_body.replace(placeholder, value)
        
        # Language-specific instructions
        language_instructions = {
            "en": "Write the email in English.",
            "fr": "Write the email in French (français).",
            "ar": "Write the email in Arabic (العربية).",
            "es": "Write the email in Spanish (español).",
            "de": "Write the email in German (Deutsch).",
            "zh": "Write the email in Chinese (中文).",
        }
        
        language_instruction = language_instructions.get(language, f"Write the email in {language}.")
        
        # Create system prompt
        system_prompt = f"""
        You are an expert sales development representative creating highly personalized outreach emails.
        {language_instruction}
        
        Follow these guidelines:
        1. Use a professional, friendly tone
        2. Keep emails concise (3-5 short paragraphs)
        3. Include specific details about the recipient's company and role
        4. Provide clear value proposition
        5. End with a clear call to action
        6. IMPORTANT: Use the recipient's actual job title and company name in the email
        7. Make sure to properly address the recipient by their first name
        8. DO NOT include template variables like {{firstName}} or {{company}} in your output

        Additional context about the company: {company_context or 'Not provided'}
        """
        
        # Create user prompt with the template and parameters
        user_prompt = f"""
        Please create a personalized email based on this template:
        
        Subject: {template_subject}
        
        Body:
        {template_body}
        
        The information about the recipient:
        - First name: {processed_params.get('firstName', '[firstName]')}
        - Last name: {processed_params.get('lastName', '[lastName]')}
        - Company: {processed_params.get('company', '[company]')}
        - Job title: {processed_params.get('jobTitle', '[jobTitle]')}
        
        The information about the sender:
        - Name: {processed_params.get('senderName', '[senderName]')}
        - Title: {processed_params.get('senderTitle', '[senderTitle]')}
        - Company: {processed_params.get('senderCompany', '[senderCompany]')}
        - Phone: {processed_params.get('senderPhone', '[senderPhone]')}
        
        Make it sound natural and conversational, not like a template. Adjust wording as needed.
        Be specific and personalized - explicitly mention their job title, company name, and other 
        details to make the email feel custom-written for them personally.
        
        Return the result as a JSON object with 'subject' and 'body' fields.
        """
        
        try:
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout
            )
            
            content = json.loads(response.choices[0].message.content)
            
            # Parse the response into the Pydantic model
            email_content = EmailContent(
                subject=content.get("subject", "No subject generated"),
                body=content.get("body", "No body generated")
            )
            
            logger.info(f"Successfully generated email content using {self.model}")
            return email_content
            
        except Exception as e:
            logger.error(f"Error generating email with LLM: {str(e)}")
            
            # Return a fallback
            return EmailContent(
                subject=f"Connecting about {params.get('company', 'your company')}",
                body=f"Error generating personalized content: {str(e)}\n\nPlease try again later."
            )
    
    def batch_generate(self, rows, template, sender_info, max_retries=2, retry_delay=5, language="en"):
        """
        Generate emails for a batch of recipient data
        
        Parameters:
        - rows: List of dicts with recipient data
        - template: Template to use
        - sender_info: Dict with sender information
        - max_retries: Maximum number of retries for failed generations
        - retry_delay: Delay between retries in seconds
        - language: Target language code (en, fr, ar, etc.)
        
        Returns:
        - List of dicts with generation results
        """
        results = []
        
        for row in rows:
            retry_count = 0
            success = False
            
            while not success and retry_count <= max_retries:
                try:
                    # Prepare parameters for template
                    first_name = row.get('firstName', row.get('first_name', ''))
                    last_name = row.get('lastName', row.get('last_name', ''))
                    company_name = row.get('company_name', 'your company')
                    job_title = row.get('jobTitle', row.get('job_title', 'professional'))
                    
                    params = {
                        "firstName": first_name,
                        "lastName": last_name,
                        "company": company_name,
                        "jobTitle": job_title,
                        "senderName": sender_info.get('name', ''),
                        "senderTitle": sender_info.get('title', ''),
                        "senderCompany": sender_info.get('company', ''),
                        "senderPhone": sender_info.get('phone', ''),
                        "companyIntro": sender_info.get('company_intro', ''),
                        "valueProposition": sender_info.get('value_proposition', '')
                    }
                    
                    # Print the parameters for debugging
                    print(f"Params for {row.get('email')}: {params}")
                    
                    # Ensure all parameters are strings
                    for key in params:
                        if params[key] is None:
                            params[key] = f"[{key}]"
                        else:
                            params[key] = str(params[key])
                    
                    # Get any additional company context
                    company_context = f"Company: {company_name}, Industry: Finance/Banking, " + \
                                     f"Job Title: {job_title}, Email: {row.get('email', '')}"
                                     
                    email_content = self.generate_email(
                        template=template,
                        params=params,
                        company_context=company_context,
                        language=language
                    )
                    
                    results.append({
                        "subject": email_content.subject,
                        "body": email_content.body,
                        "status": "generated" if not ("Error generating" in email_content.body) else "failed"
                    })
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Attempt {retry_count} failed for row: {row.get('email')}. Error: {str(e)}")
                    
                    if retry_count > max_retries:
                        logger.error(f"Max retries exceeded for row: {row.get('email')}. Giving up.")
                        results.append({
                            "subject": "Generation Failed",
                            "body": f"Failed to generate content after {max_retries} attempts: {str(e)}",
                            "status": "error"
                        })
                    else:
                        time.sleep(retry_delay)
        
        return results

# Helper function to check if OpenAI API key is available
def is_openai_available():
    """Check if OpenAI API key is configured"""
    if 'OPENAI_API_KEY' in os.environ and os.environ['OPENAI_API_KEY']:
        return True
    if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets and st.secrets['OPENAI_API_KEY']:
        return True
    return False

# Helper function to get available models (replace with dynamic fetch if needed)
def get_available_models():
    """Return a list of common OpenAI models"""
    # Ideally, fetch this from OpenAI API, but hardcoding for simplicity
    return [
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "o4-mini"
    ]

# Example usage
if __name__ == "__main__":
    # This code will only run when the script is executed directly
    
    # Example template and parameters
    example_template = {
        "name": "Example Introduction",
        "subject": "Exploring opportunities with {{company}}",
        "body": "Dear {{firstName}},\n\nI noticed your work as {{jobTitle}} at {{company}}. I'm reaching out from {{senderCompany}} to explore how we might collaborate.\n\nWould you be open to a brief chat next week?\n\nBest,\n{{senderName}}"
    }
    
    example_sender = {
        "name": "AI Assistant",
        "title": "Bot",
        "company": "LeadsFlow",
        "phone": "123-456-7890",
        "company_intro": "We help automate sales outreach",
        "value_proposition": "saving time and increasing efficiency"
    }
    
    example_recipients = [
        {"firstName": "Alice", "lastName": "Smith", "company": "TechCorp", "jobTitle": "Software Engineer"},
        {"firstName": "Bob", "lastName": "Jones", "company": "Innovate Inc", "jobTitle": "Product Manager"}
    ]
    
    if is_openai_available():
        generator = LLMGenerator()
        
        # Test single generation
        print("\n--- Testing Single Generation ---")
        single_result = generator.generate_email(example_template, example_recipients[0])
        print(f"Subject: {single_result.subject}")
        print(f"Body: {single_result.body}")
        
        # Test batch generation
        print("\n--- Testing Batch Generation ---")
        batch_results = generator.batch_generate(example_recipients, example_template, example_sender)
        for i, result in enumerate(batch_results):
            print(f"\nEmail {i+1} ({example_recipients[i].get('firstName')})")
            print(f"  Status: {result['status']}")
            print(f"  Subject: {result['subject']}")
            print(f"  Body: {result['body']}")
            
    else:
        print("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable to run the example.") 