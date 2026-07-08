import re

from priority_constants import life_area_label, quadrant_label

LIFE_AREA_KEYWORDS = {
    "milano_admin": [
        "milano", "relocation", "visa", "embassy", "diploma", "translation",
        "apostille", "landlord", "accommodation", "contract",
        "codice fiscale", "permesso", "polimi", "university documents",
        "permit", "residency", "document", "apartment", "lease", "rent",
        "notary", "immigration",
    ],
    "etf_master": [
        "thesis", "exam", "professor", "course", "enrollment",
        "etf", "master", "credits", "faculty",
    ],
    "ai_portfolio_career": [
        "portfolio", "website", "v1.1", "project page", "case study",
        "screenshots", "text polish", "github", "vercel", "cv", "linkedin",
        "resume", "recruiter", "job application", "hiring",
    ],
    "ai_projects": [
        "agent", "app", "mvp", "n8n", "automation", "ai growth advisor",
        "business intelligence", "job search assistant", "balkan tv",
        "notion system",
    ],
    "training_health": [
        "training", "gym", "workout", "session", "mobility", "walk",
        "tired", "energy", "health", "maintain consistency", "recovery",
        "sleep", "doctor", "appointment",
    ],
    "business_income": [
        "client", "invoice", "payment", "business", "income", "freelance",
    ],
    "learning_research": [
        "research", "paper", "learning", "study", "book",
    ],
    "communication_validation": [
        "client", "outreach", "sales call", "validation", "linkedin message",
        "pitch", "feedback", "interview", "mentor",
    ],
}

HIGH_IMPORTANCE_AREAS = {
    "milano_admin", "etf_master", "business_income", "ai_portfolio_career",
}

PARKING_MARKERS = [
    "not urgent", "no rush", "someday", "backlog", "just an idea",
    "save it so", "do not forget", "don't forget", "for later", "not now",
]

DONE_MARKERS = [
    "sent", "submitted", "applied", "completed", "finished", "paid",
    "booked", "mailed", "delivered", "dropped off", "signed",
]
WAITING_MARKERS = ["waiting", "pending", "on hold", "still waiting"]
PLANNED_MARKERS = ["planned", "will", "going to", "scheduled to", "plan to"]
EXTERNAL_SUBJECT_MARKERS = [
    "landlord", "embassy", "bank", "company", "they", "school",
    "university", "clinic", "doctor", "support team", "office",
]

DATE_PATTERN = re.compile(
    r"\b(today|tomorrow|next week|next month|this week|monday|tuesday|"
    r"wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

STATUS_LABELS = {
    "waiting": "Waiting",
    "planned": "Planned",
    "in_progress": "In Progress",
    "note": "Note",
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "for", "to", "of", "in", "on",
    "at", "is", "am", "are", "was", "were", "will", "with", "this", "that",
    "it", "my", "i", "so", "not", "no", "do", "does", "did", "should",
    "by", "until", "week", "today", "tomorrow", "next", "end", "currently",
    "waiting", "planned", "final", "just", "only", "want", "save",
    "forget", "remember", "again", "have", "has", "had", "be", "been",
}


def _keyword_hit(keyword, lowered_text):
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, lowered_text) is not None


def split_clauses(text):
    raw = re.split(r"[.;,]", text)
    return [c.strip() for c in raw if c.strip()]


def find_date_phrase(clause):
    match = DATE_PATTERN.search(clause)
    return match.group(1).lower() if match else None


def _any_marker(markers, lowered):
    return any(_keyword_hit(marker, lowered) for marker in markers)


def classify_clause(clause):
    lowered = clause.lower()
    if _any_marker(WAITING_MARKERS, lowered):
        return "waiting"
    if _any_marker(DONE_MARKERS, lowered):
        return "done"
    if _any_marker(PLANNED_MARKERS, lowered):
        return "planned"
    if _any_marker(EXTERNAL_SUBJECT_MARKERS, lowered):
        return "external"
    return "other"


def detect_parking_signal(text):
    lowered = text.lower()
    return _any_marker(PARKING_MARKERS, lowered)


