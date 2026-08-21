"""
Motor exhaustivo y ultra-preciso de reclasificación de productos del catálogo.
Analiza nombre y marca de cada producto para asignarlo a la categoría correcta
de las 17 disponibles, corrigiendo productos mal clasificados o en 'otros'.

Uso:
    cd backend
    source venv/bin/activate
    # Modo simulación:
    python scripts/reclassify_all_products.py --dry-run

    # Modo ejecución real:
    python scripts/reclassify_all_products.py
"""
import sys
import os
import re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.product import Product, ProductCategory


# Reglas de clasificación con estricta jerarquía de prioridad
CATEGORY_RULES = [
    # 1. MASCOTAS (Prioridad máxima para evitar que 'carne' o 'pollo' en alimento para perro clasifique como carnes)
    (
        ProductCategory.MASCOTAS,
        [
            r"\b(perro|perros|perrito|perritos|canino|caninos)\b",
            r"\b(gato|gatos|gatito|gatitos|felino|felinos)\b",
            r"\b(mascota|mascotas|pet|pets)\b",
            r"\b(pedigree|dog chow|cat chow|whiskas|felix|pro plan|eukanuba|royal canin|gati|sabrositos|dogui|catchow|dogchow)\b",
            r"\b(piedras sanitarias|piedras gato|litera gato|dentastix|snack perro|snack gato|hueso perro|huesito perro)\b",
        ],
    ),

    # 2. BEBÉS Y MATERNIDAD
    (
        ProductCategory.BEBES,
        [
            r"\b(pañal|pañales|panal|panales|huggies|pampers|babysec|estrella baby)\b",
            r"\b(toallitas humedas|toallita humeda|toallitas para bebe|oleo calcareo|óleo calcáreo)\b",
            r"\b(chupete|chupetes|mamadera|mamaderas|mordillo|mordillos|babero|baberos)\b",
            r"\b(leche maternizada|leche de formula|leche formula|enfagrow|nutrilon|vital 1|vital 2|vital 3|vital 4|sancor bebe|nan 1|nan 2|nan 3)\b",
            r"\b(shampoo bebe|shampoo baby|colonia bebe|colonia baby|jabon bebe)\b",
        ],
    ),

    # 3. ELECTRO Y TECNOLOGÍA
    (
        ProductCategory.ELECTRO_TECNOLOGIA,
        [
            r"\b(pava electrica|pava eléctrica|cafetera electrica|cafetera expreso|licuadora|tostadora|sandwichera|batidora|procesadora)\b",
            r"\b(microondas|horno electrico|horno eléctrico|freidora de aire|air fryer|anafe|extractor)\b",
            r"\b(planchita de pelo|secador de pelo|afeitadora electrica|cortadora de pelo|cortapelo)\b",
            r"\b(televisor|smart tv|auriculares|cable usb|cargador|parlante bluetooth|pilas|pila aa|pila aaa|bateria)\b",
            r"\b(ventilador|caloventor|estufa electrica|aire acondicionado|termotanque)\b",
        ],
    ),

    # 4. FARMACIA Y SALUD
    (
        ProductCategory.FARMACIA_SALUD,
        [
            r"\b(alcohol etilico|alcohol etílico|alcohol medicinal|alcohol en gel|agua oxigenada medicinal)\b",
            r"\b(algodon hidrofilo|algodón hidrófilo|algodon zig zag|gasas|gasa esteril|gasas esteriles)\b",
            r"\b(curitas|apositos|apósitos|venda|vendas|preservativos|preservativo|prime|tulipan)\b",
            r"\b(ibuprofeno|paracetamol|aspirina|tafirol|actron|novalgina|bayaspirina|dorflex|buscapina|migral|alikal|benadryl)\b",
            r"\b(test de embarazo|evatest|termometro|termómetro|barbijo|barbijos)\b",
        ],
    ),

    # 5. HOGAR Y BAZAR
    (
        ProductCategory.HOGAR_BAZAR,
        [
            r"\b(bolsa de residuo|bolsas de residuo|bolsa residuos|bolsas residuos|bolsa basura|asurin)\b",
            r"\b(papel aluminio|film adherente|film de cocina|papel manteca|moldes de aluminio)\b",
            r"\b(vasos descartables|platos descartables|cubiertos descartables|servilletas de papel|servilleta papel)\b",
            r"\b(esponja mortimer|virulana|fibra esponja|rejilla cocina|trapo de piso|trapo rejilla|guantes de latex|guantes latex|guantes de goma)\b",
            r"\b(broches para ropa|perchas para ropa|fuenton|balde|mopa|escurridor|pala y escoba|escobillon|escobillón)\b",
            r"\b(tupper|recipiente hermetico|termo lumilagro|botella termica|mate de acero|bombilla mate|fuente de vidrio|sarten|sartén|cacerola|olla)\b",
            r"\b(vela aromatizada|velas noche|fosforos|fósforos fragata|tres patitos|encendedor bic|insecticida raid|insecticida fuyi|espirales fuyi|off repelente|repelente off)\b",
        ],
    ),

    # 6. CONGELADOS (Antes de carnes/panadería para atrapar hamburguesas, nuggets, papas fritas congeladas)
    (
        ProductCategory.CONGELADOS,
        [
            r"\b(hamburguesa|hamburguesas|paty|patys|swift hamburguesa|barfy|goodmark)\b",
            r"\b(nugget|nuggets|medallon de pollo|medallones de pollo|medallon de merluza|medallones de merluza|bocaditos de pollo|patitas de pollo|formitas de pollo)\b",
            r"\b(papas congeladas|papas fritas congeladas|mccain|papas noisette|bastones de muzzarella)\b",
            r"\b(helado|helados|pote de helado|bombón helado|palito helado|grido|frigor)\b",
            r"\b(espinaca congelada|choclo congelado|arvejas congeladas|mix de verduras congeladas|vegetales congelados)\b",
            r"\b(pizza congelada|empanadas congeladas|milanesas de soja congeladas)\b",
        ],
    ),

    # 7. SNACKS Y GOLOSINAS (Antes de frutas/verduras para que 'papas lays' o 'chocolates con frutilla' no sean frutas)
    (
        ProductCategory.SNACKS,
        [
            r"\b(galletitas|galletita|galletas|masitas|oreo|pepas|sonrisas|chocolinas|traviata|criollitas|club social|rumba|amor|melba|opera|merengadas|don satur|9 de oro|pitusas|maná|mana|frutigram|boca de dama|coquitas)\b",
            r"\b(chocolate|chocolates|bombones|alfajor|alfajores|guaymallen|havanna|jorgito|aguila|milka|cadbury|block|cofler|kitkat|kinder|ferrero rocher|tita|rhodesia|bon o bon|marroc)\b",
            r"\b(papas fritas|papas lays|lay s|pringles|chitos|cheetos|doritos|3d|palitos salados|mani salado|maní salado|conos de maiz|snack)\b",
            r"\b(caramelos|caramelo|chupetin|chupetines|gomitas|mogul|mentitas|halls|beldent|topline|chicle|pastillas drf|sugus|flynn paff)\b",
        ],
    ),

    # 8. HIGIENE PERSONAL (Antes de bebidas/frutas para que shampoo de manzana o jabon de coco no se desvíen)
    (
        ProductCategory.HIGIENE_PERSONAL,
        [
            r"\b(shampoo|champu|acondicionador|enjuague capilar|pantene|head & shoulders|head and shoulders|sedal|dove|elvive|tresemme|suave shampoo|plusbelle|herbal essences)\b",
            r"\b(jabon de tocador|jabon en barra tocador|jabon liquido manos|lux|rexona jabon|palmolive|espidol|nivea jabon)\b",
            r"\b(desodorante|antitranspirante|rexona|axe|dove desodorante|nivea desodorante|old spice|polyana)\b",
            r"\b(pasta dental|pasta de dientes|dentifrico|dentífrico|colgate|oral-b|oral b|sensodyne|aquafresh|enjuague bucal|listerine|hilo dental|cepillo de dientes|cepillo dental)\b",
            r"\b(papel higienico|papel higiénico|higienol|elegante|campanita|elite papel higienico)\b",
            r"\b(toallas femeninas|protectores diarios|tampones|siempre libre|nosotras|kotex|carefree|ladysoft)\b",
            r"\b(espuma de afeitar|gel de afeitar|maquinita de afeitar|hojas de afeitar|gillette|prestobarba|venus|after shave)\b",
            r"\b(crema corporal|crema de manos|crema facial|nivea|dermaglos|hinds|st ives|protector solar|bloqueador solar|dermaglos solar|rayito de sol|bagovit|bagóvit)\b",
        ],
    ),

    # 9. LIMPIEZA
    (
        ProductCategory.LIMPIEZA,
        [
            r"\b(detergente|detergentes|magistral|ala detergente|cif detergente)\b",
            r"\b(lavandina|lavandinas|ayudin|ayudín|clorox|lavandina en gel)\b",
            r"\b(suavizante para ropa|suavizante ropa|vivere|comfort|downy)\b",
            r"\b(jabon para ropa|jabon liquido ropa|jabon en polvo|ala para ropa|ariel|skip|drive|zorro jabon|skip liquido)\b",
            r"\b(limpiador de piso|limpiador liquido|poett|procacen|cif crema|cif baño|cif cocina|desengrasante|desinfectante lysoform|lysoform|espumer)\b",
            r"\b(desodorante de ambiente|glade|aire pur|pastillas inodoro|canasta inodoro|harpic|pato purific)\b",
            r"\b(lustramuebles|blem|ceras para piso|autobrillo|destapa cañerias)\b",
        ],
    ),

    # 10. BEBIDAS (Antes de frutas para atrapar jugos de naranja, aguas saborizadas, vinos)
    (
        ProductCategory.BEBIDAS,
        [
            r"\b(gaseosa|gaseosas|coca cola|coca-cola|pepsi|sprite|fanta|7up|seven up|manaos|secco|paso de los toros|schweppes|aquarius|levite|levité|placer)\b",
            r"\b(agua mineral|agua sin gas|agua con gas|agua saborizada|villavicencio|villa del sur|glaciar|kin|eco de los andes|bon aqua|soda en sifon|sifón)\b",
            r"\b(jugo de|jugo exprimido|jugo listo|jugo concentrado|cepita|baggio|citric|tang|clight|ser jugo|ades|ades soja)\b",
            r"\b(cerveza|cervezas|quilmes|brahma|stella artois|heineken|corona|andes|imperial|patagonia|schneider|budweiser|isenbeck|amstel)\b",
            r"\b(vino|vinos|malbec|cabernet|torrontes|torrontés|chardonnay|syrah|champagne|espumante|chandon|federico de alvear|valderrobles|colon|san felipe|termidor|uvita)\b",
            r"\b(fernet|branca|aperol|campari|gancia|vodka|smirnoff|absolut|gin|bombay|whisky|johnnie walker|ron|havana|licor)\b",
        ],
    ),

    # 11. LÁCTEOS
    (
        ProductCategory.LACTEOS,
        [
            r"\b(leche entera|leche descremada|leche parcialmente descremada|leche uat|leche fluida|leche sachet|leche en polvo|la serenisima|la serenísima|sancor|ilolay|tregar|veronica|las tres niñas)\b",
            r"\b(queso|quesos|mozzarella|muzzarella|cremoso|cuartirolo|port salut|reggianito|sardo|parmesano|provolone|gouda|fontina|brie|camembert|roquefort|queso azul|queso rallado|queso crema|casancrem|finlandia|tholem|cremon)\b",
            r"\b(yogur|yogures|yogurt|yoghurt|yogur bebible|yogur firme|yogur con cereales|yogur descremado|yogurisimo|yogurísimo|ser yogur|actimel|dahi|chimy)\b",
            r"\b(manteca|margarina|crema de leche|crema para batir|dulce de leche|dulcedeleche|ricota|ricotta)\b",
        ],
    ),

    # 12. DESAYUNO
    (
        ProductCategory.DESAYUNO,
        [
            r"\b(cafe molido|cafe en grano|cafe instantaneo|café instantáneo|café|cafe torrado|nescafe|nescafé|la virginia|dolca|cabrales|arlistan|sensaciones)\b",
            r"\b(saquitos de te|te en saquitos|te verde|te negro|taragui te|taragüi|green hills|twinings|te de boldo|te de manzanilla)\b",
            r"\b(yerba|yerba mate|playadito|taragui|rosamonte|cbse|cbsé|amanda|marolio yerba|union|unión|la merced|mañanita|cachamate|romance|chamigo)\b",
            r"\b(mate cocido|matecocido|cacao en polvo|cacao nesquik|nesquik|chocolino|toddy chocolatada|cerealitas|avena instantanea|avena tradicional|quaker avena)\b",
            r"\b(mermelada|mermeladas|jalea de membrillo|dulce de batata|dulce de membrillo|arcor mermelada|la campagnola mermelada|emeth)\b",
            r"\b(cereales para desayuno|copos de maiz|copos de maíz|zucaritas|froot loops|almohaditas de avena|granola con almendras)\b",
        ],
    ),

    # 13. PANADERÍA
    (
        ProductCategory.PANADERIA,
        [
            r"\b(pan lactal|pan de molde|pan blanco fargo|pan salvado|pan integral bimbo|pan para panchos|pan para hamburguesas|pan rallado|rebozador|fargo|bimbo|lactal|sacaan)\b",
            r"\b(tapa de empanada|tapas de empanada|tapa empanadas|tapas empanadas|tapa tarta|tapas tarta|tapa pascualina|pascualina hojaldre|la salteña|mendia|villa d agri|buona pasta)\b",
            r"\b(medialunas de manteca|medialunas de grasa|facturas surtidas|bizcochitos de grasa|pan frances|pan francés|flauta de pan|pan miñon|cremona hojaldre|pan dulce con frutas|budin marmolado|budin vainilla)\b",
        ],
    ),

    # 14. CARNES
    (
        ProductCategory.CARNES,
        [
            r"\b(asado de tira|vacio vacuno|vacío vacuno|matambre vacuno|entraña vacuna|bife de chorizo|bife de lomo|bife angosto|tira de asado|tapa de asado|nalga vacuna|peceto|bola de lomo|cuadril|colita de cuadril|roast beef|palomita vacuna|paleta vacuna|tortuguita|falda vacuna|osobuco)\b",
            r"\b(carne picada|carne molida|carne vacuna fresca|carne de cerdo fresca|carne de novillo|carne de ternera)\b",
            r"\b(pollo fresco|pechuga de pollo fresca|pata y muslo fresca|alitas de pollo|pollo entero fresco|suprema de pollo fresca|menudos de pollo)\b",
            r"\b(pechito de cerdo|bondiola fresca|carre de cerdo fresco|carré de cerdo|costillita de cerdo|solomillo de cerdo)\b",
            r"\b(milanesa de carne fresca|milanesa de pollo fresca|milanesa de ternera|milanesa casera)\b",
            r"\b(filet de merluza fresco|salmon rosado fresco|salmón fresco|atun fresco|langostinos frescos|calamar entero|rabas frescas)\b",
            r"\b(chorizo parrillero|chorizos parrilleros|morcilla criolla|morcillas|achuras|chinchulin fresco|molleja vacuna)\b",
        ],
    ),

    # 15. FRUTAS Y VERDURAS (Términos específicos de verdulería fresca)
    (
        ProductCategory.FRUTAS_VERDURAS,
        [
            r"\b(banana cavendish|banana ecuador|manzana roja|manzana verde|manzana deliciosa|naranja de ombligo|naranja para jugo|mandarina criolla|limon seleccionado|limón seleccionado|pera williams|frutilla seleccionada|durazno amarillo|uva red globe|sandia entera|sandía entera|melon escrito|kiwi seleccionado|palta hass|pomelo rosado)\b",
            r"\b(papa negra lavada|papa blanca lavada|cebolla blanca|cebolla morada|cebolla de verdeo fresca|tomate redondo seleccionado|tomate perita seleccionado|lechuga mantecosa|lechuga capuchina|lechuga criolla|zanahoria seleccionada|zapallo anco|calabaza seleccionada|morron rojo|morron verde|acelga fresca|espinaca fresca|rucula fresca|rúcula fresca|apio fresco|puerro fresco|remolacha con hojas|berenjena negra|zucchini fresco|pepino fresco|choclo fresco|batata seleccionada|ajo en cabeza|jengibre fresco|albahaca fresca|perejil fresco)\b",
        ],
    ),

    # 16. ALIMENTOS (Básicos, almacén, pastas secas, arroces, aceites, condimentos, salsas)
    (
        ProductCategory.ALIMENTOS,
        [
            r"\b(arroz blanco|arroz largo fino|arroz parboil|arroz integral|gallo oro|dos hermanos arroz|maximo arroz)\b",
            r"\b(fideos secos|fideo secos|tallarines matarazzo|tirabuzon matarazzo|mostachol|guisero|spaghetti lucchetti|matarazzo|lucchetti fideos|marolio fideos|don vicente)\b",
            r"\b(harina 000|harina 0000|harina leudante pureza|blancaflor|harina cañuelas|harina morixe)\b",
            r"\b(azucar comun|azúcar ledesma|azucar chango|edulcorante hileret|edulcorante sucaryl|stevia liquida)\b",
            r"\b(aceite de girasol|aceite de maiz|aceite mezcla|aceite de oliva extra virgen|cocinero aceite|natura aceite|cañuelas aceite|marolio aceite|oliovita)\b",
            r"\b(mayonesa natura|mayonesa hellmanns|mostaza savora|ketchup hellmanns|salsa golf|chimichurri alicante)\b",
            r"\b(sal fina dos anclas|sal gruesa celusal|sal parrillera|vinagre de alcohol|vinagre de manzana|aceto balsamico|oregano alicante|pimenton dulce|comino molido|caldo knorr|caldos knorr)\b",
            r"\b(pure de tomate|puré de tomate|tomate triturado marolio|tomate pelado|salsa pomarola|arcor salsa tomate|la campagnola salsa)\b",
            r"\b(lata de arvejas|lata de choclo|lata de lentejas|garbanzos en lata|porotos al natural|lata de atun|atun en aceite|atun al natural|gomes da costa)\b",
            r"\b(polenta presto pronta|pure de papas knorr|sopa knorr|gelatina royal|polvo para flan|exquisita bizcochuelo)\b",
        ],
    ),
]


