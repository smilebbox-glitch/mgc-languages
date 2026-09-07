"""Infrastructure adapters selected by the runtime profile."""

# v6.3.6 future corporate PKI/e-sign adapter surface; disabled by default.

# v6.3.7 controlled outbound handover adapter.
from .handover import DisabledHandoverAdapter, GenericRestHandoverAdapter
