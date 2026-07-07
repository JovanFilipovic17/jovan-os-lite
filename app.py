import asyncio
import os
from datetime import date
from pathlib import Path
from scoring import calculate_weighted_overall, update_markdown_overall_score
from demo_outputs import (
    demo_plan_output,
    demo_evaluation_output,
    demo_weekly_review_output,
    demo_optimizer_output,
    demo_apply_weights_output,
)

import gradio as gr
from dotenv import load_dotenv

#from notes import summary
from database import (
    configure_database_path,
    get_goals,
    get_domain_weights,
    get_recent_logs,
    get_recent_evaluations,
    get_recent_plans,
    save_evaluation,
    add_daily_log,
    export_latest_evaluation_to_md,
    save_plan,
    export_latest_plan_to_md,
    get_latest_evaluation,
    save_optimization,
    export_latest_optimization_to_md,
    get_latest_optimization,
    create_tables,
    apply_latest_optimization_weights,
    add_item,
    get_all_items,
    get_inbox_items,
    get_items_by_status,
    get_items_by_quadrant,
    classify_item,
    move_item_status,
)
from priority_constants import (
    LIFE_AREAS,
    QUADRANTS,
    LEVELS,
    FOCUS_STATES,
    MAX_ACTIVE_NOW,
    life_area_label,
    quadrant_label,
    focus_state_label,
)

explicit_demo_mode = os.environ.get("DEMO_MODE")
load_dotenv(override=False)
DEMO_MODE = (explicit_demo_mode or "true").lower() == "true"
LIVE_DB_PATH = Path("data/jovan_os.db")
DEMO_DB_PATH = Path("data/demo_jovan_os.db")

if not DEMO_MODE:
    from os_agents import plan_day, evaluate_day, evaluate_week, optimize_goals

def initialize_database():
    if DEMO_MODE:
        configure_database_path(DEMO_DB_PATH)
        if DEMO_DB_PATH.exists():
            DEMO_DB_PATH.unlink()
        create_tables()
        from seed_demo import seed_demo_data
        seed_demo_data()
        return

    configure_database_path(LIVE_DB_PATH)
    create_tables()


initialize_database()
DOMAIN_LABELS = {
    "formalno_obrazovanje": "Formal Education",
    "neformalno_obrazovanje": "Projects / Skill Building",
    "sport": "Health / Training",
    "karijera": "Career Visibility",
}


def domain_label(domain):
    return DOMAIN_LABELS.get(domain, domain)


LIFE_AREA_CHOICES = [(label, key) for key, label in LIFE_AREAS]
QUADRANT_CHOICES = [(label, key) for key, label in QUADRANTS]
LEVEL_CHOICES = [(label, key) for key, label in LEVELS]
FOCUS_STATE_CHOICES = [(label, key) for key, label in FOCUS_STATES]


def item_choice_label(item):
    (item_id, title, description, life_area, importance, urgency, quadrant,
     next_action, deadline, status, energy_required, difficulty, notes,
     created_at, updated_at) = item
    area = life_area_label(life_area) if life_area else "Not classified yet"
    quad = quadrant_label(quadrant) if quadrant else "No quadrant yet"
    return f"#{item_id} {title} ({area}, {quad}, {status})"


def item_choices(items):
    return [(item_choice_label(item), item[0]) for item in items]


def classified_items():
    return [item for item in get_all_items() if item[6]]


def classified_item_choices():
    return item_choices(classified_items())


def render_inbox_markdown():
    items = get_inbox_items()

    if not items:
        return "_Inbox is empty. Capture something above._"

    lines = []
    for item in items:
        (item_id, title, description, life_area, importance, urgency, quadrant,
         next_action, deadline, status, energy_required, difficulty, notes,
         created_at, updated_at) = item
        desc = f" - {description}" if description else ""
        area = life_area_label(life_area) if life_area else "Not classified yet"
        quad = quadrant_label(quadrant) if quadrant else "No quadrant yet"
        lines.append(f"- **#{item_id} {title}**{desc} _(Area: {area}, Quadrant: {quad})_")

    return "\n".join(lines)


def render_matrix_markdown():
    sections = []

    for key, label in QUADRANTS:
        items = get_items_by_quadrant(key)
        sections.append(f"### {label}")

        if not items:
            sections.append("_No items._")
        else:
            for item in items:
                (item_id, title, description, life_area, importance, urgency, quadrant,
                 next_action, deadline, status, energy_required, difficulty, notes,
                 created_at, updated_at) = item
                area = life_area_label(life_area) if life_area else "-"
                next_act = next_action or "-"
                deadline_txt = deadline or "-"
                lane = "Inbox" if status == "inbox" else focus_state_label(status)
                sections.append(
                    f"- **#{item_id} {title}** ({area}) - Next: {next_act} - Deadline: {deadline_txt} - Lane: {lane}"
                )

        sections.append("")

    return "\n".join(sections)


