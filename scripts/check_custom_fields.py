"""Check the thesis custom fields and the degree date against the running
configuration (caltechthesis DR-0002, plan Phase 2.3).

It reads the application's own configuration and schemas. It writes nothing:
no draft, record or index is created, so it is safe on any instance. It checks
that

  * caltech:option_major, caltech:option_minor and caltech:division are
    list-valued vocabulary custom fields;
  * caltech:embargo_until is an ISO date custom field that accepts a full date
    and rejects a year alone and free text;
  * each of the four appears in a deposit-form section;
  * a metadata date typed degree_date is accepted by the date schema as a
    year alone and as a full date, and rejected when it is not a date.

What it cannot check is that RDM accepts the role and date type ids on a real
draft, because that needs a database write; the draft round-trip is plan 2.5.

It exits 0 when every check passes, 1 when some fail (each failure is printed
as a FAIL line).

USAGE (inside the instance, from the repository root):

    uv run --no-sync python scripts/check_custom_fields.py
"""

import sys

VOCABULARY_FIELDS = ("caltech:option_major", "caltech:option_minor", "caltech:division")
DATE_FIELD = "caltech:embargo_until"


def ui_field_names(sections):
    """Return the set of field names that the deposit-form sections carry."""
    names = set()
    for section in sections:
        for field in section.get("fields", []):
            names.add(field.get("field"))
    return names


def check_fields(custom_fields, ui_sections):
    """Return a list of problem strings for the four caltech: custom fields."""
    problems = []
    by_name = {cf.name: cf for cf in custom_fields}
    shown = ui_field_names(ui_sections)
    for name in VOCABULARY_FIELDS + (DATE_FIELD,):
        if name not in by_name:
            problems.append(f"{name}: no custom field is defined")
        if name not in shown:
            problems.append(f"{name}: not in a deposit-form section")
    for name in VOCABULARY_FIELDS:
        cf = by_name.get(name)
        if cf is not None and type(cf).__name__ != "VocabularyCF":
            problems.append(f"{name}: is {type(cf).__name__}, not a VocabularyCF")
        elif cf is not None and not getattr(cf, "multiple", False):
            problems.append(f"{name}: is not list-valued (multiple=True)")
    cf = by_name.get(DATE_FIELD)
    if cf is not None:
        if type(cf).__name__ != "ISODateStringCF":
            problems.append(f"{DATE_FIELD}: is {type(cf).__name__}, not an ISODateStringCF")
        else:
            problems.extend(check_embargo_validation(cf))
    return problems


def load_error(field, value):
    """Return the validation errors of loading value into a marshmallow field."""
    from marshmallow import Schema, ValidationError

    schema = Schema.from_dict({"v": field})()
    try:
        schema.load({"v": value})
    except ValidationError as err:
        return err.messages
    return None


def check_embargo_validation(cf):
    """Return problems with how caltech:embargo_until validates its value."""
    problems = []
    if load_error(cf.field, "2027-06-01") is not None:
        problems.append(f"{DATE_FIELD}: rejects the full date 2027-06-01")
    for bad in ("2027", "June 2027", "not a date"):
        if load_error(cf.field, bad) is None:
            problems.append(f"{DATE_FIELD}: accepts {bad!r}")
    return problems


def check_degree_date():
    """Return problems with how a degree_date metadata date validates."""
    from invenio_rdm_records.services.schemas.metadata import DateSchema

    problems = []
    for value in ("2024", "2024-06-14"):
        try:
            DateSchema().load({"date": value, "type": {"id": "degree_date"}})
        except Exception as err:  # marshmallow.ValidationError and friends
            problems.append(f"degree_date: rejects {value!r} ({err})")
    try:
        DateSchema().load({"date": "not a date", "type": {"id": "degree_date"}})
        problems.append("degree_date: accepts 'not a date'")
    except Exception:
        pass
    return problems


def main():
    from invenio_app.factory import create_app

    app = create_app()
    with app.app_context():
        problems = check_fields(
            app.config["RDM_CUSTOM_FIELDS"], app.config["RDM_CUSTOM_FIELDS_UI"]
        )
        problems.extend(check_degree_date())
    for problem in problems:
        print(f"FAIL {problem}")
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
