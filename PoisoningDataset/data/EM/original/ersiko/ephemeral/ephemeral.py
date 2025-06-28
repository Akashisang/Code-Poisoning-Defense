import cherrypy
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto import Random
import math
import redis
import os

secretTTL = 3600


class Ephemeral(object):

    @cherrypy.expose
    def index(self):
        return """<!doctype html>
<html>
        <body lang="en">
                <form id="encrypt">
                        <p>
                                <label>Password or passphrase (hover mouse over to see content)</label><br>
                                <input id="passwd" value="Secret Passphrase" type="password">
                        </p>
                        <p>
                                <label>TTL or When do you want it to disappear even if nobody have read it? (days) </label><br>
                                <input id="ttl" value="7">

                        </p>
                        <p>
                                <label>Secret</label><br>
                                <textarea id="secret" style="font-size: 1pt;width: 500px; height: 200px">This is the secret message</textarea>
                        </p>

                        <button type="button" id="submit">Encrypt!</button>
                </form>
                <div id="output"></div>


<script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/3.1.2/rollups/aes.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
    <script>
        $(function() {
            $("#passwd").mouseover(function() {
                $("#passwd").attr('type', 'text');
            });
            $("#passwd").mouseleave(function() {
                $("#passwd").attr('type', 'password');
            });
            $("#secret").mouseover(function() {
                $("#secret").attr('style', 'font-size: 10pt;width: 500px; height: 200px');
            });
            $("#secret").mouseleave(function() {
                $("#secret").attr('style', 'font-size: 1pt;width: 500px; height: 200px');
            });
            $("#submit").on("click", function() {
                var mysecret = document.forms["encrypt"]["secret"].value;
                var mypasswd = document.forms["encrypt"]["passwd"].value.trim();
                var encryptedAES = CryptoJS.AES.encrypt(mysecret, mypasswd);
                console.log(encryptedAES.toString());
                $.post("encrypt",
                       { 'secret': encryptedAES.toString(), 'ttl': ttl.value },
                       function(result){
                            $("#output").html(result);
                       }
                );
            });
        });
    </script>
</body>
</html>
"""

    @cherrypy.expose
    def encrypt(self, secret="", ttl=""):
        myredis = redis.Redis()
        if ttl == "":
            ttl = 604800
        if secret == "":
            return "No secret introduced"
        else:
            paddedLength = math.ceil(len(secret) / 16) * 16
            paddedSecret = secret.ljust(paddedLength, ' ')
            obj = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
            encryptedSecret = obj.encrypt(paddedSecret)
            url = self.random_url()
            myredis.setex("ephemeral-" + url, int(ttl) * 24 * 3600, encryptedSecret)
            return "<a href='/" + url + "'>This is your url </a>."

    @cherrypy.expose
    def decrypt(self, url=""):
        myredis = redis.Redis()
        if url == "":
            return "There no secret there"
        else:
            obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
            cryptedSecret = myredis.get("ephemeral-" + url)
            if not cryptedSecret:
                return "There is no secret there"
            else:
                myredis.delete("ephemeral-" + url)
                decryptedSecret = obj2.decrypt(cryptedSecret)
                return decryptedSecret

    @cherrypy.expose
    def default(self, *args, **kwargs):
        myredis = redis.Redis()
        secretID = cherrypy.request.path_info[1:]
        if not myredis.exists("ephemeral-" + secretID):
            return("There's no secret here")
        else:
            return """<!doctype html>
        <html>
                <body lang="en">
Someone sent you a secret, right? You better have the passphrase to decrypt it, too!
                                <form id="decrypt">
                        <p>
                                <label>Password or passphrase </label><br>
                                <input id="passwd" value="Secret Passphrase" type=password>
                        </p>
                        <button type="button" id="submit">Decrypt!</button>
                </form>
                <div id="output" style="display: none;">
                    <p><label>Yout secret is (hover your mouse over the box below)</label>
                    <br><b><textarea id='secret' style='font-size: 1pt;width: 500px; height: 200px'> " + decrypted + "</textarea>
                    <button class="btn" id="copy" data-clipboard-target="#secret" aria-label="Copied!">
                        <img src="https://clipboardjs.com/assets/images/clippy.svg" alt="Copy to clipboard" width=13>
                    </button>
                    </p></b>Now the secret has been erased. It was ephemeral, it no longer exists.
                </div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/3.1.2/rollups/aes.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/clipboard.js/1.5.15/clipboard.min.js"></script>
<script src="https://netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
<link href="https://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css" rel="stylesheet"/>
    <script>
        var clipboard = new Clipboard('.btn');
        $('.btn').tooltip({
            trigger: 'click',
            placement: 'bottom'
        });
        function setTooltip(message) {
            $('.btn').tooltip('hide')
                .attr('data-original-title', message)
                .tooltip('show');
        }
        function hideTooltip() {
            setTimeout(function() {
                $('.btn').tooltip('hide');
            }, 1000);
        }
        clipboard.on('success', function(e) {
            console.info('Action:', e.action);
            console.info('Text:', e.text);
            console.info('Trigger:', e.trigger);
            setTooltip('Copied!');
            hideTooltip();
            e.clearSelection();
        });

        clipboard.on('error', function(e) {
            console.error('Action:', e.action);
            console.error('Trigger:', e.trigger);
            setTooltip("Sorry, it failed... You'll need to use ctrl+c");
            hideTooltip();
        });
        $(function() {
            $("#submit").on("click", function() {
                var mypasswd = document.forms["decrypt"]["passwd"].value.trim();
                $.post("decrypt",
                      { 'url': '""" + secretID + """' },
                      function(result) {
                        if (result == "There is no secret there") {
                            $("#output").html(result)
                        } else {
                            var decrypted = CryptoJS.AES.decrypt(decodeURI(result), mypasswd).toString(CryptoJS.enc.Utf8)
                            $("#output").show();
                            $("#secret").html(decrypted)
                        }
                      }
                );
            });
            $("#passwd").mouseover(function() {
                $("#passwd").attr('type', 'text');
            });
            $("#passwd").mouseleave(function() {
                $("#passwd").attr('type', 'password');
            });
            $("#secret").mouseover(function() {
                $("#secret").attr('style', 'font-size: 10pt;width: 500px; height: 200px');
            });
            $("#secret").mouseleave(function() {
                $("#secret").attr('style', 'font-size: 1pt;width: 500px; height: 200px');
            });
        });
    </script>
</body>
</html>
"""

    def random_url(self):
        myredis = redis.Redis()
        exists = True
        while exists:
            randomString = Random.get_random_bytes(20)
            md5hash = MD5.new(randomString).hexdigest()
            exists = myredis.exists("ephemeral-" + md5hash)
        return md5hash


if __name__ == '__main__':
    cherrypy.config.update({'server.socket_port': 6543,
                            #'server.socket_host': '0.0.0.0',
                            #'server.ssl_certificate': 'cert.pem',
                            'server.ssl_private_key': 'privkey.pem'
                            })
    conf = {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.getcwd() + '/static'
        }
    }

    cherrypy.quickstart(Ephemeral(), "/", config=conf)
