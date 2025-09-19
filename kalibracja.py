def calculate_throw_height(service_start_point, highest_point, pixels_per_cm=5):
    """
    Oblicza wysokość podrzutu piłeczki.
    """
    start_y = service_start_point[1][1]
    highest_y = highest_point[1][1]
    pixel_diff = start_y - highest_y
    height_cm = pixel_diff / pixels_per_cm
    return round(height_cm, 2), pixel_diff
