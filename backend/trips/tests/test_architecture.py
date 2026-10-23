"""
The dependency rule, enforced: imports point inward only.

    interfaces -> application -> domain      infrastructure -> application -> domain

Nothing in domain/ or application/ may import a framework or an HTTP library,
and no layer may import one that sits outside it.
"""
import ast
from pathlib import Path

from django.test import SimpleTestCase

TRIPS = Path(__file__).resolve().parent.parent
FRAMEWORKS = {"django", "rest_framework", "httpx", "requests"}

# layer -> the trips packages it may import from
ALLOWED = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "application", "infrastructure", "models"},
    "interfaces": {"domain", "application", "interfaces", "container"},
}
PURE_LAYERS = {"domain", "application"}


def imports_of(path: Path) -> list[str]:
    """Absolute module names imported by a file, with relative imports resolved against trips."""
    package = ".".join(("trips", *path.relative_to(TRIPS).parent.parts))
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                found.append(".".join([*base, *(node.module.split(".") if node.module else [])]))
            elif node.module:
                found.append(node.module)
    return found


class DependencyRuleTests(SimpleTestCase):
    def test_pure_layers_import_no_framework(self):
        for layer in PURE_LAYERS:
            for path in (TRIPS / layer).rglob("*.py"):
                for module in imports_of(path):
                    with self.subTest(file=str(path.relative_to(TRIPS)), imports=module):
                        self.assertNotIn(module.split(".")[0], FRAMEWORKS)

    def test_layers_only_import_inward(self):
        for layer, allowed in ALLOWED.items():
            for path in (TRIPS / layer).rglob("*.py"):
                for module in imports_of(path):
                    parts = module.split(".")
                    if parts[0] != "trips" or len(parts) < 2:
                        continue
                    with self.subTest(file=str(path.relative_to(TRIPS)), imports=module):
                        self.assertIn(parts[1], allowed)
