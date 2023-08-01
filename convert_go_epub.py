# Convert an epub from gobooks.com to a set of HTML pages that are easy to navigate

import sys, os
import re

from zipfile import ZipFile
from bs4 import BeautifulSoup
import copy # bs won't let you insert the same tag in two places: need deep copies!

if (len(sys.argv) != 2):
  sys.exit("Usage: python convert_go_epub.py filename.epub")
input_filename = sys.argv[1]

if not os.path.exists(input_filename):
  sys.exit(f'File {input_filename} does not exist')

if (len(input_filename)>5) & (input_filename[-5:] == ".epub"):
  outdir = os.path.basename(input_filename[:-5])
else:
  sys.exit(f"Filename {input_filename} isn't of the form something.epub")

if os.path.exists(outdir):
  sys.exit(f"Output location {outdir} already exists")
print(f"Creating output in {outdir}")
os.mkdir(outdir)
with ZipFile(input_filename, 'r') as zObject:
  zObject.extractall(path=outdir)

manifest_file = outdir + "/OPS/book.opf"
with open(manifest_file) as fp:
  soup = BeautifulSoup(fp, 'html.parser')

manifest = soup.find('manifest')
itemlist = manifest.findAll('item')
# The manifest contains all pages, not necessarily in reading order, plus other assets.
# Each manifest item has an id and an href.  The href is the filename of the xhtml.

spine = soup.find('spine')
idlist = [i.attrs["idref"] for i in spine.findAll('itemref')]
# The spine contains the ids (but not filenames) of all pages in reading order

long_idlist = [i.attrs["id"] for i in itemlist]
long_hreflist = [i.attrs["href"] for i in itemlist]
id_to_href = dict(zip(long_idlist, long_hreflist))

def id_to_filename(pageid):
# This is *.html for the converted page, not *.xhtml for the original!
  oldname = id_to_href[pageid]
  return(oldname[:-5] + oldname[-4:])

def prev_page(pageid):
  n = idlist.index(pageid)
  return None if n==0 else idlist[n-1]

def next_page(pageid):
  n = idlist.index(pageid)
  return None if n==len(idlist)-1 else idlist[n+1]

indexfile = open(outdir+"/index.html", 'w')
indexfile.write(f'<html><head><title>{outdir}</title></head>\n<body>\n')
indexfile.write(f'<h1>{soup.find(id="mainTitle").getText()}</h1>\n')
indexfile.write(f'<h2>{soup.find(id="creator").getText()}</h2>\n')
for p in idlist:
  indexfile.write(f'<a href=OPS/{id_to_filename(p)}>{p}</a><br>\n')
indexfile.write('</body></html>')
indexfile.close()

def convert_page(pageid):
  infile = outdir+"/OPS/"+id_to_href[pageid]
  outfile = outdir+"/OPS/"+id_to_filename(pageid)
  with open(infile) as f:
    soup = BeautifulSoup(f, 'html.parser')

  nextid = next_page(pageid)
  if nextid is not None:
    nexttag = soup.new_tag("a", href=id_to_filename(nextid))
    nexttag.string="Next"
    soup.body.insert(0, copy.copy(nexttag))
    soup.body.insert(0, " -- ")
    soup.body.append(nexttag)
    soup.body.append(" -- ")

  uptag = soup.new_tag("a", href="../index.html")
  uptag.string = "Up"
  soup.body.insert(0, copy.copy(uptag))
  soup.body.insert(0, " -- ")
  soup.body.append(uptag)
  soup.body.append(" -- ")

  previd = prev_page(pageid)
  if previd is not None:
    prevtag = soup.new_tag("a", href=id_to_filename(previd))
    prevtag.string="Prev"
    soup.body.insert(0, copy.copy(prevtag))
    soup.body.append(prevtag)

  # Reduce images to half size and make them resizable
  for imgtag in soup.findAll("svg"):
    boxstring = imgtag.attrs["viewbox"] # viewBox in original HTML, but bs converts to lower case and is case sensitive!
    # boxstring should be of the form "0 0 m n" where m and n are whole numbers
    x, y = boxstring.split()[2:]
    xhalf = int(x)*2 # to make the image half size, you need to double the viewbox size
    yhalf = int(y)*2
    imgtag["viewbox"] = f'0 0 {xhalf} {yhalf}'
    imgtag["width"] = str(xhalf)
    imgtag["height"] = str(yhalf)

  # Fix internal hyperlinks to point to the edited pages not the original
  for reftag in soup.findAll("a"):
    reftag["href"] = reftag["href"].replace(".xhtml", ".html")

  with open(outfile, 'w') as f:
    f.write(str(soup))

  # Clean up unwanted old files
  os.remove(infile)


for p in idlist:
  convert_page(p)

cssfile = outdir+"/OPS/css/style.css"
with open(cssfile, 'r') as f:
  css = f.read()
css = re.sub('^p {.*',
             'p { line-height: 1.3em !important; width: 50%; margin: 0 auto; }',
             css, flags=re.MULTILINE) # need flags so that ^ will match start of line
css = re.sub('page-break-before: always', 'padding-top: 1000px', css)
with open(cssfile, 'w') as f:
  f.write(css)

