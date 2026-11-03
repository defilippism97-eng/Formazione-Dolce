// #############################################################################
//  GESTIONE ORE FORMAZIONE – Società Dolce
//  00-App.OnStart.it.fx – STESSO contenuto di 00-App.OnStart.fx in notazione italiana
//
//  Usare questo file se Power Apps Studio è in italiano (la barra della formula separa gli
//  argomenti con «;» e concatena le azioni con «;;»). Se Studio è in inglese usare il file .fx.
//
//  Le formule sono identiche a quelle dei file powerapps/src/*.pa.yaml (generati
//  dalla stessa fonte). Notazione inglese: in Studio con lingua italiana i separatori
//  diventano «;» (argomenti) e «;;» (concatenazione di azioni).
// #############################################################################

// OnStart: solo valori iniziali. Nessuna chiamata a flussi o liste qui: il profilo si carica
// in scrAccesso (OnVisible) con l'indicatore di caricamento. Ogni valore viene impostato solo
// se è ancora vuoto, così l'ordine di esecuzione con l'«OnStart non bloccante» non conta.
If(IsBlank(varCaricamento); Set(varCaricamento; false));;
If(IsBlank(varMessaggioCaricamento); Set(varMessaggioCaricamento; ""));;
If(IsBlank(varMenuAperto); Set(varMenuAperto; false));;
If(IsBlank(varProfiloCaricato); Set(varProfiloCaricato; false));;
If(IsBlank(varErroreProfilo); Set(varErroreProfilo; ""));;
If(IsBlank(varJsonProfilo); Set(varJsonProfilo; "{}"));;
If(IsBlank(varParamGestito); Set(varParamGestito; false));;
If(IsBlank(varDaLinkDiretto); Set(varDaLinkDiretto; false));;
If(IsBlank(varJsonMieRichieste); Set(varJsonMieRichieste; jsonVuotoMie));;
If(IsBlank(varMieCaricate); Set(varMieCaricate; false));;
If(IsBlank(varJsonTeam); Set(varJsonTeam; jsonVuotoTeam));;
If(IsBlank(varTeamCaricato); Set(varTeamCaricato; false));;
If(IsBlank(varAnnoTeam); Set(varAnnoTeam; Year(Today())));;
If(IsBlank(varMeseTeam); Set(varMeseTeam; 0));;
If(IsBlank(varJsonDettaglio); Set(varJsonDettaglio; jsonVuotoDettaglio));;
If(IsBlank(varIdDettaglio); Set(varIdDettaglio; 0));;
If(IsBlank(varIdModifica); Set(varIdModifica; 0));;
If(IsBlank(varFiltroGruppoMie); Set(varFiltroGruppoMie; "tutti"));;
If(IsBlank(varPerimetroRiep); Set(varPerimetroRiep; ""))
