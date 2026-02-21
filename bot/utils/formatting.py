def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


def format_speed(speed_bytes: int) -> str:
    return f"{format_size(speed_bytes)}/s"


def progress_bar(fraction: float, length: int = 20) -> str:
    filled = int(length * fraction)
    return "\u2588" * filled + "\u2591" * (length - filled)


def _calc_eta(remaining_bytes: int, speed: int) -> str:
    if speed <= 0:
        return "\u221e"
    seconds = remaining_bytes / speed
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


def format_progress(status: dict) -> str:
    total = int(status.get("totalLength", 0))
    completed = int(status.get("completedLength", 0))
    speed = int(status.get("downloadSpeed", 0))
    state = status.get("status", "unknown")
    gid = status.get("gid", "?")

    name = "Unknown"
    files = status.get("files", [])
    if files:
        path = files[0].get("path", "")
        if path:
            name = path.rsplit("/", 1)[-1]

    fraction = completed / total if total > 0 else 0
    pct = fraction * 100
    bar = progress_bar(fraction)
    eta = _calc_eta(total - completed, speed)

    lines = [
        f"\U0001F4E5 <b>{name}</b>",
        f"{bar} {pct:.1f}%",
        f"\U0001F4BE {format_size(completed)} / {format_size(total)}",
        f"\U0001F680 {format_speed(speed)}  |  ETA: {eta}",
        f"Status: <code>{state}</code>  |  GID: <code>{gid}</code>",
    ]
    return "\n".join(lines)


def format_completed(status: dict) -> str:
    total = int(status.get("totalLength", 0))
    gid = status.get("gid", "?")

    name = "Unknown"
    files = status.get("files", [])
    if files:
        path = files[0].get("path", "")
        if path:
            name = path.rsplit("/", 1)[-1]

    return (
        f"\u2705 <b>Download complete</b>\n"
        f"\U0001F4C4 {name}\n"
        f"\U0001F4BE {format_size(total)}\n"
        f"GID: <code>{gid}</code>"
    )


def format_error(status: dict) -> str:
    gid = status.get("gid", "?")
    code = status.get("errorCode", "?")
    msg = status.get("errorMessage", "Unknown error")

    name = "Unknown"
    files = status.get("files", [])
    if files:
        path = files[0].get("path", "")
        if path:
            name = path.rsplit("/", 1)[-1]

    return (
        f"\u274C <b>Download failed</b>\n"
        f"\U0001F4C4 {name}\n"
        f"Error {code}: {msg}\n"
        f"GID: <code>{gid}</code>"
    )


def format_download_list(downloads: list[dict]) -> str:
    if not downloads:
        return "\U0001F4ED No active downloads."

    lines = []
    for d in downloads:
        gid = d.get("gid", "?")
        total = int(d.get("totalLength", 0))
        completed = int(d.get("completedLength", 0))
        speed = int(d.get("downloadSpeed", 0))
        state = d.get("status", "?")

        name = "Unknown"
        files = d.get("files", [])
        if files:
            path = files[0].get("path", "")
            if path:
                name = path.rsplit("/", 1)[-1]

        fraction = completed / total if total > 0 else 0
        bar = progress_bar(fraction, length=10)
        lines.append(
            f"{'▶' if state == 'active' else '⏸' if state == 'paused' else '⏹'} "
            f"<b>{name}</b>\n"
            f"   {bar} {fraction * 100:.0f}% | {format_speed(speed)} | "
            f"<code>{gid}</code>"
        )
    return "\n\n".join(lines)


def format_global_stats(stat: dict) -> str:
    return (
        f"\U0001F4CA <b>aria2c stats</b>\n\n"
        f"\u2B07\uFE0F Download: {format_speed(int(stat.get('downloadSpeed', 0)))}\n"
        f"\u2B06\uFE0F Upload: {format_speed(int(stat.get('uploadSpeed', 0)))}\n"
        f"\u25B6\uFE0F Active: {stat.get('numActive', 0)}\n"
        f"\u23F8\uFE0F Waiting: {stat.get('numWaiting', 0)}\n"
        f"\u23F9\uFE0F Stopped: {stat.get('numStopped', 0)}"
    )
