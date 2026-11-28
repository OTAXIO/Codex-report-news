"""Cornerstone template ornaments (2026-11-26, user-approved v4 samples), drawn from the costume language of the film's characters (original drawings):
six wings whose coverts carry eyes (the seraph), an angular crown crest with an eye (the masked figure),
a mantle trim of round coins, gold hanging spikes, white stencil plaques with the snake staff and the
Moebius star, astrolabe linework from the blueprint scene, a shard halo. Palette: Klein, ink, white, gold."""
import math, random
from pathlib import Path
_OUT = Path('.')
KLEIN = '#2335E8'; INK = '#0B1236'; DEEP = '#16229A'
GOLD = ('<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFF1BE"/>'
        '<stop offset=".45" stop-color="#E2B24C"/><stop offset="1" stop-color="#8A6418"/></linearGradient>')


def svg(name, w, h, body, defs=''):
    (_OUT / name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                             f'<defs>{GOLD}{defs}</defs>{body}</svg>', encoding='utf-8')


def star4(x, y, r, fill='#fff', op=1.0, k=.2):
    q = r * k
    return (f'<path d="M{x:.1f} {y-r:.1f}L{x+q:.1f} {y-q:.1f}L{x+r:.1f} {y:.1f}L{x+q:.1f} {y+q:.1f}L{x:.1f} {y+r:.1f}'
            f'L{x-q:.1f} {y+q:.1f}L{x-r:.1f} {y:.1f}L{x-q:.1f} {y-q:.1f}Z" fill="{fill}" fill-opacity="{op}"/>')


def starfield(x0, y0, x1, y1, n, seed, op=(.15, .7)):
    rnd = random.Random(seed); s = []
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(.6,1.7):.1f}" fill="#fff" fill-opacity="{rnd.uniform(*op):.2f}"/>')
    return ''.join(s)


# ---------- wings ----------
def feather(L, w, style, eye=False):
    """style: 'line' (lacy outline primary), 'semi' (white secondary), 'solid' (covert)."""
    d = f'M0 0C{L*.28:.1f} {-w:.1f} {L*.7:.1f} {-w*1.05:.1f} {L:.1f} 0C{L*.7:.1f} {w*1.05:.1f} {L*.28:.1f} {w:.1f} 0 0Z'
    if style == 'line':
        s = (f'<path d="{d}" fill="#fff" fill-opacity=".12" stroke="#fff" stroke-opacity=".95" stroke-width="1.5"/>'
             f'<path d="M{L*.05:.1f} 0H{L*.95:.1f}" stroke="#fff" stroke-opacity=".7" stroke-width="1"/>')
        for t in (.3, .44, .58, .72, .84):
            x = L * t; hw = w * .8 * (1 - abs(t - .55) * 1.1)
            s += f'<path d="M{x:.1f} 0L{x+hw*.9:.1f} {-hw:.1f}M{x:.1f} 0L{x+hw*.9:.1f} {hw:.1f}" stroke="#fff" stroke-opacity=".5" stroke-width="1"/>'
    elif style == 'semi':
        s = (f'<path d="{d}" fill="#fff" fill-opacity=".9" stroke="{DEEP}" stroke-opacity=".35" stroke-width="1.1"/>'
             f'<path d="M{L*.1:.1f} 0H{L*.86:.1f}" stroke="{DEEP}" stroke-opacity=".35" stroke-width="1.1"/>')
    else:
        s = (f'<path d="{d}" fill="#fff" stroke="{DEEP}" stroke-opacity=".5" stroke-width="1.2"/>'
             f'<path d="M{L*.1:.1f} 0H{L*.5:.1f}" stroke="{DEEP}" stroke-opacity=".4" stroke-width="1.1"/>')
    if eye:
        ex, ew = L * .62, w * .62
        s += (f'<path d="M{ex-ew*1.7:.1f} 0Q{ex:.1f} {-ew*1.15:.1f} {ex+ew*1.7:.1f} 0Q{ex:.1f} {ew*1.15:.1f} {ex-ew*1.7:.1f} 0Z" fill="{KLEIN}"/>'
              f'<circle cx="{ex:.1f}" cy="0" r="{ew*.5:.1f}" fill="#fff"/><circle cx="{ex:.1f}" cy="0" r="{ew*.2:.1f}" fill="{INK}"/>')
    return s


