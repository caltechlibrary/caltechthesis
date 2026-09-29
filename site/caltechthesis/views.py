"""Additional views."""

from flask import Blueprint
from invenio_pages.views import create_page_view

#
# Static pages
#
# /help, /policies and friends are rows in invenio-pages' pages_page table,
# loaded from app_data/pages.yaml and app_data/pages/*.html by the fixtures
# step of setup.
#
# invenio-pages registers those URLs lazily, out of its own 404 handler, and
# that hook does not survive startup: invenio-theme's init_app runs later and
# replaces the app's 404 handler outright, so invenio-pages never gets a
# chance to look a page up. Every static page then 404s with the row present
# and intact. Registering the rules explicitly sidesteps the ordering
# question. See caltechauthors DR-0008 for the diagnosis, verified live there.
#
# Keep this tuple in step with app_data/pages.yaml. A URL listed here with no
# matching row 404s from render_page, and a row whose URL is not listed stays
# unreachable.
#
# /help/statistics is deliberately not listed. RDM owns that URL through its
# own route; listing it here would shadow a working route with a 404.
STATIC_PAGE_URLS = (
    "/about",
    "/help",
    "/metadata_searching",
    "/policies",
    "/year",
)


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""
    blueprint = Blueprint(
        "caltechthesis",
        __name__,
        template_folder="./templates",
    )

    # Add URL rules
    for url in STATIC_PAGE_URLS:
        # create_page_view() names every view it returns "_view", so each rule
        # needs its own explicit endpoint -- left to Flask's default they would
        # all derive the same one and the second registration would raise.
        blueprint.add_url_rule(
            url,
            endpoint="static_page{}".format(url.replace("/", "_")),
            view_func=create_page_view(url),
        )

    return blueprint
