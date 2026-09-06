"""A ``filetree`` directive rendering a source tree with links to the files.

The tree is walked at build time, so it never drifts from the actual layout.
File and directory names become links to the repository browser, built from
``filetree_base_url`` in :file:`conf.py`.

Only git-tracked files are listed: untracked scratch files and generated ones
(``_version.py``, ``__pycache__``) would otherwise produce dead links. When git
is unavailable -- building from an sdist, say -- the directive falls back to
walking the filesystem and filtering with ``exclude`` patterns.
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.application import Sphinx

#: Patterns dropped from the filesystem fallback; git already ignores these.
DEFAULT_EXCLUDE = ("__pycache__", "*.pyc", ".*")

TEE = "├── "  # box-drawing characters are the point
ELBOW = "└── "
PIPE = "│   "
BLANK = "    "


class _Tree(dict):
    """Nested mapping of name -> _Tree; an empty one is a file."""


def _insert(tree: _Tree, parts: Iterable[str]) -> None:
    for part in parts:
        tree = tree.setdefault(part, _Tree())


def _tracked_paths(root: Path, target: Path) -> list[PurePosixPath] | None:
    """Return target-relative paths of git-tracked files, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", str(target)],  # git resolved from PATH by design
            cwd=root,
            capture_output=True,
            check=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    paths = [PurePosixPath(line) for line in result.stdout.split("\0") if line]
    rel_target = PurePosixPath(target.relative_to(root).as_posix())
    return [path.relative_to(rel_target) for path in paths]


def _walked_paths(target: Path, exclude: tuple[str, ...]) -> list[PurePosixPath]:
    def excluded(name: str) -> bool:
        return any(fnmatch.fnmatch(name, pattern) for pattern in exclude)

    paths = []
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(target)
        if any(excluded(part) for part in relative.parts):
            continue
        paths.append(PurePosixPath(relative.as_posix()))
    return paths


def _render(  # a plain recursive walk, each argument is one axis of it
    tree: _Tree,
    prefix: str,
    url_prefix: PurePosixPath,
    url_template: str,
    depth: int,
    max_depth: int,
) -> list[nodes.line]:
    lines = []
    # Directories first, then files, each alphabetically -- mirrors how the
    # package reads in an editor sidebar.
    entries = sorted(tree.items(), key=lambda item: (not item[1], item[0].lower()))
    for index, (name, subtree) in enumerate(entries):
        last = index == len(entries) - 1
        is_dir = bool(subtree)
        path = url_prefix / name

        line = nodes.line()
        line += nodes.Text(prefix + (ELBOW if last else TEE))
        line += _link(name + ("/" if is_dir else ""), path, url_template, is_dir=is_dir)
        lines.append(line)

        if is_dir and (max_depth < 0 or depth + 1 < max_depth):
            lines += _render(
                subtree,
                prefix + (BLANK if last else PIPE),
                path,
                url_template,
                depth + 1,
                max_depth,
            )
    return lines


def _link(label: str, path: PurePosixPath, url_template: str, *, is_dir: bool) -> nodes.Node:
    """Link a tree entry to the repository browser, or leave it plain text."""
    if not url_template:
        return nodes.Text(label)
    # GitHub-style URLs: <repo>/blob/<ref>/<path> for files, /tree/<ref>/<path> for directories.
    return nodes.reference("", label, refuri=url_template.format(kind="tree" if is_dir else "blob", path=path))


class FileTreeDirective(SphinxDirective):
    """Render the tree under a repository-relative path.

    .. code-block:: rst

       .. filetree:: src/probe_station
          :max-depth: 2
    """

    required_arguments = 1
    option_spec = {  # noqa: RUF012 - docutils expects a plain class attribute
        "max-depth": directives.nonnegative_int,
        "exclude": directives.unchanged,
        "caption": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        root = Path(self.env.config.filetree_root or self.env.app.confdir).resolve()
        target = (root / self.arguments[0]).resolve()
        if not target.is_dir():
            message = f"filetree: {target} is not a directory"
            raise self.error(message)

        exclude = tuple(self.options.get("exclude", "").split()) or DEFAULT_EXCLUDE
        paths = _tracked_paths(root, target)
        if paths is None:
            paths = _walked_paths(target, exclude)

        # Rebuild the page when the tree changes. File mtimes cover edits;
        # directory mtimes cover additions and removals.
        self.env.note_dependency(str(target))
        for path in paths:
            self.env.note_dependency(str(target / path))
            for parent in (target / path).parents:
                if parent == target:
                    break
                self.env.note_dependency(str(parent))

        tree = _Tree()
        for path in paths:
            _insert(tree, path.parts)

        base_url = self.env.config.filetree_base_url.rstrip("/")
        # "" disables linking; entries then render as plain text.
        url_template = f"{base_url}/{{kind}}/{self.env.config.filetree_ref}/{{path}}" if base_url else ""
        url_root = PurePosixPath(target.relative_to(root).as_posix())
        max_depth = self.options.get("max-depth", -1)

        block = nodes.line_block(classes=["filetree"])
        root_line = nodes.line()
        root_line += _link(self.options.get("caption", target.name) + "/", url_root, url_template, is_dir=True)
        block += root_line
        block += _render(tree, "", url_root, url_template, 0, max_depth)
        return [block]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value("filetree_root", None, "env", types=(str, type(None)))
    app.add_config_value("filetree_base_url", "", "env", types=(str,))
    app.add_config_value("filetree_ref", "master", "env", types=(str,))
    app.add_directive("filetree", FileTreeDirective)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
