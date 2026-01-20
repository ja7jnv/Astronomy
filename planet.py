import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import datetime
import ephem
import Star_coordinate_cal as star_cal

mpl.rcParams['font.family'] = 'IPAGothic'

pi = 3.1415926535897932
#　　　　　　　　　　　　　太陽
me=ephem.Mercury()   #水星         88日
v1=ephem.Venus()      #金星         224.701 日
#　　　　　　　　　　　　　地球
ma=ephem.Mars()      #火星         686.980 日
j=ephem.Jupiter()    #木星         11.86155年
sa=ephem.Saturn()    #土星         29.53216 年
u1=ephem.Uranus()     #天王星       84.25301
n=ephem.Neptune()    #海王星       164.79 年
p=ephem.Pluto()      #冥王星       247.7406624 年


d=datetime.datetime.now(datetime.timezone.utc)
#d = datetime.datetime(2034, 2,3, 0, 0, 0, 0, tzinfo=datetime.timezone.utc)
#次の惑星直列の日（ただし、一直線になることはなく90度の範囲に集まる程度らしい）

fig = plt.figure()
ax = fig.add_subplot(projection='3d')

# 太陽Make data
u = np.linspace(0, 2 * np.pi, 100)
v = np.linspace(0, np.pi, 100)
x = 0.1 * np.outer(np.cos(u), np.sin(v))
y = 0.1 * np.outer(np.sin(u), np.sin(v))
z = 0.05 * np.outer(np.ones(np.size(u)), np.cos(v))

# Plot 太陽
ax.plot_surface(x, y, z, cmap='Reds')

#水星
xx_me =[]
yy_me =[]
zz_me =[]
d2 = d
for i in range(88):    #軌道データ
        me.compute(d2)
        aa2 = star_cal.star_coordinate(me.hlon / ephem.degree, me.hlat / ephem.degree, me.sun_distance)
        xx_me.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_me.append(aa2[1])
        zz_me.append(aa2[2])
        d2 += datetime.timedelta(days=1)# 1日を加算

ax.plot(xx_me, yy_me, zz_me,c='cyan', lw=0.5)
#金星
xx_v1 =[]
yy_v1 =[]
zz_v1 =[]
d2 = d
for i in range(224):    #軌道データ
        v1.compute(d2)
        aa2 = star_cal.star_coordinate(v1.hlon / ephem.degree, v1.hlat / ephem.degree, v1.sun_distance)
        xx_v1.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_v1.append(aa2[1])
        zz_v1.append(aa2[2])
        d2 += datetime.timedelta(days=1)# 1日を加算

ax.plot(xx_v1, yy_v1, zz_v1,c='tan', lw=0.5)

#地球(1AUの円) pyephemに地球のデータがない(地球が基準で作っているため？知らないだけか？)ので単純に円を描画しています。
r = 1
x = np.linspace(-r, r, 10000, endpoint=True)
y = np.sqrt(r ** 2 - x ** 2)

plt.plot(x, y, c='b', lw=0.5)
plt.plot(x, -y, c='b', lw=0.5)

#火星
xx_ma =[]
yy_ma =[]
zz_ma =[]
d2 = d
for i in range(344):    #軌道データ
        ma.compute(d2)
        aa2 = star_cal.star_coordinate(ma.hlon / ephem.degree, ma.hlat / ephem.degree, ma.sun_distance)
        xx_ma.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_ma.append(aa2[1])
        zz_ma.append(aa2[2])
        d2 += datetime.timedelta(days=2)# 2日を加算

ax.plot(xx_ma, yy_ma, zz_ma,c='gray', lw=0.5)
#木星
xx_j =[]
yy_j=[]
zz_j =[]
d2 = d
for i in range(434):    #軌道データ
        j.compute(d2)
        aa2 = star_cal.star_coordinate(j.hlon / ephem.degree, j.hlat / ephem.degree, j.sun_distance)
        xx_j.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_j.append(aa2[1])
        zz_j.append(aa2[2])
        d2 += datetime.timedelta(days=10)# 10日を加算

ax.plot(xx_j, yy_j, zz_j,c='coral', lw=0.5)


