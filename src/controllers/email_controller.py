import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders


# Updated SMTP Config (GoDaddy / secureserver.net)
SMTP_CONFIG = {
    "host": "mail.dceconnect.in",
    "port": 465,
    "username": "support@dceconnect.in",
    "password": "Support@2025",
    "from_email": "support@dceconnect.in",
    "sender_name": "DCE Support"
}

def send_enrollment_email(
    to_email,
    full_name,
    enroll_no,
    qr_path=None,
    attachment_ids=None,
    addons_file_paths=None,
    logo_path="src/assets/logo.png",
    cc_email_sent=False
):

    if not to_email:
        return {"error": "Email address not provided"}

    try:
        print("Preparing email...")

        # MIMEMultipart (related) enables inline images
        msg = MIMEMultipart("related")
        msg["From"] = f"{SMTP_CONFIG['sender_name']} <{SMTP_CONFIG['from_email']}>"
        msg["To"] = to_email
        msg["Subject"] = "Registration Confirmed - KVS Soolakkarai Alumni Meet"


        # Alternative part for HTML
        msg_alt = MIMEMultipart("alternative")
        msg.attach(msg_alt)

        # Email HTML template
        html = f"""
        <html>
        <body style="font-family:Arial; background:#f5f7fa; padding:20px;">
            <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px; box-shadow:0 010px #ddd;">

                <h2 style="text-align:center; color:#1e3a8a;">KVS Soolakkarai Alumni Meet 2025</h2>

                <p>Dear <strong>{full_name}</strong>,</p>

                <p>
                    Thank you for registering for the 
                    <strong>4th KVS Soolakkarai Alumni Meet</strong>.<br>
                    Your registration has been successfully received.
                </p>

                <!-- ⚠️ Kit Bag Notice -->
                <div style="
                    border-left:4px solid #f59e0b;
                    background:#fff7ed;
                    padding:10px 15px;
                    margin:18px 0;
                    border-radius:6px;
                ">
                    <p style="margin:0; color:#92400e;">
                        👉 <strong>Important Note:</strong><br>
                        Registrations completed <strong>after 17th December</strong> will
                        <strong>not be eligible for the KIT Bag</strong>.
                        However, all registered alumni are warmly invited to attend the Alumni Meet
                        and enjoy the event along with our special lunch.
                    </p>
                </div>

                <div style="border-left:4px solid #1e3a8a; 
                            background:#eef3ff; 
                            padding:10px 15px; 
                            margin:20px 0;">
                    <h3 style="margin-top:0;">Event Details</h3>

                    <p>📅 <strong>Date:</strong> 28 Dec 2025</p>
                    <p>⏰ <strong>Time:</strong> 07:00 AM – 02:00 PM</p>
                    <p>📍 <strong>Venue:</strong> Kshatriya Vidyasala English Medium School, Virudhunagar</p>
                </div>

                <p>
                    We look forward to welcoming you and reconnecting with fellow alumni across all batches. <br>
                    Further event updates and instructions will be shared with you soon.
                </p>

                <p>
                    If you have any questions, feel free to reach out: 
                    <a href="mailto:kvssoolakkaraiobavnr@gmail.com">kvssoolakkaraiobavnr@gmail.com</a>
                </p>

                <p>
                    Warm regards,<br>
                    <strong>KVS Soolakkarai Alumni Association</strong>
                </p>

                <br>
                <img src="cid:logo_image" style="width:120px; opacity:0.9;">
            </div>
        </body>
        </html>
        """

        msg_alt.attach(MIMEText(html, "html"))

        # Attach QR Code
        if qr_path and os.path.exists(qr_path):
            with open(qr_path, "rb") as f:
                mime = MIMEBase("image", "png")
                mime.set_payload(f.read())
                encoders.encode_base64(mime)
                mime.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{os.path.basename(qr_path)}"'
                )
                msg.attach(mime)
            print("QR Code attached")

        # DB Attachment IDs
        
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
            server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
            server.sendmail(
                SMTP_CONFIG["from_email"],
                [to_email],
                msg.as_string()
            )

        print("Email sent successfully!")
        return {"success": True, "message": "Email sent successfully"}

    except Exception as e:
        print("❌ EMAIL ERROR:", e)
        return {"error": str(e)}



def send_html_email(to_emails, subject, html_body, cc_emails=None, reply_to=None):
    """Send HTML email to one or more recipients (optional CC)."""
    to_list = [e.strip() for e in (to_emails if isinstance(to_emails, (list, tuple)) else [to_emails]) if e and str(e).strip()]
    if not to_list:
        return {"error": "No recipient email address"}

    cc_list = [e.strip() for e in (cc_emails or []) if e and str(e).strip()]
    cc_list = [e for e in cc_list if e.lower() not in {t.lower() for t in to_list}]

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{SMTP_CONFIG['sender_name']} <{SMTP_CONFIG['from_email']}>"
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.attach(MIMEText(html_body, "html"))

        recipients = to_list + cc_list
        with smtplib.SMTP_SSL(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
            server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
            server.sendmail(SMTP_CONFIG["from_email"], recipients, msg.as_string())
        return {"success": True, "message": "Email sent successfully"}
    except Exception as e:
        print("EMAIL ERROR:", e)
        return {"error": str(e)}


def send_otp_email(to_email, otp_code):
    if not to_email:
        return {"error": "Email address not provided"}

    try:
        print("Preparing OTP email...")

        msg = MIMEMultipart()
        msg["From"] = f"DCE Support OTP <{SMTP_CONFIG['from_email']}>"
        msg["To"] = to_email
        msg["Subject"] = "Your Password Reset OTP - DCE"

        # Email HTML template
        html = f"""
<html>
<body style="font-family:Arial; background:#f5f7fa; padding:20px;">
    <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px; box-shadow:0 0 10px #ddd;">

        <h2 style="text-align:center; color:#1e3a8a;">DCE - Password Reset</h2>

        <p>Dear User,</p>

        <p>
            You have requested to reset your password. Here is your OTP:
        </p>

        <div style="border-left:4px solid #1e3a8a; 
                    background:#eef3ff; 
                    padding:15px; 
                    margin:20px 0;
                    text-align:center;">
            <h3 style="margin-top:0; color:#1e3a8a;">Your OTP</h3>
            <p style="font-size:32px; font-weight:bold; letter-spacing:8px; color:#1e3a8a;">{otp_code}</p>
        </div>

        <p>
            This OTP is valid for 10 minutes only. Please use it to reset your password.
        </p>

        <p>
            If you didn't request this, you can safely ignore this email.
        </p>

        <p>
            If you have any questions, feel free to reach out: 
            <a href="mailto:support@dceconnect.in">support@dceconnect.in</a>
        </p>

        <p>
            Warm regards,<br>
            <strong>DCE Support Team</strong>
        </p>
    </div>
</body>
</html>
"""
        msg.attach(MIMEText(html, "html"))

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
            server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
            server.sendmail(
                SMTP_CONFIG["from_email"],
                [to_email],
                msg.as_string()
            )

        print("OTP email sent successfully!")
        return {"success": True, "message": "OTP sent successfully"}

    except Exception as e:
        print("❌ OTP EMAIL ERROR:", e)
        return {"error": str(e)}