def render_focus_markdown():
    active_items = get_items_by_status("active")
    scheduled_items = get_items_by_status("scheduled")
    parking_items = get_items_by_status("parking")

    def render_group(items):
        if not items:
            return "_No items._"

        lines = []
        for item in items:
            (item_id, title, description, life_area, importance, urgency, quadrant,
             next_action, deadline, status, energy_required, difficulty, notes,
             created_at, updated_at) = item
            area = life_area_label(life_area) if life_area else "-"
            quad = quadrant_label(quadrant) if quadrant else "-"
            lines.append(f"- **#{item_id} {title}** ({area}, {quad})")

        return "\n".join(lines)

    warning_md = ""
    if len(active_items) > MAX_ACTIVE_NOW:
        warning_md = (
            f"\n> **Warning:** {len(active_items)} items are Active Now. "
            f"Keep Active Now to a maximum of {MAX_ACTIVE_NOW} big focuses.\n"
        )

    return f"""### Active Now ({len(active_items)})
{warning_md}
{render_group(active_items)}

### Scheduled ({len(scheduled_items)})

{render_group(scheduled_items)}

### Parking ({len(parking_items)})

{render_group(parking_items)}
"""


def ui_add_item(title, description):
    if not title.strip():
        return "Enter a title before adding to the inbox.", render_inbox_markdown()

    add_item(title.strip(), description.strip())
    return "Added to inbox.", render_inbox_markdown()


def ui_refresh_matrix():
    return gr.Dropdown(choices=item_choices(get_all_items())), render_matrix_markdown()


def ui_classify_item(
    item_id, life_area, importance, urgency, quadrant,
    next_action, deadline, energy_required, difficulty, notes,
):
    dropdown_update = gr.Dropdown(choices=item_choices(get_all_items()))

    if item_id is None:
        return "Select an item first.", render_matrix_markdown(), dropdown_update

    if not quadrant:
        return "Select a quadrant (Q1-Q4) before saving.", render_matrix_markdown(), dropdown_update

    classify_item(
        item_id,
        life_area=life_area,
        importance=importance,
        urgency=urgency,
        quadrant=quadrant,
        next_action=next_action,
        deadline=deadline,
        energy_required=energy_required,
        difficulty=difficulty,
        notes=notes,
    )

    return "Item classified.", render_matrix_markdown(), gr.Dropdown(choices=item_choices(get_all_items()))


def ui_refresh_focus():
    return gr.Dropdown(choices=classified_item_choices()), render_focus_markdown()


def ui_move_item(item_id, target_status):
    dropdown_update = gr.Dropdown(choices=classified_item_choices())

    if item_id is None:
        return "Select an item first.", render_focus_markdown(), dropdown_update

    if not target_status:
        return "Select a target lane first.", render_focus_markdown(), dropdown_update

    try:
        active_count, warning = move_item_status(item_id, target_status)
    except ValueError as exc:
        return str(exc), render_focus_markdown(), dropdown_update

    message = f"Item moved to {focus_state_label(target_status)}."
    if warning:
        message += f" Warning: {active_count} items are now Active Now (recommended max: {MAX_ACTIVE_NOW})."

    return message, render_focus_markdown(), gr.Dropdown(choices=classified_item_choices())


def run_planner(request):
    if not request.strip():
        return "Enter a plan request."

    if DEMO_MODE:
        plan_markdown = demo_plan_output()
        save_plan(
            date=str(date.today()),
            summary="Synthetic demo plan",
            markdown=plan_markdown,
        )
        return plan_markdown

    result = asyncio.run(
        plan_day(
            request,
            get_goals(),
            get_domain_weights(),
            get_recent_logs(),
            get_recent_evaluations(),
        )
    )

    save_plan(
        date=str(date.today()),
        summary=result.summary,
        markdown=result.markdown,
    )

    export_latest_plan_to_md()

    return result.markdown

