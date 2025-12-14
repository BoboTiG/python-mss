# Lets prevent misses, and import the module to get the proper version.
# So that the version in only defined once across the whole code base:
#   src/mss/__init__.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import mss

# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
    "sphinx.ext.intersphinx",
    "sphinx_new_tab_link",
]
templates_path = ["_templates"]
source_suffix = {".rst": "restructuredtext"}
master_doc = "index"
new_tab_link_show_external_link_icon = True

# General information about the project.
project = "Python MSS"
copyright = f"{mss.__date__}, {mss.__author__} & contributors"  # noqa:A001
author = mss.__author__
version = mss.__version__

release = "latest"
language = "en"
todo_include_todos = True
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}


# -- Options for HTML output ----------------------------------------------

html_theme = "shibuya"
html_theme_options = {
    "accent_color": "lime",
    "globaltoc_expand_depth": 1,
    "toctree_titles_only": False,
}
html_favicon = "../icon.png"
html_context = {
    "source_type": "github",
    "source_user": "BoboTiG",
    "source_repo": "python-mss",
    "source_docs_path": "/docs/source/",
    "source_version": "main",
}
htmlhelp_basename = "PythonMSSdoc"


# -- Options for Epub output ----------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# A list of files that should not be packed into the epub file.
epub_exclude_files = ["search.html"]


# ----------------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
