#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica la coerenza tra modello dati (sharepoint/schema.yaml), flussi
(powerautomate/flows/*.json) e app (powerapps/src/*.pa.yaml).

    python strumenti/verifica_coerenza.py

Controlli:
  flussi  - JSON valido; connettori solo standard; runAfter e riferimenti body()/outputs()
            verso azioni esistenti; colonne usate in item/<Col>, $filter, $orderby esistenti
            nella lista indicata; etichette degli stati valide; numero di parametri del
            trigger Power Apps uguale al contratto (docs/06-api-flussi.md)
  app     - YAML valido; chiamate SDF_APIxx.Run(...) verso flussi esistenti e con il numero
            di argomenti del contratto; etichette degli stati confrontate con lo schema;
            nomi di colonna tra apici esistenti nello schema (avviso)
Esce con codice 1 se trova errori.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCHEMA = yaml.safe_load((REPO / "sharepoint" / "schema.yaml").read_text(encoding="utf-8"))

# Parametri posizionali dei flussi API (docs/06-api-flussi.md)
CONTRATTO = {
    "SDF_API01_Profilo": 0, "SDF_API02_MieRichieste": 1, "SDF_API03_SalvaRichiesta": 6,
    "SDF_API04_AggiornaProfilo": 3, "SDF_API05_RichiesteTeam": 2, "SDF_API06_EsitoCoordinatore": 5,
    "SDF_API07_EsitoHR": 1, "SDF_API08_ChiusuraMensile": 4, "SDF_API09_FilePaghe": 2,
    "SDF_API10_DettaglioRichiesta": 1,
}
FLUSSI_ATTESI = set(CONTRATTO) | {"SDF_F4_Promemoria", "SDF_F5_RiepilogoMensile", "SDF_F7_AllineaLavoratore",
                                  "SDF_F9_SincronizzaRuoli", "SDF_F9b_RuoloEliminato"}
CONNETTORI_STANDARD = {"shared_sharepointonline", "shared_office365", "shared_office365users"}
COLONNE_SISTEMA = {"ID", "Id", "Title", "Created", "Modified", "Author", "Editor", "FileLeafRef", "FileRef",
                   "FSObjType", "ContentType", "Attachments", "GUID", "LinkTitle", "LinkFilename", "DocIcon"}

STATI = set(SCHEMA["choices"]["stato_richiesta"])
TUTTE_LE_SCELTE = {v for vals in SCHEMA["choices"].values() for v in vals}
LISTE = {}          # titolo lista -> set nomi interni
DISPLAY = set()     # tutti i nomi visualizzati (Power Fx)
for lname, lst in SCHEMA["lists"].items():
    LISTE[lst["title"]] = {c["name"] for c in lst["columns"]} | COLONNE_SISTEMA
    DISPLAY |= {c["display_name"] for c in lst["columns"]}
    DISPLAY.add(lst["title"])
    if lst.get("title_display"):
        DISPLAY.add(lst["title_display"])

errori: list[str] = []
avvisi: list[str] = []


def err(msg: str) -> None:
    errori.append(msg)


def warn(msg: str) -> None:
    avvisi.append(msg)


# =============================================================================
#  Flussi
# =============================================================================
def azioni_ricorsive(actions: dict, prefisso: str = ""):
    """Restituisce (nome, azione, dizionario dei fratelli) per ogni azione, anche annidata."""
    for nome, az in (actions or {}).items():
        yield nome, az, actions
        for chiave in ("actions",):
            if isinstance(az.get(chiave), dict):
                yield from azioni_ricorsive(az[chiave])
        if isinstance(az.get("else"), dict) and isinstance(az["else"].get("actions"), dict):
            yield from azioni_ricorsive(az["else"]["actions"])
        if isinstance(az.get("cases"), dict):
            for caso in az["cases"].values():
                yield from azioni_ricorsive(caso.get("actions", {}))
        if isinstance(az.get("default"), dict):
            yield from azioni_ricorsive(az["default"].get("actions", {}))


def colonne_in_filtro(expr: str) -> set[str]:
    # identificatori a sinistra di eq/ne/gt/lt/ge/le, esclusi i valori tra apici
    senza_stringhe = re.sub(r"'[^']*'", "''", expr)
    senza_espr = re.sub(r"@\{[^}]*\}", "X", senza_stringhe)
    return {m for m in re.findall(r"([A-Za-z_][A-Za-z0-9_/]*)\s+(?:eq|ne|gt|lt|ge|le)\s", senza_espr)}


def verifica_flussi() -> set[str]:
    cartella = REPO / "powerautomate" / "flows"
    nomi = set()
    for f in sorted(cartella.glob("*.json")):
        try:
            dati = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            err(f"{f.name}: JSON non valido ({e})")
            continue
        nome = dati.get("name", "")
        nomi.add(nome)
        if f.stem != nome:
            err(f"{f.name}: il nome del file non coincide con 'name' ({nome})")
        for ref in dati.get("connectionReferences", {}):
            if ref not in CONNETTORI_STANDARD:
                err(f"{nome}: connettore non standard o non previsto: {ref}")
        definizione = dati.get("definition", {})
        tutte = {}
        for an, az, _ in azioni_ricorsive(definizione.get("actions", {})):
            if an in tutte:
                err(f"{nome}: nome azione duplicato {an}")
            tutte[an] = az
        nomi_trigger = set(definizione.get("triggers", {}))
        # runAfter verso fratelli esistenti
        for an, az, fratelli in azioni_ricorsive(definizione.get("actions", {})):
            for dip in (az.get("runAfter") or {}):
                if dip not in fratelli:
                    err(f"{nome}: {an} ha runAfter verso '{dip}' che non è un'azione dello stesso livello")
        testo = json.dumps(definizione, ensure_ascii=False)
        for rif in set(re.findall(r"(?:body|outputs|actions|items|result)\('([^']+)'\)", testo)):
            if rif not in tutte and rif not in nomi_trigger:
                err(f"{nome}: riferimento a un'azione inesistente '{rif}'")
        for rif in set(re.findall(r"variables\('([^']+)'\)", testo)):
            if not any(az.get("type") == "InitializeVariable" and
                       any(v.get("name") == rif for v in az.get("inputs", {}).get("variables", []))
                       for az in tutte.values()):
                err(f"{nome}: variabile non inizializzata '{rif}'")
        # colonne e stati nelle azioni SharePoint
        for an, az, _ in azioni_ricorsive(definizione.get("actions", {})):
            params = (az.get("inputs") or {}).get("parameters") or {}
            tabella = params.get("table")
            if isinstance(tabella, str) and tabella in LISTE:
                for k, v in params.items():
                    if k.startswith("item/"):
                        col = k.split("/")[1].split("@")[0]
                        if col not in LISTE[tabella]:
                            err(f"{nome}/{an}: colonna '{col}' inesistente in '{tabella}'")
                    if k in ("$filter", "$orderby") and isinstance(v, str):
                        cols = colonne_in_filtro(v) if k == "$filter" else \
                            {c.split()[0] for c in re.sub(r"@\{[^}]*\}", "", v).split(",") if c.strip()}
                        for col in cols:
                            base = col.split("/")[0]
                            if base not in LISTE[tabella]:
                                err(f"{nome}/{an}: colonna '{base}' nel {k} inesistente in '{tabella}'")
            elif isinstance(tabella, str) and tabella and not tabella.startswith("@"):
                err(f"{nome}/{an}: lista '{tabella}' non presente nello schema")
        for st in re.findall(r"Stato/Value\"\s*:\s*\"([^\"@]+)\"", testo):
            if st not in STATI:
                err(f"{nome}: stato non valido '{st}'")
        for st in re.findall(r"Stato(?:/Value)? (?:eq|ne) '([^']+)'", testo):
            if st not in STATI:
                err(f"{nome}: stato non valido nel filtro '{st}'")
        # trigger Power Apps
        if nome in CONTRATTO:
            trig = next(iter(definizione.get("triggers", {}).values()), {})
            if trig.get("kind") != "PowerAppV2":
                err(f"{nome}: il trigger deve essere Power Apps (V2)")
            else:
                props = trig.get("inputs", {}).get("schema", {}).get("properties", {})
                if len(props) != CONTRATTO[nome]:
                    err(f"{nome}: il trigger ha {len(props)} parametri, il contratto ne prevede {CONTRATTO[nome]}")
            if not any(az.get("type") == "Response" for az in tutte.values()):
                err(f"{nome}: manca l'azione di risposta a Power Apps")
    mancanti = FLUSSI_ATTESI - nomi
    if mancanti:
        err(f"flussi mancanti: {', '.join(sorted(mancanti))}")
    return nomi


# =============================================================================
#  App
# =============================================================================
def argomenti(testo: str, inizio: int) -> tuple[int, int]:
    """Conta gli argomenti di una chiamata a partire dalla parentesi aperta. Restituisce (n, fine)."""
    livello, n, vuoto, i = 0, 0, True, inizio
    while i < len(testo):
        c = testo[i]
        if c == '"':  # stringa Power Fx ("" = apice escapato)
            vuoto = False
            i += 1
            while i < len(testo):
                if testo[i] == '"':
                    if testo[i + 1:i + 2] == '"':
                        i += 2
                        continue
                    break
                i += 1
        elif c in "([{":
            livello += 1
            if livello > 1:
                vuoto = False
        elif c in ")]}":
            livello -= 1
            if livello == 0:
                return (0 if vuoto else n + 1), i
        elif c == "," and livello == 1:
            n += 1
        elif not c.isspace():
            vuoto = False
        i += 1
    return -1, i


def stringhe_formula(valore) -> list[str]:
    out = []
    if isinstance(valore, str):
        out.append(valore)
    elif isinstance(valore, dict):
        for v in valore.values():
            out += stringhe_formula(v)
    elif isinstance(valore, list):
        for v in valore:
            out += stringhe_formula(v)
    return out


def verifica_app(flussi: set[str]) -> None:
    cartella = REPO / "powerapps" / "src"
    file_yaml = sorted(cartella.glob("*.pa.yaml"))
    if not file_yaml:
        err("nessuna schermata trovata in powerapps/src")
        return
    nomi_controlli: dict[str, str] = {}
    for f in file_yaml:
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            err(f"{f.name}: YAML non valido ({e})")
            continue
        testo = "\n".join(stringhe_formula(doc))
        # nomi dei controlli univoci
        for m in re.finditer(r"^\s*-\s+([A-Za-z_][A-Za-z0-9_]*):\s*$", f.read_text(encoding="utf-8"), re.M):
            n = m.group(1)
            if n in nomi_controlli and nomi_controlli[n] != f.name:
                err(f"controllo '{n}' definito sia in {nomi_controlli[n]} sia in {f.name}")
            nomi_controlli.setdefault(n, f.name)
        for m in re.finditer(r"\b(SDF_[A-Za-z0-9_]+)\.Run\(", testo):
            nome = m.group(1)
            if nome not in CONTRATTO:
                err(f"{f.name}: chiamata a un flusso sconosciuto {nome}")
                continue
            if nome not in flussi:
                warn(f"{f.name}: il flusso {nome} non esiste ancora in powerautomate/flows")
            n, _ = argomenti(testo, m.end() - 1)
            if n != CONTRATTO[nome]:
                err(f"{f.name}: {nome}.Run con {n} argomenti, il contratto ne prevede {CONTRATTO[nome]}")
        for st in re.findall(r"'Stato richiesta'\.Value\s*(?:=|<>)\s*\"([^\"]+)\"", testo):
            if st not in STATI:
                err(f"{f.name}: stato non valido \"{st}\"")
        for st in re.findall(r"(?:stato|Stato)\s*(?:=|<>)\s*\"([^\"]+)\"", testo):
            if st not in STATI and st not in TUTTE_LE_SCELTE:
                warn(f"{f.name}: valore \"{st}\" confrontato con uno stato ma non presente nelle scelte")
        for nome in set(re.findall(r"'([^'\n]{3,60})'", testo)):
            if nome[0].isupper() and nome not in DISPLAY and not nome.startswith(("Stat", "Tip")):
                warn(f"{f.name}: '{nome}' non è un nome di lista/colonna dello schema (verificare)")


def main() -> None:
    flussi = verifica_flussi()
    verifica_app(flussi)
    for a in sorted(set(avvisi)):
        print(f"AVVISO  {a}")
    for e in errori:
        print(f"ERRORE  {e}")
    print(f"\n{len(errori)} errori, {len(set(avvisi))} avvisi")
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
