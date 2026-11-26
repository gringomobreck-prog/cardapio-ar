"""Modelos 3D em tamanho real para o cardápio do CAIS (um modelo por tipo de item).

Unidade: metros, Y para cima, origem no centro da base.
Bebidas usam as medidas reais das embalagens. Pratos são ilustrativos, no tamanho do prato/tábua/cumbuca.
Cada modelo tem um id "tipo" ou "tipo-cor" (ex.: "lata-laranja", "copo_suco-vermelho").

Uso: python3 tools/modelos_cais.py site/models/cais id1 id2 ...   (gera os ids pedidos)
"""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from gerar_modelos import (mat, lathe, sphere, box, cyl, ellip, jitter, write_glb, prato, tabua_redonda,
                           bloco_arredondado, costelao, petit_gateau, burger)

# ---------------------------------------------------------------- cores
CORES = {
    'amarelo': '#f2c230', 'laranja': '#f08a1c', 'vermelho': '#c8192a', 'rosa': '#f28aa0', 'roxo': '#5b1f5e',
    'verde': '#b9d77a', 'branco': '#efe9d8', 'claro': '#e9f1f2', 'escuro': '#2b120a', 'ambar': '#b8701e',
    'azul': '#2f8fd8', 'creme': '#efe0c2', 'cafe': '#6b3f22', 'tinto': '#5a0d1c', 'rose': '#f3a6a0',
    'branco_vinho': '#ecd98a', 'guarana': '#9a5a17', 'agua': '#dfeef3', 'cinza': '#9aa3ab', 'dourado': '#d9a441',
    'verde_lata': '#2f9e44', 'preta': '#202224', 'prata': '#c9ced3',
    'vidro_verde': '#1f5a2a', 'vidro_claro': '#e8efe6', 'vidro_ambar': '#6b3a12', 'vidro_azul': '#1f4fa0',
    'baiao': '#a77b52', 'azeitona': '#5a6b2a', 'feijao_verde': '#7b8a4a', 'brocolis': '#5c9a3a', 'legumes': '#e8892b',
}

def cor(c):
    return CORES.get(c, c)

def vidro():
    mat('vidro', '#e8f2f4', 0.05, 0.0, 0.22)
    return 'vidro'

def gelo():
    mat('gelo', '#f4fbff', 0.08, 0.0, 0.55)
    return 'gelo'

def liquido(c, nome='liquido', alpha=0.82):
    mat(nome, cor(c), 0.12, 0.0, alpha)
    return nome

def copo(rb, rt, h, esp=0.0025, fundo=0.008):
    """Copo de vidro aberto (parede com espessura)."""
    return lathe([(0, 0), (rb, 0), (rt, h), (rt - esp, h), (rb - esp, fundo), (0, fundo)], vidro(), 48, crease=40)

def enche(rb, rt, h, nivel, m, esp=0.0025, fundo=0.008, encolhe=0.0006):
    r_at = lambda y: rb + (rt - rb) * y / h - esp - encolhe
    return lathe([(0, fundo + 0.0005), (r_at(fundo), fundo + 0.0005), (r_at(nivel), nivel), (0, nivel)], m, 48)

def cubos_gelo(r, y0, y1, n=4):
    out = []; g = gelo()
    for i in range(n):
        a = i * 2 * math.pi / n + 0.4; rr = r * 0.45
        out.append(box(g).xf((0.022, 0.022, 0.022), (0.3 * i, 0.5 * i, 0.2), (rr * math.cos(a), y0 + (y1 - y0) * (i % 2 * 0.5 + 0.3), rr * math.sin(a))))
    return out

def silhueta(pts, m, seg=48):
    """Garrafa/sólido de revolução a partir do contorno [(r, y), ...] de baixo para cima."""
    return lathe([(0, 0)] + pts + [(0, pts[-1][1])], m, seg)

def recorta(pts, nivel, fator=0.9):
    out = []
    for (r0, y0), (r1, y1) in zip(pts, pts[1:]):
        if y0 <= nivel: out.append((r0 * fator, y0 + 0.003))
        if y0 <= nivel < y1:
            t = (nivel - y0) / (y1 - y0); out.append(((r0 + (r1 - r0) * t) * fator, nivel))
    return out

def garrafa(pts, m_vidro, liq=None, nivel=None, tampa=None, tampa_h=0.012, rotulo=None, rotulo_y=None):
    out = [silhueta(pts, m_vidro)]
    if liq and nivel:
        out.append(silhueta(recorta(pts, nivel), liq))
    rt = pts[-1][0]; yt = pts[-1][1]
    if tampa:
        out.append(cyl(rt + 0.0012, tampa_h, tampa, 24, 0.001).xf(t=(0, yt - tampa_h * 0.6, 0)))
    if rotulo and rotulo_y:
        y0, y1 = rotulo_y
        r = max(r for r, y in pts if y0 <= y <= y1) + 0.0006
        out.append(lathe([(r, y0), (r, y1)], rotulo, 48).xf())
        out.append(lathe([(r, y1), (r, y0)], rotulo, 48).xf())
    return out

# ---------------------------------------------------------------- bebidas
def copo_suco(c):  # copo long neck 300 ml
    rb, rt, h = 0.029, 0.037, 0.15
    return [copo(rb, rt, h), enche(rb, rt, h, 0.128, liquido(c))] + cubos_gelo(0.03, 0.09, 0.12, 3)

def jarra(c):  # jarra 700 ml
    rb, rt, h = 0.048, 0.044, 0.19
    out = [lathe([(0, 0), (rb, 0), (0.052, 0.06), (rt, h - 0.01), (0.047, h), (0.044, h), (rt - 0.0025, h - 0.012), (0.049, 0.06), (rb - 0.0025, 0.008), (0, 0.008)], vidro(), 56, crease=40)]
    out.append(lathe([(0, 0.0085), (0.0455, 0.0085), (0.049, 0.06), (0.045, 0.15), (0, 0.15)], liquido(c), 56))
    for k in range(14):  # alça
        a = math.pi * k / 13
        out.append(box(vidro()).xf((0.012, 0.01, 0.009), (0, 0, a), (0.052 + 0.03 * math.sin(a), 0.1 + 0.05 * math.cos(a), 0)))
    return out

