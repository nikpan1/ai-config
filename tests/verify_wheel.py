"""Check packaged resources from the built wheel, outside the repository cwd."""

import os
import sys
import tempfile
from pathlib import Path

wheel = next(Path("dist").glob("*.whl")).resolve()
sys.path.insert(0, str(wheel))
original_directory = Path.cwd()
with tempfile.TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        from importlib.resources import files

        import docgen
        from docgen.config import PROMPTS
        from docgen.llm import load_prompt

        assert ".whl" in docgen.__file__
        for prompt in {p for group in PROMPTS.values() for p in group}:
            assert load_prompt(prompt)[0]["id"] == prompt
        assert len(files("docgen").joinpath("static", "vis-network.min.js").read_bytes()) > 100000
        assert files("docgen").joinpath("static", "vis-network.LICENSE").read_text("utf-8")
    finally:
        os.chdir(original_directory)
print("Wheel imports and packaged prompts/preview assets passed outside repository cwd.")
