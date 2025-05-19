import sys
from types import ModuleType

# Stub out heavy/optional external dependencies so unit tests can run
# in environments where these packages are not installed.
for mod_name in ["google.generativeai", "SPARQLWrapper"]:
    if mod_name not in sys.modules:
        dummy_module = ModuleType(mod_name)
        # Add minimal attributes used in code paths during import
        if mod_name == "google.generativeai":
            def _noop(*args, **kwargs):
                return None
            dummy_module.configure = _noop  # type: ignore[attr-defined]
            class _DummyModel:
                def generate_content(self, *args, **kwargs):
                    raise RuntimeError("Dummy GenerativeModel should be patched in tests.")
            dummy_module.GenerativeModel = _DummyModel  # type: ignore[attr-defined]
        sys.modules[mod_name] = dummy_module 