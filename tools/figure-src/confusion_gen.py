import math, random
W,H=640,280
BL='#2a78d6';OR='#eb6834';RD='#e34948';GR='#8a8984';INK='#1f1f1d';INK2='#5c5b57';GD='#e4e3df';MU='#b9c9de';AQ='#1baf7a'
def head(h=H):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" font-family="Hiragino Sans,Noto Sans JP,Yu Gothic,sans-serif"><rect width="{W}" height="{h}" fill="#ffffff"/>'
def T(x,y,s,fs=13,c=INK,a='middle',b=False):
    return f'<text x="{x:.0f}" y="{y:.0f}" font-size="{fs}" fill="{c}" text-anchor="{a}"{" font-weight=\"700\"" if b else ""}>{s}</text>'
def L(x1,y1,x2,y2,c=INK2,w=1.5,d=None):
    return f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{c}" stroke-width="{w}"{f" stroke-dasharray=\"{d}\"" if d else ""}/>'
def C(x,y,r,c,op=1,st=None):
    return f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{c}" fill-opacity="{op}"{f" stroke=\"{st}\" stroke-width=\"1.5\"" if st else ""}/>'
def R(x,y,w,h,c,op=1,rx=3,st=None):
    return f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{c}" fill-opacity="{op}"{f" stroke=\"{st}\" stroke-width=\"1.5\"" if st else ""}/>'
def poly(pts,c,w=2,fill='none',op=1,d=None):
    s=' '.join(f'{x:.0f},{y:.0f}' for x,y in pts)
    if fill!='none': return f'<polygon points="{s}" fill="{fill}" fill-opacity="{op}"/>'
    return f'<polyline points="{s}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round"{f" stroke-dasharray=\"{d}\"" if d else ""}/>'
def arrow(x1,y1,x2,y2,c=INK2,w=2,d=None):
    a=math.atan2(y2-y1,x2-x1);s=9
    p1=(x2-s*math.cos(a-0.4),y2-s*math.sin(a-0.4));p2=(x2-s*math.cos(a+0.4),y2-s*math.sin(a+0.4))
    return L(x1,y1,x2-4*math.cos(a),y2-4*math.sin(a),c,w,d)+poly([(x2,y2),p1,p2],c,fill=c)
npdf=lambda x,m=0,s=1: math.exp(-.5*((x-m)/s)**2)/(s*math.sqrt(2*math.pi))
def curve(f,xa,xb,sx,sy,n=50): return [(sx(xa+(xb-xa)*i/n),sy(f(xa+(xb-xa)*i/n))) for i in range(n+1)]
def panel_title(x,s,c=INK): return T(x,24,s,14,c,b=True)
out={}

# 1 SD vs SE
s=head();random.seed(3)
s+=panel_title(160,'標準偏差 SD：1個1個のばらつき',BL)+panel_title(480,'標準誤差 SE：平均値のぶれ',OR)
s+=L(320,40,320,262,GD,1.5)
# left: dots of 25 daily sales
xs=[random.gauss(0,1) for _ in range(25)];m=sum(xs)/25;sd=(sum((x-m)**2 for x in xs)/24)**.5;xs=[(x-m)/sd for x in xs]
sxL=lambda v:160+v*42
for i,x in enumerate(sorted(xs)):
    s+=C(sxL(x),150+((i*37)%5-2)*10,5,BL,.8)
