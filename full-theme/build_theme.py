from pathlib import Path
import io, struct
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent
CORE=ROOT.parent/'core-drafts'
OUT=ROOT/'cursors'; PRE=ROOT/'preview'
OUT.mkdir(exist_ok=True); PRE.mkdir(exist_ok=True)

def load_core(name):
    return Image.open(CORE/f'{name}-high.png').convert('RGBA')

def paw(master, size=64):
    im=master.copy(); box=im.getchannel('A').getbbox(); im=im.crop(box)
    scale=min(size*.94/im.width,size*.94/im.height)
    im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
    out=Image.new('RGBA',(size,size)); out.alpha_composite(im,(1,1)); return out

normal=paw(load_core('normal')); hover=paw(load_core('hover')); click=paw(load_core('click')); drag=paw(load_core('drag'))

def shift(im,dx=0,dy=0):
    out=Image.new('RGBA',im.size); out.alpha_composite(im,(dx,dy)); return out

def working_frame(i):
    im=shift(hover,(0,0,1,1)[i],(0,-1,-1,0)[i]); d=ImageDraw.Draw(im)
    d.arc((38,4,61,27),185+i*15,290+i*15,fill=(106,115,126,220),width=2)
    return im

def busy_frame(i):
    im=shift(click,(0,1,1,0)[i],(0,-2,0,1)[i]); d=ImageDraw.Draw(im)
    d.arc((36,3,62,29),190+i*18,315+i*18,fill=(78,86,98,230),width=2)
    d.arc((42,9,58,25),210+i*18,300+i*18,fill=(145,151,160,180),width=2)
    return im

def unavailable():
    im=normal.copy(); d=ImageDraw.Draw(im); d.ellipse((47,47,62,62),fill=(247,247,247,245),outline=(65,67,76,255),width=2); d.line((50,50,59,59),fill=(145,82,91,255),width=2); d.line((59,50,50,59),fill=(145,82,91,255),width=2); return im

def text_select():
    im=Image.new('RGBA',(64,64)); d=ImageDraw.Draw(im); dark=(65,67,76,255)
    d.rectangle((30,10,34,54),fill=dark); d.rectangle((23,10,41,14),fill=dark); d.rectangle((23,50,41,54),fill=dark)
    small=paw(normal,26); im.alpha_composite(small,(34,34)); return im

def standard(kind):
    im=Image.new('RGBA',(64,64)); d=ImageDraw.Draw(im); dark=(65,67,76,255); gray=(151,158,166,255); white=(247,247,247,255)
    if kind=='hresize':
        d.line((9,32,55,32),fill=dark,width=5); d.polygon([(4,32),(17,21),(17,43)],fill=dark); d.polygon([(60,32),(47,21),(47,43)],fill=dark)
    elif kind=='vresize':
        d.line((32,9,32,55),fill=dark,width=5); d.polygon([(32,4),(21,17),(43,17)],fill=dark); d.polygon([(32,60),(21,47),(43,47)],fill=dark)
    elif kind=='diag1':
        d.line((11,53,53,11),fill=dark,width=5); d.polygon([(5,59),(22,56),(8,42)],fill=dark); d.polygon([(59,5),(42,8),(56,22)],fill=dark)
    elif kind=='diag2':
        d.line((11,11,53,53),fill=dark,width=5); d.polygon([(5,5),(8,22),(22,8)],fill=dark); d.polygon([(59,59),(42,56),(56,42)],fill=dark)
    elif kind=='precision':
        d.ellipse((12,12,52,52),outline=dark,width=4); d.line((32,3,32,61),fill=dark,width=3); d.line((3,32,61,32),fill=dark,width=3); d.ellipse((26,26,38,38),fill=gray,outline=dark,width=2); return im
    elif kind=='up':
        d.line((32,57,32,13),fill=dark,width=5); d.polygon([(32,5),(19,21),(45,21)],fill=dark); return im
    elif kind=='help':
        im.alpha_composite(hover,(0,0)); d=ImageDraw.Draw(im); d.ellipse((49,49,62,62),fill=white,outline=dark,width=2); d.text((53,49),'?',fill=dark,font=ImageFont.load_default()); return im
    elif kind=='pen':
        im.alpha_composite(normal,(0,0)); d=ImageDraw.Draw(im); d.line((51,10,59,18),fill=dark,width=2); d.polygon([(49,9),(60,20),(56,24),(45,13)],outline=dark,fill=gray); return im
    d.ellipse((25,25,39,39),fill=gray,outline=dark,width=3); return im

def png(im):
    b=io.BytesIO(); im.save(b,'PNG'); return b.getvalue()

def cur_bytes(im,hot=(1,1)):
    data=png(im); w,h=im.size; return struct.pack('<HHH',0,2,1)+struct.pack('<BBBBHHII',w,h,0,0,hot[0],hot[1],len(data),22)+data

def write_cur(path, im, hot=(1,1)):
    # A practical 64px cursor with the stable upper-left hotspot.
    path.write_bytes(cur_bytes(im,hot))

