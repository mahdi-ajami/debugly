"""
ابزارهای ویندوزی برای مدیریت فایل‌ها و پوشه‌ها
Windows utility tools for file and folder management

این ماژول توابعی برای:
- بررسی وجود فایل (Verify file paths with os.path.exists / pathlib.Path)
- بررسی مجوزهای دسترسی (Check file permissions on Windows)
- ویرایش، اضافه و حذف فایل‌ها و پوشه‌ها (Edit, add, delete files and folders)
- مدیریت کامنت‌ها و کد در فایل‌ها (Comment and code management)
"""

import json
import os
import shutil
import stat
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

PathLike = Union[str, os.PathLike]


# ─────────────────────────────────────────────
# 1. مسیر فایل / بررسی وجود (Path Verification)
# ─────────────────────────────────────────────

def file_exists(file_path: PathLike) -> bool:
    """بررسی وجود فایل در مسیر مشخص شده
    Verify that a file exists at the given path.

    Args:
        file_path: مسیر فایل (File path to check)

    Returns:
        True اگر فایل وجود داشته باشد (True if file exists)

    مثال (Example):
        >>> file_exists("C:\\\\Projects\\\\app\\\\main.py")
        True
    """
    return Path(file_path).is_file()


def path_exists(path: PathLike) -> bool:
    """بررسی وجود هر نوع مسیر (فایل یا پوشه)
    Verify that a path (file or directory) exists.

    Args:
        path: مسیر مورد نظر (Path to check)

    Returns:
        True اگر مسیر وجود داشته باشد
    """
    return Path(path).exists()


def resolve_windows_path(path: PathLike) -> str:
    """تبدیل مسیر به فرمت استاندارد ویندوز
    Resolve and normalize a Windows path (handles forward/back slashes).

    Args:
        path: مسیر ورودی (Input path, e.g. "C:/Projects/app" or "C:\\\\Projects\\\\app")

    Returns:
        str: مسیر نرمال شده با بک‌اسلش (Normalized path with backslashes)

    مثال (Example):
        >>> resolve_windows_path("C:/Projects/app")
        'C:\\\\Projects\\\\app'
    """
    return str(Path(path).resolve())


def get_file_size(file_path: PathLike) -> int:
    """دریافت حجم فایل به بایت
    Get file size in bytes.

    Args:
        file_path: مسیر فایل

    Returns:
        int: حجم فایل (0 اگر فایل وجود نداشته باشد)

    مثال (Example):
        >>> get_file_size("debug.log")
        1024
    """
    try:
        return Path(file_path).stat().st_size
    except (OSError, FileNotFoundError):
        return 0


# ─────────────────────────────────────────────
# 2. مجوزهای دسترسی (Permission Handling)
# ─────────────────────────────────────────────

def is_file_readable(file_path: PathLike) -> bool:
    """بررسی اینکه آیا فایل قابل خواندن است
    Check if a file is readable on Windows.
    (On Windows, checks if file is not locked by another process.)

    Args:
        file_path: مسیر فایل

    Returns:
        True اگر فایل قابل خواندن باشد
    """
    p = Path(file_path)
    if not p.is_file():
        return False
    try:
        with open(p, "rb") as f:
            f.read(1)
        return True
    except (PermissionError, OSError):
        return False


def is_file_writable(file_path: PathLike) -> bool:
    """بررسی اینکه آیا فایل قابل نوشتن است
    Check if a file is writable on Windows.
    (Checks read-only attribute and file lock status.)

    Args:
        file_path: مسیر فایل

    Returns:
        True اگر فایل قابل نوشتن باشد

    نکته ویندوزی (Windows tip):
        در ویندوز اگر فایل در برنامه دیگری باز باشد، قابل نوشتن نیست.
        (On Windows, if a file is open in another program, it may not be writable.)
    """
    p = Path(file_path)
    if not p.is_file():
        return False
    try:
        with open(p, "ab") as f:
            pass
        return True
    except (PermissionError, OSError):
        return False


