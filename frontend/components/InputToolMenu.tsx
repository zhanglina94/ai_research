"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  Atom,
  Beaker,
  BookOpen,
  Check,
  FolderOpen,
  Globe,
  ImageIcon,
  LayoutGrid,
  Paperclip,
  Plus,
  Wrench,
  X,
} from "lucide-react";
import clsx from "clsx";

export type InputToolId = "deep-research" | "canvas" | "research-tools";

export interface InputToolDef {
  id: InputToolId;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  description: string;
}

/** 可选工具（toggle，选中后显示 chip） */
export const TOGGLE_TOOLS: InputToolDef[] = [
  {
    id: "deep-research",
    label: "深度研究",
    icon: Atom,
    description: "获取详细报告",
  },
  {
    id: "canvas",
    label: "Canvas",
    icon: LayoutGrid,
    description: "结合画板笔记进行协作",
  },
];

/** 全部工具定义（含 chip 展示） */
export const INPUT_TOOLS: InputToolDef[] = [
  ...TOGGLE_TOOLS,
  {
    id: "research-tools",
    label: "科研工具",
    icon: Wrench,
    description: "规划、检索、实验设计",
  },
];

interface MenuRowProps {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  label: string;
  description?: string;
  selected?: boolean;
  actionLabel?: string;
  onClick: () => void;
}

function MenuRow({ icon: Icon, label, description, selected, actionLabel, onClick }: MenuRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "w-full flex items-center gap-3 px-3 py-2.5 text-left rounded-xl transition-colors group",
        selected ? "bg-[var(--pill-active)]" : "hover:bg-[var(--hover)]"
      )}
    >
      <span className="w-9 h-9 rounded-lg bg-[var(--hover)] group-hover:bg-[var(--active)] flex items-center justify-center shrink-0">
        <Icon className="w-[18px] h-[18px] text-[var(--foreground)]" strokeWidth={1.75} />
      </span>
      <span className="flex-1 min-w-0">
        <span className="block text-sm font-medium text-[var(--foreground)]">{label}</span>
        {description && (
          <span className="block text-xs text-[var(--muted)] mt-0.5 leading-snug">{description}</span>
        )}
      </span>
      {selected && (
        <Check className="w-4 h-4 text-[var(--accent)] shrink-0" strokeWidth={2.5} />
      )}
      {actionLabel && !selected && (
        <span className="text-xs text-[var(--accent)] shrink-0">{actionLabel}</span>
      )}
    </button>
  );
}

interface InputToolMenuProps {
  selected: InputToolId[];
  onToggle: (id: InputToolId) => void;
  onOpenResearchTools?: () => void;
  menuPlacement?: "above" | "below";
}

export function SelectedToolChips({
  selected,
  onRemove,
}: {
  selected: InputToolId[];
  onRemove: (id: InputToolId) => void;
}) {
  const toggleSelected = selected.filter((id) => TOGGLE_TOOLS.some((t) => t.id === id));
  if (toggleSelected.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 px-1 pb-2">
      {toggleSelected.map((id) => {
        const tool = INPUT_TOOLS.find((t) => t.id === id);
        if (!tool) return null;
        const Icon = tool.icon;
        return (
          <span
            key={id}
            className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full bg-[var(--pill-active)] border border-[var(--border)] text-xs text-[var(--foreground)]"
          >
            <Icon className="w-3.5 h-3.5 text-[var(--muted)]" strokeWidth={1.75} />
            <span>{tool.label}</span>
            <button
              type="button"
              onClick={() => onRemove(id)}
              className="p-0.5 rounded-full hover:bg-[var(--hover)] text-[var(--muted)]"
              aria-label={`移除 ${tool.label}`}
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        );
      })}
    </div>
  );
}

