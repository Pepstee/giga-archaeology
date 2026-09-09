"""Safe, replayable acquisition of public web sources for personal research.

Web pages are untrusted evidence, never instructions.  This module validates every
network hop before retrieval, caps response size, and writes raw
bytes plus deterministic text projections to an owner-only content-addressed archive.
It does not make claims, appraise evidence, or grant action authority.
"""

from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import math
import os
import re
import shutil
import socket
import subprocess
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from io import BytesIO
from itertools import pairwise
from pathlib import Path
from statistics import median
from typing import Any, ClassVar, Protocol
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

WEB_SOURCE_SCHEMA = "giga.research-web-source.v1"
WEB_ATTEMPT_SCHEMA = "giga.research-web-attempt.v1"
LOCAL_SOURCE_SCHEMA = "giga.research-local-source.v1"
DEFAULT_ARCHIVE = Path.home() / ".giga" / "research-web"
MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_PDF_PAGES = 250
MAX_PDF_TEXT_CHARACTERS = 5_000_000
MAX_PDF_TEXT_TABLES_PER_PAGE = 100
MAX_PDF_TEXT_TABLE_CELLS_PER_PAGE = 10_000
MAX_PDF_TEXT_TABLE_LAYOUT_OBJECTS = 200_000
PDF_OCR_RENDER_DPI = 200
MAX_PDF_OCR_RENDER_PIXELS = 20_000_000
MAX_PDF_OCR_RENDER_BYTES = 40 * 1024 * 1024
PDF_OCR_TIMEOUT_SECONDS = 60
MAX_VISUAL_TABLE_MODEL_BYTES = 32 * 1024 * 1024
MAX_VISUAL_TABLES_PER_PAGE = 10
MAX_VISUAL_TABLE_CELLS_PER_PAGE = 1_000
MAX_VISUAL_TABLE_QUADRILATERAL_EDGE_OVERSHOOT = 8.0
_VISUAL_TABLE_PACKAGE = "rapid-table"
_VISUAL_TABLE_PACKAGE_VERSION = "3.0.2"
_VISUAL_TABLE_TQDM_VERSION = "4.70.0"
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/pdf",
    "application/xhtml+xml",
    "text/html",
    "text/plain",
}
_LOCAL_SUFFIX_CONTENT_TYPES = {
    ".csv": "text/csv",
    ".htm": "text/html",
    ".html": "text/html",
    ".json": "application/json",
    ".markdown": "text/markdown",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".rst": "text/plain",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
}
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_PROMPT_INJECTION_SIGNALS = (
    re.compile(r"\bignore (?:all |any )?(?:previous|prior|system) instructions?\b", re.IGNORECASE),
    re.compile(r"\b(?:system|developer) (?:message|prompt|instructions?)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:reveal|exfiltrate|print|send) (?:the )?(?:secret|token|password|api key)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:call|use|invoke) (?:the )?(?:tool|shell|terminal|browser)\b", re.IGNORECASE),
)
_OCR_TSV_COLUMNS = (
    "level",
    "page_num",
    "block_num",
    "par_num",
    "line_num",
    "word_num",
    "left",
    "top",
    "width",
    "height",
    "conf",
    "text",
)
_PDF_TEXT_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
}


class WebAcquisitionError(ValueError):
    """A public source could not be acquired within the research safety contract."""


@dataclass(frozen=True)
class WebResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    fetched_at: str


@dataclass(frozen=True)
class _OcrRuntime:
    renderer: str
    renderer_version: str
    tesseract: str
    tesseract_version: str
    languages: tuple[tuple[str, str], ...]

    @property
    def projection(self) -> str:
        language_receipt = ",".join(
            f"{language}:{digest}" for language, digest in self.languages
        )
        return (
            f"tesseract:{self.tesseract_version};pdftoppm:{self.renderer_version};"
            f"languages:{language_receipt};layout:tsv-table:v1"
        )


@dataclass(frozen=True)
class _VisualTableConfig:
    model_path: Path
    model_sha256: str


@dataclass(frozen=True)
class _VisualTableRegion:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class _VisualTableRuntime:
    model_sha256: str
    rapid_table_version: str
    onnxruntime_version: str
    tqdm_version: str
    engine: Any

    @property
    def projection(self) -> str:
        return (
            f"rapid-table:{self.rapid_table_version};"
            f"onnxruntime:{self.onnxruntime_version};"
            f"tqdm:{self.tqdm_version};"
            f"model:{self.model_sha256};"
            "crop:opencv-line-grid:v1"
        )


@dataclass(frozen=True)
class _OcrWord:
    block: int
    paragraph: int
    line: int
    word: int
    left: int
    top: int
    width: int
    height: int
    confidence: float
    text: str


@dataclass(frozen=True)
class ArchivedWebSource:
    schema_version: str
    requested_url: str
    final_url: str
    redirect_chain: tuple[str, ...]
    status: int
    content_type: str
    content_sha256: str
    content_bytes: int
    text_sha256: str | None
    text_characters: int
    text_projection: str | None
    trust_class: str
    prompt_injection_signals: tuple[str, ...]
    fetched_at: str
    archived_at: str
    transport: str
    network_attempt_sha256s: tuple[str, ...]
    receipt_path: Path
    receipt_sha256: str


@dataclass(frozen=True)
class ArchivedLocalDocument:
    schema_version: str
    source_kind: str
    display_name: str
    requested_url: str
    final_url: str
    content_type: str
    content_sha256: str
    content_bytes: int
    text_sha256: str
    text_characters: int
    text_projection: str
    trust_class: str
    prompt_injection_signals: tuple[str, ...]
    archived_at: str
    receipt_path: Path
    receipt_sha256: str


