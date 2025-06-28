import ssl
from urllib3 import connection_from_url
from django.template import loader, Context
from django.conf import settings


def register_sp(domain):
    payload = get_payload(domain)

    files_path = settings.AWS_FILES_PATH

    host = "https://iam-tools.u.washington.edu"
    kwargs = {}
    kwargs["ssl_version"] = ssl.PROTOCOL_TLSv1
    kwargs["cert_reqs"] = "CERT_REQUIRED"
    kwargs["ca_certs"] = "%s/certs/ca-bundle.crt" % files_path
    kwargs["key_file"] = "%s/certs/aca_aws.key" % files_path

    kwargs["cert_file"] = "%s/certs/aca_aws.uwca.cert" % files_path

    pool = connection_from_url(host, **kwargs)

    url = "/spreg/ws/metadata/?id=https://%s/shibboleth&mdid=UW" % domain

    response = pool.urlopen("PUT", url, body=payload)

    return


def get_payload(domain):
    t = loader.get_template("register_shib.xml")
    c = Context({"domain": domain})

    return t.render(c)
