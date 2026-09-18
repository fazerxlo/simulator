"""WIP Nav+ / RT6 Steering Column Stalk Event Dispatcher & State Machine.

Models discrete physical button inputs, debounce-free rotary encoder steps,
short/long press thresholds, and concurrent multi-button triggers (MUTE)
for Peugeot 407 CAN2004 comfort bus architecture.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


class StalkButton(Enum):
    """Discrete physical inputs on the Peugeot 407 steering column stalks."""
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    SRC_BUTTON = "src"
    SEEK_UP = "seek_up"
    SEEK_DOWN = "seek_down"
    TRIP_BUTTON = "trip"
    VOICE_NAV_REPEAT = "voice_nav_repeat"


class StalkEventType(Enum):
    """Event types emitted by the stalk state machine."""
    PRESS_DOWN = auto()
    RELEASE = auto()
    SHORT_PRESS = auto()
    LONG_PRESS = auto()
    CONCURRENT_PRESS = auto()
    ROTARY_SCROLL = auto()


@dataclass
class StalkEvent:
    """Discrete event emitted by the stalk event dispatcher."""
    event_type: StalkEventType
    button: Optional[StalkButton] = None
    duration_ms: float = 0.0
    payload: Any = None
    timestamp_ms: float = 0.0


class StalkStateMachine:
    """Deterministic event-driven state machine for steering column controls.

    Supports both real-time execution (using monotonic clock) and discrete simulation
    time steps (via ``step_time(delta_ms)``), making it fully testable and predictable.
    """

    # Physical timing thresholds (in milliseconds)
    SRC_LONG_PRESS_MS: float = 1000.0   # >= 1000ms: Call handling; < 1000ms: Source cycle
    TRIP_LONG_PRESS_MS: float = 2000.0  # >= 2000ms: Trip reset; < 2000ms: Screen switch

    # CAN 0x21F / 0x221 command masks
    CAN_21F_IDLE = 0x00
    CAN_21F_VOL_UP = 0x08
    CAN_21F_VOL_DOWN = 0x04
    CAN_21F_MUTE = 0x0C        # Simultaneous Vol+ & Vol- (or 0x02 SRC_MUTE)
    CAN_21F_SRC = 0x02
    CAN_21F_TEL_PICKUP = 0x01
    CAN_21F_TEL_HANGUP = 0x10
    CAN_21F_SEEK_UP = 0x80
    CAN_21F_SEEK_DOWN = 0x40

    # CAN 0x21F Byte 2 button state indicators
    STATE_RELEASED = 0x00
    STATE_PRESSED = 0x01
    STATE_LONG_PRESS = 0x02

    def __init__(self, initial_scroll: int = 0x09) -> None:
        self.listeners: List[Callable[[StalkEvent], None]] = []
        
        # State tracking
        self._current_time_ms: float = 0.0
        self._pressed_since_ms: Dict[StalkButton, float] = {}
        self._long_press_emitted: Set[StalkButton] = set()
        self._concurrent_mute_active: bool = False
        
        # Rotary scroll encoder state (0x00..0xFF modulo counter)
        self.scroll_counter: int = initial_scroll & 0xFF
        
        # Current CAN 0x21F command and button state
        self.can_21f_cmd: int = self.CAN_21F_IDLE
        self.can_21f_btn_state: int = self.STATE_RELEASED
        
        # Pulse window ticks for CAN encoder persistence
        self._pulse_window_ticks: int = 3
        self._active_pulse_ticks: int = 0
        
        # Stalk tip flags for CAN 0x221
        self.com_left: int = 0
        self.com_right: int = 0

    def add_listener(self, callback: Callable[[StalkEvent], None]) -> None:
        """Register an event listener callback."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback: Callable[[StalkEvent], None]) -> None:
        """Unregister an event listener callback."""
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _emit(self, event_type: StalkEventType, button: Optional[StalkButton] = None,
              duration_ms: float = 0.0, payload: Any = None) -> None:
        """Dispatch a StalkEvent to all registered listeners."""
        event = StalkEvent(
            event_type=event_type,
            button=button,
            duration_ms=duration_ms,
            payload=payload,
            timestamp_ms=self._current_time_ms,
        )
        for listener in self.listeners:
            listener(event)

    def get_time_ms(self) -> float:
        """Get current simulation time in milliseconds."""
        return self._current_time_ms

    def set_time_ms(self, time_ms: float) -> None:
        """Set absolute simulation time in milliseconds and check threshold expirations."""
        delta = max(0.0, time_ms - self._current_time_ms)
        self.step_time(delta)

    def step_time(self, delta_ms: float) -> None:
        """Advance time by delta_ms and trigger any pending long-press events."""
        self._current_time_ms += delta_ms
        self._check_long_presses()

    def _check_long_presses(self) -> None:
        """Check if any held buttons exceeded their long press thresholds."""
        for button, press_time in list(self._pressed_since_ms.items()):
            if button in self._long_press_emitted:
                continue
            held_duration = self._current_time_ms - press_time
            
            if button == StalkButton.SRC_BUTTON and held_duration >= self.SRC_LONG_PRESS_MS:
                self._long_press_emitted.add(button)
                self.can_21f_cmd = self.CAN_21F_TEL_PICKUP
                self.can_21f_btn_state = self.STATE_LONG_PRESS
                self._active_pulse_ticks = self._pulse_window_ticks
                self._emit(StalkEventType.LONG_PRESS, button=button, duration_ms=held_duration, payload="call_handling")
                
            elif button == StalkButton.TRIP_BUTTON and held_duration >= self.TRIP_LONG_PRESS_MS:
                self._long_press_emitted.add(button)
                self.com_right = 1
                self._emit(StalkEventType.LONG_PRESS, button=button, duration_ms=held_duration, payload="trip_reset")

    # ------------------------------------------------------------------
    # Physical Button Actions
    # ------------------------------------------------------------------

    def press_down(self, button: StalkButton, time_ms: Optional[float] = None) -> None:
        """Simulate physical button press down."""
        if time_ms is not None:
            self._current_time_ms = time_ms
            
        if button in self._pressed_since_ms:
            return  # Already held
            
        self._pressed_since_ms[button] = self._current_time_ms
        self._emit(StalkEventType.PRESS_DOWN, button=button)

        # Check for concurrent VOLUME_UP + VOLUME_DOWN -> MUTE
        if (button == StalkButton.VOLUME_UP and StalkButton.VOLUME_DOWN in self._pressed_since_ms) or \
           (button == StalkButton.VOLUME_DOWN and StalkButton.VOLUME_UP in self._pressed_since_ms):
            self._concurrent_mute_active = True
            self.can_21f_cmd = self.CAN_21F_MUTE
            self.can_21f_btn_state = self.STATE_PRESSED
            self._active_pulse_ticks = self._pulse_window_ticks
            self._emit(StalkEventType.CONCURRENT_PRESS, payload="mute")
            return

        # Single button press down actions
        if button == StalkButton.VOLUME_UP:
            self.can_21f_cmd = self.CAN_21F_VOL_UP
            self.can_21f_btn_state = self.STATE_PRESSED
            self._active_pulse_ticks = self._pulse_window_ticks
        elif button == StalkButton.VOLUME_DOWN:
            self.can_21f_cmd = self.CAN_21F_VOL_DOWN
            self.can_21f_btn_state = self.STATE_PRESSED
            self._active_pulse_ticks = self._pulse_window_ticks
        elif button == StalkButton.SRC_BUTTON:
            self.can_21f_cmd = self.CAN_21F_SRC
            self.can_21f_btn_state = self.STATE_PRESSED
            self._active_pulse_ticks = self._pulse_window_ticks
        elif button == StalkButton.SEEK_UP:
            self.can_21f_cmd = self.CAN_21F_SEEK_UP
            self.can_21f_btn_state = self.STATE_PRESSED
            self._active_pulse_ticks = self._pulse_window_ticks
            self._emit(StalkEventType.SHORT_PRESS, button=button, payload="seek_next")
        elif button == StalkButton.SEEK_DOWN:
            self.can_21f_cmd = self.CAN_21F_SEEK_DOWN
            self.can_21f_btn_state = self.STATE_PRESSED
            self._active_pulse_ticks = self._pulse_window_ticks
            self._emit(StalkEventType.SHORT_PRESS, button=button, payload="seek_prev")
        elif button == StalkButton.TRIP_BUTTON:
            self.com_right = 1
        elif button == StalkButton.VOICE_NAV_REPEAT:
            self.com_left = 1
            self._emit(StalkEventType.SHORT_PRESS, button=button, payload="voice_repeat")

    def release(self, button: StalkButton, time_ms: Optional[float] = None) -> None:
        """Simulate physical button release."""
        if time_ms is not None:
            self._current_time_ms = time_ms

        if button not in self._pressed_since_ms:
            return

        press_time = self._pressed_since_ms.pop(button)
        held_duration = self._current_time_ms - press_time
        was_long_pressed = button in self._long_press_emitted
        self._long_press_emitted.discard(button)

        self._emit(StalkEventType.RELEASE, button=button, duration_ms=held_duration)

        # Handle MUTE concurrent release
        if self._concurrent_mute_active:
            if StalkButton.VOLUME_UP not in self._pressed_since_ms and \
               StalkButton.VOLUME_DOWN not in self._pressed_since_ms:
                self._concurrent_mute_active = False
            return

        # Short press completion
        if not was_long_pressed:
            if button == StalkButton.VOLUME_UP:
                self._emit(StalkEventType.SHORT_PRESS, button=button, duration_ms=held_duration, payload="volume_up")
            elif button == StalkButton.VOLUME_DOWN:
                self._emit(StalkEventType.SHORT_PRESS, button=button, duration_ms=held_duration, payload="volume_down")
            elif button == StalkButton.SRC_BUTTON:
                self._emit(StalkEventType.SHORT_PRESS, button=button, duration_ms=held_duration, payload="cycle_source")
            elif button == StalkButton.TRIP_BUTTON:
                self._emit(StalkEventType.SHORT_PRESS, button=button, duration_ms=held_duration, payload="cycle_trip_screen")

        if button == StalkButton.TRIP_BUTTON:
            self.com_right = 0
        elif button == StalkButton.VOICE_NAV_REPEAT:
            self.com_left = 0

    # ------------------------------------------------------------------
    # Rotary Scroll Encoder
    # ------------------------------------------------------------------

    def rotary_scroll(self, direction: int, ticks: int = 1) -> None:
        """Emit discrete rotary scroll encoder ticks without debounce locking.

        direction: >0 for CW (up / next), <0 for CCW (down / prev).
        ticks: number of discrete detent steps.
        """
        step = 1 if direction > 0 else -1
        total_delta = step * ticks
        self.scroll_counter = (self.scroll_counter + total_delta) & 0xFF
        
        self._emit(
            StalkEventType.ROTARY_SCROLL,
            payload={"delta": total_delta, "counter": self.scroll_counter}
        )

    # ------------------------------------------------------------------
    # CAN Encoding Helpers
    # ------------------------------------------------------------------

    def get_can_21f_frame(self) -> List[int]:
        """Produce the 3-byte CAN 0x21F payload [cmd, scroll_counter, reserved]."""
        cmd = self.can_21f_cmd if self._active_pulse_ticks > 0 else self.CAN_21F_IDLE
        return [cmd, self.scroll_counter, 0x00]

    def step_can_pulses(self) -> None:
        """Step down active CAN transmission pulse counter."""
        if self._active_pulse_ticks > 0:
            self._active_pulse_ticks -= 1
            if self._active_pulse_ticks == 0:
                self.can_21f_cmd = self.CAN_21F_IDLE
                self.can_21f_btn_state = self.STATE_RELEASED
