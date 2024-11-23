import cv2
import numpy as np
from google.colab.patches import cv2_imshow # Import cv2_imshow

# Funkcja do detekcji ruchu i identyfikacji okrągłych obiektów
def detect_moving_ball(prev_frame, current_frame):
    # Przekształcenie klatek na odcienie szarości
    gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    gray_curr = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

    # Rozmycie obrazu, aby zmniejszyć szumy
    gray_prev = cv2.GaussianBlur(gray_prev, (5, 5), 0)
    gray_curr = cv2.GaussianBlur(gray_curr, (5, 5), 0)

    # Różnica między klatkami
    diff = cv2.absdiff(gray_prev, gray_curr)

    # Próg binarny, aby wykryć zmiany
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

    # Erozja i dylatacja w celu usunięcia drobnych szumów
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.erode(thresh, kernel, iterations=2)
    thresh = cv2.dilate(thresh, kernel, iterations=2)

    # Znajdowanie konturów ruchu
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        # Filtracja obiektów na podstawie rozmiaru
        if cv2.contourArea(contour) < 50:
            continue

        # Dopasowanie okręgu do konturu
        (x, y), radius = cv2.minEnclosingCircle(contour)
        if 10 < radius < 25:  # Filtrujemy promień (dopasuj do wielkości piłki)
            center = (int(x), int(y))
            radius = int(radius)

            # Rysowanie wykrytej piłki na obrazie
            cv2.circle(current_frame, center, radius, (0, 255, 0), 2)
            return current_frame, True

    return current_frame, False


# Analiza wideo
frame_count = 0
prev_frame = None

while True:
    ret, frame = video_capture.read()
    if not ret:
        print("Koniec wideo.")
        break

    frame_count += 1

    # Wyświetlaj każdą klatkę od 20.
    if frame_count >= 20:
        # Wykrywanie ruchu
        if prev_frame is not None:
            processed_frame, ball_detected = detect_moving_ball(prev_frame, frame)

            if ball_detected:
                print(f"Ruchoma piłka wykryta na klatce {frame_count}!")
            else:
                print(f"Klatka {frame_count}: brak ruchomej piłki.")

            # Wyświetlaj przetworzoną klatkę
            cv2_imshow(processed_frame)

        # Zaktualizuj poprzednią klatkę
        prev_frame = frame

    # Wyjście z pętli po wciśnięciu klawisza 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Zwolnienie zasobów
video_capture.release()
cv2.destroyAllWindows()
