// #############################################################################
//  GESTIONE ORE FORMAZIONE – Società Dolce
//  Chiusura del mese, file paghe, riapertura (solo Amministratore)
//
//  Flussi: SDF_API08_ChiusuraMensile(anno, mese, azione, nota) con azione "chiudi" | "riapri"
//  (nota obbligatoria per riapri) · SDF_API09_FilePaghe(anno, mese) → dati.url del CSV.
//
//  Le formule sono identiche a quelle dei file powerapps/src/*.pa.yaml (generati
//  dalla stessa fonte). Notazione inglese: in Studio con lingua italiana i separatori
//  diventano «;» (argomenti) e «;;» (concatenazione di azioni).
// #############################################################################

// =============================================================================
//  1. Verifica del mese: stato del periodo, richieste aperte, anomalie, segnalazioni, CF mancanti
//  Dove: scrChiusura › chi_btnVerifica.OnSelect
//  Filtri delegabili su anno e mese (colonne indicizzate); la colonna «Anomalie rilevate» è multilinea
//  e si controlla in locale sulle richieste approvate/validate del mese.
// =============================================================================
Set(varCaricamento, true);
Set(varMessaggioCaricamento, "Verifica del mese in corso…");
UpdateContext({locPeriodo: Text(chi_ddAnno.Selected.Num) & "-" & Text(chi_ddMese.Selected.Num, "00"), locUrlFile: ""});
Refresh('Chiusure mensili');
UpdateContext({locChiusura: LookUp('Chiusure mensili', Periodo = locPeriodo)});
// richieste ancora aperte nel mese (stati precedenti alla validazione HR) – filtro delegabile
ClearCollect(
    colChiAperte,
    ShowColumns(
        Filter(
            'Richieste formazione',
            'Anno di competenza' = chi_ddAnno.Selected.Num,
            'Mese di competenza' = chi_ddMese.Selected.Num,
            'Stato richiesta'.Value = "Bozza" ||
            'Stato richiesta'.Value = "Inviata al coordinatore" ||
            'Stato richiesta'.Value = "In attesa del coordinatore" ||
            'Stato richiesta'.Value = "Integrazione richiesta dal coordinatore" ||
            'Stato richiesta'.Value = "Approvata dal coordinatore" ||
            'Stato richiesta'.Value = "In attesa di validazione HR" ||
            'Stato richiesta'.Value = "Integrazione richiesta da HR"
        ),
        ID, 'ID richiesta', Cognome, Nome, Coordinatore, 'Stato richiesta', 'Data sessione formativa'
    )
);
// richieste approvate o validate del mese: base per anomalie e controllo del codice fiscale
ClearCollect(
    colChiDaVerificare,
    ShowColumns(
        Filter(
            'Richieste formazione',
            'Anno di competenza' = chi_ddAnno.Selected.Num,
            'Mese di competenza' = chi_ddMese.Selected.Num,
            'Stato richiesta'.Value = "Approvata dal coordinatore" ||
            'Stato richiesta'.Value = "In attesa di validazione HR" ||
            'Stato richiesta'.Value = "Validata da HR" ||
            'Stato richiesta'.Value = "Inclusa nel riepilogo mensile" ||
            'Stato richiesta'.Value = "Inviata a Payroll"
        ),
        ID, 'ID richiesta', Cognome, Nome, 'Login lavoratore', Coordinatore, 'Stato richiesta', 'Possibile duplicato',
        'Attestato presente', 'Anomalie rilevate', 'Titolo del corso a catalogo', 'Titolo corso libero', 'Data sessione formativa'
    )
);
// anomalie: possibili duplicati, attestato mancante, anomalie segnalate dai flussi (colonna multilinea: filtro locale)
ClearCollect(
    colChiAnomalie,
    Filter(colChiDaVerificare, 'Possibile duplicato' || !'Attestato presente' || !IsBlank('Anomalie rilevate'))
);
// lavoratori con una segnalazione di variazione da gestire
ClearCollect(colChiSegnalazioni, Filter(Lavoratori, 'Segnalazione da gestire' = true));
// lavoratori delle richieste validate del mese senza codice fiscale
ClearCollect(colChiLavSenzaCF, Filter(Lavoratori, 'Codice fiscale registrato' = false));
ClearCollect(
    colChiSenzaCF,
    Filter(
        colChiLavSenzaCF,
        'Login Microsoft 365' in Filter(
            colChiDaVerificare,
            'Stato richiesta'.Value = "Validata da HR" || 'Stato richiesta'.Value = "Inclusa nel riepilogo mensile" || 'Stato richiesta'.Value = "Inviata a Payroll"
        ).'Login lavoratore'
    )
);
Set(varCaricamento, false)

