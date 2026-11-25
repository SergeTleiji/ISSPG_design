#!/usr/bin/env python3
"""
Rank feasible ISSPG candidates by analytical packaging size.

Inputs:
    output/feasible_candidates.csv
    data/motors.yaml

Output:
    output/ranked_candidates_packaging.csv

Primary metric:
    Cylindrical bounding-envelope volume
        V = pi/4 * D_pkg^2 * L_pkg

where
    D_pkg = max(motor OD, ring OD, carrier OD)

and the current analytical axial proxy is
    L_pkg = motor axial length
            + rotor drive plate thickness
            + gear face width (b)
            + carrier thickness
            + output-bearing span

This is a relative packaging proxy, not an exact CAD bounding box.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable

import yaml


DEFAULT_INPUT = Path("output/feasible_candidates.csv")
DEFAULT_MOTORS = Path("data/motors.yaml")
DEFAULT_OUTPUT = Path("output/ranked_candidates_packaging.csv")


def _norm(text: str) -> str:
    return str(text).strip().lower().replace("-", "_").replace(" ", "_")


def _to_float(value, *, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not convert {name}={value!r} to float.") from exc


def _find_column(
    fieldnames: Iterable[str],
    *,
    aliases: Iterable[str] = (),
    token_groups: Iterable[Iterable[str]] = (),
    required: bool = True,
) -> str | None:
    fieldnames = list(fieldnames)
    normalized = {_norm(name): name for name in fieldnames}

    for alias in aliases:
        key = _norm(alias)
        if key in normalized:
            return normalized[key]

    for group in token_groups:
        tokens = [_norm(token) for token in group]
        matches = [
            original
            for original in fieldnames
            if all(token in _norm(original) for token in tokens)
        ]
        if len(matches) == 1:
            return matches[0]

    if required:
        raise KeyError(
            "Could not resolve required CSV column.\n"
            f"Aliases tried: {list(aliases)}\n"
            f"Token groups tried: {list(token_groups)}"
        )
    return None


def _first_yaml_value(mapping: dict, aliases: Iterable[str]):
    normalized = {_norm(k): v for k, v in mapping.items()}
    for alias in aliases:
        key = _norm(alias)
        if key in normalized:
            return normalized[key]
    raise KeyError(f"Could not find any of {list(aliases)} in motor entry.")


def load_motor_dimensions(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        raise FileNotFoundError(f"Motor catalogue not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError("Motor YAML root must be a mapping.")

    motor_map = raw.get("motors", raw)
    if not isinstance(motor_map, dict):
        raise ValueError("Could not locate motor mapping in motors.yaml.")

    result = {}
    for key, entry in motor_map.items():
        if not isinstance(entry, dict):
            continue

        od = _to_float(
            _first_yaml_value(entry, ("outer_diameter_mm", "outer_diameter", "od_mm")),
            name=f"{key}.outer_diameter_mm",
        )
        length = _to_float(
            _first_yaml_value(entry, ("axial_length_mm", "axial_length", "length_mm")),
            name=f"{key}.axial_length_mm",
        )

        result[str(key)] = {
            "outer_diameter_mm": od,
            "axial_length_mm": length,
        }

    if not result:
        raise ValueError("No valid motor entries were found in motors.yaml.")

    return result


def resolve_columns(fieldnames: list[str]) -> dict[str, str | None]:
    return {
        "candidate_id": _find_column(fieldnames, aliases=("candidate_id",)),
        "motor_key": _find_column(fieldnames, aliases=("seed_motor_key", "motor_key")),
        "z_s": _find_column(fieldnames, aliases=("seed_z_s", "planetary_z_s", "z_s"), required=False),
        "z_p": _find_column(fieldnames, aliases=("seed_z_p", "planetary_z_p", "z_p"), required=False),
        "z_r": _find_column(
            fieldnames,
            aliases=("planetary_z_r", "z_r"),
            token_groups=(("planetary", "z_r"),),
            required=False,
        ),
        "n_planets": _find_column(fieldnames, aliases=("seed_n_planets", "n_planets"), required=False),
        "module_mm": _find_column(fieldnames, aliases=("seed_module_mm", "module_mm"), required=False),
        "face_width_mm": _find_column(fieldnames, aliases=("seed_face_width_mm", "face_width_mm")),
        "ratio": _find_column(
            fieldnames,
            aliases=("planetary_ratio", "ratio"),
            token_groups=(("planetary", "ratio"),),
            required=False,
        ),
        "ring_od_mm": _find_column(
            fieldnames,
            aliases=(
                "ring_outer_diameter_mm",
                "ring_ring_outer_diameter_mm",
                "ring_D_ring_out_mm",
                "ring_D_out_mm",
                "ring_od_mm",
            ),
            token_groups=(("ring", "outer", "diameter"), ("ring", "d_ring_out"), ("ring", "d_out")),
        ),
        "carrier_od_mm": _find_column(
            fieldnames,
            aliases=("carrier_outer_diameter_mm", "carrier_D_c_mm", "carrier_diameter_mm"),
            token_groups=(("carrier", "outer", "diameter"), ("carrier", "d_c")),
            required=False,
        ),
        "carrier_thickness_mm": _find_column(
            fieldnames,
            aliases=("carrier_thickness_mm", "carrier_t_c_mm", "carrier_required_thickness_mm"),
            token_groups=(("carrier", "thickness"), ("carrier", "t_c")),
            required=False,
        ),
        "rotor_plate_thickness_mm": _find_column(
            fieldnames,
            aliases=(
                "rotor_support_plate_thickness_mm",
                "rotor_support_t_plate_mm",
                "rotor_support_t_p_mm",
                "rotor_support_required_plate_thickness_mm",
            ),
            token_groups=(("rotor_support", "plate", "thickness"), ("rotor_support", "t_plate"), ("rotor_support", "t_p")),
            required=False,
        ),
        "output_span_mm": _find_column(
            fieldnames,
            aliases=(
                "output_system_L_o_mm",
                "output_system_bearing_span_mm",
                "output_system_total_length_mm",
                "output_system_output_span_mm",
            ),
            token_groups=(("output_system", "bearing", "span"), ("output_system", "l_o")),
            required=False,
        ),
    }


def _optional_value(row: dict, column: str | None, *, default: float = 0.0) -> float:
    if column is None:
        return default
    value = row.get(column, "")
    if value in ("", None):
        return default
    return float(value)


def rank_candidates(input_csv: Path, motors_yaml: Path):
    if not input_csv.exists():
        raise FileNotFoundError(f"Feasible-candidate CSV not found: {input_csv}")

    motors = load_motor_dimensions(motors_yaml)

    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Input CSV has no header.")
        columns = resolve_columns(list(reader.fieldnames))
        rows = list(reader)

    if not rows:
        raise ValueError("No feasible candidates exist in the input CSV.")

    ranked = []

    for row in rows:
        motor_key = row[columns["motor_key"]]
        if motor_key not in motors:
            raise KeyError(
                f"Candidate references motor '{motor_key}', which is not present in {motors_yaml}."
            )

        motor_od = motors[motor_key]["outer_diameter_mm"]
        motor_length = motors[motor_key]["axial_length_mm"]

        ring_od = _to_float(row[columns["ring_od_mm"]], name="ring outer diameter")
        carrier_od = _optional_value(row, columns["carrier_od_mm"], default=0.0)
        face_width = _to_float(row[columns["face_width_mm"]], name="face width")
        carrier_t = _optional_value(row, columns["carrier_thickness_mm"], default=0.0)
        rotor_plate_t = _optional_value(row, columns["rotor_plate_thickness_mm"], default=0.0)
        output_span = _optional_value(row, columns["output_span_mm"], default=0.0)

        diameter_candidates = {
            "motor": motor_od,
            "ring": ring_od,
            "carrier": carrier_od,
        }
        radial_source = max(diameter_candidates, key=diameter_candidates.get)
        D_pkg = diameter_candidates[radial_source]

        gearbox_axial_proxy = rotor_plate_t + face_width + carrier_t + output_span
        L_pkg = motor_length + gearbox_axial_proxy

        box_volume_mm3 = D_pkg**2 * L_pkg
        cyl_volume_mm3 = math.pi / 4.0 * D_pkg**2 * L_pkg

        result = dict(row)
        result.update({
            "ranking_metric": "bounding_cylinder_volume",
            "package_diameter_mm": D_pkg,
            "package_axial_length_mm": L_pkg,
            "gearbox_axial_proxy_mm": gearbox_axial_proxy,
            "bounding_cylinder_volume_mm3": cyl_volume_mm3,
            "bounding_cylinder_volume_cm3": cyl_volume_mm3 / 1000.0,
            "bounding_box_volume_mm3": box_volume_mm3,
            "bounding_box_volume_cm3": box_volume_mm3 / 1000.0,
            "radial_envelope_governed_by": radial_source,
            "motor_outer_diameter_mm": motor_od,
            "motor_axial_length_mm": motor_length,
            "ring_outer_diameter_for_ranking_mm": ring_od,
            "carrier_outer_diameter_for_ranking_mm": carrier_od,
            "rotor_plate_thickness_for_ranking_mm": rotor_plate_t,
            "carrier_thickness_for_ranking_mm": carrier_t,
            "output_span_for_ranking_mm": output_span,
        })

        if columns["z_r"] is not None:
            result["_display_z_r"] = int(float(row[columns["z_r"]]))
        elif columns["z_s"] and columns["z_p"]:
            result["_display_z_r"] = int(float(row[columns["z_s"]])) + 2 * int(float(row[columns["z_p"]]))
        else:
            result["_display_z_r"] = None

        if columns["ratio"] is not None:
            result["_display_ratio"] = float(row[columns["ratio"]])
        elif columns["z_s"] and result["_display_z_r"] is not None:
            z_s = int(float(row[columns["z_s"]]))
            result["_display_ratio"] = 1.0 + result["_display_z_r"] / z_s
        else:
            result["_display_ratio"] = None

        ranked.append(result)

    ranked.sort(
        key=lambda r: (
            float(r["bounding_cylinder_volume_mm3"]),
            float(r["package_diameter_mm"]),
            float(r["package_axial_length_mm"]),
            r[columns["candidate_id"]],
        )
    )

    for rank, row in enumerate(ranked, start=1):
        row["packaging_rank"] = rank

    return ranked, columns


def write_ranked_csv(ranked: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    cleaned = [
        {k: v for k, v in row.items() if not k.startswith("_display_")}
        for row in ranked
    ]

    ranking_columns = [
        "packaging_rank",
        "ranking_metric",
        "package_diameter_mm",
        "package_axial_length_mm",
        "gearbox_axial_proxy_mm",
        "bounding_cylinder_volume_cm3",
        "bounding_box_volume_cm3",
        "radial_envelope_governed_by",
        "motor_outer_diameter_mm",
        "motor_axial_length_mm",
        "ring_outer_diameter_for_ranking_mm",
        "carrier_outer_diameter_for_ranking_mm",
        "rotor_plate_thickness_for_ranking_mm",
        "carrier_thickness_for_ranking_mm",
        "output_span_for_ranking_mm",
    ]

    remaining = [
        k for k in cleaned[0].keys()
        if k not in ranking_columns
    ]
    fieldnames = [k for k in ranking_columns if k in cleaned[0]] + remaining

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cleaned)


def _fmt(value, digits=2):
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}"


def print_resolved_columns(columns):
    print("\nResolved packaging columns:")
    for key in (
        "ring_od_mm",
        "carrier_od_mm",
        "carrier_thickness_mm",
        "rotor_plate_thickness_mm",
        "output_span_mm",
    ):
        resolved = columns[key] if columns[key] else "[not available: 0 used]"
        print(f"  {key:<28} -> {resolved}")


def print_ranking(ranked, columns, *, top_n: int):
    top_n = min(top_n, len(ranked))

    print("\n" + "=" * 126)
    print("ISSPG FEASIBLE-CANDIDATE PACKAGING RANKING")
    print("=" * 126)
    print("Metric: smallest analytical bounding-cylinder volume (smaller is better)")
    print("Axial size is a current stack-up proxy; final CAD may reduce it through component overlap.\n")

    header = (
        f"{'Rank':>4}  {'Candidate':<38}  {'Motor':<16}  "
        f"{'Zs':>3} {'Zp':>3} {'Zr':>4} {'Np':>2} {'m':>5} {'b':>6} {'i':>6}  "
        f"{'Dpkg':>7} {'Lpkg':>7} {'Vcyl cm3':>10}"
    )
    print(header)
    print("-" * len(header))

    for row in ranked[:top_n]:
        cid = row[columns["candidate_id"]]
        motor = row[columns["motor_key"]]
        zs = row[columns["z_s"]] if columns["z_s"] else "-"
        zp = row[columns["z_p"]] if columns["z_p"] else "-"
        np_ = row[columns["n_planets"]] if columns["n_planets"] else "-"
        m = row[columns["module_mm"]] if columns["module_mm"] else "-"
        b = row[columns["face_width_mm"]]

        print(
            f"{int(row['packaging_rank']):>4}  {cid:<38.38}  {motor:<16.16}  "
            f"{str(zs):>3} {str(zp):>3} {str(row['_display_z_r'] if row['_display_z_r'] is not None else '-'):>4} "
            f"{str(np_):>2} {str(m):>5} {str(b):>6} {_fmt(row['_display_ratio'], 3):>6}  "
            f"{_fmt(row['package_diameter_mm'], 2):>7} {_fmt(row['package_axial_length_mm'], 2):>7} "
            f"{_fmt(row['bounding_cylinder_volume_cm3'], 1):>10}"
        )

    print(f"\nDisplayed top {top_n} of {len(ranked)} feasible candidates.")
    print("=" * 126)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rank feasible ISSPG candidates by smallest analytical packaging envelope."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--motors", type=Path, default=DEFAULT_MOTORS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top", type=int, default=10)
    return parser.parse_args()


def main():
    args = parse_args()

    ranked, columns = rank_candidates(
        input_csv=args.input,
        motors_yaml=args.motors,
    )

    write_ranked_csv(ranked, args.output)
    print_resolved_columns(columns)
    print_ranking(ranked, columns, top_n=args.top)
    print(f"\nRanked CSV written to: {args.output}")


if __name__ == "__main__":
    main()
