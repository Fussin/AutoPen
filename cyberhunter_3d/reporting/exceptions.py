class ReportingError(Exception):
    """Base class for exceptions in the reporting module."""
    pass

class DataFinalizationError(ReportingError):
    """Exception raised for errors in the data finalization process."""
    pass

class ReportGenerationError(ReportingError):
    """Exception raised for errors in the report generation process."""
    pass
