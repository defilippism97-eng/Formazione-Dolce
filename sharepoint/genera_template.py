#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera, a partire da sharepoint/schema.yaml:

  - sharepoint/template/GestioneFormazione.xml   modello di provisioning PnP (schema 2022/09)
  - docs/02-modello-dati.md                      documentazione del modello dati
  - docs/06-api-flussi.md                        tabella "Oggetto Richiesta (JSON)"

Uso:
    python sharepoint/genera_template.py
    python sharepoint/genera_template.py --xsd percorso/ProvisioningSchema-2022-09.xsd   # valida l'XML
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
PNP_NS = "http://schemas.dev.office.com/PnP/2022/09/ProvisioningSchema"
TITLE_FIELD_ID = "fa564e0f-0c70-4ab9-b863-0177e6ddd247"
NS_UUID = uuid.UUID("6f1d3b8e-7a51-4c0e-9d0f-5d0c1e2f3a4b")  # namespace fisso: GUID stabili tra le generazioni

PRINCIPAL = {"owners": "{associatedownergroup}", "everyone": "{everyonebutexternalusers}"}
ROLE = {r: "{roledefinition:%s}" % r for r in ("Reader", "Contributor", "Editor", "Administrator")}

TIPI_DOC = {
    "text": "Testo (una riga)", "note": "Testo (più righe)", "number": "Numero (2 decimali)",
    "int": "Numero intero", "bool": "Sì/No", "date": "Data", "datetime": "Data e ora",
    "choice": "Scelta", "user": "Persona", "url": "Collegamento ipertestuale",
}
TIPI_JSON = {
    "text": "testo", "note": "testo", "number": "numero", "int": "numero intero", "bool": "booleano",
    "date": "testo `yyyy-MM-dd`", "datetime": "testo ISO 8601 UTC", "choice": "testo (etichetta)",
    "url": "testo (URL)", "user": "testo",
}


def field_id(list_name: str, col: str) -> str:
    return str(uuid.uuid5(NS_UUID, f"{list_name}.{col}"))


def attr(name: str, value) -> str:
    if isinstance(value, bool):
        value = "TRUE" if value else "FALSE"
    return f" {name}={quoteattr(str(value))}"


# =============================================================================
#  Campi (CAML)
# =============================================================================
def field_xml(list_name: str, col: dict, choices: dict) -> str:
    t = col["type"]
    a = attr("ID", "{" + field_id(list_name, col["name"]) + "}")
    a += attr("Name", col["name"]) + attr("StaticName", col["name"]) + attr("DisplayName", col["display_name"])
    a += attr("Required", bool(col.get("required", False)))
    if col.get("description"):
        a += attr("Description", col["description"])
    if col.get("indexed") or col.get("unique"):
        a += attr("Indexed", True)
    if col.get("unique"):
        a += attr("EnforceUniqueValues", True)
    inner = ""
    if t == "text":
        a = attr("Type", "Text") + a + attr("MaxLength", col.get("max_length", 255))
    elif t == "note":
        a = attr("Type", "Note") + a + attr("NumLines", 6) + attr("RichText", False) + \
            attr("AppendOnly", False) + attr("UnlimitedLengthInDocumentLibrary", False)
    elif t in ("number", "int"):
        a = attr("Type", "Number") + a + attr("Decimals", 2 if t == "number" else 0) + attr("Min", 0)
    elif t == "bool":
        a = attr("Type", "Boolean") + a
        inner = f"<Default>{1 if col.get('default') else 0}</Default>"
    elif t in ("date", "datetime"):
        a = attr("Type", "DateTime") + a + attr("Format", "DateOnly" if t == "date" else "DateTime") + \
            attr("FriendlyDisplayFormat", "Disabled")
    elif t == "choice":
        a = attr("Type", "Choice") + a + attr("Format", "Dropdown") + attr("FillInChoice", False)
        opts = "".join(f"<CHOICE>{escape(o)}</CHOICE>" for o in choices[col["choice"]])
        default = f"<Default>{escape(col['default'])}</Default>" if col.get("default") else ""
        inner = f"{default}<CHOICES>{opts}</CHOICES>"
    elif t == "user":
        a = attr("Type", "User") + a + attr("List", "UserInfo") + attr("ShowField", "ImnName") + \
            attr("UserSelectionMode", "PeopleOnly") + attr("UserSelectionScope", 0)
    elif t == "url":
        a = attr("Type", "URL") + a + attr("Format", "Hyperlink")
    else:
        raise ValueError(f"Tipo non gestito: {t}")
    return f"<Field{a}>{inner}</Field>" if inner else f"<Field{a} />"


