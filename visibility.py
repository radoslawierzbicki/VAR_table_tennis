def count_service_visibility(detected_points, service_start_idx, service_end_idx):
    """
    Liczy ile KLATEK (spośród detekcji) rzeczywiście zawierało piłeczkę (tylko prawdziwe detekcje, nie interpolacje!)
    """
    if service_start_idx is None or service_end_idx is None:
        return 0, 0, 0.0
    ball_frames = set(f for f, _, _ in detected_points)
    n_all = (service_end_idx - service_start_idx) + 1
    n_visible = sum(1 for f in range(service_start_idx, service_end_idx + 1) if f in ball_frames)
    percent = (100.0 * n_visible / n_all) if n_all > 0 else 0.0
    return n_visible, n_all, round(percent, 1)
