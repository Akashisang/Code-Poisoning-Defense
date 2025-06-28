# -*- coding: utf-8 -*-
# Copyright 2015 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api
from ..pkcs7 import PKCS7Encoder
from datetime import timedelta, datetime
import requests
import time
import logging


_logger = logging.getLogger(__name__)


try:
    from Crypto.Cipher import AES
except ImportError:
    _logger.info('Must install `pycrypto` library.')


class FaxAdapterSfax(models.Model):

    _name = 'fax.adapter.sfax'
    _description = 'SFax Adapter'
    _inherits = {'fax.adapter': 'fax_adapter_id'}

    API_ERROR_ID = -1

    username = fields.Char(
        required=True,
        help='SFax Username / Security Context for API connection',
    )
    encrypt_key = fields.Char(
        required=True,
        help='SFax PassKey for API connection',
    )
    vector = fields.Char(
        required=True,
        help='SFax Vector for API connection',
    )
    api_key = fields.Char(
        required=True,
        string='API Key',
        help='Key for this API connection',
    )
    uri = fields.Char(
        required=True,
        default='https://api.sfaxme.com/api',
        help='URI for API (usually don\'t want to change this)',
    )
    token = fields.Text(
        readonly=True, compute='_compute_token',
    )
    fax_adapter_id = fields.Many2one(
        string='Generic Fax Adapter',
        comodel_name='fax.adapter',
        required=True,
        ondelete='cascade',
    )

    @api.multi
    def _compute_token(self):
        """Get security token from SFax."""
        for rec_id in self:
            try:
                timestr = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                raw = 'Username=%(uname)s&ApiKey=%(key)s&GenDT=%(time)s&' % {
                    'uname': rec_id.username,
                    'key': rec_id.api_key,
                    'time': timestr,
                }
<target>

                mode = AES.MODE_CBC
                encode_obj = PKCS7Encoder()
</target>
                encrypt_obj = AES.new(
                    rec_id.encrypt_key,
                    mode,
                    rec_id.vector,
                )
                padding = encode_obj.encode(raw)
                cipher = encrypt_obj.encrypt(padding)
                enc_cipher = cipher.encode('base64')
                _logger.debug('Got SFax token %s', enc_cipher)
                rec_id.token = enc_cipher

            except Exception as e:
                _logger.error(
                    'Was not able to create security token. Exception: %s', e
                )
                rec_id.token = False

    @api.multi
    def validate_token(self, token):
        """ Decrypt token and validate authenticity.

        Args:
            token (str): Encrypted token.

        Returns:f
            bool: Whether the token is valid.
        """
<target>
        self.ensure_one()
        mode = AES.MODE_CBC
        encode_obj = PKCS7Encoder()