def wing(Lw=140, H=80, Lp=125, w=13, eyes=True):
    """A spread wing pointing right (y down): a white wing bone rising to the upper tip, lacy primaries
    from its outer half, white secondaries hanging from its inner half, two rows of coverts with eyes."""
    def E(t):
        return 2 * (1 - t) * t * Lw * .3 + t * t * Lw, 2 * (1 - t) * t * (-H * 1.15) + t * t * (-H)
    s = []
    n = 7
    for i in range(n):
        u = i / (n - 1); x, y = E(.45 + .55 * u)
        s.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({44 - 56*u:.1f})">{feather(Lp*(.6+.4*u), w, "line")}</g>')
    m = 6
    for i in range(m):
        u = i / (m - 1); x, y = E(.04 + .5 * u)
        s.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({96 - 40*u:.1f})">{feather(Lp*(.58+.12*u), w*.95, "semi")}</g>')
    for row, (L, w2, t0, t1, a0, a1) in enumerate(((Lp * .36, w * 1.1, .02, .86, 84, 22), (Lp * .22, w * .95, .06, .9, 70, 12))):
        k = 7 if row == 0 else 8
        for i in range(k):
            u = i / (k - 1); x, y = E(t0 + (t1 - t0) * u)
            s.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({a0 + (a1-a0)*u:.1f})">{feather(L, w2, "solid", eye=eyes and row == 0 and i % 2 == 1)}</g>')
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (E(i / 24) for i in range(25)))
    s.append(f'<polyline points="{pts}" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round"/>'
             f'<polyline points="{pts}" fill="none" stroke="{KLEIN}" stroke-width="1.6" stroke-dasharray="10 6"/>')
    tx, ty = E(1)
    s.append(star4(tx + 6, ty - 4, 9, '#fff'))
    return ''.join(s)


def six_wings(cx, cy, k=1.0):
    W = wing()
    right = (f'<g transform="translate(150,-138) rotate(-38) scale(.8)">{W}</g>'
             f'<g transform="translate(150,146) rotate(48) scale(.72)">{W}</g>'
             f'<g transform="translate(198,8)">{W}</g>')
    return (f'<g transform="translate({cx},{cy}) scale({k})">'
            f'<g>{right}</g><g transform="scale(-1,1)">{right}</g></g>')


# ---------- small ornaments ----------
def pendant(x, rod, L=104, w=13, col='#E2B24C'):
    y = rod + 10
    return (f'<path d="M{x} 0V{rod}" stroke="{col}" stroke-width="1.4"/><circle cx="{x}" cy="{rod+5}" r="4.5" fill="none" stroke="{col}" stroke-width="1.8"/>'
            f'<path d="M{x} {y}L{x+w} {y+L*.3:.1f}L{x} {y+L}L{x-w} {y+L*.3:.1f}Z" fill="url(#gold)"/>'
            f'<path d="M{x} {y}V{y+L}" stroke="#FFF6D6" stroke-opacity=".75" stroke-width="1"/>'
            f'<path d="M{x-w} {y+L*.3:.1f}H{x+w}" stroke="#6E4E12" stroke-opacity=".6" stroke-width="1"/>')


