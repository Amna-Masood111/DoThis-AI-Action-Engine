"use client";

import { useEffect, useState } from "react";
import {
  useParams,
  useRouter,
} from "next/navigation";

import {
  supabase,
} from "../../../lib/supabase";
import { apiFetch } from "../../../lib/api";

import GoogleCalendarConnection
  from "../../../components/GoogleCalendarConnection";


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


export default function PlanPage() {

  const params = useParams();
  const router = useRouter();

  const planId =
    params.id as string;


  const [
    plan,
    setPlan
  ] =
    useState<Plan | null>(
      null
    );


  const [
    loading,
    setLoading
  ] =
    useState(true);


  const [
    error,
    setError
  ] =
    useState("");


  const [
    reminders,
    setReminders
  ] =
    useState<
      Record<
        string,
        Reminder[]
      >
    >({});


  const [
    reminderInputs,
    setReminderInputs
  ] =
    useState<
      Record<
        string,
        string
      >
    >({});


  const [
    savingReminder,
    setSavingReminder
  ] =
    useState<
      Record<
        string,
        boolean
      >
    >({});


  const [
    calendarInputs,
    setCalendarInputs
  ] =
    useState<
      Record<
        string,
        string
      >
    >({});


  const [
    calendarDuration,
    setCalendarDuration
  ] =
    useState<
      Record<
        string,
        number
      >
    >({});


  const [
    calendarMessages,
    setCalendarMessages
  ] =
    useState<
      Record<
        string,
        string
      >
    >({});


  const [
    calendarLinks,
    setCalendarLinks
  ] =
    useState<
      Record<
        string,
        string
      >
    >({});


  const [
    addingCalendar,
    setAddingCalendar
  ] =
    useState<
      Record<
        string,
        boolean
      >
    >({});


  useEffect(() => {
    loadPlan();
  }, []);


  async function getSession() {

    const {
      data: { session },
    } =
      await supabase.auth.getSession();

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

      const session =
        await getSession();

      if (!session) return;


      const response =
        await apiFetch(
          `/plans/${planId}`,
          {
            headers: {
              Authorization:
                `Bearer ${session.access_token}`,
            },
          }
        );


      const data =
        await response.json();


      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not load plan."
        );
      }


      setPlan(data);


      if (
        Array.isArray(
          data.actions
        )
      ) {

        for (
          const action
          of data.actions
        ) {

          await loadReminders(
            action.id
          );

        }

      }


    } catch (err) {

      console.error(err);

      if (
        err instanceof Error
      ) {
        setError(err.message);
      } else {
        setError(
          "Could not load plan."
        );
      }

    } finally {
      setLoading(false);
    }
  }


  async function loadReminders(
    actionId: string
  ) {

    try {

      const session =
        await getSession();

      if (!session) return;


      const response =
        await apiFetch(
          `/actions/${actionId}/reminders`,
          {
            headers: {
              Authorization:
                `Bearer ${session.access_token}`,
            },
          }
        );


      const data =
        await response.json();


      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not load reminders."
        );
      }


      setReminders(
        (current) => ({
          ...current,

          [actionId]:
            Array.isArray(
              data.reminders
            )
              ? data.reminders
              : [],
        })
      );

    } catch (err) {
      console.error(err);
    }
  }


  async function updateStatus(
    actionId: string,
    status: string
  ) {

    try {

      const session =
        await getSession();

      if (!session) return;


      const response =
        await apiFetch(
          `/actions/${actionId}/status`,
          {
            method: "PATCH",

            headers: {
              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${session.access_token}`,
            },

            body:
              JSON.stringify({
                status,
              }),
          }
        );


      const data =
        await response.json();


      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not update action."
        );
      }


      await loadPlan();

    } catch (err) {
      console.error(err);
    }
  }


  async function createReminderForAction(
    actionId: string
  ) {

    const localDateTime =
      reminderInputs[
        actionId
      ];


    if (!localDateTime) {

      alert(
        "Please choose reminder date and time."
      );

      return;

    }


    try {

      setSavingReminder(
        (current) => ({
          ...current,
          [actionId]: true,
        })
      );


      const session =
        await getSession();

      if (!session) return;


      const remindAt =
        new Date(
          localDateTime
        ).toISOString();


      const response =
        await apiFetch(
          `/actions/${actionId}/reminders`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${session.access_token}`,
            },

            body:
              JSON.stringify({
                remind_at:
                  remindAt,
              }),
          }
        );


      const data =
        await response.json();


      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not create reminder."
        );
      }


      setReminderInputs(
        (current) => ({
          ...current,
          [actionId]: "",
        })
      );


      await loadReminders(
        actionId
      );


    } catch (err) {

      console.error(err);

      if (
        err instanceof Error
      ) {
        alert(err.message);
      }

    } finally {

      setSavingReminder(
        (current) => ({
          ...current,
          [actionId]: false,
        })
      );

    }
  }


  async function deleteReminderById(
  actionId: string,
  reminderId: string
) {
  try {
    const session = await getSession();

    if (!session) return;

    const response = await fetch(
      `http://127.0.0.1:8000/reminders/${reminderId}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      }
    );

    const data = await response.json();

    // If reminder is already gone, just refresh the list
    if (!response.ok) {
      if (
        response.status === 404 ||
        data.detail === "Reminder not found."
      ) {
        await loadReminders(actionId);
        return;
      }

      throw new Error(
        data.detail ||
        "Could not delete reminder."
      );
    }

    await loadReminders(actionId);

  } catch (err) {
    console.error(err);

    if (err instanceof Error) {
      alert(err.message);
    }
  }
}


  async function addToGoogleCalendar(
    actionId: string
  ) {

    const start =
      calendarInputs[actionId];

    const duration =
      calendarDuration[actionId] || 60;


    if (!start) {

      setCalendarMessages(
        (current) => ({
          ...current,
          [actionId]:
            "Please choose a start date and time.",
        })
      );

      return;
    }


    try {

      setAddingCalendar(
        (current) => ({
          ...current,
          [actionId]: true,
        })
      );

      setCalendarMessages(
        (current) => ({
          ...current,
          [actionId]: "",
        })
      );


      const session =
        await getSession();

      if (!session) return;


      const response =
        await apiFetch(
          `/actions/${actionId}/calendar`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${session.access_token}`,
            },

            body:
              JSON.stringify({
                start_datetime:
                  start,

                duration_minutes:
                  duration,

                timezone:
                  "Asia/Karachi",
              }),
          }
        );


      const data =
        await response.json();


      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not create calendar event."
        );
      }


      setCalendarMessages(
        (current) => ({
          ...current,
          [actionId]:
            "Added to Google Calendar.",
        })
      );


      if (
        data.event?.html_link
      ) {

        setCalendarLinks(
          (current) => ({
            ...current,
            [actionId]:
              data.event.html_link,
          })
        );

      }


    } catch (err) {

      console.error(err);

      if (
        err instanceof Error
      ) {

        setCalendarMessages(
          (current) => ({
            ...current,
            [actionId]:
              err.message,
          })
        );

      }


    } finally {

      setAddingCalendar(
        (current) => ({
          ...current,
          [actionId]: false,
        })
      );

    }
  }


  function formatReminderDate(
    value: string
  ) {

    return new Date(
      value
    ).toLocaleString();

  }


  if (loading) {

    return (
      <main className="min-h-screen bg-slate-50 p-10">
        <p className="text-slate-600">
          Loading plan...
        </p>
      </main>
    );

  }


  if (error) {

    return (
      <main className="min-h-screen bg-slate-50 p-10">
        <p className="text-red-600">
          {error}
        </p>
      </main>
    );

  }


  if (!plan) {
    return null;
  }


  return (

    <main className="min-h-screen bg-slate-50 text-slate-950">

      <nav className="border-b border-slate-200 bg-white">

        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">

          <button
            onClick={() =>
              router.push("/plans")
            }
            className="text-sm font-medium text-slate-600"
          >
            ← My Plans
          </button>

          <button
            onClick={() =>
              router.push("/")
            }
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
          >
            New Plan
          </button>

        </div>

      </nav>


      <div className="mx-auto max-w-5xl px-6 py-12">

        <GoogleCalendarConnection />


        <div className="mt-7 rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-7">

          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
            Goal
          </p>

          <h1 className="mt-3 text-3xl font-bold">
            {plan.goal}
          </h1>

          {plan.summary && (
            <p className="mt-4 max-w-3xl leading-7 text-slate-600">
              {plan.summary}
            </p>
          )}

        </div>


        {plan.required_items.length > 0 && (

          <section className="mt-8 rounded-3xl border border-slate-200 bg-white p-6">

            <h2 className="font-semibold">
              Requirements
            </h2>

            <div className="mt-4 space-y-3">

              {plan.required_items.map(
                (item, index) => (

                  <div
                    key={index}
                    className="rounded-xl bg-slate-50 px-4 py-3 text-sm"
                  >
                    ✓ {item}
                  </div>

                )
              )}

            </div>

          </section>

        )}


        <section className="mt-8">

          <div className="mb-5">

            <p className="text-sm font-semibold text-indigo-600">
              Action Graph
            </p>

            <h2 className="mt-1 text-2xl font-bold">
              Steps toward your outcome
            </h2>

          </div>


          <div className="space-y-5">

            {plan.actions.map(
              (action) => (

                <div
                  key={action.id}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                >

                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

                    <div className="flex-1">

                      <p className="font-semibold text-slate-950">

                        {action.action_number}.{" "}
                        {action.title}

                      </p>


                      <div className="mt-3 flex flex-wrap gap-2">

                        <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs capitalize text-slate-600">
                          {action.type}
                        </span>


                        {action.priority && (
                          <span className="rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                            {action.priority} priority
                          </span>
                        )}


                        {action.deadline && (
                          <span className="rounded-lg bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
                            Due {action.deadline}
                          </span>
                        )}


                        {typeof action.confidence ===
                          "number" && (

                          <span className="rounded-lg bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">

                            {Math.round(
                              action.confidence * 100
                            )}
                            % confidence

                          </span>

                        )}

                      </div>


                      {action.reason && (
                        <p className="mt-3 text-sm leading-6 text-slate-500">
                          {action.reason}
                        </p>
                      )}


                      <div className="mt-5 grid gap-4 lg:grid-cols-2">

                        {/* REMINDER */}

                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">

                          <p className="text-sm font-semibold text-slate-800">
                            Reminder
                          </p>


                          <div className="mt-3 flex flex-col gap-3">

                            <input
                              type="datetime-local"

                              value={
                                reminderInputs[
                                  action.id
                                ] || ""
                              }

                              onChange={(event) =>
                                setReminderInputs(
                                  (current) => ({
                                    ...current,

                                    [action.id]:
                                      event.target.value,
                                  })
                                )
                              }

                              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            />


                            <button
                              type="button"

                              onClick={() =>
                                createReminderForAction(
                                  action.id
                                )
                              }

                              disabled={
                                savingReminder[
                                  action.id
                                ]
                              }

                              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300"
                            >

                              {savingReminder[
                                action.id
                              ]
                                ? "Saving..."
                                : "Add Reminder"}

                            </button>

                          </div>


                          {(reminders[
                            action.id
                          ]?.length ?? 0) > 0 && (

                            <div className="mt-4 space-y-2">

                              {reminders[
                                action.id
                              ]?.map(
                                (reminder) => (

                                  <div
                                    key={
                                      reminder.id
                                    }
                                    className="flex items-center justify-between rounded-xl bg-white px-3 py-2"
                                  >

                                    <div>

                                      <p className="text-sm">
                                        {formatReminderDate(
                                          reminder.remind_at
                                        )}
                                      </p>

                                      <p className="text-xs capitalize text-slate-400">
                                        {reminder.status}
                                      </p>

                                    </div>


                                    <button
                                      onClick={() =>
                                        deleteReminderById(
                                          action.id,
                                          reminder.id
                                        )
                                      }
                                      className="text-xs font-semibold text-red-600"
                                    >
                                      Delete
                                    </button>

                                  </div>

                                )
                              )}

                            </div>

                          )}

                        </div>


                        {/* GOOGLE CALENDAR */}

                        <div className="rounded-2xl border border-blue-100 bg-blue-50/40 p-4">

                          <p className="text-sm font-semibold text-slate-800">
                            Google Calendar
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            Schedule this action in your calendar.
                          </p>


                          <div className="mt-3 space-y-3">

                            <input
                              type="datetime-local"

                              value={
                                calendarInputs[
                                  action.id
                                ] || ""
                              }

                              onChange={(event) =>
                                setCalendarInputs(
                                  (current) => ({
                                    ...current,

                                    [action.id]:
                                      event.target.value,
                                  })
                                )
                              }

                              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            />


                            <select
                              value={
                                calendarDuration[
                                  action.id
                                ] || 60
                              }

                              onChange={(event) =>
                                setCalendarDuration(
                                  (current) => ({
                                    ...current,

                                    [action.id]:
                                      Number(
                                        event.target.value
                                      ),
                                  })
                                )
                              }

                              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            >

                              <option value={15}>
                                15 minutes
                              </option>

                              <option value={30}>
                                30 minutes
                              </option>

                              <option value={60}>
                                1 hour
                              </option>

                              <option value={120}>
                                2 hours
                              </option>

                            </select>


                            <button
                              type="button"

                              onClick={() =>
                                addToGoogleCalendar(
                                  action.id
                                )
                              }

                              disabled={
                                addingCalendar[
                                  action.id
                                ]
                              }

                              className="w-full rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:bg-slate-300"
                            >

                              {addingCalendar[
                                action.id
                              ]
                                ? "Adding..."
                                : "Add to Google Calendar"}

                            </button>


                            {calendarMessages[
                              action.id
                            ] && (

                              <p className="text-sm text-slate-600">
                                {calendarMessages[
                                  action.id
                                ]}
                              </p>

                            )}


                            {calendarLinks[
                              action.id
                            ] && (

                              <a
                                href={
                                  calendarLinks[
                                    action.id
                                  ]
                                }
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-block text-sm font-semibold text-blue-600 hover:text-blue-700"
                              >
                                Open event in Google Calendar →
                              </a>

                            )}

                          </div>

                        </div>

                      </div>

                    </div>


                    <select
                      value={
                        action.status ||
                        "pending"
                      }

                      onChange={(event) =>
                        updateStatus(
                          action.id,
                          event.target.value
                        )
                      }

                      className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium"
                    >

                      <option value="pending">
                        Pending
                      </option>

                      <option value="in_progress">
                        In Progress
                      </option>

                      <option value="completed">
                        Completed
                      </option>

                    </select>

                  </div>

                </div>

              )
            )}

          </div>

        </section>

      </div>

    </main>
  );
}