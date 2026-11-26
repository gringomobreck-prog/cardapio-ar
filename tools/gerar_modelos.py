"""Gera os modelos 3D (GLB) dos pratos em escala real.
Unidade: metros. Eixo Y para cima. Origem no centro da base (superfície da mesa).
Uso: python3 tools/gerar_modelos.py site/models
"""
import json, math, struct, sys, os
import numpy as np

rng = np.random.default_rng(7)

# ---------------- materiais ----------------
MAT = {}
def mat(name, rgb, rough=0.7, metal=0.0):
    MAT[name] = dict(name=name, rgb=rgb, rough=rough, metal=metal)
    return name

def hexrgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return [x ** 2.2 for x in c]  # sRGB -> linear

# ---------------- malhas ----------------
class Mesh:
    def __init__(self, P, N, I, m):
        self.P = np.asarray(P, np.float32); self.N = np.asarray(N, np.float32)
        self.I = np.asarray(I, np.uint32); self.m = m
    def xf(self, s=(1, 1, 1), r=(0, 0, 0), t=(0, 0, 0)):
        s = np.array(s, float); rx, ry, rz = r
        Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
        Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
        Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
        R = Ry @ Rx @ Rz
        P = (self.P * s) @ R.T + np.array(t)
        N = (self.N / s) @ R.T
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
        return Mesh(P, N, self.I, self.m)

def lathe(profile, m, seg=64, wobble=None, crease=50):
    """Revolve um perfil [(r, y), ...] (anti-horário: base, lado, topo)."""
    pr = np.array(profile, float)
    segs = len(pr) - 1
    sn = []
    for i in range(segs):
        dr, dy = pr[i + 1] - pr[i]
        n = np.array([dy, -dr]); n /= np.linalg.norm(n) + 1e-12; sn.append(n)
    cosc = math.cos(math.radians(crease))
    P, N, I = [], [], []
    th = np.linspace(0, 2 * math.pi, seg + 1)
    for i in range(segs):
        ends = []
        for j, k in ((i, 0), (i + 1, 1)):
            n = sn[i]
            nb = sn[i - 1] if (k == 0 and i > 0) else (sn[i + 1] if (k == 1 and i < segs - 1) else None)
            if nb is not None and np.dot(n, nb) > cosc:
                n = (n + nb); n /= np.linalg.norm(n)
            ends.append((pr[j], n))
        base = len(P)
        for (r, y), (nr, ny) in ends:
            for t in th:
                w = wobble(t, y) if wobble else 1.0
                P.append([r * w * math.cos(t), y, r * w * math.sin(t)])
                N.append([nr * math.cos(t), ny, nr * math.sin(t)])
        for a in range(seg):
            i0 = base + a; i1 = i0 + 1; j0 = base + seg + 1 + a; j1 = j0 + 1
            I += [i0, j0, i1, i1, j0, j1]
    return Mesh(P, N, I, m)

def sphere(m, la=14, lo=20):
    P, N, I = [], [], []
    for i in range(la + 1):
        v = math.pi * i / la
        for j in range(lo + 1):
            u = 2 * math.pi * j / lo
            p = [math.sin(v) * math.cos(u), math.cos(v), math.sin(v) * math.sin(u)]
            P.append(p); N.append(p)
    for i in range(la):
        for j in range(lo):
            a = i * (lo + 1) + j; b = a + lo + 1
            I += [a, a + 1, b, a + 1, b + 1, b]
    return Mesh(P, N, I, m)

def box(m):
    P, N, I = [], [], []
    for ax in range(3):
        for sgn in (-1, 1):
            n = [0, 0, 0]; n[ax] = sgn
            u = [0, 0, 0]; u[(ax + 1) % 3] = 1
            v = [0, 0, 0]; v[(ax + 2) % 3] = 1
            b = len(P)
            for cu, cv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                P.append([0.5 * (n[k] + cu * u[k] + cv * v[k]) for k in range(3)]); N.append(n)
            I += ([b, b + 1, b + 2, b, b + 2, b + 3] if sgn > 0 else [b, b + 2, b + 1, b, b + 3, b + 2])
    return Mesh(P, N, I, m)

def cyl(r, h, m, seg=40, bevel=0.0):
    b = min(bevel, h / 2, r / 2)
    if b:
        prof = [(0, 0), (r - b, 0), (r, b), (r, h - b), (r - b, h), (0, h)]
    else:
        prof = [(0, 0), (r, 0), (r, h), (0, h)]
    return lathe(prof, m, seg)

