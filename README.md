# Jovan OS Lite

Jovan OS Lite is a local personal agentic operating system for planning, evaluating, reviewing, and optimizing progress across multiple domains.

The project was built as a practical exercise in agentic AI engineering, focusing on agents, structured outputs, persistent state, evaluator loops, and human-approved optimization.

It is not designed as a generic chatbot. Instead, it is a small working system that stores context, generates plans, evaluates execution, reviews progress, and recommends small adjustments over time.

---

## Core Loop

Jovan OS Lite follows this loop:

```text
Plan → Execute → Evaluate → Save → Dashboard → Weekly Review → Optimize → Human Approval
```

The goal is to turn vague effort into measurable progress.

---

## Main Concept

The system helps a user manage several life or work domains, such as:

* formal education
* project building
* health and training
* career visibility

Each domain can have:

* active goals
* priority weights
* daily plans
* execution logs
* evaluations
* optimization recommendations

The system keeps persistent state locally and uses agents to reason over recent progress.

---

## Agents

### Planner Agent

Creates a daily plan based on:

* user input
* active goals
* domain weights
* current context

The planner separates required tasks from recommended tasks, so explicit user priorities remain more important than generic weight balancing.

---

### Evaluator Agent

Compares the user's execution log against the latest saved plan.

It identifies:

* completed items
* missed items
* unknown items
* plan completion score
* domain scores
* bottlenecks
* next actions

The evaluator distinguishes between missed tasks and tasks that were simply not mentioned. This prevents unknown items from being treated as automatic failures.

---

### Weekly Review Agent

Analyzes recent logs and evaluations to detect patterns across multiple days.

It focuses on:

* repeated bottlenecks
* strongest momentum
* weak areas
* recurring missed actions
* lack of closure
* useful next actions

Daily evaluation focuses on execution. Weekly review focuses on patterns.

---

### Optimizer Agent

Analyzes:

* active goals
* current domain weights
* recent logs
* recent evaluations
* repeated bottlenecks
* strong momentum
* weak domains

It recommends:

* goal adjustments
* domain weight changes
* weekly operating rules
* concrete targets for the next cycle

The optimizer does not automatically apply changes.

---

## Human Approval Layer

Jovan OS Lite includes a human-in-the-loop optimization layer.

The optimizer can recommend changes, but the user must approve them manually before they are applied.

Currently, only domain weight recommendations can be applied through the UI. Goal recommendations remain review-only.

```text
Optimizer recommendation → User review → Manual approval → Database update
```

This prevents the system from silently changing priorities.

---

## Tech Stack

* Python
* OpenAI Agents SDK
* Pydantic structured outputs
* SQLite
* Gradio
* Markdown reports
* Deterministic Python scoring logic

---

## Project Structure

```text
jovan_os_lite/
│
├── app.py
├── database.py
├── schemas.py
├── prompts.py
├── os_agents.py
├── scoring.py
├── seed_demo.py
│
├── data/
│   └── jovan_os.db
│
└── reports/
    ├── latest_plan.md
    ├── latest_evaluation.md
    └── latest_optimization.md
```

---

## Main Features

* Daily planning
* Daily execution evaluation
* Weekly review
* Dashboard
* Optimizer report
* Persistent SQLite state
* Markdown report export
* Pydantic structured outputs
* Python weighted scoring
* Human-approved weight updates

---

## Demo Setup

This repository does not include a real local database, private reports, or API keys.

To create a local demo database with synthetic goals, run:

```bash
uv run seed_demo.py
```

Then start the app:

```bash
uv run app.py
```

The demo data uses generic goal titles while keeping the current internal domain identifiers:

* `formalno_obrazovanje` → formal education / coursework
* `neformalno_obrazovanje` → project building / skill development
* `sport` → health and training
* `karijera` → career visibility

No private user data is included in the repository.

---

## Example Demo Goals

The demo seed creates public-safe example goals:

```text
Complete university coursework
Build AI portfolio projects
Maintain fitness routine
Improve career visibility
```

Example domain weights:

