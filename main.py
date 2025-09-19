import cv2
import os
import glob
from ultralytics import YOLO
import numpy as np
from tracker import ObjectTracker
from service_detector import detect_service_start, detect_service_end
from service_height import detect_highest_point
from kalibracja import calculate_throw_height
from angle import service_angle
from visibility import count_service_visibility


def find_highest_hand(hand_points):
    if not hand_points:
        return None, None
    min_y_point = min(hand_points, key=lambda p: p[2])
    frame_idx, x, y = min_y_point
    return frame_idx, (x, y)


def in_table_x_range(x, width, margin_ratio=0.1):
    margin = int(width * margin_ratio)
    return margin <= x <= (width - margin)


def run_analysis(video_path):
    OUTPUT_DIR = 'wynik/detekcja1'
    OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, 'output.mp4')
    MODEL_PATH = 'my_model.pt'

    BALL_CLASS_ID = 0
    RACKET_CLASS_ID = 2
    HAND_CLASS_ID = 1

    BALL_COLOR = (0, 255, 0)
    RACKET_COLOR = (255, 0, 255)
    HAND_COLOR = (128, 0, 0)
    INTERPOLATION_COLOR = (0, 140, 255)
    TRAJECTORY_COLOR = (255, 255, 0)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    model = YOLO(MODEL_PATH)
    ball_tracker = ObjectTracker(BALL_COLOR, INTERPOLATION_COLOR)
    racket_tracker = ObjectTracker(RACKET_COLOR, INTERPOLATION_COLOR)
    hand_tracker = ObjectTracker(HAND_COLOR, INTERPOLATION_COLOR)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frames = []
    frame_idx = 0

    # Clear hidden ball images folder if exists
    output_dir_hidden = os.path.join('wynik', 'piłeczka_zasłonięta')
    if os.path.exists(output_dir_hidden):
        files = glob.glob(os.path.join(output_dir_hidden, '*'))
        for f in files:
            os.remove(f)
    else:
        os.makedirs(output_dir_hidden, exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame.copy())
        results = model.predict(frame, conf=0.122, verbose=False)
        boxes = results[0].boxes

        ball = racket = hand = None

        for box in boxes:
            cls_id = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            if cls_id == BALL_CLASS_ID:
                bbox_w = x2 - x1
                bbox_h = y2 - y1
                MAX_BALL_SIZE = 50  # maksymalny rozmiar traktowany jako piłka
                if bbox_w > MAX_BALL_SIZE or bbox_h > MAX_BALL_SIZE:
                    continue  # pomijaj zbyt duże piłeczki
                if not in_table_x_range(cx, width):
                    continue
                ball = (cx, cy)
            elif cls_id == RACKET_CLASS_ID:
                racket = (cx, cy)
            elif cls_id == HAND_CLASS_ID:
                hand = (cx, cy)


        if ball:
            ball_tracker.add_detection(frame_idx, *ball)
        if racket:
            racket_tracker.add_detection(frame_idx, *racket)
        if hand:
            hand_tracker.add_detection(frame_idx, *hand)

        frame_idx += 1

    cap.release()

    ball_points = sorted(ball_tracker.detected_points + ball_tracker.interpolate(), key=lambda x: x[0])
    racket_points = sorted(racket_tracker.detected_points + racket_tracker.interpolate(), key=lambda x: x[0])
    hand_points = sorted(hand_tracker.detected_points + hand_tracker.interpolate(), key=lambda x: x[0])

    SERVICE_OUTPUT_DIR = 'wynik/wykrywanie_serwisu'
    os.makedirs(SERVICE_OUTPUT_DIR, exist_ok=True)

    service_start_idx, service_start_coords = detect_service_start(ball_points, hand_points, max_distance=20)

    if service_start_idx is None:
        highest_hand_idx, highest_hand_coords = find_highest_hand(hand_points)
        if highest_hand_idx is not None:
            start_idx = max(0, highest_hand_idx - 3)
            ball_coords = next(((x, y) for f, x, y in ball_points if f == start_idx), None)
            service_start_idx = start_idx
            service_start_coords = ball_coords if ball_coords else highest_hand_coords
    if service_start_idx is not None:
        cv2.imwrite(os.path.join(SERVICE_OUTPUT_DIR, "start_serwisu.png"), frames[service_start_idx])
    else:
        service_start_coords = None

    SERVICE_END_OUTPUT_DIR = 'wynik/wykrywanie_konca_serwisu'
    os.makedirs(SERVICE_END_OUTPUT_DIR, exist_ok=True)

    service_end_idx, service_end_coords = detect_service_end(
        ball_points, racket_points, contact_thresh=15,
        start_frame=service_start_idx if service_start_idx is not None else None
    )
    if service_end_idx is not None:
        cv2.imwrite(os.path.join(SERVICE_END_OUTPUT_DIR, "koniec_serwisu.png"), frames[service_end_idx])
    else:
        service_end_coords = None
        

    BALL_HEIGHT_OUTPUT_DIR = 'wynik/najwyzszy_punkt'
    os.makedirs(BALL_HEIGHT_OUTPUT_DIR, exist_ok=True)

    if service_start_idx is not None and service_end_idx is not None:
        ball_points_in_service = [
            p for p in ball_points if service_start_idx <= p[0] <= service_end_idx
        ]
        highest_idx, highest_coords = detect_highest_point(ball_points_in_service)
    else:
        highest_idx, highest_coords = None, None

    if highest_idx is not None and 0 <= highest_idx < len(frames):
        cv2.imwrite(
            os.path.join(BALL_HEIGHT_OUTPUT_DIR, "najwyzszy_punkt_serwisu.png"),
            frames[highest_idx]
        )
    else:
        highest_coords = None

    OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, 'output.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))

    trajectory_points = [p for p in ball_points if service_start_idx is not None and highest_idx is not None and service_start_idx <= p[0] <= highest_idx]

    SLOWDOWN_FACTOR = 5

    # Calculate measurement results early for drawing and legality decision
    wysokosc_cm = None
    kat_serwisu = None
    n_visible = None
    n_all = None
    percent = None

    if service_start_idx is not None and highest_idx is not None:
        wysokosc_cm, _ = calculate_throw_height(
            (service_start_idx, service_start_coords),
            (highest_idx, highest_coords),
            pixels_per_cm=5
        )
        kat_serwisu = service_angle(
            (service_start_idx, service_start_coords),
            (highest_idx, highest_coords)
        )

    if service_start_idx is not None and service_end_idx is not None:
        n_visible, n_all, percent = count_service_visibility(
            ball_tracker.detected_points,
            service_start_idx,
            service_end_idx
        )

    # Conditions for legality of serve
    poprawny_podrzut = wysokosc_cm is not None and wysokosc_cm >= 16
    poprawny_kat = kat_serwisu is not None and kat_serwisu < 30
    poprawna_widocznosc = percent is not None and percent > 80
    serwis_poprawny = poprawny_podrzut and poprawny_kat and poprawna_widocznosc

    # Text lines for legality issues
    error_lines = []
    error_color = (0, 255, 0)  # green by default
    if not serwis_poprawny:
        error_color = (0, 0, 255)  # red if illegal
        if not poprawna_widocznosc:
            error_lines.append("- ball hidden")
        if not poprawny_podrzut:
            error_lines.append("- toss too low")
        if not poprawny_kat:
            error_lines.append("- toss angle too wide")

    # Font settings for overlay text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale_title = 1.5
    font_scale_error = 1.1
    thickness = 3
    margin_bottom = 10
    line_height = 30

    for idx, frame in enumerate(frames):

        # Draw detected and interpolated ball points
        for f, x, y in ball_tracker.detected_points:
            if f == idx:
                cv2.circle(frame, (int(x), int(y)), 5, BALL_COLOR, -1)
        for f, x, y in ball_tracker.interpolate():
            if f == idx:
                cv2.circle(frame, (int(x), int(y)), 5, INTERPOLATION_COLOR, -1)

        # Check if frame is hidden ball frame
        is_hidden_frame = False
        if service_end_idx is not None and highest_idx is not None:
            ball_true_frames = {f for f, _, _ in ball_tracker.detected_points}
            if highest_idx <= idx <= service_end_idx and idx not in ball_true_frames:
                is_hidden_frame = True

        # Draw trajectory up to service_end_idx only if ball visible and after start
        if (not is_hidden_frame and service_start_idx is not None and highest_idx is not None and
            service_end_idx is not None and service_start_idx <= idx <= service_end_idx):
            pts = [p for p in trajectory_points if p[0] <= idx]
            for i in range(1, len(pts)):
                cv2.line(frame, (int(pts[i-1][1]), int(pts[i-1][2])), (int(pts[i][1]), int(pts[i][2])), TRAJECTORY_COLOR, 2)

        # Draw racket and hand points
        for f, x, y in racket_points:
            if f == idx:
                cv2.circle(frame, (int(x), int(y)), 6, RACKET_COLOR, -1)
        for f, x, y in hand_points:
            if f == idx:
                cv2.circle(frame, (int(x), int(y)), 6, HAND_COLOR, -1)


        # Draw hidden ball frames images
        if is_hidden_frame:
            output_dir_hidden = os.path.join('wynik', 'piłeczka_zasłonięta')
            os.makedirs(output_dir_hidden, exist_ok=True)
            cv2.imwrite(os.path.join(output_dir_hidden, f"hidden_{idx}.png"), frame)

        # Draw serve legality overlay starting from end of service to end video
        if service_end_idx is not None and idx >= service_end_idx:
            overlay_height = 110
            overlay_width = width
            overlay = frame.copy()
            alpha = 0.7  # transparency

            # Draw semi-transparent rectangle at bottom
            cv2.rectangle(overlay, (0, height - overlay_height), (overlay_width, height), (50, 50, 50), -1)
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

            # Display "Legal Serve" or "Illegal Serve"
            if serwis_poprawny:
                title_text = "LEGAL SERVE"
                title_color = (0, 255, 0)  # green
            else:
                title_text = "ILLEGAL SERVE"
                title_color = (0, 0, 255)  # red

            title_size = cv2.getTextSize(title_text, font, font_scale_title, thickness)[0]
            title_pos = ((width - title_size[0]) // 2, height - overlay_height + 40)
            cv2.putText(frame, title_text, title_pos, font, font_scale_title, title_color, thickness, cv2.LINE_AA)

            # Draw error lines below the title
            for i, line in enumerate(error_lines):
                err_pos = (50, height - overlay_height + 30 + i * line_height)
                cv2.putText(frame, line, err_pos, font, font_scale_error, error_color, thickness, cv2.LINE_AA)

        # Write slowed down output video frame
        for _ in range(SLOWDOWN_FACTOR):
            out.write(frame)

    out.release()

    if kat_serwisu is not None and service_start_coords is not None and highest_coords is not None and highest_idx is not None:
        ANGLE_OUTPUT_DIR = os.path.join('wynik', 'kąt_serwisu')
        os.makedirs(ANGLE_OUTPUT_DIR, exist_ok=True)

        x_start, y_start = service_start_coords
        x_high, y_high = highest_coords
        x_c = x_start
        y_c = y_high

        frame_triangle = frames[highest_idx].copy()

        # Rysowanie kąta serwisu na obrazku
        cv2.line(frame_triangle, (int(x_start), int(y_start)), (int(x_high), int(y_high)), (0, 0, 255), 2)
        cv2.line(frame_triangle, (int(x_start), int(y_start)), (int(x_c), int(y_c)), (0, 255, 0), 2)
        cv2.line(frame_triangle, (int(x_c), int(y_c)), (int(x_high), int(y_high)), (255, 0, 0), 2)

        cv2.circle(frame_triangle, (int(x_start), int(y_start)), 9, (0, 0, 255), -1)
        cv2.circle(frame_triangle, (int(x_high), int(y_high)), 9, (0, 255, 0), -1)
        cv2.circle(frame_triangle, (int(x_c), int(y_c)), 9, (255, 0, 0), -1)

        text = f"Angle: {kat_serwisu}"
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 4)[0]
        text_pos = (int(x_start) - text_size[0] // 2, int(y_start) - 30)
        cv2.putText(frame_triangle, text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 4)

        out_triangle_path = os.path.join(ANGLE_OUTPUT_DIR, 'kat_serwisu.png')
        cv2.imwrite(out_triangle_path, frame_triangle)


    # Prepare summary text
    result_text = []
    result_text.append(f"Początek serwisu: klatka {service_start_idx}, współrzędne {service_start_coords}")
    result_text.append(f"Koniec serwisu: klatka {service_end_idx}, współrzędne {service_end_coords}")
    result_text.append(f"Najwyższy punkt piłeczki: klatka {highest_idx}, współrzędne {highest_coords}")
    if wysokosc_cm is not None:
        result_text.append(f"Piłeczka wyrzucona na: {wysokosc_cm} cm")
    if kat_serwisu is not None:
        result_text.append(f"Kąt serwisu (beta, pion-trajektoria): {kat_serwisu}°")
    if n_visible is not None:
        result_text.append(f"WIDOCZNOŚĆ SERWISU: {n_visible}/{n_all} klatek, {percent}%")
    else:
        result_text.append("Nie można ocenić widoczności – brak danych o początku lub końcu serwisu.")

    result_str = "\n".join(result_text)

    return {
        "service_start_idx": service_start_idx,
        "service_start_coords": service_start_coords,
        "service_end_idx": service_end_idx,
        "service_end_coords": service_end_coords,
        "highest_idx": highest_idx,
        "highest_coords": highest_coords,
        "throw_height_cm": wysokosc_cm,
        "service_angle_deg": kat_serwisu,
        "is_service_valid": serwis_poprawny,
        "height_valid": poprawny_podrzut,
        "angle_valid": poprawny_kat,
        "visibility_valid": poprawna_widocznosc,
        "error": None,
        "visibility": {
            "visible_frames": n_visible,
            "all_frames": n_all,
            "percent": percent
        } if n_visible is not None else None,
        "raw_results": result_str
    }
