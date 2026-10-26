# Risenegar (رایزنگار) — Project Handoff

> Give this document to the new AI together with the project files listed in section 3.
> Last state: app version **v1.6 · 2026-10-26**. The English spelling of the app name is **Risenegar** (not Rayzangar).
> The user speaks **Persian** and is **not a backend developer**. Reply in Persian unless the user writes in English. Keep things simple and free-tier. Avoid over-engineering.

---

## 1. What the project is

A Persian (RTL) task-management and meeting-minutes web app for a small team (under 20 people), inspired by Iranian tools such as Taskulu, Mizito and Karsoo (design inspiration only, not a clone). Name: **Risenegar (رایزنگار)**, earlier called "برد کارها".

Core ideas:
- Kanban board + list view of tasks, with Persian (Jalali) dates and a Persian UI.
- A **meeting-minutes (صورتجلسه) module**: when a minute is finalized, its resolutions automatically become tasks on the board.
- Real multi-user backend (Supabase), invite links, member management.
- Must stay free/cheap, simple to run, expandable later.

Hosting and services:
| Part | Where |
|---|---|
| Frontend | Single static file `index.html` on **GitHub Pages**: `https://riseislamicstudies.github.io/risemanagement/` (public repo `risemanagement`) |
| Backend | **Supabase** (free plan). Project ref `efuihxmykttvwzsnlpod`, URL `https://efuihxmykttvwzsnlpod.supabase.co` |
| Backups | Separate **private** GitHub repo (`risemanagementbkp`) running a daily GitHub Action |
| Supabase keys | The *publishable* key (`sb_publishable_…`) is hard-coded in `index.html` (constants `SB_URL`, `SB_KEY`); this is normal and safe because Row Level Security protects data. The *secret* key (`sb_secret_…`) exists ONLY in the private backup repo's GitHub Secrets. **Never put it in the public repo or share it.** |

---

## 2. History: everything done so far (chronological)

