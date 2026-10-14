#!/usr/bin/env python3
"""Backlit Canopy — clean runtime kernel (successor V13: canonical packet batches integrated with VM zero-plane, six-plane point solving, relative hallway copying, and packet codec).

This is a standalone, deterministic implementation of the rebuilt bootstrap,
source reader, exact circle/page mechanics, addressed local fold-down, typed
state difference, replay witness, and effect-scoped authority boundary.

It deliberately does not import, execute, or wrap a historical BC engine.
It is not a full replacement for the prior scientific/glyph catalogue; its
capability manifest makes that scope explicit. The runtime keeps historical inspection data
in an optional checksum-verified companion ROM and supports bounded checkpointed event bundles.
"""
from __future__ import annotations

import argparse
import base64
import ast
import copy
import hashlib
import json
import pathlib
import re
import sys
import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

ENGINE_IDENTITY = "Backlit Canopy"
RUNTIME_STATE = "warm"
SCHEMA = "BC-CLEAN-RUNTIME-13"
ORIGIN_ID = "OriginID:0"
CIRCLE_STEPS = 360
PAGE_STEPS = 90
PAGES_PER_CIRCLE = 4
SPHERE_COUNT = 8
APERTURE_PREFIX = (3, 5, 7)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def circle_step(start: int, ticks: int) -> int:
    """Advance exact integer circle ticks. No radians/floats enter the floor."""
    if isinstance(start, bool) or not isinstance(start, int):
        raise TypeError("circle start must be an integer")
    if isinstance(ticks, bool) or not isinstance(ticks, int):
        raise TypeError("circle ticks must be an integer")
    if not 0 <= start < CIRCLE_STEPS:
        raise ValueError("circle start outside 0..359")
    return (start + ticks) % CIRCLE_STEPS


def circle_page(step: int) -> int:
    """Return the 90-step page index for an already-normalized circle address."""
    if isinstance(step, bool) or not isinstance(step, int) or not 0 <= step < CIRCLE_STEPS:
        raise ValueError("circle step must be an integer in 0..359")
    return step // PAGE_STEPS


def exact_turn_fraction(ticks: int, denominator: int = CIRCLE_STEPS) -> tuple[int, int]:
    """Return a reduced exact fraction of a turn; symbolic radians are 2*pi*n/d."""
    if isinstance(ticks, bool) or not isinstance(ticks, int):
        raise TypeError("ticks must be an integer")
    if isinstance(denominator, bool) or not isinstance(denominator, int) or denominator <= 0:
        raise ValueError("denominator must be a positive integer")
    # Exact integer reduction; no float or external rational helper enters the floor.
    a = abs(ticks)
    b = denominator
    while b:
        a, b = b, a % b
    divisor = a or 1
    numerator = ticks // divisor
    reduced_denominator = denominator // divisor
    return numerator, reduced_denominator


def one_hot_box_state(value: int) -> tuple[int, ...]:
    """Nine one-hot positions; state 0 is the explicit all-off state."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 9:
        raise ValueError("box state must be 0..9")
    if value == 0:
        return (0,) * 9
    return tuple(1 if i == value - 1 else 0 for i in range(9))


def sphere_storage_record(sphere_index: int) -> dict[str, Any]:
    """Explicit addressable sphere factor and its eight cube slots.

    Geometry/physical calibration is not inferred here; this is storage-level
    factorisation. Each slot has a one-hot identity independent of phase views.
    """
    if isinstance(sphere_index, bool) or not isinstance(sphere_index, int) or not 0 <= sphere_index < SPHERE_COUNT:
        raise ValueError("sphere index must be 0..7")
    sphere_one_hot = tuple(1 if i == sphere_index else 0 for i in range(SPHERE_COUNT))
    slots = []
    for cube_index in range(8):
        slots.append({
            "cube_index": cube_index,
            "cube_one_hot": tuple(1 if i == cube_index else 0 for i in range(8)),
            "slot_address": (sphere_index, cube_index),
        })
    return {"sphere_index": sphere_index, "sphere_one_hot": sphere_one_hot, "cube_slots": tuple(slots)}


def initial_address(payload: Mapping[str, Any] | None = None) -> "BCAddress":
    body = copy.deepcopy(dict(payload or {}))
    body.setdefault("circle_step", 0)
    body.setdefault("spheres", [sphere_storage_record(i) for i in range(SPHERE_COUNT)])
    body.setdefault("levels", [{"lattice216": {"lane8": 0, "ternary27": [0, 0, 0]}, "fractal_side": 0}])
    return BCAddress(ORIGIN_ID, _canonical_json(body))


@dataclass(frozen=True)
class BCAddress:
    """Immutable authoritative address; views are reconstructed from payload."""
    origin_id: str
    payload_json: str

    @classmethod
    def from_payload(cls, origin_id: str, payload: Mapping[str, Any]) -> "BCAddress":
        return cls(origin_id, _canonical_json(copy.deepcopy(dict(payload))))

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.payload_json)

    @property
    def address_id(self) -> str:
        return _sha256_text(self.origin_id + "\0" + self.payload_json)[:24]

    def with_payload(self, payload: Mapping[str, Any]) -> "BCAddress":
        return BCAddress.from_payload(self.origin_id, payload)


PathPart = str | int


def _get_path(payload: Any, path: Sequence[PathPart]) -> Any:
    cur = payload
    for part in path:
        cur = cur[part]
    return cur


def _set_path(payload: Any, path: Sequence[PathPart], value: Any) -> None:
    if not path:
        raise ValueError("delta path cannot be empty")
    cur = payload
    for part in path[:-1]:
        cur = cur[part]
    cur[path[-1]] = value


@dataclass(frozen=True)
class StateDifference:
    """Typed relative operation against one exact address path."""
    schema: str
    parent_address_id: str
    path: tuple[PathPart, ...]
    steps: int
    modulus: int
    difference_address: str

    def apply(self, address: BCAddress) -> BCAddress:
        if address.address_id != self.parent_address_id:
            raise ValueError("difference_parent_address_mismatch")
        if self.modulus <= 0:
            raise ValueError("difference_modulus_invalid")
        payload = address.payload
        old = _get_path(payload, self.path)
        if isinstance(old, bool) or not isinstance(old, int):
            raise TypeError("difference target must be an integer state")
        _set_path(payload, self.path, (old + self.steps) % self.modulus)
        return address.with_payload(payload)


@dataclass(frozen=True)
class ClosureReport:
    dependency_closed: bool
    return_to_entry_closed: bool
    difference_replays: bool
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class FoldComputation:
    schema: str
    root_address_id: str
    end_address_id: str
    route_addresses: tuple[str, ...]
    route_steps: tuple[int, ...]
    difference: StateDifference
    closure: ClosureReport
    witness_id: str


def _get_modular_difference(old: int, new: int, modulus: int) -> int:
    """Signed representative of the exact modular state difference."""
    if modulus <= 0:
        raise ValueError("modulus must be positive")
    residue = (new - old) % modulus
    return residue - modulus if residue > modulus // 2 else residue


def fold_down(address: BCAddress, path: Sequence[PathPart], steps: int, modulus: int) -> FoldComputation:
    """Execute locally, return typed delta, and check each closure notion separately."""
    if isinstance(steps, bool) or not isinstance(steps, int):
        raise TypeError("steps must be an integer")
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 0:
        raise ValueError("modulus must be a positive integer")
    if not path:
        raise ValueError("fold path cannot be empty")
    root_payload = address.payload
    old = _get_path(root_payload, path)
    if isinstance(old, bool) or not isinstance(old, int):
        raise TypeError("fold target must be an integer state")
    # This fold requires only the addressed integer and modulus. Neighbouring
    # parent fields are preserved, never replaced by a scalar projection.
    route = [address]
    current = address
    unit = 1 if steps >= 0 else -1
    for _ in range(abs(steps)):
        payload = current.payload
        value = _get_path(payload, path)
        _set_path(payload, path, (value + unit) % modulus)
        current = current.with_payload(payload)
        route.append(current)
    new = _get_path(current.payload, path)
    delta_steps = _get_modular_difference(old, new, modulus)
    delta_identity = _sha256_text(_canonical_json({
        "schema": "BC-DELTA-1", "parent": address.address_id,
        "path": list(path), "steps": delta_steps, "modulus": modulus,
    }))[:24]
    delta = StateDifference("BC-DELTA-1", address.address_id, tuple(path), delta_steps, modulus, delta_identity)
    replay = delta.apply(address)
    dependency_closed = True
    unresolved: list[str] = []
    if replay.payload_json != current.payload_json:
        unresolved.append("difference_replay_mismatch")
    if len(route) != abs(steps) + 1:
        unresolved.append("route_length_mismatch")
    if _get_path(current.payload, path) != new:
        unresolved.append("end_state_readback_mismatch")
    dep_closed = dependency_closed and not unresolved
    return_closed = current.address_id == address.address_id
    replay_ok = replay.payload_json == current.payload_json
    witness_body = {
        "schema": "BC-FOLD-WITNESS-1", "root": address.address_id,
        "end": current.address_id, "route": [a.address_id for a in route],
        "difference": delta.difference_address, "dependency_closed": dep_closed,
        "return_to_entry_closed": return_closed, "difference_replays": replay_ok,
        "unresolved": unresolved,
    }
    witness_id = _sha256_text(_canonical_json(witness_body))[:24]
    return FoldComputation(
        "BC-FOLD-COMPUTATION-1", address.address_id, current.address_id,
        tuple(a.address_id for a in route), tuple([unit] * abs(steps)), delta,
        ClosureReport(dep_closed, return_closed, replay_ok, tuple(unresolved)), witness_id,
    )


@dataclass(frozen=True)
class SourceReadReport:
    schema: str
    filename: str
    source_sha256: str
    bytes_read: int
    syntax_pass: bool
    ast_pass: bool
    duplicate_definition_groups: tuple[tuple[str, int], ...]
    list_comprehension_count: int
    subscript_count: int
    call_count: int
    findings: tuple[str, ...]


class _ASTStats(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defs: dict[str, int] = {}
        self.list_comprehensions = 0
        self.subscripts = 0
        self.calls = 0
        self.scope: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        key = ".".join([*self.scope, node.name])
        self.defs[key] = self.defs.get(key, 0) + 1
        self.scope.append(f"<locals:{node.name}>")
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        key = ".".join([*self.scope, node.name])
        self.defs[key] = self.defs.get(key, 0) + 1
        self.scope.append(f"<locals:{node.name}>")
        self.generic_visit(node)
        self.scope.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.list_comprehensions += 1
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        self.subscripts += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.calls += 1
        self.generic_visit(node)


def _node_tree(node: ast.AST, source: str) -> dict[str, Any]:
    """Small source tree retaining subscript indices and comprehension clauses."""
    result: dict[str, Any] = {"node": type(node).__name__}
    segment = ast.get_source_segment(source, node)
    if segment is not None:
        result["source"] = segment
    if isinstance(node, ast.Name):
        result["id"] = node.id
        result["context"] = type(node.ctx).__name__
    elif isinstance(node, ast.Constant):
        result["value"] = node.value
    elif isinstance(node, ast.Subscript):
        result["value_expr"] = _node_tree(node.value, source)
        result["index_expr"] = _node_tree(node.slice, source)
    elif isinstance(node, ast.Call):
        result["callee"] = _node_tree(node.func, source)
        result["args"] = [_node_tree(a, source) for a in node.args]
        result["keywords"] = [{"name": k.arg, "value": _node_tree(k.value, source)} for k in node.keywords]
    elif isinstance(node, ast.ListComp):
        result["element"] = _node_tree(node.elt, source)
        result["generators"] = [{
            "target": _node_tree(gen.target, source),
            "iter": _node_tree(gen.iter, source),
            "ifs": [_node_tree(c, source) for c in gen.ifs],
            "is_async": bool(gen.is_async),
        } for gen in node.generators]
    else:
        children = []
        for _, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                children.append(_node_tree(value, source))
            elif isinstance(value, list):
                children.extend(_node_tree(v, source) for v in value if isinstance(v, ast.AST))
        if children:
            result["children"] = children
    return result


def read_source_text(source: str, filename: str = "<memory>") -> SourceReadReport:
    raw = source.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    findings: list[str] = []
    try:
        tree = ast.parse(source, filename=filename, mode="exec")
        compile(tree, filename, "exec")
    except (SyntaxError, ValueError, TypeError) as exc:
        return SourceReadReport("BC-SOURCE-READ-1", filename, digest, len(raw), False, False, (), 0, 0, 0,
                                (f"syntax_or_ast_error:{type(exc).__name__}:{exc}",))
    stats = _ASTStats()
    stats.visit(tree)
    duplicates = tuple(sorted((name, count) for name, count in stats.defs.items() if count > 1))
    if duplicates:
        findings.append("duplicate_definitions_are_visible_not_automatically_dead")
    if stats.subscripts:
        findings.append("subscript_indices_preserved_in_ast")
    if stats.list_comprehensions:
        findings.append("comprehension_targets_and_iterators_preserved_in_ast")
    findings.append("source_was_parsed_and_compiled_but_not_executed")
    return SourceReadReport("BC-SOURCE-READ-1", filename, digest, len(raw), True, True, duplicates,
                            stats.list_comprehensions, stats.subscripts, stats.calls, tuple(findings))


def inspect_expression(source: str, expression: str) -> dict[str, Any]:
    """Parse exactly one expression without executing it; preserve index meanings."""
    module = ast.parse(expression, filename=source, mode="eval")
    return _node_tree(module.body, expression)


def inspect_source_fragment(source: str, fragment: str) -> dict[str, Any]:
    """Parse one or more source statements, including assignments and comprehensions."""
    module = ast.parse(fragment, filename=source, mode="exec")
    return {"node": "Module", "body": [_node_tree(node, fragment) for node in module.body]}


class EffectAuthority:
    """One effect-scoped authority boundary; function names do not grant access."""
    EFFECTS = frozenset({"source_read", "source_write", "project_save", "engine_cold_commit", "external_io", "glyph_admission"})

    def authorize(self, effect: str, grants: Iterable[str]) -> bool:
        if effect not in self.EFFECTS:
            raise ValueError("unknown_effect_scope")
        return effect in frozenset(grants)


@dataclass(frozen=True)
class ExecutorRecord:
    operation: str
    executor: Callable[..., Any]
    effect: str


class CanonicalRegistry:
    """Single registry: a duplicate operation identity is a construction error."""
    def __init__(self) -> None:
        self._records: dict[str, ExecutorRecord] = {}

    def register(self, operation: str, executor: Callable[..., Any], effect: str = "pure") -> None:
        if not operation or operation in self._records:
            raise ValueError(f"duplicate_or_empty_operation:{operation}")
        self._records[operation] = ExecutorRecord(operation, executor, effect)

    def resolve(self, operation: str) -> ExecutorRecord:
        try:
            return self._records[operation]
        except KeyError as exc:
            raise LookupError(f"unregistered_operation:{operation}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))



# ---------------------------------------------------------------------------
# Typed full-floor address substrate — V3
# ---------------------------------------------------------------------------
# These records are newly implemented. They do not import or execute legacy
# source. BCAddress above remains the generic immutable carrier used by the
# original fold-down unit tests; BCFloorAddress is the typed full-floor state.

AXES = ("X", "Y", "Z")
BOX_EMPTY = 10
GRAY_CYCLE = ((0, 0), (1, 0), (1, 1), (0, 1))
LANE8_PERMS = {
    "X": (2, 3, 6, 7, 0, 1, 4, 5),
    "Y": (1, 5, 3, 7, 0, 4, 2, 6),
    "Z": (1, 3, 0, 2, 5, 7, 4, 6),
}
LANE8_INV_PERMS = {
    "X": (4, 5, 0, 1, 6, 7, 2, 3),
    "Y": (4, 0, 6, 2, 5, 1, 7, 3),
    "Z": (2, 0, 3, 1, 6, 4, 7, 5),
}
QUARTER_FRAME = {
    (0, +1): ((0, 2, 1), (1, 1, -1)),
    (0, -1): ((0, 2, 1), (1, -1, 1)),
    (1, +1): ((2, 1, 0), (-1, 1, 1)),
    (1, -1): ((2, 1, 0), (1, 1, -1)),
    (2, +1): ((1, 0, 2), (1, -1, 1)),
    (2, -1): ((1, 0, 2), (-1, 1, 1)),
}


def _strict_int(v: Any, label: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{label}_must_be_integer")
    return v


def octant_from_cube(index: int) -> tuple[int, int, int]:
    _strict_int(index, "cube_index")
    if index not in range(8):
        raise ValueError("cube_index_out_of_range")
    return (index & 1, (index >> 1) & 1, (index >> 2) & 1)


def cube_from_octant(bits: Sequence[int]) -> int:
    if len(bits) != 3 or any(type(b) is not int or b not in (0, 1) for b in bits):
        raise ValueError("octant_must_be_three_binary_bits")
    return bits[0] + 2 * bits[1] + 4 * bits[2]


def _other_axes(axis: int) -> tuple[int, int]:
    if axis not in (0, 1, 2):
        raise ValueError("axis_index_out_of_range")
    return tuple(i for i in (0, 1, 2) if i != axis)  # type: ignore[return-value]


def _surface_circle_position(octant: tuple[int, int, int], circle_addr: int, axis: int) -> int:
    if not 1 <= circle_addr <= PAGE_STEPS:
        raise ValueError("page_circle_address_out_of_range")
    b, c = _other_axes(axis)
    try:
        gray_index = GRAY_CYCLE.index((octant[b], octant[c]))
    except ValueError as exc:
        raise ValueError("passive_polarity_pair_invalid") from exc
    return gray_index * PAGE_STEPS + circle_addr - 1


def exact_circle_step(octant: tuple[int, int, int], circle_addr: int, axis: int, ticks: int) -> tuple[tuple[int, int, int], int]:
    """Walk an addressed 360-step face path; quarter boundaries update passive Gray bits."""
    _strict_int(ticks, "circle_ticks")
    if axis not in (0, 1, 2):
        raise ValueError("axis_index_out_of_range")
    pos = _surface_circle_position(octant, circle_addr, axis)
    pos2 = (pos + ticks) % CIRCLE_STEPS
    gray_index, page_zero_based = divmod(pos2, PAGE_STEPS)
    out = list(octant)
    b, c = _other_axes(axis)
    out[b], out[c] = GRAY_CYCLE[gray_index]
    return tuple(out), page_zero_based + 1


@dataclass(frozen=True)
class FloorPage:
    axis: str
    box: int = 0
    state: int = 0  # 0..8 = one-hot position; 9 = all-off / state 10

    def __post_init__(self) -> None:
        if self.axis not in AXES:
            raise ValueError("page_axis_invalid")
        if type(self.box) is not int or self.box not in range(9):
            raise ValueError("page_box_must_be_0_through_8")
        if type(self.state) is not int or self.state not in range(10):
            raise ValueError("page_state_must_be_one_hot_0_through_8_or_all_off_9")

    @property
    def circle_addr(self) -> int:
        return self.box * 10 + self.state + 1

    def one_hot(self) -> tuple[int, ...]:
        if self.state == 9:
            return (0,) * 9
        return tuple(1 if i == self.state else 0 for i in range(9))

    @classmethod
    def from_circle_addr(cls, axis: str, address: int) -> "FloorPage":
        _strict_int(address, "page_address")
        if not 1 <= address <= PAGE_STEPS:
            raise ValueError("page_circle_address_out_of_range")
        q = address - 1
        return cls(axis, q // 10, q % 10)

    def move_local(self, dx: int, dy: int) -> "FloorPage":
        _strict_int(dx, "box_dx"); _strict_int(dy, "box_dy")
        if self.state == 9:
            raise ValueError("cannot_move_from_all_off_box")
        x, y = self.state % 3, self.state // 3
        nx, ny = x + dx, y + dy
        if nx not in range(3) or ny not in range(3):
            raise ValueError("box_move_crossed_local_boundary")
        return FloorPage(self.axis, self.box, ny * 3 + nx)


@dataclass(frozen=True)
class RotationFrame:
    perm: tuple[int, int, int] = (0, 1, 2)
    sign: tuple[int, int, int] = (1, 1, 1)

    def __post_init__(self) -> None:
        if tuple(sorted(self.perm)) != (0, 1, 2):
            raise ValueError("rotation_frame_permutation_invalid")
        if len(self.sign) != 3 or any(s not in (-1, 1) for s in self.sign):
            raise ValueError("rotation_frame_sign_invalid")

    def transport(self, local_axis: int, ticks: int) -> tuple[int, int]:
        if local_axis not in (0, 1, 2):
            raise ValueError("axis_index_out_of_range")
        return self.perm[local_axis], ticks * self.sign[local_axis]

    def compose_space(self, other: "RotationFrame") -> "RotationFrame":
        perm = tuple(self.perm[g] for g in other.perm)
        sign = tuple(self.sign[g] * other.sign[l] for l, g in enumerate(other.perm))
        return RotationFrame(perm, sign)

    def inverse(self) -> "RotationFrame":
        ip = [0, 0, 0]; sg = [1, 1, 1]
        for local, global_axis in enumerate(self.perm):
            ip[global_axis] = local
            sg[global_axis] = self.sign[local]
        return RotationFrame(tuple(ip), tuple(sg))

    def quarter(self, axis: int, direction: int) -> "RotationFrame":
        if axis not in (0, 1, 2) or direction not in (-1, 1):
            raise ValueError("quarter_turn_invalid")
        perm, sign = QUARTER_FRAME[(axis, direction)]
        # Body-generator composition: the fixed quarter-turn acts on the left.
        return RotationFrame(perm, sign).compose_space(self)

    def quarter_power(self, axis: int, count: int) -> "RotationFrame":
        out = self
        direction = 1 if count >= 0 else -1
        for _ in range(abs(count) % 4):
            out = out.quarter(axis, direction)
        return out

    def as_dict(self) -> dict[str, Any]:
        return {"perm": list(self.perm), "sign": list(self.sign)}


@dataclass(frozen=True)
class RotationSurface:
    active: bool = False
    octant: tuple[int, int, int] = (0, 0, 0)
    pages: tuple[FloorPage, FloorPage, FloorPage] = field(default_factory=lambda: (
        FloorPage("X"), FloorPage("Y"), FloorPage("Z")))
    fine: tuple[int, int, int] = (0, 0, 0)
    radices: tuple[int, ...] = ()
    frame: RotationFrame = field(default_factory=RotationFrame)

    def __post_init__(self) -> None:
        if type(self.active) is not bool:
            raise TypeError("rotation_active_must_be_bool")
        if len(self.octant) != 3 or any(type(x) is not int or x not in (0, 1) for x in self.octant):
            raise ValueError("rotation_octant_invalid")
        if tuple(p.axis for p in self.pages) != AXES:
            raise ValueError("rotation_requires_xyz_pages")
        if any(type(r) is not int or r < 2 for r in self.radices):
            raise ValueError("rotation_radices_must_be_integers_at_least_two")
        cap = self.fine_capacity
        if len(self.fine) != 3 or any(type(v) is not int or not 0 <= v < cap for v in self.fine):
            raise ValueError("rotation_fine_offset_out_of_range")

    @property
    def fine_capacity(self) -> int:
        out = 1
        for radix in self.radices:
            out *= radix
        return out

    @property
    def ticks_per_turn(self) -> int:
        return CIRCLE_STEPS * self.fine_capacity

    @property
    def cube(self) -> int:
        return cube_from_octant(self.octant)

    def set_active(self, active: bool, cube: int | None = None) -> "RotationSurface":
        if not active:
            if cube is not None:
                raise ValueError("inactive_rotation_cannot_specify_cube")
            return RotationSurface(False)
        if cube is None:
            return RotationSurface(True, self.octant, self.pages, self.fine, self.radices, self.frame)
        return RotationSurface(True, octant_from_cube(cube))

    def advance_ticks(self, axis: int, ticks: int) -> tuple["RotationSurface", dict[str, int]]:
        _strict_int(ticks, "rotation_ticks")
        if not self.active:
            raise ValueError("rotation_shell_is_off")
        if axis not in (0, 1, 2):
            raise ValueError("axis_index_out_of_range")
        if ticks == 0:
            return self, {"fine_ticks": 0, "coarse_steps": 0, "quarter_crossings": 0}
        capacity = self.fine_capacity
        coarse_delta, fine_after = divmod(self.fine[axis] + ticks, capacity)
        old_pos = _surface_circle_position(self.octant, self.pages[axis].circle_addr, axis)
        signed_quarters = (old_pos + coarse_delta) // PAGE_STEPS - old_pos // PAGE_STEPS
        octant, addr = exact_circle_step(self.octant, self.pages[axis].circle_addr, axis, coarse_delta)
        pages = list(self.pages)
        pages[axis] = FloorPage.from_circle_addr(AXES[axis], addr)
        fine = list(self.fine); fine[axis] = fine_after
        frame = self.frame.quarter_power(axis, signed_quarters)
        out = RotationSurface(self.active, octant, tuple(pages), tuple(fine), self.radices, frame)
        return out, {"fine_ticks": abs(ticks), "coarse_steps": abs(coarse_delta),
                     "quarter_crossings": abs(signed_quarters)}

    def apply_local_ticks(self, local_axis: int, ticks: int) -> tuple["RotationSurface", dict[str, Any]]:
        global_axis, transported = self.frame.transport(local_axis, ticks)
        after, ledger = self.advance_ticks(global_axis, transported)
        return after, {"local_axis": local_axis, "global_axis": global_axis, "requested_ticks": ticks,
                       "transported_ticks": transported, **ledger,
                       "frame_before": self.frame.as_dict(), "frame_after": after.frame.as_dict()}

    def promote(self, radix: int) -> "RotationSurface":
        _strict_int(radix, "promotion_radix")
        if radix < 2:
            raise ValueError("promotion_radix_must_be_at_least_two")
        return RotationSurface(self.active, self.octant, self.pages,
                              tuple(f * radix for f in self.fine), self.radices + (radix,), self.frame)

    def demote(self) -> "RotationSurface":
        if not self.radices:
            raise ValueError("already_at_base_shell")
        r = self.radices[-1]
        if any(f % r for f in self.fine):
            raise ValueError("fine_state_not_divisible_by_final_radix")
        return RotationSurface(self.active, self.octant, self.pages,
                              tuple(f // r for f in self.fine), self.radices[:-1], self.frame)

    def as_dict(self) -> dict[str, Any]:
        return {"active": self.active, "octant": list(self.octant),
                "pages": [{"axis": p.axis, "box": p.box, "state": p.state,
                           "circle_addr": p.circle_addr, "one_hot": list(p.one_hot())} for p in self.pages],
                "fine": list(self.fine), "radices": list(self.radices), "frame": self.frame.as_dict(),
                "state_code": 0 if not self.active else self.cube + 1, "cube": self.cube}


# ---------------------------------------------------------------------------
# Prime-harmonic aperture: 504 directed heads and exact 504:360 alignment.
# The head and the physical floor circle remain different address spaces.
# Their relation is carried on the exact common refinement LCM(504,360)=2520.
# ---------------------------------------------------------------------------
HARMONIC_HEADS = 504
HARMONIC_ANTIPODE_STEPS = 252
HARMONIC_COMMON_TURN_UNITS = 2520
HARMONIC_HEAD_UNIT = 5       # 2520 / 504
FLOOR_CIRCLE_UNIT = 7        # 2520 / 360
HARMONIC_APERTURE_STAGES = ((), (3,), (3, 5), (3, 5, 7))


@dataclass(frozen=True)
class PrimeHarmonicAddress:
    """One directed 504-head address with reference and winding kept explicit.

    `head` is a cyclic index 0..503. `winding` is not folded away when the head
    returns to the same cyclic index. The prime prefix selects an observation /
    search aperture; it does not itself advance the physical head.
    """
    head: int = 0
    reference_head: int = 0
    winding: int = 0
    aperture_prefix: tuple[int, ...] = (3, 5, 7)

    def __post_init__(self) -> None:
        if type(self.head) is not int or not 0 <= self.head < HARMONIC_HEADS:
            raise ValueError("harmonic_head_out_of_range")
        if type(self.reference_head) is not int or not 0 <= self.reference_head < HARMONIC_HEADS:
            raise ValueError("harmonic_reference_head_out_of_range")
        if type(self.winding) is not int:
            raise TypeError("harmonic_winding_must_be_integer")
        if tuple(self.aperture_prefix) not in HARMONIC_APERTURE_STAGES:
            raise ValueError("harmonic_aperture_prefix_invalid")

    @property
    def address_id(self) -> str:
        return _sha256_text(_canonical_json({
            "schema":"BC-PRIME-HARMONIC-HEAD-1", "head":self.head,
            "reference_head":self.reference_head, "winding":self.winding,
            "aperture_prefix":list(self.aperture_prefix)}))[:24]

    @property
    def relative_head_steps(self) -> int:
        return (self.head - self.reference_head) % HARMONIC_HEADS

    @property
    def signed_relative_steps(self) -> int:
        d = self.relative_head_steps
        # The antipodal tie is represented as -252; the oriented residue remains available.
        return d if d < HARMONIC_ANTIPODE_STEPS else d - HARMONIC_HEADS

    @property
    def antipodal(self) -> bool:
        return self.relative_head_steps == HARMONIC_ANTIPODE_STEPS

    def with_aperture(self, prefix: Sequence[int]) -> "PrimeHarmonicAddress":
        return PrimeHarmonicAddress(self.head, self.reference_head, self.winding, tuple(prefix))

    def as_dict(self) -> dict[str, Any]:
        return {"address_id":self.address_id, "head":self.head,
                "reference_head":self.reference_head, "winding":self.winding,
                "relative_head_steps":self.relative_head_steps,
                "signed_relative_steps":self.signed_relative_steps,
                "antipodal":self.antipodal, "aperture_prefix":list(self.aperture_prefix)}


@dataclass(frozen=True)
class HarmonicTransitionWitness:
    schema: str
    root_address_id: str
    end_address_id: str
    requested_head_steps: int
    root_absolute_head: int
    end_absolute_head: int
    cyclic_head_delta: int
    winding_delta: int
    replay_pass: bool
    return_to_entry_closed: bool


@dataclass(frozen=True)
class HarmonicHeadStepResult:
    address: PrimeHarmonicAddress
    witness: HarmonicTransitionWitness


def harmonic_head_step(address: PrimeHarmonicAddress, steps: int) -> HarmonicHeadStepResult:
    """Advance exact 504-head steps, retaining winding when cyclic phase returns."""
    if not isinstance(address, PrimeHarmonicAddress):
        raise TypeError("harmonic_address_required")
    _strict_int(steps, "harmonic_head_steps")
    start_abs = address.winding * HARMONIC_HEADS + address.head
    end_abs = start_abs + steps
    end_winding, end_head = divmod(end_abs, HARMONIC_HEADS)
    end = PrimeHarmonicAddress(end_head, address.reference_head, end_winding, address.aperture_prefix)
    replay_abs = address.winding * HARMONIC_HEADS + address.head + steps
    replay_winding, replay_head = divmod(replay_abs, HARMONIC_HEADS)
    replay_pass = (replay_head, replay_winding, address.reference_head, address.aperture_prefix) == (
        end.head, end.winding, end.reference_head, end.aperture_prefix)
    witness = HarmonicTransitionWitness(
        "BC-HARMONIC-504-STEP-WITNESS-1", address.address_id, end.address_id,
        steps, start_abs, end_abs, (end.head-address.head) % HARMONIC_HEADS,
        end.winding-address.winding, replay_pass, end.address_id == address.address_id)
    return HarmonicHeadStepResult(end, witness)


@dataclass(frozen=True)
class HarmonicAntipodalRelation:
    schema: str
    source_address_id: str
    source_head: int
    antipode_address: PrimeHarmonicAddress
    pair_heads: tuple[int, int]
    pair_address: str
    antipodal_distance: int
    midpoint_stored: bool
    directed_head_count: int
    antipodal_pair_count: int


def harmonic_antipode_relation(address: PrimeHarmonicAddress) -> HarmonicAntipodalRelation:
    """Return the opposite directed head; midpoint remains an implicit relation."""
    result = harmonic_head_step(address, HARMONIC_ANTIPODE_STEPS)
    pair = tuple(sorted((address.head, result.address.head)))
    pair_id = _sha256_text(_canonical_json({"schema":"BC-504-ANTIPODAL-PAIR-1","heads":pair}))[:24]
    return HarmonicAntipodalRelation("BC-504-ANTIPODAL-RELATION-1", address.address_id,
        address.head, result.address, pair, pair_id, HARMONIC_ANTIPODE_STEPS,
        False, HARMONIC_HEADS, HARMONIC_HEADS // 2)


@dataclass(frozen=True)
class PrimeHarmonicFoldView:
    schema: str
    view_address: str
    source_address_id: str
    source_head: int
    reference_head: int
    winding: int
    aperture_prefix: tuple[int, ...]
    relative_head_steps: int
    signed_relative_steps: int
    antipodal: bool
    derived_view_only: bool


def prime_harmonic_fold_views(address: PrimeHarmonicAddress) -> tuple[PrimeHarmonicFoldView, ...]:
    """Expose aperture prefixes as separately addressed views, not head motion."""
    if not isinstance(address, PrimeHarmonicAddress):
        raise TypeError("harmonic_address_required")
    views=[]
    for prefix in HARMONIC_APERTURE_STAGES[1:]:
        body={"schema":"BC-PRIME-HARMONIC-FOLD-VIEW-1", "source":address.address_id,
              "prefix":list(prefix), "head":address.head, "reference":address.reference_head,
              "winding":address.winding, "relative":address.relative_head_steps}
        view_addr=_sha256_text(_canonical_json(body))[:24]
        views.append(PrimeHarmonicFoldView("BC-PRIME-HARMONIC-FOLD-VIEW-1", view_addr,
            address.address_id, address.head, address.reference_head, address.winding, prefix,
            address.relative_head_steps, address.signed_relative_steps, address.antipodal, True))
    return tuple(views)


@dataclass(frozen=True)
class HarmonicCircleAlignment:
    schema: str
    harmonic_address_id: str
    floor_axis: int
    head: int
    floor_circle_position: int
    common_turn_units: int
    harmonic_phase_units: int
    floor_phase_units: int
    signed_residual_units: int
    aligned: bool


def harmonic_circle_alignment(address: PrimeHarmonicAddress,
                              surface: RotationSurface, axis: int = 0) -> HarmonicCircleAlignment:
    """Compare 504-head and 360-circle phase exactly on their 2520-unit refinement."""
    if not isinstance(address, PrimeHarmonicAddress):
        raise TypeError("harmonic_address_required")
    if not isinstance(surface, RotationSurface):
        raise TypeError("rotation_surface_required")
    if axis not in (0, 1, 2):
        raise ValueError("axis_index_out_of_range")
    pos=_surface_circle_position(surface.octant, surface.pages[axis].circle_addr, axis)
    harmonic_units=(address.head * HARMONIC_HEAD_UNIT) % HARMONIC_COMMON_TURN_UNITS
    floor_units=(pos * FLOOR_CIRCLE_UNIT) % HARMONIC_COMMON_TURN_UNITS
    residue=(harmonic_units-floor_units) % HARMONIC_COMMON_TURN_UNITS
    signed=residue if residue < HARMONIC_COMMON_TURN_UNITS//2 else residue-HARMONIC_COMMON_TURN_UNITS
    return HarmonicCircleAlignment("BC-HARMONIC-504-360-ALIGNMENT-1", address.address_id,
        axis, address.head, pos, HARMONIC_COMMON_TURN_UNITS, harmonic_units,
        floor_units, signed, residue == 0)


@dataclass(frozen=True)
class HarmonicCircleCrossingWitness:
    schema: str
    root_harmonic_address_id: str
    end_harmonic_address_id: str
    requested_alignment_steps: int
    head_steps: int
    floor_circle_ticks: int
    floor_axis: int
    alignment_before: HarmonicCircleAlignment
    alignment_after: HarmonicCircleAlignment
    phase_relation_preserved: bool
    phase_alignment_preserved: bool
    harmonic_return_to_entry_closed: bool
    floor_return_to_entry_closed: bool
    full_address_return_to_entry_closed: bool
    delta_replay_pass: bool
    relation_name: str
    claim_boundary: str


@dataclass(frozen=True)
class HarmonicCircleCrossingResult:
    harmonic_address: PrimeHarmonicAddress
    floor_surface: RotationSurface
    witness: HarmonicCircleCrossingWitness


def cross_harmonic_circle_boundary(address: PrimeHarmonicAddress,
                                   surface: RotationSurface,
                                   repetitions: int = 1,
                                   axis: int = 0) -> HarmonicCircleCrossingResult:
    """Advance 7 harmonic heads for every 5 floor-circle ticks, exactly.

    This is a discrete common-turn alignment rule, not a claim that any external
    physical system follows it. For nonaligned roots the phase residual is still
    preserved; `phase_alignment_preserved` records whether alignment remained true.
    """
    if not isinstance(address, PrimeHarmonicAddress):
        raise TypeError("harmonic_address_required")
    if not isinstance(surface, RotationSurface):
        raise TypeError("rotation_surface_required")
    _strict_int(repetitions, "alignment_repetitions")
    if axis not in (0, 1, 2):
        raise ValueError("axis_index_out_of_range")
    if not surface.active:
        raise ValueError("floor_rotation_shell_is_off")
    if surface.fine_capacity != 1:
        raise ValueError("harmonic_floor_crossing_requires_base_circle_resolution")
    before=harmonic_circle_alignment(address,surface,axis)
    head_result=harmonic_head_step(address, 7 * repetitions)
    surface_after,_ledger=surface.advance_ticks(axis, 5 * repetitions)
    after=harmonic_circle_alignment(head_result.address,surface_after,axis)
    relation_preserved=before.signed_residual_units == after.signed_residual_units
    witness=HarmonicCircleCrossingWitness(
        "BC-HARMONIC-504-360-CROSSING-WITNESS-1", address.address_id,
        head_result.address.address_id, repetitions, 7*repetitions, 5*repetitions,
        axis, before, after, relation_preserved, before.aligned and after.aligned,
        head_result.address.address_id == address.address_id, surface_after == surface,
        head_result.address.address_id == address.address_id and surface_after == surface,
        relation_preserved and after.head == head_result.address.head,
        "504-head/360-circle exact common-turn refinement",
        "structural phase relation only; no physical calibration is implied")
    return HarmonicCircleCrossingResult(head_result.address,surface_after,witness)


# ---------------------------------------------------------------------------
# Six-plane Structuralizer perspective, sharing the one signed-permutation
# frame mechanism above. Projection retains the omitted coordinate as depth;
# lift-back is exact and the authoritative address is never mutated.
# ---------------------------------------------------------------------------
PLANE_VIEW_ORDER = ("XY", "YX", "XZ", "ZX", "YZ", "ZY")
Point3 = tuple[int, int, int]


def _strict_point3(value: Sequence[int]) -> Point3:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise TypeError("point3_requires_three_integer_coordinates")
    if any(type(coordinate) is not int for coordinate in value):
        raise TypeError("point3_coordinates_must_be_exact_integers")
    return (value[0], value[1], value[2])


def _permutation_parity(permutation: Sequence[int]) -> int:
    inversions = sum(1 for i in range(len(permutation)) for j in range(i + 1, len(permutation))
                     if permutation[i] > permutation[j])
    return -1 if inversions % 2 else 1


def structuralizer_plane_frames() -> tuple[tuple[str, RotationFrame], ...]:
    """Return six ordered plane views from the canonical frame class.

    The two visible axes follow the plane label order. The depth-axis sign is
    selected so each 3-D signed permutation has determinant +1. No second
    transform table or trigonometric basis is generated.
    """
    result=[]
    axes={"X":0,"Y":1,"Z":2}
    for name in PLANE_VIEW_ORDER:
        first, second = axes[name[0]], axes[name[1]]
        depth = next(i for i in range(3) if i not in (first, second))
        permutation=(first, second, depth)
        parity=_permutation_parity(permutation)
        frame=RotationFrame(permutation, (1, 1, parity))
        determinant=parity * frame.sign[0] * frame.sign[1] * frame.sign[2]
        if determinant != 1:
            raise AssertionError("structuralizer_frame_not_proper")
        result.append((name,frame))
    return tuple(result)


PLANE_FRAMES = structuralizer_plane_frames()


def _frame_point_local(frame: RotationFrame, point: Point3) -> Point3:
    return tuple(point[frame.perm[i]] * frame.sign[i] for i in range(3))  # type: ignore[return-value]


def _frame_point_global(frame: RotationFrame, point: Point3) -> Point3:
    out=[0,0,0]
    for local_axis, global_axis in enumerate(frame.perm):
        out[global_axis]=point[local_axis] * frame.sign[local_axis]
    return (out[0],out[1],out[2])


def _pairwise_squared_distances(points: Sequence[Point3]) -> tuple[tuple[int,int,int], ...]:
    out=[]
    for i in range(len(points)):
        for j in range(i+1,len(points)):
            a,b=points[i],points[j]
            distance=sum((a[k]-b[k])**2 for k in range(3))
            out.append((i,j,distance))
    return tuple(out)


def _points_digest(points: Sequence[Point3]) -> str:
    return _sha256_text(_canonical_json([list(p) for p in points]))


@dataclass(frozen=True)
class SixPlaneView:
    schema: str
    plane_name: str
    view_address: str
    source_address_id: str
    source_points_digest: str
    frame: RotationFrame
    projected_points: tuple[tuple[int,int], ...]
    depth_residuals: tuple[int, ...]
    lifted_points: tuple[Point3, ...]
    source_squared_distances: tuple[tuple[int,int,int], ...]
    lifted_squared_distances: tuple[tuple[int,int,int], ...]
    exact_lift_pass: bool
    metric_preserved: bool


@dataclass(frozen=True)
class SixPlanePerspectivePacket:
    schema: str
    packet_address: str
    source_address_id: str
    source_points_digest: str
    point_count: int
    plane_order: tuple[str, ...]
    source_squared_distances: tuple[tuple[int,int,int], ...]
    views: tuple[SixPlaneView, ...]
    authoritative_carrier_mutated: bool


@dataclass(frozen=True)
class SixPlaneReopenWitness:
    schema: str
    pass_all: bool
    source_address_id: str
    packet_address: str
    views_rebuilt: int
    exact_lift_pass: bool
    metric_preserved: bool
    carrier_unchanged: bool
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class StructuralizerZeroPlaneFrame:
    """A named, source-address-bound zero origin and signed-permutation plane frame."""
    schema: str
    frame_address: str
    source_address_id: str
    zero_origin: Point3
    plane_name: str
    frame: RotationFrame
    physical_calibration_claimed: bool


def open_structuralizer_zero_plane(carrier: BCFloorAddress,
                                   zero_origin: Sequence[int] = (0, 0, 0),
                                   plane_name: str = "XY") -> StructuralizerZeroPlaneFrame:
    if not isinstance(carrier, BCFloorAddress):
        raise TypeError("full_floor_address_carrier_required")
    zero = _strict_point3(zero_origin)
    frames = dict(PLANE_FRAMES)
    if plane_name not in frames:
        raise ValueError("structuralizer_zero_plane_name_unknown")
    frame = frames[plane_name]
    body = {"schema":"BC-STRUCTURALIZER-ZERO-PLANE-FRAME-1", "source":carrier.address_id,
            "zero_origin":list(zero), "plane_name":plane_name,
            "permutation":list(frame.perm), "sign":list(frame.sign), "physical_calibration":False}
    frame_id = _sha256_text(_canonical_json(body))[:24]
    return StructuralizerZeroPlaneFrame("BC-STRUCTURALIZER-ZERO-PLANE-FRAME-1", frame_id,
        carrier.address_id, zero, plane_name, frame, False)


def reopen_structuralizer_zero_plane(carrier: BCFloorAddress,
                                     frame_packet: StructuralizerZeroPlaneFrame) -> dict[str, Any]:
    if not isinstance(frame_packet, StructuralizerZeroPlaneFrame):
        raise TypeError("structuralizer_zero_plane_frame_required")
    if carrier.address_id != frame_packet.source_address_id:
        raise ValueError("structuralizer_zero_plane_source_address_mismatch")
    rebuilt = open_structuralizer_zero_plane(carrier, frame_packet.zero_origin, frame_packet.plane_name)
    if rebuilt != frame_packet:
        raise ValueError("structuralizer_zero_plane_rebuild_mismatch")
    return {"schema":"BC-STRUCTURALIZER-ZERO-PLANE-REOPEN-1", "pass":True,
            "frame_address":frame_packet.frame_address, "source_address_id":carrier.address_id,
            "plane_name":frame_packet.plane_name, "zero_origin":frame_packet.zero_origin,
            "physical_calibration_claimed":False, "authoritative_carrier_mutated":False}


def build_six_plane_perspective(carrier: BCFloorAddress,
                                points: Sequence[Sequence[int]]) -> SixPlanePerspectivePacket:
    """Create six source-bound views; all depth residuals permit exact lift-back."""
    if not isinstance(carrier, BCFloorAddress):
        raise TypeError("full_floor_address_carrier_required")
    clean_points=tuple(_strict_point3(point) for point in points)
    if not clean_points:
        raise ValueError("perspective_requires_at_least_one_point")
    source_id=carrier.address_id
    point_digest=_points_digest(clean_points)
    metrics=_pairwise_squared_distances(clean_points)
    views=[]
    for plane_name, frame in PLANE_FRAMES:
        transformed=tuple(_frame_point_local(frame,point) for point in clean_points)
        projected=tuple((point[0],point[1]) for point in transformed)
        depths=tuple(point[2] for point in transformed)
        lifted=tuple(_frame_point_global(frame,(projected[i][0],projected[i][1],depths[i]))
                     for i in range(len(clean_points)))
        lifted_metrics=_pairwise_squared_distances(lifted)
        lift_pass=lifted==clean_points
        metric_pass=lifted_metrics==metrics
        body={"schema":"BC-SIX-PLANE-VIEW-1", "source":source_id,
              "points":point_digest, "plane":plane_name, "frame":frame.as_dict(),
              "projected":[list(p) for p in projected], "depth":list(depths),
              "metric":[list(row) for row in metrics], "lifted":[list(p) for p in lifted]}
        view_id=_sha256_text(_canonical_json(body))[:24]
        views.append(SixPlaneView("BC-SIX-PLANE-VIEW-1",plane_name,view_id,source_id,point_digest,
            frame,projected,depths,lifted,metrics,lifted_metrics,lift_pass,metric_pass))
    packet_body={"schema":"BC-SIX-PLANE-PERSPECTIVE-1","source":source_id,
                 "points":point_digest,"plane_order":list(PLANE_VIEW_ORDER),
                 "views":[v.view_address for v in views]}
    packet_id=_sha256_text(_canonical_json(packet_body))[:24]
    return SixPlanePerspectivePacket("BC-SIX-PLANE-PERSPECTIVE-1",packet_id,source_id,point_digest,
        len(clean_points),PLANE_VIEW_ORDER,metrics,tuple(views),False)


def reopen_six_plane_perspective(carrier: BCFloorAddress,
                                 points: Sequence[Sequence[int]],
                                 packet: SixPlanePerspectivePacket) -> SixPlaneReopenWitness:
    """Rebuild from source carrier/input points and reject address or payload drift."""
    if not isinstance(packet,SixPlanePerspectivePacket):
        raise TypeError("six_plane_packet_required")
    if not isinstance(carrier,BCFloorAddress):
        raise TypeError("full_floor_address_carrier_required")
    if packet.source_address_id != carrier.address_id:
        raise ValueError("perspective_carrier_address_mismatch")
    clean_points=tuple(_strict_point3(point) for point in points)
    digest=_points_digest(clean_points)
    if packet.source_points_digest != digest:
        raise ValueError("perspective_source_points_mismatch")
    rebuilt=build_six_plane_perspective(carrier,clean_points)
    if rebuilt.packet_address != packet.packet_address or rebuilt.views != packet.views:
        raise ValueError("perspective_packet_rebuild_mismatch")
    lift_pass=all(view.exact_lift_pass for view in rebuilt.views)
    metric_pass=all(view.metric_preserved for view in rebuilt.views)
    unresolved=[]
    if not lift_pass: unresolved.append("exact_lift_mismatch")
    if not metric_pass: unresolved.append("source_metric_mismatch")
    return SixPlaneReopenWitness("BC-SIX-PLANE-REOPEN-1",not unresolved,carrier.address_id,
        packet.packet_address,len(rebuilt.views),lift_pass,metric_pass,
        carrier.address_id==packet.source_address_id and not packet.authoritative_carrier_mutated,
        tuple(unresolved))


# ---------------------------------------------------------------------------
# Two-of-three point solving and relative hallway copies.  The missing point is
# only determined once the caller declares ordered_equal_step; this does not
# pretend that two arbitrary points uniquely determine an unconstrained third.
# ---------------------------------------------------------------------------
def _point3_sub(a: Point3, b: Point3) -> Point3:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _point3_add(a: Point3, b: Point3) -> Point3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def _derive_ordered_equal_step(known: Mapping[int, Point3], missing_index: int) -> tuple[tuple[Point3, Point3, Point3], Point3]:
    """Return P0/P1/P2 and exact unit step; integer midpoint closure is mandatory."""
    if missing_index == 2:
        p0, p1 = known[0], known[1]
        step = _point3_sub(p1, p0)
        p2 = _point3_add(p1, step)
    elif missing_index == 0:
        p1, p2 = known[1], known[2]
        step = _point3_sub(p2, p1)
        p0 = _point3_sub(p1, step)
    elif missing_index == 1:
        p0, p2 = known[0], known[2]
        doubled = _point3_sub(p2, p0)
        if any(component % 2 != 0 for component in doubled):
            raise ValueError("three_point_midpoint_not_exact_integer")
        step = tuple(component // 2 for component in doubled)
        p1 = _point3_add(p0, step)
    else:
        raise ValueError("three_point_missing_index_out_of_range")
    return (p0, p1, p2), step


@dataclass(frozen=True)
class ThreePointDifferenceSolution:
    schema: str
    solution_address: str
    source_address_id: str
    zero_plane_frame: StructuralizerZeroPlaneFrame
    zero_origin: Point3
    plane_name: str
    known_points: tuple[tuple[int, Point3], ...]
    missing_index: int
    relation_rule: str
    frame_points: tuple[Point3, Point3, Point3]
    world_points: tuple[Point3, Point3, Point3]
    step_delta: Point3
    plane_roundtrips: tuple[tuple[str, Point3, bool], ...]
    perspective_packet: SixPlanePerspectivePacket
    authoritative_carrier_mutated: bool
    source_state_mutated: bool


def solve_three_point_difference(carrier: BCFloorAddress,
                                 known_points: Mapping[int, Sequence[int]],
                                 missing_index: int,
                                 zero_origin: Sequence[int] = (0, 0, 0),
                                 plane_name: str = "XY",
                                 zero_plane: StructuralizerZeroPlaneFrame | None = None) -> ThreePointDifferenceSolution:
    """Solve the unfilled slot of P0→P1→P2 under an explicit equal-step rule."""
    if not isinstance(carrier, BCFloorAddress):
        raise TypeError("full_floor_address_carrier_required")
    if not isinstance(known_points, Mapping):
        raise TypeError("known_three_point_mapping_required")
    if type(missing_index) is not int or missing_index not in (0, 1, 2):
        raise ValueError("three_point_missing_index_out_of_range")
    if zero_plane is None:
        zero_frame = open_structuralizer_zero_plane(carrier, zero_origin, plane_name)
    else:
        reopen_structuralizer_zero_plane(carrier, zero_plane)
        zero_frame = zero_plane
    clean_zero = zero_frame.zero_origin
    plane_name = zero_frame.plane_name
    expected_keys = {0, 1, 2} - {missing_index}
    if any(type(key) is not int for key in known_points) or set(known_points) != expected_keys:
        raise ValueError("three_point_requires_exactly_the_other_two_indexed_points")
    clean_known = {key: _strict_point3(value) for key, value in known_points.items()}
    frame = zero_frame.frame
    known_local = {idx: _frame_point_local(frame, _point3_sub(point, clean_zero))
                   for idx, point in clean_known.items()}
    local_points, step = _derive_ordered_equal_step(known_local, missing_index)
    world_points = tuple(_point3_add(clean_zero, _frame_point_global(frame, point)) for point in local_points)
    roundtrips = []
    for other_name, other_frame in PLANE_FRAMES:
        local_known_other = {idx: _frame_point_local(other_frame, _point3_sub(point, clean_zero))
                             for idx, point in clean_known.items()}
        solved_other, _other_step = _derive_ordered_equal_step(local_known_other, missing_index)
        inferred_world = _point3_add(clean_zero, _frame_point_global(other_frame, solved_other[missing_index]))
        roundtrips.append((other_name, inferred_world, inferred_world == world_points[missing_index]))
    if not all(row[2] for row in roundtrips):
        raise ValueError("three_point_six_plane_roundtrip_disagreement")
    packet = build_six_plane_perspective(carrier, world_points)
    body = {"schema":"BC-STRUCTURALIZER-THREE-POINT-DIFFERENCE-1", "source":carrier.address_id,
            "zero_plane_frame":zero_frame.frame_address, "zero":list(clean_zero), "plane":plane_name,
            "known":[[idx,list(point)] for idx,point in sorted(clean_known.items())],
            "missing":missing_index, "rule":"ordered_equal_step",
            "frame_points":[list(p) for p in local_points], "world_points":[list(p) for p in world_points],
            "step":list(step), "roundtrips":[[name,list(point),ok] for name,point,ok in roundtrips],
            "perspective":packet.packet_address}
    solution_id = _sha256_text(_canonical_json(body))[:24]
    return ThreePointDifferenceSolution("BC-STRUCTURALIZER-THREE-POINT-DIFFERENCE-1", solution_id,
        carrier.address_id, zero_frame, clean_zero, plane_name, tuple(sorted(clean_known.items())), missing_index,
        "ordered_equal_step", local_points, world_points, step, tuple(roundtrips), packet, False, False)


def reopen_three_point_difference(carrier: BCFloorAddress,
                                  solution: ThreePointDifferenceSolution) -> dict[str, Any]:
    if not isinstance(solution, ThreePointDifferenceSolution):
        raise TypeError("three_point_difference_solution_required")
    if not isinstance(carrier, BCFloorAddress) or carrier.address_id != solution.source_address_id:
        raise ValueError("three_point_solution_source_address_mismatch")
    reopen_structuralizer_zero_plane(carrier, solution.zero_plane_frame)
    rebuilt = solve_three_point_difference(carrier, dict(solution.known_points), solution.missing_index,
                                           zero_plane=solution.zero_plane_frame)
    if rebuilt != solution:
        raise ValueError("three_point_solution_rebuild_mismatch")
    perspective_witness = reopen_six_plane_perspective(carrier, solution.world_points, solution.perspective_packet)
    if not perspective_witness.pass_all:
        raise ValueError("three_point_solution_perspective_reopen_failed")
    return {"schema":"BC-STRUCTURALIZER-THREE-POINT-REOPEN-1", "pass":True,
            "solution_address":solution.solution_address, "source_address_id":carrier.address_id,
            "missing_index":solution.missing_index, "derived_point":solution.world_points[solution.missing_index],
            "zero_plane_frame_address":solution.zero_plane_frame.frame_address,
            "plane_roundtrips":len(solution.plane_roundtrips), "all_plane_roundtrips_pass":all(r[2] for r in solution.plane_roundtrips),
            "perspective_reopen_pass":perspective_witness.pass_all, "authoritative_carrier_mutated":False,
            "source_state_mutated":False}


@dataclass(frozen=True)
class ThreePointHallwayCopy:
    schema: str
    copy_address: str
    source_solution_address: str
    source_address_id: str
    target_address_id: str
    source_zero_origin: Point3
    target_zero_origin: Point3
    source_plane_name: str
    target_plane_name: str
    source_zero_plane_frame: StructuralizerZeroPlaneFrame
    target_zero_plane_frame: StructuralizerZeroPlaneFrame
    transferred_frame_points: tuple[Point3, Point3, Point3]
    copied_world_points: tuple[Point3, Point3, Point3]
    source_step_delta: Point3
    target_step_delta: Point3
    target_perspective_packet: SixPlanePerspectivePacket
    relation_preserved: bool
    source_authoritative_carrier_mutated: bool
    target_authoritative_carrier_mutated: bool


def copy_three_point_hallway(source_carrier: BCFloorAddress,
                             solution: ThreePointDifferenceSolution,
                             target_carrier: BCFloorAddress,
                             target_zero_origin: Sequence[int],
                             target_plane_name: str | None = None) -> ThreePointHallwayCopy:
    """Copy relative geometry into a separately addressed target frame; never copy address state."""
    reopen_three_point_difference(source_carrier, solution)
    if not isinstance(target_carrier, BCFloorAddress):
        raise TypeError("target_full_floor_address_carrier_required")
    target_zero = _strict_point3(target_zero_origin)
    target_name = solution.plane_name if target_plane_name is None else target_plane_name
    if target_name not in {name for name, _frame in PLANE_FRAMES}:
        raise ValueError("hallway_target_plane_name_unknown")
    target_zero_frame = open_structuralizer_zero_plane(target_carrier, target_zero, target_name)
    target_frame = target_zero_frame.frame
    copied_world = tuple(_point3_add(target_zero, _frame_point_global(target_frame, local_point))
                         for local_point in solution.frame_points)
    target_local = tuple(_frame_point_local(target_frame, _point3_sub(point, target_zero)) for point in copied_world)
    source_relation = _point3_sub(solution.frame_points[1], solution.frame_points[0])
    target_relation = _point3_sub(target_local[1], target_local[0])
    step_again = _point3_sub(target_local[2], target_local[1])
    preserved = source_relation == target_relation == step_again == solution.step_delta
    if not preserved:
        raise ValueError("hallway_copy_relation_not_preserved")
    packet = build_six_plane_perspective(target_carrier, copied_world)
    body = {"schema":"BC-STRUCTURALIZER-THREE-POINT-HALLWAY-COPY-1",
            "source_solution":solution.solution_address, "source_root":source_carrier.address_id,
            "target_root":target_carrier.address_id, "source_zero":list(solution.zero_origin),
            "target_zero":list(target_zero), "source_plane":solution.plane_name, "target_plane":target_name,
            "source_zero_plane_frame":solution.zero_plane_frame.frame_address,
            "target_zero_plane_frame":target_zero_frame.frame_address,
            "relative_points":[list(p) for p in solution.frame_points], "world_points":[list(p) for p in copied_world],
            "step":list(solution.step_delta), "target_perspective":packet.packet_address, "relation_preserved":preserved}
    return ThreePointHallwayCopy("BC-STRUCTURALIZER-THREE-POINT-HALLWAY-COPY-1",
        _sha256_text(_canonical_json(body))[:24], solution.solution_address, source_carrier.address_id,
        target_carrier.address_id, solution.zero_origin, target_zero, solution.plane_name, target_name,
        solution.zero_plane_frame, target_zero_frame, solution.frame_points, copied_world,
        solution.step_delta, target_relation, packet, preserved, False, False)


def reopen_three_point_hallway_copy(source_carrier: BCFloorAddress,
                                    solution: ThreePointDifferenceSolution,
                                    target_carrier: BCFloorAddress,
                                    packet: ThreePointHallwayCopy) -> dict[str, Any]:
    if not isinstance(packet, ThreePointHallwayCopy):
        raise TypeError("three_point_hallway_copy_required")
    if packet.source_address_id != source_carrier.address_id or packet.target_address_id != target_carrier.address_id:
        raise ValueError("hallway_copy_root_binding_mismatch")
    reopen_structuralizer_zero_plane(source_carrier, packet.source_zero_plane_frame)
    reopen_structuralizer_zero_plane(target_carrier, packet.target_zero_plane_frame)
    rebuilt = copy_three_point_hallway(source_carrier, solution, target_carrier,
                                       packet.target_zero_origin, packet.target_plane_name)
    if rebuilt != packet:
        raise ValueError("hallway_copy_rebuild_mismatch")
    witness = reopen_six_plane_perspective(target_carrier, packet.copied_world_points, packet.target_perspective_packet)
    if not witness.pass_all:
        raise ValueError("hallway_copy_perspective_reopen_failed")
    return {"schema":"BC-STRUCTURALIZER-THREE-POINT-HALLWAY-REOPEN-1", "pass":True,
            "copy_address":packet.copy_address, "source_solution_address":solution.solution_address,
            "source_address_id":source_carrier.address_id, "target_address_id":target_carrier.address_id,
            "relation_preserved":packet.relation_preserved, "perspective_reopen_pass":witness.pass_all,
            "source_authoritative_carrier_mutated":False, "target_authoritative_carrier_mutated":False}


@dataclass(frozen=True)
class Lattice216:
    lane8: int = 0
    ternary27: tuple[int, int, int] = (0, 0, 0)

    def __post_init__(self) -> None:
        if type(self.lane8) is not int or self.lane8 not in range(8):
            raise ValueError("lattice_lane8_out_of_range")
        if len(self.ternary27) != 3 or any(type(d) is not int or d not in (0, 1, 2) for d in self.ternary27):
            raise ValueError("lattice_ternary27_must_have_three_trits")

    @property
    def group27(self) -> int:
        return self.ternary27[0] * 9 + self.ternary27[1] * 3 + self.ternary27[2]

    @property
    def corner_phase(self) -> tuple[int, int, int]:
        return octant_from_cube(self.lane8)

    @property
    def physical_coord6(self) -> tuple[int, int, int]:
        return tuple(2 * self.ternary27[a] + self.corner_phase[a] for a in range(3))

    @classmethod
    def from_factors(cls, group27: int, lane8: int) -> "Lattice216":
        if type(group27) is not int or group27 not in range(27):
            raise ValueError("lattice_group27_out_of_range")
        return cls(lane8, (group27 // 9, (group27 // 3) % 3, group27 % 3))

    @classmethod
    def from_physical_coord6(cls, coord: Sequence[int]) -> "Lattice216":
        if len(coord) != 3 or any(type(v) is not int or v not in range(6) for v in coord):
            raise ValueError("physical_coord6_out_of_range")
        ternary = tuple(v // 2 for v in coord)
        lane = cube_from_octant(tuple(v % 2 for v in coord))
        return cls(lane, ternary)

    @property
    def physical_index6(self) -> int:
        x, y, z = self.physical_coord6
        return (x * 6 + y) * 6 + z

    @property
    def physical_role(self) -> str:
        c = self.physical_coord6
        inside = sum(1 <= v <= 4 for v in c)
        return "core" if inside == 3 else "control" if inside == 2 else "translator"

    @property
    def core_slot(self) -> tuple[int, int] | None:
        if self.physical_role != "core":
            return None
        coord = self.physical_coord6
        sphere_bits = tuple((v - 1) // 2 for v in coord)
        inner_bits = tuple((v - 1) % 2 for v in coord)
        return cube_from_octant(sphere_bits), cube_from_octant(inner_bits)

    def move_physical(self, axis: int, direction: int) -> "Lattice216":
        if axis not in (0, 1, 2) or direction not in (-1, 1):
            raise ValueError("physical_216_move_invalid")
        c = list(self.physical_coord6); c[axis] += direction
        if c[axis] not in range(6):
            raise ValueError("physical_216_boundary")
        return Lattice216.from_physical_coord6(c)

    def advance_27(self, steps: int) -> tuple["Lattice216", int]:
        _strict_int(steps, "lattice27_steps")
        carry, group = divmod(self.group27 + steps, 27)
        return Lattice216.from_factors(group, self.lane8), carry

    def advance_lane(self, axis: str, quarters: int, direction: int = 1) -> "Lattice216":
        if axis not in AXES or type(direction) is not int or direction not in (-1, 1):
            raise ValueError("lane_rotation_invalid")
        _strict_int(quarters, "lane_quarters")
        perm = LANE8_PERMS[axis] if direction > 0 else LANE8_INV_PERMS[axis]
        lane = self.lane8
        for _ in range(quarters % 4):
            lane = perm[lane]
        return Lattice216(lane, self.ternary27)

    def as_dict(self) -> dict[str, Any]:
        return {"lane8": self.lane8, "ternary27": list(self.ternary27), "group27": self.group27,
                "physical_coord6": list(self.physical_coord6), "physical_index6": self.physical_index6,
                "physical_role": self.physical_role,
                "core_slot": None if self.core_slot is None else list(self.core_slot)}


@dataclass(frozen=True)
class RecursiveLevelState:
    box_pos: int = BOX_EMPTY
    side: int | None = None
    rotation_active: bool = False
    rotation_cube: int | None = None
    lattice216: Lattice216 | None = None

    def __post_init__(self) -> None:
        if type(self.box_pos) is not int or (self.box_pos not in range(9) and self.box_pos != BOX_EMPTY):
            raise ValueError("recursive_box_position_invalid")
        if self.side is not None and (type(self.side) is not int or self.side not in (0, 1)):
            raise ValueError("recursive_side_invalid")
        if self.box_pos == BOX_EMPTY and (self.side is not None or self.lattice216 is not None):
            raise ValueError("empty_recursive_box_cannot_carry_side_or_payload")
        if self.side is None and self.lattice216 is not None:
            raise ValueError("unselected_recursive_side_cannot_carry_payload")
        if type(self.rotation_active) is not bool:
            raise TypeError("recursive_rotation_active_must_be_bool")
        if self.rotation_cube is not None and (not self.rotation_active or type(self.rotation_cube) is not int or self.rotation_cube not in range(8)):
            raise ValueError("recursive_rotation_cube_invalid")

    @property
    def active(self) -> bool:
        return self.box_pos != BOX_EMPTY and self.side is not None

    @property
    def resolved(self) -> bool:
        return self.active and self.lattice216 is not None

    def as_dict(self) -> dict[str, Any]:
        return {"box_pos": self.box_pos, "side": self.side,
                "rotation": {"active": self.rotation_active, "cube": self.rotation_cube},
                "lattice216": None if self.lattice216 is None else self.lattice216.as_dict()}


# Exact prime-RPM lane mechanics migrated from the current purposeful warm source.
# The historic 3/5/7 rates are fixed address bindings, not physical RPM.
PHA_CORE_PRIME_LENSES = (3, 5, 7)
PHA_CORE_RATE_BINDINGS = ((3, 15), (5, 5), (7, 1))
PHA_PHASE_MODULUS = 504
PHA_CORE_GEAR_RETURN_TICKS = 7560
MAX_PRIME_RPM_LENSES = 64
MAX_ORDERED_PRIME_WORD = 256
MAX_PRIME_LENS_VALUE = (1 << 64) - 1
MAX_PRIME_RPM_MOMENTUM = 10**12


def _is_exact_prime_lens(value: Any) -> bool:
    """Deterministic exact primality for the bounded unsigned 64-bit lens ROM."""
    if type(value) is not int or value < 2 or value > MAX_PRIME_LENS_VALUE:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value == prime:
            return True
        if value % prime == 0:
            return False
    d = value - 1
    power = 0
    while d % 2 == 0:
        d //= 2
        power += 1
    # Deterministic Miller-Rabin bases for all unsigned 64-bit integers.
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        base %= value
        if base == 0:
            continue
        residue = pow(base, d, value)
        if residue in (1, value - 1):
            continue
        for _ in range(power - 1):
            residue = (residue * residue) % value
            if residue == value - 1:
                break
        else:
            return False
    return True


def _integer_gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def _integer_lcm(a: int, b: int) -> int:
    if not a or not b:
        return 0
    return abs((a // _integer_gcd(a, b)) * b)


@dataclass(frozen=True)
class PrimeRPMAddress:
    """Exact address of ordered prime lanes, rates, modulus and absolute positions."""
    prime_lenses: tuple[int, ...]
    rate_bindings: tuple[tuple[int, int], ...]
    phase_modulus: int
    positions: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        primes = tuple(self.prime_lenses)
        rates = tuple(tuple(row) for row in self.rate_bindings)
        positions = tuple(tuple(row) for row in self.positions)
        if not primes or len(primes) > MAX_PRIME_RPM_LENSES:
            raise ValueError("prime_rpm_lens_count_out_of_range")
        if any(not _is_exact_prime_lens(p) for p in primes):
            raise ValueError("prime_rpm_lenses_must_be_exact_prime_integers_within_uint64")
        if len(set(primes)) != len(primes):
            raise ValueError("prime_rpm_duplicate_lens")
        if type(self.phase_modulus) is not int or self.phase_modulus < 2:
            raise ValueError("prime_rpm_phase_modulus_must_be_exact_integer_at_least_2")
        if len(rates) != len(primes) or any(len(row) != 2 for row in rates):
            raise ValueError("prime_rpm_rate_binding_order_must_match_lenses")
        if tuple(row[0] for row in rates) != primes:
            raise ValueError("prime_rpm_rate_binding_order_must_match_lenses")
        if any(type(row[0]) is not int or type(row[1]) is not int or row[1] <= 0 for row in rates):
            raise ValueError("prime_rpm_rates_must_be_positive_exact_integer_bindings")
        core = dict(PHA_CORE_RATE_BINDINGS)
        for prime, rate in rates:
            if prime in core and rate != core[prime]:
                raise ValueError("prime_rpm_canonical_core_rate_override_forbidden")
        if len(positions) != len(primes) or tuple(row[0] for row in positions) != primes:
            raise ValueError("prime_rpm_position_order_must_match_lenses")
        if any(len(row) != 2 or type(row[0]) is not int or type(row[1]) is not int for row in positions):
            raise ValueError("prime_rpm_positions_must_be_exact_integer_bindings")

    @property
    def address_id(self) -> str:
        return _sha256_text(_canonical_json(self.as_dict(include_id=False)))[:24]

    @property
    def position_map(self) -> dict[int, int]:
        return dict(self.positions)

    @property
    def rate_map(self) -> dict[int, int]:
        return dict(self.rate_bindings)

    def as_dict(self, include_id: bool = True) -> dict[str, Any]:
        body = {"schema":"BC-PRIME-RPM-ADDRESS-1", "prime_lenses":list(self.prime_lenses),
                "rate_bindings":[list(row) for row in self.rate_bindings],
                "phase_modulus":self.phase_modulus, "positions":[list(row) for row in self.positions],
                "physical_rpm_calibrated":False}
        if include_id:
            body["address_id"] = self.address_id
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PrimeRPMAddress":
        if value.get("schema") != "BC-PRIME-RPM-ADDRESS-1":
            raise ValueError("prime_rpm_address_schema_required")
        result = cls(tuple(value["prime_lenses"]), tuple(tuple(row) for row in value["rate_bindings"]),
                     value["phase_modulus"], tuple(tuple(row) for row in value["positions"]))
        if value.get("address_id") not in (None, result.address_id):
            raise ValueError("prime_rpm_address_id_mismatch")
        if value.get("physical_rpm_calibrated") is not False:
            raise ValueError("prime_rpm_physical_calibration_must_remain_explicit")
        return result


@dataclass(frozen=True)
class PrimeRPMOpenResult:
    schema: str
    parent_address_id: str
    mode: str
    address: PrimeRPMAddress | None
    requested_prime_lenses: tuple[int, ...]
    bound_rate_lenses: tuple[int, ...]
    unresolved_prime_lenses: tuple[int, ...]
    dependency_cone: Mapping[str, Any]
    reason: str | None
    state_mutation: bool = False
    glyph_admission: bool = False
    physical_rpm_calibrated: bool = False

    @property
    def pass_all(self) -> bool:
        return self.mode == "opened" and self.address is not None and not self.unresolved_prime_lenses


@dataclass(frozen=True)
class PrimeRPMTransition:
    schema: str
    before_address_id: str
    after_address: PrimeRPMAddress | None
    mode: str
    momentum_ticks: int
    ordered_word: tuple[int, ...]
    step_trace: tuple[Mapping[str, Any], ...]
    lane_transitions: tuple[Mapping[str, Any], ...]
    modular_lane_return_period_packets: int | None
    target_relation: Mapping[str, Any]
    witness: Mapping[str, Any]
    transition_address: str
    reason: str | None = None

    @property
    def pass_all(self) -> bool:
        return self.mode == "opened" and self.after_address is not None and all(self.witness.values())


@dataclass(frozen=True)
class BCFloorAddress:
    """One authoritative typed address, including optional coupled 504-head state."""
    pointer_width: int = 9
    pointer_state: int | None = None
    surface: RotationSurface = field(default_factory=RotationSurface)
    lattice216: Lattice216 | None = None
    levels: tuple[RecursiveLevelState, ...] = ()
    prime_harmonic: PrimeHarmonicAddress | None = None
    prime_rpm: PrimeRPMAddress | None = None

    def __post_init__(self) -> None:
        if self.pointer_width not in (9, 27, 81):
            raise ValueError("pointer_width_must_be_9_27_or_81")
        if self.pointer_state is not None and (type(self.pointer_state) is not int or self.pointer_state not in range(self.pointer_width)):
            raise ValueError("pointer_state_out_of_range")
        if not isinstance(self.surface, RotationSurface):
            raise TypeError("surface_must_be_rotation_surface")
        if self.lattice216 is not None and not isinstance(self.lattice216, Lattice216):
            raise TypeError("lattice216_must_be_typed_address_or_none")
        if any(not isinstance(l, RecursiveLevelState) for l in self.levels):
            raise TypeError("levels_must_be_typed_recursive_level_states")
        if self.prime_harmonic is not None and not isinstance(self.prime_harmonic, PrimeHarmonicAddress):
            raise TypeError("prime_harmonic_must_be_typed_address_or_none")
        if self.prime_rpm is not None and not isinstance(self.prime_rpm, PrimeRPMAddress):
            raise TypeError("prime_rpm_must_be_typed_address_or_none")

    @property
    def address_id(self) -> str:
        return _sha256_text(_canonical_json(self.as_dict()))[:24]

    def as_dict(self) -> dict[str, Any]:
        return {"schema": "BC-FLOOR-ADDRESS-4", "pointer": {"width": self.pointer_width, "state": self.pointer_state},
                "surface": self.surface.as_dict(),
                "lattice216": None if self.lattice216 is None else self.lattice216.as_dict(),
                "levels": [level.as_dict() for level in self.levels],
                "prime_harmonic": None if self.prime_harmonic is None else self.prime_harmonic.as_dict(),
                "prime_rpm": None if self.prime_rpm is None else self.prime_rpm.as_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BCFloorAddress":
        p = value["pointer"]; surf = value["surface"]
        pages = tuple(FloorPage(str(x["axis"]), int(x["box"]), int(x["state"])) for x in surf["pages"])
        frame = RotationFrame(tuple(surf["frame"]["perm"]), tuple(surf["frame"]["sign"]))
        surface = RotationSurface(bool(surf["active"]), tuple(surf["octant"]), pages, tuple(surf["fine"]), tuple(surf["radices"]), frame)
        def lat(item: Any) -> Lattice216 | None:
            return None if item is None else Lattice216(int(item["lane8"]), tuple(item["ternary27"]))
        levels = tuple(RecursiveLevelState(int(x["box_pos"]), x["side"], bool(x["rotation"]["active"]),
                                           x["rotation"]["cube"], lat(x["lattice216"])) for x in value["levels"])
        h = value.get("prime_harmonic")
        harmonic = None if h is None else PrimeHarmonicAddress(int(h["head"]), int(h["reference_head"]),
            int(h["winding"]), tuple(h["aperture_prefix"]))
        rpm_value = value.get("prime_rpm")
        rpm = None if rpm_value is None else PrimeRPMAddress.from_dict(rpm_value)
        return cls(int(p["width"]), p["state"], surface, lat(value["lattice216"]), levels, harmonic, rpm)


def open_prime_rpm_address(parent: BCFloorAddress, prime_lenses: Sequence[int] = PHA_CORE_PRIME_LENSES,
                           rpm_rates: Mapping[int, int] | None = None, phase_modulus: int = PHA_PHASE_MODULUS,
                           phase: int = 0, start_positions: Sequence[int] | Mapping[int, int] | None = None) -> PrimeRPMOpenResult:
    """Resolve an explicit prime/RPM lane address; missing higher rates stay residuals."""
    if not isinstance(parent, BCFloorAddress):
        raise TypeError("prime_rpm_parent_full_address_required")
    def result(mode: str, primes: tuple[int, ...], bound: tuple[int, ...] = (), missing: tuple[int, ...] = (),
               cone: Mapping[str, Any] | None = None, address: PrimeRPMAddress | None = None,
               reason: str | None = None) -> PrimeRPMOpenResult:
        return PrimeRPMOpenResult("BC-PRIME-RPM-OPEN-1", parent.address_id, mode, address, primes,
            bound, missing, dict(cone or {}), reason)
    if not isinstance(prime_lenses, (tuple, list)) or not prime_lenses or len(prime_lenses) > MAX_PRIME_RPM_LENSES:
        return result("hard_fault", (), reason="prime_lenses_must_be_nonempty_bounded_ordered_sequence")
    primes = tuple(prime_lenses)
    if any(not _is_exact_prime_lens(p) for p in primes):
        return result("hard_fault", primes, reason="every_prime_lens_must_be_exact_prime_within_uint64")
    if len(set(primes)) != len(primes):
        return result("hard_fault", primes, reason="duplicate_prime_lens")
    if type(phase_modulus) is not int or phase_modulus < 2:
        return result("hard_fault", primes, reason="phase_modulus_must_be_exact_integer_at_least_2")
    if type(phase) is not int:
        return result("hard_fault", primes, reason="phase_must_be_exact_integer")
    raw_rates = {} if rpm_rates is None else rpm_rates
    if not isinstance(raw_rates, Mapping):
        return result("hard_fault", primes, reason="rpm_rates_must_be_mapping")
    supplied_rates: dict[int, int] = {}
    for raw_prime, raw_rate in raw_rates.items():
        if type(raw_prime) is not int:
            return result("hard_fault", primes, reason="rpm_rate_key_must_be_canonical_exact_integer")
        if raw_prime not in primes:
            return result("hard_fault", primes, reason=f"rate_binding_for_unrequested_prime:{raw_prime}")
        if type(raw_rate) is not int or raw_rate <= 0:
            return result("hard_fault", primes, reason=f"rpm_rate_must_be_positive_exact_integer:{raw_prime}")
        core_map = dict(PHA_CORE_RATE_BINDINGS)
        if raw_prime in core_map and raw_rate != core_map[raw_prime]:
            return result("hard_fault", primes, reason=f"canonical_core_rate_override_forbidden:{raw_prime}")
        supplied_rates[raw_prime] = raw_rate
    rates = {prime: dict(PHA_CORE_RATE_BINDINGS)[prime] for prime in primes if prime in dict(PHA_CORE_RATE_BINDINGS)}
    rates.update(supplied_rates)
    missing = tuple(prime for prime in primes if prime not in rates)
    cone = {"schema":"BC-PRIME-RPM-DEPENDENCY-CONE-1", "root_address_id":parent.address_id,
            "required_capability":"BC.PRIME.RPM.OPEN", "base_prime_lenses":PHA_CORE_PRIME_LENSES,
            "base_rate_bindings":PHA_CORE_RATE_BINDINGS, "requested_prime_lenses":primes,
            "bound_rate_lenses":tuple(prime for prime in primes if prime in rates),
            "unresolved_prime_lenses":missing,
            "status":"OPEN_MISSING_RATE_BINDING" if missing else "RATE_BINDINGS_CLOSED",
            "physical_rpm_calibrated":False, "semantic_or_physical_equivalence_certified":False}
    if missing:
        return result("residual", primes, tuple(prime for prime in primes if prime in rates), missing,
                      cone, reason="higher_prime_lanes_need_explicit_rate_bindings")
    if start_positions is None:
        starts = {prime: phase for prime in primes}
    elif isinstance(start_positions, (tuple, list)):
        if len(start_positions) != len(primes) or any(type(x) is not int for x in start_positions):
            return result("hard_fault", primes, reason="start_positions_must_match_lenses_with_exact_integers")
        starts = dict(zip(primes, start_positions))
    elif isinstance(start_positions, Mapping):
        starts = {prime: phase for prime in primes}
        for prime, position in start_positions.items():
            if type(prime) is not int or prime not in primes:
                return result("hard_fault", primes, reason="start_position_key_must_be_requested_canonical_prime")
            if type(position) is not int:
                return result("hard_fault", primes, reason=f"start_position_must_be_exact_integer:{prime}")
            starts[prime] = position
    else:
        return result("hard_fault", primes, reason="start_positions_must_be_exact_sequence_or_mapping")
    state = PrimeRPMAddress(primes, tuple((prime, rates[prime]) for prime in primes), phase_modulus,
                            tuple((prime, starts[prime]) for prime in primes))
    return result("opened", primes, tuple(primes), (), {**cone, "status":"RATE_BINDINGS_CLOSED"}, state)


def prime_rpm_step(address: PrimeRPMAddress, momentum_ticks: int = 1,
                   ordered_word: Sequence[int] | None = None, target: int | None = None,
                   reference: int = 0, winding: int | None = None) -> PrimeRPMTransition:
    """Advance lane positions with exact integer rates; ordered symbols move only their own lane."""
    if not isinstance(address, PrimeRPMAddress):
        raise TypeError("prime_rpm_address_required")
    if type(momentum_ticks) is not int or abs(momentum_ticks) > MAX_PRIME_RPM_MOMENTUM:
        raise ValueError("momentum_ticks_must_be_bounded_exact_integer")
    if type(reference) is not int:
        raise ValueError("reference_must_be_exact_integer")
    if target is not None and type(target) is not int:
        raise ValueError("target_must_be_exact_integer")
    if winding is not None and type(winding) is not int:
        raise ValueError("winding_must_be_exact_integer")
    ordered_mode = ordered_word is not None
    word = () if ordered_word is None else tuple(ordered_word)
    if ordered_mode:
        if len(word) > MAX_ORDERED_PRIME_WORD:
            raise ValueError("ordered_word_exceeds_256_symbols")
        if any(type(symbol) is not int or symbol == 0 or abs(symbol) not in address.prime_lenses for symbol in word):
            raise ValueError("ordered_word_symbols_must_be_signed_requested_prime_lenses")
        word_sum = sum(word)
        if target is None:
            actual_winding = 0 if winding is None else winding
            actual_target = reference + word_sum + address.phase_modulus * actual_winding
        else:
            delta_target = target - reference
            remainder = delta_target - word_sum
            if remainder % address.phase_modulus:
                relation = {"requested":True, "reconstructs":False, "word_sum":word_sum,
                    "target":target, "reference":reference, "phase_modulus":address.phase_modulus,
                    "remainder":remainder, "supplied_winding":winding,
                    "status":"OPEN_SIGNED_TARGET_RELATION_RESIDUE"}
                body = {"schema":"BC-PRIME-RPM-TRANSITION-1", "before":address.address_id,
                        "mode":"residual", "momentum_ticks":momentum_ticks, "word":word,
                        "relation":relation, "reason":"ordered_word_does_not_reconstruct_target_modulo_phase_modulus"}
                tid = _sha256_text(_canonical_json(body))[:24]
                return PrimeRPMTransition("BC-PRIME-RPM-TRANSITION-1", address.address_id, None,
                    "residual", momentum_ticks, word, (), (), None, relation,
                    {"exact_integer_arithmetic":True, "ordered_word_reconstructs_target":False}, tid,
                    "ordered_word_does_not_reconstruct_target_modulo_phase_modulus")
            actual_winding = remainder // address.phase_modulus
            if winding is not None and winding != actual_winding:
                raise ValueError("supplied_winding_does_not_match_ordered_word")
            actual_target = target
        relation = {"requested":True, "word_sum":word_sum, "target":actual_target,
            "reference":reference, "phase_modulus":address.phase_modulus, "winding":actual_winding,
            "reconstructs":actual_target-reference == word_sum+address.phase_modulus*actual_winding,
            "status":"RECONSTRUCTED"}
    else:
        if target is not None:
            raise ValueError("target_relation_requires_ordered_word")
        actual_winding = 0 if winding is None else winding
        relation = {"requested":False, "reconstructs":None, "reference":reference,
                    "phase_modulus":address.phase_modulus, "winding":actual_winding}
    starts = address.position_map
    positions = dict(starts)
    rates = address.rate_map
    step_trace: list[dict[str, Any]] = []
    if ordered_mode:
        for index, symbol in enumerate(word):
            prime = abs(symbol)
            before = positions[prime]
            delta = (1 if symbol > 0 else -1) * rates[prime] * momentum_ticks
            positions[prime] += delta
            step_trace.append({"index":index, "symbol":symbol, "prime_lens":prime,
                "rate_binding":rates[prime], "momentum_ticks":momentum_ticks,
                "start_absolute_phase":before, "signed_phase_delta":delta,
                "end_absolute_phase":positions[prime],
                "end_phase_residue":positions[prime] % address.phase_modulus})
        operation_mode = "ordered_generator_word"
    else:
        for prime in address.prime_lenses:
            positions[prime] = starts[prime] + rates[prime] * momentum_ticks
        operation_mode = "simultaneous_rate_step"
    net_deltas = {prime:positions[prime]-starts[prime] for prime in address.prime_lenses}
    lane_rows=[]; periods=[]
    for prime in address.prime_lenses:
        delta=net_deltas[prime]
        period=address.phase_modulus // _integer_gcd(abs(delta), address.phase_modulus)
        periods.append(period)
        lane_rows.append({"prime_lens":prime, "rate_binding":rates[prime],
            "start_absolute_phase":starts[prime], "start_phase_residue":starts[prime] % address.phase_modulus,
            "signed_phase_delta":delta, "end_absolute_phase":positions[prime],
            "end_phase_residue":positions[prime] % address.phase_modulus,
            "phase_return_period_packets":period})
    joint_return=1
    for period in periods:
        joint_return=_integer_lcm(joint_return, period)
    end=PrimeRPMAddress(address.prime_lenses, address.rate_bindings, address.phase_modulus,
                        tuple((prime,positions[prime]) for prime in address.prime_lenses))
    witness={"exact_integer_arithmetic":True,
        "every_lane_reconstructs":all(row["end_absolute_phase"]==row["start_absolute_phase"]+row["signed_phase_delta"] for row in lane_rows),
        "residues_reconstruct":all(row["end_phase_residue"]==row["end_absolute_phase"] % address.phase_modulus for row in lane_rows),
        "return_period_positive":joint_return>0,
        "ordered_word_reconstructs_target":(not ordered_mode) or relation.get("reconstructs") is True,
        "ordered_step_trace_replays":(not ordered_mode) or all(row["end_absolute_phase"]==row["start_absolute_phase"]+row["signed_phase_delta"] for row in step_trace),
        "rate_bindings_preserved":end.rate_bindings==address.rate_bindings,
        "prime_order_preserved":end.prime_lenses==address.prime_lenses}
    body={"schema":"BC-PRIME-RPM-TRANSITION-1", "before":address.address_id,
          "after":end.address_id, "operation_mode":operation_mode, "momentum_ticks":momentum_ticks,
          "ordered_word":word, "step_trace":step_trace, "lane_transitions":lane_rows,
          "return_period":joint_return, "relation":relation, "witness":witness,
          "canonical_core_return_ticks":PHA_CORE_GEAR_RETURN_TICKS if address.prime_lenses==PHA_CORE_PRIME_LENSES and address.rate_bindings==PHA_CORE_RATE_BINDINGS and momentum_ticks==1 else None}
    transition_id=_sha256_text(_canonical_json(body))[:24]
    return PrimeRPMTransition("BC-PRIME-RPM-TRANSITION-1", address.address_id, end, "opened",
        momentum_ticks, word, tuple(step_trace), tuple(lane_rows), joint_return, relation,
        witness, transition_id)


def reopen_prime_rpm_transition(before: PrimeRPMAddress, transition: PrimeRPMTransition) -> dict[str, Any]:
    """Recompute a saved prime-RPM transition from its full lane state and request."""
    if not isinstance(before, PrimeRPMAddress) or not isinstance(transition, PrimeRPMTransition):
        raise TypeError("prime_rpm_state_and_transition_required")
    checks: dict[str, bool] = {"before_address_matches": before.address_id == transition.before_address_id,
                              "transition_was_opened": transition.mode == "opened"}
    replay = None
    if checks["before_address_matches"] and transition.mode == "opened":
        replay = prime_rpm_step(before, transition.momentum_ticks,
            transition.ordered_word if transition.target_relation.get("requested") else None,
            transition.target_relation.get("target") if transition.target_relation.get("requested") else None,
            transition.target_relation.get("reference", 0),
            transition.target_relation.get("winding") if transition.target_relation.get("requested") else None)
        checks.update({"after_address_matches": replay.after_address == transition.after_address,
            "transition_address_matches": replay.transition_address == transition.transition_address,
            "step_trace_matches": replay.step_trace == transition.step_trace,
            "lane_transitions_match": replay.lane_transitions == transition.lane_transitions,
            "witness_replays": replay.witness == transition.witness and all(replay.witness.values())})
    else:
        checks.update({"after_address_matches":False, "transition_address_matches":False,
                       "step_trace_matches":False, "lane_transitions_match":False, "witness_replays":False})
    return {"schema":"BC-PRIME-RPM-REOPEN-1", "pass":all(checks.values()), "checks":checks,
            "before_address_id":before.address_id, "transition_address":transition.transition_address,
            "reopened_address":None if replay is None else replay.after_address,
            "state_mutation":False, "glyph_admission":False, "physical_rpm_calibrated":False}


@dataclass(frozen=True)
class AddressOperation:
    kind: str
    axis: str | None = None
    ticks: int = 0
    steps: int = 0
    direction: int = 1
    depth: int = 0
    side: int | None = None
    box_pos: int = BOX_EMPTY
    active: bool | None = None
    cube: int | None = None
    radix: int = 0
    prime_lenses: tuple[int, ...] = ()
    rpm_rates: tuple[tuple[int, int], ...] = ()
    rpm_phase_modulus: int = PHA_PHASE_MODULUS
    rpm_phase: int = 0
    rpm_start_positions: tuple[int, ...] | None = None
    rpm_momentum_ticks: int = 1
    rpm_ordered_word: tuple[int, ...] | None = None
    rpm_target: int | None = None
    rpm_reference: int = 0
    rpm_winding: int | None = None


class FullAddressKernel:
    """Single clean executor for the migrated finite address-operation subset."""
    SUPPORTED = frozenset({"rotate_surface", "set_surface_rotation", "promote_shell", "demote_shell",
                           "move_lattice27", "move_lattice216", "move_level_lattice27",
                           "move_level_lattice216", "flip_level_side", "resolve_level_payload",
                           "lift_level", "descend_level", "rotate_lattice_lane",
                           "move_harmonic_heads", "cross_harmonic_floor_boundary",
                           "configure_prime_rpm", "advance_prime_rpm"})

    def apply(self, address: BCFloorAddress, op: AddressOperation) -> tuple[BCFloorAddress, dict[str, Any]]:
        if op.kind not in self.SUPPORTED:
            raise LookupError(f"unsupported_address_operation:{op.kind}")
        if op.kind == "rotate_surface":
            if op.axis not in AXES: raise ValueError("rotation_axis_invalid")
            after, detail = address.surface.apply_local_ticks(AXES.index(op.axis), _strict_int(op.ticks, "rotation_ticks"))
            return BCFloorAddress(address.pointer_width, address.pointer_state, after, address.lattice216, address.levels, address.prime_harmonic, address.prime_rpm), detail
        if op.kind == "set_surface_rotation":
            if op.active is None: raise ValueError("rotation_active_required")
            after = address.surface.set_active(op.active, op.cube)
            return BCFloorAddress(address.pointer_width, address.pointer_state, after, address.lattice216, address.levels, address.prime_harmonic, address.prime_rpm), {"active": op.active, "cube": op.cube}
        if op.kind in {"promote_shell", "demote_shell"}:
            if op.kind == "promote_shell": after = address.surface.promote(_strict_int(op.radix, "shell_radix"))
            else: after = address.surface.demote()
            return BCFloorAddress(address.pointer_width, address.pointer_state, after, address.lattice216, address.levels, address.prime_harmonic, address.prime_rpm), {"radices": list(after.radices), "fine": list(after.fine)}
        if op.kind in {"move_lattice27", "move_lattice216", "rotate_lattice_lane"}:
            if address.lattice216 is None: raise ValueError("root_lattice216_unresolved")
            if op.kind == "move_lattice27": nxt, carry = address.lattice216.advance_27(op.steps); detail = {"steps": op.steps, "carry": carry}
            elif op.kind == "move_lattice216":
                if op.axis not in AXES: raise ValueError("physical_axis_invalid")
                nxt = address.lattice216.move_physical(AXES.index(op.axis), op.direction); detail = {"axis": op.axis, "direction": op.direction}
            else:
                if op.axis not in AXES: raise ValueError("lane_axis_invalid")
                nxt = address.lattice216.advance_lane(op.axis, op.steps, op.direction); detail = {"axis": op.axis, "quarters": op.steps, "direction": op.direction}
            return BCFloorAddress(address.pointer_width, address.pointer_state, address.surface, nxt, address.levels, address.prime_harmonic, address.prime_rpm), detail
        if op.kind in {"move_level_lattice27", "move_level_lattice216", "flip_level_side", "resolve_level_payload"}:
            if type(op.depth) is not int or op.depth not in range(len(address.levels)):
                raise ValueError("recursive_depth_out_of_range")
            levels = list(address.levels); level = levels[op.depth]
            if op.kind == "flip_level_side":
                if not level.active: raise ValueError("cannot_flip_inactive_level")
                nxt = RecursiveLevelState(level.box_pos, 1 - level.side, level.rotation_active, level.rotation_cube, level.lattice216)
                detail = {"depth": op.depth, "side_before": level.side, "side_after": 1-level.side}
            elif op.kind == "resolve_level_payload":
                if not level.active: raise ValueError("cannot_resolve_inactive_level")
                chosen = level.side if op.side is None else op.side
                if chosen not in (0,1): raise ValueError("payload_side_required")
                nxt = RecursiveLevelState(level.box_pos, chosen, level.rotation_active, level.rotation_cube, Lattice216())
                detail = {"depth": op.depth, "side": chosen, "resolved": True}
            else:
                if level.lattice216 is None: raise ValueError("recursive_lattice216_unresolved")
                if op.kind == "move_level_lattice27":
                    lat, carry = level.lattice216.advance_27(op.steps); detail = {"depth": op.depth, "steps": op.steps, "carry": carry}
                else:
                    if op.axis not in AXES: raise ValueError("physical_axis_invalid")
                    lat = level.lattice216.move_physical(AXES.index(op.axis), op.direction); detail = {"depth": op.depth, "axis": op.axis, "direction": op.direction}
                nxt = RecursiveLevelState(level.box_pos, level.side, level.rotation_active, level.rotation_cube, lat)
            levels[op.depth] = nxt
            return BCFloorAddress(address.pointer_width, address.pointer_state, address.surface, address.lattice216, tuple(levels), address.prime_harmonic, address.prime_rpm), detail
        if op.kind == "lift_level":
            active = address.surface.active if op.active is None else op.active
            if op.active is not None and type(op.active) is not bool:
                raise TypeError("lift_rotation_active_must_be_bool")
            if active and op.cube is not None and (type(op.cube) is not int or op.cube not in range(8)):
                raise ValueError("lift_rotation_cube_invalid")
            if not active and op.cube is not None:
                raise ValueError("inactive_lift_cannot_specify_rotation_cube")
            level = RecursiveLevelState(op.box_pos, op.side, active, op.cube if active else None, None)
            return BCFloorAddress(address.pointer_width, address.pointer_state, address.surface, address.lattice216,
                                  address.levels + (level,), address.prime_harmonic, address.prime_rpm), {"new_depth": len(address.levels), "box_pos": op.box_pos, "side": op.side}
        if op.kind == "descend_level":
            if not address.levels: raise ValueError("cannot_descend_root_address")
            return BCFloorAddress(address.pointer_width, address.pointer_state, address.surface, address.lattice216,
                                  address.levels[:-1], address.prime_harmonic, address.prime_rpm), {"new_depth": len(address.levels)-1}
        if op.kind == "move_harmonic_heads":
            if address.prime_harmonic is None: raise ValueError("prime_harmonic_address_unresolved")
            result = harmonic_head_step(address.prime_harmonic, _strict_int(op.steps, "harmonic_head_steps"))
            end = BCFloorAddress(address.pointer_width, address.pointer_state, address.surface,
                                 address.lattice216, address.levels, result.address, address.prime_rpm)
            return end, {"head_before":address.prime_harmonic.head, "head_after":result.address.head,
                         "winding_before":address.prime_harmonic.winding, "winding_after":result.address.winding,
                         "requested_steps":op.steps, "harmonic_witness_schema":result.witness.schema,
                         "harmonic_witness_replay":result.witness.replay_pass}
        if op.kind == "cross_harmonic_floor_boundary":
            if address.prime_harmonic is None: raise ValueError("prime_harmonic_address_unresolved")
            if op.axis not in AXES: raise ValueError("harmonic_floor_axis_invalid")
            result = cross_harmonic_circle_boundary(address.prime_harmonic, address.surface,
                _strict_int(op.steps, "harmonic_alignment_repetitions"), AXES.index(op.axis))
            end = BCFloorAddress(address.pointer_width, address.pointer_state, result.floor_surface,
                                 address.lattice216, address.levels, result.harmonic_address, address.prime_rpm)
            before_align = result.witness.alignment_before
            after_align = result.witness.alignment_after
            return end, {"harmonic_head_steps":result.witness.head_steps,
                         "floor_circle_ticks":result.witness.floor_circle_ticks, "axis":op.axis,
                         "phase_relation_preserved":result.witness.phase_relation_preserved,
                         "phase_alignment_preserved":result.witness.phase_alignment_preserved,
                         "alignment_before":before_align.__dict__, "alignment_after":after_align.__dict__,
                         "harmonic_winding_after":result.harmonic_address.winding,
                         "claim_boundary":result.witness.claim_boundary}
        if op.kind == "configure_prime_rpm":
            rates = {}
            for row in op.rpm_rates:
                if not isinstance(row, (tuple, list)) or len(row) != 2 or type(row[0]) is not int or type(row[1]) is not int:
                    raise ValueError("prime_rpm_rate_bindings_must_be_prime_rate_integer_pairs")
                if row[0] in rates:
                    raise ValueError("prime_rpm_duplicate_rate_binding")
                rates[row[0]] = row[1]
            result = open_prime_rpm_address(address,
                prime_lenses=op.prime_lenses or PHA_CORE_PRIME_LENSES,
                rpm_rates=rates, phase_modulus=op.rpm_phase_modulus, phase=op.rpm_phase,
                start_positions=op.rpm_start_positions)
            if not result.pass_all or result.address is None:
                raise ValueError("prime_rpm_configuration_" + result.mode + ":" + str(result.reason))
            end = BCFloorAddress(address.pointer_width, address.pointer_state, address.surface,
                address.lattice216, address.levels, address.prime_harmonic, result.address)
            return end, {"prime_rpm_open_schema":result.schema, "prime_rpm_address_id":result.address.address_id,
                "rate_bindings":result.address.rate_bindings, "phase_modulus":result.address.phase_modulus,
                "parent_address_id":address.address_id, "dependency_cone":dict(result.dependency_cone),
                "physical_rpm_calibrated":False}
        if op.kind == "advance_prime_rpm":
            if address.prime_rpm is None:
                raise ValueError("prime_rpm_address_unresolved")
            transition = prime_rpm_step(address.prime_rpm, op.rpm_momentum_ticks,
                op.rpm_ordered_word, op.rpm_target, op.rpm_reference, op.rpm_winding)
            if not transition.pass_all or transition.after_address is None:
                raise ValueError("prime_rpm_transition_residual:" + str(transition.reason))
            end = BCFloorAddress(address.pointer_width, address.pointer_state, address.surface,
                address.lattice216, address.levels, address.prime_harmonic, transition.after_address)
            return end, {"prime_rpm_before":address.prime_rpm.address_id,
                "prime_rpm_after":transition.after_address.address_id,
                "prime_rpm_transition_address":transition.transition_address,
                "operation_mode":"ordered_generator_word" if op.rpm_ordered_word is not None else "simultaneous_rate_step",
                "momentum_ticks":op.rpm_momentum_ticks, "ordered_word":transition.ordered_word,
                "step_trace":tuple(dict(row) for row in transition.step_trace),
                "lane_transitions":tuple(dict(row) for row in transition.lane_transitions),
                "modular_lane_return_period_packets":transition.modular_lane_return_period_packets,
                "target_relation":dict(transition.target_relation), "witness":dict(transition.witness),
                "canonical_core_return_ticks":PHA_CORE_GEAR_RETURN_TICKS if address.prime_rpm.prime_lenses==PHA_CORE_PRIME_LENSES and address.prime_rpm.rate_bindings==PHA_CORE_RATE_BINDINGS and op.rpm_momentum_ticks==1 else None,
                "physical_rpm_calibrated":False}
        raise AssertionError("unreachable_operation_branch")

    def execute(self, start: BCFloorAddress, ops: Sequence[AddressOperation]) -> "FullAddressWitness":
        current = start; events = []
        for index, op in enumerate(ops):
            before = current.address_id
            current, detail = self.apply(current, op)
            events.append({"index": index, "kind": op.kind, "before": before, "after": current.address_id,
                           "operation": {k: v for k, v in op.__dict__.items()}, "detail": detail})
        delta = AddressDelta.between(start, current)
        replayed = delta.apply(start)
        unresolved = []
        if replayed.address_id != current.address_id: unresolved.append("delta_replay_mismatch")
        dependency_closed = True  # all typed operations returned without unresolved-child access
        return_closed = start.address_id == current.address_id
        witness_doc = {"schema":"BC-FULL-ADDRESS-WITNESS-3", "root":start.address_id, "end":current.address_id,
                       "events":events, "delta":delta.difference_address, "dependency_closed":dependency_closed,
                       "return_to_entry_closed":return_closed, "difference_replays":not unresolved,
                       "unresolved":unresolved}
        witness_id = _sha256_text(_canonical_json(witness_doc))[:24]
        return FullAddressWitness(start, current, tuple(events), delta,
                                  dependency_closed, return_closed, not unresolved, tuple(unresolved), witness_id)


def _path_get(obj: Any, path: Sequence[str | int]) -> Any:
    cur = obj
    for part in path: cur = cur[part]
    return cur


def _path_set(obj: Any, path: Sequence[str | int], value: Any) -> None:
    if not path: raise ValueError("empty_delta_path")
    cur = obj
    for part in path[:-1]: cur = cur[part]
    cur[path[-1]] = copy.deepcopy(value)


def _leaf_changes(before: Any, after: Any, path: tuple[str | int, ...] = ()) -> list[dict[str, Any]]:
    if type(before) is dict and type(after) is dict and before.keys() == after.keys():
        out = []
        for key in sorted(before): out.extend(_leaf_changes(before[key], after[key], path + (key,)))
        return out
    if type(before) is list and type(after) is list and len(before) == len(after):
        out = []
        for i, (a, b) in enumerate(zip(before, after)): out.extend(_leaf_changes(a, b, path + (i,)))
        return out
    if before == after and type(before) is type(after): return []
    return [{"path": list(path), "before": copy.deepcopy(before), "after": copy.deepcopy(after)}]


@dataclass(frozen=True)
class AddressDelta:
    schema: str
    parent_id: str
    end_id: str
    changes: tuple[dict[str, Any], ...]
    difference_address: str

    @classmethod
    def between(cls, start: BCFloorAddress, end: BCFloorAddress) -> "AddressDelta":
        changes = tuple(_leaf_changes(start.as_dict(), end.as_dict()))
        body = {"schema":"BC-ADDRESS-DELTA-3", "parent":start.address_id, "end":end.address_id, "changes":changes}
        return cls("BC-ADDRESS-DELTA-3", start.address_id, end.address_id, changes,
                   _sha256_text(_canonical_json(body))[:24])

    def apply(self, start: BCFloorAddress) -> BCFloorAddress:
        if start.address_id != self.parent_id: raise ValueError("delta_parent_address_mismatch")
        data = start.as_dict()
        for item in self.changes:
            path = tuple(item["path"])
            current = _path_get(data, path)
            if current != item["before"] or type(current) is not type(item["before"]):
                raise ValueError("delta_before_value_mismatch")
            _path_set(data, path, item["after"])
        end = BCFloorAddress.from_dict(data)
        if end.address_id != self.end_id: raise ValueError("delta_end_address_mismatch")
        return end


@dataclass(frozen=True)
class FullAddressWitness:
    start: BCFloorAddress
    end: BCFloorAddress
    events: tuple[dict[str, Any], ...]
    delta: AddressDelta
    dependency_closed: bool
    return_to_entry_closed: bool
    difference_replays: bool
    unresolved: tuple[str, ...]
    witness_id: str

    def replay(self, kernel: FullAddressKernel, ops: Sequence[AddressOperation]) -> bool:
        replay = kernel.execute(self.start, ops)
        return (replay.end.address_id == self.end.address_id and replay.delta.changes == self.delta.changes
                and replay.dependency_closed == self.dependency_closed
                and replay.return_to_entry_closed == self.return_to_entry_closed
                and replay.difference_replays == self.difference_replays)


FULL_ADDRESS_KERNEL = FullAddressKernel()


def full_address_witness(start: BCFloorAddress, ops: Sequence[AddressOperation]) -> FullAddressWitness:
    return FULL_ADDRESS_KERNEL.execute(start, ops)


# ---------------------------------------------------------------------------
# Distinct 216 apertures and reusable recursive depth-wave state cones.
# BOXES and CUBES share the number 216, not their identities or coordinates.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ApertureDescriptor:
    schema: str
    family: str
    cardinality: int
    factorization: tuple[int, ...]
    encoding: str
    meaning: str

    def __post_init__(self) -> None:
        if self.family not in {"box", "cube"}:
            raise ValueError("aperture_family_invalid")
        if type(self.cardinality) is not int or self.cardinality != 216:
            raise ValueError("this_clean_aperture_contract_requires_cardinality_216")
        if any(type(n) is not int or n < 1 for n in self.factorization):
            raise ValueError("aperture_factorization_invalid")
        product = 1
        for n in self.factorization:
            product *= n
        if product != self.cardinality:
            raise ValueError("aperture_factorization_product_mismatch")

    @property
    def address_id(self) -> str:
        return _sha256_text(_canonical_json(self.as_dict(include_id=False)))[:24]

    def as_dict(self, include_id: bool = True) -> dict[str, Any]:
        body = {"schema": self.schema, "family": self.family, "cardinality": self.cardinality,
                "factorization": list(self.factorization), "encoding": self.encoding, "meaning": self.meaning}
        if include_id:
            body["address_id"] = self.address_id
        return body


# The BOX aperture counts 8 octants x 3 axis pages per octant x 9 boxes per page.
# Each box separately has 9 occupied one-hot states plus its all-off state.
BOX_APERTURE_216 = ApertureDescriptor(
    "BC-APERTURE-216-1", "box", 216, (8, 3, 9), "octant × axis-page × box-position",
    "216 addressed floor boxes across 24 pages; local one-hot/all-off state is a separate coordinate")
# The CUBE aperture counts the 216 Lattice216 states: 8 lane states x 27 ternary states,
# equivalently a 6 x 6 x 6 physical-coordinate factorization. It is NOT the BOX address space.
CUBE_APERTURE_216 = ApertureDescriptor(
    "BC-APERTURE-216-1", "cube", 216, (6, 6, 6), "physical x × y × z; encoded by 8 lanes × 27 groups",
    "216 Lattice216 cube states with exact lane/ternary and 6×6×6 coordinate views")


def aperture_alignment_216() -> dict[str, Any]:
    body = {"schema": "BC-APERTURE-ALIGNMENT-216-1", "shared_cardinality": 216,
            "box_aperture": BOX_APERTURE_216.as_dict(), "cube_aperture": CUBE_APERTURE_216.as_dict(),
            "address_families_distinct": BOX_APERTURE_216.address_id != CUBE_APERTURE_216.address_id,
            "state_identity_equivalent": False,
            "permitted_claim": "same aperture cardinality only; positions require an explicit typed relation",
            "mapping_inferred_from_equal_cardinality": False}
    body["alignment_address"] = _sha256_text(_canonical_json(body))[:24]
    return body


@dataclass(frozen=True)
class FloorBoxAddress:
    """One global floor-box identity; its local state is separate from its box index."""
    octant_index: int
    axis_index: int
    box_index: int
    local_state: int = 9  # 0..8 occupied one-hot positions; 9 = all-off

    def __post_init__(self) -> None:
        if type(self.octant_index) is not int or self.octant_index not in range(8):
            raise ValueError("floor_box_octant_out_of_range")
        if type(self.axis_index) is not int or self.axis_index not in range(3):
            raise ValueError("floor_box_axis_out_of_range")
        if type(self.box_index) is not int or self.box_index not in range(9):
            raise ValueError("floor_box_position_out_of_range")
        if type(self.local_state) is not int or self.local_state not in range(10):
            raise ValueError("floor_box_state_out_of_range")

    @classmethod
    def from_factors(cls, octant_index: int, axis_index: int, box_index: int,
                     local_state: int = 9) -> "FloorBoxAddress":
        """Create a global 216-box position from (octant, axis page, box slot)."""
        return cls(octant_index, axis_index, box_index, local_state)

    @classmethod
    def from_surface(cls, surface: RotationSurface, axis: str) -> "FloorBoxAddress":
        if not isinstance(surface, RotationSurface):
            raise TypeError("rotation_surface_required")
        if axis not in AXES:
            raise ValueError("floor_box_axis_invalid")
        octant_index = cube_from_octant(surface.octant)
        page = surface.pages[AXES.index(axis)]
        return cls(octant_index, AXES.index(axis), page.box, page.state)

    @property
    def global_box_index(self) -> int:
        # Stable ordinal across all 8 x 3 x 9 box positions. It excludes local state.
        return (self.octant_index * 3 + self.axis_index) * 9 + self.box_index

    @property
    def one_hot_state(self) -> tuple[int, ...]:
        if self.local_state == 9:
            return (0,) * 9
        return tuple(1 if i == self.local_state else 0 for i in range(9))

    @property
    def address_id(self) -> str:
        return _sha256_text(_canonical_json(self.as_dict(include_id=False)))[:24]

    def as_dict(self, include_id: bool = True) -> dict[str, Any]:
        body = {"schema": "BC-FLOOR-BOX-ADDRESS-1", "aperture_address": BOX_APERTURE_216.address_id,
                "octant_index": self.octant_index, "axis_index": self.axis_index,
                "axis": AXES[self.axis_index], "box_index": self.box_index,
                "global_box_index": self.global_box_index, "local_state": self.local_state,
                "one_hot_state": list(self.one_hot_state), "all_off": self.local_state == 9}
        if include_id:
            body["address_id"] = self.address_id
        return body


@dataclass(frozen=True)
class RecursiveChildAddress:
    """Stable name/binding for one recursive level's box-side Lattice216 payload."""
    schema: str
    parent_address_id: str
    level_index: int
    recursion_depth: int
    box_slot_position: int
    side: int
    payload_address_id: str
    path: tuple[str | int, ...]
    box_aperture_address: str
    cube_aperture_address: str
    shared_aperture: int = 216

    @property
    def name(self) -> str:
        return f"levels[{self.level_index}].box[{self.box_slot_position}].side[{self.side}].lattice216"

    @property
    def address_id(self) -> str:
        return _sha256_text(_canonical_json(self.as_dict(include_id=False)))[:24]

    def as_dict(self, include_id: bool = True) -> dict[str, Any]:
        body = {"schema": self.schema, "parent_address_id": self.parent_address_id,
                "level_index": self.level_index, "recursion_depth": self.recursion_depth,
                "box_slot_position": self.box_slot_position, "side": self.side,
                "payload_address_id": self.payload_address_id, "path": list(self.path),
                "box_aperture_address": self.box_aperture_address,
                "cube_aperture_address": self.cube_aperture_address,
                "shared_aperture": self.shared_aperture,
                "box_address_scope": "recursive local slot 0..8; not a global 216-box ordinal",
                "cube_payload_scope": "one Lattice216 payload address in the separate cube aperture family",
                "aperture_families_are_distinct": self.box_aperture_address != self.cube_aperture_address}
        if include_id:
            body["address_id"] = self.address_id
        return body


def resolve_recursive_child_address(address: BCFloorAddress, level_index: int) -> RecursiveChildAddress:
    if not isinstance(address, BCFloorAddress):
        raise TypeError("full_floor_address_required")
    if type(level_index) is not int or level_index not in range(len(address.levels)):
        raise ValueError("recursive_child_level_out_of_range")
    level = address.levels[level_index]
    if not level.active:
        raise ValueError("recursive_child_box_side_unresolved")
    if level.lattice216 is None:
        raise ValueError("recursive_child_lattice216_payload_unresolved")
    payload_id = _sha256_text(_canonical_json({"schema":"BC-LATTICE216-PAYLOAD-1",
                                                "state":level.lattice216.as_dict()}))[:24]
    return RecursiveChildAddress("BC-RECURSIVE-CHILD-ADDRESS-1", address.address_id,
        level_index, level_index + 1, level.box_pos, int(level.side), payload_id,
        ("levels", level_index, "lattice216"), BOX_APERTURE_216.address_id,
        CUBE_APERTURE_216.address_id, 216)


@dataclass(frozen=True)
class DepthWaveNode:
    schema: str
    root_address_id: str
    child_address_id: str
    depth: int
    wave_distance: int
    source_path: tuple[str | int, ...]
    lattice: Lattice216
    state_address_id: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema":self.schema, "root_address_id":self.root_address_id,
                "child_address_id":self.child_address_id, "depth":self.depth,
                "wave_distance":self.wave_distance, "source_path":list(self.source_path),
                "lattice":self.lattice.as_dict(), "physical_coord6":list(self.lattice.physical_coord6),
                "physical_index6":self.lattice.physical_index6, "physical_role":self.lattice.physical_role,
                "state_address_id":self.state_address_id, "state_family":"cube_state"}


@dataclass(frozen=True)
class DepthWaveFrontier:
    schema: str
    root_address_id: str
    child_address_id: str
    depth: int
    from_state_address_id: str
    target_state_address_id: str
    target_physical_index6: int
    target_coord6: tuple[int, int, int]
    axis: str
    direction: int
    next_wave_distance: int

    def as_dict(self) -> dict[str, Any]:
        return {"schema":self.schema, "root_address_id":self.root_address_id,
                "child_address_id":self.child_address_id, "depth":self.depth,
                "from_state_address_id":self.from_state_address_id,
                "target_state_address_id":self.target_state_address_id,
                "target_physical_index6":self.target_physical_index6,
                "target_coord6":list(self.target_coord6), "axis":self.axis,
                "direction":self.direction, "next_wave_distance":self.next_wave_distance}


@dataclass(frozen=True)
class DepthWaveCone:
    schema: str
    root_address_id: str
    max_recursive_depth: int
    wave_radius: int
    target_child_address_id: str | None
    include_root_lattice: bool
    aperture_alignment_address: str
    child_addresses: tuple[RecursiveChildAddress, ...]
    nodes: tuple[DepthWaveNode, ...]
    frontier: tuple[DepthWaveFrontier, ...]
    unresolved: tuple[str, ...]
    dependency_closed: bool
    local_state_spaces_closed: bool
    cone_address: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema":self.schema, "root_address_id":self.root_address_id,
                "max_recursive_depth":self.max_recursive_depth, "wave_radius":self.wave_radius,
                "target_child_address_id":self.target_child_address_id,
                "include_root_lattice":self.include_root_lattice,
                "aperture_alignment_address":self.aperture_alignment_address,
                "apertures":{"box":BOX_APERTURE_216.as_dict(), "cube":CUBE_APERTURE_216.as_dict(),
                              "shared_cardinality":216, "identities_distinct":True},
                "child_addresses":[x.as_dict() for x in self.child_addresses],
                "nodes":[x.as_dict() for x in self.nodes], "frontier":[x.as_dict() for x in self.frontier],
                "unresolved":list(self.unresolved), "dependency_closed":self.dependency_closed,
                "local_state_spaces_closed":self.local_state_spaces_closed,
                "node_count":len(self.nodes), "frontier_count":len(self.frontier),
                "cone_address":self.cone_address,
                "consumer_ports":["input_proposal", "crown_view", "full_address_execution", "structuralizer_view_and_reopen", "self_feed_observation"],
                "effect":"read-only addressed state cone; no glyph admission or persistence"}


MAX_DEPTH_WAVE_NODES = 4096  # legacy per-expansion emergency ceiling
MAX_DEPTH_WAVE_RADIUS = 15  # maximum Manhattan radius in a 6×6×6 integer state lattice
MAX_DEPTH_WAVE_CONE_NODES = 4096  # strict aggregate ceiling across all seeds in one cone
MAX_DEPTH_WAVE_CONE_FRONTIER_EDGES = 8192  # strict aggregate frontier-edge ceiling
MAX_FRACTAL_LOCK_DEPTH = 64
MAX_FRACTAL_LOCK_FAMILIES = 12


def _depth_wave_state_id(root_id: str, child_id: str, lattice: Lattice216) -> str:
    return _sha256_text(_canonical_json({"schema":"BC-DEPTH-WAVE-STATE-1", "root":root_id,
                                         "child":child_id, "lattice":lattice.as_dict()}))[:24]


def _expand_lattice_wave(root_id: str, child_id: str, depth: int,
                         path: tuple[str | int, ...], center: Lattice216, radius: int
                         ) -> tuple[list[DepthWaveNode], list[DepthWaveFrontier], bool]:
    dist: dict[int, int] = {center.physical_index6: 0}
    by_index: dict[int, Lattice216] = {center.physical_index6: center}
    frontier: list[DepthWaveFrontier] = []
    queue: list[Lattice216] = [center]
    cursor = 0
    frontier_seen: set[tuple[str, int, int, str, int]] = set()
    while cursor < len(queue):
        current = queue[cursor]; cursor += 1
        current_index = current.physical_index6
        current_distance = dist[current_index]
        for axis_index, axis_name in enumerate(AXES):
            for direction in (-1, 1):
                try:
                    nxt = current.move_physical(axis_index, direction)
                except ValueError as exc:
                    if str(exc) == "physical_216_boundary":
                        continue
                    raise
                nxt_index = nxt.physical_index6
                if nxt_index in dist:
                    continue
                if current_distance < radius:
                    dist[nxt_index] = current_distance + 1
                    by_index[nxt_index] = nxt
                    queue.append(nxt)
                    if len(queue) > MAX_DEPTH_WAVE_NODES:
                        raise ValueError("depth_wave_node_budget_exceeded")
                else:
                    from_id = _depth_wave_state_id(root_id, child_id, current)
                    to_id = _depth_wave_state_id(root_id, child_id, nxt)
                    key = (from_id, nxt_index, current_distance + 1, axis_name, direction)
                    if key not in frontier_seen:
                        frontier_seen.add(key)
                        frontier.append(DepthWaveFrontier("BC-DEPTH-WAVE-FRONTIER-1", root_id,
                            child_id, depth, from_id, to_id, nxt_index, nxt.physical_coord6,
                            axis_name, direction, current_distance + 1))
    nodes = [DepthWaveNode("BC-DEPTH-WAVE-NODE-1", root_id, child_id, depth, dist[index], path,
                           by_index[index], _depth_wave_state_id(root_id, child_id, by_index[index]))
             for index in sorted(dist, key=lambda i: (dist[i], i))]
    closed = len(dist) == 216 and not frontier
    return nodes, frontier, closed


def open_depth_wave_cone(address: BCFloorAddress, max_recursive_depth: int = 1, wave_radius: int = 1,
                         target_child: RecursiveChildAddress | None = None,
                         include_root_lattice: bool = False) -> DepthWaveCone:
    """Open a bounded depth×wave cone without conflating box and cube apertures.

    `max_recursive_depth` counts depth 0 as the root lattice and depth 1 as
    `levels[0].lattice216`. `wave_radius` is a separate graph-distance bound
    inside each selected Lattice216 payload. Missing depth stays an explicit residual.
    """
    if not isinstance(address, BCFloorAddress): raise TypeError("full_floor_address_required")
    if type(max_recursive_depth) is not int or max_recursive_depth < 0 or max_recursive_depth > 64:
        raise ValueError("depth_wave_recursion_depth_out_of_range")
    if type(wave_radius) is not int or wave_radius < 0 or wave_radius > MAX_DEPTH_WAVE_RADIUS:
        raise ValueError("depth_wave_radius_out_of_range")
    if type(include_root_lattice) is not bool: raise TypeError("include_root_lattice_must_be_bool")
    if target_child is not None:
        if not isinstance(target_child, RecursiveChildAddress): raise TypeError("recursive_child_address_required")
        if target_child.parent_address_id != address.address_id:
            raise ValueError("depth_wave_child_parent_mismatch")
        if target_child.recursion_depth > max_recursive_depth:
            raise ValueError("depth_wave_target_beyond_depth_limit")
        rebuilt = resolve_recursive_child_address(address, target_child.level_index)
        if rebuilt != target_child:
            raise ValueError("depth_wave_child_binding_stale")
        selected = (target_child,)
    else:
        selected_list: list[RecursiveChildAddress] = []
        unresolved_pre: list[str] = []
        for index in range(min(max_recursive_depth, len(address.levels))):
            level = address.levels[index]
            if not level.active:
                unresolved_pre.append(f"recursive_level_{index}_box_or_side_unresolved")
                continue
            if level.lattice216 is None:
                unresolved_pre.append(f"recursive_level_{index}_payload_unresolved")
                continue
            selected_list.append(resolve_recursive_child_address(address, index))
        if max_recursive_depth > len(address.levels):
            for depth in range(len(address.levels) + 1, max_recursive_depth + 1):
                unresolved_pre.append(f"recursive_depth_{depth}_not_present")
        selected = tuple(selected_list)
    nodes: list[DepthWaveNode] = []
    frontier: list[DepthWaveFrontier] = []
    unresolved: list[str] = []
    if target_child is None:
        unresolved.extend(unresolved_pre)
    local_closed: list[bool] = []
    seeded = 0
    if include_root_lattice:
        if address.lattice216 is None:
            unresolved.append("root_lattice216_unresolved")
        else:
            child_id = "ROOT.LATTICE216:" + address.address_id
            n, f, closed = _expand_lattice_wave(address.address_id, child_id, 0, ("lattice216",),
                                                address.lattice216, wave_radius)
            nodes.extend(n); frontier.extend(f); local_closed.append(closed); seeded += 1
            if len(nodes) > MAX_DEPTH_WAVE_CONE_NODES or len(frontier) > MAX_DEPTH_WAVE_CONE_FRONTIER_EDGES:
                raise ValueError("depth_wave_aggregate_work_budget_exceeded")
    for child in selected:
        level = address.levels[child.level_index]
        if level.lattice216 is None:
            unresolved.append(f"{child.name}:payload_unresolved")
            continue
        n, f, closed = _expand_lattice_wave(address.address_id, child.address_id, child.recursion_depth,
                                            child.path, level.lattice216, wave_radius)
        nodes.extend(n); frontier.extend(f); local_closed.append(closed); seeded += 1
        if len(nodes) > MAX_DEPTH_WAVE_CONE_NODES or len(frontier) > MAX_DEPTH_WAVE_CONE_FRONTIER_EDGES:
            raise ValueError("depth_wave_aggregate_work_budget_exceeded")
    if not seeded:
        unresolved.append("depth_wave_has_no_resolved_seed_payload")
    # Stable sorting keeps receipts independent of traversal/merge timing.
    nodes.sort(key=lambda n: (n.depth, n.child_address_id, n.wave_distance, n.lattice.physical_index6))
    frontier.sort(key=lambda f: (f.depth, f.child_address_id, f.next_wave_distance,
                                 f.target_physical_index6, f.from_state_address_id, f.axis, f.direction))
    child_addresses = tuple(selected)
    body = {"schema":"BC-DEPTH-WAVE-CONE-1", "root":address.address_id,
            "max_depth":max_recursive_depth, "wave_radius":wave_radius,
            "target_child":None if target_child is None else target_child.address_id,
            "include_root_lattice":include_root_lattice,
            "box_aperture":BOX_APERTURE_216.address_id, "cube_aperture":CUBE_APERTURE_216.address_id,
            "children":[x.as_dict() for x in child_addresses], "nodes":[x.as_dict() for x in nodes],
            "frontier":[x.as_dict() for x in frontier], "unresolved":unresolved}
    cone_id = _sha256_text(_canonical_json(body))[:24]
    return DepthWaveCone("BC-DEPTH-WAVE-CONE-1", address.address_id, max_recursive_depth, wave_radius,
        None if target_child is None else target_child.address_id, include_root_lattice,
        aperture_alignment_216()["alignment_address"], child_addresses, tuple(nodes), tuple(frontier), tuple(unresolved), not unresolved,
        bool(local_closed) and all(local_closed), cone_id)


@dataclass(frozen=True)
class DepthWaveReopenWitness:
    schema: str
    witness_address: str
    root_address_id: str
    original_cone_address: str
    rebuilt_cone_address: str
    node_set_matches: bool
    frontier_matches: bool
    child_bindings_match: bool
    dependency_closed: bool
    local_state_spaces_closed: bool
    pass_all: bool


def reopen_depth_wave_cone(address: BCFloorAddress, cone: DepthWaveCone) -> DepthWaveReopenWitness:
    """Rebuild a cone from the authoritative source address and its saved request."""
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("floor_address_and_depth_wave_cone_required")
    if address.address_id != cone.root_address_id:
        raise ValueError("depth_wave_reopen_root_address_mismatch")
    target = None
    if cone.target_child_address_id is not None:
        matches = [child for child in cone.child_addresses if child.address_id == cone.target_child_address_id]
        if len(matches) != 1:
            raise ValueError("depth_wave_reopen_target_child_binding_missing")
        target = resolve_recursive_child_address(address, matches[0].level_index)
        if target.address_id != cone.target_child_address_id:
            raise ValueError("depth_wave_reopen_target_child_binding_changed")
    rebuilt = open_depth_wave_cone(address, cone.max_recursive_depth, cone.wave_radius,
                                   target_child=target, include_root_lattice=cone.include_root_lattice)
    nodes_match = rebuilt.nodes == cone.nodes
    frontier_match = rebuilt.frontier == cone.frontier
    children_match = rebuilt.child_addresses == cone.child_addresses
    pass_all = (rebuilt.cone_address == cone.cone_address and nodes_match and frontier_match
                and children_match and rebuilt.unresolved == cone.unresolved
                and rebuilt.dependency_closed == cone.dependency_closed
                and rebuilt.local_state_spaces_closed == cone.local_state_spaces_closed)
    body = {"schema":"BC-DEPTH-WAVE-REOPEN-WITNESS-1", "root":address.address_id,
            "original":cone.cone_address, "rebuilt":rebuilt.cone_address, "nodes_match":nodes_match,
            "frontier_match":frontier_match, "children_match":children_match, "pass":pass_all}
    return DepthWaveReopenWitness("BC-DEPTH-WAVE-REOPEN-WITNESS-1", _sha256_text(_canonical_json(body))[:24],
        address.address_id, cone.cone_address, rebuilt.cone_address, nodes_match, frontier_match,
        children_match, rebuilt.dependency_closed, rebuilt.local_state_spaces_closed, pass_all)


def _require_depth_wave_cone_reopened(address: BCFloorAddress, cone: DepthWaveCone) -> DepthWaveReopenWitness:
    witness = reopen_depth_wave_cone(address, cone)
    if not witness.pass_all:
        raise ValueError("depth_wave_cone_reopen_failed")
    return witness


@dataclass(frozen=True)
class CrownDepthWaveView:
    schema: str
    view_address: str
    root_address_id: str
    cone_address: str
    head_address_id: str | None
    fold_views: tuple[PrimeHarmonicFoldView, ...]
    aperture_alignment_address: str
    depth_summary: tuple[tuple[int, int], ...]
    frontier_count: int
    unresolved: tuple[str, ...]


def crown_depth_wave_view(address: BCFloorAddress, cone: DepthWaveCone) -> CrownDepthWaveView:
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("floor_address_and_depth_wave_cone_required")
    if address.address_id != cone.root_address_id:
        raise ValueError("crown_depth_wave_root_mismatch")
    cone_reopen = _require_depth_wave_cone_reopened(address, cone)
    fold_views = () if address.prime_harmonic is None else prime_harmonic_fold_views(address.prime_harmonic)
    residuals = list(cone.unresolved)
    if address.prime_harmonic is None: residuals.append("prime_harmonic_address_unresolved")
    depths: dict[int, int] = {}
    for node in cone.nodes: depths[node.depth] = depths.get(node.depth, 0) + 1
    summary = tuple(sorted(depths.items()))
    body = {"schema":"BC-CROWN-DEPTH-WAVE-VIEW-1", "root":address.address_id,
            "cone":cone.cone_address, "head":None if address.prime_harmonic is None else address.prime_harmonic.address_id,
            "folds":[v.view_address for v in fold_views], "aperture":cone.aperture_alignment_address,
            "depth_summary":[list(x) for x in summary], "frontier":len(cone.frontier), "unresolved":residuals}
    return CrownDepthWaveView("BC-CROWN-DEPTH-WAVE-VIEW-1", _sha256_text(_canonical_json(body))[:24],
        address.address_id, cone.cone_address,
        None if address.prime_harmonic is None else address.prime_harmonic.address_id,
        fold_views, cone.aperture_alignment_address, summary, len(cone.frontier), tuple(residuals))


@dataclass(frozen=True)
class DepthWaveInputProposal:
    schema: str
    proposal_address: str
    root_address_id: str
    cone_address: str
    cone_reopen_witness_address: str
    relation: str
    proposed_operations: tuple[dict[str, Any], ...]
    status: str
    executed: bool
    persisted: bool
    glyph_admitted: bool


def propose_depth_wave_input(address: BCFloorAddress, cone: DepthWaveCone, relation: str,
                             operations: Sequence[AddressOperation] = ()) -> DepthWaveInputProposal:
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("floor_address_and_depth_wave_cone_required")
    cone_reopen = _require_depth_wave_cone_reopened(address, cone)
    if not isinstance(relation, str) or not relation.strip(): raise ValueError("input_relation_required")
    if not isinstance(operations, (tuple, list)) or any(not isinstance(op, AddressOperation) for op in operations):
        raise TypeError("input_proposal_operations_must_be_typed")
    op_rows = tuple({k:v for k,v in op.__dict__.items()} for op in operations)
    body = {"schema":"BC-DEPTH-WAVE-INPUT-PROPOSAL-1", "root":cone.root_address_id,
            "cone":cone.cone_address, "cone_reopen_witness":cone_reopen.witness_address,
            "relation":relation.strip(), "operations":op_rows,
            "executed":False, "persisted":False, "glyph_admitted":False}
    return DepthWaveInputProposal("BC-DEPTH-WAVE-INPUT-PROPOSAL-1", _sha256_text(_canonical_json(body))[:24],
        cone.root_address_id, cone.cone_address, cone_reopen.witness_address, relation.strip(), op_rows,
        "PROPOSAL_ONLY_NOT_EXECUTED", False, False, False)


@dataclass(frozen=True)
class DepthWaveSelfFeedObservation:
    schema: str
    observation_address: str
    root_address_id: str
    cone_address: str
    witness_id: str
    end_address_id: str
    changes: tuple[dict[str, Any], ...]
    target_depth_touched: bool
    dependency_closed: bool
    return_to_entry_closed: bool
    difference_replays: bool
    admission_authorized: bool
    persisted: bool


def observe_depth_wave_self_feed(address: BCFloorAddress, cone: DepthWaveCone,
                                 witness: FullAddressWitness) -> DepthWaveSelfFeedObservation:
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("floor_address_and_depth_wave_cone_required")
    if not isinstance(witness, FullAddressWitness): raise TypeError("full_address_witness_required")
    _require_depth_wave_cone_reopened(address, cone)
    if cone.root_address_id != address.address_id or witness.start.address_id != address.address_id:
        raise ValueError("self_feed_depth_wave_root_mismatch")
    replay_ok = witness.delta.apply(address).address_id == witness.end.address_id
    if not replay_ok or not witness.difference_replays:
        raise ValueError("self_feed_witness_delta_does_not_replay")
    targeted_levels = {child.level_index for child in cone.child_addresses}
    touched = any(ch.get("path", [None])[0] == "levels" and len(ch.get("path", [])) > 1
                  and ch["path"][1] in targeted_levels for ch in witness.delta.changes)
    changes = tuple(copy.deepcopy(witness.delta.changes))
    body = {"schema":"BC-DEPTH-WAVE-SELF-FEED-OBSERVATION-1", "root":address.address_id,
            "cone":cone.cone_address, "witness":witness.witness_id, "end":witness.end.address_id,
            "changes":changes, "target_touched":touched, "dependency_closed":witness.dependency_closed,
            "return_to_entry_closed":witness.return_to_entry_closed, "difference_replays":replay_ok,
            "admission_authorized":False, "persisted":False}
    return DepthWaveSelfFeedObservation("BC-DEPTH-WAVE-SELF-FEED-OBSERVATION-1",
        _sha256_text(_canonical_json(body))[:24], address.address_id, cone.cone_address,
        witness.witness_id, witness.end.address_id, changes, touched, witness.dependency_closed,
        witness.return_to_entry_closed, replay_ok, False, False)


@dataclass(frozen=True)
class DepthWaveStructuralizerLink:
    schema: str
    link_address: str
    root_address_id: str
    cone_address: str
    child_address_id: str
    child_payload_address_id: str
    source_points: tuple[Point3, ...]
    perspective_packet: SixPlanePerspectivePacket
    coordinates_are_cube_native: bool
    physical_calibration_claimed: bool


def _child_wave_points(cone: DepthWaveCone, child: RecursiveChildAddress) -> tuple[Point3, ...]:
    rows = [n for n in cone.nodes if n.child_address_id == child.address_id and n.depth == child.recursion_depth]
    rows.sort(key=lambda n: (n.wave_distance, n.lattice.physical_index6))
    if not rows: raise ValueError("structuralizer_child_has_no_wave_nodes")
    return tuple(n.lattice.physical_coord6 for n in rows)


def build_depth_wave_structuralizer_view(address: BCFloorAddress, cone: DepthWaveCone,
                                         child: RecursiveChildAddress) -> DepthWaveStructuralizerLink:
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("floor_address_and_depth_wave_cone_required")
    if cone.root_address_id != address.address_id: raise ValueError("structuralizer_depth_wave_root_mismatch")
    _require_depth_wave_cone_reopened(address, cone)
    current_child = resolve_recursive_child_address(address, child.level_index)
    if current_child != child or child.address_id not in {c.address_id for c in cone.child_addresses}:
        raise ValueError("structuralizer_child_not_bound_to_cone")
    points = _child_wave_points(cone, child)
    packet = build_six_plane_perspective(address, points)
    body = {"schema":"BC-DEPTH-WAVE-STRUCTURALIZER-LINK-1", "root":address.address_id,
            "cone":cone.cone_address, "child":child.address_id, "payload":child.payload_address_id,
            "points":[list(p) for p in points], "perspective":packet.packet_address,
            "cube_native":True, "physical_calibration":False}
    return DepthWaveStructuralizerLink("BC-DEPTH-WAVE-STRUCTURALIZER-LINK-1",
        _sha256_text(_canonical_json(body))[:24], address.address_id, cone.cone_address,
        child.address_id, child.payload_address_id, points, packet, True, False)


def reopen_depth_wave_structuralizer_view(address: BCFloorAddress, cone: DepthWaveCone,
                                           child: RecursiveChildAddress,
                                           link: DepthWaveStructuralizerLink) -> dict[str, Any]:
    if not isinstance(link, DepthWaveStructuralizerLink): raise TypeError("depth_wave_structuralizer_link_required")
    if address.address_id != link.root_address_id or cone.cone_address != link.cone_address:
        raise ValueError("depth_wave_structuralizer_link_binding_mismatch")
    _require_depth_wave_cone_reopened(address, cone)
    if child.address_id != link.child_address_id or child.payload_address_id != link.child_payload_address_id:
        raise ValueError("depth_wave_structuralizer_child_binding_mismatch")
    points = _child_wave_points(cone, child)
    if points != link.source_points: raise ValueError("depth_wave_structuralizer_source_points_mismatch")
    witness = reopen_six_plane_perspective(address, points, link.perspective_packet)
    body = {"schema":"BC-DEPTH-WAVE-STRUCTURALIZER-REOPEN-1", "link":link.link_address,
            "cone":cone.cone_address, "child":child.address_id, "perspective":witness.packet_address,
            "pass":witness.pass_all, "physical_calibration_claimed":False}
    return {"schema":"BC-DEPTH-WAVE-STRUCTURALIZER-REOPEN-1", "pass":witness.pass_all,
            "witness_address":_sha256_text(_canonical_json(body))[:24],
            "cone_address":cone.cone_address, "child_address_id":child.address_id,
            "perspective_witness":witness, "coordinates_are_cube_native":True,
            "physical_calibration_claimed":False}


@dataclass(frozen=True)
class BoundDepthWaveFoldResult:
    schema: str
    result_address: str
    aperture_alignment_address: str
    root_address_id: str
    cone_address: str
    child_before: RecursiveChildAddress
    child_after: RecursiveChildAddress
    child_operation: AddressOperation
    harmonic_operation: AddressOperation
    prime_rpm_operations: tuple[AddressOperation, ...]
    witness: FullAddressWitness
    mapping_inferred_from_shared_aperture: bool


def execute_bound_depth_wave_fold(address: BCFloorAddress, cone: DepthWaveCone,
                                  child: RecursiveChildAddress, repetitions: int, axis: str,
                                  child_operation: AddressOperation,
                                  prime_rpm_operations: Sequence[AddressOperation] = ()) -> BoundDepthWaveFoldResult:
    """Compose a harmonic crossing with an explicit operation on a named child.

    Equal 216 aperture cardinalities do not select the child operation. The caller
    names that operation; this executor verifies its depth binding and returns one
    full-address difference/witness for the composed transition.
    """
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("floor_address_and_depth_wave_cone_required")
    if not isinstance(child, RecursiveChildAddress): raise TypeError("recursive_child_address_required")
    if not isinstance(child_operation, AddressOperation): raise TypeError("typed_child_operation_required")
    rpm_ops = tuple(prime_rpm_operations)
    if any(not isinstance(op, AddressOperation) for op in rpm_ops):
        raise TypeError("prime_rpm_operations_must_be_typed_address_operations")
    if any(op.kind not in {"configure_prime_rpm", "advance_prime_rpm"} for op in rpm_ops):
        raise ValueError("bound_fold_coupled_operations_limited_to_explicit_prime_rpm_route")
    _strict_int(repetitions, "harmonic_alignment_repetitions")
    if axis not in AXES: raise ValueError("harmonic_floor_axis_invalid")
    if cone.root_address_id != address.address_id: raise ValueError("bound_fold_cone_root_mismatch")
    _require_depth_wave_cone_reopened(address, cone)
    current = resolve_recursive_child_address(address, child.level_index)
    if current != child or child.address_id not in {c.address_id for c in cone.child_addresses}:
        raise ValueError("bound_fold_child_not_in_cone")
    if address.prime_harmonic is None: raise ValueError("prime_harmonic_address_unresolved")
    if not address.surface.active: raise ValueError("floor_rotation_shell_is_off")
    if child_operation.kind not in {"move_level_lattice27", "move_level_lattice216"}:
        raise ValueError("bound_fold_child_operation_must_mutate_named_lattice_payload")
    if child_operation.depth != child.level_index:
        raise ValueError("bound_fold_child_operation_depth_mismatch")
    harmonic_op = AddressOperation("cross_harmonic_floor_boundary", axis=axis, steps=repetitions)
    ops = (harmonic_op, child_operation, *rpm_ops)
    witness = full_address_witness(address, ops)
    child_after = resolve_recursive_child_address(witness.end, child.level_index)
    if child_after.box_slot_position != child.box_slot_position or child_after.side != child.side:
        raise ValueError("bound_fold_recursive_box_binding_changed_unexpectedly")
    if not witness.difference_replays:
        raise ValueError("bound_fold_full_address_delta_failed_replay")
    body = {"schema":"BC-BOUND-DEPTH-WAVE-FOLD-1", "root":address.address_id,
            "cone":cone.cone_address, "child_before":child.address_id, "child_after":child_after.address_id,
            "harmonic_operation":harmonic_op.__dict__, "child_operation":child_operation.__dict__,
            "prime_rpm_operations":[op.__dict__ for op in rpm_ops],
            "witness":witness.witness_id, "aperture":aperture_alignment_216()["alignment_address"],
            "mapping_inferred_from_shared_aperture":False}
    return BoundDepthWaveFoldResult("BC-BOUND-DEPTH-WAVE-FOLD-1",
        _sha256_text(_canonical_json(body))[:24], aperture_alignment_216()["alignment_address"],
        address.address_id, cone.cone_address, child, child_after, child_operation, harmonic_op,
        rpm_ops, witness, False)



@dataclass(frozen=True)
class ExactRational:
    """Reduced rational arithmetic for address-scale planning; never uses float."""
    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        _strict_int(self.numerator, "rational_numerator")
        _strict_int(self.denominator, "rational_denominator")
        if self.denominator == 0:
            raise ZeroDivisionError("rational_denominator_zero")
        n, d = self.numerator, self.denominator
        if d < 0: n, d = -n, -d
        a, b = abs(n), d
        while b:
            a, b = b, a % b
        gcd = a or 1
        object.__setattr__(self, "numerator", n // gcd)
        object.__setattr__(self, "denominator", d // gcd)

    def __add__(self, other: "ExactRational | int") -> "ExactRational":
        o = other if isinstance(other, ExactRational) else ExactRational(other)
        return ExactRational(self.numerator * o.denominator + o.numerator * self.denominator,
                             self.denominator * o.denominator)

    def __sub__(self, other: "ExactRational | int") -> "ExactRational":
        o = other if isinstance(other, ExactRational) else ExactRational(other)
        return ExactRational(self.numerator * o.denominator - o.numerator * self.denominator,
                             self.denominator * o.denominator)

    def __mul__(self, other: "ExactRational | int") -> "ExactRational":
        o = other if isinstance(other, ExactRational) else ExactRational(other)
        return ExactRational(self.numerator * o.numerator, self.denominator * o.denominator)

    def __truediv__(self, other: "ExactRational | int") -> "ExactRational":
        o = other if isinstance(other, ExactRational) else ExactRational(other)
        if o.numerator == 0:
            raise ZeroDivisionError("rational_divide_by_zero")
        return ExactRational(self.numerator * o.denominator, self.denominator * o.numerator)

    def __neg__(self) -> "ExactRational":
        return ExactRational(-self.numerator, self.denominator)

    def truncate(self) -> int:
        """Truncate toward zero, unlike Python's floor division on negatives."""
        mag = abs(self.numerator) // self.denominator
        return -mag if self.numerator < 0 else mag

    def as_dict(self) -> dict[str, int]:
        return {"numerator": self.numerator, "denominator": self.denominator}


@dataclass(frozen=True)
class RationalRotationResult:
    schema: str
    requested_turns: ExactRational
    residual_turns: ExactRational
    applied_turns: ExactRational
    exact_turn_closed: bool
    status: str
    promotion_radices: tuple[int, ...]
    unresolved_reason: str | None
    witness: FullAddressWitness


def rotate_fractional_turn(
    start: BCFloorAddress,
    axis: str,
    turns: ExactRational,
    *,
    max_promotions: int = 8,
    preferred_radices: Sequence[int] = (8, 7, 5, 3, 2),
) -> RationalRotationResult:
    """Express an exact rational turn with integer ticks plus witnessed shell promotions.

    Angular closure and full-address return are deliberately separate: exact
    completion can leave a finer shell resident until an explicit inverse/demotion.
    """
    if axis not in AXES:
        raise ValueError("rotation_axis_invalid")
    if not start.surface.active:
        raise ValueError("rotation_shell_is_off")
    _strict_int(max_promotions, "max_promotions")
    if max_promotions < 0:
        raise ValueError("max_promotions_must_be_nonnegative")
    radices = tuple(preferred_radices)
    if any(type(r) is not int or r < 2 for r in radices):
        raise ValueError("preferred_radices_must_be_integers_at_least_two")

    current = start
    remaining = turns
    operations: list[AddressOperation] = []
    promoted: list[int] = []
    unresolved_reason: str | None = None

    while remaining.numerator != 0:
        ticks_per_turn = current.surface.ticks_per_turn
        tick_fraction = remaining * ticks_per_turn
        whole_ticks = tick_fraction.truncate()
        residual = remaining - ExactRational(whole_ticks, ticks_per_turn)

        if whole_ticks:
            op = AddressOperation("rotate_surface", axis=axis, ticks=whole_ticks)
            current, _ = FULL_ADDRESS_KERNEL.apply(current, op)
            operations.append(op)
        if residual.numerator == 0:
            remaining = ExactRational(0)
            break
        if len(promoted) >= max_promotions:
            remaining = residual
            unresolved_reason = "shell_promotion_budget_exhausted"
            break

        current_tick_fraction = residual * current.surface.ticks_per_turn
        denominator = current_tick_fraction.denominator
        candidates: list[tuple[int, int, int]] = []
        for rank, radix in enumerate(radices):
            reduced = denominator // _gcd_exact(denominator, radix)
            if reduced < denominator:
                candidates.append((reduced, rank, radix))
        if not candidates:
            remaining = residual
            unresolved_reason = "no_preferred_radix_reduces_residual_denominator"
            break
        _, _, chosen = min(candidates)
        op = AddressOperation("promote_shell", radix=chosen)
        current, _ = FULL_ADDRESS_KERNEL.apply(current, op)
        operations.append(op)
        promoted.append(chosen)
        remaining = residual

    witness = FULL_ADDRESS_KERNEL.execute(start, operations)
    exact_closed = remaining.numerator == 0
    status = "EXACT_TURN_CLOSED" if exact_closed else "RESIDUAL_OPEN"
    return RationalRotationResult("BC-RATIONAL-ROTATION-2", turns, remaining, turns - remaining,
                                  exact_closed, status, tuple(promoted), unresolved_reason, witness)


def _gcd_exact(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def clean_migration_matrix() -> dict[str, Any]:
    """Report precisely which capability families are implemented in this successor."""
    migrated = {
        "floor_circle_page": "migrated_and_tested",
        "one_hot_box_states": "migrated_and_tested",
        "eight_sphere_eight_cube_factor": "migrated_and_tested_as_storage_factor",
        "signed_permutation_frame": "migrated_and_tested",
        "lattice216_factor_and_physical_neighbors": "migrated_and_tested",
        "recursive_216_payload": "migrated_and_tested_for_named_operations",
        "full_address_difference_and_replay": "migrated_and_tested",
        "exact_rational_rotation_and_shell_promotion": "migrated_and_tested_for_named_fractional_turns",
        "prime_harmonic_504_head_and_antipode": "migrated_and_tested",
        "prime_harmonic_504_to_floor_360_common_refinement": "migrated_and_tested_as_discrete_relation_only",
        "prime_harmonic_embedded_in_full_address_and_parent_bound_delta": "migrated_and_tested_for_crossing_subset",
        "prime_harmonic_3_5_7_aperture_views": "migrated_as_derived_views_not_head_motion",
        "six_plane_point_perspective_and_exact_lift": "migrated_and_tested_for_integer_point_view_subset",
        "structuralizer_vm_zero_plane_frame_address": "migrated_and_tested for source-bound exact integer origin and named signed-permutation plane",
        "zero_plane_two_of_three_equal_step_solver": "migrated_and_tested with explicit relation constraint and six-frame inverse/revolve witness",
        "structuralizer_hallway_relative_relation_copy": "migrated_and_tested as source/target-bound relative-geometry copy; neither authoritative address is mutated",
        "ast_source_reader": "migrated_and_tested",
        "single_executor_registry": "migrated_and_tested",
        "effect_scoped_authority": "migrated_and_tested",
        "distinct_box216_and_cube216_aperture_addresses": "migrated_and_tested; same cardinality is not state equivalence",
        "named_recursive_child_address_binding": "migrated_and_tested_for_levels_i_lattice216",
        "depth_wave_state_cones": "migrated_and_tested_for_bounded_6x6x6_neighbor_waves_and_explicit_depth_residuals",
        "depth_wave_cone_reopen_and_witness": "migrated_and_tested_against_exact_root_child_nodes_and_frontier",
        "depth_wave_input_proposal_interface": "migrated_as_non_executing_candidate_packet",
        "depth_wave_self_feed_interface": "migrated_as_replay_checked_observation_without_admission_or_persistence",
        "depth_wave_structuralizer_interface": "migrated_for_cube_native_integer_points_with_exact_reopen",
        "depth_wave_crown_interface": "migrated_as_derived_harmonic_fold_view_with_open_residuals",
        "harmonic_fold_bound_to_named_recursive_child": "migrated_for_explicitly_supplied_child_operation; aperture equality does not infer semantics",
        "prime_rpm_core_357_and_explicit_higher_prime_lanes": "migrated_as_exact_integer_full_address_state_with_explicit_rate_residuals",
        "prime_rpm_ordered_word_momentum_and_winding": "migrated_for_bounded_signed_words_with_exact_target_relation_and_replay",
        "prime_rpm_transition_reopen": "migrated_and_tested_against_exact_source_lane_state_and_trace",
        "crown_precone_present_state_shell_selection": "migrated_for supplied counts and full-address root binding; latent capacity excluded from work budget",
        "fibonacci_growth_budget_law": "migrated_and_tested_with exact integer Fibonacci caps and cumulative openings",
        "factor_local_spiral_placement": "migrated_and_tested_without Cartesian materialisation; preserves each named stack factor tuple",
        "harmonic_spiral_plan_reopen": "migrated_and_tested against profile, root, cone, stack, budget, points and plan identity",
        "crown_precone_holistic_budget_envelope": "migrated_and_tested for bounded cases/nodes/edges/openings/path depth with content-addressed reopen",
        "harmonic64_opaque_54_payload_10_alignment_masks": "migrated for exact unsigned word validation and separated mask regions; no trit decoding or hardware calibration implied",
        "harmonic64_multi_query_route_scheduler": "migrated_and_tested for same-root/same-cone admitted query portfolio, exact mask coverage, full-address replay witness and deterministic costs",
        "harmonic64_cost_aware_compound_candidate_search": "migrated as lexicographic exact integer dimensions (reopened states, semantic edges, bit operations, mechanical depth, routing depth)",
        "evidence_gated_fibonacci_lexical_doubling_placement_crossover": "migrated for explicit finite target coverage, computed per-strategy costs, full-coverage-only selection and tamper-rejecting reopen",
        "typed_command_reference_resolution": "migrated_and_tested for exact canonical glyph/operation lookup plus root-bound static historical residuals; never dispatches legacy code",
        "historical_executor_dependency_inventory": "migrated_as_finite_ROM with 805 source-line-bound assignments, 185 captured alias records, duplicate-definition sites and dynamic lookup evidence",
        "historical_command_behavior_profiles": "migrated_as source-hash-bound AST/source-slice fingerprints, call/name shapes, domain tags and replay-probe triage; never executes or binds legacy semantics",
    }
    pending = {
        "full_historical_glyph_catalogue": "not_migrated",
        "harmonic64_physical_lane_semantics_and_external_router_binding": "not_migrated; mask operations are opaque structural carrier planning, not a decoded hardware protocol",
        "all_science_atomic_chemistry_domains": "not_migrated",
        "full_structuralizer_view_families": "not_migrated",
        "prime_harmonic_physical_calibration_and_full_aperture_search": "not_migrated",
        "physical_rpm_calibration_and_external_clock_binding": "not_migrated; rate values remain exact structural addresses only",
        "oblique_integer_chart_fallback_and_full_structuralizer_search": "not_migrated",
        "historical_learning_and_self_feed": "not_migrated",
        "project_storage_resolver_and_sealed_snapshot_io": "not_migrated",
        "source_patch_and_release_gate": "not_migrated",
        "full_legacy_frontdoor_semantic_parity": "not_migrated",
        "historical_command_semantic_bindings": "not_migrated; source records are indexed but old executors remain unmapped until per-command semantic witness and certified replay are available",
        "historical_command_behavior_equivalence": "not_migrated; AST profiles are evidence for prioritising witness work, not proof that old and clean operations are equivalent",
    }
    return {"schema":"BC-CLEAN-MIGRATION-MATRIX-3", "engine":ENGINE_IDENTITY,
            "runtime_state":"warm", "migrated":migrated, "pending":pending,
            "no_legacy_engine_imported":True, "no_legacy_engine_executed":True,
            "cold_commit":"NOT_PERFORMED"}


def inspect_legacy_source(source_path: str, expected_sha256: str | None = None) -> dict[str, Any]:
    """Static migration map: parse source, never import/execute it or assert runtime dispatch."""
    path = pathlib.Path(source_path)
    raw = path.read_bytes()
    source = raw.decode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    hash_matches = None if expected_sha256 is None else digest == expected_sha256
    tree = ast.parse(source, filename=str(path), mode="exec")
    compile(tree, str(path), "exec")
    defs: dict[str, list[dict[str, Any]]] = {}
    classes: dict[str, list[dict[str, Any]]] = {}
    direct_calls: dict[str, set[str]] = {}
    registry_writes: dict[str, list[dict[str, Any]]] = {}
    aliases: list[dict[str, Any]] = []
    dynamic: list[dict[str, Any]] = []
    list_comps: list[dict[str, Any]] = []
    subscripts: list[dict[str, Any]] = []
    all_calls = 0

    source_lines = source.splitlines()
    def source_seg(node: ast.AST, limit: int = 200) -> str:
        # Bounded line-based slicing avoids quadratic work on large nested defs.
        if not getattr(node, "lineno", None):
            return type(node).__name__
        first = node.lineno - 1
        last = getattr(node, "end_lineno", node.lineno) - 1
        if first < 0 or last >= len(source_lines):
            return type(node).__name__
        if first == last:
            line = source_lines[first]
            start_col = getattr(node, "col_offset", 0)
            end_col = getattr(node, "end_col_offset", len(line))
            return line[start_col:end_col][:limit].replace("\t", " ")
        start_col = getattr(node, "col_offset", 0)
        head = source_lines[first][start_col:]
        if len(head) >= limit:
            return head[:limit]
        parts = [head]
        used = len(head)
        for idx in range(first + 1, last + 1):
            chunk = source_lines[idx]
            if used + 1 + len(chunk) > limit:
                parts.append(chunk[:max(0, limit-used-1)])
                break
            parts.append(chunk); used += 1 + len(chunk)
        return " ".join(parts)[:limit]

    def name_of(node: ast.AST | None) -> str:
        if node is None: return ""
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute):
            base = name_of(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        if isinstance(node, ast.Subscript): return f"{name_of(node.value)}[{source_seg(node.slice, 50)}]"
        if isinstance(node, ast.Call): return name_of(node.func)
        return type(node).__name__

    class Scan(ast.NodeVisitor):
        def __init__(self): self.scope=[]
        def visit_FunctionDef(self,node):
            qual = ".".join([*self.scope, node.name]) or node.name
            defs.setdefault(qual, []).append({"line":node.lineno,"end_line":node.end_lineno,
                "span_lines":node.end_lineno-node.lineno+1,"signature":source_seg(node.args,120)})
            self.scope.append(node.name); self.generic_visit(node); self.scope.pop()
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ClassDef(self,node):
            qual = ".".join([*self.scope, node.name]) or node.name
            classes.setdefault(qual, []).append({"line":node.lineno,"end_line":node.end_lineno,
                "span_lines":node.end_lineno-node.lineno+1,"bases":[name_of(b) for b in node.bases]})
            self.scope.append(node.name); self.generic_visit(node); self.scope.pop()
        def visit_Call(self,node):
            nonlocal all_calls
            all_calls += 1
            called=name_of(node.func)
            if called.rsplit(".",1)[-1] in {"getattr","eval","exec","__import__"} or isinstance(node.func,ast.Name) and node.func.id in {"globals","locals"}:
                dynamic.append({"line":node.lineno,"callee":called,"source":source_seg(node)})
            if self.scope and (isinstance(node.func, (ast.Name, ast.Attribute))):
                direct_calls.setdefault(".".join(self.scope), set()).add(called)
            self.generic_visit(node)
        def visit_ListComp(self,node):
            list_comps.append({"line":node.lineno,"source":source_seg(node),
              "targets":[source_seg(g.target,80) for g in node.generators],
              "iterators":[source_seg(g.iter,100) for g in node.generators]})
            self.generic_visit(node)
        def visit_Subscript(self,node):
            subscripts.append({"line":node.lineno,"base":name_of(node.value),"index":source_seg(node.slice,80),"source":source_seg(node)})
            self.generic_visit(node)
        def visit_Assign(self,node):
            rhs = node.value
            target_names = [name_of(t) for t in node.targets]
            if isinstance(rhs,ast.Name):
                for target in target_names:
                    if target.startswith("_") or target in {"bc_boot","current_engine_identity"}:
                        aliases.append({"line":node.lineno,"scope":list(self.scope),"target":target,"source_name":rhs.id,"kind":"name_alias_candidate","source":source_seg(node)})
            for target in node.targets:
                if isinstance(target,ast.Subscript) and name_of(target.value).endswith("NATIVE_GLYPH_EXECUTORS"):
                    key = ast.literal_eval(target.slice) if isinstance(target.slice,(ast.Constant,ast.Tuple)) else source_seg(target.slice,80)
                    registry_writes.setdefault(str(key),[]).append({"line":node.lineno,"scope":list(self.scope),"executor_expr":name_of(rhs),"source":source_seg(node)})
            self.generic_visit(node)

    Scan().visit(tree)
    duplicates={name:rows for name,rows in sorted(defs.items()) if len(rows)>1}
    live_last={name:rows[-1] for name,rows in sorted(defs.items())}
    repeated_registry={k:v for k,v in sorted(registry_writes.items()) if len(v)>1}
    return {
        "schema":"BC-CLEAN-LEGACY-MIGRATION-MAP-2",
        "pass": hash_matches is not False,
        "status": "SOURCE_HASH_MATCH" if hash_matches is True else "SOURCE_HASH_UNBOUND" if hash_matches is None else "SOURCE_HASH_MISMATCH",
        "source":{"path":str(path.resolve()),"sha256":digest,"bytes":len(raw),"expected_hash":expected_sha256,
                  "expected_hash_matches":hash_matches,"source_executed":False},
        "scope_notice":"Static source map only. 'last definition' is source ordering, not proof of active runtime binding under conditional execution or captured references.",
        "syntax":{"pass":True,"top_level_nodes":len(tree.body),"function_definition_occurrences":sum(map(len,defs.values())),
                  "unique_qualified_function_names":len(defs),"duplicate_groups":len(duplicates),"extra_redefinitions":sum(len(v)-1 for v in defs.values()),
                  "call_nodes":all_calls,"list_comprehensions":len(list_comps),"subscripts":len(subscripts)},
        "definition_history":defs,"last_source_definition_index":live_last,"duplicate_definition_groups":duplicates,
        "class_history":classes,"direct_call_names_by_scope":{k:sorted(v) for k,v in sorted(direct_calls.items())},
        "captured_alias_candidates":aliases,"executor_assignment_history":registry_writes,"repeated_executor_keys":repeated_registry,
        "dynamic_lookup_sites":dynamic,"comprehension_sites":list_comps,"subscript_sites":subscripts,
        "migration_decision":{"history_external_only":True,"automatic_bulk_deletion":False,"single_live_executor_target":True,
                               "source_hash_is_storage_identity_not_semantic_truth":True,"cold_commit":"NOT_PERFORMED"}}


# ---------------------------------------------------------------------------
# Crown pre-cone + Fibonacci growth + factor-local spiral (V5 warm slice)
# ---------------------------------------------------------------------------
# These are deterministic planning records only. They do not execute candidate
# points, enlarge the depth-wave cone, admit glyphs, or persist learning.

HARMONIC_FIB_GROWTH = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377)
HARMONIC_SPIRAL_CROSSOVER_BUDGETS = tuple(f for f in HARMONIC_FIB_GROWTH if f <= 55)
HARMONIC_SPIRAL_UNIVERSAL_EARLY_BUDGETS = (1, 2, 3)
HARMONIC_SPIRAL_GROWTH_POLICY = "fibonacci_budget_escalation_factor_local_placement"
HARMONIC_STACK_SHELL_BUDGET_CAPS = {
    "trit2": 2, "box9": 5, "core64": 8, "page90": 13, "floor216": 21,
    "circle360": 21, "signed432": 34, "stack1512": 34, "stack1728": 34,
    "stack2592": 55, "fractal3888": 55, "dense729": 34, "page_trit81": 13,
    "fractal_equivalence": 89,
}


@dataclass(frozen=True)
class HarmonicStackSpec:
    name: str
    shape: tuple[int, ...]
    capacity: int
    shell: str
    address_family: str

    def __post_init__(self) -> None:
        if not self.name or not self.shape or any(type(v) is not int or v <= 0 for v in self.shape):
            raise ValueError("harmonic_stack_shape_must_have_positive_exact_factors")
        product = 1
        for value in self.shape:
            product *= value
        if type(self.capacity) is not int or product != self.capacity:
            raise ValueError("harmonic_stack_capacity_must_equal_factor_product")
        if self.name == "floor216" and self.address_family != "box_aperture_216":
            raise ValueError("floor216_must_remain_box_aperture_family")

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "shape": list(self.shape), "capacity": self.capacity,
                "shell": self.shell, "address_family": self.address_family}


# Factor order preserves the legacy source's named stacks. Sorting for shell
# selection happens by (capacity, name), as in its corrected pre-cone routine.
HARMONIC_STACKS = (
    HarmonicStackSpec("trit2", (2,), 2, "local", "trit"),
    HarmonicStackSpec("box9", (3, 3), 9, "box", "box_factor"),
    HarmonicStackSpec("page_trit81", (3, 3, 3, 3), 81, "page-trit", "page_trit"),
    HarmonicStackSpec("page90", (9, 10), 90, "page", "page"),
    HarmonicStackSpec("core64", (8, 8), 64, "core", "core"),
    HarmonicStackSpec("dense729", (9, 9, 9), 729, "fine-volume", "fine_volume"),
    HarmonicStackSpec("floor216", (8, 3, 9), 216, "floor", "box_aperture_216"),
    HarmonicStackSpec("circle360", (4, 90), 360, "circle", "circle"),
    HarmonicStackSpec("signed432", (2, 216), 432, "signed-transport", "signed_transport"),
    HarmonicStackSpec("stack1512", (7, 216), 1512, "7-floor-stack", "stack"),
    HarmonicStackSpec("stack1728", (8, 216), 1728, "8-floor-stack", "stack"),
    HarmonicStackSpec("stack2592", (12, 216), 2592, "12-floor-stack", "stack"),
    HarmonicStackSpec("fractal3888", (18, 216), 3888, "fractal-box", "fractal_box_stack"),
    HarmonicStackSpec("fractal_equivalence", (64, 9, 432, 729), 181398528, "fractal-equivalence", "factored_equivalence_product"),
)
HARMONIC_STACK_BY_NAME = {item.name: item for item in HARMONIC_STACKS}
HARMONIC_STACK_SHELL_ORDER = tuple(sorted(HARMONIC_STACKS, key=lambda item: (item.capacity, item.name)))


@dataclass(frozen=True)
class PreConeRequest:
    """Supplied state dimensions for Crown's pre-cone calculation.

    Sequence contents are observed only for their supplied population; this
    record does not execute them or turn them into candidate state addresses.
    The optional full address is retained by its exact address_id.
    """
    address: BCFloorAddress | None = None
    requirements: tuple[Any, ...] = ()
    fine_width: int = 0
    field: Any = ()
    members: Any = ()
    payload: bytes | str | None = None
    potential_shell: str = "fractal_equivalence"
    address_depth_override: int | None = None
    cone: DepthWaveCone | None = None

    def __post_init__(self) -> None:
        if self.address is not None and not isinstance(self.address, BCFloorAddress):
            raise TypeError("precone_root_must_be_full_floor_address_or_none")
        if self.cone is not None:
            if not isinstance(self.cone, DepthWaveCone):
                raise TypeError("precone_source_cone_must_be_depth_wave_cone_or_none")
            if self.address is None:
                raise ValueError("precone_source_cone_requires_full_root_address")
            cone_witness = reopen_depth_wave_cone(self.address, self.cone)
            if not cone_witness.pass_all:
                raise ValueError("precone_source_cone_reopen_failed")
            expected_field = tuple(node.state_address_id for node in self.cone.nodes)
            expected_members = tuple(frontier.target_state_address_id for frontier in self.cone.frontier)
            if not isinstance(self.field, (tuple, list)) or tuple(self.field) != expected_field:
                raise ValueError("precone_cone_field_population_source_mismatch")
            if not isinstance(self.members, (tuple, list)) or tuple(self.members) != expected_members:
                raise ValueError("precone_cone_member_population_source_mismatch")
        if not isinstance(self.requirements, (tuple, list, set, frozenset)):
            raise TypeError("precone_requirements_must_be_sequence")
        for name, val in (("fine_width", self.fine_width),):
            if type(val) is not int or val < 0:
                raise ValueError(f"precone_{name}_must_be_nonnegative_exact_integer")
        if self.address_depth_override is not None and (type(self.address_depth_override) is not int or self.address_depth_override < 0):
            raise ValueError("precone_address_depth_must_be_nonnegative_exact_integer")
        if self.payload is not None and not isinstance(self.payload, (bytes, bytearray, str)):
            raise TypeError("precone_payload_must_be_bytes_text_or_none")
        if self.potential_shell not in HARMONIC_STACK_BY_NAME:
            raise ValueError("precone_potential_shell_unknown")
        for name, value in (("field", self.field), ("members", self.members)):
            if not isinstance(value, (tuple, list, set, frozenset, Mapping)):
                raise TypeError(f"precone_{name}_must_be_countable_sequence_or_mapping")


def _source_population(value: Any) -> int:
    try:
        return len(value)
    except TypeError as exc:
        raise TypeError("precone_population_source_must_have_length") from exc


@dataclass(frozen=True)
class PreConeStateProfile:
    schema: str
    profile_id: str
    root_address_id: str | None
    source_cone_address: str | None
    source_cone_root_address_id: str | None
    source_cone_reopen_pass: bool
    address_depth: int
    fine_width: int
    requirement_count: int
    field_population: int
    explicit_population: int
    population: int
    payload_bytes: int
    pre_cone_units: int
    selected_shell: str
    selected_capacity: int
    potential_shell: str
    potential_cone_capacity: int
    policy: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "profile_id": self.profile_id,
                "root_address_id": self.root_address_id, "source_cone_address": self.source_cone_address,
                "source_cone_root_address_id": self.source_cone_root_address_id,
                "source_cone_reopen_pass": self.source_cone_reopen_pass,
                "address_depth": self.address_depth, "fine_width": self.fine_width, "requirement_count": self.requirement_count,
                "field_population": self.field_population, "explicit_population": self.explicit_population,
                "population": self.population, "payload_bytes": self.payload_bytes,
                "pre_cone_units": self.pre_cone_units, "selected_shell": self.selected_shell,
                "selected_capacity": self.selected_capacity, "potential_shell": self.potential_shell,
                "potential_cone_capacity": self.potential_cone_capacity, "policy": self.policy}


def profile_precone_state(request: PreConeRequest) -> PreConeStateProfile:
    """Choose a shell from supplied present-state size, not latent capacity."""
    if not isinstance(request, PreConeRequest):
        raise TypeError("precone_request_required")
    depth = (request.address_depth_override if request.address_depth_override is not None else
             len(request.address.levels) if request.address is not None else 0)
    req_count = len(request.requirements)
    field_population = _source_population(request.field)
    explicit_population = _source_population(request.members)
    population = max(field_population, explicit_population)
    payload_bytes = len(request.payload) if isinstance(request.payload, (bytes, bytearray, str)) else 0
    units = max(1, 2 * depth + request.fine_width + req_count + population + payload_bytes // 64)
    chosen = next((item for item in HARMONIC_STACK_SHELL_ORDER if item.capacity >= units), HARMONIC_STACK_SHELL_ORDER[-1])
    potential = HARMONIC_STACK_BY_NAME[request.potential_shell]
    root_address_id = None if request.address is None else request.address.address_id
    source_cone_address = None if request.cone is None else request.cone.cone_address
    source_cone_root_address_id = None if request.cone is None else request.cone.root_address_id
    source_cone_reopen_pass = request.cone is not None
    body = {"schema":"BC-PRECONE-STATE-PROFILE-2", "root_address_id":root_address_id,
            "source_cone_address":source_cone_address,
            "source_cone_root_address_id":source_cone_root_address_id,
            "source_cone_reopen_pass":source_cone_reopen_pass,
            "address_depth":depth, "fine_width":request.fine_width, "requirement_count":req_count,
            "field_population":field_population, "explicit_population":explicit_population,
            "population":population, "payload_bytes":payload_bytes, "pre_cone_units":units,
            "selected_shell":chosen.name, "selected_capacity":chosen.capacity,
            "potential_shell":potential.name, "potential_cone_capacity":potential.capacity,
            "policy":"smallest shell containing supplied present-state size; potential cone capacity never selects work budget"}
    return PreConeStateProfile(body["schema"], _sha256_text(_canonical_json(body))[:24],
        body["root_address_id"], source_cone_address, source_cone_root_address_id, source_cone_reopen_pass,
        depth, request.fine_width, req_count, field_population, explicit_population,
        population, payload_bytes, units, chosen.name, chosen.capacity, potential.name, potential.capacity, body["policy"])


def reopen_precone_state_profile(profile: PreConeStateProfile) -> dict[str, Any]:
    """Recompute the content address and derived shell from the immutable profile fields."""
    if not isinstance(profile, PreConeStateProfile):
        raise TypeError("precone_profile_required")
    integer_fields = (profile.address_depth, profile.fine_width, profile.requirement_count,
                      profile.field_population, profile.explicit_population, profile.population,
                      profile.payload_bytes, profile.pre_cone_units, profile.selected_capacity,
                      profile.potential_cone_capacity)
    basic_types = all(type(value) is int and value >= 0 for value in integer_fields)
    if not basic_types:
        return {"schema":"BC-PRECONE-STATE-PROFILE-REOPEN-1", "pass":False,
                "profile_id":profile.profile_id, "rebuilt_profile_id":None,
                "root_address_id":profile.root_address_id,
                "checks":{"metrics_consistent":False, "shell_selection_consistent":False,
                          "profile_address_matches_content":False},
                "potential_capacity_used_as_budget":False}
    metrics_match = (profile.population == max(profile.field_population, profile.explicit_population)
                     and profile.pre_cone_units == max(1, 2 * profile.address_depth + profile.fine_width +
                         profile.requirement_count + profile.population + profile.payload_bytes // 64))
    chosen = next((item for item in HARMONIC_STACK_SHELL_ORDER if item.capacity >= profile.pre_cone_units), HARMONIC_STACK_SHELL_ORDER[-1])
    potential = HARMONIC_STACK_BY_NAME.get(profile.potential_shell) if isinstance(profile.potential_shell, str) else None
    shell_match = (profile.selected_shell == chosen.name and profile.selected_capacity == chosen.capacity and
                   potential is not None and profile.potential_cone_capacity == potential.capacity)
    body = {"schema":profile.schema, "root_address_id":profile.root_address_id,
            "source_cone_address":profile.source_cone_address,
            "source_cone_root_address_id":profile.source_cone_root_address_id,
            "source_cone_reopen_pass":profile.source_cone_reopen_pass,
            "address_depth":profile.address_depth, "fine_width":profile.fine_width,
            "requirement_count":profile.requirement_count, "field_population":profile.field_population,
            "explicit_population":profile.explicit_population, "population":profile.population,
            "payload_bytes":profile.payload_bytes, "pre_cone_units":profile.pre_cone_units,
            "selected_shell":profile.selected_shell, "selected_capacity":profile.selected_capacity,
            "potential_shell":profile.potential_shell, "potential_cone_capacity":profile.potential_cone_capacity,
            "policy":profile.policy}
    rebuilt_id = _sha256_text(_canonical_json(body))[:24]
    root_valid = (profile.root_address_id is None or isinstance(profile.root_address_id, str) and len(profile.root_address_id) == 24
                  and all(ch in "0123456789abcdef" for ch in profile.root_address_id))
    cone_valid = (profile.source_cone_address is None and profile.source_cone_root_address_id is None
                  and profile.source_cone_reopen_pass is False) or (
                  isinstance(profile.source_cone_address, str) and len(profile.source_cone_address) == 24
                  and all(ch in "0123456789abcdef" for ch in profile.source_cone_address)
                  and profile.source_cone_root_address_id == profile.root_address_id
                  and profile.source_cone_reopen_pass is True)
    address_match = (profile.schema == "BC-PRECONE-STATE-PROFILE-2" and profile.profile_id == rebuilt_id and root_valid)
    checks = {"metrics_consistent": bool(metrics_match), "shell_selection_consistent": bool(shell_match),
              "profile_address_matches_content": bool(address_match), "source_cone_binding_matches": bool(cone_valid)}
    return {"schema":"BC-PRECONE-STATE-PROFILE-REOPEN-2", "pass":all(checks.values()),
            "profile_id":profile.profile_id, "rebuilt_profile_id":rebuilt_id,
            "root_address_id":profile.root_address_id, "checks":checks,
            "potential_capacity_used_as_budget":False}


def _largest_fibonacci_at_most(value: int, cap: int) -> int:
    best = 1
    for item in HARMONIC_FIB_GROWTH:
        if item <= value and item <= cap:
            best = item
        else:
            break
    return best


def harmonic_growth_profile(stack_name: str, pre_cone_units: int) -> dict[str, Any]:
    if stack_name not in HARMONIC_STACK_BY_NAME:
        raise ValueError("harmonic_stack_unknown")
    if type(pre_cone_units) is not int or pre_cone_units < 1:
        raise ValueError("pre_cone_units_must_be_positive_exact_integer")
    stack = HARMONIC_STACK_BY_NAME[stack_name]
    shell_cap = HARMONIC_STACK_SHELL_BUDGET_CAPS[stack_name]
    desired = max(1, pre_cone_units // 4)
    budget = min(stack.capacity, shell_cap, _largest_fibonacci_at_most(desired, shell_cap))
    stage = max(i for i, fib in enumerate(HARMONIC_FIB_GROWTH) if fib <= budget)
    return {"stack": stack_name, "capacity": stack.capacity, "shell_budget_cap": shell_cap,
            "desired_from_pre_cone": desired, "budget": budget, "growth_stage": stage,
            "growth_value": HARMONIC_FIB_GROWTH[stage],
            "next_growth_value": HARMONIC_FIB_GROWTH[min(stage + 1, len(HARMONIC_FIB_GROWTH) - 1)],
            "pre_cone_units": pre_cone_units,
            "policy": "Fibonacci controls bounded opening budget; placement remains factor-local; latent capacity is not multiplied into work"}


def fibonacci_offsets(count: int, bound: int, center: int = 0) -> tuple[int, ...]:
    """Alternating signed Fibonacci offsets on one exact finite cyclic factor."""
    if type(count) is not int or not 1 <= count <= 64:
        raise ValueError("fibonacci_offset_count_must_be_1_to_64")
    if type(bound) is not int or bound < 1:
        raise ValueError("fibonacci_offset_bound_must_be_positive_exact_integer")
    if type(center) is not int:
        raise TypeError("fibonacci_offset_center_must_be_exact_integer")
    n, b, c = min(count, bound), bound, center % bound
    out = [c]; seen = {c}; side = 0
    if n == 1:
        return (c,)
    offset_sequence = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597)
    for step in offset_sequence:
        signs = (-1, 1) if side % 2 == 0 else (1, -1)
        for sign in signs:
            x = (c + sign * step) % b
            if x not in seen:
                seen.add(x); out.append(x)
                if len(out) >= n:
                    return tuple(out)
        side += 1
    for distance in range(1, b):
        signs = (-1, 1) if distance % 2 else (1, -1)
        for sign in signs:
            x = (c + sign * distance) % b
            if x not in seen:
                seen.add(x); out.append(x)
                if len(out) >= n:
                    return tuple(out)
    return tuple(out[:n])


def factorized_spiral(shape: Sequence[int], centers: Sequence[int] | None = None,
                      limit: int = 32) -> tuple[tuple[int, ...], ...]:
    """Bounded factor-local point schedule; never form the Cartesian product."""
    if not isinstance(shape, (tuple, list)) or not 1 <= len(shape) <= 8:
        raise ValueError("spiral_shape_must_have_1_to_8_factors")
    if any(type(v) is not int or v <= 0 for v in shape):
        raise ValueError("spiral_shape_factors_must_be_positive_exact_integers")
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError("spiral_limit_must_be_1_to_64")
    shp = tuple(shape)
    if centers is None:
        ctr = (0,) * len(shp)
    else:
        if not isinstance(centers, (tuple, list)) or len(centers) != len(shp) or any(type(v) is not int for v in centers):
            raise ValueError("spiral_centers_must_match_shape_with_exact_integers")
        ctr = tuple(centers[i] % shp[i] for i in range(len(shp)))
    per = [fibonacci_offsets(min(max(4, limit), dim), dim, ctr[i]) for i, dim in enumerate(shp)]
    out: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    depth = 0
    while len(out) < limit:
        added = False
        for factor_index, _dim in enumerate(shp):
            seq = per[factor_index]
            if depth < len(seq):
                point = list(ctr); point[factor_index] = seq[depth]; point_tuple = tuple(point)
                if point_tuple not in seen:
                    seen.add(point_tuple); out.append(point_tuple); added = True
                    if len(out) >= limit: break
        if len(out) >= limit: break
        if depth > 0:
            for factor_index in range(len(shp) - 1):
                other = factor_index + 1
                if depth < len(per[factor_index]) and depth < len(per[other]):
                    point = list(ctr); point[factor_index] = per[factor_index][depth]; point[other] = per[other][depth]
                    point_tuple = tuple(point)
                    if point_tuple not in seen:
                        seen.add(point_tuple); out.append(point_tuple); added = True
                        if len(out) >= limit: break
        depth += 1
        if not added and depth >= max(len(part) for part in per):
            break
    return tuple(out[:limit])


@dataclass(frozen=True)
class HarmonicSpiralGrowthPlan:
    schema: str
    plan_id: str
    profile_id: str
    root_address_id: str | None
    source_cone_address: str | None
    source_cone_root_address_id: str | None
    source_cone_reopen_pass: bool
    stack_name: str
    shape: tuple[int, ...]
    capacity: int
    requested_limit: int
    pre_cone_units: int
    growth_budget: int
    growth_sequence: tuple[int, ...]
    cumulative_openings: tuple[int, ...]
    spiral_points: tuple[tuple[int, ...], ...]
    placement_method: str
    factor_local_placement: bool
    cartesian_materialisation: bool
    evidence_gated_crossover_migrated: bool
    policy: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "plan_id": self.plan_id, "profile_id": self.profile_id,
                "root_address_id": self.root_address_id, "source_cone_address": self.source_cone_address,
                "source_cone_root_address_id": self.source_cone_root_address_id,
                "source_cone_reopen_pass": self.source_cone_reopen_pass,
                "stack_name": self.stack_name,
                "shape": list(self.shape), "capacity": self.capacity, "requested_limit": self.requested_limit,
                "pre_cone_units": self.pre_cone_units, "growth_budget": self.growth_budget,
                "growth_sequence": list(self.growth_sequence), "cumulative_openings": list(self.cumulative_openings),
                "spiral_points": [list(point) for point in self.spiral_points],
                "placement_method": self.placement_method, "factor_local_placement": self.factor_local_placement,
                "cartesian_materialisation": self.cartesian_materialisation,
                "evidence_gated_crossover_migrated": self.evidence_gated_crossover_migrated, "policy": self.policy}


def _build_harmonic_spiral_plan(profile: PreConeStateProfile, stack_name: str, limit: int) -> HarmonicSpiralGrowthPlan:
    if not isinstance(profile, PreConeStateProfile):
        raise TypeError("precone_profile_required")
    if not reopen_precone_state_profile(profile)["pass"]:
        raise ValueError("precone_profile_integrity_failed")
    if stack_name not in HARMONIC_STACK_BY_NAME:
        raise ValueError("harmonic_stack_unknown")
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError("spiral_limit_must_be_1_to_64")
    spec = HARMONIC_STACK_BY_NAME[stack_name]
    growth = harmonic_growth_profile(stack_name, profile.pre_cone_units)
    budgets = tuple(value for value in HARMONIC_SPIRAL_CROSSOVER_BUDGETS if value <= growth["budget"])
    total = 0; cumulative: list[int] = []
    for value in budgets:
        total += value; cumulative.append(total)
    points = factorized_spiral(spec.shape, limit=min(limit, 64, spec.capacity))
    body = {"schema":"BC-HARMONIC-SPIRAL-GROWTH-PLAN-1", "profile_id":profile.profile_id,
        "root_address_id":profile.root_address_id, "source_cone_address":profile.source_cone_address,
        "source_cone_root_address_id":profile.source_cone_root_address_id,
        "source_cone_reopen_pass":profile.source_cone_reopen_pass,
        "stack_name":stack_name, "shape":spec.shape,
        "capacity":spec.capacity, "requested_limit":limit, "pre_cone_units":profile.pre_cone_units,
        "growth_budget":growth["budget"], "growth_sequence":budgets, "cumulative_openings":tuple(cumulative),
        "spiral_points":points, "placement_method":"fibonacci_factor_depth_order",
        "factor_local_placement":True, "cartesian_materialisation":False,
        "evidence_gated_crossover_migrated":False,
        "policy":"Fibonacci bounds widening; positions stay factor-local. Evidence-gated placement crossover is pending migration."}
    pid = _sha256_text(_canonical_json(body))[:24]
    return HarmonicSpiralGrowthPlan(body["schema"], pid, body["profile_id"], body["root_address_id"],
        body["source_cone_address"], body["source_cone_root_address_id"], body["source_cone_reopen_pass"],
        stack_name, spec.shape, spec.capacity, limit, profile.pre_cone_units, growth["budget"], budgets,
        tuple(cumulative), points, body["placement_method"], True, False, False, body["policy"])


def build_harmonic_spiral_growth_plan(profile: PreConeStateProfile, stack_name: str,
                                      limit: int = 32) -> HarmonicSpiralGrowthPlan:
    return _build_harmonic_spiral_plan(profile, stack_name, limit)


def reopen_harmonic_spiral_growth_plan(profile: PreConeStateProfile,
                                        plan: HarmonicSpiralGrowthPlan) -> dict[str, Any]:
    """Rebuild against source profile and exact requested bound; changed plans fail closed."""
    if not isinstance(profile, PreConeStateProfile) or not isinstance(plan, HarmonicSpiralGrowthPlan):
        raise TypeError("precone_profile_and_growth_plan_required")
    profile_witness = reopen_precone_state_profile(profile)
    if not profile_witness["pass"]:
        return {"schema":"BC-HARMONIC-SPIRAL-GROWTH-REOPEN-1", "pass":False,
                "profile_matches":False, "root_matches":plan.root_address_id == profile.root_address_id,
                "plan_matches_recomputed":False, "provided_plan_id":plan.plan_id,
                "rebuilt_plan_id":None, "cartesian_materialisation":False,
                "profile_witness":profile_witness,
                "policy":"profile integrity failure is closed; no candidate execution or admission"}
    rebuilt = _build_harmonic_spiral_plan(profile, plan.stack_name, plan.requested_limit)
    fields_match = rebuilt == plan
    return {"schema":"BC-HARMONIC-SPIRAL-GROWTH-REOPEN-1", "pass":fields_match,
            "profile_matches":plan.profile_id == profile.profile_id,
            "root_matches":plan.root_address_id == profile.root_address_id,
            "plan_matches_recomputed":fields_match, "provided_plan_id":plan.plan_id,
            "rebuilt_plan_id":rebuilt.plan_id, "profile_witness":profile_witness,
            "cartesian_materialisation":False,
            "policy":"planning receipt only; no candidate execution or admission"}



@dataclass(frozen=True)
class CrownPreConeBudget:
    schema: str
    budget_id: str
    profile_id: str
    root_address_id: str | None
    source_cone_address: str | None
    selected_shell: str
    pre_cone_units: int
    growth_budget: int
    growth_stage: int
    cases: int
    nodes: int
    edges: int
    opens: int
    path_depth: int
    growth_sequence: tuple[int, ...]
    cumulative_growth_openings: int
    growth_profile: tuple[tuple[str, Any], ...]
    potential_capacity_ignored: bool
    policy: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema":self.schema, "budget_id":self.budget_id, "profile_id":self.profile_id,
                "root_address_id":self.root_address_id, "source_cone_address":self.source_cone_address,
                "selected_shell":self.selected_shell, "pre_cone_units":self.pre_cone_units,
                "growth_budget":self.growth_budget, "growth_stage":self.growth_stage, "cases":self.cases,
                "nodes":self.nodes, "edges":self.edges, "opens":self.opens, "path_depth":self.path_depth,
                "growth_sequence":list(self.growth_sequence),
                "cumulative_growth_openings":self.cumulative_growth_openings,
                "growth_profile":dict(self.growth_profile),
                "potential_capacity_ignored":self.potential_capacity_ignored, "policy":self.policy}


def build_precone_holistic_budget(profile: PreConeStateProfile) -> CrownPreConeBudget:
    """Port the bounded cases/nodes/edges/open/path-depth envelope for one profile."""
    if not isinstance(profile, PreConeStateProfile):
        raise TypeError("precone_profile_required")
    if not reopen_precone_state_profile(profile)["pass"]:
        raise ValueError("precone_profile_integrity_failed")
    growth = harmonic_growth_profile(profile.selected_shell, profile.pre_cone_units)
    sequence = tuple(value for value in HARMONIC_SPIRAL_CROSSOVER_BUDGETS if value <= growth["budget"])
    stage = len(sequence) - 1 if sequence else 0
    opens = sequence[-1] if sequence else 1
    cases = max(1, min(8, 1 + stage // 2))
    nodes = 24 * opens
    edges = 48 * opens
    path_depth = 1 + stage
    cumulative = sum(sequence) if sequence else 1
    policy = "present pre-cone size selects shell; Fibonacci bounds eager openings; potential cone capacity remains closed"
    body = {"schema":"BC-CROWN-PRECONE-HOLISTIC-BUDGET-1", "profile_id":profile.profile_id,
        "root_address_id":profile.root_address_id, "source_cone_address":profile.source_cone_address,
        "selected_shell":profile.selected_shell, "pre_cone_units":profile.pre_cone_units,
        "growth_budget":growth["budget"], "growth_stage":stage, "cases":cases, "nodes":nodes,
        "edges":edges, "opens":opens, "path_depth":path_depth, "growth_sequence":sequence,
        "cumulative_growth_openings":cumulative, "growth_profile":growth,
        "potential_capacity_ignored":True, "policy":policy}
    return CrownPreConeBudget(body["schema"], _sha256_text(_canonical_json(body))[:24],
        profile.profile_id, profile.root_address_id, profile.source_cone_address,
        profile.selected_shell, profile.pre_cone_units, growth["budget"], stage, cases, nodes, edges,
        opens, path_depth, sequence, cumulative, tuple(sorted(growth.items())), True, policy)


def reopen_precone_holistic_budget(profile: PreConeStateProfile,
                                    budget: CrownPreConeBudget) -> dict[str, Any]:
    if not isinstance(profile, PreConeStateProfile) or not isinstance(budget, CrownPreConeBudget):
        raise TypeError("precone_profile_and_budget_required")
    profile_witness = reopen_precone_state_profile(profile)
    if not profile_witness["pass"]:
        return {"schema":"BC-CROWN-PRECONE-BUDGET-REOPEN-1", "pass":False,
                "profile_matches":False, "plan_matches_recomputed":False,
                "provided_budget_id":budget.budget_id, "rebuilt_budget_id":None,
                "profile_witness":profile_witness}
    rebuilt = build_precone_holistic_budget(profile)
    same = rebuilt == budget
    return {"schema":"BC-CROWN-PRECONE-BUDGET-REOPEN-1", "pass":same,
            "profile_matches":budget.profile_id == profile.profile_id,
            "root_matches":budget.root_address_id == profile.root_address_id,
            "cone_matches":budget.source_cone_address == profile.source_cone_address,
            "plan_matches_recomputed":same, "provided_budget_id":budget.budget_id,
            "rebuilt_budget_id":rebuilt.budget_id, "profile_witness":profile_witness,
            "potential_capacity_ignored":True}


@dataclass(frozen=True)
class NamedPreConeQuery:
    """One distinct text query over the common, explicitly supplied root/cone."""
    query_id: str
    query_text: str
    request: PreConeRequest

    def __post_init__(self) -> None:
        if not isinstance(self.query_id, str) or not self.query_id.strip():
            raise ValueError("multi_query_id_must_be_nonempty_text")
        if not isinstance(self.query_text, str) or not self.query_text.strip():
            raise ValueError("multi_query_text_must_be_nonempty_text")
        if not isinstance(self.request, PreConeRequest):
            raise TypeError("multi_query_requires_precone_request")

    def as_dict(self) -> dict[str, Any]:
        return {"query_id": self.query_id, "query_text": self.query_text,
                "request": {"requirements": list(self.request.requirements),
                    "fine_width": self.request.fine_width,
                    "root_address_id": None if self.request.address is None else self.request.address.address_id,
                    "cone_address": None if self.request.cone is None else self.request.cone.cone_address,
                    "potential_shell": self.request.potential_shell,
                    "address_depth_override": self.request.address_depth_override}}


def _named_precone_query_fingerprint(query: NamedPreConeQuery) -> str:
    request = query.request
    if not all(isinstance(value, str) for value in request.requirements):
        raise TypeError("multi_query_requirements_must_be_text")
    if not isinstance(request.field, (tuple, list)) or not all(isinstance(value, str) for value in request.field):
        raise TypeError("multi_query_field_must_be_ordered_text_identities")
    if not isinstance(request.members, (tuple, list)) or not all(isinstance(value, str) for value in request.members):
        raise TypeError("multi_query_members_must_be_ordered_text_identities")
    if request.payload is None:
        payload_hash = None
        payload_length = 0
    else:
        payload = request.payload.encode("utf-8") if isinstance(request.payload, str) else bytes(request.payload)
        payload_hash = hashlib.sha256(payload).hexdigest()
        payload_length = len(payload)
    body = {
        "query_id": query.query_id,
        "query_text": query.query_text,
        "requirements": list(request.requirements),
        "fine_width": request.fine_width,
        "field": list(request.field),
        "members": list(request.members),
        "payload_sha256": payload_hash,
        "payload_bytes": payload_length,
        "potential_shell": request.potential_shell,
        "address_depth_override": request.address_depth_override,
        "root_address_id": None if request.address is None else request.address.address_id,
        "cone_address": None if request.cone is None else request.cone.cone_address,
    }
    return _sha256_text(_canonical_json(body))


@dataclass(frozen=True)
class CrownMultiQueryRow:
    query_id: str
    query_text: str
    request_fingerprint: str
    profile: PreConeStateProfile
    budget: CrownPreConeBudget
    stack_window: tuple[str, ...]
    stack_open_limits: tuple[int, ...]
    stack_plans: tuple[HarmonicSpiralGrowthPlan, ...]
    deferred_stack_names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"query_id": self.query_id, "query_text": self.query_text,
                "request_fingerprint": self.request_fingerprint,
                "profile": self.profile.as_dict(), "budget": self.budget.as_dict(),
                "stack_window": list(self.stack_window),
                "stack_open_limits": list(self.stack_open_limits),
                "stack_plans": [plan.as_dict() for plan in self.stack_plans],
                "deferred_stack_names": list(self.deferred_stack_names),
                "root_address_id": self.profile.root_address_id,
                "source_cone_address": self.profile.source_cone_address}


@dataclass(frozen=True)
class CrownMultiQueryPreConePlan:
    schema: str
    plan_id: str
    coordinator_profile_id: str
    root_address_id: str | None
    source_cone_address: str | None
    coordinator_budget: CrownPreConeBudget
    neighbour_radius: int
    per_query_limit: int
    stack_window: tuple[str, ...]
    request_count: int
    request_fingerprints: tuple[tuple[str, str], ...]
    query_rows: tuple[CrownMultiQueryRow, ...]
    deferred_query_ids: tuple[str, ...]
    allocated_openings: int
    reserved_nodes: int
    reserved_edges: int
    policy: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "plan_id": self.plan_id,
                "coordinator_profile_id": self.coordinator_profile_id,
                "root_address_id": self.root_address_id,
                "source_cone_address": self.source_cone_address,
                "coordinator_budget": self.coordinator_budget.as_dict(),
                "neighbour_radius": self.neighbour_radius, "per_query_limit": self.per_query_limit,
                "stack_window": list(self.stack_window), "request_count": self.request_count,
                "request_fingerprints": [[qid, fp] for qid, fp in self.request_fingerprints],
                "query_rows": [row.as_dict() for row in self.query_rows],
                "deferred_query_ids": list(self.deferred_query_ids),
                "allocated_openings": self.allocated_openings,
                "reserved_nodes": self.reserved_nodes, "reserved_edges": self.reserved_edges,
                "policy": self.policy}


def _neighbour_stack_window(selected_shell: str, neighbour_radius: int) -> tuple[str, ...]:
    if selected_shell not in HARMONIC_STACK_BY_NAME:
        raise ValueError("multi_query_selected_shell_unknown")
    if type(neighbour_radius) is not int or not 0 <= neighbour_radius <= 2:
        raise ValueError("multi_query_neighbour_radius_must_be_0_to_2")
    ordered = tuple(item.name for item in HARMONIC_STACK_SHELL_ORDER)
    center = ordered.index(selected_shell)
    result = [selected_shell]
    for offset in range(1, neighbour_radius + 1):
        if center - offset >= 0:
            result.append(ordered[center - offset])
        if center + offset < len(ordered):
            result.append(ordered[center + offset])
    return tuple(result)


def _distribute_openings(total: int, slots: int) -> tuple[int, ...]:
    if type(total) is not int or total < 0 or type(slots) is not int or slots < 0:
        raise ValueError("multi_query_opening_allocation_requires_nonnegative_exact_integers")
    if total == 0 or slots == 0:
        return () if slots == 0 else (0,) * slots
    quotient, remainder = divmod(total, slots)
    return tuple(quotient + (1 if index < remainder else 0) for index in range(slots))


def build_multi_query_precone_plan(coordinator_profile: PreConeStateProfile,
                                   queries: Sequence[NamedPreConeQuery],
                                   neighbour_radius: int = 1,
                                   per_query_limit: int = 16) -> CrownMultiQueryPreConePlan:
    """Budget a query batch without merging query identities or materialising products.

    The coordinator's envelope caps admitted query cases and all planned openings.
    Every query keeps its own profile, budget, request fingerprint and plans. Any
    over-cap queries or neighbour stacks remain explicit deferred residuals.
    """
    if not isinstance(coordinator_profile, PreConeStateProfile):
        raise TypeError("multi_query_coordinator_profile_required")
    if not reopen_precone_state_profile(coordinator_profile)["pass"]:
        raise ValueError("multi_query_coordinator_profile_integrity_failed")
    if not isinstance(queries, (tuple, list)) or not 1 <= len(queries) <= 64:
        raise ValueError("multi_query_requires_1_to_64_named_queries")
    if type(per_query_limit) is not int or not 1 <= per_query_limit <= 64:
        raise ValueError("multi_query_point_limit_must_be_1_to_64")
    if any(not isinstance(query, NamedPreConeQuery) for query in queries):
        raise TypeError("multi_query_items_must_be_named_precone_queries")
    query_ids = tuple(query.query_id for query in queries)
    if len(set(query_ids)) != len(query_ids):
        raise ValueError("multi_query_ids_must_be_unique")

    fingerprints = tuple((query.query_id, _named_precone_query_fingerprint(query)) for query in queries)
    for query in queries:
        request = query.request
        root_id = None if request.address is None else request.address.address_id
        cone_id = None if request.cone is None else request.cone.cone_address
        if root_id != coordinator_profile.root_address_id:
            raise ValueError(f"multi_query_root_address_mismatch:{query.query_id}")
        if cone_id != coordinator_profile.source_cone_address:
            raise ValueError(f"multi_query_source_cone_mismatch:{query.query_id}")
        if request.cone is not None and request.cone.root_address_id != root_id:
            raise ValueError(f"multi_query_cone_root_mismatch:{query.query_id}")

    coordinator_budget = build_precone_holistic_budget(coordinator_profile)
    stack_window = _neighbour_stack_window(coordinator_profile.selected_shell, neighbour_radius)
    active_count = min(len(queries), coordinator_budget.cases)
    active_queries = tuple(queries[:active_count])
    deferred_ids = tuple(query.query_id for query in queries[active_count:])
    query_open_allocations = _distribute_openings(coordinator_budget.opens, active_count)
    rows: list[CrownMultiQueryRow] = []
    total_openings = 0
    for index, query in enumerate(active_queries):
        profile = profile_precone_state(query.request)
        if profile.root_address_id != coordinator_profile.root_address_id or profile.source_cone_address != coordinator_profile.source_cone_address:
            raise ValueError(f"multi_query_profile_binding_mismatch:{query.query_id}")
        budget = build_precone_holistic_budget(profile)
        allowance = min(query_open_allocations[index], budget.opens, per_query_limit * len(stack_window))
        stack_count = min(len(stack_window), allowance)
        active_stacks = stack_window[:stack_count]
        deferred_stacks = stack_window[stack_count:]
        limits = _distribute_openings(allowance, stack_count)
        plans = tuple(build_harmonic_spiral_growth_plan(profile, name, limit)
                      for name, limit in zip(active_stacks, limits))
        if sum(limits) != allowance or any(not reopen_harmonic_spiral_growth_plan(profile, plan)["pass"] for plan in plans):
            raise ValueError(f"multi_query_local_plan_verification_failed:{query.query_id}")
        total_openings += sum(limits)
        rows.append(CrownMultiQueryRow(query.query_id, query.query_text, fingerprints[index][1],
            profile, budget, active_stacks, limits, plans, deferred_stacks))

    if total_openings > coordinator_budget.opens:
        raise ValueError("multi_query_global_opening_cap_exceeded")
    reserved_nodes = 24 * total_openings
    reserved_edges = 48 * total_openings
    if reserved_nodes > coordinator_budget.nodes or reserved_edges > coordinator_budget.edges:
        raise ValueError("multi_query_global_graph_cap_exceeded")
    policy = ("coordinator envelope caps active queries and total openings; each query retains an independent profile/budget; "
              "neighbouring stacks are selected by exact sorted capacity order; deferred queries/stacks remain explicit; "
              "factor-local plans are not executions")
    body = {"schema":"BC-CROWN-MULTI-QUERY-PRECONE-PLAN-1",
        "coordinator_profile_id":coordinator_profile.profile_id,
        "root_address_id":coordinator_profile.root_address_id,
        "source_cone_address":coordinator_profile.source_cone_address,
        "coordinator_budget_id":coordinator_budget.budget_id,
        "neighbour_radius":neighbour_radius, "per_query_limit":per_query_limit, "stack_window":stack_window,
        "request_count":len(queries), "request_fingerprints":fingerprints,
        "query_rows":[{"query_id":row.query_id,"query_text":row.query_text,
            "request_fingerprint":row.request_fingerprint,"profile_id":row.profile.profile_id,
            "budget_id":row.budget.budget_id,"stack_window":row.stack_window,
            "stack_open_limits":row.stack_open_limits,"stack_plan_ids":tuple(plan.plan_id for plan in row.stack_plans),
            "deferred_stack_names":row.deferred_stack_names} for row in rows],
        "deferred_query_ids":deferred_ids,"allocated_openings":total_openings,
        "reserved_nodes":reserved_nodes,"reserved_edges":reserved_edges,"policy":policy}
    plan_id = _sha256_text(_canonical_json(body))[:24]
    return CrownMultiQueryPreConePlan(body["schema"], plan_id, coordinator_profile.profile_id,
        coordinator_profile.root_address_id, coordinator_profile.source_cone_address,
        coordinator_budget, neighbour_radius, per_query_limit, stack_window, len(queries), fingerprints,
        tuple(rows), deferred_ids, total_openings, reserved_nodes, reserved_edges, policy)


def reopen_multi_query_precone_plan(coordinator_profile: PreConeStateProfile,
                                    queries: Sequence[NamedPreConeQuery],
                                    plan: CrownMultiQueryPreConePlan) -> dict[str, Any]:
    """Rebuild a portfolio from original inputs; query swaps and envelope edits fail closed."""
    if not isinstance(coordinator_profile, PreConeStateProfile) or not isinstance(plan, CrownMultiQueryPreConePlan):
        raise TypeError("multi_query_coordinator_and_plan_required")
    profile_witness = reopen_precone_state_profile(coordinator_profile)
    if not profile_witness["pass"]:
        return {"schema":"BC-CROWN-MULTI-QUERY-REOPEN-1", "pass":False,
                "profile_matches":False, "plan_matches_recomputed":False,
                "provided_plan_id":plan.plan_id, "rebuilt_plan_id":None,
                "profile_witness":profile_witness}
    try:
        rebuilt = build_multi_query_precone_plan(coordinator_profile, queries,
            neighbour_radius=plan.neighbour_radius, per_query_limit=plan.per_query_limit)
        same = rebuilt == plan
    except (TypeError, ValueError, KeyError) as exc:
        return {"schema":"BC-CROWN-MULTI-QUERY-REOPEN-1", "pass":False,
                "profile_matches":plan.coordinator_profile_id == coordinator_profile.profile_id,
                "plan_matches_recomputed":False,"provided_plan_id":plan.plan_id,
                "rebuilt_plan_id":None,"reason":f"{type(exc).__name__}:{exc}",
                "profile_witness":profile_witness}
    return {"schema":"BC-CROWN-MULTI-QUERY-REOPEN-1", "pass":same,
            "profile_matches":plan.coordinator_profile_id == coordinator_profile.profile_id,
            "root_matches":plan.root_address_id == coordinator_profile.root_address_id,
            "cone_matches":plan.source_cone_address == coordinator_profile.source_cone_address,
            "request_count_matches":plan.request_count == len(queries),
            "query_fingerprints_match":plan.request_fingerprints == rebuilt.request_fingerprints,
            "plan_matches_recomputed":same,"provided_plan_id":plan.plan_id,
            "rebuilt_plan_id":rebuilt.plan_id,"profile_witness":profile_witness,
            "allocated_openings_within_coordinator_cap":plan.allocated_openings <= plan.coordinator_budget.opens,
            "no_cartesian_materialisation":all(not p.cartesian_materialisation for r in plan.query_rows for p in r.stack_plans),
            "policy":"reopen verifies query order/fingerprints, root/cone identity, per-query plans and global envelope"}




# ---------------------------------------------------------------------------
# Harmonic64 exact-mask routing + cost-aware search + placement crossover (V7)
# ---------------------------------------------------------------------------
# The 64-bit word is an opaque carrier: its low 54 bits are a payload mask and
# its high 10 bits are alignment fields. This API does not decode either region
# into trits, infer physical hardware calibration, execute candidate glyphs or
# admit learning. All route plans remain bound to one reopened full root/cone.

HARMONIC64_WORD_BITS = 64
HARMONIC64_PAYLOAD_BITS = 54
HARMONIC64_ALIGNMENT_BITS = 10
HARMONIC64_WORD_MASK = (1 << HARMONIC64_WORD_BITS) - 1
HARMONIC64_PAYLOAD_MASK = (1 << HARMONIC64_PAYLOAD_BITS) - 1
HARMONIC64_ALIGNMENT_MASK = (1 << HARMONIC64_ALIGNMENT_BITS) - 1
HARMONIC64_POLICY = "exact_64bit_mask_coverage_then_replayable_witness_then_integer_lexicographic_cost"


def _require_harmonic64_word(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value <= HARMONIC64_WORD_MASK:
        raise ValueError(f"{label}_must_be_unsigned_64bit_integer")
    return value


def _require_low54_mask(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value <= HARMONIC64_PAYLOAD_MASK:
        raise ValueError(f"{label}_must_be_54bit_payload_mask")
    return value


def _require_alignment_mask(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value <= HARMONIC64_ALIGNMENT_MASK:
        raise ValueError(f"{label}_must_be_10bit_alignment_mask")
    return value


@dataclass(frozen=True)
class Harmonic64RouteQuery:
    query_id: str
    required_payload_mask: int
    required_alignment_mask: int = 0
    source_cone_address: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.query_id, str) or not self.query_id.strip():
            raise ValueError("harmonic64_query_id_must_be_nonempty")
        _require_low54_mask(self.required_payload_mask, "harmonic64_required_payload_mask")
        _require_alignment_mask(self.required_alignment_mask, "harmonic64_required_alignment_mask")
        if self.required_payload_mask == 0 and self.required_alignment_mask == 0:
            raise ValueError("harmonic64_query_requires_at_least_one_mask_bit")
        if not isinstance(self.source_cone_address, str) or not self.source_cone_address:
            raise ValueError("harmonic64_query_requires_source_cone_address")

    def as_dict(self) -> dict[str, Any]:
        return {"query_id": self.query_id, "required_payload_mask": self.required_payload_mask,
                "required_alignment_mask": self.required_alignment_mask,
                "source_cone_address": self.source_cone_address}


@dataclass(frozen=True)
class Harmonic64RouteCandidate:
    candidate_id: str
    glyph_name: str
    carrier_word: int
    semantic_edges: int
    bit_operations: int
    mechanical_depth: int
    routing_depth: int
    reopened_states: int
    source_cone_address: str
    witness: FullAddressWitness

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("harmonic64_candidate_id_must_be_nonempty")
        if not isinstance(self.glyph_name, str) or not self.glyph_name.strip():
            raise ValueError("harmonic64_candidate_glyph_name_must_be_nonempty")
        _require_harmonic64_word(self.carrier_word, "harmonic64_candidate_carrier_word")
        for label in ("semantic_edges", "bit_operations", "mechanical_depth", "routing_depth", "reopened_states"):
            if type(getattr(self, label)) is not int or getattr(self, label) < 0:
                raise ValueError(f"harmonic64_{label}_must_be_nonnegative_exact_integer")
        if not isinstance(self.source_cone_address, str) or not self.source_cone_address:
            raise ValueError("harmonic64_candidate_requires_source_cone_address")
        if not isinstance(self.witness, FullAddressWitness):
            raise TypeError("harmonic64_candidate_requires_full_address_witness")

    @property
    def payload_mask(self) -> int:
        return self.carrier_word & HARMONIC64_PAYLOAD_MASK

    @property
    def alignment_mask(self) -> int:
        return (self.carrier_word >> HARMONIC64_PAYLOAD_BITS) & HARMONIC64_ALIGNMENT_MASK

    @property
    def cost_key(self) -> tuple[int, int, int, int, int, str]:
        # No guessed scalar weights: compare each integer cost dimension in a
        # stable order, keeping candidate identity as the final deterministic tie-break.
        return (self.reopened_states, self.semantic_edges, self.bit_operations,
                self.mechanical_depth, self.routing_depth, self.candidate_id)

    def as_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "glyph_name": self.glyph_name,
                "carrier_word": self.carrier_word, "payload_mask": self.payload_mask,
                "alignment_mask": self.alignment_mask,
                "cost": {"reopened_states": self.reopened_states, "semantic_edges": self.semantic_edges,
                         "bit_operations": self.bit_operations, "mechanical_depth": self.mechanical_depth,
                         "routing_depth": self.routing_depth},
                "cost_key": list(self.cost_key), "source_cone_address": self.source_cone_address,
                "witness_id": self.witness.witness_id, "witness_parent_address_id": self.witness.start.address_id,
                "witness_end_address_id": self.witness.end.address_id}


def _require_route_candidate_witness(address: BCFloorAddress, cone: DepthWaveCone,
                                     candidate: Harmonic64RouteCandidate) -> None:
    if candidate.glyph_name not in GLYPH_CATALOG.names():
        raise ValueError(f"harmonic64_candidate_glyph_not_registered:{candidate.candidate_id}")
    if candidate.source_cone_address != cone.cone_address:
        raise ValueError(f"harmonic64_candidate_cone_mismatch:{candidate.candidate_id}")
    witness = candidate.witness
    if not witness.events:
        raise ValueError(f"harmonic64_candidate_witness_has_no_transition_events:{candidate.candidate_id}")
    if witness.start.address_id != address.address_id:
        raise ValueError(f"harmonic64_candidate_witness_parent_mismatch:{candidate.candidate_id}")
    if not witness.dependency_closed or not witness.difference_replays or witness.unresolved:
        raise ValueError(f"harmonic64_candidate_witness_not_closed:{candidate.candidate_id}")
    try:
        replayed = witness.delta.apply(address)
    except Exception as exc:
        raise ValueError(f"harmonic64_candidate_delta_replay_failed:{candidate.candidate_id}:{type(exc).__name__}") from exc
    if replayed.address_id != witness.end.address_id:
        raise ValueError(f"harmonic64_candidate_end_mismatch:{candidate.candidate_id}")


@dataclass(frozen=True)
class Harmonic64RouteChoice:
    query_id: str
    candidate_id: str
    glyph_name: str
    cost_key: tuple[int, int, int, int, int, str]
    required_payload_mask: int
    required_alignment_mask: int
    provided_payload_mask: int
    provided_alignment_mask: int
    witness_id: str

    def as_dict(self) -> dict[str, Any]:
        return {"query_id": self.query_id, "candidate_id": self.candidate_id,
                "glyph_name": self.glyph_name, "cost_key": list(self.cost_key),
                "required_payload_mask": self.required_payload_mask,
                "required_alignment_mask": self.required_alignment_mask,
                "provided_payload_mask": self.provided_payload_mask,
                "provided_alignment_mask": self.provided_alignment_mask,
                "witness_id": self.witness_id}


@dataclass(frozen=True)
class Harmonic64RoutePlan:
    schema: str
    plan_id: str
    root_address_id: str
    source_cone_address: str
    multi_query_plan_id: str
    source_query_fingerprints: tuple[tuple[str, str], ...]
    route_query_fingerprints: tuple[tuple[str, str], ...]
    candidate_fingerprints: tuple[tuple[str, str], ...]
    choices: tuple[Harmonic64RouteChoice, ...]
    unresolved_residuals: tuple[str, ...]
    deferred_query_ids: tuple[str, ...]
    candidate_count: int
    policy: str
    carrier_contract: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "plan_id": self.plan_id, "root_address_id": self.root_address_id,
                "source_cone_address": self.source_cone_address, "multi_query_plan_id": self.multi_query_plan_id,
                "source_query_fingerprints": [[a, b] for a, b in self.source_query_fingerprints],
                "route_query_fingerprints": [[a, b] for a, b in self.route_query_fingerprints],
                "candidate_fingerprints": [[a, b] for a, b in self.candidate_fingerprints],
                "choices": [choice.as_dict() for choice in self.choices],
                "unresolved_residuals": list(self.unresolved_residuals),
                "deferred_query_ids": list(self.deferred_query_ids), "candidate_count": self.candidate_count,
                "policy": self.policy, "carrier_contract": self.carrier_contract,
                "execution_performed": False, "glyph_admission": False, "persistent_save": False}


def _harmonic64_route_candidate_fingerprint(candidate: Harmonic64RouteCandidate) -> str:
    body = {"candidate_id": candidate.candidate_id, "glyph_name": candidate.glyph_name,
            "carrier_word": candidate.carrier_word, "semantic_edges": candidate.semantic_edges,
            "bit_operations": candidate.bit_operations, "mechanical_depth": candidate.mechanical_depth,
            "routing_depth": candidate.routing_depth, "reopened_states": candidate.reopened_states,
            "source_cone_address": candidate.source_cone_address,
            "witness_id": candidate.witness.witness_id,
            "witness_parent_address_id": candidate.witness.start.address_id,
            "witness_end_address_id": candidate.witness.end.address_id}
    return _sha256_text(_canonical_json(body))


def _build_harmonic64_route_plan(address: BCFloorAddress, cone: DepthWaveCone,
        coordinator_profile: PreConeStateProfile, source_queries: Sequence[NamedPreConeQuery],
        multi_query_plan: CrownMultiQueryPreConePlan, route_queries: Sequence[Harmonic64RouteQuery],
        candidates: Sequence[Harmonic64RouteCandidate]) -> Harmonic64RoutePlan:
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("harmonic64_route_requires_full_address_and_depth_wave_cone")
    if cone.root_address_id != address.address_id:
        raise ValueError("harmonic64_route_cone_root_mismatch")
    if not reopen_depth_wave_cone(address, cone).pass_all:
        raise ValueError("harmonic64_route_cone_reopen_failed")
    if (coordinator_profile.root_address_id != address.address_id or
            coordinator_profile.source_cone_address != cone.cone_address):
        raise ValueError("harmonic64_route_profile_root_cone_mismatch")
    portfolio_reopen = reopen_multi_query_precone_plan(coordinator_profile, source_queries, multi_query_plan)
    if not portfolio_reopen.get("pass"):
        raise ValueError("harmonic64_route_multi_query_reopen_failed")
    if multi_query_plan.root_address_id != address.address_id or multi_query_plan.source_cone_address != cone.cone_address:
        raise ValueError("harmonic64_route_portfolio_root_cone_mismatch")
    if not isinstance(route_queries, (tuple, list)) or not 1 <= len(route_queries) <= 64 or any(
            not isinstance(q, Harmonic64RouteQuery) for q in route_queries):
        raise ValueError("harmonic64_route_queries_must_be_1_to_64_typed_items")
    route_ids = tuple(q.query_id for q in route_queries)
    if len(set(route_ids)) != len(route_ids):
        raise ValueError("harmonic64_route_query_ids_must_be_unique")
    expected_ids = tuple(row.query_id for row in multi_query_plan.query_rows)
    if route_ids != expected_ids:
        raise ValueError("harmonic64_route_queries_must_match_admitted_portfolio_order")
    for query in route_queries:
        if query.source_cone_address != cone.cone_address:
            raise ValueError(f"harmonic64_route_query_cone_mismatch:{query.query_id}")
    if not isinstance(candidates, (tuple, list)) or len(candidates) > 256 or any(
            not isinstance(c, Harmonic64RouteCandidate) for c in candidates):
        raise ValueError("harmonic64_route_candidates_must_be_0_to_256_typed_items")
    candidate_ids = tuple(c.candidate_id for c in candidates)
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("harmonic64_candidate_ids_must_be_unique")
    for candidate in candidates:
        _require_route_candidate_witness(address, cone, candidate)

    choices: list[Harmonic64RouteChoice] = []
    residuals: list[str] = []
    candidate_fingerprints = tuple(sorted((c.candidate_id, _harmonic64_route_candidate_fingerprint(c)) for c in candidates))
    route_fingerprints = tuple((q.query_id, _sha256_text(_canonical_json(q.as_dict()))) for q in route_queries)
    for query in route_queries:
        eligible = [c for c in candidates
            if query.required_payload_mask & ~c.payload_mask == 0 and
               query.required_alignment_mask & ~c.alignment_mask == 0]
        if not eligible:
            residuals.append(f"{query.query_id}:no_exact_64bit_mask_coverage")
            continue
        winner = min(eligible, key=lambda candidate: candidate.cost_key)
        choices.append(Harmonic64RouteChoice(query.query_id, winner.candidate_id, winner.glyph_name,
            winner.cost_key, query.required_payload_mask, query.required_alignment_mask,
            winner.payload_mask, winner.alignment_mask, winner.witness.witness_id))
    deferred = tuple(multi_query_plan.deferred_query_ids)
    policy = HARMONIC64_POLICY
    carrier_contract = ("unsigned 64-bit opaque carrier; low 54 bits are exact payload-mask coverage; "
                        "high 10 bits are exact alignment-mask coverage; bit membership is not a trit decoder "
                        "or physical hardware calibration")
    body = {"schema":"BC-HARMONIC64-ROUTE-PLAN-1", "root_address_id":address.address_id,
        "source_cone_address":cone.cone_address, "multi_query_plan_id":multi_query_plan.plan_id,
        "source_query_fingerprints":multi_query_plan.request_fingerprints,
        "route_query_fingerprints":route_fingerprints, "candidate_fingerprints":candidate_fingerprints,
        "choices":[choice.as_dict() for choice in choices], "unresolved_residuals":tuple(residuals),
        "deferred_query_ids":deferred, "candidate_count":len(candidates), "policy":policy,
        "carrier_contract":carrier_contract}
    return Harmonic64RoutePlan(body["schema"], _sha256_text(_canonical_json(body))[:24], address.address_id,
        cone.cone_address, multi_query_plan.plan_id, tuple(body["source_query_fingerprints"]), route_fingerprints,
        candidate_fingerprints, tuple(choices), tuple(residuals), deferred, len(candidates), policy, carrier_contract)


def build_harmonic64_route_plan(address: BCFloorAddress, cone: DepthWaveCone,
        coordinator_profile: PreConeStateProfile, source_queries: Sequence[NamedPreConeQuery],
        multi_query_plan: CrownMultiQueryPreConePlan, route_queries: Sequence[Harmonic64RouteQuery],
        candidates: Sequence[Harmonic64RouteCandidate]) -> Harmonic64RoutePlan:
    """Plan exact mask routing over the admitted query portfolio; do not execute routes."""
    return _build_harmonic64_route_plan(address, cone, coordinator_profile, source_queries,
                                        multi_query_plan, route_queries, candidates)


def reopen_harmonic64_route_plan(address: BCFloorAddress, cone: DepthWaveCone,
        coordinator_profile: PreConeStateProfile, source_queries: Sequence[NamedPreConeQuery],
        multi_query_plan: CrownMultiQueryPreConePlan, route_queries: Sequence[Harmonic64RouteQuery],
        candidates: Sequence[Harmonic64RouteCandidate], plan: Harmonic64RoutePlan) -> dict[str, Any]:
    if not isinstance(plan, Harmonic64RoutePlan):
        raise TypeError("harmonic64_route_plan_required")
    try:
        rebuilt = _build_harmonic64_route_plan(address, cone, coordinator_profile, source_queries,
                                               multi_query_plan, route_queries, candidates)
    except Exception as exc:
        return {"schema":"BC-HARMONIC64-ROUTE-REOPEN-1", "pass":False,
                "provided_plan_id":plan.plan_id, "rebuilt_plan_id":None,
                "reason":f"{type(exc).__name__}:{exc}"}
    same = rebuilt == plan
    return {"schema":"BC-HARMONIC64-ROUTE-REOPEN-1", "pass":same,
            "provided_plan_id":plan.plan_id, "rebuilt_plan_id":rebuilt.plan_id,
            "root_matches":plan.root_address_id == address.address_id,
            "cone_matches":plan.source_cone_address == cone.cone_address,
            "portfolio_matches":plan.multi_query_plan_id == multi_query_plan.plan_id,
            "candidate_masks_and_witnesses_recomputed":same,
            "execution_performed":False, "glyph_admission":False}


# Explicit finite coverage evidence gates placement strategy crossover. The
# evidence is recomputed from the supplied target addresses; no full product is
# materialised, and an uncovered target prevents selection altogether.
PLACEMENT_STRATEGIES = ("fibonacci", "lexical", "doubling")


def _lexical_factor_points(shape: tuple[int, ...], limit: int) -> tuple[tuple[int, ...], ...]:
    origin = (0,) * len(shape)
    out: list[tuple[int, ...]] = [origin]
    seen = {origin}
    for factor in range(len(shape)):
        for value in range(1, shape[factor]):
            point = [0] * len(shape); point[factor] = value; row = tuple(point)
            if row not in seen:
                seen.add(row); out.append(row)
                if len(out) >= limit: return tuple(out)
    # Bounded adjacent-factor combinations, not a Cartesian materialisation.
    for left_factor in range(len(shape) - 1):
        right_factor = left_factor + 1
        for left_value in range(1, shape[left_factor]):
            for right_value in range(1, shape[right_factor]):
                row_list = [0] * len(shape)
                row_list[left_factor] = left_value; row_list[right_factor] = right_value
                row = tuple(row_list)
                if row not in seen:
                    seen.add(row); out.append(row)
                    if len(out) >= limit: return tuple(out)
    return tuple(out[:limit])


def _doubling_factor_offsets(bound: int) -> tuple[int, ...]:
    out = [0]; seen = {0}; value = 1
    while len(out) < bound:
        state = value % bound
        if state not in seen:
            seen.add(state); out.append(state)
        value *= 2
        if value > (1 << 20): break
    for state in range(bound):
        if state not in seen:
            seen.add(state); out.append(state)
            if len(out) >= bound: break
    return tuple(out[:bound])


def _doubling_factor_points(shape: tuple[int, ...], limit: int) -> tuple[tuple[int, ...], ...]:
    per = tuple(_doubling_factor_offsets(dim) for dim in shape)
    origin = (0,) * len(shape); out = [origin]; seen = {origin}; depth = 1
    while len(out) < limit:
        added = False
        for factor_index in range(len(shape)):
            if depth < len(per[factor_index]):
                row = [0] * len(shape); row[factor_index] = per[factor_index][depth]; pt = tuple(row)
                if pt not in seen:
                    seen.add(pt); out.append(pt); added = True
                    if len(out) >= limit: break
        if len(out) < limit and depth > 0:
            for factor_index in range(len(shape) - 1):
                if depth < len(per[factor_index]) and depth < len(per[factor_index + 1]):
                    row = [0] * len(shape)
                    row[factor_index] = per[factor_index][depth]
                    row[factor_index + 1] = per[factor_index + 1][depth]
                    pt = tuple(row)
                    if pt not in seen:
                        seen.add(pt); out.append(pt); added = True
                        if len(out) >= limit: break
        depth += 1
        if not added and depth >= max(len(v) for v in per): break
    # Keep contract useful even for small factors or a sparse doubling orbit.
    if len(out) < limit:
        for pt in _lexical_factor_points(shape, limit):
            if pt not in seen:
                seen.add(pt); out.append(pt)
                if len(out) >= limit: break
    return tuple(out[:limit])


def _placement_cost(points: tuple[tuple[int, ...], ...]) -> tuple[int, int, int, int]:
    touched_factor_count = sum(sum(1 for value in point if value != 0) for point in points)
    address_travel = 0
    factor_switches = 0
    previous = (0,) * (len(points[0]) if points else 0)
    previous_active: tuple[int, ...] = ()
    for point in points:
        address_travel += sum(abs(a - b) for a, b in zip(previous, point))
        active = tuple(i for i, (a, b) in enumerate(zip(previous, point)) if a != b)
        if active and previous_active and active != previous_active:
            factor_switches += 1
        if active: previous_active = active
        previous = point
    return (touched_factor_count, address_travel, factor_switches, len(points))


@dataclass(frozen=True)
class PlacementStrategyEvidence:
    strategy: str
    points: tuple[tuple[int, ...], ...]
    covered_targets: tuple[tuple[int, ...], ...]
    deferred_targets: tuple[tuple[int, ...], ...]
    cost_key: tuple[int, int, int, int, str]

    def as_dict(self) -> dict[str, Any]:
        return {"strategy":self.strategy, "points":[list(p) for p in self.points],
                "covered_targets":[list(p) for p in self.covered_targets],
                "deferred_targets":[list(p) for p in self.deferred_targets], "cost_key":list(self.cost_key)}


@dataclass(frozen=True)
class PlacementCrossoverPlan:
    schema: str
    plan_id: str
    profile_id: str
    root_address_id: str | None
    source_cone_address: str | None
    stack_name: str
    shape: tuple[int, ...]
    limit: int
    target_points: tuple[tuple[int, ...], ...]
    evidence: tuple[PlacementStrategyEvidence, ...]
    selected_strategy: str | None
    selected_points: tuple[tuple[int, ...], ...]
    deferred_targets: tuple[tuple[int, ...], ...]
    coverage_closed: bool
    policy: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema":self.schema, "plan_id":self.plan_id, "profile_id":self.profile_id,
                "root_address_id":self.root_address_id, "source_cone_address":self.source_cone_address,
                "stack_name":self.stack_name, "shape":list(self.shape), "limit":self.limit,
                "target_points":[list(p) for p in self.target_points],
                "evidence":[e.as_dict() for e in self.evidence], "selected_strategy":self.selected_strategy,
                "selected_points":[list(p) for p in self.selected_points],
                "deferred_targets":[list(p) for p in self.deferred_targets],
                "coverage_closed":self.coverage_closed, "cartesian_materialisation":False,
                "execution_performed":False, "policy":self.policy}


def _build_placement_crossover_plan(profile: PreConeStateProfile, stack_name: str, limit: int,
                                    target_points: Sequence[Sequence[int]]) -> PlacementCrossoverPlan:
    if not isinstance(profile, PreConeStateProfile) or not reopen_precone_state_profile(profile)["pass"]:
        raise ValueError("placement_crossover_requires_reopened_precone_profile")
    if stack_name not in HARMONIC_STACK_BY_NAME:
        raise ValueError("placement_crossover_unknown_stack")
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError("placement_crossover_limit_must_be_1_to_64")
    shape = HARMONIC_STACK_BY_NAME[stack_name].shape
    if not isinstance(target_points, (tuple, list)) or not 1 <= len(target_points) <= 64:
        raise ValueError("placement_crossover_requires_1_to_64_target_points")
    checked: list[tuple[int, ...]] = []
    for point in target_points:
        if not isinstance(point, (tuple, list)) or len(point) != len(shape) or any(type(v) is not int for v in point):
            raise ValueError("placement_crossover_target_shape_mismatch")
        row = tuple(point)
        if any(not 0 <= row[i] < shape[i] for i in range(len(shape))):
            raise ValueError("placement_crossover_target_outside_factor_bounds")
        checked.append(row)
    targets = tuple(dict.fromkeys(checked))
    if len(targets) != len(checked):
        raise ValueError("placement_crossover_target_points_must_be_unique")
    generated = {
        "fibonacci": factorized_spiral(shape, limit=limit),
        "lexical": _lexical_factor_points(shape, limit),
        "doubling": _doubling_factor_points(shape, limit),
    }
    evidence: list[PlacementStrategyEvidence] = []
    for strategy in PLACEMENT_STRATEGIES:
        points = generated[strategy]
        seen = set(points)
        covered = tuple(target for target in targets if target in seen)
        deferred = tuple(target for target in targets if target not in seen)
        raw_cost = _placement_cost(points)
        evidence.append(PlacementStrategyEvidence(strategy, points, covered, deferred,
                         (len(deferred), raw_cost[0], raw_cost[1], raw_cost[2], strategy)))
    complete = [item for item in evidence if not item.deferred_targets]
    selected = min(complete, key=lambda item: item.cost_key) if complete else None
    selected_strategy = None if selected is None else selected.strategy
    selected_points = () if selected is None else selected.points
    deferred = () if selected is not None else targets
    policy = ("recompute finite target coverage for Fibonacci, lexical and doubling factor-local schedules; "
              "select lexicographically lowest exact cost only among full-coverage schedules; otherwise preserve targets as residuals")
    body = {"schema":"BC-PLACEMENT-CROSSOVER-PLAN-1", "profile_id":profile.profile_id,
        "root_address_id":profile.root_address_id, "source_cone_address":profile.source_cone_address,
        "stack_name":stack_name, "shape":shape, "limit":limit, "target_points":targets,
        "evidence":[item.as_dict() for item in evidence], "selected_strategy":selected_strategy,
        "selected_points":selected_points, "deferred_targets":deferred, "coverage_closed":selected is not None,
        "policy":policy}
    return PlacementCrossoverPlan(body["schema"], _sha256_text(_canonical_json(body))[:24], profile.profile_id,
        profile.root_address_id, profile.source_cone_address, stack_name, shape, limit, targets, tuple(evidence),
        selected_strategy, selected_points, deferred, selected is not None, policy)


def build_placement_crossover_plan(profile: PreConeStateProfile, stack_name: str, limit: int,
                                   target_points: Sequence[Sequence[int]]) -> PlacementCrossoverPlan:
    """Select a factor-local placement only when a finite supplied target set is fully covered."""
    return _build_placement_crossover_plan(profile, stack_name, limit, target_points)


def reopen_placement_crossover_plan(profile: PreConeStateProfile, plan: PlacementCrossoverPlan) -> dict[str, Any]:
    if not isinstance(plan, PlacementCrossoverPlan):
        raise TypeError("placement_crossover_plan_required")
    try:
        rebuilt = _build_placement_crossover_plan(profile, plan.stack_name, plan.limit, plan.target_points)
    except Exception as exc:
        return {"schema":"BC-PLACEMENT-CROSSOVER-REOPEN-1", "pass":False,
                "provided_plan_id":plan.plan_id, "rebuilt_plan_id":None,
                "reason":f"{type(exc).__name__}:{exc}"}
    return {"schema":"BC-PLACEMENT-CROSSOVER-REOPEN-1", "pass":rebuilt == plan,
            "provided_plan_id":plan.plan_id, "rebuilt_plan_id":rebuilt.plan_id,
            "coverage_recomputed":True, "all_strategy_costs_recomputed":True,
            "root_matches":plan.root_address_id == profile.root_address_id,
            "cone_matches":plan.source_cone_address == profile.source_cone_address,
            "cartesian_materialisation":False}

REGISTRY = CanonicalRegistry()
REGISTRY.register("circle_step", circle_step, "pure")
REGISTRY.register("fold_down", fold_down, "pure")
REGISTRY.register("source_read", read_source_text, "source_read")
REGISTRY.register("full_address_execute", full_address_witness, "pure")
REGISTRY.register("rotate_fractional_turn", rotate_fractional_turn, "pure")
REGISTRY.register("legacy_source_inventory", inspect_legacy_source, "source_read")
REGISTRY.register("migration_matrix", clean_migration_matrix, "pure")
REGISTRY.register("exact_circle_step", exact_circle_step, "pure")
REGISTRY.register("floor_page_from_circle", FloorPage.from_circle_addr, "pure")
REGISTRY.register("lattice216_physical_step", Lattice216.move_physical, "pure")
REGISTRY.register("lattice216_advance27", Lattice216.advance_27, "pure")
REGISTRY.register("sphere_storage_record", sphere_storage_record, "pure")
REGISTRY.register("floor_address_transition", FULL_ADDRESS_KERNEL.apply, "pure")
REGISTRY.register("harmonic_head_step", harmonic_head_step, "pure")
REGISTRY.register("harmonic_antipode_relation", harmonic_antipode_relation, "pure")
REGISTRY.register("prime_harmonic_fold_views", prime_harmonic_fold_views, "pure")
REGISTRY.register("harmonic_circle_alignment", harmonic_circle_alignment, "pure")
REGISTRY.register("cross_harmonic_circle_boundary", cross_harmonic_circle_boundary, "pure")
REGISTRY.register("build_six_plane_perspective", build_six_plane_perspective, "pure")
REGISTRY.register("reopen_six_plane_perspective", reopen_six_plane_perspective, "pure")
REGISTRY.register("open_structuralizer_zero_plane", open_structuralizer_zero_plane, "pure")
REGISTRY.register("reopen_structuralizer_zero_plane", reopen_structuralizer_zero_plane, "pure")
REGISTRY.register("solve_three_point_difference", solve_three_point_difference, "pure")
REGISTRY.register("reopen_three_point_difference", reopen_three_point_difference, "pure")
REGISTRY.register("copy_three_point_hallway", copy_three_point_hallway, "pure")
REGISTRY.register("reopen_three_point_hallway_copy", reopen_three_point_hallway_copy, "pure")
REGISTRY.register("floor_box_address", FloorBoxAddress.from_surface, "pure")
REGISTRY.register("aperture_alignment_216", aperture_alignment_216, "pure")
REGISTRY.register("resolve_recursive_child_address", resolve_recursive_child_address, "pure")
REGISTRY.register("open_depth_wave_cone", open_depth_wave_cone, "pure")
REGISTRY.register("reopen_depth_wave_cone", reopen_depth_wave_cone, "pure")
REGISTRY.register("crown_depth_wave_view", crown_depth_wave_view, "pure")
REGISTRY.register("propose_depth_wave_input", propose_depth_wave_input, "pure")
REGISTRY.register("observe_depth_wave_self_feed", observe_depth_wave_self_feed, "pure")
REGISTRY.register("build_depth_wave_structuralizer_view", build_depth_wave_structuralizer_view, "pure")
REGISTRY.register("reopen_depth_wave_structuralizer_view", reopen_depth_wave_structuralizer_view, "pure")
REGISTRY.register("execute_bound_depth_wave_fold", execute_bound_depth_wave_fold, "pure")
REGISTRY.register("open_prime_rpm_address", open_prime_rpm_address, "pure")
REGISTRY.register("prime_rpm_step", prime_rpm_step, "pure")
REGISTRY.register("reopen_prime_rpm_transition", reopen_prime_rpm_transition, "pure")
REGISTRY.register("profile_precone_state", profile_precone_state, "pure")
REGISTRY.register("reopen_precone_state_profile", reopen_precone_state_profile, "pure")
REGISTRY.register("harmonic_growth_profile", harmonic_growth_profile, "pure")
REGISTRY.register("build_harmonic_spiral_growth_plan", build_harmonic_spiral_growth_plan, "pure")
REGISTRY.register("reopen_harmonic_spiral_growth_plan", reopen_harmonic_spiral_growth_plan, "pure")
REGISTRY.register("build_precone_holistic_budget", build_precone_holistic_budget, "pure")
REGISTRY.register("reopen_precone_holistic_budget", reopen_precone_holistic_budget, "pure")
REGISTRY.register("build_multi_query_precone_plan", build_multi_query_precone_plan, "pure")
REGISTRY.register("reopen_multi_query_precone_plan", reopen_multi_query_precone_plan, "pure")
REGISTRY.register("build_harmonic64_route_plan", build_harmonic64_route_plan, "pure")
REGISTRY.register("reopen_harmonic64_route_plan", reopen_harmonic64_route_plan, "pure")
REGISTRY.register("build_placement_crossover_plan", build_placement_crossover_plan, "pure")
REGISTRY.register("reopen_placement_crossover_plan", reopen_placement_crossover_plan, "pure")


@dataclass(frozen=True)
class GlyphSpec:
    """Declarative identity for one clean resident operation."""
    name: str
    executor_name: str
    required_args: tuple[str, ...]
    optional_args: tuple[str, ...]
    arg_types: tuple[tuple[str, str], ...]
    effect_scope: str
    witness_contract: str
    claim_boundary: str = "typed execution is not automatic semantic or physical certification"
    address: str = ""

    @classmethod
    def make(cls, name: str, executor_name: str, required_args: Sequence[str],
             optional_args: Sequence[str], arg_types: Mapping[str, str], effect_scope: str,
             witness_contract: str) -> "GlyphSpec":
        type_rows = tuple(sorted(arg_types.items()))
        body = {"schema":"BC-GLYPH-SPEC-2", "name":name, "executor":executor_name,
                "required":list(required_args), "optional":list(optional_args),
                "arg_types":type_rows, "effect_scope":effect_scope, "witness_contract":witness_contract}
        return cls(name, executor_name, tuple(required_args), tuple(optional_args), type_rows,
                   effect_scope, witness_contract, address=_sha256_text(_canonical_json(body))[:24])


class GlyphCatalogue:
    """Single addressable catalogue; no dynamic alias/redefinition mechanism."""
    def __init__(self, registry: CanonicalRegistry, authority: EffectAuthority) -> None:
        self._registry = registry
        self._authority = authority
        self._specs: dict[str, GlyphSpec] = {}

    def register(self, spec: GlyphSpec) -> None:
        if not spec.name or spec.name in self._specs:
            raise ValueError(f"duplicate_or_empty_glyph_name:{spec.name}")
        executor = self._registry.resolve(spec.executor_name)
        if executor.effect != spec.effect_scope:
            raise ValueError(f"glyph_executor_effect_mismatch:{spec.name}")
        expected_names = set(spec.required_args) | set(spec.optional_args)
        if expected_names != {key for key, _ in spec.arg_types}:
            raise ValueError(f"glyph_argument_contract_incomplete:{spec.name}")
        self._specs[spec.name] = spec

    def resolve(self, name: str) -> GlyphSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise LookupError(f"unregistered_glyph:{name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    def describe(self) -> tuple[dict[str, Any], ...]:
        return tuple({"name":s.name, "address":s.address, "executor":s.executor_name,
                      "required_args":list(s.required_args), "optional_args":list(s.optional_args),
                      "arg_types":dict(s.arg_types), "effect_scope":s.effect_scope,
                      "witness_contract":s.witness_contract, "claim_boundary":s.claim_boundary}
                     for s in sorted(self._specs.values(), key=lambda x: x.name))

    def _validate_arg(self, name: str, kind: str, value: Any) -> None:
        valid = True
        if kind == "integer": valid = type(value) is int
        elif kind == "nonnegative_integer": valid = type(value) is int and value >= 0
        elif kind == "positive_integer": valid = type(value) is int and value > 0
        elif kind == "axis_index": valid = type(value) is int and value in (0, 1, 2)
        elif kind == "axis_name": valid = isinstance(value, str) and value in AXES
        elif kind == "binary_triple": valid = isinstance(value, (tuple, list)) and len(value) == 3 and all(type(v) is int and v in (0,1) for v in value)
        elif kind == "path_parts": valid = isinstance(value, (tuple, list)) and bool(value) and all(type(v) is int or isinstance(v, str) for v in value)
        elif kind == "floor_page": valid = isinstance(value, FloorPage)
        elif kind == "lattice216": valid = isinstance(value, Lattice216)
        elif kind == "generic_address": valid = isinstance(value, BCAddress)
        elif kind == "full_address": valid = isinstance(value, BCFloorAddress)
        elif kind == "harmonic_head_address": valid = isinstance(value, PrimeHarmonicAddress)
        elif kind == "rotation_surface": valid = isinstance(value, RotationSurface)
        elif kind == "point3_sequence": valid = isinstance(value, (tuple, list)) and all(
            isinstance(point, (tuple, list)) and len(point) == 3 and all(type(c) is int for c in point) for point in value)
        elif kind == "exact_integer_point3": valid = isinstance(value, (tuple, list)) and len(value) == 3 and all(type(c) is int for c in value)
        elif kind == "two_indexed_point3_values": valid = isinstance(value, Mapping) and len(value) == 2 and all(
            type(idx) is int and idx in (0,1,2) and isinstance(point, (tuple,list)) and len(point) == 3 and all(type(c) is int for c in point)
            for idx, point in value.items())
        elif kind == "index_0_to_2": valid = type(value) is int and value in (0,1,2)
        elif kind == "six_plane_name": valid = isinstance(value, str) and value in {name for name, _frame in PLANE_FRAMES}
        elif kind == "structuralizer_zero_plane_frame": valid = isinstance(value, StructuralizerZeroPlaneFrame)
        elif kind == "three_point_difference_solution": valid = isinstance(value, ThreePointDifferenceSolution)
        elif kind == "three_point_hallway_copy": valid = isinstance(value, ThreePointHallwayCopy)
        elif kind == "six_plane_packet": valid = isinstance(value, SixPlanePerspectivePacket)
        elif kind == "command_resolution_packet": valid = isinstance(value, CommandResolutionPacket)
        elif kind == "legacy_command_behavior_packet": valid = isinstance(value, LegacyCommandBehaviorPacket)
        elif kind == "address_operation": valid = isinstance(value, AddressOperation)
        elif kind == "address_operations": valid = isinstance(value, (tuple, list)) and all(isinstance(v, AddressOperation) for v in value)
        elif kind == "exact_rational": valid = isinstance(value, ExactRational)
        elif kind == "string": valid = isinstance(value, str)
        elif kind == "packet_schema_kind": valid = isinstance(value, str) and value in _HOST_PACKET_SCHEMA_BY_KIND
        elif kind == "host_packet_mapping": valid = isinstance(value, dict)
        elif kind == "packet_validation_receipt": valid = isinstance(value, dict)
        elif kind == "host_packet_serialization_receipt": valid = isinstance(value, dict)
        elif kind == "packet_batch_entries": valid = isinstance(value, (tuple, list))
        elif kind == "host_packet_batch_receipt": valid = isinstance(value, dict)
        elif kind == "sha256_or_none": valid = value is None or isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())
        elif kind == "integer_sequence": valid = isinstance(value, (tuple, list)) and all(type(v) is int for v in value)
        elif kind == "boolean": valid = type(value) is bool
        elif kind == "recursive_child_address": valid = isinstance(value, RecursiveChildAddress)
        elif kind == "depth_wave_cone": valid = isinstance(value, DepthWaveCone)
        elif kind == "glyph_learning_ledger": valid = isinstance(value, GlyphLearningLedger)
        elif kind == "engine_self_map": valid = isinstance(value, EngineSelfMap)
        elif kind == "depth_wave_self_feed_observation": valid = isinstance(value, DepthWaveSelfFeedObservation)
        elif kind == "compound_glyph_spec": valid = isinstance(value, CompoundGlyphSpec)
        elif kind == "compound_glyph_run": valid = isinstance(value, CompoundGlyphRun)
        elif kind == "learning_profile": valid = isinstance(value, LearningProfile)
        elif kind == "learning_proposal_set": valid = isinstance(value, LearningProposalSet)
        elif kind == "learning_comparison_map": valid = isinstance(value, LearningComparisonMap)
        elif kind == "address_relation_map": valid = isinstance(value, AddressRelationMap)
        elif kind == "typed_address_cone_sequence": valid = isinstance(value, (tuple, list)) and all(isinstance(v, Mapping) and isinstance(v.get("address"), BCFloorAddress) and isinstance(v.get("cone"), DepthWaveCone) for v in value)
        elif kind == "address_onehot_wave": valid = isinstance(value, AddressOneHotWave)
        elif kind == "address_onehot_waves": valid = isinstance(value, (tuple, list)) and bool(value) and all(isinstance(v, AddressOneHotWave) for v in value)
        elif kind == "wave_glyph_comparison_map": valid = isinstance(value, WaveGlyphComparisonMap)
        elif kind == "address_wave_glyph": valid = isinstance(value, AddressWaveGlyph)
        elif kind == "harmonic_fractal_frame": valid = isinstance(value, HarmonicFractalFrame)
        elif kind == "harmonic_fractal_comparison": valid = isinstance(value, HarmonicFractalComparison)
        elif kind == "mapping": valid = isinstance(value, Mapping)
        elif kind == "crown_engine_map": valid = isinstance(value, CrownEngineMap) or isinstance(value, Mapping) and value.get("schema") == "BC-CROWN-ENGINE-MAP-1"
        elif kind == "mapping_or_null": valid = value is None or isinstance(value, Mapping)
        elif kind == "step_mapping_sequence": valid = isinstance(value, (tuple, list)) and len(value) <= _FRACTAL_BATCH_MAX_STEPS and all(isinstance(v, Mapping) for v in value)
        elif kind == "full_address_witness": valid = isinstance(value, FullAddressWitness)
        elif kind == "full_address_witness_sequence": valid = isinstance(value, (tuple, list)) and all(isinstance(v, FullAddressWitness) for v in value)
        elif kind == "addressed_frame_map": valid = isinstance(value, Mapping) and all(isinstance(k, str) and (isinstance(v, Mapping) or callable(getattr(v, "as_dict", None))) for k, v in value.items())
        elif kind == "glyph_reference_sequence": valid = isinstance(value, (tuple, list)) and all(isinstance(v, str) and bool(v) for v in value)
        elif kind == "residual_sequence": valid = isinstance(value, (tuple, list)) and all(isinstance(row, (tuple, list)) and all(isinstance(item, str) for item in row) for row in value)
        elif kind == "shared_context_event_bundle": valid = isinstance(value, Mapping) and value.get("schema") == "BC-SHARED-CONTEXT-EVENT-BUNDLE-1"
        elif kind == "shared_context_event_segments": valid = isinstance(value, Mapping) and value.get("schema") == "BC-SHARED-CONTEXT-EVENT-SEGMENTS-1"
        elif kind == "address_id_sequence": valid = isinstance(value, (tuple, list)) and all(isinstance(x, str) and len(x) == 24 and all(c in "0123456789abcdef" for c in x) for x in value)
        elif kind == "relation_route_id_sequence": valid = isinstance(value, (tuple, list)) and len(value) <= 256 and all(isinstance(x, str) and len(x) == 24 and all(c in "0123456789abcdef" for c in x) for x in value)
        elif kind == "relation_route_batch": valid = isinstance(value, Mapping) and value.get("schema") == "BC-ADDRESS-RELATION-OPEN-BATCH-1"
        elif kind == "control_harmonic_step_sequence": valid = isinstance(value, (tuple, list)) and len(value) <= 64 and all(isinstance(x, Mapping) for x in value)
        elif kind == "control_harmonic_chain": valid = isinstance(value, Mapping) and value.get("schema") == "BC-COG64-HARMONIC-CHAIN-1"
        elif kind == "control_harmonic_state_space": valid = isinstance(value, Mapping) and value.get("schema") == "BC-COG64-HARMONIC-STATE-SPACE-1"
        elif kind == "control_harmonic_state_space_page": valid = isinstance(value, Mapping) and value.get("schema") == "BC-COG64-HARMONIC-SPACE-OPEN-1"
        elif kind == "address_id": valid = isinstance(value, str) and len(value) == 24 and all(c in "0123456789abcdef" for c in value)
        elif kind == "potential_workload_sequence": valid = isinstance(value, (tuple, list)) and all(isinstance(v, Mapping) for v in value)
        elif kind == "fractal_hallway_predictor_cone": valid = isinstance(value, Mapping) and value.get("schema") == "BC-FRACTAL-HALLWAY-PREDICTOR-CONE-1"
        elif kind == "depth_wave_structuralizer_link": valid = isinstance(value, DepthWaveStructuralizerLink)
        elif kind == "prime_rpm_address": valid = isinstance(value, PrimeRPMAddress)
        elif kind == "prime_rpm_transition": valid = isinstance(value, PrimeRPMTransition)
        elif kind == "precone_request": valid = isinstance(value, PreConeRequest)
        elif kind == "precone_state_profile": valid = isinstance(value, PreConeStateProfile)
        elif kind == "harmonic_growth_plan": valid = isinstance(value, HarmonicSpiralGrowthPlan)
        elif kind == "crown_precone_budget": valid = isinstance(value, CrownPreConeBudget)
        elif kind == "named_precone_query": valid = isinstance(value, NamedPreConeQuery)
        elif kind == "named_precone_queries": valid = isinstance(value, (tuple, list)) and all(isinstance(v, NamedPreConeQuery) for v in value)
        elif kind == "crown_multi_query_plan": valid = isinstance(value, CrownMultiQueryPreConePlan)
        elif kind == "harmonic64_route_query": valid = isinstance(value, Harmonic64RouteQuery)
        elif kind == "harmonic64_route_queries": valid = isinstance(value, (tuple, list)) and all(isinstance(v, Harmonic64RouteQuery) for v in value)
        elif kind == "harmonic64_route_candidate": valid = isinstance(value, Harmonic64RouteCandidate)
        elif kind == "harmonic64_route_candidates": valid = isinstance(value, (tuple, list)) and all(isinstance(v, Harmonic64RouteCandidate) for v in value)
        elif kind == "harmonic64_route_plan": valid = isinstance(value, Harmonic64RoutePlan)
        elif kind == "placement_crossover_plan": valid = isinstance(value, PlacementCrossoverPlan)
        elif kind == "factor_point_sequence": valid = isinstance(value, (tuple, list)) and all(isinstance(p, (tuple, list)) and all(type(v) is int for v in p) for p in value)
        elif kind == "harmonic_stack_name": valid = isinstance(value, str) and value in HARMONIC_STACK_BY_NAME
        elif kind == "ordered_prime_sequence": valid = isinstance(value, (tuple, list)) and bool(value) and all(type(v) is int for v in value)
        elif kind == "explicit_prime_integer_rates": valid = isinstance(value, Mapping) and all(type(k) is int and type(v) is int for k, v in value.items())
        elif kind == "integer_at_least_2": valid = type(value) is int and value >= 2
        elif kind == "bounded_positive_integer": valid = type(value) is int and 1 <= value <= 32
        elif kind == "integer_or_none": valid = value is None or type(value) is int
        elif kind == "harmonic_stack_name_or_none": valid = value is None or isinstance(value, str) and value in HARMONIC_STACK_BY_NAME
        elif kind == "sphere504_radix_step": valid = isinstance(value, Sphere504RadixStep)
        elif kind == "prime_cog_bundle": valid = isinstance(value, PrimeCogBundle)
        elif kind == "harmonic_fractal_step": valid = isinstance(value, HarmonicFractalStep)
        elif kind == "bounded_exact_integer": valid = type(value) is int and abs(value) <= MAX_PRIME_RPM_MOMENTUM
        elif kind == "signed_prime_sequence": valid = value is None or isinstance(value, (tuple, list)) and len(value) <= MAX_ORDERED_PRIME_WORD and all(type(v) is int for v in value)
        elif kind == "integer_sequence_or_mapping": valid = value is None or isinstance(value, Mapping) and all(type(k) is int and type(v) is int for k, v in value.items()) or isinstance(value, (tuple, list)) and all(type(v) is int for v in value)
        else: raise ValueError(f"unknown_glyph_argument_type:{kind}")
        if not valid:
            raise TypeError(f"glyph_argument_type_error:{name}:{kind}")

    def execute(self, name: str, *, grants: Iterable[str] = (), **arguments: Any) -> Any:
        spec = self.resolve(name)
        missing = set(spec.required_args) - set(arguments)
        extra = set(arguments) - set(spec.required_args) - set(spec.optional_args)
        if missing: raise ValueError(f"glyph_missing_arguments:{','.join(sorted(missing))}")
        if extra: raise ValueError(f"glyph_unknown_arguments:{','.join(sorted(extra))}")
        types = dict(spec.arg_types)
        for key, value in arguments.items(): self._validate_arg(key, types[key], value)
        if spec.effect_scope != "pure" and not self._authority.authorize(spec.effect_scope, grants):
            raise PermissionError(f"glyph_effect_not_authorized:{spec.effect_scope}")
        record = self._registry.resolve(spec.executor_name)
        positional = [arguments[key] for key in spec.required_args]
        optional = {key: arguments[key] for key in spec.optional_args if key in arguments}
        return record.executor(*positional, **optional)


GLYPH_CATALOG = GlyphCatalogue(REGISTRY, EffectAuthority())
for _spec in (
    GlyphSpec.make("BC.CIRCLE.STEP", "exact_circle_step", ("octant", "circle_addr", "axis", "ticks"), (),
                   {"octant":"binary_triple", "circle_addr":"positive_integer", "axis":"axis_index", "ticks":"integer"}, "pure",
                   "exact 360-step Gray-boundary return and inverse"),
    GlyphSpec.make("BC.PAGE.FROM_CIRCLE", "floor_page_from_circle", ("axis", "address"), (),
                   {"axis":"axis_name", "address":"positive_integer"}, "pure", "exact 1..90 page-state reconstruction"),
    GlyphSpec.make("BC.SPHERE.STORAGE", "sphere_storage_record", ("sphere_index",), (),
                   {"sphere_index":"nonnegative_integer"}, "pure", "eight sphere indices and eight cube slots each"),
    GlyphSpec.make("BC.LATTICE216.PHYSICAL_STEP", "lattice216_physical_step", ("lattice", "axis", "direction"), (),
                   {"lattice":"lattice216", "axis":"axis_index", "direction":"integer"}, "pure",
                   "exact adjacent 6x6x6 move or explicit boundary residual"),
    GlyphSpec.make("BC.LATTICE216.ADVANCE27", "lattice216_advance27", ("lattice", "steps"), (),
                   {"lattice":"lattice216", "steps":"integer"}, "pure", "exact 27-factor carry returned separately"),
    GlyphSpec.make("BC.ADDRESS.TRANSITION", "floor_address_transition", ("address", "operation"), (),
                   {"address":"full_address", "operation":"address_operation"}, "pure",
                   "one typed atom mutates the complete addressed carrier"),
    GlyphSpec.make("BC.ADDRESS.CHAIN", "full_address_execute", ("start", "ops"), (),
                   {"start":"full_address", "ops":"address_operations"}, "pure",
                   "full root-to-end route, typed delta, and replay witness"),
    GlyphSpec.make("BC.FOLD.DOWN", "fold_down", ("address", "path", "steps", "modulus"), (),
                   {"address":"generic_address", "path":"path_parts", "steps":"integer", "modulus":"positive_integer"}, "pure",
                   "parent-bound difference replay; dependency/return/replay statuses kept separate"),
    GlyphSpec.make("BC.ROTATION.RATIONAL_TURN", "rotate_fractional_turn", ("start", "axis", "turns"),
                   ("max_promotions", "preferred_radices"),
                   {"start":"full_address", "axis":"axis_name", "turns":"exact_rational",
                    "max_promotions":"nonnegative_integer", "preferred_radices":"integer_sequence"}, "pure",
                   "exact rational angle, integer ticks, shell promotion and residual witness"),
    GlyphSpec.make("BC.SOURCE.PARSE", "source_read", ("source",), ("filename",),
                   {"source":"string", "filename":"string"}, "source_read", "AST/compile only; source is not executed"),
    GlyphSpec.make("BC.SOURCE.MIGRATION_MAP", "legacy_source_inventory", ("source_path",), ("expected_sha256",),
                   {"source_path":"string", "expected_sha256":"sha256_or_none"}, "source_read",
                   "hash-bound static map; source is not imported or executed"),
    GlyphSpec.make("BC.CAPABILITY.MIGRATION_MATRIX", "migration_matrix", (), (),
                   {}, "pure", "explicit migrated/pending capabilities; never overstates parity"),
    GlyphSpec.make("BC.PHA.HEAD.STEP", "harmonic_head_step", ("address", "steps"), (),
                   {"address":"harmonic_head_address", "steps":"integer"}, "pure",
                   "exact 504-headed integer transition; winding retained on cyclic return"),
    GlyphSpec.make("BC.PHA.ANTIPODE", "harmonic_antipode_relation", ("address",), (),
                   {"address":"harmonic_head_address"}, "pure",
                   "252-step antipode; 504 directed heads and 252 pairs; midpoint is implicit"),
    GlyphSpec.make("BC.PHA.FOLD.VIEWS", "prime_harmonic_fold_views", ("address",), (),
                   {"address":"harmonic_head_address"}, "pure",
                   "derived (3),(3,5),(3,5,7) aperture views; no implied head motion"),
    GlyphSpec.make("BC.PHA.504x360.ALIGN", "harmonic_circle_alignment", ("address", "surface"),
                   ("axis",), {"address":"harmonic_head_address", "surface":"rotation_surface", "axis":"axis_index"},
                   "pure", "exact phase relation on the common 2520-unit turn refinement"),
    GlyphSpec.make("BC.PHA.CROSS.FLOOR", "cross_harmonic_circle_boundary", ("address", "surface", "repetitions"),
                   ("axis",), {"address":"harmonic_head_address", "surface":"rotation_surface", "repetitions":"integer", "axis":"axis_index"},
                   "pure", "7 harmonic-head steps per 5 floor-circle ticks; residual and closure states separate"),
    GlyphSpec.make("BC.PRIME.RPM.OPEN", "open_prime_rpm_address", ("parent",),
                   ("prime_lenses", "rpm_rates", "phase_modulus", "phase", "start_positions"),
                   {"parent":"full_address", "prime_lenses":"ordered_prime_sequence", "rpm_rates":"explicit_prime_integer_rates",
                    "phase_modulus":"integer_at_least_2", "phase":"integer", "start_positions":"integer_sequence_or_mapping"},
                   "pure", "core 3/5/7 rate lanes are fixed; each higher prime stays an explicit dependency residual until bound"),
    GlyphSpec.make("BC.PRIME.RPM.STEP", "prime_rpm_step", ("address",),
                   ("momentum_ticks", "ordered_word", "target", "reference", "winding"),
                   {"address":"prime_rpm_address", "momentum_ticks":"bounded_exact_integer", "ordered_word":"signed_prime_sequence",
                    "target":"integer_or_none", "reference":"integer", "winding":"integer_or_none"},
                   "pure", "exact integer lane movement with rates and winding preserved; physical RPM is not calibrated"),
    GlyphSpec.make("BC.PRIME.RPM.REOPEN", "reopen_prime_rpm_transition", ("before", "transition"), (),
                   {"before":"prime_rpm_address", "transition":"prime_rpm_transition"}, "pure",
                   "recompute the lane transition and verify exact address, lane deltas, target relation, and ordered trace"),
    GlyphSpec.make("BC.STRUCTURALIZER.SIX_PLANES", "build_six_plane_perspective", ("carrier", "points"), (),
                   {"carrier":"full_address", "points":"point3_sequence"}, "pure",
                   "six ordered plane views with depth residuals, exact lift-back and squared-distance witness"),
    GlyphSpec.make("BC.STRUCTURALIZER.REOPEN", "reopen_six_plane_perspective", ("carrier", "points", "packet"), (),
                   {"carrier":"full_address", "points":"point3_sequence", "packet":"six_plane_packet"}, "pure",
                   "rebuild view packet from its exact source carrier and point binding; reject tampering"),
    GlyphSpec.make("BC.STRUCTURALIZER.ZERO_PLANE.OPEN", "open_structuralizer_zero_plane", ("carrier",), ("zero_origin", "plane_name"),
                   {"carrier":"full_address", "zero_origin":"exact_integer_point3", "plane_name":"six_plane_name"}, "pure",
                   "address a VM zero origin against one named shared signed-permutation aperture frame"),
    GlyphSpec.make("BC.STRUCTURALIZER.ZERO_PLANE.REOPEN", "reopen_structuralizer_zero_plane", ("carrier", "frame_packet"), (),
                   {"carrier":"full_address", "frame_packet":"structuralizer_zero_plane_frame"}, "pure",
                   "re-open the VM zero-plane frame against the same authoritative full address and exact frame transform"),
    GlyphSpec.make("BC.STRUCTURALIZER.THREE_POINT.SOLVE", "solve_three_point_difference",
                   ("carrier", "known_points", "missing_index"), ("zero_origin", "plane_name", "zero_plane"),
                   {"carrier":"full_address", "known_points":"two_indexed_point3_values", "missing_index":"index_0_to_2",
                    "zero_origin":"exact_integer_point3", "plane_name":"six_plane_name", "zero_plane":"structuralizer_zero_plane_frame"}, "pure",
                   "derive the missing point only under explicit ordered_equal_step; zero-frame differences and all six inverse frames are witnessed"),
    GlyphSpec.make("BC.STRUCTURALIZER.THREE_POINT.REOPEN", "reopen_three_point_difference", ("carrier", "solution"), (),
                   {"carrier":"full_address", "solution":"three_point_difference_solution"}, "pure",
                   "rebuild the missing point, all six plane round-trips and perspective packet against the exact carrier"),
    GlyphSpec.make("BC.STRUCTURALIZER.HALLWAY.COPY", "copy_three_point_hallway",
                   ("source_carrier", "solution", "target_carrier", "target_zero_origin"), ("target_plane_name",),
                   {"source_carrier":"full_address", "solution":"three_point_difference_solution", "target_carrier":"full_address",
                    "target_zero_origin":"exact_integer_point3", "target_plane_name":"six_plane_name"}, "pure",
                   "copy only the solved relative relation through another named zero-plane frame; neither carrier is mutated"),
    GlyphSpec.make("BC.STRUCTURALIZER.HALLWAY.REOPEN", "reopen_three_point_hallway_copy",
                   ("source_carrier", "solution", "target_carrier", "packet"), (),
                   {"source_carrier":"full_address", "solution":"three_point_difference_solution", "target_carrier":"full_address",
                    "packet":"three_point_hallway_copy"}, "pure",
                   "rebuild hallway-copy relationship against source solution, both zero-plane frames and target perspective"),
    GlyphSpec.make("BC.ADDRESS.BOX216", "floor_box_address", ("surface", "axis"), (),
                   {"surface":"rotation_surface", "axis":"axis_name"}, "pure",
                   "one of 216 box positions; local one-hot/all-off state is separate from box identity"),
    GlyphSpec.make("BC.APERTURE.ALIGNMENT.216", "aperture_alignment_216", (), (), {}, "pure",
                   "box and cube families share cardinality only; their addresses are not equivalent"),
    GlyphSpec.make("BC.RECURSIVE.CHILD.RESOLVE", "resolve_recursive_child_address", ("address", "level_index"), (),
                   {"address":"full_address", "level_index":"nonnegative_integer"}, "pure",
                   "resolve a named levels[i].lattice216 child bound to parent, box slot, side and payload id"),
    GlyphSpec.make("BC.DEPTH.WAVE.OPEN", "open_depth_wave_cone", ("address", "max_recursive_depth", "wave_radius"),
                   ("target_child", "include_root_lattice"),
                   {"address":"full_address", "max_recursive_depth":"nonnegative_integer", "wave_radius":"nonnegative_integer",
                    "target_child":"recursive_child_address", "include_root_lattice":"boolean"}, "pure",
                   "bounded depth×wave cone; recursion depth, local graph radius, box aperture and cube aperture remain distinct"),
    GlyphSpec.make("BC.DEPTH.WAVE.REOPEN", "reopen_depth_wave_cone", ("address", "cone"), (),
                   {"address":"full_address", "cone":"depth_wave_cone"}, "pure",
                   "rebuild node set, frontier, child binding and closure against the exact root address"),
    GlyphSpec.make("BC.CROWN.DEPTH.WAVE", "crown_depth_wave_view", ("address", "cone"), (),
                   {"address":"full_address", "cone":"depth_wave_cone"}, "pure",
                   "Crown fold/aperture view over the same addressed cone; observation only"),
    GlyphSpec.make("BC.INPUT.DEPTH.WAVE.PROPOSE", "propose_depth_wave_input", ("address", "cone", "relation"), ("operations",),
                   {"address":"full_address", "cone":"depth_wave_cone", "relation":"string", "operations":"address_operations"}, "pure",
                   "LLM/input relation proposal bound to a root-verified cone; proposal is not execution or glyph admission"),
    GlyphSpec.make("BC.SELF_FEED.DEPTH.WAVE.OBSERVE", "observe_depth_wave_self_feed", ("address", "cone", "witness"), (),
                   {"address":"full_address", "cone":"depth_wave_cone", "witness":"full_address_witness"}, "pure",
                   "observe and replay-bind a transition on the cone; no persistence or automatic admission"),
    GlyphSpec.make("BC.STRUCTURALIZER.DEPTH.WAVE.VIEW", "build_depth_wave_structuralizer_view", ("address", "cone", "child"), (),
                   {"address":"full_address", "cone":"depth_wave_cone", "child":"recursive_child_address"}, "pure",
                   "build six-plane perspective from child-local cube-native coordinates and exact source carrier"),
    GlyphSpec.make("BC.STRUCTURALIZER.DEPTH.WAVE.REOPEN", "reopen_depth_wave_structuralizer_view", ("address", "cone", "child", "link"), (),
                   {"address":"full_address", "cone":"depth_wave_cone", "child":"recursive_child_address", "link":"depth_wave_structuralizer_link"}, "pure",
                   "reopen structuralizer packet against same root, cone, child and derived points"),
    GlyphSpec.make("BC.DEPTH.WAVE.HARMONIC.FOLD", "execute_bound_depth_wave_fold",
                   ("address", "cone", "child", "repetitions", "axis", "child_operation"), ("prime_rpm_operations",),
                   {"address":"full_address", "cone":"depth_wave_cone", "child":"recursive_child_address",
                    "repetitions":"integer", "axis":"axis_name", "child_operation":"address_operation",
                    "prime_rpm_operations":"address_operations"}, "pure",
                   "one authoritative full-address witness combines harmonic crossing, an explicitly named child operation and optional explicit prime-RPM operations; equal aperture size infers no mapping"),
    GlyphSpec.make("BC.CROWN.PRECONE.PROFILE", "profile_precone_state", ("request",), (),
                   {"request":"precone_request"}, "pure",
                   "profile only supplied present-state dimensions; latent cone capacity is reported but never determines the work budget"),
    GlyphSpec.make("BC.CROWN.PRECONE.REOPEN", "reopen_precone_state_profile", ("profile",), (),
                   {"profile":"precone_state_profile"}, "pure",
                   "recompute pre-cone profile content address, present-state arithmetic and smallest-shell selection"),
    GlyphSpec.make("BC.CROWN.FIBONACCI.GROWTH", "harmonic_growth_profile", ("stack_name", "pre_cone_units"), (),
                   {"stack_name":"harmonic_stack_name", "pre_cone_units":"positive_integer"}, "pure",
                   "bounded Fibonacci opening budget by named harmonic stack; no Cartesian state-space materialization"),
    GlyphSpec.make("BC.CROWN.SPIRAL.PLAN", "build_harmonic_spiral_growth_plan", ("profile", "stack_name"), ("limit",),
                   {"profile":"precone_state_profile", "stack_name":"harmonic_stack_name", "limit":"integer_at_least_2"}, "pure",
                   "deterministic factor-local placement plan, separate from execution and glyph admission"),
    GlyphSpec.make("BC.CROWN.SPIRAL.REOPEN", "reopen_harmonic_spiral_growth_plan", ("profile", "plan"), (),
                   {"profile":"precone_state_profile", "plan":"harmonic_growth_plan"}, "pure",
                   "rebuild plan against exact profile, root address, stack, limit and factor-local spiral points"),
    GlyphSpec.make("BC.CROWN.PRECONE.BUDGET", "build_precone_holistic_budget", ("profile",), (),
                   {"profile":"precone_state_profile"}, "pure",
                   "derive a bounded cases/nodes/edges/openings/path-depth envelope from the present-state profile"),
    GlyphSpec.make("BC.CROWN.PRECONE.BUDGET.REOPEN", "reopen_precone_holistic_budget", ("profile", "budget"), (),
                   {"profile":"precone_state_profile", "budget":"crown_precone_budget"}, "pure",
                   "recompute holistic budget against exact profile, root, cone, Fibonacci sequence and operation envelope"),
    GlyphSpec.make("BC.CROWN.MULTI_QUERY.PLAN", "build_multi_query_precone_plan", ("coordinator_profile", "queries"),
                   ("neighbour_radius", "per_query_limit"),
                   {"coordinator_profile":"precone_state_profile", "queries":"named_precone_queries",
                    "neighbour_radius":"nonnegative_integer", "per_query_limit":"positive_integer"}, "pure",
                   "bounded multi-query plan; every query keeps independent source-bound profile and budget; excess cases/stacks remain residuals"),
    GlyphSpec.make("BC.CROWN.MULTI_QUERY.REOPEN", "reopen_multi_query_precone_plan", ("coordinator_profile", "queries", "plan"), (),
                   {"coordinator_profile":"precone_state_profile", "queries":"named_precone_queries",
                    "plan":"crown_multi_query_plan"}, "pure",
                   "rebuild query fingerprints, same-root/same-cone boundary, adjacent-stack schedules and global budget; no query executes"),
    GlyphSpec.make("BC.HARMONIC64.ROUTE.PLAN", "build_harmonic64_route_plan",
                   ("address", "cone", "coordinator_profile", "source_queries", "multi_query_plan", "route_queries", "candidates"), (),
                   {"address":"full_address", "cone":"depth_wave_cone", "coordinator_profile":"precone_state_profile",
                    "source_queries":"named_precone_queries", "multi_query_plan":"crown_multi_query_plan",
                    "route_queries":"harmonic64_route_queries", "candidates":"harmonic64_route_candidates"}, "pure",
                   "exact opaque-64-bit mask coverage plus replayable witness and integer cost ordering, bound to the admitted same-root/same-cone query portfolio; planning only"),
    GlyphSpec.make("BC.HARMONIC64.ROUTE.REOPEN", "reopen_harmonic64_route_plan",
                   ("address", "cone", "coordinator_profile", "source_queries", "multi_query_plan", "route_queries", "candidates", "plan"), (),
                   {"address":"full_address", "cone":"depth_wave_cone", "coordinator_profile":"precone_state_profile",
                    "source_queries":"named_precone_queries", "multi_query_plan":"crown_multi_query_plan",
                    "route_queries":"harmonic64_route_queries", "candidates":"harmonic64_route_candidates",
                    "plan":"harmonic64_route_plan"}, "pure",
                   "recompute portfolio, masks, candidate fingerprints, parent-bound replay evidence, deterministic costs, route choices and unresolved residuals"),
    GlyphSpec.make("BC.CROWN.PLACEMENT.CROSSOVER", "build_placement_crossover_plan",
                   ("profile", "stack_name", "limit", "target_points"), (),
                   {"profile":"precone_state_profile", "stack_name":"harmonic_stack_name", "limit":"positive_integer",
                    "target_points":"factor_point_sequence"}, "pure",
                   "measure exact finite coverage for Fibonacci, lexical and doubling factor-local schedules; select only if every supplied target is covered; no Cartesian materialisation"),
    GlyphSpec.make("BC.CROWN.PLACEMENT.CROSSOVER.REOPEN", "reopen_placement_crossover_plan", ("profile", "plan"), (),
                   {"profile":"precone_state_profile", "plan":"placement_crossover_plan"}, "pure",
                   "recompute each strategy's exact points, coverage witnesses, integer costs, selected strategy and deferred targets"),
):
    GLYPH_CATALOG.register(_spec)


# ---------------------------------------------------------------------------
# Source-hash-bound historical command/dependency evidence ROM (V8)
# ---------------------------------------------------------------------------
LEGACY_COMMAND_SOURCE_SHA256 = '5abe5d866230448e3f9b8b22090937204f18ce126184f61727ecbfd448565e52'
LEGACY_COMMAND_SOURCE_BYTES = 6176692
LEGACY_EXECUTOR_ASSIGNMENT_ROWS = ()
LEGACY_CAPTURED_ALIAS_ROWS = ()
LEGACY_DUPLICATE_DEFINITION_ROWS = ()
LEGACY_DYNAMIC_LOOKUP_ROWS = ()

# Legacy static data stays inside this standalone source as a compressed ROM.
# Routine boots use a small cached summary; full rows/indices are materialized on demand.
_LEGACY_STATIC_ROM_LOADED = False
_LEGACY_STATIC_ROM_STATUS = {"state":"not_loaded", "error":None}
_LEGACY_STATIC_SUMMARY_CACHE = None
_LEGACY_EXECUTOR_KEYS = {}
_LEGACY_EXECUTOR_EXPRESSIONS = {}
_LEGACY_EXECUTOR_SYMBOLS = {}
_LEGACY_CAPTURED_ALIASES = {}
_LEGACY_DUPLICATE_DEFINITIONS = {}
_LEGACY_DYNAMIC_LOOKUPS = {}
LEGACY_REASSIGNED_EXECUTOR_KEY_COUNT = 72
LEGACY_UNIQUE_LITERAL_EXECUTOR_KEY_COUNT = 505
LEGACY_UNIQUE_EXECUTOR_KEY_EXPRESSION_COUNT = 516
LEGACY_DYNAMIC_LOOKUP_SITE_COUNT = 744
LEGACY_BEHAVIOR_ASSIGNMENT_COUNT = 805
LEGACY_BEHAVIOR_PROFILE_COUNT = 1033
LEGACY_BEHAVIOR_SYMBOLS_WITH_PROFILES = 651
LEGACY_BEHAVIOR_REASSIGNED_KEYS = 69
LEGACY_BEHAVIOR_AMBIGUOUS_SYMBOLS = 129

_LEGACY_STATIC_ROM_SHA256 = '762fce4bd54234f9f2698c989e22ae12cb071060bd5227661a67564880717e7f'
_LEGACY_STATIC_ROM_COMPANION = "BC_LEGACY_STATIC_ROM.zlib"
_LEGACY_STATIC_ROM_COMPRESSED_SHA256 = "598225435726270e4c7e770d705d8d7797982b83c176a732684d6e050379ffbe"
_LEGACY_SUMMARY_SHA256 = 'a680a1da2fffc94091addab6e9b00c452b883c52106e2cb4d07c0ff40108fce0'
_LEGACY_SUMMARY_B85 = (
    'c-qZcYjc~r7X2^&oX+r&1mqjRIN=l<UyRe{p1H#a5D9bqI@oTT+v$J5OW+6imFCpbx%m)}(MH;9?T7Z3{JoQi7yhM~mz~@19ll=8r+ihUF`pEC87IXoD`wA~'
    '+ni69;-)eFJb7Kb#5|i8%Vja2?Ico;H!{8wab8STqKu1WJe#lLrI_-Wd~s3E=XvLLRjwhOiM*H<D@-7t;|&p~^Yv^MXT@?=7Rh>5&HcTjbZ%8mzv-x*TS}Fi'
    'j@G#)8a{M9w{AN4(C|U<4MG$`Hyxw?V&X&nfu*2$F^gCHxn5#f;RPJ%^!FONt*4z^698VsR4)FC_pneppHA1aBIT8m#k_u+Pv-Ly=(AERF%cm*oflqC=Ma<v'
    '?4~mjyqtl$I2Glp$Tt&U(12=Fk-l)qF5|EBa*{!LOi)6pVk!xkt;+diB480sS8qDY)x6}-A}$3cU5XkOG+d{vbqPED7c4`~MNz$i>DRM#!eN%Y5Sd)j0(|jJ'
    'q%a<o#=!GzDnN2M{|e<zg*Jx8w}r$c!7g9;LR2)Rd@{jAK*gs?#wA3sy?mV}b3A9JF4tV}aw)RL1kz+!IfptGdC5F`-I{qR=g{%qOCjNbo=Lo%ugg@#$?HlE'
    'Gu2?s(oRW0F^#g$ZHMwi(9C2^(-lHYq32d&CYq*LilrNxLUPqig{m>tBsnJ343Q>z22skWpjt=T>6xdm;4c$#O@icX<IEdnvv`N0#w^vNpraHun~<0kaCWHp'
    'mw1(<mK<D6cm+6tQMX~SjF)`6n81pEem~{@1y=858Rv@7b()ft^OV7(G@_&#(-SM_n%Zf)GnV`F(2@VMw<xBIXK=nRA|Awc6!bkOez5zV9|Z%?9>kyQupdh%'
    'pgCku$~>xsRDzPQVg}_kO}FR)#`$dWx()1IxKH_FA;SP7U&KC5ELT+)sa#?P?g0W`dY%!DDQTjo%t&?J%oUOIBx9zfYJzgp;`y&K@~^Qyh{pZ67mNp8JMw}J'
    'G31z-6QbZpKjz2yjr@R-oUvTVHB~3nRB2)=LL?$HG^S~W@vHodB0F+xO4u<a_2_99tn0EsjY~9GS<Y2O(}hJ$!=gG-DN9T(S1n5yDzSc*hA6ZLBX92>#xWNS'
    'kyBwq6y>^vsPtmoWNN|{jTr``sVc)q%@b;ZpPc4tM*cA&4_X|33S!rHohSrW$Ez8k%~Wzi=uxH05hvuzsYGu0=Q%M=HO+IXa8u#T)YOC}iYgLQWsER|DaV}b'
    'Yl3rhI1g^$8%5z$?D$^)E>@d~<8bh?_QbtQ7{3#K&T?UBoLDrcrk-U66@q9+ni4};rXj8ZpI(Gdl@@&ScfwDZ$PGgvFDQVn5RI7l(+$;3z=ri6_`3mAx4cYW'
    'PGSz-k=JzxQ9N?((0P!?H(ThhoFG+lF(EJ|w+zk76jNg;g(%m#Nfm{2ix{+4?GXN91$@9lj%qrq2Nyj3ORO3+3?H6Go@4v%%~Cg-1TgYD6C&f8B21bQg=(p)'
    'DOq9=i|8r0QkpVLc|U&ChtH_M&tv!9?!6lx<EFn8H&G44B37Dc!pa2t3XLk6h0TGeikVva`*DjevWGZ=jq<1)!qQIcK1#Pggl(u-hOL;FaAz4xXj9D$T~k!q'
    '7g&kLjf68sF+`L1<F0nbV)c3w`XKV6r(?|8bupXd@}5s}PRukBEYmVACz-A?A`~+-lGLK<`ynsC3b8oGJM#KtzYc20>Bgf^t~-?2Spz$@uAbd5R)AE6!F4Ma'
    '8A==@*O`vqP$eoSL`yV!BE7eJ`9tLB+miXWc%CdpiLDM_<K;>$nk?9Z?p^R1MR1K?ZCc*EvbS3ogIv%w$@Emqbe0fPPZF9ailUhsT7c9_=v&|$rx*u3Bx(G@'
    'NGz#HUsJ3HjR9oO!kz3G!#?^&2Xc}R=gINicB!Wu#JKu)cQF<cJ!dIZQndW4i8eq6W2&I=$puk}YF>qrQsfhnu6}}((Cx`uIPO|U#F*Fa3*M*#b3(xfwXpfA'
    '%%T(<giaNPdPo;ap8XOri&7qBEl?CqwlAPWk{n4rrp325NyE_VyYUe9kssULE-I!GswGL3Of7xybDJ!vXk5EyP?d{h@q}wc=$6V<s#?04r3#`erJADWNvgkt'
    'tee9I>-<sPF|YG7DOP;X=|;58X7mucVDrHqxp5HQd6B(m)d~7T?=UJ+{4;j#TI8bhsaz;3{&6CBo)VUz^-|FpD+&5_o`|>kJafEyn7zd$-=3%LNW)Bjty>A)'
    '^?P7ufEIPnlph2i$H?cFdDyMO=vOAoyy$!ys&hThgsCu)BMh!m%}`WBB#dQ=aw3Jjk+S%=0^#_TFWyL4_Gb@q_{ko|eS7rrIALA8kYksRcHlEcVzLC-b)+s`'
    'p(#4&L_s1;GnKrXhULq=T;ZWq@hk_UhailcaRds62Mm}<2iInRU1C5Nx@n+!Czizs%@|QrGs|;5<LGE~Q+pQ!tCvy;w7;8NovdYTSHn1!PDaBAH*{n9LY=K;'
    'CJ7oxVf$>NYxL^8T-@WC5Xd(sdRTdYlQAnxsW7#~$SukQJCU7#E_-ZV;_IwvR=wSzZ+nB-9(TRysNU1A4PDbNb~ibt*p@88s7VO7a++u8Y)o!Yk`T`SDfG0Q'
    'BU5f(EizFzJZG4wjyGi6bB2;DH$R5{1KKX-;R}Zvcg_djy|<mG4{*soYVi+u?t}g41>py8&~-n5P&>P6S}X5%-N`HFU(Yg;#b@qpq#eli!fP3SEmkk_bUj%W'
    '3m9T=n@UbzwiPqk8_(q(V)IUQbJukGY89)=P{r<Eis$-NNv3JB;3ZVpYMt^0bcUw&BuAHds!3t;^<p9o+te+7F6Zk-tsx{{XIvH`^<Ee+iwdM6?=j!JC|s2s'
    'Dz;D~`N(^|$s}%E)@8+V!B^=E`o<F8vjh5nedE`-(c2LLcdxIE!H{-Vq>8R8W7_xf+`}70ZrHP(U9nY-Irh-L^L!aCjvtK1$f<SIw1m7+woaQ1g*xB<oRn`r'
    'xncatwI6@xjiA@41#5}G@5<EP_nH8DUO0+kXB>tAc1m;@qV?^016gSvuPOyY*Y0`)Sy(kT*OpWmd>ZVkFvPJf&&-+<U9Z=}9yE{&$-Bv?*!}EcYi{g7wOpN*'
    '?n2w^o=~SX4E^t*_PIGEso3H`X4e}z!J`{KwZz=PJwU1Ef%eCX?gVR+hA1j_Zs3NI*Ylk1{o2thAa_f%H*|eGJiCCrd~!|=gY+)Gqb;zVk8Tu4z%{r(6xrIP'
    '>xHsOjY98U8Uc=S=bn>&2z+l8Rd;~l*onp=;59n7L-ER~?7Fc#KQEZPM<xDf51g|CFh(Wj*kR}$xXMoKZMdlLTpuR$z5795#_dV+wxY0`i%=Na(Zd;$@!cPi'
    'yXw?`3@$=97`koedH`WTSRD<I9ItZdyU^?2yC<Zcni&JO|Jat<lD~1Qou?dw@V%b9vr%2X$v)@M@qNGFj*!E_Mp|=y%(8Q-L&4p>$G)Sl?mwDx{h;gmRoJ+n'
    'qf-+N0wl>%OIt_-2n^8@#KVUm+8DDRNK20UCule=*OVA~@x6<I`tHU*&JF(>d(Ov8=wXF%IFeZdP56bRu)i4^+98^CU%n#m3Qoz6QDXJoO=t!Od1yP@3$a)?'
    '2*Q)206rQ9tyZQrJ|1>u5*qq;8}Qaik>sH=6y6;9$`G^<ytZ*9+_(s@I_xTPTC!D7AzKP$ny8NXBj6{5dZB&Lfc(^J&EeywraCV11E(Ee!0^Y0?|ZOzyiW8q'
    'bh~eCyN~@?QU#%!h@R`V<Epwimq`=VYwROT2Cb3MMR>baa>Bpy@vA!nyS9(SRB5mi@S<wl?Ex?Xd+Td;Fjhhb`}1a-->=dIQ|{-XD+>%fKTK8qz=yy4cG$S{'
    'd{miwSz<T1OO$sAq@Evql1~EvQU097Q1){5A&osAK{Oc3g#K^)l<ixGIib9DgaZr@#wD1bi@bShCi%++St_;mtj#DYVw8>hYv28k-fpXia%%U)>e!iq_gG}q'
    'w>R|*qV=2%_8Cv^64+kgGO|vQ8KM%t+ycoT<ao}9FzBCaf7Y|&@3m+bx%=hi4{cPoliL2c?V#SJ3jOipf8QzLum'
)

def _legacy_tupleize(value):
    if isinstance(value, list):
        return tuple(_legacy_tupleize(item) for item in value)
    if isinstance(value, dict):
        return {key: _legacy_tupleize(item) for key, item in value.items()}
    return value


def _legacy_static_summaries():
    global _LEGACY_STATIC_SUMMARY_CACHE
    if _LEGACY_STATIC_SUMMARY_CACHE is None:
        raw = zlib.decompress(base64.b85decode(_LEGACY_SUMMARY_B85.encode("ascii")))
        if hashlib.sha256(raw).hexdigest() != _LEGACY_SUMMARY_SHA256:
            raise ValueError("legacy_static_summary_digest_mismatch")
        parsed = json.loads(raw.decode("utf-8"))
        if set(parsed) != {"inventory", "behavior"}:
            raise ValueError("legacy_static_summary_schema_mismatch")
        _LEGACY_STATIC_SUMMARY_CACHE = parsed
    return _LEGACY_STATIC_SUMMARY_CACHE


def legacy_static_rom_status() -> dict[str, Any]:
    """Describe optional historical evidence availability without loading its payload."""
    companion = pathlib.Path(__file__).resolve().with_name(_LEGACY_STATIC_ROM_COMPANION)
    status = _LEGACY_STATIC_ROM_STATUS
    return {"schema":"BC-LEGACY-ROM-STATUS-1", "state":status.get("state", "not_loaded"),
            "companion_name":_LEGACY_STATIC_ROM_COMPANION, "companion_path":str(companion),
            "available":companion.is_file(), "loaded":bool(_LEGACY_STATIC_ROM_LOADED),
            "error":status.get("error"), "sha256_expected":_LEGACY_STATIC_ROM_SHA256,
            "compressed_sha256_expected":_LEGACY_STATIC_ROM_COMPRESSED_SHA256,
            "historical_code_executed":False}


def _ensure_legacy_static_rom() -> bool:
    """Load optional historical inspection data; a missing/corrupt ROM is a residual, not a crash."""
    global _LEGACY_STATIC_ROM_LOADED, _LEGACY_STATIC_ROM_STATUS
    global LEGACY_EXECUTOR_ASSIGNMENT_ROWS, LEGACY_CAPTURED_ALIAS_ROWS, LEGACY_DUPLICATE_DEFINITION_ROWS, LEGACY_DYNAMIC_LOOKUP_ROWS
    global LEGACY_COMMAND_BEHAVIOR_ROWS, LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS, LEGACY_BEHAVIOR_SHAPE_TRIAGE
    global LEGACY_REASSIGNED_EXECUTOR_KEY_COUNT, LEGACY_UNIQUE_LITERAL_EXECUTOR_KEY_COUNT
    global LEGACY_UNIQUE_EXECUTOR_KEY_EXPRESSION_COUNT, LEGACY_DYNAMIC_LOOKUP_SITE_COUNT
    global LEGACY_BEHAVIOR_ASSIGNMENT_COUNT, LEGACY_BEHAVIOR_PROFILE_COUNT
    global LEGACY_BEHAVIOR_SYMBOLS_WITH_PROFILES, LEGACY_BEHAVIOR_REASSIGNED_KEYS, LEGACY_BEHAVIOR_AMBIGUOUS_SYMBOLS
    if _LEGACY_STATIC_ROM_LOADED:
        return True
    companion = pathlib.Path(__file__).resolve().with_name(_LEGACY_STATIC_ROM_COMPANION)
    try:
        compressed = companion.read_bytes()
    except OSError as exc:
        _LEGACY_STATIC_ROM_STATUS = {"state":"unavailable", "error":f"legacy_rom_companion_unavailable:{type(exc).__name__}"}
        return False
    if hashlib.sha256(compressed).hexdigest() != _LEGACY_STATIC_ROM_COMPRESSED_SHA256:
        _LEGACY_STATIC_ROM_STATUS = {"state":"corrupt", "error":"legacy_static_rom_compressed_digest_mismatch"}
        return False
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as exc:
        _LEGACY_STATIC_ROM_STATUS = {"state":"corrupt", "error":f"legacy_static_rom_decompression_failed:{type(exc).__name__}"}
        return False
    if hashlib.sha256(raw).hexdigest() != _LEGACY_STATIC_ROM_SHA256:
        _LEGACY_STATIC_ROM_STATUS = {"state":"corrupt", "error":"legacy_static_rom_digest_mismatch"}
        return False
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _LEGACY_STATIC_ROM_STATUS = {"state":"corrupt", "error":f"legacy_static_rom_json_invalid:{type(exc).__name__}"}
        return False
    expected = {
        "LEGACY_EXECUTOR_ASSIGNMENT_ROWS": 805,
        "LEGACY_CAPTURED_ALIAS_ROWS": 185,
        "LEGACY_DUPLICATE_DEFINITION_ROWS": 129,
        "LEGACY_DYNAMIC_LOOKUP_ROWS": 744,
        "LEGACY_COMMAND_BEHAVIOR_ROWS": 805,
        "LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS": 1033,
        "LEGACY_BEHAVIOR_SHAPE_TRIAGE": 805,
    }
    if not isinstance(parsed, dict) or set(parsed) != set(expected):
        _LEGACY_STATIC_ROM_STATUS = {"state":"corrupt", "error":"legacy_static_rom_schema_mismatch"}
        return False
    tables = {key: _legacy_tupleize(value) for key, value in parsed.items()}
    if any(not isinstance(tables[key], (list, tuple)) or len(tables[key]) != count for key, count in expected.items()):
        _LEGACY_STATIC_ROM_STATUS = {"state":"corrupt", "error":"legacy_static_rom_row_count_mismatch"}
        return False

    LEGACY_EXECUTOR_ASSIGNMENT_ROWS = tables["LEGACY_EXECUTOR_ASSIGNMENT_ROWS"]
    LEGACY_CAPTURED_ALIAS_ROWS = tables["LEGACY_CAPTURED_ALIAS_ROWS"]
    LEGACY_DUPLICATE_DEFINITION_ROWS = tables["LEGACY_DUPLICATE_DEFINITION_ROWS"]
    LEGACY_DYNAMIC_LOOKUP_ROWS = tables["LEGACY_DYNAMIC_LOOKUP_ROWS"]
    LEGACY_COMMAND_BEHAVIOR_ROWS = tables["LEGACY_COMMAND_BEHAVIOR_ROWS"]
    LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS = tables["LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS"]
    LEGACY_BEHAVIOR_SHAPE_TRIAGE = tables["LEGACY_BEHAVIOR_SHAPE_TRIAGE"]

    _LEGACY_EXECUTOR_KEYS.clear(); _LEGACY_EXECUTOR_EXPRESSIONS.clear(); _LEGACY_EXECUTOR_SYMBOLS.clear()
    _LEGACY_CAPTURED_ALIASES.clear(); _LEGACY_DUPLICATE_DEFINITIONS.clear(); _LEGACY_DYNAMIC_LOOKUPS.clear()
    _LEGACY_BEHAVIOR_BY_KEY.clear(); _LEGACY_BEHAVIOR_BY_EXPRESSION.clear(); _LEGACY_BEHAVIOR_BY_SYMBOL.clear()
    _LEGACY_FUNCTION_PROFILE_BY_ID.clear(); _LEGACY_FUNCTION_PROFILE_BY_NAME.clear()
    for row in LEGACY_EXECUTOR_ASSIGNMENT_ROWS:
        key, literal, executor, line = row
        if literal: _LEGACY_EXECUTOR_KEYS.setdefault(key, []).append(row)
        else: _LEGACY_EXECUTOR_EXPRESSIONS.setdefault(key, []).append(row)
        if re.fullmatch(r"[A-Za-z_]\w*", executor): _LEGACY_EXECUTOR_SYMBOLS.setdefault(executor, []).append(row)
    for row in LEGACY_CAPTURED_ALIAS_ROWS: _LEGACY_CAPTURED_ALIASES.setdefault(row[0], []).append(row)
    _LEGACY_DUPLICATE_DEFINITIONS.update({name: locations for name, locations in LEGACY_DUPLICATE_DEFINITION_ROWS})
    for row in LEGACY_DYNAMIC_LOOKUP_ROWS: _LEGACY_DYNAMIC_LOOKUPS.setdefault(row[1], []).append(row)
    for row in LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS:
        _LEGACY_FUNCTION_PROFILE_BY_ID[row[0]] = row
        _LEGACY_FUNCTION_PROFILE_BY_NAME.setdefault(row[1], []).append(row)
    for row in LEGACY_COMMAND_BEHAVIOR_ROWS:
        _bid, key, literal, executor = row[:4]
        if literal: _LEGACY_BEHAVIOR_BY_KEY.setdefault(key, []).append(row)
        else: _LEGACY_BEHAVIOR_BY_EXPRESSION.setdefault(key, []).append(row)
        if re.fullmatch(r"[A-Za-z_]\w*", executor): _LEGACY_BEHAVIOR_BY_SYMBOL.setdefault(executor, []).append(row)

    LEGACY_REASSIGNED_EXECUTOR_KEY_COUNT = sum(1 for rows in list(_LEGACY_EXECUTOR_KEYS.values()) + list(_LEGACY_EXECUTOR_EXPRESSIONS.values()) if len(rows) > 1)
    LEGACY_UNIQUE_LITERAL_EXECUTOR_KEY_COUNT = len(_LEGACY_EXECUTOR_KEYS)
    LEGACY_UNIQUE_EXECUTOR_KEY_EXPRESSION_COUNT = len(set((row[0], row[1]) for row in LEGACY_EXECUTOR_ASSIGNMENT_ROWS))
    LEGACY_DYNAMIC_LOOKUP_SITE_COUNT = len(LEGACY_DYNAMIC_LOOKUP_ROWS)
    LEGACY_BEHAVIOR_ASSIGNMENT_COUNT = len(LEGACY_COMMAND_BEHAVIOR_ROWS)
    LEGACY_BEHAVIOR_PROFILE_COUNT = len(LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS)
    LEGACY_BEHAVIOR_SYMBOLS_WITH_PROFILES = len(_LEGACY_FUNCTION_PROFILE_BY_NAME)
    LEGACY_BEHAVIOR_REASSIGNED_KEYS = sum(1 for _key, rows in _LEGACY_BEHAVIOR_BY_KEY.items() if len(rows) > 1)
    LEGACY_BEHAVIOR_AMBIGUOUS_SYMBOLS = sum(1 for _key, rows in _LEGACY_FUNCTION_PROFILE_BY_NAME.items() if len(rows) > 1)
    _LEGACY_STATIC_ROM_LOADED = True
    _LEGACY_STATIC_ROM_STATUS = {"state":"loaded", "error":None, "compressed_sha256":_LEGACY_STATIC_ROM_COMPRESSED_SHA256,
                                 "raw_sha256":_LEGACY_STATIC_ROM_SHA256}
    return True


@dataclass(frozen=True)
class CommandResolutionPacket:
    """Exact-root command-name resolution; historical observations never grant dispatch."""
    schema: str
    root_address_id: str
    requested_reference: str
    status: str
    canonical_kind: str | None
    canonical_name: str | None
    canonical_address: str | None
    historical_source_sha256: str
    evidence_rows: tuple[tuple[str, bool, str, int], ...]
    evidence_total: int
    alias_rows: tuple[tuple[str, str, int], ...]
    alias_total: int
    duplicate_sites: tuple[tuple[int, int], ...]
    duplicate_site_total: int
    dynamic_sites: tuple[tuple[int, str, str], ...]
    dynamic_site_total: int
    unresolved_dependencies: tuple[str, ...]
    packet_id: str

    @property
    def resolved(self) -> bool:
        return self.canonical_kind in {"glyph", "operation"} and self.canonical_name is not None

    def _body(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "root_address_id": self.root_address_id,
            "requested_reference": self.requested_reference, "status": self.status,
            "canonical_kind": self.canonical_kind, "canonical_name": self.canonical_name,
            "canonical_address": self.canonical_address, "historical_source_sha256": self.historical_source_sha256,
            "evidence_rows": [list(row) for row in self.evidence_rows], "evidence_total": self.evidence_total,
            "alias_rows": [list(row) for row in self.alias_rows], "alias_total": self.alias_total,
            "duplicate_sites": [list(row) for row in self.duplicate_sites],
            "duplicate_site_total": self.duplicate_site_total,
            "dynamic_sites": [list(row) for row in self.dynamic_sites],
            "dynamic_site_total": self.dynamic_site_total,
            "unresolved_dependencies": list(self.unresolved_dependencies),
        }

    def as_dict(self) -> dict[str, Any]:
        body = self._body()
        body.update({"pass": True, "resolved": self.resolved, "packet_id": self.packet_id,
                     "legacy_code_executed": False, "historical_source_mutated": False,
                     "automatic_alias_binding": False})
        return body


def _make_command_resolution_packet(address: BCFloorAddress, reference: str, status: str,
                                    canonical_kind: str | None = None, canonical_name: str | None = None,
                                    canonical_address: str | None = None,
                                    evidence_rows: Sequence[tuple[str, bool, str, int]] = (),
                                    evidence_total: int = 0, alias_rows: Sequence[tuple[str, str, int]] = (),
                                    alias_total: int = 0, duplicate_sites: Sequence[tuple[int, int]] = (),
                                    duplicate_site_total: int = 0,
                                    dynamic_sites: Sequence[tuple[int, str, str]] = (),
                                    dynamic_site_total: int = 0,
                                    unresolved_dependencies: Sequence[str] = ()) -> CommandResolutionPacket:
    packet = CommandResolutionPacket(
        "BC-COMMAND-RESOLUTION-1", address.address_id, reference, status, canonical_kind, canonical_name,
        canonical_address, LEGACY_COMMAND_SOURCE_SHA256, tuple(evidence_rows), evidence_total,
        tuple(alias_rows), alias_total, tuple(duplicate_sites), duplicate_site_total,
        tuple(dynamic_sites), dynamic_site_total, tuple(unresolved_dependencies), "")
    packet_id = _sha256_text(_canonical_json(packet._body()))[:32]
    return CommandResolutionPacket(**{**packet.__dict__, "packet_id": packet_id})


def legacy_command_inventory_summary() -> dict[str, Any]:
    """Return the compact historical inventory summary without expanding its detailed ROM."""
    result = copy.deepcopy(_legacy_static_summaries()["inventory"])
    result["reassigned_executor_keys"] = tuple(result["reassigned_executor_keys"])
    return result


def resolve_command_reference(address: BCFloorAddress, reference: str,
                              expected_legacy_source_sha256: str | None = None) -> CommandResolutionPacket:
    """Resolve exact names to current resident IDs or return static historical residuals.

    Historical executor keys/aliases are never fallback dispatch names. This API only
    constructs a source-addressed packet; it does not call the legacy engine or execute a glyph.
    """
    if not isinstance(address, BCFloorAddress):
        raise TypeError("command_resolution_requires_full_floor_address")
    if not isinstance(reference, str) or not reference:
        raise ValueError("command_reference_must_be_nonempty_exact_string")
    if expected_legacy_source_sha256 is not None and expected_legacy_source_sha256 != LEGACY_COMMAND_SOURCE_SHA256:
        raise ValueError("legacy_command_source_hash_mismatch")
    if reference in GLYPH_CATALOG.names():
        spec = GLYPH_CATALOG.resolve(reference)
        return _make_command_resolution_packet(address, reference, "canonical_glyph", "glyph", reference, spec.address)
    if reference in REGISTRY.names():
        operation = REGISTRY.resolve(reference)
        address_id = _sha256_text(_canonical_json({"operation":operation.operation, "effect":operation.effect}))[:24]
        return _make_command_resolution_packet(address, reference, "canonical_operation", "operation", reference, address_id)
    if not _ensure_legacy_static_rom():
        state = _LEGACY_STATIC_ROM_STATUS.get("state", "unavailable")
        reason = "historical_rom_companion_corrupt" if state == "corrupt" else "historical_rom_companion_unavailable"
        return _make_command_resolution_packet(address, reference, "historical_evidence_unavailable",
            unresolved_dependencies=(reason, "current_glyph_catalogue_checked_first", "historical_resolution_not_inferred"))
    if reference in _LEGACY_EXECUTOR_KEYS:
        rows = tuple(_LEGACY_EXECUTOR_KEYS[reference])
        repeated = len(rows) > 1
        deps = ["canonical_target_not_bound_by_replayable_semantic_witness", "historical_source_is_static_evidence_only"]
        if repeated: deps.extend(("historical_executor_key_reassigned", "latest_source_assignment_not_assumed_authoritative"))
        return _make_command_resolution_packet(address, reference,
            "historical_executor_key_reassigned" if repeated else "historical_executor_key_unmapped",
            evidence_rows=rows[:32], evidence_total=len(rows), unresolved_dependencies=deps + (["evidence_rows_truncated"] if len(rows)>32 else []))
    if reference in _LEGACY_EXECUTOR_EXPRESSIONS:
        rows = tuple(_LEGACY_EXECUTOR_EXPRESSIONS[reference])
        return _make_command_resolution_packet(address, reference, "historical_dynamic_executor_key_unresolved",
            evidence_rows=rows[:32], evidence_total=len(rows),
            unresolved_dependencies=("dynamic_key_expression_not_evaluated", "canonical_target_not_bound", "historical_source_is_static_evidence_only"))
    if reference in _LEGACY_CAPTURED_ALIASES:
        rows = tuple(_LEGACY_CAPTURED_ALIASES[reference])
        return _make_command_resolution_packet(address, reference,
            "historical_alias_capture_repeated" if len(rows)>1 else "historical_alias_capture_unmapped",
            alias_rows=rows[:32], alias_total=len(rows),
            unresolved_dependencies=("captured_function_binding_time_not_replayed", "canonical_target_not_bound", "automatic_alias_binding_forbidden") + (("alias_evidence_truncated",) if len(rows)>32 else ()))
    if reference in _LEGACY_DUPLICATE_DEFINITIONS:
        sites = tuple(_LEGACY_DUPLICATE_DEFINITIONS[reference])
        return _make_command_resolution_packet(address, reference, "historical_duplicate_symbol_unresolved",
            duplicate_sites=sites[:32], duplicate_site_total=len(sites),
            unresolved_dependencies=("multiple_source_definitions", "conditional_or_captured_binding_not_inferred", "canonical_target_not_bound"))
    if reference in _LEGACY_EXECUTOR_SYMBOLS:
        rows = tuple(_LEGACY_EXECUTOR_SYMBOLS[reference])
        return _make_command_resolution_packet(address, reference, "historical_executor_symbol_unmapped",
            evidence_rows=rows[:32], evidence_total=len(rows),
            unresolved_dependencies=("historical_executor_semantics_not_ported", "canonical_target_not_bound", "legacy_callable_not_executed"))
    if reference in _LEGACY_DYNAMIC_LOOKUPS:
        rows = tuple(_LEGACY_DYNAMIC_LOOKUPS[reference])
        return _make_command_resolution_packet(address, reference, "historical_dynamic_lookup_callee_unresolved",
            dynamic_sites=rows[:32], dynamic_site_total=len(rows),
            unresolved_dependencies=("dynamic_dispatch_target_not_bound", "legacy_dynamic_lookup_not_executed") + (("dynamic_site_evidence_truncated",) if len(rows)>32 else ()))
    return _make_command_resolution_packet(address, reference, "unknown_reference",
        unresolved_dependencies=("reference_not_present_in_current_or_historical_indexes",))


def reopen_command_reference(address: BCFloorAddress, reference: str, packet: CommandResolutionPacket,
                             expected_legacy_source_sha256: str | None = None) -> dict[str, Any]:
    """Rebuild packet from current ROM and exact root; any name/evidence tamper fails closed."""
    if not isinstance(packet, CommandResolutionPacket):
        return {"schema":"BC-COMMAND-RESOLUTION-REOPEN-1", "pass":False, "reason":"wrong_packet_type"}
    try:
        rebuilt = resolve_command_reference(address, reference, expected_legacy_source_sha256)
        root_matches = packet.root_address_id == address.address_id
        same_request = packet.requested_reference == reference
        passed = root_matches and same_request and rebuilt == packet
        return {"schema":"BC-COMMAND-RESOLUTION-REOPEN-1", "pass":passed,
                "root_matches":root_matches, "same_request":same_request,
                "provided_packet_id":packet.packet_id, "rebuilt_packet_id":rebuilt.packet_id,
                "legacy_code_executed":False, "automatic_alias_binding":False}
    except Exception as exc:
        return {"schema":"BC-COMMAND-RESOLUTION-REOPEN-1", "pass":False,
                "reason":f"{type(exc).__name__}:{exc}", "legacy_code_executed":False}


def _validate_command_resolution_matrix_patch() -> None:
    """Reserved named check used by tests; no dispatch or state write occurs."""
    summary = legacy_command_inventory_summary()
    if summary["historical_source_sha256"] != LEGACY_COMMAND_SOURCE_SHA256:
        raise ValueError("legacy_command_rom_hash_mismatch")
    if summary["executor_assignment_rows"] != 805 or summary["captured_alias_assignment_rows"] != 185 or summary["duplicate_definition_groups"] != 129:
        raise ValueError("legacy_command_rom_count_mismatch")



# ---------------------------------------------------------------------------
# Static historical command behaviour profiles (V9); data-only, no code bodies
# ---------------------------------------------------------------------------
LEGACY_BEHAVIOR_SOURCE_SHA256 = '5abe5d866230448e3f9b8b22090937204f18ce126184f61727ecbfd448565e52'
LEGACY_BEHAVIOR_SOURCE_BYTES = 6176692
LEGACY_COMMAND_BEHAVIOR_ROWS = ()
LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS = ()

# Detailed behaviour maps remain empty until _ensure_legacy_static_rom() is called.
_LEGACY_BEHAVIOR_BY_KEY = {}
_LEGACY_BEHAVIOR_BY_EXPRESSION = {}
_LEGACY_BEHAVIOR_BY_SYMBOL = {}
_LEGACY_FUNCTION_PROFILE_BY_ID = {}
_LEGACY_FUNCTION_PROFILE_BY_NAME = {}
LEGACY_BEHAVIOR_ASSIGNMENT_COUNT = 805
LEGACY_BEHAVIOR_PROFILE_COUNT = 1033
LEGACY_BEHAVIOR_SYMBOLS_WITH_PROFILES = 651
LEGACY_BEHAVIOR_REASSIGNED_KEYS = 69
LEGACY_BEHAVIOR_AMBIGUOUS_SYMBOLS = 129
LEGACY_BEHAVIOR_SHAPE_TRIAGE = ()

def legacy_command_behavior_summary() -> dict[str, Any]:
    """Return cached aggregate profile statistics; detailed historical rows load on demand."""
    return copy.deepcopy(_legacy_static_summaries()["behavior"])

@dataclass(frozen=True)
class LegacyCommandBehaviorPacket:
    schema: str
    root_address_id: str
    requested_reference: str
    status: str
    historical_source_sha256: str
    assignment_rows: tuple[tuple[Any, ...], ...]
    assignment_total: int
    function_profile_rows: tuple[tuple[Any, ...], ...]
    function_profile_total: int
    domain_tags: tuple[str, ...]
    structural_probe_priority: str
    unresolved_dependencies: tuple[str, ...]
    packet_id: str

    def _body(self) -> dict[str, Any]:
        return {"schema":self.schema,"root_address_id":self.root_address_id,"requested_reference":self.requested_reference,
          "status":self.status,"historical_source_sha256":self.historical_source_sha256,
          "assignment_rows":[list(r) for r in self.assignment_rows],"assignment_total":self.assignment_total,
          "function_profile_rows":[list(r) for r in self.function_profile_rows],"function_profile_total":self.function_profile_total,
          "domain_tags":list(self.domain_tags),"structural_probe_priority":self.structural_probe_priority,
          "unresolved_dependencies":list(self.unresolved_dependencies)}

    def as_dict(self) -> dict[str, Any]:
        body=self._body(); body.update({"pass":True,"packet_id":self.packet_id,"legacy_code_executed":False,
          "legacy_source_mutated":False,"semantic_mapping_proven":False,"automatic_alias_binding":False,
          "automatic_glyph_admission":False}); return body

def _make_legacy_command_behavior_packet(address: BCFloorAddress, reference: str, status: str,
        assignment_rows: Sequence[tuple[Any, ...]]=(), function_profile_rows: Sequence[tuple[Any, ...]]=(),
        domain_tags: Sequence[str]=(), structural_probe_priority: str="unclassified",
        unresolved_dependencies: Sequence[str]=()) -> LegacyCommandBehaviorPacket:
    packet=LegacyCommandBehaviorPacket("BC-LEGACY-COMMAND-BEHAVIOR-1",address.address_id,reference,status,
      LEGACY_BEHAVIOR_SOURCE_SHA256,tuple(assignment_rows),len(assignment_rows),tuple(function_profile_rows),
      len(function_profile_rows),tuple(domain_tags),structural_probe_priority,tuple(unresolved_dependencies),"")
    pid=_sha256_text(_canonical_json(packet._body()))[:32]
    return LegacyCommandBehaviorPacket(**{**packet.__dict__,"packet_id":pid})

def inspect_legacy_command_behavior(address: BCFloorAddress, reference: str,
        expected_historical_source_sha256: str | None=None) -> LegacyCommandBehaviorPacket:
    """Return exact AST/source fingerprints for a historical executor without evaluating it."""
    if not isinstance(address,BCFloorAddress): raise TypeError("legacy_behavior_requires_full_floor_address")
    if not isinstance(reference,str) or not reference: raise ValueError("legacy_behavior_reference_must_be_exact_nonempty_string")
    if expected_historical_source_sha256 is not None and expected_historical_source_sha256!=LEGACY_BEHAVIOR_SOURCE_SHA256:
        raise ValueError("legacy_behavior_source_hash_mismatch")
    if not _ensure_legacy_static_rom():
        state = _LEGACY_STATIC_ROM_STATUS.get("state", "unavailable")
        reason = "historical_rom_companion_corrupt" if state == "corrupt" else "historical_rom_companion_unavailable"
        return _make_legacy_command_behavior_packet(address, reference, "historical_evidence_unavailable", (), (),
          ("historical_function_symbol",), "unavailable", (reason, "historical_source_not_executed", "semantic_mapping_not_proven"))
    rows=tuple(_LEGACY_BEHAVIOR_BY_KEY.get(reference,()))
    if not rows: rows=tuple(_LEGACY_BEHAVIOR_BY_EXPRESSION.get(reference,()))
    if not rows: rows=tuple(_LEGACY_BEHAVIOR_BY_SYMBOL.get(reference,()))
    profiles_by_id={row[0]:row for row in LEGACY_FUNCTION_BEHAVIOR_PROFILE_ROWS}
    profiles=[]
    if rows:
        for row in rows:
            for pid in row[8]:
                if pid in profiles_by_id and pid not in {p[0] for p in profiles}: profiles.append(profiles_by_id[pid])
    else:
        profiles=list(_LEGACY_FUNCTION_PROFILE_BY_NAME.get(reference,()))
    profiles=sorted(profiles,key=lambda p:(p[1],p[3],p[0]))
    if not rows and not profiles:
        return _make_legacy_command_behavior_packet(address,reference,"unknown_historical_behavior",(),(),(),"unclassified",
          ("reference_not_present_in_command_behavior_ROM","semantic_mapping_not_proven"))
    total_assignments=len(rows); profile_total=len(profiles)
    domain_tags=tuple(sorted({tag for row in rows for tag in row[5]})) or ("historical_function_symbol",)
    if len(rows)>1: status="historical_behavior_multiple_assignments_preserved"
    elif rows and rows[0][6]!="symbol": status="historical_behavior_inline_expression_profiled"
    elif rows and profile_total==0: status="historical_behavior_executor_definition_missing"
    elif profile_total>1: status="historical_behavior_multiple_definition_profiles"
    elif rows: status="historical_behavior_single_definition_profiled"
    elif profile_total>1: status="historical_symbol_definitions_profiled_but_ambiguous"
    else: status="historical_symbol_definition_profiled"
    triage={bid:(ok,flags,n) for bid,ok,flags,n in LEGACY_BEHAVIOR_SHAPE_TRIAGE}
    if rows and all(triage[row[0]][0] for row in rows): priority="bounded_replay_probe_candidate_not_semantic_proof"
    elif profile_total>1 or len(rows)>1: priority="ambiguity_first_preserve_all"
    elif rows and any((p[-1] for p in profiles)): priority="dynamic_or_effectful_dependency_review"
    else: priority="structural_profile_available_semantics_open"
    deps=["historical_body_profile_is_static_evidence_only","semantic_mapping_not_proven",
          "no_executor_or_alias_is_returned_as_callable"]
    if len(rows)>1: deps.append("multiple_source_assignments_preserved_no_last_write_selection")
    if profile_total>1: deps.append("multiple_definition_sites_preserved_no_scope_or_capture_inference")
    if rows and rows[0][6]!="symbol": deps.append("inline_expression_profiled_without_evaluation")
    if profile_total==0 and rows: deps.append("executor_symbol_body_not_found_in_static_definition_index")
    return _make_legacy_command_behavior_packet(address,reference,status,rows,profiles,domain_tags,priority,deps)

def reopen_legacy_command_behavior(address: BCFloorAddress, reference: str,
        packet: LegacyCommandBehaviorPacket, expected_historical_source_sha256: str | None=None) -> dict[str,Any]:
    try: expected=inspect_legacy_command_behavior(address,reference,expected_historical_source_sha256)
    except Exception as exc: return {"pass":False,"reason":f"reopen_failed:{type(exc).__name__}:{exc}"}
    ok=packet==expected
    return {"pass":ok,"packet_id":packet.packet_id,"expected_packet_id":expected.packet_id,
      "root_matches":packet.root_address_id==address.address_id,"reference_matches":packet.requested_reference==reference,
      "source_hash_matches":packet.historical_source_sha256==LEGACY_BEHAVIOR_SOURCE_SHA256,
      "assignment_rows_recomputed":packet.assignment_rows==expected.assignment_rows,
      "function_profiles_recomputed":packet.function_profile_rows==expected.function_profile_rows,
      "semantic_mapping_proven":False,"legacy_code_executed":False}
# Exactly one live resolver family. Observed old command names do not become aliases.
REGISTRY.register("resolve_command_reference", resolve_command_reference, "pure")
REGISTRY.register("reopen_command_reference", reopen_command_reference, "pure")
REGISTRY.register("legacy_command_inventory_summary", legacy_command_inventory_summary, "pure")
REGISTRY.register("inspect_legacy_command_behavior", inspect_legacy_command_behavior, "pure")
REGISTRY.register("reopen_legacy_command_behavior", reopen_legacy_command_behavior, "pure")
REGISTRY.register("legacy_command_behavior_summary", legacy_command_behavior_summary, "pure")
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMAND.REFERENCE.RESOLVE", "resolve_command_reference",
    ("address", "reference"), ("expected_legacy_source_sha256",),
    {"address":"full_address", "reference":"string", "expected_legacy_source_sha256":"sha256_or_none"}, "pure",
    "exact root-bound lookup into current canonical IDs or source-hash-bound historical residual evidence; never legacy fallback dispatch"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMAND.REFERENCE.REOPEN", "reopen_command_reference",
    ("address", "reference", "packet"), ("expected_legacy_source_sha256",),
    {"address":"full_address", "reference":"string", "packet":"command_resolution_packet", "expected_legacy_source_sha256":"sha256_or_none"}, "pure",
    "recompute packet against exact root, request, historical evidence ROM and canonical resident catalogue; reject tampering"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMAND.HISTORY.SUMMARY", "legacy_command_inventory_summary", (), (),
    {}, "pure", "static audit of executor keys, captured aliases, duplicate definitions and dynamic lookup sites; source is never executed"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMAND.BEHAVIOR.INSPECT", "inspect_legacy_command_behavior",
    ("address", "reference"), ("expected_historical_source_sha256",),
    {"address":"full_address", "reference":"string", "expected_historical_source_sha256":"sha256_or_none"}, "pure",
    "return root-bound source/AST fingerprints and structural probe triage for historical executor keys; no body execution or semantic binding"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMAND.BEHAVIOR.REOPEN", "reopen_legacy_command_behavior",
    ("address", "reference", "packet"), ("expected_historical_source_sha256",),
    {"address":"full_address", "reference":"string", "packet":"legacy_command_behavior_packet", "expected_historical_source_sha256":"sha256_or_none"}, "pure",
    "recompute command behaviour profiles against exact root, source hashes and static ROM; reject changed sites or packet fields"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMAND.BEHAVIOR.SUMMARY", "legacy_command_behavior_summary", (), (),
    {}, "pure", "source-hash-bound command structure/domain summary and non-authoritative replay probe candidates; no semantic equivalence claimed"))

# ---------------------------------------------------------------------------
# Typed host packet contract migration (V11): schema-only communication boundary
# Historical source was inspected at a fixed hash/span; no legacy code is used.
# ---------------------------------------------------------------------------
HOST_PACKET_SCHEMA_VERSION = "BC-HOST-ATOMIC-V147.1"
HOST_PACKET_SCHEMA_SOURCE_SHA256 = "5abe5d866230448e3f9b8b22090937204f18ce126184f61727ecbfd448565e52"
HOST_PACKET_SCHEMA_SOURCE_LINE_SPAN = (20380, 20408)
HOST_PACKET_SCHEMA_SOURCE_SPAN_SHA256 = "133912bfa8c6555df815b1de190fa7dcbc5394df79ff129b33befa252e255398"
# Immutable tuples are the authoritative ROM; callers always receive derived copies.
_HOST_PACKET_SCHEMA_ROWS = (
    ("BCTransitionWitness", "BC_TRANSITION_WITNESS_V1",
     ("packet_type", "packet_version", "engine_digest", "authority", "source", "target", "operator",
      "allowed", "delta_energy", "matrix_element", "reason", "witness_kind"),
     ("delta_energy",), "BC witness; packet is a host-boundary projection"),
    ("BCCoulombChannel", "BC_COULOMB_CHANNEL_V1",
     ("packet_type", "packet_version", "engine_digest", "authority", "bra", "ket", "kind",
      "coefficient", "derivation", "channel_kind"),
     ("coefficient",), "BC causal interaction channel; packet is a host-boundary projection"),
    ("BCTwoAtomInteraction", "BC_TWO_ATOM_INTERACTION_V1",
     ("packet_type", "packet_version", "engine_digest", "authority", "atom_a", "atom_b",
      "separation_address", "channels", "interaction_identity", "coefficient_policy"),
     (), "BC structural opening only; no fitted interaction potential"),
)
_HOST_PACKET_SCHEMA_BY_KIND = {row[0]: row for row in _HOST_PACKET_SCHEMA_ROWS}
_HOST_PACKET_KIND_BY_TYPE = {row[1]: row[0] for row in _HOST_PACKET_SCHEMA_ROWS}

def _host_packet_schema_view(row):
    return {"kind": row[0], "packet_type": row[1], "version": HOST_PACKET_SCHEMA_VERSION,
            "required_fields": row[2], "exact_fields": row[3], "authority": row[4]}

def host_packet_contract_summary():
    return {"schema": "BC-HOST-PACKET-CONTRACT-1", "version": HOST_PACKET_SCHEMA_VERSION,
            "kind_count": len(_HOST_PACKET_SCHEMA_ROWS),
            "kinds": tuple(row[0] for row in _HOST_PACKET_SCHEMA_ROWS),
            "historical_source_sha256": HOST_PACKET_SCHEMA_SOURCE_SHA256,
            "historical_source_line_span": HOST_PACKET_SCHEMA_SOURCE_LINE_SPAN,
            "historical_source_span_sha256": HOST_PACKET_SCHEMA_SOURCE_SPAN_SHA256,
            "source_inspected_statically_only": True, "legacy_code_executed": False,
            "legacy_atomic_types_imported": False, "semantic_parity_claimed": False,
            "exact_integer_encoding_rejects_bool": True, "automatic_glyph_admission": False}

def inspect_host_packet_schema(address: BCFloorAddress, kind: str,
                               expected_historical_source_sha256: str | None = None):
    if not isinstance(address, BCFloorAddress):
        raise TypeError("host_packet_schema_requires_full_floor_address")
    if expected_historical_source_sha256 is not None and expected_historical_source_sha256 != HOST_PACKET_SCHEMA_SOURCE_SHA256:
        raise ValueError("host_packet_schema_source_hash_mismatch")
    row = _HOST_PACKET_SCHEMA_BY_KIND.get(kind) if isinstance(kind, str) else None
    if row is None:
        return {"pass": False, "reason": "unknown_packet_kind", "root_address_id": address.address_id,
                "requested_kind": kind, "historical_source_sha256": HOST_PACKET_SCHEMA_SOURCE_SHA256,
                "semantic_parity_claimed": False}
    body = {"pass": True, "schema": "BC-HOST-PACKET-SCHEMA-V1", "root_address_id": address.address_id,
            "requested_kind": kind, "packet_schema": _host_packet_schema_view(row),
            "historical_source_sha256": HOST_PACKET_SCHEMA_SOURCE_SHA256,
            "historical_source_line_span": HOST_PACKET_SCHEMA_SOURCE_LINE_SPAN,
            "historical_source_span_sha256": HOST_PACKET_SCHEMA_SOURCE_SPAN_SHA256,
            "legacy_code_executed": False, "semantic_parity_claimed": False}
    body["schema_fingerprint"] = _sha256_text(_canonical_json(body))
    return body

def _validate_host_packet_payload(packet, kind=None):
    if not isinstance(packet, dict):
        return {"pass": False, "reason": "packet_must_be_mapping"}
    wanted = kind if kind is not None else _HOST_PACKET_KIND_BY_TYPE.get(str(packet.get("packet_type", "")))
    row = _HOST_PACKET_SCHEMA_BY_KIND.get(wanted) if isinstance(wanted, str) else None
    if row is None:
        return {"pass": False, "reason": "unknown_packet_kind", "kind": wanted}
    if packet.get("packet_type") != row[1]:
        return {"pass": False, "reason": "packet_type_mismatch", "expected": row[1],
                "actual": packet.get("packet_type"), "kind": wanted}
    if str(packet.get("packet_version")) != HOST_PACKET_SCHEMA_VERSION:
        return {"pass": False, "reason": "unsupported_packet_version", "expected": HOST_PACKET_SCHEMA_VERSION,
                "actual": packet.get("packet_version"), "kind": wanted}
    missing = [field for field in row[2] if field not in packet]
    if missing:
        return {"pass": False, "reason": "missing_required_fields", "missing": missing, "kind": wanted}
    for field_name in row[3]:
        value = packet.get(field_name)
        if not (isinstance(value, dict) and value.get("encoding") == "BCRational" and
                type(value.get("numerator")) is int and type(value.get("denominator")) is int and
                value.get("denominator") != 0):
            return {"pass": False, "reason": "exact_field_encoding_invalid", "field": field_name,
                    "kind": wanted}
    return {"pass": True, "kind": wanted, "packet_type": row[1],
            "packet_version": HOST_PACKET_SCHEMA_VERSION, "required_fields": row[2],
            "exact_fields": row[3]}

def _host_packet_json_digest(packet):
    try:
        payload = _canonical_json(packet)
    except (TypeError, ValueError):
        payload = _canonical_json({"unserializable_type": type(packet).__module__ + "." + type(packet).__qualname__})
    return _sha256_text(payload)

def validate_host_packet(address: BCFloorAddress, packet, kind: str | None = None):
    if not isinstance(address, BCFloorAddress):
        raise TypeError("host_packet_validation_requires_full_floor_address")
    validation = _validate_host_packet_payload(packet, kind)
    body = {"schema": "BC-HOST-PACKET-VALIDATION-RECEIPT-1", "root_address_id": address.address_id,
            "requested_kind": kind, "packet_sha256": _host_packet_json_digest(packet),
            "validation": validation, "packet_validation_pass": bool(validation.get("pass")),
            "historical_source_sha256": HOST_PACKET_SCHEMA_SOURCE_SHA256,
            "historical_source_line_span": HOST_PACKET_SCHEMA_SOURCE_LINE_SPAN,
            "legacy_code_executed": False, "semantic_parity_claimed": False}
    body["receipt_id"] = _sha256_text(_canonical_json(body))
    body["pass"] = bool(validation.get("pass"))
    return body

def reopen_host_packet_validation(address: BCFloorAddress, packet, receipt, kind: str | None = None):
    try:
        expected = validate_host_packet(address, packet, kind)
    except Exception as exc:
        return {"pass": False, "reason": "reopen_failed:" + type(exc).__name__ + ":" + str(exc)}
    same = isinstance(receipt, dict) and receipt == expected
    return {"pass": same, "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None,
            "expected_receipt_id": expected["receipt_id"],
            "root_matches": isinstance(receipt, dict) and receipt.get("root_address_id") == address.address_id,
            "packet_hash_recomputed": isinstance(receipt, dict) and receipt.get("packet_sha256") == expected["packet_sha256"],
            "validation_recomputed": isinstance(receipt, dict) and receipt.get("validation") == expected["validation"],
            "semantic_parity_claimed": False, "legacy_code_executed": False}

REGISTRY.register("host_packet_contract_summary", host_packet_contract_summary, "pure")
REGISTRY.register("inspect_host_packet_schema", inspect_host_packet_schema, "pure")
REGISTRY.register("validate_host_packet", validate_host_packet, "pure")
REGISTRY.register("reopen_host_packet_validation", reopen_host_packet_validation, "pure")
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.SUMMARY", "host_packet_contract_summary", (), (),
    {}, "pure", "source-bound summary of three host packet schemas; no historical atomic implementation is loaded"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.SCHEMA", "inspect_host_packet_schema",
    ("address", "kind"), ("expected_historical_source_sha256",),
    {"address":"full_address", "kind":"string", "expected_historical_source_sha256":"sha256_or_none"},
    "pure", "derive an immutable schema view bound to the current full floor address and fixed historical source span"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.VALIDATE", "validate_host_packet",
    ("address", "packet"), ("kind",), {"address":"full_address", "packet":"host_packet_mapping", "kind":"string"},
    "pure", "validate packet envelope and exact rational fields; return a root-bound, replayable receipt"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.REOPEN", "reopen_host_packet_validation",
    ("address", "packet", "receipt"), ("kind",),
    {"address":"full_address", "packet":"host_packet_mapping", "receipt":"packet_validation_receipt", "kind":"string"},
    "pure", "recompute packet hash and schema validation against the full root; reject root, payload or receipt edits"))


# ---------------------------------------------------------------------------
# Bounded canonical host-packet wire codec (V12): exact, typed, root-bound.
# It serializes already-defined packet envelopes, not historical atomic objects.
# ---------------------------------------------------------------------------
HOST_PACKET_CODEC_SCHEMA = "BC-HOST-PACKET-CANONICAL-CODEC-1"
HOST_PACKET_CODEC_MAX_DEPTH = 32
HOST_PACKET_CODEC_MAX_NODES = 16384
HOST_PACKET_CODEC_MAX_BYTES = 1048576
HOST_PACKET_CODEC_MAX_STRING_BYTES = 262144
HOST_PACKET_CODEC_MAX_INTEGER_BITS = 4096

def host_packet_codec_summary():
    return {"schema": HOST_PACKET_CODEC_SCHEMA,
            "max_depth": HOST_PACKET_CODEC_MAX_DEPTH,
            "max_nodes": HOST_PACKET_CODEC_MAX_NODES,
            "max_bytes": HOST_PACKET_CODEC_MAX_BYTES,
            "max_string_bytes": HOST_PACKET_CODEC_MAX_STRING_BYTES,
            "max_integer_bits": HOST_PACKET_CODEC_MAX_INTEGER_BITS,
            "tuple_policy": "canonicalize_to_array",
            "exact_rational_policy": "ExactRational_to_BCRational_envelope",
            "float_policy": "reject_everywhere",
            "mapping_key_policy": "string_keys_only",
            "canonical_json": "UTF-8; sorted keys; compact separators; non-ASCII preserved",
            "source_schema_sha256": HOST_PACKET_SCHEMA_SOURCE_SHA256,
            "legacy_code_executed": False, "physical_transport_performed": False,
            "semantic_parity_claimed": False}

def _host_packet_codec_normalize(value, *, depth=0, budget=None, active=None):
    if budget is None: budget = {"nodes": 0}
    if active is None: active = set()
    if depth > HOST_PACKET_CODEC_MAX_DEPTH:
        raise ValueError("packet_max_depth_exceeded")
    budget["nodes"] += 1
    if budget["nodes"] > HOST_PACKET_CODEC_MAX_NODES:
        raise ValueError("packet_max_nodes_exceeded")
    if isinstance(value, ExactRational):
        return {"encoding": "BCRational", "numerator": value.numerator, "denominator": value.denominator}
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if value.bit_length() > HOST_PACKET_CODEC_MAX_INTEGER_BITS:
            raise ValueError("packet_integer_bit_limit_exceeded")
        return value
    if type(value) is float:
        raise ValueError("floating_point_not_allowed_in_canonical_packet")
    if type(value) is str:
        try: byte_len = len(value.encode("utf-8"))
        except UnicodeEncodeError as exc: raise ValueError("packet_string_invalid_unicode") from exc
        if byte_len > HOST_PACKET_CODEC_MAX_STRING_BYTES:
            raise ValueError("packet_string_byte_limit_exceeded")
        return value
    if type(value) in (list, tuple, dict):
        ident = id(value)
        if ident in active: raise ValueError("packet_cycle_detected")
        active.add(ident)
        try:
            if type(value) in (list, tuple):
                return [_host_packet_codec_normalize(v, depth=depth+1, budget=budget, active=active) for v in value]
            out = {}
            for key, item in value.items():
                if type(key) is not str: raise ValueError("packet_mapping_keys_must_be_strings")
                normalized_key = _host_packet_codec_normalize(key, depth=depth+1, budget=budget, active=active)
                out[normalized_key] = _host_packet_codec_normalize(item, depth=depth+1, budget=budget, active=active)
            return out
        finally:
            active.remove(ident)
    raise ValueError("unsupported_packet_value_type:" + type(value).__module__ + "." + type(value).__qualname__)

def serialize_host_packet(address: BCFloorAddress, packet, kind: str | None = None):
    """Return a canonical wire projection only when the finite packet envelope validates."""
    if not isinstance(address, BCFloorAddress):
        raise TypeError("host_packet_serialization_requires_full_floor_address")
    if type(packet) is not dict:
        return {"pass": False, "reason": "packet_must_be_builtin_mapping", "root_address_id": address.address_id,
                "legacy_code_executed": False, "physical_transport_performed": False}
    try:
        normalized = _host_packet_codec_normalize(packet)
        canonical = _canonical_json(normalized)
        canonical_bytes = canonical.encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as exc:
        return {"pass": False, "reason": str(exc), "root_address_id": address.address_id,
                "legacy_code_executed": False, "physical_transport_performed": False}
    if len(canonical_bytes) > HOST_PACKET_CODEC_MAX_BYTES:
        return {"pass": False, "reason": "packet_byte_limit_exceeded", "root_address_id": address.address_id,
                "canonical_bytes": len(canonical_bytes), "legacy_code_executed": False,
                "physical_transport_performed": False}
    validation = validate_host_packet(address, normalized, kind)
    if not validation.get("pass"):
        return {"pass": False, "reason": "packet_contract_validation_failed", "root_address_id": address.address_id,
                "validation": validation, "legacy_code_executed": False, "physical_transport_performed": False}
    schema = inspect_host_packet_schema(address, validation["validation"]["kind"])
    body = {"schema": HOST_PACKET_CODEC_SCHEMA, "root_address_id": address.address_id,
            "kind": validation["validation"]["kind"], "packet_type": normalized.get("packet_type"),
            "packet_sha256": _sha256_text(canonical), "canonical_payload_json": canonical,
            "canonical_bytes": len(canonical_bytes), "schema_fingerprint": schema["schema_fingerprint"],
            "historical_source_sha256": HOST_PACKET_SCHEMA_SOURCE_SHA256,
            "historical_source_span_sha256": HOST_PACKET_SCHEMA_SOURCE_SPAN_SHA256,
            "validation_receipt_id": validation["receipt_id"], "validation": validation,
            "normalized_packet": normalized,
            "codec_limits": {"max_depth": HOST_PACKET_CODEC_MAX_DEPTH, "max_nodes": HOST_PACKET_CODEC_MAX_NODES,
                "max_bytes": HOST_PACKET_CODEC_MAX_BYTES, "max_string_bytes": HOST_PACKET_CODEC_MAX_STRING_BYTES,
                "max_integer_bits": HOST_PACKET_CODEC_MAX_INTEGER_BITS},
            "legacy_code_executed": False, "physical_transport_performed": False,
            "semantic_parity_claimed": False}
    body["receipt_id"] = _sha256_text(_canonical_json(body))
    body["pass"] = True
    return body

def reopen_host_packet_serialization(address: BCFloorAddress, packet, receipt, kind: str | None = None):
    if not isinstance(address, BCFloorAddress):
        raise TypeError("host_packet_serialization_reopen_requires_full_floor_address")
    expected = serialize_host_packet(address, packet, kind)
    same = isinstance(receipt, dict) and expected.get("pass") is True and receipt == expected
    return {"pass": same, "root_matches": isinstance(receipt, dict) and receipt.get("root_address_id") == address.address_id,
            "packet_hash_recomputed": isinstance(receipt, dict) and receipt.get("packet_sha256") == expected.get("packet_sha256"),
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None,
            "expected_receipt_id": expected.get("receipt_id"),
            "failure_reason": expected.get("reason") if expected.get("pass") is not True else None,
            "legacy_code_executed": False, "physical_transport_performed": False,
            "semantic_parity_claimed": False}

REGISTRY.register("host_packet_codec_summary", host_packet_codec_summary, "pure")
REGISTRY.register("serialize_host_packet", serialize_host_packet, "pure")
REGISTRY.register("reopen_host_packet_serialization", reopen_host_packet_serialization, "pure")
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.CODEC", "host_packet_codec_summary", (), (), {}, "pure",
    "bounded canonical host-packet wire contract; exact values only; no transport or legacy execution"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.SERIALIZE", "serialize_host_packet", ("address", "packet"), ("kind",),
    {"address":"full_address", "packet":"host_packet_mapping", "kind":"string"}, "pure",
    "normalize and validate a packet to canonical UTF-8 JSON with bounded exact values and a root-bound receipt"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.SERIALIZE.REOPEN", "reopen_host_packet_serialization",
    ("address", "packet", "receipt"), ("kind",),
    {"address":"full_address", "packet":"host_packet_mapping", "receipt":"host_packet_serialization_receipt", "kind":"string"}, "pure",
    "recompute canonical packet wire projection and reject root, payload, receipt or source changes"))


# ---------------------------------------------------------------------------
# Ordered multi-packet communication batch (V13): shared full root and cone.
# It is a pure batching envelope; no transport or historical atomic code runs.
# ---------------------------------------------------------------------------
HOST_PACKET_BATCH_SCHEMA = "BC-HOST-PACKET-BATCH-1"
HOST_PACKET_BATCH_MAX_MEMBERS = 128
HOST_PACKET_BATCH_MAX_BYTES = 4194304

def host_packet_batch_summary():
    return {"schema": HOST_PACKET_BATCH_SCHEMA, "max_members": HOST_PACKET_BATCH_MAX_MEMBERS,
            "max_canonical_member_bytes": HOST_PACKET_BATCH_MAX_BYTES,
            "member_order": "caller_order_is_authoritative",
            "member_identity": "explicit_packet_id_required_unique_within_batch",
            "root_and_cone": "exact_full_root_and_reopened_depth_wave_cone_required",
            "invalid_member_policy": "batch_fails_closed_and_returns_indexed_residuals; no member is silently dropped",
            "legacy_code_executed": False, "physical_transport_performed": False,
            "automatic_glyph_admission": False}

def _packet_batch_input_fingerprint(entry):
    try:
        normalized = _host_packet_codec_normalize(entry)
        return _sha256_text(_canonical_json(normalized)), None
    except Exception as exc:
        # The source value is retained in the residual itself; unsupported values never enter a batch.
        return None, type(exc).__name__ + ":" + str(exc)

def serialize_host_packet_batch(address: BCFloorAddress, cone: DepthWaveCone, packets):
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("packet_batch_requires_full_address_and_depth_wave_cone")
    cone_witness = _require_depth_wave_cone_reopened(address, cone)
    if not isinstance(packets, (list, tuple)):
        return {"pass": False, "schema": HOST_PACKET_BATCH_SCHEMA, "reason": "packet_batch_must_be_sequence",
                "root_address_id": address.address_id, "source_cone_address": cone.cone_address,
                "residuals": [{"index": None, "reason": "packet_batch_must_be_sequence", "source_retained": True}],
                "legacy_code_executed": False, "physical_transport_performed": False}
    if not packets:
        return {"pass": False, "schema": HOST_PACKET_BATCH_SCHEMA, "reason": "packet_batch_empty",
                "root_address_id": address.address_id, "source_cone_address": cone.cone_address,
                "residuals": [], "legacy_code_executed": False, "physical_transport_performed": False}
    if len(packets) > HOST_PACKET_BATCH_MAX_MEMBERS:
        residuals=[]
        for index, entry in enumerate(packets):
            pid=entry.get("packet_id") if type(entry) is dict else None
            residuals.append({"index":index,"packet_id":pid,"reason":"packet_batch_member_limit_exceeded",
                              "input_fingerprint":_packet_batch_input_fingerprint(entry)[0],"source_retained":True})
        return {"pass":False,"schema":HOST_PACKET_BATCH_SCHEMA,"reason":"packet_batch_member_limit_exceeded",
                "root_address_id":address.address_id,"source_cone_address":cone.cone_address,
                "member_count":len(packets),"residuals":residuals,"complete_batch_created":False,
                "cone_witness_address":cone_witness.witness_address,"legacy_code_executed":False,
                "physical_transport_performed":False}
    rows=[]; residuals=[]; seen=set(); total_bytes=0
    for index, entry in enumerate(packets):
        if type(entry) is not dict:
            residuals.append({"index":index,"packet_id":None,"reason":"batch_member_must_be_mapping",
                              "input_fingerprint":None,"source_type":type(entry).__module__+"."+type(entry).__qualname__,
                              "source_retained":True})
            continue
        pid=entry.get("packet_id")
        allowed_keys={"packet_id","packet","kind"}
        fingerprint, fingerprint_error=_packet_batch_input_fingerprint(entry)
        if set(entry)-allowed_keys or "packet" not in entry or type(pid) is not str or not pid or len(pid.encode("utf-8"))>256:
            residuals.append({"index":index,"packet_id":pid if type(pid) is str else None,
                "reason":"batch_member_shape_invalid","input_fingerprint":fingerprint,
                "fingerprint_error":fingerprint_error,"source_retained":True})
            continue
        if pid in seen:
            residuals.append({"index":index,"packet_id":pid,"reason":"duplicate_packet_id",
                              "input_fingerprint":fingerprint,"source_retained":True})
            continue
        seen.add(pid)
        kind=entry.get("kind")
        if kind is not None and type(kind) is not str:
            residuals.append({"index":index,"packet_id":pid,"reason":"packet_kind_must_be_string",
                              "input_fingerprint":fingerprint,"source_retained":True})
            continue
        serialized=serialize_host_packet(address,entry["packet"],kind)
        if not serialized.get("pass"):
            residuals.append({"index":index,"packet_id":pid,"reason":"packet_member_serialization_failed",
                "failure_reason":serialized.get("reason"),
                "validation_reason":serialized.get("validation",{}).get("validation",{}).get("reason"),
                "input_fingerprint":fingerprint,"fingerprint_error":fingerprint_error,
                "source_retained":True})
            continue
        total_bytes += serialized["canonical_bytes"]
        rows.append({"index":index,"packet_id":pid,"kind":serialized["kind"],
            "packet_sha256":serialized["packet_sha256"],"canonical_bytes":serialized["canonical_bytes"],
            "canonical_payload_json":serialized["canonical_payload_json"],"serialization_receipt_id":serialized["receipt_id"]})
    if residuals:
        return {"pass":False,"schema":HOST_PACKET_BATCH_SCHEMA,"reason":"packet_batch_contains_residuals",
            "root_address_id":address.address_id,"source_cone_address":cone.cone_address,"member_count":len(packets),
            "valid_member_count":len(rows),"valid_member_diagnostics":rows,"residuals":residuals,
            "complete_batch_created":False,"cone_witness_address":cone_witness.witness_address,
            "legacy_code_executed":False,"physical_transport_performed":False}
    if total_bytes > HOST_PACKET_BATCH_MAX_BYTES:
        return {"pass":False,"schema":HOST_PACKET_BATCH_SCHEMA,"reason":"packet_batch_byte_limit_exceeded",
            "root_address_id":address.address_id,"source_cone_address":cone.cone_address,"member_count":len(packets),
            "total_member_bytes":total_bytes,
            "residuals":[{"index":r["index"],"packet_id":r["packet_id"],"reason":"batch_total_bytes_exceeded",
                           "packet_sha256":r["packet_sha256"],"source_retained":True} for r in rows],
            "complete_batch_created":False,"cone_witness_address":cone_witness.witness_address,
            "legacy_code_executed":False,"physical_transport_performed":False}
    body={"schema":HOST_PACKET_BATCH_SCHEMA,"root_address_id":address.address_id,
        "source_cone_address":cone.cone_address,"cone_witness_address":cone_witness.witness_address,
        "member_count":len(rows),"total_member_bytes":total_bytes,
        "member_order":[row["packet_id"] for row in rows],"members":rows,
        "historical_packet_schema_source_sha256":HOST_PACKET_SCHEMA_SOURCE_SHA256,
        "host_packet_codec_schema":HOST_PACKET_CODEC_SCHEMA,
        "legacy_code_executed":False,"physical_transport_performed":False,
        "automatic_glyph_admission":False,"persistent_save":False}
    body["batch_id"]=_sha256_text(_canonical_json(body))[:32]
    body["receipt_id"]=_sha256_text(_canonical_json(body))
    body["pass"]=True
    return body

def reopen_host_packet_batch(address: BCFloorAddress, cone: DepthWaveCone, packets, receipt):
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("packet_batch_reopen_requires_full_address_and_depth_wave_cone")
    try: expected=serialize_host_packet_batch(address,cone,packets)
    except Exception as exc:
        return {"pass":False,"reason":"packet_batch_reopen_failed:"+type(exc).__name__+":"+str(exc),
                "root_matches":False,"cone_matches":False,"legacy_code_executed":False}
    same=isinstance(receipt,dict) and expected.get("pass") is True and receipt==expected
    return {"pass":same,"root_matches":isinstance(receipt,dict) and receipt.get("root_address_id")==address.address_id,
            "cone_matches":isinstance(receipt,dict) and receipt.get("source_cone_address")==cone.cone_address,
            "expected_batch_id":expected.get("batch_id"),
            "batch_id":receipt.get("batch_id") if isinstance(receipt,dict) else None,
            "failure_reason":expected.get("reason") if expected.get("pass") is not True else None,
            "legacy_code_executed":False,"physical_transport_performed":False}

REGISTRY.register("host_packet_batch_summary", host_packet_batch_summary, "pure")
REGISTRY.register("serialize_host_packet_batch", serialize_host_packet_batch, "pure")
REGISTRY.register("reopen_host_packet_batch", reopen_host_packet_batch, "pure")
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.BATCH", "host_packet_batch_summary", (), (), {}, "pure",
    "bounded ordered packet batch contract; shared full root/cone; no transport or legacy execution"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.BATCH.SERIALIZE", "serialize_host_packet_batch",
    ("address","cone","packets"), (), {"address":"full_address","cone":"depth_wave_cone","packets":"packet_batch_entries"}, "pure",
    "validate and serialize an ordered bounded set of packet envelopes at one source-bound cone; invalid members stay indexed residuals"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COMMUNICATION.PACKET.BATCH.REOPEN", "reopen_host_packet_batch",
    ("address","cone","packets","receipt"), (), {"address":"full_address","cone":"depth_wave_cone",
    "packets":"packet_batch_entries","receipt":"host_packet_batch_receipt"}, "pure",
    "recompute member serialization, order, shared cone binding and batch receipt; reject tampering or wrong roots"))



# ---------------------------------------------------------------------------
# Warm glyph-composition substrate (non-persistent, content-addressed)
# ---------------------------------------------------------------------------
# Composition is kept separate from the frozen leaf GlyphSpec contract.
# Short track keys and human labels are selectors/presentation only; identity
# comes from child addresses, child implementation fingerprints, bindings,
# declared port types, checks, and the output contract. A composed plan is a
# proposal until explicitly admitted with a fresh replay receipt and authority.

import dataclasses as _bc_dataclasses
import inspect as _bc_inspect
import typing as _bc_typing
import re as _bc_re

_COMPOUND_KEY_RE = _bc_re.compile(r"[a-z][a-z0-9_.-]{0,11}\Z")
_COMPOUND_STEP_RE = _bc_re.compile(r"[a-z][a-z0-9_]{0,7}\Z")
_COMPOUND_KIND_RE = _bc_re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
_COMPOUND_CLASS_KIND = {
    "BCFloorAddress":"full_address", "BCAddress":"generic_address", "FloorPage":"floor_page",
    "Lattice216":"lattice216", "PrimeHarmonicAddress":"harmonic_head_address",
    "RotationSurface":"rotation_surface", "StructuralizerZeroPlaneFrame":"structuralizer_zero_plane_frame",
    "ThreePointDifferenceSolution":"three_point_difference_solution", "ThreePointHallwayCopy":"three_point_hallway_copy",
    "SixPlanePerspectivePacket":"six_plane_packet", "SixPlaneReopenWitness":"six_plane_reopen_witness",
    "CommandResolutionPacket":"command_resolution_packet", "LegacyCommandBehaviorPacket":"legacy_command_behavior_packet",
    "AddressOperation":"address_operation", "ExactRational":"exact_rational",
    "RecursiveChildAddress":"recursive_child_address", "DepthWaveCone":"depth_wave_cone",
    "FullAddressWitness":"full_address_witness", "DepthWaveStructuralizerLink":"depth_wave_structuralizer_link",
    "PrimeRPMAddress":"prime_rpm_address", "PrimeRPMTransition":"prime_rpm_transition",
    "PreConeRequest":"precone_request", "PreConeStateProfile":"precone_state_profile",
    "HarmonicSpiralGrowthPlan":"harmonic_growth_plan", "CrownPreConeBudget":"crown_precone_budget",
    "CrownMultiQueryPreConePlan":"crown_multi_query_plan", "Harmonic64RoutePlan":"harmonic64_route_plan",
    "PlacementCrossoverPlan":"placement_crossover_plan", "str":"string", "bool":"boolean", "int":"integer",
}


def _compound_return_class(target: Any) -> type | None:
    if isinstance(target, CompoundGlyphSpec):
        return None
    fn = getattr(REGISTRY.resolve(target.executor_name).executor, "__func__", REGISTRY.resolve(target.executor_name).executor)
    try:
        annotation = _bc_typing.get_type_hints(fn).get("return")
    except (NameError, TypeError, ValueError):
        annotation = getattr(getattr(fn, "__func__", fn), "__annotations__", {}).get("return")
    return annotation if isinstance(annotation, type) else None


def _compound_output_kind(target: Any) -> str | None:
    if isinstance(target, CompoundGlyphSpec):
        return target.output_kind
    return None if (cls := _compound_return_class(target)) is None else _COMPOUND_CLASS_KIND.get(cls.__name__)


def _compound_normalize(value: Any) -> Any:
    """Canonical value view; floats and opaque live objects are not certifiable."""
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, float):
        raise TypeError("compound_exact_witness_rejects_float")
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"__type__": type(value).__name__, "hex": bytes(value).hex()}
    if isinstance(value, Mapping):
        rows = [(_compound_normalize(k), _compound_normalize(v)) for k, v in value.items()]
        rows.sort(key=lambda row: _canonical_json(row[0]))
        return {"__mapping__": rows}
    if isinstance(value, (tuple, list)):
        return [_compound_normalize(v) for v in value]
    if isinstance(value, (set, frozenset)):
        rows = [_compound_normalize(v) for v in value]
        return sorted(rows, key=_canonical_json)
    address_id = getattr(value, "address_id", None)
    if isinstance(address_id, str):
        return {"__type__": type(value).__qualname__, "address_id": address_id}
    if _bc_dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {"__type__": type(value).__qualname__, **{
            field.name: _compound_normalize(getattr(value, field.name))
            for field in _bc_dataclasses.fields(value)
        }}
    raise TypeError(f"compound_value_not_canonically_addressable:{type(value).__qualname__}")


def _compound_hash(value: Any) -> str:
    return _sha256_text(_canonical_json(_compound_normalize(value)))


def _compound_engine_source_hash() -> str:
    """Bind every replay receipt to the exact runtime source that executed it."""
    try:
        raw = pathlib.Path(__file__).read_bytes()
    except (OSError, NameError):
        raw = _bc_inspect.getsource(_compound_engine_source_hash).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _compound_code_closure(value: Any, seen: set[tuple[str, str]]) -> Any:
    """Fingerprint the child plus same-runtime helpers/data it actually references.

    This narrows invalidation to relevant implementation dependencies instead of
    invalidating every compound whenever any unrelated source line changes.
    """
    module_name = getattr(value, "__module__", "")
    qualname = getattr(value, "__qualname__", type(value).__qualname__)
    key = (str(module_name), str(qualname))
    if key in seen:
        return {"recursive_reference":list(key)}
    seen.add(key)
    try:
        source = _bc_inspect.getsource(value)
    except (OSError, TypeError):
        code = getattr(value, "__code__", None)
        if code is None:
            return {"opaque":list(key)}
        source = _canonical_json({"bytecode":code.co_code.hex(),"names":list(code.co_names),
            "vars":list(code.co_varnames),"consts":[repr(x) for x in code.co_consts]})
    dependencies: dict[str, Any] = {}
    functions: list[Any] = []
    if _bc_inspect.isfunction(value):
        glob = value.__globals__
        code = value.__code__
        for name in sorted(set(code.co_names)):
            dep = glob.get(name, None)
            if _bc_inspect.isfunction(dep) and getattr(dep, "__module__", None) == module_name:
                functions.append((name, dep))
            elif _bc_inspect.isclass(dep) and getattr(dep, "__module__", None) == module_name:
                functions.append((name, dep))
            elif dep is not None and (type(dep) in (str, int, bool, tuple, list, dict, set, frozenset)
                    or dep is None or _bc_dataclasses.is_dataclass(dep) and not isinstance(dep, type)):
                try:
                    normalized = _compound_normalize(dep)
                    # Keep exact ROM/constants even when large; bind them by digest.
                    encoded = _canonical_json(normalized)
                    dependencies[name] = {"sha256":_sha256_text(encoded),"bytes":len(encoded)}
                except (TypeError, ValueError, RecursionError):
                    pass
    elif _bc_inspect.isclass(value):
        for name, member in sorted(vars(value).items()):
            member = getattr(member, "__func__", member)
            if _bc_inspect.isfunction(member) and getattr(member, "__module__", None) == module_name:
                functions.append((name, member))
    for name, dep in functions:
        dependencies[name] = _compound_code_closure(dep, seen)
    return {"kind":"class" if _bc_inspect.isclass(value) else "function", "symbol":list(key),
            "source_sha256":_sha256_text(source), "dependencies":dependencies}


def _compound_executor_hash(executor_name: str) -> str:
    record = REGISTRY.resolve(executor_name)
    fn = getattr(record.executor, "__func__", record.executor)
    return _sha256_text(_canonical_json(_compound_code_closure(fn, set())))


def _compound_check_values(root: Any, path: str) -> tuple[Any, ...]:
    nodes = [root]
    for part in path.split("."):
        next_nodes: list[Any] = []
        for node in nodes:
            if part == "*":
                if isinstance(node, Mapping):
                    next_nodes.extend(node.values())
                elif isinstance(node, (tuple, list)):
                    next_nodes.extend(node)
                else:
                    return ()
            elif isinstance(node, Mapping) and part in node:
                next_nodes.append(node[part])
            elif hasattr(node, part):
                next_nodes.append(getattr(node, part))
            else:
                return ()
        nodes = next_nodes
    return tuple(nodes)


@dataclass(frozen=True)
class CompoundGlyphStep:
    """One named node in a small DAG. Sources are `in:name` or `step:id`."""
    step_id: str
    glyph_ref: Any
    bindings: tuple[tuple[str, str], ...]
    output_kind: str
    success_checks: tuple[tuple[str, bool], ...] = ()
    glyph_address: str = ""
    implementation_sha256: str = ""
    effect_scopes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompoundGlyphSpec:
    schema: str
    key: str                         # short, movable family head; NOT identity
    label: str                       # human display; NOT identity
    input_kinds: tuple[tuple[str, str], ...]
    steps: tuple[CompoundGlyphStep, ...]
    output_step: str
    output_kind: str
    effect_scopes: tuple[str, ...]
    address: str                    # immutable content identity
    claim_boundary: str = "composition replay certifies declared behavior, not external physical truth"


@dataclass(frozen=True)
class CompoundStepReceipt:
    step_id: str
    glyph_address: str
    input_sha256: str
    output_sha256: str | None
    output_kind: str
    checks_pass: bool
    nested_receipt_id: str | None
    error: str | None


@dataclass(frozen=True)
class CompoundGlyphRun:
    schema: str
    compound_address: str
    key: str
    label: str
    runtime_source_sha256: str
    input_sha256: str
    step_receipts: tuple[CompoundStepReceipt, ...]
    output: Any
    output_sha256: str | None
    pass_all: bool
    unresolved: tuple[str, ...]
    receipt_id: str


@dataclass(frozen=True)
class CompoundAdmissionRecord:
    schema: str
    compound_address: str
    key: str
    run_receipt_id: str
    runtime_source_sha256: str
    input_sha256: str
    previous_head: str | None
    new_head: str
    record_id: str


class CompoundGlyphLibrary:
    """Non-persistent compound catalogue with immutable revisions and movable heads."""
    def __init__(self, catalogue: GlyphCatalogue, authority: EffectAuthority) -> None:
        self._catalogue = catalogue
        self._authority = authority
        self._revisions: dict[str, CompoundGlyphSpec] = {}
        self._heads: dict[str, str] = {}
        self._certifications: dict[str, list[CompoundAdmissionRecord]] = {}

    def _resolve(self, ref: Any) -> tuple[str, str, Any, dict[str, str], set[str], str]:
        if isinstance(ref, CompoundGlyphSpec):
            child = ref
            return ("compound", child.address, child, dict(child.input_kinds),
                    set(child.effect_scopes), child.output_kind)
        if not isinstance(ref, str) or not ref:
            raise TypeError("compound_child_reference_invalid")
        if ref in self._catalogue.names():
            spec = self._catalogue.resolve(ref)
            inputs = dict(spec.arg_types)
            effects = set() if spec.effect_scope == "pure" else {spec.effect_scope}
            return ("leaf", spec.address, spec, inputs, effects, _compound_output_kind(spec))
        address = self._heads.get(ref, ref if ref in self._revisions else None)
        if address is None or address not in self._revisions:
            raise LookupError(f"compound_child_unresolved:{ref}")
        child = self._revisions[address]
        return ("compound", child.address, child, dict(child.input_kinds),
                set(child.effect_scopes), child.output_kind)

    def compose(self, key: str, label: str, input_kinds: Mapping[str, str] | Sequence[tuple[str, str]],
                steps: Sequence[CompoundGlyphStep], output_step: str, output_kind: str) -> CompoundGlyphSpec:
        """Construct a candidate without registering, admitting, or mutating a head."""
        if not isinstance(key, str) or not _COMPOUND_KEY_RE.fullmatch(key):
            raise ValueError("compound_key_must_be_short_lowercase_selector_max_12_chars")
        if not isinstance(label, str) or not label.strip() or len(label.strip()) > 80:
            raise ValueError("compound_label_required_max_80_chars")
        if isinstance(input_kinds, Mapping):
            input_rows = tuple(sorted((str(k), str(v)) for k, v in input_kinds.items()))
        else:
            input_rows = tuple((str(k), str(v)) for k, v in input_kinds)
        if not input_rows or len({k for k, _ in input_rows}) != len(input_rows):
            raise ValueError("compound_inputs_must_have_unique_named_ports")
        known_kinds = {kind for spec in self._catalogue.describe() for kind in spec["arg_types"].values()}
        for name, kind in input_rows:
            if not _COMPOUND_KIND_RE.fullmatch(name) or kind not in known_kinds:
                raise ValueError(f"compound_input_port_or_kind_unknown:{name}:{kind}")
        if not isinstance(steps, (tuple, list)) or not steps:
            raise ValueError("compound_requires_at_least_one_step")
        if len(steps) > 64:
            raise ValueError("compound_step_limit_exceeded")
        parent_inputs = dict(input_rows)
        resolved_steps: list[CompoundGlyphStep] = []
        output_by_step: dict[str, str] = {}
        effects: set[str] = set()
        seen_ids: set[str] = set()
        for raw_step in steps:
            if not isinstance(raw_step, CompoundGlyphStep):
                raise TypeError("compound_steps_must_be_typed_records")
            sid = raw_step.step_id
            if not _COMPOUND_STEP_RE.fullmatch(sid) or sid in seen_ids:
                raise ValueError(f"compound_step_id_invalid_or_duplicate:{sid}")
            if not _COMPOUND_KIND_RE.fullmatch(raw_step.output_kind):
                raise ValueError(f"compound_output_kind_invalid:{sid}")
            seen_ids.add(sid)
            if isinstance(raw_step.glyph_ref, str) and raw_step.glyph_ref in self._catalogue.names():
                target_kind, target_addr, target, child_inputs, child_effects, target_output_kind = self._resolve(raw_step.glyph_ref)
                impl_sha = _compound_executor_hash(target.executor_name)
                child_required = set(target.required_args)
                child_optional = set(target.optional_args)
            else:
                target_kind, target_addr, target, child_inputs, child_effects, target_output_kind = self._resolve(raw_step.glyph_ref)
                impl_sha = _compound_hash({"compound_address": target_addr})
                child_required = set(child_inputs)
                child_optional = set()
            if target_output_kind is None or raw_step.output_kind != target_output_kind:
                raise TypeError(f"compound_output_type_mismatch:{sid}:{raw_step.output_kind}!={target_output_kind}")
            binds = tuple(raw_step.bindings.items()) if isinstance(raw_step.bindings, Mapping) else tuple(raw_step.bindings)
            if len({arg for arg, _ in binds}) != len(binds):
                raise ValueError(f"compound_binding_duplicate_argument:{sid}")
            bound_names = {arg for arg, _ in binds}
            if bound_names - set(child_inputs) or child_required - bound_names:
                raise ValueError(f"compound_binding_argument_set_mismatch:{sid}")
            for arg, source in binds:
                if source.startswith("in:"):
                    port = source[3:]
                    if port not in parent_inputs:
                        raise ValueError(f"compound_input_source_missing:{sid}:{port}")
                    source_kind = parent_inputs[port]
                elif source.startswith("step:"):
                    source_id = source[5:]
                    if source_id not in output_by_step:
                        raise ValueError(f"compound_step_source_not_prior_or_missing:{sid}:{source_id}")
                    source_kind = output_by_step[source_id]
                else:
                    raise ValueError(f"compound_binding_source_syntax_invalid:{sid}:{source}")
                if source_kind != child_inputs[arg]:
                    raise TypeError(f"compound_binding_type_mismatch:{sid}:{arg}:{source_kind}!={child_inputs[arg]}")
            checks: list[tuple[str, bool]] = []
            for check in raw_step.success_checks:
                if (not isinstance(check, (tuple, list)) or len(check) != 2
                        or not isinstance(check[0], str) or type(check[1]) is not bool):
                    raise ValueError(f"compound_success_check_invalid:{sid}")
                if any(not part or not _bc_re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*|\*", part)
                       for part in check[0].split(".")):
                    raise ValueError(f"compound_success_check_path_invalid:{sid}:{check[0]}")
                checks.append((check[0], check[1]))
            output_by_step[sid] = raw_step.output_kind
            effects.update(child_effects)
            resolved_steps.append(CompoundGlyphStep(sid, raw_step.glyph_ref, tuple(sorted(binds)),
                raw_step.output_kind, tuple(checks), target_addr, impl_sha, tuple(sorted(child_effects))))
        if output_step not in output_by_step or output_by_step[output_step] != output_kind:
            raise ValueError("compound_output_contract_mismatch")
        body = {"schema":"BC-COMPOUND-GLYPH-1", "inputs":[list(x) for x in input_rows],
                "steps":[{"id":s.step_id,"child":s.glyph_address,"implementation":s.implementation_sha256,
                           "bindings":[list(b) for b in s.bindings],"output_kind":s.output_kind,
                           "checks":[list(c) for c in s.success_checks],"effects":list(s.effect_scopes)}
                          for s in resolved_steps],
                "output_step":output_step,"output_kind":output_kind,"effects":sorted(effects)}
        address = _sha256_text(_canonical_json(body))[:24]
        return CompoundGlyphSpec("BC-COMPOUND-GLYPH-1", key, label.strip(), input_rows,
            tuple(resolved_steps), output_step, output_kind, tuple(sorted(effects)), address)

    def _resolve_step_child(self, step: CompoundGlyphStep) -> tuple[str, Any]:
        ref = step.glyph_ref
        if isinstance(ref, CompoundGlyphSpec):
            target_kind, address, target, _inputs, _effects, _out = self._resolve(ref)
        else:
            target_kind, address, target, _inputs, _effects, _out = self._resolve(ref)
        if address != step.glyph_address:
            raise ValueError(f"compound_child_identity_drift:{step.step_id}")
        live_impl = _compound_executor_hash(target.executor_name) if target_kind == "leaf" else _compound_hash({"compound_address": address})
        if live_impl != step.implementation_sha256:
            raise ValueError(f"compound_child_implementation_drift:{step.step_id}")
        return target_kind, target

    def _validate_step_output(self, target_kind: str, target: Any, output_kind: str, output: Any, step_id: str) -> None:
        declared = _compound_output_kind(target)
        if declared != output_kind:
            raise TypeError(f"compound_runtime_output_contract_mismatch:{step_id}:{output_kind}!={declared}")
        known_kinds = {kind for spec in self._catalogue.describe() for kind in spec["arg_types"].values()}
        if output_kind in known_kinds:
            self._catalogue._validate_arg(step_id, output_kind, output)
        elif target_kind == "leaf":
            expected_class = _compound_return_class(target)
            if expected_class is None or type(output) is not expected_class:
                raise TypeError(f"compound_runtime_output_type_mismatch:{step_id}:{type(output).__qualname__}")

    def execute(self, candidate: CompoundGlyphSpec | str, *, grants: Iterable[str] = (), **inputs: Any) -> CompoundGlyphRun:
        from_library = isinstance(candidate, str)
        if from_library:
            _kind, _addr, candidate, _in, _effects, _out = self._resolve(candidate)
            certifications = self._certifications.get(candidate.address, [])
            if candidate.address in self._revisions and not certifications:
                raise ValueError("compound_revision_missing_certification_record")
        if not isinstance(candidate, CompoundGlyphSpec):
            raise TypeError("compound_candidate_required")
        missing = set(dict(candidate.input_kinds)) - set(inputs)
        extra = set(inputs) - set(dict(candidate.input_kinds))
        if missing or extra:
            raise ValueError(f"compound_input_set_mismatch:missing={sorted(missing)}:extra={sorted(extra)}")
        for name, kind in candidate.input_kinds:
            self._catalogue._validate_arg(name, kind, inputs[name])
        grant_set = frozenset(grants)
        for effect in candidate.effect_scopes:
            if not self._authority.authorize(effect, grant_set):
                raise PermissionError(f"compound_effect_not_authorized:{effect}")
        input_hash = _compound_hash({"compound": candidate.address,
                                     "inputs": {k: inputs[k] for k, _ in candidate.input_kinds}})
        source_hash = _compound_engine_source_hash()
        values: dict[str, Any] = {}
        step_receipts: list[CompoundStepReceipt] = []
        unresolved: list[str] = []
        for index, step in enumerate(candidate.steps):
            try:
                target_kind, target = self._resolve_step_child(step)
                kwargs = {}
                for arg, source in step.bindings:
                    if source.startswith("in:"):
                        kwargs[arg] = inputs[source[3:]]
                    else:
                        kwargs[arg] = values[source[5:]]
                arg_hash = _compound_hash(kwargs)
                nested_receipt_id = None
                if target_kind == "leaf":
                    result = self._catalogue.execute(target.name, grants=grant_set, **kwargs)
                    output = result
                    child_ok = True
                else:
                    nested = self.execute(target, grants=grant_set, **kwargs)
                    result = nested
                    output = nested.output
                    nested_receipt_id = nested.receipt_id
                    child_ok = nested.pass_all
                    if not child_ok:
                        unresolved.append(f"{step.step_id}:nested_compound_not_closed")
                self._validate_step_output(target_kind, target, step.output_kind, output, step.step_id)
                checks_ok = True
                for path, expected in step.success_checks:
                    check_values = _compound_check_values(output, path)
                    if not check_values or any(type(value) is not bool or value is not expected for value in check_values):
                        checks_ok = False
                        unresolved.append(f"{step.step_id}:check_failed:{path}:expected_{str(expected).lower()}")
                combined_ok = child_ok and checks_ok
                out_hash = _compound_hash(output)
                step_receipts.append(CompoundStepReceipt(step.step_id, step.glyph_address, arg_hash,
                    out_hash, step.output_kind, combined_ok, nested_receipt_id, None))
                values[step.step_id] = output
                if not combined_ok:
                    for later in candidate.steps[index + 1:]:
                        unresolved.append(f"{later.step_id}:deferred_after_failed_step:{step.step_id}")
                    break
            except Exception as exc:
                err = f"{type(exc).__name__}:{exc}"
                unresolved.append(f"{step.step_id}:execution_residual:{err}")
                step_receipts.append(CompoundStepReceipt(step.step_id, step.glyph_address, "", None,
                    step.output_kind, False, None, err))
                for later in candidate.steps[index + 1:]:
                    unresolved.append(f"{later.step_id}:deferred_after_failed_step:{step.step_id}")
                break
        has_output = candidate.output_step in values
        output = values.get(candidate.output_step)
        output_hash = _compound_hash(output) if has_output else None
        pass_all = has_output and len(step_receipts) == len(candidate.steps) and all(r.checks_pass and r.error is None for r in step_receipts) and not unresolved
        receipt_body = {"schema":"BC-COMPOUND-RUN-1","compound":candidate.address,
            "input":input_hash,"steps":[_bc_dataclasses.asdict(r) for r in step_receipts],
            "output":output_hash,"pass_all":pass_all,"unresolved":unresolved}
        receipt_id = _sha256_text(_canonical_json(receipt_body))[:32]
        return CompoundGlyphRun("BC-COMPOUND-RUN-1", candidate.address, candidate.key, candidate.label,
            source_hash, input_hash, tuple(step_receipts), output, output_hash, pass_all,
            tuple(unresolved), receipt_id)

    def reopen(self, candidate: CompoundGlyphSpec | str, inputs: Mapping[str, Any], receipt: CompoundGlyphRun, *, grants: Iterable[str] = ()) -> dict[str, Any]:
        if isinstance(candidate, str):
            _kind, _addr, candidate, _in, _effects, _out = self._resolve(candidate)
        if not isinstance(candidate, CompoundGlyphSpec) or not isinstance(receipt, CompoundGlyphRun):
            return {"pass":False,"reason":"compound_candidate_or_receipt_invalid"}
        if receipt.compound_address != candidate.address:
            return {"pass":False,"reason":"compound_receipt_address_mismatch"}
        try:
            rebuilt = self.execute(candidate, grants=grants, **dict(inputs))
        except Exception as exc:
            return {"pass":False,"reason":f"compound_reopen_execution_failed:{type(exc).__name__}:{exc}"}
        equal = (rebuilt.schema == receipt.schema and rebuilt.compound_address == receipt.compound_address
                 and rebuilt.input_sha256 == receipt.input_sha256 and rebuilt.step_receipts == receipt.step_receipts
                 and rebuilt.output_sha256 == receipt.output_sha256 and rebuilt.pass_all == receipt.pass_all
                 and rebuilt.unresolved == receipt.unresolved and rebuilt.receipt_id == receipt.receipt_id)
        return {"pass":bool(equal and rebuilt.pass_all), "reason":None if equal and rebuilt.pass_all else "compound_receipt_rebuild_or_closure_mismatch",
            "compound_address":candidate.address,"receipt_id":receipt.receipt_id,"rebuilt_receipt_id":rebuilt.receipt_id,
            "steps_rebuilt":len(rebuilt.step_receipts),"runtime_source_recorded":bool(rebuilt.runtime_source_sha256),
            "runtime_source_unchanged":rebuilt.runtime_source_sha256==receipt.runtime_source_sha256,
            "dependency_fingerprint_matches":rebuilt.compound_address==receipt.compound_address,
            "output_rebuilt":rebuilt.output_sha256==receipt.output_sha256,"unresolved":list(rebuilt.unresolved),
            "admitted":candidate.address in self._revisions,"persistent":False}

    def admit(self, candidate: CompoundGlyphSpec, inputs: Mapping[str, Any], receipt: CompoundGlyphRun,
              *, grants: Iterable[str] = (), expected_head: str | None = None) -> dict[str, Any]:
        """Explicit in-memory admission only; never writes source or persistent storage."""
        if not isinstance(candidate, CompoundGlyphSpec):
            raise TypeError("compound_candidate_required_for_admission")
        if not self._authority.authorize("glyph_admission", grants):
            raise PermissionError("glyph_admission_not_authorized")
        if any(not step.success_checks for step in candidate.steps):
            raise ValueError("compound_admission_requires_explicit_checks_for_every_step")
        current = self._heads.get(candidate.key)
        if current != expected_head:
            raise ValueError(f"compound_head_precondition_failed:expected={expected_head}:current={current}")
        verified = self.reopen(candidate, inputs, receipt, grants=grants)
        if verified.get("pass") is not True or receipt.pass_all is not True:
            raise ValueError("compound_admission_requires_fresh_closed_replay_receipt")
        self._revisions[candidate.address] = candidate
        old = current
        self._heads[candidate.key] = candidate.address
        record_body = {"schema":"BC-COMPOUND-ADMISSION-1", "compound":candidate.address,
            "key":candidate.key,"run_receipt":receipt.receipt_id,"runtime_source":receipt.runtime_source_sha256,
            "input":receipt.input_sha256,"previous_head":old,"new_head":candidate.address}
        record_id = _sha256_text(_canonical_json(record_body))[:32]
        record = CompoundAdmissionRecord("BC-COMPOUND-ADMISSION-1", candidate.address, candidate.key,
            receipt.receipt_id, receipt.runtime_source_sha256, receipt.input_sha256, old, candidate.address, record_id)
        ledger = self._certifications.setdefault(candidate.address, [])
        if not any(row.record_id == record_id for row in ledger):
            ledger.append(record)
        return {"pass":True,"key":candidate.key,"old_head":old,"new_head":candidate.address,
            "admission_record_id":record_id,"prior_revision_retained":old is None or old in self._revisions,"persistent":False,
            "source_written":False,"cold_commit":False}

    def contains(self, ref: str) -> bool:
        return isinstance(ref, str) and (ref in self._heads or ref in self._revisions)

    def resolve_public(self, ref: str) -> CompoundGlyphSpec:
        _kind, _addr, target, _inputs, _effects, _out = self._resolve(ref)
        if not isinstance(target, CompoundGlyphSpec):
            raise LookupError(f"not_a_compound_glyph:{ref}")
        return target

    def summary(self) -> dict[str, Any]:
        stale_count = 0
        for candidate in self._revisions.values():
            try:
                for step in candidate.steps:
                    self._resolve_step_child(step)
            except (LookupError, TypeError, ValueError):
                stale_count += 1
        return {"enabled":True,"schema":"BC-COMPOUND-GLYPH-1","candidate_creation":"content-addressed_and_non-mutating",
            "short_key_max_chars":12,"label_max_chars":80,"immutable_revision_count":len(self._revisions),
            "active_track_count":len(self._heads),"certification_record_count":sum(len(x) for x in self._certifications.values()),
            "stale_revision_count":stale_count,"automatic_admission":False,"persistent_save":False,
            "source_mutation":False,"cold_commit":False,
            "typed_output_contracts":True,"child_implementation_dependency_fingerprints":True,
            "runtime_source_provenance_recorded":True,"dependency_closure_bound_replay":True,
            "revisions_immutable":True,"head_move_requires_expected_prior_address":True,
            "admission_provenance_retained":True,
            "principle":"short selectors; stable content addresses; graph provenance instead of chained names; old revisions retained"}


COMPOUND_GLYPH_LIBRARY = CompoundGlyphLibrary(GLYPH_CATALOG, EffectAuthority())


def compose_glyph(key: str, label: str, input_kinds: Mapping[str, str] | Sequence[tuple[str, str]],
                  steps: Sequence[CompoundGlyphStep], output_step: str, output_kind: str) -> CompoundGlyphSpec:
    """Public candidate builder: deliberately does not admit or persist."""
    return COMPOUND_GLYPH_LIBRARY.compose(key, label, input_kinds, steps, output_step, output_kind)


def execute_compound_glyph(candidate: CompoundGlyphSpec | str, *, grants: Iterable[str] = (), **inputs: Any) -> CompoundGlyphRun:
    return COMPOUND_GLYPH_LIBRARY.execute(candidate, grants=grants, **inputs)


def reopen_compound_glyph(candidate: CompoundGlyphSpec | str, inputs: Mapping[str, Any], receipt: CompoundGlyphRun) -> dict[str, Any]:
    return COMPOUND_GLYPH_LIBRARY.reopen(candidate, inputs, receipt)

def resolve_glyph(name: str | CompoundGlyphSpec) -> GlyphSpec | CompoundGlyphSpec:
    """Resolve a leaf or explicitly admitted compound through one public interface."""
    if isinstance(name, CompoundGlyphSpec):
        return name
    if name in GLYPH_CATALOG.names():
        return GLYPH_CATALOG.resolve(name)
    if COMPOUND_GLYPH_LIBRARY.contains(name):
        return COMPOUND_GLYPH_LIBRARY.resolve_public(name)
    raise LookupError(f"unregistered_glyph:{name}")


def execute_glyph(name: str | CompoundGlyphSpec, *, grants: Iterable[str] = (), **arguments: Any) -> Any:
    """One public execution path for leaf glyphs and compound candidates/admissions."""
    resolved = resolve_glyph(name)
    if isinstance(resolved, GlyphSpec):
        return GLYPH_CATALOG.execute(resolved.name, grants=grants, **arguments)
    return COMPOUND_GLYPH_LIBRARY.execute(resolved, grants=grants, **arguments)



# ---------------------------------------------------------------------------
# Warm deterministic learning substrate (immutable evidence; no floor writes)
# ---------------------------------------------------------------------------
# Learning here means accumulating replayable examples, recognizing repeated
# transition motifs, retaining counterexamples/residuals, and proposing reuse.
# It does NOT infer an executor from state deltas, admit glyphs, or persist files.

@dataclass(frozen=True)
class LearningEvidence:
    schema: str
    evidence_address: str
    source_kind: str
    pattern_address: str
    source_address: str | None
    source_container_address: str | None
    source_witness_id: str
    input_sha256: str
    result_address: str | None
    candidate_address: str | None
    child_addresses: tuple[str, ...]
    passed: bool
    checks: tuple[tuple[str, bool], ...]
    residuals: tuple[str, ...]
    context_json: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "evidence_address": self.evidence_address,
            "source_kind": self.source_kind, "pattern_address": self.pattern_address,
            "source_address": self.source_address,
            "source_container_address": self.source_container_address,
            "source_witness_id": self.source_witness_id, "input_sha256": self.input_sha256,
            "result_address": self.result_address, "candidate_address": self.candidate_address,
            "child_addresses": list(self.child_addresses), "passed": self.passed,
            "checks": [[name, result] for name, result in self.checks],
            "residuals": list(self.residuals), "context": json.loads(self.context_json),
        }


@dataclass(frozen=True)
class GlyphLearningLedger:
    schema: str
    evidence: tuple[LearningEvidence, ...]
    address: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "address": self.address,
                "evidence": [entry.as_dict() for entry in self.evidence],
                "evidence_count": len(self.evidence),
                "policy": "portable evidence record; import validates identity; replay/certification remains separate"}


@dataclass(frozen=True)
class LearningPatternSummary:
    schema: str
    pattern_address: str
    source_kind: str
    evidence_addresses: tuple[str, ...]
    independent_case_count: int
    passing_case_count: int
    failing_case_count: int
    distinct_input_count: int
    status: str
    reusable_candidate_address: str | None
    executable_glyph_candidate: bool
    residuals: tuple[str, ...]
    summary_address: str


@dataclass(frozen=True)
class LearningProfile:
    schema: str
    ledger_address: str
    minimum_independent_cases: int
    patterns: tuple[LearningPatternSummary, ...]
    unresolved: tuple[str, ...]
    profile_address: str


@dataclass(frozen=True)
class LearningProposal:
    schema: str
    proposal_address: str
    pattern_address: str
    source_kind: str
    evidence_addresses: tuple[str, ...]
    recommendation: str
    reusable_candidate_address: str | None
    executable_candidate: bool
    execution_performed: bool
    glyph_admitted: bool
    persisted: bool
    claim_boundary: str


@dataclass(frozen=True)
class LearningProposalSet:
    schema: str
    ledger_address: str
    profile_address: str
    minimum_independent_cases: int
    proposals: tuple[LearningProposal, ...]
    unresolved: tuple[str, ...]
    proposal_set_address: str


def _learn_transition_shape(changes: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Retain paths/types/direction while abstracting exact values into evidence context."""
    rows = []
    for change in changes:
        before, after = change.get("before"), change.get("after")
        if type(before) is int and type(after) is int:
            direction = "increase" if after > before else "decrease" if after < before else "same"
        elif type(before) is bool and type(after) is bool:
            direction = "true_to_false" if before and not after else "false_to_true" if after and not before else "same"
        elif type(before) is type(after):
            direction = "changed" if before != after else "same"
        else:
            direction = "type_replacement"
        rows.append({"path": list(change.get("path", ())),
                     "before_type": type(before).__name__, "after_type": type(after).__name__,
                     "direction": direction})
    return tuple(sorted(rows, key=_canonical_json))


def _learn_context_json(value: Mapping[str, Any]) -> str:
    # Preserve a directly navigable JSON record; normalize opaque values at the
    # call site rather than wrapping every mapping as an encoded key/value list.
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _learn_evidence_body(*, source_kind: str, pattern_address: str,
                         source_address: str | None, source_container_address: str | None,
                         source_witness_id: str, input_sha256: str, result_address: str | None,
                         candidate_address: str | None, child_addresses: Sequence[str], passed: bool,
                         checks: Sequence[tuple[str, bool]], residuals: Sequence[str],
                         context_json: str) -> dict[str, Any]:
    return {"schema":"BC-LEARNING-EVIDENCE-1", "source_kind":source_kind,
        "pattern_address":pattern_address, "source_address":source_address,
        "source_container_address":source_container_address, "source_witness_id":source_witness_id,
        "input_sha256":input_sha256, "result_address":result_address,
        "candidate_address":candidate_address, "child_addresses":list(child_addresses),
        "passed":passed, "checks":[[n,v] for n,v in checks],
        "residuals":list(residuals), "context":json.loads(context_json)}


def _make_learning_evidence(*, source_kind: str, pattern_address: str,
                            source_address: str | None, source_container_address: str | None,
                            source_witness_id: str, input_sha256: str, result_address: str | None,
                            candidate_address: str | None, child_addresses: Sequence[str], passed: bool,
                            checks: Sequence[tuple[str, bool]], residuals: Sequence[str],
                            context: Mapping[str, Any]) -> LearningEvidence:
    context_json = _learn_context_json(context)
    checks_t = tuple(sorted((str(n), bool(v)) for n, v in checks))
    children_t = tuple(child_addresses)
    residuals_t = tuple(sorted(set(str(x) for x in residuals)))
    body = _learn_evidence_body(source_kind=source_kind, pattern_address=pattern_address,
        source_address=source_address, source_container_address=source_container_address,
        source_witness_id=source_witness_id, input_sha256=input_sha256, result_address=result_address,
        candidate_address=candidate_address, child_addresses=children_t, passed=bool(passed),
        checks=checks_t, residuals=residuals_t, context_json=context_json)
    address = _compound_hash(body)[:32]
    return LearningEvidence("BC-LEARNING-EVIDENCE-1", address, source_kind, pattern_address,
        source_address, source_container_address, source_witness_id, input_sha256, result_address,
        candidate_address, children_t, bool(passed), checks_t, residuals_t, context_json)


def _learning_ledger_address(evidence: Sequence[LearningEvidence]) -> str:
    return _compound_hash({"schema":"BC-GLYPH-LEARNING-LEDGER-1",
                           "evidence":sorted(row.evidence_address for row in evidence)})[:32]


def new_glyph_learning_ledger() -> GlyphLearningLedger:
    return GlyphLearningLedger("BC-GLYPH-LEARNING-LEDGER-1", (), _learning_ledger_address(()))


def _learning_add(ledger: GlyphLearningLedger, row: LearningEvidence) -> GlyphLearningLedger:
    if not isinstance(ledger, GlyphLearningLedger):
        raise TypeError("glyph_learning_ledger_required")
    existing = {entry.evidence_address: entry for entry in ledger.evidence}
    existing.setdefault(row.evidence_address, row)
    rows = tuple(existing[k] for k in sorted(existing))
    return GlyphLearningLedger("BC-GLYPH-LEARNING-LEDGER-1", rows, _learning_ledger_address(rows))


def record_self_feed_evidence(ledger: GlyphLearningLedger, address: BCFloorAddress,
                              cone: DepthWaveCone, witness: FullAddressWitness,
                              observation: DepthWaveSelfFeedObservation) -> GlyphLearningLedger:
    """Turn a real self-feed observation into portable evidence after source-bound checks."""
    if not isinstance(ledger, GlyphLearningLedger): raise TypeError("glyph_learning_ledger_required")
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("self_feed_address_and_cone_required")
    if not isinstance(witness, FullAddressWitness) or not isinstance(observation, DepthWaveSelfFeedObservation):
        raise TypeError("self_feed_witness_and_observation_required")
    cone_witness = reopen_depth_wave_cone(address, cone)
    identity_checks = {
        "cone_reopened": cone_witness.pass_all,
        "observation_root_matches": observation.root_address_id == address.address_id == cone.root_address_id,
        "observation_cone_matches": observation.cone_address == cone.cone_address,
        "observation_witness_matches": observation.witness_id == witness.witness_id,
        "witness_root_matches": witness.start.address_id == address.address_id,
        "observation_end_matches": observation.end_address_id == witness.end.address_id,
        "observation_changes_match": observation.changes == witness.delta.changes,
    }
    try:
        replayed_end = witness.delta.apply(address)
        identity_checks["delta_replays_to_end"] = replayed_end.address_id == witness.end.address_id
    except (TypeError, ValueError, KeyError, IndexError):
        identity_checks["delta_replays_to_end"] = False
    identity_checks["observation_replay_flag_matches"] = observation.difference_replays == witness.difference_replays
    identity_checks["observation_dependency_flag_matches"] = observation.dependency_closed == witness.dependency_closed
    if not all(identity_checks.values()):
        raise ValueError("learning_self_feed_source_binding_failed:" + ",".join(k for k,v in identity_checks.items() if not v))

    shape = _learn_transition_shape(witness.delta.changes)
    pattern_body = {"schema":"BC-LEARN-TRANSITION-MOTIF-1", "shape":shape,
                    "target_depth_touched":observation.target_depth_touched}
    pattern = _compound_hash(pattern_body)[:32]
    passed = bool(cone_witness.pass_all and witness.dependency_closed and witness.difference_replays)
    residuals = list(witness.unresolved)
    if not witness.dependency_closed: residuals.append("dependency_closure_not_established")
    if not witness.difference_replays: residuals.append("difference_replay_not_established")
    if not shape: residuals.append("empty_change_set_not_a_growth_candidate")
    context = {
        "source_address_payload": address.as_dict(), "result_address_payload": witness.end.as_dict(),
        "cone_request":{"max_recursive_depth":cone.max_recursive_depth,"wave_radius":cone.wave_radius,
                        "target_child_address_id":cone.target_child_address_id,
                        "include_root_lattice":cone.include_root_lattice},
        "cone_address":cone.cone_address,"cone_reopen_witness_address":cone_witness.witness_address,
        "witness":{"witness_id":witness.witness_id,"events":list(witness.events),
                   "delta":{"schema":witness.delta.schema,"parent_id":witness.delta.parent_id,
                            "end_id":witness.delta.end_id,"difference_address":witness.delta.difference_address,
                            "changes":list(witness.delta.changes)},
                   "dependency_closed":witness.dependency_closed,
                   "return_to_entry_closed":witness.return_to_entry_closed,
                   "difference_replays":witness.difference_replays,"unresolved":list(witness.unresolved)},
        "observation":observation.__dict__,"normalized_transition_shape":list(shape),
        "pattern_body":pattern_body,"glyph_admitted":False,"persisted":False}
    row = _make_learning_evidence(source_kind="self_feed", pattern_address=pattern,
        source_address=address.address_id, source_container_address=cone.cone_address,
        source_witness_id=witness.witness_id, input_sha256=_compound_hash(address.as_dict()),
        result_address=witness.end.address_id, candidate_address=None, child_addresses=(),
        passed=passed, checks=tuple(identity_checks.items()), residuals=residuals, context=context)
    return _learning_add(ledger, row)


def record_compound_learning_case(ledger: GlyphLearningLedger, candidate: CompoundGlyphSpec,
                                 inputs: Mapping[str, Any], receipt: CompoundGlyphRun) -> GlyphLearningLedger:
    """Record both passing and failing runs, only when the exact receipt replays."""
    if not isinstance(ledger, GlyphLearningLedger): raise TypeError("glyph_learning_ledger_required")
    if not isinstance(candidate, CompoundGlyphSpec) or not isinstance(receipt, CompoundGlyphRun):
        raise TypeError("compound_candidate_and_run_receipt_required")
    if not isinstance(inputs, Mapping): raise TypeError("compound_learning_inputs_must_be_mapping")
    if receipt.compound_address != candidate.address:
        raise ValueError("learning_compound_receipt_address_mismatch")
    fresh = COMPOUND_GLYPH_LIBRARY.execute(candidate, **dict(inputs))
    if (fresh.receipt_id != receipt.receipt_id or fresh.input_sha256 != receipt.input_sha256
            or fresh.step_receipts != receipt.step_receipts or fresh.output_sha256 != receipt.output_sha256
            or fresh.pass_all != receipt.pass_all or fresh.unresolved != receipt.unresolved):
        raise ValueError("learning_compound_receipt_not_reproducible")
    input_sha = _compound_hash(dict(inputs))
    carrier = inputs.get("carrier", inputs.get("address", inputs.get("start")))
    source_address = getattr(carrier, "address_id", None)
    child_addresses = tuple(step.glyph_address for step in candidate.steps)
    checks = tuple((f"step:{r.step_id}:checks_pass", r.checks_pass and r.error is None) for r in fresh.step_receipts)
    context = {"candidate_definition":{"schema":candidate.schema,"address":candidate.address,
                "key":candidate.key,"label":candidate.label,
                "input_kinds":[list(x) for x in candidate.input_kinds],
                "steps":[{"id":s.step_id,"child_address":s.glyph_address,
                           "child_ref":s.glyph_ref if isinstance(s.glyph_ref,str) else s.glyph_ref.address,
                           "implementation_sha256":s.implementation_sha256,
                           "bindings":[list(x) for x in s.bindings],"output_kind":s.output_kind,
                           "success_checks":[list(x) for x in s.success_checks],
                           "effect_scopes":list(s.effect_scopes)} for s in candidate.steps],
                "output_step":candidate.output_step,"output_kind":candidate.output_kind,
                "effect_scopes":list(candidate.effect_scopes)},
        "inputs_normalized":{str(k):_compound_normalize(v) for k,v in sorted(inputs.items(),key=lambda item:str(item[0]))},
        "run":{"receipt_id":fresh.receipt_id,"input_sha256":fresh.input_sha256,
               "output_sha256":fresh.output_sha256,"runtime_source_sha256":fresh.runtime_source_sha256,
               "pass_all":fresh.pass_all,"unresolved":list(fresh.unresolved),
               "step_receipts":[_bc_dataclasses.asdict(x) for x in fresh.step_receipts]},
        "result_address":fresh.output_sha256,"glyph_admitted":False,"persisted":False}
    row = _make_learning_evidence(source_kind="compound_case", pattern_address=candidate.address,
        source_address=source_address, source_container_address=candidate.address,
        source_witness_id=fresh.receipt_id, input_sha256=input_sha,
        result_address=fresh.output_sha256, candidate_address=candidate.address,
        child_addresses=child_addresses, passed=fresh.pass_all, checks=checks,
        residuals=fresh.unresolved, context=context)
    return _learning_add(ledger, row)


def build_learning_profile(ledger: GlyphLearningLedger, min_cases: int = 2) -> LearningProfile:
    if not isinstance(ledger, GlyphLearningLedger): raise TypeError("glyph_learning_ledger_required")
    if type(min_cases) is not int or not 1 <= min_cases <= 64:
        raise ValueError("learning_min_cases_must_be_1_to_64")
    grouped: dict[tuple[str,str], list[LearningEvidence]] = {}
    for row in ledger.evidence:
        grouped.setdefault((row.source_kind,row.pattern_address), []).append(row)
    summaries=[]
    for (source_kind,pattern), rows in sorted(grouped.items()):
        evidence_ids=tuple(sorted(row.evidence_address for row in rows))
        independent = {row.source_witness_id for row in rows} if source_kind == "self_feed" else {row.input_sha256 for row in rows}
        inputs = {row.input_sha256 for row in rows}
        pass_count=sum(1 for row in rows if row.passed)
        fail_count=len(rows)-pass_count
        residuals=sorted({r for row in rows for r in row.residuals})
        child_candidates={row.candidate_address for row in rows if row.candidate_address}
        reuse_address=next(iter(child_candidates)) if len(child_candidates)==1 else None
        if source_kind == "self_feed":
            if not rows[0].context_json:
                nontrivial=False
            else:
                try: nontrivial=bool(json.loads(rows[0].context_json).get("normalized_transition_shape"))
                except (TypeError,ValueError): nontrivial=False
            if not nontrivial:
                status="no_change_not_proposed"
            elif fail_count:
                status="mixed_transition_evidence_requires_review"
            elif len(independent) >= min_cases:
                status="repeated_transition_motif"
            else:
                status="insufficient_independent_evidence"
            executable=False
        else:
            if pass_count == 0:
                status="no_successful_replay"
            elif fail_count:
                status="boundary_review_required"
            elif len(inputs) < min_cases:
                status="insufficient_input_diversity"
            else:
                status="reusable_block_candidate"
            executable=False  # an observed compound is reusable as a child only after separate admission
        body={"schema":"BC-LEARNING-PATTERN-SUMMARY-1","pattern":pattern,"kind":source_kind,
              "evidence":list(evidence_ids),"independent":len(independent),"pass_count":pass_count,
              "fail_count":fail_count,"inputs":len(inputs),"status":status,
              "reuse_address":reuse_address,"executable":executable,"residuals":residuals}
        summaries.append(LearningPatternSummary("BC-LEARNING-PATTERN-SUMMARY-1",pattern,source_kind,
            evidence_ids,len(independent),pass_count,fail_count,len(inputs),status,reuse_address,executable,
            tuple(residuals),_compound_hash(body)[:32]))
    unresolved=tuple(sorted({r for row in ledger.evidence for r in row.residuals}))
    body={"schema":"BC-LEARNING-PROFILE-1","ledger":ledger.address,"minimum_independent_cases":min_cases,
          "patterns":[p.summary_address for p in summaries],"unresolved":list(unresolved)}
    return LearningProfile("BC-LEARNING-PROFILE-1",ledger.address,min_cases,tuple(summaries),unresolved,
                           _compound_hash(body)[:32])


def reopen_learning_profile(ledger: GlyphLearningLedger, profile: LearningProfile) -> dict[str, Any]:
    if not isinstance(profile,LearningProfile):
        return {"pass":False,"reason":"learning_profile_required"}
    try: rebuilt=build_learning_profile(ledger,profile.minimum_independent_cases)
    except (TypeError,ValueError) as exc:
        return {"pass":False,"reason":f"learning_profile_rebuild_failed:{type(exc).__name__}:{exc}"}
    passed=rebuilt==profile and profile.ledger_address==ledger.address
    return {"schema":"BC-LEARNING-PROFILE-REOPEN-1","pass":passed,
            "ledger_address":ledger.address,"profile_address":profile.profile_address,
            "rebuilt_profile_address":rebuilt.profile_address,"patterns_rebuilt":len(rebuilt.patterns),
            "evidence_count":len(ledger.evidence),"persisted":False}


def propose_learning_routes(ledger: GlyphLearningLedger, min_cases: int = 2) -> LearningProposalSet:
    profile=build_learning_profile(ledger,min_cases)
    proposals=[]
    for pattern in profile.patterns:
        if pattern.status == "repeated_transition_motif":
            recommendation="inspect_transition_delta_and_bind_to_a_named_resident_operation"
            reusable_address=None
            claim="repeated structural motif only; no executor inferred from a delta; needs operation-level construction and replay"
        elif pattern.status == "reusable_block_candidate":
            recommendation="test_as_a_reusable_child_in_a_new_compound_candidate"
            reusable_address=pattern.reusable_candidate_address
            claim="repeated passing executions show reuse evidence, not semantic universality or admission"
        else:
            continue
        body={"schema":"BC-LEARNING-PROPOSAL-1","pattern":pattern.pattern_address,
              "kind":pattern.source_kind,"evidence":list(pattern.evidence_addresses),
              "recommendation":recommendation,"reusable_candidate_address":reusable_address,
              "executable_candidate":False,"execution_performed":False,"glyph_admitted":False,
              "persisted":False,"claim_boundary":claim}
        proposals.append(LearningProposal("BC-LEARNING-PROPOSAL-1",_compound_hash(body)[:32],
            pattern.pattern_address,pattern.source_kind,pattern.evidence_addresses,recommendation,
            reusable_address,False,False,False,False,claim))
    proposals=tuple(sorted(proposals,key=lambda p:p.proposal_address))
    unresolved=profile.unresolved
    body={"schema":"BC-LEARNING-PROPOSAL-SET-1","ledger":ledger.address,"profile":profile.profile_address,
          "minimum_independent_cases":min_cases,
          "proposals":[p.proposal_address for p in proposals],"unresolved":list(unresolved)}
    return LearningProposalSet("BC-LEARNING-PROPOSAL-SET-1",ledger.address,profile.profile_address,
                               min_cases,proposals,unresolved,_compound_hash(body)[:32])


def reopen_learning_proposals(ledger: GlyphLearningLedger, proposals: LearningProposalSet) -> dict[str, Any]:
    if not isinstance(proposals,LearningProposalSet):
        return {"pass":False,"reason":"learning_proposal_set_required"}
    rebuilt=propose_learning_routes(ledger, proposals.minimum_independent_cases)
    passed=rebuilt==proposals
    return {"schema":"BC-LEARNING-PROPOSAL-REOPEN-1","pass":passed,
            "ledger_address":ledger.address,"proposal_set_address":proposals.proposal_set_address,
            "rebuilt_proposal_set_address":rebuilt.proposal_set_address,
            "proposal_count":len(rebuilt.proposals),"persisted":False}



def export_glyph_learning_ledger(ledger: GlyphLearningLedger) -> dict[str, Any]:
    if not isinstance(ledger,GlyphLearningLedger): raise TypeError("glyph_learning_ledger_required")
    return ledger.as_dict()


def import_glyph_learning_ledger(payload: Mapping[str, Any]) -> GlyphLearningLedger:
    """Validate and reconstruct portable evidence; this is not a persistence side effect."""
    if not isinstance(payload,Mapping) or payload.get("schema")!="BC-GLYPH-LEARNING-LEDGER-1":
        raise ValueError("learning_ledger_schema_invalid")
    raw_rows=payload.get("evidence")
    if not isinstance(raw_rows,list): raise TypeError("learning_ledger_evidence_must_be_list")
    rows=[]; seen=set()
    for raw in raw_rows:
        if not isinstance(raw,Mapping): raise TypeError("learning_evidence_record_must_be_mapping")
        context=raw.get("context")
        if not isinstance(context,Mapping): raise TypeError("learning_evidence_context_must_be_mapping")
        checks=raw.get("checks",[]); children=raw.get("child_addresses",[]); residuals=raw.get("residuals",[])
        if type(raw.get("passed")) is not bool: raise TypeError("learning_evidence_pass_flag_must_be_boolean")
        if not isinstance(checks,list) or any(not isinstance(x,(list,tuple)) or len(x)!=2
                or not isinstance(x[0],str) or type(x[1]) is not bool for x in checks):
            raise TypeError("learning_evidence_checks_must_be_named_boolean_pairs")
        if not isinstance(children,list) or any(not isinstance(x,str) for x in children):
            raise TypeError("learning_evidence_child_addresses_must_be_strings")
        if not isinstance(residuals,list) or any(not isinstance(x,str) for x in residuals):
            raise TypeError("learning_evidence_residuals_must_be_strings")
        row=_make_learning_evidence(source_kind=raw["source_kind"],pattern_address=raw["pattern_address"],
            source_address=raw.get("source_address"),source_container_address=raw.get("source_container_address"),
            source_witness_id=raw["source_witness_id"],input_sha256=raw["input_sha256"],
            result_address=raw.get("result_address"),candidate_address=raw.get("candidate_address"),
            child_addresses=children,passed=raw["passed"],checks=tuple((x[0],x[1]) for x in checks),
            residuals=residuals,context=context)
        if row.evidence_address != raw.get("evidence_address"):
            raise ValueError("learning_evidence_content_address_mismatch")
        if row.evidence_address in seen: raise ValueError("learning_evidence_duplicate_address")
        seen.add(row.evidence_address); rows.append(row)
    rows_t=tuple(sorted(rows,key=lambda x:x.evidence_address))
    ledger=GlyphLearningLedger("BC-GLYPH-LEARNING-LEDGER-1",rows_t,_learning_ledger_address(rows_t))
    if payload.get("address") != ledger.address:
        raise ValueError("learning_ledger_address_mismatch")
    expected_payload=ledger.as_dict()
    if payload.get("evidence_count") != len(rows_t):
        raise ValueError("learning_ledger_evidence_count_mismatch")
    if payload.get("policy") != expected_payload["policy"]:
        raise ValueError("learning_ledger_policy_mismatch")
    if set(payload.keys()) != set(expected_payload.keys()):
        raise ValueError("learning_ledger_top_level_fields_mismatch")
    return ledger


def reopen_glyph_learning_ledger(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        rebuilt=import_glyph_learning_ledger(payload)
        exported=export_glyph_learning_ledger(rebuilt)
        exact=exported==dict(payload)
        return {"schema":"BC-LEARNING-LEDGER-REOPEN-1","pass":exact,
                "ledger_address":rebuilt.address,"evidence_count":len(rebuilt.evidence),
                "all_evidence_addresses_recomputed":True,"full_context_retained":True,
                "persistent_save_performed":False}
    except (KeyError,TypeError,ValueError) as exc:
        return {"schema":"BC-LEARNING-LEDGER-REOPEN-1","pass":False,
                "reason":f"learning_ledger_reopen_failed:{type(exc).__name__}:{exc}",
                "persistent_save_performed":False}


# ---------------------------------------------------------------------------
# Sparse perspective comparison and structural-name index.
# This is deliberately separate from BC.LEARN.PROFILE and BC.LEARN.PROPOSALS:
# the same evidence may have several comparison views, but those views must not
# become extra patterns, extra proposals, or extra executable glyphs.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LearningComparisonEntry:
    evidence_address: str
    pattern_address: str
    source_kind: str
    route_names: tuple[str, ...]
    view_signatures: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        return {"evidence_address":self.evidence_address,"pattern_address":self.pattern_address,
                "source_kind":self.source_kind,"route_names":list(self.route_names),
                "view_signatures":[[name,address] for name,address in self.view_signatures]}


@dataclass(frozen=True)
class LearningComparisonClass:
    view_name: str
    signature_address: str
    evidence_addresses: tuple[str, ...]
    pattern_addresses: tuple[str, ...]
    route_names: tuple[str, ...]
    class_address: str
    claim_boundary: str = "comparison-view match only; not semantic equivalence, admission, or permission to merge execution"

    def as_dict(self) -> dict[str, Any]:
        return {"view_name":self.view_name,"signature_address":self.signature_address,
                "evidence_addresses":list(self.evidence_addresses),
                "pattern_addresses":list(self.pattern_addresses),"route_names":list(self.route_names),
                "class_address":self.class_address,"claim_boundary":self.claim_boundary}


@dataclass(frozen=True)
class LearningComparisonMap:
    schema: str
    ledger_address: str
    evidence_count: int
    entries: tuple[LearningComparisonEntry, ...]
    classes: tuple[LearningComparisonClass, ...]
    scale_routes: tuple[tuple[str, tuple[int, ...], int, str, str], ...]
    center_depth_contract: str
    unique_generalized_redundancy: int
    unresolved: tuple[str, ...]
    map_address: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema":self.schema,"ledger_address":self.ledger_address,
                "evidence_count":self.evidence_count,"entries":[x.as_dict() for x in self.entries],
                "classes":[x.as_dict() for x in self.classes],
                "scale_routes":[{"name":name,"shape":list(shape),"capacity":capacity,
                                 "shell":shell,"address_family":family}
                                for name,shape,capacity,shell,family in self.scale_routes],
                "center_depth_contract":self.center_depth_contract,
                "unique_generalized_redundancy":self.unique_generalized_redundancy,
                "unresolved":list(self.unresolved),"map_address":self.map_address,
                "policy":"derived name/control index; full evidence stays in the ledger; no profile/proposal multiplication; matches are not executable equivalence proofs"}


def _learn_gcd(values: Sequence[int]) -> int:
    a=0
    for value in values:
        if type(value) is not int:
            continue
        b=abs(value)
        while b:
            a,b=b,a%b
    return a or 1


def _learn_points(context: Mapping[str, Any]) -> tuple[tuple[int,int,int], ...] | None:
    inputs=context.get("inputs_normalized")
    if not isinstance(inputs,Mapping):
        return None
    points=inputs.get("points")
    if not isinstance(points,(tuple,list)) or not points:
        return None
    out=[]
    for point in points:
        if not isinstance(point,(tuple,list)) or len(point)!=3 or any(type(v) is not int for v in point):
            return None
        out.append((point[0],point[1],point[2]))
    return tuple(out)


def _learn_normalize_points(points: tuple[tuple[int,int,int], ...] | None, view_name: str) -> Any:
    if points is None:
        return None
    origin=points[0]
    relative=tuple(tuple(p[i]-origin[i] for i in range(3)) for p in points)
    if view_name in {"zero_plane_unit_magnitude","zero_plane_unit_magnitude_six_plane"}:
        unit=_learn_gcd(tuple(v for point in relative for v in point))
        relative=tuple(tuple(v//unit for v in point) for point in relative)
    if view_name == "zero_plane_unit_magnitude_six_plane":
        # Use the six resident Structuralizer views; this is not a generated 3-D
        # rotation table and does not claim physical calibration.
        views=[]
        for _plane_name, frame in PLANE_FRAMES:
            transformed=tuple(_frame_point_local(frame,point) for point in relative)
            views.append(tuple(tuple(p) for p in transformed))
        relative=min(views,key=_canonical_json)
    return [list(point) for point in relative]


def _learn_operation_rows(row: LearningEvidence, context: Mapping[str, Any]) -> tuple[dict[str,Any], ...]:
    rows=[]
    if row.source_kind == "self_feed":
        witness=context.get("witness",{})
        events=witness.get("events",[]) if isinstance(witness,Mapping) else []
        for event in events if isinstance(events,list) else []:
            if not isinstance(event,Mapping):
                continue
            op=event.get("operation",{})
            if not isinstance(op,Mapping):
                op={}
            # Retain declared operation semantics and exact selector fields;
            # event addresses and before/after address hashes are provenance,
            # not part of the comparison signature.
            rows.append({"kind":op.get("kind",event.get("kind")),
                         "axis":op.get("axis"),"direction":op.get("direction"),
                         "depth":op.get("depth"),"box_pos":op.get("box_pos"),
                         "side":op.get("side"),"steps":op.get("steps"),
                         "ticks":op.get("ticks"),"active":op.get("active"),
                         "cube":op.get("cube"),"radix":op.get("radix"),
                         "prime_lenses":op.get("prime_lenses"),
                         "rpm_momentum_ticks":op.get("rpm_momentum_ticks"),
                         "rpm_ordered_word":op.get("rpm_ordered_word"),
                         "rpm_phase":op.get("rpm_phase"),
                         "rpm_phase_modulus":op.get("rpm_phase_modulus"),
                         "rpm_rates":op.get("rpm_rates"),"rpm_reference":op.get("rpm_reference"),
                         "rpm_start_positions":op.get("rpm_start_positions"),
                         "rpm_target":op.get("rpm_target"),"rpm_winding":op.get("rpm_winding")})
    elif row.source_kind == "compound_case":
        candidate=context.get("candidate_definition",{})
        steps=candidate.get("steps",[]) if isinstance(candidate,Mapping) else []
        for step in steps if isinstance(steps,list) else []:
            if isinstance(step,Mapping):
                rows.append({"child_address":step.get("child_address"),
                             "implementation_sha256":step.get("implementation_sha256"),
                             "bindings":step.get("bindings"),"output_kind":step.get("output_kind"),
                             "success_checks":step.get("success_checks"),
                             "effect_scopes":step.get("effect_scopes")})
    return tuple(rows)


def _learn_scale_operation_rows(rows: Sequence[Mapping[str,Any]]) -> list[dict[str,Any]]:
    scale_keys={"steps","ticks","rpm_momentum_ticks"}
    values=[]
    for row in rows:
        for key in scale_keys:
            value=row.get(key)
            if type(value) is int and value:
                values.append(value)
    divisor=_learn_gcd(values)
    out=[]
    for row in rows:
        item=dict(row)
        for key in scale_keys:
            value=item.get(key)
            if type(value) is int:
                item[key]=value//divisor
        out.append(item)
    return out


def _learn_delta_rows(context: Mapping[str,Any], magnitude_normalized: bool, zero_plane: bool = True) -> Any:
    witness=context.get("witness",{})
    delta=witness.get("delta",{}) if isinstance(witness,Mapping) else {}
    changes=delta.get("changes",[]) if isinstance(delta,Mapping) else []
    rows=[]; numeric=[]
    for change in changes if isinstance(changes,list) else []:
        if not isinstance(change,Mapping):
            continue
        before,after=change.get("before"),change.get("after")
        if type(before) is int and type(after) is int:
            d=after-before; numeric.append(d)
            if zero_plane:
                rows.append({"path":change.get("path",[]),"before_type":"int","after_type":"int","delta":d})
            else:
                rows.append({"path":change.get("path",[]),"before_type":"int","after_type":"int",
                             "before":before,"after":after,"delta":d})
        else:
            rows.append({"path":change.get("path",[]),"before_type":type(before).__name__,
                         "after_type":type(after).__name__,"change_class":"changed" if before!=after else "same"})
    if magnitude_normalized and numeric:
        unit=_learn_gcd(numeric)
        for row in rows:
            if "delta" in row:
                row["delta"]//=unit
    return sorted(rows,key=_canonical_json)


def _learn_route_names(row: LearningEvidence, context: Mapping[str,Any]) -> tuple[str,...]:
    names=set()
    if row.source_kind == "compound_case":
        candidate=context.get("candidate_definition",{})
        if isinstance(candidate,Mapping):
            if candidate.get("key"): names.add("track:"+str(candidate["key"]))
            for step in candidate.get("steps",[]) if isinstance(candidate.get("steps",[]),list) else []:
                if isinstance(step,Mapping):
                    ref=step.get("child_ref") or step.get("child_address")
                    if ref: names.add("child:"+str(ref))
                    for binding in step.get("bindings",[]) if isinstance(step.get("bindings",[]),list) else []:
                        if isinstance(binding,(tuple,list)) and len(binding)==2:
                            names.add("port:"+str(binding[0]))
    if row.source_kind == "self_feed":
        witness=context.get("witness",{})
        for event in witness.get("events",[]) if isinstance(witness,Mapping) else []:
            if isinstance(event,Mapping):
                op=event.get("operation",{})
                if isinstance(op,Mapping):
                    if op.get("kind"): names.add("op:"+str(op["kind"]))
                    if op.get("axis"): names.add("axis:"+str(op["axis"]))
        for change in witness.get("delta",{}).get("changes",[]) if isinstance(witness,Mapping) and isinstance(witness.get("delta",{}),Mapping) else []:
            if isinstance(change,Mapping) and change.get("path"):
                path=change["path"]
                names.add("path:"+".".join(str(part) for part in path))
    return tuple(sorted(names))


def _learn_comparison_signature(row: LearningEvidence, view_name: str) -> str | None:
    context=json.loads(row.context_json)
    ops=_learn_operation_rows(row,context)
    points=_learn_points(context)
    if view_name == "exact":
        geometry=None if points is None else [list(p) for p in points]
        delta=_learn_delta_rows(context,False,zero_plane=False)
        operation_view=list(ops)
    elif view_name == "zero_plane":
        geometry=_learn_normalize_points(points,"zero_plane")
        delta=_learn_delta_rows(context,False,zero_plane=True)
        operation_view=list(ops)
    elif view_name == "zero_plane_unit_magnitude":
        geometry=_learn_normalize_points(points,"zero_plane_unit_magnitude")
        delta=_learn_delta_rows(context,True,zero_plane=True)
        operation_view=_learn_scale_operation_rows(ops)
    elif view_name == "zero_plane_unit_magnitude_six_plane":
        # Perspective comparisons need a point-bearing case. We do not fabricate
        # a point interpretation from generic scalar state paths.
        if points is None:
            return None
        geometry=_learn_normalize_points(points,view_name)
        delta=[]
        operation_view=_learn_scale_operation_rows(ops)
        # The six-plane view changes orientation; a child-address graph remains
        # authoritative and is not replaced by the projected geometry.
    else:
        raise ValueError("learning_comparison_view_unknown")
    body={"schema":"BC-LEARN-COMPARISON-SIGNATURE-1","source_kind":row.source_kind,
          "operations":operation_view,"geometry":geometry,"delta":delta,
          "comparison_view":view_name}
    return _compound_hash(body)[:32]


def build_learning_comparison_map(ledger: GlyphLearningLedger) -> LearningComparisonMap:
    """Build a sparse alias/view index; do not add rows to learning profiles/proposals."""
    if not isinstance(ledger,GlyphLearningLedger):
        raise TypeError("glyph_learning_ledger_required")
    view_names=("exact","zero_plane","zero_plane_unit_magnitude","zero_plane_unit_magnitude_six_plane")
    entries=[]; buckets: dict[tuple[str,str],list[LearningComparisonEntry]]={}
    unresolved=[]
    for row in sorted(ledger.evidence,key=lambda item:item.evidence_address):
        context=json.loads(row.context_json)
        signatures=[]
        for view_name in view_names:
            sig=_learn_comparison_signature(row,view_name)
            if sig is not None:
                signatures.append((view_name,sig))
                buckets.setdefault((view_name,sig),[]).append(None)  # filled after entry exists
        entry=LearningComparisonEntry(row.evidence_address,row.pattern_address,row.source_kind,
                                      _learn_route_names(row,context),tuple(signatures))
        entries.append(entry)
        for view_name,sig in signatures:
            bucket=buckets[(view_name,sig)]
            bucket[bucket.index(None)]=entry
        if not signatures:
            unresolved.append("no_comparison_view:"+row.evidence_address)
    classes=[]
    for (view_name,sig),members in sorted(buckets.items()):
        rows=tuple(sorted({m.evidence_address:m for m in members}.values(),key=lambda x:x.evidence_address))
        if len(rows)<2:
            continue
        evidence_ids=tuple(x.evidence_address for x in rows)
        pattern_ids=tuple(sorted({x.pattern_address for x in rows}))
        routes=tuple(sorted({name for x in rows for name in x.route_names}))
        body={"schema":"BC-LEARN-COMPARISON-CLASS-1","view":view_name,"signature":sig,
              "evidence":list(evidence_ids),"patterns":list(pattern_ids),"routes":list(routes)}
        classes.append(LearningComparisonClass(view_name,sig,evidence_ids,pattern_ids,routes,
                                               _compound_hash(body)[:32]))
    # Count potential deduplication once per evidence family, using its broadest
    # available lens. Self-feed deltas have no point cloud, so their broadest
    # view is unit magnitude; point-bearing compound cases may use six planes.
    view_priority={"exact":0,"zero_plane":1,"zero_plane_unit_magnitude":2,
                   "zero_plane_unit_magnitude_six_plane":3}
    kinds={entry.source_kind for entry in entries}
    best_view_by_kind={}
    for kind in kinds:
        available=[c.view_name for c in classes if any(
            next((e.source_kind for e in entries if e.evidence_address==eid),None)==kind
            for eid in c.evidence_addresses)]
        best_view_by_kind[kind]=max(available,key=lambda x:view_priority[x]) if available else None
    selected=[c for c in classes if c.view_name==best_view_by_kind.get(
        next((e.source_kind for e in entries if e.evidence_address in c.evidence_addresses),None))]
    redundancy=sum(max(0,len(c.evidence_addresses)-1) for c in selected)
    entry_tuple=tuple(sorted(entries,key=lambda x:x.evidence_address))
    class_tuple=tuple(sorted(classes,key=lambda x:(x.view_name,x.signature_address)))
    scale_routes=tuple((item.name,tuple(item.shape),item.capacity,item.shell,item.address_family)
                       for item in HARMONIC_STACKS)
    center_contract=("No fixed fractal-to-center count is encoded in this runtime. The address carries an actual levels tuple; "
        "depth-wave max_recursive_depth is an explicit probe cap from 0 through 64, with depth 0 denoting the root lattice "
        "and depth 1 denoting levels[0].lattice216. fractal3888 is the named 18x216 capacity (3888), not a recursion depth. "
        "A center must be declared by an address-bound zero-plane/center witness, not inferred from the capacity or the cap.")
    body={"schema":"BC-LEARNING-COMPARISON-MAP-1","ledger":ledger.address,
          "entries":[x.as_dict() for x in entry_tuple],"classes":[x.as_dict() for x in class_tuple],
          "scale_routes":[{"name":n,"shape":list(sh),"capacity":cap,"shell":shell,"address_family":family}
                          for n,sh,cap,shell,family in scale_routes],
          "center_depth_contract":center_contract,
          "redundancy":redundancy,"unresolved":sorted(unresolved)}
    return LearningComparisonMap("BC-LEARNING-COMPARISON-MAP-1",ledger.address,len(ledger.evidence),
                                 entry_tuple,class_tuple,scale_routes,center_contract,redundancy,
                                 tuple(sorted(unresolved)),_compound_hash(body)[:32])


def reopen_learning_comparison_map(ledger: GlyphLearningLedger, comparison_map: LearningComparisonMap) -> dict[str,Any]:
    if not isinstance(comparison_map,LearningComparisonMap):
        return {"schema":"BC-LEARNING-COMPARISON-REOPEN-1","pass":False,"reason":"comparison_map_required"}
    try:
        rebuilt=build_learning_comparison_map(ledger)
        passed=rebuilt==comparison_map and comparison_map.ledger_address==ledger.address
        return {"schema":"BC-LEARNING-COMPARISON-REOPEN-1","pass":passed,
                "ledger_address":ledger.address,"map_address":comparison_map.map_address,
                "rebuilt_map_address":rebuilt.map_address,"evidence_count":rebuilt.evidence_count,
                "comparison_class_count":len(rebuilt.classes),"persisted":False}
    except (TypeError,ValueError,KeyError) as exc:
        return {"schema":"BC-LEARNING-COMPARISON-REOPEN-1","pass":False,
                "reason":f"comparison_rebuild_failed:{type(exc).__name__}:{exc}"}


def export_learning_comparison_map(comparison_map: LearningComparisonMap) -> dict[str,Any]:
    if not isinstance(comparison_map,LearningComparisonMap):
        raise TypeError("learning_comparison_map_required")
    return comparison_map.as_dict()


REGISTRY.register("build_learning_comparison_map",build_learning_comparison_map,"pure")
REGISTRY.register("reopen_learning_comparison_map",reopen_learning_comparison_map,"pure")
REGISTRY.register("export_learning_comparison_map",export_learning_comparison_map,"pure")
for _compare_spec in (
    GlyphSpec.make("BC.LEARN.COMPARE","build_learning_comparison_map",("ledger",),(),
        {"ledger":"glyph_learning_ledger"},"pure",
        "sparse exact/zero-plane/unit-magnitude/six-plane match index; no profile or proposal expansion"),
    GlyphSpec.make("BC.LEARN.COMPARE.REOPEN","reopen_learning_comparison_map",("ledger","comparison_map"),(),
        {"ledger":"glyph_learning_ledger","comparison_map":"learning_comparison_map"},"pure",
        "rebuild name/view map from existing evidence; address-bound; no persistence"),
):
    GLYPH_CATALOG.register(_compare_spec)



# ---------------------------------------------------------------------------
# Address-native one-hot compactification waves and wave glyphs.
# One-hot occupancy is the comparison substrate; coordinates and zero-plane
# projections are derived lenses. Each lens keeps its omitted-coordinate and
# boundary residues. Box-216 and cube-216 remain distinct typed families.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SparseOneHotWord:
    family: str
    width: int
    active_slots: tuple[int, ...]
    mode: str = "one_hot"       # one_hot for a state; multi_hot for a wave occupancy set
    presence: str = "present"   # present, all_off, or absent

    def __post_init__(self) -> None:
        if not isinstance(self.family, str) or not self.family:
            raise ValueError("onehot_family_required")
        if type(self.width) is not int or self.width < 1:
            raise ValueError("onehot_width_must_be_positive_integer")
        if self.mode not in {"one_hot", "multi_hot"}:
            raise ValueError("onehot_mode_invalid")
        if self.presence not in {"present", "all_off", "absent"}:
            raise ValueError("onehot_presence_invalid")
        if tuple(sorted(set(self.active_slots))) != self.active_slots:
            raise ValueError("onehot_slots_must_be_sorted_unique")
        if any(type(v) is not int or v not in range(self.width) for v in self.active_slots):
            raise ValueError("onehot_slot_out_of_range")
        if self.mode == "one_hot" and len(self.active_slots) > 1:
            raise ValueError("onehot_word_has_multiple_active_slots")
        if self.presence != "present" and self.active_slots:
            raise ValueError("absent_or_all_off_word_cannot_have_active_slots")
        if self.presence == "present" and not self.active_slots:
            raise ValueError("present_onehot_word_requires_active_slot")

    @property
    def word_address(self) -> str:
        return _sha256_text(_canonical_json(self.as_dict(include_address=False)))[:24]

    def as_dict(self, include_address: bool = True) -> dict[str, Any]:
        body = {"schema":"BC-SPARSE-ONEHOT-WORD-1", "family":self.family, "width":self.width,
                "active_slots":list(self.active_slots), "mode":self.mode, "presence":self.presence,
                "active_count":len(self.active_slots), "is_single_onehot":self.mode=="one_hot" and len(self.active_slots)==1,
                "is_all_off":self.presence=="all_off", "is_absent":self.presence=="absent"}
        if include_address:
            body["word_address"] = self.word_address
        return body


@dataclass(frozen=True)
class AddressOneHotFrame:
    frame_name: str
    frame_kind: str
    depth: int
    dimension_rank: int
    source_address_id: str
    aperture_address: str
    path: tuple[str | int, ...]
    words: tuple[SparseOneHotWord, ...]
    address_factors: tuple[tuple[str, Any], ...]
    frame_address: str

    def _body(self) -> dict[str, Any]:
        return {"schema":"BC-ADDRESS-ONEHOT-FRAME-1", "frame_name":self.frame_name,
                "frame_kind":self.frame_kind, "depth":self.depth, "dimension_rank":self.dimension_rank,
                "source_address_id":self.source_address_id, "aperture_address":self.aperture_address,
                "path":list(self.path), "words":[w.as_dict() for w in self.words],
                "address_factors":[[k,v] for k,v in self.address_factors]}

    def as_dict(self) -> dict[str, Any]:
        body=self._body(); body["frame_address"]=self.frame_address; return body


def _onehot_word(family: str, width: int, slot: int | None, *, absent: bool=False) -> SparseOneHotWord:
    if absent:
        return SparseOneHotWord(family,width,(),"one_hot","absent")
    if slot is None:
        return SparseOneHotWord(family,width,(),"one_hot","all_off")
    if type(slot) is not int or slot not in range(width):
        raise ValueError("onehot_source_slot_out_of_range")
    return SparseOneHotWord(family,width,(slot,),"one_hot","present")


def _multi_hot_word(family: str, width: int, slots: Sequence[int]) -> SparseOneHotWord:
    clean=tuple(sorted(set(slots)))
    return SparseOneHotWord(family,width,clean,"multi_hot","present" if clean else "all_off")


def _make_address_onehot_frame(root_id: str, name: str, kind: str, depth: int, rank: int,
                               aperture: str, path: Sequence[str | int], words: Sequence[SparseOneHotWord],
                               factors: Mapping[str, Any]) -> AddressOneHotFrame:
    tmp=AddressOneHotFrame(name,kind,depth,rank,root_id,aperture,tuple(path),tuple(words),
                           tuple(sorted(factors.items())),"")
    fid=_sha256_text(_canonical_json(tmp._body()))[:24]
    return AddressOneHotFrame(name,kind,depth,rank,root_id,aperture,tuple(path),tuple(words),
                              tuple(sorted(factors.items())),fid)


def _address_onehot_frames(address: BCFloorAddress) -> tuple[AddressOneHotFrame, ...]:
    out=[]
    octant_slot=address.surface.cube
    octant_word=_onehot_word("octant8",8,octant_slot)
    for axis_index,page in enumerate(address.surface.pages):
        page_state_slot=None if page.state==9 else page.state
        words=(octant_word,
               _onehot_word("axis_page3",3,axis_index),
               _onehot_word("box_position9",9,page.box),
               _onehot_word("box_local_state9",9,page_state_slot))
        out.append(_make_address_onehot_frame(address.address_id,f"surface.{AXES[axis_index]}",
            "floor_page_state",0,2,BOX_APERTURE_216.address_id,("surface","pages",axis_index),words,
            {"axis":AXES[axis_index],"circle_addr":page.circle_addr,"box_index":page.box,
             "local_state_index":page.state,"all_off":page.state==9,"aperture_family":"box216"}))
    if address.lattice216 is not None:
        lat=address.lattice216
        words=(_onehot_word("cube_state216",216,lat.physical_index6),
               _onehot_word("lane8",8,lat.lane8))
        out.append(_make_address_onehot_frame(address.address_id,"root.lattice216","cube_lattice_state",0,3,
            CUBE_APERTURE_216.address_id,("lattice216",),words,
            {"lane8_address":lat.lane8,"group27_address":lat.group27,
             "ternary27_address":tuple(lat.ternary27),"physical_coord6":tuple(lat.physical_coord6),
             "physical_index6":lat.physical_index6,"aperture_family":"cube216",
             "box_cube_mapping_inferred":False}))
    for index,level in enumerate(address.levels):
        slot=None if level.box_pos==BOX_EMPTY else level.box_pos
        side=level.side
        words=[_onehot_word("recursive_box_slot9",9,slot),
               _onehot_word("recursive_side2",2,side,absent=side is None)]
        factors={"box_pos":level.box_pos,"side":side,"active":level.active,"resolved":level.resolved,
                 "rotation_active":level.rotation_active,"rotation_cube":level.rotation_cube,
                 "aperture_families_distinct":True,"box_aperture_address":BOX_APERTURE_216.address_id,
                 "cube_aperture_address":CUBE_APERTURE_216.address_id}
        if level.lattice216 is not None:
            lat=level.lattice216
            words.extend((_onehot_word("cube_state216",216,lat.physical_index6),
                          _onehot_word("lane8",8,lat.lane8)))
            factors.update({"group27_address":lat.group27,"ternary27_address":tuple(lat.ternary27),
                            "physical_coord6":tuple(lat.physical_coord6),"physical_index6":lat.physical_index6})
        else:
            words.extend((_onehot_word("cube_state216",216,None,absent=True),
                          _onehot_word("lane8",8,None,absent=True)))
            factors.update({"group27_address":None,"ternary27_address":None,"physical_coord6":None,
                            "physical_index6":None})
        out.append(_make_address_onehot_frame(address.address_id,f"levels.{index}","recursive_box_cube_frame",
            index+1,3 if level.lattice216 is not None else 2,
            CUBE_APERTURE_216.address_id if level.lattice216 is not None else BOX_APERTURE_216.address_id,
            ("levels",index),words,factors))
    return tuple(out)


@dataclass(frozen=True)
class WaveProjection:
    rank: int
    wave_distance: int
    domain_width: int
    active_slots: tuple[int, ...]
    multiplicities: tuple[tuple[int, int], ...]
    omitted_fibres: tuple[tuple[int, tuple[tuple[tuple[int, ...], int], ...]], ...]
    chosen_frame: str
    signature_address: str
    projected_claim: str = "occupancy signature only; omitted coordinates and fibre multiplicities remain residuals"

    def as_dict(self) -> dict[str, Any]:
        return {"schema":"BC-WAVE-ONEHOT-PROJECTION-1","rank":self.rank,"wave_distance":self.wave_distance,
                "domain_width":self.domain_width,"active_slots":list(self.active_slots),
                "multiplicities":[[s,n] for s,n in self.multiplicities],
                "omitted_fibres":[[slot,[[list(coords),count] for coords,count in rows]] for slot,rows in self.omitted_fibres],
                "collision_count":sum(max(0,count-1) for _,count in self.multiplicities),
                "chosen_frame":self.chosen_frame,"signature_address":self.signature_address,
                "projected_claim":self.projected_claim}


def _compact_signed_coordinate(coords: Sequence[int], rank: int) -> int:
    slot=0
    for value in coords[:rank]:
        if type(value) is not int or value not in range(-5,6):
            raise ValueError("wave_relative_coordinate_outside_compactification_domain")
        slot=slot*11+(value+5)
    return slot


def _project_wave_shell(nodes: Sequence[DepthWaveNode], seed: Lattice216, rank: int,
                        depth: int, distance: int) -> WaveProjection:
    if rank not in (1,2,3): raise ValueError("wave_projection_rank_must_be_1_to_3")
    seed_coord=seed.physical_coord6
    deltas=[tuple(p[i]-seed_coord[i] for i in range(3)) for p in (n.lattice.physical_coord6 for n in nodes)]
    choices=[]
    for plane_name,frame in PLANE_FRAMES:
        rows=[]
        for delta in deltas:
            transformed=tuple(delta[frame.perm[i]]*frame.sign[i] for i in range(3))
            slot=_compact_signed_coordinate(transformed,rank)
            omitted=tuple(transformed[rank:])
            rows.append((slot,omitted))
        counts={}
        omitted_counts={}
        for slot,omitted in rows:
            counts[slot]=counts.get(slot,0)+1
            omitted_counts.setdefault(slot,{})[omitted]=omitted_counts.setdefault(slot,{}).get(omitted,0)+1
        active=tuple(sorted(counts))
        mult=tuple(sorted(counts.items()))
        fibres=tuple((slot,tuple(sorted(((coords,count) for coords,count in om.items()),key=lambda x:x[0])))
                     for slot,om in sorted(omitted_counts.items()))
        # Canonical orientation is selected by sparse occupancy first; residual detail breaks ties.
        key=(_canonical_json(active),_canonical_json(fibres),plane_name)
        choices.append((key,active,mult,fibres,plane_name))
    _,active,mult,fibres,plane_name=min(choices,key=lambda row:row[0])
    width=11**rank
    sig_body={"schema":"BC-WAVE-ONEHOT-SIGNATURE-1","rank":rank,"wave_distance":distance,
              "domain_width":width,"active_slots":list(active),"encoding":"sparse onehot occupancy"}
    sig=_sha256_text(_canonical_json(sig_body))[:24]
    return WaveProjection(rank,distance,width,active,mult,fibres,plane_name,sig)


@dataclass(frozen=True)
class AddressWaveGlyph:
    short_name: str
    label: str
    depth: int
    child_address_id: str
    wave_distance: int
    node_state_addresses: tuple[str, ...]
    native_occupancy: SparseOneHotWord
    projections: tuple[WaveProjection, ...]
    frontier_addresses: tuple[str, ...]
    residuals: tuple[str, ...]
    wave_glyph_address: str

    def _body(self) -> dict[str, Any]:
        return {"schema":"BC-ADDRESS-WAVE-GLYPH-1","short_name":self.short_name,"label":self.label,
                "depth":self.depth,"child_address_id":self.child_address_id,"wave_distance":self.wave_distance,
                "node_state_addresses":list(self.node_state_addresses),
                "native_occupancy":self.native_occupancy.as_dict(),
                "projections":[x.as_dict() for x in self.projections],
                "frontier_addresses":list(self.frontier_addresses),"residuals":list(self.residuals),
                "claim_boundary":"address-bound reusable pattern record; not an executable glyph or global centre claim"}

    def as_dict(self) -> dict[str, Any]:
        body=self._body(); body["wave_glyph_address"]=self.wave_glyph_address; return body


@dataclass(frozen=True)
class WaveFrontierResidual:
    root_address_id: str
    child_address_id: str
    depth: int
    from_state_address_id: str
    target_state_address_id: str
    target_physical_index6: int
    target_coord6: tuple[int,int,int]
    axis: str
    direction: int
    next_wave_distance: int
    target_relative_coord6: tuple[int,int,int] | None
    residual_kind: str = "wave_frontier_unopened_state"

    def as_dict(self) -> dict[str, Any]:
        return {"schema":"BC-WAVE-FRONTIER-RESIDUAL-1","root_address_id":self.root_address_id,
                "child_address_id":self.child_address_id,"depth":self.depth,
                "from_state_address_id":self.from_state_address_id,"target_state_address_id":self.target_state_address_id,
                "target_physical_index6":self.target_physical_index6,"target_coord6":list(self.target_coord6),
                "axis":self.axis,"direction":self.direction,"next_wave_distance":self.next_wave_distance,
                "target_relative_coord6":None if self.target_relative_coord6 is None else list(self.target_relative_coord6),
                "residual_kind":self.residual_kind}


@dataclass(frozen=True)
class AddressOneHotWave:
    schema: str
    source_address_id: str
    cone_address: str
    frames: tuple[AddressOneHotFrame, ...]
    wave_glyphs: tuple[AddressWaveGlyph, ...]
    frontier_residuals: tuple[WaveFrontierResidual, ...]
    unresolved: tuple[str, ...]
    seed_semantics: str
    wave_address: str

    def _body(self) -> dict[str, Any]:
        return {"schema":self.schema,"source_address_id":self.source_address_id,"cone_address":self.cone_address,
                "frames":[x.as_dict() for x in self.frames],"wave_glyphs":[x.as_dict() for x in self.wave_glyphs],
                "frontier_residuals":[x.as_dict() for x in self.frontier_residuals],"unresolved":list(self.unresolved),
                "seed_semantics":self.seed_semantics,
                "aperture_contract":{"box216":BOX_APERTURE_216.address_id,"cube216":CUBE_APERTURE_216.address_id,
                    "equal_cardinality_is_not_state_equivalence":True},
                "profile_or_proposal_rows_added":0,"glyph_admission":False,"persistent_save":False}

    def as_dict(self) -> dict[str, Any]:
        body=self._body(); body["wave_address"]=self.wave_address; return body


def build_address_onehot_wave(address: BCFloorAddress, cone: DepthWaveCone) -> AddressOneHotWave:
    """Compactify a reopened addressed depth-wave using sparse one-hot occupancy.

    The seed is local to each selected lattice payload. A seed is not asserted to
    be the global fractal centre. Every dimensional projection retains omitted-axis
    fibres and cone-frontier residuals for exact later inspection.
    """
    if not isinstance(address,BCFloorAddress) or not isinstance(cone,DepthWaveCone):
        raise TypeError("full_address_and_depth_wave_cone_required")
    if cone.root_address_id != address.address_id:
        raise ValueError("onehot_wave_cone_root_mismatch")
    reopen=reopen_depth_wave_cone(address,cone)
    if not reopen.pass_all:
        raise ValueError("onehot_wave_requires_reopened_depth_cone")
    frames=_address_onehot_frames(address)
    seed_by_child={}
    if cone.include_root_lattice and address.lattice216 is not None:
        seed_by_child["ROOT.LATTICE216:"+address.address_id]=address.lattice216
    for child in cone.child_addresses:
        if child.parent_address_id!=address.address_id:
            raise ValueError("onehot_wave_child_parent_mismatch")
        level=address.levels[child.level_index]
        if level.lattice216 is not None:
            seed_by_child[child.address_id]=level.lattice216
    grouped={}
    for node in cone.nodes:
        if node.child_address_id not in seed_by_child:
            raise ValueError("onehot_wave_node_seed_unresolved")
        grouped.setdefault((node.depth,node.child_address_id,node.wave_distance),[]).append(node)
    frontier_by_group={}
    frontier_residuals=[]
    for item in cone.frontier:
        # Relative target offsets are computed from the addressed seed; absolute node ids remain provenance.
        seed=seed_by_child.get(item.child_address_id)
        relative=None if seed is None else tuple(item.target_coord6[i]-seed.physical_coord6[i] for i in range(3))
        frontier_residuals.append(WaveFrontierResidual(item.root_address_id,item.child_address_id,item.depth,
            item.from_state_address_id,item.target_state_address_id,item.target_physical_index6,item.target_coord6,
            item.axis,item.direction,item.next_wave_distance,relative))
        frontier_by_group.setdefault((item.depth,item.child_address_id,item.next_wave_distance-1),[]).append(
            _sha256_text(_canonical_json(item.as_dict()))[:24])
    wave_glyphs=[]
    for (depth,child_id,distance),nodes in sorted(grouped.items()):
        nodes=sorted(nodes,key=lambda n:(n.lattice.physical_index6,n.state_address_id))
        seed=seed_by_child[child_id]
        native_slots=tuple(sorted({n.lattice.physical_index6 for n in nodes}))
        native=_multi_hot_word("cube_state216_occupancy",216,native_slots)
        projections=tuple(_project_wave_shell(nodes,seed,rank,depth,distance) for rank in (1,2,3))
        front=tuple(sorted(frontier_by_group.get((depth,child_id,distance),())))
        residuals=[]
        for projection in projections:
            if projection.rank<3:
                collision=sum(max(0,count-1) for _,count in projection.multiplicities)
                residuals.append(f"dimension_compactification_rank_{projection.rank}_omits_{3-projection.rank}_axes")
                if collision:
                    residuals.append(f"rank_{projection.rank}_projection_has_{collision}_collapsed_fibre_members")
        if front:
            residuals.append(f"{len(front)}_unopened_frontier_transitions_after_shell_{distance}")
        if cone.unresolved:
            residuals.extend("cone:"+x for x in cone.unresolved)
        body={"schema":"BC-ADDRESS-WAVE-GLYPH-1","root":address.address_id,"cone":cone.cone_address,
              "depth":depth,"child":child_id,"distance":distance,"native":native.as_dict(),
              "nodes":[n.state_address_id for n in nodes],"projections":[p.as_dict() for p in projections],
              "frontier":list(front),"residuals":sorted(set(residuals))}
        gid=_sha256_text(_canonical_json(body))[:32]
        short="wg."+gid[:8]
        wave_glyphs.append(AddressWaveGlyph(short,f"depth {depth} · wave {distance} · cube216",depth,child_id,distance,
             tuple(n.state_address_id for n in nodes),native,projections,front,tuple(sorted(set(residuals))),gid))
    frontier_residuals=sorted(frontier_residuals,key=lambda row:_canonical_json(row.as_dict()))
    unresolved=tuple(sorted(set(cone.unresolved)))
    body={"schema":"BC-ADDRESS-ONEHOT-WAVE-1","source":address.address_id,"cone":cone.cone_address,
          "frames":[x.as_dict() for x in frames],"wave_glyphs":[x.as_dict() for x in wave_glyphs],
          "frontier_residuals":[x.as_dict() for x in frontier_residuals],"unresolved":list(unresolved),
          "seed_semantics":"each opened lattice seed is address-bound; not asserted to be the global fractal centre",
          "box_cube_same_cardinality_is_not_equivalence":True}
    wid=_sha256_text(_canonical_json(body))[:32]
    return AddressOneHotWave("BC-ADDRESS-ONEHOT-WAVE-1",address.address_id,cone.cone_address,frames,
                             tuple(wave_glyphs),tuple(frontier_residuals),unresolved,
                             "each opened lattice seed is address-bound; not asserted to be the global fractal centre",wid)


def reopen_address_onehot_wave(address: BCFloorAddress, cone: DepthWaveCone,
                               wave: AddressOneHotWave) -> dict[str,Any]:
    if not isinstance(wave,AddressOneHotWave):
        return {"schema":"BC-ADDRESS-ONEHOT-WAVE-REOPEN-1","pass":False,"reason":"address_onehot_wave_required"}
    try:
        rebuilt=build_address_onehot_wave(address,cone)
        passed=rebuilt==wave and wave.source_address_id==address.address_id and wave.cone_address==cone.cone_address
        return {"schema":"BC-ADDRESS-ONEHOT-WAVE-REOPEN-1","pass":passed,"wave_address":wave.wave_address,
                "rebuilt_wave_address":rebuilt.wave_address,"frame_count":len(rebuilt.frames),
                "wave_glyph_count":len(rebuilt.wave_glyphs),"frontier_residual_count":len(rebuilt.frontier_residuals),
                "profile_or_proposal_rows_added":0,"glyph_admission":False,"persistent_save":False}
    except (TypeError,ValueError,KeyError) as exc:
        return {"schema":"BC-ADDRESS-ONEHOT-WAVE-REOPEN-1","pass":False,
                "reason":f"onehot_wave_rebuild_failed:{type(exc).__name__}:{exc}"}


@dataclass(frozen=True)
class WaveGlyphMatchEntry:
    wave_address: str
    wave_glyph_address: str
    short_name: str
    root_address_id: str
    cone_address: str
    depth: int
    child_address_id: str
    wave_distance: int
    rank: int
    signature_address: str
    active_slots: tuple[int, ...]
    multiplicities: tuple[tuple[int,int], ...]
    residuals: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"wave_address":self.wave_address,"wave_glyph_address":self.wave_glyph_address,
                "short_name":self.short_name,"root_address_id":self.root_address_id,"cone_address":self.cone_address,
                "depth":self.depth,"child_address_id":self.child_address_id,"wave_distance":self.wave_distance,
                "projection_rank":self.rank,"signature_address":self.signature_address,
                "active_slots":list(self.active_slots),"multiplicities":[[s,n] for s,n in self.multiplicities],
                "residuals":list(self.residuals)}


@dataclass(frozen=True)
class WaveGlyphMatchClass:
    signature_address: str
    rank: int
    wave_distance: int
    member_addresses: tuple[str, ...]
    roots: tuple[str, ...]
    depths: tuple[int, ...]
    residual_variants: int
    class_address: str
    claim_boundary: str = "shared sparse one-hot projection; not equality of omitted dimensions or permission to merge execution"

    def as_dict(self) -> dict[str, Any]:
        return {"signature_address":self.signature_address,"projection_rank":self.rank,
                "wave_distance":self.wave_distance,"member_addresses":list(self.member_addresses),
                "roots":list(self.roots),"depths":list(self.depths),"residual_variants":self.residual_variants,
                "class_address":self.class_address,"claim_boundary":self.claim_boundary}


@dataclass(frozen=True)
class WaveDimensionalLink:
    parent_wave_glyph_address: str
    source_wave_address: str
    depth: int
    wave_distance: int
    lower_rank: int
    higher_rank: int
    lower_signature: str
    higher_signature: str
    lower_collision_count: int
    higher_collision_count: int
    omitted_axis_residuals: tuple[str, ...]
    lift_to_rank3_required_for_full_3d_identity: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {"parent_wave_glyph_address":self.parent_wave_glyph_address,"source_wave_address":self.source_wave_address,
                "depth":self.depth,"wave_distance":self.wave_distance,"lower_rank":self.lower_rank,
                "higher_rank":self.higher_rank,"lower_signature":self.lower_signature,
                "higher_signature":self.higher_signature,"lower_collision_count":self.lower_collision_count,
                "higher_collision_count":self.higher_collision_count,"omitted_axis_residuals":list(self.omitted_axis_residuals),
                "lift_to_rank3_required_for_full_3d_identity":self.lift_to_rank3_required_for_full_3d_identity}


@dataclass(frozen=True)
class AddressFrameMatchEntry:
    source_wave_address: str
    root_address_id: str
    frame_address: str
    frame_name: str
    frame_kind: str
    path: tuple[str | int, ...]
    depth: int
    dimension_rank: int
    aperture_address: str
    word_family: str
    word_width: int
    word_mode: str
    presence: str
    active_slots: tuple[int, ...]
    word_address: str
    signature_address: str

    def as_dict(self) -> dict[str, Any]:
        return {"source_wave_address":self.source_wave_address,"root_address_id":self.root_address_id,
                "frame_address":self.frame_address,"frame_name":self.frame_name,"frame_kind":self.frame_kind,
                "path":list(self.path),"depth":self.depth,"dimension_rank":self.dimension_rank,
                "aperture_address":self.aperture_address,"word_family":self.word_family,"word_width":self.word_width,
                "word_mode":self.word_mode,"presence":self.presence,"active_slots":list(self.active_slots),
                "word_address":self.word_address,"signature_address":self.signature_address}


@dataclass(frozen=True)
class AddressFrameMatchClass:
    signature_address: str
    word_family: str
    word_width: int
    word_mode: str
    presence: str
    active_slots: tuple[int, ...]
    member_word_addresses: tuple[str, ...]
    frame_names: tuple[str, ...]
    roots: tuple[str, ...]
    depths: tuple[int, ...]
    class_address: str
    claim_boundary: str = "same typed one-hot word signature only; distinct aperture families are never equated by cardinality"

    def as_dict(self) -> dict[str, Any]:
        return {"signature_address":self.signature_address,"word_family":self.word_family,
                "word_width":self.word_width,"word_mode":self.word_mode,"presence":self.presence,
                "active_slots":list(self.active_slots),"member_word_addresses":list(self.member_word_addresses),
                "frame_names":list(self.frame_names),"roots":list(self.roots),"depths":list(self.depths),
                "class_address":self.class_address,"claim_boundary":self.claim_boundary}


@dataclass(frozen=True)
class WaveGlyphComparisonMap:
    schema: str
    source_wave_addresses: tuple[str, ...]
    entries: tuple[WaveGlyphMatchEntry, ...]
    classes: tuple[WaveGlyphMatchClass, ...]
    dimensional_links: tuple[WaveDimensionalLink, ...]
    frame_entries: tuple[AddressFrameMatchEntry, ...]
    frame_classes: tuple[AddressFrameMatchClass, ...]
    unmatched_wave_glyph_addresses: tuple[str, ...]
    unmatched_frame_word_addresses: tuple[str, ...]
    map_address: str

    def _body(self) -> dict[str, Any]:
        return {"schema":self.schema,"source_wave_addresses":list(self.source_wave_addresses),
                "entries":[x.as_dict() for x in self.entries],"classes":[x.as_dict() for x in self.classes],
                "dimensional_links":[x.as_dict() for x in self.dimensional_links],
                "frame_entries":[x.as_dict() for x in self.frame_entries],
                "frame_classes":[x.as_dict() for x in self.frame_classes],
                "unmatched_wave_glyph_addresses":list(self.unmatched_wave_glyph_addresses),
                "unmatched_frame_word_addresses":list(self.unmatched_frame_word_addresses),
                "policy":"projection occupancy can pair across depths and dimension-ranks; exact typed frame words are independently indexed; omitted axes, multiplicities, source addresses and frontiers remain evidence residues; no glyph admission"}

    def as_dict(self) -> dict[str, Any]:
        body=self._body();body["map_address"]=self.map_address;return body


def compare_address_onehot_waves(waves: Sequence[AddressOneHotWave]) -> WaveGlyphComparisonMap:
    if not isinstance(waves,(tuple,list)) or not waves or any(not isinstance(w,AddressOneHotWave) for w in waves):
        raise TypeError("nonempty_address_onehot_wave_sequence_required")
    wave_rows=tuple(sorted(waves,key=lambda w:w.wave_address))
    entries=[]; buckets={}; all_glyphs=[]; dimensional_links=[]
    wave_by_addr={w.wave_address:w for w in wave_rows}
    for wave in wave_rows:
        for glyph in wave.wave_glyphs:
            all_glyphs.append(glyph.wave_glyph_address)
            projected={p.rank:p for p in glyph.projections}
            residual_variants=[]
            for proj in glyph.projections:
                residuals=tuple(sorted(glyph.residuals))
                entry=WaveGlyphMatchEntry(wave.wave_address,glyph.wave_glyph_address,glyph.short_name,
                    wave.source_address_id,wave.cone_address,glyph.depth,glyph.child_address_id,glyph.wave_distance,
                    proj.rank,proj.signature_address,proj.active_slots,proj.multiplicities,residuals)
                entries.append(entry)
                buckets.setdefault((proj.rank,glyph.wave_distance,proj.signature_address),[]).append(entry)
            if 1 in projected and 2 in projected:
                dimensional_links.append(WaveDimensionalLink(glyph.wave_glyph_address,wave.wave_address,glyph.depth,
                    glyph.wave_distance,1,2,projected[1].signature_address,projected[2].signature_address,
                    sum(max(0,n-1) for _,n in projected[1].multiplicities),
                    sum(max(0,n-1) for _,n in projected[2].multiplicities),tuple(glyph.residuals),True))
            if 2 in projected and 3 in projected:
                dimensional_links.append(WaveDimensionalLink(glyph.wave_glyph_address,wave.wave_address,glyph.depth,
                    glyph.wave_distance,2,3,projected[2].signature_address,projected[3].signature_address,
                    sum(max(0,n-1) for _,n in projected[2].multiplicities),
                    sum(max(0,n-1) for _,n in projected[3].multiplicities),tuple(glyph.residuals),True))
    classes=[]
    for (rank,distance,sig),members in sorted(buckets.items()):
        # Repetition means either another source/root or another addressed depth/child.
        member_map={m.wave_glyph_address+":"+m.signature_address:m for m in members}
        rows=tuple(sorted(member_map.values(),key=lambda x:(x.root_address_id,x.depth,x.child_address_id,x.wave_distance)))
        distinct_origins={(m.root_address_id,m.depth,m.child_address_id) for m in rows}
        if len(distinct_origins)<2: continue
        residual_keys={_canonical_json(m.residuals) for m in rows}
        body={"schema":"BC-WAVE-GLYPH-MATCH-CLASS-1","signature":sig,"rank":rank,"distance":distance,
              "members":[m.wave_glyph_address for m in rows],"roots":sorted({m.root_address_id for m in rows}),
              "depths":sorted({m.depth for m in rows}),"residual_variants":len(residual_keys)}
        classes.append(WaveGlyphMatchClass(sig,rank,distance,tuple(m.wave_glyph_address for m in rows),
            tuple(sorted({m.root_address_id for m in rows})),tuple(sorted({m.depth for m in rows})),
            len(residual_keys),_sha256_text(_canonical_json(body))[:32]))
    matched={a for c in classes for a in c.member_addresses}
    unmatched=tuple(sorted(set(all_glyphs)-matched))
    entries_tuple=tuple(sorted(entries,key=lambda e:(e.wave_address,e.wave_glyph_address,e.rank)))
    classes_tuple=tuple(sorted(classes,key=lambda c:(c.rank,c.wave_distance,c.signature_address)))
    links_tuple=tuple(sorted(dimensional_links,key=lambda row:_canonical_json(row.as_dict())))

    # Exact frame-word indexing compares the actual one-hot workload at each
    # addressed structural level. Different word/aperture families remain typed.
    frame_entries=[]; frame_buckets={}
    for wave in wave_rows:
        for frame in wave.frames:
            for word in frame.words:
                sig_body={"schema":"BC-ADDRESS-FRAME-ONEHOT-SIGNATURE-1","family":word.family,
                          "width":word.width,"mode":word.mode,"presence":word.presence,
                          "active_slots":list(word.active_slots)}
                sig=_sha256_text(_canonical_json(sig_body))[:24]
                entry=AddressFrameMatchEntry(wave.wave_address,wave.source_address_id,frame.frame_address,
                    frame.frame_name,frame.frame_kind,frame.path,frame.depth,frame.dimension_rank,frame.aperture_address,
                    word.family,word.width,word.mode,word.presence,word.active_slots,word.word_address,sig)
                frame_entries.append(entry);frame_buckets.setdefault(sig,[]).append(entry)
    frame_classes=[]
    for sig,members in sorted(frame_buckets.items()):
        distinct={(m.root_address_id,m.frame_address,m.word_address) for m in members}
        if len(distinct)<2: continue
        rows=tuple(sorted(members,key=lambda m:(m.root_address_id,m.depth,m.frame_name,m.word_address)))
        first=rows[0]
        member_addresses=tuple(sorted({m.frame_address+":"+m.word_address for m in rows}))
        frame_names=tuple(sorted({m.frame_name for m in rows}))
        roots=tuple(sorted({m.root_address_id for m in rows}))
        depths=tuple(sorted({m.depth for m in rows}))
        body={"schema":"BC-ADDRESS-FRAME-ONEHOT-CLASS-1","signature":sig,
              "members":list(member_addresses),"frames":list(frame_names),"roots":list(roots),"depths":list(depths)}
        frame_classes.append(AddressFrameMatchClass(sig,first.word_family,first.word_width,first.word_mode,
            first.presence,first.active_slots,member_addresses,frame_names,roots,depths,
            _sha256_text(_canonical_json(body))[:32]))
    frame_entries_tuple=tuple(sorted(frame_entries,key=lambda e:(e.source_wave_address,e.depth,e.frame_name,e.word_family,e.word_address)))
    frame_classes_tuple=tuple(sorted(frame_classes,key=lambda c:(c.word_family,c.word_width,c.signature_address)))
    matched_frame_words={a for c in frame_classes for a in c.member_word_addresses}
    all_frame_words={e.frame_address+":"+e.word_address for e in frame_entries_tuple}
    unmatched_frame_words=tuple(sorted(all_frame_words-matched_frame_words))
    source_ids=tuple(w.wave_address for w in wave_rows)
    body={"schema":"BC-WAVE-GLYPH-COMPARISON-MAP-2","sources":list(source_ids),
          "entries":[e.as_dict() for e in entries_tuple],"classes":[c.as_dict() for c in classes_tuple],
          "dimensional_links":[x.as_dict() for x in links_tuple],"frame_entries":[e.as_dict() for e in frame_entries_tuple],
          "frame_classes":[c.as_dict() for c in frame_classes_tuple],"unmatched":list(unmatched),
          "unmatched_frame_words":list(unmatched_frame_words)}
    mid=_sha256_text(_canonical_json(body))[:32]
    return WaveGlyphComparisonMap("BC-WAVE-GLYPH-COMPARISON-MAP-2",source_ids,entries_tuple,classes_tuple,
        links_tuple,frame_entries_tuple,frame_classes_tuple,unmatched,unmatched_frame_words,mid)


def reopen_wave_glyph_comparison(waves: Sequence[AddressOneHotWave],
                                 comparison_map: WaveGlyphComparisonMap) -> dict[str, Any]:
    if not isinstance(comparison_map,WaveGlyphComparisonMap):
        return {"schema":"BC-WAVE-GLYPH-COMPARISON-REOPEN-1","pass":False,"reason":"wave_comparison_map_required"}
    try:
        rebuilt=compare_address_onehot_waves(waves)
        passed=rebuilt==comparison_map and rebuilt.map_address==comparison_map.map_address
        return {"schema":"BC-WAVE-GLYPH-COMPARISON-REOPEN-2","pass":passed,
                "map_address":comparison_map.map_address,"rebuilt_map_address":rebuilt.map_address,
                "source_wave_count":len(rebuilt.source_wave_addresses),"entry_count":len(rebuilt.entries),
                "match_class_count":len(rebuilt.classes),"dimensional_link_count":len(rebuilt.dimensional_links),
                "frame_entry_count":len(rebuilt.frame_entries),"frame_match_class_count":len(rebuilt.frame_classes),
                "glyph_admission":False,"persistent_save":False}
    except (TypeError,ValueError,KeyError) as exc:
        return {"schema":"BC-WAVE-GLYPH-COMPARISON-REOPEN-1","pass":False,
                "reason":f"wave_comparison_rebuild_failed:{type(exc).__name__}:{exc}"}


def open_address_wave_glyph(wave: AddressOneHotWave, wave_glyph_address: str) -> AddressWaveGlyph:
    """Open one addressed wave glyph without copying it out of its source provenance."""
    if not isinstance(wave,AddressOneHotWave):
        raise TypeError("address_onehot_wave_required")
    if not isinstance(wave_glyph_address,str) or not wave_glyph_address:
        raise ValueError("wave_glyph_address_required")
    matches=[glyph for glyph in wave.wave_glyphs if glyph.wave_glyph_address==wave_glyph_address]
    if len(matches)!=1:
        raise LookupError("wave_glyph_not_uniquely_present_in_source_wave")
    return matches[0]


def reopen_address_wave_glyph(address: BCFloorAddress, cone: DepthWaveCone,
                              wave: AddressOneHotWave, glyph: AddressWaveGlyph) -> dict[str,Any]:
    """Rebuild the parent wave and prove this glyph remains bound to its source shell."""
    if not isinstance(glyph,AddressWaveGlyph):
        return {"schema":"BC-WAVE-GLYPH-REOPEN-1","pass":False,"reason":"address_wave_glyph_required"}
    try:
        rebuilt_wave=build_address_onehot_wave(address,cone)
        matches=[item for item in rebuilt_wave.wave_glyphs if item.wave_glyph_address==glyph.wave_glyph_address]
        passed=len(matches)==1 and matches[0]==glyph and wave==rebuilt_wave
        return {"schema":"BC-WAVE-GLYPH-REOPEN-1","pass":passed,
                "source_wave_address":wave.wave_address,"rebuilt_source_wave_address":rebuilt_wave.wave_address,
                "wave_glyph_address":glyph.wave_glyph_address,
                "wave_glyph_short_name":glyph.short_name,"source_address_id":address.address_id,
                "child_address_id":glyph.child_address_id,"depth":glyph.depth,"wave_distance":glyph.wave_distance,
                "projection_ranks":[p.rank for p in glyph.projections],
                "frontier_residual_count":len(glyph.frontier_addresses),
                "glyph_admission":False,"persistent_save":False}
    except (TypeError,ValueError,KeyError) as exc:
        return {"schema":"BC-WAVE-GLYPH-REOPEN-1","pass":False,
                "reason":f"wave_glyph_rebuild_failed:{type(exc).__name__}:{exc}"}



# ---------------------------------------------------------------------------
# Joint structural-fractal / prime-harmonic center gauge.
# The center is a paired address (actual one-hot frame + harmonic reference),
# not a claim about a globally located or finitely counted fractal center.
# Cyclic residues and unwrapped winding are kept separately. The 504-head
# cycle and the PrimeRPM word phase modulus are distinct fields/roles even
# when both happen to equal 504.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PrimeLaneRelativeWord:
    prime: int
    rate: int
    absolute_position: int
    reference_position: int
    relative_steps: int
    phase_modulus: int
    cycle_residue: int
    phase_residue: int

    def as_dict(self) -> dict[str, int]:
        return {"prime":self.prime,"rate":self.rate,"absolute_position":self.absolute_position,
                "reference_position":self.reference_position,"relative_steps":self.relative_steps,
                "phase_modulus":self.phase_modulus,"cycle_residue":self.cycle_residue,
                "phase_residue":self.phase_residue}


@dataclass(frozen=True)
class HarmonicFractalFrame:
    schema: str
    source_address_id: str
    frame_selector: str
    center_selector: str
    target_frame: AddressOneHotFrame
    center_frame: AddressOneHotFrame
    center_address: str
    structural_depth_delta: int
    harmonic_address_id: str
    harmonic_head: int
    harmonic_reference_head: int
    harmonic_winding: int
    center_head: int
    center_winding: int
    relative_harmonic_steps: int
    harmonic_cycle_delta: int
    harmonic_phase_residue: int
    harmonic_signed_phase: int
    aperture_prefix: tuple[int, ...]
    rpm_address_id: str | None
    rpm_phase_modulus: int | None
    rpm_reference_positions: tuple[tuple[int, int], ...]
    rpm_lanes: tuple[PrimeLaneRelativeWord, ...]
    scale_family: str | None
    scale_factors: tuple[int, ...]
    structural_signature: str
    center_signature: str
    comparison_signature: str
    frame_address: str
    residuals: tuple[str, ...]
    claim_boundary: str = "joint addressable comparison center only; no global-center count, geometric calibration, or physical phase claim"

    def _body(self) -> dict[str, Any]:
        return {"schema":self.schema,"source_address_id":self.source_address_id,
            "frame_selector":self.frame_selector,"center_selector":self.center_selector,
            "target_frame":self.target_frame.as_dict(),"center_frame":self.center_frame.as_dict(),
            "center_address":self.center_address,"structural_depth_delta":self.structural_depth_delta,
            "harmonic_address_id":self.harmonic_address_id,"harmonic_head":self.harmonic_head,
            "harmonic_reference_head":self.harmonic_reference_head,"harmonic_winding":self.harmonic_winding,
            "center_head":self.center_head,"center_winding":self.center_winding,
            "relative_harmonic_steps":self.relative_harmonic_steps,"harmonic_cycle_delta":self.harmonic_cycle_delta,
            "harmonic_phase_residue":self.harmonic_phase_residue,"harmonic_signed_phase":self.harmonic_signed_phase,
            "aperture_prefix":list(self.aperture_prefix),"rpm_address_id":self.rpm_address_id,
            "rpm_phase_modulus":self.rpm_phase_modulus,
            "rpm_reference_positions":[list(row) for row in self.rpm_reference_positions],
            "rpm_lanes":[lane.as_dict() for lane in self.rpm_lanes],"scale_family":self.scale_family,
            "scale_factors":list(self.scale_factors),"structural_signature":self.structural_signature,
            "center_signature":self.center_signature,"comparison_signature":self.comparison_signature,
            "residuals":list(self.residuals),"claim_boundary":self.claim_boundary}

    def as_dict(self) -> dict[str, Any]:
        body=self._body(); body["frame_address"]=self.frame_address; return body


@dataclass(frozen=True)
class HarmonicFractalComparison:
    schema: str
    left_frame_address: str
    right_frame_address: str
    left_source_address_id: str
    right_source_address_id: str
    target_onehot_match: bool
    center_onehot_match: bool
    target_aperture_match: bool
    center_aperture_match: bool
    rank_match: bool
    depth_offset_match: bool
    harmonic_phase_match: bool
    harmonic_winding_match: bool
    aperture_prefix_match: bool
    rpm_lane_phase_match: bool | None
    rpm_lane_winding_match: bool | None
    scale_family_match: bool
    joint_pattern_match: bool
    status: str
    residuals: tuple[str, ...]
    comparison_address: str
    claim_boundary: str = "structural/harmonic relation only; a match is not automatic glyph admission or proof of physical equivalence"

    def _body(self) -> dict[str, Any]:
        return {"schema":self.schema,"left_frame_address":self.left_frame_address,
            "right_frame_address":self.right_frame_address,"left_source_address_id":self.left_source_address_id,
            "right_source_address_id":self.right_source_address_id,"target_onehot_match":self.target_onehot_match,
            "center_onehot_match":self.center_onehot_match,"target_aperture_match":self.target_aperture_match,
            "center_aperture_match":self.center_aperture_match,"rank_match":self.rank_match,
            "depth_offset_match":self.depth_offset_match,"harmonic_phase_match":self.harmonic_phase_match,
            "harmonic_winding_match":self.harmonic_winding_match,"aperture_prefix_match":self.aperture_prefix_match,
            "rpm_lane_phase_match":self.rpm_lane_phase_match,"rpm_lane_winding_match":self.rpm_lane_winding_match,
            "scale_family_match":self.scale_family_match,"joint_pattern_match":self.joint_pattern_match,
            "status":self.status,"residuals":list(self.residuals),"claim_boundary":self.claim_boundary}

    def as_dict(self) -> dict[str, Any]:
        body=self._body(); body["comparison_address"]=self.comparison_address; return body


def _hf_frame_select(address: BCFloorAddress, selector: str) -> AddressOneHotFrame:
    frames=_address_onehot_frames(address)
    if selector == "deepest_resolved":
        rows=[f for f in frames if f.frame_kind=="recursive_box_cube_frame" and
              dict(f.address_factors).get("active") is True and dict(f.address_factors).get("resolved") is True]
        if rows:
            return max(rows,key=lambda f:(f.depth,f.frame_name))
        root=next((f for f in frames if f.frame_name=="root.lattice216"),None)
        if root is not None:
            return root
        return next(f for f in frames if f.frame_name=="surface.X")
    if selector == "deepest_addressed":
        return max(frames,key=lambda f:(f.depth,f.frame_name))
    for frame in frames:
        if frame.frame_name == selector:
            return frame
    raise LookupError(f"harmonic_fractal_frame_selector_unresolved:{selector}")


def _hf_words_signature(frame: AddressOneHotFrame) -> str:
    body={"frame_kind":frame.frame_kind,"aperture_address":frame.aperture_address,
          "words":[{"family":w.family,"width":w.width,"active_slots":list(w.active_slots),
                     "mode":w.mode,"presence":w.presence} for w in frame.words]}
    return _sha256_text(_canonical_json(body))[:24]


def open_harmonic_fractal_frame(address: BCFloorAddress,
        frame_selector: str = "deepest_resolved", center_selector: str = "root.lattice216",
        center_head: int | None = None, center_winding: int = 0,
        rpm_reference_positions: Mapping[int, int] | None = None,
        scale_family: str | None = None) -> HarmonicFractalFrame:
    """Compose one actual sparse one-hot frame with an explicit 504-head and prime-lane center.

    Selectors refer to existing frame names (e.g. ``levels.1`` or ``root.lattice216``),
    or ``deepest_resolved`` / ``deepest_addressed``. A missing/unknown center is not inferred.
    Scale family, when supplied, names an existing factored stack; it does not claim a
    physical scaling law. The PHA head-cycle and RPM word modulus remain separately carried.
    """
    if not isinstance(address,BCFloorAddress):
        raise TypeError("harmonic_fractal_requires_full_floor_address")
    if address.prime_harmonic is None:
        raise ValueError("harmonic_fractal_requires_address_bound_prime_harmonic")
    if not isinstance(frame_selector,str) or not frame_selector:
        raise ValueError("harmonic_fractal_frame_selector_required")
    if not isinstance(center_selector,str) or not center_selector:
        raise ValueError("harmonic_fractal_center_selector_required")
    if type(center_winding) is not int:
        raise TypeError("harmonic_fractal_center_winding_must_be_integer")
    harmonic=address.prime_harmonic
    anchor_head=harmonic.reference_head if center_head is None else center_head
    if type(anchor_head) is not int or not 0 <= anchor_head < HARMONIC_HEADS:
        raise ValueError("harmonic_fractal_center_head_out_of_range")
    scale_factors: tuple[int,...]=()
    if scale_family is not None:
        if not isinstance(scale_family,str) or scale_family not in HARMONIC_STACK_BY_NAME:
            raise ValueError("harmonic_fractal_scale_family_unknown")
        scale_factors=HARMONIC_STACK_BY_NAME[scale_family].shape
    refs={} if rpm_reference_positions is None else dict(rpm_reference_positions)
    if any(type(k) is not int or type(v) is not int for k,v in refs.items()):
        raise TypeError("harmonic_fractal_rpm_references_must_be_exact_integer_mapping")
    target=_hf_frame_select(address,frame_selector)
    anchor=_hf_frame_select(address,center_selector)
    # This is an unwrapped relation against an explicit center, not only (head-reference) % 504.
    absolute=harmonic.winding*HARMONIC_HEADS+harmonic.head
    anchor_absolute=center_winding*HARMONIC_HEADS+anchor_head
    relative=absolute-anchor_absolute
    cycle,residue=divmod(relative,HARMONIC_HEADS)
    signed=residue if residue < HARMONIC_ANTIPODE_STEPS else residue-HARMONIC_HEADS
    rpm=address.prime_rpm
    lane_rows=[]
    residuals=[]
    if rpm is None:
        rpm_modulus=None
        residuals.append("prime_rpm_lane_address_unresolved")
    else:
        rpm_modulus=rpm.phase_modulus
        unknown_refs=set(refs)-set(rpm.prime_lenses)
        if unknown_refs:
            raise ValueError("harmonic_fractal_rpm_reference_for_unbound_lanes:"+",".join(map(str,sorted(unknown_refs))))
        for prime,rate in rpm.rate_bindings:
            position=rpm.position_map[prime]
            reference=refs.get(prime,0)
            delta=position-reference
            turns,phase=divmod(delta,rpm.phase_modulus)
            lane_rows.append(PrimeLaneRelativeWord(prime,rate,position,reference,delta,rpm.phase_modulus,turns,phase))
    target_sig=_hf_words_signature(target)
    anchor_sig=_hf_words_signature(anchor)
    comparison_body={"schema":"BC-HARMONIC-FRACTAL-CENTER-SIGNATURE-1",
        "target_signature":target_sig,"center_signature":anchor_sig,
        "target_kind":target.frame_kind,"center_kind":anchor.frame_kind,
        "target_aperture":target.aperture_address,"center_aperture":anchor.aperture_address,
        "harmonic_phase_residue":residue,"aperture_prefix":list(harmonic.aperture_prefix),
        "rpm_lanes":[[r.prime,r.rate,r.phase_modulus,r.phase_residue] for r in lane_rows],
        "scale_family":scale_family,"scale_factors":list(scale_factors)}
    comparison_signature=_sha256_text(_canonical_json(comparison_body))[:24]
    center_body={"schema":"BC-HARMONIC-FRACTAL-CENTER-ADDRESS-1","source":address.address_id,
        "center_frame":anchor.frame_address,"center_head":anchor_head,"center_winding":center_winding,
        "aperture_prefix":list(harmonic.aperture_prefix),"rpm_address":None if rpm is None else rpm.address_id,
        "rpm_reference_positions":sorted(refs.items()),"scale_family":scale_family,"scale_factors":list(scale_factors)}
    center_address=_sha256_text(_canonical_json(center_body))[:24]
    body={"schema":"BC-HARMONIC-FRACTAL-CENTER-1","source":address.address_id,
        "frame_selector":frame_selector,"center_selector":center_selector,
        "target_frame":target.frame_address,"center_frame":anchor.frame_address,"center_address":center_address,
        "center_head":anchor_head,"center_winding":center_winding,
        "relative_harmonic_steps":relative,"scale_family":scale_family,
        "rpm_reference_positions":sorted(refs.items()),"comparison_signature":comparison_signature}
    frame_address=_sha256_text(_canonical_json(body))[:24]
    return HarmonicFractalFrame("BC-HARMONIC-FRACTAL-CENTER-1",address.address_id,frame_selector,center_selector,
        target,anchor,center_address,target.depth-anchor.depth,harmonic.address_id,harmonic.head,harmonic.reference_head,harmonic.winding,
        anchor_head,center_winding,relative,cycle,residue,signed,harmonic.aperture_prefix,
        None if rpm is None else rpm.address_id,rpm_modulus,tuple(sorted(refs.items())),tuple(lane_rows),scale_family,
        scale_factors,target_sig,anchor_sig,comparison_signature,frame_address,tuple(residuals))


def reopen_harmonic_fractal_frame(address: BCFloorAddress, frame: HarmonicFractalFrame) -> dict[str,Any]:
    if not isinstance(frame,HarmonicFractalFrame):
        return {"schema":"BC-HARMONIC-FRACTAL-REOPEN-1","pass":False,"reason":"harmonic_fractal_frame_required"}
    if address.address_id!=frame.source_address_id:
        return {"schema":"BC-HARMONIC-FRACTAL-REOPEN-1","pass":False,
                "reason":"harmonic_fractal_source_address_mismatch","source_matches":False}
    try:
        rebuilt=open_harmonic_fractal_frame(address,frame.frame_selector,frame.center_selector,frame.center_head,
            frame.center_winding,dict(frame.rpm_reference_positions),frame.scale_family)
    except (TypeError,ValueError,LookupError) as exc:
        return {"schema":"BC-HARMONIC-FRACTAL-REOPEN-1","pass":False,"reason":f"{type(exc).__name__}:{exc}"}
    passed=rebuilt==frame
    return {"schema":"BC-HARMONIC-FRACTAL-REOPEN-1","pass":passed,
        "source_matches":frame.source_address_id==address.address_id,
        "target_frame_rebuilt":rebuilt.target_frame==frame.target_frame,
        "center_frame_rebuilt":rebuilt.center_frame==frame.center_frame,
        "unwrapped_phase_recomputed":(rebuilt.relative_harmonic_steps,rebuilt.harmonic_cycle_delta,rebuilt.harmonic_phase_residue)==
            (frame.relative_harmonic_steps,frame.harmonic_cycle_delta,frame.harmonic_phase_residue),
        "rpm_modulus_kept_separate":rebuilt.rpm_phase_modulus==frame.rpm_phase_modulus,
        "frame_address":frame.frame_address,"rebuilt_frame_address":rebuilt.frame_address,
        "global_center_claimed":False,"glyph_admission":False}


def compare_harmonic_fractal_frames(left: HarmonicFractalFrame,
                                    right: HarmonicFractalFrame) -> HarmonicFractalComparison:
    if not isinstance(left,HarmonicFractalFrame) or not isinstance(right,HarmonicFractalFrame):
        raise TypeError("harmonic_fractal_pair_required")
    target_words=left.structural_signature==right.structural_signature
    center_words=left.center_signature==right.center_signature
    target_ap=left.target_frame.aperture_address==right.target_frame.aperture_address
    center_ap=left.center_frame.aperture_address==right.center_frame.aperture_address
    ranks=(left.target_frame.dimension_rank,left.center_frame.dimension_rank)==(right.target_frame.dimension_rank,right.center_frame.dimension_rank)
    depths=left.structural_depth_delta==right.structural_depth_delta
    phase=left.harmonic_phase_residue==right.harmonic_phase_residue
    winding=left.harmonic_cycle_delta==right.harmonic_cycle_delta
    prefix=left.aperture_prefix==right.aperture_prefix
    if left.rpm_phase_modulus is None or right.rpm_phase_modulus is None:
        lane_phase=None; lane_winding=None
    else:
        lane_phase=(tuple((x.prime,x.rate,x.phase_modulus,x.phase_residue) for x in left.rpm_lanes)==
                    tuple((x.prime,x.rate,x.phase_modulus,x.phase_residue) for x in right.rpm_lanes))
        lane_winding=(tuple((x.prime,x.cycle_residue) for x in left.rpm_lanes)==
                      tuple((x.prime,x.cycle_residue) for x in right.rpm_lanes))
    scale_match=left.scale_family==right.scale_family and left.scale_factors==right.scale_factors
    residuals=[]
    if not target_words: residuals.append("target_onehot_pattern_difference")
    if not center_words: residuals.append("center_onehot_pattern_difference")
    if not target_ap: residuals.append("target_aperture_family_difference")
    if not center_ap: residuals.append("center_aperture_family_difference")
    if not ranks: residuals.append("dimension_rank_difference")
    if not depths: residuals.append("structural_depth_offset_difference")
    if not phase: residuals.append("harmonic_phase_residue_difference")
    if not winding: residuals.append("harmonic_winding_difference_same_or_different_cycle_not_collapsed")
    if not prefix: residuals.append("prime_aperture_prefix_difference")
    if lane_phase is None: residuals.append("prime_rpm_lane_phase_unresolved")
    elif not lane_phase: residuals.append("prime_rpm_lane_phase_difference")
    if lane_winding is False: residuals.append("prime_rpm_lane_winding_difference")
    if not scale_match: residuals.append("scale_family_difference")
    joint=(target_words and center_words and target_ap and center_ap and phase and prefix and
           lane_phase is True and scale_match)
    status="joint_pattern_match" if joint and winding and depths and ranks else (
        "reusable_joint_pattern_with_residuals" if joint else "partial_relation_only")
    body={"schema":"BC-HARMONIC-FRACTAL-COMPARISON-1","left":left.frame_address,"right":right.frame_address,
        "target_onehot_match":target_words,"center_onehot_match":center_words,"target_aperture_match":target_ap,
        "center_aperture_match":center_ap,"rank_match":ranks,"depth_offset_match":depths,
        "harmonic_phase_match":phase,"harmonic_winding_match":winding,"aperture_prefix_match":prefix,
        "rpm_lane_phase_match":lane_phase,"rpm_lane_winding_match":lane_winding,"scale_family_match":scale_match,
        "joint_pattern_match":joint,"status":status,"residuals":residuals}
    cid=_sha256_text(_canonical_json(body))[:24]
    return HarmonicFractalComparison("BC-HARMONIC-FRACTAL-COMPARISON-1",left.frame_address,right.frame_address,
        left.source_address_id,right.source_address_id,target_words,center_words,target_ap,center_ap,ranks,depths,
        phase,winding,prefix,lane_phase,lane_winding,scale_match,joint,status,tuple(residuals),cid)


def reopen_harmonic_fractal_comparison(left: HarmonicFractalFrame, right: HarmonicFractalFrame,
                                       comparison: HarmonicFractalComparison) -> dict[str,Any]:
    if not isinstance(comparison,HarmonicFractalComparison):
        return {"schema":"BC-HARMONIC-FRACTAL-COMPARISON-REOPEN-1","pass":False,"reason":"comparison_required"}
    try:
        rebuilt=compare_harmonic_fractal_frames(left,right)
    except (TypeError,ValueError) as exc:
        return {"schema":"BC-HARMONIC-FRACTAL-COMPARISON-REOPEN-1","pass":False,"reason":f"{type(exc).__name__}:{exc}"}
    return {"schema":"BC-HARMONIC-FRACTAL-COMPARISON-REOPEN-1","pass":rebuilt==comparison,
        "comparison_address":comparison.comparison_address,"rebuilt_address":rebuilt.comparison_address,
        "residues_recomputed":rebuilt.residuals==comparison.residuals,"glyph_admission":False,"persistent_save":False}



# ---------------------------------------------------------------------------
# Exact 8 -> 9 -> 7 sphere-504 carry path and prime-cog views.
# Modulo is retained as the cyclic readout, but is no longer the whole
# transition model: every factor carry, unwrapped cycle delta and one-hot
# octant projection is surfaced. Prime cog rates are projections of the same
# whole phase, never independent phase authorities.
# ---------------------------------------------------------------------------
SPHERE504_SIZE = HARMONIC_HEADS
SPHERE504_RADICES = (8, 9, 7)   # octant -> ternary pair -> heptad
SPHERE504_COG_RATES = (3, 5, 7)


@dataclass(frozen=True)
class Sphere504RadixStep:
    schema: str
    head_before: int
    signed_ticks: int
    head_after: int
    octant_before: int
    pair_before: int
    heptad_before: int
    octant_after: int
    pair_after: int
    heptad_after: int
    carry8_octant_to_pair: int
    carry9_pair_to_heptad: int
    carry7_heptad_to_sphere: int
    direct_sphere_cycle_carry: int
    onehot_before_mask: int
    onehot_after_mask: int
    direct_modulo_match: bool
    factor_cycle_match: bool
    step_address: str

    def _body(self) -> dict[str, Any]:
        return {"schema":self.schema,"head_before":self.head_before,"signed_ticks":self.signed_ticks,
            "head_after":self.head_after,"radix_before":{"octant8":self.octant_before,"pair9":self.pair_before,"heptad7":self.heptad_before},
            "radix_after":{"octant8":self.octant_after,"pair9":self.pair_after,"heptad7":self.heptad_after},
            "carry8_octant_to_pair":self.carry8_octant_to_pair,"carry9_pair_to_heptad":self.carry9_pair_to_heptad,
            "carry7_heptad_to_sphere":self.carry7_heptad_to_sphere,
            "direct_sphere_cycle_carry":self.direct_sphere_cycle_carry,
            "onehot_before_mask":self.onehot_before_mask,"onehot_after_mask":self.onehot_after_mask,
            "direct_modulo_match":self.direct_modulo_match,"factor_cycle_match":self.factor_cycle_match}

    def as_dict(self) -> dict[str, Any]:
        body=self._body(); body["step_address"]=self.step_address; return body


def _sphere504_radix_core(head: int, signed_ticks: int) -> tuple[int,int,int,int,int,int,int,int]:
    """Exact mixed-radix carries, using floor division so negative walks replay correctly."""
    octant=head % 8
    pair=(head // 8) % 9
    heptad=head // 72
    octant_total=octant+signed_ticks
    octant_after=octant_total % 8
    carry8=octant_total // 8
    pair_total=pair+carry8
    pair_after=pair_total % 9
    carry9=pair_total // 9
    heptad_total=heptad+carry9
    heptad_after=heptad_total % 7
    carry7=heptad_total // 7
    head_after=(heptad_after*9+pair_after)*8+octant_after
    direct_carry=(head+signed_ticks)//SPHERE504_SIZE
    return head_after,carry8,carry9,carry7,direct_carry,octant_after,pair_after,heptad_after


def sphere504_mixed_radix_step(head: int, signed_ticks: int) -> Sphere504RadixStep:
    """Advance a 504 head by explicit 8 -> 9 -> 7 carries and retain modulo as a check."""
    if type(head) is not int or not 0 <= head < SPHERE504_SIZE:
        raise ValueError("sphere504_head_out_of_range")
    if type(signed_ticks) is not int:
        raise TypeError("sphere504_signed_ticks_must_be_exact_integer")
    octant_before=head % 8; pair_before=(head // 8) % 9; heptad_before=head // 72
    after,c8,c9,c7,direct,oa,pa,ha=_sphere504_radix_core(head,signed_ticks)
    direct_after=(head+signed_ticks)%SPHERE504_SIZE
    direct_match=after==direct_after
    factor_match=c7==direct
    body={"schema":"BC-SPHERE504-RADIX-STEP-1","head_before":head,"signed_ticks":signed_ticks,
        "head_after":after,"radix_before":{"octant8":octant_before,"pair9":pair_before,"heptad7":heptad_before},
        "radix_after":{"octant8":oa,"pair9":pa,"heptad7":ha},
        "carry8_octant_to_pair":c8,"carry9_pair_to_heptad":c9,"carry7_heptad_to_sphere":c7,
        "direct_sphere_cycle_carry":direct,"onehot_before_mask":1<<octant_before,"onehot_after_mask":1<<oa,
        "direct_modulo_match":direct_match,"factor_cycle_match":factor_match}
    return Sphere504RadixStep("BC-SPHERE504-RADIX-STEP-1",head,signed_ticks,after,octant_before,pair_before,
        heptad_before,oa,pa,ha,c8,c9,c7,direct,1<<octant_before,1<<oa,direct_match,factor_match,
        _sha256_text(_canonical_json(body))[:24])


def reopen_sphere504_radix_step(head: int, signed_ticks: int, step: Sphere504RadixStep) -> dict[str,Any]:
    if not isinstance(step,Sphere504RadixStep):
        return {"schema":"BC-SPHERE504-RADIX-REOPEN-1","pass":False,"reason":"sphere504_radix_step_required"}
    try:
        rebuilt=sphere504_mixed_radix_step(head,signed_ticks)
    except (TypeError,ValueError) as exc:
        return {"schema":"BC-SPHERE504-RADIX-REOPEN-1","pass":False,"reason":f"{type(exc).__name__}:{exc}"}
    return {"schema":"BC-SPHERE504-RADIX-REOPEN-1","pass":rebuilt==step,
        "step_address":step.step_address,"rebuilt_step_address":rebuilt.step_address,
        "factor_carries_recomputed":(rebuilt.carry8_octant_to_pair,rebuilt.carry9_pair_to_heptad,rebuilt.carry7_heptad_to_sphere)==
            (step.carry8_octant_to_pair,step.carry9_pair_to_heptad,step.carry7_heptad_to_sphere),
        "direct_modulo_check_recomputed":rebuilt.direct_modulo_match==step.direct_modulo_match}


@dataclass(frozen=True)
class PrimeCogLaneStep:
    schema: str
    rate: int
    whole_phase_before: int
    signed_ticks: int
    whole_phase_after: int
    scaled_phase_before: int
    scaled_phase_after: int
    scaled_tick_delta: int
    sphere_period: int
    signed_sphere_cycles_crossed: int
    radix_step: Sphere504RadixStep
    same_onehot_octant: bool
    full_sphere_head_moved: bool
    octant_dot: int
    tangent_vector: tuple[int,int,int]
    tangent_dot_source: int
    tangent_norm_squared: int
    tangent_defined: bool
    octant_transition_kind: str
    octant_read: str
    projection_matches_whole_phase: bool
    lane_address: str

    def _body(self) -> dict[str,Any]:
        return {"schema":self.schema,"rate":self.rate,"whole_phase_before":self.whole_phase_before,
            "signed_ticks":self.signed_ticks,"whole_phase_after":self.whole_phase_after,
            "scaled_phase_before":self.scaled_phase_before,"scaled_phase_after":self.scaled_phase_after,
            "scaled_tick_delta":self.scaled_tick_delta,"sphere_period":self.sphere_period,
            "signed_sphere_cycles_crossed":self.signed_sphere_cycles_crossed,
            "radix_step":self.radix_step.as_dict(),"same_onehot_octant":self.same_onehot_octant,
            "full_sphere_head_moved":self.full_sphere_head_moved,"octant_dot":self.octant_dot,
            "tangent_vector":list(self.tangent_vector),"tangent_dot_source":self.tangent_dot_source,
            "tangent_norm_squared":self.tangent_norm_squared,"tangent_defined":self.tangent_defined,
            "octant_transition_kind":self.octant_transition_kind,"octant_read":self.octant_read,
            "projection_matches_whole_phase":self.projection_matches_whole_phase}

    def as_dict(self) -> dict[str,Any]:
        body=self._body(); body["lane_address"]=self.lane_address; return body


def prime_cog_lane_step(whole_phase: int, signed_ticks: int, rate: int) -> PrimeCogLaneStep:
    """Read a 3/5/7 sphere lane from one authoritative unwrapped whole phase."""
    if type(whole_phase) is not int or type(signed_ticks) is not int:
        raise TypeError("prime_cog_phase_and_ticks_must_be_exact_integers")
    if type(rate) is not int or rate not in SPHERE504_COG_RATES:
        raise ValueError("prime_cog_rate_must_be_one_of_3_5_7")
    before_abs=whole_phase*rate; after_abs=(whole_phase+signed_ticks)*rate
    before=before_abs % SPHERE504_SIZE; after=after_abs % SPHERE504_SIZE
    delta=signed_ticks*rate
    radix=sphere504_mixed_radix_step(before,delta)
    period=SPHERE504_SIZE // _integer_gcd(SPHERE504_SIZE,rate)
    cycle_delta=after_abs//SPHERE504_SIZE-before_abs//SPHERE504_SIZE
    same_octant=radix.onehot_before_mask==radix.onehot_after_mask
    head_moved=before!=radix.head_after
    source=tuple(1 if radix.octant_before & (1 << axis) else -1 for axis in range(3))
    target=tuple(1 if radix.octant_after & (1 << axis) else -1 for axis in range(3))
    dot=sum(source[i]*target[i] for i in range(3))
    tangent=tuple(3*target[i]-dot*source[i] for i in range(3))
    tangent_dot_source=sum(tangent[i]*source[i] for i in range(3))
    tangent_norm_squared=sum(v*v for v in tangent)
    transition_kind=("stationary" if dot==3 else
        ("antipodal_route_required" if dot==-3 else ("cube_edge" if dot==1 else "face_diagonal")))
    tangent_defined=dot not in (3,-3)
    if not head_moved: read="STATIONARY_SHELL_ADDRESS"
    elif same_octant: read="OCTANT_PROJECTION_STABLE_BUT_SHELL_ADDRESS_MOVED"
    elif transition_kind=="antipodal_route_required": read="ANTIPODAL_OCTANT_PROJECTION_ROUTE_REQUIRED"
    else: read="DIRECTED_OCTANT_TANGENT_VIEW"
    direct_match=radix.head_after==after and radix.direct_sphere_cycle_carry==cycle_delta
    body={"schema":"BC-SPHERE504-COG-LANE-1","rate":rate,"whole_phase_before":whole_phase,
        "signed_ticks":signed_ticks,"whole_phase_after":whole_phase+signed_ticks,
        "scaled_phase_before":before,"scaled_phase_after":after,"scaled_tick_delta":delta,
        "sphere_period":period,"signed_sphere_cycles_crossed":cycle_delta,"radix_step":radix.as_dict(),
        "same_onehot_octant":same_octant,"full_sphere_head_moved":head_moved,"octant_dot":dot,
        "tangent_vector":list(tangent),"tangent_dot_source":tangent_dot_source,
        "tangent_norm_squared":tangent_norm_squared,"tangent_defined":tangent_defined,
        "octant_transition_kind":transition_kind,"octant_read":read,
        "projection_matches_whole_phase":direct_match}
    return PrimeCogLaneStep("BC-SPHERE504-COG-LANE-1",rate,whole_phase,signed_ticks,whole_phase+signed_ticks,
        before,after,delta,period,cycle_delta,radix,same_octant,head_moved,dot,tangent,tangent_dot_source,
        tangent_norm_squared,tangent_defined,transition_kind,read,direct_match,
        _sha256_text(_canonical_json(body))[:24])


@dataclass(frozen=True)
class PrimeCogBundle:
    schema: str
    authority_phase_before: int
    signed_ticks: int
    authority_phase_after: int
    base_step: Sphere504RadixStep
    lanes: tuple[PrimeCogLaneStep,...]
    joint_return_period: int
    all_projections_replay: bool
    bundle_address: str

    def _body(self) -> dict[str,Any]:
        return {"schema":self.schema,"authority_phase_before":self.authority_phase_before,
            "signed_ticks":self.signed_ticks,"authority_phase_after":self.authority_phase_after,
            "base_step":self.base_step.as_dict(),"lanes":[lane.as_dict() for lane in self.lanes],
            "joint_return_period":self.joint_return_period,"all_projections_replay":self.all_projections_replay}

    def as_dict(self) -> dict[str,Any]:
        body=self._body(); body["bundle_address"]=self.bundle_address; return body


def prime_cog_bundle_step(whole_phase: int, signed_ticks: int) -> PrimeCogBundle:
    if type(whole_phase) is not int or type(signed_ticks) is not int:
        raise TypeError("prime_cog_bundle_phase_and_ticks_must_be_exact_integers")
    base=sphere504_mixed_radix_step(whole_phase % SPHERE504_SIZE,signed_ticks)
    lanes=tuple(prime_cog_lane_step(whole_phase,signed_ticks,rate) for rate in SPHERE504_COG_RATES)
    joint=SPHERE504_SIZE
    for lane in lanes:
        joint=_integer_lcm(joint,lane.sphere_period)
    replay=base.head_after==(whole_phase+signed_ticks)%SPHERE504_SIZE and base.factor_cycle_match and all(l.projection_matches_whole_phase for l in lanes)
    body={"schema":"BC-SPHERE504-COG-BUNDLE-1","authority_phase_before":whole_phase,
        "signed_ticks":signed_ticks,"authority_phase_after":whole_phase+signed_ticks,
        "base_step":base.as_dict(),"lanes":[lane.as_dict() for lane in lanes],
        "joint_return_period":joint,"all_projections_replay":replay}
    return PrimeCogBundle("BC-SPHERE504-COG-BUNDLE-1",whole_phase,signed_ticks,whole_phase+signed_ticks,
        base,lanes,joint,replay,_sha256_text(_canonical_json(body))[:24])


def reopen_prime_cog_bundle(whole_phase: int, signed_ticks: int, bundle: PrimeCogBundle) -> dict[str,Any]:
    if not isinstance(bundle,PrimeCogBundle):
        return {"schema":"BC-SPHERE504-COG-REOPEN-1","pass":False,"reason":"prime_cog_bundle_required"}
    try:
        rebuilt=prime_cog_bundle_step(whole_phase,signed_ticks)
    except (TypeError,ValueError) as exc:
        return {"schema":"BC-SPHERE504-COG-REOPEN-1","pass":False,"reason":f"{type(exc).__name__}:{exc}"}
    return {"schema":"BC-SPHERE504-COG-REOPEN-1","pass":rebuilt==bundle,
        "bundle_address":bundle.bundle_address,"rebuilt_bundle_address":rebuilt.bundle_address,
        "lanes_reopened":len(rebuilt.lanes),"all_projections_replay":rebuilt.all_projections_replay}


def _hf_full_address_witness_dict(witness: FullAddressWitness) -> dict[str,Any]:
    """Portable serialization of the actual full-address transition witness."""
    return {"schema":"BC-FULL-ADDRESS-WITNESS-3","start_address_id":witness.start.address_id,
        "end_address_id":witness.end.address_id,"events":[dict(event) for event in witness.events],
        "delta":{"schema":witness.delta.schema,"parent_id":witness.delta.parent_id,"end_id":witness.delta.end_id,
                 "changes":[dict(change) for change in witness.delta.changes],"difference_address":witness.delta.difference_address},
        "dependency_closed":witness.dependency_closed,"return_to_entry_closed":witness.return_to_entry_closed,
        "difference_replays":witness.difference_replays,"unresolved":list(witness.unresolved),"witness_id":witness.witness_id}


@dataclass(frozen=True)
class HarmonicFractalStep:
    schema: str
    source_address_id: str
    source_frame_address: str
    requested_ticks: int
    after_address: BCFloorAddress
    after_frame: HarmonicFractalFrame
    address_witness: FullAddressWitness
    radix_step: Sphere504RadixStep
    cog_bundle: PrimeCogBundle | None
    winding_delta: int
    prior_frame_reopen_pass: bool
    after_frame_reopen_pass: bool
    radix_matches_address_step: bool
    factor_cycle_matches_winding: bool
    prime_rpm_carrier_unchanged: bool
    pass_all: bool
    residuals: tuple[str,...]
    step_address: str

    def _body(self) -> dict[str,Any]:
        return {"schema":self.schema,"source_address_id":self.source_address_id,
            "source_frame_address":self.source_frame_address,"requested_ticks":self.requested_ticks,
            "after_address":self.after_address.as_dict(),"after_frame":self.after_frame.as_dict(),
            "address_witness":_hf_full_address_witness_dict(self.address_witness),
            "radix_step":self.radix_step.as_dict(),"cog_bundle":None if self.cog_bundle is None else self.cog_bundle.as_dict(),
            "winding_delta":self.winding_delta,"prior_frame_reopen_pass":self.prior_frame_reopen_pass,
            "after_frame_reopen_pass":self.after_frame_reopen_pass,"radix_matches_address_step":self.radix_matches_address_step,
            "factor_cycle_matches_winding":self.factor_cycle_matches_winding,
            "prime_rpm_carrier_unchanged":self.prime_rpm_carrier_unchanged,"pass_all":self.pass_all,
            "residuals":list(self.residuals)}

    def as_dict(self) -> dict[str,Any]:
        body=self._body(); body["step_address"]=self.step_address; return body


def step_harmonic_fractal_center(address: BCFloorAddress, frame: HarmonicFractalFrame,
                                 signed_ticks: int, include_cog_lanes: bool = True) -> HarmonicFractalStep:
    """Move the paired structural/harmonic center through exact 8->9->7 carries.

    Produces a new full address instead of mutating the source. The optional 3/5/7
    cog bundle consists of projections of the same unwrapped phase, not separate wheels.
    The separately addressed PrimeRPMAddress is intentionally retained unchanged.
    """
    if not isinstance(address,BCFloorAddress):
        raise TypeError("harmonic_fractal_step_requires_full_floor_address")
    if not isinstance(frame,HarmonicFractalFrame):
        raise TypeError("harmonic_fractal_step_requires_open_frame")
    if type(signed_ticks) is not int:
        raise TypeError("harmonic_fractal_signed_ticks_must_be_exact_integer")
    if type(include_cog_lanes) is not bool:
        raise TypeError("include_cog_lanes_must_be_boolean")
    if address.prime_harmonic is None:
        raise ValueError("harmonic_fractal_step_requires_prime_harmonic_address")
    prior_check=reopen_harmonic_fractal_frame(address,frame)
    if not prior_check.get("pass"):
        raise ValueError("harmonic_fractal_prior_frame_reopen_failed")
    before=address.prime_harmonic
    head_result=harmonic_head_step(before,signed_ticks)
    # The shared full-address kernel owns the authoritative state transition and emits
    # the portable delta/witness; the specialised radix kernel independently cross-checks it.
    address_witness=FULL_ADDRESS_KERNEL.execute(address,(AddressOperation(kind="move_harmonic_heads",steps=signed_ticks),))
    end=address_witness.end
    if end.prime_harmonic != head_result.address:
        raise ValueError("harmonic_head_step_differs_from_full_address_kernel")
    radix=sphere504_mixed_radix_step(before.head,signed_ticks)
    whole_phase=before.winding*SPHERE504_SIZE+before.head
    cog=prime_cog_bundle_step(whole_phase,signed_ticks) if include_cog_lanes else None
    after_frame=open_harmonic_fractal_frame(end,frame.frame_selector,frame.center_selector,
        frame.center_head,frame.center_winding,dict(frame.rpm_reference_positions),frame.scale_family)
    after_check=reopen_harmonic_fractal_frame(end,after_frame)
    winding_delta=head_result.address.winding-before.winding
    radix_match=radix.head_after==head_result.address.head
    carry_match=radix.direct_sphere_cycle_carry==winding_delta and radix.carry7_heptad_to_sphere==winding_delta
    rpm_unchanged=end.prime_rpm==address.prime_rpm
    residuals=[]
    if not radix_match: residuals.append("mixed_radix_head_differs_from_harmonic_head_step")
    if not carry_match: residuals.append("factor_cycle_carry_differs_from_unwrapped_winding")
    if not after_check.get("pass"): residuals.append("after_center_frame_reopen_failed")
    if cog is not None and not cog.all_projections_replay: residuals.append("prime_cog_projection_replay_failed")
    if not rpm_unchanged: residuals.append("independent_prime_rpm_carrier_changed_unexpectedly")
    passed=bool(prior_check.get("pass") and after_check.get("pass") and address_witness.difference_replays and
                not address_witness.unresolved and radix_match and carry_match and rpm_unchanged and
                (cog is None or cog.all_projections_replay))
    body={"schema":"BC-HARMONIC-FRACTAL-STEP-1","source_address_id":address.address_id,
        "source_frame_address":frame.frame_address,"requested_ticks":signed_ticks,"after_address":end.as_dict(),
        "after_frame":after_frame.as_dict(),"address_witness":_hf_full_address_witness_dict(address_witness),"radix_step":radix.as_dict(),
        "cog_bundle":None if cog is None else cog.as_dict(),"winding_delta":winding_delta,
        "prior_frame_reopen_pass":bool(prior_check.get("pass")),"after_frame_reopen_pass":bool(after_check.get("pass")),
        "radix_matches_address_step":radix_match,"factor_cycle_matches_winding":carry_match,
        "prime_rpm_carrier_unchanged":rpm_unchanged,"pass_all":passed,"residuals":residuals}
    return HarmonicFractalStep("BC-HARMONIC-FRACTAL-STEP-1",address.address_id,frame.frame_address,signed_ticks,
        end,after_frame,address_witness,radix,cog,winding_delta,bool(prior_check.get("pass")),bool(after_check.get("pass")),
        radix_match,carry_match,rpm_unchanged,passed,tuple(residuals),_sha256_text(_canonical_json(body))[:24])


def reopen_harmonic_fractal_step(address: BCFloorAddress, frame: HarmonicFractalFrame,
                                  step: HarmonicFractalStep) -> dict[str,Any]:
    if not isinstance(step,HarmonicFractalStep):
        return {"schema":"BC-HARMONIC-FRACTAL-STEP-REOPEN-1","pass":False,"reason":"harmonic_fractal_step_required"}
    if step.cog_bundle is not None:
        cog_ok=reopen_prime_cog_bundle(address.prime_harmonic.winding*SPHERE504_SIZE+address.prime_harmonic.head,
            step.requested_ticks,step.cog_bundle).get("pass",False) if address.prime_harmonic is not None else False
    else: cog_ok=True
    address_witness_ok=(step.address_witness.start.address_id==address.address_id and
        step.address_witness.end.address_id==step.after_address.address_id and
        step.address_witness.difference_replays and not step.address_witness.unresolved and
        step.address_witness.replay(FULL_ADDRESS_KERNEL,(AddressOperation(kind="move_harmonic_heads",steps=step.requested_ticks),)))
    try:
        rebuilt=step_harmonic_fractal_center(address,frame,step.requested_ticks,step.cog_bundle is not None)
    except (TypeError,ValueError,LookupError) as exc:
        return {"schema":"BC-HARMONIC-FRACTAL-STEP-REOPEN-1","pass":False,"reason":f"{type(exc).__name__}:{exc}","cog_bundle_reopen_pass":cog_ok}
    return {"schema":"BC-HARMONIC-FRACTAL-STEP-REOPEN-1","pass":rebuilt==step and cog_ok and address_witness_ok,
        "step_address":step.step_address,"rebuilt_step_address":rebuilt.step_address,
        "after_address_rebuilt":rebuilt.after_address==step.after_address,
        "after_frame_rebuilt":rebuilt.after_frame==step.after_frame,
        "cog_bundle_reopen_pass":cog_ok,"full_address_witness_replay_pass":address_witness_ok,
        "address_delta_changes":len(step.address_witness.delta.changes),
        "all_carries_recomputed":rebuilt.radix_step==step.radix_step,
        "source_address_unchanged":address.address_id==step.source_address_id,
        "glyph_admission":False,"persistent_save":False}

def harmonic_fractal_summary() -> dict[str,Any]:
    return {"enabled":True,"center_model":"paired addressed sparse one-hot frame + 504-head prime-harmonic reference + optional explicit prime-RPM lane word",
        "glyphs":["BC.HF.OPEN","BC.HF.REOPEN","BC.HF.MATCH","BC.HF.MATCH.REOPEN",
                  "BC.H504.STEP","BC.H504.STEP.REOPEN","BC.H504.COG","BC.H504.COG.REOPEN",
                  "BC.HF.STEP","BC.HF.STEP.REOPEN"],
        "head_cycle_modulus":HARMONIC_HEADS,"head_common_refinement_units":HARMONIC_COMMON_TURN_UNITS,
        "sphere504_mixed_radix":list(SPHERE504_RADICES),"factor_carries_retained":True,
        "prime_cog_rates_are_views_of_whole_phase":list(SPHERE504_COG_RATES),
        "mixed_radix_cycle_carry_checked_against_head_winding":True,
        "static_historical_carry_formula_reimplemented":True,
        "full_historical_wrapper_semantic_parity_claimed":False,
        "exact_integer_cube_tangent_view":True,
        "rpm_phase_modulus_is_separate":True,"rpm_core_lenses":list(PHA_CORE_PRIME_LENSES),
        "rpm_core_rate_bindings":[list(row) for row in PHA_CORE_RATE_BINDINGS],
        "unwrapped_winding_retained":True,"onehot_frame_and_harmonic_center_composed":True,
        "scale_family_is_explicit_not_inferred":True,"box_cube_equal_cardinality_does_not_merge":True,
        "global_fractal_center_count_known":False,"auto_glyph_admission":False,"persistent_save":False}

def structural_wave_glyph_summary() -> dict[str, Any]:
    return {"enabled":True,"method":"address-native sparse one-hot frames plus compactified wave-shell occupancy; dimensions 1/2/3 are projections of the same addressed wave; omitted-axis fibres and frontiers remain residuals",
        "glyphs":["BC.ADDRESS.1HOT.WAVE","BC.ADDRESS.1HOT.WAVE.REOPEN",
                  "BC.WAVE.GLYPH.OPEN","BC.WAVE.GLYPH.REOPEN",
                  "BC.WAVE.GLYPH.COMPARE","BC.WAVE.GLYPH.COMPARE.REOPEN"],
        "local_onehot_states":10,"active_local_positions":9,"page_states":90,"box_aperture":216,"cube_aperture":216,
        "addressable_wave_glyph_open_and_reopen":True,
        "box_cube_state_equivalence_inferred":False,"dimension_ranks":[1,2,3],"coordinate_domain_per_axis":11,
        "wave_glyphs_are_executable_glyphs":False,"wave_glyphs_are_addressed_patterns":True,
        "omitted_dimension_residuals_retained":True,"frontier_residuals_retained":True,
        "exact_onehot_frame_words_indexed_separately":True,"box_slot_and_cube_state_words_never_merge_by_width_only":True,
        "profile_proposal_rows_added":0,"automatic_glyph_construction":False,"automatic_glyph_admission":False,
        "persistent_save":False,"global_center_count_known":False,
        "center_semantics":"each opened lattice seed is addressed; no global fractal-to-center count is inferred"}


REGISTRY.register("build_address_onehot_wave",build_address_onehot_wave,"pure")
REGISTRY.register("reopen_address_onehot_wave",reopen_address_onehot_wave,"pure")
REGISTRY.register("compare_address_onehot_waves",compare_address_onehot_waves,"pure")
REGISTRY.register("reopen_wave_glyph_comparison",reopen_wave_glyph_comparison,"pure")
REGISTRY.register("open_address_wave_glyph",open_address_wave_glyph,"pure")
REGISTRY.register("reopen_address_wave_glyph",reopen_address_wave_glyph,"pure")
_COMPOUND_CLASS_KIND.update({"AddressOneHotWave":"address_onehot_wave",
                             "AddressWaveGlyph":"address_wave_glyph",
                             "WaveGlyphComparisonMap":"wave_glyph_comparison_map"})
for _wave_spec in (
    GlyphSpec.make("BC.ADDRESS.1HOT.WAVE","build_address_onehot_wave",("address","cone"),(),
        {"address":"full_address","cone":"depth_wave_cone"},"pure",
        "compactify actual addressed box/page/cube frames and depth-wave shells as sparse one-hot patterns; retain dimension and frontier residues"),
    GlyphSpec.make("BC.ADDRESS.1HOT.WAVE.REOPEN","reopen_address_onehot_wave",("address","cone","wave"),(),
        {"address":"full_address","cone":"depth_wave_cone","wave":"address_onehot_wave"},"pure",
        "rebuild frames, shell glyphs, projected views and residuals against the same root and cone"),
    GlyphSpec.make("BC.WAVE.GLYPH.OPEN","open_address_wave_glyph",("wave","wave_glyph_address"),(),
        {"wave":"address_onehot_wave","wave_glyph_address":"string"},"pure",
        "open one content-addressed wave glyph from the source wave; retain parent address and shell provenance"),
    GlyphSpec.make("BC.WAVE.GLYPH.REOPEN","reopen_address_wave_glyph",("address","cone","wave","glyph"),(),
        {"address":"full_address","cone":"depth_wave_cone","wave":"address_onehot_wave",
         "glyph":"address_wave_glyph"},"pure",
        "rebuild the source wave and verify a single wave glyph against its exact address, shell, projections and residues"),
    GlyphSpec.make("BC.WAVE.GLYPH.COMPARE","compare_address_onehot_waves",("waves",),(),
        {"waves":"address_onehot_waves"},"pure",
        "compare sparse one-hot shells across addressed depths and 1D/2D/3D projections; map only, no candidate or glyph admission"),
    GlyphSpec.make("BC.WAVE.GLYPH.COMPARE.REOPEN","reopen_wave_glyph_comparison",("waves","comparison_map"),(),
        {"waves":"address_onehot_waves","comparison_map":"wave_glyph_comparison_map"},"pure",
        "rebuild wave-glyph match classes, dimensional links and residual variants from the actual wave records"),
):
    GLYPH_CATALOG.register(_wave_spec)



REGISTRY.register("open_harmonic_fractal_frame",open_harmonic_fractal_frame,"pure")
REGISTRY.register("reopen_harmonic_fractal_frame",reopen_harmonic_fractal_frame,"pure")
REGISTRY.register("compare_harmonic_fractal_frames",compare_harmonic_fractal_frames,"pure")
REGISTRY.register("reopen_harmonic_fractal_comparison",reopen_harmonic_fractal_comparison,"pure")
REGISTRY.register("sphere504_mixed_radix_step",sphere504_mixed_radix_step,"pure")
REGISTRY.register("reopen_sphere504_radix_step",reopen_sphere504_radix_step,"pure")
REGISTRY.register("prime_cog_bundle_step",prime_cog_bundle_step,"pure")
REGISTRY.register("reopen_prime_cog_bundle",reopen_prime_cog_bundle,"pure")
REGISTRY.register("step_harmonic_fractal_center",step_harmonic_fractal_center,"pure")
REGISTRY.register("reopen_harmonic_fractal_step",reopen_harmonic_fractal_step,"pure")
_COMPOUND_CLASS_KIND.update({"HarmonicFractalFrame":"harmonic_fractal_frame",
                             "HarmonicFractalComparison":"harmonic_fractal_comparison",
                             "Sphere504RadixStep":"sphere504_radix_step",
                             "PrimeCogBundle":"prime_cog_bundle",
                             "HarmonicFractalStep":"harmonic_fractal_step"})
for _hf_spec in (
    GlyphSpec.make("BC.HF.OPEN","open_harmonic_fractal_frame",("address",),("frame_selector","center_selector","center_head","center_winding","rpm_reference_positions","scale_family"),
        {"address":"full_address","frame_selector":"string","center_selector":"string","center_head":"integer_or_none",
         "center_winding":"integer","rpm_reference_positions":"integer_sequence_or_mapping","scale_family":"harmonic_stack_name_or_none"},"pure",
        "open an address-bound structural one-hot frame composed with an explicit prime-harmonic center and optional RPM lanes"),
    GlyphSpec.make("BC.HF.REOPEN","reopen_harmonic_fractal_frame",("address","frame"),(),
        {"address":"full_address","frame":"harmonic_fractal_frame"},"pure",
        "rebuild the paired structural/harmonic center and retain cyclic residue, winding, lane and scale residuals"),
    GlyphSpec.make("BC.HF.MATCH","compare_harmonic_fractal_frames",("left","right"),(),
        {"left":"harmonic_fractal_frame","right":"harmonic_fractal_frame"},"pure",
        "compare joint one-hot/harmonic centers; cyclic matches never erase winding, dimension, aperture or scale residuals"),
    GlyphSpec.make("BC.HF.MATCH.REOPEN","reopen_harmonic_fractal_comparison",("left","right","comparison"),(),
        {"left":"harmonic_fractal_frame","right":"harmonic_fractal_frame","comparison":"harmonic_fractal_comparison"},"pure",
        "recompute a joint center comparison from both addressed frames; no automatic glyph admission"),
):
    GLYPH_CATALOG.register(_hf_spec)

for _hc_spec in (
    GlyphSpec.make("BC.H504.STEP","sphere504_mixed_radix_step",("head","signed_ticks"),(),
        {"head":"integer","signed_ticks":"integer"},"pure",
        "exact 8->9->7 factor-carry step with one-hot octant and direct 504-cycle cross-check"),
    GlyphSpec.make("BC.H504.STEP.REOPEN","reopen_sphere504_radix_step",("head","signed_ticks","step"),(),
        {"head":"integer","signed_ticks":"integer","step":"sphere504_radix_step"},"pure",
        "rebuild every mixed-radix carry and the modular reference for one 504-head step"),
    GlyphSpec.make("BC.H504.COG","prime_cog_bundle_step",("whole_phase","signed_ticks"),(),
        {"whole_phase":"integer","signed_ticks":"integer"},"pure",
        "project the authoritative unwrapped phase through the 3/5/7 504-head lanes; retain each factor carry"),
    GlyphSpec.make("BC.H504.COG.REOPEN","reopen_prime_cog_bundle",("whole_phase","signed_ticks","bundle"),(),
        {"whole_phase":"integer","signed_ticks":"integer","bundle":"prime_cog_bundle"},"pure",
        "rebuild the common head and all three rate projections without independent wheel state"),
    GlyphSpec.make("BC.HF.STEP","step_harmonic_fractal_center",("address","frame","signed_ticks"),("include_cog_lanes",),
        {"address":"full_address","frame":"harmonic_fractal_frame","signed_ticks":"integer","include_cog_lanes":"boolean"},"pure",
        "move a source-bound structural/harmonic center; exact carries must agree with winding and the new frame must reopen"),
    GlyphSpec.make("BC.HF.STEP.REOPEN","reopen_harmonic_fractal_step",("address","frame","step"),(),
        {"address":"full_address","frame":"harmonic_fractal_frame","step":"harmonic_fractal_step"},"pure",
        "recompute the whole joint center transition and every retained factor/lane carry"),
):
    GLYPH_CATALOG.register(_hc_spec)

def glyph_learning_summary() -> dict[str, Any]:
    return {"enabled":True,"schema":"BC-GLYPH-LEARNING-LEDGER-1",
        "method":"immutable replay-bound evidence; normalized transition motifs; diverse compound executions; residual-preserving proposals; sparse comparison/name map kept outside compact profile/proposal outputs",
        "self_feed_evidence":"source root, cone request/reopen witness, full end address, exact delta, operation events and observation are retained in portable context",
        "negative_cases":"retained as evidence; mixed outcomes trigger boundary review",
        "minimum_reuse_support":2,"inference_from_delta_to_executor":False,
        "automatic_glyph_construction":False,"automatic_glyph_admission":False,
        "automatic_persistence":False,"cold_commit":False,"ledger_store":"caller-owned immutable object; export/import is explicit",
        "comparison_views":["exact","zero_plane","zero_plane_unit_magnitude","zero_plane_unit_magnitude_six_plane"],
        "comparison_map_separate_from_profile_proposals":True,
        "comparison_matches_create_glyphs":False,
        "glyphs":["BC.LEARN.LEDGER.NEW","BC.LEARN.SELF_FEED","BC.LEARN.COMPOUND_CASE",
                  "BC.LEARN.PROFILE","BC.LEARN.PROPOSALS","BC.LEARN.PROFILE.REOPEN",
                  "BC.LEARN.LEDGER.EXPORT","BC.LEARN.LEDGER.IMPORT","BC.LEARN.LEDGER.REOPEN",
                  "BC.LEARN.COMPARE","BC.LEARN.COMPARE.REOPEN"]}


# Expose learning as short, resident operations. These functions return new
# immutable values; none writes the authoritative BC floor or auto-admits glyphs.
REGISTRY.register("new_glyph_learning_ledger", new_glyph_learning_ledger, "pure")
REGISTRY.register("record_self_feed_evidence", record_self_feed_evidence, "pure")
REGISTRY.register("record_compound_learning_case", record_compound_learning_case, "pure")
REGISTRY.register("build_learning_profile", build_learning_profile, "pure")
REGISTRY.register("propose_learning_routes", propose_learning_routes, "pure")
REGISTRY.register("reopen_learning_profile", reopen_learning_profile, "pure")
REGISTRY.register("export_glyph_learning_ledger", export_glyph_learning_ledger, "pure")
REGISTRY.register("import_glyph_learning_ledger", import_glyph_learning_ledger, "pure")
REGISTRY.register("reopen_glyph_learning_ledger", reopen_glyph_learning_ledger, "pure")

_COMPOUND_CLASS_KIND.update({
    "GlyphLearningLedger":"glyph_learning_ledger",
    "DepthWaveSelfFeedObservation":"depth_wave_self_feed_observation",
    "CompoundGlyphSpec":"compound_glyph_spec",
    "CompoundGlyphRun":"compound_glyph_run",
    "LearningProfile":"learning_profile",
    "LearningProposalSet":"learning_proposal_set",
    "LearningComparisonMap":"learning_comparison_map",
})

for _learn_spec in (
    GlyphSpec.make("BC.LEARN.LEDGER.NEW","new_glyph_learning_ledger",(),(),{},"pure",
                   "new empty immutable evidence ledger; no disk persistence"),
    GlyphSpec.make("BC.LEARN.SELF_FEED","record_self_feed_evidence",("ledger","address","cone","witness","observation"),(),
                   {"ledger":"glyph_learning_ledger","address":"full_address","cone":"depth_wave_cone",
                    "witness":"full_address_witness","observation":"depth_wave_self_feed_observation"},"pure",
                   "source-bound self-feed evidence with exact deltas and cone reopening"),
    GlyphSpec.make("BC.LEARN.COMPOUND_CASE","record_compound_learning_case",("ledger","candidate","inputs","receipt"),(),
                   {"ledger":"glyph_learning_ledger","candidate":"compound_glyph_spec","inputs":"mapping",
                    "receipt":"compound_glyph_run"},"pure",
                   "fresh-replayed compound case; negative cases retained, not learned away"),
    GlyphSpec.make("BC.LEARN.PROFILE","build_learning_profile",("ledger",),("min_cases",),
                   {"ledger":"glyph_learning_ledger","min_cases":"positive_integer"},"pure",
                   "repeated motifs and reuse support with explicit diversity threshold"),
    GlyphSpec.make("BC.LEARN.PROPOSALS","propose_learning_routes",("ledger",),("min_cases",),
                   {"ledger":"glyph_learning_ledger","min_cases":"positive_integer"},"pure",
                   "non-executing residual-aware proposals; no inferred executor or auto-admission"),
    GlyphSpec.make("BC.LEARN.PROFILE.REOPEN","reopen_learning_profile",("ledger","profile"),(),
                   {"ledger":"glyph_learning_ledger","profile":"learning_profile"},"pure",
                   "rebuild profile from immutable evidence ledger"),
    GlyphSpec.make("BC.LEARN.LEDGER.EXPORT","export_glyph_learning_ledger",("ledger",),(),
                   {"ledger":"glyph_learning_ledger"},"pure",
                   "portable ledger data; exported payload is the data, its address is only a locator"),
    GlyphSpec.make("BC.LEARN.LEDGER.IMPORT","import_glyph_learning_ledger",("payload",),(),
                   {"payload":"mapping"},"pure","verify all evidence and ledger content addresses on import"),
    GlyphSpec.make("BC.LEARN.LEDGER.REOPEN","reopen_glyph_learning_ledger",("payload",),(),
                   {"payload":"mapping"},"pure","round-trip and address verification; no file write"),
):
    GLYPH_CATALOG.register(_learn_spec)



# ---------------------------------------------------------------------------
# Shared-context event bundles and fractal-hallway workload prediction.
# Compact records reference immutable shared context; full addresses are
# reconstructed by replaying exact deltas from the retained root.
# ---------------------------------------------------------------------------


def _scb_json_value(value: Any) -> Any:
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return json.loads(_canonical_json(value.as_dict()))
    if isinstance(value, Mapping):
        return json.loads(_canonical_json(dict(value)))
    if isinstance(value, (tuple, list)):
        return json.loads(_canonical_json(value))
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    raise TypeError(f"shared_context_value_not_portable:{type(value).__name__}")


def _scb_put(payloads: dict[str, Any], kind: str, value: Any) -> str:
    normalized = _scb_json_value(value)
    body = {"kind": kind, "value": normalized}
    ref = _sha256_text(_canonical_json(body))
    payloads.setdefault(ref, {"kind": kind, "value": normalized, "sha256": ref,
                              "canonical_bytes": len(_canonical_json(normalized).encode("utf-8"))})
    return ref


def _scb_delta_dict(delta: AddressDelta) -> dict[str, Any]:
    return {"schema": delta.schema, "parent_id": delta.parent_id, "end_id": delta.end_id,
            "changes": _scb_json_value(delta.changes), "difference_address": delta.difference_address}


def _scb_depth_wave_cone_from_dict(raw: Mapping[str, Any]) -> DepthWaveCone:
    """Restore the typed cone so bundle reopening can rerun its real witness."""
    child_addresses = tuple(RecursiveChildAddress(
        str(x["schema"]), str(x["parent_address_id"]), int(x["level_index"]),
        int(x["recursion_depth"]), int(x["box_slot_position"]), int(x["side"]),
        str(x["payload_address_id"]), tuple(x["path"]), str(x["box_aperture_address"]),
        str(x["cube_aperture_address"]), int(x.get("shared_aperture", 216)))
        for x in raw["child_addresses"])
    nodes = tuple(DepthWaveNode(str(x["schema"]), str(x["root_address_id"]),
        str(x["child_address_id"]), int(x["depth"]), int(x["wave_distance"]), tuple(x["source_path"]),
        Lattice216(int(x["lattice"]["lane8"]), tuple(x["lattice"]["ternary27"])),
        str(x["state_address_id"])) for x in raw["nodes"])
    frontier = tuple(DepthWaveFrontier(str(x["schema"]), str(x["root_address_id"]),
        str(x["child_address_id"]), int(x["depth"]), str(x["from_state_address_id"]),
        str(x["target_state_address_id"]), int(x["target_physical_index6"]), tuple(x["target_coord6"]),
        str(x["axis"]), int(x["direction"]), int(x["next_wave_distance"])) for x in raw["frontier"])
    return DepthWaveCone(str(raw["schema"]), str(raw["root_address_id"]),
        int(raw["max_recursive_depth"]), int(raw["wave_radius"]), raw.get("target_child_address_id"),
        bool(raw["include_root_lattice"]), str(raw["aperture_alignment_address"]), child_addresses,
        nodes, frontier, tuple(raw["unresolved"]), bool(raw["dependency_closed"]),
        bool(raw["local_state_spaces_closed"]), str(raw["cone_address"]))


def _scb_operation_from_dict(raw: Mapping[str, Any]) -> AddressOperation:
    values = dict(raw)
    for key in ("prime_lenses", "rpm_start_positions", "rpm_ordered_word"):
        if values.get(key) is not None:
            values[key] = tuple(values[key])
    if values.get("rpm_rates") is not None:
        values["rpm_rates"] = tuple(tuple(x) for x in values["rpm_rates"])
    return AddressOperation(**values)


def build_shared_context_event_bundle(
    root: BCFloorAddress,
    witnesses: Sequence[FullAddressWitness],
    *,
    cone: DepthWaveCone | None = None,
    frames: Mapping[str, Any] | None = None,
    glyph_refs: Sequence[str] | None = None,
    residuals: Sequence[Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Pack an ordered (possibly branching) witness set with root/context stored once.

    Each transition retains operation inputs, exact delta, witness identity and residuals;
    intermediate full addresses are reconstructed by replay, not redundantly serialized.
    """
    if not isinstance(root, BCFloorAddress):
        raise TypeError("shared_bundle_full_root_address_required")
    if not isinstance(witnesses, (tuple, list)) or not all(isinstance(w, FullAddressWitness) for w in witnesses):
        raise TypeError("shared_bundle_full_address_witness_sequence_required")
    if cone is not None:
        if not isinstance(cone, DepthWaveCone) or cone.root_address_id != root.address_id:
            raise ValueError("shared_bundle_cone_root_mismatch")
        if not reopen_depth_wave_cone(root, cone).pass_all:
            raise ValueError("shared_bundle_cone_reopen_failed")
    n = len(witnesses)
    if glyph_refs is not None and len(glyph_refs) != n:
        raise ValueError("shared_bundle_glyph_ref_count_mismatch")
    if residuals is not None and len(residuals) != n:
        raise ValueError("shared_bundle_residual_count_mismatch")

    payloads: dict[str, Any] = {}
    root_ref = _scb_put(payloads, "full_address", root.as_dict())
    context_refs: dict[str, str] = {"root": root_ref}
    if cone is not None:
        context_refs["cone"] = _scb_put(payloads, "depth_wave_cone", cone.as_dict())
    for name, frame in sorted((frames or {}).items()):
        if not isinstance(name, str) or not name:
            raise ValueError("shared_bundle_frame_name_required")
        frame_data = _scb_json_value(frame)
        source_id = frame_data.get("source_address_id") or frame_data.get("root_address_id")
        if source_id is not None and source_id != root.address_id:
            raise ValueError(f"shared_bundle_frame_root_mismatch:{name}")
        context_refs[f"frame:{name}"] = _scb_put(payloads, "addressed_frame", frame_data)

    events: list[dict[str, Any]] = []
    known_states: dict[str, BCFloorAddress] = {root.address_id: root}
    last_event_for_state: dict[str, int] = {root.address_id: -1}
    naive_bytes = 0
    for seq, witness in enumerate(witnesses):
        if not witness.difference_replays or witness.unresolved:
            raise ValueError(f"shared_bundle_unreplayed_witness:{seq}")
        if witness.start.address_id not in known_states:
            raise ValueError(f"shared_bundle_event_start_not_reachable:{seq}")
        if known_states[witness.start.address_id] != witness.start:
            raise ValueError(f"shared_bundle_event_start_payload_mismatch:{seq}")
        # Independent recomputation at packing time prevents malformed witness objects
        # becoming a trusted shared bundle.
        ops = [_scb_operation_from_dict(row["operation"]) for row in witness.events]
        rebuilt = FULL_ADDRESS_KERNEL.execute(witness.start, ops)
        if rebuilt != witness:
            raise ValueError(f"shared_bundle_witness_rebuild_mismatch:{seq}")
        delta_ref = _scb_put(payloads, "address_delta", _scb_delta_dict(witness.delta))
        op_ref = _scb_put(payloads, "address_operations", [row["operation"] for row in witness.events])
        residual_ref = None
        event_residuals = list((residuals or [()] * n)[seq])
        if event_residuals:
            residual_ref = _scb_put(payloads, "residuals", event_residuals)
        parent_event = last_event_for_state.get(witness.start.address_id, -1)
        event = {
            "seq": seq,
            "glyph_ref": (glyph_refs[seq] if glyph_refs is not None else "full_address_execute"),
            "parent_event": None if parent_event < 0 else parent_event,
            "before_address_id": witness.start.address_id,
            "after_address_id": witness.end.address_id,
            "delta_ref": delta_ref,
            "operations_ref": op_ref,
            "operation_count": len(witness.events),
            "witness_id": witness.witness_id,
            "dependency_closed": witness.dependency_closed,
            "return_to_entry_closed": witness.return_to_entry_closed,
            "difference_replays": witness.difference_replays,
            "unresolved": list(witness.unresolved),
            "residuals_ref": residual_ref,
        }
        events.append(event)
        known_states[witness.end.address_id] = witness.end
        last_event_for_state[witness.end.address_id] = seq
        # Counterfactual naive format: repeat full root/cone/frame context and full
        # before/after addresses for every transition.
        naive_doc = {"root": root.as_dict(), "cone": None if cone is None else cone.as_dict(),
            "frames": {k: _scb_json_value(v) for k, v in (frames or {}).items()},
            "start": witness.start.as_dict(), "end": witness.end.as_dict(),
            "delta": _scb_delta_dict(witness.delta), "events": _scb_json_value(witness.events),
            "glyph_ref": event["glyph_ref"], "residuals": event_residuals}
        naive_bytes += len(_canonical_json(naive_doc).encode("utf-8"))

    body = {"schema": "BC-SHARED-CONTEXT-EVENT-BUNDLE-1", "root_ref": root_ref,
            "root_address_id": root.address_id, "context_refs": context_refs,
            "events": events, "payloads": payloads,
            "index": {"event_count": len(events), "root_ids": [root.address_id],
                      "end_address_ids": [e["after_address_id"] for e in events],
                      "residual_event_seqs": [e["seq"] for e in events if e["residuals_ref"]]},
            "limits": {"profile_rows_added": 0, "proposal_rows_added": 0,
                       "glyph_admission": False, "persistent_save": False}}
    # Address the complete bundle. Size metrics intentionally sit outside the
    # identity body so measurement does not make the bundle identity recursive.
    bundle_id = _sha256_text(_canonical_json(body))
    compact_bytes = len(_canonical_json(body).encode("utf-8"))
    context_bytes = sum(len(_canonical_json(payloads[ref]["value"]).encode("utf-8"))
                        for key, ref in context_refs.items() if key == "root" or key == "cone" or key.startswith("frame:"))
    unique_transition_bytes = sum(len(_canonical_json(payloads[ref]["value"]).encode("utf-8"))
                                  for ref in {e["delta_ref"] for e in events} | {e["operations_ref"] for e in events}
                                  | {e["residuals_ref"] for e in events if e["residuals_ref"]})
    return {**body, "bundle_id": bundle_id,
        "metrics": {"compact_bundle_body_bytes": compact_bytes,
                    "naive_repeated_context_bytes": naive_bytes,
                    "shared_context_payload_bytes": context_bytes,
                    "unique_transition_payload_bytes": unique_transition_bytes,
                    "payload_object_count": len(payloads),
                    "deduplicated_bytes_estimate": max(0, naive_bytes - compact_bytes),
                    "event_count": len(events)}}


def reopen_shared_context_event_bundle(bundle: Mapping[str, Any],
                                        materialize_address_ids: Sequence[str] = ()) -> dict[str, Any]:
    """Verify payload addresses, restore transitions from deltas and replay operations."""
    try:
        if not isinstance(bundle, Mapping) or bundle.get("schema") != "BC-SHARED-CONTEXT-EVENT-BUNDLE-1":
            raise ValueError("shared_bundle_schema_invalid")
        body = {k: v for k, v in bundle.items() if k not in {"bundle_id", "metrics"}}
        actual_id = _sha256_text(_canonical_json(body))
        if actual_id != bundle.get("bundle_id"):
            raise ValueError("shared_bundle_content_address_mismatch")
        payloads = bundle.get("payloads")
        if not isinstance(payloads, Mapping):
            raise ValueError("shared_bundle_payload_store_required")
        for ref, item in payloads.items():
            if not isinstance(item, Mapping) or "kind" not in item or "value" not in item:
                raise ValueError("shared_bundle_payload_record_invalid")
            expect = _sha256_text(_canonical_json({"kind": item["kind"], "value": item["value"]}))
            if ref != expect or item.get("sha256") != expect:
                raise ValueError(f"shared_bundle_payload_digest_mismatch:{ref}")
        refs = bundle.get("context_refs", {})
        root_ref = bundle.get("root_ref")
        if root_ref != refs.get("root") or root_ref not in payloads or payloads[root_ref]["kind"] != "full_address":
            raise ValueError("shared_bundle_root_reference_invalid")
        root = BCFloorAddress.from_dict(payloads[root_ref]["value"])
        if root.address_id != bundle.get("root_address_id"):
            raise ValueError("shared_bundle_root_address_mismatch")
        cone_ref = refs.get("cone")
        if cone_ref is not None:
            if cone_ref not in payloads or payloads[cone_ref]["kind"] != "depth_wave_cone":
                raise ValueError("shared_bundle_cone_reference_invalid")
            if payloads[cone_ref]["value"].get("root_address_id") != root.address_id:
                raise ValueError("shared_bundle_cone_root_mismatch")
            typed_cone = _scb_depth_wave_cone_from_dict(payloads[cone_ref]["value"])
            if not reopen_depth_wave_cone(root, typed_cone).pass_all:
                raise ValueError("shared_bundle_cone_reopen_failed")
        if not isinstance(materialize_address_ids, (tuple, list)) or not all(isinstance(x, str) for x in materialize_address_ids):
            raise TypeError("shared_bundle_materialize_address_id_sequence_required")
        states: dict[str, BCFloorAddress] = {root.address_id: root}
        end_event_for_state: dict[str, int] = {root.address_id: -1}
        events = bundle.get("events", [])
        for seq, event in enumerate(events):
            if event.get("seq") != seq:
                raise ValueError("shared_bundle_sequence_gap")
            before_id = event.get("before_address_id")
            start = states.get(before_id)
            if start is None:
                raise ValueError(f"shared_bundle_before_state_unavailable:{seq}")
            parent = event.get("parent_event")
            expected_parent = end_event_for_state.get(before_id, -1)
            if parent != (None if expected_parent < 0 else expected_parent):
                raise ValueError(f"shared_bundle_parent_link_mismatch:{seq}")
            delta_ref, ops_ref = event.get("delta_ref"), event.get("operations_ref")
            if delta_ref not in payloads or payloads[delta_ref]["kind"] != "address_delta":
                raise ValueError(f"shared_bundle_delta_reference_invalid:{seq}")
            if ops_ref not in payloads or payloads[ops_ref]["kind"] != "address_operations":
                raise ValueError(f"shared_bundle_operations_reference_invalid:{seq}")
            d = payloads[delta_ref]["value"]
            delta = AddressDelta(str(d["schema"]), str(d["parent_id"]), str(d["end_id"]),
                                 tuple(d["changes"]), str(d["difference_address"]))
            if delta.parent_id != before_id or delta.end_id != event.get("after_address_id"):
                raise ValueError(f"shared_bundle_delta_binding_mismatch:{seq}")
            end_via_delta = delta.apply(start)
            if end_via_delta.address_id != event.get("after_address_id"):
                raise ValueError(f"shared_bundle_delta_end_mismatch:{seq}")
            # Apply alone verifies transport; re-execution independently verifies
            # the operation trace and canonical witness identity.
            ops = [_scb_operation_from_dict(op) for op in payloads[ops_ref]["value"]]
            replay = FULL_ADDRESS_KERNEL.execute(start, ops)
            if replay.end.address_id != end_via_delta.address_id:
                raise ValueError(f"shared_bundle_operation_delta_disagreement:{seq}")
            if _canonical_json(_scb_delta_dict(replay.delta)) != _canonical_json(d):
                raise ValueError(f"shared_bundle_replayed_delta_mismatch:{seq}")
            if replay.witness_id != event.get("witness_id") or len(replay.events) != event.get("operation_count"):
                raise ValueError(f"shared_bundle_witness_replay_mismatch:{seq}")
            flags = (replay.dependency_closed == event.get("dependency_closed") and
                     replay.return_to_entry_closed == event.get("return_to_entry_closed") and
                     replay.difference_replays == event.get("difference_replays") and
                     list(replay.unresolved) == event.get("unresolved"))
            if not flags or not replay.difference_replays or replay.unresolved:
                raise ValueError(f"shared_bundle_witness_flags_mismatch:{seq}")
            rr = event.get("residuals_ref")
            if rr is not None and (rr not in payloads or payloads[rr]["kind"] != "residuals"):
                raise ValueError(f"shared_bundle_residual_reference_invalid:{seq}")
            states[replay.end.address_id] = replay.end
            end_event_for_state[replay.end.address_id] = seq
        missing_targets = sorted(set(materialize_address_ids) - set(states))
        if missing_targets:
            raise ValueError("shared_bundle_materialize_target_unreachable:" + ",".join(missing_targets))
        materialized = {target: states[target].as_dict() for target in sorted(set(materialize_address_ids))}
        return {"schema": "BC-SHARED-CONTEXT-EVENT-BUNDLE-REOPEN-1", "pass": True,
                "bundle_id": bundle.get("bundle_id"), "event_count": len(events),
                "payload_count": len(payloads), "root_address_reopened": root.address_id,
                "replayed_end_addresses": [e["after_address_id"] for e in events],
                "address_index": {"root": root.address_id, "event_ends": [
                    {"seq":e["seq"], "address_id":e["after_address_id"]} for e in events]},
                "all_deltas_applied": True, "all_operations_replayed": True,
                "full_intermediate_address_payloads_stored": False,
                "materialized_address_ids": sorted(materialized),
                "materialized_addresses": materialized,
                "context_stored_once": True, "glyph_admission": False, "persistent_save": False}
    except (KeyError, TypeError, ValueError, LookupError) as exc:
        return {"schema": "BC-SHARED-CONTEXT-EVENT-BUNDLE-REOPEN-1", "pass": False,
                "reason": f"{type(exc).__name__}:{exc}"}


def open_shared_context_event_bundle_address(bundle: Mapping[str, Any], address_id: str) -> dict[str, Any]:
    """Retrieve one complete address payload from the compact shared-context event stream."""
    if not isinstance(address_id, str) or not address_id:
        raise TypeError("shared_bundle_address_id_required")
    receipt = reopen_shared_context_event_bundle(bundle, (address_id,))
    if not receipt.get("pass"):
        raise ValueError("shared_bundle_address_open_failed:" + str(receipt.get("reason")))
    payload = receipt["materialized_addresses"][address_id]
    restored = BCFloorAddress.from_dict(payload)
    if restored.address_id != address_id:
        raise ValueError("shared_bundle_materialized_address_id_mismatch")
    return {"schema":"BC-SHARED-CONTEXT-ADDRESS-OPEN-1", "pass":True,
        "bundle_id":bundle.get("bundle_id"), "address_id":address_id,
        "payload":payload, "reconstructed_by_delta_and_operation_replay":True,
        "address_payload_is_actual_data":True, "retrieval_address_is_not_payload":True}



# ---------------------------------------------------------------------------
# Bounded, checkpointed shared-context event segments.
# Shared root/cone/frame payloads are stored once in the collection; each segment
# stores exact event evidence and only those checkpoint states needed at its boundary.
# ---------------------------------------------------------------------------

def _scs_checkpoint(address: BCFloorAddress, last_event_seq: int | None, root_id: str) -> dict[str, Any]:
    payload = address.as_dict()
    state_ref = "shared_root" if address.address_id == root_id else None
    body = {"address_id": address.address_id, "state_ref": state_ref,
            "payload": None if state_ref else payload, "last_event_seq": last_event_seq,
            "payload_sha256": _sha256_text(_canonical_json(payload))}
    return body


def _scs_event_estimated_bytes(witness: FullAddressWitness, glyph_ref: str, residuals: Sequence[str]) -> int:
    # Conservative planner cost: include full start/end payload estimates even though
    # the actual segment stores only delta/operation evidence plus boundary checkpoints.
    sample = {"start": witness.start.as_dict(), "end": witness.end.as_dict(),
              "delta": _scb_delta_dict(witness.delta), "operations": _scb_json_value(witness.events),
              "glyph_ref": glyph_ref, "residuals": list(residuals)}
    return len(_canonical_json(sample).encode("utf-8")) + 512


def build_shared_context_event_segments(
    root: BCFloorAddress,
    witnesses: Sequence[FullAddressWitness],
    *, max_events_per_segment: int = 128, max_segment_bytes: int = 4 * 1024 * 1024,
    cone: DepthWaveCone | None = None, frames: Mapping[str, Any] | None = None,
    glyph_refs: Sequence[str] | None = None, residuals: Sequence[Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Build bounded event segments with complete replay evidence and address checkpoints.

    Chunking bounds per-segment event counts and normally serialized size. A single
    evidence event larger than the byte budget is preserved as an oversize singleton,
    explicitly flagged rather than truncated or dropped.
    """
    if not isinstance(root, BCFloorAddress):
        raise TypeError("segmented_bundle_full_root_address_required")
    if not isinstance(witnesses, (list, tuple)) or not all(isinstance(w, FullAddressWitness) for w in witnesses):
        raise TypeError("segmented_bundle_witness_sequence_required")
    if type(max_events_per_segment) is not int or not 1 <= max_events_per_segment <= 4096:
        raise ValueError("segment_event_limit_must_be_1_to_4096")
    if type(max_segment_bytes) is not int or not 4096 <= max_segment_bytes <= 64 * 1024 * 1024:
        raise ValueError("segment_byte_budget_must_be_4096_to_67108864")
    if cone is not None and (not isinstance(cone, DepthWaveCone) or cone.root_address_id != root.address_id or not reopen_depth_wave_cone(root, cone).pass_all):
        raise ValueError("segmented_bundle_cone_root_or_reopen_invalid")
    n = len(witnesses)
    if glyph_refs is not None and len(glyph_refs) != n:
        raise ValueError("segmented_bundle_glyph_ref_count_mismatch")
    if residuals is not None and len(residuals) != n:
        raise ValueError("segmented_bundle_residual_count_mismatch")
    glyphs = list(glyph_refs) if glyph_refs is not None else ["full_address_execute"] * n
    residual_rows = [list(x) for x in residuals] if residuals is not None else [[] for _ in witnesses]

    # Validate the entire incoming evidence stream first and compute exact state ancestry.
    reachable: dict[str, BCFloorAddress] = {root.address_id: root}
    last_event_by_state: dict[str, int | None] = {root.address_id: None}
    for seq, witness in enumerate(witnesses):
        if not witness.difference_replays or witness.unresolved:
            raise ValueError(f"segmented_bundle_unreplayed_witness:{seq}")
        state = reachable.get(witness.start.address_id)
        if state is None or state != witness.start:
            raise ValueError(f"segmented_bundle_event_start_unreachable_or_mismatched:{seq}")
        ops = [_scb_operation_from_dict(row["operation"]) for row in witness.events]
        if FULL_ADDRESS_KERNEL.execute(witness.start, ops) != witness:
            raise ValueError(f"segmented_bundle_witness_rebuild_mismatch:{seq}")
        reachable[witness.end.address_id] = witness.end
        last_event_by_state[witness.end.address_id] = seq

    shared_payloads: dict[str, Any] = {}
    root_ref = _scb_put(shared_payloads, "full_address", root.as_dict())
    context_refs: dict[str, str] = {"root": root_ref}
    if cone is not None:
        context_refs["cone"] = _scb_put(shared_payloads, "depth_wave_cone", cone.as_dict())
    for name, frame in sorted((frames or {}).items()):
        if not isinstance(name, str) or not name:
            raise ValueError("segmented_bundle_frame_name_required")
        frame_data = _scb_json_value(frame)
        source_id = frame_data.get("source_address_id") or frame_data.get("root_address_id")
        if source_id is not None and source_id != root.address_id:
            raise ValueError(f"segmented_bundle_frame_root_mismatch:{name}")
        context_refs[f"frame:{name}"] = _scb_put(shared_payloads, "addressed_frame", frame_data)

    # Greedy deterministic boundaries on event count and conservative per-event size.
    ranges: list[tuple[int, int, int]] = []
    i = 0
    while i < n:
        j = i
        estimate = 0
        while j < n and (j - i) < max_events_per_segment:
            cost = _scs_event_estimated_bytes(witnesses[j], glyphs[j], residual_rows[j])
            if j > i and estimate + cost > max_segment_bytes:
                break
            estimate += cost
            j += 1
            if estimate >= max_segment_bytes:  # event may be an oversize singleton
                break
        if j == i:
            j = i + 1
            estimate = _scs_event_estimated_bytes(witnesses[i], glyphs[i], residual_rows[i])
        ranges.append((i, j, estimate))
        i = j

    segments: list[dict[str, Any]] = []
    global_last: dict[str, int | None] = {root.address_id: None}
    previous_segment_id: str | None = None
    event_end_ids: list[str] = []
    residual_event_seqs: list[int] = []
    for seg_idx, (start_seq, stop_seq, estimate) in enumerate(ranges):
        payloads: dict[str, Any] = {}
        local_states: dict[str, BCFloorAddress] = {root.address_id: root}
        local_last: dict[str, int | None] = {root.address_id: global_last.get(root.address_id)}
        checkpoints: dict[str, Any] = {}
        events: list[dict[str, Any]] = []
        for seq in range(start_seq, stop_seq):
            witness = witnesses[seq]
            before_id = witness.start.address_id
            if before_id not in local_states:
                # Full checkpoint is an actual payload. Its last event binds it to
                # already-replayed evidence in a prior segment; root uses shared payload.
                checkpoint = _scs_checkpoint(witness.start, global_last.get(before_id), root.address_id)
                checkpoints.setdefault(before_id, checkpoint)
                local_states[before_id] = witness.start
                local_last[before_id] = global_last.get(before_id)
            if local_states[before_id] != witness.start:
                raise ValueError(f"segmented_bundle_checkpoint_state_mismatch:{seq}")
            parent_event = local_last.get(before_id)
            delta_ref = _scb_put(payloads, "address_delta", _scb_delta_dict(witness.delta))
            trace_ref = _scb_put(payloads, "address_witness_trace", _scb_json_value(witness.events))
            residual_ref = _scb_put(payloads, "residuals", residual_rows[seq]) if residual_rows[seq] else None
            event = {"seq":seq,"glyph_ref":glyphs[seq],
                "parent_event":parent_event,"before_address_id":before_id,"after_address_id":witness.end.address_id,
                "delta_ref":delta_ref,"witness_trace_ref":trace_ref,"operation_count":len(witness.events),
                "witness_id":witness.witness_id,"dependency_closed":witness.dependency_closed,
                "return_to_entry_closed":witness.return_to_entry_closed,"difference_replays":witness.difference_replays,
                "unresolved":list(witness.unresolved),"residuals_ref":residual_ref}
            events.append(event)
            local_states[witness.end.address_id] = witness.end
            local_last[witness.end.address_id] = seq
            global_last[witness.end.address_id] = seq
            event_end_ids.append(witness.end.address_id)
            if residual_ref is not None: residual_event_seqs.append(seq)
        seg_body = {"schema":"BC-SHARED-CONTEXT-EVENT-SEGMENT-1","segment_index":seg_idx,
            "seq_start":start_seq,"seq_end_exclusive":stop_seq,"previous_segment_id":previous_segment_id,
            "checkpoint_states":{k:checkpoints[k] for k in sorted(checkpoints)},
            "events":events,"payloads":payloads,
            "limits":{"max_events_per_segment":max_events_per_segment,"max_segment_bytes":max_segment_bytes,
                "estimated_payload_bytes":estimate,"oversize_event_singleton":(stop_seq-start_seq==1 and estimate>max_segment_bytes)}}
        segment_id = _sha256_text(_canonical_json(seg_body))
        segment = {**seg_body,"segment_id":segment_id}
        # Metrics are outside the segment identity; iterate their byte count to a fixed point.
        actual_segment_bytes = len(_canonical_json(segment).encode("utf-8"))
        for _ in range(4):
            segment["metrics"] = {"serialized_segment_bytes":actual_segment_bytes,
                "actual_segment_exceeds_byte_budget":actual_segment_bytes > max_segment_bytes}
            measured = len(_canonical_json(segment).encode("utf-8"))
            if measured == actual_segment_bytes:
                break
            actual_segment_bytes = measured
        segment["metrics"] = {"serialized_segment_bytes":actual_segment_bytes,
            "actual_segment_exceeds_byte_budget":actual_segment_bytes > max_segment_bytes}
        segments.append(segment)
        previous_segment_id = segment_id

    body = {"schema":"BC-SHARED-CONTEXT-EVENT-SEGMENTS-1","root_address_id":root.address_id,
        "root_ref":root_ref,"context_refs":context_refs,"shared_payloads":shared_payloads,
        "segments":segments,"index":{"segment_count":len(segments),"event_count":n,
            "event_end_address_ids":event_end_ids,"residual_event_seqs":residual_event_seqs,
            "segment_ids":[x["segment_id"] for x in segments]},
        "limits":{"max_events_per_segment":max_events_per_segment,"max_segment_bytes":max_segment_bytes,
            "profile_rows_added":0,"proposal_rows_added":0,"glyph_admission":False,"persistent_save":False,
            "full_event_evidence_retained":True,"single_large_event_is_preserved_and_flagged":True}}
    collection_id = _sha256_text(_canonical_json(body))
    raw_size = len(_canonical_json({k:v for k,v in body.items() if k!="segments"}).encode("utf-8")) + sum(len(_canonical_json(x).encode("utf-8")) for x in segments)
    full_naive_bytes = sum(len(_canonical_json({"root":root.as_dict(),"cone":None if cone is None else cone.as_dict(),
        "frames":_scb_json_value(frames or {}),"start":w.start.as_dict(),"end":w.end.as_dict(),
        "delta":_scb_delta_dict(w.delta),"events":_scb_json_value(w.events),"glyph_ref":glyphs[idx],
        "residuals":residual_rows[idx]}).encode("utf-8")) for idx,w in enumerate(witnesses))
    serialized_bytes = len(_canonical_json({**body,"collection_id":collection_id}).encode("utf-8"))
    return {**body,"collection_id":collection_id,"metrics":{"serialized_collection_bytes":serialized_bytes,
        "naive_repeated_context_bytes":full_naive_bytes,"bytes_avoided_estimate":max(0,full_naive_bytes-serialized_bytes),
        "segment_serialized_bytes_sum":sum(len(_canonical_json(x).encode("utf-8")) for x in segments),
        "max_actual_segment_bytes":max((x["metrics"]["serialized_segment_bytes"] for x in segments),default=0),
        "oversize_segment_count":sum(1 for x in segments if x["metrics"]["actual_segment_exceeds_byte_budget"]),
        "event_count":n,"segment_count":len(segments),"full_evidence_retained":True}}


def reopen_shared_context_event_segments(collection: Mapping[str, Any],
        materialize_address_ids: Sequence[str] = ()) -> dict[str, Any]:
    """Replay bounded segments independently using authenticated checkpoints and a compact end index."""
    try:
        if not isinstance(collection, Mapping) or collection.get("schema") != "BC-SHARED-CONTEXT-EVENT-SEGMENTS-1":
            raise ValueError("segmented_bundle_schema_invalid")
        body = {k:v for k,v in collection.items() if k not in {"collection_id","metrics"}}
        if _sha256_text(_canonical_json(body)) != collection.get("collection_id"):
            raise ValueError("segmented_bundle_content_address_mismatch")
        if not isinstance(materialize_address_ids,(list,tuple)) or not all(isinstance(x,str) for x in materialize_address_ids):
            raise TypeError("segmented_bundle_materialize_ids_required")
        shared = collection.get("shared_payloads")
        if not isinstance(shared,Mapping): raise ValueError("segmented_bundle_shared_payloads_invalid")
        for ref,item in shared.items():
            if not isinstance(item,Mapping) or ref != _sha256_text(_canonical_json({"kind":item.get("kind"),"value":item.get("value")})) or item.get("sha256") != ref:
                raise ValueError("segmented_bundle_shared_payload_digest_mismatch")
        root_ref=collection.get("root_ref")
        if root_ref not in shared or shared[root_ref].get("kind")!="full_address": raise ValueError("segmented_bundle_root_ref_invalid")
        root=BCFloorAddress.from_dict(shared[root_ref]["value"])
        if root.address_id != collection.get("root_address_id"): raise ValueError("segmented_bundle_root_binding_mismatch")
        context_refs=collection.get("context_refs",{})
        if context_refs.get("root")!=root_ref: raise ValueError("segmented_bundle_context_root_mismatch")
        cone_ref=context_refs.get("cone")
        if cone_ref is not None:
            if cone_ref not in shared or shared[cone_ref].get("kind")!="depth_wave_cone": raise ValueError("segmented_bundle_cone_ref_invalid")
            cone=_scb_depth_wave_cone_from_dict(shared[cone_ref]["value"])
            if not reopen_depth_wave_cone(root,cone).pass_all: raise ValueError("segmented_bundle_cone_reopen_failed")
        # Validate immutable frames against the one shared root.
        for name,ref in context_refs.items():
            if name.startswith("frame:"):
                if ref not in shared or shared[ref].get("kind")!="addressed_frame": raise ValueError("segmented_bundle_frame_ref_invalid")
                data=shared[ref]["value"]
                sid=data.get("source_address_id") or data.get("root_address_id")
                if sid is not None and sid!=root.address_id: raise ValueError("segmented_bundle_frame_root_mismatch")
        segments=collection.get("segments")
        index=collection.get("index",{})
        if not isinstance(segments,list) or len(segments)!=index.get("segment_count"): raise ValueError("segmented_bundle_segment_count_mismatch")
        end_index=index.get("event_end_address_ids")
        if not isinstance(end_index,list) or len(end_index)!=index.get("event_count"): raise ValueError("segmented_bundle_event_index_length_mismatch")
        replayed_end_ids=[]; requested=set(materialize_address_ids); materialized={}
        prior_segment_id=None; expected_seq=0; root_payload=shared[root_ref]["value"]
        for seg_idx,segment in enumerate(segments):
            if not isinstance(segment,Mapping) or segment.get("schema")!="BC-SHARED-CONTEXT-EVENT-SEGMENT-1": raise ValueError("segmented_bundle_segment_schema_invalid")
            seg_body={k:v for k,v in segment.items() if k not in {"segment_id","metrics"}}
            segid=_sha256_text(_canonical_json(seg_body))
            if segid!=segment.get("segment_id"): raise ValueError(f"segmented_bundle_segment_digest_mismatch:{seg_idx}")
            if segment.get("segment_index")!=seg_idx or segment.get("previous_segment_id")!=prior_segment_id: raise ValueError("segmented_bundle_segment_chain_mismatch")
            if segment.get("seq_start")!=expected_seq: raise ValueError("segmented_bundle_segment_sequence_start_mismatch")
            payloads=segment.get("payloads")
            if not isinstance(payloads,Mapping): raise ValueError("segmented_bundle_segment_payloads_invalid")
            for ref,item in payloads.items():
                if not isinstance(item,Mapping) or ref != _sha256_text(_canonical_json({"kind":item.get("kind"),"value":item.get("value")})) or item.get("sha256")!=ref:
                    raise ValueError(f"segmented_bundle_payload_digest_mismatch:{seg_idx}")
            states:dict[str,BCFloorAddress]={}
            last_by_state:dict[str,int|None]={}
            checkpoints=segment.get("checkpoint_states",{})
            for aid,cp in checkpoints.items():
                if cp.get("address_id")!=aid: raise ValueError("segmented_bundle_checkpoint_id_mismatch")
                payload=root_payload if cp.get("state_ref")=="shared_root" else cp.get("payload")
                if not isinstance(payload,Mapping) or _sha256_text(_canonical_json(payload))!=cp.get("payload_sha256"): raise ValueError("segmented_bundle_checkpoint_payload_digest_mismatch")
                typed=BCFloorAddress.from_dict(payload)
                if typed.address_id!=aid: raise ValueError("segmented_bundle_checkpoint_address_binding_mismatch")
                lastseq=cp.get("last_event_seq")
                if lastseq is None:
                    if aid!=root.address_id: raise ValueError("segmented_bundle_nonroot_checkpoint_missing_origin")
                else:
                    if type(lastseq)is not int or lastseq < 0 or lastseq >= expected_seq or end_index[lastseq]!=aid:
                        raise ValueError("segmented_bundle_checkpoint_not_bound_to_prior_replay")
                states[aid]=typed; last_by_state[aid]=lastseq
            # Root is always available in the shared context. A branch that returns
            # to it after a prior event must use a checkpoint with its latest event index.
            if root.address_id not in states:
                states[root.address_id]=root; last_by_state[root.address_id]=None
            events=segment.get("events",[])
            if not isinstance(events,list): raise ValueError("segmented_bundle_events_invalid")
            if not events and segment.get("seq_end_exclusive")!=expected_seq: raise ValueError("segmented_bundle_empty_segment_invalid")
            for event in events:
                seq=event.get("seq")
                if seq!=expected_seq: raise ValueError("segmented_bundle_event_sequence_gap")
                before=event.get("before_address_id"); start=states.get(before)
                if start is None: raise ValueError(f"segmented_bundle_checkpoint_missing_for_start:{seq}")
                if event.get("parent_event")!=last_by_state.get(before): raise ValueError(f"segmented_bundle_parent_event_mismatch:{seq}")
                dr,tr=event.get("delta_ref"),event.get("witness_trace_ref")
                if dr not in payloads or payloads[dr].get("kind")!="address_delta": raise ValueError("segmented_bundle_delta_ref_invalid")
                if tr not in payloads or payloads[tr].get("kind")!="address_witness_trace": raise ValueError("segmented_bundle_witness_trace_ref_invalid")
                d=payloads[dr]["value"]
                trace=payloads[tr]["value"]
                if not isinstance(trace,list) or not all(isinstance(row,Mapping) and "operation" in row for row in trace):
                    raise ValueError("segmented_bundle_witness_trace_invalid")
                delta=AddressDelta(str(d["schema"]),str(d["parent_id"]),str(d["end_id"]),tuple(d["changes"]),str(d["difference_address"]))
                end_delta=delta.apply(start)
                if end_delta.address_id!=event.get("after_address_id"): raise ValueError("segmented_bundle_delta_end_mismatch")
                ops=[_scb_operation_from_dict(x["operation"]) for x in trace]
                replay=FULL_ADDRESS_KERNEL.execute(start,ops)
                if replay.end!=end_delta or _canonical_json(_scb_delta_dict(replay.delta))!=_canonical_json(d): raise ValueError("segmented_bundle_delta_operation_disagreement")
                if _canonical_json(_scb_json_value(replay.events))!=_canonical_json(trace): raise ValueError("segmented_bundle_full_trace_disagreement")
                if replay.witness_id!=event.get("witness_id") or len(replay.events)!=event.get("operation_count"): raise ValueError("segmented_bundle_witness_identity_mismatch")
                if not replay.difference_replays or replay.unresolved or replay.dependency_closed!=event.get("dependency_closed") or replay.return_to_entry_closed!=event.get("return_to_entry_closed") or list(replay.unresolved)!=event.get("unresolved"):
                    raise ValueError("segmented_bundle_witness_replay_flags_mismatch")
                rr=event.get("residuals_ref")
                if rr is not None and (rr not in payloads or payloads[rr].get("kind")!="residuals"): raise ValueError("segmented_bundle_residual_ref_invalid")
                states[replay.end.address_id]=replay.end; last_by_state[replay.end.address_id]=seq
                replayed_end_ids.append(replay.end.address_id)
                if replay.end.address_id in requested: materialized[replay.end.address_id]=replay.end.as_dict()
                expected_seq+=1
            if segment.get("seq_end_exclusive")!=expected_seq: raise ValueError("segmented_bundle_segment_sequence_end_mismatch")
            prior_segment_id=segid
        if expected_seq!=index.get("event_count") or replayed_end_ids!=end_index: raise ValueError("segmented_bundle_final_event_index_mismatch")
        missing=sorted(requested-set(materialized)-{root.address_id})
        if root.address_id in requested: materialized[root.address_id]=root.as_dict()
        if missing: raise ValueError("segmented_bundle_materialize_target_unreachable:"+",".join(missing))
        if index.get("segment_ids")!=[x.get("segment_id") for x in segments]: raise ValueError("segmented_bundle_index_segment_ids_mismatch")
        return {"schema":"BC-SHARED-CONTEXT-EVENT-SEGMENTS-REOPEN-1","pass":True,
            "collection_id":collection.get("collection_id"),"segment_count":len(segments),"event_count":expected_seq,
            "all_deltas_applied":True,"all_operations_replayed":True,"checkpoint_chain_reopened":True,
            "full_event_evidence_retained":True,"materialized_address_ids":sorted(materialized),
            "materialized_addresses":materialized,"profile_rows_added":0,"proposal_rows_added":0,"glyph_admission":False}
    except (KeyError,TypeError,ValueError,LookupError) as exc:
        return {"schema":"BC-SHARED-CONTEXT-EVENT-SEGMENTS-REOPEN-1","pass":False,"reason":f"{type(exc).__name__}:{exc}"}


def open_shared_context_event_segments_address(collection: Mapping[str, Any], address_id: str) -> dict[str, Any]:
    if not isinstance(address_id,str) or not address_id: raise TypeError("segmented_bundle_address_id_required")
    receipt=reopen_shared_context_event_segments(collection,(address_id,))
    if not receipt.get("pass"): raise ValueError("segmented_bundle_address_open_failed:"+str(receipt.get("reason")))
    return {"schema":"BC-SHARED-CONTEXT-SEGMENTED-ADDRESS-OPEN-1","pass":True,
        "collection_id":collection.get("collection_id"),"address_id":address_id,
        "payload":receipt["materialized_addresses"][address_id],"reconstructed_from_checkpoint_delta_and_operation_replay":True,
        "retrieval_address_is_not_payload":True}

def _pc_tokens(value: str) -> set[str]:
    raw = set(re.findall(r"[a-z0-9]+", value.lower()))
    aliases = {"hf": {"harmonic", "fractal", "center"},
               "h504": {"harmonic", "sphere504", "prime"},
               "1hot": {"onehot", "wave", "address"},
               "rpm": {"prime", "lane", "rate"},
               "hallway": {"structuralizer", "difference", "perspective"},
               "cone": {"depth", "wave", "recursive"},
               "gcd": {"magnitude", "normalize", "scale"}}
    expanded = set(raw)
    for token in tuple(raw):
        expanded.update(aliases.get(token, ()))
    return expanded


def _pc_glyph_profiles() -> list[dict[str, Any]]:
    profiles = []
    for spec in GLYPH_CATALOG.describe():
        words = " ".join([spec.get("name", ""), spec.get("executor", ""),
                          spec.get("witness_contract", ""),
                          " ".join(f"{k} {v}" for k, v in spec.get("arg_types", {}).items())])
        profiles.append({"name": spec["name"], "address": spec["address"],
                         "executor": spec["executor"], "effect_scope": spec["effect_scope"],
                         "required_args": list(spec.get("required_args", [])),
                         "arg_types": dict(spec.get("arg_types", {})), "tokens": sorted(_pc_tokens(words))})
    return profiles


def build_fractal_hallway_predictor_cone(
    address: BCFloorAddress,
    cone: DepthWaveCone,
    workloads: Sequence[Mapping[str, Any]],
    *,
    top_k: int = 5,
) -> dict[str, Any]:
    """Estimate known-glyph fit and route potential workload requests through opened hallways.

    Scores are integer coverage indicators for planning only; they are not floor state,
    probability, semantic certification, or glyph-admission decisions.
    """
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("predictor_requires_address_and_depth_wave_cone")
    if cone.root_address_id != address.address_id or not reopen_depth_wave_cone(address, cone).pass_all:
        raise ValueError("predictor_source_cone_not_reopened")
    if type(top_k) is not int or not 1 <= top_k <= 32:
        raise ValueError("predictor_top_k_out_of_range")
    if not isinstance(workloads, (list, tuple)):
        raise TypeError("predictor_workload_sequence_required")

    glyphs = _pc_glyph_profiles()
    glyph_by_name = {g["name"]: g for g in glyphs}
    catalogue_digest = _sha256_text(_canonical_json([{k: v for k, v in g.items() if k != "tokens"} for g in glyphs]))
    hallway_rows = [{"child_address_id": address.address_id, "payload_address_id": None, "depth": 0,
        "level_index": None, "box_slot_position": None, "side": None, "path": [],
        "box_aperture_address": BOX_APERTURE_216.address_id,
        "cube_aperture_address": CUBE_APERTURE_216.address_id,
        "same_cardinality_does_not_merge_families": True, "root_fallback": True}]
    for child in cone.child_addresses:
        hallway_rows.append({"child_address_id": child.address_id, "payload_address_id": child.payload_address_id,
            "depth": child.recursion_depth, "level_index": child.level_index, "box_slot_position": child.box_slot_position,
            "side": child.side, "path": list(child.path), "box_aperture_address": child.box_aperture_address,
            "cube_aperture_address": child.cube_aperture_address,
            "same_cardinality_does_not_merge_families": child.box_aperture_address != child.cube_aperture_address})

    predictions = []
    for idx, raw in enumerate(workloads):
        if not isinstance(raw, Mapping):
            raise TypeError(f"predictor_workload_{idx}_must_be_mapping")
        wid = str(raw.get("workload_id", f"w{idx}"))
        tags = sorted({str(x).lower() for x in raw.get("tags", raw.get("required_tags", ()))})
        demanded_types = {str(k): str(v) for k, v in dict(raw.get("required_arg_types", {})).items()}
        demanded_effect = raw.get("effect_scope")
        if demanded_effect is not None and not isinstance(demanded_effect, str):
            raise TypeError("predictor_effect_scope_must_be_string")
        rank = raw.get("dimension_rank")
        if rank is not None and (type(rank) is not int or rank not in (1, 2, 3)):
            raise ValueError("predictor_dimension_rank_must_be_1_2_or_3")
        target_depth = raw.get("target_depth", 0)
        if type(target_depth) is not int or target_depth < 0:
            raise ValueError("predictor_target_depth_must_be_nonnegative_integer")
        aperture = raw.get("aperture_family", "box")
        if aperture not in ("box", "cube"):
            raise ValueError("predictor_aperture_family_must_be_box_or_cube")
        requested_glyph_chain = [str(x) for x in raw.get("required_glyphs", ())]
        missing_glyph_chain = [name for name in requested_glyph_chain if name not in glyph_by_name]
        tag_sets = {tag: _pc_tokens(tag) for tag in tags}
        candidate_rows = []
        for g in glyphs:
            gt = set(g["tokens"])
            tag_hits = [tag for tag, expanded in tag_sets.items() if gt.intersection(expanded)]
            type_hits = [k for k in sorted(demanded_types) if g["arg_types"].get(k) == demanded_types[k]]
            type_misses = [k for k in sorted(demanded_types) if g["arg_types"].get(k) != demanded_types[k]]
            required_unprovided = [k for k in g.get("required_args", []) if k not in demanded_types]
            effect_ok = demanded_effect is None or g["effect_scope"] == demanded_effect
            exact_ok = not requested_glyph_chain or g["name"] in requested_glyph_chain
            # Score only available evidence. A name-token hit is a lead, never proof.
            weights = []
            values = []
            if tags:
                weights.append(3500); values.append(10000 * len(tag_hits) // len(tags))
            if demanded_types:
                type_fit = 10000 * len(type_hits) // len(demanded_types)
                type_fit = type_fit * max(0, 10000 - 2500 * len(required_unprovided)) // 10000
                weights.append(3500); values.append(type_fit)
            if demanded_effect is not None:
                weights.append(1000); values.append(10000 if effect_ok else 0)
            hallway_available = target_depth == 0 or any(h["depth"] == target_depth for h in hallway_rows)
            if target_depth > 0 or rank is not None or aperture:
                weights.append(2000); values.append(10000 if hallway_available and (rank is None or rank in (1,2,3)) else 0)
            if not weights:
                weights, values = [10000], [0]
            score = sum(w * v for w, v in zip(weights, values)) // sum(weights)
            candidate_rows.append({"glyph": g["name"], "glyph_address": g["address"], "executor": g["executor"],
                "contract_coverage_bps": score, "matched_tags": tag_hits, "unmatched_tags": [x for x in tags if x not in tag_hits],
                "matched_input_types": type_hits, "unmatched_input_types": type_misses,
                "unprovided_required_inputs": required_unprovided, "effect_match": effect_ok, "required_glyph_constraint_match": exact_ok,
                "interpretation": "ranked candidate only; executable semantics require separate witness tests"})
        # If a workload names its intended chain, show those named members first;
        # name presence alone is not typed-composition certification.
        candidate_rows.sort(key=lambda g: (
            -int(bool(requested_glyph_chain) and g["required_glyph_constraint_match"]),
            -g["contract_coverage_bps"], g["glyph"]))
        available_depths = [h["depth"] for h in hallway_rows]
        route = next((h for h in hallway_rows if h["depth"] == target_depth), None)
        route_residuals = []
        requested_depth_open = route is not None
        if route is None:
            # Never route deeper than the request or the actually opened structure.
            supported = [h for h in hallway_rows if h["depth"] <= target_depth]
            route = max(supported, key=lambda h: h["depth"]) if supported else hallway_rows[0]
            route_residuals.append("requested_fractal_depth_not_open_in_cone")
        if not cone.dependency_closed:
            route_residuals.append("cone_dependency_not_closed")
        if not cone.local_state_spaces_closed:
            route_residuals.append("cone_local_state_space_not_closed")
        if rank in (1, 2):
            route_residuals.append("omitted_dimensions_must_remain_residuals")
        route_data = {**route, "requested_depth": target_depth,
            "requested_depth_open": requested_depth_open,
            "route_depth_never_exceeds_requested": route["depth"] <= target_depth,
            "maximum_depth_observed_in_opened_cone": max(available_depths, default=0),
            "aperture_family_requested": aperture,
            "aperture_address_selected": route["box_aperture_address"] if aperture == "box" else route["cube_aperture_address"],
            "dimension_rank_requested": rank,
            "available_projection_ranks": [1,2,3] if cone.nodes else [],
            "projection_is_a_view_not_a_new_glyph": True,
            "route_fidelity_bps": (4000 if target_depth in available_depths else 0) +
                                  (2000 if cone.root_address_id == address.address_id else 0) +
                                  (2000 if cone.dependency_closed else 0) +
                                  (2000 if cone.local_state_spaces_closed else 0),
            "residuals": route_residuals}
        for candidate in candidate_rows:
            candidate["hallway_route_ref"] = {"root_address_id": address.address_id,
                "cone_address": cone.cone_address, "child_address_id": route_data["child_address_id"],
                "depth": route_data["depth"], "aperture_family": aperture,
                "aperture_address": route_data["aperture_address_selected"],
                "dimension_rank": rank, "route_fidelity_bps": route_data["route_fidelity_bps"],
                "candidate_only": True}
        event_count = raw.get("expected_events", 0)
        mean_payload = raw.get("mean_event_payload_bytes", 0)
        unique_bps = raw.get("unique_evidence_fraction_bps", 10000)
        repeat_context = raw.get("context_repeated_in_full", True)
        if type(repeat_context) is not bool:
            raise ValueError("predictor_context_repeated_in_full_must_be_boolean")
        if type(event_count) is not int or event_count < 0 or type(mean_payload) is not int or mean_payload < 0:
            raise ValueError("predictor_event_and_payload_estimates_must_be_nonnegative_integers")
        if type(unique_bps) is not int or not 0 <= unique_bps <= 10000:
            raise ValueError("predictor_unique_evidence_fraction_bps_invalid")
        context_bytes = len(_canonical_json(address.as_dict()).encode("utf-8")) + len(_canonical_json(cone.as_dict()).encode("utf-8"))
        event_payload_bytes = event_count * mean_payload
        repeated_context_bytes = event_count * context_bytes if repeat_context else 0
        full_bytes = event_payload_bytes + repeated_context_bytes
        estimated_compact = context_bytes + event_count * (256 + mean_payload * unique_bps // 10000)
        chain_residuals = []
        if requested_glyph_chain:
            chain_residuals.append("required_glyph_chain_composition_not_tested_by_name_matching")
        if missing_glyph_chain:
            chain_residuals.append("required_glyph_chain_contains_unknown_glyph")
        predictions.append({"workload_id": wid, "tags": tags, "requested_arg_types": demanded_types,
            "effect_scope": demanded_effect, "route": route_data,
            "known_glyph_candidates": candidate_rows[:top_k],
            "requested_glyph_chain": requested_glyph_chain,
            "known_glyph_chain_requested": bool(requested_glyph_chain),
            "known_glyph_chain_present": bool(requested_glyph_chain) and not missing_glyph_chain,
            "required_glyph_names_all_registered": bool(requested_glyph_chain) and not missing_glyph_chain,
            "required_glyph_chain_composition_certified": False,
            "missing_glyph_chain": missing_glyph_chain,
            "best_contract_coverage_bps": candidate_rows[0]["contract_coverage_bps"] if candidate_rows else 0,
            "planning_support_bps": ((candidate_rows[0]["contract_coverage_bps"] * 6000 +
                route_data["route_fidelity_bps"] * 4000) // 10000) if candidate_rows else 0,
            "expected_events": event_count, "mean_event_payload_bytes_excluding_shared_context": mean_payload,
            "estimated_event_payload_bytes": event_payload_bytes,
            "estimated_repeated_context_bytes": repeated_context_bytes,
            "estimated_full_export_bytes": full_bytes, "estimated_shared_bundle_bytes": estimated_compact,
            "estimated_bytes_avoided": max(0, full_bytes - estimated_compact),
            "size_estimate_assumptions": {"context_serialized_once": True, "baseline_repeats_context_per_event": repeat_context,
                "shared_context_bytes": context_bytes, "event_reference_overhead_bytes": 256,
                "unique_evidence_fraction_bps": unique_bps,
                "default_is_conservative_full_event_payload_retention": unique_bps == 10000,
                "delta_compaction_beyond_context_is_not_assumed_unless_fraction_supplied": True,
                "not_a_measured_execution_rate": True},
            "residuals": sorted(set(route_residuals + chain_residuals + ([] if candidate_rows and candidate_rows[0]["contract_coverage_bps"] >= 7000 else ["no_high_contract_coverage_known_glyph_match"])))})
    body = {"schema": "BC-FRACTAL-HALLWAY-PREDICTOR-CONE-1", "root_address_id": address.address_id,
        "source_cone_address": cone.cone_address, "catalogue_digest": catalogue_digest,
        "catalogue_count": len(glyphs), "hallways": hallway_rows, "workloads": _scb_json_value(workloads),
        "predictions": predictions,
        "policy": {"floor_state_mutated": False, "profile_rows_added": 0, "proposal_rows_added": 0,
            "glyph_admission": False, "probability_interpretation": False,
            "same_cardinality_box_cube_merge": False, "unknown_depth_stays_residual": True}}
    return {**body, "predictor_cone_address": _sha256_text(_canonical_json(body))}


def reopen_fractal_hallway_predictor_cone(address: BCFloorAddress, cone: DepthWaveCone,
                                           predictor: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(predictor, Mapping):
            raise TypeError("predictor_cone_mapping_required")
        if predictor.get("root_address_id") != address.address_id or predictor.get("source_cone_address") != cone.cone_address:
            raise ValueError("predictor_cone_source_binding_mismatch")
        body = {k:v for k,v in predictor.items() if k != "predictor_cone_address"}
        if _sha256_text(_canonical_json(body)) != predictor.get("predictor_cone_address"):
            raise ValueError("predictor_cone_content_address_mismatch")
        rebuilt = build_fractal_hallway_predictor_cone(address, cone, predictor["workloads"],
            top_k=max(1, max((len(x["known_glyph_candidates"]) for x in predictor["predictions"]), default=1)))
        if rebuilt != predictor:
            raise ValueError("predictor_cone_rebuild_mismatch")
        return {"schema":"BC-FRACTAL-HALLWAY-PREDICTOR-CONE-REOPEN-1", "pass":True,
            "predictor_cone_address":predictor["predictor_cone_address"],
            "workload_count":len(predictor["predictions"]), "catalogue_digest_recomputed":True,
            "hallway_root_binding_reopened":True, "profile_rows_added":0, "proposal_rows_added":0,
            "glyph_admission":False}
    except (KeyError, TypeError, ValueError, LookupError) as exc:
        return {"schema":"BC-FRACTAL-HALLWAY-PREDICTOR-CONE-REOPEN-1", "pass":False,
                "reason":f"{type(exc).__name__}:{exc}"}


REGISTRY.register("build_shared_context_event_bundle", build_shared_context_event_bundle, "pure")
REGISTRY.register("reopen_shared_context_event_bundle", reopen_shared_context_event_bundle, "pure")
REGISTRY.register("open_shared_context_event_bundle_address", open_shared_context_event_bundle_address, "pure")
REGISTRY.register("build_fractal_hallway_predictor_cone", build_fractal_hallway_predictor_cone, "pure")
REGISTRY.register("reopen_fractal_hallway_predictor_cone", reopen_fractal_hallway_predictor_cone, "pure")
for _scb_spec in (
    GlyphSpec.make("BC.BUNDLE.SHARED.OPEN", "build_shared_context_event_bundle",
        ("root", "witnesses"), ("cone", "frames", "glyph_refs", "residuals"),
        {"root":"full_address", "witnesses":"full_address_witness_sequence", "cone":"depth_wave_cone",
         "frames":"addressed_frame_map", "glyph_refs":"glyph_reference_sequence", "residuals":"residual_sequence"},
        "pure", "deduplicate immutable root/cone/frame context; retain deltas, operation traces, witnesses and residual links"),
    GlyphSpec.make("BC.BUNDLE.SHARED.REOPEN", "reopen_shared_context_event_bundle",
        ("bundle",), (), {"bundle":"shared_context_event_bundle"}, "pure",
        "verify content-addressed payloads, apply each exact delta, and replay operation traces to reconstruct full addresses"),
    GlyphSpec.make("BC.BUNDLE.SHARED.ADDRESS", "open_shared_context_event_bundle_address",
        ("bundle", "address_id"), (), {"bundle":"shared_context_event_bundle", "address_id":"address_id"}, "pure",
        "materialize one requested complete address from the compact event stream without exporting every intermediate state"),
    GlyphSpec.make("BC.HALLWAY.PREDICT", "build_fractal_hallway_predictor_cone",
        ("address", "cone", "workloads"), ("top_k",),
        {"address":"full_address", "cone":"depth_wave_cone", "workloads":"potential_workload_sequence", "top_k":"positive_integer"},
        "pure", "rank known glyph candidates and route workload requests through opened recursive hallways with explicit residuals"),
    GlyphSpec.make("BC.HALLWAY.PREDICT.REOPEN", "reopen_fractal_hallway_predictor_cone",
        ("address", "cone", "predictor"), (),
        {"address":"full_address", "cone":"depth_wave_cone", "predictor":"fractal_hallway_predictor_cone"},
        "pure", "rebuild predictor from current glyph catalogue and same opened address cone"),
):
    GLYPH_CATALOG.register(_scb_spec)

REGISTRY.register("build_shared_context_event_segments", build_shared_context_event_segments, "pure")
REGISTRY.register("reopen_shared_context_event_segments", reopen_shared_context_event_segments, "pure")
REGISTRY.register("open_shared_context_event_segments_address", open_shared_context_event_segments_address, "pure")
for _seg_spec in (
    GlyphSpec.make("BC.BUNDLE.SEGMENTS.OPEN", "build_shared_context_event_segments",
        ("root", "witnesses"), ("max_events_per_segment", "max_segment_bytes", "cone", "frames", "glyph_refs", "residuals"),
        {"root":"full_address", "witnesses":"full_address_witness_sequence", "max_events_per_segment":"positive_integer",
         "max_segment_bytes":"positive_integer", "cone":"depth_wave_cone", "frames":"addressed_frame_map",
         "glyph_refs":"glyph_reference_sequence", "residuals":"residual_sequence"}, "pure",
        "split a replayable event stream into bounded checkpointed segments; preserve all evidence and explicit oversize-event residuals"),
    GlyphSpec.make("BC.BUNDLE.SEGMENTS.REOPEN", "reopen_shared_context_event_segments",
        ("collection",), ("materialize_address_ids",), {"collection":"shared_context_event_segments",
         "materialize_address_ids":"address_id_sequence"}, "pure",
        "verify segment chain, checkpoints, exact delta application and operation replay without requiring all full states to be exported"),
    GlyphSpec.make("BC.BUNDLE.SEGMENTS.ADDRESS", "open_shared_context_event_segments_address",
        ("collection", "address_id"), (), {"collection":"shared_context_event_segments", "address_id":"address_id"}, "pure",
        "materialize a requested full address by replaying bounded checkpointed segments"),
):
    GLYPH_CATALOG.register(_seg_spec)


# ---------------------------------------------------------------------------
# Read-only self map: source AST -> resident glyph routes -> opened structural
# views -> self-feed evidence. Static source is parsed/compiled, never executed.
# Maps stay separate from learning profiles/proposals and from executable glyphs.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineSelfMap:
    schema: str
    map_address: str
    payload_json: str

    def as_dict(self) -> dict[str, Any]:
        body=json.loads(self.payload_json)
        body["map_address"]=self.map_address
        return body


def _engine_self_domains(name: str) -> tuple[str, ...]:
    low=name.lower()
    groups={
        "source":("source","inspect_legacy","migration_map","ast_"),
        "structuralizer":("structuralizer","perspective","zero_plane","three_point_hallway"),
        "self_feed":("self_feed","observe_depth_wave"),
        "learning":("learning","learn_","proposal","evidence"),
        "glyph_store":("glyph","catalogue","registry","compound","executor"),
        "wave":("wave","compactification","onehot"),
        "routing":("predictor","hallway","route_plan","resolve_command","resolve_glyph"),
        "bundle":("bundle","segment","shared_context","event_collection"),
        "harmonic_scale":("harmonic","prime_rpm","sphere504","prime_cog","scale_family"),
        "simulation_foundation":("simulation","material_kernel","physics_kernel","immersive","world_state","chemistry_kernel"),
    }
    return tuple(sorted(tag for tag, needles in groups.items() if any(n in low for n in needles)))


def _engine_self_source_graph(source_text: str, filename: str) -> dict[str, Any]:
    """Build a bounded source symbol/call map from source text without executing it."""
    raw=source_text.encode("utf-8")
    report=read_source_text(source_text,filename)
    if not report.syntax_pass or not report.ast_pass:
        return {"pass":False,"reason":"source_syntax_or_ast_check_failed","source_sha256":report.source_sha256,
                "bytes":report.bytes_read,"findings":list(report.findings),"source_executed":False}
    tree=ast.parse(source_text,filename=filename,mode="exec")
    defs=[]; calls=[]; class_stack=[]; function_stack=[]
    def leaf_name(node: ast.AST) -> str:
        if isinstance(node,ast.Name): return node.id
        if isinstance(node,ast.Attribute): return node.attr
        if isinstance(node,ast.Call): return leaf_name(node.func)
        return type(node).__name__
    class SourceGraph(ast.NodeVisitor):
        def visit_ClassDef(self,node):
            class_stack.append(node.name); self.generic_visit(node); class_stack.pop()
        def visit_FunctionDef(self,node):
            parts=[*class_stack,*function_stack,node.name]
            qual=".".join(parts)
            domain=_engine_self_domains(qual)
            defs.append({"symbol":qual,"short_name":node.name,"line_start":node.lineno,
                "line_end":getattr(node,"end_lineno",node.lineno),"domain_tags":list(domain),
                "kind":"method" if class_stack else ("nested_function" if function_stack else "function")})
            function_stack.append(node.name); self.generic_visit(node); function_stack.pop()
        visit_AsyncFunctionDef=visit_FunctionDef
        def visit_Call(self,node):
            if function_stack or class_stack:
                caller=".".join([*class_stack,*function_stack])
                calls.append({"caller":caller,"callee_leaf":leaf_name(node.func),"line":node.lineno})
            self.generic_visit(node)
    SourceGraph().visit(tree)
    by_short: dict[str,list[str]]={}
    by_qual={row["symbol"]:row for row in defs}
    for row in defs: by_short.setdefault(row["short_name"],[]).append(row["symbol"])
    domain_map={row["symbol"]:set(row["domain_tags"]) for row in defs}
    edges=[]; ambiguous=0; unresolved=0
    for call in calls:
        targets=by_short.get(call["callee_leaf"],[])
        if len(targets)==1:
            target=targets[0]
            if domain_map.get(call["caller"]) or domain_map.get(target):
                edges.append({"from":call["caller"],"to":target,"line":call["line"],"resolution":"unique_symbol"})
        elif len(targets)>1:
            ambiguous+=1
            if _engine_self_domains(call["caller"]) and len(edges)<4000:
                edges.append({"from":call["caller"],"to_candidates":sorted(targets)[:8],"line":call["line"],
                              "callee_leaf":call["callee_leaf"],"resolution":"ambiguous_short_name"})
        else:
            unresolved+=1
    edges.sort(key=lambda e:(e["from"],e.get("to", ""),e["line"],e.get("callee_leaf","")))
    if len(edges)>5000: edges=edges[:5000]
    domain_counts={}
    for row in defs:
        for domain in row["domain_tags"]: domain_counts[domain]=domain_counts.get(domain,0)+1
    relevant_domains={"source","structuralizer","self_feed","learning","glyph_store","wave","routing","bundle","harmonic_scale","simulation_foundation"}
    focused=[row for row in defs if set(row["domain_tags"]) & relevant_domains]
    duplicate_groups=[]
    for name,rows in sorted(by_short.items()):
        if len(rows)>1 and any(_engine_self_domains(x) for x in rows):
            duplicate_groups.append({"short_name":name,"symbols":sorted(rows)})
    return {"pass":True,"source_sha256":report.source_sha256,"bytes":report.bytes_read,
        "top_level_nodes":len(tree.body),"function_definition_occurrences":len(defs),
        "unique_qualified_function_names":len(by_qual),"duplicate_qualified_definition_groups":len(report.duplicate_definition_groups),
        "short_name_collisions_in_focus_domains":len(duplicate_groups),"call_nodes":len(calls),
        "internal_edges_retained":len(edges),"ambiguous_internal_call_sites":ambiguous,"external_or_unresolved_call_sites":unresolved,
        "list_comprehensions":report.list_comprehension_count,"subscripts":report.subscript_count,
        "call_count":report.call_count,"source_executed":False,"compile_only":True,
        "symbols":sorted(focused,key=lambda x:(x["symbol"],x["line_start"])),
        "edges":edges,"short_name_collisions":duplicate_groups,"domain_symbol_counts":dict(sorted(domain_counts.items())),
        "parse_findings":list(report.findings)}


def build_engine_self_map(address: BCFloorAddress, cone: DepthWaveCone,
                          workloads: Sequence[Mapping[str, Any]] = (),
                          ledger: GlyphLearningLedger | None = None,
                          feed_witness: FullAddressWitness | None = None,
                          top_k: int = 5,
                          historical_references: Sequence[str] = ()) -> EngineSelfMap:
    """Read-only map of this engine's source, actual glyph routes, opened frames and optional feed evidence.

    This operation reads only its own Python source file, parses/compiles but never executes that text,
    and requires the source_read effect grant when called through the glyph interface.
    """
    if not isinstance(address,BCFloorAddress) or not isinstance(cone,DepthWaveCone):
        raise TypeError("engine_self_map_requires_address_and_opened_cone")
    if cone.root_address_id!=address.address_id or not reopen_depth_wave_cone(address,cone).pass_all:
        raise ValueError("engine_self_map_source_cone_not_reopened")
    if not isinstance(workloads,(tuple,list)) or any(not isinstance(x,Mapping) for x in workloads):
        raise TypeError("engine_self_map_workloads_must_be_mappings")
    if ledger is not None and not isinstance(ledger,GlyphLearningLedger):
        raise TypeError("engine_self_map_ledger_type_invalid")
    if feed_witness is not None and not isinstance(feed_witness,FullAddressWitness):
        raise TypeError("engine_self_map_feed_witness_type_invalid")
    if type(top_k) is not int or not 1<=top_k<=32:
        raise ValueError("engine_self_map_top_k_out_of_range")
    if not isinstance(historical_references,(tuple,list)) or any(not isinstance(x,str) or not x for x in historical_references):
        raise TypeError("engine_self_map_historical_references_must_be_exact_names")
    active_path=pathlib.Path(__file__)
    source_bytes=active_path.read_bytes()
    source_text=source_bytes.decode("utf-8")
    source_hash=hashlib.sha256(source_bytes).hexdigest()
    source_graph=_engine_self_source_graph(source_text,active_path.name)
    if source_graph.get("pass") is not True:
        raise ValueError("engine_source_static_read_failed")
    if source_graph["source_sha256"]!=source_hash:
        raise ValueError("engine_source_digest_and_parser_mismatch")
    symbols={row["symbol"]:row for row in source_graph["symbols"]}
    # Runtime executor code objects supply the definitive callable source route; AST names are a cross-check.
    all_source_tree=ast.parse(source_text,filename=active_path.name,mode="exec")
    all_symbols=[]
    class ScanAll(ast.NodeVisitor):
        def __init__(self): self.classes=[]; self.functions=[]
        def visit_ClassDef(self,node): self.classes.append(node.name); self.generic_visit(node); self.classes.pop()
        def visit_FunctionDef(self,node):
            q=".".join([*self.classes,*self.functions,node.name])
            all_symbols.append({"symbol":q,"short_name":node.name,"line_start":node.lineno,
                                "line_end":getattr(node,"end_lineno",node.lineno)})
            self.functions.append(node.name); self.generic_visit(node); self.functions.pop()
        visit_AsyncFunctionDef=visit_FunctionDef
    ScanAll().visit(all_source_tree)
    code_lookup={row["symbol"]:row for row in all_symbols}
    glyph_rows=[]; executor_groups={}; effect_counts={}; unlinked=[]; effect_mismatch=[]
    for spec in GLYPH_CATALOG.describe():
        record=REGISTRY.resolve(spec["executor"])
        fn=getattr(record.executor,"__func__",record.executor)
        code=getattr(fn,"__code__",None)
        qual=getattr(fn,"__qualname__",None)
        line=None if code is None else code.co_firstlineno
        symbol=code_lookup.get(qual) if qual else None
        if symbol is None and line is not None:
            same=[row for row in all_symbols if row["line_start"]==line]
            symbol=same[0] if len(same)==1 else None
        route={"name":spec["name"],"address":spec["address"],"executor":spec["executor"],
            "effect_scope":spec["effect_scope"],"registry_effect":record.effect,
            "effect_matches":record.effect==spec["effect_scope"],"executor_qualname":qual,
            "executor_source_line":line,"source_symbol":None if symbol is None else symbol["symbol"],
            "source_symbol_line":None if symbol is None else symbol["line_start"],
            "required_args":spec["required_args"],"optional_args":spec["optional_args"],
            "arg_types":spec["arg_types"],"witness_contract":spec["witness_contract"]}
        glyph_rows.append(route); executor_groups.setdefault(spec["executor"],[]).append(spec["name"])
        effect_counts[spec["effect_scope"]]=effect_counts.get(spec["effect_scope"],0)+1
        if not route["effect_matches"]: effect_mismatch.append(spec["name"])
        if symbol is None: unlinked.append(spec["name"])
    wave=build_address_onehot_wave(address,cone)
    wave_reopen=reopen_address_onehot_wave(address,cone,wave)
    wave_map=compare_address_onehot_waves((wave,))
    wave_map_reopen=reopen_wave_glyph_comparison((wave,),wave_map)
    structural_views=[]
    for child in cone.child_addresses:
        try:
            link=build_depth_wave_structuralizer_view(address,cone,child)
            reopened=reopen_depth_wave_structuralizer_view(address,cone,child,link)
            structural_views.append({"child_address_id":child.address_id,"payload_address_id":child.payload_address_id,
                "level_index":child.level_index,"depth":child.recursion_depth,"aperture_box":child.box_aperture_address,
                "aperture_cube":child.cube_aperture_address,"point_count":len(link.source_points),
                "link_address":link.link_address,"perspective_packet_address":link.perspective_packet.packet_address,
                "reopened":bool(reopened.get("pass")),"source_points":[list(p) for p in link.source_points],
                "residuals":[] if reopened.get("pass") else [str(reopened.get("reason","structuralizer_reopen_failed"))]})
        except (TypeError,ValueError,KeyError,LookupError) as exc:
            structural_views.append({"child_address_id":child.address_id,"level_index":child.level_index,
                "depth":child.recursion_depth,"reopened":False,"residuals":[f"{type(exc).__name__}:{exc}"]})
    # Connect source/runtime layers to floor structure only as a navigational index; never infer semantic equivalence.
    namespace_counts={}
    for row in glyph_rows:
        parts=row["name"].split(".")
        namespace=".".join(parts[:2]) if len(parts)>1 else row["name"]
        namespace_counts[namespace]=namespace_counts.get(namespace,0)+1
    shared_executors={k:sorted(v) for k,v in sorted(executor_groups.items()) if len(v)>1}
    function_by_domain={}
    for row in source_graph["symbols"]:
        for domain in row["domain_tags"]: function_by_domain.setdefault(domain,[]).append(row["symbol"])
    route_links=[]
    available_depths=sorted({0,*[c.recursion_depth for c in cone.child_addresses]})
    for domain in ("source","structuralizer","self_feed","learning","glyph_store","wave","routing","bundle","harmonic_scale","simulation_foundation"):
        route_links.append({"domain":domain,"source_symbols":function_by_domain.get(domain,[]),
            "runtime_glyphs":[g["name"] for g in glyph_rows if domain in _engine_self_domains(g["name"]+" "+g["executor"])],
            "opened_hallway_depths":available_depths,"route_only":True,"semantic_equivalence_asserted":False})
    learning={"supplied":ledger is not None,"ledger_address":None if ledger is None else ledger.address,
        "evidence_count":0 if ledger is None else len(ledger.evidence),"profile_address":None,"profile_patterns":0,
        "proposal_set_address":None,"proposal_count":0,"comparison_map_address":None,"comparison_entries":0,
        "comparison_classes":0,"profile_and_proposal_storage_separate_from_map":True,
        "persistence":"caller-owned immutable objects; no disk write"}
    if ledger is not None:
        prof=build_learning_profile(ledger); props=propose_learning_routes(ledger); cmp=build_learning_comparison_map(ledger)
        learning.update({"profile_address":prof.profile_address,"profile_patterns":len(prof.patterns),
            "profile_unresolved":list(prof.unresolved),"proposal_set_address":props.proposal_set_address,
            "proposal_count":len(props.proposals),"proposal_unresolved":list(props.unresolved),
            "comparison_map_address":cmp.map_address,"comparison_entries":len(cmp.entries),
            "comparison_classes":len(cmp.classes),"comparison_reopen":reopen_learning_comparison_map(ledger,cmp)})
    feed=None
    if feed_witness is not None:
        # This is genuine address-transition self-feed, distinct from the static Python source map.
        observation=observe_depth_wave_self_feed(address,cone,feed_witness)
        base_ledger=ledger if ledger is not None else new_glyph_learning_ledger()
        updated=record_self_feed_evidence(base_ledger,address,cone,feed_witness,observation)
        added=[row for row in updated.evidence if row.evidence_address not in {r.evidence_address for r in base_ledger.evidence}]
        feed={"observation":_bc_dataclasses.asdict(observation),"ledger_before_address":base_ledger.address,
            "ledger_after_address":updated.address,"new_evidence_count":len(added),
            "new_evidence":[row.as_dict() for row in added],"ledger_export":export_glyph_learning_ledger(updated),
            "profile": {"address":build_learning_profile(updated).profile_address,
                        "pattern_count":len(build_learning_profile(updated).patterns)},
            "proposals":{"address":propose_learning_routes(updated).proposal_set_address,
                         "count":len(propose_learning_routes(updated).proposals)},
            "comparison_map": {"address":build_learning_comparison_map(updated).map_address,
                 "entry_count":len(build_learning_comparison_map(updated).entries),
                 "class_count":len(build_learning_comparison_map(updated).classes)},
            "auto_admitted":False,"persisted":False,"source_write":False}
    predictor=None
    if workloads:
        predictor=build_fractal_hallway_predictor_cone(address,cone,workloads,top_k=top_k)
        pr=reopen_fractal_hallway_predictor_cone(address,cone,predictor)
        if not pr.get("pass"): raise ValueError("engine_self_map_predictor_reopen_failed")
    historical_routing=[]
    for reference in historical_references:
        packet=resolve_command_reference(address,reference)
        route={"reference":reference,"status":packet.status,"packet":packet.as_dict(),
               "reopen":reopen_command_reference(address,reference,packet),
               "legacy_code_executed":False,"semantic_mapping_proven":False}
        if packet.status.startswith("historical_"):
            behavior=inspect_legacy_command_behavior(address,reference)
            route["behavior_packet"]=behavior.as_dict()
            route["behavior_reopen"]=reopen_legacy_command_behavior(address,reference,behavior)
        historical_routing.append(route)
    body={"schema":"BC-ENGINE-SELF-MAP-1","pass":True,
        "source":{"basename":active_path.name,"source_sha256":source_hash,"bytes":len(source_bytes),
            "parsed_and_compiled":True,"executed":False,"source_graph":source_graph},
        "active_runtime":{"engine_identity":ENGINE_IDENTITY,"runtime_state":RUNTIME_STATE,
            "source_path_is_module_file":True,"source_to_runtime_hash_current_file":source_hash,
            "catalogue_count":len(glyph_rows),"catalogue_digest":_sha256_text(_canonical_json([{k:v for k,v in g.items() if k not in {"executor_qualname","executor_source_line","source_symbol","source_symbol_line"}} for g in glyph_rows])),
            "registry_count":len(REGISTRY.names()),"effect_counts":dict(sorted(effect_counts.items())),
            "glyph_route_rows":glyph_rows,"glyph_namespace_counts":dict(sorted(namespace_counts.items())),
            "shared_executor_groups":shared_executors,"unlinked_glyph_names":sorted(unlinked),
            "effect_mismatches":sorted(effect_mismatch),"registry_operation_names":list(REGISTRY.names()),
            "registry_operations_without_glyph_specs":sorted(set(REGISTRY.names())-{g["executor"] for g in glyph_rows})},
        "stores":{"resident_glyph_catalogue":{"count":len(glyph_rows),"digest":_sha256_text(_canonical_json([g["address"] for g in glyph_rows])),
                "mutated":False},
            "compound_glyph_library":COMPOUND_GLYPH_LIBRARY.summary(),
            "learning":learning,
            "historical_rom":legacy_static_rom_status(),
            "wave_map":{"wave_address":wave.wave_address,"reopen":wave_reopen,
                "wave_glyph_count":len(wave.wave_glyphs),"comparison_map_address":wave_map.map_address,
                "comparison_map_reopen":wave_map_reopen,"comparison_entry_count":len(wave_map.entries),
                "comparison_class_count":len(wave_map.classes),"full_wave_payload":wave.as_dict(),
                "full_wave_comparison_payload":wave_map.as_dict()}},
        "opened_structure":{"root_address_id":address.address_id,"cone_address":cone.cone_address,
            "requested_depth_cap":cone.max_recursive_depth,"opened_depths":available_depths,
            "child_count":len(cone.child_addresses),"node_count":len(cone.nodes),"frontier_count":len(cone.frontier),
            "dependency_closed":cone.dependency_closed,"local_state_spaces_closed":cone.local_state_spaces_closed,
            "cone_reopen":_bc_dataclasses.asdict(reopen_depth_wave_cone(address,cone)),
            "structuralizer_views":structural_views,
            "frontier_residuals":[x.as_dict() for x in cone.frontier],
            "global_fractal_center_depth_known":False,
            "unopened_depth_is_not_inferred":True},
        "navigation_links":route_links,
        "predictor":predictor,
        "historical_routing":{"requested_references":list(historical_references),"routes":historical_routing,
            "rom_loaded_only_if_historical_lookup_requested":bool(historical_references),
            "legacy_code_executed":False,"automatic_alias_binding":False,"semantic_parity_proven":False},
        "self_feed_transition":feed,
        "flow_contract":{"read_source_effect_required":True,"source_was_not_executed":True,
            "source_ast_map_separate_from_floor_transition_evidence":True,
            "profile_rows_added":0,"proposal_rows_added":0,"glyph_admission":False,
            "persistent_save":False,"source_write":False,"cold_commit":False,
            "same_cardinality_box_cube_merge":False,
            "function_to_structural_frame_links_are_navigation_only":True,
            "unknown_depth_stays_residual":True}}
    map_address=_sha256_text(_canonical_json(body))
    return EngineSelfMap("BC-ENGINE-SELF-MAP-1",map_address,_canonical_json(body))


def reopen_engine_self_map(address: BCFloorAddress, cone: DepthWaveCone, self_map: EngineSelfMap,
                           workloads: Sequence[Mapping[str, Any]] = (),
                           ledger: GlyphLearningLedger | None = None,
                           feed_witness: FullAddressWitness | None = None,
                           top_k: int = 5,
                           historical_references: Sequence[str] = ()) -> dict[str, Any]:
    if not isinstance(self_map,EngineSelfMap):
        return {"schema":"BC-ENGINE-SELF-MAP-REOPEN-1","pass":False,"reason":"engine_self_map_required"}
    try:
        payload=json.loads(self_map.payload_json)
        if _sha256_text(_canonical_json(payload))!=self_map.map_address:
            raise ValueError("engine_self_map_content_address_mismatch")
        rebuilt=build_engine_self_map(address,cone,workloads,ledger,feed_witness,top_k,historical_references)
        passed=rebuilt==self_map and rebuilt.map_address==self_map.map_address
        return {"schema":"BC-ENGINE-SELF-MAP-REOPEN-1","pass":passed,
            "map_address":self_map.map_address,"rebuilt_map_address":rebuilt.map_address,
            "source_sha256":payload.get("source",{}).get("source_sha256"),
            "runtime_glyph_count":payload.get("active_runtime",{}).get("catalogue_count"),
            "structuralizer_view_count":len(payload.get("opened_structure",{}).get("structuralizer_views",[])),
            "opened_depths":payload.get("opened_structure",{}).get("opened_depths",[]),
            "unresolved_frontiers":payload.get("opened_structure",{}).get("frontier_count",0),
            "profile_rows_added":0,"proposal_rows_added":0,"glyph_admission":False,
            "persistent_save":False,"source_write":False,"cold_commit":False}
    except (TypeError,ValueError,KeyError,LookupError,OSError,UnicodeError) as exc:
        return {"schema":"BC-ENGINE-SELF-MAP-REOPEN-1","pass":False,
            "reason":f"engine_self_map_rebuild_failed:{type(exc).__name__}:{exc}"}


_COMPOUND_CLASS_KIND["EngineSelfMap"]="engine_self_map"
REGISTRY.register("build_engine_self_map",build_engine_self_map,"source_read")
REGISTRY.register("reopen_engine_self_map",reopen_engine_self_map,"source_read")
GLYPH_CATALOG.register(GlyphSpec.make("BC.LEARN.COMPARE.EXPORT","export_learning_comparison_map",("comparison_map",),(),
    {"comparison_map":"learning_comparison_map"},"pure",
    "export the full comparison/name index as portable data; the map address is only a locator and does not replace payloads"))

for _self_map_spec in (
    GlyphSpec.make("BC.ENGINE.SELF.MAP","build_engine_self_map",("address","cone"),
        ("workloads","ledger","feed_witness","top_k","historical_references"),
        {"address":"full_address","cone":"depth_wave_cone","workloads":"potential_workload_sequence",
         "ledger":"glyph_learning_ledger","feed_witness":"full_address_witness","top_k":"positive_integer",
         "historical_references":"glyph_reference_sequence"},
        "source_read","read-only Python AST/runtime-glyph/structuralizer/self-feed map; source text is parsed and compiled but never executed"),
    GlyphSpec.make("BC.ENGINE.SELF.MAP.REOPEN","reopen_engine_self_map",("address","cone","self_map"),
        ("workloads","ledger","feed_witness","top_k","historical_references"),
        {"address":"full_address","cone":"depth_wave_cone","self_map":"engine_self_map",
         "workloads":"potential_workload_sequence","ledger":"glyph_learning_ledger",
         "feed_witness":"full_address_witness","top_k":"positive_integer",
         "historical_references":"glyph_reference_sequence"},
        "source_read","rebuild the source map and all structuralizer/feed routes against the exact current source and reopened cone"),
):
    GLYPH_CATALOG.register(_self_map_spec)



# ---------------------------------------------------------------------------
# Unified relation map: names are routes into opened address-space evidence,
# not containers of duplicated glyph implementations. Similarity edges retain
# their comparison lens, source witness and unresolved residuals.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AddressRelationMap:
    schema: str
    map_address: str
    payload_json: str

    def as_dict(self) -> dict[str, Any]:
        body = json.loads(self.payload_json)
        body["map_address"] = self.map_address
        return body


def _relation_route_id(kind: str, stable_key: str, source_key: str = "") -> str:
    return _sha256_text(_canonical_json({"schema":"BC-RELATION-ROUTE-ID-1",
        "kind":kind,"stable_key":stable_key,"source_key":source_key}))[:24]


def _relation_link(links: list[dict[str, Any]], route_ids: set[str], source: str, target: str,
                   kind: str, proof_kind: str, evidence_refs: Sequence[str],
                   residuals: Sequence[str] = (), claim_boundary: str = "") -> None:
    if source not in route_ids or target not in route_ids:
        return
    body={"schema":"BC-ADDRESS-RELATION-1","source_route_id":source,"target_route_id":target,
          "relation":kind,"proof_kind":proof_kind,"evidence_refs":sorted(set(evidence_refs)),
          "residuals":sorted(set(residuals)),"claim_boundary":claim_boundary or
          "route relation only; does not imply semantic equivalence or execution certification"}
    body["relation_id"]=_sha256_text(_canonical_json(body))[:24]
    links.append(body)


def _collision_stage_route_index(stage: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Make a small control-surface index into a separately retained collision stage.

    Candidate summaries are copied because there are few of them; detailed prime-lane,
    one-hot, and structuralizer witnesses remain in the full staging evidence artifact.
    """
    if stage is None:
        return None
    if not isinstance(stage, Mapping):
        raise TypeError("collision_stage_must_be_mapping")
    if stage.get("schema") == "BC-COLLISION-STAGE-ROUTE-INDEX-1":
        index_body={k:v for k,v in stage.items() if k!="index_address"}
        if _sha256_text(_canonical_json(index_body))[:32] != stage.get("index_address"):
            raise ValueError("collision_stage_route_index_content_address_mismatch")
        return dict(stage)
    if stage.get("schema") != "BC-FRACTAL-COLLISION-CONE-STAGE-1":
        raise ValueError("collision_stage_schema_not_supported")
    stage_body={k:v for k,v in stage.items() if k!="stage_address"}
    if _sha256_text(_canonical_json(stage_body))[:32] != stage.get("stage_address"):
        raise ValueError("collision_stage_content_address_mismatch")
    source_contexts=[]
    for row in stage.get("source_contexts",[]):
        root=row.get("root_address_id"); cone=row.get("cone_address")
        if not isinstance(root,str) or not isinstance(cone,str):
            raise ValueError("collision_stage_source_binding_missing")
        source_contexts.append({
            "source_key":_sha256_text(_canonical_json({"root":root,"cone":cone}))[:24],
            "label":row.get("label",""),"root_address_id":root,"cone_address":cone,
            "lock_address":row.get("lock_address"),"opening_address":row.get("opening_address"),
            "effective_depth_cap":row.get("effective_depth_cap",-1),
            "effective_wave_radius":row.get("effective_wave_radius",-1)})
    if len(source_contexts)<2:
        raise ValueError("collision_stage_requires_at_least_two_bound_sources")
    scan_rows=[]
    for ix,row in enumerate(stage.get("pair_fidelity_scans",[])):
        left=next((x for x in source_contexts if x["label"]==row.get("left_label") and x["root_address_id"]==row.get("left_root_address_id")),None)
        right=next((x for x in source_contexts if x["label"]==row.get("right_label") and x["root_address_id"]==row.get("right_root_address_id")),None)
        if left is None or right is None:
            raise ValueError("collision_stage_pair_scan_source_unbound")
        scan_rows.append({"pair_scan_address":row.get("pair_scan_address"),
            "left_label":row.get("left_label"),"right_label":row.get("right_label"),
            "left_root_address_id":row.get("left_root_address_id"),"right_root_address_id":row.get("right_root_address_id"),
            "governing_source_keys":sorted({left["source_key"],right["source_key"]}),
            "comparison_count":len(row.get("comparisons",[])),
            "signed_ticks":sorted({x.get("tick") for x in row.get("comparisons",[]) if type(x.get("tick")) is int}),
            "plane_count":sum(len(lane.get("planes",[])) for comp in row.get("comparisons",[]) for lane in comp.get("prime_lane_comparisons",[])),
            "payload_ref":{"artifact_hint":"BC_TRANSITION_STAGING_EVIDENCE.json","json_pointer":f"/collision_stage/pair_fidelity_scans/{ix}"},
            "claim_boundary":"compact scan index; detailed prime-lane and plane witnesses remain in the full evidence artifact"})
    alias_rows=[]
    for ix,row in enumerate(stage.get("sphere_winding_alias_refs",[])):
        members=[]
        for member in row.get("members",[]):
            src=next((x for x in source_contexts if x["root_address_id"]==member.get("root_address_id") and x["label"]==member.get("label")),None)
            if src is None: raise ValueError("sphere_winding_alias_source_unbound")
            members.append({"source_key":src["source_key"],"label":member.get("label"),
                "root_address_id":member.get("root_address_id"),"address_id":member.get("address_id"),
                "head":member.get("head"),"winding":member.get("winding"),"absolute_phase":member.get("absolute_phase")})
        alias_rows.append({"head":row.get("head"),"members":members,
            "governing_source_keys":sorted({x["source_key"] for x in members}),
            "interpretation":row.get("interpretation","same cyclic head does not imply same lifted phase"),
            "payload_ref":{"artifact_hint":"BC_TRANSITION_STAGING_EVIDENCE.json","json_pointer":f"/collision_stage/sphere_winding_alias_refs/{ix}"},
            "claim_boundary":"cyclic alias only; winding paths and address identities remain distinct"})
    candidates=[]
    for ix,row in enumerate(stage.get("candidates",[])):
        left=next((x for x in source_contexts if x["label"]==row.get("left_label")),None)
        right=next((x for x in source_contexts if x["label"]==row.get("right_label")),None)
        if left is None or right is None: raise ValueError("collision_candidate_source_unbound")
        candidates.append({"candidate_index":ix,"candidate_address":row.get("candidate_address"),"kind":row.get("kind"),
            "depth":row.get("depth"),"wave_distance":row.get("wave_distance"),"physical_coord6":row.get("physical_coord6"),
            "left_label":row.get("left_label"),"right_label":row.get("right_label"),
            "left_root_address_id":left["root_address_id"],"right_root_address_id":right["root_address_id"],
            "left_source_key":left["source_key"],"right_source_key":right["source_key"],
            "left_node_ids":row.get("left_node_ids",[]),"right_node_ids":row.get("right_node_ids",[]),
            "pair_fidelity_scan":row.get("pair_fidelity_scan"),"same_address_identity":row.get("same_address_identity",False),
            "opened_nodes_remain_root_bound":row.get("opened_nodes_remain_root_bound",True),"merging_permitted":False,
            "governing_source_keys":sorted({left["source_key"],right["source_key"]}),
            "payload_ref":{"artifact_hint":"BC_TRANSITION_STAGING_EVIDENCE.json","json_pointer":f"/collision_stage/candidates/{ix}"},
            "claim_boundary":"projected overlap candidate, not an identity merge; detailed evidence remains at payload_ref"})
    body={"schema":"BC-COLLISION-STAGE-ROUTE-INDEX-1","stage_address":stage.get("stage_address"),
        "source_contexts":source_contexts,"sweep_ticks":list(stage.get("sweep_ticks",[])),
        "aperture_stage_count":stage.get("aperture_stage_count"),
        "projected_overlap_total":stage.get("projected_overlap_total"),
        "projected_overlap_samples_available":stage.get("projected_overlap_samples_available"),
        "projected_overlap_candidates_unexamined_residual":stage.get("projected_overlap_candidates_unexamined_residual"),
        "candidate_count_staged":len(candidates),"candidates":candidates,"pair_fidelity_scans":scan_rows,
        "sphere_winding_alias_groups":alias_rows,
        "max_candidate_depth":max([int(x["depth"]) for x in candidates if type(x.get("depth")) is int] or [0]),
        "payload_ref":{"artifact_hint":"BC_TRANSITION_STAGING_EVIDENCE.json","json_pointer":"/collision_stage"},
        "full_evidence_is_external":True,"frontier_traversal_performed":False,
        "claim_boundary":"compact address-control index; complete stage, transition witnesses and source payloads remain separately stored"}
    body["index_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def build_address_relation_map(address: BCFloorAddress, cone: DepthWaveCone,
                               related_sources: Sequence[Mapping[str, Any]] = (),
                               ledger: GlyphLearningLedger | None = None,
                               workloads: Sequence[Mapping[str, Any]] = (), top_k: int = 5,
                               collision_stage: Mapping[str, Any] | None = None) -> AddressRelationMap:
    """Build a sparse control map linking opened addresses, wave comparisons,
    learning evidence and candidate workload routes. The map indexes evidence;
    actual source payloads remain openable from their source objects/ledger.
    """
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("primary_full_address_and_depth_wave_cone_required")
    if not isinstance(related_sources, (tuple, list)):
        raise TypeError("related_sources_must_be_bounded_sequence")
    if not isinstance(workloads, (tuple, list)):
        raise TypeError("workloads_must_be_bounded_sequence")
    if type(top_k) is not int or not 1 <= top_k <= 32:
        raise ValueError("relation_map_top_k_must_be_1_to_32")
    collision_index=_collision_stage_route_index(collision_stage)
    source_pairs=[(address,cone,"primary")]
    for ix, row in enumerate(related_sources):
        if not isinstance(row, Mapping) or not isinstance(row.get("address"), BCFloorAddress) or not isinstance(row.get("cone"), DepthWaveCone):
            raise TypeError(f"related_source_{ix}_requires_typed_address_and_cone")
        source_pairs.append((row["address"],row["cone"],f"related:{ix}"))
    if len(source_pairs)>32:
        raise ValueError("relation_map_source_count_exceeds_32")
    source_rows=[]; waves=[]; source_objects=[]
    seen_pairs=set()
    for src_addr, src_cone, source_label in source_pairs:
        if src_cone.root_address_id != src_addr.address_id:
            raise ValueError("relation_map_cone_root_mismatch:"+source_label)
        reopen_cone=reopen_depth_wave_cone(src_addr,src_cone)
        if not reopen_cone.pass_all:
            raise ValueError("relation_map_cone_reopen_failed:"+source_label)
        pair_key=(src_addr.address_id,src_cone.cone_address)
        if pair_key in seen_pairs:
            raise ValueError("duplicate_relation_map_source_pair")
        seen_pairs.add(pair_key)
        wave=build_address_onehot_wave(src_addr,src_cone)
        wr=reopen_address_onehot_wave(src_addr,src_cone,wave)
        if not wr.get("pass"):
            raise ValueError("relation_map_wave_reopen_failed:"+source_label)
        source_key=_sha256_text(_canonical_json({"root":src_addr.address_id,"cone":src_cone.cone_address}))[:24]
        waves.append(wave); source_objects.append((source_key,src_addr,src_cone,wave))
        source_rows.append({"source_key":source_key,"label":source_label,"root_address_id":src_addr.address_id,
            "cone_address":src_cone.cone_address,"wave_address":wave.wave_address,
            "opened_depths":sorted({0,*[n.depth for n in src_cone.nodes]}),
            "node_count":len(src_cone.nodes),"frontier_count":len(src_cone.frontier),
            "dependency_closed":src_cone.dependency_closed,
            "local_state_spaces_closed":src_cone.local_state_spaces_closed,
            "cone_reopened":True,"wave_reopened":True,"global_center_depth_known":False})
    wave_map=compare_address_onehot_waves(tuple(waves))
    wave_map_reopen=reopen_wave_glyph_comparison(tuple(waves),wave_map)
    if not wave_map_reopen.get("pass"):
        raise ValueError("relation_map_wave_comparison_reopen_failed")
    learning_map=None; learning_reopen=None
    if ledger is not None:
        if not isinstance(ledger,GlyphLearningLedger):
            raise TypeError("relation_map_ledger_must_be_glyph_learning_ledger")
        learning_map=build_learning_comparison_map(ledger)
        learning_reopen=reopen_learning_comparison_map(ledger,learning_map)
        if not learning_reopen.get("pass"):
            raise ValueError("relation_map_learning_map_reopen_failed")
    workload_rows=_scb_json_value(workloads)
    predictor=None; predictor_reopen=None
    if workload_rows:
        predictor=build_fractal_hallway_predictor_cone(address,cone,workload_rows,top_k=top_k)
        predictor_reopen=reopen_fractal_hallway_predictor_cone(address,cone,predictor)
        if not predictor_reopen.get("pass"):
            raise ValueError("relation_map_predictor_reopen_failed")
    glyph_rows=list(GLYPH_CATALOG.describe())
    glyph_digest=_sha256_text(_canonical_json([{k:v for k,v in row.items()} for row in glyph_rows]))
    routes=[]; links=[]; route_ids=set(); by_source={}; by_kind_key={}; scale_routes={}
    def add_route(kind: str, stable_key: str, label: str, source_key: str = "",
                  **fields: Any) -> str:
        rid=_relation_route_id(kind,stable_key,source_key)
        if rid in route_ids:
            return rid
        row={"route_id":rid,"kind":kind,"label":label,"source_key":source_key,
             "openable":True,"route_state":"indexed","target_key":stable_key,**fields}
        routes.append(row);route_ids.add(rid);by_kind_key[(kind,source_key,stable_key)]=rid
        return rid
    # Every source retains a real root, cone, recursive child and frame opening path.
    for source_key, src_addr, src_cone, wave in source_objects:
        root_r=add_route("root",src_addr.address_id,"Full addressed root",source_key,
            target_address_id=src_addr.address_id,source_address_id=src_addr.address_id,
            cone_address=src_cone.cone_address,payload_ref={"kind":"full_address","address_id":src_addr.address_id},
            evidence_status="opened_address")
        cone_r=add_route("cone",src_cone.cone_address,"Opened recursive cone",source_key,
            target_address_id=src_cone.cone_address,root_route_id=root_r,opened_depths=source_rows[[r['source_key'] for r in source_rows].index(source_key)]["opened_depths"],
            node_count=len(src_cone.nodes),frontier_count=len(src_cone.frontier),
            dependency_closed=src_cone.dependency_closed,local_state_spaces_closed=src_cone.local_state_spaces_closed,
            payload_ref={"kind":"depth_wave_cone","cone_address":src_cone.cone_address},
            evidence_status="cone_reopened")
        wave_r=add_route("wave",wave.wave_address,"Address-native one-hot wave",source_key,
            target_address_id=wave.wave_address,root_route_id=root_r,cone_route_id=cone_r,
            frame_count=len(wave.frames),wave_glyph_count=len(wave.wave_glyphs),
            frontier_residual_count=len(wave.frontier_residuals),payload_ref={"kind":"address_onehot_wave","wave_address":wave.wave_address},
            evidence_status="wave_reopened")
        child_rids={}
        for child in src_cone.child_addresses:
            state=src_addr.levels[child.level_index]
            cr=add_route("child",child.address_id,child.name,source_key,
                target_address_id=child.address_id,root_route_id=root_r,cone_route_id=cone_r,
                level_index=child.level_index,depth=child.recursion_depth,path=list(child.path),
                box_aperture_address=child.box_aperture_address,cube_aperture_address=child.cube_aperture_address,
                payload_address_id=child.payload_address_id,aperture_families_distinct=True,
                payload_ref={"kind":"recursive_child_address","address_id":child.address_id},evidence_status="child_resolved")
            child_rids[child.address_id]=cr
            _relation_link_placeholder=None
        frame_rids={}
        for frame in wave.frames:
            fr=add_route("frame",frame.frame_address,frame.frame_name,source_key,
                target_address_id=frame.frame_address,root_route_id=root_r,depth=frame.depth,
                dimension_rank=frame.dimension_rank,aperture_address=frame.aperture_address,
                frame_kind=frame.frame_kind,path=list(frame.path),word_count=len(frame.words),
                payload_ref={"kind":"address_onehot_frame","frame_address":frame.frame_address},evidence_status="frame_rebuilt")
            frame_rids[frame.frame_address]=fr
            for word in frame.words:
                wrid=add_route("frame_word",frame.frame_address+":"+word.word_address,
                    frame.frame_name+" · "+word.family,source_key,target_address_id=word.word_address,
                    parent_route_id=fr,word_family=word.family,word_width=word.width,word_mode=word.mode,
                    presence=word.presence,active_slots=list(word.active_slots),aperture_address=frame.aperture_address,
                    payload_ref={"kind":"sparse_onehot_word","word_address":word.word_address},evidence_status="typed_word")
        glyph_rids={}
        for glyph in wave.wave_glyphs:
            gr=add_route("wave_glyph",glyph.wave_glyph_address,glyph.short_name,source_key,
                target_address_id=glyph.wave_glyph_address,root_route_id=root_r,cone_route_id=cone_r,
                wave_route_id=wave_r,child_address_id=glyph.child_address_id,depth=glyph.depth,
                wave_distance=glyph.wave_distance,projection_ranks=[p.rank for p in glyph.projections],
                residuals=list(glyph.residuals),payload_ref={"kind":"address_wave_glyph","wave_glyph_address":glyph.wave_glyph_address},
                evidence_status="comparison_pattern_not_executable_glyph")
            glyph_rids[glyph.wave_glyph_address]=gr
            for projection in glyph.projections:
                pr=add_route("projection",glyph.wave_glyph_address+":"+str(projection.rank),
                    glyph.short_name+f" · rank {projection.rank}",source_key,
                    target_address_id=projection.signature_address,parent_route_id=gr,root_route_id=root_r,
                    wave_glyph_address=glyph.wave_glyph_address,rank=projection.rank,
                    wave_distance=projection.wave_distance,domain_width=projection.domain_width,
                    active_slots=list(projection.active_slots),multiplicities=[list(x) for x in projection.multiplicities],
                    collision_count=sum(max(0,n-1) for _,n in projection.multiplicities),
                    omitted_fibres_count=sum(len(rows) for _,rows in projection.omitted_fibres),
                    chosen_frame=projection.chosen_frame,claim_boundary=projection.projected_claim,
                    payload_ref={"kind":"wave_projection","wave_glyph_address":glyph.wave_glyph_address,"rank":projection.rank},
                    evidence_status="exact_projected_signature_with_residuals")
                by_kind_key[("projection_by_glyph",source_key,glyph.wave_glyph_address+":"+str(projection.rank))]=pr
        # Frontiers are addressable evidence but are not opened states or routes to deeper levels.
        for frontier in wave.frontier_residuals:
            fk=_canonical_json(frontier.as_dict())
            add_route("frontier",fk,"Unopened wave frontier",source_key,
                target_address_id=frontier.target_state_address_id,root_route_id=root_r,cone_route_id=cone_r,
                child_address_id=frontier.child_address_id,depth=frontier.depth,
                from_state_address_id=frontier.from_state_address_id,axis=frontier.axis,
                direction=frontier.direction,next_wave_distance=frontier.next_wave_distance,
                openable=False,route_state="unopened_residual",residual_kind=frontier.residual_kind,
                payload_ref={"kind":"wave_frontier_residual","target_state_address_id":frontier.target_state_address_id},
                evidence_status="frontier_not_opened")
        cog_space=build_64core_harmonic_state_space(src_addr,"deepest_resolved")
        cog_space_route=add_route("cog64_state_space",cog_space["space_address"],"Core64 × sphere504 cyclic state space",source_key,
            target_address_id=cog_space["space_address"],root_route_id=root_r,cone_route_id=cone_r,
            source_frame_address=cog_space["source_frame"]["frame_address"],frame_selector=cog_space["frame_selector"],
            factor_shape={"control":8,"translation":8,"sphere504":504,"aperture_stages":len(HARMONIC_APERTURE_STAGES)},
            cyclic_configuration_count=cog_space["cyclic_configuration_count"],
            aperture_stages=cog_space["aperture_stages"],residuals=list(cog_space["residuals"]),
            payload_ref={"kind":"cog64_harmonic_state_space","space_address":cog_space["space_address"]},
            evidence_status="exact_factorized_cyclic_index_not_materialized")
        by_source[source_key]={"address":src_addr,"cone":src_cone,"wave":wave,"root_route":root_r,
            "cone_route":cone_r,"wave_route":wave_r,"children":child_rids,"frames":frame_rids,"glyphs":glyph_rids,
            "cog64_space":cog_space,"cog64_space_route":cog_space_route}
    # Public glyph routes point to the single resident catalogue, not copied implementations.
    glyph_routes={}
    for specrow in glyph_rows:
        erec=REGISTRY.resolve(specrow["executor"])
        efn=getattr(erec.executor,"__func__",erec.executor)
        ecode=getattr(efn,"__code__",None)
        gr=add_route("glyph",specrow["name"],specrow["name"],"library",
            glyph_address=specrow["address"],executor=specrow["executor"],effect_scope=specrow["effect_scope"],
            implementation_source_path=None if ecode is None else pathlib.Path(ecode.co_filename).name,
            implementation_source_line=None if ecode is None else ecode.co_firstlineno,
            required_args=specrow["required_args"],optional_args=specrow["optional_args"],
            arg_types=specrow["arg_types"],witness_contract=specrow["witness_contract"],
            payload_ref={"kind":"resident_glyph_spec","name":specrow["name"],"address":specrow["address"]},
            evidence_status="registered_contract_and_executor_pointer_not_semantic_certification")
        glyph_routes[specrow["name"]]=gr
    # Named scales exist independently of any learning ledger; they are routes,
    # never claims about recursion depth or a globally known centre.
    for item in HARMONIC_STACKS:
        sr=add_route("scale_route",item.name,item.name,"library_scale",target_address_id=item.name,
            shape=list(item.shape),capacity=item.capacity,shell=item.shell,address_family=item.address_family,
            payload_ref={"kind":"named_scale_route","name":item.name},
            evidence_status="named_scale_route_not_recursive_depth_or_center_count")
        scale_routes[item.name]=sr
    aperture_stage_routes={}
    for stage_index,prime_prefix in enumerate(HARMONIC_APERTURE_STAGES):
        stage_key=str(stage_index)+":"+_canonical_json(list(prime_prefix))
        stage_route=add_route("harmonic_aperture_stage",stage_key,
            "Sphere aperture stage "+str(stage_index)+" · "+("zero" if not prime_prefix else "×".join(map(str,prime_prefix))),
            "library_harmonic",target_address_id=stage_key,stage_index=stage_index,
            prime_prefix=list(prime_prefix),active_prime_lane_count=len(prime_prefix),
            sphere_head_count=HARMONIC_HEADS,core64_lane_pairs=64,
            stage_configuration_count=64*HARMONIC_HEADS,
            payload_ref={"kind":"prime_harmonic_aperture_stage","stage_index":stage_index},
            evidence_status="exact_named_aperture_prefix_not_physical_calibration")
        aperture_stage_routes[stage_index]=stage_route
    sphere_route=add_route("sphere504_cycle","sphere504","Sphere-504 prime-harmonic cycle","library_harmonic",
        target_address_id="sphere504",head_count=HARMONIC_HEADS,radices=list(SPHERE504_RADICES),
        factor_product=(SPHERE504_RADICES[0]*SPHERE504_RADICES[1]*SPHERE504_RADICES[2]),aperture_stage_count=len(HARMONIC_APERTURE_STAGES),
        payload_ref={"kind":"sphere504_cycle_definition","radices":list(SPHERE504_RADICES)},
        evidence_status="exact_integer_factor_cycle_not_physical_rpm_calibration")
    # Shared signature classes retain all member routes and the comparison lens.
    waveclass_routes={}
    entries_by_glyph_rank={(e.wave_glyph_address,e.rank):e for e in wave_map.entries}
    for cls in wave_map.classes:
        classkey=cls.class_address
        cr=add_route("wave_match_class",classkey,"Shared projected pattern", "comparison",
            target_address_id=classkey,signature_address=cls.signature_address,rank=cls.rank,
            wave_distance=cls.wave_distance,member_wave_glyph_addresses=list(cls.member_addresses),
            roots=list(cls.roots),depths=list(cls.depths),residual_variants=cls.residual_variants,
            claim_boundary=cls.claim_boundary,payload_ref={"kind":"wave_glyph_match_class","class_address":classkey},
            evidence_status="comparison_only")
        waveclass_routes[classkey]=cr
        for member in cls.member_addresses:
            for (ga,rank),entry in entries_by_glyph_rank.items():
                if ga==member and rank==cls.rank and entry.signature_address==cls.signature_address:
                    # Locate route by its source key from exact wave provenance.
                    sk=next((k for k,v in by_source.items() if v["wave"].wave_address==entry.wave_address),"")
                    projrid=by_kind_key.get(("projection_by_glyph",sk,ga+":"+str(rank)))
                    if projrid:
                        _relation_link(links,route_ids,projrid,cr,"shares_projection_signature","reopened_wave_comparison",
                            [wave_map.map_address,entry.wave_address,ga],entry.residuals,
                            "same projection signature and rank/distance; not execution equivalence")
    frameclass_routes={}
    for cls in wave_map.frame_classes:
        ck=cls.class_address
        fr=add_route("frame_match_class",ck,"Shared typed one-hot frame word","comparison",
            target_address_id=ck,signature_address=cls.signature_address,word_family=cls.word_family,
            word_width=cls.word_width,word_mode=cls.word_mode,presence=cls.presence,
            member_word_addresses=list(cls.member_word_addresses),frame_names=list(cls.frame_names),
            roots=list(cls.roots),depths=list(cls.depths),claim_boundary=cls.claim_boundary,
            payload_ref={"kind":"address_frame_match_class","class_address":ck},evidence_status="typed_word_comparison_only")
        frameclass_routes[ck]=fr
        for member in cls.member_word_addresses:
            for source_key,src_addr,src_cone,wave in source_objects:
                for frame in wave.frames:
                    if member.startswith(frame.frame_address+":"):
                        wid=member.split(":",1)[1]
                        frame_route=by_kind_key.get(("frame_word",source_key,member))
                        if frame_route:
                            _relation_link(links,"",frame_route,fr,"shares_typed_frame_word","reopened_wave_comparison",
                                [wave_map.map_address,wave.wave_address,frame.frame_address,wid],(),
                                "same typed one-hot word signature; aperture and frame provenance remain explicit")
    dimensional_routes={}
    for dlink in wave_map.dimensional_links:
        ddata=dlink.as_dict(); dlkey=_sha256_text(_canonical_json(ddata))[:24]
        dr=add_route("dimensional_link",dlkey,"Cross-rank projection relation","comparison",
            target_address_id=dlkey,wave_glyph_address=dlink.parent_wave_glyph_address,
            from_rank=dlink.lower_rank,to_rank=dlink.higher_rank,from_signature_address=dlink.lower_signature,
            to_signature_address=dlink.higher_signature,from_collision_count=dlink.lower_collision_count,
            to_collision_count=dlink.higher_collision_count,residuals=list(dlink.omitted_axis_residuals),
            payload_ref={"kind":"wave_dimensional_link","link_address":dlkey},evidence_status="projection_relation_with_residuals")
        dimensional_routes[dlkey]=dr
        sk=next((k for k,v in by_source.items() if v["wave"].wave_address==dlink.source_wave_address),"")
        p1=by_kind_key.get(("projection_by_glyph",sk,dlink.parent_wave_glyph_address+":"+str(dlink.lower_rank)))
        p2=by_kind_key.get(("projection_by_glyph",sk,dlink.parent_wave_glyph_address+":"+str(dlink.higher_rank)))
        _relation_link(links,route_ids,p1 or "",p2 or "","projects_between_dimensions","reopened_wave_comparison",
            [wave_map.map_address,dlink.source_wave_address,dlink.parent_wave_glyph_address],dlink.omitted_axis_residuals,
            "dimensional view link preserves omitted-axis and collision residuals")
        if p1: _relation_link(links,route_ids,p1,dr,"documented_by_dimensional_link","reopened_wave_comparison",[wave_map.map_address],dlink.omitted_axis_residuals)
        if p2: _relation_link(links,route_ids,dr,p2,"documents_target_projection","reopened_wave_comparison",[wave_map.map_address],dlink.omitted_axis_residuals)
    # Learning evidence is indexed by the separate ledger; its classes never absorb the evidence.
    learning_evidence_routes={}; learning_class_routes={}; learning_witness_routes={}
    if ledger is not None and learning_map is not None:
        for evidence in ledger.evidence:
            er=add_route("learning_evidence",evidence.evidence_address,evidence.source_kind,"learning",
                target_address_id=evidence.evidence_address,pattern_address=evidence.pattern_address,
                passed=evidence.passed,source_address=evidence.source_address,
                source_container_address=evidence.source_container_address,
                source_witness_id=evidence.source_witness_id,residuals=list(evidence.residuals),
                checks=[[n,v] for n,v in evidence.checks],payload_ref={"kind":"learning_ledger_evidence","evidence_address":evidence.evidence_address},
                evidence_status="ledger_record_not_automatically_admitted")
            learning_evidence_routes[evidence.evidence_address]=er
            witness_key=evidence.evidence_address+":"+evidence.source_witness_id
            wvr=add_route("learning_witness",witness_key,"Witness · "+evidence.source_witness_id[:8],"learning",
                target_address_id=evidence.source_witness_id,evidence_address=evidence.evidence_address,
                payload_ref={"kind":"learning_evidence_witness","evidence_address":evidence.evidence_address,"witness_id":evidence.source_witness_id},
                evidence_status="witness_embedded_in_source_evidence")
            learning_witness_routes[witness_key]=wvr
            _relation_link(links,route_ids,er,wvr,"opens_source_witness","ledger_payload_index",
                [ledger.address,evidence.evidence_address,evidence.source_witness_id],evidence.residuals,
                "witness is opened from its full evidence record; it is not a summary substitute")
            for source_key,src_addr,src_cone,src_wave in source_objects:
                info=by_source[source_key]
                if evidence.source_address==src_addr.address_id:
                    _relation_link(links,route_ids,info["root_route"],er,"has_self_feed_evidence","ledger_source_binding",
                        [ledger.address,evidence.evidence_address,evidence.source_witness_id,src_addr.address_id],evidence.residuals,
                        "evidence binds to this exact source address")
                if evidence.source_container_address==src_cone.cone_address:
                    _relation_link(links,route_ids,info["cone_route"],er,"contains_self_feed_evidence","ledger_source_binding",
                        [ledger.address,evidence.evidence_address,evidence.source_witness_id,src_cone.cone_address],evidence.residuals,
                        "evidence binds to this exact opened cone")
        for cls in learning_map.classes:
            cr=add_route("learning_match_class",cls.class_address,cls.view_name+" comparison class","learning",
                target_address_id=cls.class_address,view_name=cls.view_name,signature_address=cls.signature_address,
                evidence_addresses=list(cls.evidence_addresses),pattern_addresses=list(cls.pattern_addresses),
                route_names=list(cls.route_names),claim_boundary=cls.claim_boundary,
                payload_ref={"kind":"learning_comparison_class","class_address":cls.class_address},evidence_status="comparison_only")
            learning_class_routes[cls.class_address]=cr
            for scale_name in cls.route_names:
                sr=scale_routes.get(scale_name)
                if sr:
                    _relation_link(links,route_ids,cr,sr,"references_named_scale_route","reopened_learning_map",
                        [learning_map.map_address,cls.class_address,scale_name],(),
                        "scale route is a named structural slice; capacity is not fractal center depth")
            for eid in cls.evidence_addresses:
                er=learning_evidence_routes.get(eid)
                if er:
                    _relation_link(links,route_ids,er,cr,"shares_learning_comparison_view","reopened_learning_map",
                        [learning_map.map_address,eid,cls.signature_address],(),cls.claim_boundary)
    # Workloads route through the primary opened cone only. Predictions remain candidates.
    predictor_route_refs={}
    if predictor is not None:
        for pred in predictor["predictions"]:
            wid=pred["workload_id"]
            wr=add_route("workload",wid,wid,"predictor",
                target_address_id=wid,requested_depth=pred["route"]["requested_depth"],
                selected_depth=pred["route"]["depth"],requested_depth_open=pred["route"]["requested_depth_open"],
                route_fidelity_bps=pred["route"]["route_fidelity_bps"],
                best_contract_coverage_bps=pred["best_contract_coverage_bps"],
                planning_support_bps=pred["planning_support_bps"],
                ranked_candidates=[{"glyph":x["glyph"],"glyph_address":x["glyph_address"],
                    "contract_coverage_bps":x["contract_coverage_bps"],"effect_match":x["effect_match"],
                    "matched_input_types":x["matched_input_types"],"unprovided_required_inputs":x["unprovided_required_inputs"]}
                    for x in pred["known_glyph_candidates"]],residuals=list(pred["residuals"]),
                claim_boundary="predictor ranking only; not execution certification or semantic equivalence",
                payload_ref={"kind":"fractal_hallway_workload_prediction","workload_id":wid},evidence_status="candidate_only")
            predictor_route_refs[wid]=wr
            for candidate in pred["known_glyph_candidates"]:
                gr=glyph_routes.get(candidate["glyph"])
                if gr:
                    _relation_link(links,route_ids,wr,gr,"predicts_candidate_glyph","reopened_predictor_not_execution",
                        [predictor["predictor_cone_address"],address.address_id,cone.cone_address,candidate["glyph_address"]],
                        pred["residuals"],"ranked contract fit only; child composition and execution require independent replay")
            selected_child=pred["route"].get("child_address_id")
            source_key=source_objects[0][0]
            target_child=by_kind_key.get(("child",source_key,selected_child)) if selected_child else None
            if target_child:
                _relation_link(links,route_ids,wr,target_child,"routes_through_opened_hallway","reopened_predictor_not_execution",
                    [predictor["predictor_cone_address"],cone.cone_address,selected_child],pred["route"]["residuals"],
                    "bounded route through opened structure; residuals still apply")
            else:
                root_r=by_source[source_key]["root_route"]
                _relation_link(links,route_ids,wr,root_r,"falls_back_to_opened_root","reopened_predictor_not_execution",
                    [predictor["predictor_cone_address"],address.address_id],pred["route"]["residuals"],
                    "no matching opened child route; deeper target remains unresolved")
    # Root/child and child/wave paths are explicit opening paths.
    for source_key,src_addr,src_cone,wave in source_objects:
        source_info=by_source[source_key]
        _relation_link(links,route_ids,source_info["root_route"],source_info["cone_route"],
            "opens_bound_cone","reopened_depth_wave_cone",[src_addr.address_id,src_cone.cone_address],
            src_cone.unresolved,"cone is only the structure actually opened from this exact root")
        _relation_link(links,route_ids,source_info["cone_route"],source_info["wave_route"],
            "compactifies_to_onehot_wave","reopened_address_onehot_wave",[src_cone.cone_address,wave.wave_address],
            wave.unresolved,"wave preserves frame identity and frontier residuals")
        for glyph in wave.wave_glyphs:
            gr=source_info["glyphs"].get(glyph.wave_glyph_address)
            if gr:
                _relation_link(links,route_ids,source_info["wave_route"],gr,"contains_addressed_pattern","reopened_address_onehot_wave",
                    [wave.wave_address,glyph.wave_glyph_address],glyph.residuals,
                    "wave pattern is a denotation of opened structure, not a newly created operation")
        for fr_route in [r for r in routes if r["kind"]=="frontier" and r["source_key"]==source_key]:
            _relation_link(links,route_ids,source_info["cone_route"],fr_route["route_id"],"retains_unopened_frontier",
                "reopened_address_onehot_wave",[src_cone.cone_address,fr_route["target_address_id"]],
                [fr_route["residual_kind"]],"frontier target is inspectable but is not treated as opened")
        for child in src_cone.child_addresses:
            cr=source_info["children"].get(child.address_id)
            if cr:
                _relation_link(links,route_ids,source_info["root_route"],cr,"opens_recursive_child","reopened_depth_wave_cone",
                    [src_addr.address_id,src_cone.cone_address,child.address_id,child.payload_address_id],(),
                    "actual active recursive address; box and cube aperture families remain distinct")
                matching=[g for g in wave.wave_glyphs if g.child_address_id==child.address_id]
                for glyph in matching:
                    gr=source_info["glyphs"].get(glyph.wave_glyph_address)
                    if gr:
                        _relation_link(links,route_ids,cr,gr,"opens_wave_pattern_for_child","reopened_address_onehot_wave",
                            [src_cone.cone_address,wave.wave_address,child.address_id,glyph.wave_glyph_address],glyph.residuals,
                            "pattern denotation references source addresses; it is not a new executable glyph")
        for glyph in wave.wave_glyphs:
            gr=source_info["glyphs"].get(glyph.wave_glyph_address)
            if not gr: continue
            for proj in glyph.projections:
                pr=by_kind_key.get(("projection_by_glyph",source_key,glyph.wave_glyph_address+":"+str(proj.rank)))
                if pr:
                    _relation_link(links,route_ids,gr,pr,"has_projection_view","reopened_address_onehot_wave",
                        [wave.wave_address,glyph.wave_glyph_address,proj.signature_address],glyph.residuals,
                        "projection is a view of the same addressed pattern; omitted axes remain residuals")
        for frame in wave.frames:
            fr=source_info["frames"].get(frame.frame_address)
            if fr:
                _relation_link(links,route_ids,source_info["root_route"],fr,"opens_structural_frame","reopened_address_onehot_wave",
                    [src_addr.address_id,wave.wave_address,frame.frame_address],(),
                    "frame is a view bound to the source address and its typed aperture")
        space_route=source_info["cog64_space_route"]
        space=source_info["cog64_space"]
        matching_frame_route=source_info["frames"].get(space["source_frame"]["frame_address"])
        if matching_frame_route:
            _relation_link(links,route_ids,matching_frame_route,space_route,
                "indexes_core64_sphere504_cyclic_projection","exact_factor_product_and_ordinal_bijection",
                [src_addr.address_id,src_cone.cone_address,space["source_frame"]["frame_address"],space["space_address"]],
                space["residuals"],
                "8×8 control/translation roles × 504 heads × four aperture prefixes; winding lifts and unopened fractal depths are outside this finite count")
        cog_glyph_route=glyph_routes.get("BC.COG64.CHAIN")
        if cog_glyph_route:
            _relation_link(links,route_ids,space_route,cog_glyph_route,
                "traverses_factorized_state_space","registered_parameterized_cog_not_per_state_glyph",
                [space["space_address"],"BC.COG64.CHAIN"],space["residuals"],
                "one parameterized executable cog denotes the transition family; no glyph is created per cyclic state")
        project_glyph_route=glyph_routes.get("BC.COG64.SPACE.PROJECT")
        if project_glyph_route:
            _relation_link(links,route_ids,space_route,project_glyph_route,
                "projects_full_cyclic_space_in_bounded_pages","registered_projection_with_page_receipts",
                [space["space_address"],"BC.COG64.SPACE.PROJECT"],space["residuals"],
                "all 129024 cyclic states are traversed in bounded pages; full row collection is regenerated on demand and no per-state glyph is created")
        core_route=scale_routes.get("core64")
        if core_route:
            _relation_link(links,route_ids,space_route,core_route,
                "uses_core64_factor","exact_named_scale_factor",[space["space_address"],"core64"],
                space["residuals"],"core64 capacity 64 is factorized as 8 control × 8 translation lane pairs; axes are not physically calibrated")
        _relation_link(links,route_ids,space_route,sphere_route,
            "uses_sphere504_phase","exact_integer_cycle_factor",[space["space_address"],"sphere504"],
            space["residuals"],"504-head phase carries winding separately; cycle cardinality does not determine global fractal depth")
        for stage_index,stage_route in aperture_stage_routes.items():
            _relation_link(links,route_ids,space_route,stage_route,
                "selects_prime_harmonic_aperture_stage","exact_stage_prefix",[space["space_address"],stage_route],
                space["residuals"],"aperture prefix selects which 3/5/7 prime-cog views are active; it does not multiply physical ticks")
    # Collision candidates become indexed control-surface routes, not new glyphs.
    # Their full prime/plane witnesses remain in the separate staging evidence.
    if collision_index is not None:
        source_key_rows={r["source_key"]:r for r in source_rows}
        for cx in collision_index["source_contexts"]:
            got=source_key_rows.get(cx["source_key"])
            if got is None or got["root_address_id"]!=cx["root_address_id"] or got["cone_address"]!=cx["cone_address"]:
                raise ValueError("collision_stage_context_missing_from_relation_map")
        governing_keys=sorted(x["source_key"] for x in collision_index["source_contexts"])
        def lock_refs(keys: Sequence[str]) -> list[dict[str, Any]]:
            return [{"source_key":x["source_key"],"lock_address":x.get("lock_address"),
                     "opening_address":x.get("opening_address")}
                    for x in collision_index["source_contexts"] if x["source_key"] in set(keys)]
        stage_r=add_route("collision_stage",collision_index["index_address"],"Collision cone fidelity stage","comparison",
            target_address_id=collision_index["stage_address"],stage_address=collision_index["stage_address"],
            governing_source_keys=governing_keys,governing_lock_addresses=lock_refs(governing_keys),
            depth=collision_index["max_candidate_depth"],required_aperture_stage_cap=3,
            required_transition_families=["collision_probe","sphere504","prime3","prime5","prime7"],
            candidate_count=collision_index["candidate_count_staged"],pair_scan_count=len(collision_index["pair_fidelity_scans"]),
            winding_alias_group_count=len(collision_index["sphere_winding_alias_groups"]),
            payload_ref=collision_index["payload_ref"],evidence_status="indexed_collision_stage_full_witnesses_external")
        scan_routes={}
        for scan in collision_index["pair_fidelity_scans"]:
            sr=add_route("collision_fidelity_scan",scan["pair_scan_address"],
                f"Sphere/prime fidelity · {scan['left_label']} ↔ {scan['right_label']}","comparison",
                target_address_id=scan["pair_scan_address"],stage_route_id=stage_r,
                governing_source_keys=scan["governing_source_keys"],governing_lock_addresses=lock_refs(scan["governing_source_keys"]),
                depth=collision_index["max_candidate_depth"],required_aperture_stage_cap=3,
                required_transition_families=["collision_probe","sphere504","prime3","prime5","prime7"],
                comparison_count=scan["comparison_count"],signed_ticks=scan["signed_ticks"],plane_count=scan["plane_count"],
                left_root_address_id=scan["left_root_address_id"],right_root_address_id=scan["right_root_address_id"],
                payload_ref=scan["payload_ref"],evidence_status="compact_scan_route_detailed_evidence_external")
            scan_routes[scan["pair_scan_address"]]=sr
            _relation_link(links,route_ids,stage_r,sr,"contains_pair_fidelity_scan","reopened_collision_stage_index",
                [collision_index["index_address"],scan["pair_scan_address"]],(),
                "one scan is shared by all candidate occurrences for this source pair")
        alias_routes={}
        for ix,alias in enumerate(collision_index["sphere_winding_alias_groups"]):
            ar=add_route("sphere_winding_alias",collision_index["stage_address"]+":alias:"+str(ix),
                f"Sphere head {alias['head']} · distinct winding lifts","comparison",
                target_address_id=collision_index["stage_address"]+":alias:"+str(ix),stage_route_id=stage_r,
                head=alias["head"],members=alias["members"],governing_source_keys=alias["governing_source_keys"],
                governing_lock_addresses=lock_refs(alias["governing_source_keys"]),depth=collision_index["max_candidate_depth"],
                required_aperture_stage_cap=3,required_transition_families=["collision_probe","sphere504","prime3","prime5","prime7"],
                payload_ref=alias["payload_ref"],evidence_status="cyclic_alias_not_address_identity")
            alias_routes[ix]=ar
            _relation_link(links,route_ids,stage_r,ar,"indexes_winding_alias","exact_head_with_distinct_winding_evidence",
                [collision_index["stage_address"],str(alias["head"])],(),alias["claim_boundary"])
            for member in alias["members"]:
                info=by_source.get(member["source_key"])
                if info:
                    _relation_link(links,route_ids,ar,info["root_route"],"member_root_of_cyclic_alias","full_address_and_prime_harmonic_address",
                        [member["address_id"],member["root_address_id"]],(),alias["claim_boundary"])
        for cand in collision_index["candidates"]:
            cr=add_route("collision_candidate",cand["candidate_address"],
                f"Projected overlap · depth {cand['depth']} · {cand['left_label']} ↔ {cand['right_label']}","comparison",
                target_address_id=cand["candidate_address"],stage_route_id=stage_r,
                pair_scan_route_id=scan_routes.get(cand["pair_fidelity_scan"]),pair_fidelity_scan=cand["pair_fidelity_scan"],
                depth=cand["depth"],wave_distance=cand["wave_distance"],physical_coord6=cand["physical_coord6"],
                left_label=cand["left_label"],right_label=cand["right_label"],
                left_root_address_id=cand["left_root_address_id"],right_root_address_id=cand["right_root_address_id"],
                left_node_ids=cand["left_node_ids"],right_node_ids=cand["right_node_ids"],
                governing_source_keys=cand["governing_source_keys"],governing_lock_addresses=lock_refs(cand["governing_source_keys"]),
                required_aperture_stage_cap=3,required_transition_families=["collision_probe","sphere504","prime3","prime5","prime7"],
                same_address_identity=cand["same_address_identity"],merging_permitted=False,
                payload_ref=cand["payload_ref"],evidence_status="projected_overlap_candidate_not_merged_identity",
                claim_boundary=cand["claim_boundary"])
            _relation_link(links,route_ids,stage_r,cr,"stages_projected_overlap","candidate_retains_both_addressed_members",
                [collision_index["stage_address"],cand["candidate_address"]],(),cand["claim_boundary"])
            scan_route=scan_routes.get(cand["pair_fidelity_scan"])
            if scan_route:
                _relation_link(links,route_ids,scan_route,cr,"supports_candidate_with_shared_pair_scan","prime_harmonic_and_six_plane_fidelity_scan",
                    [cand["pair_fidelity_scan"],cand["candidate_address"]],(),
                    "fidelity scan is shared evidence and does not imply address merge")
            for source_key,root_field,node_field in ((cand["left_source_key"],"left_root_address_id","left_node_ids"),
                                                     (cand["right_source_key"],"right_root_address_id","right_node_ids")):
                info=by_source.get(source_key)
                if info:
                    _relation_link(links,route_ids,cr,info["root_route"],"candidate_member_source_root","root-bound opened-node projection",
                        [cand[root_field],cand["candidate_address"]],(),cand["claim_boundary"])
                    _relation_link(links,route_ids,cr,info["cone_route"],"candidate_member_source_cone","actual opened cone node IDs",
                        [*cand[node_field],cand["candidate_address"]],(),cand["claim_boundary"])
    links=sorted({row["relation_id"]:row for row in links}.values(),key=lambda x:x["relation_id"])
    body={"schema":"BC-ADDRESS-RELATION-MAP-1","source_contexts":source_rows,
        "primary_root_address_id":address.address_id,"primary_cone_address":cone.cone_address,
        "wave_map_address":wave_map.map_address,"wave_comparison_reopen":wave_map_reopen,
        "learning_map_address":None if learning_map is None else learning_map.map_address,
        "learning_map_reopen":learning_reopen,
        "predictor_address":None if predictor is None else predictor["predictor_cone_address"],
        "predictor_reopen":predictor_reopen,
        "catalogue":{"count":len(glyph_rows),"digest":glyph_digest,"routes_are_references_not_copied_executors":True},
        "routes":sorted(routes,key=lambda x:(x["kind"],x["source_key"],x["route_id"])),
        "relations":links,
        "summary":{"route_count":len(routes),"relation_count":len(links),
            "opened_root_count":len(source_objects),"opened_child_route_count":sum(x["kind"]=="child" for x in routes),
            "wave_pattern_count":sum(x["kind"]=="wave_glyph" for x in routes),
            "projection_route_count":sum(x["kind"]=="projection" for x in routes),
            "cross_rank_link_count":sum(x["relation"]=="projects_between_dimensions" for x in links),
            "shared_projection_class_count":sum(x["kind"]=="wave_match_class" for x in routes),
            "typed_frame_class_count":sum(x["kind"]=="frame_match_class" for x in routes),
            "learning_evidence_count":sum(x["kind"]=="learning_evidence" for x in routes),
            "workload_count":sum(x["kind"]=="workload" for x in routes),
            "learning_witness_count":sum(x["kind"]=="learning_witness" for x in routes),
            "named_scale_route_count":sum(x["kind"]=="scale_route" for x in routes),
            "cog64_state_space_route_count":sum(x["kind"]=="cog64_state_space" for x in routes),
            "harmonic_aperture_stage_route_count":sum(x["kind"]=="harmonic_aperture_stage" for x in routes),
            "sphere504_cycle_route_count":sum(x["kind"]=="sphere504_cycle" for x in routes),
            "collision_stage_route_count":sum(x["kind"]=="collision_stage" for x in routes),
            "collision_fidelity_scan_route_count":sum(x["kind"]=="collision_fidelity_scan" for x in routes),
            "sphere_winding_alias_route_count":sum(x["kind"]=="sphere_winding_alias" for x in routes),
            "collision_candidate_route_count":sum(x["kind"]=="collision_candidate" for x in routes),
            "cog64_cyclic_configurations_per_source":_COG64_CONFIG_CYCLE_STATES,
            "unopened_frontier_count":sum(x["kind"]=="frontier" for x in routes),
            "unknown_global_center_depth":True},
        "inputs":{"related_sources":[{"root_address_id":r["root_address_id"],"cone_address":r["cone_address"],"source_key":r["source_key"]} for r in source_rows[1:]],
            "ledger_address":None if ledger is None else ledger.address,"workloads":workload_rows,"top_k":top_k,
            "collision_stage_index":collision_index},
        "policy":{"library_is_control_surface":True,"patterns_are_denotations_not_new_glyph_implementations":True,
            "underlying_address_space_is_not_exhaustively_enumerated":True,"all_routes_require_real_source_binding":True,
            "comparison_match_is_not_semantic_equivalence":True,"unopened_frontiers_are_not_open_routes":True,
            "box_cube_same_cardinality_is_not_equivalence":True,"profile_rows_added":0,"proposal_rows_added":0,
            "glyph_admission":False,"source_write":False,"persistent_save":False,"cold_commit":False}}
    body["map_address"]=_sha256_text(_canonical_json(body))
    return AddressRelationMap("BC-ADDRESS-RELATION-MAP-1",body["map_address"],_canonical_json(body))


def reopen_address_relation_map(address: BCFloorAddress, cone: DepthWaveCone, relation_map: AddressRelationMap,
                                related_sources: Sequence[Mapping[str, Any]] = (),
                                ledger: GlyphLearningLedger | None = None,
                                collision_stage: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(relation_map,AddressRelationMap):
        return {"schema":"BC-ADDRESS-RELATION-MAP-REOPEN-1","pass":False,"reason":"address_relation_map_required"}
    try:
        body=json.loads(relation_map.payload_json)
        if body.get("map_address") != relation_map.map_address:
            raise ValueError("relation_map_embedded_address_mismatch")
        hash_body={k:v for k,v in body.items() if k!="map_address"}
        if _sha256_text(_canonical_json(hash_body)) != relation_map.map_address:
            raise ValueError("relation_map_content_address_mismatch")
        if body["inputs"].get("ledger_address") != (None if ledger is None else ledger.address):
            raise ValueError("relation_map_ledger_binding_mismatch")
        embedded_collision=body["inputs"].get("collision_stage_index")
        if collision_stage is not None and _collision_stage_route_index(collision_stage) != embedded_collision:
            raise ValueError("relation_map_collision_stage_binding_mismatch")
        rebuilt=build_address_relation_map(address,cone,related_sources,ledger,body["inputs"]["workloads"],body["inputs"]["top_k"],embedded_collision)
        passed=rebuilt==relation_map and rebuilt.map_address==relation_map.map_address
        return {"schema":"BC-ADDRESS-RELATION-MAP-REOPEN-1","pass":passed,
            "map_address":relation_map.map_address,"rebuilt_map_address":rebuilt.map_address,
            "source_context_count":len(body["source_contexts"]),"route_count":body["summary"]["route_count"],
            "relation_count":body["summary"]["relation_count"],"wave_map_reopened":body["wave_comparison_reopen"].get("pass",False),
            "learning_map_reopened":None if body["learning_map_reopen"] is None else body["learning_map_reopen"].get("pass",False),
            "predictor_reopened":None if body["predictor_reopen"] is None else body["predictor_reopen"].get("pass",False),
            "profile_rows_added":0,"proposal_rows_added":0,"glyph_admission":False,"persistent_save":False,
            "source_write":False,"cold_commit":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-ADDRESS-RELATION-MAP-REOPEN-1","pass":False,
            "reason":f"relation_map_rebuild_failed:{type(exc).__name__}:{exc}"}



def _open_address_relation_route_verified(address: BCFloorAddress, cone: DepthWaveCone,
                                relation_map: AddressRelationMap, route_id: str,
                                related_sources: Sequence[Mapping[str, Any]] = (),
                                ledger: GlyphLearningLedger | None = None,
                                _route_cache: dict[str, Any] | None = None) -> dict[str, Any]:
    """Open an indexed route into actual source payloads. An unopened frontier
    can be inspected as a residual but can never be returned as an opened state.
    """
    # Private helper: caller has already reopened the map against these exact inputs.
    body=json.loads(relation_map.payload_json)
    if _route_cache is None:
        _route_cache={}
    wave_cache=_route_cache.setdefault("waves_by_key", {})
    compare_cache=_route_cache.setdefault("wave_comparison", {})
    predictor_cache=_route_cache.setdefault("predictor", {})
    def cached_wave(src_addr: BCFloorAddress, src_cone: DepthWaveCone, sk: str) -> AddressOneHotWave:
        if sk not in wave_cache:
            wave_cache[sk]=(src_addr,src_cone,build_address_onehot_wave(src_addr,src_cone),sk)
        return wave_cache[sk][2]
    route=next((x for x in body["routes"] if x["route_id"]==route_id),None)
    if route is None:
        return {"schema":"BC-ADDRESS-RELATION-OPEN-1","pass":False,"reason":"route_id_not_indexed","route_id":route_id}
    all_sources=[(address,cone,"primary")]
    all_sources.extend((x["address"],x["cone"],f"related:{ix}") for ix,x in enumerate(related_sources))
    match=None
    kind=route["kind"]
    wave_required=kind in {"wave","child","frame","frame_word","wave_glyph","projection","frontier"}
    for src_addr,src_cone,label in all_sources:
        sk=_sha256_text(_canonical_json({"root":src_addr.address_id,"cone":src_cone.cone_address}))[:24]
        if route["source_key"]==sk:
            wave=cached_wave(src_addr,src_cone,sk) if wave_required else None
            match=(src_addr,src_cone,wave,sk);break
    kind=route["kind"];payload=None;opened=True
    if kind=="workload":
        primary_key=_sha256_text(_canonical_json({"root":address.address_id,"cone":cone.cone_address}))[:24]
        if primary_key not in wave_cache:
            wave_cache[primary_key]=(address,cone,build_address_onehot_wave(address,cone),primary_key)
        match=wave_cache[primary_key]
    if kind=="root":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        payload=match[0].as_dict()
    elif kind=="cone":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        payload=match[1].as_dict()
    elif kind=="wave":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        payload=match[2].as_dict()
    elif kind=="child":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        child=next((x for x in match[1].child_addresses if x.address_id==route["target_address_id"]),None)
        if child is None: raise LookupError("child_address_not_present_in_opened_cone")
        payload={"child":child.as_dict(),"level":match[0].levels[child.level_index].as_dict(),
            "parent_address_id":match[0].address_id,"aperture_families_distinct":True}
    elif kind=="frame":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        item=next((x for x in match[2].frames if x.frame_address==route["target_address_id"]),None)
        if item is None: raise LookupError("frame_not_in_opened_wave")
        payload=item.as_dict()
    elif kind=="frame_word":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        found=None
        for frame in match[2].frames:
            for word in frame.words:
                if word.word_address==route["target_address_id"] and frame.frame_address+":"+word.word_address==route["target_key"]:
                    found={"frame":frame.as_dict(),"word":word.as_dict()};break
            if found: break
        if found is None: raise LookupError("typed_frame_word_not_found")
        payload=found
    elif kind=="wave_glyph":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        payload=open_address_wave_glyph(match[2],route["target_address_id"]).as_dict()
    elif kind=="projection":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        glyph=open_address_wave_glyph(match[2],route["wave_glyph_address"])
        proj=next((x for x in glyph.projections if x.rank==route["rank"]),None)
        if proj is None: raise LookupError("projection_rank_not_found")
        payload={"wave_glyph":glyph.as_dict(),"projection":proj.as_dict()}
    elif kind=="frontier":
        if match is None: raise ValueError("relation_route_source_not_supplied")
        frontier=next((x for x in match[2].frontier_residuals if x.target_state_address_id==route["target_address_id"] and
            x.child_address_id==route["child_address_id"] and x.depth==route["depth"] and
            x.next_wave_distance==route["next_wave_distance"] and x.from_state_address_id==route["from_state_address_id"] and
            x.axis==route["axis"] and x.direction==route["direction"]),None)
        if frontier is None: raise LookupError("frontier_residual_not_found")
        opened=False;payload={"frontier":frontier.as_dict(),"opened":False,
            "reason":"frontier_is_indexed_evidence_not_an_opened_state","deeper_route_permitted":False}
    elif kind=="glyph":
        spec=GLYPH_CATALOG.resolve(route["target_key"]);record=REGISTRY.resolve(spec.executor_name)
        fn=getattr(record.executor,"__func__",record.executor); code=getattr(fn,"__code__",None)
        payload={"glyph_spec":GLYPH_CATALOG.describe()[GLYPH_CATALOG.names().index(spec.name)],
            "executor":{"name":record.operation,"effect_scope":record.effect,"registered":True,
                "implementation_source_path":None if code is None else pathlib.Path(code.co_filename).name,
                "implementation_source_line":None if code is None else code.co_firstlineno},
            "implementation_copy_created":False}
    elif kind=="wave_match_class":
        cache_key=tuple(_sha256_text(_canonical_json({"root":a.address_id,"cone":c.cone_address}))[:24] for a,c,_ in all_sources)
        if cache_key not in compare_cache:
            compare_cache[cache_key]=compare_address_onehot_waves(tuple(
                cached_wave(a,c,sk) for (a,c,_),sk in zip(all_sources,cache_key)))
        cmap=compare_cache[cache_key]
        item=next((x for x in cmap.classes if x.class_address==route["target_address_id"]),None)
        if item is None: raise LookupError("wave_match_class_not_found")
        payload=item.as_dict()
    elif kind=="frame_match_class":
        cache_key=tuple(_sha256_text(_canonical_json({"root":a.address_id,"cone":c.cone_address}))[:24] for a,c,_ in all_sources)
        if cache_key not in compare_cache:
            compare_cache[cache_key]=compare_address_onehot_waves(tuple(
                cached_wave(a,c,sk) for (a,c,_),sk in zip(all_sources,cache_key)))
        cmap=compare_cache[cache_key]
        item=next((x for x in cmap.frame_classes if x.class_address==route["target_address_id"]),None)
        if item is None: raise LookupError("frame_match_class_not_found")
        payload=item.as_dict()
    elif kind=="dimensional_link":
        cache_key=tuple(_sha256_text(_canonical_json({"root":a.address_id,"cone":c.cone_address}))[:24] for a,c,_ in all_sources)
        if cache_key not in compare_cache:
            compare_cache[cache_key]=compare_address_onehot_waves(tuple(
                cached_wave(a,c,sk) for (a,c,_),sk in zip(all_sources,cache_key)))
        cmap=compare_cache[cache_key]
        item=next((x for x in cmap.dimensional_links if _sha256_text(_canonical_json(x.as_dict()))[:24]==route["target_address_id"]),None)
        if item is None: raise LookupError("dimensional_link_not_found")
        payload=item.as_dict()
    elif kind=="cog64_state_space":
        if match is None: raise ValueError("cog64_state_space_source_not_supplied")
        payload=build_64core_harmonic_state_space(match[0],route["frame_selector"])
        if payload["space_address"]!=route["target_address_id"] or payload["source_frame"]["frame_address"]!=route["source_frame_address"]:
            raise ValueError("cog64_state_space_route_binding_mismatch")
    elif kind=="harmonic_aperture_stage":
        stage=route.get("stage_index")
        if type(stage) is not int or not 0<=stage<len(HARMONIC_APERTURE_STAGES): raise ValueError("harmonic_aperture_stage_index_invalid")
        prefix=list(HARMONIC_APERTURE_STAGES[stage])
        if prefix!=route.get("prime_prefix"): raise ValueError("harmonic_aperture_stage_binding_mismatch")
        payload={"stage_index":stage,"aperture_prefix":prefix,"active_prime_lane_count":len(prefix),
            "sphere_head_count":HARMONIC_HEADS,"core64_lane_pairs":64,
            "stage_configuration_count":64*HARMONIC_HEADS,
            "active_prime_lanes":[p for p in (3,5,7) if p in prefix],
            "aperture_selects_views_not_tick_multiplier":True,
            "claim_boundary":"exact aperture prefix definition; not physical calibration"}
    elif kind=="sphere504_cycle":
        payload={"name":"sphere504","head_count":HARMONIC_HEADS,"radices":list(SPHERE504_RADICES),
            "factor_product":(SPHERE504_RADICES[0]*SPHERE504_RADICES[1]*SPHERE504_RADICES[2]),"aperture_stage_count":len(HARMONIC_APERTURE_STAGES),
            "winding_stored_separately":True,"claim_boundary":"exact integer phase cycle; not physical RPM calibration"}
    elif kind in {"collision_stage","collision_fidelity_scan","sphere_winding_alias","collision_candidate"}:
        # Open the compact relation/control descriptor. The complete detailed scan and
        # transition witnesses remain in the separately addressable evidence artifact.
        if kind=="collision_stage":
            payload={"stage_address":route["stage_address"],"candidate_count":route["candidate_count"],
                "pair_scan_count":route["pair_scan_count"],"winding_alias_group_count":route["winding_alias_group_count"],
                "governing_source_keys":route["governing_source_keys"],"governing_lock_addresses":route["governing_lock_addresses"],
                "payload_ref":route["payload_ref"],"full_evidence_external":True,"frontier_traversal_performed":False}
        elif kind=="collision_fidelity_scan":
            payload={k:route.get(k) for k in ("target_address_id","stage_route_id","governing_source_keys","governing_lock_addresses",
                "comparison_count","signed_ticks","plane_count","left_root_address_id","right_root_address_id","payload_ref")}
            payload["full_fidelity_rows_external"]=True
        elif kind=="sphere_winding_alias":
            payload={k:route.get(k) for k in ("target_address_id","head","members","governing_source_keys","governing_lock_addresses","payload_ref")}
            payload["members_remain_distinct"]=True
        else:
            payload={k:route.get(k) for k in ("target_address_id","stage_route_id","pair_scan_route_id","pair_fidelity_scan",
                "depth","wave_distance","physical_coord6","left_label","right_label","left_root_address_id",
                "right_root_address_id","left_node_ids","right_node_ids","governing_source_keys","governing_lock_addresses",
                "same_address_identity","merging_permitted","payload_ref","claim_boundary")}
            payload["full_candidate_witness_external"]=True
            payload["candidate_is_new_glyph"]=False
    elif kind=="scale_route":
        item=next((x for x in HARMONIC_STACKS if x.name==route["target_address_id"]),None)
        if item is None: raise LookupError("named_scale_route_not_found")
        payload={"name":item.name,"shape":list(item.shape),"capacity":item.capacity,"shell":item.shell,
            "address_family":item.address_family,"capacity_is_not_center_depth":True}
    elif kind in {"learning_evidence","learning_match_class","learning_witness"}:
        if ledger is None: raise ValueError("learning_ledger_required_to_open_learning_route")
        lmap=build_learning_comparison_map(ledger)
        if kind=="learning_evidence":
            item=next((x for x in ledger.evidence if x.evidence_address==route["target_address_id"]),None)
            payload=None if item is None else item.as_dict()
        elif kind=="learning_match_class":
            item=next((x for x in lmap.classes if x.class_address==route["target_address_id"]),None)
            payload=None if item is None else item.as_dict()
        elif kind=="learning_witness":
            item=next((x for x in ledger.evidence if x.evidence_address==route.get("evidence_address")),None)
            if item is None: raise LookupError("witness_source_evidence_not_found")
            ctx=json.loads(item.context_json)
            witness=ctx.get("witness")
            if not isinstance(witness,Mapping) or witness.get("witness_id")!=route["target_address_id"]:
                raise ValueError("embedded_witness_binding_mismatch")
            payload={"evidence_address":item.evidence_address,"witness":witness,
                "source_address":item.source_address,"source_container_address":item.source_container_address,
                "witness_is_full_evidence_child":True}
        if payload is None: raise LookupError("learning_route_target_not_found")
    elif kind=="workload":
        if match is None: raise ValueError("workload_route_primary_source_required")
        workload_rows=body["inputs"]["workloads"]
        pkey=(match[0].address_id,match[1].cone_address,_sha256_text(_canonical_json(workload_rows))[:24],body["inputs"]["top_k"])
        if pkey not in predictor_cache:
            predictor_cache[pkey]=build_fractal_hallway_predictor_cone(match[0],match[1],workload_rows,top_k=body["inputs"]["top_k"])
        predictor=predictor_cache[pkey]
        payload=next((x for x in predictor["predictions"] if x["workload_id"]==route["target_address_id"]),None)
        if payload is None: raise LookupError("workload_prediction_not_found")
        payload={"prediction":payload,"execution_certified":False}
    else:
        return {"schema":"BC-ADDRESS-RELATION-OPEN-1","pass":False,"reason":"unsupported_route_kind","kind":kind}
    return {"schema":"BC-ADDRESS-RELATION-OPEN-1","pass":True,"route_id":route_id,
        "kind":kind,"route_state":route["route_state"],"opened":opened,"payload":payload,
        "relation_map_address":relation_map.map_address,"map_reopened":True,
        "source_refs":route.get("payload_ref"),"residuals":route.get("residuals",[]),
        "claim_boundary":route.get("claim_boundary","route opening does not establish semantic or physical equivalence")}



def open_address_relation_route(address: BCFloorAddress, cone: DepthWaveCone,
                                relation_map: AddressRelationMap, route_id: str,
                                related_sources: Sequence[Mapping[str, Any]] = (),
                                ledger: GlyphLearningLedger | None = None) -> dict[str, Any]:
    """Verify the control map, then open one route into the actual payload."""
    reopened=reopen_address_relation_map(address,cone,relation_map,related_sources,ledger)
    if not reopened.get("pass"):
        return {"schema":"BC-ADDRESS-RELATION-OPEN-1","pass":False,
                "reason":"relation_map_must_reopen_before_route_open","reopen":reopened}
    cache={"waves_by_key":{},"wave_comparison":{},"predictor":{}}
    return _open_address_relation_route_verified(address,cone,relation_map,route_id,related_sources,ledger,cache)


def _relation_batch_body(address: BCFloorAddress, cone: DepthWaveCone, relation_map: AddressRelationMap,
                         route_ids: Sequence[str], start_index: int, max_items: int,
                         max_output_bytes: int, records: Sequence[Mapping[str, Any]], next_index: int,
                         related_sources: Sequence[Mapping[str, Any]], ledger: GlyphLearningLedger) -> dict[str, Any]:
    return {"schema":"BC-ADDRESS-RELATION-OPEN-BATCH-1","root_address_id":address.address_id,
        "cone_address":cone.cone_address,"map_address":relation_map.map_address,
        "route_ids":list(route_ids),"start_index":start_index,"max_items":max_items,
        "max_output_bytes":max_output_bytes,"next_index":next_index,
        "complete":next_index>=len(route_ids),"budget_exhausted":next_index<len(route_ids) and len(records)>=0,
        "records":[dict(r) for r in records],"opened_count":sum(r.get("pass") is True and r.get("opened") is True for r in records),
        "record_count":len(records),"failed_count":sum(r.get("pass") is not True for r in records),
        "hydrated_payload_count":sum(r.get("pass") is True and r.get("opened") is True and r.get("payload") is not None for r in records),
        "route_ids_are_handles_not_payloads":True,"frontiers_remain_unopened":True,
        "related_root_ids":[x["address"].address_id for x in related_sources],
        "ledger_address":None if ledger is None else ledger.address,
        "claim_boundary":"each route is opened only from a previously reopened map; batch boundaries do not imply deeper structure or semantic equivalence"}


def open_address_relation_routes(address: BCFloorAddress, cone: DepthWaveCone, relation_map: AddressRelationMap,
                                route_ids: Sequence[str], related_sources: Sequence[Mapping[str, Any]] = (),
                                ledger: GlyphLearningLedger | None = None, start_index: int = 0,
                                max_items: int = 32, max_output_bytes: int = 1_048_576) -> dict[str, Any]:
    """Open a bounded batch after one map verification, reusing cached waves/comparisons.

    Records always include full payloads for routes that fit. If the byte budget is reached,
    the response gives a continuation index; it never truncates a payload or opens a frontier.
    """
    if not isinstance(address,BCFloorAddress) or not isinstance(cone,DepthWaveCone) or not isinstance(relation_map,AddressRelationMap):
        raise TypeError("batch_open_requires_address_cone_and_relation_map")
    if not isinstance(route_ids,(tuple,list)) or len(route_ids)>256 or any(
        not isinstance(r,str) or len(r)!=24 or any(c not in "0123456789abcdef" for c in r) for r in route_ids):
        raise ValueError("route_id_batch_must_contain_at_most_256_24hex_ids")
    if len(set(route_ids))!=len(route_ids):
        raise ValueError("route_id_batch_duplicates_not_allowed")
    if type(start_index) is not int or not 0<=start_index<=len(route_ids):
        raise ValueError("batch_start_index_out_of_range")
    if type(max_items) is not int or not 1<=max_items<=64:
        raise ValueError("batch_item_limit_must_be_1_to_64")
    if type(max_output_bytes) is not int or not 1024<=max_output_bytes<=4*1024*1024:
        raise ValueError("batch_output_budget_must_be_1024_to_4194304_bytes")
    reopened=reopen_address_relation_map(address,cone,relation_map,related_sources,ledger)
    if not reopened.get("pass"):
        return {"schema":"BC-ADDRESS-RELATION-OPEN-BATCH-1","pass":False,
            "reason":"relation_map_must_reopen_before_batch_open","map_reopen":reopened}
    body=json.loads(relation_map.payload_json)
    known={row["route_id"] for row in body["routes"]}
    cache={"waves_by_key":{},"wave_comparison":{},"predictor":{}}
    # Hydrate each supplied root/cone only once for the whole batch.
    all_sources=[(address,cone,"primary")]+[(x["address"],x["cone"],f"related:{ix}") for ix,x in enumerate(related_sources)]
    records=[]; next_index=start_index
    limit=min(len(route_ids),start_index+max_items)
    budget_exhausted=False
    for idx in range(start_index,limit):
        rid=route_ids[idx]
        try:
            if rid not in known:
                record={"schema":"BC-ADDRESS-RELATION-OPEN-1","pass":False,"reason":"route_id_not_indexed","route_id":rid}
            else:
                record=_open_address_relation_route_verified(address,cone,relation_map,rid,related_sources,ledger,cache)
        except (TypeError,ValueError,LookupError,KeyError) as exc:
            record={"schema":"BC-ADDRESS-RELATION-OPEN-1","pass":False,"reason":f"{type(exc).__name__}:{exc}","route_id":rid}
        prospective=records+[record]
        candidate_body=_relation_batch_body(address,cone,relation_map,route_ids,start_index,max_items,max_output_bytes,
            prospective,idx+1,related_sources,ledger)
        candidate_body["budget_exhausted"]=(idx+1<min(len(route_ids),start_index+max_items))
        candidate_size=len(_canonical_json(candidate_body).encode("utf-8"))
        if candidate_size>max_output_bytes:
            budget_exhausted=True
            if not records:
                return {"schema":"BC-ADDRESS-RELATION-OPEN-BATCH-1","pass":False,
                    "reason":"single_route_exceeds_output_budget","route_id":rid,"required_at_least_bytes":candidate_size,
                    "max_output_bytes":max_output_bytes,"next_index":start_index,"partial_payload_returned":False}
            break
        records.append(record); next_index=idx+1
    body_out=_relation_batch_body(address,cone,relation_map,route_ids,start_index,max_items,max_output_bytes,records,next_index,related_sources,ledger)
    body_out["budget_exhausted"]=budget_exhausted or (next_index<len(route_ids) and next_index>=start_index+max_items and False)
    # Batch pass describes its own binding/integrity; per-route failures remain in records.
    body_out["pass"]=True
    body_out["all_routes_opened"]=(len(records)>0 and all(r.get("pass") is True and r.get("opened") is True for r in records))
    body_out["batch_address"]=_sha256_text(_canonical_json(body_out))[:24]
    return body_out


def reopen_address_relation_routes(address: BCFloorAddress, cone: DepthWaveCone, relation_map: AddressRelationMap,
                                   route_ids: Sequence[str], batch: Mapping[str, Any],
                                   related_sources: Sequence[Mapping[str, Any]] = (),
                                   ledger: GlyphLearningLedger | None = None) -> dict[str, Any]:
    if not isinstance(batch,Mapping) or batch.get("schema")!="BC-ADDRESS-RELATION-OPEN-BATCH-1":
        return {"schema":"BC-ADDRESS-RELATION-OPEN-BATCH-REOPEN-1","pass":False,"reason":"relation_route_batch_required"}
    try:
        rebuilt=open_address_relation_routes(address,cone,relation_map,route_ids,related_sources,ledger,
            batch["start_index"],batch["max_items"],batch["max_output_bytes"])
        same=rebuilt==dict(batch)
        return {"schema":"BC-ADDRESS-RELATION-OPEN-BATCH-REOPEN-1","pass":same,
            "batch_address":batch.get("batch_address"),"rebuilt_batch_address":rebuilt.get("batch_address"),
            "records_rebuilt":len(rebuilt.get("records",[])),"map_reopened":rebuilt.get("pass") is True,
            "frontiers_opened_as_states":False,"payloads_truncated":False,
            "claim_boundary":"batch receipt replay only; route evidence remains subject to each route's proof kind"}
    except (TypeError,ValueError,LookupError,KeyError) as exc:
        return {"schema":"BC-ADDRESS-RELATION-OPEN-BATCH-REOPEN-1","pass":False,
            "reason":f"batch_reopen_failed:{type(exc).__name__}:{exc}"}


_COG64_LANE_COUNT=8
_COG64_CONFIG_CYCLE_STATES=_COG64_LANE_COUNT*_COG64_LANE_COUNT*HARMONIC_HEADS*len(HARMONIC_APERTURE_STAGES)
_COG64_MAX_STEPS=64


def _cog64_folded_state(root_id: str, source_frame: AddressOneHotFrame,
                        control_absolute: int, translation_absolute: int,
                        harmonic_absolute: int, aperture_prefix: Sequence[int]) -> dict[str, Any]:
    control_turn,control_lane=divmod(control_absolute,_COG64_LANE_COUNT)
    translation_turn,translation_lane=divmod(translation_absolute,_COG64_LANE_COUNT)
    winding,head=divmod(harmonic_absolute,HARMONIC_HEADS)
    prefix=tuple(aperture_prefix)
    if prefix not in HARMONIC_APERTURE_STAGES:
        raise ValueError("cog64_aperture_prefix_invalid")
    core_slot=control_lane*_COG64_LANE_COUNT+translation_lane
    lanes=[prime_cog_lane_step(harmonic_absolute,0,rate).as_dict() for rate in prefix]
    body={"schema":"BC-COG64-FOLDED-STATE-1","source_address_id":root_id,
        "source_frame_address":source_frame.frame_address,"source_frame_kind":source_frame.frame_kind,
        "source_frame_depth":source_frame.depth,"source_frame_rank":source_frame.dimension_rank,
        "source_aperture_address":source_frame.aperture_address,
        "core64_stack":{"name":"core64","shape":[8,8],"capacity":64,"address_family":"core"},
        "control":{"absolute":control_absolute,"winding":control_turn,"lane":control_lane,
            "one_hot":[1 if i==control_lane else 0 for i in range(8)]},
        "translation":{"absolute":translation_absolute,"winding":translation_turn,"lane":translation_lane,
            "one_hot":[1 if i==translation_lane else 0 for i in range(8)]},
        "core_slot":core_slot,"core_one_hot":[1 if i==core_slot else 0 for i in range(64)],
        "sphere504":{"absolute_phase":harmonic_absolute,"head":head,"winding":winding},
        "aperture_prefix":list(prefix),"active_prime_cog_rates":list(prefix),"prime_lane_views":lanes,
        "cyclic_configuration_count":_COG64_CONFIG_CYCLE_STATES,
        "residuals":["control_translation_axes_are_factorized_roles_not_physical_cube_calibration",
                     "global_fractal_center_depth_unknown"]}
    body["folded_state_address"]=_sha256_text(_canonical_json(body))[:24]
    return body


def build_64core_harmonic_state_space(address: BCFloorAddress,
                                     frame_selector: str = "deepest_resolved") -> dict[str, Any]:
    """Describe a finite cyclic projection without materializing every state.

    The projection covers 8 control lanes × 8 translation lanes × 504 sphere heads ×
    four explicit aperture prefixes. Winding lifts and recursive depths are separate,
    address-bound dimensions and are intentionally not folded into this finite count.
    """
    if not isinstance(address,BCFloorAddress):
        raise TypeError("cog64_space_requires_full_floor_address")
    if not isinstance(frame_selector,str) or not frame_selector:
        raise ValueError("cog64_space_frame_selector_required")
    frame=_hf_frame_select(address,frame_selector)
    body={"schema":"BC-COG64-HARMONIC-STATE-SPACE-1","source_address_id":address.address_id,
        "frame_selector":frame_selector,"source_frame":frame.as_dict(),
        "core64":{"shape":[8,8],"capacity":64,"control_axis_states":8,"translation_axis_states":8,
                  "slot_formula":"control_lane*8+translation_lane"},
        "sphere504":{"head_states":504,"radices":list(SPHERE504_RADICES),"winding_included_in_finite_count":False},
        "aperture_stages":[list(p) for p in HARMONIC_APERTURE_STAGES],
        "cyclic_configuration_count":_COG64_CONFIG_CYCLE_STATES,
        "ordinal_encoding":{"formula":"(((aperture_stage*504+head)*8+control_lane)*8+translation_lane)",
            "decode":{"translation_lane":"ordinal%8","control_lane":"(ordinal//8)%8",
                      "head":"(ordinal//64)%504","aperture_stage":"ordinal//(64*504)"},
            "ordinal_min":0,"ordinal_max_exclusive":_COG64_CONFIG_CYCLE_STATES},
        "projection_is_factorized_not_materialized":True,"all_rows_can_be_opened_in_bounded_pages":True,
        "residuals":["control_translation_axes_are_factorized_roles_not_physical_cube_calibration",
                     "winding_lifts_are_unbounded_and_not_counted_in_cyclic_configurations",
                     "recursive_depth_is_not_inferred_by_state_space_cardinality",
                     "global_fractal_center_depth_unknown"],
        "claim_boundary":"complete finite index for the stated cyclic factor product only; not the whole BC address space"}
    body["space_address"]=_sha256_text(_canonical_json(body))[:24]
    return body


def open_64core_harmonic_state_space(address: BCFloorAddress, space: Mapping[str, Any],
                                     start_index: int = 0, count: int = 32,
                                     max_output_bytes: int = 1_048_576) -> dict[str, Any]:
    if not isinstance(space,Mapping) or space.get("schema")!="BC-COG64-HARMONIC-STATE-SPACE-1":
        raise TypeError("cog64_state_space_required")
    selector=space.get("frame_selector")
    rebuilt_space=build_64core_harmonic_state_space(address,selector)
    if rebuilt_space!=dict(space): raise ValueError("cog64_state_space_binding_or_content_mismatch")
    if type(start_index) is not int or not 0<=start_index<_COG64_CONFIG_CYCLE_STATES:
        raise ValueError("cog64_space_start_index_out_of_range")
    if type(count) is not int or not 1<=count<=64:
        raise ValueError("cog64_space_page_count_must_be_1_to_64")
    if type(max_output_bytes) is not int or not 1024<=max_output_bytes<=4*1024*1024:
        raise ValueError("cog64_space_output_budget_must_be_1024_to_4194304_bytes")
    frame=_hf_frame_select(address,selector)
    stop=min(_COG64_CONFIG_CYCLE_STATES,start_index+count)
    states=[]
    for ordinal in range(start_index,stop):
        translation_lane=ordinal%8
        control_lane=(ordinal//8)%8
        head=(ordinal//64)%HARMONIC_HEADS
        stage=ordinal//(64*HARMONIC_HEADS)
        prefix=HARMONIC_APERTURE_STAGES[stage]
        state=_cog64_folded_state(address.address_id,frame,control_lane,translation_lane,head,prefix)
        state["state_ordinal"]=ordinal
        state["aperture_stage_index"]=stage
        body={"schema":"BC-COG64-HARMONIC-SPACE-OPEN-1","source_address_id":address.address_id,
            "space_address":space["space_address"],"frame_address":frame.frame_address,
            "start_index":start_index,"requested_count":count,"next_index":ordinal+1,
            "complete":ordinal+1>=_COG64_CONFIG_CYCLE_STATES,"states":states+[state],
            "state_count":len(states)+1,"max_output_bytes":max_output_bytes,
            "winding_lifts_materialized":False,"frontier_depth_opened":frame.depth,
            "residuals":list(space["residuals"]),"payloads_truncated":False}
        if len(_canonical_json(body).encode("utf-8"))>max_output_bytes:
            if not states:
                raise ValueError(f"single_cog64_state_exceeds_output_budget:{len(_canonical_json(body).encode('utf-8'))}")
            break
        states.append(state)
    body={"schema":"BC-COG64-HARMONIC-SPACE-OPEN-1","source_address_id":address.address_id,
        "space_address":space["space_address"],"frame_address":frame.frame_address,
        "start_index":start_index,"requested_count":count,"next_index":start_index+len(states),
        "complete":start_index+len(states)>=_COG64_CONFIG_CYCLE_STATES,"states":states,
        "state_count":len(states),"max_output_bytes":max_output_bytes,
        "winding_lifts_materialized":False,"frontier_depth_opened":frame.depth,
        "residuals":list(space["residuals"]),"payloads_truncated":False}
    body["page_address"]=_sha256_text(_canonical_json(body))[:24]
    if len(_canonical_json(body).encode("utf-8"))>max_output_bytes:
        raise ValueError("cog64_page_envelope_exceeds_output_budget")
    return body


def reopen_64core_harmonic_state_space(address: BCFloorAddress, space: Mapping[str, Any],
                                       page: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(page,Mapping) or page.get("schema")!="BC-COG64-HARMONIC-SPACE-OPEN-1":
        return {"schema":"BC-COG64-HARMONIC-SPACE-REOPEN-1","pass":False,"reason":"cog64_state_space_page_required"}
    try:
        rebuilt=open_64core_harmonic_state_space(address,space,page["start_index"],page["requested_count"],page["max_output_bytes"])
        same=rebuilt==dict(page)
        hash_body={k:v for k,v in page.items() if k!="page_address"}
        hash_ok=_sha256_text(_canonical_json(hash_body))[:24]==page.get("page_address")
        return {"schema":"BC-COG64-HARMONIC-SPACE-REOPEN-1","pass":same and hash_ok,
            "page_address":page.get("page_address"),"rebuilt_page_address":rebuilt.get("page_address"),
            "state_count":len(rebuilt.get("states",[])),"ordinals_contiguous":all(
                state["state_ordinal"]==page["start_index"]+ix for ix,state in enumerate(rebuilt.get("states",[]))),
            "onehot_core_states_valid":all(sum(state["core_one_hot"])==1 and len(state["core_one_hot"])==64 for state in rebuilt.get("states",[])),
            "frontier_depth_opened_only":True,"global_fractal_center_depth_known":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-COG64-HARMONIC-SPACE-REOPEN-1","pass":False,
            "reason":f"cog64_space_reopen_failed:{type(exc).__name__}:{exc}"}


def project_64core_harmonic_state_space(address: BCFloorAddress, space: Mapping[str, Any],
                                         page_size: int = 64, max_receipt_bytes: int = 1_048_576) -> dict[str, Any]:
    """Project every cyclic COG64×sphere504×aperture configuration in bounded pages.

    Full state rows exist only within one working page. The output retains every page's
    content address, ordered coverage, rolling receipt, factor counts and collision counts.
    Any individual folded state is regenerated by opening the descriptor at its ordinal.
    """
    if not isinstance(address, BCFloorAddress):
        raise TypeError("cog64_projection_requires_full_floor_address")
    if not isinstance(space, Mapping) or space.get("schema") != "BC-COG64-HARMONIC-STATE-SPACE-1":
        raise TypeError("cog64_state_space_required")
    if build_64core_harmonic_state_space(address, space.get("frame_selector")) != dict(space):
        raise ValueError("cog64_projection_state_space_binding_mismatch")
    if type(page_size) is not int or not 1 <= page_size <= 64:
        raise ValueError("cog64_projection_page_size_must_be_1_to_64")
    if type(max_receipt_bytes) is not int or not 1024 <= max_receipt_bytes <= 4 * 1024 * 1024:
        raise ValueError("cog64_projection_receipt_budget_must_be_1024_to_4194304_bytes")
    frame = _hf_frame_select(address, space["frame_selector"])
    total = _COG64_CONFIG_CYCLE_STATES
    stage_counts = [0] * len(HARMONIC_APERTURE_STAGES)
    control_counts = [0] * 8
    translation_counts = [0] * 8
    head_counts = [0] * HARMONIC_HEADS
    core_slot_counts = [0] * 64
    folded_addresses: set[str] = set()
    page_receipts: list[dict[str, Any]] = []
    stage_samples: dict[str, dict[str, str]] = {}
    rolling = "0" * 64
    total_rows = 0
    for start_index in range(0, total, page_size):
        stop = min(total, start_index + page_size)
        state_refs: list[dict[str, Any]] = []
        page_stage_counts = [0] * len(HARMONIC_APERTURE_STAGES)
        for ordinal in range(start_index, stop):
            translation_lane = ordinal % 8
            control_lane = (ordinal // 8) % 8
            head = (ordinal // 64) % HARMONIC_HEADS
            stage = ordinal // (64 * HARMONIC_HEADS)
            prefix = HARMONIC_APERTURE_STAGES[stage]
            state = _cog64_folded_state(address.address_id, frame, control_lane, translation_lane, head, prefix)
            state["state_ordinal"] = ordinal
            state["aperture_stage_index"] = stage
            state_refs.append({"state_ordinal":ordinal,"folded_state_address":state["folded_state_address"]})
            stage_counts[stage] += 1
            page_stage_counts[stage] += 1
            control_counts[control_lane] += 1
            translation_counts[translation_lane] += 1
            head_counts[head] += 1
            core_slot_counts[state["core_slot"]] += 1
            folded_addresses.add(state["folded_state_address"])
            sample = stage_samples.setdefault(str(stage), {"first": state["folded_state_address"]})
            sample["last"] = state["folded_state_address"]
        # Hash the ordered ordinal/address pairs. Full expanded state rows are intentionally
        # not serialized into every saved projection; each folded address is itself content-derived
        # from the complete state body, and every row can be reopened by ordinal on demand.
        page_body = {"schema":"BC-COG64-HARMONIC-PROJECTION-PAGE-1", "source_address_id":address.address_id,
            "space_address":space["space_address"], "frame_address":frame.frame_address,
            "start_index":start_index,"stop_index_exclusive":stop,"state_refs":state_refs,
            "stage_counts":page_stage_counts,"payloads_truncated":False,
            "full_state_rows_retained":False}
        page_size_bytes = len(_canonical_json(page_body).encode("utf-8"))
        if page_size_bytes > max_receipt_bytes:
            raise ValueError(f"cog64_projection_receipt_exceeds_budget:{start_index}:{page_size_bytes}")
        page_address = _sha256_text(_canonical_json(page_body))[:24]
        next_rolling = _sha256_text(_canonical_json({"previous":rolling,"page_address":page_address,
            "start_index":start_index,"stop_index":stop,"count":len(state_refs)}))
        nonzero_stages = [i for i, count in enumerate(page_stage_counts) if count]
        page_receipts.append({"page_index":len(page_receipts),"start_index":start_index,"stop_index_exclusive":stop,
            "state_count":len(state_refs),"page_address":page_address,"receipt_bytes":page_size_bytes,
            "rolling_receipt":next_rolling,"first_folded_state_address":state_refs[0]["folded_state_address"],
            "last_folded_state_address":state_refs[-1]["folded_state_address"],
            "stage_indices_present":nonzero_stages,"stage_counts":page_stage_counts,
            "payload_truncated":False,"full_state_rows_retained_in_projection":False})
        rolling = next_rolling
        total_rows += len(state_refs)
    # Check closed-form symmetry counts against the observed complete traversal.
    expected_stage = 64 * HARMONIC_HEADS
    expected_control = 8 * HARMONIC_HEADS * len(HARMONIC_APERTURE_STAGES)
    expected_head = 64 * len(HARMONIC_APERTURE_STAGES)
    expected_core_slot = HARMONIC_HEADS * len(HARMONIC_APERTURE_STAGES)
    if stage_counts != [expected_stage] * len(HARMONIC_APERTURE_STAGES):
        raise ValueError("cog64_projection_stage_count_mismatch")
    if control_counts != [expected_control] * 8 or translation_counts != [expected_control] * 8:
        raise ValueError("cog64_projection_lane_count_mismatch")
    if head_counts != [expected_head] * HARMONIC_HEADS or core_slot_counts != [expected_core_slot] * 64:
        raise ValueError("cog64_projection_head_or_core_count_mismatch")
    if total_rows != total or len(folded_addresses) != total:
        raise ValueError("cog64_projection_coverage_or_folded_address_collision")
    body = {"schema":"BC-COG64-HARMONIC-SPACE-PROJECTION-1", "source_address_id":address.address_id,
        "source_frame":frame.as_dict(), "space_address":space["space_address"],
        "factor_shape":{"control_lanes":8,"translation_lanes":8,"sphere504_heads":HARMONIC_HEADS,
            "aperture_prefixes":len(HARMONIC_APERTURE_STAGES)},
        "cyclic_configuration_count":total, "projected_state_count":total,
        "page_size":page_size,"page_count":len(page_receipts),"max_receipt_bytes":max_receipt_bytes,
        "coverage":{"start_index":0,"stop_index_exclusive":total,"contiguous":True,"gaps":0,"duplicates":0},
        "folded_state_address_unique_count":len(folded_addresses),"folded_state_address_collisions":0,
        "stage_counts":stage_counts,"stage_prefixes":[list(p) for p in HARMONIC_APERTURE_STAGES],
        "control_lane_counts":control_counts,"translation_lane_counts":translation_counts,
        "sphere_head_counts":{"each_head_count":expected_head,"head_count":len(head_counts)},
        "core_slot_counts":{"each_slot_count":expected_core_slot,"slot_count":len(core_slot_counts)},
        "stage_address_samples":stage_samples,"page_receipts":page_receipts,"rolling_receipt":rolling,
        "transition_families":{"control_lane_forward_cycle_edges":total,"translation_lane_forward_cycle_edges":total,
            "sphere504_head_forward_cycle_edges":total,
            "aperture_stage_adjacent_expansion_edges":(len(HARMONIC_APERTURE_STAGES)-1)*64*HARMONIC_HEADS,
            "aperture_stage_adjacent_folding_edges":(len(HARMONIC_APERTURE_STAGES)-1)*64*HARMONIC_HEADS,
            "edges_are_factorized_formulas_not_materialized":True},
        "evidence_policy":{"full_state_rows_saved":False,"every_state_regenerable_from_ordinal":True,
            "all_page_content_addresses_retained":True,"each_page_hashes_ordered_state_addresses":True,
            "no_per_state_glyphs_created":True},
        "residuals":["control and translation axes are factorized roles, not physical cube calibration",
            "winding lifts are independent of finite cyclic index", "global fractal centre depth remains unknown",
            "the projection covers the specified cyclic factors only, not the complete BC address space"],
        "glyph_admission":False,"source_write":False,"project_save":False,"cold_commit":False}
    body["projection_address"] = _sha256_text(_canonical_json(body))
    return body


def reopen_64core_harmonic_state_space_projection(address: BCFloorAddress, space: Mapping[str, Any],
                                                     projection: Mapping[str, Any], full_rescan: bool = False) -> dict[str, Any]:
    """Fast reopen checks the indexed page chain plus first/middle/last pages.

    Set full_rescan=True when a complete 129024-state recomputation is required.
    """
    if not isinstance(projection, Mapping) or projection.get("schema") != "BC-COG64-HARMONIC-SPACE-PROJECTION-1":
        return {"schema":"BC-COG64-HARMONIC-SPACE-PROJECTION-REOPEN-1","pass":False,"reason":"cog64_projection_required"}
    if type(full_rescan) is not bool:
        return {"schema":"BC-COG64-HARMONIC-SPACE-PROJECTION-REOPEN-1","pass":False,"reason":"full_rescan_must_be_boolean"}
    try:
        hash_body={k:v for k,v in projection.items() if k!="projection_address"}
        if _sha256_text(_canonical_json(hash_body))!=projection.get("projection_address"):
            return {"schema":"BC-COG64-HARMONIC-SPACE-PROJECTION-REOPEN-1","pass":False,
                "reason":"cog64_projection_content_address_mismatch"}
        rebuilt_space=build_64core_harmonic_state_space(address,space.get("frame_selector"))
        if rebuilt_space!=dict(space) or projection.get("source_address_id")!=address.address_id or projection.get("space_address")!=space.get("space_address"):
            raise ValueError("cog64_projection_source_or_space_binding_mismatch")
        total=_COG64_CONFIG_CYCLE_STATES
        page_size=projection["page_size"]
        if type(page_size) is not int or not 1<=page_size<=64: raise ValueError("cog64_projection_page_size_invalid")
        expected_pages=(total+page_size-1)//page_size
        receipts=projection.get("page_receipts")
        if not isinstance(receipts,list) or len(receipts)!=expected_pages or projection.get("page_count")!=expected_pages:
            raise ValueError("cog64_projection_page_count_mismatch")
        rolling="0"*64
        previous_stop=0
        for ix,receipt in enumerate(receipts):
            start_index=ix*page_size; stop=min(total,start_index+page_size); count=stop-start_index
            if receipt.get("page_index")!=ix or receipt.get("start_index")!=start_index or receipt.get("stop_index_exclusive")!=stop or receipt.get("state_count")!=count:
                raise ValueError(f"cog64_projection_page_coverage_mismatch:{ix}")
            expected_stage_counts=[]
            for stage_index in range(len(HARMONIC_APERTURE_STAGES)):
                stage_lo=stage_index*64*HARMONIC_HEADS; stage_hi=(stage_index+1)*64*HARMONIC_HEADS
                expected_stage_counts.append(max(0,min(stop,stage_hi)-max(start_index,stage_lo)))
            if receipt.get("stage_counts")!=expected_stage_counts or receipt.get("page_address") is None:
                raise ValueError(f"cog64_projection_page_stage_mismatch:{ix}")
            next_rolling=_sha256_text(_canonical_json({"previous":rolling,"page_address":receipt["page_address"],
                "start_index":start_index,"stop_index":stop,"count":count}))
            if receipt.get("rolling_receipt")!=next_rolling:
                raise ValueError(f"cog64_projection_receipt_chain_mismatch:{ix}")
            rolling=next_rolling; previous_stop=stop
        if previous_stop!=total or projection.get("coverage")!={"start_index":0,"stop_index_exclusive":total,"contiguous":True,"gaps":0,"duplicates":0}:
            raise ValueError("cog64_projection_coverage_incomplete")
        if projection.get("cyclic_configuration_count")!=total or projection.get("projected_state_count")!=total or projection.get("folded_state_address_unique_count")!=total or projection.get("folded_state_address_collisions")!=0:
            raise ValueError("cog64_projection_summary_count_mismatch")
        if projection.get("rolling_receipt")!=rolling:
            raise ValueError("cog64_projection_final_receipt_mismatch")
        if full_rescan:
            rebuilt=project_64core_harmonic_state_space(address,space,page_size,projection["max_receipt_bytes"])
            same=rebuilt==dict(projection)
            return {"schema":"BC-COG64-HARMONIC-SPACE-PROJECTION-REOPEN-1","pass":same,
                "verification_mode":"full_rescan","projection_address":projection.get("projection_address"),
                "rebuilt_projection_address":rebuilt.get("projection_address"),"projected_state_count":total,
                "page_count":expected_pages,"all_page_receipts_rebuilt":True,"coverage_contiguous":True,
                "folded_state_address_collisions":0,"global_fractal_center_depth_known":False,"per_state_glyphs_created":0}
        # Open sample pages independently and recompute their compact page-address from every state id.
        sample_indices=sorted(set((0,expected_pages//2,expected_pages-1)))
        for ix in sample_indices:
            receipt=receipts[ix]; start_index=receipt["start_index"]
            page=open_64core_harmonic_state_space(address,space,start_index,page_size,4*1024*1024)
            refs=[{"state_ordinal":state["state_ordinal"],"folded_state_address":state["folded_state_address"]} for state in page["states"]]
            stage_counts=[sum(1 for state in page["states"] if state["aperture_stage_index"]==stage) for stage in range(len(HARMONIC_APERTURE_STAGES))]
            page_body={"schema":"BC-COG64-HARMONIC-PROJECTION-PAGE-1","source_address_id":address.address_id,
                "space_address":space["space_address"],"frame_address":page["frame_address"],
                "start_index":start_index,"stop_index_exclusive":page["next_index"],"state_refs":refs,
                "stage_counts":stage_counts,"payloads_truncated":False,"full_state_rows_retained":False}
            if _sha256_text(_canonical_json(page_body))[:24]!=receipt["page_address"]:
                raise ValueError(f"cog64_projection_sample_page_mismatch:{ix}")
        return {"schema":"BC-COG64-HARMONIC-SPACE-PROJECTION-REOPEN-1","pass":True,
            "verification_mode":"content_addressed_page_chain_plus_first_middle_last_page_recompute",
            "projection_address":projection.get("projection_address"),"projected_state_count":total,
            "page_count":expected_pages,"all_page_receipts_rebuilt":True,"sample_pages_recomputed":sample_indices,
            "coverage_contiguous":True,"folded_state_address_collisions":0,
            "global_fractal_center_depth_known":False,"per_state_glyphs_created":0,
            "full_rescan_performed":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-COG64-HARMONIC-SPACE-PROJECTION-REOPEN-1","pass":False,
            "reason":f"cog64_projection_reopen_failed:{type(exc).__name__}:{exc}"}


def build_64core_harmonic_cog_chain(address: BCFloorAddress, steps: Sequence[Mapping[str, Any]],
                                    control_start: int = 0, translation_start: int = 0,
                                    frame_selector: str = "deepest_resolved") -> dict[str, Any]:
    """Compose the core64 (8×8) control/translation factors with the sphere-504 phase.

    Prime aperture prefixes select which existing 3/5/7 cog projections are exposed; they do
    not silently multiply physical movement. Each event explicitly supplies exact deltas.
    The returned folded states are address-bound and preserve independent lane/phase winding.
    """
    if not isinstance(address,BCFloorAddress) or address.prime_harmonic is None:
        raise ValueError("cog64_chain_requires_address_bound_prime_harmonic")
    if not isinstance(steps,(tuple,list)) or not 1<=len(steps)<=_COG64_MAX_STEPS:
        raise ValueError("cog64_chain_requires_1_to_64_steps")
    for name,value in (("control_start",control_start),("translation_start",translation_start)):
        _strict_int(value,name)
        if abs(value)>MAX_PRIME_RPM_MOMENTUM:
            raise ValueError(name+"_out_of_range")
    frame=_hf_frame_select(address,frame_selector)
    normalized=[]
    for ix,row in enumerate(steps):
        if not isinstance(row,Mapping): raise TypeError(f"cog64_step_{ix}_must_be_mapping")
        allowed={"control_delta","translation_delta","harmonic_ticks","aperture_prefix","label"}
        if set(row)-allowed: raise ValueError(f"cog64_step_{ix}_unknown_fields")
        vals={}
        for name in ("control_delta","translation_delta","harmonic_ticks"):
            val=row.get(name,0); _strict_int(val,f"cog64_step_{ix}_{name}")
            if abs(val)>MAX_PRIME_RPM_MOMENTUM: raise ValueError(f"cog64_step_{ix}_{name}_out_of_range")
            vals[name]=val
        prefix=tuple(row.get("aperture_prefix",address.prime_harmonic.aperture_prefix))
        if prefix not in HARMONIC_APERTURE_STAGES: raise ValueError(f"cog64_step_{ix}_aperture_prefix_invalid")
        label=row.get("label",f"s{ix}")
        if not isinstance(label,str) or len(label)>32: raise ValueError(f"cog64_step_{ix}_label_invalid")
        normalized.append({**vals,"aperture_prefix":list(prefix),"label":label})
    control_abs=control_start; translation_abs=translation_start
    harmonic_abs=address.prime_harmonic.winding*HARMONIC_HEADS+address.prime_harmonic.head
    prefix=address.prime_harmonic.aperture_prefix
    initial=_cog64_folded_state(address.address_id,frame,control_abs,translation_abs,harmonic_abs,prefix)
    trace=[]; residuals=[]
    for ix,row in enumerate(normalized):
        before=_cog64_folded_state(address.address_id,frame,control_abs,translation_abs,harmonic_abs,prefix)
        old_harmonic=harmonic_abs
        old_control=control_abs; old_translation=translation_abs
        control_abs+=row["control_delta"]; translation_abs+=row["translation_delta"]
        harmonic_abs+=row["harmonic_ticks"]
        prefix=tuple(row["aperture_prefix"])
        new_head=harmonic_abs%HARMONIC_HEADS
        radix=sphere504_mixed_radix_step(old_harmonic%HARMONIC_HEADS,row["harmonic_ticks"])
        direct_winding_delta=harmonic_abs//HARMONIC_HEADS-old_harmonic//HARMONIC_HEADS
        rates=tuple(prefix)
        lanes=[prime_cog_lane_step(old_harmonic,row["harmonic_ticks"],rate).as_dict() for rate in rates]
        carry_pass=(radix.head_after==new_head and radix.factor_cycle_match and radix.direct_sphere_cycle_carry==direct_winding_delta)
        if not carry_pass: raise ValueError(f"cog64_step_{ix}_sphere504_carry_mismatch")
        after=_cog64_folded_state(address.address_id,frame,control_abs,translation_abs,harmonic_abs,prefix)
        req={k:row[k] for k in ("control_delta","translation_delta","harmonic_ticks","aperture_prefix","label")}
        transition_body={"schema":"BC-COG64-TRANSITION-1","index":ix,"label":row["label"],
            "before_address":before["folded_state_address"],"after_address":after["folded_state_address"],
            "request":req,"control_carry":divmod(control_abs,8)[0]-divmod(old_control,8)[0],
            "translation_carry":divmod(translation_abs,8)[0]-divmod(old_translation,8)[0],
            "sphere504_radix_step":radix.as_dict(),"sphere_winding_delta":direct_winding_delta,
            "active_lane_views":lanes,"all_carries_recomputed":carry_pass}
        transition_body["transition_address"]=_sha256_text(_canonical_json(transition_body))[:24]
        trace.append({"before":before,"after":after,"transition":transition_body})
    final=trace[-1]["after"]
    body={"schema":"BC-COG64-HARMONIC-CHAIN-1","source_address_id":address.address_id,
        "source_frame":frame.as_dict(),"frame_selector":frame_selector,"request":{"control_start":control_start,
            "translation_start":translation_start,"frame_selector":frame_selector,"steps":normalized},
        "initial_state":initial,"final_state":final,"trace":trace,"step_count":len(trace),
        "cyclic_configuration_count":_COG64_CONFIG_CYCLE_STATES,
        "aperture_stage_count":len(HARMONIC_APERTURE_STAGES),
        "aperture_lane_combinations":[{"prefix":list(p),"active_lane_count":len(p)} for p in HARMONIC_APERTURE_STAGES],
        "cog_compression":{"cyclic_joint_configurations":_COG64_CONFIG_CYCLE_STATES,
            "parameterized_chain_executors":1,"existing_prime_lane_kernels_reused":3,
            "registered_glyphs_added_for_this_mechanic":2,
            "per_state_glyphs_created":0,
            "interpretation":"one parameterized chain plus the existing 3/5/7 lane kernels denotes the cyclic states; winding lifts remain explicit and unbounded"},
        "residuals":sorted(set(residuals+[
            "control_translation_axes_are_factorized_roles_not_physical_cube_calibration",
            "no relation_map_route_mutated; folded states reference actual source frame and address",
            "global_fractal_center_depth_unknown"])),
        "source_write":False,"glyph_admission":False,"project_save":False,"cold_commit":False,
        "claim_boundary":"exact integer address-space control/translation factors paired with existing sphere504 prime-cog projections; not physical RPM or hardware semantics"}
    body["chain_address"]=_sha256_text(_canonical_json(body))[:24]
    return body


def reopen_64core_harmonic_cog_chain(address: BCFloorAddress, chain: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(chain,Mapping) or chain.get("schema")!="BC-COG64-HARMONIC-CHAIN-1":
        return {"schema":"BC-COG64-HARMONIC-CHAIN-REOPEN-1","pass":False,"reason":"cog64_chain_required"}
    if chain.get("source_address_id")!=address.address_id:
        return {"schema":"BC-COG64-HARMONIC-CHAIN-REOPEN-1","pass":False,"reason":"cog64_source_address_mismatch"}
    try:
        req=chain["request"]
        rebuilt=build_64core_harmonic_cog_chain(address,req["steps"],req["control_start"],req["translation_start"],req["frame_selector"])
        hash_body={k:v for k,v in chain.items() if k!="chain_address"}
        hash_ok=_sha256_text(_canonical_json(hash_body))[:24]==chain.get("chain_address")
        same=rebuilt==dict(chain)
        return {"schema":"BC-COG64-HARMONIC-CHAIN-REOPEN-1","pass":same and hash_ok,
            "chain_address":chain.get("chain_address"),"rebuilt_chain_address":rebuilt.get("chain_address"),
            "source_matches":True,"all_transition_carries_recomputed":all(x["transition"]["all_carries_recomputed"] for x in rebuilt["trace"]),
            "all_folded_state_addresses_rebuilt":all(x["before"]["folded_state_address"] and x["after"]["folded_state_address"] for x in rebuilt["trace"]),
            "cyclic_configuration_count":rebuilt["cyclic_configuration_count"],"per_state_glyphs_created":0,
            "global_fractal_center_depth_known":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-COG64-HARMONIC-CHAIN-REOPEN-1","pass":False,
            "reason":f"cog64_reopen_failed:{type(exc).__name__}:{exc}"}


_COMPOUND_CLASS_KIND["AddressRelationMap"]="address_relation_map"
REGISTRY.register("build_address_relation_map",build_address_relation_map,"pure")
REGISTRY.register("reopen_address_relation_map",reopen_address_relation_map,"pure")
REGISTRY.register("open_address_relation_route",open_address_relation_route,"pure")
for _relation_spec in (
    GlyphSpec.make("BC.RELATION.MAP","build_address_relation_map",("address","cone"),
        ("related_sources","ledger","workloads","top_k","collision_stage"),
        {"address":"full_address","cone":"depth_wave_cone","related_sources":"typed_address_cone_sequence",
         "ledger":"glyph_learning_ledger","workloads":"potential_workload_sequence","top_k":"bounded_positive_integer",
         "collision_stage":"fractal_collision_cone_stage_or_verified_index"},"pure",
        "build a compact control map joining opened addresses, one-hot cross-scale relations, learning evidence and bounded predictor routes; names denote structure and do not create glyph implementations"),
    GlyphSpec.make("BC.RELATION.MAP.REOPEN","reopen_address_relation_map",("address","cone","relation_map"),
        ("related_sources","ledger","collision_stage"),
        {"address":"full_address","cone":"depth_wave_cone","relation_map":"address_relation_map",
         "related_sources":"typed_address_cone_sequence","ledger":"glyph_learning_ledger",
         "collision_stage":"fractal_collision_cone_stage_or_verified_index"},"pure",
        "rebuild relation edges from the exact opened structures and ledger; reject modified map contents or source bindings"),
    GlyphSpec.make("BC.RELATION.OPEN","open_address_relation_route",("address","cone","relation_map","route_id"),
        ("related_sources","ledger"),
        {"address":"full_address","cone":"depth_wave_cone","relation_map":"address_relation_map",
         "route_id":"string","related_sources":"typed_address_cone_sequence","ledger":"glyph_learning_ledger"},"pure",
        "open one indexed route into its actual source evidence; frontier routes return unopened residuals and never masquerade as opened deeper states"),
):
    GLYPH_CATALOG.register(_relation_spec)



# Bounded relation opening and parameterized 64-core / harmonic cog-chain controls.
REGISTRY.register("open_address_relation_routes",open_address_relation_routes,"pure")
REGISTRY.register("reopen_address_relation_routes",reopen_address_relation_routes,"pure")
REGISTRY.register("build_64core_harmonic_cog_chain",build_64core_harmonic_cog_chain,"pure")
REGISTRY.register("reopen_64core_harmonic_cog_chain",reopen_64core_harmonic_cog_chain,"pure")
REGISTRY.register("build_64core_harmonic_state_space",build_64core_harmonic_state_space,"pure")
REGISTRY.register("open_64core_harmonic_state_space",open_64core_harmonic_state_space,"pure")
REGISTRY.register("reopen_64core_harmonic_state_space",reopen_64core_harmonic_state_space,"pure")
for _dense_spec in (
    GlyphSpec.make("BC.RELATION.OPEN.BATCH","open_address_relation_routes",
        ("address","cone","relation_map","route_ids"),("related_sources","ledger","start_index","max_items","max_output_bytes"),
        {"address":"full_address","cone":"depth_wave_cone","relation_map":"address_relation_map",
         "route_ids":"relation_route_id_sequence","related_sources":"typed_address_cone_sequence","ledger":"glyph_learning_ledger",
         "start_index":"nonnegative_integer","max_items":"positive_integer","max_output_bytes":"positive_integer"},"pure",
        "open a bounded batch from one verified relation map; reuse hydrated waves, preserve full payloads and return an exact continuation index when output budget is reached"),
    GlyphSpec.make("BC.RELATION.OPEN.BATCH.REOPEN","reopen_address_relation_routes",
        ("address","cone","relation_map","route_ids","batch"),("related_sources","ledger"),
        {"address":"full_address","cone":"depth_wave_cone","relation_map":"address_relation_map",
         "route_ids":"relation_route_id_sequence","batch":"relation_route_batch",
         "related_sources":"typed_address_cone_sequence","ledger":"glyph_learning_ledger"},"pure",
        "rebuild a bounded route batch and verify its complete payloads, order, map binding and continuation point"),
    GlyphSpec.make("BC.COG64.CHAIN","build_64core_harmonic_cog_chain",
        ("address","steps"),("control_start","translation_start","frame_selector"),
        {"address":"full_address","steps":"control_harmonic_step_sequence","control_start":"integer",
         "translation_start":"integer","frame_selector":"string"},"pure",
        "compose two 8-state control/translation factors with the address-bound sphere504 phase and selected 3/5/7 prime-cog projections; folded states retain independent winding and source-frame binding"),
    GlyphSpec.make("BC.COG64.CHAIN.REOPEN","reopen_64core_harmonic_cog_chain",
        ("address","chain"),(),{"address":"full_address","chain":"control_harmonic_chain"},"pure",
        "recompute every core64 folded state, sphere504 mixed-radix carry, aperture-lane projection and chain address from the actual source address"),
    GlyphSpec.make("BC.COG64.SPACE","build_64core_harmonic_state_space",("address",),("frame_selector",),
        {"address":"full_address","frame_selector":"string"},"pure",
        "index the exact finite cyclic product 8 control × 8 translation × 504 sphere heads × four aperture prefixes without materializing the full state set"),
    GlyphSpec.make("BC.COG64.SPACE.OPEN","open_64core_harmonic_state_space",("address","space"),("start_index","count","max_output_bytes"),
        {"address":"full_address","space":"control_harmonic_state_space","start_index":"nonnegative_integer",
         "count":"positive_integer","max_output_bytes":"positive_integer"},"pure",
        "open a bounded page of complete folded states from the factorized cyclic index; preserve one-hot state, aperture stage and source frame"),
    GlyphSpec.make("BC.COG64.SPACE.OPEN.REOPEN","reopen_64core_harmonic_state_space",("address","space","page"),(),
        {"address":"full_address","space":"control_harmonic_state_space","page":"control_harmonic_state_space_page"},"pure",
        "rebuild and verify every indexed state and page address without inferring winding or global fractal depth"),
):
    GLYPH_CATALOG.register(_dense_spec)


REGISTRY.register("project_64core_harmonic_state_space",project_64core_harmonic_state_space,"pure")
REGISTRY.register("reopen_64core_harmonic_state_space_projection",reopen_64core_harmonic_state_space_projection,"pure")
GLYPH_CATALOG.register(GlyphSpec.make("BC.COG64.SPACE.PROJECT","project_64core_harmonic_state_space",
    ("address","space"),("page_size","max_receipt_bytes"),
    {"address":"full_address","space":"control_harmonic_state_space","page_size":"positive_integer",
     "max_receipt_bytes":"positive_integer"},"pure",
    "project every addressable COG64×sphere504×four-aperture cyclic configuration in bounded pages; retain exact factor counts, unique folded-address evidence and a digest receipt per page without creating per-state glyphs"))
GLYPH_CATALOG.register(GlyphSpec.make("BC.COG64.SPACE.PROJECT.REOPEN","reopen_64core_harmonic_state_space_projection",
    ("address","space","projection"),("full_rescan",),
    {"address":"full_address","space":"control_harmonic_state_space","projection":"mapping","full_rescan":"boolean"},"pure",
    "verify the compact page receipt chain and sample pages; optional full_rescan performs the exhaustive recomputation of every state"))


# Explicit recursive-depth/aperture/family work locks and non-opening front audits.
# A lock is a bounded work contract derived from the actual addressed structure,
# not a claim that unopened depth exists or that equal projections are identical.
_FRACTAL_TRANSITION_FAMILIES = (
    "control8", "translation8", "sphere504", "prime3", "prime5", "prime7",
    "aperture_expand", "aperture_fold", "depth_step", "frontier_travel", "collision_probe",
)


def _fractal_l1_ball_upper(radius: int) -> int:
    # Upper bound for integer points in an unbounded 3-D Manhattan ball,
    # clipped to the 216-state 6x6x6 address family.
    return min(216, 1 + sum(4 * d * d + 2 for d in range(1, radius + 1)))


def _fractal_contiguous_resolved_depths(address: BCFloorAddress, requested_depth: int) -> tuple[list[dict[str, Any]], list[str]]:
    """Inventory the actual contiguous resolved prefix, not merely the requested prefix."""
    rows: list[dict[str, Any]] = []
    blocker: str | None = None
    for depth, level in enumerate(address.levels, start=1):
        if not level.active:
            blocker = f"depth_{depth}_blocked_inactive_level"
            break
        if level.lattice216 is None:
            blocker = f"depth_{depth}_blocked_unresolved_lattice_payload"
            break
        child = resolve_recursive_child_address(address, depth - 1)
        rows.append({"depth": depth, "child_address_id": child.address_id,
                     "level_index": depth - 1, "box_pos": level.box_pos,
                     "side": level.side, "lattice_payload_resolved": True})
    residuals: list[str] = []
    if requested_depth > len(address.levels):
        residuals.append(f"requested_depth_{requested_depth}_exceeds_present_depth_{len(address.levels)}")
        residuals.extend(f"recursive_depth_{d}_not_present" for d in range(len(address.levels)+1, requested_depth+1))
    if requested_depth > len(rows) and blocker:
        residuals.append(f"requested_depth_{requested_depth}_blocked_by_{blocker}")
    return rows, residuals

def _fractal_lock_cost(seed_count: int, recursive_depths: Sequence[int], radius: int,
                       aperture_stage_cap: int, available_families: Sequence[str]) -> dict[str, Any]:
    per_seed = _fractal_l1_ball_upper(radius)
    node_upper = seed_count * per_seed
    frontier_upper = 0 if radius >= MAX_DEPTH_WAVE_RADIUS else seed_count * min(1296, per_seed * 6)
    per_node_edges = {"control8": 2, "translation8": 2, "sphere504": 2,
                      "prime3": 2, "prime5": 2, "prime7": 2}
    edges: dict[str, int] = {}
    for family in available_families:
        if family in per_node_edges:
            edges[family] = node_upper * per_node_edges[family]
        elif family in {"aperture_expand", "aperture_fold"}:
            edges[family] = seed_count * aperture_stage_cap * 64 * HARMONIC_HEADS
        elif family == "depth_step":
            edges[family] = max(0, seed_count - 1) * 216
        elif family == "frontier_travel":
            edges[family] = frontier_upper
        elif family == "collision_probe":
            # Address-indexed collision scan; no all-pairs materialisation.
            edges[family] = node_upper
    return {"seed_count": seed_count, "max_nodes_per_seed_upper": per_seed,
            "aggregate_nodes_upper": node_upper, "aggregate_frontier_edges_upper": frontier_upper,
            "transition_edges_upper_by_family": dict(sorted(edges.items())),
            "transition_edges_upper": sum(edges.values()),
            "family_depth_cells": len(available_families) * seed_count}


def build_fractal_aperture_lock(address: BCFloorAddress, requested_depth: int = 1, wave_radius: int = 1,
                                aperture_families: Sequence[str] = ("box", "cube"),
                                transition_families: Sequence[str] = _FRACTAL_TRANSITION_FAMILIES,
                                aperture_stage_cap: int = 3, include_root_lattice: bool = False,
                                max_nodes: int = MAX_DEPTH_WAVE_CONE_NODES,
                                max_frontier_edges: int = MAX_DEPTH_WAVE_CONE_FRONTIER_EDGES,
                                max_transition_edges: int = 1_000_000,
                                max_transition_families: int = MAX_FRACTAL_LOCK_FAMILIES) -> dict[str, Any]:
    """Preflight and lock depth, aperture identities, family width and aggregate work.

    The deepest permitted recursion is the contiguous active/resolved prefix of the
    actual address, further limited by aggregate node/frontier/transition budgets.
    This plans work; it does not open deeper states or execute transitions.
    """
    if not isinstance(address, BCFloorAddress): raise TypeError("full_floor_address_required")
    if type(requested_depth) is not int or not 0 <= requested_depth <= MAX_FRACTAL_LOCK_DEPTH:
        raise ValueError("fractal_lock_requested_depth_out_of_range")
    if type(wave_radius) is not int or not 0 <= wave_radius <= MAX_DEPTH_WAVE_RADIUS:
        raise ValueError("fractal_lock_wave_radius_out_of_range")
    if type(aperture_stage_cap) is not int or not 0 <= aperture_stage_cap < len(HARMONIC_APERTURE_STAGES):
        raise ValueError("fractal_lock_aperture_stage_cap_out_of_range")
    if type(include_root_lattice) is not bool: raise TypeError("fractal_lock_include_root_must_be_boolean")
    for name, value, low, high in (("max_nodes",max_nodes,1,MAX_DEPTH_WAVE_CONE_NODES),
                                   ("max_frontier_edges",max_frontier_edges,0,MAX_DEPTH_WAVE_CONE_FRONTIER_EDGES),
                                   ("max_transition_edges",max_transition_edges,1,2_000_000),
                                   ("max_transition_families",max_transition_families,1,MAX_FRACTAL_LOCK_FAMILIES)):
        if type(value) is not int or not low <= value <= high: raise ValueError(f"fractal_lock_{name}_out_of_range")
    apertures = tuple(aperture_families)
    if not apertures or len(set(apertures)) != len(apertures) or any(x not in {"box","cube"} for x in apertures):
        raise ValueError("fractal_lock_aperture_families_invalid")
    families = tuple(transition_families)
    if len(set(families)) != len(families) or any(x not in _FRACTAL_TRANSITION_FAMILIES for x in families):
        raise ValueError("fractal_lock_transition_families_invalid")
    if not families or len(families) > max_transition_families:
        raise ValueError("fractal_lock_transition_family_count_exceeds_lock")
    present_rows, depth_residuals = _fractal_contiguous_resolved_depths(address, requested_depth)
    max_present_depth = len(present_rows)
    root_available = address.lattice216 is not None
    if include_root_lattice and not root_available:
        depth_residuals.append("root_lattice216_unresolved")
    if "sphere504" in families and address.prime_harmonic is None:
        # It can be named but is not authorized as executable work for this root.
        depth_residuals.append("sphere504_transition_requested_without_prime_harmonic_address")
    available: list[str] = []
    unavailable: list[str] = []
    for family in families:
        if family in {"sphere504","prime3","prime5","prime7"} and address.prime_harmonic is None:
            unavailable.append(family)
        elif family in {"prime3","prime5","prime7"} and aperture_stage_cap < {"prime3":1,"prime5":2,"prime7":3}[family]:
            unavailable.append(family)
        elif family == "aperture_expand" and aperture_stage_cap == 0:
            unavailable.append(family)
        elif family == "aperture_fold" and aperture_stage_cap == 0:
            unavailable.append(family)
        elif family == "depth_step" and max_present_depth < 2:
            unavailable.append(family)
        elif family == "frontier_travel" and wave_radius >= MAX_DEPTH_WAVE_RADIUS:
            unavailable.append(family)
        else:
            available.append(family)
    if not available:
        raise ValueError("fractal_lock_has_no_available_transition_families")
    depth_cap = 0
    selected_depths: list[int] = []
    selected_cost: dict[str, Any] | None = None
    selected_families: list[str] = []
    max_candidate_depth = min(requested_depth, max_present_depth)
    candidates = range(0, max_candidate_depth + 1)
    for depth_cap_candidate in candidates:
        depths = list(range(1, depth_cap_candidate + 1))
        seed_count = (1 if include_root_lattice and root_available else 0) + len(depths)
        candidate_families = [f for f in available if f != "depth_step" or seed_count >= 2]
        cost = _fractal_lock_cost(seed_count, depths, wave_radius, aperture_stage_cap, candidate_families)
        fits = (cost["aggregate_nodes_upper"] <= max_nodes and
                cost["aggregate_frontier_edges_upper"] <= max_frontier_edges and
                cost["transition_edges_upper"] <= max_transition_edges)
        if fits:
            depth_cap, selected_depths, selected_cost = depth_cap_candidate, depths, cost
            selected_families = list(candidate_families)
        else:
            break
    if selected_cost is None: raise ValueError("fractal_lock_budget_cannot_open_any_seed")
    # The final family set is the set meaningful at the selected depth, not merely
    # the set that could be meaningful at some deeper address.
    available = selected_families
    unavailable = [f for f in families if f not in available]
    residuals = list(depth_residuals)
    if depth_cap < min(requested_depth, max_present_depth):
        residuals.append(f"aggregate_work_budget_locks_depth_at_{depth_cap}")
    if requested_depth > depth_cap and not any(x.startswith("recursive_depth_") or x.startswith("requested_depth_") for x in residuals):
        residuals.append(f"requested_depth_{requested_depth}_not_authorized_by_work_budget")
    if unavailable: residuals.extend(f"transition_family_{x}_not_open_under_selected_aperture_or_source" for x in unavailable)
    lock_body = {"schema":"BC-FRACTAL-APERTURE-WORK-LOCK-1", "root_address_id":address.address_id,
        "request":{"requested_depth":requested_depth,"wave_radius":wave_radius,"aperture_families":sorted(apertures),
            "transition_families":list(families),"aperture_stage_cap":aperture_stage_cap,
            "include_root_lattice":include_root_lattice,"max_nodes":max_nodes,
            "max_frontier_edges":max_frontier_edges,"max_transition_edges":max_transition_edges,
            "max_transition_families":max_transition_families},
        "address_depth_inventory":{"levels_tuple_length":len(address.levels),"contiguous_resolved_depths":selected_depths,
            "max_present_contiguous_depth":max_present_depth,"requested_depth_is_present":requested_depth<=max_present_depth,
            "present_level_bindings":present_rows[:depth_cap],"root_lattice_available":root_available,
            "actual_contiguous_resolved_depth_count":max_present_depth},
        "apertures":{"selected":sorted(apertures),"box_address":BOX_APERTURE_216.address_id if "box" in apertures else None,
            "cube_address":CUBE_APERTURE_216.address_id if "cube" in apertures else None,
            "identities_distinct":True,"equal_cardinality_does_not_merge":True,
            "aperture_stage_cap":aperture_stage_cap,"stage_prefixes":[list(x) for x in HARMONIC_APERTURE_STAGES[:aperture_stage_cap+1]]},
        "transition_families":{"requested":list(families),"available":sorted(available),"unavailable":sorted(unavailable),
            "requested_family_count":len(families),"family_count":len(available),
            "family_depth_matrix":[{"depth":d,"families":sorted(available)} for d in ([0] if include_root_lattice and root_available else [])+selected_depths]},
        "work_bound":selected_cost,"limits":{"aggregate_nodes":max_nodes,"aggregate_frontier_edges":max_frontier_edges,
            "aggregate_transition_edges":max_transition_edges,"max_transition_families":max_transition_families,
            "local_lattice_nodes_max":216,"local_lattice_frontier_edges_max":1296},
        "effective_depth_cap":depth_cap,"effective_wave_radius":wave_radius,
        "authorized":bool(selected_cost["seed_count"] and available and
            selected_cost["aggregate_nodes_upper"]<=max_nodes and
            selected_cost["aggregate_frontier_edges_upper"]<=max_frontier_edges and
            selected_cost["transition_edges_upper"]<=max_transition_edges),
        "residuals":sorted(set(residuals)),"deeper_states_opened":False,
        "global_fractal_center_depth_known":False,"source_write":False,"project_save":False,
        "glyph_admission":False,"cold_commit":False}
    lock_body["lock_address"] = _sha256_text(_canonical_json(lock_body))[:32]
    return lock_body


def reopen_fractal_aperture_lock(address: BCFloorAddress, lock: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(lock, Mapping) or lock.get("schema") != "BC-FRACTAL-APERTURE-WORK-LOCK-1":
            raise TypeError("fractal_aperture_work_lock_required")
        if lock.get("root_address_id") != address.address_id: raise ValueError("fractal_lock_root_binding_mismatch")
        body={k:v for k,v in lock.items() if k!="lock_address"}
        if _sha256_text(_canonical_json(body))[:32] != lock.get("lock_address"):
            raise ValueError("fractal_lock_content_address_mismatch")
        req=lock["request"]
        rebuilt=build_fractal_aperture_lock(address, req["requested_depth"], req["wave_radius"],
            req["aperture_families"],req["transition_families"],req["aperture_stage_cap"],
            req["include_root_lattice"],req["max_nodes"],req["max_frontier_edges"],
            req["max_transition_edges"],req["max_transition_families"])
        if rebuilt != dict(lock): raise ValueError("fractal_lock_rebuild_mismatch")
        return {"schema":"BC-FRACTAL-APERTURE-WORK-LOCK-REOPEN-1","pass":True,
            "lock_address":lock["lock_address"],"root_binding_reopened":True,
            "effective_depth_cap":lock["effective_depth_cap"],"family_count":lock["transition_families"]["family_count"],
            "aggregate_node_upper":lock["work_bound"]["aggregate_nodes_upper"],
            "aggregate_frontier_edge_upper":lock["work_bound"]["aggregate_frontier_edges_upper"],
            "aggregate_transition_edge_upper":lock["work_bound"]["transition_edges_upper"],
            "deeper_states_opened":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-FRACTAL-APERTURE-WORK-LOCK-REOPEN-1","pass":False,
            "reason":f"{type(exc).__name__}:{exc}"}


def open_fractal_locked_cone(address: BCFloorAddress, lock: Mapping[str, Any]) -> dict[str, Any]:
    checked=reopen_fractal_aperture_lock(address,lock)
    if not checked.get("pass") or not lock.get("authorized"):
        return {"schema":"BC-FRACTAL-LOCKED-CONE-1","pass":False,"reason":"valid_authorizing_lock_required",
            "lock_reopen":checked,"deeper_states_opened":False}
    cone=open_depth_wave_cone(address, lock["effective_depth_cap"], lock["effective_wave_radius"],
                              target_child=None, include_root_lattice=lock["request"]["include_root_lattice"])
    bounds=lock["work_bound"]
    if len(cone.nodes)>lock["limits"]["aggregate_nodes"] or len(cone.frontier)>lock["limits"]["aggregate_frontier_edges"]:
        raise ValueError("fractal_locked_cone_actual_work_exceeded_lock")
    if len(cone.nodes)>bounds["aggregate_nodes_upper"] or len(cone.frontier)>bounds["aggregate_frontier_edges_upper"]:
        raise ValueError("fractal_locked_cone_exceeded_conservative_estimate")
    opened_depths=sorted({n.depth for n in cone.nodes})
    if any(depth>lock["effective_depth_cap"] for depth in opened_depths):
        raise ValueError("fractal_locked_cone_opened_beyond_depth_cap")
    body={"schema":"BC-FRACTAL-LOCKED-CONE-1","root_address_id":address.address_id,
        "lock_address":lock["lock_address"],"cone":cone.as_dict(),"opened_depths":opened_depths,
        "actual_node_count":len(cone.nodes),"actual_frontier_edge_count":len(cone.frontier),
        "actual_work_within_lock":True,"frontier_edges_are_unopened":True,
        "frontier_count_by_depth":{str(d):sum(1 for f in cone.frontier if f.depth==d) for d in sorted({f.depth for f in cone.frontier})},
        "residuals":list(lock["residuals"])+list(cone.unresolved),
        "deeper_states_opened":False,"global_fractal_center_depth_known":False}
    body["opening_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def reopen_fractal_locked_cone(address: BCFloorAddress, lock: Mapping[str, Any], opening: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(opening,Mapping) or opening.get("schema")!="BC-FRACTAL-LOCKED-CONE-1":
            raise TypeError("fractal_locked_cone_packet_required")
        body={k:v for k,v in opening.items() if k!="opening_address"}
        if _sha256_text(_canonical_json(body))[:32] != opening.get("opening_address"):
            raise ValueError("fractal_locked_cone_content_address_mismatch")
        if opening.get("root_address_id")!=address.address_id or opening.get("lock_address")!=lock.get("lock_address"):
            raise ValueError("fractal_locked_cone_source_binding_mismatch")
        rebuilt=open_fractal_locked_cone(address,lock)
        if not rebuilt.get("pass",True) or rebuilt != dict(opening):
            raise ValueError("fractal_locked_cone_rebuild_mismatch")
        # `rebuilt` was generated from the authoritative root and reopened lock;
        # exact whole-packet equality above already compares every serialized cone
        # node, frontier and child binding. A second cone rebuild here repeated the
        # same expansion without adding a distinct validation algorithm.
        cone_payload=opening["cone"]
        return {"schema":"BC-FRACTAL-LOCKED-CONE-REOPEN-1","pass":True,
            "opening_address":opening["opening_address"],"lock_address":lock["lock_address"],
            "cone_address":cone_payload["cone_address"],"node_count":opening["actual_node_count"],
            "frontier_count":opening["actual_frontier_edge_count"],"frontier_edges_are_unopened":True,
            "deeper_states_opened":False,"full_opening_rebuilt_from_root_and_lock":True}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-FRACTAL-LOCKED-CONE-REOPEN-1","pass":False,
            "reason":f"{type(exc).__name__}:{exc}"}


def audit_fractal_cone_fronts(address: BCFloorAddress, cone: DepthWaveCone,
                              related_sources: Sequence[Mapping[str, Any]] = (),
                              max_overlap_pairs: int = 4096, max_samples: int = 32) -> dict[str, Any]:
    """Inspect traveling front edges and projected cone/sphere collisions without opening them.

    Coordinate coincidences across different roots/frames are candidates only. The audit
    preserves source identities and winding; it never merges cones or advances a frontier.
    """
    if not isinstance(address,BCFloorAddress) or not isinstance(cone,DepthWaveCone):
        raise TypeError("front_audit_requires_address_and_opened_cone")
    if type(max_overlap_pairs) is not int or not 1<=max_overlap_pairs<=65536:
        raise ValueError("front_audit_overlap_budget_out_of_range")
    if type(max_samples) is not int or not 1<=max_samples<=128:
        raise ValueError("front_audit_sample_budget_out_of_range")
    if len(related_sources)>7: raise ValueError("front_audit_related_source_limit_exceeded")
    pairs=[{"address":address,"cone":cone,"label":"primary"}]
    for ix,row in enumerate(related_sources):
        if not isinstance(row,Mapping) or not isinstance(row.get("address"),BCFloorAddress) or not isinstance(row.get("cone"),DepthWaveCone):
            raise TypeError(f"front_audit_related_source_{ix}_must_bind_address_and_cone")
        pairs.append({"address":row["address"],"cone":row["cone"],"label":str(row.get("label",f"related:{ix}"))})
    validated=[]
    for item in pairs:
        c=item["cone"]; a=item["address"]
        if c.root_address_id!=a.address_id: raise ValueError("front_audit_cone_root_binding_mismatch")
        witness=reopen_depth_wave_cone(a,c)
        if not witness.pass_all: raise ValueError("front_audit_cone_reopen_failed")
        if len(c.nodes)>MAX_DEPTH_WAVE_CONE_NODES or len(c.frontier)>MAX_DEPTH_WAVE_CONE_FRONTIER_EDGES:
            raise ValueError("front_audit_cone_exceeds_aggregate_bounds")
        validated.append((item,a,c))
    total_nodes=sum(len(c.nodes) for _,_,c in validated)
    if total_nodes>MAX_DEPTH_WAVE_CONE_NODES:
        raise ValueError("front_audit_total_node_budget_exceeded")
    from collections import Counter,defaultdict
    per_cone=[]; cross_samples=[]; cross_count=0
    sphere_rows=[]
    for item,a,c in validated:
        depth_counts=Counter(n.depth for n in c.nodes)
        front_depth=Counter(f.depth for f in c.frontier)
        front_axis=Counter(f"{f.axis}:{'+' if f.direction>0 else '-'}" for f in c.frontier)
        inbound=defaultdict(set)
        for f in c.frontier:
            inbound[(f.child_address_id,f.depth,f.target_physical_index6)].add(f.from_state_address_id)
        convergence=[{"child_address_id":k[0],"depth":k[1],"target_physical_index6":k[2],
                       "distinct_inbound_sources":len(v)} for k,v in inbound.items() if len(v)>1]
        ids=[n.state_address_id for n in c.nodes]
        node_identity_duplicates=len(ids)-len(set(ids))
        per_cone.append({"label":item["label"],"root_address_id":a.address_id,"cone_address":c.cone_address,
            "opened_node_count":len(c.nodes),"opened_nodes_by_depth":dict(sorted(depth_counts.items())),
            "front_edge_count":len(c.frontier),"front_edges_by_depth":dict(sorted(front_depth.items())),
            "front_edges_by_axis_direction":dict(sorted(front_axis.items())),
            "front_target_convergence_count":len(convergence),"front_target_convergence_samples":convergence[:max_samples],
            "duplicate_state_identity_count":node_identity_duplicates,
            "front_edge_samples":[{**f.as_dict(),"opened":False,"traversal_permitted":False} for f in c.frontier[:max_samples]],
            "local_state_spaces_closed":c.local_state_spaces_closed,"dependency_closed":c.dependency_closed})
        if a.prime_harmonic is not None:
            phase=a.prime_harmonic.winding*HARMONIC_HEADS+a.prime_harmonic.head
            sphere_rows.append({"label":item["label"],"root_address_id":a.address_id,
                "head":a.prime_harmonic.head,"winding":a.prime_harmonic.winding,
                "absolute_phase":phase,"address_id":a.prime_harmonic.address_id})
    # Compare coordinate/distance fibres only as collision candidates; source addresses
    # remain distinct and the pair scan is bounded by indexed key intersections.
    for i in range(len(validated)):
        item_a,addr_a,cone_a=validated[i]
        keys_a=defaultdict(list)
        for n in cone_a.nodes:
            key=(n.depth,n.wave_distance,tuple(n.lattice.physical_coord6))
            keys_a[key].append(n)
        for j in range(i+1,len(validated)):
            item_b,addr_b,cone_b=validated[j]
            keys_b=defaultdict(list)
            for n in cone_b.nodes:
                key=(n.depth,n.wave_distance,tuple(n.lattice.physical_coord6))
                keys_b[key].append(n)
            common=sorted(set(keys_a).intersection(keys_b))
            cross_count+=len(common)
            if cross_count>max_overlap_pairs:
                raise ValueError("front_audit_cross_cone_overlap_budget_exceeded")
            for key in common[:max(0,max_samples-len(cross_samples))]:
                cross_samples.append({"left_label":item_a["label"],"right_label":item_b["label"],
                    "depth":key[0],"wave_distance":key[1],"physical_coord6":list(key[2]),
                    "left_node_ids":[x.state_address_id for x in keys_a[key]],
                    "right_node_ids":[x.state_address_id for x in keys_b[key]],
                    "same_address_identity":addr_a.address_id==addr_b.address_id,
                    "interpretation":"projected cone overlap candidate; distinct roots/child identities are not merged"})
    head_groups=defaultdict(list)
    for row in sphere_rows: head_groups[row["head"]].append(row)
    winding_alias_groups=[]; same_lift_across_roots=[]
    for head,rows in sorted(head_groups.items()):
        if len({r["winding"] for r in rows})>1:
            winding_alias_groups.append({"head":head,"members":rows,
                "interpretation":"same cyclic head, different winding lifts; expected modulo alias, not same full phase"})
        elif len({r["root_address_id"] for r in rows})>1:
            same_lift_across_roots.append({"head":head,"winding":rows[0]["winding"],"members":rows,
                "interpretation":"same lifted harmonic phase appears in different structural roots; root addresses stay distinct"})
    body={"schema":"BC-FRACTAL-CONE-FRONT-AUDIT-1","primary_root_address_id":address.address_id,
        "audit_request":{"max_overlap_pairs":max_overlap_pairs,"max_samples":max_samples},
        "sources":[{"label":item["label"],"root_address_id":a.address_id,"cone_address":c.cone_address} for item,a,c in validated],
        "source_count":len(validated),"total_opened_nodes":total_nodes,
        "aggregate_node_budget":MAX_DEPTH_WAVE_CONE_NODES,"aggregate_frontier_edge_budget_per_cone":MAX_DEPTH_WAVE_CONE_FRONTIER_EDGES,
        "cones":per_cone,"cross_cone_projected_overlap_candidate_count":cross_count,
        "cross_cone_projected_overlap_samples":cross_samples,
        "sphere_phase_rows":sphere_rows,"same_head_different_winding_alias_groups":winding_alias_groups,
        "same_lift_across_distinct_roots":same_lift_across_roots,
        "frontier_edges_opened_as_states":False,"frontier_traversal_performed":False,
        "unopened_frontiers_remain_residuals":True,"global_fractal_center_depth_known":False,
        "residuals":["coordinate overlap is not address identity","sphere head equality discards winding unless full phase is retained",
            "front edges are indexed candidates and were not traversed","unknown deeper frame is not inferred"],
        "source_write":False,"project_save":False,"glyph_admission":False,"cold_commit":False}
    body["audit_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def reopen_fractal_cone_front_audit(address: BCFloorAddress, cone: DepthWaveCone,
                                    audit: Mapping[str, Any],
                                    related_sources: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    try:
        if not isinstance(audit,Mapping) or audit.get("schema")!="BC-FRACTAL-CONE-FRONT-AUDIT-1":
            raise TypeError("fractal_cone_front_audit_required")
        body={k:v for k,v in audit.items() if k!="audit_address"}
        if _sha256_text(_canonical_json(body))[:32]!=audit.get("audit_address"):
            raise ValueError("fractal_front_audit_content_address_mismatch")
        request=audit["audit_request"]
        rebuilt=audit_fractal_cone_fronts(address,cone,related_sources,
            max_overlap_pairs=request["max_overlap_pairs"],max_samples=request["max_samples"])
        if rebuilt != dict(audit): raise ValueError("fractal_front_audit_rebuild_mismatch")
        return {"schema":"BC-FRACTAL-CONE-FRONT-AUDIT-REOPEN-1","pass":True,
            "audit_address":audit["audit_address"],"source_count":audit["source_count"],
            "frontier_edges_opened_as_states":False,"collision_candidates_rebuilt":True}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-FRACTAL-CONE-FRONT-AUDIT-REOPEN-1","pass":False,
            "reason":f"{type(exc).__name__}:{exc}"}


REGISTRY.register("build_fractal_aperture_lock", build_fractal_aperture_lock, "pure")
REGISTRY.register("reopen_fractal_aperture_lock", reopen_fractal_aperture_lock, "pure")
REGISTRY.register("open_fractal_locked_cone", open_fractal_locked_cone, "pure")
REGISTRY.register("reopen_fractal_locked_cone", reopen_fractal_locked_cone, "pure")
REGISTRY.register("audit_fractal_cone_fronts", audit_fractal_cone_fronts, "pure")
REGISTRY.register("reopen_fractal_cone_front_audit", reopen_fractal_cone_front_audit, "pure")
for _lock_spec in (
    GlyphSpec.make("BC.FRACTAL.LOCK", "build_fractal_aperture_lock",
        ("address", "requested_depth", "wave_radius"),
        ("aperture_families", "transition_families", "aperture_stage_cap", "include_root_lattice", "max_nodes", "max_frontier_edges", "max_transition_edges", "max_transition_families"),
        {"address":"full_address","requested_depth":"nonnegative_integer","wave_radius":"nonnegative_integer",
         "aperture_families":"box_cube_aperture_family_sequence","transition_families":"bounded_transition_family_sequence",
         "aperture_stage_cap":"prime_harmonic_aperture_stage_index","include_root_lattice":"boolean",
         "max_nodes":"positive_integer","max_frontier_edges":"nonnegative_integer",
         "max_transition_edges":"positive_integer","max_transition_families":"positive_integer"},"pure",
        "lock requested depth to contiguous resolved levels plus distinct aperture and transition-family budgets before work is opened; no unknown center depth is inferred"),
    GlyphSpec.make("BC.FRACTAL.LOCK.REOPEN", "reopen_fractal_aperture_lock", ("address", "lock"), (),
        {"address":"full_address","lock":"fractal_aperture_work_lock"},"pure",
        "rebuild the depth/aperture/family work envelope from the exact source address and reject changed caps or root bindings"),
    GlyphSpec.make("BC.FRACTAL.LOCK.OPEN", "open_fractal_locked_cone", ("address", "lock"), (),
        {"address":"full_address","lock":"fractal_aperture_work_lock"},"pure",
        "open a depth-wave cone only under a reopened work lock and enforce aggregate node/frontier limits"),
    GlyphSpec.make("BC.FRACTAL.LOCK.OPEN.REOPEN", "reopen_fractal_locked_cone", ("address", "lock", "opening"), (),
        {"address":"full_address","lock":"fractal_aperture_work_lock","opening":"fractal_locked_cone_packet"},"pure",
        "rebuild the locked cone and full depth-wave witness; unopened front edges remain residuals"),
    GlyphSpec.make("BC.FRACTAL.FRONT.AUDIT", "audit_fractal_cone_fronts", ("address", "cone"), ("related_sources","max_overlap_pairs","max_samples"),
        {"address":"full_address","cone":"depth_wave_cone","related_sources":"bounded_related_address_cone_sequence",
         "max_overlap_pairs":"positive_integer","max_samples":"positive_integer"},"pure",
        "audit traveling front edges, convergent targets, projected cone intersections and sphere head/winding aliases without traversing an unopened frontier"),
    GlyphSpec.make("BC.FRACTAL.FRONT.AUDIT.REOPEN", "reopen_fractal_cone_front_audit", ("address", "cone", "audit"), ("related_sources",),
        {"address":"full_address","cone":"depth_wave_cone","audit":"fractal_cone_front_audit",
         "related_sources":"bounded_related_address_cone_sequence"},"pure",
        "recompute the root-bound front/collision audit and reject tampered identities or residuals"),
):
    GLYPH_CATALOG.register(_lock_spec)



# Lock-bound route batching and sphere504 collision-cone staging.
# One reusable cog/profile carries many named views; no glyph is minted per view.

def _locked_context_open(address: BCFloorAddress, cone: DepthWaveCone,
                         lock: Mapping[str, Any], opening: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError(f"{label}:typed_address_and_cone_required")
    lock_check = reopen_fractal_aperture_lock(address, lock)
    if not lock_check.get("pass") or not lock.get("authorized"):
        raise ValueError(f"{label}:authorizing_work_lock_failed")
    opening_check = reopen_fractal_locked_cone(address, lock, opening)
    if not opening_check.get("pass"):
        raise ValueError(f"{label}:locked_opening_failed")
    if cone.root_address_id != address.address_id or cone.cone_address != opening_check.get("cone_address"):
        raise ValueError(f"{label}:cone_is_not_the_locked_opening")
    return {"label":label, "address":address, "cone":cone, "lock":dict(lock), "opening":dict(opening),
            "lock_check":lock_check, "opening_check":opening_check}


def _relation_required_families(route: Mapping[str, Any]) -> tuple[str, ...]:
    kind=route.get("kind")
    if kind in {"collision_stage","collision_fidelity_scan","sphere_winding_alias","collision_candidate"}:
        return ("collision_probe","sphere504","prime3","prime5","prime7")
    if kind == "sphere504_cycle": return ("sphere504",)
    if kind == "cog64_state_space": return ("control8","translation8","sphere504")
    if kind == "harmonic_aperture_stage":
        prefix=route.get("prime_prefix",[])
        result=["aperture_expand"] if prefix else []
        result.extend(f"prime{p}" for p in prefix)
        return tuple(result)
    if kind == "frontier": return ()
    if kind in {"child","frame"}: return ("depth_step",)
    if kind in {"wave","wave_glyph","projection"}: return ("control8",)
    return ()


def open_locked_relation_route_batch(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], relation_map: AddressRelationMap,
        route_ids: Sequence[str], related_contexts: Sequence[Mapping[str, Any]] = (),
        ledger: GlyphLearningLedger | None = None, start_index: int = 0, max_items: int = 16,
        max_output_bytes: int = 1_048_576) -> dict[str, Any]:
    """Open a route batch only under root-bound locks/openings for every structural source."""
    primary=_locked_context_open(address,cone,lock,opening,"primary")
    contexts=[primary]
    if not isinstance(related_contexts,(tuple,list)) or len(related_contexts)>7:
        raise ValueError("locked_route_related_context_limit_exceeded")
    for ix,row in enumerate(related_contexts):
        if not isinstance(row,Mapping): raise TypeError("related_context_must_be_mapping")
        contexts.append(_locked_context_open(row.get("address"),row.get("cone"),row.get("lock"),row.get("opening"),
                                             str(row.get("label",f"related:{ix}"))))
    labels=[x["label"] for x in contexts]
    if len(set(labels))!=len(labels): raise ValueError("locked_route_context_labels_must_be_unique")
    relation_sources=[{"address":x["address"],"cone":x["cone"],"label":x["label"]} for x in contexts[1:]]
    source_contexts={_sha256_text(_canonical_json({"root":x["address"].address_id,"cone":x["cone"].cone_address}))[:24]:x for x in contexts}
    map_body=json.loads(relation_map.payload_json)
    map_source_rows=map_body.get("source_contexts",[])
    map_source_keys={row.get("source_key") for row in map_source_rows}
    unlocked_source_keys=sorted(k for k in map_source_keys if k not in source_contexts)
    if unlocked_source_keys:
        return {"schema":"BC-FRACTAL-LOCKED-RELATION-BATCH-1","pass":False,
            "reason":"relation_map_contains_unlocked_source_context","unlocked_source_keys":unlocked_source_keys,
            "root_address_id":address.address_id,"lock_address":lock.get("lock_address"),
            "deeper_states_opened":False,"partial_batch_opened":False}
    map_check=reopen_address_relation_map(address,cone,relation_map,relation_sources,ledger)
    if not map_check.get("pass"):
        return {"schema":"BC-FRACTAL-LOCKED-RELATION-BATCH-1","pass":False,
            "reason":"locked_route_relation_map_reopen_failed","map_reopen":map_check,
            "deeper_states_opened":False,"partial_batch_opened":False}
    rows=map_body.get("routes",[])
    by_id={r["route_id"]:r for r in rows}
    if not isinstance(route_ids,(tuple,list)) or len(route_ids)>256:
        raise ValueError("locked_route_batch_max_256")
    if type(start_index) is not int or not 0<=start_index<=len(route_ids): raise ValueError("locked_route_start_index_invalid")
    if type(max_items) is not int or not 1<=max_items<=64: raise ValueError("locked_route_max_items_must_be_1_to_64")
    source_contexts={_sha256_text(_canonical_json({"root":x["address"].address_id,"cone":x["cone"].cone_address}))[:24]:x for x in contexts}
    selected=route_ids[start_index:min(len(route_ids),start_index+max_items)]
    preflight=[]
    for rid in selected:
        row=by_id.get(rid)
        if row is None:
            preflight.append({"route_id":rid,"pass":False,"reason":"route_id_not_indexed"}); continue
        sk=row.get("source_key","")
        context=source_contexts.get(sk)
        collision_kind=row.get("kind") in {"collision_stage","collision_fidelity_scan","sphere_winding_alias","collision_candidate"}
        if collision_kind:
            governed_keys=row.get("governing_source_keys",[])
            if not isinstance(governed_keys,list) or not governed_keys:
                preflight.append({"route_id":rid,"pass":False,"reason":"collision_route_missing_governing_source_keys"}); continue
            missing_keys=sorted(set(governed_keys)-set(source_contexts))
            if missing_keys:
                preflight.append({"route_id":rid,"pass":False,"reason":"collision_route_source_lock_missing","missing_source_keys":missing_keys}); continue
            ordered_keys=sorted(set(governed_keys))
            governing=[source_contexts[k] for k in ordered_keys]
            expected_by_key={x.get("source_key"):x for x in row.get("governing_lock_addresses",[])}
            mismatch=[]
            for gkey,gov in zip(ordered_keys,governing):
                expected=expected_by_key.get(gkey,{})
                if expected.get("lock_address") != gov["lock"].get("lock_address") or expected.get("opening_address") != gov["opening"].get("opening_address"):
                    mismatch.append({"source_key":gkey,"expected_lock_address":expected.get("lock_address"),
                        "actual_lock_address":gov["lock"].get("lock_address"),
                        "expected_opening_address":expected.get("opening_address"),
                        "actual_opening_address":gov["opening"].get("opening_address")})
            if mismatch:
                preflight.append({"route_id":rid,"pass":False,"reason":"collision_route_lock_opening_binding_mismatch","mismatches":mismatch}); continue
        else:
            if context is None and sk not in {"library","library_scale","library_harmonic","comparison","learning",""}:
                preflight.append({"route_id":rid,"pass":False,"reason":"route_source_has_no_matching_locked_context","source_key":sk}); continue
            # Root-bound route uses its own lock; shared library-wide harmonic routes must fit every participating lock.
            governing=[context] if context is not None else (contexts if sk=="library_harmonic" else [primary])
        family_fail=None
        required=_relation_required_families(row)
        for gov in governing:
            c_lock=gov["lock"]
            if (context is not None and row.get("kind") in {"child","frame","wave","wave_glyph","projection"}) or collision_kind:
                depth=row.get("depth",0)
                if type(depth) is int and depth>c_lock.get("effective_depth_cap",-1):
                    family_fail={"reason":"route_depth_exceeds_open_lock","depth":depth,
                                 "effective_depth_cap":c_lock.get("effective_depth_cap"),"locked_context":gov["label"]}; break
            available=set(c_lock.get("transition_families",{}).get("available",[]))
            missing=sorted(set(required)-available)
            if missing:
                family_fail={"reason":"route_transition_family_not_locked","missing_families":missing,
                             "locked_context":gov["label"]}; break
            if row.get("kind")=="harmonic_aperture_stage" and row.get("stage_index",0)>c_lock.get("apertures",{}).get("aperture_stage_cap",-1):
                family_fail={"reason":"aperture_stage_exceeds_lock","locked_context":gov["label"]}; break
            required_stage=row.get("required_aperture_stage_cap")
            if type(required_stage) is int and required_stage>c_lock.get("apertures",{}).get("aperture_stage_cap",-1):
                family_fail={"reason":"collision_aperture_stage_exceeds_lock","required_aperture_stage_cap":required_stage,
                    "aperture_stage_cap":c_lock.get("apertures",{}).get("aperture_stage_cap"),"locked_context":gov["label"]}; break
        if family_fail:
            preflight.append({"route_id":rid,"pass":False,**family_fail}); continue
        preflight.append({"route_id":rid,"pass":True,"required_families":list(required),
                          "governing_locks":[gov["lock"]["lock_address"] for gov in governing]})
    if any(not x["pass"] for x in preflight):
        return {"schema":"BC-FRACTAL-LOCKED-RELATION-BATCH-1","pass":False,
                "reason":"route_preflight_rejected_before_open","preflight":preflight,
                "root_address_id":address.address_id,"lock_address":lock.get("lock_address"),
                "deeper_states_opened":False,"partial_batch_opened":False}
    batch=open_address_relation_routes(address,cone,relation_map,route_ids,relation_sources,ledger,
                                      start_index,max_items,max_output_bytes)
    if not batch.get("pass"):
        return {"schema":"BC-FRACTAL-LOCKED-RELATION-BATCH-1","pass":False,"reason":"underlying_relation_batch_failed","batch":batch}
    body={k:v for k,v in batch.items() if k!="batch_address"}
    body.update({"schema":"BC-FRACTAL-LOCKED-RELATION-BATCH-1","primary_lock_address":lock["lock_address"],
        "primary_opening_address":opening["opening_address"],
        "locked_contexts":[{"label":x["label"],"root_address_id":x["address"].address_id,
             "cone_address":x["cone"].cone_address,"lock_address":x["lock"]["lock_address"],
             "opening_address":x["opening"]["opening_address"],"effective_depth_cap":x["lock"]["effective_depth_cap"],
             "effective_wave_radius":x["lock"]["effective_wave_radius"]} for x in contexts],
        "route_preflight":preflight,"preflight_before_hydration":True,
        "unopened_frontiers_traversed":False,
        "claim_boundary":"route opening is allowed only where its source has a matching reopened lock; evidence views do not grant deeper traversal"})
    body["batch_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def reopen_locked_relation_route_batch(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], relation_map: AddressRelationMap,
        route_ids: Sequence[str], batch: Mapping[str, Any],
        related_contexts: Sequence[Mapping[str, Any]] = (), ledger: GlyphLearningLedger | None = None) -> dict[str, Any]:
    try:
        if not isinstance(batch,Mapping) or batch.get("schema")!="BC-FRACTAL-LOCKED-RELATION-BATCH-1":
            raise TypeError("locked_relation_batch_required")
        body={k:v for k,v in batch.items() if k!="batch_address"}
        if _sha256_text(_canonical_json(body))[:32]!=batch.get("batch_address"):
            raise ValueError("locked_relation_batch_content_address_mismatch")
        rebuilt=open_locked_relation_route_batch(address,cone,lock,opening,relation_map,route_ids,related_contexts,ledger,
            batch["start_index"],batch["max_items"],batch["max_output_bytes"])
        if rebuilt!=dict(batch): raise ValueError("locked_relation_batch_rebuild_mismatch")
        return {"schema":"BC-FRACTAL-LOCKED-RELATION-BATCH-REOPEN-1","pass":True,
            "batch_address":batch["batch_address"],"record_count":batch["record_count"],
            "all_lock_bindings_reopened":True,"route_preflight_rebuilt":True,"frontiers_traversed":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-FRACTAL-LOCKED-RELATION-BATCH-REOPEN-1","pass":False,
                "reason":f"{type(exc).__name__}:{exc}"}


def _octant_signed_vertex(octant: int) -> tuple[int,int,int]:
    bits=octant_from_cube(octant)
    return tuple(1 if bit else -1 for bit in bits)  # type: ignore[return-value]


def _prime_lane_structuralizer_views(lane: PrimeCogLaneStep) -> list[dict[str, Any]]:
    """Six exact signed-permutation views of the lane's one-hot octant transition."""
    before=_octant_signed_vertex(lane.radix_step.octant_before)
    after=_octant_signed_vertex(lane.radix_step.octant_after)
    rows=[]
    for name,frame in PLANE_FRAMES:
        pb=_frame_point_local(frame,before); pa=_frame_point_local(frame,after)
        lb=_frame_point_global(frame,pb); la=_frame_point_global(frame,pa)
        rows.append({"plane":name,"frame":frame.as_dict(),"octant_before":lane.radix_step.octant_before,
            "octant_after":lane.radix_step.octant_after,"vertex_before":list(before),"vertex_after":list(after),
            "projected_before_xy":list(pb[:2]),"projected_after_xy":list(pa[:2]),
            "depth_before":pb[2],"depth_after":pa[2],"lift_before":list(lb),"lift_after":list(la),
            "lift_exact":lb==before and la==after,
            "view_address":_sha256_text(_canonical_json({"schema":"BC-PRIME-OCTANT-STRUCTURALIZER-VIEW-1",
                "lane":lane.lane_address,"plane":name,"before":list(pb),"after":list(pa)}))[:24]})
    return rows


def _sphere_state_short(address: BCFloorAddress) -> dict[str, Any]:
    p=address.prime_harmonic
    if p is None: raise ValueError("sphere504_address_required_for_collision_stage")
    absolute=p.winding*SPHERE504_SIZE+p.head
    return {"address_id":address.address_id,"harmonic_address_id":p.address_id,"head":p.head,
            "reference_head":p.reference_head,"winding":p.winding,"absolute_phase":absolute,
            "aperture_prefix":list(p.aperture_prefix)}


def _sphere_order_probe(address: BCFloorAddress, magnitude: int, frame_selector: str = "deepest_resolved") -> dict[str, Any]:
    """Compare +m then -m against -m then +m under the same whole-phase authority."""
    if type(magnitude) is not int or magnitude<1 or magnitude>HARMONIC_HEADS*10:
        raise ValueError("sphere_order_probe_magnitude_out_of_range")
    if address.prime_harmonic is None: raise ValueError("sphere_order_probe_requires_prime_harmonic_address")
    frame=open_harmonic_fractal_frame(address,frame_selector,"root.lattice216")
    forward=step_harmonic_fractal_center(address,frame,magnitude,True)
    backward_after_forward=step_harmonic_fractal_center(forward.after_address,forward.after_frame,-magnitude,True)
    backward=step_harmonic_fractal_center(address,frame,-magnitude,True)
    forward_after_backward=step_harmonic_fractal_center(backward.after_address,backward.after_frame,magnitude,True)
    steps=[forward,backward_after_forward,backward,forward_after_backward]
    for step in steps:
        if not step.pass_all: raise ValueError("sphere_order_probe_step_witness_failed")
    start_id=address.address_id
    fb_end=backward_after_forward.after_address.address_id
    bf_end=forward_after_backward.after_address.address_id
    forward_phase=_sphere_state_short(forward.after_address)
    backward_phase=_sphere_state_short(backward.after_address)
    step_rows=[]
    for step in steps:
        step_rows.append({"step_address":step.step_address,"source_address_id":step.source_address_id,
            "after_address_id":step.after_address.address_id,"requested_ticks":step.requested_ticks,
            "before":_sphere_state_short(step.address_witness.start),"after":_sphere_state_short(step.after_address),
            "full_address_witness":_hf_full_address_witness_dict(step.address_witness),
            "radix_step":step.radix_step.as_dict(),
            "prime_cog_bundle":None if step.cog_bundle is None else step.cog_bundle.as_dict(),
            "frame_before":step.source_frame_address,"frame_after":step.after_frame.frame_address,
            "step_pass":step.pass_all,"winding_delta":step.winding_delta})
    body={"schema":"BC-SPHERE504-FORWARD-BACKWARD-ORDER-PROBE-1","source_address_id":start_id,
        "magnitude":magnitude,"forward_then_backward":{"step_addresses":[forward.step_address,backward_after_forward.step_address],
            "intermediate":forward_phase,"end_address_id":fb_end,"return_to_entry_closed":fb_end==start_id},
        "backward_then_forward":{"step_addresses":[backward.step_address,forward_after_backward.step_address],
            "intermediate":backward_phase,"end_address_id":bf_end,"return_to_entry_closed":bf_end==start_id},
        "intermediate_paths_are_distinct":forward_phase["address_id"]!=backward_phase["address_id"],
        "same_head_different_winding_intermediates":forward_phase["head"]==backward_phase["head"] and forward_phase["winding"]!=backward_phase["winding"],
        "both_orders_replay_and_close":fb_end==start_id and bf_end==start_id,
        "aperture_stages":[{"stage_index":ix,"prefix":list(prefix),"active_rates":list(prefix),
            "phase_authority":"unwrapped sphere504 whole phase; prefix selects views only"}
            for ix,prefix in enumerate(HARMONIC_APERTURE_STAGES)],
        "steps":step_rows,"prime_lanes_are_projections_of_one_phase":True,
        "global_fractal_center_depth_known":False,
        "claim_boundary":"both inverse orders close for this additive sphere movement; their intermediate winding paths differ and remain distinct"}
    body["probe_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def _sphere504_aperture_fidelity(address: BCFloorAddress, signed_ticks: int, frame_selector: str) -> dict[str, Any]:
    """Build one source-bound harmonic movement with four lenses and six cube-plane views."""
    frame=open_harmonic_fractal_frame(address,frame_selector,"root.lattice216")
    step=step_harmonic_fractal_center(address,frame,signed_ticks,True)
    if not step.pass_all: raise ValueError("sphere504_aperture_fidelity_step_failed")
    bundle=step.cog_bundle
    if bundle is None: raise ValueError("prime_cog_bundle_required")
    lanes={x.rate:x for x in bundle.lanes}
    stage_rows=[]
    for stage_index,prefix in enumerate(HARMONIC_APERTURE_STAGES):
        active=[lanes[r] for r in prefix]
        stage_rows.append({"stage_index":stage_index,"prefix":list(prefix),"active_rates":list(prefix),
            "source_address_id":address.address_id,"step_address":step.step_address,
            "before":_sphere_state_short(address),"after":_sphere_state_short(step.after_address),
            "whole_phase_before":bundle.authority_phase_before,"whole_phase_after":bundle.authority_phase_after,
            "base_radix_step":bundle.base_step.as_dict(),
            "lane_views":[{"rate":lane.rate,"whole_phase_before":lane.whole_phase_before,
                "whole_phase_after":lane.whole_phase_after,"scaled_phase_before":lane.scaled_phase_before,
                "scaled_phase_after":lane.scaled_phase_after,"scaled_tick_delta":lane.scaled_tick_delta,
                "signed_sphere_cycles_crossed":lane.signed_sphere_cycles_crossed,
                "same_onehot_octant":lane.same_onehot_octant,"full_sphere_head_moved":lane.full_sphere_head_moved,
                "octant_before":lane.radix_step.octant_before,"octant_after":lane.radix_step.octant_after,
                "radix_step_address":lane.radix_step.step_address,"lane_address":lane.lane_address,
                "structuralizer_views":_prime_lane_structuralizer_views(lane)} for lane in active],
            "view_only_prefix":True,"physical_calibration_claimed":False})
    frame_selectors=[]
    for selector in (frame_selector,"root.lattice216"):
        hf=open_harmonic_fractal_frame(address,selector,"root.lattice216")
        frame_selectors.append({"selector":selector,"frame":hf.as_dict(),
            "reopen":reopen_harmonic_fractal_frame(address,hf)})
    body={"schema":"BC-SPHERE504-APERTURE-FIDELITY-1","source_address_id":address.address_id,
        "signed_ticks":signed_ticks,"source_state":_sphere_state_short(address),
        "after_state":_sphere_state_short(step.after_address),"step_address":step.step_address,
        "full_address_witness":_hf_full_address_witness_dict(step.address_witness),
        "radix_carries":step.radix_step.as_dict(),"prime_cog_bundle":bundle.as_dict(),
        "aperture_stages":stage_rows,"structuralizer_frame_options":frame_selectors,
        "step_reopen_pass":step.pass_all,"carrier_unchanged":step.prime_rpm_carrier_unchanged,
        "residuals":list(step.residuals)+["sphere504 phase is exact integer structure; no physical rotation calibration implied"],
        "glyph_admission":False,"source_write":False,"project_save":False,"cold_commit":False}
    body["fidelity_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def stage_fractal_collision_cones(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], related_contexts: Sequence[Mapping[str, Any]] = (),
        max_overlap_pairs: int = 4096, max_samples: int = 64, max_candidates: int = 14,
        sweep_ticks: Sequence[int] = (-504,-7,-5,-3,3,5,7,504), frame_selector: str = "deepest_resolved",
        open_adjacent_shell: bool = False) -> dict[str, Any]:
    """Stage collisions under root-bound locks; aperture the shared sphere/prime state without merging identities.

    The two additive orderings are compared once per unique source. Overlap candidates reference those shared
    fidelity scans, so repeated geometric coincidences do not duplicate the same prime/structuralizer work.
    Optional adjacent-shell opening requires a separately reconstructed lock and remains budget-gated.
    """
    if type(open_adjacent_shell) is not bool: raise TypeError("open_adjacent_shell_must_be_boolean")
    if type(max_overlap_pairs) is not int or not 1<=max_overlap_pairs<=65536: raise ValueError("collision_stage_overlap_budget_invalid")
    if type(max_samples) is not int or not 1<=max_samples<=128: raise ValueError("collision_stage_sample_budget_invalid")
    if type(max_candidates) is not int or not 1<=max_candidates<=32: raise ValueError("collision_stage_candidate_cap_must_be_1_to_32")
    if not isinstance(sweep_ticks,(tuple,list)) or not 1<=len(sweep_ticks)<=9 or any(type(x) is not int or abs(x)>HARMONIC_HEADS*10 for x in sweep_ticks):
        raise ValueError("collision_stage_sweep_ticks_must_be_1_to_9_bounded_integers")
    if len(set(sweep_ticks))!=len(sweep_ticks): raise ValueError("collision_stage_sweep_ticks_must_be_unique")
    if not frame_selector: raise ValueError("collision_stage_frame_selector_required")
    primary=_locked_context_open(address,cone,lock,opening,"primary")
    contexts=[primary]
    if not isinstance(related_contexts,(tuple,list)) or len(related_contexts)>7: raise ValueError("collision_stage_context_limit_exceeded")
    for ix,row in enumerate(related_contexts):
        if not isinstance(row,Mapping): raise TypeError("collision_stage_related_context_must_be_mapping")
        contexts.append(_locked_context_open(row.get("address"),row.get("cone"),row.get("lock"),row.get("opening"),str(row.get("label",f"related:{ix}"))))
    if len({x["label"] for x in contexts})!=len(contexts): raise ValueError("collision_stage_context_labels_must_be_unique")
    for cx in contexts:
        fam=set(cx["lock"].get("transition_families",{}).get("available",[]))
        if "collision_probe" not in fam: raise ValueError("collision_stage_requires_collision_probe_in_each_context_lock")
        if "sphere504" not in fam or cx["address"].prime_harmonic is None:
            raise ValueError("collision_stage_requires_address_bound_sphere504_in_each_context")
        if not {"prime3","prime5","prime7"}.issubset(fam) or cx["lock"].get("apertures",{}).get("aperture_stage_cap",-1)<3:
            raise ValueError("collision_stage_requires_all_prime_lenses_and_aperture_stage_3_in_each_context_lock")
        if open_adjacent_shell and "frontier_travel" not in fam:
            raise ValueError("collision_stage_adjacent_shell_requires_frontier_travel_in_original_lock")
    related=[{"address":x["address"],"cone":x["cone"],"label":x["label"]} for x in contexts[1:]]
    audit=audit_fractal_cone_fronts(address,cone,related_sources=related,max_overlap_pairs=max_overlap_pairs,max_samples=max_samples)
    audit_reopen=reopen_fractal_cone_front_audit(address,cone,audit,related_sources=related)
    if not audit_reopen.get("pass"): raise ValueError("collision_stage_front_audit_reopen_failed")
    if len(sweep_ticks)>9: raise ValueError("collision_stage_sweep_budget_exceeded")
    context_by_label={x["label"]:x for x in contexts}
    # Build fidelity once per rooted context and requested tick, then share those references across overlaps.
    fidelity_rows=[]; fidelity_by_root_tick={}; order_rows=[]; order_by_root_mag={}
    missing_prime=[]
    for cx in contexts:
        a=cx["address"]
        for tick in sweep_ticks:
            row=_sphere504_aperture_fidelity(a,tick,frame_selector)
            fidelity_rows.append(row); fidelity_by_root_tick[(a.address_id,tick)]=row["fidelity_address"]
        for mag in sorted({abs(x) for x in sweep_ticks if x!=0}):
            probe=_sphere_order_probe(a,mag,frame_selector)
            order_rows.append(probe); order_by_root_mag[(a.address_id,mag)]=probe["probe_address"]
    pair_scans=[]; pair_scan_by_labels={}
    labels=list(context_by_label)
    needed_pairs=set()
    for overlap in audit["cross_cone_projected_overlap_samples"][:max_candidates]:
        needed_pairs.add(tuple(sorted((overlap["left_label"],overlap["right_label"]))))
    # Add only root pairs with a real cross-front/opened-state coordinate candidate.
    def opened_index_for(cx):
        return {(n.depth,n.wave_distance,tuple(n.lattice.physical_coord6)):n for n in cx["cone"].nodes}
    opened_indices={cx["label"]:opened_index_for(cx) for cx in contexts}
    for i,left in enumerate(contexts):
        for right in contexts[i+1:]:
            r_index=opened_indices[right["label"]]; l_index=opened_indices[left["label"]]
            if any((edge.depth,edge.next_wave_distance,tuple(edge.target_coord6)) in r_index for edge in left["cone"].frontier) or \
               any((edge.depth,edge.next_wave_distance,tuple(edge.target_coord6)) in l_index for edge in right["cone"].frontier):
                needed_pairs.add(tuple(sorted((left["label"],right["label"]))))
            lp=left["address"].prime_harmonic; rp=right["address"].prime_harmonic
            if lp is not None and rp is not None and lp.head==rp.head and lp.winding!=rp.winding:
                needed_pairs.add(tuple(sorted((left["label"],right["label"]))))
    # Only compute a cross-root fidelity scan when some collision/alias/front event needs it.
    # Multiple spatial candidates share this one expensive harmonic × aperture × plane comparison.
    for left_label,right_label in sorted(needed_pairs):
        left=context_by_label[left_label]; right=context_by_label[right_label]
        comparisons=[]
        for tick in sweep_ticks:
            lf=next(x for x in fidelity_rows if x["source_address_id"]==left["address"].address_id and x["signed_ticks"]==tick)
            rf=next(x for x in fidelity_rows if x["source_address_id"]==right["address"].address_id and x["signed_ticks"]==tick)
            for stage_l,stage_r in zip(lf["aperture_stages"],rf["aperture_stages"]):
                left_lane={r["rate"]:r for r in stage_l["lane_views"]}; right_lane={r["rate"]:r for r in stage_r["lane_views"]}
                common_rates=sorted(set(left_lane)&set(right_lane))
                lane_comps=[]
                for rate in common_rates:
                    ll=left_lane[rate]; rr=right_lane[rate]
                    lplanes={v["plane"]:v for v in ll["structuralizer_views"]}; rplanes={v["plane"]:v for v in rr["structuralizer_views"]}
                    plane_comps=[]
                    for pname in PLANE_VIEW_ORDER:
                        lv,rv=lplanes[pname],rplanes[pname]
                        plane_comps.append({"plane":pname,"projected_octant_match":lv["projected_after_xy"]==rv["projected_after_xy"],
                            "depth_match":lv["depth_after"]==rv["depth_after"],"lift_exact_both":lv["lift_exact"] and rv["lift_exact"],
                            "left_view_address":lv["view_address"],"right_view_address":rv["view_address"]})
                    lane_comps.append({"rate":rate,"cyclic_scaled_head_match":ll["scaled_phase_after"]==rr["scaled_phase_after"],
                        "whole_phase_match":ll["whole_phase_after"]==rr["whole_phase_after"],
                        "scaled_cycle_crossing_match":ll["signed_sphere_cycles_crossed"]==rr["signed_sphere_cycles_crossed"],
                        "onehot_octant_match":ll["octant_after"]==rr["octant_after"],"planes":plane_comps})
                comparisons.append({"tick":tick,"stage_index":stage_l["stage_index"],"prefix":stage_l["prefix"],
                    "stage_same":stage_l["prefix"]==stage_r["prefix"],
                    "full_phase_match":stage_l["after"]["absolute_phase"]==stage_r["after"]["absolute_phase"],
                    "head_match":stage_l["after"]["head"]==stage_r["after"]["head"],
                    "winding_match":stage_l["after"]["winding"]==stage_r["after"]["winding"],
                    "prime_lane_comparisons":lane_comps,
                    "interpretation":"cyclic projection matches and whole-phase/carry matches are separate claims"})
        body={"schema":"BC-COLLISION-PAIR-FIDELITY-1","left_label":left_label,"right_label":right_label,
            "left_root_address_id":left["address"].address_id,"right_root_address_id":right["address"].address_id,
            "comparisons":comparisons,"same_root":left["address"].address_id==right["address"].address_id,
            "structuralizer_planes":list(PLANE_VIEW_ORDER),"residuals":["equal coordinate projection is not address identity",
                "equal sphere head does not imply equal winding","prime lane cyclic equality does not imply equal cycle-crossing count"]}
        body["pair_scan_address"]=_sha256_text(_canonical_json(body))[:32]
        pair_scans.append(body); pair_scan_by_labels[(left_label,right_label)]=body["pair_scan_address"]
    candidates=[]
    # Already-opened node overlaps: candidates only, not merged state identities.
    for row in audit["cross_cone_projected_overlap_samples"][:max_candidates]:
        left_label=row["left_label"]; right_label=row["right_label"]
        pair_key=(left_label,right_label)
        reverse=(right_label,left_label)
        scan=pair_scan_by_labels.get(pair_key,pair_scan_by_labels.get(reverse))
        if scan is None: continue
        cb={"kind":"opened_node_projection_overlap","left_label":left_label,"right_label":right_label,
            "depth":row["depth"],"wave_distance":row["wave_distance"],"physical_coord6":row["physical_coord6"],
            "left_node_ids":row["left_node_ids"],"right_node_ids":row["right_node_ids"],
            "same_address_identity":row["same_address_identity"],"pair_fidelity_scan":scan,
            "opened_nodes_remain_root_bound":True,"merging_permitted":False}
        cb["candidate_address"]=_sha256_text(_canonical_json(cb))[:24]; candidates.append(cb)
    # A frontier target hitting an opened node in another cone is staged without opening it in the source cone.
    def opened_index(cx):
        return {(n.depth,n.wave_distance,tuple(n.lattice.physical_coord6)):n for n in cx["cone"].nodes}
    for i,left in enumerate(contexts):
        for right in contexts[i+1:]:
            right_index=opened_index(right); left_index=opened_index(left)
            for edge in left["cone"].frontier:
                key=(edge.depth,edge.next_wave_distance,tuple(edge.target_coord6))
                target=right_index.get(key)
                if target is not None and len(candidates)<max_candidates:
                    scan=pair_scan_by_labels.get((left["label"],right["label"]))
                    cb={"kind":"frontier_to_opened_projection_candidate","left_label":left["label"],"right_label":right["label"],
                        "source_frontier":{"from_state_address_id":edge.from_state_address_id,"target_state_address_id":edge.target_state_address_id,
                            "target_physical_index6":edge.target_physical_index6,"target_coord6":list(edge.target_coord6),"opened":False},
                        "other_cone_opened_node_id":target.state_address_id,"depth":edge.depth,
                        "next_wave_distance":edge.next_wave_distance,"same_state_identity":edge.target_state_address_id==target.state_address_id,
                        "pair_fidelity_scan":scan,"traversal_performed":False,"merging_permitted":False}
                    cb["candidate_address"]=_sha256_text(_canonical_json(cb))[:24]; candidates.append(cb)
                if len(candidates)>=max_candidates: break
            if len(candidates)>=max_candidates: break
    # Alias groups are attached by pointer, not expanded into additional glyphs or duplicate scans.
    alias_refs=[]
    for group in audit["same_head_different_winding_alias_groups"]:
        alias_refs.append({"head":group["head"],"members":group["members"],
            "interpretation":"same cyclic head with different integer winding; compare both traversal orders before any compacted control name is reused"})
    adjacent_shells=[]; shell_residuals=[]
    if open_adjacent_shell:
        for cx in contexts:
            req=cx["lock"]["request"]
            next_radius=cx["lock"]["effective_wave_radius"]+1
            if next_radius>MAX_DEPTH_WAVE_RADIUS:
                shell_residuals.append({"label":cx["label"],"reason":"maximum_wave_radius_reached","opened":False}); continue
            try:
                next_lock=build_fractal_aperture_lock(cx["address"],req["requested_depth"],next_radius,
                    req["aperture_families"],req["transition_families"],req["aperture_stage_cap"],req["include_root_lattice"],
                    req["max_nodes"],req["max_frontier_edges"],req["max_transition_edges"],req["max_transition_families"])
                if not next_lock.get("authorized"):
                    shell_residuals.append({"label":cx["label"],"reason":"adjacent_shell_lock_not_authorized","lock_address":next_lock.get("lock_address"),"opened":False}); continue
                next_open=open_fractal_locked_cone(cx["address"],next_lock)
                if not next_open.get("actual_work_within_lock"):
                    shell_residuals.append({"label":cx["label"],"reason":"adjacent_shell_open_did_not_fit_lock","opened":False}); continue
                next_cone=_scb_depth_wave_cone_from_dict(next_open["cone"])
                next_reopen=reopen_fractal_locked_cone(cx["address"],next_lock,next_open)
                adjacent_shells.append({"label":cx["label"],"lock":next_lock,"opening":next_open,
                    "reopen":next_reopen,"cone_address":next_cone.cone_address,
                    "opened_depths":next_open["opened_depths"],"frontier_edges_traversed":False})
            except (TypeError,ValueError,KeyError,LookupError) as exc:
                shell_residuals.append({"label":cx["label"],"reason":f"{type(exc).__name__}:{exc}","opened":False})
    body={"schema":"BC-FRACTAL-COLLISION-CONE-STAGE-1","primary_root_address_id":address.address_id,
        "primary_lock_address":lock["lock_address"],"primary_opening_address":opening["opening_address"],
        "source_contexts":[{"label":cx["label"],"root_address_id":cx["address"].address_id,"cone_address":cx["cone"].cone_address,
            "lock_address":cx["lock"]["lock_address"],"opening_address":cx["opening"]["opening_address"],
            "effective_depth_cap":cx["lock"]["effective_depth_cap"],"effective_wave_radius":cx["lock"]["effective_wave_radius"]} for cx in contexts],
        "front_audit_address":audit["audit_address"],"front_audit_reopen":audit_reopen,
        "audit_request":{"max_overlap_pairs":max_overlap_pairs,"max_samples":max_samples},
        "stage_request":{"max_candidates":max_candidates,"sweep_ticks":list(sweep_ticks),"frame_selector":frame_selector,
            "open_adjacent_shell":open_adjacent_shell},
        "projected_overlap_total":audit["cross_cone_projected_overlap_candidate_count"],
        "projected_overlap_samples_available":len(audit["cross_cone_projected_overlap_samples"]),
        "projected_overlap_sampling_complete":len(audit["cross_cone_projected_overlap_samples"])>=audit["cross_cone_projected_overlap_candidate_count"],
        "projected_overlap_candidates_unexamined_residual":max(0,audit["cross_cone_projected_overlap_candidate_count"]-len(audit["cross_cone_projected_overlap_samples"])),
        "candidate_count_staged":len(candidates),"candidates":candidates,"pair_fidelity_scans":pair_scans,
        "source_fidelity_profiles":fidelity_rows,"sphere_order_probes":order_rows,"sphere_winding_alias_refs":alias_refs,
        "sweep_ticks":list(sweep_ticks),"aperture_stage_count":len(HARMONIC_APERTURE_STAGES),
        "structuralizer_plane_options":list(PLANE_VIEW_ORDER),
        "all_full_sphere_steps_replay":all(row["step_reopen_pass"] for row in fidelity_rows),
        "all_six_plane_views_lift_exact":all(v["lift_exact"] for row in fidelity_rows for stage in row["aperture_stages"] for lane in stage["lane_views"] for v in lane["structuralizer_views"]),
        "all_inverse_orders_close":all(p["both_orders_replay_and_close"] for p in order_rows),
        "alias_paths_preserved_as_distinct":all(p["intermediate_paths_are_distinct"] for p in order_rows if p["same_head_different_winding_intermediates"]),
        "opened_shells":adjacent_shells,"adjacent_shell_residuals":shell_residuals,
        "frontier_targets_opened_from_source_cones":False,"frontier_traversal_performed":False,"frontier_traversal_performed_by_audit":False,
        "unknown_depths_inferred":False,"global_fractal_center_depth_known":False,
        "claim_boundary":"projected overlap and harmonic/plane coincidence are staged evidence only; no addresses are merged; optional adjacent shells are opened only by separately budgeted root-bound locks",
        "glyph_admission":False,"source_write":False,"project_save":False,"cold_commit":False}
    body["stage_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def reopen_fractal_collision_cone_stage(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], stage: Mapping[str, Any],
        related_contexts: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    try:
        if not isinstance(stage,Mapping) or stage.get("schema")!="BC-FRACTAL-COLLISION-CONE-STAGE-1":
            raise TypeError("collision_cone_stage_required")
        body={k:v for k,v in stage.items() if k!="stage_address"}
        if _sha256_text(_canonical_json(body))[:32]!=stage.get("stage_address"):
            raise ValueError("collision_cone_stage_content_address_mismatch")
        req=stage["request"] if "request" in stage else None
        # Rebuild from recorded scalar options and the same root-bound source contexts.
        audit_contexts=[{"address":x["address"],"cone":x["cone"],"lock":x["lock"],"opening":x["opening"],"label":x.get("label",f"related:{ix}")}
                        for ix,x in enumerate(related_contexts)]
        rebuilt=stage_fractal_collision_cones(address,cone,lock,opening,audit_contexts,
            max_overlap_pairs=stage["audit_request"]["max_overlap_pairs"],
            max_samples=stage["audit_request"]["max_samples"],max_candidates=stage["stage_request"]["max_candidates"],
            sweep_ticks=stage["stage_request"]["sweep_ticks"],frame_selector=stage["stage_request"]["frame_selector"],
            open_adjacent_shell=stage["stage_request"]["open_adjacent_shell"])
        if rebuilt!=dict(stage): raise ValueError("collision_cone_stage_rebuild_mismatch")
        return {"schema":"BC-FRACTAL-COLLISION-CONE-STAGE-REOPEN-1","pass":True,
            "stage_address":stage["stage_address"],"candidate_count":len(stage["candidates"]),
            "pair_fidelity_scans_rebuilt":len(stage["pair_fidelity_scans"]),"profiles_replayed":len(stage["source_fidelity_profiles"]),
            "sphere_order_probes_rebuilt":len(stage["sphere_order_probes"]),"frontier_traversal_performed":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-FRACTAL-COLLISION-CONE-STAGE-REOPEN-1","pass":False,
            "reason":f"{type(exc).__name__}:{exc}"}


# A small number of resident control operations denotes the whole family of routes.
REGISTRY.register("open_locked_relation_route_batch",open_locked_relation_route_batch,"pure")
REGISTRY.register("reopen_locked_relation_route_batch",reopen_locked_relation_route_batch,"pure")
REGISTRY.register("stage_fractal_collision_cones",stage_fractal_collision_cones,"pure")
REGISTRY.register("reopen_fractal_collision_cone_stage",reopen_fractal_collision_cone_stage,"pure")
for _stage_spec in (
    GlyphSpec.make("BC.FRACTAL.BATCH.OPEN","open_locked_relation_route_batch",
        ("address","cone","lock","opening","relation_map","route_ids"),
        ("related_contexts","ledger","start_index","max_items","max_output_bytes"),
        {"address":"full_floor_address","cone":"depth_wave_cone","lock":"fractal_aperture_work_lock",
         "opening":"fractal_locked_cone_packet","relation_map":"address_relation_map","route_ids":"relation_route_id_sequence",
         "related_contexts":"root_bound_locked_context_sequence","ledger":"glyph_learning_ledger","start_index":"nonnegative_integer",
         "max_items":"bounded_positive_integer","max_output_bytes":"positive_integer"},"pure",
        "preflight route families and source depths against matching reopened locks before hydrating a bounded relation-route batch; unopenable routes stay residuals"),
    GlyphSpec.make("BC.FRACTAL.BATCH.OPEN.REOPEN","reopen_locked_relation_route_batch",
        ("address","cone","lock","opening","relation_map","route_ids","batch"),("related_contexts","ledger"),
        {"address":"full_floor_address","cone":"depth_wave_cone","lock":"fractal_aperture_work_lock",
         "opening":"fractal_locked_cone_packet","relation_map":"address_relation_map","route_ids":"relation_route_id_sequence",
         "batch":"locked_relation_batch","related_contexts":"root_bound_locked_context_sequence","ledger":"glyph_learning_ledger"},"pure",
        "rebuild lock, opening, map binding, preflight decisions, full route payloads and exact batch continuation"),
    GlyphSpec.make("BC.FRACTAL.COLLISION.STAGE","stage_fractal_collision_cones",
        ("address","cone","lock","opening"),("related_contexts","max_overlap_pairs","max_samples","max_candidates","sweep_ticks","frame_selector","open_adjacent_shell"),
        {"address":"full_floor_address","cone":"depth_wave_cone","lock":"fractal_aperture_work_lock","opening":"fractal_locked_cone_packet",
         "related_contexts":"root_bound_locked_context_sequence","max_overlap_pairs":"positive_integer","max_samples":"positive_integer",
         "max_candidates":"bounded_positive_integer","sweep_ticks":"bounded_signed_integer_sequence","frame_selector":"string",
         "open_adjacent_shell":"boolean"},"pure",
        "stage cone/sphere overlaps under paired locks, compare forward/backward winding paths and prime3/5/7 apertures across six structuralizer planes; optionally open one adjacent shell only under a new fitting lock; no per-state glyphs"),
    GlyphSpec.make("BC.FRACTAL.COLLISION.STAGE.REOPEN","reopen_fractal_collision_cone_stage",
        ("address","cone","lock","opening","stage"),("related_contexts",),
        {"address":"full_floor_address","cone":"depth_wave_cone","lock":"fractal_aperture_work_lock","opening":"fractal_locked_cone_packet",
         "stage":"fractal_collision_cone_stage","related_contexts":"root_bound_locked_context_sequence"},"pure",
        "rebuild collision candidates, sphere order paths, aperture profiles, structuralizer views and optional adjacent-shell locks from the same addressed sources"),
):
    GLYPH_CATALOG.register(_stage_spec)


# Cross-fractal sparse-one-hot fidelity scaling.
# This is one parameterized mechanism, not one glyph per depth/plane/aperture.
# It only scales a sphere504 step when both recursive frames are present in the
# reopened cone and the paired structural frames share typed address families.
# The exact match ratio is a combinatorial routing scale, never physical units.
# ---------------------------------------------------------------------------

def _onehot_frame_at_recursive_depth(address: BCFloorAddress, depth: int) -> AddressOneHotFrame:
    if type(depth) is not int or depth < 0:
        raise ValueError("cross_fractal_depth_must_be_nonnegative_integer")
    selector = "root.lattice216" if depth == 0 else f"levels.{depth - 1}"
    return _hf_frame_select(address, selector)


def _cone_has_opened_recursive_frame(address: BCFloorAddress, cone: DepthWaveCone,
                                     depth: int, opening: Mapping[str, Any]) -> tuple[bool, str | None]:
    if depth not in set(opening.get("opened_depths", [])):
        return False, f"depth_{depth}_not_in_locked_opening"
    if depth == 0:
        if not cone.include_root_lattice or address.lattice216 is None:
            return False, "root_lattice_not_opened"
        wanted = "ROOT.LATTICE216:" + address.address_id
    else:
        if depth > len(address.levels):
            return False, f"recursive_depth_{depth}_not_present"
        try:
            child = resolve_recursive_child_address(address, depth - 1)
        except (TypeError, ValueError, LookupError) as exc:
            return False, f"recursive_depth_{depth}_not_resolved:{type(exc).__name__}"
        wanted = child.address_id
    found = any(node.depth == depth and node.child_address_id == wanted for node in cone.nodes)
    return found, None if found else f"depth_{depth}_frame_not_seeded_in_opened_cone"


def _onehot_word_value(word: SparseOneHotWord) -> tuple[Any, ...]:
    return (word.family, word.width, word.mode, word.presence, word.active_slots)


def _onehot_scale_planes(source_frame: AddressOneHotFrame,
                          target_frame: AddressOneHotFrame) -> dict[str, Any]:
    sf = dict(source_frame.address_factors); tf = dict(target_frame.address_factors)
    sc = sf.get("physical_coord6"); tc = tf.get("physical_coord6")
    if sc is None or tc is None:
        return {"available":False,"views":[],"residuals":["physical_coord6_missing_from_one_or_both_frames"]}
    sc=tuple(sc); tc=tuple(tc)
    if len(sc)!=3 or len(tc)!=3 or any(type(v) is not int for v in sc+tc):
        return {"available":False,"views":[],"residuals":["physical_coord6_not_exact_integer_triples"]}
    delta=tuple(tc[i]-sc[i] for i in range(3))
    views=[]
    for name,frame in PLANE_FRAMES:
        sl=_frame_point_local(frame,sc); tl=_frame_point_local(frame,tc)
        sd=_frame_point_local(frame,delta)
        views.append({"plane":name,"source_local":list(sl),"target_local":list(tl),
            "relative_step_local":list(sd),"source_lift":list(_frame_point_global(frame,sl)),
            "target_lift":list(_frame_point_global(frame,tl)),
            "relative_step_lift":list(_frame_point_global(frame,sd)),
            "lift_exact":(_frame_point_global(frame,sl)==sc and _frame_point_global(frame,tl)==tc and
                          _frame_point_global(frame,sd)==delta)})
    return {"available":True,"source_coord6":list(sc),"target_coord6":list(tc),
        "relative_step":list(delta),"views":views,"all_lifts_exact":all(x["lift_exact"] for x in views),
        "residuals":[]}


def build_cross_fractal_onehot_scaled_step(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], source_depth: int,
        target_depth: int, signed_ticks: int, aperture_stage_index: int = 3,
        execute_step: bool = True, context_preverified: bool = False) -> dict[str, Any]:
    """Compare opened recursive one-hot frames and scale a 504 step by exact word fidelity.

    `matched/common` is reduced as an exact integer ratio. A step is executed only
    when frames are same typed family/rank, both are genuinely seeded in the reopened
    locked cone, the selected prime aperture is authorized, and the scaled tick count
    is integral. Partial or cross-aperture comparisons remain inspectable without
    executing an unjustified movement. This is structural scaling, not physical calibration.
    """
    if not isinstance(address,BCFloorAddress) or not isinstance(cone,DepthWaveCone):
        raise TypeError("cross_fractal_onehot_requires_address_and_cone")
    if type(source_depth) is not int or type(target_depth) is not int or source_depth<0 or target_depth<0:
        raise ValueError("cross_fractal_depths_must_be_nonnegative_integers")
    if source_depth==target_depth:
        raise ValueError("cross_fractal_depths_must_differ")
    if type(signed_ticks) is not int or abs(signed_ticks)>HARMONIC_HEADS*10:
        raise ValueError("cross_fractal_signed_ticks_out_of_range")
    if type(aperture_stage_index) is not int or aperture_stage_index not in range(len(HARMONIC_APERTURE_STAGES)):
        raise ValueError("cross_fractal_aperture_stage_out_of_range")
    if type(execute_step) is not bool:
        raise TypeError("cross_fractal_execute_step_must_be_boolean")
    if type(context_preverified) is not bool:
        raise TypeError("cross_fractal_context_preverified_must_be_boolean")
    if cone.root_address_id != address.address_id:
        raise ValueError("cross_fractal_cone_root_mismatch")
    # The lock-opening reopen rebuilds the lock and complete opening from root;
    # compare the supplied cone payload directly instead of reopening the same cone
    # a second time in this operation.
    if context_preverified:
        # Internal batch fast path: caller already ran a full opening reopen or created
        # this context through _fb_build_context. Recheck packet hash, lock and bindings,
        # but do not reconstruct the same cone a second time.
        obody={k:v for k,v in opening.items() if k!="opening_address"}
        opening_hash_ok=(_sha256_text(_canonical_json(obody))[:32] == opening.get("opening_address"))
        opening_lock_ok=reopen_fractal_aperture_lock(address,lock).get("pass",False)
        opening_reopen={"pass":bool(opening_hash_ok and opening_lock_ok and
            opening.get("root_address_id")==address.address_id and
            opening.get("lock_address")==lock.get("lock_address")),
            "fast_bound_packet_check":True}
    else:
        opening_reopen=reopen_fractal_locked_cone(address,lock,opening)
    if not opening_reopen.get("pass"):
        raise ValueError("cross_fractal_lock_opening_reopen_failed")
    if (opening.get("lock_address")!=lock.get("lock_address") or
            opening.get("cone",{}).get("cone_address")!=cone.cone_address or
            opening.get("cone")!=cone.as_dict()):
        raise ValueError("cross_fractal_opening_binding_mismatch")
    if not lock.get("authorized"):
        raise ValueError("cross_fractal_work_lock_not_authorized")
    if target_depth>lock.get("effective_depth_cap",-1) or source_depth>lock.get("effective_depth_cap",-1):
        raise ValueError("cross_fractal_depth_exceeds_lock")
    aperture_cap=lock.get("apertures",{}).get("aperture_stage_cap",-1)
    if aperture_stage_index>aperture_cap:
        raise ValueError("cross_fractal_prime_aperture_exceeds_lock")
    available=set(lock.get("transition_families",{}).get("available",()))
    needed={3:"prime3",5:"prime5",7:"prime7"}
    for prime in HARMONIC_APERTURE_STAGES[aperture_stage_index]:
        if needed[prime] not in available:
            raise ValueError(f"cross_fractal_prime_lane_not_locked:{prime}")
    source_open,source_block=_cone_has_opened_recursive_frame(address,cone,source_depth,opening)
    target_open,target_block=_cone_has_opened_recursive_frame(address,cone,target_depth,opening)
    # Build the source's sparse one-hot frame index once for both depths.
    frames_by_name={frame.frame_name:frame for frame in _address_onehot_frames(address)}
    source_name="root.lattice216" if source_depth==0 else f"levels.{source_depth-1}"
    target_name="root.lattice216" if target_depth==0 else f"levels.{target_depth-1}"
    if source_name not in frames_by_name or target_name not in frames_by_name:
        raise ValueError("cross_fractal_requested_depth_not_present_in_address")
    source_frame=frames_by_name[source_name]
    target_frame=frames_by_name[target_name]
    common=[]; matched=[]; mismatched=[]
    target_words={(w.family,w.width):w for w in target_frame.words}
    for word in source_frame.words:
        other=target_words.get((word.family,word.width))
        if other is None: continue
        entry={"family":word.family,"width":word.width,"source":word.as_dict(),"target":other.as_dict(),
               "exact_match":_onehot_word_value(word)==_onehot_word_value(other)}
        common.append(entry)
        (matched if entry["exact_match"] else mismatched).append(word.family)
    same_frame_type=(source_frame.frame_kind==target_frame.frame_kind and
                     source_frame.aperture_address==target_frame.aperture_address and
                     source_frame.dimension_rank==target_frame.dimension_rank)
    comparable=len(common); matched_count=len(matched)
    residuals=[]
    if not same_frame_type: residuals.append("cross_aperture_or_dimension_comparison_only_no_step_scaling")
    if comparable==0: residuals.append("no_shared_typed_onehot_basis")
    if not source_open: residuals.append(source_block or "source_frame_not_opened")
    if not target_open: residuals.append(target_block or "target_frame_not_opened")
    scale_num=matched_count; scale_den=comparable
    if scale_den:
        divisor=_integer_gcd(scale_num,scale_den) or 1
        scale_num//=divisor; scale_den//=divisor
    effective_ticks=None; scale_integral=False; step=None; step_reopen=None; cog=None
    can_scale=(same_frame_type and comparable>0 and matched_count>0 and source_open and target_open)
    if can_scale:
        scaled_numerator=signed_ticks*scale_num
        if scaled_numerator % scale_den==0:
            effective_ticks=scaled_numerator//scale_den
            scale_integral=True
        else:
            residuals.append("structural_fidelity_requires_fractional_step_not_representable")
    elif same_frame_type and comparable>0 and matched_count==0:
        residuals.append("zero_exact_onehot_word_fidelity_step_blocked")
    stage_prefix=HARMONIC_APERTURE_STAGES[aperture_stage_index]
    if effective_ticks is not None and execute_step:
        hf_frame=open_harmonic_fractal_frame(address,source_frame.frame_name,"root.lattice216")
        step=step_harmonic_fractal_center(address,hf_frame,effective_ticks,True)
        step_reopen=reopen_harmonic_fractal_step(address,hf_frame,step)
        phase=address.prime_harmonic.winding*HARMONIC_HEADS+address.prime_harmonic.head
        cog=prime_cog_bundle_step(phase,effective_ticks)
        if not step.pass_all or not step_reopen.get("pass") or not cog.all_projections_replay:
            residuals.append("scaled_harmonic_step_or_prime_cog_replay_failed")
    plane_views=_onehot_scale_planes(source_frame,target_frame)
    if plane_views.get("available") and not plane_views.get("all_lifts_exact"):
        residuals.append("cross_fractal_six_plane_lift_mismatch")
    lane_rows=[]
    if cog is not None:
        lane_by_rate={lane.rate:lane for lane in cog.lanes}
        for prime in stage_prefix:
            lane=lane_by_rate[prime]
            lane_rows.append({"prime":prime,"lane_address":lane.lane_address,
                "projection_matches_whole_phase":lane.projection_matches_whole_phase,
                "full_sphere_head_moved":lane.full_sphere_head_moved,
                "same_onehot_octant":lane.same_onehot_octant,
                "cycle_delta":lane.signed_sphere_cycles_crossed})
    executed=(effective_ticks is not None and step is not None and step.pass_all and
              step_reopen is not None and step_reopen.get("pass") and
              (not plane_views.get("available") or plane_views.get("all_lifts_exact")) and
              all(x["projection_matches_whole_phase"] for x in lane_rows))
    body={"schema":"BC-CROSS-FRACTAL-ONEHOT-SCALED-STEP-1","source_address_id":address.address_id,
        "cone_address":cone.cone_address,"lock_address":lock["lock_address"],"opening_address":opening["opening_address"],
        "source_depth":source_depth,"target_depth":target_depth,"source_frame":source_frame.as_dict(),
        "target_frame":target_frame.as_dict(),"same_typed_frame_family":same_frame_type,
        "common_onehot_words":common,"comparable_word_count":comparable,"matched_word_families":matched,
        "mismatched_word_families":mismatched,"structural_fidelity":{"numerator":matched_count,
        "denominator":comparable,"reduced_numerator":scale_num,"reduced_denominator":scale_den,
        "exact_match_ratio":f"{scale_num}/{scale_den}" if scale_den else None,
        "interpretation":"combinatorial one-hot word fidelity; not physical units or universal semantic equivalence"},
        "requested_ticks":signed_ticks,"effective_ticks":effective_ticks,"scale_integral":scale_integral,
        "execution_mode":"execute" if execute_step else "compare_only",
        "context_verification":"bound_packet_and_lock" if context_preverified else "full_opening_rebuild",
        "aperture_stage_index":aperture_stage_index,"aperture_prefix":list(stage_prefix),
        "selected_prime_lane_checks":lane_rows,"prime_cog_bundle":None if cog is None else cog.as_dict(),
        "source_frame_opened":source_open,"target_frame_opened":target_open,"six_plane_alignment":plane_views,
        "step":None if step is None else step.as_dict(),"step_reopen":step_reopen,
        "step_executed":executed,"pass":bool(source_open and target_open and comparable>0 and plane_views.get("available",True)),
        "residuals":sorted(set(residuals)),"deeper_states_opened":False,"frontier_traversed":False,
        "glyph_admission":False,"persistent_save":False,"cold_commit":False,
        "claim_boundary":"fidelity-scaled sphere504 movement conditioned on two opened same-family recursive one-hot frames; no physical calibration or global-centre-depth claim"}
    body["step_plan_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def reopen_cross_fractal_onehot_scaled_step(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(packet,Mapping) or packet.get("schema")!="BC-CROSS-FRACTAL-ONEHOT-SCALED-STEP-1":
            raise TypeError("cross_fractal_onehot_step_packet_required")
        body={k:v for k,v in packet.items() if k!="step_plan_address"}
        if _sha256_text(_canonical_json(body))[:32]!=packet.get("step_plan_address"):
            raise ValueError("cross_fractal_onehot_step_content_address_mismatch")
        rebuilt=build_cross_fractal_onehot_scaled_step(address,cone,lock,opening,
            packet["source_depth"],packet["target_depth"],packet["requested_ticks"],packet["aperture_stage_index"],
            packet.get("execution_mode","execute")!="compare_only",
            packet.get("context_verification","full_opening_rebuild")=="bound_packet_and_lock")
        passed=rebuilt==dict(packet)
        return {"schema":"BC-CROSS-FRACTAL-ONEHOT-SCALED-STEP-REOPEN-1","pass":passed,
            "step_plan_address":packet["step_plan_address"],"rebuilt_step_plan_address":rebuilt.get("step_plan_address"),
            "same_source_cone_lock_opening":passed,"exact_ratio_recomputed":passed,
            "step_witness_rebuilt":passed and packet.get("step_reopen",{}).get("pass",False),
            "frontier_traversed":False,"glyph_admission":False,"persistent_save":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-CROSS-FRACTAL-ONEHOT-SCALED-STEP-REOPEN-1","pass":False,
            "reason":f"{type(exc).__name__}:{exc}","frontier_traversed":False}


def cross_fractal_onehot_summary() -> dict[str, Any]:
    return {"enabled":True,"method":"same-family recursive one-hot words produce an exact reduced integer fidelity ratio; sphere504 ticks are scaled only if the ratio yields an integral step and both frames are seeded in the reopened locked cone",
        "glyphs":["BC.FRACTAL.1HOT.SCALE.STEP","BC.FRACTAL.1HOT.SCALE.STEP.REOPEN"],
        "fidelity":"matched comparable sparse one-hot words / comparable typed word count; exact integer ratio",
        "prime_aperture_stages": [list(x) for x in HARMONIC_APERTURE_STAGES],
        "six_plane_roundtrip":True,"same_frame_kind_rank_and_aperture_required_for_step":True,
        "cross_aperture_matches_are_comparison_only":True,"missing_opened_depth_blocks_step":True,
        "unopened_frontier_traversed":False,"physical_calibration_claimed":False,"global_fractal_center_depth_known":False,
        "automatic_glyph_admission":False,"persistent_save":False}


REGISTRY.register("build_cross_fractal_onehot_scaled_step",build_cross_fractal_onehot_scaled_step,"pure")
REGISTRY.register("reopen_cross_fractal_onehot_scaled_step",reopen_cross_fractal_onehot_scaled_step,"pure")
for _cross_fractal_spec in (
    GlyphSpec.make("BC.FRACTAL.1HOT.SCALE.STEP","build_cross_fractal_onehot_scaled_step",
        ("address","cone","lock","opening","source_depth","target_depth","signed_ticks"),("aperture_stage_index",),
        {"address":"full_address","cone":"depth_wave_cone","lock":"mapping",
         "opening":"mapping","source_depth":"nonnegative_integer","target_depth":"nonnegative_integer",
         "signed_ticks":"integer","aperture_stage_index":"nonnegative_integer"},"pure",
        "compare actual opened recursive one-hot frames, scale an integer sphere504 step by exact matched-word fidelity, and verify selected prime lanes; partial and unopened cases retain residuals"),
    GlyphSpec.make("BC.FRACTAL.1HOT.SCALE.STEP.REOPEN","reopen_cross_fractal_onehot_scaled_step",
        ("address","cone","lock","opening","packet"),(),
        {"address":"full_address","cone":"depth_wave_cone","lock":"mapping",
         "opening":"mapping","packet":"mapping"},"pure",
        "recompute the exact cross-fractal one-hot ratio, selected aperture checks, scaled sphere step and witness"),
):
    GLYPH_CATALOG.register(_cross_fractal_spec)



# Bounded multi-step composition: one mechanic carries exact rational remainder
# across steps and localizes any terminal fractional stall to the addressed frame.
_FRACTAL_BATCH_MAX_STEPS = 16


def _fb_reduce(num: int, den: int) -> tuple[int, int]:
    if type(num) is not int or type(den) is not int or den == 0:
        raise ValueError("fractal_batch_rational_must_use_nonzero_integer_denominator")
    if den < 0:
        num, den = -num, -den
    if num == 0:
        return 0, 1
    g = _integer_gcd(abs(num), den) or 1
    return num // g, den // g


def _fb_carry_state(raw: Mapping[str, Any] | None) -> tuple[int, int]:
    if raw is None:
        return 0, 1
    if not isinstance(raw, Mapping):
        raise TypeError("fractal_batch_carry_state_must_be_mapping")
    num, den = raw.get("numerator"), raw.get("denominator")
    if type(num) is not int or type(den) is not int or den <= 0:
        raise ValueError("fractal_batch_carry_state_invalid")
    n, d = _fb_reduce(num, den)
    if (n, d) != (num, den) or abs(n) >= d:
        raise ValueError("fractal_batch_carry_state_must_be_reduced_proper_fraction")
    return n, d


def _fb_add_carry(carry: tuple[int, int], step_num: int, step_den: int) -> tuple[int, tuple[int, int]]:
    cn, cd = carry
    total_num = cn * step_den + step_num * cd
    total_den = cd * step_den
    total_num, total_den = _fb_reduce(total_num, total_den)
    # Truncate toward zero, so sign-reversed paths remain symmetric.
    whole = (abs(total_num) // total_den) * (1 if total_num >= 0 else -1)
    rn, rd = _fb_reduce(total_num - whole * total_den, total_den)
    return whole, (rn, rd)


def _fb_build_context(address: BCFloorAddress, req: Mapping[str, Any],
                      aperture_cap: int | None = None, wave_radius: int | None = None) -> tuple[dict[str, Any], dict[str, Any], DepthWaveCone]:
    stage_cap = req.get("aperture_stage_cap", 3) if aperture_cap is None else aperture_cap
    radius = req["wave_radius"] if wave_radius is None else wave_radius
    lock = build_fractal_aperture_lock(address,
        requested_depth=req["requested_depth"], wave_radius=radius,
        aperture_families=tuple(req["aperture_families"]),
        transition_families=tuple(req["transition_families"]), aperture_stage_cap=stage_cap,
        include_root_lattice=req["include_root_lattice"], max_nodes=req["max_nodes"],
        max_frontier_edges=req["max_frontier_edges"], max_transition_edges=req["max_transition_edges"],
        max_transition_families=req["max_transition_families"])
    opening = open_fractal_locked_cone(address, lock)
    if not opening.get("pass", True):
        raise ValueError("fractal_batch_locked_opening_failed")
    cone = _scb_depth_wave_cone_from_dict(opening["cone"])
    return lock, opening, cone


def _fb_execute_integer(address: BCFloorAddress, source_depth: int, target_depth: int,
                        integer_ticks: int, aperture_stage_index: int) -> dict[str, Any]:
    if integer_ticks == 0:
        return {"executed":False,"reason":"fractional_carry_not_yet_integral","step":None,
                "step_reopen":None,"selected_prime_lanes":[],"after_address":address.as_dict()}
    source_selector = "root.lattice216" if source_depth == 0 else f"levels.{source_depth - 1}"
    hf_frame = open_harmonic_fractal_frame(address, source_selector, "root.lattice216")
    step = step_harmonic_fractal_center(address, hf_frame, integer_ticks, True)
    reopened = reopen_harmonic_fractal_step(address, hf_frame, step)
    phase = address.prime_harmonic.winding * HARMONIC_HEADS + address.prime_harmonic.head
    cog = prime_cog_bundle_step(phase, integer_ticks)
    by_rate = {lane.rate: lane for lane in cog.lanes}
    selected = []
    for prime in HARMONIC_APERTURE_STAGES[aperture_stage_index]:
        lane = by_rate[prime]
        selected.append({"prime":prime,"lane_address":lane.lane_address,
            "projection_matches_whole_phase":lane.projection_matches_whole_phase,
            "full_sphere_head_moved":lane.full_sphere_head_moved,
            "same_onehot_octant":lane.same_onehot_octant,
            "cycle_delta":lane.signed_sphere_cycles_crossed})
    passed = bool(step.pass_all and reopened.get("pass") and cog.all_projections_replay and
                  all(row["projection_matches_whole_phase"] for row in selected))
    if not passed:
        raise ValueError("fractal_batch_integer_step_witness_failed")
    return {"executed":True,"reason":None,"step":step.as_dict(),"step_reopen":reopened,
            "selected_prime_lanes":selected,"after_address":step.after_address.as_dict(),
            "prime_cog_bundle":cog.as_dict()}


def build_cross_fractal_onehot_scaled_batch(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], steps: Sequence[Mapping[str, Any]],
        carry_in: Mapping[str, Any] | None = None, terminal_batch: bool = False,
        max_steps: int = _FRACTAL_BATCH_MAX_STEPS) -> dict[str, Any]:
    """Run a bounded transition batch with exact fractional carry and frame-local terminal backlash.

    One glyph covers different depths, prime aperture prefixes and signed steps. Fractional
    remainders carry across step and batch boundaries; only a terminal nonzero remainder
    stages a frame-local backlash and attempts a one-stage aperture opening.
    """
    if not isinstance(address, BCFloorAddress) or not isinstance(cone, DepthWaveCone):
        raise TypeError("fractal_batch_requires_full_address_and_depth_wave_cone")
    if not isinstance(lock, Mapping) or not isinstance(opening, Mapping):
        raise TypeError("fractal_batch_requires_lock_and_opening_mappings")
    if cone.root_address_id != address.address_id or lock.get("root_address_id") != address.address_id or opening.get("root_address_id") != address.address_id:
        raise ValueError("fractal_batch_initial_context_root_mismatch")
    if type(terminal_batch) is not bool:
        raise TypeError("fractal_batch_terminal_flag_must_be_boolean")
    if type(max_steps) is not int or not 1 <= max_steps <= _FRACTAL_BATCH_MAX_STEPS:
        raise ValueError("fractal_batch_max_steps_out_of_range")
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)) or not 1 <= len(steps) <= max_steps:
        raise ValueError("fractal_batch_step_count_out_of_range")
    if not reopen_fractal_locked_cone(address, lock, opening).get("pass"):
        raise ValueError("fractal_batch_initial_opening_reopen_failed")
    base_req = dict(lock.get("request", {}))
    required_req = {"requested_depth","wave_radius","aperture_families","transition_families","aperture_stage_cap",
                    "include_root_lattice","max_nodes","max_frontier_edges","max_transition_edges","max_transition_families"}
    if not required_req.issubset(base_req):
        raise ValueError("fractal_batch_lock_request_incomplete")
    carry = _fb_carry_state(carry_in)
    initial_carry = {"numerator":carry[0],"denominator":carry[1]}
    current = address
    active_lock, active_opening, active_cone = lock, opening, cone
    rows: list[dict[str, Any]] = []
    batch_residuals: list[str] = []
    carry_stalled_on: dict[str, Any] | None = None
    for idx, raw in enumerate(steps):
        if not isinstance(raw, Mapping):
            raise TypeError(f"fractal_batch_step_{idx}_must_be_mapping")
        source_depth, target_depth, requested_ticks = raw.get("source_depth"), raw.get("target_depth"), raw.get("signed_ticks")
        stage = raw.get("aperture_stage_index", active_lock.get("apertures", {}).get("aperture_stage_cap", 3))
        if type(source_depth) is not int or type(target_depth) is not int or source_depth < 0 or target_depth < 0 or source_depth == target_depth:
            raise ValueError(f"fractal_batch_step_{idx}_depth_pair_invalid")
        if type(requested_ticks) is not int or abs(requested_ticks) > HARMONIC_HEADS * 10:
            raise ValueError(f"fractal_batch_step_{idx}_ticks_out_of_range")
        if type(stage) is not int or stage not in range(len(HARMONIC_APERTURE_STAGES)):
            raise ValueError(f"fractal_batch_step_{idx}_aperture_stage_invalid")
        if current.address_id != active_lock.get("root_address_id"):
            active_lock, active_opening, active_cone = _fb_build_context(current, base_req)
        if source_depth > active_lock.get("effective_depth_cap", -1) or target_depth > active_lock.get("effective_depth_cap", -1):
            raise ValueError(f"fractal_batch_step_{idx}_depth_exceeds_locked_cone")
        if stage > active_lock.get("apertures", {}).get("aperture_stage_cap", -1):
            raise ValueError(f"fractal_batch_step_{idx}_aperture_exceeds_lock")
        probe = build_cross_fractal_onehot_scaled_step(current, active_cone, active_lock, active_opening,
            source_depth, target_depth, requested_ticks, stage, execute_step=False, context_preverified=True)
        if not probe.get("pass") or not probe.get("source_frame_opened") or not probe.get("target_frame_opened"):
            batch_residuals.extend(f"step_{idx}:{x}" for x in probe.get("residuals", []))
            rows.append({"index":idx,"input":dict(raw),"source_address_id":current.address_id,
                "probe_address":probe.get("step_plan_address"),"fidelity":probe.get("structural_fidelity"),
                "carry_in":{"numerator":carry[0],"denominator":carry[1]},"emitted_ticks":0,
                "carry_out":{"numerator":carry[0],"denominator":carry[1]},"executed":False,
                "reason":"source_or_target_frame_not_validly_opened","after_address":current.as_dict(),
                "probe":probe,"step":None,"residuals":list(probe.get("residuals", []))})
            if carry != (0, 1):
                carry_stalled_on = {"step_index":idx,"source_address_id":current.address_id,
                    "after_address_id":current.address_id,"source_depth":source_depth,"target_depth":target_depth,
                    "requested_ticks":requested_ticks,"aperture_stage_index":stage,
                    "frame_address":(probe.get("source_frame") or {}).get("frame_address"),
                    "fractional_remainder":{"numerator":carry[0],"denominator":carry[1]}}
            continue
        fidelity = probe.get("structural_fidelity", {})
        scale_num, scale_den = fidelity.get("reduced_numerator"), fidelity.get("reduced_denominator")
        if (not probe.get("same_typed_frame_family") or type(scale_num) is not int or type(scale_den) is not int or
            scale_den <= 0 or scale_num <= 0):
            reason = "no_positive_same-family_onehot_fidelity_to_scale_step"
            batch_residuals.append(f"step_{idx}:{reason}")
            rows.append({"index":idx,"input":dict(raw),"source_address_id":current.address_id,
                "probe_address":probe["step_plan_address"],"fidelity":fidelity,
                "carry_in":{"numerator":carry[0],"denominator":carry[1]},"scaled_rational":None,
                "emitted_ticks":0,"carry_out":{"numerator":carry[0],"denominator":carry[1]},
                "executed":False,"reason":reason,"after_address":current.as_dict(),
                "probe":probe,"step":None,"residuals":[reason]})
            if carry != (0, 1):
                carry_stalled_on = {"step_index":idx,"source_address_id":current.address_id,
                    "after_address_id":current.address_id,"source_depth":source_depth,"target_depth":target_depth,
                    "requested_ticks":requested_ticks,"aperture_stage_index":stage,
                    "frame_address":(probe.get("source_frame") or {}).get("frame_address"),
                    "fractional_remainder":{"numerator":carry[0],"denominator":carry[1]}}
            continue
        scaled_num, scaled_den = _fb_reduce(requested_ticks * scale_num, scale_den)
        before_carry = carry
        emitted, carry = _fb_add_carry(carry, scaled_num, scaled_den)
        execution = _fb_execute_integer(current, source_depth, target_depth, emitted, stage)
        if execution["executed"]:
            current = BCFloorAddress.from_dict(execution["after_address"])
            # Defer re-opening until another step needs the current root or the batch
            # needs a resumable endpoint. This avoids creating a cone that no operation uses.
        if carry != (0, 1):
            carry_stalled_on = {"step_index":idx,"source_address_id":probe["source_address_id"],
                "after_address_id":current.address_id,"source_depth":source_depth,"target_depth":target_depth,
                "requested_ticks":requested_ticks,"aperture_stage_index":stage,
                "frame_address":(execution["step"].get("after_frame", {}).get("frame_address")
                    if execution["executed"] and isinstance(execution.get("step"), Mapping)
                    else probe["source_frame"].get("frame_address")),
                "fractional_remainder":{"numerator":carry[0],"denominator":carry[1]}}
        else:
            carry_stalled_on = None
        rows.append({"index":idx,"input":dict(raw),"source_address_id":probe["source_address_id"],
            "probe_address":probe["step_plan_address"],"fidelity":fidelity,
            "scaled_rational_before_carry":{"numerator":scaled_num,"denominator":scaled_den},
            "carry_in":{"numerator":before_carry[0],"denominator":before_carry[1]},
            "accumulated_emitted_ticks":emitted,
            "carry_out":{"numerator":carry[0],"denominator":carry[1]},
            "executed":execution["executed"],"reason":execution["reason"],
            "after_address":current.as_dict(),"probe":probe,"step":execution["step"],
            "step_reopen":execution["step_reopen"],"selected_prime_lanes":execution["selected_prime_lanes"],
            "residuals":[] if execution["executed"] or emitted == 0 else ["integer_step_not_executed"]})
    terminal_backlash = None
    aperture_opening = None
    if terminal_batch and carry != (0, 1):
        # Backlash is attached only to this final addressed frame; it never mutates the
        # authoritative full address or turns a frontier into a traversable route.
        context_is_current = active_lock.get("root_address_id") == current.address_id
        active_cap = int((active_lock.get("apertures", {}).get("aperture_stage_cap", 3)
                          if context_is_current else base_req.get("aperture_stage_cap", 3)))
        active_radius = int(active_lock.get("effective_wave_radius", base_req.get("wave_radius", 0)))
        terminal_backlash = {"schema":"BC-FRAME-LOCAL-FRACTIONAL-BACKLASH-1",
            "scope":"frame_local","address_id":current.address_id,
            "frame_address":carry_stalled_on.get("frame_address") if carry_stalled_on else None,
            "last_step_index":carry_stalled_on.get("step_index") if carry_stalled_on else None,
            "fractional_remainder":{"numerator":carry[0],"denominator":carry[1]},
            "authoritative_state_mutated":False,"frontier_traversed":False,
            "reason":"terminal_batch_has_unconsumed_fractional_movement"}
        aperture_kind = None
        try:
            if active_cap < len(HARMONIC_APERTURE_STAGES) - 1:
                escalated_lock, escalated_opening, escalated_cone = _fb_build_context(current, base_req, aperture_cap=active_cap + 1)
                aperture_kind = "prime_harmonic"
                opened_cap, opened_radius = active_cap + 1, escalated_lock.get("effective_wave_radius")
                aperture_reason = "terminal_fractional_backlash_requests_more_prime_aperture"
            elif active_radius < MAX_DEPTH_WAVE_RADIUS:
                escalated_lock, escalated_opening, escalated_cone = _fb_build_context(
                    current, base_req, aperture_cap=active_cap, wave_radius=active_radius + 1)
                aperture_kind = "spatial_wave"
                opened_cap, opened_radius = active_cap, escalated_lock.get("effective_wave_radius")
                aperture_reason = "terminal_fractional_backlash_requests_local_spatial_aperture"
            else:
                escalated_lock = escalated_opening = escalated_cone = None
                opened_cap = opened_radius = None
                aperture_reason = "no_higher_prime_or_spatial_aperture_within_lock_limits"
        except (TypeError, ValueError, LookupError) as exc:
            # Failed aperture expansion is a retained local residual, not a failed or
            # partially applied movement batch.
            escalated_lock = escalated_opening = escalated_cone = None
            opened_cap = opened_radius = None
            aperture_reason = f"aperture_escalation_refused_by_work_lock:{type(exc).__name__}:{exc}"
            batch_residuals.append("terminal_fractional_backlash_aperture_opening_not_authorized")
        if escalated_lock is not None:
            # Re-test fidelity under the newly opened aperture. The aperture may open
            # successfully but still fail to authorize the same depth pair under its
            # own tighter work budget; preserve that as a residual rather than aborting
            # an already-valid movement batch.
            opened_stage = int(opened_cap)
            try:
                recheck = build_cross_fractal_onehot_scaled_step(current, escalated_cone, escalated_lock,
                    escalated_opening, carry_stalled_on["source_depth"], carry_stalled_on["target_depth"],
                    carry_stalled_on["requested_ticks"], opened_stage, execute_step=False)
                recheck_ok = bool(recheck.get("pass") and recheck.get("source_frame_opened") and recheck.get("target_frame_opened"))
                recheck_error = None if recheck_ok else "opened_aperture_does_not_cover_both_comparison_frames"
            except (TypeError, ValueError, LookupError) as exc:
                recheck = {"schema":"BC-FRAME-LOCAL-FIDELITY-RECHECK-1","pass":False,
                    "reason":f"{type(exc).__name__}:{exc}","deeper_states_opened":False,"frontier_traversed":False}
                recheck_ok = False; recheck_error = recheck["reason"]
            before_ratio = rows[-1].get("fidelity", {}).get("exact_match_ratio") if rows else None
            after_ratio = recheck.get("structural_fidelity", {}).get("exact_match_ratio")
            if not recheck_ok:
                batch_residuals.append("terminal_fractional_backlash_fidelity_recheck_blocked_by_opening")
            aperture_opening = {"schema":"BC-FRAME-LOCAL-APERTURE-ESCALATION-1","pass":True,
                "kind":aperture_kind,"reason":aperture_reason,"source_address_id":current.address_id,
                "prior_aperture_cap":active_cap,"opened_aperture_cap":opened_cap,
                "prior_wave_radius":active_radius,"opened_wave_radius":opened_radius,
                "aperture_prefixes":[list(x) for x in HARMONIC_APERTURE_STAGES[:opened_cap+1]],
                "lock":escalated_lock,"opening":escalated_opening,"cone":escalated_cone.as_dict(),
                "lock_address":escalated_lock["lock_address"],"opening_address":escalated_opening["opening_address"],
                "fidelity_recheck":recheck,"fidelity_recheck_pass":recheck_ok,"fidelity_recheck_error":recheck_error,
                "fidelity_ratio_before":before_ratio,"fidelity_ratio_after":after_ratio,
                "fidelity_changed":(before_ratio != after_ratio) if recheck_ok else None,
                "fractional_remainder_preserved":{"numerator":carry[0],"denominator":carry[1]},
                "deeper_states_opened":False,"frontier_traversed":False}
            active_lock, active_opening, active_cone = escalated_lock, escalated_opening, escalated_cone
        else:
            aperture_opening = {"schema":"BC-FRAME-LOCAL-APERTURE-ESCALATION-1","pass":False,
                "kind":None,"reason":aperture_reason,"source_address_id":current.address_id,
                "prior_aperture_cap":active_cap,"opened_aperture_cap":None,
                "deeper_states_opened":False,"frontier_traversed":False}
            batch_residuals.append("terminal_fractional_backlash_no_higher_aperture_within_limits")
    elif terminal_batch:
        carry_stalled_on = None
    carry_out = {"numerator":carry[0],"denominator":carry[1]}
    batch_route_id = _sha256_text(_canonical_json({"kind":"cross_fractal_batch_route",
        "root":address.address_id,"source_lock":lock.get("lock_address"),
        "initial_opening":opening.get("opening_address"),"count":len(rows)}))[:24]
    relation_edges=[{"from":address.address_id,"to":batch_route_id,"relation":"source_opens_batch"}]
    route_ids=[]
    for row in rows:
        route_id=_sha256_text(_canonical_json({"kind":"cross_fractal_batch_step_route",
            "batch_route":batch_route_id,"index":row["index"],"probe":row.get("probe_address"),
            "input":row.get("input")}))[:24]
        row["route_id"]=route_id; route_ids.append(route_id)
        relation_edges.append({"from":batch_route_id,"to":route_id,"relation":"batch_contains_step"})
        if row.get("probe_address"):
            relation_edges.append({"from":route_id,"to":row["probe_address"],"relation":"opens_onehot_fidelity_comparison"})
        if isinstance(row.get("step"), Mapping) and row["step"].get("step_address"):
            relation_edges.append({"from":route_id,"to":row["step"]["step_address"],"relation":"witnesses_integer_movement"})
        relation_edges.append({"from":route_id,"to":row.get("after_address",{}).get("address_id"),"relation":"produces_address_state"})
        if row.get("index", -1) > 0:
            prev=rows[row["index"]-1]
            if prev.get("after_address",{}).get("address_id") == row.get("source_address_id"):
                relation_edges.append({"from":prev.get("route_id",route_ids[-2] if len(route_ids)>1 else batch_route_id),
                    "to":route_id,"relation":"ordered_state_handoff"})
    relation_edges.append({"from":batch_route_id,"to":current.address_id,"relation":"batch_final_address"})
    if terminal_backlash:
        relation_edges.append({"from":batch_route_id,"to":terminal_backlash.get("frame_address"),"relation":"terminal_frame_local_backlash"})
    if aperture_opening:
        relation_edges.append({"from":batch_route_id,"to":aperture_opening.get("opening_address"),"relation":"terminal_aperture_opening"})
    body={"schema":"BC-CROSS-FRACTAL-ONEHOT-BATCH-1","batch_route_id":batch_route_id,
        "relation_edges":relation_edges,"source_address_id":address.address_id,
        "source_cone_address":cone.cone_address,"source_lock_address":lock.get("lock_address"),
        "source_opening_address":opening.get("opening_address"),"max_steps":max_steps,
        "step_count":len(rows),"terminal_batch":terminal_batch,"carry_in":initial_carry,"carry_out":carry_out,
        "steps":rows,"after_address":current.as_dict(),"after_address_id":current.address_id,
        "terminal_backlash":terminal_backlash,"aperture_escalation":aperture_opening,
        "active_context_is_after_address":active_lock.get("root_address_id") == current.address_id,
        "active_lock_address":active_lock.get("lock_address") if active_lock.get("root_address_id") == current.address_id else None,
        "active_opening_address":active_opening.get("opening_address") if active_lock.get("root_address_id") == current.address_id else None,
        "active_cone_address":active_cone.cone_address if active_lock.get("root_address_id") == current.address_id else None,
        "resume_seed":{"after_address_id":current.address_id,"carry":carry_out,
            "work_policy":dict(active_lock.get("request",{}) if active_lock.get("root_address_id") == current.address_id else base_req),"next_batch_max_steps":_FRACTAL_BATCH_MAX_STEPS,
            "required_reopen_sequence":["restore after_address","rebuild lock from work_policy",
                "open locked cone","pass carry into next batch"],"continuation_address_is_not_data":True},
        "residuals":sorted(set(batch_residuals)),
        "all_executed_steps_witnessed":all((not r["executed"]) or bool(r.get("step_reopen",{}).get("pass")) for r in rows),
        "all_remainders_exact":True,"collision_backlash_is_frame_local":True,
        "frontier_traversed":False,"glyph_admission":False,"persistent_save":False,"cold_commit":False,
        "interpretation":"exact rational carry across fidelity-scaled sphere steps; terminal remainder opens one higher prime aperture if authorized; local backlash never mutates state or traverses frontiers"}
    body["batch_address"]=_sha256_text(_canonical_json(body))[:32]
    return body


def reopen_cross_fractal_onehot_scaled_batch(address: BCFloorAddress, cone: DepthWaveCone,
        lock: Mapping[str, Any], opening: Mapping[str, Any], steps: Sequence[Mapping[str, Any]],
        packet: Mapping[str, Any], carry_in: Mapping[str, Any] | None = None,
        terminal_batch: bool = False, max_steps: int = _FRACTAL_BATCH_MAX_STEPS) -> dict[str, Any]:
    try:
        if not isinstance(packet, Mapping) or packet.get("schema") != "BC-CROSS-FRACTAL-ONEHOT-BATCH-1":
            raise TypeError("cross_fractal_scaled_batch_packet_required")
        body={k:v for k,v in packet.items() if k!="batch_address"}
        if _sha256_text(_canonical_json(body))[:32] != packet.get("batch_address"):
            raise ValueError("cross_fractal_scaled_batch_content_address_mismatch")
        rebuilt=build_cross_fractal_onehot_scaled_batch(address,cone,lock,opening,steps,carry_in,terminal_batch,max_steps)
        passed=rebuilt == dict(packet)
        return {"schema":"BC-CROSS-FRACTAL-ONEHOT-BATCH-REOPEN-1","pass":passed,
            "batch_address":packet.get("batch_address"),"rebuilt_batch_address":rebuilt.get("batch_address"),
            "step_count":packet.get("step_count"),"step_witnesses_rebuilt":passed and rebuilt.get("all_executed_steps_witnessed"),
            "exact_carry_recomputed":passed,"terminal_backlash_recomputed":passed,
            "aperture_escalation_reopened":passed and (not (packet.get("aperture_escalation") or {}).get("pass") or
                reopen_fractal_locked_cone(BCFloorAddress.from_dict(packet["after_address"]),
                    packet["aperture_escalation"]["lock"],packet["aperture_escalation"]["opening"]).get("pass",False)),
            "frontier_traversed":False,"glyph_admission":False,"persistent_save":False}
    except (TypeError,ValueError,KeyError,LookupError) as exc:
        return {"schema":"BC-CROSS-FRACTAL-ONEHOT-BATCH-REOPEN-1","pass":False,
            "reason":f"{type(exc).__name__}:{exc}","frontier_traversed":False}


REGISTRY.register("build_cross_fractal_onehot_scaled_batch", build_cross_fractal_onehot_scaled_batch, "pure")
REGISTRY.register("reopen_cross_fractal_onehot_scaled_batch", reopen_cross_fractal_onehot_scaled_batch, "pure")
for _fractal_batch_spec in (
    GlyphSpec.make("BC.FRACTAL.1HOT.BATCH", "build_cross_fractal_onehot_scaled_batch",
        ("address","cone","lock","opening","steps"),("carry_in","terminal_batch","max_steps"),
        {"address":"full_address","cone":"depth_wave_cone","lock":"mapping","opening":"mapping",
         "steps":"step_mapping_sequence","carry_in":"mapping_or_null","terminal_batch":"boolean","max_steps":"bounded_positive_integer"},
        "pure","bounded multi-step cross-fractal one-hot scaling with exact rational carry, selected prime-lane witnesses and frame-local terminal aperture escalation"),
    GlyphSpec.make("BC.FRACTAL.1HOT.BATCH.REOPEN", "reopen_cross_fractal_onehot_scaled_batch",
        ("address","cone","lock","opening","steps","packet"),("carry_in","terminal_batch","max_steps"),
        {"address":"full_address","cone":"depth_wave_cone","lock":"mapping","opening":"mapping",
         "steps":"step_mapping_sequence","packet":"mapping","carry_in":"mapping_or_null","terminal_batch":"boolean","max_steps":"bounded_positive_integer"},
        "pure","rebuild the bounded batch, exact carry, per-step witnesses, terminal backlash and aperture escalation from the original context"),
):
    GLYPH_CATALOG.register(_fractal_batch_spec)



# ---------------------------------------------------------------------------
# Crown engine map: the complete in-engine navigation graph and its compact
# continuation head. The head selects a route; it is never the archive itself.
# Every symbol, registered operation, glyph, subsystem, history route and
# on-disk evidence artifact remains independently addressable.
# ---------------------------------------------------------------------------

_CROWN_PREVIOUS_ROUTE_ID = "BC-CROWN-ROUTE-82688c8ecfe836e7"  # previous current map; full map/reopen/tests/workpack appended below
_CROWN_CURRENT_SCOPE = (
    "in-engine Crown map; append-preserve prior whole-map route; map source symbols, registered operations, "
    "glyph control surface, cross-fractal batch evidence, and the exact-source cold-release regression suite"
)
_CROWN_ROUTE_HISTORY_SEED = (
    {"route_id":"BC-CROWN-ROUTE-SELF-6f28088742d8566d", "parent_route_id":"",
     "source_sha256":"6f28088742d8566d43a2444fa8e3f6921dec2299b6034f5214403a555f6dbb75",
     "label":"Read-only engine self-map", "scope":"AST/source/glyph/structuralizer/self-feed inventory",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_SELF_MAP.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_SELF_MAP.md",
     "workpack":"history/workpacks/BC_WARM_SELF_MAP_WORKPACK.zip"},
    {"route_id":"BC-CROWN-ROUTE-REL-e5eba0ca3c9bc6c0", "parent_route_id":"BC-CROWN-ROUTE-SELF-6f28088742d8566d",
     "source_sha256":"e5eba0ca3c9bc6c0fce19c6c09de9cb5653539445048a599bfc20a1df8bc45d9",
     "label":"Unified relation map", "scope":"address opening, cross-scale projections and evidence-backed routing",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_RELATIONS.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_RELATIONS.md",
     "workpack":"history/workpacks/BC_RELATION_MAP_WORKPACK.zip"},
    {"route_id":"BC-CROWN-ROUTE-COG64-12dccddba69fc30c", "parent_route_id":"BC-CROWN-ROUTE-REL-e5eba0ca3c9bc6c0",
     "source_sha256":"12dccddba69fc30cfcfd8c42ffd5340d89d3a10e9e28be3611e1a4e6cb3ef7d4",
     "label":"COG64 prime-harmonic projection", "scope":"finite sphere504/aperture state space and compact page receipts",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_COG64.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_COG64.md",
     "workpack":"history/workpacks/BC_COG64_PRIME_HARMONIC_COG_WORKPACK.zip"},
    {"route_id":"BC-CROWN-ROUTE-LOCKS-0bb423258394ab64", "parent_route_id":"BC-CROWN-ROUTE-COG64-12dccddba69fc30c",
     "source_sha256":"0bb423258394ab64d3c14206780165c27aa779a1a9bb6fbe5c8cf236b5e43bdf",
     "label":"Fractal depth/aperture work locks", "scope":"aggregate budgets, collision cones and frontiers",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_LOCKS.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_LOCKS.md",
     "workpack":"history/workpacks/BC_FRACTAL_DEPTH_LOCK_WORKPACK.zip"},
    {"route_id":"BC-CROWN-ROUTE-1HOT-0f00fde8933f0498", "parent_route_id":"BC-CROWN-ROUTE-LOCKS-0bb423258394ab64",
     "source_sha256":"0f00fde8933f0498c64099654c2684958ec3d0bbcbaa81c3e30b4d2bf600cbd2",
     "label":"Cross-fractal one-hot scaling", "scope":"addressed one-hot fidelity and scale-adjusted sphere movements",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_SCALE.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_SCALE.md",
     "workpack":"history/workpacks/BC_CROSS_FRACTAL_SCALE_WARM_WORKPACK.zip"},
    {"route_id":"BC-CROWN-ROUTE-BATCH-f1ba731239e99765", "parent_route_id":"BC-CROWN-ROUTE-1HOT-0f00fde8933f0498",
     "source_sha256":"f1ba731239e99765c60943e4e26d1e11fe0aaf1faa3289a717bea627fdf9315b",
     "label":"Bounded cross-fractal one-hot batches", "scope":"exact carry, local backlash and aperture escalation",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_BATCH.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_BATCH.md",
     "workpack":"history/workpacks/BC_CROSS_FRACTAL_BATCH_WARM_WORKPACK.zip"},
    {"route_id":"BC-CROWN-ROUTE-2353f6ace351f91c", "parent_route_id":"BC-CROWN-ROUTE-BATCH-f1ba731239e99765",
     "source_sha256":"2353f6ace351f91c192b96e020e819d8aff53c3fd8a68cd9507f17d4a221e093",
     "label":"Crown whole-engine map v1", "scope":"first in-engine whole-source map, bounded route/artifact opening, and preserved route history",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_CROWN_V1.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_CROWN_V1.md",
     "workpack":"history/workpacks/BC_CROWN_ENGINE_MAP_WARM_WORKPACK_V1.zip",
     "map_snapshot":"history/maps/BC_CROWN_ENGINE_MAP_V1.json",
     "map_reopen_receipt":"history/maps/BC_CROWN_ENGINE_MAP_V1_REOPEN.json",
     "map_test_receipt":"history/maps/BC_CROWN_ENGINE_MAP_V1_TESTS.json"},
    {"route_id":"BC-CROWN-ROUTE-82688c8ecfe836e7", "parent_route_id":"BC-CROWN-ROUTE-2353f6ace351f91c",
     "source_sha256":"82688c8ecfe836e728d6c4320b802b302b723c563b0fa24cd82788c9be3a53d5",
     "label":"Crown whole-engine map v2 — bounded query and preserved route history",
     "scope":"whole-source map and bounded query/open path; cross-fractal batch work; previous route nodes preserved",
     "route_json":"history/routes/BC_CROWN_CONTINUATION_WARM_CROWN_V2.json",
     "route_md":"history/routes/BC_CROWN_CONTINUATION_WARM_CROWN_V2.md",
     "workpack":"history/workpacks/BC_CROWN_ENGINE_MAP_WARM_WORKPACK_V2.zip",
     "map_snapshot":"history/maps/BC_CROWN_ENGINE_MAP_V2.json",
     "map_reopen_receipt":"history/maps/BC_CROWN_ENGINE_MAP_V2_REOPEN.json",
     "map_test_receipt":"history/maps/BC_CROWN_ENGINE_MAP_V2_TESTS.json"},
)
_CROWN_CURRENT_ARTIFACT_PATHS = (
    ("BC_WARM.py", "current executable engine source", "source"),
    ("BC_WARM_PARENT.py", "immediate source parent for exact patch replay", "source_parent"),
    ("BC_CROWN_ENGINE_MAP_WARM.patch", "exact source delta from immediate parent", "patch"),
    ("BC_WARM_WELCOME.json", "full cold-welcome style scope report", "welcome"),
    ("BC_WARM_CAPABILITY_SUMMARY.json", "compact capability and authority summary", "capability_summary"),
    ("BC_CROSS_FRACTAL_BATCH_REPORT.md", "current development report", "report"),
    ("BC_CROSS_FRACTAL_BATCH_WORKLIST.md", "next work and residuals", "worklist"),
    ("README_RESUME.md", "portable resume instructions", "resume_instructions"),
    ("actual_data/BC_CROSS_FRACTAL_BATCH_EVIDENCE.json", "full batch input/output/witness evidence", "actual_data"),
    ("actual_data/BC_CROSS_FRACTAL_BATCH_TESTS.json", "predecessor batch fixture results", "historical_test_results"),
    ("BC_CROSS_FRACTAL_BATCH_TESTS_CURRENT_SOURCE.py", "repeatable bounded-batch regression on the active source", "test_harness"),
    ("BC_CROSS_FRACTAL_BATCH_VALIDATION_CURRENT_SOURCE.json", "bounded batch regression rerun against current Crown source", "validation_summary"),
    ("actual_data/BC_BATCH_THROUGHPUT_PROFILE.json", "local throughput measurements", "profile"),
    ("BC_CROWN_ENGINE_MAP_TESTS.py", "repeatable Crown map and bounded query tests", "test_harness"),
    ("BC_CROWN_MAP_QUERY_VALIDATION.json", "frozen bounded query/whole-map validation summary", "validation_summary"),
    ("BC_REGRESSION_SUMMARY.json", "individual-suite regression status and authority boundaries", "regression_summary"),
    ("BC_COLD_RELEASE_TESTS.py", "isolated exact-source release test runner", "test_harness"),
    ("BC_COLD_RELEASE_TEST_MATRIX.json", "frozen exact-source test matrix; does not claim unrun suites", "validation_summary"),
    ("BC_COLD_SCOPE_OVERVIEW.md", "cold release scope, limits, and next warm route", "scope_report"),
    ("BC_CROWN_CONTINUATION_COLD_RELEASE.md", "short route into the current cold snapshot and complete Crown map", "continuation_route"),
    ("BC_CROWN_CONTINUATION_COLD_RELEASE.json", "machine route selector and direct artifact pointers", "continuation_index"),
    ("tests/BC_HARMONIC_FRACTAL_REGRESSION_TESTS.py", "current-source harmonic/fractal regression", "test_harness"),
    ("tests/BC_LAZY_ROM_TESTS.py", "current-source optional historical ROM regression", "test_harness"),
    ("tests/BC_SEGMENTED_BUNDLE_TESTS.py", "current-source segmented shared-context bundle regression", "test_harness"),
    ("tests/BC_SHARED_CONTEXT_HALLWAY_TESTS.py", "current-source shared-context and hallway regression", "test_harness"),
    ("tests/test_self_map.py", "current-source engine self-map regression", "test_harness"),
    ("tests/test_relation_map.py", "current-source relation-map regression", "test_harness"),
    ("tests/test_fractal_work_locks.py", "current-source depth/aperture lock regression", "test_harness"),
    ("tests/test_transition_stage.py", "current-source transition/collision stage regression", "test_harness"),
    ("tests/test_cross_fractal_onehot.py", "current-source cross-fractal one-hot scaling regression", "test_harness"),
    ("tests/test_cog64_batch.py", "current-source exhaustive finite COG64 projection regression", "test_harness"),
    ("actual_data/current_source_release_tests/BC_CROWN_ENGINE_MAP_TEST_SUMMARY.json", "current-source Crown map/query test summary; excludes self-referential map digest", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_CROSS_FRACTAL_BATCH_TESTS.json", "current-source bounded cross-fractal batch checks", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_CROSS_FRACTAL_BATCH_EVIDENCE.json", "current-source complete batch transitions and witnesses", "actual_data"),
    ("actual_data/current_source_release_tests/BC_HARMONIC_FRACTAL_REGRESSION_RESULTS.json", "current-source harmonic/fractal regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_LAZY_ROM_TESTS.json", "current-source optional-ROM regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_SEGMENTED_BUNDLE_TESTS.json", "current-source segmented evidence bundle regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_SHARED_CONTEXT_HALLWAY_TESTS.json", "current-source shared-context and hallway regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_ENGINE_SELF_MAP_TESTS.json", "current-source engine self-map regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_ENGINE_SELF_MAP.json", "current-source whole-engine source/glyph self-map", "actual_data"),
    ("actual_data/current_source_release_tests/BC_ADDRESS_RELATION_MAP_TESTS.json", "current-source address relation-map regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_ADDRESS_RELATION_MAP.json", "current-source relation map with typed address and evidence links", "actual_data"),
    ("actual_data/current_source_release_tests/BC_FRACTAL_WORK_LOCK_TESTS.json", "current-source depth/aperture work-lock regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_FRACTAL_WORK_LOCK_EVIDENCE.json", "current-source locked cone and collision/frontier evidence", "actual_data"),
    ("actual_data/current_source_release_tests/BC_TRANSITION_STAGING_TESTS.json", "current-source transition and collision-stage regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_TRANSITION_STAGING_EVIDENCE.json", "current-source transition order, sphere collision and aperture evidence", "actual_data"),
    ("actual_data/current_source_release_tests/BC_CROSS_FRACTAL_ONEHOT_TESTS.json", "current-source cross-fractal one-hot scaling regression receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_CROSS_FRACTAL_ONEHOT_EVIDENCE.json", "current-source one-hot frame comparison and scaled-step witnesses", "actual_data"),
    ("actual_data/current_source_release_tests/BC_COG64_BATCH_TESTS.json", "current-source exhaustive finite COG64 projection receipt", "validation_summary"),
    ("actual_data/current_source_release_tests/BC_COG64_SPACE_PROJECTION.json", "current-source full 129024-state projection and page receipts", "actual_data"),
    ("actual_data/current_source_release_tests/BC_COG64_BATCH_DATA.json", "current-source COG64 batch input/output witnesses", "actual_data"),
    ("BC_LEGACY_STATIC_ROM.zlib", "optional checksum-verified historical inventory", "optional_rom"),
)

@dataclass(frozen=True)
class CrownEngineMap:
    """Addressable map of the running Python engine and its preserved route history."""
    schema: str
    map_address: str
    payload_json: str

    def as_dict(self) -> dict[str, Any]:
        body = json.loads(self.payload_json)
        body["map_address"] = self.map_address
        return body


_COMPOUND_CLASS_KIND["CrownEngineMap"] = "crown_engine_map"


def _crown_route_key(kind: str, key: str) -> str:
    return _sha256_text(_canonical_json({"schema":"BC-CROWN-ROUTE-NODE-1", "kind":kind, "key":key}))[:24]


def _crown_link(links: list[dict[str, Any]], source: str, target: str, relation: str,
                evidence: str = "runtime_map", details: Mapping[str, Any] | None = None) -> None:
    if not source or not target or source == target:
        return
    body = {"schema":"BC-CROWN-ENGINE-LINK-1", "source_route_id":source,
            "target_route_id":target, "relation":relation, "evidence":evidence,
            "details":dict(details or {})}
    body["link_id"] = _sha256_text(_canonical_json(body))[:24]
    links.append(body)


def _crown_source_inventory(source_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[str]]]:
    tree = ast.parse(source_text, filename=pathlib.Path(__file__).name, mode="exec")
    symbols: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    module_statements: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            continue
        segment=ast.get_source_segment(source_text,node) or ""
        stored_names=sorted({n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store)})
        module_statements.append({"statement_kind":type(node).__name__,
            "line_start":getattr(node,"lineno",1),"line_end":getattr(node,"end_lineno",getattr(node,"lineno",1)),
            "bound_names":stored_names,"span_sha256":_sha256_text(segment),
            "summary":(segment.strip().splitlines()[0][:96] if segment.strip() else type(node).__name__)})
    scope: list[tuple[str, str]] = []
    class_stack: list[str] = []
    function_stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            qualified = ".".join([*class_stack, *function_stack, node.name])
            symbols.append({"qualified_name":qualified, "short_name":node.name, "symbol_kind":"class",
                            "line_start":node.lineno, "line_end":getattr(node,"end_lineno",node.lineno)})
            class_stack.append(node.name)
            self.generic_visit(node)
            class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            qualified = ".".join([*class_stack, *function_stack, node.name])
            symbols.append({"qualified_name":qualified, "short_name":node.name, "symbol_kind":"function",
                            "line_start":node.lineno, "line_end":getattr(node,"end_lineno",node.lineno)})
            function_stack.append(node.name)
            self.generic_visit(node)
            function_stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                short = node.func.id
            elif isinstance(node.func, ast.Attribute):
                short = node.func.attr
            else:
                short = "<dynamic-call>"
            caller = ".".join([*class_stack, *function_stack]) or "<module>"
            calls.append({"caller":caller, "short_target":short, "line":getattr(node,"lineno",0)})
            self.generic_visit(node)

    Visitor().visit(tree)
    by_short: dict[str, list[str]] = {}
    for row in symbols:
        by_short.setdefault(row["short_name"], []).append(row["qualified_name"])
    return symbols, calls, by_short, module_statements


def _crown_artifact_row(relative_path: str, label: str, artifact_kind: str, root: pathlib.Path) -> dict[str, Any]:
    path = pathlib.PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("crown_artifact_path_must_be_relative_and_confined")
    full = (root / pathlib.Path(*path.parts)).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("crown_artifact_path_escapes_engine_root") from exc
    base = {"relative_path":path.as_posix(), "label":label, "artifact_kind":artifact_kind,
            "available":False, "bytes":0, "sha256":None, "status":"missing_artifact"}
    try:
        data = full.read_bytes()
    except OSError:
        return base
    base.update({"available":True, "bytes":len(data), "sha256":hashlib.sha256(data).hexdigest(),
                 "status":"available"})
    return base


def crown_continuation_entry(source_sha256: str, source_bytes: int = 0) -> dict[str, Any]:
    """Small welcome fold pointing into the full map; never substitutes for that map."""
    current_route = "BC-CROWN-ROUTE-" + str(source_sha256)[:16]
    return {"schema":"BC-CROWN-ENTRY-1", "route_id":current_route,
        "parent_route_id":_CROWN_PREVIOUS_ROUTE_ID, "map_operation":"BC.CROWN.MAP",
        "open_routes_operation":"BC.CROWN.OPEN.BATCH", "query_routes_operation":"BC.CROWN.QUERY",
        "open_artifact_operation":"BC.CROWN.ARTIFACT.OPEN",
        "source_sha256":source_sha256, "source_bytes":source_bytes,
        "map_is_generated_inside_python_engine":True, "covers_complete_runtime_source_and_registered_surface":True,
        "preserves_prior_route_history":True, "preserved_prior_route_count":len(_CROWN_ROUTE_HISTORY_SEED),
        "entry_is_retrieval_pointer_not_archive":True,
        "history_routes":[row["route_id"] for row in _CROWN_ROUTE_HISTORY_SEED],
        "full_map_output":"BC_CROWN_ENGINE_MAP.json", "external_continuation_index":"BC_CROWN_CONTINUATION_COLD_RELEASE.json",
        "current_scope":"Crown whole-engine route query and append-preserving history"}


def build_crown_engine_map(scope: str = _CROWN_CURRENT_SCOPE) -> CrownEngineMap:
    """Build the full navigation graph from the live source, registry, glyph catalogue and preserved route lineage."""
    if not isinstance(scope, str) or not scope.strip() or len(scope) > 240:
        raise ValueError("crown_scope_must_be_nonempty_and_bounded")
    root = pathlib.Path(__file__).resolve().parent
    source_path = pathlib.Path(__file__).resolve()
    source_bytes = source_path.read_bytes()
    source_text = source_bytes.decode("utf-8")
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    symbols, calls, by_short, module_statements = _crown_source_inventory(source_text)
    routes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    route_by_key: dict[tuple[str, str], str] = {}
    route_by_id: dict[str, dict[str, Any]] = {}

    def add(kind: str, stable_key: str, label: str, **fields: Any) -> str:
        rid = _crown_route_key(kind, stable_key)
        existing = route_by_id.get(rid)
        if existing is not None:
            if existing.get("kind") != kind or existing.get("target_key") != stable_key:
                raise ValueError("crown_route_id_collision")
            return rid
        row = {"route_id":rid, "kind":kind, "target_key":stable_key, "label":label,
               "openable":True, **fields}
        routes.append(row); route_by_id[rid] = row; route_by_key[(kind,stable_key)] = rid
        return rid

    engine_root_id = "BC-CROWN-ENGINE-ROOT"
    root_row = {"route_id":engine_root_id, "kind":"engine_root", "target_key":ENGINE_IDENTITY,
        "label":"Backlit Canopy — whole executable engine map", "openable":True,
        "source_sha256":source_sha, "source_bytes":len(source_bytes), "source_executed":False,
        "history_preserved":True, "current_route_selector":"active"}
    routes.append(root_row); route_by_id[engine_root_id] = root_row
    source_r = add("python_source", source_path.name, "Current executable Python source",
        sha256=source_sha, bytes=len(source_bytes), source_executed=False,
        source_read_is_not_source_execution=True, line_count=source_text.count("\n")+1)
    _crown_link(links, engine_root_id, source_r, "opens_complete_source")

    symbol_routes: dict[str, str] = {}
    for row in symbols:
        q = row["qualified_name"]
        sr = add("python_symbol", q, q, source_path=source_path.name,
            source_sha256=source_sha, line_start=row["line_start"], line_end=row["line_end"],
            symbol_kind=row["symbol_kind"], short_name=row["short_name"],
            source_executed=False, payload_ref={"artifact_route_id":source_r,"line_start":row["line_start"],"line_end":row["line_end"]})
        symbol_routes[q] = sr
        _crown_link(links, source_r, sr, "defines_symbol", details={"line_start":row["line_start"],"line_end":row["line_end"]})
    module_statement_routes=[]
    for row in module_statements:
        stable_key=f"{row['line_start']}:{row['line_end']}:{row['statement_kind']}:{row['span_sha256']}"
        label=("Top-level binding: "+", ".join(row["bound_names"][:6])) if row["bound_names"] else             f"Top-level {row['statement_kind']} @ {row['line_start']}"
        mr=add("python_statement",stable_key,label,source_path=source_path.name,source_sha256=source_sha,
            line_start=row["line_start"],line_end=row["line_end"],statement_kind=row["statement_kind"],
            bound_names=row["bound_names"],span_sha256=row["span_sha256"],summary=row["summary"],
            source_executed=False,payload_ref={"artifact_route_id":source_r,"line_start":row["line_start"],"line_end":row["line_end"]})
        module_statement_routes.append((row,mr))
        _crown_link(links,source_r,mr,"contains_module_level_data_or_statement",
            details={"line_start":row["line_start"],"line_end":row["line_end"],"statement_kind":row["statement_kind"]})
    source_symbol_edges = 0
    ambiguous_calls: dict[str, list[dict[str, Any]]] = {}
    external_counts: dict[str, int] = {}
    for call in calls:
        caller = call["caller"]; short = call["short_target"]
        owner_candidates = []
        scope_parts = caller.split(".") if caller != "<module>" else []
        for i in range(len(scope_parts), 0, -1):
            candidate = ".".join([*scope_parts[:i], short])
            if candidate in symbol_routes:
                owner_candidates = [candidate]; break
        if not owner_candidates:
            all_candidates = by_short.get(short, [])
            if len(all_candidates) == 1:
                owner_candidates = list(all_candidates)
            elif len(all_candidates) > 1:
                ambiguous_calls.setdefault(caller, []).append({"short_target":short,"line":call["line"],
                    "candidate_count":len(all_candidates),"candidates":sorted(all_candidates)[:8]})
        if caller in symbol_routes and len(owner_candidates) == 1:
            _crown_link(links, symbol_routes[caller], symbol_routes[owner_candidates[0]], "calls_internal_symbol",
                details={"line":call["line"],"resolved_by":"qualified_scope_or_unique_short_name"})
            source_symbol_edges += 1
        else:
            external_counts[caller] = external_counts.get(caller,0) + 1
        if caller == "<module>" and len(owner_candidates)==1:
            matches=[mr for row,mr in module_statement_routes if row["line_start"] <= call["line"] <= row["line_end"]]
            if len(matches)==1 and owner_candidates[0] in symbol_routes:
                _crown_link(links,matches[0],symbol_routes[owner_candidates[0]],"top_level_statement_calls_symbol",
                    details={"line":call["line"],"resolution":"unique_symbol"})
    unresolved_route = add("source_scan_residuals", "source-call-resolution", "Unresolved/ambiguous source call sites",
        ambiguous_owner_count=len(ambiguous_calls), ambiguous_site_count=sum(len(v) for v in ambiguous_calls.values()),
        external_or_unresolved_site_count=sum(external_counts.values()),
        examples={k:v[:8] for k,v in sorted(ambiguous_calls.items())[:64]},
        claim_boundary="static call resolution is navigation evidence, not runtime call certification")
    _crown_link(links, engine_root_id, unresolved_route, "retains_source_resolution_residuals")

    operation_routes: dict[str, str] = {}
    for op_name in REGISTRY.names():
        op = REGISTRY.resolve(op_name)
        orid = add("registered_operation", op_name, op_name, effect_scope=op.effect,
            executor_name=op_name, operation_identity=_sha256_text(_canonical_json({"name":op_name,"effect":op.effect}))[:24])
        operation_routes[op_name] = orid
        _crown_link(links, engine_root_id, orid, "contains_registered_operation")
        candidates = by_short.get(op_name, [])
        if len(candidates) == 1:
            _crown_link(links, orid, symbol_routes[candidates[0]], "implemented_by_source_symbol",
                details={"resolution":"unique_qualified_symbol"})
        elif candidates:
            _crown_link(links, orid, unresolved_route, "implementation_symbol_ambiguous",
                details={"candidate_symbols":sorted(candidates)[:8]})
    glyph_routes: dict[str, str] = {}
    subsystem_routes: dict[str, str] = {}
    glyph_rows = list(GLYPH_CATALOG.describe())
    for spec in glyph_rows:
        name = spec["name"]
        parts = name.split(".")
        group = ".".join(parts[:2]) if len(parts) >= 2 else name
        if group not in subsystem_routes:
            subsystem_routes[group] = add("subsystem", group, group + " subsystem",
                member_count=0, claim_boundary="navigation grouping only; no new behaviour is inferred")
            _crown_link(links, engine_root_id, subsystem_routes[group], "contains_subsystem")
        gr = add("glyph", name, name, glyph_address=spec["address"], executor_name=spec["executor"],
            required_args=spec["required_args"], optional_args=spec["optional_args"], arg_types=spec["arg_types"],
            effect_scope=spec["effect_scope"], witness_contract=spec["witness_contract"],
            claim_boundary=spec.get("claim_boundary","typed execution is not semantic or physical certification"))
        glyph_routes[name] = gr
        subsystem_routes[group]
        _crown_link(links, subsystem_routes[group], gr, "indexes_glyph_control_route")
        if spec["executor"] in operation_routes:
            _crown_link(links, gr, operation_routes[spec["executor"]], "routes_to_registered_executor")
        else:
            _crown_link(links, gr, unresolved_route, "executor_missing_from_registry")
        candidates = by_short.get(spec["executor"], [])
        if len(candidates) == 1:
            _crown_link(links, gr, symbol_routes[candidates[0]], "opens_executor_source")
    for group, rid in subsystem_routes.items():
        route_by_id[rid]["member_count"] = sum(1 for spec in glyph_rows if ".".join(spec["name"].split(".")[:2]) == group)

    # Historical continuation routes are immutable map nodes. Adding the current
    # route never erases or overwrites a previously addressed development spread.
    history_ids = {r["route_id"] for r in _CROWN_ROUTE_HISTORY_SEED}
    for row in _CROWN_ROUTE_HISTORY_SEED:
        r = {"route_id":row["route_id"],"kind":"historical_continuation","target_key":row["route_id"],
             "label":row["label"],"openable":True,"status":"historical_route_preserved",
             "source_sha256":row["source_sha256"],"scope":row["scope"],
             "parent_route_id":row["parent_route_id"],"artifact_paths":[row["route_json"],row["route_md"],row["workpack"]]+
                [row[k] for k in ("map_snapshot","map_reopen_receipt","map_test_receipt") if row.get(k)],
             "route_record_json":row["route_json"],"route_record_md":row["route_md"],"workpack_path":row["workpack"],
             "map_snapshot_path":row.get("map_snapshot"),"map_reopen_receipt_path":row.get("map_reopen_receipt"),
             "map_test_receipt_path":row.get("map_test_receipt")}
        routes.append(r); route_by_id[r["route_id"]]=r
        if row["parent_route_id"] in history_ids:
            _crown_link(links,row["parent_route_id"],row["route_id"],"continues_prior_work",evidence="preserved_continuation_lineage")
        else:
            _crown_link(links,engine_root_id,row["route_id"],"retains_earlier_route")
    current_route_id = "BC-CROWN-ROUTE-" + source_sha[:16]
    current_row = {"route_id":current_route_id,"kind":"current_continuation","target_key":current_route_id,
        "label":"Current warm scope — in-engine Crown map integration","openable":True,"status":"current_warm",
        "source_sha256":source_sha,"scope":scope,"parent_route_id":_CROWN_PREVIOUS_ROUTE_ID,
        "prior_route_count":len(_CROWN_ROUTE_HISTORY_SEED),"engine_root_route_id":engine_root_id,
        "current_artifact_paths":[row[0] for row in _CROWN_CURRENT_ARTIFACT_PATHS],
        "history_preserved":True,"entry_is_locator_not_archive":True}
    routes.append(current_row); route_by_id[current_route_id]=current_row
    _crown_link(links,engine_root_id,current_route_id,"selects_current_continuation")
    if _CROWN_PREVIOUS_ROUTE_ID in route_by_id:
        _crown_link(links,_CROWN_PREVIOUS_ROUTE_ID,current_route_id,"continues_from_previous_warm_route")
    else:
        _crown_link(links,engine_root_id,current_route_id,"parent_route_residual_missing_from_history_seed")

    artifact_entries: dict[str, str] = {}
    for path, label, kind in _CROWN_CURRENT_ARTIFACT_PATHS:
        row = _crown_artifact_row(path,label,kind,root)
        artifact_fields={k:v for k,v in row.items() if k!="label"}
        ar = add("artifact", path, label, **artifact_fields, locator_only=True,
            content_is_separate_from_route_map=True)
        artifact_entries[path] = ar
        _crown_link(links,current_route_id,ar,"opens_current_work_artifact")
    for hist in _CROWN_ROUTE_HISTORY_SEED:
        historical_artifacts = [(hist["route_json"],hist["label"]+" route index","historical_route_json"),
                                (hist["route_md"],hist["label"]+" readable route","historical_route_record"),
                                (hist["workpack"],hist["label"]+" complete workpack","historical_workpack")]
        for key,label_suffix,kind in (("map_snapshot"," full map snapshot","historical_map_snapshot"),
                                      ("map_reopen_receipt"," map reopen receipt","historical_map_receipt"),
                                      ("map_test_receipt"," map test receipt","historical_map_test_receipt")):
            if hist.get(key): historical_artifacts.append((hist[key],hist["label"]+label_suffix,kind))
        for path,label,kind in historical_artifacts:
            if path not in artifact_entries:
                row = _crown_artifact_row(path,label,kind,root)
                artifact_fields={k:v for k,v in row.items() if k!="label"}
                ar = add("artifact",path,label,**artifact_fields,locator_only=True,content_is_separate_from_route_map=True)
                artifact_entries[path] = ar
            else:
                ar = artifact_entries[path]
            _crown_link(links,hist["route_id"],ar,"opens_preserved_historical_artifact")
    # Route map links are sorted to make rebuild and diff deterministic.
    links = sorted({row["link_id"]:row for row in links}.values(),key=lambda x:x["link_id"])
    routes = sorted(routes,key=lambda x:(x["kind"],x["route_id"]))
    body = {"schema":"BC-CROWN-ENGINE-MAP-1","engine":ENGINE_IDENTITY,
        "map_scope":"whole executable source, glyph/control surface, operation registry, subsystem routes and preserved continuation history",
        "current_scope":scope,"engine_root_route_id":engine_root_id,"current_route_id":current_route_id,
        "parent_route_id":_CROWN_PREVIOUS_ROUTE_ID,"source":{"relative_path":source_path.name,"sha256":source_sha,
            "bytes":len(source_bytes),"line_count":source_text.count("\n")+1,"source_executed":False},
        "coverage":{"python_symbol_count":len(symbols),"module_statement_count":len(module_statements),
            "module_statement_bound_names":sum(len(x["bound_names"]) for x in module_statements),
            "registered_operation_count":len(operation_routes),
            "registered_glyph_count":len(glyph_routes),"subsystem_count":len(subsystem_routes),
            "historical_route_count":len(_CROWN_ROUTE_HISTORY_SEED),"current_route_count":1,
            "artifact_route_count":len(artifact_entries),"resolved_internal_call_edges":source_symbol_edges,
            "ambiguous_call_owner_count":len(ambiguous_calls),"ambiguous_call_site_count":sum(len(v) for v in ambiguous_calls.values()),
            "unresolved_or_external_call_site_count":sum(external_counts.values())},
        "authority":{"source_write":False,"project_save":False,"engine_cold_commit":False,"glyph_admission":False,
            "source_parsed_not_executed":True},
        "route_policy":{"history_is_append_preserving":True,"current_entry_is_small_pointer":True,
            "map_is_generated_inside_python_engine":True,"payloads_are_opened_separately":True,
            "batch_max_items":64,"artifact_max_bytes_per_open":262144,
            "unknown_route_is_residual":True,"missing_artifact_is_explicit":True},
        "history_route_ids":[r["route_id"] for r in _CROWN_ROUTE_HISTORY_SEED],
        "routes":routes,"links":links}
    map_address = _sha256_text(_canonical_json(body))
    return CrownEngineMap("BC-CROWN-ENGINE-MAP-1",map_address,_canonical_json(body))


def reopen_crown_engine_map(crown_map: CrownEngineMap | Mapping[str, Any]) -> dict[str, Any]:
    try:
        if isinstance(crown_map,CrownEngineMap):
            obj=crown_map.as_dict()
        elif isinstance(crown_map,Mapping):
            obj=dict(crown_map)
        else:
            raise TypeError("crown_engine_map_required")
        body={k:v for k,v in obj.items() if k!="map_address"}
        actual=_sha256_text(_canonical_json(body))
        if actual != obj.get("map_address"):
            raise ValueError("crown_engine_map_content_address_mismatch")
        rebuilt=build_crown_engine_map(body.get("current_scope",_CROWN_CURRENT_SCOPE)).as_dict()
        passed=rebuilt==obj
        return {"schema":"BC-CROWN-ENGINE-MAP-REOPEN-1","pass":passed,
            "map_address":obj.get("map_address"),"rebuilt_map_address":rebuilt.get("map_address"),
            "source_sha256":body.get("source",{}).get("sha256"),"current_route_id":body.get("current_route_id"),
            "route_count":len(body.get("routes",[])),"link_count":len(body.get("links",[])),
            "history_preserved":passed and body.get("history_route_ids")==[r["route_id"] for r in _CROWN_ROUTE_HISTORY_SEED],
            "source_executed":False,"source_write":False,"project_save":False,"engine_cold_commit":False}
    except (TypeError,ValueError,KeyError,OSError,UnicodeError) as exc:
        return {"schema":"BC-CROWN-ENGINE-MAP-REOPEN-1","pass":False,
            "reason":f"{type(exc).__name__}:{exc}","source_executed":False}


def open_crown_route_batch(crown_map: CrownEngineMap | Mapping[str, Any], route_ids: Sequence[str],
                           start_index: int = 0, max_items: int = 32,
                           max_output_bytes: int = 262144) -> dict[str, Any]:
    """Open a bounded group of engine routes while leaving all unselected routes untouched."""
    if isinstance(crown_map,CrownEngineMap):
        obj=crown_map.as_dict()
    elif isinstance(crown_map,Mapping):
        obj=dict(crown_map)
    else:
        raise TypeError("crown_engine_map_required")
    body={k:v for k,v in obj.items() if k!="map_address"}
    if _sha256_text(_canonical_json(body)) != obj.get("map_address"):
        raise ValueError("crown_engine_map_content_address_mismatch")
    if not isinstance(route_ids,(tuple,list)) or len(route_ids)>256 or any(not isinstance(x,str) for x in route_ids):
        raise ValueError("crown_route_ids_must_be_bounded_sequence")
    if type(start_index) is not int or not 0<=start_index<=len(route_ids):
        raise ValueError("crown_route_start_index_invalid")
    if type(max_items) is not int or not 1<=max_items<=64:
        raise ValueError("crown_route_batch_max_items_must_be_1_to_64")
    if type(max_output_bytes) is not int or not 1024<=max_output_bytes<=262144:
        raise ValueError("crown_route_output_budget_must_be_1k_to_256k")
    by_id={r["route_id"]:r for r in body.get("routes",[])}
    links=body.get("links",[]); adjacency: dict[str,list[dict[str,Any]]] = {}
    for edge in links:
        adjacency.setdefault(edge["source_route_id"],[]).append(edge)
        adjacency.setdefault(edge["target_route_id"],[]).append(edge)
    out=[]; next_index=start_index
    stop=min(len(route_ids),start_index+max_items)
    for i in range(start_index,stop):
        rid=route_ids[i]
        row=by_id.get(rid)
        if row is None:
            row={"route_id":rid,"kind":"unresolved_route","openable":False,
                 "status":"route_id_not_found","residual":"unknown route identifiers are not inferred"}
        record={"route":row,"links":adjacency.get(rid,[])}
        trial=out+[record]
        if len(_canonical_json(trial).encode("utf-8"))>max_output_bytes:
            if not out:
                return {"schema":"BC-CROWN-ROUTE-BATCH-OPEN-1","pass":False,
                    "reason":"next_route_exceeds_output_budget","blocked_route_id":rid,
                    "map_address":obj.get("map_address"),"route_ids":list(route_ids),"start_index":start_index,
                    "next_index":start_index,"opened_count":0,"records":[],"frontiers_traversed":False,
                    "source_executed":False,"continuation_address_is_pointer_only":True}
            break
        out=trial;next_index=i+1
    return {"schema":"BC-CROWN-ROUTE-BATCH-OPEN-1","pass":True,
        "map_address":obj.get("map_address"),"route_ids":list(route_ids),"start_index":start_index,
        "next_index":next_index,"complete":next_index>=len(route_ids),"opened_count":len(out),
        "records":out,"frontiers_traversed":False,"source_executed":False,
        "continuation_address_is_pointer_only":True}


def query_crown_engine_routes(crown_map: CrownEngineMap | Mapping[str, Any], query: str,
                              kinds: Sequence[str] = (), start_index: int = 0,
                              max_items: int = 24, max_output_bytes: int = 65536,
                              include_links: bool = True) -> dict[str, Any]:
    """Search the existing whole-engine map and return bounded route records, never a new map."""
    if isinstance(crown_map,CrownEngineMap): obj=crown_map.as_dict()
    elif isinstance(crown_map,Mapping): obj=dict(crown_map)
    else: raise TypeError("crown_engine_map_required")
    body={k:v for k,v in obj.items() if k!="map_address"}
    if _sha256_text(_canonical_json(body)) != obj.get("map_address"):
        raise ValueError("crown_engine_map_content_address_mismatch")
    if not isinstance(query,str) or not query.strip() or len(query)>180:
        raise ValueError("crown_query_must_be_nonempty_and_at_most_180_chars")
    if not isinstance(kinds,(tuple,list)) or len(kinds)>16 or any(not isinstance(x,str) or not x or len(x)>48 for x in kinds):
        raise ValueError("crown_query_kinds_must_be_a_bounded_string_sequence")
    if type(start_index) is not int or start_index<0: raise ValueError("crown_query_start_index_invalid")
    if type(max_items) is not int or not 1<=max_items<=64: raise ValueError("crown_query_max_items_must_be_1_to_64")
    if type(max_output_bytes) is not int or not 1024<=max_output_bytes<=262144:
        raise ValueError("crown_query_output_budget_must_be_1k_to_256k")
    if type(include_links) is not bool: raise ValueError("crown_query_include_links_must_be_boolean")
    tokens=[t for t in query.casefold().split() if t]
    kind_set={k.casefold() for k in kinds}
    searchable_fields=("route_id","kind","target_key","label","qualified_name","short_name","executor_name",
        "effect_scope","witness_contract","scope","status","artifact_kind","relative_path","source_path",
        "symbol_kind","parent_route_id","subsystem","claim_boundary","residual")
    matches=[]
    for row in body.get("routes",[]):
        if kind_set and str(row.get("kind","")).casefold() not in kind_set: continue
        text_value=" ".join(str(row.get(k,"")) for k in searchable_fields).casefold()
        if all(token in text_value for token in tokens): matches.append(row)
    # Index adjacency once; each route query opens only the links of emitted rows.
    adjacency: dict[str,list[dict[str,Any]]] = {}
    if include_links:
        for edge in body.get("links",[]):
            adjacency.setdefault(edge["source_route_id"],[]).append(edge)
            adjacency.setdefault(edge["target_route_id"],[]).append(edge)
    out=[]; next_index=start_index; end=min(len(matches),start_index+max_items)
    selected_fields=("route_id","kind","target_key","label","openable","status","parent_route_id","source_sha256",
        "relative_path","sha256","bytes","effect_scope","executor_name","required_args","optional_args","arg_types",
        "witness_contract","scope","symbol_kind","line_start","line_end","artifact_kind","available","subsystem","member_count",
        "claim_boundary","residual","map_snapshot_path","map_reopen_receipt_path","map_test_receipt_path")
    for i in range(start_index,end):
        row=matches[i]
        compact={k:row[k] for k in selected_fields if k in row}
        record={"route":compact,"links":adjacency.get(row["route_id"],[]) if include_links else []}
        trial=out+[record]
        if len(_canonical_json(trial).encode("utf-8"))>max_output_bytes:
            if not out:
                return {"schema":"BC-CROWN-QUERY-1","pass":False,"reason":"next_route_exceeds_output_budget",
                    "blocked_route_id":row.get("route_id"),"map_address":obj.get("map_address"),
                    "source_sha256":body.get("source",{}).get("sha256"),"query":query,"kinds":list(kinds),
                    "total_matches":len(matches),"start_index":start_index,"next_index":start_index,
                    "opened_count":0,"complete":False,"records":[],"output_budget_bytes":max_output_bytes,
                    "map_rebuilt":False,"frontiers_traversed":False,"continuation_address_is_pointer_only":True}
            break
        out=trial; next_index=i+1
    return {"schema":"BC-CROWN-QUERY-1","pass":True,"map_address":obj.get("map_address"),
        "source_sha256":body.get("source",{}).get("sha256"),"query":query,"kinds":list(kinds),
        "total_matches":len(matches),"start_index":start_index,"next_index":next_index,
        "opened_count":len(out),"complete":next_index>=len(matches),"records":out,
        "output_budget_bytes":max_output_bytes,"map_rebuilt":False,"frontiers_traversed":False,
        "continuation_address_is_pointer_only":True}


def open_crown_route_artifact(crown_map: CrownEngineMap | Mapping[str, Any], route_id: str,
                              start_offset: int = 0, max_bytes: int = 65536) -> dict[str, Any]:
    """Open actual artifact bytes or a Python source-symbol span by bounded range."""
    if isinstance(crown_map,CrownEngineMap): obj=crown_map.as_dict()
    elif isinstance(crown_map,Mapping): obj=dict(crown_map)
    else: raise TypeError("crown_engine_map_required")
    body={k:v for k,v in obj.items() if k!="map_address"}
    if _sha256_text(_canonical_json(body)) != obj.get("map_address"):
        raise ValueError("crown_engine_map_content_address_mismatch")
    if type(start_offset) is not int or start_offset<0: raise ValueError("artifact_start_offset_invalid")
    if type(max_bytes) is not int or not 1<=max_bytes<=262144: raise ValueError("artifact_open_max_bytes_must_be_1_to_262144")
    route=next((r for r in body.get("routes",[]) if r.get("route_id")==route_id),None)
    if route is None: return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":False,"reason":"route_id_not_found","route_id":route_id}
    root=pathlib.Path(__file__).resolve().parent
    if route.get("kind") in {"python_symbol","python_statement"}:
        path=root/route.get("source_path", "")
        expected=route.get("source_sha256")
        try: raw=path.read_bytes()
        except OSError as exc: return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":False,"reason":"source_artifact_unavailable:"+str(exc)}
        got=hashlib.sha256(raw).hexdigest()
        if got!=expected or got!=body.get("source",{}).get("sha256"):
            return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":False,"reason":"source_symbol_source_hash_mismatch","expected_sha256":expected,"actual_sha256":got}
        lines=raw.decode("utf-8").splitlines(keepends=True)
        first=route["line_start"]-1; last=route["line_end"]
        selected="".join(lines[first:last]).encode("utf-8")
        cut=selected[start_offset:start_offset+max_bytes]
        return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":True,"route_id":route_id,
            "kind":route.get("kind"),"qualified_name":route["target_key"],"statement_kind":route.get("statement_kind"),"source_sha256":got,
            "line_start":route["line_start"],"line_end":route["line_end"],"total_bytes":len(selected),
            "start_offset":start_offset,"returned_bytes":len(cut),"complete":start_offset+len(cut)>=len(selected),
            "encoding":"utf-8","content":cut.decode("utf-8",errors="replace"),"source_executed":False}
    if route.get("kind")!="artifact":
        return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":False,"reason":"route_does_not_target_openable_artifact_or_source_symbol","route_id":route_id}
    rel=route.get("relative_path")
    p=pathlib.PurePosixPath(rel or "")
    if p.is_absolute() or ".." in p.parts: raise ValueError("crown_artifact_path_must_be_relative_and_confined")
    path=(root/pathlib.Path(*p.parts)).resolve()
    try: path.relative_to(root.resolve())
    except ValueError as exc: raise ValueError("crown_artifact_path_escapes_engine_root") from exc
    try: raw=path.read_bytes()
    except OSError as exc: return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":False,
        "reason":"artifact_unavailable","relative_path":rel,"detail":type(exc).__name__}
    got=hashlib.sha256(raw).hexdigest()
    if got != route.get("sha256"):
        return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":False,"reason":"artifact_sha256_mismatch",
            "relative_path":rel,"expected_sha256":route.get("sha256"),"actual_sha256":got}
    cut=raw[start_offset:start_offset+max_bytes]
    try:
        content=cut.decode("utf-8")
        encoding="utf-8"
    except UnicodeDecodeError:
        content=base64.b64encode(cut).decode("ascii")
        encoding="base64"
    return {"schema":"BC-CROWN-ARTIFACT-OPEN-1","pass":True,"route_id":route_id,
        "relative_path":rel,"artifact_kind":route.get("artifact_kind"),"sha256":got,"total_bytes":len(raw),
        "start_offset":start_offset,"returned_bytes":len(cut),"complete":start_offset+len(cut)>=len(raw),
        "encoding":encoding,"content":content,"source_executed":False}


REGISTRY.register("build_crown_engine_map",build_crown_engine_map,"source_read")
REGISTRY.register("reopen_crown_engine_map",reopen_crown_engine_map,"source_read")
REGISTRY.register("open_crown_route_batch",open_crown_route_batch,"source_read")
REGISTRY.register("query_crown_engine_routes",query_crown_engine_routes,"source_read")
REGISTRY.register("open_crown_route_artifact",open_crown_route_artifact,"source_read")
for _crown_spec in (
    GlyphSpec.make("BC.CROWN.MAP","build_crown_engine_map",(),("scope",),{"scope":"string"},"source_read",
        "build the whole-engine navigation graph from Python symbols, registered operations, glyph routes, artifacts and preserved continuation history"),
    GlyphSpec.make("BC.CROWN.MAP.REOPEN","reopen_crown_engine_map",("crown_map",),(),{"crown_map":"crown_engine_map"},"source_read",
        "verify the complete Crown map content address and rebuild against the current source and route history"),
    GlyphSpec.make("BC.CROWN.OPEN.BATCH","open_crown_route_batch",("crown_map","route_ids"),("start_index","max_items","max_output_bytes"),
        {"crown_map":"crown_engine_map","route_ids":"glyph_reference_sequence","start_index":"nonnegative_integer","max_items":"positive_integer","max_output_bytes":"positive_integer"},"source_read",
        "open a bounded batch of route nodes and adjacent links; keep unselected routes unexpanded"),
    GlyphSpec.make("BC.CROWN.QUERY","query_crown_engine_routes",("crown_map","query"),("kinds","start_index","max_items","max_output_bytes","include_links"),
        {"crown_map":"crown_engine_map","query":"string","kinds":"glyph_reference_sequence","start_index":"nonnegative_integer",
         "max_items":"positive_integer","max_output_bytes":"positive_integer","include_links":"boolean"},"source_read",
        "query the whole-engine map by bounded terms and return only selected route nodes/links; do not rebuild or replace map/history"),
    GlyphSpec.make("BC.CROWN.ARTIFACT.OPEN","open_crown_route_artifact",("crown_map","route_id"),("start_offset","max_bytes"),
        {"crown_map":"crown_engine_map","route_id":"string","start_offset":"nonnegative_integer","max_bytes":"positive_integer"},"source_read",
        "open checksummed real artifact bytes or exact Python source-symbol spans by a bounded range"),
):
    GLYPH_CATALOG.register(_crown_spec)


def bc_boot(mode: str = "welcome", *, source_path: str | None = None, expected_source_sha256: str | None = None) -> dict[str, Any]:
    """Single cold-start entry; no imports of legacy engine, no source execution."""
    if mode not in {"welcome", "inspect", "capabilities", "migration"}:
        return {"schema": SCHEMA, "engine": ENGINE_IDENTITY, "pass": False, "status": "unknown_mode", "mode": mode}
    # The engine identity always describes this clean runtime. A requested
    # legacy source is a separate input address, never substituted as the
    # running engine source.
    current_path = pathlib.Path(__file__)
    read = None
    try:
        data = current_path.read_bytes()
        read = read_source_text(data.decode("utf-8"), str(current_path))
        exists = True
    except (OSError, UnicodeDecodeError) as exc:
        exists = False
        read = SourceReadReport("BC-SOURCE-READ-1", str(current_path), "", 0, False, False, (), 0, 0, 0,
                                (f"source_unavailable:{type(exc).__name__}:{exc}",))
    report = {
        "schema": SCHEMA,
        "engine": ENGINE_IDENTITY,
        "runtime_state": RUNTIME_STATE,
        "historical_rom": legacy_static_rom_status(),
        "mode": mode,
        "pass": bool(exists and read.syntax_pass and read.ast_pass),
        "source": {
            "path": str(current_path), "available": exists,
            "sha256": read.source_sha256, "bytes": read.bytes_read,
            "syntax_pass": read.syntax_pass, "ast_pass": read.ast_pass,
            "duplicate_definition_groups": len(read.duplicate_definition_groups),
            "source_executed": False,
        },
        "capabilities": {
            "exact_integer_circle": True,
            "four_90_step_pages": True,
            "eight_explicit_sphere_records": True,
            "recursive_address_payload": True,
            "local_fold_difference_witness": True,
            "ast_subscript_and_comprehension_reader": True,
            "single_canonical_registry": True,
            "addressable_clean_glyph_catalogue": True,
            "effect_scoped_authority": True,
            "typed_full_floor_address": True,
            "exact_360_circle_gray_boundary_transport": True,
            "typed_216_factor_and_physical_neighbors": True,
            "recursive_216_payload_operations": True,
            "full_address_difference_patch_and_replay": True,
            "exact_rational_turn_shell_promotion": True,
            "prime_harmonic_504_head_antipode_and_504x360_alignment": True,
            "prime_harmonic_is_part_of_authoritative_floor_address": True,
            "structural_fractal_prime_harmonic_center_composition": True,
            "prime_harmonic_head_and_prime_rpm_moduli_kept_distinct": True,
            "harmonic_fractal_center_winding_and_onehot_frame_reopen": True,
            "sphere504_exact_mixed_radix_8_9_7_carries": True,
            "prime_cog_rates_project_one_authoritative_whole_phase": True,
            "harmonic_fractal_step_reopens_full_after_address": True,
            "structuralizer_six_plane_exact_lift_and_reopen": True,
            "structuralizer_vm_zero_plane_address_binding_and_reopen": True,
            "structuralizer_zero_plane_two_of_three_difference_solve": True,
            "structuralizer_hallway_relative_relation_copy_and_reopen": True,
            "distinct_box216_cube216_apertures": True,
            "named_recursive_child_addresses": True,
            "depth_wave_state_cones": True,
            "depth_wave_cone_reopen_and_witness": True,
            "fractal_aperture_family_depth_locks": True,
            "aggregate_depth_wave_node_frontier_budgets": True,
            "frontier_travel_and_cross_cone_collision_audit": True,
            "lock_bound_batch_route_preflight": True,
            "collision_cone_prime_harmonic_aperture_fidelity": True,
            "sphere504_forward_backward_winding_alias_probe": True,
            "six_plane_prime_cog_octant_lift_checks": True,
            "sphere_head_winding_aliases_kept_distinct": True,
            "depth_wave_input_self_feed_structuralizer_crown_interfaces": True,
            "deterministic_self_feed_pattern_learning": True,
            "shared_context_event_bundle_delta_reconstruction": True,
            "shared_context_event_bundle_operation_replay": True,
            "shared_context_on_demand_full_address_materialization": True,
            "fractal_hallway_workload_predictor_cone": True,
            "workload_fit_is_candidate_ranking_not_probability": True,
            "repeatable_compound_case_learning": True,
            "negative_case_and_residual_retention": True,
            "portable_learning_ledger_export_import_reopen": True,
            "translation_invariant_learning_comparison": True,
            "integer_magnitude_normalized_learning_comparison": True,
            "six_plane_comparison_view_for_point_cases": True,
            "sparse_structural_name_control_index": True,
            "comparison_views_do_not_expand_learning_profile_proposals": True,
            "address_native_onehot_compactification_waves": True,
            "cross_fractal_onehot_fidelity_scaled_sphere_steps": True,
            "bounded_cross_fractal_onehot_batches": True,
            "exact_fractional_step_carry_across_batch_boundaries": True,
            "terminal_fractional_backlash_frame_local": True,
            "terminal_fractional_backlash_opens_one_bounded_aperture": True,
            "batch_reopen_recomputes_carry_and_step_witnesses": True,
            "addressed_wave_glyph_records": True,
            "cross_dimensional_wave_projection_residues": True,
            "global_fractal_to_center_count_known": False,
            "onehot_wave_match_map_separate_from_learning_profile": True,
            "automatic_glyph_learning_admission": False,
            "harmonic_fold_bound_to_named_child": True,
            "prime_rpm_exact_integer_lane_addresses": True,
            "prime_rpm_explicit_rate_dependency_cones": True,
            "prime_rpm_address_in_authoritative_full_address": True,
            "prime_rpm_transition_and_reopen_witness": True,
            "crown_precone_state_size_profile": True,
            "fibonacci_growth_budget_law": True,
            "factor_local_spiral_without_cartesian_materialisation": True,
            "spiral_growth_plan_exact_reopen": True,
            "crown_precone_holistic_operation_envelope": True,
            "crown_precone_budget_exact_reopen": True,
            "crown_multi_query_precone_orchestration": True,
            "crown_neighbour_stack_budgeted_orchestration": True,
            "harmonic64_exact_64bit_route_masks": True,
            "harmonic64_route_plan_parent_bound_reopen": True,
            "harmonic64_cost_aware_integer_search": True,
            "evidence_gated_fibonacci_lexical_doubling_crossover": True,
            "evidence_gated_spiral_crossover_selection": True,
            "canonical_command_reference_resolution": True,
            "legacy_command_behavior_static_profiles": True,
            "legacy_command_behavior_root_bound_reopen": True,
            "legacy_command_semantic_equivalence_proven": False,
            "historical_executor_key_source_index": True,
            "legacy_captured_alias_resolution_is_observational_only": True,
            "legacy_command_auto_fallback_dispatch": False,
            "historical_command_semantic_parity": False,
            "harmonic64_decoded_trit_semantics": False,
            "physical_harmonic64_router_calibration": False,
            "multi_query_identity_and_source_cone_preserved": True,
            "evidence_gated_spiral_crossover_selection": True,
            "static_legacy_source_migration_map": True,
            "read_only_engine_self_map_ast_catalogue_structuralizer_routes": True,
            "whole_engine_crown_route_map_in_python": True,
            "small_welcome_continuation_entry_preserves_map_history": True,
            "full_historical_glyph_catalogue_migrated": False,
            "prime_rpm_physical_calibration_migrated": False,
        },
        "registry": REGISTRY.names(),
        "clean_glyph_catalogue": {"count": len(GLYPH_CATALOG.names()), "names": list(GLYPH_CATALOG.names()),
                                   "definitions": list(GLYPH_CATALOG.describe())},
        "glyph_composition": COMPOUND_GLYPH_LIBRARY.summary(),
        "glyph_learning": glyph_learning_summary(),
        "structural_wave_glyphs": structural_wave_glyph_summary(),
        "harmonic_fractal": harmonic_fractal_summary(),
        "cross_fractal_onehot": cross_fractal_onehot_summary(),
        "sphere504_cog": {"radices":list(SPHERE504_RADICES),"rates":list(SPHERE504_COG_RATES),
            "carry_steps":"octant8 -> pair9 -> heptad7 -> whole sphere504",
            "modulo_role":"cyclic readout and independent cross-check; not the sole transition mechanism",
            "whole_phase_authoritative":True,"rpm_word_modulus_is_separate":True},
        "authority": {"source_write": False, "project_save": False, "engine_cold_commit": False,
                      "glyph_admission": False},
        "reader_findings": list(read.findings),
        "command_resolution": legacy_command_inventory_summary(),
        "command_behavior": legacy_command_behavior_summary(),
    }
    report["crown_continuation"] = crown_continuation_entry(read.source_sha256, read.bytes_read)
    if mode == "welcome":
        report["welcome"] = (
            "Backlit Canopy opens addressed structure, executes typed resident mechanics, "
            "and returns differences with independently reported closure and replay. "
            "This warm candidate adds typed, content-addressed compound-glyph proposals with short selectors, graph provenance, checked output contracts, and replayable receipts. "
            "Candidates and admitted revisions remain separate; deterministic learning records source-bound cases, repeated motifs, negative evidence, and portable data without automatic admission. "
            "A sparse comparison/name index pairs exact, zero-plane, unit-magnitude, and six-plane views without multiplying profile rows or proposals. "
            "Address-native one-hot compactification opens the actual box/page/cube frames and emits reusable wave glyph records with 1D/2D/3D projections; omitted dimensions, shell frontiers and source addresses remain residues rather than being erased. "
            "Harmonic-fractal center frames compose an actual sparse one-hot frame with the 504-head reference and optional prime-RPM lanes; cyclic residues, unwrapped winding, scale-family identity and unresolved lane/frontier residues remain separately inspectable. "
            "Sphere-504 movement uses exact octant8 -> pair9 -> heptad7 factor carries; the 3/5/7 cog lenses are projections of one unwrapped whole phase, with factor cycles checked against the direct 504 transition and retained winding. "
            "Shared-context event bundles store the root, recursive cone and named frames once; each transition retains content-addressed operation inputs, exact deltas, witness identities and residual links, and reopening reconstructs full intermediate addresses by replay. "
            "A fractal-hallway predictor ranks current glyph contracts against potential workload requirements and binds the ranking to an opened recursive path; missing input types, unavailable depths and omitted dimensions remain residuals, not probabilities or admissions. "
            "The Crown route is a small selector into the whole engine map generated in Python; bounded query/open operations expose selected source, glyph, route, history, and evidence edges without replacing the map or its prior route nodes. Source is parsed for navigation, never executed. "
            "A read-only engine self-map links parsed Python symbols, runtime glyph executors, the caller-owned learning ledger, the in-memory compound library, wave comparison maps, and only those recursive hallways actually opened; source is never executed. "
            "Fractal work locks bind the request to contiguous resolved levels, distinct box/cube aperture identities, prime-stage and transition-family counts, and aggregate node/frontier/transition budgets before the cone opens. "
            "Cross-fractal one-hot scaling compares only actually opened same-family recursive frames, reduces matched typed one-hot words to an exact integer fidelity ratio, scales sphere504 ticks only when the result is integral, and retains six-plane, prime-lane, and unopened-frontier residuals. "
            "Traveling front edges, convergent frontier targets, cross-cone coordinate overlaps and sphere head/winding aliases are auditable evidence; frontiers are not traversed automatically, projected coincidences do not merge address identities, and global center depth remains unknown. "
            "Locked relation batches preflight each route against the reopened root's family/depth lock before hydration. Collision staging compares forward-then-backward and backward-then-forward sphere504 paths, shares each source's 3/5/7 aperture and six signed-permutation structuralizer sweep across overlapping candidates, and only opens an adjacent shell under a separate fitting lock."
        )
    report["migration_matrix"] = clean_migration_matrix()
    if mode == "inspect" and source_path:
        try:
            inspected_bytes = pathlib.Path(source_path).read_bytes()
            inspected = read_source_text(inspected_bytes.decode("utf-8"), str(pathlib.Path(source_path)))
            report["inspected_source"] = {"path": str(pathlib.Path(source_path).resolve()),
                "sha256": inspected.source_sha256, "bytes": inspected.bytes_read,
                "syntax_pass": inspected.syntax_pass, "ast_pass": inspected.ast_pass,
                "source_executed": False, "findings": list(inspected.findings)}
            if not (inspected.syntax_pass and inspected.ast_pass): report["pass"] = False
        except Exception as exc:
            report["pass"] = False
            report["inspected_source"] = {"pass":False,"reason":f"{type(exc).__name__}:{exc}"}
    if mode == "migration" and not source_path:
        report["pass"] = False
        report["status"] = "legacy_source_path_required"
        report["legacy_migration_inventory"] = {"pass": False, "reason": "explicit_source_path_required_for_migration_mode"}
    elif mode == "migration" and source_path:
        try:
            report["legacy_migration_inventory"] = inspect_legacy_source(source_path, expected_source_sha256)
            if report["legacy_migration_inventory"].get("pass") is not True:
                report["pass"] = False
        except Exception as exc:
            report["pass"] = False
            report["legacy_migration_inventory"] = {"pass": False, "reason": f"{type(exc).__name__}:{exc}"}
    return report


def bc_fast_summary(mode: str = "welcome") -> dict[str, Any]:
    """Return a low-output runtime summary without constructing the full AST inventory.

    This is intentionally not a substitute for bc_boot(): it hashes the source and
    reports the active registry/catalogue, but does not rerun duplicate-definition
    inventory, legacy behaviour summaries, migration matrix, or deep welcome payloads.
    """
    if mode not in {"welcome", "capabilities"}:
        return {"schema": SCHEMA, "engine": ENGINE_IDENTITY, "mode": mode, "pass": False,
                "status": "fast_summary_supports_welcome_or_capabilities_only",
                "report_level": "fast_summary", "full_source_audit_run": False}
    current_path = pathlib.Path(__file__)
    try:
        data = current_path.read_bytes()
    except OSError as exc:
        return {"schema": SCHEMA, "engine": ENGINE_IDENTITY, "mode": mode, "pass": False,
                "status": "source_unavailable", "reason": type(exc).__name__ + ":" + str(exc),
                "report_level": "fast_summary", "full_source_audit_run": False}
    names = list(GLYPH_CATALOG.names())
    return {
        "schema": SCHEMA, "engine": ENGINE_IDENTITY, "runtime_state": RUNTIME_STATE,
        "mode": mode, "report_level": "fast_summary", "pass": True,
        "status": "runtime_summary_pass_full_source_audit_not_run",
        "source": {"path": str(current_path), "available": True,
                   "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                   "python_module_loaded": True, "duplicate_definition_scan": "not_run",
                   "legacy_inventory_scan": "not_run", "source_executed": False},
        "registry_count": len(REGISTRY.names()), "glyph_count": len(names),
        "glyph_catalogue_digest": _sha256_text(_canonical_json(names)),
        "authority": {"source_write": False, "project_save": False,
                      "engine_cold_commit": False, "glyph_admission": False},
        "crown_continuation": crown_continuation_entry(hashlib.sha256(data).hexdigest(), len(data)),
        "full_report_command": "rerun without --fast-summary",
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backlit Canopy clean runtime")
    parser.add_argument("--mode", choices=("welcome", "inspect", "capabilities", "migration"), default="welcome")
    parser.add_argument("--source", help="explicit source path for inspect/migration")
    parser.add_argument("--expected-sha256", help="optional exact source identity for migration inventory")
    parser.add_argument("--output", help="write complete report JSON here instead of printing full inventory")
    parser.add_argument("--summary", action="store_true", help="print a compact summary after full checks")
    parser.add_argument("--fast-summary", action="store_true", help="fast compact runtime summary; skips full source/legacy inventory checks")
    parser.add_argument("--compact-json", action="store_true", help="write compact sorted JSON without indentation")
    parser.add_argument("--crown-map", action="store_true", help="build and open the complete in-engine Crown route map")
    parser.add_argument("--crown-route-id", help="open one selected Crown route node from the whole-engine map")
    parser.add_argument("--crown-query", help="query bounded routes in the whole-engine Crown map")
    parser.add_argument("--crown-kind", action="append", default=[], help="optional route kind filter for --crown-query; may repeat")
    parser.add_argument("--crown-start-index", type=int, default=0, help="result page offset for --crown-query")
    parser.add_argument("--crown-max-items", type=int, default=24, help="maximum routes returned by --crown-query (1..64)")
    parser.add_argument("--crown-artifact-route-id", help="open a checksummed artifact or source-symbol span through the Crown map")
    parser.add_argument("--crown-offset", type=int, default=0, help="byte offset for bounded Crown artifact opening")
    parser.add_argument("--crown-bytes", type=int, default=65536, help="maximum bytes for bounded Crown artifact opening (1..262144)")
    args = parser.parse_args(argv)
    if args.crown_map or args.crown_route_id or args.crown_query is not None or args.crown_artifact_route_id:
        crown_map = build_crown_engine_map()
        if args.crown_query is not None:
            crown_report = query_crown_engine_routes(crown_map,args.crown_query,kinds=args.crown_kind,
                start_index=args.crown_start_index,max_items=args.crown_max_items,max_output_bytes=args.crown_bytes)
        elif args.crown_artifact_route_id:
            crown_report = open_crown_route_artifact(crown_map, args.crown_artifact_route_id, args.crown_offset, args.crown_bytes)
        elif args.crown_route_id:
            crown_report = open_crown_route_batch(crown_map, [args.crown_route_id], max_items=1)
        elif args.output:
            crown_report = crown_map.as_dict()
        else:
            crown_report = {"schema":crown_map.schema,"pass":True,"map_address":crown_map.map_address,
                "current_route_id":crown_map.as_dict().get("current_route_id"),"route_count":len(crown_map.as_dict().get("routes",[])),
                "link_count":len(crown_map.as_dict().get("links",[])),"output_command":"rerun with --crown-map --output BC_CROWN_ENGINE_MAP.json"}
        rendered=json.dumps(crown_report,sort_keys=True,separators=(",",":") if args.compact_json else None,indent=None if args.compact_json else 2)
        if args.output:
            out=pathlib.Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(rendered,encoding="utf-8")
            print(json.dumps({"pass":crown_report.get("pass",True),"schema":crown_report.get("schema"),"output":str(out.resolve()),
                "map_address":crown_report.get("map_address"),"current_route_id":crown_report.get("current_route_id")},sort_keys=True))
        else:
            print(rendered)
        return 0 if crown_report.get("pass",True) is True else 2
    if args.fast_summary:
        report = bc_fast_summary(args.mode)
        compact = args.compact_json
        rendered = json.dumps(report, sort_keys=True, separators=(",", ":") if compact else None,
                              indent=None if compact else 2)
        if args.output:
            out = pathlib.Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered, encoding="utf-8")
            print(json.dumps({"pass": report.get("pass"), "mode": args.mode,
                              "report_level": "fast_summary", "output": str(out.resolve()),
                              "source": report.get("source", {}).get("sha256")},
                             sort_keys=True, separators=(",", ":") if compact else None,
                             indent=None if compact else 2))
        else:
            print(rendered)
        return 0 if report.get("pass") is True else 2
    report = bc_boot(args.mode, source_path=args.source, expected_source_sha256=args.expected_sha256)
    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, sort_keys=True, separators=(",", ":") if args.compact_json else None,
                                   indent=None if args.compact_json else 2), encoding="utf-8")
        print(json.dumps({"pass": report.get("pass"), "mode": args.mode, "output": str(out.resolve()),
                          "source": report.get("source", {}).get("sha256"),
                          "legacy_source": report.get("legacy_migration_inventory", {}).get("source", {}).get("sha256"),
                          "inventory_counts": report.get("legacy_migration_inventory", {}).get("syntax")}, indent=2))
    elif args.summary or args.mode == "migration":
        inv = report.get("legacy_migration_inventory", {})
        print(json.dumps({"schema": report.get("schema"), "engine": report.get("engine"),
                          "mode": args.mode, "pass": report.get("pass"), "status": report.get("status"),
                          "runtime_source": report.get("source", {}).get("sha256"),
                          "legacy_source": inv.get("source", {}).get("sha256"),
                          "syntax": inv.get("syntax"), "registry_count": len(REGISTRY.names()),
                          "cold_commit": "NOT_PERFORMED"}, sort_keys=True,
                         separators=(",", ":") if args.compact_json else None,
                         indent=None if args.compact_json else 2))
    else:
        print(json.dumps(report, sort_keys=True, separators=(",", ":") if args.compact_json else None,
                         indent=None if args.compact_json else 2))
    return 0 if report.get("pass") is True else 2


if __name__ == "__main__":
    raise SystemExit(_main())
