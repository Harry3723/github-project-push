from __future__ import annotations

import smtplib
from email.message import EmailMessage


class EmailSender:
    def __init__(
        self,
        smtp_host: str | None,
        smtp_port: int,
        smtp_username: str | None,
        smtp_password: str | None,
        smtp_use_starttls: bool,
        smtp_use_ssl: bool,
        email_from: str | None,
        email_to: list[str],
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_starttls = smtp_use_starttls
        self.smtp_use_ssl = smtp_use_ssl
        self.email_from = email_from
        self.email_to = email_to

    def is_available(self) -> bool:
        return bool(self.smtp_host and self.email_from and self.email_to)

    def send(self, content: str, subject: str) -> bool:
        if not self.is_available():
            return False
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.email_from
        message["To"] = ", ".join(self.email_to)
        message.set_content(content)
        if self.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=20) as smtp:
                self._login_if_needed(smtp)
                smtp.send_message(message)
            return True
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as smtp:
            smtp.ehlo()
            if self.smtp_use_starttls:
                smtp.starttls()
                smtp.ehlo()
            self._login_if_needed(smtp)
            smtp.send_message(message)
        return True

    def _login_if_needed(self, smtp: smtplib.SMTP) -> None:
        if self.smtp_username and self.smtp_password:
            smtp.login(self.smtp_username, self.smtp_password)
