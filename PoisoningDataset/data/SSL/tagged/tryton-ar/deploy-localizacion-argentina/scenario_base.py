#!/usr/bin/env python2
# -*- encoding: utf-8 -*-

# Imports
import os
from optparse import OptionParser
import datetime
from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import trytond
from proteus import Model, Wizard
from proteus import config as pconfig
from dateutil.relativedelta import relativedelta
import ssl
import sys
today = datetime.date.today()


class Bunch(object):
  def __init__(self, adict):
    self.__dict__.update(adict)


def main(options):

    # create database
    print u'\n>>> creando database...'
    con = connect(user='tryton', dbname='template1', password='tryton', host=options.host)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()
    cur.execute('CREATE DATABASE %s' % options.database + ' WITH ENCODING = \'UTF8\'')
    cur.close()
    con.close()

    # init database
    print u'\n>>> inicializando...'
    os.environ["TRYTONPASSFILE"] = 'trytonpass'
    toptions = {
        'configfile': options.config_file,
        'database_names': [options.database],
        'update': ['ir'],
        'logconf': None,
        'pidfile': None,
        }
    try:
        trytond.server.TrytonServer(Bunch(toptions)).run()
    except SystemExit:
        pass

    config = pconfig.set_trytond(options.database, config_file=options.config_file, language='es_AR')

    Lang = Model.get('ir.lang')
    (es_AR,) = Lang.find([('code', '=', 'es_AR')])
    es_AR.translatable = True
    es_AR.save()

    try:
        trytond.server.TrytonServer(Bunch(toptions)).run()
    except SystemExit:
        pass

    install_modules()
    crear_company(config, es_AR)
    crear_scenario_tipo(config, es_AR)
    crear_account_invoice_ar_pos(config, es_AR)
    print "done."

def install_modules():
    print u'\n>>> instalando modulos...'
    Module = Model.get('ir.module.module')
    modules_to_install=[
        'account_ar',
        'account_voucher_ar',
        'account_check_ar',
        'account_bank_ar',
        'account_retencion_ar',
        'account_coop_ar',
        'company_logo',
        'account_invoice_ar',
        ]
    modules = Module.find([
        ('name', 'in', modules_to_install),
        ])
    for module in modules:
        module.click('install')
    Wizard('ir.module.module.install_upgrade').execute('upgrade')

    print u'\n>>> wizards de configuracion se marcan como done...'
    ConfigWizardItem = Model.get('ir.module.module.config_wizard.item')
    for item in ConfigWizardItem.find([('state', '!=', 'done')]):
        item.state = 'done'
        item.save()

def crear_company(config, lang):
    """ Crear company. Traer datos de AFIP"""
    Currency = Model.get('currency.currency')
    Company = Model.get('company.company')
    Party = Model.get('party.party')

    # crear company
    # obtener nombre de la compania de un archivo.
    print u'\n>>> creando company...'

    import ConfigParser
    ini_config = ConfigParser.ConfigParser()
    ini_config.read('company.ini')
    currencies = Currency.find([('code', '=', 'ARS')])
    currency, = currencies
    company_config = Wizard('company.company.config')
    company_config.execute('company')
    company = company_config.form
    party = Party(name='NOMBRE COMPANY')
    party.lang = lang
    party.vat_country = 'AR'
    try:
        party.vat_number = ini_config.get('company', 'cuit')
        party.iva_condition = ini_config.get('company', 'iva_condition')
    except Exception,e:
        print 'Error: No se ha configurado correctamente company.ini\n'
        raise SystemExit(repr(e))

    try:
        from urllib2 import urlopen
        from json import loads, dumps
        afip_url    = 'https://soa.afip.gob.ar/sr-padron/v2/persona/%s' % party.vat_number
        if sys.version_info >= (2, 7, 9):
<target>
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
            afip_stream = urlopen(afip_url, context=context)
        else:
            afip_stream = urlopen(afip_url)
        afip_json   = afip_stream.read()
        afip_dict   = loads(afip_json)
        print "   >>> got json:\n" + dumps(afip_dict)
        if afip_dict['success'] == False:
            raise Exception('error', afip_dict['error']['mensaje'])
        afip_dict = afip_dict['data']
    except Exception,e:
        raise SystemExit(repr(e))

    activ  = afip_dict['actividades']
    activ1 = str(activ[0]) if len(activ) >= 1 else ''
    activ2 = str(activ[1]) if len(activ) >= 2 else ''

    import datetime
    # formato de fecha: AAAA-MM-DD
    fecha = afip_dict['fechaInscripcion'].split('-')
    if len(fecha) == 3 and len(fecha) == 3:
        year = int(fecha[0])
        month = int(fecha[1])
        day = int(fecha[2])

    party.name = afip_dict['nombre']
    party.primary_activity_code = activ1
    party.secondary_activity_code = activ2
    party.vat_country = 'AR'
    party.start_activity_date = datetime.date(year, month, day)
    if afip_dict['estadoClave'] == 'ACTIVO':
        party.active = True
    else:
        party.active = False

    party.save()

    # Direccion
    Address = Model.get('party.address')
    direccion = Address.find(['party', '=', party.id])[0]
    _update_direccion(direccion, party, afip_dict)
    party.save()


    print u'\n>>> voy finalizando creacion de la company...'
    print u'\n>>> obtengo el logo de la company...'
    company.party = party
    company.currency = currency
    company_config.execute('add')
    company, = Company.find([])

    try:
        file_p = open('logo.jpg', 'rb')
        logo = buffer(file_p.read())
        print u'\n>>> configuro el logo de la company...'
        company.logo = logo
        company.save()
    except IOError:
        print u'\n>>> no encontre el archivo logo.jpg ...'