def run_evaluator(day_log):
    if not day_log.strip():
        return "Enter a daily execution log."

    if DEMO_MODE:
        evaluation_markdown = demo_evaluation_output()
        add_daily_log(
            date=str(date.today()),
            formal="Completed one focused study block.",
            informal="Fixed one small project issue.",
            sport="Skipped training due to time constraints.",
            career="Career visibility task not mentioned.",
            sleep_hours=None,
            energy=None,
            notes="Synthetic demo execution log.",
        )
        save_evaluation(
            period_type="day",
            period_label=str(date.today()),
            score=7.2,
            feedback=evaluation_markdown,
            next_actions=(
                "Schedule training earlier or reduce it to a 10-minute fallback.\n"
                "Keep the next study block narrow and outcome-based.\n"
                "End the next project block with one visible artifact or note."
            ),
        )
        return evaluation_markdown

    plans = get_recent_plans(limit=1)
    latest_plan = plans[0][2] if plans else "No plan available."

    result = asyncio.run(
        evaluate_day(
            day_log,
            latest_plan,
            get_goals(),
            get_domain_weights(),
            get_recent_logs(),
            get_recent_evaluations(),
        )
    )

    llm_score = result.overall_score

    weighted_score = calculate_weighted_overall(
        evaluation=result,
        weights=get_domain_weights(),
    )

    result.overall_score = weighted_score
    result.markdown = update_markdown_overall_score(
        markdown=result.markdown,
        weighted_score=weighted_score,
        llm_score=llm_score,
    )

    save_evaluation(
        period_type="day",
        period_label=str(date.today()),
        score=result.overall_score,
        feedback=result.markdown,
        next_actions="\n".join(result.next_actions),
    )

    export_latest_evaluation_to_md()

    return result.markdown

def run_weekly_review():
    if DEMO_MODE:
        return demo_weekly_review_output()

    recent_logs = get_recent_logs(limit=7)
    recent_evaluations = get_recent_evaluations(limit=7)
    recent_plans = get_recent_plans(limit=7)

    if not recent_evaluations and not recent_logs:
        return "Not enough saved logs or evaluations for a weekly review."

    result = asyncio.run(
        evaluate_week(
            get_goals(),
            get_domain_weights(),
            recent_logs,
            recent_evaluations,
            recent_plans,
        )
    )

    llm_score = result.overall_score

    weighted_score = calculate_weighted_overall(
        evaluation=result,
        weights=get_domain_weights(),
    )

    result.overall_score = weighted_score
    result.markdown = update_markdown_overall_score(
        markdown=result.markdown,
        weighted_score=weighted_score,
        llm_score=llm_score,
    )

    save_evaluation(
        period_type="week",
        period_label=str(date.today()),
        score=result.overall_score,
        feedback=result.markdown,
        next_actions="\n".join(result.next_actions),
    )

    export_latest_evaluation_to_md()

    return result.markdown

def run_optimizer():
    if DEMO_MODE:
        optimizer_markdown = demo_optimizer_output()
        save_optimization(
            summary="Synthetic demo optimizer report",
            markdown=optimizer_markdown,
            weight_recommendations=[],
            goal_recommendations=[],
        )
        return optimizer_markdown

    recent_logs = get_recent_logs(limit=14)
    recent_evaluations = get_recent_evaluations(limit=10)

    if not recent_evaluations:
        return "Not enough evaluations for the optimizer. Run at least one daily or weekly evaluation first."

    result = asyncio.run(
        optimize_goals(
            get_goals(),
            get_domain_weights(),
            recent_logs,
            recent_evaluations,
        )
    )

    save_optimization(
        summary=result.summary,
        markdown=result.markdown,
        weight_recommendations=[
            rec.model_dump() for rec in result.weight_recommendations
        ],
        goal_recommendations=[
            rec.model_dump() for rec in result.goal_recommendations
        ],
    )

    export_latest_optimization_to_md()

    return result.markdown

def run_apply_latest_weights():
    if DEMO_MODE:
        return demo_apply_weights_output()

    new_weights, message = apply_latest_optimization_weights()

    if not new_weights:
        return f"## Apply Weights\n\n{message}"

    rows_md = "\n".join(
        [
            f"| {domain} | {weight}% |"
            for domain, weight in new_weights.items()
        ]
    )

    return f"""
## Apply Weights

{message}

### New Domain Weights

| Domain | Weight |
|---|---:|
{rows_md}
"""

