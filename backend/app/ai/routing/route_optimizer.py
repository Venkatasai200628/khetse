"""Route optimisation for consolidated shipment runs.

The MVP ships a dependency-free nearest-neighbour heuristic over haversine
distances: deterministic, fast for the short multi-farmer runs KhetSe
consolidates, and it needs no third-party package. OR-Tools (capacity- and
time-window-aware) is a planned upgrade — replace :func:`solve_route` when
it lands; callers only consume the :class:`SolvedRoute` result.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.utils.geo import haversine_km

SOLVER_NEAREST_NEIGHBOUR = "nearest_neighbour"


@dataclass(frozen=True)
class RouteStop:
    """A routable stop: identity plus coordinates (None → cannot route)."""

    stop_id: uuid.UUID
    lat: float | None
    lng: float | None


@dataclass(frozen=True)
class SolvedRoute:
    """Solver output: visiting order and total driven distance."""

    solver: str
    order: list[uuid.UUID]
    total_distance_km: float


def solve_route(
    stops: Sequence[RouteStop], start: tuple[float, float] | None = None
) -> SolvedRoute:
    """Order `stops` with the nearest-neighbour heuristic.

    `start` is the (lat, lng) the vehicle departs from — the collection
    centre when one is set. Without it, the first stop that has coordinates
    acts as the origin (the "first pickup" rule). Stops without coordinates
    cannot take part in distance decisions and keep their input order at the
    end of the route. Distance ties break on input order, so the result is
    deterministic for a given stop list.
    """
    routable = [s for s in stops if s.lat is not None and s.lng is not None]
    unroutable = [s for s in stops if s.lat is None or s.lng is None]

    if not routable:
        return SolvedRoute(
            solver=SOLVER_NEAREST_NEIGHBOUR,
            order=[s.stop_id for s in stops],
            total_distance_km=0.0,
        )

    remaining = list(routable)
    visited: list[RouteStop] = []
    if start is None:
        first = remaining.pop(0)
        visited.append(first)
        start = (float(first.lat), float(first.lng))  # type: ignore[assignment]

    total_km = 0.0
    while remaining:
        here_lat, here_lng = start
        nearest_index = min(
            range(len(remaining)),
            key=lambda i: (
                haversine_km(here_lat, here_lng, remaining[i].lat, remaining[i].lng),
                i,  # stable tie-break on input order
            ),
        )
        nxt = remaining.pop(nearest_index)
        total_km += haversine_km(here_lat, here_lng, nxt.lat, nxt.lng)
        visited.append(nxt)
        start = (float(nxt.lat), float(nxt.lng))

    visited.extend(unroutable)
    return SolvedRoute(
        solver=SOLVER_NEAREST_NEIGHBOUR,
        order=[s.stop_id for s in visited],
        total_distance_km=round(total_km, 3),
    )
