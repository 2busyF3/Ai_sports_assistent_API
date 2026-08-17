export type Profile = { height_cm: number; body_weight_kg: number; weight_updated_at: string };
export type Workout = { id: number; performed_at: string; exercises: string; total_volume_kg: number; sleep_hours?: number; duration_minutes?: number };
export type TrendPoint = { performed_at: string; best_set_score: number; total_volume_kg: number };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || "Request failed");
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => request<{ profile: Profile | null; latest_sleep_hours: number | null; message: string; suggestions: { name: string; suggested_weight_kg: number; target_reps: number }[] }>("/api/dashboard"),
  profile: () => request<{ profile: Profile | null }>("/api/profile"),
  saveProfile: (height_cm: number, body_weight_kg: number) => request<{ profile: Profile }>("/api/profile", { method: "PUT", body: JSON.stringify({ height_cm, body_weight_kg }) }),
  logSleep: (hours: number) => request("/api/sleep", { method: "POST", body: JSON.stringify({ hours }) }),
  analyze: (text: string) => request<{ response: string }>("/api/workouts/analyze", { method: "POST", body: JSON.stringify({ text }) }),
  workouts: () => request<{ workouts: Workout[] }>("/api/history/workouts"),
  exercises: () => request<{ exercises: string[] }>("/api/history/exercises"),
  trend: (name: string) => request<{ points: TrendPoint[] }>(`/api/history/exercises/${encodeURIComponent(name)}/trend`),
  calendar: (year: number, month: number) => request<{ workout_days: number[] }>(`/api/history/calendar?year=${year}&month=${month}`),
  details: (id: number) => request<{ sets: { name: string; weight_kg: number; reps: number }[] }>(`/api/history/workouts/${id}`),
  clearDemo: () => request("/api/demo/clear", { method: "POST" }),
};
