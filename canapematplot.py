


def _format_valise_counts_console(
    sizes, counts, total, order=("gauche", "bas", "droite")
):
    """
    Affichage console *valise* : agrège les quantités par dimension et trie selon
    l'ordre des côtés spécifié (défaut: gauche, bas, droite).
    Exemple : "4x86 / 3x83 / 3x81 - total 10".

    Paramètres :
      sizes  : dict {"bas":int,"gauche":int,"droite":int (optionnel)}
      counts : dict même clés -> quantités posées par côté.
      total  : nombre total de coussins posés.
      order  : ordre de priorité des côtés pour le tri (tuple/list).
    """
    from collections import defaultdict

    # Dans certains cas, best["counts"] peut ne pas exister ; counts peut être None.
    if counts is None:
        counts = {}

    # 1) Agrégation par dimension : somme des coussins pour chaque taille.
    agg = defaultdict(int)
    for side, size in sizes.items():
        c = counts.get(side, 0)
        if c > 0:
            agg[size] += c

    # Si aucun coussin, on affiche juste le total.
    if not agg:
        return f"- total {total}"

    # 2) Déterminer pour chaque dimension le premier côté qui l'utilise,
    #    selon l'ordre de priorité indiqué. Ce côté servira à trier les tailles.
    side_index = {side: i for i, side in enumerate(order)}
    first_side_for_size = {}
    for side in order:
        size = sizes.get(side)
        if size is None:
            continue
        if counts.get(side, 0) > 0 and size not in first_side_for_size:
            first_side_for_size[size] = side_index.get(side, len(order))

    # 3) Tri des couples (taille, quantité) :
    #    d'abord par index de côté prioritaire, puis par taille décroissante.
    def sort_key(item):
        size, _ = item
        return (first_side_for_size.get(size, len(order)), -size)

    parts = [
        f"{n}x{sz}"
        for sz, n in sorted(agg.items(), key=sort_key)
    ]
    return " / ".join(parts) + f" - total {total}"

# -------------------------------------------------------------------------
# Comptage pondéré des dossiers
# -------------------------------------------------------------------------

def _compute_dossiers_count(polys):
    """
    Calcule un nombre pondéré de dossiers en fonction de leur longueur.
    Chaque dossier de longueur > 110 cm compte pour 1, et chaque dossier
    de longueur <= 110 cm compte pour 0,5.

    Parameters:
        polys (dict): dictionnaire contenant notamment la clé 'dossiers'
                      avec une liste de polygones représentant les dossiers.
    Returns:
        float: le nombre total pondéré de dossiers.
    """
    total = 0.0
    for p in polys.get("dossiers", []):
        # p est une liste de coordonnées (x,y)
        xs = [pt[0] for pt in p]
        ys = [pt[1] for pt in p]
        length = max(max(xs) - min(xs), max(ys) - min(ys))
        if length <= 110:
            total += 0.5
        else:
            total += 1.0
    return total


# -*- coding: utf-8 -*-
# canape_complet_v6_palette_legende_U.py
# Base validée + ajouts :
#   - Choix des couleurs par noms FR (gris, beige, gris foncé/foncée, taupe, crème, etc.) ou #hex
#   - Préréglage demandé : accoudoirs=gris ; dossiers=gris (plus clair) ;
#                          assises=gris très clair (presque blanc) ; coussins=taupe
#   - Dossiers automatiquement un ton plus clair que accoudoirs si non précisé
#   - Légende "U" déplacée en haut-centré (hors canapé) ; autres : haut-droite
#   - Légende affiche la couleur choisie ("Dossier (gris clair)", etc.)
#   - Correctifs nommage 'coussins_count' -> 'cushions_count'

import math
import unicodedata

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import types

# =========================
# Adapteur "turtle" -> Matplotlib
# =========================

_current_screen = None

class _Screen:
    def __init__(self):
        global _current_screen
        self.fig, self.ax = plt.subplots()
        self.ax.set_aspect('equal', adjustable='box')
        self.width = None
        self.height = None
        _current_screen = self

    def setup(self, width, height):
        """Approxime turtle.Screen().setup(width,height)."""
        self.width, self.height = float(width), float(height)
        # conversion très simple pixels -> pouces
        try:
            self.fig.set_size_inches(self.width / 100.0, self.height / 100.0)
        except Exception:
            pass
        # on centre la scène sur (0,0), comme turtle
        half_w = self.width / 2.0
        half_h = self.height / 2.0
        self.ax.set_xlim(-half_w, half_w)
        self.ax.set_ylim(-half_h, half_h)
        self.ax.axis('off')

    def title(self, text):
        try:
            self.fig.suptitle(text)
        except Exception:
            pass

    def tracer(self, flag):
        # Utilisé uniquement pour accélérer le rendu dans turtle.
        # Avec Matplotlib on ne s'en sert pas : méthode factice pour compatibilité.
        pass


class _Turtle:
    def __init__(self, visible=True):
        global _current_screen
        if _current_screen is None:
            _current_screen = _Screen()
        self.screen = _current_screen
        self.ax = self.screen.ax
        self.x = 0.0
        self.y = 0.0
        # 0° vers la droite, positif = anti-horaire (comme turtle)
        self.heading = 0.0
        self.pen_down = True
        self.linewidth = 1.0
        self.pencolor_value = "black"
        self.fillcolor_value = "black"
        self.is_filling = False
        self.fill_path = []
        # "visible" ignoré : on ne dessine jamais la tortue elle-même.

    # --- Gestion du stylo ---
    def up(self):
        self.pen_down = False

    def down(self):
        self.pen_down = True

    # alias turtle
    def penup(self):
        self.up()

    def pendown(self):
        self.down()

    def pensize(self, w):
        self.linewidth = float(w)

    def pencolor(self, c):
        self.pencolor_value = c

    def fillcolor(self, c):
        self.fillcolor_value = c

    # --- Orientation / déplacement ---
    def setheading(self, angle):
        self.heading = float(angle)

    def goto(self, x, y):
        x = float(x)
        y = float(y)
        if self.pen_down:
            self.ax.plot([self.x, x], [self.y, y],
                         linewidth=self.linewidth,
                         color=self.pencolor_value)
        if self.is_filling:
            if not self.fill_path:
                self.fill_path.append((self.x, self.y))
            self.fill_path.append((x, y))
        self.x, self.y = x, y

    def forward(self, dist):
        r = math.radians(self.heading)
        nx = self.x + dist * math.cos(r)
        ny = self.y + dist * math.sin(r)
        self.goto(nx, ny)

    def left(self, angle):
        self.heading += float(angle)

    def right(self, angle):
        self.heading -= float(angle)

    # --- Remplissage ---
    def begin_fill(self):
        self.is_filling = True
        self.fill_path = [(self.x, self.y)]

    def end_fill(self):
        if self.is_filling and len(self.fill_path) >= 3:
            poly = Polygon(self.fill_path, closed=True,
                           facecolor=self.fillcolor_value,
                           edgecolor=self.pencolor_value,
                           linewidth=self.linewidth)
            self.ax.add_patch(poly)
        self.is_filling = False
        self.fill_path = []

    # --- Arc de cercle (utilisé pour les coins arrondis) ---
    def circle(self, radius, extent=None, steps=None):
        if extent is None:
            extent = 360.0
        extent = float(extent)
        # nombre de segments pour approcher l'arc
        if steps is None:
            steps = max(4, int(abs(extent) / 5.0))
        steps = max(1, int(steps))

        start_heading = self.heading
        r = float(radius)
        # centre du cercle : à gauche de la tortue
        h_rad = math.radians(start_heading)
        cx = self.x - r * math.sin(h_rad)
        cy = self.y + r * math.cos(h_rad)
        phi0 = start_heading - 90.0  # angle du rayon au point de départ

        xs = []
        ys = []
        for i in range(steps + 1):
            phi = phi0 + extent * (i / float(steps))
            pr = math.radians(phi)
            x = cx + r * math.cos(pr)
            y = cy + r * math.sin(pr)
            xs.append(x)
            ys.append(y)

        # tracer l'arc
        for x, y in zip(xs[1:], ys[1:]):
            self.goto(x, y)

        # nouvelle orientation de la tortue à la fin de l'arc
        self.heading = start_heading + extent

    # --- Texte ---
    def write(self, text, align="left", font=None):
        ha = {"left": "left", "center": "center", "right": "right"}.get(align, "left")
        kwargs = {"ha": ha, "va": "center"}
        if font is not None:
            # tuple de type ("Arial", 12, "bold")
            if len(font) > 0:
                kwargs["fontfamily"] = font[0]
            if len(font) > 1:
                kwargs["fontsize"] = font[1]
            if len(font) > 2:
                style = font[2]
                if style in ("bold", "normal"):
                    kwargs["fontweight"] = style
                else:
                    kwargs["fontstyle"] = style
        self.ax.text(self.x, self.y, str(text), **kwargs)

    # --- Autres méthodes ---
    def speed(self, _):
        # ignoré : sans effet en Matplotlib
        pass

    def hideturtle(self):
        # la tortue n'est jamais affichée
        pass


def _done():
    """Équivalent de turtle.done() : affiche la figure Matplotlib."""
    global _current_screen
    if _current_screen is not None:
        _current_screen.ax.set_aspect("equal", adjustable="box")
        plt.show()
    _current_screen = None


turtle = types.SimpleNamespace(Screen=_Screen, Turtle=_Turtle, done=_done)

# =========================
# Réglages / constantes
# =========================
WIN_W, WIN_H       = 900, 700
PAD_PX             = 60
ZOOM               = 0.85
LINE_WIDTH         = 2

# ========= PALETTE / THÈME =========
# Couleurs par défaut, selon la demande :
# - accoudoirs = gris (moyen)
# - dossiers = gris (un ton plus clair)
# - assises/banquettes = gris très clair (presque blanc)
# - coussins = taupe
# NB : Ces valeurs seront éventuellement écrasées à chaque render_* via _resolve_and_apply_colors()
COLOR_ASSISE       = "#f6f6f6"  # gris très clair / presque blanc
COLOR_ACC          = "#8f8f8f"  # gris
COLOR_DOSSIER      = "#b8b8b8"  # gris plus clair que accoudoirs
COLOR_CUSHION      = "#8B7E74"  # taupe
COLOR_CONTOUR      = "black"

# (Conservés mais non utilisés car quadrillage/repères supprimés)
GRID_MINOR_STEP    = 10
GRID_MAJOR_STEP    = 50
COLOR_GRID_MINOR   = "#f0f0f0"
COLOR_GRID_MAJOR   = "#dcdcdc"
AXIS_LABEL_STEP    = 50
AXIS_LABEL_MAX     = 800

DEPTH_STD          = 70
ACCOUDOIR_THICK    = 15
DOSSIER_THICK      = 10
CUSHION_DEPTH      = 15

# *** Seuil strict de scission ***
MAX_BANQUETTE      = 250
SPLIT_THRESHOLD    = 250  # scission dès que longueur > 250 (aucune tolérance)

# --- Coins arrondis coussins ---
CUSHION_ROUND_R_CM = 3.0  # rayon ~3 cm, léger

# --- Traversins (bolsters) ---
TRAVERSIN_LEN   = 70     # longueur selon la profondeur
TRAVERSIN_THK   = 30     # retrait sur la ligne de coussins
COLOR_TRAVERSIN = "#e0d9c7"

def _segment_x_limits(pts, a_key, b_key):
    """
    Retourne (x_min, x_max, y) pour le segment horizontal défini par deux
    points partageant le même y (ex.: By–By2 ou By3–By4).
    """
    ax, ay = pts[a_key]
    bx, by = pts[b_key]
    # Par sécurité on ne s'appuie pas sur un éventuel By_ / By4_ (méridienne)
    # → l'appelant fournit explicitement By/By2/By3/By4.
    x0 = min(ax, bx)
    x1 = max(ax, bx)
    y  = ay  # ay == by par construction
    return x0, x1, y

def _clamp_to_segment(x0, length, seg_min, seg_max, align="start"):
    """
    Calcule [X0, X1] pour une brique de 'length' posée DANS [seg_min, seg_max].
    - align='start'  → coller au début du segment (gauche)
    - align='end'    → coller à la fin   du segment (droite)
    """
    length = max(0.0, float(length))
    if align == "start":
        X0 = max(seg_min, min(x0, seg_max))
        X1 = min(seg_max, X0 + length)
        # Si la longueur excède le segment, on se borne au segment complet
        if X1 - X0 < length:
            X0 = seg_min
            X1 = min(seg_max, seg_min + length)
    else:  # align == "end"
        X1 = min(seg_max, max(x0, seg_min))
        X0 = max(seg_min, X1 - length)
        if X1 - X0 < length:
            X1 = seg_max
            X0 = max(seg_min, seg_max - length)
    return X0, X1

# --- Polices / légende / titres (lisibilité accrue) ---
# Réduction légère des tailles de police pour une meilleure lisibilité
FONT_LABEL      = ("Arial", 10, "bold")   # libellés banquettes/dossiers/accoudoirs
FONT_CUSHION    = ("Arial", 9,  "bold")   # tailles des coussins + "70x30"
FONT_DIM        = ("Arial", 10, "bold")   # flèches d’encombrement
FONT_LEGEND     = ("Arial", 10, "normal") # texte de légende
FONT_TITLE      = ("Arial", 12, "bold")   # titre "Canapé en U …"
LEGEND_BOX_PX   = 14
LEGEND_GAP_PX   = 6
TITLE_MARGIN_PX = 28  # marge sous le bord haut du dessin

# --- Sécurité d'affichage pour la légende ---
LEGEND_SAFE_PX = 16   # distance minimale entre la légende et le schéma (px)
LEGEND_EDGE_PX = 10   # marge minimale par rapport aux bords de fenêtre (px)

# =============================================================================
# ================     OUTILS PALETTE / COULEURS (NOUVEAU)     ================
# =============================================================================

# Palette de base (nuanciers simples)
_BASE_COLORS = {
    "gris":   "#9e9e9e",
    "beige":  "#d8c4a8",
    "taupe":  "#8B7E74",
    "crème":  "#f4f1e9",
    "creme":  "#f4f1e9",
    "blanc":  "#ffffff",
    "noir":   "#111111",
    "sable":  "#e6d8b8",
    "anthracite": "#4b4b4b",
}

# Helpers accents/normalisation
def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = _strip_accents(s)
    return ' '.join(s.split())

def _clamp(x, lo=0, hi=255):
    return int(max(lo, min(hi, round(x))))

def _hex_to_rgb(h):
    h = h.strip()
    if h.startswith("#"):
        h = h[1:]
    if len(h) == 3:
        h = ''.join([c*2 for c in h])
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def _lighten(hexcol, factor):
    """factor in [0,1] vers blanc; 0 = identique; 1 = blanc complet."""
    r,g,b = _hex_to_rgb(hexcol)
    r = _clamp(r + (255-r)*factor)
    g = _clamp(g + (255-g)*factor)
    b = _clamp(b + (255-b)*factor)
    return _rgb_to_hex((r,g,b))

def _darken(hexcol, factor):
    """factor in [0,1] vers noir; 0 = identique; 1 = noir complet."""
    r,g,b = _hex_to_rgb(hexcol)
    r = _clamp(r*(1-factor))
    g = _clamp(g*(1-factor))
    b = _clamp(b*(1-factor))
    return _rgb_to_hex((r,g,b))

def _apply_shade(hexcol, tokens):
    """
    tokens: contient éventuellement 'clair', 'tres clair', 'fonce', 'tres fonce', 'presque blanc'
    """
    t = ' '.join(tokens)
    t_norm = _norm(t)
    if "presque blanc" in t_norm:
        return _lighten(hexcol, 0.75)
    if "tres clair" in t_norm:
        return _lighten(hexcol, 0.40)
    if "clair" in t_norm:
        return _lighten(hexcol, 0.22)
    if "tres fonce" in t_norm:
        return _darken(hexcol, 0.40)
    if "fonce" in t_norm or "foncee" in t_norm:
        return _darken(hexcol, 0.22)
    return hexcol

def _pretty_shade(tokens):
    t = _norm(' '.join(tokens))
    t = t.replace("tres", "très")
    t = t.replace("fonce", "foncé")
    return t

def _parse_color_value(val):
    """
    Convertit un nom FR (évent. qualifié) ou un #hex en (#hex, nom jolis mots ou None)
    Ex : "gris foncé" -> (#..., "gris foncé")
         "#c0ffee"    -> ("#c0ffee", None)
    """
    if val is None:
        return None, None
    s_raw = str(val).strip()
    s = _norm(s_raw)

    # cas hex
    if s.startswith("#") or all(c in "0123456789abcdef" for c in s.replace("#","")) and len(s.replace("#","")) in (3,6):
        try:
            _ = _hex_to_rgb(s)
            if not s.startswith("#"): s = "#" + s
            return s, None
        except Exception:
            pass

    # cherche base connue
    tokens = s.split()
    if not tokens:
        return None, None

    # base candidates (un ou deux mots, ex "gris", "blanc", "beige", "taupe")
    base = tokens[0]
    base_hex = _BASE_COLORS.get(base)
    if base_hex is None and len(tokens)>=2:
        # ex: "gris clair" = base "gris" + shade "clair"
        base_hex = _BASE_COLORS.get(tokens[0])
    if base_hex is None:
        # fallback : gris
        base_hex = _BASE_COLORS["gris"]; base = "gris"

    shade = tokens[1:] if len(tokens)>1 else []
    hexcol = _apply_shade(base_hex, shade)
    pretty = base
    if shade:
        pretty += " " + _pretty_shade(shade)
    return hexcol, pretty

def _parse_couleurs_argument(couleurs):
    """
    Accepte dict, ou string "clé:val; clé:val".
    Normalise les clés en {'accoudoirs','dossiers','assise','coussins'}
    """
    if couleurs is None:
        return {}

    if isinstance(couleurs, dict):
        raw = { _norm(k): str(v) for k,v in couleurs.items() }
    else:
        raw = {}
        for part in str(couleurs).split(";"):
            if ":" in part:
                k,v = part.split(":",1)
                raw[_norm(k)] = v.strip()

    keymap = {
        "accoudoir":"accoudoirs", "accoudoirs":"accoudoirs",
        "dossier":"dossiers", "dossiers":"dossiers",
        "assise":"assise", "assises":"assise", "banquette":"assise", "banquettes":"assise",
        "coussin":"coussins", "coussins":"coussins"
    }
    res={}
    for k,v in raw.items():
        kn = keymap.get(k, k)
        if kn in ("accoudoirs","dossiers","assise","coussins"):
            res[kn] = v
    return res

def _resolve_and_apply_colors(couleurs):
    """
    Résout la palette utilisateur puis applique aux variables globales:
      COLOR_ASSISE, COLOR_ACC, COLOR_DOSSIER, COLOR_CUSHION
    Retourne une liste d'items pour la légende: [(libellé, hex, nom)]
    Règle : si dossiers non spécifié mais accoudoirs oui => dossiers = accoudoirs éclaircis.
    """
    global COLOR_ASSISE, COLOR_ACC, COLOR_DOSSIER, COLOR_CUSHION

    # base par défaut (demande client)
    default = {
        "accoudoirs": "gris",
        "dossiers":   None,  # sera éclairci à partir des accoudoirs si None
        "assise":     "gris très clair presque blanc",
        "coussins":   "taupe",
    }
    user = _parse_couleurs_argument(couleurs)
    spec = {**default, **user}

    # accoudoirs
    acc_hex, acc_name = _parse_color_value(spec["accoudoirs"])
    # dossiers
    if spec["dossiers"] is None:
        # auto : un ton plus clair que accoudoirs
        dos_hex = _lighten(acc_hex, 0.20)
        dos_name = (acc_name+" clair") if acc_name else "gris clair"
    else:
        dos_hex, dos_name = _parse_color_value(spec["dossiers"])
    # assise
    ass_hex, ass_name = _parse_color_value(spec["assise"])
    # coussins
    cush_hex, cush_name = _parse_color_value(spec["coussins"])

    # applique globals
    COLOR_ACC     = acc_hex
    COLOR_DOSSIER = dos_hex
    COLOR_ASSISE  = ass_hex
    COLOR_CUSHION = cush_hex

    # Items de légende (texte + nom de couleur si dispo)
    items = [
        ("Dossier",   COLOR_DOSSIER, dos_name),
        ("Accoudoir", COLOR_ACC,     acc_name),
        ("Coussins",  COLOR_CUSHION, cush_name),
        ("Assise",    COLOR_ASSISE,  ass_name),
    ]
    return items

# =========================
# Transform cm → px (isométrique & centré)
# =========================
class WorldToScreen:
    def __init__(self, tx_cm, ty_cm, win_w=WIN_W, win_h=WIN_H, pad_px=PAD_PX, zoom=ZOOM):
        sx = (win_w - 2*pad_px) / float(tx_cm or 1)
        sy = (win_h - 2*pad_px) / float(ty_cm or 1)
        self.scale = min(sx, sy) * zoom
        used_w = tx_cm * self.scale
        used_h = ty_cm * self.scale
        self.left_px   = -used_w / 2.0
        self.bottom_px = -used_h / 2.0
    def pt(self, x_cm, y_cm):
        return (self.left_px + x_cm*self.scale, self.bottom_px + y_cm*self.scale)

# =========================
# Outils dessin
# =========================
def pen_up_to(t, x, y):
    t.up(); t.goto(x, y)

def _is_axis_aligned_rect(pts):
    """Détecte un rectangle axis‑aligné fermé (le dernier point répète le premier)."""
    if not pts or len(pts) < 4:
        return False
    body = pts[:-1] if pts[0] == pts[-1] else pts
    if len(body) != 4:
        return False
    xs = {round(x, 6) for x, _ in body}
    ys = {round(y, 6) for _, y in body}
    return len(xs) == 2 and len(ys) == 2

def draw_rounded_rect_cm(t, tr, x0, y0, x1, y1, r_cm=CUSHION_ROUND_R_CM,
                         fill=None, outline=COLOR_CONTOUR, width=LINE_WIDTH):
    # normalise
    if x0 > x1: x0, x1 = x1, x0
    if y0 > y1: y0, y1 = y1, y0
    rx = max(0.0, min(r_cm, (x1-x0)/2.0, (y1-y0)/2.0))
    wpx = (x1 - x0) * tr.scale
    hpx = (y1 - y0) * tr.scale
    rpx = rx * tr.scale
    sx, sy = tr.pt(x0 + rx, y0)

    t.pensize(width)
    t.pencolor(outline)
    pen_up_to(t, sx, sy)
    if fill:
        t.fillcolor(fill)
        t.begin_fill()
    t.setheading(0)
    t.down()
    for _ in range(2):
        t.forward(max(0.0, wpx - 2*rpx)); t.circle(rpx, 90)
        t.forward(max(0.0, hpx - 2*rpx)); t.circle(rpx, 90)
    t.up()
    if fill:
        t.end_fill()

def draw_polygon_cm(t, tr, pts, fill=None, outline=COLOR_CONTOUR, width=LINE_WIDTH):
    if not pts: return
    # Arrondi auto pour coussins rectangulaires axis‑alignés
    if fill == COLOR_CUSHION and _is_axis_aligned_rect(pts):
        xs = [x for x, _ in pts[:-1]] if pts[0] == pts[-1] else [x for x, _ in pts]
        ys = [y for _, y in pts[:-1]] if pts[0] == pts[-1] else [y for _, y in pts]
        x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys)
        draw_rounded_rect_cm(t, tr, x0, y0, x1, y1, r_cm=CUSHION_ROUND_R_CM,
                             fill=fill, outline=outline, width=width)
        return
    # Fallback polygonal
    t.pensize(width); t.pencolor(outline)
    x0, y0 = tr.pt(*pts[0]); pen_up_to(t, x0, y0)
    if fill: t.fillcolor(fill); t.begin_fill()
    t.down()
    for x, y in pts[1:]:
        t.goto(*tr.pt(x, y))
    t.goto(x0, y0)
    if fill: t.end_fill()
    t.up()

# (Quadrillage & repères supprimés à la demande client → fonctions conservées mais non appelées)
def draw_grid_cm(t, tr, tx, ty, step, color, width):  # non utilisé
    pass

def draw_axis_labels_cm(t, tr, tx, ty, step=AXIS_LABEL_STEP, max_mark=AXIS_LABEL_MAX):  # non utilisé
    pass

def _unit(vx, vy):
    n = math.hypot(vx, vy)
    return (vx/n, vy/n) if n else (0, 0)

def draw_double_arrow_px(t, p1, p2, text=None, text_perp_offset_px=0, text_tang_shift_px=0):
    t.pensize(1.5); t.pencolor("black")
    pen_up_to(t, *p1); t.down(); t.goto(*p2); t.up()
    vx, vy = (p2[0]-p1[0], p2[1]-p1[1]); ux, uy = _unit(vx, vy); px, py = -uy, ux
    ah, spread = 12, 5
    for base, sgn in [(p1, +1), (p2, -1)]:
        a = (base[0] + ux*ah*sgn + px*spread, base[1] + uy*ah*sgn + py*spread)
        b = (base[0] + ux*ah*sgn - px*spread, base[1] + uy*ah*sgn - py*spread)
        pen_up_to(t, *base); t.down(); t.goto(*a); t.up()
        pen_up_to(t, *base); t.down(); t.goto(*b); t.up()
    if text:
        cx, cy = ((p1[0]+p2[0])/2.0, (p1[1]+p2[1])/2.0)
        tx = cx + px*text_perp_offset_px + ux*text_tang_shift_px
        ty = cy + py*text_perp_offset_px + uy*text_tang_shift_px
        pen_up_to(t, tx, ty); t.write(text, align="center", font=FONT_DIM)

def draw_double_arrow_vertical_cm(t, tr, x_cm, y0_cm, y1_cm, label):
    draw_double_arrow_px(t, tr.pt(x_cm, y0_cm), tr.pt(x_cm, y1_cm), text=label, text_perp_offset_px=+12)

def draw_double_arrow_horizontal_cm(t, tr, y_cm, x0_cm, x1_cm, label):
    draw_double_arrow_px(t, tr.pt(x0_cm, y_cm), tr.pt(x1_cm, y_cm), text=label,
                         text_perp_offset_px=-12, text_tang_shift_px=20)

def centroid(poly):
    return (sum(x for x,y in poly)/len(poly), sum(y for x,y in poly)/len(poly))

def label_poly(t, tr, poly, text, font=FONT_LABEL):
    cx, cy = centroid(poly); pen_up_to(t, *tr.pt(cx, cy))
    t.write(text, align="center", font=font)

def label_poly_offset_cm(t, tr, poly, text, dx_cm=0.0, dy_cm=0.0, font=FONT_LABEL):
    cx, cy = centroid(poly); x, y = tr.pt(cx + dx_cm, cy + dy_cm)
    pen_up_to(t, x, y); t.write(text, align="center", font=font)

def banquette_dims(poly):
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    L=max(max(xs)-min(xs), max(ys)-min(ys)); P=min(max(xs)-min(xs), max(ys)-min(ys))
    return int(round(L)), int(round(P))

def _split_mid_int(a, b):
    delta = b - a; L = abs(delta); left = L // 2
    return a + (left if delta >= 0 else -left)

def _rectU(x0, y0, x1, y1):
    return [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]

def _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0=None, seat_y1=None):
    """
    Construit 1 ou 2 rectangles verticaux (liste de polygones) pour un dossier.
    - [x0,x1] = épaisseur du dossier (ex: 0 → F0x)
    - [y0,y1] = étendue réelle du dossier à dessiner (tenue compte méridienne)
    - seat_y0/seat_y1 = bornes 'assise' complètes (sans méridienne) : si |seat_y1-seat_y0|>SPLIT_THRESHOLD
      on coupe au milieu de [seat_y0, seat_y1], mais seulement si la coupe tombe dans ]y0,y1[.
    """
    xL, xR = (min(x0, x1), max(x0, x1))
    yB, yT = (min(y0, y1), max(y0, y1))
    rects = []

    do_split = (seat_y0 is not None and seat_y1 is not None and abs(seat_y1 - seat_y0) > SPLIT_THRESHOLD)
    if do_split:
        ymid = _split_mid_int(seat_y0, seat_y1)
        if yB < ymid < yT:
            rects.append(_rectU(xL, yB, xR, ymid))
            rects.append(_rectU(xL, ymid, xR, yT))
            return rects

    rects.append(_rectU(xL, yB, xR, yT))
    return rects

def _build_dossier_horizontal_rects(x0, x1, y0, y1, seat_x0=None, seat_x1=None):
    """
    Construit 1 ou 2 rectangles horizontaux (liste de polygones) pour un dossier bas.
    - [x0,x1] = étendue réelle du dossier à dessiner (tenue compte méridienne)
    - [y0,y1] = épaisseur verticale du dossier (ex: 0 → F0y)
    - seat_x0/seat_x1 = bornes 'assise' complètes : si |seat_x1-seat_x0|>SPLIT_THRESHOLD
      on coupe au milieu de [seat_x0, seat_x1], mais seulement si la coupe tombe dans ]x0,x1[.
    """
    xL, xR = (min(x0, x1), max(x0, x1))
    yB, yT = (min(y0, y1), max(y0, y1))
    rects = []

    do_split = (seat_x0 is not None and seat_x1 is not None and abs(seat_x1 - seat_x0) > SPLIT_THRESHOLD)
    if do_split:
        xmid = _split_mid_int(seat_x0, seat_x1)
        if xL < xmid < xR:
            rects.append(_rectU(xL, yB, xmid, yT))
            rects.append(_rectU(xmid, yB, xR, yT))
            return rects

    rects.append(_rectU(xL, yB, xR, yT))
    return rects

def _poly_has_area(p):
    if not p or len(p) < 4: return False
    xs=[x for x,y in p]; ys=[y for x,y in p]
    return (max(xs)-min(xs) > 1e-9) and (max(ys)-min(ys) > 1e-9)

def _assert_banquettes_max_250(polys):
    for poly in polys.get("banquettes", []):
        L, P = banquette_dims(poly)
        if L > MAX_BANQUETTE:
            raise ValueError(f"Banquette de {L}×{P} cm > {MAX_BANQUETTE} cm — scission supplémentaire nécessaire.")

# =====================================================================
# ================  Outils légende & titres (lisibilité)  =============
# =====================================================================

def _draw_rect_px(t, x, y, w, h, fill=None, outline=COLOR_CONTOUR, width=1):
    t.pensize(width); t.pencolor(outline)
    pen_up_to(t, x, y)
    if fill:
        t.fillcolor(fill); t.begin_fill()
    t.setheading(0); t.down()
    for _ in range(2):
        t.forward(w); t.left(90); t.forward(h); t.left(90)
    t.up()
    if fill:
        t.end_fill()

def _wrap_text(text, max_len=28):
    words = str(text).split()
    if not words: return [""]
    lines=[]; cur=words[0]
    for w in words[1:]:
        if len(cur)+1+len(w) <= max_len:
            cur += " " + w
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines

def draw_title_center(t, tr, tx_cm, ty_cm, text):
    """Titre centré en haut de la scène, à l’intérieur de l’espace visible."""
    left = tr.left_px; bottom = tr.bottom_px
    right = left + tx_cm*tr.scale; top = bottom + ty_cm*tr.scale
    cx = (left + right)/2.0
    y  = top - TITLE_MARGIN_PX
    lines = _wrap_text(text, max_len=34)
    for i, line in enumerate(lines):
        pen_up_to(t, cx, y - i*18)
        t.write(line, align="center", font=FONT_TITLE)

def draw_legend(t, tr, tx_cm, ty_cm, items=None, pos="top-right"):
    """
    Légende avec items = [(label, hex, name), ...]
      - pos: "top-right" (par défaut) ou "top-center" (pour U afin d'éviter recouvrement)
    """
    left = tr.left_px; bottom = tr.bottom_px
    right = left + tx_cm*tr.scale; top = bottom + ty_cm*tr.scale

    # Items / couleurs
    if not items:
        items = [
            ("Dossier",   COLOR_DOSSIER, None),
            ("Accoudoir", COLOR_ACC,     None),
            ("Coussins",  COLOR_CUSHION, None),
            ("Assise",    COLOR_ASSISE,  None),
        ]
    # Taille & position + placement "safe" (jamais sur le schéma)
    box = LEGEND_BOX_PX
    gap = LEGEND_GAP_PX
    # largeur texte (un peu plus pour nom de teinte)
    max_text_w_px = 220
    total_h = len(items) * (box) + (len(items) - 1) * gap
    total_w = box + 8 + max_text_w_px

    # Dimensions du fond de légende
    legend_w = total_w + 16
    legend_h = total_h + 16

    # Bords de l'écran (px)
    scr_left, scr_right = -WIN_W / 2.0, WIN_W / 2.0
    scr_bottom, scr_top = -WIN_H / 2.0, WIN_H / 2.0

    # Limites de la scène utile (schéma)
    # (déjà calculées : left, right, bottom, top)

    # Espaces libres autour du schéma
    free_top = scr_top - top
    free_right = scr_right - right
    free_left = left - scr_left
    free_bottom = bottom - scr_bottom  # pas utilisé mais conservé pour extensions

    def _clamp(v, a, b):
        return max(a, min(b, v))

    SAFE = LEGEND_SAFE_PX
    EDGE = LEGEND_EDGE_PX
    x0 = None; y0 = None

    if pos == "top-center":
        # 1) Idéal : au‑dessus du schéma, centré, à distance SAFE
        if free_top >= legend_h + SAFE:
            cx = (left + right) / 2.0
            x0 = _clamp(cx - total_w / 2.0, scr_left + EDGE, scr_right - EDGE - total_w)
            # y0 = "ligne de tête" des items ; le fond ira de (y0 - total_h - 8) à (y0 + 8)
            y0 = min(scr_top - EDGE, top + SAFE + total_h + 8)
        # 2) Sinon : à droite du schéma
        elif free_right >= legend_w + SAFE:
            x0 = min(scr_right - EDGE - total_w, right + SAFE + 8)
            y0 = min(scr_top - EDGE, top - 12)
        # 3) Sinon : à gauche du schéma
        elif free_left >= legend_w + SAFE:
            x0 = max(scr_left + EDGE, left - SAFE - total_w - 8)
            y0 = min(scr_top - EDGE, top - 12)
        # 4) Repli ultime : en haut‑centre, à l’intérieur (comportement d’avant)
        else:
            cx = (left + right) / 2.0
            x0 = _clamp(cx - total_w / 2.0, left + 12, right - total_w - 12)
            y0 = top - 12
    else:
        # pos = "top-right" → on privilégie la droite, sinon le dessus, puis la gauche
        if free_right >= legend_w + SAFE:
            x0 = min(scr_right - EDGE - total_w, right + SAFE + 8)
            y0 = min(scr_top - EDGE, top - 12)
        elif free_top >= legend_h + SAFE:
            x0 = _clamp(right - total_w, scr_left + EDGE, scr_right - EDGE - total_w)
            y0 = min(scr_top - EDGE, top + SAFE + total_h + 8)
        elif free_left >= legend_w + SAFE:
            x0 = max(scr_left + EDGE, left - SAFE - total_w - 8)
            y0 = min(scr_top - EDGE, top - 12)
        else:
            # Repli : ancien placement en haut‑droite à l’intérieur
            x0 = right - total_w - 12
            y0 = top - 12

    # Fond (léger)
    _draw_rect_px(
        t,
        x0 - 8,
        y0 - total_h - 8,
        total_w + 16,
        total_h + 16,
        fill="#ffffff",
        outline="#aaaaaa",
        width=1,
    )

    # Lignes
    cur_y = y0 - box
    for label, col, name in items:
        _draw_rect_px(t, x0, cur_y, box, box, fill=col, outline=COLOR_CONTOUR, width=1)
        pen_up_to(t, x0 + box + 8, cur_y + box/2 - 6)
        lbl = f"{label}" + ("" if not name else f" ({name})")
        t.write(lbl, align="left", font=FONT_LEGEND)
        cur_y -= (box + gap)

