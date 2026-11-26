# Cardápio CAIS em Realidade Aumentada

Cardápio do **CAIS restaurante & bar** em que cada prato e bebida aparece em 3D e pode ser colocado **em tamanho real** na mesa pela câmera do celular. Não precisa instalar app.

Endereço: https://gringomobreck-prog.github.io/cardapio-ar/ (QR code em `qrcode-mesa.png`).

| Aparelho | Como o AR abre |
|---|---|
| Android com ARCore (Chrome) | WebXR ou Google Scene Viewer |
| iPhone / iPad (Safari) | AR Quick Look |
| Computador | Só o visualizador 3D |

## O que tem aqui

```
index.html                     página do cardápio
cardapio.json                  353 itens em 45 categorias (gerado a partir do dguests)
fotos/cais/*.webp              fotos dos itens
models/cais/*.glb              108 modelos 3D em escala 1:1 (um por tipo de item)
dados/dguests_*.json           cópia dos dados do cardápio no dguests
tools/montar_cardapio_cais.py  monta cardapio.json e escolhe o modelo 3D de cada item
tools/modelos_cais.py          gera os modelos 3D
```

**Bebidas** usam as medidas reais (lata 350 ml = 12,2 cm, long neck 330 ml, garrafa 600 ml, dose 50 ml, garrafas de vinho, etc.).
**Pratos** são ilustrativos, no tamanho do prato, tábua, cestinha ou cumbuca em que são servidos. Para ter o prato real em 3D, escaneie com Polycam/RealityScan, exporte em GLB e troque o arquivo em `models/cais/`.

## Atualizar o cardápio

1. Baixe de novo os dados do dguests para `dados/dguests_caisbarerestaurante.json`.
2. Rode:

```bash
python3 tools/montar_cardapio_cais.py dados/dguests_caisbarerestaurante.json cardapio.json
```

3. O script lista os modelos usados. Gere algum que esteja faltando:

```bash
python3 tools/modelos_cais.py models/cais NOME-DO-MODELO
```

4. Fotos novas vão em `fotos/cais/` com o nome `produto_<id>.webp`.
