"use client";

import { useState } from "react";
import { Beaker, BookOpen, FlaskConical, Loader2, Map, Sparkles, X } from "lucide-react";
import { api, Paper } from "@/lib/api";
import AutoResearchPanel from "@/components/AutoResearchPanel";
import ScientistPanel from "@/components/ScientistPanel";

interface ResearchToolsDrawerProps {
  open: boolean;
  onClose: () => void;
  onRunPrompt: (prompt: string) => void;
}

export default function ResearchToolsDrawer({ open, onClose, onRunPrompt }: ResearchToolsDrawerProps) {
  const [tab, setTab] = useState<"tools" | "autoresearch" | "scientist">("tools");
  const [planTopic, setPlanTopic] = useState("");
  const [paperQuery, setPaperQuery] = useState("");
  const [expTopic, setExpTopic] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadingPapers, setLoadingPapers] = useState(false);
  const [loadingExp, setLoadingExp] = useState(false);
  const [planPreview, setPlanPreview] = useState<string | null>(null);

  if (!open) return null;

  const generatePlan = async () => {
    if (!planTopic.trim()) return;
    setLoadingPlan(true);
    try {
      const plan = await api.createPlan(planTopic.trim());
      setPlanPreview(
        `${plan.research_question}\n\n${plan.tasks.map((t) => `• ${t.title}`).join("\n")}`
      );
      onRunPrompt(`create a research plan for ${planTopic.trim()}`);
    } catch {
      setPlanPreview("生成失败，请检查后端连接。");
    } finally {
      setLoadingPlan(false);
    }
  };

  const searchPapers = async () => {
    if (!paperQuery.trim()) return;
    setLoadingPapers(true);
    try {
      const res = await api.searchPapers(paperQuery.trim(), 5);
      setPapers(res.papers);
    } catch {
      setPapers([]);
    } finally {
      setLoadingPapers(false);
    }
  };

  const designExperiment = async () => {
    if (!expTopic.trim()) return;
    setLoadingExp(true);
    try {
      await api.designExperiment(expTopic.trim());
      onRunPrompt(`design an experiment for ${expTopic.trim()}`);
      onClose();
    } catch {
      /* ignore */
    } finally {
      setLoadingExp(false);
    }
  };

  const tools = [
    {
      icon: Map,
      title: "研究规划",
      desc: "生成 Research Roadmap 与任务拆解",
      action: generatePlan,
      loading: loadingPlan,
      input: planTopic,
      setInput: setPlanTopic,
      placeholder: "输入研究主题...",
      btn: "生成规划",
    },
    {
      icon: BookOpen,
      title: "论文检索",
      desc: "arXiv 论文搜索与摘要",
      action: searchPapers,
      loading: loadingPapers,
      input: paperQuery,
      setInput: setPaperQuery,
      placeholder: "搜索关键词...",
      btn: "搜索",
    },
    {
      icon: Beaker,
      title: "实验设计",
      desc: "Baseline、指标、Ablation 设计",
      action: designExperiment,
      loading: loadingExp,
      input: expTopic,
      setInput: setExpTopic,
      placeholder: "实验主题...",
      btn: "设计实验",
    },
    {
      icon: Sparkles,
      title: "AI Scientist",
      desc: "全自动科研闭环（流式进度）",
      action: () => setTab("scientist"),
      loading: false,
      input: "",
      setInput: () => {},
      placeholder: "",
      btn: "打开",
      noInput: true,
    },
  ];

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/30" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-[var(--background)] border-l border-[var(--border)] shadow-xl flex flex-col animate-in slide-in-from-right">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <div className="flex gap-1 p-1 rounded-full bg-[var(--hover)]">
            <button
              onClick={() => setTab("tools")}
              className={`px-3 py-1 rounded-full text-xs ${tab === "tools" ? "bg-[var(--card)] shadow-sm" : ""}`}
            >
              科研工具
            </button>
            <button
              onClick={() => setTab("autoresearch")}
              className={`px-3 py-1 rounded-full text-xs flex items-center gap-1 ${tab === "autoresearch" ? "bg-[var(--card)] shadow-sm" : ""}`}
            >
              <FlaskConical className="w-3 h-3" /> AutoResearch
            </button>
            <button
              onClick={() => setTab("scientist")}
              className={`px-3 py-1 rounded-full text-xs flex items-center gap-1 ${tab === "scientist" ? "bg-[var(--card)] shadow-sm" : ""}`}
            >
              <Sparkles className="w-3 h-3" /> Scientist
            </button>
          </div>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-[var(--hover)] text-[var(--muted)]">
            <X className="w-5 h-5" />
          </button>
        </div>

        {tab === "autoresearch" ? (
          <AutoResearchPanel />
        ) : tab === "scientist" ? (
          <div className="flex-1 overflow-y-auto">
            <ScientistPanel />
          </div>
        ) : (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {tools.map((t) => (
            <div
              key={t.title}
              className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4"
            >
              <div className="flex items-start gap-3 mb-3">
                <div className="w-9 h-9 rounded-full bg-[var(--hover)] flex items-center justify-center shrink-0">
                  <t.icon className="w-4 h-4 text-[var(--foreground)]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[var(--foreground)]">{t.title}</p>
                  <p className="text-xs text-[var(--muted)] mt-0.5">{t.desc}</p>
                </div>
              </div>
              {!t.noInput && (
                <div className="flex gap-2">
                  <input
                    value={t.input}
                    onChange={(e) => t.setInput(e.target.value)}
                    placeholder={t.placeholder}
                    className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-full px-4 py-2 text-sm focus:outline-none focus:border-[var(--border-focus)]"
                  />
                  <button
                    onClick={t.action}
                    disabled={t.loading}
                    className="px-4 py-2 rounded-full bg-[var(--foreground)] text-[var(--background)] text-sm hover:opacity-90 disabled:opacity-40 transition-opacity"
                  >
                    {t.loading ? <Loader2 className="w-4 h-4 animate-spin" /> : t.btn}
                  </button>
                </div>
              )}
              {t.noInput && (
                <button
                  onClick={t.action}
                  className="w-full py-2 rounded-full bg-[var(--foreground)] text-[var(--background)] text-sm hover:opacity-90"
                >
                  {t.btn}
                </button>
              )}
            </div>
          ))}

          {planPreview && (
            <pre className="text-xs bg-[var(--hover)] rounded-2xl p-4 whitespace-pre-wrap text-[var(--foreground)]">
              {planPreview}
            </pre>
          )}

          {papers.length > 0 && (
            <div className="space-y-2">
              {papers.map((p) => (
                <a
                  key={p.arxiv_id}
                  href={p.pdf_url || `https://arxiv.org/abs/${p.arxiv_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs border border-[var(--border)] rounded-xl p-3 hover:bg-[var(--hover)] transition-colors"
                >
                  <p className="font-medium text-[var(--foreground)] mb-1">{p.title}</p>
                  <p className="text-[var(--muted)] line-clamp-2">{p.abstract}</p>
                </a>
              ))}
            </div>
          )}
        </div>
        )}
      </div>
    </>
  );
}