# =====================================================================
# ================  COUSSINS — utilitaires limites méridienne =========
# =====================================================================

def _lim_x(pts, key):
    """Récupère x d’extrémité pour dessin coussins : supporte <key>, <key>_mer et <key>_."""
    if f"{key}_mer" in pts: return pts[f"{key}_mer"][0]
    if f"{key}_"   in pts: return pts[f"{key}_"][0]
    return pts[key][0]

def _lim_y(pts, key):
    """Récupère y d’extrémité pour dessin coussins : supporte <key>, <key>_mer et <key>_."""
    if f"{key}_mer" in pts: return pts[f"{key}_mer"][1]
    if f"{key}_"   in pts: return pts[f"{key}_"][1]
    return pts[key][1]

# =====================================================================
# ================  COUSSINS — moteur "valise" (utilitaires)  =========
# =====================================================================

def _parse_coussins_spec(coussins):
    """
    Retourne un dict :
      - mode: "auto" | "fixed" | "valise"
      - fixed: int (si mode=fixed)
      - range: (min,max)  (si mode=valise)
      - same: bool        (si mode=valise, 'same' pour :s)
    Règles:
      auto          -> ancien auto (65,80,90)
      entier        -> taille globale fixe (toutes branches)
      valise        -> 60..100,  Δ global ≤ 5
      p             -> 60..74,   Δ global ≤ 5
      g             -> 76..100,  Δ global ≤ 5
      s             -> same global, 60..100
      p:s           -> same global, 60..74
      g:s           -> same global, 76..100
    """
    if isinstance(coussins, int):
        return {"mode":"fixed", "fixed": int(coussins)}
    s = str(coussins).strip().lower()
    if s == "auto":
        return {"mode":"auto"}
    if s.isdigit():
        return {"mode":"fixed", "fixed": int(s)}
    same = (":s" in s) or (s == "s")
    base = s.replace(":s", "")
    if base == "s":
        base = "valise"
    if base not in ("valise", "p", "g"):
        raise ValueError(f"Spécification coussins invalide: {coussins}")
    if base == "p":
        r = (60, 74)
    elif base == "g":
        r = (76, 100)
    else:
        r = (60, 100)
    return {"mode":"valise", "range": r, "same": bool(same)}

def _parse_traversins_spec(traversins, allowed={"g","b","d"}):
    """
    Renvoie un set parmi {'g','b','d'} selon la demande utilisateur.
    - traversins peut être None, 'g', 'd', 'b', 'g,d', ['g','d'], ...
    - allowed restreint selon le type de canapé.
    """
    if not traversins:
        return set()
    if isinstance(traversins, (list, tuple, set)):
        raw = {str(x).strip().lower() for x in traversins}
    else:
        raw = {p.strip().lower() for p in str(traversins).replace(";", ",").split(",") if p.strip()}
    return raw & set(allowed)

