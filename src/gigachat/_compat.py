import warnings
from typing import Any, Dict


def warn_deprecated_symbol(old: str, new: str, *, stacklevel: int = 2) -> None:
    warnings.warn(
        f"'{old}' is deprecated and will be removed in a future release; use '{new}' instead.",
        DeprecationWarning,
        stacklevel=stacklevel,
    )


def resolve_deprecated(name: str, mapping: Dict[str, Any], *, module_name: str) -> Any:
    try:
        target = mapping[name]
    except KeyError as exc:
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}") from exc

    warn_deprecated_symbol(f"{module_name}.{name}", f"gigachat.{name}", stacklevel=3)
    return target
