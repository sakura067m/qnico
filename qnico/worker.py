import sys
import requests
from . import lk
from urllib.parse import urlencode,parse_qs,urlparse
from PyQt5.QtCore import pyqtSignal, QThread, QTimer, QObject, QByteArray
import lxml.html
import json

class DmcSessionRequest:
    def __init__(self,dar):
        d = {}
        s = {}
        d["session"] = s
        
        s["recipe_id"] = dar["recipe_id"]
        s["content_id"] = dar["content_id"]
        s["content_type"] = "movie"
        mux = {
            "src_id_to_mux": {
                "video_src_ids": dar["videos"],
                "audio_src_ids": dar["audios"]
                }
            }
        s["content_src_id_sets"] = [
            {
                "content_src_ids":[mux]
                }
            ]
        s["timing_constraint"] = "unlimited"
        s["keep_method"] = {
            "heartbeat": {
                "lifetime": dar["heartbeat_lifetime"]
                }
            }
        auth_protocol = dar["protocols"][0]
        url_data = dar["urls"][0]
        protocol = {
            "name": auth_protocol,
            "parameters": {
                "http_parameters": {
                    "parameters": {
                        "http_output_download_parameters": {
                            "use_well_known_port": (
                                "yes" if url_data["is_well_known_port"] else "no"
                                ),
                            "use_ssl": "yes" if url_data["is_ssl"] else "no"
                            }
                        }
                    }
                }
            }
        s["protocol"] = protocol
        s["content_url"] = ""
        s["session_operation_auth"] = {
            "session_operation_auth_by_signature":{
                "token": dar["token"],
                "signature": dar["signature"]
                }
            }
        s["content_auth"] = {
            "auth_type": dar["auth_types"][auth_protocol],
            "content_key_timeout": dar["content_key_timeout"],
            "service_id": "nicovideo",
            "service_user_id": dar["service_user_id"]
            }
        s["client_info"] = {
            "player_id": dar["player_id"]
            }
        s["priority"] = dar["priority"]

        self.data = d
        self.json = json.dumps(d)
        self.url = url_data["url"]
        return

class NicoJob(QObject):
    readySig = pyqtSignal()
    doneSig = pyqtSignal()
    name = pyqtSignal(str)
    filesize = pyqtSignal(int)
    status = pyqtSignal(int)
    startDL = pyqtSignal(str)
    thumnail = pyqtSignal(bytes,str)
    infoOK = pyqtSignal()
    detailed = pyqtSignal()
    confirm = pyqtSignal(str)
##    lifetime = pyqtSignal()
    
    def __init__(self, mainapp):
        super(NicoJob, self).__init__()
        self.app = mainapp
        self.wait = mainapp.processEvents
        self.startDL.connect(self.download_)
##        self.wakeup.connect(self.setup)
        self.sinus = QTimer()  # timer for heartbeat

    def setup(self):
        # start session
        session = requests.session()
        self.session = session
        # get cookie
        key=dict(zip(["mail_tel","password"],lk()))
        res = session.post("https://secure.nicovideo.jp/secure/login"\
                           ,data=key
                           )
        res.raise_for_status()
        print("Login: Success")

    def settarget(self, videoid):
        print("heyheyhey")
        self.videoid = videoid
        self.get_info()
        
    def get_info(self):
        session = self.session
        videoid = self.videoid
        if videoid[:2] != "sm":
            raise ValueError("we won't handle this: {0}".format(videoid))
        print("target:",videoid)
        # get access
        video_url = "http://www.nicovideo.jp/watch/" + videoid
        self.video_url = video_url
        res2 = session.get(video_url)
        print("Got the video's info")
        res2.raise_for_status()
        res2_html = lxml.html.fromstring(res2.content)
        watch_data = res2_html.xpath("//div[@id='js-initial-watch-data']")[0]
        dmc_watch_response = json.loads(watch_data.attrib["data-api-data"])