// =============================================================================
//  2. Conferma: chiudi (SDF_API08), riapri (SDF_API08, solo Amministratore), genera file (SDF_API09)
//  Dove: scrChiusura › chi_btnDialogoConferma.OnSelect
// =============================================================================
Set(varCaricamento, true);
Set(varMessaggioCaricamento, "Operazione in corso…");
Switch(
    locDialogo,
    "chiudi",
        With(
            {r: IfError(
                SDF_API08_ChiusuraMensile.Run(chi_ddAnno.Selected.Num, chi_ddMese.Selected.Num, "chiudi", Trim(chi_txtDialogoNota.Text)),
                {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
            )},
            If(
                r.esito = "OK",
                Notify(Coalesce(r.messaggio, "Mese chiuso."), NotificationType.Success);
                UpdateContext({locDialogo: ""});
                Reset(chi_txtDialogoNota);
                Select(chi_btnVerifica),
                Notify(r.messaggio, NotificationType.Error)
            )
        ),
    "riapri",
        With(
            {r: IfError(
                SDF_API08_ChiusuraMensile.Run(chi_ddAnno.Selected.Num, chi_ddMese.Selected.Num, "riapri", Trim(chi_txtDialogoNota.Text)),
                {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
            )},
            If(
                r.esito = "OK",
                Notify(Coalesce(r.messaggio, "Mese riaperto."), NotificationType.Success);
                UpdateContext({locDialogo: ""});
                Reset(chi_txtDialogoNota);
                Select(chi_btnVerifica),
                Notify(r.messaggio, NotificationType.Error)
            )
        ),
    "paghe",
        With(
            {r: IfError(
                SDF_API09_FilePaghe.Run(chi_ddAnno.Selected.Num, chi_ddMese.Selected.Num),
                {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
            )},
            If(
                r.esito = "OK",
                With(
                    {d: IfError(ParseJSON(r.dati), ParseJSON("{}"))},
                    UpdateContext({locUrlFile: Text(d.url), locDialogo: ""});
                    Notify(
                        "File paghe generato con " & Text(d.richieste) & " richieste: usa «Apri il file paghe»." &
                        If(Coalesce(Value(d.senzaCodiceFiscale), 0) > 0, " Attenzione: " & Text(d.senzaCodiceFiscale) & " righe senza codice fiscale.", ""),
                        If(Coalesce(Value(d.senzaCodiceFiscale), 0) > 0, NotificationType.Warning, NotificationType.Success)
                    )
                );
                Select(chi_btnVerifica),
                Notify(r.messaggio, NotificationType.Error)
            )
        )
);
Set(varCaricamento, false)

// =============================================================================
//  3. HR: segnalazione del lavoratore gestita (Patch diretta sulla lista Lavoratori)
//  Dove: scrChiusura › chi_icoGestita.OnSelect
//  HR può modificare la lista Lavoratori; la riga di registro la scrive solo l'Amministratore
//  (il gruppo HR ha sola lettura sul Registro modifiche; vale il controllo versioni di SharePoint).
// =============================================================================
// IfError(azione1, errore1, azione2, errore2, finale): si ferma al primo errore
With(
    {lav: ThisItem},
    IfError(
        Patch(Lavoratori, LookUp(Lavoratori, ID = lav.ID), {'Segnalazione da gestire': false}),
        Notify("Aggiornamento non riuscito: " & FirstError.Message, NotificationType.Error),
        If(
            isAdmin,
            Patch(
                'Registro modifiche',
                Defaults('Registro modifiche'),
                {
                    Azione: "Segnalazione gestita",
                    Lista: "Lavoratori",
                    'ID elemento': Text(lav.ID),
                    Campo: "Segnalazione da gestire",
                    'Valore precedente': "Sì",
                    'Valore nuovo': "No",
                    Ruolo: {Value: "Amministratore"},
                    'Login autore': recProfilo.login,
                    Nota: ""
                }
            )
        ),
        Notify("Segnalazione aggiornata, ma il Registro modifiche non è stato scritto: " & FirstError.Message, NotificationType.Warning),
        RemoveIf(colChiSegnalazioni, ID = lav.ID);
        Notify("Segnalazione di " & lav.Nominativo & " segnata come gestita. Ricorda di aggiornare i dati del lavoratore se necessario.", NotificationType.Success)
    )
)

// =============================================================================
//  4. HR: correzione del codice fiscale mancante
//  Dove: scrChiusura › chi_icoSalvaCF.OnSelect
//  Il valore del CF non viene mai scritto nel registro.
// =============================================================================
With(
    {lav: ThisItem, cf: Upper(Trim(chi_txtRigaCF.Text))},
    If(
        !IsMatch(cf, "^[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$"),
        Notify("Il codice fiscale non è valido: controlla i 16 caratteri.", NotificationType.Error),
        IfError(
            Patch(
                Lavoratori,
                LookUp(Lavoratori, ID = lav.ID),
                {'Codice fiscale': cf, 'Codice fiscale (mascherato)': Left(cf, 3) & "**********" & Right(cf, 3), 'Codice fiscale registrato': true}
            ),
            Notify("Salvataggio non riuscito: " & FirstError.Message, NotificationType.Error),
            If(
                isAdmin,
                Patch(
                    'Registro modifiche',
                    Defaults('Registro modifiche'),
                    {
                        Azione: "Correzione codice fiscale",
                        Lista: "Lavoratori",
                        'ID elemento': Text(lav.ID),
                        Campo: "Codice fiscale",
                        'Valore precedente': "",
                        'Valore nuovo': "Codice fiscale aggiornato",
                        Ruolo: {Value: "Amministratore"},
                        'Login autore': recProfilo.login,
                        Nota: ""
                    }
                )
            ),
            Notify("Codice fiscale salvato, ma il Registro modifiche non è stato scritto: " & FirstError.Message, NotificationType.Warning),
            RemoveIf(colChiSenzaCF, ID = lav.ID);
            Notify("Codice fiscale di " & lav.Nominativo & " salvato.", NotificationType.Success)
        )
    )
)