def ellip(rx, ry, rz, m, at=(0, 0, 0), rot=(0, 0, 0), la=10, lo=16):
    return sphere(m, la, lo).xf((rx, ry, rz), rot, at)

def jitter(m, amt):
    m.P = m.P + rng.normal(0, amt, m.P.shape).astype(np.float32); return m

# ---------------- GLB ----------------
def write_glb(path, meshes, name):
    groups = {}
    for me in meshes:
        groups.setdefault(me.m, []).append(me)
    bin_ = bytearray(); views = []; accs = []; prims = []; mats = []; mi = {}
    def add(arr, target, comp, typ, mm=False):
        while len(bin_) % 4: bin_.append(0)
        off = len(bin_); data = arr.tobytes(); bin_.extend(data)
        views.append(dict(buffer=0, byteOffset=off, byteLength=len(data), target=target))
        a = dict(bufferView=len(views) - 1, componentType=comp, count=len(arr), type=typ)
        if mm: a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
        accs.append(a); return len(accs) - 1
    for key, ms in groups.items():
        P, N, I, o = [], [], [], 0
        for me in ms:
            P.append(me.P); N.append(me.N); I.append(me.I + o); o += len(me.P)
        P = np.concatenate(P).astype(np.float32); N = np.concatenate(N).astype(np.float32)
        I = np.concatenate(I).astype(np.uint32)
        if key not in mi:
            d = MAT[key]; mi[key] = len(mats)
            mats.append(dict(name=key, pbrMetallicRoughness=dict(
                baseColorFactor=hexrgb(d['rgb']) + [1.0], roughnessFactor=d['rough'], metallicFactor=d['metal'])))
        prims.append(dict(attributes=dict(POSITION=add(P, 34962, 5126, 'VEC3', True),
                                          NORMAL=add(N, 34962, 5126, 'VEC3')),
                          indices=add(I, 34963, 5125, 'SCALAR'), material=mi[key]))
    while len(bin_) % 4: bin_.append(0)
    gltf = dict(asset=dict(version='2.0', generator='cardapio-ar'), scene=0, scenes=[dict(nodes=[0])],
                nodes=[dict(mesh=0, name=name)], meshes=[dict(name=name, primitives=prims)],
                materials=mats, accessors=accs, bufferViews=views, buffers=[dict(byteLength=len(bin_))])
    js = json.dumps(gltf, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(bin_), 0x004E4942)); f.write(bin_)
    allP = np.concatenate([m.P for m in meshes])
    return (allP.max(0) - allP.min(0)), os.path.getsize(path)

# ---------------- utensílios ----------------
mat('porcelana', '#f4f3ef', 0.22)
mat('madeira', '#9a6a3f', 0.65)
mat('madeira_clara', '#c9a274', 0.6)
mat('ardosia', '#2e3236', 0.8)

def prato(r=0.135, poco=0.095, h=0.025):
    """Prato raso. Retorna (malha, altura da superfície interna)."""
    f = 0.012
    prof = [(0, 0.002), (poco - 0.01, 0.002), (poco - 0.006, 0), (poco, 0.004), (r, h - 0.003), (r + 0.002, h - 0.001),
            (r - 0.002, h), (poco + 0.004, f + 0.002), (poco - 0.004, f), (0, f)]
    return lathe(prof, 'porcelana', 72), f

def tabua_redonda(r, h, m='madeira'):
    return cyl(r, h, m, 72, bevel=0.003)

# ---------------- pratos ----------------
def pizza():
    mat('massa', '#d9a35b', 0.8); mat('borda_tostada', '#6b3a1a', 0.85)
    mat('molho', '#b8321f', 0.55); mat('mussarela', '#f3e6c4', 0.45); mat('manjericao', '#2f6b2a', 0.5)
    out = [tabua_redonda(0.19, 0.016)]
    y = 0.016; R = 0.165
    out.append(lathe([(0, 0), (R, 0), (R + 0.009, 0.007), (R + 0.004, 0.019), (R - 0.008, 0.017), (R - 0.013, 0.008), (0, 0.006)],
                     'massa', 96, wobble=lambda t, yy: 1 + 0.012 * math.sin(7 * t) + 0.006 * math.sin(19 * t)).xf(t=(0, y, 0)))
    out.append(lathe([(0, 0.006), (R - 0.012, 0.006), (R - 0.011, 0.0085), (0, 0.0085)], 'molho', 96).xf(t=(0, y, 0)))
    for _ in range(26):  # tostado da borda
        a = rng.uniform(0, 2 * math.pi); rr = R - 0.002
        out.append(ellip(0.007, 0.002, 0.004, 'borda_tostada', (rr * math.cos(a), y + 0.0175, rr * math.sin(a)), (0, -a, 0)))
    for _ in range(14):
        a = rng.uniform(0, 2 * math.pi); rr = math.sqrt(rng.uniform(0, 1)) * 0.12
        s = rng.uniform(0.018, 0.03)
        out.append(jitter(ellip(s, 0.004, s * rng.uniform(0.7, 1), 'mussarela', (rr * math.cos(a), y + 0.0092, rr * math.sin(a)), (0, rng.uniform(0, 3), 0)), 0.0008))
    for _ in range(9):
        a = rng.uniform(0, 2 * math.pi); rr = math.sqrt(rng.uniform(0.05, 1)) * 0.12
        out.append(ellip(0.017, 0.0015, 0.009, 'manjericao', (rr * math.cos(a), y + 0.0135, rr * math.sin(a)), (0.15, rng.uniform(0, 3), 0)))
    return out

