/**
 * components/docs/TopicOverview.tsx
 * Topic summary dashboard with CSS-only donut chart and category cards.
 */

"use client";

import { useMemo } from "react";
import { BookOpen, Code, BarChart, Globe, FileText, FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TopicCategorySummary } from "@/types";

interface TopicOverviewProps {
  summary: TopicCategorySummary[];
  selectedCategory: string | null;
  onSelectCategory: (category: string | null) => void;
}

// Map categories to beautiful icons
function getCategoryIcon(category: string) {
  const cat = category.toLowerCase();
  if (cat.includes("toán") || cat.includes("math") || cat.includes("giải tích") || cat.includes("đại số")) {
    return BookOpen;
  }
  if (
    cat.includes("công nghệ") ||
    cat.includes("it") ||
    cat.includes("lập trình") ||
    cat.includes("tin học") ||
    cat.includes("python") ||
    cat.includes("web")
  ) {
    return Code;
  }
  if (
    cat.includes("kinh tế") ||
    cat.includes("tài chính") ||
    cat.includes("marketing") ||
    cat.includes("quản trị")
  ) {
    return BarChart;
  }
  if (cat.includes("ngôn ngữ") || cat.includes("tiếng") || cat.includes("anh") || cat.includes("trung")) {
    return Globe;
  }
  return FileText;
}

// Hash function to get unique hue color per category
export function getCategoryColors(category: string) {
  let hash = 0;
  for (let i = 0; i < category.length; i++) {
    hash = category.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return {
    bg: `hsla(${hue}, 60%, 45%, 0.12)`,
    text: `hsla(${hue}, 85%, 75%, 1)`,
    border: `hsla(${hue}, 60%, 50%, 0.25)`,
    primary: `hsl(${hue}, 80%, 65%)`,
    primaryHover: `hsl(${hue}, 80%, 75%)`,
  };
}

export function TopicOverview({ summary, selectedCategory, onSelectCategory }: TopicOverviewProps) {
  const totalDocs = useMemo(() => {
    return summary.reduce((acc, curr) => acc + curr.count, 0);
  }, [summary]);

  // Construct conic gradient CSS for CSS-only donut chart
  const donutChartStyle = useMemo(() => {
    if (summary.length === 0 || totalDocs === 0) {
      return {
        background: "var(--border)",
      };
    }

    let currentAngle = 0;
    const gradientParts: string[] = [];

    summary.forEach((item) => {
      const percentage = (item.count / totalDocs) * 100;
      const colors = getCategoryColors(item.category);
      const nextAngle = currentAngle + percentage;
      
      gradientParts.push(`${colors.primary} ${currentAngle.toFixed(1)}% ${nextAngle.toFixed(1)}%`);
      currentAngle = nextAngle;
    });

    return {
      background: `conic-gradient(${gradientParts.join(", ")})`,
    };
  }, [summary, totalDocs]);

  if (summary.length === 0) {
    return null;
  }

  return (
    <div className="topic-overview-container mb-8 p-6 rounded-2xl border border-border bg-bg-secondary/40 backdrop-blur-md">
      <div className="flex flex-col md:flex-row gap-8 items-center justify-between mb-6">
        {/* Left: Summary and Donut Chart */}
        <div className="flex items-center gap-6 flex-1 min-w-[280px]">
          {/* CSS-only donut chart */}
          <div className="relative w-24 h-24 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg" style={donutChartStyle}>
            <div className="w-16 h-16 rounded-full bg-bg-secondary flex flex-col items-center justify-center shadow-inner">
              <span className="text-lg font-bold text-text-primary">{totalDocs}</span>
              <span className="text-[10px] text-text-secondary uppercase tracking-wider font-semibold">Tài liệu</span>
            </div>
          </div>

          <div className="flex-1">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <FolderOpen size={16} className="text-accent" /> Phân loại học tập
            </h3>
            <p className="text-xs text-text-secondary mt-1">
              Hệ thống tự động phân tích và gom nhóm tài liệu theo các danh mục học tập chính.
            </p>
            <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3">
              {summary.map((item) => {
                const colors = getCategoryColors(item.category);
                const percent = Math.round((item.count / totalDocs) * 100);
                return (
                  <div key={item.category} className="flex items-center gap-1.5 text-xs">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: colors.primary }} />
                    <span className="text-text-secondary font-medium">{item.category}</span>
                    <span className="text-text-muted font-bold">({percent}%)</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap gap-2 mb-6 border-t border-border/60 pt-4">
        <button
          onClick={() => onSelectCategory(null)}
          className={cn(
            "px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200",
            selectedCategory === null
              ? "bg-accent/20 text-accent border-accent/40 shadow-sm shadow-accent/10"
              : "bg-bg-elevated/40 text-text-secondary border-border hover:text-text-primary hover:border-border-hover"
          )}
        >
          Tất cả tài liệu
        </button>
        {summary.map((item) => {
          const colors = getCategoryColors(item.category);
          const isSelected = selectedCategory === item.category;
          return (
            <button
              key={item.category}
              onClick={() => onSelectCategory(isSelected ? null : item.category)}
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200 flex items-center gap-1.5",
                isSelected
                  ? "shadow-sm"
                  : "bg-bg-elevated/40 hover:text-text-primary hover:border-border-hover"
              )}
              style={{
                backgroundColor: isSelected ? colors.bg : undefined,
                color: isSelected ? colors.text : undefined,
                borderColor: isSelected ? colors.primary : "var(--border)",
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colors.primary }} />
              {item.category}
              <span className="opacity-60 text-[10px] font-semibold bg-black/10 px-1.5 py-0.5 rounded-full ml-1">
                {item.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Category Grid Section */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {summary.map((item) => {
          const Icon = getCategoryIcon(item.category);
          const colors = getCategoryColors(item.category);
          const isSelected = selectedCategory === item.category;
          return (
            <div
              key={item.category}
              onClick={() => onSelectCategory(isSelected ? null : item.category)}
              className={cn(
                "p-4 rounded-xl border transition-all duration-200 cursor-pointer group flex flex-col justify-between",
                "bg-bg-secondary border-border hover:border-border-hover hover:translate-y-[-2px] hover:shadow-md",
                isSelected && "border-accent/40 bg-accent/5 ring-1 ring-accent/30"
              )}
              style={{
                borderColor: isSelected ? colors.primary : undefined,
              }}
            >
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div
                    className="p-2 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: colors.bg, color: colors.text }}
                  >
                    <Icon size={18} />
                  </div>
                  <span className="text-[11px] font-semibold text-text-secondary bg-bg-elevated px-2 py-0.5 rounded-full border border-border">
                    {item.count} tài liệu
                  </span>
                </div>
                <h4 className="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors">
                  {item.category}
                </h4>
                {item.topics.length > 0 && (
                  <div className="mt-2.5">
                    <p className="text-[10px] text-text-secondary uppercase tracking-wider font-semibold mb-1">Chủ đề chính</p>
                    <div className="flex flex-wrap gap-1">
                      {item.topics.slice(0, 3).map((topic) => (
                        <span
                          key={topic}
                          className="text-[10px] px-2 py-0.5 rounded bg-bg-elevated/60 text-text-secondary border border-border/40 truncate max-w-[120px]"
                          title={topic}
                        >
                          {topic}
                        </span>
                      ))}
                      {item.topics.length > 3 && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-bg-elevated/60 text-text-muted border border-border/40">
                          +{item.topics.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