def view_xml(lst: dict, view: dict) -> str:
    is_library = lst["template"] == 101
    fields = view["fields"]
    if is_library:
        fields = ["DocIcon", "LinkFilename"] + [f for f in fields if f not in ("DocIcon", "LinkFilename")]
    vf = "".join(f'<FieldRef Name="{f}" />' for f in fields)
    query = ""
    if view.get("where_stato"):
        query += ('<Where><Eq><FieldRef Name="Stato" /><Value Type="Choice">'
                  f'{escape(view["where_stato"])}</Value></Eq></Where>')
    if view.get("order_by"):
        query += (f'<OrderBy><FieldRef Name="{view["order_by"]}" '
                  f'Ascending="{"TRUE" if view.get("ascending", True) else "FALSE"}" /></OrderBy>')
    a = attr("DisplayName", view["name"]) + attr("DefaultView", bool(view.get("default", False)))
    a += attr("MobileView", True) + attr("Type", "HTML")
    return (f"<View{a}><Query>{query}</Query><ViewFields>{vf}</ViewFields>"
            f'<RowLimit Paged="TRUE">50</RowLimit></View>')


def security_xml(perm, indent: str) -> str:
    if perm == "inherit" or not perm:
        return ""
    br = perm["break"]
    lines = [f'{indent}<pnp:Security>',
             f'{indent}  <pnp:BreakRoleInheritance CopyRoleAssignments="{str(br.get("copy", True)).lower()}" '
             f'ClearSubscopes="true">']
    for ra in br.get("add", []):
        principal = PRINCIPAL.get(ra["principal"], ra["principal"])
        lines.append(f'{indent}    <pnp:RoleAssignment Principal={quoteattr(principal)} '
                     f'RoleDefinition="{ROLE[ra["role"]]}" />')
    lines += [f'{indent}  </pnp:BreakRoleInheritance>', f'{indent}</pnp:Security>']
    return "\n".join(lines)


