from whitenoise.storage import CompressedManifestStaticFilesStorage

class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False  # Don't crash on missing referenced files