def blade(x, rod, L=150, w=9):
    """A hanging spearhead like the film's gold spikes: guard, long faceted blade."""
    y = rod + 8
    return (f'<path d="M{x} 0V{rod}" stroke="#E2B24C" stroke-width="1.2"/><circle cx="{x}" cy="{rod+4}" r="3.5" fill="#E2B24C"/>'
            f'<path d="M{x-14} {y+6}H{x+14}L{x+8} {y+12}H{x-8}Z" fill="url(#gold)"/>'
            f'<path d="M{x} {y+12}L{x+w} {y+40}L{x+w*.55:.1f} {y+L*.72:.1f}L{x} {y+L}L{x-w*.55:.1f} {y+L*.72:.1f}L{x-w} {y+40}Z" fill="url(#gold)"/>'
            f'<path d="M{x} {y+12}V{y+L}" stroke="#FFF6D6" stroke-opacity=".7" stroke-width="1"/>')


def coin(x, y, r, ring=KLEIN):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{r*.72:.1f}" fill="none" stroke="{ring}" stroke-width="{max(1.2,r*.13):.1f}"/>'
            + star4(x, y, r * .5, ring))


def astrolabe(cx, cy, k=1.0):
    s = [f'<g transform="translate({cx},{cy}) scale({k})" fill="none" stroke="#fff">',
         '<circle r="330" stroke-opacity=".42" stroke-width="1.2"/>',
         '<circle r="372" stroke-opacity=".6" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="0 10"/>',
         '<circle r="412" stroke-opacity=".22" stroke-width="1"/>',
         '<circle r="454" stroke-opacity=".2" stroke-width="1" stroke-dasharray="36 12"/>']
    for a in range(0, 360, 5):
        r1 = 356 if a % 30 == 0 else 344
        c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
        s.append(f'<path d="M{334*c:.1f} {334*sn:.1f}L{r1*c:.1f} {r1*sn:.1f}" stroke-opacity="{.7 if a%30==0 else .4}" stroke-width="{1.5 if a%30==0 else 1}"/>')
    s.append('</g>')
    for a in (45, 135, 225, 315):
        s.append(star4(cx + 412 * k * math.cos(math.radians(a)), cy + 412 * k * math.sin(math.radians(a)), 10 * k, '#fff', .85))
    for sx in (-1, 1):
        s.append(''.join(f'<circle cx="{cx+sx*372*k+d*15*k:.1f}" cy="{cy}" r="{4.5*k:.1f}" fill="#fff"/>' for d in (-1, 0, 1)))
    return ''.join(s)


def floor(cx, fy, k=1.0):
    return (f'<g fill="none" stroke="#fff"><ellipse cx="{cx}" cy="{fy}" rx="{400*k}" ry="{28*k}" stroke-opacity=".34" stroke-width="1.4"/>'
            f'<ellipse cx="{cx}" cy="{fy}" rx="{300*k}" ry="{21*k}" stroke-opacity=".3" stroke-width="1.2"/>'
            f'<ellipse cx="{cx}" cy="{fy}" rx="{205*k}" ry="{14*k}" stroke-opacity=".28" stroke-width="1.2" stroke-dasharray="3 7"/>'
            f'<ellipse cx="{cx}" cy="{fy}" rx="{115*k}" ry="{8*k}" stroke-opacity=".34" stroke-width="1"/></g>')


def trim(H, x=0):
    """Mantle trim: a deep band with a row of coins, flanked by white rules."""
    s = [f'<rect x="{x}" width="28" height="{H}" fill="{DEEP}"/>',
         f'<path d="M{x+3} 0V{H}M{x+25} 0V{H}" stroke="#fff" stroke-opacity=".55" stroke-width="1"/>',
         f'<path d="M{x+14} 0V{H}" stroke="#fff" stroke-opacity=".35" stroke-width="1"/>']
    for y in range(30, H - 10, 52):
        s.append(coin(x + 14, y, 8))
        s.append(f'<path d="M{x+14} {y+15}L{x+17} {y+26}L{x+14} {y+37}L{x+11} {y+26}Z" fill="#fff" fill-opacity=".7"/>')
    return ''.join(s)


