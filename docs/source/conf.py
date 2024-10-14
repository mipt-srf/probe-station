import pathlib
import sys

sys.path.insert(0, pathlib.Path(__file__).parents[2].resolve().as_posix())

project = "probe-station"
copyright = "2024, Sergey"
author = "Sergey"
release = "0.5"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",
    "sphinx_rtd_theme",
    "sphinx_copybutton",
    "sphinx.ext.todo",
    "nbsphinx",
]

# typehints_use_signature = True
typehints_defaults = "comma"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("http://docs.scipy.org/doc/numpy/", None),
    "scipy": ("http://docs.scipy.org/doc/scipy/reference/", None),
    "matplotlib": ("http://matplotlib.sourceforge.net/", None),
}

templates_path = ["_templates"]
exclude_patterns = []

default_role = "any"
trim_footnote_reference_space = True
html_favicon = "https://estore.oxinst.com/INTERSHOP/static/WFS/Oxinst-US-Site/-/Oxinst/en_US/Category%20Images/Modes%20icons/piezoresponse-force-microscopy-pfm-afm-mode-icon-300x300.png"
html_last_updated_fmt = ""
html_show_sphinx = False
todo_include_todos = False

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
