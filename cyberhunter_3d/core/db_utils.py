from cyberhunter_3d.web.models import db, Finding, Alert

def save_findings_to_db(findings, app):
    """
    Saves findings and their related alerts to the database.
    """
    with app.app_context():
        for finding_dict in findings:
            # Pop alerts so we don't try to save it in the Finding model
            alerts_to_create = finding_dict.pop('alerts', [])

            # Create the Finding object
            new_finding = Finding(**finding_dict)
            db.session.add(new_finding)
            db.session.flush() # Flush to get the ID for the new_finding

            # Create and associate Alert objects
            for alert in alerts_to_create:
                alert.finding_id = new_finding.id
                db.session.add(alert)

        db.session.commit()