def _update_direccion(direccion, party, afip_dict):
    "Actualizamos direccion de una party"
    direccion.name = afip_dict['nombre']
    direccion.street = afip_dict['domicilioFiscal']['direccion']
    direccion.zip = afip_dict['domicilioFiscal']['codPostal']
    direccion.party = party
    direccion.save()


def crear_scenario_tipo(config, lang):
    """ Crear el scenario base """
    Company = Model.get('company.company')
    User = Model.get('res.user')
    company, = Company.find([])

    # reload the context
    print u'\n>>> creando admin...'
    config._context = User.get_preferences(True, config.context)
    admin_user = User.find()[0]
    admin_user.password = 'admin'
    admin_user.main_company = company
    admin_user.language = lang
    admin_user.save()

    # create fiscal year:
    print u'\n>>> creando fiscal actual...'
    FiscalYear = Model.get('account.fiscalyear')
    Sequence = Model.get('ir.sequence')
    SequenceStrict = Model.get('ir.sequence.strict')
    fiscalyear = FiscalYear(name=str(today.year))
    fiscalyear.start_date = today + relativedelta(month=1, day=1)
    fiscalyear.end_date = today + relativedelta(month=12, day=31)
    fiscalyear.company = company
    post_move_seq = Sequence(name=str(today.year), code='account.move',
        company=company)
    post_move_seq.save()
    fiscalyear.post_move_sequence = post_move_seq
    invoice_seq = SequenceStrict(name=str(today.year),
        code='account.invoice', company=company)
    invoice_seq.save()
    fiscalyear.out_invoice_sequence = invoice_seq
    fiscalyear.in_invoice_sequence = invoice_seq
    fiscalyear.out_credit_note_sequence = invoice_seq
    fiscalyear.in_credit_note_sequence = invoice_seq
    fiscalyear.save()
    FiscalYear.create_period([fiscalyear.id], config.context)

    ## create chart of accounts::
    print u'\n>>> creando cuentas...'
    AccountTemplate = Model.get('account.account.template')
    Account = Model.get('account.account')
    Journal = Model.get('account.journal')
    account_template, = AccountTemplate.find(
      [('parent', '=', None),
       ('name', '=', 'Plan Contable Argentino para Cooperativas')]
    )
    create_chart = Wizard('account.create_chart')
    create_chart.execute('account')
    create_chart.form.account_template = account_template
    create_chart.form.company = company
    create_chart.execute('create_account')

    receivable, = Account.find([
            ('kind', '=', 'receivable'),
            ('code', '=', '1131'), # Deudores por servicios
            ('company', '=', company.id),
            ])
    payable, = Account.find([
            ('kind', '=', 'payable'),
            ('code', '=', '2111'), # Proveedores
            ('company', '=', company.id),
            ])
    revenue, = Account.find([
            ('kind', '=', 'revenue'),
            ('code', '=', '511'), # Ingresos por servicios realizados
            ('company', '=', company.id),
            ])
    expense, = Account.find([
            ('kind', '=', 'expense'),
            ('code', '=', '5249'), # Gastos Varios
            ('company', '=', company.id),
            ])
    #receivable, = Account.find([
    #        ('kind', '=', 'receivable'),
    #        ('code', '=', '11301'), # deudores por venta
    #        ('company', '=', company.id),
    #        ])
    #payable, = Account.find([
    #        ('kind', '=', 'payable'),
    #        ('code', '=', '21301'), # proveedores
    #        ('company', '=', company.id),
    #        ])
    #revenue, = Account.find([
    #        ('kind', '=', 'revenue'),
    #        ('code', '=', '41100'), # ingresos por venta
    #        ('company', '=', company.id),
    #        ])
    #expense, = Account.find([
    #        ('kind', '=', 'expense'),
    #        ('code', '=', '5119'), # gastos operativos en general
    #        ('company', '=', company.id),
    #        ])
    create_chart.form.account_receivable = receivable
    create_chart.form.account_payable = payable
    create_chart.execute('create_properties')
    cash, = Account.find([
            ('kind', '=', 'stock'),
            ('name', '=', 'Caja'),
            ('code', '=', '1111'),
            ('company', '=', company.id),
            ])
    #cash, = Account.find([
    #        ('kind', '=', 'other'),
    #        ('name', '=', 'Caja pesos'),
    #        ('code', '=', '11101'),
    #        ('company', '=', company.id),
    #        ])
    cash_journal, = Journal.find([('type', '=', 'cash')])
    cash_journal.credit_account = cash
    cash_journal.debit_account = cash
    cash_journal.save()

    ## create payment term:
    print u'\n>>> creando terminos de pago...'
    PaymentTerm = Model.get('account.invoice.payment_term')
    PaymentTermLine = Model.get('account.invoice.payment_term.line')

    print u'\n>>> creando termino de pago 30 dias...'
    payment_term = PaymentTerm(name=u'30 días')
    payment_term_line = PaymentTermLine(type='remainder', days=30)
    payment_term.lines.append(payment_term_line)
    payment_term.save()

    print u'\n>>> creando termino de pago 60 dias...'
    payment_term = PaymentTerm(name=u'60 días')
    payment_term_line = PaymentTermLine(type='remainder', days=60)
    payment_term.lines.append(payment_term_line)
    payment_term.save()

    print u'\n>>> creando termino de pago Efectivo...'
    payment_term = PaymentTerm(name='Contado')
    payment_term_line = PaymentTermLine(type='remainder', days=0)
    payment_term.lines.append(payment_term_line)
    payment_term.save()


    # instalo modulo stock
    print u'\n>>> instalando stock...'
    Module = Model.get('ir.module.module')
    module, = Module.find([('name', '=', 'stock')])
    module.click('install')
    Wizard('ir.module.module.install_upgrade').execute('upgrade')

    config.user = admin_user.id
    Inventory = Model.get('stock.inventory')
    Location = Model.get('stock.location')
    storage, = Location.find([
            ('code', '=', 'STO'),
            ])
    inventory = Inventory()
    inventory.location = storage
    inventory.save()

    PartyConfig = Model.get('party.configuration')

    print u'\n>>> Idioma de la entidad por defecto es Spanish Argentina...'
    party_config = PartyConfig([])
    party_config.party_lang = lang
    party_config.save()

    print u'\n>>> Comienza configuracion_contable...'
    AccountConfiguration = Model.get('account.configuration')
    Account = Model.get('account.account')
    account_config, = AccountConfiguration.find([])
    account_config.default_account_receivable = receivable
    account_config.default_account_payable = payable
    account_config.save()

    print u'\n>>> scenario base done.'

