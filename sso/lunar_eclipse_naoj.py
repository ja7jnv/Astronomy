import numpy as np
from skyfield.api import load
from datetime import datetime, timedelta

# --------------------------------------------
# JPL ephemeris (DE421: 軽量 / DE440:最高精度)
# --------------------------------------------
ts = load.timescale()
eph = load('de421.bsp')   # 初回のみDL

earth = eph['earth']
moon  = eph['moon']
sun   = eph['sun']


# --------------------------------------------
# 月食判定（地心幾何）
# --------------------------------------------
def lunar_eclipse_status(t):
    """
    地球中心から見た太陽・月方向で
    月が地球影に入るか判定
    """

    e = earth.at(t)

    # 地球→月, 地球→太陽 ベクトル
    r_m = e.observe(moon).position.km
    r_s = e.observe(sun).position.km

    # 距離
    d_m = np.linalg.norm(r_m)
    d_s = np.linalg.norm(r_s)

    # 単位ベクトル
    u_m = r_m / d_m
    u_s = r_s / d_s

    # 太陽と反対方向（影軸）
    shadow_axis = -u_s

    # 月と影軸の角距離
    cos_sep = np.dot(u_m, shadow_axis)
    sep = np.arccos(cos_sep)

    # ---- 天体半径 ----
    R_earth = 6378.137
    R_sun   = 696000.0

    # ---- 影円錐モデル ----
    # umbra半角
    theta_u = np.arctan((R_earth - R_sun * d_m / d_s) / d_m)

    # penumbra半角
    theta_p = np.arctan((R_earth + R_sun * d_m / d_s) / d_m)

    if sep < abs(theta_u):
        return "皆既食"

    if sep < abs(theta_u) + 0.0045:   # 月半径補正
        return "部分食"

    if sep < abs(theta_p) + 0.0045:
        return "半影食"

    return None


# --------------------------------------------
# 月食探索（時間スキャン）
# --------------------------------------------
def search_lunar_eclipses(start_year, years=5, step_minutes=5):

    start = datetime(start_year, 1, 1)
    end   = datetime(start_year + years, 1, 1)

    current = start
    prev_state = None
    results = []

    while current < end:

        t = ts.utc(current.year, current.month, current.day,
                   current.hour, current.minute)

        state = lunar_eclipse_status(t)

        # 状態変化のみ記録
        if state != prev_state and state is not None:
            results.append((current, state))

        prev_state = state
        current += timedelta(minutes=step_minutes)

    return results


# --------------------------------------------
# 実行例
# --------------------------------------------
if __name__ == "__main__":

    res = search_lunar_eclipses(2026, years=2)

    print("=== lunar eclipse candidates ===")
    for d, s in res:
        print(d, s)