def detect_life_area(text):
    lowered = text.lower()
    best_key = None
    best_score = 0
    for key, keywords in LIFE_AREA_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if _keyword_hit(kw, lowered):
                score += 2 if " " in kw else 1
        if score > best_score:
            best_score = score
            best_key = key
    return best_key if best_score > 0 else None


def _waiting_next_action(waiting_clause):
    match = re.search(r"waiting\s+(?:until\s+)?(.+)", waiting_clause, re.IGNORECASE)
    if match:
        return f"Check back {match.group(1).strip().rstrip('.')}"
    return f"Follow up: {waiting_clause}"


def _classify_quadrant(life_area, status, has_date, parking_signal):
    if parking_signal:
        return "Q4"

    if life_area is None:
        return "Q4"

    if life_area == "training_health":
        return "Q2"

    if life_area in HIGH_IMPORTANCE_AREAS:
        if status == "waiting" or has_date:
            return "Q1"
        return "Q2"

    if has_date and status in ("waiting", "planned"):
        return "Q3"

    return "Q2" if status != "note" else "Q4"


def _tokenize(text):
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'.]*", (text or "").lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def parse_status_update(text):
    text = (text or "").strip()
    if not text:
        return None

    clauses = split_clauses(text)
    tagged = [(clause, classify_clause(clause), find_date_phrase(clause)) for clause in clauses]

    waiting_clauses = [c for c in tagged if c[1] == "waiting"]
    done_clauses = [c for c in tagged if c[1] == "done"]
    planned_clauses = [c for c in tagged if c[1] == "planned"]
    external_clauses = [c for c in tagged if c[1] == "external"]

    has_date = any(date for _, _, date in tagged)
    life_area = detect_life_area(text)
    parking_signal = detect_parking_signal(text)

    if waiting_clauses:
        status = "waiting"
    elif planned_clauses and not done_clauses:
        status = "planned"
    elif done_clauses:
        status = "in_progress"
    else:
        status = "note"

    quadrant = _classify_quadrant(life_area, status, has_date, parking_signal)

    blocker = None
    if waiting_clauses:
        waiting_text = waiting_clauses[0][0]
        if done_clauses:
            blocker = f"{done_clauses[-1][0]} (now {waiting_text})"
        else:
            blocker = waiting_text

    next_action = None
    if waiting_clauses:
        next_action = _waiting_next_action(waiting_clauses[0][0])
    elif planned_clauses:
        next_action = planned_clauses[0][0]
    elif done_clauses:
        next_action = f"Confirm outcome of: {done_clauses[0][0]}"

    follow_up_action = None
    if planned_clauses:
        if next_action != planned_clauses[0][0]:
            follow_up_action = planned_clauses[0][0]
        elif len(planned_clauses) > 1:
            follow_up_action = planned_clauses[1][0]

    external_dependency = external_clauses[0][0] if external_clauses else None

    review_date = None
    if waiting_clauses and waiting_clauses[0][2]:
        review_date = waiting_clauses[0][2]
    else:
        for _, _, date in tagged:
            if date:
                review_date = date
                break

    if parking_signal:
        recommended_decision = "No action needed now; park this as a backlog/idea item for later review."
    elif status == "waiting":
        rd = review_date.capitalize() if review_date else "the next check-in"
        recommended_decision = f"No extra work today; review again {rd}."
    elif status == "planned":
        rd = review_date.capitalize() if review_date else "the planned date"
        recommended_decision = f"No action needed until {rd}; proceed with the planned step then."
    elif status == "in_progress":
        recommended_decision = "Confirm the next concrete step and set a review date."
    else:
        recommended_decision = "Capture as a note; no clear next action detected yet."

    if life_area == "training_health" and not parking_signal:
        recommended_decision = (
            "Keep it minimal - the goal is maintaining consistency, not adding a new project."
        )

    quadrant_note = quadrant_label(quadrant)
    if quadrant == "Q1" and status == "waiting":
        quadrant_note = "Q1 - important and time-sensitive, but currently waiting for external input"
    elif quadrant == "Q4" and parking_signal:
        quadrant_note = "Q4 - Parking / Not Now (explicitly marked not urgent)"

    if life_area and next_action and status != "note":
        confidence = "high"
    elif life_area:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "raw_text": text,
        "life_area": life_area,
        "life_area_label": life_area_label(life_area) if life_area else "Not classified yet",
        "quadrant": quadrant,
        "quadrant_note": quadrant_note,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "blocker": blocker,
        "next_action": next_action,
        "follow_up_action": follow_up_action,
        "external_dependency": external_dependency,
        "review_date": review_date,
        "recommended_decision": recommended_decision,
        "confidence": confidence,
        "parking_signal": parking_signal,
    }


