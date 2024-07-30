# Lets prevent misses, and import the module to get the proper version.
# So that the version in only defined once across the whole code base:
#   src/mss/__init__.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import mss

# -- General configuration ------------------------------------------------

extensions = ["sphinx.ext.intersphinx"]
templates_path = ["_templates"]
source_suffix = {".rst": "restructuredtext"}
master_doc = "index"

# General information about the project.
project = "Python MSS"
copyright = f"{mss.__date__}, {mss.__author__} & contributors"  # noqa:A001
author = mss.__author__
version = mss.__version__

release = "latest"
language = "en"
todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

html_theme = "default"
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
