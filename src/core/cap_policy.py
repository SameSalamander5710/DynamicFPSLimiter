# cap_policy.py
# Pure FPS cap decrease policy, extracted from app.monitoring_loop so it
# can be unit-tested without a GUI, RTSS, or .NET.


def next_cap_on_decrease(fps_limit_list, current_cap, fps_mean):
    """Return the next FPS cap to apply after a decrease decision, or None
    when no decrease is possible.

    ``fps_limit_list`` is the ladder of stepped cap values (e.g.
    [30, 45, 60, 75, 90]); ``current_cap`` is the cap currently applied
    (maxcap + CurrentFPSOffset); ``fps_mean`` is the recent average FPS.

    Policy:
    - empty ladder: None
    - ``current_cap`` in ladder at the lowest rung: None (already at floor)
    - ``current_cap`` in ladder above the floor:
        - ``current_cap <= fps_mean`` (the cap is the limiting factor):
          step down exactly one rung
        - ``current_cap > fps_mean``: jump to the highest rung below
          ``fps_mean``
    - ``current_cap`` not in ladder: highest rung below ``current_cap``
    """
    if not fps_limit_list:
        return None
    try:
        idx = fps_limit_list.index(current_cap)
    except ValueError:
        below_cap = [x for x in fps_limit_list if x < current_cap]
        return max(below_cap) if below_cap else None
    if idx == 0:
        return None
    if current_cap <= fps_mean:
        return fps_limit_list[idx - 1]
    below_mean = [x for x in fps_limit_list if x < fps_mean]
    return max(below_mean) if below_mean else None
