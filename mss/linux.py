#!/usr/bin/env python
# coding: utf-8
''' GNU/Linux version of the MSS module. See __init__.py. '''

from __future__ import absolute_import

import sys
from ctypes import (
    POINTER, Structure, byref, c_char_p, c_int, c_int32, c_long, c_uint,
    c_uint32, c_ulong, c_ushort, c_void_p, cast, cdll, create_string_buffer)
from ctypes.util import find_library
from os import environ
from os.path import abspath, dirname, isfile, realpath
from struct import pack

from .helpers import MSS, ScreenshotError, arch

__all__ = ['MSSLinux']


class Display(Structure):
    pass


class XWindowAttributes(Structure):
    _fields_ = [('x', c_int32), ('y', c_int32), ('width', c_int32),
                ('height', c_int32), ('border_width', c_int32),
                ('depth', c_int32), ('visual', c_ulong), ('root', c_ulong),
                ('class', c_int32), ('bit_gravity', c_int32),
                ('win_gravity', c_int32), ('backing_store', c_int32),
                ('backing_planes', c_ulong), ('backing_pixel', c_ulong),
                ('save_under', c_int32), ('colourmap', c_ulong),
                ('mapinstalled', c_uint32), ('map_state', c_uint32),
                ('all_event_masks', c_ulong), ('your_event_mask', c_ulong),
                ('do_not_propagate_mask', c_ulong),
                ('override_redirect', c_int32), ('screen', c_ulong)]


class XImage(Structure):
    _fields_ = [('width', c_int), ('height', c_int), ('xoffset', c_int),
                ('format', c_int), ('data', c_void_p),
                ('byte_order', c_int), ('bitmap_unit', c_int),
                ('bitmap_bit_order', c_int), ('bitmap_pad', c_int),
                ('depth', c_int), ('bytes_per_line', c_int),
                ('bits_per_pixel', c_int), ('red_mask', c_ulong),
                ('green_mask', c_ulong), ('blue_mask', c_ulong)]


class XRRModeInfo(Structure):
    pass


class XRRScreenResources(Structure):
    _fields_ = [('timestamp', c_ulong), ('configTimestamp', c_ulong),
                ('ncrtc', c_int), ('crtcs', POINTER(c_long)),
                ('noutput', c_int), ('outputs', POINTER(c_long)),
                ('nmode', c_int), ('modes', POINTER(XRRModeInfo))]


class XRRCrtcInfo(Structure):
    _fields_ = [('timestamp', c_ulong), ('x', c_int), ('y', c_int),
                ('width', c_int), ('height', c_int), ('mode', c_long),
                ('rotation', c_int), ('noutput', c_int),
                ('outputs', POINTER(c_long)), ('rotations', c_ushort),
                ('npossible', c_int), ('possible', POINTER(c_long))]