s+=L(sxL(-1),200,sxL(1),200,BL,3)+L(sxL(-1),194,sxL(-1),206,BL,3)+L(sxL(1),194,sxL(1),206,BL,3)
s+=T(160,222,'±1 SD（例：±10個）',12,BL,b=True)
s+=L(30,240,290,240,INK2,1)+T(160,258,'1日ごとの売上（25日分）',11.5,INK2)
s+=T(160,72,'n を増やしても',12,INK2)+T(160,90,'幅はほぼ変わらない',12,INK2,b=True)
# right: dist of xbar narrow vs wide
sxR=lambda v:480+v*42;base=240
f1=lambda v:npdf(v,0,1);f2=lambda v:npdf(v,0,.2)
sy1=lambda y:base-y*95/0.4;sy2=lambda y:base-y*150/2.0
s+=poly(curve(f1,-3,3,sxR,sy1),BL,1.5,d='5 4')
s+=poly(curve(f2,-1,1,sxR,sy2),OR,2.6)
s+=L(sxR(-.2),base-158,sxR(.2),base-158,OR,3)
s+=T(480,base-168,'±1 SE = SD/√n = 10/√25 = 2',12,OR,b=True)
s+=L(340,base,620,base,INK2,1)+T(480,258,'標本平均 x̄ を何度も作ったときの分布',11.5,INK2)
s+=T(600,base-40,'点線＝データ',11,BL,'end')+T(600,base-24,'実線＝x̄',11,OR,'end')
out['01_sd_se']=s+'</svg>'

# 2 排反 vs 独立
s=head()
s+=panel_title(160,'排反：同時に起きない',BL)+panel_title(480,'独立：Aが起きてもBの確率は同じ',OR)+L(320,40,320,262,GD,1.5)
s+=R(30,50,260,170,'#f4f3ef',1,6,GD)
s+=C(110,135,55,BL,.35,BL)+C(210,135,55,OR,.35,OR)
s+=T(110,140,'A',18,BL,b=True)+T(210,140,'B',18,OR,b=True)
s+=T(160,240,'P(A∩B)＝0（重なりが無い）',12.5,INK,b=True)+T(160,258,'→ Aが起きたらBは必ず起きない＝強く依存',11.5,RD)
# right: unit square
x0,y0,w,h=370,50,220,170
s+=R(x0,y0,w,h,'#f4f3ef',1,4,GD)
s+=R(x0,y0,w*.4,h,BL,.30,0)+R(x0,y0,w,h*.5,OR,.30,0)
s+=R(x0,y0,w*.4,h*.5,'#6250d6',.25,0,'#6250d6')
s+=T(x0+w*.2,y0+h*.75+5,'A＝0.4',12,BL,b=True)+T(x0+w*.7,y0+h*.25+5,'B＝0.5',12,OR,b=True)
s+=T(x0+w*.2,y0+h*.25+5,'0.2',13,'#6250d6',b=True)
s+=T(480,240,'P(A∩B)＝0.4×0.5＝0.2',12.5,INK,b=True)+T(480,258,'Aの中でもBの割合は 0.2/0.4＝0.5（変わらない）',11.5,INK2)
out['02_exclusive_indep']=s+'</svg>'

# 3 母数 vs 統計量
s=head()
s+=panel_title(320,'母数は1つに固定、統計量は標本ごとに変わる')
s+=R(30,50,200,190,'#f4f3ef',1,8,GD)+T(130,72,'母集団（全店舗）',13,INK,b=True)
random.seed(7)
for i in range(30):
    s+=C(50+random.random()*160,85+random.random()*120,3,GR,.6)
s+=T(130,228,'μ＝100（母数・1つだけ）',13,RD,b=True)
xs=[(330,'標本1','x̄＝97.2'),(330,'標本2','x̄＝103.5'),(330,'標本3','x̄＝99.1')]
for k,(x,lab,v) in enumerate(xs):
    y=70+k*62
    s+=arrow(235,145,300,y+12,GR,1.5)
    s+=R(305,y-6,150,40,'#ffffff',1,6,BL)
    for j in range(5): s+=C(320+j*12,y+14,3.5,BL,.8)
    s+=T(390,y+19,lab,12,INK2,'start')
    s+=T(470,y+19,v,13.5,BL,'start',True)
s+=T(560,250,'↑ 統計量（取り直すと変わる）',11.5,BL,'end')
out['03_param_stat']=s+'</svg>'