# =============================================================================
#  Modello PnP
# =============================================================================
def build_template(s: dict) -> str:
    choices = s["choices"]
    out: list[str] = []
    w = out.append
    w('<?xml version="1.0" encoding="utf-8"?>')
    w("<!-- Generato da sharepoint/genera_template.py a partire da sharepoint/schema.yaml: non modificare a mano -->")
    w(f'<pnp:Provisioning xmlns:pnp="{PNP_NS}">')
    w('  <pnp:Preferences Generator="Formazione-Dolce/sharepoint/genera_template.py" />')
    w('  <pnp:Templates ID="GestioneFormazione-Contenitore">')
    w(f'    <pnp:ProvisioningTemplate ID="GestioneFormazione" Version="1" '
      f'DisplayName={quoteattr(s["site"]["title"])} Scope="RootSite">')
    # --- Sicurezza del sito
    w('      <pnp:Security>')
    w('        <pnp:SiteGroups>')
    for g in s["groups"]:
        w(f'          <pnp:SiteGroup Title={quoteattr(g["name"])} Description={quoteattr(g["description"])} '
          'Owner="{associatedownergroup}" AllowMembersEditMembership="false" AllowRequestToJoinLeave="false" '
          'AutoAcceptRequestToJoinLeave="false" OnlyAllowMembersViewMembership="true" />')
    w('        </pnp:SiteGroups>')
    w('        <pnp:Permissions>')
    w('          <pnp:RoleAssignments>')
    for g in s["groups"]:
        if g.get("site_role"):
            w(f'            <pnp:RoleAssignment Principal={quoteattr(g["name"])} RoleDefinition="{ROLE[g["site_role"]]}" />')
    w('          </pnp:RoleAssignments>')
    w('        </pnp:Permissions>')
    w('      </pnp:Security>')
    # --- Liste
    w('      <pnp:Lists>')
    for lname, lst in s["lists"].items():
        is_library = lst["template"] == 101
        url = lname if is_library else f"Lists/{lname}"
        a = attr("Title", lst["title"]) + attr("Description", lst.get("description", ""))
        a += attr("TemplateType", lst["template"]) + attr("Url", url)
        a += attr("OnQuickLaunch", "true") + attr("EnableVersioning", "true" if lst.get("versioning") else "false")
        if lst.get("versioning"):
            a += attr("MaxVersionLimit", 100)
        a += attr("EnableFolderCreation", "true" if is_library else "false")
        a += attr("NoCrawl", "true") + attr("ContentTypesEnabled", "false") + attr("RemoveExistingContentTypes", "false")
        w(f"        <pnp:ListInstance{a}>")
        if lst.get("views"):
            w('          <pnp:Views RemoveExistingViews="true">')
            for v in lst["views"]:
                w(f"            {view_xml(lst, v)}")
            w('          </pnp:Views>')
        w('          <pnp:Fields>')
        for col in lst["columns"]:
            w(f"            {field_xml(lname, col, choices)}")
        w('          </pnp:Fields>')
        if lst.get("title_display") and not is_library:
            required = "true" if lname not in ("RichiesteFormazione",) else "false"
            w('          <pnp:FieldRefs>')
            w(f'            <pnp:FieldRef ID="{TITLE_FIELD_ID}" Name="Title" '
              f'DisplayName={quoteattr(lst["title_display"])} Required="{required}" />')
            w('          </pnp:FieldRefs>')
        if lst.get("rows"):
            w('          <pnp:DataRows KeyColumn="Title" UpdateBehavior="Skip">')
            for row in lst["rows"]:
                w('            <pnp:DataRow>')
                for k, v in row.items():
                    w(f'              <pnp:DataValue FieldName={quoteattr(k)}>{escape(str(v))}</pnp:DataValue>')
                w('            </pnp:DataRow>')
            w('          </pnp:DataRows>')
        sec = security_xml(lst.get("permissions"), "          ")
        if sec:
            w(sec)
        w("        </pnp:ListInstance>")
    w('      </pnp:Lists>')
    w('    </pnp:ProvisioningTemplate>')
    w('  </pnp:Templates>')
    w('</pnp:Provisioning>')
    return "\n".join(out) + "\n"


# =============================================================================
#  Documentazione
# =============================================================================
def principal_label(p: str) -> str:
    return {"owners": "Proprietari del sito", "everyone": "Tutti tranne gli utenti esterni"}.get(p, p)


ROLE_LABEL = {"Reader": "Lettura", "Contributor": "Collaborazione", "Editor": "Modifica",
              "Administrator": "Controllo completo"}