def lata(c, r=0.033, h=0.122):  # lata padrão 350 ml (Ø 6,6 x 12,2 cm)
    mat('aluminio', '#c9ced3', 0.3, 0.9); mat('lata_cor', cor(c), 0.35, 0.4)
    corpo = [(0, 0.002), (r - 0.006, 0.002), (r - 0.003, 0), (r, 0.01), (r, h - 0.014), (r - 0.006, h - 0.002), (r - 0.0055, h), (0, h)]
    return [lathe(corpo, 'aluminio', 56),
            lathe([(r + 0.0004, 0.012), (r + 0.0004, h - 0.016)], 'lata_cor', 56),
            lathe([(r + 0.0004, h - 0.016), (r + 0.0004, 0.012)], 'lata_cor', 56)]

def garrafa_ks(c):  # vidro 290 ml
    pts = [(0.026, 0), (0.029, 0.01), (0.029, 0.06), (0.025, 0.08), (0.029, 0.11), (0.025, 0.14), (0.014, 0.175), (0.0115, 0.19), (0.0125, 0.195)]
    mat('vidro_ks', '#cfe3d9', 0.05, 0, 0.35); mat('tampinha', '#c0392b', 0.3, 0.6)
    return garrafa(pts, 'vidro_ks', liquido(c), 0.165, 'tampinha', 0.008)

def pet(c, tampa='#c0392b'):  # garrafa PET 1 L
    pts = [(0.036, 0), (0.042, 0.012), (0.042, 0.19), (0.038, 0.21), (0.016, 0.26), (0.0125, 0.27), (0.0135, 0.285)]
    mat('pet', '#e6f0f2', 0.08, 0, 0.3); mat('tampa_pet', cor(tampa), 0.4, 0)
    out = garrafa(pts, 'pet', liquido(c), 0.24, 'tampa_pet', 0.016)
    return out

def agua(c='agua', tampa='#2f6fd8'):  # garrafa 500 ml
    pts = [(0.03, 0), (0.033, 0.01), (0.033, 0.15), (0.029, 0.165), (0.0135, 0.19), (0.0125, 0.2), (0.0135, 0.205)]
    mat('pet_agua', '#e6f2f6', 0.06, 0, 0.28); mat('tampa_agua', cor(tampa), 0.4, 0)
    return garrafa(pts, 'pet_agua', liquido(c, alpha=0.35), 0.17, 'tampa_agua', 0.012)

def caipirinha(c):  # copo baixo ~ 300 ml
    rb, rt, h = 0.037, 0.043, 0.1
    out = [copo(rb, rt, h, fundo=0.012), enche(rb, rt, h, 0.085, liquido(c, alpha=0.6), fundo=0.012)] + cubos_gelo(0.038, 0.04, 0.075, 4)
    mat('limao', '#7cbf3a', 0.4)
    for i in range(3):
        out.append(ellip(0.016, 0.012, 0.009, 'limao', (0.012 * math.cos(i * 2.1), 0.03, 0.012 * math.sin(i * 2.1)), (0.4, i * 2.1, 0.6)))
    return out

def long_drink(c):  # copo long drink ~ 350 ml
    rb, rt, h = 0.032, 0.034, 0.15
    mat('canudo', '#1e1e1e', 0.4)
    return ([copo(rb, rt, h), enche(rb, rt, h, 0.13, liquido(c, alpha=0.7))] + cubos_gelo(0.032, 0.07, 0.12, 4)
            + [cyl(0.003, 0.2, 'canudo', 12).xf(r=(0.18, 0, 0.12), t=(0.008, 0.01, 0))])

def taca_balao(c, fruta='#f08a1c'):  # taça de Aperol/gin
    mat('fruta_taca', cor(fruta), 0.4)
    bowl = [(0, 0), (0.035, 0), (0.035, 0.003), (0.004, 0.006), (0.004, 0.1), (0.03, 0.115), (0.05, 0.15), (0.048, 0.2),
            (0.0455, 0.2), (0.0475, 0.15), (0.029, 0.118), (0.003, 0.104), (0, 0.104)]
    out = [lathe(bowl, vidro(), 56, crease=40)]
    out.append(lathe([(0, 0.105), (0.026, 0.118), (0.046, 0.15), (0.046, 0.17), (0, 0.17)], liquido(c, alpha=0.7), 56))
    out += [g.xf(t=(0, 0.06, 0)) for g in cubos_gelo(0.04, 0.06, 0.09, 3)]
    out.append(cyl(0.028, 0.004, 'fruta_taca', 32).xf(r=(math.pi / 2 - 0.2, 0, 0), t=(0.03, 0.16, 0)))
    return out

def cremoso(c):  # taça tulipa de drink cremoso
    pts = [(0.03, 0), (0.03, 0.006), (0.006, 0.012), (0.006, 0.05), (0.03, 0.08), (0.04, 0.12), (0.042, 0.17)]
    out = [lathe([(0, 0)] + pts + [(0.0395, 0.17), (0.0375, 0.12), (0.0275, 0.083), (0.004, 0.056), (0, 0.056)], vidro(), 48, crease=40)]
    out.append(lathe([(0, 0.057), (0.026, 0.084), (0.036, 0.12), (0.038, 0.155), (0.02, 0.172), (0, 0.176)], liquido(c, alpha=0.95), 48))
    return out

