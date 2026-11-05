"""Boundary helper: works out the geometry of a simple line chart, drawn as an
inline SVG by templates/shared/_chart.html. No JavaScript or chart library is needed."""

WIDTH, HEIGHT = 480, 200
LEFT, RIGHT, TOP, BOTTOM = 40, 22, 12, 28


def _nice_step(value):
    """Step between the 4 grid lines: 1, 2, 3 or 5 times a power of ten, so the
    top of the axis (4 steps) is just above the highest value."""
    needed = max(value, 1) / 4
    power = 1
    while True:
        for step in (1, 2, 3, 5):
            if step * power >= needed:
                return step * power
        power *= 10


def line_chart(labels, values, max_labels=8):
    """Return everything the template needs: the line, the shaded area, the
    points (with a tooltip each), y-axis ticks and a few x-axis labels.
    A value of None (a day that has not happened yet) gets a label but no point."""
    count = len(values)
    known = [v for v in values if v is not None]
    step = _nice_step(max(known) if known else 0)
    top = step * 4
    plot_w, plot_h = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM

    def x(i):
        return LEFT + (plot_w * i / (count - 1) if count > 1 else plot_w / 2)

    def y(v):
        return TOP + plot_h - plot_h * v / top

    slots = [round(x(i), 1) for i in range(count)]
    points = [{"x": slots[i], "y": round(y(v), 1), "label": labels[i], "value": v}
              for i, v in enumerate(values) if v is not None]
    line = " ".join(f"{p['x']},{p['y']}" for p in points)
    base = TOP + plot_h
    area = f"{LEFT},{base} {line} {points[-1]['x'] if points else LEFT},{base}" if points else ""
    ticks = [{"y": round(y(step * k), 1), "value": step * k} for k in range(5)]
    every = max(1, -(-count // max_labels))  # ceiling division
    shown = list(range(0, count, every))  # evenly spaced; the tooltips still give every point
    x_labels = [{"x": slots[i], "text": labels[i]} for i in shown]
    return {"width": WIDTH, "height": HEIGHT, "left": LEFT, "right": WIDTH - RIGHT, "base": base,
            "points": points, "line": line, "area": area, "ticks": ticks, "x_labels": x_labels,
            "total": sum(known), "peak": max(known) if known else 0,
            "show_dots": count <= 40}
