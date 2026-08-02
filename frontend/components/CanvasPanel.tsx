"use client";

import { useEffect, useState } from "react";
import { Download, Eraser, X } from "lucide-react";

const STORAGE_KEY = "research-canvas";

interface CanvasPanelProps {
  open: boolean;
  onClose: () => void;
}

export default function CanvasPanel({ open, onClose }: CanvasPanelProps) {
  const [content, setContent] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) setContent(saved);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, content);
    }, 300);
    return () => clearTimeout(timer);
  }, [content]);

  if (!open) return null;

  const exportNotes = () => {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "research-canvas.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearNotes = () => {
    setContent("");
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/30" onClick={onClose} />
      <div className="fixed inset-y-0 left-0 right-0 md:left-auto md:w-[640px] z-50 bg-[var(--background)] border-l border-[var(--border)] shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <div>
            <h2 className="text-base font-medium text-[var(--foreground)]">画板</h2>
            <p className="text-xs text-[var(--muted)] mt-0.5">研究笔记、思路梳理、Markdown 草稿</p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={clearNotes}
              className="p-2 rounded-full hover:bg-[var(--hover)] text-[var(--muted)]"
              title="清空"
            >
              <Eraser className="w-4 h-4" />
            </button>
            <button
              onClick={exportNotes}
              className="p-2 rounded-full hover:bg-[var(--hover)] text-[var(--muted)]"
              title="导出"
            >
              <Download className="w-4 h-4" />
            </button>
            <button onClick={onClose} className="p-2 rounded-full hover:bg-[var(--hover)] text-[var(--muted)]">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={`# 研究笔记\n\n## 核心问题\n\n## 方法思路\n\n## 实验计划\n\n## 参考文献`}
          className="flex-1 p-5 bg-transparent text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] resize-none focus:outline-none leading-relaxed font-mono"
        />
      </div>
    </>
  );
}
