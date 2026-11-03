# 4. Guida all'installazione

**Costo:** nessuna licenza aggiuntiva. Si usano SharePoint, Power Apps e Power Automate già inclusi in Microsoft 365, solo con connettori standard.
**Tempo stimato:** 1 giorno per un ambiente di prova, con il supporto dell'IT per i passaggi da amministratore.

| Chi | Cosa |
|---|---|
| IT / amministratore Microsoft 365 | account di servizio, registrazione app PnP, creazione del sito |
| Amministratore applicativo | script di installazione, importazione dei flussi, creazione dell'app |
| HR | dati iniziali (organigramma, catalogo, lavoratori), collaudo |

## 4.0 Prerequisiti

1. **Licenze.** Gli utenti devono avere una licenza Microsoft 365 che includa SharePoint e Power Apps / Power Automate *per Microsoft 365*: la includono quasi tutte, comprese le licenze frontline F1/F3, Business ed E1/E3/E5. Per verificarla: *Interfaccia di amministrazione di Microsoft 365 → Utenti → (utente) → Licenze e app*. L'account di servizio ha bisogno di una licenza con **cassetta postale** (per inviare le e-mail).
2. **Account di servizio** `svc-formazione@societadolce.it`, vedi [03-sicurezza.md §3.5](03-sicurezza.md#35-account-di-servizio).
3. **Facoltativo:** una cassetta condivisa `formazione@societadolce.it` come mittente delle e-mail, con permesso *Invia come* per l'account di servizio.
4. Sul PC di chi installa:
   - [PowerShell 7](https://aka.ms/powershell) e il modulo PnP:
     ```powershell
     Install-Module PnP.PowerShell -Scope CurrentUser
     ```
   - una **registrazione app Entra ID per PnP** (una sola volta, la crea un amministratore):
     ```powershell
     Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP Societa Dolce" -Tenant societadolce.onmicrosoft.com -Interactive
     ```
     Annotare il **Client ID** restituito.
   - Python 3.10+ (solo se l'indirizzo del sito è diverso da `/sites/GestioneFormazione`, vedi 4.3).

## 4.1 Preparare i dati (consigliato prima dell'installazione)

Preparare tre file CSV con separatore `;`, codifica UTF-8 e la prima riga uguale ai modelli in `sharepoint/seed/`:

| File | Modello | Contenuto |
|---|---|---|
| strutture.csv | `sharepoint/seed/strutture.csv` | Area · Servizio · Centro di costo · Login coordinatore servizio |
| corsi.csv | `sharepoint/seed/corsi.csv` | Corsi *Datore di lavoro* del catalogo: codice, titolo, modalità, durata, gettone previsto, ecc. |
| lavoratori.csv | `sharepoint/seed/lavoratori_modello.csv` | Login Microsoft 365 · Cognome · Nome · E-mail aziendale (se esiste) · Centro di costo · Login coordinatore · Stato · Date di validità |

L'area deve essere esattamente una di: *Area Nord Ovest, Area Centro, Area Educativa, Area Socio Sanitaria, Area Staff*. Se il *Login coordinatore* di un lavoratore è vuoto, viene preso quello della sua struttura.

## 4.2 Creare il sito e le liste

Da PowerShell 7, nella cartella `sharepoint` del progetto:

```powershell
./Installa-GestioneFormazione.ps1 `
    -SitoUrl https://societadolce.sharepoint.com/sites/GestioneFormazione `
    -ClientId <Client ID PnP> `
    -CreaSito -Proprietario <amministratore>@societadolce.it `
    -AccountServizio svc-formazione@societadolce.it `
    -Amministratori <amministratore app>@societadolce.it `
    -UtentiHR <hr1>@societadolce.it,<hr2>@societadolce.it `
    -UtentiPaghe <paghe>@societadolce.it `
    -EmailHR formazione@societadolce.it `
    -DestinatariPayroll "paghe@societadolce.it;formazione@societadolce.it" `
    -ImportaStrutture ./strutture.csv -ImportaCorsi ./corsi.csv -ImportaLavoratori ./lavoratori.csv
```

- `-CreaSito` richiede un amministratore SharePoint. In alternativa il sito si crea a mano: *Interfaccia di amministrazione di SharePoint → Siti attivi → Crea → Altre opzioni → Sito del team senza gruppo*, lingua **Italiano**, fuso **Roma**. Poi si lancia lo script senza `-CreaSito`.
- In un ambiente di prova si può usare `-DatiEsempio` al posto dei CSV.
- Lo script si può rilanciare: salta ciò che esiste già.

Al termine il sito contiene 8 liste, 2 raccolte, i gruppi *Formazione - HR* e *Formazione - Paghe* e i permessi descritti in [02-modello-dati.md](02-modello-dati.md).

> **Importante:** importare i lavoratori **prima** di attivare il flusso F7. Altrimenti F7 partirebbe per ogni lavoratore importato.

## 4.3 Importare i flussi

1. Se il sito ha un indirizzo **diverso** da `https://societadolce.sharepoint.com/sites/GestioneFormazione`, rigenerare i pacchetti:
   ```bash
   python powerautomate/crea_pacchetti.py --sito https://<tenant>.sharepoint.com/sites/<nome>
   ```
   Altrimenti usare quelli già pronti in `powerautomate/pacchetti/`.
2. Accedere a [make.powerautomate.com](https://make.powerautomate.com) **con l'account di servizio**, nell'ambiente predefinito.
3. **I miei flussi → Importa → Importa pacchetto (legacy)** → `GestioneFormazione_tutti_i_flussi.zip`, oppure un pacchetto alla volta.
4. Per ogni riga:
   - *Impostazione importazione* del flusso = **Crea come nuovo**;
   - per SharePoint e Office 365 Outlook = **Seleziona durante l'importazione** → connessione dell'account di servizio (crearla se manca).
5. **Importa**. I flussi vengono creati **spenti**.

Se l'importazione di un flusso non riesce, lo si può ricreare a mano seguendo la descrizione passo passo in [powerautomate/README.md](../powerautomate/README.md).

## 4.4 Creare l'app

Seguire [powerapps/README.md](../powerapps/README.md): creare un'app Canvas vuota, collegare le liste SharePoint, aggiungere i 10 flussi `SDF_API…`, incollare formule e schermate, aggiungere i controlli allegati, salvare e **pubblicare**.

Poi:
1. **Dettagli** dell'app → copiare il **Collegamento web**.
2. Lista **Configurazione** del sito → chiave `AppUrl` → incollare il collegamento. Serve ai link diretti nelle e-mail.
3. **Condividi** l'app con *Tutti tranne gli utenti esterni*, oppure con un gruppo che comprenda tutti i lavoratori. La condivisione dà solo la possibilità di aprire l'app: i dati restano protetti dai flussi.
4. I flussi API, quando vengono chiamati dall'app, usano le connessioni dell'account di servizio. In *Dettagli del flusso → Utenti solo esecuzione*, lasciare per SharePoint e Outlook **"Usa questa connessione"**.

## 4.5 Attivare i flussi

Ordine consigliato:

1. `SDF_F9_SincronizzaRuoli` e `SDF_F9b_RuoloEliminato`
2. `SDF_F7_AllineaLavoratore`, dopo l'importazione dei lavoratori
3. i 10 flussi `SDF_API…`
4. `SDF_F4_Promemoria` e `SDF_F5_RiepilogoMensile`

## 4.6 Pubblicare l'app per i lavoratori

- **Intranet:** su una pagina SharePoint della intranet aggiungere la **web part Power Apps** e incollare il collegamento web o l'ID dell'app. I lavoratori la trovano dove sono già abituati ad andare.
- **Smartphone:** app *Power Apps* (iOS/Android) con l'account Microsoft 365, oppure il collegamento web nel browser.
- **Teams** (facoltativo): *App → Power Apps → aggiungi*.

## 4.7 Collaudo e avvio

1. Collaudare con almeno un utente per ruolo seguendo [05-collaudo.md](05-collaudo.md).
2. Comunicazione ai lavoratori:
   - link all'app;
   - al primo accesso va inserita l'**e-mail personale**, dove arriveranno le notifiche;
   - breve guida;
   - informativa privacy.
3. Comunicazione ai coordinatori: notifiche sull'e-mail aziendale; promemoria dopo 3, 5 e 7 giorni lavorativi.

## 4.8 Manutenzione

| Attività | Chi | Dove |
|---|---|---|
| Nuovi lavoratori, cambi di servizio o di coordinatore | Amministratore / HR | App → Amministrazione → Lavoratori, oppure lista *Lavoratori* |
| Nuovi utenti HR o amministratori | Amministratore | App → Amministrazione → Ruoli (F9 aggiorna i gruppi) |
| Nuovi corsi; validazione dei corsi esterni inseriti dai lavoratori | Amministratore | App → Amministrazione → Catalogo corsi |
| Festività dell'anno successivo (con il **patrono locale**) | Amministratore | Lista *Configurazione* → `Festivita` |
| Riapertura di un mese chiuso | Amministratore | App → Chiusura mensile → Riapri |
| Modifica del modello dati | Sviluppatore | `sharepoint/schema.yaml` → `python sharepoint/genera_template.py` → rilanciare lo script (aggiunge le colonne mancanti) |
| Controllo errori dei flussi | Amministratore | make.powerautomate.com con l'account di servizio → cronologia delle esecuzioni; le e-mail di errore arrivano a `EmailHR` |
