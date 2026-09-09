# Fusiones sin backup JSON — corrida interrumpida del 2026-09-08

`merge_coto_strict_matches.py --apply` se lanzó en segundo plano para aplicar
las 46 fusiones encontradas tras arreglar el prefiltro (ver commit
`a8bd8f0`). El proceso quedó corriendo cuando la sesión de Claude Code se
reinició — el script hace `session.commit()` por cada fusión dentro del
loop, pero solo escribe el JSON de backup (`coto_merge_backup_*.json`) al
final, después de procesar las 46. El reinicio mató el proceso a mitad de
camino: **21 de las 46 fusiones ya habían quedado commiteadas en
producción cuando el proceso murió, sin que se llegara a escribir el
backup.**

No hay forma de reconstruir el backup completo (id/normalized_name/brand/
category/unit/quantity/description/image_url/barcode del producto
borrado, ids de price_history, id de alias) porque esas filas ya no
existen — Neon no está conectado en esta sesión (sin CLI ni API key), así
que no hay acceso a point-in-time recovery / branching desde acá. Si
alguna de estas 21 fusiones necesitara deshacerse, la única vía es el
point-in-time restore del dashboard de Neon (retención según el plan del
proyecto) creando un branch desde antes del 2026-09-08 ~23:37 (hora del
primer commit de esta corrida).

Se verificó (post-hoc, 2026-09-09) que los 21 productos canónicos destino
existen y tienen el nombre esperado — es decir, las 21 fusiones
efectivamente se aplicaron tal como las revisó el dry-run (0 ambiguos),
no hay indicios de corrupción. Igual queda documentado acá por
transparencia, ya que rompe el patrón de "todo merge en producción tiene
su JSON de backup" que se venía siguiendo el resto de la sesión.

## Las 21 fusiones aplicadas sin backup

| Producto aislado de Coto (borrado) | Producto canónico (id) |
|---|---|
| Aceite Oliva Suave Natura 500ml | Aceite De Oliva Suave Natura 500 Ml. (`ccbb907c-c93f-4aa6-922a-cb6607d3fee8`) |
| Chocolate Dubai COFLER 43g | Chocolate Cofler Dubai 43gr (`de71c2c4-9642-4bb8-92bd-cadb5b780081`) |
| Fideos Tirabuzón LUCCHETTI 500g | Fideos Lucchetti Tirabuzón 500 G (`19605faa-a9cc-443e-bb1e-abe983673021`) |
| Gaseosa Coca-Cola Sin Azúcar 220 Ml | Gaseosa cola Coca Cola sin azúcar 220 ml (`df35fbf6-560e-4ac9-8f40-be12643ef416`) |
| Detergente Bioactive Limon CIF 450ml | Detergente Cif Bioactive Limón 450ml (`0981fd16-4850-4c1f-a382-2be8d2aae871`) |
| Gaseosa Cola Manaos 2.25l | Gaseosa Manaos Cola 2.25 L (`67a0310c-5eed-4f9c-920c-69b9c8d52ac6`) |
| Shampoo Reconstrucción Completa DOVE 750 Ml | Shampoo Dove Reconstruccion Completa 750ml (`d9fc1e53-4181-47fb-bfd4-95bed7d4ef10`) |
| Yogur Griego Sabor Natural Endulzado YOGURISIMO 300g | Yogur Sabor Natural Griego Endulzado 300 Grs Yogurisimo (`e6e9e3b6-9e37-4f8e-97a3-c4db344f9635`) |
| Manteca Extra Sal Tonadita 200g | Manteca Tonadita Extra Sal 200 G (`7a549a1e-1f9e-4898-b900-94546223f90e`) |
| Lavandina Original Ayudin 4l | Lavandina Ayudin Original 4l (`3695e680-af6e-4d9d-b5c5-d95cfc2a556e`) |
| Gaseosa Coca-Cola Zero 354 Ml | GASEOSA COCA COLA ZERO LATA 354 CC. (`cae3e1a0-f88e-467b-9720-a286bbd85c39`) |
| Shampoo Reconstrucción Completa DOVE 400 Ml | Shampoo Dove Reconstrucción Completa 400 Ml (`4ca543ab-60d7-42fd-ae98-87c67fa28d14`) |
| Queso Cremón Cremoso La Serenísima X Kg | Queso cremoso Cremón x kg (`11243844-f1dc-4cc2-894f-705128c0ebf0`) |
| Gaseosa Coca-Cola Sabor Original 354 Ml | Gaseosa cola Coca Cola sabor original en lata 354 ml (`c7337446-8a57-4d92-b135-299e6406aadc`) |
| Chocolate Blanco ARCOR 25g | Chocolate Arcor Blanco 25 Gr (`6d268a11-b43d-4215-844e-9b5a334db3bd`) |
| NESTLÉ® Chocolate con Almendras x25g | Chocolate con Almendras Nestle x 25 Gr. (`ec041ebb-b1bf-48f5-a85c-2bbfd9e2dc08`) |
| Caramelos Rellenos De Miel Arcor 80g | Caramelos Arcor rellenos de miel 80 grs (`f85069e5-eb9d-44f1-8653-88fdca7730ce`) |
| Gaseosa Pomelo Suave Cunnington 2,25l | Gaseosa Cunnington Pomelo Suave 2.25lt (`4d6ca64b-8b87-412e-9c49-6c19a4805653`) |
| Shampoo ELVIVE Rt5 Keratin 400ml | Shampoo Rt5 Keratin 400 Ml Elvive (`e10e3807-5ee0-4c4b-8531-b8152cf2d327`) |
| Papas Fritas Clásicas Lays 230g | Papas fritas Lays clásicas 230 g. (`88d5adff-7f63-4e8e-9da7-44f02061e06e`) |
| Vinagre De Vino Favinco 500 Ml | VINAGRE FAVINCO DE VINO 500 ML. (`e4a0e077-d34e-443d-9de3-0fbadb88fa0e`) |

## Fix aplicado al script para que esto no vuelva a pasar

Ver commit siguiente: se movió la escritura del backup a modo incremental
(un append por fusión, no al final del loop) en `merge_coto_strict_matches.py`.