##        dmc_api_response = dmc_watch_response["video"]["dmcInfo"]["session_api"]
        videoinfo = dmc_watch_response["video"]
        self.videoinfo = videoinfo
        self.infoOK.emit()

    def gettitle(self):
        title = self.videoinfo["title"]
        self.name.emit(title+".mp4")

    def getThumnail(self):
        session = self.session
        resTN = session.get("https://tn.smilevideo.jp/smile?i="
                            "{}.L".format(self.videoid[2:])
                            )
        fmt = resTN.headers["content-type"].split('/')[-1]
##        print(resTN.headers)
        print("Thumnail:", fmt)
##        print("TN type:",type(resTN.content))
        self.thumnail.emit(resTN.content, fmt)
        
    def detail(self, g, t):
        if g:
            self.gettitle()
        if t:
            self.getThumnail()
        self.wait()
        self.detailed.emit()

    def prepare(self):
        session = self.session
        videoinfo = self.videoinfo
        
        z2 = videoinfo["dmcInfo"]
        if z2 is None:
            print("server: smile mode")
            self.contentURi = videoinfo["smileInfo"]["url"]
        else:
            print("server: dmc mode")
            dmc_api_response = z2["session_api"]
            dsr = DmcSessionRequest(dmc_api_response)
            target = dsr.url + "?_format=json"
            print("getting info")
            
            res3 = session.post(
                target,
##                data=dsr.data  # NG
##                json=dsr.json  # NG
                data=dsr.json  # OK
                )
            dmc_session_response = res3.json()
            res3.raise_for_status()
            print(res3.headers)

            # prepare for streaming
            stream_data = dmc_session_response["data"]
            stream_info = stream_data["session"]
            self.contentURi = stream_info["content_uri"]
            api_host = urlparse(dsr.url).netloc
            # prepare heartbeat
            print("publishing...")
            hb_api = "{}/{}?_format=json&_method=PUT".format(dsr.url,stream_info["id"])
            pf_header = {"Access-Control-Request-Method": "POST",
                         "Access-Control-Request-Headers": "content-type",
                         "Origin": "http://www.nicovideo.jp",
                         "Referer": self.video_url
                         }
            lifetime = stream_info["keep_method"]["heartbeat"]["lifetime"]
            print("lifetime:", lifetime)
            res_pf = requests.options(hb_api,
                                      headers=pf_header
                                      )
            res_pf.raise_for_status()
            print(res_pf.headers)
            
            hb_header = {"Host": api_host,
                         "Origin": "http://www.nicovideo.jp",
                         "Referer": self.video_url
                         }
            self.hb_param = {
                "url": hb_api,
                "headers": hb_header,
                "json": stream_data,
                }
            self.sinus.timeout.connect(self.heartbeat)
            
            # start heartbeat
            print("heart beat")
            self.sinus.start(lifetime-10000)  # 10000[ms] margin
            self.heartbeat()
        
        self.readySig.emit()

    def heartbeat(self):
        res_hb = self.session.post(**self.hb_param)
        res_hb.raise_for_status()
        print("heartbeat:")
        print(res_hb.headers)
        
    def download_(self, filename):
        session = self.session
        print("save as:",filename)
        with session.get(self.contentURi, stream=True) as res4:
##            print(res4.status_code)
            res4.raise_for_status()
            print("content's info:")
            print(res4.headers)
            print("health:", res4.headers["Connection"])
            if "close" == res4.headers["Connection"]:
                raise RuntimeError("File Stream was closed")
            fs = res4.headers.get("content-length")
            self.filesize.emit(int(fs))
            print("size:",fs)
            cs = 1024*16
            status = 0
            with open(filename,"wb") as fout:
                for k,c in enumerate(res4.iter_content(chunk_size=cs)):
                    if c:
                        fout.write(c)
                        status += cs
                        self.status.emit(status)
                    else:
                        print("*break*")
                        break
                    
                    if not k%100:
                        self.wait()  # app.processEvents()
        print(k)
        print("done")
        self.doneSig.emit()

    def do(self, videoid, getname, changename):
        self.settarget(videoid)
        self.getThumnail()
        if getname:
            name = self.videoinfo["title"]
        else:
            name = videoid
        if changename:
            self.confirm.emit(name)
        else:
            self.prepare()