def cerveja(c_vidro='#6b3a12', alto=True):  # 600 ml (alto) ou long neck 330 ml
    if alto:
        pts = [(0.035, 0), (0.038, 0.008), (0.038, 0.17), (0.035, 0.19), (0.016, 0.245), (0.0135, 0.27), (0.0145, 0.285), (0.0135, 0.29)]
        nivel = 0.25
    else:
        pts = [(0.028, 0), (0.0305, 0.008), (0.0305, 0.12), (0.027, 0.14), (0.013, 0.18), (0.012, 0.215), (0.013, 0.225)]
        nivel = 0.19
    mat('vidro_cerveja', cor(c_vidro), 0.08, 0, 0.75); mat('tampinha', '#c9ced3', 0.3, 0.8)
    return garrafa(pts, 'vidro_cerveja', liquido('#e0a43a', alpha=0.9), nivel, 'tampinha', 0.008)

def chopp():  # tulipa 300 ml
    pts_out = [(0.028, 0), (0.028, 0.006), (0.005, 0.012), (0.005, 0.04), (0.025, 0.06), (0.036, 0.11), (0.032, 0.175)]
    out = [lathe([(0, 0)] + pts_out + [(0.0295, 0.175), (0.0335, 0.11), (0.023, 0.062), (0.003, 0.044), (0, 0.044)], vidro(), 48, crease=40)]
    out.append(lathe([(0, 0.045), (0.022, 0.063), (0.0325, 0.11), (0.0305, 0.15), (0, 0.15)], liquido('#e3a12f', alpha=0.85), 48))
    mat('espuma', '#fbf6ea', 0.7)
    out.append(lathe([(0, 0.15), (0.0305, 0.15), (0.03, 0.176), (0.018, 0.182), (0, 0.183)], 'espuma', 48))
    return out

def dose(c):  # copo de dose 50 ml
    rb, rt, h = 0.019, 0.023, 0.065
    return [copo(rb, rt, h, esp=0.003, fundo=0.014), enche(rb, rt, h, 0.05, liquido(c, alpha=0.65), esp=0.003, fundo=0.014)]

def whisky_dose(c='ambar'):  # copo baixo com 50 ml e gelo
    rb, rt, h = 0.04, 0.042, 0.088
    return [copo(rb, rt, h, fundo=0.014), enche(rb, rt, h, 0.035, liquido(c, alpha=0.7), fundo=0.014)] + cubos_gelo(0.036, 0.025, 0.05, 3)

def garrafa_destilado(c, tampa='#202224'):  # 700 ml – 1 L
    pts = [(0.04, 0), (0.043, 0.008), (0.043, 0.2), (0.036, 0.23), (0.016, 0.26), (0.0135, 0.29), (0.0145, 0.3)]
    mat('vidro_dest', '#eef4f4', 0.05, 0, 0.3); mat('tampa_dest', cor(tampa), 0.4, 0.3)
    return garrafa(pts, 'vidro_dest', liquido(c, alpha=0.6), 0.22, 'tampa_dest', 0.022)

def garrafa_whisky(c='ambar'):  # garrafa quadrada 1 L
    mat('vidro_wh', '#f1ece0', 0.05, 0, 0.3); mat('tampa_wh', '#2a2018', 0.4, 0.2)
    corpo = bloco_arredondado(0.088, 0.2, 0.088, 'vidro_wh', 0.2, (0, 0.1, 0))
    liq = bloco_arredondado(0.08, 0.17, 0.08, liquido(c, alpha=0.85), 0.2, (0, 0.09, 0))
    ombro = lathe([(0, 0.2), (0.05, 0.2), (0.03, 0.235), (0.015, 0.25), (0.0145, 0.275), (0, 0.275)], 'vidro_wh', 32)
    return [corpo, liq, ombro, cyl(0.0165, 0.025, 'tampa_wh', 24, 0.002).xf(t=(0, 0.265, 0))]

def vinho(c_vidro='#1f3a26', c_liq='tinto', capsula='#5a0d1c', espumante=False):  # 750 ml
    if espumante:
        pts = [(0.042, 0), (0.0445, 0.01), (0.0445, 0.17), (0.04, 0.2), (0.016, 0.26), (0.0145, 0.3), (0.0155, 0.31)]
    else:
        pts = [(0.034, 0), (0.0375, 0.01), (0.0375, 0.2), (0.033, 0.23), (0.0145, 0.26), (0.0145, 0.29), (0.0155, 0.3)]
    mat('vidro_vinho', cor(c_vidro), 0.08, 0, 0.8); mat('capsula', cor(capsula), 0.3, 0.6); mat('rotulo_vinho', '#f3eee2', 0.7)
    out = garrafa(pts, 'vidro_vinho', liquido(c_liq, alpha=0.95), 0.235, 'capsula', 0.06 if espumante else 0.045)
    r = pts[2][0] + 0.0006
    out += [lathe([(r, 0.06), (r, 0.14)], 'rotulo_vinho', 48), lathe([(r, 0.14), (r, 0.06)], 'rotulo_vinho', 48)]
    return out

# ---------------------------------------------------------------- comida
def _arroz(at, r=0.05, h=0.03):
    mat('arroz', '#f5f0e2', 0.9)
    return lathe([(0, 0), (r, 0), (r * 0.85, h * 0.5), (r * 0.5, h * 0.9), (0, h)], 'arroz', 40,
                 wobble=lambda t, y: 1 + 0.05 * math.sin(5 * t + y * 200)).xf(t=at)

def _salada(at, n=8, r=0.03):
    mat('folha', '#5f9e3a', 0.5); mat('tomate', '#d0321f', 0.35)
    g = np.random.default_rng(3); out = []
    for i in range(n):
        a = g.uniform(0, 6.28); rr = g.uniform(0, r)
        out.append(ellip(0.018, 0.003, 0.012, 'folha', (at[0] + rr * math.cos(a), at[1] + 0.004 + i * 0.0015, at[2] + rr * math.sin(a)), (g.uniform(-.4, .4), g.uniform(0, 3), 0), 5, 8))
    for i in range(3):
        out.append(cyl(0.012, 0.005, 'tomate', 20).xf(r=(0.3, 0, 0.2), t=(at[0] + 0.012 * (i - 1), at[1] + 0.012, at[2] + 0.01)))
    return out

