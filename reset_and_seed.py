"""
reset_and_seed.py
-----------------
1. Limpia TODAS las tablas transaccionales via TRUNCATE ... CASCADE.
2. Preserva: empresas, sucursales, roles, usuarios.
3. Siembra el catalogo completo de insumos y productos terminados de una pizzeria.
4. Configura stocks minimos/maximos por sucursal.
5. Registra los tipos de movimiento y documento de catalogo.

Uso:
    python reset_and_seed.py
"""

import asyncio
from sqlalchemy import text
from app.core.database import engine   # AsyncEngine

# --- SQL TRUNCATE ------------------------------------------------------------
TRUNCATE_SQL = """
TRUNCATE TABLE
    bitacora_acciones,
    ordenes_produccion,
    receta_ingredientes,
    recetas,
    movimientos_inventario,
    saldos_inventario,
    lotes,
    despacho_detalles,
    despachos,
    requisicion_detalles,
    requisiciones,
    productos_sucursal,
    productos,
    categorias_producto,
    unidades_medida,
    tipos_movimiento,
    tipos_documento_salida
RESTART IDENTITY CASCADE;
"""

# --- CATALOGO BASE -----------------------------------------------------------

CATEGORIAS = [
    ("Harinas y Masas",        "Harinas, semolinas y mezclas para masas"),
    ("Lacteos y Quesos",       "Quesos, mantequillas y productos lacteos"),
    ("Embutidos y Carnes",     "Pepperoni, jamon, salchicha y carnes frias"),
    ("Salsas y Condimentos",   "Salsas de tomate, especias, aceites y aderezos"),
    ("Vegetales y Frescos",    "Pimientos, cebolla, champinones, aceitunas y vegetales"),
    ("Bebidas",                "Refrescos, aguas y bebidas en botella/lata"),
    ("Empaques",               "Cajas, bolsas y materiales de empaque"),
    ("Productos Terminados",   "Pizzas listas para despacho o venta"),
    ("Limpieza",               "Articulos de limpieza e higiene"),
]

# (nombre, abreviatura)
UNIDADES = [
    ("Kilogramo",   "kg"),
    ("Gramo",       "g"),
    ("Litro",       "L"),
    ("Mililitro",   "mL"),
    ("Pieza",       "pza"),
    ("Caja",        "cja"),
    ("Bolsa",       "bls"),
    ("Lata",        "lta"),
    ("Rollo",       "rol"),
    ("Paquete",     "paq"),
]

# (codigo, nombre, direccion: E/S, afecta_costo)
TIPOS_MOVIMIENTO = [
    ("ENTRADA_COMPRA",   "Entrada por Compra",               "E", True),
    ("ENTRADA_PROD",     "Entrada por Produccion",           "E", True),
    ("ENTRADA_DEVOL",    "Entrada por Devolucion",           "E", True),
    ("SALIDA_DESPACHO",  "Salida por Despacho",              "S", True),
    ("SALIDA_MERMA",     "Salida por Merma / Desperdicio",   "S", True),
    ("SALIDA_PROD",      "Salida por Consumo en Produccion", "S", True),
    ("AJUSTE_POSITIVO",  "Ajuste Positivo de Inventario",   "E", False),
    ("AJUSTE_NEGATIVO",  "Ajuste Negativo de Inventario",   "S", False),
    ("TRASLADO",         "Traslado entre Sucursales",        "S", False),
]

# (codigo, nombre, descripcion)
TIPOS_DOC_SALIDA = [
    ("NOTA_TRASLADO", "Nota de Traslado",  "Documento interno de traslado entre sucursales"),
    ("FACTURA",       "Factura",           "Factura electronica CFDI"),
    ("NOTA_VENTA",    "Nota de Venta",     "Venta directa sin factura"),
]

