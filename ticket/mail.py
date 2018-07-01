import smtplib
from email.mime.text import MIMEText

def sendmail(fromemail, toemail, smtpserver, subject, body):
    # Envia um e-mail
    for contact in toemail:
        msg = MIMEText(body.encode('utf-8'))
        msg.set_charset('utf-8')
        msg['Subject'] = subject
        msg['From'] = fromemail
        msg['To'] = contact
        s = smtplib.SMTP(smtpserver, timeout=10)
        s.sendmail(fromemail, contact, msg.as_string())
        s.quit()