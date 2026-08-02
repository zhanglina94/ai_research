"use client";

import { useState } from "react";
import { Check, Loader2, Play, RefreshCw, X } from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";

interface AutoResearchPanelProps {
  onClose?: () => void;
}

export default function AutoResearchPanel({ onClose }: AutoResearchPanelProps) {
  const [topic, setTopic] = useState("");
  const [budget, setBudget] = useState(30);
  const [maxIter, setMaxIter] = useState(5);
  const [loading, setLoading] = useState(false);
  const [experimentId, setExperimentId] = useState<string | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.runAutoResearch>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runFull = async () => {
    if (!topic.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const init = await api.initAutoResearch(topic.trim(), {
        trainBudgetSeconds: budget,
        maxIterations: maxIter,
      });
      setExperimentId(init.experiment_id);
      const res = await api.runAutoResearch(init.experiment_id, {
        maxIterations: maxIter,
        trainBudgetSeconds: budget,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "AutoResearch 失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
        <div>
          <h2 className="text-base font-medium text-[var(--foreground)]">AutoResearch</h2>
          <p className="text-xs text-[var(--muted)] mt-0.5">
            改 train.py → 固定时长训练 → val_bpb 评估 → keep/discard
          </p>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-2 rounded-full hover:bg-[var(--hover)] text-[var(--muted)]">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 space-y-3">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="研究主题，例如：优化小型 LM 的 val_bpb"
            className="w-full bg-[var(--background)] border border-[var(--border)] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-[var(--border-focus)]"
          />
          <div className="flex gap-3">
            <label className="flex-1 text-xs text-[var(--muted)]">
              训练预算 (秒)
              <input
                type="number"
                min={5}
                max={3600}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="mt-1 w-full bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-sm text-[var(--foreground)]"
              />
            </label>
            <label className="flex-1 text-xs text-[var(--muted)]">
              最大迭代
              <input
                type="number"
                min={1}
                max={100}
                value={maxIter}
                onChange={(e) => setMaxIter(Number(e.target.value))}
                className="mt-1 w-full bg-[var(--background)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-sm text-[var(--foreground)]"
              />
            </label>
          </div>
          <button
            onClick={runFull}
            disabled={loading || !topic.trim()}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-full bg-[var(--foreground)] text-[var(--background)] text-sm hover:opacity-90 disabled:opacity-40"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            启动 AutoResearch
          </button>
        </div>

        {error && (
          <p className="text-xs text-red-500 bg-red-500/10 rounded-xl px-4 py-3">{error}</p>
        )}

        {experimentId && (
          <p className="text-xs text-[var(--muted)]">
            Experiment ID: <code className="text-[var(--foreground)]">{experimentId}</code>
          </p>
        )}

        {result && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <RefreshCw className="w-4 h-4 text-[var(--accent)]" />
              <span>
                完成 {result.iteration_count} 轮 · best{" "}
                <strong className="text-[var(--accent)]">{result.best_metric?.toFixed(4) ?? "—"}</strong>{" "}
                {result.primary_metric} (越低越好)
              </span>
            </div>

            <div className="space-y-1.5">
              {result.iterations.map((it) => (
                <div
                  key={it.iteration}
                  className={clsx(
                    "flex items-center justify-between text-xs rounded-xl px-3 py-2 border",
                    it.kept
                      ? "border-[var(--accent)]/30 bg-[var(--pill-active)]"
                      : "border-[var(--border)] bg-[var(--card)]"
                  )}
                >
                  <span className="text-[var(--foreground)]">
                    iter {it.iteration}
                    {it.val_bpb != null && ` · val_bpb=${it.val_bpb.toFixed(4)}`}
                  </span>
                  <span className="flex items-center gap-1 text-[var(--muted)]">
                    {it.kept ? (
                      <>
                        <Check className="w-3 h-3 text-[var(--accent)]" /> keep
                      </>
                    ) : (
                      "discard"
                    )}
                  </span>
                </div>
              ))}
            </div>

            <a
              href="http://localhost:5000"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-[var(--accent)] hover:underline"
            >
              在 MLflow 查看实验记录 →
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
