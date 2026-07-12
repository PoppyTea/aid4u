🧹 [Code Health] Replace print statements with logfire in secrets management

🎯 **What:** Replaced direct `print` statements in `core/secrets.py` with `logfire` structured logging.
💡 **Why:** This improves the maintainability and observability of the codebase by adhering to the standard logging pattern used across the project (`logfire`). It ensures secrets management operations are properly traced and logged alongside other application events.
✅ **Verification:** Verified by ensuring the code passes the existing test suite (`uv run pytest tests/`). Since the change only touches `print` -> `logfire` replacements, functionality is fully preserved.
✨ **Result:** Improved code health, cleaner console output, and consistent logging practice across the `core/` module.
