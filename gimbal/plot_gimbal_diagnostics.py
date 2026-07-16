import glob
import os
import matplotlib.pyplot as plt
import pandas as pd


def get_latest_csv():
    """Finds the most recently created gimbal CSV file in the current directory."""
    csv_files = glob.glob("gimbal_test_*.csv")
    if not csv_files:
        return None
    return max(csv_files, key=os.path.getctime)


def main():
    # --- DIAGNOSTIK-EINSTELLUNG ---
    # Setze dies auf True, um die gespiegelten Werte von Motor 2 für die Grafik zu korrigieren
    INVERT_M2_PLOT = True
    # ------------------------------

    # 1. Locate the latest file
    csv_file = get_latest_csv()
    if not csv_file:
        print("Error: No 'gimbal_test_*.csv' files found in this directory.")
        return

    print(f"Loading data for diagnostic plot: {csv_file}")
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()

    # 12-column fallback map
    expected_cols = [
        "time_ms",
        "loop_us",
        "target1",
        "angle1",
        "v_target1",
        "vel1",
        "vq1",
        "target2",
        "angle2",
        "v_target2",
        "vel2",
        "vq2",
    ]

    if "time_ms" not in df.columns or len(df.columns) < 12:
        df = pd.read_csv(csv_file, header=None)
        df = df[pd.to_numeric(df[0], errors="coerce").notnull()]
        df.columns = expected_cols[: len(df.columns)]

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()

    # Relative time calculation
    df["time_s"] = (df["time_ms"] - df["time_ms"].iloc[0]) / 1000.0

    # --- INVERTIERUNG FÜR MOTOR 2 ANWENDEN ---
    if INVERT_M2_PLOT:
        print("--> Info: Invertiere Motor 2 Werte (Target, Vel, Vq) für den Plot.")
        # Wir invertieren die Ist-Werte und Spannungen, damit sie grafisch zum Target passen
        df["vel2"] = -df["vel2"]
        df["vq2"] = -df["vq2"]
        # Falls auch das Target gespiegelt zum eigentlichen Sollwert läuft:
        # df["v_target2"] = -df["v_target2"]

    # 2. Setup plotting grid (3 rows, 1 column)
    plt.rcParams["font.family"] = "sans-serif"
    fig, (ax_vel, ax_vq, ax_loop) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    # Colors
    c_m1 = "#1f77b4"  # Blue
    c_m2 = "#2ca02c"  # Green
    c_dark = "#333333"

    # --- PANEL 1: Cascade Velocity tracking ---
    ax_vel.plot(
        df["time_s"],
        df["v_target1"],
        color=c_m1,
        linestyle="--",
        alpha=0.7,
        label="M1 Target Vel (sp)",
    )
    ax_vel.plot(
        df["time_s"], df["vel1"], color=c_m1, linewidth=1.5, label="M1 Actual Vel"
    )

    # Label-Zusatz für die Legende, falls invertiert
    m2_label_suffix = " (Inverted for Plot)" if INVERT_M2_PLOT else ""

    ax_vel.plot(
        df["time_s"],
        df["v_target2"],
        color=c_m2,
        linestyle="--",
        alpha=0.7,
        label=f"M2 Target Vel (sp)",
    )
    ax_vel.plot(
        df["time_s"],
        df["vel2"],
        color=c_m2,
        linewidth=1.5,
        label=f"M2 Actual Vel{m2_label_suffix}",
    )

    ax_vel.set_ylabel("Velocity (Deg/s)", fontsize=10, fontweight="bold")
    ax_vel.grid(True, linestyle=":", alpha=0.6)
    ax_vel.set_title(
        "Cascade Control: Outer Loop Velocity Targets vs. Inner Loop Velocity Response",
        fontsize=12,
        fontweight="bold",
    )
    ax_vel.legend(
        loc="upper right", frameon=True, facecolor="white", edgecolor="none", ncol=2
    )

    # --- PANEL 2: Control Effort (Vq Voltage) ---
    ax_vq.plot(
        df["time_s"],
        df["vq1"],
        color=c_m1,
        linewidth=1.5,
        alpha=0.8,
        label="M1 Voltage (Vq)",
    )
    ax_vq.plot(
        df["time_s"],
        df["vq2"],
        color=c_m2,
        linewidth=1.5,
        alpha=0.8,
        label=f"M2 Voltage (Vq){m2_label_suffix}",
    )
    ax_vq.set_ylabel("Effort (Volts)", fontsize=10, fontweight="bold")
    ax_vq.grid(True, linestyle=":", alpha=0.6)
    ax_vq.set_title(
        "Control Effort: Quadrature Voltage (Vq) Over Time",
        fontsize=12,
        fontweight="bold",
    )
    ax_vq.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="none")

    # --- PANEL 3: MCU Loop Execution Time Overhead ---
    avg_loop = df["loop_us"].mean()

    ax_loop.plot(
        df["time_s"],
        df["loop_us"],
        color=c_dark,
        linewidth=1.2,
        label=f"Loop Exec Time (Avg: {avg_loop:.1f} \u03bcs)",
    )
    ax_loop.axhline(
        y=avg_loop, color="red", linestyle=":", alpha=0.8, label="Mean Loop Latency"
    )
    ax_loop.set_xlabel("Time (Seconds)", fontsize=11, fontweight="bold")
    ax_loop.set_ylabel("Execution Time (\u03bcs)", fontsize=10, fontweight="bold")
    ax_loop.grid(True, linestyle=":", alpha=0.6)
    ax_loop.set_title(
        "Microcontroller Overhead: Loop Execution Duration",
        fontsize=12,
        fontweight="bold",
    )
    ax_loop.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="none")

    # Adjust layout
    plt.tight_layout()

    # Save image
    output_image = csv_file.replace(".csv", "_diagnostics.png")
    plt.savefig(output_image, dpi=300, bbox_inches="tight")
    print(f"Diagnostic plot saved successfully as: {output_image}")
    plt.show()


if __name__ == "__main__":
    main()