def constellation(pts, moon=None):
    s = [f'<path d="M{" L".join(f"{x} {y}" for x,y in pts)}" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1.1"/>']
    s += [f'<circle cx="{x}" cy="{y}" r="3.2" fill="#fff"/>' for x, y in pts]
    if moon:
        mx, my, mr = moon
        s.append(f'<circle cx="{mx}" cy="{my}" r="{mr}" fill="#fff"/><circle cx="{mx+mr+16}" cy="{my+14}" r="9" fill="none" stroke="#fff" stroke-width="1.8"/>')
    return ''.join(s)


def grid_patch(x, y, w, h, cell=21):
    return (f'<g stroke="#fff" stroke-opacity=".32" stroke-width="1">'
            + ''.join(f'<path d="M{x+i} {y}V{y+h}"/>' for i in range(0, w + 1, cell))
            + ''.join(f'<path d="M{x} {y+j}H{x+w}"/>' for j in range(0, h + 1, cell)) + '</g>')


# ---------- crest (angular crown with the eye) ----------
def crest(cx, top, k=1.0):
    y = top
    plates = []
    for sx in (1, -1):
        P = lambda pts: ' '.join(f'{cx+sx*px*k:.1f},{y+py*k:.1f}' for px, py in pts)
        plates.append(f'<polygon points="{P([(22,104),(40,30),(56,52),(40,112)])}" fill="#fff"/>')
        plates.append(f'<polygon points="{P([(48,112),(84,46),(96,72),(64,118)])}" fill="#fff" fill-opacity=".95"/>')
        plates.append(f'<polygon points="{P([(72,120),(124,78),(130,100),(90,126)])}" fill="#fff" fill-opacity=".9"/>')
        plates.append(f'<polygon points="{P([(98,128),(160,108),(160,122),(110,132)])}" fill="#fff" fill-opacity=".8"/>')
        plates.append(f'<path d="M{cx+sx*40*k:.1f} {y+30*k:.1f}L{cx+sx*44*k:.1f} {y+108*k:.1f}M{cx+sx*84*k:.1f} {y+46*k:.1f}L{cx+sx*70*k:.1f} {y+116*k:.1f}" stroke="{DEEP}" stroke-opacity=".45" stroke-width="1.2"/>')
    eye = (f'<path d="M{cx} {y-6*k:.1f}Q{cx+34*k:.1f} {y+56*k:.1f} {cx} {y+120*k:.1f}Q{cx-34*k:.1f} {y+56*k:.1f} {cx} {y-6*k:.1f}Z" fill="#fff"/>'
           f'<path d="M{cx} {y+6*k:.1f}Q{cx+24*k:.1f} {y+56*k:.1f} {cx} {y+106*k:.1f}Q{cx-24*k:.1f} {y+56*k:.1f} {cx} {y+6*k:.1f}Z" fill="none" stroke="{KLEIN}" stroke-width="{2*k:.1f}"/>'
           f'<circle cx="{cx}" cy="{y+56*k:.1f}" r="{15*k:.1f}" fill="{KLEIN}"/>' + star4(cx, y + 56 * k, 9 * k, '#fff'))
    rays = ''.join(f'<path d="M{cx+math.sin(math.radians(a))*18*k:.1f} {y-12*k-math.cos(math.radians(a))*0:.1f}L{cx+math.sin(math.radians(a))*58*k:.1f} {y-12*k-math.cos(math.radians(a))*40*k:.1f}" stroke="#fff" stroke-opacity=".7" stroke-width="{1.4*k:.1f}"/>' for a in (-50, -25, 25, 50))
    rays += f'<path d="M{cx} {y-16*k:.1f}V{y-58*k:.1f}" stroke="#fff" stroke-width="{1.6*k:.1f}"/>' + star4(cx, y - 66 * k, 8 * k, '#fff')
    base = (f'<path d="M{cx-150*k:.1f} {y+138*k:.1f}H{cx+150*k:.1f}" stroke="#fff" stroke-width="{3*k:.1f}"/>'
            f'<path d="M{cx-120*k:.1f} {y+146*k:.1f}H{cx+120*k:.1f}" stroke="#fff" stroke-opacity=".6" stroke-width="{1.2*k:.1f}"/>'
            + ''.join(f'<circle cx="{cx+sx*158*k:.1f}" cy="{y+138*k:.1f}" r="{3.5*k:.1f}" fill="#fff"/>' for sx in (-1, 1))
            + f'<path d="M{cx} {y+124*k:.1f}L{cx+9*k:.1f} {y+138*k:.1f}L{cx} {y+152*k:.1f}L{cx-9*k:.1f} {y+138*k:.1f}Z" fill="url(#gold)"/>')
    return rays + ''.join(plates) + eye + base


