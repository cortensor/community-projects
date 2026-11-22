"""Public entrypoint for the report_exporter vertical slice."""

from src.features.report_exporter._exporter import export_diagnostic_artifacts

__all__ = ["export_diagnostic_artifacts"]
