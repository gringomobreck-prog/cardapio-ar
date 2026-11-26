"""Monta site/cardapio.json a partir do cardápio do CAIS no dguests, escolhendo o modelo 3D de cada item.

Uso: python3 tools/montar_cardapio_cais.py dados/dguests_caisbarerestaurante.json site/cardapio.json
Imprime a lista de modelos usados (para gerar com tools/modelos_cais.py).
"""
import json, re, sys, unicodedata

def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', s)

def tem(n, *ks):
    return any(k in n for k in ks)

FRUTAS = [('LARANJA COM MORANGO', 'laranja'), ('ABACAXI', 'amarelo'), ('CAJA', 'amarelo'), ('GOIABA', 'rosa'), ('GRAVIOLA', 'branco'),
          ('ACEROLA', 'vermelho'), ('MANGA', 'laranja'), ('CAJU', 'laranja'), ('MARACUJA', 'amarelo'), ('LIMAO', 'verde'),
          ('LARANJA', 'laranja'), ('MORANGO', 'vermelho'), ('KIWI', 'verde'), ('TANGERINA', 'laranja'), ('SIRIGUELA', 'laranja'),
          ('PITAYA', 'rosa'), ('UVA', 'roxo'), ('BERRY', 'roxo'), ('PINK', 'rosa'), ('AZUL', 'azul')]

def fruta(n, padrao):
    for k, c in FRUTAS:
        if k in n: return c
    return padrao

