import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings=None):
        settings = settings or {}
        self.smtp_host = settings.get('smtp.host', 'localhost')
        self.smtp_port = int(settings.get('smtp.port', 587))
        self.smtp_user = settings.get('smtp.user', '')
        self.smtp_password = settings.get('smtp.password', '')
        self.from_email = settings.get('smtp.from_email', 'noreply@analytics.local')
        self.use_tls = settings.get('smtp.use_tls', 'true').lower() == 'true'

    def send_email(self, to_email: str, subject: str, body: str, html_body: str = None) -> bool:
        """Send an email notification."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # HTML version (if provided)
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Send the email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [to_email], msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise

    def send_welcome_email(self, user_email: str, user_name: str = None) -> bool:
        """Send a welcome email to a new user."""
        name = user_name or 'there'
        subject = 'Welcome to Analytics Platform'
        body = f"""Hi {name},

Welcome to the Analytics Platform! Your account has been created successfully.

You can now start tracking events and setting up notifications.

Best regards,
The Analytics Team
"""
        html_body = f"""
<html>
<body>
<h2>Welcome to Analytics Platform!</h2>
<p>Hi {name},</p>
<p>Your account has been created successfully.</p>
<p>You can now start tracking events and setting up notifications.</p>
<p>Best regards,<br>The Analytics Team</p>
</body>
</html>
"""
        return self.send_email(user_email, subject, body, html_body)

    def send_notification_email(self, to_email: str, title: str, content: str) -> bool:
        """Send a notification email."""
        html_body = f"""
<html>
<body>
<h2>{title}</h2>
<p>{content}</p>
<hr>
<p style="color: #666; font-size: 12px;">
This is an automated notification from Analytics Platform.
</p>
</body>
</html>
"""
        return self.send_email(to_email, title, content, html_body)
