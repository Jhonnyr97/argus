import os
import sys

# Add the project's root directory to the system path
sys.path.insert(0, os.path.abspath('..'))

# -- Project Information -----------------------------------------------------

project = 'Argus'
copyright = '2024, Nilthon Jhon Rojas Apumayta'
author = 'Nilthon Jhon Rojas Apumayta'
release = '1.1'  # Version of the project

# -- General Configuration ---------------------------------------------------

# List of Sphinx extensions to be used
extensions = [
    'sphinx.ext.duration',                  # Measure build time
    'sphinx.ext.doctest',                   # Support for doctest
    'sphinx.ext.autodoc',                   # Automatically document from docstrings
    'sphinx.ext.autosummary',               # Generate summary tables
    'sphinx.ext.napoleon',                  # Support for Google and NumPy docstrings
    'sphinx_autodoc_typehints',             # Show type hints in documentation
    'sphinx.ext.viewcode',                  # Add links to the source code
    'sphinx.ext.intersphinx',               # Link to other project's documentation
]

# Paths that contain templates, relative to this directory
templates_path = ['_templates']

# Patterns to exclude from the documentation
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML Output -------------------------------------------------

# The theme to use for HTML and HTML Help pages
html_theme = 'sphinx_rtd_theme'  # Read the Docs theme

# Add any paths that contain custom static files (such as style sheets)
html_static_path = ['_static']

# Order members by the order they appear in the source code
autodoc_member_order = 'bysource'

# Enable automatic generation of summary tables
autosummary_generate = True

# Intersphinx mapping to link to other project's documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('https://requests.readthedocs.io/en/latest/', None),
    # Add more mappings as needed
}

# Napoleon settings to support Google and NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True
