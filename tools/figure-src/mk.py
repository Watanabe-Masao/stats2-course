import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from math import comb
import glob
for f in glob.glob("/usr/share/fonts/opentype/noto/NotoSansCJK-*.ttc"): fm.fontManager.addfont(f)
plt.rcParams["font.family"]="Noto Sans CJK JP"; plt.rcParams["svg.fonttype"]="none"; plt.rcParams["font.sans-serif"]=["Noto Sans CJK JP"]
BG="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; GRID="#e4e3df"
BLUE="#2a78d6"; ORANGE="#eb6834"; MUTED="#b9c9de"
def base(ax):
    ax.set_facecolor(BG)
    for s in ["top","right","left"]: ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(colors=INK2,labelsize=13,length=0)
    ax.yaxis.grid(True,color=GRID,lw=1); ax.set_axisbelow(True)

# A: distribution with E and SD
fig,ax=plt.subplots(figsize=(6.4,4.2),dpi=200); fig.patch.set_facecolor(BG); base(ax)
x=[0,1,2]; p=[0.2,0.5,0.3]; E=1.1; sd=0.7
ax.axvspan(E-sd,E+sd,color=BLUE,alpha=0.08,lw=0)
ax.bar(x,p,width=0.5,color=BLUE,edgecolor=BG,lw=2)
for xi,pi in zip(x,p): ax.text(xi-(0.1 if xi==1 else 0),pi+0.015,f"{pi}",ha="center",va="bottom",fontsize=14,color=INK)
ax.axvline(E,color=ORANGE,lw=2)
ax.text(E+0.04,0.585,"期待値 E(X)=1.1\n＝分布の重心",color=INK,fontsize=12,va="top")
ax.annotate("",xy=(E-sd,0.035),xytext=(E+sd,0.035),arrowprops=dict(arrowstyle="<->",color=INK2,lw=1.5))
ax.text(E,0.05,"±標準偏差 0.7",ha="center",va="bottom",fontsize=11,color=INK2,bbox=dict(fc=BG,ec="none",pad=1.5))
ax.set_xticks(x,["0個","1個","2個"]); ax.set_ylim(0,0.62); ax.set_xlim(-0.6,2.6)
ax.set_ylabel("確率 P(X=x)",color=INK2,fontsize=12)
ax.set_title("1人が買う個数 X の分布",loc="left",fontsize=15,color=INK,pad=10)
fig.tight_layout(); fig.savefig("t13_dist.svg",facecolor=BG); plt.close(fig)

# B: same mean, different variance (small multiples)
fig,axs=plt.subplots(1,2,figsize=(6.4,3.6),dpi=200,sharey=True); fig.patch.set_facecolor(BG)
sets=[("売場A｜分散 0.49",[0.2,0.5,0.3]),("売場B｜分散 0.99",[0.45,0.0,0.55])]
for ax,(t,pp) in zip(axs,sets):
    base(ax); ax.bar(x,pp,width=0.5,color=BLUE,edgecolor=BG,lw=2)
    for xi,pi in zip(x,pp):
        if pi>0: ax.text(xi,pi+0.015,f"{pi}",ha="center",va="bottom",fontsize=12,color=INK)
    ax.axvline(1.1,color=ORANGE,lw=2)
    ax.set_xticks(x,["0個","1個","2個"]); ax.set_ylim(0,0.66)
    ax.set_title(t,loc="left",fontsize=13,color=INK)
axs[0].text(1.16,0.62,"平均 1.1",fontsize=11,color=INK2)
fig.suptitle("平均は同じでも、ばらつき（分散）が違う",x=0.02,ha="left",fontsize=14,color=INK)
fig.tight_layout(); fig.savefig("t13_var.svg",facecolor=BG); plt.close(fig)

# C: binomial B(4,0.25)
n,pr=4,0.25; ks=list(range(n+1)); pk=[comb(n,k)*pr**k*(1-pr)**(n-k) for k in ks]
fig,ax=plt.subplots(figsize=(6.4,4.2),dpi=200); fig.patch.set_facecolor(BG); base(ax)
cols=[ORANGE if k==1 else MUTED for k in ks]
ax.bar(ks,pk,width=0.6,color=cols,edgecolor=BG,lw=2)
for k,v in zip(ks,pk): ax.text(k,v+0.012,f"{v:.3f}",ha="center",va="bottom",fontsize=12,color=INK)
ax.text(1,pk[1]+0.055,"ちょうど1人",ha="center",fontsize=12,color=INK)
ax.set_xticks(ks,[f"{k}人" for k in ks]); ax.set_ylim(0,0.56)
ax.set_ylabel("確率",color=INK2,fontsize=12)
ax.set_title("4人のうち買う人数（購入率25%）B(4, 0.25)",loc="left",fontsize=14,color=INK,pad=10)
fig.tight_layout(); fig.savefig("t14_binom.svg",facecolor=BG); plt.close(fig)
print([round(v,6) for v in pk], sum(pk))
