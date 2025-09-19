import math

def distance(p1, p2):
    if p1 is None or p2 is None:
        return None
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def detect_service_start(ball_points, hand_points, max_distance=20, min_upward_frames=3, lookahead=10):
    """
    Detekcja startu serwisu z uwzględnieniem momentu, kiedy piłeczka i dłoń idą razem w górę,
    a następnie piłeczka oddala się od dłoni, która przestaje ją prowadzić (zatrzymuje się).
    """
    n = min(len(ball_points), len(hand_points))

    for i in range(n - min_upward_frames - lookahead):
        upward_hand = True
        upward_ball = True

        for j in range(i + 1, i + 1 + min_upward_frames):
            if hand_points[j][0] != ball_points[j][0]:
                upward_hand = False
                upward_ball = False
                break
            if hand_points[j][2] >= hand_points[j - 1][2]:  # ręka idzie w dół lub stoi
                upward_hand = False
            if ball_points[j][2] >= ball_points[j - 1][2]:
                upward_ball = False
            if not (upward_hand and upward_ball):
                break

        if not (upward_hand and upward_ball):
            continue

        dist_start = distance(
            (ball_points[i][1], ball_points[i][2]),
            (hand_points[i][1], hand_points[i][2])
        )

        distances_after = []
        ball_y_after = []
        hand_y_after = []

        for k in range(i + min_upward_frames, i + min_upward_frames + lookahead):
            if k >= n:
                break
            if ball_points[k][0] != hand_points[k][0]:
                continue
            d = distance(
                (ball_points[k][1], ball_points[k][2]),
                (hand_points[k][1], hand_points[k][2])
            )
            distances_after.append(d)
            ball_y_after.append(ball_points[k][2])
            hand_y_after.append(hand_points[k][2])

        if distances_after and ball_y_after and hand_y_after:
            if distances_after[-1] > dist_start:
                hand_upward = all(hand_y_after[i] < hand_y_after[i - 1] for i in range(1, len(hand_y_after)))
                ball_upward_or_stable = all(ball_y_after[i] <= ball_y_after[i - 1] for i in range(1, len(ball_y_after)))

                if not hand_upward and ball_upward_or_stable:
                    hit_frame = ball_points[i + min_upward_frames][0]
                    hit_coords = (ball_points[i + min_upward_frames][1], ball_points[i + min_upward_frames][2])
                    return hit_frame, hit_coords

    return None, None


def detect_service_end(ball_points, racket_points, contact_thresh=15, start_frame=None):
    """
    Wykrywa koniec serwisu jako klatkę, w której piłka i rakietka są najbliżej siebie
    w odległości mniejszej niż contact_thresh pikseli.
    start_frame – jeśli podany, szuka końca tylko od tej klatki włącznie.
    """
    min_dist = float('inf')
    best_frame = None
    best_coords = None

    for f_b, x_b, y_b in ball_points:
        if start_frame is not None and f_b < start_frame:
            continue
        for f_r, x_r, y_r in racket_points:
            if start_frame is not None and f_r < start_frame:
                continue
            dist = distance((x_b, y_b), (x_r, y_r))
            if dist is not None and dist < contact_thresh:
                if dist < min_dist:
                    min_dist = dist
                    best_frame = f_b
                    best_coords = (x_b, y_b)

    if best_frame is not None:
        return best_frame, best_coords
    else:
        return None, None
