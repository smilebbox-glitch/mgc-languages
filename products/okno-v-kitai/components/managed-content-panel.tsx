"use client";

import { useEffect, useState } from "react";
import { Megaphone } from "lucide-react";

type Item = { id: string; title: string; body: string; updatedAt: string };
export function ManagedContentPanel({ section = "travel-guide" }: { section?: string }) {
  const [items,setItems]=useState<Item[]>([]);
  useEffect(()=>{fetch(`/api/content?section=${encodeURIComponent(section)}`,{cache:"no-store"}).then(r=>r.ok?r.json():null).then(d=>setItems(d?.items||[])).catch(()=>{});},[section]);
  if(!items.length) return null;
  return <section className="mt-8 rounded-2xl border border-violet-400/15 bg-violet-400/[0.045] p-5 sm:p-6"><div className="flex items-center gap-2 font-semibold text-white"><Megaphone className="size-5 text-violet-300"/> Корпоративные заметки</div><div className="mt-4 grid gap-3 md:grid-cols-2">{items.map(item=><article key={item.id} className="rounded-xl border border-white/8 bg-[#071011]/70 p-4"><h3 className="font-semibold text-white">{item.title}</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">{item.body}</p><p className="mt-3 text-[11px] text-slate-600">Обновлено {new Date(item.updatedAt).toLocaleString("ru-RU")}</p></article>)}</div></section>;
}
