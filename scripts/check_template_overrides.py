"""Check that every template override in templates/ still resolves under the
installed InvenioRDM.

An override is a full-file copy of an upstream template. When RDM is upgraded
upstream renames, moves or deletes the templates a copy includes, extends or
imports, and the copy then fails at render time with TemplateNotFound (the
record landing page returned 500 on v14 because of this).

This script parses each override with the application's own Jinja environment,
finds every template it references, and asks the application's loader to
resolve each one. Nothing is rendered, so no data is needed. It exits 0 when
every reference resolves, 1 when some do not (the unresolved references are
printed), 66 when the templates directory is missing.

USAGE (inside the instance, from the repository root):

    uv run --no-sync python scripts/check_template_overrides.py [TEMPLATES_DIR]

TEMPLATES_DIR defaults to ./templates.
"""

import sys
from pathlib import Path

from jinja2 import meta
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError


def references(env, source):
    """Return the template names that source includes, extends or imports.

    Names built from a variable (a dynamic include) come back as None and are
    skipped by the caller; they cannot be checked without rendering.
    """
    return [n for n in meta.find_referenced_templates(env.parse(source)) if n]


def check(env, templates_dir):
    """Return (checked, problems) for every override under templates_dir.

    Each problem is (override path, referenced name, reason).
    """
    problems = []
    files = sorted(p for p in templates_dir.rglob("*") if p.is_file() and p.name != ".gitkeep")
    for path in files:
        if path.suffix not in (".html", ".txt", ".jinja", ".j2"):
            continue
        rel = path.relative_to(templates_dir).as_posix()
        try:
            names = references(env, path.read_text())
        except TemplateSyntaxError as err:
            problems.append((rel, "(syntax)", f"line {err.lineno}: {err.message}"))
            continue
        for name in names:
            try:
                env.loader.get_source(env, name)
            except TemplateNotFound:
                problems.append((rel, name, "not found"))
    return len(files), problems


def main(argv):
    templates_dir = Path(argv[1] if len(argv) > 1 else "templates")
    if not templates_dir.is_dir():
        print(f"no such directory: {templates_dir}", file=sys.stderr)
        return 66
    from invenio_app.factory import create_app

    app = create_app()
    with app.app_context():
        checked, problems = check(app.jinja_env, templates_dir)
    for rel, name, reason in problems:
        print(f"FAIL {rel}: {name} ({reason})")
    print(f"{checked} override files checked, {len(problems)} unresolved references")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
