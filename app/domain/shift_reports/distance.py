from math import asin, cos, radians, sin, sqrt


EARTH_RADIUS_METERS = 6_371_000.0


def calculate_distance_meters(
    point_lng: float,
    point_ltd: float,
    object_lng: float,
    object_ltd: float,
) -> float:
    """Return the straight-line distance between two WGS84 points in meters."""
    point_latitude = radians(point_ltd)
    object_latitude = radians(object_ltd)
    delta_latitude = object_latitude - point_latitude
    delta_longitude = radians(object_lng - point_lng)

    haversine = (
        sin(delta_latitude / 2) ** 2
        + cos(point_latitude)
        * cos(object_latitude)
        * sin(delta_longitude / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(haversine))
