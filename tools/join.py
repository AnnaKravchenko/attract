import sys, glob
from _read_struc import read_struc

if len(sys.argv) < 2:
  print >> sys.stderr, "Usage: join.py <file pattern>"
  sys.exit()

files = glob.glob(sys.argv[1]+"-*")
nrsplit = 0
while 1:
  fnam = "%s-%d" % (sys.argv[1], nrsplit+1)
  if fnam not in files: break
  nrsplit += 1

if nrsplit == 0: 
  print >> sys.stderr, "Pattern not found"
  sys.exit()

allstructures = {}
maxstruc = 0
for n in range(nrsplit):
  fnam = "%s-%d" % (sys.argv[1], n+1)
  header0,structures = read_struc(fnam)
  if n == 0: header = header0
  currstruc = None
  currstruc_false = False
  stnr = 0  
  for s in structures:
    l1,l2 = s
    stnr += 1
    for l in l1:
      if l.startswith("### SPLIT"):
        try:
          currstruc = int(l[len("### SPLIT"):])
	except:
	  currstruc = l[len("### SPLIT"):]
	  currstruc_false = True
        break
    if currstruc is None:
      print >> sys.stderr, "Structure has no SPLIT number"
      print >> sys.stderr, fnam
      print >> sys.stderr, "#"+str(stnr)
      for l in l1: print >>sys.stderr, l  
      for l in l2: print >>sys.stderr, l
      sys.exit()
    if currstruc_false or currstruc <= 0:
      print >> sys.stderr, "Invalid SPLIT number:", currstruc
      print >> sys.stderr, fnam
      print >> sys.stderr, "#"+str(stnr)
      for l in l1: print >>sys.stderr, l  
      for l in l2: print >>sys.stderr, l
      sys.exit()
    if currstruc in allstructures:
      print >> sys.stderr, "Duplicate SPLIT number:", currstruc
      print >> sys.stderr, fnam
      print >> sys.stderr, "#"+str(stnr)
      for l in l1: print >>sys.stderr, l  
      for l in l2: print >>sys.stderr, l
      sys.exit()
    
    if currstruc > maxstruc: maxstruc = currstruc
    allstructures[currstruc] = s


for snr in range(1,maxstruc+1):
  if snr not in allstructures:
    print >> sys.stderr, "Missing SPLIT number:", snr
    sys.exit()

for h in header: print h
stnr = 0
for snr in range(1,maxstruc+1):
  s = allstructures[snr]
  stnr += 1
  l1,l2 = s
  print "#"+str(stnr)
  for l in l1: 
    if l.startswith("### SPLIT "): continue
    print l
  for l in l2: print l
