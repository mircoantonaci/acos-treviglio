# AGENTS.md — A.S.D. A.C.O.S. Treviglio Calcio 1971 (CLI, WordPress & GitHub Pages Context)

> **Progetto:** A.S.D. A.C.O.S. Treviglio Calcio — Fondata il 18 Agosto 1971 (v5.0 Top-Club Broadcast Edition)
> **Sede:** Via Monte Grappa snc (Stadio "Ambrogio Mazza") & Viale Merisio 17 (Centro Sportivo "San Pietro"), 24047 Treviglio (BG)
> **Root Progetto Indipendente:** `/Users/antonacim/Local Sites/calcio`
> **Link Pubblico Permanente (GitHub Pages H24):** `https://mircoantonaci.github.io/acos-treviglio/`

Questo file fornisce la memoria architetturale permanente e autonoma per **Antigravity IDE** e **Antigravity CLI (`agy`)**. Aprendo una sessione in `/Users/antonacim/Local Sites/calcio`, l'agente conosce immediatamente l'intera struttura senza dipendere da alcuna conversazione passata e mantenendo totale separazione dal progetto `gastronomia`.

---

## 1. Comandi Rapidi CLI (`acos-cli.py`)
Il progetto è gestito tramite lo strumento CLI [`acos-cli.py`](file:///Users/antonacim/Local%20Sites/calcio/acos-cli.py) situato nella root `/Users/antonacim/Local Sites/calcio`:

- **Rigenera il sito WordPress locale, i file HTML e aggiorna automaticamente GitHub Pages:**
  ```bash
  python3 acos-cli.py build
  ```
- **Forza la pubblicazione / push sul repository GitHub Pages (`https://mircoantonaci.github.io/acos-treviglio/`):**
  ```bash
  python3 acos-cli.py deploy
  ```
- **Controlla lo stato di file locali, server Local.app (`127.0.0.1:10013` / `calcio.local`) e GitHub Pages:**
  ```bash
  python3 acos-cli.py status
  ```
- **Esporta il pacchetto ZIP pronto per hosting esterno (`acos-studio/dist/acos-treviglio-deploy.zip`):**
  ```bash
  python3 acos-cli.py export
  ```

---

## 2. Architettura dei File del Progetto (`/Users/antonacim/Local Sites/calcio`)
- **Sorgenti, Generatore & GitHub Pages (`acos-studio/`):**
  - [`acos-studio/build_acos_cinematic.py`](file:///Users/antonacim/Local%20Sites/calcio/acos-studio/build_acos_cinematic.py): Generatore master Python (v5.0) che contiene l'intero design system giallonero, le 15 squadre (dalla Prima Squadra Promozione ai Piccoli Amici 2020), la Scuola Calcio Élite (Affiliazione Atalanta B.C., Progetto Vitalis, Torneo Viganò), la Storia dal 1971, Gothia Cup, Cuore Giallonero (18 ONLUS) e la Segreteria Digitale (Calcolatore Quote, IBAN, Safeguarding D.Lgs. 36/2021 e 39/2021).
  - [`acos-studio/index.html`](file:///Users/antonacim/Local%20Sites/calcio/acos-studio/index.html): Sito web statico collegato alla cartella fotografica [`acos-studio/assets/`](file:///Users/antonacim/Local%20Sites/calcio/acos-studio/assets).
  - [`acos-studio/simulazione_acos.html`](file:///Users/antonacim/Local%20Sites/calcio/acos-studio/simulazione_acos.html): Versione standalone autonoma (`5.5 MB`) con tutte le 26 fotografie e lo stemma ovale incorporati in Base64.
  - [`acos-studio/gh-pages/`](file:///Users/antonacim/Local%20Sites/calcio/acos-studio/gh-pages/index.html): Repository Git locale collegato a `https://github.com/mircoantonaci/acos-treviglio.git` che alimenta il link pubblico `https://mircoantonaci.github.io/acos-treviglio/`.
- **WordPress Live (`app/public/`):**
  - [`app/public/wp-content/mu-plugins/acos-cinematic-portal.php`](file:///Users/antonacim/Local%20Sites/calcio/app/public/wp-content/mu-plugins/acos-cinematic-portal.php): MU-Plugin WordPress per il rendering istantaneo del portale.
  - [`app/public/wp-content/mu-plugins/acos-cinematic-template.html`](file:///Users/antonacim/Local%20Sites/calcio/app/public/wp-content/mu-plugins/acos-cinematic-template.html): Template HTML/CSS/JS servito da Local.app.

---

## 3. Parametri Tecnici Local.app & GitHub Pages
- **Local.app Site ID:** `Ac0sTrv71`
- **URL Sito Locale:** `http://127.0.0.1:10013/` oppure `http://calcio.local/`
- **Repository GitHub:** `https://github.com/mircoantonaci/acos-treviglio` (branch `main`, root `/`)
- **URL Pubblico H24 (Condiviso con Presidente e Direttivo):** `https://mircoantonaci.github.io/acos-treviglio/`

---

## 4. Regole Architetturali e Design System
1. **Zero Risultati Domenicali / Classifiche Statiche:** Il portale adotta un'architettura istituzionale evergreen (zero risultati domenicali o classifiche che invecchiano). Non reintrodurre tabellini o punteggi settimanali.
2. **Modifiche Centralizzate:** Qualsiasi modifica a testi, foto, squadre, quote o colori va applicata in [`acos-studio/build_acos_cinematic.py`](file:///Users/antonacim/Local%20Sites/calcio/acos-studio/build_acos_cinematic.py) eseguendo poi `python3 acos-cli.py build` per aggiornare in un solo colpo WordPress locale, file statici e GitHub Pages (`https://mircoantonaci.github.io/acos-treviglio/`).
3. **Separazione Totale:** Non toccare mai i file di `/Users/antonacim/Local Sites/gastronomia`.
