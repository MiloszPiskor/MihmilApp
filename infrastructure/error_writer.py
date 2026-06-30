from pathlib import Path
from datetime import date, datetime
from typing import Optional


class ErrorReportWriter:
    def __init__(self, directory: str | Path, filename: str | None = None):
        self.directory = Path(directory) # folder
        self.directory.mkdir(parents=True, exist_ok=True)
        if filename is None:
            filename = f"daily_maintenance_{date.today().isoformat()}.txt"
        self.path = self.directory / filename # full path to the file

    def start_new_report(self):
        self.path.write_text("", encoding="utf-8")

    def write_line(self, text: str):
        stamp = datetime.now().isoformat(timespec="seconds")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {text}\n")

    def has_content(self):
        return self.path.exists() and self.path.stat().st_size > 0

    def clear(self):
        self.path.write_text("")

