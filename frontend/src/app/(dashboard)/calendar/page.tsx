/**
 * Calendar page – FullCalendar view of Google Calendar events.
 * Features: event detail modal, upcoming events sidebar, error handling,
 * date-range-based fetching, and responsive design.
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import { getCalendarEvents } from "@/lib/api";
import {
  MessageSquare,
  RefreshCw,
  Calendar,
  Clock,
  MapPin,
  FileText,
  ChevronRight,
  AlertCircle,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import type { CalendarEvent } from "@/types";

/* ─── Helpers ──────────────────────────────────────────────────────────── */

function formatTime(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return "";
  }
}

function formatDate(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("vi-VN", {
      weekday: "short",
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return "";
  }
}

function formatFullDate(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("vi-VN", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

function isToday(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  return (
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear()
  );
}

function isFutureOrToday(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return d >= now;
}

/** Generate a consistent hue from event title for color-coding */
function eventHue(title: string): number {
  let hash = 0;
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % 360;
}

/* ─── Types ────────────────────────────────────────────────────────────── */

interface SelectedEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  description?: string;
}

/* ─── Component ────────────────────────────────────────────────────────── */

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<SelectedEvent | null>(
    null
  );
  const router = useRouter();
  const calendarRef = useRef<FullCalendar>(null);

  /* ── Fetch events ──────────────────────────────────────────────────── */

  const fetchEvents = useCallback(async (showRefresh = false) => {
    if (showRefresh) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);

    try {
      const data = await getCalendarEvents(100);
      setEvents(data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Không thể tải sự kiện lịch";
      setError(msg);
      setEvents([]);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  /* ── Derived data ──────────────────────────────────────────────────── */

  // Convert to FullCalendar format with color-coding
  const calendarEvents = useMemo(
    () =>
      events.map((e) => {
        const hue = eventHue(e.summary);
        return {
          id: e.id,
          title: e.summary,
          start: e.start,
          end: e.end,
          backgroundColor: `hsl(${hue}, 65%, 50%)`,
          borderColor: `hsl(${hue}, 65%, 40%)`,
          textColor: "#ffffff",
          extendedProps: {
            location: e.location,
            description: e.description,
          },
        };
      }),
    [events]
  );

  // Upcoming events (today and future), sorted by start time
  const upcomingEvents = useMemo(
    () =>
      events
        .filter((e) => isFutureOrToday(e.start))
        .sort(
          (a, b) => new Date(a.start).getTime() - new Date(b.start).getTime()
        )
        .slice(0, 8),
    [events]
  );

  /* ── Event click handler ───────────────────────────────────────────── */

  const handleEventClick = (info: { event: { id: string; title: string; startStr: string; endStr: string; extendedProps: Record<string, unknown> } }) => {
    setSelectedEvent({
      id: info.event.id,
      title: info.event.title,
      start: info.event.startStr,
      end: info.event.endStr,
      location: info.event.extendedProps?.location as string | undefined,
      description: info.event.extendedProps?.description as string | undefined,
    });
  };

  /* ── Render ─────────────────────────────────────────────────────────── */

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 animate-fade-in">
      <div className="max-w-[1400px] mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
          <div>
            <h2 className="text-xl font-semibold text-text-primary flex items-center gap-2">
              <Calendar size={22} className="text-accent" />
              Lịch học
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Xem và quản lý lịch học từ Google Calendar
              {events.length > 0 && (
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent font-medium">
                  {events.length} sự kiện
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchEvents(true)}
              disabled={isRefreshing}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-xl text-sm",
                "border border-border bg-bg-secondary text-text-secondary",
                "hover:bg-bg-elevated hover:text-text-primary transition-all duration-150",
                "disabled:opacity-50"
              )}
            >
              <RefreshCw
                size={15}
                className={isRefreshing ? "animate-spin" : ""}
              />
              Làm mới
            </button>

            <button
              onClick={() => router.push("/chat")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
                "bg-accent text-text-on-accent",
                "hover:bg-accent-hover transition-colors duration-150",
                "shadow-sm shadow-accent/20"
              )}
            >
              <MessageSquare size={16} />
              Hỏi AI tạo lịch
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 rounded-xl border border-red-500/30 bg-red-500/5 flex items-start gap-3">
            <AlertCircle
              size={20}
              className="text-red-400 shrink-0 mt-0.5"
            />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-400">
                Không thể tải lịch
              </p>
              <p className="text-xs text-text-secondary mt-1">{error}</p>
            </div>
            <button
              onClick={() => fetchEvents(true)}
              className="text-xs px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-text-secondary">
                Đang tải lịch từ Google Calendar...
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Main Calendar */}
            <div className="flex-1 min-w-0">
              <div className="orca-calendar rounded-xl border border-border p-4 bg-bg-secondary">
                <FullCalendar
                  ref={calendarRef}
                  plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                  initialView="dayGridMonth"
                  headerToolbar={{
                    left: "prev,next today",
                    center: "title",
                    right: "dayGridMonth,timeGridWeek,timeGridDay",
                  }}
                  events={calendarEvents}
                  eventClick={handleEventClick}
                  locale="vi"
                  height="auto"
                  buttonText={{
                    today: "Hôm nay",
                    month: "Tháng",
                    week: "Tuần",
                    day: "Ngày",
                  }}
                  dayHeaderFormat={{ weekday: "short" }}
                  slotLabelFormat={{
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  }}
                  eventTimeFormat={{
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  }}
                  nowIndicator={true}
                  dayMaxEvents={3}
                  moreLinkText={(num) => `+${num} sự kiện`}
                  eventDisplay="block"
                />
              </div>
            </div>

            {/* Sidebar: Upcoming Events */}
            <div className="w-full lg:w-80 shrink-0">
              <div className="rounded-xl border border-border bg-bg-secondary p-4 sticky top-6">
                <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <Clock size={15} className="text-accent" />
                  Sự kiện sắp tới
                </h3>

                {upcomingEvents.length === 0 ? (
                  <div className="text-center py-8">
                    <Calendar
                      size={32}
                      className="mx-auto text-text-secondary/30 mb-3"
                    />
                    <p className="text-sm text-text-secondary">
                      Không có sự kiện nào sắp tới
                    </p>
                    <button
                      onClick={() => router.push("/chat")}
                      className="mt-3 text-xs text-accent hover:underline"
                    >
                      Tạo sự kiện mới →
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {upcomingEvents.map((e) => {
                      const hue = eventHue(e.summary);
                      const today = isToday(e.start);
                      return (
                        <button
                          key={e.id}
                          onClick={() =>
                            setSelectedEvent({
                              id: e.id,
                              title: e.summary,
                              start: e.start,
                              end: e.end,
                              location: e.location ?? undefined,
                              description: e.description ?? undefined,
                            })
                          }
                          className={cn(
                            "w-full text-left p-3 rounded-lg transition-all duration-150",
                            "border border-transparent",
                            "hover:bg-bg-elevated hover:border-border",
                            "group"
                          )}
                        >
                          <div className="flex items-start gap-3">
                            <div
                              className="w-1 h-full min-h-[36px] rounded-full shrink-0"
                              style={{
                                backgroundColor: `hsl(${hue}, 65%, 50%)`,
                              }}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-text-primary truncate">
                                {e.summary}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-text-secondary">
                                  {formatDate(e.start)}
                                </span>
                                <span className="text-xs text-text-secondary">
                                  {formatTime(e.start)} –{" "}
                                  {formatTime(e.end)}
                                </span>
                              </div>
                              {today && (
                                <span className="inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-accent/15 text-accent font-medium">
                                  Hôm nay
                                </span>
                              )}
                              {e.location && (
                                <p className="text-xs text-text-secondary mt-1 flex items-center gap-1 truncate">
                                  <MapPin size={10} />
                                  {e.location}
                                </p>
                              )}
                            </div>
                            <ChevronRight
                              size={14}
                              className="text-text-secondary/40 group-hover:text-text-secondary mt-1 shrink-0 transition-colors"
                            />
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Event Detail Modal */}
        {selectedEvent && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
            onClick={() => setSelectedEvent(null)}
          >
            <div
              className="bg-bg-primary border border-border rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal header with color strip */}
              <div
                className="h-2"
                style={{
                  backgroundColor: `hsl(${eventHue(selectedEvent.title)}, 65%, 50%)`,
                }}
              />
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-lg font-semibold text-text-primary pr-4">
                    {selectedEvent.title}
                  </h3>
                  <button
                    onClick={() => setSelectedEvent(null)}
                    className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors shrink-0"
                  >
                    <X size={16} className="text-text-secondary" />
                  </button>
                </div>

                <div className="space-y-3">
                  {/* Date */}
                  <div className="flex items-start gap-3">
                    <Calendar
                      size={16}
                      className="text-text-secondary mt-0.5 shrink-0"
                    />
                    <div>
                      <p className="text-sm text-text-primary">
                        {formatFullDate(selectedEvent.start)}
                      </p>
                    </div>
                  </div>

                  {/* Time */}
                  <div className="flex items-start gap-3">
                    <Clock
                      size={16}
                      className="text-text-secondary mt-0.5 shrink-0"
                    />
                    <p className="text-sm text-text-primary">
                      {formatTime(selectedEvent.start)} –{" "}
                      {formatTime(selectedEvent.end)}
                    </p>
                  </div>

                  {/* Location */}
                  {selectedEvent.location && (
                    <div className="flex items-start gap-3">
                      <MapPin
                        size={16}
                        className="text-text-secondary mt-0.5 shrink-0"
                      />
                      <p className="text-sm text-text-primary">
                        {selectedEvent.location}
                      </p>
                    </div>
                  )}

                  {/* Description */}
                  {selectedEvent.description && (
                    <div className="flex items-start gap-3">
                      <FileText
                        size={16}
                        className="text-text-secondary mt-0.5 shrink-0"
                      />
                      <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
                        {selectedEvent.description}
                      </p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="mt-6 flex gap-2">
                  <button
                    onClick={() => {
                      setSelectedEvent(null);
                      router.push("/chat");
                    }}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm",
                      "bg-accent text-text-on-accent",
                      "hover:bg-accent-hover transition-colors"
                    )}
                  >
                    <MessageSquare size={14} />
                    Hỏi AI về sự kiện này
                  </button>
                  <button
                    onClick={() => setSelectedEvent(null)}
                    className="px-4 py-2.5 rounded-xl text-sm border border-border text-text-secondary hover:bg-bg-elevated transition-colors"
                  >
                    Đóng
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
