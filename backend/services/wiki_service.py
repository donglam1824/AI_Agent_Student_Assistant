"""
Dịch vụ quản lý wiki cá nhân dưới dạng Markdown cho tài liệu học tập.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from typing import Iterable, List, Optional

from langchain_core.documents import Document as LangChainDocument

from core.logger import logger
from core.llm_manager import llm_manager


WIKI_ROOT = Path(__file__).parent.parent / "data" / "wiki"
MANIFEST_NAME = "manifest.json"
INDEX_NAME = "index.md"
CATEGORY_SUMMARY_NAME = "_summary.md"
MAX_SUMMARY_SOURCE_CHARS = 8000


@dataclass(frozen=True)
class WikiUpdateResult:
    document_path: Path
    relative_document_path: str
    summary: str


class WikiService:
    """Tạo và quản lý cơ sở tri thức Markdown cá nhân"""

    def upsert_document(
        self,
        *,
        user_id: str,
        document_key: str,
        title: str,
        chunks: List[LangChainDocument],
        topic: str,
        category: str,
        tags: Iterable[str],
        source_type: str,
        source_id: Optional[str] = None,
    ) -> WikiUpdateResult:
        if not chunks:
            raise ValueError("Cannot create wiki entry for an empty document.")

        tags_list = list(tags)
        user_dir = self._user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        manifest = self._read_manifest(user_dir)
        document_text = self._extract_document_text(chunks)
        summary = self._summarize_document(
            title=title,
            topic=topic,
            category=category,
            tags=tags_list,
            text=document_text,
        )

        category_dir = user_dir / self._slug(category)
        category_dir.mkdir(parents=True, exist_ok=True)

        document_filename = f"{self._slug(Path(title).stem)}-{self._slug(document_key)[:48]}.md"
        document_path = category_dir / document_filename
        relative_path = document_path.relative_to(user_dir).as_posix()

        old_entry = manifest.get("documents", {}).get(document_key)
        if old_entry:
            old_path = user_dir / old_entry.get("path", "")
            if old_path != document_path and old_path.exists():
                old_path.unlink()

        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "key": document_key,
            "title": title,
            "topic": topic,
            "category": category,
            "tags": tags_list,
            "source_type": source_type,
            "source_id": source_id,
            "path": relative_path,
            "summary": summary,
            "updated_at": now,
            "chunk_count": len(chunks),
        }

        self._write_document_markdown(document_path, entry, document_text)
        manifest.setdefault("documents", {})[document_key] = entry
        manifest["updated_at"] = now
        self._write_manifest(user_dir, manifest)
        self._write_index(user_dir, manifest)
        self._write_category_summaries(user_dir, manifest)

        return WikiUpdateResult(
            document_path=document_path,
            relative_document_path=relative_path,
            summary=summary,
        )

    def remove_document(self, *, user_id: str, document_key: str) -> None:
        user_dir = self._user_dir(user_id)
        manifest = self._read_manifest(user_dir)
        entry = manifest.get("documents", {}).pop(document_key, None)
        if not entry:
            return

        document_path = user_dir / entry.get("path", "")
        if document_path.exists():
            document_path.unlink()

        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_manifest(user_dir, manifest)
        self._write_index(user_dir, manifest)
        self._write_category_summaries(user_dir, manifest)

    def contextualize_chunks(
        self,
        *,
        chunks: List[LangChainDocument],
        title: str,
        topic: str,
        category: str,
        tags: Iterable[str],
        wiki_path: str,
        summary: str,
    ) -> None:
        """Lưu ngữ cảnh tài liệu vào metadata để hỗ trợ RAG"""
        tags_text = ", ".join(tags) if tags else "không có"
        context = (
            f"Nguồn: {title}\n"
            f"Danh mục: {category}\n"
            f"Chủ đề: {topic}\n"
            f"Tags: {tags_text}\n"
            f"Tóm tắt tài liệu: {summary}"
        )

        for chunk in chunks:
            if chunk.metadata.get("contextualized") is True:
                continue
            chunk.metadata.update(
                {
                    "contextualized": True,
                    "context_summary": summary[:1000],
                    "wiki_path": wiki_path,
                    "context_prefix": context,
                }
            )

    def _summarize_document(
        self,
        *,
        title: str,
        topic: str,
        category: str,
        tags: List[str],
        text: str,
    ) -> str:
        sample = text[:MAX_SUMMARY_SOURCE_CHARS].strip()
        if not sample:
            return "Chưa trích xuất được nội dung đủ rõ để tạo tóm tắt."

        try:
            llm = llm_manager.get_model(task="rag")
            prompt = (
                "Tóm tắt tài liệu học tập sau bằng tiếng Việt trong 4-6 câu. "
                "Nêu mục tiêu, các khái niệm chính, và sinh viên nên dùng tài liệu này để làm gì. "
                "Không bịa thông tin ngoài nội dung.\n\n"
                f"Tên tài liệu: {title}\n"
                f"Danh mục: {category}\n"
                f"Chủ đề: {topic}\n"
                f"Tags: {', '.join(tags)}\n\n"
                f"Nội dung trích xuất:\n{sample}"
            )
            result = llm.invoke(prompt)
            content = getattr(result, "content", str(result)).strip()
            if content:
                return self._normalize_summary(content)
        except Exception as exc:
            logger.warning(f"WikiService: LLM summary failed for {title}: {exc}")

        return self._fallback_summary(sample)

    def _extract_document_text(self, chunks: List[LangChainDocument]) -> str:
        markdown_path = self._first_markdown_path(chunks)
        if markdown_path and markdown_path.exists():
            return markdown_path.read_text(encoding="utf-8", errors="ignore").strip()

        parts = []
        for chunk in chunks:
            text = chunk.page_content.strip()
            if text:
                parts.append(text)
        return "\n\n---\n\n".join(parts).strip()

    @staticmethod
    def _first_markdown_path(chunks: List[LangChainDocument]) -> Optional[Path]:
        for chunk in chunks:
            markdown_path = chunk.metadata.get("markdown_path")
            if markdown_path:
                return Path(markdown_path)
        return None

    def _write_document_markdown(self, path: Path, entry: dict, document_text: str) -> None:
        frontmatter = {
            "title": entry["title"],
            "topic": entry["topic"],
            "category": entry["category"],
            "tags": entry["tags"],
            "source_type": entry["source_type"],
            "source_id": entry["source_id"],
            "document_key": entry["key"],
            "updated_at": entry["updated_at"],
        }
        content = (
            "---\n"
            f"{json.dumps(frontmatter, ensure_ascii=False, indent=2)}\n"
            "---\n\n"
            f"# {entry['title']}\n\n"
            "## Tóm tắt\n\n"
            f"{entry['summary']}\n\n"
            "## Metadata\n\n"
            f"- Danh mục: {entry['category']}\n"
            f"- Chủ đề: {entry['topic']}\n"
            f"- Tags: {', '.join(entry['tags']) if entry['tags'] else 'Không có'}\n"
            f"- Nguồn: {entry['source_type']}\n"
            f"- Số chunks: {entry['chunk_count']}\n\n"
            "## Nội dung trích xuất\n\n"
            f"{document_text.strip()}\n"
        )
        path.write_text(content, encoding="utf-8")

    def _write_index(self, user_dir: Path, manifest: dict) -> None:
        entries = self._sorted_entries(manifest)
        by_category: dict[str, list[dict]] = {}
        for entry in entries:
            by_category.setdefault(entry["category"], []).append(entry)

        lines = [
            "# ORCA Knowledge Base",
            "",
            f"Cập nhật: {manifest.get('updated_at', '')}",
            "",
            "## Tổng quan",
            "",
            f"- Tổng số tài liệu: {len(entries)}",
            f"- Tổng số danh mục: {len(by_category)}",
            "",
        ]

        for category, category_entries in sorted(by_category.items()):
            lines.extend([f"## {category}", ""])
            lines.append(f"- Số tài liệu: {len(category_entries)}")
            lines.append(f"- File tóm tắt: [{CATEGORY_SUMMARY_NAME}]({self._slug(category)}/{CATEGORY_SUMMARY_NAME})")
            lines.append("")
            for entry in category_entries:
                tags_text = ", ".join(entry.get("tags") or [])
                lines.append(
                    f"- [{entry['title']}]({entry['path']}) - {entry['topic']}"
                    + (f" ({tags_text})" if tags_text else "")
                )
            lines.append("")

        (user_dir / INDEX_NAME).write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def _write_category_summaries(self, user_dir: Path, manifest: dict) -> None:
        entries = self._sorted_entries(manifest)
        by_category: dict[str, list[dict]] = {}
        for entry in entries:
            by_category.setdefault(entry["category"], []).append(entry)

        for category, category_entries in by_category.items():
            category_dir = user_dir / self._slug(category)
            category_dir.mkdir(parents=True, exist_ok=True)
            topics = sorted({entry["topic"] for entry in category_entries if entry.get("topic")})
            lines = [
                f"# {category}",
                "",
                f"Số tài liệu: {len(category_entries)}",
                f"Chủ đề: {', '.join(topics) if topics else 'Chưa xác định'}",
                "",
                "## Tài liệu",
                "",
            ]
            for entry in category_entries:
                lines.extend(
                    [
                        f"### [{entry['title']}]({Path(entry['path']).name})",
                        "",
                        f"- Chủ đề: {entry['topic']}",
                        f"- Tags: {', '.join(entry.get('tags') or []) if entry.get('tags') else 'Không có'}",
                        "",
                        entry.get("summary") or "Chưa có tóm tắt.",
                        "",
                    ]
                )
            (category_dir / CATEGORY_SUMMARY_NAME).write_text(
                "\n".join(lines).strip() + "\n",
                encoding="utf-8",
            )

    def _read_manifest(self, user_dir: Path) -> dict:
        manifest_path = user_dir / MANIFEST_NAME
        if not manifest_path.exists():
            return {"version": 1, "documents": {}, "updated_at": ""}
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"WikiService: cannot read manifest {manifest_path}: {exc}")
            return {"version": 1, "documents": {}, "updated_at": ""}

    @staticmethod
    def _write_manifest(user_dir: Path, manifest: dict) -> None:
        (user_dir / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _sorted_entries(manifest: dict) -> list[dict]:
        entries = list(manifest.get("documents", {}).values())
        return sorted(entries, key=lambda item: (item.get("category", ""), item.get("title", "")))

    @staticmethod
    def _normalize_summary(summary: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", summary).strip()

    @staticmethod
    def _fallback_summary(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) <= 700:
            return cleaned
        return cleaned[:700].rsplit(" ", 1)[0] + "..."

    def _user_dir(self, user_id: str) -> Path:
        return WIKI_ROOT / self._slug(user_id)

    @staticmethod
    def _slug(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "unknown")
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", ascii_value).strip("-._").lower()
        return slug[:120] or "unknown"


_wiki_service: WikiService | None = None


def get_wiki_service() -> WikiService:
    global _wiki_service
    if _wiki_service is None:
        _wiki_service = WikiService()
    return _wiki_service
