# # database.py
from zoneinfo import ZoneInfo
import pandas as pd
import os
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# ─── Initialize Supabase client ─────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─── Attendees ───────────────────────────────────────────────────────────────
def register_attendee(badge_id: int, name: str, email: str):
    """Insert a new attendee row into Supabase."""
    supabase.table("attendees") \
            .insert({"badge_id": badge_id, "name": name, "email": email}) \
            .execute()


def get_all_attendees():
    """Fetch all attendees from Supabase as a list of dicts."""
    resp = supabase.table("attendees") \
                   .select("*") \
                   .order("badge_id", desc=False) \
                   .execute()
    return resp.data


# ─── Scanning ────────────────────────────────────────────────────────────────
def log_scan(badge_id: int):
    """
    1) Insert raw scan event into scanlog
    2) Update next empty scanN column in attendees
    """
    badge = int(badge_id)
    local_tz = ZoneInfo("America/Chicago")
    now_iso  = datetime.datetime.now(local_tz).isoformat()

    # 1) raw log
    supabase.table("scanlog") \
            .insert({"badge_id": badge, "timestamp": now_iso}) \
            .execute()

    # 2) fetch the attendee row
    resp = supabase.table("attendees") \
                   .select("*") \
                   .eq("badge_id", badge) \
                   .execute()
    rows = resp.data
    if not rows:
        return

    row = rows[0]
    updates = {}
    for i in range(1, 11):
        col = f"scan{i}"
        if row.get(col) is None:
            updates[col] = now_iso
            break

    if updates:
        supabase.table("attendees") \
                .update(updates) \
                .eq("badge_id", badge) \
                .execute()


def get_scan_log():
    """
    Fetch every scan event, then look up each attendee’s name/email in Python.
    Returns a list of dicts: { badge_id, name, email, timestamp }.
    """
    # 1) grab raw scan events
    resp_scans = supabase.table("scanlog") \
                        .select("*") \
                        .order("timestamp", desc=True) \
                        .execute()
    scans = resp_scans.data  # list of { badge_id, timestamp, ... }

    # 2) grab attendees and build a quick lookup
    attendees = get_all_attendees()  # from database.py
    attendee_map = { a["badge_id"]: a for a in attendees }

    # 3) stitch them together
    logs = []
    for sc in scans:
        bid = sc["badge_id"]
        raw_ts = sc["timestamp"]
        # parse to datetime for your generate_ce_report logic
        ts = datetime.datetime.fromisoformat(raw_ts)
        a = attendee_map.get(bid, {})
        logs.append({
            "badge_id": bid,
            "name":      a.get("name", ""),
            "email":     a.get("email", ""),
            "timestamp": ts
        })
    return logs
def save_ce_report(df: pd.DataFrame, report_date: datetime.date):
    """
    Expect df like:
       Badge ID | Name | Email | [session1] | [session2] | ...
    This will melt it to one row per session and insert into ce_reports.
    """
    # melt wide→long
    id_vars = ["Badge ID", "Name", "Email"]
    value_vars = [c for c in df.columns if c not in id_vars]
    df_long = (
        df
        .melt(id_vars=id_vars, value_vars=value_vars,
              var_name="session_title", value_name="attended_mark")
        # convert "✅"→True, ""→False
        .assign(
            badge_id       = lambda d: d["Badge ID"].astype(int),
            attended       = lambda d: d["attended_mark"] == "✅",
            report_date    = report_date
        )
        .loc[:, ["badge_id","session_title","attended","report_date"]]
    )

    # insert into Supabase
    records = df_long.to_dict(orient="records")
    supabase.table("ce_reports").insert(records).execute()
