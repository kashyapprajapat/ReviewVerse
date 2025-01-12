import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email_via_gmail(receiver_email, receiver_name, subject=None):
    try:
        # Sender's email credentials
        sender_email = "reviewverseone@gmail.com"  # Your Gmail address
        sender_password = "kykf npru ftzb nmea"  # Your Gmail password or App Password

        # Default subject list
        default_subject = f"Welcome to ReviewVerse! 🎉 Thank you for joining, {receiver_name}! 🎁✨"

        # Use the combined subject if none is provided
        if subject is None:
            subject = default_subject

        # Recipient's email
        recipient_email = receiver_email  # The recipient's email

        # Set up the MIME (Multipurpose Internet Mail Extensions) message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # HTML body content with dynamic name and green color
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f4f4f9; margin: 0; padding: 20px; color: #333;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td style="text-align: center; background-color: #28a745; padding: 20px;">
                <h1 style="color: white;">Welcome to ReviewVerse, {receiver_name}! 🎉</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 20px; background-color: #ffffff;">
                <p>Hello <strong>{receiver_name}</strong>,</p>
                <p>Thank you for joining ReviewVerse! We are thrilled to have you with us. 💚</p>
                <ul>
                    <li>Discover and share reviews. 📚</li>
                    <li>Get personalized book recommendations. 📖</li>
                    <li>Join discussions and engage with other readers. 🗣️</li>
                </ul>
                <p><a href="https://reviewverse.com" style="color: #28a745;">Click here to get started!</a> 🍀</p>
            </td>
        </tr>
        <tr>
            <td style="text-align: center; padding: 10px; background-color: #f4f4f9;">
                <p style="font-size: 12px; color: #888;">If you have any questions, feel free to <a href="mailto:reviewverseone@gmail.com" style="color: #28a745;">contact us</a>. 📧</p>
            </td>
        </tr>
    </table>
</body>
</html>'''

        # Attach the email body
        msg.attach(MIMEText(html_content, 'html'))

        # Set up the Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)  # Login to the server

        # Send the email
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()  # Close the connection
        
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

# Example usage: Send an email to a user
# send_email_via_gmail("kashyap.kp2003@gmail.com", "Kashyap")
