"""
Converts a PDB into a modified PDB format, where the atom type for each atom is indicated
This reduced PDB is what is understood by ATTRACT.
These atoms are parsed from the trans files and topology files derived from the OPLS forcefield
"""
import sys, os
import parse_cns_top 
from pdbcomplete import pdbcomplete, run_pdb2pqr, run_whatif, pdbfix, update_patches, pdb_lastresort

has_argparse = False
try:
  import argparse  
  has_argparse = True  
except ImportError:
  import optparse  #Python 2.6

#Mapping of nucleic-acid codes to DNA/RNA
mapnuc = {
  "A": ["DA", "RA"],
  "ADE": ["DA", "RA"],
  "C": ["DC", "RC"],
  "CYT": ["DC", "RC"],
  "G": ["DG", "RG"],
  "GUA": ["DG", "RG"],
  "T": ["DT", None],
  "THY": ["DT", None],
  "U": [None, "RU"],
  "URA": [None, "RU"],
  "URI": [None, "RU"],  
} 
mapnucrev = {
  "DA":"A",
  "RA":"A",
  "DC":"C",
  "RC":"C",
  "DG":"G",
  "RG":"G",
  "DT":"T",
  "RU":"U",
}  
class PDBres:
  def __init__(self, chain, resid, resname, topology):
    self.chain = chain
    self.resid = resid
    self.resname = resname
    self.coords = {} 
    self.nter = False    
    self.cter = False
    self.topology = topology

code_to_type = {}
def parse_transfile(transfile, topname):
  for l in open(transfile):
    ll = l.split()
    type = int(ll[0])
    for code in ll[3:]:
      if code.startswith("#"): break
      assert (code, topname) not in code_to_type, code
      code_to_type[code, topname] = type


def read_pdb(pdblines, add_termini=False):
  repl = (
    ("H","HN"),
    ("HT1","HN"),
    ("OP1","O1P"),
    ("OP2","O2P"),
  )
  topres, toppatch = parse_cns_top.residues, parse_cns_top.presidues
  pdbres = []
  curr_res = None
  for l in pdblines:
    if l.startswith("ATOM"):
      atomcode = l[12:16].strip()
      assert l[16] == " ", l
      resname = l[17:20].strip()
      if resname in mapnuc:
        if args.dna: 
          resname = mapnuc[resname][0]
        elif args.rna:
          resname = mapnuc[resname][1]
        else:
          raise ValueError("PDB contains a nucleic acid named \"%s\", but it could be either RNA or DNA. Please specify the --dna or --rna option" % resname)      
        
        if resname is None:
          if args.dna: na = "DNA"
          if args.rna: na = "RNA"
          raise ValueError("'%s' can't be %s" % (l[17:20].strip(), na))      
      chain = l[21]
      resid = int(l[22:27])
      x = float(l[30:38])
      y = float(l[38:46])
      z = float(l[46:54])
      newres = False
      nter = False
      if curr_res is None:
        newres = True
        if add_termini: nter = True
      elif chain != curr_res.chain:
        newres = True
        if add_termini: 
          nter = True
          curr_res.cter = True 
      elif resid != curr_res.resid or resname != curr_res.resname:
        newres = True
      if newres:  
        try:
          if resname is None: raise KeyError
          topr = topres[resname.lower()].copy()
        except KeyError:
          raise KeyError("Residue type %s not known by the topology file" % resname)            
        curr_res = PDBres(chain, resid, resname, topr)        
        if nter: curr_res.nter = True
        pdbres.append(curr_res)
      curr_res.coords[atomcode] = (x,y,z)
      for pin, pout in repl:
        if atomcode != pin: continue
        curr_res.coords[pout] = (x,y,z)
  if add_termini: 
    curr_res.cter = True    
  return pdbres

def termini_pdb(pdbres, nter, cter):
  xter = nter, cter
  for n in range(2):
    ter = xter[n]
    for resnr in ter:
      r = [res for res in pdbres if res.resid == resnr]
      if len(r) == 0:
        raise ValueError("Cannot find residue %d" % resnr)
      elif len(r) > 1:
        raise ValueError("Multiple residues %d" % resnr)
      res = r[0]
      if n == 0: res.nter = True
      else: res.cter = True
      
