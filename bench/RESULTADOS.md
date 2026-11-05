# Resultados del benchmark (2026-11-05)

Escena: lámina v2 de la referencia (3 cerditos + lobo con pelaje, pasto por partículas), animada (dolly de cámara + cabeza del lobo + brazo de un cerdito).
Runner: GitHub Actions `ubuntu-24.04`, repo público, 4 vCPU, sin GPU (Mesa llvmpipe bajo xvfb).

## bench4 (24 cuadros, FAST=1, vertical 1080x1920 al 50% = 540x960)
| Variante | Blender | Motor | Construcción | Render | s/cuadro |
|---|---|---|---|---|---|
| eevee42_pelo | 4.2.23 LTS | BLENDER_EEVEE_NEXT | 16.3 s | 130.1 s | **5.42** |
| eevee40_pelo | 4.0.2 (apt) | BLENDER_EEVEE | 17.0 s | 236.8 s | 9.87 |
| eevee40_sin_pelo | 4.0.2 (apt) | BLENDER_EEVEE | 21.4 s | 251.3 s | 10.47 |
| cycles42_pelo | 4.2.23 LTS | CYCLES 16 spp + OIDN | 22.3 s | 559.6 s | 23.32 |

## bench (workflow simple, Blender 4.0.2)
| Run | Paso Bench | Estimado |
|---|---|---|
| #1 rápido 48 cuadros vertical | 644 s | ~12.6 s/cuadro |
| #2 completo 24 cuadros vertical | 2073 s | ~84 s/cuadro |
| #3 rápido 48 cuadros horizontal | 731 s | ~14.4 s/cuadro |

## Conclusiones
- Motor elegido: **Eevee Next (Blender LTS oficial, no el de apt)**. ~2x más rápido que Eevee 4.0, con pelaje y pasto visibles.
- El pelaje no es el cuello de botella (sin pelaje no fue más rápido).
- Calidad completa descartada (~84 s/cuadro). Cycles descartado.
- Eevee Next se ve más lavado (menos contraste, sombras más suaves): hay que reajustar luces y AgX para 4.2 en la biblioteca.
- En vertical se pierde el cerdito de la izquierda y se ve el borde del parche de pasto: el encuadre vertical se diseña aparte (1-2 personajes por plano).
- Pendiente: probar Blender 4.5 LTS (4.2 LTS ya salió de soporte) en el primer bench del director.

## Presupuesto con 5.4 s/cuadro, 24 fps, 20 jobs en paralelo
- Short 60 s: 1440 cuadros ≈ 2.2 h de runner ≈ 7 min de reloj.
- Largo 8 min: 11520 cuadros ≈ 17 h de runner ≈ 52 min de reloj.
