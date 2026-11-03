#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica statica delle definizioni dei flussi in powerautomate/flows/*.json

Controlla:
  - JSON valido e struttura dell'involucro (name, description, connectionReferences, definition);
  - nomi delle azioni unici e validi; runAfter verso azioni sorelle esistenti, stati validi, nessun ciclo;
  - riferimenti body()/outputs()/actions()/result()/items()/variables() verso azioni o variabili esistenti,
    raggiungibili (contenitore antenato) ed eseguite prima (predecessori nel grafo runAfter);
  - sintassi delle espressioni (parentesi, apici) e nomi delle funzioni;
  - parametri del trigger Power Apps (triggerBody()?['text_N'] esistenti);
  - riferimenti di connessione usati/dichiarati, operationId noti;
  - {{SITO_URL}} presente una sola volta nelle azioni (variabile SitoUrl);
  - InitializeVariable solo al primo livello; Response e Terminate mai dentro un ciclo;
  - colonne SharePoint (item/<Colonna>, $filter, $orderby) e valori delle scelte rispetto a sharepoint/schema.yaml
    (se PyYAML è installato).

Uso:  python3 powerautomate/verifica_flussi.py [cartella_flussi]
Esce con codice 1 se trova errori.
"""
import json
import os
import re
import sys
from collections import OrderedDict

QUI = os.path.dirname(os.path.abspath(__file__))
CARTELLA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(QUI, 'flows')
SCHEMA = os.path.join(QUI, '..', 'sharepoint', 'schema.yaml')

FUNZIONI = set('''
action actions add addDays addHours addMinutes addProperty addSeconds addToTime and array base64 base64ToBinary
base64ToString binary body bool chunk coalesce concat contains convertFromUtc convertTimeZone convertToUtc
createArray dataUri dataUriToBinary dataUriToString dateDifference dayOfMonth dayOfWeek dayOfYear decodeBase64
decodeDataUri decodeUriComponent div empty encodeUriComponent endsWith equals first float formatDateTime
formatNumber getFutureTime getPastTime greater greaterOrEquals guid if indexOf int intersection isFloat isInt item
items iterationIndexes join json last lastIndexOf length less lessOrEquals listCallbackUrl max min mod mul
multipartBody not nthIndexOf or outputs parameters parseDateTime rand range removeProperty replace result
reverse setProperty skip slice sort split startOfDay startOfHour startOfMonth startsWith string sub substring
subtractFromTime take ticks toLower toUpper trigger triggerBody triggerFormDataMultiValues triggerFormDataValue
triggerMultipartBody triggerOutputs trim union uriComponent uriComponentToBinary uriComponentToString uriHost
uriPath uriPathAndQuery uriPort uriQuery uriScheme utcNow variables workflow xml xpath
'''.split())
LETTERALI = {'true', 'false', 'null'}
STATI_RUNAFTER = {'Succeeded', 'Failed', 'Skipped', 'TimedOut'}
OPERAZIONI = {
    'shared_sharepointonline': {'GetItems', 'GetItem', 'PostItem', 'PatchItem', 'HttpRequest', 'CreateFile',
                                'PatchFileItem', 'CreateNewFolder', 'GrantAccess', 'GetItemChanges',
                                'GetOnUpdatedItems', 'GetOnDeletedItems', 'GetOnNewItems'},
    'shared_office365': {'SendEmailV2'},
    'shared_office365users': {'UserProfile_V2', 'MyProfile_V2'},
}
LISTE_GRANDI = {'Richieste formazione', 'Lavoratori', 'Registro modifiche', 'Catalogo corsi', 'Allegati formazione'}
CONTENITORI = ('actions', 'else', 'cases', 'default')


class Esito:
    def __init__(self):
        self.errori, self.avvisi = [], []

    def err(self, flusso, msg):
        self.errori.append('%s: %s' % (flusso, msg))

    def warn(self, flusso, msg):
        self.avvisi.append('%s: %s' % (flusso, msg))


# ---------------------------------------------------------------------------
# Espressioni
# ---------------------------------------------------------------------------
def estrai_espressioni(s):
    """Restituisce le espressioni contenute in una stringa (intera '@...' o interpolazioni '@{...}')."""
    if not isinstance(s, str) or '@' not in s:
        return []
    if s.startswith('@@'):
        return []
    if s.startswith('@') and not s.startswith('@{'):
        return [s[1:]]
    out, i = [], 0
    while True:
        j = s.find('@{', i)
        if j < 0:
            break
        k, in_str = j + 2, False
        while k < len(s):
            c = s[k]
            if in_str:
                if c == "'":
                    if k + 1 < len(s) and s[k + 1] == "'":
                        k += 1
                    else:
                        in_str = False
            elif c == "'":
                in_str = True
            elif c == '}':
                break
            k += 1
        if k >= len(s):
            out.append(('NON_CHIUSA', s[j:j + 60]))
            break
        out.append(s[j + 2:k])
        i = k + 1
    return out


def tokenizza(e):
    toks, i = [], 0
    while i < len(e):
        c = e[i]
        if c.isspace():
            i += 1
        elif c == "'":
            j, buf = i + 1, []
            while True:
                if j >= len(e):
                    raise ValueError('stringa non chiusa')
                if e[j] == "'":
                    if j + 1 < len(e) and e[j + 1] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    break
                buf.append(e[j])
                j += 1
            toks.append(('S', ''.join(buf)))
            i = j + 1
        elif c.isalpha() or c == '_':
            j = i
            while j < len(e) and (e[j].isalnum() or e[j] == '_'):
                j += 1
            toks.append(('I', e[i:j]))
            i = j
        elif c.isdigit() or (c == '-' and i + 1 < len(e) and e[i + 1].isdigit()):
            j = i + 1
            while j < len(e) and (e[j].isdigit() or e[j] == '.'):
                j += 1
            toks.append(('N', e[i:j]))
            i = j
        elif c in '()[],?.':
            toks.append(('P', c))
            i += 1
        else:
            raise ValueError('carattere inatteso %r' % c)
    return toks


def analizza(e):
    """Restituisce (chiamate, riferimenti, chiavi_trigger) oppure solleva ValueError."""
    toks = tokenizza(e)
    pila = []
    for t, v in toks:
        if t == 'P' and v in '([':
            pila.append(v)
        elif t == 'P' and v in ')]':
            if not pila or {')': '(', ']': '['}[v] != pila.pop():
                raise ValueError('parentesi non bilanciate')
    if pila:
        raise ValueError('parentesi non chiuse')
    chiamate, rif, chiavi = [], [], []
    for n, (t, v) in enumerate(toks):
        if t == 'I':
            succ = toks[n + 1] if n + 1 < len(toks) else None
            prec = toks[n - 1] if n > 0 else None
            if succ == ('P', '('):
                chiamate.append(v)
                if v in ('body', 'outputs', 'actions', 'result', 'items', 'variables'):
                    if n + 3 < len(toks) and toks[n + 2][0] == 'S' and toks[n + 3] == ('P', ')'):
                        rif.append((v, toks[n + 2][1]))
                    elif v != 'items' or toks[n + 2] != ('P', ')'):
                        raise ValueError('%s() senza nome letterale' % v)
                if v == 'triggerBody' and n + 6 < len(toks) and toks[n + 2] == ('P', ')') \
                        and toks[n + 3] == ('P', '?') and toks[n + 4] == ('P', '[') and toks[n + 5][0] == 'S':
                    chiavi.append(toks[n + 5][1])
            elif prec == ('P', '.'):
                pass
            elif v not in LETTERALI:
                raise ValueError('identificatore isolato %r' % v)
    return chiamate, rif, chiavi


def stringhe(obj, escludi_contenitori=False):
    """Tutte le stringhe (chiavi e valori) di un oggetto."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if escludi_contenitori and k in CONTENITORI:
                continue
            yield k
            yield from stringhe(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from stringhe(v)
    elif isinstance(obj, str):
        yield obj


# ---------------------------------------------------------------------------
# Struttura
# ---------------------------------------------------------------------------
def figli(nome, a):
    t = a.get('type')
    out = []
    if t == 'If':
        out.append(((nome, 'actions'), a.get('actions', {})))
        out.append(((nome, 'else'), (a.get('else') or {}).get('actions', {})))
    elif t in ('Foreach', 'Scope', 'Until'):
        out.append(((nome, 'actions'), a.get('actions', {})))
    elif t == 'Switch':
        for cn, c in (a.get('cases') or {}).items():
            out.append(((nome, 'case:' + cn), c.get('actions', {})))
        out.append(((nome, 'default'), (a.get('default') or {}).get('actions', {})))
    return out


def raccogli(azioni, cont, catena, info, contenitori, es, fl):
    contenitori[cont] = azioni
    for nome, a in azioni.items():
        if nome in info:
            es.err(fl, 'nome di azione duplicato: %s' % nome)
        if not re.match(r'^[A-Za-z0-9_]{1,80}$', nome):
            es.err(fl, 'nome di azione non valido: %s' % nome)
        info[nome] = {'cont': cont, 'catena': catena, 'azione': a, 'tipo': a.get('type')}
        for cid, sotto in figli(nome, a):
            raccogli(sotto, cid, catena + [(nome, cid)], info, contenitori, es, fl)


def predecessori(contenitore, nome):
    vis, pila = set(), [nome]
    while pila:
        n = pila.pop()
        for p in (contenitore.get(n, {}).get('runAfter') or {}):
            if p not in vis:
                vis.add(p)
                pila.append(p)
    return vis


def antenati(info, nome):
    """[(contenitore, rappresentante)] dal contenitore dell'azione fino alla radice."""
    out = [(info[nome]['cont'], nome)]
    for owner, cid in reversed(info[nome]['catena']):
        pass
    cat = info[nome]['catena']
    rep = nome
    for i in range(len(cat) - 1, -1, -1):
        owner = cat[i][0]
        out.append((info[owner]['cont'], owner))
        rep = owner
    return out


# ---------------------------------------------------------------------------
def carica_schema():
    try:
        import yaml
    except ImportError:
        return None
    if not os.path.exists(SCHEMA):
        return None
    with open(SCHEMA, encoding='utf-8') as fh:
        s = yaml.safe_load(fh)
    liste = {}
    for l in s['lists'].values():
        cols = {c['name']: c for c in l['columns']}
        liste[l['title']] = cols
    return liste, s['choices']


def verifica_colonne(fl, nome, a, schema, es):
    liste, scelte = schema
    p = a['inputs'].get('parameters', {})
    op = a['inputs']['host']['operationId']
    tab = p.get('table')
    if tab is None or op in ('HttpRequest', 'CreateFile'):
        return
    if tab not in liste:
        es.err(fl, '%s: lista sconosciuta %r' % (nome, tab))
        return
    cols = liste[tab]
    for k, v in p.items():
        if not k.startswith('item/'):
            continue
        parti = k.split('/')[1:]
        col = parti[0]
        if col == 'Title':
            continue
        if col not in cols:
            es.err(fl, '%s: colonna %r inesistente in %r' % (nome, col, tab))
            continue
        tipo = cols[col]['type']
        if tipo == 'choice':
            if parti[1:] != ['Value']:
                es.err(fl, '%s: la colonna scelta %r va scritta come item/%s/Value' % (nome, col, col))
            elif isinstance(v, str) and not v.startswith('@') and v not in scelte[cols[col]['choice']]:
                es.err(fl, '%s: valore %r non ammesso per %s' % (nome, v, col))
        elif len(parti) > 1:
            es.err(fl, '%s: %r non è una colonna scelta' % (nome, col))
    sistema = {'ID', 'Title', 'Created', 'Modified'}
    flt = p.get('$filter')
    if isinstance(flt, str):
        semplice = re.sub(r'@\{[^}]*\}', '0', flt)
        usate = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s+(?:eq|ne|ge|le|gt|lt)\b', semplice)
        for c in usate:
            if c not in cols and c not in sistema:
                es.err(fl, '%s: colonna %r nel filtro non esiste in %r' % (nome, c, tab))
        for c, val in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s+(?:eq|ne)\s+'([^'@]*)'", flt):
            if c in cols and cols[c]['type'] == 'choice' and val not in scelte[cols[c]['choice']]:
                es.err(fl, '%s: valore %r non ammesso per %s nel filtro' % (nome, val, c))
        if tab in LISTE_GRANDI and op == 'GetItems':
            if not any(c == 'ID' or (c in cols and cols[c].get('indexed')) for c in usate):
                es.warn(fl, '%s: filtro senza colonne indicizzate su %r (soglia 5000)' % (nome, tab))
    elif tab in LISTE_GRANDI and op == 'GetItems':
        es.warn(fl, '%s: lettura senza filtro su %r' % (nome, tab))
    ob = p.get('$orderby')
    if isinstance(ob, str):
        for c in re.findall(r'([A-Za-z_][A-Za-z0-9_]*)(?:\s+(?:asc|desc))?', ob):
            if c in ('asc', 'desc'):
                continue
            if c not in cols and c not in sistema:
                es.err(fl, '%s: colonna %r in $orderby non esiste' % (nome, c))
            elif tab in LISTE_GRANDI and c not in ('ID',) and not (c in cols and cols[c].get('indexed')):
                es.warn(fl, '%s: ordinamento su colonna non indicizzata %r (liste oltre 5000 elementi)' % (nome, c))


