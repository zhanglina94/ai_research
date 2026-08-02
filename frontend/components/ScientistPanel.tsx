"use client";

import { useEffect, useState } from "react";
import { Atom, Loader2, Play } from "lucide-react";
import { api } from "@/lib/api";

const STEPS = ["idea", "experiment", "autoresearch", "analyze", "paper", "done"];

type StreamEvent = Record<string, unknown>;

export default function ScientistPanel() {
  const [idea, setIdea] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState("");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.runScientist>> | null>(null);
  const [runtime, setRuntime] = useState<Awaited<ReturnType<typeof api.getExperimentRuntime>> | null>(null);

  useEffect(() => {
    api.getExperimentRuntime().then(setRuntime).catch(() => setRuntime(null));
  }, []);

  const runLoop = async () => {
    if (!idea.trim() || loading) return;
    setLoading(true);
    setResult(null);
    setEvents([]);
    setCurrentStep("idea");

    try {
      for await (const event of api.streamScientist(idea.trim())) {
        setEvents((prev) => [...prev.slice(-50), event]);
        if (event.event === "step_start" && typeof event.step === "string") {
          setCurrentStep(event.step);
        }
        if (event.event === "step_done" && typeof event.step === "string") {
          setCurrentStep(event.step);
        }
        if (event.event === "iteration_done") {
          setCurrentStep("autoresearch");
        }
        if (event.event === "complete" && event.result) {
          setResult(event.result as typeof result);
          setCurrentStep("done");
        }
        if (event.event === "error") {
          break;
        }
      }
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const stepIndex = STEPS.indexOf(currentStep);
  const iterations = events.filter((e) => e.event === "iteration_done");

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-2">
        <Atom className="w-4 h-4 text-[var(--foreground)]" />
        <h3 className="text-sm font-semibold text-[var(--foreground)]">AI Scientist Loop</h3>
      </div>
      <p className="text-xs text-[var(--muted)]">
        Idea → Experiment → AutoResearch → Analyze → Paper（SSE 流式进度）
      </p>

      {runtime && (
        <div className="text-[10px] text-[var(--muted)] rounded-xl bg-[var(--hover)] px-3 py-2 space-y-0.5">
          <p>
            训练模式: {runtime.training_mode} · GPU: {runtime.gpu.available ? runtime.gpu.device_name || runtime.gpu.device : "不可用"}
          </p>
          <p>
            Docker 隔离: {runtime.use_docker ? "开启" : "关闭"}
            {runtime.use_docker && !runtime.docker_available ? "（Docker 未安装）" : ""}
          </p>
        </div>
      )}

      <div className="flex gap-2">
        <input
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="研究想法..."
          className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-full px-4 py-2 text-sm focus:outline-none focus:border-[var(--border-focus)]"
        />
        <button
          onClick={runLoop}
          disabled={loading}
          className="px-4 py-2 rounded-full bg-[var(--foreground)] text-[var(--background)] text-sm hover:opacity-90 disabled:opacity-40 flex items-center gap-1"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          运行
        </button>
      </div>

      {(loading || result) && (
        <div className="flex gap-1">
          {STEPS.slice(0, -1).map((step, i) => (
            <div
              key={step}
              title={step}
              className={`flex-1 h-1 rounded-full ${i <= stepIndex ? "bg-[var(--foreground)]" : "bg-[var(--border)]"}`}
            />
          ))}
        </div>
      )}

      {iterations.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-[var(--foreground)]">AutoResearch 迭代</p>
          {iterations.map((it, idx) => (
            <div key={idx} className="text-[10px] text-[var(--muted)] flex justify-between">
              <span>iter {String(it.iteration)}</span>
              <span>
                val_bpb={String(it.val_bpb ?? "—")} {it.kept ? "✓ kept" : "✗ discard"}
              </span>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div className="space-y-2">
          <div className="text-xs px-2 py-1 rounded-full bg-green-500/10 text-green-600 dark:text-green-400 inline-block">
            {result.status} — {result.current_step}
          </div>
          {result.run_result?.metrics && (
            <pre className="text-xs bg-[var(--hover)] rounded-xl p-3 overflow-x-auto">
              {JSON.stringify(result.run_result.metrics, null, 2)}
            </pre>
          )}
          {result.paper_draft && (
            <pre className="text-xs bg-[var(--hover)] rounded-xl p-3 max-h-40 overflow-y-auto whitespace-pre-wrap">
              {result.paper_draft.slice(0, 1200)}
              {result.paper_draft.length > 1200 ? "\n..." : ""}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
