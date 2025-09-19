def detect_highest_point(ball_points):
    """
    Zwraca indeks klatki i współrzędne piłeczki w najwyższym punkcie (najmniejsze Y).
    """
    if not ball_points:
        return None, None
    min_y_point = min(ball_points, key=lambda p: p[2])
    frame_idx, x, y = min_y_point
    return frame_idx, (x, y)