def modelo(cat, nome):
    """Retorna (id do modelo, texto da medida real)."""
    c, n = norm(cat), norm(nome)
    # ---------------- bebidas
    if c.startswith('SUCOS COPO'): return f'copo_suco-{fruta(n, "laranja")}', 'copo long neck 300 ml · 15 cm de altura'
    if c.startswith('SUCOS JARRA'): return f'jarra-{fruta(n, "laranja")}', 'jarra 700 ml · 19 cm de altura'
    if c.startswith('REFRI LATA') or (c == 'AGUA' and 'TONICA' in n):
        corl = 'laranja' if 'FANTA LARANJA' in n else 'roxo' if 'UVA' in n else 'verde_lata' if tem(n, 'SPRITE', 'GUARANA') else 'amarelo' if 'SCHWEPPES' in n else 'cinza'
        return f'lata-{corl}', 'lata 350 ml · 12,2 cm de altura'
    if c == 'AGUA': return 'agua', 'garrafa 500 ml · 20 cm de altura'
    if c.startswith('REFRI KS'):
        return f'ks-{"escuro" if "COCA" in n else "claro" if "SPRITE" in n else "laranja"}', 'garrafa de vidro 290 ml · 19,5 cm'
    if c.startswith('REFRI 1 LITRO'): return f'pet-{"escuro" if "COCA" in n else "guarana"}', 'garrafa 1 litro · 28,5 cm de altura'
    if c.startswith('ENERGETICOS'):
        if 'MONSTER' in n: return 'lata_alta-preta', 'lata 473 ml · 16,8 cm de altura'
        return 'lata_slim-azul', 'lata 250 ml · 13,4 cm de altura'
    if 'CAIPIS' in c:
        if 'COQUETEL' in n: return f'long_drink-{fruta(n, "laranja")}', 'copo long drink 350 ml'
        return f'caipirinha-{fruta(n, "verde" if "CAIPIRINHA" == n.strip() else "claro")}', 'copo baixo 300 ml · 10 cm de altura'
    if 'CLASSICOS' in c or 'AUTORAIS' in c:
        if tem(n, 'GIN'): return f'taca-{fruta(n, "claro")}', 'taça balão · 20 cm de altura'
        if 'NEGRONI' in n: return 'caipirinha-vermelho', 'copo baixo 300 ml · 10 cm de altura'
        corl = ('azul' if tem(n, 'LAGOA AZUL', 'INTERESTELAR') else 'laranja' if tem(n, 'SUNRISE', 'SEX ON', 'MARACUJ') else
                'rosa' if tem(n, 'COSMOPOLITAN') else 'roxo' if tem(n, 'UVA', 'BERRY') else 'claro' if tem(n, 'MOJITO CLASSICO', 'MULLER', 'MARGARITA', 'CORONITA') else fruta(n, 'claro'))
        return f'long_drink-{corl}', 'copo long drink 350 ml · 15 cm de altura'
    if 'CAFE & CREMOSOS' in c or 'CAFE E CREMOSOS' in c: return 'cremoso-cafe', 'taça 300 ml · 17 cm de altura'
    if 'SEM ALCOOL' in c and 'DRINK' in c:
        if 'CREMOSO' in n: return f'cremoso-{fruta(n, "creme")}', 'taça 300 ml · 17 cm de altura'
        return f'long_drink-{fruta(n, "rosa")}', 'copo long drink 350 ml · 15 cm de altura'
    if 'APEROL' in c: return 'taca-laranja', 'taça balão · 20 cm de altura'
    if c.startswith('CERVEJA 600'):
        return f'cerveja600-{"vidro_verde" if tem(n, "HEINEKEN", "STELLA") else "vidro_claro" if "CORONA" in n else "vidro_ambar"}', 'garrafa 600 ml · 29 cm de altura'
    if c.startswith('CERVEJA CHOPP'): return 'chopp', 'tulipa 300 ml · 18 cm de altura'
    if c.startswith('CERVEJA LONG') or c.startswith('CERVEJA SEM'):
        corv = 'vidro_verde' if tem(n, 'HEINEKEN', 'STELLA') else 'vidro_claro' if tem(n, 'CORONA', 'SMIRNOFF') else 'vidro_azul' if tem(n, 'BEATS', 'MICHELOB') else 'vidro_ambar'
        return f'longneck-{corv}', 'long neck 330 ml · 22,5 cm de altura'
    if c.startswith('CERVEJA LATA'): return 'lata-amarelo', 'lata 350 ml · 12,2 cm de altura'
    def destilado_cor():
        if 'CAMPARI' in n: return 'vermelho'
        if 'BAILEYS' in n: return 'creme'
        if 'JAGER' in n: return 'escuro'
        if tem(n, 'OURO', '150', '160', 'CONHAQUE', 'LICOR 43', 'BALLENA', 'BANANAZINHA', 'MARTINI'): return 'ambar'
        return 'claro'
    if c.startswith('DESTILADOS DOSE'): return f'dose-{destilado_cor()}', 'dose 50 ml · copo de 6,5 cm'
    if c.startswith('DESTILADOS LITRO'): return f'garrafa-{destilado_cor()}', 'garrafa 700 ml a 1 L · 30 cm de altura'
    if c.startswith('WHISKY DOSE'): return 'whisky_dose', 'dose 50 ml com gelo · copo de 8,8 cm'
    if c.startswith('WHISKY LITRO'): return 'garrafa_whisky', 'garrafa 1 L · 28 cm de altura'
    if c.startswith('VINHO TINTO'): return 'vinho_tinto', 'garrafa 750 ml · 30 cm de altura'
    if c.startswith('VINHO BRANCO'): return ('vinho_rose' if 'ROSE' in n else 'vinho_branco'), 'garrafa 750 ml · 30 cm de altura'
    if c.startswith('ESPUMANTE'): return ('espumante_rose' if 'ROSE' in n else 'espumante'), 'garrafa 750 ml · 31 cm de altura'
    # ---------------- comida
    if 'COSTELA 12' in n: return 'costelao', 'chapa 30 × 24 cm · tábua 40 × 30 cm'
    if 'PETIT GATEAU' in n: return 'petit_gateau', 'prato Ø 26 cm'
    if c.startswith('SOBREMESAS'):
        return ('sobremesa-sorvete' if tem(n, 'BROWNIE', 'COOKIE', 'CHOCOLATE') else 'sobremesa-torta'), 'prato Ø 20 cm'
    if c.startswith('SANDUICHES'):
        return ('burger', 'Ø 12 cm · tábua 30 × 20 cm') if 'BURGER' in n else ('baguete', 'tábua 34 × 18 cm')
    if c.startswith('SALADAS') or tem(n, 'SALADA', 'FOLHAS VERDES'): return 'salada', 'saladeira Ø 24 cm'
    if c.startswith('CALDOS'): return 'caldo', 'cumbuca Ø 12 cm'
    if c.startswith('GUARNICOES'):
        if 'BANANA' in n: return 'porcao-frito', 'cestinha 24 × 18 cm'
        if 'PURE' in n: return 'cumbuca-creme', 'cumbuca Ø 16 cm'
        if 'BAIAO' in n: return 'cumbuca-baiao', 'cumbuca Ø 16 cm'
        if tem(n, 'GREGA', 'BROCOLIS', 'CARRETEIRO', 'PIAMONTESE', 'PROVENCAL'):
            return 'cumbuca-branco+' + ('brocolis' if 'BROCOLIS' in n else 'legumes'), 'cumbuca Ø 16 cm'
        return 'cumbuca-branco', 'cumbuca Ø 16 cm'
    if c.startswith('LINGUICAS'): return 'tabua_linguica', 'tábua Ø 30 cm'
    if c.startswith('MEDALHOES'): return 'espeto-medalhao', 'espeto 34 cm · tábua 34 × 12 cm'
    if c.startswith('ESPETOS'):
        if 'QUEIJO' in n: return 'espeto-queijo', 'espeto 34 cm · tábua 34 × 12 cm'
        if tem(n, 'FRANGO', 'ASINHA', 'CORACAO DE FRANGO'): return 'espeto-frango', 'espeto 34 cm · tábua 34 × 12 cm'
        if 'LINGUICA' in n: return 'espeto-linguica', 'espeto 34 cm · tábua 34 × 12 cm'
        return 'espeto-carne', 'espeto 34 cm · tábua 34 × 12 cm'
    if 'ENTRADAS' in c:
        if 'CARPACCIO' in n: return 'carpaccio', 'prato Ø 28 cm'
        if 'OSTRA' in n: return 'ostras', 'travessa Ø 32 cm'
        if tem(n, 'CARANGUEJO', 'CASQUINHA') and 'PATINHA' not in n: return 'caranguejo', 'travessa Ø 32 cm'
        if tem(n, 'CAMARAO', 'PATINHA'): return 'porcao-camarao', 'cestinha 24 × 18 cm'
        if tem(n, 'BATATA', 'MACAXEIRA FRITA', 'CHIPPS', 'COM FRITAS', 'COM FRITA'): return 'porcao-batata', 'cestinha 24 × 18 cm'
        if tem(n, 'BOLINHA', 'CROQUETE', 'DADINHO'): return 'porcao-bolinhas', 'cestinha 24 × 18 cm'
        if tem(n, 'AZEITONA', 'FEIJAO VERDE'): return ('cumbuca-azeitona' if 'AZEITONA' in n else 'cumbuca-feijao_verde'), 'cumbuca Ø 16 cm'
        return 'porcao-frito', 'cestinha 24 × 18 cm'
    if c.startswith('FRUTOS DO MAR'):
        if tem(n, 'PAELLA', 'ARROZ DE CAMARAO', 'SACO DE MARISCO'): return 'paella', 'panela Ø 38 cm'
        if 'LAGOSTA' in n: return 'travessa-lagosta', 'travessa 40 × 28 cm'
        if 'POLVO' in n: return 'travessa-polvo', 'travessa 40 × 28 cm'
        if tem(n, 'TRIO', 'QUARTETO'): return 'travessa-mar', 'travessa 40 × 28 cm'
        if 'MASSA' in n: return 'massa', 'prato fundo Ø 26 cm'
        if n.startswith('PEIXE'): return 'prato-peixe', 'prato Ø 28 cm'
        return 'prato-camarao', 'prato Ø 28 cm'
    if c.startswith('CARNES (CORTES') or tem(n, 'TOMAHAWK', 'BISTECA', 'CARRE', 'COSTELINHA', 'FRALDINHA'):
        return 'tabua_carne', 'tábua 38 × 26 cm'
    if tem(n, 'MACARRAO', 'MASSA', 'FETTUCC', 'ESPAGUE', 'ESPAGETE', 'LASANHA'): return 'massa', 'prato fundo Ø 26 cm'
    if 'RISOTO' in n: return 'risoto', 'prato fundo Ø 26 cm'
    if tem(n, 'LEGUMES', 'RATATOUILLE'): return 'prato-legumes', 'prato Ø 28 cm'
    if 'CAMAR' in n: return 'prato-camarao', 'prato Ø 28 cm'
    if c.startswith('PEIXES') or tem(n, 'PEIXE', 'SALMAO', 'CAVALA', 'SAUNA', 'ATUM'): return 'prato-peixe', 'prato Ø 28 cm'
    if tem(n, 'FRANGO', 'COXA'): return 'prato-frango', 'prato Ø 28 cm'
    return 'prato-carne', 'prato Ø 28 cm'

