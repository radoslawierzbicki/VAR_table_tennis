import streamlit as st
import tempfile
import os
import time
from PIL import Image
import cv2
from main import run_analysis
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase, RTCConfiguration
import av

st.title("Analiza serwisu w tenisie stołowym")

def _init_state():
    st.session_state.setdefault("results", None)
    st.session_state.setdefault("video_path", None)
    st.session_state.setdefault("live_results", None)
    #st.session_state.setdefault("live_video_path", None)
    st.session_state.setdefault("live_capture_saved_path", None)
    st.session_state.setdefault("mark_start_idx", None)
    st.session_state.setdefault("mark_end_idx", None)

_init_state()

class CaptureProcessor(VideoProcessorBase):
    def __init__(self) -> None:
        self.frames_buf = []
        self.store_enabled = False
        self.frame_index = 0
    def enable_store(self, enabled: bool):
        self.store_enabled = enabled
    def clear_buffer(self):
        self.frames_buf.clear()
        self.frame_index = 0
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img_bgr = frame.to_ndarray(format="bgr24")
        info = f"frame {self.frame_index}"
        if self.store_enabled:
            info += " | recording"
        cv2.putText(img_bgr, info, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2, cv2.LINE_AA)
        if self.store_enabled:
            self.frames_buf.append(img_bgr.copy())
        self.frame_index += 1
        return av.VideoFrame.from_ndarray(img_bgr, format="bgr24")

RTC_CFG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

tab_file, tab_live = st.tabs(["Wgraj wideo", "Przechwytuj na żywo (WebRTC)"])

with tab_file:
    uploaded_file = st.file_uploader("Wgraj film do analizy (.mp4, .avi)", type=["mp4", "avi"], key="uploader_file_tab")
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmpfile:
            tmpfile.write(uploaded_file.read())
            st.session_state["video_path"] = tmpfile.name
        st.session_state["results"] = None
    if st.session_state["video_path"]:
        st.video(st.session_state["video_path"])
    if st.button("Uruchom analizę", key="run_analysis_btn"):
        if not st.session_state["video_path"]:
            st.warning("Najpierw wgraj plik.")
        else:
            st.info("Analizuję...")
            st.session_state["results"] = run_analysis(st.session_state["video_path"])
            time.sleep(1)
            st.success("Analiza zakończona!")
    results = st.session_state["results"]
    if results is not None:
        service_valid = results.get("is_service_valid")
        error_info = results.get("error")
        height_valid = results.get("height_valid")
        angle_valid = results.get("angle_valid")
        visibility_valid = results.get("visibility_valid")
        height = results.get("throw_height_cm")
        angle = results.get("service_angle_deg")
        vis = results.get("visibility") or {}
        n_visible, n_all, percent = (vis.get("visible_frames"), vis.get("all_frames"), vis.get("percent"))
        if error_info:
            st.markdown(f"<h2 style='color: orange'>BŁĄD: {error_info}</h2>", unsafe_allow_html=True)
        else:
            if service_valid:
                st.markdown("<h2 style='color: #1baf37'>✅ SERWIS PRAWIDŁOWY</h2>", unsafe_allow_html=True)
            else:
                st.markdown("<h2 style='color: #e64646'>❌ SERWIS NIEPRAWIDŁOWY</h2>", unsafe_allow_html=True)
            def colorize(ok: bool) -> str:
                return "#1baf37" if ok else "#e64646"
            st.markdown(f"<span style='font-size: 1.2em; color: {colorize(height_valid)}'>Piłeczka wyrzucona na: {height if height is not None else '-'} cm</span>", unsafe_allow_html=True)
            st.markdown(f"<span style='font-size: 1.2em; color: {colorize(angle_valid)}'>Kąt serwisu: {angle if angle is not None else '-'}°</span>", unsafe_allow_html=True)
            st.markdown(f"<span style='font-size: 1.2em; color: {colorize(visibility_valid)}'>Widoczność serwisu: {n_visible if n_visible is not None else '-'} / {n_all if n_all is not None else '-'} klatek, {percent if percent is not None else '-'}%</span>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.9em; color: #bbb; margin-top:12px;'>"
            f"{'Początek serwisu: klatka ' + str(results.get('service_start_idx')) + ', współrzędne ' + str(results.get('service_start_coords')) if results and results.get('service_start_idx') is not None else ''}<br>"
            f"{'Koniec serwisu: klatka ' + str(results.get('service_end_idx')) + ', współrzędne ' + str(results.get('service_end_coords')) if results and results.get('service_end_idx') is not None else ''}<br>"
            f"{'Najwyższy punkt piłeczki: klatka ' + str(results.get('highest_idx')) + ', współrzędne ' + str(results.get('highest_coords')) if results and results.get('highest_idx') is not None else ''}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<hr>", unsafe_allow_html=True)
        wynik_mp4_path = os.path.join("wynik", "detekcja1", "output.mp4")
        if os.path.exists(wynik_mp4_path) and os.path.getsize(wynik_mp4_path) > 0:
            st.video(wynik_mp4_path)
        else:
            st.warning("Plik wynikowego wideo jest pusty lub nie został znaleziony.")
        obrazki = {
            "Start serwisu": os.path.join("wynik", "wykrywanie_serwisu", "start_serwisu.png"),
            "Koniec serwisu": os.path.join("wynik", "wykrywanie_konca_serwisu", "koniec_serwisu.png"),
            "Najwyższy punkt": os.path.join("wynik", "najwyzszy_punkt", "najwyzszy_punkt_serwisu.png"),
            "Kąt serwisu": os.path.join("wynik", "kąt_serwisu", "kat_serwisu.png"),
        }
        for opis, sciezka in obrazki.items():
            if os.path.exists(sciezka):
                st.image(sciezka, caption=opis)
            else:
                st.write(f"Brak pliku: {opis}")
        hidden_dir = "wynik/piłeczka_zasłonięta"
        if os.path.exists(hidden_dir):
            hidden_images = sorted([os.path.join(hidden_dir, f) for f in os.listdir(hidden_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))])
        else:
            hidden_images = []
        st.markdown("---")
        st.subheader("Klatki z zasłoniętą piłeczką")
        if not hidden_images:
            st.write("Brak zdjęć z zasłoniętą piłeczką.")
        else:
            cols_num = 3
            cols = st.columns(cols_num)
            for i, img_path in enumerate(hidden_images):
                with cols[i % cols_num]:
                    img = Image.open(img_path)
                    st.image(img, caption=os.path.basename(img_path), use_container_width=True)
    else:
        st.write("Wczytaj plik i uruchom analizę.")

