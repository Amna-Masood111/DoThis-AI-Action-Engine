"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabase";


export default function LoginPage() {

  const router = useRouter();

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  async function handleLogin(
    event: FormEvent
  ) {

    event.preventDefault();

    setLoading(true);
    setError("");

    try {

      const {
        error: loginError
      } = await supabase.auth
        .signInWithPassword({

          email,

          password,

        });


      if (loginError) {
        throw loginError;
      }


      router.push("/");


    } catch (err) {

      if (err instanceof Error) {

        setError(err.message);

      } else {

        setError(
          "Could not sign in."
        );

      }

    } finally {

      setLoading(false);

    }

  }


  return (

    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">

      <div className="w-full max-w-md">


        {/* BRAND */}

        <div className="mb-8 text-center">

          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 font-bold text-white shadow-sm">
            D
          </div>

          <h1 className="mt-5 text-3xl font-bold tracking-tight text-slate-950">
            Welcome back
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Sign in to continue to DoThis.
          </p>

        </div>


        {/* CARD */}

        <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">

          <form
            onSubmit={handleLogin}
            className="space-y-5"
          >

            {/* EMAIL */}

            <div>

              <label className="text-sm font-medium text-slate-700">
                Email address
              </label>

              <input
                type="email"
                required
                value={email}
                onChange={(event) =>
                  setEmail(
                    event.target.value
                  )
                }
                placeholder="you@example.com"
                className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
              />

            </div>


            {/* PASSWORD */}

            <div>

              <label className="text-sm font-medium text-slate-700">
                Password
              </label>

              <input
                type="password"
                required
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value
                  )
                }
                placeholder="Your password"
                className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
              />

            </div>


            {/* ERROR */}

            {error && (

              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>

            )}


            {/* LOGIN */}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-indigo-600 px-5 py-3.5 font-semibold text-white transition hover:bg-indigo-700 disabled:bg-slate-300"
            >

              {loading
                ? "Signing in..."
                : "Sign in"}

            </button>

          </form>


          <div className="mt-6 border-t border-slate-100 pt-6 text-center">

            <p className="text-sm text-slate-500">

              Don&apos;t have an account?{" "}

              <button
                onClick={() =>
                  router.push("/signup")
                }
                className="font-semibold text-indigo-600 hover:text-indigo-700"
              >
                Create account
              </button>

            </p>

          </div>

        </div>

      </div>

    </main>
  );
}