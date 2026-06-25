import tempfile
import pytest
import os
from pathlib import Path
from gangway.core.sandbox import verify_path


def test_verify_path_sandbox():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed = str(Path(tmpdir).resolve())
        valid_file = os.path.join(allowed, "file.txt")
        # Ensure we test a subpath
        subpath_file = os.path.join(allowed, "subdir", "file.txt")
        # Ensure we test a path outside the allowed root
        invalid_file = os.path.join(allowed, "..", "outside.txt")

        # Test valid path
        assert verify_path(valid_file, allowed) == valid_file

        # Test valid subpath (nested)
        # Note: verify_path returns the resolved absolute path as a string.
        # Let's ensure verify_path resolves it.
        resolved_subpath = str(Path(subpath_file).resolve())
        # verify_path will resolve it but since it doesn't exist physically,
        # resolve() in Python on Windows/Linux resolves paths lexically if they don't exist.
        # Let's verify that lexical or physical resolution doesn't crash.
        assert verify_path(subpath_file, allowed) == resolved_subpath

        # Test exactly the allowed root
        assert verify_path(allowed, allowed) == allowed

        # Test invalid path (outside allowed root)
        with pytest.raises(PermissionError):
            verify_path(invalid_file, allowed)

        # Test allowed root is None -> all paths allowed and resolved absolutely
        assert verify_path(invalid_file, None) == os.path.abspath(invalid_file)