def patch_pdb(pdbres, patches):
  topres, toppatch = parse_cns_top.residues, parse_cns_top.presidues
  for res in pdbres:
    if res.resid in patches:
      for p in patches[res.resid]:
        if p is None: continue
        res.topology.patch(toppatch[p])
    elif len(pdbres) > 1 and "ca" in res.topology.atomorder: #protein
      if res.nter:
        if res.resname == "PRO":
          res.topology.patch(toppatch["prop"])
        else:  
          res.topology.patch(toppatch["nter"])
      if res.cter:
        res.topology.patch(toppatch["cter2"])
    elif len(pdbres) > 1 and "p" in res.topology.atomorder: #DNA/RNA
      if res.nter:
        res.topology.patch(toppatch["5ter"])
      if res.cter:
        res.topology.patch(toppatch["3ter"])

def check_pdb(pdbres, heavy=False):
  for res in pdbres:
    top = res.topology
    for a in top.atomorder: 
      atom = top.atoms[a]
      if a.lower().startswith("h"):
        if heavy: continue
        if atom.charge == 0: continue            
      aa = a.upper()
      if aa.strip() not in res.coords:
        raise ValueError('Missing coordinates for atom "%s" in residue %s %s%s' % (aa.strip(), res.resname, res.chain, res.resid))

def write_pdb(pdbres, heavy = False, one_letter_na = False):
  pdblines = []
  mapping = []
  atomcounter = 1
  rescounter = 1
  for res in pdbres:
    top = res.topology
    for a in top.atomorder: 
      atom = top.atoms[a]
      if a.lower().startswith("h"):
        if heavy: continue
        if atom.charge == 0: continue            
      aa = a.upper()
      x = " XXXXXXX"
      y = x; z = x
      if aa.strip() in res.coords:
        x,y,z = ("%8.3f" % v for v in res.coords[aa.strip()])
      xyz = x + y + z
      type = code_to_type[atom.type.upper(), top.topname]
      a0 = aa
      if len(a0) < 4:
        a0 = " " + a0 + "   "[len(a0):]
      resname = res.resname
      if one_letter_na and resname in mapnucrev:
        resname = mapnucrev[resname]
      pdblines.append("ATOM %6d %4s %s %5d    %s %4d %7.3f 0 1.00" % \
       (atomcounter, a0, resname, rescounter, xyz, type, atom.charge))
      atomcounter += 1
    mapping.append((res.resid, rescounter))
    rescounter += 1
  return pdblines, mapping

def set_reference(pdbres, pdbreferes):
  if len(pdbres) != len(pdbreferes):
    raise ValueError("PDB and reference do not have the same number of residues, %d vs %s" % (len(pdbres), len(pdbreferes)))
  for n in range(len(pdbres)):
    pdbr, refr = pdbres[n], pdbreferes[n]
    if pdbr.resname != refr.resname:
      rsid = pdbr.resid
      if refr.resid != pdbr.resid: rsid = "%d(%d)" % (pdbr.resid, refr.resid)
      raise ValueError("PDB and reference are different at resid %s: %s vs %s" % (rsid, pdbr.resname, refr.resname))
    pdbr.nter = refr.nter
    pdbr.cter = refr.cter 
    pdbr.topology = refr.topology

currdir = os.path.abspath(os.path.split(__file__)[0])
topstream = [(currdir + "/topallhdg5.3.pro", "oplsx"),
             (currdir + "/dna-rna-allatom.top", "dna-rna")
            ]
transfiles = [(currdir + "/oplsx.trans", "oplsx"), 
              (currdir + "/dna-rna.trans", "dna-rna")
             ] 

if has_argparse:
  parser = argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("pdb",help="PDB file to reduce")
  parser.add_argument("output",help="all-atom reduced output PDB file", nargs="?")
else:
  parser = optparse.OptionParser()
  parser.add_argument = parser.add_option

parser.add_argument("--heavy",help="Ignore all hydrogens", action="store_true")
parser.add_argument("--refe",help="Analyze the hydrogens of a reference file to determine histidine/cysteine states")
parser.add_argument("--autorefe",help="Analyze the hydrogens of the input PDB to determine histidine/cysteine states", action="store_true")
parser.add_argument("--dna",help="Automatically interpret nucleic acids as DNA", action="store_true")
parser.add_argument("--rna",help="Automatically interpret nucleic acids as RNA", action="store_true")
parser.add_argument("--pdb2pqr",help="Use PDB2PQR to complete missing atoms. If no reference has been specified, analyze the hydrogens to determine histidine/cysteine states", action="store_true")
parser.add_argument("--whatif",help="Use the WHATIF server to complete missing atoms. If no reference has been specified, analyze the hydrogens to determine histidine/cysteine states", action="store_true")
parser.add_argument("--termini",help="An N-terminus and a C-terminus (5-terminus and 3-terminus for nucleic acids) will be added for each chain", action="store_true")
parser.add_argument("--nter", "--nterm" , dest="nter",
                    help="Add an N-terminus (5-terminus for nucleic acids) for the specified residue number", action="append", 
                    type=int, default=[])
