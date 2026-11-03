#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A.C.O.S. TREVIGLIO CALCIO 1971 — v5.0 "TOP-CLUB STADIUM BROADCAST EDITION"
===========================================================================
Generatore master full-stack per il sito ufficiale di A.S.D. A.C.O.S. Treviglio Calcio (dal 1971).
Architettura UI/UX ispirata ai top club europei (Inter.it, Borussia Dortmund BVB.de, Juventus.com):
1. Estrazione automatica dello Stemma Ovale Ufficiale A.C.O.S. (con l'elefantino giallonero)
   da logo.jpg con rimozione dello sfondo bianco esterno e generazione di PNG trasparente RGBA
   (crest_oval.png) incorporato nativamente in Base64 + cornice vettoriale Oro 24k.
2. Full-Bleed Stadium Hero (88vh) con carosello fotografico cinematografico a 3 slide (Gothia Cup
   Ullevi Stadium Fireworks, Trionfo Torneo Cassera, Giovani Gialloneri in campo), effetto Ken Burns,
   watermark cinetico "1971 • TREVIGLIO" e HUD Broadcast Scoreboard + Countdown Live sul Hero.
3. Live Broadcast Ticker (stile Sky Sport24 / UEFA) con scorrimento continuo dei 13 risultati.
4. Match Center interattivo con schede televisive (stemmi club, punteggi LED, filtri per categoria,
   tab Ultimi Risultati [13] e Prossimo Turno [9]).
5. Poster Card visive per tutte le 15 Squadre (dalla Promozione ai Piccoli Amici 2020) con foto
   di sfondo, watermark annata/categoria, ultimo risultato, prossimo turno e concierge WhatsApp.
6. Scuola Calcio Riconosciuta FIGC, Partnership Atalanta B.C., Progetto Vitalis e Torneo Viganò.
7. Storia 1966-2026, Organigramma, Gothia Cup (Svezia & Cina) e Cuore Giallonero (18 ONLUS).
8. Segreteria Digitale: Calcolatore Quote 2025/2026, IBAN one-click copy, Kit Remels, Sinistri LND/SGS,
   Safeguarding (D.Lgs. 36/2021 e 39/2021 — Resp. Francesco Scrivanti) e Mappe dei 2 Stadi.
"""

import base64
import json
import math
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

BASE_DIR = Path("/Users/antonacim/Local Sites/calcio/acos-studio")
ASSETS_DIR = BASE_DIR / "assets"
INDEX_OUT = BASE_DIR / "index.html"
SIM_OUT = BASE_DIR / "simulazione_acos.html"


# ==============================================================================
# 0. ESTRAZIONE STEMMA OVALE TRASPARENTE (RGBA PNG) DA LOGO.JPG
# ==============================================================================
def encode_rgba_png(width: int, height: int, rgba_rows: list) -> bytes:
    def make_chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + row for row in rgba_rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", zlib.compress(raw, 9))
        + make_chunk(b"IEND", b"")
    )


def epx_scale2x(grid: list, w: int, h: int):
    """Upscaler 2x EPX (Edge-Preserving) per contorni nitidi senza sfocatura JPEG."""
    out = [[(252, 224, 22, 255) for _ in range(w * 2)] for _ in range(h * 2)]

    def same(c1, c2):
        return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2]) < 65

    def blend(c1, c2):
        return (
            (c1[0] + c2[0]) // 2,
            (c1[1] + c2[1]) // 2,
            (c1[2] + c2[2]) // 2,
            255,
        )

    for y in range(h):
        for x in range(w):
            p = grid[y][x]
            a = grid[max(0, y - 1)][x]
            b = grid[y][min(w - 1, x + 1)]
            c = grid[y][max(0, x - 1)]
            d = grid[min(h - 1, y + 1)][x]

            p1, p2, p3, p4 = p, p, p, p
            if same(c, a) and not same(c, d) and not same(a, b):
                p1 = blend(p, blend(c, a))
            if same(a, b) and not same(a, c) and not same(b, d):
                p2 = blend(p, blend(a, b))
            if same(d, c) and not same(d, b) and not same(c, a):
                p3 = blend(p, blend(d, c))
            if same(b, d) and not same(b, a) and not same(d, c):
                p4 = blend(p, blend(b, d))

            out[y * 2][x * 2] = p1
            out[y * 2][x * 2 + 1] = p2
            out[y * 2 + 1][x * 2] = p3
            out[y * 2 + 1][x * 2 + 1] = p4
    return out, w * 2, h * 2


def extract_transparent_oval_crest() -> str:
    """
    Ricostruisce lo Stemma Ovale Ufficiale A.C.O.S. Treviglio in Alta Definizione (SVG Ibrido):
    - Estrae la mascotte storica originale (l'elefantino giallonero con il pallone) da logo.jpg
      (x=13..65, y=28..81), rimuovendo gli artefatti JPEG dello sfondo giallo e applicando
      super-risoluzione 4x EPX edge-preserving.
    - Ricostruisce in vettoriale 100% nitido l'ovale giallonero, le calotte nere superiore/inferiore
      e i testi "A.C.O.S." e "TREVIGLIO CALCIO" (che nel JPEG 78x110px del 2013 erano alti solo 5px).
    """
    logo_jpg = ASSETS_DIR / "logo.jpg"
    if not logo_jpg.exists():
        alt_logo = Path("/Users/antonacim/.gemini/antigravity/brain/d9b03909-66a0-4e21-9f45-f0ff00cfeaaa/scratch/logo.jpg")
        if alt_logo.exists():
            logo_jpg = alt_logo
        else:
            return ""

    bmp_tmp = Path("/tmp/_acos_logo_mascot.bmp")
    try:
        subprocess.run(
            ["sips", "-s", "format", "bmp", str(logo_jpg), "--out", str(bmp_tmp)],
            check=True,
            capture_output=True,
        )
        data = bmp_tmp.read_bytes()
        bmp_tmp.unlink(missing_ok=True)

        pixel_offset = struct.unpack_from("<I", data, 10)[0]
        w, h = struct.unpack_from("<ii", data, 18)
        bpp = struct.unpack_from("<H", data, 28)[0]
        top_down = h < 0
        h = abs(h)
        bytes_per_px = bpp // 8
        row_stride = ((w * bytes_per_px + 3) // 4) * 4

        def get_rgb(x: int, y: int):
            bmp_y = y if top_down else (h - 1 - y)
            pos = pixel_offset + bmp_y * row_stride + x * bytes_per_px
            b, g, r = data[pos], data[pos + 1], data[pos + 2]
            return r, g, b

        x0, x1 = 13, 65
        y0, y1 = 28, 81
        mw = x1 - x0 + 1
        mh = y1 - y0 + 1
        bg_r, bg_g, bg_b = 252, 226, 22

        grid = []
        for y in range(mh):
            row = []
            for x in range(mw):
                r, g, b = get_rgb(x0 + x, y0 + y)
                dist_bg = math.sqrt((r - bg_r) ** 2 + (g - bg_g) ** 2 + (b - bg_b) ** 2)
                if dist_bg < 30:
                    row.append((252, 224, 22, 255))
                else:
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    if lum < 98:
                        f = max(0.0, (lum - 22) / 76.0)
                        nr = int(r * f * 0.45)
                        ng = int(g * f * 0.45)
                        nb = int(b * f * 0.45)
                        row.append((nr, ng, nb, 255))
                    elif lum > 210 and (r - b) < 48:
                        row.append((255, 255, 255, 255))
                    else:
                        row.append((r, g, b, 255))
            grid.append(row)

        grid, mw, mh = epx_scale2x(grid, mw, mh)
        grid, mw, mh = epx_scale2x(grid, mw, mh)

        rgba_rows = []
        for y in range(mh):
            row_bytes = bytearray()
            for x in range(mw):
                row_bytes.extend(grid[y][x])
            rgba_rows.append(bytes(row_bytes))

        mascot_png = encode_rgba_png(mw, mh, rgba_rows)
        mascot_uri = f"data:image/png;base64,{base64.b64encode(mascot_png).decode('ascii')}"

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 320" width="260" height="320">
  <defs>
    <clipPath id="ovalClip">
      <ellipse cx="130" cy="160" rx="118" ry="148" />
    </clipPath>
    <linearGradient id="goldRim" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFF59D" />
      <stop offset="45%" stop-color="#FCE016" />
      <stop offset="100%" stop-color="#C89600" />
    </linearGradient>
  </defs>
  <ellipse cx="130" cy="160" rx="126" ry="156" fill="url(#goldRim)" />
  <ellipse cx="130" cy="160" rx="121" ry="151" fill="#111111" />
  <g clip-path="url(#ovalClip)">
    <rect x="0" y="0" width="260" height="320" fill="#FCE016" />
    <rect x="0" y="0" width="260" height="74" fill="#141414" />
    <line x1="0" y1="74" x2="260" y2="74" stroke="#000000" stroke-width="4" />
    <rect x="0" y="238" width="260" height="86" fill="#141414" />
    <line x1="0" y1="238" x2="260" y2="238" stroke="#000000" stroke-width="4" />
    <image href="{mascot_uri}" x="44" y="76" width="172" height="160" preserveAspectRatio="xMidYMid meet" />
    <text x="130" y="58" text-anchor="middle" fill="#FCE016" font-family="'Arial Black', 'Barlow Condensed', Impact, sans-serif" font-weight="900" font-style="italic" font-size="30" letter-spacing="1.5">A.C.O.S.</text>
    <text x="130" y="266" text-anchor="middle" fill="#FCE016" font-family="'Arial Black', 'Barlow Condensed', Impact, sans-serif" font-weight="900" font-size="22" letter-spacing="1.4">TREVIGLIO</text>
    <text x="130" y="292" text-anchor="middle" fill="#FCE016" font-family="'Arial Black', 'Barlow Condensed', Impact, sans-serif" font-weight="900" font-size="20.5" letter-spacing="2.2">CALCIO</text>
  </g>
  <ellipse cx="130" cy="160" rx="118" ry="148" fill="none" stroke="#141414" stroke-width="5.5" />
</svg>"""
        svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{svg_b64}"
    except Exception as exc:
        print(f"[WARN] Fallback crest extraction: {exc}")
        raw = logo_jpg.read_bytes()
        return f"data:image/jpeg;base64,{base64.b64encode(raw).decode('ascii')}"


# ==============================================================================
# 1. DATI UFFICIALI COMPLETI A.S.D. A.C.O.S. TREVIGLIO CALCIO (DAL 1971)
# ==============================================================================
CLUB_DATA = {
    "name": "A.S.D. A.C.O.S. Treviglio Calcio",
    "short_name": "A.C.O.S. Treviglio",
    "meaning": "Associazione Calcistica Operai e Studenti",
    "founded": "18 Agosto 1971",
    "roots_year": "1966 (Castel Cerreto)",
    "motto": "La terra trema, il cielo si oscura, ma l'Acos non ha paura",
    "colors": "Giallo / Nero",
    "cf_piva": "02115860161",
    "matricola_figc": "676164",
    "hq_name": 'Centro Sportivo "Ambrogio Mazza" (Campo Enzo Riganti)',
    "hq_address": "Via ai Malgari, 6 — 24047 Treviglio (BG)",
    "stadium_name": 'Stadio Comunale "Mario Zanconti"',
    "stadium_address": "Via Milano, 7 — 24047 Treviglio (BG)",
    "phone": "0363 304036",
    "phone_clean": "+390363304036",
    "scuola_calcio_resp": "Sig. Pierangelo Gusmini",
    "scuola_mobile": "348 7929125",
    "scuola_mobile_clean": "393487929125",
    "email": "info@acos.it",
    "iban": "IT72U 05034 53640 000000012350",
    "iban_clean": "IT72U0503453640000000012350",
    "iban_holder": "A.C.O.S. TREVIGLIO CALCIO C/O STUDIO PROFESSIONALE VIGANO'",
    "facebook": "https://www.facebook.com/acostrevigliocalcio",
    "instagram": "https://www.instagram.com/acos_treviglio_calcio/",
    "remels_url": "https://www.remelssport.com/",
    "remels_guide_pdf": "http://www.acos.it/files/2022/GUIDA-PORTALE-ACQUISTI-REMELS.pdf",
    "autocert_pdf": "http://www.acos.it/files/documents/2019/AUTOCERTIFICAZIONE.pdf",
    "safeguarding_modello_url": "https://drive.google.com/file/d/1ew3so4PM2ZYxz-E94XPx1_YWPG4nR2pv/view",
    "safeguarding_codice_url": "https://drive.google.com/file/d/1__4fwW-1liI_lC5NWNRZ_uM6c_X9VEXn/view",
    "safeguarding_responsabile": "Sig. Francesco Scrivanti (Segretario dal 01/07/2006 — in carica fino al 31/12/2026)",
    "lnd_sinistri_url": "https://www.onecare.aon.it/login?usertype=lnd",
    "sgs_sinistri_url": "https://figc.eclaim.cloud/",
    "figc_tutela_url": "https://www.figc-tutelaminori.it/",
}

TEAMS = [
    {
        "id": 1,
        "code": "1ª",
        "name": "Promozione",
        "category": "Campionato Regionale Promozione",
        "macro": "agonistica",
        "macro_label": "Prima Squadra · LND",
        "annata": "Seniores",
        "campionato": "LND Lombardia — Promozione",
        "stadio": 'Stadio Comunale "Mario Zanconti" (Via Milano, 7)',
        "allenamenti": "Centro Sportivo Mazza / Stadio Zanconti",
        "bg_img": "assets/event_239.jpg",
        "desc": "La Prima Squadra giallonera protagonista nel campionato regionale di Promozione lombarda (conquistata per la prima volta nella storica stagione 2016/2017).",
    },
    {
        "id": 2,
        "code": "U19",
        "name": "Juniores U19 Reg. Élite",
        "category": "Juniores Under 19 Regionali Élite",
        "macro": "agonistica",
        "macro_label": "Agonistica · LND",
        "annata": "U19",
        "campionato": "Campionato Regionale Juniores Under 19 Élite",
        "stadio": 'Stadio Comunale "Mario Zanconti" / C.S. Mazza',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/event_239.jpg",
        "desc": "Massima espressione giovanile regionale, trampolino diretto verso la Prima Squadra in Promozione.",
    },
    {
        "id": 3,
        "code": "U17",
        "name": "Allievi U17 Regionali",
        "category": "Allievi Under 17 Regionali (2009)",
        "macro": "agonistica",
        "macro_label": "Agonistica · SGS",
        "annata": "2009",
        "campionato": "FIGC SGS — Allievi Under 17 Regionali",
        "stadio": 'Centro Sportivo "Ambrogio Mazza" (Via ai Malgari, 6)',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/gothia_2024_3.jpg",
        "desc": "Formazione Allievi Under 17 impegnata nel campionato Regionale FIGC Settore Giovanile e Scolastico.",
    },
    {
        "id": 4,
        "code": "U16",
        "name": "Allievi U16 Regionali",
        "category": "Allievi Under 16 Regionali (2010)",
        "macro": "agonistica",
        "macro_label": "Agonistica · SGS",
        "annata": "2010",
        "campionato": "FIGC SGS — Allievi Under 16 Regionali",
        "stadio": 'Centro Sportivo "Ambrogio Mazza" (Via ai Malgari, 6)',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/gothia_2024_1.jpg",
        "desc": "Formazione Allievi Under 16 protagonista nel campionato Regionale e nei tornei giovanili lombardi e internazionali.",
    },
    {
        "id": 5,
        "code": "U15",
        "name": "Giovanissimi U15 Regionali",
        "category": "Giovanissimi Under 15 Regionali (2011)",
        "macro": "agonistica",
        "macro_label": "Agonistica · SGS",
        "annata": "2011",
        "campionato": "FIGC SGS — Giovanissimi Under 15 Regionali",
        "stadio": 'Centro Sportivo "Ambrogio Mazza" (Via ai Malgari, 6)',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/gothia_2024_2.jpg",
        "desc": "Sviluppo tecnico-coordinativo nel campionato Regionale Giovanissimi U15 con prevenzione posturale Vitalis.",
    },
    {
        "id": 6,
        "code": "U14",
        "name": "Giovanissimi U14 Provinciali",
        "category": "Giovanissimi Under 14 Provinciali (2012)",
        "macro": "agonistica",
        "macro_label": "Agonistica · SGS",
        "annata": "2012",
        "campionato": "FIGC SGS — Giovanissimi Under 14 Provinciali",
        "stadio": 'Centro Sportivo "Ambrogio Mazza" (Via ai Malgari, 6)',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/gothia_2024_1.jpg",
        "desc": "Ingresso nel settore agonistico FIGC: accompagnamento educativo e tecnico nel passaggio al calcio a 11.",
    },
    {
        "id": 7,
        "code": "E13",
        "name": "Esordienti FIGC 12a (2013)",
        "category": "Esordienti FIGC 12 anni (Annata 2013)",
        "macro": "base",
        "macro_label": "Attività di Base · FIGC",
        "annata": "2013",
        "campionato": "Torneo FIGC Esordienti 12 anni (2013)",
        "stadio": 'C.S. "Ambrogio Mazza" — Campo Enzo Riganti',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_1.jpg",
        "desc": "Didattica tecnica individuale, fair play e crescita motoria secondo i principi della Scuola Calcio Riconosciuta FIGC.",
    },
    {
        "id": 8,
        "code": "EM",
        "name": "Esordienti Misti (2013/14)",
        "category": "Esordienti FIGC Misti (2013/2014)",
        "macro": "base",
        "macro_label": "Attività di Base · FIGC",
        "annata": "13/14",
        "campionato": "Torneo FIGC Esordienti Misti (2013/2014)",
        "stadio": 'C.S. "Ambrogio Mazza" — Campo Enzo Riganti',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_2.jpg",
        "desc": "Formazione Esordienti Misti per garantire a tutti i tesserati ampio minutaggio e pari opportunità di apprendimento.",
    },
    {
        "id": 9,
        "code": "E14",
        "name": "Esordienti FIGC 11a (2014)",
        "category": "Esordienti FIGC 11 anni (Annata 2014)",
        "macro": "base",
        "macro_label": "Attività di Base · FIGC",
        "annata": "2014",
        "campionato": "Torneo FIGC Esordienti 11 anni (2014)",
        "stadio": 'C.S. "Ambrogio Mazza" — Campo Enzo Riganti',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_3.jpg",
        "desc": "Approccio al calcio a 9 con istruttori qualificati FIGC e monitoraggio motorio Vitalis.",
    },
    {
        "id": 10,
        "code": "P15",
        "name": "Pulcini FIGC 10a (2015)",
        "category": "Pulcini FIGC 10 anni (Annata 2015)",
        "macro": "base",
        "macro_label": "Attività di Base · FIGC",
        "annata": "2015",
        "campionato": "Torneo FIGC Pulcini 10 anni & Torneo Stefano Viganò",
        "stadio": 'C.S. "Ambrogio Mazza" — Via ai Malgari, 6',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_3.jpg",
        "desc": "Categoria protagonista dei tornei FIGC e dello storico Torneo Primaverile 'Stefano Viganò – Memorial Enzo Riganti'.",
    },
    {
        "id": 11,
        "code": "P16",
        "name": "Pulcini FIGC 9a (2016)",
        "category": "Pulcini FIGC 9 anni (Annata 2016)",
        "macro": "base",
        "macro_label": "Attività di Base · FIGC",
        "annata": "2016",
        "campionato": "Torneo FIGC Pulcini 9 anni (2016)",
        "stadio": 'C.S. "Ambrogio Mazza" — Via ai Malgari, 6',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_1.jpg",
        "desc": "Crescita tecnica e divertimento nel calcio a 7 seguendo la Carta dei Diritti dei Bambini FIGC e il Decalogo UEFA.",
    },
    {
        "id": 12,
        "code": "PC17",
        "name": "Primi Calci 2017",
        "category": "Scuola Calcio Primi Calci 2017",
        "macro": "scuola",
        "macro_label": "Scuola Calcio FIGC",
        "annata": "2017",
        "campionato": "Torneo / Raggruppamenti FIGC Primi Calci 2017",
        "stadio": 'C.S. "Ambrogio Mazza" — Via ai Malgari, 6',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_2.jpg",
        "desc": "Scuola Calcio Riconosciuta FIGC: giochi polivalenti, motricità di base e mini-partite per imparare divertendosi.",
    },
    {
        "id": 13,
        "code": "PC18",
        "name": "Primi Calci 2018",
        "category": "Scuola Calcio Primi Calci 2018",
        "macro": "scuola",
        "macro_label": "Scuola Calcio FIGC",
        "annata": "2018",
        "campionato": "Torneo / Raggruppamenti FIGC Primi Calci 2018",
        "stadio": 'C.S. "Ambrogio Mazza" — Via ai Malgari, 6',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_1.jpg",
        "desc": "Sviluppo degli schemi motori di base, amicizia e scoperta del pallone in un ambiente protetto e certificato Safeguarding.",
    },
    {
        "id": 14,
        "code": "PA19",
        "name": "Piccoli Amici 2019",
        "category": "Scuola Calcio Piccoli Amici 2019",
        "macro": "scuola",
        "macro_label": "Scuola Calcio FIGC",
        "annata": "2019",
        "campionato": "Attività Ludico-Motoria Scuola Calcio FIGC",
        "stadio": 'C.S. "Ambrogio Mazza" — Via ai Malgari, 6',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_3.jpg",
        "desc": "Avviamento ludico-motorio per i nati nel 2019 con gli istruttori qualificati della Scuola Calcio Riconosciuta FIGC.",
    },
    {
        "id": 15,
        "code": "PA20",
        "name": "Piccoli Amici 2020",
        "category": "Scuola Calcio Piccoli Amici 2020",
        "macro": "scuola",
        "macro_label": "Scuola Calcio FIGC",
        "annata": "2020",
        "campionato": "Attività Ludico-Motoria Scuola Calcio FIGC",
        "stadio": 'C.S. "Ambrogio Mazza" — Via ai Malgari, 6',
        "allenamenti": "Centro Sportivo Ambrogio Mazza (Via ai Malgari, 6)",
        "bg_img": "assets/vigano_3.jpg",
        "desc": "I più piccoli calciatori gialloneri (classe 2020): coordinazione, gioco e socializzazione al Centro Sportivo Mazza.",
    },
]

TIMELINE = [
    {
        "year": "1966 – 1970",
        "title": "Castel Cerreto & Bar Milano",
        "desc": "Dal gruppo di amici del Castel Cerreto (1966) al trionfo nel Torneo Notturno del Bar Milano ('Boccale d'Oro' 1971) che accende la nascita del club.",
    },
    {
        "year": "18 Agosto 1971",
        "title": "Fondazione A.C.O.S. 1971",
        "desc": "Battista 'Tista' Bugini, Enzo Riganti e Mario Barbieri fondano l'Associazione Calcistica Operai e Studenti con i colori sociali Giallo e Nero.",
    },
    {
        "year": "Anni '80 – 1989",
        "title": "Vivaio Modello & Gothia Cup",
        "desc": "Sotto la presidenza di Enzo Riganti esplode il settore giovanile e nel 1989 inizia l'epopea internazionale alla Gothia Cup di Göteborg.",
    },
    {
        "year": "Anni '90 – 2010",
        "title": "Emergency & Torneo Viganò",
        "desc": "Il logo Emergency portato gratuitamente sulle maglie con Gino Strada ospite a Treviglio e la nascita del Torneo Primaverile Stefano Viganò.",
    },
    {
        "year": "Agosto 2016",
        "title": "Shenyang 2016 & Promozione",
        "desc": "Unica squadra italiana invitata alla Gothia Cup China (3° posto e Coppa Disciplina) e storica conquista del campionato regionale di Promozione.",
    },
    {
        "year": "Oggi · 2025/2026",
        "title": "15 Squadre & Atalanta B.C.",
        "desc": "Dalla Promozione e Juniores U19 Élite alla Scuola Calcio Riconosciuta FIGC con partnership tecnica Atalanta B.C. e presidio Safeguarding.",
    },
]

CUORE_GIALLONERO = [
    "Villaggio della Gioia di Padre Fulgenzio",
    "Aiutare i Bambini ONLUS – Progetto 'Cuore di Bimbi' e Adozioni a distanza",
    "Associazione Futura ONLUS di Verdello",
    "Lega Italiana Fibrosi Cistica ONLUS",
    "Save The Children",
    "Associazione Italiana per la Lotta al Neuroblastoma",
    "Scuole Elementari e Medie di Treviglio (fornitura palloni, percorsi vita e attrezzature)",
    "Solidalmente ONLUS di Treviglio",
    "Mensa Solidale di Treviglio",
    "Associazione Ambrogio Mazza (acquisto di 4 defibrillatori per gli impianti trevigliesi)",
    "Progetto 'Il Giardino di Ozanam' (post-scuola ragazzi)",
    "Croce Rossa Italiana – Sezione di Treviglio (acquisto nuovo automezzo)",
    "Progetto Perù con Angelo Goisis (assistenza sanitaria bambini di Huaycan)",
    "Al di là del mio naso c'è ONLUS – Fara Gera d'Adda",
    "Cooperativa 'La Famiglia' di Treviglio (assistenza disabilità)",
    "Fondi Terremotati del Nepal (2015) e del Centro Italia (2016)",
    "Pizzeria Solidale Kalica di Treviglio (casa-famiglia per disabili)",
    "Girasole Calcio – Il Girasole ONLUS (Centro Diurno di Treviglio)",
    "Associazione Amici di Gabry (prevenzione e supporto oncologico)",
    "Cooperativa Sociale 'Insieme' di Treviglio (inserimento lavorativo disabili dal 1979)",
]

SPONSORS = [
    {"name": "Interfood S.r.l.", "img": "assets/sponsor_interfood.jpg", "url": "#contatti", "role": "Official Partner"},
    {"name": "Moriggi S.r.l.", "img": "assets/sponsor_moriggi.jpg", "url": "#contatti", "role": "Official Partner"},
    {"name": "Coriweb Digital Agency", "img": "assets/sponsor_coriweb.jpg", "url": "https://www.coriweb.it/chi-siamo/", "role": "coriweb.it"},
    {"name": "MCT Scaffalature Metalliche", "img": "assets/sponsor_mct.jpg", "url": "https://www.mctscaffalature.com/scaffalature-metalliche-cantilever-scaffali", "role": "mctscaffalature.com"},
    {"name": "Sage Sistemi S.r.l.", "img": "assets/sponsor_sage.jpg", "url": "https://www.sagesistemi.it/", "role": "sagesistemi.it"},
    {"name": "Compressori Bergamo", "img": "assets/sponsor_compressori.jpg", "url": "https://www.compressoribergamo.it/azienda/", "role": "compressoribergamo.it"},
    {"name": "Daminelli S.n.c.", "img": "assets/sponsor_daminelli.jpg", "url": "https://www.daminellisnc.it/", "role": "daminellisnc.it"},
    {"name": "Guerzoni S.r.l.", "img": "assets/sponsor_guerzoni.jpg", "url": "https://guerzonisrl.it/", "role": "guerzonisrl.it"},
    {"name": "2Vi Sicurezza", "img": "assets/sponsor_2vi.jpg", "url": "https://www.2visicurezza.it/", "role": "2visicurezza.it"},
    {"name": "Studio Geometra Riganti", "img": "assets/sponsor_riganti.jpg", "url": "http://www.geometrariganti.it/", "role": "geometrariganti.it"},
]


def get_asset_src(rel_path: str, embed_base64: bool) -> str:
    if not embed_base64:
        return rel_path
    full_p = BASE_DIR / rel_path
    if not full_p.exists():
        return rel_path
    raw = full_p.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = "image/png" if rel_path.endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def build_html(embed_base64: bool = False, crest_data_uri: str = "") -> str:
    def asset(rel_path: str) -> str:
        return get_asset_src(rel_path, embed_base64)

    teams_json = json.dumps(TEAMS, ensure_ascii=False)

    # Componente Stemma Ufficiale A.C.O.S. (SVG Ibrido HD 240x336 nitidissimo)
    def render_crest_badge(size_cls: str = "crest-header") -> str:
        return f"""<div class="acos-crest-shield {size_cls}" aria-hidden="true">
          <img src="{crest_data_uri}" alt="Stemma Ufficiale A.C.O.S. Treviglio Calcio 1971" />
        </div>"""

    # 1. Architettura Squadre in 4 Fasce Settoriali (Zero Foto Ripetute 15 Volte · Massima Chiarezza per Genitori e Atleti)
    SECTOR_BANDS = [
        {
            "macro": "agonistica",
            "sector_id": "vertice",
            "num": "01",
            "eyebrow": "Vertice Agonistico · L.N.D. Lombardia",
            "title": "Prima Squadra & U19 Élite",
            "subtitle": "Calcio a 11 regionale allo Stadio Comunale Mario Zanconti e al Centro Sportivo Ambrogio Mazza.",
            "bg_img": "assets/event_239.jpg",
            "watermark": "LND",
            "highlight_pill": "Stadio Zanconti & C.S. Mazza",
            "team_ids": [1, 2],
        },
        {
            "macro": "agonistica",
            "sector_id": "agonistica-sgs",
            "num": "02",
            "eyebrow": "Settore Agonistico F.I.G.C. · Calcio a 11",
            "title": "Allievi & Giovanissimi",
            "subtitle": "Campionati U17, U16, U15 e U14 (nati 2009–2012) con preparatore atletico, portieri e visita agonistica.",
            "bg_img": "assets/gothia_2024_3.jpg",
            "watermark": "A11",
            "highlight_pill": "Agonistica FIGC · Kit Remels",
            "team_ids": [3, 4, 5, 6],
        },
        {
            "macro": "base",
            "sector_id": "base-sgs",
            "num": "03",
            "eyebrow": "Attività di Base F.I.G.C. · Calcio a 9 e a 7",
            "title": "Esordienti & Pulcini",
            "subtitle": "Tornei federali U13, U12, U11 e U10 (nati 2013–2016): crescita tecnica individuale e fair play.",
            "bg_img": "assets/gothia_2024_1.jpg",
            "watermark": "SGS",
            "highlight_pill": "Tornei FIGC · Kit Remels",
            "team_ids": [7, 8, 9, 10, 11],
        },
        {
            "macro": "scuola",
            "sector_id": "scuola-figc",
            "num": "04",
            "eyebrow": "Scuola Calcio Riconosciuta F.I.G.C. · 5–8 Anni",
            "title": "Primi Calci & Piccoli Amici",
            "subtitle": "Avviamento motorio e ludico (nati 2017–2020) con istruttori F.I.G.C., metodo Atalanta B.C. e Vitalis.",
            "bg_img": "assets/vigano_3.jpg",
            "watermark": "KIDS",
            "highlight_pill": "Metodo Atalanta B.C. & Vitalis",
            "team_ids": [12, 13, 14, 15],
        },
    ]

    teams_by_id = {t["id"]: t for t in TEAMS}
    teams_grid_html = ""
    for band in SECTOR_BANDS:
        rows_html = ""
        for tid in band["team_ids"]:
            t = teams_by_id[tid]
            if tid in (1, 2):
                format_short = "Calcio a 11 · LND"
                fee_badge = "Tesseramento LND"
                venue_short = "Stadio Zanconti / C.S. Mazza"
            elif tid in (3, 4, 5, 6):
                format_short = "Calcio a 11 · FIGC SGS"
                fee_badge = "Kit Ufficiale Remels"
                venue_short = "C.S. Ambrogio Mazza"
            elif tid in (7, 8, 9):
                format_short = "Calcio a 9 · FIGC SGS"
                fee_badge = "Kit Ufficiale Remels"
                venue_short = "C.S. Ambrogio Mazza"
            elif tid in (10, 11):
                format_short = "Calcio a 7 · FIGC SGS"
                fee_badge = "Kit Ufficiale Remels"
                venue_short = "C.S. Ambrogio Mazza"
            elif tid in (12, 13):
                format_short = "Mini-Partite · FIGC SGS"
                fee_badge = "Kit Ufficiale Remels"
                venue_short = "C.S. Ambrogio Mazza"
            else:
                format_short = "Ludico-Motorio · 5–6 Anni"
                fee_badge = "Kit Ufficiale Remels"
                venue_short = "C.S. Ambrogio Mazza"

            rows_html += f"""
            <div class="sector-team-row" onclick="openTeamModal({t['id']})" role="button" tabindex="0">
              <div class="str-year-box">
                <span class="str-year-lbl">ANNATA</span>
                <span class="str-year-val">{t['annata']}</span>
              </div>
              <div class="str-main-info">
                <div class="str-title-line">
                  <h4 class="str-team-name">{t['name']}</h4>
                  <span class="str-format-pill">{format_short}</span>
                </div>
              </div>
              <div class="str-actions">
                <button type="button" class="btn-str-gold" onclick="event.stopPropagation(); openTeamModal({t['id']})">
                  Scheda<span class="str-btn-extra"> &amp; Contatto</span> →
                </button>
              </div>
            </div>
            """

        teams_grid_html += f"""
        <article class="sector-showcase-band" data-macro="{band['macro']}">
          <div class="ssb-visual" style="background-image:url('{asset(band['bg_img'])}');">
            <div class="ssb-visual-veil"></div>
            <span class="ssb-watermark">{band['watermark']}</span>
            <div class="ssb-visual-top">
              <span class="ssb-num">SETTORE {band['num']}</span>
              <span class="ssb-highlight-pill">{band['highlight_pill']}</span>
            </div>
            <div class="ssb-visual-bottom">
              <span class="ssb-eyebrow">{band['eyebrow']}</span>
              <h3 class="ssb-title">{band['title']}</h3>
              <p class="ssb-desc">{band['subtitle']}</p>
            </div>
          </div>
          <div class="ssb-matrix">
            {rows_html}
          </div>
        </article>
        """

    # 4. Timeline Storica Orizzontale 3x2 (Serie A Heritage Cards)
    timeline_html = ""
    for idx, item in enumerate(TIMELINE, 1):
        active_cls = " is-active-slide" if idx == 1 else ""
        slide_lbl = f"TAPPA {idx} / {len(TIMELINE)} • {item['year']}"
        timeline_html += f"""
        <article class="heritage-milestone-card{active_cls}" data-slide-label="{slide_lbl}">
          <span class="hmc-watermark">0{idx}</span>
          <div class="hmc-top">
            <span class="hmc-step-badge">TAPPA 0{idx}</span>
            <span class="hmc-year-pill">{item['year']}</span>
          </div>
          <h3 class="hmc-title">{item['title']}</h3>
          <p class="hmc-desc">{item['desc']}</p>
        </article>
        """

    # 5. Cuore Giallonero (20 realtà verificate da acos.it/pagina/cuore-giallonero)
    charities_html = "".join(
        f'<div class="charity-pill"><span class="charity-dot">💛</span><span>{c}</span></div>'
        for c in CUORE_GIALLONERO
    )

    # 6. Partner Wall Ufficiale (10 loghi originali da acos.it senza testo duplicato sotto le piastre)
    sponsors_html = ""
    for sp in SPONSORS:
        ext_attrs = (
            'target="_blank" rel="noopener noreferrer"'
            if sp["url"].startswith("http")
            else 'onclick="switchPage(\'page-contatti\'); return false;"'
        )
        sponsors_html += f"""
        <a href="{sp['url']}" {ext_attrs} class="sponsor-card" title="{sp['name']} ({sp['role']})">
          <div class="sponsor-plate">
            <img src="{asset(sp['img'])}" alt="{sp['name']}" loading="lazy" />
          </div>
        </a>
        """

    return f"""<!DOCTYPE html>
<html lang="it" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>A.C.O.S. Treviglio Calcio 1971 | Sito Ufficiale</title>
  <meta name="description" content="Sito Ufficiale A.S.D. A.C.O.S. Treviglio Calcio (Fondata il 18 Agosto 1971). Squadre dalla Promozione ai Piccoli Amici, Scuola Calcio Riconosciuta FIGC, Partnership Atalanta B.C., Gothia Cup e Safeguarding." />
  <meta name="theme-color" content="#050609" />

  <!-- Google Fonts: Bebas Neue, Barlow Condensed, Plus Jakarta Sans, JetBrains Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,600;0,700;0,800;0,900;1,700&family=Bebas+Neue&family=JetBrains+Mono:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />

  <style>
    /* ==========================================================================
       1. DESIGN TOKENS — SERIE A BROADCAST EDITION (v6.0)
       ========================================================================== */
    :root {{
      --bg-obsidian: #050609;
      --bg-stadium: #0A0C12;
      --bg-card: #10141E;
      --bg-card-elevated: #161B28;
      --bg-glass: rgba(8, 10, 15, 0.92);
      --acos-yellow: #FFDE24;
      --acos-gold: #F5B700;
      --acos-yellow-glow: rgba(255, 222, 36, 0.28);
      --acos-yellow-soft: rgba(255, 222, 36, 0.12);
      --acos-border-gold: rgba(255, 222, 36, 0.42);
      --atalanta-blue: #1D5BA6;
      --figc-azure: #0072CE;
      --text-white: #FFFFFF;
      --text-silver: #C4CCD8;
      --text-muted: #7F8A9E;
      --border-subtle: rgba(255, 255, 255, 0.09);
      --border-strong: rgba(255, 255, 255, 0.18);
      --win-green: #10B981;
      --draw-gold: #FFDE24;
      --loss-red: #F43F5E;
      --font-display: 'Barlow Condensed', 'Bebas Neue', Impact, sans-serif;
      --font-num: 'Bebas Neue', 'Barlow Condensed', sans-serif;
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
      --max-w: 1400px;
      --header-h: 126px;
    }}

    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html {{
      scroll-behavior: smooth;
      -webkit-text-size-adjust: 100%;
      background-color: #030406;
      color: var(--text-white);
      font-family: var(--font-sans);
    }}

    body {{
      background-color: var(--bg-obsidian);
      color: var(--text-white);
      line-height: 1.55;
      overflow-x: hidden;
      min-height: 100vh;
    }}

    :focus-visible {{
      outline: 2px solid var(--acos-yellow);
      outline-offset: 3px;
    }}

    a {{ color: inherit; text-decoration: none; }}
    button {{ font-family: inherit; cursor: pointer; }}
    img {{ display: block; max-width: 100%; height: auto; }}

    .container {{
      width: 100%;
      max-width: var(--max-w);
      margin: 0 auto;
      padding: 0 1.5rem;
    }}

    /* ==========================================================================
       2. OFFICIAL A.C.O.S. HD VECTOR-ENHANCED OVAL CREST (SERIE A DROP-CREST)
       ========================================================================== */
    .acos-crest-shield {{
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0 !important;
      filter: drop-shadow(0 10px 24px rgba(0, 0, 0, 0.92)) drop-shadow(0 0 22px rgba(255, 222, 36, 0.38));
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), filter 0.25s ease;
    }}

    .acos-crest-shield img {{
      width: 100% !important;
      height: 100% !important;
      max-width: none !important;
      object-fit: contain;
    }}

    /* Stemma Monumentale Serie A nell'Header (92x112px ad alto impatto visivo) */
    .crest-header {{
      width: 92px;
      height: 112px;
      transform: none;
      z-index: 1600;
    }}

    .crest-footer {{
      width: 76px;
      height: 92px;
    }}

    /* ==========================================================================
       3. SERIE A BROADCAST HEADER (118px) & INSTITUTIONAL TOP MICRO-BAR
       ========================================================================== */
    .top-Broadcast-ribbon {{
      background: #020305;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      height: 34px;
      display: flex;
      align-items: center;
      font-size: 0.72rem;
    }}

    .top-ribbon-inner {{
      max-width: var(--max-w);
      width: 100%;
      margin: 0 auto;
      padding: 0 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: nowrap;
      overflow: hidden;
    }}

    .ribbon-left, .ribbon-right {{
      display: flex;
      align-items: center;
      gap: 0.65rem;
      flex-wrap: nowrap;
      white-space: nowrap;
      color: var(--text-silver);
      font-weight: 600;
    }}

    .ribbon-dot {{
      color: var(--acos-yellow);
      font-weight: 900;
    }}

    .ribbon-link {{
      color: var(--text-silver);
      background: none;
      border: none;
      font-size: inherit;
      font-weight: 700;
      padding: 0;
      transition: color 0.15s ease;
    }}

    .ribbon-link:hover {{
      color: var(--acos-yellow);
    }}

    /* Pill tag usato nelle card interne del sito */
    .fed-tag {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.18rem 0.65rem;
      border-radius: 4px;
      font-weight: 800;
      font-size: 0.7rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      white-space: nowrap;
      background: rgba(255, 222, 36, 0.10);
      color: var(--text-white);
      border: 1px solid rgba(255, 222, 36, 0.32);
    }}

    .site-header {{
      position: sticky;
      top: 0;
      z-index: 1500;
      height: var(--header-h);
      width: 100%;
      background: radial-gradient(circle at 14% 50%, rgba(255, 222, 36, 0.13) 0%, rgba(9, 11, 16, 0.98) 45%, #050609 100%);
      border-bottom: 2.5px solid var(--acos-yellow);
      box-shadow: 0 14px 36px rgba(0, 0, 0, 0.88);
    }}

    .header-inner {{
      max-width: var(--max-w);
      width: 100%;
      margin: 0 auto;
      height: 100%;
      padding: 0 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1.25rem;
    }}

    .club-brand {{
      display: flex;
      align-items: center;
      gap: 1.05rem;
      cursor: pointer;
      flex: 0 0 auto;
    }}

    .club-brand:hover .crest-header {{
      transform: scale(1.04);
      filter: drop-shadow(0 10px 24px rgba(0, 0, 0, 0.95)) drop-shadow(0 0 26px rgba(255, 222, 36, 0.58));
    }}

    .club-brand-text {{
      display: flex;
      flex-direction: column;
      flex: 0 0 auto;
    }}

    .club-brand-title {{
      font-family: var(--font-display);
      font-size: 2.18rem;
      font-weight: 900;
      letter-spacing: 0.03em;
      line-height: 0.92;
      text-transform: uppercase;
      color: var(--text-white);
      white-space: nowrap;
      text-shadow: 0 4px 16px rgba(0, 0, 0, 0.75);
    }}

    .club-brand-title span {{
      color: var(--acos-yellow);
    }}

    .club-brand-sub {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 800;
      color: var(--acos-yellow);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      white-space: nowrap;
      margin-top: 0.28rem;
      opacity: 0.95;
    }}

    .main-nav {{
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      gap: 0.25rem;
      flex: 0 0 auto;
    }}

    .nav-btn {{
      background: transparent;
      border: none;
      color: var(--text-silver);
      font-family: var(--font-display);
      font-size: 1.12rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      height: 100%;
      padding: 0 0.85rem;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
      position: relative;
      transition: color 0.18s ease, background 0.18s ease;
    }}

    .nav-btn:hover {{
      color: var(--text-white);
      background: rgba(255, 255, 255, 0.04);
    }}

    .nav-btn.active {{
      color: var(--acos-yellow);
      background: linear-gradient(180deg, transparent 30%, rgba(255, 222, 36, 0.10) 100%);
    }}

    .nav-btn.active::after {{
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 4px;
      background: var(--acos-yellow);
      box-shadow: 0 -2px 12px var(--acos-yellow);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 0.65rem;
      flex: 0 0 auto;
    }}

    .btn-gold-broadcast {{
      background: linear-gradient(135deg, #FFEA5A 0%, #FFDE24 55%, #E5B80B 100%);
      color: #050609;
      border: none;
      font-family: var(--font-display);
      font-size: 1.05rem;
      font-weight: 900;
      letter-spacing: 0.045em;
      text-transform: uppercase;
      padding: 0.65rem 1.15rem;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      white-space: nowrap;
      flex-shrink: 0;
      box-shadow: 0 6px 20px rgba(255, 222, 36, 0.28);
      transition: transform 0.18s ease, box-shadow 0.18s ease;
    }}

    .btn-gold-broadcast:hover {{
      transform: translateY(-2px);
      box-shadow: 0 10px 30px rgba(255, 222, 36, 0.5);
    }}

    .btn-ghost-broadcast {{
      background: rgba(255, 255, 255, 0.07);
      color: var(--text-white);
      border: 1px solid rgba(255, 255, 255, 0.25);
      font-family: var(--font-display);
      font-size: 1.08rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      padding: 0.65rem 1.25rem;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      white-space: nowrap;
      backdrop-filter: blur(8px);
      transition: all 0.18s ease;
    }}

    .btn-ghost-broadcast:hover {{
      border-color: var(--acos-yellow);
      color: var(--acos-yellow);
      background: rgba(255, 222, 36, 0.08);
    }}

    .mobile-burger {{
      display: none;
      background: var(--bg-card-elevated);
      border: 1px solid var(--acos-border-gold);
      color: var(--acos-yellow);
      width: 46px;
      height: 46px;
      border-radius: 6px;
      align-items: center;
      justify-content: center;
      font-size: 1.4rem;
      flex-shrink: 0;
    }}

    /* ==========================================================================
       4. FULL-BLEED CINEMATIC STADIUM HERO (STILE SERIE A / INTER / CHAMPIONS LEAGUE)
       ========================================================================== */
    .stadium-hero {{
      position: relative;
      min-height: 650px;
      padding: 3.75rem 0 0;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
      border-bottom: 1px solid var(--acos-border-gold);
      background: #040508;
    }}

    .hero-slides-backdrop {{
      position: absolute;
      inset: 0;
      z-index: 0;
    }}

    @keyframes stadiumKenBurns {{
      0% {{ transform: scale(1.02) translate3d(0, 0, 0); }}
      100% {{ transform: scale(1.11) translate3d(-1.2%, -1%, 0); }}
    }}

    .hero-slide-bg {{
      position: absolute;
      inset: 0;
      background-size: cover;
      background-position: center 30%;
      opacity: 0;
      transform: scale(1.06);
      transition: opacity 1.1s cubic-bezier(0.16, 1, 0.3, 1);
      filter: contrast(1.22) saturate(1.28) brightness(0.84);
      will-change: opacity, transform;
    }}

    .hero-slide-bg.active {{
      opacity: 1;
      animation: stadiumKenBurns 7.5s ease-out forwards;
    }}

    /* Vignettatura cinematografica Widescreen 21:9 fissa (Zero cursore retroilluminato) */
    .hero-cinematic-veil {{
      position: absolute;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(4, 5, 8, 0.95) 0%, rgba(4, 5, 8, 0.76) 46%, rgba(4, 5, 8, 0.18) 100%),
        linear-gradient(180deg, rgba(4, 5, 8, 0.48) 0%, rgba(4, 5, 8, 0.08) 46%, rgba(4, 5, 8, 0.96) 100%);
    }}

    /* Fasci volumetrici dei riflettori stadio dall'alto */
    .hero-floodlight-beams {{
      position: absolute;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      background:
        conic-gradient(from 195deg at 88% -6%, transparent 0deg, rgba(255, 222, 36, 0.10) 18deg, transparent 38deg),
        conic-gradient(from 155deg at 14% -8%, transparent 0deg, rgba(255, 255, 255, 0.06) 16deg, transparent 34deg);
      mix-blend-mode: screen;
    }}

    /* Watermark monumentale sullo sfondo dello stadio */
    .hero-kinetic-watermark {{
      position: absolute;
      bottom: 62px;
      right: 2.5%;
      z-index: 1;
      font-family: var(--font-num);
      font-size: clamp(6rem, 15vw, 14.5rem);
      line-height: 0.8;
      color: transparent;
      -webkit-text-stroke: 1.5px rgba(255, 222, 36, 0.13);
      letter-spacing: 0.04em;
      pointer-events: none;
      user-select: none;
      white-space: nowrap;
    }}

    .hero-stage-grid {{
      position: relative;
      z-index: 2;
      display: block;
      max-width: 780px;
      width: 100%;
      padding-bottom: 3.35rem;
    }}

    .hero-identity-row {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }}

    .hero-season-pill {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: linear-gradient(135deg, #FFEA5A 0%, #FFDE24 100%);
      color: #050609;
      font-family: var(--font-display);
      font-weight: 900;
      font-size: 0.86rem;
      letter-spacing: 0.09em;
      padding: 0.26rem 0.85rem;
      border-radius: 4px;
      text-transform: uppercase;
      box-shadow: 0 6px 22px rgba(255, 222, 36, 0.32);
    }}

    .hero-pill-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #050609;
      display: inline-block;
    }}

    .hero-location-tag {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--text-silver);
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      padding: 0.24rem 0.7rem;
      border-radius: 4px;
      background: rgba(11, 14, 22, 0.76);
      border: 1px solid rgba(255, 255, 255, 0.14);
      backdrop-filter: blur(8px);
    }}

    .hero-monumental-h1 {{
      position: relative;
      font-family: var(--font-display);
      font-weight: 900;
      line-height: 0.90;
      text-transform: uppercase;
      margin-bottom: 1.35rem;
      padding-left: 1.25rem;
    }}

    .hero-monumental-h1::before {{
      content: '';
      position: absolute;
      left: 0;
      top: 0.06em;
      bottom: 0.06em;
      width: 6px;
      border-radius: 3px;
      background: var(--acos-yellow);
      box-shadow: 0 0 22px rgba(255, 222, 36, 0.65);
    }}

    .hero-monumental-h1 .hollow-line {{
      display: block;
      font-size: clamp(2.15rem, 3.5vw, 3.35rem);
      color: rgba(255, 255, 255, 0.14);
      -webkit-text-stroke: 2px rgba(255, 255, 255, 0.92);
      letter-spacing: 0.04em;
      transform: skewX(-6deg);
      transform-origin: left center;
      white-space: nowrap;
      margin-bottom: 0.06em;
    }}

    .hero-monumental-h1 .stroke-line {{
      display: block;
      font-size: clamp(2.75rem, 4.5vw, 4.45rem);
      color: #FFFFFF;
      letter-spacing: 0.015em;
      transform: skewX(-6deg);
      transform-origin: left center;
      text-shadow: 0 14px 32px rgba(0, 0, 0, 0.95);
      white-space: nowrap;
    }}

    .hero-monumental-h1 .gold-line {{
      display: block;
      font-size: clamp(3.15rem, 5.25vw, 5.15rem);
      letter-spacing: 0.015em;
      transform: skewX(-6deg);
      transform-origin: left center;
      background: linear-gradient(180deg, #FFF9B0 0%, #FFDE24 46%, #D49000 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 12px 24px rgba(0, 0, 0, 0.95)) drop-shadow(0 0 28px rgba(255, 222, 36, 0.36));
      white-space: nowrap;
    }}

    .hero-lead-copy {{
      font-size: 1.05rem;
      color: var(--text-silver);
      max-width: 54ch;
      line-height: 1.58;
      margin-bottom: 1.85rem;
      text-shadow: 0 2px 12px rgba(0, 0, 0, 0.92);
    }}

    /* Serie A Sleek Single-Line Action Buttons (Allineati a sinistra con il testo Hero) */
    .hero-cta-row {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 1rem;
      margin-top: 0.35rem;
    }}

    .hero-deck-btn {{
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.85rem;
      padding: 0.92rem 1.65rem;
      border-radius: 8px;
      font-family: var(--font-display);
      font-size: 1.24rem;
      font-weight: 900;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      line-height: 1;
      white-space: nowrap;
      cursor: pointer;
      transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.22s ease, border-color 0.22s ease, background 0.22s ease, color 0.22s ease;
    }}

    .hero-deck-arrow {{
      width: 26px;
      height: 26px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      font-size: 0.92rem;
      font-weight: 900;
      transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease;
    }}

    .hero-deck-btn.primary {{
      background: linear-gradient(135deg, #FFEA5A 0%, #FFDE24 55%, #E5B800 100%);
      color: #050609;
      border: 1px solid #FFF282;
      box-shadow: 0 10px 28px rgba(255, 222, 36, 0.28);
    }}

    .hero-deck-btn.primary .hero-deck-arrow {{
      background: rgba(5, 6, 9, 0.14);
      color: #050609;
    }}

    .hero-deck-btn.primary:hover {{
      transform: translateY(-2px);
      box-shadow: 0 16px 36px rgba(255, 222, 36, 0.44);
    }}

    .hero-deck-btn.primary:hover .hero-deck-arrow {{
      transform: translateX(3px);
    }}

    .hero-deck-btn.secondary {{
      background: rgba(11, 14, 22, 0.84);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      color: var(--text-white);
      border: 1px solid rgba(255, 222, 36, 0.45);
      box-shadow: 0 10px 26px rgba(0, 0, 0, 0.5);
    }}

    .hero-deck-btn.secondary .hero-deck-arrow {{
      background: rgba(255, 222, 36, 0.14);
      color: var(--acos-yellow);
    }}

    .hero-deck-btn.secondary:hover {{
      transform: translateY(-2px);
      border-color: var(--acos-yellow);
      background: rgba(20, 25, 38, 0.95);
      color: var(--acos-yellow);
      box-shadow: 0 14px 32px rgba(0, 0, 0, 0.7);
    }}

    .hero-deck-btn.secondary:hover .hero-deck-arrow {{
      transform: translateX(3px);
      background: var(--acos-yellow);
      color: #050609;
    }}

    /* ==========================================================================
       5. FLOATING GLASSMORPHIC MATCHDAY SPOTLIGHT POD (DESTRA DEL HERO — ZERO RIDONDANZE)
       ========================================================================== */
    .broadcast-hud-card {{
      position: relative;
      background: linear-gradient(165deg, rgba(14, 18, 28, 0.84) 0%, rgba(6, 8, 13, 0.92) 100%);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid rgba(255, 222, 36, 0.42);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.45rem 1.45rem 1.3rem;
      box-shadow: 0 30px 70px rgba(0, 0, 0, 0.88), 0 0 45px rgba(255, 222, 36, 0.12);
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.3s ease, box-shadow 0.3s ease;
    }}

    .broadcast-hud-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
      box-shadow: 0 34px 80px rgba(0, 0, 0, 0.92), 0 0 55px rgba(255, 222, 36, 0.20);
    }}

    .hud-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      padding-bottom: 0.85rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.10);
      margin-bottom: 1.15rem;
    }}

    .hud-live-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .hud-stadium-tag {{
      font-family: var(--font-mono);
      font-size: 0.66rem;
      color: var(--text-silver);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 0.18rem 0.55rem;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.09);
    }}

    .pulse-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--acos-yellow);
      box-shadow: 0 0 10px var(--acos-yellow);
      animation: pulseGlow 1.6s infinite;
    }}

    @keyframes pulseGlow {{
      0%, 100% {{ transform: scale(1); opacity: 1; }}
      50% {{ transform: scale(1.35); opacity: 0.55; }}
    }}

    .hud-scoreboard-main {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 0.8rem;
      background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 10px;
      padding: 1.15rem 0.85rem;
      text-align: center;
    }}

    .hud-club {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
    }}

    .hud-club-crest {{
      width: 68px;
      height: 92px;
      object-fit: contain;
      filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.85)) drop-shadow(0 0 14px rgba(255, 222, 36, 0.35));
    }}

    .hud-opp-shield {{
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: linear-gradient(135deg, #262E42, #141926);
      border: 2px solid var(--border-strong);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-weight: 900;
      font-size: 1.25rem;
      color: var(--text-silver);
    }}

    .hud-club-name {{
      font-family: var(--font-display);
      font-size: 1.15rem;
      font-weight: 900;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      line-height: 1.05;
    }}

    .hud-score-center {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.32rem;
    }}

    .hud-led-digits {{
      font-family: var(--font-num);
      font-size: 3.35rem;
      line-height: 0.9;
      color: var(--acos-yellow);
      background: #040508;
      border: 1px solid var(--acos-border-gold);
      padding: 0.4rem 0.95rem;
      border-radius: 8px;
      letter-spacing: 0.06em;
      box-shadow: inset 0 0 18px rgba(255, 222, 36, 0.16);
    }}

    .hud-ft-tag {{
      font-family: var(--font-mono);
      font-size: 0.64rem;
      color: var(--win-green);
      font-weight: 800;
      letter-spacing: 0.09em;
      text-transform: uppercase;
    }}

    .hud-pod-footer {{
      margin-top: 1.05rem;
      padding-top: 0.95rem;
      border-top: 1px solid rgba(255, 255, 255, 0.09);
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 0.65rem;
      align-items: center;
    }}

    .hud-pod-cta {{
      display: inline-flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.6rem;
      width: 100%;
      padding: 0.68rem 0.95rem;
      border-radius: 6px;
      background: rgba(255, 222, 36, 0.10);
      border: 1px solid rgba(255, 222, 36, 0.38);
      color: var(--acos-yellow);
      font-family: var(--font-display);
      font-size: 0.98rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .hud-pod-cta:hover {{
      background: var(--acos-yellow);
      color: #050609;
      border-color: var(--acos-yellow);
    }}

    .hud-pod-secondary {{
      padding: 0.68rem 0.85rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.14);
      color: var(--text-silver);
      font-family: var(--font-mono);
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s ease;
    }}

    .hud-pod-secondary:hover {{
      border-color: var(--text-white);
      color: var(--text-white);
      background: rgba(255, 255, 255, 0.09);
    }}

    /* ==========================================================================
       5B. BROADCAST LOWER-THIRD TELEMETRY BAR (4 PILLARS ARCHITETTONICI BILANCIATI)
       ========================================================================== */
    .hero-lower-third {{
      position: relative;
      z-index: 3;
      width: 100%;
      background: linear-gradient(180deg, rgba(9, 12, 19, 0.92) 0%, rgba(5, 6, 10, 0.98) 100%);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-top: 1px solid rgba(255, 222, 36, 0.28);
    }}

    .hero-lower-inner {{
      width: 100%;
      max-width: var(--max-w);
      margin: 0 auto;
      padding: 0 1.5rem;
    }}

    .hero-telemetry-strip {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      align-items: stretch;
      width: 100%;
    }}

    .hero-telemetry-item {{
      position: relative;
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 0.9rem;
      padding: 1.05rem 1.35rem;
      background: transparent;
      border: none;
      border-right: 1px solid rgba(255, 255, 255, 0.08);
      text-align: left;
      cursor: default;
    }}

    .hero-telemetry-item:first-child {{
      border-left: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .telemetry-copy {{
      display: flex;
      flex-direction: column;
      min-width: 0;
    }}

    .telemetry-val {{
      font-family: var(--font-display);
      font-size: 1.35rem;
      font-weight: 900;
      color: var(--acos-yellow);
      line-height: 1;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .telemetry-lbl {{
      font-family: var(--font-body);
      font-size: 0.76rem;
      color: var(--text-silver);
      font-weight: 500;
      margin-top: 0.25rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    /* ==========================================================================
       5C. TOP-LEVEL HOME 3-PILLAR SECTOR POSTERS & HERITAGE SHOWCASE (ZERO CLUTTER)
       ========================================================================== */
    .home-sectors-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1.5rem;
    }}

    .home-sector-poster {{
      position: relative;
      min-height: 410px;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid rgba(255, 255, 255, 0.12);
      background: #080A10;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      padding: 1.85rem 1.75rem;
      cursor: pointer;
      box-shadow: 0 22px 50px rgba(0, 0, 0, 0.72);
      transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.28s ease, box-shadow 0.28s ease;
    }}

    .home-sector-poster:hover {{
      transform: translateY(-6px);
      border-color: var(--acos-yellow);
      box-shadow: 0 28px 64px rgba(0, 0, 0, 0.88), 0 0 36px rgba(255, 222, 36, 0.14);
    }}

    .hsp-bg {{
      position: absolute;
      inset: 0;
      background-size: cover;
      background-position: center;
      filter: brightness(0.86) contrast(1.1) saturate(1.12);
      transition: transform 0.55s cubic-bezier(0.16, 1, 0.3, 1), filter 0.35s ease;
      z-index: 0;
    }}

    .home-sector-poster:hover .hsp-bg {{
      transform: scale(1.05);
      filter: brightness(0.95) contrast(1.12) saturate(1.18);
    }}

    .hsp-veil {{
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(5, 6, 10, 0.12) 0%, rgba(5, 6, 10, 0.62) 46%, rgba(5, 6, 10, 0.96) 100%);
      z-index: 1;
    }}

    .hsp-content {{
      position: relative;
      z-index: 2;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
    }}

    .hsp-eyebrow {{
      font-family: var(--font-mono);
      font-size: 0.68rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .hsp-title {{
      font-family: var(--font-display);
      font-size: 2.05rem;
      font-weight: 900;
      color: var(--text-white);
      text-transform: uppercase;
      line-height: 0.96;
      letter-spacing: 0.02em;
      margin: 0;
    }}

    .hsp-desc {{
      font-family: var(--font-body);
      font-size: 0.9rem;
      line-height: 1.52;
      color: var(--text-silver);
      margin: 0.15rem 0 0.45rem;
    }}

    .hsp-link {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      font-family: var(--font-display);
      font-size: 0.98rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--acos-yellow);
      transition: gap 0.2s ease;
    }}

    .home-sector-poster:hover .hsp-link {{
      gap: 0.72rem;
    }}

    .home-heritage-showcase {{
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      border-radius: 18px;
      overflow: hidden;
      background: linear-gradient(145deg, #101420 0%, #07090F 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 26px 64px rgba(0, 0, 0, 0.78);
    }}

    .hhs-visual {{
      position: relative;
      min-height: 360px;
      background-size: cover;
      background-position: center;
    }}

    .hhs-visual::after {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, rgba(7, 9, 15, 0.05) 50%, rgba(7, 9, 15, 0.92) 100%);
    }}

    .hhs-body {{
      padding: 2.75rem 2.6rem;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: flex-start;
      gap: 0.95rem;
    }}

    .hhs-title {{
      font-family: var(--font-display);
      font-size: clamp(1.95rem, 3vw, 2.65rem);
      font-weight: 900;
      color: var(--text-white);
      text-transform: uppercase;
      line-height: 0.96;
      margin: 0;
    }}

    .hhs-title span {{
      color: var(--acos-yellow);
    }}

    .hhs-copy {{
      font-family: var(--font-body);
      font-size: 0.95rem;
      line-height: 1.62;
      color: var(--text-silver);
      margin: 0;
    }}

    /* ==========================================================================
       6. CONTINUOUS BROADCAST RESULT TICKER TAPE
       ========================================================================== */
    .broadcast-ticker-bar {{
      background: #090B10;
      border-bottom: 1px solid var(--border-subtle);
      height: 46px;
      display: flex;
      align-items: center;
      overflow: hidden;
      position: relative;
    }}

    .ticker-label {{
      background: var(--acos-yellow);
      color: #050609;
      font-family: var(--font-display);
      font-weight: 900;
      font-size: 0.92rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      height: 100%;
      padding: 0 1.15rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      flex-shrink: 0;
      z-index: 2;
      box-shadow: 8px 0 20px rgba(0, 0, 0, 0.7);
    }}

    .ticker-track-wrap {{
      flex: 1;
      overflow: hidden;
      display: flex;
    }}

    .ticker-track {{
      display: flex;
      align-items: center;
      gap: 1.75rem;
      white-space: nowrap;
      padding-left: 1.25rem;
      animation: tickerScroll 48s linear infinite;
    }}

    .ticker-track:hover {{
      animation-play-state: paused;
    }}

    @keyframes tickerScroll {{
      0% {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}

    .ticker-item {{
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
      font-size: 0.82rem;
      cursor: pointer;
    }}

    .ticker-cat {{
      background: rgba(255, 222, 36, 0.14);
      color: var(--acos-yellow);
      font-family: var(--font-display);
      font-weight: 800;
      padding: 0.1rem 0.45rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .ticker-score {{
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      padding: 0 0.25rem;
    }}

    /* ==========================================================================
       7. SECTIONS, MATCH CENTER & BENTO CARDS
       ========================================================================== */
    .page-view {{
      display: none;
      animation: pageFadeIn 0.28s ease-out;
    }}

    .page-view.active {{
      display: block;
    }}

    @keyframes pageFadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    .section-block {{
      padding: 4rem 0;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .section-header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1.25rem;
      margin-bottom: 2.25rem;
    }}

    .section-eyebrow {{
      color: var(--acos-yellow);
      font-family: var(--font-display);
      font-size: 1rem;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      display: block;
      margin-bottom: 0.25rem;
    }}

    .section-title {{
      font-family: var(--font-display);
      font-size: clamp(2.1rem, 3.8vw, 3.1rem);
      font-weight: 900;
      text-transform: uppercase;
      line-height: 0.98;
      letter-spacing: 0.01em;
    }}

    /* Tabs & Filters */
    .tabs-bar {{
      display: inline-flex;
      background: var(--bg-card);
      border: 1px solid var(--acos-border-gold);
      border-radius: 8px;
      padding: 0.3rem;
      gap: 0.35rem;
    }}

    .tab-pill {{
      background: transparent;
      border: none;
      color: var(--text-silver);
      font-family: var(--font-display);
      font-size: 1.02rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 0.5rem 1.1rem;
      border-radius: 6px;
      transition: all 0.18s ease;
    }}

    .tab-pill.active {{
      background: var(--acos-yellow);
      color: #050609;
    }}

    .filter-chips-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1.75rem;
    }}

    .filter-chip {{
      background: var(--bg-card);
      border: 1px solid var(--border-strong);
      color: var(--text-silver);
      padding: 0.45rem 0.95rem;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 700;
      transition: all 0.18s ease;
    }}

    .filter-chip.active, .filter-chip:hover {{
      background: var(--acos-yellow-soft);
      border-color: var(--acos-yellow);
      color: var(--acos-yellow);
    }}

    /* ==========================================================================
       7B. MAIN EVENT PRIMA SQUADRA BANNER (FULL-WIDTH CORONA DEL MATCH CENTER)
       ========================================================================== */
    .mc-featured-banner {{
      position: relative;
      background:
        radial-gradient(520px circle at 50% 0%, rgba(255, 222, 36, 0.14) 0%, transparent 70%),
        linear-gradient(135deg, #131824 0%, #0A0D14 55%, #111622 100%);
      border: 1px solid rgba(255, 222, 36, 0.42);
      border-left: 5px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.35rem 1.65rem;
      margin-bottom: 1.35rem;
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.05rem;
      box-shadow: 0 22px 54px rgba(0, 0, 0, 0.65), 0 0 36px rgba(255, 222, 36, 0.08);
    }}

    .mc-featured-banner:hover {{
      transform: translateY(-3px);
      border-color: var(--acos-yellow);
      box-shadow: 0 26px 64px rgba(0, 0, 0, 0.8), 0 0 44px rgba(255, 222, 36, 0.16);
    }}

    .mcfb-meta {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.75rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.09);
    }}

    .mcfb-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .mcfb-venue {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--text-silver);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}

    .mcfb-stage {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 1.5rem;
      background: rgba(4, 5, 8, 0.68);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 10px;
      padding: 1.05rem 1.5rem;
    }}

    .mcfb-club {{
      display: flex;
      align-items: center;
      gap: 0.95rem;
      min-width: 0;
    }}

    .mcfb-club.is-opp {{
      justify-content: flex-end;
    }}

    .mcfb-crest {{
      width: 58px;
      height: 78px;
      object-fit: contain;
      flex-shrink: 0;
      filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.85)) drop-shadow(0 0 14px rgba(255, 222, 36, 0.32));
    }}

    .mcfb-opp-shield {{
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: linear-gradient(135deg, #252E42 0%, #131824 100%);
      border: 2px solid var(--border-strong);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-size: 1.15rem;
      font-weight: 900;
      color: var(--text-silver);
      flex-shrink: 0;
    }}

    .mcfb-club-copy {{
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      min-width: 0;
    }}

    .mcfb-club-copy.align-right {{
      text-align: right;
      align-items: flex-end;
    }}

    .mcfb-club-kicker {{
      font-family: var(--font-mono);
      font-size: 0.64rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-muted);
    }}

    .mcfb-club.is-acos .mcfb-club-name {{
      color: var(--acos-yellow);
    }}

    .mcfb-club-name {{
      font-family: var(--font-display);
      font-size: clamp(1.35rem, 2.2vw, 1.95rem);
      font-weight: 900;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      line-height: 1;
      color: var(--text-white);
    }}

    .mcfb-score-pod {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.35rem;
      flex-shrink: 0;
    }}

    .mcfb-led-score {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.45rem;
      white-space: nowrap;
      font-family: var(--font-num);
      font-size: clamp(2.35rem, 3.4vw, 3.25rem);
      line-height: 0.92;
      color: var(--acos-yellow);
      background: #030407;
      border: 1px solid var(--acos-border-gold);
      padding: 0.38rem 1.15rem;
      border-radius: 8px;
      box-shadow: inset 0 0 18px rgba(255, 222, 36, 0.16);
    }}

    .mcfb-colon {{
      opacity: 0.72;
    }}

    .mcfb-status {{
      font-family: var(--font-mono);
      font-size: 0.65rem;
      font-weight: 800;
      color: var(--win-green);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .mcfb-action {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.78rem;
      color: var(--text-silver);
    }}

    .mcfb-cta-pill {{
      margin-left: auto;
      font-family: var(--font-display);
      font-size: 0.98rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--acos-yellow);
    }}

    /* Broadcast Match Cards Grid (12 Gare Giovanili = 3x4 su Desktop, 2x6 su Tablet — Zero Carte Orfane) */
    .matches-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1.15rem;
    }}

    /* ==========================================================================
       7C. UX LAB SIMULATION SWITCHER & ZERO-MAINTENANCE EVERGREEN ARCHITECTURE
       ========================================================================== */
    .ux-sim-bar {{
      background: linear-gradient(135deg, rgba(255, 222, 36, 0.12) 0%, rgba(12, 15, 23, 0.96) 100%);
      border: 1px solid rgba(255, 222, 36, 0.45);
      border-left: 5px solid var(--acos-yellow);
      border-radius: 12px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.55);
    }}

    .ux-sim-bar-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.75rem;
    }}

    .ux-sim-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--acos-yellow);
    }}

    .ux-sim-tabs {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.65rem;
    }}

    .ux-sim-tab {{
      background: rgba(6, 8, 13, 0.86);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 8px;
      padding: 0.75rem 0.95rem;
      text-align: left;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      transition: all 0.2s ease;
    }}

    .ux-sim-tab:hover {{
      border-color: rgba(255, 222, 36, 0.55);
      background: rgba(18, 23, 35, 0.95);
    }}

    .ux-sim-tab.active {{
      background: linear-gradient(135deg, #FFEA5A 0%, #FFDE24 60%, #E5B800 100%);
      border-color: #FFF38A;
      color: #050609;
      box-shadow: 0 10px 26px rgba(255, 222, 36, 0.28);
    }}

    .ux-sim-tab-kicker {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--acos-yellow);
    }}

    .ux-sim-tab.active .ux-sim-tab-kicker {{
      color: #050609;
      opacity: 0.82;
    }}

    .ux-sim-tab-title {{
      font-family: var(--font-display);
      font-size: 1.08rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      color: var(--text-white);
      line-height: 1.05;
    }}

    .ux-sim-tab.active .ux-sim-tab-title {{
      color: #050609;
    }}

    .ux-sim-pane {{
      display: none;
      animation: pageFadeIn 0.24s ease-out;
    }}

    .ux-sim-pane.active {{
      display: block;
    }}

    /* SIMULAZIONE A: PIRAMIDE STAGIONALE EVERGREEN (ZERO SITI ESTERNI, ZERO SCADENZA) */
    .evergreen-flagship-banner {{
      position: relative;
      border-radius: 14px;
      overflow: hidden;
      border: 1px solid rgba(255, 222, 36, 0.44);
      border-left: 5px solid var(--acos-yellow);
      background:
        radial-gradient(560px circle at 85% 25%, rgba(255, 222, 36, 0.16) 0%, transparent 68%),
        linear-gradient(135deg, #131824 0%, #090C12 100%);
      padding: 1.65rem 1.85rem;
      margin-bottom: 1.35rem;
      display: grid;
      grid-template-columns: 1.35fr 0.65fr;
      gap: 1.5rem;
      align-items: center;
      box-shadow: 0 22px 54px rgba(0, 0, 0, 0.68);
    }}

    .efb-left {{
      display: flex;
      align-items: center;
      gap: 1.25rem;
    }}

    .efb-crest {{
      width: 68px;
      height: 88px;
      object-fit: contain;
      flex-shrink: 0;
      filter: drop-shadow(0 8px 18px rgba(0, 0, 0, 0.9)) drop-shadow(0 0 18px rgba(255, 222, 36, 0.32));
    }}

    .efb-copy {{
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }}

    .efb-title {{
      font-family: var(--font-display);
      font-size: clamp(1.65rem, 2.8vw, 2.35rem);
      font-weight: 900;
      text-transform: uppercase;
      line-height: 0.96;
      color: var(--text-white);
    }}

    .efb-title span {{
      color: var(--acos-yellow);
    }}

    .efb-sub {{
      font-size: 0.9rem;
      color: var(--text-silver);
      max-width: 58ch;
    }}

    .efb-right {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 0.6rem;
    }}

    .efb-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      justify-content: flex-end;
    }}

    .efb-pill {{
      font-family: var(--font-mono);
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 0.3rem 0.68rem;
      border-radius: 6px;
      background: rgba(5, 6, 9, 0.72);
      border: 1px solid rgba(255, 255, 255, 0.14);
      color: var(--text-silver);
    }}

    .efb-pill strong {{
      color: var(--acos-yellow);
    }}

    .pyramid-3-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1.25rem;
    }}

    .pyramid-sector-card {{
      background: linear-gradient(165deg, #131824 0%, #0A0D14 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
    }}

    .pyramid-sector-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
      box-shadow: 0 20px 44px rgba(0, 0, 0, 0.68);
    }}

    .psc-visual {{
      position: relative;
      height: 165px;
      background-size: cover;
      background-position: center 28%;
      padding: 1rem 1.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .psc-visual::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(5, 6, 9, 0.25) 0%, rgba(10, 13, 20, 0.96) 100%);
    }}

    .psc-top, .psc-bottom {{
      position: relative;
      z-index: 2;
    }}

    .psc-num {{
      position: absolute;
      right: 14px;
      top: 8px;
      font-family: var(--font-num);
      font-size: 4.4rem;
      line-height: 0.85;
      color: rgba(255, 222, 36, 0.18);
      z-index: 1;
      pointer-events: none;
    }}

    .psc-title {{
      font-family: var(--font-display);
      font-size: 1.55rem;
      font-weight: 900;
      text-transform: uppercase;
      line-height: 0.98;
      color: var(--text-white);
    }}

    .psc-body {{
      padding: 1.15rem 1.25rem 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      flex: 1;
    }}

    .psc-team-list {{
      display: flex;
      flex-direction: column;
      gap: 0.42rem;
    }}

    .psc-team-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      background: rgba(5, 6, 9, 0.62);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 6px;
      padding: 0.45rem 0.68rem;
      cursor: pointer;
      transition: all 0.16s ease;
    }}

    .psc-team-row:hover {{
      border-color: var(--acos-yellow);
      background: rgba(255, 222, 36, 0.08);
    }}

    .psc-team-name {{
      font-family: var(--font-display);
      font-size: 0.98rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--text-white);
    }}

    .psc-team-year {{
      font-family: var(--font-mono);
      font-size: 0.66rem;
      font-weight: 700;
      color: var(--acos-yellow);
      text-transform: uppercase;
    }}

    /* SIMULAZIONE B: IN-PAGE EMBEDDED LIVE CONSOLE (ZERO REDIRECT FUORI DAL SITO) */
    .inpage-live-console {{
      background: linear-gradient(165deg, #121723 0%, #080A10 100%);
      border: 1px solid rgba(255, 222, 36, 0.42);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.78);
    }}

    .ilc-toolbar {{
      background: #06080D;
      border-bottom: 1px solid rgba(255, 255, 255, 0.10);
      padding: 1rem 1.35rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.85rem;
    }}

    .ilc-cat-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
    }}

    .ilc-cat-btn {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: var(--text-silver);
      font-family: var(--font-display);
      font-size: 0.92rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 0.42rem 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.18s ease;
    }}

    .ilc-cat-btn.active, .ilc-cat-btn:hover {{
      background: var(--acos-yellow);
      border-color: var(--acos-yellow);
      color: #050609;
    }}

    .ilc-stage {{
      padding: 1.35rem;
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 1.25rem;
    }}

    .ilc-panel {{
      background: rgba(5, 6, 9, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 10px;
      padding: 1.15rem;
    }}

    .ilc-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
      margin-top: 0.65rem;
    }}

    .ilc-table th {{
      text-align: left;
      font-family: var(--font-mono);
      font-size: 0.66rem;
      text-transform: uppercase;
      color: var(--text-muted);
      padding: 0.45rem 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.10);
    }}

    .ilc-table td {{
      padding: 0.52rem 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: var(--text-silver);
    }}

    .ilc-table tr.is-acos-row td {{
      background: rgba(255, 222, 36, 0.12);
      color: var(--acos-yellow);
      font-weight: 800;
    }}

    .broadcast-match-card {{
      background: linear-gradient(165deg, var(--bg-card-elevated) 0%, var(--bg-card) 100%);
      border: 1px solid var(--border-subtle);
      border-left: 4px solid var(--acos-yellow);
      border-radius: 12px;
      padding: 1.15rem 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.95rem;
      cursor: pointer;
      transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    .broadcast-match-card:hover {{
      transform: translateY(-3px);
      border-color: var(--acos-border-gold);
      box-shadow: 0 14px 34px rgba(0, 0, 0, 0.55);
    }}

    .broadcast-match-card.outcome-win {{ border-left-color: var(--win-green); }}
    .broadcast-match-card.outcome-draw {{ border-left-color: var(--acos-yellow); }}
    .broadcast-match-card.outcome-figc {{ border-left-color: var(--figc-azure); }}

    .bmc-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      font-size: 0.76rem;
    }}

    .bmc-category {{
      font-family: var(--font-display);
      font-size: 0.95rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--text-white);
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }}

    .bmc-code {{
      background: var(--acos-yellow);
      color: #050609;
      padding: 0.08rem 0.42rem;
      border-radius: 4px;
      font-size: 0.78rem;
      font-weight: 900;
    }}

    .bmc-date {{
      font-family: var(--font-mono);
      color: var(--text-muted);
      font-size: 0.72rem;
    }}

    .bmc-scoreboard {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 0.65rem;
      background: rgba(5, 6, 9, 0.65);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.75rem;
    }}

    .bmc-team {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      min-width: 0;
    }}

    .bmc-team:last-child {{
      justify-content: flex-end;
      text-align: right;
    }}

    .bmc-team.is-acos .bmc-team-name {{
      color: var(--acos-yellow);
      font-weight: 900;
    }}

    .bmc-team-name {{
      font-family: var(--font-display);
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.1;
      text-transform: uppercase;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .mc-mini-crest {{
      width: 28px;
      height: 39px;
      object-fit: contain;
      flex-shrink: 0;
    }}

    .mc-opp-avatar {{
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: #1E2536;
      border: 1px solid var(--border-strong);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-size: 0.68rem;
      font-weight: 800;
      color: var(--text-silver);
      flex-shrink: 0;
    }}

    .bmc-score-box {{
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      background: #040507;
      border: 1px solid var(--acos-border-gold);
      padding: 0.2rem 0.65rem;
      border-radius: 6px;
      font-family: var(--font-num);
      font-size: 1.65rem;
      line-height: 1;
      color: var(--acos-yellow);
    }}

    .bmc-vs-badge {{
      background: var(--acos-yellow-soft);
      color: var(--acos-yellow);
      font-family: var(--font-display);
      font-weight: 900;
      padding: 0.2rem 0.55rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }}

    .bmc-footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.74rem;
      color: var(--text-silver);
    }}

    .bmc-status-pill {{
      font-family: var(--font-mono);
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
    }}

    .bmc-link {{
      color: var(--acos-yellow);
      font-weight: 700;
    }}

    /* ==========================================================================
       8. SQUAD POSTER CARDS (TUTTE LE 15 SQUADRE)
       ========================================================================== */
    .roster-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 1.5rem;
    }}

    .squad-poster-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
    }}

    .squad-poster-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-border-gold);
      box-shadow: 0 20px 44px rgba(0, 0, 0, 0.65);
    }}

    .spc-visual {{
      position: relative;
      height: 195px;
      background-size: cover;
      background-position: center 25%;
      padding: 1rem 1.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      cursor: pointer;
      overflow: hidden;
    }}

    .spc-visual-overlay {{
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(5,6,9,0.35) 0%, rgba(16,20,30,0.96) 100%);
    }}

    .spc-watermark {{
      position: absolute;
      right: 10px;
      bottom: -10px;
      font-family: var(--font-num);
      font-size: 6.2rem;
      line-height: 0.85;
      color: rgba(255, 222, 36, 0.14);
      pointer-events: none;
      z-index: 1;
    }}

    .spc-top-row {{
      position: relative;
      z-index: 2;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .spc-macro-badge {{
      background: var(--acos-yellow);
      color: #050609;
      font-family: var(--font-display);
      font-weight: 900;
      font-size: 0.76rem;
      padding: 0.15rem 0.6rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .spc-year-pill {{
      background: rgba(5, 6, 9, 0.82);
      border: 1px solid var(--acos-border-gold);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 700;
      padding: 0.15rem 0.55rem;
      border-radius: 4px;
    }}

    .spc-bottom-title {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .spc-crest {{
      width: 44px;
      height: 62px;
      object-fit: contain;
      flex-shrink: 0;
      filter: drop-shadow(0 4px 10px rgba(0,0,0,0.85));
    }}

    .spc-result-banner {{
      background: rgba(5, 6, 9, 0.72);
      border: 1px solid var(--acos-border-gold);
      border-left: 3px solid var(--acos-yellow);
      border-radius: 8px;
      padding: 0.65rem 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      margin-top: auto;
    }}

    .spc-res-lbl {{
      font-family: var(--font-mono);
      font-size: 0.68rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
    }}

    .spc-res-score {{
      font-family: var(--font-display);
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--text-white);
      text-transform: uppercase;
    }}

    .spc-res-score b {{
      color: var(--acos-yellow);
      font-family: var(--font-num);
      font-size: 1.35rem;
      padding: 0 0.35rem;
    }}

    .spc-subcat {{
      font-size: 0.72rem;
      color: var(--acos-yellow);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      display: block;
    }}

    .spc-title {{
      font-family: var(--font-display);
      font-size: 1.65rem;
      font-weight: 900;
      line-height: 1;
      text-transform: uppercase;
    }}

    .spc-body {{
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      flex: 1;
    }}

    .spc-desc {{
      font-size: 0.86rem;
      color: var(--text-silver);
    }}

    .spc-data-grid {{
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      background: rgba(5, 6, 9, 0.55);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.75rem;
      font-size: 0.78rem;
    }}

    .spc-data-row {{
      display: flex;
      justify-content: space-between;
      gap: 0.5rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      padding-bottom: 0.35rem;
    }}

    .spc-data-row:last-child {{
      border-bottom: none;
      padding-bottom: 0;
    }}

    .spc-label {{ color: var(--text-muted); font-weight: 600; white-space: nowrap; }}
    .spc-val {{ color: var(--text-white); font-weight: 700; text-align: right; }}

    .spc-actions {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.6rem;
      margin-top: auto;
    }}

    .btn-card-outline {{
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border-strong);
      color: var(--text-white);
      font-family: var(--font-display);
      font-size: 0.95rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 0.55rem;
      border-radius: 6px;
      transition: all 0.15s ease;
    }}

    .btn-card-outline:hover {{
      border-color: var(--acos-yellow);
      color: var(--acos-yellow);
    }}

    .btn-card-gold {{
      background: var(--acos-yellow);
      border: 1px solid var(--acos-yellow);
      color: #050609;
      font-family: var(--font-display);
      font-size: 0.95rem;
      font-weight: 900;
      text-transform: uppercase;
      padding: 0.55rem;
      border-radius: 6px;
      transition: all 0.15s ease;
    }}

    .btn-card-gold:hover {{
      background: #FFEA61;
    }}

    /* ==========================================================================
       8B. INTERACTIVE AGE FINDER (HOME ATTO II) & 4 SECTOR SHOWCASE BANDS (SQUADRE)
       ========================================================================== */
    .age-finder-stage {{
      display: flex;
      flex-direction: column;
      gap: 1.35rem;
    }}

    .age-finder-pills {{
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: 0.65rem;
    }}

    .age-pill-btn {{
      background: linear-gradient(165deg, rgba(20, 26, 38, 0.92) 0%, rgba(10, 13, 20, 0.96) 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 0.85rem 0.65rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.22rem;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      text-align: center;
    }}

    .age-pill-btn:hover {{
      border-color: rgba(255, 222, 36, 0.55);
      transform: translateY(-2px);
    }}

    .age-pill-btn.active {{
      background: linear-gradient(135deg, #FFE135 0%, #F2BE00 100%);
      border-color: #FFF078;
      box-shadow: 0 12px 28px rgba(255, 222, 36, 0.26);
      transform: translateY(-2px);
    }}

    .age-pill-years {{
      font-family: var(--font-num);
      font-size: 1.38rem;
      line-height: 1;
      letter-spacing: 0.03em;
      color: var(--text-white);
    }}

    .age-pill-btn.active .age-pill-years {{
      color: #050609;
    }}

    .age-pill-cat {{
      font-family: var(--font-mono);
      font-size: 0.63rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--acos-yellow);
    }}

    .age-pill-btn.active .age-pill-cat {{
      color: rgba(5, 6, 9, 0.82);
    }}

    .age-spotlight-card {{
      display: grid;
      grid-template-columns: 5fr 7fr;
      background: linear-gradient(165deg, #131926 0%, #0A0D14 100%);
      border: 1px solid rgba(255, 222, 36, 0.38);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 26px 60px rgba(0, 0, 0, 0.68);
      min-height: 350px;
    }}

    .asc-visual {{
      position: relative;
      background-size: cover;
      background-position: center 25%;
      padding: 1.65rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 290px;
      overflow: hidden;
    }}

    .asc-visual-veil {{
      position: absolute;
      inset: 0;
      background:
        linear-gradient(180deg, rgba(5, 6, 9, 0.25) 0%, rgba(10, 13, 20, 0.94) 100%),
        linear-gradient(90deg, rgba(5, 6, 9, 0.15) 0%, rgba(10, 13, 20, 0.78) 100%);
    }}

    .asc-watermark {{
      position: absolute;
      right: 14px;
      bottom: -8px;
      font-family: var(--font-num);
      font-size: 6.4rem;
      line-height: 0.82;
      color: rgba(255, 222, 36, 0.16);
      pointer-events: none;
      z-index: 1;
    }}

    .asc-visual-top,
    .asc-visual-bottom {{
      position: relative;
      z-index: 2;
    }}

    .asc-visual-bottom {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }}

    .asc-crest {{
      width: 48px;
      height: 66px;
      object-fit: contain;
      filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.85));
      flex-shrink: 0;
    }}

    .asc-body {{
      padding: 2rem 2.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1.2rem;
    }}

    .asc-header-title {{
      font-family: var(--font-display);
      font-size: clamp(1.48rem, 2.05vw, 1.88rem);
      font-weight: 900;
      line-height: 1.02;
      text-transform: uppercase;
      color: var(--text-white);
      margin-top: 0.25rem;
      white-space: nowrap;
    }}

    .asc-header-title span {{
      color: var(--acos-yellow);
    }}

    .asc-pitch-copy {{
      font-size: 0.9rem;
      color: var(--text-silver);
      line-height: 1.48;
      max-width: none;
    }}

    .asc-telemetry-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.75rem;
    }}

    .asc-telemetry-box {{
      background: rgba(5, 6, 9, 0.68);
      border: 1px solid rgba(255, 255, 255, 0.09);
      border-left: 3px solid var(--acos-yellow);
      border-radius: 8px;
      padding: 0.68rem 0.9rem;
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }}

    .asc-tel-lbl {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
    }}

    .asc-tel-val {{
      font-family: var(--font-display);
      font-size: 1.12rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--text-white);
      line-height: 1.15;
    }}

    .asc-tel-val.is-gold {{
      color: var(--acos-yellow);
    }}

    .asc-actions-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.85rem;
      padding-top: 0.25rem;
    }}

    /* 4 FASCE SETTORIALI PER #PAGE-SQUADRE (ZERO FOTO RIPETUTE) */
    .sector-bands-stack {{
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }}

    .sector-showcase-band {{
      display: grid;
      grid-template-columns: 360px 1fr;
      background: linear-gradient(165deg, #121722 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.11);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 22px 50px rgba(0, 0, 0, 0.6);
    }}

    .ssb-visual {{
      position: relative;
      background-size: cover;
      background-position: center 25%;
      padding: 1.65rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border-right: 1px solid rgba(255, 222, 36, 0.22);
      min-height: 280px;
      overflow: hidden;
    }}

    .ssb-visual-veil {{
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(5, 6, 9, 0.38) 0%, rgba(8, 10, 16, 0.96) 100%);
    }}

    .ssb-watermark {{
      position: absolute;
      right: 12px;
      top: 38px;
      font-family: var(--font-num);
      font-size: 5.8rem;
      line-height: 0.85;
      color: rgba(255, 222, 36, 0.13);
      pointer-events: none;
      z-index: 1;
    }}

    .ssb-visual-top,
    .ssb-visual-bottom {{
      position: relative;
      z-index: 2;
    }}

    .ssb-visual-top {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }}

    .ssb-num {{
      background: var(--acos-yellow);
      color: #050609;
      font-family: var(--font-display);
      font-size: 0.78rem;
      font-weight: 900;
      letter-spacing: 0.06em;
      padding: 0.18rem 0.6rem;
      border-radius: 4px;
      text-transform: uppercase;
    }}

    .ssb-highlight-pill {{
      background: rgba(5, 6, 9, 0.84);
      border: 1px solid rgba(255, 222, 36, 0.38);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 4px;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .ssb-eyebrow {{
      display: block;
      font-family: var(--font-mono);
      font-size: 0.64rem;
      font-weight: 700;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.3rem;
      white-space: nowrap;
    }}

    .ssb-title {{
      font-family: var(--font-display);
      font-size: 1.72rem;
      font-weight: 900;
      line-height: 0.96;
      text-transform: uppercase;
      color: var(--text-white);
      margin-bottom: 0.55rem;
      white-space: nowrap;
    }}

    .ssb-desc {{
      font-size: 0.84rem;
      color: var(--text-silver);
      line-height: 1.48;
    }}

    .ssb-matrix {{
      padding: 1.25rem 1.5rem;
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 0.75rem;
    }}

    .sector-team-row {{
      display: grid;
      grid-template-columns: 112px 1fr auto;
      align-items: center;
      gap: 1.1rem;
      background: rgba(255, 255, 255, 0.025);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 0.85rem 1.1rem;
      transition: all 0.18s ease;
    }}

    .sector-team-row:hover {{
      background: rgba(255, 222, 36, 0.05);
      border-color: rgba(255, 222, 36, 0.38);
      transform: translateX(3px);
    }}

    .str-year-box {{
      background: #06080D;
      border: 1px solid rgba(255, 222, 36, 0.36);
      border-radius: 8px;
      padding: 0.45rem 0.5rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
    }}

    .str-year-lbl {{
      font-family: var(--font-mono);
      font-size: 0.56rem;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .str-year-val {{
      font-family: var(--font-num);
      font-size: 1.32rem;
      line-height: 1.05;
      color: var(--acos-yellow);
      letter-spacing: 0.03em;
    }}

    .str-main-info {{
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      min-width: 0;
    }}

    .str-title-line {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.6rem;
    }}

    .str-team-name {{
      font-family: var(--font-display);
      font-size: 1.32rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--text-white);
      line-height: 1.05;
    }}

    .str-format-pill {{
      background: rgba(255, 255, 255, 0.07);
      border: 1px solid rgba(255, 255, 255, 0.14);
      color: var(--text-silver);
      font-family: var(--font-mono);
      font-size: 0.64rem;
      font-weight: 700;
      padding: 0.14rem 0.5rem;
      border-radius: 4px;
      text-transform: uppercase;
    }}

    .str-meta-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.85rem;
      font-size: 0.78rem;
      color: var(--text-silver);
    }}

    .str-meta-item.is-gold {{
      color: var(--acos-yellow);
      font-weight: 700;
    }}

    .str-actions {{
      display: flex;
      align-items: center;
      gap: 0.55rem;
      flex-shrink: 0;
    }}

    .btn-str-outline {{
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.18);
      color: var(--text-white);
      font-family: var(--font-display);
      font-size: 0.86rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      padding: 0.5rem 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.16s ease;
      white-space: nowrap;
    }}

    .btn-str-outline:hover {{
      border-color: var(--acos-yellow);
      color: var(--acos-yellow);
    }}

    .btn-str-gold {{
      background: linear-gradient(135deg, #FFE135 0%, #F2BE00 100%);
      border: 1px solid #FFF078;
      color: #050609;
      font-family: var(--font-display);
      font-size: 0.86rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      padding: 0.5rem 0.9rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.16s ease;
      white-space: nowrap;
    }}

    .btn-str-gold:hover {{
      filter: brightness(1.06);
      transform: translateY(-1px);
    }}

    @media (max-width: 1080px) {{
      .age-finder-pills {{
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }}
      .age-spotlight-card {{
        grid-template-columns: 1fr;
      }}
      .asc-header-title {{
        white-space: normal;
      }}
      .sector-showcase-band {{
        grid-template-columns: 1fr;
      }}
      .ssb-visual {{
        border-right: none;
        border-bottom: 1px solid rgba(255, 222, 36, 0.22);
        min-height: 220px;
      }}
    }}

    @media (max-width: 720px) {{
      .age-finder-pills {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .age-finder-pills .age-pill-btn:last-child {{
        grid-column: 1 / -1;
      }}
      .asc-telemetry-grid {{
        grid-template-columns: 1fr;
      }}
      .sector-team-row {{
        grid-template-columns: 1fr;
        gap: 0.65rem;
      }}
      .str-year-box {{
        flex-direction: row;
        justify-content: space-between;
        padding: 0.35rem 0.75rem;
      }}
      .str-actions {{
        width: 100%;
        display: grid;
        grid-template-columns: 1fr;
      }}
      .str-actions button {{
        width: 100%;
        justify-content: center;
      }}
    }}

    /* ==========================================================================
       9. SERIE A ASYMMETRIC EDITORIAL STORYBOARD (HOME ATTO III) & BENTO CARDS
       ========================================================================== */
    .seriea-storyboard {{
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}

    .storyboard-lead-card {{
      position: relative;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid rgba(255, 222, 36, 0.36);
      background: #07090F;
      min-height: 390px;
      display: flex;
      align-items: flex-end;
      padding: 2.5rem;
      box-shadow: 0 26px 64px rgba(0, 0, 0, 0.72);
    }}

    .storyboard-lead-bg {{
      position: absolute;
      inset: 0;
      background-size: cover;
      background-position: center 28%;
      filter: contrast(1.18) saturate(1.22) brightness(0.82);
      transition: transform 0.65s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    .storyboard-lead-card:hover .storyboard-lead-bg {{
      transform: scale(1.04);
    }}

    .storyboard-lead-veil {{
      position: absolute;
      inset: 0;
      background:
        linear-gradient(90deg, rgba(4, 5, 8, 0.95) 0%, rgba(4, 5, 8, 0.76) 54%, rgba(4, 5, 8, 0.22) 100%),
        linear-gradient(180deg, rgba(4, 5, 8, 0.15) 0%, rgba(4, 5, 8, 0.92) 100%);
    }}

    .storyboard-lead-watermark {{
      position: absolute;
      top: 18px;
      right: 24px;
      font-family: var(--font-num);
      font-size: clamp(4.2rem, 9vw, 8.5rem);
      line-height: 0.82;
      color: transparent;
      -webkit-text-stroke: 1.5px rgba(255, 222, 36, 0.16);
      letter-spacing: 0.04em;
      pointer-events: none;
      user-select: none;
    }}

    .storyboard-lead-content {{
      position: relative;
      z-index: 2;
      max-width: 690px;
      display: flex;
      flex-direction: column;
      gap: 0.95rem;
    }}

    .storyboard-lead-title {{
      font-family: var(--font-display);
      font-size: clamp(2rem, 3.6vw, 3.05rem);
      font-weight: 900;
      line-height: 0.95;
      text-transform: uppercase;
      color: var(--text-white);
      letter-spacing: 0.01em;
    }}

    .storyboard-lead-title span {{
      color: var(--acos-yellow);
    }}

    .storyboard-lead-copy {{
      font-size: 0.98rem;
      color: var(--text-silver);
      line-height: 1.58;
      max-width: 60ch;
    }}

    .storyboard-kpi-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
      margin-top: 0.15rem;
    }}

    .storyboard-kpi-pill {{
      background: rgba(12, 16, 24, 0.86);
      border: 1px solid rgba(255, 222, 36, 0.34);
      border-radius: 6px;
      padding: 0.38rem 0.78rem;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--text-white);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}

    .storyboard-kpi-pill strong {{
      color: var(--acos-yellow);
    }}

    .storyboard-duo-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1.5rem;
    }}

    .storyboard-card {{
      position: relative;
      background: linear-gradient(165deg, #131824 0%, #0B0E16 100%);
      border: 1px solid rgba(255, 255, 255, 0.11);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
    }}

    .storyboard-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
      box-shadow: 0 22px 48px rgba(0, 0, 0, 0.68);
    }}

    .storyboard-card-visual {{
      position: relative;
      height: 220px;
      background-size: cover;
      background-position: center 25%;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      padding: 1.25rem 1.5rem;
      overflow: hidden;
    }}

    .storyboard-card-visual::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(5, 6, 9, 0.08) 0%, rgba(11, 14, 22, 0.84) 100%);
    }}

    .storyboard-corner-emblem {{
      position: absolute;
      top: 14px;
      right: 16px;
      z-index: 2;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      background: rgba(5, 6, 9, 0.82);
      border: 1px solid rgba(255, 222, 36, 0.45);
      border-radius: 8px;
      padding: 0.32rem 0.65rem;
      backdrop-filter: blur(8px);
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      color: var(--acos-yellow);
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}

    .storyboard-card-body {{
      padding: 1.4rem 1.5rem 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      flex: 1;
    }}

    .storyboard-card-title {{
      font-family: var(--font-display);
      font-size: 1.62rem;
      font-weight: 900;
      line-height: 1.02;
      text-transform: uppercase;
      color: var(--text-white);
      white-space: nowrap;
    }}

    .storyboard-card-copy {{
      font-size: 0.9rem;
      color: var(--text-silver);
      line-height: 1.56;
    }}

    .storyboard-meta-list {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.55rem;
      margin-top: 0.15rem;
    }}

    .storyboard-meta-box {{
      background: rgba(5, 6, 9, 0.65);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-left: 2px solid var(--acos-yellow);
      border-radius: 6px;
      padding: 0.48rem 0.68rem;
    }}

    .storyboard-meta-lbl {{
      display: block;
      font-family: var(--font-mono);
      font-size: 0.6rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}

    .storyboard-meta-val {{
      display: block;
      font-family: var(--font-display);
      font-size: 0.98rem;
      font-weight: 800;
      color: var(--text-white);
      text-transform: uppercase;
      margin-top: 0.08rem;
    }}

    .bento-4-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
      gap: 1.35rem;
    }}

    .bento-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.22s ease, border-color 0.22s ease;
    }}

    .bento-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-border-gold);
    }}

    .bento-photo {{
      aspect-ratio: 16 / 10;
      overflow: hidden;
      background: #07090E;
      position: relative;
    }}

    .bento-photo img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.45s ease;
    }}

    .bento-card:hover .bento-photo img {{
      transform: scale(1.05);
    }}

    /* Per i banner istituzionali su sfondo bianco (Scuola Calcio FIGC) */
    .bento-photo.logo-plate {{
      background: #FFFFFF;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.25rem;
    }}

    .bento-photo.logo-plate img {{
      object-fit: contain !important;
      max-height: 100%;
    }}

    .bento-body {{
      padding: 1.35rem;
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
      flex: 1;
    }}

    .bento-body h3 {{
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 900;
      text-transform: uppercase;
      line-height: 1.05;
    }}

    .bento-body p {{
      font-size: 0.88rem;
      color: var(--text-silver);
      flex: 1;
    }}

    /* Official Club Partners Wall: Matrice Paritaria 5x2 su PC e 2x5 su Mobile (100% Visibilità Simultanea, Zero Partner Nascosti) */
    .sponsors-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 1rem;
      width: 100%;
      align-items: stretch;
    }}

    .sponsor-card {{
      background: linear-gradient(165deg, rgba(20, 25, 38, 0.9) 0%, rgba(9, 12, 18, 0.95) 100%);
      border: 1px solid rgba(255, 222, 36, 0.24);
      border-radius: 12px;
      padding: 0.5rem;
      display: flex;
      flex-direction: column;
      justify-content: center;
      transition: all 0.22s ease;
    }}

    .sponsor-card:hover {{
      border-color: var(--acos-yellow);
      transform: translateY(-3px);
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.65), 0 0 18px rgba(255, 222, 36, 0.14);
    }}

    .sponsor-plate {{
      background: #FFFFFF;
      border-radius: 8px;
      height: 84px;
      padding: 0.55rem 0.9rem;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}

    .sponsor-plate img {{
      max-height: 58px;
      max-width: 175px;
      width: auto;
      height: auto;
      object-fit: contain;
    }}

    .sponsor-caption {{
      display: flex;
      flex-direction: column;
    }}

    .sponsor-tier {{
      font-size: 0.66rem;
      color: var(--acos-yellow);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .sponsor-brand {{
      font-family: var(--font-display);
      font-size: 1.1rem;
      text-transform: uppercase;
    }}

    /* Photo Gallery Grid */
    .photo-gallery-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1rem;
    }}

    .gallery-thumb {{
      aspect-ratio: 16 / 10;
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid var(--acos-border-gold);
      cursor: pointer;
    }}

    .gallery-thumb img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.35s ease;
    }}

    .gallery-thumb:hover img {{
      transform: scale(1.06);
    }}

    /* Timeline & Board */
    .timeline-wrap {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}

    .timeline-step {{
      display: grid;
      grid-template-columns: 48px 1fr;
      gap: 1rem;
      align-items: start;
    }}

    .tl-badge {{
      width: 48px;
      height: 48px;
      border-radius: 10px;
      background: var(--acos-yellow);
      color: #050609;
      font-family: var(--font-num);
      font-size: 1.5rem;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .tl-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.15rem;
    }}

    .tl-year {{
      font-family: var(--font-mono);
      font-size: 0.76rem;
      color: var(--acos-yellow);
      font-weight: 800;
    }}

    .tl-card h3 {{
      font-family: var(--font-display);
      font-size: 1.35rem;
      text-transform: uppercase;
      margin: 0.2rem 0 0.4rem;
    }}

    .tl-card p {{
      font-size: 0.88rem;
      color: var(--text-silver);
    }}

    /* ==========================================================================
       10B. ARCHITETTURA CINEMATOGRAFICA #PAGE-CLUB (4 ATTI SERIE A HERITAGE)
       ========================================================================== */
    .club-manifesto-banner {{
      position: relative;
      background:
        radial-gradient(620px circle at 12% 18%, rgba(255, 222, 36, 0.14) 0%, transparent 65%),
        linear-gradient(155deg, #131926 0%, #080A10 100%);
      border: 1px solid rgba(255, 222, 36, 0.38);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 18px;
      padding: 2.5rem;
      overflow: hidden;
      box-shadow: 0 28px 64px rgba(0, 0, 0, 0.68);
      margin-bottom: 2rem;
    }}

    .club-manifesto-watermark {{
      position: absolute;
      right: 28px;
      top: 10px;
      font-family: var(--font-num);
      font-size: clamp(5.5rem, 11vw, 9.8rem);
      line-height: 0.82;
      color: transparent;
      -webkit-text-stroke: 1.5px rgba(255, 222, 36, 0.13);
      pointer-events: none;
      user-select: none;
      z-index: 1;
    }}

    .club-manifesto-grid {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 2.25rem;
      align-items: stretch;
    }}

    .cmb-copy-col {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1.25rem;
    }}

    .cmb-eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .cmb-title {{
      font-family: var(--font-display);
      font-size: clamp(2.25rem, 4vw, 3.45rem);
      font-weight: 900;
      line-height: 0.94;
      text-transform: uppercase;
      color: var(--text-white);
      letter-spacing: 0.01em;
      margin: 0;
    }}

    .cmb-title span {{
      color: var(--acos-yellow);
      display: block;
    }}

    .cmb-lead {{
      font-size: 0.96rem;
      color: var(--text-silver);
      line-height: 1.6;
      max-width: 62ch;
      margin: 0;
    }}

    .cmb-kpi-strip {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 0.75rem;
      margin-top: auto;
    }}

    .cmb-kpi-box {{
      background: rgba(5, 6, 9, 0.78);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-top: 2px solid var(--acos-yellow);
      border-radius: 10px;
      padding: 0.72rem 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      min-width: 0;
    }}

    .cmb-kpi-num {{
      font-family: var(--font-num);
      font-size: 1.65rem;
      line-height: 1;
      color: var(--acos-yellow);
      white-space: nowrap;
    }}

    .cmb-kpi-lbl {{
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 700;
      color: var(--text-silver);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .cmb-archive-wrap {{
      position: relative;
      z-index: 2;
      display: flex;
      flex-direction: column;
      height: 100%;
    }}

    .cmb-archive-duo {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1rem;
      align-items: stretch;
      flex: 1;
    }}

    .cmb-archive-card {{
      position: relative;
      border-radius: 14px;
      overflow: hidden;
      border: 1px solid rgba(255, 222, 36, 0.36);
      background: #050609;
      cursor: pointer;
      min-height: 300px;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.58);
      transition: transform 0.25s ease, border-color 0.25s ease;
    }}

    .cmb-archive-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
    }}

    .cmb-archive-card img {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center 25%;
      filter: contrast(1.12) brightness(0.88);
      transition: transform 0.45s ease;
      z-index: 1;
    }}

    .cmb-archive-card:hover img {{
      transform: scale(1.06);
    }}

    .cmb-archive-tag {{
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 3;
      background: rgba(5, 6, 9, 0.88);
      border: 1px solid rgba(255, 222, 36, 0.45);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 800;
      padding: 0.22rem 0.52rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .cmb-archive-zoom {{
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 3;
      background: rgba(5, 6, 9, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.22);
      color: var(--text-white);
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 700;
      padding: 0.2rem 0.45rem;
      border-radius: 4px;
    }}

    .cmb-archive-caption {{
      position: relative;
      z-index: 2;
      width: 100%;
      padding: 2.6rem 0.95rem 0.95rem;
      background: linear-gradient(180deg, transparent 0%, rgba(5, 6, 9, 0.9) 45%, rgba(5, 6, 9, 0.98) 100%);
      display: flex;
      flex-direction: column;
      gap: 0.22rem;
    }}

    .cmb-archive-caption h4 {{
      font-family: var(--font-display);
      font-size: 1.15rem;
      font-weight: 900;
      color: var(--text-white);
      text-transform: uppercase;
      line-height: 1.05;
      margin: 0;
    }}

    .cmb-archive-caption p {{
      font-size: 0.78rem;
      color: var(--text-silver);
      line-height: 1.38;
      margin: 0;
    }}

    /* GRIGLIA ORIZZONTALE 3x2 PER LE 6 TAPPE STORICHE */
    .heritage-milestone-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1.15rem;
      margin-bottom: 3.5rem;
    }}

    .heritage-milestone-card {{
      position: relative;
      background: linear-gradient(165deg, #121722 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-top: 2px solid rgba(255, 222, 36, 0.55);
      border-radius: 14px;
      padding: 1.35rem 1.4rem;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
      transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
    }}

    .heritage-milestone-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.6);
    }}

    .hmc-watermark {{
      position: absolute;
      right: 12px;
      bottom: -8px;
      font-family: var(--font-num);
      font-size: 4.8rem;
      line-height: 0.85;
      color: rgba(255, 222, 36, 0.09);
      pointer-events: none;
    }}

    .hmc-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }}

    .hmc-step-badge {{
      background: rgba(255, 222, 36, 0.14);
      border: 1px solid rgba(255, 222, 36, 0.35);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 700;
      padding: 0.16rem 0.5rem;
      border-radius: 4px;
      text-transform: uppercase;
    }}

    .hmc-year-pill {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--text-white);
      text-transform: uppercase;
    }}

    .hmc-title {{
      font-family: var(--font-display);
      font-size: 1.45rem;
      font-weight: 900;
      line-height: 1.02;
      text-transform: uppercase;
      color: var(--text-white);
      margin-top: 0.15rem;
    }}

    .hmc-desc {{
      font-size: 0.86rem;
      color: var(--text-silver);
      line-height: 1.5;
      position: relative;
      z-index: 2;
    }}

    /* ATTO II: GOTHIA CUP SVEZIA & CINA DUAL ARENA STAGE */
    .gothia-arena-stage {{
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(640px circle at 88% 12%, rgba(255, 222, 36, 0.12) 0%, transparent 65%),
        linear-gradient(170deg, #111622 0%, #07090E 100%);
      border: 1px solid rgba(255, 222, 36, 0.35);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 18px;
      padding: 2.35rem;
      margin-bottom: 3.5rem;
      box-shadow: 0 26px 60px rgba(0, 0, 0, 0.65);
    }}

    .gothia-stage-watermark {{
      position: absolute;
      right: 24px;
      top: 14px;
      font-family: var(--font-num);
      font-size: clamp(3.8rem, 7.5vw, 6.8rem);
      line-height: 0.85;
      color: transparent;
      -webkit-text-stroke: 1.5px rgba(255, 222, 36, 0.11);
      pointer-events: none;
      user-select: none;
      z-index: 1;
    }}

    .gothia-stage-header {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1.5rem;
      flex-wrap: wrap;
      padding-bottom: 1.35rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }}

    .gothia-world-pill {{
      background: rgba(255, 222, 36, 0.12);
      border: 1px solid rgba(255, 222, 36, 0.42);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      padding: 0.5rem 0.95rem;
      border-radius: 8px;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .gothia-dual-grid {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1.5rem;
      margin: 1.6rem 0;
    }}

    .gothia-monument-card {{
      background: linear-gradient(165deg, #131926 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.55);
      transition: transform 0.24s ease, border-color 0.24s ease;
    }}

    .gothia-monument-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
    }}

    .gothia-monument-visual {{
      position: relative;
      height: 235px;
      overflow: hidden;
      cursor: pointer;
      background: #050609;
    }}

    .gothia-monument-visual img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center 28%;
      filter: contrast(1.12) saturate(1.14) brightness(0.86);
      transition: transform 0.45s ease;
    }}

    .gothia-monument-card:hover .gothia-monument-visual img {{
      transform: scale(1.05);
    }}

    .gothia-monument-visual::after {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(5, 6, 9, 0.24) 0%, rgba(9, 12, 18, 0.94) 100%);
      pointer-events: none;
    }}

    .gothia-monument-badges {{
      position: absolute;
      top: 14px;
      left: 14px;
      right: 14px;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}

    .gothia-country-tag {{
      background: var(--acos-yellow);
      color: #050609;
      font-family: var(--font-display);
      font-size: 0.8rem;
      font-weight: 900;
      padding: 0.2rem 0.65rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .gothia-edition-tag {{
      background: rgba(5, 6, 9, 0.86);
      border: 1px solid rgba(255, 222, 36, 0.42);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.6rem;
      font-weight: 800;
      padding: 0.22rem 0.55rem;
      border-radius: 4px;
      text-transform: uppercase;
    }}

    .gothia-monument-body {{
      position: relative;
      padding: 1.45rem 1.55rem 1.6rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1rem;
      flex: 1;
      overflow: hidden;
    }}

    .gothia-monument-watermark {{
      position: absolute;
      right: 14px;
      bottom: -8px;
      font-family: var(--font-num);
      font-size: 5.2rem;
      line-height: 0.84;
      color: rgba(255, 222, 36, 0.08);
      pointer-events: none;
      user-select: none;
    }}

    .gothia-monument-title {{
      position: relative;
      z-index: 2;
      font-family: var(--font-display);
      font-size: 1.65rem;
      font-weight: 900;
      text-transform: uppercase;
      line-height: 1.0;
      color: var(--text-white);
      margin: 0;
    }}

    .gothia-monument-desc {{
      position: relative;
      z-index: 2;
      font-size: 0.9rem;
      color: var(--text-silver);
      line-height: 1.55;
      margin: 0;
    }}

    .gothia-kpi-row {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.6rem;
      margin-top: auto;
    }}

    .gothia-kpi-cell {{
      background: rgba(5, 6, 9, 0.72);
      border: 1px solid rgba(255, 222, 36, 0.28);
      border-top: 2px solid var(--acos-yellow);
      border-radius: 8px;
      padding: 0.55rem 0.6rem;
      text-align: center;
    }}

    .gothia-kpi-val {{
      display: block;
      font-family: var(--font-display);
      font-size: 1.15rem;
      font-weight: 900;
      color: var(--acos-yellow);
      text-transform: uppercase;
      line-height: 1.05;
      white-space: nowrap;
    }}

    .gothia-kpi-lbl {{
      display: block;
      font-family: var(--font-mono);
      font-size: 0.56rem;
      font-weight: 700;
      color: var(--text-silver);
      text-transform: uppercase;
      margin-top: 0.14rem;
      white-space: nowrap;
    }}

    .gothia-gallery-bar-label {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.5rem;
      font-family: var(--font-mono);
      font-size: 0.66rem;
      font-weight: 800;
      color: var(--acos-yellow);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin: 0.2rem 0 0.85rem;
      padding-top: 1rem;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }}

    /* ATTO IV: FONDAZIONE ETICA CUORE GIALLONERO — IVAN ARZILLI */
    .cuore-ethical-stage {{
      background:
        radial-gradient(580px circle at 10% 15%, rgba(255, 222, 36, 0.12) 0%, transparent 65%),
        linear-gradient(155deg, #16140A 0%, #090C13 100%);
      border: 1px solid rgba(255, 222, 36, 0.42);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 18px;
      padding: 2.35rem;
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.65);
    }}

    .cuore-lead-banner {{
      display: grid;
      grid-template-columns: 108px 1.35fr 0.95fr;
      align-items: center;
      gap: 1.65rem;
      background: rgba(5, 6, 9, 0.76);
      border: 1px solid rgba(255, 222, 36, 0.32);
      border-left: 4px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.5rem 1.75rem;
      margin-bottom: 1.65rem;
    }}

    .cuore-emblem-box {{
      position: relative;
      width: 108px;
      height: 108px;
      border-radius: 18px;
      background: radial-gradient(circle at 50% 45%, rgba(255, 222, 36, 0.18) 0%, #06080E 78%);
      border: 1px solid rgba(255, 222, 36, 0.48);
      padding: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 14px 32px rgba(0, 0, 0, 0.72), inset 0 0 18px rgba(255, 222, 36, 0.08);
      flex-shrink: 0;
      transition: transform 0.22s ease, border-color 0.22s ease;
    }}

    .cuore-emblem-box:hover {{
      transform: scale(1.05);
      border-color: var(--acos-yellow);
    }}

    .cuore-emblem-svg {{
      width: 90px;
      height: 90px;
      filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.85));
    }}

    .cuore-emblem-crest {{
      position: absolute;
      width: 30px;
      height: 42px;
      object-fit: contain;
      top: 51%;
      left: 50%;
      transform: translate(-50%, -50%);
      filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.9));
      pointer-events: none;
    }}

    .cuore-lead-copy {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      min-width: 0;
    }}

    .cuore-lead-copy h3 {{
      font-family: var(--font-display);
      font-size: clamp(1.65rem, 2.5vw, 2.15rem);
      font-weight: 900;
      text-transform: uppercase;
      line-height: 0.98;
      color: var(--text-white);
      margin: 0;
    }}

    .cuore-lead-copy p {{
      font-size: 0.92rem;
      color: var(--text-silver);
      line-height: 1.55;
      margin: 0;
    }}

    .cuore-strada-quote {{
      background: linear-gradient(145deg, rgba(255, 222, 36, 0.1) 0%, rgba(10, 13, 20, 0.9) 100%);
      border: 1px solid rgba(255, 222, 36, 0.36);
      border-left: 3px solid var(--acos-yellow);
      border-radius: 12px;
      padding: 1.15rem 1.3rem;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }}

    .csq-tag {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}

    .csq-text {{
      font-size: 0.86rem;
      color: var(--text-white);
      line-height: 1.5;
      font-style: italic;
      margin: 0;
    }}

    .cuore-pillars-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1.25rem;
    }}

    .cuore-pillar-card {{
      background: linear-gradient(165deg, #131824 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.11);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.45rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.45);
    }}

    .cuore-pillar-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 0.75rem;
      padding-bottom: 0.85rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .cuore-pillar-num {{
      display: block;
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 0.2rem;
    }}

    .cuore-pillar-title {{
      font-family: var(--font-display);
      font-size: 1.45rem;
      font-weight: 900;
      text-transform: uppercase;
      color: var(--text-white);
      line-height: 1.02;
      margin: 0;
    }}

    .cuore-pillar-icon {{
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: rgba(255, 222, 36, 0.12);
      border: 1px solid rgba(255, 222, 36, 0.34);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 1.05rem;
      flex-shrink: 0;
    }}

    .cuore-charity-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
    }}

    .cuore-charity-item {{
      display: grid;
      grid-template-columns: 10px 1fr;
      gap: 0.6rem;
      align-items: baseline;
      font-size: 0.83rem;
      color: var(--text-silver);
      line-height: 1.42;
      padding: 0.5rem 0.65rem;
      background: rgba(5, 6, 9, 0.58);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
    }}

    .cuore-charity-item strong {{
      color: var(--text-white);
      font-weight: 700;
    }}

    .cci-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--acos-yellow);
      box-shadow: 0 0 8px rgba(255, 222, 36, 0.6);
      display: inline-block;
      transform: translateY(-1px);
    }}

    @media (max-width: 1080px) {{
      .club-manifesto-grid {{
        grid-template-columns: 1fr;
      }}
      .heritage-milestone-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .gothia-dual-grid {{
        grid-template-columns: 1fr;
      }}
      .cuore-lead-banner {{
        grid-template-columns: 1fr;
      }}
      .cuore-pillars-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 720px) {{
      .cmb-kpi-strip {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .cmb-archive-duo {{
        grid-template-columns: 1fr;
      }}
      .heritage-milestone-grid {{
        grid-template-columns: 1fr;
      }}
      .gothia-kpi-row {{
        grid-template-columns: 1fr;
      }}
    }}

    .board-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1rem;
    }}

    .board-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 10px;
      padding: 1.25rem;
    }}

    .board-role {{
      font-size: 0.72rem;
      color: var(--acos-yellow);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}

    .board-name {{
      font-family: var(--font-display);
      font-size: 1.45rem;
      font-weight: 900;
      text-transform: uppercase;
      margin-top: 0.2rem;
    }}

    /* ==========================================================================
       SERIE A EXECUTIVE ORGANIGRAMMA (BROADCAST 3-TIER GOVERNANCE STAGE)
       ========================================================================== */
    .org-stage {{
      position: relative;
      background-color: #06080E;
      background-image:
        radial-gradient(ellipse 80% 45% at 50% 0%, rgba(255, 222, 36, 0.16) 0%, transparent 70%),
        repeating-linear-gradient(-45deg, rgba(255, 222, 36, 0.022) 0px, rgba(255, 222, 36, 0.022) 1px, transparent 1px, transparent 14px),
        linear-gradient(180deg, rgba(8, 11, 18, 0.94) 0%, rgba(5, 6, 10, 0.98) 100%);
      border: 1px solid rgba(255, 222, 36, 0.32);
      border-top: 4px solid var(--acos-yellow);
      border-radius: 18px;
      padding: 2.6rem 2.5rem;
      margin-bottom: 3rem;
      box-shadow: 0 30px 70px rgba(0, 0, 0, 0.85), inset 0 1px 0 rgba(255, 255, 255, 0.12);
      overflow: hidden;
    }}

    .org-stage-bg-watermark {{
      position: absolute;
      top: 12px;
      right: 24px;
      font-family: var(--font-num);
      font-size: clamp(5rem, 11vw, 9.5rem);
      line-height: 0.82;
      color: rgba(255, 222, 36, 0.035);
      letter-spacing: 0.04em;
      pointer-events: none;
      user-select: none;
      z-index: 0;
    }}

    .org-stage-header {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1.25rem;
      padding-bottom: 1.6rem;
      margin-bottom: 1.85rem;
      border-bottom: 1px solid rgba(255, 222, 36, 0.22);
    }}

    .org-stage-header::after {{
      content: "";
      position: absolute;
      left: 0;
      bottom: -2px;
      width: 140px;
      height: 3px;
      background: var(--acos-yellow);
      box-shadow: 0 0 14px rgba(255, 222, 36, 0.75);
    }}

    .org-fed-seal {{
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      background: linear-gradient(135deg, rgba(20, 25, 38, 0.95) 0%, rgba(8, 10, 16, 0.98) 100%);
      border: 1px solid var(--acos-border-gold);
      border-left: 3px solid var(--acos-yellow);
      border-radius: 8px;
      padding: 0.65rem 1.05rem;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.07em;
      box-shadow: 0 10px 24px rgba(0, 0, 0, 0.55);
    }}

    /* Connettori Gerarchici Stile Broadcast TV (Catena di Comando) */
    .org-tier-label-bar {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      gap: 0.85rem;
      margin-bottom: 0.95rem;
    }}

    .org-tier-tag {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      font-family: var(--font-mono);
      font-size: 0.68rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      background: rgba(255, 222, 36, 0.1);
      border: 1px solid rgba(255, 222, 36, 0.32);
      padding: 0.25rem 0.7rem;
      border-radius: 4px;
      white-space: nowrap;
    }}

    .org-tier-rail {{
      flex: 1;
      height: 1px;
      background: linear-gradient(90deg, rgba(255, 222, 36, 0.45) 0%, rgba(255, 255, 255, 0.06) 100%);
    }}

    .org-connector-bridge {{
      position: relative;
      z-index: 2;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0.15rem 0 0.35rem;
    }}

    .org-connector-bridge::before {{
      content: "";
      position: absolute;
      top: 0;
      bottom: 0;
      left: 50%;
      width: 2px;
      transform: translateX(-50%);
      background: linear-gradient(180deg, var(--acos-yellow) 0%, rgba(255, 222, 36, 0.25) 100%);
    }}

    .org-connector-bridge::after {{
      content: "";
      position: absolute;
      bottom: 4px;
      left: 12%;
      right: 12%;
      height: 1px;
      background: linear-gradient(90deg, transparent 0%, rgba(255, 222, 36, 0.45) 20%, var(--acos-yellow) 50%, rgba(255, 222, 36, 0.45) 80%, transparent 100%);
    }}

    .org-connector-node {{
      width: 10px;
      height: 10px;
      background: var(--acos-yellow);
      border: 2px solid #050609;
      transform: rotate(45deg);
      box-shadow: 0 0 12px rgba(255, 222, 36, 0.9);
      position: relative;
      z-index: 3;
    }}

    /* Tier 1: Vertice Presidenziale (2 Poster Card Monumentali Serie A) */
    .org-tier-presidency {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1.5rem;
    }}

    .org-pres-card {{
      position: relative;
      background:
        radial-gradient(circle at 88% 18%, rgba(255, 222, 36, 0.18) 0%, transparent 55%),
        linear-gradient(145deg, #171D2C 0%, #0A0D15 65%, #07090F 100%);
      border: 1px solid rgba(255, 222, 36, 0.42);
      border-top: 4px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.85rem 2rem;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.7);
      transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
    }}

    .org-pres-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
      box-shadow: 0 24px 52px rgba(0, 0, 0, 0.85), 0 0 28px rgba(255, 222, 36, 0.16);
    }}

    .org-pres-body {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      gap: 1.5rem;
      margin: 0.75rem 0 1.25rem;
    }}

    .org-pres-shield {{
      width: 82px;
      height: 100px;
      border-radius: 12px;
      background: radial-gradient(circle at 50% 30%, rgba(255, 222, 36, 0.22) 0%, rgba(8, 10, 16, 0.95) 75%);
      border: 1.5px solid rgba(255, 222, 36, 0.55);
      box-shadow: inset 0 0 18px rgba(255, 222, 36, 0.15), 0 10px 24px rgba(0, 0, 0, 0.65);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      position: relative;
    }}

    .org-pres-shield img {{
      width: 58px;
      height: 74px;
      object-fit: contain;
      filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.85));
    }}

    .org-name-stack {{
      display: flex;
      flex-direction: column;
      min-width: 0;
    }}

    .org-first-name {{
      font-family: var(--font-sans);
      font-size: 0.8rem;
      font-weight: 800;
      color: var(--text-silver);
      text-transform: uppercase;
      letter-spacing: 0.2em;
      line-height: 1.1;
      margin-bottom: 0.15rem;
    }}

    .org-last-name {{
      font-family: var(--font-display);
      font-size: clamp(2.35rem, 3.2vw, 3.05rem);
      font-weight: 900;
      line-height: 0.92;
      letter-spacing: 0.02em;
      color: var(--text-white);
      text-transform: uppercase;
      text-shadow: 0 6px 20px rgba(0, 0, 0, 0.75);
    }}

    .org-gold-slash {{
      width: 44px;
      height: 3px;
      background: var(--acos-yellow);
      margin-top: 0.55rem;
      border-radius: 2px;
      box-shadow: 0 0 10px rgba(255, 222, 36, 0.6);
    }}

    .org-telemetry-bar {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
      padding-top: 0.85rem;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      margin-top: auto;
    }}

    .org-tel-cell {{
      display: flex;
      flex-direction: column;
      gap: 0.12rem;
    }}

    .org-tel-lbl {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .org-tel-val {{
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--text-white);
    }}

    .org-exec-card {{
      position: relative;
      background:
        radial-gradient(circle at 92% 12%, rgba(255, 222, 36, 0.10) 0%, transparent 55%),
        linear-gradient(165deg, #141926 0%, #090C13 100%);
      border: 1px solid rgba(255, 255, 255, 0.13);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 12px;
      padding: 1.45rem 1.5rem;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 14px 32px rgba(0, 0, 0, 0.6);
      transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
    }}

    .org-exec-card:hover {{
      transform: translateY(-4px);
      border-color: var(--acos-yellow);
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.8), 0 0 22px rgba(255, 222, 36, 0.14);
    }}

    .org-watermark {{
      position: absolute;
      right: 12px;
      bottom: -12px;
      font-family: var(--font-num);
      font-size: 5.8rem;
      line-height: 0.82;
      color: rgba(255, 222, 36, 0.065);
      pointer-events: none;
      user-select: none;
      z-index: 0;
    }}

    .org-pres-card .org-watermark {{
      font-size: 7.8rem;
      color: rgba(255, 222, 36, 0.085);
    }}

    .org-card-top {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.65rem;
      margin-bottom: 0.95rem;
    }}

    .org-role-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: rgba(255, 222, 36, 0.13);
      border: 1px solid rgba(255, 222, 36, 0.4);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.66rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 0.26rem 0.65rem;
      border-radius: 4px;
    }}

    .org-pres-card .org-role-badge {{
      background: var(--acos-yellow);
      color: #050609;
      border-color: var(--acos-yellow);
      font-size: 0.7rem;
      padding: 0.3rem 0.75rem;
    }}

    .org-monogram-shield {{
      width: 40px;
      height: 44px;
      border-radius: 8px;
      background: linear-gradient(145deg, rgba(255, 222, 36, 0.2) 0%, rgba(10, 13, 20, 0.95) 100%);
      border: 1px solid rgba(255, 222, 36, 0.5);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-size: 1.1rem;
      font-weight: 900;
      color: var(--acos-yellow);
      letter-spacing: 0.04em;
      flex-shrink: 0;
      box-shadow: inset 0 0 10px rgba(255, 222, 36, 0.12);
    }}

    .org-exec-card .org-first-name {{
      font-size: 0.73rem;
      letter-spacing: 0.18em;
    }}

    .org-exec-card .org-last-name {{
      font-size: clamp(1.75rem, 2.2vw, 2.15rem);
    }}

    .org-exec-desc {{
      position: relative;
      z-index: 2;
      font-size: 0.8rem;
      line-height: 1.45;
      color: var(--text-silver);
      padding-top: 0.75rem;
      margin-top: 0.9rem;
      border-top: 1px solid rgba(255, 255, 255, 0.09);
    }}

    .org-exec-desc strong {{
      display: block;
      font-family: var(--font-mono);
      font-size: 0.63rem;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 0.15rem;
    }}

    /* Tier 2: Direzione Esecutiva, Tecnica & Segreteria (4 Colonne Simmetriche) */
    .org-tier-management {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1.15rem;
    }}

    /* Tier 3: Consiglio Direttivo (Plancia Orizzontale Serie A a 5 Colonne) */
    .org-council-deck {{
      position: relative;
      z-index: 2;
      background:
        radial-gradient(circle at 50% 0%, rgba(255, 222, 36, 0.08) 0%, transparent 70%),
        linear-gradient(180deg, rgba(13, 17, 26, 0.96) 0%, rgba(7, 9, 14, 0.98) 100%);
      border: 1px solid rgba(255, 222, 36, 0.25);
      border-left: 4px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.5rem 1.65rem;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65);
    }}

    .org-council-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 1.15rem;
      padding-bottom: 0.85rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .org-council-title {{
      font-family: var(--font-display);
      font-size: 1.45rem;
      font-weight: 900;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .org-council-sub {{
      font-family: var(--font-mono);
      font-size: 0.68rem;
      color: var(--text-silver);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .org-council-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 0.95rem;
    }}

    .org-councilor-card {{
      position: relative;
      background: linear-gradient(165deg, #151A28 0%, #0B0E16 100%);
      border: 1px solid rgba(255, 255, 255, 0.11);
      border-top: 3px solid rgba(255, 222, 36, 0.75);
      border-radius: 10px;
      padding: 1.05rem 1.1rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.65rem;
      overflow: hidden;
      transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .org-councilor-card:hover {{
      border-color: var(--acos-yellow);
      transform: translateY(-3px);
      box-shadow: 0 12px 26px rgba(0, 0, 0, 0.65);
    }}

    .org-councilor-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }}

    .org-councilor-role {{
      font-family: var(--font-mono);
      font-size: 0.61rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .org-councilor-avatar {{
      width: 30px;
      height: 30px;
      border-radius: 6px;
      background: rgba(255, 222, 36, 0.14);
      border: 1px solid rgba(255, 222, 36, 0.42);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-size: 0.88rem;
      font-weight: 900;
      color: var(--acos-yellow);
      flex-shrink: 0;
    }}

    .org-councilor-card .org-first-name {{
      font-size: 0.68rem;
      letter-spacing: 0.16em;
    }}

    .org-councilor-card .org-last-name {{
      font-size: 1.55rem;
      line-height: 0.95;
    }}

    @media (max-width: 1100px) {{
      .org-tier-management {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .org-council-grid {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}
    }}

    @media (max-width: 720px) {{
      .org-stage {{
        padding: 1.35rem;
      }}
      .org-pres-body {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .org-tier-presidency,
      .org-tier-management,
      .org-council-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .charities-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 0.65rem;
      margin-top: 1.25rem;
    }}

    .charity-pill {{
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.6rem 0.85rem;
      font-size: 0.82rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    /* ==========================================================================
       SEGRETERIA DIGITALE SERIE A (SEASON PASS, TESORERIA IBAN, PORTALI & SAFEGUARDING)
       ========================================================================== */
    .sp-header-kit-pill {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      background: rgba(255, 222, 36, 0.12);
      border: 1px solid rgba(255, 222, 36, 0.42);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.68rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.42rem 0.85rem;
      border-radius: 8px;
    }}

    .season-pass-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1.25rem;
      margin: 1rem 0 1.65rem;
    }}

    .season-pass-card {{
      position: relative;
      background: linear-gradient(165deg, #131824 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-top: 3px solid rgba(255, 222, 36, 0.55);
      border-radius: 14px;
      padding: 1.35rem 1.45rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.85rem;
      overflow: hidden;
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.65);
      transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
    }}

    .season-pass-card:hover {{
      transform: translateY(-3px);
      border-color: var(--acos-yellow);
      box-shadow: 0 22px 48px rgba(0, 0, 0, 0.8), 0 0 22px rgba(255, 222, 36, 0.14);
    }}

    .season-pass-card.is-featured {{
      background:
        radial-gradient(circle at 90% 10%, rgba(255, 222, 36, 0.16) 0%, transparent 58%),
        linear-gradient(165deg, #1A1F2E 0%, #0A0D15 100%);
      border: 1.5px solid rgba(255, 222, 36, 0.68);
      border-top: 4px solid var(--acos-yellow);
      box-shadow: 0 22px 48px rgba(0, 0, 0, 0.78), 0 0 28px rgba(255, 222, 36, 0.12);
    }}

    .sp-top {{
      position: relative;
      z-index: 2;
      display: flex;
      flex-direction: column;
      gap: 0.38rem;
    }}

    .sp-badge-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.45rem;
      flex-wrap: wrap;
    }}

    .sp-tier-tag {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-silver);
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      padding: 0.22rem 0.56rem;
      border-radius: 5px;
    }}

    .season-pass-card.is-featured .sp-tier-tag {{
      background: rgba(255, 222, 36, 0.16);
      border-color: rgba(255, 222, 36, 0.45);
      color: var(--acos-yellow);
    }}

    .sp-type-lbl {{
      font-family: var(--font-mono);
      font-size: 0.6rem;
      color: var(--acos-yellow);
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}

    .sp-title {{
      font-family: var(--font-display);
      font-size: clamp(1.45rem, 2.2vw, 1.72rem);
      font-weight: 900;
      text-transform: uppercase;
      line-height: 1.04;
      color: var(--text-white);
      margin-top: 0.12rem;
    }}

    .sp-cats-grid {{
      position: relative;
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.42rem;
    }}

    .sp-cat-chip {{
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 7px;
      padding: 0.4rem 0.58rem;
      font-family: var(--font-sans);
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-white);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.35rem;
      white-space: nowrap;
    }}

    .sp-cat-chip em {{
      font-family: var(--font-mono);
      font-style: normal;
      font-size: 0.64rem;
      font-weight: 800;
      color: var(--acos-yellow);
    }}

    .sp-breakdown {{
      position: relative;
      z-index: 2;
      display: flex;
      flex-direction: column;
      gap: 0.38rem;
      background: rgba(5, 6, 9, 0.62);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 9px;
      padding: 0.62rem 0.78rem;
    }}

    .sp-bd-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      font-size: 0.78rem;
      padding-bottom: 0.32rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      white-space: nowrap;
    }}

    .sp-bd-row:last-child {{
      border-bottom: none;
      padding-bottom: 0;
    }}

    .sp-bd-lbl {{
      color: var(--text-muted);
      font-weight: 600;
    }}

    .sp-bd-val {{
      color: var(--text-white);
      font-weight: 800;
      text-align: right;
    }}

    .sp-bd-val.is-gold {{
      color: var(--acos-yellow);
    }}

    /* Fascia Istituzionale Unica Contatto Segreteria Tesseramenti */
    .sp-segreteria-strip {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      background: linear-gradient(145deg, rgba(18, 23, 35, 0.96) 0%, rgba(9, 12, 19, 0.98) 100%);
      border: 1px solid rgba(255, 222, 36, 0.28);
      border-radius: 12px;
      padding: 0.9rem 1.25rem;
      margin: 0 0 1.15rem;
      box-shadow: 0 14px 32px rgba(0, 0, 0, 0.55);
    }}

    .sps-info {{
      display: flex;
      flex-direction: column;
      gap: 0.18rem;
      min-width: 0;
    }}

    .sps-eyebrow {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--acos-yellow);
    }}

    .sps-hours {{
      font-size: 0.84rem;
      color: var(--text-silver);
      line-height: 1.35;
    }}

    .sps-hours strong {{
      color: var(--text-white);
      font-weight: 700;
    }}

    .sps-actions {{
      display: flex;
      align-items: center;
      gap: 0.65rem;
      flex-shrink: 0;
    }}

    .sps-btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.35rem;
      padding: 0.52rem 0.95rem;
      font-size: 0.78rem;
      border-radius: 8px;
      white-space: nowrap;
      text-decoration: none;
    }}

    /* Plancia Tesoreria Bancaria & IBAN */
    .treasury-iban-stage {{
      position: relative;
      background:
        radial-gradient(circle at 85% 20%, rgba(255, 222, 36, 0.14) 0%, transparent 60%),
        linear-gradient(155deg, #101521 0%, #06080D 100%);
      border: 1px solid rgba(255, 222, 36, 0.42);
      border-left: 5px solid var(--acos-yellow);
      border-radius: 16px;
      padding: 1.45rem 1.75rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.75);
      overflow: hidden;
    }}

    .treasury-top-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1rem;
      padding-bottom: 1.05rem;
      margin-bottom: 1.05rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }}

    .iban-code {{
      font-family: var(--font-mono);
      font-size: clamp(1rem, 2.1vw, 1.48rem);
      font-weight: 900;
      color: var(--acos-yellow);
      letter-spacing: 0.05em;
      word-break: break-all;
      margin-top: 0.2rem;
      text-shadow: 0 0 18px rgba(255, 222, 36, 0.22);
    }}

    .treasury-rules-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.85rem;
    }}

    .treasury-rule-box {{
      background: rgba(5, 6, 9, 0.68);
      border: 1px solid rgba(255, 255, 255, 0.09);
      border-radius: 10px;
      padding: 0.78rem 0.95rem;
      display: flex;
      flex-direction: column;
      gap: 0.22rem;
    }}

    .trb-tag {{
      font-family: var(--font-mono);
      font-size: 0.6rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .trb-val {{
      font-size: 0.84rem;
      color: var(--text-white);
      font-weight: 700;
      line-height: 1.35;
    }}

    /* Sportello Digitale a 3 Moduli Numerati */
    .portal-desk-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1.1rem;
      margin-bottom: 1.65rem;
    }}

    .portal-desk-card {{
      position: relative;
      background: linear-gradient(165deg, #131824 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.3rem 1.35rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.95rem;
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.6);
      overflow: hidden;
    }}

    .pdc-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 0.65rem;
    }}

    .pdc-num {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      display: block;
      margin-bottom: 0.2rem;
    }}

    .pdc-title {{
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 900;
      text-transform: uppercase;
      line-height: 1;
      color: var(--text-white);
    }}

    .pdc-icon {{
      width: 38px;
      height: 38px;
      border-radius: 9px;
      background: rgba(255, 222, 36, 0.12);
      border: 1px solid rgba(255, 222, 36, 0.38);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      flex-shrink: 0;
    }}

    .pdc-desc {{
      font-size: 0.84rem;
      color: var(--text-silver);
      line-height: 1.45;
      margin-top: 0.5rem;
    }}

    .pdc-actions {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.55rem;
    }}

    /* Safeguarding Command Stage */
    .safeguarding-command-stage {{
      position: relative;
      background:
        radial-gradient(circle at 12% 20%, rgba(255, 222, 36, 0.14) 0%, transparent 55%),
        linear-gradient(155deg, #16140B 0%, #090C12 65%, #06080D 100%);
      border: 1.5px solid rgba(255, 222, 36, 0.45);
      border-top: 4px solid var(--acos-yellow);
      border-radius: 16px;
      padding: 1.65rem 1.85rem;
      box-shadow: 0 26px 60px rgba(0, 0, 0, 0.8);
      overflow: hidden;
    }}

    .safeguarding-top-head {{
      display: flex;
      flex-direction: column;
      align-items: flex-start;
    }}

    .safeguarding-grid {{
      display: grid;
      grid-template-columns: 5fr 7fr;
      gap: 1.35rem;
      align-items: stretch;
      margin-top: 1.05rem;
    }}

    .safe-officer-card {{
      background: rgba(5, 6, 9, 0.72);
      border: 1px solid rgba(255, 222, 36, 0.36);
      border-left: 4px solid var(--acos-yellow);
      border-radius: 12px;
      padding: 1.2rem 1.3rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.8rem;
    }}

    .safe-officer-tag {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.07em;
      display: block;
      margin-bottom: 0.25rem;
    }}

    .safe-officer-name {{
      font-family: var(--font-display);
      font-size: 1.95rem;
      font-weight: 900;
      text-transform: uppercase;
      line-height: 0.96;
      color: var(--text-white);
    }}

    .safe-officer-desc {{
      font-size: 0.82rem;
      color: var(--text-silver);
      margin-top: 0.45rem;
      line-height: 1.45;
    }}

    .safe-officer-contact-pill {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.45rem;
      padding: 0.55rem 0.75rem;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      font-size: 0.78rem;
      color: var(--text-silver);
    }}

    .safe-docs-stack {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.75rem;
    }}

    .safe-doc-row {{
      background: rgba(16, 21, 32, 0.86);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 12px;
      padding: 0.9rem 1.15rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.85rem;
      flex-wrap: wrap;
      transition: border-color 0.2s ease, transform 0.2s ease;
    }}

    .safe-doc-row:hover {{
      border-color: var(--acos-yellow);
      transform: translateX(3px);
    }}

    .safe-doc-tag {{
      font-family: var(--font-mono);
      font-size: 0.6rem;
      color: var(--acos-yellow);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}

    .safe-doc-title {{
      font-family: var(--font-display);
      font-size: 1.28rem;
      font-weight: 900;
      text-transform: uppercase;
      color: var(--text-white);
      line-height: 1.05;
    }}

    /* ==========================================================================
       STADI, ARENE & CONTATTI MULTI-PROFILO (#PAGE-CONTATTI)
       ========================================================================== */
    .stadium-arenas-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1.35rem;
      margin-bottom: 2.15rem;
    }}

    .stadium-arena-card {{
      background: linear-gradient(165deg, #131824 0%, #090C12 100%);
      border: 1px solid rgba(255, 222, 36, 0.34);
      border-top: 4px solid var(--acos-yellow);
      border-radius: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.72);
    }}

    .sac-visual-header {{
      position: relative;
      min-height: 165px;
      background-size: cover;
      background-position: center 35%;
      padding: 1.1rem 1.35rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 222, 36, 0.24);
      overflow: hidden;
    }}

    .sac-visual-veil {{
      position: absolute;
      inset: 0;
      background:
        linear-gradient(180deg, rgba(5, 6, 9, 0.3) 0%, rgba(8, 10, 16, 0.95) 100%),
        linear-gradient(90deg, rgba(5, 6, 9, 0.65) 0%, transparent 100%);
    }}

    .sac-watermark {{
      position: absolute;
      right: 14px;
      bottom: -10px;
      font-family: var(--font-num);
      font-size: 4.8rem;
      line-height: 0.82;
      color: rgba(255, 222, 36, 0.14);
      pointer-events: none;
      z-index: 1;
    }}

    .sac-top-badges,
    .sac-bottom-headline {{
      position: relative;
      z-index: 2;
    }}

    .sac-top-badges {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}

    .sac-arena-tag {{
      background: var(--acos-yellow);
      color: #050609;
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 0.22rem 0.6rem;
      border-radius: 4px;
    }}

    .sac-dae-pill {{
      background: rgba(5, 6, 9, 0.85);
      border: 1px solid rgba(255, 222, 36, 0.45);
      color: var(--acos-yellow);
      font-family: var(--font-mono);
      font-size: 0.6rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 0.2rem 0.55rem;
      border-radius: 4px;
    }}

    .sac-title {{
      font-family: var(--font-display);
      font-size: clamp(1.55rem, 2.2vw, 1.98rem);
      font-weight: 900;
      text-transform: uppercase;
      line-height: 0.98;
      color: var(--text-white);
      margin-bottom: 0.2rem;
    }}

    .sac-address {{
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--acos-yellow);
      line-height: 1.32;
    }}

    .sac-body {{
      padding: 1.05rem 1.35rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      flex: 1;
    }}

    .arena-map-frame {{
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid rgba(255, 222, 36, 0.28);
      background: #050609;
      height: 190px;
    }}

    .venue-map-embed {{
      width: 100%;
      height: 100%;
      border: none;
      filter: contrast(1.04) saturate(0.92);
    }}

    .sac-actions-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.65rem;
      flex-wrap: wrap;
      margin-top: auto;
    }}

    /* Centralino Diretto & Concierge Form Multi-Profilo (Serie A Broadcast Precision) */
    .contact-command-stage {{
      display: grid;
      grid-template-columns: 6.5fr 5.5fr;
      gap: 1.35rem;
      align-items: stretch;
    }}

    .concierge-form-card {{
      background: linear-gradient(165deg, #131824 0%, #090C12 100%);
      border: 1px solid rgba(255, 222, 36, 0.36);
      border-top: 4px solid var(--acos-yellow);
      border-radius: 16px;
      padding: 1.45rem 1.65rem;
      box-shadow: 0 24px 56px rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.75rem;
    }}

    .concierge-form-title {{
      font-family: var(--font-display);
      font-size: clamp(1.65rem, 2.5vw, 2.15rem);
      font-weight: 900;
      text-transform: uppercase;
      line-height: 0.98;
      margin-bottom: 0.2rem;
    }}

    .cf-profile-tabs {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 0.45rem;
      margin: 0.65rem 0 0.4rem;
    }}

    .cf-profile-tab {{
      background: rgba(5, 6, 9, 0.78);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 8px;
      padding: 0.52rem 0.45rem;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.18s ease;
      text-align: center;
    }}

    .cf-profile-tab:hover {{
      border-color: rgba(255, 222, 36, 0.55);
      background: rgba(255, 222, 36, 0.06);
    }}

    .cf-profile-tab.active {{
      background: linear-gradient(135deg, #FFE135 0%, #F2BE00 100%);
      border-color: #FFF078;
      color: #050609;
      box-shadow: 0 6px 16px rgba(255, 222, 36, 0.22);
    }}

    .cfp-title {{
      font-family: var(--font-sans);
      font-size: 0.74rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.01em;
      line-height: 1.15;
      color: var(--text-white);
      white-space: nowrap;
    }}

    .cf-profile-tab.active .cfp-title {{
      color: #050609;
    }}

    .cf-cat-phone-grid {{
      display: grid;
      grid-template-columns: 1.35fr 0.85fr;
      gap: 0.65rem;
    }}

    .concierge-submit-row {{
      display: flex;
      gap: 0.65rem;
      flex-wrap: wrap;
      padding-top: 0.15rem;
    }}

    .switchboard-stack {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.68rem;
      height: 100%;
    }}

    .switchboard-card {{
      background: linear-gradient(165deg, #131824 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-left: 4px solid var(--acos-yellow);
      border-radius: 12px;
      padding: 0.9rem 1.15rem;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 0.85rem;
      box-shadow: 0 14px 32px rgba(0, 0, 0, 0.55);
      flex: 1;
    }}

    .swc-info {{
      display: flex;
      flex-direction: column;
      gap: 0.18rem;
      min-width: 0;
    }}

    .swc-tag {{
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }}

    .swc-main-val {{
      font-family: var(--font-sans);
      font-size: 1.22rem;
      font-weight: 800;
      letter-spacing: 0.01em;
      line-height: 1.15;
      color: var(--text-white);
    }}

    .swc-meta {{
      font-size: 0.78rem;
      color: var(--text-silver);
      line-height: 1.32;
    }}

    .swc-meta strong {{
      color: var(--text-white);
    }}

    .swc-cta-btn {{
      width: auto !important;
      padding: 0.48rem 0.9rem !important;
      font-size: 0.8rem !important;
      white-space: nowrap !important;
      flex-shrink: 0;
    }}

    .grid-2-responsive {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }}

    .form-input, .form-select, .form-textarea {{
      width: 100%;
      background: #06080E;
      border: 1px solid rgba(255, 255, 255, 0.18);
      color: var(--text-white);
      padding: 0.78rem 0.95rem;
      border-radius: 8px;
      font-family: var(--font-sans);
      font-size: 0.88rem;
      font-weight: 600;
      transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }}

    .form-input:focus, .form-select:focus, .form-textarea:focus {{
      outline: none;
      border-color: var(--acos-yellow);
      box-shadow: 0 0 0 3px rgba(255, 222, 36, 0.15);
    }}

    /* ==========================================================================
       PAGE 3: SCUOLA CALCIO RICONOSCIUTA FIGC, ATALANTA B.C. & TORNEO VIGANÒ
       ========================================================================== */
    .academy-manifesto-stage {{
      position: relative;
      background:
        radial-gradient(circle at 86% 18%, rgba(255, 222, 36, 0.14) 0%, transparent 48%),
        linear-gradient(155deg, #121724 0%, #070A10 100%);
      border: 1px solid rgba(255, 222, 36, 0.34);
      border-top: 4px solid var(--acos-yellow);
      border-radius: 18px;
      padding: 2.3rem 2.4rem;
      margin-bottom: 2.4rem;
      box-shadow: 0 28px 64px rgba(0, 0, 0, 0.72);
      overflow: hidden;
    }}

    .academy-manifesto-watermark {{
      position: absolute;
      right: 1.5rem;
      bottom: -1.4rem;
      font-family: var(--font-display);
      font-size: clamp(4.8rem, 9vw, 8.2rem);
      font-weight: 900;
      text-transform: uppercase;
      color: rgba(255, 222, 36, 0.04);
      line-height: 0.85;
      pointer-events: none;
      user-select: none;
    }}

    .academy-manifesto-grid {{
      display: grid;
      grid-template-columns: 7fr 5fr;
      gap: 2rem;
      align-items: stretch;
      position: relative;
      z-index: 2;
    }}

    .academy-badge-cluster {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.55rem;
      margin-bottom: 0.9rem;
    }}

    .academy-official-pill {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.34rem 0.75rem;
      border-radius: 6px;
      background: rgba(255, 222, 36, 0.11);
      border: 1px solid rgba(255, 222, 36, 0.38);
      font-family: var(--font-mono);
      font-size: 0.66rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--acos-yellow);
    }}

    .academy-official-pill.atalanta-pill {{
      background: rgba(30, 110, 220, 0.16);
      border-color: rgba(88, 166, 255, 0.45);
      color: #8CC4FF;
    }}

    .academy-kpi-strip {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 0.75rem;
      margin: 1.35rem 0;
    }}

    .academy-kpi-box {{
      background: rgba(5, 7, 12, 0.78);
      border: 1px solid rgba(255, 255, 255, 0.11);
      border-left: 3px solid var(--acos-yellow);
      border-radius: 10px;
      padding: 0.72rem 0.75rem;
      min-width: 0;
    }}

    .academy-kpi-num {{
      font-family: var(--font-sans);
      font-size: clamp(1.04rem, 1.25vw, 1.18rem);
      font-weight: 800;
      color: var(--acos-yellow);
      line-height: 1.1;
      letter-spacing: -0.02em;
      white-space: nowrap;
    }}

    .academy-kpi-lbl {{
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-silver);
      margin-top: 0.2rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .academy-visual-card {{
      position: relative;
      border-radius: 14px;
      overflow: hidden;
      border: 1px solid rgba(255, 222, 36, 0.34);
      background: #06080E;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 360px;
    }}

    .academy-visual-card > img {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      filter: brightness(0.84) contrast(1.12) saturate(1.12);
      transition: transform 0.45s ease;
    }}

    .academy-visual-card:hover > img {{
      transform: scale(1.04);
    }}

    .academy-visual-overlay {{
      position: relative;
      z-index: 2;
      margin-top: auto;
      background: linear-gradient(180deg, rgba(5, 6, 10, 0) 0%, rgba(5, 6, 10, 0.92) 48%, rgba(5, 6, 10, 0.98) 100%);
      padding: 2.4rem 1.35rem 1.25rem;
    }}

    .academy-seal-bar {{
      position: relative;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      margin: 0.95rem 0.95rem 0;
      padding: 0.6rem 0.85rem;
      background: rgba(7, 9, 15, 0.88);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 222, 36, 0.38);
      border-radius: 10px;
    }}

    .academy-pillars-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1.15rem;
      margin-bottom: 2.5rem;
    }}

    .academy-pillar-card {{
      position: relative;
      background: linear-gradient(165deg, #131824 0%, #090C12 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-top: 3px solid var(--acos-yellow);
      border-radius: 14px;
      padding: 1.45rem 1.35rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.85rem;
      overflow: hidden;
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.55);
    }}

    .academy-pillar-num {{
      position: absolute;
      top: 0.55rem;
      right: 0.85rem;
      font-family: var(--font-display);
      font-size: 3.1rem;
      font-weight: 900;
      line-height: 1;
      color: rgba(255, 222, 36, 0.08);
      pointer-events: none;
    }}

    .academy-pillar-icon {{
      width: 42px;
      height: 42px;
      border-radius: 10px;
      background: rgba(255, 222, 36, 0.12);
      border: 1px solid rgba(255, 222, 36, 0.36);
      color: var(--acos-yellow);
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }}

    .academy-pillar-title {{
      font-family: var(--font-sans);
      font-size: 1.03rem;
      font-weight: 800;
      color: var(--text-white);
      line-height: 1.25;
      margin-top: 0.25rem;
      letter-spacing: -0.01em;
    }}

    .academy-pillar-desc {{
      font-size: 0.84rem;
      color: var(--text-silver);
      line-height: 1.5;
    }}

    .academy-pillar-meta {{
      font-family: var(--font-mono);
      font-size: 0.6rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--acos-yellow);
      padding-top: 0.65rem;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    @media (min-width: 1121px) {{
      .academy-pillar-title,
      .uefa-right-title,
      .sp-title,
      .sac-title,
      .hmc-title,
      .age-pill-cat,
      .atc-val,
      .asc-tel-val,
      .pathway-spec-val,
      .safe-doc-row h5,
      .str-year-val,
      .bmc-team-name,
      .gothia-monument-title {{
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
    }}

    /* Percorso Evolutivo 5-12 Anni */
    .academy-pathway-stage {{
      background: linear-gradient(165deg, #111622 0%, #080A10 100%);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 16px;
      padding: 2rem 2.1rem;
      margin-bottom: 2.5rem;
    }}

    .academy-pathway-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1.1rem;
      margin-top: 1.25rem;
    }}

    .pathway-step-card {{
      background: rgba(5, 7, 12, 0.82);
      border: 1px solid rgba(255, 255, 255, 0.13);
      border-radius: 12px;
      padding: 1.25rem 1.2rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 0.75rem;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}

    .pathway-step-card:hover {{
      transform: translateY(-3px);
      border-color: rgba(255, 222, 36, 0.55);
    }}

    .pathway-age-pill {{
      display: inline-flex;
      align-items: center;
      justify-content: space-between;
      font-family: var(--font-mono);
      font-size: 0.64rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #050609;
      background: var(--acos-yellow);
      padding: 0.24rem 0.6rem;
      border-radius: 5px;
      width: fit-content;
    }}

    .pathway-cat-name {{
      font-family: var(--font-sans);
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--text-white);
      line-height: 1.2;
      margin-top: 0.25rem;
    }}

    .pathway-Births {{
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--acos-yellow);
      text-transform: uppercase;
    }}

    .pathway-specs {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.38rem;
      font-size: 0.8rem;
      color: var(--text-silver);
      padding: 0.65rem 0;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .pathway-specs li {{
      display: flex;
      justify-content: space-between;
      gap: 0.4rem;
    }}

    .pathway-specs strong {{
      color: var(--text-white);
      font-weight: 700;
    }}

    /* Carta dei Diritti dei Bambini & Decalogo UEFA */
    .uefa-charter-stage {{
      background: linear-gradient(160deg, #131824 0%, #080B11 100%);
      border: 1px solid rgba(255, 222, 36, 0.28);
      border-radius: 16px;
      padding: 2rem 2.1rem;
      margin-bottom: 2.5rem;
    }}

    .uefa-charter-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1rem;
      margin-top: 1.25rem;
    }}

    .uefa-right-card {{
      background: rgba(5, 7, 12, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.11);
      border-left: 3px solid var(--acos-yellow);
      border-radius: 10px;
      padding: 1.05rem 1.15rem;
      display: flex;
      flex-direction: column;
      gap: 0.38rem;
    }}

    .uefa-right-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      color: var(--acos-yellow);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .uefa-right-title {{
      font-family: var(--font-sans);
      font-size: 0.96rem;
      font-weight: 800;
      color: var(--text-white);
    }}

    .uefa-right-desc {{
      font-size: 0.81rem;
      color: var(--text-silver);
      line-height: 1.45;
    }}

    /* Monument Stage Torneo Stefano Viganò – Memorial Enzo Riganti */
    .vigano-monument-stage {{
      background:
        radial-gradient(circle at 12% 20%, rgba(255, 222, 36, 0.12) 0%, transparent 45%),
        linear-gradient(165deg, #141926 0%, #070A10 100%);
      border: 1px solid rgba(255, 222, 36, 0.38);
      border-top: 4px solid var(--acos-yellow);
      border-radius: 18px;
      padding: 2.2rem 2.3rem;
      box-shadow: 0 26px 60px rgba(0, 0, 0, 0.72);
    }}

    .vigano-patronage-bar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 0.9rem 1.15rem;
      background: rgba(5, 7, 12, 0.85);
      border: 1px solid rgba(255, 222, 36, 0.28);
      border-radius: 12px;
      margin: 1.25rem 0 1.5rem;
    }}

    .vigano-patron-Main {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }}

    .vigano-patron-crest {{
      height: 44px;
      width: auto;
      border-radius: 6px;
      border: 1px solid rgba(255, 222, 36, 0.4);
      background: #fff;
      padding: 3px 8px;
      object-fit: contain;
    }}

    .vigano-patron-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
    }}

    .vigano-patron-pill {{
      font-family: var(--font-mono);
      font-size: 0.62rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 0.32rem 0.65rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.14);
      color: var(--text-white);
    }}

    @media (max-width: 1120px) {{
      .season-pass-grid,
      .academy-pillars-grid,
      .academy-pathway-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .uefa-charter-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .treasury-rules-grid,
      .portal-desk-grid,
      .academy-manifesto-grid {{
        grid-template-columns: 1fr;
      }}
      .safeguarding-grid,
      .stadium-arenas-grid,
      .contact-command-stage {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 720px) {{
      .cf-profile-tabs,
      .academy-kpi-strip {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .season-pass-grid,
      .arena-telemetry-grid,
      .cf-cat-phone-grid,
      .grid-2-responsive,
      .academy-pillars-grid,
      .academy-pathway-grid,
      .uefa-charter-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    /* Serie A Top-Level Architectural Footer (Griglia Asimmetrica a 4 Colonne + Link Tipografici Puri) */
    .site-footer {{
      background: radial-gradient(circle at 18% 0%, rgba(255, 222, 36, 0.06) 0%, #07090F 52%, #030406 100%);
      border-top: 2px solid var(--acos-yellow);
      padding: 0;
      color: var(--text-silver);
      font-size: 0.9rem;
      box-shadow: 0 -14px 36px rgba(0, 0, 0, 0.88);
    }}

    .footer-main-wrap {{
      max-width: var(--max-w);
      width: 100%;
      margin: 0 auto;
      padding: 3.25rem 1.5rem 2.6rem;
    }}

    .footer-grid {{
      display: grid;
      grid-template-columns: 1.45fr 1fr 1.05fr 1.15fr;
      gap: 2.75rem;
      align-items: start;
    }}

    .footer-col-brand {{
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 1.05rem;
      padding-right: 1rem;
    }}

    .footer-brand-desc {{
      font-family: var(--font-body);
      font-size: 0.86rem;
      line-height: 1.62;
      color: var(--text-silver);
      margin: 0;
      max-width: 340px;
    }}

    .footer-social-row {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-top: 0.15rem;
    }}

    .footer-social-icon {{
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text-silver);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }}

    .footer-social-icon svg {{
      width: 16px;
      height: 16px;
    }}

    .footer-social-icon:hover {{
      color: #050608;
      background: var(--acos-yellow);
      border-color: var(--acos-yellow);
      transform: translateY(-2px);
    }}

    .footer-col h4 {{
      font-family: var(--font-body);
      font-size: 0.74rem;
      font-weight: 800;
      color: var(--acos-yellow);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      line-height: 1.2;
      margin: 0 0 1.15rem 0;
    }}

    .footer-links {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.68rem;
    }}

    .footer-links a,
    .footer-links button.footer-text-link,
    .footer-links span.footer-meta-item {{
      background: none;
      border: none;
      color: var(--text-silver);
      text-align: left;
      font-family: var(--font-body);
      font-size: 0.9rem;
      font-weight: 500;
      line-height: 1.4;
      padding: 0;
      display: inline-block;
      width: fit-content;
      position: relative;
      cursor: pointer;
      transition: color 0.18s ease;
    }}

    .footer-links span.footer-meta-item {{
      color: var(--text-muted);
      font-size: 0.84rem;
      cursor: default;
    }}

    .footer-links a::after,
    .footer-links button.footer-text-link::after {{
      content: '';
      position: absolute;
      left: 0;
      right: 0;
      bottom: -2px;
      height: 1px;
      background: var(--acos-yellow);
      transform: scaleX(0);
      transform-origin: left center;
      transition: transform 0.22s ease;
    }}

    .footer-links a:hover,
    .footer-links button.footer-text-link:hover {{
      color: var(--text-white);
    }}

    .footer-links a:hover::after,
    .footer-links button.footer-text-link:hover::after {{
      transform: scaleX(1);
    }}

    /* Band 3: Micro-barra inferiore strutturata su righe gerarchiche */
    .footer-bottom-ribbon {{
      background: #020305;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding: 0.9rem 0;
      display: flex;
      align-items: center;
      font-size: 0.74rem;
      color: var(--text-silver);
      font-weight: 600;
    }}

    .footer-bottom-inner {{
      max-width: var(--max-w);
      width: 100%;
      margin: 0 auto;
      padding: 0 1.5rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      gap: 0.28rem;
    }}

    .footer-legal-line-1 {{
      color: var(--acos-yellow);
      font-family: var(--font-display);
      font-size: 0.92rem;
      font-weight: 900;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      line-height: 1.2;
    }}

    .footer-legal-line-2 {{
      color: var(--text-white);
      font-family: var(--font-mono);
      font-size: 0.74rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
      gap: 0.45rem;
      line-height: 1.35;
    }}

    .footer-legal-line-3 {{
      color: var(--text-muted);
      font-size: 0.68rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
      gap: 0.4rem;
      line-height: 1.3;
    }}

    /* ==========================================================================
       10. FLOATING STUDIO DEVICE SWITCHER (NON INVASIVO IN BASSO A SINISTRA)
       ========================================================================== */
    .floating-studio-switcher {{
      position: fixed;
      bottom: 16px;
      left: 16px;
      z-index: 4000;
      background: rgba(5, 6, 9, 0.94);
      border: 1px solid var(--acos-border-gold);
      border-radius: 999px;
      padding: 0.3rem 0.55rem;
      display: flex;
      align-items: center;
      gap: 0.3rem;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.85);
      backdrop-filter: blur(12px);
    }}

    .vp-btn {{
      background: transparent;
      border: none;
      color: var(--text-silver);
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.28rem 0.55rem;
      border-radius: 999px;
      transition: all 0.15s ease;
    }}

    .vp-btn.active, .vp-btn:hover {{
      background: var(--acos-yellow);
      color: #050609;
      font-weight: 800;
    }}

    #viewport-stage {{
      width: 100%;
      margin: 0 auto;
      transition: max-width 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      background: var(--bg-obsidian);
    }}

    #viewport-stage.framed-device {{
      margin: 1.5rem auto 4rem;
      border: 2px solid var(--acos-border-gold);
      border-radius: 22px;
      box-shadow: 0 28px 90px rgba(0, 0, 0, 0.9), 0 0 0 8px #10131C;
      overflow-x: hidden;
      container-type: inline-size;
    }}

    /* MOBILE BOTTOM DOCK (4 VOCI PRIMARIE — APPLE HIG / MATERIAL 3) & SEGMENTED SUB-TABS */
    .mobile-bottom-dock {{
      display: none;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 3500;
      background: linear-gradient(180deg, rgba(8, 10, 16, 0.96) 0%, rgba(4, 5, 8, 0.99) 100%);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border-top: 1px solid rgba(255, 222, 36, 0.38);
      box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.85);
      grid-template-columns: repeat(4, 1fr);
      padding: 0 0.25rem env(safe-area-inset-bottom);
    }}

    .dock-btn {{
      position: relative;
      background: none;
      border: none;
      color: var(--text-silver);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.2rem;
      font-family: var(--font-display);
      font-size: 0.74rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      min-height: 56px;
      padding: 0.36rem 0.15rem 0.3rem;
      transition: all 0.18s ease;
    }}

    .dock-btn svg {{
      width: 18px;
      height: 18px;
      stroke-width: 2.15;
      opacity: 0.8;
      transition: transform 0.18s ease, opacity 0.18s ease, color 0.18s ease;
    }}

    /* UNIFIED 3-COLUMN SEGMENTED SUB-NAVIGATION BAR (IDENTICAL ACROSS SQUADRE, IL CLUB, INFO & SEDE) */
    .acos-subnav-wrap {{
      position: sticky;
      top: 98px;
      z-index: 1200;
      margin: 0;
      padding: 0.55rem 0;
      background: linear-gradient(180deg, rgba(7, 9, 14, 0.98) 0%, rgba(7, 9, 14, 0.93) 100%);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid rgba(255, 222, 36, 0.24);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    }}

    .acos-subnav-bar {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      align-items: stretch;
      gap: 0.38rem;
      width: 100%;
      background: #0C0F16;
      border: 1.5px solid rgba(255, 222, 36, 0.34);
      border-radius: 12px;
      padding: 0.28rem;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }}

    .acos-subnav-pill {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.14rem;
      min-height: 48px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      color: var(--text-silver);
      padding: 0.4rem 0.45rem;
      border-radius: 9px;
      cursor: pointer;
      transition: all 0.18s ease;
      text-align: center;
      min-width: 0;
    }}

    .subnav-idx {{
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      color: var(--acos-yellow);
      line-height: 1;
      text-transform: uppercase;
    }}

    .subnav-lbl {{
      font-family: var(--font-display);
      font-size: 0.96rem;
      font-weight: 900;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      line-height: 1.05;
      color: var(--text-white);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 100%;
    }}

    .acos-subnav-pill:hover {{
      color: var(--text-white);
      background: rgba(255, 222, 36, 0.08);
      border-color: rgba(255, 222, 36, 0.32);
    }}

    .acos-subnav-pill.active {{
      background: var(--acos-yellow);
      color: #050608;
      border-color: var(--acos-yellow);
      box-shadow: 0 4px 14px rgba(255, 222, 36, 0.35);
    }}

    .acos-subnav-pill.active .subnav-idx {{
      color: #050608;
      opacity: 0.78;
    }}

    .acos-subnav-pill.active .subnav-lbl {{
      color: #050608;
    }}

    /* Nascondiamo la seconda barra filtri ridondante su Desktop per mantenere un'unica barra top identica */
    .filter-chips-row {{
      display: none !important;
    }}
    .fc-mobile {{
      display: none;
    }}
    .vigano-mobile-cta-row,
    .vigano-mobile-only {{
      display: none;
    }}

    .subpane-view {{
      display: none;
    }}

    .subpane-view.active {{
      display: block;
      animation: pageFadeIn 0.22s ease-out;
    }}

    .dock-btn.active {{
      color: var(--acos-yellow);
      background: radial-gradient(circle at 50% 0%, rgba(255, 222, 36, 0.16) 0%, transparent 75%);
    }}

    .dock-btn.active::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 18%;
      right: 18%;
      height: 2.5px;
      background: var(--acos-yellow);
      border-radius: 0 0 3px 3px;
      box-shadow: 0 2px 8px rgba(255, 222, 36, 0.65);
    }}

    .dock-btn.active svg {{
      opacity: 1;
      color: var(--acos-yellow);
      transform: translateY(-1px);
    }}

    .drawer-nav-btn {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      background: rgba(255, 255, 255, 0.035);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-white);
      font-family: var(--font-display);
      font-size: 1.02rem;
      font-weight: 800;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      padding: 0.72rem 0.9rem;
      border-radius: 8px;
      text-align: left;
      transition: all 0.16s ease;
    }}

    .drawer-nav-btn.active,
    .drawer-nav-btn:hover {{
      background: rgba(255, 222, 36, 0.12);
      border-color: var(--acos-yellow);
      color: var(--acos-yellow);
    }}

    .drawer-nav-idx {{
      font-family: var(--font-mono);
      font-size: 0.66rem;
      color: var(--acos-yellow);
      margin-right: 0.55rem;
      font-weight: 800;
    }}

    .modal-backdrop {{
      display: none;
      position: fixed;
      inset: 0;
      z-index: 5000;
      background: rgba(3, 4, 6, 0.88);
      backdrop-filter: blur(10px);
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }}

    .modal-backdrop.open {{ display: flex; }}

    .modal-dialog {{
      background: var(--bg-card);
      border: 2px solid var(--acos-border-gold);
      border-radius: 14px;
      max-width: 680px;
      width: 100%;
      max-height: 88vh;
      overflow-y: auto;
      padding: 1.65rem;
    }}

    .modal-close {{
      float: right;
      background: var(--bg-card-elevated);
      border: 1px solid var(--border-strong);
      color: var(--text-white);
      width: 36px;
      height: 36px;
      border-radius: 50%;
      font-weight: 900;
    }}

    /* ==========================================================================
       11. RESPONSIVE BREAKPOINTS & CONTAINER QUERIES (320px -> 1440px)
       ========================================================================== */
    html, body {{
      overflow-x: hidden;
      max-width: 100%;
    }}

    @media (max-width: 1150px) {{
      .main-nav, .footer-mirror-nav {{ display: none; }}
      .mobile-burger {{ display: inline-flex; }}
      .ribbon-right {{ display: none; }}
    }}

    @media (max-width: 1024px) {{
      .hero-stage-grid, .venues-grid, .storyboard-duo-grid, .evergreen-flagship-banner, .pyramid-3-grid, .ilc-stage, .ux-sim-tabs, .home-sectors-grid, .home-heritage-showcase, .treasury-rules-grid, .portal-desk-grid, .safeguarding-grid, .stadium-arenas-grid, .contact-command-stage {{ grid-template-columns: 1fr; }}
      .season-pass-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .efb-right {{ align-items: flex-start; }}
      .efb-pills {{ justify-content: flex-start; }}
      .matches-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .hero-telemetry-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .footer-grid {{ grid-template-columns: 1fr 1fr; }}
      .footer-bottom-ribbon {{ padding-bottom: 5.25rem; }}
      .mobile-bottom-dock {{ display: grid; }}
      .floating-studio-switcher {{ bottom: 70px; }}
    }}

    /* ==========================================================================
       12. SERIE A NATIVE MOBILE APP ARCHITECTURE (<= 768px & <= 640px)
       ========================================================================== */
    @media (max-width: 768px) {{
      /* 1. HEADER MONUMENTALE MOBILE SERIE A (118PX + CROWN BAR 30PX, STEMMA GIGANTE 74x90PX, ZERO BOTTONI DUPLICATI) */
      .top-Broadcast-ribbon {{
        display: flex !important;
        height: 28px !important;
        min-height: 28px !important;
        padding: 0 0.35rem !important;
        justify-content: center !important;
        align-items: center !important;
        background: linear-gradient(90deg, #040507 0%, #0D111A 50%, #040507 100%) !important;
        border-bottom: 1px solid rgba(255, 222, 36, 0.32) !important;
      }}
      .top-ribbon-inner {{
        padding: 0 0.25rem !important;
        justify-content: center !important;
      }}
      .ribbon-left {{
        width: 100% !important;
        justify-content: center !important;
        gap: 0.35rem !important;
        font-size: 0.6rem !important;
        letter-spacing: 0.025em !important;
        white-space: nowrap !important;
      }}
      .ribbon-only-desktop {{
        display: none !important;
      }}
      .ribbon-right {{
        display: none !important;
      }}
      .site-header {{
        height: 118px !important;
        min-height: 118px !important;
        background: radial-gradient(circle at 50% 50%, rgba(255, 222, 36, 0.22) 0%, rgba(9, 11, 16, 0.98) 64%, #050609 100%) !important;
        border-bottom: 2px solid var(--acos-yellow) !important;
      }}
      .header-inner {{
        height: 118px !important;
        min-height: 118px !important;
        padding: 0.75rem 1.15rem !important;
        gap: 0.85rem !important;
        justify-content: center !important;
      }}
      .club-brand {{
        gap: 1.05rem !important;
        min-width: 0 !important;
      }}
      .crest-header {{
        width: 74px !important;
        height: 90px !important;
        flex-shrink: 0 !important;
        filter: drop-shadow(0 10px 22px rgba(0, 0, 0, 0.96)) drop-shadow(0 0 24px rgba(255, 222, 36, 0.52)) !important;
      }}
      .club-brand-title {{
        font-size: 2.06rem !important;
        letter-spacing: 0.035em !important;
        line-height: 0.95 !important;
        white-space: nowrap !important;
      }}
      .club-brand-sub {{
        font-size: 0.78rem !important;
        letter-spacing: 0.08em !important;
        margin-top: 0.34rem !important;
        white-space: nowrap !important;
      }}
      .header-actions,
      .header-actions .btn-gold-broadcast,
      .mobile-burger {{
        display: none !important;
      }}
      .acos-subnav-wrap {{
        top: 118px !important;
        margin: 0 !important;
        padding: 0.55rem 0 !important;
      }}
      .acos-subnav-bar {{
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        width: 100% !important;
        padding: 0.24rem !important;
        gap: 0.28rem !important;
      }}
      .acos-subnav-pill {{
        min-height: 46px !important;
        padding: 0.35rem 0.25rem !important;
        gap: 0.1rem !important;
      }}
      .subnav-idx {{
        font-size: 0.52rem !important;
      }}
      .subnav-lbl {{
        font-size: 0.82rem !important;
        letter-spacing: 0.02em !important;
      }}
      /* In Home su mobile eliminiamo il blocco Storyboard che duplicava Gothia/Scuola/Cuore già presenti nei sotto-tab */
      #home-storyboard-section {{
        display: none !important;
      }}

      /* =====================================================================
         2. UX MOBILE DEDICATA (SERIE A / APPLE SPORTS NATIVE APP PATTERN)
         - Canone 1: Progressive Disclosure (Taglio del 70% del rumore visivo,
           niente watermark giganti, niente doppi titoli, testi max 2-3 righe)
         - Canone 2: Leggibilità Tipografica Reale (Font >= 14.5px / 0.9rem,
           ZERO doppie colonne testuali strette da 160px)
         - Canone 3: Caroselli Orizzontali Touch a Scatto (Swipe X Mandatory)
           per pilastri, storia, quote e card informative (-65% scroll verticale)
         - Canone 4: Liste "1 Riga = 1 Tap" per le 15 Squadre Giallonere
         ===================================================================== */
      .container {{
        padding: 0 1rem !important;
      }}
      .section-block {{
        padding: 1.5rem 0 !important;
      }}
      .section-header {{
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.35rem !important;
        margin-bottom: 1rem !important;
      }}
      /* Nascondi eyebrow chilometrici e bottoni secondari ridondanti nell'header sezione */
      .section-eyebrow,
      .section-header > .btn-gold-broadcast,
      .section-header > .btn-ghost-broadcast {{
        display: none !important;
      }}
      .section-title {{
        font-size: clamp(1.68rem, 7.2vw, 2.05rem) !important;
        line-height: 0.96 !important;
        white-space: normal !important;
      }}

      /* RIMOZIONE TOTALE DEL RUMORE DECORATIVO SU MOBILE (Progressive Disclosure) */
      .hero-kinetic-watermark,
      .asc-watermark,
      .storyboard-lead-watermark,
      .ssb-watermark,
      .sp-watermark,
      .telemetry-chevron,
      .telemetry-idx,
      .asc-header-title,
      .ssb-desc,
      .str-meta-pills,
      .btn-str-outline,
      .academy-pillar-meta,
      .sp-sub,
      .trb-sub,
      .swc-desc,
      .org-exec-desc,
      .cuore-strada-quote,
      .cmb-archive-zoom {{
        display: none !important;
      }}

      /* 3. ZERO HORIZONTAL OVERFLOW RULES */
      .hero-monumental-h1 .hollow-line,
      .hero-monumental-h1 .stroke-line,
      .hero-monumental-h1 .gold-line,
      .storyboard-card-title,
      .ssb-title,
      .ssb-eyebrow,
      .ssb-highlight-pill,
      .gothia-world-pill,
      .gothia-kpi-val,
      .gothia-kpi-lbl,
      .gothia-country-tag,
      .gothia-edition-tag,
      .org-tier-tag,
      .org-fed-seal,
      .cfp-title,
      .cfp-sub,
      .academy-kpi-num,
      .academy-kpi-lbl,
      .academy-official-pill,
      .vigano-patron-pill,
      .telemetry-val,
      .telemetry-lbl,
      .fiscal-row,
      .fed-tag,
      .sac-arena-tag,
      .sac-dae-pill,
      .cmb-kpi-num,
      .cmb-kpi-lbl,
      .btn-gold-broadcast,
      .btn-ghost-broadcast {{
        white-space: normal !important;
      }}

      /* 4. PAGE 1 (HOME): HERO ESSENZIALE, SWIPE AGE FINDER & STORYBOARD CAROUSEL */
      .stadium-hero {{
        padding: 1.45rem 0 0 !important;
        min-height: auto !important;
      }}
      .hero-stage-grid {{
        min-height: auto !important;
        padding: 0.1rem 0 1.15rem !important;
      }}
      .hero-identity-row {{
        gap: 0.4rem !important;
        margin-bottom: 0.65rem !important;
      }}
      .hero-season-pill {{
        font-size: 0.72rem !important;
        padding: 0.24rem 0.65rem !important;
      }}
      /* Su mobile mostriamo solo il badge principale nella barra identità Hero */
      .hero-location-tag {{
        display: none !important;
      }}
      .hero-monumental-h1 {{
        transform: none !important;
        margin-bottom: 0.65rem !important;
      }}
      .hero-monumental-h1 .hollow-line,
      .hero-monumental-h1 .stroke-line,
      .hero-monumental-h1 .gold-line {{
        font-size: clamp(1.92rem, 8.4vw, 2.4rem) !important;
        line-height: 0.94 !important;
      }}
      .hero-lead-copy {{
        font-size: 0.92rem !important;
        line-height: 1.48 !important;
        margin-bottom: 1rem !important;
        padding-left: 0.75rem !important;
        border-left-width: 3px !important;
        display: -webkit-box !important;
        -webkit-line-clamp: 3 !important;
        -webkit-box-orient: vertical !important;
        overflow: hidden !important;
      }}
      .hero-cta-row {{
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.48rem !important;
        width: 100% !important;
        max-width: 100% !important;
      }}
      .hero-deck-btn {{
        width: 100% !important;
        min-width: 0 !important;
        justify-content: space-between !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.025em !important;
        padding: 0.66rem 0.55rem !important;
        gap: 0.3rem !important;
        border-radius: 8px !important;
      }}
      .hero-deck-arrow {{
        width: 18px !important;
        height: 18px !important;
        font-size: 0.7rem !important;
      }}
      .hero-lower-inner {{
        padding: 0 !important;
      }}
      .hero-telemetry-strip {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
      }}
      .hero-telemetry-item {{
        padding: 0.72rem 0.85rem !important;
        gap: 0.35rem !important;
      }}
      .hero-telemetry-item:nth-child(1),
      .hero-telemetry-item:nth-child(2) {{
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
      }}
      .hero-telemetry-item:nth-child(2n) {{
        border-right: none !important;
      }}
      .telemetry-val {{
        font-size: 1.12rem !important;
        line-height: 1.05 !important;
      }}
      .telemetry-lbl {{
        font-size: 0.68rem !important;
      }}
      .home-sectors-grid {{
        grid-template-columns: 1fr !important;
        gap: 0.9rem !important;
      }}
      .home-sector-poster {{
        min-height: 210px !important;
        padding: 1.25rem 1.2rem !important;
        border-radius: 14px !important;
      }}
      .hsp-title {{
        font-size: 1.62rem !important;
      }}
      .hsp-desc {{
        font-size: 0.84rem !important;
        line-height: 1.42 !important;
        margin-bottom: 0.25rem !important;
      }}
      .home-heritage-showcase {{
        grid-template-columns: 1fr !important;
        border-radius: 14px !important;
      }}
      .hhs-visual {{
        min-height: 195px !important;
      }}
      .hhs-visual::after {{
        background: linear-gradient(180deg, rgba(7, 9, 15, 0.05) 40%, rgba(7, 9, 15, 0.95) 100%) !important;
      }}
      .hhs-body {{
        padding: 1.35rem 1.2rem 1.5rem !important;
        gap: 0.7rem !important;
      }}
      .hhs-copy {{
        font-size: 0.86rem !important;
        line-height: 1.5 !important;
      }}

      /* Home Atto II: Age Finder con Selettore Orizzontale Touch (App Style) */
      .age-finder-stage {{
        padding: 1rem !important;
        border-radius: 14px !important;
      }}
      .age-finder-pills {{
        display: flex !important;
        overflow-x: auto !important;
        scroll-snap-type: x mandatory !important;
        -webkit-overflow-scrolling: touch !important;
        scrollbar-width: none !important;
        gap: 0.5rem !important;
        margin-bottom: 0.9rem !important;
        padding-bottom: 0.25rem !important;
      }}
      .age-finder-pills::-webkit-scrollbar {{
        display: none !important;
      }}
      .age-pill-btn {{
        flex: 0 0 auto !important;
        min-width: 126px !important;
        scroll-snap-align: start !important;
        padding: 0.58rem 0.75rem !important;
        border-radius: 10px !important;
      }}
      .age-pill-years {{
        font-size: 1.15rem !important;
      }}
      .age-pill-cat {{
        font-size: 0.64rem !important;
      }}
      .asc-visual {{
        min-height: 155px !important;
        padding: 0.9rem !important;
      }}
      .asc-crest {{
        width: 42px !important;
        height: 54px !important;
      }}
      #asc-visual-title {{
        font-size: 1.55rem !important;
        line-height: 1.02 !important;
      }}
      .asc-body {{
        padding: 1rem !important;
        gap: 0.75rem !important;
      }}
      .asc-pitch-copy {{
        font-size: 0.9rem !important;
        line-height: 1.46 !important;
        padding-left: 0.65rem !important;
        display: -webkit-box !important;
        -webkit-line-clamp: 2 !important;
        -webkit-box-orient: vertical !important;
        overflow: hidden !important;
      }}
      .asc-telemetry-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.48rem !important;
      }}
      .asc-telemetry-box {{
        padding: 0.6rem 0.68rem !important;
      }}
      .asc-tel-lbl {{
        font-size: 0.6rem !important;
      }}
      .asc-tel-val {{
        font-size: 0.88rem !important;
        line-height: 1.2 !important;
      }}
      .asc-actions-row {{
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 0.5rem !important;
      }}
      .asc-actions-row .btn-gold-broadcast,
      .asc-actions-row .btn-ghost-broadcast {{
        width: 100% !important;
        justify-content: center !important;
        font-size: 0.86rem !important;
        padding: 0.64rem 0.5rem !important;
      }}

      /* Home Atto III: Storyboard Snello + Carosello Orizzontale */
      .storyboard-lead-card {{
        min-height: auto !important;
        padding: 1.15rem !important;
      }}
      .storyboard-lead-title {{
        font-size: 1.55rem !important;
        line-height: 1.02 !important;
      }}
      .storyboard-lead-title br {{
        display: none !important;
      }}
      .storyboard-lead-copy {{
        font-size: 0.9rem !important;
        line-height: 1.46 !important;
        display: -webkit-box !important;
        -webkit-line-clamp: 2 !important;
        -webkit-box-orient: vertical !important;
        overflow: hidden !important;
      }}
      .storyboard-kpi-pills {{
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 0.4rem !important;
        width: 100% !important;
      }}
      .storyboard-kpi-pill {{
        font-size: 0.68rem !important;
        padding: 0.35rem 0.6rem !important;
      }}
      .storyboard-lead-content .btn-gold-broadcast {{
        width: 100% !important;
        justify-content: center !important;
        font-size: 0.9rem !important;
        padding: 0.65rem 0.85rem !important;
      }}
      .storyboard-duo-grid {{
        display: flex !important;
        overflow-x: auto !important;
        scroll-snap-type: x mandatory !important;
        -webkit-overflow-scrolling: touch !important;
        scrollbar-width: none !important;
        gap: 0.75rem !important;
        padding-bottom: 0.35rem !important;
      }}
      .storyboard-duo-grid::-webkit-scrollbar {{
        display: none !important;
      }}
      .storyboard-duo-grid > .storyboard-card {{
        flex: 0 0 85% !important;
        max-width: 85% !important;
        scroll-snap-align: start !important;
      }}
      .storyboard-card-visual {{
        height: 150px !important;
        padding: 0.85rem !important;
      }}
      .storyboard-card-body {{
        padding: 1rem !important;
        gap: 0.55rem !important;
      }}
      .storyboard-card-title {{
        font-size: 1.38rem !important;
      }}
      .storyboard-card-copy {{
        font-size: 0.88rem !important;
        line-height: 1.44 !important;
        display: -webkit-box !important;
        -webkit-line-clamp: 2 !important;
        -webkit-box-orient: vertical !important;
        overflow: hidden !important;
      }}

      /* 5. PAGE 2 (SQUADRE): BARRA FILTRI TOUCH 4 SETTORI + LISTA BROADCAST LEGGIBILE */
      #subpane-sq-organico .filter-chips-row {{
        display: grid !important;
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
        gap: 0.36rem !important;
        margin-bottom: 1rem !important;
      }}
      #subpane-sq-organico .filter-chip {{
        width: 100% !important;
        padding: 0.5rem 0.25rem !important;
        font-size: 0.7rem !important;
        letter-spacing: 0.03em !important;
        text-align: center !important;
        border-radius: 8px !important;
        white-space: nowrap !important;
      }}
      .fc-desktop {{
        display: none !important;
      }}
      .fc-mobile {{
        display: inline !important;
      }}
      .sector-bands-stack {{
        gap: 1.15rem !important;
      }}
      .sector-showcase-band {{
        grid-template-columns: 1fr !important;
      }}
      .ssb-visual {{
        min-height: 96px !important;
        padding: 0.78rem 0.92rem !important;
        border-right: none !important;
        border-bottom: 1px solid rgba(255, 222, 36, 0.22) !important;
      }}
      .ssb-title {{
        font-size: 1.42rem !important;
        margin-bottom: 0 !important;
      }}
      .ssb-desc {{
        display: none !important;
      }}
      .ssb-matrix {{
        padding: 0.6rem !important;
        gap: 0.42rem !important;
      }}
      /* Ogni squadra diventa una riga nativa iOS/Android: [Annata] [Nome Squadra + Pill Sotto] [Scheda →] */
      .sector-team-row {{
        display: grid !important;
        grid-template-columns: 62px minmax(0, 1fr) auto !important;
        align-items: center !important;
        padding: 0.6rem 0.68rem !important;
        gap: 0.55rem !important;
        border-radius: 10px !important;
      }}
      .str-year-box {{
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        padding: 0.3rem 0.28rem !important;
        border-radius: 7px !important;
      }}
      .str-year-lbl {{
        font-size: 0.44rem !important;
      }}
      .str-year-val {{
        font-size: 0.88rem !important;
      }}
      .str-title-line {{
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.16rem !important;
      }}
      .str-team-name {{
        font-size: 1.1rem !important;
        line-height: 1.05 !important;
        margin: 0 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        max-width: 100% !important;
      }}
      .str-format-pill {{
        font-size: 0.58rem !important;
        padding: 0.1rem 0.42rem !important;
      }}
      .str-actions {{
        display: flex !important;
        width: auto !important;
      }}
      .str-btn-extra {{
        display: none !important;
      }}
      .btn-str-gold {{
        width: auto !important;
        padding: 0.46rem 0.62rem !important;
        font-size: 0.76rem !important;
        border-radius: 7px !important;
        white-space: nowrap !important;
      }}

      /* 6. PAGE 3 (SCUOLA CALCIO & TORNEO VIGANÒ): LAYOUT MOBILE PULITO, PILASTRI 100% VISIBILI E MOSAICO 1+2 */
      .academy-manifesto-stage,
      .uefa-charter-stage,
      .vigano-monument-stage {{
        padding: 1.05rem !important;
        margin-bottom: 1.15rem !important;
        border-radius: 14px !important;
      }}
      .academy-manifesto-grid {{
        grid-template-columns: 1fr !important;
        gap: 0.9rem !important;
      }}
      .academy-hero-title {{
        font-size: clamp(1.48rem, 6.2vw, 1.82rem) !important;
        line-height: 1.02 !important;
        margin-bottom: 0.5rem !important;
      }}
      .academy-sec-title {{
        font-size: clamp(1.38rem, 5.8vw, 1.68rem) !important;
        line-height: 1.04 !important;
      }}
      .academy-lead-copy {{
        font-size: 0.85rem !important;
        line-height: 1.46 !important;
        display: -webkit-box !important;
        -webkit-line-clamp: 4 !important;
        -webkit-box-orient: vertical !important;
        overflow: hidden !important;
      }}
      .academy-badge-cluster {{
        gap: 0.35rem !important;
        margin-bottom: 0.55rem !important;
      }}
      .academy-badge-cluster .academy-official-pill:nth-child(3) {{
        display: none !important;
      }}
      .academy-official-pill {{
        font-size: 0.58rem !important;
        padding: 0.22rem 0.5rem !important;
      }}
      .academy-kpi-strip {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.45rem !important;
        margin: 0.75rem 0 !important;
      }}
      .academy-kpi-box {{
        padding: 0.55rem 0.65rem !important;
      }}
      .academy-kpi-num {{
        font-size: 1.18rem !important;
      }}
      .academy-kpi-lbl {{
        font-size: 0.58rem !important;
      }}
      .academy-cta-bar {{
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 0.6rem !important;
        padding-top: 0.8rem !important;
      }}
      .academy-cta-btns {{
        display: grid !important;
        grid-template-columns: 1fr !important;
        gap: 0.48rem !important;
        width: 100% !important;
      }}
      .academy-cta-btns .btn-gold-broadcast,
      .academy-cta-btns .btn-ghost-broadcast {{
        width: 100% !important;
        justify-content: center !important;
        padding: 0.62rem 0.45rem !important;
        font-size: 0.74rem !important;
        white-space: nowrap !important;
      }}
      .academy-visual-card {{
        min-height: 185px !important;
      }}
      .academy-seal-bar {{
        margin: auto 0.6rem 0.6rem !important;
        padding: 0.48rem 0.68rem !important;
      }}
      .academy-visual-overlay {{
        display: none !important;
      }}
      /* I 4 Pilastri diventano uno Stepper 1-Card-alla-Volta con Frecce su Mobile */
      #academy-pillars-grid {{
        display: block !important;
        overflow: visible !important;
        margin-bottom: 0.48rem !important;
        padding-bottom: 0 !important;
      }}
      #academy-pillars-grid .academy-pillar-card {{
        display: none !important;
        flex: none !important;
        max-width: 100% !important;
        width: 100% !important;
        padding: 0.95rem 1.02rem !important;
        gap: 0.45rem !important;
      }}
      #academy-pillars-grid .academy-pillar-card.is-active-slide {{
        display: flex !important;
      }}
      .academy-pillar-num {{
        font-size: 1.95rem !important;
        top: 0.45rem !important;
        right: 0.65rem !important;
      }}
      .academy-pillar-icon {{
        width: 32px !important;
        height: 32px !important;
        margin-bottom: 0.25rem !important;
      }}
      .academy-pillar-title {{
        font-size: 1.12rem !important;
        line-height: 1.12 !important;
        margin-bottom: 0.22rem !important;
      }}
      .academy-pillar-desc {{
        font-size: 0.82rem !important;
        line-height: 1.44 !important;
        display: block !important;
        -webkit-line-clamp: unset !important;
        overflow: visible !important;
      }}
      .academy-pillar-meta {{
        padding-top: 0.45rem !important;
        font-size: 0.56rem !important;
      }}
      /* Carta dei Diritti dei Bambini: Stepper 1-Card-alla-Volta con Frecce su Mobile */
      #uefa-charter-grid {{
        display: block !important;
        overflow: visible !important;
        margin-top: 0.65rem !important;
        margin-bottom: 0.48rem !important;
        padding-bottom: 0 !important;
      }}
      #uefa-charter-grid .uefa-right-card {{
        display: none !important;
        flex: none !important;
        max-width: 100% !important;
        width: 100% !important;
        padding: 0.88rem 0.98rem !important;
        gap: 0.28rem !important;
      }}
      #uefa-charter-grid .uefa-right-card.is-active-slide {{
        display: flex !important;
      }}
      .uefa-right-title {{
        font-size: 1.06rem !important;
      }}
      .uefa-right-desc {{
        font-size: 0.82rem !important;
        line-height: 1.42 !important;
      }}
      /* Torneo Stefano Viganò: Layout Compatto Mobile con Carosello 1-Foto a Frecce e Zero Overlay */
      #subpane-sq-torneo .section-header > .btn-gold-broadcast {{
        display: none !important;
      }}
      #subpane-sq-torneo .vigano-monument-stage {{
        padding: 1.05rem 1rem !important;
      }}
      .vigano-top-badges.vigano-mobile-only {{
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 0.38rem !important;
        margin-bottom: 0.45rem !important;
      }}
      .vigano-title-dot {{
        display: none !important;
      }}
      .vigano-title-memorial {{
        display: block !important;
        color: var(--acos-yellow) !important;
        font-size: 0.78em !important;
        margin-top: 0.1rem !important;
      }}
      .vigano-lead-copy {{
        font-size: 0.82rem !important;
        line-height: 1.42 !important;
      }}
      .vigano-patronage-bar {{
        padding: 0.68rem 0.78rem !important;
        gap: 0.48rem !important;
        margin: 0.68rem 0 0.72rem !important;
        flex-direction: column !important;
        align-items: stretch !important;
      }}
      .vigano-patron-Main {{
        flex-direction: column-reverse !important;
        align-items: stretch !important;
        gap: 0.48rem !important;
        width: 100% !important;
      }}
      .vigano-patron-crest {{
        width: 100% !important;
        height: auto !important;
        max-height: 68px !important;
        padding: 5px 8px !important;
        border-radius: 8px !important;
        object-fit: contain !important;
      }}
      .vigano-patron-pills {{
        width: 100% !important;
      }}
      .vigano-patron-pill {{
        width: 100% !important;
        text-align: center !important;
        font-size: 0.56rem !important;
        padding: 0.26rem 0.45rem !important;
      }}
      #subpane-sq-torneo .photo-gallery-grid {{
        display: block !important;
        margin-top: 0.55rem !important;
        padding-bottom: 0 !important;
      }}
      #subpane-sq-torneo .gallery-thumb,
      #subpane-sq-torneo .gallery-thumb:first-child {{
        display: none !important;
        width: 100% !important;
        max-width: 100% !important;
        height: 178px !important;
        aspect-ratio: 16 / 10 !important;
        border-radius: 12px !important;
      }}
      #subpane-sq-torneo .gallery-thumb.is-active-slide {{
        display: block !important;
      }}
      .vigano-slider-bar.vigano-mobile-only {{
        display: grid !important;
        grid-template-columns: 42px 1fr 42px !important;
        align-items: center !important;
        gap: 0.5rem !important;
        margin-top: 0.48rem !important;
        padding: 0.38rem 0.45rem !important;
        background: rgba(5, 7, 12, 0.92) !important;
        border: 1px solid rgba(255, 222, 36, 0.34) !important;
        border-radius: 10px !important;
      }}
      .vigano-slider-arrow {{
        width: 42px !important;
        height: 34px !important;
        border-radius: 8px !important;
        background: rgba(255, 222, 36, 0.14) !important;
        border: 1px solid rgba(255, 222, 36, 0.48) !important;
        color: var(--acos-yellow) !important;
        font-family: var(--font-sans) !important;
        font-size: 1rem !important;
        font-weight: 900 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
      }}
      .vigano-slider-arrow.is-next {{
        background: var(--acos-yellow) !important;
        border-color: var(--acos-yellow) !important;
        color: #050609 !important;
      }}
      .vigano-slider-status {{
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.22rem !important;
        min-width: 0 !important;
        text-align: center !important;
      }}
      .vigano-slider-status > span:first-child {{
        font-family: var(--font-mono) !important;
        font-size: 0.6rem !important;
        font-weight: 800 !important;
        color: var(--text-white) !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        max-width: 100% !important;
      }}
      .vigano-slider-dots {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 0.32rem !important;
      }}
      .vigano-slider-dots .v-dot {{
        width: 6px !important;
        height: 6px !important;
        border-radius: 50% !important;
        background: rgba(255, 255, 255, 0.24) !important;
        transition: all 0.18s ease !important;
      }}
      .vigano-slider-dots .v-dot.active {{
        width: 18px !important;
        border-radius: 99px !important;
        background: var(--acos-yellow) !important;
      }}
      .vigano-mobile-cta-row {{
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.48rem !important;
        margin-top: 0.72rem !important;
        padding-top: 0.72rem !important;
        border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
      }}
      .vigano-mobile-cta-row .btn-gold-broadcast,
      .vigano-mobile-cta-row .btn-ghost-broadcast {{
        width: 100% !important;
        justify-content: center !important;
        padding: 0.62rem 0.45rem !important;
        font-size: 0.74rem !important;
        white-space: nowrap !important;
      }}
      /* Modal Scheda Squadra Mobile */
      #team-modal .modal-dialog {{
        padding: 1.15rem !important;
      }}
      #team-modal h3 {{
        font-size: 1.55rem !important;
        line-height: 1.02 !important;
      }}
      #team-modal .spc-data-row {{
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.15rem !important;
        padding: 0.48rem 0 !important;
      }}
      #team-modal .spc-val {{
        text-align: left !important;
      }}

      /* 7. PAGE 3 (IL CLUB): ORGANIGRAMMA COMPATTO, STORIA & GOTHIA CON STEPPER A FRECCIA, CUORE GIALLONERO */
      .club-manifesto-banner,
      .gothia-arena-stage,
      .org-stage,
      .cuore-ethical-stage {{
        padding: 1rem !important;
        margin-bottom: 1.05rem !important;
        border-radius: 14px !important;
      }}
      .club-manifesto-grid {{
        grid-template-columns: 1fr !important;
        gap: 0.85rem !important;
      }}
      .cmb-eyebrow {{
        font-size: 0.58rem !important;
        padding: 0.24rem 0.58rem !important;
        white-space: normal !important;
        line-height: 1.25 !important;
      }}
      .cmb-title {{
        font-size: 1.52rem !important;
        line-height: 1.02 !important;
      }}
      .cmb-lead {{
        font-size: 0.83rem !important;
        line-height: 1.44 !important;
        display: block !important;
        overflow: visible !important;
      }}
      .cmb-kpi-strip {{
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
        gap: 0.36rem !important;
      }}
      .cmb-kpi-box {{
        padding: 0.45rem 0.35rem !important;
        text-align: center !important;
      }}
      .cmb-kpi-num {{
        font-size: 1.02rem !important;
      }}
      .cmb-kpi-lbl {{
        font-size: 0.5rem !important;
        letter-spacing: 0.02em !important;
      }}
      /* Archivio Fotografico 1971: 1 foto alla volta con frecce, ZERO badge HD in sovrapposizione */
      .cmb-archive-zoom {{
        display: none !important;
      }}
      #storia-archive-duo {{
        display: block !important;
      }}
      #storia-archive-duo .cmb-archive-card {{
        display: none !important;
        min-height: 184px !important;
        height: 184px !important;
        width: 100% !important;
        border-radius: 12px !important;
      }}
      #storia-archive-duo .cmb-archive-card.is-active-slide {{
        display: flex !important;
      }}
      .cmb-archive-caption {{
        padding: 1.2rem 0.82rem 0.72rem !important;
      }}
      .cmb-archive-caption h4 {{
        font-size: 1.06rem !important;
        line-height: 1.05 !important;
      }}
      .cmb-archive-caption p {{
        display: block !important;
        font-size: 0.75rem !important;
        line-height: 1.32 !important;
        margin-top: 0.14rem !important;
      }}
      /* Le 6 Tappe Storiche: 1 Tappa alla volta con barra frecce (zero testo tagliato, pagina compatta) */
      #storia-milestones-grid {{
        display: block !important;
        overflow: visible !important;
        margin-bottom: 0.48rem !important;
        padding-bottom: 0 !important;
      }}
      #storia-milestones-grid .heritage-milestone-card {{
        display: none !important;
        width: 100% !important;
        max-width: 100% !important;
        padding: 1rem 1.05rem !important;
        gap: 0.48rem !important;
      }}
      #storia-milestones-grid .heritage-milestone-card.is-active-slide {{
        display: flex !important;
      }}
      .club-stepper-bar {{
        margin-top: 0 !important;
        margin-bottom: 1.15rem !important;
      }}
      .hmc-title {{
        font-size: 1.32rem !important;
        line-height: 1.05 !important;
      }}
      .hmc-desc {{
        font-size: 0.84rem !important;
        line-height: 1.44 !important;
        display: block !important;
        -webkit-line-clamp: unset !important;
        overflow: visible !important;
      }}
      /* Gothia Cup Svezia & Cina: 1 scheda alla volta con frecce e zero badge sovrapposti */
      .gothia-stage-header {{
        gap: 0.65rem !important;
        padding-bottom: 0.85rem !important;
      }}
      .gothia-stage-header p {{
        font-size: 0.83rem !important;
        line-height: 1.42 !important;
      }}
      .gothia-world-pill {{
        font-size: 0.6rem !important;
        padding: 0.35rem 0.55rem !important;
        width: 100% !important;
        text-align: center !important;
        justify-content: center !important;
        white-space: normal !important;
        line-height: 1.25 !important;
      }}
      #gothia-dual-grid {{
        display: block !important;
        overflow: visible !important;
        margin: 0.85rem 0 0.48rem !important;
        padding-bottom: 0 !important;
      }}
      #gothia-dual-grid .gothia-monument-card {{
        display: none !important;
        width: 100% !important;
        max-width: 100% !important;
      }}
      #gothia-dual-grid .gothia-monument-card.is-active-slide {{
        display: flex !important;
      }}
      .gothia-monument-visual {{
        height: 158px !important;
        padding: 0.65rem !important;
      }}
      .gothia-edition-tag {{
        display: none !important;
      }}
      .gothia-country-tag {{
        font-size: 0.64rem !important;
        padding: 0.22rem 0.55rem !important;
      }}
      .gothia-monument-body {{
        padding: 0.92rem 0.98rem !important;
        gap: 0.55rem !important;
      }}
      .gothia-monument-title {{
        font-size: 1.28rem !important;
        line-height: 1.04 !important;
      }}
      .gothia-monument-desc {{
        font-size: 0.83rem !important;
        line-height: 1.42 !important;
        display: block !important;
        -webkit-line-clamp: unset !important;
        overflow: visible !important;
      }}
      .gothia-kpi-row {{
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        gap: 0.38rem !important;
      }}
      .gothia-kpi-cell {{
        padding: 0.44rem 0.26rem !important;
        text-align: center !important;
      }}
      .gothia-kpi-val {{
        font-size: 0.92rem !important;
      }}
      .gothia-kpi-lbl {{
        font-size: 0.52rem !important;
      }}

      /* Organigramma Societario Mobile: Piramide Sinottica One-Screen (3 Livelli in 1 Schermata) */
      #subpane-club-org .org-stage {{
        padding: 0.72rem 0.68rem !important;
        margin-bottom: 0.85rem !important;
        border-radius: 14px !important;
      }}
      .org-stage-header {{
        margin-bottom: 0.48rem !important;
        padding-bottom: 0.44rem !important;
        gap: 0.35rem !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-wrap: wrap !important;
      }}
      .org-stage-header .section-eyebrow {{
        display: none !important;
      }}
      .org-stage-header .section-title {{
        font-size: 1.12rem !important;
        line-height: 1.05 !important;
      }}
      .org-fed-seal {{
        width: auto !important;
        font-size: 0.52rem !important;
        padding: 0.22rem 0.44rem !important;
        gap: 0.3rem !important;
      }}
      .org-fed-seal img {{
        width: 16px !important;
        height: 20px !important;
      }}
      .org-tier-label-bar {{
        margin: 0.18rem 0 0.34rem !important;
      }}
      .org-tier-tag {{
        white-space: nowrap !important;
        font-size: 0.52rem !important;
        line-height: 1.15 !important;
        letter-spacing: 0.06em !important;
        padding: 0.18rem 0.52rem !important;
        width: auto !important;
        text-align: left !important;
      }}
      .org-tier-rail {{
        display: block !important;
        opacity: 0.45 !important;
      }}
      .org-connector-bridge {{
        display: flex !important;
        height: 14px !important;
        margin: 0.12rem 0 !important;
      }}
      .org-connector-node {{
        width: 7px !important;
        height: 7px !important;
      }}
      /* Livello 01: Vertice Presidenziale affiancato a 2 colonne in cima alla piramide */
      .org-tier-presidency {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.38rem !important;
        margin-bottom: 0.2rem !important;
      }}
      .org-pres-card {{
        padding: 0.5rem 0.58rem !important;
        gap: 0.22rem !important;
        border-radius: 10px !important;
      }}
      .org-pres-card .org-card-top {{
        margin-bottom: 0 !important;
      }}
      .org-pres-card .org-card-top > span:last-child {{
        display: none !important;
      }}
      .org-pres-card .org-role-badge {{
        font-size: 0.49rem !important;
        padding: 0.14rem 0.38rem !important;
        letter-spacing: 0.04em !important;
      }}
      .org-pres-body {{
        flex-direction: row !important;
        align-items: center !important;
        gap: 0.42rem !important;
      }}
      .org-pres-shield,
      .org-pres-card .org-gold-slash,
      .org-pres-card .org-exec-desc {{
        display: none !important;
      }}
      .org-pres-card .org-name-stack {{
        display: flex !important;
        flex-direction: row !important;
        align-items: baseline !important;
        gap: 0.28rem !important;
        flex-wrap: wrap !important;
      }}
      .org-pres-card .org-first-name {{
        font-size: 0.68rem !important;
        margin: 0 !important;
      }}
      .org-pres-card .org-last-name {{
        font-size: 1.18rem !important;
        line-height: 1 !important;
      }}
      /* Livello 02: Direzione Esecutiva & Sportiva in Matrice Compatta a 4 righe orizzontali */
      .org-tier-management {{
        grid-template-columns: 1fr !important;
        gap: 0.3rem !important;
        margin-bottom: 0.2rem !important;
      }}
      .org-exec-card {{
        display: grid !important;
        grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr) !important;
        grid-template-areas:
          "name top"
          "name desc" !important;
        align-items: center !important;
        column-gap: 0.4rem !important;
        row-gap: 0.1rem !important;
        padding: 0.42rem 0.58rem !important;
        border-radius: 10px !important;
      }}
      .org-exec-card .org-card-top {{
        grid-area: top !important;
        justify-content: flex-end !important;
        margin: 0 !important;
      }}
      .org-exec-card .org-role-badge {{
        font-size: 0.48rem !important;
        padding: 0.12rem 0.36rem !important;
        letter-spacing: 0.04em !important;
      }}
      .org-monogram-shield {{
        display: none !important;
      }}
      .org-exec-card .org-name-stack {{
        grid-area: name !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: baseline !important;
        gap: 0.3rem !important;
        margin: 0 !important;
        flex-wrap: nowrap !important;
      }}
      .org-exec-card .org-first-name {{
        font-size: 0.7rem !important;
        margin: 0 !important;
      }}
      .org-exec-card .org-last-name {{
        font-size: 1.08rem !important;
        line-height: 1 !important;
      }}
      .org-exec-card .org-gold-slash {{
        display: none !important;
      }}
      .org-exec-card .org-exec-desc {{
        grid-area: desc !important;
        margin: 0 !important;
        padding: 0 !important;
        border-top: none !important;
        font-size: 0.62rem !important;
        line-height: 1.15 !important;
        text-align: right !important;
        color: rgba(255, 255, 255, 0.78) !important;
        display: block !important;
      }}
      .org-exec-card .org-exec-desc strong {{
        display: none !important;
      }}
      /* Livello 03: Consiglio Direttivo in Griglia Pill a 1 Riga */
      .org-council-deck {{
        padding: 0.52rem 0.58rem !important;
        border-radius: 11px !important;
      }}
      .org-council-header {{
        margin-bottom: 0.38rem !important;
        padding-bottom: 0.32rem !important;
        gap: 0.25rem !important;
      }}
      .org-council-title {{
        font-size: 0.92rem !important;
      }}
      .org-council-sub {{
        display: none !important;
      }}
      .org-council-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.28rem !important;
      }}
      .org-councilor-card {{
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        padding: 0.34rem 0.48rem !important;
        gap: 0.36rem !important;
        border-radius: 8px !important;
      }}
      .org-councilor-top {{
        order: 1 !important;
        margin: 0 !important;
        flex-shrink: 0 !important;
      }}
      .org-councilor-role {{
        display: none !important;
      }}
      .org-councilor-avatar {{
        width: 20px !important;
        height: 20px !important;
        font-size: 0.52rem !important;
        border-radius: 5px !important;
      }}
      .org-councilor-card .org-name-stack {{
        order: 2 !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: baseline !important;
        gap: 0.24rem !important;
        margin: 0 !important;
        min-width: 0 !important;
      }}
      .org-councilor-card .org-first-name {{
        font-size: 0.64rem !important;
        margin: 0 !important;
      }}
      .org-councilor-card .org-last-name {{
        font-size: 0.96rem !important;
        line-height: 1 !important;
      }}
      .org-councilor-card:last-child {{
        grid-column: 1 / -1 !important;
        justify-content: center !important;
      }}

      /* Cuore Giallonero Mobile: Banner Compatto + 1 Pilastro alla volta con Frecce */
      .cuore-lead-banner {{
        grid-template-columns: 1fr !important;
        padding: 0.92rem !important;
        gap: 0.68rem !important;
        margin-bottom: 0.85rem !important;
      }}
      .cuore-emblem-box {{
        width: 64px !important;
        height: 64px !important;
        border-radius: 14px !important;
        padding: 5px !important;
      }}
      .cuore-emblem-svg {{
        width: 52px !important;
        height: 52px !important;
      }}
      .cuore-emblem-crest {{
        width: 18px !important;
        height: 26px !important;
      }}
      .cuore-lead-copy h3 {{
        font-size: 1.38rem !important;
        line-height: 1.04 !important;
      }}
      .cuore-lead-copy p {{
        font-size: 0.82rem !important;
        line-height: 1.42 !important;
      }}
      .cuore-strada-quote {{
        padding: 0.72rem 0.84rem !important;
        gap: 0.28rem !important;
      }}
      .csq-text {{
        font-size: 0.78rem !important;
        line-height: 1.4 !important;
      }}
      #cuore-pillars-grid {{
        display: block !important;
        overflow: visible !important;
        margin-bottom: 0.48rem !important;
        padding-bottom: 0 !important;
      }}
      #cuore-pillars-grid .cuore-pillar-card {{
        display: none !important;
        width: 100% !important;
        max-width: 100% !important;
        padding: 0.95rem !important;
        gap: 0.65rem !important;
      }}
      #cuore-pillars-grid .cuore-pillar-card.is-active-slide {{
        display: flex !important;
      }}
      .cuore-pillar-head {{
        padding-bottom: 0.62rem !important;
      }}
      .cuore-pillar-title {{
        font-size: 1.28rem !important;
      }}
      .cuore-charity-item {{
        font-size: 0.8rem !important;
        padding: 0.46rem 0.58rem !important;
      }}

      /* 8. PAGE 5 (ISCRIZIONI, IBAN, KIT & TUTELA): DOSSIER A 2 FILIERE COMPATTE & MICRO-PILLOLE */
      .sp-header-kit-pill {{
        font-size: 0.64rem !important;
        padding: 0.3rem 0.52rem !important;
        margin-top: 0.35rem !important;
        line-height: 1.28 !important;
      }}
      .season-pass-grid {{
        display: grid !important;
        grid-template-columns: 1fr !important;
        overflow: visible !important;
        gap: 0.55rem !important;
        margin: 0.5rem 0 0.78rem !important;
        padding-bottom: 0 !important;
      }}
      .season-pass-card {{
        flex: none !important;
        max-width: 100% !important;
        padding: 0.72rem 0.78rem !important;
        gap: 0.42rem !important;
        border-radius: 11px !important;
      }}
      .season-pass-card > button {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        min-height: 30px !important;
        padding: 0.34rem 0.48rem !important;
        font-size: 0.7rem !important;
        border-radius: 6px !important;
        letter-spacing: 0.03em !important;
        white-space: nowrap !important;
      }}
      .sp-badge-row {{
        gap: 0.25rem !important;
        flex-wrap: nowrap !important;
      }}
      .sp-tier-tag {{
        font-size: 0.5rem !important;
        padding: 0.14rem 0.38rem !important;
        letter-spacing: 0.03em !important;
        white-space: nowrap !important;
      }}
      .sp-type-lbl {{
        font-size: 0.5rem !important;
        letter-spacing: 0.03em !important;
        white-space: nowrap !important;
      }}
      .sp-title {{
        font-size: 1.16rem !important;
        line-height: 1.04 !important;
        margin-top: 0.04rem !important;
      }}
      .sp-cats-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.32rem !important;
      }}
      .sp-cat-chip {{
        padding: 0.28rem 0.44rem !important;
        font-size: 0.7rem !important;
        border-radius: 6px !important;
      }}
      .sp-cat-chip em {{
        font-size: 0.56rem !important;
      }}
      .sp-breakdown {{
        padding: 0.42rem 0.56rem !important;
        gap: 0.24rem !important;
        border-radius: 7px !important;
      }}
      .sp-bd-row {{
        font-size: 0.7rem !important;
        padding-bottom: 0.18rem !important;
        gap: 0.3rem !important;
        white-space: nowrap !important;
      }}
      .sp-segreteria-strip {{
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 0.52rem !important;
        padding: 0.72rem 0.82rem !important;
        margin: 0 0 0.75rem !important;
        border-radius: 11px !important;
      }}
      .sps-eyebrow {{
        font-size: 0.54rem !important;
        letter-spacing: 0.05em !important;
      }}
      .sps-hours {{
        font-size: 0.74rem !important;
        line-height: 1.3 !important;
      }}
      .sps-actions {{
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.42rem !important;
        width: 100% !important;
      }}
      .sps-btn {{
        width: 100% !important;
        min-height: 34px !important;
        padding: 0.38rem 0.48rem !important;
        font-size: 0.72rem !important;
        border-radius: 7px !important;
      }}
      .treasury-iban-stage,
      .safeguarding-command-stage {{
        padding: 0.82rem 0.85rem !important;
        margin-bottom: 0.85rem !important;
        border-radius: 12px !important;
      }}
      .treasury-top-row {{
        gap: 0.52rem !important;
        padding-bottom: 0.65rem !important;
        margin-bottom: 0.65rem !important;
      }}
      .iban-code {{
        font-size: 0.88rem !important;
        padding: 0.42rem 0.5rem !important;
        word-break: break-all !important;
        width: 100% !important;
        text-align: center !important;
        background: rgba(5, 6, 9, 0.72) !important;
        border: 1px solid rgba(255, 222, 36, 0.28) !important;
        border-radius: 7px !important;
      }}
      .treasury-top-row > div:last-child {{
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 0.4rem !important;
        width: 100% !important;
      }}
      .treasury-top-row .btn-gold-broadcast,
      .treasury-top-row .btn-ghost-broadcast {{
        width: 100% !important;
        justify-content: center !important;
        font-size: 0.7rem !important;
        padding: 0.36rem 0.4rem !important;
        border-radius: 6px !important;
        letter-spacing: 0.03em !important;
        min-height: 31px !important;
      }}
      .treasury-rules-grid {{
        grid-template-columns: 1fr !important;
        gap: 0.36rem !important;
      }}
      .treasury-rule-box {{
        padding: 0.46rem 0.62rem !important;
        border-radius: 8px !important;
        gap: 0.1rem !important;
      }}
      .trb-tag {{
        font-size: 0.52rem !important;
      }}
      .trb-val {{
        font-size: 0.76rem !important;
        line-height: 1.24 !important;
      }}
      .portal-desk-grid {{
        display: grid !important;
        grid-template-columns: 1fr !important;
        overflow: visible !important;
        gap: 0.5rem !important;
        margin-bottom: 0.85rem !important;
        padding-bottom: 0 !important;
      }}
      .portal-desk-card {{
        flex: none !important;
        max-width: 100% !important;
        padding: 0.72rem 0.82rem !important;
        gap: 0.42rem !important;
        border-radius: 10px !important;
      }}
      .pdc-num {{
        font-size: 0.52rem !important;
        margin-bottom: 0.1rem !important;
      }}
      .pdc-icon {{
        width: 28px !important;
        height: 28px !important;
        font-size: 0.82rem !important;
        border-radius: 6px !important;
      }}
      .pdc-title {{
        font-size: 1.12rem !important;
      }}
      .pdc-desc {{
        font-size: 0.75rem !important;
        line-height: 1.32 !important;
        margin-top: 0.25rem !important;
      }}
      .pdc-actions {{
        gap: 0.38rem !important;
      }}
      .pdc-actions a {{
        padding: 0.34rem 0.45rem !important;
        font-size: 0.7rem !important;
        border-radius: 6px !important;
        letter-spacing: 0.03em !important;
        min-height: 30px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
      }}
      .safeguarding-grid {{
        grid-template-columns: 1fr !important;
        gap: 0.55rem !important;
        margin-top: 0.65rem !important;
      }}
      .safe-officer-card {{
        padding: 0.72rem 0.82rem !important;
        gap: 0.42rem !important;
      }}
      .safe-officer-tag {{
        font-size: 0.52rem !important;
        margin-bottom: 0.12rem !important;
      }}
      .safe-officer-name {{
        font-size: 1.22rem !important;
      }}
      .safe-officer-desc {{
        font-size: 0.75rem !important;
        margin-top: 0.22rem !important;
        line-height: 1.34 !important;
      }}
      .safe-officer-contact-pill {{
        font-size: 0.68rem !important;
        padding: 0.34rem 0.52rem !important;
        gap: 0.3rem !important;
      }}
      .safe-docs-stack {{
        gap: 0.42rem !important;
      }}
      .safe-doc-row {{
        display: grid !important;
        grid-template-columns: minmax(0, 1fr) auto !important;
        align-items: center !important;
        padding: 0.54rem 0.68rem !important;
        gap: 0.45rem !important;
        border-radius: 9px !important;
      }}
      .safe-doc-tag {{
        font-size: 0.5rem !important;
      }}
      .safe-doc-title {{
        font-size: 0.88rem !important;
        line-height: 1.08 !important;
      }}
      .safe-doc-row a,
      .safe-doc-row .btn-gold-broadcast,
      .safe-doc-row .btn-ghost-broadcast {{
        width: auto !important;
        flex-shrink: 0 !important;
        padding: 0.32rem 0.56rem !important;
        font-size: 0.68rem !important;
        border-radius: 6px !important;
        letter-spacing: 0.03em !important;
        white-space: nowrap !important;
        min-height: 28px !important;
      }}

      /* 9. PAGE 6 (STADI & CONTATTI): STEPPER SINGOLO STADIO, CENTRALINO PRIMA DEL FORM & MICRO-BOTTONI */
      #stadium-arenas-grid {{
        display: block !important;
        overflow: visible !important;
        margin-bottom: 0.42rem !important;
        padding-bottom: 0 !important;
      }}
      #stadium-arenas-grid .stadium-arena-card {{
        display: none !important;
        width: 100% !important;
        max-width: 100% !important;
      }}
      #stadium-arenas-grid .stadium-arena-card.is-active-slide {{
        display: flex !important;
      }}
      .sac-visual-header {{
        min-height: 106px !important;
        padding: 0.72rem 0.82rem !important;
      }}
      .sac-arena-tag,
      .sac-dae-pill {{
        font-size: 0.52rem !important;
        padding: 0.14rem 0.38rem !important;
      }}
      .sac-title {{
        font-size: 1.24rem !important;
      }}
      .sac-address {{
        font-size: 0.72rem !important;
      }}
      .sac-body {{
        padding: 0.72rem 0.82rem !important;
        gap: 0.5rem !important;
      }}
      .arena-map-frame {{
        height: 138px !important;
      }}
      .sac-actions-bar {{
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 0.38rem !important;
      }}
      .sac-actions-bar button,
      .sac-actions-bar a,
      .sac-actions-bar .btn-gold-broadcast,
      .sac-actions-bar .btn-ghost-broadcast {{
        width: 100% !important;
        justify-content: center !important;
        font-size: 0.7rem !important;
        padding: 0.36rem 0.38rem !important;
        border-radius: 6px !important;
        letter-spacing: 0.03em !important;
        min-height: 30px !important;
        white-space: nowrap !important;
      }}
      /* Su telefono mostriamo PRIMA il Centralino con Orari & Numeri Diretti e DOPO il modulo */
      .contact-command-stage {{
        display: flex !important;
        flex-direction: column-reverse !important;
        gap: 0.75rem !important;
      }}
      .switchboard-stack {{
        gap: 0.42rem !important;
      }}
      .switchboard-card {{
        padding: 0.6rem 0.74rem !important;
        gap: 0.45rem !important;
        border-radius: 10px !important;
      }}
      .swc-tag {{
        font-size: 0.5rem !important;
      }}
      .swc-main-val {{
        font-size: 0.98rem !important;
        line-height: 1.1 !important;
      }}
      .swc-meta {{
        font-size: 0.68rem !important;
        line-height: 1.24 !important;
      }}
      .swc-cta-btn {{
        padding: 0.3rem 0.58rem !important;
        font-size: 0.68rem !important;
        border-radius: 6px !important;
        min-height: 28px !important;
        letter-spacing: 0.03em !important;
      }}
      .concierge-form-card {{
        padding: 0.82rem 0.85rem !important;
        border-radius: 12px !important;
        gap: 0.55rem !important;
      }}
      .concierge-form-title {{
        font-size: 1.28rem !important;
      }}
      .cf-profile-tabs {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.34rem !important;
        margin: 0.42rem 0 0.25rem !important;
      }}
      .cf-profile-tab {{
        padding: 0.34rem 0.42rem !important;
        border-radius: 6px !important;
      }}
      .cfp-title {{
        font-size: 0.68rem !important;
      }}
      .cf-cat-phone-grid {{
        grid-template-columns: 1fr !important;
        gap: 0.48rem !important;
      }}
      .form-input,
      .form-select,
      .form-textarea {{
        padding: 0.5rem 0.68rem !important;
        font-size: 0.8rem !important;
        border-radius: 6px !important;
      }}
      .concierge-submit-row {{
        display: grid !important;
        grid-template-columns: 1fr !important;
        gap: 0.4rem !important;
      }}
      .concierge-submit-row .btn-gold-broadcast,
      .concierge-submit-row .btn-ghost-broadcast {{
        width: 100% !important;
        justify-content: center !important;
        font-size: 0.72rem !important;
        padding: 0.38rem 0.45rem !important;
        border-radius: 6px !important;
        min-height: 32px !important;
        letter-spacing: 0.03em !important;
      }}

      /* 10. PARTNER UFFICIALI: MATRICE PARITARIA 2x5 SU MOBILE (TUTTI I 10 LOGHI VISIBILI AL 100% SENZA SCORRIMENTO NASCOSTO) */
      .sponsors-grid {{
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        overflow-x: visible !important;
        gap: 0.55rem !important;
        padding-bottom: 0 !important;
      }}
      .sponsor-card {{
        padding: 0.35rem !important;
        background: rgba(16, 20, 30, 0.85) !important;
        border: 1px solid rgba(255, 222, 36, 0.26) !important;
        border-radius: 10px !important;
      }}
      .sponsor-plate {{
        height: 58px !important;
        padding: 0.32rem 0.55rem !important;
        border-radius: 7px !important;
        border: none !important;
      }}
      .sponsor-plate img {{
        max-height: 100% !important;
        max-width: 100% !important;
      }}

      .footer-main-wrap {{
        padding: 1.75rem 1rem 1.4rem !important;
      }}
      .crest-footer {{
        width: 56px !important;
        height: 70px !important;
      }}
      .footer-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 1.35rem 1rem !important;
      }}
      .footer-col-brand {{
        grid-column: 1 / -1 !important;
        padding-right: 0 !important;
        padding-bottom: 1.1rem !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        gap: 0.75rem !important;
      }}
      .footer-brand-desc {{
        font-size: 0.8rem !important;
        max-width: 100% !important;
      }}
      /* Su mobile la barra inferiore fissa già copre le sezioni principali */
      .footer-col-nav {{
        display: none !important;
      }}
      .footer-col h4 {{
        font-size: 0.66rem !important;
        margin-bottom: 0.75rem !important;
      }}
      .footer-links {{
        gap: 0.52rem !important;
      }}
      .footer-links a,
      .footer-links button.footer-text-link,
      .footer-links span.footer-meta-item {{
        font-size: 0.8rem !important;
      }}
      .footer-bottom-ribbon {{
        padding: 0.78rem 0 calc(4.4rem + env(safe-area-inset-bottom)) !important;
        font-size: 0.68rem !important;
      }}
      .footer-bottom-inner {{
        padding: 0 0.85rem !important;
        justify-content: center !important;
        text-align: center !important;
        gap: 0.26rem !important;
      }}
      .footer-legal-line-1 {{
        font-size: 0.84rem !important;
        letter-spacing: 0.04em !important;
      }}
      .footer-legal-line-2 {{
        font-size: 0.7rem !important;
        gap: 0.38rem !important;
      }}
      .footer-legal-line-3 {{
        font-size: 0.62rem !important;
        gap: 0.32rem !important;
      }}

      /* 11. MODALS MOBILE FIT */
      .modal-dialog {{
        padding: 1.15rem !important;
        max-height: 84vh !important;
      }}
      .spc-data-row {{
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.12rem !important;
      }}
      .spc-val {{
        text-align: left !important;
      }}
      #team-modal-body .btn-gold-broadcast,
      #team-modal-body .btn-ghost-broadcast {{
        width: 100% !important;
        justify-content: center !important;
      }}
      .floating-studio-switcher {{
        display: none !important;
      }}
    }}

    @media (max-width: 380px) {{
      .crest-header {{
        width: 66px !important;
        height: 80px !important;
      }}
      .club-brand-title {{
        font-size: 1.84rem !important;
      }}
      .club-brand-sub {{
        font-size: 0.72rem !important;
      }}
      .hero-cta-row {{
        grid-template-columns: 1fr !important;
      }}
      .academy-pillars-grid,
      .heritage-milestone-grid,
      .org-tier-management,
      .footer-venues-grid {{
        grid-template-columns: 1fr !important;
      }}
    }}

    @container (max-width: 1150px) {{
      .hero-stage-grid, .venues-grid, .storyboard-duo-grid, .home-sectors-grid, .home-heritage-showcase {{ grid-template-columns: 1fr !important; }}
      .matches-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }}
      .hero-telemetry-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }}
      .main-nav, .footer-mirror-nav {{ display: none !important; }}
      .mobile-burger {{ display: inline-flex !important; }}
      .ribbon-right {{ display: none !important; }}
    }}

    @container (max-width: 640px) {{
      .top-Broadcast-ribbon {{ display: flex !important; height: 28px !important; min-height: 28px !important; padding: 0 0.35rem !important; justify-content: center !important; }}
      .top-ribbon-inner {{ padding: 0 0.25rem !important; justify-content: center !important; }}
      .ribbon-left {{ width: 100% !important; justify-content: center !important; gap: 0.35rem !important; font-size: 0.6rem !important; letter-spacing: 0.025em !important; white-space: nowrap !important; }}
      .ribbon-only-desktop {{ display: none !important; }}
      .ribbon-right {{ display: none !important; }}
      .site-header, .header-inner {{ height: 118px !important; min-height: 118px !important; padding: 0.75rem 1.15rem !important; justify-content: center !important; }}
      .crest-header {{ width: 74px !important; height: 90px !important; }}
      .crest-footer {{ width: 58px !important; height: 72px !important; }}
      .club-brand {{ gap: 1.05rem !important; }}
      .club-brand-title {{ font-size: 2.06rem !important; white-space: nowrap !important; }}
      .club-brand-sub {{ font-size: 0.78rem !important; margin-top: 0.34rem !important; white-space: nowrap !important; }}
      .acos-subnav-wrap {{ top: 118px !important; padding: 0.55rem 0 !important; }}
      .header-actions, .header-actions .btn-gold-broadcast, .mobile-burger, #home-storyboard-section {{ display: none !important; }}
      .hero-monumental-h1 .hollow-line, .hero-monumental-h1 .stroke-line, .hero-monumental-h1 .gold-line {{ font-size: clamp(1.92rem, 8.4vw, 2.35rem) !important; line-height: 0.94 !important; white-space: normal !important; }}
      .hero-cta-row {{ display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.48rem !important; width: 100% !important; max-width: 100% !important; }}
      .hero-deck-btn {{ width: 100% !important; min-width: 0 !important; justify-content: space-between !important; font-size: 0.78rem !important; letter-spacing: 0.025em !important; padding: 0.66rem 0.55rem !important; gap: 0.3rem !important; border-radius: 8px !important; }}
      .hero-deck-arrow {{ width: 18px !important; height: 18px !important; font-size: 0.7rem !important; }}
      .sponsors-grid {{ display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)) !important; max-width: 100% !important; overflow-x: visible !important; gap: 0.55rem !important; }}
      .sponsor-card {{ padding: 0.35rem !important; border: 1px solid rgba(255, 222, 36, 0.26) !important; border-radius: 10px !important; }}
      .sponsor-plate img {{ max-height: 100% !important; max-width: 100% !important; }}
      .footer-main-wrap {{ padding: 1.75rem 1rem 1.4rem !important; }}
      .footer-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 1.35rem 1rem !important; }}
      .footer-col-brand {{ grid-column: 1 / -1 !important; padding-bottom: 1.1rem !important; border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important; }}
      .footer-col-nav {{ display: none !important; }}
      #subpane-sq-organico .filter-chips-row {{ display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 0.36rem !important; margin-bottom: 1rem !important; }}
      #subpane-sq-organico .filter-chip {{ width: 100% !important; padding: 0.5rem 0.25rem !important; font-size: 0.7rem !important; letter-spacing: 0.03em !important; text-align: center !important; border-radius: 8px !important; white-space: nowrap !important; }}
      .fc-desktop {{ display: none !important; }}
      .fc-mobile {{ display: inline !important; }}
      .sector-showcase-band {{ grid-template-columns: 1fr !important; }}
      .ssb-visual {{ min-height: 96px !important; padding: 0.78rem 0.92rem !important; border-right: none !important; border-bottom: 1px solid rgba(255, 222, 36, 0.22) !important; }}
      .ssb-title {{ font-size: 1.42rem !important; margin-bottom: 0 !important; }}
      .ssb-desc {{ display: none !important; }}
      .ssb-matrix {{ padding: 0.6rem !important; gap: 0.42rem !important; }}
      .sector-team-row {{ display: grid !important; grid-template-columns: 62px minmax(0, 1fr) auto !important; align-items: center !important; padding: 0.6rem 0.68rem !important; gap: 0.55rem !important; border-radius: 10px !important; }}
      .str-year-box {{ flex-direction: column !important; justify-content: center !important; align-items: center !important; padding: 0.3rem 0.28rem !important; border-radius: 7px !important; }}
      .str-year-lbl {{ font-size: 0.44rem !important; }}
      .str-year-val {{ font-size: 0.88rem !important; }}
      .str-title-line {{ flex-direction: column !important; align-items: flex-start !important; gap: 0.16rem !important; }}
      .str-team-name {{ font-size: 1.1rem !important; line-height: 1.05 !important; margin: 0 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; max-width: 100% !important; }}
      .str-format-pill {{ font-size: 0.58rem !important; padding: 0.1rem 0.42rem !important; }}
      .str-actions {{ display: flex !important; width: auto !important; }}
      .str-btn-extra {{ display: none !important; }}
      .btn-str-gold {{ width: auto !important; padding: 0.46rem 0.62rem !important; font-size: 0.76rem !important; border-radius: 7px !important; white-space: nowrap !important; }}
      .academy-manifesto-stage, .uefa-charter-stage, .vigano-monument-stage {{ padding: 1.05rem !important; margin-bottom: 1.15rem !important; border-radius: 14px !important; }}
      .academy-manifesto-grid, .vigano-grid {{ grid-template-columns: 1fr !important; gap: 0.9rem !important; }}
      .academy-hero-title {{ font-size: clamp(1.48rem, 6.2vw, 1.82rem) !important; line-height: 1.02 !important; margin-bottom: 0.5rem !important; }}
      .academy-sec-title {{ font-size: clamp(1.38rem, 5.8vw, 1.68rem) !important; line-height: 1.04 !important; }}
      .academy-lead-copy {{ font-size: 0.85rem !important; line-height: 1.46 !important; display: -webkit-box !important; -webkit-line-clamp: 4 !important; -webkit-box-orient: vertical !important; overflow: hidden !important; }}
      .academy-badge-cluster .academy-official-pill:nth-child(3) {{ display: none !important; }}
      .academy-kpi-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.45rem !important; margin: 0.75rem 0 !important; }}
      .academy-cta-bar {{ flex-direction: column !important; align-items: stretch !important; gap: 0.6rem !important; padding-top: 0.8rem !important; }}
      .academy-cta-btns {{ display: grid !important; grid-template-columns: 1fr !important; gap: 0.48rem !important; width: 100% !important; }}
      .academy-cta-btns .btn-gold-broadcast, .academy-cta-btns .btn-ghost-broadcast {{ width: 100% !important; justify-content: center !important; padding: 0.62rem 0.45rem !important; font-size: 0.74rem !important; white-space: nowrap !important; }}
      .academy-visual-card {{ min-height: 185px !important; }}
      .academy-seal-bar {{ margin: auto 0.6rem 0.6rem !important; padding: 0.48rem 0.68rem !important; }}
      .academy-visual-overlay {{ display: none !important; }}
      #academy-pillars-grid {{ display: block !important; overflow: visible !important; margin-bottom: 0.48rem !important; padding-bottom: 0 !important; }}
      #academy-pillars-grid .academy-pillar-card {{ display: none !important; flex: none !important; max-width: 100% !important; width: 100% !important; padding: 0.95rem 1.02rem !important; gap: 0.45rem !important; }}
      #academy-pillars-grid .academy-pillar-card.is-active-slide {{ display: flex !important; }}
      .academy-pillar-title {{ font-size: 1.12rem !important; line-height: 1.12 !important; margin-bottom: 0.22rem !important; white-space: normal !important; }}
      .academy-pillar-desc {{ font-size: 0.82rem !important; line-height: 1.44 !important; display: block !important; -webkit-line-clamp: unset !important; overflow: visible !important; }}
      #uefa-charter-grid {{ display: block !important; overflow: visible !important; margin-top: 0.65rem !important; margin-bottom: 0.48rem !important; padding-bottom: 0 !important; }}
      #uefa-charter-grid .uefa-right-card {{ display: none !important; flex: none !important; max-width: 100% !important; width: 100% !important; padding: 0.88rem 0.98rem !important; gap: 0.28rem !important; }}
      #uefa-charter-grid .uefa-right-card.is-active-slide {{ display: flex !important; }}
      .uefa-right-title {{ font-size: 1.06rem !important; white-space: normal !important; }}
      #subpane-sq-torneo .section-header > .btn-gold-broadcast {{ display: none !important; }}
      #subpane-sq-torneo .vigano-monument-stage {{ padding: 1.05rem 1rem !important; }}
      .vigano-top-badges.vigano-mobile-only {{ display: flex !important; flex-wrap: wrap !important; gap: 0.38rem !important; margin-bottom: 0.45rem !important; }}
      .vigano-title-dot {{ display: none !important; }}
      .vigano-title-memorial {{ display: block !important; color: var(--acos-yellow) !important; font-size: 0.78em !important; margin-top: 0.1rem !important; }}
      .vigano-lead-copy {{ font-size: 0.82rem !important; line-height: 1.42 !important; }}
      .vigano-patronage-bar {{ padding: 0.68rem 0.78rem !important; gap: 0.48rem !important; margin: 0.68rem 0 0.72rem !important; flex-direction: column !important; align-items: stretch !important; }}
      .vigano-patron-Main {{ flex-direction: column-reverse !important; align-items: stretch !important; gap: 0.48rem !important; width: 100% !important; }}
      .vigano-patron-crest {{ width: 100% !important; height: auto !important; max-height: 68px !important; padding: 5px 8px !important; border-radius: 8px !important; object-fit: contain !important; }}
      .vigano-patron-pills {{ width: 100% !important; }}
      .vigano-patron-pill {{ width: 100% !important; text-align: center !important; font-size: 0.56rem !important; padding: 0.26rem 0.45rem !important; }}
      #subpane-sq-torneo .photo-gallery-grid {{ display: block !important; margin-top: 0.55rem !important; padding-bottom: 0 !important; }}
      #subpane-sq-torneo .gallery-thumb, #subpane-sq-torneo .gallery-thumb:first-child {{ display: none !important; width: 100% !important; max-width: 100% !important; height: 178px !important; aspect-ratio: 16 / 10 !important; border-radius: 12px !important; }}
      #subpane-sq-torneo .gallery-thumb.is-active-slide {{ display: block !important; }}
      .vigano-slider-bar.vigano-mobile-only {{ display: grid !important; grid-template-columns: 42px 1fr 42px !important; align-items: center !important; gap: 0.5rem !important; margin-top: 0.48rem !important; padding: 0.38rem 0.45rem !important; background: rgba(5, 7, 12, 0.92) !important; border: 1px solid rgba(255, 222, 36, 0.34) !important; border-radius: 10px !important; }}
      .vigano-slider-arrow {{ width: 42px !important; height: 34px !important; border-radius: 8px !important; background: rgba(255, 222, 36, 0.14) !important; border: 1px solid rgba(255, 222, 36, 0.48) !important; color: var(--acos-yellow) !important; font-family: var(--font-sans) !important; font-size: 1rem !important; font-weight: 900 !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; }}
      .vigano-slider-arrow.is-next {{ background: var(--acos-yellow) !important; border-color: var(--acos-yellow) !important; color: #050609 !important; }}
      .vigano-slider-status {{ display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; gap: 0.22rem !important; min-width: 0 !important; text-align: center !important; }}
      .vigano-slider-status > span:first-child {{ font-family: var(--font-mono) !important; font-size: 0.6rem !important; font-weight: 800 !important; color: var(--text-white) !important; letter-spacing: 0.04em !important; text-transform: uppercase !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; max-width: 100% !important; }}
      .vigano-slider-dots {{ display: inline-flex !important; align-items: center !important; gap: 0.32rem !important; }}
      .vigano-slider-dots .v-dot {{ width: 6px !important; height: 6px !important; border-radius: 50% !important; background: rgba(255, 255, 255, 0.24) !important; transition: all 0.18s ease !important; }}
      .vigano-slider-dots .v-dot.active {{ width: 18px !important; border-radius: 99px !important; background: var(--acos-yellow) !important; }}
      .vigano-mobile-cta-row {{ display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.48rem !important; margin-top: 0.72rem !important; padding-top: 0.72rem !important; border-top: 1px solid rgba(255, 255, 255, 0.1) !important; }}
      .vigano-mobile-cta-row .btn-gold-broadcast, .vigano-mobile-cta-row .btn-ghost-broadcast {{ width: 100% !important; justify-content: center !important; padding: 0.62rem 0.45rem !important; font-size: 0.74rem !important; white-space: nowrap !important; }}
      .club-manifesto-banner, .gothia-arena-stage, .org-stage, .cuore-ethical-stage {{ padding: 1rem !important; margin-bottom: 1.05rem !important; border-radius: 14px !important; }}
      .club-manifesto-grid {{ grid-template-columns: 1fr !important; gap: 0.85rem !important; }}
      .cmb-eyebrow {{ font-size: 0.58rem !important; padding: 0.24rem 0.58rem !important; white-space: normal !important; line-height: 1.25 !important; }}
      .cmb-title {{ font-size: 1.52rem !important; line-height: 1.02 !important; }}
      .cmb-lead {{ font-size: 0.83rem !important; line-height: 1.44 !important; display: block !important; overflow: visible !important; }}
      .cmb-kpi-strip {{ grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 0.36rem !important; }}
      .cmb-kpi-box {{ padding: 0.45rem 0.35rem !important; text-align: center !important; }}
      .cmb-kpi-num {{ font-size: 1.02rem !important; }}
      .cmb-kpi-lbl {{ font-size: 0.5rem !important; letter-spacing: 0.02em !important; }}
      .cmb-archive-zoom {{ display: none !important; }}
      #storia-archive-duo {{ display: block !important; }}
      #storia-archive-duo .cmb-archive-card {{ display: none !important; min-height: 184px !important; height: 184px !important; width: 100% !important; border-radius: 12px !important; }}
      #storia-archive-duo .cmb-archive-card.is-active-slide {{ display: flex !important; }}
      .cmb-archive-caption {{ padding: 1.2rem 0.82rem 0.72rem !important; }}
      .cmb-archive-caption h4 {{ font-size: 1.06rem !important; line-height: 1.05 !important; }}
      .cmb-archive-caption p {{ display: block !important; font-size: 0.75rem !important; line-height: 1.32 !important; margin-top: 0.14rem !important; }}
      #storia-milestones-grid {{ display: block !important; overflow: visible !important; margin-bottom: 0.48rem !important; padding-bottom: 0 !important; }}
      #storia-milestones-grid .heritage-milestone-card {{ display: none !important; width: 100% !important; max-width: 100% !important; padding: 1rem 1.05rem !important; gap: 0.48rem !important; }}
      #storia-milestones-grid .heritage-milestone-card.is-active-slide {{ display: flex !important; }}
      .club-stepper-bar {{ margin-top: 0 !important; margin-bottom: 1.15rem !important; }}
      .hmc-title {{ font-size: 1.32rem !important; line-height: 1.05 !important; }}
      .hmc-desc {{ font-size: 0.84rem !important; line-height: 1.44 !important; display: block !important; -webkit-line-clamp: unset !important; overflow: visible !important; }}
      .gothia-stage-header {{ gap: 0.65rem !important; padding-bottom: 0.85rem !important; }}
      .gothia-stage-header p {{ font-size: 0.83rem !important; line-height: 1.42 !important; }}
      .gothia-world-pill {{ font-size: 0.6rem !important; padding: 0.35rem 0.55rem !important; width: 100% !important; text-align: center !important; justify-content: center !important; white-space: normal !important; line-height: 1.25 !important; }}
      #gothia-dual-grid {{ display: block !important; overflow: visible !important; margin: 0.85rem 0 0.48rem !important; padding-bottom: 0 !important; }}
      #gothia-dual-grid .gothia-monument-card {{ display: none !important; width: 100% !important; max-width: 100% !important; }}
      #gothia-dual-grid .gothia-monument-card.is-active-slide {{ display: flex !important; }}
      .gothia-monument-visual {{ height: 158px !important; padding: 0.65rem !important; }}
      .gothia-edition-tag {{ display: none !important; }}
      .gothia-country-tag {{ font-size: 0.64rem !important; padding: 0.22rem 0.55rem !important; }}
      .gothia-monument-body {{ padding: 0.92rem 0.98rem !important; gap: 0.55rem !important; }}
      .gothia-monument-title {{ font-size: 1.28rem !important; line-height: 1.04 !important; }}
      .gothia-monument-desc {{ font-size: 0.83rem !important; line-height: 1.42 !important; display: block !important; -webkit-line-clamp: unset !important; overflow: visible !important; }}
      .gothia-kpi-row {{ grid-template-columns: repeat(3, minmax(0, 1fr)) !important; gap: 0.38rem !important; }}
      .gothia-kpi-cell {{ padding: 0.44rem 0.26rem !important; text-align: center !important; }}
      .gothia-kpi-val {{ font-size: 0.92rem !important; }}
      .gothia-kpi-lbl {{ font-size: 0.52rem !important; }}
      #subpane-club-org .org-stage {{ padding: 0.72rem 0.68rem !important; margin-bottom: 0.85rem !important; border-radius: 14px !important; }}
      .org-stage-header {{ margin-bottom: 0.48rem !important; padding-bottom: 0.44rem !important; gap: 0.35rem !important; flex-direction: row !important; align-items: center !important; justify-content: space-between !important; flex-wrap: wrap !important; }}
      .org-stage-header .section-eyebrow {{ display: none !important; }}
      .org-stage-header .section-title {{ font-size: 1.12rem !important; line-height: 1.05 !important; }}
      .org-fed-seal {{ width: auto !important; font-size: 0.52rem !important; padding: 0.22rem 0.44rem !important; gap: 0.3rem !important; }}
      .org-fed-seal img {{ width: 16px !important; height: 20px !important; }}
      .org-tier-label-bar {{ margin: 0.18rem 0 0.34rem !important; }}
      .org-tier-tag {{ white-space: nowrap !important; font-size: 0.52rem !important; line-height: 1.15 !important; letter-spacing: 0.06em !important; padding: 0.18rem 0.52rem !important; width: auto !important; text-align: left !important; }}
      .org-tier-rail {{ display: block !important; opacity: 0.45 !important; }}
      .org-connector-bridge {{ display: flex !important; height: 14px !important; margin: 0.12rem 0 !important; }}
      .org-connector-node {{ width: 7px !important; height: 7px !important; }}
      .org-tier-presidency {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.38rem !important; margin-bottom: 0.2rem !important; }}
      .org-pres-card {{ padding: 0.5rem 0.58rem !important; gap: 0.22rem !important; border-radius: 10px !important; }}
      .org-pres-card .org-card-top {{ margin-bottom: 0 !important; }}
      .org-pres-card .org-card-top > span:last-child {{ display: none !important; }}
      .org-pres-card .org-role-badge {{ font-size: 0.49rem !important; padding: 0.14rem 0.38rem !important; letter-spacing: 0.04em !important; }}
      .org-pres-body {{ flex-direction: row !important; align-items: center !important; gap: 0.42rem !important; }}
      .org-pres-shield, .org-pres-card .org-gold-slash, .org-pres-card .org-exec-desc {{ display: none !important; }}
      .org-pres-card .org-name-stack {{ display: flex !important; flex-direction: row !important; align-items: baseline !important; gap: 0.28rem !important; flex-wrap: wrap !important; }}
      .org-pres-card .org-first-name {{ font-size: 0.68rem !important; margin: 0 !important; }}
      .org-pres-card .org-last-name {{ font-size: 1.18rem !important; line-height: 1 !important; }}
      .org-tier-management {{ grid-template-columns: 1fr !important; gap: 0.3rem !important; margin-bottom: 0.2rem !important; }}
      .org-exec-card {{ display: grid !important; grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr) !important; grid-template-areas: "name top" "name desc" !important; align-items: center !important; column-gap: 0.4rem !important; row-gap: 0.1rem !important; padding: 0.42rem 0.58rem !important; border-radius: 10px !important; }}
      .org-exec-card .org-card-top {{ grid-area: top !important; justify-content: flex-end !important; margin: 0 !important; }}
      .org-exec-card .org-role-badge {{ font-size: 0.48rem !important; padding: 0.12rem 0.36rem !important; letter-spacing: 0.04em !important; }}
      .org-monogram-shield {{ display: none !important; }}
      .org-exec-card .org-name-stack {{ grid-area: name !important; display: flex !important; flex-direction: row !important; align-items: baseline !important; gap: 0.3rem !important; margin: 0 !important; flex-wrap: nowrap !important; }}
      .org-exec-card .org-first-name {{ font-size: 0.7rem !important; margin: 0 !important; }}
      .org-exec-card .org-last-name {{ font-size: 1.08rem !important; line-height: 1 !important; }}
      .org-exec-card .org-gold-slash {{ display: none !important; }}
      .org-exec-card .org-exec-desc {{ grid-area: desc !important; margin: 0 !important; padding: 0 !important; border-top: none !important; font-size: 0.62rem !important; line-height: 1.15 !important; text-align: right !important; color: rgba(255, 255, 255, 0.78) !important; display: block !important; }}
      .org-exec-card .org-exec-desc strong {{ display: none !important; }}
      .org-council-deck {{ padding: 0.52rem 0.58rem !important; border-radius: 11px !important; }}
      .org-council-header {{ margin-bottom: 0.38rem !important; padding-bottom: 0.32rem !important; gap: 0.25rem !important; }}
      .org-council-title {{ font-size: 0.92rem !important; }}
      .org-council-sub {{ display: none !important; }}
      .org-council-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.28rem !important; }}
      .org-councilor-card {{ flex-direction: row !important; align-items: center !important; justify-content: flex-start !important; padding: 0.34rem 0.48rem !important; gap: 0.36rem !important; border-radius: 8px !important; }}
      .org-councilor-top {{ order: 1 !important; margin: 0 !important; flex-shrink: 0 !important; }}
      .org-councilor-role {{ display: none !important; }}
      .org-councilor-avatar {{ width: 20px !important; height: 20px !important; font-size: 0.52rem !important; border-radius: 5px !important; }}
      .org-councilor-card .org-name-stack {{ order: 2 !important; display: flex !important; flex-direction: row !important; align-items: baseline !important; gap: 0.24rem !important; margin: 0 !important; min-width: 0 !important; }}
      .org-councilor-card .org-first-name {{ font-size: 0.64rem !important; margin: 0 !important; }}
      .org-councilor-card .org-last-name {{ font-size: 0.96rem !important; line-height: 1 !important; }}
      .org-councilor-card:last-child {{ grid-column: 1 / -1 !important; justify-content: center !important; }}
      .cuore-lead-banner {{ grid-template-columns: 1fr !important; padding: 0.92rem !important; gap: 0.68rem !important; margin-bottom: 0.85rem !important; }}
      .cuore-emblem-box {{ width: 64px !important; height: 64px !important; border-radius: 14px !important; padding: 5px !important; }}
      .cuore-emblem-svg {{ width: 52px !important; height: 52px !important; }}
      .cuore-emblem-crest {{ width: 18px !important; height: 26px !important; }}
      .cuore-lead-copy h3 {{ font-size: 1.38rem !important; line-height: 1.04 !important; }}
      .cuore-lead-copy p {{ font-size: 0.82rem !important; line-height: 1.42 !important; }}
      .cuore-strada-quote {{ padding: 0.72rem 0.84rem !important; gap: 0.28rem !important; }}
      .csq-text {{ font-size: 0.78rem !important; line-height: 1.4 !important; }}
      #cuore-pillars-grid {{ display: block !important; overflow: visible !important; margin-bottom: 0.48rem !important; padding-bottom: 0 !important; }}
      #cuore-pillars-grid .cuore-pillar-card {{ display: none !important; width: 100% !important; max-width: 100% !important; padding: 0.95rem !important; gap: 0.65rem !important; }}
      #cuore-pillars-grid .cuore-pillar-card.is-active-slide {{ display: flex !important; }}
      .cuore-pillar-head {{ padding-bottom: 0.62rem !important; }}
      .cuore-pillar-title {{ font-size: 1.28rem !important; }}
      .cuore-charity-item {{ font-size: 0.8rem !important; padding: 0.46rem 0.58rem !important; }}
      .sp-header-kit-pill {{ font-size: 0.64rem !important; padding: 0.3rem 0.52rem !important; margin-top: 0.35rem !important; }}
      .season-pass-grid {{ display: grid !important; grid-template-columns: 1fr !important; overflow: visible !important; gap: 0.65rem !important; margin: 0.55rem 0 0.85rem !important; }}
      .season-pass-card {{ flex: none !important; max-width: 100% !important; padding: 0.82rem 0.88rem !important; gap: 0.5rem !important; border-radius: 12px !important; }}
      .season-pass-card > button {{ display: inline-flex !important; align-items: center !important; justify-content: center !important; width: 100% !important; min-height: 36px !important; padding: 0.42rem 0.65rem !important; font-size: 0.72rem !important; border-radius: 8px !important; letter-spacing: 0.03em !important; white-space: nowrap !important; }}
      .sp-badge-row {{ gap: 0.35rem !important; margin-bottom: 0.25rem !important; flex-wrap: nowrap !important; }}
      .sp-tier-tag, .sp-type-lbl {{ font-size: 0.52rem !important; padding: 0.14rem 0.4rem !important; }}
      .sp-title {{ font-size: 1.24rem !important; line-height: 1.04 !important; }}
      .sp-cats-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.32rem !important; }}
      .sp-cat-chip {{ padding: 0.32rem 0.48rem !important; border-radius: 7px !important; }}
      .sp-cat-name {{ font-size: 0.68rem !important; }}
      .sp-cat-age {{ font-size: 0.54rem !important; }}
      .sp-breakdown {{ padding: 0.48rem 0.62rem !important; gap: 0.28rem !important; border-radius: 9px !important; }}
      .sp-bd-row {{ font-size: 0.72rem !important; padding-bottom: 0.24rem !important; }}
      .sp-bd-lbl, .sp-bd-val {{ font-size: 0.7rem !important; white-space: nowrap !important; }}
      .sp-segreteria-strip {{ flex-direction: column !important; align-items: stretch !important; gap: 0.52rem !important; padding: 0.72rem 0.82rem !important; margin: 0 0 0.75rem !important; border-radius: 11px !important; }}
      .sps-eyebrow {{ font-size: 0.54rem !important; letter-spacing: 0.05em !important; }}
      .sps-hours {{ font-size: 0.74rem !important; line-height: 1.3 !important; }}
      .sps-actions {{ display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.42rem !important; width: 100% !important; }}
      .sps-btn {{ width: 100% !important; min-height: 34px !important; padding: 0.38rem 0.48rem !important; font-size: 0.72rem !important; border-radius: 7px !important; }}
      .treasury-top-row .btn-gold-broadcast, .treasury-top-row .btn-ghost-broadcast {{ font-size: 0.7rem !important; padding: 0.36rem 0.4rem !important; border-radius: 6px !important; min-height: 31px !important; }}
      .treasury-rules-grid {{ grid-template-columns: 1fr !important; gap: 0.36rem !important; }}
      .portal-desk-grid {{ display: grid !important; grid-template-columns: 1fr !important; overflow: visible !important; gap: 0.5rem !important; margin-bottom: 0.85rem !important; }}
      .portal-desk-card {{ flex: none !important; max-width: 100% !important; padding: 0.72rem 0.82rem !important; gap: 0.42rem !important; }}
      .pdc-actions a {{ padding: 0.34rem 0.45rem !important; font-size: 0.7rem !important; border-radius: 6px !important; min-height: 30px !important; }}
      .safeguarding-grid {{ grid-template-columns: 1fr !important; gap: 0.55rem !important; }}
      .safe-doc-row {{ display: grid !important; grid-template-columns: minmax(0, 1fr) auto !important; align-items: center !important; padding: 0.54rem 0.68rem !important; gap: 0.45rem !important; }}
      .safe-doc-row a {{ width: auto !important; padding: 0.32rem 0.56rem !important; font-size: 0.68rem !important; border-radius: 6px !important; min-height: 28px !important; }}
      #stadium-arenas-grid {{ display: block !important; overflow: visible !important; margin-bottom: 0.42rem !important; }}
      #stadium-arenas-grid .stadium-arena-card {{ display: none !important; width: 100% !important; max-width: 100% !important; }}
      #stadium-arenas-grid .stadium-arena-card.is-active-slide {{ display: flex !important; }}
      .sac-actions-bar button, .sac-actions-bar a {{ font-size: 0.7rem !important; padding: 0.36rem 0.38rem !important; border-radius: 6px !important; min-height: 30px !important; }}
      .contact-command-stage {{ display: flex !important; flex-direction: column-reverse !important; gap: 0.75rem !important; }}
      .switchboard-card {{ padding: 0.6rem 0.74rem !important; gap: 0.45rem !important; }}
      .swc-cta-btn {{ padding: 0.3rem 0.58rem !important; font-size: 0.68rem !important; border-radius: 6px !important; min-height: 28px !important; }}
      .concierge-submit-row {{ display: grid !important; grid-template-columns: 1fr !important; gap: 0.4rem !important; }}
      .concierge-submit-row .btn-gold-broadcast, .concierge-submit-row .btn-ghost-broadcast {{ font-size: 0.72rem !important; padding: 0.38rem 0.45rem !important; border-radius: 6px !important; min-height: 32px !important; }}
      .container {{ padding: 0 0.9rem !important; }}
    }}
  </style>
</head>
<body>
  <div id="viewport-stage">

    <!-- TOP INSTITUTIONAL MICRO-BAR (SERIE A CLEAN STYLE) -->
    <div class="top-Broadcast-ribbon">
      <div class="top-ribbon-inner">
        <div class="ribbon-left">
          <span style="color:var(--acos-yellow);font-weight:800;">SCUOLA CALCIO <span class="ribbon-only-desktop">RICONOSCIUTA </span>F.I.G.C.</span>
          <span class="ribbon-dot">•</span>
          <span>PARTNER TECNICO ATALANTA B.C.</span>
        </div>
        <div class="ribbon-right">
          <span>Treviglio (BG)</span>
          <span class="ribbon-dot">•</span>
          <a href="tel:0363304036" class="ribbon-link">0363 304036</a>
          <span class="ribbon-dot">•</span>
          <a href="mailto:info@acos.it" class="ribbon-link">info@acos.it</a>
        </div>
      </div>
    </div>

    <!-- MAIN SERIE A CLUB HEADER CON STEMMA OVALE UFFICIALE A.C.O.S. -->
    <header class="site-header">
      <div class="header-inner">
        <div class="club-brand" onclick="switchPage('page-home')" role="button" tabindex="0" aria-label="Home A.C.O.S. Treviglio Calcio 1971">
          {render_crest_badge('crest-header')}
          <div class="club-brand-text">
            <div class="club-brand-title">A.C.O.S. <span>TREVIGLIO</span></div>
            <div class="club-brand-sub">FONDATA NEL 1971 • TREVIGLIO</div>
          </div>
        </div>

        <nav class="main-nav" aria-label="Navigazione Principale Club">
          <button type="button" class="nav-btn active" data-target="page-home" onclick="switchPage('page-home')">Home</button>
          <button type="button" class="nav-btn" data-target="page-squadre" onclick="switchPage('page-squadre')">Squadre</button>
          <button type="button" class="nav-btn" data-target="page-club" onclick="switchPage('page-club')">Il Club</button>
          <button type="button" class="nav-btn" data-target="page-contatti" onclick="switchPage('page-contatti')">Info &amp; Sede</button>
        </nav>

        <div class="header-actions">
          <button type="button" class="btn-gold-broadcast" onclick="switchPage('page-contatti', 'info-contatti')">
            Entra nel Club →
          </button>
          <button type="button" class="mobile-burger" onclick="toggleMobileDrawer()" aria-label="Apri menu di navigazione">
            ☰
          </button>
        </div>
      </div>
    </header>

    <!-- ========================================================================
         PAGE 1: HOME — ARCHITETTURA TOP-LEVEL IN 3 ATTI (ZERO RIDONDANZE, ZERO MICRO-BOX)
         ======================================================================== -->
    <main id="page-home" class="page-view active">

      <!-- ATTO I: FULL-BLEED CINEMATIC STADIUM HERO -->
      <section class="stadium-hero" id="stadium-hero-stage">
        <div class="hero-slides-backdrop">
          <div class="hero-slide-bg active" id="hero-bg-0" style="background-image:url('{asset('assets/gothia_2015.jpg')}');"></div>
          <div class="hero-slide-bg" id="hero-bg-1" style="background-image:url('{asset('assets/event_239.jpg')}');"></div>
          <div class="hero-slide-bg" id="hero-bg-2" style="background-image:url('{asset('assets/vigano_3.jpg')}');"></div>
        </div>
        <div class="hero-cinematic-veil"></div>
        <div class="hero-floodlight-beams"></div>
        <div class="hero-kinetic-watermark">ACOS 1971</div>

        <div class="container">
          <div class="hero-stage-grid">
            <div>
              <div class="hero-identity-row">
                <span class="hero-season-pill">Stagione Sportiva 2025/2026</span>
              </div>

              <h1 class="hero-monumental-h1">
                <span class="hollow-line">OLTRE MEZZO SECOLO</span>
                <span class="stroke-line">DI PASSIONE CALCISTICA.</span>
                <span class="gold-line">CUORE GIALLONERO.</span>
              </h1>

              <p class="hero-lead-copy">
                Dal vivaio giovanile agonistico e di base fino alla <strong>Prima Squadra</strong>: il punto di riferimento del calcio a Treviglio, tra crescita tecnica, valori sportivi e palcoscenici internazionali.
              </p>

              <div class="hero-cta-row">
                <button type="button" class="hero-deck-btn primary" onclick="switchPage('page-squadre', 'sq-organico')">
                  <span>Esplora le 15 Squadre</span>
                  <span class="hero-deck-arrow">→</span>
                </button>
                <button type="button" class="hero-deck-btn secondary" onclick="switchPage('page-contatti', 'info-quote')">
                  <span>Iscrizioni &amp; Segreteria</span>
                  <span class="hero-deck-arrow">→</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- FASCIA CREDENZIALI ISTITUZIONALI (PURA TIPOGRAFIA, NON CLICCABILE) -->
        <div class="hero-lower-third">
          <div class="hero-lower-inner">
            <div class="hero-telemetry-strip">
              <div class="hero-telemetry-item">
                <div class="telemetry-copy">
                  <span class="telemetry-val">18 Ago 1971</span>
                  <span class="telemetry-lbl">Fondazione Storica a Treviglio</span>
                </div>
              </div>
              <div class="hero-telemetry-item">
                <div class="telemetry-copy">
                  <span class="telemetry-val">15 Squadre F.I.G.C.</span>
                  <span class="telemetry-lbl">Dalla Promozione ai Piccoli Amici</span>
                </div>
              </div>
              <div class="hero-telemetry-item">
                <div class="telemetry-copy">
                  <span class="telemetry-val">Atalanta B.C.</span>
                  <span class="telemetry-lbl">Partnership Tecnica Vivaio</span>
                </div>
              </div>
              <div class="hero-telemetry-item">
                <div class="telemetry-copy">
                  <span class="telemetry-val">27 Gothia Cup</span>
                  <span class="telemetry-lbl">26 in Svezia + 1 in Cina</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ATTO II: IL CAMPO GIALLONERO (3 POSTER EDITORIALI DIRETTI — ZERO TAB RIDONDANTI) -->
      <section id="home-sectors-section" class="section-block">
        <div class="container">
          <div class="section-header">
            <div>
              <span class="section-eyebrow">Filiera Sportiva Completa · Stagione 2025/2026</span>
              <h2 class="section-title">Dalla Scuola Calcio alla Prima Squadra</h2>
            </div>
          </div>

          <div class="home-sectors-grid">
            <!-- Poster 1: Prima Squadra & Settore Agonistico -->
            <article class="home-sector-poster" onclick="jumpToRosterMacro('agonistica')" role="button" tabindex="0">
              <div class="hsp-bg" style="background-image:url('{asset('assets/event_239.jpg')}');"></div>
              <div class="hsp-veil"></div>
              <div class="hsp-content">
                <span class="hsp-eyebrow">Promozione L.N.D., U19 Élite, Allievi &amp; Giovanissimi</span>
                <h3 class="hsp-title">Prima Squadra &amp; Agonistica</h3>
                <p class="hsp-desc">
                  Il vertice sportivo allo Stadio Mario Zanconti e i campionati F.I.G.C. a 11 giocatori con tecnici UEFA e spedizioni internazionali.
                </p>
                <span class="hsp-link">Esplora il Settore Agonistico <span>→</span></span>
              </div>
            </article>

            <!-- Poster 2: Attività di Base F.I.G.C. (Esordienti & Pulcini) -->
            <article class="home-sector-poster" onclick="jumpToRosterMacro('base')" role="button" tabindex="0">
              <div class="hsp-bg" style="background-image:url('{asset('assets/gothia_2024_3.jpg')}');"></div>
              <div class="hsp-veil"></div>
              <div class="hsp-content">
                <span class="hsp-eyebrow">Esordienti U13/U12 &amp; Pulcini U11/U10 · 9–13 Anni</span>
                <h3 class="hsp-title">Attività di Base F.I.G.C.</h3>
                <p class="hsp-desc">
                  Sviluppo tecnico a 9 e a 7 giocatori al Centro Sportivo Ambrogio Mazza, con metodo condiviso Atalanta B.C. e tornei ufficiali.
                </p>
                <span class="hsp-link">Esplora l'Attività di Base <span>→</span></span>
              </div>
            </article>

            <!-- Poster 3: Scuola Calcio Riconosciuta F.I.G.C. -->
            <article class="home-sector-poster" onclick="switchPage('page-squadre', 'sq-scuola')" role="button" tabindex="0">
              <div class="hsp-bg" style="background-image:url('{asset('assets/vigano_3.jpg')}');"></div>
              <div class="hsp-veil"></div>
              <div class="hsp-content">
                <span class="hsp-eyebrow">5–8 Anni · Partner Tecnico Atalanta B.C.</span>
                <h3 class="hsp-title">Scuola Calcio F.I.G.C.</h3>
                <p class="hsp-desc">
                  Primi Calci e Piccoli Amici: crescita motoria, prevenzione posturale Vitalis e Torneo Primaverile Stefano Viganò.
                </p>
                <span class="hsp-link">Scopri la Scuola Calcio <span>→</span></span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <!-- ATTO III: IDENTITÀ INTERNAZIONALE & VALORI (1 UNICO FEATURE EDITORIALE WIDESCREEN) -->
      <section id="home-heritage-section" class="section-block" style="background:var(--bg-stadium);">
        <div class="container">
          <article class="home-heritage-showcase">
            <div class="hhs-visual" style="background-image:url('{asset('assets/gothia_2015.jpg')}');"></div>
            <div class="hhs-body">
              <span class="section-eyebrow" style="display:block !important;margin:0;">Oltre il Campo · L'Identità A.C.O.S. dal 1971</span>
              <h2 class="hhs-title">
                Da Treviglio all'Europa:<br/><span>Gothia Cup &amp; Cuore Giallonero</span>
              </h2>
              <p class="hhs-copy">
                Unica società italiana invitata alla <strong>Gothia Cup China 2016</strong> e protagonista di <strong>26 spedizioni in Svezia</strong> davanti ai 55.000 spettatori dello Stadio Ullevi, l'A.C.O.S. Treviglio unisce dal 1971 la crescita sportiva all'impegno solidale con <strong>Emergency</strong> e il <strong>25° Memorial</strong>.
              </p>
              <button type="button" class="btn-gold-broadcast" onclick="switchPage('page-club', 'club-storia')" style="margin-top:0.35rem;">
                Scopri la Storia e i Valori del Club →
              </button>
            </div>
          </article>
        </div>
      </section>
    </main>

    <!-- ========================================================================
         PAGE 2: SQUADRE, SCUOLA CALCIO FIGC & TORNEO VIGANÒ (3 SOTTO-VISTE IDENTICHE)
         ======================================================================== -->
    <section id="page-squadre" class="page-view">
      <!-- BARRA DI SOTTO-NAVIGAZIONE UNIFICATA A 3 COLONNE (IDENTICA SU TUTTE LE PAGINE) -->
      <div class="acos-subnav-wrap">
        <div class="container">
          <div class="acos-subnav-bar" role="tablist" aria-label="Sotto-sezioni Squadre e Vivaio">
            <button type="button" class="acos-subnav-pill active" data-sub-group="squadre" data-subpane="sq-organico" onclick="switchSubPane('squadre', 'sq-organico', this)">
              <span class="subnav-idx">01</span>
              <span class="subnav-lbl">Le 15 Squadre</span>
            </button>
            <button type="button" class="acos-subnav-pill" data-sub-group="squadre" data-subpane="sq-scuola" onclick="switchSubPane('squadre', 'sq-scuola', this)">
              <span class="subnav-idx">02</span>
              <span class="subnav-lbl">Scuola Calcio</span>
            </button>
            <button type="button" class="acos-subnav-pill" data-sub-group="squadre" data-subpane="sq-torneo" onclick="switchSubPane('squadre', 'sq-torneo', this)">
              <span class="subnav-idx">03</span>
              <span class="subnav-lbl">Torneo Vigan&ograve;</span>
            </button>
          </div>
        </div>
      </div>

      <div class="section-block">
        <div class="container">

          <!-- SOTTO-VISTA 1: LE 15 SQUADRE GIALLONERE -->
          <div id="subpane-sq-organico" class="subpane-view active" data-sub-group="squadre">
            <div class="section-header">
              <div>
                <span class="section-eyebrow">Organico Ufficiale Stagione Sportiva 2025/2026 · 4 Settori · 15 Categorie</span>
                <h2 class="section-title">L'Organico Giallonero</h2>
                <p style="color:var(--text-silver);max-width:68ch;margin-top:0.35rem;">
                  Dalla <strong>Prima Squadra in Promozione</strong> e la <strong>Juniores U19 Élite</strong> fino al <strong>Settore Giovanile e Scuola Calcio</strong>: tocca una squadra per scheda tecnica, campo e contatto diretto.
                </p>
              </div>
              <button type="button" class="btn-gold-broadcast" onclick="switchPage('page-contatti', 'info-quote')">
                📋 Iscrizioni &amp; IBAN →
              </button>
            </div>

            <div class="filter-chips-row">
              <button type="button" class="filter-chip active" onclick="filterRoster('all', this)"><span class="fc-desktop">Tutti i 4 Settori (15 Squadre)</span><span class="fc-mobile">Tutti (15)</span></button>
              <button type="button" class="filter-chip" onclick="filterRoster('agonistica', this)"><span class="fc-desktop">Prima Squadra &amp; Agonistica (U19–U14)</span><span class="fc-mobile">Agonistica</span></button>
              <button type="button" class="filter-chip" onclick="filterRoster('base', this)"><span class="fc-desktop">Attività di Base FIGC (2013–2016)</span><span class="fc-mobile">Base FIGC</span></button>
              <button type="button" class="filter-chip" onclick="filterRoster('scuola', this)"><span class="fc-desktop">Scuola Calcio &amp; Piccoli Amici (2017–2020)</span><span class="fc-mobile">Scuola</span></button>
            </div>

            <div id="roster-cards-container" class="sector-bands-stack">
              {teams_grid_html}
            </div>
          </div>

          <!-- SOTTO-VISTA 2: SCUOLA CALCIO RICONOSCIUTA FIGC, ATALANTA B.C. & TORNEO VIGANÒ -->
          <div id="subpane-sq-scuola" class="subpane-view" data-sub-group="squadre">

          <!-- ATTO I: MANIFESTO SCUOLA CALCIO RICONOSCIUTA F.I.G.C. & PARTNERSHIP ATALANTA B.C. -->
          <div class="academy-manifesto-stage">
            <div class="academy-manifesto-watermark" aria-hidden="true">ACADEMY 1971</div>
            <div class="academy-manifesto-grid">
              <div style="display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                  <div class="academy-badge-cluster">
                    <span class="academy-official-pill">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2l7 4v6c0 5-3.5 9.5-7 10-3.5-.5-7-5-7-10V6l7-4z"/></svg>
                      SCUOLA CALCIO RICONOSCIUTA F.I.G.C. &bull; S.G.S.
                    </span>
                    <span class="academy-official-pill atalanta-pill">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="9"/><path d="M9 12l2 2 4-4"/></svg>
                      PARTNERSHIP TECNICA ATALANTA B.C.
                    </span>
                    <span class="academy-official-pill">
                      PROGETTO PREVENZIONE VITALIS
                    </span>
                  </div>
                  <h2 class="section-title academy-hero-title" style="font-size:clamp(2.3rem, 4.1vw, 3.45rem);line-height:0.96;margin-bottom:0.85rem;">
                    Dove il Talento Cresce con Metodo, Tutela e Sorriso
                  </h2>
                  <p class="academy-lead-copy" style="font-size:0.95rem;color:var(--text-silver);line-height:1.62;max-width:68ch;">
                    La Scuola Calcio dell&rsquo;<strong style="color:var(--text-white);">A.S.D. A.C.O.S. Treviglio</strong> &egrave; ufficialmente riconosciuta dal <strong style="color:var(--text-white);">Settore Giovanile e Scolastico F.I.G.C.</strong>. Uniamo la formazione tecnica condivisa con gli istruttori del Settore Giovanile di <strong style="color:var(--acos-yellow);">Atalanta Bergamasca Calcio</strong>, la supervisione di laureati in Scienze Motorie e il protocollo posturale <strong style="color:var(--text-white);">Vitalis</strong> per accompagnare ogni bambina e ogni bambino dai 5 ai 12 anni.
                  </p>

                  <!-- 4 KPI TELEMETRICI -->
                  <div class="academy-kpi-strip">
                    <div class="academy-kpi-box">
                      <div class="academy-kpi-num">5 &ndash; 12 Anni</div>
                      <div class="academy-kpi-lbl">4 Fasce FIGC SGS</div>
                    </div>
                    <div class="academy-kpi-box">
                      <div class="academy-kpi-num">Atalanta B.C.</div>
                      <div class="academy-kpi-lbl">Metodo Condiviso</div>
                    </div>
                    <div class="academy-kpi-box">
                      <div class="academy-kpi-num">100% Tecnici</div>
                      <div class="academy-kpi-lbl">Qualificati FIGC</div>
                    </div>
                    <div class="academy-kpi-box">
                      <div class="academy-kpi-num">Centro Mazza</div>
                      <div class="academy-kpi-lbl">Via ai Malgari 6</div>
                    </div>
                  </div>
                </div>

                <!-- CTA BAR DIREZIONE SCUOLA CALCIO -->
                <div class="academy-cta-bar" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.85rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.1);">
                  <div>
                    <div style="font-family:var(--font-mono);font-size:0.62rem;font-weight:800;color:var(--acos-yellow);text-transform:uppercase;letter-spacing:0.08em;">
                      DIREZIONE SCUOLA CALCIO &bull; PROVE GRATUITE &amp; OPEN DAY
                    </div>
                    <div style="font-family:var(--font-sans);font-size:0.98rem;font-weight:800;color:var(--text-white);margin-top:0.15rem;">
                      Resp. Sig. Pierangelo Gusmini (Vice Presidente)
                    </div>
                  </div>
                  <div class="academy-cta-btns" style="display:flex;gap:0.65rem;flex-wrap:wrap;">
                    <button type="button" class="btn-gold-broadcast" onclick="openWhatsAppInfo('Prenotazione Prova Scuola Calcio FIGC (5-12 Anni)')">
                      💬 WhatsApp Scuola Calcio &rarr;
                    </button>
                  </div>
                </div>
              </div>

              <!-- VISUAL SHOWCASE CON SIGILLO UFFICIALE INTEGRATO -->
              <div class="academy-visual-card" onclick="openLightbox('{asset('assets/vigano_3.jpg')}', 'Giovani calciatori gialloneri in campo al Centro Sportivo Ambrogio Mazza (Via ai Malgari 6, Treviglio)')" style="cursor:pointer;">
                <img src="{asset('assets/vigano_3.jpg')}" alt="Scuola Calcio Riconosciuta FIGC ACOS Treviglio" />
                <div class="academy-seal-bar">
                  <div style="display:flex;align-items:center;gap:0.75rem;width:100%;">
                    <img src="{asset('assets/scuola_calcio.jpg')}" alt="Scuola Calcio Riconosciuta FIGC" style="height:40px;width:auto;border-radius:5px;background:#fff;padding:2px 6px;object-fit:contain;flex-shrink:0;" />
                    <div style="min-width:0;">
                      <div style="font-family:var(--font-mono);font-size:0.62rem;font-weight:800;color:var(--acos-yellow);text-transform:uppercase;letter-spacing:0.06em;white-space:nowrap;">AFFILIAZIONE UFFICIALE</div>
                      <div style="font-family:var(--font-sans);font-size:0.88rem;font-weight:800;color:var(--text-white);white-space:nowrap;">Matricola F.I.G.C. 676164</div>
                    </div>
                  </div>
                </div>
                <div class="academy-visual-overlay">
                  <span style="font-family:var(--font-mono);font-size:0.62rem;font-weight:800;color:var(--acos-yellow);text-transform:uppercase;letter-spacing:0.08em;">
                    CENTRO SPORTIVO &ldquo;AMBROGIO MAZZA&rdquo; &bull; CAMPO CENTRALE ENZO RIGANTI
                  </span>
                  <div style="font-family:var(--font-sans);font-size:1.05rem;font-weight:800;color:var(--text-white);margin-top:0.2rem;">
                    Crescita motoria, coordinativa e relazionale in un impianto protetto e dedicato al vivaio giallonero
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ATTO II: I 4 PILASTRI METODOLOGICI DELLA SCUOLA CALCIO -->
          <div class="section-header" style="margin-bottom:1.25rem;">
            <div>
              <span class="section-eyebrow">Atto II &bull; Standard Qualitativi Certificati F.I.G.C. S.G.S.</span>
              <h3 class="section-title academy-sec-title" style="font-size:clamp(1.85rem, 3vw, 2.5rem);">I 4 Pilastri del Metodo Formativo Giallonero</h3>
            </div>
            <button type="button" class="btn-ghost-broadcast" onclick="jumpToRosterMacro('scuola')">
              Esplora Tutte le Annate in Campo &rarr;
            </button>
          </div>

          <div class="academy-pillars-grid" id="academy-pillars-grid">
            <article class="academy-pillar-card is-active-slide" data-slide-label="PILASTRO 1 / 4 • IMPIANTI MAZZA &amp; ZANCONTI">
              <div>
                <span class="academy-pillar-num">01</span>
                <div class="academy-pillar-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="12" y1="4" x2="12" y2="20"/><circle cx="12" cy="12" r="3"/></svg>
                </div>
                <h4 class="academy-pillar-title">Impianti Sportivi d&rsquo;Eccellenza</h4>
                <p class="academy-pillar-desc">
                  Campi in erba naturale e sintetica di ultima generazione al Centro Sportivo &ldquo;Ambrogio Mazza&rdquo; (Via ai Malgari 6) e allo Stadio Comunale &ldquo;Mario Zanconti&rdquo;, con spogliatoi dedicati per fascia d&rsquo;et&agrave;.
                </p>
              </div>
              <div class="academy-pillar-meta">2 STADI &bull; ERBA NATURALE &amp; SINTETICA</div>
            </article>

            <article class="academy-pillar-card" data-slide-label="PILASTRO 2 / 4 • TECNICI QUALIFICATI FIGC">
              <div>
                <span class="academy-pillar-num">02</span>
                <div class="academy-pillar-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                </div>
                <h4 class="academy-pillar-title">Rapporto Istruttori / Allievi</h4>
                <p class="academy-pillar-desc">
                  Ogni gruppo squadra &egrave; affidato a tecnici abilitati dal Settore Tecnico F.I.G.C. e a laureati in Scienze Motorie, garantendo attenzione individuale al ritmo di apprendimento di ciascun bambino.
                </p>
              </div>
              <div class="academy-pillar-meta">TECNICI UEFA / FIGC &bull; SCIENZE MOTORIE</div>
            </article>

            <article class="academy-pillar-card" data-slide-label="PILASTRO 3 / 4 • PARTNERSHIP ATALANTA B.C.">
              <div>
                <span class="academy-pillar-num">03</span>
                <div class="academy-pillar-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                </div>
                <h4 class="academy-pillar-title">Partnership Atalanta B.C.</h4>
                <p class="academy-pillar-desc">
                  Programma di formazione permanente e incontri periodici sul campo tenuti dagli istruttori del Settore Giovanile dell&rsquo;Atalanta Bergamasca Calcio a beneficio di tutti gli allenatori gialloneri.
                </p>
              </div>
              <div class="academy-pillar-meta">METODO ZINGONIA &bull; CLINIC TECNICI</div>
            </article>

            <article class="academy-pillar-card" data-slide-label="PILASTRO 4 / 4 • PREVENZIONE VITALIS">
              <div>
                <span class="academy-pillar-num">04</span>
                <div class="academy-pillar-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                </div>
                <h4 class="academy-pillar-title">Prevenzione Posturale Vitalis</h4>
                <p class="academy-pillar-desc">
                  Protocolli motori e posturali studiati in collaborazione con gli specialisti del centro Vitalis per armonizzare lo sviluppo muscolo-scheletrico e prevenire gli infortuni dell&rsquo;et&agrave; evolutiva.
                </p>
              </div>
              <div class="academy-pillar-meta">TUTELA MOTORIA &bull; SCREENING BASE</div>
            </article>
          </div>
          <div class="vigano-slider-bar vigano-mobile-only club-stepper-bar" aria-label="Sfoglia i 4 pilastri del metodo formativo">
            <button type="button" class="vigano-slider-arrow" onclick="stepMobileClubSlide('academy-pillars-grid', '.academy-pillar-card', 'academy-pillar-label', 'academy-pillar-dots', -1)" aria-label="Pilastro precedente">←</button>
            <div class="vigano-slider-status">
              <span id="academy-pillar-label">PILASTRO 1 / 4 • IMPIANTI MAZZA &amp; ZANCONTI</span>
              <div class="vigano-slider-dots" id="academy-pillar-dots">
                <span class="v-dot active"></span>
                <span class="v-dot"></span>
                <span class="v-dot"></span>
                <span class="v-dot"></span>
              </div>
            </div>
            <button type="button" class="vigano-slider-arrow is-next" onclick="stepMobileClubSlide('academy-pillars-grid', '.academy-pillar-card', 'academy-pillar-label', 'academy-pillar-dots', 1)" aria-label="Pilastro successivo">→</button>
          </div>

          <!-- ATTO III: CARTA DEI DIRITTI DEI BAMBINI (ONU / FIGC) & DECALOGO UEFA -->
          <div class="uefa-charter-stage">
            <div class="section-header" style="margin-bottom:0.4rem;">
              <div>
                <span class="section-eyebrow">Atto III &bull; Codice Etico del Settore Giovanile e Scolastico F.I.G.C. &amp; UEFA</span>
                <h3 class="academy-sec-title" style="font-family:var(--font-display);font-size:clamp(1.75rem, 2.8vw, 2.35rem);font-weight:900;text-transform:uppercase;line-height:1;">
                  Carta dei Diritti dei Bambini &amp; Decalogo del Fair Play
                </h3>
              </div>
              <span class="academy-official-pill">TUTELA SAFEGUARDING ATTIVA</span>
            </div>
            <p style="font-size:0.88rem;color:var(--text-silver);max-width:82ch;">
              All&rsquo;A.C.O.S. Treviglio il risultato numerico non prevarica mai la crescita umana: adottiamo la Carta dei Diritti dei Ragazzi allo Sport (F.I.G.C. S.G.S.) e il Decalogo UEFA per atleti, tecnici e famiglie.
            </p>

            <div class="uefa-charter-grid" id="uefa-charter-grid">
              <div class="uefa-right-card is-active-slide" data-slide-label="CARTA 1 / 3 • DIRITTO AL GIOCO ONU / FIGC">
                <div class="uefa-right-top"><span>01 &bull; CARTA ONU / FIGC</span><span>DIRITTO AL GIOCO</span></div>
                <div class="uefa-right-title">Divertimento e pari opportunit&agrave;</div>
                <p class="uefa-right-desc">Il calcio giovanile &egrave; gioia, scoperta motoria e pari dignit&agrave; per ogni iscritto, nel pieno rispetto dei tempi individuali di crescita.</p>
              </div>
              <div class="uefa-right-card" data-slide-label="CARTA 2 / 3 • TUTELA &amp; SAFEGUARDING">
                <div class="uefa-right-top"><span>02 &bull; TUTELA &amp; METODO</span><span>COMPETENZA</span></div>
                <div class="uefa-right-title">Istruttori qualificati ed equilibrio</div>
                <p class="uefa-right-desc">Ambiente sano e protetto guidato da formatori F.I.G.C. e Atalanta B.C., in armonia tra studio, sport e presidio Safeguarding.</p>
              </div>
              <div class="uefa-right-card" data-slide-label="CARTA 3 / 3 • DECALOGO UEFA &amp; FAIR PLAY">
                <div class="uefa-right-top"><span>03 &bull; DECALOGO UEFA</span><span>TRIBUNA POSITIVA</span></div>
                <div class="uefa-right-title">Rispetto di arbitri, avversari e campo</div>
                <p class="uefa-right-desc">L&rsquo;avversario &egrave; un compagno di gioco e sugli spalti del Centro Mazza le famiglie sostengono i ragazzi con il Fair Play.</p>
              </div>
            </div>
            <div class="vigano-slider-bar vigano-mobile-only" style="margin-top:0.48rem;" aria-label="Sfoglia i 3 principi della Carta dei Diritti e Fair Play">
              <button type="button" class="vigano-slider-arrow" onclick="stepMobileClubSlide('uefa-charter-grid', '.uefa-right-card', 'uefa-charter-label', 'uefa-charter-dots', -1)" aria-label="Principio precedente">←</button>
              <div class="vigano-slider-status">
                <span id="uefa-charter-label">CARTA 1 / 3 • DIRITTO AL GIOCO ONU / FIGC</span>
                <div class="vigano-slider-dots" id="uefa-charter-dots">
                  <span class="v-dot active"></span>
                  <span class="v-dot"></span>
                  <span class="v-dot"></span>
                </div>
              </div>
              <button type="button" class="vigano-slider-arrow is-next" onclick="stepMobileClubSlide('uefa-charter-grid', '.uefa-right-card', 'uefa-charter-label', 'uefa-charter-dots', 1)" aria-label="Principio successivo">→</button>
            </div>
          </div>
          </div><!-- /#subpane-sq-scuola -->

          <!-- SOTTO-VISTA 3: TORNEO STEFANO VIGANÒ – MEMORIAL ENZO RIGANTI -->
          <div id="subpane-sq-torneo" class="subpane-view" data-sub-group="squadre">
          <div class="vigano-monument-stage" style="margin-top:0;">
            <div class="section-header" style="margin-bottom:0.6rem;">
              <div>
                <div class="vigano-mobile-only vigano-top-badges">
                  <span class="academy-gold-badge">RASSEGNA PRIMAVERILE DAL 2010</span>
                  <span class="academy-dark-badge">PULCINI F.I.G.C.</span>
                </div>
                <span class="section-eyebrow">Rassegna Giovanile Primaverile dal 2010 &bull; Categoria Pulcini</span>
                <h2 class="section-title academy-hero-title" style="font-size:clamp(2rem, 3.4vw, 2.9rem);">
                  Torneo &ldquo;Stefano Vigan&ograve;&rdquo; <span class="vigano-title-dot">&bull;</span> <span class="vigano-title-memorial">Memorial Enzo Riganti</span>
                </h2>
              </div>
              <button type="button" class="btn-gold-broadcast" onclick="switchPage('page-contatti', 'info-contatti');selectContactProfile('societa', null);">
                Iscrivi la Tua Societ&agrave; al Torneo &rarr;
              </button>
            </div>

            <p class="vigano-lead-copy" style="color:var(--text-silver);font-size:0.94rem;line-height:1.62;max-width:88ch;">
              Nato nella primavera del <strong style="color:var(--text-white);">2010</strong> per custodire l&rsquo;entusiasmo e il sorriso del giovane Presidente <strong style="color:var(--acos-yellow);">Stefano Vigan&ograve;</strong> e intitolato alla memoria del co-fondatore <strong style="color:var(--text-white);">Enzo Riganti</strong>, il torneo richiama ogni anno a Treviglio le migliori Scuole Calcio lombarde.
            </p>

            <!-- PATROCINI UFFICIALI (DARK-GOLD INSTITUTIONAL BAR) -->
            <div class="vigano-patronage-bar">
              <div class="vigano-patron-Main">
                <img src="{asset('assets/vigano_patrocinio.jpg')}" alt="Con il Patrocinio della Città di Treviglio" class="vigano-patron-crest" />
                <div>
                  <div style="font-family:var(--font-mono);font-size:0.62rem;font-weight:800;color:var(--acos-yellow);text-transform:uppercase;letter-spacing:0.08em;">
                    MANIFESTAZIONE UFFICIALE PATROCINATA
                  </div>
                  <div style="font-family:var(--font-sans);font-size:0.9rem;font-weight:800;color:var(--text-white);">
                    Citt&agrave; di Treviglio &bull; Settore Giovanile e Scolastico F.I.G.C.
                  </div>
                </div>
              </div>
              <div class="vigano-patron-pills">
                <span class="vigano-patron-pill">DAL 2010 &bull; CAMPO CENTRALE ENZO RIGANTI</span>
              </div>
            </div>

            <!-- GALLERIA FOTOGRAFICA HD (3 CARD SU PC, SLIDER 1-FOTO CON FRECCE SU MOBILE, ZERO OVERLAY ZOOM) -->
            <div class="photo-gallery-grid" id="vigano-gallery-grid">
              <div class="gallery-thumb is-active-slide" data-slide-label="FOTO 1 / 3 &bull; Spirito del Torneo" onclick="openLightbox(this.querySelector('img').src, 'Torneo Stefano Viganò – Memorial Enzo Riganti al Centro Sportivo Ambrogio Mazza')">
                <img src="{asset('assets/vigano_1.jpg')}" alt="Torneo Stefano Viganò foto 1" loading="lazy" />
              </div>
              <div class="gallery-thumb" data-slide-label="FOTO 2 / 3 &bull; Campo Enzo Riganti" onclick="openLightbox(this.querySelector('img').src, 'Sfilata e premiazioni sul Campo Centrale Enzo Riganti — Torneo Stefano Viganò')">
                <img src="{asset('assets/vigano_2.jpg')}" alt="Torneo Stefano Viganò foto 2" loading="lazy" />
              </div>
              <div class="gallery-thumb" data-slide-label="FOTO 3 / 3 &bull; Pulcini in Campo" onclick="openLightbox(this.querySelector('img').src, 'I Pulcini gialloneri in azione al Torneo Primaverile Stefano Viganò')">
                <img src="{asset('assets/vigano_3.jpg')}" alt="Torneo Stefano Viganò foto 3" loading="lazy" />
              </div>
            </div>

            <!-- CONTROLLI FRECCIA SLIDER FOTO (SOLO MOBILE, PER COMPATTARE LA PAGINA) -->
            <div class="vigano-mobile-only vigano-slider-bar">
              <button type="button" class="vigano-slider-arrow" onclick="stepViganoPhoto(-1)" aria-label="Foto precedente">&larr;</button>
              <div class="vigano-slider-status">
                <span id="vigano-slide-label">FOTO 1 / 3 &bull; Spirito del Torneo</span>
                <div class="vigano-slider-dots" id="vigano-slider-dots">
                  <span class="v-dot active"></span>
                  <span class="v-dot"></span>
                  <span class="v-dot"></span>
                </div>
              </div>
              <button type="button" class="vigano-slider-arrow is-next" onclick="stepViganoPhoto(1)" aria-label="Foto successiva">&rarr;</button>
            </div>

            <!-- CTA BAR MOBILE TORNEO VIGANÒ (NASCOSTA SU PC, GRIGLIA 50%+50% SU SMARTPHONE) -->
            <div class="vigano-mobile-cta-row">
              <button type="button" class="btn-gold-broadcast" onclick="switchPage('page-contatti', 'info-contatti');selectContactProfile('societa', null);">
                Iscrivi Societ&agrave; &rarr;
              </button>
              <button type="button" class="btn-ghost-broadcast" onclick="openWhatsAppInfo('Iscrizione / Informazioni Torneo Stefano Viganò')">
                Info su WhatsApp &rarr;
              </button>
            </div>
          </div>
          </div><!-- /#subpane-sq-torneo -->

        </div>
      </div>
    </section>

    <!-- ========================================================================
         PAGE 3: IL CLUB (3 SOTTO-VISTE IDENTICHE: ORGANIGRAMMA · STORIA & GOTHIA · CUORE)
         ======================================================================== -->
    <section id="page-club" class="page-view">
      <!-- BARRA DI SOTTO-NAVIGAZIONE UNIFICATA A 3 COLONNE (IDENTICA SU TUTTE LE PAGINE) -->
      <div class="acos-subnav-wrap">
        <div class="container">
          <div class="acos-subnav-bar" role="tablist" aria-label="Sotto-sezioni Il Club">
            <button type="button" class="acos-subnav-pill active" data-sub-group="club" data-subpane="club-org" onclick="switchSubPane('club', 'club-org', this)">
              <span class="subnav-idx">01</span>
              <span class="subnav-lbl">Organigramma</span>
            </button>
            <button type="button" class="acos-subnav-pill" data-sub-group="club" data-subpane="club-storia" onclick="switchSubPane('club', 'club-storia', this)">
              <span class="subnav-idx">02</span>
              <span class="subnav-lbl">Storia &amp; Gothia</span>
            </button>
            <button type="button" class="acos-subnav-pill" data-sub-group="club" data-subpane="club-cuore" onclick="switchSubPane('club', 'club-cuore', this)">
              <span class="subnav-idx">03</span>
              <span class="subnav-lbl">Cuore Giallonero</span>
            </button>
          </div>
        </div>
      </div>

      <div class="section-block">
        <div class="container">

          <!-- SOTTO-VISTA 2: STORIA (1966-2026) & GOTHIA CUP SVEZIA/CINA -->
          <div id="subpane-club-storia" class="subpane-view" data-sub-group="club">
          <!-- ATTO I: MANIFESTO HERITAGE 1971 & ORIZZONTE STORICO ORIZZONTALE -->
          <div class="club-manifesto-banner">
            <div class="club-manifesto-watermark">1971</div>
            <div class="club-manifesto-grid">
              <div class="cmb-copy-col">
                <span class="cmb-eyebrow">★ Heritage Giallonero · Fondata a Treviglio il 18 Agosto 1971</span>
                <h2 class="cmb-title">
                  ASSOCIAZIONE CALCISTICA
                  <span>OPERAI E STUDENTI</span>
                </h2>
                <p class="cmb-lead">
                  Nata dalle radici del <strong>Castel Cerreto (1966)</strong> per visione di <strong>Battista &ldquo;Tista&rdquo; Bugini</strong>, <strong>Enzo Riganti</strong> e <strong>Mario Barbieri</strong>, l&rsquo;A.C.O.S. Treviglio custodisce nel proprio nome l&rsquo;identit&agrave; popolare e formativa che da oltre mezzo secolo unisce le generazioni della Gera d&rsquo;Adda sotto i colori gialloneri.
                </p>
                <div class="cmb-kpi-strip">
                  <div class="cmb-kpi-box">
                    <span class="cmb-kpi-num">1971</span>
                    <span class="cmb-kpi-lbl">Fondazione Club</span>
                  </div>
                  <div class="cmb-kpi-box">
                    <span class="cmb-kpi-num">55+ Anni</span>
                    <span class="cmb-kpi-lbl">Storia del Club</span>
                  </div>
                  <div class="cmb-kpi-box">
                    <span class="cmb-kpi-num">27 Gothia Cup</span>
                    <span class="cmb-kpi-lbl">26 Svezia + 1 Cina</span>
                  </div>
                  <div class="cmb-kpi-box">
                    <span class="cmb-kpi-num">20 Realt&agrave;</span>
                    <span class="cmb-kpi-lbl">Cuore Giallonero</span>
                  </div>
                </div>
              </div>

              <div class="cmb-archive-wrap">
                <div class="cmb-archive-duo" id="storia-archive-duo">
                  <div class="cmb-archive-card is-active-slide" data-slide-label="FOTO 1 / 2 • ARCHIVIO 1971" onclick="openLightbox(this.querySelector('img').src, 'Archivio Storico 1971 — Le prime formazioni di Operai e Studenti sui campi di Treviglio')">
                    <span class="cmb-archive-tag">ARCHIVIO STORICO · 1971</span>
                    <img src="{asset('assets/storia_1.jpg')}" alt="Origini Storiche A.C.O.S. Treviglio 1971" />
                    <div class="cmb-archive-caption">
                      <h4>Origini: Operai e Studenti</h4>
                      <p>Le prime rose giallonere nate tra volontariato, amicizia e talento.</p>
                    </div>
                  </div>
                  <div class="cmb-archive-card" data-slide-label="FOTO 2 / 2 • TRADIZIONE GIALLONERA" onclick="openLightbox(this.querySelector('img').src, 'Tradizione Giallonera — Dai tornei storici del Bar Milano alla Promozione regionale')">
                    <span class="cmb-archive-tag">TRADIZIONE TREVIGLIESE</span>
                    <img src="{asset('assets/storia_2.jpg')}" alt="Tradizione Storica A.C.O.S. Treviglio" />
                    <div class="cmb-archive-caption">
                      <h4>55 Anni di Maglia Giallonera</h4>
                      <p>Dal Torneo Notturno del Bar Milano ai campionati L.N.D. Lombardia.</p>
                    </div>
                  </div>
                </div>
                <div class="vigano-slider-bar vigano-mobile-only" aria-label="Sfoglia foto storiche A.C.O.S. 1971">
                  <button type="button" class="vigano-slider-arrow" onclick="stepMobileClubSlide('storia-archive-duo', '.cmb-archive-card', 'storia-photo-label', 'storia-photo-dots', -1)" aria-label="Foto precedente">←</button>
                  <div class="vigano-slider-status">
                    <span id="storia-photo-label">FOTO 1 / 2 • ARCHIVIO 1971</span>
                    <div class="vigano-slider-dots" id="storia-photo-dots">
                      <span class="v-dot active"></span>
                      <span class="v-dot"></span>
                    </div>
                  </div>
                  <button type="button" class="vigano-slider-arrow is-next" onclick="stepMobileClubSlide('storia-archive-duo', '.cmb-archive-card', 'storia-photo-label', 'storia-photo-dots', 1)" aria-label="Foto successiva">→</button>
                </div>
              </div>
            </div>
          </div>

          <div class="section-header" style="margin-bottom:1.25rem;">
            <div>
              <span class="section-eyebrow">Cronologia Ufficiale · 6 Tappe Fondamentali (1966 – 2026)</span>
              <h3 class="section-title" style="font-size:clamp(1.5rem, 2.5vw, 2.1rem);">Le Pietre Miliari della Nostra Storia</h3>
            </div>
          </div>

          <div class="heritage-milestone-grid" id="storia-milestones-grid">
            {timeline_html}
          </div>
          <div class="vigano-slider-bar vigano-mobile-only club-stepper-bar" aria-label="Sfoglia le 6 tappe storiche">
            <button type="button" class="vigano-slider-arrow" onclick="stepMobileClubSlide('storia-milestones-grid', '.heritage-milestone-card', 'storia-milestone-label', 'storia-milestone-dots', -1)" aria-label="Tappa precedente">←</button>
            <div class="vigano-slider-status">
              <span id="storia-milestone-label">TAPPA 1 / 6 • 1966 – 1970</span>
              <div class="vigano-slider-dots" id="storia-milestone-dots">
                <span class="v-dot active"></span>
                <span class="v-dot"></span>
                <span class="v-dot"></span>
                <span class="v-dot"></span>
                <span class="v-dot"></span>
                <span class="v-dot"></span>
              </div>
            </div>
            <button type="button" class="vigano-slider-arrow is-next" onclick="stepMobileClubSlide('storia-milestones-grid', '.heritage-milestone-card', 'storia-milestone-label', 'storia-milestone-dots', 1)" aria-label="Tappa successiva">→</button>
          </div>

          <!-- ATTO II: PALCOSCENICO INTERNAZIONALE GOTHIA CUP (SVEZIA & CINA) -->
          <div class="gothia-arena-stage">
            <div class="gothia-stage-watermark">WORLD YOUTH CUP</div>

            <div class="gothia-stage-header">
              <div>
                <span class="section-eyebrow">Palcoscenico Internazionale · Ambasciatori di Treviglio nel Mondo dal 1989</span>
                <h2 class="section-title" style="margin-bottom:0.35rem;">Gothia Cup · Svezia &amp; Cina</h2>
                <p style="color:var(--text-silver);font-size:0.95rem;max-width:78ch;margin:0;">
                  Pochissime societ&agrave; dilettantistiche in Italia vantano una tradizione internazionale paragonabile a quella giallonera: un&rsquo;esperienza di vita e di sport che porta i nostri ragazzi a confrontarsi con 80 nazioni del pianeta.
                </p>
              </div>
              <div class="gothia-world-pill">
                🌍 THE WORLD YOUTH CUP · GÖTEBORG &amp; SHENYANG
              </div>
            </div>

            <div class="gothia-dual-grid" id="gothia-dual-grid">
              <!-- SVEZIA: GOTEBORG -->
              <article class="gothia-monument-card is-active-slide" data-slide-label="1 / 2 • 🇸🇪 SVEZIA GÖTEBORG (26 ED.)">
                <div class="gothia-monument-visual" onclick="openLightbox(this.querySelector('img').src, 'Gothia Cup Göteborg — Cerimonia inaugurale allo Stadio Ullevi davanti a 55.000 spettatori')">
                  <img src="{asset('assets/gothia_2015.jpg')}" alt="Gothia Cup Göteborg Stadio Ullevi" loading="lazy" />
                  <div class="gothia-monument-badges">
                    <span class="gothia-country-tag">🇸🇪 SVEZIA · GÖTEBORG (1989 – 2024)</span>
                    <span class="gothia-edition-tag">RECORD ITALIANO DI PRESENZE</span>
                  </div>
                </div>
                <div class="gothia-monument-body">
                  <span class="gothia-monument-watermark">ULLEVI</span>
                  <h3 class="gothia-monument-title">26 Spedizioni a Göteborg · Stadio Ullevi</h3>
                  <p class="gothia-monument-desc">
                    Dal debutto del <strong>1989</strong> fino all&rsquo;edizione <strong>2024</strong>, l&rsquo;A.C.O.S. Treviglio ha rappresentato l&rsquo;Italia per ben <strong>26 edizioni</strong> al torneo giovanile pi&ugrave; grande del mondo (1.700 squadre di 80 nazioni), sfilando con il tricolore nella leggendaria cerimonia inaugurale dello <strong>Stadio Ullevi</strong> e alla <strong>SKF Arena</strong>.
                  </p>
                  <div class="gothia-kpi-row">
                    <div class="gothia-kpi-cell">
                      <span class="gothia-kpi-val">26 Edizioni</span>
                      <span class="gothia-kpi-lbl">Dal 1989 al 2024</span>
                    </div>
                    <div class="gothia-kpi-cell">
                      <span class="gothia-kpi-val">80 Nazioni</span>
                      <span class="gothia-kpi-lbl">1.700 Squadre</span>
                    </div>
                    <div class="gothia-kpi-cell">
                      <span class="gothia-kpi-val">55.000</span>
                      <span class="gothia-kpi-lbl">Spettatori Ullevi</span>
                    </div>
                  </div>
                </div>
              </article>

              <!-- CINA: SHENYANG -->
              <article class="gothia-monument-card" data-slide-label="2 / 2 • 🇨🇳 CINA SHENYANG (3° POSTO)">
                <div class="gothia-monument-visual" onclick="openLightbox(this.querySelector('img').src, 'Gothia Cup — La delegazione giallonera A.C.O.S. Treviglio nei tornei internazionali')">
                  <img src="{asset('assets/gothia_2024_3.jpg')}" alt="Gothia Cup Delegazione Internazionale ACOS" loading="lazy" />
                  <div class="gothia-monument-badges">
                    <span class="gothia-country-tag">🇨🇳 CINA · SHENYANG (AGOSTO 2016)</span>
                    <span class="gothia-edition-tag">IMPRESA INTERCONTINENTALE</span>
                  </div>
                </div>
                <div class="gothia-monument-body">
                  <span class="gothia-monument-watermark">CHINA</span>
                  <h3 class="gothia-monument-title">Shenyang 2016: Unica Italiana sul Podio</h3>
                  <p class="gothia-monument-desc">
                    Nell&rsquo;agosto <strong>2016</strong> l&rsquo;A.C.O.S. vola a <strong>Shenyang (Cina)</strong> come <strong>unica societ&agrave; italiana invitata</strong> alla Gothia Cup China: una spedizione memorabile culminata con la conquista del <strong>3&deg; Posto Assoluto</strong> sul podio internazionale e della prestigiosa <strong>Coppa Disciplina</strong> per il Fair Play esemplare.
                  </p>
                  <div class="gothia-kpi-row">
                    <div class="gothia-kpi-cell">
                      <span class="gothia-kpi-val">Club Invitato</span>
                      <span class="gothia-kpi-lbl">Unica Italiana</span>
                    </div>
                    <div class="gothia-kpi-cell">
                      <span class="gothia-kpi-val">🏆 3&deg; Posto</span>
                      <span class="gothia-kpi-lbl">Podio Shenyang</span>
                    </div>
                    <div class="gothia-kpi-cell">
                      <span class="gothia-kpi-val">🏆 Fair Play</span>
                      <span class="gothia-kpi-lbl">Coppa Disciplina</span>
                    </div>
                  </div>
                </div>
              </article>
            </div>
            <div class="vigano-slider-bar vigano-mobile-only" aria-label="Sfoglia spedizioni Gothia Cup Svezia e Cina">
              <button type="button" class="vigano-slider-arrow" onclick="stepMobileClubSlide('gothia-dual-grid', '.gothia-monument-card', 'gothia-slide-label', 'gothia-slide-dots', -1)" aria-label="Spedizione precedente">←</button>
              <div class="vigano-slider-status">
                <span id="gothia-slide-label">1 / 2 • 🇸🇪 SVEZIA GÖTEBORG (26 ED.)</span>
                <div class="vigano-slider-dots" id="gothia-slide-dots">
                  <span class="v-dot active"></span>
                  <span class="v-dot"></span>
                </div>
              </div>
              <button type="button" class="vigano-slider-arrow is-next" onclick="stepMobileClubSlide('gothia-dual-grid', '.gothia-monument-card', 'gothia-slide-label', 'gothia-slide-dots', 1)" aria-label="Spedizione successiva">→</button>
            </div>
          </div>
          </div><!-- /#subpane-club-storia -->

          <!-- SOTTO-VISTA 1 (DEFAULT): ORGANIGRAMMA SERIE A BROADCAST GOVERNANCE STAGE -->
          <div id="subpane-club-org" class="subpane-view active" data-sub-group="club">
          <!-- ATTO III: ORGANIGRAMMA SERIE A BROADCAST GOVERNANCE STAGE -->
          <div class="org-stage" style="margin-bottom:1.5rem;">
            <div class="org-stage-bg-watermark">ACOS 1971</div>

            <div class="org-stage-header">
              <div>
                <span class="section-eyebrow">Corporate Governance, Presidenza &amp; Direzione Sportiva</span>
                <h2 class="section-title" style="margin-bottom:0;">Organigramma Societario Ufficiale</h2>
              </div>
              <div class="org-fed-seal">
                <img src="{crest_data_uri}" alt="Stemma A.C.O.S." style="width:24px;height:30px;object-fit:contain;" />
                <span>A.S.D. A.C.O.S. TREVIGLIO · MATR. FIGC 676164</span>
              </div>
            </div>

            <!-- LIVELLO 01: VERTICE PRESIDENZIALE -->
            <div class="org-tier-label-bar">
              <span class="org-tier-tag">01 // VERTICE PRESIDENZIALE</span>
              <div class="org-tier-rail"></div>
            </div>

            <div class="org-tier-presidency">
              <article class="org-pres-card">
                <span class="org-watermark">PRES</span>
                <div class="org-card-top">
                  <span class="org-role-badge">★ Presidente del Club</span>
                  <span style="font-family:var(--font-mono);font-size:0.68rem;color:var(--acos-yellow);font-weight:800;">CARICA ESECUTIVA</span>
                </div>
                <div class="org-pres-body">
                  <div class="org-pres-shield">
                    <img src="{crest_data_uri}" alt="Stemma A.C.O.S. Treviglio" />
                  </div>
                  <div class="org-name-stack">
                    <span class="org-first-name">Stefano</span>
                    <div class="org-last-name">Viganò</div>
                    <div class="org-gold-slash"></div>
                  </div>
                </div>
                <div class="org-exec-desc">
                  <strong>Guida Societaria &amp; Rappresentanza Legale</strong>
                  Affiliazione F.I.G.C. / L.N.D. Lombardia · Matr. 676164
                </div>
              </article>

              <article class="org-pres-card">
                <span class="org-watermark">1971</span>
                <div class="org-card-top">
                  <span class="org-role-badge">★ Presidente Onorario</span>
                  <span style="font-family:var(--font-mono);font-size:0.68rem;color:var(--acos-yellow);font-weight:800;">MEMORIA STORICA</span>
                </div>
                <div class="org-pres-body">
                  <div class="org-pres-shield">
                    <img src="{crest_data_uri}" alt="Stemma A.C.O.S. Treviglio" />
                  </div>
                  <div class="org-name-stack">
                    <span class="org-first-name">Mario</span>
                    <div class="org-last-name">Barbieri</div>
                    <div class="org-gold-slash"></div>
                  </div>
                </div>
                <div class="org-exec-desc">
                  <strong>Co-Fondatore Storico A.C.O.S. Treviglio</strong>
                  Fondata il 18 Agosto 1971 · Custode dei Valori Gialloneri
                </div>
              </article>
            </div>

            <!-- CONNETTORE GERARCHICO BROADCAST (LIVELLO 01 -> LIVELLO 02) -->
            <div class="org-connector-bridge" aria-hidden="true">
              <div class="org-connector-node"></div>
            </div>

            <!-- LIVELLO 02: DIREZIONE ESECUTIVA, SPORTIVA & SEGRETERIA -->
            <div class="org-tier-label-bar">
              <span class="org-tier-tag">02 // VICE PRESIDENZA, DIREZIONE SPORTIVA &amp; SEGRETERIA</span>
              <div class="org-tier-rail"></div>
            </div>

            <div class="org-tier-management">
              <article class="org-exec-card">
                <span class="org-watermark">VP</span>
                <div class="org-card-top">
                  <span class="org-role-badge">Vice Presidente</span>
                  <span class="org-monogram-shield">PG</span>
                </div>
                <div class="org-name-stack">
                  <span class="org-first-name">Pierangelo</span>
                  <div class="org-last-name">Gusmini</div>
                  <div class="org-gold-slash"></div>
                </div>
                <div class="org-exec-desc">
                  <strong>Delega Operativa</strong>
                  Resp. Scuola Calcio F.I.G.C.
                </div>
              </article>

              <article class="org-exec-card">
                <span class="org-watermark">VP</span>
                <div class="org-card-top">
                  <span class="org-role-badge">Vice Presidente</span>
                  <span class="org-monogram-shield">NR</span>
                </div>
                <div class="org-name-stack">
                  <span class="org-first-name">Niccolò</span>
                  <div class="org-last-name">Riganti</div>
                  <div class="org-gold-slash"></div>
                </div>
                <div class="org-exec-desc">
                  <strong>Delega Operativa</strong>
                  Governance &amp; Coordinamento
                </div>
              </article>

              <article class="org-exec-card">
                <span class="org-watermark">DS</span>
                <div class="org-card-top">
                  <span class="org-role-badge">Direttore Sportivo</span>
                  <span class="org-monogram-shield">PF</span>
                </div>
                <div class="org-name-stack">
                  <span class="org-first-name">Paolo</span>
                  <div class="org-last-name">Facchinetti</div>
                  <div class="org-gold-slash"></div>
                </div>
                <div class="org-exec-desc">
                  <strong>Delega Tecnica</strong>
                  Prima Squadra &amp; Agonistica
                </div>
              </article>

              <article class="org-exec-card">
                <span class="org-watermark">SG</span>
                <div class="org-card-top">
                  <span class="org-role-badge">Segretario Generale</span>
                  <span class="org-monogram-shield">FS</span>
                </div>
                <div class="org-name-stack">
                  <span class="org-first-name">Francesco</span>
                  <div class="org-last-name">Scrivanti</div>
                  <div class="org-gold-slash"></div>
                </div>
                <div class="org-exec-desc">
                  <strong>Safeguarding &amp; Segreteria</strong>
                  Segretario &amp; Tutela Minori
                </div>
              </article>
            </div>

            <!-- CONNETTORE GERARCHICO BROADCAST (LIVELLO 02 -> LIVELLO 03) -->
            <div class="org-connector-bridge" aria-hidden="true">
              <div class="org-connector-node"></div>
            </div>

            <!-- LIVELLO 03: CONSIGLIO DIRETTIVO SOCIETARIO -->
            <div class="org-council-deck">
              <div class="org-council-header">
                <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
                  <span class="org-tier-tag" style="margin:0;">03 // ORGANO COLLEGIALE</span>
                  <span class="org-council-title">Consiglio Direttivo Societario</span>
                </div>
                <span class="org-council-sub">Indirizzo Strategico &amp; Gestione Sportiva A.C.O.S.</span>
              </div>
              <div class="org-council-grid">
                <div class="org-councilor-card">
                  <div class="org-councilor-top">
                    <span class="org-councilor-role">Consigliere</span>
                    <span class="org-councilor-avatar">EF</span>
                  </div>
                  <div class="org-name-stack">
                    <span class="org-first-name">Enrico</span>
                    <div class="org-last-name">Fontana</div>
                  </div>
                </div>

                <div class="org-councilor-card">
                  <div class="org-councilor-top">
                    <span class="org-councilor-role">Consigliere</span>
                    <span class="org-councilor-avatar">FP</span>
                  </div>
                  <div class="org-name-stack">
                    <span class="org-first-name">Federico</span>
                    <div class="org-last-name">Perazza</div>
                  </div>
                </div>

                <div class="org-councilor-card">
                  <div class="org-councilor-top">
                    <span class="org-councilor-role">Consigliere</span>
                    <span class="org-councilor-avatar">JR</span>
                  </div>
                  <div class="org-name-stack">
                    <span class="org-first-name">Jacopo</span>
                    <div class="org-last-name">Riganti</div>
                  </div>
                </div>

                <div class="org-councilor-card">
                  <div class="org-councilor-top">
                    <span class="org-councilor-role">Consigliere</span>
                    <span class="org-councilor-avatar">EV</span>
                  </div>
                  <div class="org-name-stack">
                    <span class="org-first-name">Enrico</span>
                    <div class="org-last-name">Viganò</div>
                  </div>
                </div>

                <div class="org-councilor-card">
                  <div class="org-councilor-top">
                    <span class="org-councilor-role">Consigliere</span>
                    <span class="org-councilor-avatar">AZ</span>
                  </div>
                  <div class="org-name-stack">
                    <span class="org-first-name">Angelo</span>
                    <div class="org-last-name">Zucchinali</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div><!-- /#subpane-club-org -->

          <!-- SOTTO-VISTA 3: FONDAZIONE ETICA "CUORE GIALLONERO – IVAN ARZILLI" -->
          <div id="subpane-club-cuore" class="subpane-view" data-sub-group="club">
          <!-- ATTO IV: FONDAZIONE ETICA "CUORE GIALLONERO – IVAN ARZILLI" -->
          <div class="cuore-ethical-stage">
            <div class="cuore-lead-banner">
              <div class="cuore-emblem-box" style="cursor:pointer;" onclick="openLightbox('{asset('assets/cuore_giallonero.jpg')}', 'Cuore Giallonero — Iniziative Benefiche nel nome di Ivan Arzilli')">
                <svg class="cuore-emblem-svg" viewBox="0 0 100 94" aria-label="Emblema Cuore Giallonero A.C.O.S. Treviglio">
                  <defs>
                    <clipPath id="heartLeftClip"><rect x="0" y="0" width="50" height="94" /></clipPath>
                    <clipPath id="heartRightClip"><rect x="50" y="0" width="50" height="94" /></clipPath>
                  </defs>
                  <path d="M50 86 C20 65 4 46 4 27 C4 13 15 4 28 4 C38 4 46 10 50 19 C54 10 62 4 72 4 C85 4 96 13 96 27 C96 46 80 65 50 86 Z" fill="#FFDE24" clip-path="url(#heartLeftClip)" />
                  <path d="M50 86 C20 65 4 46 4 27 C4 13 15 4 28 4 C38 4 46 10 50 19 C54 10 62 4 72 4 C85 4 96 13 96 27 C96 46 80 65 50 86 Z" fill="#06080D" clip-path="url(#heartRightClip)" />
                  <line x1="50" y1="18" x2="50" y2="85" stroke="#FFDE24" stroke-width="1.5" stroke-opacity="0.45" />
                  <path d="M50 86 C20 65 4 46 4 27 C4 13 15 4 28 4 C38 4 46 10 50 19 C54 10 62 4 72 4 C85 4 96 13 96 27 C96 46 80 65 50 86 Z" fill="none" stroke="#FFDE24" stroke-width="3.2" stroke-linejoin="round" />
                </svg>
                <img src="{crest_data_uri}" alt="Cuore Giallonero Ivan Arzilli" class="cuore-emblem-crest" />
              </div>
              <div class="cuore-lead-copy">
                <span class="section-eyebrow">Fondazione Etica &amp; Impegno Sociale · In Memoria di Ivan Arzilli</span>
                <h3>Cuore Giallonero: Quando una Maglia di Calcio Diventa Impegno Civile</h3>
                <p>
                  Fin dagli anni &rsquo;90 — quando l&rsquo;A.C.O.S. scelse di apporre gratuitamente sulle proprie maglie da gioco il logo di <strong>Emergency</strong> accogliendo a Treviglio <strong>Gino Strada</strong> — la societ&agrave; educa i propri atleti alla solidariet&agrave; concreta, sostenendo nel nome dell&rsquo;indimenticato dirigente <strong>Ivan Arzilli</strong> oltre <strong>20 realtà del volontariato locale, nazionale e internazionale</strong>.
                </p>
              </div>
              <div class="cuore-strada-quote">
                <span class="csq-tag">MEMORIA STORICA · ANNI &rsquo;90</span>
                <p class="csq-text">
                  &ldquo;Una scelta pionieristica nel calcio dilettantistico italiano: scendere in campo con il simbolo di <strong>Emergency</strong> sul petto e ospitare <strong>Gino Strada</strong> a Treviglio per insegnare ai ragazzi che lo sport non &egrave; mai neutrale di fronte a chi soffre.&rdquo;
                </p>
              </div>
            </div>

            <div class="cuore-pillars-grid" id="cuore-pillars-grid">
              <!-- PILASTRO 01: SALUTE, RICERCA & PEDIATRIA -->
              <div class="cuore-pillar-card is-active-slide" data-slide-label="PILASTRO 1 / 3 • RICERCA &amp; PEDIATRIA">
                <div class="cuore-pillar-head">
                  <div>
                    <span class="cuore-pillar-num">01 // RICERCA MEDICA &amp; PEDIATRIA</span>
                    <h4 class="cuore-pillar-title">Salute &amp; Tutela Bambini</h4>
                  </div>
                  <span class="cuore-pillar-icon">❤️</span>
                </div>
                <ul class="cuore-charity-list">
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Fibrosi Cistica &amp; Neuroblastoma</strong> — Ricerca medica pediatrica</span></li>
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Fondazione Aiutare i Bambini</strong> — Progetto &ldquo;Cuore di Bimbi&rdquo;</span></li>
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Amici di Gabry &amp; Futura ONLUS</strong> — Inclusione e sostegno famiglie</span></li>
                </ul>
              </div>

              <!-- PILASTRO 02: COMUNITÀ, SCUOLE & IMPIANTI DI TREVIGLIO -->
              <div class="cuore-pillar-card" data-slide-label="PILASTRO 2 / 3 • COMUNIT&Agrave; &amp; DAE">
                <div class="cuore-pillar-head">
                  <div>
                    <span class="cuore-pillar-num">02 // TERRITORIO &amp; CARDIOPROTEZIONE</span>
                    <h4 class="cuore-pillar-title">Comunit&agrave; di Treviglio</h4>
                  </div>
                  <span class="cuore-pillar-icon">🏛️</span>
                </div>
                <ul class="cuore-charity-list">
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Associazione Ambrogio Mazza</strong> — Donazione 4 Defibrillatori DAE</span></li>
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Croce Rossa &amp; Scuole Treviglio</strong> — Automezzo e dotazioni didattiche</span></li>
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Mensa Solidale &amp; Cooperative</strong> — Sostegno alla rete cittadina</span></li>
                </ul>
              </div>

              <!-- PILASTRO 03: EMERGENZE & MISSIONI UMANITARIE -->
              <div class="cuore-pillar-card" data-slide-label="PILASTRO 3 / 3 • MISSIONI &amp; EMERGENCY">
                <div class="cuore-pillar-head">
                  <div>
                    <span class="cuore-pillar-num">03 // SOLIDARIET&Agrave; SENZA CONFINI</span>
                    <h4 class="cuore-pillar-title">Missioni &amp; Emergenze</h4>
                  </div>
                  <span class="cuore-pillar-icon">🌍</span>
                </div>
                <ul class="cuore-charity-list">
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Emergency ONLUS</strong> — Logo sulle maglie e incontro con Gino Strada</span></li>
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Save The Children &amp; Tanzania</strong> — Tutela infanzia e Villaggio della Gioia</span></li>
                  <li class="cuore-charity-item"><span class="cci-dot"></span><span><strong>Per&ugrave; Huaycan &amp; Emergenza Sisma</strong> — Solidariet&agrave; internazionale</span></li>
                </ul>
              </div>
            </div>
            <div class="vigano-slider-bar vigano-mobile-only" aria-label="Sfoglia i 3 pilastri solidali Cuore Giallonero">
              <button type="button" class="vigano-slider-arrow" onclick="stepMobileClubSlide('cuore-pillars-grid', '.cuore-pillar-card', 'cuore-pillar-label', 'cuore-pillar-dots', -1)" aria-label="Pilastro precedente">←</button>
              <div class="vigano-slider-status">
                <span id="cuore-pillar-label">PILASTRO 1 / 3 • RICERCA &amp; PEDIATRIA</span>
                <div class="vigano-slider-dots" id="cuore-pillar-dots">
                  <span class="v-dot active"></span>
                  <span class="v-dot"></span>
                  <span class="v-dot"></span>
                </div>
              </div>
              <button type="button" class="vigano-slider-arrow is-next" onclick="stepMobileClubSlide('cuore-pillars-grid', '.cuore-pillar-card', 'cuore-pillar-label', 'cuore-pillar-dots', 1)" aria-label="Pilastro successivo">→</button>
            </div>
          </div>
          </div><!-- /#subpane-club-cuore -->

        </div>
      </div>
    </section>

    <!-- ========================================================================
         PAGE 4: INFO & SEDE (3 SOTTO-VISTE IDENTICHE: STADI & CONTATTI · QUOTE & IBAN · KIT & TUTELA)
         ======================================================================== -->
    <section id="page-contatti" class="page-view">
      <!-- BARRA DI SOTTO-NAVIGAZIONE UNIFICATA A 3 COLONNE (IDENTICA SU TUTTE LE PAGINE) -->
      <div class="acos-subnav-wrap">
        <div class="container">
          <div class="acos-subnav-bar" role="tablist" aria-label="Sotto-sezioni Info, Sede e Segreteria">
            <button type="button" class="acos-subnav-pill active" data-sub-group="info" data-subpane="info-contatti" onclick="switchSubPane('info', 'info-contatti', this)">
              <span class="subnav-idx">01</span>
              <span class="subnav-lbl">Stadi &amp; Contatti</span>
            </button>
            <button type="button" class="acos-subnav-pill" data-sub-group="info" data-subpane="info-quote" onclick="switchSubPane('info', 'info-quote', this)">
              <span class="subnav-idx">02</span>
              <span class="subnav-lbl">Iscrizioni &amp; IBAN</span>
            </button>
            <button type="button" class="acos-subnav-pill" data-sub-group="info" data-subpane="info-servizi" onclick="switchSubPane('info', 'info-servizi', this)">
              <span class="subnav-idx">03</span>
              <span class="subnav-lbl">Kit &amp; Tutela</span>
            </button>
          </div>
        </div>
      </div>

      <div class="section-block">
        <div class="container">

          <!-- SUB-PANE 2: PERCORSI DI TESSERAMENTO STAGIONE 2025/2026 & TESORERIA BANCARIA IBAN -->
          <div id="subpane-info-quote" class="subpane-view" data-sub-group="info">
          <div class="section-header">
            <div>
              <span class="section-eyebrow">Segreteria Sportiva · Tesseramenti Stagione Sportiva 2025/2026</span>
              <h2 class="section-title">Percorsi di Tesseramento &amp; Tesoreria IBAN</h2>
            </div>
          </div>

          <div class="season-pass-grid">
            <!-- FILIERA 01: SETTORE GIOVANILE & ATTIVITÀ DI BASE -->
            <article class="season-pass-card">
              <div class="sp-top">
                <div class="sp-badge-row">
                  <span class="sp-tier-tag">FILIERA 01 // AGONISTICA &amp; BASE</span>
                  <span class="sp-type-lbl">U17 &ndash; U10 F.I.G.C.</span>
                </div>
                <h3 class="sp-title">Settore Giovanile &amp; Attivit&agrave; di Base</h3>
              </div>
              <div class="sp-cats-grid">
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Allievi</span>
                  <span class="sp-cat-age">U17 / U16</span>
                </div>
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Giovanissimi</span>
                  <span class="sp-cat-age">U15 / U14</span>
                </div>
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Esordienti</span>
                  <span class="sp-cat-age">U13 / U12</span>
                </div>
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Pulcini</span>
                  <span class="sp-cat-age">U11 / U10</span>
                </div>
              </div>
              <div class="sp-breakdown">
                <div class="sp-bd-row">
                  <span class="sp-bd-lbl">Rinnovo Tesserati</span>
                  <span class="sp-bd-val">Quota Ordinaria</span>
                </div>
                <div class="sp-bd-row">
                  <span class="sp-bd-lbl">Nuovi Iscritti 1&deg; Anno</span>
                  <span class="sp-bd-val is-gold">Quota Agevolata</span>
                </div>
              </div>
            </article>

            <!-- FILIERA 02: SCUOLA CALCIO F.I.G.C. & PICCOLI AMICI (FEATURED) -->
            <article class="season-pass-card is-featured">
              <div class="sp-top">
                <div class="sp-badge-row">
                  <span class="sp-tier-tag">★ FILIERA 02 // SCUOLA CALCIO</span>
                  <span class="sp-type-lbl">5 &ndash; 8 ANNI F.I.G.C.</span>
                </div>
                <h3 class="sp-title">Scuola Calcio F.I.G.C. &amp; Piccoli Amici</h3>
              </div>
              <div class="sp-cats-grid">
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Primi Calci</span>
                  <span class="sp-cat-age">7 &ndash; 8 Anni</span>
                </div>
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Piccoli Amici</span>
                  <span class="sp-cat-age">5 &ndash; 6 Anni</span>
                </div>
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Metodo</span>
                  <span class="sp-cat-age">Atalanta B.C.</span>
                </div>
                <div class="sp-cat-chip">
                  <span class="sp-cat-name">Prove</span>
                  <span class="sp-cat-age">Open Day</span>
                </div>
              </div>
              <div class="sp-breakdown">
                <div class="sp-bd-row">
                  <span class="sp-bd-lbl">Rinnovo Tesserati</span>
                  <span class="sp-bd-val">Quota Ordinaria</span>
                </div>
                <div class="sp-bd-row">
                  <span class="sp-bd-lbl">Nuovi Iscritti 1&deg; Anno</span>
                  <span class="sp-bd-val is-gold">Quota Agevolata</span>
                </div>
              </div>
            </article>
          </div>

          <!-- BARRA UNICA SEGRETERIA TESSERAMENTI (CONTATTO DIRETTO FISSO + EMAIL) -->
          <div class="sp-segreteria-strip">
            <div class="sps-info">
              <span class="sps-eyebrow">Segreteria Tesseramenti &amp; Dettaglio Quote &bull; Via ai Malgari, 6</span>
              <div class="sps-hours">🕒 Orari Sportello: <strong>Lun&ndash;Ven 17:00&ndash;19:30 &bull; Sab 09:30&ndash;12:00</strong></div>
            </div>
            <div class="sps-actions">
              <a href="tel:0363304036" class="btn-card-gold sps-btn">📞 0363 304036</a>
              <a href="mailto:info@acos.it?subject=Informazioni%20Tesseramento%20Stagione%202025/2026%20-%20A.C.O.S.%20Treviglio" class="btn-card-outline sps-btn">✉️ Scrivi Email</a>
            </div>
          </div>

          <!-- PLANCIA TESORERIA BANCARIA & ISTRUZIONI BONIFICO -->
          <div class="treasury-iban-stage">
            <div class="treasury-top-row">
              <div>
                <span class="section-eyebrow" style="margin-bottom:0.2rem;">Tesoreria Ufficiale del Club · Pagamento Tracciabile con Bonifico Bancario</span>
                <div class="iban-code" id="iban-text">{CLUB_DATA['iban']}</div>
              </div>
              <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
                <button type="button" class="btn-gold-broadcast" onclick="copyIban()" id="copy-iban-btn">
                  📋 Copia Codice IBAN
                </button>
                <button type="button" class="btn-ghost-broadcast" onclick="copyCausale()" id="copy-causale-btn">
                  ✍️ Copia Schema Causale
                </button>
              </div>
            </div>

            <div class="treasury-rules-grid">
              <div class="treasury-rule-box">
                <span class="trb-tag">01 // INTESTATARIO CONTO</span>
                <span class="trb-val">{CLUB_DATA['iban_holder']}</span>
              </div>
              <div class="treasury-rule-box">
                <span class="trb-tag">02 // CAUSALE OBBLIGATORIA</span>
                <span class="trb-val">&ldquo;COGNOME NOME ATLETA &bull; ANNATA &bull; QUOTA 2025/2026&rdquo;</span>
              </div>
              <div class="treasury-rule-box">
                <span class="trb-tag">03 // CONTABILE &amp; DETRAZIONE 730</span>
                <span class="trb-val">Invia PDF a <a href="mailto:info@acos.it" style="color:var(--acos-yellow);text-decoration:underline;">info@acos.it</a> o in Sede (Via ai Malgari, 6)</span>
              </div>
            </div>
          </div>
          </div><!-- /#subpane-info-quote -->

          <!-- SUB-PANE 3: SPORTELLO OPERATIVO DIGITALE (KIT REMELS, SINISTRI, VISITE & SAFEGUARDING) -->
          <div id="subpane-info-servizi" class="subpane-view" data-sub-group="info">
          <div class="section-header" style="margin-bottom:1.15rem;">
            <div>
              <span class="section-eyebrow">Servizi Online per Tesserati &amp; Famiglie</span>
              <h3 class="section-title" style="font-size:clamp(1.6rem, 2.6vw, 2.2rem);">Sportello Operativo: Kit Tecnico, Assicurazione &amp; Safeguarding</h3>
            </div>
          </div>

          <div class="portal-desk-grid">
            <!-- MODULO 01: KIT REMELS SPORT -->
            <article class="portal-desk-card">
              <div>
                <div class="pdc-head">
                  <div>
                    <span class="pdc-num">01 // FORNITURA TECNICA UFFICIALE</span>
                    <h4 class="pdc-title">Store Kit Remels Sport</h4>
                  </div>
                  <span class="pdc-icon">👕</span>
                </div>
                <p class="pdc-desc">
                  Ordina online il kit ufficiale giallonero presso il partner tecnico <strong>Remels Sport (Cologne)</strong>.
                </p>
              </div>
              <div class="pdc-actions">
                <a href="{CLUB_DATA['remels_url']}" target="_blank" rel="noopener noreferrer" class="btn-card-gold" style="text-align:center;">🛍️ Store Online →</a>
                <a href="{CLUB_DATA['remels_guide_pdf']}" target="_blank" rel="noopener noreferrer" class="btn-card-outline" style="text-align:center;">📄 Guida PDF</a>
              </div>
            </article>

            <!-- MODULO 02: SINISTRI LND & FIGC SGS -->
            <article class="portal-desk-card">
              <div>
                <div class="pdc-head">
                  <div>
                    <span class="pdc-num">02 // TUTELA ASSICURATIVA FEDERALE</span>
                    <h4 class="pdc-title">Apertura Sinistri LND / FIGC</h4>
                  </div>
                  <span class="pdc-icon">🏥</span>
                </div>
                <p class="pdc-desc">
                  Portali telematici federali <strong>L.N.D. (AON OneCare)</strong> e <strong>F.I.G.C. SGS (eClaim)</strong> per pratiche infortuni.
                </p>
              </div>
              <div class="pdc-actions">
                <a href="{CLUB_DATA['lnd_sinistri_url']}" target="_blank" rel="noopener noreferrer" class="btn-card-outline" style="text-align:center;">🏥 Sinistri L.N.D.</a>
                <a href="{CLUB_DATA['sgs_sinistri_url']}" target="_blank" rel="noopener noreferrer" class="btn-card-outline" style="text-align:center;">🏥 Sinistri F.I.G.C.</a>
              </div>
            </article>

            <!-- MODULO 03: IDONEITÀ MEDICA & MODULISTICA -->
            <article class="portal-desk-card">
              <div>
                <div class="pdc-head">
                  <div>
                    <span class="pdc-num">03 // IDONEIT&Agrave; MEDICO-SPORTIVA</span>
                    <h4 class="pdc-title">Visite Mediche &amp; Moduli</h4>
                  </div>
                  <span class="pdc-icon">📋</span>
                </div>
                <p class="pdc-desc">
                  Fino a 11 anni certificato non agonistico; da 12 anni visita agonistica gratuita con modulo timbrato in Sede.
                </p>
              </div>
              <div class="pdc-actions">
                <a href="{CLUB_DATA['autocert_pdf']}" target="_blank" rel="noopener noreferrer" class="btn-card-gold" style="text-align:center;">📥 Modulo PDF</a>
                <a href="tel:0363304036" class="btn-card-outline" style="text-align:center;">📞 0363 304036</a>
              </div>
            </article>
          </div>

          <!-- ATTO III: PRESIDIO FEDERALE SAFEGUARDING (D.LGS. 36/2021 E 39/2021) -->
          <div class="safeguarding-command-stage">
            <div class="safeguarding-top-head">
              <span class="fed-tag fed-safe" style="margin-bottom:0.35rem;">Adempimento Normativo F.I.G.C. / C.O.N.I. · D.Lgs. 36/2021 e 39/2021</span>
              <h3 class="section-title" style="margin-bottom:0;">Presidio Safeguarding · Tutela dei Minori &amp; Prevenzione Abusi</h3>
            </div>

            <div class="safeguarding-grid">
              <div class="safe-officer-card">
                <div>
                  <span class="safe-officer-tag">
                    ★ Responsabile Safeguarding Nominato dal Consiglio Direttivo
                  </span>
                  <div class="safe-officer-name">
                    Sig. Francesco Scrivanti
                  </div>
                  <p class="safe-officer-desc">
                    Segretario Generale dal <strong>01/07/2006</strong>, Responsabile contro abusi, violenze e discriminazioni (mandato fino al <strong>31/12/2026</strong>).
                  </p>
                </div>
                <div class="safe-officer-contact-pill">
                  <span>📍 Via ai Malgari, 6</span>
                  <span>&bull;</span>
                  <a href="tel:0363304036" style="color:var(--acos-yellow);font-weight:800;">📞 0363 304036</a>
                  <span>&bull;</span>
                  <a href="mailto:info@acos.it" style="color:var(--acos-yellow);font-weight:800;">✉️ info@acos.it</a>
                </div>
              </div>

              <div class="safe-docs-stack">
                <div class="safe-doc-row">
                  <div>
                    <span class="safe-doc-tag">01 // REGOLAMENTO SOCIETARIO UFFICIALE</span>
                    <div class="safe-doc-title">Modello Organizzativo e di Controllo (M.O.C.)</div>
                  </div>
                  <a href="{CLUB_DATA['safeguarding_modello_url']}" target="_blank" rel="noopener noreferrer" class="btn-gold-broadcast" style="padding:0.48rem 0.85rem;font-size:0.82rem;">
                    📘 PDF M.O.C. →
                  </a>
                </div>

                <div class="safe-doc-row">
                  <div>
                    <span class="safe-doc-tag">02 // CARTA DEI DOVERI ETICI</span>
                    <div class="safe-doc-title">Codice di Condotta a Tutela dei Minori</div>
                  </div>
                  <a href="{CLUB_DATA['safeguarding_codice_url']}" target="_blank" rel="noopener noreferrer" class="btn-ghost-broadcast" style="padding:0.48rem 0.85rem;font-size:0.82rem;">
                    📗 PDF Codice →
                  </a>
                </div>
              </div>
            </div>
          </div>
          </div><!-- /#subpane-info-servizi -->

          <!-- SUB-PANE 1: STADI, QUARTIER GENERALE & CENTRALINO DIRETTO (ATTIVO DI DEFAULT) -->
          <div id="subpane-info-contatti" class="subpane-view active" data-sub-group="info">
          <div class="section-header">
            <div>
              <span class="section-eyebrow">Le Case del Calcio Giallonero · 2 Impianti Cardioprotetti a Treviglio (BG)</span>
              <h2 class="section-title">I Nostri Stadi, Quartier Generale &amp; Centralino Diretto</h2>
            </div>
          </div>

          <div class="stadium-arenas-grid" id="stadium-arenas-grid">
            <!-- ARENA 01: CENTRO SPORTIVO AMBROGIO MAZZA / CAMPO ENZO RIGANTI -->
            <article class="stadium-arena-card is-active-slide" data-slide-label="IMPIANTO 1 / 2 &middot; C.S. AMBROGIO MAZZA (VIA AI MALGARI, 6)">
              <div class="sac-visual-header" style="background-image:url('{asset('assets/vigano_1.jpg')}');">
                <div class="sac-visual-veil"></div>
                <span class="sac-watermark">MAZZA</span>
                <div class="sac-top-badges">
                  <span class="sac-arena-tag">01 // SEDE &amp; SCUOLA CALCIO FIGC</span>
                  <span class="sac-dae-pill">❤️ PRESIDIO DAE</span>
                </div>
                <div class="sac-bottom-headline">
                  <h3 class="sac-title">Centro Sportivo &ldquo;Ambrogio Mazza&rdquo;</h3>
                  <div class="sac-address">📍 Campo &ldquo;Enzo Riganti&rdquo; · Via ai Malgari, 6 — Treviglio (BG) · Sede, Vivaio &amp; Torneo Vigan&ograve;</div>
                </div>
              </div>

              <div class="sac-body">
                <div class="arena-map-frame">
                  <iframe
                    class="venue-map-embed"
                    title="Mappa Sede e Centro Sportivo Ambrogio Mazza Via ai Malgari 6 Treviglio"
                    loading="lazy"
                    src="https://maps.google.com/maps?q=Via+ai+Malgari+6,+24047+Treviglio+BG&t=&z=15&ie=UTF8&iwloc=&output=embed">
                  </iframe>
                </div>
              </div>
            </article>

            <!-- ARENA 02: STADIO COMUNALE MARIO ZANCONTI -->
            <article class="stadium-arena-card" data-slide-label="IMPIANTO 2 / 2 &middot; STADIO COMUNALE ZANCONTI (VIA MILANO, 7)">
              <div class="sac-visual-header" style="background-image:url('{asset('assets/event_239.jpg')}');">
                <div class="sac-visual-veil"></div>
                <span class="sac-watermark">ZANCONTI</span>
                <div class="sac-top-badges">
                  <span class="sac-arena-tag">02 // STADIO GARE L.N.D.</span>
                  <span class="sac-dae-pill">⚽ PROMOZIONE &amp; U19 &Eacute;LITE</span>
                </div>
                <div class="sac-bottom-headline">
                  <h3 class="sac-title">Stadio Comunale &ldquo;Mario Zanconti&rdquo;</h3>
                  <div class="sac-address">📍 Via Milano, 7 — Treviglio (BG) · Campo a 11 &amp; Tribuna Spettatori</div>
                </div>
              </div>

              <div class="sac-body">
                <div class="arena-map-frame">
                  <iframe
                    class="venue-map-embed"
                    title="Mappa Stadio Comunale Mario Zanconti Via Milano 7 Treviglio"
                    loading="lazy"
                    src="https://maps.google.com/maps?q=Via+Milano+7,+24047+Treviglio+BG&t=&z=15&ie=UTF8&iwloc=&output=embed">
                  </iframe>
                </div>
              </div>
            </article>
          </div>

          <!-- BARRA FRECCE MOBILE PER SFOGLIARE I 2 STADI (1 MAPPA ALLA VOLTA SU TELEFONO) -->
          <div class="vigano-slider-bar vigano-mobile-only" style="margin-bottom:1.15rem;" aria-label="Selettore Impianti Sportivi">
            <button type="button" class="vigano-slider-arrow" onclick="stepMobileClubSlide('stadium-arenas-grid', '.stadium-arena-card', 'stadium-slide-label', 'stadium-slide-dots', -1)" aria-label="Impianto precedente">&#8592;</button>
            <div class="vigano-slider-status">
              <span id="stadium-slide-label">IMPIANTO 1 / 2 &middot; C.S. AMBROGIO MAZZA (VIA AI MALGARI, 6)</span>
              <div class="vigano-slider-dots" id="stadium-slide-dots">
                <span class="v-dot active"></span>
                <span class="v-dot"></span>
              </div>
            </div>
            <button type="button" class="vigano-slider-arrow is-next" onclick="stepMobileClubSlide('stadium-arenas-grid', '.stadium-arena-card', 'stadium-slide-label', 'stadium-slide-dots', 1)" aria-label="Impianto successivo">&#8594;</button>
          </div>

          <!-- ATTO II: CONCIERGE FORM MULTI-PROFILO & CENTRALINO DIRETTO (SERIE A BROADCAST) -->
          <div class="contact-command-stage" id="contact-concierge-stage">
            <div class="concierge-form-card">
              <div>
                <span class="section-eyebrow">Sportello Digitale Ufficiale &bull; Richiesta Diretta al Club</span>
                <h3 class="concierge-form-title">
                  Scrivi Direttamente al Club
                </h3>

                <!-- 4 PILLOLE PROFILO UTENTE COMPATTE -->
                <div class="cf-profile-tabs" role="tablist" aria-label="Profilo di Contatto">
                  <button type="button" class="cf-profile-tab active" data-cf-profile="atleta" onclick="selectContactProfile('atleta', this)">
                    <span class="cfp-title">⚽ Atleta / Famiglia</span>
                  </button>
                  <button type="button" class="cf-profile-tab" data-cf-profile="sponsor" onclick="selectContactProfile('sponsor', this)">
                    <span class="cfp-title">🤝 Azienda / Sponsor</span>
                  </button>
                  <button type="button" class="cf-profile-tab" data-cf-profile="societa" onclick="selectContactProfile('societa', this)">
                    <span class="cfp-title">🏆 Societ&agrave; / Tornei</span>
                  </button>
                  <button type="button" class="cf-profile-tab" data-cf-profile="segreteria" onclick="selectContactProfile('segreteria', this)">
                    <span class="cfp-title">📋 Segreteria Club</span>
                  </button>
                </div>
              </div>

              <form onsubmit="submitContactForm(event)" style="display:flex;flex-direction:column;gap:0.78rem;margin-top:auto;">
                <input type="hidden" id="cf-profile-type" value="Atleta / Tesseramento" />
                <div>
                  <label id="cf-name-label" for="cf-name" style="font-size:0.74rem;font-weight:800;display:block;margin-bottom:0.25rem;color:var(--text-silver);text-transform:uppercase;letter-spacing:0.05em;">Nome e Cognome (Atleta o Referente) *</label>
                  <input id="cf-name" type="text" class="form-input" required placeholder="Es. Marco Rossi" />
                </div>
                <div class="cf-cat-phone-grid">
                  <div>
                    <label id="cf-year-label" for="cf-year" style="font-size:0.74rem;font-weight:800;display:block;margin-bottom:0.25rem;color:var(--text-silver);text-transform:uppercase;letter-spacing:0.05em;">Categoria / Fascia d&rsquo;Interesse</label>
                    <select id="cf-year" class="form-select">
                      <option value="Prima Squadra Promozione / Juniores U19 Élite">Promozione &amp; Juniores U19 &Eacute;lite</option>
                      <option value="Agonistica Allievi & Giovanissimi U14-U17 (2009-2012)">Agonistica U14&ndash;U17 (2009&ndash;2012)</option>
                      <option value="Attività di Base Esordienti & Pulcini (2013-2016)">Esordienti &amp; Pulcini (2013&ndash;2016)</option>
                      <option value="Scuola Calcio Primi Calci & Piccoli Amici (2017-2020)">Scuola Calcio 5&ndash;8 Anni (2017&ndash;2020)</option>
                    </select>
                  </div>
                  <div>
                    <label for="cf-phone" style="font-size:0.74rem;font-weight:800;display:block;margin-bottom:0.25rem;color:var(--text-silver);text-transform:uppercase;letter-spacing:0.05em;">Recapito Telefonico *</label>
                    <input id="cf-phone" type="tel" class="form-input" required placeholder="Es. 348 1234567" />
                  </div>
                </div>
                <div>
                  <label id="cf-msg-label" for="cf-msg" style="font-size:0.74rem;font-weight:800;display:block;margin-bottom:0.25rem;color:var(--text-silver);text-transform:uppercase;letter-spacing:0.05em;">Dettagli della Richiesta</label>
                  <textarea id="cf-msg" rows="2" class="form-textarea" placeholder="Indica annata, ruolo o informazioni richieste..."></textarea>
                </div>
                <label style="display:flex;align-items:flex-start;gap:0.5rem;font-size:0.76rem;color:var(--text-silver);cursor:pointer;">
                  <input type="checkbox" required style="margin-top:0.2rem;" />
                  <span>Accetto l&rsquo;<button type="button" onclick="openPrivacyModal()" style="background:none;border:none;color:var(--acos-yellow);text-decoration:underline;font-size:inherit;cursor:pointer;">Informativa Privacy GDPR</button> A.C.O.S. Treviglio.</span>
                </label>
                <div class="concierge-submit-row">
                  <button type="submit" class="btn-gold-broadcast">
                    ✉️ Invia Richiesta &rarr;
                  </button>
                </div>
              </form>
            </div>

            <!-- CENTRALINO ESECUTIVO A 3 RIGHE ORIZZONTALI (ORARI UFFICIALI + 1-CLICK CTA) -->
            <div class="switchboard-stack">
              <div class="switchboard-card">
                <div class="swc-info">
                  <span class="swc-tag">01 // SEGRETERIA &amp; SEDE (VIA AI MALGARI, 6)</span>
                  <div class="swc-main-val">0363 304036</div>
                  <div class="swc-meta">🕒 Orari: <strong>Lun&ndash;Ven 17:00&ndash;19:30 &bull; Sab 09:30&ndash;12:00</strong></div>
                </div>
                <a href="tel:0363304036" class="btn-card-outline swc-cta-btn">📞 Chiama</a>
              </div>

              <div class="switchboard-card">
                <div class="swc-info">
                  <span class="swc-tag">02 // RESP. SCUOLA CALCIO F.I.G.C.</span>
                  <div class="swc-main-val">Pierangelo Gusmini</div>
                  <div class="swc-meta">⭐ Vice Presidente &bull; Iscrizioni, Prove &amp; Open Day</div>
                </div>
                <button type="button" class="btn-card-gold swc-cta-btn" onclick="openWhatsAppInfo('Informazioni Scuola Calcio F.I.G.C. A.C.O.S. Treviglio')">💬 WhatsApp</button>
              </div>

              <div class="switchboard-card">
                <div class="swc-info">
                  <span class="swc-tag">03 // POSTA UFFICIALE, PEC &amp; DATI FISCALI</span>
                  <div class="swc-main-val">info@acos.it</div>
                  <div class="swc-meta">PEC: <strong>acostreviglio@pec.it</strong> &bull; P.IVA <strong>02115860161</strong> &bull; Matr. <strong style="color:var(--acos-yellow);">676164</strong></div>
                </div>
                <a href="mailto:info@acos.it" class="btn-card-outline swc-cta-btn">✉️ Email</a>
              </div>
            </div>
          </div>
          </div><!-- /#subpane-info-contatti -->

        </div>
      </div>
    </section>

    <!-- GLOBAL OFFICIAL CLUB PARTNERS BAR (MATRICE PARITARIA 5x2 PC / 2x5 MOBILE · 100% VISIBILITÀ SIMULTANEA) -->
    <section id="official-partners-section" class="section-block" style="background:#06080C;border-top:1px solid var(--acos-border-gold);">
      <div class="container">
        <div class="section-header" style="margin-bottom:1.5rem;">
          <div>
            <span class="section-eyebrow">Official Club Partners · A.S.D. A.C.O.S. Treviglio Calcio</span>
            <h2 class="section-title">Partner Ufficiali del Club</h2>
          </div>
          <button type="button" class="btn-ghost-broadcast" onclick="openPartnerInquiry()">
            Diventa Partner →
          </button>
        </div>
        <div class="sponsors-grid">
          {sponsors_html}
        </div>
      </div>
    </section>

    <!-- SERIE A TOP-LEVEL ARCHITECTURAL FOOTER (4 COLONNE ASIMMETRICHE, ZERO DOPPIONI, SEMPLICI LINK TIPOGRAFICI) -->
    <footer class="site-footer">
      <div class="footer-main-wrap">
        <div class="footer-grid">
          <!-- Colonna 1: Identità Club, Affiliazione & Icone Social Minimali -->
          <div class="footer-col-brand">
            <div class="club-brand" onclick="switchPage('page-home')" role="button" tabindex="0">
              {render_crest_badge('crest-footer')}
              <div class="club-brand-text">
                <span class="club-brand-title">A.C.O.S. <span>TREVIGLIO</span></span>
                <span class="club-brand-sub">FONDATA NEL 1971 • TREVIGLIO</span>
              </div>
            </div>
            <p class="footer-brand-desc">
              Scuola Calcio Riconosciuta F.I.G.C. e Partner Tecnico Settore Giovanile Atalanta B.C. Dal 1971 punto di riferimento sportivo ed educativo a Treviglio.
            </p>
            <div class="footer-social-row" aria-label="Canali Ufficiali A.C.O.S.">
              <a href="tel:0363304036" class="footer-social-icon" aria-label="Telefono Segreteria 0363 304036" title="Telefono Segreteria 0363 304036">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
              </a>
              <a href="mailto:info@acos.it" class="footer-social-icon" aria-label="Email Ufficiale info@acos.it" title="Email Ufficiale info@acos.it">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
              </a>
              <a href="{CLUB_DATA['instagram']}" target="_blank" rel="noopener noreferrer" class="footer-social-icon" aria-label="Instagram Ufficiale" title="Instagram @acostreviglio">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>
              </a>
              <a href="{CLUB_DATA['facebook']}" target="_blank" rel="noopener noreferrer" class="footer-social-icon" aria-label="Facebook Ufficiale" title="Facebook A.C.O.S. Treviglio">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>
              </a>
            </div>
          </div>

          <!-- Colonna 2: Navigazione Sito (Semplici Link Testuali) -->
          <div class="footer-col footer-col-nav">
            <h4>Esplora il Club</h4>
            <div class="footer-links">
              <a href="#home" onclick="switchPage('page-home'); return false;">Home</a>
              <a href="#squadre" onclick="switchPage('page-squadre', 'sq-organico'); return false;">Le 15 Squadre</a>
              <a href="#scuola" onclick="switchPage('page-squadre', 'sq-scuola'); return false;">Scuola Calcio &amp; Vitalis</a>
              <a href="#storia" onclick="switchPage('page-club', 'club-storia'); return false;">Il Club &amp; Storia 1971</a>
              <a href="#torneo" onclick="switchPage('page-squadre', 'sq-torneo'); return false;">Torneo Viganò &amp; Eventi</a>
              <a href="#official-partners-section" onclick="document.getElementById('official-partners-section').scrollIntoView({{behavior:'smooth'}}); return false;">Partner Ufficiali</a>
            </div>
          </div>

          <!-- Colonna 3: Segreteria, Documenti & Tutela F.I.G.C. -->
          <div class="footer-col">
            <h4>Tutela &amp; Documenti F.I.G.C.</h4>
            <div class="footer-links">
              <a href="#iscrizioni" onclick="switchPage('page-contatti', 'info-quote'); return false;">Iscrizioni, IBAN &amp; Visite</a>
              <a href="{CLUB_DATA['safeguarding_modello_url']}" target="_blank" rel="noopener noreferrer">Modello Safeguarding (PDF)</a>
              <a href="{CLUB_DATA['safeguarding_codice_url']}" target="_blank" rel="noopener noreferrer">Codice di Condotta (PDF)</a>
              <a href="{CLUB_DATA['remels_url']}" target="_blank" rel="noopener noreferrer">Store Kit Ufficiale Remels</a>
              <button type="button" class="footer-text-link" onclick="openPrivacyModal()">Privacy &amp; Cookie Policy GDPR</button>
            </div>
          </div>

          <!-- Colonna 4: Sede & Contatti Diretti -->
          <div class="footer-col">
            <h4>Sede &amp; Contatti Ufficiali</h4>
            <div class="footer-links">
              <a href="#sede" onclick="switchPage('page-contatti', 'info-contatti'); return false;">Via ai Malgari — Treviglio (BG)</a>
              <a href="tel:0363304036">Tel. 0363 304036</a>
              <a href="mailto:info@acos.it">info@acos.it</a>
              <a href="mailto:acostreviglio@pec.it">PEC: acostreviglio@pec.it</a>
              <span class="footer-meta-item">Lun–Ven 17:00–19:30 · Sab 09:30–12:00</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Band 3: Copyright, P.IVA & Matricola F.I.G.C. strutturati su più righe ordinate -->
      <div class="footer-bottom-ribbon">
        <div class="footer-bottom-inner">
          <div class="footer-legal-line-1">
            © 1971–2026 A.S.D. A.C.O.S. TREVIGLIO CALCIO
          </div>
          <div class="footer-legal-line-2">
            <span>P.IVA 02115860161</span>
            <span class="ribbon-dot" style="color:var(--acos-yellow);">•</span>
            <span>Matricola F.I.G.C. 676164</span>
          </div>
          <div class="footer-legal-line-3">
            <span>PEC: acostreviglio@pec.it</span>
            <span class="ribbon-dot">•</span>
            <span>Affiliazione F.I.G.C. / L.N.D. Lombardia</span>
          </div>
        </div>
      </div>
    </footer>

    <!-- MOBILE BOTTOM DOCK (4 PILASTRI UFFICIALI — SERIE A ULTRA-LIGHT APP NAVIGATION) -->
    <nav class="mobile-bottom-dock" aria-label="Navigazione Mobile">
      <button type="button" class="dock-btn active" data-dock="page-home" onclick="switchPage('page-home')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5.5v-6h-5v6H4a1 1 0 0 1-1-1v-9.5z"/></svg>
        <span>HOME</span>
      </button>
      <button type="button" class="dock-btn" data-dock="page-squadre" onclick="switchPage('page-squadre')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2l7 4v6c0 5-3.5 9.5-7 10-3.5-.5-7-5-7-10V6l7-4z"/></svg>
        <span>SQUADRE</span>
      </button>
      <button type="button" class="dock-btn" data-dock="page-club" onclick="switchPage('page-club')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>
        <span>IL CLUB</span>
      </button>
      <button type="button" class="dock-btn" data-dock="page-contatti" onclick="switchPage('page-contatti')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span>INFO &amp; SEDE</span>
      </button>
    </nav>

  </div><!-- /#viewport-stage -->

  <!-- MODALS -->
  <div id="team-modal" class="modal-backdrop" role="dialog" aria-modal="true" onclick="if(event.target===this)closeTeamModal()">
    <div class="modal-dialog">
      <button type="button" class="modal-close" onclick="closeTeamModal()">✕</button>
      <div id="team-modal-body"></div>
    </div>
  </div>

  <div id="lightbox-modal" class="modal-backdrop" role="dialog" aria-modal="true" onclick="if(event.target===this)closeLightbox()">
    <div class="modal-dialog" style="max-width:920px;text-align:center;">
      <button type="button" class="modal-close" onclick="closeLightbox()">✕</button>
      <img id="lightbox-img" src="" alt="" style="max-height:74vh;margin:0 auto;border-radius:10px;" />
      <p id="lightbox-caption" style="margin-top:0.85rem;color:var(--acos-yellow);font-weight:800;"></p>
    </div>
  </div>

  <div id="privacy-modal" class="modal-backdrop" role="dialog" aria-modal="true" onclick="if(event.target===this)closePrivacyModal()">
    <div class="modal-dialog">
      <button type="button" class="modal-close" onclick="closePrivacyModal()">✕</button>
      <span class="section-eyebrow">Regolamento UE 2016/679 (GDPR)</span>
      <h3 style="font-family:var(--font-display);font-size:1.85rem;text-transform:uppercase;margin-bottom:0.75rem;">
        Informativa Privacy & Tutela Minori
      </h3>
      <p style="font-size:0.88rem;color:var(--text-silver);">
        <strong>Titolare del Trattamento:</strong> A.S.D. A.C.O.S. Treviglio Calcio — Via ai Malgari, 6 – 24047 Treviglio (BG) — C.F./P.IVA 02115860161 — Email: info@acos.it. I dati sono trattati esclusivamente per finalità sportive, assicurative e di tesseramento FIGC/LND.
      </p>
    </div>
  </div>

  <div id="mobile-drawer" class="modal-backdrop" onclick="if(event.target===this)toggleMobileDrawer()">
    <div class="modal-dialog" style="max-width:380px;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:0.75rem;padding-bottom:0.85rem;margin-bottom:0.9rem;border-bottom:1px solid rgba(255,255,255,0.1);">
        <div style="display:flex;align-items:center;gap:0.65rem;">
          {render_crest_badge('crest-footer')}
          <div>
            <div style="font-family:var(--font-display);font-size:1.25rem;font-weight:900;line-height:0.95;text-transform:uppercase;color:var(--text-white);">A.C.O.S. <span style="color:var(--acos-yellow);">TREVIGLIO</span></div>
            <div style="font-family:var(--font-mono);font-size:0.55rem;color:var(--text-silver);font-weight:700;letter-spacing:0.06em;margin-top:0.15rem;">FONDATA NEL 1971 • TREVIGLIO</div>
          </div>
        </div>
        <button type="button" class="modal-close" style="float:none;" onclick="toggleMobileDrawer()">✕</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:0.45rem;">
        <button type="button" class="drawer-nav-btn active" data-drawer-target="page-home" onclick="switchPage('page-home');toggleMobileDrawer()">
          <span><span class="drawer-nav-idx">01</span>Home</span><span>→</span>
        </button>
        <button type="button" class="drawer-nav-btn" data-drawer-target="page-squadre" onclick="switchPage('page-squadre');toggleMobileDrawer()">
          <span><span class="drawer-nav-idx">02</span>Squadre &amp; Scuola</span><span>→</span>
        </button>
        <button type="button" class="drawer-nav-btn" data-drawer-target="page-club" onclick="switchPage('page-club');toggleMobileDrawer()">
          <span><span class="drawer-nav-idx">03</span>Il Club</span><span>→</span>
        </button>
        <button type="button" class="drawer-nav-btn" data-drawer-target="page-contatti" onclick="switchPage('page-contatti');toggleMobileDrawer()">
          <span><span class="drawer-nav-idx">04</span>Info &amp; Sede</span><span>→</span>
        </button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.45rem;margin-top:0.9rem;padding-top:0.85rem;border-top:1px solid rgba(255,255,255,0.1);">
        <a href="tel:0363304036" class="btn-card-outline" style="text-align:center;font-size:0.78rem;padding:0.5rem 0.35rem;">📞 Sede 0363 304036</a>
        <a href="mailto:info@acos.it?subject=Richiesta%20Informazioni%20-%20A.S.D.%20A.C.O.S.%20Treviglio" class="btn-card-gold" style="text-align:center;font-size:0.78rem;padding:0.5rem 0.35rem;text-decoration:none;">✉️ Email Segreteria</a>
      </div>
    </div>
  </div>

  <script>
    const TEAMS_DATA = {teams_json};

    // Hero Background Slider & Interactive Stadium Spotlight
    let currentSlide = 0;
    let heroSlideTimer = null;

    function setHeroSlide(idx) {{
      currentSlide = idx;
      document.querySelectorAll('.hero-slide-bg').forEach((el, i) => {{
        el.classList.toggle('active', i === idx);
      }});
      if (heroSlideTimer) clearInterval(heroSlideTimer);
      heroSlideTimer = setInterval(() => {{
        setHeroSlide((currentSlide + 1) % 3);
      }}, 6500);
    }}

    heroSlideTimer = setInterval(() => {{
      setHeroSlide((currentSlide + 1) % 3);
    }}, 6500);

    function switchSubPane(group, paneId, btnEl) {{
      document.querySelectorAll(`.subpane-view[data-sub-group="${{group}}"]`).forEach(el => {{
        el.classList.toggle('active', el.id === 'subpane-' + paneId);
      }});
      document.querySelectorAll(`.acos-subnav-pill[data-sub-group="${{group}}"]`).forEach(btn => {{
        btn.classList.toggle('active', btn === btnEl || btn.getAttribute('data-subpane') === paneId);
      }});
    }}

    function switchPage(pageId, subPaneId) {{
      if (pageId === 'page-scuola') {{ pageId = 'page-squadre'; subPaneId = subPaneId || 'sq-scuola'; }}
      if (pageId === 'page-segreteria') {{ pageId = 'page-contatti'; subPaneId = subPaneId || 'info-quote'; }}
      if (pageId === 'page-societa') {{ pageId = 'page-club'; subPaneId = subPaneId || 'club-storia'; }}
      if (pageId === 'page-eventi') {{ pageId = 'page-club'; subPaneId = subPaneId || 'club-eventi'; }}
      if (pageId === 'page-sponsor') {{ pageId = 'page-club'; subPaneId = subPaneId || 'club-sponsor'; }}
      if (subPaneId === 'sq-rose') subPaneId = 'sq-organico';
      if (subPaneId === 'info-sede') subPaneId = 'info-contatti';
      document.querySelectorAll('.page-view').forEach(el => el.classList.remove('active'));
      const target = document.getElementById(pageId);
      if (target) target.classList.add('active');
      if (subPaneId) {{
        const grp = pageId === 'page-squadre' ? 'squadre' : (pageId === 'page-club' ? 'club' : 'info');
        switchSubPane(grp, subPaneId, null);
      }}
      document.querySelectorAll('.nav-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-target') === pageId);
      }});
      document.querySelectorAll('.dock-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-dock') === pageId);
      }});
      document.querySelectorAll('.drawer-nav-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-drawer-target') === pageId);
      }});
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function filterRoster(macro, chipEl) {{
      if (chipEl) {{
        chipEl.parentElement.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        chipEl.classList.add('active');
      }}
      document.querySelectorAll('#roster-cards-container .sector-showcase-band').forEach(card => {{
        const cm = card.getAttribute('data-macro');
        card.style.display = (macro === 'all' || cm === macro) ? 'grid' : 'none';
      }});
    }}

    function jumpToRosterMacro(macro) {{
      switchPage('page-squadre', 'sq-organico');
      const chips = document.querySelectorAll('#page-squadre .filter-chip');
      const idx = macro === 'agonistica' ? 1 : (macro === 'base' ? 2 : (macro === 'scuola' ? 3 : 0));
      filterRoster(macro, chips[idx] || null);
    }}

    function openTeamModal(teamId) {{
      const t = TEAMS_DATA.find(x => x.id === Number(teamId) || x.code === teamId || x.id === teamId);
      if (!t) return;
      const formatLabel = t.macro === 'agonistica'
        ? 'Calcio a 11 · Girone Stagionale LND / F.I.G.C.'
        : (t.name.includes('Esordienti')
            ? 'Calcio a 9 · Tornei Federali F.I.G.C. SGS'
            : (t.name.includes('Pulcini')
                ? 'Calcio a 7 · Sviluppo Tecnico F.I.G.C. SGS'
                : 'Scuola Calcio Riconosciuta F.I.G.C. · Metodologia Atalanta B.C.'));
      const feeLabel = (t.id === 1 || t.id === 2)
        ? 'Tesseramento L.N.D. Lombardia'
        : 'Kit Ufficiale Remels + Tesseramento F.I.G.C.';
      const medLabel = (t.id <= 7)
        ? 'Visita Medica Agonistica Gratuita (con richiesta timbrata in Segreteria)'
        : 'Certificato Medico Non Agonistico (Pediatra o Medico Sportivo)';
      const primaryActionHtml = (t.macro === 'scuola')
        ? `<button type="button" class="btn-gold-broadcast" onclick="openWhatsAppInfo('${{t.name}} (${{t.annata}})')">💬 WhatsApp Scuola Calcio (P. Gusmini) →</button>`
        : `<a href="tel:0363304036" class="btn-gold-broadcast" style="text-decoration:none;">📞 Chiama Segreteria (0363 304036)</a>`;

      document.getElementById('team-modal-body').innerHTML = `
        <span class="spc-macro-badge">${{t.macro_label}}</span>
        <h3 style="font-family:var(--font-display);font-size:2.1rem;text-transform:uppercase;margin:0.4rem 0;">
          ${{t.name}} (Annata ${{t.annata}})
        </h3>
        <p style="color:var(--text-silver);font-size:0.92rem;margin-bottom:1rem;">${{t.desc}}</p>
        <div class="spc-data-grid">
          <div class="spc-data-row"><span class="spc-label">Campionato / Attività</span><span class="spc-val">${{t.campionato}}</span></div>
          <div class="spc-data-row"><span class="spc-label">Anno di Nascita</span><span class="spc-val">Classe ${{t.annata}}</span></div>
          <div class="spc-data-row"><span class="spc-label">Formula Tecnica</span><span class="spc-val">${{formatLabel}}</span></div>
          <div class="spc-data-row"><span class="spc-label">Campo di Allenamento</span><span class="spc-val">${{t.allenamenti}}</span></div>
          <div class="spc-data-row"><span class="spc-label">Dotazione & Tesseramento</span><span class="spc-val" style="color:var(--acos-yellow);">${{feeLabel}}</span></div>
          <div class="spc-data-row"><span class="spc-label">Certificato Medico</span><span class="spc-val">${{medLabel}}</span></div>
        </div>
        <div style="display:flex;gap:0.65rem;flex-wrap:wrap;margin-top:1.25rem;">
          ${{primaryActionHtml}}
          <button type="button" class="btn-ghost-broadcast" onclick="closeTeamModal();switchPage('page-contatti', 'info-quote')">📋 Iscrizioni &amp; Segreteria →</button>
        </div>
      `;
      document.getElementById('team-modal').classList.add('open');
    }}

    function closeTeamModal() {{ document.getElementById('team-modal').classList.remove('open'); }}
    function openLightbox(src, caption) {{
      document.getElementById('lightbox-img').src = src;
      document.getElementById('lightbox-caption').textContent = caption || '';
      document.getElementById('lightbox-modal').classList.add('open');
    }}
    function closeLightbox() {{ document.getElementById('lightbox-modal').classList.remove('open'); }}
    function openPrivacyModal() {{ document.getElementById('privacy-modal').classList.add('open'); }}
    function closePrivacyModal() {{ document.getElementById('privacy-modal').classList.remove('open'); }}
    function toggleMobileDrawer() {{ document.getElementById('mobile-drawer').classList.toggle('open'); }}

    let viganoSlideIdx = 0;
    function stepViganoPhoto(delta) {{
      const grid = document.getElementById('vigano-gallery-grid');
      if (!grid) return;
      const slides = grid.querySelectorAll('.gallery-thumb');
      if (!slides.length) return;
      viganoSlideIdx = (viganoSlideIdx + delta + slides.length) % slides.length;
      slides.forEach((el, idx) => {{
        el.classList.toggle('is-active-slide', idx === viganoSlideIdx);
      }});
      const lbl = document.getElementById('vigano-slide-label');
      if (lbl) {{
        lbl.innerHTML = slides[viganoSlideIdx].getAttribute('data-slide-label') || `FOTO ${{viganoSlideIdx + 1}} / ${{slides.length}}`;
      }}
      const dots = document.querySelectorAll('#vigano-slider-dots .v-dot');
      dots.forEach((d, idx) => d.classList.toggle('active', idx === viganoSlideIdx));
    }}

    const clubSliderState = {{}};
    function stepMobileClubSlide(containerId, itemSelector, labelId, dotsId, delta) {{
      const container = document.getElementById(containerId);
      if (!container) return;
      const slides = container.querySelectorAll(itemSelector);
      if (!slides.length) return;
      const cur = clubSliderState[containerId] || 0;
      const next = (cur + delta + slides.length) % slides.length;
      clubSliderState[containerId] = next;
      slides.forEach((el, idx) => {{
        el.classList.toggle('is-active-slide', idx === next);
      }});
      const lbl = document.getElementById(labelId);
      if (lbl) {{
        lbl.innerHTML = slides[next].getAttribute('data-slide-label') || `SCHEDA ${{next + 1}} / ${{slides.length}}`;
      }}
      if (dotsId) {{
        const dots = document.querySelectorAll(`#${{dotsId}} .v-dot`);
        dots.forEach((d, idx) => d.classList.toggle('active', idx === next));
      }}
    }}

    function copyIban() {{
      const ibanClean = "{CLUB_DATA['iban_clean']}";
      if (navigator.clipboard) navigator.clipboard.writeText(ibanClean);
      const btn = document.getElementById('copy-iban-btn');
      if (btn) {{
        btn.textContent = '✓ Codice IBAN Copiato!';
        setTimeout(() => {{ btn.textContent = '📋 Copia Codice IBAN'; }}, 2500);
      }}
    }}

    function copyCausale() {{
      const schema = "COGNOME NOME ATLETA • ANNATA • QUOTA 2025/2026";
      if (navigator.clipboard) navigator.clipboard.writeText(schema);
      const btn = document.getElementById('copy-causale-btn');
      if (btn) {{
        btn.textContent = '✓ Schema Causale Copiato!';
        setTimeout(() => {{ btn.textContent = '✍️ Copia Schema Causale'; }}, 2500);
      }}
    }}

    const CONTACT_PROFILES = {{
      atleta: {{
        typeLabel: 'Atleta / Tesseramento',
        nameLabel: 'Nome e Cognome (Atleta o Referente) *',
        namePlaceholder: 'Es. Marco Rossi',
        yearLabel: 'Categoria / Fascia d’Interesse',
        msgLabel: 'Dettagli della Richiesta',
        msgPlaceholder: 'Indica qui l’annata di nascita, eventuale ruolo o richiesta di prova...',
        options: [
          ['Prima Squadra Promozione / Juniores U19 Élite', 'Promozione & Juniores U19 Élite'],
          ['Agonistica Allievi & Giovanissimi U14-U17 (2009-2012)', 'Agonistica U14–U17 (2009–2012)'],
          ['Attività di Base Esordienti & Pulcini (2013-2016)', 'Esordienti & Pulcini (2013–2016)'],
          ['Scuola Calcio Primi Calci & Piccoli Amici (2017-2020)', 'Scuola Calcio 5–8 Anni (2017–2020)']
        ]
      }},
      sponsor: {{
        typeLabel: 'Azienda / Sponsor & Partnership',
        nameLabel: 'Ragione Sociale Azienda & Referente *',
        namePlaceholder: 'Es. Rossi S.r.l. — Dott. Marco Rossi',
        yearLabel: 'Formula di Partnership d’Interesse',
        msgLabel: 'Proposta o Obiettivo di Visibilità',
        msgPlaceholder: 'Indica se desideri ricevere la brochure sponsorizzazioni o fissare un incontro in sede...',
        options: [
          ['Main / Jersey Sponsor Maglie da Gioco', 'Main Sponsor Maglie da Gioco'],
          ['Sponsor Stadio Zanconti & C.S. Ambrogio Mazza', 'Cartellonistica Stadio & C.S. Mazza'],
          ['Partner Torneo Primaverile Viganò – Mem. Riganti', 'Partner Torneo Primaverile Viganò'],
          ['Fornitura Tecnica / Convenzione Tesserati', 'Partner Tecnico / Convenzioni']
        ]
      }},
      societa: {{
        typeLabel: 'Società Sportiva / Tornei & Amichevoli',
        nameLabel: 'Società Sportiva & Nome Dirigente/DS *',
        namePlaceholder: 'Es. A.S.D. Calcio — Dir. Sportivo',
        yearLabel: 'Ambito Tecnico / Organizzativo',
        msgLabel: 'Proposta Tecnica (Data / Categoria)',
        msgPlaceholder: 'Specifica la categoria coinvolta e la proposta di gara amichevole o iscrizione torneo...',
        options: [
          ['Iscrizione Torneo Primaverile Stefano Viganò', 'Torneo Primaverile Stefano Viganò'],
          ['Richiesta Gara Amichevole / Test Match', 'Gara Amichevole / Test Match'],
          ['Scouting / Osservatori & Collaborazione Tecnica', 'Scouting & Collaborazione Tecnica'],
          ['Comunicazione Ufficiale Segreteria FIGC / LND', 'Comunicazione Segreteria FIGC / LND']
        ]
      }},
      segreteria: {{
        typeLabel: 'Segreteria Amministrativa & Servizi',
        nameLabel: 'Nome e Cognome Richiedente *',
        namePlaceholder: 'Es. Laura Bianchi',
        yearLabel: 'Servizio di Segreteria Richiesto',
        msgLabel: 'Note per l’Ufficio di Segreteria',
        msgPlaceholder: 'Indica il nome del tesserato e il documento o supporto richiesto...',
        options: [
          ['Quote Iscrizione, Bonifico IBAN & Ricevute Fiscali', 'Quote, IBAN & Ricevute Fiscali'],
          ['Richiesta Modulo Visita Medica Agonistica / Non Agon.', 'Visite Mediche & Idoneità Sportiva'],
          ['Ordine Kit Sportivo Ufficiale Remels Sport', 'Kit Ufficiale Remels Sport'],
          ['Apertura Sinistro Assicurativo LND / FIGC SGS', 'Sinistro Assicurativo LND / SGS']
        ]
      }}
    }};

    function selectContactProfile(profileKey, btnEl) {{
      const p = CONTACT_PROFILES[profileKey];
      if (!p) return;
      document.querySelectorAll('.cf-profile-tab').forEach(b => {{
        b.classList.toggle('active', b === btnEl || b.getAttribute('data-cf-profile') === profileKey);
      }});
      document.getElementById('cf-profile-type').value = p.typeLabel;
      document.getElementById('cf-name-label').textContent = p.nameLabel;
      document.getElementById('cf-name').placeholder = p.namePlaceholder;
      document.getElementById('cf-year-label').textContent = p.yearLabel;
      document.getElementById('cf-msg-label').textContent = p.msgLabel;
      document.getElementById('cf-msg').placeholder = p.msgPlaceholder;
      const sel = document.getElementById('cf-year');
      sel.innerHTML = p.options.map(o => `<option value="${{o[0]}}">${{o[1]}}</option>`).join('');
    }}

    function openPartnerInquiry() {{
      switchPage('page-contatti', 'info-contatti');
      selectContactProfile('sponsor', null);
      setTimeout(() => {{
        const stage = document.getElementById('contact-concierge-stage');
        if (stage) stage.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}, 140);
    }}

    function openWhatsAppInfo(teamName) {{
      const text = encodeURIComponent(`Buongiorno A.C.O.S. Treviglio, vorrei informazioni per: ${{teamName}} (Stagione 2025/2026).`);
      window.open(`https://wa.me/{CLUB_DATA['scuola_mobile_clean']}?text=${{text}}`, '_blank', 'noopener,noreferrer');
    }}

    function submitContactForm(e) {{
      e.preventDefault();
      const profileType = document.getElementById('cf-profile-type') ? document.getElementById('cf-profile-type').value : 'Contatto Sito';
      const name = document.getElementById('cf-name').value.trim();
      const year = document.getElementById('cf-year').value;
      const phone = document.getElementById('cf-phone').value.trim();
      const msg = document.getElementById('cf-msg').value.trim();
      const subject = encodeURIComponent(`[Sito A.C.O.S. Treviglio] ${{profileType}} — ${{name || 'Richiesta Info'}}`);
      const body = encodeURIComponent(
        `Buongiorno Segreteria A.C.O.S. Treviglio,\\n\\nProfilo: ${{profileType}}\\nReferente: ${{name || '-'}}\\nTelefono: ${{phone || '-'}}\\nAmbito / Categoria: ${{year}}\\n\\nMessaggio:\\n${{msg || 'Vorrei essere ricontattato per maggiori informazioni.'}}`
      );
      window.location.href = `mailto:info@acos.it?subject=${{subject}}&body=${{body}}`;
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') {{
        closeTeamModal();
        closeLightbox();
        closePrivacyModal();
        document.getElementById('mobile-drawer').classList.remove('open');
      }}
    }});
  </script>
</body>
</html>
"""


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    target_script = BASE_DIR / "build_acos_cinematic.py"
    if Path(__file__).resolve() != target_script.resolve():
        shutil.copy2(__file__, target_script)
    crest_uri = extract_transparent_oval_crest()
    print(f"[OK] Stemma Ovale Ufficiale A.C.O.S. estratto e scontornato ({len(crest_uri)} bytes data URI)")

    html_live = build_html(embed_base64=False, crest_data_uri=crest_uri)
    INDEX_OUT.write_text(html_live, encoding="utf-8")
    print(f"[OK] Generato {INDEX_OUT} ({INDEX_OUT.stat().st_size / 1024:.1f} KB)")

    html_sim = build_html(embed_base64=True, crest_data_uri=crest_uri)
    SIM_OUT.write_text(html_sim, encoding="utf-8")
    (Path(__file__).resolve().parent / "header_preview.html").write_text(html_sim, encoding="utf-8")
    print(f"[OK] Generato {SIM_OUT} ({SIM_OUT.stat().st_size / (1024*1024):.2f} MB — Standalone Base64)")

    public_dir = BASE_DIR.parent / "app" / "public"
    if public_dir.exists() and BASE_DIR.parent.name in ("calcio", "acos"):
        acos_pub = public_dir / "acos"
        acos_pub_assets = acos_pub / "assets"
        acos_pub_assets.mkdir(parents=True, exist_ok=True)
        for img_f in ASSETS_DIR.glob("*.*"):
            if img_f.suffix.lower() in (".jpg", ".png"):
                shutil.copy2(img_f, acos_pub_assets / img_f.name)
        (acos_pub / "index.html").write_text(html_live, encoding="utf-8")
        html_wp = (
            html_live.replace('"assets/', '"/acos/assets/')
            .replace("'assets/", "'/acos/assets/")
        )
        mu_dir = public_dir / "wp-content" / "mu-plugins"
        mu_dir.mkdir(parents=True, exist_ok=True)
        mu_tpl = mu_dir / "acos-cinematic-template.html"
        mu_tpl.write_text(html_wp, encoding="utf-8")
        print(f"[OK] Sincronizzato con Local.app in {mu_tpl}")

    candidate_repos = [
        BASE_DIR / "gh-pages",
        Path(__file__).resolve().parent / "acos-gh-pages",
    ]
    for gh_repo_dir in candidate_repos:
        if (gh_repo_dir / ".git").exists():
            (gh_repo_dir / "index.html").write_text(html_sim, encoding="utf-8")
            shutil.copy2(__file__, gh_repo_dir / "build_acos_cinematic.py")
            status_proc = subprocess.run(
                ["git", "-C", str(gh_repo_dir), "status", "--porcelain"],
                capture_output=True,
                text=True,
            )
            if status_proc.stdout.strip():
                subprocess.run(["git", "-C", str(gh_repo_dir), "add", "index.html", "build_acos_cinematic.py"], check=False)
                subprocess.run(
                    ["git", "-C", str(gh_repo_dir), "commit", "-m", "Aggiornamento portale A.C.O.S. Treviglio Calcio 1971"],
                    check=False,
                )
                push_proc = subprocess.run(
                    ["git", "-C", str(gh_repo_dir), "push", "origin", "main"],
                    capture_output=True,
                    text=True,
                )
                if push_proc.returncode == 0:
                    print("[OK] Pubblicato automaticamente su GitHub Pages: https://mircoantonaci.github.io/acos-treviglio/")
                else:
                    print(f"[INFO] Commit locale pronto in {gh_repo_dir}; esegui git push per aggiornare GitHub Pages.")
            else:
                print(f"[OK] Repository GitHub Pages già allineato in {gh_repo_dir}.")
            break


if __name__ == "__main__":
    main()
