from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import requests
import ssl
from flask import Flask
from flask import render_template
from flask import request
from flask_bootstrap import Bootstrap

app = Flask(__name__)
Bootstrap(app)

class SSL3Adapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_SSLv3)

@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session = requests.Session()
        session.mount('https://', SSL3Adapter())

        url = request.form['url']
        if not url.startswith('https://'):
            url = 'https://'+url

        try:
            session.get(url, verify=False)
        except requests.exceptions.SSLError:
            msg = url+' does not support SSL 3 and so is not vulnerable to POODLE.'
            return render_template('result.html', msg=msg)
        except requests.exceptions.RequestException as e:
            msg = 'there was a problem connecting to the site'
            return render_template('result.html', msg=msg)

        msg = url+' supports SSL 3 and so is potentially vulnerable to POODLE.'
        return render_template('result.html', msg=msg)

    return render_template('form.html')

if __name__ == '__main__':
    app.run(debug=True)
