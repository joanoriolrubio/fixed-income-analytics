# Local validation

Validated on Python 3.12.14, macOS ARM64.

- 43 pytest cases passed, including Streamlit widget interaction.
- Analytics statement coverage: 99.48% (191/192 statements).
- Ruff lint and formatting checks passed.
- Strict mypy passed for all six engine modules.
- Source distribution and universal Python wheel built successfully.
- Browser inspection confirmed the dashboard renders with the configured dark theme.
- Synthetic calibration maximum absolute residual: 3.90e-11 per 100 face.

GitHub Actions is configured for Python 3.11, 3.12 and 3.13; remote CI has not yet run.
The exact local dependency snapshot is in `validated-environment.txt`. It is a reproducibility record, not a cross-platform lockfile.