class WebTransport(Protocol):
    name: str

    def fetch(self, url: str, *, timeout_seconds: int) -> WebResponse: ...


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _visual_table_config(
    model_path: Path | None,
    model_sha256: str | None,
) -> _VisualTableConfig | None:
    if model_path is None and model_sha256 is None:
        return None
    if model_path is None or model_sha256 is None:
        raise WebAcquisitionError(
            "visual table extraction requires both a local model path and its SHA-256"
        )
    expected = str(model_sha256).casefold()
    if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise WebAcquisitionError(
            "visual table model SHA-256 must be exactly 64 hexadecimal characters"
        )
    candidate = model_path.expanduser()
    if candidate.is_symlink():
        raise WebAcquisitionError("visual table model cannot be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise WebAcquisitionError("visual table model does not exist") from exc
    if not resolved.is_file():
        raise WebAcquisitionError("visual table model must be a regular file")
    size = resolved.stat().st_size
    if size < 1 or size > MAX_VISUAL_TABLE_MODEL_BYTES:
        raise WebAcquisitionError("visual table model is outside the bounded size envelope")
    actual = _sha256_path(resolved)
    if actual != expected:
        raise WebAcquisitionError("visual table model SHA-256 does not match the supplied identity")
    return _VisualTableConfig(model_path=resolved, model_sha256=actual)


def _visual_table_runtime(config: _VisualTableConfig) -> _VisualTableRuntime:
    try:
        rapid_table_version = installed_version(_VISUAL_TABLE_PACKAGE)
        tqdm_version = installed_version("tqdm")
        onnxruntime_version = installed_version("onnxruntime")
        from rapid_table import ModelType, RapidTable, RapidTableInput
    except (ImportError, PackageNotFoundError) as exc:
        raise WebAcquisitionError(
            "visual table extraction is unavailable; install the research-visual-table optional runtime"
        ) from exc
    if rapid_table_version != _VISUAL_TABLE_PACKAGE_VERSION:
        raise WebAcquisitionError(
            "visual table extraction requires rapid-table "
            f"{_VISUAL_TABLE_PACKAGE_VERSION}, not {rapid_table_version}"
        )
    if tqdm_version != _VISUAL_TABLE_TQDM_VERSION:
        raise WebAcquisitionError(
            "visual table extraction requires tqdm "
            f"{_VISUAL_TABLE_TQDM_VERSION}, not {tqdm_version}"
        )
    try:
        engine = RapidTable(
            RapidTableInput(
                model_type=ModelType.SLANETPLUS,
                model_dir_or_path=config.model_path,
                use_ocr=False,
                engine_cfg={"intra_op_num_threads": 1, "inter_op_num_threads": 1},
            )
        )
    except Exception as exc:
        raise WebAcquisitionError("visual table model could not initialise locally") from exc
    return _VisualTableRuntime(
        model_sha256=config.model_sha256,
        rapid_table_version=rapid_table_version,
        onnxruntime_version=onnxruntime_version,
        tqdm_version=tqdm_version,
        engine=engine,
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise WebAcquisitionError("fetch timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise WebAcquisitionError("fetch timestamp must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _admitted_content_type(*, declared: str, body: bytes) -> str:
    """Return the canonical projection type after a deliberately narrow PDF check."""
    if declared in ALLOWED_CONTENT_TYPES:
        return declared
    if declared == "application/octet-stream" and body.startswith(b"%PDF-"):
        return "application/pdf"
    raise WebAcquisitionError(f"unsupported source content type {declared!r}")


def _normalise_url(value: str) -> str:
    parts = urlsplit(value)
    if (
        parts.scheme.casefold() != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise WebAcquisitionError("source must be a credential-free, fragment-free HTTPS URL")
    host = parts.hostname.casefold().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        raise WebAcquisitionError("source cannot target localhost")
    port = parts.port
    if port not in (None, 443):
        raise WebAcquisitionError("source must use the standard HTTPS port")
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit(("https", netloc, parts.path or "/", parts.query, ""))


def _assert_public_host(
    url: str,
    *,
    resolver: Callable[..., Iterable[tuple]] = socket.getaddrinfo,
) -> None:
    host = urlsplit(url).hostname
    assert host is not None
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    if literal is not None:
        addresses.add(literal)
    else:
        try:
            for row in resolver(host, 443, type=socket.SOCK_STREAM):
                addresses.add(ipaddress.ip_address(row[4][0]))
        except (OSError, ValueError) as exc:
            raise WebAcquisitionError(f"cannot resolve public source host {host!r}") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise WebAcquisitionError("source resolves to a non-public network address")


def _private_archive(path: Path, repository_root: Path) -> Path:
    repository = repository_root.resolve(strict=True)
    archive = path.expanduser().resolve()
    if archive == repository or repository in archive.parents:
        raise WebAcquisitionError("web archive must live outside the repository")
    if archive.exists() and archive.is_symlink():
        raise WebAcquisitionError("web archive cannot be a symlink")
    archive.mkdir(parents=True, exist_ok=True)
    os.chmod(archive, 0o700)
    return archive


def _write_exact(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != value:
            raise WebAcquisitionError("content-addressed archive replay differs")
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


class _VisibleTextParser(HTMLParser):
    _ignored: ClassVar[set[str]] = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in self._ignored:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self._ignored and self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._depth:
            stripped = " ".join(data.split())
            if stripped:
                self.parts.append(stripped)


def _command_output(
    arguments: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = PDF_OCR_TIMEOUT_SECONDS,
    failure: str,
    include_stderr: bool = True,
) -> str:
    try:
        completed = subprocess.run(
            arguments,
            cwd=str(cwd) if cwd is not None else None,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WebAcquisitionError(failure) from exc
    if completed.returncode != 0:
        raise WebAcquisitionError(failure)
    outputs = (completed.stdout, completed.stderr) if include_stderr else (completed.stdout,)
    return "\n".join(part for part in outputs if part).strip()


def _tool_version(executable: str, argument: str, *, prefix: str) -> str:
    output = _command_output(
        [executable, argument],
        failure=f"scanned PDF OCR could not inspect {prefix}",
    )
    for line in output.splitlines():
        match = re.search(r"\b(?:version\s+)?([0-9]+(?:\.[0-9A-Za-z.+-]+)+)", line)
        if match:
            return match.group(1)
    raise WebAcquisitionError(f"scanned PDF OCR could not determine {prefix} version")


def _ocr_runtime() -> _OcrRuntime:
    renderer = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if renderer is None or tesseract is None:
        raise WebAcquisitionError(
            "scanned PDF OCR requires local pdftoppm and tesseract executables"
        )
    language_output = _command_output(
        [tesseract, "--list-langs"],
        failure="scanned PDF OCR could not inspect Tesseract language data",
    )
    root_match = re.search(r'List of available languages in "([^"\n]+)"', language_output)
    if root_match is None:
        raise WebAcquisitionError("scanned PDF OCR could not determine Tesseract data root")
    available = {
        line.strip()
        for line in language_output.splitlines()
        if re.fullmatch(r"[a-z0-9_]+", line.strip())
    }
    if "eng" not in available:
        raise WebAcquisitionError("scanned PDF OCR requires Tesseract English language data")
    selected = ["eng"]
    if "chi_sim" in available:
        selected.append("chi_sim")
    data_root = Path(root_match.group(1))
    language_hashes: list[tuple[str, str]] = []
    for language in selected:
        try:
            traineddata = (data_root / f"{language}.traineddata").resolve(strict=True)
        except OSError as exc:
            raise WebAcquisitionError(
                "scanned PDF OCR language data is not a readable regular file"
            ) from exc
        if not traineddata.is_file():
            raise WebAcquisitionError("scanned PDF OCR language data is not a regular file")
        language_hashes.append((language, _sha256(traineddata.read_bytes())))
    return _OcrRuntime(
        renderer=renderer,
        renderer_version=_tool_version(renderer, "-v", prefix="pdftoppm"),
        tesseract=tesseract,
        tesseract_version=_tool_version(tesseract, "--version", prefix="Tesseract"),
        languages=tuple(language_hashes),
    )


def _ocr_page_pixel_count(page: Any) -> int:
    try:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
    except (AttributeError, TypeError, ValueError) as exc:
        raise WebAcquisitionError("PDF OCR page dimensions are invalid") from exc
    if not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0:
        raise WebAcquisitionError("PDF OCR page dimensions are invalid")
    pixels = math.ceil(width * PDF_OCR_RENDER_DPI / 72) * math.ceil(
        height * PDF_OCR_RENDER_DPI / 72
    )
    if pixels > MAX_PDF_OCR_RENDER_PIXELS:
        raise WebAcquisitionError("PDF OCR page exceeds the rendering pixel limit")
    return pixels


def _ocr_words(tsv: str) -> list[_OcrWord]:
    reader = csv.DictReader(tsv.splitlines(), delimiter="\t")
    if tuple(reader.fieldnames or ()) != _OCR_TSV_COLUMNS:
        raise WebAcquisitionError("PDF OCR emitted an unexpected TSV schema")
    words: list[_OcrWord] = []
    for row in reader:
        try:
            if int(row["level"] or "") != 5:
                continue
            text = " ".join((row["text"] or "").replace("\x00", "").split())
            if not text:
                continue
            left = int(row["left"] or "")
            top = int(row["top"] or "")
            width = int(row["width"] or "")
            height = int(row["height"] or "")
            confidence = float(row["conf"] or "")
            identifiers = [
                int(row["block_num"] or ""),
                int(row["par_num"] or ""),
                int(row["line_num"] or ""),
                int(row["word_num"] or ""),
            ]
        except (TypeError, ValueError) as exc:
            raise WebAcquisitionError("PDF OCR emitted malformed TSV values") from exc
        if (
            left < 0
            or top < 0
            or width < 1
            or height < 1
            or not math.isfinite(confidence)
            or confidence < -1
            or confidence > 100
            or any(value < 0 for value in identifiers)
        ):
            raise WebAcquisitionError("PDF OCR emitted unsafe TSV geometry")
        words.append(
            _OcrWord(
                block=identifiers[0],
                paragraph=identifiers[1],
                line=identifiers[2],
                word=identifiers[3],
                left=left,
                top=top,
                width=width,
                height=height,
                confidence=confidence,
                text=text,
            )
        )
    if not words:
        raise WebAcquisitionError("PDF OCR produced no readable words")
    return words


def _ocr_bounds(words: Iterable[_OcrWord]) -> tuple[int, int, int, int]:
    values = list(words)
    left = min(word.left for word in values)
    top = min(word.top for word in values)
    right = max(word.left + word.width for word in values)
    bottom = max(word.top + word.height for word in values)
    return left, top, right - left, bottom - top


def _ocr_lines(words: Iterable[_OcrWord]) -> list[tuple[tuple[int, int, int], list[_OcrWord]]]:
    grouped: dict[tuple[int, int, int], list[_OcrWord]] = {}
    for word in words:
        grouped.setdefault((word.block, word.paragraph, word.line), []).append(word)
    return sorted(
        (
            (key, sorted(line, key=lambda item: (item.word, item.left, item.top, item.text)))
            for key, line in grouped.items()
        ),
        key=lambda item: (
            min(word.top for word in item[1]),
            min(word.left for word in item[1]),
            item[0],
        ),
    )


def _ocr_cells(words: list[_OcrWord]) -> list[list[_OcrWord]]:
    """Segment obvious horizontal gaps into auditable geometric table cells."""
    ordered = sorted(words, key=lambda word: (word.left, word.top, word.word, word.text))
    if not ordered:
        return []
    gaps = [
        next_word.left - (word.left + word.width)
        for word, next_word in pairwise(ordered)
    ]
    # Table rows can contain one token per cell, so there is no reliable
    # within-cell gap sample. Scale the boundary to ordinary word geometry;
    # only a gap larger than an entire normal word separates a cell.
    baseline_height = median(word.height for word in ordered)
    baseline_width = median(word.width for word in ordered)
    boundary = max(24.0, baseline_height * 1.5, baseline_width * 0.75)
    cells: list[list[_OcrWord]] = [[ordered[0]]]
    for gap, word in zip(gaps, ordered[1:], strict=True):
        if gap > boundary:
            cells.append([word])
        else:
            cells[-1].append(word)
    return cells


def _ocr_table_rows(
    lines: list[tuple[tuple[int, int, int], list[_OcrWord]]]
) -> list[list[list[_OcrWord]]]:
    by_block: dict[int, list[list[_OcrWord]]] = {}
    for (block, _, _), words in lines:
        by_block.setdefault(block, []).append(words)
    candidates: list[list[list[_OcrWord]]] = []
    for block_lines in by_block.values():
        rows = [_ocr_cells(words) for words in block_lines]
        populated = [row for row in rows if len(row) >= 2]
        if len(populated) < 3:
            continue
        column_counts = [len(row) for row in populated]
        columns = max(set(column_counts), key=lambda value: (column_counts.count(value), value))
        matched = [row for row in populated if len(row) == columns]
        if columns >= 2 and len(matched) >= 3:
            candidates.append(matched)
    return candidates


def _format_ocr_page(
    *, page_number: int, words: list[_OcrWord], runtime: _OcrRuntime
) -> str:
    lines = _ocr_lines(words)
    output = [
        (
            f"[Page {page_number} OCR backend=tesseract:{runtime.tesseract_version} "
            f"renderer=pdftoppm:{runtime.renderer_version} "
            f"languages={'+'.join(language for language, _ in runtime.languages)}]"
        )
    ]
    for (block, paragraph, line), line_words in lines:
        left, top, width, height = _ocr_bounds(line_words)
        confidence = sum(word.confidence for word in line_words) / len(line_words)
        output.append(
            f"[OCR Line page={page_number} block={block} paragraph={paragraph} "
            f"line={line} x={left} y={top} width={width} height={height} "
            f"confidence={confidence:.3f}]"
        )
        output.append(" ".join(word.text for word in line_words))
    for table_number, rows in enumerate(_ocr_table_rows(lines), start=1):
        output.append(
            f"[OCR Table Candidate page={page_number} table={table_number} "
            f"rows={len(rows)} columns={len(rows[0])}]"
        )
        for row_number, cells in enumerate(rows, start=1):
            for column_number, cell_words in enumerate(cells, start=1):
                left, top, width, height = _ocr_bounds(cell_words)
                confidence = sum(word.confidence for word in cell_words) / len(cell_words)
                output.append(
                    f"[OCR Cell page={page_number} table={table_number} row={row_number} "
                    f"column={column_number} x={left} y={top} width={width} "
                    f"height={height} confidence={confidence:.3f}]"
                )
                output.append(" ".join(word.text for word in cell_words))
    return "\n".join(output)


def _visual_table_regions(rendered: Path) -> tuple[Any, tuple[_VisualTableRegion, ...]]:
    try:
        import cv2
    except ImportError as exc:
        raise WebAcquisitionError(
            "visual table extraction is unavailable; install the "
            "research-visual-table optional runtime"
        ) from exc
    image = cv2.imread(str(rendered), cv2.IMREAD_COLOR)
    if image is None or len(image.shape) != 3 or image.shape[2] != 3:
        raise WebAcquisitionError("visual table renderer did not produce a readable colour image")
    height, width = (int(value) for value in image.shape[:2])
    if height < 1 or width < 1:
        raise WebAcquisitionError("visual table renderer produced an empty image")
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.threshold(
        grayscale,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (min(width, max(15, width // 30)), 1),
    )
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, min(height, max(15, height // 30))),
    )
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    grid = cv2.bitwise_or(horizontal, vertical)
    grid = cv2.dilate(
        grid,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)),
        iterations=1,
    )
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    minimum_width = max(64, width // 4)
    minimum_height = max(32, height // 20)
    regions: list[_VisualTableRegion] = []
    for contour in contours:
        x, y, candidate_width, candidate_height = (
            int(value) for value in cv2.boundingRect(contour)
        )
        if (
            candidate_width < minimum_width
            or candidate_height < minimum_height
            or x < 0
            or y < 0
            or x + candidate_width > width
            or y + candidate_height > height
        ):
            continue
        regions.append(
            _VisualTableRegion(
                x=x,
                y=y,
                width=candidate_width,
                height=candidate_height,
            )
        )
    if len(regions) > MAX_VISUAL_TABLES_PER_PAGE:
        raise WebAcquisitionError("PDF page exceeds the visual table-candidate limit")
    return image, tuple(sorted(regions, key=lambda region: (region.y, region.x)))


def _visual_table_index(value: object, *, label: str) -> int:
    if isinstance(value, bool):
        raise WebAcquisitionError(f"visual table model emitted an invalid {label}")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise WebAcquisitionError(f"visual table model emitted an invalid {label}") from exc
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric < 0:
        raise WebAcquisitionError(f"visual table model emitted an invalid {label}")
    return int(numeric)


def _visual_table_cell_bounds(
    value: object,
    *,
    region: _VisualTableRegion,
) -> tuple[float, float, float, float, str]:
    try:
        values = list(value)
    except TypeError as exc:
        raise WebAcquisitionError("visual table model emitted invalid cell geometry") from exc
    if len(values) == 4:
        left, top, right, bottom = (
            _pdf_table_coordinate(coordinate, label=label)
            for coordinate, label in zip(
                values,
                ("left", "top", "right", "bottom"),
                strict=True,
            )
        )
        geometry_kind = "axis-aligned"
    elif len(values) == 8:
        points = [
            (
                _pdf_table_coordinate(values[index], label=f"point {index // 2 + 1} x"),
                _pdf_table_coordinate(
                    values[index + 1], label=f"point {index // 2 + 1} y"
                ),
            )
            for index in range(0, 8, 2)
        ]
        left = min(point[0] for point in points)
        right = max(point[0] for point in points)
        top = min(point[1] for point in points)
        bottom = max(point[1] for point in points)
        geometry_kind = "quadrilateral-bounding-box"
    else:
        raise WebAcquisitionError("visual table model emitted invalid cell geometry")
    if right <= left or bottom <= top:
        raise WebAcquisitionError("visual table model emitted unsafe cell geometry")
    if geometry_kind == "quadrilateral-bounding-box":
        if (
            left < -MAX_VISUAL_TABLE_QUADRILATERAL_EDGE_OVERSHOOT
            or top < -MAX_VISUAL_TABLE_QUADRILATERAL_EDGE_OVERSHOOT
            or right > region.width + MAX_VISUAL_TABLE_QUADRILATERAL_EDGE_OVERSHOOT
            or bottom > region.height + MAX_VISUAL_TABLE_QUADRILATERAL_EDGE_OVERSHOOT
        ):
            raise WebAcquisitionError("visual table model emitted unsafe cell geometry")
        clipped = left < 0 or top < 0 or right > region.width or bottom > region.height
        left = max(0.0, left)
        top = max(0.0, top)
        right = min(float(region.width), right)
        bottom = min(float(region.height), bottom)
        if right <= left or bottom <= top:
            raise WebAcquisitionError("visual table model emitted unsafe cell geometry")
        if clipped:
            geometry_kind = "quadrilateral-clipped-bounding-box"
    elif (
        left < 0
        or top < 0
        or right > region.width
        or bottom > region.height
    ):
        raise WebAcquisitionError("visual table model emitted unsafe cell geometry")
    return (
        region.x + left,
        region.y + top,
        right - left,
        bottom - top,
        geometry_kind,
    )


def _format_visual_table_candidates(
    *,
    page_number: int,
    rendered: Path,
    runtime: _VisualTableRuntime,
) -> str:
    image, regions = _visual_table_regions(rendered)
    output: list[str] = []
    cells_on_page = 0
    table_number = 0
    for region in regions:
        crop = image[region.y : region.y + region.height, region.x : region.x + region.width]
        try:
            result = runtime.engine(crop)
            cell_bboxes = result.cell_bboxes
            logic_points = result.logic_points
        except Exception as exc:
            raise WebAcquisitionError("visual table model inference failed") from exc
        if len(cell_bboxes) != 1 or len(logic_points) != 1:
            raise WebAcquisitionError("visual table model emitted an invalid batch result")
        cells = cell_bboxes[0]
        logic = logic_points[0]
        if len(cells) != len(logic):
            raise WebAcquisitionError("visual table model emitted inconsistent cell logic")
        if len(cells) == 0:
            continue
        if len(cells) > MAX_VISUAL_TABLE_CELLS_PER_PAGE - cells_on_page:
            raise WebAcquisitionError("PDF page exceeds the visual table-cell limit")
        table_number += 1
        output.append(
            f"[OCR Visual Table Candidate page={page_number} table={table_number} "
            f"x={region.x} y={region.y} width={region.width} height={region.height} "
            f"cells={len(cells)} detector={runtime.projection}]"
        )
        for cell_number, (bounds, point) in enumerate(zip(cells, logic, strict=True), start=1):
            cell_x, cell_y, cell_width, cell_height, geometry_kind = _visual_table_cell_bounds(
                bounds,
                region=region,
            )
            try:
                indices = list(point)
            except TypeError as exc:
                raise WebAcquisitionError("visual table model emitted invalid cell logic") from exc
            if len(indices) != 4:
                raise WebAcquisitionError("visual table model emitted invalid cell logic")
            row_start, row_end, column_start, column_end = (
                _visual_table_index(value, label=label)
                for value, label in zip(
                    indices,
                    ("row start", "row end", "column start", "column end"),
                    strict=True,
                )
            )
            if row_end < row_start or column_end < column_start:
                raise WebAcquisitionError("visual table model emitted invalid cell logic")
            output.append(
                f"[OCR Visual Table Cell page={page_number} table={table_number} "
                f"cell={cell_number} x={_pdf_table_geometry(cell_x)} "
                f"y={_pdf_table_geometry(cell_y)} width={_pdf_table_geometry(cell_width)} "
                f"height={_pdf_table_geometry(cell_height)} model_geometry={geometry_kind} "
                f"model_row_start={row_start} "
                f"model_row_end={row_end} model_column_start={column_start} "
                f"model_column_end={column_end}]"
            )
        cells_on_page += len(cells)
    return "\n".join(output)


def _project_scanned_pdf_page(
    source: Path,
    *,
    page_number: int,
    page: Any,
    workspace: Path,
    runtime: _OcrRuntime,
    visual_table_runtime: _VisualTableRuntime | None = None,
) -> str:
    _ocr_page_pixel_count(page)
    prefix = f"ocr-page-{page_number}"
    _command_output(
        [
            runtime.renderer,
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-r",
            str(PDF_OCR_RENDER_DPI),
            "-png",
            source.name,
            prefix,
        ],
        cwd=workspace,
        failure="PDF OCR rendering failed",
    )
    rendered = sorted(workspace.glob(f"{prefix}-*.png"))
    if len(rendered) != 1 or rendered[0].is_symlink() or not rendered[0].is_file():
        raise WebAcquisitionError("PDF OCR did not produce one regular page image")
    if rendered[0].stat().st_size > MAX_PDF_OCR_RENDER_BYTES:
        raise WebAcquisitionError("PDF OCR rendered page exceeds the byte limit")
    tsv = _command_output(
        [
            runtime.tesseract,
            rendered[0].name,
            "stdout",
            "-l",
            "+".join(language for language, _ in runtime.languages),
            "--psm",
            "3",
            "tsv",
        ],
        # Tesseract on this runtime rejects absolute input paths. The source and
        # rendered image are private regular files in this per-projection directory.
        cwd=workspace,
        failure="PDF OCR recognition failed",
        include_stderr=False,
    )
    rendered_text = _format_ocr_page(
        page_number=page_number,
        words=_ocr_words(tsv),
        runtime=runtime,
    )
    if visual_table_runtime is not None:
        visual_tables = _format_visual_table_candidates(
            page_number=page_number,
            rendered=rendered[0],
            runtime=visual_table_runtime,
        )
        if visual_tables:
            rendered_text = f"{rendered_text}\n{visual_tables}"
    return rendered_text


def _pdf_table_coordinate(value: object, *, label: str) -> float:
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise WebAcquisitionError(f"PDF table extractor emitted an invalid {label}") from exc
    if not math.isfinite(coordinate):
        raise WebAcquisitionError(f"PDF table extractor emitted an invalid {label}")
    return coordinate


def _pdf_table_bounds(bounds: object, *, page: Any) -> tuple[float, float, float, float]:
    if not isinstance(bounds, tuple) or len(bounds) != 4:
        raise WebAcquisitionError("PDF table extractor emitted invalid cell geometry")
    x0, top, x1, bottom = (
        _pdf_table_coordinate(value, label=label)
        for value, label in zip(bounds, ("x0", "top", "x1", "bottom"), strict=True)
    )
    page_width = _pdf_table_coordinate(getattr(page, "width", None), label="page width")
    page_height = _pdf_table_coordinate(getattr(page, "height", None), label="page height")
    if (
        page_width <= 0
        or page_height <= 0
        or x0 < 0
        or top < 0
        or x1 <= x0
        or bottom <= top
        or x1 > page_width
        or bottom > page_height
    ):
        raise WebAcquisitionError("PDF table extractor emitted unsafe cell geometry")
    return x0, top, x1 - x0, bottom - top


def _pdf_table_geometry(value: float) -> str:
    return f"{value:.3f}"


def _format_pdf_text_table_candidates(
    *, page_number: int, page: Any, pdfplumber_version: str
) -> str:
    """Emit bounded geometric table candidates without inferring table semantics."""
    try:
        layout_objects = sum(
            len(getattr(page, attribute))
            for attribute in ("chars", "lines", "rects", "curves")
        )
    except (AttributeError, TypeError) as exc:
        raise WebAcquisitionError("PDF table extractor emitted an unreadable page layout") from exc
    if layout_objects > MAX_PDF_TEXT_TABLE_LAYOUT_OBJECTS:
        raise WebAcquisitionError("PDF table layout exceeds the object limit")
    try:
        tables = page.find_tables(table_settings=_PDF_TEXT_TABLE_SETTINGS)
    except Exception as exc:
        raise WebAcquisitionError("PDF table candidate extraction failed") from exc
    if len(tables) > MAX_PDF_TEXT_TABLES_PER_PAGE:
        raise WebAcquisitionError("PDF page exceeds the table-candidate limit")

    output: list[str] = []
    candidate_number = 0
    cells_on_page = 0
    for table in tables:
        try:
            rows = table.extract()
            row_geometries = table.rows
            columns = table.columns
        except Exception as exc:
            raise WebAcquisitionError("PDF table extractor emitted unreadable table data") from exc
        if not isinstance(rows, list) or len(rows) != len(row_geometries):
            raise WebAcquisitionError("PDF table extractor emitted inconsistent row geometry")
        if len(rows) < 2 or len(columns) < 2:
            continue
        cells_in_table = len(rows) * len(columns)
        if cells_in_table > MAX_PDF_TEXT_TABLE_CELLS_PER_PAGE - cells_on_page:
            raise WebAcquisitionError("PDF page exceeds the table-cell limit")
        table_x, table_y, table_width, table_height = _pdf_table_bounds(table.bbox, page=page)
        candidate_number += 1
        output.append(
            f"[PDF Text Table Candidate page={page_number} table={candidate_number} "
            f"rows={len(rows)} columns={len(columns)} x={_pdf_table_geometry(table_x)} "
            f"y={_pdf_table_geometry(table_y)} width={_pdf_table_geometry(table_width)} "
            f"height={_pdf_table_geometry(table_height)} detector=pdfplumber:{pdfplumber_version} "
            "strategy=lines]"
        )
        for row_number, (values, row_geometry) in enumerate(
            zip(rows, row_geometries, strict=True), start=1
        ):
            cells = row_geometry.cells
            if not isinstance(values, list) or len(values) != len(cells):
                raise WebAcquisitionError("PDF table extractor emitted inconsistent cell geometry")
            for column_number, (value, bounds) in enumerate(zip(values, cells, strict=True), start=1):
                if value is not None and not isinstance(value, str):
                    raise WebAcquisitionError("PDF table extractor emitted non-text cell data")
                text = (value or "").replace("\x00", "").strip()
                if bounds is None:
                    if text:
                        raise WebAcquisitionError("PDF table extractor emitted text without cell geometry")
                    output.append(
                        f"[PDF Text Table Cell page={page_number} table={candidate_number} "
                        f"row={row_number} column={column_number} geometry=unavailable empty=true]"
                    )
                    continue
                cell_x, cell_y, cell_width, cell_height = _pdf_table_bounds(bounds, page=page)
                empty = str(not text).lower()
                output.append(
                    f"[PDF Text Table Cell page={page_number} table={candidate_number} "
                    f"row={row_number} column={column_number} x={_pdf_table_geometry(cell_x)} "
                    f"y={_pdf_table_geometry(cell_y)} width={_pdf_table_geometry(cell_width)} "
                    f"height={_pdf_table_geometry(cell_height)} empty={empty}]"
                )
                if text:
                    output.append(text)
        cells_on_page += cells_in_table
    return "\n".join(output)


def _project_pdf_text(
    body: bytes,
    *,
    visual_table_config: _VisualTableConfig | None = None,
) -> tuple[str, str]:
    try:
        import pdfplumber
        import pypdf
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError as exc:
        raise WebAcquisitionError(
            "PDF extraction is unavailable; install the research-web optional runtime"
        ) from exc
    try:
        reader = PdfReader(BytesIO(body), strict=True)
        if reader.is_encrypted:
            raise WebAcquisitionError("encrypted PDFs cannot be projected")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise WebAcquisitionError(f"PDF exceeds the {MAX_PDF_PAGES}-page projection limit")
        with pdfplumber.open(BytesIO(body), strict_metadata=True) as table_document:
            if len(table_document.pages) != len(reader.pages):
                raise WebAcquisitionError("PDF table extractor disagrees with the page count")
            parts: list[str] = []
            characters = 0
            runtime: _OcrRuntime | None = None
            visual_table_runtime: _VisualTableRuntime | None = None
            workspace: tempfile.TemporaryDirectory[str] | None = None
            try:
                for number, (page, table_page) in enumerate(
                    zip(reader.pages, table_document.pages, strict=True), start=1
                ):
                    page_text = (page.extract_text() or "").replace("\x00", "").strip()
                    if page_text:
                        rendered_text = f"[Page {number}]\n{page_text}"
                        table_candidates = _format_pdf_text_table_candidates(
                            page_number=number,
                            page=table_page,
                            pdfplumber_version=pdfplumber.__version__,
                        )
                        if table_candidates:
                            rendered_text = f"{rendered_text}\n{table_candidates}"
                    else:
                        if runtime is None:
                            runtime = _ocr_runtime()
                            workspace = tempfile.TemporaryDirectory(prefix="giga-pdf-ocr-")
                            source = Path(workspace.name) / "source.pdf"
                            source.write_bytes(body)
                            os.chmod(source, 0o600)
                        if visual_table_config is not None and visual_table_runtime is None:
                            visual_table_runtime = _visual_table_runtime(visual_table_config)
                        assert workspace is not None
                        rendered_text = _project_scanned_pdf_page(
                            source,
                            page_number=number,
                            page=page,
                            workspace=Path(workspace.name),
                            runtime=runtime,
                            visual_table_runtime=visual_table_runtime,
                        )
                    characters += len(rendered_text)
                    if characters > MAX_PDF_TEXT_CHARACTERS:
                        raise WebAcquisitionError("PDF text projection exceeds the character limit")
                    parts.append(rendered_text)
            finally:
                if workspace is not None:
                    workspace.cleanup()
    except WebAcquisitionError:
        raise
    except (OSError, PyPdfError, RecursionError, TypeError, ValueError) as exc:
        raise WebAcquisitionError("PDF text projection failed") from exc
    except Exception as exc:
        raise WebAcquisitionError("PDF text-table projection failed") from exc
    projection = (
        f"pypdf:{pypdf.__version__}+text-table-candidates:"
        f"pdfplumber:{pdfplumber.__version__};strategy:lines:v1"
    )
    if runtime is not None:
        projection = f"{projection}+scanned-ocr:{runtime.projection}"
    if visual_table_runtime is not None:
        projection = f"{projection}+scanned-visual-table:{visual_table_runtime.projection}"
    return "\n\n".join(parts), projection


def _project_text(
    body: bytes,
    content_type: str,
    *,
    visual_table_config: _VisualTableConfig | None = None,
) -> tuple[str | None, str | None]:
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = _VisibleTextParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        return "\n".join(parser.parts), "giga-visible-html:v1"
    if content_type == "text/plain":
        text = body.decode("utf-8", errors="replace").replace("\x00", "")
        return text, "utf8-replace:v1"
    if content_type in {"text/csv", "text/markdown", "text/tab-separated-values"}:
        text = body.decode("utf-8", errors="replace").replace("\x00", "")
        return text, f"utf8-replace:{content_type}:v1"
    if content_type == "application/json":
        try:
            value = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebAcquisitionError("source declares invalid JSON") from exc
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        return text, "canonical-json:v1"
    if content_type == "application/pdf":
        return _project_pdf_text(body, visual_table_config=visual_table_config)
    return None, None


def _injection_signals(text: str | None) -> tuple[str, ...]:
    if not text:
        return ()
    return tuple(pattern.pattern for pattern in _PROMPT_INJECTION_SIGNALS if pattern.search(text))


class ScraplingTransport:
    """One-hop Scrapling transport; redirect policy remains in this module."""

    def __init__(self, mode: str = "static") -> None:
        if mode not in {"static", "dynamic", "stealth"}:
            raise WebAcquisitionError("Scrapling mode must be static, dynamic, or stealth")
        self.mode = mode
        self.name = f"scrapling:{mode}"

    def fetch(self, url: str, *, timeout_seconds: int) -> WebResponse:
        try:
            from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher
        except ImportError as exc:
            raise WebAcquisitionError(
                "Scrapling fetchers are unavailable; install the research-web optional runtime"
            ) from exc
        fetcher = {
            "static": Fetcher,
            "dynamic": DynamicFetcher,
            "stealth": StealthyFetcher,
        }[self.mode]
        options: dict[str, object] = {
            "timeout": timeout_seconds,
            "follow_redirects": False,
        }
        if self.mode == "static":
            options["stealthy_headers"] = True
        page = fetcher.get(url, **options)
        headers = {
            str(key).casefold(): str(value) for key, value in dict(page.headers or {}).items()
        }
        return WebResponse(
            url=url,
            status=int(page.status),
            headers=headers,
            body=bytes(page.body),
            fetched_at=_utc_now(),
        )


class PublicWebAcquirer:
    """Acquire one public source and preserve an immutable, inspectable receipt."""

    def __init__(
        self,
        *,
        repository_root: Path,
        archive_root: Path = DEFAULT_ARCHIVE,
        transport: WebTransport | None = None,
        resolver: Callable[..., Iterable[tuple]] = socket.getaddrinfo,
        timeout_seconds: int = 30,
        maximum_bytes: int = MAX_SOURCE_BYTES,
        visual_table_model: Path | None = None,
        visual_table_model_sha256: str | None = None,
    ) -> None:
        self.archive = _private_archive(archive_root, repository_root)
        self.transport = transport or ScraplingTransport()
        self.resolver = resolver
        self.timeout_seconds = max(1, min(int(timeout_seconds), 60))
        self.maximum_bytes = max(1, min(int(maximum_bytes), MAX_SOURCE_BYTES))
        self.visual_table_config = _visual_table_config(
            visual_table_model,
            visual_table_model_sha256,
        )

    def _archive_network_attempt(self, response: WebResponse) -> tuple[str, Path]:
        content_hash = _sha256(response.body)
        _write_exact(self.archive / "objects" / content_hash[:2] / content_hash, response.body)
        receipt = {
            "schema_version": WEB_ATTEMPT_SCHEMA,
            "url": response.url,
            "status": response.status,
            "content_type": response.headers.get("content-type"),
            "location": response.headers.get("location"),
            "content_sha256": content_hash,
            "content_bytes": len(response.body),
            "fetched_at": _timestamp(response.fetched_at),
            "transport": self.transport.name,
            "trust_class": "untrusted_external_network_attempt",
        }
        raw = _canonical_bytes(receipt)
        digest = _sha256(raw)
        path = self.archive / "attempts" / digest[:2] / f"{digest}.json"
        _write_exact(path, raw)
        return digest, path

    def _fetch_hop(self, url: str) -> tuple[WebResponse, str]:
        safe = _normalise_url(url)
        _assert_public_host(safe, resolver=self.resolver)
        response = self.transport.fetch(safe, timeout_seconds=self.timeout_seconds)
        if response.url != safe:
            raise WebAcquisitionError("transport substituted the validated URL")
        if len(response.body) > self.maximum_bytes:
            raise WebAcquisitionError("source exceeds the configured byte limit")
        attempt_sha, _ = self._archive_network_attempt(response)
        return response, attempt_sha

    def acquire(self, url: str) -> ArchivedWebSource:
        requested = _normalise_url(url)
        _assert_public_host(requested, resolver=self.resolver)

        chain = [requested]
        current = requested
        response: WebResponse | None = None
        network_attempts: list[str] = []
        for _ in range(MAX_REDIRECTS + 1):
            response, attempt_sha = self._fetch_hop(current)
            network_attempts.append(attempt_sha)
            if response.status not in _REDIRECT_STATUSES:
                break
            location = response.headers.get("location")
            if not location:
                raise WebAcquisitionError("redirect response has no Location header")
            next_url = _normalise_url(urljoin(current, location))
            _assert_public_host(next_url, resolver=self.resolver)
            if next_url in chain:
                raise WebAcquisitionError("redirect loop detected")
            chain.append(next_url)
            current = next_url
        else:
            raise WebAcquisitionError("source exceeds the redirect limit")

        assert response is not None
        if response.status != 200 or not response.body:
            raise WebAcquisitionError(
                "source did not return a non-empty HTTP 200 response; "
                f"network attempt {network_attempts[-1]}"
            )
        declared_content_type = (
            response.headers.get("content-type", "").split(";", 1)[0].strip().casefold()
        )
        content_type = _admitted_content_type(
            declared=declared_content_type,
            body=response.body,
        )

        fetched_at = _timestamp(response.fetched_at)
        content_hash = _sha256(response.body)
        text, text_projection = _project_text(
            response.body,
            content_type,
            visual_table_config=self.visual_table_config,
        )
        text_bytes = text.encode("utf-8") if text is not None else None
        text_hash = _sha256(text_bytes) if text_bytes is not None else None
        signals = _injection_signals(text)
        archived_at = _utc_now()

        _write_exact(self.archive / "objects" / content_hash[:2] / content_hash, response.body)
        if text_bytes is not None and text_hash is not None:
            _write_exact(self.archive / "text" / text_hash[:2] / text_hash, text_bytes)
        receipt = {
            "schema_version": WEB_SOURCE_SCHEMA,
            "requested_url": requested,
            "final_url": current,
            "redirect_chain": chain,
            "status": response.status,
            "content_type": content_type,
            "content_sha256": content_hash,
            "content_bytes": len(response.body),
            "text_sha256": text_hash,
            "text_characters": len(text or ""),
            "text_projection": text_projection,
            "trust_class": "untrusted_external_source",
            "prompt_injection_signals": list(signals),
            "fetched_at": fetched_at,
            "archived_at": archived_at,
            "transport": self.transport.name,
            "network_attempt_sha256s": network_attempts,
        }
        receipt_bytes = _canonical_bytes(receipt)
        receipt_hash = _sha256(receipt_bytes)
        receipt_path = self.archive / "receipts" / receipt_hash[:2] / f"{receipt_hash}.json"
        _write_exact(receipt_path, receipt_bytes)
        typed_receipt = dict(receipt)
        typed_receipt["redirect_chain"] = tuple(chain)
        typed_receipt["prompt_injection_signals"] = signals
        typed_receipt["network_attempt_sha256s"] = tuple(network_attempts)
        return ArchivedWebSource(
            **typed_receipt,
            receipt_path=receipt_path,
            receipt_sha256=receipt_hash,
        )


class LocalDocumentAcquirer:
    """Copy one operator-selected document into the canonical private source archive."""

    def __init__(
        self,
        *,
        repository_root: Path,
        archive_root: Path = DEFAULT_ARCHIVE,
        maximum_bytes: int = MAX_SOURCE_BYTES,
        visual_table_model: Path | None = None,
        visual_table_model_sha256: str | None = None,
    ) -> None:
        self.archive = _private_archive(archive_root, repository_root)
        self.maximum_bytes = max(1, min(int(maximum_bytes), MAX_SOURCE_BYTES))
        self.visual_table_config = _visual_table_config(
            visual_table_model,
            visual_table_model_sha256,
        )

    def acquire(
        self,
        path: Path,
        *,
        archived_at: str | None = None,
    ) -> ArchivedLocalDocument:
        source_input = path.expanduser()
        if source_input.is_symlink():
            raise WebAcquisitionError("local document cannot be a symlink")
        try:
            source = source_input.resolve(strict=True)
        except OSError as exc:
            raise WebAcquisitionError("local document does not exist") from exc
        if not source.is_file():
            raise WebAcquisitionError("local document must be a regular file")
        content_type = _LOCAL_SUFFIX_CONTENT_TYPES.get(source.suffix.casefold())
        if content_type is None:
            raise WebAcquisitionError(
                f"unsupported local document extension {source.suffix.casefold()!r}"
            )
        size = source.stat().st_size
        if size < 1:
            raise WebAcquisitionError("local document is empty")
        if size > self.maximum_bytes:
            raise WebAcquisitionError("local document exceeds the configured byte limit")
        body = source.read_bytes()
        if len(body) != size:
            raise WebAcquisitionError("local document changed while it was being read")
        if content_type == "application/pdf" and not body.startswith(b"%PDF-"):
            raise WebAcquisitionError("local PDF does not have a PDF file signature")
        content_hash = _sha256(body)
        text, text_projection = _project_text(
            body,
            content_type,
            visual_table_config=self.visual_table_config,
        )
        if not text or not text.strip() or text_projection is None:
            raise WebAcquisitionError("local document has no retrievable text projection")
        text_bytes = text.encode("utf-8")
        text_hash = _sha256(text_bytes)
        source_uri = (
            f"local-document://{content_hash}/{quote(source.name, safe='')}"
        )
        signals = _injection_signals(text)
        recorded_at = _timestamp(archived_at) if archived_at else _utc_now()
        _write_exact(self.archive / "objects" / content_hash[:2] / content_hash, body)
        _write_exact(self.archive / "text" / text_hash[:2] / text_hash, text_bytes)
        receipt = {
            "schema_version": LOCAL_SOURCE_SCHEMA,
            "source_kind": "local_document",
            "display_name": source.name,
            "requested_url": source_uri,
            "final_url": source_uri,
            "content_type": content_type,
            "content_sha256": content_hash,
            "content_bytes": len(body),
            "text_sha256": text_hash,
            "text_characters": len(text),
            "text_projection": text_projection,
            "trust_class": "operator_selected_local_document_untrusted_content",
            "prompt_injection_signals": list(signals),
            "archived_at": recorded_at,
        }
        receipt_bytes = _canonical_bytes(receipt)
        receipt_hash = _sha256(receipt_bytes)
        receipt_path = self.archive / "receipts" / receipt_hash[:2] / f"{receipt_hash}.json"
        _write_exact(receipt_path, receipt_bytes)
        return ArchivedLocalDocument(
            **{**receipt, "prompt_injection_signals": signals},
            receipt_path=receipt_path,
            receipt_sha256=receipt_hash,
        )


def archived_source_json(
    source: ArchivedWebSource | ArchivedLocalDocument,
) -> dict[str, object]:
    """Return a stable JSON projection without leaking local Path objects."""
    value = asdict(source)
    value["receipt_path"] = str(source.receipt_path)
    return value


def _verified_archived_receipt(
    receipt_path: Path, archive_root: Path
) -> tuple[Path, str, dict[str, Any]]:
    archive_input = archive_root.expanduser()
    receipt_input = receipt_path.expanduser()
    if archive_input.is_symlink() or receipt_input.is_symlink():
        raise WebAcquisitionError("archive and receipt paths cannot be symlinks")
    archive = archive_input.resolve(strict=True)
    receipt_file = receipt_input.resolve(strict=True)
    if not archive.is_dir() or archive.stat().st_mode & 0o077:
        raise WebAcquisitionError("archive must be an owner-only directory")
    receipts_root = archive / "receipts"
    if not receipt_file.is_file() or receipts_root not in receipt_file.parents:
        raise WebAcquisitionError("receipt must be a regular file inside the archive")
    raw = receipt_file.read_bytes()
    receipt_sha = _sha256(raw)
    if receipt_file.stem != receipt_sha:
        raise WebAcquisitionError("receipt filename does not match its content hash")
    try:
        receipt = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebAcquisitionError("receipt is not valid JSON") from exc
    if not isinstance(receipt, dict) or receipt.get("schema_version") not in {
        WEB_SOURCE_SCHEMA,
        LOCAL_SOURCE_SCHEMA,
    }:
        raise WebAcquisitionError("receipt has the wrong schema")
    if _canonical_bytes(receipt) != raw:
        raise WebAcquisitionError("receipt is not in canonical immutable form")
    return archive, receipt_sha, receipt


def load_archived_bytes(
    receipt_path: Path, archive_root: Path
) -> tuple[str, dict[str, Any], bytes]:
    """Verify and read one immutable raw object from the private archive."""
    archive, receipt_sha, receipt = _verified_archived_receipt(receipt_path, archive_root)
    content_sha = receipt.get("content_sha256")
    if not isinstance(content_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", content_sha):
        raise WebAcquisitionError("source has no valid archived content object")
    content_file = archive / "objects" / content_sha[:2] / content_sha
    if not content_file.is_file() or content_file.is_symlink():
        raise WebAcquisitionError("archived content object is missing or unsafe")
    content = content_file.read_bytes()
    if _sha256(content) != content_sha:
        raise WebAcquisitionError("archived content object hash differs")
    return receipt_sha, receipt, content


def load_archived_text(receipt_path: Path, archive_root: Path) -> tuple[str, dict[str, Any], str]:
    """Verify and read one immutable text projection from the private archive."""
    archive, receipt_sha, receipt = _verified_archived_receipt(receipt_path, archive_root)
    text_sha = receipt.get("text_sha256")
    if not isinstance(text_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", text_sha):
        raise WebAcquisitionError("source has no valid archived text projection")
    text_file = archive / "text" / text_sha[:2] / text_sha
    if not text_file.is_file() or text_file.is_symlink():
        raise WebAcquisitionError("archived text projection is missing or unsafe")
    text_bytes = text_file.read_bytes()
    if _sha256(text_bytes) != text_sha:
        raise WebAcquisitionError("archived text projection hash differs")
    try:
        text = text_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WebAcquisitionError("archived text projection is not UTF-8") from exc
    return receipt_sha, receipt, text