#土星
xx_sa =[]
yy_sa =[]
zz_sa =[]
d2 = d
for i in range(583):    #軌道データ
        sa.compute(d2)
        aa2 = star_cal.star_coordinate(sa.hlon / ephem.degree, sa.hlat / ephem.degree, sa.sun_distance)
        xx_sa.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_sa.append(aa2[1])
        zz_sa.append(aa2[2])
        d2 += datetime.timedelta(days=20)# 20日を加算

ax.plot(xx_sa, yy_sa, zz_sa,c='m', lw=0.5)

#天王星
xx_u1 =[]
yy_u1 =[]
zz_u1 =[]
d2 = d
for i in range(513):    #軌道データ
        u1.compute(d2)
        aa2 = star_cal.star_coordinate(u1.hlon / ephem.degree, u1.hlat / ephem.degree, u1.sun_distance)
        xx_u1.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_u1.append(aa2[1])
        zz_u1.append(aa2[2])
        d2 += datetime.timedelta(days=60)# 60日を加算

ax.plot(xx_u1, yy_u1, zz_u1,c='b', lw=0.5)

#海王星
xx_n =[]
yy_n =[]
zz_n =[]
d2 = d
for i in range(601):    #軌道データ
        n.compute(d2)
        aa2 = star_cal.star_coordinate(n.hlon / ephem.degree, n.hlat / ephem.degree, n.sun_distance)
        xx_n.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_n.append(aa2[1])
        zz_n.append(aa2[2])
        d2 += datetime.timedelta(days=100)# 100日を加算

ax.plot(xx_n, yy_n, zz_n,c='green', lw=0.5)

#冥王星
xx_p =[]
yy_p =[]
zz_p =[]
d2 = d
for i in range(223):    #軌道データ
        p.compute(d2)
        aa2 = star_cal.star_coordinate(p.hlon / ephem.degree, p.hlat / ephem.degree, p.sun_distance)
        xx_p.append(aa2[0]) # LISTに5分毎のlonを追加
        yy_p.append(aa2[1])
        zz_p.append(aa2[2])
        d2 += datetime.timedelta(days=365)# 365日を加算

ax.plot(xx_p, yy_p, zz_p,c='red', lw=0.5)

me.compute()
v1.compute()
#mo.compute()
ma.compute()
j.compute()
sa.compute()
u1.compute()
n.compute()
p.compute()

me_cal = star_cal.star_coordinate(me.hlon*180/pi, me.hlat*180/pi, me.sun_distance) #単位：度、度、AU
ax.scatter(xs=me_cal[0],zs=me_cal[1],ys=me_cal[2],zdir='y',c='cyan', s=10)
ax.text(me_cal[0],me_cal[1],me_cal[2]," 水星")

v1_cal = star_cal.star_coordinate(v1.hlon*180/pi, v1.hlat*180/pi, v1.sun_distance) #単位：度、度、AU
ax.scatter(xs=v1_cal[0],zs=v1_cal[1],ys=v1_cal[2],zdir='y',c='tan', s=10)
ax.text(v1_cal[0],v1_cal[1],v1_cal[2]," 金星")

ma_cal = star_cal.star_coordinate(ma.hlon*180/pi, ma.hlat*180/pi, ma.sun_distance) #単位：度、度、AU
ax.scatter(xs=ma_cal[0],zs=ma_cal[1],ys=ma_cal[2],zdir='y',c='gray', s=10)
ax.text(ma_cal[0],ma_cal[1],ma_cal[2]," 火星")

j_cal = star_cal.star_coordinate(j.hlon*180/pi, j.hlat*180/pi, j.sun_distance) #単位：度、度、AU
ax.scatter(xs=j_cal[0],zs=j_cal[1],ys=j_cal[2],zdir='y',c='coral', s=10)
ax.text(j_cal[0],j_cal[1],j_cal[2]," 木星")

sa_cal = star_cal.star_coordinate(sa.hlon*180/pi, sa.hlat*180/pi, sa.sun_distance) #単位：度、度、AU
ax.scatter(xs=sa_cal[0],zs=sa_cal[1],ys=sa_cal[2],zdir='y',c='m', s=10)
ax.text(sa_cal[0],sa_cal[1],sa_cal[2]," 土星")