def dashboard():
    goals = get_goals()
    weights = get_domain_weights()
    logs = get_recent_logs()
    plans = get_recent_plans(limit=1)
    latest_eval = get_latest_evaluation()
    latest_optimization = get_latest_optimization()

    latest_plan_md = plans[0][2] if plans else "_No saved plan yet._"

    if latest_eval:
        period_type, period_label, score, feedback, next_actions, created_at = latest_eval
        latest_score = f"{score}/10"
        latest_eval_preview = feedback[:2500]
    else:
        latest_score = "No evaluation yet"
        latest_eval_preview = "_No evaluation yet._"
        created_at = "-"

    if latest_optimization:
        optimization_md = latest_optimization[2]
    else:
        optimization_md = "_No optimization report yet._"

    weights_md = "\n".join(
        [f"- **{domain_label(domain)}**: {weight}%" for domain, weight in weights]
    ) or "_No domain weights defined._"

    active_goals = [g for g in goals if g[4] == "active"]

    unique_goals = []
    seen = set()

    for goal in active_goals:
        domain = goal[1]
        title = goal[2]
        priority = goal[5]

        key = (domain, title, priority)

        if key not in seen:
            unique_goals.append(goal)
            seen.add(key)

    goals_md = "\n".join(
        [
            f"- **{goal[2]}** ({domain_label(goal[1])}, priority: {goal[5]})"
            for goal in unique_goals
        ]
    ) or "_No active goals._"

    return f"""
# Jovan OS Lite Dashboard

## Current Status

| Metric | Value |
|---|---|
| Latest score | **{latest_score}** |
| Last evaluation date | {created_at} |
| Active goals | {len(unique_goals)} |
| Recent logs loaded | {len(logs)} |

---

## Current Domain Weights

{weights_md}

---

## Active Goals

{goals_md}

---

## Latest Plan

{latest_plan_md}

---

## Latest Evaluation

{latest_eval_preview}

---

## Latest Optimization

{optimization_md}
"""