def burger():
    mat('pao', '#c47a35', 0.55); mat('pao_miolo', '#e8c38a', 0.85); mat('carne', '#4a2616', 0.8)
    mat('queijo', '#f0a828', 0.4); mat('tomate', '#c7281c', 0.35); mat('alface', '#6fae3a', 0.6)
    mat('gergelim', '#f2e2b8', 0.6); mat('batata', '#eab64e', 0.7)
    out = [box('madeira').xf((0.30, 0.018, 0.20), t=(0, 0.009, 0))]
    y = 0.018; cx = -0.04
    out.append(lathe([(0, 0), (0.054, 0), (0.058, 0.01), (0.056, 0.02), (0.05, 0.024), (0, 0.024)], 'pao', 64).xf(t=(cx, y, 0)))
    y += 0.024
    out.append(lathe([(0, 0), (0.062, 0), (0.064, 0.0025), (0.062, 0.005), (0, 0.005)], 'alface', 80,
                     wobble=lambda t, yy: 1 + 0.07 * math.sin(9 * t) + 0.03 * math.sin(23 * t)).xf(t=(cx, y, 0)))
    y += 0.004
    out.append(jitter(cyl(0.06, 0.02, 'carne', 56, bevel=0.006), 0.0007).xf(t=(cx, y, 0)))
    y += 0.02
    out.append(box('queijo').xf((0.088, 0.003, 0.088), (0, math.radians(30), 0), (cx, y + 0.0015, 0)))
    y += 0.003
    for dx, dz in ((-0.02, -0.012), (0.022, 0.014)):
        out.append(cyl(0.035, 0.007, 'tomate', 40, bevel=0.002).xf(t=(cx + dx, y, dz)))
    y += 0.007
    top = [(0, 0), (0.055, 0), (0.059, 0.008), (0.057, 0.022), (0.048, 0.036), (0.032, 0.044), (0, 0.047)]
    out.append(lathe(top, 'pao', 64).xf(t=(cx, y, 0)))
    for _ in range(40):
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0, 1)) * 0.046
        h = 0.047 * math.sqrt(max(0, 1 - (r / 0.058) ** 2))
        out.append(ellip(0.0028, 0.0012, 0.0016, 'gergelim', (cx + r * math.cos(a), y + h + 0.0005, r * math.sin(a)), (0, rng.uniform(0, 3), 0), 6, 8))
    for _ in range(18):  # batata frita
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 0.035)
        out.append(box('batata').xf((0.009, 0.009, rng.uniform(0.05, 0.08)),
                                    (rng.uniform(-0.25, 0.25), rng.uniform(0, 3.14), 0),
                                    (0.09 + r * math.cos(a) * 0.6, 0.018 + 0.006 + rng.uniform(0, 0.02), r * math.sin(a))))
    return out

