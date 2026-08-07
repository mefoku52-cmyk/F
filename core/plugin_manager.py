import importlib
import logging
import pkgutil
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from core.collector import FileInfo

logger = logging.getLogger("forensicsuite.plugin_manager")


class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    def version(self) -> str:
        return "1.0.0"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        return True

    @abstractmethod
    def analyze(self, project_path: str, files: List[FileInfo]) -> Dict[str, Any]:
        raise NotImplementedError


def discover_plugins(plugins_package: str = "plugins") -> List[Plugin]:
    plugins: List[Plugin] = []
    try:
        package = importlib.import_module(plugins_package)
    except ModuleNotFoundError:
        logger.warning("Balíček pluginov '%s' sa nenašiel", plugins_package)
        return plugins

    for _, subpackage_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if not is_pkg:
            continue
        module_name = f"{plugins_package}.{subpackage_name}.plugin"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            logger.warning("Plugin modul '%s' neexistuje, preskakujem", module_name)
            continue
        except Exception as e:
            logger.error("Chyba pri importovaní pluginu '%s': %s", module_name, e)
            continue

        found_plugin = False
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Plugin)
                and attr is not Plugin
            ):
                try:
                    plugins.append(attr())
                    found_plugin = True
                except Exception as e:
                    logger.error(
                        "Nepodarilo sa vytvoriť inštanciu '%s': %s", attr_name, e
                    )
        if not found_plugin:
            logger.warning(
                "Modul '%s' neobsahuje žiadnu triedu implementujúcu Plugin", module_name
            )

    return plugins
