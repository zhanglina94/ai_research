const API_URL = process.env.NEXT_PUBLIC_API_URL || "/backend";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Request failed: ${res.status}`);
  }
  return res.json();
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

export interface Project {
  id: string;
  title: string;
  topic: string;
  status: string;
  created_at: string;
}

export interface Paper {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published?: string;
  pdf_url?: string;
}

export const api = {
  health: () => request<{ status: string; app: string }>("/health"),

  chat: (message: string, sessionId?: string, projectId?: string) =>
    request<{ reply: string; session_id: string; agent?: string }>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId, project_id: projectId }),
    }),

  createPlan: (topic: string) =>
    request<{
      research_question: string;
      tasks: { title: string; description: string; priority: string; estimated_days: number }[];
      timeline: string;
      directions: string[];
      project_id?: string;
    }>("/api/v1/research/plan", {
      method: "POST",
      body: JSON.stringify({ topic }),
    }),

  searchPapers: (query: string, maxResults = 10) =>
    request<{ query: string; papers: Paper[]; total: number }>("/api/v1/papers/search", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults }),
    }),

  listProjects: () => request<Project[]>("/api/v1/projects"),

  createProject: (title: string, topic: string) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ title, topic }),
    }),

  designExperiment: (topic: string, projectId?: string) =>
    request<{
      experiment_id: string;
      hypothesis: string;
      datasets: { name: string; reason: string }[];
      baselines: { name: string; description: string }[];
      metrics: { name: string; description: string }[];
      ablations: { name: string; variable: string; values: string[] }[];
      training_config: Record<string, number>;
    }>("/api/v1/experiments/design", {
      method: "POST",
      body: JSON.stringify({ topic, project_id: projectId }),
    }),

  runScientist: (idea: string, projectId?: string) =>
    request<{
      run_id: string;
      status: string;
      current_step: string;
      plan?: Record<string, unknown>;
      experiment_spec?: Record<string, unknown>;
      run_result?: { metrics?: Record<string, number>; status?: string };
      analysis?: Record<string, unknown>;
      paper_draft?: string;
    }>("/api/v1/scientist/run", {
      method: "POST",
      body: JSON.stringify({ idea, project_id: projectId }),
    }),

  streamScientist: async function* (
    idea: string,
    projectId?: string
  ): AsyncGenerator<Record<string, unknown>> {
    const res = await fetch(`${API_URL}/api/v1/scientist/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea, project_id: projectId }),
    });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const line = part.trim();
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6));
          } catch {
            /* skip malformed */
          }
        }
      }
    }
  },

  getExperimentRuntime: () =>
    request<{
      training_mode: string;
      use_gpu: boolean;
      use_docker: boolean;
      docker_available: boolean;
      docker_image: string;
      gpu: { available: boolean; device: string; device_name?: string };
    }>("/api/v1/experiments/runtime"),

  getKnowledgeGraph: () =>
    request<{ nodes: { type: string; id: string; label: string }[]; edges: { source: string; target: string; relation: string }[] }>(
      "/api/v1/knowledge/graph"
    ),

  listExperiments: (projectId?: string) =>
    request<{ id: string; name: string; status: string; metrics?: Record<string, number> }[]>(
      `/api/v1/experiments${projectId ? `?project_id=${projectId}` : ""}`
    ),

  initAutoResearch: (
    topic: string,
    opts?: { trainBudgetSeconds?: number; maxIterations?: number; projectId?: string }
  ) =>
    request<{
      experiment_id: string;
      experiment_dir: string;
      program_path: string;
      train_path: string;
      prepare_status: string;
      primary_metric: string;
    }>("/api/v1/experiments/autoresearch/init", {
      method: "POST",
      body: JSON.stringify({
        topic,
        project_id: opts?.projectId,
        train_budget_seconds: opts?.trainBudgetSeconds ?? 300,
        max_iterations: opts?.maxIterations ?? 12,
      }),
    }),

  runAutoResearch: (
    experimentId: string,
    opts?: { maxIterations?: number; trainBudgetSeconds?: number }
  ) =>
    request<{
      experiment_id: string;
      status: string;
      best_metric: number | null;
      primary_metric: string;
      iteration_count: number;
      iterations: {
        iteration: number;
        val_bpb?: number;
        kept: boolean;
        status?: string;
        best_metric?: number;
      }[];
      experiment_dir: string;
    }>(`/api/v1/experiments/${experimentId}/autoresearch`, {
      method: "POST",
      body: JSON.stringify({
        max_iterations: opts?.maxIterations,
        train_budget_seconds: opts?.trainBudgetSeconds,
      }),
    }),

  listAutoResearchIterations: (experimentId: string) =>
    request<
      {
        iteration: number;
        val_bpb?: number;
        kept: boolean;
        status?: string;
        best_metric?: number;
      }[]
    >(`/api/v1/experiments/${experimentId}/iterations`),

  generateExperimentCode: (experimentId: string, spec?: Record<string, unknown>) =>
    request<{ experiment_id: string; experiment_dir: string; written_paths: string[] }>(
      "/api/v1/experiments/code",
      {
        method: "POST",
        body: JSON.stringify({ experiment_id: experimentId, spec: spec ?? {} }),
      }
    ),

  runExperiment: (experimentId: string) =>
    request<{ experiment_id: string; run_result: Record<string, unknown> }>("/api/v1/experiments/run", {
      method: "POST",
      body: JSON.stringify({ experiment_id: experimentId }),
    }),

  listMlflowExperiments: () =>
    request<{ experiment_id: string; name: string; lifecycle_stage: string }[]>("/api/v1/experiments/mlflow"),
};
