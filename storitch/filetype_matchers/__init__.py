from filetype import Type, add_type

from . import m3shape_dcm

print(isinstance(m3shape_dcm.M3shapeDCM, Type))
add_type(m3shape_dcm.M3shapeDCM())