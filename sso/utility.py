import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

import ephem
import datetime
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

"""
月の満ち欠けの様子をMatplotlibを使って画像表示する
初期化パラメタ：
    obs: type<ephem.Observer> インスタンス
    moon: type<ephem.Moon> インスタンス
"""
class MoonPhase:

    def __init__(self, obs, moon):
        self.obs = obs
        self.moon = moon
        logger.debug(f"MoonPhase: initialized.\nobs: {obs}\nmoon: {moon}")
        plt.ion()  # インタラクティブモードをオンにする

    def draw(self):
        logger.debug(f"MoonPhase: draw.")
        obs = self.obs
        moon = self.moon

        # 月と太陽の離角を計算
        moon.compute(self.obs)
        moon_elong = np.rad2deg(moon.elong)

        # 描画領域を準備
        fig = plt.figure(figsize=(5,5))
        ax = fig.add_subplot(projection='3d')

        # x, y, z軸の範囲設定
        ax.set_xlim([-1., 1.])
        ax.set_ylim([-1., 1.])
        ax.set_zlim([-1., 1.])

        # x, y, z軸や目盛を非表示に
        for a in [ax.xaxis, ax.yaxis, ax.zaxis]:
            a.set_ticklabels([])
            a._axinfo['grid']['linewidth'] = 0
            a._axinfo['tick']['linewidth'] = 0

        # 背景の x, y, z面を非表示に
        for a in [ax.xaxis, ax.yaxis, ax.zaxis]:
            a.line.set_linewidth(0)
            a.set_pane_color((0., 0., 0., 0.))

        # 背面を灰色に
        ax.set_facecolor('lightgray')

        # メッシュ状の球面 (u, v) を準備し、(x, y, z) 値を計算
        u, v = np.mgrid[0:2*np.pi:50j, 0:np.pi:25j] # u:接線方向　v:動経方向
        x = np.cos(u) * np.sin(v)
        y = np.sin(u) * np.sin(v)
        z = np.cos(v)

        # メッシュの球面に貼りつける色を準備（半分だけ黄色に）
        colors = np.zeros((50, 25, 3))
        for i in range(0, 25):
            for j in range(0, 25):
                colors[i][j][0] = 1
                colors[i][j][1] = 1
                colors[i][j][2] = 0

        # 球面をプロット
        ax.plot_surface(x, y, z, facecolors = colors, shade = False)

        # グラフを見る方向を設定
        ax.view_init(elev = 0, azim = moon_elong - 90)

        #plt.show()
        if not plt.get_fignums():
            self.fig = plt.figure()
        else:
            self.fig = plt.gcf()
            self.fig.clf() # 中身をクリアして再描画
        
        plt.draw()
        plt.pause(0.5)
        plt.gcf().canvas.flush_events() # 描画キューを強制消化
