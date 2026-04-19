"""Auto-generated package — re-exports all CAN message classes.

Provides ``ALL_MESSAGES``, ``CanMessage``, ``STARTUP_WAKEUP_BURST``
and every ``MsgXXX`` class so that existing import patterns keep working.
"""

from generated.base import CanMessage  # noqa: F401

from generated.bsi_messages import Msg036, Msg0B6, Msg0F6, Msg110, Msg128, Msg161, Msg168, Msg190, Msg1A1, Msg1A8, Msg217, Msg220, Msg2B6, Msg336, Msg3B6, Msg52D, STARTUP_WAKEUP_BURST  # noqa: F401
from generated.bte_messages import Msg12B  # noqa: F401
from generated.clim_messages import Msg12D, Msg1D0, Msg1E3  # noqa: F401
from generated.kml_messages import Msg1A3, Msg223, Msg323  # noqa: F401
from generated.parktronic_messages import Msg0E1  # noqa: F401
from generated.radio_messages import Msg0A4, Msg165, Msg1A5, Msg1E0, Msg1E5, Msg225, Msg265, Msg2A5, Msg3E5  # noqa: F401
from generated.trip_messages import Msg221, Msg2A1, Msg261  # noqa: F401


#: Maps CAN arbitration IDs to their :class:`CanMessage` subclass.
ALL_MESSAGES: dict[int, type] = {
    cls.can_id: cls
    for cls in (
        Msg036, Msg0B6, Msg0F6, Msg110, Msg128, Msg161,
        Msg168, Msg190, Msg1A1, Msg1A8, Msg217, Msg220,
        Msg2B6, Msg336, Msg3B6, Msg52D, Msg12B, Msg12D,
        Msg1D0, Msg1E3, Msg1A3, Msg223, Msg323, Msg0E1,
        Msg0A4, Msg165, Msg1A5, Msg1E0, Msg1E5, Msg225,
        Msg265, Msg2A5, Msg3E5, Msg221, Msg2A1, Msg261,
    )
}
