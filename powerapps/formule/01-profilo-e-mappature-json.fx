// #############################################################################
//  GESTIONE ORE FORMAZIONE – Società Dolce
//  Caricamento del profilo, instradamento e mappatura JSON → tabelle
//
//  Flussi: SDF_API01_Profilo (nessun parametro), SDF_API04_AggiornaProfilo(email, cf, segnalazione).
//  La risposta di ogni flusso è un record {esito, messaggio, dati}: «dati» è un JSON in testo che
//  viene salvato in una variabile (varJsonProfilo, varJsonMieRichieste, varJsonTeam, varJsonDettaglio).
//  Le formule con nome (00-App.Formulas.fx) lo convertono con ParseJSON in record e tabelle tipizzate,
//  per esempio:
//    colMieRichieste = ForAll(Table(ParseJSON(varJsonMieRichieste).richieste) As x,
//                             {id: Value(x.Value.id), idRichiesta: Text(x.Value.idRichiesta),
//                              dataSessione: DateValue(x.Value.dataSessione), ...})
//  e si ricalcolano da sole ogni volta che la variabile cambia.
//
//  Le formule sono identiche a quelle dei file powerapps/src/*.pa.yaml (generati
//  dalla stessa fonte). Notazione inglese: in Studio con lingua italiana i separatori
//  diventano «;» (argomenti) e «;;» (concatenazione di azioni).
// #############################################################################

