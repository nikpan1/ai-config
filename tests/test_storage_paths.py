import os
from pathlib import Path, PureWindowsPath

import pytest

from docgen_graph.storage import ArtifactStore, windows_extended_path


@pytest.mark.skipif(os.name != "nt", reason="Exercises Windows realpath error-code transition")
def test_concurrent_parent_creation_during_resolution_preserves_containment(tmp_path, monkeypatch):
    import ntpath

    try:
        ntpath._getfinalpathname(str(tmp_path))
    except OSError:
        pytest.skip("Canonical Windows filesystem resolution is unavailable")
    store = ArtifactStore(tmp_path)
    target = store.root / "cache" / "response.json"
    original = ntpath._getfinalpathname
    transitions = []

    def resolve_with_parent_created(path):
        try:
            return original(path)
        except OSError as error:
            if str(path) == str(target) and not transitions:
                transitions.append(error.winerror)
                target.parent.mkdir()
            raise

    monkeypatch.setattr(ntpath, "_getfinalpathname", resolve_with_parent_created)
    result = store.write("cache/response.json", '{"result": "saved"}')
    assert transitions == [3]
    assert result.read_text() == '{"result": "saved"}'
    assert target.read_text() == result.read_text()


@pytest.mark.parametrize(
    "value,expected",
    [
        (r"C:\workspace\result.json", r"\\?\C:\workspace\result.json"),
        (r"\\?\C:\workspace\result.json", r"\\?\C:\workspace\result.json"),
        (r"\\server\share\result.json", r"\\?\UNC\server\share\result.json"),
        (r"\\?\UNC\server\share\result.json", r"\\?\UNC\server\share\result.json"),
    ],
)
def test_extended_windows_path_is_idempotent_and_preserves_unc(value, expected):
    assert windows_extended_path(PureWindowsPath(value)) == expected


def test_parent_traversal_still_cannot_write_outside_store(tmp_path):
    store = ArtifactStore(tmp_path / "workspace")
    with pytest.raises(ValueError, match="Artifact path leaves workspace"):
        store.write("../outside.json", "forbidden")
    with pytest.raises(ValueError, match="Event path leaves workspace"):
        store.event("../../../outside", "stage", "event")
    assert not (tmp_path / "outside.json").exists()


def test_resolved_symlink_escape_still_cannot_write_outside_store(tmp_path):
    store = ArtifactStore(tmp_path / "workspace")
    external = tmp_path / "external"
    external.mkdir()
    link = store.root / "link"
    try:
        link.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this account")
    with pytest.raises(ValueError, match="Artifact path leaves workspace"):
        store.write("link/outside.json", "forbidden")
    assert not (external / "outside.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows extended paths")
def test_extended_absolute_path_cannot_bypass_containment(tmp_path):
    store = ArtifactStore(tmp_path / "workspace")
    destination = Path(windows_extended_path((tmp_path / "outside.json").resolve()))
    with pytest.raises(ValueError, match="Artifact path leaves workspace"):
        store.write(str(destination), "forbidden")
    assert not destination.exists()
