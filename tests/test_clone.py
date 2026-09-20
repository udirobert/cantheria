"""The clone step is argv, not a prompt — so it needs its own guard.

Every other attacker-facing string in this pipeline ends up inside an envelope
in front of a model. The repo URL goes into a subprocess. `git clone` executes
code it is given (`ext::sh -c '...'`), and anything starting with `-` is read as
an option rather than a remote, which is how a "just paste the URL" step becomes
remote code execution on the scanning box.

The hackathon's own guardrails are about not causing collateral damage. Getting
pwned through the argument we typed in ourselves would be the worst way to learn
that lesson.
"""

import pytest

from cantheria.scan import clone


@pytest.mark.parametrize(
    "hostile",
    [
        "ext::sh -c 'touch /tmp/cantheria_pwned'",
        "--upload-pack=touch /tmp/pwned",
        "-u;touch /tmp/pwned",
        "file:///etc",
        "local/tmp/x",
        "",
    ],
)
async def test_refuses_transports_that_execute(hostile: str, tmp_path):
    with pytest.raises(ValueError, match="only http"):
        await clone(hostile, tmp_path / "src")


async def test_local_checkout_is_used_directly(tmp_path):
    repo = tmp_path / "already-cloned"
    repo.mkdir()
    assert await clone(str(repo), tmp_path / "src") == repo.resolve()


@pytest.mark.parametrize(
    "ok",
    [
        "https://github.com/org/proj",
        "http://git.internal/org/proj.git",
        "git@github.com:org/proj.git",
        "ssh://git@host:2222/org/proj.git",
        "git://github.com/org/proj.git",
    ],
)
def test_conventional_remotes_pass_the_shape_check(ok: str):
    from cantheria.scan import _CLONE_URL

    assert _CLONE_URL.match(ok)
