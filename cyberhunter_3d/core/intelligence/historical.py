from sqlalchemy import func
from cyberhunter_3d.web.models import db, Scan, Asset
from typing import List, Dict, Any

def get_subdomain_growth(user_id: int) -> List[Dict[str, Any]]:
    """
    Returns the total number of subdomains discovered over time for a user.
    """
    results = db.session.query(
        func.date(Scan.created_at).label('date'),
        func.count(Asset.id).label('subdomain_count')
    ).join(Asset).filter(
        Scan.user_id == user_id,
        Asset.type == 'subdomain'
    ).group_by(
        func.date(Scan.created_at)
    ).order_by(
        func.date(Scan.created_at)
    ).all()

    return [{"date": str(r.date), "count": r.subdomain_count} for r in results]

def get_live_host_growth(user_id: int) -> List[Dict[str, Any]]:
    """
    Returns the total number of live hosts discovered over time for a user.
    """
    results = db.session.query(
        func.date(Scan.created_at).label('date'),
        func.count(Asset.id).label('host_count')
    ).join(Asset).filter(
        Scan.user_id == user_id,
        Asset.type == 'live_host'
    ).group_by(
        func.date(Scan.created_at)
    ).order_by(
        func.date(Scan.created_at)
    ).all()

    return [{"date": str(r.date), "count": r.host_count} for r in results]

def get_new_technologies_growth(user_id: int) -> List[Dict[str, Any]]:
    """
    Returns the number of newly discovered technologies over time for a user.
    """
    results = db.session.query(
        func.date(Scan.created_at).label('date'),
        func.count(Asset.id).label('tech_count')
    ).join(Asset).filter(
        Scan.user_id == user_id,
        Asset.type == 'technology'
    ).group_by(
        func.date(Scan.created_at)
    ).order_by(
        func.date(Scan.created_at)
    ).all()

    return [{"date": str(r.date), "count": r.tech_count} for r in results]
