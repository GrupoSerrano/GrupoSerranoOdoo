# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to Odoo, Open Source Management Solution
#
#    All Rights Reserved.
#    info skype: german_442 email: (german.ponce@argil.mx)
############################################################################
#    Coded by: german_442 email: (german.ponce@argil.mx)

##############################################################################

from odoo import api, fields, models, _, tools, release
from datetime import datetime
from datetime import datetime, date
from odoo.exceptions import UserError, RedirectWarning, ValidationError

## Manejo de Fechas y Horas ##
from pytz import timezone
import pytz

import re

import logging
_logger = logging.getLogger(__name__)

import re

#### Librerias LdM E.E. ###
from lxml import etree
from xml.dom import minidom
from xml.dom.minidom import parse, parseString

from odoo.tools import DEFAULT_SERVER_TIME_FORMAT
import base64
from io import BytesIO
from lxml.objectify import fromstring

### Reemplazo de las Cadenas XSLT Para Cadena
CFDI_TEMPLATE_33 = 'l10n_mx_edi.cfdiv33'
CFDI_XSLT_CADENA_TFD = 'l10n_mx_einvoice_waybill_complemento_ee/SAT/cadenaoriginal_3_3/cadenaoriginal_TFD_1_1.xslt'
CFDI_XSLT_CADENA = 'l10n_mx_einvoice_waybill_complemento_ee/SAT/cadenaoriginal_3_3/cadenaoriginal_3_3.xslt'

def create_list_html(array):
    '''Convert an array of string to a html list.
    :param array: A list of strings
    :return: an empty string if not array, an html list otherwise.
    '''
    if not array:
        return ''
    msg = ''
    for item in array:
        msg += '<li>' + item + '</li>'
    return '<ul>' + msg + '</ul>'


# Cambiar el error
msg2 = "Contacta a tu administrador de Sistema o contactanos info@argil.mx"

#### Metodos de la LdM E.E. ####

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'
    
    def _l10n_mx_edi_export_invoice_cfdi(self, invoice):
        self.ensure_one()
        if invoice.cfdi_complemento != 'carta_porte':
            return super(AccountEdiFormat, self)._l10n_mx_edi_export_invoice_cfdi(invoice)

        # == CFDI values ==
        cfdi_values = self._l10n_mx_edi_get_invoice_cfdi_values(invoice)
        if cfdi_values.get('document_type', '') == 'T':
            ### Integración CFDI Traslado ###
            _logger.info("\n########## Si es un CFDI de Traslado no lleva tipo de cambio y la moneda es XXX >>>>>>>> ")
            cfdi_values.update({
                         'currency_name': 'XXX',
                         'currency_conversion_rate': False,
                       })

        # == Generate the CFDI ==
        cfdi = self.env.ref('l10n_mx_edi.cfdiv33')._render(cfdi_values)

        #### Trucando el CFDI XML para corregir el error en la moneda XXX el 0.0 por 0 ya que Qweb lo borra ###
        ### CFDI Traslado ####
        if cfdi_values.get('document_type', '') == 'T':
            _logger.info("\n########## Si es un CFDI de Traslado eliminamos el Total y SubTotal por el error en decimales. >>>>>>>> ")
            cfdi_minidom = minidom.parseString(cfdi)
            if cfdi_minidom.getElementsByTagName('cfdi:Comprobante'):
                subnode_cfdi_comprobante = cfdi_minidom.getElementsByTagName('cfdi:Comprobante')[0]
                ### Obtenemos los Totales para verificar en modo Debug ####
                cfdi_minidom_total = subnode_cfdi_comprobante.getAttribute('Total') if subnode_cfdi_comprobante.getAttribute('Total') else ''
                cfdi_minidom_subtotal = subnode_cfdi_comprobante.getAttribute('SubTotal') if subnode_cfdi_comprobante.getAttribute('SubTotal') else ''
                ### Eliminamos los Totales ####
                subnode_cfdi_comprobante.setAttribute('Total', str(0))
                subnode_cfdi_comprobante.setAttribute('SubTotal', str(0))
                cfdi_custom = cfdi_minidom.toxml('UTF-8')
                cfdi = cfdi_custom

        #### Proceso Normal ####
        decoded_cfdi_values = invoice._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi)
        cfdi_cadena_crypted = cfdi_values['certificate'].sudo().get_encrypted_cadena(decoded_cfdi_values['cadena'])
        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted

        # == Optional check using the XSD ==
        # xsd_attachment = self.env.ref('l10n_mx_edi.xsd_cached_cfdv33_xsd', False)
        # xsd_datas = base64.b64decode(xsd_attachment.datas) if xsd_attachment else None

        # if xsd_datas:
        #     try:
        #         with BytesIO(xsd_datas) as xsd:
        #             _check_with_xsd(decoded_cfdi_values['cfdi_node'], xsd)
        #     except (IOError, ValueError):
        #         _logger.info(_('The xsd file to validate the XML structure was not found'))
        #     except Exception as e:
        #         return {'errors': str(e).split('\\n')}
        cfdi_previo = etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print=True, xml_declaration=True, encoding='UTF-8')
        cfdi_previo_debug = str(cfdi_previo).replace('\n','')
        _logger.info("\nCFDI Precio con Complemento Carta Porte:\n%s" % cfdi_previo_debug)
        return {
            'cfdi_str': cfdi_previo,
        }


