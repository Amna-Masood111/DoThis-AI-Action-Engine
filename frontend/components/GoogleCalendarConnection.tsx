"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  supabase,
} from "../lib/supabase";
import { apiFetch } from "../lib/api";


export default function GoogleCalendarConnection() {

  const [connected, setConnected] =
    useState(false);

  const [loading, setLoading] =
    useState(true);

  const [working, setWorking] =
    useState(false);

  const [error, setError] =
    useState("");


  useEffect(() => {

    checkStatus();

  }, []);


  async function getSession() {

    const {
      data: {
        session
      }
    } =
      await supabase.auth
        .getSession();


    return session;

  }


  async function checkStatus() {

    setLoading(true);
    setError("");


    try {

      const session =
        await getSession();


      if (!session) {

        setConnected(false);

        return;
      }


      const response =
        await apiFetch("/google/status",
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
          "Could not check Google Calendar."
        );

      }


      setConnected(
        Boolean(
          data.connected
        )
      );


    } catch (err) {

      console.error(err);

      if (
        err instanceof Error
      ) {

        setError(
          err.message
        );

      }

    } finally {

      setLoading(false);

    }

  }


  async function connectGoogle() {

    setWorking(true);
    setError("");


    try {

      const session =
        await getSession();


      if (!session) {

        throw new Error(
          "Please sign in first."
        );

      }


      const response =
        await apiFetch("/google/connect",
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
          "Could not start Google connection."
        );

      }


      if (
        !data.authorization_url
      ) {

        throw new Error(
          "Google authorization URL missing."
        );

      }


      window.location.href =
        data.authorization_url;


    } catch (err) {

      console.error(err);

      if (
        err instanceof Error
      ) {

        setError(
          err.message
        );

      }

      setWorking(false);

    }

  }


  async function disconnectGoogle() {

    if (
      !window.confirm(
        "Disconnect Google Calendar?"
      )
    ) {
      return;
    }


    setWorking(true);
    setError("");


    try {

      const session =
        await getSession();


      if (!session) {

        throw new Error(
          "Please sign in first."
        );

      }


      const response =
        await apiFetch("/google/disconnect",
          {
            method: "DELETE",

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
          "Could not disconnect Google."
        );

      }


      setConnected(false);


    } catch (err) {

      console.error(err);

      if (
        err instanceof Error
      ) {

        setError(
          err.message
        );

      }

    } finally {

      setWorking(false);

    }

  }


  if (loading) {

    return (

      <div className="rounded-2xl border border-slate-200 bg-white p-5">

        <p className="text-sm text-slate-500">
          Checking Google Calendar...
        </p>

      </div>

    );

  }


  return (

    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">

        <div>

          <div className="flex items-center gap-2">

            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-sm font-bold text-blue-600">
              G
            </div>


            <div>

              <p className="font-semibold text-slate-900">
                Google Calendar
              </p>


              <p className="text-sm text-slate-500">

                {connected
                  ? "Connected to your DoThis account."
                  : "Connect your calendar to execute actions."}

              </p>

            </div>

          </div>

        </div>


        {connected ? (

          <div className="flex items-center gap-3">

            <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">

              Connected

            </span>


            <button
              type="button"
              onClick={
                disconnectGoogle
              }
              disabled={working}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
            >

              {working
                ? "Disconnecting..."
                : "Disconnect"}

            </button>

          </div>

        ) : (

          <button
            type="button"
            onClick={
              connectGoogle
            }
            disabled={working}
            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:bg-slate-300"
          >

            {working
              ? "Connecting..."
              : "Connect Google Calendar"}

          </button>

        )}

      </div>


      {error && (

        <p className="mt-3 text-sm text-red-600">
          {error}
        </p>

      )}

    </div>

  );
}