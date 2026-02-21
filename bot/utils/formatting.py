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


def _get_name(status: dict) -> str:
    bt = status.get("bittorrent", {})
    info = bt.get("info", {}) if bt else {}
    if info and info.get("name"):
        return info["name"]
    files = status.get("files", [])
    if files:
        path = files[0].get("path", "")
        if path:
            return path.rsplit("/", 1)[-1]
    return "Unknown"


def format_progress(status: dict) -> str:
    total = int(status.get("totalLength", 0))
    completed = int(status.get("completedLength", 0))
    speed = int(status.get("downloadSpeed", 0))
    state = status.get("status", "unknown")
    gid = status.get("gid", "?")
    name = _get_name(status)

    fraction = completed / total if total > 0 else 0
    pct = fraction * 100
    bar = progress_bar(fraction)
    eta = _calc_eta(total - completed, speed)

    lines = [
        f"\U0001F4E5 <b>{name}</b>",
        f"{bar} {pct:.1f}%",
        f"\U0001F4BE {format_size(completed)} / {format_size(total)}",
        f"\U0001F680 {format_speed(speed)}  |  ETA: {eta}",
    ]

    # Seeders info for torrents
    bt = status.get("bittorrent")
    if bt is not None:
        seeders = int(status.get("numSeeders", 0))
        connections = int(status.get("connections", 0))
        lines.append(f"S: {seeders}  |  Connections: {connections}")

    lines.append(f"Status: <code>{state}</code>  |  GID: <code>{gid}</code>")
    return "\n".join(lines)


def format_completed(status: dict) -> str:
    total = int(status.get("totalLength", 0))
    gid = status.get("gid", "?")
    name = _get_name(status)

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
    name = _get_name(status)

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
        name = _get_name(d)

        fraction = completed / total if total > 0 else 0
        bar = progress_bar(fraction, length=10)

        extra = ""
        bt = d.get("bittorrent")
        if bt is not None:
            seeders = int(d.get("numSeeders", 0))
            extra = f" S:{seeders}"

        lines.append(
            f"{'▶' if state == 'active' else '⏸' if state == 'paused' else '⏹'} "
            f"<b>{name}</b>\n"
            f"   {bar} {fraction * 100:.0f}% | {format_speed(speed)}{extra} | "
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


def format_torrent_info(status: dict, files: list[dict]) -> str:
    name = _get_name(status)
    total = int(status.get("totalLength", 0))
    gid = status.get("gid", "?")
    file_count = len(files)

    return (
        f"\U0001F9F2 <b>Torrent added</b>\n\n"
        f"\U0001F4C4 <b>{name}</b>\n"
        f"\U0001F4BE Size: {format_size(total)}\n"
        f"\U0001F4C2 Files: {file_count}\n"
        f"GID: <code>{gid}</code>"
    )


def format_file_list(files: list[dict], selected: set[int] | None = None) -> str:
    lines = []
    for f in files:
        index = int(f.get("index", 0))
        path = f.get("path", "Unknown")
        name = path.rsplit("/", 1)[-1] if path else "Unknown"
        size = int(f.get("length", 0))

        if selected is not None:
            mark = "\u2705" if index in selected else "\u2B1C"
            lines.append(f"{mark} <b>{index}.</b> {name} ({format_size(size)})")
        else:
            lines.append(f"<b>{index}.</b> {name} ({format_size(size)})")

    return "\n".join(lines)
