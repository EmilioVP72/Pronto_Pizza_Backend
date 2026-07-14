-- ============================================================
--  WMS PRONTO PIZZA — Datos de Prueba (Seed)
--  Script para popular catálogos y generar inventario inicial.
--  IMPORTANTE: Ejecutar DESPUÉS de Schema.sql y seed_admin.sql
-- ============================================================

DO $$
DECLARE
    v_empresa_id UUID;
    v_comisariato_id UUID;
    v_sucursal_norte_id UUID;
    v_sucursal_sur_id UUID;
    
    -- Variables para Productos
    v_prod_harina UUID;
    v_prod_queso UUID;
    v_prod_salsa UUID;
    v_prod_caja UUID;
    v_prod_masa UUID;

    -- Variables para Usuarios
    v_rol_almacenista INT;
    v_rol_encargado INT;
    
    -- Variables para Categorias
    v_cat_insumo INT;
    v_cat_preparado INT;
    v_cat_empaque INT;
    
    -- Variables para Unidades
    v_um_kg INT;
    v_um_lt INT;
    v_um_pza INT;

BEGIN
    -- 1. Obtener Empresa Matriz y Comisariato (ya creados en seed_admin.sql)
    SELECT id INTO v_empresa_id FROM empresas WHERE rfc = 'PPIZZA1234567' LIMIT 1;
    SELECT id INTO v_comisariato_id FROM sucursales WHERE codigo = 'MTZ' LIMIT 1;
    
    -- Si no existen, salimos para no causar errores (debe correrse seed_admin.sql primero)
    IF v_empresa_id IS NULL OR v_comisariato_id IS NULL THEN
        RAISE NOTICE 'No se encontró la empresa matriz o el comisariato. Ejecuta seed_admin.sql primero.';
        RETURN;
    END IF;

    -- 2. Obtener IDs de catálogos fijos
    SELECT id INTO v_cat_insumo FROM categorias_producto WHERE nombre = 'Insumo';
    SELECT id INTO v_cat_preparado FROM categorias_producto WHERE nombre = 'Preparado';
    SELECT id INTO v_cat_empaque FROM categorias_producto WHERE nombre = 'Empaque';
    
    SELECT id INTO v_um_kg FROM unidades_medida WHERE abreviatura = 'kg';
    SELECT id INTO v_um_lt FROM unidades_medida WHERE abreviatura = 'lt';
    SELECT id INTO v_um_pza FROM unidades_medida WHERE abreviatura = 'pza';
    
    SELECT id INTO v_rol_almacenista FROM roles WHERE nombre = 'almacenista';
    SELECT id INTO v_rol_encargado FROM roles WHERE nombre = 'encargado_sucursal';

    -- 3. Crear Nuevas Sucursales (Puntos de Venta)
    INSERT INTO sucursales (empresa_id, nombre, codigo, direccion, es_comisariato)
    VALUES 
        (v_empresa_id, 'Pronto Pizza Norte', 'NRT', 'Av. Norte 123', FALSE),
        (v_empresa_id, 'Pronto Pizza Sur', 'SUR', 'Blvd. Sur 456', FALSE)
    ON CONFLICT (codigo) DO NOTHING;
    
    SELECT id INTO v_sucursal_norte_id FROM sucursales WHERE codigo = 'NRT';
    SELECT id INTO v_sucursal_sur_id FROM sucursales WHERE codigo = 'SUR';

    -- 4. Crear Usuarios de Prueba para las sucursales y almacén
    INSERT INTO usuarios (sucursal_id, rol_id, nombre_completo, email, auth_user_id)
    VALUES 
        (v_comisariato_id, v_rol_almacenista, 'Pedro Almacenista', 'bodega@prontopizza.com', gen_random_uuid()),
        (v_sucursal_norte_id, v_rol_encargado, 'María Encargada Norte', 'norte@prontopizza.com', gen_random_uuid()),
        (v_sucursal_sur_id, v_rol_encargado, 'Jorge Encargado Sur', 'sur@prontopizza.com', gen_random_uuid())
    ON CONFLICT (email) DO NOTHING;

    -- 5. Crear Productos Base
    -- Insumos
    INSERT INTO productos (categoria_id, unidad_medida_id, codigo_interno, nombre, tipo_producto, precio_referencia)
    VALUES 
        (v_cat_insumo, v_um_kg, 'IN-001', 'Harina de Trigo Alta Proteína', 'insumo', 15.50),
        (v_cat_insumo, v_um_kg, 'IN-002', 'Queso Mozzarella', 'insumo', 120.00),
        (v_cat_insumo, v_um_lt, 'IN-003', 'Salsa de Tomate Base', 'insumo', 35.00)
    RETURNING id INTO v_prod_harina;

    SELECT id INTO v_prod_queso FROM productos WHERE codigo_interno = 'IN-002';
    SELECT id INTO v_prod_salsa FROM productos WHERE codigo_interno = 'IN-003';

    -- Empaques
    INSERT INTO productos (categoria_id, unidad_medida_id, codigo_interno, nombre, tipo_producto, precio_referencia)
    VALUES 
        (v_cat_empaque, v_um_pza, 'EM-001', 'Caja para Pizza Mediana 14"', 'empaque', 8.50)
    RETURNING id INTO v_prod_caja;

    -- Preparados
    INSERT INTO productos (categoria_id, unidad_medida_id, codigo_interno, nombre, tipo_producto, precio_referencia)
    VALUES 
        (v_cat_preparado, v_um_kg, 'PR-001', 'Masa Fermentada Lista', 'preparado', 25.00)
    RETURNING id INTO v_prod_masa;

    -- 6. Configurar Stocks Mínimos y Máximos (Comisariato y Sucursal Norte)
    -- Comisariato maneja mucho volumen
    INSERT INTO productos_sucursal (producto_id, sucursal_id, stock_minimo, stock_maximo, punto_reorden)
    VALUES 
        (v_prod_harina, v_comisariato_id, 100, 500, 150),
        (v_prod_queso, v_comisariato_id, 50, 200, 80),
        (v_prod_caja, v_comisariato_id, 1000, 5000, 1500)
    ON CONFLICT DO NOTHING;

    -- Sucursal Norte maneja poco volumen
    INSERT INTO productos_sucursal (producto_id, sucursal_id, stock_minimo, stock_maximo, punto_reorden)
    VALUES 
        (v_prod_queso, v_sucursal_norte_id, 10, 30, 15),
        (v_prod_caja, v_sucursal_norte_id, 100, 500, 150),
        (v_prod_masa, v_sucursal_norte_id, 5, 20, 10)
    ON CONFLICT DO NOTHING;

    -- 7. Agregar Inventario Inicial en Comisariato (Esto disparará el trigger que llena saldos_inventario)
    -- Se usa un usuario administrador o almacenista para el registro
    DECLARE
        v_admin_user UUID;
        v_tipo_ajuste_pos INT;
    BEGIN
        SELECT id INTO v_admin_user FROM usuarios WHERE email = 'admin@prontopizza.com' LIMIT 1;
        SELECT id INTO v_tipo_ajuste_pos FROM tipos_movimiento WHERE codigo = 'AJU_POSITIVO';

        IF v_admin_user IS NOT NULL AND v_tipo_ajuste_pos IS NOT NULL THEN
            -- Inyectar inventario inicial en el comisariato
            INSERT INTO movimientos_inventario 
                (tipo_movimiento_id, producto_id, sucursal_destino_id, cantidad, costo_unitario, notas, registrado_por_id)
            VALUES 
                (v_tipo_ajuste_pos, v_prod_harina, v_comisariato_id, 300, 15.50, 'Inventario Inicial', v_admin_user),
                (v_tipo_ajuste_pos, v_prod_queso, v_comisariato_id, 150, 120.00, 'Inventario Inicial', v_admin_user),
                (v_tipo_ajuste_pos, v_prod_salsa, v_comisariato_id, 100, 35.00, 'Inventario Inicial', v_admin_user),
                (v_tipo_ajuste_pos, v_prod_caja, v_comisariato_id, 2500, 8.50, 'Inventario Inicial', v_admin_user),
                (v_tipo_ajuste_pos, v_prod_masa, v_comisariato_id, 50, 25.00, 'Inventario Inicial', v_admin_user);
                
            -- Inyectar algo de inventario en la Sucursal Norte para que "Norte" tenga saldos
            INSERT INTO movimientos_inventario 
                (tipo_movimiento_id, producto_id, sucursal_destino_id, cantidad, costo_unitario, notas, registrado_por_id)
            VALUES 
                (v_tipo_ajuste_pos, v_prod_queso, v_sucursal_norte_id, 12, 120.00, 'Inventario Inicial Sucursal', v_admin_user),
                (v_tipo_ajuste_pos, v_prod_caja, v_sucursal_norte_id, 200, 8.50, 'Inventario Inicial Sucursal', v_admin_user),
                (v_tipo_ajuste_pos, v_prod_masa, v_sucursal_norte_id, 8, 25.00, 'Inventario Inicial Sucursal', v_admin_user);
        END IF;
    END;

    RAISE NOTICE '¡Datos de prueba generados exitosamente!';
END $$;
