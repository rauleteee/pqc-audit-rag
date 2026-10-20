"""Exceptions shared across layers without pulling in optional dependencies."""


class PublishError(RuntimeError):
    """The job id could not be delivered to the queue."""