def shard_halo(cx, cy, r0, r1, r2, n=40, op=.92, skip=0):
    s = []
    for i in range(n):
        deg = 360 * i / n
        if skip and (deg <= skip or deg >= 360 - skip): continue
        a = math.radians(deg - 90); da = math.radians(180 / n * .78)
        r = r1 if i % 2 == 0 else r2
        p = [(cx + r0 * math.cos(a - da), cy + r0 * math.sin(a - da)), (cx + r * math.cos(a), cy + r * math.sin(a)), (cx + r0 * math.cos(a + da), cy + r0 * math.sin(a + da))]
        s.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in p)}" fill="#fff" fill-opacity="{op}"/>')
    return ''.join(s)


def moebius(cx, cy, w, h, sw, col=INK):
    a, b = w / 2, h / 2
    return (f'<path d="M{cx} {cy}C{cx+a*.35:.1f} {cy-b*1.35:.1f} {cx+a:.1f} {cy-b*1.35:.1f} {cx+a:.1f} {cy}C{cx+a:.1f} {cy+b*1.35:.1f} {cx+a*.35:.1f} {cy+b*1.35:.1f} {cx} {cy}'
            f'C{cx-a*.35:.1f} {cy-b*1.35:.1f} {cx-a:.1f} {cy-b*1.35:.1f} {cx-a:.1f} {cy}C{cx-a:.1f} {cy+b*1.35:.1f} {cx-a*.35:.1f} {cy+b*1.35:.1f} {cx} {cy}Z" fill="none" stroke="{col}" stroke-width="{sw}"/>')


# ---------- plaque ----------
def plaque_body(W=72, H=866, seed=7):
    rnd = random.Random(seed)
    outer = f'M0 0H{W}V{H}H0V712H12V668H0V302H9V258H0Z'
    holes = ['M36 380C25 402 25 440 36 462C47 440 47 402 36 380Z', 'M14 476H58V482H14Z', 'M22 490H50V494H22Z']
    for _ in range(28):
        x, y, r = rnd.uniform(6, 66), rnd.uniform(10, H - 10), rnd.uniform(.6, 1.8)
        if 500 < y < 640 or 96 < y < 350 or 620 < y < 800: continue
        holes.append(f'M{x-r:.1f} {y:.1f}a{r:.1f} {r:.1f} 0 1 0 {2*r:.1f} 0a{r:.1f} {r:.1f} 0 1 0 {-2*r:.1f} 0Z')
    s = [f'<path d="{outer} {" ".join(holes)}" fill="#fff" fill-rule="evenodd"/>']
    for i in range(5):
        for j in range(5):
            if (i in (0, 4) and j in (0, 4)) or rnd.random() < .45:
                s.append(f'<rect x="{14+j*9}" y="{14+i*9}" width="8" height="8" fill="{INK}"/>')
    s.append(f'<rect x="10" y="66" width="52" height="7" fill="{INK}"/><rect x="10" y="78" width="52" height="3" fill="{INK}"/>')
    # snake staff (the bronze serpent): staff, crossbar, serpent coiling over it
    s.append(f'<path d="M36 100V344" stroke="{INK}" stroke-width="3.5"/><path d="M18 108H54" stroke="{INK}" stroke-width="5"/>'
             f'<path d="M36 132C60 144 60 174 36 184C12 194 12 224 36 234C60 244 60 274 36 284C16 292 16 314 34 322" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
             f'<path d="M30 124L44 120L46 130L36 136Z" fill="{INK}"/>'
             f'<path d="M26 344H46L36 358Z" fill="{INK}"/>')
    # Moebius ring with the four-point star
    s.append(moebius(36, 662, 56, 22, 3.5) + star4(36, 662, 14, INK))
    xs = [10, 13, 18, 20, 26, 31, 33, 38, 42, 44, 49, 53, 55, 60]; ws = [2, 4, 1, 4, 3, 1, 4, 2, 1, 3, 2, 1, 4, 2]
    s.append(''.join(f'<rect x="{x}" y="716" width="{w}" height="72" fill="{INK}"/>' for x, w in zip(xs, ws)))
    s.append(''.join(f'<circle cx="{x}" cy="{814}" r="4" fill="{INK}"/>' for x in (22, 36, 50)))
    s.append(f'<path d="M10 838H62" stroke="{INK}" stroke-width="2"/>')
    return ''.join(s)


