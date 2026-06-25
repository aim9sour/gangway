import tempfile
import os
import pytest
import base64
import zipfile
import tarfile
from gangway.core.files import (
    list_directory,
    glob_search,
    preview_file,
    project_overview,
    upload_chunk,
    assemble_upload,
    download_chunk,
    compress_archive,
    extract_archive,
)


def test_list_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file and a subdirectory
        file_path = os.path.join(tmpdir, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("content")

        subdir_path = os.path.join(tmpdir, "subdir")
        os.makedirs(subdir_path, exist_ok=True)

        # Test listing directory
        entries = list_directory(tmpdir, tmpdir)
        assert len(entries) == 2

        file_entry = next(e for e in entries if e["name"] == "test_file.txt")
        assert file_entry["is_dir"] is False
        assert file_entry["size"] == 7
        assert "modified" in file_entry

        subdir_entry = next(e for e in entries if e["name"] == "subdir")
        assert subdir_entry["is_dir"] is True
        assert subdir_entry["size"] is None

        # Test listing non-directory
        with pytest.raises(NotADirectoryError):
            list_directory(file_path, tmpdir)

        # Test sandboxing
        outside_path = os.path.join(tmpdir, "..")
        with pytest.raises(PermissionError):
            list_directory(outside_path, tmpdir)


def test_glob_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files
        file1 = os.path.join(tmpdir, "a.py")
        file2 = os.path.join(tmpdir, "b.txt")
        subdir = os.path.join(tmpdir, "sub")
        os.makedirs(subdir, exist_ok=True)
        file3 = os.path.join(subdir, "c.py")

        for fpath in [file1, file2, file3]:
            with open(fpath, "w") as f:
                f.write("dummy")

        # Search for .py files
        py_files = glob_search("**/*.py", tmpdir)
        assert len(py_files) == 2
        # Verify paths are returned (may be resolved or not depending on implementation, but must end with appropriate subpaths)
        assert any(f.endswith("a.py") for f in py_files)
        assert any(f.endswith("c.py") for f in py_files)

        # Search with pattern that tries to go outside allowed_root
        # Should not include files from outside allowed_root
        results = glob_search("../**/*", subdir)
        # Results should only contain files within subdir, even if glob matched parent files
        assert all(f.startswith(subdir) for f in results)


def test_preview_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Test small file (no omission)
        small_file = os.path.join(tmpdir, "small.txt")
        with open(small_file, "w") as f:
            f.write("line 1\nline 2")

        preview = preview_file(small_file, tmpdir, head=5, tail=5)
        assert preview == "line 1\nline 2"

        # 2. Test large file (omission)
        large_file = os.path.join(tmpdir, "large.txt")
        lines = [f"Line {i}\n" for i in range(200)]
        with open(large_file, "w") as f:
            f.writelines(lines)

        preview = preview_file(large_file, tmpdir, head=10, tail=5)
        assert "Line 0" in preview
        assert "Line 9" in preview
        assert "OMITTED" in preview
        assert "Line 199" in preview
        assert "Line 10\n" not in preview

        # 3. Test sandboxing
        outside_file = os.path.join(tmpdir, "..", "outside.txt")
        with pytest.raises(PermissionError):
            preview_file(outside_file, tmpdir)


def test_project_overview():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create readme
        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write("Project Readme info")

        # Create git and venv directories to ensure they are ignored
        git_dir = os.path.join(tmpdir, ".git")
        os.makedirs(git_dir, exist_ok=True)
        with open(os.path.join(git_dir, "config"), "w") as f:
            f.write("git config")

        venv_dir = os.path.join(tmpdir, ".venv")
        os.makedirs(venv_dir, exist_ok=True)
        with open(os.path.join(venv_dir, "pip.conf"), "w") as f:
            f.write("pip config")

        # Create some project files
        src_dir = os.path.join(tmpdir, "src")
        os.makedirs(src_dir, exist_ok=True)
        main_py = os.path.join(src_dir, "main.py")
        with open(main_py, "w") as f:
            f.write("print('hello')")

        nested_dir = os.path.join(src_dir, "utils", "helpers")
        os.makedirs(nested_dir, exist_ok=True)
        helper_py = os.path.join(nested_dir, "helper.py")
        with open(helper_py, "w") as f:
            f.write("def help(): pass")

        # Verify overview
        overview = project_overview(tmpdir, tmpdir)

        # Files should contain README.md and src/main.py
        # But should NOT contain .git/config, .venv/pip.conf
        assert "README.md" in overview["files"]
        assert os.path.join("src", "main.py").replace("\\", "/") in [
            f.replace("\\", "/") for f in overview["files"]
        ]
        assert not any(".git" in f or ".venv" in f for f in overview["files"])

        # Walk depth limit: since depth limit is 3 (max depth 3 - wait, let's check:
        # os.walk depth check: Target depth is 0, src depth is 1, utils depth is 2, helpers depth is 3.
        # "depth > 2: dirs.clear() # don't descend further"
        # So it descends into src, and then under src it has dirs like utils.
        # For utils, depth is 2. So it lists utils files, but does not descend into helpers.
        # Thus helper_py (depth 3) should NOT be in overview["files"]
        assert os.path.join("src", "utils", "helpers", "helper.py").replace(
            "\\", "/"
        ) not in [f.replace("\\", "/") for f in overview["files"]]

        # Readme content
        assert overview["readme_content"] == "Project Readme info"

        # Recent files
        assert "README.md" in overview["recent_files"]
        assert os.path.join("src", "main.py").replace("\\", "/") in [
            f.replace("\\", "/") for f in overview["recent_files"]
        ]

        # Test sandboxing
        outside_path = os.path.join(tmpdir, "..")
        with pytest.raises(PermissionError):
            project_overview(outside_path, tmpdir)


def test_chunked_transfer_and_archives():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test_binary.bin")
        data = b"Hello, this is a binary chunk transfer test!"
        data_b64 = base64.b64encode(data).decode("utf-8")

        # Split into 2 chunks
        chunk1 = data_b64[: len(data_b64) // 2]
        chunk2 = data_b64[len(data_b64) // 2 :]

        assert upload_chunk(file_path, 0, 2, chunk1, tmpdir) is True
        assert upload_chunk(file_path, 1, 2, chunk2, tmpdir) is True

        final_path = assemble_upload(file_path, 2, tmpdir)
        with open(final_path, "rb") as f:
            assert f.read() == data

        # Test download chunk
        dl = download_chunk(file_path, 0, 10, tmpdir)
        assert dl["chunk_index"] == 0
        assert dl["has_more"] is True
        assert base64.b64decode(dl["data_b64"]) == data[:10]

        dl_last = download_chunk(file_path, 4, 10, tmpdir)
        assert dl_last["chunk_index"] == 4
        assert dl_last["has_more"] is False
        assert base64.b64decode(dl_last["data_b64"]) == data[40:]

        # Test download chunk with nonexistent file
        with pytest.raises(FileNotFoundError):
            download_chunk(os.path.join(tmpdir, "missing.bin"), 0, 10, tmpdir)

        # Archive compression/decompression for zip
        archive_file = os.path.join(tmpdir, "archive.zip")
        sub_dir = os.path.join(tmpdir, "subdir")
        os.makedirs(sub_dir, exist_ok=True)
        with open(os.path.join(sub_dir, "inner.txt"), "w") as f:
            f.write("archived content")

        compress_archive(archive_file, sub_dir, tmpdir, format="zip")
        assert os.path.exists(archive_file)

        out_dir = os.path.join(tmpdir, "out")
        extract_archive(archive_file, out_dir, tmpdir)
        with open(os.path.join(out_dir, "inner.txt"), "r") as f:
            assert f.read() == "archived content"

        # Archive compression/decompression for tar.gz
        tar_archive_file = os.path.join(tmpdir, "archive.tar.gz")
        compress_archive(tar_archive_file, sub_dir, tmpdir, format="tar.gz")
        # May be written as archive.tar.gz
        assert os.path.exists(tar_archive_file) or os.path.exists(
            tar_archive_file + ".tar.gz"
        )
        actual_tar_path = (
            tar_archive_file
            if os.path.exists(tar_archive_file)
            else tar_archive_file + ".tar.gz"
        )

        tar_out_dir = os.path.join(tmpdir, "tar_out")
        extract_archive(actual_tar_path, tar_out_dir, tmpdir)
        with open(os.path.join(tar_out_dir, "inner.txt"), "r") as f:
            assert f.read() == "archived content"

        # Test unsupported format
        with pytest.raises(ValueError):
            compress_archive(
                os.path.join(tmpdir, "archive.rar"), sub_dir, tmpdir, format="rar"
            )
        with pytest.raises(ValueError):
            extract_archive(os.path.join(tmpdir, "archive.rar"), tar_out_dir, tmpdir)


def test_chunked_transfer_and_archives_sandboxing():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create allowed root and outside directory
        allowed_dir = os.path.join(tmpdir, "allowed")
        outside_dir = os.path.join(tmpdir, "outside")
        os.makedirs(allowed_dir, exist_ok=True)
        os.makedirs(outside_dir, exist_ok=True)

        outside_file = os.path.join(outside_dir, "leak.bin")
        data_b64 = base64.b64encode(b"secret").decode("utf-8")

        # 1. upload_chunk sandboxing
        with pytest.raises(PermissionError):
            upload_chunk(outside_file, 0, 1, data_b64, allowed_dir)

        # 2. assemble_upload sandboxing
        with pytest.raises(PermissionError):
            assemble_upload(outside_file, 1, allowed_dir)

        # 3. download_chunk sandboxing
        with pytest.raises(PermissionError):
            download_chunk(outside_file, 0, 10, allowed_dir)

        # 4. compress_archive sandboxing
        archive_file = os.path.join(allowed_dir, "archive.zip")
        with pytest.raises(PermissionError):
            # source outside allowed root
            compress_archive(archive_file, outside_dir, allowed_dir)
        with pytest.raises(PermissionError):
            # target outside allowed root
            compress_archive(
                os.path.join(outside_dir, "archive.zip"), allowed_dir, allowed_dir
            )

        # 5. extract_archive sandboxing
        # Write a dummy zip first
        dummy_zip = os.path.join(allowed_dir, "dummy.zip")
        with zipfile.ZipFile(dummy_zip, "w") as zf:
            zf.writestr("test.txt", "hello")
        with pytest.raises(PermissionError):
            # archive outside allowed root
            extract_archive(
                os.path.join(outside_dir, "dummy.zip"), allowed_dir, allowed_dir
            )
        with pytest.raises(PermissionError):
            # target extraction outside allowed root
            extract_archive(dummy_zip, outside_dir, allowed_dir)

        # 6. Malicious path traversal in Zip extraction
        traversal_zip = os.path.join(allowed_dir, "traversal.zip")
        with zipfile.ZipFile(traversal_zip, "w") as zf:
            zf.writestr("../traversal.txt", "evil")
        with pytest.raises(PermissionError):
            extract_archive(traversal_zip, allowed_dir, allowed_dir)

        # 7. Malicious path traversal in Tar extraction
        traversal_tar = os.path.join(allowed_dir, "traversal.tar.gz")
        with tarfile.open(traversal_tar, "w:gz") as tf:
            ti = tarfile.TarInfo(name="../traversal.txt")
            import io

            tf.addfile(ti, io.BytesIO(b"evil"))
        with pytest.raises(PermissionError):
            extract_archive(traversal_tar, allowed_dir, allowed_dir)


def test_compress_archive_case_insensitive():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub_dir = os.path.join(tmpdir, "subdir")
        os.makedirs(sub_dir, exist_ok=True)
        with open(os.path.join(sub_dir, "file.txt"), "w") as f:
            f.write("test case insensitivity")

        # ZIP uppercase format and suffix
        zip_path = os.path.join(tmpdir, "TEST_ARCHIVE.ZIP")
        res = compress_archive(zip_path, sub_dir, tmpdir, format="ZIP")
        # should return path ending with lowercase '.zip' as generated by shutil
        assert res.lower().endswith(".zip")
        assert os.path.exists(res)
