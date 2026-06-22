import asyncio
from datetime import date
from scoring import calculate_weighted_overall, update_markdown_overall_score

import gradio as gr

#from notes import summary
from os_agents import plan_day, evaluate_day, evaluate_week, optimize_goals
from database import (
    get_goals,
    get_domain_weights,
    get_recent_logs,
    get_recent_evaluations,
    get_recent_plans,
    save_evaluation,
    export_latest_evaluation_to_md,
    save_plan,
    export_latest_plan_to_md,
    get_latest_evaluation,
    save_optimization,
    export_latest_optimization_to_md,
    get_latest_optimization,
    create_tables,
    apply_latest_optimization_weights,
)

create_tables()

def run_planner(request):
    if not request.strip():
        return "Unesi šta želiš da planiraš."

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
        return "Unesi dnevni log."

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
    recent_logs = get_recent_logs(limit=7)
    recent_evaluations = get_recent_evaluations(limit=7)
    recent_plans = get_recent_plans(limit=7)

    if not recent_evaluations and not recent_logs:
        return "Nema dovoljno podataka za weekly review."

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
    recent_logs = get_recent_logs(limit=14)
    recent_evaluations = get_recent_evaluations(limit=10)

    if not recent_evaluations:
        return "Nema dovoljno evaluacija za optimizer. Uradi bar jednu dnevnu ili weekly evaluaciju."

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

    latest_plan_md = plans[0][2] if plans else "_Još nema sačuvanog plana._"

    if latest_eval:
        period_type, period_label, score, feedback, next_actions, created_at = latest_eval
        latest_score = f"{score}/10"
        latest_eval_preview = feedback[:2500]
    else:
        latest_score = "Nema još evaluacije"
        latest_eval_preview = "_Još nema evaluacije._"
        created_at = "-"

    if latest_optimization:
        optimization_md = latest_optimization[2]
    else:
        optimization_md = "_Još nema optimizer report-a._"

    weights_md = "\n".join(
        [f"- **{domain}**: {weight}%" for domain, weight in weights]
    ) or "_Nema definisanih težina._"

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
            f"- **{goal[2]}** ({goal[1]}, priority: {goal[5]})"
            for goal in unique_goals
        ]
    ) or "_Nema aktivnih ciljeva._"

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

with gr.Blocks(title="Jovan OS Lite") as app:
    gr.Markdown("# Jovan OS Lite")
    gr.Markdown("Planner + Evaluator + Dashboard")

    with gr.Tab("Planner"):
        planner_input = gr.Textbox(
            label="Plan Request",
            lines=6,
            placeholder="Danas imam 4 sata, energija 8/10, prioritet ETF i Jovan OS..."
        )
        planner_button = gr.Button("Generate Plan")
        planner_output = gr.Markdown()

        planner_button.click(
            fn=run_planner,
            inputs=planner_input,
            outputs=planner_output,
        )

    with gr.Tab("Evaluator"):
        evaluator_input = gr.Textbox(
            label="Daily Log",
            lines=8,
            placeholder="Formalno: 90 min DOS2\nNeformalno: 60 min Jovan OS\nSport: trening\nKarijera: ništa\nSan: 7h\nEnergija: 8/10"
        )
        evaluator_button = gr.Button("Evaluate Day")
        evaluator_output = gr.Markdown()

        evaluator_button.click(
            fn=run_evaluator,
            inputs=evaluator_input,
            outputs=evaluator_output,
            
        )

    with gr.Tab("Dashboard"):
        refresh_button = gr.Button("Refresh Dashboard")
        dashboard_output = gr.Markdown(value=dashboard())

        refresh_button.click(
        fn=dashboard,
        inputs=[],
        outputs=dashboard_output,
    )

    with gr.Tab("Optimizer"):
        gr.Markdown("## Optimizer")
        gr.Markdown(
            "Analizira ciljeve, težine domena, skorove i bottleneck-e. "
            "Prvo generiše preporuke, a zatim možeš ručno da primeniš samo preporuke za težine."
        )
        
        optimizer_button = gr.Button("Generate Optimizer Report")
        optimizer_output = gr.Markdown()

        apply_weights_button = gr.Button("Apply Latest Weight Recommendations")
        apply_weights_output = gr.Markdown()

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
        weekly_button = gr.Button("Generate Weekly Review")
        weekly_output = gr.Markdown()

        weekly_button.click(
            fn=run_weekly_review,
            inputs=[],
            outputs=weekly_output,
    )


if __name__ == "__main__":
    app.launch(inbrowser=True)