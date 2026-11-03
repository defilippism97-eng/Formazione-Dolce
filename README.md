# Gestione ore formazione – Società Dolce

Soluzione **Microsoft Power Platform** che sostituisce il foglio cartaceo delle ore di formazione con un processo digitale:

**Lavoratore → Coordinatore → Ufficio HR/Formazione → Ufficio Paghe**

| | |
|---|---|
| App | Power Apps **Canvas** responsive (PC, tablet, smartphone, anche dentro Microsoft Teams) |
| Dati | **Dataverse**: 6 tabelle, 9 scelte globali, sicurezza per riga e per colonna, audit |
| Automazioni | **Power Automate**: 8 flussi (notifiche, approvazioni, promemoria, riepiloghi, file paghe) |
| Ruoli | Lavoratore · Coordinatore · Formazione HR · Amministratore |

## Struttura del repository

```
docs/
  00-requisiti.md          requisiti originali (documento di analisi)
  01-architettura.md       architettura, stati, regole, schermate, flussi  ← partire da qui
  02-modello-dati.md       tabelle, colonne, scelte, ruoli (generato da schema.yaml)
  03-sicurezza.md          ruoli, team, sicurezza riga/colonna, GDPR
  04-installazione.md      guida passo-passo all'installazione
  05-collaudo.md           piano di test (UAT) per ruolo
dataverse/
  schema.yaml              modello dati: fonte unica di verità
  provision.py             crea in automatico soluzione, tabelle, sicurezza, flussi
  genera_documentazione.py rigenera docs/02-modello-dati.md
  config.example.json      configurazione (copiare in config.json)
  seed/                    dati d'esempio e modello CSV dei lavoratori
powerapps/
  README.md                come creare l'app Canvas dal sorgente
  src/*.pa.yaml            formule dell'app e schermate (formato YAML di Power Apps)
  formule/                 formule principali commentate
powerautomate/
  README.md                descrizione dei flussi e verifiche post-importazione
  flows/*.json             definizioni dei flussi F1–F8
```

## Avvio rapido

1. Leggere [docs/01-architettura.md](docs/01-architettura.md) e confermare i **punti aperti** (§1.9) con HR e Paghe.
2. Verificare le **licenze** ([docs/04-installazione.md §4.0](docs/04-installazione.md#40-prerequisiti)).
3. Creare l'ambiente, i gruppi Entra ID e l'account di servizio ([§4.1–4.2](docs/04-installazione.md)).
4. Creare tabelle, ruoli, profili colonne e flussi:
   ```bash
   pip install -r dataverse/requirements.txt
   cp dataverse/config.example.json dataverse/config.json   # compilare
   az login
   python dataverse/provision.py --dry-run
   python dataverse/provision.py
   ```
5. Collegare le connessioni, creare l'app Canvas ([powerapps/README.md](powerapps/README.md)), impostare `sdf_AppUrl`, attivare i flussi.
6. Caricare organigramma, catalogo e lavoratori; collaudare con [docs/05-collaudo.md](docs/05-collaudo.md).

## Cosa è automatizzato e cosa no

| Componente | Modalità |
|---|---|
| Publisher, soluzione, scelte, tabelle, colonne, relazioni, chiavi | **Automatico** (`provision.py`) |
| Variabili d'ambiente, riferimenti di connessione | **Automatico**; i valori e le connessioni si collegano dal portale |
| Ruoli di sicurezza, profili di sicurezza delle colonne, team Entra | **Automatico** (i team se si indicano gli ID dei gruppi) |
| Flussi Power Automate F1–F8 | **Automatico** (creati spenti); verifica e attivazione dal portale |
| App Canvas | **Semi-automatico**: si crea l'app vuota e si incollano formule e schermate dal sorgente YAML; il modulo allegati si aggiunge con due clic |
| Dati iniziali (organigramma, catalogo, lavoratori) | Importazione Excel/CSV o flusso di dati dall'anagrafica |

## Note importanti

- **Login.** L'accesso avviene con il Single Sign-On Microsoft 365. Un'app Power Apps non può chiedere nome utente e password al proprio interno, e non sarebbe sicuro. La schermata iniziale mostra l'utente collegato e il link *"Hai dimenticato la password?"* verso https://password.societadolce.it/.
- **Licenze.** Le app che usano Dataverse sono *premium*: valutare il pagamento a consumo per i lavoratori.
- **Identità visiva.** I colori sono centralizzati nelle formule dell'app (`colPrimario` e simili): sostituirli con quelli del manuale d'identità di Società Dolce.

## Modificare il modello dati

1. Modificare `dataverse/schema.yaml`.
2. `python dataverse/provision.py --steps columns,relationships,keys,publish` (aggiunge solo ciò che manca).
3. `python dataverse/genera_documentazione.py` per aggiornare la documentazione.
4. Aggiornare app e flussi se usano le nuove colonne.