# ---
# (codigo, nombre, cat_idx, um_abr, tipo, precio, desc, stock_min, stock_max, punto_reorden)
PRODUCTOS = [
    # HARINAS Y MASAS
    ("HRN-001", "Harina de Trigo Todo Uso 25 kg",       0, "kg",  "insumo",    12.50, "Harina de trigo para masa de pizza, bolsa 25 kg", 50, 200, 80),
    ("HRN-002", "Semolina Fina",                         0, "kg",  "insumo",    18.00, "Semolina de trigo duro para base crujiente", 20, 100, 35),
    ("HRN-003", "Harina Integral",                       0, "kg",  "insumo",    14.00, "Harina integral para masa artesanal", 15, 80, 25),
    ("HRN-004", "Levadura Instantanea",                  0, "pza", "insumo",     3.50, "Levadura seca activa, sobre 11 g", 30, 150, 50),
    ("HRN-005", "Aceite de Oliva Extra Virgen 4 L",      3, "L",   "insumo",    95.00, "Aceite de oliva para masa y terminado", 8, 40, 12),

    # LACTEOS Y QUESOS
    ("QSO-001", "Queso Mozzarella Bajo en Humedad 2 kg", 1, "kg",  "insumo",    85.00, "Queso mozzarella rallado, bloque 2 kg", 40, 160, 60),
    ("QSO-002", "Queso Manchego Rallado",                1, "kg",  "insumo",    70.00, "Queso manchego estilo mexicano rallado", 20, 80, 30),
    ("QSO-003", "Queso Gouda Rebanado",                  1, "kg",  "insumo",    90.00, "Queso gouda en rebanadas para pizza gourmet", 10, 50, 15),
    ("QSO-004", "Queso Parmesano Molido",                1, "kg",  "insumo",   110.00, "Parmesano importado molido fino para terminado", 8, 30, 12),
    ("QSO-005", "Crema Acida 1 L",                       1, "L",   "insumo",    28.00, "Crema acida para pizza blanca y dip", 10, 40, 15),

    # EMBUTIDOS Y CARNES
    ("EMB-001", "Pepperoni Natural Casing 1 kg",         2, "kg",  "insumo",    78.00, "Pepperoni estilo americano, rebanado, 1 kg", 30, 120, 45),
    ("EMB-002", "Jamon de Pierna Rebanado 1 kg",         2, "kg",  "insumo",    62.00, "Jamon cocido de pierna en rebanadas delgadas", 25, 100, 40),
    ("EMB-003", "Tocino Ahumado 1 kg",                   2, "kg",  "insumo",    88.00, "Tocino ahumado natural, tiras delgadas", 20, 80, 30),
    ("EMB-004", "Salchicha Italiana 1 kg",               2, "kg",  "insumo",    74.00, "Salchicha italiana picante y dulce mezclada", 15, 60, 25),
    ("EMB-005", "Pollo a la Parrilla Pre-Cocido 1 kg",   2, "kg",  "insumo",    56.00, "Pechuga de pollo marinada pre-cocida desmenuzada", 20, 80, 30),

    # SALSAS Y CONDIMENTOS
    ("SLS-001", "Salsa de Tomate Pizza 3 kg",            3, "kg",  "insumo",    35.00, "Salsa base para pizza, tomates San Marzano, balde 3 kg", 25, 100, 40),
    ("SLS-002", "Pasta de Tomate 850 g",                 3, "kg",  "insumo",    18.00, "Concentrado de tomate para reforzar la salsa", 15, 60, 25),
    ("SLS-003", "Ajo en Polvo",                          3, "kg",  "insumo",    22.00, "Ajo en polvo para masa y salsas", 5, 20, 8),
    ("SLS-004", "Oregano Seco Molido",                   3, "kg",  "insumo",    18.00, "Oregano mediterraneo para terminado de pizza", 5, 20, 8),
    ("SLS-005", "Salsa BBQ 1 L",                         3, "L",   "insumo",    42.00, "Salsa BBQ ahumada para pizza especial", 10, 40, 15),
    ("SLS-006", "Chile de Arbol Seco",                   3, "kg",  "insumo",    30.00, "Chile seco para aceite picante y salsas", 3, 15, 5),
    ("SLS-007", "Aceite Vegetal 4 L",                    3, "L",   "insumo",    55.00, "Aceite vegetal para engrasado de charolas", 10, 40, 15),

    # VEGETALES Y FRESCOS
    ("VEG-001", "Pimiento Rojo 1 kg",                    4, "kg",  "insumo",    28.00, "Pimiento morron rojo fresco en tiras", 10, 40, 15),
    ("VEG-002", "Pimiento Verde 1 kg",                   4, "kg",  "insumo",    22.00, "Pimiento morron verde fresco en tiras", 10, 40, 15),
    ("VEG-003", "Cebolla Blanca 1 kg",                   4, "kg",  "insumo",    15.00, "Cebolla blanca en julianas", 15, 60, 25),
    ("VEG-004", "Champinones Laminados 1 kg",            4, "kg",  "insumo",    40.00, "Champinones frescos laminados", 10, 40, 15),
    ("VEG-005", "Aceitunas Negras Rebanadas 400 g",      4, "pza", "insumo",    32.00, "Aceitunas negras en rodajas, lata 400 g", 8, 30, 12),
    ("VEG-006", "Jitomate Bola 1 kg",                    4, "kg",  "insumo",    18.00, "Jitomate fresco para decoracion y ensalada", 10, 40, 15),
    ("VEG-007", "Albahaca Fresca",                       4, "pza", "insumo",    12.00, "Manojo de albahaca fresca para pizza Margherita", 5, 20, 8),
    ("VEG-008", "Espinaca Baby 500 g",                   4, "kg",  "insumo",    22.00, "Espinaca tierna para pizza vegetariana", 5, 20, 8),
    ("VEG-009", "Jalapeno en Escabeche 400 g",           4, "pza", "insumo",    20.00, "Jalape nos en escabeche en rodajas", 8, 30, 12),
    ("VEG-010", "Pina en Trozos 820 g",                  4, "lta", "insumo",    18.00, "Pina en almibar natural, lata 820 g", 8, 30, 12),

    # BEBIDAS
    ("BEB-001", "Coca-Cola 355 mL Lata",                 5, "pza", "preparado", 14.00, "Refresco Coca-Cola lata 355 mL", 24, 144, 48),
    ("BEB-002", "Pepsi 355 mL Lata",                     5, "pza", "preparado", 13.00, "Refresco Pepsi lata 355 mL", 24, 144, 48),
    ("BEB-003", "Agua Natural 600 mL",                   5, "pza", "preparado",  8.00, "Agua purificada botella 600 mL", 36, 216, 60),
    ("BEB-004", "Jugo de Naranja 1 L",                   5, "pza", "preparado", 22.00, "Jugo de naranja natural 100%% botella 1 L", 12, 60, 24),
    ("BEB-005", "Cerveza Carta Blanca 355 mL",           5, "pza", "preparado", 18.00, "Cerveza clara mexicana lata 355 mL", 24, 120, 48),

    # EMPAQUES
    ("EMP-001", "Caja Pizza Chica 8 pulgadas",           6, "pza", "empaque",    2.80, "Caja corrugada para pizza chica 8 pulgadas", 50, 300, 80),
    ("EMP-002", "Caja Pizza Mediana 10 pulgadas",        6, "pza", "empaque",    3.20, "Caja corrugada para pizza mediana 10 pulgadas", 50, 300, 80),
    ("EMP-003", "Caja Pizza Grande 12 pulgadas",         6, "pza", "empaque",    3.80, "Caja corrugada para pizza grande 12 pulgadas", 50, 300, 80),
    ("EMP-004", "Caja Pizza Familiar 14 pulgadas",       6, "pza", "empaque",    4.50, "Caja corrugada para pizza familiar 14 pulgadas", 30, 200, 60),
    ("EMP-005", "Bolsa Kraft Manija",                    6, "pza", "empaque",    1.20, "Bolsa de papel kraft para llevar", 100, 500, 150),
    ("EMP-006", "Servilletas Paquete 500",               6, "paq", "empaque",   28.00, "Servilletas de papel paquete 500 piezas", 10, 50, 15),

    # PRODUCTOS TERMINADOS
    ("PZZ-001", "Pizza Pepperoni Chica 8 pulgadas",      7, "pza", "preparado",  89.00, "Pizza pepperoni individual masa delgada 8 pulgadas", 0, 50, 5),
    ("PZZ-002", "Pizza Pepperoni Mediana 10 pulgadas",   7, "pza", "preparado", 129.00, "Pizza pepperoni mediana 10 pulgadas", 0, 50, 5),
    ("PZZ-003", "Pizza Pepperoni Grande 12 pulgadas",    7, "pza", "preparado", 169.00, "Pizza pepperoni grande 12 pulgadas", 0, 50, 5),
    ("PZZ-004", "Pizza Pepperoni Familiar 14 pulgadas",  7, "pza", "preparado", 219.00, "Pizza pepperoni familiar 14 pulgadas", 0, 50, 5),
    ("PZZ-005", "Pizza Margherita Grande",               7, "pza", "preparado", 155.00, "Pizza Margherita salsa tomate mozzarella albahaca fresca", 0, 50, 5),
    ("PZZ-006", "Pizza Hawaiana Grande",                 7, "pza", "preparado", 165.00, "Pizza jamon mas pina mas mozzarella", 0, 50, 5),
    ("PZZ-007", "Pizza 4 Quesos Grande",                 7, "pza", "preparado", 185.00, "Mozzarella manchego gouda y parmesano", 0, 50, 5),
    ("PZZ-008", "Pizza Vegetariana Grande",              7, "pza", "preparado", 175.00, "Pimientos champinones cebolla espinaca y aceitunas", 0, 50, 5),
    ("PZZ-009", "Pizza Mexicana Grande",                 7, "pza", "preparado", 180.00, "Chorizo jalapeno cebolla jitomate y mozzarella", 0, 50, 5),
    ("PZZ-010", "Pizza Suprema Familiar",                7, "pza", "preparado", 249.00, "Pepperoni tocino jamon pimientos cebolla champinones", 0, 50, 5),

    # LIMPIEZA
    ("LMP-001", "Desengrasante Industrial 4 L",          8, "pza", "limpieza",  45.00, "Desengrasante para hornos y superficies de cocina", 3, 15, 5),
    ("LMP-002", "Cloro Concentrado 4 L",                 8, "pza", "limpieza",  28.00, "Hipoclorito de sodio al 6%%", 3, 15, 5),
    ("LMP-003", "Jabon Liquido para Manos 1 L",          8, "pza", "limpieza",  22.00, "Jabon antibacterial para personal", 5, 20, 8),
    ("LMP-004", "Guantes de Latex Caja 100",             8, "cja", "limpieza",  65.00, "Guantes desechables talla M caja 100 piezas", 3, 15, 5),
    ("LMP-005", "Papel Absorbente Rollo",                8, "rol", "limpieza",   8.00, "Rollo de papel absorbente para limpieza de superficies", 6, 30, 10),
]


