#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera docs/02-modello-dati.md a partire da dataverse/schema.yaml.

    python dataverse/genera_documentazione.py
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
TIPI = {
    "text": "Testo", "email": "Testo (e-mail)", "url": "Testo (URL)", "memo": "Testo multiriga",
    "int": "Numero intero", "decimal": "Numero decimale (2 cifre)", "bool": "Sì/No",
    "date": "Solo data", "datetime": "Data e ora (fuso utente)",
    "datetime_tzi": "Data e ora (indipendente dal fuso)", "choice": "Scelta", "lookup": "Ricerca",
    "file": "File",
}
PROFONDITA = {"user": "Utente", "bu": "Business unit", "deep": "BU padre-figlio", "org": "Organizzazione"}


def main() -> None:
    s = yaml.safe_load((ROOT / "schema.yaml").read_text(encoding="utf-8"))
    out: list[str] = []
    w = out.append
    w("# 2. Modello dati Dataverse")
    w("")
    w("> Documento generato automaticamente da `dataverse/schema.yaml` con "
      "`python dataverse/genera_documentazione.py`. Non modificarlo a mano.")
    w("")
    w(f"- **Publisher:** {s['publisher']['friendlyname']} (`{s['publisher']['uniquename']}`), "
      f"prefisso `{s['publisher']['customizationprefix']}_`, prefisso valori scelta "
      f"`{s['publisher']['customizationoptionvalueprefix']}`")
    w(f"- **Soluzione:** {s['solution']['friendlyname']} (`{s['solution']['uniquename']}`) "
      f"v{s['solution']['version']}")
    w("- Tutte le tabelle sono di proprietà utente/team, con controllo (audit) attivo.")
    w("")
    w("```mermaid")
    w("erDiagram")
    for tname, t in s["tables"].items():
        for col in t["columns"]:
            if col["type"] == "lookup" and col["target"] != "systemuser":
                w(f"  {col['target']} ||--o{{ {tname} : \"{col['display_name']}\"")
    w("```")
    w("")
    w("## Tabelle")
    for tname, t in s["tables"].items():
        w("")
        w(f"### {t['plural_name']} (`{tname}`)")
        w("")
        w(f"{t.get('description', '')}  ")
        w(f"Entity set Web API: `{t['entity_set']}` · Nome singolare: *{t['display_name']}*")
        w("")
        w("| Nome visualizzato | Nome logico | Tipo | Dettagli |")
        w("|---|---|---|---|")
        p = t["primary"]
        det = "Colonna nome primario"
        if p.get("autonumber"):
            det += f"; numerazione automatica `{p['autonumber']}`"
        if p.get("description"):
            det += f"; {p['description']}"
        w(f"| **{p['display_name']}** | `{p['name']}` | Testo ({p.get('max_length', 200)}) | {det} |")
        for c in t["columns"]:
            tipo = TIPI[c["type"]]
            d: list[str] = []
            if c["type"] == "choice":
                d.append(f"scelta `{c['choice']}` ({s['choices'][c['choice']]['display_name']})")
            if c["type"] == "lookup":
                d.append(f"→ `{c['target']}`" + (" (relazione padre-figlio)" if c.get("parental") else ""))
            if c.get("max_length") and c["type"] in ("text", "memo"):
                tipo += f" ({c['max_length']})"
            if c.get("autonumber"):
                d.append(f"numerazione automatica `{c['autonumber']}`")
            if c.get("required"):
                d.append("obbligatoria")
            if "default" in c:
                dv = c["default"]
                if c["type"] == "choice":
                    dv = next(o["label"] for o in s["choices"][c["choice"]]["options"] if o["value"] == dv)
                elif isinstance(dv, bool):
                    dv = "Sì" if dv else "No"
                d.append(f"predefinito: {dv}")
            if c.get("secured"):
                d.append(f"🔒 colonna protetta (`{c['secured']}`)")
            if c.get("max_size_kb"):
                d.append(f"max {c['max_size_kb'] // 1024} MB")
            if c.get("description"):
                d.append(c["description"])
            w(f"| {c['display_name']} | `{c['name']}` | {tipo} | {'; '.join(d)} |")
        for k in t.get("alternate_keys", []):
            w("")
            w(f"Chiave alternativa **{k['display_name']}** (`{k['name']}`): {', '.join('`'+c+'`' for c in k['columns'])}")
    w("")
    w("## Scelte globali")
    for cname, ch in s["choices"].items():
        w("")
        w(f"### {ch['display_name']} (`{cname}`)")
        w("")
        w("| Valore | Etichetta |")
        w("|---|---|")
        for o in ch["options"]:
            w(f"| {o['value']} | {o['label']} |")
    w("")
    w("## Variabili d'ambiente")
    w("")
    w("| Nome schema | Nome visualizzato | Valore predefinito | Note |")
    w("|---|---|---|---|")
    for ev in s["environment_variables"]:
        default = ev.get("default", "")
        if len(default) > 60:
            default = default[:57] + "..."
        w(f"| `{ev['name']}` | {ev['display_name']} | `{default}` | {ev.get('description', '')} |")
    w("")
    w("## Riferimenti di connessione")
    w("")
    w("| Nome logico | Nome visualizzato | Connettore |")
    w("|---|---|---|")
    for cr in s["connection_references"]:
        w(f"| `{cr['name']}` | {cr['display_name']} | `{cr['connector']}` |")
    w("")
    w("## Ruoli di sicurezza")
    for rname, r in s["security_roles"].items():
        w("")
        w(f"### {rname}")
        w("")
        w(r.get("description", ""))
        w("")
        w("| Tabella | Crea | Leggi | Scrivi | Elimina | Aggiungi | Aggiungi a | Assegna | Condividi |")
        w("|---|---|---|---|---|---|---|---|---|")
        for tname, acc in r["privileges"].items():
            cells = [PROFONDITA.get(acc.get(a, ""), "—") for a in
                     ("create", "read", "write", "delete", "append", "appendto", "assign", "share")]
            w(f"| {s['tables'][tname]['plural_name']} | " + " | ".join(cells) + " |")
    w("")
    w("## Profili di sicurezza delle colonne")
    w("")
    gruppi: dict[str, list[str]] = {}
    for tname, t in s["tables"].items():
        for c in t["columns"]:
            if c.get("secured"):
                gruppi.setdefault(c["secured"], []).append(f"{t['plural_name']}.{c['display_name']}")
    w("| Gruppo di colonne | Colonne |")
    w("|---|---|")
    for g, cols in gruppi.items():
        w(f"| `{g}` | {', '.join(cols)} |")
    w("")
    w("| Profilo | Gruppo | Lettura | Creazione | Aggiornamento |")
    w("|---|---|---|---|---|")
    for pname, p in s["column_security_profiles"].items():
        for g, perm in p["groups"].items():
            yn = lambda v: "Sì" if v else "No"  # noqa: E731
            w(f"| {pname} | `{g}` | {yn(perm.get('read'))} | {yn(perm.get('create'))} | {yn(perm.get('update'))} |")
    w("")
    w("## Team (gruppi Microsoft Entra ID)")
    w("")
    w("| Team | Chiave in config.json | Ruoli | Profili colonne |")
    w("|---|---|---|---|")
    for tname, t in s["teams"].items():
        w(f"| {tname} | `{t['entra_group_config_key']}` | {', '.join(t['roles'])} | {', '.join(t['column_profiles'])} |")
    w("")
    (REPO / "docs" / "02-modello-dati.md").write_text("\n".join(out), encoding="utf-8")
    print("docs/02-modello-dati.md generato")


if __name__ == "__main__":
    main()
