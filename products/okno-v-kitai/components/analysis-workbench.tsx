"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  DatabaseZap,
  FileSearch,
  Loader2,
  RefreshCw,
  SearchCheck,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { seedNews, type NewsItem } from "@/lib/data";
import type { AnalysisFocus, AnalysisMarket, AnalysisPeriod, AnalysisResult } from "@/lib/analysis";

const focusOptions: AnalysisFocus[] = ["SHACMAN", "GWM", "Все"];
const quickQuestions = [
  { text: "Какие свежие изменения могут повлиять на продажи, локализацию и поставки SHACMAN в России?", focus: "SHACMAN" },
  { text: "Как меняются продажи GWM и какие сигналы важны для российского рынка?", focus: "GWM" },
  { text: "Какие стратегические и геополитические риски появились за последний год?", focus: "Все" },
  { text: "Сравни продажи основных автомобильных брендов за 2025 год и январь–июль 2026 года.", focus: "Все" },
] as const;

export function AnalysisWorkbench() {
  const [focus, setFocus] = useState<AnalysisFocus>("SHACMAN");
  const [market, setMarket] = useState<AnalysisMarket>("Все рынки");
  const [period, setPeriod] = useState<AnalysisPeriod>("365");
  const [query, setQuery] = useState(quickQuestions[0].text);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [corpus, setCorpus] = useState<NewsItem[]>(seedNews);
  const [indexStatus, setIndexStatus] = useState<"loading" | "live" | "partial" | "fallback">("loading");
  const [error, setError] = useState("");

  const loadCorpus = useCallback(async () => {
    setIndexStatus("loading");
    try {
      const response = await fetch("/api/news", { cache: "no-store", signal: AbortSignal.timeout(14_000) });
      if (!response.ok) throw new Error();
      const payload = await response.json() as { news: NewsItem[]; errors: string[] };
      const merged = [...new Map([...payload.news, ...seedNews].map((item) => [item.url, item])).values()];
      setCorpus(merged);
      setIndexStatus(payload.errors.length ? "partial" : "live");
    } catch {
      setCorpus(seedNews);
      setIndexStatus("fallback");
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => void loadCorpus(), 0);
    return () => window.clearTimeout(initial);
  }, [loadCorpus]);

  async function analyze() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ focus, market, period, query, items: corpus }),
      });
      if (!response.ok) throw new Error();
      setResult(await response.json() as AnalysisResult);
    } catch {
      setError("Анализ не сформирован. Обновите индекс и повторите запрос.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="radar-grid min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
        <section className="grid gap-6 xl:grid-cols-[430px_minmax(0,1fr)]">
          <aside className="xl:sticky xl:top-24 xl:self-start">
            <div className="rounded-2xl border border-violet-400/20 bg-[#0a1516]/95 p-5 sm:p-6">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-violet-300"><BrainCircuit className="size-5" /><span className="text-sm font-semibold uppercase tracking-[0.12em]">RAG 3.0</span></div>
                <CorpusStatus status={indexStatus} count={corpus.length} />
              </div>
              <h1 className="mt-4 text-3xl font-semibold tracking-[-0.035em] text-white">Доказательный анализ</h1>
              <p className="mt-3 text-sm leading-6 text-slate-400">Двухэтапный поиск понимает названия брендов и смысл вопроса, учитывает свежесть, рыночные показатели и связывает каждый вывод с нумерованным источником.</p>

              <div className="mt-6 grid grid-cols-3 gap-2" role="group" aria-label="Фокус анализа">
                {focusOptions.map((item) => <button key={item} type="button" aria-pressed={focus === item} onClick={() => setFocus(item)} className={`min-h-11 rounded-xl border px-2 text-sm font-semibold transition-colors ${focus === item ? "border-violet-300/45 bg-violet-300/15 text-white" : "border-white/10 bg-white/[0.035] text-slate-400 hover:text-white"}`}>{item}</button>)}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2">
                <Select value={market} onValueChange={(value) => setMarket(value as AnalysisMarket)}><SelectTrigger className="h-11 border-white/10 bg-[#071011] text-slate-200"><SelectValue /></SelectTrigger><SelectContent className="border-zinc-300 bg-white text-zinc-900"><SelectItem value="Все рынки">Все рынки</SelectItem><SelectItem value="Россия">Россия</SelectItem><SelectItem value="Китай">Китай</SelectItem><SelectItem value="Международный">Международный</SelectItem></SelectContent></Select>
                <Select value={period} onValueChange={(value) => setPeriod(value as AnalysisPeriod)}><SelectTrigger className="h-11 border-white/10 bg-[#071011] text-slate-200"><SelectValue /></SelectTrigger><SelectContent className="border-zinc-300 bg-white text-zinc-900"><SelectItem value="90">90 дней</SelectItem><SelectItem value="365">1 год</SelectItem><SelectItem value="all">Весь архив</SelectItem></SelectContent></Select>
              </div>

              <label className="mt-5 block text-sm font-semibold text-slate-200" htmlFor="analysis-question">Вопрос</label>
              <Textarea id="analysis-question" value={query} onChange={(event) => setQuery(event.target.value)} className="mt-2 min-h-32 resize-y rounded-xl border-white/10 bg-[#071011] p-4 leading-6 text-white" />
              <div className="mt-3 space-y-1.5">{quickQuestions.slice(1).map((question) => <button key={question.text} type="button" onClick={() => { setQuery(question.text); setFocus(question.focus); }} className="block w-full rounded-lg px-3 py-2 text-left text-xs leading-5 text-slate-500 hover:bg-white/[0.04] hover:text-slate-300">{question.text}</button>)}</div>
              <Button onClick={() => void analyze()} disabled={loading || !query.trim()} className="mt-4 w-full bg-violet-400 text-[#10051c] hover:bg-violet-300">{loading ? <Loader2 className="animate-spin" /> : <Sparkles />} {loading ? "Сопоставление фактов…" : "Сформировать анализ"}</Button>
              <Button type="button" variant="ghost" onClick={() => void loadCorpus()} disabled={indexStatus === "loading"} className="mt-2 w-full text-slate-500 hover:bg-white/[0.04] hover:text-slate-300"><RefreshCw className={indexStatus === "loading" ? "animate-spin" : ""} /> Обновить индекс</Button>
              <div className="mt-4 flex gap-2 border-t border-white/7 pt-4 text-xs leading-5 text-slate-500"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-300" />Если данных мало, система сообщает об ограничении вместо уверенного предположения.</div>
            </div>
          </aside>

          <section className="min-w-0">
            {error && <div className="mb-5 rounded-xl border border-red-300/15 bg-red-300/[0.05] p-4 text-sm text-red-200">{error}</div>}
            {!result ? (
              <div className="grid min-h-[560px] place-items-center rounded-2xl border border-dashed border-white/12 bg-[#0a1516]/75 p-8 text-center">
                <div><FileSearch className="mx-auto size-10 text-slate-600" /><h2 className="mt-4 text-xl font-semibold text-slate-200">Задайте вопрос по ленте</h2><p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">В ответе будут ключевые сигналы, риски, действия и ссылки с номерами цитат.</p></div>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="rounded-2xl border border-violet-400/15 bg-violet-400/[0.045] p-5 sm:p-6">
                  <div className="flex flex-wrap items-center gap-2"><Badge variant="outline" className="border-violet-400/25 text-violet-300">Прямой ответ</Badge><Badge variant="outline" className="border-cyan-400/20 text-cyan-300">{result.mode === "model" ? "Модель + доказательства" : "Доказательный поиск"}</Badge><ConfidenceBadge level={result.confidence.level} score={result.confidence.score} /></div>
                  <p className="mt-4 text-lg leading-8 text-slate-200">{result.summary}</p>
                  <div className="mt-5 grid gap-3 sm:grid-cols-4"><Coverage label="Материалы" value={result.coverage.materials} /><Coverage label="Источники" value={result.coverage.sources} /><Coverage label="В фокусе" value={result.coverage.focusMaterials} /><Coverage label="Официальные" value={result.coverage.officialMaterials} /></div>
                  <p className="mt-4 text-xs text-slate-600">{result.confidence.reason}</p>
                </div>

                <div className="rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5 sm:p-6">
                  <div className="flex items-center gap-2"><SearchCheck className="size-5 text-cyan-300" /><h2 className="font-semibold text-white">Ключевые сигналы</h2></div>
                  <div className="mt-4 space-y-3">{result.signals.map((signal) => <div key={`${signal.citation}-${signal.claim}`} className="grid gap-3 rounded-xl border border-white/8 bg-[#071011]/70 p-4 sm:grid-cols-[34px_1fr]"><span className="grid size-8 place-items-center rounded-lg bg-violet-300/10 font-mono text-sm text-violet-300">{signal.citation}</span><div><p className="text-sm leading-6 text-slate-200">{signal.claim}</p><p className="mt-2 text-sm leading-6 text-slate-500">{signal.impact}</p></div></div>)}</div>
                </div>

                <div className="grid gap-5 lg:grid-cols-2"><AnalysisList title="Риски и оговорки" items={result.risks} tone="orange" /><AnalysisList title="Следующие действия" items={result.actions} tone="cyan" /></div>

                <div className="rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5 sm:p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><DatabaseZap className="size-5 text-violet-300" /><h2 className="font-semibold text-white">Доказательная база</h2></div><span className="text-sm text-slate-500">{result.evidence.length} материалов</span></div>
                  <div className="mt-4 divide-y divide-white/7">{result.evidence.map((item) => <a key={item.url} href={item.url} target="_blank" rel="noopener noreferrer" className="group grid gap-3 py-4 sm:grid-cols-[36px_minmax(0,1fr)_72px]"><span className="grid size-8 place-items-center rounded-lg border border-violet-300/20 font-mono text-sm text-violet-300">{item.citation}</span><span className="min-w-0"><span className="block font-medium leading-6 text-slate-200 group-hover:text-white">{item.title}</span><span className="mt-1 block text-sm text-slate-500">{item.source} · {item.market} · {new Date(item.publishedAt).toLocaleDateString("ru-RU")}</span>{item.matchedTerms.length > 0 && <span className="mt-2 flex flex-wrap gap-1.5">{item.matchedTerms.map((term) => <span key={term} className="rounded-full bg-white/[0.04] px-2 py-0.5 text-xs text-slate-600">{term}</span>)}</span>}</span><span className="flex items-center justify-end gap-2 text-xs font-semibold text-cyan-300">{item.relevance}% <ArrowUpRight className="size-4" /></span></a>)}</div>
                </div>
              </div>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

function CorpusStatus({ status, count }: { status: "loading" | "live" | "partial" | "fallback"; count: number }) {
  if (status === "loading") return <span className="inline-flex items-center gap-1.5 text-xs text-slate-500"><Loader2 className="size-3.5 animate-spin" /> индекс</span>;
  const color = status === "live" ? "text-emerald-300" : status === "partial" ? "text-amber-300" : "text-slate-500";
  return <span className={`inline-flex items-center gap-1.5 text-xs ${color}`}><CheckCircle2 className="size-3.5" /> {count} материалов</span>;
}

function ConfidenceBadge({ level, score }: { level: string; score: number }) {
  const style = level === "Высокая" ? "border-emerald-300/20 text-emerald-300" : level === "Средняя" ? "border-amber-300/20 text-amber-300" : "border-slate-300/15 text-slate-400";
  return <Badge variant="outline" className={style}>полнота: {level.toLocaleLowerCase("ru-RU")} · {score}%</Badge>;
}

function Coverage({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-white/8 bg-[#071011]/60 p-3"><p className="text-xs text-slate-600">{label}</p><p className="mt-1 text-xl font-semibold text-white">{value}</p></div>;
}

function AnalysisList({ title, items, tone }: { title: string; items: string[]; tone: "orange" | "cyan" }) {
  const dot = tone === "orange" ? "bg-orange-400" : "bg-cyan-400";
  return <div className="rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5 sm:p-6"><h2 className="font-semibold text-white">{title}</h2><ul className="mt-4 space-y-3">{items.map((item) => <li key={item} className="flex gap-3 text-sm leading-6 text-slate-400"><span className={`mt-2 size-1.5 shrink-0 rounded-full ${dot}`} />{item}</li>)}</ul></div>;
}
