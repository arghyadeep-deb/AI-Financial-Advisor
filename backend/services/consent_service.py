from backend.models.models import ConsentRecord, User

def allowed(db, owner, purpose):
    user = db.get(User, owner)
    if not user or not user.is_active:
        return False
    row = db.query(ConsentRecord).filter_by(user_id=owner, purpose=purpose).order_by(ConsentRecord.id.desc()).first()
    return bool(row and row.granted)