APP_CSS = """
:root {
    --jos-page: #f6f0e4;
    --jos-page-soft: #fbf7ee;
    --jos-surface: #fffdf8;
    --jos-surface-muted: #f2eadc;
    --jos-card: #fffaf1;
    --jos-border: #dfd0b8;
    --jos-border-soft: #eadfcc;
    --jos-text: #111827;
    --jos-muted: #61574a;
    --jos-accent: #d7aa58;
    --jos-accent-dark: #b88935;
    --jos-accent-soft: #ead8b5;
    --jos-shadow: 0 18px 42px rgba(79, 64, 40, 0.13);
    --jos-shadow-soft: 0 10px 24px rgba(79, 64, 40, 0.09);
}

body {
    background: radial-gradient(circle at top, #fffaf0 0%, #f6f0e4 48%, #f3eadc 100%) !important;
}

.gradio-container {
    max-width: 940px !important;
    margin: 0 auto !important;
    padding: 44px 22px 54px !important;
    color: var(--jos-text);
}

.jos-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 300px;
    align-items: center;
    gap: 28px;
    margin: 0 auto 22px;
    padding: 30px;
    border: 1px solid var(--jos-border-soft);
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(255, 253, 248, 0.96) 0%, rgba(247, 239, 224, 0.94) 100%);
    box-shadow: var(--jos-shadow);
}

.jos-hero h1 {
    margin: 0 0 8px;
    font-size: 34px;
    line-height: 1.08;
    font-weight: 780;
    letter-spacing: 0;
    color: #172033;
}

.jos-subtitle {
    margin: 0 0 14px;
    max-width: 600px;
    color: #172033;
    font-size: 15.5px;
    line-height: 1.42;
}

.jos-loop-pill {
    display: inline-flex;
    max-width: 100%;
    padding: 6px 11px;
    border: 1px solid #d4b77e;
    border-radius: 999px;
    background: #fff7e8;
    color: #152033;
    font-size: 12.5px;
    line-height: 1.2;
    white-space: nowrap;
}

.jos-badges {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
}

.jos-badge {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 5px 11px;
    border: 1px solid #e1c895;
    border-radius: 999px;
    background: #ead8b5;
    color: #2f2518;
    font-size: 12.5px;
    line-height: 1;
}

.jos-badge.strong {
    background: #d7aa58;
    border-color: #c79b4a;
    color: #1f1a12;
}

.jos-mode-notice {
    margin: 0 0 18px;
    padding: 12px 16px;
    border: 1px solid #d7bd86;
    border-radius: 12px;
    background: #fff7e8;
    color: #3f2f17;
    font-size: 13.5px;
    line-height: 1.4;
    box-shadow: var(--jos-shadow-soft);
}

.jos-tabs-shell {
    overflow: hidden;
    border: 1px solid var(--jos-border-soft);
    border-radius: 18px;
    background: rgba(255, 253, 248, 0.96);
    box-shadow: var(--jos-shadow);
}

.jos-panel {
    padding: 28px;
    background: var(--jos-surface);
}

.jos-screen-title {
    margin: 0 0 16px;
    color: #172033;
    font-size: 21px;
    font-weight: 760;
    line-height: 1.25;
}

.jos-info {
    margin-bottom: 18px;
    padding: 18px 20px;
    border: 1px solid var(--jos-border);
    border-radius: 12px;
    background: linear-gradient(180deg, #fffdf8 0%, #fbf3e4 100%);
    box-shadow: var(--jos-shadow-soft);
}

.jos-info h3,
.jos-output-card h3 {
    margin: 0 0 8px;
    color: #172033;
    font-size: 17px;
    font-weight: 740;
    line-height: 1.25;
}

.jos-info p {
    margin: 0;
    color: #172033;
    font-size: 14.5px;
    line-height: 1.45;
}

.jos-request-block {
    margin-bottom: 14px;
}

.jos-action-row {
    justify-content: flex-start;
    margin: 0 0 18px;
}

.jos-output-card {
    width: 100%;
    padding: 0;
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

.jos-output-card h3 {
    margin: 0 0 10px;
}

.jos-output {
    min-height: 170px;
    padding: 18px;
    border: 1px solid #eadfcc !important;
    border-radius: 10px !important;
    background: rgba(255, 255, 255, 0.72) !important;
    box-shadow: none !important;
}

.jos-output.compact {
    min-height: 96px;
}

.jos-placeholder {
    min-height: 126px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: #1f2937;
    font-size: 14px;
    line-height: 1.45;
}

.gradio-container .tabs {
    border: 0 !important;
    background: transparent !important;
}

.gradio-container .tab-nav {
    display: grid !important;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: 6px !important;
    margin: 20px 20px 0 !important;
    padding: 6px !important;
    border: 0 !important;
    border-radius: 999px !important;
    background: #e8ddca !important;
}

.gradio-container .tab-nav button {
    min-height: 40px;
    padding: 8px 14px !important;
    border: 0 !important;
    border-radius: 999px !important;
    background: transparent !important;
    color: #6d5434 !important;
    font-size: 14.5px;
    font-weight: 560;
    box-shadow: none !important;
}

.gradio-container .tab-nav button.selected {
    background: #fffaf0 !important;
    color: #4f391c !important;
    box-shadow: 0 5px 13px rgba(79, 64, 40, 0.14) !important;
}

.jos-top-tabs > .tab-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    margin: 20px 20px 4px !important;
    padding: 7px !important;
    background: #e3d0a0 !important;
    border-radius: 16px !important;
}

.jos-top-tabs > .tab-nav button {
    min-height: 48px;
    border-radius: 12px !important;
    font-size: 16.5px !important;
    font-weight: 780 !important;
    letter-spacing: 0.1px;
    color: #6d5434 !important;
}

.jos-top-tabs > .tab-nav button.selected {
    background: #d7aa58 !important;
    color: #1f1a12 !important;
    box-shadow: 0 8px 18px rgba(180, 129, 48, 0.3) !important;
}

.jos-sub-tabs > .tab-nav {
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)) !important;
    margin: 4px 20px 0 !important;
    padding: 5px !important;
    background: #efe6d3 !important;
}

.jos-sub-tabs > .tab-nav button {
    min-height: 34px;
    font-size: 13px !important;
    font-weight: 540 !important;
    color: #7c6a4a !important;
}

.jos-sub-tabs > .tab-nav button.selected {
    background: #fffaf0 !important;
    color: #4f391c !important;
    box-shadow: 0 4px 10px rgba(79, 64, 40, 0.12) !important;
}

.jos-section-intro {
    margin: 16px 20px 0;
    padding: 14px 18px;
    border: 1px solid var(--jos-border-soft);
    border-radius: 12px;
    background: linear-gradient(180deg, #fffdf8 0%, #fbf3e4 100%);
    box-shadow: var(--jos-shadow-soft);
}

.jos-section-intro p {
    margin: 0;
    color: #172033;
    font-size: 14.5px;
    line-height: 1.45;
}

.gradio-container textarea,
.gradio-container input {
    border-color: #d8bf8f !important;
    border-radius: 12px !important;
    background: #fffdf8 !important;
    box-shadow: inset 0 1px 2px rgba(79, 64, 40, 0.05);
}

.gradio-container label span {
    color: #172033 !important;
    font-weight: 560 !important;
}

.gradio-container button.primary {
    border: 0 !important;
    border-radius: 999px !important;
    background: linear-gradient(180deg, #e1bb72 0%, #d4a34c 100%) !important;
    color: #17120a !important;
    font-weight: 760 !important;
    min-height: 44px;
    box-shadow: 0 10px 20px rgba(180, 129, 48, 0.24);
}

.gradio-container button.primary:hover {
    background: linear-gradient(180deg, #ddb163 0%, #c8943e 100%) !important;
}

.gradio-container button.secondary {
    border-radius: 999px !important;
    border-color: var(--jos-border) !important;
    background: #fffaf0 !important;
    color: #4f391c !important;
}

@media (max-width: 820px) {
    .gradio-container {
        padding: 28px 14px 42px !important;
    }

    .jos-hero {
        grid-template-columns: 1fr;
        padding: 24px;
    }

    .jos-badges {
        justify-content: flex-start;
    }

    .gradio-container .tab-nav {
        grid-template-columns: 1fr;
        border-radius: 16px !important;
    }

    .jos-panel {
        padding: 20px;
    }
}
"""

