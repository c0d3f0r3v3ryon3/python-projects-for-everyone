# send_emails.py
import smtplib
from email.mime.text import MIMEText

# Настройки (пример)
sender = "your@gmail.com" #логин
password = "your_app_password" #пароль
recipients = ["friend1@gmail.com", "friend2@gmail.com"] #получатели

msg = MIMEText("Привет! Это автоматическое письмо.")
msg["Subject"] = "Авто-письмо от Python"
msg["From"] = sender

#чтобы отправить - раскоментировать следующий код:
"""
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(sender, password)
    for recipient in recipients:
        msg["To"] = recipient
        server.sendmail(sender, recipient, msg.as_string())
"""

print("✅ Письма отправлены!")