def picanha():
    mat('arroz', '#f5f0e2', 0.9); mat('feijao', '#3d2418', 0.6); mat('farofa', '#d8b06a', 0.95)
    mat('picanha', '#7a3b22', 0.7); mat('gordura', '#efe0c0', 0.5); mat('vinagrete_t', '#d23a26', 0.4)
    mat('vinagrete_c', '#e8e0b8', 0.5); mat('salsinha', '#3f8a2f', 0.5)
    p, f = prato(0.14, 0.10); out = [p]
    out.append(lathe([(0, 0), (0.055, 0), (0.05, 0.016), (0.035, 0.03), (0, 0.036)], 'arroz', 48,
                     wobble=lambda t, y: 1 + 0.04 * math.sin(5 * t + y * 200)).xf(t=(-0.045, f, -0.04)))
    out.append(lathe([(0, 0), (0.045, 0), (0.044, 0.008), (0.03, 0.014), (0, 0.016)], 'feijao', 48,
                     wobble=lambda t, y: 1 + 0.05 * math.sin(4 * t)).xf(t=(0.05, f, -0.05)))
    for _ in range(14):
        a = rng.uniform(0, 6.28); r = rng.uniform(0, 0.03)
        out.append(ellip(0.0055, 0.0032, 0.0035, 'feijao', (0.05 + r * math.cos(a), f + 0.014 - r * 0.2, -0.05 + r * math.sin(a)), (0, rng.uniform(0, 3), 0), 6, 10))
    out.append(lathe([(0, 0), (0.04, 0), (0.03, 0.01), (0, 0.014)], 'farofa', 40,
                     wobble=lambda t, y: 1 + 0.08 * math.sin(6 * t)).xf(t=(-0.065, f, 0.045)))
    for i in range(5):  # fatias de picanha em leque
        ang = math.radians(-20 + i * 10); x = 0.02 + i * 0.012; z = 0.05 - i * 0.004
        out.append(box('picanha').xf((0.095, 0.014, 0.024), (0.2, ang, 0), (x, f + 0.011 + i * 0.0015, z)))
        out.append(box('gordura').xf((0.006, 0.0145, 0.024), (0.2, ang, 0), (x + 0.05 * math.cos(ang), f + 0.011 + i * 0.0015 - 0.05 * math.sin(ang) * 0, z - 0.05 * math.sin(ang))))
    for _ in range(26):
        a = rng.uniform(0, 6.28); r = rng.uniform(0, 0.025)
        m = ['vinagrete_t', 'vinagrete_c', 'salsinha'][rng.integers(0, 3)]
        out.append(box(m).xf((0.007, 0.006, 0.007), (rng.uniform(0, 3), rng.uniform(0, 3), 0), (0.075 + r * math.cos(a), f + 0.004, 0.0 + r * math.sin(a))))
    return out

def sushi():
    mat('arroz_sushi', '#f7f5ee', 0.85); mat('salmao', '#f07a4a', 0.35); mat('salmao_listra', '#fbd2b8', 0.4)
    mat('nori', '#1d2419', 0.6); mat('gengibre', '#f2b3a6', 0.4); mat('wasabi', '#8fb446', 0.7)
    out = [box('madeira_clara').xf((0.34, 0.02, 0.15), t=(0, 0.014, 0))]
    for x in (-0.15, 0.15):
        out.append(box('madeira_clara').xf((0.02, 0.006, 0.13), t=(x, 0.003, 0)))
    y = 0.024
    for i in range(4):  # nigiri
        x = -0.12 + i * 0.045
        out.append(jitter(ellip(0.012, 0.011, 0.024, 'arroz_sushi', (x, y + 0.009, -0.025)), 0.0006))
        out.append(ellip(0.015, 0.0045, 0.032, 'salmao', (x, y + 0.019, -0.025), (0.0, 0.0, 0.08)))
        for k in (-0.012, 0.0, 0.012):
            out.append(ellip(0.0146, 0.0012, 0.0016, 'salmao_listra', (x, y + 0.0228, -0.025 + k), (0.25, 0, 0), 5, 8))
    for i in range(6):  # uramaki/hossomaki
        x = -0.12 + (i % 3) * 0.032 + (0.0 if i < 3 else 0.016); z = 0.035 + (0 if i < 3 else 0.0)
        x = -0.125 + i * 0.03; z = 0.04
        out.append(lathe([(0, 0), (0.0145, 0), (0.0145, 0.022), (0, 0.022)], 'nori', 32).xf(t=(x, y, z)))
        out.append(cyl(0.0128, 0.0012, 'arroz_sushi', 32).xf(t=(x, y + 0.0218, z)))
        out.append(cyl(0.0055, 0.0016, 'salmao', 20).xf(t=(x, y + 0.0218, z)))
    out.append(jitter(lathe([(0, 0), (0.018, 0), (0.012, 0.014), (0, 0.018)], 'gengibre', 24), 0.001).xf(t=(0.1, y, -0.03)))
    out.append(jitter(lathe([(0, 0), (0.011, 0), (0.008, 0.009), (0, 0.012)], 'wasabi', 20), 0.0008).xf(t=(0.125, y, 0.04)))
    return out