def is_file_locked(file_path: PathLike) -> bool:
    """بررسی قفل بودن فایل در ویندوز
    Check if a file is locked by another process on Windows.
    Useful before attempting to read/delete/edit a file.

    Args:
        file_path: مسیر فایل

    Returns:
        True اگر فایل توسط برنامه دیگری قفل شده باشد

    مثال (Example):
        >>> if is_file_locked("data.db"):
        ...     print("فایل در حال استفاده است - لطفاً برنامه را ببندید")
        ...     print("File is in use - please close the program")
    """
    p = Path(file_path)
    if not p.is_file():
        return False
    try:
        with open(p, "r+b") as f:
            try:
                f.tell()
            except OSError:
                return True
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def make_file_writable(file_path: PathLike) -> bool:
    """حذف ویژگی read-only از فایل در ویندوز
    Remove the read-only attribute from a file on Windows.

    Args:
        file_path: مسیر فایل

    Returns:
        True اگر عملیات موفق باشد
    """
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        current = p.stat().st_mode
        p.chmod(current | stat.S_IWRITE)
        return True
    except (OSError, PermissionError):
        return False


# ─────────────────────────────────────────────
# 3. عملیات فایل (File CRUD: Edit, Add, Delete)
# ─────────────────────────────────────────────

def read_file(
    file_path: PathLike,
    encoding: str = "utf-8",
    retry: int = 3,
    delay: float = 0.5,
) -> Optional[str]:
    """خواندن امن محتوای فایل با قابلیت تلاش مجدد
    Safely read file contents with retry mechanism for Windows.

    Args:
        file_path: مسیر فایل
        encoding: encoding (پیش‌فرض utf-8)
        retry: تعداد دفعات تلاش مجدد (Number of retry attempts)
        delay: تأخیر بین تلاش‌ها به ثانیه (Delay between retries in seconds)

    Returns:
        str: محتوای فایل (File content)
        None: اگر خطا رخ دهد (If an error occurs)

    مثال (Example):
        >>> content = read_file("config.json")
        >>> if content:
        ...     data = json.loads(content)
    """
    for attempt in range(retry):
        try:
            return Path(file_path).read_text(encoding=encoding)
        except FileNotFoundError:
            return None
        except PermissionError:
            if attempt < retry - 1:
                time.sleep(delay)
                continue
            return None
        except OSError:
            if attempt < retry - 1:
                time.sleep(delay)
                continue
            return None
    return None


def write_file(
    file_path: PathLike,
    content: str,
    encoding: str = "utf-8",
    backup: bool = True,
) -> bool:
    """نوشتن امن محتوای فایل با پشتیبان‌گیری
    Safely write content to a file with optional backup on Windows.

    Args:
        file_path: مسیر فایل
        content: محتوای جدید (New content)
        encoding: encoding (پیش‌فرض utf-8)
        backup: آیا از فایل قبلی پشتیبان تهیه شود (Create .bak backup)

    Returns:
        True اگر نوشتن موفق باشد

    مثال (Example):
        >>> write_file("settings.json", json.dumps(config, indent=2))
    """
    p = Path(file_path)
    try:
        if backup and p.is_file():
            backup_path = p.with_suffix(p.suffix + ".bak")
            shutil.copy2(str(p), str(backup_path))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return True
    except (OSError, PermissionError):
        return False


def append_to_file(
    file_path: PathLike,
    content: str,
    encoding: str = "utf-8",
    new_line: bool = True,
) -> bool:
    """اضافه کردن محتوا به انتهای فایل
    Append content to the end of a file on Windows.

    Args:
        file_path: مسیر فایل
        content: محتوایی که اضافه می‌شود (Content to append)
        encoding: encoding
        new_line: آیا قبل از append خط جدید اضافه شود (Add newline before)

    Returns:
        True اگر عملیات موفق باشد
    """
    try:
        with open(file_path, "a", encoding=encoding) as f:
            if new_line and Path(file_path).is_file() and Path(file_path).stat().st_size > 0:
                f.write("\n")
            f.write(content)
        return True
    except (OSError, PermissionError):
        return False


