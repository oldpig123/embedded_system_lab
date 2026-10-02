import socket
import threading
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

sensor_data = {
    'AX': [], 'AY': [], 'AZ': [],
    'GX': [], 'GY': [], 'GZ': [],
    'T': [], 'H': [], 'P': [],
    'MX': [], 'MY': [], 'MZ': [],
}
motion_events = []
MAX_POINTS = 100
EXPECTED_KEYS = 12

def receive_data():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 8002))

    server.listen(1)
    print("Server listening")

    while True:
        conn, addr = server.accept()
        while True:
            data = conn.recv(4096)
            if not data:
                break
            data = data.decode(encoding='utf-8').replace('\x00', '').strip()
            for line in data.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line == "MOTION":
                    motion_events.append(len(sensor_data['AX']))
                    print(">>> MOTION detected! <<<")
                    continue
                try:
                    parts = line.split(' ')
                    if len(parts) != EXPECTED_KEYS:
                        continue
                    for part in parts:
                        key, val = part.split(':')
                        sensor_data[key].append(float(val))
                    if len(sensor_data['AX']) > MAX_POINTS:
                        for key in sensor_data:
                            sensor_data[key].pop(0)
                        motion_events[:] = [i - 1 for i in motion_events if i - 1 >= 0]
                except (ValueError, IndexError, KeyError):
                    continue
        conn.close()
    server.close()

def update(frame):
    for key, line_obj in lines.items():
        line_obj.set_data(range(len(sensor_data[key])), sensor_data[key])

    for vl in vlines:
        vl.remove()
    vlines.clear()
    for idx in motion_events:
        vl = ax_acc.axvline(x=idx, color='red', linestyle='--', alpha=0.7)
        vlines.append(vl)

    ax_acc.set_title(f'Accelerometer (mg)  |  Motion: {len(motion_events)}')

    t_val = sensor_data['T'][-1] if sensor_data['T'] else 0
    h_val = sensor_data['H'][-1] if sensor_data['H'] else 0
    p_val = sensor_data['P'][-1] if sensor_data['P'] else 0
    ax_env.set_title(f'Temp: {t_val:.1f} °C  |  Humidity: {h_val:.1f} %  |  Pressure: {p_val:.1f} hPa')

    for a in axes:
        a.relim()
        a.autoscale_view()

t = threading.Thread(target=receive_data)
t.daemon = True
t.start()

vlines = []

fig, axes = plt.subplots(2, 2, figsize=(16, 9))
ax_acc = axes[0][0]
ax_gyro = axes[0][1]
ax_mag = axes[1][0]
ax_env = axes[1][1]
fig.suptitle('B-L475E-IOT01A Sensor Dashboard', fontsize=14)
fig.subplots_adjust(hspace=0.45, wspace=0.3, top=0.92, bottom=0.06, left=0.07, right=0.97)

lines = {}

lines['AX'], = ax_acc.plot([], [], 'r', label='X')
lines['AY'], = ax_acc.plot([], [], 'g', label='Y')
lines['AZ'], = ax_acc.plot([], [], 'b', label='Z')
ax_acc.legend(loc='upper right')
ax_acc.set_ylabel('mg')
ax_acc.set_title('Accelerometer (mg)')

lines['GX'], = ax_gyro.plot([], [], 'r', label='X')
lines['GY'], = ax_gyro.plot([], [], 'g', label='Y')
lines['GZ'], = ax_gyro.plot([], [], 'b', label='Z')
ax_gyro.legend(loc='upper right')
ax_gyro.set_ylabel('mdps')
ax_gyro.set_title('Gyroscope (mdps)')

lines['MX'], = ax_mag.plot([], [], 'r', label='X')
lines['MY'], = ax_mag.plot([], [], 'g', label='Y')
lines['MZ'], = ax_mag.plot([], [], 'b', label='Z')
ax_mag.legend(loc='upper right')
ax_mag.set_ylabel('mGauss')
ax_mag.set_title('Magnetometer (mGauss)')

lines['T'], = ax_env.plot([], [], 'r', label='Temp (°C)')
lines['H'], = ax_env.plot([], [], 'b', label='Humidity (%)')
ax_env.legend(loc='upper right')
ax_env.set_title('Environment')

axes = axes.flatten()
ani = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
plt.show()
plt.close()
