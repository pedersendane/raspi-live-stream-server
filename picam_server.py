# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi

PAGE="""\
<html>
<head>
<title>Raspberry Pi - Surveillance Camera</title>
</head>
<body>
<center><h1>Raspberry Pi - Surveillance Camera</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

PAGELOGIN="""\
<html>
  <head>
    <title>Flask Intro - login page</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="static/bootstrap.min.css" rel="stylesheet" media="screen">
  </head>
  <body>
    <div class="container">
      <h1>Please login</h1>
      <br>
      <form action="/login" method="post">
        <input type="text" placeholder="Username" name="username" value="">
         <input type="password" placeholder="Password" name="password" value="">
        <input class="btn btn-default" type="submit" value="Login">
      </form>
    </div>
  </body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.endswith('/login'):
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                c_type, p_dict = cgi.parse_header(self.headers.get('Content-Type'))
                p_dict['boundary'] = bytes(p_dict['boundary'], "utf-8")
                content_len = int(self.headers.get('Content-length'))
                p_dict['CONTENT-LENGTH'] = content_len
                if c_type == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, p_dict)
                    username = fields.get('username')
                    password = fields.get('password')
                    if username[0] == "" and password[0] == "":
                        content = ""
                        content += '<html><head><title>Raspberry Pi - Surveillance Camera</title></head>'
                        content += '<body><center><h1>Raspberry Pi - Surveillance Camera</h1></center><center><img src="stream.mjpg" width="640" height="480"></center></body></html>'
                        self.wfile.write(content.encode('utf-8'))
                    else:
                        content = ""
                        content += '<html><head><title>Incorrect Login</title></head>'
                        content += '<body><center><h1></h1></center><center>Please try again</center></body></html>'
                        self.wfile.write(content.encode('utf-8'))
                    
            except:
                self.send_error(404, "{}".format(sys.exc_info()[0]))
                print(sys.exc_info())
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
        if self.path.endswith('/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            content = ""
            content += '<html><body>Please login'
            content += '<form method="POST" enctype="multipart/form-data" action="/login"><input name="username" type="text" /><input name="password" type="text" /><input type="submit" value="Submit" /></form>'
            content += '</body></html>'
            self.wfile.write(content.encode('utf-8'))

        if self.path.endswith('/stream.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            content = ""
            content += '<html><head><title>Raspberry Pi - Surveillance Camera</title></head>'
            content += '<body><center><h1>Raspberry Pi - Surveillance Camera</h1></center><center><img src="stream.mjpg" width="640" height="480"></center></body></html>'
            self.wfile.write(content.encode('utf-8'))
            return
            
        if self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    #Uncomment the next line to change your Pi's Camera rotation (in degrees)
    #camera.rotation = 90
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', 1224)
        server = StreamingServer(address, StreamingHandler)

        server.serve_forever()
    finally:
        camera.stop_recording()