def prepend_to_file(
    file_path: PathLike,
    content: str,
    encoding: str = "utf-8",
) -> bool:
    """اضافه کردن محتوا به ابتدای فایل
    Prepend content to the beginning of a file on Windows.

    Args:
        file_path: مسیر فایل
        content: محتوایی که اضافه می‌شود (Content to prepend)
        encoding: encoding

    Returns:
        True اگر عملیات موفق باشد
    """
    try:
        p = Path(file_path)
        if p.is_file():
            existing = p.read_text(encoding=encoding)
        else:
            existing = ""
        p.write_text(content + "\n" + existing, encoding=encoding)
        return True
    except (OSError, PermissionError):
        return False


def delete_file(file_path: PathLike, trash: bool = True) -> bool:
    """حذف امن فایل با گزینه انتقال به سطل زباله
    Safely delete a file with optional move-to-trash behavior.

    Args:
        file_path: مسیر فایل
        trash: اگر True باشد، فایل به پوشه .trash منتقل می‌شود
               (If True, move to .trash folder instead of permanent delete)

    Returns:
        True اگر حذف موفق باشد

    نکته ویندوزی (Windows tip):
        اگر فایل در برنامه دیگری باز باشد در ویندوز قابل حذف نیست.
        (On Windows, open files in other programs cannot be deleted.)
    """
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        if trash:
            trash_dir = p.parent / ".trash"
            trash_dir.mkdir(parents=True, exist_ok=True)
            dest = trash_dir / p.name
            # Add timestamp to avoid name collision
            if dest.exists():
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest = trash_dir / f"{p.stem}_{stamp}{p.suffix}"
            shutil.move(str(p), str(dest))
        else:
            p.unlink()
        return True
    except (PermissionError, OSError):
        return False


def restore_from_trash(
    file_name: str,
    original_dir: PathLike,
) -> bool:
    """بازیابی فایل از پوشه .trash
    Restore a file from the .trash folder back to its original location.

    Args:
        file_name: نام فایل (File name to restore)
        original_dir: مسیر اصلی (Original directory)

    Returns:
        True اگر بازیابی موفق باشد
    """
    try:
        trash_dir = Path(original_dir) / ".trash"
        if not trash_dir.is_dir():
            return False
        # Try exact name first, then with timestamps
        for f in trash_dir.iterdir():
            if f.is_file() and (f.name == file_name or f.name.startswith(Path(file_name).stem)):
                shutil.move(str(f), str(Path(original_dir) / file_name))
                return True
        return False
    except (OSError, PermissionError):
        return False


def copy_file(
    src: PathLike,
    dst: PathLike,
    overwrite: bool = False,
) -> bool:
    """کپی کردن فایل با گزینه بازنویسی
    Copy a file with overwrite protection on Windows.

    Args:
        src: مسیر مبدأ (Source path)
        dst: مسیر مقصد (Destination path)
        overwrite: آیا فایل مقصد بازنویسی شود (Overwrite if exists)

    Returns:
        True اگر کپی موفق باشد
    """
    try:
        dest_path = Path(dst)
        if dest_path.exists() and not overwrite:
            return False
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dest_path))
        return True
    except (FileNotFoundError, PermissionError, OSError):
        return False


def move_file(src: PathLike, dst: PathLike, overwrite: bool = False) -> bool:
    """انتقال فایل از مکانی به مکان دیگر
    Move a file from one location to another on Windows.

    Args:
        src: مسیر مبدأ
        dst: مسیر مقصد
        overwrite: آیا فایل مقصد بازنویسی شود

    Returns:
        True اگر انتقال موفق باشد
    """
    try:
        dest_path = Path(dst)
        if dest_path.exists() and not overwrite:
            return False
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest_path))
        return True
    except (FileNotFoundError, PermissionError, OSError):
        return False


def rename_file(file_path: PathLike, new_name: str) -> bool:
    """تغییر نام فایل
    Rename a file on Windows.

    Args:
        file_path: مسیر فایل
        new_name: نام جدید (فقط نام، نه مسیر کامل)
                  (New name only, not full path)

    Returns:
        True اگر تغییر نام موفق باشد
    """
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        new_path = p.with_name(new_name)
        if new_path.exists():
            return False
        p.rename(new_path)
        return True
    except (OSError, PermissionError):
        return False