def pudim():
    mat('pudim', '#f1c35f', 0.45); mat('caramelo', '#8a3d0c', 0.12)
    p, f = prato(0.11, 0.075, 0.022); out = [p]
    prof = [(0.022, 0), (0.085, 0), (0.084, 0.012), (0.078, 0.048), (0.07, 0.06), (0.04, 0.062), (0.03, 0.058), (0.024, 0.05), (0.022, 0)]
    out.append(lathe(prof, 'pudim', 72).xf(t=(0, f, 0)))
    car = [(0.0789, 0.049), (0.0706, 0.0612), (0.04, 0.0632), (0.0292, 0.0588), (0.0232, 0.0505), (0.0215, 0.046)]
    car = [(0.0798, 0.044)] + car
    out.append(lathe(car[::-1][::-1], 'caramelo', 72, wobble=lambda t, y: 1 + (0.012 * math.sin(11 * t) if y < 0.052 else 0)).xf(t=(0, f, 0)))
    for k in range(9):  # escorridos de calda
        a = k * 2 * math.pi / 9 + 0.2
        out.append(ellip(0.0035, 0.014, 0.006, 'caramelo', (0.0812 * math.cos(a), f + 0.034, 0.0812 * math.sin(a)), (0, -a, 0.12)))
    out.append(lathe([(0, 0), (0.1, 0), (0.1, 0.0015), (0, 0.0015)], 'caramelo', 72,
                     wobble=lambda t, y: 1 + 0.03 * math.sin(5 * t)).xf(t=(0, f, 0)))
    return out

def acai():
    mat('tigela', '#3a4a3f', 0.35); mat('acai', '#3b1238', 0.5); mat('banana', '#f3e3a1', 0.6)
    mat('granola', '#a8692e', 0.9); mat('morango', '#c8102e', 0.3); mat('leite_cond', '#f6efe0', 0.25)
    prof = [(0, 0), (0.035, 0), (0.037, 0.006), (0.07, 0.045), (0.078, 0.07), (0.074, 0.071), (0.067, 0.05), (0.035, 0.012), (0, 0.012)]
    out = [lathe(prof, 'tigela', 72)]
    out.append(lathe([(0, 0.06), (0.071, 0.06), (0.06, 0.068), (0, 0.072)], 'acai', 64,
                     wobble=lambda t, y: 1 + 0.01 * math.sin(6 * t)))
    for i in range(7):
        a = 0.3 + i * 0.32; r = 0.042
        out.append(cyl(0.0135, 0.004, 'banana', 24).xf(r=(0.25, -a, 0), t=(r * math.cos(a), 0.0695, r * math.sin(a))))
    for _ in range(70):
        a = rng.uniform(math.pi * 0.95, math.pi * 1.75); r = rng.uniform(0.0, 0.058)
        out.append(box('granola').xf((rng.uniform(.004, .008), .003, rng.uniform(.004, .007)), (rng.uniform(0, 1), rng.uniform(0, 3), 0),
                                    (r * math.cos(a), 0.071 + rng.uniform(0, 0.004) - r * 0.06, r * math.sin(a))))
    for a in (4.9, 5.4, 5.9):
        out.append(ellip(0.012, 0.009, 0.014, 'morango', (0.035 * math.cos(a), 0.073, 0.035 * math.sin(a)), (0, a, 0.3)))
    out.append(lathe([(0, 0), (0.004, 0), (0.004, 0.002), (0, 0.002)], 'leite_cond', 16).xf((1, 1, 1), t=(0, 0.072, 0)))
    pts = np.linspace(-0.05, 0.05, 22)
    for x in pts:
        out.append(ellip(0.0035, 0.0018, 0.003, 'leite_cond', (x, 0.0735, 0.012 * math.sin(x * 90)), la=6, lo=8))
    return out

def normais(m):
    """Recalcula normais suaves a partir das faces (para malhas deformadas)."""
    P = m.P.astype(float); I = m.I.reshape(-1, 3); N = np.zeros_like(P)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    for k in range(3): np.add.at(N, I[:, k], fn)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    m.N = N.astype(np.float32); return m

def bloco_arredondado(sx, sy, sz, m, e=0.28, at=(0, 0, 0), rot=(0, 0, 0), la=24, lo=36):
    """Superelipsoide: um bloco de cantos arredondados (e menor = mais quadrado)."""
    b = sphere(m, la, lo); P = b.P.astype(float)
    P = np.sign(P) * np.abs(P) ** e
    b.P = P.astype(np.float32)
    return normais(b).xf((sx / 2, sy / 2, sz / 2), rot, at)