```text
formalno_obrazovanje: 30%
neformalno_obrazovanje: 30%
sport: 20%
karijera: 20%
```

These are only synthetic demo values.

---

## Scoring

The evaluator agent produces domain scores and a plan completion score.

Python then calculates the final score deterministically.

Example formula:

```text
final_score = 0.8 * weighted_domain_score + 0.2 * plan_completion_score
```

This keeps the LLM responsible for interpretation, while Python handles deterministic scoring.

---

## Reports

The system exports the latest generated reports as markdown files:

```text
reports/latest_plan.md
reports/latest_evaluation.md
reports/latest_optimization.md
```

These reports make the system easier to inspect, debug, and demonstrate.

The `reports/` folder is ignored by Git because reports may contain private local data.

---

## Demo Flow

A typical demo flow:

1. Seed demo data.
2. Start the local Gradio app.
3. Generate a daily plan.
4. Enter a daily execution log.
5. Run the evaluator.
6. Check the dashboard.
7. Generate a weekly review.
8. Generate an optimizer report.
9. Apply latest weight recommendations manually.
10. Confirm that the dashboard updates.

Example synthetic plan request:

```text
Study, project work, and training.
```

Example synthetic execution log:

```text
Completed a 90-minute study block. Fixed one project bug and updated the README. Skipped training due to time constraints.
```

Example system behavior:

```text
- Study marked as completed
- Project work marked as completed
- Training marked as explicitly missed
- Domain scores generated
- Final score calculated
- Next actions recommended
```

---

## Privacy Note

This repository should not include private user data.

The following files and folders should stay local and should not be committed:

```text
.env
data/
reports/
README_PRIVATE.md
notes.txt
notes.ipynb
```

A public demo should use synthetic goals, logs, and reports instead of personal data.

---

## Example `.gitignore`

```gitignore
# Secrets
.env

# Local database and generated reports
data/
reports/
*.db

# Private notes / private README
README_PRIVATE.md
notes.txt
notes.ipynb

# Python
__pycache__/
*.pyc
.pytest_cache/

# Virtual environments
.venv/
venv/

# Jupyter
.ipynb_checkpoints/

# OS/editor
.DS_Store
.vscode/
```

---

## Why This Project Matters

This project demonstrates practical agentic AI patterns in a real working application:

* multiple agents with different responsibilities
* structured outputs
* persistent local state
* evaluator loop
* optimizer loop
* human approval layer
* deterministic scoring outside the LLM
* product-oriented agent design

The goal was not to build another chatbot, but to build a small system that can plan, evaluate, learn from history, and recommend improvements.

---

## Agentic AI Concepts Used

* Planner/evaluator pattern
* Structured outputs
* Tool/function-based architecture
* Stateful system design
* Agent loop
* Human-in-the-loop approval
* Optimization loop
* Markdown report generation
* SQLite-based local memory

---

## Current MVP Status

Jovan OS Lite is currently feature-complete as a local MVP.

Completed:

* Planner Agent
* Evaluator Agent
* Weekly Review Agent
* Optimizer Agent
* SQLite persistence
* Gradio UI
* Dashboard
* Markdown exports
* Python weighted scoring
* Human-approved weight updates
* Public-safe demo seed

---

## Future Improvements

Potential future improvements:

* duplicate goal cleanup
* charts and trends
* calendar integration
* GitHub integration
* Notion integration
* multi-user support
* generalized Personal OS version
* improved goal recommendation workflow
* hosted demo with synthetic data

These are intentionally left out of the Lite version to avoid feature creep.

---

## Future Direction

The same architecture could be adapted to other planning and optimization problems, such as:

* project planning
* study planning
* personal productivity systems
* team capacity planning
* workforce scheduling

The reusable pattern is:

```text
Plan → Execute → Evaluate → Optimize
```

Jovan OS Lite is the personal MVP version of that broader architecture.

---

## Status

This project is a local MVP and portfolio demonstration of an agentic AI system.

Current focus:

```text
polish → demo → repository cleanup → public portfolio version
```
