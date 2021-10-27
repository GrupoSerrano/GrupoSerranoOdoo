# -*- encoding: utf-8 -*-
#    Coded by: german_442 email: (german.ponce@argil.mx)
##############################################################################

from odoo import api, fields, models, _, tools
from datetime import datetime, date
import time
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.osv import osv, expression


import logging
_logger = logging.getLogger(__name__)

class InvoiceWaybillTrailerInfo(models.Model):
    _name = 'invoice.waybill.trailer.info'
    _description = 'Nodos para Remolques'
    
    invoice_id = fields.Many2one('account.move', 'Factura')

    subtype_trailer_id = fields.Many2one('waybill.tipo.remolque', 'Subtipo Remolque',
                                              help="Atributo: SubTipoRem")

    trailer_plate_cp = fields.Char('Placa',
                                              help="Atributo: Placa")

    
class AccountInvoice(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'

    @api.depends('invoice_line_complement_cp_ids')
    def _get_total_items_cp(self):
        total_quantity_items = 0
        for rec in self:
            if rec.invoice_line_complement_cp_ids:
                total_quantity_items = len(rec.invoice_line_complement_cp_ids)
            rec.total_quantity_items = total_quantity_items

    def _get_permiso_general_tpaf01(self):
        code = 'TPAF01'
        tipo_permiso_obj = self.env["waybill.tipo.permiso"]
        tipo_permiso_general_id = tipo_permiso_obj.search([('code','=',code)], limit=1)
        if tipo_permiso_general_id:
            return tipo_permiso_general_id.id
        else:
            return False

    @api.depends('invoice_line_complement_cp_ids')
    def _get_weight_total(self):
        for rec in self:
            weight_charge_total = 0
            if rec.invoice_line_complement_cp_ids:
                for merchandise in rec.invoice_line_complement_cp_ids:
                    weight_line = merchandise.weight_charge * merchandise.quantity
                    weight_charge_total += weight_line
                    # weight_charge_total += merchandise.weight_charge
            rec.weight_charge_total = weight_charge_total

    def _get_default_clave_transporte(self):
        clave_transporte_obj = self.env['waybill.clave.transporte']
        clave_transporte_federal = clave_transporte_obj.search([('code','=','01')], limit=1)
        if clave_transporte_federal:
            return clave_transporte_federal.id
        
        return False

    def _get_default_station_01(self):
        tipo_estacion_obj = self.env['waybill.tipo.estacion']
        estacion_nacional = tipo_estacion_obj.search([('code','=','01')], limit=1)
        if estacion_nacional:
            return estacion_nacional.id
        
        return False

    cfdi_complemento = fields.Selection([('na','Sin Complemento'),('carta_porte', 'Carta porte')],
        string='Complemento CFDI', readonly=True, states={'draft': [('readonly', False)]}, 
                                        copy=False, default='na', required=True)  

    ### Lineas ###
    invoice_line_complement_cp_ids = fields.One2many('invoice.line.complement.cp', 'invoice_id',
                                                     'Lineas Complemento CP', copy=True, auto_join=True)
    ##############
    international_shipping = fields.Selection([('SI','SI'),('NO','NO')], 'Transporte Internacional', 
                                              default="NO", help="Atributo: TranspInternac")
    
    shipping_complement_type = fields.Selection([('Entrada','Entrada'),('Salida','Salida')], 'Entrada/Salida Mercancia', default="Salida",
                                                help="Atributo: EntradaSalidaMerc")

    tipo_transporte_id = fields.Many2one('waybill.clave.transporte', 'Tipo Transporte',
                                         help="Atributo: ViaEntradaSalida", default=_get_default_clave_transporte)

    tipo_transporte_code = fields.Char('Codigo Tipo Transporte', related="tipo_transporte_id.code",
                                         help="Atributo: ViaEntradaSalida")

    travel_total_distance =  fields.Float('Distancia total recorrida', digits=(14,2),
                                         help="Atributo: TotalDistRec")

    travel_total_distance_type = fields.Selection([('KM','Kilometros'),('M','Metros')], 
                                                  'Tipo Distancia Recorrida (Total)',
                                                  default="KM")
    
    weight_charge_total = fields.Float('Peso Bruto Total', digits=(14,3), compute="_get_weight_total")

    ### Ubicaciones ###
    ### Remitente ####
    waybill_origin_station_type_id = fields.Many2one('waybill.tipo.estacion', 'Tipo Estación (Origen)',
                                                     help="Atributo: TipoEstacion",  default=_get_default_station_01)

    waybill_origin_partner_id = fields.Many2one('res.partner', 'Remitente',
                                                help="Atributo: RFCRemitente y Atributo: NombreRemitente")

    waybill_origin_date_out = fields.Datetime('Fecha/Hora Salida', 
                                              help="Atributo: FechaHoraSalida")

    waybill_origin_partner_references = fields.Char('Referencias (Origen)',
                                                    help="Atributo: Referencia")
    ### Destinatario ####

    waybill_destiny_station_type_id = fields.Many2one('waybill.tipo.estacion', 'Tipo Estación (Destino)',
                                                     help="Atributo: TipoEstacion", default=_get_default_station_01)

    waybill_destiny_partner_id = fields.Many2one('res.partner', 'Destinatario',
                                                help="Atributo: RFCDestinatario y Atributo: NombreDestinatario")

    waybill_destiny_date_prog_arrived = fields.Datetime('Fecha/Hora programada de Llegada', 
                                              help="Atributo: FechaHoraProgLlegada")

    waybill_destiny_partner_references = fields.Char('Referencias (Destino)',
                                                    help="Atributo: Referencia")

    waybill_destiny_distance = fields.Float('Distancia recorrida', digits=(14,2),
                                         help="Atributo: DistanciaRecorrida")

    waybill_destiny_total_distance_type = fields.Selection([('KM','Kilometros'),('M','Metros')], 'Tipo Distancia Recorrida',
                                                  default="KM")

    total_quantity_items = fields.Integer('Total Mercancias', compute="_get_total_items_cp",
                                         help="Atributo: NumTotalMercancias")

    waybill_tasc_charges = fields.Float('Cargo por Tasacion', digits=(14,2),
                                         help="Atributo: CargoPorTasacion")


    type_stc_permit_id = fields.Many2one('waybill.tipo.permiso', 'Permiso STC',
                                                     help="Atributo: PermSCT", default=_get_permiso_general_tpaf01)

    type_stc_permit_number = fields.Char('Numero Permiso STC',
                                                     help="Atributo: NumPermisoSCT")

    partner_insurance_id = fields.Many2one('res.partner', 'Aseguradora',
                                           help="Atributo: NombreAseg")

    partner_insurance_number = fields.Char('No. Póliza Seguro', related="partner_insurance_id.partner_insurance_number", 
                                        readonly=False, help="Atributo: NumPolizaSeguro")

    configuracion_federal_id = fields.Many2one('waybill.configuracion.autotransporte.federal', 'Configuracion Auto Transporte Federal',
                                              help="Atributo: ConfigVehicular")

    vehicle_plate_cp = fields.Char('Placa Vehicular',
                                              help="Atributo: PlacaVM")

    vehicle_year_model_cp = fields.Char('Año del Modelo',
                                              help="Atributo: AnioModeloVM")

    trailer_line_ids = fields.One2many('invoice.waybill.trailer.info', 'invoice_id', 'Remolques')

    driver_cp_id = fields.Many2one('hr.employee', 'Operador')

    driver_cp_vat = fields.Char('RFC Operador', related="driver_cp_id.driver_cp_vat", 
                                        readonly=False, help="Atributo: RFCOperador")

    cp_driver_license = fields.Char('Numero de Licencia', related="driver_cp_id.cp_driver_license", 
                                        readonly=False, help="Atributo: NumLicencia")

    partner_owner_id = fields.Many2one('res.partner', 'Propietario',
                                           help="Atributo: cartaporte:Propietario")

    partner_lessee_id = fields.Many2one('res.partner', 'Arrendatario',
                                           help="Atributo: cartaporte:Arrendatario")

    partner_notified_id = fields.Many2one('res.partner', 'Notificado',
                                           help="Atributo: cartaporte:Arrendatario")
    
    waybill_origin_station_id = fields.Many2one(
        'waybill.complemento.estacion', string='Estación Origen')
    waybill_destiny_station_id = fields.Many2one(
        'waybill.complemento.estacion', string='Estación Destino')
    waybill_num_guia_aereo = fields.Char(string="Número Guía")
    waybill_transportista_aereo_id = fields.Many2one('res.partner', string="Transportista")
    codigo_transportista_aereo_id = fields.Many2one(related="waybill_transportista_aereo_id.codigo_transportista_aereo_id")
    waybill_embarcador_aereo_id = fields.Many2one('res.partner', string="Embarcador")

    waybill_pedimento = fields.Char(string="Pedimento")
    
    @api.onchange('waybill_num_guia_aereo')
    def _onchange_waybill_num_guia_aereo(self):
        if self.waybill_num_guia_aereo and (len(self.waybill_num_guia_aereo) < 12 or len(self.waybill_num_guia_aereo) > 15):
            raise ValidationError(_('Aviso!\n\nLa longitud para el Número de Guía debe ser entre 12 y 15 caracteres'))


    @api.onchange('tipo_transporte_id')
    def _onchange_tipo_transporte_id(self):
        if self.tipo_transporte_id.code not in ('01','03'):
            raise ValidationError(_("Advertencia!\n\nSolo se soporta 01 (Autotransporte Federal) y 03 (Transporte Aéreo)"))
        
        if self.tipo_transporte_id.code == '01': # Autotransporte
            self.type_stc_permit_id = self.env["waybill.tipo.permiso"].search([('code','=','TPAF01')], limit=1).id
            
        elif self.tipo_transporte_id.code == '03': # Aereo
            self.type_stc_permit_id = self.env["waybill.tipo.permiso"].search([('code','=','TPTA01')], limit=1).id
    
    @api.onchange('waybill_origin_partner_id')
    def onchange_waybill_origin_partner_id(self):
        if self.waybill_origin_partner_id:
            if self.waybill_origin_partner_id.l10n_mx_street_reference:
                self.waybill_origin_partner_references = self.waybill_origin_partner_id.l10n_mx_street_reference

    @api.onchange('waybill_destiny_partner_id')
    def onchange_waybill_destiny_partner_id(self):
        if self.waybill_destiny_partner_id:
            if self.waybill_destiny_partner_id.l10n_mx_street_reference:
                self.waybill_destiny_partner_references = self.waybill_destiny_partner_id.l10n_mx_street_reference
    

    def refresh_complement_waybill_data(self):

        return True


class InvoiceLineComplementCP(models.Model):
    _name = 'invoice.line.complement.cp'
    _description = 'Lineas Complemento Carta Porte'
    _rec_name = 'invoice_line_id'

    product_id = fields.Many2one('product.product', 'Producto')

    description = fields.Char('Descripción')

    invoice_line_id = fields.Many2one('account.move.line', 'Linea Factura')  

    sat_product_id = fields.Many2one('product.unspsc.code','Producto SAT',domain=[('applies_to', '=', 'product')]) ### Campo LdM E.E.

    quantity = fields.Float('Cantidad', digits=(14,4))

    sat_uom_id = fields.Many2one('product.unspsc.code','UdM SAT', domain=[('applies_to', '=', 'uom')]) ### Campo LdM E.E.

    invoice_id = fields.Many2one('account.move', 'Factura Relacionada')  

    weight_charge = fields.Float('Peso en KG', digits=(14,3))

    dimensions_charge = fields.Char('Dimensiones', size=128)

    clave_stcc_id = fields.Many2one('waybill.producto.stcc', 'Clave STCC')

    hazardous_material = fields.Selection([('Si','Si'),('No','No')], string="Material Peligroso", default="No" )
    
    hazardous_key_product_id = fields.Many2one('waybill.materiales.peligrosos', 'Clave Material Peligroso')

    charge_value = fields.Float('Valor Mercancia', digits=(14,3))


    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            if self.product_id.dimensiones_plg:
                self.dimensions_charge = self.product_id.dimensiones_plg
            if self.product_id.weight:
                self.weight_charge = self.product_id.weight
            if self.product_id.unspsc_code_id:
                ### Campo LdM E.E.
                self.sat_product_id = self.product_id.unspsc_code_id.id
            if self.product_id.clave_stcc_id:
                self.clave_stcc_id = self.product_id.clave_stcc_id.id
            if self.product_id.uom_id and self.product_id.uom_id.unspsc_code_id:
                ### Campo LdM E.E.
                self.sat_uom_id = self.product_id.uom_id.unspsc_code_id.id
            self.description =  self.product_id.name
