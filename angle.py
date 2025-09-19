import math

def service_angle(service_start_point, highest_point):
    """
    Liczy kąt serwisu przy punkcie STARTOWYM piłeczki (kąt między pionem a trajektorią).
    Wynik w stopniach.
    """
    x_start, y_start = service_start_point[1]
    x_high, y_high = highest_point[1]

    dx = x_high - x_start
    dy = y_start - y_high

    if dy == 0:
        # Idealnie poziomo, kąt 90°
        return 90.0
    # Kąt (beta): arctan(dx / dy)
    angle_rad = math.atan2(abs(dx), abs(dy))
    angle_deg = round(math.degrees(angle_rad), 2)
    return angle_deg
