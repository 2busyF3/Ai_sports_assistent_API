# Function reference

This document is the developer-facing map of the project. Every new public
function must have a short docstring in code and an entry here when it changes
the application behaviour. Private helpers are marked with an underscore.

## Analytics

| Function | What it does | Input → output |
|---|---|---|
| `analytics.volume.exercise_volume` | Calculates the total lifted load for one exercise. | exercise sets → `sum(weight × reps)` in kg |
| `analytics.volume.format_sets` | Creates a compact readable representation of sets. | exercise → text such as `100x8, 100x6` |
| `analytics.progression.volume_change_percent` | Compares current exercise volume with the most recent occurrence. | current + previous snapshot → percent change or `None` |
| `analytics.fatigue.recovery_risks` | Creates recovery warnings from sleep duration in the chosen language. | sleep hours + locale → list of warnings |
| `analytics.strength.estimated_one_rep_max` | Estimates a one-repetition maximum with the Epley formula. Repetitions are capped at 15 to avoid overrating high-rep sets. | weight + reps → estimated kg |
| `analytics.strength.strength_rating` | Converts the best estimated 1RM into a rounded 0–100 relative-strength rating. It uses body weight and an exercise reference ratio. | exercise + sets + body weight → rating or `None` |

## LLM layer

| Function | What it does | Notes |
|---|---|---|
| `llm.extractor.detect_language` | Detects Russian when Cyrillic text is present; otherwise uses English. | Controls the language of the response. |
| `llm.extractor.extract_locally` | Parses standard workout notation without internet access. | Fallback used when there is no API key. |
| `llm.extractor.extract_workout` | Selects OpenAI Structured Outputs or the local parser. | With an API key, it extracts exercises, sets, sleep and session metrics from free text. |
| `llm.extractor._number` | Converts a number written with either a comma or decimal point into a Python float. | Private parsing helper. |
| `llm.extractor._repeat_count` | Detects shorthand such as `60x12 x3`. | Private parsing helper. |
| `llm.coach.generate_coach_advice` | Calls the configured OpenAI model to interpret verified metrics and return a structured coaching plan. | Returns `None` if no key is present or the request fails, so the app can fall back safely. |

`CoachAdvice` is the LLM response schema. It requires: a session headline,
assessment, per-exercise next-session plans, recovery advice, and no more than
two follow-up questions. `NextExercisePlan` requires a prescription and a
data-based rationale.

## LangGraph workflow

| Node/function | What it does |
|---|---|
| `graph.graph.build_graph` | Builds the workflow: extract → history → analytics → analysis and risks → LLM coach → response. |
| `graph.nodes.extract_node` | Turns raw user text into `WorkoutInput` and detects the response language. |
| `graph.nodes.history_node` | Reads the latest sleep and exercise history before saving the new workout. It also loads the profile goal and body weight. |
| `graph.nodes.analytics_node` | Calculates volume change for every exercise. |
| `graph.nodes.risks_node` | Adds recovery warnings from sleep, excessive session duration and peak heart rate. |
| `graph.nodes.analysis_node` | Produces the deterministic baseline decision used as evidence for the coach and as an offline fallback. |
| `graph.nodes.coach_node` | Builds a compact evidence packet and sends it to `generate_coach_advice`. This is the AI recommendation node. |
| `graph.nodes.response_node` | Renders the LLM plan when available; otherwise renders the clearly labelled local fallback. |
| `graph.nodes._format_coach_advice` | Formats the structured LLM answer for Russian or English display. |

## Data repositories

`SQLiteRepository` and `PostgresRepository` implement the same operations.
Their methods have identical intent so the graph can work locally or in Docker.

| Repository method | What it does |
|---|---|
| `_initialize` | Creates tables and applies safe additive schema migrations. |
| `_connect` | Opens a database connection; SQLite also enables foreign keys. |
| `_ensure_column` | SQLite-only migration helper that adds a missing column. |
| `save_workout` | Stores a workout, its exercises and ordered sets; returns the workout ID. |
| `latest_exercise` | Reads the most recent historical occurrence of an exercise. |
| `get_profile` / `save_profile` | Reads or stores height, body weight, update date and training goal. |
| `weight_update_due` | Checks whether seven days passed since the last body-weight update. |
| `save_sleep` / `latest_sleep_hours` | Stores sleep separately and retrieves the newest relevant value. |
| `has_workouts` | Reports whether at least one workout exists. |
| `clear_demo_data` | Removes only data marked as demo data. |
| `exercise_names` | Returns distinct exercise names for the chart selector. |
| `exercise_trend` | Returns chart points including volume, best set and rating inputs. |
| `recent_workouts` | Returns recent workout summaries for History. |
| `workouts_in_month` / `workouts_on_date` | Supply the calendar markers and date-specific sessions. |
| `workout_details` | Returns ordered sets for a chosen workout. |
| `latest_workout_exercises` | Supplies the Home-page suggestions from the last workout. |
| `database.factory.create_repository` | Selects PostgreSQL for a PostgreSQL URL, otherwise SQLite. |
| `database.demo.seed_demo_data` | Inserts the first-run visual demo only into an empty database. |
| `database.demo._exercise` | Private helper that builds one demo exercise from `(weight, reps)` pairs. |

## FastAPI endpoints

| Function / endpoint | What it does |
|---|---|
| `repository` | Gets the shared repository from FastAPI application state. |
| `lifespan` | Creates the repository, optionally seeds demo data and compiles LangGraph on application startup. |
| `health` — `GET /health` | Checks database connectivity. |
| `analyze_workout` — `POST /api/workouts/analyze` | Runs the full LangGraph workflow and saves the workout. |
| `get_profile` / `update_profile` — `GET` / `PUT /api/profile` | Reads or saves profile data and the training goal. |
| `log_sleep` — `POST /api/sleep` | Saves a sleep entry. |
| `dashboard` — `GET /api/dashboard` | Returns summary metrics and last-workout suggestions for Home. |
| `workout_history` — `GET /api/history/workouts` | Returns paginated workout summaries. |
| `exercise_names` — `GET /api/history/exercises` | Returns exercises available in the graph selector. |
| `exercise_trend` — `GET /api/history/exercises/{name}/trend` | Adds the 0–100 relative-strength rating to each trend point. |
| `calendar_data` — `GET /api/history/calendar` | Returns days with logged workouts for a given month. |
| `workout_details` — `GET /api/history/workouts/{id}` | Returns a session's sets. |
| `clear_demo` — `POST /api/demo/clear` | Deletes only demo records. |

## Frontend functions

| Function | What it does |
|---|---|
| `TrendChart` | Draws the 0–100 chart, grid labels, point labels and linear trend line. |
| `Calendar` | Draws the monthly calendar, marks training days and opens a selected workout. |
| `App` | Owns page state, loads API data, submits forms and renders all tabs. |
| `api.request` | Shared HTTP helper: sends JSON and turns API errors into JavaScript errors. |
| `api.dashboard`, `profile`, `saveProfile`, `logSleep`, `analyze`, `workouts`, `exercises`, `trend`, `calendar`, `details`, `clearDemo` | Small typed wrappers around the corresponding REST endpoints. |

## Local desktop and CLI functions

| Function | What it does |
|---|---|
| `main._required_number` | Repeats terminal input until the user enters a valid positive number. |
| `main.collect_workout_note` | Reads a multi-line terminal workout note until `END`. |
| `main.initialize_or_update_profile` | Creates the first profile and requests body weight again only when due. |
| `main.main` | CLI entry point. |
| `app.main` | Desktop Tkinter application entry point. |
