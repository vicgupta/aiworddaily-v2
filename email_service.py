import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from dotenv import load_dotenv
from typing import List, Optional
import logging
import ssl

load_dotenv()

# Email configuration
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        if not all([EMAIL_FROM, EMAIL_USERNAME, EMAIL_PASSWORD]):
            missing = []
            if not EMAIL_FROM: missing.append("EMAIL_FROM")
            if not EMAIL_USERNAME: missing.append("EMAIL_USERNAME") 
            if not EMAIL_PASSWORD: missing.append("EMAIL_PASSWORD")
            raise ValueError(f"Missing email configuration: {', '.join(missing)}")
        
        logger.info(f"Email service initialized:")
        logger.info(f"  Host: {EMAIL_HOST}")
        logger.info(f"  Port: {EMAIL_PORT}")
        logger.info(f"  From: {EMAIL_FROM}")
        logger.info(f"  Username: {EMAIL_USERNAME}")
        logger.info(f"  Use TLS: {EMAIL_USE_TLS}")
    
    def test_connection(self):
        """Test SMTP connection without sending email"""
        try:
            logger.info(f"Testing SMTP connection to {EMAIL_HOST}:{EMAIL_PORT}")
            
            # Create SMTP connection
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            
            # Enable debug output
            server.set_debuglevel(1)
            
            logger.info("SMTP connection established")
            
            if EMAIL_USE_TLS:
                logger.info("Starting TLS encryption")
                # Create SSL context
                context = ssl.create_default_context()
                server.starttls(context=context)
                logger.info("TLS started successfully")
            
            logger.info("Attempting SMTP authentication")
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            logger.info("SMTP authentication successful")
            
            server.quit()
            logger.info("SMTP connection test completed successfully")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            logger.error("Check your EMAIL_USERNAME and EMAIL_PASSWORD")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            logger.error(f"Check EMAIL_HOST ({EMAIL_HOST}) and EMAIL_PORT ({EMAIL_PORT})")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during SMTP test: {str(e)}")
            return False
    
    def send_email(self, to_emails: List[str], subject: str, html_content: str, text_content: Optional[str] = None):
        """Send email to multiple recipients"""
        logger.info(f"Attempting to send email to {len(to_emails)} recipients")
        logger.info(f"Subject: {subject}")
        logger.debug(f"Recipients: {', '.join(to_emails[:3])}{'...' if len(to_emails) > 3 else ''}")
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = EMAIL_FROM
            msg['Subject'] = subject
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            logger.info(f"Connecting to SMTP server {EMAIL_HOST}:{EMAIL_PORT}")
            
            # Create SMTP connection with better error handling
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30)
            
            # Enable debug output for troubleshooting
            # server.set_debuglevel(1)
            
            try:
                if EMAIL_USE_TLS:
                    logger.info("Starting TLS encryption")
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    logger.info("TLS encryption started")
                
                logger.info(f"Logging in as {EMAIL_USERNAME}")
                server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                logger.info("SMTP login successful")
                
                # Send to each recipient
                successful_sends = 0
                failed_sends = 0
                
                for email in to_emails:
                    try:
                        msg['To'] = email
                        result = server.send_message(msg)
                        
                        if result:
                            logger.warning(f"Partial failure sending to {email}: {result}")
                            failed_sends += 1
                        else:
                            logger.info(f"✅ Email sent successfully to {email}")
                            successful_sends += 1
                        
                        del msg['To']
                        
                    except Exception as e:
                        logger.error(f"Failed to send to {email}: {str(e)}")
                        failed_sends += 1
                        if 'To' in msg:
                            del msg['To']
                
                logger.info(f"Email batch completed: {successful_sends} successful, {failed_sends} failed")
                
            finally:
                server.quit()
                logger.info("SMTP connection closed")
            
            return successful_sends > 0
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            logger.error("Possible causes:")
            logger.error("- Wrong username/password")
            logger.error("- 2FA enabled but not using app password")
            logger.error("- Account access blocked by provider")
            return False
            
        except smtplib.SMTPConnectError as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            logger.error(f"Check if {EMAIL_HOST}:{EMAIL_PORT} is accessible")
            return False
            
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipients refused: {str(e)}")
            return False
            
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected unexpectedly: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return False

    def create_word_email(self, word_data: dict, recipient_name: str = "Friend") -> tuple:
        """Create HTML and text content for word of the day email"""
        
        # HTML template
        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Word Daily - {{ word_data.term.title() }}</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: #f8fafc;
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 2rem;
                    text-align: center;
                }
                .header h1 {
                    margin: 0 0 0.5rem 0;
                    font-size: 2rem;
                    font-weight: 700;
                }
                .header p {
                    margin: 0;
                    opacity: 0.9;
                }
                .content {
                    padding: 2rem;
                }
                .word-section {
                    background: #f8fafc;
                    border-radius: 8px;
                    padding: 1.5rem;
                    margin-bottom: 1.5rem;
                }
                .word-term {
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: #1a202c;
                    margin-bottom: 0.5rem;
                    text-transform: capitalize;
                }
                .word-pronunciation {
                    font-style: italic;
                    color: #718096;
                    margin-bottom: 1rem;
                    font-size: 1.1rem;
                }
                .word-definition {
                    color: #4a5568;
                    margin-bottom: 1rem;
                    font-size: 1.1rem;
                    line-height: 1.6;
                }
                .word-example {
                    background: white;
                    padding: 1rem;
                    border-radius: 6px;
                    border-left: 4px solid #667eea;
                    font-style: italic;
                    color: #4a5568;
                    margin-bottom: 1rem;
                }
                .word-meta {
                    display: flex;
                    gap: 0.5rem;
                    justify-content: center;
                    flex-wrap: wrap;
                    margin-bottom: 1rem;
                }
                .badge {
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-size: 0.8rem;
                    font-weight: 500;
                    text-transform: capitalize;
                }
                .category-badge {
                    background: #e2e8f0;
                    color: #4a5568;
                }
                .difficulty-beginner { background: #c6f6d5; color: #22543d; }
                .difficulty-intermediate { background: #fef5e7; color: #c05621; }
                .difficulty-advanced { background: #fed7d7; color: #c53030; }
                .difficulty-expert { background: #e9d8fd; color: #553c9a; }
                .footer {
                    background: #f8fafc;
                    padding: 1.5rem;
                    text-align: center;
                    color: #718096;
                    font-size: 0.9rem;
                }
                .footer a {
                    color: #667eea;
                    text-decoration: none;
                }
                .cta-button {
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 0.75rem 1.5rem;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                    margin-top: 1rem;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 AI Word Daily</h1>
                    <p>{{ word_date }}</p>
                </div>
                
                <div class="content">
                    <p>Hello {{ recipient_name }},</p>
                    <p>Here's your word of the day to expand your vocabulary!</p>
                    
                    <div class="word-section">
                        <div class="word-term">{{ word_data.term }}</div>
                        {% if word_data.pronunciation %}
                        <div class="word-pronunciation">{{ word_data.pronunciation }}</div>
                        {% endif %}
                        <div class="word-definition">{{ word_data.definition }}</div>
                        {% if word_data.example %}
                        <div class="word-example">"{{ word_data.example }}"</div>
                        {% endif %}
                        <div class="word-meta">
                            {% if word_data.category %}
                            <span class="badge category-badge">{{ word_data.category }}</span>
                            {% endif %}
                            <span class="badge difficulty-{{ word_data.difficulty }}">{{ word_data.difficulty }}</span>
                        </div>
                    </div>
                    
                    <p>Keep learning and expanding your vocabulary! 🚀</p>
                    
                    <div style="text-align: center;">
                        <a href="http://localhost:8000" class="cta-button">Visit AI Word Daily</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>You're receiving this because you signed up for AI Word Daily.</p>
                    <p>© 2025 AI Word Daily. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        # Text template
        text_template = Template("""
AI Word Daily - {{ word_date }}

Hello {{ recipient_name }},

Here's your word of the day:

{{ word_data.term.upper() }}
{% if word_data.pronunciation %}{{ word_data.pronunciation }}{% endif %}

Definition: {{ word_data.definition }}

{% if word_data.example %}Example: "{{ word_data.example }}"{% endif %}

{% if word_data.category %}Category: {{ word_data.category }}{% endif %}
Difficulty: {{ word_data.difficulty.title() }}

Keep learning and expanding your vocabulary!

Visit AI Word Daily: http://localhost:8000

---
You're receiving this because you signed up for AI Word Daily.
© 2025 AI Word Daily. All rights reserved.
        """)
        
        # Format date
        from datetime import date
        word_date = word_data.get('date_published')
        if word_date:
            try:
                if isinstance(word_date, str):
                    formatted_date = date.fromisoformat(word_date).strftime("%A, %B %d, %Y")
                else:
                    formatted_date = word_date.strftime("%A, %B %d, %Y")
            except:
                formatted_date = "Today"
        else:
            formatted_date = "Today"
        
        # Render templates
        html_content = html_template.render(
            word_data=word_data,
            recipient_name=recipient_name,
            word_date=formatted_date
        )
        
        text_content = text_template.render(
            word_data=word_data,
            recipient_name=recipient_name,
            word_date=formatted_date
        )
        
        return html_content, text_content

# Create global instance
email_service = EmailService()