class AccountInvoice(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'


    @api.onchange('travel_total_distance','waybill_destiny_distance')
    def onchange_total_distance(self):
        if self.travel_total_distance:
            self.waybill_destiny_distance = self.travel_total_distance
    
    def _check_validations_complement_waybill(self):
        _logger.info("\n########## Realizamos algunas validaciones sobre el complemento de Carta Porte >>>>>>>> ")
        if self.cfdi_complemento == 'carta_porte':
            #### Si no tiene CP Forzamos la Escritura ####
            if self.company_id.partner_id.zip_sat_id and not self.company_id.partner_id.zip:
                self.company_id.partner_id.zip = self.company_id.partner_id.zip_sat_id.code

            if self.company_id.partner_id.commercial_partner_id.zip_sat_id and not self.company_id.partner_id.commercial_partner_id.zip:
                self.company_id.partner_id.commercial_partner_id.zip = self.company_id.partner_id.commercial_partner_id.zip_sat_id.code

            if self.partner_id.zip_sat_id and not self.partner_id.zip:
                self.partner_id.zip = self.partner_id.zip_sat_id.code

            #### Validaciones Direcciones ###
            ##### Origen #####
            waybill_origin_partner_id = self.waybill_origin_partner_id
            ### Si no tiene CP Forzamos la Escritura ####
            if waybill_origin_partner_id.zip_sat_id and not waybill_origin_partner_id.zip:
                waybill_origin_partner_id.zip = waybill_origin_partner_id.zip_sat_id.code

            waybill_origin_partner_parent_id = False
            if self.waybill_origin_partner_id.parent_id:
                waybill_origin_partner_parent_id = self.waybill_origin_partner_id.parent_id
                ### Si no tiene CP Forzamos la Escritura ####
                if waybill_origin_partner_parent_id.zip_sat_id and not waybill_origin_partner_parent_id.zip:
                    waybill_origin_partner_parent_id.zip = waybill_origin_partner_parent_id.zip_sat_id.code
            #### Dirección/Domicilio ####
            origin_partner_street = waybill_origin_partner_id.street_name
            if not origin_partner_street and waybill_origin_partner_parent_id:
                origin_partner_street = waybill_origin_partner_parent_id.street_name
            if not origin_partner_street:
                raise UserError("La Calle es un dato obligatorio de la dirección Origen.")
            origin_partner_state = ""
            if waybill_origin_partner_id.state_id and waybill_origin_partner_id.state_id.code:
                origin_partner_state = waybill_origin_partner_id.state_id.code
            
            if not origin_partner_state and waybill_origin_partner_parent_id:
                if waybill_origin_partner_parent_id.state_id and waybill_origin_partner_parent_id.state_id.code:
                    origin_partner_state = waybill_origin_partner_parent_id.state_id.code

            if not origin_partner_state:
                raise UserError("El estado ingresado en la direccion Origen no cuenta con el Codigo SAT.")

            origin_partner_country = ""
            if waybill_origin_partner_id.country_id and waybill_origin_partner_id.country_id.l10n_mx_edi_code:
                origin_partner_country = waybill_origin_partner_id.l10n_mx_edi_code

            if not origin_partner_country and waybill_origin_partner_parent_id:
                if waybill_origin_partner_parent_id.country_id and waybill_origin_partner_parent_id.country_id.l10n_mx_edi_code:
                    origin_partner_country = waybill_origin_partner_parent_id.country_id.l10n_mx_edi_code

            if not origin_partner_country:
                raise UserError("El pais ingresado en la direccion Origen no cuenta con el Codigo SAT.")

            origin_partner_zip = ""
            if waybill_origin_partner_id.zip_sat_id:
                origin_partner_zip = waybill_origin_partner_id.zip_sat_id.code
            if not origin_partner_zip and waybill_origin_partner_parent_id:
                if waybill_origin_partner_parent_id.zip_sat_id:
                    origin_partner_zip = waybill_origin_partner_parent_id.zip_sat_id.code
            if not origin_partner_zip:
                origin_partner_zip = waybill_origin_partner_id.zip
                if not origin_partner_zip and waybill_origin_partner_parent_id:
                    origin_partner_zip = waybill_origin_partner_parent_id.zip
                if not origin_partner_zip:
                    raise UserError("La direccion Origen no cuenta con el Codigo Postal.")

            ##### Destino #####
            waybill_destiny_partner_id = self.waybill_destiny_partner_id
            ### Si no tiene CP Forzamos la Escritura ####
            if waybill_destiny_partner_id.zip_sat_id and not waybill_destiny_partner_id.zip:
                waybill_destiny_partner_id.zip = waybill_destiny_partner_id.zip_sat_id.code

            waybill_destiny_partner_parent_id = False
            if self.waybill_destiny_partner_id.parent_id:
                waybill_destiny_partner_parent_id = self.waybill_destiny_partner_id.parent_id
                ### Si no tiene CP Forzamos la Escritura ####
                if waybill_destiny_partner_parent_id.zip_sat_id and not waybill_destiny_partner_parent_id.zip:
                    waybill_destiny_partner_parent_id.zip = waybill_destiny_partner_parent_id.zip_sat_id.code
            #### Dirección/Domicilio ####
            destiny_partner_street = waybill_destiny_partner_id.street_name
            if not destiny_partner_street and waybill_destiny_partner_parent_id:
                destiny_partner_street = waybill_destiny_partner_parent_id.street_name
            if not destiny_partner_street:
                raise UserError("La Calle es un dato obligatorio de la dirección Destino.")

            destiny_partner_state = ""
            if waybill_destiny_partner_id.state_id and waybill_destiny_partner_id.state_id.code:
                destiny_partner_state = waybill_destiny_partner_id.state_id.code
            if not destiny_partner_state and waybill_destiny_partner_parent_id:
                if waybill_destiny_partner_parent_id.state_id and waybill_destiny_partner_parent_id.state_id.code:
                    destiny_partner_state = waybill_destiny_partner_parent_id.state_id.code
            if not destiny_partner_state:
                raise UserError("El estado ingresado en la direccion Destino no cuenta con el Codigo SAT.")

            destiny_partner_country = ""
            if waybill_destiny_partner_id.country_id and waybill_destiny_partner_id.country_id.l10n_mx_edi_code:
                destiny_partner_country = waybill_destiny_partner_id.l10n_mx_edi_code
            if not destiny_partner_country and waybill_destiny_partner_parent_id:
                if waybill_destiny_partner_parent_id.country_id and waybill_destiny_partner_parent_id.country_id.l10n_mx_edi_code:
                    destiny_partner_country = waybill_destiny_partner_parent_id.country_id.l10n_mx_edi_code

            if not destiny_partner_country:
                raise UserError("El pais ingresado en la direccion Destino no cuenta con el Codigo SAT.")

            destiny_partner_zip = ""
            if waybill_destiny_partner_id.zip_sat_id:
                destiny_partner_zip = waybill_destiny_partner_id.zip_sat_id.code
            if not destiny_partner_zip and waybill_destiny_partner_parent_id:
                if waybill_destiny_partner_parent_id.zip_sat_id:
                    destiny_partner_zip = waybill_destiny_partner_parent_id.zip_sat_id.code
            if not destiny_partner_zip:
                destiny_partner_zip = waybill_destiny_partner_id.zip
                if not destiny_partner_zip and waybill_destiny_partner_parent_id:
                    destiny_partner_zip = waybill_destiny_partner_parent_id.zip
                if not destiny_partner_zip:
                    raise UserError("La direccion Destino no cuenta con el Codigo Postal.")
            
            #### Validacion de las Claves para el Complemento ####
            for line in self.invoice_line_complement_cp_ids:
                sat_product_id = line.sat_product_id
                if not sat_product_id:
                    raise UserError(_("Error!\nEl producto:\n %s \nNo cuenta con la Clave de Producto/Servicio del SAT." % line.sat_product_id.code))

                clave_stcc_id = line.clave_stcc_id
                if not sat_product_id:
                    raise UserError(_("Error!\nLa linea de factura:\n %s \nNo cuenta con la Clave Clave STCC del SAT." % line.sat_product_id.code))

                sat_uom_id = line.sat_uom_id
                if not sat_uom_id:
                    raise UserError(_("Error!\nLa linea de factura:\n %s \nNo cuenta con la Clave de Unidad de Medida SAT." % line.sat_product_id.code))

                if not line.weight_charge:
                    raise UserError(_("Error!\nLa linea de factura:\n %s \nNo cuenta con el Peso en KG." % line.product_id.name))
            
            ### Validacion del Operador ####
            driver_cp_id = self.driver_cp_id
            if self.driver_cp_id.country_id:
                if not self.driver_cp_id.country_id.l10n_mx_edi_code:
                    raise UserError("El Pais %s no cuenta con la clave SAT." % self.driver_cp_id.country_id.name) 
            
            ### Validacion del Propietario ###
            partner_owner_id = self.partner_owner_id
            if partner_owner_id:
                ### Si no tiene CP Forzamos la Escritura ####
                if partner_owner_id.zip_sat_id and not partner_owner_id.zip:
                    partner_owner_id.zip = partner_owner_id.zip_sat_id.code

                if partner_owner_id.parent_id:
                    partner_owner_id = partner_owner_id.parent_id
                if partner_owner_id.country_id:
                    if not partner_owner_id.country_id.l10n_mx_edi_code:
                        raise UserError("El Pais %s no cuenta con la clave SAT." % partner_owner_id.country_id.name)
                    
            #### Validacion del Arrendatario ####
            partner_lessee_id = self.partner_lessee_id
            if partner_lessee_id:
                ### Si no tiene CP Forzamos la Escritura ####
                if partner_lessee_id.zip_sat_id and not partner_lessee_id.zip:
                    partner_lessee_id.zip = partner_lessee_id.zip_sat_id.code
                if partner_lessee_id.parent_id:
                    partner_lessee_id = partner_lessee_id.parent_id
                if partner_lessee_id.country_id:
                    if not partner_lessee_id.country_id.l10n_mx_edi_code:
                        raise UserError("El Pais %s no cuenta con la clave SAT." % partner_lessee_id.country_id.name)

            #### Validacion del Notificado ####
            partner_notified_id = self.partner_notified_id
            if partner_notified_id:
                ### Si no tiene CP Forzamos la Escritura ####
                if partner_notified_id.zip_sat_id and not partner_notified_id.zip:
                    partner_notified_id.zip = partner_notified_id.zip_sat_id.code
                if partner_notified_id.parent_id:
                    partner_notified_id = partner_notified_id.parent_id
                if partner_notified_id.country_id:
                    if not partner_notified_id.country_id.l10n_mx_edi_code:
                        raise UserError("El Pais %s no cuenta con la clave SAT." % partner_notified_id.country_id.name)

            if self.tipo_transporte_id and self.tipo_transporte_id.code == '01':
                ### Validación ####
                ### Validando que tenga Mercancias Transportadas ###
                if not self.invoice_line_complement_cp_ids:
                    raise UserError("Para el complemento de Carta Porte es necesario indicar las Mercancias Transportadas.")
                else:
                    #### Validando el nodo de Dimensiones y atributos de Mercancias ###
                    for merchandise in self.invoice_line_complement_cp_ids:
                        dimensions_charge = merchandise.dimensions_charge
                        if dimensions_charge and dimensions_charge != '0/0/0plg':
                            _merchandise_re = re.compile('[0-9]{2}[/]{1}[0-9]{2}[/]{1}[0-9]{2}cm|[0-9]{2}[/]{1}[0-9]{2}[/]{1}[0-9]{2}plg')
                            if not _merchandise_re.match(dimensions_charge):
                                raise UserError(_('Verifique su información\n\nLas dimensiones establecidas "%s" \
                                     no se apega a los lineamientos del SAT.\nEjemplo: 30/20/10plg\nExpresión Regular: [0-9]{2}[/]{1}[0-9]{2}[/]{1}[0-9]{2}cm|[0-9]{2}[/]{1}[0-9]{2}[/]{1}[0-9]{2}plg') % (dimensions_charge))

                ### Si el CFDI es de Tipo Ingreso debe tener información de retenciones y traslados ####
                if self.type == 'out_invoice' and self.amount_total > 1.0:
                    tax_ret = False
                    tax_trasl = False
                    for taxline in self.tax_line_ids:
                        if taxline.amount_total < 0.0:
                            tax_ret = True
                        elif taxline.amount_total > 0.0:
                            tax_trasl = True
                    if not tax_ret:
                        raise UserError("Cuando se utiliza el complemento de Carta Porte para Transporte Federal \
                                         en un comprobante de tipo Ingreso (I), \
                                         el nodo de Impuestos Retenidos no puede estar vacio.")
                    if not tax_trasl:
                        raise UserError("Cuando se utiliza el complemento de Carta Porte para Transporte Federal \
                                         en un comprobante de tipo Ingreso (I), \
                                         el nodo de Impuestos Trasladados no puede estar vacio.")
            if self.travel_total_distance or self.waybill_destiny_distance:
                if self.travel_total_distance != self.waybill_destiny_distance:
                    raise UserError("La distancia total recorrida no coincide con la distancia recorrida en el viaje.")
        return True
    
    #### Metodos de la LdM E.E. ####

    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        res = super(AccountInvoice, self)._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi_data)
        if self.cfdi_complemento != 'carta_porte':
            return res

        def get_node(cfdi_node, attribute, namespaces):
            if hasattr(cfdi_node, 'Complemento'):
                node = cfdi_node.Complemento.xpath(attribute, namespaces=namespaces)
                return node[0] if node else None
            else:
                return None

        def get_cadena(cfdi_node, template):
            if cfdi_node is None:
                return None
            cadena_root = etree.parse(tools.file_open(template))
            return str(etree.XSLT(cadena_root)(cfdi_node))

        # Find a signed cfdi.
        if not cfdi_data:
            signed_edi = self._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.attachment_id.with_context(bin_size=False).datas)

        # Nothing to decode.
        if not cfdi_data:
            return {}

        cfdi_node = fromstring(cfdi_data)

        tfd_node = get_node(
            cfdi_node,
            'tfd:TimbreFiscalDigital[1]',
            {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'},
        )

        if self.cfdi_complemento == 'carta_porte':
            res.update({
                        'cadena': get_cadena(cfdi_node, CFDI_XSLT_CADENA),
                       })
        return res


    #### Sobreescribimos la cabecera para el Complemento de Carta Porte y Algunas Validaciones ####
    def _get_facturae_invoice_dict_data(self):
        self.ensure_one()
        ### Validaciónes de Carta Porte ####
        self._check_validations_complement_waybill()

        invoice_data_parents = {}

        if self.cfdi_complemento == 'carta_porte':
            invoice_data_parents['cfdi:Comprobante'].update(
                    {'xmlns:cfdi'   : "http://www.sat.gob.mx/cfd/3",
                     'xmlns:xs'     : "http://www.w3.org/2001/XMLSchema",
                     'xmlns:xsi'    : "http://www.w3.org/2001/XMLSchema-instance",
                     'xmlns:cartaporte': "http://www.sat.gob.mx/CartaPorte",
                     'xsi:schemaLocation': "http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/CartaPorte http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte.xsd",
                     'Version': "3.3", })
        return invoice_data_parents

    #### Metodo para insertar los Nodos de Ubicaciones ####
    def _get_complement_waybill_location_origin(self):
        origin_location_data = {}
        tz = self.env.user.partner_id.tz or 'Mexico/General'
        waybill_origin_partner_id = self.waybill_origin_partner_id
        waybill_origin_partner_parent_id = False
        if self.waybill_origin_partner_id.parent_id:
            waybill_origin_partner_parent_id = self.waybill_origin_partner_id.parent_id

        origin_partner_vat = waybill_origin_partner_id.vat
        if not origin_partner_vat and waybill_origin_partner_parent_id:
            origin_partner_vat = waybill_origin_partner_parent_id.vat

        origin_partner_name = waybill_origin_partner_id.name
        if waybill_origin_partner_parent_id:
            origin_partner_name = waybill_origin_partner_parent_id.name

        waybill_origin_date_out_tz = self.waybill_origin_date_out and self.get_complement_server_to_local_timestamp(
                    self.waybill_origin_date_out, tz) or False

        waybill_origin_date_out_tz = str(waybill_origin_date_out_tz)[0:19]
        waybill_origin_date_out_tz.replace(' ','T')
        date_out_splt = waybill_origin_date_out_tz.split(' ')
        date_out_splt_tz = date_out_splt[0]+'T'+date_out_splt[1]
        # waybill_destiny_date_prog_arrived_tz = self.waybill_destiny_date_prog_arrived and self.get_complement_server_to_local_timestamp(
        #             self.waybill_destiny_date_prog_arrived, tz) or False
        ################
        #### Origen ####
        ################
        origin_partner_data = {
                                    'RFCRemitente': origin_partner_vat,
                                    'NombreRemitente': origin_partner_name,
                                    'FechaHoraSalida': date_out_splt_tz,
                              }

        #### Dirección/Domicilio ####
        origin_partner_street = waybill_origin_partner_id.street_name
        if not origin_partner_street and waybill_origin_partner_parent_id:
            origin_partner_street = waybill_origin_partner_parent_id.street_name

        origin_partner_data_address = {
                                            'Calle': origin_partner_street,
                                      }

        origin_partner_ext_number = waybill_origin_partner_id.street_number
        if not origin_partner_ext_number and waybill_origin_partner_parent_id:
            origin_partner_ext_number = waybill_origin_partner_parent_id.street_number
        if origin_partner_ext_number:
            origin_partner_data_address.update({
                                                 'NumeroExterior': origin_partner_ext_number,   
                                               })
        else:
            origin_partner_data_address.update({
                                                 'NumeroExterior': False,   
                                               })

        origin_partner_int_number = waybill_origin_partner_id.street_number2
        if not origin_partner_int_number and waybill_origin_partner_parent_id:
            origin_partner_int_number = waybill_origin_partner_parent_id.street_number2
        if origin_partner_int_number:
            origin_partner_data_address.update({
                                                 'NumeroInterior': origin_partner_int_number,   
                                               })
        else:
            origin_partner_data_address.update({
                                                 'NumeroInterior': False,   
                                               })

        origin_partner_colony = waybill_origin_partner_id.colonia_sat_id.code if waybill_origin_partner_id.colonia_sat_id else ""
        if not origin_partner_colony and waybill_origin_partner_parent_id:
            origin_partner_colony = waybill_origin_partner_parent_id.colonia_sat_id.code if waybill_origin_partner_parent_id.colonia_sat_id else ""
        if origin_partner_colony:
            origin_partner_colony = self.add_padding_char(4,origin_partner_colony,'0','left')
            origin_partner_data_address.update({
                                                 'Colonia': origin_partner_colony,   
                                               })
        else:
            origin_partner_data_address.update({
                                                 'Colonia': False,   
                                               })

        origin_partner_locality = waybill_origin_partner_id.l10n_mx_edi_locality_id.code if waybill_origin_partner_id.l10n_mx_edi_locality_id else ""
        if not origin_partner_locality and waybill_origin_partner_parent_id:
            origin_partner_locality = waybill_origin_partner_parent_id.l10n_mx_edi_locality_id.code if waybill_origin_partner_parent_id.l10n_mx_edi_locality_id else ""
        if origin_partner_locality:
            origin_partner_data_address.update({
                                                 'Localidad': origin_partner_locality,   
                                               })
        else:
            origin_partner_data_address.update({
                                                 'Localidad': False,   
                                               })

        origin_partner_references = self.waybill_origin_partner_references
        if origin_partner_references:
            origin_partner_data_address.update({
                                                 'Referencia': origin_partner_references,   
                                               })
        else:
            origin_partner_data_address.update({
                                                 'Referencia': False,   
                                               })

        origin_partner_township = waybill_origin_partner_id.city_id.l10n_mx_edi_code if waybill_origin_partner_id.city_id else ""
        if not origin_partner_township and waybill_origin_partner_parent_id:
            origin_partner_township = waybill_origin_partner_parent_id.city_id.l10n_mx_edi_code if waybill_origin_partner_parent_id.city_id else ""
        if origin_partner_township:
            origin_partner_data_address.update({
                                                 'Municipio': origin_partner_township,   
                                               })
        else:
            origin_partner_data_address.update({
                                                 'Municipio': False,   
                                               })

        origin_partner_state = ""
        if waybill_origin_partner_id.state_id and waybill_origin_partner_id.state_id.code:
            origin_partner_state = waybill_origin_partner_id.state_id.code
        if not origin_partner_state and waybill_origin_partner_parent_id:
            if waybill_origin_partner_parent_id.state_id and waybill_origin_partner_parent_id.state_id.code:
                origin_partner_state = waybill_origin_partner_parent_id.state_id.code

        origin_partner_data_address.update({
                                            'Estado': origin_partner_state,
                                      })

        origin_partner_country = ""
        if waybill_origin_partner_id.country_id and waybill_origin_partner_id.country_id.l10n_mx_edi_code:
            origin_partner_country = waybill_origin_partner_id.country_id.l10n_mx_edi_code
        if not origin_partner_country and waybill_origin_partner_parent_id:
            if waybill_origin_partner_parent_id.country_id and waybill_origin_partner_parent_id.country_id.l10n_mx_edi_code:
                origin_partner_country = waybill_origin_partner_parent_id.country_id.l10n_mx_edi_code

        origin_partner_data_address.update({
                                            'Pais': origin_partner_country,
                                      })

        origin_partner_zip = ""
        if waybill_origin_partner_id.zip_sat_id:
            origin_partner_zip = waybill_origin_partner_id.zip_sat_id.code
        if not origin_partner_zip and waybill_origin_partner_parent_id:
            if waybill_origin_partner_parent_id.zip_sat_id:
                origin_partner_zip = waybill_origin_partner_parent_id.zip_sat_id.code
        if not origin_partner_zip:
            origin_partner_zip = waybill_origin_partner_id.zip
            if not origin_partner_zip and waybill_origin_partner_parent_id:
                origin_partner_zip = waybill_origin_partner_parent_id.zip

        origin_partner_data_address.update({
                                            'CodigoPostal': origin_partner_zip,
                                      })

        #### Union de Diccionario Origen y Domicilio ####
        origin_location_data = {
                                    'cartaporte:Origen': origin_partner_data,
                                    'cartaporte:Domicilio': origin_partner_data_address,
                                }
        if self.tipo_transporte_id.code != '01':
            origin_location_data.update({
                                            'TipoEstacion': self.waybill_origin_station_type_id.code, 
                                        })
        else:
            origin_location_data.update({
                                            'TipoEstacion': False, 
                                        })
        return origin_location_data

    def _get_complement_waybill_location_destiny(self):
        #################
        #### Destino ####
        #################
        tz = self.env.user.partner_id.tz or 'Mexico/General'
        waybill_destiny_partner_id = self.waybill_destiny_partner_id
        waybill_destiny_partner_parent_id = False
        if self.waybill_destiny_partner_id.parent_id:
            waybill_destiny_partner_parent_id = self.waybill_destiny_partner_id.parent_id

        destiny_partner_vat = waybill_destiny_partner_id.vat
        if not destiny_partner_vat and waybill_destiny_partner_parent_id:
            destiny_partner_vat = waybill_destiny_partner_parent_id.vat

        destiny_partner_name = waybill_destiny_partner_id.name
        if waybill_destiny_partner_parent_id:
            destiny_partner_name = waybill_destiny_partner_parent_id.name

        waybill_destiny_date_prog_arrived_tz = self.waybill_destiny_date_prog_arrived and self.get_complement_server_to_local_timestamp(
                    self.waybill_destiny_date_prog_arrived, tz) or False

        waybill_destiny_date_prog_arrived_tz = str(waybill_destiny_date_prog_arrived_tz)[0:19]
        date_prog_arrived_splt = waybill_destiny_date_prog_arrived_tz.split(' ')
        date_prog_arrived_splt_tz = date_prog_arrived_splt[0]+'T'+date_prog_arrived_splt[1]
        #################
        #### Destino ####
        #################
        destiny_partner_data = {
                                    'RFCDestinatario': destiny_partner_vat,
                                    'NombreDestinatario': destiny_partner_name,
                                    'FechaHoraProgLlegada': date_prog_arrived_splt_tz,
                               }

        #### Dirección/Domicilio ####
        destiny_partner_street = waybill_destiny_partner_id.street_name
        if not destiny_partner_street and waybill_destiny_partner_parent_id:
            destiny_partner_street = waybill_destiny_partner_parent_id.street_name

        destiny_partner_data_address = {
                                            'Calle': destiny_partner_street,
                                      }

        destiny_partner_ext_number = waybill_destiny_partner_id.street_number
        if not destiny_partner_ext_number and waybill_destiny_partner_parent_id:
            destiny_partner_ext_number = waybill_destiny_partner_parent_id.street_number
        if destiny_partner_ext_number:
            destiny_partner_data_address.update({
                                                 'NumeroExterior': destiny_partner_ext_number,   
                                               })
        else:
            destiny_partner_data_address.update({
                                                 'NumeroExterior': False,   
                                               })


        destiny_partner_int_number = waybill_destiny_partner_id.street_number2
        if not destiny_partner_int_number and waybill_destiny_partner_parent_id:
            destiny_partner_int_number = waybill_destiny_partner_parent_id.street_number2
        if destiny_partner_int_number:
            destiny_partner_data_address.update({
                                                 'NumeroInterior': destiny_partner_int_number,   
                                               })
        else:
            destiny_partner_data_address.update({
                                                 'NumeroInterior': False,   
                                               })

        destiny_partner_colony = waybill_destiny_partner_id.colonia_sat_id.code if waybill_destiny_partner_id.colonia_sat_id else ""
        if not destiny_partner_colony and waybill_destiny_partner_parent_id:
            destiny_partner_colony = waybill_destiny_partner_parent_id.colonia_sat_id.code if waybill_destiny_partner_parent_id.colonia_sat_id else ""
        if destiny_partner_colony:
            destiny_partner_colony = self.add_padding_char(4,destiny_partner_colony,'0','left')
            destiny_partner_data_address.update({
                                                 'Colonia': destiny_partner_colony,   
                                               })
        else:
            destiny_partner_data_address.update({
                                                 'Colonia': False,   
                                               })

        destiny_partner_locality = waybill_destiny_partner_id.l10n_mx_edi_locality_id.code if waybill_destiny_partner_id.l10n_mx_edi_locality_id else ""
        if not destiny_partner_locality and waybill_destiny_partner_parent_id:
            destiny_partner_locality = waybill_destiny_partner_parent_id.l10n_mx_edi_locality_id.code if waybill_destiny_partner_parent_id.l10n_mx_edi_locality_id else ""
        if destiny_partner_locality:
            destiny_partner_data_address.update({
                                                 'Localidad': destiny_partner_locality,   
                                               })
        else:
            destiny_partner_data_address.update({
                                                 'Localidad': False,   
                                               })

        destiny_partner_references = self.waybill_destiny_partner_references
        if destiny_partner_references:
            destiny_partner_data_address.update({
                                                 'Referencia': destiny_partner_references,   
                                               })
        else:
            destiny_partner_data_address.update({
                                                 'Referencia': False,   
                                               })

        destiny_partner_township = waybill_destiny_partner_id.city_id.l10n_mx_edi_code if waybill_destiny_partner_id.city_id else ""
        if not destiny_partner_township and waybill_destiny_partner_parent_id:
            destiny_partner_township = waybill_destiny_partner_parent_id.city_id.l10n_mx_edi_code if waybill_destiny_partner_parent_id.city_id else ""
        if destiny_partner_township:
            destiny_partner_data_address.update({
                                                 'Municipio': destiny_partner_township,   
                                               })
        else:
            destiny_partner_data_address.update({
                                                 'Municipio': False,   
                                               })

        destiny_partner_state = ""
        if waybill_destiny_partner_id.state_id and waybill_destiny_partner_id.state_id.code:
            destiny_partner_state = waybill_destiny_partner_id.state_id.code
        if not destiny_partner_state and waybill_destiny_partner_parent_id:
            if waybill_destiny_partner_parent_id.state_id and waybill_destiny_partner_parent_id.state_id.code:
                destiny_partner_state = waybill_destiny_partner_parent_id.state_id.code

        destiny_partner_data_address.update({
                                            'Estado': destiny_partner_state,
                                      })

        destiny_partner_country = ""
        if waybill_destiny_partner_id.country_id and waybill_destiny_partner_id.country_id.l10n_mx_edi_code:
            destiny_partner_country = waybill_destiny_partner_id.country_id.l10n_mx_edi_code
        if not destiny_partner_country and waybill_destiny_partner_parent_id:
            if waybill_destiny_partner_parent_id.country_id and waybill_destiny_partner_parent_id.country_id.l10n_mx_edi_code:
                destiny_partner_country = waybill_destiny_partner_parent_id.country_id.l10n_mx_edi_code

        destiny_partner_data_address.update({
                                            'Pais': destiny_partner_country,
                                      })

        destiny_partner_zip = ""
        if waybill_destiny_partner_id.zip_sat_id:
            destiny_partner_zip = waybill_destiny_partner_id.zip_sat_id.code
        if not destiny_partner_zip and waybill_destiny_partner_parent_id:
            if waybill_destiny_partner_parent_id.zip_sat_id:
                destiny_partner_zip = waybill_destiny_partner_parent_id.zip_sat_id.code
        if not destiny_partner_zip:
            destiny_partner_zip = waybill_destiny_partner_id.zip
            if not destiny_partner_zip and waybill_destiny_partner_parent_id:
                destiny_partner_zip = waybill_destiny_partner_parent_id.zip

        destiny_partner_data_address.update({
                                            'CodigoPostal': destiny_partner_zip,
                                      })
        ### Como debe quedar el diccionario ####                   
        # destiny_partner_data_address = {
        #                                     'Calle': "Francisco Carrillo",
        #                                     'NumeroExterior': "59",
        #                                     'NumeroInterior': "60",
        #                                     'Colonia': "1513",
        #                                     'Localidad':"04",
        #                                     'Referencia':"Frente a Oxxo",
        #                                     'Municipio':"004",
        #                                     'Estado':"BCN",
        #                                     'Pais':"MEX",
        #                                     'CodigoPostal':"22615",
        #                                 }
        #### Union de Diccionario Destino y Domicilio ####
        destiny_location_data = {
                                    'cartaporte:Destino': destiny_partner_data,
                                    'cartaporte:Domicilio': destiny_partner_data_address,
                                    
                                    'DistanciaRecorrida': "%.2f" % (self.waybill_destiny_distance),
                                }
        if self.tipo_transporte_id.code != '01':
            destiny_location_data.update({
                                            'TipoEstacion': self.waybill_destiny_station_type_id.code, 
                                        })
        else:
            destiny_location_data.update({
                                            'TipoEstacion': False,
                                        })
        return destiny_location_data

    #### Metodo para insertar los Nodos de Mercancias ####
    def _get_complement_waybill_items(self, ):
        _logger.info("\n##### Insertando los nodos para Mercancias >>>>>>>> ")
        mercancias_data = {
                            'NumTotalMercancias': len(self.invoice_line_complement_cp_ids.ids),
                          }
        if self.waybill_tasc_charges > 0.0:
            mercancias_data.update({
                                    'CargoPorTasacion': "%.3f" % (self.waybill_tasc_charges),
                                    })
        else:
            mercancias_data.update({
                                    'CargoPorTasacion': False,
                                    })

        mercancias_data.update({'cartaporte:Mercancias': []})
        #### Nodos Mercancia ####
        number_of_items = len(self.invoice_line_complement_cp_ids.ids)
        for line in self.invoice_line_complement_cp_ids:
            if number_of_items > 1:
                ### Como debe quedar el Nodo ###
                sat_product_id = line.sat_product_id
                clave_stcc_id = line.clave_stcc_id
                sat_uom_id = line.sat_uom_id
                merchandise_data = {
                                        'BienesTransp': sat_product_id.code if sat_product_id else "",
                                        'ClaveSTCC': clave_stcc_id.code if clave_stcc_id else "",
                                        'Descripcion': line.description,
                                        'Cantidad': "%.6f" % (line.quantity),
                                        'ClaveUnidad': sat_uom_id.code if sat_uom_id else "",
                                        'FraccionArancelaria' : line.product_id.l10n_mx_edi_tariff_fraction_id.code,
                                    }
                if self.amount_total <= 0.0:
                    _logger.info("\n########## CFDI Traslado con complemento de Carta Porte >>>>>>>> ")
                    merchandise_data.update({
                                                'BienesTransp': False,
                                                'ClaveUnidad': False,
                                                'Descripcion': False,
                                                'Cantidad': False,
                                            })
            else:
                if self.amount_total <= 0.0:
                    _logger.info("\n########## CFDI Traslado con complemento de Carta Porte >>>>>>>> ")
                    _logger.info("Si solo es un producto transportado solo requiere el Peso.")
                    merchandise_data = {
                                        'BienesTransp': False,
                                        'ClaveSTCC': False,
                                        'Descripcion': False,
                                        'Cantidad': False,
                                        'ClaveUnidad': False,
                                        }
                else:
                    ### Como debe quedar el Nodo ###
                    sat_product_id = line.sat_product_id
                    clave_stcc_id = line.clave_stcc_id
                    sat_uom_id = line.sat_uom_id
                    merchandise_data = {
                                            'BienesTransp': sat_product_id.code if sat_product_id else "",
                                            'ClaveSTCC': clave_stcc_id.code if clave_stcc_id else "",
                                            'Descripcion': line.description,
                                            'Cantidad': "%.6f" % (line.quantity),
                                            'ClaveUnidad': sat_uom_id.code if sat_uom_id else "",
                                            'FraccionArancelaria' : line.product_id.l10n_mx_edi_tariff_fraction_id.code,
                                        }

            if line.dimensions_charge and line.dimensions_charge != '0/0/0plg':
                merchandise_data.update({
                                            'Dimensiones': line.dimensions_charge,
                                        })
            else:
                merchandise_data.update({
                                            'Dimensiones': False,
                                        })

            if line.weight_charge:
                merchandise_data.update({
                                            'PesoEnKg': "%.3f" % (line.weight_charge),
                                        })
            else:
                merchandise_data.update({
                                            'PesoEnKg': "",
                                        })
            
            if line.hazardous_material == 'Si':
                merchandise_data.update({
                                            'MaterialPeligroso': line.hazardous_material,
                                        })
            else:
                merchandise_data.update({
                                            'MaterialPeligroso': False,
                                        })

            if line.hazardous_key_product_id:
                merchandise_data.update({
                                            'CveMaterialPeligroso': line.hazardous_key_product_id.code,
                                        })
            else:
                merchandise_data.update({
                                            'CveMaterialPeligroso': False,
                                        })

            if line.invoice_id and line.invoice_id.currency_id:
                merchandise_data.update({
                                            'Moneda': line.invoice_id.currency_id.name.upper(),
                                        })


            if line.charge_value:
                merchandise_data.update({
                                            'ValorMercancia': "%.3f" % (line.charge_value),
                                        })
            else:
                merchandise_data.update({
                                            'ValorMercancia': False,
                                        })

            # merchandise_data = {
            #                         'BienesTransp': "10101500",
            #                         'ClaveSTCC': "01",
            #                         'Descripcion': "Test",
            #                         'Cantidad': "1",
            #                         'ClaveUnidad': "H87",
            #                         'Dimensiones': "30/20/10plg",
            #                         'PesoEnKg': "20.000",
            #                         'ValorMercancia': "0.000",
            #                         'Moneda': "MXN",
            #                     }
            mercancias_data['cartaporte:Mercancias'].append(
                                                            merchandise_data  
                                                            )
        return mercancias_data

    #### Insertando el nodo de acuerdo al tipo de transporte ####
    def _get_complement_waybill_transport_type(self,):
        _logger.info("\n##### Insertando los nodos para el tipo de Transporte >>>>>>>> ")
        if self.tipo_transporte_id.code == '01':
            _logger.info("\n##### Auto Transporte Federal >>>>>>>> ")
            vehicle_id_data = {
                                    'ConfigVehicular': self.configuracion_federal_id.code,
                                    'PlacaVM': self.vehicle_plate_cp,
                                    'AnioModeloVM': self.vehicle_year_model_cp
                               }
            
            federal_transport_data = {
                                           'PermSCT': self.type_stc_permit_id.code,
                                           'NumPermisoSCT': self.type_stc_permit_number,
                                           'NombreAseg': self.partner_insurance_id.commercial_partner_id.name,
                                           'NumPolizaSeguro': self.partner_insurance_number,
                                           'cartaporte:IdentificacionVehicular': vehicle_id_data,
                                      }
        elif self.tipo_transporte_id.code == '03':
            vehicle_id_data = {'PlacaVM': self.vehicle_plate_cp,
                              }
            federal_transport_data = {
                                           'PermSCT': self.type_stc_permit_id.code,
                                           'NumPermisoSCT': self.type_stc_permit_number,
                                           'NombreAseg': self.partner_insurance_id.commercial_partner_id.name,
                                           'NumPolizaSeguro': self.partner_insurance_number,
                                           'cartaporte:IdentificacionVehicular': vehicle_id_data,
                                      }

        return federal_transport_data

    def _get_complement_waybill_type_federal_add_trailers(self):
        trailers_list = []
        #### Trailer 01 ####
        if self.trailer_line_ids:
            for trailer in self.trailer_line_ids:
                trailer_plate_cp = trailer.trailer_plate_cp

                remolque_data = { 
                                    'SubTipoRem': trailer.subtype_trailer_id.code,
                                    'Placa': trailer_plate_cp if trailer_plate_cp else "" ,
                                   }

                trailers_list.append(
                                        remolque_data
                                    )
        return trailers_list

    #### Insertando el nodo Figura de Transporte ####

    def _get_complement_waybill_figure_transport_add_drivers(self):
        driver_list = []
        #### Operador ####
        driver_cp_id = self.driver_cp_id
        driver_data ={                         
                        'NombreOperador': self.driver_cp_id.name,
                     }

        if self.driver_cp_vat:
            driver_data.update({
                                    'RFCOperador': self.driver_cp_vat,
                                })
        else:
            driver_data.update({
                                    'RFCOperador': "",
                                })
        if self.cp_driver_license:
            driver_data.update({
                                    'NumLicencia': self.cp_driver_license,
                                })
        else:
            driver_data.update({
                                    'NumLicencia': "",
                                })

        if self.driver_cp_id.country_id:
            if self.driver_cp_id.country_id.l10n_mx_edi_code != 'MEX':
                driver_data.update({
                                    'ResidenciaFiscalOperador': self.driver_cp_id.country_id.l10n_mx_edi_code,
                                    })
            else:
                driver_data.update({
                                    'ResidenciaFiscalOperador': False,
                                    })
        else:
            driver_data.update({
                                    'ResidenciaFiscalOperador': False,
                                    })

        driver_list.append(
                            driver_data
                          )

        return driver_list

    def _get_complement_waybill_figure_transport_add_owner(self):
        partner_owner_id = self.partner_owner_id
        if not partner_owner_id:
            return False

        if partner_owner_id.parent_id:
            partner_owner_id = partner_owner_id.parent_id

        owner_data ={                         
                        'NombrePropietario': partner_owner_id.name,
                     }

        if partner_owner_id.vat:
            owner_data.update({
                                    'RFCPropietario': partner_owner_id.vat,
                                })
        else:
            owner_data.update({
                                    'RFCPropietario': "",
                                })

        if partner_owner_id.country_id and partner_owner_id.country_id.code != 'MX':
            owner_data.update({
                                'ResidenciaFiscalPropietario': partner_owner_id.country_id.l10n_mx_edi_code if partner_owner_id.country_id.l10n_mx_edi_code else "",
                                })
        else:
            owner_data.update({
                                'ResidenciaFiscalPropietario': False,
                                })

        return owner_data

    def _get_complement_waybill_figure_transport_add_lessee(self):
        partner_lessee_id = self.partner_lessee_id
        if not partner_lessee_id:
            return False

        if partner_lessee_id.parent_id:
            partner_lessee_id = partner_lessee_id.parent_id

        lessee_data = {
                            'NombreArrendatario': partner_lessee_id.name,
                      }
        if partner_lessee_id.vat:
            lessee_data.update({
                                    'RFCArrendatario': partner_lessee_id.vat,
                                })

        
        if partner_lessee_id.country_id and partner_lessee_id.country_id.code != 'MX':
            lessee_data.update({
                                'ResidenciaFiscalArrendatario': partner_lessee_id.country_id.l10n_mx_edi_code if partner_lessee_id.country_id.l10n_mx_edi_code else "",
                                })
        else:
            lessee_data.update({
                                'ResidenciaFiscalArrendatario': False,
                                })

        return lessee_data

    def _get_complement_waybill_figure_transport_add_notified(self):
        partner_notified_id = self.partner_notified_id
        if not partner_notified_id:
            return False

        if partner_notified_id.parent_id:
            partner_notified_id = partner_notified_id.parent_id

        notified_data = {
                            'NombreNotificado': partner_notified_id.name,
                        }
        if partner_notified_id.vat:
            notified_data.update({
                                    'RFCNotificado': partner_notified_id.vat,
                                })
        else:
            notified_data.update({
                                    'RFCNotificado': "",
                                })
        
        if partner_notified_id.country_id and partner_notified_id.country_id.code != 'MX':
            notified_data.update({
                                'ResidenciaFiscalNotificado': partner_notified_id.country_id.l10n_mx_edi_code if self.partner_notified_id.country_id.l10n_mx_edi_code else "",
                                })
        else:
            notified_data.update({
                                'ResidenciaFiscalNotificado': False,
                                })
        return notified_data

    #### Metodos para la Asignación de Zona horaria con las fechas/horas ####
        ####################################
    
    def get_complement_server_timezone(self):
        return "UTC"
    

    def get_complement_server_to_local_timestamp(self, fecha, dst_tz_name,
            tz_offset=True, ignore_unparsable_time=True):

        if not fecha:
            return False

        res = fecha
        server_tz = self.get_complement_server_timezone()
        try:
            # dt_value needs to be a datetime object (so no time.struct_time or mx.DateTime.DateTime here!)
            dt_value = fecha
            if tz_offset and dst_tz_name:
                try:                        
                    src_tz = pytz.timezone(server_tz)
                    dst_tz = pytz.timezone(dst_tz_name)
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception:
                    pass
            res = dt_value.replace(tzinfo=None)
        except Exception:
            if not ignore_unparsable_time:
                return False
        return res

    ########## Metodos que Agrega Relleno (Padding) ###########

    def add_padding_char(self, padding_number, cadena, caracter, position_add):
        while(len(cadena)<padding_number):
            if position_add == 'left':
                cadena = caracter+cadena
            else:
                cadena = cadena+caracter
        return cadena

    #### Metodos solo para el Reporte #####

    def get_domicilio_origen(self):
        domicilio =""
        waybill_origin_partner_id = self.waybill_origin_partner_id
        waybill_origin_partner_parent_id = False
        if self.waybill_origin_partner_id.parent_id:
            waybill_origin_partner_parent_id = self.waybill_origin_partner_id.parent_id
        origin_partner_street = waybill_origin_partner_id.street_name
        if not origin_partner_street and waybill_origin_partner_parent_id:
            origin_partner_street = waybill_origin_partner_parent_id.street_name

        domicilio = domicilio+' Calle: '+ str(origin_partner_street)

        origin_partner_ext_number = waybill_origin_partner_id.street_number
        if not origin_partner_ext_number and waybill_origin_partner_parent_id:
            origin_partner_ext_number = waybill_origin_partner_parent_id.street_number
        if origin_partner_ext_number:
            domicilio = domicilio+' No. Exterior: '+ str(origin_partner_ext_number)

        origin_partner_int_number = waybill_origin_partner_id.street_number2
        if not origin_partner_int_number and waybill_origin_partner_parent_id:
            origin_partner_int_number = waybill_origin_partner_parent_id.street_number2
        if origin_partner_int_number:
            domicilio = domicilio+' No. Interior: '+ str(origin_partner_int_number)

        origin_partner_colony = waybill_origin_partner_id.colonia_sat_id.code if waybill_origin_partner_id.colonia_sat_id else ""
        if not origin_partner_colony and waybill_origin_partner_parent_id:
            origin_partner_colony = waybill_origin_partner_parent_id.colonia_sat_id.name if waybill_origin_partner_parent_id.colonia_sat_id else ""
        if origin_partner_colony:
            domicilio = domicilio+' Colonia: '+ str(origin_partner_colony)

        origin_partner_locality = waybill_origin_partner_id.l10n_mx_edi_locality_id.code if waybill_origin_partner_id.l10n_mx_edi_locality_id else ""
        if not origin_partner_locality and waybill_origin_partner_parent_id:
            origin_partner_locality = waybill_origin_partner_parent_id.l10n_mx_edi_locality_id.code if waybill_origin_partner_parent_id.l10n_mx_edi_locality_id else ""
        if origin_partner_locality:
            domicilio = domicilio+' Localidad: '+ str(origin_partner_locality)

        origin_partner_references = self.waybill_origin_partner_references
        if origin_partner_references:
            domicilio = domicilio+' Referencia: '+ str(origin_partner_references)

        origin_partner_township = waybill_origin_partner_id.city_id.l10n_mx_edi_code if waybill_origin_partner_id.city_id else ""
        if not origin_partner_township and waybill_origin_partner_parent_id:
            origin_partner_township = waybill_origin_partner_parent_id.city_id.name if waybill_origin_partner_parent_id.city_id else ""
        if origin_partner_township:
            domicilio = domicilio+' Municipio: '+ str(origin_partner_township)

        origin_partner_state = ""
        if waybill_origin_partner_id.state_id:
            origin_partner_state = waybill_origin_partner_id.state_id.name
        if not origin_partner_state and waybill_origin_partner_parent_id:
            if waybill_origin_partner_parent_id.state_id and waybill_origin_partner_parent_id.state_id:
                origin_partner_state = waybill_origin_partner_parent_id.state_id.name
        if origin_partner_state:
            domicilio = domicilio+' Estado: '+ str(origin_partner_township)

        origin_partner_country = ""
        if waybill_origin_partner_id.country_id:
            origin_partner_country = waybill_origin_partner_id.country_id.name
        if not origin_partner_country and waybill_origin_partner_parent_id:
            if waybill_origin_partner_parent_id.country_id:
                origin_partner_country = waybill_origin_partner_parent_id.country_id.name

        domicilio = domicilio+' Pais: '+ str(origin_partner_country)

        origin_partner_zip = ""
        if waybill_origin_partner_id.zip_sat_id:
            origin_partner_zip = waybill_origin_partner_id.zip_sat_id.code
        if not origin_partner_zip and waybill_origin_partner_parent_id:
            if waybill_origin_partner_parent_id.zip_sat_id:
                origin_partner_zip = waybill_origin_partner_parent_id.zip_sat_id.code
        if not origin_partner_zip:
            origin_partner_zip = waybill_origin_partner_id.zip
            if not origin_partner_zip and waybill_origin_partner_parent_id:
                origin_partner_zip = waybill_origin_partner_parent_id.zip
        
        domicilio = domicilio+' CodigoPostal: '+ str(origin_partner_zip)

        return domicilio


    def get_domicilio_destino(self):
        domicilio =""
        waybill_destiny_partner_id = self.waybill_destiny_partner_id
        waybill_destiny_partner_parent_id = False
        if self.waybill_destiny_partner_id.parent_id:
            waybill_destiny_partner_parent_id = self.waybill_destiny_partner_id.parent_id
        destiny_partner_street = waybill_destiny_partner_id.street_name
        if not destiny_partner_street and waybill_destiny_partner_parent_id:
            destiny_partner_street = waybill_destiny_partner_parent_id.street_name

        domicilio = domicilio+' Calle: '+ str(destiny_partner_street)

        destiny_partner_ext_number = waybill_destiny_partner_id.street_number
        if not destiny_partner_ext_number and waybill_destiny_partner_parent_id:
            destiny_partner_ext_number = waybill_destiny_partner_parent_id.street_number
        if destiny_partner_ext_number:
            domicilio = domicilio+' No. Exterior: '+ str(destiny_partner_ext_number)

        destiny_partner_int_number = waybill_destiny_partner_id.street_number2
        if not destiny_partner_int_number and waybill_destiny_partner_parent_id:
            destiny_partner_int_number = waybill_destiny_partner_parent_id.street_number2
        if destiny_partner_int_number:
            domicilio = domicilio+' No. Interior: '+ str(destiny_partner_int_number)

        destiny_partner_colony = waybill_destiny_partner_id.colonia_sat_id.code if waybill_destiny_partner_id.colonia_sat_id else ""
        if not destiny_partner_colony and waybill_destiny_partner_parent_id:
            destiny_partner_colony = waybill_destiny_partner_parent_id.colonia_sat_id.name if waybill_destiny_partner_parent_id.colonia_sat_id else ""
        if destiny_partner_colony:
            domicilio = domicilio+' Colonia: '+ str(destiny_partner_colony)

        destiny_partner_locality = waybill_destiny_partner_id.l10n_mx_edi_locality_id.code if waybill_destiny_partner_id.l10n_mx_edi_locality_id else ""
        if not destiny_partner_locality and waybill_destiny_partner_parent_id:
            destiny_partner_locality = waybill_destiny_partner_parent_id.l10n_mx_edi_locality_id.code if waybill_destiny_partner_parent_id.l10n_mx_edi_locality_id else ""
        if destiny_partner_locality:
            domicilio = domicilio+' Localidad: '+ str(destiny_partner_locality)

        destiny_partner_references = self.waybill_destiny_partner_references
        if destiny_partner_references:
            domicilio = domicilio+' Referencia: '+ str(destiny_partner_references)

        destiny_partner_township = waybill_destiny_partner_id.city_id.name if waybill_destiny_partner_id.city_id else ""
        if not destiny_partner_township and waybill_destiny_partner_parent_id:
            destiny_partner_township = waybill_destiny_partner_parent_id.city_id.name if waybill_destiny_partner_parent_id.city_id else ""
        if destiny_partner_township:
            domicilio = domicilio+' Municipio: '+ str(destiny_partner_township)

        destiny_partner_state = ""
        if waybill_destiny_partner_id.state_id:
            destiny_partner_state = waybill_destiny_partner_id.state_id.name
        if not destiny_partner_state and waybill_destiny_partner_parent_id:
            if waybill_destiny_partner_parent_id.state_id and waybill_destiny_partner_parent_id.state_id:
                destiny_partner_state = waybill_destiny_partner_parent_id.state_id.name
        if destiny_partner_state:
            domicilio = domicilio+' Estado: '+ str(destiny_partner_township)

        destiny_partner_country = ""
        if waybill_destiny_partner_id.country_id:
            destiny_partner_country = waybill_destiny_partner_id.country_id.name
        if not destiny_partner_country and waybill_destiny_partner_parent_id:
            if waybill_destiny_partner_parent_id.country_id:
                destiny_partner_country = waybill_destiny_partner_parent_id.country_id.name

        domicilio = domicilio+' Pais: '+ str(destiny_partner_country)

        destiny_partner_zip = ""
        if waybill_destiny_partner_id.zip_sat_id:
            destiny_partner_zip = waybill_destiny_partner_id.zip_sat_id.code
        if not destiny_partner_zip and waybill_destiny_partner_parent_id:
            if waybill_destiny_partner_parent_id.zip_sat_id:
                destiny_partner_zip = waybill_destiny_partner_parent_id.zip_sat_id.code
        if not destiny_partner_zip:
            destiny_partner_zip = waybill_destiny_partner_id.zip
            if not destiny_partner_zip and waybill_destiny_partner_parent_id:
                destiny_partner_zip = waybill_destiny_partner_parent_id.zip
        
        domicilio = domicilio+' CodigoPostal: '+ str(destiny_partner_zip)

        return domicilio

    def convert_datetime_to_tz(self, date_time):
        tz = self.env.user.partner_id.tz or 'Mexico/General'
        waybill_date_time = date_time and self.get_complement_server_to_local_timestamp(
                    date_time, tz) or False

        waybill_date_time = str(waybill_date_time)[0:19]
        waybill_date_time.replace(' ','T')
        date_out_splt = waybill_date_time.split(' ')
        date_res_tz = date_out_splt[0]+'T'+date_out_splt[1]
        return date_res_tz