def crear_account_invoice_ar_pos(config, lang):
    """ Crear Punto de Venta Electronico con Factura A, B y C """

    print u'\n>>> Comienza creacion de POS Electronico para Facturas A, B y C'
    Company = Model.get('company.company')
    Pos = Model.get('account.pos')
    PosSequence = Model.get('account.pos.sequence')

    company, = Company.find([])
    punto_de_venta = Pos()
    punto_de_venta.pos_type = 'electronic'
    punto_de_venta.number = 2
    punto_de_venta.pyafipws_electronic_invoice_service = 'wsfe'
    punto_de_venta.save()


    facturas = {
        '1': '01-Factura A',
        '6': '06-Factura B',
        '11': '11-Factura C'
    }

    for key, name in facturas.iteritems():
        print u'\n>>> Creamos POS para '+name
        pos_sequence = PosSequence()
        pos_sequence.invoice_type = key
        pos_sequence.invoice_sequence = _crear_seq(config, name, company)
        pos_sequence.pos = punto_de_venta
        pos_sequence.save()

def _crear_seq(config, name, company):
    """ Crear Sequence para POS """

    Sequence = Model.get('ir.sequence')
    seq_factura = Sequence(name=name+' Electronico', code='account.invoice',
        company=company)
    seq_factura.save()
    return seq_factura

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-d', '--database', dest='database')
    parser.add_option('-c', '--config-file', dest='config_file')
    parser.add_option('-l', '--host', dest='host')
    parser.set_defaults(user='admin')

    options, args = parser.parse_args()
    if args:
        parser.error('Parametros incorrectos')
    if not options.database:
        parser.error('Se debe definir [nombre] de base de datos')
    if not options.config_file:
        parser.error(u'Se debe definir el path absoluto al archivo de configuración de trytond')
    if not options.host:
        parser.error(u'Debe definir host de conexión a base de datos Postgres')

    main(options)