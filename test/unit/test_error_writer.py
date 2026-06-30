from datetime import date
from infrastructure.error_writer import ErrorReportWriter

def test_error_report_writer_creates_dated_file(tmp_path):
    writer = ErrorReportWriter(tmp_path)

    assert writer.directory == tmp_path
    assert writer.path.parent == tmp_path
    assert writer.path.name == f"daily_maintenance_{date.today().isoformat()}.txt"

def test_error_report_writer_starts_new_report(tmp_path):
    writer = ErrorReportWriter(tmp_path)
    writer.start_new_report()

    assert writer.path.exists()
    assert writer.path.read_text(encoding="utf-8") == ""

def test_error_report_writer_writes_line(tmp_path):
    writer = ErrorReportWriter(tmp_path)
    writer.start_new_report()
    writer.write_line("something failed")

    content = writer.path.read_text(encoding="utf-8")
    assert "something failed" in content
    assert content.startswith("[")
    assert content.endswith("\n")

def test_error_report_writer_has_content(tmp_path):
    writer = ErrorReportWriter(tmp_path)
    writer.start_new_report()
    assert not writer.has_content()

    writer.write_line("boom")
    assert writer.has_content()

def test_error_report_writer_clear(tmp_path):
    writer = ErrorReportWriter(tmp_path)
    writer.start_new_report()
    writer.write_line("boom")
    writer.clear()

    assert writer.path.read_text(encoding="utf-8") == ""

def test_error_report_writer_uses_only_current_day_file(tmp_path):
    old_writer = ErrorReportWriter(
        directory=tmp_path,
        filename="daily_maintenance_2000-01-01.txt",
    )
    old_writer.start_new_report()
    old_writer.write_line("old report")

    writer = ErrorReportWriter(tmp_path)
    writer.start_new_report()

    old_content = old_writer.path.read_text(encoding="utf-8")
    assert "old report" in old_content
    assert writer.path == tmp_path / f"daily_maintenance_{date.today().isoformat()}.txt"
    assert writer.has_content() is False

    writer.write_line("new issue")
    assert writer.has_content() is True
    assert "old report" in old_writer.path.read_text(encoding="utf-8")

    assert writer.path != old_writer.path

