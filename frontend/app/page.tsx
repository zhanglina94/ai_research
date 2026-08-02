"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { api, Project } from "@/lib/api";
import ChatPanel from "@/components/ChatPanel";
import Sidebar from "@/components/Sidebar";
import CanvasPanel from "@/components/CanvasPanel";
import ResearchToolsDrawer from "@/components/ResearchToolsDrawer";

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [chatResetKey, setChatResetKey] = useState(0);
  const [prefill, setPrefill] = useState("");
  const [recentChats, setRecentChats] = useState<string[]>([]);
  const [canvasOpen, setCanvasOpen] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);

  useEffect(() => {
    const checkHealth = () =>
      api.health()
        .then(() => setBackendOk(true))
        .catch(() => setBackendOk(false));

    checkHealth();
    const timer = setInterval(() => {
      checkHealth();
    }, 15000);

    api
      .listProjects()
      .then(setProjects)
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));

    const saved = localStorage.getItem("recentChats");
    if (saved) {
      try {
        setRecentChats(JSON.parse(saved));
      } catch {
        /* ignore */
      }
    }

    return () => clearInterval(timer);
  }, []);

  const handleNewChat = () => {
    setChatResetKey((k) => k + 1);
    setPrefill("");
    setMobileSidebarOpen(false);
  };

  const handleQuickAction = (prompt: string) => {
    setPrefill(prompt);
    setMobileSidebarOpen(false);
  };

  const handleChatSent = useCallback((title: string) => {
    setRecentChats((prev) => {
      const next = [title, ...prev.filter((t) => t !== title)].slice(0, 10);
      localStorage.setItem("recentChats", JSON.stringify(next));
      return next;
    });
  }, []);

  return (
    <div className="h-full min-h-screen flex bg-[var(--background)] text-[var(--foreground)]">
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      <div
        className={clsx(
          "fixed inset-y-0 left-0 z-40 lg:relative lg:z-auto h-full transition-transform duration-200",
          mobileSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
          onNewChat={handleNewChat}
          onQuickAction={handleQuickAction}
          onOpenLibrary={() => setToolsOpen(true)}
          projects={projects}
          loading={loading}
          recentChats={recentChats}
        />
      </div>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 min-h-0 relative">
        {/* Backend status pill */}
        <div className="absolute top-3 right-4 z-10 flex items-center gap-1.5 text-xs text-[var(--muted)] bg-[var(--card)] border border-[var(--border)] rounded-full px-3 py-1">
          <span
            className={clsx(
              "w-1.5 h-1.5 rounded-full",
              backendOk === null ? "bg-yellow-400" : backendOk ? "bg-green-500" : "bg-red-500"
            )}
          />
          {backendOk === null ? "连接中" : backendOk ? "后端在线" : "后端离线"}
        </div>

        <ChatPanel
          resetKey={chatResetKey}
          prefill={prefill}
          onPrefillConsumed={() => setPrefill("")}
          onChatSent={handleChatSent}
          onMenuClick={() => setMobileSidebarOpen(true)}
          onOpenCanvas={() => setCanvasOpen(true)}
          onOpenTools={() => setToolsOpen(true)}
        />
      </main>

      <CanvasPanel open={canvasOpen} onClose={() => setCanvasOpen(false)} />
      <ResearchToolsDrawer
        open={toolsOpen}
        onClose={() => setToolsOpen(false)}
        onRunPrompt={(prompt) => {
          setPrefill(prompt);
          setToolsOpen(false);
        }}
      />
    </div>
  );
}
