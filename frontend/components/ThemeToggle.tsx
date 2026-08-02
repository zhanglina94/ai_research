"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import clsx from "clsx";

export default function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={clsx(
        "p-2 rounded-lg transition-colors",
        "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--foreground)]",
        className
      )}
      title={theme === "light" ? "切换暗色模式" : "切换亮色模式"}
      aria-label="Toggle theme"
    >
      {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
    </button>
  );
}