u1_cal = star_cal.star_coordinate(u1.hlon*180/pi, u1.hlat*180/pi, u1.sun_distance) #単位：度、度、AU
ax.scatter(xs=u1_cal[0],zs=u1_cal[1],ys=u1_cal[2],zdir='y',c='b', s=10)
ax.text(u1_cal[0],u1_cal[1],u1_cal[2]," 天王星")

n_cal = star_cal.star_coordinate(n.hlon*180/pi, n.hlat*180/pi, n.sun_distance) #単位：度、度、AU
ax.scatter(xs=n_cal[0],zs=n_cal[1],ys=n_cal[2],zdir='y',c='green', s=10)
ax.text(n_cal[0],n_cal[1],n_cal[2]," 海王星")

p_cal = star_cal.star_coordinate(p.hlon*180/pi, p.hlat*180/pi, p.sun_distance) #単位：度、度、AU
ax.scatter(xs=p_cal[0],zs=p_cal[1],ys=p_cal[2],zdir='y',c='red', s=10)
ax.text(p_cal[0],p_cal[1],p_cal[2]," 冥王星")

plt.title("太陽系惑星と冥王星")
fig.tight_layout()
plt.show()

Star_coordinate_cal.py(同じフォルダに入れる)


import numpy as np

def star_coordinate(hlon, hlat, sun_distance):
    # hlon 太陽中心経度(度)　　西経の場合は(-)をつける
    # hlat 北緯(度)
    # sun_distance 太陽までの距離（AU）
    # 戻り値
    # x  x座標 (AU)
    # y  y座標 (AU)
    # z  z座標 (AU)

    if hlon < 0:
        hlon = 360 - hlon   # 西経の場合は東経に変換

    if hlon > 360:
        print("経度は360以下で入力する")

    if (hlat < -90) or (hlat > 90):
        print("経度は-90〜90の間で入力する")


    lat_f = 1        # 北緯の場合
    if hlat < 0:
        lat_f = -1   # 南緯の場合

    z = sun_distance * np.sin(np.radians(abs(hlat)))
    xy = sun_distance * np.cos(np.radians(abs(hlat)))
    z = z * lat_f

    if (hlon >= 0) and (hlon < 90):
        x = xy * np.cos(np.radians(90-hlon))
        y = -xy * np.sin(np.radians(90-hlon))
    elif (hlon >= 90) and (hlon < 180):
        x = xy * np.cos(np.radians(hlon-90))
        y = xy * np.sin(np.radians(hlon-90))
    elif (hlon >= 180) and (hlon < 270):
        x = -xy * np.cos(np.radians(270-hlon))
        y = xy * np.sin(np.radians(270-hlon))
    else:
        x = -xy * np.cos(np.radians(hlon-270))
        y = -xy * np.sin(np.radians(hlon-270))
    return (x,y,z)

Star_coordinate_cal.py(同じフォルダに入れる)


import numpy as np

def star_coordinate(hlon, hlat, sun_distance):
    # hlon 太陽中心経度(度)　　西経の場合は(-)をつける
    # hlat 北緯(度)
    # sun_distance 太陽までの距離（AU）
    # 戻り値
    # x  x座標 (AU)
    # y  y座標 (AU)
    # z  z座標 (AU)

    if hlon < 0:
        hlon = 360 - hlon   # 西経の場合は東経に変換

    if hlon > 360:
        print("経度は360以下で入力する")

    if (hlat < -90) or (hlat > 90):
        print("経度は-90〜90の間で入力する")


    lat_f = 1        # 北緯の場合
    if hlat < 0:
        lat_f = -1   # 南緯の場合

    z = sun_distance * np.sin(np.radians(abs(hlat)))
    xy = sun_distance * np.cos(np.radians(abs(hlat)))
    z = z * lat_f

    if (hlon >= 0) and (hlon < 90):
        x = xy * np.cos(np.radians(90-hlon))
        y = -xy * np.sin(np.radians(90-hlon))
    elif (hlon >= 90) and (hlon < 180):
        x = xy * np.cos(np.radians(hlon-90))
        y = xy * np.sin(np.radians(hlon-90))
    elif (hlon >= 180) and (hlon < 270):
        x = -xy * np.cos(np.radians(270-hlon))
        y = xy * np.sin(np.radians(270-hlon))
    else:
        x = -xy * np.cos(np.radians(hlon-270))
        y = -xy * np.sin(np.radians(hlon-270))
    return (x,y,z)