def prato_principal(proteina):
    """Prato executivo: arroz, salada e a proteína (carne, frango, peixe, camarão, legumes)."""
    p, f = prato(0.135, 0.095); out = [p]; g = np.random.default_rng(11)
    out.append(_arroz((-0.045, f, -0.04)))
    out += _salada((-0.05, f, 0.05))
    if proteina == 'carne':
        mat('carne', '#6e3519', 0.6)
        out.append(jitter(bloco_arredondado(0.11, 0.018, 0.075, 'carne', 0.35, (0.04, f + 0.009, 0.005), (0, 0.4, 0)), 0.0008))
    elif proteina == 'frango':
        mat('frango', '#d39a4f', 0.55)
        out.append(jitter(bloco_arredondado(0.12, 0.02, 0.07, 'frango', 0.4, (0.04, f + 0.01, 0.005), (0, 0.3, 0)), 0.0008))
    elif proteina == 'peixe':
        mat('peixe', '#f1dcb8', 0.5); mat('limao', '#e5e07a', 0.4); mat('grelha', '#9c6a32', 0.6)
        out.append(jitter(bloco_arredondado(0.13, 0.016, 0.06, 'peixe', 0.45, (0.04, f + 0.008, 0.0), (0, 0.5, 0)), 0.0006))
        for k in range(4):
            out.append(box('grelha').xf((0.004, 0.001, 0.055), (0, 0.5 + 0.6, 0), (0.005 + k * 0.022, f + 0.0163, 0.02 - k * 0.012)))
        out.append(ellip(0.02, 0.012, 0.012, 'limao', (0.1, f + 0.01, 0.045)))
    elif proteina == 'camarao':
        mat('camarao', '#ef8a5a', 0.45); mat('camarao_claro', '#f6c7a2', 0.5)
        for i in range(6):
            a = -1.0 + i * 0.42; x = 0.035 + 0.045 * math.cos(a); z = 0.055 * math.sin(a)
            for k in range(7):  # gomos em arco (camarão de ~8 cm)
                t = k / 6 * 2.6
                out.append(ellip(0.012 - k * 0.001, 0.009 - k * 0.0007, 0.011, 'camarao' if k % 2 == 0 else 'camarao_claro',
                                 (x + 0.02 * math.cos(t + a), f + 0.009 + 0.002 * (i % 2), z + 0.02 * math.sin(t + a)), (0, -t, 0), 6, 8))
    elif proteina == 'legumes':
        for nome, c in (('abobrinha', '#7da34a'), ('cenoura', '#e8892b'), ('pimentao', '#c8301e'), ('berinjela', '#4a2a4f')):
            mat(nome, c, 0.5)
        for i in range(22):
            m = ['abobrinha', 'cenoura', 'pimentao', 'berinjela'][i % 4]; a = g.uniform(0, 6.28); r = g.uniform(0, 0.045)
            out.append(cyl(0.012, 0.007, m, 16).xf(r=(g.uniform(0, 1), 0, g.uniform(0, 1)), t=(0.04 + r * math.cos(a), f + 0.006 + g.uniform(0, 0.01), r * math.sin(a))))
    return out

def massa():
    p, f = prato(0.13, 0.08, 0.035); out = [p]; g = np.random.default_rng(5)
    mat('macarrao', '#f0cf7a', 0.5); mat('molho_tomate', '#b5301c', 0.4); mat('parmesao', '#f6efd6', 0.7)
    for i in range(40):  # fios enrolados
        a = g.uniform(0, 6.28); r = g.uniform(0, 0.055)
        out.append(cyl(0.0025, 0.12, 'macarrao', 8).xf(r=(math.pi / 2 + g.uniform(-.3, .3), g.uniform(0, 3), 0), t=(r * math.cos(a), f + 0.006 + g.uniform(0, 0.025) * (1 - r / 0.06), r * math.sin(a))))
    out.append(lathe([(0, 0), (0.04, 0), (0.03, 0.01), (0, 0.014)], 'molho_tomate', 32, wobble=lambda t, y: 1 + 0.15 * math.sin(4 * t)).xf(t=(0, f + 0.026, 0)))
    out.append(ellip(0.025, 0.003, 0.02, 'parmesao', (0.005, f + 0.04, 0)))
    return out

def risoto():
    p, f = prato(0.13, 0.08, 0.035); out = [p]
    mat('risoto', '#f1dca0', 0.45); mat('camarao', '#ef8a5a', 0.45)
    out.append(lathe([(0, 0), (0.07, 0), (0.06, 0.012), (0.03, 0.02), (0, 0.022)], 'risoto', 48, wobble=lambda t, y: 1 + 0.04 * math.sin(6 * t)).xf(t=(0, f, 0)))
    for i in range(6):
        a = i * 1.05
        out.append(ellip(0.012, 0.006, 0.007, 'camarao', (0.035 * math.cos(a), f + 0.022, 0.035 * math.sin(a)), (0, -a, 0)))
    return out

