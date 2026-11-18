"""Build the 'Map to Our Clinic' graphic: an OpenStreetMap vector basemap in the site palette, framed exactly
like the original hand-annotated map (1253x810), with the original directions redrawn on top at the same
positions. usage: python3 -I build_map.py <area.json> <fit.json> <wordmark.png> <orig.jpg> <out_dir> <final|compare>"""
import sys, json, math, base64

area, fitp, wordmark, orig, out, mode = sys.argv[1:7]
W, H = 1253, 810
fit = json.load(open(fitp))
E = json.load(open(area))['elements']
ways = [e for e in E if e['type'] == 'way' and e.get('geometry')]

def P(lat, lon):
    s = 256 * 2 ** fit['z']
    x = (lon + 180) / 360 * s
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * s
    return fit['s'] * x + fit['tx'], fit['s'] * y + fit['ty']

def pts(w): return [P(g['lat'], g['lon']) for g in w['geometry']]
def near(ps, m=80): return any(-m <= x <= W + m and -m <= y <= H + m for x, y in ps)
def d(ps, close=False): return 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in ps) + ('Z' if close else '')

# ---------- base areas ----------
AREA = [  # (test, fill, stroke)
    (lambda t: t.get('amenity') == 'hospital', '#FBEEF0', None),
    (lambda t: t.get('amenity') in ('school', 'college'), '#EEF2F7', None),
    (lambda t: t.get('natural') in ('wood', 'scrub') or t.get('landuse') == 'forest', '#E3F1E8', None),
    (lambda t: t.get('landuse') in ('grass', 'recreation_ground') or t.get('natural') == 'grassland' or t.get('leisure') == 'park', '#EDF5F0', None),
    (lambda t: t.get('leisure') == 'pitch', '#E6F3EB', '#D6EADE'),
    (lambda t: t.get('amenity') == 'parking', '#E9EEF3', None),
    (lambda t: t.get('leisure') == 'swimming_pool', '#CDE5F4', None),
]
areas = {i: [] for i in range(len(AREA))}
for w in ways:
    t = w.get('tags', {})
    if 'building' in t or 'highway' in t: continue
    p = pts(w)
    if len(p) < 3 or not near(p): continue
    for i, (test, *_r) in enumerate(AREA):
        if test(t): areas[i].append(d(p, True)); break

buildings = [d(pts(w), True) for w in ways if 'building' in w.get('tags', {}) and near(pts(w))]

# ---------- roads ----------
CLS = {  # highway: (fill width, casing extra, casing colour)
    'secondary': (14, 3, '#C5D2DF'), 'primary': (14, 3, '#C5D2DF'), 'tertiary': (11, 2.4, '#CFDAE5'),
    'residential': (9, 2.2, '#D3DDE7'), 'unclassified': (9, 2.2, '#D3DDE7'), 'living_street': (8, 2, '#D3DDE7'),
    'service': (5, 1.8, '#D6DFE8'),
}
roads = {k: [] for k in CLS}; paths = []
for w in ways:
    t = w.get('tags', {}); h = t.get('highway')
    p = pts(w)
    if not near(p): continue
    if h in CLS:
        wdt = CLS[h][0] * (0.6 if t.get('service') in ('parking_aisle', 'driveway') else 1)
        roads[h].append((d(p), wdt))
    elif h in ('footway', 'path', 'pedestrian', 'steps', 'cycleway', 'track'):
        paths.append(d(p))
order = ['service', 'living_street', 'unclassified', 'residential', 'tertiary', 'secondary', 'primary']

# ---------- street labels: angle taken from the real road under each label ----------
def named(n): return [pts(w) for w in ways if 'highway' in w.get('tags', {}) and (w['tags'].get('name') == n if n else w['tags']['highway'] in CLS)]
def snap(name, x, y):
    best = None
    for p in named(name):
        for (ax, ay), (bx, by) in zip(p, p[1:]):
            vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy or 1
            u = max(0, min(1, ((x - ax) * vx + (y - ay) * vy) / L2))
            qx, qy = ax + u * vx, ay + u * vy; dist = math.hypot(x - qx, y - qy)
            if best is None or dist < best[0]:
                a = math.degrees(math.atan2(vy, vx))
                if a > 90: a -= 180
                if a < -90: a += 180
                best = (dist, qx, qy, a)
    return best
LABELS = [('Tipahi St', 'Tipahi Street', 45, 30), ('Kawai St', 'Kawai Street', 303, 34),
          ('Franklyn St', 'Franklyn Street', 315, 103), ('Franklyn St', 'Franklyn Street', 520, 262),
          ('Waimea Rd', 'Waimea Road', 345, 355), ('Waimea Rd', 'Waimea Road', 133, 668), ('Waimea Rd', 'Waimea Road', 597, 14),
          ('Motueka St', 'Motueka Street', 225, 700), ('Braemar Pl', 'Braemar Place', 752, 560),
          ('Corgarff Pl', 'Braemar Place', 790, 725), ('Grampian Oaks Ln', 'Grampian Oaks Lane', 460, 787),
          ('Ngatitama St', None, 1068, 90), ('Hampden St', 'Hampden Street East', 1195, 70)]