# 4 標本分散 vs 不偏分散
s=head()
s+=panel_title(320,'σ²＝4 の母集団から何度も取ったときの「平均的な値」')
ns=[2,3,5,10,30];x0=80;base=238;sc=36
s+=L(60,base,600,base,INK2,1)
s+=L(60,base-4*sc,600,base-4*sc,RD,1.6,'6 4')
for i,n in enumerate(ns):
    cx=110+i*105
    v=(n-1)/n*4
    s+=R(cx-26,base-v*sc,24,v*sc,OR,.85,3)+R(cx+2,base-4*sc,24,4*sc,BL,.75,3)
    s+=T(cx-14,base-v*sc-6,f'{v:.2f}',11,OR,b=True)
    s+=T(cx,base+18,f'n＝{n}',12,INK2)
s+=R(40,40,12,12,OR,.85,2)+T(58,50,'v（nで割る）：小さく出る',12,INK,'start')
s+=R(250,40,12,12,BL,.75,2)+T(268,50,'s²（n−1で割る）：ちょうど4',12,INK,'start')
s+=L(470,46,500,46,RD,1.6,'6 4')+T(506,50,'真の σ²＝4',12,RD,'start',True)
s+=T(320,275,'n が小さいほど差が大きい。n＝30 ではほぼ同じ（一致性）',11.5,INK2)
out['04_var_unbiased']=s+'</svg>'

# 5 CI
s=head(300)
s+=panel_title(320,'同じ方法で区間を20回つくると…')
random.seed(11)
zs=[random.gauss(0,1) for _ in range(20)]
zs[13]=2.4
mu=320;sc=60;h=1.96
s+=L(mu,40,mu,262,INK,2,'5 3')+T(mu,280,'真の μ（固定・動かない）',12,INK,b=True)
for i,z in enumerate(zs):
    y=48+i*10.6;ok=abs(z)<=h;c=BL if ok else RD
    s+=L(mu+(z-h)*sc*0.9,y,mu+(z+h)*sc*0.9,y,c,2.6 if ok else 3.4)+C(mu+z*sc*0.9,y,2.6,c)
s+=T(40,120,'◯ 正しい読み方',13,BL,'start',True)+T(40,140,'「この方法は」',12,INK,'start')+T(40,158,'約95%の区間が μ を含む',12,INK,'start')
s+=T(600,120,'✕ よくある誤り',13,RD,'end',True)+T(600,140,'「この区間に μ が',12,INK,'end')+T(600,158,'95%の確率で入る」',12,INK,'end')
s+=T(600,200,'赤＝μ を外した区間',11.5,RD,'end')
out['05_ci']=s+'</svg>'

# 6 p値
s=head()
s+=panel_title(320,'p値＝「H₀が正しいとしたら」今回以上に極端な結果が出る確率')
sx=lambda v:320+v*70;base=225;sy=lambda y:base-y*400
s+=poly([(sx(2.1),base)]+curve(npdf,2.1,4,sx,sy)+[(sx(4),base)],None,fill=RD,op=.55)
s+=poly([(sx(-4),base)]+curve(npdf,-4,-2.1,sx,sy)+[(sx(-2.1),base)],None,fill=RD,op=.55)
s+=poly(curve(npdf,-4,4,sx,sy),BL,2.4)+L(40,base,600,base,INK2,1)
s+=L(sx(2.1),base,sx(2.1),70,INK,2)+T(sx(2.1),62,'今回の z＝2.1',12.5,INK,b=True)
s+=T(sx(0),base-170,'H₀ が正しいときの z の分布',12,BL,b=True)
s+=T(sx(3.1),base-20,'0.018',12,RD,b=True)+T(sx(-3.1),base-20,'0.018',12,RD,b=True)
s+=T(320,250,'赤の合計＝p値 0.036（両側）',13,RD,b=True)
s+=T(320,270,'✕「H₀が正しい確率が3.6%」ではない（H₀を前提にした計算だから）',11.5,INK2)
out['06_pvalue']=s+'</svg>'

# 7 相関と因果
s=head()
s+=panel_title(320,'一緒に動く ≠ 原因と結果（第3の要因＝交絡）')
def box(x,y,w,t,c):
    return R(x-w/2,y-20,w,40,'#ffffff',1,8,c)+T(x,y+5,t,14,c,b=True)
