"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpenText,
  Sparkles,
  UploadCloud,
  FileText,
  KeyRound,
  Eye,
  EyeOff,
  Feather,
  LibraryBig,
  Trash2,
  Copy,
  Check,
  Download,
  RefreshCw,
  Quote,
  ArrowRight,
  ArrowDown,
  Layers,
  ScanText,
  BookOpen,
  Wand2,
  CircleAlert,
  CircleCheck,
  Info,
  X,
} from "lucide-react";

type DocInfo = {
  id: number;
  filename: string;
  charCount: number;
  chunkCount: number;
  pageCount: number;
  excerpt: string;
};

type Poem = {
  id: number;
  content: string;
  topic: string;
  tone?: string | null;
  form?: string | null;
  model?: string | null;
  documentName?: string | null;
  createdAt?: string;
};

const TONES = ["Contemplativo", "Melancólico", "Alegre", "Romántico", "Épico", "Oscuro", "Esperanzado"];
const FORMS = ["Verso libre", "Soneto", "Haiku", "Décima", "Romance", "Oda"];

const TONE_HINT: Record<string, string> = {
  Contemplativo: "pausado y reflexivo, como mirar por la ventana",
  Melancólico: "nostálgico, con niebla y atardeceres",
  Alegre: "luminoso, con ritmo juguetón",
  Romántico: "tierno e íntimo, de latidos y jazmines",
  Épico: "grande y heroico, de horizontes en llamas",
  Oscuro: "nocturno, de sombras y ecos",
  Esperanzado: "abierto al mañana, de semillas y albas",
};

function formatNum(n: number) {
  return new Intl.NumberFormat("es-ES").format(n);
}

