import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

logger = logging.getLogger("omni_english.email")

class EmailService:
    @staticmethod
    def send_otp_email(to_email: str, otp_code: str, username: str = "Bạn") -> bool:
        load_dotenv(override=True)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        from_email = os.getenv("EMAIL_FROM", smtp_user or "noreply@omnienglish.com")

        subject = f"[{otp_code}] Mã xác nhận đặt lại mật khẩu - OmniEnglish"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 520px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
                .logo {{ font-size: 24px; font-weight: 800; color: #1e50e6; text-decoration: none; display: inline-block; margin-bottom: 24px; }}
                .title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }}
                .text {{ font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 24px; }}
                .otp-box {{ background-color: #eff6ff; border: 2px dashed #3b82f6; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px; }}
                .otp-code {{ font-size: 32px; font-weight: 900; letter-spacing: 8px; color: #1e50e6; margin: 0; font-family: monospace; }}
                .warning {{ font-size: 12px; color: #94a3b8; line-height: 1.5; border-t: 1px solid #f1f5f9; padding-top: 16px; margin-top: 24px; }}
                .footer {{ text-align: center; margin-top: 24px; font-size: 12px; color: #94a3b8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="#" class="logo">🎓 OmniEnglish</a>
                <div class="title">Xin chào {username},</div>
                <div class="text">
                    Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản OmniEnglish liên kết với email <strong>{to_email}</strong>.
                </div>
                <div class="otp-box">
                    <div style="font-size: 12px; font-weight: 700; color: #3b82f6; text-transform: uppercase; margin-bottom: 8px;">Mã OTP xác nhận của bạn</div>
                    <div class="otp-code">{otp_code}</div>
                </div>
                <div class="text">
                    Mã xác nhận này có hiệu lực trong <strong>10 phút</strong>. Vui lòng không chia sẻ mã này cho bất kỳ ai để đảm bảo an toàn tài khoản.
                </div>
                <div class="warning">
                    Nếu bạn không yêu cầu đặt lại mật khẩu, bạn có thể bỏ qua email này. Tài khoản của bạn vẫn được bảo mật an toàn.
                </div>
            </div>
            <div class="footer">
                © 2024 OmniEnglish Language Systems. All rights reserved.
            </div>
        </body>
        </html>
        """

        # Log OTP clearly in console for local dev testing
        try:
            print("\n" + "="*50)
            print(f"[EMAIL SERVICE - OTP GENERATED]")
            print(f"   To: {to_email}")
            print(f"   OTP Code: {otp_code}")
            print("="*50 + "\n")
        except Exception:
            pass

        # Send via SMTP if credentials are configured
        if smtp_user and smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = from_email
                msg["To"] = to_email
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(from_email, to_email, msg.as_string())

                logger.info(f"OTP email sent successfully to {to_email}")
                return True
            except Exception as e:
                logger.error(f"Failed to send email via SMTP: {e}")
                return False

        logger.info("SMTP credentials not configured. OTP printed to console log.")
        return True
