from __future__ import annotations

import tkinter as tk
import calendar
from datetime import datetime
from tkinter import messagebox, ttk

from database.sqlite import SQLiteRepository
from database.demo import seed_demo_data
from graph.graph import build_graph
from models import SleepEntry


BACKGROUND = "#F7F8FA"
SURFACE = "#FFFFFF"
INK = "#172033"
MUTED = "#64748B"
ACCENT = "#2563EB"
GRID = "#E2E8F0"


class FitnessAssistantApp(tk.Tk):
    def __init__(self, database_path: str = "fitness.db") -> None:
        super().__init__()
        self.repository = SQLiteRepository(database_path)
        self.demo_loaded = seed_demo_data(self.repository)
        self.graph = build_graph(self.repository)
        self.title("AI Fitness Assistant")
        self.geometry("1120x760")
        self.minsize(880, 620)
        self.configure(bg=BACKGROUND)
        self._configure_style()

        header = tk.Frame(self, bg=BACKGROUND, padx=28, pady=20)
        header.pack(fill="x")
        tk.Label(header, text="AI Fitness Assistant", font=("Segoe UI", 20, "bold"), bg=BACKGROUND, fg=INK).pack(anchor="w")
        tk.Label(header, text="Log training. Track progress. Make informed next-session decisions.",
                 font=("Segoe UI", 10), bg=BACKGROUND, fg=MUTED).pack(anchor="w", pady=(4, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self.home_tab = ttk.Frame(self.notebook, padding=20)
        self.workout_tab = ttk.Frame(self.notebook, padding=20)
        self.sleep_tab = ttk.Frame(self.notebook, padding=20)
        self.history_tab = ttk.Frame(self.notebook, padding=20)
        self.settings_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.home_tab, text="Home")
        self.notebook.add(self.workout_tab, text="Workout")
        self.notebook.add(self.sleep_tab, text="Sleep")
        self.notebook.add(self.history_tab, text="History")
        self.notebook.add(self.settings_tab, text="Settings")

        self._build_home_tab()
        self._build_workout_tab()
        self._build_sleep_tab()
        self._build_history_tab()
        self._build_settings_tab()
        self.refresh_history()
        self.refresh_dashboard()
        self.after(200, self._prompt_initial_profile)
        if self.demo_loaded:
            self.after(400, lambda: messagebox.showinfo(
                "Demo data loaded", "Sample workouts were added so you can explore Home, History, and the calendar. Use Clear demo data when you are ready to start."
            ))

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("TNotebook.Tab", background=BACKGROUND, foreground=MUTED, padding=(16, 10), font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", SURFACE)], foreground=[("selected", INK)])
        style.configure("TFrame", background=SURFACE)
        style.configure("TLabel", background=SURFACE, foreground=INK, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        style.configure("Accent.TButton", background=ACCENT, foreground="white")
        style.map("Accent.TButton", background=[("active", "#1D4ED8")])
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 9), background=SURFACE, fieldbackground=SURFACE)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#F1F5F9", foreground=INK)

    def _build_home_tab(self) -> None:
        self.home_tab.columnconfigure((0, 1, 2), weight=1, uniform="home")
        self.home_tab.rowconfigure(2, weight=1)
        tk.Label(self.home_tab, text="Today at a glance", font=("Segoe UI", 14, "bold"), bg=SURFACE, fg=INK).grid(
            row=0, column=0, columnspan=3, sticky="w")
        self.height_stat = self._stat_card("HEIGHT", "—")
        self.weight_stat = self._stat_card("BODY WEIGHT", "—")
        self.sleep_stat = self._stat_card("LATEST SLEEP", "—")
        self.height_stat.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(16, 20))
        self.weight_stat.grid(row=1, column=1, sticky="ew", padx=8, pady=(16, 20))
        self.sleep_stat.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(16, 20))
        advice = tk.Frame(self.home_tab, bg="#EFF6FF", padx=20, pady=18)
        advice.grid(row=2, column=0, columnspan=3, sticky="nsew")
        advice.columnconfigure(0, weight=1)
        tk.Label(advice, text="Today’s recommendation", font=("Segoe UI", 12, "bold"), bg="#EFF6FF", fg=INK).grid(
            row=0, column=0, sticky="w")
        self.daily_advice = tk.Label(advice, text="", justify="left", anchor="nw", wraplength=900,
                                     font=("Segoe UI", 10), bg="#EFF6FF", fg=INK)
        self.daily_advice.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        ttk.Button(self.home_tab, text="Refresh overview", command=self.refresh_dashboard).grid(
            row=3, column=0, sticky="w", pady=(16, 0))
        ttk.Button(self.home_tab, text="Clear demo data", command=self.clear_demo_data).grid(
            row=3, column=1, sticky="w", pady=(16, 0))

    def _stat_card(self, label: str, value: str) -> tk.Frame:
        card = tk.Frame(self.home_tab, bg="#F8FAFC", padx=16, pady=14, highlightthickness=1, highlightbackground=GRID)
        tk.Label(card, text=label, font=("Segoe UI", 8, "bold"), bg="#F8FAFC", fg=MUTED).pack(anchor="w")
        value_label = tk.Label(card, text=value, font=("Segoe UI", 20, "bold"), bg="#F8FAFC", fg=INK)
        value_label.pack(anchor="w", pady=(4, 0))
        card.value_label = value_label
        return card

    def _build_workout_tab(self) -> None:
        self.workout_tab.columnconfigure(0, weight=1)
        self.workout_tab.rowconfigure(2, weight=1)
        tk.Label(self.workout_tab, text="Workout conversation", font=("Segoe UI", 14, "bold"), bg=SURFACE, fg=INK).grid(
            row=0, column=0, sticky="w")
        tk.Label(self.workout_tab, text="Write your session naturally. Use one line per set when possible.",
                 bg=SURFACE, fg=MUTED).grid(row=1, column=0, sticky="w", pady=(4, 0))

        chat_frame = tk.Frame(self.workout_tab, bg="#EFF6FF", padx=16, pady=14)
        chat_frame.grid(row=2, column=0, sticky="nsew", pady=(14, 12))
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)
        self.response_box = tk.Text(chat_frame, height=15, wrap="word", bg="#EFF6FF", fg=INK, borderwidth=0,
                                    font=("Segoe UI", 10), state="disabled", padx=4, pady=4)
        self.response_box.grid(row=0, column=0, sticky="nsew")

        tk.Label(self.workout_tab, text="Your workout note", font=("Segoe UI", 10, "bold"), bg=SURFACE, fg=INK).grid(
            row=3, column=0, sticky="w")
        self.note_box = tk.Text(self.workout_tab, height=10, wrap="word", bg="#F8FAFC", fg=INK, relief="solid",
                                borderwidth=1, font=("Segoe UI", 10), padx=12, pady=10)
        self.note_box.grid(row=4, column=0, sticky="ew", pady=(8, 12))
        self.note_box.bind("<Control-v>", self._paste_workout_note)
        self.note_box.insert("1.0", "Bench press\n100x8\n100x8\n100x6")
        footer = tk.Frame(self.workout_tab, bg=SURFACE)
        footer.grid(row=5, column=0, sticky="ew")
        tk.Label(footer, text="The workout is saved after analysis.", bg=SURFACE, fg=MUTED).pack(side="left")
        ttk.Button(footer, text="Analyze and save", style="Accent.TButton", command=self.analyze_workout).pack(side="right")

    def _build_sleep_tab(self) -> None:
        self.sleep_tab.columnconfigure(0, weight=1)
        tk.Label(self.sleep_tab, text="Sleep log", font=("Segoe UI", 14, "bold"), bg=SURFACE, fg=INK).grid(
            row=0, column=0, sticky="w")
        tk.Label(self.sleep_tab, text="Log sleep when you wake up. The latest entry is used in your next workout analysis.",
                 bg=SURFACE, fg=MUTED).grid(row=1, column=0, sticky="w", pady=(5, 28))
        form = tk.Frame(self.sleep_tab, bg="#F8FAFC", padx=18, pady=18, highlightthickness=1, highlightbackground=GRID)
        form.grid(row=2, column=0, sticky="ew")
        tk.Label(form, text="Sleep duration (hours)", bg="#F8FAFC", fg=INK).pack(anchor="w")
        self.sleep_entry = ttk.Entry(form, width=20)
        self.sleep_entry.pack(anchor="w", pady=(8, 14))
        ttk.Button(form, text="Save sleep", style="Accent.TButton", command=self.save_sleep).pack(anchor="w")
        self.sleep_status = tk.Label(self.sleep_tab, text="", bg=SURFACE, fg=MUTED)
        self.sleep_status.grid(row=3, column=0, sticky="w", pady=(16, 0))
        self.refresh_sleep_status()

    def _build_history_tab(self) -> None:
        self.history_tab.columnconfigure(0, weight=1)
        self.history_tab.rowconfigure(2, weight=1)
        controls = tk.Frame(self.history_tab, bg=SURFACE)
        controls.grid(row=0, column=0, sticky="ew")
        tk.Label(controls, text="Progress history", font=("Segoe UI", 14, "bold"), bg=SURFACE, fg=INK).pack(side="left")
        tk.Label(controls, text="Exercise", bg=SURFACE, fg=MUTED).pack(side="left", padx=(28, 6))
        self.exercise_var = tk.StringVar()
        self.exercise_select = ttk.Combobox(controls, textvariable=self.exercise_var, state="readonly", width=28)
        self.exercise_select.pack(side="left")
        self.exercise_select.bind("<<ComboboxSelected>>", lambda _: self.draw_trend())
        ttk.Button(controls, text="View workout history", command=self.show_workout_history).pack(side="right")
        ttk.Button(controls, text="Open calendar", command=self.show_calendar).pack(side="right", padx=8)
        ttk.Button(controls, text="Refresh", command=self.refresh_history).pack(side="right", padx=8)

        self.chart_caption = tk.Label(self.history_tab, text="Select an exercise to see its trend.", bg=SURFACE, fg=MUTED)
        self.chart_caption.grid(row=1, column=0, sticky="w", pady=(12, 4))
        self.chart = tk.Canvas(self.history_tab, height=280, bg="#FFFFFF", highlightthickness=1, highlightbackground=GRID)
        self.chart.grid(row=2, column=0, sticky="nsew")
        self.chart.bind("<Configure>", lambda _: self.draw_trend())


    def _build_settings_tab(self) -> None:
        self.settings_tab.columnconfigure(1, weight=1)
        tk.Label(self.settings_tab, text="Profile and parameters", font=("Segoe UI", 14, "bold"), bg=SURFACE, fg=INK).grid(
            row=0, column=0, columnspan=2, sticky="w")
        tk.Label(self.settings_tab, text="Height is saved once. Update body weight whenever you want; weekly updates are enough.",
                 bg=SURFACE, fg=MUTED).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 24))
        tk.Label(self.settings_tab, text="Height (cm)", bg=SURFACE).grid(row=2, column=0, sticky="w", pady=7)
        self.height_entry = ttk.Entry(self.settings_tab, width=22)
        self.height_entry.grid(row=2, column=1, sticky="w", pady=7)
        tk.Label(self.settings_tab, text="Body weight (kg)", bg=SURFACE).grid(row=3, column=0, sticky="w", pady=7)
        self.weight_entry = ttk.Entry(self.settings_tab, width=22)
        self.weight_entry.grid(row=3, column=1, sticky="w", pady=7)
        self.profile_status = tk.Label(self.settings_tab, text="", bg=SURFACE, fg=MUTED)
        self.profile_status.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 12))
        ttk.Button(self.settings_tab, text="Save profile", style="Accent.TButton", command=self.save_profile).grid(
            row=5, column=0, sticky="w")
        self.load_profile()

    def _prompt_initial_profile(self) -> None:
        if self.repository.get_profile() is None:
            self.notebook.select(self.settings_tab)
            messagebox.showinfo("Profile setup", "Add height and current body weight before saving your first workout.")

    def load_profile(self) -> None:
        profile = self.repository.get_profile()
        self.height_entry.delete(0, "end")
        self.weight_entry.delete(0, "end")
        if profile is None:
            self.profile_status.config(text="Profile not set yet.")
            return
        self.height_entry.insert(0, f"{profile.height_cm:g}")
        self.weight_entry.insert(0, f"{profile.body_weight_kg:g}")
        self.profile_status.config(text=f"Last body-weight update: {profile.weight_updated_at:%d %b %Y}")

    def save_profile(self) -> None:
        try:
            height = float(self.height_entry.get().replace(",", "."))
            weight = float(self.weight_entry.get().replace(",", "."))
            if height <= 0 or weight <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid profile", "Enter positive numbers for height and body weight.")
            return
        self.repository.save_profile(height, weight)
        self.load_profile()
        self.refresh_dashboard()
        messagebox.showinfo("Profile saved", "Your profile was saved locally.")

    def refresh_sleep_status(self) -> None:
        latest = self.repository.latest_sleep_hours()
        self.sleep_status.config(
            text=f"Latest saved sleep: {latest:g} hours" if latest is not None else "No sleep logged yet."
        )

    def refresh_dashboard(self) -> None:
        profile = self.repository.get_profile()
        latest_sleep = self.repository.latest_sleep_hours()
        self.height_stat.value_label.config(text=f"{profile.height_cm:g} cm" if profile else "—")
        self.weight_stat.value_label.config(text=f"{profile.body_weight_kg:g} kg" if profile else "—")
        self.sleep_stat.value_label.config(text=f"{latest_sleep:g} h" if latest_sleep is not None else "—")
        exercises = self.repository.latest_workout_exercises()
        if latest_sleep is None:
            intro = "Log last night’s sleep to receive a recovery-aware recommendation."
            multiplier = 1.0
        elif latest_sleep < 7:
            intro = "Sleep was below target. Train a little lighter today and keep effort controlled."
            multiplier = 0.9
        else:
            intro = "Recovery looks acceptable. You can follow your normal planned training load today."
            multiplier = 1.0
        if exercises:
            suggestions = []
            for exercise in exercises:
                weight = float(exercise["max_weight_kg"]) * multiplier
                reps = int(exercise["max_reps"])
                suggestions.append(f"• {exercise['name']}: start around {weight:g} kg for up to {reps} reps")
            plan = "\nSuggested exercises based on your latest session:\n" + "\n".join(suggestions)
        else:
            plan = "\nLog a workout to receive exercise and working-weight suggestions here."
        self.daily_advice.config(text=intro + plan)

    def clear_demo_data(self) -> None:
        if not messagebox.askyesno("Clear demo data", "Remove only the sample data added for first launch? Your own saved workouts will remain."):
            return
        self.repository.clear_demo_data()
        self.load_profile()
        self.refresh_sleep_status()
        self.refresh_history()
        self.refresh_dashboard()
        messagebox.showinfo("Demo data cleared", "Sample data was removed. Add your profile and log your first workout.")
        self._prompt_initial_profile()

    def save_sleep(self) -> None:
        try:
            hours = float(self.sleep_entry.get().strip().replace(",", "."))
            if not 0 < hours <= 24:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid sleep entry", "Enter sleep duration from 0 to 24 hours.")
            return
        self.repository.save_sleep(SleepEntry(hours=hours))
        self.sleep_entry.delete(0, "end")
        self.refresh_sleep_status()
        self.refresh_dashboard()
        messagebox.showinfo("Sleep saved", "Sleep was saved and will be used in your next workout analysis.")

    def analyze_workout(self) -> None:
        if self.repository.get_profile() is None:
            messagebox.showwarning("Profile required", "Save your height and body weight in Settings before logging a workout.")
            self.notebook.select(self.settings_tab)
            return
        note = self.note_box.get("1.0", "end").strip()
        if not note:
            messagebox.showwarning("Workout note required", "Enter your workout before analyzing it.")
            return
        try:
            result = self.graph.invoke({"raw_text": note})
        except Exception as error:
            messagebox.showerror("Could not analyze workout", str(error))
            return
        self.response_box.config(state="normal")
        self.response_box.delete("1.0", "end")
        self.response_box.insert("1.0", result["response"])
        self.response_box.config(state="disabled")
        self.refresh_history()
        self.refresh_dashboard()

    def _paste_workout_note(self, event: tk.Event) -> str:
        """Keep Ctrl+V explicit and reliable on Windows Tkinter installations."""
        event.widget.event_generate("<<Paste>>")
        return "break"

    def refresh_history(self) -> None:
        names = self.repository.exercise_names()
        self.exercise_select["values"] = names
        if names and self.exercise_var.get() not in names:
            self.exercise_var.set(names[0])
        if not names:
            self.exercise_var.set("")
        self.draw_trend()

    def show_workout_history(self) -> None:
        window = tk.Toplevel(self)
        window.title("Workout history")
        window.geometry("940x500")
        window.configure(bg=BACKGROUND)
        tk.Label(window, text="Workout history", font=("Segoe UI", 14, "bold"), bg=BACKGROUND, fg=INK).pack(
            anchor="w", padx=20, pady=(18, 10))
        columns = ("date", "exercises", "volume", "sleep", "duration")
        table = ttk.Treeview(window, columns=columns, show="headings")
        for column, title, width in [
            ("date", "Date", 150), ("exercises", "Exercises", 380), ("volume", "Volume", 120),
            ("sleep", "Sleep", 90), ("duration", "Duration", 100),
        ]:
            table.heading(column, text=title)
            table.column(column, width=width, anchor="w")
        table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        for workout in self.repository.recent_workouts():
            performed_at = datetime.fromisoformat(str(workout["performed_at"]))
            sleep = f"{workout['sleep_hours']:g} h" if workout["sleep_hours"] is not None else "—"
            duration = f"{workout['duration_minutes']} min" if workout["duration_minutes"] else "—"
            table.insert("", "end", values=(
                performed_at.strftime("%d %b %Y, %H:%M"), workout["exercises"] or "—",
                f"{float(workout['total_volume_kg']):,.0f} kg", sleep, duration,
            ))

    def show_calendar(self) -> None:
        window = tk.Toplevel(self)
        window.title("Training calendar")
        window.geometry("640x520")
        window.configure(bg=BACKGROUND)
        current = datetime.now()
        state = {"year": current.year, "month": current.month}
        header = tk.Frame(window, bg=BACKGROUND, padx=20, pady=16)
        header.pack(fill="x")
        title = tk.Label(header, font=("Segoe UI", 14, "bold"), bg=BACKGROUND, fg=INK)
        title.pack(side="left", expand=True)
        grid = tk.Frame(window, bg=BACKGROUND, padx=20, pady=(0, 20))
        grid.pack(fill="both", expand=True)

        def render() -> None:
            for widget in grid.winfo_children():
                widget.destroy()
            year, month = state["year"], state["month"]
            title.config(text=f"{calendar.month_name[month]} {year}")
            workout_days = self.repository.workouts_in_month(year, month)
            for column, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                tk.Label(grid, text=day_name, font=("Segoe UI", 9, "bold"), bg=BACKGROUND, fg=MUTED).grid(
                    row=0, column=column, sticky="nsew", padx=3, pady=3)
                grid.columnconfigure(column, weight=1)
            for row, week in enumerate(calendar.monthcalendar(year, month), start=1):
                grid.rowconfigure(row, weight=1)
                for column, day in enumerate(week):
                    if not day:
                        tk.Label(grid, text="", bg=BACKGROUND).grid(row=row, column=column, sticky="nsew", padx=3, pady=3)
                        continue
                    trained = day in workout_days
                    button = tk.Button(
                        grid, text=str(day), relief="flat", font=("Segoe UI", 10, "bold" if trained else "normal"),
                        bg="#FEE2E2" if trained else SURFACE, fg="#B91C1C" if trained else INK,
                        activebackground="#FCA5A5" if trained else "#F1F5F9",
                        command=lambda selected_day=day: self.show_day_workouts(year, month, selected_day),
                    )
                    button.grid(row=row, column=column, sticky="nsew", padx=3, pady=3)

        def change_month(delta: int) -> None:
            month = state["month"] + delta
            year = state["year"]
            if month == 0:
                year, month = year - 1, 12
            elif month == 13:
                year, month = year + 1, 1
            state.update(year=year, month=month)
            render()

        ttk.Button(header, text="‹", width=3, command=lambda: change_month(-1)).pack(side="left")
        ttk.Button(header, text="›", width=3, command=lambda: change_month(1)).pack(side="right")
        render()

    def show_day_workouts(self, year: int, month: int, day: int) -> None:
        workouts = self.repository.workouts_on_date(year, month, day)
        if not workouts:
            messagebox.showinfo("No workout", "No workout was logged on this date.")
            return
        window = tk.Toplevel(self)
        window.title(f"Workout details · {day:02d}.{month:02d}.{year}")
        window.geometry("700x460")
        window.configure(bg=BACKGROUND)
        container = tk.Frame(window, bg=BACKGROUND, padx=20, pady=18)
        container.pack(fill="both", expand=True)
        for workout in workouts:
            performed_at = datetime.fromisoformat(str(workout["performed_at"]))
            tk.Label(container, text=f"{performed_at:%H:%M} · {float(workout['total_volume_kg']):,.0f} kg volume",
                     font=("Segoe UI", 11, "bold"), bg=BACKGROUND, fg=INK).pack(anchor="w", pady=(0, 6))
            by_exercise: dict[str, list[str]] = {}
            for item in self.repository.workout_details(int(workout["id"])):
                by_exercise.setdefault(str(item["name"]), []).append(f"{float(item['weight_kg']):g}x{item['reps']}")
            for name, sets in by_exercise.items():
                tk.Label(container, text=f"{name}: {', '.join(sets)}", bg=BACKGROUND, fg=INK,
                         font=("Segoe UI", 10), wraplength=640, justify="left").pack(anchor="w", pady=2)
            tk.Frame(container, height=1, bg=GRID).pack(fill="x", pady=12)

    def draw_trend(self) -> None:
        canvas = self.chart
        canvas.delete("all")
        name = self.exercise_var.get()
        if not name:
            self.chart_caption.config(text="No workout history yet. Analyze a workout to start tracking progress.")
            canvas.create_text(canvas.winfo_width() / 2, canvas.winfo_height() / 2, text="No data yet", fill=MUTED,
                               font=("Segoe UI", 11))
            return
        points = self.repository.exercise_trend(name)
        profile = self.repository.get_profile()
        body_weight = profile.body_weight_kg if profile else 1
        values = [point.best_set_score / body_weight for point in points]
        self.chart_caption.config(
            text=f"{name} · relative strength trend (best weight × reps / body weight) · {len(points)} sessions"
        )
        if not values:
            return
        width, height = max(canvas.winfo_width(), 400), max(canvas.winfo_height(), 220)
        left, right, top, bottom = 60, 26, 24, 42
        minimum, maximum = min(values), max(values)
        spread = maximum - minimum or max(maximum * 0.1, 1)
        minimum -= spread * 0.12
        maximum += spread * 0.12
        plot_width, plot_height = width - left - right, height - top - bottom
        for index in range(4):
            value = minimum + (maximum - minimum) * index / 3
            y = top + plot_height * (1 - index / 3)
            canvas.create_line(left, y, width - right, y, fill=GRID)
            canvas.create_text(left - 8, y, text=f"{value:.0f}", anchor="e", fill=MUTED, font=("Segoe UI", 8))
        coordinates: list[float] = []
        label_every = max(1, (len(points) + 5) // 6)
        for index, (point, value) in enumerate(zip(points, values)):
            x = left + (plot_width * index / max(len(points) - 1, 1))
            y = top + (maximum - value) / (maximum - minimum) * plot_height
            coordinates.extend([x, y])
            if index % label_every == 0 or index == len(points) - 1:
                label = point.performed_at.strftime("%d %b")
                canvas.create_text(x, height - bottom + 16, text=label, fill=MUTED, font=("Segoe UI", 8))
        if len(coordinates) > 2:
            canvas.create_line(*coordinates, fill=ACCENT, width=2)
        for x, y in zip(coordinates[::2], coordinates[1::2]):
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=ACCENT, outline="white", width=2)
        if len(values) >= 2:
            indexes = list(range(len(values)))
            mean_x = sum(indexes) / len(indexes)
            mean_y = sum(values) / len(values)
            denominator = sum((x - mean_x) ** 2 for x in indexes)
            slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(indexes, values)) / denominator
            intercept = mean_y - slope * mean_x
            trend_values = [intercept, intercept + slope * (len(values) - 1)]
            trend_coordinates = []
            for index, value in enumerate(trend_values):
                x = left + plot_width * index
                y = top + (maximum - value) / (maximum - minimum) * plot_height
                trend_coordinates.extend([x, y])
            canvas.create_line(*trend_coordinates, fill="#16A34A", width=2, dash=(5, 4))


def main() -> None:
    FitnessAssistantApp().mainloop()


if __name__ == "__main__":
    main()
