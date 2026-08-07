class DependencyContainer:
    def __init__(self):
        self._bindings = {}

    def bind(self, interface, implementation):
        self._bindings[interface] = implementation

    def get(self, interface):
        return self._bindings.get(interface)


container = DependencyContainer()


def configure(binder):  # noqa: F841
    """Konfigurácia závislostí."""
    pass
