"Main menu UI"

import pygame, pygame.gfxdraw, numpy as np, math, random, os, time, threading, subprocess
from settings import (MUSIC_PATH, HOVER_SFX_PATH, SELECT_SFX_PATH,
                      LOGO_SFX_PATH, OSU_LOGO_PATH, CLASSES)

VIRT_W, VIRT_H = 1920, 1080

# ── Constants ────────────────────────────────────────────────────────────────
CONSTANTS = {
    'ANIM_DUR': 0.75,
    'LOGO_CENTER': (VIRT_W // 2, VIRT_H // 2),
    'LOGO_TARGET': (200, 110),
    'LOGO_R_BIG': 130,
    'LOGO_R_SMALL': 72,
    'MENU_IH': 72,
    'MENU_IW': 300,
    'MENU_GAP': 7,
    'CARD_Y': VIRT_H // 2 + 30,
    'CARD_SPACING': 480,
    'CLASS_ANIM_DUR': 0.55,
    'LOGO_CLICK_DUR': 0.43,
    'BEAT_DETECTION': {
        'SR': 44100,
        'HOP_MS': 20,
        'THRESHOLD': 1.6,
        'MIN_GAP': 0.22,
        'ENERGY_K': 25,
    },
    'COLORS': {
        'BG': (7, 7, 15),
        'WHITE': (255, 255, 255),
        'ACCENT': (100, 180, 255),
    },
    'FONT_SIZES': {
        'SMALL': 15,
        'NP': 17,
        'HINT': 14,
    },
    'PARTICLE_COUNT': 80,
    'RING_OFFSETS': [22, 52],
    'RING_ALPHAS': [38, 20],
}

BG = CONSTANTS['COLORS']['BG']
WHITE = CONSTANTS['COLORS']['WHITE']

# ── Beat detection ─────────────────────────────────────────────────────────────
def _decode_mp3(path, sr=CONSTANTS['BEAT_DETECTION']['SR']):
    cmd = ["ffmpeg","-i",path,"-f","f32le","-acodec","pcm_f32le",
           "-ar",str(sr),"-ac","1","-loglevel","quiet","pipe:1"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0: raise RuntimeError(r.stderr.decode())
    return np.frombuffer(r.stdout, dtype=np.float32).copy(), sr

def _detect_beats(path, threshold=CONSTANTS['BEAT_DETECTION']['THRESHOLD'], hop_ms=CONSTANTS['BEAT_DETECTION']['HOP_MS']):
    print("probam dekodirat beat-e")
    samples, sr = _decode_mp3(path)
    hop = int(sr*hop_ms/1000); win = hop*2
    energies = np.array([float(np.mean(samples[i:i+win]**2))
                         for i in range(0, len(samples)-win, hop)])
    k = CONSTANTS['BEAT_DETECTION']['ENERGY_K']
    beats, last = [], -0.4
    for i in range(k, len(energies)-k):
        avg = np.mean(energies[i-k:i+k])
        if energies[i] > threshold*avg:
            t = i*hop_ms/1000.0
            if t-last > CONSTANTS['BEAT_DETECTION']['MIN_GAP']:
                s = max(0.2, min(1.0, (energies[i]/max(avg,1e-9)-threshold)/3.0+0.3))
                beats.append((t, s)); last = t
    print(f"najdenih: {len(beats)}")
    return beats

# ── Easing ────────────────────────────────────────────────────────────────────
def _ease_out_cubic(t):
    t=max(0.,min(1.,t)); return 1-(1-t)**3
def _ease_in_out_quint(t):
    t=max(0.,min(1.,t)); return 16*t**5 if t<0.5 else 1-(-2*t+2)**5/2
def _ease_out_expo(t):
    return 0. if t==0 else 1-2**(-10*max(0.,min(1.,t)))
def _ease_out_back(t):
    t=max(0.,min(1.,t)); c1,c3=1.70158,2.70158
    return 1+c3*(t-1)**3+c1*(t-1)**2
def _ease_in_cubic(t):
    t=max(0.,min(1.,t)); return t*t*t
def _lerp(a,b,t):    return a+(b-a)*t
def _lerp2(a,b,t):   return (_lerp(a[0],b[0],t),_lerp(a[1],b[1],t))
def _smooth(c,tgt,spd,dt): return c+(tgt-c)*(1.-math.exp(-spd*dt))

_FC = {}
def _font(size, bold=False):
    k=(size,bold)
    if k not in _FC:
        for n in ["Nunito","Segoe UI","Arial Rounded MT Bold","Verdana"]:
            try: _FC[k]=pygame.font.SysFont(n,size,bold=bold); break
            except: pass
        else: _FC[k]=pygame.font.SysFont(None,size,bold=bold)
    return _FC[k]

BG, WHITE = (7,7,15), (255,255,255)

CLASS_DATA = {
    "Knight":   {
        "icon": "⚔", "color": (100,180,255),
        "stats": {"HP":150,"DMG":35,"SPD":200,"STAM":100},
        "desc": ["High HP & Armor","Wide melee swing","Medium speed","Low crit chance"],
    },
    "Mage":     {
        "icon": "✦", "color": (180,120,255),
        "stats": {"HP":80,"DMG":65,"SPD":185,"STAM":160},
        "desc": ["Long-range staff","Very high damage","High stamina pool","Glass cannon"],
    },
    "Assassin": {
        "icon": "◈", "color": (100,230,160),
        "stats": {"HP":100,"DMG":50,"SPD":260,"STAM":130},
        "desc": ["Dual daggers","Fastest speed","Highest crit rate","Medium HP"],
    },
}
STAT_MAX    = {"HP":150,"DMG":65,"SPD":260,"STAM":160}
CLASS_NAMES = ["Knight","Mage","Assassin"]


# ══════════════════════════════════════════════════════════════════════════════
#  SettingsPanel
# ══════════════════════════════════════════════════════════════════════════════
class SettingsPanel:
    FPS_OPTIONS = [30,60,120,144,240]
    ITEM_H=100; SL_W=440; PAD_LEFT=28; PAD_TOP=30; PANEL_W=520
    FONT_LBL=26; FONT_PCT=20; ANIM_SPEED=4.5; ROW_ANIM_SPEED=5.5
    PANEL_BG_ALPHA=48; PANEL_BORDER_ALPHA=55; LABEL_ALPHA_MAX=200; PCT_ALPHA_MAX=155

    def __init__(self, vol_music, vol_sfx, vol_hover, vol_click, vol_logo, fps_idx):
        self.open=False; self.t=0.0
        self.vol_music=vol_music; self.vol_sfx=vol_sfx; self.vol_hover=vol_hover
        self.vol_click=vol_click; self.vol_logo=vol_logo; self.fps_idx=fps_idx
        self.anchor_x=0; self.anchor_y=0; self.dragging=None; self._row_t=[0.0]*6

    def toggle(self,ax,ay):
        self.open=not self.open; self.anchor_x=ax; self.anchor_y=ay
        if self.open:
            for i in range(len(self._row_t)): self._row_t[i]=0.0

    def zazeni(self,dt):
        target=1.0 if self.open else 0.0
        self.t=_smooth(self.t,target,self.ANIM_SPEED,dt)
        for i in range(len(self._row_t)):
            delay=i*0.07
            row_prog=(max(0.,self.t-delay)/max(1.-delay,0.01) if target>0
                      else max(0.,self.t-(len(self._row_t)-1-i)*0.05))
            self._row_t[i]=_smooth(self._row_t[i],min(1.,row_prog),self.ROW_ANIM_SPEED,dt)

    def vrstice(self):
        return list(zip(
            ['music','sfx','hover','click','logo','fps'],
            ["Glasba","Zvočni efekti","Hover zvok","Klik zvok","Logo zvok","FPS"],
            [self.vol_music,self.vol_sfx,self.vol_hover,self.vol_click,self.vol_logo,None]
        ))

    def event_handler(self,ev,vmx,vmy):
        if self.t<0.06: return False
        slide_et=_ease_out_cubic(self.t)
        px=self.anchor_x+int((1.-slide_et)*60); py=self.anchor_y
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            for i,(key,label,val) in enumerate(self.vrstice()):
                ry=py+self.PAD_TOP+i*self.ITEM_H; rx=px+self.PAD_LEFT
                if key=='fps':
                    btn_y=ry+self.ITEM_H//2+8
                    if btn_y<=vmy<=btn_y+36:
                        if rx+200<=vmx<=rx+236: self.fps_idx=max(0,self.fps_idx-1); return True
                        if rx+280<=vmx<=rx+316: self.fps_idx=min(len(self.FPS_OPTIONS)-1,self.fps_idx+1); return True
                else:
                    sly=ry+self.ITEM_H-30
                    if rx<=vmx<=rx+self.SL_W and abs(vmy-sly)<20: self.dragging=key; return True
        if ev.type==pygame.MOUSEBUTTONUP: self.dragging=None
        if ev.type==pygame.MOUSEMOTION and self.dragging:
            rx2=self.anchor_x+int((1.-_ease_out_cubic(self.t))*60)+self.PAD_LEFT
            slv=max(0.,min(1.,(vmx-rx2)/max(self.SL_W,1)))
            setattr(self,'vol_'+self.dragging,slv); return True
        return False

    def settings_UI(self,surf,vmx,vmy):
        if self.t<0.015: return
        slide_et=_ease_out_cubic(self.t)
        px=self.anchor_x+int((1.-slide_et)*60); py=self.anchor_y
        total_h=len(self.vrstice())*self.ITEM_H+self.PAD_TOP*2; pw=self.PANEL_W
        global_a=min(1.,self.t*1.8)
        ps=pygame.Surface((pw,total_h),pygame.SRCALPHA)
        ps.fill((18,18,28,int(self.PANEL_BG_ALPHA*global_a)))
        for ry2 in range(min(total_h,300)):
            ga=int(10*(1-ry2/300)*global_a)
            if ga>0: pygame.draw.line(ps,(255,255,255,ga),(0,ry2),(pw,ry2))
        pygame.draw.rect(ps,(200,200,220,int(self.PANEL_BORDER_ALPHA*global_a)),ps.get_rect(),1,border_radius=8)
        surf.blit(ps,(px,py))
        for i,(key,label,val) in enumerate(self.vrstice()):
            row_et=_ease_out_cubic(min(1.,self._row_t[i]))
            row_alpha=int(255*min(1.,self._row_t[i]*2.)*global_a)
            if row_alpha<3: continue
            rx=px+self.PAD_LEFT+int((1.-row_et)*30); ry=py+self.PAD_TOP+i*self.ITEM_H
            if i>0:
                ss=pygame.Surface((pw-self.PAD_LEFT*2,1),pygame.SRCALPHA)
                ss.fill((255,255,255,int(22*global_a))); surf.blit(ss,(px+self.PAD_LEFT,ry-2))
            lc=(int(_lerp(110,215,row_et)),int(_lerp(115,220,row_et)),int(_lerp(135,235,row_et)))
            ls=_font(self.FONT_LBL,bold=True).render(label,True,lc)
            ls.set_alpha(int(self.LABEL_ALPHA_MAX*row_et*global_a)); surf.blit(ls,(rx,ry+8))
            if key=='fps':
                fv=self.FPS_OPTIONS[self.fps_idx]; by2=ry+self.ITEM_H//2+10
                dim=(60,65,75); act=(195,200,215)
                for txt,ox2,can in [("◀",200,self.fps_idx>0),(str(fv),244,True),
                                    ("▶",296,self.fps_idx<len(self.FPS_OPTIONS)-1)]:
                    s2=_font(28,bold=True).render(txt,True,act if can else dim)
                    s2.set_alpha(row_alpha); surf.blit(s2,(rx+ox2,by2))
            else:
                sly=ry+self.ITEM_H-30; slw=self.SL_W; slh=5
                kxp=rx+int(slw*val); is_hov=abs(vmx-kxp)<18 and abs(vmy-(sly+slh//2))<18
                is_drag=self.dragging==key
                ts=pygame.Surface((slw,slh),pygame.SRCALPHA)
                ts.fill((255,255,255,int(32*global_a))); surf.blit(ts,(rx,sly))
                fw=int(slw*val)
                if fw>2:
                    fs2=pygame.Surface((fw,slh),pygame.SRCALPHA)
                    for cx2 in range(fw):
                        tg=cx2/max(fw-1,1)
                        pygame.draw.line(fs2,(int(_lerp(130,200,tg)),int(_lerp(145,215,tg)),
                                         int(_lerp(195,235,tg)),int(row_alpha*_lerp(.4,.75,tg))),(cx2,0),(cx2,slh-1))
                    surf.blit(fs2,(rx,sly))
                kx=rx+fw; ky=sly+slh//2; kr=9 if(is_hov or is_drag) else 7; ka=int(row_alpha*.85)
                for gr in range(kr+7,kr,-1):
                    ga2=max(0,int(ka*(.18 if(is_hov or is_drag) else .08)*(1-(gr-kr)/8.)))
                    if ga2>0: pygame.gfxdraw.aacircle(surf,kx,ky,gr,(170,190,225,ga2))
                pygame.gfxdraw.filled_circle(surf,kx,ky,kr,(200,210,230,ka))
                pygame.gfxdraw.aacircle(surf,kx,ky,kr,(220,228,245,ka))
                pygame.gfxdraw.filled_circle(surf,kx,ky,max(2,kr//3),(12,16,35,int(ka*.65)))
                pc=_font(self.FONT_PCT).render(f"{int(val*100)}%",True,(200,210,228) if(is_hov or is_drag) else(155,165,185))
                pc.set_alpha(int(self.PCT_ALPHA_MAX*row_et*global_a)); surf.blit(pc,(rx+slw+14,sly-7))


# ══════════════════════════════════════════════════════════════════════════════
#  obročki / MenuAnimacije / LepotniDodatkiAlNeki
# ══════════════════════════════════════════════════════════════════════════════
class obročki:
    def __init__(self,offset_r,base_alpha):
        self.offset_r=offset_r; self.base_alpha=base_alpha; self.pulse=0.; self.visible=1.
    def beat(self,s=1.): self.pulse=min(1.,s)
    def upd(self,dt,lp):
        self.pulse*=math.exp(-1.8*dt); self.visible=_smooth(self.visible,1.-lp,6.,dt)
    def ring(self,surf,cx,cy,base_r):
        if self.visible<0.01: return
        r=int(base_r+self.offset_r+self.pulse*24)
        a=max(0,min(255,int((self.base_alpha+self.pulse*160)*self.visible)))
        if r>0 and a>0:
            pygame.gfxdraw.aacircle(surf,cx,cy,r,(255,255,255,a))
            if r>1: pygame.gfxdraw.aacircle(surf,cx,cy,r-1,(255,255,255,a//2))

class MenuAnimacije:
    def __init__(self,icon,label,color):
        self.icon=icon; self.label=label; self.color=color
        self.hover_val=0.; self.shimmer=0.; self.shimmer_active=False
        self.ripple=[]; self.scale=1.; self.push=0.
    def hover(self,is_hov,dt):
        self.hover_val=_smooth(self.hover_val,1. if is_hov else 0.,12.,dt)
        if is_hov and not self.shimmer_active: self.shimmer_active=True; self.shimmer=-0.3
        if self.shimmer_active:
            self.shimmer+=dt*1.7
            if self.shimmer>1.3: self.shimmer_active=False
        self.scale=_smooth(self.scale,1.10 if is_hov else 1.0,11.,dt)
    def click(self,rx,ry): self.ripple.append([float(rx),float(ry),0.])
    def update_ripples(self,dt): self.ripple=[[x,y,t+dt*2.] for x,y,t in self.ripple if t<1.]
    def izris(self,surf,ix,iy,iw,ih,drop_p,settings_active=False):
        am=min(1.,drop_p*2.); h=self.hover_val; cr,cg,cb=self.color
        diw=int(iw*self.scale); dih=int(ih*self.scale)
        dix=ix+(iw-diw)//2; diy=iy+(ih-dih)//2
        box=pygame.Surface((diw,dih),pygame.SRCALPHA)
        box.fill((cr//7,cg//7,cb//7,int((12+h*26)*am)))
        if h>0.01:
            ov=pygame.Surface((diw,dih),pygame.SRCALPHA); ov.fill((cr,cg,cb,int(h*32))); box.blit(ov,(0,0))
        if settings_active:
            pa=max(0,min(255,int(am*(125+40*math.sin(pygame.time.get_ticks()/420.)))))
            for go in range(3,0,-1):
                ga=int(pa*(1-go/4.)*0.45)
                pygame.draw.rect(box,(cr,cg,cb,ga),(-go,-go,diw+go*2,dih+go*2),1,border_radius=10+go)
            pygame.draw.rect(box,(cr,cg,cb,pa),box.get_rect(),2,border_radius=10)
            ti=pygame.Surface((diw,dih),pygame.SRCALPHA); ti.fill((cr,cg,cb,int(am*28))); box.blit(ti,(0,0))
        else:
            pygame.draw.rect(box,(int(_lerp(70,cr,h)),int(_lerp(70,cg,h)),int(_lerp(70,cb,h)),int((30+h*100)*am)),
                             box.get_rect(),1,border_radius=10)
        bh=int((dih-14)*h)
        if bh>2:
            bar=pygame.Surface((4,bh),pygame.SRCALPHA)
            for row in range(bh):
                t2=row/max(bh-1,1); ga=int(220*math.sin(t2*math.pi)*h*am)
                bar.set_at((0,row),(cr,cg,cb,ga)); bar.set_at((1,row),(cr,cg,cb,ga))
                bar.set_at((2,row),(cr,cg,cb,ga*2//3)); bar.set_at((3,row),(cr,cg,cb,ga//3))
            box.blit(bar,(0,(dih-bh)//2))
        if self.shimmer_active and am>0.3:
            sw2=diw//3; sx0=int(self.shimmer*(diw+sw2))-sw2
            for col in range(max(0,sx0),min(diw,sx0+sw2)):
                ga=int(math.sin((col-sx0)/max(sw2-1,1)*math.pi)*40*am)
                if ga>0: pygame.draw.line(box,(255,255,255,ga),(col,0),(col,dih-1))
        for rx2,ry2,rt in self.ripple:
            rr=int(rt*diw*1.5); ra=int((1-rt)*55*am)
            if rr>0 and ra>0:
                rip=pygame.Surface((rr*2,rr*2),pygame.SRCALPHA)
                pygame.gfxdraw.aacircle(rip,rr,rr,rr,(cr,cg,cb,ra))
                box.blit(rip,(int(rx2*(diw/iw))-rr,int(ry2*(dih/ih))-rr))
        surf.blit(box,(dix,diy))
        fi=_font(max(14,int(dih*0.38*(1+h*0.18))))
        ico=fi.render(self.icon,True,(int(_lerp(175,cr,h)),int(_lerp(185,cg,h)),int(_lerp(200,cb,h))))
        ico.set_alpha(min(255,int(205*am+h*50))); surf.blit(ico,(dix+int(24*(diw/iw)),diy+dih//2-ico.get_height()//2))
        fl=_font(max(14,int(dih*0.42)))
        lbl=fl.render(self.label,True,(int(_lerp(205,255,h)),int(_lerp(210,255,h)),int(_lerp(228,255,h))))
        lbl.set_alpha(min(255,int((185+h*70)*am))); surf.blit(lbl,(dix+int(60*(diw/iw)),diy+dih//2-lbl.get_height()//2))

class LepotniDodatkiAlNeki:
    def __init__(self):
        self.x=random.uniform(0,VIRT_W); self.y=random.uniform(0,VIRT_H)
        self.r=random.uniform(0.8,2.5); self.vx=random.uniform(-0.15,0.15)
        self.vy=random.uniform(-0.15,0.15); self.o=random.uniform(0.06,0.28)
    def update(self):
        self.x+=self.vx; self.y+=self.vy
        if not 0<=self.x<=VIRT_W: self.x=random.uniform(0,VIRT_W)
        if not 0<=self.y<=VIRT_H: self.y=random.uniform(0,VIRT_H)


# ══════════════════════════════════════════════════════════════════════════════
#  _ClassCard  –  animated dark-theme class card
# ══════════════════════════════════════════════════════════════════════════════
class _ClassCard:
    W, H = 420, 560

    def __init__(self, name, data):
        self.name=name; self.data=data; self.color=data["color"]
        self.hover=0.; self.scale=0.92; self.shimmer=0.
        self.shimmer_active=False; self.selected_flash=0.

    def set_hover(self,is_hov,dt):
        self.hover=_smooth(self.hover,1. if is_hov else 0.,10.,dt)
        if is_hov and not self.shimmer_active: self.shimmer_active=True; self.shimmer=-0.3
        if self.shimmer_active:
            self.shimmer+=dt*1.4
            if self.shimmer>1.3: self.shimmer_active=False
        self.scale=_smooth(self.scale,1.04 if is_hov else 1.0,9.,dt)

    def flash(self): self.selected_flash=1.0

    def kartica(self,surf,cx,cy,progress,beat=0.):
        if progress<=0: return
        ep=_ease_out_back(progress); h=self.hover; cr,cg,cb=self.color
        w=int(self.W*self.scale*ep); ht=int(self.H*self.scale*ep)
        if w<4 or ht<4: return
        x=cx-w//2; y=cy-ht//2
        card=pygame.Surface((w,ht),pygame.SRCALPHA)

        # background – original brightness
        card.fill((cr//6,cg//6,cb//6,int((22+h*30)*ep)))
        if h>0.01:
            ov=pygame.Surface((w,ht),pygame.SRCALPHA); ov.fill((cr,cg,cb,int(h*28))); card.blit(ov,(0,0))

        # selection flash
        if self.selected_flash>0.01:
            fov=pygame.Surface((w,ht),pygame.SRCALPHA)
            fov.fill((255,255,255,int(self.selected_flash*180))); card.blit(fov,(0,0))
            self.selected_flash*=0.75

        # border – original
        brd_a=int((35+h*120)*ep)
        pygame.draw.rect(card,(int(_lerp(60,cr,h)),int(_lerp(60,cg,h)),int(_lerp(70,cb,h)),brd_a),
                         card.get_rect(),2,border_radius=18)
        if beat>0.05:
            pygame.draw.rect(card,(cr,cg,cb,int(beat*80*ep)),card.get_rect(),3,border_radius=18)

        # left accent bar
        bar_ht=int(ht*0.7*ep); bar_y0=(ht-bar_ht)//2
        for bx2 in range(4):
            ba=int((80-bx2*20)*h*ep)
            if ba>0: pygame.draw.line(card,(cr,cg,cb,ba),(bx2,bar_y0),(bx2,bar_y0+bar_ht))

        # shimmer
        if self.shimmer_active:
            sw2=w//3; sx0=int(self.shimmer*(w+sw2))-sw2
            for col in range(max(0,sx0),min(w,sx0+sw2)):
                ga=int(math.sin((col-sx0)/max(sw2-1,1)*math.pi)*35*ep)
                if ga>0: pygame.draw.line(card,(255,255,255,ga),(col,0),(col,ht-1))

        surf.blit(card,(x,y))

        # icon – brighter color + alpha on hover
        icon_size=max(20,int(90*ep*self.scale))
        ico=_font(icon_size).render(self.data["icon"],True,
            (int(_lerp(160,min(255,cr+90),h)),int(_lerp(170,min(255,cg+90),h)),int(_lerp(200,255,h))))
        ico.set_alpha(min(255,int((180+h*75)*ep)))
        surf.blit(ico,(cx-ico.get_width()//2, y+int(28*ep)))

        # name – brighter + more opaque on hover
        ns=_font(max(12,int(52*ep)),bold=True).render(self.name,True,
            (int(_lerp(200,255,h)),)*3)
        ns.set_alpha(min(255,int((200+h*55)*ep)))
        surf.blit(ns,(cx-ns.get_width()//2, y+int(130*ep*self.scale)))

        # divider
        div_y=y+int(200*ep*self.scale)
        dw=max(1,w-40)
        ds=pygame.Surface((dw,1),pygame.SRCALPHA)
        ds.fill((cr,cg,cb,int(50*ep))); surf.blit(ds,(x+20,div_y))

        # stat bars
        bar_x=x+int(24*ep); bw=max(1,w-int(48*ep)); sy2=div_y+int(18*ep)
        lbl_size=max(8,int(20*ep)); fl2=_font(lbl_size)
        for sname,sval in self.data["stats"].items():
            pct=sval/STAT_MAX[sname]
            sl=fl2.render(sname,True,(int(_lerp(120,min(255,cr+70),h)),int(_lerp(130,min(255,cg+70),h)),int(_lerp(150,255,h))))
            sl.set_alpha(int((180+h*55)*ep)); surf.blit(sl,(bar_x,sy2))
            tk=pygame.Surface((bw,7),pygame.SRCALPHA); tk.fill((255,255,255,int(18*ep))); surf.blit(tk,(bar_x,sy2+lbl_size+3))
            fw2=int(bw*pct)
            if fw2>0:
                fill=pygame.Surface((fw2,7),pygame.SRCALPHA)
                for cx3 in range(fw2):
                    tg=cx3/max(fw2-1,1)
                    pygame.draw.line(fill,(int(_lerp(cr*.5,cr,tg)),int(_lerp(cg*.5,cg,tg)),
                                     int(_lerp(cb*.5,cb,tg)),int(_lerp(.3,.85,tg)*255*ep)),(cx3,0),(cx3,6))
                surf.blit(fill,(bar_x,sy2+lbl_size+3))
            sy2+=lbl_size+18

        # desc
        sy2+=int(8*ep); fd=_font(max(8,int(18*ep)))
        for line in self.data["desc"]:
            dl=fd.render(f"• {line}",True,(int(_lerp(140,238,h)),int(_lerp(148,244,h)),int(_lerp(165,255,h))))
            dl.set_alpha(int((155+h*65)*ep)); surf.blit(dl,(bar_x,sy2)); sy2+=max(8,int(18*ep))+6

        # select hint
        if h>0.05:
            fh=_font(max(8,int(22*ep)),bold=True).render("IZBERI  ▶",True,(cr,cg,cb))
            fh.set_alpha(int(h*220*ep))
            surf.blit(fh,(cx-fh.get_width()//2, y+ht-int(44*ep)))


# ══════════════════════════════════════════════════════════════════════════════
#  MainScreen
# ══════════════════════════════════════════════════════════════════════════════
class MainScreen:
    MENU_DATA = [
        ("▶","Igraj",        (100,200,255)),
        ("✦","Multiigralec", (180,140,255)),
        ("◈","Urednik",      (100,230,180)),
        ("◉","Nastavitve",   (200,200,200)),
        ("⏻","Izhod",        (255,130,130)),
    ]
    SETTINGS_IDX = 3
    LOGO_CENTER = CONSTANTS['LOGO_CENTER']
    LOGO_TARGET = CONSTANTS['LOGO_TARGET']
    LOGO_R_BIG = CONSTANTS['LOGO_R_BIG']
    LOGO_R_SMALL = CONSTANTS['LOGO_R_SMALL']
    ANIM_DUR = CONSTANTS['ANIM_DUR']
    MENU_IH = CONSTANTS['MENU_IH']
    MENU_IW = CONSTANTS['MENU_IW']
    MENU_GAP = CONSTANTS['MENU_GAP']
    CARD_Y = CONSTANTS['CARD_Y']
    CARD_SPACING = CONSTANTS['CARD_SPACING']
    CLASS_ANIM_DUR = CONSTANTS['CLASS_ANIM_DUR']

    def __init__(self,screen,clock,fps=60,vol_music=0.7,vol_sfx=0.5,settings=None):
        if settings is not None:
            vol_music = settings.vol_music
            vol_sfx   = settings.vol_sfx
            fps       = SettingsPanel.FPS_OPTIONS[settings.fps_idx]
        self.screen=screen; self.clock=clock; self.fps=fps
        self.canvas=pygame.Surface((VIRT_W,VIRT_H))
        self.font_small=_font(CONSTANTS['FONT_SIZES']['SMALL'])
        self.font_np=_font(CONSTANTS['FONT_SIZES']['NP'],bold=True)
        self.font_hint=_font(CONSTANTS['FONT_SIZES']['HINT'])
        self.vol_music=vol_music; self.vol_sfx=vol_sfx
        fps_opts=SettingsPanel.FPS_OPTIONS
        self.fps_idx=fps_opts.index(fps) if fps in fps_opts else 1

        pygame.mixer.set_num_channels(8)
        self._hover_ch=pygame.mixer.Channel(0); self._select_ch=pygame.mixer.Channel(1)
        self._logo_ch=pygame.mixer.Channel(2)
        self._sfx_hover=self._load_sfx(HOVER_SFX_PATH)
        self._sfx_select=self._load_sfx(SELECT_SFX_PATH)
        self._sfx_logo=self._load_sfx(LOGO_SFX_PATH)

        self._logo_img=None; self._logo_img_cache={}
        try:
            if os.path.exists(OSU_LOGO_PATH):
                self._logo_img=pygame.image.load(OSU_LOGO_PATH).convert_alpha()
        except Exception as e: print(f"Logo error: {e}")

        self.menu_open=False; self.logo_t=0.; self.menu_anim_t=0.
        self.hint_t=0.; self.hint_vis=1.; self.smooth_beat=0.; self.beat_flash=0.
        self.beat_times=[]; self.beat_idx=0; self.beats_ready=False
        self.music_start_t=None; self.prev_hovered=-1
        self.logo_beat_scale=1.; self.logo_hover_t=0.; self.halo_rings=[]
        self.logo_click_t=1.; self.logo_click_sx=1.; self.logo_click_sy=1.
        self.logo_click_flash=[]; self.music_vol_cur=vol_music*0.04; self.music_vol_target=vol_music
        self.logo_clicked_once=False

        self.particles=[LepotniDodatkiAlNeki() for _ in range(CONSTANTS['PARTICLE_COUNT'])]
        self.rings=[obročki(offset_r, base_alpha) for offset_r, base_alpha in zip(CONSTANTS['RING_OFFSETS'], CONSTANTS['RING_ALPHAS'])]
        self.menu_items=[MenuAnimacije(ic,lb,col) for ic,lb,col in self.MENU_DATA]
        self.eq_heights=[8.0]*6
        self.settings=(settings if settings is not None
                       else SettingsPanel(vol_music,vol_sfx,vol_sfx,vol_sfx,vol_sfx,self.fps_idx))

        # class select state
        self.class_cards=[_ClassCard(n,CLASS_DATA[n]) for n in CLASS_NAMES]
        self.cs_phase="hidden"   # hidden | in | idle | selected | out
        self.cs_t=0.; self.cs_card_t=[0.,0.,0.]
        self.cs_hovered=-1; self.cs_prev_hov=-1; self.cs_chosen=None
        self.menu_out_t=0.; self.title_alpha=0.

        self.vignette=pygame.Surface((VIRT_W,VIRT_H),pygame.SRCALPHA)
        for step in range(20,0,-1):
            rw=int(VIRT_W*step/20); rh=int(VIRT_H*step/20)
            pygame.draw.ellipse(self.vignette,(0,0,0,(20-step)*7),(VIRT_W//2-rw//2,VIRT_H//2-rh//2,rw,rh))

        self._start_music()
        threading.Thread(target=self._load_beats,daemon=True).start()

    def _load_sfx(self,path):
        try: return pygame.mixer.Sound(path) if os.path.exists(path) else None
        except: return None

    def _play_sfx(self,ch,snd,vol=0.5,vol_key='sfx'):
        if snd:
            vm={'sfx':self.settings.vol_sfx,'hover':self.settings.vol_hover,
                'click':self.settings.vol_click,'logo':self.settings.vol_logo}
            snd.set_volume(vol*vm.get(vol_key,self.settings.vol_sfx)); ch.stop(); ch.play(snd)

    def _start_music(self):
        if os.path.exists(MUSIC_PATH):
            try:
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.set_volume(self.vol_music*0.04)
                time.sleep(0.1); pygame.mixer.music.play(-1)
                self.music_start_t=time.time()
            except Exception as e: print(f"Music error: {e}")

    def stop_music(self, fade_ms=0):
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
            time.sleep(fade_ms / 1000.0)
        else:
            pygame.mixer.music.stop()

    def _load_beats(self):
        if not os.path.exists(MUSIC_PATH): self.beats_ready=True; return
        try: self.beat_times=_detect_beats(MUSIC_PATH)
        except Exception as e: print(f"Beat error: {e}")
        self.beats_ready=True

    def logo_pos(self):
        t_prog=_ease_in_out_quint(min(1., self.logo_t/self.ANIM_DUR))
        return (_lerp2(self.LOGO_CENTER, self.LOGO_TARGET, t_prog),
                _lerp(self.LOGO_R_BIG, self.LOGO_R_SMALL, t_prog),
                t_prog)

    def _is_over_logo(self, vmx, vmy, logo_cx, logo_cy, logo_r, margin=14):
        return math.hypot(vmx-logo_cx, vmy-logo_cy) < logo_r+margin

    def MouseTracer(self, vmx, vmy, logo_cx, logo_cy, logo_r):
        if self.menu_anim_t <= 0.2 or self.cs_phase != "hidden": return None
        bx,by = self._menu_base(logo_cx, logo_cy, logo_r)
        for i,item in enumerate(self.menu_items):
            iy = by + i*(self.MENU_IH + self.MENU_GAP) + int(item.push)
            if bx <= vmx <= bx + self.MENU_IW and iy <= vmy <= iy + self.MENU_IH:
                return i
        return None

    def _toggle_menu(self, logo_r):
        self.menu_open = not self.menu_open
        self.logo_clicked_once = True
        self._play_sfx(self._logo_ch, self._sfx_logo, 0.6, 'logo')
        if not self.menu_open:
            self.menu_anim_t = 0.; self.prev_hovered = -1
        self.music_vol_target = 0.3 if self.menu_open else 0.15
        self.logo_click_t = 0.; self.logo_click_flash = [[float(logo_r), 255.]]
        if self.settings.open: self.settings.open = False

    def _activate_menu_item(self, item_index, rel_x, rel_y):
        item = self.menu_items[item_index]
        self._play_sfx(self._select_ch, self._sfx_select, 0.6, 'click')
        item.click(rel_x, rel_y)
        label = self.MENU_DATA[item_index][1]
        if label == "Igraj":
            self._enter_class_select()
        elif label == "Izhod":
            return "quit"
        elif label == "Nastavitve":
            self.settings.toggle(self.settings.anchor_x, self.settings.anchor_y)
        return None

    def _handle_mouse_down(self, vmx, vmy, logo_cx, logo_cy, logo_r):
        if self.cs_phase == "idle" and self.cs_hovered >= 0:
            idx = self.cs_hovered
            self.cs_chosen = CLASS_NAMES[idx]
            self.class_cards[idx].flash()
            self._play_sfx(self._select_ch, self._sfx_select, 0.7, 'click')
            self.cs_phase = "selected"; self.cs_t = 0.
            return None

        if self.cs_phase != "hidden":
            return None

        if self._is_over_logo(vmx, vmy, logo_cx, logo_cy, logo_r):
            self._toggle_menu(logo_r)
            return None

        item_index = self.MouseTracer(vmx, vmy, logo_cx, logo_cy, logo_r)
        if item_index is None:
            return None

        bx,by = self._menu_base(logo_cx, logo_cy, logo_r)
        iy = by + item_index*(self.MENU_IH + self.MENU_GAP) + int(self.menu_items[item_index].push)
        return self._activate_menu_item(item_index, vmx-bx, vmy-iy)

    def get_scale(self):
        w,h=self.screen.get_size(); return min(w/VIRT_W,h/VIRT_H)

    def screen_to_virt(self,sx,sy):
        sc=self.get_scale(); w,h=self.screen.get_size()
        return (sx-(w-VIRT_W*sc)/2)/sc,(sy-(h-VIRT_H*sc)/2)/sc

    _LOGO_RENDER_R=200

    def _draw_logo(self,surf,cx,cy,r,pulse=0.,ring_vis=1.,hover_t=0.):
        cx=int(cx); cy=int(cy); r=int(r)
        if r<6: return
        if ring_vis>0.02:
            gr=r+int(pulse*16); ga=int((18+pulse*65)*ring_vis)
            if gr>0 and ga>0:
                tmp=pygame.Surface((gr*2+10,gr*2+10),pygame.SRCALPHA)
                pygame.gfxdraw.filled_circle(tmp,gr+5,gr+5,gr,(255,255,255,ga)); surf.blit(tmp,(cx-gr-5,cy-gr-5))
        if self._logo_img:
            sz=r*2
            if sz not in self._logo_img_cache:
                if len(self._logo_img_cache)>20: self._logo_img_cache.clear()
                self._logo_img_cache[sz]=pygame.transform.smoothscale(self._logo_img,(sz,sz))
            sc2=self._logo_img_cache[sz].copy()
            sc2.set_alpha(min(255,int(200+pulse*55+hover_t*55))); surf.blit(sc2,(cx-r,cy-r))

    def _menu_base(self,logo_cx,logo_cy,logo_r):
        return int(logo_cx-logo_r),int(logo_cy+logo_r+12)

    def _draw_menu(self,surf,progress,logo_cx,logo_cy,logo_r,dt,vmx,vmy):
        if progress<=0: return
        ih,iw=self.MENU_IH,self.MENU_IW
        bx,by=self._menu_base(logo_cx,logo_cy,logo_r)
        slide_out=_ease_in_cubic(min(1.,self.menu_out_t)); bx-=int(slide_out*420)

        focus_i=-1
        if self.cs_phase=="hidden":
            for i,item in enumerate(self.menu_items):
                p=max(0.,min(1.,(progress-i*0.09)/0.72))
                if p<=0: continue
                eop=_ease_out_expo(p)
                iy2=by+i*(ih+self.MENU_GAP)-int((1-eop)*26)+int(item.push)
                ix2=bx-int((1-eop)*20)
                if ix2<=vmx<=ix2+iw and iy2<=vmy<=iy2+ih: focus_i=i
        if focus_i!=self.prev_hovered and focus_i!=-1:
            self._play_sfx(self._hover_ch,self._sfx_hover,0.5,'hover')
        self.prev_hovered=focus_i

        for i,item in enumerate(self.menu_items):
            dist=i-focus_i if focus_i>=0 else 0
            pt=(12.*(1/abs(dist))*(1 if dist>0 else -1)) if(focus_i>=0 and dist!=0) else 0.
            item.push=_smooth(item.push,pt,9.,dt)

        settings_open=self.settings.t>0.05
        for i,item in enumerate(self.menu_items):
            p=max(0.,min(1.,(progress-i*0.09)/0.72))
            if p<=0: item.hover_val=0.; item.scale=1.; item.push=0.; continue
            ep=_ease_out_back(p); eop=_ease_out_expo(p)
            iy2=by+i*(ih+self.MENU_GAP)-int((1-eop)*26)+int(item.push)
            ix2=bx-int((1-eop)*20)
            is_hov=(i==focus_i); item.hover(is_hov,dt); item.update_ripples(dt)
            if focus_i>=0 and not is_hov:
                item.scale=_smooth(item.scale,max(0.85,1.-abs(i-focus_i)*0.04),9.,dt)
            is_set=(i==self.SETTINGS_IDX)
            if is_set and settings_open: item.scale=_smooth(item.scale,1.18,11.,dt)
            item.izris(surf,ix2+int(item.hover_val*3),iy2-int(item.hover_val*5),iw,ih,ep,
                      settings_active=(is_set and settings_open))

        if self.settings.t>0.015:
            panel_x=bx+iw+18; n=len(self.menu_items)
            total_menu_h=n*ih+(n-1)*self.MENU_GAP
            panel_total_h=len(self.settings.vrstice())*self.settings.ITEM_H+self.settings.PAD_TOP*2
            centre_y=by+total_menu_h//2; panel_y=centre_y-panel_total_h//2
            self.settings.anchor_x=panel_x; self.settings.anchor_y=panel_y
            self.settings.settings_UI(surf,vmx,vmy)

    # ── class select ──────────────────────────────────────────────────────────
    def _enter_class_select(self):
        self.cs_phase="in"; self.cs_t=0.; self.cs_card_t=[0.,0.,0.]
        self.cs_chosen=None; self.menu_out_t=0.; self.title_alpha=0.
        self._play_sfx(self._select_ch,self._sfx_select,0.5,'click')

    def _exit_class_select(self):
        if self.cs_phase in ("in","idle"):
            self.cs_phase="leaving"; self.cs_t=0.
            self.cs_hovered=-1; self.cs_prev_hov=-1
            self._play_sfx(self._select_ch,self._sfx_select,0.35,'click')

    def _update_class_select(self,dt):
        if self.cs_phase=="hidden": return
        if self.cs_phase=="in":
            self.cs_t=min(1.,self.cs_t+dt/self.CLASS_ANIM_DUR)
            self.menu_out_t=min(1.,self.menu_out_t+dt*3.5)
            for i in range(3):
                delay=i*0.12
                prog=max(0.,self.cs_t-delay)/max(1.-delay,0.01)
                self.cs_card_t[i]=min(1.,prog)
            if self.cs_t>=1.: self.cs_phase="idle"
        elif self.cs_phase=="selected":
            self.cs_t=min(1.,self.cs_t+dt*2.5)
            if self.cs_t>=1.: self.cs_phase="zoom"; self.cs_t=0.
        elif self.cs_phase=="zoom":
            self.cs_t=min(1.,self.cs_t+dt*1.6)
            if self.cs_t>=1.: self.cs_phase="out"; self.cs_t=0.
        elif self.cs_phase=="out":
            self.cs_t=min(1.,self.cs_t+dt*1.8)
        elif self.cs_phase=="leaving":
            self.cs_t=min(1.,self.cs_t+dt*2.0)
            self.menu_out_t=max(0.,self.menu_out_t-dt*3.5)
            for i in range(3):
                delay=(2-i)*0.10
                prog=max(0.,self.cs_t-delay)/max(1.-delay,0.01)
                self.cs_card_t[i]=max(0.,1.-min(1.,prog))
            if self.cs_t>=1.:
                self.cs_phase="hidden"; self.cs_t=0.; self.cs_card_t=[0.,0.,0.]
                self.cs_chosen=None; self.menu_out_t=0.; self.title_alpha=0.
                self.cs_hovered=-1; self.cs_prev_hov=-1

    def _draw_class_select(self,surf,dt,vmx,vmy):
        if self.cs_phase=="hidden": return

        # overall progress — only used for "in" phase; stays 1.0 for all later phases
        if self.cs_phase in("in",):
            overall=_ease_out_cubic(self.cs_t)
        else:
            overall=1.0

        # title
        if self.cs_phase in("in","idle","selected"):
            tgt_alpha=overall*255
        elif self.cs_phase=="zoom":
            tgt_alpha=int(_lerp(255,0,_ease_in_cubic(self.cs_t)))
        elif self.cs_phase=="leaving":
            tgt_alpha=0
        else:  # out
            tgt_alpha=0
        self.title_alpha=_smooth(self.title_alpha,tgt_alpha,10.,dt)
        if self.title_alpha>3:
            if self.cs_phase=="leaving":
                leave_prog=_ease_in_cubic(self.cs_t)
                title_y=int(_lerp(100,VIRT_H//2-40,leave_prog))
            else:
                title_y=int(_lerp(VIRT_H//2-80,100,overall))
            ft=_font(max(14,int(62*overall)),bold=True)
            ts=ft.render("Izberi razred",True,(220,228,255))
            ts.set_alpha(int(self.title_alpha*0.85))
            surf.blit(ts,(VIRT_W//2-ts.get_width()//2,title_y))
            fs=_font(max(8,int(26*overall)))
            sub=fs.render("Klikni na razred ali pritisni  1 / 2 / 3",True,(100,108,130))
            sub.set_alpha(int(self.title_alpha*0.6))
            surf.blit(sub,(VIRT_W//2-sub.get_width()//2,title_y+int(72*overall)))

        # cards
        n=len(self.class_cards); total_w=(n-1)*self.CARD_SPACING
        start_x=VIRT_W//2-total_w//2
        self.cs_hovered=-1

        for i,card in enumerate(self.class_cards):
            cx=start_x+i*self.CARD_SPACING; cy=self.CARD_Y; p=self.cs_card_t[i]
            if p<=0: continue
            if self.cs_phase=="idle":
                hw=int(card.W*card.scale*_ease_out_back(p))//2
                hh=int(card.H*card.scale*_ease_out_back(p))//2
                if cx-hw<=vmx<=cx+hw and cy-hh<=vmy<=cy+hh: self.cs_hovered=i

        if self.cs_hovered!=self.cs_prev_hov and self.cs_hovered!=-1:
            self._play_sfx(self._hover_ch,self._sfx_hover,0.4,'hover')
        self.cs_prev_hov=self.cs_hovered

        chosen_idx=CLASS_NAMES.index(self.cs_chosen) if self.cs_chosen else -1

        for i,card in enumerate(self.class_cards):
            cx=start_x+i*self.CARD_SPACING; cy=self.CARD_Y; p=self.cs_card_t[i]
            if p<=0: continue

            if self.cs_phase=="zoom":
                zoom_p=_ease_in_out_quint(self.cs_t)
                if i==chosen_idx:
                    # chosen card slides to center and scales up
                    cx=int(_lerp(cx,VIRT_W//2,zoom_p))
                    cy=int(_lerp(cy,VIRT_H//2,zoom_p))
                    p=_lerp(p,2.0,zoom_p)   # scale beyond 1 for zoom feel
                else:
                    # other cards fade out and drift away
                    drift=300*(1 if i<chosen_idx else -1)
                    cx+=int(zoom_p*drift)
                    p=_lerp(p,0.,zoom_p)
            elif self.cs_phase=="out":
                out_p=_ease_in_cubic(self.cs_t)
                if i==chosen_idx:
                    # chosen card continues zooming and fading
                    cx=VIRT_W//2; cy=VIRT_H//2
                    p=_lerp(2.0,3.5,out_p)
                    # draw with decreasing alpha handled via card alpha below
                else:
                    p=0.; continue
            elif self.cs_phase=="leaving":
                cy+=int(_ease_in_cubic(self.cs_t)*70)

            card.set_hover(self.cs_hovered==i,dt)
            # for "out" phase, reduce alpha on chosen card
            if self.cs_phase=="out" and i==chosen_idx:
                card._exit_alpha=int(_lerp(255,0,_ease_in_cubic(self.cs_t)))
            else:
                card._exit_alpha=-1
            card.kartica(surf,cx,cy,min(p,1.0),self.smooth_beat)

        # full-screen fade to black during out phase
        if self.cs_phase=="out":
            fa=int(_ease_in_cubic(self.cs_t)*255)
            if fa>0:
                fov=pygame.Surface((VIRT_W,VIRT_H),pygame.SRCALPHA)
                fov.fill((0,0,0,fa)); surf.blit(fov,(0,0))

        if self.cs_phase=="idle" and overall>0.8:
            fk=_font(max(8,int(20*overall)))
            ks=fk.render("[ ESC ] Nazaj",True,(70,75,95))
            ks.set_alpha(int(120*overall)); surf.blit(ks,(40,VIRT_H-50))

    def _handle_keydown(self,event):
        if event.key==pygame.K_ESCAPE:
            if self.cs_phase in("in","idle"): self._exit_class_select()
            elif self.settings.open: self.settings.open=False
            elif self.menu_open: self.menu_open=False; self.menu_anim_t=0.
            else: return "quit"
        if self.cs_phase=="idle":
            for ki,key in enumerate([pygame.K_1,pygame.K_2,pygame.K_3]):
                if event.key==key:
                    self.cs_chosen=CLASS_NAMES[ki]; self.class_cards[ki].flash()
                    self._play_sfx(self._select_ch,self._sfx_select,0.7,'click')
                    self.cs_phase="selected"; self.cs_t=0.
        return None

    def _update_logo_menu_state(self,dt,vmx,vmy):
        self.logo_t = min(self.logo_t+dt,self.ANIM_DUR) if self.menu_open else max(self.logo_t-dt*1.1,0.)
        t_prog=_ease_in_out_quint(min(1.,self.logo_t/self.ANIM_DUR))
        logo_cx,logo_cy=_lerp2(self.LOGO_CENTER,self.LOGO_TARGET,t_prog)
        logo_r=_lerp(self.LOGO_R_BIG,self.LOGO_R_SMALL,t_prog)
        hover_logo=self._is_over_logo(vmx,vmy,logo_cx,logo_cy,logo_r)
        self.logo_hover_t=_smooth(self.logo_hover_t,1. if hover_logo else 0.,10.,dt)
        self.hint_vis=_smooth(self.hint_vis,0. if(self.menu_open or self.logo_t>0.05) else 1.,5.,dt)
        if self.menu_open and self.logo_t>=self.ANIM_DUR*0.65:
            self.menu_anim_t=min(self.menu_anim_t+dt*1.6,1.)
        elif not self.menu_open:
            self.menu_anim_t=max(self.menu_anim_t-dt*4.,0.)
            if self.menu_anim_t<=0 and self.settings.open: self.settings.open=False
        return logo_cx, logo_cy, logo_r, t_prog, hover_logo

    def _update_music_state(self,dt):
        self.settings.zazeni(dt)
        if not self.logo_clicked_once:
            vol_tgt=self.settings.vol_music*0.04
        else:
            vol_tgt=self.settings.vol_music*(0.30 if self.menu_open else 0.14)
        self.music_vol_cur=_smooth(self.music_vol_cur,vol_tgt,4.,dt)
        pygame.mixer.music.set_volume(self.music_vol_cur)

    def _update_beat_state(self,logo_r,dt):
        if not (self.music_start_t and self.beats_ready and self.beat_times):
            return
        elapsed=(time.time()-self.music_start_t)%137.7
        while self.beat_idx<len(self.beat_times) and self.beat_times[self.beat_idx][0]<elapsed-0.05:
            self.beat_idx+=1
        if self.beat_idx>=len(self.beat_times): self.beat_idx=0
        if self.beat_idx<len(self.beat_times) and abs(elapsed-self.beat_times[self.beat_idx][0])<0.06:
            _,bs=self.beat_times[self.beat_idx]
            self.beat_flash=bs
            for ring in self.rings: ring.beat(bs)
            self.logo_beat_scale=min(1.10,self.logo_beat_scale+bs*0.07)
            self.halo_rings.append([float(logo_r),180.*bs,bs]); self.beat_idx+=1

    def _update_click_state(self,dt):
        if self.logo_click_t<1.:
            self.logo_click_t=min(1.,self.logo_click_t+dt/CONSTANTS['LOGO_CLICK_DUR'])
            ct=self.logo_click_t
            if ct<0.22:
                p=_ease_in_out_quint(ct/0.22)
                self.logo_click_sx=_lerp(1.,0.78,p); self.logo_click_sy=_lerp(1.,0.82,p)
            else:
                p=_ease_out_cubic((ct-0.22)/0.78)
                self.logo_click_sx=_lerp(0.78,1.,p); self.logo_click_sy=_lerp(0.82,1.,p)
        else:
            self.logo_click_sx=self.logo_click_sy=1.
        self.logo_click_flash=[[r+dt*520.,a-dt*900.] for r,a in self.logo_click_flash if a-dt*900.>0]
        self.halo_rings=[[r+dt*(300.+s*80.),a-dt*420.*s,s] for r,a,s in self.halo_rings if a-dt*420.*s>0]

    def _update_cursor(self,vmx,vmy,logo_cx,logo_cy,logo_r,hover_logo):
        if hover_logo: return True
        if self.menu_anim_t>0.2 and self.cs_phase=="hidden":
            mnx=logo_cx-logo_r; mny=logo_cy+logo_r+12
            if any(mnx<=vmx<=mnx+self.MENU_IW and mny+i*(self.MENU_IH+self.MENU_GAP)+item.push<=vmy<=mny+i*(self.MENU_IH+self.MENU_GAP)+item.push+self.MENU_IH
                   for i,item in enumerate(self.menu_items)):
                return True
        return self.cs_phase=="idle" and self.cs_hovered>=0

    def _render_frame(self,dt,vmx,vmy,logo_cx,logo_cy,logo_r,t_prog):
        self.canvas.fill(BG)
        for p in self.particles:
            p.update(); r2=max(1,int(p.r)); a2=int(p.o*255)
            pygame.gfxdraw.filled_circle(self.canvas,int(p.x),int(p.y),r2,(255,255,255,a2))
            pygame.gfxdraw.aacircle(self.canvas,int(p.x),int(p.y),r2,(255,255,255,a2))
        self._draw_bg_glow(self.canvas,self.smooth_beat,t_prog)
        for ring in self.rings: ring.ring(self.canvas,int(logo_cx),int(logo_cy),self.LOGO_R_BIG)
        for r,a,s in self.halo_rings:
            hr=int(r); ha=max(0,min(255,int(a)))
            if hr>0 and ha>0:
                pygame.gfxdraw.aacircle(self.canvas,int(logo_cx),int(logo_cy),hr,(255,255,255,ha))
                if hr>2: pygame.gfxdraw.aacircle(self.canvas,int(logo_cx),int(logo_cy),hr-2,(200,220,255,ha//2))
        for cf_r,cf_a in self.logo_click_flash:
            cr2=int(cf_r); ca=max(0,min(255,int(cf_a)))
            if cr2>0 and ca>0: pygame.gfxdraw.aacircle(self.canvas,int(logo_cx),int(logo_cy),cr2,(255,255,255,ca))

        hover_scale=1.0+0.08*self.logo_hover_t
        beat_r=logo_r*self.logo_beat_scale*hover_scale; base_size=int(beat_r*2)
        if base_size>=4:
            rx2=max(4,int(base_size*self.logo_click_sx)); ry2=max(4,int(base_size*self.logo_click_sy))
            tmp2=pygame.Surface((base_size,base_size),pygame.SRCALPHA)
            self._draw_logo(tmp2,base_size//2,base_size//2,int(beat_r),self.smooth_beat,1.-t_prog,self.logo_hover_t)
            stretched=pygame.transform.smoothscale(tmp2,(rx2,ry2)) if(rx2!=base_size or ry2!=base_size) else tmp2
            self.canvas.blit(stretched,(int(logo_cx)-rx2//2,int(logo_cy)-ry2//2))

        if self.hint_vis>0.01:
            a3=max(0,min(255,int((155+math.sin(self.hint_t*2.)*70)*self.hint_vis)))
            hs=self.font_hint.render("K L I K N I",True,(a3,a3,a3))
            self.canvas.blit(hs,hs.get_rect(center=(self.LOGO_CENTER[0],self.LOGO_CENTER[1]+self.LOGO_R_BIG+28)))

        if self.menu_anim_t>0:
            self._draw_menu(self.canvas,self.menu_anim_t,logo_cx,logo_cy,logo_r,dt,vmx,vmy)

        self._draw_class_select(self.canvas,dt,vmx,vmy)
        self._draw_now_playing(self.canvas,self.smooth_beat,dt)
        self.canvas.blit(self.vignette,(0,0))

        sc=self.get_scale(); sw,sh=self.screen.get_size()
        sw2=int(VIRT_W*sc); sh2=int(VIRT_H*sc)
        self.screen.fill((0,0,0))
        self.screen.blit(pygame.transform.smoothscale(self.canvas,(sw2,sh2)),((sw-sw2)//2,(sh-sh2)//2))
        pygame.display.flip()

    def _draw_now_playing(self,surf,bass,dt):
        x,y=28,VIRT_H-78
        for i,tgt in enumerate([bass*.9,bass*.65,bass,bass*.75,bass*.55,bass*.8]):
            self.eq_heights[i]=_smooth(self.eq_heights[i],tgt*28+5,12.,dt)
        for i,h in enumerate(self.eq_heights):
            bh=int(h); pygame.draw.rect(surf,(180,205,230),(x+i*6,y+30-bh,4,bh),border_radius=2)
        surf.blit(self.font_small.render("ZDAJ IGRA",True,(100,100,130)),(x+44,y+2))
        surf.blit(self.font_np.render("Lobby  (2020 Version)",True,(220,228,255)),(x+44,y+18))
        surf.blit(self.font_small.render("Flood Escape 2 OST",True,(100,100,130)),(x+44,y+36))

    def _draw_bg_glow(self,surf,bass,lp):
        vis=1.-lp
        if bass<0.04 or vis<0.01: return
        gw=int(VIRT_W*.6); tmp=pygame.Surface((gw,gw),pygame.SRCALPHA); c=gw//2; a=int(bass*40*vis)
        for ri in range(6,0,-1):
            pygame.gfxdraw.filled_circle(tmp,c,c,gw//2*ri//6,(65,105,185,a*ri//6))
        surf.blit(tmp,(VIRT_W//2-gw//2,VIRT_H//2-gw//2),special_flags=pygame.BLEND_ADD)

    # ── run ───────────────────────────────────────────────────────────────────
    def run(self):
        """Returns 'quit' or ('play', class_name)."""
        running=True; result=None; LOGO_CLICK_DUR=CONSTANTS['LOGO_CLICK_DUR']

        while running:
            fps_target=SettingsPanel.FPS_OPTIONS[self.settings.fps_idx]
            dt=min(self.clock.tick(fps_target)/1000.,0.05)
            self.hint_t+=dt
            vmx,vmy=self.screen_to_virt(*pygame.mouse.get_pos())
            (logo_cx,logo_cy),logo_r,t_prog=self.logo_pos()

            # class-select-out done → return
            if self.cs_phase=="out" and self.cs_t>=1. and self.cs_chosen:
                result=("play",self.cs_chosen); break

            for event in pygame.event.get():
                if event.type==pygame.QUIT: return "quit"
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:
                        if self.cs_phase in("in","idle"): self._exit_class_select()
                        elif self.settings.open:          self.settings.open=False
                        elif self.menu_open:              self.menu_open=False; self.menu_anim_t=0.
                        else:                             return "quit"
                    if self.cs_phase=="idle":
                        for ki,key in enumerate([pygame.K_1,pygame.K_2,pygame.K_3]):
                            if event.key==key:
                                self.cs_chosen=CLASS_NAMES[ki]; self.class_cards[ki].flash()
                                self._play_sfx(self._select_ch,self._sfx_select,0.7,'click')
                                self.cs_phase="selected"; self.cs_t=0.

                if self.settings.t>0.05 and self.cs_phase=="hidden":
                    if self.settings.event_handler(event,vmx,vmy):
                        pygame.mixer.music.set_volume(self.settings.vol_music); continue

                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    result=self._handle_mouse_down(vmx,vmy,logo_cx,logo_cy,logo_r)
                    if result=="quit":
                        running=False; break

                if event.type==pygame.VIDEORESIZE:
                    self.screen=pygame.display.set_mode(event.size,pygame.RESIZABLE)

            self._update_class_select(dt)
            logo_cx,logo_cy,logo_r,t_prog,hover_logo=self._update_logo_menu_state(dt,vmx,vmy)
            self._update_music_state(dt)
            self._update_beat_state(logo_r,dt)
            self.beat_flash*=math.exp(-2.2*dt)
            self.smooth_beat=_smooth(self.smooth_beat,self.beat_flash,5.,dt)
            self.logo_beat_scale=max(0.98,min(1.10,_smooth(self.logo_beat_scale,1.,4.5,dt)))
            self._update_click_state(dt)
            for ring in self.rings: ring.upd(dt,t_prog)
            self._render_frame(dt,vmx,vmy,logo_cx,logo_cy,logo_r,t_prog)
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self._update_cursor(vmx,vmy,logo_cx,logo_cy,logo_r,hover_logo) else pygame.SYSTEM_CURSOR_ARROW)

        return result or "quit"

    @property
    def current_vol_music(self): 
        return self.settings.vol_music
    @property
    def current_vol_sfx(self):   
        return self.settings.vol_sfx
    @property
    def current_fps(self):       
        return SettingsPanel.FPS_OPTIONS[self.settings.fps_idx]