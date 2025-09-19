import cv2

class ObjectTracker:
    def __init__(self, detection_color, interpolation_color=(0, 140, 255)):
        """
        detection_color: kolor punktów z detekcji (BGR)
        interpolation_color: kolor punktów interpolowanych (BGR)
        """
        self.detected_points = []
        self.detection_color = detection_color
        self.interpolation_color = interpolation_color

    def add_detection(self, frame_idx, x, y):
        """Dodaje punkt detekcji dla określonej klatki."""
        self.detected_points.append((frame_idx, x, y))

    def interpolate(self):
        """Interpoluje brakujące punkty między detekcjami."""
        if len(self.detected_points) < 2:
            return []
        interpolated = []
        for i in range(len(self.detected_points) - 1):
            f0, x0, y0 = self.detected_points[i]
            f1, x1, y1 = self.detected_points[i + 1]
            for f in range(f0 + 1, f1):
                alpha = (f - f0) / (f1 - f0)
                xi = x0 + alpha * (x1 - x0)
                yi = y0 + alpha * (y1 - y0)
                interpolated.append((f, xi, yi))
        return interpolated
