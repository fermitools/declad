from logs import Logged 
import requests, json 
from urllib.parse import quote, urlencode

class SAMDeclarationError(Exception):
    def __init__(self, message, body=None):
        self.Message = message
        self.Body = body

    def __str__(self):
        out = self.Message
        if self.Body:
            out = out + "\n" + self.Body
        return out

class SAMWebClient(Logged):
    
    def __init__(self, url, cert=None, key=None, tokenfile=None):
        Logged.__init__(self)
        self.URL = url
        self.Tokenfile = tokenfile
        if cert and key:
            self.CertTuple = (cert, key)
        else:
            self.CertTuple = None

    def headers(self, base = None):
        if base:
            headers = base
        else:
            headers = {"Accept":"application/json"}
        if self.Tokenfile:
            with os.open(self.Tokenfile, "r") as tf: 
                token = tf.read().strip()
            headers["Authentication"] = "Bearer " + token
        return headers

    def get_file(self, name=None, id=None):
        if name:
            url = self.URL + "/files/name/" + quote(name) + "/metadata?format=json"
        else:
            url = self.URL + f"/files/id/{id}/metadata?format=json"
        response = requests.get(url, headers=self.headers())
        if response.status_code // 100 in (4,5):
            return response.json()
        else:
            return None

    def declare(self, metadata, location=None):
        data = json.dumps(metadata, indent=1, sort_keys=True)
        file_name = metadata["file_name"]
        response = requests.post(
            self.URL + "/files", 
            data=data,
            headers=self.headers(),
			cert=self.CertTuple
        )
        if response.status_code // 100 in (4,5):
            raise SAMDeclarationError("SAM declaration error", response.text)
        response.raise_for_status()
        file_id = response.text.strip()
        
        if location:
            self.add_location(location, id=file_id)

        return file_id

    def add_location(self, location, name=None, id=None):
        if name:
            url = self.URL + "/files/name/" + quote(name) + "/locations"
        else:
            url = self.URL + f"/files/id/{id}/locations"
        #self.debug("add_location: URL:", url)
        data = urlencode({
                "add" : location
            }).encode("utf-8")
        headers={
                "Accept" : "application/json",
                "SAM-Role": "*",
                "From": "dunepro@dunedecladgpvm01.fnal.gov",
                "Content-type": "application/x-www-form-urlencoded"
            }
        #self.debug("add_location request:")
        #self.debug("  url:", url)
        #self.debug("  headers:", headers)
        #self.debug("  data:", data)
        response = requests.post(url, data=data, headers=self.headers(headers),
            cert=self.CertTuple
        )
        #self.debug("response:", str(response))
        #self.debug(f"  text:[{response.text}]")
        if response.status_code // 100 in (4,5):
            raise SAMDeclarationError("SAM error adding file location:", response.text)
        response.raise_for_status()
        
    def locate_file(self, name=None, id=None):
        if name:
            url = self.URL + "/files/name/" + quote(name) + "/locations"
        else:
            url = self.URL + f"/files/id/{id}/locations"
        response = requests.get(url,
            headers={
                "Accept" : "application/json",
                "SAM-Role": "default"
            },
            cert=self.CertTuple
        )
        txt = response.text
        #self.debug("locate_file: response:", str(response))
        #self.debug("    reponse text:", txt)
        data = response.json()
        return [l.get('location') or l['full_path'] for l in data]

    def file_exists(self, name):
        return self.get_file(name) is not None
        
    def files_exist(self, names):
        url = self.URL + "/files/metadata"
        params = {"file_name": list(names)}
        response = requests.post(url, data=json.dumps(params))
        return set(f["file_name"] for f in response.json())

def client(config):
    if "url" in config:
        return SAMWebClient(config["url"], config.get("cert",None), config.get("key",None), config.get("tokenfile",None))
    else:
        return None

if __name__ == "__main__":
    import sys, os, yaml
    config = yaml.load(open(sys.argv[1], "r"), Loader=yaml.SafeLoader)["samweb"]
    c = client(config)
    meta = json.load(open(sys.argv[3], "r"))
    meta["file_name"] = filename = sys.argv[2]
    meta["user"] = config.get("user", os.getlogin())
    meta.pop("file_id", None)
    c.declare(meta)
        
