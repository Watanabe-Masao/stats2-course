import cairosvg, sys
from PIL import Image
keys=sys.argv[2:]; ims=[]
for k in keys:
    svg=open(f"{k}.svg").read().replace('font-family="sans-serif"','font-family="Noto Sans CJK JP"')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{k}.png", output_width=640); ims.append(Image.open(f"{k}.png"))
cols=2; rows=[ims[i:i+cols] for i in range(0,len(ims),cols)]
W=640*cols; H=sum(max(i.height for i in r) for r in rows)
sh=Image.new("RGB",(W,H),"white"); y=0
for r in rows:
    x=0
    for im in r: sh.paste(im,(x,y)); x+=640
    y+=max(i.height for i in r)
sh.save(sys.argv[1])
