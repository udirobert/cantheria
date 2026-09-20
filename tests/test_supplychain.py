"""Lockfile parsing + advisory mapping — no network required."""

from cantheria.supplychain import _fixed, _severity, parse_lockfiles


def test_parse_cargo_lock(tmp_path):
    (tmp_path / "Cargo.lock").write_text(
        'version = 3\n\n[[package]]\nname = "serde"\nversion = "1.0.0"\n\n'
        '[[package]]\nname = "tokio"\nversion = "1.40.0"\n'
    )
    pkgs = parse_lockfiles(tmp_path)
    assert {(p["name"], p["version"], p["ecosystem"]) for p in pkgs} == {
        ("serde", "1.0.0", "crates.io"),
        ("tokio", "1.40.0", "crates.io"),
    }


def test_parse_package_lock(tmp_path):
    (tmp_path / "package-lock.json").write_text(
        '{"packages": {"": {"name": "root"}, "node_modules/lodash": {"version": "4.17.20"}}}'
    )
    pkgs = parse_lockfiles(tmp_path)
    assert pkgs == [
        {
            "ecosystem": "npm",
            "name": "lodash",
            "version": "4.17.20",
            "lockfile": "package-lock.json",
        }
    ]


def test_parse_pnpm_lock_scoped(tmp_path):
    (tmp_path / "pnpm-lock.yaml").write_text(
        "snapshots:\n  '@scope/pkg@1.2.3':\n    resolution: {}\n  plain@4.5.6:\n    resolution: {}\n"
    )
    pkgs = parse_lockfiles(tmp_path)
    names = {(p["name"], p["version"]) for p in pkgs}
    assert ("@scope/pkg", "1.2.3") in names
    assert ("plain", "4.5.6") in names


def test_dedup_across_lockfiles(tmp_path):
    (tmp_path / "Cargo.lock").write_text(
        'version = 3\n\n[[package]]\nname = "serde"\nversion = "1.0.0"\n'
    )
    (tmp_path / "package-lock.json").write_text(
        '{"packages": {"node_modules/lodash": {"version": "4.17.20"}}}'
    )
    pkgs = parse_lockfiles(tmp_path)
    assert len(pkgs) == len({(p["ecosystem"], p["name"], p["version"]) for p in pkgs})


def test_severity_prefers_database_specific():
    assert _severity({"database_specific": {"severity": "HIGH"}}) == "high"
    assert _severity({"severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N"}]}) is None


def test_fixed_version_extraction():
    v = {"affected": [{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.2.4"}]}]}]}
    assert _fixed(v) == "1.2.4"
    assert _fixed({"affected": []}) is None
