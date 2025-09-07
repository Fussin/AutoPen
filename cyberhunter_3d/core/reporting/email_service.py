from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def send_report_email(recipient: str, scan, report_path: str):
    """
    Sends a scan report email with the report as an attachment.

    :param recipient: The email address of the recipient.
    :param scan: The Scan object.
    :param report_path: The path to the report file to attach.
    """
    try:
        msg = Message(
            subject=f"CyberHunter 3D Scan Report for Scan #{scan.id}",
            recipients=[recipient],
            body=f"Please find the attached report for CyberHunter 3D scan #{scan.id}.",
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )

        with current_app.open_resource(report_path) as fp:
            msg.attach(
                f"scan_report_{scan.id}.pdf",
                "application/pdf",
                fp.read()
            )

        mail.send(msg)
        print(f"Successfully sent report for scan {scan.id} to {recipient}.")

    except Exception as e:
        print(f"Error sending email for scan {scan.id}: {e}")
