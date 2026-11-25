# Cardápio em Realidade Aumentada

Cardápio web em que cada prato aparece em 3D e pode ser colocado **em tamanho real** na mesa pela câmera do celular. Não precisa instalar app.

| Aparelho | Como o AR abre |
|---|---|
| Android com ARCore (Chrome) | WebXR ou Google Scene Viewer |
| iPhone / iPad (Safari) | AR Quick Look (o USDZ é gerado automaticamente a partir do GLB) |
| Computador | Só o visualizador 3D (girar e dar zoom) |

O que garante o tamanho real: os modelos estão em metros, e a página usa `ar-scale="fixed"`, que impede o cliente de redimensionar o prato no AR. `ar-placement="floor"` posiciona o prato em superfícies horizontais, como a mesa.

## Estrutura

```
site/
  index.html            página pronta para publicar
  models/*.glb          um modelo 3D por prato (escala 1:1, em metros)
menu.html               a mesma página, sem o <html>/<head> (versão usada no preview)
tools/gerar_modelos.py  gera os GLB de exemplo de forma procedural (Python + numpy)
```

## Publicar

A câmera/AR só funciona em **HTTPS**. Suba esta pasta em qualquer hospedagem estática, por exemplo GitHub Pages, Netlify, Vercel ou Cloudflare Pages.

Para testar no computador:

```bash
python3 -m http.server 8000
```

## QR code nas mesas

Cada prato tem um link direto pelo `#`, por exemplo `https://seusite.com/#pizza-margherita`. Imprima um QR code com o endereço do cardápio em cada mesa.

## Trocar pelos pratos reais

Os modelos incluídos são ilustrações procedurais, feitas para demonstrar a escala. Para o cardápio de verdade:

1. **Fotogrametria do prato real**: fotografe o prato de todos os ângulos (cerca de 40 a 80 fotos) e gere o modelo com **Polycam**, **Luma AI**, **RealityScan** ou **Apple Object Capture** (Reality Composer no iPhone). Exporte em **GLB**.
2. **Confira a escala**: o modelo precisa estar em metros (uma pizza de 35 cm tem 0.35 de largura). Dá para ajustar no Blender (`Scale`, depois `Apply > Scale`).
3. **Deixe leve**: tente ficar abaixo de 3 a 5 MB por prato (por exemplo com `npx @gltf-transform/cli optimize prato.glb prato-otim.glb --texture-compress webp`).
4. Coloque o arquivo em `site/models/` e adicione o prato na lista `PRATOS` do `index.html`:

```js
{ id: 'nome_do_arquivo', cat: 'Pratos principais', nome: 'Nome', preco: 59, desc: '...', medida: 'prato Ø 28 cm' },
```

Se quiser um USDZ feito à mão para o iPhone (melhor qualidade de textura), coloque `ios-src="models/prato.usdz"` no `<model-viewer>`.

## Regenerar os modelos de exemplo

```bash
python3 tools/gerar_modelos.py models            # todos
python3 tools/gerar_modelos.py models costelao_12h  # só um prato
```
