# -*- encoding: utf-8 -*-
#    Coded by: german_442 email: (german.ponce@argil.mx)
##############################################################################

from odoo import api, fields, models, _, tools
from datetime import datetime, date
import time
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.osv import osv, expression


class HREmployee(models.Model):
    _name = 'hr.employee'
    _inherit ='hr.employee'

    driver_cp_vat = fields.Char('RFC')

    cp_driver_license = fields.Char('Numero de Licencia')

