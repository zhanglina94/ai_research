"use client";

import {
  Beaker,
  BookOpen,
  FlaskConical,
  LayoutGrid,
  Loader2,
  Map,
  PanelLeftClose,
  PanelLeftOpen,
  PenLine,
  Search,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { useMemo, useState } from "react";
import { Project } from "@/lib/api";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/lib/theme";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onNewChat: () => void;
  onQuickAction: (prompt: string) => void;
  onOpenLibrary?: () => void;
  projects: Project[];
  loading: boolean;
  recentChats: string[];
}

const NAV_ITEMS = [
  { icon: Sparkles, label: "深度调研", prompt: "请对该主题进行深度调研：", highlight: true },
  { icon: BookOpen, label: "论文库", prompt: "search papers about " },
  { icon: LayoutGrid, label: "项目库", action: "library" as const },
  { icon: Map, label: "研究规划", prompt: "create a research plan for " },
  { icon: Beaker, label: "实验设计", prompt: "design an experiment for " },
];

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  onNewChat,
  onQuickAction,
  onOpenLibrary,
  projects,
  loading,
  recentChats,
}: SidebarProps) {
  const { theme } = useTheme();
  const [search, setSearch] = useState("");

  const filteredChats = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return recentChats;
    return recentChats.filter((t) => t.toLowerCase().includes(q));
  }, [recentChats, search]);

  const filteredProjects = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = projects.slice(0, 8);
    if (!q) return list;
    return list.filter(
      (p) => p.title.toLowerCase().includes(q) || p.topic.toLowerCase().includes(q)
    );
  }, [projects, search]);

  return (
    <aside
      className={clsx(
        "h-full flex flex-col bg-[var(--sidebar)] border-r border-[var(--border)] transition-all duration-200 overflow-hidden",
        collapsed ? "w-[52px]" : "w-[280px]"
      )}
    >
      {/* Header — Gemini style */}
      <div className="flex items-center justify-between px-3 pt-4 pb-2 shrink-0">
        {!collapsed ? (
          <div className="flex items-center gap-2.5 min-w-0 pl-1">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 via-purple-500 to-teal-400 flex items-center justify-center shrink-0 shadow-sm">
              <FlaskConical className="w-4 h-4 text-white" />
            </div>
            <span className="text-[15px] font-medium text-[var(--foreground)] tracking-tight">
              Research OS
            </span>
          </div>
        ) : (
          <div className="w-8 h-8 mx-auto rounded-full bg-gradient-to-br from-blue-500 via-purple-500 to-teal-400 flex items-center justify-center">
            <FlaskConical className="w-4 h-4 text-white" />
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-2 rounded-full text-[var(--muted)] hover:bg-[var(--hover)] transition-colors shrink-0"
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? <PanelLeftOpen className="w-5 h-5" /> : <PanelLeftClose className="w-5 h-5" />}
        </button>
      </div>

      {/* 发起新对话 — pill highlight */}
      <div className="px-3 py-2 shrink-0">
        <button
          onClick={onNewChat}
          className={clsx(
            "w-full flex items-center gap-3 transition-colors text-[var(--foreground)]",
            collapsed
              ? "justify-center p-2.5 rounded-full hover:bg-[var(--hover)]"
              : "px-4 py-3 rounded-full bg-[var(--pill-active)] hover:bg-[var(--active)] text-sm font-normal"
          )}
          title="发起新对话"
        >
          <PenLine className="w-[18px] h-[18px] shrink-0" strokeWidth={1.75} />
          {!collapsed && <span>发起新对话</span>}
        </button>
      </div>

      {/* 搜索对话 */}
      {!collapsed && (
        <div className="px-3 py-1 shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--muted)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索对话内容"
              className="w-full pl-9 pr-3 py-2.5 rounded-full bg-transparent text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] hover:bg-[var(--hover)] focus:bg-[var(--hover)] focus:outline-none transition-colors"
            />
          </div>
        </div>
      )}

      {/* Nav items */}
      <nav className="px-2 py-1 space-y-0.5 shrink-0">
        {NAV_ITEMS.map(({ icon: Icon, label, prompt, action, highlight }) => (
          <button
            key={label}
            onClick={() => {
              if (action === "library") {
                onOpenLibrary?.();
              } else if (prompt) {
                onQuickAction(prompt);
              }
            }}
            title={label}
            className={clsx(
              "w-full flex items-center rounded-full text-sm text-[var(--foreground)] hover:bg-[var(--hover)] transition-colors",
              collapsed ? "justify-center p-2.5" : "gap-3.5 px-4 py-2.5",
              highlight && !collapsed && "font-medium"
            )}
          >
            <Icon className="w-[18px] h-[18px] text-[var(--foreground)] shrink-0" strokeWidth={1.75} />
            {!collapsed && label}
          </button>
        ))}
      </nav>

      {/* 最近 */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto px-2 pt-3 min-h-0">
          <p className="px-4 py-1 text-xs text-[var(--muted)]">最近</p>
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin mx-auto mt-4 text-[var(--muted)]" />
          ) : (
            <div className="space-y-0.5 mt-0.5">
              {filteredChats.length === 0 && filteredProjects.length === 0 ? (
                <p className="px-4 py-2 text-xs text-[var(--muted)]">暂无记录</p>
              ) : (
                <>
                  {filteredChats.map((title, i) => (
                    <button
                      key={`chat-${i}`}
                      className="w-full text-left px-4 py-2.5 rounded-full text-sm text-[var(--foreground)] hover:bg-[var(--hover)] truncate transition-colors"
                    >
                      {title}
                    </button>
                  ))}
                  {filteredProjects.map((p) => (
                    <button
                      key={p.id}
                      className="w-full text-left px-4 py-2.5 rounded-full text-sm text-[var(--foreground)] hover:bg-[var(--hover)] truncate transition-colors"
                      title={p.topic}
                    >
                      {p.title}
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}

      {collapsed && <div className="flex-1" />}

      {/* Footer */}
      <div className="p-3 border-t border-[var(--border)] shrink-0 flex items-center gap-1">
        <ThemeToggle />
        {!collapsed && (
          <span className="text-xs text-[var(--muted)] ml-1">{theme === "dark" ? "暗色" : "亮色"}</span>
        )}
      </div>
    </aside>
  );
}
