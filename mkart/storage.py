from whitenoise.storage import CompressedManifestStaticFilesStorage
from django.core.files.storage import get_storage_class

class IgnoreMissingCompressedStorage(CompressedManifestStaticFilesStorage):
    def post_process(self, *args, **kwargs):
        try:
            return super().post_process(*args, **kwargs)
        except Exception as e:
            if "could not be found" in str(e):
                return  # Ignore missing source maps
            raise