def travessa_mar(tipo='mar'):
    """Travessa oval de 40 x 28 cm com frutos do mar (lagosta, polvo, camarões, mexilhões)."""
    mat('travessa', '#f4f3ef', 0.22); mat('camarao', '#ef8a5a', 0.45); mat('mexilhao', '#2b2b38', 0.3)
    mat('polvo', '#a8455a', 0.4); mat('limao', '#e5e07a', 0.4); mat('lagosta', '#d9502a', 0.35)
    out = [lathe([(0, 0), (0.17, 0), (0.19, 0.022), (0.2, 0.026), (0.185, 0.026), (0.165, 0.008), (0, 0.008)], 'travessa', 64).xf((1, 1, 0.7))]
    g = np.random.default_rng(9); f = 0.008
    out.append(_arroz((-0.07, f, 0), 0.06, 0.03).xf((1, 1, 0.9)))
    if tipo in ('mar', 'lagosta'):
        out.append(bloco_arredondado(0.16, 0.035, 0.05, 'lagosta', 0.5, (0.06, f + 0.017, 0.0), (0, 0.15, 0)))
    for i in range(10):
        a = g.uniform(0, 6.28); r = g.uniform(0.03, 0.12)
        x, z = r * math.cos(a), r * math.sin(a) * 0.6
        if i % 2: out.append(ellip(0.02, 0.008, 0.011, 'mexilhao', (x, f + 0.03, z), (0, g.uniform(0, 3), 0)))
        else: out.append(ellip(0.013, 0.007, 0.008, 'camarao', (x, f + 0.03, z), (0, g.uniform(0, 3), 0)))
    if tipo == 'polvo':
        for i in range(5):
            a = i * 1.2
            for k in range(8):
                t = k / 7
                out.append(ellip(0.009 - t * 0.005, 0.006 - t * 0.003, 0.009 - t * 0.005, 'polvo', (0.05 + (0.02 + 0.07 * t) * math.cos(a + t), f + 0.012, (0.02 + 0.07 * t) * math.sin(a + t) * 0.7), la=6, lo=8))
    out.append(ellip(0.022, 0.013, 0.013, 'limao', (0.15, f + 0.012, 0.07)))
    return out

def paella():  # panela de paella Ø 38 cm
    mat('panela', '#3a3c3f', 0.4, 0.7); mat('paella', '#e4a63a', 0.6); mat('camarao', '#ef8a5a', 0.45)
    mat('mexilhao', '#2b2b38', 0.3); mat('ervilha', '#5c9a3a', 0.5); mat('pimentao', '#c8301e', 0.5); mat('limao', '#e5e07a', 0.4)
    out = [lathe([(0, 0), (0.17, 0), (0.19, 0.045), (0.193, 0.045), (0.173, 0.003), (0, 0.003)], 'panela', 72).xf()]
    for s in (-1, 1):
        out.append(box('panela').xf((0.05, 0.006, 0.03), t=(s * 0.215, 0.04, 0)))
    out.append(lathe([(0, 0.003), (0.172, 0.003), (0.185, 0.03), (0, 0.032)], 'paella', 72, wobble=lambda t, y: 1).xf())
    g = np.random.default_rng(4)
    for i in range(70):
        a = g.uniform(0, 6.28); r = math.sqrt(g.uniform(0, 1)) * 0.16
        m = ['ervilha', 'pimentao'][i % 2]
        out.append(box(m).xf((0.007, 0.004, 0.007), (0, g.uniform(0, 3), 0), (r * math.cos(a), 0.033, r * math.sin(a))))
    for i in range(10):
        a = i * 0.628; r = 0.11
        out.append(ellip(0.02, 0.008, 0.011, 'mexilhao' if i % 2 else 'camarao', (r * math.cos(a), 0.038, r * math.sin(a)), (0, -a, 0)))
    for i in range(4):
        out.append(ellip(0.022, 0.012, 0.012, 'limao', (0.05 * math.cos(i * 1.57 + .7), 0.04, 0.05 * math.sin(i * 1.57 + .7))))
    return out

def tabua_carne():
    """Tábua 38 x 26 cm com corte fatiado, farofa, vinagrete e mandioca."""
    mat('carne', '#6e3519', 0.6); mat('carne_ponto', '#b4534a', 0.55); mat('gordura', '#efe0c0', 0.5)
    mat('farofa', '#d8b06a', 0.95); mat('vinagrete', '#d23a26', 0.4); mat('mandioca', '#e9c97c', 0.7); mat('cumbuca', '#3d3a36', 0.5)
    out = [box('madeira').xf((0.38, 0.022, 0.26), t=(0, 0.011, 0))]; y = 0.022
    for i in range(7):
        x = -0.07 + i * 0.022
        out.append(box('carne').xf((0.018, 0.03, 0.1), (0, 0, 0.25), (x, y + 0.016, -0.03)))
        out.append(box('carne_ponto').xf((0.0186, 0.022, 0.092), (0, 0, 0.25), (x, y + 0.016, -0.03)))
        out.append(box('gordura').xf((0.019, 0.03, 0.012), (0, 0, 0.25), (x, y + 0.016, 0.026)))
    for (x, z, m) in ((0.12, -0.06, 'farofa'), (0.12, 0.06, 'vinagrete')):
        out.append(lathe([(0, 0), (0.035, 0), (0.042, 0.035), (0.039, 0.035), (0.032, 0.004), (0, 0.004)], 'cumbuca', 40).xf(t=(x, y, z)))
        out.append(lathe([(0, 0.004), (0.038, 0.004), (0.039, 0.03), (0, 0.033)], m, 40).xf(t=(x, y, z)))
    g = np.random.default_rng(2)
    for i in range(6):
        out.append(box('mandioca').xf((0.02, 0.018, 0.07), (0, g.uniform(-.4, .4), 0), (-0.03 + i * 0.022, y + 0.01 + (i % 2) * 0.01, 0.085)))
    return out

