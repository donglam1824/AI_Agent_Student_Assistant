"""
Trích xuất và chia nhỏ tài liệu (PDF, DOCX, PPTX, TXT) thành chunks cho RAG.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.logger import logger

CHUNK_SIZE = 1000       
CHUNK_OVERLAP = 200     # Ký tự chồng lấp giữa các chunk
MARKDOWN_CACHE_DIR = Path(__file__).parent.parent / "data" / "markdown_cache"
OFFICE_EXTENSIONS = {".docx", ".pptx"}

_MARKER_UNAVAILABLE_REASON: Optional[str] = None


class DocumentLoader:
    """Tải và chia nhỏ tài liệu"""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        # Cắt theo dấu chấm nhưng giữ lại ký tự
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n# ",
                "\n## ",
                "\n### ",
                "\n#### ",
                "\n\n",
                "\n",
                r"(?<=\. )",
                " ",
                ""
            ],
            is_separator_regex=True
        )

    def load(self, file_path: str, metadata: Optional[dict] = None) -> List[Document]:
        """Tải file từ disk, chia nhỏ và trả về danh sách Document"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        metadata = metadata or {}
        ext = path.suffix.lower()
        logger.info(f"DocumentLoader: loading {path.name} ({ext})")

        if ext == ".pdf":
            raw_docs = self._load_pdf(path, metadata)
        elif ext in OFFICE_EXTENSIONS:
            raw_docs = self._load_office_with_markitdown(path)
        elif ext == ".txt":
            raw_docs = self._load_txt(path)
        else:
            raise ValueError(f"Định dạng không hỗ trợ: {ext}. Chỉ nhận PDF, DOCX, PPTX, TXT.")

        chunks = self._splitter.split_documents(raw_docs)
        for chunk in chunks:
            chunk.metadata.update(metadata)
        logger.info(f"DocumentLoader: {len(chunks)} chunks từ {path.name}")
        return chunks

    def load_from_text(self, text: str, metadata: dict) -> List[Document]:
        """Chia nhỏ text string nguồn Google Docs/Slides export"""
        if not text or not text.strip():
            logger.warning(f"DocumentLoader.load_from_text: text rỗng cho {metadata.get('source', '?')}")
            return []

        doc = Document(page_content=text, metadata=metadata)
        chunks = self._splitter.split_documents([doc])
        for chunk in chunks:
            chunk.metadata.update(metadata)

        logger.info(f"DocumentLoader.load_from_text: {len(chunks)} chunks từ '{metadata.get('source', '?')}'")
        return chunks

    def load_from_bytes(self, content: bytes, ext: str, metadata: dict) -> List[Document]:
        """Chia nhỏ file tải trực tiếp từ Drive/OneDrive dưới dạng bytes"""
        if not content:
            logger.warning(f"DocumentLoader.load_from_bytes: content rỗng cho {metadata.get('source', '?')}")
            return []

        ext = ext.lower()
        logger.info(f"DocumentLoader.load_from_bytes: xử lý {ext} ({len(content)} bytes)")

        # Lưu file tạm để parse
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            if ext == ".pdf":
                raw_docs = self._load_pdf(tmp_path, metadata)
            elif ext in OFFICE_EXTENSIONS:
                raw_docs = self._load_office_with_markitdown(tmp_path)
            elif ext in (".txt", ".csv"):
                raw_docs = self._load_txt(tmp_path)
            else:
                raise ValueError(f"Extension không hỗ trợ: {ext}")

            # Cập nhật thông tin Drive
            for doc in raw_docs:
                doc.metadata.update(metadata)

            chunks = self._splitter.split_documents(raw_docs)
            for chunk in chunks:
                chunk.metadata.update(metadata)

            logger.info(f"DocumentLoader.load_from_bytes: {len(chunks)} chunks")
            return chunks
        finally:
            tmp_path.unlink(missing_ok=True)

    def _load_pdf(self, path: Path, metadata: Optional[dict] = None) -> List[Document]:
        metadata = metadata or {}
        marker_doc = self._load_pdf_with_marker(path, metadata)
        if marker_doc:
            return [marker_doc]
        return self._load_pdf_with_pypdf(path, metadata)

    def _load_pdf_with_marker(self, path: Path, metadata: dict) -> Optional[Document]:
        global _MARKER_UNAVAILABLE_REASON

        if _MARKER_UNAVAILABLE_REASON:
            logger.info(f"DocumentLoader: skipping marker-pdf: {_MARKER_UNAVAILABLE_REASON}")
            return None

        cache_dir = self._get_markdown_cache_dir(path, metadata)
        markdown_path = cache_dir / "source.md"
        source_name = metadata.get("source") or path.name

        if markdown_path.exists():
            markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
            if markdown.strip():
                logger.info(f"DocumentLoader: using cached marker Markdown for {source_name}")
                return Document(
                    page_content=markdown,
                    metadata=self._marker_metadata(path, metadata, markdown_path, cache_dir, cached=True),
                )

        try:
            markdown = self._convert_pdf_to_markdown_with_marker(path, cache_dir)
        except Exception as e:
            if self._is_marker_environment_error(str(e)):
                _MARKER_UNAVAILABLE_REASON = str(e)
            logger.warning(f"DocumentLoader: marker failed for {source_name}, falling back to pypdf: {e}")
            return None

        if not markdown.strip():
            logger.warning(f"DocumentLoader: marker returned empty Markdown for {source_name}")
            return None

        self._write_marker_cache_metadata(path, metadata, cache_dir)
        return Document(
            page_content=markdown,
            metadata=self._marker_metadata(path, metadata, markdown_path, cache_dir, cached=False),
        )

    def _convert_pdf_to_markdown_with_marker(self, path: Path, cache_dir: Path) -> str:
        cache_dir.mkdir(parents=True, exist_ok=True)
        marker_cmd = self._marker_command()
        output_root = cache_dir / "_marker_output"
        if output_root.exists():
            shutil.rmtree(output_root)
        output_root.mkdir(parents=True, exist_ok=True)

        command = [
            marker_cmd,
            str(path),
            "--output_dir",
            str(output_root),
            "--output_format",
            "markdown",
            "--disable_multiprocessing",
            "--disable_image_extraction",
            "--disable_tqdm",
        ]
        if self._env_flag("ORCA_MARKER_DISABLE_OCR", default=True):
            command.append("--disable_ocr")

        env = os.environ.copy()
        env.setdefault("GRPC_VERBOSITY", "ERROR")
        env.setdefault("GLOG_minloglevel", "2")
        env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        env.setdefault("TOKENIZERS_PARALLELISM", "false")

        timeout = int(os.getenv("ORCA_MARKER_TIMEOUT_SECONDS", "240"))
        logger.info(f"DocumentLoader: running marker-pdf for {path.name}")
        try:
            result = subprocess.run(
                command,
                cwd=str(path.parent),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            shutil.rmtree(output_root, ignore_errors=True)
            raise RuntimeError(f"marker timed out after {timeout}s") from e

        if result.returncode != 0:
            error_tail = (result.stderr or result.stdout or "").strip()[-2000:]
            shutil.rmtree(output_root, ignore_errors=True)
            raise RuntimeError(error_tail or f"marker exited with code {result.returncode}")

        marker_markdown = next(output_root.rglob("*.md"), None)
        if marker_markdown is None:
            raise RuntimeError("marker did not produce a Markdown file")

        markdown = marker_markdown.read_text(encoding="utf-8", errors="ignore")
        (cache_dir / "source.md").write_text(markdown, encoding="utf-8")

        marker_meta = next(output_root.rglob("*_meta.json"), None)
        if marker_meta:
            shutil.copy2(marker_meta, cache_dir / "source_meta.json")

        shutil.rmtree(output_root, ignore_errors=True)
        return markdown

    def _marker_command(self) -> str:
        marker_cmd = shutil.which("marker_single")
        if marker_cmd:
            return marker_cmd

        scripts_dir = Path(sys.executable).parent / "Scripts"
        marker_exe = scripts_dir / "marker_single.exe"
        if marker_exe.exists():
            return str(marker_exe)

        raise RuntimeError("marker_single command not found")

    @staticmethod
    def _env_flag(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() not in {"0", "false", "no", "off"}

    @staticmethod
    def _is_marker_environment_error(message: str) -> bool:
        lowered = message.lower()
        return any(
            term in lowered
            for term in (
                "paging file is too small",
                "out of memory",
                "memoryerror",
                "cuda out of memory",
                "torchvision::nms",
                "marker_single command not found",
                "marker timed out",
            )
        )

    def _load_pdf_with_pypdf(self, path: Path, metadata: dict) -> List[Document]:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        docs = []
        source_name = metadata.get("source") or path.name
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                doc_metadata = {
                    "source": source_name,
                    "page": i + 1,
                    "file_path": str(path),
                    "parser": "pypdf",
                    "content_format": "text",
                }
                doc_metadata.update(metadata)
                docs.append(Document(
                    page_content=text,
                    metadata=doc_metadata,
                ))
        return docs

    def _get_markdown_cache_dir(self, path: Path, metadata: dict) -> Path:
        user_key = self._safe_path_part(str(metadata.get("user_id") or "anonymous"))
        source_key = (
            metadata.get("doc_id")
            or metadata.get("drive_file_id")
            or metadata.get("source")
            or path.stem
        )
        source_key = self._safe_path_part(str(source_key))
        content_hash = self._hash_file(path)[:12]
        return MARKDOWN_CACHE_DIR / user_key / f"{source_key}_{content_hash}"

    def _marker_metadata(
        self,
        path: Path,
        metadata: dict,
        markdown_path: Path,
        cache_dir: Path,
        cached: bool,
    ) -> dict:
        doc_metadata = {
            "source": metadata.get("source") or path.name,
            "file_path": str(path),
            "parser": "marker",
            "content_format": "markdown",
            "markdown_path": str(markdown_path),
            "markdown_cache_dir": str(cache_dir),
            "markdown_cached": cached,
        }
        doc_metadata.update(metadata)
        return doc_metadata

    def _write_marker_cache_metadata(self, path: Path, metadata: dict, cache_dir: Path) -> None:
        meta_path = cache_dir / "conversion_meta.json"
        cache_metadata = {
            "parser": "marker",
            "source": metadata.get("source") or path.name,
            "file_path": str(path),
            "content_hash": self._hash_file(path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
        }
        meta_path.write_text(
            json.dumps(cache_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _safe_path_part(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)
        cleaned = cleaned.strip("._")
        return cleaned[:120] or "unknown"

    def _load_office_with_markitdown(self, path: Path) -> List[Document]:
        try:
            from markitdown import MarkItDown
        except ImportError as e:
            raise RuntimeError(
                "MarkItDown is required to parse DOCX/PPTX files. "
                "Install backend requirements to enable Office document support."
            ) from e

        try:
            result = MarkItDown().convert(str(path))
        except Exception as e:
            raise RuntimeError(f"MarkItDown failed to parse {path.name}: {e}") from e

        markdown = (
            getattr(result, "text_content", None)
            or getattr(result, "markdown", None)
            or getattr(result, "text", None)
            or ""
        )
        if not markdown.strip():
            raise RuntimeError(f"MarkItDown returned empty content for {path.name}")

        return [Document(
            page_content=markdown,
            metadata={
                "source": path.name,
                "file_path": str(path),
                "parser": "markitdown",
                "content_format": "markdown",
            },
        )]

    def _load_txt(self, path: Path) -> List[Document]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [Document(
            page_content=text,
            metadata={"source": path.name, "file_path": str(path)},
        )]


# ── Hàm tương thích ngược ─────────────────────────────────────────────────────

def load_document(file_path: str, metadata: Optional[dict] = None) -> List[Document]:
    """Hàm helper tương thích ngược"""
    return DocumentLoader().load(file_path, metadata=metadata)
