"""
SMTP Email Sender
================

This module handles sending emails via SMTP:
1. Connection to SMTP server
2. Email creation and sending
3. Error handling and rate limiting
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import random
import logging
from datetime import datetime
from leadsflow.core.config.env_loader import get_smtp_config

logger = logging.getLogger("leadsflow.smtp")

class SMTPSender:
    """Class to handle SMTP email sending operations"""
    
    def __init__(self, delay_range=(2, 5), test_mode=False, config=None):
        """
        Initialize the SMTP sender
        
        Parameters:
        - delay_range: Tuple with min and max seconds to delay between emails
        - test_mode: If True, emails will be logged but not sent
        - config: SMTP configuration dictionary (if None, loaded from environment)
        """
        self.delay_range = delay_range
        self.test_mode = test_mode
        
        # Load SMTP config from environment if not provided
        if config is None:
            self.config = get_smtp_config()
        else:
            self.config = config
            
        # Validate config
        self._validate_config()
    
    def _validate_config(self):
        """Validate SMTP configuration"""
        required_fields = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
        missing_fields = [field for field in required_fields if not self.config.get(field)]
        
        if missing_fields:
            logger.warning(f"Missing SMTP configuration fields: {', '.join(missing_fields)}")
            self.configured = False
        else:
            self.configured = True
    
    def create_email(self, to_email, subject, body, cc=None, bcc=None, html_body=False, 
                     tracking=False, importance=1):
        """
        Create an email message
        
        Parameters:
        - to_email: Recipient email address(es)
        - subject: Email subject
        - body: Email body content
        - cc: Carbon copy recipient(s)
        - bcc: Blind carbon copy recipient(s)
        - html_body: If True, body is treated as HTML
        - tracking: If True, add tracking headers (not always supported)
        - importance: 0=Low, 1=Normal, 2=High
        
        Returns:
        - MIMEMultipart message object
        """
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.config.get('from_email', self.config.get('smtp_username', ''))
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC and BCC if provided
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
        
        # Add body
        if html_body:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Set importance
        if importance == 0:  # Low
            msg['Importance'] = 'low'
            msg['X-Priority'] = '5'
        elif importance == 2:  # High
            msg['Importance'] = 'high'
            msg['X-Priority'] = '1'
        
        # Set tracking (read receipt)
        if tracking:
            msg['Disposition-Notification-To'] = self.config.get('from_email', self.config.get('smtp_username', ''))
        
        return msg
    
    def send_email(self, to_email, subject, body, **kwargs):
        """
        Create and send an email
        
        Parameters:
        - to_email: Recipient email address(es)
        - subject: Email subject
        - body: Email body content
        - **kwargs: Additional parameters for create_email
        
        Returns:
        - Dict with status and details
        """
        if not self.configured:
            return {
                "status": "failed",
                "details": "SMTP not properly configured. Check your .env file.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        try:
            # Create the email
            msg = self.create_email(to_email, subject, body, **kwargs)
            
            # Log email creation
            logger.info(f"Created email to {to_email} with subject '{subject}'")
            
            if self.test_mode:
                # In test mode, log the email but don't send
                logger.info(f"TEST MODE: Would send email to {to_email}")
                result = {
                    "status": "test",
                    "details": "Email created but not sent (test mode)",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                # Send the email
                self._send_message(msg, to_email)
                result = {
                    "status": "sent",
                    "details": "Email sent successfully via SMTP",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                logger.info(f"Email sent to {to_email}")
            
            # Add random delay to avoid triggering spam filters
            delay = random.uniform(self.delay_range[0], self.delay_range[1])
            logger.debug(f"Waiting {delay:.1f}s before next email")
            time.sleep(delay)
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return {
                "status": "failed",
                "details": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def _send_message(self, msg, to_email):
        """
        Send a message via SMTP
        
        Parameters:
        - msg: MIMEMultipart message object
        - to_email: Recipient email for logging
        """
        use_ssl = self.config.get('use_ssl', True)
        server = None
        
        try:
            # Connect to server
            if use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config['smtp_server'], 
                    self.config['smtp_port']
                )
            else:
                server = smtplib.SMTP(
                    self.config['smtp_server'], 
                    self.config['smtp_port']
                )
                server.starttls()
            
            # Login to server
            server.login(
                self.config['smtp_username'],
                self.config['smtp_password']
            )
            
            # Get all recipients
            recipients = []
            
            # Add To recipients
            to_emails = msg['To'].split(',')
            recipients.extend([email.strip() for email in to_emails])
            
            # Add CC recipients if present
            if msg.get('Cc'):
                cc_emails = msg['Cc'].split(',')
                recipients.extend([email.strip() for email in cc_emails])
            
            # Add BCC recipients if present
            if msg.get('Bcc'):
                bcc_emails = msg['Bcc'].split(',')
                recipients.extend([email.strip() for email in bcc_emails])
            
            # Send the message
            server.send_message(msg)
            
        finally:
            # Close connection
            if server:
                server.quit()

# Context manager for SMTP connections
class SMTPConnection:
    """Context manager for SMTP connections"""
    
    def __init__(self, **kwargs):
        self.sender = SMTPSender(**kwargs)
    
    def __enter__(self):
        return self.sender
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # Nothing to clean up

# Helper function to check if SMTP is configured
def is_smtp_available():
    """Check if SMTP is properly configured"""
    config = get_smtp_config()
    required_fields = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
    return all(config.get(field) for field in required_fields) 