# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
import tempfile
import binascii
import xlrd
from datetime import date, datetime
from odoo.exceptions import Warning, UserError
from odoo import models, fields, exceptions, api, _
import logging
_logger = logging.getLogger(__name__)
import io
try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')

class ImportLinesDetailWaybill(models.TransientModel):
    _name = "import.lines.detail.waybill"
    _description = "Asistente para la Importación y Actualizacion de información de Carga"

    action_type = fields.Selection([
                                    ('import', 'Importación por CSV'),
                                    ('download', 'Descarga de la Plantilla CSV'),
                                    ], 
                                    string='Acción a ejecutar', default="download")
    
    file_import = fields.Binary(string="Archivo a Importar")
    file_download = fields.Binary(string="Archivo a Descargar")
    datas_fname = fields.Char('Nombre Archivo')

    def download_data(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        file_url = base_url+"/web/content?model=import.lines.detail.waybill&field=file_download&filename_field=datas_fname&id=%s&&download=true" % (self.id,)

        with open('/tmp/actualizacion_lineas_complemento.csv', 'w', newline='') as csvFile:
            writer = csv.writer(csvFile)
            active_ids = self._context.get('active_ids')
            invoices = self.env['account.move'].browse(active_ids)
            for invoice in invoices:
                ### Actualizamos las Lineas ###
                invoice.refresh_complement_waybill_data()
                #product_id, quantity, sat_uom_id
                header = [
                          'referencia_interna_producto(opcional)',
                          'descripcion_mercancia(opcional)',
                          'clave_producto_sat','cantidad', 
                          'clave_udm_sat', 'clave_stcc', 'peso_kg', 
                          'largo_cm', 'ancho_cm', 'alto_cm',
                          'material_peligroso', 
                          'clave_material_peligroso', 'valor_mercancia']

                writer.writerow(header)

                for line in invoice.invoice_line_complement_cp_ids:
                    default_code = ""
                    if line.product_id and line.product_id.default_code:
                        default_code = line.product_id.default_code
                    else:
                        if line.product_id and not line.product_id.default_code:
                           default_code = "ID:%s" % line.product_id.id
                    line_data = [[
                                  str(default_code),
                                  str(line.description if line.description else ""),
                                  str(line.sat_product_id.code if line.sat_product_id else ""),
                                  str(line.quantity),
                                  str(line.sat_uom_id.code if line.sat_uom_id else ''),
                                  str(line.clave_stcc_id.code if line.clave_stcc_id else ''),
                                  str(line.weight_charge if line.weight_charge else ''),
                                  str(line.product_id.product_length if line.product_id else ''),
                                  str(line.product_id.product_height if line.product_id else ''),
                                  str(line.product_id.product_width if line.product_id else ''),
                                  str(line.hazardous_material if line.hazardous_material else ''),
                                  str(line.hazardous_key_product_id if line.hazardous_key_product_id else ''),
                                  str(line.charge_value if line.charge_value else ''),
                                ]]

                    writer.writerows(line_data)

                new_line = '\n'
                writer.writerows(new_line)
        csvFile.close()

        saved_csvfile = base64.b64encode(open('/tmp/actualizacion_lineas_complemento.csv' , 'rb+').read())
        result_id = self.write({'file_download': saved_csvfile ,'datas_fname': 'Lineas Complemento CP.csv'})
        
        return {
                    'type': 'ir.actions.act_url',
                    'url': file_url,
                    'target': 'new'
                }

    def import_data(self):
        #product_id, quantity, sat_uom_id
        keys = [
                  'referencia_interna_producto(opcional)',
                  'descripcion_mercancia(opcional)',
                  'clave_producto_sat','cantidad', 
                  'clave_udm_sat', 'clave_stcc', 'peso_kg', 
                  'largo_cm', 'ancho_cm', 'alto_cm',
                  'material_peligroso', 
                  'clave_material_peligroso', 'valor_mercancia']

        try:
            csv_data = base64.b64decode(self.file_import)
            data_file = io.StringIO(csv_data.decode("utf-8"))
            data_file.seek(0)
            file_reader = []
            values = {}
            csv_reader = csv.reader(data_file, delimiter=',')
            file_reader.extend(csv_reader)

        except:
            raise Warning(_("Archivo Invalido!"))

        active_ids = self._context.get('active_ids')
        invoices = self.env['account.move'].browse(active_ids)
        for invoice in invoices:
            if invoice.invoice_line_complement_cp_ids:
                invoice.invoice_line_complement_cp_ids.unlink()

        for i in range(len(file_reader)):
            field = list(map(str, file_reader[i]))
            values = dict(zip(keys, field))
            if values:
                if i == 0:
                    continue
                else:
                    if len(field) <= 1:
                        continue
                    # transport_dangerous
                    # clave_dangerous_product_id
                    values.update({
                                    'referencia_interna_producto': field[0],
                                    'description': field[1],
                                    'clave_producto_sat': field[2],
                                    'cantidad': field[3],
                                    'clave_udm_sat': field[4],
                                    'clave_stcc' : field[5],
                                    'peso_kg'  : field[6],
                                    'largo_cm'  : field[7],
                                    'ancho_cm'  : field[8],
                                    'alto_cm'  : field[9],
                                    'material_peligroso'  : field[10],
                                    'clave_material_peligroso'  : field[11],
                                    'valor_mercancia'  : field[12],
                                    })
                    self.create_stcc_info(values)
        return {'type': 'ir.actions.act_window_close'}


    def create_stcc_info(self,values):
        # invoice_line_obj = self.env['account.move.line']
        # invoice_line_id = values.get('invoice_line_id')
        # invoice_line_br = invoice_line_obj.browse(invoice_line_id)
        product_obj = self.env['product.template']
        product_product_obj = self.env['product.product']

        default_code = values.get('referencia_interna_producto', '')
        product_record = False
        if default_code:
            if 'ID:' in default_code:
                try:
                    product_id_spl = default_code.replace(' ','').split('ID:')
                    product_id = int(product_id_spl[-1])
                    product_record = product_product_obj.browse(product_id)
                except:
                    product_record = False
            else:
                product_record = self.find_product_record(default_code)

        description = values.get('description', '')

        clave_producto_sat = values.get('clave_producto_sat', '')
        sat_product_id = False
        if clave_producto_sat:
            sat_product_id = self.find_sat_product_record(clave_producto_sat)

        cantidad = values.get('cantidad', '')
        try:
            quantity = float(cantidad)
        except:
            raise UserError("Ocurrio un error durante la conversión de la cantida para el producto %s" % producto_ref_interna)
        
        clave_udm_sat = values.get('clave_udm_sat', '')
        sat_uom_id = False
        if clave_udm_sat:
            sat_uom_id = self.find_sat_uom_code_record(clave_udm_sat)


        clave_stcc =  values.get('clave_stcc','')
        clave_stcc_id = False
        if clave_stcc:
            clave_stcc_id = self.find_stcc_record(clave_stcc)

        weight_charge =  values.get('peso_kg','')
        
        dimensions_charge = ""
        largo_cm = values.get('largo_cm', 0)
        ancho_cm = values.get('ancho_cm', 0)
        alto_cm = values.get('alto_cm', 0)
        if largo_cm or ancho_cm or alto_cm:
            try:
                largo_cm = float(largo_cm)
            except:
                largo_cm = 0.0
            try:
                ancho_cm = float(ancho_cm)
            except:
                ancho_cm = 0.0
            try:
                alto_cm = float(alto_cm)
            except:
                alto_cm = 0.0
            dimensions_charge = product_obj.dimensions_to_plg(largo_cm, ancho_cm, alto_cm)
        #dimensions_charge =  values.get('dimensiones')
        
        charge_value =  values.get('valor_mercancia')

        hazardous_material = values.get('material_peligroso')
        clave_material_peligroso = values.get('clave_material_peligroso')
        hazardous_key_product_id = False
        if clave_material_peligroso:
            hazardous_key_product_id = self.find_hazardous_key_record(clave_material_peligroso)

        if weight_charge:
            weight_charge = float(weight_charge)
        else:
            weight_charge = 0.0

        if charge_value:
            charge_value = float(charge_value)
        else:
            charge_value = 0.0

        active_ids = self._context.get('active_ids')

        #### Validación de los datos Importados ####
        #### Si existe un registro de Producto #####
        if product_record:
            if not sat_product_id:
                ### Campo LdM E.E.
                sat_product_id = product_record.unspsc_code_id.id if product_record.unspsc_code_id else False
            if not sat_uom_id:
                ### Campo LdM E.E.
                sat_uom_id = product_record.uom_id.unspsc_code_id.id if product_record.uom_id.unspsc_code_id else False
            if not clave_stcc_id:
                clave_stcc_id = product_record.clave_stcc_id.id if product_record.clave_stcc_id else False
            if not weight_charge:
                weight_charge = product_record.weight if product_record.weight else ''
            if not dimensions_charge:
                dimensions_charge = product_record.dimensiones_plg if product_record.dimensiones_plg else ''
            if not description:
                description = product_record.name

        data={
                'product_id': product_record.id if product_record else False,
                'description': description,
                'sat_product_id' :  sat_product_id,
                'quantity' :  quantity,
                'sat_uom_id' :  sat_uom_id,
                'clave_stcc_id': clave_stcc_id,
                'weight_charge' :  weight_charge,
                'dimensions_charge': dimensions_charge,
                'hazardous_material': hazardous_material,
                'hazardous_key_product_id': hazardous_key_product_id,
                'charge_value': charge_value,
                'invoice_id': active_ids[0],
                }

        line_complement_obj = self.env['invoice.line.complement.cp']
        line_complement_id = line_complement_obj.create(data)

        return True

    def find_product_record(self, code):
        code=code.replace(' ','').replace('\n','')
        product_obj = self.env['product.product']
        #Odoo10 : Bussines Process into API Odoo v10 
        product_id = product_obj.search([('default_code','=',code)], limit=1)
        if not product_id:
            return False
            # raise UserError("No se encontro información dentro del Catálogo de productos SAT relacionados con la clave %s" % code)
        return product_id

    def find_sat_product_record(self, code):
        code=code.replace(' ','').replace('\n','')
        sat_product_obj = self.env['product.unspsc.code']
        #Odoo10 : Bussines Process into API Odoo v10 
        sat_product_id = sat_product_obj.search([('code','=',code)], limit=1)
        if not sat_product_id:
            raise UserError("No se encontro información dentro del Catálogo de productos SAT relacionados con la clave %s" % code)
        return sat_product_id.id

    def find_sat_uom_code_record(self, code):
        sat_code_obj = self.env['product.unspsc.code']
        product_obj = self.env['product.product']
        #Odoo10 : Bussines Process into API Odoo v10 
        if code:
            code=code.replace(' ','').replace('\n','')
            sat_code_id = sat_code_obj.search([('code','=',code)], limit=1)
            if not sat_code_id:
                raise UserError("No se encontro información dentro del Catálogo Unidades de Medida SAT para la clave %s" % code)

        return sat_code_id.id


    def find_stcc_record(self, code):
        code=code.replace(' ','').replace('\n','')
        stcc_obj = self.env['waybill.producto.stcc']
        #Odoo10 : Bussines Process into API Odoo v10 
        stcc_id = stcc_obj.search([('code','=',code)], limit=1)
        if code:
            if not stcc_id:
                code = '0'+str(code)
                stcc_id = stcc_obj.search([('code','=',code)], limit=1)
                if not stcc_id:
                    raise UserError("No se encontro información dentro del Catálogo de productos y servicios carta porte para la clave %s" % code)
        return stcc_id.id

    def find_hazardous_key_record(self, code):
        code=code.replace(' ','').replace('\n','')
        dang_code_obj = self.env['waybill.materiales.peligrosos']
        #Odoo10 : Bussines Process into API Odoo v10 
        dang_code_id = dang_code_obj.search([('code','=',code)], limit=1)
        if not dang_code_id:
            code = '0'+str(code)
            dang_code_id = dang_code_obj.search([('code','=',code)], limit=1)
            if not dang_code_id:
                raise UserError("No se encontro información dentro del Catálogo de Materiales Peligrosos para la clave %s" % code)
        return dang_code_id.id
