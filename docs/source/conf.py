import datetime
import pathlib
import sys
from importlib.metadata import version as _version

path = pathlib.Path(__file__).parents[2] / "src"
sys.path.insert(0, path.resolve().as_posix())

project = "Probe Station"
author = "Sergey Ilyev"
copyright = f"{datetime.datetime.now().year}, {author}"
release = _version("probe-station")
rst_prolog = f"""
.. |name| replace:: {project}
"""

extensions = [
    "sphinx.ext.autodoc",  # generate documentation from docstrings
    "sphinx.ext.intersphinx",  # link to other projects' documentation
    "sphinx.ext.doctest",  # test snippets in the documentation
    "sphinx.ext.autosummary",  # create summaries for modules
    "sphinx.ext.viewcode",  # add links to source code
    "sphinx_copybutton",  # add copy buttons to code blocks
    "sphinx_autodoc_typehints",  #  move typehints to descriptions
    "sphinx_design",  # add tab elements
    "sphinx_codeautolink",  # add intersphinx links in code blocks
    # "nbsphinx",
]

# keysight_b1530a is installed for real on the docs builder (via the
# "measurements" extra) so autodoc sees real enums and docstrings, but its
# _ffi module dlopens the WGFMU DLL at import time, which only works on
# Windows with the instrument library present. Mock just that module; the
# rest of the package imports cleanly without it.
autodoc_mock_imports = [
    "keysight_b1530a._ffi",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("http://docs.scipy.org/doc/numpy/", None),
    "scipy": ("http://docs.scipy.org/doc/scipy/reference/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "pandas": ("http://pandas.pydata.org/pandas-docs/stable/", None),
}

copybutton_exclude = ".linenos, .gp"  # to exclude prompts ($, >>>, etc.) from copied code
copybutton_prompt_text = " "  # to remove space in (.venv) $

typehints_use_rtype = False
typehints_defaults = "comma"

templates_path = ["_templates"]
exclude_patterns = []

default_role = "any"
trim_footnote_reference_space = True
html_favicon = "https://estore.oxinst.com/INTERSHOP/static/WFS/Oxinst-US-Site/-/Oxinst/en_US/Category%20Images/Modes%20icons/piezoresponse-force-microscopy-pfm-afm-mode-icon-300x300.png"
html_last_updated_fmt = ""
html_show_sphinx = False
todo_include_todos = False

html_theme = "furo"
