"use client";

import { ChangeEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppNav from "../components/AppNav";
import { supabase } from "../lib/supabase";
import { apiFetch } from "../lib/api";

type ActionItem = { id:number; title:string; type:string; deadline?:string|null; depends_on?:number[]; priority?:"low"|"medium"|"high"; confidence?:number; status?:string; needs_confirmation?:boolean; reason?:string };
type OutcomeResult = { goal:string; summary:string; required_items:string[]; actions:ActionItem[] };

export default function Home() {
  const router = useRouter();
  const [text,setText]=useState(""); const [result,setResult]=useState<OutcomeResult|null>(null);
  const [loading,setLoading]=useState(false); const [uploading,setUploading]=useState(false); const [saving,setSaving]=useState(false);
  const [error,setError]=useState(""); const [message,setMessage]=useState(""); const [signedIn,setSignedIn]=useState(false);

  useEffect(()=>{ supabase.auth.getSession().then(({data})=>setSignedIn(Boolean(data.session))); const {data}=supabase.auth.onAuthStateChange((_e,s)=>setSignedIn(Boolean(s))); return()=>data.subscription.unsubscribe(); },[]);

  async function buildPlan(){ if(!text.trim()) return; setLoading(true); setError(""); setMessage("");
    try{ const r=await apiFetch("/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})}); const d=await r.json(); if(!r.ok) throw new Error(d.detail||"Could not analyze this information."); setResult(d); }
    catch(e){setError(e instanceof Error?e.message:"Unable to connect to DoThis.");} finally{setLoading(false);} }

  async function uploadFile(event:ChangeEvent<HTMLInputElement>){ const file=event.target.files?.[0]; if(!file)return; setUploading(true);setError("");setMessage("");
    try{ const form=new FormData();form.append("file",file); const r=await apiFetch("/extract-file",{method:"POST",body:form});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Could not read file.");setText(d.text);setResult(null);setMessage(`${file.name} is ready. Review the extracted text, then build your plan.`); }
    catch(e){setError(e instanceof Error?e.message:"Could not read file.");}finally{setUploading(false);event.target.value="";} }

  async function savePlan(){ if(!result)return; const {data:{session}}=await supabase.auth.getSession(); if(!session){router.push("/login");return;} setSaving(true);setMessage("");
    try{const r=await apiFetch("/plans",{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${session.access_token}`},body:JSON.stringify({original_text:text,outcome:result})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Could not save plan.");setMessage("Plan saved. You can now add reminders and calendar events.");}
    catch(e){setError(e instanceof Error?e.message:"Could not save plan.");}finally{setSaving(false);} }

  return <main className="min-h-screen bg-slate-50 text-slate-950"><AppNav/>
    <div className="mx-auto max-w-6xl px-5 py-12 sm:px-6 sm:py-16">
      <section className="mx-auto max-w-3xl text-center"><div className="mx-auto mb-5 inline-flex rounded-full border border-indigo-100 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">Plan → schedule → remember → execute</div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">Turn messy information into <span className="text-indigo-600">clear action.</span></h1>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">Paste a schedule, deadline, email or brief—or upload a document. DoThis turns it into an actionable plan you can save, track, remind and add to Google Calendar.</p>
      </section>

      <section className="mx-auto mt-10 max-w-4xl rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <div className="mb-3 flex items-center justify-between gap-3"><label className="font-semibold">What do you need to accomplish?</label><span className="text-xs text-slate-400">{text.length}/15,000</span></div>
        <textarea value={text} onChange={e=>setText(e.target.value.slice(0,15000))} rows={9} placeholder="Example: I have a hackathon demo next Friday. I need to finish the prototype, prepare slides and rehearse before the presentation..." className="w-full resize-y rounded-2xl border border-slate-200 bg-slate-50 p-4 leading-7 outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"/>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <label className="cursor-pointer rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-center text-sm font-semibold text-slate-700 hover:bg-slate-50"><input type="file" className="hidden" accept=".pdf,.docx,.txt,.md,.csv,.png,.jpg,.jpeg,.webp" onChange={uploadFile}/>{uploading?"Reading file...":"Upload PDF / document / screenshot"}</label>
          <div className="flex gap-2"><button onClick={()=>{setText("");setResult(null);setMessage("");setError("");}} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-500 hover:bg-slate-100">Clear</button><button onClick={buildPlan} disabled={loading||!text.trim()} className="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:bg-slate-300">{loading?"Building plan...":"Build Action Plan"}</button></div>
        </div>
        <p className="mt-3 text-xs text-slate-400">PDF, DOCX and text work directly. Screenshot OCR requires Tesseract on the backend server.</p>
        {error&&<div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{message&&<div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
      </section>

      {result&&<section className="mx-auto mt-8 max-w-4xl space-y-5">
        <div className="rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-6"><p className="text-xs font-bold uppercase tracking-wider text-indigo-600">Detected goal</p><h2 className="mt-2 text-2xl font-bold">{result.goal}</h2><p className="mt-3 leading-7 text-slate-600">{result.summary}</p></div>
        {result.required_items?.length>0&&<div className="rounded-3xl border border-slate-200 bg-white p-6"><h3 className="font-semibold">Requirements</h3><div className="mt-3 flex flex-wrap gap-2">{result.required_items.map((x,i)=><span key={i} className="rounded-xl bg-slate-100 px-3 py-2 text-sm">✓ {x}</span>)}</div></div>}
        <div className="space-y-3">{result.actions.map(a=><div key={a.id} className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex gap-4"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 font-bold text-indigo-600">{a.id}</div><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{a.title}</h3>{a.priority&&<span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize">{a.priority}</span>}{a.deadline&&<span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">Due {a.deadline}</span>}</div>{a.reason&&<p className="mt-2 text-sm leading-6 text-slate-500">{a.reason}</p>}</div></div></div>)}</div>
        <div className="flex flex-col items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row"><p className="text-sm text-slate-500">{signedIn?"Save this plan to track progress, reminders and calendar events.":"Sign in to save this plan and enable execution features."}</p><button onClick={savePlan} disabled={saving} className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white disabled:bg-slate-300">{saving?"Saving...":signedIn?"Save Plan":"Sign in to Save"}</button></div>
      </section>}
    </div>
  </main>;
}
