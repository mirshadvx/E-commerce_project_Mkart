from whitenoise.storage import CompressedStaticFilesStorage


class IgnoreMissingCompressedStorage(CompressedStaticFilesStorage):
    """Compress static files without failing on stale vendor CSS references."""

    pass
