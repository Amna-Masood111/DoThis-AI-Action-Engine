"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import GoogleCalendarConnection from "../../../components/GoogleCalendarConnection";
import { apiFetch } from "../../../lib/api";
import { supabase } from "../../../lib/supabase";

type Reminder = {
  id: string;
  action_id: string;
  remind_at: string;
  status: string;
};

type Action = {
  id: string;
  action_number: number;
  title: string;
  type: string;
  deadline?: string | null;
  priority?: string;
  confidence?: number;
  status?: string;
  needs_confirmation?: boolean;
  reason?: string;
  depends_on?: number[];
  scheduled_start?: string | null;
  duration_minutes?: number | null;
  calendar_event_id?: string | null;
  calendar_event_link?: string | null;
  auto_scheduled?: boolean;
};

type Plan = {
  id: string;
  goal: string;
  summary?: string;
  original_text?: string;
  created_at?: string;
  required_items: string[];
  actions: Action[];
};

type ScheduleItem = {
  action_id: string;
  action_number: number;
  title: string;
  scheduled_start: string;
  duration_minutes: number;
  reminder_minutes_before: number;
  rationale: string;
};

function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Karachi";
  } catch {
    return "Asia/Karachi";
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatLocalSchedule(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.replace("T", " ");
  }
  return parsed.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function PlanPage() {
  const params = useParams();
  const router = useRouter();
  const planId = params.id as string;

  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [reminders, setReminders] = useState<Record<string, Reminder[]>>({});
  const [reminderInputs, setReminderInputs] = useState<Record<string, string>>({});
  const [savingReminder, setSavingReminder] = useState<Record<string, boolean>>({});

  const [calendarInputs, setCalendarInputs] = useState<Record<string, string>>({});
  const [calendarDuration, setCalendarDuration] = useState<Record<string, number>>({});
  const [calendarMessages, setCalendarMessages] = useState<Record<string, string>>({});
  const [calendarLinks, setCalendarLinks] = useState<Record<string, string>>({});
  const [addingCalendar, setAddingCalendar] = useState<Record<string, boolean>>({});

  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [scheduleNotes, setScheduleNotes] = useState<string[]>([]);
  const [generatingSchedule, setGeneratingSchedule] = useState(false);
  const [approvingSchedule, setApprovingSchedule] = useState(false);
  const [automationMessage, setAutomationMessage] = useState("");

  const timezone = useMemo(() => browserTimezone(), []);

  useEffect(() => {
    loadPlan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  async function getSession() {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      router.push("/login");
      return null;
    }
    return session;
  }

  async function loadPlan() {
    setLoading(true);
    setError("");
    try {
      const session = await getSession();
      if (!session) return;

      const response = await apiFetch(`/plans/${planId}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load plan.");

      setPlan(data);
      if (Array.isArray(data.actions)) {
        await Promise.all(data.actions.map((action: Action) => loadReminders(action.id, session.access_token)));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load plan.");
    } finally {
      setLoading(false);
    }
  }

  async function loadReminders(actionId: string, token?: string) {
    try {
      let accessToken = token;
      if (!accessToken) {
        const session = await getSession();
        if (!session) return;
        accessToken = session.access_token;
      }

      const response = await apiFetch(`/actions/${actionId}/reminders`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load reminders.");
      setReminders((current) => ({
        ...current,
        [actionId]: Array.isArray(data.reminders) ? data.reminders : [],
      }));
    } catch (err) {
      console.error(err);
    }
  }

  async function updateStatus(actionId: string, status: string) {
    try {
      const session = await getSession();
      if (!session) return;
      const response = await apiFetch(`/actions/${actionId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not update action.");
      await loadPlan();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not update action.");
    }
  }

  async function generateSmartSchedule() {
    setGeneratingSchedule(true);
    setAutomationMessage("");
    setSchedule([]);
    setScheduleNotes([]);
    try {
      const session = await getSession();
      if (!session) return;
      const response = await apiFetch(`/plans/${planId}/schedule-preview`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ timezone }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not build smart schedule.");
      setSchedule(Array.isArray(data.schedule) ? data.schedule : []);
      setScheduleNotes(Array.isArray(data.notes) ? data.notes : []);
      if (!data.schedule?.length) {
        setAutomationMessage("Everything in this plan is already completed or scheduled.");
      }
    } catch (err) {
      setAutomationMessage(err instanceof Error ? err.message : "Could not build smart schedule.");
    } finally {
      setGeneratingSchedule(false);
    }
  }

  async function approveSmartSchedule() {
    if (!schedule.length) return;
    setApprovingSchedule(true);
    setAutomationMessage("");
    try {
      const session = await getSession();
      if (!session) return;
      const response = await apiFetch(`/plans/${planId}/approve-schedule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ timezone, schedule }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not approve schedule.");

      setAutomationMessage(
        `${data.message} Calendar events and email reminders are now automated.`,
      );
      setSchedule([]);
      setScheduleNotes([]);
      await loadPlan();
    } catch (err) {
      setAutomationMessage(err instanceof Error ? err.message : "Could not approve schedule.");
    } finally {
      setApprovingSchedule(false);
    }
  }

  async function createReminderForAction(actionId: string) {
    const localDateTime = reminderInputs[actionId];
    if (!localDateTime) {
      alert("Please choose reminder date and time.");
      return;
    }
    try {
      setSavingReminder((current) => ({ ...current, [actionId]: true }));
      const session = await getSession();
      if (!session) return;
      const response = await apiFetch(`/actions/${actionId}/reminders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ remind_at: new Date(localDateTime).toISOString() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not create reminder.");
      setReminderInputs((current) => ({ ...current, [actionId]: "" }));
      await loadReminders(actionId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not create reminder.");
    } finally {
      setSavingReminder((current) => ({ ...current, [actionId]: false }));
    }
  }

  async function deleteReminderById(actionId: string, reminderId: string) {
    try {
      const session = await getSession();
      if (!session) return;
      const response = await apiFetch(`/reminders/${reminderId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 404 || data.detail === "Reminder not found.") {
          await loadReminders(actionId);
          return;
        }
        throw new Error(data.detail || "Could not delete reminder.");
      }
      await loadReminders(actionId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not delete reminder.");
    }
  }

  async function addToGoogleCalendar(actionId: string) {
    const start = calendarInputs[actionId];
    const duration = calendarDuration[actionId] || 60;
    if (!start) {
      setCalendarMessages((current) => ({
        ...current,
        [actionId]: "Please choose a start date and time.",
      }));
      return;
    }

    try {
      setAddingCalendar((current) => ({ ...current, [actionId]: true }));
      setCalendarMessages((current) => ({ ...current, [actionId]: "" }));
      const session = await getSession();
      if (!session) return;
      const response = await apiFetch(`/actions/${actionId}/calendar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          start_datetime: start,
          duration_minutes: duration,
          timezone,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not create calendar event.");
      setCalendarMessages((current) => ({ ...current, [actionId]: "Added to Google Calendar." }));
      if (data.event?.html_link) {
        setCalendarLinks((current) => ({ ...current, [actionId]: data.event.html_link }));
      }
    } catch (err) {
      setCalendarMessages((current) => ({
        ...current,
        [actionId]: err instanceof Error ? err.message : "Could not create calendar event.",
      }));
    } finally {
      setAddingCalendar((current) => ({ ...current, [actionId]: false }));
    }
  }

  if (loading) {
    return <main className="min-h-screen bg-slate-50 p-10 text-slate-600">Loading plan...</main>;
  }
  if (error) {
    return <main className="min-h-screen bg-slate-50 p-10 text-red-600">{error}</main>;
  }
  if (!plan) return null;

  const alreadyScheduled = plan.actions.filter((action) => action.auto_scheduled).length;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-6">
          <button
            onClick={() => router.push("/plans")}
            className="text-sm font-semibold text-slate-600 transition hover:text-slate-950"
          >
            ← My Plans
          </button>
          <button
            onClick={() => router.push("/")}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700"
          >
            New Plan
          </button>
        </div>
      </nav>

      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-6 sm:py-12">
        <GoogleCalendarConnection />

        <section className="mt-6 overflow-hidden rounded-3xl border border-indigo-200 bg-gradient-to-br from-indigo-600 via-indigo-600 to-violet-600 p-6 text-white shadow-lg shadow-indigo-100 sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-2xl">
              <div className="inline-flex rounded-full bg-white/15 px-3 py-1 text-xs font-bold uppercase tracking-wider">
                Smart Execution
              </div>
              <h2 className="mt-3 text-2xl font-bold sm:text-3xl">Let DoThis schedule the work for you.</h2>
              <p className="mt-3 leading-7 text-indigo-100">
                AI proposes practical times from your priorities, deadlines and dependencies. Review once, then approve to create every Google Calendar event and email reminder automatically.
              </p>
              <p className="mt-3 text-sm text-indigo-200">
                Your timezone: <span className="font-semibold text-white">{timezone}</span>
                {alreadyScheduled > 0 ? ` · ${alreadyScheduled} action(s) already automated` : ""}
              </p>
            </div>
            <button
              type="button"
              onClick={generateSmartSchedule}
              disabled={generatingSchedule}
              className="shrink-0 rounded-2xl bg-white px-5 py-3 text-sm font-bold text-indigo-700 shadow-sm transition hover:bg-indigo-50 disabled:opacity-60"
            >
              {generatingSchedule ? "Building schedule..." : schedule.length ? "Regenerate Schedule" : "Generate Smart Schedule"}
            </button>
          </div>
        </section>

        {schedule.length > 0 && (
          <section className="mt-5 rounded-3xl border border-indigo-100 bg-white p-5 shadow-sm sm:p-7">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-bold text-indigo-600">REVIEW BEFORE EXECUTION</p>
                <h3 className="mt-1 text-2xl font-bold">Your suggested schedule</h3>
                <p className="mt-2 text-sm text-slate-500">Nothing external happens until you approve.</p>
              </div>
              <button
                type="button"
                onClick={approveSmartSchedule}
                disabled={approvingSchedule}
                className="rounded-2xl bg-slate-950 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:bg-slate-400"
              >
                {approvingSchedule ? "Scheduling everything..." : "Approve & Schedule All"}
              </button>
            </div>

            <div className="mt-5 grid gap-3">
              {schedule.map((item) => (
                <div key={item.action_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="font-semibold">{item.action_number}. {item.title}</p>
                      {item.rationale && <p className="mt-1 text-sm leading-6 text-slate-500">{item.rationale}</p>}
                    </div>
                    <div className="shrink-0 text-sm sm:text-right">
                      <p className="font-semibold text-indigo-700">{formatLocalSchedule(item.scheduled_start)}</p>
                      <p className="mt-1 text-slate-500">
                        {item.duration_minutes} min · remind {item.reminder_minutes_before >= 1440 ? "1 day" : item.reminder_minutes_before >= 60 ? `${item.reminder_minutes_before / 60} hr` : `${item.reminder_minutes_before} min`} before
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {scheduleNotes.length > 0 && (
              <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm text-amber-800">
                {scheduleNotes.map((note, index) => <p key={index}>• {note}</p>)}
              </div>
            )}
          </section>
        )}

        {automationMessage && (
          <div className={`mt-5 rounded-2xl border p-4 text-sm ${automationMessage.includes("Could not") || automationMessage.includes("Connect Google") ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
            {automationMessage}
          </div>
        )}

        <section className="mt-7 rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-7">
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-600">Goal</p>
          <h1 className="mt-3 text-3xl font-bold">{plan.goal}</h1>
          {plan.summary && <p className="mt-4 max-w-3xl leading-7 text-slate-600">{plan.summary}</p>}
        </section>

        {plan.required_items.length > 0 && (
          <section className="mt-6 rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold">Requirements</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {plan.required_items.map((item, index) => (
                <span key={index} className="rounded-xl bg-slate-100 px-3 py-2 text-sm">✓ {item}</span>
              ))}
            </div>
          </section>
        )}

        <section className="mt-8">
          <div className="mb-5">
            <p className="text-sm font-bold text-indigo-600">ACTION GRAPH</p>
            <h2 className="mt-1 text-2xl font-bold">Steps toward your outcome</h2>
          </div>

          <div className="space-y-5">
            {plan.actions.map((action) => (
              <article key={action.id} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 font-bold text-indigo-600">
                        {action.action_number}
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-semibold text-slate-950">{action.title}</h3>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs capitalize text-slate-600">{action.type}</span>
                          {action.priority && <span className="rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-medium capitalize text-amber-700">{action.priority} priority</span>}
                          {action.deadline && <span className="rounded-lg bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">Due {action.deadline}</span>}
                          {action.auto_scheduled && <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">✓ Smart scheduled</span>}
                        </div>
                      </div>
                    </div>

                    {action.reason && <p className="mt-3 text-sm leading-6 text-slate-500">{action.reason}</p>}

                    {action.auto_scheduled && action.scheduled_start && (
                      <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                        <p className="text-sm font-semibold text-emerald-900">Scheduled automatically</p>
                        <p className="mt-1 text-sm text-emerald-700">
                          {formatDate(action.scheduled_start)}{action.duration_minutes ? ` · ${action.duration_minutes} minutes` : ""}
                        </p>
                        {action.calendar_event_link && (
                          <a href={action.calendar_event_link} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm font-semibold text-emerald-800 underline underline-offset-2">
                            Open Google Calendar event →
                          </a>
                        )}
                      </div>
                    )}

                    <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50">
                      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-600">Manual controls</summary>
                      <div className="grid gap-4 border-t border-slate-200 p-4 lg:grid-cols-2">
                        <div>
                          <p className="text-sm font-semibold text-slate-800">Reminder</p>
                          <div className="mt-2 flex flex-col gap-2">
                            <input
                              type="datetime-local"
                              value={reminderInputs[action.id] || ""}
                              onChange={(event) => setReminderInputs((current) => ({ ...current, [action.id]: event.target.value }))}
                              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            />
                            <button
                              type="button"
                              onClick={() => createReminderForAction(action.id)}
                              disabled={savingReminder[action.id]}
                              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
                            >
                              {savingReminder[action.id] ? "Saving..." : "Add Reminder"}
                            </button>
                          </div>
                          {(reminders[action.id]?.length ?? 0) > 0 && (
                            <div className="mt-3 space-y-2">
                              {reminders[action.id]?.map((reminder) => (
                                <div key={reminder.id} className="flex items-center justify-between gap-3 rounded-xl bg-white px-3 py-2 text-sm">
                                  <div>
                                    <p className="font-medium">{formatDate(reminder.remind_at)}</p>
                                    <p className="text-xs capitalize text-slate-400">{reminder.status}</p>
                                  </div>
                                  <button onClick={() => deleteReminderById(action.id, reminder.id)} className="text-xs font-semibold text-red-600">Delete</button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        <div>
                          <p className="text-sm font-semibold text-slate-800">Google Calendar</p>
                          <div className="mt-2 space-y-2">
                            <input
                              type="datetime-local"
                              value={calendarInputs[action.id] || ""}
                              onChange={(event) => setCalendarInputs((current) => ({ ...current, [action.id]: event.target.value }))}
                              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            />
                            <select
                              value={calendarDuration[action.id] || 60}
                              onChange={(event) => setCalendarDuration((current) => ({ ...current, [action.id]: Number(event.target.value) }))}
                              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            >
                              <option value={30}>30 minutes</option>
                              <option value={60}>1 hour</option>
                              <option value={90}>90 minutes</option>
                              <option value={120}>2 hours</option>
                            </select>
                            <button
                              type="button"
                              onClick={() => addToGoogleCalendar(action.id)}
                              disabled={addingCalendar[action.id]}
                              className="w-full rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
                            >
                              {addingCalendar[action.id] ? "Adding..." : "Add to Google Calendar"}
                            </button>
                            {calendarMessages[action.id] && <p className="text-sm text-slate-600">{calendarMessages[action.id]}</p>}
                            {calendarLinks[action.id] && (
                              <a href={calendarLinks[action.id]} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-blue-600">Open event →</a>
                            )}
                          </div>
                        </div>
                      </div>
                    </details>
                  </div>

                  <select
                    value={action.status || "pending"}
                    onChange={(event) => updateStatus(action.id, event.target.value)}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium"
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