def find_strong_match(parsed, existing_items, min_shared=2):
    life_area = parsed["life_area"]
    if not life_area:
        return None

    parsed_tokens = _tokenize(parsed["raw_text"])
    if not parsed_tokens:
        return None

    best = None
    for item in existing_items:
        item_id, title, description = item[0], item[1], item[2]
        item_life_area, item_status = item[3], item[9]

        if item_life_area != life_area or item_status == "parking":
            continue

        item_tokens = _tokenize(f"{title} {description or ''}")
        shared = parsed_tokens & item_tokens
        score = len(shared)

        if score >= min_shared and (best is None or score > best[2]):
            best = (item_id, title, score)

    return best


def suggest_system_action(parsed, existing_items):
    life_area = parsed["life_area"]
    confidence = parsed["confidence"]

    if not life_area:
        return {
            "action": "note",
            "item_id": None,
            "text": "No clear life area detected - keep this as a note only.",
        }

    if confidence == "low":
        return {
            "action": "note",
            "item_id": None,
            "text": "Low confidence in this classification - keep this as a note only.",
        }

    if parsed["parking_signal"]:
        return {
            "action": "create",
            "item_id": None,
            "text": (
                f"Create a new {parsed['life_area_label']} parking/backlog item "
                f"(explicitly marked not urgent)."
            ),
        }

    match = find_strong_match(parsed, existing_items)
    if match:
        item_id, title, score = match
        return {
            "action": "update",
            "item_id": item_id,
            "text": (
                f"Update existing item #{item_id} \"{title}\" - "
                f"strong title/topic match ({score} shared keyword(s))."
            ),
        }

    return {
        "action": "create",
        "item_id": None,
        "text": f"Create a new {parsed['life_area_label']} inbox item with status \"{parsed['status_label']}\".",
    }


def build_notes_block(parsed):
    lines = [
        f"[Status Update] {parsed['raw_text']}",
        f"Status: {parsed['status_label']}",
    ]
    if parsed["blocker"]:
        lines.append(f"Blocker: {parsed['blocker']}")
    if parsed["follow_up_action"]:
        lines.append(f"Follow-up: {parsed['follow_up_action']}")
    if parsed["external_dependency"]:
        lines.append(f"External dependency: {parsed['external_dependency']}")
    if parsed["review_date"]:
        lines.append(f"Review date: {parsed['review_date']}")
    lines.append(f"Recommended decision: {parsed['recommended_decision']}")
    return "\n".join(lines)


def render_status_update_markdown(parsed, suggestion):
    if not parsed:
        return "_Enter a status update above and click Parse Update._"

    return f"""### Parsed Status Update

**Area:** {parsed['life_area_label']}

**Quadrant:** {parsed['quadrant_note']}

**Status:** {parsed['status_label']}

**Current blocker:** {parsed['blocker'] or '-'}

**Next action:** {parsed['next_action'] or '-'}

**Follow-up action:** {parsed['follow_up_action'] or '-'}

**External dependency:** {parsed['external_dependency'] or '-'}

**Review date:** {parsed['review_date'].capitalize() if parsed['review_date'] else '-'}

**Recommended decision:** {parsed['recommended_decision']}

**Suggested system action:** {suggestion['text']}
"""
