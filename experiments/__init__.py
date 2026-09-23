"""Reusable experiments for mutation and scaling studies.

Public APIs live in :mod:`experiments.mutations` and
:mod:`experiments.scaling`.  Keeping package initialisation side-effect free
also permits either module to be executed directly with ``python -m``.
"""

__all__ = ["mutations", "scaling"]
