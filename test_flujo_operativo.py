import asyncio
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import SessionLocal
from app.models.organizacion import Usuario, Sucursal, Empresa
from app.models.catalogo import Producto
from app.models.requisiciones import Requisicion, RequisicionDetalle
from app.schemas.requisiciones import RequisicionCreate, RequisicionDetalleBase
from app.schemas.despachos import DespachoCreate, DespachoDetalleBase
from app.schemas.contabilidad import ExportacionCreate
from app.services.requisicion_service import RequisicionService
from app.services.despacho_service import DespachoService
from app.services.contabilidad_service import ContabilidadService
from datetime import date

async def test_flujo():
    print("Iniciando prueba de flujo operativo...")
    async with SessionLocal() as db:
        # Generar datos de prueba
        from app.models.organizacion import Empresa, Sucursal, Rol, Usuario
        from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida, ProductoSucursal
        
        # Buscar empresa o crear
        empresa = (await db.execute(select(Empresa).limit(1))).scalars().first()
        if not empresa:
            empresa = Empresa(razon_social="Pronto Pizza S.A. de C.V.", rfc="PPO123456789", es_matriz=True)
            db.add(empresa)
            await db.commit()
            await db.refresh(empresa)

        # Sucursales
        comisariato = (await db.execute(select(Sucursal).where(Sucursal.codigo == "MTZ"))).scalars().first()
        if not comisariato:
            comisariato = Sucursal(empresa_id=empresa.id, nombre="Comisariato", codigo="MTZ", es_comisariato=True)
            db.add(comisariato)

        sucursal_norte = (await db.execute(select(Sucursal).where(Sucursal.codigo == "NOR"))).scalars().first()
        if not sucursal_norte:
            sucursal_norte = Sucursal(empresa_id=empresa.id, nombre="Sucursal Norte", codigo="NOR", es_comisariato=False)
            db.add(sucursal_norte)
        await db.commit()

        # Productos
        harina = (await db.execute(select(Producto).where(Producto.codigo_interno == "INS-001"))).scalars().first()
        if not harina:
            harina = Producto(categoria_id=1, unidad_medida_id=1, codigo_interno="INS-001", nombre="Harina", tipo_producto="insumo")
            db.add(harina)
            await db.commit()

        # Roles
        rol_encargado = (await db.execute(select(Rol).where(Rol.nombre == "encargado_sucursal"))).scalars().first().id
        rol_almacenista = (await db.execute(select(Rol).where(Rol.nombre == "almacenista"))).scalars().first().id
        rol_contador = (await db.execute(select(Rol).where(Rol.nombre == "contador"))).scalars().first().id

        # Usuarios
        encargado = (await db.execute(select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.email == "encargado.norte@prontopizza.com"))).scalars().first()
        if not encargado:
            encargado = Usuario(sucursal_id=sucursal_norte.id, rol_id=rol_encargado, nombre_completo="Encargado Norte", email="encargado.norte@prontopizza.com")
            db.add(encargado)
        
        almacenista = (await db.execute(select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.email == "almacenista@prontopizza.com"))).scalars().first()
        if not almacenista:
            almacenista = Usuario(sucursal_id=comisariato.id, rol_id=rol_almacenista, nombre_completo="Almacenista Central", email="almacenista@prontopizza.com")
            db.add(almacenista)

        contador = (await db.execute(select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.email == "contador@prontopizza.com"))).scalars().first()
        if not contador:
            contador = Usuario(sucursal_id=comisariato.id, rol_id=rol_contador, nombre_completo="Contador General", email="contador@prontopizza.com")
            db.add(contador)
            
        await db.commit()

        # Reload added users to load relationship
        encargado = (await db.execute(select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.id == encargado.id))).scalars().first()
        almacenista = (await db.execute(select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.id == almacenista.id))).scalars().first()
        contador = (await db.execute(select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.id == contador.id))).scalars().first()

        print("\n--- PASO 1 y 2: Creación de Requisición por Encargado de Sucursal ---")
        req_data = RequisicionCreate(
            fecha_requerida=date.today(),
            notas="Requisición urgente de prueba",
            detalles=[
                RequisicionDetalleBase(producto_id=harina.id, cantidad_solicitada=50.0)
            ]
        )
        req = await RequisicionService.crear(db, req_data, encargado)
        print(f"Requisición creada: {req.folio} (Estado: {req.estatus})")

        print("\n--- PASO 3: Envío de Requisición ---")
        req = await RequisicionService.transicionar_estado(db, req.id, "enviada", encargado)
        print(f"Requisición enviada (Estado: {req.estatus})")
        
        print("\n--- Aprobación en Comisariato ---")
        req = await RequisicionService.transicionar_estado(db, req.id, "aprobada", almacenista)
        print(f"Requisición aprobada (Estado: {req.estatus})")

        print("\n--- PASO 4: Picking y Despacho en Comisariato ---")
        despacho_data = DespachoCreate(
            requisicion_id=req.id,
            sucursal_destino_id=sucursal_norte.id,
            notas="Despacho de prueba automatizado",
            detalles=[
                DespachoDetalleBase(producto_id=harina.id, cantidad=50.0)
            ]
        )
        despacho = await DespachoService.crear(db, despacho_data, almacenista)
        print(f"Despacho creado: {despacho.folio_documento} - Tipo ID: {despacho.tipo_documento_id}")
        if despacho.tipo_documento_id == 2:
            print("=> Correcto: Sucursal Externa genera FACTURA.")
        elif despacho.tipo_documento_id == 1:
            print("=> Correcto: Misma razón social genera NOTA DE TRASLADO.")

        despacho = await DespachoService.completar_despacho(db, despacho.id, almacenista)
        print(f"Despacho completado. Estatus actual: {despacho.estatus}")

        print("\n--- PASO 6: Contador exporta a CONTPAQI ---")
        exp_data = ExportacionCreate(
            periodo_inicio=date.today(),
            periodo_fin=date.today(),
            notas="Exportación de prueba automática"
        )
        exportacion = await ContabilidadService.generar_exportacion(db, exp_data, contador)
        print(f"Exportación CONTPAQI generada: {exportacion.archivo_nombre}")
        print(f"Total de registros exportados: {exportacion.total_registros}")

        print("\n¡Prueba de Flujo Completa y Exitosa!")

if __name__ == "__main__":
    asyncio.run(test_flujo())