def classify_text(text: str) -> ProductCategory | None:
    if not text:
        return None
    
    clean_text = text.lower()
    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                return category
    return None


def run_reclassification(dry_run: bool = False):
    session = SessionLocal()
    try:
        total_products = session.query(Product).count()
        print(f"🔍 Evaluando {total_products} productos en el catálogo...")
        if dry_run:
            print("⚠️ MODO SIMULACIÓN (--dry-run): No se modificarán registros en la BD.\n")
        else:
            print("🚀 MODO EJECUCIÓN REAL: Se actualizarán las categorías en la BD.\n")

        all_products = session.query(Product).all()

        changes_count = 0
        unchanged_count = 0
        from_to_matrix = defaultdict(lambda: defaultdict(int))
        new_category_counts = defaultdict(int)

        for prod in all_products:
            searchable_text = f"{prod.name} {prod.normalized_name or ''} {prod.brand or ''}"
            suggested_cat = classify_text(searchable_text)

            current_cat = prod.category

            if suggested_cat is not None and suggested_cat != current_cat:
                changes_count += 1
                from_to_matrix[current_cat.value][suggested_cat.value] += 1
                new_category_counts[suggested_cat.value] += 1
                if not dry_run:
                    prod.category = suggested_cat
            else:
                unchanged_count += 1
                new_category_counts[current_cat.value] += 1

        if not dry_run:
            session.commit()

        print(f"📊 RESULTADOS DE LA RECLASIFICACIÓN:")
        print(f"   • Productos reclasificados a una categoría más precisa: {changes_count}")
        print(f"   • Productos que mantuvieron su categoría correcta     : {unchanged_count}")
        print(f"   • Total evaluado                                      : {total_products}\n")

        print("📈 DETALLE DE MOVIMIENTOS:")
        for orig_cat, targets in sorted(from_to_matrix.items()):
            for target_cat, cnt in sorted(targets.items(), key=lambda x: -x[1]):
                print(f"   [{orig_cat}] ➔ [{target_cat}]: {cnt} productos")

        print("\n🏆 DISTRIBUCIÓN FINAL POR CATEGORÍA:")
        for cat_name, cnt in sorted(new_category_counts.items(), key=lambda x: -x[1]):
            print(f"   • {cat_name.ljust(20)}: {cnt} productos")

    except Exception as e:
        session.rollback()
        print(f"❌ Error durante la reclasificación: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    dry_run_mode = "--dry-run" in sys.argv
    run_reclassification(dry_run=dry_run_mode)