HEADER_MD = """
<div class="jos-hero">
  <div>
    <h1>Jovan OS Lite</h1>
    <p class="jos-subtitle">Local agentic AI operating system for planning, evaluation, weekly review, and human-approved optimization.</p>
    <div class="jos-loop-pill">Plan &rarr; Execute &rarr; Evaluate &rarr; Review &rarr; Optimize &rarr; Human Apply</div>
  </div>
  <div class="jos-badges">
    <span class="jos-badge">Planner Agent</span>
    <span class="jos-badge">Evaluator Agent</span>
    <span class="jos-badge">Optimizer Agent</span>
    <span class="jos-badge">SQLite State</span>
    <span class="jos-badge strong">Human Approval</span>
  </div>
</div>
"""



DEMO_NOTICE_MD = """
<div class="jos-mode-notice"><strong>Demo Mode:</strong> This hosted version uses synthetic data and static sample outputs. Clone the GitHub repo and run locally with your own OpenAI API key for live agent execution.</div>
"""

LIVE_NOTICE_MD = """
<div class="jos-mode-notice"><strong>Live Mode:</strong> using local database and OpenAI agent execution.</div>
"""
theme = gr.themes.Soft(
    primary_hue="amber",
    neutral_hue="stone",
    radius_size="lg",
).set(
    body_background_fill="#f6f0e4",
    block_background_fill="#fffdf8",
    block_border_color="#dfd0b8",
    button_primary_background_fill="#d4a34c",
    button_primary_background_fill_hover="#c8943e",
)


