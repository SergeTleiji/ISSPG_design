"""
PROJECT CONFIGURATION LOADER

Purpose:
    Load config/config.yaml and provide safe access to nested
    configuration values.

DESIGN
------
    - YAML is loaded once.
    - Missing/null values are allowed during development.
    - A stage calls require(...) when it actually needs a value.
    - Clear errors identify the exact missing configuration path.
    - No engineering calculations are performed here.

EXAMPLE
-------
    config = load_config()

    torque = config.require(
        "requirements.output_torque_nm"
    )

    ratio_min = config.require(
        "planetary.ratio.min"
    )

    modules = config.require_list(
        "planetary.search.modules_mm"
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# ============================================================
# EXCEPTION
# ============================================================

class ConfigError(ValueError):
    """Raised for invalid or missing project configuration."""


# ============================================================
# PROJECT CONFIG
# ============================================================

@dataclass(frozen=True)
class ProjectConfig:

    data: dict

    # ========================================================
    # GENERIC GET
    # ========================================================

    def get(
        self,
        path: str,
        default: Any = None,
    ) -> Any:
        """
        Read a dotted configuration path.

        Example:
            config.get("planetary.ratio.min")
        """

        if not path:
            raise ConfigError(
                "Configuration path cannot be empty."
            )

        current: Any = self.data

        for key in path.split("."):

            if not isinstance(
                current,
                dict,
            ):
                return default

            if key not in current:
                return default

            current = current[key]

        return current

    # ========================================================
    # REQUIRE VALUE
    # ========================================================

    def require(
        self,
        path: str,
    ) -> Any:
        """
        Require a non-null configuration value.
        """

        sentinel = object()

        value = self.get(
            path,
            sentinel,
        )

        if value is sentinel:

            raise ConfigError(
                f"Missing required configuration "
                f"'{path}'."
            )

        if value is None:

            raise ConfigError(
                f"Required configuration "
                f"'{path}' is null."
            )

        return value

    # ========================================================
    # REQUIRE SECTION
    # ========================================================

    def require_section(
        self,
        path: str,
    ) -> dict:

        value = self.require(
            path
        )

        if not isinstance(
            value,
            dict,
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"must be a mapping."
            )

        return value

    # ========================================================
    # REQUIRE NUMBER
    # ========================================================

    def require_number(
        self,
        path: str,
        *,
        positive: bool = False,
        nonnegative: bool = False,
    ) -> float:

        value = self.require(
            path
        )

        if isinstance(
            value,
            bool,
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"must be numeric."
            )

        try:

            result = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ConfigError(
                f"Configuration '{path}' "
                f"must be numeric."
            ) from exc

        if (
            positive
            and result <= 0
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"must be > 0."
            )

        if (
            nonnegative
            and result < 0
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"must be >= 0."
            )

        return result

    # ========================================================
    # REQUIRE INTEGER
    # ========================================================

    def require_int(
        self,
        path: str,
        *,
        positive: bool = False,
    ) -> int:

        value = self.require(
            path
        )

        if isinstance(
            value,
            bool,
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"must be an integer."
            )

        try:

            result = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ConfigError(
                f"Configuration '{path}' "
                f"must be an integer."
            ) from exc

        # Prevent 4.5 silently becoming 4.
        try:

            if float(value) != result:

                raise ConfigError(
                    f"Configuration '{path}' "
                    f"must be an integer."
                )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ConfigError(
                f"Configuration '{path}' "
                f"must be an integer."
            ) from exc

        if (
            positive
            and result <= 0
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"must be > 0."
            )

        return result

    # ========================================================
    # REQUIRE LIST
    # ========================================================

    def require_list(
        self,
        path: str,
        *,
        nonempty: bool = True,
    ) -> list:

        value = self.require(
            path
        )

        if not isinstance(
            value,
            list,
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"must be a list."
            )

        if (
            nonempty
            and len(value) == 0
        ):
            raise ConfigError(
                f"Configuration '{path}' "
                f"cannot be empty."
            )

        return value

    # ========================================================
    # HAS VALUE
    # ========================================================

    def has_value(
        self,
        path: str,
    ) -> bool:
        """
        True only if path exists AND is not null.
        """

        sentinel = object()

        value = self.get(
            path,
            sentinel,
        )

        return (
            value is not sentinel
            and value is not None
        )


# ============================================================
# LOAD CONFIG
# ============================================================

def load_config(
    path: str | Path = (
        "config/config.yaml"
    ),
) -> ProjectConfig:

    path = Path(
        path
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Configuration file not found: "
            f"{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        raw = yaml.safe_load(
            file
        )

    if raw is None:

        raise ConfigError(
            "Configuration file is empty."
        )

    if not isinstance(
        raw,
        dict,
    ):

        raise ConfigError(
            "Configuration root must be "
            "a mapping/dictionary."
        )

    return ProjectConfig(
        data=raw
    )