# ─────────────────────────────────────────────
# 4. عملیات پوشه (Directory CRUD)
# ─────────────────────────────────────────────

def create_directory(dir_path: PathLike, exist_ok: bool = True) -> bool:
    """ایجاد پوشه با تمام زیرپوشه‌های مورد نیاز
    Create a directory (and all parent directories) on Windows.

    Args:
        dir_path: مسیر پوشه (Directory path)
        exist_ok: اگر پوشه وجود داشته باشد خطا نده (Don't error if exists)

    Returns:
        True اگر ایجاد یا وجود داشته باشد
    """
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=exist_ok)
        return True
    except (OSError, PermissionError):
        return False


def delete_directory(dir_path: PathLike, force: bool = False) -> bool:
    """حذف پوشه و تمام محتویات آن
    Delete a directory and all its contents on Windows.

    Args:
        dir_path: مسیر پوشه
        force: اگر True باشد، حتی فایل‌های read-only حذف می‌شوند
               (If True, remove read-only files too)

    Returns:
        True اگر حذف موفق باشد

    نکته ویندوزی (Windows tip):
        ویندوز ممکن است پوشه‌های حاوی فایل‌های read-only را بدون force حذف نکند.
        (Windows may not delete folders with read-only files without force.)
    """
    try:
        p = Path(dir_path)
        if not p.is_dir():
            return False
        if force:

            def on_error(func, path, exc_info):
                try:
                    Path(path).chmod(stat.S_IWRITE)
                    func(path)
                except (OSError, PermissionError):
                    pass

            shutil.rmtree(str(p), onerror=on_error)
        else:
            shutil.rmtree(str(p))
        return True
    except (OSError, PermissionError):
        return False