def build_doc(s: dict) -> str:
    out: list[str] = []
    w = out.append
    w("# 2. Modello dati SharePoint")
    w("")
    w("> Documento generato automaticamente da `sharepoint/schema.yaml` con "
      "`python sharepoint/genera_template.py`. Non modificarlo a mano.")
    w("")
    w(f"Sito: **{s['site']['title']}** (indirizzo suggerito `{s['site']['url_suggerito']}`), "
      "sito del team **senza** gruppo Microsoft 365, lingua italiana.")
    w("")
    w("Le colonne si leggono così: *nome visualizzato* (usato dall'app Power Apps) e `nome interno` "
      "(usato dai flussi e nei filtri). Le colonne indicizzate (🔎) permettono di filtrare liste oltre la "
      "soglia dei 5.000 elementi. I collegamenti tra liste sono ID numerici (es. *ID lavoratore*).")
    w("")
    w("## Gruppi e permessi")
    w("")
    w("| Gruppo | Descrizione | Permesso sul sito |")
    w("|---|---|---|")
    w("| Proprietari del sito | Amministratori applicativi e account di servizio dei flussi | Controllo completo |")
    for g in s["groups"]:
        w(f"| {g['name']} | {g['description']} | {ROLE_LABEL.get(g.get('site_role', ''), '—')} |")
    w("")
    w("| Lista / raccolta | Permessi |")
    w("|---|---|")
    for lname, lst in s["lists"].items():
        p = lst.get("permissions")
        if p == "inherit":
            desc = "ereditati dal sito (Proprietari: controllo completo; Formazione - HR: lettura)"
        else:
            br = p["break"]
            parts = ["ereditati dal sito" if br.get("copy", True) else "ereditarietà interrotta"]
            parts += [f"+ {principal_label(r['principal'])}: {ROLE_LABEL[r['role']]}" for r in br["add"]]
            desc = " ".join(parts)
        if lname == "AllegatiFormazione":
            desc += "; ogni cartella coordinatore è condivisa in lettura con il coordinatore (flusso API03)"
        w(f"| {lst['title']} | {desc} |")
    w("")
    w("## Liste e raccolte")
    for lname, lst in s["lists"].items():
        w("")
        kind = "Raccolta documenti" if lst["template"] == 101 else "Lista"
        url = lname if lst["template"] == 101 else f"Lists/{lname}"
        w(f"### {lst['title']}")
        w("")
        w(f"{kind} · URL `{url}` · {lst.get('description', '')}")
        w("")
        w("| Nome visualizzato | Nome interno | Tipo | Dettagli |")
        w("|---|---|---|---|")
        if lst.get("title_display"):
            w(f"| **{lst['title_display']}** | `Title` | Testo (una riga) | colonna titolo rinominata |")
        for c in lst["columns"]:
            d: list[str] = []
            if c["type"] == "choice":
                d.append("valori: " + ", ".join(s["choices"][c["choice"]]))
            if c.get("required"):
                d.append("obbligatoria")
            if c.get("unique"):
                d.append("valori univoci")
            if "default" in c:
                dv = c["default"]
                d.append(f"predefinito: {'Sì' if dv is True else 'No' if dv is False else dv}")
            if c.get("indexed") or c.get("unique"):
                d.append("🔎 indicizzata")
            if c.get("description"):
                d.append(c["description"])
            w(f"| {c['display_name']} | `{c['name']}` | {TIPI_DOC[c['type']]} | {'; '.join(d)} |")
        if lst.get("rows"):
            w("")
            w("Valori iniziali:")
            w("")
            w("| Chiave | Valore | Descrizione |")
            w("|---|---|---|")
            for r in lst["rows"]:
                val = str(r.get("Valore", ""))
                if len(val) > 70:
                    val = val[:67] + "..."
                w(f"| `{r['Title']}` | `{val}` | {r.get('Descrizione', '')} |")
    w("")
    w("## Colori degli stati")
    w("")
    w("| Stato | Colore |")
    w("|---|---|")
    for st, col in s["colori_stato"].items():
        w(f"| {st} | `{col}` |")
    w("")
    return "\n".join(out)


def build_json_table(s: dict) -> str:
    lst = s["lists"]["RichiesteFormazione"]
    rows = ["| Campo JSON | Colonna SharePoint (nome interno) | Nome visualizzato | Tipo JSON |",
            "|---|---|---|---|",
            "| `id` | `ID` | ID | numero intero |",
            f"| `{lst['title_json']}` | `Title` | {lst['title_display']} | testo |"]
    for c in lst["columns"]:
        rows.append(f"| `{c['json']}` | `{c['name']}` | {c['display_name']} | {TIPI_JSON[c['type']]} |")
    rows += ["| `creato` | `Created` | Creato | testo ISO 8601 UTC |",
             "| `modificato` | `Modified` | Modificato | testo ISO 8601 UTC |"]
    return "\n".join(rows) + "\n"