function downloadText(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function Page() {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [useDemo, setUseDemo] = useState(true);

  const [doc, setDoc] = useState<DocInfo | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [topic, setTopic] = useState("");
  const [tone, setTone] = useState("Contemplativo");
  const [form, setForm] = useState("Verso libre");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [poem, setPoem] = useState<Poem | null>(null);
  const [usedFragments, setUsedFragments] = useState<number | null>(null);

  const [library, setLibrary] = useState<Poem[]>([]);
  const [loadingLib, setLoadingLib] = useState(true);
  const [selected, setSelected] = useState<Poem | null>(null);
  const [copied, setCopied] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const resultRef = useRef<HTMLDivElement>(null);

  const stepsDone = useMemo(() => {
    return {
      key: useDemo || apiKey.trim().length > 8,
      doc: !!doc,
      poem: !!poem,
    };
  }, [useDemo, apiKey, doc, poem]);

  const progress = (stepsDone.key ? 1 : 0) + (stepsDone.doc ? 1 : 0) + (stepsDone.poem ? 1 : 0);

  const fetchLibrary = useCallback(async () => {
    setLoadingLib(true);
    try {
      const res = await fetch("/api/poems");
      const data = await res.json();
      setLibrary(Array.isArray(data.poems) ? data.poems : []);
    } catch {
      setLibrary([]);
    } finally {
      setLoadingLib(false);
    }
  }, []);

  useEffect(() => {
    fetchLibrary();
  }, [fetchLibrary]);

  useEffect(() => {
    if (apiKey.trim().length > 4) setUseDemo(false);
  }, [apiKey]);

  const handleFile = useCallback(async (file: File | undefined | null) => {
    if (!file) return;
    setDocError(null);
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/documents", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "No se pudo procesar el PDF.");
      setDoc(data as DocInfo);
      setPoem(null);
      setUsedFragments(null);
    } catch (e) {
      setDocError(e instanceof Error ? e.message : "Error al subir el PDF.");
    } finally {
      setUploading(false);
    }
  }, []);

  const handleGenerate = async () => {
    if (!doc) {
      setGenError("Primero sube un PDF para tener materia prima poética.");
      return;
    }
    if (topic.trim().length < 4) {
      setGenError("Cuéntanos el tema en una frase: ¿qué debería cantar el poema?");
      return;
    }
    setGenerating(true);
    setGenError(null);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          documentId: doc.id,
          topic: topic.trim(),
          tone,
          form,
          apiKey: useDemo ? "" : apiKey.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "No se pudo generar el poema.");
      setPoem(data.poem as Poem);
      setUsedFragments(data.usedFragments ?? null);
      fetchLibrary();
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    } catch (e) {
      setGenError(e instanceof Error ? e.message : "Error al generar.");
    } finally {
      setGenerating(false);
    }
  };

  const copyPoem = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  const deletePoem = async (id: number) => {
    setDeletingId(id);
    try {
      await fetch(`/api/poems/${id}`, { method: "DELETE" });
      setLibrary((prev) => prev.filter((p) => p.id !== id));
      if (selected?.id === id) setSelected(null);
    } finally {
      setDeletingId(null);
    }
  };

  const useExample = () => {
    setTopic("Un poema que transforme las ideas centrales del documento en una meditación sobre el tiempo y la memoria");
  };

  return (
    <div className="paper-grain min-h-screen">
      {/* Cinta superior */}
      <div className="bg-moss-deep text-[13px] text-[#f3ecdd]">
        <div className="mx-auto flex max-w-6xl items-center justify-center gap-2 px-4 py-2 text-center">
          <Sparkles className="h-3.5 w-3.5 text-[#e7c873]" />
          <p className="tracking-wide">
            Nuevo atelier: funciona <strong className="font-semibold">sin clave de API</strong> en modo demostración, o conecta OpenAI para versos con GPT-4o-mini.
          </p>
        </div>
      </div>

      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-line bg-paper/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <a href="#inicio" className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-clay text-white card-shadow">
              <Feather className="h-5 w-5" />
            </span>
            <span className="leading-tight">
              <span className="font-display block text-[19px] font-semibold tracking-tight">Trovador</span>
              <span className="block text-[11px] font-medium uppercase tracking-[0.18em] text-muted">Atelier · de PDF a poema</span>
            </span>
          </a>
          <nav className="hidden items-center gap-7 text-[14px] font-medium text-ink-soft md:flex">
            <a href="#taller" className="transition hover:text-clay">Taller</a>
            <a href="#biblioteca" className="transition hover:text-clay">Biblioteca</a>
            <a href="#como-funciona" className="transition hover:text-clay">Cómo funciona</a>
          </nav>
          <a
            href="#taller"
            className="group inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2.5 text-[13.5px] font-semibold text-white transition hover:bg-clay"
          >
            Crear poema
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </a>
        </div>
      </header>

      {/* HERO */}
      <section id="inicio" className="mx-auto max-w-6xl px-4 pt-10 pb-6 sm:px-6 sm:pt-14">
        <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="animate-rise">
            <p className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-3.5 py-1.5 text-[12px] font-semibold uppercase tracking-[0.16em] text-moss">
              <BookOpenText className="h-4 w-4" />
              RAG poético · Lectura que se vuelve canto
            </p>
            <h1 className="font-display mt-5 text-[clamp(2.4rem,5.2vw,3.9rem)] font-medium leading-[1.04] tracking-tight text-ink">
              Tus documentos,
              <br />
              convertidos en{" "}
              <span className="relative inline-block text-clay">
                poesía
                <svg viewBox="0 0 220 14" className="absolute -bottom-1 left-0 w-full" fill="none" aria-hidden>
                  <path d="M3 10C60 3 140 3 217 9" stroke="#b98a1f" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
                </svg>
              </span>{" "}
              viva.
            </h1>
            <p className="mt-5 max-w-xl text-[16.5px] leading-relaxed text-ink-soft">
              Sube un PDF, elige un tono y una forma literaria. El atelier lee los fragmentos más relevantes
              y compone un poema fiel a tus ideas — claro, estético y listo para compartir.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <a
                href="#taller"
                className="inline-flex items-center gap-2 rounded-full bg-clay px-6 py-3.5 text-[15px] font-semibold text-white card-shadow transition hover:bg-clay-deep"
              >
                <Wand2 className="h-4.5 w-4.5" />
                Empezar en el taller
              </a>
              <a
                href="#como-funciona"
                className="inline-flex items-center gap-2 rounded-full border border-line-strong bg-card px-6 py-3.5 text-[15px] font-semibold text-ink transition hover:border-ink"
              >
                <BookOpen className="h-4.5 w-4.5" />
                Ver cómo funciona
              </a>
            </div>
            <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-muted">
              <span className="inline-flex items-center gap-1.5"><CircleCheck className="h-4 w-4 text-moss" /> Sin registro</span>
              <span className="inline-flex items-center gap-1.5"><CircleCheck className="h-4 w-4 text-moss" /> Tu clave nunca se guarda</span>
              <span className="inline-flex items-center gap-1.5"><CircleCheck className="h-4 w-4 text-moss" /> Copia y descarga tus versos</span>
            </div>
          </div>

          {/* Tarjeta flotante */}
          <div className="relative animate-rise animate-rise-1">
            <div className="absolute -top-4 right-6 z-10 rotate-3 rounded-full bg-gold px-4 py-1.5 text-[12px] font-bold uppercase tracking-[0.14em] text-white card-shadow">
              ✦ Edición del día
            </div>
            <div className="animate-floaty rounded-[26px] border border-line bg-card p-7 card-shadow-lg sm:p-8">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-clay">Poema · Verso libre</p>
                <Quote className="h-5 w-5 text-line-strong" />
              </div>
              <p className="font-display mt-4 text-[26px] font-medium leading-tight">“Donde el papel respira”</p>
              <div className="ruled-lines mt-4 rounded-2xl border border-line bg-paper p-5">
                <p className="poem-verse text-[15.5px] text-ink">
                  Leí tu documento al caer la tarde,
                  <br />y cada idea encendió una lámpara;
                  <br />lo que era informe se hizo jardín,
                  <br />lo que era dato, golondrina.
                </p>
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                <span className="rounded-full bg-moss-soft px-3 py-1.5 text-[12px] font-semibold text-moss-deep">4 fragmentos leídos</span>
                <span className="rounded-full bg-clay-soft px-3 py-1.5 text-[12px] font-semibold text-clay-deep">Tono contemplativo</span>
                <span className="rounded-full bg-gold-soft px-3 py-1.5 text-[12px] font-semibold text-[#7a5c0a]">RAG fiel al texto</span>
              </div>
            </div>
            <div className="absolute -bottom-5 -left-3 flex -rotate-2 items-center gap-3 rounded-2xl border border-line bg-card px-4 py-3 card-shadow sm:-left-6">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-moss text-white"><Layers className="h-4.5 w-4.5" /></span>
              <span className="text-[13px] leading-tight"><strong>Fragmenta · Recupera · Compone</strong><br /><span className="text-muted">tres gestos, un poema</span></span>
            </div>
          </div>
        </div>

        {/* Indicador de progreso */}
        <div className="mt-12 rounded-3xl border border-line bg-card p-5 card-shadow sm:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="relative h-12 w-12">
                <svg viewBox="0 0 48 48" className="h-12 w-12 -rotate-90">
                  <circle cx="24" cy="24" r="20" fill="none" stroke="#e7dcc8" strokeWidth="5" />
                  <circle
                    cx="24" cy="24" r="20" fill="none" stroke="#bc4b26" strokeWidth="5" strokeLinecap="round"
                    strokeDasharray={`${(progress / 3) * 125.6} 125.6`}
                    className="transition-all duration-500"
                  />
                </svg>
                <span className="absolute inset-0 grid place-items-center text-[13px] font-bold">{progress}/3</span>
              </div>
              <div>
                <p className="text-[14px] font-bold">Tu progreso en el taller</p>
                <p className="text-[13px] text-muted">Completa los tres pasos para estrenar tu poema.</p>
              </div>
            </div>
            <ol className="flex flex-wrap items-center gap-2 text-[13px] font-semibold">
              <li className={`inline-flex items-center gap-2 rounded-full px-3.5 py-2 ${stepsDone.key ? "bg-moss text-white" : "bg-paper-deep text-ink-soft"}`}>
                {stepsDone.key ? <Check className="h-4 w-4" /> : <span className="grid h-5 w-5 place-items-center rounded-full bg-white text-[11px]">1</span>}
                Conexión
              </li>
              <li className={`inline-flex items-center gap-2 rounded-full px-3.5 py-2 ${stepsDone.doc ? "bg-moss text-white" : "bg-paper-deep text-ink-soft"}`}>
                {stepsDone.doc ? <Check className="h-4 w-4" /> : <span className="grid h-5 w-5 place-items-center rounded-full bg-white text-[11px]">2</span>}
                Documento
              </li>
              <li className={`inline-flex items-center gap-2 rounded-full px-3.5 py-2 ${stepsDone.poem ? "bg-moss text-white" : "bg-paper-deep text-ink-soft"}`}>
                {stepsDone.poem ? <Check className="h-4 w-4" /> : <span className="grid h-5 w-5 place-items-center rounded-full bg-white text-[11px]">3</span>}
                Poema
              </li>
            </ol>
          </div>
        </div>
      </section>

      {/* TALLER */}
      <main id="taller" className="mx-auto max-w-6xl scroll-mt-24 px-4 pb-4 sm:px-6">
        <div className="mt-8 flex items-end justify-between gap-4">
          <div>
            <p className="text-[12px] font-bold uppercase tracking-[0.22em] text-clay">El taller</p>
            <h2 className="font-display mt-1 text-[clamp(1.8rem,3.5vw,2.6rem)] font-medium tracking-tight">Tres pasos, cero complicaciones</h2>
          </div>
          <ArrowDown className="hidden h-6 w-6 text-line-strong sm:block" />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_380px]">
          <div className="space-y-6">
            {/* PASO 1 */}
            <section className="animate-rise rounded-3xl border border-line bg-card p-6 card-shadow sm:p-8">
              <div className="flex items-start gap-4">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-ink text-[16px] font-bold text-white">1</span>
                <div className="flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-display text-[21px] font-semibold">Conecta tu inspiración</h3>
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-bold ${useDemo ? "bg-gold-soft text-[#7a5c0a]" : "bg-moss-soft text-moss-deep"}`}>
                      {useDemo ? "Modo atelier (demo)" : "Modo OpenAI"}
                    </span>
                  </div>
                  <p className="mt-1 text-[14px] leading-relaxed text-ink-soft">
                    Puedes crear al instante sin clave, o pegar tu API key de OpenAI para versos con <em>gpt-4o-mini</em>. Tu clave solo vive en tu navegador.
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-[1fr_auto]">
                <label className="block">
                  <span className="mb-1.5 flex items-center gap-1.5 text-[13px] font-semibold text-ink-soft">
                    <KeyRound className="h-4 w-4" /> Clave de OpenAI <span className="font-normal text-muted">(opcional)</span>
                  </span>
                  <span className="relative block">
                    <input
                      type={showKey ? "text" : "password"}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="sk-… pega tu clave aquí"
                      disabled={useDemo}
                      className="w-full rounded-2xl border border-line bg-paper px-4 py-3 pr-12 text-[14px] outline-none transition placeholder:text-muted focus:border-clay focus:ring-2 focus:ring-clay/20 disabled:opacity-60"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-muted transition hover:bg-paper-deep hover:text-ink"
                      aria-label={showKey ? "Ocultar clave" : "Mostrar clave"}
                    >
                      {showKey ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
                    </button>
                  </span>
                </label>
                <div className="flex items-end">
                  <button
                    onClick={() => setUseDemo((v) => !v)}
                    className={`inline-flex items-center gap-2 rounded-2xl border px-4 py-3 text-[13.5px] font-semibold transition ${
                      useDemo ? "border-moss bg-moss-soft text-moss-deep" : "border-line bg-paper text-ink-soft hover:border-ink"
                    }`}
                  >
                    {useDemo ? <Check className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                    {useDemo ? "Demo activado" : "Usar demo"}
                  </button>
                </div>
              </div>
              <div className="mt-4 flex items-start gap-2 rounded-2xl bg-paper-deep/70 p-3.5 text-[13px] leading-relaxed text-ink-soft">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-moss" />
                <p>
                  <strong>¿Cuál elijo?</strong> El modo atelier compone con plantillas líricas a partir de tus fragmentos reales — perfecto para probar.
                  Con OpenAI obtienes metáforas más ricas y formas métricas precisas.
                </p>
              </div>
            </section>

            {/* PASO 2 */}
            <section className="animate-rise animate-rise-1 rounded-3xl border border-line bg-card p-6 card-shadow sm:p-8">
              <div className="flex items-start gap-4">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-clay text-[16px] font-bold text-white">2</span>
                <div>
                  <h3 className="font-display text-[21px] font-semibold">Sube tu documento</h3>
                  <p className="mt-1 text-[14px] text-ink-soft">Arrastra un PDF con texto seleccionable (hasta 15 MB). Lo leeremos y fragmentaremos al instante.</p>
                </div>
              </div>

              {!doc ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files?.[0]); }}
                  onClick={() => fileInputRef.current?.click()}
                  className={`mt-5 cursor-pointer rounded-3xl border-2 border-dashed p-8 text-center transition sm:p-10 ${
                    dragOver ? "border-clay bg-clay-soft" : "border-line-strong bg-paper hover:border-clay hover:bg-clay-soft/40"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="application/pdf,.pdf"
                    className="hidden"
                    onChange={(e) => handleFile(e.target.files?.[0])}
                  />
                  <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-ink text-white">
                    {uploading ? <RefreshCw className="h-6 w-6 animate-spin" /> : <UploadCloud className="h-6 w-6" />}
                  </span>
                  <p className="mt-4 text-[15px] font-bold">{uploading ? "Leyendo tu PDF…" : "Suelta tu PDF aquí o haz clic para elegirlo"}</p>
                  <p className="mt-1 text-[13px] text-muted">Extraemos páginas, caracteres y fragmentos automáticamente.</p>
                  {uploading && (
                    <div className="mx-auto mt-5 max-w-sm space-y-2">
                      <div className="shimmer-line h-2.5 rounded-full" />
                      <div className="shimmer-line h-2.5 w-2/3 rounded-full" />
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-5 rounded-3xl border border-line bg-paper p-5 sm:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-clay-soft text-clay-deep"><FileText className="h-5 w-5" /></span>
                      <div>
                        <p className="max-w-[260px] truncate text-[15px] font-bold sm:max-w-[340px]">{doc.filename}</p>
                        <p className="mt-0.5 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-moss-deep">
                          <CircleCheck className="h-4 w-4" /> Listo para poetizar
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => { setDoc(null); setPoem(null); }}
                      className="rounded-full border border-line bg-card px-4 py-2 text-[13px] font-semibold text-ink-soft transition hover:border-clay hover:text-clay"
                    >
                      Cambiar archivo
                    </button>
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    <div className="rounded-2xl border border-line bg-card p-3.5 text-center">
                      <p className="font-display text-[22px] font-semibold">{formatNum(doc.pageCount)}</p>
                      <p className="text-[11.5px] font-semibold uppercase tracking-wider text-muted">Páginas</p>
                    </div>
                    <div className="rounded-2xl border border-line bg-card p-3.5 text-center">
                      <p className="font-display text-[22px] font-semibold">{formatNum(doc.charCount)}</p>
                      <p className="text-[11.5px] font-semibold uppercase tracking-wider text-muted">Caracteres</p>
                    </div>
                    <div className="rounded-2xl border border-line bg-card p-3.5 text-center">
                      <p className="font-display text-[22px] font-semibold">{formatNum(doc.chunkCount)}</p>
                      <p className="text-[11.5px] font-semibold uppercase tracking-wider text-muted">Fragmentos</p>
                    </div>
                  </div>
                  {doc.excerpt && (
                    <div className="mt-4 rounded-2xl border border-line bg-card p-4">
                      <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted">Vista previa del texto</p>
                      <p className="dropcap mt-2 line-clamp-4 text-[13.5px] leading-relaxed text-ink-soft">{doc.excerpt}</p>
                    </div>
                  )}
                </div>
              )}
              {docError && (
                <p className="mt-4 flex items-start gap-2 rounded-2xl bg-[#fdeaea] p-3.5 text-[13.5px] font-medium text-[#8f1d1d]">
                  <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" /> {docError}
                </p>
              )}
            </section>

            {/* PASO 3 */}
            <section className="animate-rise animate-rise-2 rounded-3xl border border-line bg-card p-6 card-shadow sm:p-8">
              <div className="flex items-start gap-4">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-moss text-[16px] font-bold text-white">3</span>
                <div>
                  <h3 className="font-display text-[21px] font-semibold">Pide tu poema</h3>
                  <p className="mt-1 text-[14px] text-ink-soft">Describe el tema, elige el tono y la forma. Nosotros buscamos los fragmentos que mejor responden.</p>
                </div>
              </div>

              <label className="mt-5 block">
                <span className="mb-1.5 flex items-center justify-between text-[13px] font-semibold text-ink-soft">
                  Tema o enfoque del poema
                  <button onClick={useExample} className="font-semibold text-clay underline-offset-2 hover:underline">Probar ejemplo</button>
                </span>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  rows={3}
                  placeholder="Ejemplo: un poema melancólico que resuma las conclusiones clave del documento…"
                  className="w-full resize-none rounded-2xl border border-line bg-paper px-4 py-3 text-[14.5px] leading-relaxed outline-none transition placeholder:text-muted focus:border-clay focus:ring-2 focus:ring-clay/20"
                />
              </label>

              <div className="mt-5">
                <p className="text-[13px] font-semibold text-ink-soft">Tono <span className="font-normal text-muted">— {TONE_HINT[tone]}</span></p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {TONES.map((t) => (
                    <button
                      key={t}
                      onClick={() => setTone(t)}
                      className={`rounded-full px-4 py-2 text-[13.5px] font-semibold transition ${
                        tone === t ? "bg-ink text-white card-shadow" : "border border-line bg-paper text-ink-soft hover:border-ink hover:text-ink"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5">
                <p className="text-[13px] font-semibold text-ink-soft">Forma literaria</p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {FORMS.map((f) => (
                    <button
                      key={f}
                      onClick={() => setForm(f)}
                      className={`rounded-full px-4 py-2 text-[13.5px] font-semibold transition ${
                        form === f ? "bg-clay text-white card-shadow" : "border border-line bg-paper text-ink-soft hover:border-clay hover:text-clay"
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              {genError && (
                <p className="mt-4 flex items-start gap-2 rounded-2xl bg-[#fdeaea] p-3.5 text-[13.5px] font-medium text-[#8f1d1d]">
                  <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" /> {genError}
                </p>
              )}

              <button
                onClick={handleGenerate}
                disabled={generating || !doc}
                className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-ink px-6 py-4 text-[15.5px] font-bold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:opacity-50"
              >
                {generating ? (
                  <>
                    <RefreshCw className="h-5 w-5 animate-spin" />
                    El trovador está componiendo…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5" />
                    Generar poema
                  </>
                )}
              </button>
              {!doc && <p className="mt-2 text-center text-[12.5px] text-muted">Sube un PDF para activar la composición.</p>}
              {generating && (
                <div className="mt-4 space-y-2 rounded-2xl border border-line bg-paper p-5">
                  <div className="shimmer-line h-3 rounded-full" />
                  <div className="shimmer-line h-3 w-5/6 rounded-full" />
                  <div className="shimmer-line h-3 w-2/3 rounded-full" />
                  <p className="pt-1 text-[12.5px] text-muted">Buscando los 4 fragmentos más afines a tu tema…</p>
                </div>
              )}
            </section>
          </div>

          {/* Columna lateral */}
          <aside className="space-y-6 lg:sticky lg:top-24 lg:self-start">
            <div className="rounded-3xl border border-line bg-moss-deep p-6 text-[#f3ecdd] card-shadow">
              <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em]">
                <ScanText className="h-3.5 w-3.5" /> Cómo lee el atelier
              </p>
              <ol className="mt-4 space-y-4 text-[13.5px] leading-relaxed">
                <li className="flex gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#e7c873] text-[12px] font-bold text-moss-deep">1</span><span><strong>Fragmenta</strong> tu PDF en porciones de ~600 caracteres.</span></li>
                <li className="flex gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#e7c873] text-[12px] font-bold text-moss-deep">2</span><span><strong>Recupera</strong> los 4 fragmentos más afines a tu tema.</span></li>
                <li className="flex gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#e7c873] text-[12px] font-bold text-moss-deep">3</span><span><strong>Compone</strong> un poema fiel, con tu tono y forma.</span></li>
              </ol>
              <div className="stamp-border mt-5 rounded-2xl p-3.5 text-[12.5px] text-[#e7dcc8]">
                A esto se le llama <strong className="text-white">RAG</strong>: el poema nace de tu texto, no de la nada.
              </div>
            </div>

            <div className="rounded-3xl border border-line bg-card p-6 card-shadow">
              <h4 className="font-display text-[17px] font-semibold">Consejos de trovador</h4>
              <ul className="mt-3 space-y-2.5 text-[13.5px] leading-relaxed text-ink-soft">
                <li className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-moss" /> Sé específico: “las conclusiones sobre el clima” vence a “algo bonito”.</li>
                <li className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-moss" /> Prueba el mismo tema con dos tonos distintos.</li>
                <li className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-moss" /> El haiku ama lo breve; el romance, las historias.</li>
              </ul>
              <div className="mt-4 rounded-2xl bg-gold-soft p-3.5 text-[12.5px] leading-relaxed text-[#6b530a]">
                Cada poema se guarda automáticamente en tu biblioteca inferior.
              </div>
            </div>
          </aside>
        </div>

        {/* RESULTADO */}
        <div ref={resultRef} className="scroll-mt-28">
          {poem ? (
            <section className="animate-rise mt-6 overflow-hidden rounded-3xl border border-line bg-card card-shadow-lg">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-paper-deep/60 px-6 py-4 sm:px-8">
                <p className="inline-flex items-center gap-2 text-[12px] font-bold uppercase tracking-[0.2em] text-moss">
                  <Feather className="h-4 w-4" /> Poema resultante
                </p>
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-full bg-card px-3 py-1 text-[12px] font-bold text-ink-soft border border-line">{poem.form}</span>
                  <span className="rounded-full bg-card px-3 py-1 text-[12px] font-bold text-ink-soft border border-line">{poem.tone}</span>
                  <span className={`rounded-full px-3 py-1 text-[12px] font-bold ${poem.model === "gpt-4o-mini" ? "bg-moss text-white" : "bg-gold-soft text-[#7a5c0a]"}`}>
                    {poem.model === "gpt-4o-mini" ? "GPT-4o-mini" : "Modo atelier"}
                  </span>
                </div>
              </div>
              <div className="grid gap-0 md:grid-cols-[1fr_280px]">
                <div className="p-6 sm:p-9">
                  <p className="text-[12px] font-semibold text-muted">Inspirado en “{poem.documentName}” · {usedFragments ?? 4} fragmentos</p>
                  <p className="mt-1 text-[13px] italic text-ink-soft">Tema: “{poem.topic}”</p>
                  <div className="relative mt-5 rounded-3xl border border-line bg-paper p-6 sm:p-8">
                    <Quote className="absolute -top-4 left-6 h-8 w-8 rounded-full bg-clay p-1.5 text-white" />
                    <p className="poem-verse whitespace-pre-line text-ink">{poem.content}</p>
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2.5">
                    <button
                      onClick={() => copyPoem(poem.content)}
                      className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-[13.5px] font-bold text-white transition hover:bg-clay"
                    >
                      {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      {copied ? "¡Copiado!" : "Copiar versos"}
                    </button>
                    <button
                      onClick={() => downloadText(`poema-${poem.id}.txt`, `${poem.content}\n\n— Tema: ${poem.topic}\n— Fuente: ${poem.documentName}\n— Tono: ${poem.tone} · Forma: ${poem.form}`)}
                      className="inline-flex items-center gap-2 rounded-full border border-line-strong bg-card px-5 py-2.5 text-[13.5px] font-bold transition hover:border-ink"
                    >
                      <Download className="h-4 w-4" /> Descargar .txt
                    </button>
                    <button
                      onClick={() => { setPoem(null); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                      className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-[13.5px] font-bold text-muted transition hover:text-clay"
                    >
                      <RefreshCw className="h-4 w-4" /> Nuevo poema
                    </button>
                  </div>
                </div>
                <div className="border-t border-line bg-paper p-6 md:border-l md:border-t-0">
                  <p className="text-[12px] font-bold uppercase tracking-[0.18em] text-muted">Ficha del poema</p>
                  <dl className="mt-3 space-y-3 text-[13.5px]">
                    <div className="rounded-2xl border border-line bg-card p-3"><dt className="text-[11px] font-bold uppercase tracking-wider text-muted">Documento</dt><dd className="mt-0.5 font-semibold">{poem.documentName}</dd></div>
                    <div className="rounded-2xl border border-line bg-card p-3"><dt className="text-[11px] font-bold uppercase tracking-wider text-muted">Tono</dt><dd className="mt-0.5 font-semibold">{poem.tone}</dd></div>
                    <div className="rounded-2xl border border-line bg-card p-3"><dt className="text-[11px] font-bold uppercase tracking-wider text-muted">Forma</dt><dd className="mt-0.5 font-semibold">{poem.form}</dd></div>
                    <div className="rounded-2xl bg-moss-soft p-3 text-[12.5px] leading-relaxed text-moss-deep">
                      Fiel al texto: cada verso dialoga con los fragmentos recuperados de tu PDF.
                    </div>
                  </dl>
                </div>
              </div>
            </section>
          ) : (
            <section className="mt-6 rounded-3xl border border-dashed border-line-strong bg-card/60 p-8 text-center sm:p-10">
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-paper-deep text-muted"><Feather className="h-6 w-6" /></span>
              <p className="font-display mt-4 text-[20px] font-medium">Tu poema aparecerá aquí, sobre papel verjurado</p>
              <p className="mx-auto mt-1 max-w-md text-[13.5px] text-muted">Sube un documento, describe el tema y pulsa “Generar poema”. El atelier hará el resto.</p>
            </section>
          )}
        </div>

        {/* BIBLIOTECA */}
        <section id="biblioteca" className="mt-14 scroll-mt-24">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="inline-flex items-center gap-2 text-[12px] font-bold uppercase tracking-[0.22em] text-clay">
                <LibraryBig className="h-4 w-4" /> Biblioteca
              </p>
              <h2 className="font-display mt-1 text-[clamp(1.8rem,3.5vw,2.6rem)] font-medium tracking-tight">Tus versos guardados</h2>
              <p className="mt-1 text-[14px] text-ink-soft">Todo lo que compongas queda archivado aquí, como en un cuaderno de taller.</p>
            </div>
            <button
              onClick={fetchLibrary}
              className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-4 py-2 text-[13px] font-bold text-ink-soft transition hover:border-ink"
            >
              <RefreshCw className={`h-4 w-4 ${loadingLib ? "animate-spin" : ""}`} /> Actualizar
            </button>
          </div>

          {loadingLib ? (
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="rounded-3xl border border-line bg-card p-5 card-shadow">
                  <div className="shimmer-line h-4 w-2/3 rounded-full" />
                  <div className="shimmer-line mt-3 h-3 rounded-full" />
                  <div className="shimmer-line mt-2 h-3 w-5/6 rounded-full" />
                  <div className="shimmer-line mt-2 h-3 w-1/2 rounded-full" />
                </div>
              ))}
            </div>
          ) : library.length === 0 ? (
            <div className="mt-6 rounded-3xl border border-line bg-card p-10 text-center card-shadow">
              <BookOpen className="mx-auto h-8 w-8 text-line-strong" />
              <p className="font-display mt-3 text-[19px] font-medium">Aún no hay poemas en el estante</p>
              <p className="mx-auto mt-1 max-w-sm text-[13.5px] text-muted">Cuando generes tu primer poema, vivirá aquí con su ficha de tono, forma y documento de origen.</p>
            </div>
          ) : (
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {library.map((p) => (
                <article key={p.id} className="group flex flex-col rounded-3xl border border-line bg-card p-5 card-shadow transition hover:-translate-y-0.5 hover:card-shadow-lg">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${p.model === "gpt-4o-mini" ? "bg-moss-soft text-moss-deep" : "bg-gold-soft text-[#7a5c0a]"}`}>
                      {p.form} · {p.tone}
                    </span>
                    <button
                      onClick={() => deletePoem(p.id)}
                      disabled={deletingId === p.id}
                      className="rounded-lg p-1.5 text-muted opacity-0 transition group-hover:opacity-100 hover:bg-[#fdeaea] hover:text-[#8f1d1d] disabled:opacity-50"
                      aria-label="Eliminar poema"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <p className="mt-3 line-clamp-2 text-[13.5px] font-semibold leading-snug">“{p.topic}”</p>
                  <p className="font-display mt-2 line-clamp-4 whitespace-pre-line text-[13.5px] leading-relaxed text-ink-soft">{p.content}</p>
                  <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-[12px] text-muted">
                    <span className="max-w-[150px] truncate">{p.documentName}</span>
                    <button onClick={() => setSelected(p)} className="font-bold text-clay hover:underline">Leer entero →</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* CÓMO FUNCIONA */}
        <section id="como-funciona" className="mt-14 scroll-mt-24 rounded-[30px] border border-line bg-card p-7 card-shadow sm:p-10">
          <p className="text-[12px] font-bold uppercase tracking-[0.22em] text-clay">Comprender sin tecnicismos</p>
          <h2 className="font-display mt-1 text-[clamp(1.8rem,3.5vw,2.6rem)] font-medium tracking-tight">¿Qué es esto del RAG?</h2>
          <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-ink-soft">
            Piensa en un investigador que primero <strong>lee y subraya</strong> tu PDF, luego <strong>elige las páginas exactas</strong> que hablan de tu tema
            y finalmente <strong>se las dicta al poeta</strong>. El poema nunca inventa desde cero: canta desde tu texto.
          </p>
          <div className="mt-7 grid gap-4 md:grid-cols-3">
            <div className="rounded-3xl bg-paper p-6">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-ink text-white"><BookOpen className="h-5 w-5" /></span>
              <h3 className="font-display mt-4 text-[18px] font-semibold">1 · Lee con calma</h3>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-soft">Extraemos el texto del PDF y lo cortamos en fragmentos de lectura cómoda, como fichas de biblioteca.</p>
            </div>
            <div className="rounded-3xl bg-paper p-6">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-clay text-white"><ScanText className="h-5 w-5" /></span>
              <h3 className="font-display mt-4 text-[18px] font-semibold">2 · Subraya lo esencial</h3>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-soft">Comparamos tu tema con cada ficha y rescatamos las 4 que más resuenan. Sin humo, con criterio.</p>
            </div>
            <div className="rounded-3xl bg-paper p-6">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-moss text-white"><Feather className="h-5 w-5" /></span>
              <h3 className="font-display mt-4 text-[18px] font-semibold">3 · Canta tu tema</h3>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-soft">El poeta —demo o GPT-4o-mini— compone con tu tono y forma, mirando siempre a los fragmentos.</p>
            </div>
          </div>
          <div className="mt-6 flex flex-col items-start justify-between gap-4 rounded-3xl bg-moss-deep p-6 text-[#f3ecdd] sm:flex-row sm:items-center">
            <p className="max-w-xl text-[14px] leading-relaxed">
              <strong>Diferencia con el original:</strong> antes todo era un fondo oscuro difícil de escanear. Ahora cada paso respira,
              los estados son visibles y el poema se presenta como una página de libro, no como un bloque de código.
            </p>
            <a href="#taller" className="inline-flex shrink-0 items-center gap-2 rounded-full bg-[#e7c873] px-5 py-3 text-[14px] font-bold text-moss-deep transition hover:bg-white">
              Volver al taller <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="flex flex-col items-center justify-between gap-4 border-t border-line pt-7 text-[13px] text-muted sm:flex-row">
          <p className="flex items-center gap-2">
            <Feather className="h-4 w-4" />
            Trovador · Atelier de poesía — de PDF a poema, con cariño por la palabra.
          </p>
          <p>RAG fiel al texto · Tu clave nunca se almacena · {new Date().getFullYear()}</p>
        </div>
      </footer>

      {/* Modal lectura */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 p-0 backdrop-blur-sm sm:items-center sm:p-6" onClick={() => setSelected(null)}>
          <div
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-t-[28px] bg-card p-7 card-shadow-lg sm:rounded-[28px] sm:p-9"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-clay">{selected.form} · {selected.tone}</p>
                <p className="font-display mt-1 text-[22px] font-medium leading-tight">“{selected.topic}”</p>
                <p className="mt-1 text-[12.5px] text-muted">Desde “{selected.documentName}”</p>
              </div>
              <button onClick={() => setSelected(null)} className="rounded-full border border-line p-2 text-muted transition hover:border-ink hover:text-ink" aria-label="Cerrar">
                <X className="h-4.5 w-4.5" />
              </button>
            </div>
            <div className="mt-5 rounded-3xl border border-line bg-paper p-6">
              <p className="poem-verse whitespace-pre-line text-[15.5px]">{selected.content}</p>
            </div>
            <div className="mt-5 flex flex-wrap gap-2.5">
              <button
                onClick={() => copyPoem(selected.content)}
                className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-[13.5px] font-bold text-white hover:bg-clay"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />} {copied ? "¡Copiado!" : "Copiar"}
              </button>
              <button
                onClick={() => downloadText(`poema-${selected.id}.txt`, selected.content)}
                className="inline-flex items-center gap-2 rounded-full border border-line-strong px-5 py-2.5 text-[13.5px] font-bold hover:border-ink"
              >
                <Download className="h-4 w-4" /> Descargar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
