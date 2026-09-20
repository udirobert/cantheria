from pathlib import Path

from cantheria.index import chunk_repo


def test_python_function_chunking(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(
        "import os\n\n"
        "def parse_user(data):\n"
        "    return eval(data)\n\n\n"
        "class Loader:\n"
        "    def load(self, path):\n"
        "        return open(path).read()\n"
    )
    chunks = chunk_repo(tmp_path)
    symbols = {c.symbol for c in chunks}
    assert "parse_user" in symbols
    assert "Loader" in symbols or "load" in symbols
    pu = next(c for c in chunks if c.symbol == "parse_user")
    assert "eval(data)" in pu.text
    assert pu.start_line == 3


def test_rust_fallback_chunking(tmp_path: Path) -> None:
    (tmp_path / "main.rs").write_text(
        "fn read_input(buf: &[u8]) -> usize {\n    buf.len()\n}\n\n"
        "pub fn parse(s: &str) -> u32 {\n    1\n}\n"
    )
    chunks = chunk_repo(tmp_path)
    assert chunks, "rust file should still produce chunks"
    assert all(c.path == "main.rs" for c in chunks)


def test_skips_vendor_dirs(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.py").write_text("def a():\n    pass\n")
    (tmp_path / "real.py").write_text("def b():\n    pass\n")
    chunks = chunk_repo(tmp_path)
    assert {c.path for c in chunks} == {"real.py"}
