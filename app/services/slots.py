from app.validation import WORK_DAY_END_MINUTES, WORK_DAY_START_MINUTES, format_minutes


def _hhmm_to_minutes(hhmm: str) -> int:
    hours_str, mins_str = hhmm.split(":")
    return int(hours_str) * 60 + int(mins_str)


def compute_free_slots(active_intervals: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Строит максимальные непрерывные свободные окна внутри рабочего дня 09:00–18:00."""
    occupied: list[tuple[int, int]] = []
    for start_str, end_str in active_intervals:
        start_min = max(WORK_DAY_START_MINUTES, _hhmm_to_minutes(start_str))
        end_min = min(WORK_DAY_END_MINUTES, _hhmm_to_minutes(end_str))
        if start_min < end_min:
            occupied.append((start_min, end_min))

    occupied.sort(key=lambda pair: (pair[0], pair[1]))

    free_slots: list[dict[str, str]] = []
    cursor = WORK_DAY_START_MINUTES
    for busy_start, busy_end in occupied:
        if busy_start > cursor:
            free_slots.append(
                {
                    "startTime": format_minutes(cursor),
                    "endTime": format_minutes(busy_start),
                }
            )
        if busy_end > cursor:
            cursor = busy_end

    if cursor < WORK_DAY_END_MINUTES:
        free_slots.append(
            {
                "startTime": format_minutes(cursor),
                "endTime": format_minutes(WORK_DAY_END_MINUTES),
            }
        )

    return free_slots
