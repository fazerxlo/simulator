"""CanMessage base class for the Peugeot 407 CAN2004 simulator.

Auto-generated — do not edit by hand.
"""

from __future__ import annotations


class CanMessage:
    """Base class for a periodic CAN message.

    Subclasses **must** set ``can_id`` and ``period_ms`` as class attributes
    and override ``encode``.  Overriding ``decode`` is optional but strongly
    recommended so that monitor mode and loopback testing work correctly.

    ``required_modules`` may be set to one or more config-module names.
    When non-empty, the runner only transmits this message while at least
    one of those modules is enabled in ``config.yml``.
    """

    #: CAN arbitration ID owned by this object.
    can_id: int = 0

    #: Transmit period in milliseconds.
    period_ms: int = 100

    #: Config-module names that must be enabled for this message to transmit.
    required_modules: frozenset[str] = frozenset()

    #: When True the runner only calls decode() on this message and never
    #: calls encode() / transmits it.  Set on CAN IDs that are owned by an
    #: external node (e.g. the real workbench radio) so the simulator only
    #: monitors and displays the traffic without injecting its own frames.
    listen_only: bool = False

    def get_period_ms(self, car) -> int:
        """Return the active transmit period for the current car state."""
        return self.period_ms

    def encode(self, car) -> list | None:
        """Build frame byte payload from car state.

        Return ``None`` to skip transmission this cycle.
        """
        return None

    def decode(self, car, data: bytes) -> None:
        """Update car state from a received frame with this *can_id*."""

    def __repr__(self) -> str:
        return f'{type(self).__name__}(can_id=0x{self.can_id:03X}, period_ms={self.period_ms})'
