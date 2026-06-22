import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QTabWidget, QSplitter, QTextEdit, QFileDialog,
    QFrame, QVBoxLayout
)
from PyQt5.QtCore import Qt

# 一、点类进行点数据存储
class Point:
    def __init__(self, n = None, x = None, y = None, h = None):
        self.n = n
        self.x = float(x)
        self.y = float(y)
        self.h = float(h)

# 二、凸包构建
def cross(a, b, c):
    return (b.x - a.x)*(c.y - a.y) - (b.y - a.y)*(c.x - a.x)
import math
# 凸包（Graham Scan）
def distance2(p1, p2):
    return (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2
def angle(p0, p):
    return math.atan2(p.y - p0.y, p.x - p0.x)
def find_stone(points):
    return min(points, key = lambda p:(p.y, p.x))
def graham_scan(points):
    if len(points) <= 2:
        return points
    # 1、找基点
    p0 = find_stone(points)
    # 2、去掉基点
    other = []
    for p in points:
        if p is not p0:
            other.append(p)
    # 3、排序
    other.sort(key = lambda p: (angle(p0, p), distance2(p0, p)))
    # 4、构建
    hull = []
    hull.append(p0)
    for p in other:
        while len(hull) >= 2 and cross(hull[-2], hull[-1], p) <= 0:
            hull.pop()
        hull.append(p)
    # 5、构建完成
    return hull

# 三、Delaunay三角网构建
class Triangle:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c
# 点p是否在三角形tri的外接圆内部或边上
def is_in(tri, p):
    a, b, c = tri.a, tri.b ,tri.c
    x1, x2, x3 = a.x, b.x, c.x
    y1, y2, y3 = a.y, b.y, c.y
    d = 2 * ((x3 - x1) * (y2 - y1) - (x2 - x1) * (y3 - y1))
    if abs(d) < 1e-12:
        return 0
    # 求外心
    x0 = ((y2 - y1) * (y3 ** 2 - y1 ** 2 + x3 ** 2 - x1 ** 2) - (y3 - y1) * (y2 ** 2 - y1 ** 2 + x2 ** 2 - x1 ** 2)) / d
    y0 = ((x2 - x1) * (x3 ** 2 - x1 ** 2 + y3 ** 2 - y1 ** 2) - (x3 - x1) * (x2 ** 2 - x1 ** 2 + y2 ** 2 - y1 ** 2)) / (-d)
    # 求半径平方
    r2 = (x0 - x1) ** 2 + (y0 - y1) ** 2
    # 点p到外心距离平方
    d2 = (p.x - x0) ** 2 + (p.y - y0) ** 2
    # 判断
    return d2 <= r2
# 构造凸包边
def get_hull_edges(hull):
    edges = []
    n = len(hull)
    for i in range(n):
        edges.append((hull[i], hull[(i+1) % n]))
    return edges
# 在t2的三角形中寻找所有公共边，并删除，将剩下的边放入边列表s
def find_shared_lines(t2):
    line_cnt = {}
    for tri in t2:
        line1 = tuple(sorted([tri.a, tri.b], key=lambda p: p.n))
        line2 = tuple(sorted([tri.b, tri.c], key=lambda p: p.n))
        line3 = tuple(sorted([tri.c, tri.a], key=lambda p: p.n))
        # 边计数
        for line in [line1, line2, line3]:
            line_cnt[line] = line_cnt.get(line, 0) + 1
    s = [line for line, cnt in line_cnt.items() if cnt == 1]
    return s

# 四、等高线生成
# 判断点p1和点p2是否重合
def same_xy(p1, p2, eps=1e-9):
    return abs(p1.x - p2.x) <= eps and abs(p1.y - p2.y) <= eps
# 去除等高线点列表中连续的重复点
def remove_consecutive_duplicate_points(points):
    if not points:
        return points
    cleaned = [points[0]]
    for pt in points[1:]:
        if not same_xy(pt, cleaned[-1]):
            cleaned.append(pt)
    return cleaned
# 将坐标点生成一个可作为字典键/集合元素的标识符
def point_key(pt, ndigits=9):
    return (round(pt.x, ndigits), round(pt.y, ndigits))
# 等高线与三角形边的交点计算
def edge_contour_intersection(p1, p2, h, eps=1e-9):
    d1 = p1.h - h
    d2 = p2.h - h
    # 1、三角形的这条边完全落在等高线上
    if abs(d1) <= eps and abs(d2) <= eps:
        return ("edge", (p1, p2))
    # 2、端点p1恰好在等高线上
    if abs(d1) <= eps:
        return ("point", p1)
    # 3、端点p2恰好在等高线上
    if abs(d2) <= eps:
        return ("point", p2)
    # 4、求交点，用Point类存储
    if d1 * d2 < 0:
        t = (h - p1.h) / (p2.h - p1.h)
        x = p1.x + t * (p2.x - p1.x)
        y = p1.y + t * (p2.y - p1.y)
        return ("point", Point(x=x, y=y, h=h))
    return None
# 高程为h的等高线穿过三角形tri所产生的所有线段
def triangle_contour_segments(tri, h):
    edges = [(tri.a, tri.b), (tri.b, tri.c), (tri.c, tri.a)]
    points = []
    segments = []
    for p1, p2 in edges:
        hit = edge_contour_intersection(p1, p2, h)
        if hit is None:
            continue
        kind, value = hit
        if kind == "edge":
            a, b = value
            if not same_xy(a, b):
                segments.append((a, b))
        else:
            # 可能出现重复点，比如某个顶点的高度和h是相同的，这并不是一个线段（上游过滤）
            if not any(same_xy(value, old) for old in points):
                points.append(value)
    if len(points) == 2:
        segments.append((points[0], points[1]))
    return segments
# 给一条边生成唯一标识（方向无关）
def edge_id(a, b):
    return tuple(sorted([a, b]))
# 从起点出发，沿着邻接图走出一条完整的等高线
def walk(start, adjacency, point_lookup, used_edges):
    line = [point_lookup[start]]
    prev = None
    current = start
    while True:
        next_key = None
        for nb in adjacency[current]:
            if nb == prev:
                # 不走回头路
                continue
            eid = edge_id(current, nb)
            # 不走已经走过的边
            if eid in used_edges:
                continue
            next_key = nb
            used_edges.add(eid)
            break
        # 开放等高线情况的出口
        if next_key is None:
            break
        line.append(point_lookup[next_key])
        prev, current = current, next_key
        # 闭合等高线情况的出口
        if current == start:
            break
    return remove_consecutive_duplicate_points(line)
# 把各三角形贡献的零散线段，拼接成完整的等高线。
def build_contours_from_segments(segments):
    unique_segments = []
    seen = set()
    for p1, p2 in segments:
        k1 = point_key(p1)
        k2 = point_key(p2)
        # 退化为点，双重保险（下游过滤）
        if k1 == k2:
            continue
        seg_key = tuple(sorted([k1, k2], key=lambda k: (k[0], k[1])))
        if seg_key in seen:
            continue
        seen.add(seg_key) # seen只是来判断是否重复的
        unique_segments.append((p1, p2)) # 存储最终结果
    adjacency = {}
    point_lookup = {}
    for p1, p2 in unique_segments:
        k1 = point_key(p1)
        k2 = point_key(p2)
        # 双向存储
        adjacency.setdefault(k1, []).append(k2)
        adjacency.setdefault(k2, []).append(k1)
        # key → Point 的映射表
        point_lookup[k1] = p1
        point_lookup[k2] = p2
    used_edges = set()
    contours = []
    # 第一轮：从端点出发（度为1），追踪开放等高线
    for start in [k for k, neighbors in adjacency.items() if len(neighbors) == 1]:
        nb = adjacency[start][0]
        if edge_id(start, nb) in used_edges:
            continue
        contours.append(walk(start, adjacency, point_lookup, used_edges))
    # 第二轮：从剩余未走边的任意点出发，追踪闭合等高线
    for start in adjacency:
        for nb in adjacency[start]:
            if edge_id(start, nb) in used_edges:
                continue
            contours.append(walk(start, adjacency, point_lookup, used_edges))
    return contours

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("构建不规则三角网进行等高线的自动绘制")
        self.setGeometry(100,100,850,600)
        self._init_ui()
    def _init_ui(self):
        # 菜单栏
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction("📂打开",self.open_file)
        file_menu.addAction("💾保存",self.save_file)
        file_menu.addSeparator()
        file_menu.addAction("❌关闭",self.close)
        menu_bar.addMenu("算法").addAction("🏃运行算法",self.process_data)
        menu_bar.addMenu("显示").addAction("🖥️显示结果",self.process_data)
        # 工具栏
        toolbar = self.addToolBar("工具栏")
        toolbar.addAction("📂打开",self.open_file)
        toolbar.addAction("🏃运行算法",self.process_data)
        # 状态栏
        self.status_label = QLabel("✅就绪")
        self.statusBar().addPermanentWidget(self.status_label,1)
        self.statusBar().setStyleSheet("background:#e8f4f0;")
        # 主区域
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._make_panel("原始数据"))
        splitter.addWidget(self._make_panel("运行结果"))
        splitter.setSizes([425, 425])
        layout.addWidget(splitter)
        notebook = QTabWidget()
        notebook.addTab(tab, "数据处理")
        self.setCentralWidget(notebook)
        self.original_text_area = self.panels[0]
        self.result_text_area = self.panels[1]
    def _make_panel(self, title):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel(title))
        text = QTextEdit()
        text.setStyleSheet("font-family:Consolas;font-size:10pt;")
        layout.addWidget(text)
        if not hasattr(self,'panels'):
            self.panels = []
        self.panels.append(text)
        return frame
    def open_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "打开文件", "", "文本文件(*.txt)")
        content = "\n".join(open(p, "r", encoding="utf-8").read() for p in paths)
        self.original_text_area.setText(content)
        self.result_text_area.setText("⌛️等待用户处理数据...")
        self.status_label.setText(f"✅打开{len(paths)}个文件,等待处理数据。")
    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存文件", "", "文本文件 (*.txt)")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.result_text_area.toPlainText())
        self.status_label.setText(f"✅已保存文件:{path}")
    def process_data(self):
        try:
            processed_lines = []
            lines = self.original_text_area.toPlainText().strip().split("\n")


            # 一、解析数据
            processed_lines.append("一、解析数据")
            points = []
            for line in lines:
                part = line.strip().split(",")
                points.append(Point(part[0], part[1], part[2], part[3]))
            processed_lines.append(f"散点总数:{len(points)}")


            # 二、凸包多边形的生成
            processed_lines.append("")
            processed_lines.append("二、凸包构建")
            hull = graham_scan(points)
            processed_lines.append(f"凸包点数量:{len(hull)}")


            # 三、不规则三角网的构建
            '''
            本文采用 Delaunay 三角剖分方法构建不规则三角网（TIN）
            以保证三角形尽可能接近等角性质，从而提高等高线插值精度
            '''
            # 1、生成初始三角网（有两种方法，这是其中一种，另一种为构造超级三角形）
            processed_lines.append("")
            processed_lines.append("三、不规则三角网的构建")
            # 删除离散点中的凸包点
            new_points = []
            for p in points:
                if p in hull:
                    continue
                new_points.append(p)
            # 取出离散点的一点，与凸包多边形的每一条边相连，构成多个三角形，并加入T1列表
            p = new_points[0]
            t1 = []
            n = len(hull)
            for i in range(n):
                a = hull[i]
                b = hull[(i+1) % n]
                t1.append(Triangle(p, a, b))
            # 2、遍历离散点，生成平面三角网
            for p in new_points[1:]: # 跳过第一个点，已用来构建初始三角网
                # 待插点p
                t2 = []
                for tri in t1:
                    if is_in(tri, p):
                        # 剪切到t2
                        t2.append(tri)
                for tri in t2:
                    t1.remove(tri)
                # 在t2的三角形中寻找所有公共边，并删除，将剩下的边放入边列表s
                s = find_shared_lines(t2)
                # 将s中的每条边的端点与p点链接组成新三角形，放入t1
                for line in s:
                    new_tri = Triangle(line[0], line[1], p)
                    t1.append(new_tri)
            # 此时t1即为所存的Delaunay三角形
            processed_lines.append(f"Delaunay三角形个数为:{len(t1)}")


            # 四、等高线的自动绘制
            processed_lines.append("")
            processed_lines.append("四、等高线的自动绘制")

            # 1、等高线的高程范围
            dh = 1
            zmax = max(points, key=lambda point: point.h).h
            zmin = min(points, key=lambda point: point.h).h
            hmin = math.floor(zmin) + dh
            hmax = math.floor(zmax)
            # 2、等高线追踪（生成）
            for h in [hmin + i * dh for i in range(int((hmax - hmin) / dh) + 1)]:
                segments = []
                for tri in t1:
                    segments.extend(triangle_contour_segments(tri, h))
                contour = build_contours_from_segments(segments)
                # 3、等高线构建结果输出
                processed_lines.append(f"高程为{h}的等高线共有{len(contour)}条")
                for ci, cl in enumerate(contour, 1):
                    processed_lines.append(f"第{ci}条等高线（{len(cl)}个点）:")
                    for pi, pt in enumerate(cl, 1):
                        processed_lines.append(f"点{pi}: ({pt.x:.4e}, {pt.y:.4e})")


            self.result_text_area.setText("\n".join(processed_lines))
            self.status_label.setText("✅数据处理成功！")
        except Exception as e:
            self.status_label.setText(f"❌数据处理失败:{e}")
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = App()
    window.show()
    sys.exit(app.exec_())