export default function InputToolMenu({
  selected,
  onToggle,
  onOpenResearchTools,
  menuPlacement = "above",
}: InputToolMenuProps) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<React.CSSProperties>({});
  const rootRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  const updatePosition = () => {
    if (!btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    const maxWidth = Math.min(340, window.innerWidth - 16);
    const left = Math.min(rect.left, window.innerWidth - maxWidth - 8);

    if (menuPlacement === "below") {
      setMenuStyle({ position: "fixed", top: rect.bottom + 8, left, width: maxWidth, zIndex: 9999 });
    } else {
      setMenuStyle({ position: "fixed", bottom: window.innerHeight - rect.top + 8, left, width: maxWidth, zIndex: 9999 });
    }
  };

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (rootRef.current?.contains(target)) return;
      if (document.getElementById("input-tool-menu-portal")?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open, menuPlacement]);

  const close = () => setOpen(false);

  const pickToggle = (id: InputToolId) => {
    onToggle(id);
    close();
  };

  const pickAction = (fn?: () => void) => {
    fn?.();
    close();
  };

  const menu = open ? (
    <div id="input-tool-menu-portal" style={menuStyle}>
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--input-shadow)] py-2 px-1.5 max-h-[min(420px,60vh)] overflow-y-auto">
        <MenuRow
          icon={Paperclip}
          label="上传文件"
          description="支持 PDF、Markdown、代码文件"
          onClick={close}
        />
        <MenuRow
          icon={FolderOpen}
          label="从文件库添加"
          description="浏览和搜索你的文件"
          onClick={close}
        />

        <div className="my-1.5 mx-2 border-t border-[var(--border)]" />

        <MenuRow
          icon={BookOpen}
          label="论文检索"
          description="搜索学术文献与引用"
          onClick={() => pickAction(onOpenResearchTools)}
        />
        <MenuRow
          icon={Beaker}
          label="实验设计"
          description="AI 辅助实验方案与变量设计"
          onClick={() => pickAction(onOpenResearchTools)}
        />
        <MenuRow
          icon={ImageIcon}
          label="创建图片"
          description="根据描述生成示意图"
          onClick={close}
        />
        <MenuRow
          icon={Globe}
          label="网页搜索"
          description="查找实时新闻和信息"
          onClick={close}
        />

        {TOGGLE_TOOLS.map((tool) => (
          <MenuRow
            key={tool.id}
            icon={tool.icon}
            label={tool.label}
            description={tool.description}
            selected={selected.includes(tool.id)}
            onClick={() => pickToggle(tool.id)}
          />
        ))}

        <MenuRow
          icon={Wrench}
          label="科研工具"
          description="研究规划、文献库、AI Scientist"
          actionLabel="打开"
          onClick={() => pickAction(onOpenResearchTools)}
        />

        <p className="px-3 pt-2 pb-1 text-[11px] text-[var(--muted)] leading-relaxed">
          输入以搜索插件、文件、文件夹和技能
        </p>
      </div>
    </div>
  ) : null;

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        ref={btnRef}
        type="button"
        onClick={() => {
          setOpen((o) => !o);
          if (!open) requestAnimationFrame(updatePosition);
        }}
        className={clsx(
          "w-9 h-9 rounded-full flex items-center justify-center transition-colors",
          open
            ? "bg-[var(--pill-active)] text-[var(--foreground)]"
            : "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--foreground)]"
        )}
        title="添加工具"
      >
        <Plus className="w-5 h-5" strokeWidth={1.75} />
      </button>

      {typeof document !== "undefined" && menu && createPortal(menu, document.body)}
    </div>
  );
}

export function buildToolPlaceholder(selected: InputToolId[]): string {
  if (selected.includes("deep-research")) return "描述研究主题，深度研究将生成详细报告…";
  if (selected.includes("canvas")) return "结合 Canvas 画板，输入你的问题…";
  return "有问题，尽管问";
}

export function augmentMessage(text: string, selected: InputToolId[], canvasContent?: string): string {
  let msg = text.trim();

  if (selected.includes("deep-research") && !msg.includes("深度研究") && !msg.includes("深度调研")) {
    msg = `请对该主题进行深度研究，包括：文献综述、研究空白、方法建议、实验方向与潜在创新点，并输出详细报告。\n\n主题：${msg}`;
  }

  if (selected.includes("canvas") && canvasContent?.trim()) {
    msg = `${msg}\n\n--- Canvas 笔记 ---\n${canvasContent.trim().slice(0, 4000)}`;
  }

  return msg;
}
