#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provisioning Dataverse - "Gestione ore formazione" (Società Dolce)
=================================================================

Crea (o completa, se già presenti) nell'ambiente Power Platform indicato:

  1. publisher e soluzione
  2. scelte globali
  3. tabelle, colonne, relazioni (colonne di ricerca), chiavi alternative
  4. pubblicazione delle personalizzazioni
  5. variabili d'ambiente e riferimenti di connessione
  6. ruoli di sicurezza con i privilegi
  7. profili di sicurezza delle colonne
  8. team collegati ai gruppi Microsoft Entra ID (se configurati)
  9. flussi cloud Power Automate (da powerautomate/flows/*.json, creati spenti)
 10. dati di esempio (solo per ambienti di test)

Lo script è idempotente: ogni componente viene creato solo se non esiste.
Legge il modello dati da dataverse/schema.yaml.

Uso
---
    pip install -r dataverse/requirements.txt
    cp dataverse/config.example.json dataverse/config.json   # e compilare
    python dataverse/provision.py --config dataverse/config.json --dry-run
    python dataverse/provision.py --config dataverse/config.json
    python dataverse/provision.py --config dataverse/config.json --steps flows --update-flows

Autenticazione (--auth):
    azcli       usa "az account get-access-token" (richiede Azure CLI con az login)
    devicecode  accesso tramite codice dispositivo (richiede il pacchetto msal)
    interactive accesso interattivo nel browser (richiede msal)
    env         legge il token dalla variabile d'ambiente DATAVERSE_TOKEN
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Installare le dipendenze: pip install -r dataverse/requirements.txt")

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
API = "/api/data/v9.2/"
ALL_STEPS = [
    "solution", "choices", "tables", "columns", "relationships", "keys", "publish",
    "envvars", "connrefs", "roles", "colsec", "teams", "flows", "seed",
]
DEFAULT_STEPS = [s for s in ALL_STEPS if s != "seed"]
# App registration pubblica di esempio Microsoft per Dataverse (multi-tenant)
DEFAULT_CLIENT_ID = "51f81489-12ee-4a9e-aaae-a2591f45987d"

DEPTH = {"user": "Basic", "bu": "Local", "deep": "Deep", "org": "Global"}
PRIV_ACCESS = {
    "create": "Create", "read": "Read", "write": "Write", "delete": "Delete",
    "append": "Append", "appendto": "AppendTo", "assign": "Assign", "share": "Share",
}


# =============================================================================
#  Utilità di output
# =============================================================================
def info(msg: str) -> None:
    print(f"  {msg}")


def ok(msg: str) -> None:
    print(f"  ✔ {msg}")


def skip(msg: str) -> None:
    print(f"  · {msg} (già presente)")


def warn(msg: str) -> None:
    print(f"  ⚠ {msg}")


def header(msg: str) -> None:
    print(f"\n== {msg} ==")


# =============================================================================
#  Client Web API Dataverse
# =============================================================================
class DataverseError(RuntimeError):
    pass


class Dataverse:
    def __init__(self, url: str, token: str | None, solution: str, dry_run: bool):
        self.url = url.rstrip("/")
        self.base = self.url + API
        self.solution = solution
        self.dry_run = dry_run
        self.language = 1040
        self._session = None
        if not dry_run:
            import requests  # import ritardato: non serve in dry-run

            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {token}",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            })

    # ------------------------------------------------------------------ http
    def request(self, method: str, path: str, body: Any = None, solution_aware: bool = False,
                extra_headers: dict | None = None, ok_404: bool = False) -> Any:
        url = path if path.startswith("http") else self.base + path
        headers = dict(extra_headers or {})
        if solution_aware:
            headers["MSCRM.SolutionUniqueName"] = self.solution
        if self.dry_run:
            if method != "GET":
                summary = ""
                if isinstance(body, dict):
                    summary = body.get("SchemaName") or body.get("Name") or body.get("name") or body.get("uniquename") or \
                        body.get("schemaname") or body.get("connectionreferencelogicalname") or ""
                info(f"[dry-run] {method} {path} {summary}")
            return None
        for attempt in range(6):
            resp = self._session.request(method, url, json=body, headers=headers, timeout=600)
            if resp.status_code in (429, 503) and attempt < 5:
                wait = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                warn(f"limite richieste raggiunto, nuovo tentativo tra {wait}s")
                time.sleep(wait)
                continue
            break
        if resp.status_code == 404 and ok_404:
            return None
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except ValueError:
                detail = resp.text
            raise DataverseError(f"{method} {path} -> {resp.status_code}: {detail}")
        if resp.status_code == 204 or not resp.content:
            entity_id = resp.headers.get("OData-EntityId", "")
            return {"_id": entity_id[entity_id.rfind("(") + 1:-1]} if "(" in entity_id else {}
        return resp.json()

    def get(self, path: str) -> Any:
        return self.request("GET", path, ok_404=True)

    def first(self, path: str) -> dict | None:
        res = self.get(path)
        if not res:
            return None
        values = res.get("value", [])
        return values[0] if values else None

    def post(self, path: str, body: Any, solution_aware: bool = True, **kw) -> Any:
        return self.request("POST", path, body, solution_aware=solution_aware, **kw)

    def patch(self, path: str, body: Any, solution_aware: bool = False) -> Any:
        return self.request("PATCH", path, body, solution_aware=solution_aware,
                            extra_headers={"If-Match": "*"})

    # ------------------------------------------------------------- etichette
    def label(self, text: str | None) -> dict:
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.Label",
            "LocalizedLabels": [{
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text or "",
                "LanguageCode": self.language,
            }],
        }

    def detect_language(self) -> None:
        if self.dry_run:
            return
        org = self.first("organizations?$select=languagecode")
        if org:
            self.language = int(org["languagecode"])
            info(f"lingua di base dell'ambiente: {self.language}")


# =============================================================================
#  Autenticazione
# =============================================================================
def get_token(method: str, url: str, cfg: dict) -> str:
    resource = url.rstrip("/")
    if method == "env":
        token = os.environ.get("DATAVERSE_TOKEN")
        if not token:
            sys.exit("Variabile DATAVERSE_TOKEN non impostata")
        return token
    if method == "azcli":
        try:
            out = subprocess.run(
                ["az", "account", "get-access-token", "--resource", resource,
                 "--query", "accessToken", "-o", "tsv"],
                check=True, capture_output=True, text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            sys.exit(f"Impossibile ottenere il token con Azure CLI ({exc}). Eseguire 'az login' "
                     "oppure usare --auth devicecode")
        return out.stdout.strip()
    try:
        import msal
    except ImportError:
        sys.exit("Per --auth devicecode/interactive installare msal: pip install msal")
    tenant = cfg.get("tenant_id") or "organizations"
    app = msal.PublicClientApplication(cfg.get("client_id") or DEFAULT_CLIENT_ID,
                                       authority=f"https://login.microsoftonline.com/{tenant}")
    scopes = [f"{resource}/.default"]
    if method == "interactive":
        result = app.acquire_token_interactive(scopes=scopes)
    else:
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            sys.exit(f"Errore avvio device code: {flow}")
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        sys.exit(f"Autenticazione non riuscita: {result.get('error_description', result)}")
    return result["access_token"]


# =============================================================================
#  Costruzione metadati
# =============================================================================
def required_level(required: bool) -> dict:
    return {
        "Value": "ApplicationRequired" if required else "None",
        "CanBeChanged": True,
        "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings",
    }


def audit(enabled: bool = True) -> dict:
    return {"Value": enabled, "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyauditsettings"}


def attribute_payload(dv: Dataverse, col: dict, optionset_ids: dict[str, str] | None = None) -> dict:
    """Restituisce il payload AttributeMetadata per una colonna (non lookup)."""
    t = col["type"]
    base = {
        "SchemaName": col["name"],
        "DisplayName": dv.label(col["display_name"]),
        "Description": dv.label(col.get("description", "")),
        "RequiredLevel": required_level(col.get("required", False)),
        "IsAuditEnabled": audit(),
    }
    if col.get("secured"):
        base["IsSecured"] = True

    if t in ("text", "email", "url"):
        fmt = {"text": "Text", "email": "Email", "url": "Url"}[t]
        default_len = {"text": 200, "email": 100, "url": 500}[t]
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "AttributeType": "String",
            "AttributeTypeName": {"Value": "StringType"},
            "FormatName": {"Value": fmt},
            "MaxLength": col.get("max_length", default_len),
        })
        if col.get("autonumber"):
            base["AutoNumberFormat"] = col["autonumber"]
    elif t == "memo":
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            "AttributeType": "Memo",
            "AttributeTypeName": {"Value": "MemoType"},
            "Format": "TextArea",
            "MaxLength": col.get("max_length", 4000),
        })
    elif t == "int":
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
            "AttributeType": "Integer",
            "AttributeTypeName": {"Value": "IntegerType"},
            "Format": "None",
            "MinValue": col.get("min", 0),
            "MaxValue": col.get("max", 2147483647),
        })
    elif t == "decimal":
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
            "AttributeType": "Decimal",
            "AttributeTypeName": {"Value": "DecimalType"},
            "Precision": col.get("precision", 2),
            "MinValue": col.get("min", 0),
            "MaxValue": col.get("max", 1000),
        })
    elif t == "bool":
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
            "AttributeType": "Boolean",
            "AttributeTypeName": {"Value": "BooleanType"},
            "DefaultValue": bool(col.get("default", False)),
            "OptionSet": {
                "@odata.type": "Microsoft.Dynamics.CRM.BooleanOptionSetMetadata",
                "TrueOption": {"Value": 1, "Label": dv.label("Sì")},
                "FalseOption": {"Value": 0, "Label": dv.label("No")},
                "OptionSetType": "Boolean",
            },
        })
    elif t in ("date", "datetime", "datetime_tzi"):
        fmt, behavior = {
            "date": ("DateOnly", "DateOnly"),
            "datetime": ("DateAndTime", "UserLocal"),
            "datetime_tzi": ("DateAndTime", "TimeZoneIndependent"),
        }[t]
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
            "AttributeType": "DateTime",
            "AttributeTypeName": {"Value": "DateTimeType"},
            "Format": fmt,
            "DateTimeBehavior": {"Value": behavior},
        })
    elif t == "choice":
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
            "AttributeType": "Picklist",
            "AttributeTypeName": {"Value": "PicklistType"},
            "GlobalOptionSet@odata.bind": "/GlobalOptionSetDefinitions("
                                          f"{(optionset_ids or {}).get(col['choice'], col['choice'])})",
        })
        if "default" in col:
            base["DefaultFormValue"] = col["default"]
    elif t == "file":
        base.update({
            "@odata.type": "Microsoft.Dynamics.CRM.FileAttributeMetadata",
            "AttributeType": "Virtual",
            "AttributeTypeName": {"Value": "FileType"},
            "MaxSizeInKB": col.get("max_size_kb", 32768),
        })
        base.pop("IsAuditEnabled", None)
    else:
        raise ValueError(f"Tipo colonna non gestito: {t} ({col['name']})")
    return base


def relationship_payload(dv: Dataverse, table: str, col: dict) -> dict:
    target = col["target"]
    parental = col.get("parental", False)
    if parental:
        cascade = {"Assign": "Cascade", "Delete": "Cascade", "Merge": "NoCascade",
                   "Reparent": "Cascade", "Share": "Cascade", "Unshare": "Cascade",
                   "RollupView": "NoCascade"}
    else:
        cascade = {"Assign": "NoCascade", "Delete": col.get("cascade_delete", "RemoveLink"),
                   "Merge": "NoCascade", "Reparent": "NoCascade", "Share": "NoCascade",
                   "Unshare": "NoCascade", "RollupView": "NoCascade"}
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": col["relationship"],
        "ReferencedEntity": target,
        "ReferencedAttribute": f"{target}id",
        "ReferencingEntity": table,
        "CascadeConfiguration": cascade,
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "AttributeType": "Lookup",
            "AttributeTypeName": {"Value": "LookupType"},
            "SchemaName": col["name"],
            "DisplayName": dv.label(col["display_name"]),
            "Description": dv.label(col.get("description", "")),
            "RequiredLevel": required_level(col.get("required", False)),
            "IsAuditEnabled": audit(),
        },
    }


# =============================================================================
#  Passi di provisioning
# =============================================================================
class Provisioner:
    def __init__(self, dv: Dataverse, schema: dict, cfg: dict, args: argparse.Namespace):
        self.dv = dv
        self.schema = schema
        self.cfg = cfg
        self.args = args
        self._root_bu: str | None = None
        self._roles: dict[str, str] = {}
        self._profiles: dict[str, str] = {}
        self._optionsets: dict[str, str] = {}

    # ---------------------------------------------------------------- utilità
    def root_bu(self) -> str:
        if self._root_bu is None:
            if self.dv.dry_run:
                self._root_bu = "00000000-0000-0000-0000-000000000000"
            else:
                bu = self.dv.first("businessunits?$select=businessunitid&$filter=_parentbusinessunitid_value eq null")
                if not bu:
                    raise DataverseError("Business unit radice non trovata")
                self._root_bu = bu["businessunitid"]
        return self._root_bu

    def optionset_id(self, name: str) -> str:
        """MetadataId della scelta globale (necessario per il collegamento della colonna)."""
        if name not in self._optionsets:
            if self.dv.dry_run:
                self._optionsets[name] = "00000000-0000-0000-0000-000000000000"
            else:
                res = self.dv.get(f"GlobalOptionSetDefinitions(Name='{name}')?$select=MetadataId")
                if not res:
                    raise DataverseError(f"Scelta globale {name} non trovata: eseguire prima il passo 'choices'")
                self._optionsets[name] = res["MetadataId"]
        return self._optionsets[name]

    def attr_exists(self, table: str, attr: str) -> bool:
        if self.dv.dry_run:
            return False
        return self.dv.get(
            f"EntityDefinitions(LogicalName='{table}')/Attributes(LogicalName='{attr}')?$select=LogicalName"
        ) is not None

    # ------------------------------------------------------------- 1 soluzione
    def step_solution(self) -> None:
        header("Publisher e soluzione")
        pub = self.schema["publisher"]
        sol = self.schema["solution"]
        existing = self.dv.first(f"publishers?$select=publisherid&$filter=uniquename eq '{pub['uniquename']}'")
        if existing:
            pub_id = existing["publisherid"]
            skip(f"publisher {pub['uniquename']}")
        else:
            res = self.dv.post("publishers", {
                "uniquename": pub["uniquename"],
                "friendlyname": pub["friendlyname"],
                "description": pub.get("description", ""),
                "customizationprefix": pub["customizationprefix"],
                "customizationoptionvalueprefix": pub["customizationoptionvalueprefix"],
            }, solution_aware=False)
            pub_id = (res or {}).get("_id", "<nuovo-publisher>")
            ok(f"publisher {pub['uniquename']} creato")
        if self.dv.first(f"solutions?$select=solutionid&$filter=uniquename eq '{sol['uniquename']}'"):
            skip(f"soluzione {sol['uniquename']}")
        else:
            self.dv.post("solutions", {
                "uniquename": sol["uniquename"],
                "friendlyname": sol["friendlyname"],
                "description": sol.get("description", ""),
                "version": sol["version"],
                "publisherid@odata.bind": f"/publishers({pub_id})",
            }, solution_aware=False)
            ok(f"soluzione {sol['uniquename']} creata")

    # --------------------------------------------------------------- 2 scelte
    def step_choices(self) -> None:
        header("Scelte globali")
        for name, ch in self.schema["choices"].items():
            if not self.dv.dry_run and self.dv.get(f"GlobalOptionSetDefinitions(Name='{name}')"):
                skip(name)
                continue
            options = []
            for opt in ch["options"]:
                o = {"Value": opt["value"], "Label": self.dv.label(opt["label"])}
                if opt.get("color"):
                    o["Color"] = opt["color"]
                options.append(o)
            self.dv.post("GlobalOptionSetDefinitions", {
                "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
                "Name": name,
                "DisplayName": self.dv.label(ch["display_name"]),
                "Description": self.dv.label(ch.get("description", "")),
                "IsGlobal": True,
                "OptionSetType": "Picklist",
                "Options": options,
            })
            ok(f"{name} ({len(options)} valori)")

    # -------------------------------------------------------------- 3 tabelle
    def step_tables(self) -> None:
        header("Tabelle")
        for name, t in self.schema["tables"].items():
            if not self.dv.dry_run and self.dv.get(f"EntityDefinitions(LogicalName='{name}')?$select=LogicalName"):
                skip(name)
                continue
            prim = t["primary"]
            primary_attr = {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "AttributeType": "String",
                "AttributeTypeName": {"Value": "StringType"},
                "SchemaName": prim["name"],
                "IsPrimaryName": True,
                "DisplayName": self.dv.label(prim["display_name"]),
                "Description": self.dv.label(prim.get("description", "")),
                "RequiredLevel": required_level(not prim.get("autonumber")),
                "FormatName": {"Value": "Text"},
                "MaxLength": prim.get("max_length", 200),
            }
            if prim.get("autonumber"):
                primary_attr["AutoNumberFormat"] = prim["autonumber"]
            payload = {
                "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
                "SchemaName": name,
                "DisplayName": self.dv.label(t["display_name"]),
                "DisplayCollectionName": self.dv.label(t["plural_name"]),
                "Description": self.dv.label(t.get("description", "")),
                "OwnershipType": "UserOwned",
                "IsActivity": False,
                "HasActivities": False,
                "HasNotes": False,
                "IsAuditEnabled": audit(),
                "EntitySetName": t["entity_set"],
                "Attributes": [primary_attr],
            }
            self.dv.post("EntityDefinitions", payload)
            ok(f"{name} creata")
            if not self.dv.dry_run:
                meta = self.dv.get(f"EntityDefinitions(LogicalName='{name}')?$select=EntitySetName")
                if meta and meta.get("EntitySetName") != t["entity_set"]:
                    warn(f"EntitySetName di {name} = {meta.get('EntitySetName')} (atteso {t['entity_set']}): "
                         "aggiornare i flussi o rinominare l'entity set")

    # --------------------------------------------------------------- 4 colonne
    def step_columns(self) -> None:
        header("Colonne")
        for name, t in self.schema["tables"].items():
            created = 0
            for col in t["columns"]:
                if col["type"] == "lookup":
                    continue
                if self.attr_exists(name, col["name"]):
                    continue
                payload = attribute_payload(self.dv, col, {col["choice"]: self.optionset_id(col["choice"])}
                                            if col["type"] == "choice" else None)
                self.dv.post(f"EntityDefinitions(LogicalName='{name}')/Attributes", payload)
                created += 1
            ok(f"{name}: {created} colonne create")

    # ------------------------------------------------------------ 5 relazioni
    def step_relationships(self) -> None:
        header("Relazioni (colonne di ricerca)")
        for name, t in self.schema["tables"].items():
            for col in t["columns"]:
                if col["type"] != "lookup":
                    continue
                rel = col["relationship"]
                if not self.dv.dry_run and self.dv.get(f"RelationshipDefinitions(SchemaName='{rel}')?$select=SchemaName"):
                    skip(rel)
                    continue
                self.dv.post("RelationshipDefinitions", relationship_payload(self.dv, name, col))
                ok(f"{name}.{col['name']} -> {col['target']} ({rel})")

    # ---------------------------------------------------------------- 6 chiavi
    def step_keys(self) -> None:
        header("Chiavi alternative")
        for name, t in self.schema["tables"].items():
            for key in t.get("alternate_keys", []):
                if not self.dv.dry_run:
                    found = self.dv.get(
                        f"EntityDefinitions(LogicalName='{name}')/Keys?$select=SchemaName"
                        f"&$filter=SchemaName eq '{key['name']}'")
                    if found and found.get("value"):
                        skip(key["name"])
                        continue
                self.dv.post(f"EntityDefinitions(LogicalName='{name}')/Keys", {
                    "@odata.type": "Microsoft.Dynamics.CRM.EntityKeyMetadata",
                    "SchemaName": key["name"],
                    "DisplayName": self.dv.label(key["display_name"]),
                    "KeyAttributes": key["columns"],
                })
                ok(f"{name}: {key['name']}")

    # ------------------------------------------------------------- 7 publish
    def step_publish(self) -> None:
        header("Pubblicazione personalizzazioni")
        self.dv.post("PublishAllXml", {}, solution_aware=False)
        ok("PublishAllXml eseguito")

    # --------------------------------------------------- 8 variabili ambiente
    def step_envvars(self) -> None:
        header("Variabili d'ambiente")
        values = self.cfg.get("variabili_ambiente", {})
        for ev in self.schema.get("environment_variables", []):
            existing = self.dv.first(
                "environmentvariabledefinitions?$select=environmentvariabledefinitionid"
                f"&$filter=schemaname eq '{ev['name']}'")
            if existing:
                def_id = existing["environmentvariabledefinitionid"]
                skip(ev["name"])
            else:
                res = self.dv.post("environmentvariabledefinitions", {
                    "schemaname": ev["name"],
                    "displayname": ev["display_name"],
                    "description": ev.get("description", ""),
                    "type": 100000000,  # Testo
                    "defaultvalue": ev.get("default", ""),
                })
                def_id = (res or {}).get("_id")
                ok(ev["name"])
            value = values.get(ev["name"])
            if value and def_id:
                cur = self.dv.first(
                    "environmentvariablevalues?$select=environmentvariablevalueid"
                    f"&$filter=_environmentvariabledefinitionid_value eq {def_id}")
                if cur:
                    self.dv.patch(f"environmentvariablevalues({cur['environmentvariablevalueid']})", {"value": value})
                else:
                    self.dv.post("environmentvariablevalues", {
                        "schemaname": f"{ev['name']}_valore",
                        "value": value,
                        "EnvironmentVariableDefinitionId@odata.bind": f"/environmentvariabledefinitions({def_id})",
                    })
                ok(f"{ev['name']} = {value}")

    # ------------------------------------------------ 9 riferimenti connessione
    def step_connrefs(self) -> None:
        header("Riferimenti di connessione")
        for cr in self.schema.get("connection_references", []):
            if self.dv.first("connectionreferences?$select=connectionreferenceid"
                             f"&$filter=connectionreferencelogicalname eq '{cr['name']}'"):
                skip(cr["name"])
                continue
            self.dv.post("connectionreferences", {
                "connectionreferencelogicalname": cr["name"],
                "connectionreferencedisplayname": cr["display_name"],
                "connectorid": f"/providers/Microsoft.PowerApps/apis/{cr['connector']}",
                "description": "Gestione ore formazione",
            })
            ok(f"{cr['name']} ({cr['connector']})")
        info("Collegare ogni riferimento a una connessione dalla soluzione (vedi docs/04-installazione.md)")

    # ------------------------------------------------------- 10 ruoli sicurezza
    def privilege_id(self, name: str) -> str | None:
        if self.dv.dry_run:
            return "00000000-0000-0000-0000-000000000000"
        p = self.dv.first(f"privileges?$select=privilegeid,name&$filter=name eq '{name}'")
        return p["privilegeid"] if p else None

    def step_roles(self) -> None:
        header("Ruoli di sicurezza")
        bu = self.root_bu()
        for role_name, role in self.schema.get("security_roles", {}).items():
            existing = self.dv.first(
                f"roles?$select=roleid&$filter=name eq '{role_name}' and _businessunitid_value eq {bu}")
            if existing:
                role_id = existing["roleid"]
                skip(role_name)
            else:
                res = self.dv.post("roles", {
                    "name": role_name,
                    "description": role.get("description", ""),
                    "businessunitid@odata.bind": f"/businessunits({bu})",
                })
                role_id = (res or {}).get("_id", "<nuovo-ruolo>")
                ok(f"{role_name} creato")
            self._roles[role_name] = role_id
            privileges = []
            for table, accesses in role["privileges"].items():
                for access, depth in accesses.items():
                    pname = f"prv{PRIV_ACCESS[access]}{table}"
                    pid = self.privilege_id(pname)
                    if not pid:
                        warn(f"privilegio {pname} non trovato (la tabella è stata pubblicata?)")
                        continue
                    privileges.append({"PrivilegeId": pid, "BusinessUnitId": bu,
                                       "Depth": DEPTH[depth], "PrivilegeName": pname})
            if privileges:
                self.dv.post(f"roles({role_id})/Microsoft.Dynamics.CRM.AddPrivilegesRole",
                             {"Privileges": privileges}, solution_aware=False)
                ok(f"{role_name}: {len(privileges)} privilegi assegnati")

    # ------------------------------------------- 11 sicurezza a livello colonna
    def step_colsec(self) -> None:
        header("Profili di sicurezza delle colonne")
        groups: dict[str, list[tuple[str, str]]] = {}
        for table, t in self.schema["tables"].items():
            for col in t["columns"]:
                if col.get("secured"):
                    groups.setdefault(col["secured"], []).append((table, col["name"]))
        for prof_name, prof in self.schema.get("column_security_profiles", {}).items():
            existing = self.dv.first(
                f"fieldsecurityprofiles?$select=fieldsecurityprofileid&$filter=name eq '{prof_name}'")
            if existing:
                prof_id = existing["fieldsecurityprofileid"]
                skip(prof_name)
            else:
                res = self.dv.post("fieldsecurityprofiles", {
                    "name": prof_name, "description": prof.get("description", "")})
                prof_id = (res or {}).get("_id", "<nuovo-profilo>")
                ok(f"{prof_name} creato")
            self._profiles[prof_name] = prof_id
            count = 0
            for group, perm in prof["groups"].items():
                for table, attr in groups.get(group, []):
                    body = {
                        "entityname": table,
                        "attributelogicalname": attr,
                        "canread": 4 if perm.get("read") else 0,
                        "cancreate": 4 if perm.get("create") else 0,
                        "canupdate": 4 if perm.get("update") else 0,
                    }
                    cur = None
                    if not self.dv.dry_run:
                        cur = self.dv.first(
                            "fieldpermissions?$select=fieldpermissionid"
                            f"&$filter=_fieldsecurityprofileid_value eq {prof_id} and entityname eq '{table}'"
                            f" and attributelogicalname eq '{attr}'")
                    if cur:
                        self.dv.patch(f"fieldpermissions({cur['fieldpermissionid']})", body)
                    else:
                        body["fieldsecurityprofileid@odata.bind"] = f"/fieldsecurityprofiles({prof_id})"
                        self.dv.post("fieldpermissions", body)
                    count += 1
            ok(f"{prof_name}: {count} permessi di colonna")

    # ----------------------------------------------------------------- 12 team
    def _lookup_ids(self) -> None:
        for role_name in self.schema.get("security_roles", {}):
            if role_name not in self._roles:
                r = self.dv.first(f"roles?$select=roleid&$filter=name eq '{role_name}' and "
                                  f"_businessunitid_value eq {self.root_bu()}")
                if r:
                    self._roles[role_name] = r["roleid"]
        for prof_name in self.schema.get("column_security_profiles", {}):
            if prof_name not in self._profiles:
                p = self.dv.first(f"fieldsecurityprofiles?$select=fieldsecurityprofileid&$filter=name eq '{prof_name}'")
                if p:
                    self._profiles[prof_name] = p["fieldsecurityprofileid"]

    def _associate(self, team_id: str, nav: str, entity_set: str, target_id: str) -> None:
        try:
            self.dv.post(f"teams({team_id})/{nav}/$ref",
                         {"@odata.id": f"{self.dv.base}{entity_set}({target_id})"}, solution_aware=False)
        except DataverseError as exc:  # già associato
            if "duplicate" not in str(exc).lower() and "already" not in str(exc).lower():
                raise

    def step_teams(self) -> None:
        header("Team collegati ai gruppi Entra ID")
        groups_cfg = self.cfg.get("gruppi_entra", {})
        if not any(groups_cfg.values()):
            warn("nessun gruppo Entra configurato in config.json: creare i team manualmente "
                 "(docs/03-sicurezza.md)")
            return
        if not self.dv.dry_run:
            self._lookup_ids()
        for team_name, team in self.schema.get("teams", {}).items():
            group_id = groups_cfg.get(team["entra_group_config_key"])
            if not group_id:
                warn(f"{team_name}: gruppo Entra non indicato, saltato")
                continue
            existing = self.dv.first(f"teams?$select=teamid&$filter=azureactivedirectoryobjectid eq {group_id}")
            if existing:
                team_id = existing["teamid"]
                skip(team_name)
            else:
                res = self.dv.post("teams", {
                    "name": team_name,
                    "teamtype": 2,             # Gruppo di sicurezza Microsoft Entra
                    "membershiptype": 0,       # Membri e ospiti
                    "azureactivedirectoryobjectid": group_id,
                    "businessunitid@odata.bind": f"/businessunits({self.root_bu()})",
                }, solution_aware=False)
                team_id = (res or {}).get("_id", "<nuovo-team>")
                ok(f"{team_name} creato")
            for role_name in team.get("roles", []):
                if role_name in self._roles or self.dv.dry_run:
                    self._associate(team_id, "teamroles_association", "roles", self._roles.get(role_name, "<ruolo>"))
                    ok(f"{team_name} ← ruolo {role_name}")
            for prof_name in team.get("column_profiles", []):
                if prof_name in self._profiles or self.dv.dry_run:
                    self._associate(team_id, "teamprofiles_association", "fieldsecurityprofiles",
                                    self._profiles.get(prof_name, "<profilo>"))
                    ok(f"{team_name} ← profilo colonne {prof_name}")

    # ---------------------------------------------------------------- 13 flussi
    def step_flows(self) -> None:
        header("Flussi cloud Power Automate")
        flow_dir = REPO / "powerautomate" / "flows"
        files = sorted(flow_dir.glob("*.json"))
        if not files:
            warn(f"nessun flusso trovato in {flow_dir}")
            return
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            name = data["name"]
            clientdata = json.dumps(data["clientdata"], ensure_ascii=False)
            existing = self.dv.first(
                f"workflows?$select=workflowid,statecode&$filter=name eq '{name}' and category eq 5")
            if existing:
                if self.args.update_flows:
                    if existing.get("statecode") == 1:
                        warn(f"{name}: è attivo, disattivarlo prima di aggiornarlo")
                        continue
                    self.dv.patch(f"workflows({existing['workflowid']})", {
                        "clientdata": clientdata, "description": data.get("description", "")})
                    ok(f"{name} aggiornato")
                else:
                    skip(name)
                continue
            self.dv.post("workflows", {
                "category": 5,          # Flusso cloud moderno
                "type": 1,              # Definizione
                "primaryentity": "none",
                "name": name,
                "description": data.get("description", ""),
                "clientdata": clientdata,
            })
            ok(f"{name} creato (spento)")
        info("Accendere i flussi dopo aver collegato i riferimenti di connessione")

    # ----------------------------------------------------------------- 14 seed
    def step_seed(self) -> None:
        header("Dati di esempio (solo ambienti di test)")
        seed_dir = ROOT / "seed"
        area_map = {o["label"]: o["value"] for o in self.schema["choices"]["sdf_area"]["options"]}
        modal_map = {o["label"]: o["value"] for o in self.schema["choices"]["sdf_modalita"]["options"]}
        ente_map = {o["label"]: o["value"] for o in self.schema["choices"]["sdf_tipoente"]["options"]}

        def rows(file: str):
            path = seed_dir / file
            if not path.exists():
                return []
            with path.open(encoding="utf-8-sig", newline="") as fh:
                return list(csv.DictReader(fh, delimiter=";"))

        def to_bool(v: str) -> bool:
            return v.strip().lower() in ("si", "sì", "true", "1", "yes")

        def to_num(v: str) -> float | None:
            v = v.strip().replace(",", ".")
            return float(v) if v else None

        for r in rows("strutture.csv"):
            flt = (f"sdf_name eq '{r['Servizio'].replace(chr(39), chr(39) * 2)}' "
                   f"and sdf_centrodicosto eq '{r['Centro di costo']}'")
            if self.dv.first(f"sdf_strutture?$select=sdf_strutturaorganizzativaid&$filter={flt}"):
                skip(r["Servizio"])
                continue
            body = {
                "sdf_name": r["Servizio"],
                "sdf_area": area_map[r["Area"]],
                "sdf_centrodicosto": r["Centro di costo"],
                "sdf_emailcoordinatoreservizio": r.get("E-mail coordinatore servizio") or None,
                "sdf_upncoordinatoreservizio": (r.get("E-mail coordinatore servizio") or "").lower() or None,
                "sdf_attiva": True,
            }
            self.dv.post("sdf_strutture", body, solution_aware=False)
            ok(f"struttura {r['Servizio']}")

        for r in rows("corsi.csv"):
            if self.dv.first(f"sdf_corsi?$select=sdf_corsoid&$filter=sdf_codicecorso eq '{r['Codice univoco corso']}'"):
                skip(r["Codice univoco corso"])
                continue
            body = {
                "sdf_codicecorso": r["Codice univoco corso"],
                "sdf_name": r["Titolo corso"],
                "sdf_descrizione": r.get("Descrizione") or None,
                "sdf_tipoente": ente_map[r["Ente erogatore"]],
                "sdf_nomeente": r.get("Nome ente erogatore") or None,
                "sdf_tipologia": r.get("Tipologia") or None,
                "sdf_modalita": modal_map[r["Modalità di svolgimento"]],
                "sdf_duratacorso": to_num(r.get("Durata corso (ore)", "")),
                "sdf_gettoneprevisto": to_bool(r.get("Gettone previsto", "")),
                "sdf_attivo": to_bool(r.get("Corso attivo", "sì")),
                "sdf_piugiornate": to_bool(r.get("Più giornate formative", "")),
                "sdf_origine": 741500000,
                "sdf_statovalidazione": 741500001,
            }
            self.dv.post("sdf_corsi", body, solution_aware=False)
            ok(f"corso {r['Codice univoco corso']}")

    # ------------------------------------------------------------------ run
    def run(self, steps: list[str]) -> None:
        for step in steps:
            getattr(self, f"step_{step}")()


# =============================================================================
#  Validazione dello schema (eseguita sempre, anche in dry-run)
# =============================================================================
def validate_schema(schema: dict) -> list[str]:
    errors: list[str] = []
    prefix = schema["publisher"]["customizationprefix"] + "_"
    opt_prefix = str(schema["publisher"]["customizationoptionvalueprefix"])
    tables = schema["tables"]
    for name, ch in schema["choices"].items():
        if not name.startswith(prefix):
            errors.append(f"scelta {name}: manca il prefisso {prefix}")
        for o in ch["options"]:
            if not str(o["value"]).startswith(opt_prefix):
                errors.append(f"scelta {name}: valore {o['value']} senza prefisso {opt_prefix}")
    rel_names: set[str] = set()
    for tname, t in tables.items():
        if not tname.startswith(prefix):
            errors.append(f"tabella {tname}: manca il prefisso")
        seen = {t["primary"]["name"]}
        display = {t["primary"]["display_name"].lower()}
        for col in t["columns"]:
            n = col["name"]
            if n != n.lower() or not n.startswith(prefix):
                errors.append(f"{tname}.{n}: nome non valido (minuscolo con prefisso)")
            if n in seen:
                errors.append(f"{tname}.{n}: colonna duplicata")
            seen.add(n)
            dn = col["display_name"].lower()
            if dn in display:
                errors.append(f"{tname}.{n}: nome visualizzato duplicato '{col['display_name']}'")
            display.add(dn)
            if col["type"] == "choice" and col["choice"] not in schema["choices"]:
                errors.append(f"{tname}.{n}: scelta {col['choice']} inesistente")
            if col["type"] == "lookup":
                if col["target"] not in tables and col["target"] != "systemuser":
                    errors.append(f"{tname}.{n}: tabella di destinazione {col['target']} inesistente")
                if col["relationship"] in rel_names:
                    errors.append(f"{tname}.{n}: relazione {col['relationship']} duplicata")
                rel_names.add(col["relationship"])
            if col.get("secured"):
                groups = {g for p in schema["column_security_profiles"].values() for g in p["groups"]}
                if col["secured"] not in groups:
                    errors.append(f"{tname}.{n}: gruppo di sicurezza colonna {col['secured']} non usato da nessun profilo")
        for key in t.get("alternate_keys", []):
            for c in key["columns"]:
                if c not in seen:
                    errors.append(f"{tname}: chiave {key['name']} su colonna inesistente {c}")
    for role, r in schema["security_roles"].items():
        for table, acc in r["privileges"].items():
            if table not in tables:
                errors.append(f"ruolo {role}: tabella {table} inesistente")
            for a, d in acc.items():
                if a not in PRIV_ACCESS or d not in DEPTH:
                    errors.append(f"ruolo {role}: {table}.{a}={d} non valido")
    for team, tm in schema.get("teams", {}).items():
        for r in tm.get("roles", []):
            if r not in schema["security_roles"]:
                errors.append(f"team {team}: ruolo {r} inesistente")
        for p in tm.get("column_profiles", []):
            if p not in schema["column_security_profiles"]:
                errors.append(f"team {team}: profilo {p} inesistente")
    return errors


# =============================================================================
#  main
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Provisioning Dataverse - Gestione ore formazione")
    parser.add_argument("--config", default=str(ROOT / "config.json"), help="file di configurazione JSON")
    parser.add_argument("--schema", default=str(ROOT / "schema.yaml"), help="modello dati YAML")
    parser.add_argument("--url", help="URL dell'ambiente (sovrascrive config.json)")
    parser.add_argument("--auth", choices=["azcli", "devicecode", "interactive", "env"], default="azcli")
    parser.add_argument("--steps", default=",".join(DEFAULT_STEPS),
                        help=f"passi separati da virgola. Disponibili: {', '.join(ALL_STEPS)}")
    parser.add_argument("--update-flows", action="store_true", help="aggiorna i flussi già esistenti (se spenti)")
    parser.add_argument("--dry-run", action="store_true", help="mostra le operazioni senza eseguirle")
    args = parser.parse_args()

    schema = yaml.safe_load(Path(args.schema).read_text(encoding="utf-8"))
    errors = validate_schema(schema)
    if errors:
        print("Errori nello schema:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    cfg: dict = {}
    if Path(args.config).exists():
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    elif not args.dry_run:
        sys.exit(f"File di configurazione non trovato: {args.config} (copiare config.example.json)")
    url = args.url or cfg.get("environment_url") or "https://ambiente.crm4.dynamics.com"
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = [s for s in steps if s not in ALL_STEPS]
    if unknown:
        sys.exit(f"Passi sconosciuti: {', '.join(unknown)}")

    print(f"Ambiente: {url}{'  [DRY-RUN]' if args.dry_run else ''}")
    print(f"Passi: {', '.join(steps)}")
    token = None if args.dry_run else get_token(args.auth, url, cfg)
    dv = Dataverse(url, token, schema["solution"]["uniquename"], args.dry_run)
    dv.detect_language()
    try:
        Provisioner(dv, schema, cfg, args).run(steps)
    except DataverseError as exc:
        print(f"\nERRORE: {exc}")
        sys.exit(2)
    print("\nCompletato.")


if __name__ == "__main__":
    main()
