#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crea i pacchetti di importazione Power Automate (formato "Pacchetto (legacy)" .zip)
a partire dalle definizioni in powerautomate/flows/*.json.

    python powerautomate/crea_pacchetti.py --sito https://societadolce.sharepoint.com/sites/GestioneFormazione

Produce in powerautomate/pacchetti/:
  - un .zip per ogni flusso (es. SDF_API01_Profilo.zip)
  - GestioneFormazione_tutti_i_flussi.zip con tutti i flussi insieme

Importazione: make.powerautomate.com -> I miei flussi -> Importa -> Importa pacchetto (legacy)
-> scegliere il file -> per ogni connessione "Seleziona durante l'importazione" scegliere la
connessione dell'account di servizio -> per ogni flusso "Crea come nuovo" -> Importa.

Il segnaposto {{SITO_URL}} nelle definizioni viene sostituito con l'indirizzo del sito.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NS = uuid.UUID("0b8f3c52-6f0e-4c34-9a8e-2b7f9a1d6c11")  # GUID stabili tra le generazioni

CONNETTORI = {
    "shared_sharepointonline": ("SharePoint", "sharepointonline"),
    "shared_office365": ("Office 365 Outlook", "office365"),
    "shared_office365users": ("Office 365 Users", "office365users"),
}


def gid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


def icon(slug: str) -> str:
    return f"https://connectoricons-prod.azureedge.net/{slug}/icon.png"


def carica_flussi(sito: str) -> list[dict]:
    flussi = []
    for f in sorted((ROOT / "flows").glob("*.json")):
        testo = f.read_text(encoding="utf-8").replace("{{SITO_URL}}", sito.rstrip("/"))
        dati = json.loads(testo)
        for chiave in ("name", "definition", "connectionReferences"):
            if chiave not in dati:
                sys.exit(f"{f.name}: manca la chiave '{chiave}'")
        for ref in dati["connectionReferences"]:
            if ref not in CONNETTORI:
                sys.exit(f"{f.name}: connettore non previsto '{ref}' (solo connettori standard)")
        resto = re.findall(r"\{\{[A-Z_]+\}\}", testo)
        if resto:
            sys.exit(f"{f.name}: segnaposto non sostituiti {sorted(set(resto))}")
        flussi.append(dati)
    if not flussi:
        sys.exit("Nessun flusso trovato in powerautomate/flows/")
    return flussi


def scrivi_pacchetto(percorso: Path, nome_pacchetto: str, flussi: list[dict]) -> None:
    risorse: dict[str, dict] = {}
    api_ids: dict[str, str] = {}
    conn_ids: dict[str, str] = {}
    # Una risorsa API e una risorsa connessione per connettore, condivise da tutti i flussi del pacchetto
    for f in flussi:
        for ref in f["connectionReferences"]:
            if ref in api_ids:
                continue
            nome, slug = CONNETTORI[ref]
            api_ids[ref] = gid("api", ref)
            conn_ids[ref] = gid("conn", ref)
            risorse[api_ids[ref]] = {
                "id": f"/providers/Microsoft.PowerApps/apis/{ref}",
                "name": ref,
                "type": "Microsoft.PowerApps/apis",
                "suggestedCreationType": "Existing",
                "details": {"displayName": nome, "iconUri": icon(slug)},
                "configurableBy": "System",
                "hierarchy": "Child",
                "dependsOn": [],
            }
            risorse[conn_ids[ref]] = {
                "type": "Microsoft.PowerApps/apis/connections",
                "suggestedCreationType": "Existing",
                "creationType": "Existing",
                "details": {"displayName": f"{nome} (account di servizio)", "iconUri": icon(slug)},
                "configurableBy": "User",
                "hierarchy": "Child",
                "dependsOn": [api_ids[ref]],
            }

    with zipfile.ZipFile(percorso, "w", zipfile.ZIP_DEFLATED) as z:
        asset_paths = []
        for f in flussi:
            flow_id = gid("flow", f["name"])
            res_id = gid("res", f["name"])
            asset_paths.append(flow_id)
            refs = list(f["connectionReferences"])
            risorse[res_id] = {
                "id": f"/providers/Microsoft.Flow/flows/{flow_id}",
                "name": flow_id,
                "type": "Microsoft.Flow/flows",
                "suggestedCreationType": "New",
                "creationType": "Existing, New, Update",
                "details": {"displayName": f["name"]},
                "configurableBy": "User",
                "hierarchy": "Root",
                "dependsOn": [api_ids[r] for r in refs] + [conn_ids[r] for r in refs],
            }
            definizione = {
                "name": flow_id,
                "id": f"/providers/Microsoft.Flow/flows/{flow_id}",
                "type": "Microsoft.Flow/flows",
                "properties": {
                    "apiId": "/providers/Microsoft.PowerApps/apis/shared_logicflows",
                    "displayName": f["name"],
                    "definition": f["definition"],
                    "connectionReferences": f["connectionReferences"],
                    "flowFailureAlertSubscribed": False,
                    "isManaged": False,
                },
            }
            base = f"Microsoft.Flow/flows/{flow_id}"
            z.writestr(f"{base}/definition.json", json.dumps(definizione, ensure_ascii=False, indent=2))
            z.writestr(f"{base}/apisMap.json", json.dumps({r: api_ids[r] for r in refs}, indent=2))
            z.writestr(f"{base}/connectionsMap.json", json.dumps({r: conn_ids[r] for r in refs}, indent=2))
        z.writestr("Microsoft.Flow/flows/manifest.json",
                   json.dumps({"packageSchemaVersion": "1.0", "flowAssets": {"assetPaths": asset_paths}}, indent=2))
        manifest = {
            "schema": "1.0",
            "details": {
                "displayName": nome_pacchetto,
                "description": "Gestione ore formazione - Società Dolce",
                "createdTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000Z"),
                "packageTelemetryId": gid("pkg", nome_pacchetto),
                "creator": "Formazione-Dolce/powerautomate/crea_pacchetti.py",
                "sourceEnvironment": "",
            },
            "resources": risorse,
        }
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="Crea i pacchetti di importazione dei flussi")
    ap.add_argument("--sito", required=True, help="URL del sito SharePoint, es. https://societadolce.sharepoint.com/sites/GestioneFormazione")
    ap.add_argument("--uscita", default=str(ROOT / "pacchetti"), help="cartella di destinazione")
    args = ap.parse_args()
    if not re.match(r"^https://[a-z0-9-]+\.sharepoint\.com/sites/[^/]+/?$", args.sito, re.I):
        sys.exit("URL del sito non valido: atteso https://<tenant>.sharepoint.com/sites/<nome>")
    flussi = carica_flussi(args.sito)
    uscita = Path(args.uscita)
    uscita.mkdir(parents=True, exist_ok=True)
    for f in flussi:
        scrivi_pacchetto(uscita / f"{f['name']}.zip", f["name"], [f])
        print(f"  creato {f['name']}.zip")
    scrivi_pacchetto(uscita / "GestioneFormazione_tutti_i_flussi.zip", "Gestione ore formazione - flussi", flussi)
    print(f"  creato GestioneFormazione_tutti_i_flussi.zip ({len(flussi)} flussi)")
    print(f"Pacchetti in {uscita}")


if __name__ == "__main__":
    main()