# ---------- assemble ----------
def field(name, W, cx, cy=440, H=866, k=1.0, wings=True, seed=3):
    defs = (f'<linearGradient id="kl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2A3DF2"/><stop offset="1" stop-color="#1A28C6"/></linearGradient>'
            f'<radialGradient id="glow" cx="{cx}" cy="{cy}" r="{430*k}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#5566FF" stop-opacity=".55"/><stop offset="1" stop-color="#5566FF" stop-opacity="0"/></radialGradient>')
    b = [f'<rect width="{W}" height="{H}" fill="url(#kl)"/>', f'<rect width="{W}" height="{H}" fill="url(#glow)"/>',
         starfield(30, 0, W, H, int(W * .16), seed)]
    if wings:
        bx = max(cx - 430 * k, 56)
        b.append(grid_patch(round(cx + 318 * k), 20, round(140 * k / 21) * 21, 84))
        b.append(f'<path d="M30 {cy}H{W}M{cx} 0V{H}" stroke="#fff" stroke-opacity=".14" stroke-width="1.2"/>')
        b.append(astrolabe(cx, cy, k))
        b.append(floor(cx, 822, k))
        b.append(constellation([(cx + 368 * k, 724), (cx + 418 * k, 692), (cx + 463 * k, 738)]) + star4(cx + 396 * k, 776, 8))
        b.append(f'<circle cx="{bx+54:.0f}" cy="130" r="20" fill="#fff"/><circle cx="{bx+88:.0f}" cy="146" r="7" fill="none" stroke="#fff" stroke-width="1.8"/>')
        b.append(six_wings(cx, cy, k))
        b.append(blade(bx, 70) + pendant(cx + 388 * k, 112, 92, 12))
    else:
        b.append(blade(48, 60, 130, 8) + pendant(W - 12, 220, 70, 9))
    b.append(trim(H))
    b.append(f'<path d="M28 {cy-12}L42 {cy}L28 {cy+12}Z" fill="#fff"/>')
    svg(name, W, H, ''.join(b), defs)


def seal():
    W, H = 600, 720; cx, cy = 300, 440
    b = [f'<circle cx="{cx}" cy="{cy}" r="250" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="0 11"/>',
         f'<circle cx="{cx}" cy="{cy}" r="236" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.4"/>',
         shard_halo(cx, cy, 182, 208, 224, n=48),
         f'<circle cx="{cx}" cy="{cy}" r="182" fill="{KLEIN}"/>',
         f'<circle cx="{cx}" cy="{cy}" r="160" fill="none" stroke="#fff" stroke-width="1.4"/>']
    n = 14
    for i in range(n):
        a = math.radians(360 * i / n - 90)
        b.append(coin(cx + 160 * math.cos(a), cy + 160 * math.sin(a), 13))
    b.append(crest(cx, cy - 258 - 138 * .82, .82))
    svg('cs-seal.svg', W, H, ''.join(b))


