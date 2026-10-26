"""بازیابی رایزنگار از فایل بکاپ JSON (همان فایل‌هایی که backup.py هر شب می‌سازد).

پیش‌فرض فقط «نشان می‌دهد چه می‌شود» و چیزی را تغییر نمی‌دهد (dry-run).
برای اجرای واقعی باید --apply بزنی.

نمونه‌ها (راهنمای کامل فارسی: RESTORE-fa.md):
  python3 restore.py backups/backup-2026-10-24.json --list
  python3 restore.py backups/backup-2026-10-24.json                      # فقط گزارش
  python3 restore.py backups/backup-2026-10-24.json --apply              # کارهای پاک‌شده را برمی‌گرداند
  python3 restore.py backups/backup-2026-10-24.json --apply --mode overwrite
  python3 restore.py backups/backup-2026-10-24.json --apply --create-users   # پروژه‌ی جدید و خالی

آدرس و کلید از متغیرهای محیطی خوانده می‌شود (کلید را روی خط فرمان ننویس):
  SUPABASE_URL=https://xxxx.supabase.co   SUPABASE_SECRET_KEY=sb_secret_...

فقط کتابخانه‌ی استاندارد پایتون لازم است.
"""
import argparse
import datetime
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

# ترتیب مهم است: اول چیزهایی که بقیه به آن‌ها وابسته‌اند
ORDER = ["workspaces", "members", "profiles", "invites", "meetings", "tasks"]
KEYS = {
    "workspaces": ["id"],
    "members": ["workspace_id", "user_id"],
    "profiles": ["user_id"],
    "invites": ["code"],
    "meetings": ["id"],
    "tasks": ["id"],
}
PAGE = 1000
CHUNK = 200


class Fail(Exception):
    pass


