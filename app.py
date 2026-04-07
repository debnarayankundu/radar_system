import streamlit as st
import numpy as np


# ------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------
st.set_page_config(page_title=" antenna applications", layout="wide")

# ------------------------------------------------
# 🎨 CSS (UNCHANGED)
# ------------------------------------------------
st.markdown("""
<style>
.main {
    background: linear-gradient(135deg, #1f4037, #99f2c8);
}
h1 {
    text-align: center;
    color: white;
}
.card {
    background: rgba(255,255,255,0.9);
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    margin-bottom: 20px;
}
[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 12px;
}
[data-testid="stMetricValue"] {
    color: black !important;
    font-size: 28px !important;
    font-weight: bold;
}
[data-testid="stMetricLabel"] {
    color: #444 !important;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f2027, #203a43, #2c5364);
    color: white;
}
.footer {
    background: white;
    padding: 25px;
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

st.title("📡 Antenna applications")
st.markdown("---")

# ------------------------------------------------
# MODE SELECTOR
# ------------------------------------------------
mode = st.sidebar.selectbox("Select Mode", ["Antenna Design", "phased array detection"])


# =================================================
# 🔵 MODE 1: YOUR ORIGINAL CODE (UNCHANGED)
# =================================================
if mode == "Antenna Design":

    st.sidebar.title("⚙️ Controls")

    antenna_type = st.sidebar.selectbox(
        "Antenna Type",
        ["Microstrip Patch", "UPA", "ULA"]
    )

    freq = st.sidebar.number_input("Frequency (GHz)", value=3.5)
    h = st.sidebar.number_input("Substrate Height (mm)", value=1.6) * 1e-3

    materials = {
        "FR4": {"er": 4.4, "loss": 0.02},
        "Rogers RT5880": {"er": 2.2, "loss": 0.0009},
        "Rogers RT6006": {"er": 6.15, "loss": 0.0027},
        "Air": {"er": 1.0, "loss": 0.0}
    }

    mat_choice = st.sidebar.selectbox("Substrate Material", list(materials.keys()))
    er = materials[mat_choice]["er"]

    metals = {
        "Copper": 5.8e7,
        "Aluminum": 3.5e7,
        "Gold": 4.1e7
    }

    metal_choice = st.sidebar.selectbox("Metal", list(metals.keys()))
    conductivity = metals[metal_choice]

    c = 3e8
    f = freq * 1e9
    wavelength = c / f

    W = (c/(2*f))*np.sqrt(2/(er+1))
    eeff = ((er+1)/2)+((er-1)/2)*(1+12*h/W)**(-0.5)

    deltaL = 0.412*h*((eeff+0.3)*(W/h+0.264))/((eeff-0.258)*(W/h+0.8))
    L = (c/(2*f*np.sqrt(eeff))) - 2*deltaL

    Rin = 90*(er**2)/(er-1)*(L/W)

    def microstrip_width(Z0, er, h):
        A = Z0/60*np.sqrt((er+1)/2)
        return (8*np.exp(A))/(np.exp(2*A)-2)*h

    Wf = microstrip_width(50, er, h)
    Lf = wavelength/(4*np.sqrt(eeff))
    y0 = (L/np.pi)*np.arccos(np.sqrt(50/Rin))

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📐 Patch")

    c1,c2,c3 = st.columns(3)
    c1.metric("Width (mm)", round(W*1000,2))
    c2.metric("Length (mm)", round(L*1000,2))
    c3.metric("εeff", round(eeff,3))

    c4,c5 = st.columns(2)
    c4.metric("ΔL (mm)", round(deltaL*1000,3))
    c5.metric("Rin (Ω)", round(Rin,2))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🔌 Feed")

    c6,c7,c8 = st.columns(3)
    c6.metric("Wf (mm)", round(Wf*1000,2))
    c7.metric("Lf (mm)", round(Lf*1000,2))
    c8.metric("Inset y0 (mm)", round(y0*1000,2))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📡 Export to CST")

    def cst_macro():
        return f'''
Sub Main()

With Material
.Name "{mat_choice}"
.Epsilon "{er}"
.Create
End With

End Sub
'''

    st.download_button("Download CST Macro", cst_macro(), "antenna.bas")

    st.markdown("<div class='footer'>", unsafe_allow_html=True)
    st.write("All geometry values are displayed in millimeters (mm).")
    st.markdown("</div>", unsafe_allow_html=True)

# =================================================
# 🔴 MODE 2: CSI MODULE (ANGLE + RANGE UPGRADE)
# =================================================
else:

    import plotly.graph_objects as go

    st.sidebar.title("📡 CSI Controls")

    # ---------------- ARRAY TYPE ----------------
    array_type = st.sidebar.selectbox("Array Type", ["ULA", "UPA"])

    if array_type == "ULA":
        N = st.sidebar.number_input("Number of Antennas", 2, 32, 8)
    else:
        Nx = st.sidebar.number_input("Nx", 2, 16, 4)
        Ny = st.sidebar.number_input("Ny", 2, 16, 4)
        N = Nx * Ny

    # ---------------- INPUT ----------------
    file = st.file_uploader("Upload CSI (.npy only)")

    if file is None:
        st.warning("Upload CSI file")
        st.stop()

    try:
        H = np.load(file)
    except:
        st.error("Invalid file")
        st.stop()

    st.write("### 📊 CSI Shape:", H.shape)

    # ------------------------------------------------
    # CONSTANTS
    # ------------------------------------------------
    c = 3e8
    f = 3.5e9
    lam = c / f
    d = lam / 2
    k = 2 * np.pi / lam

    # =================================================
    # 📏 RANGE ESTIMATION (NEW 🔥)
    # =================================================
    st.subheader("📏 Range Estimation")

    bandwidth = st.sidebar.number_input("Bandwidth (GHz)", value=20.0) * 1e6

    if H.ndim == 2:
        # (F, N)
        h_tau = np.fft.ifft(H, axis=0)
        power_delay = np.abs(h_tau).mean(axis=1)

    elif H.ndim == 3:
        # (F, Nx, Ny)
        h_tau = np.fft.ifft(H, axis=0)
        power_delay = np.abs(h_tau).mean(axis=(1,2))

    else:
        st.error("Unsupported CSI format")
        st.stop()

    power_delay /= np.max(power_delay)

    delay_idx = np.argmax(power_delay)
    tau = delay_idx / bandwidth
    range_est = (c * tau) / 2

    st.success(f"Estimated Range: {range_est:.2f} meters")

    st.line_chart(power_delay)

    # =================================================
    # 📡 ANGLE DETECTION (SAME LOGIC)
    # =================================================
    st.subheader("📡 Angle Detection")

    if array_type == "ULA":

        # Use first subcarrier for angle
        H_use = H[0] if H.ndim == 2 else H[0].flatten()

        theta_scan = np.linspace(-90, 90, 200)
        response = []

        for angle in theta_scan:
            theta = np.radians(angle)
            steering = np.exp(1j * k * np.arange(len(H_use)) * d * np.sin(theta))
            val = np.abs(np.sum(H_use * np.conj(steering)))
            response.append(val)

        response = np.array(response)
        response /= np.max(response)

        angle_est = theta_scan[np.argmax(response)]
        st.success(f"Detected Angle: {angle_est:.2f}°")

        st.line_chart(response)

    else:

        H_use = H[0]  # first subcarrier

        theta_scan = np.linspace(0, 90, 40)
        phi_scan = np.linspace(-90, 90, 40)

        TH, PH = np.meshgrid(theta_scan, phi_scan)
        response = np.zeros_like(TH)

        for i in range(len(theta_scan)):
            for j in range(len(phi_scan)):

                theta = np.radians(theta_scan[i])
                phi = np.radians(phi_scan[j])

                val = 0

                for m in range(Nx):
                    for n in range(Ny):

                        phase = k * (
                            m*d*np.sin(theta)*np.cos(phi) +
                            n*d*np.sin(theta)*np.sin(phi)
                        )

                        val += H_use[m,n] * np.exp(-1j*phase)

                response[j,i] = np.abs(val)

        response /= np.max(response)

        idx = np.unravel_index(np.argmax(response), response.shape)

        theta_est = theta_scan[idx[1]]
        phi_est = phi_scan[idx[0]]

        st.success(f"θ: {theta_est:.2f}° | φ: {phi_est:.2f}°")

        fig = go.Figure(data=[go.Surface(z=response, x=TH, y=PH)])
        st.plotly_chart(fig, use_container_width=True)