// =============================================================================
//  1. Accesso: carica il profilo e instrada (primo accesso → profilo; link e-mail → dettaglio)
//  Dove: scrAccesso.OnVisible
//  SDF_API01_Profilo viene chiamato una sola volta per sessione, con l'indicatore di caricamento.
//  Se il lavoratore non ha e-mail personale o codice fiscale va su scrProfilo (obbligatorio).
//  Se l'app è stata aperta dal link di un'e-mail (…&richiesta=<ID>) apre scrDettaglio.
//  Se l'utente non ha alcun ruolo la schermata mostra «Utente non censito».
// =============================================================================
Set(varMenuAperto, false);
// 1) carica il profilo una sola volta per sessione (SDF_API01_Profilo)
If(
    !varProfiloCaricato,
    Set(varCaricamento, true);
    Set(varMessaggioCaricamento, "Caricamento del profilo…");
    With(
        {rp: IfError(SDF_API01_Profilo.Run(), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
        If(
            rp.esito = "OK",
            Set(varJsonProfilo, rp.dati);
            Set(varErroreProfilo, "");
            Set(varProfiloCaricato, true),
            Set(varErroreProfilo, Coalesce(rp.messaggio, testoErroreRete))
        )
    );
    Set(varCaricamento, false)
);
// 2) primo accesso del lavoratore -> profilo obbligatorio; collegamento diretto -> dettaglio
If(
    varProfiloCaricato && isLavoratore && !recProfilo.profiloCompleto,
    Navigate(scrProfilo, ScreenTransition.None),
    varProfiloCaricato && haRuolo && !IsBlank(Param("richiesta")) && !varParamGestito,
    Set(varParamGestito, true);
    Set(varDaLinkDiretto, true);
    Set(varIdDettaglio, Value(Param("richiesta")));
    Navigate(scrDettaglio, ScreenTransition.None)
)

// =============================================================================
//  2. Testo di stato della schermata di accesso
//  Dove: scrAccesso › acc_lblStato.Text
//  Messaggi chiari per errore, utente non censito, primo accesso, ruolo.
// =============================================================================
If(
    varCaricamento, "Caricamento del profilo in corso…",
    !IsBlank(varErroreProfilo), "Non è stato possibile caricare il profilo: " & varErroreProfilo,
    !varProfiloCaricato, "",
    !haRuolo, "Utente non censito: contatta l’Ufficio HR/Formazione.",
    isLavoratore && !recProfilo.profiloCompleto, "Primo accesso: completa il profilo con e-mail personale e codice fiscale.",
    "Ruolo nell’applicativo: " & ruoloApp & If(testoRuoli <> ruoloApp, " (abilitato come: " & testoRuoli & ")", "")
)

// =============================================================================
//  3. Profilo: salvataggio di e-mail personale e codice fiscale (SDF_API04_AggiornaProfilo)
//  Dove: scrProfilo › pro_btnSalva.OnSelect
//  Controlli lato app: e-mail con IsMatch(..., Match.Email); CF con l'espressione regolare ufficiale.
//  Il CF si invia solo se è stato inserito o modificato (altrimenti ""). Dopo il salvataggio
//  si ricarica il profilo (SDF_API01) per avere il CF mascherato e lo stato «profilo completo».
// =============================================================================
If(
    !IsMatch(Trim(pro_txtEmail.Text), Match.Email),
    Notify("Inserisci un indirizzo e-mail personale valido (es. nome.cognome@gmail.com).", NotificationType.Error),
    !(!locModificaCF || IsMatch(Upper(Trim(pro_txtCF.Text)), "^[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$")),
    Notify("Il codice fiscale non è valido: controlla i 16 caratteri.", NotificationType.Error),
    Set(varCaricamento, true);
    Set(varMessaggioCaricamento, "Salvataggio del profilo…");
    With(
        {r: IfError(
            SDF_API04_AggiornaProfilo.Run(Trim(pro_txtEmail.Text), If(locModificaCF, Upper(Trim(pro_txtCF.Text)), ""), ""),
            {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
        )},
        If(
            r.esito = "OK",
            // ricarica il profilo (SDF_API01_Profilo) per avere dati aggiornati e CF mascherato
            With(
                {rp: IfError(SDF_API01_Profilo.Run(), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
                If(
                    rp.esito = "OK",
                    Set(varJsonProfilo, rp.dati);
                    Set(varErroreProfilo, "");
                    Set(varProfiloCaricato, true),
                    Set(varErroreProfilo, Coalesce(rp.messaggio, testoErroreRete))
                )
            );
            Notify("Profilo salvato. Le notifiche arriveranno a " & recProfilo.emailPersonale & ".", NotificationType.Success);
            UpdateContext({locModificaCF: !recProfilo.cfRegistrato});
            Reset(pro_txtCF);
            If(
                locEraIncompleto && recProfilo.profiloCompleto,
                UpdateContext({locEraIncompleto: false});
                If(
                    !IsBlank(Param("richiesta")) && !varParamGestito,
                    Set(varParamGestito, true);
                    Set(varDaLinkDiretto, true);
                    Set(varIdDettaglio, Value(Param("richiesta")));
                    Navigate(scrDettaglio, ScreenTransition.None),
                    Navigate(scrHome, ScreenTransition.None)
                )
            ),
            Notify(r.messaggio, NotificationType.Error)
        )
    );
    Set(varCaricamento, false)
)

// =============================================================================
//  4. Profilo: segnalazione di variazione a HR
//  Dove: scrProfilo › pro_btnSegnala.OnSelect
//  Il terzo parametro di SDF_API04 è il testo della segnalazione; e-mail e CF restano invariati.
// =============================================================================
If(
    IsBlank(Trim(pro_txtSegnalazione.Text)),
    Notify("Descrivi la variazione da segnalare (es. nuovo servizio, nuovo coordinatore, centro di costo errato).", NotificationType.Error),
    Set(varCaricamento, true);
    Set(varMessaggioCaricamento, "Invio della segnalazione…");
    With(
        {r: IfError(
            SDF_API04_AggiornaProfilo.Run(recProfilo.emailPersonale, "", Trim(pro_txtSegnalazione.Text)),
            {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
        )},
        If(
            r.esito = "OK",
            With(
                {rp: IfError(SDF_API01_Profilo.Run(), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
                If(
                    rp.esito = "OK",
                    Set(varJsonProfilo, rp.dati);
                    Set(varErroreProfilo, "");
                    Set(varProfiloCaricato, true),
                    Set(varErroreProfilo, Coalesce(rp.messaggio, testoErroreRete))
                )
            );
            Reset(pro_txtSegnalazione);
            Notify("Segnalazione inviata all’Ufficio HR/Formazione: riceverai una risposta all’e-mail personale.", NotificationType.Success),
            Notify(r.messaggio, NotificationType.Error)
        )
    );
    Set(varCaricamento, false)
)

// =============================================================================
//  5. Home: caricamento dei dati secondo il ruolo
//  Dove: scrHome.OnVisible
//  Lavoratore: SDF_API02 · Coordinatore: SDF_API05 · HR: conteggi con lettura diretta e filtri
//  delegabili (CountRows su SharePoint non è delegabile: si raccolgono solo gli ID, massimo 2000,
//  e si mostra «2000+» oltre il limite). Le liste HR vengono lette solo se isHR.
// =============================================================================
Set(varMenuAperto, false);
If(
    !varProfiloCaricato,
    Navigate(scrAccesso, ScreenTransition.None),
    isLavoratore && !recProfilo.profiloCompleto,
    Navigate(scrProfilo, ScreenTransition.None),
    Set(varCaricamento, true);
    Set(varMessaggioCaricamento, "Caricamento della pagina iniziale…");
    // Lavoratore: le proprie richieste tramite SDF_API02 (una volta per sessione, poi pulsante Aggiorna)
    If(
        isLavoratore && !varMieCaricate,
        With(
            {rm: IfError(SDF_API02_MieRichieste.Run(0), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
            If(
                rm.esito = "OK",
                Set(varJsonMieRichieste, rm.dati);
                Set(varMieCaricate, true),
                Notify("Non è stato possibile caricare le tue richieste. " & rm.messaggio, NotificationType.Error)
            )
        )
    );
// Coordinatore: richieste del team dell'anno in corso tramite SDF_API05
If(
    isCoord && !varTeamCaricato,
    Set(varAnnoTeam, Year(Today()));
    Set(varMeseTeam, 0);
        With(
            {rt: IfError(SDF_API05_RichiesteTeam.Run(varAnnoTeam, varMeseTeam), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
            If(
                rt.esito = "OK",
                Set(varJsonTeam, rt.dati);
                Set(varTeamCaricato, true),
                Notify("Non è stato possibile caricare le richieste del team. " & rt.messaggio, NotificationType.Error)
            )
        )
    );
// HR / Amministratore: conteggi con lettura diretta e filtri delegabili (massimo 2000 righe per conteggio)
If(
    isHR,
        ClearCollect(colHomeHrValidare, ShowColumns(Filter('Richieste formazione', 'Stato richiesta'.Value = "In attesa di validazione HR"), ID));
        ClearCollect(colHomeHrCoord, ShowColumns(Filter('Richieste formazione', 'Stato richiesta'.Value = "In attesa del coordinatore"), ID));
        ClearCollect(
            colHomeHrIntegr,
            ShowColumns(
                Filter(
                    'Richieste formazione',
                    'Stato richiesta'.Value = "Integrazione richiesta dal coordinatore" || 'Stato richiesta'.Value = "Integrazione richiesta da HR"
                ),
                ID
            )
        );
        ClearCollect(
            colHomeHrSolleciti,
            ShowColumns(Filter('Richieste formazione', 'Stato richiesta'.Value = "In attesa del coordinatore", 'Sollecito segnalato a HR' = true), ID)
        )
    );
    Set(varCaricamento, false)
)
