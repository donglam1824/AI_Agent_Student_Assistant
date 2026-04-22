/**
 * Calendar page – FullCalendar view of Google Calendar events.
 */

"use client";

import { useEffect, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import { getCalendarEvents } from "@/lib/api";
import { MessageSquare } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import type { CalendarEvent } from "@/types";

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    getCalendarEvents(50)
      .then((data) => {
        setEvents(data);
        setIsLoading(false);
      })
      .catch(() => {
        setEvents([]);
        setIsLoading(false);
      });
  }, []);

  // Convert to FullCalendar format
  const calendarEvents = events.map((e) => ({
    id: e.id,
    title: e.summary,
    start: e.start,
    end: e.end,
    extendedProps: {
      location: e.location,
      description: e.description,
    },
  }));

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-text-primary">
              📅 Lịch học
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Xem và quản lý lịch học từ Google Calendar
            </p>
          </div>

          <button
            onClick={() => router.push("/chat")}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
              "bg-accent text-text-on-accent",
              "hover:bg-accent-hover transition-colors duration-150"
            )}
          >
            <MessageSquare size={16} />
            Hỏi AI tạo lịch
          </button>
        </div>

        {/* Calendar */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-text-secondary">Đang tải lịch...</p>
            </div>
          </div>
        ) : (
          <div className="orca-calendar rounded-xl border border-border p-4 bg-bg-secondary">
            <FullCalendar
              plugins={[dayGridPlugin, timeGridPlugin]}
              initialView="dayGridMonth"
              headerToolbar={{
                left: "prev,next today",
                center: "title",
                right: "dayGridMonth,timeGridWeek",
              }}
              events={calendarEvents}
              locale="vi"
              height="auto"
              buttonText={{
                today: "Hôm nay",
                month: "Tháng",
                week: "Tuần",
              }}
              dayHeaderFormat={{ weekday: "short" }}
              eventColor="var(--accent)"
              eventTextColor="var(--text-on-accent)"
            />
          </div>
        )}
      </div>
    </div>
  );
}