def costelao():
    """Costelão 12 horas na chapa de ferro sobre tábua, com arroz, molho e fritas."""
    r = np.random.default_rng(12)
    mat('ferro', '#232323', 0.55, 0.35); mat('casca', '#8a4413', 0.28); mat('casca_escura', '#5a2a0c', 0.35)
    mat('carne_lado', '#4b2414', 0.55); mat('osso', '#e7dcc4', 0.55); mat('alecrim', '#4f7a3a', 0.6)
    mat('tomate_cereja', '#d81e12', 0.18); mat('cebola_roxa', '#9b4a68', 0.35)
    mat('arroz', '#f2ead2', 0.9); mat('legume_cenoura', '#e8892b', 0.5); mat('legume_milho', '#f1c232', 0.5)
    mat('legume_ervilha', '#5c9a3a', 0.5); mat('azeitona', '#2a2626', 0.4); mat('molho_escuro', '#2e1408', 0.12)
    mat('batata', '#eab64e', 0.7); mat('papel', '#e9e7e1', 0.85); mat('porcelana', '#f4f3ef', 0.22)
    out = []
    # tábua e chapa de ferro (30 x 24 cm)
    out.append(box('madeira').xf((0.40, 0.022, 0.30), t=(0, 0.011, 0)))
    y = 0.022
    out.append(box('ferro').xf((0.30, 0.008, 0.24), t=(0, y + 0.004, 0)))
    for (sx, sz, x, z) in ((0.30, 0.008, 0, 0.116), (0.30, 0.008, 0, -0.116), (0.008, 0.24, 0.146, 0), (0.008, 0.24, -0.146, 0)):
        out.append(box('ferro').xf((sx, 0.02, sz), t=(x, y + 0.01, z)))
    y += 0.008
    # costela: bloco de ~22 x 15 cm, 9 cm de altura, levemente girado
    giro = math.radians(-12)
    out.append(jitter(bloco_arredondado(0.215, 0.085, 0.145, 'casca', 0.32, (-0.01, y + 0.0425, 0.0), (0, giro, 0)), 0.0012))
    out.append(bloco_arredondado(0.20, 0.03, 0.13, 'carne_lado', 0.3, (-0.004, y + 0.013, 0.008), (0, giro, 0)))
    for _ in range(18):  # partes mais tostadas
        a = r.uniform(-0.09, 0.08); b = r.uniform(-0.055, 0.055)
        x = a * math.cos(giro) + b * math.sin(giro); z = -a * math.sin(giro) + b * math.cos(giro)
        out.append(ellip(r.uniform(.008, .016), .003, r.uniform(.006, .012), 'casca_escura', (x - 0.01, y + 0.0855, z), (0, r.uniform(0, 3), 0), 6, 10))
    # 4 ossos saindo pela lateral (lado +x, como na foto)
    for i, (dz, h) in enumerate(((-0.05, 0.018), (-0.015, 0.03), (0.02, 0.04), (0.055, 0.03))):
        L = 0.075 + 0.01 * (i % 2)
        bx = 0.09 * math.cos(giro) + dz * math.sin(giro) - 0.01; bz = -0.09 * math.sin(giro) + dz * math.cos(giro)
        osso = lathe([(0, 0), (0.013, 0), (0.0145, 0.004), (0.0135, L - 0.004), (0.011, L), (0, L)], 'osso', 20)
        out.append(osso.xf((1, 1, 0.75), (0, giro, -math.pi / 2), (bx, y + h, bz)))
    # alecrim por cima
    for k in range(5):
        out.append(ellip(0.035, 0.0025, 0.0028, 'alecrim', (-0.02 + k * 0.004, y + 0.088, -0.01 + k * 0.006), (0, giro + 0.35 * (k - 2), 0), 5, 8))
        for j in range(8):
            t = (j - 3.5) * 0.008
            out.append(ellip(0.006, 0.0012, 0.0012, 'alecrim', (-0.02 + k * 0.004 + t * math.cos(giro + 0.35 * (k - 2)), y + 0.0895, -0.01 + k * 0.006 - t * math.sin(giro + 0.35 * (k - 2))), (0, r.uniform(0, 3), 0), 4, 6))
    # tomates-cereja na frente da chapa e cebola roxa atrás
    for k in range(7):
        out.append(ellip(0.012, 0.011, 0.012, 'tomate_cereja', (-0.03 + k * 0.025 + r.uniform(-.004, .004), y + 0.011, 0.095 - (k % 2) * 0.012)))
    for _ in range(10):
        out.append(ellip(0.012, 0.004, 0.006, 'cebola_roxa', (-0.12 + r.uniform(0, 0.04), y + 0.006 + r.uniform(0, .006), -0.09 + r.uniform(0, 0.03)), (r.uniform(0, 1), r.uniform(0, 3), 0), 6, 10))
    # tigela de arroz colorido (atrás, fora da tábua)
    tig = [(0, 0), (0.035, 0), (0.037, 0.005), (0.06, 0.04), (0.062, 0.058), (0.058, 0.058), (0.055, 0.042), (0.035, 0.01), (0, 0.01)]
    cx, cz = 0.02, -0.215
    out.append(lathe(tig, 'porcelana', 56).xf(t=(cx, 0, cz)))
    out.append(lathe([(0, 0.045), (0.056, 0.045), (0.045, 0.06), (0, 0.068)], 'arroz', 40, wobble=lambda t, yy: 1 + 0.03 * math.sin(7 * t)).xf(t=(cx, 0, cz)))
    for _ in range(45):
        a = r.uniform(0, 6.28); rr = math.sqrt(r.uniform(0, 1)) * 0.048
        m = ['legume_cenoura', 'legume_milho', 'legume_ervilha', 'azeitona'][r.integers(0, 4)]
        out.append(box(m).xf((0.006, 0.005, 0.006), (r.uniform(0, 3), r.uniform(0, 3), 0), (cx + rr * math.cos(a), 0.067 - rr * 0.3, cz + rr * math.sin(a))))
    # ramequim de molho
    ram = [(0, 0), (0.036, 0), (0.038, 0.004), (0.038, 0.042), (0.034, 0.042), (0.034, 0.008), (0, 0.008)]
    out.append(lathe(ram, 'porcelana', 48).xf(t=(0.16, 0, -0.2)))
    out.append(cyl(0.0342, 0.03, 'molho_escuro', 40).xf(t=(0.16, 0.006, -0.2)))
    # fritas no papel (à esquerda)
    out.append(box('papel').xf((0.17, 0.002, 0.15), (0, 0.35, 0), (-0.245, 0.001, -0.14)))
    for _ in range(40):
        a = r.uniform(0, 6.28); rr = math.sqrt(r.uniform(0, 1)) * 0.055
        out.append(box('batata').xf((0.009, 0.009, r.uniform(0.05, 0.085)), (r.uniform(-0.2, 0.2), r.uniform(0, 3.14), 0),
                                    (-0.245 + rr * math.cos(a), 0.007 + r.uniform(0, 0.022), -0.14 + rr * math.sin(a))))
    return out

