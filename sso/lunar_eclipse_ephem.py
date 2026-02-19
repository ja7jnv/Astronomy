import ephem
import math

# --------------------------------------------
# 閾値（経験値：現実の月食に合わせて調整）
# --------------------------------------------

# 月食が起きる最大黄道緯度（約1.55°）
NODE_LIMIT = math.radians(1.55)

# 離角誤差で種類判定（rad）
TOTAL_LIMIT   = math.radians(0.50)   # 皆既
PARTIAL_LIMIT = math.radians(1.00)   # 部分
PENUM_LIMIT   = math.radians(1.80)   # 半影


# --------------------------------------------
# 月食判定
# --------------------------------------------

def lunar_eclipse_state(date):

    obs = ephem.Observer()
    obs.date = date
    obs.pressure = 0

    sun = ephem.Sun(obs)
    moon = ephem.Moon(obs)

    # 月の黄道緯度（ノードからの距離）
    beta = abs(moon.hlat)

    # ノードから遠ければ月食なし
    if beta > NODE_LIMIT:
        return None

    # 満月からのズレ（太陽月離角）
    sep = ephem.separation(sun, moon)
    d = abs(sep - math.pi)

    if d < TOTAL_LIMIT:
        return "皆既食"

    if d < PARTIAL_LIMIT:
        return "部分食"

    if d < PENUM_LIMIT:
        return "半影食"

    return None


# --------------------------------------------
# 満月周辺探索
# --------------------------------------------

def search_lunar_eclipses(start_year, years=5):

    obs = ephem.Observer()
    obs.date = f"{start_year}/1/1"

    end = ephem.Date(f"{start_year+years}/1/1")

    results = []

    while obs.date < end:

        full_moon = ephem.next_full_moon(obs.date)

        # 満月±8時間探索
        best = None
        t = full_moon - 8 * ephem.hour

        while t <= full_moon + 8 * ephem.hour:

            state = lunar_eclipse_state(t)

            if state:
                best = (t, state)
                break

            t += 5 * ephem.minute

        if best:
            results.append(best)

        # 次の満月へ（+30日不要）
        obs.date = ephem.next_full_moon(full_moon + 1)

    return results


# --------------------------------------------
# 実行
# --------------------------------------------

if __name__ == "__main__":

    res = search_lunar_eclipses(2026, years=4)

    print("=== lunar eclipses ===")
    for d, s in res:
        print(ephem.localtime(d), s)
