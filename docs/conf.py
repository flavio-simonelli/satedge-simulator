"""Configurazione di Sphinx per la documentazione di satedge-simulator."""

from importlib.metadata import version as _version

project = "satedge-simulator"
author = "Flavio Simonelli"
copyright = "2026, Flavio Simonelli"
release = _version("satedge-simulator")
version = release
language = "it"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxcontrib.mermaid",
]

# --- sorgenti ------------------------------------------------------------------------------
source_suffix = {".md": "markdown"}
exclude_patterns = ["_build"]
myst_enable_extensions = ["colon_fence", "deflist", "dollarmath"]
myst_heading_anchors = 3
myst_fence_as_directive = ["mermaid"]

# --- API dal codice: docstring in stile Google ----------------------------------------------
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"
autodoc_default_options = {"members": True, "show-inheritance": True}
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_attr_annotations = True

# --- aspetto -------------------------------------------------------------------------------
html_theme = "furo"
html_title = f"satedge-simulator {release}"
html_static_path: list[str] = []