def verifica_file(percorso, schema, es):
    fl = os.path.basename(percorso)
    try:
        with open(percorso, encoding='utf-8') as fh:
            doc = json.load(fh, object_pairs_hook=OrderedDict)
    except Exception as ex:  # noqa: BLE001
        es.err(fl, 'JSON non valido: %s' % ex)
        return
    for k in ('name', 'description', 'connectionReferences', 'definition'):
        if k not in doc:
            es.err(fl, 'chiave mancante %r' % k)
            return
    if doc['name'] + '.json' != fl:
        es.err(fl, 'name %r diverso dal nome del file' % doc['name'])
    d = doc['definition']
    for k in ('$schema', 'contentVersion', 'parameters', 'triggers', 'actions'):
        if k not in d:
            es.err(fl, 'definition senza %r' % k)
            return
    if set(d['parameters']) != {'$connections', '$authentication'}:
        es.err(fl, 'parametri della definizione inattesi')
    if len(d['triggers']) != 1:
        es.err(fl, 'deve esserci un solo trigger')
    trig_nome, trig = next(iter(d['triggers'].items()))
    powerapps = trig.get('kind') == 'PowerAppV2'
    chiavi_trigger = set()
    if powerapps:
        sch = trig['inputs']['schema']
        chiavi_trigger = set(sch.get('properties', {}))
        if set(sch.get('required', [])) != chiavi_trigger:
            es.err(fl, 'tutti i parametri del trigger devono essere obbligatori')
        for k, v in sch.get('properties', {}).items():
            atteso = 'TEXT' if v.get('type') == 'string' else 'NUMBER'
            if not re.match(r'^(text|number)(_\d+)?$', k) or v.get('x-ms-content-hint') != atteso:
                es.err(fl, 'parametro del trigger non coerente: %s' % k)

    info, contenitori = OrderedDict(), {}
    raccogli(d['actions'], ('', 'root'), [], info, contenitori, es, fl)

    # runAfter
    for cid, azioni in contenitori.items():
        for nome, a in azioni.items():
            ra = a.get('runAfter')
            if ra is None:
                es.err(fl, '%s: runAfter mancante' % nome)
                continue
            for p, stati in ra.items():
                if p not in azioni:
                    es.err(fl, '%s: runAfter verso %r che non è un\'azione sorella' % (nome, p))
                if not stati or not set(stati) <= STATI_RUNAFTER:
                    es.err(fl, '%s: stati runAfter non validi %r' % (nome, stati))
            if nome in predecessori(azioni, nome):
                es.err(fl, '%s: ciclo nel grafo runAfter' % nome)
        primi = [n for n, a in azioni.items() if not a.get('runAfter')]
        if azioni and not primi:
            es.err(fl, 'contenitore %r senza azione iniziale' % (cid,))

    # variabili
    variabili = {}
    for nome, i in info.items():
        if i['tipo'] == 'InitializeVariable':
            if i['cont'] != ('', 'root'):
                es.err(fl, '%s: InitializeVariable deve stare al primo livello' % nome)
            for v in i['azione']['inputs']['variables']:
                variabili[v['name']] = nome

    # connessioni
    usate = set()
    for nome, i in info.items():
        a = i['azione']
        if i['tipo'] == 'OpenApiConnection':
            h = a['inputs']['host']
            usate.add(h['connectionName'])
            if h['connectionName'] not in doc['connectionReferences']:
                es.err(fl, '%s: connessione %r non dichiarata' % (nome, h['connectionName']))
            elif h['operationId'] not in OPERAZIONI.get(h['connectionName'], set()):
                es.err(fl, '%s: operationId sconosciuto %r' % (nome, h['operationId']))
            if h['apiId'] != '/providers/Microsoft.PowerApps/apis/' + h['connectionName']:
                es.err(fl, '%s: apiId non coerente' % nome)
            if a['inputs'].get('authentication') != "@parameters('$authentication')":
                es.err(fl, '%s: authentication mancante' % nome)
            if schema:
                verifica_colonne(fl, nome, a, schema, es)
        if i['tipo'] in ('Response', 'Terminate') and any(info[o]['tipo'] in ('Foreach', 'Until') for o, _ in i['catena']):
            es.err(fl, '%s: %s non può stare dentro un ciclo' % (nome, i['tipo']))
        if i['tipo'] == 'Response' and not powerapps:
            es.err(fl, '%s: risposta in un flusso senza trigger Power Apps' % nome)
        if i['tipo'] in ('SetVariable', 'AppendToArrayVariable') and a['inputs']['name'] not in variabili:
            es.err(fl, '%s: variabile %r non inizializzata' % (nome, a['inputs']['name']))
        if i['tipo'] == 'Foreach' and 'foreach' not in a:
            es.err(fl, '%s: Foreach senza "foreach"' % nome)
        if i['tipo'] == 'If' and 'expression' not in a:
            es.err(fl, '%s: If senza "expression"' % nome)
    th = trig.get('inputs', {}).get('host', {})
    if th.get('connectionName'):
        usate.add(th['connectionName'])
    for c in doc['connectionReferences']:
        if c not in usate:
            es.err(fl, 'connessione dichiarata ma non usata: %s' % c)

    # risposte Power Apps
    if powerapps:
        risposte = [i['azione'] for i in info.values() if i['tipo'] == 'Response']
        if not risposte:
            es.err(fl, 'flusso Power Apps senza risposta')
        schemi = {json.dumps(r['inputs']['schema'], sort_keys=True) for r in risposte}
        if len(schemi) > 1:
            es.err(fl, 'le risposte non hanno tutte lo stesso schema')
        for r in risposte:
            if set(r['inputs']['body']) != {'esito', 'messaggio', 'dati'}:
                es.err(fl, 'risposta con chiavi diverse da esito/messaggio/dati')

    # {{SITO_URL}}
    testo_azioni = json.dumps(d['actions'], ensure_ascii=False)
    n_sito = testo_azioni.count('{{SITO_URL}}')
    if n_sito != 1:
        es.err(fl, '{{SITO_URL}} compare %d volte nelle azioni (atteso 1)' % n_sito)
    if re.search(r'https://[a-z0-9-]+\.sharepoint\.com', testo_azioni + json.dumps(d['triggers'])):
        es.err(fl, 'URL SharePoint scritto in chiaro')
    if 'dataset' in json.dumps(d['triggers']) and '{{SITO_URL}}' not in json.dumps(d['triggers']):
        es.err(fl, 'il trigger SharePoint deve usare {{SITO_URL}}')

    # espressioni e riferimenti
    def controlla_espressioni(dove, oggetto, nome_azione=None):
        for s in stringhe(oggetto, escludi_contenitori=nome_azione is not None):
            for e in estrai_espressioni(s):
                if isinstance(e, tuple):
                    es.err(fl, '%s: interpolazione non chiusa: %s' % (dove, e[1]))
                    continue
                try:
                    chiamate, rif, chiavi = analizza(e)
                except ValueError as ex:
                    es.err(fl, '%s: espressione non valida (%s): %s' % (dove, ex, e[:160]))
                    continue
                for f in chiamate:
                    if f not in FUNZIONI:
                        es.err(fl, '%s: funzione sconosciuta %r' % (dove, f))
                for k in chiavi:
                    if powerapps and k not in chiavi_trigger and k not in ('value',):
                        es.err(fl, '%s: parametro del trigger inesistente %r' % (dove, k))
                if nome_azione is None:
                    continue
                for f, x in rif:
                    if f == 'variables':
                        if x not in variabili:
                            es.err(fl, '%s: variabile %r non inizializzata' % (dove, x))
                        else:
                            radice_rep = antenati(info, nome_azione)[-1][1]
                            if variabili[x] != radice_rep and variabili[x] not in predecessori(contenitori[('', 'root')], radice_rep):
                                es.err(fl, '%s: variabile %r usata prima di essere inizializzata' % (dove, x))
                        continue
                    if f == 'items':
                        if x not in [o for o, _ in info[nome_azione]['catena']] or info[x]['tipo'] != 'Foreach':
                            es.err(fl, "%s: items('%s') fuori dal ciclo" % (dove, x))
                        continue
                    if x not in info:
                        es.err(fl, "%s: %s('%s') verso azione inesistente" % (dove, f, x))
                        continue
                    if f == 'result' and info[x]['tipo'] not in ('Scope', 'Foreach', 'Until'):
                        es.err(fl, "%s: result('%s') richiede un ambito o un ciclo" % (dove, x))
                    cx = info[x]['cont']
                    trovato = False
                    for cont, rep in antenati(info, nome_azione):
                        if cont == cx:
                            trovato = True
                            if x != rep and x not in predecessori(contenitori[cont], rep):
                                es.err(fl, "%s: %s('%s') non è eseguita prima" % (dove, f, x))
                            elif x == rep and f != 'result':
                                es.err(fl, "%s: %s('%s') riferito a un'azione contenitore antenata" % (dove, f, x))
                            break
                    if not trovato:
                        es.err(fl, "%s: %s('%s') sta in un ramo o ambito non raggiungibile" % (dove, f, x))

    controlla_espressioni('trigger', d['triggers'])
    for nome, i in info.items():
        controlla_espressioni(nome, i['azione'], nome)
    return len(info)


def main():
    schema = carica_schema()
    es = Esito()
    file = sorted(f for f in os.listdir(CARTELLA) if f.endswith('.json'))
    if not file:
        print('Nessun flusso in', CARTELLA)
        return 1
    totale = 0
    for f in file:
        n = verifica_file(os.path.join(CARTELLA, f), schema, es) or 0
        totale += n
        print('%-40s %4d azioni' % (f, n))
    print()
    if schema is None:
        print('Nota: PyYAML non disponibile, controllo delle colonne SharePoint saltato.')
    for a in es.avvisi:
        print('AVVISO  ', a)
    for e in es.errori:
        print('ERRORE  ', e)
    print('\n%d file, %d azioni, %d errori, %d avvisi' % (len(file), totale, len(es.errori), len(es.avvisi)))
    return 1 if es.errori else 0


if __name__ == '__main__':
    sys.exit(main())
