MAX_ACTIVE_NOW = 3
MAX_ACTIVE_PER_LIFE_AREA = 1
MAX_Q1_ITEMS_WARNING = 3

LIFE_AREAS = [
    ("milano_admin", "Relocation / Admin"),
    ("etf_master", "Graduate Studies"),
    ("ai_portfolio_career", "AI Portfolio / Career"),
    ("ai_projects", "AI Projects"),
    ("training_health", "Training / Health"),
    ("business_income", "Business / Income"),
    ("learning_research", "Learning / Research"),
    ("communication_validation", "Communication / Validation"),
]

LIFE_AREA_LABELS = dict(LIFE_AREAS)

QUADRANTS = [
    ("Q1", "Q1 - Important & Urgent"),
    ("Q2", "Q2 - Important, Not Urgent"),
    ("Q3", "Q3 - Urgent, Less Important"),
    ("Q4", "Q4 - Parking / Not Now"),
]

QUADRANT_LABELS = dict(QUADRANTS)

LEVELS = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]

LEVEL_LABELS = dict(LEVELS)

FOCUS_STATES = [
    ("active", "Active Now"),
    ("scheduled", "Scheduled"),
    ("parking", "Parking"),
]

FOCUS_STATE_LABELS = dict(FOCUS_STATES)


def life_area_label(key):
    return LIFE_AREA_LABELS.get(key, "Not classified yet")


def quadrant_label(key):
    return QUADRANT_LABELS.get(key, "No quadrant yet")


def level_label(key):
    return LEVEL_LABELS.get(key, "-")


def focus_state_label(key):
    return FOCUS_STATE_LABELS.get(key, "Inbox")