with tab_live:
    st.markdown("Podgląd z kamerki przez WebRTC. Włącz nagrywanie do bufora, oznacz START/KONIEC i zapisz fragment do analizy.")
    target_dir = os.path.join("wynik", "serwy")
    os.makedirs(target_dir, exist_ok=True)
    col_codec, col_fps = st.columns(2)
    with col_codec:
        codec_name = st.selectbox("Kodek zapisu", ["mp4v", "avc1"], index=0)
    with col_fps:
        fps_choice = st.number_input("FPS zapisu", min_value=5, max_value=120, value=30, step=1)
    ctx = webrtc_streamer(
        key="webrtc-capture",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CFG,
        video_processor_factory=CaptureProcessor,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )
    if ctx and ctx.video_processor:
        vp: CaptureProcessor = ctx.video_processor
        colA, colB, colC, colD, colE = st.columns(5)
        with colA:
            if st.button("Wyczyść bufor"):
                vp.clear_buffer()
                st.session_state["mark_start_idx"] = None
                st.session_state["mark_end_idx"] = None
                st.info("Bufor wyczyszczony.")
        with colB:
            toggle = st.toggle("Nagrywaj do bufora", value=vp.store_enabled)
            vp.enable_store(toggle)
        with colC:
            if st.button("Oznacz START"):
                st.session_state["mark_start_idx"] = len(vp.frames_buf)
                st.success(f"START = klatka {st.session_state['mark_start_idx']}")
        with colD:
            if st.button("Oznacz KONIEC"):
                st.session_state["mark_end_idx"] = len(vp.frames_buf)
                st.success(f"KONIEC = klatka {st.session_state['mark_end_idx']}")
        with colE:
            save_and_analyze = st.button("Zapisz fragment i analizuj")
        st.caption(f"Klatki w buforze: {len(vp.frames_buf)}")
        if save_and_analyze:
            start_idx = st.session_state.get("mark_start_idx")
            end_idx = st.session_state.get("mark_end_idx")
            if start_idx is None or end_idx is None:
                st.warning("Najpierw oznacz START i KONIEC.")
            elif start_idx >= end_idx:
                st.warning("Zakres niepoprawny: START musi być mniejszy od KONIEC.")
            else:
                frames = vp.frames_buf[start_idx:end_idx]

                if not frames:
                    st.error("Brak klatek w wybranym zakresie.")
                else:
                    # rozmiar bierzemy z pierwszej klatki (BGR: h, w, 3)
                    h, w = frames[0].shape[:2]
                    out_size = (w, h)  # UWAGA: VideoWriter przyjmuje (width, height)

                    fourcc = cv2.VideoWriter_fourcc(*codec_name)
                    ts = int(time.time())
                    outfile = os.path.join(target_dir, f"serve_{ts}.mp4")
                    out = cv2.VideoWriter(outfile, fourcc, float(fps_choice), out_size)

                    for f in frames:
                        # na wszelki wypadek wyrównaj rozmiar, jeśli różny
                        if f.shape[:2] != (h, w):
                            f = cv2.resize(f, out_size)
                        out.write(f)

                    out.release()
                    st.session_state["live_capture_saved_path"] = outfile
                    #st.session_state["live_video_path"] = outfile
                    st.success(f"Zapisano fragment: {outfile}")
                    st.info("Analizuję zapisany fragment...")
                    res = run_analysis(outfile)
                    st.success("Analiza zakończona.")
                    st.session_state["live_results"] = res
        live_results = st.session_state.get("live_results")
        if live_results:
            service_valid = live_results.get("is_service_valid")
            error_info = live_results.get("error")
            height_valid = live_results.get("height_valid")
            angle_valid = live_results.get("angle_valid")
            visibility_valid = live_results.get("visibility_valid")
            height = live_results.get("throw_height_cm")
            angle = live_results.get("service_angle_deg")
            vis = live_results.get("visibility") or {}
            n_visible, n_all, percent = (vis.get("visible_frames"), vis.get("all_frames"), vis.get("percent"))

            if error_info:
                st.markdown(f"<h2 style='color: orange'>BŁĄD: {error_info}</h2>", unsafe_allow_html=True)
            else:
                if service_valid:
                    st.markdown("<h2 style='color: #1baf37'>✅ SERWIS PRAWIDŁOWY</h2>", unsafe_allow_html=True)
                else:
                    st.markdown("<h2 style='color: #e64646'>❌ SERWIS NIEPRAWIDŁOWY</h2>", unsafe_allow_html=True)

                def colorize_live(ok: bool) -> str:
                    return "#1baf37" if ok else "#e64646"

                st.markdown(
                    f"<span style='font-size: 1.2em; color: {colorize_live(height_valid)}'>"
                    f"Piłeczka wyrzucona na: {height if height is not None else '-'} cm</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<span style='font-size: 1.2em; color: {colorize_live(angle_valid)}'>"
                    f"Kąt serwisu: {angle if angle is not None else '-'}°</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<span style='font-size: 1.2em; color: {colorize_live(visibility_valid)}'>"
                    f"Widoczność serwisu: {n_visible if n_visible is not None else '-'} / "
                    f"{n_all if n_all is not None else '-'} klatek, {percent if percent is not None else '-'}%</span>",
                    unsafe_allow_html=True,
                )

            # ⬇⬇⬇ TU dopiero po wynikach pokazujesz spowolnione wideo
            wynik_mp4_path_live = os.path.join("wynik", "detekcja1", "output.mp4")
            if os.path.exists(wynik_mp4_path_live) and os.path.getsize(wynik_mp4_path_live) > 0:
                st.video(wynik_mp4_path_live)
            else:
                st.warning("Plik wynikowego wideo jest pusty lub nie został znaleziony.")

            # a poniżej obrazki
            obrazki_live = {
                "Start serwisu": os.path.join("wynik", "wykrywanie_serwisu", "start_serwisu.png"),
                "Koniec serwisu": os.path.join("wynik", "wykrywanie_konca_serwisu", "koniec_serwisu.png"),
                "Najwyższy punkt": os.path.join("wynik", "najwyzszy_punkt", "najwyzszy_punkt_serwisu.png"),
                "Kąt serwisu": os.path.join("wynik", "kąt_serwisu", "kat_serwisu.png"),
            }
            for opis, sciezka in obrazki_live.items():
                if os.path.exists(sciezka):
                    st.image(sciezka, caption=opis)
                else:
                    st.write(f"Brak pliku: {opis}")

            hidden_dir_live = "wynik/piłeczka_zasłonięta"
            if os.path.exists(hidden_dir_live):
                hidden_images_live = sorted([
                    os.path.join(hidden_dir_live, f)
                    for f in os.listdir(hidden_dir_live)
                    if f.lower().endswith((".png", ".jpg", ".jpeg"))
                ])
            else:
                hidden_images_live = []

            st.markdown("---")
            st.subheader("Klatki z zasłoniętą piłeczką")
            if not hidden_images_live:
                st.write("Brak zdjęć z zasłoniętą piłeczką.")
            else:
                cols_num = 3
                cols = st.columns(cols_num)
                for i, img_path in enumerate(hidden_images_live):
                    with cols[i % cols_num]:
                        img = Image.open(img_path)
                        st.image(img, caption=os.path.basename(img_path), use_container_width=True)
