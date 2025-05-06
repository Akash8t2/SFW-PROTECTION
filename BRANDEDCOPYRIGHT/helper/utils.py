def time_formatter(milliseconds: int) -> str:
    seconds, _ = divmod(int(milliseconds / 1000), 60)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    uptime = (
        (f"{days}d, " if days else "")
        + (f"{hours}h, " if hours else "")
        + (f"{minutes}m, " if minutes else "")
        + (f"{seconds}s" if seconds else "")
    )
    return uptime.strip(", ")
