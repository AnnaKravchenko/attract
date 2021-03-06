# Copyright 2007-2011, Sjoerd de Vries
# This file is part of the Spyder module: "core" 
# For licensing information, see LICENSE.txt 

import os, functools
import spyder

def generate_class(typename,parentnames, source, members, deleted_members, block):
  reservednames = ("Spyder", "Exception", "Type", "Delete", "None", "True", "False")
  if (not typename[0].isupper()) or typename.endswith("Error") or typename.endswith("Array") or typename in reservednames:
    raise Exception("compile error: illegal typename for type %s" % typename)
  if block != None: raise Exception
  if len(parentnames):
     s = '\nclass %s(%s):\n  \"\"\"%s\"\"\"\n' % (typename, ",".join(parentnames), source.replace('"""', '\\\"\\\"\\\"'))
  else: s ='\nclass %s(Object):\n  \"\"\"%s\"\"\"\n' % (typename, source.replace('"""', '\\\"\\\"\\\"'))
  
  s += """  
  @staticmethod
  def typename():
    \"\"\"Auto-generated by Spyder:
     module core
     file class.py
     function generate_class
    Return the class name of the current object\"\"\"
    return "%s"
""" % typename
  s += """  def cast(self, othertype):
    \"\"\"Auto-generated by Spyder:
     module core
     file class.py
     function generate_class
    Return an object of the type "othertype" initialized from this object\"\"\"
    if type(othertype) == type(int): return othertype(self)    
    return globals()[othertype](self)
"""
  return s, None

def generate_endclass(typename, parentnames, source, members, deleted_members, block, endclass):
  requiredmembers, defaultmembers, optionalmembers, args, allargs = spyder.core.parse_members(typename,members,None, spyder.safe_eval)
  single = None
  s = ""
  if block != None:
    s += block  
  if len(requiredmembers) == 0:
    if len(optionalmembers) > 0:
      single = optionalmembers[0]
  elif len(requiredmembers) == 1:  
    single = requiredmembers[0][1]
  if single is not None:
    msingle = [m for m in requiredmembers+defaultmembers if m[1] == single][0]    
    singletyp = msingle[0]    
    s += "if issubclass(%s,Spyder.String) or issubclass(%s,Spyder.Data):\n" % (singletyp, singletyp)
    s += "  if not issubclass(%s,getattr(Spyder,\"Degenerate\")):\n" % typename
    s += "    raise TypeError(\"Spyder type '%s' is degenerate: it has no more than one required member, and the first member can be constructed from a string.\\nPlease change the members, or inherit explicitly from Spyder.Degenerate\")\n" % typename
  s += "spyder.__types__[\"%s\"] = %s\n" % (typename, typename)
  s += "spyder.core.error[\"%s\"] = {}\n" % typename
  s += "if hasattr(%s, '_register_errors'): %s._register_errors()\n" % (typename, typename)
  s += "%s._requiredmembers = %s\n" % (typename, repr(requiredmembers))
  s += "%s._defaultmembers = %s\n" % (typename, repr(defaultmembers))
  s += "%s.__form__()\n" % typename
  s += "%s = spyder.__types__[\"_Resource\"](%s)\n" % ("Resource"+typename, typename)

  
  s += """
%s.empty = functools.partial(spyder.__constructor, 
  "constructor_empty",
  %s,
  "constructor_fromany",
)
%s.fromlist = functools.partial(spyder.__constructor, 
  "constructor_fromlist",
  %s,
  "constructor_fromany",
)
%s.fromdict = functools.partial(spyder.__constructor, 
  "constructor_fromdict",
  %s,
  "constructor_fromany",
)
""" % (typename,typename,typename,typename,typename,typename)
  
  s += "\n"
  #generate Array
  cast = """  def cast(self, othertype):
    if type(othertype) == type: return othertype(self)
    return globals()[othertype](self)
"""    
  for n in range(spyder.arraymax):
    classname = typename + (n+1) * "Array"
    prevclassname = typename + n * "Array"
    rclassname = "Resource"+classname
    d = dict(typename=typename,classname=classname,prevclassname=prevclassname,rclassname=rclassname)
    s += 'class %s(spyder.core.spyderlist):\n' % classname
    s += '  @staticmethod\n  def typename(): return "%s"\n' % classname 
    for b in endclass:
      if endclass[b] != None:
        s += endclass[b].replace("\\\"\\\"\\\"", '"""')  % d + "\n"
    s += """    
spyder.core.defineconverter(\"%(classname)s\",\"%(prevclassname)s\","SPLIT")
spyder.core.defineconverter(\"%(prevclassname)s\",\"%(classname)s\","CAST")
spyder.__types__[\"%(classname)s\"] = globals()[\"%(classname)s\"]  
arrayclass = spyder.__types__[\"%(classname)s\"]
spyder.__types__[\"%(rclassname)s\"] = spyder.__types__["_Resource"](arrayclass)
arrayclass.empty = functools.partial(spyder.__constructor, 
"constructor_empty",
arrayclass,
"constructor_fromany",
)
arrayclass.fromlist = functools.partial(spyder.__constructor, 
"constructor_fromlist",
arrayclass,
"constructor_fromany",
)
arrayclass.fromdict = functools.partial(spyder.__constructor, 
"constructor_fromdict",
arrayclass,
"constructor_fromany",
)
arrayclass.__form__()
""" % d
  
  return s

spyder.defineunimethod("__class", generate_class)
spyder.defineunimethod("__endclass", generate_endclass)