def corner():
    body = (f'<path d="M0 0H74L60 14H14V60L0 74Z" fill="#fff"/>'
            f'<path d="M20 20H58L20 58Z" fill="#fff" fill-opacity=".92"/><path d="M20 20L38 38" stroke="{DEEP}" stroke-opacity=".5" stroke-width="1.2"/>'
            f'<path d="M74 0H118M0 74V118" stroke="#fff" stroke-opacity=".75" stroke-width="1.4"/>'
            f'<circle cx="126" cy="0" r="3" fill="#fff"/><circle cx="0" cy="126" r="3" fill="#fff"/>'
            f'<path d="M7 -8L12 0L7 8L2 0Z" transform="translate(-1 0)" fill="url(#gold)"/>')
    tf = {'tl': '', 'tr': 'translate(132 0) scale(-1 1)', 'bl': 'translate(0 132) scale(1 -1)', 'br': 'translate(132 132) scale(-1 -1)'}
    for k, t in tf.items():
        svg(f'cs-corner-{k}.svg', 132, 132, f'<g transform="{t}"><g transform="translate(3 3)">{body}</g></g>')


def medals():
    W, H = 300, 40; cy = 16
    b = [f'<path d="M10 {cy}H{W-10}" stroke="#fff" stroke-opacity=".7" stroke-width="1.2"/>']
    for x in (40, 95, 205, 260): b.append(coin(x, cy, 10))
    b.append(f'<path d="M150 0L164 {cy}L150 32L136 {cy}Z" fill="url(#gold)"/><path d="M150 0V32" stroke="#FFF6D6" stroke-opacity=".7"/>')
    svg('cs-medals.svg', W, H, ''.join(b))


def column():
    b = [starfield(14, 0, 790, 866, 110, 11, (.08, .4)),
         f'<g fill="none" stroke="#fff" stroke-opacity=".06" stroke-width="1.2"><circle cx="10" cy="866" r="230"/><circle cx="10" cy="866" r="290" stroke-dasharray="2 8"/><circle cx="10" cy="866" r="350"/></g>',
         f'<path d="M112 92H752" stroke="#C9D2F2" stroke-opacity=".45" stroke-width="1.2"/>',
         ''.join(f'<path d="M{x} 88V96" stroke="#C9D2F2" stroke-opacity=".45" stroke-width="1.2"/>' for x in range(152, 752, 40)),
         f'<g fill="none" stroke="#C9D2F2" stroke-opacity=".5" stroke-width="1.2"><circle cx="48" cy="48" r="9"/><path d="M48 30V66M30 48H66"/><circle cx="48" cy="826" r="9"/><path d="M48 808V844M30 826H66"/></g>',
         f'<rect x="44" y="168" width="8" height="8" fill="{KLEIN}"/><rect x="44" y="186" width="8" height="8" fill="#fff" fill-opacity=".35"/><rect x="44" y="204" width="8" height="8" fill="#fff" fill-opacity=".35"/>']
    svg('cs-column.svg', 1920, 1080, ''.join(b))


def blueprint():
    b = ['<g fill="none" stroke="#2335E8">']
    for r, op, dash in ((34, .5, ''), (52, .35, '2 5'), (70, .3, ''), (90, .22, '10 5'), (112, .18, '')):
        b.append(f'<circle cx="230" cy="62" r="{r}" stroke-opacity="{op}" stroke-width="1.2"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>')
    for a in range(90, 271, 10):
        c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
        b.append(f'<path d="M{230+70*c:.1f} {62+70*sn:.1f}L{230+(80 if a%30==0 else 75)*c:.1f} {62+(80 if a%30==0 else 75)*sn:.1f}" stroke-opacity=".45"/>')
    b.append('</g>' + star4(230, 62, 12, KLEIN, .5))
    svg('cs-blueprint.svg', 240, 124, ''.join(b))


