#!/bin/sh
# You can pass either the path to allwpilib or the actual include path.
if [ -e $1/nivision.h ]; then
    HDRPATH=$1
elif [ -e $1/wpilibc/wpilibC++Devices/include/nivision.h ]; then
    HDRPATH=$1/wpilibc/wpilibC++Devices/include
else
    echo "Usage: $0 <path to nivision.h>"
    exit 1
fi

python3 gen_wrap.py ${HDRPATH}/nivision.h nivision_2011.ini ${HDRPATH}/NIIMAQdx.h imaqdx.ini