street_labels = []
for text, name, x, y in LABELS:
    s = snap(name, x, y)
    if s: street_labels.append(f'<text class="st" transform="translate({s[1]:.1f} {min(s[2], H - 12):.1f}) rotate({s[3]:.1f})">{text}</text>')
    else: print('no road for', name, file=sys.stderr)

# ---------- POIs (positions as on the original) ----------
def pin(x, y, c): return (f'<path d="M{x} {y+13}c-6-7-10-11-10-16a10 10 0 1 1 20 0c0 5-4 9-10 16z" fill="{c}" stroke="#fff" stroke-width="1.5"/>'
                          f'<circle cx="{x}" cy="{y-3}" r="3.6" fill="#fff"/>')
pois = f'''
  <circle cx="168" cy="229" r="13" fill="#D9534F" stroke="#fff" stroke-width="2"/><text class="ico" x="168" y="229">H</text>
  <text class="poi red" x="191" y="236">Nelson Hospital</text>
  {pin(305, 290, '#D9534F')}
  <text class="poi red" x="283" y="289" text-anchor="end">Nelson Hospital</text>
  <text class="poi red" x="283" y="310" text-anchor="end">Emergency Room</text>
  {pin(437, 488, '#7A8796')}
  <text class="poi red" x="457" y="482">Nelson Hospital</text>
  <text class="poi red" x="457" y="503">Ophthalmology</text>
  <circle cx="885" cy="122" r="13" fill="#7A8796" stroke="#fff" stroke-width="2"/>
  <path d="M877 120l8-4 8 4-8 4zM880.5 122v4c2.5 2 6.5 2 9 0v-4" fill="#fff" stroke="#fff" stroke-width=".8" stroke-linejoin="round"/>
  <text class="poi grey" x="858" y="129" text-anchor="end">Nelson College</text>
  <circle cx="107" cy="53" r="13" fill="#1B6FB3" stroke="#fff" stroke-width="2"/><text class="ico" x="107" y="53">P</text>
  <circle cx="43" cy="243" r="13" fill="#1B6FB3" stroke="#fff" stroke-width="2"/><text class="ico" x="43" y="243">P</text>
  <rect x="371" y="148" width="18" height="18" rx="5" fill="#7A8796" stroke="#fff" stroke-width="1.5"/><path d="M375 152h10v7h-10zM376 161h2M382 161h2" stroke="#fff" stroke-width="1.6" fill="none"/>
  <rect x="391" y="264" width="18" height="18" rx="5" fill="#7A8796" stroke="#fff" stroke-width="1.5"/><path d="M395 268h10v7h-10zM396 277h2M402 277h2" stroke="#fff" stroke-width="1.6" fill="none"/>'''

# ---------- the original directions, redrawn at the original positions ----------
def head(x1, y1, x2, y2, L, hw):
    a = math.atan2(y2 - y1, x2 - x1); bx, by = x2 - L * math.cos(a), y2 - L * math.sin(a)
    nx, ny = -math.sin(a) * hw, math.cos(a) * hw
    return f'{x2:.1f},{y2:.1f} {bx+nx:.1f},{by+ny:.1f} {bx-nx:.1f},{by-ny:.1f}', (bx, by)
h1, b1 = head(548, 232, 642, 302, 26, 11.5)
route = [(460, 201), (568, 284), (650, 340), (742, 404), (758, 418), (784, 447), (801, 466), (808, 471), (824, 475), (840, 484), (912, 538)]
wm = base64.b64encode(open(wordmark, 'rb').read()).decode()
cmp = mode in ('compare', 'ann')
panel_fill = 'none' if cmp else 'rgba(255,255,255,.88)'
box_fill = 'none' if cmp else '#fff'
directions = f'''
<g id="directions">
  <polygon points="1022,810 1058,652 1253,604 1253,810" fill="{'none' if cmp else '#CDF8DD'}"/>
  <g transform="translate(893.5 418) rotate(36.75)"><rect x="-93.5" y="-64" width="187" height="128" fill="{'none' if cmp else '#D2FAE2'}"/></g>
  <g transform="translate(554 125) rotate(35.6)">
    <rect x="-12" y="-28" width="206" height="136" rx="8" fill="{panel_fill}"/>
    <text class="dir" y="0">Turn up the steep</text><text class="dir" y="24">hill towards the</text><text class="dir" y="48">Grampians, veer</text>
    <text class="dir" y="72">left and follow the</text><text class="dir" y="96">signs</text>
  </g>
  <line x1="548" y1="232" x2="{b1[0]:.1f}" y2="{b1[1]:.1f}" stroke="#000" stroke-width="5"/><polygon points="{h1}" fill="#000"/>
  <polyline points="{' '.join(f'{x},{y}' for x, y in route)}" fill="none" stroke="#000" stroke-width="6" stroke-dasharray="20 13" stroke-linejoin="round"/>
  <text class="veer" x="776" y="413">Veer Left</text>
  <line x1="818" y1="416" x2="818" y2="447" stroke="#000" stroke-width="6"/><polygon points="809,446 827,446 818,462" fill="#000"/>
  <circle cx="925" cy="547" r="15" fill="#000"/>
  <g transform="translate(895 612.5) rotate(36.7)">
    <rect x="-83" y="-45" width="166" height="90" fill="{box_fill}" stroke="#000" stroke-width="5"/>
    <image href="data:image/png;base64,{wm}" x="-78.5" y="-14.5" width="151" height="{151/4.695:.1f}"/>
  </g>
  <g transform="translate(893.5 418) rotate(36.75)">
    <text class="dir sm" x="-71.5" y="-44">BOY&#8217;S COLLEGE</text><text class="dir sm" x="-71.5" y="-19.5">PLAYING FIELDS</text>
  </g>
  <text class="dir gr" transform="translate(1109 796) rotate(-49)">GRAMPIANS&#160; RESERVE</text>
</g>'''