def list_directory(
    dir_path: PathLike,
    pattern: Optional[str] = None,
    include_hidden: bool = False,
) -> list[dict]:
    """لیست کردن محتویات پوشه با جزئیات
    List directory contents with detailed info on Windows.

    Args:
        dir_path: مسیر پوشه
        pattern: الگوی فیلتر (مثلاً "*.py" برای فایل‌های پایتون)
                 (Filter pattern, e.g. "*.py")
        include_hidden: آیا فایل‌های مخفی نمایش داده شوند (Include hidden files)

    Returns:
        list[dict]: لیست dictionary‌های شامل name, path, is_dir, size, modified_at
                    (List of dicts with file details)

    مثال (Example):
        >>> files = list_directory(".", pattern="*.py")
        >>> for f in files:
        ...     print(f["name"], f["size"], "bytes")
    """
    results = []
    try:
        p = Path(dir_path)
        if not p.is_dir():
            return results
        for entry in p.iterdir():
            if not include_hidden and entry.name.startswith("."):
                continue
            if pattern:
                if not entry.match(pattern):
                    continue
            try:
                stat_info = entry.stat()
                results.append({
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "is_dir": entry.is_dir(),
                    "size": stat_info.st_size if entry.is_file() else 0,
                    "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                })
            except (OSError, PermissionError):
                results.append({
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "is_dir": entry.is_dir(),
                    "size": 0,
                    "modified_at": "",
                })
    except PermissionError:
        pass
    return results


def get_directory_size(dir_path: PathLike) -> int:
    """محاسبه حجم کل یک پوشه
    Calculate the total size of a directory on Windows.

    Args:
        dir_path: مسیر پوشه

    Returns:
        int: حجم کل به بایت (Total size in bytes)
    """
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except OSError:
        pass
    return total


# ─────────────────────────────────────────────
# 5. ویرایش کد و کامنت (Code & Comment Editing)
# ─────────────────────────────────────────────

def add_comment_to_file(
    file_path: PathLike,
    comment: str,
    language: str = "python",
    at_top: bool = True,
) -> bool:
    """اضافه کردن کامنت به فایل کد
    Add a comment header to a code file on Windows.

    Args:
        file_path: مسیر فایل
        comment: متن کامنت (Comment text)
        language: زبان برنامه‌نویسی ("python", "js", "html", "css", "sql", "bat", "ps1")
        at_top: اگر True باشد کامنت به بالای فایل اضافه می‌شود
                (If True, add at top; otherwise at bottom)

    Returns:
        True اگر عملیات موفق باشد

    مثال (Example):
        >>> add_comment_to_file("script.ps1",
        ...     "This script automates backup on Windows Server 2022",
        ...     language="ps1")
    """
    comment_styles = {
        "python": ("# " + comment, "# " + comment),
        "js": ("// " + comment, "// " + comment),
        "ts": ("// " + comment, "// " + comment),
        "html": (f"<!-- {comment} -->", f"<!-- {comment} -->"),
        "css": (f"/* {comment} */", f"/* {comment} */"),
        "sql": ("-- " + comment, "-- " + comment),
        "yaml": ("# " + comment, "# " + comment),
        "json": (f"// {comment}", f"// {comment}"),
        "bat": (f"REM {comment}", f"REM {comment}"),
        "ps1": (f"# {comment}", f"# {comment}"),
        "cpp": (f"// {comment}", f"// {comment}"),
        "c": (f"// {comment}", f"// {comment}"),
        "java": (f"// {comment}", f"// {comment}"),
        "rust": (f"// {comment}", f"// {comment}"),
        "go": (f"// {comment}", f"// {comment}"),
        "ruby": ("# " + comment, "# " + comment),
    }
    if language not in comment_styles:
        return False
    line_comment = comment_styles[language][0]
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        content = p.read_text(encoding="utf-8")
        if at_top:
            new_content = line_comment + "\n" + content
        else:
            new_content = content.rstrip("\n") + "\n" + line_comment + "\n"
        p.write_text(new_content, encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


def remove_comments(
    file_path: PathLike,
    language: str = "python",
    preserve_shebang: bool = True,
) -> bool:
    """حذف کامنت‌های تکی از فایل کد
    Remove single-line comments from a code file on Windows.

    Args:
        file_path: مسیر فایل
        language: زبان برنامه‌نویسی ("python", "js", "bat", "ps1", ...)
        preserve_shebang: اگر True باشد خط #! نگه داشته می‌شود
                           (If True, preserve #! shebang line)

    Returns:
        True اگر عملیات موفق باشد

    توجه (Note):
        این تابع فقط کامنت‌های تکی را حذف می‌کند، نه کامنت‌های چندخطی را.
        (This only removes single-line comments, not block comments.)
    """
    comment_prefixes = {
        "python": "#",
        "js": "//",
        "ts": "//",
        "sql": "--",
        "yaml": "#",
        "bat": "REM",
        "ps1": "#",
        "cpp": "//",
        "c": "//",
        "java": "//",
        "rust": "//",
        "go": "//",
        "ruby": "#",
    }
    if language not in comment_prefixes:
        return False
    prefix = comment_prefixes[language]
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        lines = p.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
            if language == "bat" and stripped.upper().startswith(prefix):
                continue  # Skip REM lines
            if preserve_shebang and i == 0 and stripped.startswith("#!"):
                new_lines.append(line)
                continue
            if stripped.startswith(prefix):
                continue  # Skip comment lines
            new_lines.append(line)
        p.write_text("\n".join(new_lines), encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


def insert_line_in_file(
    file_path: PathLike,
    line_number: int,
    content: str,
) -> bool:
    """درج خط در موقعیت مشخص فایل
    Insert a line at a specific position in a file on Windows.

    Args:
        file_path: مسیر فایل
        line_number: شماره خط (شروع از 1) (Line number, 1-indexed)
        content: محتوای خط جدید (New line content)

    Returns:
        True اگر درج موفق باشد
    """
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        lines = p.read_text(encoding="utf-8").splitlines()
        if line_number < 1:
            line_number = 1
        if line_number > len(lines):
            lines.append(content)
        else:
            lines.insert(line_number - 1, content)
        p.write_text("\n".join(lines), encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


def replace_line_in_file(
    file_path: PathLike,
    line_number: int,
    new_content: str,
) -> bool:
    """جایگزینی یک خط در فایل
    Replace a specific line in a file on Windows.

    Args:
        file_path: مسیر فایل
        line_number: شماره خط (شروع از 1)
        new_content: محتوای جدید خط

    Returns:
        True اگر جایگزینی موفق باشد
    """
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        lines = p.read_text(encoding="utf-8").splitlines()
        if line_number < 1 or line_number > len(lines):
            return False
        lines[line_number - 1] = new_content
        p.write_text("\n".join(lines), encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


def delete_line_in_file(file_path: PathLike, line_number: int) -> bool:
    """حذف یک خط از فایل
    Delete a specific line from a file on Windows.

    Args:
        file_path: مسیر فایل
        line_number: شماره خط (شروع از 1)

    Returns:
        True اگر حذف موفق باشد
    """
    try:
        p = Path(file_path)
        if not p.is_file():
            return False
        lines = p.read_text(encoding="utf-8").splitlines()
        if line_number < 1 or line_number > len(lines):
            return False
        lines.pop(line_number - 1)
        p.write_text("\n".join(lines), encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


def search_and_replace_in_file(
    file_path: PathLike,
    search_text: str,
    replace_text: str,
    count: int = 0,
) -> int:
    """جستجو و جایگزینی متن در فایل
    Search and replace text in a file on Windows.

    Args:
        file_path: مسیر فایل
        search_text: متن مورد جستجو
        replace_text: متن جایگزین
        count: تعداد دفعات جایگزینی (0 = همه موارد)
               (Number of replacements, 0 = all)

    Returns:
        int: تعداد جایگزینی‌های انجام شده (Number of replacements made)
    """
    try:
        p = Path(file_path)
        if not p.is_file():
            return 0
        content = p.read_text(encoding="utf-8")
        if count <= 0:
            new_content = content.replace(search_text, replace_text)
        else:
            new_content = content.replace(search_text, replace_text, count)
        if new_content != content:
            p.write_text(new_content, encoding="utf-8")
        return (len(content) - len(new_content)) // max(len(replace_text) - len(search_text), 1)
    except (OSError, PermissionError):
        return 0


# ─────────────────────────────────────────────
# 6. ابزارهای عمومی (General Utilities)
# ─────────────────────────────────────────────

def get_file_info(file_path: PathLike) -> dict[str, Any]:
    """دریافت اطلاعات کامل یک فایل
    Get comprehensive metadata about a file on Windows.

    Args:
        file_path: مسیر فایل

    Returns:
        dict: شامل name, path, size, created, modified, extension, is_readable, is_writable, is_locked
              (Full file metadata including Windows attribute info)

    مثال (Example):
        >>> info = get_file_info("config.json")
        >>> print(f"Size: {info['size']} bytes, Modified: {info['modified_at']}")
    """
    result: dict[str, Any] = {
        "name": "",
        "path": "",
        "size": 0,
        "created_at": "",
        "modified_at": "",
        "extension": "",
        "exists": False,
        "is_file": False,
        "is_dir": False,
        "is_readable": False,
        "is_writable": False,
        "is_locked": False,
    }
    try:
        p = Path(file_path)
        result["name"] = p.name
        result["path"] = str(p.resolve())
        result["extension"] = p.suffix
        result["exists"] = p.exists()
        result["is_file"] = p.is_file()
        result["is_dir"] = p.is_dir()
        if p.exists():
            stat_info = p.stat()
            result["size"] = stat_info.st_size
            result["created_at"] = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
            result["modified_at"] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            if p.is_file():
                result["is_readable"] = is_file_readable(p)
                result["is_writable"] = is_file_writable(p)
                result["is_locked"] = is_file_locked(p)
    except OSError:
        pass
    return result


def safe_json_read(file_path: PathLike, default: Any = None) -> Any:
    """خواندن امن فایل JSON
    Safely read a JSON file with error handling on Windows.

    Args:
        file_path: مسیر فایل JSON
        default: مقدار پیش‌فرض در صورت خطا (Default value on error)

    Returns:
        Any: داده‌های JSON یا مقدار پیش‌فرض
    """
    content = read_file(file_path)
    if content is None:
        return default
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return default


def safe_json_write(file_path: PathLike, data: Any, indent: int = 2) -> bool:
    """نوشتن امن فایل JSON
    Safely write a JSON file with formatting on Windows.

    Args:
        file_path: مسیر فایل JSON
        data: داده‌های JSON
        indent: تورفتگی (Indentation level)

    Returns:
        True اگر نوشتن موفق باشد
    """
    try:
        content = json.dumps(data, indent=indent, ensure_ascii=False)
        return write_file(file_path, content)
    except (TypeError, ValueError):
        return False


def ensure_dir_exists(dir_path: PathLike) -> bool:
    """اطمینان از وجود پوشه (ایجاد در صورت نیاز)
    Ensure a directory exists, creating it if necessary on Windows.

    Args:
        dir_path: مسیر پوشه

    Returns:
        True اگر پوشه وجود داشته باشد یا ایجاد شود
    """
    return create_directory(dir_path, exist_ok=True)


def get_windows_drives() -> list[str]:
    """دریافت لیست درایوهای ویندوز
    Get list of available Windows drives.

    Returns:
        list[str]: لیست درایوها (Drive letters, e.g. ["C:", "D:", "E:"])

    مثال (Example):
        >>> drives = get_windows_drives()
        >>> print("Available drives:", drives)
    """
    drives = []
    try:
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(f"{letter}:")
    except Exception:
        pass
    return drives


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """پاکسازی نام فایل برای ویندوز
    Sanitize a filename for Windows by removing invalid characters.

    Args:
        name: نام پیشنهادی (Suggested name)
        replacement: کاراکتر جایگزین (Replacement character)

    Returns:
        str: نام فایل امن برای ویندوز (Windows-safe filename)

    نکته ویندوزی (Windows tip):
        کاراکترهای غیرمجاز در ویندوز: \\ / : * ? \" < > |
        (Invalid Windows filename characters: \\ / : * ? \" < > |)
    """
    invalid_chars = set('<>:"/\\|?*')
    result = "".join(replacement if c in invalid_chars else c for c in name)
    # Windows reserved names
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    stem = Path(result).stem.upper()
    if stem in reserved:
        result = replacement + result
    # Windows max path length
    if len(result) > 255:
        name_part = Path(result).stem[:250]
        ext = Path(result).suffix
        result = name_part + ext
    return result


# ─────────────────────────────────────────────
# 7. مدیریت تصویر (Image Utilities)
# ─────────────────────────────────────────────

def verify_image_path(image_path: PathLike) -> dict[str, Any]:
    """بررسی کامل مسیر تصویر
    Comprehensively verify an image file path on Windows.

    شامل بررسی‌های (Includes checks for):
    - وجود فایل (File existence)
    - مجوز خواندن (Read permission)
    - قفل نبودن (Not locked)
    - فرمت پشتیبانی شده (Supported format)

    Args:
        image_path: مسیر تصویر

    Returns:
        dict: شامل status, path, exists, readable, locked, format, size, error
              (Verification result with all checks)

    مثال (Example):
        >>> result = verify_image_path("screenshot.png")
        >>> if not result["success"]:
        ...     print(f"Error: {result['error']}")
    """
    result: dict[str, Any] = {
        "success": False,
        "path": str(image_path),
        "exists": False,
        "readable": False,
        "locked": False,
        "format": None,
        "size": 0,
        "error": None,
    }
    p = Path(image_path)
    if not p.is_file():
        result["error"] = f"فایل وجود ندارد | File not found: {image_path}"
        return result
    result["exists"] = True
    if not is_file_readable(p):
        result["error"] = (
            f"فایل قابل خواندن نیست | File not readable: {image_path}. "
            "در ویندوز، مطمئن شوید فایل در برنامه دیگری باز نباشد. "
            "On Windows, ensure the file is not open in another program."
        )
        return result
    result["readable"] = True
    result["locked"] = is_file_locked(p)
    ext = p.suffix.lower()
    supported = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".ico"}
    if ext not in supported:
        result["error"] = (
            f"فرمت تصویر پشتیبانی نمی‌شود | Unsupported image format: {ext}. "
            f"فرمت‌های مجاز: {', '.join(sorted(supported))}"
        )
        return result
    result["format"] = ext
    result["size"] = get_file_size(p)
    result["success"] = True
    return result