# ---------------------------------------------------------------- HTTP
class Api:
    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key

    def call(self, path, method="GET", body=None, extra=None):
        headers = {"apikey": self.key}
        headers.update(extra or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            text = e.read().decode(errors="replace")[:600]
            raise Fail("HTTP %s on %s %s -> %s" % (e.code, method, path.split("?")[0], text))
        except urllib.error.URLError as e:
            raise Fail("cannot reach %s (%s)" % (self.url, e.reason))

    def fetch_all(self, table, cols="*", order=None):
        rows, start = [], 0
        while True:
            q = "/rest/v1/%s?select=%s" % (table, cols)
            if order:
                q += "&order=" + order
            page = self.call(q, extra={"Range-Unit": "items", "Range": "%d-%d" % (start, start + PAGE - 1)})
            rows += page
            if len(page) < PAGE:
                return rows
            start += PAGE

    def users(self):
        out, page = [], 1
        while True:
            r = self.call("/auth/v1/admin/users?page=%d&per_page=200" % page)
            batch = (r or {}).get("users", [])
            out += [{"id": u["id"], "email": u.get("email")} for u in batch]
            if len(batch) < 200:
                return out
            page += 1

    def create_user(self, email, password, name):
        r = self.call(
            "/auth/v1/admin/users",
            method="POST",
            body={"email": email, "password": password, "email_confirm": True, "user_metadata": {"name": name or ""}},
        )
        return r["id"]

    def upsert(self, table, rows, on_conflict, overwrite):
        prefer = "resolution=%s,return=minimal" % ("merge-duplicates" if overwrite else "ignore-duplicates")
        self.call(
            "/rest/v1/%s?on_conflict=%s" % (table, urllib.parse.quote(",".join(on_conflict))),
            method="POST",
            body=rows,
            extra={"Prefer": prefer},
        )


# ---------------------------------------------------------------- helpers
def remap_meeting(r, umap, names):
    """رئیس/دبیر/حاضرین/غایبین و who_id مصوبه‌ها (شناسه‌ی حساب) را به شناسه‌های مقصد تبدیل می‌کند.
    حسابی که در مقصد نیست: از شناسه‌ها کنار می‌رود (رئیس/دبیر نامشان در ستون متنی هست؛ حاضرین/غایبین به متن اضافه می‌شوند)."""
    for k in ("chair_id", "secretary_id"):
        if r.get(k):
            r[k] = umap.get(r[k])
    for ids_col, txt_col in (("attendee_ids", "attendees"), ("absentee_ids", "absentees")):
        ids = r.get(ids_col)
        if isinstance(ids, list):
            keep, lost = [], []
            for u in ids:
                if u in umap:
                    keep.append(umap[u])
                elif names.get(u):
                    lost.append(names[u])
            r[ids_col] = keep
            if lost:
                r[txt_col] = "\n".join(lost + ([r[txt_col]] if r.get(txt_col) else []))
    res = r.get("resolutions")
    if isinstance(res, list):
        out = []
        for x in res:
            if isinstance(x, dict) and x.get("who_id"):
                x = dict(x)
                nid = umap.get(x["who_id"])
                if nid:
                    x["who_id"] = nid
                else:
                    x.pop("who_id")
            out.append(x)
        r["resolutions"] = out


def key_of(table, row):
    return tuple(str(row.get(k)) for k in KEYS[table])


def remap_comments(comments, umap):
    """شناسه‌ی نویسنده و واکنش‌های داخل کامنت‌ها را به شناسه‌های جدید تبدیل می‌کند."""
    if not isinstance(comments, list):
        return comments
    out = []
    for c in comments:
        if not isinstance(c, dict):
            out.append(c)
            continue
        c = dict(c)
        if c.get("by") in umap:
            c["by"] = umap[c["by"]]
        if isinstance(c.get("rx"), dict):
            c["rx"] = {e: [umap.get(u, u) for u in (ids or [])] for e, ids in c["rx"].items()}
        out.append(c)
    return out


def load_backup(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise Fail("cannot read backup file: %s" % e)
    if not isinstance(data, dict) or not isinstance(data.get("tables"), dict):
        raise Fail("this does not look like a Risenegar backup (no 'tables' section)")
    return data


def show_list(b):
    print("Backup created at:", b.get("created_at"))
    for t in ORDER + ["heartbeat"]:
        if t in b["tables"]:
            print("  %-11s %d rows" % (t, len(b["tables"][t])))
    print("  %-11s %d accounts" % ("users", len(b.get("users", []))))
    for t in b["tables"].get("workspaces", []):
        n_t = sum(1 for x in b["tables"].get("tasks", []) if x.get("workspace_id") == t["id"])
        n_m = sum(1 for x in b["tables"].get("meetings", []) if x.get("workspace_id") == t["id"])
        print("  workspace %r: %d tasks, %d minutes" % (t.get("name"), n_t, n_m))


# ---------------------------------------------------------------- planning
def build_user_map(api, backup, create, apply_, notes, temp_pw):
    """شناسه‌ی کاربرهای بکاپ → شناسه‌ی همان آدم‌ها در پروژه‌ی مقصد (اول با شناسه، بعد با ایمیل)."""
    target = api.users()
    by_id = {u["id"]: u for u in target}
    by_email = {(u["email"] or "").lower(): u["id"] for u in target if u.get("email")}
    names = {p["user_id"]: p.get("name", "") for p in backup["tables"].get("profiles", [])}
    umap, missing = {}, []
    for u in backup.get("users", []):
        uid, em = u["id"], (u.get("email") or "").lower()
        if uid in by_id:
            umap[uid] = uid
        elif em and em in by_email:
            umap[uid] = by_email[em]
        else:
            missing.append(u)
    created = 0
    for u in missing:
        em = u.get("email")
        if create and em:
            if apply_:
                pw = secrets.token_urlsafe(9)
                umap[u["id"]] = api.create_user(em, pw, names.get(u["id"], ""))
                temp_pw.append((em, pw))
            else:
                umap[u["id"]] = "NEW-" + u["id"]  # فقط برای گزارش dry-run
            created += 1
    still = [u for u in missing if u["id"] not in umap]
    if created:
        notes.append("accounts %s: %d" % ("created" if apply_ else "that would be created", created))
    if still:
        notes.append("accounts not found in target and not created (rows depending on them are skipped): %d  -> add --create-users" % len(still))
    return umap


def plan(api, backup, umap, tables, only_ws, skipped):
    """برای هر جدول: چه ردیف‌هایی جدید، یکسان، یا متفاوت‌اند."""
    bt = backup["tables"]
    plans, ws_ok = {}, set()
    now = datetime.datetime.now(datetime.timezone.utc)
    existing_ws = {w["id"] for w in api.fetch_all("workspaces", "id", "id")}
    ws_ok |= existing_ws
    names = {p["user_id"]: p.get("name", "") for p in bt.get("profiles", [])}
    admins = {}
    for m in bt.get("members", []):
        if m.get("role") == "admin":
            admins.setdefault(m["workspace_id"], []).append(m["user_id"])

    for t in ORDER:
        if t not in tables or t not in bt:
            continue
        rows = []
        for r in bt[t]:
            r = dict(r)
            ws = r.get("id") if t == "workspaces" else r.get("workspace_id")
            if only_ws and t != "profiles" and ws != only_ws:
                continue
            if t == "profiles" and only_ws:
                if not any(m["user_id"] == r["user_id"] and m["workspace_id"] == only_ws for m in bt.get("members", [])):
                    continue
            # --- user ids
            if t in ("members", "profiles"):
                if r["user_id"] not in umap:
                    skipped[t + ": account missing"] = skipped.get(t + ": account missing", 0) + 1
                    continue
                r["user_id"] = umap[r["user_id"]]
            if t == "workspaces":
                cb = umap.get(r.get("created_by"))
                if cb is None:
                    cb = next((umap[a] for a in admins.get(r["id"], []) if a in umap), None)
                if cb is None:
                    skipped["workspaces: no owner account"] = skipped.get("workspaces: no owner account", 0) + 1
                    continue
                r["created_by"] = cb
            if t == "invites":
                r["created_by"] = umap.get(r.get("created_by"))
                exp = r.get("expires_at")
                try:
                    if exp and datetime.datetime.fromisoformat(exp.replace("Z", "+00:00")) < now:
                        skipped["invites: expired"] = skipped.get("invites: expired", 0) + 1
                        continue
                except ValueError:
                    pass
            if t in ("meetings", "tasks") and r.get("created_by") in umap:
                r["created_by"] = umap[r["created_by"]]
            if t == "meetings":
                remap_meeting(r, umap, names)
            if t == "tasks":
                if r.get("assignee_id"):
                    r["assignee_id"] = umap.get(r["assignee_id"])  # نبود حساب → خالی (نام می‌ماند)
                r["comments"] = remap_comments(r.get("comments"), umap)
            # --- needs its workspace
            if t != "workspaces" and t != "profiles" and r.get("workspace_id") not in ws_ok and r.get("workspace_id") not in {
                x["id"] for x in plans.get("workspaces", {}).get("rows", [])
            }:
                skipped[t + ": workspace missing"] = skipped.get(t + ": workspace missing", 0) + 1
                continue
            rows.append(r)

        cols = sorted({c for r in rows for c in r})
        have = {}
        if rows:
            for e in api.fetch_all(t, "*", ",".join(KEYS[t])):
                have[key_of(t, e)] = e
        new, same, diff = [], 0, []
        for r in rows:
            e = have.get(key_of(t, r))
            if e is None:
                new.append(r)
            elif all(e.get(c) == r.get(c) for c in cols if c in e):
                same += 1
            else:
                diff.append(r)
        plans[t] = {"rows": rows, "new": new, "same": same, "diff": diff}
        if t == "workspaces":
            ws_ok |= {r["id"] for r in rows}
    return plans


def write_batches(api, t, rows, overwrite):
    for i in range(0, len(rows), CHUNK):
        chunk = rows[i:i + CHUNK]
        # همه‌ی ردیف‌های یک درخواست باید ستون‌های یکسان داشته باشند
        cols = sorted({c for r in chunk for c in r})
        chunk = [{c: r.get(c) for c in cols} for r in chunk]
        try:
            api.upsert(t, chunk, KEYS[t], overwrite)
        except Fail as e:
            msg = str(e)
            if "assignee_id" in msg and ("column" in msg or "PGRST204" in msg):
                raise Fail(msg + "\n  -> the target database has not run supabase-update-6.sql yet. Run it first, then retry.")
            if "archived" in msg and ("column" in msg or "PGRST204" in msg):
                raise Fail(msg + "\n  -> the target database has not run supabase-update-8.sql yet. Run it first, then retry.")
            if any(c in msg for c in ("chair_id", "secretary_id", "attendee_ids", "absentee_ids")) and ("column" in msg or "PGRST204" in msg):
                raise Fail(msg + "\n  -> the target database has not run supabase-update-7.sql yet. Run it first, then retry.")
            if "notifications" in msg and "does not exist" in msg:
                raise Fail(msg + "\n  -> run supabase-update-5.sql / update-6.sql on the target first.")
            raise


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Restore a Risenegar JSON backup into Supabase (dry-run by default).")
    ap.add_argument("backup", help="path to backups/backup-YYYY-MM-DD.json")
    ap.add_argument("--list", action="store_true", help="only show what is inside the backup")
    ap.add_argument("--apply", action="store_true", help="really write to the database (default: report only)")
    ap.add_argument("--mode", choices=["missing", "overwrite"], default="missing",
                    help="missing = only add rows that are gone (default, safe); overwrite = also reset rows that changed since the backup")
    ap.add_argument("--tables", default=",".join(ORDER), help="comma list, default: " + ",".join(ORDER))
    ap.add_argument("--workspace", help="restore only this workspace id")
    ap.add_argument("--create-users", action="store_true",
                    help="create accounts that exist in the backup but not in the target (for a NEW empty project). Temporary passwords are saved to restored-users.txt")
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    a = ap.parse_args()

    try:
        backup = load_backup(a.backup)
        if a.list:
            show_list(backup)
            return 0
        url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
        if not url or not key:
            raise Fail("set SUPABASE_URL and SUPABASE_SECRET_KEY environment variables first")
        tables = [t.strip() for t in a.tables.split(",") if t.strip()]
        bad = [t for t in tables if t not in ORDER]
        if bad:
            raise Fail("unknown table(s): %s (allowed: %s)" % (", ".join(bad), ", ".join(ORDER)))
        api = Api(url, key)
        print("Target :", url)
        print("Backup :", a.backup, "(created %s)" % backup.get("created_at"))
        print("Mode   : %s, %s\n" % (a.mode, "APPLY" if a.apply else "dry-run (nothing will be changed)"))

        notes, skipped, temp_pw = [], {}, []
        if a.apply and not a.yes:
            if not sys.stdin.isatty():
                raise Fail("not an interactive terminal: add --yes to confirm")
            if input("Type RESTORE to continue: ").strip() != "RESTORE":
                print("Cancelled.")
                return 1
        umap = build_user_map(api, backup, a.create_users, a.apply, notes, temp_pw)
        plans = plan(api, backup, umap, tables, a.workspace, skipped)

        print("%-11s %8s %8s %8s %8s" % ("table", "in-backup", "new", "same", "changed"))
        for t in ORDER:
            if t in plans:
                p = plans[t]
                print("%-11s %8d %8d %8d %8d" % (t, len(p["rows"]), len(p["new"]), p["same"], len(p["diff"])))
        for n in notes:
            print("\n*", n)
        if skipped:
            print("\nSkipped rows:")
            for k, v in sorted(skipped.items()):
                print("  %-34s %d" % (k, v))

        if not a.apply:
            would = sum(len(p["new"]) + (len(p["diff"]) if a.mode == "overwrite" else 0) for p in plans.values())
            print("\nDry-run finished: %d rows would be written. Add --apply to do it." % would)
            if a.mode == "missing" and any(p["diff"] for p in plans.values()):
                print("(Some rows differ from the backup because they were edited later; --mode overwrite would reset them.)")
            return 0

        written = {}
        for t in ORDER:
            if t not in plans:
                continue
            p = plans[t]
            rows = p["new"] + (p["diff"] if a.mode == "overwrite" else [])
            if rows:
                write_batches(api, t, rows, a.mode == "overwrite")
            written[t] = len(rows)
        print("\nDone. Rows written:", ", ".join("%s=%d" % kv for kv in written.items()))
        if temp_pw:
            with open("restored-users.txt", "w", encoding="utf-8") as f:
                f.write("Temporary passwords for re-created accounts. Hand each one to its owner, then delete this file.\n"
                        "They can change it inside the app (Invite & members -> change password).\n\n")
                for em, pw in temp_pw:
                    f.write("%s\t%s\n" % (em, pw))
            try:
                os.chmod("restored-users.txt", 0o600)
            except OSError:
                pass
            print("Temporary passwords for %d accounts saved in restored-users.txt (keep it private, delete it after use)." % len(temp_pw))
        print("Note: notifications are not part of the backup and are not recreated.")
        return 0
    except Fail as e:
        print("\nERROR:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