def espeto(tipo):
    """Espeto de ~30 cm sobre prato/tábua com farofa."""
    cores = dict(carne=('#7a3b22', '#7a3b22'), frango=('#d39a4f', '#c6873d'), queijo=('#f2dc9b', '#b87a33'),
                 linguica=('#8e3a24', '#8e3a24'), medalhao=('#7a3b22', '#a3242a'))
    a, b = cores[tipo]
    mat('pedaco_a', a, 0.55); mat('pedaco_b', b, 0.55); mat('palito', '#d8b77a', 0.7); mat('farofa', '#d8b06a', 0.95)
    out = [box('madeira').xf((0.34, 0.018, 0.12), t=(0, 0.009, 0))]; y = 0.018 + 0.02
    out.append(cyl(0.003, 0.34, 'palito', 10).xf(r=(0, 0, math.pi / 2), t=(0.17, y, 0)))
    for i in range(6):
        x = -0.1 + i * 0.035
        if tipo == 'queijo':
            out.append(box('pedaco_a').xf((0.07, 0.022, 0.03), t=(x * 0 + -0.05, y, 0)) if i == 0 else box('pedaco_b').xf((0.002, 0.0222, 0.031), t=(-0.075 + i * 0.01, y + 0.0001, 0)))
        elif tipo == 'linguica':
            if i < 2: out.append(lathe([(0, 0), (0.016, 0.006), (0.016, 0.08), (0, 0.086)], 'pedaco_a', 20).xf(r=(0, 0, math.pi / 2), t=(-0.07 + i * 0.09 + 0.043, y, 0)))
        elif tipo == 'medalhao':
            if i < 4:
                out.append(cyl(0.024, 0.026, 'pedaco_b', 24, 0.004).xf(r=(0, 0, math.pi / 2), t=(x + 0.013, y, 0)))
                out.append(cyl(0.02, 0.0262, 'pedaco_a', 24).xf(r=(0, 0, math.pi / 2), t=(x + 0.0131, y, 0)))
        else:
            out.append(jitter(bloco_arredondado(0.03, 0.03, 0.03, 'pedaco_a' if i % 2 == 0 else 'pedaco_b', 0.5, (x, y, 0), (0.3 * i, 0.2, 0)), 0.0008))
    if tipo == 'queijo':
        out = out[:2] + [bloco_arredondado(0.1, 0.022, 0.032, 'pedaco_a', 0.35, (-0.03, y, 0))] + [box('pedaco_b').xf((0.003, 0.0225, 0.033), t=(-0.07 + k * 0.016, y, 0)) for k in range(6)]
    out.append(lathe([(0, 0), (0.035, 0), (0.025, 0.01), (0, 0.014)], 'farofa', 32).xf(t=(0.12, 0.018, 0.035)))
    return out

def tabua_linguica():
    mat('linguica', '#8e3a24', 0.5); mat('pao', '#d9a35b', 0.7); mat('vinagrete', '#d23a26', 0.4)
    out = [tabua_redonda(0.15, 0.02)]; y = 0.02
    for i in range(3):
        out.append(jitter(lathe([(0, 0), (0.017, 0.008), (0.017, 0.12), (0, 0.128)], 'linguica', 20), 0.0005).xf(r=(0, i * 0.35 - 0.35, math.pi / 2), t=(0.064, y + 0.017, -0.04 + i * 0.04)))
    for i in range(4):
        out.append(bloco_arredondado(0.03, 0.018, 0.025, 'pao', 0.5, (-0.08, y + 0.009, -0.045 + i * 0.03)))
    out.append(lathe([(0, 0), (0.025, 0), (0.02, 0.008), (0, 0.01)], 'vinagrete', 24).xf(t=(0.0, y, 0.09)))
    return out

def porcao(tipo):
    """Porção em travessa/cestinha: batata, bolinhas, frituras em geral, camarão."""
    mat('papel', '#e9e7e1', 0.85); mat('cesta', '#2e2b28', 0.6)
    mat('frito', '#d79b3f', 0.7); mat('frito_b', '#c47f2c', 0.7); mat('batata', '#eab64e', 0.7); mat('camarao', '#ef8a5a', 0.45); mat('limao', '#e5e07a', 0.4)
    out = [lathe([(0, 0), (0.1, 0), (0.12, 0.05), (0.117, 0.05), (0.097, 0.004), (0, 0.004)], 'cesta', 48).xf((1, 1, 0.75))]
    out.append(lathe([(0, 0.004), (0.098, 0.004), (0.112, 0.04), (0.11, 0.04), (0.096, 0.006), (0, 0.006)], 'papel', 48).xf((1, 1, 0.75)))
    g = np.random.default_rng(6)
    for i in range(45 if tipo == 'batata' else 26):
        a = g.uniform(0, 6.28); r = math.sqrt(g.uniform(0, 1)) * 0.065; x, z = r * math.cos(a), r * math.sin(a) * 0.65
        h = 0.012 + g.uniform(0, 0.03) * (1 - r / 0.08)
        if tipo == 'batata':
            ang = math.atan2(z, x) + math.pi / 2 + g.uniform(-.5, .5)  # deitadas ao longo da cestinha
            out.append(box('batata').xf((0.01, 0.01, g.uniform(0.045, 0.065)), (g.uniform(-.25, .25), -ang, 0), (x * 0.8, h, z * 0.8)))
        elif tipo == 'bolinhas':
            out.append(jitter(ellip(0.015, 0.014, 0.015, 'frito' if i % 2 else 'frito_b', (x, h + 0.008, z), la=10, lo=12), 0.0006))
        elif tipo == 'camarao':
            out.append(ellip(0.016, 0.008, 0.009, 'camarao', (x, h, z), (0, g.uniform(0, 3), 0.3)))
        else:
            out.append(jitter(bloco_arredondado(0.035, 0.016, 0.022, 'frito' if i % 2 else 'frito_b', 0.45, (x, h + 0.004, z), (0, g.uniform(0, 3), g.uniform(-.3, .3)), la=10, lo=14), 0.0008))
    out.append(ellip(0.02, 0.012, 0.012, 'limao', (0.07, 0.03, 0.04)))
    return out

def ostras():
    mat('travessa', '#f4f3ef', 0.22); mat('concha', '#9a958a', 0.7); mat('ostra', '#e8dcc6', 0.3); mat('gelo_moido', '#f2f7f9', 0.3); mat('limao', '#e5e07a', 0.4)
    out = [lathe([(0, 0), (0.15, 0), (0.16, 0.02), (0.157, 0.02), (0.147, 0.006), (0, 0.006)], 'travessa', 64)]
    out.append(lathe([(0, 0.006), (0.148, 0.006), (0.14, 0.014), (0, 0.016)], 'gelo_moido', 48))
    for i in range(6):
        a = i * 1.047
        out.append(ellip(0.04, 0.009, 0.03, 'concha', (0.09 * math.cos(a), 0.022, 0.09 * math.sin(a)), (0, -a, 0)))
        out.append(ellip(0.025, 0.006, 0.018, 'ostra', (0.09 * math.cos(a), 0.028, 0.09 * math.sin(a)), (0, -a, 0)))
    out.append(ellip(0.024, 0.014, 0.014, 'limao', (0, 0.025, 0)))
    return out