BEBIDAS = ('SUCOS', 'REFRI', 'AGUA', 'DRINKS', 'CERVEJA', 'ENERGETICOS', 'DESTILADOS', 'WHISKY', 'VINHO', 'ESPUMANTE')

def titulo_bonito(s):
    s = re.sub(r'\s+', ' ', (s or '').strip())
    if s.isupper() or sum(ch.isupper() for ch in s) > len(s) * 0.6:
        pequenas = {'DE', 'DA', 'DO', 'DAS', 'DOS', 'E', 'COM', 'C/', 'A', 'À', 'AO', 'NA', 'NO', 'EM', 'OU'}
        palavras = s.split(' ')
        out = []
        for i, w in enumerate(palavras):
            lw = w.lower()
            if i and w in pequenas: out.append(lw)
            elif w in ('CAIS', 'KS', 'BBQ', 'ML', 'GR', 'UND') or re.fullmatch(r'\d+[A-Z]*', w): out.append(w if w != 'ML' else 'ml')
            else: out.append(lw[:1].upper() + lw[1:])
        s = ' '.join(out)
    return s

def main(src, dst):
    d = json.load(open(src))
    cats = []; usados = {}
    for c in d['categoria']:
        itens = []
        for p in c['estFinProdutos']:
            mid, medida = modelo(c['titulo'], p['titulo'])
            usados[mid] = usados.get(mid, 0) + 1
            foto = (p.get('foto') or '').split('?')[0]
            itens.append(dict(id=p['id'], nome=titulo_bonito(p['titulo']), desc=(p.get('detalhe') or '').strip(),
                              preco=p.get('preco'), promo=p.get('preco_promo'), pessoas=p.get('qtd_pessoas') or 0,
                              foto=('fotos/cais/' + foto.replace('.png', '.webp')) if foto else '', modelo=mid, medida=medida))
        grupo = 'Bebidas' if norm(c['titulo']).startswith(BEBIDAS) else 'Comidas'
        cats.append(dict(id=c['id'], nome=titulo_bonito(c['titulo']), grupo=grupo, itens=itens))
    json.dump(dict(restaurante='CAIS restaurante & bar', fonte='dguests.com.br/cardapio/caisbarerestaurante', categorias=cats),
              open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
    for k in sorted(usados): print(k, usados[k])
    print('TOTAL_MODELOS', len(usados), 'ITENS', sum(usados.values()))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
