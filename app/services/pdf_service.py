import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.despachos import Despacho
from app.models.requisiciones import Requisicion

class PDFService:
    
    @staticmethod
    def generar_pdf_despacho(despacho: Despacho) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=2))
        styles.add(ParagraphStyle(name='CenterTitle', parent=styles['Heading1'], alignment=1))
        
        # Header
        elements.append(Paragraph("<b>PRONTO PIZZA</b>", styles['CenterTitle']))
        doc_type = despacho.tipo_documento.nombre if despacho.tipo_documento else "Nota de Traslado"
        elements.append(Paragraph(f"<b>{doc_type.upper()}</b>", styles['CenterTitle']))
        elements.append(Spacer(1, 12))
        
        # Info
        folio = despacho.folio_documento or "N/A"
        fecha = despacho.fecha_despacho.strftime("%d/%m/%Y %H:%M") if despacho.fecha_despacho else "No completado"
        estatus = despacho.estatus.upper()
        
        info_text = f"""
        <b>Folio:</b> {folio}<br/>
        <b>Fecha:</b> {fecha}<br/>
        <b>Estatus:</b> {estatus}<br/>
        <b>Notas:</b> {despacho.notas or 'Ninguna'}<br/>
        """
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Table Header
        data = [['Producto', 'Cantidad', 'Costo U.', 'Total']]
        
        # Table Data
        total_monto = 0
        for det in despacho.detalles:
            prod_nombre = str(det.producto_id)[:8] # Fallback si no está cargado
            if 'producto' in det.__dict__ and det.producto:
                prod_nombre = det.producto.nombre
                
            qty = float(det.cantidad)
            costo = float(det.costo_unitario) if getattr(det, 'costo_unitario', None) else 0.0
            subtotal = qty * costo
            total_monto += subtotal
            
            data.append([
                prod_nombre,
                f"{qty:.2f}",
                f"${costo:.2f}",
                f"${subtotal:.2f}"
            ])
            
        data.append(['', '', 'TOTAL:', f'${total_monto:.2f}'])
        
        table = Table(data, colWidths=[250, 80, 80, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Producto left align
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'), # Total bold
        ]))
        
        elements.append(table)
        
        # Footer
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Este documento no es un comprobante fiscal.", styles['CenterTitle']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generar_pdf_requisicion(requisicion: Requisicion) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='CenterTitle', parent=styles['Heading1'], alignment=1))
        
        elements.append(Paragraph("<b>PRONTO PIZZA</b>", styles['CenterTitle']))
        elements.append(Paragraph("<b>REQUISICIÓN DE INSUMOS</b>", styles['CenterTitle']))
        elements.append(Spacer(1, 12))
        
        folio = requisicion.folio or "N/A"
        fecha_req = requisicion.fecha_requerida.strftime("%d/%m/%Y") if requisicion.fecha_requerida else "N/A"
        
        info_text = f"""
        <b>Folio:</b> {folio}<br/>
        <b>Fecha Requerida:</b> {fecha_req}<br/>
        <b>Estatus:</b> {requisicion.estatus.upper()}<br/>
        <b>Notas:</b> {requisicion.notas or 'Ninguna'}<br/>
        """
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 20))
        
        data = [['Producto', 'Cant. Solicitada', 'Cant. Aprobada', 'Cant. Surtida']]
        
        for det in requisicion.detalles:
            prod_nombre = str(det.producto_id)[:8]
            if 'producto' in det.__dict__ and det.producto:
                prod_nombre = det.producto.nombre
            
            data.append([
                prod_nombre,
                f"{float(det.cantidad_solicitada):.2f}" if det.cantidad_solicitada is not None else "0.00",
                f"{float(det.cantidad_aprobada):.2f}" if det.cantidad_aprobada is not None else "-",
                f"{float(det.cantidad_surtida):.2f}" if det.cantidad_surtida is not None else "-"
            ])
            
        table = Table(data, colWidths=[250, 100, 100, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Este documento es de uso interno.", styles['CenterTitle']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
