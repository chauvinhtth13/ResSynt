from whitenoise.storage import CompressedManifestStaticFilesStorage

class NonStrictCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Subclass of WhiteNoise storage that disables strict manifest checking.
    This prevents the build from failing if a referenced file (like a .map file) is missing.
    """
    manifest_strict = False