def _waste_and_count_1d(length, size):
    """Retourne (count, waste) pour un segment 1D de longueur 'length' avec modules de 'size'."""
    if length <= 0 or size <= 0:
        return 0, max(0, length)
    n = int(length // size)
    waste = length - n*size
    return n, waste

# ----- Traversins : dessin -----
def _draw_traversin_block(t, tr, x0, y0, x1, y1):
    draw_rounded_rect_cm(t, tr, x0, y0, x1, y1,
                         r_cm=CUSHION_ROUND_R_CM,
                         fill=COLOR_TRAVERSIN, outline=COLOR_CONTOUR, width=1)
    cx, cy = (x0+x1)/2.0, (y0+y1)/2.0
    pen_up_to(t, *tr.pt(cx, cy))
    t.write("70x30", align="center", font=FONT_CUSHION)

# ----- L-like / U / S1 : placement traversins -----
def _draw_traversins_simple_S1(t, tr, pts, profondeur, dossier, traversins):
    """
    Traversins S1 : positionnés à la fin du dossier.
    - Si méridienne à gauche/droite, on s'aligne sur D0_m / Dx_m.
    """
    if not traversins:
        return 0
    y_base = DOSSIER_THICK if dossier else 0
    usable_h = max(0.0, profondeur - y_base)
    y0 = y_base + max(0.0, (usable_h - TRAVERSIN_LEN)/2.0)
    y1 = y0 + min(TRAVERSIN_LEN, usable_h)

    n = 0
    if "g" in traversins:
        # fin du dossier côté gauche
        x0 = (pts["D0_m"][0] if "D0_m" in pts else (pts["D0"][0] if "D0" in pts else pts["B0"][0]))
        x1 = x0 + TRAVERSIN_THK
        _draw_traversin_block(t, tr, x0, y0, x1, y1); n += 1
    if "d" in traversins:
        # fin du dossier côté droit
        x1 = (pts["Dx_m"][0] if "Dx_m" in pts else (pts["Dx"][0] if "Dx" in pts else pts["Bx"][0]))
        x0 = x1 - TRAVERSIN_THK
        _draw_traversin_block(t, tr, x0, y0, x1, y1); n += 1
    return n

def _draw_traversins_L_like(t, tr, pts, profondeur, traversins):
    """
    Placement des TR pour les formes 'L-like' (LNF v1/v2, LF).
    - 'g'  (gauche, horizontal) : collé sur la FIN DE BANQUETTE gauche (segment By–By2, ignorer *_mer)
    - 'b'  (bas, vertical)      : collé sur l’EXTRÉMITÉ DE BANQUETTE (Bx2–Bx),
                                  même en présence d’une méridienne (on ignore *_mer)
    """
    if not traversins:
        return 0

    F0x, F0y = pts["F0"]
    depth_len = min(TRAVERSIN_LEN, max(0.0, profondeur))
    n = 0

    # --- Gauche (horizontal) → collé sur la FIN DE BANQUETTE (segment By–By2) ---
    if "g" in traversins:
        # Coller à la FIN DE BANQUETTE (segment By–By2), et ignorer toute version *_mer
        y_end = pts["By"][1] if "By" in pts else (F0y + profondeur)
        y0 = y_end - TRAVERSIN_THK
        y1 = y_end
        _draw_traversin_block(t, tr, F0x, y0, F0x + depth_len, y1)
        n += 1

    # --- Bas (vertical) → FIN DE BANQUETTE (Bx2–Bx), pas fin de dossier ---
    if "b" in traversins:
        # On force Bx/Bx2 (et surtout PAS Bx_mer) pour coller au bord de banquette
        if   "Bx"  in pts: x_end = pts["Bx"][0]
        elif "Bx2" in pts: x_end = pts["Bx2"][0]
        else:
            # Secours (très improbable) : retomber sur une des anciennes clés ou un _lim
            if   "DxR" in pts: x_end = pts["DxR"][0]
            elif "Dx2" in pts: x_end = pts["Dx2"][0]
            elif "Dx"  in pts: x_end = pts["Dx"][0]
            else:              x_end = _lim_x(pts, "Bx")

        x0 = x_end - TRAVERSIN_THK
        x1 = x_end
        _draw_traversin_block(t, tr, x0, F0y, x1, F0y + depth_len)
        n += 1

    return n

def _u_right_col_x(variant, pts):
    return pts["Bx"][0] if variant in ("v1","v4") else pts["F02"][0]

def _draw_traversins_U_common(t, tr, variant, pts, profondeur, traversins):
    """
    U v1..v4 : traversins STRICTEMENT sur les segments de dossier internes :
      - gauche  → segment By–By2
      - droite  → segment By3–By4
    On ignore toute version 'avec _' (méridienne) et on n'utilise pas F02 ici.
    """
    if not traversins:
        return 0

    # Longueur du traversin posée dans le sens X (horizontal)
    depth_len = min(TRAVERSIN_LEN, max(0.0, float(profondeur)))
    n = 0

    # --- Gauche : By–By2 (alignement au début du segment)
    if "g" in traversins:
        seg_min, seg_max, y_line = _segment_x_limits(pts, "By", "By2")
        x0, x1 = _clamp_to_segment(seg_min, depth_len, seg_min, seg_max, align="start")
        y0 = y_line - TRAVERSIN_THK
        y1 = y_line
        _draw_traversin_block(t, tr, x0, y0, x1, y1)
        n += 1

    # --- Droite : By3–By4 (alignement à la fin du segment)
    if "d" in traversins:
        seg_min, seg_max, y_line = _segment_x_limits(pts, "By3", "By4")
        x0, x1 = _clamp_to_segment(seg_max, depth_len, seg_min, seg_max, align="end")
        y0 = y_line - TRAVERSIN_THK
        y1 = y_line
        _draw_traversin_block(t, tr, x0, y0, x1, y1)
        n += 1

    return n

def _draw_traversins_U_side_F02(t, tr, pts, profondeur, traversins):
    """
    U1F / U2f : traversins STRICTEMENT sur les segments de dossier internes :
      - gauche  → segment By–By2
      - droite  → segment By3–By4
    On ignore complètement F02 pour le placement des traversins.
    """
    if not traversins:
        return 0

    depth_len = min(TRAVERSIN_LEN, max(0.0, float(profondeur)))
    n = 0

    # --- Gauche : By–By2 (début du segment)
    if "g" in traversins:
        seg_min, seg_max, y_line = _segment_x_limits(pts, "By", "By2")
        x0, x1 = _clamp_to_segment(seg_min, depth_len, seg_min, seg_max, align="start")
        y0 = y_line - TRAVERSIN_THK
        y1 = y_line
        _draw_traversin_block(t, tr, x0, y0, x1, y1)
        n += 1

    # --- Droite : By3–By4 (fin du segment)
    if "d" in traversins:
        seg_min, seg_max, y_line = _segment_x_limits(pts, "By3", "By4")
        x0, x1 = _clamp_to_segment(seg_max, depth_len, seg_min, seg_max, align="end")
        y0 = y_line - TRAVERSIN_THK
        y1 = y_line
        _draw_traversin_block(t, tr, x0, y0, x1, y1)
        n += 1

    return n

# =====================================================================
# ================  COUSSINS — moteur "valise" (utilitaires)  =========
# =====================================================================

def _apply_traversin_limits_L_like(pts, x_end_key, y_end_key, traversins):
    x_end = _lim_x(pts, x_end_key); y_end = _lim_y(pts, y_end_key)
    if traversins:
        if "b" in traversins: x_end -= TRAVERSIN_THK
        if "g" in traversins: y_end -= TRAVERSIN_THK
    return x_end, y_end

def _eval_L_like_counts(pts, size_bas, size_g, shift_bas, x_end_key="Bx", y_end_key="By", traversins=None):
    F0x, F0y = pts["F0"]
    x_end, y_end = _apply_traversin_limits_L_like(pts, x_end_key, y_end_key, traversins)

    xs = F0x + (CUSHION_DEPTH if shift_bas else 0)
    xe = x_end
    y0 = F0y + (0 if shift_bas else CUSHION_DEPTH)
    ye = y_end

    len_b = max(0, xe - xs)
    len_g = max(0, ye - y0)

    nb_b, wb = _waste_and_count_1d(len_b, size_bas)
    nb_g, wg = _waste_and_count_1d(len_g, size_g)
    waste_tot = wb + wg
    cover = nb_b*size_bas + nb_g*size_g
    return {
        "counts": {"bas": nb_b, "gauche": nb_g},
        "waste": waste_tot,
        "cover": cover,
        "geom": {"xs": xs, "xe": xe, "y0": y0, "ye": ye}
    }

def _optimize_valise_L_like(pts, rng, same, x_end_key="Bx", y_end_key="By", traversins=None):
    best = None
    r0, r1 = rng
    for size_g in range(r0, r1+1):
        cand_b = [size_g] if same else range(r0, r1+1)
        for size_b in cand_b:
            if abs(size_b - size_g) > 5:
                continue
            eval_A = _eval_L_like_counts(pts, size_b, size_g, shift_bas=False, x_end_key=x_end_key, y_end_key=y_end_key, traversins=traversins)
            eval_B = _eval_L_like_counts(pts, size_b, size_g, shift_bas=True,  x_end_key=x_end_key, y_end_key=y_end_key, traversins=traversins)
            e = min([eval_A, eval_B], key=lambda E: (E["waste"], -E["cover"], -size_b, -size_g))
            score = (e["waste"], -e["cover"], -size_b, -size_g)
            if (best is None) or (score < best["score"]):
                best = {"score": score, "sizes": {"bas": size_b, "gauche": size_g}, "eval": e,
                        "shift_bas": (e is eval_B)}
    return best

def _draw_L_like_with_sizes(t, tr, pts, sizes, shift_bas, x_end_key="Bx", y_end_key="By", traversins=None):
    F0x, F0y = pts["F0"]
    x_end, y_end = _apply_traversin_limits_L_like(pts, x_end_key, y_end_key, traversins)

    # bas
    xs = F0x + (CUSHION_DEPTH if shift_bas else 0)
    xe = x_end; yb = F0y
    nb = 0; x = xs
    sb = sizes["bas"]
    while x + sb <= xe + 1e-6:
        poly = [(x,yb), (x+sb,yb), (x+sb,yb+CUSHION_DEPTH), (x,yb+CUSHION_DEPTH), (x,yb)]
        draw_polygon_cm(t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1)
        label_poly(t, tr, poly, f"{sb}", font=FONT_CUSHION)
        x += sb; nb += 1

    # gauche
    yg0 = F0y + (0 if shift_bas else CUSHION_DEPTH)
    yg1 = y_end; xg = F0x
    ng = 0; y = yg0
    sg = sizes["gauche"]
    while y + sg <= yg1 + 1e-6:
        poly = [(xg,y), (xg+CUSHION_DEPTH,y), (xg+CUSHION_DEPTH,y+sg), (xg,y+sg), (xg,y)]
        draw_polygon_cm(t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1)
        label_poly(t, tr, poly, f"{sg}", font=FONT_CUSHION)
        y += sg; ng += 1

    return nb + ng, sb, sg

# ----- U2f : évaluation / dessin -----
def _eval_U2f_counts(pts, sb, sg, sd, shiftL, shiftR, traversins=None):
    F0x, F0y = pts["F0"]
    F02x = pts["F02"][0]
    y_end_L = pts.get("By_", pts["By"])[1]
    y_end_R = pts.get("By4_", pts["By4"])[1]
    if traversins:
        if "g" in traversins: y_end_L -= TRAVERSIN_THK
        if "d" in traversins: y_end_R -= TRAVERSIN_THK

    xs = F0x + (CUSHION_DEPTH if shiftL else 0)
    xe = F02x - (CUSHION_DEPTH if shiftR else 0)
    yL0 = F0y + (0 if shiftL else CUSHION_DEPTH)
    yR0 = F0y + (0 if shiftR else CUSHION_DEPTH)

    len_b = max(0, xe - xs)
    len_g = max(0, y_end_L - yL0)
    len_d = max(0, y_end_R - yR0)

    nb, wb = _waste_and_count_1d(len_b, sb)
    ng, wg = _waste_and_count_1d(len_g, sg)
    nd, wd = _waste_and_count_1d(len_d, sd)
    waste = wb + wg + wd
    cover = nb*sb + ng*sg + nd*sd
    return {"counts": {"bas": nb, "gauche": ng, "droite": nd},
            "waste": waste, "cover": cover,
            "geom": {"xs": xs, "xe": xe, "yL0": yL0, "yR0": yR0}}

def _optimize_valise_U2f(pts, rng, same, traversins=None):
    best=None; r0,r1=rng
    for sg in range(r0, r1+1):
        cand_b = [sg] if same else range(r0, r1+1)
        for sb in cand_b:
            cand_d = [sg] if same else range(r0, r1+1)
            for sd in cand_d:
                if max(sb, sg, sd) - min(sb, sg, sd) > 5:
                    continue
                E = []
                for sl in (False, True):
                    for sr in (False, True):
                        E.append(_eval_U2f_counts(pts, sb, sg, sd, sl, sr, traversins=traversins))
                e = min(E, key=lambda x: (x["waste"], -x["cover"], -sb, -sg, -sd))
                score = (e["waste"], -e["cover"], -sb, -sg, -sd)
                if (best is None) or (score < best["score"]):
                    best = {"score": score, "sizes": {"bas": sb, "gauche": sg, "droite": sd}, "eval": e}
    if best:
        chosen = best["eval"]
        for sl in (False, True):
            for sr in (False, True):
                chk = _eval_U2f_counts(pts, best["sizes"]["bas"], best["sizes"]["gauche"], best["sizes"]["droite"], sl, sr, traversins=traversins)
                if abs(chk["waste"] - chosen["waste"])<1e-9 and chk["cover"]==chosen["cover"]:
                    best["shiftL"], best["shiftR"] = sl, sr
                    return best
    return best

def _draw_U2f_with_sizes(t, tr, pts, sizes, shiftL, shiftR, traversins=None):
    F0x, F0y = pts["F0"]
    F02x = pts["F02"][0]
    y_end_L = pts.get("By_", pts["By"])[1]
    y_end_R = pts.get("By4_", pts["By4"])[1]
    if traversins:
        if "g" in traversins: y_end_L -= TRAVERSIN_THK
        if "d" in traversins: y_end_R -= TRAVERSIN_THK

    # Bas
    xs = F0x + (CUSHION_DEPTH if shiftL else 0)
    xe = F02x - (CUSHION_DEPTH if shiftR else 0)
    yb = F0y; sb = sizes["bas"]; nb=0; x=xs
    while x + sb <= xe + 1e-6:
        poly=[(x,yb),(x+sb,yb),(x+sb,yb+CUSHION_DEPTH),(x,yb+CUSHION_DEPTH),(x,yb)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{sb}",font=FONT_CUSHION)
        x+=sb; nb+=1

    # Gauche
    yL0 = F0y + (0 if shiftL else CUSHION_DEPTH)
    xg = F0x; sg = sizes["gauche"]; ng=0; y=yL0
    while y + sg <= y_end_L + 1e-6:
        poly=[(xg,y),(xg+CUSHION_DEPTH,y),(xg+CUSHION_DEPTH,y+sg),(xg,y+sg),(xg,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{sg}",font=FONT_CUSHION)
        y+=sg; ng+=1

    # Droite
    yR0 = F0y + (0 if shiftR else CUSHION_DEPTH)
    xr = F02x; sd = sizes["droite"]; nd=0; y=yR0
    while y + sd <= y_end_R + 1e-6:
        poly=[(xr-CUSHION_DEPTH,y),(xr,y),(xr,y+sd),(xr-CUSHION_DEPTH,y+sd),(xr-CUSHION_DEPTH,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{sd}",font=FONT_CUSHION)
        y+=sd; nd+=1

    return nb+ng+nd

def _draw_cushions_U2f_optimized(t, tr, pts, size, traversins=None):
    F0x, F0y = pts["F0"]
    F02x = pts["F02"][0]
    y_end_L = pts.get("By_", pts["By"])[1]
    y_end_R = pts.get("By4_", pts["By4"])[1]
    if traversins:
        if "g" in traversins: y_end_L -= TRAVERSIN_THK
        if "d" in traversins: y_end_R -= TRAVERSIN_THK

    def cnt_h(x0, x1):
        return int(max(0, x1-x0) // size)
    def cnt_v(y0, y1):
        return int(max(0, y1-y0) // size)

    def score(shift_left, shift_right):
        xs = F0x + (CUSHION_DEPTH if shift_left else 0)
        xe = F02x - (CUSHION_DEPTH if shift_right else 0)
        bas = cnt_h(xs, xe)
        yL0 = F0y + (0 if shift_left else CUSHION_DEPTH)
        yR0 = F0y + (0 if shift_right else CUSHION_DEPTH)
        g = cnt_v(yL0, y_end_L)
        d = cnt_v(yR0, y_end_R)
        w = (max(0, xe-xs) % size) + (max(0, y_end_L-yL0) % size) + (max(0, y_end_R-yR0) % size)
        return (bas+g+d, -w), xs, xe, yL0, yR0

    candidates = [score(False,False), score(True,False), score(False,True), score(True,True)]
    best = max(candidates, key=lambda s: s[0])
    _, xs, xe, yL0, yR0 = best

    count = 0
    # Bas
    y, x = F0y, xs
    while x + size <= xe + 1e-6:
        poly = [(x,y),(x+size,y),(x+size,y+CUSHION_DEPTH),(x,y+CUSHION_DEPTH),(x,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
        x += size; count += 1
    # Gauche
    x, y = F0x, yL0
    while y + size <= y_end_L + 1e-6:
        poly = [(x,y),(x+CUSHION_DEPTH,y),(x+CUSHION_DEPTH,y+size),(x,y+size),(x,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
        y += size; count += 1
    # Droite
    x, y = F02x, yR0
    while y + size <= y_end_R + 1e-6:
        poly = [(x-CUSHION_DEPTH,y),(x,y),(x,y+size),(x-CUSHION_DEPTH,y+size),(x-CUSHION_DEPTH,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
        y += size; count += 1
    return count

# ----- U1F : évaluation / dessin -----
def _eval_U1F_counts(pts, sb, sg, sd, shiftL, shiftR, traversins=None):
    F0x, F0y = pts["F0"]; F02x = pts["F02"][0]
    y_end_L = pts["By_cush"][1]; y_end_R = pts["By4_cush"][1]
    if traversins:
        if "g" in traversins: y_end_L -= TRAVERSIN_THK
        if "d" in traversins: y_end_R -= TRAVERSIN_THK
    xs = F0x + (CUSHION_DEPTH if shiftL else 0)
    xe = F02x - (CUSHION_DEPTH if shiftR else 0)
    yL0 = F0y + (0 if shiftL else CUSHION_DEPTH)
    yR0 = F0y + (0 if shiftR else CUSHION_DEPTH)
    len_b = max(0, xe-xs); len_g=max(0, y_end_L-yL0); len_d=max(0, y_end_R-yR0)
    nb, wb = _waste_and_count_1d(len_b, sb)
    ng, wg = _waste_and_count_1d(len_g, sg)
    nd, wd = _waste_and_count_1d(len_d, sd)
    waste = wb+wg+wd; cover=nb*sb+ng*sg+nd*sd
    return {"counts":{"bas":nb,"gauche":ng,"droite":nd},"waste":waste,"cover":cover}

def _optimize_valise_U1F(pts, rng, same, traversins=None):
    best=None; r0,r1=rng
    for sg in range(r0,r1+1):
        for sb in ([sg] if same else range(r0,r1+1)):
            for sd in ([sg] if same else range(r0,r1+1)):
                if max(sb,sg,sd)-min(sb,sg,sd) > 5:
                    continue
                E=[]
                for sl in (False,True):
                    for sr in (False,True):
                        E.append(_eval_U1F_counts(pts,sb,sg,sd,sl,sr,traversins=traversins))
                e = min(E, key=lambda x: (x["waste"], -x["cover"], -sb, -sg, -sd))
                score=(e["waste"], -e["cover"], -sb, -sg, -sd)
                if (best is None) or (score < best["score"]):
                    best={"score":score, "sizes":{"bas":sb,"gauche":sg,"droite":sd}, "shifts":("?", "?")}
    # Retrouver shifts exacts
    if best:
        tgt = best["score"]
        for sl in (False,True):
            for sr in (False,True):
                chk=_eval_U1F_counts(pts,best["sizes"]["bas"],best["sizes"]["gauche"],best["sizes"]["droite"],sl,sr,traversins=traversins)
                score=(chk["waste"], -chk["cover"], -best["sizes"]["bas"], -best["sizes"]["gauche"], -best["sizes"]["droite"])
                if score==tgt:
                    best["shifts"]=(sl,sr); break
    return best

def _draw_U1F_with_sizes(t,tr,pts,sizes,shiftL,shiftR,traversins=None):
    F0x, F0y = pts["F0"]; F02x=pts["F02"][0]
    y_end_L = pts["By_cush"][1]; y_end_R=pts["By4_cush"][1]
    if traversins:
        if "g" in traversins: y_end_L -= TRAVERSIN_THK
        if "d" in traversins: y_end_R -= TRAVERSIN_THK

    # Bas
    xs = F0x + (CUSHION_DEPTH if shiftL else 0)
    xe = F02x - (CUSHION_DEPTH if shiftR else 0)
    sb=sizes["bas"]; nb=0; x=xs; y=F0y
    while x + sb <= xe + 1e-6:
        poly=[(x,y),(x+sb,y),(x+sb,y+CUSHION_DEPTH),(x,y+CUSHION_DEPTH),(x,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{sb}",font=FONT_CUSHION)
        nb+=1; x+=sb

    # Gauche
    yL0 = F0y + (0 if shiftL else CUSHION_DEPTH)
    sg=sizes["gauche"]; ng=0; xg=F0x; y_=yL0
    while y_ + sg <= y_end_L + 1e-6:
        poly=[(xg,y_),(xg+CUSHION_DEPTH,y_),(xg+CUSHION_DEPTH,y_+sg),(xg,y_+sg),(xg,y_)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{sg}",font=FONT_CUSHION)
        ng+=1; y_+=sg

    # Droite
    yR0 = F0y + (0 if shiftR else CUSHION_DEPTH)
    sd=sizes["droite"]; nd=0; xr=F02x; y_=yR0
    while y_ + sd <= y_end_R + 1e-6:
        poly=[(xr-CUSHION_DEPTH,y_),(xr,y_),(xr,y_+sd),(xr-CUSHION_DEPTH,y_+sd),(xr-CUSHION_DEPTH,y_)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{sd}",font=FONT_CUSHION)
        nd+=1; y_+=sd

    return nb+ng+nd

# ----- U (no fromage) : fonctions de choix et dessin coussins -----
def _u_variant_x_end(variant, pts):
    if variant in ("v1","v4"):
        return pts["Bx"][0]
    else:
        return pts["F02"][0]

def _eval_U_counts(variant, pts, drawn, sb, sg, sd, shiftL, shiftR, traversins=None):
    """
    Evaluate how many cushions of sizes ``sb``, ``sg`` and ``sd`` will fit on
    the bottom, left and right branches of a U‑shaped sofa, considering
    possible méridienne limits.
    """
    F0x, F0y = pts["F0"]
    x_end = _u_variant_x_end(variant, pts)
    xs = F0x + (CUSHION_DEPTH if shiftL else 0)
    xe = x_end - (CUSHION_DEPTH if shiftR else 0)

    y_end_L = pts.get("By_", pts["By"])[1]
    y_end_R = pts.get("By4_", pts["By4"])[1]
    if traversins:
        if "g" in traversins:
            y_end_L -= TRAVERSIN_THK
        if "d" in traversins:
            y_end_R -= TRAVERSIN_THK
    yL0 = F0y + (0 if (not drawn.get("D1", False) or shiftL) else CUSHION_DEPTH)
    has_right = drawn.get("D4", False) or drawn.get("D5", False)
    yR0 = F0y + (0 if (not has_right or shiftR) else CUSHION_DEPTH)

    nb, wb = _waste_and_count_1d(max(0, xe - xs), sb)
    ng, wg = _waste_and_count_1d(max(0, y_end_L - yL0), sg)
    nd, wd = _waste_and_count_1d(max(0, y_end_R - yR0), sd)
    waste = wb + wg + wd
    cover = nb * sb + ng * sg + nd * sd
    return {
        "counts": {"bas": nb, "gauche": ng, "droite": nd},
        "waste": waste,
        "cover": cover,
    }

def _optimize_valise_U(variant, pts, drawn, rng, same, traversins=None):
    best=None; r0,r1=rng
    for sg in range(r0,r1+1):
        for sb in ([sg] if same else range(r0,r1+1)):
            for sd in ([sg] if same else range(r0,r1+1)):
                if max(sb,sg,sd)-min(sb,sg,sd) > 5:
                    continue
                E=[]
                for sl in (False,True):
                    for sr in (False,True):
                        E.append(_eval_U_counts(variant, pts, drawn, sb, sg, sd, sl, sr, traversins=traversins))
                e = min(E, key=lambda x: (x["waste"], -x["cover"], -sb, -sg, -sd))
                score=(e["waste"], -e["cover"], -sb, -sg, -sd)
                if (best is None) or (score < best["score"]):
                    best={"score":score, "sizes":{"bas":sb,"gauche":sg,"droite":sd}}
    if best:
        tgt=best["score"]
        for sl in (False,True):
            for sr in (False,True):
                chk=_eval_U_counts(variant, pts, drawn, best["sizes"]["bas"], best["sizes"]["gauche"], best["sizes"]["droite"], sl, sr, traversins=traversins)
                score=(chk["waste"], -chk["cover"], -best["sizes"]["bas"], -best["sizes"]["gauche"], -best["sizes"]["droite"])
                if score==tgt:
                    best["shiftL"], best["shiftR"] = sl, sr
                    break
    return best

def _draw_U_with_sizes(
    variant, t, tr, pts, sizes, drawn, shiftL, shiftR, traversins=None
):
    """
    Draw cushions with specific sizes for each part of a U‑shaped sofa.

    ``sizes`` should be a dict with keys ``"bas"``, ``"gauche"`` and
    ``"droite"`` giving the cushion size for the bottom, left and right,
    respectively. This version respects méridienne limits via ``By_`` and
    ``By4_`` when present and optional traversins.
    """
    F0x, F0y = pts["F0"]
    x_end = _u_variant_x_end(variant, pts)
    # bottom
    xs = F0x + (CUSHION_DEPTH if shiftL else 0)
    xe = x_end - (CUSHION_DEPTH if shiftR else 0)
    sb = sizes["bas"]
    nb = 0
    x = xs
    y = F0y
    while x + sb <= xe + 1e-6:
        poly = [
            (x, y),
            (x + sb, y),
            (x + sb, y + CUSHION_DEPTH),
            (x, y + CUSHION_DEPTH),
            (x, y),
        ]
        draw_polygon_cm(
            t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1
        )
        label_poly(t, tr, poly, f"{sb}", font=FONT_CUSHION)
        nb += 1
        x += sb

    # left branch
    y_end_L = pts.get("By_", pts["By"])[1]
    if traversins and "g" in traversins:
        y_end_L -= TRAVERSIN_THK
    yL0 = F0y + (
        0
        if (not drawn.get("D1", False) or shiftL)
        else CUSHION_DEPTH
    )
    sg = sizes["gauche"]
    ng = 0
    xg = F0x
    y_ = yL0
    while y_ + sg <= y_end_L + 1e-6:
        poly = [
            (xg, y_),
            (xg + CUSHION_DEPTH, y_),
            (xg + CUSHION_DEPTH, y_ + sg),
            (xg, y_ + sg),
            (xg, y_),
        ]
        draw_polygon_cm(
            t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1
        )
        label_poly(t, tr, poly, f"{sg}", font=FONT_CUSHION)
        ng += 1
        y_ += sg

    # right branch
    y_end_R = pts.get("By4_", pts["By4"])[1]
    if traversins and "d" in traversins:
        y_end_R -= TRAVERSIN_THK
    has_right = drawn.get("D4", False) or drawn.get("D5", False)
    yR0 = F0y + (
        0
        if (not has_right or shiftR)
        else CUSHION_DEPTH
    )
    sd = sizes["droite"]
    nd = 0
    x_col = pts["Bx"][0] if variant in ("v1", "v4") else pts["F02"][0]
    y_ = yR0
    while y_ + sd <= y_end_R + 1e-6:
        poly = [
            (x_col - CUSHION_DEPTH, y_),
            (x_col, y_),
            (x_col, y_ + sd),
            (x_col - CUSHION_DEPTH, y_ + sd),
            (x_col - CUSHION_DEPTH, y_),
        ]
        draw_polygon_cm(
            t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1
        )
        label_poly(t, tr, poly, f"{sd}", font=FONT_CUSHION)
        nd += 1
        y_ += sd

    return nb + ng + nd

# ----- Simple S1 -----
def _optimize_valise_simple(pts, rng, mer_side=None, mer_len=0, traversins=None):
    x0 = pts["B0"][0]; x1 = pts["Bx"][0]
    if mer_side == 'g' and mer_len>0:
        x0 = max(x0, pts.get("B0_m", (x0,0))[0])
    if mer_side == 'd' and mer_len>0:
        x1 = min(x1, pts.get("Bx_m", (x1,0))[0])
    if traversins:
        if "g" in traversins: x0 += TRAVERSIN_THK
        if "d" in traversins: x1 -= TRAVERSIN_THK

    best=None; r0,r1=rng
    for s in range(r0, r1+1):
        n0, w0 = _waste_and_count_1d(max(0, x1-x0), s)
        n1, w1 = _waste_and_count_1d(max(0, x1-(x0+CUSHION_DEPTH)), s)
        if w1 < w0 or (w1==w0 and n1>n0):
            n, waste, off = n1, w1, CUSHION_DEPTH
        else:
            n, waste, off = n0, w0, 0
        score=(waste, -n, -s)
        if (best is None) or (score < best["score"]):
            best={"score":score, "size":s, "offset":off, "count":n}
    return best

def _draw_simple_with_size(t,tr,pts,size,mer_side=None,mer_len=0, traversins=None):
    x0 = pts["B0"][0]; x1 = pts["Bx"][0]
    if mer_side == 'g' and mer_len>0:
        x0 = max(x0, pts.get("B0_m", (x0,0))[0])
    if mer_side == 'd' and mer_len>0:
        x1 = min(x1, pts.get("Bx_m", pts["Bx"])[0])
    if traversins:
        if "g" in traversins: x0 += TRAVERSIN_THK
        if "d" in traversins: x1 -= TRAVERSIN_THK

    n0, w0 = _waste_and_count_1d(max(0,x1-x0), size)
    n1, w1 = _waste_and_count_1d(max(0,x1-(x0+CUSHION_DEPTH)), size)
    off = CUSHION_DEPTH if (w1 < w0 or (w1==w0 and n1>n0)) else 0
    x = x0 + off; y = pts["B0"][1]; n=0
    while x + size <= x1 + 1e-6:
        poly=[(x,y),(x+size,y),(x+size,y+CUSHION_DEPTH),(x,y+CUSHION_DEPTH),(x,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
        x+=size; n+=1
    return n

# =====================================================================
# =======================  LF (L avec angle fromage)  ==================
# =====================================================================
def compute_points_LF_variant(tx, ty, profondeur=DEPTH_STD,
                              dossier_left=True, dossier_bas=True,
                              acc_left=True, acc_bas=True,
                              meridienne_side=None, meridienne_len=0):
    A = profondeur + 20
    prof = profondeur
    pts = {}
    if dossier_left and dossier_bas:
        F0x, F0y = 10, 10
    elif (not dossier_left) and dossier_bas:
        F0x, F0y = 0, 10
    elif dossier_left and (not dossier_bas):
        F0x, F0y = 10, 0
    else:
        F0x, F0y = 0, 0

    pts["F0"]  = (F0x, F0y)
    pts["Fy"]  = (F0x, F0y + A)
    pts["Fx"]  = (F0x + A, F0y)
    pts["Fy2"] = (F0x + prof, F0y + A)
    pts["Fx2"] = (F0x + A, F0y + prof)

    top_y = ty - (ACCOUDOIR_THICK if acc_left else 0)
    pts["By"]  = (F0x, top_y)
    pts["By2"] = (F0x + prof, top_y)

    pts["D0"]  = (0, 0)
    pts["D0x"] = (F0x, 0)
    pts["D0y"] = (0, F0y)
    pts["Dy"]  = (0, F0y + A)
    pts["Dy2"] = (0, top_y)

    pts["Ay"]  = (0, ty)
    pts["Ay2"] = (F0x + prof, ty)
    pts["Ay_"] = (F0x, ty)

    banq_stop_x = tx - (ACCOUDOIR_THICK if acc_bas else 0)
    pts["Dx"]  = (F0x + A, 0)
    pts["Dx2"] = (banq_stop_x, 0)
    pts["Bx"]  = (banq_stop_x, F0y)
    pts["Bx2"] = (banq_stop_x, F0y + prof)

    pts["Ax"]  = (tx, 0)
    pts["Ax2"] = (tx, F0y + prof)
    pts["Ax_"] = (tx, F0y)

    if meridienne_side == 'b' and meridienne_len > 0:
        dx2_stop = min(banq_stop_x, tx - meridienne_len)
        pts["Dx2"] = (dx2_stop, 0)
        pts["Bx_"] = (tx - meridienne_len, F0y)

    if meridienne_side == 'g' and meridienne_len > 0:
        mer_y = max(F0y + A, top_y - meridienne_len); mer_y = min(mer_y, top_y)
        pts["By_"] = (F0x, mer_y)
        pts["Dy2"] = (0, min(top_y, mer_y))

    if dossier_left and not dossier_bas:
        pts["D0y"] = (0, 0)
    if dossier_bas and not dossier_left:
        pts["D0x"] = (0, 0)

    return pts

def _choose_cushion_size_auto(pts, tx, ty, meridienne_side=None, meridienne_len=0, traversins=None):
    xF, yF = pts["F0"]
    x_end = pts.get("Bx_", pts.get("Bx", (tx, yF)))[0]
    if meridienne_side == 'b' and meridienne_len > 0:
        x_end = min(x_end, tx - meridienne_len)
    y_start = yF + CUSHION_DEPTH
    y_end = pts.get("By_", pts.get("By", (xF, ty)))[1]
    if traversins:
        if "b" in traversins: x_end -= TRAVERSIN_THK
        if "g" in traversins: y_end -= TRAVERSIN_THK
    usable_h = max(0.0, x_end - xF)
    usable_v = max(0.0, y_end - y_start)

    candidates = [65, 80, 90]
    def score(s):
        waste_h = usable_h % s if usable_h > 0 else 0
        waste_v = usable_v % s if usable_v > 0 else 0
        return (max(waste_h, waste_v), -s)
    return min(candidates, key=score)

def draw_cousins_and_return_count(t, tr, pts, tx, ty, coussins, meridienne_side, meridienne_len, traversins=None):
    if isinstance(coussins, str) and coussins.strip().lower() == "auto":
        size = _choose_cushion_size_auto(pts, tx, ty, meridienne_side, meridienne_len, traversins=traversins)
    else:
        size = int(coussins)

    F0x, F0y = pts["F0"]
    x_end = pts.get("Bx_", pts.get("Bx", (tx, F0y)))[0]
    y_end = pts.get("By_", pts.get("By", (F0x, ty)))[1]
    if traversins:
        if "b" in traversins: x_end -= TRAVERSIN_THK
        if "g" in traversins: y_end -= TRAVERSIN_THK

    def count_bas(x_start, x_stop):
        L = max(0, x_stop - x_start)
        return int(L // size)
    def count_gauche(y_start, y_stop):
        L = max(0, y_stop - y_start)
        return int(L // size)

    # Compare orientation A vs B
    A_bas = count_bas(F0x, x_end); A_g = count_gauche(F0y + CUSHION_DEPTH, y_end)
    B_bas = count_bas(F0x + CUSHION_DEPTH, x_end); B_g = count_gauche(F0y, y_end)
    use_shift = (B_bas + B_g, -( (x_end-(F0x+CUSHION_DEPTH))%size + (y_end-F0y)%size )) > (A_bas + A_g, -((x_end-F0x)%size + (y_end-(F0y+CUSHION_DEPTH))%size))

    count = 0
    # bas
    y = F0y
    x_cur = F0x + (CUSHION_DEPTH if use_shift else 0)
    while x_cur + size <= x_end + 1e-6:
        poly = [(x_cur, y), (x_cur+size, y), (x_cur+size, y+CUSHION_DEPTH), (x_cur, y+CUSHION_DEPTH), (x_cur, y)]
        draw_polygon_cm(t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1)
        label_poly(t, tr, poly, f"{size}", font=FONT_CUSHION)
        x_cur += size; count += 1
    # gauche
    x = F0x
    y_cur = F0y + (0 if use_shift else CUSHION_DEPTH)
    while y_cur + size <= y_end + 1e-6:
        poly = [(x, y_cur), (x+CUSHION_DEPTH, y_cur), (x+CUSHION_DEPTH, y_cur+size), (x, y_cur+size), (x, y_cur)]
        draw_polygon_cm(t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1)
        label_poly(t, tr, poly, f"{size}", font=FONT_CUSHION)
        y_cur += size; count += 1

    return count, size

def build_polys_LF_variant(pts, tx, ty, profondeur=DEPTH_STD,
                           dossier_left=True, dossier_bas=True,
                           acc_left=True, acc_bas=True,
                           meridienne_side=None, meridienne_len=0):
    polys={"angle":[],"banquettes":[],"dossiers":[],"accoudoirs":[]}

    angle=[pts["F0"],pts["Fx"],pts["Fx2"],pts["Fy2"],pts["Fy"],pts["F0"]]
    polys["angle"].append(angle)

    ban_g=[pts["Fy"],pts["Fy2"],pts["By2"],pts["By"],pts["Fy"]]
    Lg=abs(pts["By"][1]-pts["Fy"][1])
    split_g = False
    if Lg>SPLIT_THRESHOLD:
        split_g = True
        mid_y=_split_mid_int(pts["Fy"][1],pts["By"][1])
        Fy_mid=(pts["Fy"][0],mid_y); Fy2_mid=(pts["Fy2"][0],mid_y)
        polys["banquettes"]+=[
            [pts["Fy"],pts["Fy2"],Fy2_mid,Fy_mid,pts["Fy"]],
            [Fy_mid,Fy2_mid,pts["By2"],pts["By"],Fy_mid]
        ]
    else:
        polys["banquettes"].append(ban_g)

    ban_b=[pts["Fx"],pts["Fx2"],pts["Bx2"],pts["Bx"],pts["Fx"]]
    Lb=abs(pts["Bx"][0]-pts["Fx"][0])
    split_b = False
    if Lb>SPLIT_THRESHOLD:
        split_b = True
        mid_x=_split_mid_int(pts["Fx"][0],pts["Bx"][0])
        Fx_mid=(mid_x,pts["Fx"][1]); Fx2_mid=(mid_x,pts["Fx2"][1])
        polys["banquettes"]+=[
            [pts["Fx"],pts["Fx2"],Fx2_mid,Fx_mid,pts["Fx"]],
            [Fx_mid,Fx2_mid,pts["Bx2"],pts["Bx"],Fx_mid]
        ]
    else:
        polys["banquettes"].append(ban_b)

    if dossier_left:
        # retour gauche (inchangé)
        dos_g_from=[pts["D0"],pts["D0x"],pts["F0"],pts["Fy"],pts["Dy"],pts["D0"]] if dossier_bas \
            else [pts["D0y"],pts["F0"],pts["Fy"],pts["Dy"],pts["D0y"]]
        polys["dossiers"].append(dos_g_from)
        # bande sur la banquette gauche : scindée si nécessaire
        x0, x1 = 0, pts["F0"][0]
        y0 = pts["Dy"][1]
        y1 = pts.get("By_", pts["By"])[1]
        seat_y0 = pts["Fy"][1]
        seat_y1 = pts["By"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)
    if dossier_bas:
        # retour bas (inchangé)
        dos_b_from=[pts["D0x"],pts["Dx"],pts["Fx"],pts["F0"],pts["D0x"]] if dossier_left \
            else [pts["D0x"],pts["F0"],pts["Fx"],pts["Dx"],pts["D0x"]]
        polys["dossiers"].append(dos_b_from)
        # bande sur la banquette bas : scindée si nécessaire
        y0, y1 = 0, pts["F0"][1]
        x0 = pts["Dx"][0]
        x1 = pts.get("Bx_", pts["Bx"])[0]
        seat_x0 = pts["Fx"][0]
        seat_x1 = pts["Bx"][0]
        polys["dossiers"] += _build_dossier_horizontal_rects(x0, x1, y0, y1, seat_x0, seat_x1)

    if acc_left:
        acc_g=[pts["Dy2"],pts["Ay"],pts["Ay2"],pts["By2"],pts["Dy2"]] if dossier_left \
            else [pts["By"],pts["Ay_"],pts["Ay2"],pts["By2"],pts["By"]]
        polys["accoudoirs"].append(acc_g)
    if acc_bas:
        acc_b=[pts["Dx2"],pts["Ax"],pts["Ax2"],pts["Bx2"],pts["Dx2"]] if dossier_bas \
            else [pts["Bx"],pts["Ax_"],pts["Ax2"],pts["Bx2"],pts["Bx"]]
        polys["accoudoirs"].append(acc_b)

    polys["split_flags"]={"left":split_g,"bottom":split_b,"right":False}
    return polys

def render_LF_variant(tx, ty, profondeur=DEPTH_STD,
                      dossier_left=True, dossier_bas=True,
                      acc_left=True, acc_bas=True,
                      meridienne_side=None, meridienne_len=0,
                      coussins="auto",
                      traversins=None,
                      couleurs=None,
                      window_title="LF — variantes"):
    if meridienne_side == 'g' and acc_left:
        raise ValueError("Erreur: une méridienne gauche ne peut pas coexister avec un accoudoir gauche.")
    if meridienne_side == 'b' and acc_bas:
        raise ValueError("Erreur: une méridienne bas ne peut pas coexister avec un accoudoir bas.")

    trv = _parse_traversins_spec(traversins, allowed={"g","b"})
    legend_items = _resolve_and_apply_colors(couleurs)

    pts=compute_points_LF_variant(tx,ty,profondeur,dossier_left,dossier_bas,acc_left,acc_bas,meridienne_side,meridienne_len)
    polys=build_polys_LF_variant(pts,tx,ty,profondeur,dossier_left,dossier_bas,acc_left,acc_bas,meridienne_side,meridienne_len)
    _assert_banquettes_max_250(polys)

    screen=turtle.Screen(); screen.setup(WIN_W,WIN_H)
    screen.title(f"{window_title} — {tx}x{ty} cm — prof={profondeur} — méridienne {meridienne_side or '-'}={meridienne_len} — coussins={coussins}")
    t=turtle.Turtle(visible=False); t.speed(0); screen.tracer(False)
    tr=WorldToScreen(tx,ty,WIN_W,WIN_H,PAD_PX,ZOOM)

    # (Quadrillage et repères supprimés)

    for poly in polys["dossiers"]:   draw_polygon_cm(t,tr,poly,fill=COLOR_DOSSIER)
    for poly in polys["banquettes"]: draw_polygon_cm(t,tr,poly,fill=COLOR_ASSISE)
    for poly in polys["accoudoirs"]: draw_polygon_cm(t,tr,poly,fill=COLOR_ACC)
    for poly in polys["angle"]:      draw_polygon_cm(t,tr,poly,fill=COLOR_ASSISE)

    # Traversins (visuel) + comptage
    n_traversins = _draw_traversins_L_like(t, tr, pts, profondeur, trv)

    draw_double_arrow_vertical_cm(t,tr,-25,0,ty,f"{ty} cm")
    draw_double_arrow_horizontal_cm(t,tr,-25,0,tx,f"{tx} cm")

    banquette_sizes = []
    if polys["angle"]:
        side = int(round(pts["Fy"][1] - pts["F0"][1]))
        # Écrire les dimensions d'angle sur deux lignes et centrer dans le carré d'angle
        # Pour l'angle, on affiche la première dimension sans unité suivie d'un « x » et la seconde avec « cm »
        label_poly(t, tr, polys["angle"][0], f"{side}x\n{side} cm")
    # Afficher les dimensions des banquettes en les décalant légèrement lorsqu'elles sont verticales
    for poly in polys["banquettes"]:
        L, P = banquette_dims(poly)
        banquette_sizes.append((L, P))
        # Afficher la première dimension sans unité suivie d'un « x », la seconde avec « cm »
        text = f"{L}x\n{P} cm"
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # Si la banquette est plus haute que large, décaler le texte vers la droite pour l'éloigner des coussins
        # Réduction de 3 cm : offset moindre pour un positionnement plus proche des coussins
        if bb_h >= bb_w:
            label_poly_offset_cm(t, tr, poly, text, dx_cm=CUSHION_DEPTH + 7, dy_cm=0.0)
        else:
            label_poly(t, tr, poly, text)
    for poly in polys["dossiers"]: label_poly(t,tr,poly,"10")
    for poly in polys["accoudoirs"]: label_poly(t,tr,poly,"15")

    # ===== COUSSINS =====
    spec = _parse_coussins_spec(coussins)
    if spec["mode"] == "auto":
        cushions_count, chosen_size = draw_cousins_and_return_count(t,tr,pts,tx,ty,"auto",meridienne_side,meridienne_len,traversins=trv)
        total_line = f"{coussins} → {cushions_count} × {chosen_size} cm"
    elif spec["mode"] == "fixed":
        cushions_count, chosen_size = draw_cousins_and_return_count(t,tr,pts,tx,ty,int(spec["fixed"]),meridienne_side,meridienne_len,traversins=trv)
        total_line = f"{coussins} → {cushions_count} × {chosen_size} cm"
    else:
        best = _optimize_valise_L_like(pts, spec["range"], spec["same"], x_end_key="Bx", y_end_key="By", traversins=trv)
        if not best:
            raise ValueError("Aucune configuration valise valide pour LF.")
        sizes = best["sizes"]; shift = best["shift_bas"]
        n, sb, sg = _draw_L_like_with_sizes(t, tr, pts, sizes, shift, x_end_key="Bx", y_end_key="By", traversins=trv)
        cushions_count = n
        total_line = _format_valise_counts_console(
            {"bas": sb, "gauche": sg},
            best.get("counts", best.get("eval", {}).get("counts")),
            cushions_count,
        )

    # Légende (couleurs)
    draw_legend(t, tr, tx, ty, items=legend_items, pos="top-right")

    screen.tracer(True); t.hideturtle()
    add_split = int(polys["split_flags"]["left"] and dossier_left) + int(polys["split_flags"]["bottom"] and dossier_bas)
    A = profondeur + 20
    print("=== Rapport canapé (LF) ===")
    print(f"Dimensions : {tx}×{ty} cm — profondeur : {profondeur} cm")
    print(f"Banquettes : {len(polys['banquettes'])} → {banquette_sizes}")
    # Comptage pondéré des dossiers : <=110cm → 0.5, >110cm → 1
    dossiers_count = _compute_dossiers_count(polys)
    dossiers_str = f"{int(dossiers_count)}" if abs(dossiers_count - int(dossiers_count)) < 1e-9 else f"{dossiers_count}"
    print(f"Dossiers : {dossiers_str} (+{add_split} via scission) | Accoudoirs : {len(polys['accoudoirs'])}")
    print(f"Banquettes d’angle : 1")
    print(f"Angles : 1 × {A}×{A} cm")
    print(f"Traversins : {n_traversins} × 70x30")
    print(f"Coussins : {total_line}")
    turtle.done()

# =====================================================================
# ========================  U2f (2 angles fromage)  ====================
# =====================================================================
def compute_points_U2f(tx, ty_left, tz_right, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True, dossier_right=True,
                       acc_left=True, acc_bas=True, acc_right=True,
                       meridienne_side=None, meridienne_len=0):
    A = profondeur + 20
    pts = {}
    # Offsets depend on presence of left and bottom backrests (10 cm if present, 0 otherwise)
    F0x = 10 if dossier_left else 0
    F0y = 10 if dossier_bas else 0
    pts["D0"] = (0, 0)
    pts["D0x"] = (F0x, 0)
    pts["D0y"] = (0, F0y)
    pts["F0"] = (F0x, F0y)
    # Base of the left branch: height A above F0y
    pts["Fy"]  = (F0x,      F0y + A)
    pts["Fy2"] = (F0x+profondeur, F0y + A)
    # Start of the bottom run (between left and right branches)
    pts["Fx"]  = (F0x + A,  F0y)
    pts["Fx2"] = (F0x + A,  F0y + profondeur)

    top_y_L = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    # Left branch vertical points: align with F0y and F0x when there is no backrest
    pts["Dy"]  = (0, F0y + A)
    pts["Dy2"] = (0, top_y_L)
    pts["By"]  = (F0x, top_y_L)
    pts["By2"] = (F0x + profondeur, top_y_L)
    # Armrest end and alignment for the left branch
    pts["Ay"]  = (0, ty_left)
    pts["Ay2"] = (F0x + profondeur, ty_left)
    pts["Ay_"] = (F0x, ty_left)

    # Determine the interior end of the bottom run: subtract 10 cm only if a right backrest exists
    F02x = tx - (10 if dossier_right else 0)
    # Left branch end of bottom run occurs A cm before F02x
    BxL = F02x - A
    # Points for the bottom and right branches
    pts["Dx"]  = (F0x + A, 0)
    pts["Dx2"] = (BxL,     0)
    pts["Bx"]  = (BxL,     F0y)
    pts["Bx2"] = (BxL,     F0y + profondeur)

    pts["F02"] = (F02x, F0y)
    pts["Fy4"] = (F02x, F0y + A)
    pts["Fy3"] = (F02x - profondeur, F0y + A)
    top_y_R = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    pts["By3"]=(pts["Fy3"][0], top_y_R); pts["By4"]=(F02x, top_y_R)
    pts["D02"] = (tx, 0)
    # D02y starts at the same height as the base of the sofa (F0y)
    pts["D02y"] = (tx, F0y)
    # Right branch vertical segments align with F0y + A
    pts["Dy_r"] = (tx, F0y + A)
    pts["Dy2_r"] = (tx, top_y_R)
    # Armrest points (unchanged except for left/backrest offset at right)
    pts["Ax"]    = (pts["By3"][0], tz_right)
    pts["Ax2"]   = (tx, tz_right)
    # Adjust Ax_par depending on right backrest presence (subtract 10 cm only if dossier_right)
    pts["Ax_par"] = (tx - (10 if dossier_right else 0), tz_right)

    if meridienne_side == 'g' and meridienne_len > 0:
        mer_y_L = max(10 + A, ty_left - meridienne_len); mer_y_L = min(mer_y_L, top_y_L)
        pts["By_"]=(pts["By"][0], mer_y_L); pts["By2_"]=(pts["By2"][0], mer_y_L)
        pts["Dy2"]=(0, mer_y_L)
    if meridienne_side == 'd' and meridienne_len > 0:
        mer_y_R = max(10 + A, tz_right - meridienne_len); mer_y_R = min(mer_y_R, top_y_R)
        pts["By4_"]=(pts["By4"][0], mer_y_R); pts["Dy2_r"]=(tx, mer_y_R)

    pts["_ty_canvas"] = max(ty_left, tz_right)
    return pts

def build_polys_U2f(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                    dossier_left=True, dossier_bas=True, dossier_right=True,
                    acc_left=True, acc_bas=True, acc_right=True):
    polys = {"angles": [], "banquettes": [], "dossiers": [], "accoudoirs": []}
    # U2F — couture overlays for bottom angle seams (drawn after all other dossiers)
    angle_seams = []

    angle_L = [pts["F0"], pts["Fx"], pts["Fx2"], pts["Fy2"], pts["Fy"], pts["F0"]]
    polys["angles"].append(angle_L)
    angle_R = [pts["Bx2"], pts["Bx"], pts["F02"], pts["Fy4"], pts["Fy3"], pts["Bx2"]]
    polys["angles"].append(angle_R)

    # G
    ban_g = [pts["Fy"], pts["Fy2"], pts["By2"], pts["By"], pts["Fy"]]
    Lg = abs(pts["By"][1] - pts["Fy"][1])
    split_g = False
    if Lg > SPLIT_THRESHOLD:
        split_g = True
        mid_y = _split_mid_int(pts["Fy"][1], pts["By"][1])
        Fy_mid  = (pts["Fy"][0],  mid_y); Fy2_mid = (pts["Fy2"][0], mid_y)
        polys["banquettes"] += [[pts["Fy"],pts["Fy2"],Fy2_mid,Fy_mid,pts["Fy"]],
                                [Fy_mid,Fy2_mid,pts["By2"],pts["By"],Fy_mid]]
    else:
        polys["banquettes"].append(ban_g)

    # Bas
    ban_b = [pts["Fx"], pts["Fx2"], pts["Bx2"], pts["Bx"], pts["Fx"]]
    Lb = abs(pts["Bx"][0] - pts["Fx"][0])
    split_b = False
    if Lb > SPLIT_THRESHOLD:
        split_b = True
        mid_x = _split_mid_int(pts["Fx"][0], pts["Bx"][0])
        Fx_mid  = (mid_x, pts["Fx"][1]); Fx2_mid = (mid_x, pts["Fx2"][1])
        polys["banquettes"] += [[pts["Fx"],pts["Fx2"],Fx2_mid,Fx_mid,pts["Fx"]],
                                [Fx_mid,Fx2_mid,pts["Bx2"],pts["Bx"],Fx_mid]]
    else:
        polys["banquettes"].append(ban_b)

    # Droite
    ban_r = [pts["Fy3"], pts["By3"], pts["By4"], pts["Fy4"], pts["Fy3"]]
    Lr = abs(pts["By4"][1] - pts["Fy4"][1])
    split_r = False
    if Lr > SPLIT_THRESHOLD:
        split_r = True
        mid_y = _split_mid_int(pts["Fy4"][1], pts["By4"][1])
        Fy3_mid = (pts["Fy3"][0], mid_y); Fy4_mid = (pts["Fy4"][0], mid_y)
        polys["banquettes"] += [[pts["Fy3"],Fy3_mid,Fy4_mid,pts["Fy4"],pts["Fy3"]],
                                [Fy3_mid,pts["By3"],pts["By4"],Fy4_mid,Fy3_mid]]
    else:
        polys["banquettes"].append(ban_r)

    if dossier_left:
        # retour gauche : dépend de la présence du dossier bas
        if dossier_bas:
            # avec dossier bas : le retour inclut les 10 cm inférieurs
            polys["dossiers"].append([pts["D0"], pts["D0x"], pts["F0"], pts["Fy"], pts["Dy"], pts["D0"]])
        else:
            # sans dossier bas : on démarre à la hauteur de l'assise (10 cm)
            polys["dossiers"].append([pts["D0y"], pts["F0"], pts["Fy"], pts["Dy"], pts["D0y"]])
        # bande sur la banquette gauche : scindée si nécessaire
        x0, x1 = 0, pts["F0"][0]
        y0 = pts["Dy"][1]
        y1 = pts.get("By_", pts["By"])[1]
        seat_y0 = pts["Fy"][1]
        seat_y1 = pts["By"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)
    # --- Dossiers bas : suivre la scission de la banquette du bas ---
    if dossier_bas:
        F0x, F0y = pts["F0"]
        F02x     = pts["F02"][0]  # fin intérieure côté droit
        # longueur de l'assise centrale (entre Fx et Bx)
        Lb = abs(pts["Bx"][0] - pts["Fx"][0])
        if Lb > SPLIT_THRESHOLD:
            mid_x = _split_mid_int(pts["Fx"][0], pts["Bx"][0])
            polys["dossiers"] += [
                _rectU(F0x, 0, mid_x, F0y),
                _rectU(mid_x, 0, F02x, F0y),
            ]
        else:
            polys["dossiers"].append(_rectU(F0x, 0, F02x, F0y))
    if dossier_right:
        # retour droit (dossier 6)
        if dossier_bas:
            # avec dossier bas : le retour inclut les 10 cm inférieurs
            F02x = pts["F02"][0]
            polys["dossiers"].append(_rectU(F02x, 0, pts["D02"][0], pts["Dy_r"][1]))
        else:
            # sans dossier bas : on démarre à la hauteur de l'assise (10 cm)
            polys["dossiers"].append([pts["D02y"], pts["F02"], pts["Fy4"], pts["Dy_r"], pts["D02y"]])
        # bande sur la banquette droite : scindée si nécessaire
        x0, x1 = pts["F02"][0], tx
        y0 = pts["Fy4"][1]
        y1 = pts.get("By4_", pts["By4"])[1]
        seat_y0 = pts["Fy4"][1]
        seat_y1 = pts["By4"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)

    if acc_left and dossier_left:
        polys["accoudoirs"].append([pts["Dy2"], pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"]])
    elif acc_left and not dossier_left:
        polys["accoudoirs"].append([pts["By"], pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"]])

    if acc_right and dossier_right:
        polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], pts["Dy2_r"], pts["By3"]])
    elif acc_right and not dossier_right:
        polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts.get("Ax_par", (tx-10, max(ty_left, tz_right))), pts["By4"], pts["By3"]])

    polys["split_flags"]={"left":split_g,"bottom":split_b,"right":split_r}
    # ------------------------------------------------------------
    # U2F — Overlays des coutures d’angle bas (toujours au-dessus de D3)
    # ------------------------------------------------------------
    # Ajoute deux fines bandes verticales sur les arêtes internes des angles
    # pour rendre visible la délimitation des dossiers d'angle bas.
    if dossier_bas:
        # Épaisseur visuelle de la couture : ~2% de la hauteur du dossier bas, bornée
        F0y_local = pts["F0"][1]
        seam = max(0.2, min(0.8, F0y_local * 0.02))
        # Angle gauche (D2) : trait vertical centré entre Fx.x et Dx.x
        # On trace cette couture dès qu'il y a un dossier bas, même si dossier_left est False.
        x_left_candidates = []
        if "Fx" in pts:
            x_left_candidates.append(pts["Fx"][0])
        if "Dx" in pts:
            x_left_candidates.append(pts["Dx"][0])
        if x_left_candidates:
            if len(x_left_candidates) > 1:
                x = 0.5 * (x_left_candidates[0] + x_left_candidates[1])
            else:
                x = x_left_candidates[0]
            angle_seams.append(_rectU(x - seam/2, 0, x + seam/2, F0y_local))
        # Angle droit (D4/D5) : trait vertical centré sur l'arête Dx2–Bx
        # On trace cette couture dès qu'il y a un dossier bas, même si dossier_right est False.
        x_right_candidates = []
        # Utiliser Dx2 et Bx pour la couture droite (médiane robuste si les deux existent)
        if "Dx2" in pts:
            x_right_candidates.append(pts["Dx2"][0])
        if "Bx" in pts:
            x_right_candidates.append(pts["Bx"][0])
        if x_right_candidates:
            if len(x_right_candidates) > 1:
                xr = 0.5 * (x_right_candidates[0] + x_right_candidates[1])
            else:
                xr = x_right_candidates[0]
            angle_seams.append(_rectU(xr - seam/2, 0, xr + seam/2, F0y_local))
    # Flusher les coutures en dernier pour garantir leur visibilité
    if angle_seams:
        polys["dossiers"] += angle_seams
    return polys

def _draw_cushions_U2f_optimized_wrapper(t, tr, pts, size, traversins=None):
    return _draw_cushions_U2f_optimized(t, tr, pts, size, traversins=traversins)

def render_U2f_variant(tx, ty_left, tz_right, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True, dossier_right=True,
                       acc_left=True, acc_bas=True, acc_right=True,
                       meridienne_side=None, meridienne_len=0,
                       coussins="auto",
                       traversins=None,
                       couleurs=None,
                       window_title="U2F — variantes"):
    if meridienne_side == 'g' and acc_left:
        raise ValueError("Erreur: une méridienne gauche ne peut pas coexister avec un accoudoir gauche.")
    if meridienne_side == 'd' and acc_right:
        raise ValueError("Erreur: une méridienne droite ne peut pas coexister avec un accoudoir droit.")

    trv = _parse_traversins_spec(traversins, allowed={"g","d"})
    legend_items = _resolve_and_apply_colors(couleurs)

    pts = compute_points_U2f(tx, ty_left, tz_right, profondeur,
                             dossier_left, dossier_bas, dossier_right,
                             acc_left, acc_bas, acc_right,
                             meridienne_side, meridienne_len)
    polys = build_polys_U2f(pts, tx, ty_left, tz_right, profondeur,
                            dossier_left, dossier_bas, dossier_right,
                            acc_left, acc_bas, acc_right)
    _assert_banquettes_max_250(polys)

    ty_canvas = pts["_ty_canvas"]
    screen = turtle.Screen(); screen.setup(WIN_W, WIN_H)
    screen.title(f"{window_title} — tx={tx} / ty(left)={ty_left} / tz(right)={tz_right} — prof={profondeur}")
    t = turtle.Turtle(visible=False); t.speed(0); screen.tracer(False)
    tr = WorldToScreen(tx, ty_canvas, WIN_W, WIN_H, PAD_PX, ZOOM)

    # (Quadrillage et repères supprimés)

    for poly in polys["dossiers"]:   draw_polygon_cm(t, tr, poly, fill=COLOR_DOSSIER)
    for poly in polys["banquettes"]: draw_polygon_cm(t, tr, poly, fill=COLOR_ASSISE)
    for poly in polys["accoudoirs"]: draw_polygon_cm(t, tr, poly, fill=COLOR_ACC)
    for poly in polys["angles"]:     draw_polygon_cm(t, tr, poly, fill=COLOR_ASSISE)

    # Traversins (visuel) + comptage
    n_traversins = _draw_traversins_U_side_F02(t, tr, pts, profondeur, trv)

    draw_double_arrow_vertical_cm(t, tr, -25,    0, ty_left,  f"{ty_left} cm")
    draw_double_arrow_vertical_cm(t, tr,  tx+25, 0, tz_right, f"{tz_right} cm")
    draw_double_arrow_horizontal_cm(t, tr, -25,  0, tx, f"{tx} cm")

    A = profondeur + 20
    for poly in polys["angles"]:
        # Écrire les dimensions d’angle sur deux lignes, première ligne sans unité suivie d’un « x »
        label_poly(t, tr, poly, f"{A}x\n{A} cm")

    banquette_sizes = []
    for poly in polys["banquettes"]:
        L, P = banquette_dims(poly)
        banquette_sizes.append((L, P))
        # Affichage de la dimension principale sans unité suivie d'un « x », et de la profondeur avec « cm »
        text = f"{L}x\n{P} cm"
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # Décaler horizontalement si la banquette est plus haute que large
        if bb_h >= bb_w:
            cx = sum(xs) / len(xs)
            # Réduire les offsets : 3 cm en moins sur les branches verticales
            # Branche gauche : CUSHION_DEPTH+7 (ex: 22 cm). Branche droite : -(CUSHION_DEPTH-8) (ex: -7 cm).
            dx = (CUSHION_DEPTH + 7) if cx < tx / 2.0 else -(CUSHION_DEPTH - 8)
            label_poly_offset_cm(t, tr, poly, text, dx_cm=dx, dy_cm=0.0)
        else:
            label_poly(t, tr, poly, text)

    # ===== COUSSINS =====
    spec = _parse_coussins_spec(coussins)
    if spec["mode"] == "auto":
        # ancien auto (65,80,90)
        F0x, F0y = pts["F0"]; F02x = pts["F02"][0]
        y_end_L = pts.get("By_", pts["By"])[1]
        y_end_R = pts.get("By4_", pts["By4"])[1]
        if trv:
            if "g" in trv: y_end_L -= TRAVERSIN_THK
            if "d" in trv: y_end_R -= TRAVERSIN_THK
        best, best_score = 65, (1e9, -1)
        for s in (65,80,90):
            usable_h = max(0, F02x - F0x)
            usable_v_L = max(0, y_end_L - (F0y + CUSHION_DEPTH))
            usable_v_R = max(0, y_end_R - (F0y + CUSHION_DEPTH))
            waste_h = usable_h % s if usable_h > 0 else 0
            waste_v = max(usable_v_L % s if usable_v_L > 0 else 0,
                          usable_v_R % s if usable_v_R > 0 else 0)
            score = (max(waste_h, waste_v), -s)
            if score < best_score:
                best_score, best = score, s
        size = best
        cushions_count = _draw_cushions_U2f_optimized_wrapper(t, tr, pts, size, traversins=trv)
        total_line = f"{coussins} → {cushions_count} × {size} cm"
    elif spec["mode"] == "fixed":
        size = int(spec["fixed"])
        cushions_count = _draw_cushions_U2f_optimized_wrapper(t, tr, pts, size, traversins=trv)
        total_line = f"{coussins} → {cushions_count} × {size} cm"
    else:
        best = _optimize_valise_U2f(pts, spec["range"], spec["same"], traversins=trv)
        if not best:
            raise ValueError("Aucune configuration valise valide pour U2f.")
        sizes = best["sizes"]; shiftL = best["shiftL"]; shiftR = best["shiftR"]
        cushions_count = _draw_U2f_with_sizes(t, tr, pts, sizes, shiftL, shiftR, traversins=trv)
        sb, sg, sd = sizes["bas"], sizes["gauche"], sizes["droite"]
        total_line = _format_valise_counts_console(
            {"bas": sb, "gauche": sg, "droite": sd},
            best.get("counts", best.get("eval", {}).get("counts")),
            cushions_count,
        )

    # Titre demandé + légende (U → légende en haut-centre)
    draw_title_center(t, tr, tx, ty_canvas, "Canapé en U avec deux angles")
    draw_legend(t, tr, tx, ty_canvas, items=legend_items, pos="top-center")

    screen.tracer(True); t.hideturtle()
    add_split = sum(int(v) for v in polys.get("split_flags", {}).values())
    print("=== Rapport canapé U2f ===")
    print(f"Dimensions : tx={tx} / ty(left)={ty_left} / tz(right)={tz_right} — prof={profondeur} (A={A})")
    print(f"Méridienne : {meridienne_side or '-'} ({meridienne_len} cm)")
    print(f"Banquettes : {len(polys['banquettes'])} → {banquette_sizes}")
    dossier_bonus = int(polys["split_flags"].get("left", False) and dossier_left) + \
                   int(polys["split_flags"].get("bottom", False) and dossier_bas) + \
                   int(polys["split_flags"].get("right", False) and dossier_right)
    # Comptage pondéré des dossiers : <=110cm → 0.5, >110cm → 1
    dossiers_count = _compute_dossiers_count(polys)
    dossiers_str = f"{int(dossiers_count)}" if abs(dossiers_count - int(dossiers_count)) < 1e-9 else f"{dossiers_count}"
    print(f"Dossiers : {dossiers_str} (+{dossier_bonus} via scission) | Accoudoirs : {len(polys['accoudoirs'])}")
    print(f"Banquettes d'angle : 2")
    print(f"Angles : 2 × {A}×{A} cm")
    print(f"Traversins : {n_traversins} × 70x30")
    print(f"Coussins : {total_line}")
    turtle.done()

# =====================================================================
# ===================  U1F (1 angle fromage) — v1..v4  =================
# =====================================================================
# (version validée + palette + légende U en haut-centre)

def _split_banquette_if_needed_U1F(poly):
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys)
    w=x1-x0; h=y1-y0
    if w<=SPLIT_THRESHOLD and h<=SPLIT_THRESHOLD:
        return [poly], False
    res=[]
    split=True
    if w>=h and w>SPLIT_THRESHOLD:
        mx=_split_mid_int(x0,x1)
        left = [(x0,y0),(mx,y0),(mx,y1),(x0,y1),(x0,y0)]
        right=[(mx,y0),(x1,y0),(x1,y1),(mx,y1),(mx,y0)]
        res += [left,right]
    else:
        my=_split_mid_int(y0,y1)
        low =[(x0,y0),(x1,y0),(x1,my),(x0,my),(x0,y0)]
        high=[(x0,my),(x1,my),(x1,y1),(x0,y1),(x0,my)]
        res += [low,high]
    return res, split

def _common_offsets_u1f(profondeur, dossier_left, dossier_bas, dossier_right):
    A = profondeur + 20
    F0x = 10 if dossier_left else 0
    F0y = 10 if dossier_bas  else 0
    return A, F0x, F0y

def _choose_cushion_size_auto_U1F(pts, traversins=None):
    F0x, F0y = pts["F0"]; F02x = pts["F02"][0]
    x_len = max(0, F02x - F0x)
    y_end_L = pts["By_cush"][1]
    y_end_R = pts["By4_cush"][1]
    if traversins:
        if "g" in traversins: y_end_L -= TRAVERSIN_THK
        if "d" in traversins: y_end_R -= TRAVERSIN_THK
    yL0 = F0y + CUSHION_DEPTH
    yR0 = F0y + CUSHION_DEPTH
    best, score_best = 65, (1e9,-1)
    for s in (65,80,90):
        waste_bas = x_len % s if x_len>0 else 0
        waste_g   = max(0, y_end_L - yL0) % s if y_end_L>yL0 else 0
        waste_d   = max(0, y_end_R - yR0) % s if y_end_R>yR0 else 0
        sc = (max(waste_bas,waste_g,waste_d), -s)
        if sc < score_best: best, score_best = s, sc
    return best

def _draw_coussins_U1F(t, tr, pts, size, traversins=None):
    F0x, F0y = pts["F0"]; F02x = pts["F02"][0]
    y_end_L = pts["By_cush"][1]; y_end_R = pts["By4_cush"][1]
    if traversins:
        if "g" in traversins: y_end_L -= TRAVERSIN_THK
        if "d" in traversins: y_end_R -= TRAVERSIN_THK
    def cnt_h(x0,x1): return int(max(0,x1-x0)//size)
    def cnt_v(y0,y1): return int(max(0,y1-y0)//size)
    def score(sL,sR):
        xs = F0x + (CUSHION_DEPTH if sL else 0)
        xe = F02x - (CUSHION_DEPTH if sR else 0)
        bas = cnt_h(xs,xe)
        yL0 = F0y + (0 if sL else CUSHION_DEPTH)
        yR0 = F0y + (0 if sR else CUSHION_DEPTH)
        g = cnt_v(yL0,y_end_L); d = cnt_v(yR0,y_end_R)
        w = (max(0,xe-xs)%size) + (max(0,y_end_L-yL0)%size) + (max(0,y_end_R-yR0)%size)
        return (bas+g+d, -w), xs, xe, yL0, yR0
    candidates=[score(False,False),score(True,False),score(False,True),score(True,True)]
    _, xs, xe, yL0, yR0 = max(candidates, key=lambda s:s[0])

    count=0
    # BAS
    y = F0y; x = xs
    while x + size <= xe + 1e-6:
        poly=[(x,y),(x+size,y),(x+size,y+CUSHION_DEPTH),(x,y+CUSHION_DEPTH),(x,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
        count+=1; x+=size
    # GAUCHE
    x = F0x; y = yL0
    while y + size <= y_end_L + 1e-6:
        poly=[(x,y),(x+CUSHION_DEPTH,y),(x+CUSHION_DEPTH,y+size),(x,y+size),(x,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
        count+=1; y+=size
    # DROITE
    x = F02x; y = yR0
    while y + size <= y_end_R + 1e-6:
        poly=[(x-CUSHION_DEPTH,y),(x,y),(x,y+size),(x-CUSHION_DEPTH,y+size),(x-CUSHION_DEPTH,y)]
        draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
        label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
        count+=1; y+=size
    return count

def compute_points_U1F_v1(tx, ty_left, tz_right, profondeur=DEPTH_STD,
                          dossier_left=True, dossier_bas=True, dossier_right=True,
                          acc_left=True, acc_right=True,
                          meridienne_side=None, meridienne_len=0):
    if meridienne_side == 'g' and acc_left:  raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
    if meridienne_side == 'd' and acc_right: raise ValueError("Méridienne droite interdite avec accoudoir droit.")

    A, F0x, F0y = _common_offsets_u1f(profondeur, dossier_left, dossier_bas, dossier_right)
    pts={}
    pts["D0"]=(0,0); pts["D0x"]=(F0x,0); pts["D0y"]=(0,F0y); pts["F0"]=(F0x,F0y)

    # Gauche
    pts["Fy"]  = (F0x, F0y + A); pts["Fy2"]=(F0x+profondeur, F0y + A)
    pts["Fx"]  = (F0x + A, F0y); pts["Fx2"]=(F0x + A, F0y + profondeur); pts["Dx"]=(F0x + A, 0)

    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    top_y_L_dos  = (max(F0y + A, top_y_L_full - meridienne_len) if meridienne_side=='g' else top_y_L_full)
    pts["By"]=(F0x, top_y_L_full); pts["By2"]=(F0x+profondeur, top_y_L_full)
    pts["Dy"]=(0, F0y + A); pts["Dy2"]=(0, top_y_L_dos)
    pts["By_dL"]=(F0x, top_y_L_dos)   # stop dossier G avec méridienne G
    pts["Ay"]=(0, ty_left); pts["Ay2"]=(F0x+profondeur, ty_left); pts["Ay_"]=(F0x, ty_left)

    # Bas/droite
    D02x_x = tx - (10 if (dossier_right or dossier_bas) else 0)
    pts["D02x"]=(D02x_x,0); pts["F02"]=(D02x_x, F0y)
    Dx2_x = D02x_x - profondeur
    pts["Dx2"]=(Dx2_x,0); pts["Bx"]=(Dx2_x, F0y); pts["Bx2"]=(Dx2_x, F0y + profondeur)
    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    top_y_R_dos  = (max(F0y + A, top_y_R_full - meridienne_len) if meridienne_side=='d' else top_y_R_full)
    pts["By3"]=(Dx2_x, top_y_R_full); pts["By4"]=(D02x_x, top_y_R_full); pts["By4_d"]=(D02x_x, top_y_R_dos)
    pts["D02"]=(tx,0); pts["D02y"]=(tx, F0y); pts["Dy3"]=(tx, top_y_R_dos)
    pts["Ax"]=(Dx2_x, tz_right); pts["Ax2"]=(tx, tz_right); pts["Ax_par"]=(D02x_x, tz_right)

    if not dossier_bas:
        pts["D0y"]=(0,0); pts["D02y"]=(tx,0)

    pts["By_cush"]=(pts["By"][0], min(pts["By"][1], pts["Dy2"][1]))
    pts["By4_cush"]=(pts["By4"][0], min(pts["By4"][1], pts["By4_d"][1]))

    pts["_A"]=A; pts["_ty_canvas"]=max(ty_left, tz_right)
    pts["_draw"]={
        "D1": bool(dossier_left), "D2": bool(dossier_left),
        "D3": bool(dossier_bas),  "D4": bool(dossier_bas), "D5": bool(dossier_bas),
        "D6": bool(dossier_right),
    }
    pts["_acc"]={"L":acc_left, "R":acc_right}
    return pts

def build_polys_U1F_v1(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True, dossier_right=True,
                       acc_left=True, acc_right=True):
    polys={"angle": [], "banquettes": [], "dossiers": [], "accoudoirs": []}
    d={"D1":dossier_left,"D2":dossier_left,"D3":dossier_bas,"D4":dossier_bas,"D5":dossier_bas,"D6":dossier_right}

    polys["angle"].append([pts["F0"], pts["Fx"], pts["Fx2"], pts["Fy2"], pts["Fy"], pts["F0"]])

    split_any=False
    for ban in (
        [pts["Fy"], pts["Fy2"], pts["By2"], pts["By"], pts["Fy"]],
        [pts["Fx2"], pts["Fx"], pts["Bx"], pts["Bx2"], pts["Fx2"]],
        [pts["Bx"], pts["F02"], pts["By4"], pts["By3"], pts["Bx"]],
    ):
        pieces, split = _split_banquette_if_needed_U1F(ban)
        polys["banquettes"] += pieces
        split_any = split_any or split

    if d["D1"]:
        # scinder D1 sur la banquette gauche si nécessaire
        x0, x1 = 0, pts["F0"][0]
        y0 = pts["Fy"][1]
        y1 = pts["By_dL"][1]
        seat_y0, seat_y1 = pts["Fy"][1], pts["By"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)
    if d["D2"]: polys["dossiers"].append([pts["D0x"], pts["D0"], pts["Dy"], pts["Fy"], pts["D0x"]])
    # --- Dossiers bas : 1 ou 2 rectangles selon scission de l'assise ---
    if d["D3"] or d["D4"] or d["D5"]:
        F0x, F0y   = pts["F0"]
        xL_total   = F0x
        xR_total   = pts["F02"][0]                 # fin intérieure à droite
        Lb         = abs(pts["Bx"][0] - pts["Fx"][0])  # assise centrale
        if Lb > SPLIT_THRESHOLD:
            mid_x = _split_mid_int(pts["Fx"][0], pts["Bx"][0])
            polys["dossiers"] += [
                _rectU(xL_total, 0, mid_x,  F0y),
                _rectU(mid_x,    0, xR_total, F0y),
            ]
        else:
            polys["dossiers"].append(_rectU(xL_total, 0, xR_total, F0y))
    if d["D6"]:
        # scinder D6 (droit haut) si nécessaire
        x0, x1 = pts["D02x"][0], tx
        y0 = 0
        y1 = pts["By4_d"][1]
        seat_y0, seat_y1 = pts["F0"][1], pts["By4"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)

    if acc_left:
        if d["D1"]:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_"]])
    if acc_right:
        if d["D6"]:
            dy_top = pts.get("Dy3", None) or pts.get("Dy4", None)
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], dy_top, pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    # U1F v1 — délimitations verticales des dossiers bas :
    # - Dx–Fx  : jonction dossiers 3 et 4
    # - Dx2–Bx : jonction dossiers 4 et 5
    if dossier_bas:
        F0y_local = pts["F0"][1]
        seam = max(0.2, min(0.8, F0y_local * 0.02))
        # Jonction D3/D4 : trait centré entre Dx.x et Fx.x
        x_mid_candidates = []
        if "Dx" in pts:
            x_mid_candidates.append(pts["Dx"][0])
        if "Fx" in pts:
            x_mid_candidates.append(pts["Fx"][0])
        if x_mid_candidates:
            if len(x_mid_candidates) > 1:
                xm = 0.5 * (x_mid_candidates[0] + x_mid_candidates[1])
            else:
                xm = x_mid_candidates[0]
            polys["dossiers"].append(_rectU(xm - seam/2, 0, xm + seam/2, F0y_local))
        # Jonction D4/D5 : trait centré entre Dx2.x et Bx.x
        x_right_candidates = []
        if "Dx2" in pts:
            x_right_candidates.append(pts["Dx2"][0])
        if "Bx" in pts:
            x_right_candidates.append(pts["Bx"][0])
        if x_right_candidates:
            if len(x_right_candidates) > 1:
                xr = 0.5 * (x_right_candidates[0] + x_right_candidates[1])
            else:
                xr = x_right_candidates[0]
            polys["dossiers"].append(_rectU(xr - seam/2, 0, xr + seam/2, F0y_local))

    polys["split_flags"]={"any":split_any}
    return polys

def compute_points_U1F_v2(tx, ty_left, tz_right, profondeur=DEPTH_STD,
                          dossier_left=True, dossier_bas=True, dossier_right=True,
                          acc_left=True, acc_right=True,
                          meridienne_side=None, meridienne_len=0):
    if meridienne_side == 'g' and acc_left:  raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
    if meridienne_side == 'd' and acc_right: raise ValueError("Méridienne droite interdite avec accoudoir droit.")

    A, F0x, F0y = _common_offsets_u1f(profondeur, dossier_left, dossier_bas, dossier_right)
    pts={}
    pts["D0"]=(0,0); pts["D0x"]=(F0x,0); pts["D0y"]=(0,F0y); pts["F0"]=(F0x,F0y)

    # Gauche
    pts["Fy"]=(F0x, F0y + A); pts["Fy2"]=(F0x+profondeur, F0y + A)
    pts["Fx"]=(F0x + A, F0y); pts["Fx2"]=(F0x + A, F0y + profondeur); pts["Dx"]=(F0x + A, 0)

    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    top_y_L_dos  = (max(F0y + A, top_y_L_full - meridienne_len) if meridienne_side=='g' else top_y_L_full)
    pts["By"]=(F0x, top_y_L_full); pts["By2"]=(F0x+profondeur, top_y_L_full)
    pts["Dy"]=(0, F0y + A); pts["Dy2"]=(0, top_y_L_dos)
    pts["By_dL"]=(F0x, top_y_L_dos)
    pts["Ay"]=(0, ty_left); pts["Ay2"]=(F0x+profondeur, ty_left); pts["Ay_"]=(F0x, ty_left)

    # Droite interne F02 (dep. dossier_right)
    F02x = tx - (10 if dossier_right else 0)
    pts["F02"]=(F02x, F0y)
    # ajout alias D02x pour build_polys_U1F_v2
    pts["D02x"] = (F02x, 0)  # alias utilisé par build_polys_U1F_v2

    # Bas v2
    pts["Dx2"]=(F02x, 0); pts["Bx2"]=(F02x, F0y + profondeur)

    # Colonne droite (x = F02x - profondeur)
    col_x = F02x - profondeur
    pts["Fy3"]=(col_x, F0y + profondeur); pts["By3"]=(col_x, tz_right - (ACCOUDOIR_THICK if acc_right else 0))

    # Extrémité droite
    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    top_y_R_dos  = (max(F0y + A, top_y_R_full - meridienne_len) if meridienne_side=='d' else top_y_R_full)
    pts["By4"]=(F02x, top_y_R_full); pts["By4_d"]=(F02x, top_y_R_dos)
    pts["D02"]=(tx,0); pts["D02y"]=(tx, F0y); pts["Dy3"]=(tx, F0y + profondeur); pts["Dy4"]=(tx, top_y_R_dos)
    pts["Ax"]=(col_x, tz_right); pts["Ax2"]=(tx, tz_right); pts["Ax_par"]=(F02x, tz_right)

    if not dossier_bas:
        pts["D0y"]=(0,0); pts["D02y"]=(tx,0)

    pts["By_cush"]=(pts["By"][0], min(pts["By"][1], pts["Dy2"][1]))
    pts["By4_cush"]=(pts["By4"][0], min(pts["By4"][1], pts["By4_d"][1]))

    pts["_A"]=A; pts["_ty_canvas"]=max(ty_left, tz_right)
    pts["_draw"]={
        "D1": bool(dossier_left), "D2": bool(dossier_left),
        "D3": bool(dossier_bas),  "D4": bool(dossier_bas), "D5": bool(dossier_bas),
        "D6": bool(dossier_right),
    }
    pts["_acc"]={"L":acc_left, "R":acc_right}
    return pts

def build_polys_U1F_v2(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True, dossier_right=True,
                       acc_left=True, acc_right=True):
    polys={"angle": [], "banquettes": [], "dossiers": [], "accoudoirs": []}
    d={"D1":dossier_left,"D2":dossier_left,"D3":dossier_bas,"D4":dossier_bas,"D5":dossier_bas,"D6":dossier_right}

    polys["angle"].append([pts["F0"], pts["Fx"], pts["Fx2"], pts["Fy2"], pts["Fy"], pts["F0"]])

    split_any=False
    for ban in (
        [pts["Fy"], pts["Fy2"], pts["By2"], pts["By"], pts["Fy"]],
        [pts["Fx2"], pts["Fx"], pts["F02"], pts["Bx2"], pts["Fx2"]],
        [pts["By3"], pts["Fy3"], pts["Bx2"], pts["By4"], pts["By3"]],
    ):
        pieces, split = _split_banquette_if_needed_U1F(ban)
        polys["banquettes"] += pieces
        split_any = split_any or split

    # D1 (gauche) — scinder selon la banquette gauche si nécessaire
    if d["D1"]:
        # Rectangle vertical sur la banquette gauche : de y=Fy.y à y=By_dL.y
        x0, x1 = 0, pts["F0"][0]
        y0 = pts["Fy"][1]
        y1 = pts["By_dL"][1]
        # Bornes complètes de l'assise gauche (sans méridienne) : Fy.y → By.y
        seat_y0, seat_y1 = pts["Fy"][1], pts["By"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)
    if d["D2"]: polys["dossiers"].append([pts["D0x"], pts["D0"], pts["Dy"], pts["Fy"], pts["D0x"]])
    # --- Dossiers bas : 1 ou 2 rectangles selon scission de l'assise ---
    if d["D3"] or d["D4"] or d["D5"]:
        F0x, F0y = pts["F0"]
        xL_total = F0x
        xR_total = pts["F02"][0]
        # assise centrale = Fx → F02
        Lb = abs(pts["F02"][0] - pts["Fx"][0])
        if Lb > SPLIT_THRESHOLD:
            mid_x = _split_mid_int(pts["Fx"][0], pts["F02"][0])
            polys["dossiers"] += [
                _rectU(xL_total, 0, mid_x,  F0y),
                _rectU(mid_x,    0, xR_total, F0y),
            ]
        else:
            polys["dossiers"].append(_rectU(xL_total, 0, xR_total, F0y))
    # Ajout d'une bande de dossier bas-droite (D5) pour la variante v2.
    # Le polygone est défini lorsque le dossier bas est actif OU lorsque le dossier droit est actif.
    # Cela garantit la fermeture visuelle même si seul le dossier droit est présent.
    if d["D5"] or dossier_right:
        polys["dossiers"].append([pts["Dx2"], pts["D02"], pts["Dy3"], pts["Bx2"], pts["Dx2"]])
    if d["D6"]:
        # D6 (droit haut) — scinder selon la banquette droite si nécessaire
        x0, x1 = pts["D02x"][0], tx
        # Le dossier droit démarre à la hauteur Fy3.y (banquette droite en v2)
        y0 = pts["Fy3"][1]
        y1 = pts["By4_d"][1]
        seat_y0, seat_y1 = pts["Fy3"][1], pts["By4"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)

    if acc_left:
        if d["D1"]:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_"]])
    if acc_right:
        if d["D6"]:
            dy_top = pts.get("Dy4", pts.get("Dy3"))
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], dy_top, pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    # U1F v1/v2 — délimitation verticale Dx–Fx (jonction dossiers 3 et 4)
    if dossier_bas:
        F0y_local = pts["F0"][1]
        seam = max(0.2, min(0.8, F0y_local * 0.02))
        x_mid_candidates = []
        if "Dx" in pts:
            x_mid_candidates.append(pts["Dx"][0])
        if "Fx" in pts:
            x_mid_candidates.append(pts["Fx"][0])
        if x_mid_candidates:
            if len(x_mid_candidates) > 1:
                xm = 0.5 * (x_mid_candidates[0] + x_mid_candidates[1])
            else:
                xm = x_mid_candidates[0]
            polys["dossiers"].append(_rectU(xm - seam/2, 0, xm + seam/2, F0y_local))

    polys["split_flags"]={"any":split_any}
    return polys

def compute_points_U1F_v3(tx, ty_left, tz_right, profondeur=DEPTH_STD,
                          dossier_left=True, dossier_bas=True, dossier_right=True,
                          acc_left=True, acc_right=True,
                          meridienne_side=None, meridienne_len=0):
    if meridienne_side == 'g' and acc_left:
        raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
    if meridienne_side == 'd' and acc_right:
        raise ValueError("Méridienne droite interdite avec accoudoir droit.")

    A = profondeur + 20
    F0x = 10 if dossier_left else 0
    F0y = 10 if dossier_bas  else 0

    pts = {}
    pts["D0"]=(0,0); pts["D0x"]=(F0x,0); pts["D0y"]=(0,F0y); pts["F0"]=(F0x, F0y)

    # Gauche
    pts["Fx"]  = (F0x + profondeur, F0y)
    pts["Fx2"] = (F0x + profondeur, F0y + profondeur)
    pts["Dx"]  = (F0x + profondeur, 0)

    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    top_y_L_dos  = (max(F0y + A, top_y_L_full - meridienne_len) if meridienne_side == 'g' else top_y_L_full)
    pts["By"]=(F0x, top_y_L_full); pts["By2"]=(F0x + profondeur, top_y_L_full)
    pts["Dy"]=(0, F0y + A); pts["Dy2"]=(0, top_y_L_dos); pts["By_dL"]=(F0x, top_y_L_dos)
    pts["Ay"]=(0, ty_left); pts["Ay2"]=(F0x + profondeur, ty_left); pts["Ay_"]=(F0x, ty_left)

    # Droite globale
    F02x = tx - (10 if dossier_right else 0)
    pts["F02"]=(F02x, F0y)
    pts["D02x"]=(F02x, 0)

    # Assise bas (côté angle)
    bx_x = F02x - (profondeur + 20)
    pts["Bx"]=(bx_x, F0y); pts["Bx2"]=(bx_x, F0y + profondeur); pts["Dx2"]=(bx_x, 0)

    # Colonne droite et hautesurs
    col_x = F02x - profondeur
    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    top_y_R_dos  = (max(F0y + A, top_y_R_full - meridienne_len) if meridienne_side == 'd' else top_y_R_full)
    pts["Fy"]  = (col_x, F0y + A)
    pts["Fy2"] = (F02x,  F0y + A)
    # ajout alias Fy3 pour build_polys_U1F_v3 : Fy3 = Fy
    pts["Fy3"] = pts["Fy"]  # alias attendu par build_polys_U1F_v3
    pts["By3"] = (col_x, top_y_R_full)
    pts["By4"] = (F02x,  top_y_R_full)
    pts["By4_d"]=(F02x,  top_y_R_dos)
    pts["D02"]  = (tx, 0)
    pts["D02y"] = (tx, F0y)
    pts["Dy3"]  = (tx, top_y_R_dos)
    pts["Dy2R"] = (tx, F0y + A)  # pour D5/D6

    pts["Ax"]=(col_x, tz_right); pts["Ax2"]=(tx, tz_right); pts["Ax_par"]=(F02x, tz_right)

    if not dossier_bas:
        pts["D0y"]=(0, 0); pts["D02y"]=(tx, 0)

    # Bornes coussins (arrêt si méridienne)
    pts["By_cush"]  = (pts["By"][0],  min(pts["By"][1],  pts["Dy2"][1]))
    pts["By4_cush"] = (pts["By4"][0], min(pts["By4"][1], pts["By4_d"][1]))

    pts["_A"]=A; pts["_ty_canvas"]=max(ty_left, tz_right)
    pts["_draw"] = {"D1":bool(dossier_left), "D2":bool(dossier_bas), "D3":bool(dossier_bas),
                    "D4":bool(dossier_bas), "D5":bool(dossier_right), "D6":bool(dossier_right)}
    pts["_acc"]={"L":acc_left, "R":acc_right}
    return pts

def build_polys_U1F_v3(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True, dossier_right=True,
                       acc_left=True, acc_right=True):
    polys={"angle": [], "banquettes": [], "dossiers": [], "accoudoirs": []}
    d={"D1":dossier_left,"D2":dossier_bas,"D3":dossier_bas,"D4":dossier_bas,"D5":dossier_right,"D6":dossier_right}

    # Banquettes
    split_any=False
    ban_g = [pts["F0"], pts["By"], pts["By2"], pts["Fx"],  pts["F0"]]
    ban_b = [pts["Fx"], pts["Bx"], pts["Bx2"], pts["Fx2"], pts["Fx"]]
    ban_d = [pts["Fy"], pts["By3"], pts["By4"], pts["Fy2"], pts["Fy"]]
    for ban in (ban_g, ban_b, ban_d):
        pieces, split = _split_banquette_if_needed_U1F(ban)
        polys["banquettes"] += pieces
        split_any = split_any or split

    # Angle fromage gauche
    polys["angle"].append([pts["Bx"], pts["F02"], pts["Fy2"], pts["Fy"], pts["Bx2"], pts["Bx"]])

    # Dossiers
    if d["D1"]:
        # scinder D1 sur la banquette gauche si nécessaire
        x0, x1 = 0, pts["F0"][0]
        # Étirer le dossier gauche jusqu'à la base du canapé (y=0) pour éviter le « trou »
        y0 = 0
        y1 = pts["By_dL"][1]
        # Bornes complètes de l'assise gauche pour la scission (F0.y → By.y)
        seat_y0, seat_y1 = pts["F0"][1], pts["By"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)
    # --- Dossiers bas : 1 ou 2 rectangles selon scission de l'assise ---
    if d["D2"] or d["D3"] or d["D4"]:
        F0x, F0y = pts["F0"]
        xL_total = F0x
        xR_total = pts["F02"][0]
        Lb = abs(pts["Bx"][0] - pts["Fx"][0])
        if Lb > SPLIT_THRESHOLD:
            mid_x = _split_mid_int(pts["Fx"][0], pts["Bx"][0])
            polys["dossiers"] += [
                _rectU(xL_total, 0, mid_x,  F0y),
                _rectU(mid_x,    0, xR_total, F0y),
            ]
        else:
            polys["dossiers"].append(_rectU(xL_total, 0, xR_total, F0y))
    if d["D5"]:
        polys["dossiers"].append([pts["D02x"], pts["Fy2"], pts["Dy2R"], pts["D02"], pts["D02x"]])
    if d["D6"]:
        # scinder D6 (droit haut) si nécessaire
        x0, x1 = pts["D02x"][0], tx
        y0 = pts["Fy3"][1]
        y1 = pts["By4_d"][1]
        seat_y0, seat_y1 = pts["Fy3"][1], pts["By4"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)

    # U1F v3 — délimitation verticale Dx–Fx (jonction dossiers 3 et 4)
    if dossier_bas:
        F0y_local = pts["F0"][1]
        seam = max(0.2, min(0.8, F0y_local * 0.02))
        x_mid_candidates = []
        if "Dx" in pts:
            x_mid_candidates.append(pts["Dx"][0])
        if "Fx" in pts:
            x_mid_candidates.append(pts["Fx"][0])
        if x_mid_candidates:
            if len(x_mid_candidates) > 1:
                xm = 0.5 * (x_mid_candidates[0] + x_mid_candidates[1])
            else:
                xm = x_mid_candidates[0]
            polys["dossiers"].append(_rectU(xm - seam/2, 0, xm + seam/2, F0y_local))

    # --- Overlay couture verticale Dx2–Bx pour délimiter le dossier bas (jonction D4/D5) ---
    # Dessinée en dernier dans les dossiers pour garantir la visibilité. Ceci reproduit le
    # comportement de la variante v4 pour rendre visible la séparation entre la banquette
    # centrale et la banquette droite (Dx2–Bx). Nous ne modifions aucune géométrie
    # existante : seule cette fine bande est ajoutée en overlay si le côté droit est actif.
    if d.get("D4") or d.get("D5"):
        F0y_local = pts["F0"][1]
        # épaisseur visuelle cohérente (~2 % de la hauteur du dossier bas), bornée entre 0.2 et 0.8 cm
        seam = max(0.2, min(0.8, F0y_local * 0.02))

        x_right_candidates = []
        if "Dx2" in pts:
            x_right_candidates.append(pts["Dx2"][0])
        if "Bx" in pts:
            x_right_candidates.append(pts["Bx"][0])

        if x_right_candidates:
            # On prend la moyenne des coordonnées pour robustesse en cas de léger décalage
            xr = sum(x_right_candidates) / len(x_right_candidates)
            polys["dossiers"].append(
                _rectU(xr - seam / 2, 0,
                       xr + seam / 2, F0y_local)
            )

    # Accoudoirs
    if acc_left:
        if d["D1"]:
            polys["accoudoirs"].append([pts["Ay"],  pts["Ay2"],  pts["By2"],  pts["Dy2"],  pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"],  pts["By2"],  pts["By"],   pts["Ay_"]])
    if acc_right:
        if d["D5"] or d["D6"]:
            dy_top = pts.get("Dy3", pts.get("Dy4"))
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], dy_top, pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    polys["split_flags"]={"any":split_any}
    return polys

def compute_points_U1F_v4(tx, ty_left, tz_right, profondeur=DEPTH_STD,
                          dossier_left=True, dossier_bas=True, dossier_right=True,
                          acc_left=True, acc_right=True,
                          meridienne_side=None, meridienne_len=0):
    if meridienne_side == 'g' and acc_left:
        raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
    if meridienne_side == 'd' and acc_right:
        raise ValueError("Méridienne droite interdite avec accoudoir droit.")

    A, F0x, F0y = _common_offsets_u1f(profondeur, dossier_left, dossier_bas, dossier_right)
    F02x = tx - (10 if dossier_right else 0)

    pts={}
    pts["D0"]=(0,0); pts["D0x"]=(F0x,0); pts["D0y"]=(0,F0y); pts["F0"]=(F0x,F0y)

    # GAUCHE
    pts["Dy"]=(0, F0y+profondeur)
    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    top_y_L_dos  = top_y_L_full if meridienne_side!='g' else max(F0y+profondeur, top_y_L_full - meridienne_len)

    pts["Fy"]=(F0x, F0y+profondeur); pts["Fy2"]=(F0x+profondeur, F0y+profondeur)
    pts["By"]=(F0x, top_y_L_full);   pts["By2"]=(F0x+profondeur, top_y_L_full)
    pts["Dy2"]=(0, top_y_L_dos)
    pts["By_dL"]=(F0x, top_y_L_dos)
    pts["Ay"]=(0, ty_left); pts["Ay2"]=(F0x+profondeur, ty_left); pts["Ay_"]=(F0x, ty_left)

    # BAS + angle droite
    pts["Fx"]=(F0x+profondeur, F0y); pts["Fx2"]=(F0x+profondeur, F0y+profondeur)
    bx_x = F02x - (profondeur+20)
    pts["Bx"]=(bx_x, F0y); pts["Bx2"]=(bx_x, F0y+profondeur); pts["Dx"]=(bx_x, 0)

    # DROITE
    col_x = F02x - profondeur
    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    top_y_R_dos  = top_y_R_full if meridienne_side!='d' else max(F0y + (profondeur+20), top_y_R_full - meridienne_len)

    pts["Fy3"]=(col_x, F0y + (profondeur+20)); pts["Fy4"]=(F02x, F0y + (profondeur+20))
    pts["By3"]=(col_x, top_y_R_full); pts["By4"]=(F02x, top_y_R_full); pts["By4_d"]=(F02x, top_y_R_dos)
    pts["Ax"]=(col_x, tz_right); pts["Ax2"]=(tx, tz_right); pts["Ax_par"]=(F02x, tz_right)

    pts["D02x"]=(F02x, 0); pts["F02"]=(F02x, F0y)
    pts["D02"]=(tx, 0); pts["D02y"]=(tx, F0y)
    pts["Dy3"]=(tx, F0y + (profondeur+20)); pts["Dy4"]=(tx, top_y_R_dos)

    if not dossier_bas:
        pts["D0y"]=(0,0); pts["D02y"]=(tx,0)

    pts["By_cush"]  = (pts["By"][0],  min(pts["By"][1],  top_y_L_dos))
    pts["By4_cush"] = (pts["By4"][0], min(pts["By4"][1], top_y_R_dos))

    pts["_A"]=profondeur+20; pts["_ty_canvas"]=max(ty_left, tz_right)
    pts["_draw"]={
        "D1": bool(dossier_left), "D2": bool(dossier_left),
        "D3": bool(dossier_bas),  "D4": bool(dossier_bas),
        "D5": bool(dossier_right),"D6": bool(dossier_right),
    }
    pts["_acc"]={"L":acc_left, "R":acc_right}
    return pts

def build_polys_U1F_v4(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True, dossier_right=True,
                       acc_left=True, acc_right=True):
    polys={"angle": [], "banquettes": [], "dossiers": [], "accoudoirs": []}
    d=pts["_draw"]

    split_any=False
    for ban in (
        [pts["Fy"], pts["By"], pts["By2"], pts["Fy2"], pts["Fy"]],
        [pts["F0"], pts["Bx"], pts["Bx2"], pts["Fy"],  pts["F0"]],
        [pts["Fy4"], pts["By4"], pts["By3"], pts["Fy3"], pts["Fy4"]],
    ):
        pieces, split = _split_banquette_if_needed_U1F(ban)
        polys["banquettes"] += pieces
        split_any = split_any or split

    polys["angle"].append([pts["Bx"], pts["F02"], pts["Fy4"], pts["Fy3"], pts["Bx2"], pts["Bx"]])

    if d["D1"]:
        # D1 (gauche) — scinder selon la banquette gauche si nécessaire
        x0, x1 = 0, pts["F0"][0]
        y0 = pts["Fy"][1]            # hauteur de départ de la banquette gauche
        y1 = pts["By_dL"][1]         # hauteur maximale du dossier gauche (tenue compte méridienne)
        seat_y0, seat_y1 = pts["Fy"][1], pts["By"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)
    if d["D2"]:
        polys["dossiers"].append([pts["D0x"], pts["D0"], pts["Dy"], pts["Fy"], pts["D0x"]])
    # --- Dossiers bas : 1 ou 2 rectangles selon scission de l'assise ---
    if d["D3"] or d["D4"]:
        F0x, F0y = pts["F0"]
        xL_total = F0x
        xR_total = pts["F02"][0]
        # largeur de la banquette centrale (F0 → Bx), comme dans la scission de l'assise
        Lb = abs(pts["Bx"][0] - pts["F0"][0])
        if Lb > SPLIT_THRESHOLD:
            # milieu identique à celui utilisé pour la scission de l'assise : médiane entre F0.x et Bx.x
            mid_x = _split_mid_int(pts["F0"][0], pts["Bx"][0])
            polys["dossiers"] += [
                _rectU(xL_total, 0, mid_x,  F0y),
                _rectU(mid_x,    0, xR_total, F0y),
            ]
        else:
            polys["dossiers"].append(_rectU(xL_total, 0, xR_total, F0y))
    if d["D5"]:
        polys["dossiers"].append([pts["D02x"], pts["Fy4"], pts["Dy3"], pts["D02"], pts["D02x"]])
    if d["D6"]:
        # D6 (droit haut) — scinder selon la banquette droite si nécessaire
        x0, x1 = pts["D02x"][0], tx
        # Le dossier droit démarre à Fy4.y (banquette droite pour v4)
        y0 = pts["Fy4"][1]
        y1 = pts["By4_d"][1]
        seat_y0, seat_y1 = pts["Fy4"][1], pts["By4"][1]
        polys["dossiers"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)

    # U1F v4 — délimitation verticale Dx2–Bx (jonction dossiers 4 et 5)
    if dossier_bas:
        F0y_local = pts["F0"][1]
        seam = max(0.2, min(0.8, F0y_local * 0.02))
        x_right_candidates = []
        if "Dx2" in pts:
            x_right_candidates.append(pts["Dx2"][0])
        if "Bx" in pts:
            x_right_candidates.append(pts["Bx"][0])
        if x_right_candidates:
            if len(x_right_candidates) > 1:
                xr = 0.5 * (x_right_candidates[0] + x_right_candidates[1])
            else:
                xr = x_right_candidates[0]
            polys["dossiers"].append(_rectU(xr - seam/2, 0, xr + seam/2, F0y_local))

    if acc_left:
        if d["D1"]:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_"]])

    if acc_right:
        has_right = (d["D5"] or d["D6"])
        if has_right:
            dy_top = pts.get("Dy4", pts.get("Dy3"))
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], dy_top, pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    polys["split_flags"]={"any":split_any}
    return polys

# --- rendu commun + wrappers (U1F) ---
def _render_common_U1F(variant, tx, ty_left, tz_right, profondeur,
                       dossier_left, dossier_bas, dossier_right,
                       acc_left, acc_right,
                       meridienne_side, meridienne_len,
                       coussins, traversins, couleurs, window_title):
    comp = {"v1":compute_points_U1F_v1, "v2":compute_points_U1F_v2,
            "v3":compute_points_U1F_v3, "v4":compute_points_U1F_v4}[variant]
    build= {"v1":build_polys_U1F_v1,   "v2":build_polys_U1F_v2,
            "v3":build_polys_U1F_v3,   "v4":build_polys_U1F_v4}[variant]

    trv = _parse_traversins_spec(traversins, allowed={"g","d"})
    legend_items = _resolve_and_apply_colors(couleurs)

    pts = comp(tx, ty_left, tz_right, profondeur,
               dossier_left, dossier_bas, dossier_right,
               acc_left, acc_right,
               meridienne_side, meridienne_len)
    polys = build(pts, tx, ty_left, tz_right, profondeur,
                  dossier_left, dossier_bas, dossier_right,
                  acc_left, acc_right)
    _assert_banquettes_max_250(polys)

    ty_canvas = max(ty_left, tz_right)
    screen = turtle.Screen(); screen.setup(WIN_W, WIN_H)
    screen.title(f"U1F {variant} — {window_title} — tx={tx} / ty(left)={ty_left} / tz(right)={tz_right} — prof={profondeur}")
    t = turtle.Turtle(visible=False); t.speed(0); screen.tracer(False)
    tr = WorldToScreen(tx, ty_canvas, WIN_W, WIN_H, PAD_PX, ZOOM)

    # (Quadrillage et repères supprimés)

    for p in polys["dossiers"]:
        xs=[pp[0] for pp in p]; ys=[pp[1] for pp in p]
        if (max(xs)-min(xs) > 1e-9) and (max(ys)-min(ys) > 1e-9):
            draw_polygon_cm(t, tr, p, fill=COLOR_DOSSIER)
    for p in polys["banquettes"]: draw_polygon_cm(t, tr, p, fill=COLOR_ASSISE)
    for p in polys["accoudoirs"]: draw_polygon_cm(t, tr, p, fill=COLOR_ACC)
    for p in polys["angle"]:      draw_polygon_cm(t, tr, p, fill=COLOR_ASSISE)

    # Traversins + comptage
    n_traversins = _draw_traversins_U_side_F02(t, tr, pts, profondeur, trv)

    draw_double_arrow_vertical_cm(t, tr, -25,   0, ty_left,   f"{ty_left} cm")
    draw_double_arrow_vertical_cm(t, tr,  tx+25,0, tz_right,   f"{tz_right} cm")
    draw_double_arrow_horizontal_cm(t, tr, -25, 0, tx,   f"{tx} cm")

    A = pts["_A"]
    if polys["angle"]:
        # Dimensions d’angle sur deux lignes : première ligne sans unité suivie d'un « x », deuxième ligne avec « cm »
        label_poly(t, tr, polys["angle"][0], f"{A}x\n{A} cm")
    banquette_sizes = []
    for poly in polys["banquettes"]:
        L, P = banquette_dims(poly)
        banquette_sizes.append((L, P))
        # Afficher la longueur sans unité suivie d'un « x », et la profondeur avec « cm »
        text = f"{L}x\n{P} cm"
        xs = [pp[0] for pp in poly]
        ys = [pp[1] for pp in poly]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # Décaler horizontalement si la banquette est plus haute que large
        if bb_h >= bb_w:
            # Centre X de la banquette
            cx = sum(xs) / len(xs)
            # Réduire les offsets : 3 cm en moins sur les branches verticales
            # Branche gauche : CUSHION_DEPTH+7 (22 cm). Branche droite : -(CUSHION_DEPTH-8) (-7 cm).
            dx = (CUSHION_DEPTH + 7) if cx < tx / 2.0 else -(CUSHION_DEPTH - 8)
            label_poly_offset_cm(t, tr, poly, text, dx_cm=dx, dy_cm=0.0)
        else:
            label_poly(t, tr, poly, text)
    for p in polys["dossiers"]:
        xs=[pp[0] for pp in p]; ys=[pp[1] for pp in p]
        if (max(xs)-min(xs) > 1e-9) and (max(ys)-min(ys) > 1e-9):
            label_poly(t,tr,p,"10")
    for p in polys["accoudoirs"]:
        xs=[pp[0] for pp in p]; ys=[pp[1] for pp in p]
        if (max(xs)-min(xs) > 1e-9) and (max(ys)-min(ys) > 1e-9):
            label_poly(t,tr,p,"15")

    # ===== COUSSINS =====
    spec = _parse_coussins_spec(coussins)
    if spec["mode"] == "auto":
        size = _choose_cushion_size_auto_U1F(pts, traversins=trv)
        nb_coussins = _draw_coussins_U1F(t, tr, pts, size, traversins=trv)
        total_line = f"{coussins} → {nb_coussins} × {size} cm"
    elif spec["mode"] == "fixed":
        size = int(spec["fixed"])
        nb_coussins = _draw_coussins_U1F(t, tr, pts, size, traversins=trv)
        total_line = f"{coussins} → {nb_coussins} × {size} cm"
    else:
        best = _optimize_valise_U1F(pts, spec["range"], spec["same"], traversins=trv)
        if not best:
            raise ValueError("Aucune configuration valise valide pour U1F.")
        sizes = best["sizes"]; shiftL, shiftR = best["shifts"]
        nb_coussins = _draw_U1F_with_sizes(t, tr, pts, sizes, shiftL, shiftR, traversins=trv)
        sb, sg, sd = sizes["bas"], sizes["gauche"], sizes["droite"]
        total_line = _format_valise_counts_console(
            {"bas": sb, "gauche": sg, "droite": sd},
            best.get("counts", best.get("eval", {}).get("counts")),
            nb_coussins,
        )

    # Titre + légende (U → haut-centre)
    draw_title_center(t, tr, tx, ty_canvas, "Canapé en U avec un angle")
    draw_legend(t, tr, tx, ty_canvas, items=legend_items, pos="top-center")

    screen.tracer(True); t.hideturtle()

    add_split = int(polys.get("split_flags",{}).get("any",False))
    print(f"=== Rapport U1F {variant} ===")
    print(f"Dimensions : tx={tx} / ty(left)={ty_left} / tz(right)={tz_right} — profondeur={profondeur} (A={A})")
    print(f"Banquettes : {len(polys['banquettes'])} → {banquette_sizes}")
    # Comptage pondéré des dossiers : <=110cm → 0.5, >110cm → 1
    dossiers_count = _compute_dossiers_count(polys)
    dossiers_str = f"{int(dossiers_count)}" if abs(dossiers_count - int(dossiers_count)) < 1e-9 else f"{dossiers_count}"
    print(f"Dossiers : {dossiers_str} (+{add_split} via scission) | Accoudoirs : {len(polys['accoudoirs'])}")
    print(f"Banquettes d’angle : 1")
    print(f"Angles : 1 × {A}×{A} cm")
    print(f"Traversins : {n_traversins} × 70x30")
    print(f"Coussins : {total_line}")
    turtle.done()

def _dry_polys_for_U1F_variant(tx, ty_left, tz_right, profondeur,
                               dossier_left, dossier_bas, dossier_right,
                               acc_left, acc_right,
                               meridienne_side, meridienne_len,
                               variant):
    """
    Calcule (pts, polys) pour une variante U1F donnée sans rendre le dessin.
    Utile pour comparer plusieurs variantes et choisir celle qui convient.
    """
    comp = {
        "v1": compute_points_U1F_v1,
        "v2": compute_points_U1F_v2,
        "v3": compute_points_U1F_v3,
        "v4": compute_points_U1F_v4,
    }[variant]
    build = {
        "v1": build_polys_U1F_v1,
        "v2": build_polys_U1F_v2,
        "v3": build_polys_U1F_v3,
        "v4": build_polys_U1F_v4,
    }[variant]
    pts = comp(
        tx, ty_left, tz_right, profondeur,
        dossier_left, dossier_bas, dossier_right,
        acc_left, acc_right,
        meridienne_side, meridienne_len,
    )
    polys = build(
        pts, tx, ty_left, tz_right, profondeur,
        dossier_left, dossier_bas, dossier_right,
        acc_left, acc_right,
    )
    return pts, polys

def render_U1F(tx, ty_left, tz_right, profondeur=DEPTH_STD,
               dossier_left=True, dossier_bas=True, dossier_right=True,
               acc_left=True, acc_right=True,
               meridienne_side=None, meridienne_len=0,
               coussins="auto",
               variant="auto",
               traversins=None,
               couleurs=None,
               window_title="U1F — auto"):
    """
    Rendu générique pour les U1F. Permet de forcer une variante (v1/v2/v3/v4)
    ou de laisser le choix automatique (auto) entre les variantes les plus simples (v1 et v3).
    """
    v_norm = (variant or "auto").lower()
    # Forcer explicitement une variante
    if v_norm in {"v1", "v2", "v3", "v4"}:
        if v_norm == "v1":
            return render_U1F_v1(
                tx=tx, ty_left=ty_left, tz_right=tz_right, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas, dossier_right=dossier_right,
                acc_left=acc_left, acc_right=acc_right,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, traversins=traversins, couleurs=couleurs,
                window_title=window_title,
            )
        if v_norm == "v2":
            return render_U1F_v2(
                tx=tx, ty_left=ty_left, tz_right=tz_right, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas, dossier_right=dossier_right,
                acc_left=acc_left, acc_right=acc_right,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, traversins=traversins, couleurs=couleurs,
                window_title=window_title,
            )
        if v_norm == "v3":
            return render_U1F_v3(
                tx=tx, ty_left=ty_left, tz_right=tz_right, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas, dossier_right=dossier_right,
                acc_left=acc_left, acc_right=acc_right,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, traversins=traversins, couleurs=couleurs,
                window_title=window_title,
            )
        if v_norm == "v4":
            return render_U1F_v4(
                tx=tx, ty_left=ty_left, tz_right=tz_right, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas, dossier_right=dossier_right,
                acc_left=acc_left, acc_right=acc_right,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, traversins=traversins, couleurs=couleurs,
                window_title=window_title,
            )
    # Mode automatique: choisir la variante la plus simple entre v1 et v3
    candidates = ("v1", "v3")
    best_variant = None
    best_nb_ban = float("inf")
    best_scissions = float("inf")
    def _count_scissions(polys):
        base = 3
        nb = len(polys.get("banquettes", []))
        return max(0, nb - base)
    for var in candidates:
        try:
            _pts, _polys = _dry_polys_for_U1F_variant(
                tx, ty_left, tz_right, profondeur,
                dossier_left, dossier_bas, dossier_right,
                acc_left, acc_right,
                meridienne_side, meridienne_len,
                var,
            )
        except ValueError:
            continue
        nb_ban = len(_polys.get("banquettes", []))
        sci = _count_scissions(_polys)
        if (nb_ban < best_nb_ban) or (nb_ban == best_nb_ban and sci < best_scissions):
            best_variant = var
            best_nb_ban = nb_ban
            best_scissions = sci
    if best_variant is None:
        best_variant = "v1"
    return _render_common_U1F(
        best_variant,
        tx, ty_left, tz_right, profondeur,
        dossier_left, dossier_bas, dossier_right,
        acc_left, acc_right,
        meridienne_side, meridienne_len,
        coussins, traversins, couleurs,
        window_title,
    )

def render_U1F_v1(*args, **kwargs):
    if "traversins" not in kwargs: kwargs["traversins"]=None
    if "couleurs" not in kwargs: kwargs["couleurs"]=None
    # compat. anciens appels : ty/tz -> ty_left/tz_right
    if "ty_left" not in kwargs and "ty" in kwargs: kwargs["ty_left"] = kwargs.pop("ty")
    if "tz_right" not in kwargs and "tz" in kwargs: kwargs["tz_right"] = kwargs.pop("tz")
    _render_common_U1F("v1", *args, **kwargs)
def render_U1F_v2(*args, **kwargs):
    if "traversins" not in kwargs: kwargs["traversins"]=None
    if "couleurs" not in kwargs: kwargs["couleurs"]=None
    if "ty_left" not in kwargs and "ty" in kwargs: kwargs["ty_left"] = kwargs.pop("ty")
    if "tz_right" not in kwargs and "tz" in kwargs: kwargs["tz_right"] = kwargs.pop("tz")
    _render_common_U1F("v2", *args, **kwargs)
def render_U1F_v3(*args, **kwargs):
    if "traversins" not in kwargs: kwargs["traversins"]=None
    if "couleurs" not in kwargs: kwargs["couleurs"]=None
    if "ty_left" not in kwargs and "ty" in kwargs: kwargs["ty_left"] = kwargs.pop("ty")
    if "tz_right" not in kwargs and "tz" in kwargs: kwargs["tz_right"] = kwargs.pop("tz")
    _render_common_U1F("v3", *args, **kwargs)
def render_U1F_v4(*args, **kwargs):
    if "traversins" not in kwargs: kwargs["traversins"]=None
    if "couleurs" not in kwargs: kwargs["couleurs"]=None
    if "ty_left" not in kwargs and "ty" in kwargs: kwargs["ty_left"] = kwargs.pop("ty")
    if "tz_right" not in kwargs and "tz" in kwargs: kwargs["tz_right"] = kwargs.pop("tz")
    _render_common_U1F("v4", *args, **kwargs)

# =====================================================================
# ======================  L (no fromage) v1 + v2  =====================
# =====================================================================
def compute_points_LNF_v2(tx, ty, profondeur=DEPTH_STD,
                          dossier_left=True, dossier_bas=True,
                          acc_left=True, acc_bas=True,
                          meridienne_side=None, meridienne_len=0):
    prof = profondeur; pts = {}
    if dossier_left and dossier_bas:         F0x, F0y = 10, 10; D0x0=(10,0); D0y0=(0,10)
    elif (not dossier_left) and dossier_bas: F0x, F0y = 0, 10;  D0x0=(0,0);  D0y0=(0,10)
    elif dossier_left and (not dossier_bas): F0x, F0y = 10, 0;  D0x0=(10,0); D0y0=(0,0)
    else:                                    F0x, F0y = 0, 0;   D0x0=(0,0);  D0y0=(0,0)

    pts["D0"]=(0,0); pts["D0x"]=D0x0; pts["D0y"]=D0y0; pts["F0"]=(F0x,F0y)

    top_y = ty - (ACCOUDOIR_THICK if acc_left else 0)
    pts["Dy"]  =(0, F0y+prof); pts["Dy2"]=(0, top_y); pts["Ay"]=(0, ty)
    pts["Fy"]  =(F0x, F0y+prof); pts["By"]=(F0x, top_y)
    pts["Ay2"] =(F0x+prof, ty); pts["By2"]=(F0x+prof, top_y); pts["Ay_par"]=(F0x, ty)

    stop_x = tx - (ACCOUDOIR_THICK if acc_bas else 0)
    pts["Dx"]=(stop_x,0); pts["Bx"]=(stop_x,F0y); pts["Bx2"]=(stop_x,F0y+prof)
    pts["Ax"]=(tx,0); pts["Ax2"]=(tx,F0y+prof); pts["Ax_par"]=(tx,F0y)

    if meridienne_side=='g' and meridienne_len>0:
        mer_y=max(pts["Fy"][1], top_y - meridienne_len); mer_y=min(mer_y, top_y)
        pts["By_mer"]=(pts["By"][0],mer_y); pts["By2_mer"]=(pts["By2"][0],mer_y); pts["Dy2"]=(0,mer_y)
    if meridienne_side=='b' and meridienne_len>0:
        mer_x=min(stop_x, tx - meridienne_len)
        pts["Bx_mer"]=(mer_x, pts["Bx"][1]); pts["Bx2_mer"]=(mer_x, pts["Bx2"][1]); pts["Dx_mer"]=(mer_x,0)

    pts["_tx"], pts["_ty"] = tx, ty
    return pts

def build_polys_LNF_v2(pts, tx, ty, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True,
                       acc_left=True, acc_bas=True,
                       meridienne_side=None, meridienne_len=0):
    polys={"banquettes":[],"dossiers":[],"accoudoirs":[]}

    Fy=(pts["Fy"][0], pts["Fy"][1]); Fy2=(pts["Fy"][0]+profondeur, pts["Fy"][1])
    By=pts.get("By"); By2=pts.get("By2")
    ban_g=[Fy, By, By2, Fy2, Fy]
    split_left=False; mid_y_left=None
    Lg = abs(By2[1] - Fy2[1])
    if Lg > SPLIT_THRESHOLD:
        split_left=True; mid_y_left=_split_mid_int(Fy2[1], By2[1])
        low  = [(Fy[0],Fy[1]),(Fy2[0],Fy2[1]),(Fy2[0],mid_y_left),(Fy[0],mid_y_left),(Fy[0],Fy[1])]
        high = [(Fy[0],mid_y_left),(Fy2[0],mid_y_left),(By2[0],By2[1]),(By[0],By[1]),(Fy[0],mid_y_left)]
        polys["banquettes"] += [low, high]
    else:
        polys["banquettes"].append(ban_g)

    F0=pts["F0"]; Bx=pts["Bx"]; Bx2=pts["Bx2"]
    ban_b=[F0, Bx, Bx2, pts["Fy"], F0]
    split_bas=False; mid_x_bas=None
    Lb = abs(Bx2[0] - pts["Fy"][0])
    if Lb > SPLIT_THRESHOLD:
        split_bas=True; mid_x_bas=_split_mid_int(pts["Fy"][0], Bx2[0])
        left  = [(F0[0],F0[1]),(mid_x_bas,F0[1]),(mid_x_bas,pts["Fy"][1]),(pts["Fy"][0],pts["Fy"][1]),(F0[0],F0[1])]
        right = [(mid_x_bas,F0[1]),(Bx[0],Bx[1]),(Bx2[0],Bx2[1]),(mid_x_bas,pts["Fy"][1]),(mid_x_bas,F0[1])]
        polys["banquettes"] += [left, right]
    else:
        polys["banquettes"].append(ban_b)

    if dossier_left:
        if split_left:
            F0x=pts["F0"][0]; y0=pts["Dy"][1]; yTop=pts.get("By_mer", pts["By"])[1]
            d1b=[(0,y0),(F0x,y0),(F0x,mid_y_left),(0,mid_y_left),(0,y0)]
            d1h=[(0,mid_y_left),(F0x,mid_y_left),(F0x,yTop),(0,yTop),(0,mid_y_left)]
            polys["dossiers"] += [d1b, d1h]
        else:
            By_use = pts.get("By_mer", pts["By"])
            polys["dossiers"].append([pts["Dy2"], By_use, pts["Fy"], pts["Dy"], pts["Dy2"]])
    if dossier_left:
        polys["dossiers"].append([pts["D0x"], pts["D0"], pts["Dy"], pts["Fy"], pts["D0x"]])
    if dossier_bas:
        Bx_use = pts.get("Bx_mer", pts["Bx"]); Dx_use = pts.get("Dx_mer", pts["Dx"])
        if split_bas:
            yTop=pts["F0"][1]
            d3g=[(mid_x_bas,0),(pts["D0x"][0],0),(pts["D0x"][0],yTop),(mid_x_bas,yTop),(mid_x_bas,0)]
            d3d=[(Dx_use[0],0),(mid_x_bas,0),(mid_x_bas,yTop),(Bx_use[0],yTop),(Dx_use[0],0)]
            polys["dossiers"] += [d3g, d3d]
        else:
            polys["dossiers"].append([Dx_use, pts["D0x"], pts["F0"], Bx_use, Dx_use])

    if acc_left:
        if dossier_left:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["By"], pts["Ay_par"], pts["Ay2"], pts["By2"], pts["By"]])
    if acc_bas:
        if dossier_bas:
            polys["accoudoirs"].append([pts["Dx"], pts["Ax"], pts["Ax2"], pts["Bx2"], pts["Dx"]])
        else:
            polys["accoudoirs"].append([pts["Bx"], pts["Ax_par"], pts["Ax2"], pts["Bx2"], pts["Bx"]])

    polys["split_flags"]={"left":split_left,"bottom":split_bas}
    return polys

def compute_points_LNF_v1(tx, ty, profondeur=DEPTH_STD,
                          dossier_left=True, dossier_bas=True,
                          acc_left=True, acc_bas=True,
                          meridienne_side=None, meridienne_len=0):
    prof=profondeur; pts={}
    if dossier_left and dossier_bas:         F0x,F0y=10,10; D0x0=(10,0); D0y0=(0,10)
    elif (not dossier_left) and dossier_bas: F0x,F0y=0,10;  D0x0=(0,0);  D0y0=(0,10)
    elif dossier_left and (not dossier_bas): F0x,F0y=10,0;  D0x0=(10,0); D0y0=(0,0)
    else:                                    F0x,F0y=0,0;   D0x0=(0,0);  D0y0=(0,0)

    pts["D0"]=(0,0); pts["D0x"]=D0x0; pts["D0y"]=D0y0; pts["F0"]=(F0x,F0y)
    top_y = ty - (ACCOUDOIR_THICK if acc_left else 0)
    pts["Dy2"]=(0, top_y); pts["Ay"] =(0, ty); pts["By"] =(F0x, top_y)
    pts["Ay2"]=(F0x+prof, ty); pts["By2"]=(F0x+prof, top_y)

    stop_x = tx - (ACCOUDOIR_THICK if acc_bas else 0)
    pts["Dy"] =(0, F0y+prof)
    pts["Fx"] =(F0x+prof, F0y); pts["Fx2"]=(F0x+prof, F0y+prof)
    pts["Bx"] =(stop_x, F0y);   pts["Bx2"]=(stop_x, F0y+prof)
    pts["Dx"] =(F0x+prof, 0);   pts["DxR"]=(stop_x, 0)
    pts["Ax"] =(tx, 0); pts["Ax2"]=(tx, F0y+prof)
    pts["Ay_par"]=(F0x, ty); pts["Ax_par"]=(tx, F0y)

    if meridienne_side=='g' and meridienne_len>0:
        mer_y=max(F0y, top_y - meridienne_len); mer_y=min(mer_y, top_y)
        pts["By_mer"]=(pts["By"][0],mer_y); pts["By2_mer"]=(pts["By2"][0],mer_y); pts["Dy2"]=(0,mer_y)
    if meridienne_side=='b' and meridienne_len>0:
        mer_x=min(stop_x, tx - meridienne_len)
        pts["Bx_mer"]=(mer_x, pts["Bx"][1]); pts["Bx2_mer"]=(mer_x, pts["Bx2"][1]); pts["DxR_mer"]=(mer_x,0)
    pts["_tx"], pts["_ty"]=tx,ty
    return pts

def build_polys_LNF_v1(pts, tx, ty, profondeur=DEPTH_STD,
                       dossier_left=True, dossier_bas=True,
                       acc_left=True, acc_bas=True,
                       meridienne_side=None, meridienne_len=0):
    polys={"banquettes":[], "dossiers":[], "accoudoirs":[]}

    F0=pts["F0"]; Fx=pts["Fx"]; By=pts.get("By"); By2=pts.get("By2")
    ban_g=[F0, By, By2, Fx, F0]
    split_left=False; mid_y_left=None
    # IMPORTANT : ne pas tronquer la banquette par la méridienne.
    # La méridienne se matérialise par l'absence de dossier au-dessus,
    # l'assise doit rester à la hauteur "By/By2" (pleine hauteur).
    top_y = By2[1]; base_y = F0[1]
    Lg = abs(top_y - base_y)
    if Lg > SPLIT_THRESHOLD:
        split_left=True; mid_y_left=_split_mid_int(base_y, top_y)
        lower=[(F0[0],base_y),(Fx[0],base_y),(Fx[0],mid_y_left),(F0[0],mid_y_left),(F0[0],base_y)]
        upper=[(F0[0],mid_y_left),(Fx[0],mid_y_left),(By2[0],top_y),(By[0],top_y),(F0[0],mid_y_left)]
        polys["banquettes"] += [lower, upper]
    else:
        polys["banquettes"].append(ban_g)

    Bx=pts["Bx"]; Bx2=pts["Bx2"]; Fx2=pts["Fx2"]
    ban_b=[pts["Fx"], Bx, Bx2, Fx2, pts["Fx"]]
    split_bas=False; mid_x_bas=None
    Lb = abs(Bx2[0] - pts["Fx"][0])
    if Lb > SPLIT_THRESHOLD:
        split_bas=True; mid_x_bas=_split_mid_int(pts["Fx"][0], Bx2[0])
        left =[ (pts["Fx"][0], pts["Fx"][1]), (mid_x_bas, pts["Fx"][1]),
                (mid_x_bas, Fx2[1]), (Fx2[0], Fx2[1]), (pts["Fx"][0], pts["Fx"][1]) ]
        right=[ (mid_x_bas, pts["Fx"][1]), (Bx[0],Bx[1]), (Bx2[0],Bx2[1]),
                (mid_x_bas, Fx2[1]), (mid_x_bas, pts["Fx"][1]) ]
        polys["banquettes"] += [left, right]
    else:
        polys["banquettes"].append(ban_b)

    if dossier_left:
        By_use = pts.get("By_mer", pts["By"])
        if split_left:
            x0=0; x1=pts["D0x"][0]; y_base=0; y_top=By_use[1]; y_mid=mid_y_left
            d1_bas=[(x0,y_base),(x1,y_base),(x1,y_mid),(x0,y_mid),(x0,y_base)]
            d1_haut=[(x0,y_mid),(x1,y_mid),(x1,y_top),(x0,y_top),(x0,y_mid)]
            polys["dossiers"] += [d1_bas, d1_haut]
        else:
            polys["dossiers"].append([pts["D0"], pts["Dy2"], By_use, pts["D0x"], pts["D0"]])
    if dossier_left:
        polys["dossiers"].append([pts["D0x"], pts["Dx"], pts["Fx"], pts["F0"], pts["D0x"]])
    if dossier_bas:
        DxR_use = pts.get("DxR_mer", pts["DxR"]); Bx_use = pts.get("Bx_mer", pts["Bx"])
        if split_bas:
            yTop = pts["F0"][1]
            d3_g = [(mid_x_bas,0),(pts["Dx"][0],0),(pts["Dx"][0],yTop),(mid_x_bas,yTop),(mid_x_bas,0)]
            d3_d = [(DxR_use[0],0),(mid_x_bas,0),(mid_x_bas,yTop),(Bx_use[0],yTop),(DxR_use[0],0)]
            polys["dossiers"] += [d3_g, d3_d]
        else:
            polys["dossiers"].append([pts["Dx"], DxR_use, Bx_use, pts["Fx"], pts["Dx"]])
        # --- retour gauche si aucun dossier gauche (False ou None) et pas de méridienne bas
        if (dossier_left is None or dossier_left is False) and (meridienne_side not in ('b','B','bas','bottom')):
            # Ajoute un demi-dossier pour fermer la zone entre D0x/F0 et Dx/Fx
            polys["dossiers"].append([pts["D0x"], pts["Dx"], pts["Fx"], pts["F0"], pts["D0x"]])

    if acc_left:
        if dossier_left:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_par"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_par"]])
    if acc_bas:
        if dossier_bas:
            polys["accoudoirs"].append([pts["DxR"], pts["Ax"], pts["Ax2"], pts["Bx2"], pts["DxR"]])
        else:
            polys["accoudoirs"].append([pts["Bx"], pts["Ax_par"], pts["Ax2"], pts["Bx2"], pts["Bx"]])

    polys["split_flags"]={"left":split_left,"bottom":split_bas}
    return polys

def _choose_cushion_size_auto_L(pts, traversins=None):
    """
    Choix automatique de la taille de coussins (65/80/90) pour un L.
    Critère : choisir le standard qui permet de couvrir la plus grande
    surface de canapé (≈ nb_coussins * taille), en tenant compte des
    traversins éventuels.
    """
    F0x, F0y = pts["F0"]

    # Même logique de fin de segment que partout ailleurs (LNF v1/v2)
    x_end = pts.get("Bx_mer", pts.get("Bx", (F0x, 0)))[0]
    y_end = pts.get("By_mer", pts.get("By", (F0x, F0y)))[1]

    # On retire l’épaisseur des traversins sur les lignes concernées
    if traversins:
        if "b" in traversins:
            x_end -= TRAVERSIN_THK
        if "g" in traversins:
            y_end -= TRAVERSIN_THK

    def count_bottom(x_start, size):
        if x_end <= x_start or size <= 0:
            return 0
        return max(0, int((x_end - x_start) // size))

    def count_left(y_start, size):
        if y_end <= y_start or size <= 0:
            return 0
        return max(0, int((y_end - y_start) // size))

    best_size = 65
    # score = (surface_couverte, -déchet_total, taille)
    best_score = (-1, 0.0, 0)

    for size in (65, 80, 90):
        # Disposition A : bas collé au coin, gauche décalé vers le haut
        cbA = count_bottom(F0x, size)
        clA = count_left(F0y + CUSHION_DEPTH, size)
        nA = cbA + clA
        wasteA = 0.0
        if x_end > F0x:
            wasteA += (x_end - F0x) % size
        if y_end > (F0y + CUSHION_DEPTH):
            wasteA += (y_end - (F0y + CUSHION_DEPTH)) % size
        coverA = nA * size  # proportionnel à la surface (CUSHION_DEPTH est constant)

        # Disposition B : gauche collé au coin, bas décalé vers la droite
        cbB = count_bottom(F0x + CUSHION_DEPTH, size)
        clB = count_left(F0y, size)
        nB = cbB + clB
        wasteB = 0.0
        if x_end > (F0x + CUSHION_DEPTH):
            wasteB += (x_end - (F0x + CUSHION_DEPTH)) % size
        if y_end > F0y:
            wasteB += (y_end - F0y) % size
        coverB = nB * size

        # Pour cette taille, garder la disposition qui couvre le plus,
        # puis qui génère le moins de déchet.
        if (coverB, -wasteB) > (coverA, -wasteA):
            cover, waste = coverB, wasteB
        else:
            cover, waste = coverA, wasteA

        # Score global pour cette taille :
        # 1. plus de surface couverte
        # 2. moins de déchet
        # 3. taille plus grande en dernier recours
        score = (cover, -waste, size)
        if score > best_score:
            best_score = score
            best_size = size

    return best_size

def draw_coussins_L_optimized(t, tr, pts, coussins, traversins=None):
    if isinstance(coussins, str) and coussins.strip().lower()=="auto":
        size = _choose_cushion_size_auto_L(pts, traversins=traversins)
    else:
        size = int(coussins)

    F0x, F0y = pts["F0"]
    x_end = pts.get("Bx_mer", pts["Bx"])[0]
    y_end = pts.get("By_mer", pts["By"])[1]
    if traversins:
        if "b" in traversins: x_end -= TRAVERSIN_THK
        if "g" in traversins: y_end -= TRAVERSIN_THK

    def count_bottom(x_start): return max(0, int((x_end - x_start)//size))
    def count_left(y_start):   return max(0, int((y_end - y_start)//size))

    nA = count_bottom(F0x) + count_left(F0y + CUSHION_DEPTH)  # bas collé
    nB = count_bottom(F0x + CUSHION_DEPTH) + count_left(F0y)  # bas décalé

    def draw_bottom(x_start):
        cnt=0; y=F0y; x_cur=x_start
        while x_cur + size <= x_end + 1e-6:
            poly=[(x_cur,y),(x_cur+size,y),(x_cur+size,y+CUSHION_DEPTH),(x_cur,y+CUSHION_DEPTH),(x_cur,y)]
            draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
            label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
            x_cur += size; cnt += 1
        return cnt
    def draw_left(y_start):
        cnt=0; x=F0x; y_cur=y_start
        while y_cur + size <= y_end + 1e-6:
            poly=[(x,y_cur),(x+CUSHION_DEPTH,y_cur),(x+CUSHION_DEPTH,y_cur+size),(x,y_cur+size),(x,y_cur)]
            draw_polygon_cm(t,tr,poly,fill=COLOR_CUSHION,outline=COLOR_CONTOUR,width=1)
            label_poly(t,tr,poly,f"{size}",font=FONT_CUSHION)
            y_cur += size; cnt += 1
        return cnt

    # tie-break : max coussins, puis déchet minimal
    wasteA = (max(0, x_end-F0x)%size) + (max(0, y_end-(F0y+CUSHION_DEPTH))%size)
    wasteB = (max(0, x_end-(F0x+CUSHION_DEPTH))%size) + (max(0, y_end-F0y)%size)
    if (nB, -wasteB) > (nA, -wasteA):
        cb = draw_bottom(F0x + CUSHION_DEPTH); cl = draw_left(F0y)
        return cb + cl, size
    else:
        cb = draw_bottom(F0x); cl = draw_left(F0y + CUSHION_DEPTH)
        return cb + cl, size

def _render_common_L(tx, ty, pts, polys, coussins, window_title,
                     profondeur, dossier_left, dossier_bas, meridienne_side, meridienne_len,
                     traversins=None, couleurs=None):
    _assert_banquettes_max_250(polys)

    trv = _parse_traversins_spec(traversins, allowed={"g","b"})
    legend_items = _resolve_and_apply_colors(couleurs)

    screen = turtle.Screen(); screen.setup(WIN_W,WIN_H)
    screen.title(f"{window_title} — {tx}×{ty} — prof={profondeur} — méridienne {meridienne_side or '-'}={meridienne_len} — coussins={coussins}")
    t = turtle.Turtle(visible=False); t.speed(0); screen.tracer(False)
    tr = WorldToScreen(tx, ty, WIN_W, WIN_H, PAD_PX, ZOOM)

    # (Quadrillage et repères supprimés)

    for p in polys["dossiers"]:   draw_polygon_cm(t,tr,p,fill=COLOR_DOSSIER)
    for p in polys["banquettes"]: draw_polygon_cm(t,tr,p,fill=COLOR_ASSISE)
    for p in polys["accoudoirs"]: draw_polygon_cm(t,tr,p,fill=COLOR_ACC)

    # Traversins + comptage
    n_traversins = _draw_traversins_L_like(t, tr, pts, profondeur, trv)

    draw_double_arrow_vertical_cm(t,tr,-25,0,ty,f"{ty} cm")
    draw_double_arrow_horizontal_cm(t,tr,-25,0,tx,f"{tx} cm")

    # Banquettes : afficher les dimensions sur deux lignes. Décaler légèrement lorsque la banquette est verticale.
    banquette_sizes = []
    for poly in polys["banquettes"]:
        L, P = banquette_dims(poly)
        banquette_sizes.append((L, P))
        # Afficher la longueur sans unité suivie d'un « x » puis la profondeur avec « cm »
        text = f"{L}x\n{P} cm"
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # Décaler horizontalement pour éloigner le texte des coussins lorsque la banquette est plus haute que large
        # Réduction de 3 cm : offset plus faible
        if bb_h >= bb_w:
            label_poly_offset_cm(t, tr, poly, text, dx_cm=CUSHION_DEPTH + 7, dy_cm=0.0)
        else:
            label_poly(t, tr, poly, text)

    for p in polys["dossiers"]:   label_poly(t,tr,p,"10")
    for p in polys["accoudoirs"]: label_poly(t,tr,p,"15")

    # ===== COUSSINS =====
    spec = _parse_coussins_spec(coussins)
    if spec["mode"] == "auto":
        cushions_count, chosen_size = draw_coussins_L_optimized(t,tr,pts,"auto", traversins=trv)
        total_line = f"{coussins} → {cushions_count} × {chosen_size} cm"
    elif spec["mode"] == "fixed":
        cushions_count, chosen_size = draw_coussins_L_optimized(t,tr,pts,int(spec["fixed"]), traversins=trv)
        total_line = f"{coussins} → {cushions_count} × {chosen_size} cm"
    else:
        best = _optimize_valise_L_like(pts, spec["range"], spec["same"], traversins=trv)
        if not best:
            raise ValueError("Aucune configuration valise valide pour L.")
        sizes = best["sizes"]; shift = best["shift_bas"]
        n, sb, sg = _draw_L_like_with_sizes(t, tr, pts, sizes, shift, traversins=trv)
        cushions_count = n
        total_line = _format_valise_counts_console(
            {"bas": sb, "gauche": sg},
            best.get("counts", best.get("eval", {}).get("counts")),
            cushions_count,
        )

    # Légende
    draw_legend(t, tr, tx, ty, items=legend_items, pos="top-right")

    screen.tracer(True); t.hideturtle()

    add_split = int(polys.get("split_flags",{}).get("left",False) and dossier_left) \
              + int(polys.get("split_flags",{}).get("bottom",False) and dossier_bas)

    print("=== Rapport LNF ===")
    print(f"Dimensions : {tx}×{ty} — prof={profondeur} — méridienne {meridienne_side or '-'}={meridienne_len}")
    print(f"Banquettes : {len(polys['banquettes'])} → {banquette_sizes}")
    # Comptage pondéré des dossiers : <=110cm → 0.5, >110cm → 1
    dossiers_count = _compute_dossiers_count(polys)
    dossiers_str = f"{int(dossiers_count)}" if abs(dossiers_count - int(dossiers_count)) < 1e-9 else f"{dossiers_count}"
    print(f"Dossiers : {dossiers_str} (+{add_split} via scission) | Accoudoirs : {len(polys['accoudoirs'])}")
    print(f"Banquettes d’angle : 0")
    print(f"Traversins : {n_traversins} × 70x30")
    print(f"Coussins : {total_line}")
    turtle.done()

def render_LNF_v1(tx, ty, profondeur=DEPTH_STD,
                  dossier_left=True, dossier_bas=True,
                  acc_left=True, acc_bas=True,
                  meridienne_side=None, meridienne_len=0,
                  coussins="auto",
                  traversins=None,
                  couleurs=None,
                  window_title="LNF v1 — pivot gauche"):
    if meridienne_side=='g':
        if acc_left: raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
        if not dossier_left: raise ValueError("Méridienne gauche impossible sans dossier gauche.")
    if meridienne_side=='b':
        if acc_bas: raise ValueError("Méridienne bas interdite avec accoudoir bas.")
        if not dossier_bas: raise ValueError("Méridienne bas impossible sans dossier bas.")
    pts = compute_points_LNF_v1(tx,ty,profondeur,dossier_left,dossier_bas,acc_left,acc_bas,meridienne_side,meridienne_len)
    polys = build_polys_LNF_v1(pts,tx,ty,profondeur,dossier_left,dossier_bas,acc_left,acc_bas,meridienne_side,meridienne_len)
    _render_common_L(tx,ty,pts,polys,coussins,window_title,profondeur,dossier_left,dossier_bas,meridienne_side,meridienne_len,traversins=traversins, couleurs=couleurs)

def render_LNF_v2(tx, ty, profondeur=DEPTH_STD,
                  dossier_left=True, dossier_bas=True,
                  acc_left=True, acc_bas=True,
                  meridienne_side=None, meridienne_len=0,
                  coussins="auto",
                  traversins=None,
                  couleurs=None,
                  window_title="LNF v2 — pivot bas"):
    if meridienne_side=='g':
        if acc_left: raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
        if not dossier_left: raise ValueError("Méridienne gauche impossible sans dossier gauche.")
    if meridienne_side=='b':
        if acc_bas: raise ValueError("Méridienne bas interdite avec accoudoir bas.")
        if not dossier_bas: raise ValueError("Méridienne bas impossible sans dossier bas.")
    pts = compute_points_LNF_v2(tx,ty,profondeur,dossier_left,dossier_bas,acc_left,acc_bas,meridienne_side,meridienne_len)
    polys = build_polys_LNF_v2(pts,tx,ty,profondeur,dossier_left,dossier_bas,acc_left,acc_bas,meridienne_side,meridienne_len)
    _render_common_L(tx,ty,pts,polys,coussins,window_title,profondeur,dossier_left,dossier_bas,meridienne_side,meridienne_len,traversins=traversins, couleurs=couleurs)

def _dry_polys_for_variant(tx, ty, profondeur,
                           dossier_left, dossier_bas,
                           acc_left, acc_bas,
                           meridienne_side, meridienne_len,
                           variant):
    if meridienne_side == 'g':
        if acc_left:        raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
        if not dossier_left:raise ValueError("Méridienne gauche impossible sans dossier gauche.")
    if meridienne_side == 'b':
        if acc_bas:         raise ValueError("Méridienne bas interdite avec accoudoir bas.")
        if not dossier_bas: raise ValueError("Méridienne bas impossible sans dossier bas.")

    if variant == "v1":
        pts = compute_points_LNF_v1(tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas, meridienne_side, meridienne_len)
        polys = build_polys_LNF_v1(pts, tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas, meridienne_side, meridienne_len)
    else:
        pts = compute_points_LNF_v2(tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas, meridienne_side, meridienne_len)
        polys = build_polys_LNF_v2(pts, tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas, meridienne_side, meridienne_len)
    return pts, polys

def render_LNF(tx, ty, profondeur=DEPTH_STD,
               dossier_left=True, dossier_bas=True,
               acc_left=True, acc_bas=True,
               meridienne_side=None, meridienne_len=0,
               coussins="auto",
               variant="auto",
               traversins=None,
               couleurs=None,
               window_title="LNF — auto"):
    if variant and variant.lower() in ("v1", "v2"):
        chosen = variant.lower()
        if chosen == "v2":
            render_LNF_v2(tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas,
                          meridienne_side, meridienne_len, coussins, traversins=traversins, couleurs=couleurs,
                          window_title=window_title)
        else:
            render_LNF_v1(tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas,
                          meridienne_side, meridienne_len, coussins, traversins=traversins, couleurs=couleurs,
                          window_title=window_title)
        return

    nb_ban_v1 = float("inf")
    nb_ban_v2 = float("inf")
    polys1 = polys2 = None
    try:
        _pts1, _polys1 = _dry_polys_for_variant(tx, ty, profondeur,
                                               dossier_left, dossier_bas,
                                               acc_left, acc_bas,
                                               meridienne_side, meridienne_len,
                                               "v1")
        nb_ban_v1 = len(_polys1["banquettes"]); polys1=_polys1
    except ValueError:
        pass
    try:
        _pts2, _polys2 = _dry_polys_for_variant(tx, ty, profondeur,
                                               dossier_left, dossier_bas,
                                               acc_left, acc_bas,
                                               meridienne_side, meridienne_len,
                                               "v2")
        nb_ban_v2 = len(_polys2["banquettes"]); polys2=_polys2
    except ValueError:
        pass

    # choix : moins de banquettes ; tie-break = moins de scissions
    def scissions(polys):
        if not polys: return 999
        base_groups = 2  # L = gauche + bas
        return max(0, len(polys["banquettes"]) - base_groups)
    if nb_ban_v1 < nb_ban_v2: chosen = "v1"
    elif nb_ban_v2 < nb_ban_v1: chosen = "v2"
    else:
        if scissions(polys1) < scissions(polys2): chosen="v1"
        elif scissions(polys2) < scissions(polys1): chosen="v2"
        else: chosen = "v1" if tx >= ty else "v2"

    if chosen == "v2":
        render_LNF_v2(tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas,
                      meridienne_side, meridienne_len, coussins, traversins=traversins, couleurs=couleurs,
                      window_title=window_title)
    else:
        render_LNF_v1(tx, ty, profondeur, dossier_left, dossier_bas, acc_left, acc_bas,
                      meridienne_side, meridienne_len, coussins, traversins=traversins, couleurs=couleurs,
                      window_title=window_title)

# =====================================================================
# =====================  U (no fromage) — v1..v4  =====================
# =====================================================================

def compute_points_U_v1(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Compute the key geometry points for a U‑shaped sofa variant v1,
    optionally including a méridienne. When ``meridienne_side`` is 'g'
    (left) or 'd' (right) and ``meridienne_len`` > 0, the corresponding
    branch's back height is reduced accordingly. Additional keys
    ``By_`` and/or ``By4_`` are created to record these reduced heights.

    Parameters
    ----------
    tx, ty_left, tz_right : int
        Dimensions of the sofa (overall width and branch heights).
    profondeur : int
        Depth of the seat.
    dossier_left, dossier_bas, dossier_right : bool
        Flags indicating presence of backs on the left, bottom and right.
    acc_left, acc_bas, acc_right : bool
        Flags indicating presence of armrests on the left, bottom and right.
    meridienne_side : {'g', 'd', None}
        Side on which a méridienne is present ('g' for left, 'd' for right).
    meridienne_len : int
        Length of the méridienne; ignored if non‑positive or ``meridienne_side`` is None.

    Returns
    -------
    dict
        A dictionary of named points used to build the sofa's geometry.
    """
    prof = profondeur
    pts = {}
    F0x = 10 if dossier_left else 0
    F0y = 10 if dossier_bas else 0
    pts["D0"] = (0, 0)
    pts["D0x"] = (F0x, 0)
    pts["D0y"] = (0, F0y)
    pts["F0"] = (F0x, F0y)

    # Left branch geometry
    pts["Dy"] = (0, F0y + prof)
    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    top_y_L_dos = (
        max(F0y + prof, top_y_L_full - meridienne_len)
        if (meridienne_side == "g" and meridienne_len > 0)
        else top_y_L_full
    )
    pts["Dy2"] = (0, top_y_L_dos)
    pts["Ay"] = (0, ty_left)
    pts["Ay2"] = (F0x + prof, ty_left)
    pts["Ay_"] = (F0x, ty_left)

    pts["Fy"] = (F0x, F0y + prof)
    pts["Fy2"] = (F0x + prof, F0y + prof)
    pts["By"] = (F0x, top_y_L_full)
    pts["By2"] = (F0x + prof, top_y_L_full)
    if meridienne_side == "g" and meridienne_len > 0:
        # Reduced height points for méridienne on left
        pts["By_"] = (pts["By"][0], top_y_L_dos)
        pts["By2_"] = (pts["By2"][0], top_y_L_dos)

    # Right branch above the bottom
    D02x_x = tx - (10 if (dossier_right or dossier_bas) else 0)
    pts["Dx"] = (F0x + prof, 0)
    pts["Bx"] = (D02x_x, F0y)
    pts["Bx2"] = (D02x_x, F0y + prof)

    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    x_left_R = D02x_x - prof
    pts["Fy3"] = (x_left_R, F0y + prof)
    pts["By3"] = (x_left_R, top_y_R_full)
    pts["By4"] = (D02x_x, top_y_R_full)

    top_y_R_dos = (
        max(F0y + prof, top_y_R_full - meridienne_len)
        if (meridienne_side == "d" and meridienne_len > 0)
        else top_y_R_full
    )
    pts["D02x"] = (D02x_x, 0)
    pts["D02"] = (tx, 0)
    pts["D02y"] = (tx, F0y)
    pts["Dy3"] = (tx, top_y_R_dos)
    if meridienne_side == "d" and meridienne_len > 0:
        # Reduced height point for méridienne on right
        pts["By4_"] = (pts["By4"][0], top_y_R_dos)

    pts["Ax"] = (x_left_R, tz_right)
    pts["Ax2"] = (tx, tz_right)
    pts["Ax_par"] = (D02x_x, tz_right)

    # Canvas height for drawing
    pts["_ty_canvas"] = max(ty_left, tz_right)
    return pts

def build_polys_U_v1(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                     dossier_left=True, dossier_bas=True, dossier_right=True,
                     acc_left=True, acc_bas=True, acc_right=True):
    polys={"banquettes":[],"dossiers":[],"accoudoirs":[]}

    draw = {
        "D1": bool(dossier_left),
        "D2": bool(dossier_left or dossier_bas),
        "D3": bool(dossier_bas),
        "D4": bool(dossier_right),              # v1 : uniquement dossier_droit
        "D5": bool(dossier_right),
    }

    F0=pts["F0"]; Fy=pts["Fy"]; Fy2=pts["Fy2"]; By=pts["By"]; By2=pts["By2"]
    Bx=pts["Bx"]; Bx2=pts["Bx2"]; Fy3=pts["Fy3"]; By3=pts["By3"]; By4=pts["By4"]

    # banquettes
    split_left=split_bottom=split_right=False
    ban_g=[Fy,By,By2,Fy2,Fy]
    Lg=abs(By[1]-Fy[1])
    if Lg>SPLIT_THRESHOLD:
        split_left=True
        mid_y=_split_mid_int(Fy[1],By[1])
        g_low=[(Fy[0],Fy[1]),(Fy2[0],Fy[1]),(Fy2[0],mid_y),(Fy[0],mid_y),(Fy[0],Fy[1])]
        g_up=[(Fy[0],mid_y),(By[0],By[1]),(By2[0],By2[1]),(Fy2[0],mid_y),(Fy[0],mid_y)]
        polys["banquettes"]+=[g_low,g_up]
    else:
        polys["banquettes"].append(ban_g)

    ban_b=[F0,Bx,Bx2,Fy,F0]
    Lb=abs(Bx[0]-F0[0])
    if Lb>SPLIT_THRESHOLD:
        split_bottom=True
        mid_x=_split_mid_int(F0[0],Bx[0])
        b_left=[(F0[0],F0[1]),(mid_x,F0[1]),(mid_x,Fy[1]),(Fy[0],Fy[1]),(F0[0],F0[1])]
        b_right=[(mid_x,F0[1]),(Bx[0],Bx[1]),(Bx2[0],Bx2[1]),(mid_x,Fy[1]),(mid_x,F0[1])]
        polys["banquettes"]+=[b_left,b_right]
    else:
        polys["banquettes"].append(ban_b)

    ban_r=[By3,By4,Bx2,Fy3,By3]
    Lr=abs(By4[1]-Fy3[1])
    if Lr>SPLIT_THRESHOLD:
        split_right=True
        mid_y=_split_mid_int(Fy3[1],By4[1])
        r_low=[(Fy3[0],Fy3[1]),(Bx2[0],Fy3[1]),(Bx2[0],mid_y),(Fy3[0],mid_y),(Fy3[0],Fy3[1])]
        r_up=[(Fy3[0],mid_y),(By3[0],By3[1]),(By4[0],By4[1]),(Bx2[0],mid_y),(Fy3[0],mid_y)]
        polys["banquettes"]+=[r_low,r_up]
    else:
        polys["banquettes"].append(ban_r)

    # dossiers (groupes par côtés)
    groups = _dossiers_groups_U("v1", pts, tx, profondeur, draw)
    _append_groups_to_polys_U(polys, groups)

    # Accoudoirs U v1
    if acc_left:
        if draw["D1"]:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_"]])
    if acc_right:
        if draw["D5"]:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], pts["Dy3"], pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    polys["split_flags"]={"left":split_left,"bottom":split_bottom,"right":split_right}
    return polys, draw

def compute_points_U_v2(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Compute the key geometry points for a U‑shaped sofa variant v2,
    including optional méridienne support. Variant v2 has the left branch
    aligned with the bottom. When a méridienne is specified on either
    side, the branch height is reduced and additional keys ``By_`` or
    ``By4_`` are created to hold the reduced heights.

    See ``compute_points_U_v1`` for parameter descriptions.
    """
    prof = profondeur
    pts = {}
    F0x = 10 if dossier_left else 0
    F0y = 10 if dossier_bas else 0
    pts["D0"] = (0, 0)
    pts["D0x"] = (F0x, 0)
    pts["D0y"] = (0, F0y)
    pts["F0"] = (F0x, F0y)

    # Left branch (Fy at the bottom)
    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    top_y_L_dos = (
        max(F0y + prof, top_y_L_full - meridienne_len)
        if (meridienne_side == "g" and meridienne_len > 0)
        else top_y_L_full
    )
    pts["Dy2"] = (0, top_y_L_dos)
    pts["Ay"] = (0, ty_left)
    pts["Ay2"] = (F0x + prof, ty_left)
    pts["Ay_"] = (F0x, ty_left)
    pts["Fy"] = (F0x, F0y)
    pts["Fy2"] = (F0x + prof, F0y)
    pts["Fx"] = (F0x + prof, F0y)
    pts["Fx2"] = (F0x + prof, F0y + prof)
    pts["By"] = (F0x, top_y_L_full)
    pts["By2"] = (F0x + prof, top_y_L_full)
    if meridienne_side == "g" and meridienne_len > 0:
        pts["By_"] = (pts["By"][0], top_y_L_dos)
        pts["By2_"] = (pts["By2"][0], top_y_L_dos)

    # Bottom part up to Dx2
    D02x_x = tx - (10 if (dossier_right or dossier_bas) else 0)
    Dx2_x = D02x_x - prof
    pts["Dx"] = (F0x + prof, 0)
    pts["Dx2"] = (Dx2_x, 0)
    pts["Bx"] = (Dx2_x, F0y)
    pts["Bx2"] = (Dx2_x, F0y + prof)

    # Right branch (to the right of the bottom)
    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    pts["F02"] = (D02x_x, F0y)
    pts["By4"] = (D02x_x, top_y_R_full)
    pts["By3"] = (Dx2_x, top_y_R_full)
    top_y_R_dos = (
        max(F0y + prof, top_y_R_full - meridienne_len)
        if (meridienne_side == "d" and meridienne_len > 0)
        else top_y_R_full
    )
    pts["D02x"] = (D02x_x, 0)
    pts["D02"] = (tx, 0)
    pts["D02y"] = (tx, F0y)
    pts["Dy3"] = (tx, top_y_R_dos)
    if meridienne_side == "d" and meridienne_len > 0:
        pts["By4_"] = (pts["By4"][0], top_y_R_dos)

    pts["Ax"] = (Dx2_x, tz_right)
    pts["Ax2"] = (tx, tz_right)
    pts["Ax_par"] = (D02x_x, tz_right)
    # Store the exact right banquette split height for backrest scission.
    # For variant v2 the right banquette spans vertically from the y of
    # ``F02`` (the bottom of the right branch) to the y of ``By3`` (the top of
    # the right seat).  Using these values exactly ensures the backrest
    # scission aligns perfectly with the banquette scission.
    seat_y0_right = pts["F02"][1]  # bottom of the right banquette
    # The top of the right banquette is given by By3 (same as By4 on y)
    seat_y1_right = pts["By4"][1]
    pts["__SPLIT_Y_RIGHT"] = 0.5 * (seat_y0_right + seat_y1_right)

    pts["_ty_canvas"] = max(ty_left, tz_right)
    return pts

def build_polys_U_v2(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                     dossier_left=True, dossier_bas=True, dossier_right=True,
                     acc_left=True, acc_bas=True, acc_right=True):
    polys={"banquettes":[],"dossiers":[],"accoudoirs":[]}

    draw = {
        "D1": bool(dossier_left),
        "D2": bool(dossier_left or dossier_bas),
        "D3": bool(dossier_bas),
        "D4": bool(dossier_right or dossier_bas),
        "D5": bool(dossier_right),
    }

    F0=pts["F0"]; Fy=pts["Fy"]; Fx=pts["Fx"]; Fx2=pts["Fx2"]; By=pts["By"]; By2=pts["By2"]
    Bx=pts["Bx"]; Bx2=pts["Bx2"]; By3=pts["By3"]; By4=pts["By4"]; F02=pts["F02"]

    split_left=split_bottom=split_right=False

    # banquettes
    ban_g=[F0,By,By2,Fx,F0]
    Lg=abs(By[1]-F0[1])
    if Lg>SPLIT_THRESHOLD:
        split_left=True
        mid_y=_split_mid_int(F0[1],By[1])
        g_low=[(F0[0],F0[1]),(Fx[0],F0[1]),(Fx[0],mid_y),(F0[0],mid_y),(F0[0],F0[1])]
        g_up=[(F0[0],mid_y),(By[0],By[1]),(By2[0],By2[1]),(Fx[0],mid_y),(F0[0],mid_y)]
        polys["banquettes"]+=[g_low,g_up]
    else:
        polys["banquettes"].append(ban_g)

    ban_b=[Fx,Bx,Bx2,Fx2,Fx]
    Lb=abs(Bx2[0]-Fx2[0])
    if Lb>SPLIT_THRESHOLD:
        split_bottom=True
        mid_x=_split_mid_int(Fx2[0],Bx2[0])
        b_left=[(Fx[0],Fx[1]),(mid_x,Fx[1]),(mid_x,Fx2[1]),(Fx2[0],Fx2[1]),(Fx[0],Fx[1])]
        b_right=[(mid_x,Fx[1]),(Bx[0],Bx[1]),(Bx2[0],Bx2[1]),(mid_x,Fx2[1]),(mid_x,Fx[1])]
        polys["banquettes"]+=[b_left,b_right]
    else:
        polys["banquettes"].append(ban_b)

    ban_r=[F02,By4,By3,Bx,F02]
    Lr=abs(By3[1]-F02[1])
    if Lr>SPLIT_THRESHOLD:
        split_right=True
        mid_y=_split_mid_int(F02[1],By3[1])
        # Use the exact split height from the banquette for the right backrest
        pts["__SPLIT_Y_RIGHT"] = mid_y
        r_low=[(Bx[0],mid_y),(Bx[0],F02[1]),(F02[0],F02[1]),(F02[0],mid_y),(Bx[0],mid_y)]
        r_up=[(Bx[0],mid_y),(By3[0],By3[1]),(By4[0],By4[1]),(F02[0],mid_y),(Bx[0],mid_y)]
        polys["banquettes"]+=[r_low,r_up]
    else:
        # No split: still compute the median as potential split height
        pts["__SPLIT_Y_RIGHT"] = 0.5 * (F02[1] + By3[1])
        polys["banquettes"].append(ban_r)

    # dossiers
    groups = _dossiers_groups_U("v2", pts, tx, profondeur, draw)
    _append_groups_to_polys_U(polys, groups)

    # Accoudoirs U v2
    if acc_left:
        if draw["D1"]:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_"]])
    if acc_right:
        if draw["D5"]:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], pts["Dy3"], pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    polys["split_flags"]={"left":split_left,"bottom":split_bottom,"right":split_right}
    return polys, draw

def compute_points_U_v3(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Compute the key geometry points for a U‑shaped sofa variant v3,
    including optional méridienne support. Variant v3 is similar to v1
    but with different layout. As with other variants, specifying a
    méridienne reduces the corresponding branch height and adds ``By_``
    or ``By4_`` keys.

    See ``compute_points_U_v1`` for parameter descriptions.
    """
    prof = profondeur
    pts = {}
    F0x = 10 if dossier_left else 0
    F0y = 10 if dossier_bas else 0
    pts["D0"] = (0, 0)
    pts["D0x"] = (F0x, 0)
    pts["D0y"] = (0, F0y)
    pts["F0"] = (F0x, F0y)

    # Left branch (similar to v1)
    pts["Dy"] = (0, F0y + prof)
    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    top_y_L_dos = (
        max(F0y + prof, top_y_L_full - meridienne_len)
        if (meridienne_side == "g" and meridienne_len > 0)
        else top_y_L_full
    )
    pts["Dy2"] = (0, top_y_L_dos)
    pts["Ay"] = (0, ty_left)
    pts["Ay2"] = (F0x + prof, ty_left)
    pts["Ay_"] = (F0x, ty_left)
    pts["Fy"] = (F0x, F0y + prof)
    pts["Fy2"] = (F0x + prof, F0y + prof)
    pts["By"] = (F0x, top_y_L_full)
    pts["By2"] = (F0x + prof, top_y_L_full)
    if meridienne_side == "g" and meridienne_len > 0:
        pts["By_"] = (pts["By"][0], top_y_L_dos)
        pts["By2_"] = (pts["By2"][0], top_y_L_dos)

    # Bottom up to Bx (= D02x - prof)
    D02x_x = tx - (10 if (dossier_right or dossier_bas) else 0)
    Bx_x = D02x_x - prof
    pts["Dx"] = (F0x + prof, 0)
    pts["Bx"] = (Bx_x, F0y)
    pts["Bx2"] = (Bx_x, F0y + prof)

    # Right branch (to the right of the bottom)
    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    pts["By3"] = (Bx_x, top_y_R_full)
    pts["F02"] = (D02x_x, F0y)
    pts["By4"] = (D02x_x, top_y_R_full)
    top_y_R_dos = (
        max(F0y + prof, top_y_R_full - meridienne_len)
        if (meridienne_side == "d" and meridienne_len > 0)
        else top_y_R_full
    )
    pts["D02x"] = (D02x_x, 0)
    pts["D02"] = (tx, 0)
    pts["D02y"] = (tx, F0y)
    pts["Dy3"] = (tx, top_y_R_dos)
    if meridienne_side == "d" and meridienne_len > 0:
        pts["By4_"] = (pts["By4"][0], top_y_R_dos)

    pts["Ax"] = (Bx_x, tz_right)
    pts["Ax2"] = (tx, tz_right)
    pts["Ax_par"] = (D02x_x, tz_right)
    # Store the exact right banquette split height for backrest scission.
    # For variant v3 the right banquette spans from ``F02.y`` (the bottom
    # of the right branch) to ``By3.y`` (the top of the right seat).  Using
    # these values ensures the backrest scission aligns perfectly with the
    # banquette scission.
    seat_y0_right = pts["F02"][1]
    seat_y1_right = pts["By4"][1]  # By4 and By3 share the same y
    pts["__SPLIT_Y_RIGHT"] = 0.5 * (seat_y0_right + seat_y1_right)

    pts["_ty_canvas"] = max(ty_left, tz_right)
    return pts

def build_polys_U_v3(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                     dossier_left=True, dossier_bas=True, dossier_right=True,
                     acc_left=True, acc_bas=True, acc_right=True):
    polys={"banquettes":[],"dossiers":[],"accoudoirs":[]}

    draw = {
        "D1": bool(dossier_left),
        "D2": bool(dossier_left or dossier_bas),
        "D3": bool(dossier_bas),
        "D4": bool(dossier_right or dossier_bas),
        "D5": bool(dossier_right),
    }

    F0=pts["F0"]; Fy=pts["Fy"]; Fy2=pts["Fy2"]; By=pts["By"]; By2=pts["By2"]
    Bx=pts["Bx"]; Bx2=pts["Bx2"]; By3=pts["By3"]; By4=pts["By4"]; F02=pts["F02"]

    split_left=split_bottom=split_right=False
    # banquettes
    ban_g=[Fy,By,By2,Fy2,Fy]
    Lg=abs(By[1]-Fy[1])
    if Lg>SPLIT_THRESHOLD:
        split_left=True
        mid_y=_split_mid_int(Fy[1],By[1])
        g_low=[(Fy[0],Fy[1]),(Fy2[0],Fy[1]),(Fy2[0],mid_y),(Fy[0],mid_y),(Fy[0],Fy[1])]
        g_up=[(Fy[0],mid_y),(By[0],By[1]),(By2[0],By2[1]),(Fy2[0],mid_y),(Fy[0],mid_y)]
        polys["banquettes"]+=[g_low,g_up]
    else:
        polys["banquettes"].append(ban_g)

    ban_b=[F0,Bx,Bx2,Fy,F0]
    Lb=abs(Bx[0]-F0[0])
    if Lb>SPLIT_THRESHOLD:
        split_bottom=True
        mid_x=_split_mid_int(F0[0],Bx[0])
        b_left=[(F0[0],F0[1]),(mid_x,F0[1]),(mid_x,Fy[1]),(Fy[0],Fy[1]),(F0[0],F0[1])]
        b_right=[(mid_x,F0[1]),(Bx[0],Bx[1]),(Bx2[0],Bx2[1]),(mid_x,Fy[1]),(mid_x,F0[1])]
        polys["banquettes"]+=[b_left,b_right]
    else:
        polys["banquettes"].append(ban_b)

    # droite : By3 - By4 - F02 - Bx - By3
    ban_r=[By3,By4,F02,Bx,By3]
    Lr=abs(By3[1]-F02[1])
    if Lr>SPLIT_THRESHOLD:
        split_right=True
        mid_y=_split_mid_int(F02[1],By3[1])
        # Use the exact split height from the banquette for the right backrest
        pts["__SPLIT_Y_RIGHT"] = mid_y
        r_low=[(Bx[0],F02[1]),(F02[0],F02[1]),(F02[0],mid_y),(Bx[0],mid_y),(Bx[0],F02[1])]
        r_up=[(Bx[0],mid_y),(By3[0],By3[1]),(By4[0],By4[1]),(F02[0],mid_y),(Bx[0],mid_y)]
        polys["banquettes"]+=[r_low,r_up]
    else:
        # No split: still compute the median as potential split height
        pts["__SPLIT_Y_RIGHT"] = 0.5 * (F02[1] + By3[1])
        polys["banquettes"].append(ban_r)

    # dossiers
    groups = _dossiers_groups_U("v3", pts, tx, profondeur, draw)
    _append_groups_to_polys_U(polys, groups)

    # Accoudoirs U v3
    if acc_left:
        if draw["D1"]:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_"]])
    if acc_right:
        if draw["D5"]:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], pts["Dy3"], pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    polys["split_flags"]={"left":split_left,"bottom":split_bottom,"right":split_right}
    return polys, draw

def compute_points_U_v4(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Compute the key geometry points for a U‑shaped sofa variant v4,
    including optional méridienne support. Variant v4 has a particular
    arrangement of the left and right branches. When a méridienne is
    specified, the back height on that side is reduced, and keys
    ``By_`` and/or ``By4_`` are added as appropriate.

    See ``compute_points_U_v1`` for parameter descriptions.
    """
    prof = profondeur
    pts = {}
    F0x = 10 if dossier_left else 0
    F0y = 10 if dossier_bas else 0
    pts["D0"] = (0, 0)
    pts["D0x"] = (F0x, 0)
    pts["D0y"] = (0, F0y)
    pts["F0"] = (F0x, F0y)

    # Left post (montant gauche)
    top_y_L_full = ty_left - (ACCOUDOIR_THICK if acc_left else 0)
    pts["By"] = (F0x, top_y_L_full)
    pts["Fx"] = (F0x + profondeur, F0y)
    pts["Fx2"] = (F0x + profondeur, F0y + prof)
    pts["By2"] = (F0x + profondeur, top_y_L_full)
    top_y_L_dos = (
        max(F0y + prof, top_y_L_full - meridienne_len)
        if (meridienne_side == "g" and meridienne_len > 0)
        else top_y_L_full
    )
    pts["Dy2"] = (0, top_y_L_dos)
    if meridienne_side == "g" and meridienne_len > 0:
        pts["By_"] = (pts["By"][0], top_y_L_dos)
        pts["By2_"] = (pts["By2"][0], top_y_L_dos)
    pts["Ay"] = (0, ty_left)
    pts["Ay2"] = (F0x + profondeur, ty_left)
    pts["Ay_"] = (F0x, ty_left)

    # Right limit
    D02x_x = tx - (10 if (dossier_right or dossier_bas) else 0)
    pts["Dx"] = (F0x + profondeur, 0)
    pts["Bx"] = (D02x_x, F0y)
    pts["Bx2"] = (D02x_x, F0y + prof)

    # Right branch (above the bottom)
    top_y_R_full = tz_right - (ACCOUDOIR_THICK if acc_right else 0)
    x_left_R = D02x_x - prof
    pts["Fy3"] = (x_left_R, F0y + prof)
    pts["By3"] = (x_left_R, top_y_R_full)
    pts["By4"] = (D02x_x, top_y_R_full)
    top_y_R_dos = (
        max(F0y + prof, top_y_R_full - meridienne_len)
        if (meridienne_side == "d" and meridienne_len > 0)
        else top_y_R_full
    )
    pts["D02x"] = (D02x_x, 0)
    pts["D02"] = (tx, 0)
    pts["D02y"] = (tx, F0y)
    pts["Dy3"] = (tx, top_y_R_dos)
    if meridienne_side == "d" and meridienne_len > 0:
        pts["By4_"] = (pts["By4"][0], top_y_R_dos)

    pts["Ax"] = (x_left_R, tz_right)
    pts["Ax2"] = (tx, tz_right)
    pts["Ax_par"] = (D02x_x, tz_right)

    pts["_ty_canvas"] = max(ty_left, tz_right)
    return pts

def build_polys_U_v4(pts, tx, ty_left, tz_right, profondeur=DEPTH_STD,
                     dossier_left=True, dossier_bas=True, dossier_right=True,
                     acc_left=True, acc_bas=True, acc_right=True):
    polys = {"banquettes": [], "dossiers": [], "accoudoirs": []}

    draw = {
        "D1": bool(dossier_left),
        "D2": bool(dossier_left or dossier_bas),
        "D3": bool(dossier_bas),
        "D4": bool(dossier_right or dossier_bas),
        "D5": bool(dossier_right),
    }

    F0=pts["F0"]; Fx=pts["Fx"]; Fx2=pts["Fx2"]; By=pts["By"]; By2=pts["By2"]
    Bx=pts["Bx"]; Bx2=pts["Bx2"]; Fy3=pts["Fy3"]; By3=pts["By3"]; By4=pts["By4"]

    split_left=split_bottom=split_right=False

    # banquettes
    ban_g = [F0, By, By2, Fx, F0]
    Lg = abs(By[1] - F0[1])
    if Lg > SPLIT_THRESHOLD:
        split_left=True
        mid_y = _split_mid_int(F0[1], By[1])
        g_low  = [(F0[0],F0[1]), (Fx[0],F0[1]), (Fx[0],mid_y), (F0[0],mid_y), (F0[0],F0[1])]
        g_high = [(F0[0],mid_y), (By[0],By[1]), (By2[0],By2[1]), (Fx[0],mid_y), (F0[0],mid_y)]
        polys["banquettes"] += [g_low, g_high]
    else:
        polys["banquettes"].append(ban_g)

    ban_b = [Fx, Bx, Bx2, Fx2, Fx]
    Lb = abs(Bx2[0] - Fx2[0])
    if Lb > SPLIT_THRESHOLD:
        split_bottom=True
        mid_x = _split_mid_int(Fx2[0], Bx2[0])
        pts["__SPLIT_X_BOTTOM"] = mid_x
        b_left  = [(Fx[0],Fx[1]), (mid_x,Fx[1]), (mid_x,Fx2[1]), (Fx2[0],Fx2[1]), (Fx[0],Fx[1])]
        b_right = [(mid_x,Fx[1]), (Bx[0],Bx[1]), (Bx2[0],Bx2[1]), (mid_x,Fx2[1]), (mid_x,Fx[1])]
        polys["banquettes"] += [b_left, b_right]
    else:
        polys["banquettes"].append(ban_b)

    ban_r = [Fy3, By3, By4, Bx2, Fy3]
    Lr = abs(By3[1] - Fy3[1])
    if Lr > SPLIT_THRESHOLD:
        split_right=True
        mid_y = _split_mid_int(Fy3[1], By3[1])
        r_low  = [(Fy3[0],Fy3[1]), (Bx2[0],Fy3[1]), (Bx2[0],mid_y), (Fy3[0],mid_y), (Fy3[0],Fy3[1])]
        r_high = [(Fy3[0],mid_y), (By3[0],By3[1]), (By4[0],By4[1]), (Bx2[0],mid_y), (Fy3[0],mid_y)]
        polys["banquettes"] += [r_low, r_high]
    else:
        polys["banquettes"].append(ban_r)

    # dossiers
    groups = _dossiers_groups_U("v4", pts, tx, profondeur, draw)
    _append_groups_to_polys_U(polys, groups)

    # Accoudoirs U v4
    if acc_left:
        if draw["D1"]:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By2"], pts["Dy2"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay_"], pts["Ay2"], pts["By2"], pts["By"], pts["Ay_"]])
    if acc_right:
        if draw["D5"]:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax2"], pts["Dy3"], pts["By3"]])
        else:
            polys["accoudoirs"].append([pts["By3"], pts["Ax"], pts["Ax_par"], pts["By4"], pts["By3"]])

    polys["split_flags"]={"left":split_left,"bottom":split_bottom,"right":split_right}
    return polys, draw

# ---------- Dossiers par côtés (U) ----------
def _dossiers_groups_U(variant, pts, tx, profondeur, draw):
    """
    Build the groups of polygons for the backs (dossiers) of a U‑shaped sofa.

    This version honours ``By_`` and ``By4_`` when present, so that the
    dossier height is limited by the méridienne. Each group is a dict of
    lists keyed by the back segment (left D1/D2, bottom D3, right D4/D5).
    """
    groups = {
        "left": {"D1": [], "D2": []},
        "bottom": {"D3": []},
        "right": {"D4": [], "D5": []},
    }
    F0x, F0y = pts["F0"]

    By_use = pts.get("By_", pts.get("By"))
    By4_use = pts.get("By4_", pts.get("By4"))

    if variant == "v1":
        if draw["D1"]:
            # D1 gauche — rectangle(s) vertical(aux) avec scission alignée sur la banquette gauche
            x0, x1 = 0, F0x
            # portion de dossier au-dessus de l'assise : de Fy.y jusqu'à By_use.y
            y0, y1 = pts["Fy"][1], By_use[1]
            # bornes complètes de l'assise gauche pour calculer la scission (Fy.y → By.y)
            seat_y0, seat_y1 = pts["Fy"][1], pts["By"][1]
            groups["left"]["D1"] += _build_dossier_vertical_rects(x0, x1, y0, y1, seat_y0, seat_y1)
        if draw["D2"]:
            groups["left"]["D2"].append([
                pts["D0x"],
                pts["D0"],
                pts["Dy"],
                pts["Fy"],
                pts["D0x"],
            ])
        if draw["D3"]:
            F0x, F0y = pts["F0"]; xL = F0x; xR = pts["Bx"][0]
            if abs(xR - xL) > SPLIT_THRESHOLD:
                mid_x = _split_mid_int(xL, xR)
                groups["bottom"]["D3"] += [
                    _rectU(xL, 0, mid_x, F0y),
                    _rectU(mid_x, 0, xR,  F0y),
                ]
            else:
                groups["bottom"]["D3"].append(_rectU(xL, 0, xR, F0y))
        if draw["D4"]:
            groups["right"]["D4"].append([
                pts["D02x"],
                pts["D02"],
                pts["Dy3"],
                pts["Bx2"],
                pts["D02x"],
            ])
        if draw["D5"]:
            # D5 droite — rectangle(s) vertical(aux) avec scission alignée sur la banquette droite
            x0 = pts["D02x"][0]
            y1 = F0y + profondeur
            y_top = By4_use[1]
            # Utilise les bornes de l'assise droite pour déterminer la scission (Fy3.y → By4_use.y)
            groups["right"]["D5"] += _build_dossier_vertical_rects(
                x0, tx, y1, y_top,
                pts["Fy3"][1], By4_use[1]
            )

    elif variant == "v2":
        if draw["D1"]:
            # D1 gauche — scission alignée sur la banquette gauche
            x0, x1 = 0, F0x
            # inclut la lame basse : zone 0 → By_use.y
            y0, y1 = 0, By_use[1]
            seat_y0, seat_y1 = pts["Fy"][1], pts["By"][1]
            groups["left"]["D1"] += _build_dossier_vertical_rects(
                x0, x1, y0, y1,
                seat_y0, seat_y1
            )
        if draw["D2"]:
            groups["left"]["D2"].append([
                pts["D0x"],
                pts["Dx"],
                pts["Fx"],
                pts["F0"],
                pts["D0x"],
            ])
        if draw["D3"]:
            # Clip the bottom backrest so it does not overlap the left vertical backrest.
            F0x, F0y = pts["F0"]
            # Left limit starts at the right edge of the left banquette (Fx.x)
            x_left_limit = pts["Fx"][0] if "Fx" in pts else F0x
            # Right limit ends at the left edge of the right banquette (F02.x) if present
            x_right_limit = pts["F02"][0] if "F02" in pts else tx
            # Original extents of the D3 band
            xL_orig = F0x
            xR_orig = pts["F02"][0] if "F02" in pts else tx
            Lb = abs(pts["Bx"][0] - pts["Fx"][0])
            if Lb > SPLIT_THRESHOLD:
                mid_x = _split_mid_int(pts["Fx"][0], pts["Bx"][0])
                # First segment: from xL_orig to mid_x (clamped)
                x0c = max(x_left_limit, xL_orig)
                x1c = min(mid_x, x_right_limit)
                if x1c > x0c:
                    groups["bottom"]["D3"].append(_rectU(x0c, 0, x1c, F0y))
                # Second segment: from mid_x to xR_orig (clamped)
                x0c = max(x_left_limit, mid_x)
                x1c = min(xR_orig, x_right_limit)
                if x1c > x0c:
                    groups["bottom"]["D3"].append(_rectU(x0c, 0, x1c, F0y))
            else:
                # Single segment case, clamp to limits
                x0c = max(x_left_limit, xL_orig)
                x1c = min(xR_orig, x_right_limit)
                if x1c > x0c:
                    groups["bottom"]["D3"].append(_rectU(x0c, 0, x1c, F0y))
        if draw["D4"]:
            groups["right"]["D4"].append([
                pts["Dx2"],
                pts["D02x"],
                pts["F02"],
                pts["Bx"],
                pts["Dx2"],
            ])
        if draw["D5"]:
            # D5 droite pour v2 : un unique rectangle 0 → By4_use scindé une seule fois.
            # Use the exact banquette split height if available to align the
            # backrest scission.  The seat on the right branch starts at
            # 'profondeur' (depth) and ends at By4_use.y.  When a split height
            # has been recorded in __SPLIT_Y_RIGHT, calculate the mirrored
            # lower bound so that the median of (seat_y0, seat_y1) equals the
            # split.  Otherwise, fall back to the old behaviour.
            x0 = pts["D02x"][0]
            y0, y1 = 0, By4_use[1]
            y_split = pts.get("__SPLIT_Y_RIGHT", None)
            if y_split is not None:
                seat_y1 = y1
                seat_y0 = 2 * y_split - seat_y1
            else:
                # fallback: use the bottom y of the right seat (F02.y if present, else Fy3.y or depth)
                if "F02" in pts:
                    seat_y0 = pts["F02"][1]
                elif "Fy3" in pts:
                    seat_y0 = pts["Fy3"][1]
                else:
                    seat_y0 = profondeur
                seat_y1 = y1
            groups["right"]["D5"] += _build_dossier_vertical_rects(
                x0, tx, y0, y1,
                seat_y0, seat_y1
            )

    elif variant == "v3":
        if draw["D1"]:
            # D1 gauche — scission alignée sur la banquette gauche
            x0, x1 = 0, F0x
            y0, y1 = pts["Fy"][1], By_use[1]
            seat_y0, seat_y1 = pts["Fy"][1], pts["By"][1]
            groups["left"]["D1"] += _build_dossier_vertical_rects(
                x0, x1, y0, y1,
                seat_y0, seat_y1
            )
        if draw["D2"]:
            groups["left"]["D2"].append([
                pts["D0x"],
                pts["D0"],
                pts["Dy"],
                pts["Fy"],
                pts["D0x"],
            ])
        if draw["D3"]:
            xL = F0x; xR = pts["Bx"][0]; y0 = 0; y1 = F0y
            if abs(xR - xL) > SPLIT_THRESHOLD:
                mid_x = _split_mid_int(xL, xR)
                groups["bottom"]["D3"] += [_rectU(xL, y0, mid_x, y1), _rectU(mid_x, y0, xR, y1)]
            else:
                groups["bottom"]["D3"].append(_rectU(xL, y0, xR, y1))
        if draw["D4"]:
            bx0 = pts["Bx"][0]
            groups["right"]["D4"].append([
                pts["Dx"],
                pts["D02x"],
                pts["F02"],
                pts["Bx"],
                (bx0, 0),
                pts["Dx"],
            ])
        if draw["D5"]:
            # D5 droite pour v3 : un unique rectangle 0 → By4_use scindé une seule fois.
            # Use the exact banquette split height if available to align the
            # backrest scission.  The seat on the right branch starts at
            # 'profondeur' (depth) and ends at By4_use.y.  When a split height
            # has been recorded in __SPLIT_Y_RIGHT, calculate the mirrored
            # lower bound so that the median of (seat_y0, seat_y1) equals the
            # split.  Otherwise, fall back to the old behaviour.
            x0 = pts["D02x"][0]
            y0, y1 = 0, By4_use[1]
            y_split = pts.get("__SPLIT_Y_RIGHT", None)
            if y_split is not None:
                seat_y1 = y1
                seat_y0 = 2 * y_split - seat_y1
            else:
                # fallback: use the bottom y of the right seat (F02.y if present, else Fy3.y or depth)
                if "F02" in pts:
                    seat_y0 = pts["F02"][1]
                elif "Fy3" in pts:
                    seat_y0 = pts["Fy3"][1]
                else:
                    seat_y0 = profondeur
                seat_y1 = y1
            groups["right"]["D5"] += _build_dossier_vertical_rects(
                x0, tx, y0, y1,
                seat_y0, seat_y1
            )

    else:  # v4
        if draw["D1"]:
            # D1 gauche — scission alignée sur la banquette gauche, incluant la lame basse
            x0, x1 = 0, F0x
            # inclut la lame basse : zone 0 → By_use.y
            y0, y1 = 0, By_use[1]
            # fallback pour Fy : si absent, utiliser F0y
            seat_y0_left = (pts.get("Fy", [None, None])[1] if "Fy" in pts else F0y)
            # fallback pour By : si absent, utiliser By_use.y
            seat_y1_left = (pts.get("By", [None, None])[1] if "By" in pts else By_use[1])
            groups["left"]["D1"] += _build_dossier_vertical_rects(
                x0, x1, y0, y1,
                seat_y0_left, seat_y1_left
            )
        if draw["D2"]:
            groups["left"]["D2"].append([
                pts["D0x"],
                pts["Dx"],
                pts["Fx"],
                pts["F0"],
                pts["D0x"],
            ])
        if draw["D3"]:
            # ----- Clip and split the bottom backrest D3 for v4 -----
            # 1) Determine left and right limits
            # Left limit: the right edge of D2 (Dx.x) if it exists, otherwise Fx.x or F0.x
            x_left_limit = (
                pts["Dx"][0] if "Dx" in pts else (
                    pts["Fx"][0] if "Fx" in pts else F0x
                )
            )
            # Only consider the right column if D5 is active
            # The right column exists if either the bottom-right backrest (D4) or
            # the top-right backrest (D5) is active. Without this, D3 can extend
            # too far to the right when only D4 is present (dossier_bas=True but
            # dossier_right=False).  Clipping based on D4 as well ensures the
            # bottom backrest is properly limited.
            have_right_col = bool(draw.get("D4") or draw.get("D5"))
            if have_right_col:
                if "F02x" in pts:
                    x_right_limit = pts["F02x"][0]
                elif "D02x" in pts:
                    x_right_limit = pts["D02x"][0]
                else:
                    x_right_limit = tx
            else:
                x_right_limit = tx
            # If no space remains, skip drawing D3
            if x_right_limit > x_left_limit:
                # Split only if the bottom seat actually split.
                x_mid_mark = pts.get("__SPLIT_X_BOTTOM")
                if x_mid_mark is not None:
                    # Clamp x_mid within the effective span
                    x_mid = max(x_left_limit, min(x_mid_mark, x_right_limit))
                    if x_mid > x_left_limit:
                        groups["bottom"]["D3"].append(_rectU(x_left_limit, 0, x_mid, F0y))
                    if x_right_limit > x_mid:
                        groups["bottom"]["D3"].append(_rectU(x_mid, 0, x_right_limit, F0y))
                else:
                    # No seat split: draw a single continuous bottom backrest
                    groups["bottom"]["D3"].append(_rectU(x_left_limit, 0, x_right_limit, F0y))
        F02x = pts["D02x"][0]
        y0 = F0y
        y1 = y0 + profondeur
        # Only draw the right backrest D4 if both D4 and D5 are active (right side requested).
        # In v4 the shape of D4 depends on whether a bottom backrest (D3) exists.
        # When a bottom backrest is present, the angle is closed by a polygon Dy3-By4-D02x-D02-Dy3.
        # Otherwise (no bottom backrest), the angle is closed by Dy3-D02y-Bx-By4-Dy3.
        if draw.get("D4") and draw.get("D5"):
            if draw.get("D3"):
                # with bottom backrest: D4 = Dy3 - By4 - D02x - D02 - Dy3
                groups["right"]["D4"].append([
                    pts["Dy3"], pts["By4"], pts["D02x"], pts["D02"], pts["Dy3"],
                ])
            else:
                # without bottom backrest: D4 = Dy3 - D02y - Bx - By4 - Dy3
                groups["right"]["D4"].append([
                    pts["Dy3"], pts["D02y"], pts["Bx"], pts["By4"], pts["Dy3"],
                ])
        if draw["D5"]:
            y_top = By4_use[1]
            # D5 droite — scission alignée sur la banquette droite au-dessus de l'assise
            # fallback pour seat_y0_right : Fy3.y si présent, sinon Fy.y, sinon F0y+profondeur
            seat_y0_right = (
                pts.get("Fy3", [None, None])[1] if "Fy3" in pts else (
                    pts.get("Fy", [None, None])[1] if "Fy" in pts else F0y + profondeur
                )
            )
            # zone au-dessus de l'assise : F0y+profondeur → y_top
            groups["right"]["D5"] += _build_dossier_vertical_rects(
                F02x, tx, F0y + profondeur, y_top,
                seat_y0_right, By4_use[1]
            )
    return groups

def _append_groups_to_polys_U(polys, groups):
    order = {"left":["D1","D2"], "bottom":["D3"], "right":["D4","D5"]}
    for side in ("left","bottom","right"):
        for d in order[side]:
            for poly in groups[side].get(d, []):
                polys["dossiers"].append(poly)
    polys["dossiers_by_side"] = groups  # info

# === AUTO optimisé pour U (taille + orientation) ===
def _best_orientation_score_U(variant, pts, drawn, size, traversins=None):
    """
    Determine the optimal orientation for placing cushions in a U‑shaped sofa.

    This version considers potential méridienne limits by using the
    ``By_``/``By4_`` keys for the left and right branches when present.

    Parameters
    ----------
    variant : str
        The sofa variant (v1, v2, v3 or v4).
    pts : dict
        Geometry points defining the sofa.
    drawn : dict
        Flags indicating which backs/arms are drawn.
    size : int
        Size of each cushion.
    traversins : set or None
        A set containing 'g' and/or 'd' if traversins (bolsters) are
        present on the left or right; used to reduce available height.

    Returns
    -------
    tuple
        (score tuple, x_start, x_end, y_left_start, y_right_start)
    """
    F0x, F0y = pts["F0"]
    x_end = _u_variant_x_end(variant, pts)

    def cnt_h(x0, x1):
        return int(max(0, x1 - x0) // size)

    def cnt_v(y0, y1):
        return int(max(0, y1 - y0) // size)

    # vertical limits: take méridienne into account if present
    y_end_L = pts.get("By_", pts["By"])[1]
    y_end_R = pts.get("By4_", pts["By4"])[1]
    if traversins:
        if "g" in traversins:
            y_end_L -= TRAVERSIN_THK
        if "d" in traversins:
            y_end_R -= TRAVERSIN_THK

    def score(shiftL, shiftR):
        xs = F0x + (CUSHION_DEPTH if shiftL else 0)
        xe = x_end - (CUSHION_DEPTH if shiftR else 0)
        bas = cnt_h(xs, xe)
        yL0 = F0y + (0 if (not drawn.get("D1", False) or shiftL) else CUSHION_DEPTH)
        has_right = drawn.get("D4", False) or drawn.get("D5", False)
        yR0 = F0y + (0 if (not has_right or shiftR) else CUSHION_DEPTH)
        g = cnt_v(yL0, y_end_L)
        d = cnt_v(yR0, y_end_R)
        waste = (
            (max(0, xe - xs) % size)
            + (max(0, y_end_L - yL0) % size)
            + (max(0, y_end_R - yR0) % size)
        )
        return (bas + g + d, -waste, -size), xs, xe, yL0, yR0

    cands = [
        score(False, False),
        score(True, False),
        score(False, True),
        score(True, True),
    ]
    return max(cands, key=lambda k: k[0])

def _choose_cushion_size_auto_U(variant, pts, drawn, traversins=None):
    best_s, best_tuple = 65, (-1, -1, -65)
    for s in (65, 80, 90):
        (score_tuple, *_rest) = _best_orientation_score_U(variant, pts, drawn, s, traversins=traversins)
        if score_tuple > best_tuple:
            best_tuple, best_s = score_tuple, s
    return best_s

def _draw_cushions_variant_U(t, tr, variant, pts, size, drawn, traversins=None):
    """
    Draw cushions for the U‑shaped sofa, taking a possible méridienne into account.

    This function uses ``_best_orientation_score_U`` to determine the optimal
    placement and then draws cushions on the bottom and both branches. The
    ``By_``/``By4_`` keys and optional traversins reduce the available
    height as needed.
    """
    (score_tuple, xs, xe, yL0, yR0) = _best_orientation_score_U(
        variant, pts, drawn, size, traversins=traversins
    )
    F0x, F0y = pts["F0"]
    x_col = pts["Bx"][0] if variant in ("v1", "v4") else pts["F02"][0]
    y_end_L = pts.get("By_", pts["By"])[1]
    y_end_R = pts.get("By4_", pts["By4"])[1]
    if traversins:
        if "g" in traversins:
            y_end_L -= TRAVERSIN_THK
        if "d" in traversins:
            y_end_R -= TRAVERSIN_THK

    count = 0
    # bottom
    y = F0y
    x = xs
    while x + size <= xe + 1e-6:
        poly = [
            (x, y),
            (x + size, y),
            (x + size, y + CUSHION_DEPTH),
            (x, y + CUSHION_DEPTH),
            (x, y),
        ]
        draw_polygon_cm(
            t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1
        )
        label_poly(t, tr, poly, f"{size}", font=FONT_CUSHION)
        x += size
        count += 1

    # left branch
    x = F0x
    y = yL0
    while y + size <= y_end_L + 1e-6:
        poly = [
            (x, y),
            (x + CUSHION_DEPTH, y),
            (x + CUSHION_DEPTH, y + size),
            (x, y + size),
            (x, y),
        ]
        draw_polygon_cm(
            t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1
        )
        label_poly(t, tr, poly, f"{size}", font=FONT_CUSHION)
        y += size
        count += 1

    # right branch
    x = x_col
    y = yR0
    while y + size <= y_end_R + 1e-6:
        poly = [
            (x - CUSHION_DEPTH, y),
            (x, y),
            (x, y + size),
            (x - CUSHION_DEPTH, y + size),
            (x - CUSHION_DEPTH, y),
        ]
        draw_polygon_cm(
            t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1
        )
        label_poly(t, tr, poly, f"{size}", font=FONT_CUSHION)
        y += size
        count += 1

    return count

def _render_common_U(
    variant,
    tx,
    ty_left,
    tz_right,
    profondeur,
    dossier_left,
    dossier_bas,
    dossier_right,
    acc_left,
    acc_bas,
    acc_right,
    coussins,
    window_title,
    compute_fn,
    build_fn,
    traversins=None,
    couleurs=None,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Common rendering routine for all U‑shaped sofa variants.

    This function computes the geometry via ``compute_fn`` (passing
    through ``meridienne_side`` and ``meridienne_len``), builds the
    polygons via ``build_fn``, draws the backs, seats, armrests,
    cushions and traversins, and prints a textual report. The window
    title is augmented to display the méridienne configuration.
    """
    # Compute points with méridienne parameters
    pts = compute_fn(
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
        meridienne_side,
        meridienne_len,
    )
    # Build polygons and drawing flags
    polys, drawn = build_fn(
        pts,
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
    )
    # Ensure no seat exceeds maximum length
    _assert_banquettes_max_250(polys)

    # Parse traversins and resolve colors
    trv = _parse_traversins_spec(traversins, allowed={"g", "d"})
    legend_items = _resolve_and_apply_colors(couleurs)

    # Setup drawing canvas
    ty_canvas = pts["_ty_canvas"]
    screen = turtle.Screen()
    screen.setup(WIN_W, WIN_H)
    screen.title(
        f"{window_title} — {variant} — tx={tx} / ty(left)={ty_left} / tz(right)={tz_right} — prof={profondeur}"
        f" — méridienne {meridienne_side or '-'}={meridienne_len}"
    )
    t = turtle.Turtle(visible=False)
    t.speed(0)
    screen.tracer(False)
    tr = WorldToScreen(tx, ty_canvas, WIN_W, WIN_H, PAD_PX, ZOOM)

    # Draw backs, seats and armrests
    for p in polys["dossiers"]:
        if _poly_has_area(p):
            draw_polygon_cm(t, tr, p, fill=COLOR_DOSSIER)
    for p in polys["banquettes"]:
        draw_polygon_cm(t, tr, p, fill=COLOR_ASSISE)
    for p in polys["accoudoirs"]:
        draw_polygon_cm(t, tr, p, fill=COLOR_ACC)

    # Draw traversins and count
    n_traversins = _draw_traversins_U_common(
        t, tr, variant, pts, profondeur, trv
    )

    # Dimension arrows
    draw_double_arrow_vertical_cm(
        t, tr, -25, 0, ty_left, f"{ty_left} cm"
    )
    draw_double_arrow_vertical_cm(
        t, tr, tx + 25, 0, tz_right, f"{tz_right} cm"
    )
    draw_double_arrow_horizontal_cm(
        t, tr, -25, 0, tx, f"{tx} cm"
    )

    # Label seats : afficher les dimensions sur deux lignes. Décaler légèrement selon l'orientation et la position.
    banquette_sizes = []
    for poly in polys["banquettes"]:
        L, P = banquette_dims(poly)
        banquette_sizes.append((L, P))
        # Première dimension sans unité suivie d'un « x », seconde avec « cm »
        text = f"{L}x\n{P} cm"
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # Si la banquette est plus haute que large, décaler horizontalement en fonction de sa position
        if bb_h >= bb_w:
            cx = sum(xs) / len(xs)
            # Séparer par rapport à la moitié de la largeur totale (tx) pour savoir à quel côté se trouve la banquette
            # Réduction d'environ 3 cm par rapport aux offsets précédents :
            # Branche gauche (cx < tx/2) : CUSHION_DEPTH+7 ; branche droite : -(CUSHION_DEPTH-8)
            dx = (CUSHION_DEPTH + 7) if cx < tx / 2.0 else -(CUSHION_DEPTH - 8)
            label_poly_offset_cm(t, tr, poly, text, dx_cm=dx, dy_cm=0.0)
        else:
            # Si la banquette est plus large que haute, centrer simplement
            label_poly(t, tr, poly, text)

    # Label backs and armrests
    for p in polys["dossiers"]:
        if _poly_has_area(p):
            label_poly(t, tr, p, "10")
    for p in polys["accoudoirs"]:
        if _poly_has_area(p):
            label_poly(t, tr, p, "15")

    # Draw cushions
    spec = _parse_coussins_spec(coussins)
    if spec["mode"] == "auto":
        size = _choose_cushion_size_auto_U(
            variant, pts, drawn, traversins=trv
        )
        cushions_count = _draw_cushions_variant_U(
            t, tr, variant, pts, size, drawn, traversins=trv
        )
        total_line = f"{coussins} → {cushions_count} × {size} cm"
    elif spec["mode"] == "fixed":
        size = int(spec["fixed"])
        cushions_count = _draw_cushions_variant_U(
            t, tr, variant, pts, size, drawn, traversins=trv
        )
        total_line = f"{coussins} → {cushions_count} × {size} cm"
    else:
        best = _optimize_valise_U(
            variant,
            pts,
            drawn,
            spec["range"],
            spec["same"],
            traversins=trv,
        )
        if not best:
            raise ValueError(
                "Aucune configuration valise valide pour U."
            )
        sizes = best["sizes"]
        shiftL = best.get("shiftL", False)
        shiftR = best.get("shiftR", False)
        cushions_count = _draw_U_with_sizes(
            variant,
            t,
            tr,
            pts,
            sizes,
            drawn,
            shiftL,
            shiftR,
            traversins=trv,
        )
        sb, sg, sd = (
            sizes["bas"],
            sizes["gauche"],
            sizes["droite"],
        )
        total_line = _format_valise_counts_console(
            {"bas": sb, "gauche": sg, "droite": sd},
            best.get("counts", best.get("eval", {}).get("counts")),
            cushions_count,
        )

    # Title and legend
    draw_title_center(
        t, tr, tx, ty_canvas, "Canapé en U sans angle"
    )
    draw_legend(
        t, tr, tx, ty_canvas, items=legend_items, pos="top-center"
    )

    # Finalize drawing
    screen.tracer(True)
    t.hideturtle()

    # Compute split bonus for backs
    split_flags = polys.get("split_flags", {})
    add_split = int(
        split_flags.get("left", False)
        and (drawn.get("D1") or drawn.get("D2"))
    ) + int(
        split_flags.get("bottom", False) and drawn.get("D3")
    ) + int(
        split_flags.get("right", False) and drawn.get("D5")
    )

    # Print report
    print(f"=== Rapport canapé U (variant {variant}) ===")
    print(
        f"Dimensions : tx={tx} / ty(left)={ty_left} / tz(right)={tz_right} — prof={profondeur}"
    )
    print(
        f"Méridienne : {meridienne_side or '-'} ({meridienne_len} cm)"
    )
    print(
        f"Banquettes : {len(polys['banquettes'])} → {banquette_sizes}"
    )
    # Comptage pondéré des dossiers : <=110cm → 0.5, >110cm → 1
    dossiers_count = _compute_dossiers_count(polys)
    dossiers_str = f"{int(dossiers_count)}" if abs(dossiers_count - int(dossiers_count)) < 1e-9 else f"{dossiers_count}"
    print(
        f"Dossiers : {dossiers_str} (+{add_split} via scission) | Accoudoirs : {len(polys['accoudoirs'])}"
    )
    print("Banquettes d’angle : 0")
    print(f"Traversins : {n_traversins} × 70x30")
    print(f"Coussins : {total_line}")
    turtle.done()

def render_U_v1(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    coussins="auto",
    window_title="U v1",
    traversins=None,
    couleurs=None,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Render a U‑shaped sofa variant v1, optionally with a méridienne.

    Validates that the méridienne does not conflict with an armrest on the
    same side or with a missing back, then delegates to the common render
    function. All parameters are forwarded along.
    """
    if meridienne_side == "g":
        if acc_left:
            raise ValueError(
                "Méridienne gauche interdite avec accoudoir gauche."
            )
        if not dossier_left:
            raise ValueError(
                "Méridienne gauche impossible sans dossier gauche."
            )
    if meridienne_side == "d":
        if acc_right:
            raise ValueError(
                "Méridienne droite interdite avec accoudoir droit."
            )
        if not dossier_right:
            raise ValueError(
                "Méridienne droite impossible sans dossier droit."
            )
    _render_common_U(
        "v1",
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
        coussins,
        window_title,
        compute_points_U_v1,
        build_polys_U_v1,
        traversins=traversins,
        couleurs=couleurs,
        meridienne_side=meridienne_side,
        meridienne_len=meridienne_len,
    )

def render_U_v2(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    coussins="auto",
    window_title="U v2",
    traversins=None,
    couleurs=None,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Render a U‑shaped sofa variant v2, with optional méridienne.
    Validations ensure the méridienne does not conflict with an armrest
    on the same side and that the relevant back exists.
    """
    if meridienne_side == "g":
        if acc_left:
            raise ValueError(
                "Méridienne gauche interdite avec accoudoir gauche."
            )
        if not dossier_left:
            raise ValueError(
                "Méridienne gauche impossible sans dossier gauche."
            )
    if meridienne_side == "d":
        if acc_right:
            raise ValueError(
                "Méridienne droite interdite avec accoudoir droit."
            )
        if not dossier_right:
            raise ValueError(
                "Méridienne droite impossible sans dossier droit."
            )
    _render_common_U(
        "v2",
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
        coussins,
        window_title,
        compute_points_U_v2,
        build_polys_U_v2,
        traversins=traversins,
        couleurs=couleurs,
        meridienne_side=meridienne_side,
        meridienne_len=meridienne_len,
    )

def render_U_v3(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    coussins="auto",
    window_title="U v3",
    traversins=None,
    couleurs=None,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Render a U‑shaped sofa variant v3, with optional méridienne.
    Performs the same validations as other variants before delegating
    to the common render function.
    """
    if meridienne_side == "g":
        if acc_left:
            raise ValueError(
                "Méridienne gauche interdite avec accoudoir gauche."
            )
        if not dossier_left:
            raise ValueError(
                "Méridienne gauche impossible sans dossier gauche."
            )
    if meridienne_side == "d":
        if acc_right:
            raise ValueError(
                "Méridienne droite interdite avec accoudoir droit."
            )
        if not dossier_right:
            raise ValueError(
                "Méridienne droite impossible sans dossier droit."
            )
    _render_common_U(
        "v3",
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
        coussins,
        window_title,
        compute_points_U_v3,
        build_polys_U_v3,
        traversins=traversins,
        couleurs=couleurs,
        meridienne_side=meridienne_side,
        meridienne_len=meridienne_len,
    )

def render_U_v4(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    coussins="auto",
    window_title="U v4",
    traversins=None,
    couleurs=None,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Render a U‑shaped sofa variant v4, with optional méridienne.
    Ensures the méridienne is compatible with armrests and backs before
    delegating to the common render routine.
    """
    if meridienne_side == "g":
        if acc_left:
            raise ValueError(
                "Méridienne gauche interdite avec accoudoir gauche."
            )
        if not dossier_left:
            raise ValueError(
                "Méridienne gauche impossible sans dossier gauche."
            )
    if meridienne_side == "d":
        if acc_right:
            raise ValueError(
                "Méridienne droite interdite avec accoudoir droit."
            )
        if not dossier_right:
            raise ValueError(
                "Méridienne droite impossible sans dossier droit."
            )
    _render_common_U(
        "v4",
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
        coussins,
        window_title,
        compute_points_U_v4,
        build_polys_U_v4,
        traversins=traversins,
        couleurs=couleurs,
        meridienne_side=meridienne_side,
        meridienne_len=meridienne_len,
    )

# ---------- AUTO sélection U ----------
def _metrics_U(
    variant,
    tx,
    ty_left,
    tz_right,
    profondeur,
    dossier_left,
    dossier_bas,
    dossier_right,
    acc_left,
    acc_bas,
    acc_right,
    meridienne_side=None,
    meridienne_len=0,
):
    """
    Compute metrics used to automatically select the best U‑shaped sofa variant.

    Returns a 4‑tuple:
      (nb_banquettes, scissions, nb_le_200, ok)

    - nb_banquettes : number of seat polygons after internal splits
    - scissions     : number of extra splits beyond the base 3 (left, bottom, right)
    - nb_le_200     : number of seats whose longest dimension ≤ 200 cm
    - ok            : True if no seat exceeds MAX_BANQUETTE (250 cm), False otherwise

    Additional parameters ``meridienne_side`` and ``meridienne_len`` are
    forwarded to the geometry computation to account for a méridienne.
    """
    comp = {
        "v1": compute_points_U_v1,
        "v2": compute_points_U_v2,
        "v3": compute_points_U_v3,
        "v4": compute_points_U_v4,
    }[variant]
    build = {
        "v1": build_polys_U_v1,
        "v2": build_polys_U_v2,
        "v3": build_polys_U_v3,
        "v4": build_polys_U_v4,
    }[variant]

    pts = comp(
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
        meridienne_side,
        meridienne_len,
    )
    polys, _ = build(
        pts,
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
    )

    nb_banquettes = len(polys["banquettes"])
    scissions = max(0, nb_banquettes - 3)

    # Check feasibility: no seat > 250 cm
    try:
        _assert_banquettes_max_250(polys)
        ok = True
    except ValueError:
        ok = False

    # Count seats with largest dimension ≤ 200 cm
    nb_le_200 = sum(
        1 for p in polys["banquettes"] if banquette_dims(p)[0] <= 200
    )

    return nb_banquettes, scissions, nb_le_200, ok

def render_U(
    tx,
    ty_left,
    tz_right,
    profondeur=DEPTH_STD,
    dossier_left=True,
    dossier_bas=True,
    dossier_right=True,
    acc_left=True,
    acc_bas=True,
    acc_right=True,
    coussins="auto",
    variant="auto",
    traversins=None,
    couleurs=None,
    window_title="U — auto",
    meridienne_side=None,
    meridienne_len=0,
):
    """
    High‑level entry point to render a U‑shaped sofa. Automatically selects
    an appropriate variant unless one is specified, taking into account
    méridienne parameters. Validations ensure a méridienne does not
    conflict with armrests or absent backs.

    Parameters are the same as for individual render functions, with
    additional ``meridienne_side`` and ``meridienne_len``.
    """
    # Validate méridienne configuration
    if meridienne_side == "g":
        if acc_left:
            raise ValueError(
                "Méridienne gauche interdite avec accoudoir gauche."
            )
        if not dossier_left:
            raise ValueError(
                "Méridienne gauche impossible sans dossier gauche."
            )
    if meridienne_side == "d":
        if acc_right:
            raise ValueError(
                "Méridienne droite interdite avec accoudoir droit."
            )
        if not dossier_right:
            raise ValueError(
                "Méridienne droite impossible sans dossier droit."
            )

    v = (variant or "auto").lower()
    # If a specific variant is requested, delegate directly
    if v in ("v1", "v2", "v3", "v4"):
        return {
            "v1": render_U_v1,
            "v2": render_U_v2,
            "v3": render_U_v3,
            "v4": render_U_v4,
        }[v](
            tx,
            ty_left,
            tz_right,
            profondeur,
            dossier_left,
            dossier_bas,
            dossier_right,
            acc_left,
            acc_bas,
            acc_right,
            coussins,
            window_title=f"{window_title} [{v}]",
            traversins=traversins,
            couleurs=couleurs,
            meridienne_side=meridienne_side,
            meridienne_len=meridienne_len,
        )

    # Automatic variant selection
    variants = ["v1", "v2", "v3", "v4"]
    metrics = {
        vv: _metrics_U(
            vv,
            tx,
            ty_left,
            tz_right,
            profondeur,
            dossier_left,
            dossier_bas,
            dossier_right,
            acc_left,
            acc_bas,
            acc_right,
            meridienne_side,
            meridienne_len,
        )
        for vv in variants
    }

    # 1) Keep only feasible variants (no seat > 250 cm)
    ok_variants = [vv for vv in variants if metrics[vv][3]]
    if not ok_variants:
        raise ValueError(
            "Aucune variante U faisable (certaines banquettes resteraient > 250 cm). "
            "Ajustez les dimensions ou la profondeur pour respecter 250 cm par banquette."
        )

    # 2) Minimize number of seats
    min_b = min(metrics[vv][0] for vv in ok_variants)
    tied = [vv for vv in ok_variants if metrics[vv][0] == min_b]

    # 3) Among ties, maximize number of seats ≤ 200 cm
    if len(tied) > 1:
        max_le200 = max(metrics[vv][2] for vv in tied)
        tied = [vv for vv in tied if metrics[vv][2] == max_le200]

    # Final tie‑break: stable preference order
    choice = None
    for pref in ["v2", "v1", "v3", "v4"]:
        if pref in tied:
            choice = pref
            break
    if choice is None:
        choice = tied[0]

    # Delegate to the chosen variant
    return render_U(
        tx,
        ty_left,
        tz_right,
        profondeur,
        dossier_left,
        dossier_bas,
        dossier_right,
        acc_left,
        acc_bas,
        acc_right,
        coussins,
        variant=choice,
        traversins=traversins,
        couleurs=couleurs,
        window_title=window_title,
        meridienne_side=meridienne_side,
        meridienne_len=meridienne_len,
    )

# =====================================================================
# ===================  SIMPLE droit (S1)  =============================
# =====================================================================

def compute_points_simple_S1(tx,
                             profondeur=DEPTH_STD,
                             dossier=True,
                             acc_left=True, acc_right=True,
                             meridienne_side=None, meridienne_len=0):
    if meridienne_side == 'g' and acc_left:
        raise ValueError("Méridienne gauche interdite avec accoudoir gauche.")
    if meridienne_side == 'd' and acc_right:
        raise ValueError("Méridienne droite interdite avec accoudoir droit.")

    xL_in = ACCOUDOIR_THICK if acc_left  else 0
    xR_in = tx - (ACCOUDOIR_THICK if acc_right else 0)
    y_base = DOSSIER_THICK if dossier else 0
    # profondeur passée = profondeur d'assise
    prof_tot = profondeur + y_base  # profondeur TOTALE dossier + assise

    pts = {}
    # Axe Y du canapé : de 0 (sol) à prof_tot
    pts["Ay"]  = (0, 0);          pts["Ay2"] = (0, prof_tot)
    pts["Ax"]  = (tx, 0);         pts["Ax2"] = (tx, prof_tot)
    # Banquette et assise : démarre à y_base et monte jusqu'à prof_tot
    pts["B0"]  = (xL_in, y_base); pts["By"]  = (xL_in, prof_tot)
    pts["Bx"]  = (xR_in, y_base); pts["Bx2"] = (xR_in, prof_tot)
    # Pieds avant au sol
    pts["D0"]  = (xL_in, 0);      pts["Dx"]  = (xR_in, 0)

    if meridienne_side == 'g' and meridienne_len > 0:
        start_x = min(max(xL_in + meridienne_len, xL_in), xR_in)
        pts["D0_m"] = (start_x, 0); pts["B0_m"] = (start_x, y_base)
    if meridienne_side == 'd' and meridienne_len > 0:
        end_x = max(min(xR_in - meridienne_len, xR_in), xL_in)
        pts["Dx_m"] = (end_x, 0); pts["Bx_m"] = (end_x, y_base)

    pts["_tx"] = tx
    # on conserve la profondeur d'assise dans _prof
    pts["_prof"] = profondeur
    return pts

def build_polys_simple_S1(pts, dossier=True, acc_left=True, acc_right=True,
                          meridienne_side=None, meridienne_len=0):
    polys = {"banquettes": [], "dossiers": [], "accoudoirs": []}
    # --- Ajout pour scission de dossier si banquette scindée ---
    mid_x = None

    ban = [pts["By"], pts["B0"], pts["Bx"], pts["Bx2"], pts["By"]]
    L = abs(pts["Bx"][0] - pts["B0"][0])
    split = False
    if L > SPLIT_THRESHOLD:
        split = True
        mid_x = _split_mid_int(pts["B0"][0], pts["Bx"][0])
        left  = [pts["By"], pts["B0"], (mid_x, pts["B0"][1]), (mid_x, pts["By"][1]), pts["By"]]
        right = [(mid_x, pts["By"][1]), (mid_x, pts["B0"][1]), pts["Bx"], pts["Bx2"], (mid_x, pts["By"][1])]
        polys["banquettes"] += [left, right]
    else:
        polys["banquettes"].append(ban)

    if dossier:
        x0, x1 = pts["D0"][0], pts["Dx"][0]
        if meridienne_side == 'g' and meridienne_len > 0: x0 = pts["D0_m"][0]
        if meridienne_side == 'd' and meridienne_len > 0: x1 = pts["Dx_m"][0]
        if x1 > x0 + 1e-6:
            # Si banquette scindée et mid_x tombe dans le segment → scinder le dossier aussi
            if (mid_x is not None) and (x0 < mid_x < x1):
                left_dossier  = [(x0,0), (mid_x,0), (mid_x,DOSSIER_THICK), (x0,DOSSIER_THICK), (x0,0)]
                right_dossier = [(mid_x,0), (x1,0), (x1,DOSSIER_THICK), (mid_x,DOSSIER_THICK), (mid_x,0)]
                polys["dossiers"] += [left_dossier, right_dossier]
            else:
                # sinon, un seul dossier
                polys["dossiers"].append([(x0,0),(x1,0),(x1,DOSSIER_THICK),(x0,DOSSIER_THICK),(x0,0)])

    if acc_left:
        if dossier:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By"], pts["D0"], pts["Ay"]])
        else:
            polys["accoudoirs"].append([pts["Ay"], pts["Ay2"], pts["By"], pts["B0"], pts["Ay"]])
    if acc_right:
        if dossier:
            polys["accoudoirs"].append([pts["Bx2"], pts["Dx"], pts["Ax"], pts["Ax2"], pts["Bx2"]])
        else:
            polys["accoudoirs"].append([pts["Bx2"], pts["Ax2"], pts["Ax"], pts["Bx"], pts["Bx2"]])

    polys["split_flags"]={"center":split}
    return polys

def _choose_cushion_size_auto_simple_S1(x0, x1):
    usable = max(0, x1 - x0)
    best, best_score = 65, (1e9, -1)
    for s in (65, 80, 90):
        waste = usable % s if usable > 0 else 0
        score = (waste, -s)
        if score < best_score:
            best_score, best = score, s
    return best

def _draw_coussins_simple_S1(t, tr, pts, size,
                             meridienne_side=None, meridienne_len=0,
                             traversins=None):
    x0 = pts["B0"][0]; x1 = pts["Bx"][0]
    if meridienne_side == 'g' and meridienne_len > 0:
        x0 = max(x0, pts.get("B0_m", (x0, 0))[0])
    if meridienne_side == 'd' and meridienne_len > 0:
        x1 = min(x1, pts.get("Bx_m", pts["Bx"])[0])
    if traversins:
        if "g" in traversins: x0 += TRAVERSIN_THK
        if "d" in traversins: x1 -= TRAVERSIN_THK

    def count(off):
        xs = x0 + off; xe = x1
        return int(max(0, xe - xs) // size)
    off = CUSHION_DEPTH if count(CUSHION_DEPTH) > count(0) else 0

    y = pts["B0"][1]
    x = x0 + off; n = 0
    while x + size <= x1 + 1e-6:
        poly = [(x, y), (x+size, y), (x+size, y+CUSHION_DEPTH), (x, y+CUSHION_DEPTH), (x, y)]
        draw_polygon_cm(t, tr, poly, fill=COLOR_CUSHION, outline=COLOR_CONTOUR, width=1)
        label_poly(t, tr, poly, f"{size}", font=FONT_CUSHION)
        x += size; n += 1
    return n

def render_Simple1(tx,
                   profondeur=DEPTH_STD,
                   dossier=True,
                   acc_left=True, acc_right=True,
                   meridienne_side=None, meridienne_len=0,
                   coussins="auto",
                   traversins=None,
                   couleurs=None,
                   window_title="Canapé simple 1"):
    pts   = compute_points_simple_S1(tx, profondeur, dossier, acc_left, acc_right,
                                     meridienne_side, meridienne_len)
    polys = build_polys_simple_S1(pts, dossier, acc_left, acc_right,
                                  meridienne_side, meridienne_len)
    _assert_banquettes_max_250(polys)

    trv = _parse_traversins_spec(traversins, allowed={"g","d"})
    legend_items = _resolve_and_apply_colors(couleurs)

    # profondeur totale pour l'affichage : dossier + assise
    y_base = DOSSIER_THICK if dossier else 0
    prof_tot = profondeur + y_base

    screen = turtle.Screen(); screen.setup(WIN_W, WIN_H)
    screen.title(f"{window_title} — tx={tx} / prof={profondeur} — méridienne {meridienne_side or '-'}={meridienne_len} — coussins={coussins}")
    t = turtle.Turtle(visible=False); t.speed(0); screen.tracer(False)
    # utiliser la profondeur totale pour le repère
    tr = WorldToScreen(tx, prof_tot, WIN_W, WIN_H, PAD_PX, ZOOM)

    # (Quadrillage et repères supprimés)

    for p in polys["dossiers"]:
        if _poly_has_area(p):  draw_polygon_cm(t, tr, p, fill=COLOR_DOSSIER)
    for p in polys["banquettes"]:
        draw_polygon_cm(t, tr, p, fill=COLOR_ASSISE)
    for p in polys["accoudoirs"]:
        draw_polygon_cm(t, tr, p, fill=COLOR_ACC)

    # Traversins + comptage (on travaille avec la profondeur totale)
    n_traversins = _draw_traversins_simple_S1(t, tr, pts, prof_tot, dossier, trv)

    # Flèche de profondeur = profondeur TOTALE (dossier + assise)
    # - avec dossier: prof_tot = profondeur + DOSSIER_THICK, ex : 80 cm
    # - sans dossier: prof_tot = profondeur, ex : 70 cm
    draw_double_arrow_vertical_cm(
        t, tr,
        -25,
        0,
        prof_tot,
        f"{prof_tot} cm"
    )
    # Largeur identique
    draw_double_arrow_horizontal_cm(t, tr, -25, 0, tx, f"{tx} cm")

    banquette_sizes = []
    for poly in polys["banquettes"]:
        L, P = banquette_dims(poly)
        banquette_sizes.append((L, P))
        # Première dimension sans unité avec un « x », seconde dimension avec « cm »
        text = f"{L}x\n{P} cm"
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bb_w = max(xs) - min(xs)
        bb_h = max(ys) - min(ys)
        # Décaler horizontalement si la banquette est plus haute que large, pour éloigner légèrement le texte des coussins
        # Offset réduit : 3 cm de moins que la version précédente
        if bb_h >= bb_w:
            label_poly_offset_cm(t, tr, poly, text, dx_cm=CUSHION_DEPTH + 7, dy_cm=0.0)
        else:
            label_poly(t, tr, poly, text)
    for p in polys["dossiers"]:
        if _poly_has_area(p): label_poly(t, tr, p, "10")
    for p in polys["accoudoirs"]:
        if _poly_has_area(p): label_poly(t, tr, p, "15")

    # ===== COUSSINS =====
    spec = _parse_coussins_spec(coussins)
    if spec["mode"] == "auto":
        x0 = pts.get("B0_m", pts["B0"])[0] if meridienne_side == 'g' else pts["B0"][0]
        x1 = pts.get("Bx_m", pts["Bx"])[0] if meridienne_side == 'd' else pts["Bx"][0]
        if trv:
            if "g" in trv: x0 += TRAVERSIN_THK
            if "d" in trv: x1 -= TRAVERSIN_THK
        size = _choose_cushion_size_auto_simple_S1(x0, x1)
        nb_coussins = _draw_coussins_simple_S1(t, tr, pts, size, meridienne_side, meridienne_len, traversins=trv)
        total_line = f"{coussins} → {nb_coussins} × {size} cm"
    elif spec["mode"] == "fixed":
        size = int(spec["fixed"])
        nb_coussins = _draw_coussins_simple_S1(t, tr, pts, size, meridienne_side, meridienne_len, traversins=trv)
        total_line = f"{coussins} → {nb_coussins} × {size} cm"
    else:
        best = _optimize_valise_simple(pts, spec["range"], meridienne_side, meridienne_len, traversins=trv)
        if not best:
            raise ValueError("Aucune configuration valise valide pour S1.")
        size = best["size"]
        nb_coussins = _draw_simple_with_size(t, tr, pts, size, meridienne_side, meridienne_len, traversins=trv)
        total_line = f"{nb_coussins} × {size} cm"

    # Légende
    draw_legend(t, tr, tx, profondeur, items=legend_items, pos="top-right")

    screen.tracer(True); t.hideturtle()
    add_split = int(polys.get("split_flags",{}).get("center",False) and dossier)
    print("=== Rapport Canapé simple 1 ===")
    print(f"Dimensions : {tx}×{profondeur} cm")
    print(f"Banquettes : {len(polys['banquettes'])} → {banquette_sizes}")
    # Comptage pondéré des dossiers : <=110cm → 0.5, >110cm → 1
    dossiers_count = _compute_dossiers_count(polys)
    dossiers_str = f"{int(dossiers_count)}" if abs(dossiers_count - int(dossiers_count)) < 1e-9 else f"{dossiers_count}"
    print(f"Dossiers   : {dossiers_str} (+{add_split} via scission)  |  Accoudoirs : {len(polys['accoudoirs'])}")
    print(f"Banquettes d’angle : 0")
    print(f"Traversins : {n_traversins} × 70x30")
    print(f"Coussins   : {total_line}")
    if meridienne_side:
        print(f"Méridienne : côté {'gauche' if meridienne_side=='g' else 'droit'} — {meridienne_len} cm")
    turtle.done()

# =====================================================================
# =====================  TESTS ÉTENDUS (30)  ==========================
# =====================================================================




def TEST_22_LNF_v1_mer_bas_split_TRb_gs():
    render_LNF(
        tx=250, ty=260, profondeur=70,
        dossier_left=True, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="p", variant="v2",
        traversins="None",
        window_title="T22 — LNF v1 | méridienne bas | split bas | g:s | TR bas"
    )


def TEST_23_LNF_v1_grand_scission_valise_TRgb_palette():
    render_LNF(
        tx=540, ty=360, profondeur=70,
        dossier_left=True, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="valise", variant="v1",
        traversins="g,b",
        couleurs="accoudoirs:gris foncé; assise:gris très clair presque blanc; coussins:#8B7E74",
        window_title="T23 — LNF v1 | grandes longueurs | valise | TR G+B | palette"
    )


def TEST_24_LNF_v2_mer_gauche_split_TRg_ps():
    render_LNF(
        tx=280, ty=360, profondeur=70,
        dossier_left=True, dossier_bas=True,
        acc_left=False, acc_bas=True,               # méridienne gauche -> pas d'accoudoir gauche (déjà OFF)
        meridienne_side='g', meridienne_len=90,
        coussins="p:s", variant="v2",
        traversins="g",
        window_title="T24 — LNF v2 | méridienne G 90 | split gauche | p:s | TR G"
    )


def TEST_25_LNF_v2_mer_bas_split_TRb_auto():
    render_LNF(
        tx=520, ty=280, profondeur=80,
        dossier_left=True, dossier_bas=True,
        acc_left=True, acc_bas=False,               # méridienne bas -> pas d'accoudoir bas
        meridienne_side='b', meridienne_len=140,
        coussins="auto", variant="v2",
        traversins="b",
        window_title="T25 — LNF v2 | méridienne bas 140 | split bas | auto | TR bas"
    )


def TEST_26_LF_mer_bas_TRgb_palette_dict():
    render_LF_variant(
        tx=420, ty=440, profondeur=80,
        dossier_left=False, dossier_bas=True,
        acc_left=True, acc_bas=False,               # méridienne bas -> pas d'accoudoir bas
        meridienne_side='b', meridienne_len=50,
        coussins="90", traversins="",
        couleurs={"accoudoirs": "anthracite", "assise": "crème", "coussins": "#c0ffee"},
        window_title="T26 — LF | méridienne bas 100 | TR G+B | palette dict"
    )


def TEST_27_LF_valise_sans_mer_TRg_split():
    render_LF_variant(
        tx=500, ty=500, profondeur=70,
        dossier_left=True, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="valise", traversins="g",
        window_title="T27 — LF | valise | sans méridienne | TR G | grandes longueurs"
    )


def TEST_28_S1_TR_both_auto_palette():
    render_Simple1(
        tx=260, profondeur=70, dossier=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="auto", traversins="g,d",
        couleurs="accoudoirs:#444444; assise:#f0f0f0; coussins:#b38b6d",
        window_title="T28 — S1 | dossier | TR G+D | auto | palette"
    )


def TEST_29_S1_mer_droite_120_no_accR_90_TRg():
    render_Simple1(
        tx=320, profondeur=70, dossier=True,
        acc_left=True, acc_right=False,             # méridienne droite -> pas d'accoudoir droit
        meridienne_side='d', meridienne_len=120,
        coussins="90", traversins="g",
        couleurs=None,
        window_title="T29 — S1 | méridienne D 120 | accR OFF | 90 | TR G"
    )


def TEST_30_U_v1_left_TRg_auto_no_dossier_droit():
    render_U(
        tx=240, ty_left=260, tz_right=260, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=False, acc_bas=True, acc_right=False,
        coussins="p", variant="v4", traversins=None,
        meridienne_side='d', meridienne_len=20,
        window_title="T30 — U v1 | pas de dossier droit | TR G | auto"
    )


def TEST_31_U_v1_TR_both_80_palette():
    render_U(
        tx=420, ty_left=400, tz_right=420, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_bas=True, acc_right=True,
        coussins="auto", variant="v4", traversins="",
        couleurs="accoudoirs:#333333; assise:#f5f5f5; coussins:#a67c52",
        window_title="T31 — U v1 | TR G+D | 80 | palette"
    )


def TEST_32_U_auto_valise_g():
    render_U(
        tx=520, ty_left=420, tz_right=420, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_bas=True, acc_right=True,
        coussins="valise", variant="auto", traversins="g",
        couleurs=None,
        window_title="T32 — U auto | valise g"
    )


def TEST_33_U_v3_valise_p_sans_TR():
    render_U(
        tx=460, ty_left=380, tz_right=360, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_bas=True, acc_right=True,
        coussins="p", variant="v3", traversins=None,
        couleurs=None,
        window_title="T33 — U v3 | valise p | sans TR"
    )


def TEST_34_U_v4_TR_both_75_palette_hex():
    render_U(
        tx=300, ty_left=400, tz_right=480, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_bas=True, acc_right=True,
        coussins="75", variant="v4", traversins="g,d",
        couleurs="accoudoirs:#4b4b4b; assise:#f6f6f6; coussins:#8B7E74",
        window_title="T34 — U v4 | TR G+D | 75 | palette hex"
    )


def TEST_35_U2F_mer_g_120_no_accL_s_TRd():
    render_U2f_variant(
        tx=520, ty_left=450, tz_right=450, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=False, acc_bas=True, acc_right=True,   # méridienne gauche -> pas d'accoudoir gauche
        meridienne_side='g', meridienne_len=120,
        coussins="s", traversins="d",
        window_title="T35 — U2F | méridienne G 120 | accL OFF | s | TR D"
    )


def TEST_36_U2F_mer_d_100_no_accR_80_TRg():
    render_U2f_variant(
        tx=520, ty_left=420, tz_right=330, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_bas=True, acc_right=False,   # méridienne droite -> pas d'accoudoir droit
        meridienne_side='d', meridienne_len=100,
        coussins="g", traversins="g",
        window_title="T36 — U2F | méridienne D 100 | accR OFF | 80 | TR G"
    )


def TEST_37_U2F_valise_same_TR_both():
    render_U2f_variant(
        tx=560, ty_left=540, tz_right=520, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=False, acc_bas=True, acc_right=True,
        meridienne_side='g', meridienne_len=50,
        coussins="g:s", traversins="g,d",
        window_title="T37 — U2F | valise g:s | TR G+D"
    )


def TEST_38_U1F_v1_mer_g_90_no_accL_p_TRd():
    render_U1F(
        tx=400, ty_left=280, tz_right=300, profondeur=70,
        dossier_left=False, dossier_bas=False, dossier_right=True,
        acc_left=False, acc_right=True,                  # méridienne gauche -> pas d'accoudoir gauche
        meridienne_side='g', meridienne_len=90,
        coussins="p", variant="v1",
        traversins="d",
        window_title="T38 — U1F v1 | méridienne G 90 | accL OFF | p | TR D"
    )


def TEST_39_U1F_v2_mer_d_110_no_accR_65_TRg():
    render_U1F(
        tx=520, ty_left=400, tz_right=420, profondeur=80,
        dossier_left=False, dossier_bas=False, dossier_right=True,
        acc_left=True, acc_right=False,                 # méridienne droite -> pas d'accoudoir droit
        meridienne_side='d', meridienne_len=110,
        coussins="65", variant="v2",
        traversins="g",
        window_title="T39 — U1F v2 | méridienne D 110 | accR OFF | 65 | TR G"
    )


def TEST_40_U1F_v3_TR_both_valise_g_palette():
    render_U1F(
        tx=380, ty_left=320, tz_right=300, profondeur=70,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="g", variant="v3",
        traversins="g,d",
        couleurs={"accoudoirs": "gris", "assise": "crème", "coussins": "taupe"},
        window_title="T40 — U1F v3 | TR G+D | valise g | palette dict"
    )


def TEST_41_U1F_v4_valise_TRg():
    render_U1F(
        tx=400, ty_left=280, tz_right=320, profondeur=70,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="valise", variant="v4",
        traversins="g",
        window_title="T41 — U1F v4 | valise | TR G"
    )


def TEST_42_U1F_v4_auto_sans_TR():
    render_U1F(
        tx=460, ty_left=400, tz_right=480, profondeur=70,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="auto", variant="v4",
        traversins=None,
        window_title="T42 — U1F v4 | auto | pas de TR"
    )


def TEST_43_U1F_v2_grand_split_TRg_palette():
    render_U1F(
        tx=520, ty_left=450, tz_right=430, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="p:s", variant="v2",
        traversins="g",
        couleurs="accoudoirs:anthracite; assise:gris très clair; coussins:#e0d9c7",
        window_title="T43 — U1F v2 | grandes longueurs (scissions) | p:s | TR G | palette"
    )


def TEST_44_U1F_v3_split_droite_TRd_ps():
    render_U1F(
        tx=460, ty_left=300, tz_right=360, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="p:s", variant="v3",
        traversins="d",
        window_title="T44 — U1F v3 | split droite | p:s | TR D"
    )


def TEST_45_U1F_v4_TR_both_90_palette_dict():
    render_U1F(
        tx=420, ty_left=300, tz_right=300, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="90", variant="v4",
        traversins="g,d",
        couleurs={"accoudoirs": "gris", "assise": "blanc", "coussins": "#8B7E74"},
        window_title="T45 — U1F v4 | TR G+D | 90 | palette dict"
    )


def TEST_46_LNF_v1_palette_lighten_dossiers_auto():
    render_LNF(
        tx=300, ty=280, profondeur=70,
        dossier_left=True, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="80", variant="v1",
        traversins=None,
        couleurs={"accoudoirs": "anthracite fonce", "assise": "gris très clair", "coussins": "#b5651d"},
        window_title="T46 — LNF v1 | palette lighten dossiers auto"
    )


def TEST_47_LNF_v2_palette_string_accents_TRb():
    render_LNF(
        tx=320, ty=300, profondeur=80,
        dossier_left=True, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="auto", variant="v2",
        traversins="b",
        couleurs="accoudoirs:gris; dossiers:gris clair; assise:crème; coussins:taupe",
        window_title="T47 — LNF v2 | palette string (accents) | TR bas"
    )


def TEST_48_S1_sans_dossier_TR_both_auto():
    render_Simple1(
        tx=300, profondeur=70, dossier=False,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="auto", traversins="g,d",
        couleurs=None,
        window_title="T48 — S1 | sans dossier | TR G+D | auto"
    )


def TEST_49_LF_valise_same_TRg():
    render_LF_variant(
        tx=460, ty=460, profondeur=70,
        dossier_left=True, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="valise", traversins="g",
        couleurs=None,
        window_title="T49 — LF | valise | TR G | mêmes longueurs"
    )


def TEST_50_U_v2_valise_same_TRg_palette():
    render_U(
        tx=460, ty_left=460, tz_right=460, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_bas=True, acc_right=True,
        coussins="valise", variant="v2", traversins="g",
        couleurs="accoudoirs:#444444; assise:#f0f0f0; coussins:#b38b6d",
        window_title="T50 — U v2 | valise | TR G | mêmes longueurs | palette"
    )


def TEST_51_LNF_auto_dossier_bas_seul_TRb():
    # LNF : uniquement dossier bas, choix de variante automatique
    render_LNF(
        tx=280, ty=220, profondeur=70,
        dossier_left=False, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="auto", variant="auto",
        traversins="b",
        couleurs="accoudoirs:gris; assise:gris très clair; coussins:taupe",
        window_title="T51 — LNF auto | dossier bas seul | TR bas"
    )


def TEST_52_LNF_auto_dossier_gauche_seul_TRg_palette_dict():
    # LNF : uniquement dossier gauche, test de variant=auto + palette dictionnaire
    render_LNF(
        tx=240, ty=360, profondeur=70,
        dossier_left=False, dossier_bas=True,
        acc_left=True, acc_bas=True,
        meridienne_side=None, meridienne_len=0,
        coussins="65", variant="auto",
        traversins=None,
        couleurs={"accoudoirs": "anthracite",
                  "assise": "gris très clair",
                  "coussins": "#c8ad7f"},
        window_title="T52 — LNF auto | dossier gauche seul | TR G | palette dict"
    )


def TEST_53_U1F_auto_TR_both_auto_palette():
    # U1F : 3 dossiers, TR gauche + droite, choix auto de la variante
    render_U1F(
        tx=520, ty_left=360, tz_right=380, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="auto", variant="auto",
        traversins="g,d",
        couleurs="accoudoirs:gris foncé; assise:gris très clair; coussins:taupe",
        window_title="T53 — U1F auto | TR G+D | palette"
    )


def TEST_54_U1F_v3_dossiers_gauche_et_bas_TRg():
    # U1F : variante v3 forcée, dossiers gauche + bas uniquement
    render_U1F(
        tx=420, ty_left=320, tz_right=280, profondeur=75,
        dossier_left=True, dossier_bas=True, dossier_right=False,
        acc_left=True, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="p", variant="v3",
        traversins="g",
        window_title="T54 — U1F v3 | dossiers G+bas | TR G"
    )


def TEST_55_U1F_v4_dossier_droit_seul_TRd_palette():
    # U1F : variante v4 forcée, uniquement dossier droit (cas limite pour D5 / couture Dx2–Bx)
    render_U1F(
        tx=450, ty_left=280, tz_right=340, profondeur=70,
        dossier_left=False, dossier_bas=False, dossier_right=True,
        acc_left=False, acc_right=True,
        meridienne_side=None, meridienne_len=0,
        coussins="s", variant="v4",
        traversins="d",
        couleurs="accoudoirs:gris; assise:blanc cassé; coussins:#b5651d",
        window_title="T55 — U1F v4 | dossier droit seul | TR D | palette"
    )

def TEST_56_U_v1_mer_g_120_no_accL_TRg():
    """
    U v1 avec méridienne gauche 120 cm :
    - dossier gauche et bas présents
    - pas d'accoudoir gauche (acc_left=False obligatoire)
    - méridienne sur branche gauche (meridienne_side='g')
    - traversin à gauche
    """
    render_U(
        tx=520, ty_left=450, tz_right=420, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=False, acc_bas=True, acc_right=True,
        meridienne_side="g", meridienne_len=120,
        coussins="auto", variant="v1",
        traversins="g",
        couleurs="accoudoirs:anthracite; assise:gris très clair; coussins:taupe",
        window_title="T56 — U v1 | méridienne G 120 | accL OFF | TR G"
    )


def TEST_57_U_v2_mer_d_100_no_accR_TRd():
    """
    U v2 avec méridienne droite 100 cm :
    - dossier droit et bas présents
    - pas d'accoudoir droit (acc_right=False obligatoire)
    - méridienne sur branche droite (meridienne_side='d')
    - traversin à droite
    """
    render_U(
        tx=580, ty_left=430, tz_right=460, profondeur=80,
        dossier_left=True, dossier_bas=True, dossier_right=True,
        acc_left=True, acc_bas=True, acc_right=False,
        meridienne_side="d", meridienne_len=100,
        coussins="80", variant="v2",
        traversins="d",
        couleurs="accoudoirs:#444444; assise:#f0f0f0; coussins:#b38b6d",
        window_title="T57 — U v2 | méridienne D 100 | accR OFF | TR D"
    )

if __name__ == "__main__":
    #TEST_21_LNF_v1_mer_gauche_split_TRg_p()
    #TEST_22_LNF_v1_mer_bas_split_TRb_gs()
    #TEST_23_LNF_v1_grand_scission_valise_TRgb_palette()
    #TEST_24_LNF_v2_mer_gauche_split_TRg_ps()
    #TEST_25_LNF_v2_mer_bas_split_TRb_auto()
    #TEST_26_LF_mer_bas_TRgb_palette_dict()
    #TEST_27_LF_valise_sans_mer_TRg_split()
    #TEST_28_S1_TR_both_auto_palette()
    #TEST_29_S1_mer_droite_120_no_accR_90_TRg()
    #TEST_30_U_v1_left_TRg_auto_no_dossier_droit()
    #TEST_31_U_v1_TR_both_80_palette()
    #TEST_32_U_auto_valise_g()
    #TEST_33_U_v3_valise_p_sans_TR()
    #TEST_34_U_v4_TR_both_75_palette_hex()
    #TEST_35_U2F_mer_g_120_no_accL_s_TRd()
    TEST_36_U2F_mer_d_100_no_accR_80_TRg()
    #TEST_37_U2F_valise_same_TR_both()
    #TEST_38_U1F_v1_mer_g_90_no_accL_p_TRd()
    #TEST_39_U1F_v2_mer_d_110_no_accR_65_TRg()
    #TEST_40_U1F_v3_TR_both_valise_g_palette()
    #TEST_41_U1F_v4_valise_TRg()
    #TEST_42_U1F_v4_auto_sans_TR()
    #TEST_43_U1F_v2_grand_split_TRg_palette()
    #TEST_44_U1F_v3_split_droite_TRd_ps()
    #TEST_45_U1F_v4_TR_both_90_palette_dict()
    #TEST_46_LNF_v1_palette_lighten_dossiers_auto()
    #TEST_47_LNF_v2_palette_string_accents_TRb()
    #TEST_48_S1_sans_dossier_TR_both_auto()
    #TEST_49_LF_valise_same_TRg()
    #TEST_50_U_v2_valise_same_TRg_palette()
    #TEST_51_LNF_auto_dossier_bas_seul_TRb()
    #TEST_52_LNF_auto_dossier_gauche_seul_TRg_palette_dict()
    #TEST_53_U1F_auto_TR_both_auto_palette()
    #TEST_54_U1F_v3_dossiers_gauche_et_bas_TRg()
    #TEST_55_U1F_v4_dossier_droit_seul_TRd_palette()
    #TEST_56_U_v1_mer_g_120_no_accL_TRg()
    #TEST_57_U_v2_mer_d_100_no_accR_TRd()
    pass
