#!/usr/bin/env python3
import core as nivision
import sys

def main(name):
    id = nivision.IMAQdxOpenCamera(name, nivision.IMAQdxCameraControlModeController)

    print("Enumerating...", file=sys.stderr, flush=True)
    modes, currentMode = nivision.IMAQdxEnumerateVideoModes(id)
    simple_attrs = nivision.IMAQdxEnumerateAttributes3(id, b"", nivision.IMAQdxAttributeVisibilitySimple)
    intermediate_attrs = nivision.IMAQdxEnumerateAttributes3(id, b"", nivision.IMAQdxAttributeVisibilityIntermediate)
    advanced_attrs = nivision.IMAQdxEnumerateAttributes3(id, b"", nivision.IMAQdxAttributeVisibilityAdvanced)
    print("Current mode = %d" % currentMode.value)
    print("Available Modes:")
    for mode in modes:
        print(" %d: %s" % (mode.Value, mode.Name))
    seen_attrs = set()
    for attrs_name, attrs in [("Simple", simple_attrs),
                              ("Intermediate", intermediate_attrs),
                              ("Advanced", advanced_attrs)]:
        print("%s Attributes:" % attrs_name)
        for attr in attrs:
            if attr.Name in seen_attrs:
                continue
            seen_attrs.add(attr.Name)
            if attr.Type == nivision.IMAQdxAttributeTypeU32:
                atype = "U32"
            elif attr.Type == nivision.IMAQdxAttributeTypeI64:
                atype = "I64"
            elif attr.Type == nivision.IMAQdxAttributeTypeF64:
                atype = "F64"
            elif attr.Type == nivision.IMAQdxAttributeTypeString:
                atype = "String"
            elif attr.Type == nivision.IMAQdxAttributeTypeEnum:
                atype = "Enum"
            elif attr.Type == nivision.IMAQdxAttributeTypeBool:
                atype = "Bool"
            elif attr.Type == nivision.IMAQdxAttributeTypeCommand:
                atype = "Command"
            elif attr.Type == nivision.IMAQdxAttributeTypeBlob:
                atype = "Blob"
            else:
                atype = "Unknown (%d)" % attr.Type.value
                value = ""
            if not atype.startswith("Unknown"):
                value = nivision.IMAQdxGetAttribute(id, attr.Name)
                if attr.Type == nivision.IMAQdxAttributeTypeEnum:
                    value = "%d (%s)" % (value.Value, value.Name)
            print(" %s (%s%s - %s) = %s" % (attr.Name, "R" if attr.Readable else " ",
                                       "W" if attr.Writable else " ",
                                       atype, value))
            if attr.Type == nivision.IMAQdxAttributeTypeEnum:
                print("  Values:")
                values = nivision.IMAQdxEnumerateAttributeValues(id, attr.Name)
                for value in values:
                    print("   %d: %s" % (value.Value, value.Name))
            if attr.Type in (nivision.IMAQdxAttributeTypeU32, nivision.IMAQdxAttributeTypeI64):
                mini = nivision.IMAQdxGetAttributeMinimum(id, attr.Name)
                maxi = nivision.IMAQdxGetAttributeMaximum(id, attr.Name)
                incr = nivision.IMAQdxGetAttributeIncrement(id, attr.Name)
                print("  Min, Max, Incr: %d, %d, %d" % (mini, maxi, incr))
            if attr.Type == nivision.IMAQdxAttributeTypeF64:
                mini = nivision.IMAQdxGetAttributeMinimum(id, attr.Name)
                maxi = nivision.IMAQdxGetAttributeMaximum(id, attr.Name)
                incr = nivision.IMAQdxGetAttributeIncrement(id, attr.Name)
                print("  Min, Max, Incr: %f, %f, %f" % (mini, maxi, incr))

    nivision.IMAQdxCloseCamera(id)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: caminfo.py [cam#]")
        sys.exit(1)
    if len(sys.argv) == 2:
        main(sys.argv[1].encode('utf-8'))
    else:
        print("Enumerating...", file=sys.stderr, flush=True)
        cameras = nivision.IMAQdxEnumerateCameras(1)
        for n, camera in enumerate(cameras):
            print("Camera %d:" % n)
            print(" Type: %d" % camera.Type)
            print(" Version: %d" % camera.Version)
            flags = []
            if (camera.Flags & nivision.IMAQdxInterfaceFileFlagsConnected.value) != 0:
                flags.append("Connected")
            if (camera.Flags & nivision.IMAQdxInterfaceFileFlagsDirty.value) != 0:
                flags.append("Dirty")
            print(" Flags: %d (%s)" % (camera.Flags, ", ".join(flags)))
            print(" SerialNumberHi: 0x%08x" % camera.SerialNumberHi)
            print(" SerialNumberLo: 0x%08x" % camera.SerialNumberLo)
            if camera.BusType == nivision.IMAQdxBusTypeFireWire:
                bustype = "FireWire"
            elif camera.BusType == nivision.IMAQdxBusTypeEthernet:
                bustype = "Ethernet"
            elif camera.BusType == nivision.IMAQdxBusTypeSimulator:
                bustype = "Simulator"
            elif camera.BusType == nivision.IMAQdxBusTypeDirectShow:
                bustype = "DirectShow"
            elif camera.BusType == nivision.IMAQdxBusTypeIP:
                bustype = "IP"
            elif camera.BusType == nivision.IMAQdxBusTypeSmartCam2:
                bustype = "SmartCam2"
            elif camera.BusType == nivision.IMAQdxBusTypeUSB3Vision:
                bustype = "USB3Vision"
            elif camera.BusType == nivision.IMAQdxBusTypeUVC:
                bustype = "UVC"
            else:
                bustype = "0x%08x" % camera.BusType.value
            print(" BusType: %s" % bustype)
            print(" InterfaceName: %s" % camera.InterfaceName)
            print(" VendorName: %s" % camera.VendorName)
            print(" ModelName: %s" % camera.ModelName)
            print(" CameraFileName: %s" % camera.CameraFileName)
            print(" CameraAttributeURL: %s" % camera.CameraAttributeURL)