style = '''
  .st { font: 600 16px Urbanist, sans-serif; fill: #5B6B7D; text-anchor: middle; dominant-baseline: central; letter-spacing: .01em;
        paint-order: stroke; stroke: #fff; stroke-width: 3.5px; stroke-linejoin: round; }
  .poi { font: 600 19px Urbanist, sans-serif; paint-order: stroke; stroke: #fff; stroke-width: 3.5px; stroke-linejoin: round; letter-spacing: -.005em; }
  .poi.red { fill: #B8434C; } .poi.grey { fill: #5B6B7D; }
  .ico { font: 700 15px Urbanist, sans-serif; fill: #fff; text-anchor: middle; dominant-baseline: central; }
  .dir { font: 400 21.5px 'Didact Gothic', sans-serif; fill: #000; letter-spacing: .045em; } .dir.sm { font-size: 18.5px; letter-spacing: .03em; } .dir.gr { font-size: 18.5px; letter-spacing: 0; }
  .veer { font: 700 17.5px Jost, sans-serif; fill: #000; }
  .attr { font: 500 11px Urbanist, sans-serif; fill: #6B7A8C; }'''

base = []
if mode == 'ann':
    base.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
elif cmp:
    base.append(f'<image href="data:image/jpeg;base64,{base64.b64encode(open(orig, "rb").read()).decode()}" width="{W}" height="{H}"/>')
else:
    base.append(f'<rect width="{W}" height="{H}" fill="#F3F6F9"/>')
    for i, (_t, fill, stroke) in enumerate(AREA):
        if areas[i]: base.append(f'<path d="{"".join(areas[i])}" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="1"' if stroke else '') + '/>')
    base.append(f'<path d="{"".join(buildings)}" fill="#E2E9F0" stroke="#D4DDE7" stroke-width=".7"/>')
    base.append(f'<path d="{"".join(paths)}" fill="none" stroke="#DCE4EC" stroke-width="1.6" stroke-linecap="round"/>')
    for k in order:
        for dd, wdt in roads[k]:
            base.append(f'<path d="{dd}" fill="none" stroke="{CLS[k][2]}" stroke-width="{wdt + 2 * CLS[k][1]:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    for k in order:
        for dd, wdt in roads[k]:
            base.append(f'<path d="{dd}" fill="none" stroke="#fff" stroke-width="{wdt:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    base += street_labels
    base.append(pois)

overlay_filter = '' if mode == 'ann' else '<filter id="red"><feColorMatrix values="0 0 0 0 1  0 0 0 0 0  0 0 0 0 0  0 0 0 .75 0"/></filter>' if cmp else ''
attribution = '' if cmp else f'<rect x="8" y="{H-25}" width="172" height="18" rx="4" fill="#fff" fill-opacity=".85"/><text class="attr" x="15" y="{H-12}">© OpenStreetMap contributors</text>'
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" id="map">
<defs><style>{style}</style>{overlay_filter}</defs>
{''.join(base)}
<g{' filter="url(#red)"' if mode == 'compare' else ''}>{directions}</g>
{attribution}
</svg>'''
html = f'''<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Didact+Gothic&family=Jost:wght@700&family=Urbanist:wght@500;600;700&display=block" rel="stylesheet">
<style>html,body{{margin:0;background:#fff}} svg{{display:block}}</style></head><body>{svg}</body></html>'''
open(f'{out}/map-{mode}.html', 'w').write(html)
open(f'{out}/map-{mode}.svg', 'w').write(svg)
print('ok', mode, 'buildings', len(buildings), 'labels', len(street_labels))