with gr.Blocks(title="Jovan OS Lite") as app:
    gr.HTML(HEADER_MD)
    gr.HTML(DEMO_NOTICE_MD if DEMO_MODE else LIVE_NOTICE_MD)

    with gr.Group(elem_classes="jos-tabs-shell"):
        with gr.Tabs(elem_classes="jos-top-tabs"):
            with gr.Tab("Priority OS"):
                gr.HTML(
                    """
                    <div class="jos-section-intro">
                      <p>Capture ideas, classify priorities, and limit active focus so the system helps decide what matters now.</p>
                    </div>
                    """
                )
                with gr.Tabs(elem_classes="jos-sub-tabs"):
                    with gr.Tab("Inbox"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Brain Dump Inbox</h2>")
                            gr.HTML(
                                """
                                <div class="jos-info">
                                  <h3>Capture First, Classify Later</h3>
                                  <p>Drop in ideas, obligations, worries, or projects here. Nothing becomes active until it is classified in the Matrix tab.</p>
                                </div>
                                """
                            )
                            with gr.Group(elem_classes="jos-request-block"):
                                inbox_title_input = gr.Textbox(
                                    label="Title",
                                    placeholder="Example: Finish portfolio website v1.1",
                                )
                                inbox_description_input = gr.Textbox(
                                    label="Description / Notes",
                                    lines=3,
                                    placeholder="Optional details, context, or why this matters.",
                                )
                            with gr.Row(elem_classes="jos-action-row"):
                                inbox_add_button = gr.Button("Add to Inbox", variant="primary")
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Add Status</h3>")
                                inbox_status_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>Nothing added yet.</div>",
                                    elem_classes="jos-output compact",
                                )
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Unclassified Inbox Items</h3>")
                                inbox_list_output = gr.Markdown(
                                    value=render_inbox_markdown(),
                                    elem_classes="jos-output",
                                )

                        inbox_add_button.click(
                            fn=ui_add_item,
                            inputs=[inbox_title_input, inbox_description_input],
                            outputs=[inbox_status_output, inbox_list_output],
                        )

                    with gr.Tab("Matrix"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Eisenhower Matrix</h2>")
                            gr.HTML(
                                """
                                <div class="jos-info">
                                  <h3>Classify Items</h3>
                                  <p>Assign a life area, importance, urgency, quadrant, next action, and deadline. An item needs a quadrant before it can move to Active Now, Scheduled, or Parking.</p>
                                </div>
                                """
                            )

                            matrix_item_dropdown = gr.Dropdown(
                                label="Select Item",
                                choices=item_choices(get_all_items()),
                            )

                            with gr.Row():
                                matrix_life_area = gr.Dropdown(label="Life Area", choices=LIFE_AREA_CHOICES)
                                matrix_quadrant = gr.Dropdown(label="Quadrant", choices=QUADRANT_CHOICES)

                            with gr.Row():
                                matrix_importance = gr.Dropdown(label="Importance", choices=LEVEL_CHOICES)
                                matrix_urgency = gr.Dropdown(label="Urgency", choices=LEVEL_CHOICES)

                            with gr.Row():
                                matrix_energy = gr.Dropdown(label="Energy Required", choices=LEVEL_CHOICES)
                                matrix_difficulty = gr.Dropdown(label="Difficulty", choices=LEVEL_CHOICES)

                            matrix_next_action = gr.Textbox(label="Next Action", placeholder="The single next concrete step.")
                            matrix_deadline = gr.Textbox(label="Deadline", placeholder="Optional, e.g. 2026-07-20")
                            matrix_notes = gr.Textbox(label="Notes", lines=3)

                            with gr.Row(elem_classes="jos-action-row"):
                                matrix_classify_button = gr.Button("Save Classification", variant="primary")
                                matrix_refresh_button = gr.Button("Refresh", variant="secondary")

                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Classification Status</h3>")
                                matrix_status_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>No changes yet.</div>",
                                    elem_classes="jos-output compact",
                                )

                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Matrix Board</h3>")
                                matrix_board_output = gr.Markdown(
                                    value=render_matrix_markdown(),
                                    elem_classes="jos-output",
                                )

                        matrix_classify_button.click(
                            fn=ui_classify_item,
                            inputs=[
                                matrix_item_dropdown, matrix_life_area, matrix_importance, matrix_urgency,
                                matrix_quadrant, matrix_next_action, matrix_deadline, matrix_energy,
                                matrix_difficulty, matrix_notes,
                            ],
                            outputs=[matrix_status_output, matrix_board_output, matrix_item_dropdown],
                        )

                        matrix_refresh_button.click(
                            fn=ui_refresh_matrix,
                            inputs=[],
                            outputs=[matrix_item_dropdown, matrix_board_output],
                        )

                    with gr.Tab("Active Now"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Active Now / Scheduled / Parking</h2>")
                            gr.HTML(
                                f"""
                                <div class="jos-info">
                                  <h3>Focus Discipline</h3>
                                  <p>Only classified items (with a quadrant) can move here. Keep Active Now to a maximum of {MAX_ACTIVE_NOW} big focuses.</p>
                                </div>
                                """
                            )

                            focus_item_dropdown = gr.Dropdown(
                                label="Select Classified Item",
                                choices=classified_item_choices(),
                            )
                            focus_target_dropdown = gr.Dropdown(
                                label="Move To",
                                choices=FOCUS_STATE_CHOICES,
                            )

                            with gr.Row(elem_classes="jos-action-row"):
                                focus_move_button = gr.Button("Move Item", variant="primary")
                                focus_refresh_button = gr.Button("Refresh", variant="secondary")

                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Move Status</h3>")
                                focus_status_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>No changes yet.</div>",
                                    elem_classes="jos-output compact",
                                )

                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Focus Board</h3>")
                                focus_board_output = gr.Markdown(
                                    value=render_focus_markdown(),
                                    elem_classes="jos-output",
                                )

                        focus_move_button.click(
                            fn=ui_move_item,
                            inputs=[focus_item_dropdown, focus_target_dropdown],
                            outputs=[focus_status_output, focus_board_output, focus_item_dropdown],
                        )

                        focus_refresh_button.click(
                            fn=ui_refresh_focus,
                            inputs=[],
                            outputs=[focus_item_dropdown, focus_board_output],
                        )

            with gr.Tab("Agent Workflow"):
                gr.HTML(
                    """
                    <div class="jos-section-intro">
                      <p>Use the original agent loop to generate plans, evaluate execution, review progress, and optimize priorities.</p>
                    </div>
                    """
                )
                with gr.Tabs(elem_classes="jos-sub-tabs"):
                    with gr.Tab("Planner"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Planner Screen</h2>")
                            gr.HTML(
                                """
                                <div class="jos-info">
                                  <h3>Planner Agent</h3>
                                  <p>Creates structured daily plans from goals, weights, user request, and recent context.</p>
                                </div>
                                """
                            )
                            with gr.Group(elem_classes="jos-request-block"):
                                planner_input = gr.Textbox(
                                    label="Plan Request",
                                    lines=5,
                                    placeholder="Example: I have 4 hours today. Priorities: study, project work, and training. Energy: 8/10.",
                                )
                            with gr.Row(elem_classes="jos-action-row"):
                                planner_button = gr.Button("Generate Plan", variant="primary")
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Generated Plan</h3>")
                                planner_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>No plan generated yet. Submit a request above to generate a structured plan.</div>",
                                    elem_classes="jos-output",
                                )

                        planner_button.click(
                            fn=run_planner,
                            inputs=planner_input,
                            outputs=planner_output,
                        )

                    with gr.Tab("Evaluator"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Evaluator Screen</h2>")
                            gr.HTML(
                                """
                                <div class="jos-info">
                                  <h3>Evaluator Agent</h3>
                                  <p>Compares the execution log against the latest saved plan and calculates a Python weighted score.</p>
                                </div>
                                """
                            )
                            evaluator_input = gr.Textbox(
                                label="Daily Log",
                                lines=7,
                                placeholder="Example: Completed a study block, fixed one project issue, and skipped training due to time constraints.",
                            )
                            evaluator_button = gr.Button("Evaluate Day", variant="primary")
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Daily Evaluation</h3>")
                                evaluator_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>No evaluation generated yet. Submit a daily log above to generate a review.</div>",
                                    elem_classes="jos-output",
                                )

                        evaluator_button.click(
                            fn=run_evaluator,
                            inputs=evaluator_input,
                            outputs=evaluator_output,
                        )

                    with gr.Tab("Dashboard"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Dashboard</h2>")
                            gr.HTML(
                                """
                                <div class="jos-info">
                                  <h3>Dashboard</h3>
                                  <p>Shows the latest saved state from SQLite: goals, weights, plans, evaluations, and optimizer reports.</p>
                                </div>
                                """
                            )
                            refresh_button = gr.Button("Refresh Dashboard", variant="primary")
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Saved State</h3>")
                                dashboard_output = gr.Markdown(value=dashboard(), elem_classes="jos-output")

                        refresh_button.click(
                            fn=dashboard,
                            inputs=[],
                            outputs=dashboard_output,
                        )

                    with gr.Tab("Optimizer"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Optimizer Screen</h2>")
                            gr.HTML(
                                """
                                <div class="jos-info">
                                  <h3>Optimizer Agent</h3>
                                  <p>Reviews recent progress and recommends small changes. Weight updates require human approval.</p>
                                </div>
                                """
                            )
                            optimizer_button = gr.Button("Generate Optimizer Report", variant="primary")
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Optimizer Report</h3>")
                                optimizer_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>No optimizer report generated yet.</div>",
                                    elem_classes="jos-output",
                                )
                            apply_weights_button = gr.Button("Apply", variant="primary")
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Weight Application Result</h3>")
                                apply_weights_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>No weight recommendation applied yet.</div>",
                                    elem_classes="jos-output compact",
                                )

                        optimizer_button.click(
                            fn=run_optimizer,
                            inputs=[],
                            outputs=optimizer_output,
                        )

                        apply_weights_button.click(
                            fn=run_apply_latest_weights,
                            inputs=[],
                            outputs=apply_weights_output,
                        )

                    with gr.Tab("Weekly Review"):
                        with gr.Group(elem_classes="jos-panel"):
                            gr.HTML("<h2 class='jos-screen-title'>Weekly Review Screen</h2>")
                            gr.HTML(
                                """
                                <div class="jos-info">
                                  <h3>Weekly Review Agent</h3>
                                  <p>Detects patterns across recent logs and evaluations, including bottlenecks and momentum.</p>
                                </div>
                                """
                            )
                            weekly_button = gr.Button("Generate Weekly Review", variant="primary")
                            with gr.Group(elem_classes="jos-output-card"):
                                gr.HTML("<h3>Weekly Review</h3>")
                                weekly_output = gr.Markdown(
                                    value="<div class='jos-placeholder'>No weekly review generated yet.</div>",
                                    elem_classes="jos-output",
                                )

                        weekly_button.click(
                            fn=run_weekly_review,
                            inputs=[],
                            outputs=weekly_output,
                        )

if __name__ == "__main__":
    app.launch(inbrowser=True, theme=theme, css=APP_CSS)