def petit_gateau():
    """Petit gateau com sorvete de creme e calda de chocolate, em prato raso de 26 cm."""
    r = np.random.default_rng(21)
    mat('bolo_choc', '#4a2a1c', 0.75); mat('calda_choc', '#2a1208', 0.1)
    mat('sorvete', '#f3e6c6', 0.55); mat('sorvete_derretido', '#efdcb4', 0.25)
    p, f = prato(0.13, 0.09, 0.022); out = [p]
    # bolinho: tronco de cone ~7 cm de base, 5 cm de altura, um pouco irregular
    cx, cz = 0.045, -0.035
    bolo = [(0, 0), (0.036, 0), (0.0365, 0.004), (0.031, 0.044), (0.027, 0.05), (0.012, 0.053), (0, 0.053)]
    out.append(jitter(lathe(bolo, 'bolo_choc', 48, wobble=lambda t, y: 1 + 0.03 * math.sin(5 * t + y * 60)), 0.0009).xf(t=(cx, f, cz)))
    # calda escorrendo pelo bolinho
    for k in range(5):
        a = 1.9 + k * 0.33
        rr = 0.034 - 0.0
        out.append(ellip(0.0045, 0.02, 0.003, 'calda_choc', (cx + 0.0335 * math.cos(a), f + 0.027, cz + 0.0335 * math.sin(a)), (0, -a, 0.1), 6, 10))
    out.append(ellip(0.02, 0.003, 0.016, 'calda_choc', (cx, f + 0.053, cz), la=8, lo=14))
    # bola de sorvete sobre poça derretida
    sx, sz = -0.035, 0.015
    out.append(lathe([(0, 0), (0.07, 0), (0.07, 0.002), (0, 0.003)], 'sorvete_derretido', 48,
                     wobble=lambda t, y: 1 + 0.14 * math.sin(3 * t) + 0.06 * math.sin(7 * t)).xf((0.85, 1, 0.75), t=(sx + 0.01, f, sz)))
    out.append(jitter(ellip(0.04, 0.032, 0.038, 'sorvete', (sx, f + 0.03, sz), la=16, lo=24), 0.0012))
    for k in range(6):  # calda sobre o sorvete
        a = r.uniform(0, 6.28)
        out.append(ellip(0.016, 0.003, 0.004, 'calda_choc', (sx + 0.022 * math.cos(a), f + 0.054, sz + 0.022 * math.sin(a)), (0.4, -a, 0), 6, 10))
    # fio de calda em volta e pingos no prato
    for k in range(70):
        a = k / 70 * 2 * math.pi; rr = 0.085 + 0.006 * math.sin(5 * a)
        if r.uniform() < 0.25: continue
        out.append(ellip(r.uniform(0.004, 0.008), 0.0012, 0.003, 'calda_choc', (rr * math.cos(a), f + 0.0008, rr * math.sin(a)), (0, -a, 0), 5, 8))
    for _ in range(30):
        a = r.uniform(0, 6.28); rr = r.uniform(0.06, 0.11)
        s = r.uniform(0.002, 0.005)
        out.append(ellip(s, 0.0012, s, 'calda_choc', (rr * math.cos(a), f + 0.0008, rr * math.sin(a)), la=5, lo=8))
    return out

