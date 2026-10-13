"""速用工具箱 FastAPI 后端

提供以下能力（需要用户自行安装 LibreOffice / Ghostscript / Tesseract 等外部依赖，各接口在缺依赖时会返回友好的 503）：

- GET  /api/health            健康检查
- GET  /api/config            后端能力披露（ocr/word/strong_compress）
- POST /api/ocr               图片 OCR 提取文本
- POST /api/pdf/compress      PDF 强力压缩
- POST /api/convert/word-to-pdf   Word → PDF
- POST /api/convert/pdf-to-word   PDF → Word

所有路由统一前缀 /api，部署时配合前端 web 工程的同源或代理使用。
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# 本地依赖目录（pip install --target 安装）：追加到 sys.path 末尾，
# 仅补充全局环境缺失的包（如 opencv/numpy），不影响全局已安装的包
_PYDEPS_DIR = Path(__file__).resolve().parent / ".pydeps"
if _PYDEPS_DIR.is_dir() and str(_PYDEPS_DIR) not in sys.path:
    sys.path.append(str(_PYDEPS_DIR))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware

# AI 生成 PPT 子路由（langgraph 大纲编排 + 进程内并发生成队列）
try:
    from ai_ppt import router as _ai_ppt_router
    _HAS_AI_PPT = True
except Exception as _ai_ppt_err:  # pragma: no cover
    _HAS_AI_PPT = False
    logging.getLogger("suyong-server").warning("ai_ppt 模块加载失败（不影响其他功能）：%s", _ai_ppt_err)

# 面试题库子路由（SQLite 存储，Python 标准库，始终可用）
try:
    from interview import router as _interview_router
    _HAS_INTERVIEW = True
except Exception as _interview_err:  # pragma: no cover
    _HAS_INTERVIEW = False
    logging.getLogger("suyong-server").warning("interview 模块加载失败（不影响其他功能）：%s", _interview_err)

# pdf2docx 用于 PDF→Word（比 LibreOffice headless 更可靠，LibreOffice 会将 PDF 当矢量图导入）
try:
    from pdf2docx import Converter as _Pdf2DocxConverter  # type: ignore
    _HAS_PDF2DOCX = True
except Exception:  # pragma: no cover
    _HAS_PDF2DOCX = False

# PyMuPDF 用于 PDF 水印检测与移除
try:
    import pymupdf as fitz  # type: ignore
    _HAS_PYMUPDF = True
except Exception:  # pragma: no cover
    try:
        import fitz  # type: ignore
        _HAS_PYMUPDF = True
    except Exception:  # pragma: no cover
        _HAS_PYMUPDF = False

# OpenCV 用于图片修复（Inpainting）
try:
    import cv2 as _cv2  # type: ignore
    import numpy as _np  # type: ignore
    _HAS_OPENCV = True
except Exception:  # pragma: no cover
    _HAS_OPENCV = False

# python-docx 用于提取 Word 文档文本
try:
    from docx import Document as _DocxDocument  # type: ignore
    _HAS_DOCX = True
except Exception:  # pragma: no cover
    _HAS_DOCX = False

# ffmpeg 检测（用于视频处理）
_FFMPEG: Optional[str] = None

def _has_ffmpeg() -> bool:
    global _FFMPEG
    if _FFMPEG is not None:
        return _FFMPEG != ""
    _FFMPEG = _find_cmd("ffmpeg") or ""
    return _FFMPEG != ""

# markdown + xhtml2pdf 用于 Markdown → PDF 转换
try:
    import markdown as _markdown  # type: ignore
    _HAS_MARKDOWN = True
except Exception:  # pragma: no cover
    _HAS_MARKDOWN = False

try:
    from xhtml2pdf import pisa as _pisa  # type: ignore
    _HAS_XHTML2PDF = True
except Exception:  # pragma: no cover
    _HAS_XHTML2PDF = False

__version__ = "0.2.0"

logger = logging.getLogger("suyong-server")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="速用工具箱后端", version=__version__)

if _HAS_AI_PPT:
    app.include_router(_ai_ppt_router)
if _HAS_INTERVIEW:
    app.include_router(_interview_router)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_LOCK = threading.Lock()


# ---------------- 工具依赖检测 ----------------


def _find_cmd(name: str) -> Optional[str]:
    """在 PATH 中查找命令，找不到时回退到 Windows 常见安装路径。"""
    p = shutil.which(name)
    if p:
        return p
    # Windows 常见安装路径回退
    if sys.platform == "win32":
        candidates: list[str] = []
        repo_root = Path(__file__).resolve().parent.parent
        if name in ("tesseract", "tesseract.exe"):
            candidates = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
        elif name in ("gs", "gswin64c", "gswin32c"):
            candidates = [
                r"C:\Program Files\gs\gs\bin\gswin64c.exe",
                r"C:\Program Files\gs\gs\bin\gswin32c.exe",
            ]
            # 通配匹配 C:\Program Files\gs\gs*\bin\gswin64c.exe
            gs_root = Path(r"C:\Program Files\gs")
            if gs_root.exists():
                for child in gs_root.iterdir():
                    exe = child / "bin" / "gswin64c.exe"
                    if exe.exists():
                        candidates.insert(0, str(exe))
                    exe32 = child / "bin" / "gswin32c.exe"
                    if exe32.exists():
                        candidates.append(str(exe32))
            # 本仓库内自定义安装目录：
            #   D:\ai\mytools\gs*\bin\gswin64c.exe           （直接结构，如 gs_extract2）
            #   D:\ai\mytools\gs*\gs*\bin\gswin64c.exe       （子目录结构，如 gs\gs10.02.0）
            if repo_root.exists():
                for d in repo_root.iterdir():
                    if not d.is_dir() or not d.name.lower().startswith("gs"):
                        continue
                    exe = d / "bin" / "gswin64c.exe"
                    if exe.exists():
                        candidates.insert(0, str(exe))
                    exe32 = d / "bin" / "gswin32c.exe"
                    if exe32.exists():
                        candidates.append(str(exe32))
                    for child in d.iterdir():
                        if not child.is_dir():
                            continue
                        exe = child / "bin" / "gswin64c.exe"
                        if exe.exists():
                            candidates.insert(0, str(exe))
                        exe32 = child / "bin" / "gswin32c.exe"
                        if exe32.exists():
                            candidates.append(str(exe32))
        elif name in ("soffice", "soffice.exe"):
            candidates = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            # 本仓库内自定义安装目录：D:\ai\mytools\libreoffice*\program\soffice.exe
            # 或子目录结构 D:\ai\mytools\libreoffice*\LibreOffice\program\soffice.exe
            if repo_root.exists():
                for d in repo_root.iterdir():
                    if not d.is_dir():
                        continue
                    low = d.name.lower()
                    if not (low.startswith("libreoffice") or low.startswith("lo")):
                        continue
                    for cand in (d, *(c for c in d.iterdir() if c.is_dir())):
                        prog = cand / "program"
                        if not prog.is_dir():
                            continue
                        # Windows: 优先 soffice.exe（主程序包装器，配合 CREATE_NO_WINDOW 隐藏窗口），
                        # 回退 soffice.com（控制台版本），最后 soffice.bin（裸二进制）
                        for bin_name in ("soffice.exe", "soffice.com", "soffice.bin"):
                            exe = prog / bin_name
                            if exe.exists():
                                candidates.append(str(exe))
        elif name in ("ffmpeg", "ffmpeg.exe"):
            # 支持通过环境变量 FFMPEG_PATH 指定 ffmpeg.exe 完整路径
            env_path = os.environ.get("FFMPEG_PATH")
            if env_path and Path(env_path).exists():
                return env_path
            candidates = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                # 本机已下载的静态构建（AILowCode 工作区）
                r"D:\ai\AILowCode\ffmpeg.exe",
            ]
            # 本仓库内自定义安装目录：
            #   D:\ai\mytools\ffmpeg*\bin\ffmpeg.exe          （直接结构）
            #   D:\ai\mytools\ffmpeg*\ffmpeg-*\bin\ffmpeg.exe （解压子目录结构）
            if repo_root.exists():
                for d in repo_root.iterdir():
                    if not d.is_dir() or not d.name.lower().startswith("ffmpeg"):
                        continue
                    exe = d / "bin" / "ffmpeg.exe"
                    if exe.exists():
                        candidates.insert(0, str(exe))
                    for child in d.iterdir():
                        if not child.is_dir():
                            continue
                        exe = child / "bin" / "ffmpeg.exe"
                        if exe.exists():
                            candidates.insert(0, str(exe))
        for c in candidates:
            if Path(c).exists():
                return c
    return None


_LO = _find_cmd("soffice")
_GS = _find_cmd("gs") or _find_cmd("gswin64c")
_TESS = _find_cmd("tesseract")


def _has_soffice() -> bool:
    return bool(_LO)


def _has_gs() -> bool:
    return bool(_GS)


def _has_tess() -> bool:
    return bool(_TESS)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _suffix_from_filename(filename: str) -> str:
    s = Path(filename).suffix.lower()
    return s if s.startswith(".") else f".{s}"


def _rfc_filename(filename: str) -> str:
    safe = Path(filename).name
    # 构造 RFC 5987 编码的 filename*，浏览器自动解析
    return urllib.parse.quote(safe)


def _attachment_header(filename: str) -> dict[str, str]:
    return {
        "Content-Disposition": f"attachment; filename*=UTF-8''{_rfc_filename(filename)}"
    }


def _run(args: list[str], *, cwd: Optional[Path] = None, input_bytes: Optional[bytes] = None, timeout: int = 240, env: Optional[dict] = None) -> bytes:
    # Windows: 隐藏 GUI 窗口
    creationflags = 0
    startupinfo = None
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        proc = subprocess.run(
            args,
            input=input_bytes,
            capture_output=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            check=False,
            creationflags=creationflags,
            startupinfo=startupinfo,
            env=env,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"缺少依赖：{exc.filename}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="处理超时") from exc
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        stdout = proc.stdout.decode("utf-8", errors="replace").strip()
        msg = stderr or stdout
        logger.error("命令执行失败 (exit=%d): %s\nstderr: %s\nstdout: %s", proc.returncode, " ".join(str(a) for a in args), stderr[:500], stdout[:500])
        raise HTTPException(status_code=500, detail=msg[:400] or f"命令执行失败（退出码 {proc.returncode}）")
    return proc.stdout


# ---------------- 基础接口 ----------------


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "python": sys.version.split()[0],
        "capabilities": {
            "ocr": _has_tess(),
            "word": _has_soffice(),
            "strong_compress": _has_gs(),
            "watermark": _HAS_PYMUPDF,
            "markdown_pdf": _HAS_MARKDOWN and _HAS_XHTML2PDF,
            "inpaint": _HAS_OPENCV,
            "doc_extract": _HAS_DOCX or _HAS_PYMUPDF,
            "video_process": _has_ffmpeg(),
        },
    }


@app.get("/api/config")
def server_config() -> dict:
    return {
        "version": __version__,
        "maxUpload": int(os.getenv("MAX_UPLOAD_MB", "200")) * 1024 * 1024,
        "capabilities": {
            "ocr": _has_tess(),
            "word": _has_soffice(),
            "strong_compress": _has_gs(),
            "watermark": _HAS_PYMUPDF,
            "markdown_pdf": _HAS_MARKDOWN and _HAS_XHTML2PDF,
            "inpaint": _HAS_OPENCV,
            "doc_extract": _HAS_DOCX or _HAS_PYMUPDF,
            "video_process": _has_ffmpeg(),
            "ai_ppt": _HAS_AI_PPT and bool(os.getenv("LLM_API_KEY")),
            "interview": _HAS_INTERVIEW,
        },
        "docs": (
            "依赖安装：\n"
            "  Word↔PDF   → soffice  (LibreOffice)\n"
            "  PDF 强力压缩 → gs      (Ghostscript)\n"
            "  OCR         → tesseract (可选 chi_sim / eng 语言包)\n"
        ),
    }


# ---------------- URL 可访问性检查 ----------------

@app.get("/api/check-url")
def check_url(url: str):
    """检查 URL 格式是否正确以及是否可访问"""
    # 1. 基本格式校验
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return {"ok": False, "reason": "URL 格式不正确，请输入完整的网址（如 https://example.com）"}
    if parsed.scheme not in ("http", "https"):
        return {"ok": False, "reason": f"仅支持 http/https 协议，当前为 {parsed.scheme}"}

    # 2. 可访问性检查（HEAD 请求，超时 5s）
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        status_code = resp.getcode()
        return {"ok": True, "statusCode": status_code, "reason": f"访问成功（HTTP {status_code}）"}
    except urllib.error.HTTPError as e:
        # HTTP 错误码（如 404）说明服务器有响应，URL 本身可达
        return {"ok": True, "statusCode": e.code, "reason": f"服务器已响应（HTTP {e.code}）"}
    except urllib.error.URLError as e:
        return {"ok": False, "reason": f"无法访问该地址：{e.reason}"}
    except Exception as e:
        return {"ok": False, "reason": f"访问失败：{e}"}


def _read_bytes_limit(file: UploadFile) -> bytes:
    limit_mb = int(os.getenv("MAX_UPLOAD_MB", "200"))
    limit = limit_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"单文件超过 {limit_mb}MB 限制")
    return data


# ---------------- OCR ----------------


@app.post("/api/ocr")
def ocr_extract(
    file: UploadFile = File(...),
    lang: str = Form(default="chi_sim+eng"),
):
    if not _has_tess():
        raise HTTPException(
            status_code=503,
            detail="未安装 tesseract；请先安装 tesseract-ocr，并按需安装中文语言包 tesseract-ocr-chi-sim。",
        )
    data = _read_bytes_limit(file)
    ext = _suffix_from_filename(file.filename or "image.png")
    with tempfile.TemporaryDirectory(prefix="suyocr_") as td:
        td_path = Path(td)
        input_path = td_path / f"source{ext}"
        out_base = td_path / "out"
        input_path.write_bytes(data)
        args = [_TESS or "tesseract", str(input_path), str(out_base), "-l", lang, "txt"]
        _run(args)
        output_txt = Path(str(out_base) + ".txt")
        if not output_txt.exists():
            raise HTTPException(status_code=500, detail="OCR 未生成输出文件")
        text = output_txt.read_text(encoding="utf-8", errors="replace")
    out_name = Path(file.filename or "result").stem + ".txt"
    headers = _attachment_header(out_name)
    return Response(content=text.encode("utf-8"), media_type="text/plain; charset=utf-8", headers=headers)


# ---------------- PDF 强力压缩 ----------------


@app.post("/api/pdf/compress")
def pdf_compress(
    file: UploadFile = File(...),
    quality: int = Form(default=3),  # 1 最激进 ~ 5 最轻
):
    if not _has_gs():
        raise HTTPException(
            status_code=503,
            detail="未安装 Ghostscript（gs）；请先安装 Ghostscript 以启用强力压缩。",
        )
    data = _read_bytes_limit(file)
    # 1..5 → /screen /ebook /printer /prepress /default
    presets = ["/screen", "/ebook", "/printer", "/prepress", "/default"]
    preset = presets[max(0, min(4, quality - 1))]
    with tempfile.TemporaryDirectory(prefix="suycmp_") as td:
        td_path = Path(td)
        inp = td_path / "input.pdf"
        out = td_path / "output.pdf"
        inp.write_bytes(data)
        args = [
            _GS,
            "-sDEVICE=pdfwrite",
            f"-dPDFSETTINGS={preset}",
            "-dCompatibilityLevel=1.5",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            f"-sOutputFile={out}",
            str(inp),
        ]
        with _LOCK:
            # Ghostscript 多个实例并发偶尔会撞临时字体缓存，用进程锁串行一下
            _run(args)
        if not out.exists():
            raise HTTPException(status_code=500, detail="压缩失败：未生成输出")
        out_bytes = out.read_bytes()
    name = Path(file.filename or "result").stem + ".min.pdf"
    # 若压缩后反而变大：返回输入（前端据此给提示）
    final = out_bytes if len(out_bytes) < len(data) else data
    headers = _attachment_header(name)
    return Response(content=final, media_type="application/pdf", headers=headers)


# ---------------- Word ↔ PDF ----------------


def _run_soffice_convert(
    src_bytes: bytes, src_name: str, target_ext: str, in_filter: str = ""
) -> tuple[bytes, str]:
    """LibreOffice headless 单文件转换。返回 (字节, 输出文件名)。

    target_ext: ".pdf" / ".docx"
    in_filter: 可选导入过滤器名，例如 PDF→Word 需传 "writer_pdf_import"
    """
    if not _has_soffice():
        raise HTTPException(
            status_code=503,
            detail="未安装 LibreOffice（soffice），请先安装 LibreOffice 以启用 Word/PDF 互转。",
        )
    src_ext = _suffix_from_filename(src_name)
    with tempfile.TemporaryDirectory(prefix="suyconv_") as td:
        td_path = Path(td)
        in_dir = td_path / "in"
        out_dir = td_path / "out"
        user_profile = td_path / "loprofile"
        in_dir.mkdir()
        out_dir.mkdir()
        user_profile.mkdir()
        input_path = in_dir / f"input{src_ext}"
        input_path.write_bytes(src_bytes)
        # LibreOffice 26.x 不支持 --xxx=yyy 等号格式，须用空格分隔
        # 解压安装的 LibreOffice 需指定用户配置目录（-env:UserInstallation）
        # 每次使用全新临时目录，避免损坏的 profile 导致 C++ 异常崩溃
        args = [
            _LO,
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--nologo",
            "--nodefault",
            f"-env:UserInstallation=file:///{str(user_profile).replace(chr(92), '/')}",
        ]
        if in_filter:
            args += ["--infilter", in_filter]
        args += [
            "--convert-to", target_ext.lstrip("."),
            "--outdir", str(out_dir),
            str(input_path),
        ]
        # LibreOffice 多进程并发稳定性较差，用全局锁串行
        # 将 program 目录加入 PATH，确保 DLL 可被找到（解压版 LibreOffice 需要）
        lo_program = Path(_LO).parent
        env = os.environ.copy()
        lo_path = str(lo_program)
        if lo_path not in env.get("PATH", ""):
            env["PATH"] = lo_path + os.pathsep + env.get("PATH", "")
        with _LOCK:
            _run(args, timeout=300, env=env)
        produced = list(out_dir.glob(f"*{target_ext}"))
        if not produced:
            raise HTTPException(status_code=500, detail="LibreOffice 未生成输出文件")
        out_path = produced[0]
        out_bytes = out_path.read_bytes()
    out_name = Path(src_name).stem + target_ext
    return out_bytes, out_name


def _run_pdf2docx_convert(src_bytes: bytes, src_name: str) -> tuple[bytes, str]:
    """使用 pdf2docx 库将 PDF 转换为 Word（DOCX）。

    LibreOffice headless 会将 PDF 当矢量图导入，无法提取可编辑文本，
    因此 PDF→Word 改用 pdf2docx（基于 PyMuPDF + python-docx）。
    """
    if not _HAS_PDF2DOCX:
        raise HTTPException(
            status_code=503,
            detail="未安装 pdf2docx 库，请先运行 pip install pdf2docx 以启用 PDF→Word 转换。",
        )
    with tempfile.TemporaryDirectory(prefix="suyconv_") as td:
        td_path = Path(td)
        input_path = td_path / "input.pdf"
        output_path = td_path / "output.docx"
        input_path.write_bytes(src_bytes)
        try:
            # pdf2docx 多线程并发不稳定，用全局锁串行（与 LibreOffice 共享 _LOCK）
            with _LOCK:
                cv = _Pdf2DocxConverter(str(input_path))
                cv.convert(str(output_path), start=0, end=None)
                cv.close()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF→Word 转换失败：{exc}") from exc
        if not output_path.exists():
            raise HTTPException(status_code=500, detail="pdf2docx 未生成输出文件")
        out_bytes = output_path.read_bytes()
    out_name = Path(src_name).stem + ".docx"
    return out_bytes, out_name


@app.post("/api/convert/word-to-pdf")
def convert_word_to_pdf(file: UploadFile = File(...)):
    data = _read_bytes_limit(file)
    ext = _suffix_from_filename(file.filename or "input.docx")
    if ext not in (".doc", ".docx"):
        raise HTTPException(status_code=400, detail="仅接受 .doc / .docx 文件")
    out_bytes, out_name = _run_soffice_convert(data, file.filename or "input.docx", ".pdf")
    headers = _attachment_header(out_name)
    return Response(content=out_bytes, media_type="application/pdf", headers=headers)


@app.get("/api/soffice-test")
def soffice_test():
    """测试 soffice 是否能正常运行"""
    if not _LO:
        return {"ok": False, "reason": "soffice 未找到"}
    try:
        proc = subprocess.run(
            [_LO, "--version"],
            capture_output=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        version = proc.stdout.decode("utf-8", errors="replace").strip()
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        return {
            "ok": proc.returncode == 0,
            "exitCode": proc.returncode,
            "path": _LO,
            "version": version,
            "stderr": stderr,
        }
    except Exception as e:
        return {"ok": False, "reason": str(e)}


@app.post("/api/convert/pdf-to-word")
def convert_pdf_to_word(file: UploadFile = File(...)):
    data = _read_bytes_limit(file)
    ext = _suffix_from_filename(file.filename or "input.pdf")
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="仅接受 PDF 文件")
    out_bytes, out_name = _run_pdf2docx_convert(data, file.filename or "input.pdf")
    headers = _attachment_header(out_name)
    return Response(
        content=out_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


# ---------------- PDF 水印检测与移除 ----------------


def _detect_text_watermarks(doc) -> list[dict]:
    """检测文本水印：跨页重复出现的相同文本、半透明文字、注释层水印。"""
    watermarks: list[dict] = []
    # 统计每段文本在多少页出现
    text_pages: dict[str, list[int]] = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        # 检查注释/水印注释
        for annot in page.annots() or []:
            if annot.type[0] in (8, 19, 20):  # Watermark, FreeText, Text
                info = annot.info
                content = info.get("content", "")
                if content:
                    watermarks.append({
                        "id": f"annot_{page_num}_{annot.xref}",
                        "type": "annotation",
                        "text": content,
                        "page": page_num + 1,
                        "rect": list(annot.rect),
                    })
        # 提取页面文本块
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:  # 仅文本块
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text or len(text) < 2:
                        continue
                    # 记录文本出现的页码
                    key = text[:80]  # 截断长文本
                    if key not in text_pages:
                        text_pages[key] = []
                    if page_num not in text_pages[key]:
                        text_pages[key].append(page_num)
                    # 检查是否半透明（opacity < 1）
                    color = span.get("color", 0)
                    # 常见水印特征：灰色文字（颜色值在 0xC0C0C0 附近）
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    is_gray = abs(r - g) < 20 and abs(g - b) < 20 and r > 150
                    if is_gray and len(text_pages[key]) >= 1:
                        wm_id = f"text_{page_num}_{hash(key) & 0xFFFFFF}"
                        watermarks.append({
                            "id": wm_id,
                            "type": "text",
                            "text": text[:100],
                            "page": page_num + 1,
                            "color": f"#{r:02X}{g:02X}{b:02X}",
                            "rect": [span["bbox"][0], span["bbox"][1], span["bbox"][2], span["bbox"][3]],
                        })

    # 跨页重复文本（出现 3 页以上）视为水印
    for text, pages in text_pages.items():
        if len(pages) >= 3:
            wm_id = f"text_repeat_{hash(text) & 0xFFFFFF}"
            watermarks.append({
                "id": wm_id,
                "type": "text_repeat",
                "text": text,
                "pages": [p + 1 for p in pages],
                "count": len(pages),
            })
    return watermarks


def _detect_image_watermarks(doc) -> list[dict]:
    """检测图片水印：出现在每页相同位置的小图片、半透明图片。"""
    watermarks: list[dict] = []
    # 统计每页图片位置
    img_positions: dict[tuple, list[int]] = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        for img_idx, img in enumerate(images):
            xref = img[0]
            # 获取图片在页面上的位置
            rects = page.get_image_rects(xref)
            for rect in rects:
                # 归一化位置（相对于页面大小）
                page_rect = page.rect
                pos_key = (
                    round(rect.width / page_rect.width, 2),
                    round(rect.height / page_rect.height, 2),
                    round(rect.x0 / page_rect.width, 2),
                    round(rect.y0 / page_rect.height, 2),
                )
                if pos_key not in img_positions:
                    img_positions[pos_key] = []
                if page_num not in img_positions[pos_key]:
                    img_positions[pos_key].append(page_num)
                # 小尺寸图片可能是水印（占页面面积 < 15%）
                area_ratio = (rect.width * rect.height) / (page_rect.width * page_rect.height)
                if area_ratio < 0.15:
                    watermarks.append({
                        "id": f"img_{page_num}_{xref}",
                        "type": "image",
                        "page": page_num + 1,
                        "xref": xref,
                        "rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                        "area_ratio": round(area_ratio, 4),
                    })

    # 跨页相同位置图片视为水印
    for pos_key, pages in img_positions.items():
        if len(pages) >= 3:
            watermarks.append({
                "id": f"img_repeat_{hash(pos_key) & 0xFFFFFF}",
                "type": "image_repeat",
                "pages": [p + 1 for p in pages],
                "count": len(pages),
                "position": list(pos_key),
            })
    return watermarks


@app.post("/api/pdf/watermark-detect")
def detect_watermarks(file: UploadFile = File(...)):
    """检测 PDF 中的水印（文本 + 图片）"""
    if not _HAS_PYMUPDF:
        raise HTTPException(status_code=503, detail="未安装 PyMuPDF，请运行 pip install PyMuPDF")
    data = _read_bytes_limit(file)
    ext = _suffix_from_filename(file.filename or "input.pdf")
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="仅接受 PDF 文件")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF 解析失败：{e}")
    text_wms = _detect_text_watermarks(doc)
    img_wms = _detect_image_watermarks(doc)
    doc.close()
    return {
        "total": len(text_wms) + len(img_wms),
        "textWatermarks": text_wms,
        "imageWatermarks": img_wms,
    }


@app.post("/api/pdf/watermark-remove")
def remove_watermarks(
    file: UploadFile = File(...),
    mode: str = Form("all"),
    keywords: str = Form(""),
):
    """移除 PDF 水印。
    mode: all | text | image | keyword
    keywords: 逗号分隔的关键词列表（mode=keyword 时使用）
    """
    if not _HAS_PYMUPDF:
        raise HTTPException(status_code=503, detail="未安装 PyMuPDF，请运行 pip install PyMuPDF")
    data = _read_bytes_limit(file)
    ext = _suffix_from_filename(file.filename or "input.pdf")
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="仅接受 PDF 文件")
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF 解析失败：{e}")

    removed_count = 0
    for page_num in range(len(doc)):
        page = doc[page_num]

        # 1. 移除注释层水印
        if mode in ("all", "text"):
            annots_to_delete = []
            for annot in page.annots() or []:
                if annot.type[0] in (8, 19, 20):
                    annots_to_delete.append(annot)
                    removed_count += 1
            for annot in annots_to_delete:
                page.delete_annot(annot)

        # 2. 文本水印：使用 redaction（遮盖删除）
        if mode in ("all", "text", "keyword"):
            # 收集需要删除的文本区域
            redact_rects = []
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text or len(text) < 2:
                            continue
                        should_remove = False
                        if mode == "all":
                            # 灰色文字视为水印
                            color = span.get("color", 0)
                            r = (color >> 16) & 0xFF
                            g = (color >> 8) & 0xFF
                            b = color & 0xFF
                            is_gray = abs(r - g) < 20 and abs(g - b) < 20 and r > 150
                            if is_gray:
                                should_remove = True
                        elif mode == "text":
                            should_remove = True  # 移除所有文本（慎用）
                        elif mode == "keyword" and keyword_list:
                            for kw in keyword_list:
                                if kw in text:
                                    should_remove = True
                                    break
                        if should_remove:
                            bbox = span["bbox"]
                            redact_rects.append(fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3]))
                            removed_count += 1
            # 应用 redaction
            for rect in redact_rects:
                page.add_redact_annot(rect, fill=(1, 1, 1))  # 白色填充
            if redact_rects:
                page.apply_redactions()

        # 3. 图片水印：删除小尺寸图片对象
        if mode in ("all", "image"):
            page_rect = page.rect
            images = page.get_images(full=True)
            for img in images:
                xref = img[0]
                rects = page.get_image_rects(xref)
                for rect in rects:
                    area_ratio = (rect.width * rect.height) / (page_rect.width * page_rect.height)
                    if area_ratio < 0.15:  # 占页面面积 < 15% 的图片视为水印
                        page.delete_image(xref)
                        removed_count += 1
                        break

    # 保存修改后的 PDF
    out_bytes = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    out_name = Path(file.filename or "input.pdf").stem + "_no_watermark.pdf"
    headers = _attachment_header(out_name)
    return Response(content=out_bytes, media_type="application/pdf", headers=headers)


# ---------------- Markdown → PDF ----------------


@app.post("/api/md-to-pdf")
def markdown_to_pdf(
    content: str = Form(...),
    filename: str = Form("document.pdf"),
):
    """将 Markdown 文本转换为 PDF 文件"""
    if not (_HAS_MARKDOWN and _HAS_XHTML2PDF):
        missing = []
        if not _HAS_MARKDOWN:
            missing.append("markdown")
        if not _HAS_XHTML2PDF:
            missing.append("xhtml2pdf")
        raise HTTPException(
            status_code=503,
            detail=f"未安装依赖：{', '.join(missing)}，请运行 pip install {' '.join(missing)}",
        )
    if not content.strip():
        raise HTTPException(status_code=400, detail="Markdown 内容为空")
    try:
        # Markdown → HTML
        html_body = _markdown.markdown(
            content,
            extensions=["extra", "tables", "fenced_code", "codehilite", "toc"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Markdown 解析失败：{e}")

    # 包装为完整 HTML 文档，添加中文字体支持
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
@page {{
  size: A4;
  margin: 2cm;
}}
body {{
  font-family: "Microsoft YaHei", "SimSun", sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}}
h1 {{ font-size: 24px; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
h2 {{ font-size: 20px; border-bottom: 1px solid #eee; padding-bottom: 6px; }}
h3 {{ font-size: 16px; }}
code {{ background: #f5f5f5; padding: 2px 6px; font-family: "Consolas", monospace; font-size: 13px; }}
pre {{ background: #f5f5f5; padding: 12px; overflow-x: auto; }}
pre code {{ background: none; padding: 0; }}
blockquote {{ border-left: 4px solid #ddd; margin: 0; padding: 8px 16px; color: #666; background: #fafafa; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f5f5f5; font-weight: bold; }}
a {{ color: #409eff; text-decoration: none; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    try:
        # HTML → PDF (xhtml2pdf)
        pdf_buffer = io.BytesIO()
        result = _pisa.CreatePDF(io.StringIO(full_html), dest=pdf_buffer)
        if result.err > 0:
            raise HTTPException(status_code=500, detail=f"PDF 生成失败，错误数：{result.err}")
        pdf_bytes = pdf_buffer.getvalue()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败：{e}")

    out_name = filename if filename.endswith(".pdf") else filename + ".pdf"
    headers = _attachment_header(out_name)
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


# ---------------- 图片修复（Inpainting） ----------------


@app.post("/api/image/inpaint")
def image_inpaint(
    file: UploadFile = File(...),
    mask: UploadFile = File(...),
    radius: int = Form(8),
):
    """图片修复：根据 mask 在原图上去除文字/瑕疵区域。
    radius: Telea 算法的修复半径（像素）
    """
    if not _HAS_OPENCV:
        raise HTTPException(status_code=503, detail="未安装 opencv-python + numpy，请先 pip install opencv-python numpy")
    img_bytes = _read_bytes_limit(file)
    mask_bytes = _read_bytes_limit(mask)
    try:
        img_arr = _np.frombuffer(img_bytes, dtype=_np.uint8)
        img = _cv2.imdecode(img_arr, _cv2.IMREAD_COLOR)
        mask_arr = _np.frombuffer(mask_bytes, dtype=_np.uint8)
        mask_color = _cv2.imdecode(mask_arr, _cv2.IMREAD_COLOR)
        # 转灰度 + 阈值 -> 二值 mask
        mask_gray = _cv2.cvtColor(mask_color, _cv2.COLOR_BGR2GRAY)
        _, mask_bin = _cv2.threshold(mask_gray, 10, 255, _cv2.THRESH_BINARY)
        # mask 尺寸与原图对齐（按原图大小 resize）
        if mask_bin.shape[:2] != img.shape[:2]:
            mask_bin = _cv2.resize(mask_bin, (img.shape[1], img.shape[0]))
        # Inpaint 使用 Telea 算法（快速稳定）
        radius_val = max(1, min(100, int(radius)))
        result = _cv2.inpaint(img, mask_bin, radius_val, _cv2.INPAINT_TELEA)
        ok, buf = _cv2.imencode(".png", result)
        if not ok:
            raise HTTPException(status_code=500, detail="图片编码失败")
        out_bytes = buf.tobytes()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修复失败：{e}")
    headers = _attachment_header(f"inpaint_{Path(file.filename or 'image.png').stem}.png")
    return Response(content=out_bytes, media_type="image/png", headers=headers)


# ---------------- 文档文本提取 ----------------


@app.post("/api/doc/extract-text")
def extract_document_text(file: UploadFile = File(...)):
    """从 .txt / .docx / .doc / .pdf 文件中提取纯文本"""
    data = _read_bytes_limit(file)
    ext = _suffix_from_filename(file.filename or "file.txt").lower()
    text = ""
    if ext == ".txt":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("gbk")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"文本编码无法识别：{e}")
    elif ext in (".docx", ".doc"):
        if ext == ".docx":
            if not _HAS_DOCX:
                raise HTTPException(status_code=503, detail="未安装 python-docx，请先 pip install python-docx")
            try:
                import io as _bio
                doc = _DocxDocument(_bio.BytesIO(data))
                text = "\n".join(p.text for p in doc.paragraphs)
            except HTTPException:
                raise
            except Exception as e:
                # 回退：尝试 pymupdf
                if _HAS_PYMUPDF:
                    try:
                        import io as _bio2
                        pdf_doc = fitz.open(stream=data)
                        text = "\n".join(p.get_text() for p in pdf_doc)
                        pdf_doc.close()
                    except Exception as e2:
                        raise HTTPException(status_code=500, detail=f"DOCX 解析失败：{e}；回退 PyMuPDF 也失败：{e2}")
                else:
                    raise HTTPException(status_code=500, detail=f"DOCX 解析失败：{e}")
        else:  # .doc (legacy format) - only via pymupdf
            if not _HAS_PYMUPDF:
                raise HTTPException(status_code=503, detail=".doc 格式需要 PyMuPDF 支持，请安装 pip install pymupdf")
            try:
                import io as _bio3
                pdf_doc = fitz.open(stream=data)
                text = "\n".join(p.get_text() for p in pdf_doc)
                pdf_doc.close()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f".doc 解析失败：{e}")
    elif ext == ".pdf":
        if not _HAS_PYMUPDF:
            raise HTTPException(status_code=503, detail=".pdf 需要 PyMuPDF，请 pip install pymupdf")
        try:
            pdf_doc = fitz.open(stream=data, filetype="pdf")
            text = "\n".join(p.get_text() for p in pdf_doc)
            pdf_doc.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF 解析失败：{e}")
    else:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{ext}")
    return {"filename": file.filename, "length": len(text), "text": text}


# ---------------- 视频压缩 ----------------


@app.post("/api/video/compress")
def compress_video(
    file: UploadFile = File(...),
    quality: int = Form(3),
    format: str = Form("keep"),
):
    """压缩视频文件。
    quality: 1..5 (1=极低码率, 5=无损画质), 默认 3 -> CRF 值映射 28,26,23,20,18
    format: keep / mp4 / webm
    """
    if not _has_ffmpeg():
        raise HTTPException(status_code=503, detail="未检测到 ffmpeg，请先安装并加入 PATH")
    data = _read_bytes_limit(file)
    src_name = file.filename or "video.mp4"
    src_ext = _suffix_from_filename(src_name)
    with tempfile.TemporaryDirectory(prefix="suyvid_") as td:
        td_path = Path(td)
        input_path = td_path / f"input{src_ext}"
        input_path.write_bytes(data)
        # 确定输出扩展名
        if format == "keep":
            out_ext = src_ext if src_ext in (".mp4", ".webm", ".mov", ".mkv") else ".mp4"
        elif format == "webm":
            out_ext = ".webm"
        else:
            out_ext = ".mp4"
        output_path = td_path / f"output{out_ext}"
        # 质量 -> CRF: 1=28, 2=26, 3=23, 4=20, 5=18
        crf_map = {1: 28, 2: 26, 3: 23, 4: 20, 5: 18}
        crf = crf_map.get(max(1, min(5, int(quality))), 23)
        if out_ext == ".webm":
            # VP9 codec
            args = [_FFMPEG or "ffmpeg", "-y", "-i", str(input_path),
                    "-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0",
                    "-c:a", "libopus", "-b:a", "96k",
                    "-hide_banner", "-loglevel", "error", str(output_path)]
        else:
            # H.264 codec
            args = [_FFMPEG or "ffmpeg", "-y", "-i", str(input_path),
                    "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-hide_banner", "-loglevel", "error", str(output_path)]
        try:
            _run(args, timeout=600)
        except HTTPException as e:
            # 从 detail 推断 ffmpeg 输出
            raise HTTPException(status_code=500, detail=f"ffmpeg 执行失败：{e.detail}")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="ffmpeg 未生成输出文件（可能不支持此视频编码）")
        out_bytes = output_path.read_bytes()
        out_name = Path(src_name).stem + f".compressed{out_ext}"
        headers = _attachment_header(out_name)
        mime = "video/webm" if out_ext == ".webm" else "video/mp4"
        return Response(content=out_bytes, media_type=mime, headers=headers)


# ---------------- 视频提取音频 ----------------


@app.post("/api/video/extract-audio")
def extract_audio(
    file: UploadFile = File(...),
    format: str = Form("mp3"),
):
    """从视频文件提取音频。
    format: mp3 / aac / wav / webm
    """
    if not _has_ffmpeg():
        raise HTTPException(status_code=503, detail="未检测到 ffmpeg")
    data = _read_bytes_limit(file)
    src_name = file.filename or "video.mp4"
    src_ext = _suffix_from_filename(src_name)
    fmt = format.lower()
    if fmt not in ("mp3", "aac", "wav", "webm"):
        fmt = "mp3"
    codec_map = {
        "mp3": ("libmp3lame", ".mp3", "audio/mpeg"),
        "aac": ("aac", ".m4a", "audio/mp4"),
        "wav": ("pcm_s16le", ".wav", "audio/wav"),
        "webm": ("libopus", ".webm", "audio/webm"),
    }
    codec, out_ext, mime = codec_map[fmt]
    with tempfile.TemporaryDirectory(prefix="suyaud_") as td:
        td_path = Path(td)
        input_path = td_path / f"input{src_ext}"
        input_path.write_bytes(data)
        output_path = td_path / f"output{out_ext}"
        args = [_FFMPEG or "ffmpeg", "-y", "-i", str(input_path),
                "-vn", "-c:a", codec,
                "-hide_banner", "-loglevel", "error", str(output_path)]
        if fmt == "mp3":
            args.insert(-1, "-q:a")
            args.insert(-1, "2")
        try:
            _run(args, timeout=300)
        except HTTPException as e:
            raise HTTPException(status_code=500, detail=f"ffmpeg 执行失败：{e.detail}")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="未生成音频输出文件（视频可能不包含音轨）")
        out_bytes = output_path.read_bytes()
        out_name = Path(src_name).stem + out_ext
        headers = _attachment_header(out_name)
        return Response(content=out_bytes, media_type=mime, headers=headers)


# ---------------- 入口 ----------------

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host=host, port=port, reload=False, workers=1)