def caranguejo():
    mat('travessa', '#f4f3ef', 0.22); mat('carapaca', '#d0482a', 0.45); mat('pata', '#e0613a', 0.45)
    out = [lathe([(0, 0), (0.15, 0), (0.16, 0.02), (0.157, 0.02), (0.147, 0.006), (0, 0.006)], 'travessa', 64)]
    for j, (cx, cz) in enumerate(((-0.06, -0.03), (0.06, -0.02), (0, 0.06))):
        out.append(jitter(ellip(0.045, 0.02, 0.035, 'carapaca', (cx, 0.026, cz), la=12, lo=16), 0.0008))
        for k in range(4):
            for s in (-1, 1):
                a = s * (0.6 + k * 0.3)
                out.append(cyl(0.004, 0.05, 'pata', 8).xf(r=(0, a, math.pi / 2 - 0.4 * s), t=(cx + s * 0.03, 0.02, cz + (k - 1.5) * 0.012)))
    return out

def cumbuca(c, cobertura=None):  # cumbuca de barro Ø 16 cm (guarnições, caldos)
    mat('barro', '#6b3e26', 0.6); mat('recheio', cor(c), 0.6)
    out = [lathe([(0, 0), (0.05, 0), (0.07, 0.03), (0.08, 0.06), (0.076, 0.06), (0.066, 0.032), (0.048, 0.008), (0, 0.008)], 'barro', 56)]
    out.append(lathe([(0, 0.008), (0.049, 0.008), (0.067, 0.033), (0.075, 0.052), (0.05, 0.058), (0, 0.06)], 'recheio', 56,
                     wobble=lambda t, y: 1 + 0.02 * math.sin(6 * t)))
    if cobertura:
        mat('cobertura', cor(cobertura), 0.5); g = np.random.default_rng(1)
        for i in range(30):
            a = g.uniform(0, 6.28); r = g.uniform(0, 0.06)
            out.append(box('cobertura').xf((0.006, 0.004, 0.006), (0, g.uniform(0, 3), 0), (r * math.cos(a), 0.06 - r * 0.1, r * math.sin(a))))
    return out

def caldo():
    mat('barro', '#6b3e26', 0.6); mat('caldo', '#5a3520', 0.2); mat('cheiro_verde', '#4f8f3a', 0.5)
    out = [lathe([(0, 0), (0.04, 0), (0.06, 0.04), (0.062, 0.075), (0.058, 0.075), (0.056, 0.042), (0.038, 0.008), (0, 0.008)], 'barro', 48)]
    out.append(lathe([(0, 0.008), (0.039, 0.008), (0.057, 0.045), (0.058, 0.06), (0, 0.06)], 'caldo', 48))
    g = np.random.default_rng(8)
    for i in range(18):
        a = g.uniform(0, 6.28); r = g.uniform(0, 0.045)
        out.append(box('cheiro_verde').xf((0.004, 0.001, 0.004), (0, g.uniform(0, 3), 0), (r * math.cos(a), 0.0605, r * math.sin(a))))
    return out

def salada():  # saladeira Ø 24 cm
    mat('saladeira', '#f4f3ef', 0.25); mat('folha', '#5f9e3a', 0.5); mat('folha_b', '#8cc152', 0.5); mat('tomate', '#d0321f', 0.35); mat('cenoura', '#e8892b', 0.5)
    out = [lathe([(0, 0), (0.06, 0), (0.1, 0.04), (0.12, 0.07), (0.116, 0.07), (0.096, 0.044), (0.058, 0.008), (0, 0.008)], 'saladeira', 56)]
    g = np.random.default_rng(12)
    for i in range(55):
        a = g.uniform(0, 6.28); r = math.sqrt(g.uniform(0, 1)) * 0.095
        out.append(ellip(0.025, 0.003, 0.016, 'folha' if i % 2 else 'folha_b', (r * math.cos(a), 0.03 + 0.035 * (r / 0.1) + g.uniform(0, 0.02), r * math.sin(a)), (g.uniform(-.6, .6), g.uniform(0, 3), g.uniform(-.4, .4)), 5, 8))
    for i in range(8):
        a = i * 0.785
        out.append(ellip(0.013, 0.012, 0.013, 'tomate', (0.05 * math.cos(a), 0.07, 0.05 * math.sin(a))))
    for i in range(20):
        a = g.uniform(0, 6.28); r = g.uniform(0, 0.07)
        out.append(box('cenoura').xf((0.003, 0.003, 0.03), (0, g.uniform(0, 3), 0), (r * math.cos(a), 0.072, r * math.sin(a))))
    return out

def carpaccio():
    p, f = prato(0.14, 0.11, 0.02); out = [p]
    mat('carpaccio', '#a8323a', 0.4); mat('rucula', '#4f8f3a', 0.5); mat('parmesao', '#f6efd6', 0.7); mat('torrada', '#d8a35b', 0.7)
    for i in range(12):
        a = i * 0.5236
        out.append(cyl(0.035, 0.002, 'carpaccio', 24).xf((1, 1, 0.8), (0, a, 0), (0.06 * math.cos(a), f + i * 0.0002, 0.06 * math.sin(a))))
    out += [g.xf(t=(0, 0, 0)) for g in _salada((0, f, 0), 6, 0.02)][:6]
    for i in range(4):
        out.append(box('torrada').xf((0.05, 0.008, 0.025), (0, i * 0.8, 0), (0.1 * math.cos(i * 1.57 + 0.78), f + 0.006, 0.1 * math.sin(i * 1.57 + 0.78))))
    return out

