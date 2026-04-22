/**
 * components/chat/AgentBadge.tsx
 * Color-coded chip showing which AI agent is processing.
 */

import { Calendar, StickyNote, Mail, BookOpen, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentType } from "@/types";

const AGENT_CONFIG: Record<
  AgentType,
  { label: string; icon: typeof Calendar; colorClass: string }
> = {
  calendar: { label: "Lịch", icon: Calendar, colorClass: "bg-blue-500/15 text-blue-400 dark:text-blue-300" },
  note: { label: "Ghi chú", icon: StickyNote, colorClass: "bg-amber-500/15 text-amber-600 dark:text-amber-300" },
  email: { label: "Email", icon: Mail, colorClass: "bg-purple-500/15 text-purple-600 dark:text-purple-300" },
  docsearch: { label: "Tài liệu", icon: BookOpen, colorClass: "bg-orange-500/15 text-orange-600 dark:text-orange-300" },
  unknown: { label: "Trợ lý", icon: HelpCircle, colorClass: "bg-gray-500/15 text-gray-500" },
};

interface AgentBadgeProps {
  agent: AgentType;
  className?: string;
}

export function AgentBadge({ agent, className }: AgentBadgeProps) {
  const config = AGENT_CONFIG[agent] || AGENT_CONFIG.unknown;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium",
        config.colorClass,
        className
      )}
    >
      <Icon size={12} />
      {config.label}
    </span>
  );
}
