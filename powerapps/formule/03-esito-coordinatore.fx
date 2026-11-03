// #############################################################################
//  GESTIONE ORE FORMAZIONE – Società Dolce
//  Coordinatore: richieste del team, dettaglio ed esito
//
//  Flussi: SDF_API05_RichiesteTeam(anno, mese) · SDF_API10_DettaglioRichiesta(id) ·
//  SDF_API06_EsitoCoordinatore(id, azione, oreRetribuite, oreGettone, nota)
//  azione = "approva" | "respingi" | "integrazione". I pannelli del dettaglio compaiono solo se
//  SDF_API10 restituisce permessi.esitoCoordinatore = true (mai sulle proprie richieste).
//
//  Le formule sono identiche a quelle dei file powerapps/src/*.pa.yaml (generati
//  dalla stessa fonte). Notazione inglese: in Studio con lingua italiana i separatori
//  diventano «;» (argomenti) e «;;» (concatenazione di azioni).
// #############################################################################

// =============================================================================
//  1. Richieste del team: caricamento all'apertura
//  Dove: scrTeam.OnVisible
// =============================================================================
Set(varMenuAperto, false);
If(
    !varTeamCaricato,
    Set(varCaricamento, true);
    Set(varMessaggioCaricamento, "Caricamento delle richieste del team…");
    With(
        {rt: IfError(SDF_API05_RichiesteTeam.Run(varAnnoTeam, varMeseTeam), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
        If(
            rt.esito = "OK",
            Set(varJsonTeam, rt.dati);
            Set(varTeamCaricato, true),
            Notify("Non è stato possibile caricare le richieste del team. " & rt.messaggio, NotificationType.Error)
        )
    );
    Set(varCaricamento, false)
)

// =============================================================================
//  2. Cambio di anno o mese: nuovo caricamento da SDF_API05
//  Dove: scrTeam › tea_ddAnno.OnChange
// =============================================================================
Set(varAnnoTeam, tea_ddAnno.Selected.Num);
Set(varMeseTeam, tea_ddMese.Selected.Num);
Set(varCaricamento, true);
Set(varMessaggioCaricamento, "Caricamento delle richieste del team…");
With(
    {rt: IfError(SDF_API05_RichiesteTeam.Run(varAnnoTeam, varMeseTeam), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
    If(
        rt.esito = "OK",
        Set(varJsonTeam, rt.dati);
        Set(varTeamCaricato, true),
        Notify("Non è stato possibile caricare le richieste del team. " & rt.messaggio, NotificationType.Error)
    )
);
Set(varCaricamento, false)

// =============================================================================
//  3. Filtri locali (lavoratore, servizio, centro di costo, stato)
//  Dove: scrTeam › tea_galRichieste.Items
// =============================================================================
Sort(
    Filter(
        colRichiesteTeam,
        IsBlank(tea_ddLavoratore.Selected.Value) || nominativo = tea_ddLavoratore.Selected.Value,
        IsBlank(tea_ddServizio.Selected.Value) || servizio = tea_ddServizio.Selected.Value,
        IsBlank(tea_ddCdc.Selected.Value) || centroDiCosto = tea_ddCdc.Selected.Value,
        IsBlank(tea_ddStato.Selected.Value) || stato = tea_ddStato.Selected.Value
    ),
    dataSessione,
    SortOrder.Descending
)

// =============================================================================
//  4. Dettaglio: caricamento con SDF_API10 (dati, permessi, storico)
//  Dove: scrDettaglio.OnVisible
// =============================================================================
Set(varMenuAperto, false);
UpdateContext({locDialogo: "", locAzione: "", locErrore: ""});
Set(varCaricamento, true);
Set(varMessaggioCaricamento, "Caricamento della richiesta…");
Set(varJsonDettaglio, jsonVuotoDettaglio);
With(
    {r: IfError(SDF_API10_DettaglioRichiesta.Run(varIdDettaglio), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
    If(
        r.esito = "OK",
        Set(varJsonDettaglio, r.dati),
        UpdateContext({locErrore: r.messaggio});
        Notify(r.messaggio, NotificationType.Error)
    )
);
Reset(det_txtOreRetCoord);
Reset(det_txtOreGetCoord);
Reset(det_txtNotaCoord);
Reset(det_txtOreRetHR);
Reset(det_txtOreGetHR);
Reset(det_txtNotaHR);
Set(varCaricamento, false)

// =============================================================================
//  5. R4: ore riconosciute ≤ ore frequentate, mai negative
//  Dove: scrDettaglio › det_lblErrCoord.Text
// =============================================================================
With(
    {rt: Coalesce(Value(det_txtOreRetCoord.Text), 0), gt: Coalesce(Value(det_txtOreGetCoord.Text), 0)},
    If(
        rt < 0 || gt < 0, "R4 · Le ore riconosciute non possono essere negative.",
        rt + gt > recDettaglio.oreFrequentate, "R4 · Ore retribuite + gettone riconosciute (" & Text(rt + gt, "[$-en-US]0.##") & ") superano le ore frequentate (" & Text(recDettaglio.oreFrequentate, "[$-en-US]0.##") & ").",
        ""
    )
)

// =============================================================================
//  6. Conferma dell'esito (coordinatore SDF_API06, HR SDF_API07, lavoratore SDF_API03 «annulla»)
//  Dove: scrDettaglio › det_btnDialogoConferma.OnSelect
//  Respingi e Richiedi integrazione sono disabilitati finché la nota è vuota.
// =============================================================================
Switch(
    locDialogo,
    "coord",
        Set(varCaricamento, true);
        Set(varMessaggioCaricamento, "Registrazione dell’esito…");
        With(
            {r: IfError(
                SDF_API06_EsitoCoordinatore.Run(
                    varIdDettaglio,
                    locAzione,
                    Coalesce(Value(det_txtOreRetCoord.Text), 0),
                    Coalesce(Value(det_txtOreGetCoord.Text), 0),
                    Trim(det_txtNotaCoord.Text)
                ),
                {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
            )},
            If(
                r.esito = "OK",
                Notify(
                    Switch(
                        locAzione,
                        "approva", "Richiesta approvata: è stata inoltrata all’Ufficio HR per la validazione.",
                        "respingi", "Richiesta respinta: il lavoratore riceverà la motivazione.",
                        "Integrazione richiesta: il lavoratore riceverà la tua nota e potrà correggere la richiesta."
                    ),
                    NotificationType.Success
                );
                UpdateContext({locDialogo: ""});
                // aggiorna l'elenco del team (SDF_API05) e torna indietro
                With(
                    {rt: IfError(SDF_API05_RichiesteTeam.Run(varAnnoTeam, varMeseTeam), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
                    If(
                        rt.esito = "OK",
                        Set(varJsonTeam, rt.dati);
                        Set(varTeamCaricato, true),
                        Notify("Non è stato possibile caricare le richieste del team. " & rt.messaggio, NotificationType.Error)
                    )
                );
                Set(varCaricamento, false);
                If(varDaLinkDiretto, Set(varDaLinkDiretto, false); Navigate(scrTeam, ScreenTransition.None), Back()),
                Notify(r.messaggio, NotificationType.Error)
            )
        );
        Set(varCaricamento, false),
    "hr",
        Set(varCaricamento, true);
        Set(varMessaggioCaricamento, "Registrazione della validazione…");
        With(
            {r: IfError(
                SDF_API07_EsitoHR.Run(
                    JSON(
                        {
                            azione: locAzione,
                            nota: Trim(det_txtNotaHR.Text),
                            richieste: Table(
                                {
                                    id: varIdDettaglio,
                                    oreRetribuite: Coalesce(Value(det_txtOreRetHR.Text), 0),
                                    oreGettone: Coalesce(Value(det_txtOreGetHR.Text), 0)
                                }
                            )
                        },
                        JSONFormat.IgnoreBinaryData
                    )
                ),
                {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
            )},
            If(
                r.esito = "OK",
                With(
                    {scartate: IfError(Concat(Table(ParseJSON(r.dati).scartate) As s, Text(s.Value.motivo), " · "), "")},
                    If(
                        IsBlank(scartate),
                        Notify(
                            Switch(locAzione, "valida", "Richiesta validata.", "respingi", "Richiesta respinta.", "Integrazione richiesta.") &
                            " Lavoratore e coordinatore riceveranno una notifica.",
                            NotificationType.Success
                        );
                        UpdateContext({locDialogo: ""});
                        Refresh('Richieste formazione');
                        Set(varCaricamento, false);
                        If(varDaLinkDiretto, Set(varDaLinkDiretto, false); Navigate(scrValidazioneHR, ScreenTransition.None), Back()),
                        Notify("Operazione non eseguita: " & scartate, NotificationType.Error)
                    )
                ),
                Notify(r.messaggio, NotificationType.Error)
            )
        );
        Set(varCaricamento, false),
    "annulla",
        Set(varCaricamento, true);
        Set(varMessaggioCaricamento, "Annullamento in corso…");
        With(
            {r: IfError(
                SDF_API03_SalvaRichiesta.Run(JSON({id: varIdDettaglio}, JSONFormat.IgnoreBinaryData), "annulla", "", "", "", ""),
                {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
            )},
            If(
                r.esito = "OK",
                Notify("Richiesta annullata.", NotificationType.Success);
                With(
                    {rm: IfError(SDF_API02_MieRichieste.Run(0), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
                    If(
                        rm.esito = "OK",
                        Set(varJsonMieRichieste, rm.dati);
                        Set(varMieCaricate, true),
                        Notify("Non è stato possibile caricare le tue richieste. " & rm.messaggio, NotificationType.Error)
                    )
                );
                UpdateContext({locDialogo: ""});
                Set(varCaricamento, false);
                Navigate(scrMieRichieste, ScreenTransition.None),
                Notify(r.messaggio, NotificationType.Error)
            )
        );
        Set(varCaricamento, false)
)
