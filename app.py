from flask import Flask, render_template, request, redirect
from datetime import date
import csv, json, os
from collections import defaultdict

app = Flask(__name__)

# ======================================================
# CONFIG
# ======================================================

EXAM_DATE = date(2026, 3, 31)

PHASE1_SUBJECTS = {
    "quant": {
        "name": "Quantitative Aptitude",
        "csv": "data/phase1_quant.csv",
        "progress": "data/quant_progress.json"
    },
    "reasoning": {
        "name": "Reasoning",
        "csv": "data/phase1_reasoning.csv",
        "progress": "data/reasoning_progress.json"
    },
    "english": {
        "name": "English",
        "csv": "data/phase1_english.csv",
        "progress": "data/english_progress.json"
    },
    "ga": {
        "name": "General Awareness",
        "csv": "data/phase1_ga.csv",
        "progress": "data/ga_progress.json"
    }
}

# ======================================================
# CSV / JSON HELPERS
# ======================================================

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_progress(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_progress(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def parse_date(d):
    if not d:
        return None

    d = d.strip()

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return date.strptime(d, fmt)
        except ValueError:
            continue

    return None


# ======================================================
# SUBJECT ANALYSIS
# ======================================================

def subject_analysis(key):
    cfg = PHASE1_SUBJECTS[key]
    rows = load_csv(cfg["csv"])
    progress = load_progress(cfg["progress"])

    total = len(rows)
    completed = 0
    overdue = 0
    today = date.today()

    for r in rows:
        k = f"{r['chapter_name']}||{r['topic_name']}"
        done = progress.get(k, {}).get("completed")
        target = parse_date(r.get("target_date"))
        
        
        if done:
            completed += 1
        else:
            if target and target < today:
                overdue += 1

    pending = total - completed

    integrity_pct = int((completed / total) * 100) if total else 0

    if pending == 0:
        credibility_pct = 100
    else:
        credibility_pct = int(((pending - overdue) / pending) * 100)

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "integrity": integrity_pct,
        "credibility": credibility_pct
    }
def today_lectures():
    today = date.today()
    out = []

    for key, cfg in PHASE1_SUBJECTS.items():
        rows = load_csv(cfg["csv"])
        progress = load_progress(cfg["progress"])

        for r in rows:
            k = f"{r['chapter_name']}||{r['topic_name']}"
            done = progress.get(k, {}).get("completed")
            target = parse_date(r.get("target_date"))

            if not done and target == today:
                out.append({
                    "subject_key": key,
                    "subject": cfg["name"],
                    "chapter": r["chapter_name"],
                    "topic": r["topic_name"]
                })

    return out
@app.route("/today", methods=["GET", "POST"])
def today_plan():
    if request.method == "POST":
        subject = request.form["subject"]
        chapter = request.form["chapter"]
        topic = request.form["topic"]

        cfg = PHASE1_SUBJECTS[subject]
        progress = load_progress(cfg["progress"])
        key = f"{chapter}||{topic}"

        progress[key] = {
            "completed": True,
            "completed_date": date.today().isoformat()
        }

        save_progress(cfg["progress"], progress)
        return redirect("/today")

    lectures = today_lectures()

    return render_template(
        "today.html",
        lectures=lectures
    )

# ======================================================
# PHASE-1 AGGREGATE (DASHBOARD)
# ======================================================

def phase1_summary():
    total = completed = pending = overdue = 0

    for key in PHASE1_SUBJECTS:
        s = subject_analysis(key)
        total += s["total"]
        completed += s["completed"]
        pending += s["pending"]
        overdue += s["overdue"]

    integrity_pct = int((completed / total) * 100) if total else 0

    if pending == 0:
        credibility_pct = 100
    else:
        credibility_pct = int(((pending - overdue) / pending) * 100)

    return {
        "integrity": integrity_pct,
        "credibility": credibility_pct,
        "pending": pending,
        "overdue": overdue
    }
def overdue_lectures(key):
    cfg = PHASE1_SUBJECTS[key]
    rows = load_csv(cfg["csv"])
    progress = load_progress(cfg["progress"])

    today = date.today()
    out = []

    for r in rows:
        k = f"{r['chapter_name']}||{r['topic_name']}"
        done = progress.get(k, {}).get("completed")
        target = parse_date(r.get("target_date"))

        if not done and target and target < today:
            out.append({
                "chapter": r["chapter_name"],
                "topic": r["topic_name"],
                "target": target,
                "days_overdue": (today - target).days
            })

    return out

# ======================================================
# SUBJECT DASHBOARD BUILDER
# ======================================================

def build_subject_dashboard(key):
    cfg = PHASE1_SUBJECTS[key]
    rows = load_csv(cfg["csv"])
    progress = load_progress(cfg["progress"])

    chapters = defaultdict(list)
    for r in rows:
        chapters[r["chapter_name"]].append(r)

    output = []
    for ch, items in chapters.items():
        done = 0
        for i in items:
            k = f"{ch}||{i['topic_name']}"
            if progress.get(k, {}).get("completed"):
                done += 1

        output.append({
            "chapter": ch,
            "done": done,
            "total": len(items),
            "topics": items
        })

    return output, progress
def sync_progress_with_csv(subject_key):
    cfg = PHASE1_SUBJECTS[subject_key]

    rows = load_csv(cfg["csv"])
    progress = load_progress(cfg["progress"])

    # Valid keys from CSV
    valid_keys = {
        f"{r['chapter_name']}||{r['topic_name']}"
        for r in rows
    }

    # Remove stale progress entries
    cleaned = {
        k: v for k, v in progress.items()
        if k in valid_keys
    }

    # Save only if something changed
    if cleaned != progress:
        save_progress(cfg["progress"], cleaned)


# ======================================================
# ROUTES
# ======================================================
@app.before_request
def refresh_csv_data():
    for key in PHASE1_SUBJECTS:
        sync_progress_with_csv(key)

@app.route("/", methods=["GET", "POST"])
def dashboard():
    # Handle mark done / undo from overdue panel
    if request.method == "POST":
        subject = request.form["subject"]
        chapter = request.form["chapter"]
        topic = request.form["topic"]
        action = request.form["action"]

        cfg = PHASE1_SUBJECTS[subject]
        progress = load_progress(cfg["progress"])
        key = f"{chapter}||{topic}"

        if action == "undo":
            progress.pop(key, None)
        else:
            progress[key] = {
                "completed": True,
                "completed_date": date.today().isoformat()
            }

        save_progress(cfg["progress"], progress)
        return redirect("/")

    # Phase-1 summary
    p1 = phase1_summary()

    subjects = []
    overdue_map = {}

    for key, cfg in PHASE1_SUBJECTS.items():
        data = subject_analysis(key)

        subjects.append({
            "key": key,
            "subject": cfg["name"],
            "percent": data["integrity"],
            "overdue": data["overdue"]
        })

        overdue_map[key] = overdue_lectures(key)

    # Phase-2 placeholder
    p2 = {"integrity": "N/A", "credibility": "N/A"}

    return render_template(
        "dashboard.html",
        p1_integrity=p1["integrity"],
        p1_credibility=p1["credibility"],
        p2_integrity=p2["integrity"],
        p2_credibility=p2["credibility"],
        subjects=subjects,
        overdue_map=overdue_map
    )

    p1 = phase1_summary()

    # TEMP Phase-2 placeholder (prevents NameError)
    p2 = {
        "integrity": "N/A",
        "credibility": "N/A"
    }

    return render_template(
        "dashboard.html",
        p1_integrity=p1["integrity"],
        p1_credibility=p1["credibility"],
        p2_integrity=p2["integrity"],
        p2_credibility=p2["credibility"],
        subjects=[]
    )


@app.route("/phase-1")
def phase_1():
    return render_template(
        "phase1.html",
        qa_pct=subject_analysis("quant")["integrity"],
        reasoning_pct=subject_analysis("reasoning")["integrity"],
        english_pct=subject_analysis("english")["integrity"],
        ga_pct=subject_analysis("ga")["integrity"]
    )


@app.route("/phase-1/<subject>", methods=["GET", "POST"])
def phase1_subject(subject):
    if subject not in PHASE1_SUBJECTS:
        return redirect("/phase-1")

    cfg = PHASE1_SUBJECTS[subject]

    if request.method == "POST":
        chapter = request.form["chapter"]
        topic = request.form["topic"]
        action = request.form["action"]

        progress = load_progress(cfg["progress"])
        key = f"{chapter}||{topic}"

        if action == "undo":
            progress.pop(key, None)
        else:
            progress[key] = {
                "completed": True,
                "completed_date": date.today().isoformat()
            }

        save_progress(cfg["progress"], progress)
        return redirect(f"/phase-1/{subject}")

    chapters, progress = build_subject_dashboard(subject)

    return render_template(
        "reasoning_dashboard.html",
        chapters=chapters,
        progress=progress
    )

# ======================================================
# CONTEXT
# ======================================================

@app.context_processor
def inject_globals():
    return dict(
        days_left=(EXAM_DATE - date.today()).days
    )

# ======================================================
# START
# ======================================================

if __name__ == "__main__":
    app.run(debug=True)
