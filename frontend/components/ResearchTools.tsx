"use client";

import { useState } from "react";
import { BookOpen, Map, Loader2 } from "lucide-react";
import { api, Paper } from "@/lib/api";

export default function ResearchTools() {
  const [planTopic, setPlanTopic] = useState("");
  const [planResult, setPlanResult] = useState<string | null>(null);
  const [paperQuery, setPaperQuery] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadingPapers, setLoadingPapers] = useState(false);

  const generatePlan = async () => {
    if (!planTopic.trim()) return;
    setLoadingPlan(true);
    try {
      const plan = await api.createPlan(planTopic.trim());
      setPlanResult(
        `**${plan.research_question}**\n\nTimeline: ${plan.timeline}\n\n` +
          plan.tasks.map((t) => `- **${t.title}** (${t.estimated_days}d): ${t.description}`).join("\n") +
          `\n\nDirections:\n` +
          plan.directions.map((d) => `- ${d}`).join("\n")
      );
    } catch {
      setPlanResult("Failed to generate plan. Check backend connection.");
    } finally {
      setLoadingPlan(false);
    }
  };

  const searchPapers = async () => {
    if (!paperQuery.trim()) return;
    setLoadingPapers(true);
    try {
      const res = await api.searchPapers(paperQuery.trim());
      setPapers(res.papers);
    } catch {
      setPapers([]);
    } finally {
      setLoadingPapers(false);
    }
  };

  return (
    <div className="space-y-6 p-4">
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Map className="w-4 h-4 text-brand-500" />
          <h3 className="text-sm font-semibold">Research Plan</h3>
        </div>
        <div className="flex gap-2">
          <input
            value={planTopic}
            onChange={(e) => setPlanTopic(e.target.value)}
            placeholder="Research topic..."
            className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
          />
          <button
            onClick={generatePlan}
            disabled={loadingPlan}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-40 rounded-lg px-3 py-2 text-sm transition-colors"
          >
            {loadingPlan ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate"}
          </button>
        </div>
        {planResult && (
          <pre className="mt-3 text-xs bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 whitespace-pre-wrap leading-relaxed">
            {planResult.replace(/\*\*/g, "")}
          </pre>
        )}
      </section>

      <section>
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-brand-500" />
          <h3 className="text-sm font-semibold">Paper Search (arXiv)</h3>
        </div>
        <div className="flex gap-2">
          <input
            value={paperQuery}
            onChange={(e) => setPaperQuery(e.target.value)}
            placeholder="Search query..."
            className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
          />
          <button
            onClick={searchPapers}
            disabled={loadingPapers}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-40 rounded-lg px-3 py-2 text-sm transition-colors"
          >
            {loadingPapers ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
          </button>
        </div>
        <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
          {papers.map((p) => (
            <a
              key={p.arxiv_id}
              href={p.pdf_url || `https://arxiv.org/abs/${p.arxiv_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 hover:border-brand-500 transition-colors"
            >
              <p className="font-medium mb-1">{p.title}</p>
              <p className="text-gray-400 line-clamp-2">{p.abstract}</p>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
