"""Pizza 2 Queijos com textura REAL tirada do vídeo filmado de cima.
1) ajusta uma elipse na borda do prato e endireita a imagem para um círculo (vista de cima);
2) acha a pizza dentro do prato;
3) monta prato + pizza em 3D (escala real) com a foto aplicada por cima.
Uso: python3 tools/pizza_real.py quadro.png saida.glb [diametro_prato_cm]
"""
import sys, json, struct, math, io
import numpy as np, cv2
from PIL import Image, ImageFilter
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from gerar_modelos import lathe

frame, saida = sys.argv[1], sys.argv[2]
PRATO_CM = float(sys.argv[3]) if len(sys.argv) > 3 else 35.0
TEX = 1024

im = cv2.imread(frame); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
branco = ((hsv[..., 1] < 45) & (hsv[..., 2] > 170)).astype(np.uint8) * 255
branco = cv2.morphologyEx(branco, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
cs, _ = cv2.findContours(branco, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
(cx, cy), (a, b), ang = cv2.fitEllipse(max(cs, key=cv2.contourArea))

# afim: elipse do prato -> círculo de raio Rt no centro da textura (margem de 2%)
Rt = TEX / 2 * 0.98; t = math.radians(ang)
R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
A = R @ np.diag([2 * Rt / a, 2 * Rt / b]) @ R.T
M = np.hstack([A, (np.array([TEX / 2, TEX / 2]) - A @ np.array([cx, cy]))[:, None]])
ret = cv2.warpAffine(im, M, (TEX, TEX), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)

# pizza: região colorida (não branca) dentro do prato
h2 = cv2.cvtColor(ret, cv2.COLOR_BGR2HSV)
yy, xx = np.mgrid[:TEX, :TEX]; dentro = (xx - TEX / 2) ** 2 + (yy - TEX / 2) ** 2 < (Rt * 0.97) ** 2
pz = ((h2[..., 1] > 50) & dentro).astype(np.uint8) * 255
pz = cv2.morphologyEx(pz, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
pz = cv2.morphologyEx(pz, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
cs, _ = cv2.findContours(pz, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cont = max(cs, key=cv2.contourArea)
mo = cv2.moments(cont); px, py = mo['m10'] / mo['m00'], mo['m01'] / mo['m00']
# contorno real da pizza em coordenadas polares (raio por ângulo), suavizado
pts = cont[:, 0, :].astype(float); angs = np.arctan2(pts[:, 1] - py, pts[:, 0] - px); rads = np.hypot(pts[:, 0] - px, pts[:, 1] - py)
bins = np.linspace(-math.pi, math.pi, 181); rb = np.zeros(180)
for i in range(180):
    sel = (angs >= bins[i]) & (angs < bins[i + 1]); rb[i] = np.median(rads[sel]) if sel.any() else np.nan
ok = ~np.isnan(rb); ctr = (bins[:-1] + bins[1:]) / 2
rb = np.interp(ctr, ctr[ok], rb[ok], period=2 * math.pi)
rb = np.convolve(np.r_[rb[-3:], rb, rb[:3]], np.ones(7) / 7, 'valid')
pr = float(rb.mean())
def contorno(t, y=None):
    a = (t + math.pi) % (2 * math.pi) - math.pi
    return float(np.interp(a, ctr, rb, period=2 * math.pi)) / pr

m_por_px = (PRATO_CM / 100 / 2) / Rt
pizza_r = pr * m_por_px; off = ((px - TEX / 2) * m_por_px, (py - TEX / 2) * m_por_px)
print(f'prato Ø {PRATO_CM:.0f} cm | pizza Ø {pizza_r * 200:.1f} cm | deslocada {off[0]*100:.1f}, {off[1]*100:.1f} cm')

# fora do prato: pinta de branco (não aparece, mas evita madeira na borda filtrada)
ret[~((xx - TEX / 2) ** 2 + (yy - TEX / 2) ** 2 < (Rt * 0.995) ** 2)] = ret[int(TEX / 2), int(TEX / 2 - Rt * 0.97)]
# no prato, fora da pizza: cor do prato (tira restos de borda que ficariam pintados no prato)
ang_px = np.arctan2(yy - py, xx - px); r_lim = np.interp(ang_px.ravel(), ctr, rb, period=2 * math.pi).reshape(TEX, TEX)
fora_pizza = (np.hypot(xx - px, yy - py) > r_lim * 1.01) & ((xx - TEX / 2) ** 2 + (yy - TEX / 2) ** 2 < (Rt * 0.995) ** 2)
anel_prato = fora_pizza & (np.hypot(xx - px, yy - py) > r_lim * 1.08)
cor_prato = np.median(ret[anel_prato], axis=0)
mistura = np.clip((np.hypot(xx - px, yy - py) - r_lim * 1.01) / (r_lim * 0.05), 0, 1)[..., None]
ret = np.where(fora_pizza[..., None], (ret * (1 - mistura) * 0.0 + cor_prato * 1.0), ret).astype(np.uint8)
img = Image.fromarray(cv2.cvtColor(ret, cv2.COLOR_BGR2RGB)).filter(ImageFilter.UnsharpMask(2, 60, 2))
buf = io.BytesIO(); img.save(buf, 'JPEG', quality=88); jpg = buf.getvalue()
img.save(saida.rsplit('.', 1)[0] + '_textura.jpg', quality=88)

def uv(P):  # metros -> coordenadas da textura (x para a direita, z para baixo)
    return np.stack([0.5 + P[:, 0] / (m_por_px * TEX), 0.5 + P[:, 2] / (m_por_px * TEX)], 1).astype(np.float32)

Rp = PRATO_CM / 200; f = 0.01
# prato: topo texturizado, fundo e borda em branco liso
topo_prato = lathe([(Rp - 0.004, f + 0.004), (Rp - 0.012, f), (0, f)], 'tex', 96)
fundo = lathe([(0, 0.002), (Rp * 0.8, 0.002), (Rp * 0.8 + 0.004, 0), (Rp * 0.85, 0.003), (Rp, f + 0.002), (Rp + 0.001, f + 0.004), (Rp - 0.004, f + 0.0045)], 'branco', 96)
# pizza: disco com leve cúpula e borda alta, com a foto por cima
r = pizza_r
prof_topo = [(r, 0.012), (r * 0.97, 0.017), (r * 0.9, 0.0145), (r * 0.6, 0.0135), (0, 0.013)]
pizza_topo = lathe(prof_topo, 'tex', 180, wobble=contorno)
pizza_lado = lathe([(0, 0), (r - 0.003, 0), (r, 0.004), (r, 0.012)], 'borda', 180, wobble=contorno)
for m in (pizza_topo, pizza_lado):
    m.P[:, 0] += off[0]; m.P[:, 2] += off[1]; m.P[:, 1] += f
# cor da borda tirada da própria foto (anel externo da pizza)
anel = (np.hypot(xx - px, yy - py) > pr * 0.93) & (np.hypot(xx - px, yy - py) < pr * 0.99)
borda_rgb = (cv2.cvtColor(ret, cv2.COLOR_BGR2RGB)[anel].mean(0) / 255) ** 2.2

prims = [(topo_prato, 'tex'), (pizza_topo, 'tex'), (fundo, 'branco'), (pizza_lado, 'borda')]
mats = {'tex': dict(name='foto_real', pbrMetallicRoughness=dict(baseColorTexture=dict(index=0), metallicFactor=0, roughnessFactor=0.55)),
        'branco': dict(name='porcelana', pbrMetallicRoughness=dict(baseColorFactor=[0.9, 0.9, 0.88, 1], metallicFactor=0, roughnessFactor=0.25)),
        'borda': dict(name='borda_pizza', pbrMetallicRoughness=dict(baseColorFactor=list(borda_rgb) + [1], metallicFactor=0, roughnessFactor=0.75))}
order = ['tex', 'branco', 'borda']
bin_ = bytearray(); views = []; accs = []; out_prims = []
def add(data, target=None):
    while len(bin_) % 4: bin_.append(0)
    o = len(bin_); bin_.extend(data); v = dict(buffer=0, byteOffset=o, byteLength=len(data))
    if target: v['target'] = target
    views.append(v); return len(views) - 1
def acc(arr, typ, comp, target, mm=False):
    a = dict(bufferView=add(arr.tobytes(), target), componentType=comp, count=len(arr), type=typ)
    if mm: a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
    accs.append(a); return len(accs) - 1
for m, k in prims:
    att = dict(POSITION=acc(m.P.astype(np.float32), 'VEC3', 5126, 34962, True), NORMAL=acc(m.N.astype(np.float32), 'VEC3', 5126, 34962))
    if k == 'tex': att['TEXCOORD_0'] = acc(uv(m.P), 'VEC2', 5126, 34962)
    out_prims.append(dict(attributes=att, indices=acc(m.I.astype(np.uint32), 'SCALAR', 5125, 34963), material=order.index(k)))
img_view = add(jpg)
while len(bin_) % 4: bin_.append(0)
g = dict(asset=dict(version='2.0', generator='cardapio-ar'), scene=0, scenes=[dict(nodes=[0])], nodes=[dict(mesh=0, name='pizza_dois_queijos')],
         meshes=[dict(name='pizza_dois_queijos', primitives=out_prims)], materials=[mats[k] for k in order],
         textures=[dict(source=0, sampler=0)], samplers=[dict(magFilter=9729, minFilter=9987, wrapS=33071, wrapT=33071)],
         images=[dict(bufferView=img_view, mimeType='image/jpeg')], accessors=accs, bufferViews=views, buffers=[dict(byteLength=len(bin_))])
js = json.dumps(g, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
with open(saida, 'wb') as fo:
    fo.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
    fo.write(struct.pack('<II', len(js), 0x4E4F534A)); fo.write(js)
    fo.write(struct.pack('<II', len(bin_), 0x004E4942)); fo.write(bin_)
print('ok', saida, len(bin_) // 1024, 'KB')
