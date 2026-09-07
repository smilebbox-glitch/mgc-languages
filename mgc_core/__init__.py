"""Modular runtime boundary for MGC Languages.

The package is intentionally small in v5.7.3. It provides a stable deployment
entrypoint and runtime contracts while the legacy monolith is decomposed in
subsequent increments.
"""

from .contracts import CRITICAL_ROUTE_CONTRACT, RuntimeContractError, route_inventory, validate_route_contract

__all__ = [
    "CRITICAL_ROUTE_CONTRACT",
    "RuntimeContractError",
    "route_inventory",
    "validate_route_contract",
]