def write_ani(path, frames, rate=8):
    anih=struct.pack('<IIIIIIII',36,len(frames),len(frames),0,32,1,rate,0)
    def chunk(tag,data): return tag+struct.pack('<I',len(data))+data+(b'\0' if len(data)%2 else b'')
    body=chunk(b'anih',anih)+chunk(b'rate',struct.pack('<'+'I'*len(frames),*([rate]*len(frames))))+chunk(b'LIST',b'fram'+b''.join(chunk(b'icon',cur_bytes(f)) for f in frames))
    path.write_bytes(b'RIFF'+struct.pack('<I',len(body)+4)+b'ACON'+body)

static={
    'normal':normal,'link':hover,'click':click,'move':drag,'unavailable':unavailable(),
    'text':text_select(),'hresize':standard('hresize'),'vresize':standard('vresize'),
    'diag1':standard('diag1'),'diag2':standard('diag2'),'precision':standard('precision'),
    'up':standard('up'),'help':standard('help'),'pen':standard('pen')}

def high_preview(name, fallback):
    masters={'normal':'normal','link':'hover','click':'click','move':'drag'}
    if name not in masters: return fallback
    im=load_core(masters[name]); box=im.getchannel('A').getbbox(); im=im.crop(box)
    scale=min(256/im.width,256/im.height); im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
    out=Image.new('RGBA',(256,256)); out.alpha_composite(im,((256-im.width)//2,(256-im.height)//2)); return out

def high_text_preview():
    im=high_preview('normal',normal); d=ImageDraw.Draw(im); dark=(65,67,76,255)
    # Compact I-beam beside the already locked high-resolution paw.
    d.rectangle((127,36,133,214),fill=dark); d.rectangle((101,36,159,47),fill=dark); d.rectangle((101,203,159,214),fill=dark)
    return im

def high_badge_preview(master_name, kind):
    im=high_preview(master_name,normal); d=ImageDraw.Draw(im); dark=(65,67,76,255); white=(247,247,247,245)
    if kind=='unavailable':
        d.ellipse((212,212,251,251),fill=white,outline=dark,width=4); d.line((220,220,244,244),fill=(145,82,91,255),width=4); d.line((244,220,220,244),fill=(145,82,91,255),width=4)
    elif kind=='help':
        d.ellipse((222,222,251,251),fill=white,outline=dark,width=3); d.text((232,222),'?',fill=dark,font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22) if Path('C:/Windows/Fonts/arial.ttf').exists() else ImageFont.load_default())
    return im

def high_pen_preview():
    im=high_preview('normal',normal); d=ImageDraw.Draw(im); dark=(65,67,76,255); gray=(151,158,166,255)
    d.line((216,36,244,64),fill=dark,width=4); d.polygon([(209,31),(249,71),(237,83),(197,43)],outline=dark,fill=gray,width=3)
    return im

for name,im in static.items():
    write_cur(OUT/f'{name}.cur',im,(1,1)); im.resize((256,256),Image.Resampling.NEAREST).save(PRE/f'{name}.png')
    high_preview(name,im).save(PRE/f'{name}.png')
high_text_preview().save(PRE/'text.png'); high_badge_preview('normal','unavailable').save(PRE/'unavailable.png'); high_badge_preview('link','help').save(PRE/'help.png'); high_pen_preview().save(PRE/'pen.png')
working=[working_frame(i) for i in range(4)]; busy=[busy_frame(i) for i in range(4)]
write_ani(OUT/'working-in-background.ani',working); write_ani(OUT/'busy.ani',busy)
write_ani(OUT/'move.ani',[shift(drag,0,0),shift(drag,1,-1),shift(drag,0,0)])
work_hi=high_preview('link',hover); dw=ImageDraw.Draw(work_hi); dw.arc((150,15,245,110),185,290,fill=(106,115,126,220),width=5); dw.arc((175,35,245,105),195,285,fill=(125,132,142,150),width=4)
busy_hi=high_preview('click',click); db=ImageDraw.Draw(busy_hi); db.arc((145,12,248,115),190,315,fill=(78,86,98,230),width=5); db.arc((170,32,235,100),210,300,fill=(145,151,160,180),width=4)
work_hi.save(PRE/'working.png'); busy_hi.save(PRE/'busy.png')

try: font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',28); small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
except OSError: font=small=ImageFont.load_default()
items=[('normal','普通选择'),('link','链接/悬停'),('click','点击'),('move','移动/拖拽'),('text','文字输入'),('working','后台工作'),('busy','忙碌中'),('unavailable','不可用'),('hresize','水平调整'),('vresize','垂直调整'),('diag1','对角调整1'),('diag2','对角调整2'),('precision','精确选择'),('help','帮助选择'),('up','向上选择'),('pen','手写笔')]
sheet=Image.new('RGBA',(1800,1500),(248,247,249,255)); d=ImageDraw.Draw(sheet); d.text((45,30),'小狗前爪 Windows 鼠标指针主题 · 完整版',fill=(35,35,40,255),font=font)
for i,(name,label) in enumerate(items):
    x=45+(i%4)*435; y=95+(i//4)*340; im=Image.open(PRE/(name+'.png')).resize((240,240),Image.Resampling.LANCZOS); sheet.alpha_composite(im,(x,y)); d.text((x,y+255),label,fill=(35,35,40,255),font=small)
sheet.convert('RGB').save(PRE/'overview-full.png',quality=96)
print('created full theme:',len(static),'static cursors and 3 animated cursors')
