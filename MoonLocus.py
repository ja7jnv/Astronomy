import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_body
import astropy.units as u

# ==========================
# 観測地点
# ==========================
lat = 35.681236
lon = 139.767125
height = 40

# ==========================
# 時刻
# ==========================
start = Time(datetime.utcnow())
minutes = np.arange(0, 24*60, 2)
times = start + minutes * u.minute

# ==========================
# 観測地点
# ==========================
location = EarthLocation(
    lat=lat*u.deg,
    lon=lon*u.deg,
    height=height*u.m
)

altaz = AltAz(obstime=times, location=location)

# ==========================
# 月の位置
# ==========================
moon = get_body("moon", times, location)
moon_altaz = moon.transform_to(altaz)

alt = moon_altaz.alt.to(u.deg).value
az  = moon_altaz.az.to(u.deg).value

# 地平線上のみ
mask = alt > 0
alt = alt[mask]
az  = az[mask]

# 東→南→西 に制限
mask2 = (az > 60) & (az < 300)
alt = alt[mask2]
az  = az[mask2]

# ==========================
# 半球断面への投影
# ==========================
alt_r = np.deg2rad(alt)
az_r  = np.deg2rad(az)

x = np.cos(alt_r) * np.sin(az_r)
y = np.sin(alt_r)

# ==========================
# 描画
# ==========================
plt.figure(figsize=(8, 5))

# 天球半円
theta = np.linspace(0, np.pi, 300)
plt.plot(np.cos(theta), np.sin(theta), color="black")

# 地平線
plt.plot([-1, 1], [0, 0], linestyle="--", color="gray")

# 月の通り道
plt.plot(x, y, linewidth=3)

# 方位ラベル
plt.text(-1.05, -0.05, "East", ha="center")
plt.text( 0.00, -0.05, "South", ha="center")
plt.text( 1.05, -0.05, "West", ha="center")

plt.axis("equal")
plt.axis("off")
plt.title("How the Moon Moves Across the Sky")

plt.show()

