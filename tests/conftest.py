"""
pytest configuration for the simulator test suite.

Mocks Kivy modules at collection time so that tests can import simulator
modules (e.g. ``modules/clim``) without a running Kivy environment.  Only
the minimal surface needed by the modules under test is stubbed out.
"""
import sys
import types


def _make_kivy_stubs():
    """Return a dict of {module_name: stub_module} for kivy subsystems."""

    stubs = {}

    def _mod(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        return m

    # kivy.clock — only Clock.schedule_once / schedule_interval are used.
    class _Clock:
        @staticmethod
        def schedule_once(callback, delay=0):
            return None

        @staticmethod
        def schedule_interval(callback, interval):
            return None

        @staticmethod
        def unschedule(event):
            pass

    stubs['kivy'] = _mod('kivy')
    stubs['kivy.clock'] = _mod('kivy.clock', Clock=_Clock)

    # kivy.uix.tabbedpanel
    class _TabbedPanelItem:
        def __init__(self, **kwargs):
            self.ids = {}
            self.text = ''

    stubs['kivy.uix'] = _mod('kivy.uix')
    stubs['kivy.uix.tabbedpanel'] = _mod(
        'kivy.uix.tabbedpanel', TabbedPanelItem=_TabbedPanelItem
    )

    # kivy.app
    class _App:
        def __init__(self, **kwargs):
            pass

    stubs['kivy.app'] = _mod('kivy.app', App=_App)

    # kivy.lang.builder
    class _Builder:
        @staticmethod
        def load_file(path):
            return None

        @staticmethod
        def apply(widget, *args, **kwargs):
            pass

    stubs['kivy.lang'] = _mod('kivy.lang')
    stubs['kivy.lang.builder'] = _mod('kivy.lang.builder', Builder=_Builder)

    # kivy.properties — provide common property descriptors as plain values
    stubs['kivy.properties'] = _mod('kivy.properties')

    return stubs


# Install stubs before any test module is imported.
for _name, _stub in _make_kivy_stubs().items():
    sys.modules.setdefault(_name, _stub)


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

def make_can_mock():
    """Return a minimal 'can' module stub so CanRunner can be imported."""
    can_mock = types.ModuleType('can')

    class MockBus:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def recv(self, timeout):
            return None
        def send(self, msg):
            pass

    class MockMessage:
        def __init__(self, **kwargs):
            self.arbitration_id = kwargs.get('arbitration_id', 0)
            self.data = kwargs.get('data', [])
            self.is_extended_id = kwargs.get('is_extended_id', False)

    can_mock.Bus = MockBus
    can_mock.Message = MockMessage
    return can_mock


class DummyWidget:
    """Lightweight widget stub for UI tests."""
    def __init__(self, state='normal', value=0, text=''):
        self.state = state
        self.value = value
        self.text = text