1. **Planning.** Discussed building a Taskulu-like tool. Recommended Supabase (real Postgres, auth, RLS, realtime) because the user knows no backend. Compared self-hosting Plane vs Focalboard (Plane recommended; Focalboard is community-maintained). User decided to build their own simple app.
2. **Prototype as a Claude artifact** (hosted page with Claude's shared `db` capability). Built a minimal Persian kanban and iterated:
   - 3 columns (todo / doing / done), add task (title, assignee, priority), move with arrow buttons, delete.
   - Bugs found and fixed: `confirm()` is blocked in the sandbox (replaced by two-step buttons); snapshot data objects are frozen so assigning `id` silently failed (fixed by copying the object); toast messages hidden behind overlays (z-index).
   - Added: deadlines, edit panel with comments, projects (chips), search + assignee filter, sorting, checklists, CSV export/import (restore by file or by pasting text; auto-detects tab vs comma so Google-Sheets paste works), drag-and-drop (desktop only), Jalali date handling.
   - Limitations discovered: artifacts cannot call external servers (CSP), data only works when signed in to claude.ai, sharing is unavailable on the free plan → decided to move to Supabase + own hosting.
3. **Supabase setup.** User created the project (Data API on, "automatic RLS" on). Ran SQL files (section 3). Confirmed success.
4. **Real app (`index.html`)** built by reusing the prototype: a small adapter makes the old Firestore-like `db.doc().set()/delete()/collection().onSnapshot()` calls work on Supabase, so the rest of the UI code was unchanged. Supabase JS (v2.117.2) is **inlined** in the file. Hosted on GitHub Pages by the user.
5. **Auth + visual feedback:** email/password sign-in/sign-up with inline status messages, busy states, Persian error messages.
6. **Invite links** (no manual DB work): admin generates a link `…?join=<code>`; invitee signs up/in and joins automatically; code remembered across email confirmation; users with no team see "join with code / create team".
7. **Jalali date picker** (custom calendar popup; stored as ISO Gregorian, shown as Jalali). Conversion functions `g2j`, `j2g`, `iso2j`, `j2iso` (tested: 2026-10-20 = 1405/07/28; leap years correct).
8. **Meeting minutes module** (`meetings` table + `finalize_meeting()` RPC).
9. **Rename** to Risenegar; **version label** under the login form (bump on every delivery so the user can verify GitHub Pages deployed the latest file).
10. **v1.0 batch:** per-user name (profiles), assignee chosen from member names, whole task card clickable (cursor pointer), color labels and progress percent on tasks.
11. **v1.1 batch:** forgot/reset password, change password, member management (remove, change role, leave team), list of active invites with revoke.
12. **Automated backup + keep-alive:** private repo with `backup.py` + GitHub Action (daily 03:17 UTC). Fixed a bug (`order=1` is invalid in PostgREST → ordering by real columns). **User confirmed the backup works** and saves files.
13. **v1.2 redesign:** sidebar layout, list view, side drawer for task details, embedded Vazirmatn font, new visual style (see 4.8). Deployed and confirmed visually by the user (screenshots, desktop + phone).
14. **v1.3 batch (2026-10-24):** "My tasks" view, notifications (assigned + comment) with a bell and unread badge, comment author names (stamped server-side), manual day/night theme toggle (saved in localStorage, defaults to the system theme), logo is now a link to the home (board) view. New file `supabase-update-5.sql`. Tested in a real Chromium against an in-memory Supabase stand-in (behavior + screenshots, light/dark, desktop/mobile) and the SQL on a real PostgreSQL 16 with RLS roles; **not yet tested against the live Supabase project**.

15. **v1.4 batch (2026-10-24):** (a) tasks are linked to **accounts** (`tasks.assignee_id`) instead of name text; the name column stays for display and is kept in sync by the database (rename a user → all their tasks follow). (b) `restore.py` + Persian guide `RESTORE-fa.md`. (c) UI polish: emoji **reactions** on comments (stored inside the comment JSON as `rx: {emoji: [userIds]}`), entrance animations (first render / view switch only, never on realtime refresh), skeleton loading, drag highlights, completion flash, bell shake + badge pop, toast with **undo for deleted tasks**, offline banner, keyboard shortcuts (`/` search, `N` new task, `?` help; layout-independent via `event.code`), `prefers-reduced-motion` support. New file `supabase-update-6.sql`.
   Tested: Chromium + in-memory Supabase stand-in (behaviour, screenshots), SQL 1-6 on real PostgreSQL 16 with roles/RLS (regression + new scenarios), and a full backup.py -> restore.py round trip on real PostgreSQL through a small PostgREST stand-in. **Not tested against the live Supabase project, and restore.py has not been run against real PostgREST/GoTrue** (e.g. the admin "create user" endpoint) — try `--list` and a dry-run first.

16. **v1.5 batch (2026-10-26):** (a) **Rise Tracker logo** (supplied by the user; black wordmark + gold bar) is used everywhere a logo belongs: sidebar brand (still a link to the home view), login card, team-join sheet, favicon + apple-touch-icon + `theme-color`. Two transparent PNG variants (ink for light theme, cream for dark) are embedded as base64 and swapped by CSS per theme (`.logo.l` / `.logo.d`). The **colour palette** was derived from the logo (ink `#1F1F1D`, gold `#B39365`; warm paper backgrounds) as a final override block "v1.5" at the end of `<style>`, with light / dark-media / `[data-theme=dark]` layers and WCAG-checked contrast (buttons are ink on light, gold on dark). Note: the logo reads "Rise Tracker" while the UI/app name remains رایزنگار. (b) **Visual feedback for pending writes** (user request): every task write goes through `wr(id, kind, overlay, run, okFn)`; the card changes immediately (optimistic overlay applied by `applyPend()` on top of `base`, the last server snapshot), shows a spinner + "در حال ذخیره… منتظر پاسخ بمان", its action buttons are hidden and dragging is disabled until the DB answers, a global chip `#sv` shows the number of pending writes, then "✓ ذخیره شد" fades out; on failure the card returns to its old place, shakes and a toast says why. Adds show a dashed ghost card, deletes show a struck-through card, comments/checklist show a chip inside the drawer (`#dst`) and disable their submit buttons; a second write to the same task while one is pending is refused with a toast (prevents lost updates). `beforeunload` warns while writes are pending. `busy(btn, promise)` gives other buttons (meeting save/finalize/delete, restore) a spinner + disabled state. (c) **Touch drag** (`touchDrag()`): long-press ~0.3 s on a card, then drag; a ghost card follows the finger, the column under it is highlighted, edge auto-scroll works vertically and horizontally (scroll-snap is switched off while dragging), a short tap still opens the task, a swipe before 0.3 s still scrolls. Native HTML5 drag is enabled only for mouse/pen (`pointerdown` sets `draggable`). A one-time toast explains the gesture on touch devices. (d) **Meeting people are accounts:** chair/secretary are member selects (`chair_id`, `secretary_id`; the text columns keep the display name), attendees/absentees are member chips (`attendee_ids`, `absentee_ids`; a person cannot be both) plus a free-text box that now means "outside guests". Legacy text names that match exactly one member are linked automatically; unmatched names stay as text (select shows "name (نام متنی)"). If the new columns are missing (`probeM()`), the page falls back to writing names into the text columns. `restore.py` remaps these ids (and `who_id` in resolutions). (e) **In-app restore** (admin only, in the existing "بازیابی بکاپ" dialog): pick a `backup-*.json`, choose the team inside it, choose "only missing" (default) or "overwrite", see how many tasks/meetings are missing, confirm twice; the page calls RPC `restore_from_backup` in chunks of 150 (meetings first, then tasks). New file `supabase-update-7.sql`.

17. **v1.6 batch (2026-10-26):** (a) **Archive**: `tasks.archived` (update-8); done cards get «بایگانی», the done column gets «بایگانی همه» (two-step), a new «آرشیو» view lists archived tasks with restore/delete; archived tasks are excluded from board/list/My tasks/calendar (`applyPend()` splits `base` into `tasks` and `archT`; `T(id)` searches both). If the column is missing (`probeA()`), the archive UI hides itself and `archived` is never sent. (b) **Duplicate task** (drawer button, resets progress/comments/checks). (c) **Comment edit/delete** for the author's own comments (matched by `at`+`by`+`text`, flag `edited:true`; the stamp trigger only touches newly appended comments so authorship is kept). The restriction to own comments is UI-only (RLS lets any member update the task row). (d) **Team switcher** (`#wsw` in the sidebar; choice stored in localStorage `ws`; switching/creating/joining reloads the page; «＋ تیم جدید / پیوستن» opens the `#jn` sheet with a close button). (e) **Download backup now** (admin, in the restore dialog): JSON in the same shape as the nightly backup, so it can be fed back to the in-app restore. (f) **Jalali calendar view** (`renderCal`): month grid, chips per due date (priority colour, done struck through, late red), day panel, «بدون ددلاین» list, mouse drag of a chip to another day changes the due date (via `sv`), dots instead of titles on phones. (g) **PWA**: `manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` must sit **next to index.html** in the same folder; the service worker caches only the app shell (network-first for the page, never caches Supabase or any cross-origin request); install button `#pwa` appears when the browser offers installation (iOS: Share → Add to Home Screen). Data still needs the network; offline you get the shell and the offline banner.

---

## 3. Files (all must be handed over)

| File | Purpose |
|---|---|
| `site/index.html` (~370 KB) | The whole app: CSS, HTML, inlined supabase-js, app script. Deployed as `index.html` in the `risemanagement` repo |
| `supabase-setup.sql` | Base schema: `workspaces`, `members`, `tasks`; `is_member()`; trigger making the creator admin; RLS; grants; realtime on `tasks` |
| `supabase-invites.sql` | `is_admin()`, `invites` table + RLS, `join_workspace(code)`, `list_members(ws)` |
| `supabase-meetings.sql` | `meetings` table + RLS (draft-only edit/delete), `tasks.meeting_id`, `finalize_meeting(id)` |
| `supabase-update-3.sql` | `profiles` (names), `tasks.color`, `tasks.progress`, new `list_members` returning `name` |
| `supabase-update-4.sql` | `remove_member()`, `set_member_role()`, `heartbeat` table, `service_role` grants for the backup |
| `supabase-update-5.sql` | `notifications` table (RLS own rows, only `read` column updatable, realtime), trigger `stamp_comment_author` (BEFORE UPDATE on tasks: stamps `by`/`name` on newly appended comments from the real `auth.uid()` + profile), trigger `notify_task_change` (AFTER INSERT/UPDATE on tasks: notifies the new assignee and, on new comments, the assignee + task creator, never the actor). Safe to re-run. |
| `supabase-update-6.sql` | `tasks.assignee_id` (FK auth.users, on delete set null); trigger `sync_task_assignee` (BEFORE insert/update: a name-only change from an older page re-resolves the account by name, new ids must be workspace members, display name comes from the profile); trigger `propagate_profile_name` (renaming a profile updates `tasks.assignee`); `notify_task_change` rewritten to use `assignee_id` and to **skip when `auth.uid()` is null** (SQL editor / restore never notify); `finalize_meeting` honours `who_id` in resolutions; backfills old tasks by unique name match. Safe to re-run; old v1.3 pages keep working after it. **Run it, then deploy index.html v1.4 right away.** |
| `supabase-update-7.sql` | `meetings.chair_id / secretary_id / attendee_ids / absentee_ids` + backfill (unique name match; attendee/absentee text lines that match exactly one member move into the id arrays, the rest stay as text); `stamp_comment_author` and `notify_task_change` recreated to stay silent when `risenegar.restore='1'`; `_restore_row()` (internal, not callable by users) and `restore_from_backup(p_ws, p_meetings, p_tasks, p_overwrite)` (security definer, **admin of that workspace only**, ≤500 rows per array, rows are always written into `p_ws` whatever workspace_id they carry, never touches rows of other workspaces, nulls `assignee_id` of accounts that no longer exist, drops dangling `meeting_id`, creates no notifications, keeps comment authors). Safe to re-run. **Run it, then deploy index.html v1.5.** |
| `supabase-update-8.sql` | `tasks.archived boolean not null default false` + index. Safe to re-run; without it everything works except the archive UI is hidden. |
| `manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` | PWA files (v1.6), deployed beside `index.html`. Bump `CACHE` in `sw.js` when the shell file list changes. |
| `restore.py`, `RESTORE-fa.md` | Restore from `backups/backup-*.json`: dry-run by default, `--apply`, `--mode missing|overwrite`, `--tables`, `--workspace`, `--create-users` (new empty project: re-creates accounts by e-mail with temporary passwords in `restored-users.txt` and remaps every user id incl. comment authors/reactions), refuses to run without confirmation unless `--yes`. Stdlib only; reads `SUPABASE_URL` / `SUPABASE_SECRET_KEY` from the environment. |
| `backup-repo/backup.py` | Dumps all tables to `backups/backup-YYYY-MM-DD.json`, prunes after 60 days, updates `heartbeat` |
| `backup-repo/.github/workflows/backup.yml` | Daily cron + manual run; commits backups |

Run order of SQL files: setup → invites → meetings → update-3 → update-4 → update-5 → update-6 → update-7 → update-8. Since the backup (which reads all those tables and `heartbeat`) succeeded, the first five have been run (confirm update-5 too). **update-5, update-6 and update-7 must be run by the user in the Supabase SQL Editor; until update-5 the bell stays hidden, until update-7 meeting people fall back to text and the in-app JSON restore says to run update-7.**

**Legacy:** the first prototype artifact (`https://claude.ai/artifact/Wd8itP1dMr6pkBshpTHoE1`) is superseded; ignore it.

---

## 4. Current system in detail

### 4.1 Database (Supabase / Postgres, all with RLS)
- `workspaces(id, name, created_by, created_at)`
- `members(workspace_id, user_id, role['admin'|'member'])`
- `profiles(user_id, name, updated_at)` — own row only via RLS
- `tasks(id uuid, workspace_id, **assignee_id uuid (v1.4)**, title, project, assignee, priority['high'|'mid'|'low'], status['todo'|'doing'|'done'], due date, checks jsonb, comments jsonb, color text, progress int 0–100, meeting_id, created_by, created_at)`
  - `checks` = `[{t, d}]`; `comments` = `[{text, at(ms), by(user id), name}]` (`by`/`name` exist only on comments written since v1.3, stamped by the DB; `rx` = reactions, added v1.4; older comments have no author and render without a name)
  - `assignee_id` (v1.4) is the source of truth; `assignee` is the display name kept in sync by triggers (legacy tasks whose name matches no/several members have `assignee_id = null` and appear in the UI as "name (بدون حساب)")
- `meetings(id, workspace_id, title, project, held_on date, held_time text, location, chair, secretary, **chair_id, secretary_id, attendee_ids jsonb, absentee_ids jsonb (v1.5)**, attendees, absentees, agenda, discussion, next_meeting, resolutions jsonb [{text, who, who_id, due, pr}], status['draft'|'final'], created_by, created_at, finalized_at)`
- `invites(code, workspace_id, created_by, expires_at default +14 days)` — admins only
- `heartbeat(id=1, at)` — no policies; written only by the backup script with the secret key
- `notifications(id, workspace_id, user_id, kind['assigned'|'comment'], task_id, task_title, actor_name, body, read, created_at)` — created only by the `notify_task_change` trigger; users select/delete their own rows and can update only `read`. Not included in the daily backup (low value).
- Functions (security definer, `search_path=''`): `is_member`, `is_admin`, `join_workspace`, `list_members` (returns user_id, email, name, role), `finalize_meeting`, `remove_member`, `set_member_role`.
- Rules: tasks are visible/editable by workspace members. Meetings: members read; insert/update/delete only while `draft` (final = locked in the DB). `finalize_meeting` creates one task per resolution (todo, project/assignee/due/priority from the resolution, plus a comment referencing the minute), then locks the minute — atomic, cannot run twice. Last admin cannot be removed/demoted.

### 4.2 Auth
Email + password (supabase-js). Sign-up requires a full name (stored in user metadata and `profiles`; existing users are prompted once). Forgot password sends a reset link (`redirectTo` = the Pages URL); recovery flow shows a "new password" overlay. A logged-in user can change password and name from the "دعوت و اعضا" panel. The user decided SMTP is **not needed for now**: the team is small and the admin sends invite links by hand.

### 4.3 Frontend structure (`index.html`)
Single file: `<style>` (older rules first, then the v1.2 override block, embedded Vazirmatn subset as base64), HTML (sidebar + main + overlays), inlined supabase-js, then the app `<script>`. Key pieces in the script:
- `frow/trow` (row ↔ app object mapping), `db` adapter (`doc().set/delete`, `collection().orderBy().onSnapshot` → select + realtime channel + refetch), `reload()`.
- Auth: `enter()`, `ensureProfile()`, `begin(w)`, `auth()`, `showReset()`, workspace chooser (`#jn`).
- v1.4 block (before the bootstrap IIFE): `whoKey/dispName/idByName/keyByName/whoOf` (assignee as account; select option values are user ids or `n:<name>` for legacy), `probeId` (if `assignee_id` column is missing the page falls back to names and never sends it), `undoDel`, `skel`, `rxRow/react`, `ringBell`, offline banner, shortcuts. Global `MB` = member objects `{id,name,role,email}`.
- v1.3 block (just before the bootstrap IIFE): `isMine/mrow/renderMine` (My tasks), theme (`curTheme/drawTg`, class `swap` briefly disables transitions), logo handler, notifications (`loadNotifs/drawNotifs/openNotif/markRead/startNotifs`, realtime channel `n-<userId>`; the bell hides itself if the table is missing).
- v1.5 code: `wr/sv/applyPend/pUI/dStatus/busy` (pending writes; globals `pend`, `base`, `savedId`, `shakeId`), `touchDrag`, meeting people (`fillMem/fldM/fldP/pkDraw/pkTog/pick/probeM`, globals `PK`, `HAS_M`), in-app restore (`bk*` functions, element ids `#bf #bw #bmo #bm #bg #bx #bn`). Tasks are shown from `tasks = base + pending overlay`; always write via `sv(t, fields)` / `wr(...)`, never directly mutate `tasks`.
- Board: `render()`, `chips()` (builds sidebar project list + assignee filter + datalist), `renderList()`, `vis()`, `cmp()` (sort), `openT()` (task drawer), `move()`, `body()` (copy task fields for writes).
- Meetings: `openM/saveM/loadMeetings`, finalize via `sb.rpc("finalize_meeting")`, resolution rows `rrow/getRes`.
- Members: `drawMembers()`, `drawInvites()`, `mrpc()`, `two()` (two-step confirm helper — `confirm()` is avoided).
- Dates: `g2j/j2g/iso2j/j2iso/today`, calendar `openDP/drawDP`.
- CSV export/import: `#ex` handler, `parseCSV`, `doImport` (skips tasks with same title+project; columns: title, project, assignee, priority label, status label, Jalali due, comments, checklist `+/-text`, color, progress).
- Assignee dropdowns: `fillWho(select, current)` fed by `mem` (member names).

### 4.4 Features currently available
Board (3 columns, arrows + desktop drag-drop), list view, **"My tasks"** (tasks assigned to my account (`assignee_id = me`; legacy name-only tasks fall back to a name match), grouped: overdue / today / next 7 days / later-or-no-deadline / done (last 10), with quick start/finish buttons and an open-count badge in the sidebar), **notification bell + panel** (unread badge, mark one/all read, click opens the task, plus a client-side "deadline reminder" list of my tasks overdue or due within 2 days; the reminders do not count in the badge), **comment author names**, **day/night toggle** in the top bar, **logo link** (returns to the board and clears project/search/assignee filters), side drawer for tasks (edit title/assignee/project/priority/Jalali deadline/color/progress %, checklist with "compute progress from checklist", comments), color labels, progress bars, projects in sidebar with counts, search + assignee filter + sort (creation / nearest deadline / priority), CSV export/import, meeting minutes (all fields above, draft → finalize → tasks), members panel (names/emails/roles), invite links (create, copy, list, revoke), remove member / change role / leave team, name editing, password reset/change, realtime updates, mobile off-canvas sidebar, Esc closes overlays, dark mode follows the system.

### 4.5 Backup + keep-alive
Private repo `risemanagementbkp`: `backup.py` + `.github/workflows/backup.yml`; GitHub Secrets `SUPABASE_URL`, `SUPABASE_SECRET_KEY`. Runs daily; writes JSON dumps (tables + user emails list), keeps 60 days, patches `heartbeat` so the free Supabase project isn't paused for inactivity (free projects pause after ~1 week of low activity; no fake user needed because the script uses the secret key). Google Drive backup was discussed but **not** implemented (service accounts have no quota on personal Drive; private repo chosen instead).

### 4.6 Design notes
Sidebar (brand, nav: برد / فهرست کارها / صورتجلسه‌ها, projects, user area, invite/logout, version), top bar with page title and hamburger on mobile, card-style add-task bar, status-colored column dots, avatar initials with per-name color, priority pills, drawer on the left for task details, gradient login card, Vazirmatn font embedded (OFL).

---

## 5. Open items / not yet done

**Needs the user (not code):**
- Run `supabase-update-5.sql` in the Supabase SQL Editor, deploy `index.html` v1.3, then test with two real accounts: assign a task to the other person, comment, check the bell on both sides (realtime), check that the comment shows the author name.
- (Postponed by the user) Custom SMTP for auth emails (user wants to use `info@riseislamicstudies.com`, hosted on another server; needs SMTP host/port/user/password from that site's admin → Supabase Authentication → Emails → SMTP). Then test a reset email to Gmail and check spam. Supabase's default email has tight limits.
- Supabase Authentication → URL Configuration: Site URL and Redirect URLs must include `https://riseislamicstudies.github.io/risemanagement/` and `…/**` for password-reset links to work. (User was told; not confirmed.)
- Deploy `index.html` v1.2 to GitHub and verify the version label.
- Test with two real accounts: invite flow, names, minutes finalize → tasks appear, colors/progress, member removal. **Most features were only tested in a jsdom simulation, not against live Supabase, and the v1.2 visuals have not been seen in a real browser.** The user was asked to send screenshots (desktop + phone) for visual tuning.

**Known gaps / ideas (rough priority):**
1. (Done in v1.6: calendar view.) Activity history, deadline notifications that are stored (today deadlines are only shown as a client-side reminder list; real ones need a scheduled job such as `pg_cron`, plus e-mail needs SMTP), notification preferences.
2. (Done in v1.6: archive, workspace switcher.) Remaining: delete/rename a team, per-team invite from the switcher.
3. File attachments (Supabase Storage; planned for v1.7), minutes PDF/print export, choose attendees from members, admin-only (or role-based) finalize (currently **any member can finalize**), admin "reopen" of a finalized minute, search in minutes, include minutes in the CSV/restore.
4. (Done in v1.4: `restore.py`.) Still to do: rehearse a restore into a scratch Supabase project once; add `notifications` to the backup only if ever needed.
5. (Done in v1.5: touch drag.) Still to do: (Done in v1.6: PWA install.) Reaction/comment rows are not yet individually optimistic (the whole drawer is locked while a write is pending).
6. (Done in v1.4/v1.5: assignee, chair, secretary, attendees are accounts.) Remaining: CSV export/import still uses names; a removed member's tasks keep their `assignee_id` (shown by name); a removed member appears in old minutes as the chip "عضو سابق" (names of removed attendees are not snapshotted).
7. Longer term: split the single 370 KB file into a proper project (e.g. Vite), staging Supabase project, migrations, viewer role, captcha/rate limits if ever public.

---

## 6. Technical lessons / gotchas
- Claude artifacts (published pages) cannot make network calls to other hosts → the real app must be hosted elsewhere (GitHub Pages).
- GitHub Pages (free) requires a **public** repo → never commit backups or secret keys there; backups live in a private repo.
- Supabase new key format: `sb_publishable_…` (client) and `sb_secret_…` (server only). Send secret keys only in the `apikey` header. New projects require explicit `GRANT`s for Data API access (the SQL files include them; `service_role` grants are in update-4).
- PostgREST: `order=1` is invalid; always order by real columns. Paged reads use `Range` headers (1000 rows per page).
- Row data from realtime/queries should be copied before adding properties (frozen objects in the prototype).
- `confirm()`/`alert()` are unreliable in embedded contexts → use two-step buttons.
- Toasts need a z-index above all overlays.
- **Always replace a whole comment marker, e.g. `/* ===== x ===== */`, together with its closing `*/`.** In v1.5 a patch accidentally left `/* … ` open; `node --check` still passed because the comment silently swallowed the next block of code. After patching, also compare the counts of `/*` and `*/` in the extracted script and grep for a known function name from the swallowed region.
- When editing `index.html` programmatically, use unique anchor strings; Persian strings often contain ZWNJ (U+200C), which breaks naive matching. Always syntax-check the extracted script (`node --check`) and smoke-test with jsdom before delivering. In jsdom, `form.someName` named access fails for `<select>`; the code uses `form.elements.name` for robustness.
- User workflow preferences: deliver every new build as a **file** (the user could not reach the artifact button on mobile), show a **version number** each time (next is v1.7), explain steps simply in Persian, and clearly say what was *not* tested.

---

## 7. How to continue
1. Make sure you have all files from section 3 (especially `site/index.html`, the latest).
2. Ask the user: (a) did v1.5 deploy, were `supabase-update-5/6/7.sql` run, and did the two-account test work (assign, comment, bell, touch drag on a real phone)? (b) was Supabase Authentication → URL Configuration (Site URL / Redirect URLs) confirmed for password reset? (c) what is the next priority — suggested: ask whether the v1.5 restore button worked on the live project, then calendar view / archive for done tasks / PWA install.
3. For any new DB change, deliver a new numbered SQL file (`supabase-update-9.sql`, …) and tell the user exactly when to run it; bump the version label in `index.html`.
