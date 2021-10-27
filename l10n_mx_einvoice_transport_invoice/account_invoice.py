# -*- encoding: utf-8 -*-


from odoo import api, fields, models, _, tools, release
from datetime import datetime
from datetime import datetime, date
from odoo.exceptions import UserError, RedirectWarning, ValidationError

## Manejo de Fechas y Horas ##
from pytz import timezone
import pytz
import base64

from xml.dom import minidom

import re

import logging
_logger = logging.getLogger(__name__)

import re

class AccountInvoice(models.Model):
    _inherit = 'account.move'
         
    @api.depends('cfdi_state','cfdi_folio_fiscal')
    def _compute_cfdi_values_extend(self):
        '''Fill the invoice fields from the cfdi values.
        '''       
        attachment_obj = self.env['ir.attachment']
        for rec in self:
            if rec.move_type in ('out_invoice','out_refund'):
                if rec.transport_document_cfdi:
                    xml_data = rec._get_attach_xml_file_content()
                    if xml_data:
                        cfdi_minidom = minidom.parseString(xml_data)
                        if cfdi_minidom.getElementsByTagName('tfd:TimbreFiscalDigital'):
                            subnode = cfdi_minidom.getElementsByTagName('tfd:TimbreFiscalDigital')[0]
                            rfcprovcertif = subnode.getAttribute('RfcProvCertif') if subnode.getAttribute('RfcProvCertif') else ''
                            rec.rfcprovcertif = rfcprovcertif
                    else:
                        rec.rfcprovcertif = False
                else:
                    rec.rfcprovcertif = False
            else:
                rec.rfcprovcertif = False


    transport_document_cfdi = fields.Boolean('CFDI Traslado')
    rfcprovcertif = fields.Char('RfcProvCertif', size=64, compute="_compute_cfdi_values_extend")


    def _get_attach_xml_file_content(self):
        attachment = self.env['ir.attachment'].search([('res_model', '=', 'account.move'), 
                                                       ('res_id', '=', self.id), 
                                                       ('name', 'ilike', '.xml')], order="id desc", limit=1)
        if not attachment:
            return False
        try:
            file_path = self.env['ir.attachment']._full_path('checklist').replace('checklist','') + attachment.store_fname
            attach_file = open(file_path, 'rb')
            xml_data = attach_file.read()
            attach_file.close()
            return xml_data
        except:
            _logger.error("No se pudo leer el archivo XML adjunto a esta factura, favor de revisar...")
            return False

    @api.onchange('transport_document_cfdi','move_type')
    def onchange_transport_doument(self):
        sat_tipo_obj = self.env['sat.tipo.comprobante']
        if self.transport_document_cfdi:
            if self.transport_document_cfdi == True:
                tipo_id = sat_tipo_obj.search([('code','=','T')], limit=1)
                self.type_document_id = tipo_id[0].id if tipo_id else False
                self.metodo_pago_id = False
                self.pay_method_id = False
            else:
                if self.move_type in ('out_invoice','out_refund'):
                    if not self.uso_cfdi_id:
                        raise UserError('Error!\nEl campo Uso CFDI es Obligatorio.')
            
                    if rec.move_type == 'out_invoice':
                        tipo_id = sat_tipo_obj.search([('code','=','I')], limit=1)
                        self.type_document_id = tipo_id[0].id if tipo_id else False
                    else:
                        tipo_id = sat_tipo_obj.search([('code','=','E')], limit=1)
                        self.type_document_id = tipo_id[0].id if tipo_id else False

    # @api.onchange('partner_id')
    # def _onchange_partner_id(self):
    #     res = super(AccountInvoice, self)._onchange_partner_id()
    #     if self.transport_document_cfdi:
    #         self.metodo_pago_id = False
    #         self.uso_cfdi_id = self.partner_id.commercial_partner_id.uso_cfdi_id.id
    #         self.pay_method_id = False
    #     return res

    def action_post(self):
        sat_tipo_obj = self.env['sat.tipo.comprobante']
        for rec in self:
            if rec.move_type in ('out_invoice','out_refund'):
                if self.transport_document_cfdi:
                    tipo_id = sat_tipo_obj.search([('code','=','T')], limit=1)
                    self.type_document_id = tipo_id[0].id if tipo_id else False
                    # if self.metodo_pago_id:
                    #     self.metodo_pago_id = False
                    # if self.pay_method_id:
                    #     self.pay_method_id = False
                    if self.metodo_pago_id:
                        raise UserError(_("La Factura de traslado no requiere Metodo de Pago."))
                    if self.pay_method_id:
                        raise UserError(_("La Factura de traslado no requiere Forma de Pago."))

                if self.transport_document_cfdi == False:
                    if not self.uso_cfdi_id:
                        raise UserError('Error!\nEl campo Uso CFDI es Obligatorio.')
            
                    if rec.move_type == 'out_invoice':
                        tipo_id = sat_tipo_obj.search([('code','=','I')], limit=1)
                        self.type_document_id = tipo_id[0].id if tipo_id else False
                    else:
                        tipo_id = sat_tipo_obj.search([('code','=','E')], limit=1)
                        self.type_document_id = tipo_id[0].id if tipo_id else False

        res = super(AccountInvoice, self).action_post()        
        return res

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        sat_tipo_obj = self.env['sat.tipo.comprobante']
        type_document = res.move_type
        if res.transport_document_cfdi:
            tipo_id = sat_tipo_obj.search([('code','=','T')], limit=1)
            res.type_document_id = tipo_id[0].id if tipo_id else False
            return res
        if type_document == 'out_invoice':
            tipo_id = sat_tipo_obj.search([('code','=','I')], limit=1)
            res.type_document_id = tipo_id[0].id if tipo_id else False
        elif type_document == 'out_refund':
            tipo_id = sat_tipo_obj.search([('code','=','E')], limit=1)
            res.type_document_id = tipo_id[0].id if tipo_id else False
        return res



    @api.constrains('transport_document_cfdi','metodo_pago_id','pay_method_id')
    def _constraint_transport_document(self):
        if self.transport_document_cfdi:            
            if self.amount_total != 0.0:
                raise UserError(_("La Factura de traslado no requiere especificar Montos, debe ser igual 0.0."))
            for line in self.invoice_line_ids:
                if line.tax_ids:
                    raise UserError(_("La Factura de traslado no requiere Impuestos."))

        return True

    def _get_facturae_invoice_dict_data(self):
        res = super(AccountInvoice, self)._get_facturae_invoice_dict_data()
        if self.transport_document_cfdi:
            while(type(res)!=dict):
                try:
                    res = res[0]
                except:
                    res = res
            #### Pensado para CFDI Traslado ######
            if 'cfdi:Impuestos' in res['cfdi:Comprobante']:
                res['cfdi:Comprobante'].pop('cfdi:Impuestos')
            if 'cfdi:MetodoPago' in res['cfdi:Comprobante']:
                res['cfdi:Comprobante'].pop('cfdi:MetodoPago')
            if 'cfdi:FormaPago' in res['cfdi:Comprobante']:
                res['cfdi:Comprobante'].pop('FormaPago')
            if 'CondicionesDePago' in res['cfdi:Comprobante']:
                res['cfdi:Comprobante'].pop('CondicionesDePago')
            res['cfdi:Comprobante'].update({'TipoDeComprobante':'T'})
            for concepto in res['cfdi:Comprobante']['cfdi:Conceptos']:
                if 'cfdi:Impuestos' in concepto['cfdi:Concepto']:
                    concepto['cfdi:Concepto'].pop('cfdi:Impuestos')
            sat_tipo_obj = self.env['sat.tipo.comprobante']
            tipo_id = sat_tipo_obj.search([('code','=','T')], limit=1)
            self.write({'type_document_id': tipo_id[0].id if tipo_id else False})
        return res