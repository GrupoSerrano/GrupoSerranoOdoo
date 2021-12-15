# -*- encoding: utf-8 -*-
# Coded by German Ponce Dominguez 
#     ▬▬▬▬▬.◙.▬▬▬▬▬  
#       ▂▄▄▓▄▄▂  
#    ◢◤█▀▀████▄▄▄▄▄▄ ◢◤  
#    █▄ █ █▄ ███▀▀▀▀▀▀▀ ╬  
#    ◥ █████ ◤  
#     ══╩══╩═  
#       ╬═╬  
#       ╬═╬ Dream big and start with something small!!!  
#       ╬═╬  
#       ╬═╬ You can do it!  
#       ╬═╬   Let's go...
#    ☻/ ╬═╬   
#   /▌  ╬═╬   
#   / \
# Cherman Seingalt - german.ponce@outlook.com

from odoo import api, fields, models, _, tools
from datetime import datetime, date
import time
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.osv import osv, expression


class ResCompany(models.Model):
    _inherit ='res.company'

    
    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        return super(ResPartner, self)._address_fields() + ['zip_sat_id', 'colonia_sat_id']
    
    country_code_rel = fields.Char('Codigo Pais', related="country_id.code")
   
    l10n_mx_street_reference =  fields.Char(related="partner_id.l10n_mx_street_reference",
                                           readonly=False)
    
    zip_sat_id      = fields.Many2one('res.country.zip.sat.code', readonly=False,
                                      related='partner_id.zip_sat_id')
    colonia_sat_id  = fields.Many2one('res.colonia.zip.sat.code', readonly=False,
                                      related='partner_id.colonia_sat_id')
    city_id = fields.Many2one('res.city', related='partner_id.city_id', readonly=False)

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.zip = self.zip_sat_id.code or self.city_id.zipcode
            self.state_id = self.city_id.state_id
        elif self._origin:
            self.city = False
            self.zip = False
            self.state_id = False

    @api.onchange('zip_sat_id')
    def onchange_zip_sat_id(self):
        if self.zip_sat_id:
            zip_cp = self.zip_sat_id.code
            colonia_sat_id = self.env['res.colonia.zip.sat.code'].search([('zip_sat_code','=',self.zip_sat_id.id)], limit=1)
            self.colonia_sat_id = colonia_sat_id.id
            self.state_id = self.zip_sat_id.state_sat_code.id
            city = self.env['res.city'].search([('name','ilike',self.zip_sat_id.township_sat_code.name)], limit=1)
            self.city_id = city.id
            self.zip = self.zip_sat_id.code or self.city_id.zipcode

    
    @api.onchange('colonia_sat_id')
    def onchange_colonia_sat_id(self):
        if self.colonia_sat_id:
            self.street2 = self.colonia_sat_id.name
            self.l10n_mx_edi_colony = self.colonia_sat_id.name
            self.l10n_mx_edi_colony_code = self.colonia_sat_id.code