def pizza_dois_queijos():
    """Pizza 2 queijos de 35 cm, gratinada e cortada em 8 fatias, sobre tábua redonda."""
    r = np.random.default_rng(35)
    mat('massa', '#d9a35b', 0.8); mat('borda_tostada', '#8a5222', 0.85)
    mat('queijo_base', '#f2dfa8', 0.4); mat('gratinado', '#c9852f', 0.5); mat('gratinado_escuro', '#9a5a1e', 0.55)
    mat('corte', '#b08a4a', 0.7)
    out = [tabua_redonda(0.19, 0.016)]
    y = 0.016; R = 0.165
    out.append(lathe([(0, 0), (R, 0), (R + 0.01, 0.008), (R + 0.006, 0.021), (R - 0.008, 0.019), (R - 0.014, 0.009), (0, 0.007)],
                     'massa', 96, wobble=lambda t, yy: 1 + 0.01 * math.sin(6 * t) + 0.005 * math.sin(17 * t)).xf(t=(0, y, 0)))
    # camada de queijo derretido cobrindo quase até a borda
    out.append(lathe([(0, 0.007), (R - 0.011, 0.007), (R - 0.009, 0.0105), (R - 0.02, 0.0125), (0, 0.0125)], 'queijo_base', 96,
                     wobble=lambda t, yy: 1 + 0.012 * math.sin(11 * t)).xf(t=(0, y, 0)))
    for _ in range(30):  # tostado da borda
        a = r.uniform(0, 2 * math.pi); rr = R + 0.002
        out.append(ellip(0.008, 0.002, 0.005, 'borda_tostada', (rr * math.cos(a), y + 0.02, rr * math.sin(a)), (0, -a, 0)))
    for _ in range(190):  # pintinhas gratinadas
        a = r.uniform(0, 2 * math.pi); rr = math.sqrt(r.uniform(0, 1)) * (R - 0.02)
        sz = r.uniform(0.002, 0.006); m = 'gratinado' if r.uniform() < 0.75 else 'gratinado_escuro'
        out.append(ellip(sz, 0.0009, sz * r.uniform(0.6, 1), m, (rr * math.cos(a), y + 0.0127, rr * math.sin(a)), (0, r.uniform(0, 3), 0), 5, 8))
    for k in range(4):  # cortes das 8 fatias
        a = k * math.pi / 4
        out.append(box('corte').xf((2 * (R - 0.012), 0.002, 0.0022), (0, a, 0), (0, y + 0.0128, 0)))
    return out

# pizza_dois_queijos: o modelo publicado é o real (tools/pizza_real.py); a versão ilustrada fica na função acima.
PRATOS = dict(petit_gateau=petit_gateau, costelao_12h=costelao, pizza_margherita=pizza, burger_da_casa=burger, picanha_completa=picanha,
              combinado_salmao=sushi, pudim_de_leite=pudim, acai_na_tigela=acai)

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'site/models'
    os.makedirs(out, exist_ok=True)
    so = sys.argv[2:]  # opcional: gerar só alguns pratos
    for k, fn in PRATOS.items():
        if so and k not in so: continue
        dims, size = write_glb(os.path.join(out, k + '.glb'), fn(), k)
        print(f'{k:20s} {dims[0]*100:5.1f} x {dims[1]*100:4.1f} x {dims[2]*100:5.1f} cm   {size/1024:6.0f} KB')
