from .config import run_config

# Explicit list of extensions to be included in an export of the XUI by default
# only .py and .html are exported
ALLOWED_XUI_EXTENSIONS = [".py", ".pyc", ".html", ".png", ".js", ".json", ".md",
                          ".*"]

__version__ = "0.1"

# run_config(__version__)