# =============================================================================
#  Controlli sullo schema
# =============================================================================
def validate_schema(s: dict) -> list[str]:
    errors = []
    group_names = {g["name"] for g in s["groups"]}
    for lname, lst in s["lists"].items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", lname):
            errors.append(f"{lname}: nome lista non valido")
        names, displays, indexed = set(), set(), 0
        if lst.get("title_display"):
            displays.add(lst["title_display"].lower())
        for c in lst["columns"]:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", c["name"]):
                errors.append(f"{lname}.{c['name']}: nome interno non valido")
            if c["name"] in names:
                errors.append(f"{lname}.{c['name']}: duplicato")
            names.add(c["name"])
            if c["display_name"].lower() in displays:
                errors.append(f"{lname}.{c['name']}: nome visualizzato duplicato")
            displays.add(c["display_name"].lower())
            if c["type"] not in TIPI_DOC:
                errors.append(f"{lname}.{c['name']}: tipo {c['type']} non valido")
            if c["type"] == "choice":
                if c["choice"] not in s["choices"]:
                    errors.append(f"{lname}.{c['name']}: scelta {c['choice']} inesistente")
                elif "default" in c and c["default"] not in s["choices"][c["choice"]]:
                    errors.append(f"{lname}.{c['name']}: valore predefinito non tra le scelte")
            if c.get("indexed") or c.get("unique"):
                indexed += 1
            if lname == "RichiesteFormazione" and "json" not in c:
                errors.append(f"{lname}.{c['name']}: manca la chiave json")
        if indexed > 20:
            errors.append(f"{lname}: più di 20 colonne indicizzate")
        p = lst.get("permissions")
        if p != "inherit":
            for r in p["break"]["add"]:
                if r["principal"] not in PRINCIPAL and r["principal"] not in group_names:
                    errors.append(f"{lname}: gruppo {r['principal']} inesistente")
                if r["role"] not in ROLE:
                    errors.append(f"{lname}: ruolo {r['role']} non valido")
    for st in s["choices"]["stato_richiesta"]:
        if st not in s["colori_stato"]:
            errors.append(f"colori_stato: manca {st}")
    return errors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xsd", help="schema XSD PnP 2022/09 per validare il modello generato")
    args = ap.parse_args()
    s = yaml.safe_load((ROOT / "schema.yaml").read_text(encoding="utf-8"))
    errors = validate_schema(s)
    if errors:
        print("Errori nello schema:\n  - " + "\n  - ".join(errors))
        sys.exit(1)

    xml = build_template(s)
    out = ROOT / "template" / "GestioneFormazione.xml"
    out.parent.mkdir(exist_ok=True)
    out.write_text(xml, encoding="utf-8")
    print(f"generato {out.relative_to(REPO)}")

    (REPO / "docs" / "02-modello-dati.md").write_text(build_doc(s), encoding="utf-8")
    print("generato docs/02-modello-dati.md")

    api = REPO / "docs" / "06-api-flussi.md"
    if api.exists():
        text = api.read_text(encoding="utf-8")
        new = re.sub(r"(<!-- TABELLA_RICHIESTA_JSON_INIZIO -->\n).*?(<!-- TABELLA_RICHIESTA_JSON_FINE -->)",
                     lambda m: m.group(1) + build_json_table(s) + m.group(2), text, flags=re.S)
        api.write_text(new, encoding="utf-8")
        print("aggiornata la tabella JSON in docs/06-api-flussi.md")

    if args.xsd:
        from lxml import etree
        schema = etree.XMLSchema(etree.parse(args.xsd))
        doc = etree.parse(str(out))
        if schema.validate(doc):
            print("XML valido rispetto allo schema PnP")
        else:
            for e in schema.error_log:
                print(f"  riga {e.line}: {e.message}")
            sys.exit(2)


if __name__ == "__main__":
    main()
