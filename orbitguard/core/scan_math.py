# orbitguard/core/scan_math.py
from __future__ import annotations
import math


def clamp(x: float, lo: float, hi: float) -> float:
    """
    After func. is minimized, theres a chance that result might
    be outside the scan time window the user asked for (t1, t2). 
    The clamp function makes the scan answer the closest approach
    in the requested window rather than the closest approach at 
    any time. 
    """
    return max(lo, min(hi, x))


def closest_approach_constant_velocity(
    epoch_ts: int,
    x_km: float, y_km: float, z_km: float,
    vx_km_s: float, vy_km_s: float, vz_km_s: float,
    start_ts: int,
    end_ts: int,
) -> tuple[int, float]:
    """
    This func. computes the time of closest approach and the minimum 
    distance between the object and Earth (origin) during a scan window.

    Model (MVP), assumes object moves in a straight line at constant v:
      r(t) = r0 + v*(t - t0)

    We want to:
      minimize ||r(t)||(distance) over t in [start_ts, end_ts]

    Returns:
      (tca_ts, min_distance_km)
    """

    #time windows are converted to floating point numbers
    t1 = float(start_ts)
    t2 = float(end_ts)

    #t0 is the epoch time (when the dataset says r0 and v are valid)
    t0 = float(epoch_ts)

    #initial position vector r0 (km)
    rx, ry, rz = float(x_km), float(y_km), float(z_km)

    #velocity vector v (km/s)
    vx, vy, vz = float(vx_km_s), float(vy_km_s), float(vz_km_s)

    # v2 = v·v = ||v||^2
    # This shows up in the formula for t*
    v2 = vx*vx + vy*vy + vz*vz

    #Special case: object isn't moving (or velocity is exactly zero)
    #If v is zero, the object stays at the same position forever,
    # so the closest distance in the window must be at one of the endpoints.
    if v2 == 0.0:
        # Distance at the start of the window
        dt1 = t1 - t0  # seconds from epoch to start
        r1x = rx + vx * dt1
        r1y = ry + vy * dt1
        r1z = rz + vz * dt1
        d1 = math.sqrt(r1x*r1x + r1y*r1y + r1z*r1z)

        # Distance at the end of the window
        dt2 = t2 - t0
        r2x = rx + vx * dt2
        r2y = ry + vy * dt2
        r2z = rz + vz * dt2
        d2 = math.sqrt(r2x*r2x + r2y*r2y + r2z*r2z)

        # Pick whichever endpoint is closer
        if d1 <= d2:
            return start_ts, d1
        return end_ts, d2

    # result (unconstrained minimum)
    # We want to minimize ||r(t)||^2 where:
    # r(t) = r0 + v*(t - t0)
    # The minimum happens at:
    #   t* = t0 - (r0·v)/(v·v)
    # r0·v (dot product) measures how much the object is moving
    # toward (+negative) or away (+positive) from the origin at the epoch.
    rv = rx*vx + ry*vy + rz*vz  # r0·v

    # Unconstrained best time (could be outside the scan window)
    t_star = t0 - (rv / v2)

    #constrain to scan window
    # Even if the best mathematical time is outside the window,
    # the closest point within the window must be at a boundary.
    t_star = clamp(t_star, t1, t2)

    #Compute position at t_star
    dt = t_star - t0  # seconds after epoch
    cx = rx + vx * dt
    cy = ry + vy * dt
    cz = rz + vz * dt

    # euclidean distance from origin 
    dmin = math.sqrt(cx*cx + cy*cy + cz*cz)

    # Return integer timestamp and min distance
    return int(round(t_star)), dmin