# Dev task runner. Use: .\Makefile.ps1 <task>
# All tools run as Python modules to sidestep Windows Smart App Control.
param([string]$task = "help")

switch ($task) {
    "lint"    { uv run python -m ruff check . }
    "format"  { uv run python -m ruff format . }
    "type"    { uv run python -m mypy src }
    "test"    { uv run python -m pytest }
    "check"   {
        uv run python -m ruff check .
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        uv run python -m mypy src
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        uv run python -m pytest
    }
    "help"    { Write-Host "Tasks: lint, format, type, test, check" }
    default   { Write-Host "Unknown task: $task. Run '.\Makefile.ps1 help'." }
}
