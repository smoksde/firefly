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
    # Auf True setzen, um die Inversion von Motor 2 im Plot auszugleichen
    INVERT_M2_PLOT = True
    # ------------------------------

    csv_file = get_latest_csv()
    if not csv_file:
        print("Error: No 'gimbal_test_*.csv' files found.")
        return

    print(f"Loading data for Phase Space analysis: {csv_file}")
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

    # --- INVERTIERUNG VOR DER FEHLERBERECHNUNG ANWENDEN ---
    if INVERT_M2_PLOT:
        print(
            "--> Info: Invertiere M2 Winkel und Geschwindigkeit zur Fehlerberechnung."
        )
        df["angle2"] = -df["angle2"]
        df["vel2"] = -df["vel2"]

    # Calculate dynamic position error (Target - Actual)
    df["error1"] = df["target1"] - df["angle1"]
    df["error2"] = df["target2"] - df["angle2"]

    # Set up the plot
    plt.rcParams["font.family"] = "sans-serif"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # --- MOTOR 1 PHASE SPACE ---
    ax1.plot(
        df["error1"],
        df["vel1"],
        color="#1f77b4",
        alpha=0.8,
        linewidth=1.5,
        label="Trajectory",
    )
    ax1.scatter(
        df["error1"].iloc[0],
        df["vel1"].iloc[0],
        color="green",
        s=100,
        zorder=5,
        label="Start",
    )
    ax1.scatter(
        df["error1"].iloc[-1],
        df["vel1"].iloc[-1],
        color="red",
        marker="X",
        s=150,
        zorder=5,
        label="End",
    )

    ax1.axhline(0, color="black", linestyle=":", alpha=0.5)
    ax1.axvline(0, color="black", linestyle=":", alpha=0.5)

    ax1.set_title(
        "Motor 1 Phase Portrait\n(Yaw Stability)", fontsize=12, fontweight="bold"
    )
    ax1.set_xlabel("Position Error (Degrees)", fontweight="bold")
    ax1.set_ylabel("Shaft Velocity (Deg/s)", fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.5)
    ax1.legend()

    # --- MOTOR 2 PHASE SPACE ---
    m2_title_suffix = " (Inverted)" if INVERT_M2_PLOT else ""

    ax2.plot(
        df["error2"],
        df["vel2"],
        color="#2ca02c",
        alpha=0.8,
        linewidth=1.5,
        label="Trajectory",
    )
    ax2.scatter(
        df["error2"].iloc[0],
        df["vel2"].iloc[0],
        color="green",
        s=100,
        zorder=5,
        label="Start",
    )
    ax2.scatter(
        df["error2"].iloc[-1],
        df["vel2"].iloc[-1],
        color="red",
        marker="X",
        s=150,
        zorder=5,
        label="End",
    )

    ax2.axhline(0, color="black", linestyle=":", alpha=0.5)
    ax2.axvline(0, color="black", linestyle=":", alpha=0.5)

    ax2.set_title(
        f"Motor 2 Phase Portrait{m2_title_suffix}\n(Roll Stability)",
        fontsize=12,
        fontweight="bold",
    )
    ax2.set_xlabel("Position Error (Degrees)", fontweight="bold")
    ax2.set_ylabel("Shaft Velocity (Deg/s)", fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.5)
    ax2.legend()

    plt.tight_layout()
    output_image = csv_file.replace(".csv", "_phasespace.png")
    plt.savefig(output_image, dpi=300, bbox_inches="tight")
    print(f"Phase space portrait saved as: {output_image}")
    plt.show()


if __name__ == "__main__":
    main()