s+=box(320,80,140,'気温',OR)+box(150,200,170,'アイス売上',BL)+box(490,200,170,'熱中症の搬送',BL)
s+=arrow(290,102,180,178,OR,2.5)+arrow(350,102,460,178,OR,2.5)
s+=L(237,200,403,200,RD,2,'6 5')
s+=T(320,192,'相関あり',12,RD,b=True)+T(320,224,'でも因果ではない',12,RD)
s+=T(212,130,'原因',11.5,OR,'end')+T(428,130,'原因',11.5,OR,'start')
s+=T(320,262,'疑う順：①交絡（第3の要因）②逆の因果 ③偶然',12,INK2)
out['07_corr_cause']=s+'</svg>'

# 8 観察 vs 実験
s=head()
s+=panel_title(160,'観察研究：本人が選ぶ',OR)+panel_title(480,'実験研究：無作為に割り付ける',BL)+L(320,40,320,262,GD,1.5)
random.seed(5)
def people(x0,y0,cols,colsel):
    r=''
    for i in range(12):
        r+=C(x0+(i%6)*18,y0+(i//6)*18,6,colsel(i),.85)
    return r
s+=people(115,60,6,lambda i:OR if i<6 else BL)
s+=T(160,112,'意識の高い人(橙)ほど',11.5,INK2)+T(160,128,'アプリを選びがち',11.5,INK2)
s+=arrow(130,140,90,170,GR,1.5)+arrow(190,140,230,170,GR,1.5)
s+=R(40,175,100,58,'#ffffff',1,6,GR)+T(90,192,'使った',12,INK,b=True)
for i in range(5): s+=C(58+i*16,214,5.5,OR if i<4 else BL,.85)
s+=R(180,175,100,58,'#ffffff',1,6,GR)+T(230,192,'使わない',12,INK,b=True)
for i in range(5): s+=C(198+i*16,214,5.5,OR if i<1 else BL,.85)
s+=T(160,256,'差が出ても「意識の差」かもしれない',12,RD,b=True)
s+=people(435,60,6,lambda i:OR if i<6 else BL)
s+=T(480,112,'くじで2群に分ける',11.5,INK2)+T(480,128,'（本人は選べない）',11.5,INK2)
s+=arrow(450,140,410,170,GR,1.5)+arrow(510,140,550,170,GR,1.5)
s+=R(360,175,100,58,'#ffffff',1,6,GR)+T(410,192,'使う群',12,INK,b=True)
for i,c in enumerate([OR,BL,OR,BL,OR]): s+=C(378+i*16,214,5.5,c,.85)
s+=R(500,175,100,58,'#ffffff',1,6,GR)+T(550,192,'使わない群',12,INK,b=True)
for i,c in enumerate([BL,OR,BL,OR,BL]): s+=C(518+i*16,214,5.5,c,.85)
s+=T(480,256,'他の要因がそろう → 差＝効果と言いやすい',12,BL,b=True)
out['08_obs_exp']=s+'</svg>'

# 9 LLN vs CLT
s=head()
s+=panel_title(160,'大数の法則：1本の平均が μ に近づく',BL)+panel_title(480,'中心極限定理：平均の分布が正規に',OR)+L(320,40,320,262,GD,1.5)
random.seed(2);c=0;pts=[]
for i in range(1,401):
    pass
    
    c+=1 if random.random()<.3 else 0
    if i%4==0 or i<40: pts.append((40+260*i/400,220-min(c/i,0.55)*300))
s+=L(40,220-.3*300,300,220-.3*300,OR,1.8,'6 4')+T(300,220-.3*300-6,'p＝0.3',11.5,OR,'end',True)
s+=poly(pts,BL,2)+L(40,230,300,230,INK2,1)+T(170,250,'試行回数 →（1〜400）',11.5,INK2)
s+=T(170,268,'見るもの：1つの数が落ち着く',11.5,BL,b=True)
# right: skewed pop small + histogram of means
random.seed(4)
ms=[sum(-math.log(1-random.random()) for _ in range(30))/30 for _ in range(1500)]
bins=[0]*30
for v in ms:
    k=int((v-0.4)/0.04)
    if 0<=k<30: bins[k]+=1
mx=max(bins)
for k,b in enumerate(bins):
    hgt=b/mx*130
    s+=R(345+k*8.5,225-hgt,7.5,hgt,OR,.7,1)
fx=[(345+k*0.25*8.5, 225-npdf(0.4+k*0.01,1,1/math.sqrt(30))/npdf(0,0,1/math.sqrt(30))*130) for k in range(0,121,3)]
s+=poly(fx,INK,1.6,d='4 3')
s+=L(340,230,605,230,INK2,1)+T(480,250,'右に歪んだ母集団でも、n＝30 の x̄ は山形',11.5,INK2)
s+=T(480,268,'見るもの：分布の「形」',11.5,OR,b=True)
out['09_lln_clt']=s+'</svg>'

# 10 R2 vs prediction
s=head()
s+=panel_title(320,'手元のデータに合わせ込むほど R² は上がるが、新しいデータは外れる')
random.seed(9)
xs=[i/9 for i in range(10)];ys=[0.5+0.6*x+random.gauss(0,.12) for x in xs]
nx=[0.05+i/7*0.9 for i in range(8)];ny=[0.5+0.6*x+random.gauss(0,.12) for x in nx]
def pan(x0,title,col,wig):
    r=R(x0,44,280,190,'#ffffff',1,6,GD)+T(x0+140,62,title,13,col,b=True)
    sx=lambda v:x0+20+v*240;sy=lambda v:224-(v-0.2)*150
    if wig:
        # lagrange interpolation through points (clipped)
        def lag(t):
            tot=0
            for i in range(10):
                p=ys[i]
                for j in range(10):
                    if j!=i: p*=(t-xs[j])/(xs[i]-xs[j])
                tot+=p
            return max(0.15,min(1.35,tot))
        r+=poly([(sx(t/200),sy(lag(t/200))) for t in range(0,201,3)],col,2.2)
    else:
        r+=L(sx(0),sy(0.5),sx(1),sy(1.1),col,2.4)
    for x,y in zip(xs,ys): r+=C(sx(x),sy(y),4.5,BL,.85)
    for x,y in zip(nx,ny): r+=C(sx(x),sy(y),4.5,'#ffffff',1,RD)
    return r
s+=pan(25,'直線（単純なモデル）',INK,False)+pan(335,'くねくね曲線（複雑なモデル）',OR,True)
s+=T(165,252,'手元 R²＝0.83　新データの誤差：小',12,INK,b=True)
s+=T(475,252,'手元 R²＝1.00　新データの誤差：大',12,RD,b=True)
s+=C(210,272,4.5,BL,.85)+T(220,276,'手元のデータ',11.5,INK2,'start')+C(330,272,4.5,'#ffffff',1,RD)+T(340,276,'新しいデータ',11.5,INK2,'start')
out['10_r2_pred']=s+'</svg>'

# 11 arith vs geo
s=head()
s+=panel_title(320,'+10% のあと −10%：算術平均は 0% でも、実際は減っている')
base=230;sc=1.5
vals=[('最初',100,GR),('1年後 +10%',110,BL),('2年後 −10%',99,RD)]
for i,(lab,v,c) in enumerate(vals):
    x=110+i*130
    s+=R(x-35,base-v*sc,70,v*sc,c,.8,3)+T(x,base-v*sc-8,str(v),14,c,b=True)+T(x,base+18,lab,12,INK2)
s+=L(60,base-100*sc,460,base-100*sc,INK2,1.2,'5 4')
s+=L(50,base,470,base,INK2,1)
s+=R(480,70,150,150,'#f4f3ef',1,8,GD)
s+=T(555,95,'算術平均',12,INK2)+T(555,115,'(10%−10%)/2＝0%',12,INK,b=True)+T(555,133,'✕ 100のまま',12,RD)
s+=T(555,165,'幾何平均',12,INK2)+T(555,185,'√(1.1×0.9)−1',12,INK,b=True)+T(555,203,'＝−0.5%/年 ◯',12,BL,b=True)
out['11_arith_geo']=s+'</svg>'

# 12 P(A|B) vs P(B|A)
s=head(300)
s+=panel_title(320,'1万人を検査（有病率1%・感度90%・偽陽性5%）')
x0,y0,w,h=40,46,380,210
s+=R(x0,y0,w,h,'#f4f3ef',1,4,GD)
ws=w*0.10  # exaggerate sick width for visibility
s+=R(x0,y0,ws,h,RD,.18,0)+T(x0+ws/2,y0+h+16,'病気 100人',11.5,RD,b=True)
s+=T(x0+ws+(w-ws)/2,y0+h+16,'健康 9,900人',11.5,INK2,b=True)
s+=R(x0,y0,ws,h*.9,RD,.75,0)
s+=R(x0+ws,y0,w-ws,h*.05,OR,.8,0)
s+=T(x0+ws/2,y0+h*.45,'90',13,'#ffffff',b=True)
s+=T(x0+ws+(w-ws)/2,y0+h*.05+16,'陽性 495人（偽陽性）',12,OR,b=True)
s+=T(x0+ws+(w-ws)/2,y0+h*.6,'陰性 9,405人',12,INK2)
s+=R(440,46,190,100,'#ffffff',1,8,RD)+T(535,70,'P(陽性｜病気)',13,RD,b=True)+T(535,94,'＝90/100',12.5,INK)+T(535,118,'＝90%',16,RD,b=True)+T(535,137,'分母：病気の人',11,INK2)
s+=R(440,156,190,100,'#ffffff',1,8,OR)+T(535,180,'P(病気｜陽性)',13,OR,b=True)+T(535,204,'＝90/(90+495)',12.5,INK)+T(535,228,'＝15%',16,OR,b=True)+T(535,247,'分母：陽性の人',11,INK2)
s+=T(320,290,'※図の幅は見やすさのため病気側を広げています',10.5,INK2)
out['12_cond_reverse']=s+'</svg>'

# 13 simple vs multiple
s=head()
s+=panel_title(320,'客数の違いを混ぜると、価格の効果が逆向きに見える')
random.seed(21)
sx=lambda v:60+(v-180)*7.5;sy=lambda v:240-(v-300)*1.35
groups=[(190,330,BL,'客が少ない日'),(205,370,OR,'客が多い日'),(220,410,'#6250d6','客がとても多い日')]
allp=[]
for (pc,yc,c,lab) in groups:
    for i in range(12):
        p=pc+random.uniform(-7,7);y=yc-1.6*(p-pc)+random.gauss(0,6)
        s+=C(sx(p),sy(y),4.2,c,.8);allp.append((p,y))
    s+=L(sx(pc-8),sy(yc+1.6*8),sx(pc+8),sy(yc-1.6*8),c,2.4)
mp=sum(p for p,_ in allp)/len(allp);my=sum(y for _,y in allp)/len(allp)
b=sum((p-mp)*(y-my) for p,y in allp)/sum((p-mp)**2 for p,_ in allp)
s+=L(sx(180),sy(my+b*(180-mp)),sx(232),sy(my+b*(232-mp)),RD,2.4,'7 5')
s+=L(50,248,470,248,INK2,1)+T(260,268,'価格（円）→',11.5,INK2)
s+=R(470,60,160,170,'#f4f3ef',1,8,GD)
s+=T(550,84,'赤点線＝単回帰',12,RD,b=True)+T(550,102,f'傾き ＋{b:.0f}',12,RD)+T(550,120,'「値上げで売れる？」',11.5,INK2)
s+=T(550,156,'色別の線＝重回帰',12,INK,b=True)+T(550,174,'客数をそろえると',11.5,INK2)+T(550,192,'傾き −1.6',12,BL,b=True)+T(550,210,'（値上げで減る）',11.5,INK2)
out['13_simple_multi']=s+'</svg>'

for k,v in out.items():
    open(k+'.svg','w').write(v)
print({k:len(v.encode()) for k,v in out.items()})
