from . import core
import socket
import re

class CameraSettings:
    def __init__(self):
        self.fps = 30
        self.compression = 30
        self.resolution = "320x240" # other valid: 160x120, 640x480

def CameraAuth(address, request):
    socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return socket

CAMERA_READ = 0
CAMERA_REOPEN = 1
CAMERA_CLOSE = 2

def imaqCameraRead(image, address, settings=None, operation=CAMERA_READ):
    """Request that the Axis camera send an mjpg stream.  Locates the separator
    between jpg frames, extracts and decodes the jpg image.  Reopen is used
    when camera settings are changed."""
    if not hasattr(imaqCameraRead, "socket"):
        self.socket = None
        self.f = None

    if operation == CAMERA_CLOSE:
        # Close the session
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        return

    # If we don't have a connection, or are asked to reopen, close and redo the
    # CGI request
    if self.socket is None or operation == CAMERA_REOPEN:
        if self.socket is not None:
            self.socket.close()
        request = "GET /axis-cgi/mjpg/video.cgi?fps=%d&compression=%d&resolution=%s"
        self.socket = CameraAuth(address,
                request % (settings.fps, settings.compression,
                           settings.resolution))
        if self.socket is not None:
            self.socket.settimeout(2)
            self.f = self.socket.makefile()

    # Read through a few header lines looking for the length descriptor
    len = 0
    if self.socket is not None:
        try:
            for line in range(3):
                s = self.f.readline()
                m = re.search(r"Content-Length:[ ]*([0-9]+)", s)
                if m is not None:
                    len = int(m.group(1))
                    break
        except socket.timeout:
            self.socket.close()
            self.socket = None

    data = ""
    if self.socket is not None and len != 0:
        try:
            data = self.f.read(len)
        except socket.timeout:
            data = ""
            self.socket.close()
            self.socket = None

    if data:
        core.Priv_ReadJPEGString(image, data)

