"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  supabase,
} from "../../lib/supabase";
import { apiFetch } from "../../lib/api";


type Plan = {
  id: string;
  goal: string;
  summary?: string;
  created_at?: string;
  total_actions: number;
  completed_actions: number;
};


export default function PlansPage() {

  const router = useRouter();

  const [plans, setPlans] =
    useState<Plan[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {

    loadPlans();

  }, []);


  async function loadPlans() {

    setLoading(true);
    setError("");

    try {

      const {
        data: {
          session
        }
      } =
        await supabase.auth
          .getSession();


      if (!session) {

        router.push(
          "/login"
        );

        return;
      }


      const response =
        await apiFetch("/plans",
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
          "Could not load plans."
        );

      }


      setPlans(
        Array.isArray(
          data.plans
        )
          ? data.plans
          : []
      );


    } catch (err) {

      console.error(err);

      if (
        err instanceof Error
      ) {

        setError(
          err.message
        );

      } else {

        setError(
          "Could not load plans."
        );

      }

    } finally {

      setLoading(false);

    }

  }


  async function logout() {

    await supabase.auth
      .signOut();

    router.push(
      "/login"
    );

  }


  function formatDate(
    date?: string
  ) {

    if (!date) {
      return "Unknown date";
    }

    return new Date(
      date
    ).toLocaleDateString(
      undefined,
      {
        year: "numeric",
        month: "short",
        day: "numeric",
      }
    );

  }


  return (

    <main className="min-h-screen bg-slate-50 text-slate-950">

      {/* NAVBAR */}

      <nav className="border-b border-slate-200 bg-white">

        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">

          <button
            onClick={() =>
              router.push("/")
            }
            className="flex items-center gap-3"
          >

            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white">

              D

            </div>


            <div className="text-left">

              <p className="font-semibold">
                DoThis
              </p>

              <p className="text-xs text-slate-500">
                Outcome Engine
              </p>

            </div>

          </button>


          <div className="flex items-center gap-3">

            <button
              onClick={() =>
                router.push("/")
              }
              className="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
            >

              New Plan

            </button>


            <button
              onClick={logout}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
            >

              Sign out

            </button>

          </div>

        </div>

      </nav>


      {/* PAGE */}

      <div className="mx-auto max-w-6xl px-6 py-12">

        {/* HEADER */}

        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">

          <div>

            <p className="text-sm font-semibold text-indigo-600">

              Workspace

            </p>

            <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">

              My Plans

            </h1>

            <p className="mt-3 text-slate-500">

              Your saved outcomes and
              action plans.

            </p>

          </div>


          <button
            onClick={() =>
              router.push("/")
            }
            className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700"
          >

            + New Outcome

          </button>

        </div>


        {/* LOADING */}

        {loading && (

          <div className="mt-10 rounded-2xl border border-indigo-100 bg-indigo-50 p-5">

            <div className="flex items-center gap-3">

              <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />

              <p className="text-sm font-medium text-indigo-700">

                Loading your plans...

              </p>

            </div>

          </div>

        )}


        {/* ERROR */}

        {error && (

          <div className="mt-10 rounded-2xl border border-red-200 bg-red-50 p-5">

            <p className="font-medium text-red-700">

              {error}

            </p>

          </div>

        )}


        {/* EMPTY */}

        {!loading &&
          !error &&
          plans.length === 0 && (

            <div className="mt-10 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">

              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 font-bold text-indigo-600">

                +

              </div>

              <h2 className="mt-5 text-xl font-semibold">

                No plans yet

              </h2>

              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">

                Build your first outcome
                plan and save it to see
                it here.

              </p>

              <button
                onClick={() =>
                  router.push("/")
                }
                className="mt-6 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white"
              >

                Create first plan

              </button>

            </div>

          )}


        {/* PLAN GRID */}

        {!loading &&
          plans.length > 0 && (

            <div className="mt-10 grid gap-5 md:grid-cols-2">

              {plans.map(
                (plan) => {

                  const progress =
                    plan.total_actions >
                    0

                      ? Math.round(
                          (
                            plan.completed_actions /
                            plan.total_actions
                          ) * 100
                        )

                      : 0;


                  return (

                    <button
                      key={plan.id}
                      onClick={() =>
                        router.push(
                          `/plans/${plan.id}`
                        )
                      }
                      className="group rounded-3xl border border-slate-200 bg-white p-6 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md"
                    >

                      {/* TOP */}

                      <div className="flex items-start justify-between gap-4">

                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 font-semibold text-indigo-600">

                          ◎

                        </div>

                        <span className="text-xs text-slate-400">

                          {formatDate(
                            plan.created_at
                          )}

                        </span>

                      </div>


                      {/* GOAL */}

                      <h2 className="mt-5 text-lg font-semibold leading-7 text-slate-950 transition group-hover:text-indigo-700">

                        {plan.goal}

                      </h2>


                      {plan.summary && (

                        <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500">

                          {plan.summary}

                        </p>

                      )}


                      {/* STATS */}

                      <div className="mt-6 flex items-center justify-between">

                        <span className="text-sm text-slate-500">

                          {
                            plan.completed_actions
                          }
                          /
                          {
                            plan.total_actions
                          }{" "}
                          actions completed

                        </span>


                        <span className="text-sm font-semibold text-indigo-600">

                          {progress}%

                        </span>

                      </div>


                      {/* PROGRESS */}

                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">

                        <div
                          style={{
                            width:
                              `${progress}%`,
                          }}
                          className="h-full rounded-full bg-indigo-600 transition-all"
                        />

                      </div>


                      <div className="mt-5 border-t border-slate-100 pt-4">

                        <span className="text-sm font-semibold text-indigo-600">

                          Open plan →

                        </span>

                      </div>

                    </button>

                  );

                }
              )}

            </div>

          )}

      </div>

    </main>

  );
}