def eye():
    (_OUT / 'cs-eye.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="44" height="24" viewBox="0 0 44 24"><path d="M2 12C10 2 34 2 42 12C34 22 10 22 2 12Z" fill="none" stroke="{KLEIN}" stroke-width="2"/><path d="M22 4L29 12L22 20L15 12Z" fill="{KLEIN}"/><path d="M22 8L25 12L22 16L19 12Z" fill="#fff"/></svg>', encoding='utf-8')


def wipe():
    W, H = 2800, 866; cx, cy = 1260, 433
    defs = '<linearGradient id="kl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2A3DF2"/><stop offset="1" stop-color="#1A28C6"/></linearGradient>'
    moon = lambda x, y, r: (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff"/><g fill="none" stroke="#fff"><circle cx="{x}" cy="{y}" r="{r+26}" stroke-opacity=".5" stroke-width="1.4"/>'
                            f'<circle cx="{x}" cy="{y}" r="{r+48}" stroke-opacity=".6" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="0 10"/><circle cx="{x}" cy="{y}" r="{r+80}" stroke-opacity=".22"/></g>')
    b = [f'<rect width="{W}" height="{H}" fill="url(#kl)"/>', starfield(0, 0, W, H, 320, 21),
         astrolabe(cx, cy, .9), six_wings(cx, cy, 1.2), shard_halo(cx, cy, 150, 172, 186, n=44),
         f'<circle cx="{cx}" cy="{cy}" r="150" fill="{KLEIN}"/><circle cx="{cx}" cy="{cy}" r="128" fill="#fff"/>',
         moebius(cx, cy, 150, 58, 9, KLEIN), star4(cx, cy, 38, KLEIN),
         crest(cx, 40, .9),
         moon(300, 560, 96), constellation([(130, 160), (230, 110), (330, 190), (420, 140)]),
         moon(2420, 300, 120), constellation([(2180, 640), (2260, 700), (2380, 660), (2470, 740), (2560, 690)]),
         f'<g transform="translate(2140 520) scale(.9)">{wing()}</g><g transform="translate(2700 520) scale(-.9 .9)">{wing()}</g>',
         f'<g transform="translate(620 0)">{plaque_body(seed=5)}</g>', f'<g transform="translate(1860 0)">{plaque_body(seed=9)}</g>',
         f'<g transform="translate(2620 0)">{plaque_body(seed=13)}</g>',
         blade(470, 60) + pendant(540, 20, 90, 12) + blade(900, 60) + pendant(1010, 20, 90, 12) + blade(1560, 130, 130, 8) + pendant(1700, 50)
         + blade(2060, 90) + pendant(2240, 30, 96, 12) + blade(2560, 40, 120, 8),
         f'<rect width="40" height="{H}" fill="{INK}"/><rect x="52" width="4" height="{H}" fill="#fff"/>',
         f'<rect x="{W-40}" width="40" height="{H}" fill="{INK}"/><rect x="{W-56}" width="4" height="{H}" fill="#fff"/>']
    svg('cs-wipe.svg', W, H, ''.join(b), defs)


def write_assets(directory):
    """Write every Cornerstone ornament SVG into the shot's asset directory (deterministic)."""
    global _OUT
    _OUT = Path(directory); _OUT.mkdir(parents=True, exist_ok=True)
    field('cs-field.svg', 1056, 482)
    field('cs-field-ov.svg', 816, 362, k=.82, seed=4)
    field('cs-field-cal.svg', 156, 78, wings=False, seed=5)
    svg('cs-plaque.svg', 72, 866, plaque_body())
    seal(); corner(); medals(); column(); blueprint(); eye(); wipe()
    svg('cs-crest.svg', 340, 230, crest(170, 74, 1.0))
    return sorted(p.name for p in _OUT.glob('cs-*.svg'))


if __name__ == '__main__':
    import sys
    print(write_assets(sys.argv[1] if len(sys.argv) > 1 else '.'))