parser.add_argument("--cter","--cterm", dest="cter",
                    help="Add a C-terminus (3-terminus for nucleic acids) for the specified residue number", action="append", 
                    type=int, default=[])
parser.add_argument("--manual",help="""Enables manual mode. 
In automatic mode (default), aareduce tries to produce a PDB file that can be used directly by ATTRACT. In case of missing atoms, a number of 
last-resort fixes are attempted that add pseudo-hydrogens at the position of its connected heavy atom. If there are other missing atoms,
an exception is raised.
In manual mode, last-resort fixes are disabled, and missing atoms are simply printed as XXXXXXX in their coordinates. These coordinates
cannot be read by ATTRACT, they need to be edited manually by the user.
""", action="store_true")
parser.add_argument("--transfile",help="Additional trans file that contains additional user-defined atom types (e.g. modified amino acids)", action="append",default=[])
parser.add_argument("--topfile",help="Additional topology file in CNS format that contains additional user-defined atom types (e.g. modified amino acids)", action="append",default=[])
parser.add_argument("--patch",dest="patches",
                    help="Provide residue number and patch name to apply", nargs=2, action="append",default=[])

if has_argparse:
  args = parser.parse_args()
else:
  args, positional_args = parser.parse_args()
  args.pdb = None
  args.output = None
  if positional_args:
    args.pdb = positional_args[0]
    if len(positional_args) > 1: args.output = positional_args[1]

if args.heavy and (args.autorefe or args.refe):
  raise ValueError("--(auto)refe and --heavy are mutually incompatible")

if args.autorefe and args.refe:
  raise ValueError("--autorefe and --refe are mutually incompatible")
if args.autorefe: 
  args.refe = args.pdb

outfile = os.path.splitext(args.pdb)[0] + "-aa.pdb"
if args.output is not None: 
  outfile = args.output

for fnr, f in enumerate(args.topfile):
  assert os.path.exists(f), f
  topstream.append((f, "userfile-%d" % (fnr+1)))
for f in args.transfile:
  transfiles.append((f, "userfile-%d" % (fnr+1)))

for f, name in topstream:
  parse_cns_top.parse_stream(open(f), name)
for f, name in transfiles:
  parse_transfile(f, name)
  
pdb = read_pdb(open(args.pdb), add_termini=args.termini)
pdblines = write_pdb(pdb)[0]

termini_pdb(pdb, args.nter, args.cter)
patches = {}
for p in args.patches:
  resnr = int(p[0])
  if resnr not in patches: patches[resnr] = []
  patches[resnr].append(p[1])
patch_pdb(pdb, patches)

if args.refe:
  refe = read_pdb(open(args.refe), add_termini=args.termini)
  patch_pdb(refe, patches)
  if not args.heavy:
    update_patches(refe)
  set_reference(pdb, refe)
if args.pdb2pqr:
  pdblines = write_pdb(pdb, one_letter_na = True)[0]
  pqrlines = run_pdb2pqr(pdblines)
  pqr = read_pdb(pqrlines)
  pdbcomplete(pdb, pqr)
  if not args.heavy and not args.refe: 
    update_patches(pdb)
if args.whatif:
  pdblines = write_pdb(pdb, one_letter_na = True)[0]
  whatiflines = run_whatif(pdblines)
  whatif = read_pdb(whatiflines)
  pdbcomplete(pdb, whatif)
  if not args.heavy and not args.refe and not args.pdb2pqr: 
    update_patches(pdb)

if args.refe:  
  pdbfix(pdb, refe)

if not args.manual: 
  pdb_lastresort(pdb)
  check_pdb(pdb, heavy=args.heavy)
pdblines, mapping = write_pdb(pdb, heavy=args.heavy)

outf = open(outfile, "w")
for l in pdblines: 
  print >> outf, l
for v1, v2 in mapping:
  print v1, v2  