import sqlite3
from google.cloud import firestore
from datetime import datetime

db = firestore.Client()

def migrate(sqlite_path="db/hui.db"):
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    # Adjust these queries to match your real schema.
    try:
        cur.execute("SELECT id, name, telegram_id, phone, notes, created_at FROM members")
        for rid, name, tg_id, phone, notes, created_at in cur.fetchall():
            doc = {
                "name": name,
                "telegram_id": str(tg_id) if tg_id is not None else None,
                "phone": phone,
                "notes": notes,
                "created_at": datetime.fromisoformat(created_at) if created_at else firestore.SERVER_TIMESTAMP,
            }
            db.collection("members").document(str(rid)).set(doc)
    except Exception:
        pass

    try:
        cur.execute("""SELECT id, title, type, start_date, slots, face_value, floor_pct, cap_pct, bid_pct, status, created_at
                       FROM pools""")
        for (pid, title, typ, start_date, slots, face_value, floor_pct, cap_pct, bid_pct, status, created_at) in cur.fetchall():
            doc = {
                "title": title,
                "type": typ,
                "start_date": datetime.fromisoformat(start_date) if start_date else None,
                "slots": slots,
                "face_value": face_value,
                "floor_pct": float(floor_pct) if floor_pct is not None else None,
                "cap_pct": float(cap_pct) if cap_pct is not None else None,
                "bid_pct": float(bid_pct) if bid_pct is not None else None,
                "status": status or "open",
                "created_at": datetime.fromisoformat(created_at) if created_at else firestore.SERVER_TIMESTAMP,
            }
            db.collection("pools").document(str(pid)).set(doc)
    except Exception:
        pass

    try:
        cur.execute("""SELECT id, pool_id, round_order, date, winner_member_id, bid_pct, amount_due, paid
                       FROM rounds""")
        for (rid, pool_id, order, date, winner_member_id, bid_pct, amount_due, paid) in cur.fetchall():
            doc = {
                "order": order,
                "date": datetime.fromisoformat(date) if date else None,
                "winner_member_id": str(winner_member_id) if winner_member_id else None,
                "bid_pct": float(bid_pct) if bid_pct is not None else None,
                "amount_due": amount_due,
                "paid": bool(paid),
            }
            db.collection("pools").document(str(pool_id)) \                  .collection("rounds").document(str(rid)).set(doc)
    except Exception:
        pass

    try:
        cur.execute("""SELECT id, pool_id, round_order, member_id, amount, paid_at, method
                       FROM payments""")
        for (pid, pool_id, round_order, member_id, amount, paid_at, method) in cur.fetchall():
            doc = {
                "pool_id": str(pool_id),
                "round_order": round_order,
                "member_id": str(member_id),
                "amount": amount,
                "paid_at": datetime.fromisoformat(paid_at) if paid_at else None,
                "method": method,
            }
            db.collection("payments").document(str(pid)).set(doc)
    except Exception:
        pass

    conn.close()
    print("Migration done.")

if __name__ == "__main__":
    migrate()