async def main():
    async with engine.begin() as conn:
        print("Limpiando tablas transaccionales...")
        await conn.execute(text(TRUNCATE_SQL))
        print("Tablas limpiadas.\n")

        # Unidades de medida
        print("Insertando unidades de medida...")
        unidad_map: dict[str, int] = {}
        for nombre, abr in UNIDADES:
            result = await conn.execute(
                text("INSERT INTO unidades_medida (nombre, abreviatura) VALUES (:n, :a) RETURNING id"),
                {"n": nombre, "a": abr}
            )
            unidad_map[abr] = result.scalar_one()
        print(f"  {len(UNIDADES)} unidades insertadas.")

        # Categorias
        print("Insertando categorias de producto...")
        cat_ids: list[int] = []
        for nombre, desc in CATEGORIAS:
            result = await conn.execute(
                text("INSERT INTO categorias_producto (nombre, descripcion) VALUES (:n, :d) RETURNING id"),
                {"n": nombre, "d": desc}
            )
            cat_ids.append(result.scalar_one())
        print(f"  {len(CATEGORIAS)} categorias insertadas.")

        # Tipos de movimiento
        print("Insertando tipos de movimiento...")
        for cod, nom, dir_, costo in TIPOS_MOVIMIENTO:
            await conn.execute(
                text("INSERT INTO tipos_movimiento (codigo, nombre, direccion, afecta_costo) VALUES (:c, :n, :d, :ac)"),
                {"c": cod, "n": nom, "d": dir_, "ac": costo}
            )
        print(f"  {len(TIPOS_MOVIMIENTO)} tipos de movimiento insertados.")

        # Tipos de documento de salida
        print("Insertando tipos de documento de salida...")
        for cod, nom, desc in TIPOS_DOC_SALIDA:
            await conn.execute(
                text("INSERT INTO tipos_documento_salida (codigo, nombre, descripcion) VALUES (:c, :n, :d)"),
                {"c": cod, "n": nom, "d": desc}
            )
        print(f"  {len(TIPOS_DOC_SALIDA)} tipos de documento insertados.")

        # Productos
        print("Insertando productos...")
        producto_ids: list[tuple] = []
        for row in PRODUCTOS:
            (cod, nom, cat_idx, um_abr, tipo, precio, desc, smin, smax, preorden) = row
            cat_id = cat_ids[cat_idx]
            um_id  = unidad_map[um_abr]
            result = await conn.execute(
                text("""
                    INSERT INTO productos
                        (codigo_interno, nombre, categoria_id, unidad_medida_id,
                         tipo_producto, precio_referencia, descripcion, activo)
                    VALUES (:cod, :nom, :cat, :um, :tipo, :precio, :desc, true)
                    RETURNING id
                """),
                {"cod": cod, "nom": nom, "cat": cat_id, "um": um_id,
                 "tipo": tipo, "precio": str(precio), "desc": desc}
            )
            pid = result.scalar_one()
            producto_ids.append((pid, smin, smax, preorden))
        print(f"  {len(PRODUCTOS)} productos insertados.")

        # ProductoSucursal
        print("Configurando stocks por sucursal...")
        sucursales = await conn.execute(text("SELECT id FROM sucursales WHERE activo = true"))
        suc_ids = [row[0] for row in sucursales.fetchall()]
        if not suc_ids:
            print("  ADVERTENCIA: No hay sucursales activas, omitiendo configuracion de stocks.")
        else:
            count = 0
            for pid, smin, smax, preorden in producto_ids:
                for sid in suc_ids:
                    await conn.execute(
                        text("""
                            INSERT INTO productos_sucursal
                                (producto_id, sucursal_id, stock_minimo, stock_maximo, punto_reorden, activo)
                            VALUES (:pid, :sid, :smin, :smax, :pr, true)
                        """),
                        {"pid": pid, "sid": sid,
                         "smin": str(smin), "smax": str(smax), "pr": str(preorden)}
                    )
                    count += 1
            print(f"  {count} configuraciones de stock insertadas.")

        print("\nSeed completado exitosamente!")
        print(f"\nResumen:")
        print(f"  {len(UNIDADES)} unidades de medida")
        print(f"  {len(CATEGORIAS)} categorias de producto")
        print(f"  {len(PRODUCTOS)} productos (insumos + terminados + empaques + bebidas + limpieza)")
        print(f"  {len(TIPOS_MOVIMIENTO)} tipos de movimiento")
        print(f"  {len(TIPOS_DOC_SALIDA)} tipos de documento de salida")
        if suc_ids:
            print(f"  {len(suc_ids) * len(producto_ids)} configs de stock por sucursal")
        print(f"\nDatos preservados: empresas, sucursales, roles, usuarios")


if __name__ == "__main__":
    asyncio.run(main())
