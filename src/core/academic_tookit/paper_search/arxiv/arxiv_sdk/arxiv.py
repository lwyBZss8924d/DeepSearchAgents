# Adapted from https://github.com/lukasschwab/arxiv.py/blob/master/arxiv/arxiv.py
# Original file was released under MIT License, with the full license text
# available at https://github.com/lukasschwab/arxiv.py/blob/master/LICENSE.txt
# Copyright (c) 2015 Lukas Schwab
# This modified file is released under the same license.
"""
This submodule is only an alias included for backwards compatibility. Its use is
deprecated as of 2.1.0.

Use `import arxiv`.
"""

from .__init__ import *  # noqa: F403
import warnings

warnings.warn("**Deprecated** after 2.1.0; use 'import arxiv' instead.")
