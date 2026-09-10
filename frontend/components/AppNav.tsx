"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";

export default function AppNav() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, []);

  async function logout() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <nav className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5 sm:px-6">
        <button onClick={() => router.push("/")} className="flex items-center gap-3 text-left">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-sm">D</div>
          <div><p className="font-semibold tracking-tight text-slate-950">DoThis</p><p className="text-xs text-slate-500">AI execution assistant</p></div>
        </button>
        <div className="flex items-center gap-1 sm:gap-2">
          {session ? <>
            <button onClick={() => router.push("/")} className="rounded-xl px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">New Plan</button>
            <button onClick={() => router.push("/plans")} className="rounded-xl px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">My Plans</button>
            <button onClick={logout} className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Logout</button>
          </> : <>
            <button onClick={() => router.push("/login")} className="rounded-xl px-3 py-2 text-sm font-medium text-slate-600">Sign in</button>
            <button onClick={() => router.push("/signup")} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">Get started</button>
          </>}
        </div>
      </div>
    </nav>
  );
}
