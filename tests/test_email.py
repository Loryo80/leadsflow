import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import sys

# Add src directory to Python path to allow importing leadsflow module
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, SRC_DIR)

from src.leadsflow.core.config.env_loader import get_smtp_config

def send_email_via_smtp(to_email, subject, body, smtp_server, smtp_port, 
                        smtp_username, smtp_password, from_email, use_ssl=True):
    """
    Send an email using SMTP instead of Outlook
    
    Parameters:
    - to_email: Recipient email address
    - subject: Email subject
    - body: Email body content
    - smtp_server: SMTP server address (e.g., smtp.gmail.com)
    - smtp_port: SMTP port (e.g., 587 for TLS, 465 for SSL)
    - smtp_username: SMTP username
    - smtp_password: SMTP password
    - from_email: Sender email address
    - use_ssl: Whether to use SSL (True) or TLS (False)
    
    Returns:
    - Dictionary with status and details
    """
    try:
        print(f"Setting up email to {to_email} via {smtp_server}:{smtp_port}")
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        print(f"Connecting to server with {'SSL' if use_ssl else 'TLS'}...")
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        print(f"Logging in as {smtp_username}...")
        server.login(smtp_username, smtp_password)
        
        print(f"Sending message...")
        server.send_message(msg)
        server.quit()
        print("Server connection closed")
        
        result = {
            "status": "sent",
            "details": "Email sent successfully via SMTP",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return result
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        result = {
            "status": "failed",
            "details": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return result
    

# Example usage
if __name__ == "__main__":
    print("Loading SMTP configuration from .env file...")
    smtp_config = get_smtp_config()

    # Check if essential configuration is present
    if not smtp_config.get('smtp_username') or not smtp_config.get('smtp_password'):
        print("Error: SMTP_USERNAME or SMTP_PASSWORD not found in .env file or environment variables.")
        print("Please ensure your .env file is correctly configured in the project root.")
        sys.exit(1)

    # Assign values from config
    smtp_server = smtp_config['smtp_server']
    smtp_port = smtp_config['smtp_port']
    smtp_username = smtp_config['smtp_username']
    smtp_password = smtp_config['smtp_password']
    from_email = smtp_config['from_email']
    use_ssl = smtp_config['use_ssl']

    # Test details
    to_email = "recipient@example.com"  # Replace with a valid recipient for testing
    subject = "Test Email via SMTP (from test_email.py)"
    body = f"This is a test email sent via SMTP using configuration loaded from .env at {datetime.now()}"
    
    print("Starting email test...")
    result = send_email_via_smtp(to_email, subject, body, smtp_server, smtp_port, 
                                smtp_username, smtp_password, from_email, use_ssl)
    
    print(f"Email sending result: {result}") 