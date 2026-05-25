"""CLI smoke tests."""

from typer.testing import CliRunner

from sinoquantis.cli import app

runner = CliRunner()


def test_doctor_runs() -> None:
    """doctor command should run successfully."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "SinoQuantis doctor" in result.output
