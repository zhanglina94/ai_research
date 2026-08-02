"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { ArrowUp, Bot, Loader2, Menu, Sparkles, User } from "lucide-react";
import { api, ChatMessage } from "@/lib/api";
import clsx from "clsx";
import InputToolMenu, {
  InputToolId,
  SelectedToolChips,
  augmentMessage,
  buildToolPlaceholder,
} from "@/components/InputToolMenu";

interface ChatPanelProps {
  onMenuClick?: () => void;
  resetKey?: number;
  prefill?: string;
  onPrefillConsumed?: () => void;
  onChatSent?: (title: string) => void;
  onOpenCanvas?: () => void;
  onOpenTools?: () => void;
}

export default function ChatPanel({
  onMenuClick,
  resetKey = 0,
  prefill = "",
  onPrefillConsumed,
  onChatSent,
  onOpenCanvas,
  onOpenTools,
}: ChatPanelProps) {
  const WELCOME =
    "Welcome to **AI Research OS**. I can help you plan research, search papers, and discuss ideas.";

  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: WELCOME },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const [selectedTools, setSelectedTools] = useState<InputToolId[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const hasConversation = messages.some((m) => m.role === "user");

  useEffect(() => {
    setMessages([{ role: "assistant", content: WELCOME }]);
    setInput("");
    setSessionId(undefined);
    setSelectedTools([]);
  }, [resetKey]);

  useEffect(() => {
    if (prefill) {
      setInput(prefill);
      inputRef.current?.focus();
      onPrefillConsumed?.();
    }
  }, [prefill, onPrefillConsumed]);

  useEffect(() => {
    if (hasConversation) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, hasConversation]);

  const toggleTool = useCallback(
    (id: InputToolId) => {
      setSelectedTools((prev) => {
        const next = prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id];
        if (id === "canvas" && !prev.includes("canvas")) {
          onOpenCanvas?.();
        }
        return next;
      });
      inputRef.current?.focus();
    },
    [onOpenCanvas]
  );

  const removeTool = useCallback((id: InputToolId) => {
    setSelectedTools((prev) => prev.filter((t) => t !== id));
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || loading) return;

      const canvasContent =
        typeof window !== "undefined" ? localStorage.getItem("research-canvas") ?? "" : "";
      const trimmed = augmentMessage(text, selectedTools, canvasContent);
      const userMsg: ChatMessage = { role: "user", content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);
      onChatSent?.(trimmed.slice(0, 40));

      try {
        const res = await api.chat(trimmed, sessionId);
        setSessionId(res.session_id);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.reply, agent: res.agent },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "连接失败，请确认后端已在 8002 端口运行。" },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading, sessionId, onChatSent, selectedTools]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const activeToolBadges = selectedTools.length > 0 && (
    <div className="flex flex-wrap gap-1.5 px-1">
      {selectedTools.map((id) => {
        const labels: Record<InputToolId, string> = {
          "deep-research": "深度研究",
          canvas: "Canvas",
          "research-tools": "科研工具",
        };
        return (
          <span
            key={id}
            className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--pill-active)] text-[var(--accent)] font-medium"
          >
            {labels[id]}
          </span>
        );
      })}
    </div>
  );

  const renderInputBox = (menuPlacement: "above" | "below") => (
    <div className="relative flex flex-col bg-[var(--input-bg)] border border-[var(--border)] rounded-[28px] px-4 py-3 shadow-[var(--input-shadow)] focus-within:border-[var(--border-focus)] transition-colors">
      <SelectedToolChips selected={selectedTools} onRemove={removeTool} />
      <div className="flex items-end gap-2">
        <InputToolMenu
          selected={selectedTools}
          onToggle={toggleTool}
          onOpenResearchTools={onOpenTools}
          menuPlacement={menuPlacement}
        />
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={buildToolPlaceholder(selectedTools)}
          rows={1}
          disabled={loading}
          className="flex-1 bg-transparent resize-none text-[15px] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none max-h-32 leading-relaxed py-0.5"
          style={{ fieldSizing: "content" } as React.CSSProperties}
        />
        <button
          type="button"
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className={clsx(
            "shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors mb-0.5",
            input.trim()
              ? "bg-[var(--send-bg)] text-[var(--send-fg)] hover:opacity-90"
              : "bg-[var(--send-disabled)] text-[var(--muted)] cursor-not-allowed"
          )}
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ArrowUp className="w-4 h-4" strokeWidth={2} />
          )}
        </button>
      </div>
    </div>
  );

  if (!hasConversation) {
    return (
      <div className="flex flex-col flex-1 min-h-0 h-full">
        <header className="shrink-0 flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              onClick={onMenuClick}
              className="lg:hidden p-2 rounded-full hover:bg-[var(--hover)] text-[var(--muted)]"
            >
              <Menu className="w-5 h-5" />
            </button>
            <button className="flex items-center gap-1 text-[var(--foreground)] font-medium text-sm hover:bg-[var(--hover)] px-3 py-1.5 rounded-full transition-colors">
              AI Research OS
              <span className="text-[var(--muted)] text-xs ml-0.5">▾</span>
            </button>
          </div>
          {activeToolBadges}
        </header>

        <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8 min-h-0">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 via-purple-500 to-teal-400 flex items-center justify-center mb-6 shadow-md">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl md:text-[28px] font-normal text-[var(--foreground)] mb-8 text-center tracking-tight">
            我们先从哪里开始呢？
          </h1>
          <div className="w-full max-w-2xl">{renderInputBox("below")}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 h-full">
      <header className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
        <div className="flex items-center">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-full hover:bg-[var(--hover)] text-[var(--muted)] mr-2"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="text-sm font-medium text-[var(--foreground)]">AI Research OS</span>
        </div>
        {activeToolBadges}
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages
            .filter((m) => m.role === "user" || messages.indexOf(m) > 0)
            .map((msg, i) => (
              <div key={i} className="flex gap-4">
                <div
                  className={clsx(
                    "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                    msg.role === "user" ? "bg-[var(--user-avatar)]" : "bg-[var(--accent)]"
                  )}
                >
                  {msg.role === "user" ? (
                    <User className="w-4 h-4 text-[var(--muted)]" />
                  ) : (
                    <Bot className="w-4 h-4 text-white" />
                  )}
                </div>
                <div className="flex-1 min-w-0 pt-0.5">
                  {msg.agent && msg.role === "assistant" && (
                    <span className="text-xs text-[var(--accent)] font-medium block mb-1">
                      {msg.agent} agent
                    </span>
                  )}
                  <div className="text-[15px] leading-relaxed text-[var(--foreground)]">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                        ul: ({ children }) => <ul className="list-disc pl-5 space-y-1 mb-3">{children}</ul>,
                        li: ({ children }) => <li>{children}</li>,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
          {loading && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-[var(--accent)] flex items-center justify-center shrink-0">
                <Loader2 className="w-4 h-4 text-white animate-spin" />
              </div>
              <div className="pt-1 text-[var(--muted)] text-sm">思考中...</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="shrink-0 px-4 pb-4 pt-2">
        <div className="max-w-3xl mx-auto">{renderInputBox("above")}</div>
        <p className="text-center text-xs text-[var(--muted)] mt-3">
          AI Research OS 可能会出错，请核实重要信息。
        </p>
      </div>
    </div>
  );
}