def sobremesa(tipo):
    p, f = prato(0.1, 0.07, 0.018); out = [p]
    mat('massa_torta', '#d9a35b', 0.7); mat('recheio_torta', '#f4e08a', 0.4); mat('brownie', '#3f2416', 0.6); mat('sorvete', '#f3e6c6', 0.55)
    mat('calda', '#2a1208', 0.1); mat('chantilly', '#fbf7ee', 0.6)
    if tipo == 'torta':
        out.append(cyl(0.045, 0.03, 'massa_torta', 48, 0.004).xf(t=(0, f, 0)))
        out.append(cyl(0.041, 0.006, 'recheio_torta', 48).xf(t=(0, f + 0.027, 0)))
        for i in range(8):
            a = i * 0.785
            out.append(ellip(0.008, 0.008, 0.008, 'chantilly', (0.03 * math.cos(a), f + 0.035, 0.03 * math.sin(a)), la=8, lo=10))
    else:
        out.append(jitter(bloco_arredondado(0.07, 0.035, 0.06, 'brownie', 0.3, (-0.02, f + 0.0175, 0)), 0.0006))
        out.append(jitter(ellip(0.03, 0.025, 0.03, 'sorvete', (0.035, f + 0.022, 0.02), la=14, lo=20), 0.001))
        for i in range(7):
            out.append(ellip(0.018, 0.0025, 0.004, 'calda', (-0.02 + i * 0.01, f + 0.036 - (0.01 if i > 4 else 0), 0.012 * math.sin(i)), (0, i * 0.4, 0), 5, 8))
    return out

def baguete():
    mat('pao', '#d9a35b', 0.7); mat('recheio', '#7a3b22', 0.6); mat('folha', '#5f9e3a', 0.5); mat('batata', '#eab64e', 0.7)
    out = [box('madeira').xf((0.34, 0.018, 0.18), t=(0, 0.009, 0))]; y = 0.018
    for s in (-1, 1):
        out.append(bloco_arredondado(0.12, 0.05, 0.065, 'pao', 0.45, (s * 0.07, y + 0.025, -0.02)))
        out.append(box('recheio').xf((0.115, 0.014, 0.06), t=(s * 0.07, y + 0.05, -0.02)))
        out.append(box('folha').xf((0.12, 0.004, 0.068), t=(s * 0.07, y + 0.058, -0.02)))
    g = np.random.default_rng(13)
    for i in range(16):
        out.append(box('batata').xf((0.009, 0.009, 0.06), (g.uniform(-.2, .2), g.uniform(0, 3), 0), (g.uniform(-0.1, 0.1), y + 0.006 + g.uniform(0, 0.015), 0.055)))
    return out

# ---------------------------------------------------------------- catálogo
def construir(mid):
    tipo, _, c = mid.partition('-')
    if tipo == 'copo_suco': return copo_suco(c)
    if tipo == 'jarra': return jarra(c)
    if tipo == 'lata': return lata(c)
    if tipo == 'lata_slim': return lata(c, 0.0265, 0.134)
    if tipo == 'lata_alta': return lata(c, 0.033, 0.168)
    if tipo == 'ks': return garrafa_ks(c)
    if tipo == 'pet': return pet(c)
    if tipo == 'agua': return agua(c or 'agua')
    if tipo == 'caipirinha': return caipirinha(c)
    if tipo == 'long_drink': return long_drink(c)
    if tipo == 'taca': return taca_balao(c, '#f08a1c' if c in ('laranja', 'vermelho') else '#7cbf3a')
    if tipo == 'cremoso': return cremoso(c)
    if tipo == 'cerveja600': return cerveja(c or 'vidro_ambar', True)
    if tipo == 'longneck': return cerveja(c or 'vidro_ambar', False)
    if tipo == 'chopp': return chopp()
    if tipo == 'dose': return dose(c)
    if tipo == 'whisky_dose': return whisky_dose(c or 'ambar')
    if tipo == 'garrafa': return garrafa_destilado(c)
    if tipo == 'garrafa_whisky': return garrafa_whisky(c or 'ambar')
    if tipo == 'vinho_tinto': return vinho('#1f3a26', 'tinto', '#5a0d1c')
    if tipo == 'vinho_branco': return vinho('#b9cf9a', 'branco_vinho', '#d9a441')
    if tipo == 'vinho_rose': return vinho('#f0d6d2', 'rose', '#d98a9a')
    if tipo == 'espumante': return vinho('#1f3a26', 'branco_vinho', '#d9a441', espumante=True)
    if tipo == 'espumante_rose': return vinho('#e9c8c4', 'rose', '#d98a9a', espumante=True)
    if tipo == 'prato': return prato_principal(c)
    if tipo == 'massa': return massa()
    if tipo == 'risoto': return risoto()
    if tipo == 'travessa': return travessa_mar(c or 'mar')
    if tipo == 'paella': return paella()
    if tipo == 'tabua_carne': return tabua_carne()
    if tipo == 'costelao': return costelao()
    if tipo == 'espeto': return espeto(c)
    if tipo == 'tabua_linguica': return tabua_linguica()
    if tipo == 'porcao': return porcao(c)
    if tipo == 'ostras': return ostras()
    if tipo == 'caranguejo': return caranguejo()
    if tipo == 'cumbuca': return cumbuca(*(c.split('+') if '+' in c else (c,)))
    if tipo == 'caldo': return caldo()
    if tipo == 'salada': return salada()
    if tipo == 'carpaccio': return carpaccio()
    if tipo == 'sobremesa': return sobremesa(c)
    if tipo == 'petit_gateau': return petit_gateau()
    if tipo == 'burger': return burger()
    if tipo == 'baguete': return baguete()
    raise ValueError('modelo desconhecido: ' + mid)

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for mid in sys.argv[2:]:
        dims, size = write_glb(os.path.join(out, mid + '.glb'), construir(mid), mid)
        print(f'{mid:28s} {dims[0]*100:5.1f} x {dims[1]*100:5.1f} x {dims[2]*100:5.1f} cm  {size/1024:5.0f} KB')
