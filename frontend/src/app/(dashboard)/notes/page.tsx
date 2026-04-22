/**
 * Notes page – CRUD note management with inline editing.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { getNotes, createNote, updateNote, deleteNote } from "@/lib/api";
import { Plus, Trash2, Pencil, Save, X, MessageSquare, StickyNote } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import type { Note } from "@/types";

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const router = useRouter();

  const fetchNotes = useCallback(async () => {
    try {
      const data = await getNotes();
      setNotes(data);
    } catch {
      setNotes([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setSaving(true);
    try {
      await createNote(newTitle.trim(), newContent.trim());
      setNewTitle("");
      setNewContent("");
      setShowCreate(false);
      fetchNotes();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (noteId: string) => {
    setSaving(true);
    try {
      await updateNote(noteId, { title: editTitle, content: editContent });
      setEditingId(null);
      fetchNotes();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (noteId: string) => {
    if (!confirm("Bạn có chắc muốn xóa ghi chú này?")) return;
    try {
      await deleteNote(noteId);
      fetchNotes();
    } catch (e) {
      console.error(e);
    }
  };

  const startEdit = (note: Note) => {
    setEditingId(note.id);
    setEditTitle(note.title);
    setEditContent(note.content);
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-text-primary">
              📝 Ghi chú học tập
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Ghi chép bài giảng, deadline và ý tưởng
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push("/chat")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
                "bg-bg-elevated text-text-secondary",
                "hover:bg-bg-secondary hover:text-text-primary transition-colors"
              )}
            >
              <MessageSquare size={16} />
              Nhờ AI tạo ghi chú
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
                "bg-accent text-text-on-accent",
                "hover:bg-accent-hover transition-colors duration-150"
              )}
            >
              <Plus size={16} />
              Tạo ghi chú
            </button>
          </div>
        </div>

        {/* Create new note form */}
        {showCreate && (
          <div className="mb-6 rounded-xl border border-accent/30 bg-bg-secondary p-5 animate-scale-in">
            <h3 className="text-sm font-medium text-accent mb-3">Ghi chú mới</h3>
            <input
              type="text"
              placeholder="Tiêu đề (ví dụ: Bài tập Toán chương 5)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className={cn(
                "w-full px-4 py-2.5 rounded-lg text-sm mb-3",
                "bg-bg-primary border border-border",
                "text-text-primary placeholder:text-text-secondary/60",
                "focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30",
                "transition-colors"
              )}
              autoFocus
            />
            <textarea
              placeholder="Nội dung ghi chú..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              rows={4}
              className={cn(
                "w-full px-4 py-2.5 rounded-lg text-sm mb-4 resize-none",
                "bg-bg-primary border border-border",
                "text-text-primary placeholder:text-text-secondary/60",
                "focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30",
                "transition-colors"
              )}
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setShowCreate(false); setNewTitle(""); setNewContent(""); }}
                className="px-4 py-2 rounded-lg text-sm text-text-secondary hover:bg-bg-elevated transition-colors"
              >
                Hủy
              </button>
              <button
                onClick={handleCreate}
                disabled={!newTitle.trim() || saving}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm",
                  "bg-accent text-text-on-accent",
                  "hover:bg-accent-hover transition-colors",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <Save size={14} />
                {saving ? "Đang lưu..." : "Lưu ghi chú"}
              </button>
            </div>
          </div>
        )}

        {/* Loading */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-text-secondary">Đang tải ghi chú...</p>
            </div>
          </div>
        ) : notes.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-4">
              <StickyNote size={28} className="text-accent" />
            </div>
            <h3 className="text-lg font-medium text-text-primary mb-2">
              Chưa có ghi chú nào
            </h3>
            <p className="text-sm text-text-secondary max-w-sm mb-6">
              Tạo ghi chú đầu tiên hoặc nhờ AI tạo ghi chú từ cuộc trò chuyện.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className={cn(
                "flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm",
                "bg-accent text-text-on-accent",
                "hover:bg-accent-hover transition-colors"
              )}
            >
              <Plus size={16} />
              Tạo ghi chú đầu tiên
            </button>
          </div>
        ) : (
          /* Notes grid */
          <div className="grid gap-4 sm:grid-cols-2">
            {notes.map((note, idx) => (
              <div
                key={note.id}
                className={cn(
                  "rounded-xl border border-border bg-bg-secondary p-5",
                  "hover:border-border-hover hover:shadow-[var(--shadow-md)]",
                  "transition-all duration-200 animate-slide-up",
                  "group"
                )}
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                {editingId === note.id ? (
                  /* Edit mode */
                  <div>
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className={cn(
                        "w-full px-3 py-2 rounded-lg text-sm mb-2",
                        "bg-bg-primary border border-border",
                        "text-text-primary focus:outline-none focus:border-accent"
                      )}
                    />
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={4}
                      className={cn(
                        "w-full px-3 py-2 rounded-lg text-sm mb-3 resize-none",
                        "bg-bg-primary border border-border",
                        "text-text-primary focus:outline-none focus:border-accent"
                      )}
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-2 rounded-lg text-text-secondary hover:bg-bg-elevated transition-colors"
                      >
                        <X size={14} />
                      </button>
                      <button
                        onClick={() => handleUpdate(note.id)}
                        disabled={saving}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-accent text-text-on-accent hover:bg-accent-hover transition-colors"
                      >
                        <Save size={12} />
                        Lưu
                      </button>
                    </div>
                  </div>
                ) : (
                  /* View mode */
                  <>
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-sm font-semibold text-text-primary leading-tight">
                        {note.title}
                      </h3>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => startEdit(note)}
                          className="p-1.5 rounded-lg text-text-secondary hover:bg-bg-elevated hover:text-accent transition-colors"
                          title="Sửa"
                        >
                          <Pencil size={13} />
                        </button>
                        <button
                          onClick={() => handleDelete(note.id)}
                          className="p-1.5 rounded-lg text-text-secondary hover:bg-bg-elevated hover:text-error transition-colors"
                          title="Xóa"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                    <p className="text-sm text-text-secondary leading-relaxed mb-3 line-clamp-4">
                      {note.content || "Chưa có nội dung"}
                    </p>
                    <p className="text-[11px] text-text-secondary/70">
                      Cập nhật: {formatDate(note.updated_at)}
                    </p>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