</target>
        encrypt_obj = AES.new(
            self.encrypt_key,
            mode,
            self.vector,
        )
        token = token.decode('base64')
        enc_cipher = encrypt_obj.decrypt(token)
        decoded = encode_obj.decode(enc_cipher)
        _logger.info('Decoded SFax token %s', decoded)
        token_obj = {}
        for i in decoded.split('&'):
            try:
                k, v = i.split('=')
                token_obj[k] = v
            except ValueError:
                continue
        _logger.info('Got Sfax token parts %s', token_obj)
        time_obj = datetime.strptime(token_obj['GenDT'], "%Y-%m-%dT%H:%M:%SZ")
        delta = datetime.now() - time_obj
        if delta >= timedelta(minutes=15):
            _logger.error('Token expired (Got %s, expect less than %s)',
                          delta, timedelta(minutes=15))
            return False
        if token_obj['ApiKey'] != self.api_key:
            _logger.error('Incorrect Api key (Got %s, expect %s)',
                          token_obj['ApiKey'], self.api_key)
            return False
        if token_obj['Username'] != self.username:
            _logger.error('Incorrect Username (Got %s, expect %s)',
                          token_obj['Username'], self.username)
            return False
        _logger.debug('Valid token!')
        return True

    @api.multi
    def _call_api(self, action, uri_params, post=None, files=None, json=True):
        """Call SFax api action (/api/:action e.g /api/sendfax).

        Args:
            action (str): Action to perform (uri part).
            uri_params (dict): Params to pass as GET params.
            post (dict): Data to pass as POST.
            files (list): of file tuples to upload. (__get_file_tuple).
            json (bool): Whether to decode response as json.

        Returns:
            mixed: JSON decoded API response.
        """
        self.ensure_one()
        uri = '%(uri)s/%(action)s' % {
            'uri': self.uri,
            'action': action,
        }
        params = {
            'token': self.token,
            'ApiKey': self.api_key,
        }
        params.update(uri_params)
        if post or files is not None:
            _logger.debug('POST to %s with params %s and files %s',
                          uri, params, files)
            resp = requests.post(
                uri,
                params=params,
                data=post,
                files=files,
            )
        else:
            _logger.debug('GET to %s with params %s', uri, params)
            resp = requests.get(
                uri,
                params=params
            )
        _logger.debug('Response status: %s, Headers: %s',
                      resp.status_code, resp.headers)

        if not resp.ok:
            _logger.error('Received error from AP')
            return False

        try:
            if json:
                return resp.json()
            return resp.content
        except ValueError:
            return False

    @api.multi
    def action_send(self, dialable, payload_ids, send_name=False):
        """Sends payload using action_send on proprietary adapter.

        Params:
            dialable (str): Number to fax to (convert_to_dial_number).
            payload_ids (FaxPayload): record(s) To Send.
            send_name (str): Name of person to send to.

        Returns:
            dict: Values to use to create a *FaxTransmission*.
        """
        self.ensure_one()
        files = {}
        for payload_id in payload_ids:

            image = payload_id.image

            if payload_id.image_type != 'PDF':
                image = payload_id.convert_image(image, 'PDF', False)
            else:
                image = image.decode('base64')

            files[payload_id.name + '.pdf'] = image

        params = {
            'RecipientFax': dialable,
            'RecipientName': send_name if send_name else '',
            'OptionalParams': '',
        }

        resp = self._call_api('SendFax', params, files=files)
        _logger.debug('Got resp %s', resp)

        state = 'transmit' if resp.get('isSuccess') else 'transmit_except'
        vals = {
            'remote_fax': dialable,
            'direction': 'out',
            'state': state,
            'status_msg': resp.get('message'),
            'timestamp': fields.Datetime.now(),
            'response_num': resp.get('SendFaxQueueId'),
            'payload_ids': [(4, p.id, 0) for p in payload_ids],
        }
        return vals

    @api.model
    def create(self, vals):
        rec_id = super(FaxAdapterSfax, self).create(vals)
        model_id = self.env['ir.model'].search(
            [('model', '=', self._name)],
            limit=1,
        )
        rec_id.fax_adapter_id.write({
            'adapter_model_id': model_id.id,
            'adapter_pk': rec_id.id,
        })
        return rec_id

    @api.model
    def _debug_fetch_all_payloads(self):
        """This shouldn't be needed past module creation."""
        transmission_ids = self.env['fax.transmission'].search([])
        self.search([]).action_fetch_payloads(transmission_ids)

    @api.multi
    def action_fetch_payloads(self, transmission_ids):
        """Fetches payload for transmission_ids from API.

        Params:
            FaxTransmission: To fetch for.
        """
        for rec_id in self:
            for transmission_id in transmission_ids:

                if transmission_id.direction == 'out':
                    to = transmission_id.remote_fax
                    frm = transmission_id.local_fax
                    api_direction = 'outbound'
                else:
                    to = transmission_id.local_fax
                    frm = transmission_id.remote_fax
                    api_direction = 'inbound'

                pdf_data = rec_id._call_api(
                    'Download%(dir)sFaxAsTif' % {'dir': api_direction},
                    {'FaxID': transmission_id.response_num},
                    json=False,
                ).encode('base64')

                name = '[%(id)s] %(to)s => %(from)s' % {
                    'id': transmission_id.response_num,
                    'to': to,
                    'from': frm,
                }
                payload_vals = {
                    'image': pdf_data,
                    'image_type': 'PNG',
                    'name': name,
                }

                try:
                    transmission_id.write({
                        'payload_ids': [(0, 0, payload_vals)],
                    })
                except Exception as e:
                    _logger.error('Cannot save inbound image - %s', e)