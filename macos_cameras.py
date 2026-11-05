"""Read AVFoundation camera names in OpenCV 4.11's unique-ID order.

No capture session is created. Uses macOS frameworks through the Objective-C
runtime so a separate PyObjC install is not required.
"""
import ctypes as c
import sys


def list_cameras():
    if sys.platform != 'darwin':
        raise RuntimeError('Named camera discovery requires macOS.')
    c.CDLL('/System/Library/Frameworks/Foundation.framework/Foundation')
    av = c.CDLL('/System/Library/Frameworks/AVFoundation.framework/AVFoundation')
    objc = c.CDLL('/usr/lib/libobjc.A.dylib')
    ptr = c.c_void_p
    objc.objc_getClass.argtypes = [c.c_char_p]
    objc.objc_getClass.restype = ptr
    objc.sel_registerName.argtypes = [c.c_char_p]
    objc.sel_registerName.restype = ptr
    address = c.cast(objc.objc_msgSend, ptr).value

    def send(receiver, name, result=ptr, args=(), values=()):
        method = c.CFUNCTYPE(result, ptr, ptr, *args)(address)
        return method(receiver, objc.sel_registerName(name.encode()), *values)

    pool = send(send(objc.objc_getClass(b'NSAutoreleasePool'), 'alloc'), 'init')
    try:
        device_class = objc.objc_getClass(b'AVCaptureDevice')
        devices = []
        # Match OpenCV's video + muxed discovery and uniqueID ordering.
        for symbol in ('AVMediaTypeVideo', 'AVMediaTypeMuxed'):
            media = ptr.in_dll(av, symbol).value
            array = send(device_class, 'devicesWithMediaType:', args=(ptr,), values=(media,))
            count = send(array, 'count', result=c.c_ulong)
            for i in range(count):
                device = send(array, 'objectAtIndex:', args=(c.c_ulong,), values=(i,))
                def string(property_name):
                    value = send(device, property_name)
                    raw = send(value, 'UTF8String', result=c.c_char_p)
                    return raw.decode('utf-8') if raw else ''
                devices.append({'name': string('localizedName'), 'id': string('uniqueID')})
        devices.sort(key=lambda device: device['id'])
        return [dict(device, index=i) for i, device in enumerate(devices)]
    finally:
        send(pool, 'drain', result=None)


if __name__ == '__main__':
    import json
    print(json.dumps(list_cameras(), indent=2))