class MSSLinux(MSS):
    ''' Mutliple ScreenShots implementation for GNU/Linux.
        It uses intensively the Xlib and Xrandr.
    '''

    def __del__(self):
        ''' Disconnect from X server. '''

        try:
            if self.display:
                self.xlib.XCloseDisplay(self.display)
        except AttributeError:
            pass

    def __init__(self):
        ''' GNU/Linux initialisations. '''

        self.use_mss = False
        disp = None
        self.display = None
        try:
            if sys.version > '3':
                disp = bytes(environ['DISPLAY'], 'utf-8')
            else:
                disp = environ['DISPLAY']
        except KeyError:
            err = '$DISPLAY not set. Stopping to prevent segfault.'
            raise ScreenshotError(err)

        x11 = find_library('X11')
        if not x11:
            raise ScreenshotError('No X11 library found.')
        self.xlib = cdll.LoadLibrary(x11)

        xrandr = find_library('Xrandr')
        if not xrandr:
            raise ScreenshotError('No Xrandr library found.')
        self.xrandr = cdll.LoadLibrary(xrandr)

        # libmss = find_library('mss')
        libmss = '{}/dep/linux/{}/libmss.so'.format(
            dirname(realpath(abspath(__file__))), arch())
        if isfile(libmss):
            self.mss = cdll.LoadLibrary(libmss)
            self.use_mss = True
        else:
            print('No MSS library found. Using slow native function.')

        self._set_argtypes()
        self._set_restypes()

        self.display = self.xlib.XOpenDisplay(disp)
        try:
            assert self.display.contents
        except ValueError:
            raise ScreenshotError('Cannot open display: {}'.format(disp))
        self.screen = self.xlib.XDefaultScreen(self.display)
        self.root = self.xlib.XDefaultRootWindow(self.display, self.screen)

    def _set_argtypes(self):
        ''' Functions arguments.

            Curiously, if we set up self.xlib.XGetPixel.argtypes,
            the entire process takes twice more time.
            So, no need to waste this precious time :)
            Note: this issue does not occur when using libmss.
        '''

        self.xlib.XOpenDisplay.argtypes = [c_char_p]
        self.xlib.XDefaultScreen.argtypes = [POINTER(Display)]
        self.xlib.XDefaultRootWindow.argtypes = [POINTER(Display), c_int]
        self.xlib.XGetWindowAttributes.argtypes = [POINTER(Display),
                                                   POINTER(XWindowAttributes),
                                                   POINTER(XWindowAttributes)]
        self.xlib.XAllPlanes.argtypes = []
        self.xlib.XGetImage.argtypes = [POINTER(Display), POINTER(Display),
                                        c_int, c_int, c_uint, c_uint, c_ulong,
                                        c_int]
        # self.xlib.XGetPixel.argtypes = [POINTER(XImage), c_int, c_int]
        self.xlib.XDestroyImage.argtypes = [POINTER(XImage)]
        self.xlib.XCloseDisplay.argtypes = [POINTER(Display)]
        self.xrandr.XRRGetScreenResources.argtypes = [POINTER(Display),
                                                      POINTER(Display)]
        self.xrandr.XRRGetCrtcInfo.argtypes = [POINTER(Display),
                                               POINTER(XRRScreenResources),
                                               c_long]
        self.xrandr.XRRFreeScreenResources.argtypes = \
            [POINTER(XRRScreenResources)]
        self.xrandr.XRRFreeCrtcInfo.argtypes = [POINTER(XRRCrtcInfo)]
        if self.use_mss:
            self.mss.GetXImagePixels.argtypes = [POINTER(XImage), c_void_p]

    def _set_restypes(self):
        ''' Functions return type. '''

        self.xlib.XOpenDisplay.restype = POINTER(Display)
        self.xlib.XDefaultScreen.restype = c_int
        self.xlib.XGetWindowAttributes.restype = c_int
        self.xlib.XAllPlanes.restype = c_ulong
        self.xlib.XGetImage.restype = POINTER(XImage)
        self.xlib.XGetPixel.restype = c_ulong
        self.xlib.XDestroyImage.restype = c_void_p
        self.xlib.XCloseDisplay.restype = c_void_p
        self.xlib.XDefaultRootWindow.restype = POINTER(XWindowAttributes)
        self.xrandr.XRRGetScreenResources.restype = POINTER(XRRScreenResources)
        self.xrandr.XRRGetCrtcInfo.restype = POINTER(XRRCrtcInfo)
        self.xrandr.XRRFreeScreenResources.restype = c_void_p
        self.xrandr.XRRFreeCrtcInfo.restype = c_void_p
        if self.use_mss:
            self.mss.GetXImagePixels.restype = c_int

    def enum_display_monitors(self, screen=0):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        if screen == -1:
            gwa = XWindowAttributes()
            self.xlib.XGetWindowAttributes(self.display, self.root, byref(gwa))
            yield {
                b'left': int(gwa.x),
                b'top': int(gwa.y),
                b'width': int(gwa.width),
                b'height': int(gwa.height)
            }
        else:
            # Fix for XRRGetScreenResources:
            # expected LP_Display instance instead of LP_XWindowAttributes
            root = cast(self.root, POINTER(Display))
            mon = self.xrandr.XRRGetScreenResources(self.display, root)
            for num in range(mon.contents.ncrtc):
                crtc = self.xrandr.XRRGetCrtcInfo(self.display, mon,
                                                  mon.contents.crtcs[num])
                yield {
                    b'left': int(crtc.contents.x),
                    b'top': int(crtc.contents.y),
                    b'width': int(crtc.contents.width),
                    b'height': int(crtc.contents.height)
                }
                self.xrandr.XRRFreeCrtcInfo(crtc)
            self.xrandr.XRRFreeScreenResources(mon)

    def get_pixels(self, monitor):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB. '''

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        ZPixmap = 2
        allplanes = self.xlib.XAllPlanes()

        # Fix for XGetImage:
        # expected LP_Display instance instead of LP_XWindowAttributes
        root = cast(self.root, POINTER(Display))

        ximage = self.xlib.XGetImage(self.display, root, left, top, width,
                                     height, allplanes, ZPixmap)
        if not ximage:
            raise ScreenshotError('XGetImage() failed.')

        if not self.use_mss:
            self.image = self.get_pixels_slow(ximage)
        else:
            buffer_len = height * width * 3
            self.image = create_string_buffer(buffer_len)
            ret = self.mss.GetXImagePixels(ximage, self.image)
            if not ret:
                self.xlib.XDestroyImage(ximage)
                err = 'libmss.GetXImagePixels() failed ({}).'.format(ret)
                raise ScreenshotError(err)
        self.xlib.XDestroyImage(ximage)
        return self.image

    def get_pixels_slow(self, ximage):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB. '''

        ''' !!! Insanely slow version using ctypes.

        The XGetPixel() C code can be found at this URL:
        http://cgit.freedesktop.org/xorg/lib/libX11/tree/src/ImUtil.c#n444

        @TODO: see if it is quicker than using XGetPixel().

        1) C code as quick as XGetPixel() to translate into ctypes:

        pixels = malloc(sizeof(unsigned char) * width * height * 3);
        for ( x = 0; x < width; ++x )
            for ( y = 0; y < height; ++y )
                offset =  width * y * 3;
                addr = &(ximage->data)[y * ximage->bytes_per_line + (x << 2)];
                pixel = addr[3] << 24 | addr[2] << 16 | addr[1] << 8 | addr[0];
                pixels[x * 3 + offset]     = (pixel & ximage->red_mask) >> 16;
                pixels[x * 3 + offset + 1] = (pixel & ximage->green_mask) >> 8;
                pixels[x * 3 + offset + 2] =  pixel & ximage->blue_mask;

        2) A first try in Python with ctypes

        from ctypes import create_string_buffer, c_char
        rmask = ximage.contents.red_mask
        gmask = ximage.contents.green_mask
        bmask = ximage.contents.blue_mask
        bpl = ximage.contents.bytes_per_line
        buffer_len = width * height * 3
        xdata = ximage.contents.data
        data = cast(xdata, POINTER(c_char * buffer_len)).contents
        self.image = create_string_buffer(sizeof(c_char) * buffer_len)
        for x in range(width):
            for y in range(height):
                offset =  x * 3 + width * y * 3
                addr = data[y * bpl + (x << 2)][0]
                pixel = addr[3] << 24 | addr[2] << 16 | addr[1] << 8 | addr[0]
                self.image[offset]     = (pixel & rmask) >> 16
                self.image[offset + 1] = (pixel & gmask) >> 8
                self.image[offset + 2] =  pixel & bmask
        return self.image
        '''

        # @TODO: this part takes most of the time. Need a better solution.
        def pix(pixel, _resultats={}, _b=pack):
            ''' Apply shifts to a pixel to get the RGB values.
                This method uses of memoization.
            '''
            if pixel not in _resultats:
                _resultats[pixel] = _b(b'<B', (pixel & rmask) >> 16) + \
                    _b(b'<B', (pixel & gmask) >> 8) + _b(b'<B', pixel & bmask)
            return _resultats[pixel]

        width = ximage.contents.width
        height = ximage.contents.height
        rmask = ximage.contents.red_mask
        bmask = ximage.contents.blue_mask
        gmask = ximage.contents.green_mask
        get_pix = self.xlib.XGetPixel
        pixels = [pix(get_pix(ximage, x, y))
                  for y in range(height) for x in range(width)]
        self.image = b''.join(pixels)
        return self.image