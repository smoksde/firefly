import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

def get_latest_csv():
    """Finds the most recently created gimbal CSV file in the current directory."""
    csv_files = glob.glob("gimbal_test_*.csv")
    if not csv_files:
        return None
    return max(csv_files, key=os.path.getctime)

def main():
    # 1. Locate the latest file
    csv_file = get_latest_csv()
    if not csv_file:
        print("Error: No 'gimbal_test_*.csv' files found in this directory.")
        return
    
    print(f"Loading data from: {csv_file}")
    
    # Read the CSV. We try to read headers, but if they are missing/corrupted we handle it.
    df = pd.read_csv(csv_file)
    
    # Clean up column names (strip trailing/leading spaces if any)
    df.columns = df.columns.str.strip()
    
    # Fallback Mechanism: If headers are missing or mismatched, assign them manually based on position
    expected_cols = ['time_ms', 'target1', 'angle1', 'vel1', 'target2', 'angle2', 'vel2']
    if 'time_ms' not in df.columns or len(df.columns) < 7:
        print("Warning: Standard CSV headers not found or incomplete. Re-mapping columns by position...")
        # Re-read without assuming the first row is a header
        df = pd.read_csv(csv_file, header=None)
        # Drop rows that are purely text (like the printed header if it got caught halfway)
        df = df[pd.to_numeric(df[0], errors='coerce').notnull()]
        df.columns = expected_cols[:len(df.columns)]
        
    # Ensure all data is numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()

    # 2. Pre-process timestamps to relative seconds
    df['time_s'] = (df['time_ms'] - df['time_ms'].iloc[0]) / 1000.0

    # 3. Setup the plot style
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    
    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # --- MOTOR 1 (Roll) Plot ---
    color_actual_1 = '#1f77b4' # Tech Blue
    color_target = '#d62728'   # Crimson Red
    
    ax1.plot(df['time_s'], df['target1'], color=color_target, linestyle='--', linewidth=1.5, label='Target 1')
    ax1.plot(df['time_s'], df['angle1'], color=color_actual_1, linewidth=2.0, label='Actual Angle 1')
    ax1.set_ylabel('Angle (Degrees)', color='black', fontsize=11, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.set_title('Motor 1 (Roll) Dynamics', fontsize=13, fontweight='bold', pad=10)
    
    # Right Axis: Velocity
    ax2 = ax1.twinx()
    color_vel = '#7f7f7f'      # Muted Gray
    ax2.plot(df['time_s'], df['vel1'], color=color_vel, linestyle=':', alpha=0.5, linewidth=1.2, label='Velocity 1')
    ax2.set_ylabel('Velocity (Deg/s)', color=color_vel, fontsize=10)
    ax2.tick_params(axis='y', labelcolor=color_vel)
    
    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', frameon=True, facecolor='white', edgecolor='none')

    # --- MOTOR 2 (Pitch) Plot ---
    color_actual_2 = '#2ca02c' # Forest Green
    
    ax3.plot(df['time_s'], df['target2'], color=color_target, linestyle='--', linewidth=1.5, label='Target 2')
    ax3.plot(df['time_s'], df['angle2'], color=color_actual_2, linewidth=2.0, label='Actual Angle 2')
    ax3.set_xlabel('Time (Seconds)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Angle (Degrees)', color='black', fontsize=11, fontweight='bold')
    ax3.tick_params(axis='y', labelcolor='black')
    ax3.grid(True, linestyle=':', alpha=0.6)
    ax3.set_title('Motor 2 (Pitch) Dynamics', fontsize=13, fontweight='bold', pad=10)
    
    # Right Axis: Velocity
    ax4 = ax3.twinx()
    ax4.plot(df['time_s'], df['vel2'], color=color_vel, linestyle=':', alpha=0.5, linewidth=1.2, label='Velocity 2')
    ax4.set_ylabel('Velocity (Deg/s)', color=color_vel, fontsize=10)
    ax4.tick_params(axis='y', labelcolor=color_vel)
    
    # Combine legends
    lines3, labels3 = ax3.get_legend_handles_labels()
    lines4, labels4 = ax4.get_legend_handles_labels()
    ax3.legend(lines3 + lines4, labels3 + labels4, loc='upper right', frameon=True, facecolor='white', edgecolor='none')

    # 4. Final Layout and Save
    plt.tight_layout()
    
    output_image = csv_file.replace('.csv', '.png')
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"Plot saved successfully as: {output_image}")
    plt.show()

if __name__ == "__main__":
    main()