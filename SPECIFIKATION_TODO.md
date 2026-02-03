# Specifikation TODO

Punkter der skal afklares før implementering kan påbegyndes.

---

## A. Konceptuelle uklarheder

### Transaktion og Budgetpost

- [x] **A1.** Hvordan gemmes transaktion→budgetpost-relationen? (junction-tabel med beløb/procent?)

> **Beslutning A1:** Fast beløb + "resten"-model.
> - Hver tildeling gemmes som et fast beløb
> - Én tildeling kan markeres som "resten" (beregnes som total minus øvrige)
> - Hvis kun én tildeling, er den implicit "resten"
> - UI kan vise/beregne procent som hjælpemiddel, men DB gemmer beløb
> - Split kan ændres efterfølgende
> - Split kan ske manuelt eller automatisk via regler
- [x] **A2.** Er det tilladt at en transaktion kun er delvist tildelt budgetposter? (f.eks. 80% tildelt, 20% "ufordelt")

> **Beslutning A2:** Ja, delvis tildeling er tilladt.
> - En transaktion kan have en "ufordelt rest"
> - Transaktioner med ufordelt beløb vises i en afventer-liste
> - Brugeren kan arbejde sig igennem transaktioner løbende
> - Man kan aldrig fordele mere end transaktionens beløb (validering)
> - Man kan ikke fordele 0 kr (validering)

### Kategori vs. Budgetpost

- [x] **A3.** Skal transaktioner både have kategori OG budgetpost-tildeling, eller er budgetposten implicit kategorien?
- [x] **A4.** Hvis begge: Hvad er formålet med at have begge koncepter?
- [x] **A5.** Afklar kategori-konceptet fuldt ud (markeret "under udvikling" i CLAUDE.md)

> **Beslutning A3-A5:** Budgetpost ER kategorien.
> - Transaktioner tildeles budgetposter (ikke separate kategorier)
> - Kategorier er hierarkisk gruppering af budgetposter (til overblik/rapporter)
> - To modes for budgetposter:
>   - **Planlagt:** Har budgetteret beløb, vises altid (husleje, løn, mad)
>   - **Ad-hoc:** 0 kr budgetteret, vises kun når der er transaktioner (tandlæge, reparationer)
> - Brugeren kan oprette budgetposter on-demand ved kategorisering
> - Transaktioner uden budgetpost forbliver i "ukategoriseret"-listen (se C12-C13)

### Budgetpost-gentagelse

- [x] **A6.** Oprettes der automatisk "forventede transaktioner" per periode ud fra gentagelsesmønster?
- [x] **A7.** Eller er budgetposten bare en skabelon der sammenlignes med faktiske transaktioner?
- [x] **A8.** Hvordan håndteres beløbsændringer over tid? (f.eks. huslejestigning fra næste måned)

> **Beslutning A6-A8:** Budgetpost-livscyklus, matching og segmenter.
>
> **Periode-spalning:**
> - Ved periode-afslutning "spaltes" budgetposten:
>   - **Arkiveret instans:** Snapshot af perioden (forventet, faktisk, transaktioner). Uforanderlig.
>   - **Aktiv budgetpost:** Fortsætter med segmenter. Renses for overstået periode-data.
> - Arkiveret instans har reference til den aktive budgetpost (til historik-visning)
>
> **Forventede forekomster:**
> - Gentagelsesmønster genererer konkrete forventede forekomster per periode
> - F.eks. "100 kr hver mandag" → 4 forventede forekomster i januar
> - Matching sker på antal forekomster, ikke bare totalt beløb
>
> **Afvigelser:**
> - Forkert antal eller beløb markeres som afvigelse
> - Bruger kan "kvittere" afvigelse (har set problemet)
> - Kvittering fjerner IKKE afvigelsen fra grafer/rapporter - den vises stadig
> - Afvigelser kan kvitteres i både aktive og arkiverede perioder
>
> **Segmenter (fremtidige ændringer):**
> - En budgetpost har en overordnet slutdato (eller ∞)
> - Budgetposten har ét eller flere segmenter med hver deres indstillinger
> - Basis-segment gælder fra oprettelse (ingen startdato)
> - Øvrige segmenter har kun startdato - gælder til dagen før næste segment
> - Sidste segment gælder til budgetpostens slutdato
> - Segmenter kan ændre beløb, gentagelse, eller begge
> - Uændrede felter arves fra forrige segment
> - Ingen overlap-validering - sorteres bare efter startdato
>
> **Struktur:**
> - Kategorier er grupper/mapper (kan ikke modtage transaktioner)
> - Budgetposter er blade i hierarkiet (modtager transaktioner)
> - Én budgetpost = ét gentagelsesmønster (per segment)
> - Flere budgetposter kan dele kategori

### Interne overførsler

- [x] **A9.** Overførsel Normal→Opsparing: Påvirker det hovedsektionens "disponible saldo"?
- [x] **A10.** Er der forskel på "intern overførsel" (samme sektion) og "overførsel mellem sektioner"?

> **Beslutning A9-A10:** Overførsler og budgetpost-model.
>
> **Budgetpost-typer via fra/til konti:**
> - `fra=null, til=konto(er)` → **Indtægt**
> - `fra=konto(er), til=null` → **Udgift**
> - `fra=én konto, til=én konto` → **Overførsel** (ingen kategori tilladt)
>
> **Saldo-effekt ved overførsler:**
>
> | Fra → Til | Hovedsektion saldo |
> |-----------|-------------------|
> | Normal → Normal | Uændret |
> | Normal → Opsparing | Falder |
> | Normal → Lån | Falder (afdrag) |
> | Opsparing → Normal | Stiger |
>
> **Transaktioner er virkelighed:**
> - Transaktioner importeres fra bank eller oprettes manuelt
> - Budgetposten (overførsel) er forventningen
> - Faktiske transaktioner skal eksistere og matches til budgetposten
>
> **Konti med/uden bankforbindelse:**
> - Med bankforbindelse: Transaktioner importeres, skal matche
> - Uden bankforbindelse (virtuel): Transaktioner oprettes manuelt eller auto-genereres som modpart
>
> **Matching af overførsler:**
> - Ved import: Systemet matcher to transaktioner (én på hver konto) som overførsel
> - Ved virtuel konto: Modpart-transaktion kan auto-genereres

### Regel-matching

- [x] **A11.** Hvad sker der hvis flere regler matcher samme transaktion?
- [x] **A12.** Er der en prioritetsrækkefølge for regler?
- [x] **A13.** Kan en transaktion matche flere regler samtidig (og dermed få flere tildelinger)?

> **Beslutning A11-A13:** Regel-prioritet og matching.
> - Regler har en rækkefølge/prioritet (sorteret liste)
> - Første matchende regel anvendes - øvrige ignoreres
> - Én regel definerer hele fordelingen (kan indeholde split til flere budgetposter)
> - Hvis reglen ikke fordeler 100%, ender resten som ukategoriseret
> - Brugeren kan omsortere regler for at ændre prioritet

### Periode-definition

- [x] **A14.** Er en "periode" altid en kalendermåned?
- [x] **A15.** Kan brugeren definere custom perioder? (f.eks. d. 25 til d. 24 som lønperiode)
- [x] **A16.** Hvordan håndteres ugentlige budgetposter i en månedlig periode?

> **Beslutning A14-A16:** Periode = kalendermåned, kontinuerligt budget.
> - Én periode-type: Kalendermåned
> - Budgettet kører kontinuerligt (ingen "regnskabsår" der afsluttes)
> - Perioder arkiveres løbende når måneden slutter
> - Ingen custom perioder (kun kalendermåneder)
> - Ugentlige budgetposter håndteres via gentagelsesmønster (4-5 forekomster per måned)
> - UI kan vise "næste 12 måneder", "2026", "seneste 6 måneder" som filtre/views - ikke formelle enheder
> - Terminologi: "Periode" internt, "Februar 2026" eller "denne måned" i UI

### Fleksible budgetposter

- [x] **A17.** Når en budgetpost kan betales fra flere konti - hvordan matches transaktioner automatisk?
- [x] **A18.** Skal reglen specificere kontoen, eller arves det fra budgetposten?

> **Beslutning A17-A18:** Regel-matching via budgetpost-konti.
> - Konti angives på budgetposten (én eller flere `fra_konti`)
> - Regler bindes til budgetposter (ikke direkte til konti)
> - Matching-flow:
>   1. Transaktion ankommer på en konto
>   2. Find budgetposter der har den konto som én af deres `fra_konti`
>   3. Find regler der er tilknyttet de fundne budgetposter
>   4. Kør reglerne i prioritetsrækkefølge
>   5. Første matchende regel anvendes

### Budget-omfordelinger

- [x] **A19.** Er omfordelinger kun visuelle justeringer eller ændrer de faktisk "tilgængeligt" beløb?
- [x] **A20.** Kan man omfordele FRA en budgetpost der allerede er fuldt matched?

> **Beslutning A19-A20:** Omfordelinger ændrer budgettet.
> - Omfordeling ændrer det planlagte/budgetterede beløb for de påvirkede budgetposter i perioden
> - Ja, man kan omfordele fra en budgetpost der allerede er fuldt matched
> - Transaktioner forbliver matchede - kun forventningen justeres
> - Brugeren har fuldt ansvar - systemet forhindrer ikke "dumme" omfordelinger
> - Budgettet er et værktøj til overblik, ikke en tvangstrøje

---

## B. Database-specifikationer

- [x] **B1.** Primære nøgler: UUID eller auto-increment integer?

> **Beslutning B1:** UUID (helst UUIDv7).
> - UUID giver bedre sikkerhed (ingen enumeration)
> - Kan genereres på klient (fremtidig offline-support)
> - Nemmere ved delte budgetter og distribuerede setups
> - UUIDv7 foretrækkes (tidsbaseret, sortérbar, bedre indeks-performance)
> - UUIDv4 som fallback hvis PostgreSQL < 17

- [x] **B2.** Soft delete eller permanent sletning?

> **Beslutning B2:** Soft delete for hovedentiteter.
> - Soft delete (`deleted_at` timestamp) på: Budgetter, Konti, Budgetposter, Regler, Kategorier, Transaktioner
> - Permanent sletning på: Junction-tabeller (tildelinger), Sessions/tokens
> - Soft-deleted filtreres fra i normale queries
> - Periodisk cleanup kan permanent slette gamle soft-deleted records (f.eks. > 1 år)

- [x] **B3.** Audit trail: Skal ændringer logges (hvem, hvornår, hvad)?

> **Beslutning B3:** Minimal audit trail til MVP.
> - `created_at` og `updated_at` på alle entiteter
> - `created_by` og `updated_by` på vigtige entiteter (Budget, Konto, Budgetpost, Transaktion, Regel, Kategori, Omfordeling)
> - Ingen fuld ændringshistorik (hvad blev ændret fra/til) i MVP
> - Kan udvides senere hvis behov opstår

- [x] **B4.** Timestamps: Hvilke entiteter får created_at/updated_at?

> **Beslutning B4:** Alle entiteter får timestamps.
>
> | Entitet | created_at | updated_at | created_by | updated_by |
> |---------|------------|------------|------------|------------|
> | User | ✓ | ✓ | - | - |
> | Budget | ✓ | ✓ | ✓ | ✓ |
> | Konto | ✓ | ✓ | ✓ | ✓ |
> | Transaktion | ✓ | ✓ | ✓ | ✓ |
> | Budgetpost | ✓ | ✓ | ✓ | ✓ |
> | Budgetpost-segment | ✓ | ✓ | - | - |
> | Budgetpost-instans (arkiveret) | ✓ | - | - | - |
> | Kategori | ✓ | ✓ | ✓ | ✓ |
> | Regel | ✓ | ✓ | ✓ | ✓ |
> | Tildeling (junction) | ✓ | ✓ | - | - |
> | Omfordeling | ✓ | ✓ | ✓ | ✓ |
>
> - Arkiveret budgetpost-instans er uforanderlig (kun `created_at`)

- [x] **B5.** Beløb-præcision: Decimal(10,2), integer i øre, eller andet?

> **Beslutning B5:** Integer i mindste møntenhed.
> - Beløb gemmes som integer (f.eks. 1.234,56 kr = 123456)
> - Undgår floating-point afrundingsfejl
> - Hurtigere beregninger, simpel sammenligning
> - Kolonnenavn: `amount` (generisk, ikke bundet til specifik valuta)
> - Valuta på konto/budget bestemmer fortolkning (øre, cents, etc.)
> - BIGINT giver rigeligt med plads

- [x] **B6.** Håndtering af afrundingsfejl ved split-transaktioner

> **Beslutning B6:** Dækket af A1 (fast beløb + remainder).
> - Tildelinger gemmes som faste beløb (integer)
> - Én tildeling markeres som `is_remainder = true`
> - Remainder beregnes som: transaktionsbeløb - sum(øvrige tildelinger)
> - Eksempel 3-vejs split af 1.000 kr: 33333 + 33333 + 33334 (remainder) = 100000 øre
> - Validering: sum må aldrig overstige transaktionsbeløb, remainder kan ikke blive negativ

---

## C. Forretningslogik

### Matching

- [x] **C1.** Hvad definerer en "match" mellem transaktion og budgetpost?
- [x] **C2.** Er det kun via regler, eller også dato-proximitet + beløb-match?
- [x] **C3.** Tolerance for beløb-match? (f.eks. husleje 8.000 matcher 7.995?)

> **Beslutning C1-C3:** Matching via regler eller manuelt.
> - Transaktion matches til budgetpost via regel (automatisk) eller manuelt
> - Ingen implicit matching baseret på dato/beløb alene
> - Regler er fleksible og kan kombinere flere betingelsestyper:
>   - Dato inden for X dage fra budgetpostens forventede dato
>   - Beløb matcher præcist
>   - Beløb inden for ± X af budgetpostens forventede beløb
>   - Tekst indeholder/matcher mønster
>   - Konto er én af (arvet fra budgetpost eller specificeret)
> - Alle betingelser i en regel skal passe for at reglen matcher
> - Tolerance defineres per regel, ikke globalt

### Periode-livscyklus

- [x] **C4.** Hvornår låses en periode? (automatisk ved ny måned, manuel handling?)
- [x] **C5.** Kan en låst periode låses op igen?
- [x] **C6.** Hvad kan ændres i en låst periode?

> **Beslutning C4-C6:** Bekræftelsesmodel i stedet for låsning.
>
> **Periode-skift:**
> - Aktuel periode skifter automatisk ved månedens udløb
> - Håndteres af baggrundsjob eller ved første indlæsning efter skiftet
> - Ved skift: Budgetpost-forventninger for den afsluttede periode arkiveres (spaltes)
> - Teknisk lås på budget under periode-skift for at undgå race conditions
>
> **Ændringer i afsluttede perioder:**
> - Intet brugersynligt "låse/oplåse"-koncept
> - Alle ændringer til afsluttede perioder (transaktioner) samles som "afventende kladde"
> - Gælder både manuelle ændringer og import af gamle transaktioner
> - Regel-matching foreslås men anvendes først ved bekræftelse
>
> **Bekræftelses-flow:**
> - Brugeren samler ændringer (kan være mange)
> - Før godkendelse vises konsekvenser:
>   - Påvirkning af løbende budgetposter
>   - Ændrede afvigelser
>   - Effekt på nutidens saldi
> - Brugeren bekræfter samlet, ændringer træder i kraft
>
> **Teknisk lås:**
> - Budget låses internt under periode-skift og større rettelser
> - Forhindrer race conditions
> - Ikke synlig for brugeren som "låst" tilstand

### Import

- [x] **C7.** Hvilke felter bruges til duplikat-detection? (dato + beløb + beskrivelse?)
- [x] **C8.** Hvordan håndteres legitime duplikater? (to køb samme dag, samme beløb, samme butik)
- [x] **C9.** Forventet CSV-kolonneformat, eller fleksibel mapping ved import?
- [x] **C10.** Dato-format ved import (DD-MM-YYYY, YYYY-MM-DD, eller auto-detect?)
- [x] **C11.** Tal-format ved import (1.234,56 dansk vs 1,234.56 engelsk)

> **Beslutning C7-C8:** Duplikat-detection med hash og bruger-godkendelse.
>
> **Felter til duplikat-detection:**
> - `external_id` - bankens unikke reference (gemmes separat, kan være null)
> - `import_hash` - hash af (konto_id + dato + tidsstempel + beløb + beskrivelse)
> - Tidsstempel inkluderes hvis tilgængeligt
>
> **Duplikat-tjek:**
> 1. Hvis `external_id` findes → tjek mod eksisterende
> 2. Uanset → tjek også mod `import_hash`
> - Begge gemmes separat for fleksibilitet
>
> **Legitime duplikater:**
> - Potentielle duplikater vises til brugeren ved import
> - Brugeren vælger: "Skip (duplikat)" eller "Importér (ny transaktion)"
> - Ved automatisk import: Brugeren får besked næste gang de åbner budgettet
>
> **Beslutning C9-C11:** Fleksibel mapping med auto-detect.
>
> **CSV-import flow:**
> 1. Bruger uploader CSV
> 2. System viser preview af første rækker
> 3. Bruger mapper kolonner (Dato, Beløb, Beskrivelse, Bank-reference, Tidsstempel, Saldo)
> 4. Mapping gemmes som "profil" til fremtidige imports
>
> **Dato- og tal-format:**
> - Auto-detect baseret på data
> - Brugeren bekræfter/justerer i preview
> - Gemmes i import-profilen
> - Preview viser fortolkning så brugeren kan verificere
>
> **Import-profiler:**
> - Gemmes per konto (f.eks. "Nordea CSV", "Danske Bank CSV")
> - Kan genbruges ved fremtidige imports

### Ukategoriserede transaktioner

- [x] **C12.** Default-adfærd når ingen regel matcher?
- [x] **C13.** Er der en "catch-all" kategori eller forbliver de bare ukategoriserede?

> **Beslutning C12-C13:** Ingen automatisk catch-all, transaktioner forbliver ukategoriserede.
>
> **Når ingen regel matcher:**
> - Transaktionen forbliver ukategoriseret (ingen automatisk tildeling)
> - Vises i "afventer"-liste opdelt på indtægter/udgifter
> - Brugeren håndterer manuelt: tildel budgetpost, opret ny, eller opret regel
>
> **Ukategoriserede transaktioner tæller med:**
> - Påvirker periodens totaler (samlet ind/ud)
> - Respekterer konto-formål (transaktion på opsparingskonto påvirker kun opsparings-sektionen)
> - Er "virkelighed" der mangler kobling til "forventning" (budgetpost)
>
> **Ingen skjult catch-all:**
> - Ingen "Udgift → Andet" eller lignende automatisk fallback
> - "Catch-all" er reelt afventer-listen selv
> - Tvinger brugeren til bevidst stillingtagen

- [x] **C14.** Timeout/påmindelse for ukategoriserede transaktioner?

> **Beslutning C14:** Ingen automatiske påmindelser i MVP.
> - Ingen timeout, emails eller push-notifikationer
> - Synlig indikation i UI: tæller/badge ved afventer-listen (f.eks. "Afventer (12)")
> - Vises på dashboard så brugeren ser det ved login
> - Brugeren kan have ukategoriserede transaktioner i al evighed - ingen tvang
> - Post-MVP: Valgfri opsummerings-email kan tilføjes som opt-in

---

## D. Brugermodel og deling

- [x] **D1.** Roller i delte budgetter: Har alle brugere samme rettigheder?
- [x] **D2.** Ejer vs. medlem - forskellige rettigheder?

> **Beslutning D1-D2:** Simpel rollemodel med Ejer og Medlem.
>
> | Handling | Ejer | Medlem |
> |----------|------|--------|
> | Se alt | Ja | Ja |
> | Oprette/redigere transaktioner | Ja | Ja |
> | Oprette/redigere budgetposter | Ja | Ja |
> | Oprette/redigere regler | Ja | Ja |
> | Tilføje/fjerne konti | Ja | Ja |
> | Invitere nye medlemmer | Ja | Nej |
> | Fjerne medlemmer | Ja | Nej |
> | Slette budgettet | Ja | Nej |
> | Forlade budgettet | - | Ja |
>
> - Medlemmer har fuld redigerings-adgang (høj tillid, typisk familie/partner)
> - Ejer beskytter mod utilsigtet sletning og medlemshåndtering
> - Post-MVP: "Læseadgang"-rolle kan tilføjes hvis behov opstår

- [x] **D3.** Hvordan inviteres en bruger til et budget?

> **Beslutning D3:** Email-invitation med token-link.
> - Ejer indtaster email → system sender invitation med unikt link
> - Token-levetid: 7 dage (kan gen-sendes)
> - Modtager klikker link → login/opret konto → tilføjes som Medlem
> - Afventende invitationer vises i budget-indstillinger, kan annulleres
> - Validering: Ingen duplikat-invitationer, ingen selv-invitation

- [x] **D4.** Kan man forlade et delt budget? Hvad sker der med ens data?

> **Beslutning D4:** Ja, man kan forlade. Data forbliver i budgettet.
> - Medlem kan altid forlade
> - Ejer kan kun forlade hvis der er mindst én anden bruger (som bliver ny ejer)
> - Sidste bruger kan ikke forlade - skal slette budgettet
> - Alle data (transaktioner, konti, etc.) forbliver i budgettet
> - `created_by`/`updated_by` referencer bevares
> - Bekræftelses-dialog advarer om at adgang mistes

- [x] **D5.** Kan samme bankkonto bruges i flere budgetter?
- [x] **D6.** Er konti personlige eller tilhører de budgettet?

> **Beslutning D5-D6:** Konti tilhører ét budget, ingen global unikhed.
> - Konto oprettes i ét specifikt budget og lever der (`budget_id` required)
> - **Inden for ét budget:** Duplikat-check - samme fysiske bankkonto kan kun tilføjes én gang
> - **På tværs af budgetter:** Ingen tjek - samme konto kan bruges uafhængigt
> - Begrundelse: Undgår data-læk mellem brugere og "trolling" ved at reservere kontonumre
> - Delte budgetter løser use-casen hvor flere personer skal se samme konto

---

## E. Authentication og sikkerhed

- [x] **E1.** Login-metode: Email/password, OAuth (Google/Apple), eller begge?

> **Beslutning E1:** Email/password til MVP.
> - Simpel, velforstået løsning uden eksterne afhængigheder
> - Passer naturligt med email-invitation (D3)
> - OAuth (Google) kan tilføjes post-MVP som supplement
- [x] **E2.** Password-krav (længde, kompleksitet)?

> **Beslutning E2:** Længde over kompleksitet.
> - Minimum: 12 tegn
> - Maximum: 128 tegn
> - Ingen kompleksitetskrav (ingen krav om tal, store bogstaver, specialtegn)
> - Valgfrit: Tjek mod top 10.000 mest almindelige passwords
> - UI: Password strength-indikator (find passende bibliotek til dette)
- [x] **E3.** Session-håndtering (JWT, server-side sessions?)

> **Beslutning E3:** Server-side sessions + API-tokens.
>
> **Web UI (sessions):**
> - Session-ID i cookie (HttpOnly, Secure, SameSite=Strict)
> - Session-data i PostgreSQL
> - Levetid: 30 dage (sliding expiration ved aktivitet)
> - Ved logout/password-skift: Invalidér alle sessions for brugeren
>
> **Programmatisk adgang (API-tokens):**
> - Brugeren kan oprette API-tokens i indstillinger
> - Tokens har valgfri udløbsdato (eller "aldrig")
> - Tokens kan have begrænset scope (læs/skriv, specifikke budgetter)
> - Bruges til integrationer (Home Assistant, scripts, etc.)
> - Tokens kan tilbagekaldes individuelt
- [x] **E4.** Password-reset flow

> **Beslutning E4:** Standard email-token flow.
> - Bruger anmoder om reset → email med unikt link sendes
> - Token-levetid: 1 time
> - Token kan kun bruges én gang, hashet i database
> - Ved nyt password: Alle sessions invalideres
> - Rate limiting: Max 3 reset-emails per time per email
> - Feedback: Altid "Hvis emailen findes, har vi sendt et link" (ingen enumeration)
- [x] **E5.** Email-verifikation ved oprettelse?

> **Beslutning E5:** Ja, påkrævet før brug.
> - Email skal verificeres før brugeren kan tilgå appen
> - Flow: Opret konto → "Tjek din email" → Klik link → Adgang
> - Token-levetid: 24 timer
> - Kan gen-sende verifikations-email (rate limited: max 3 per time)
> - Uverificerede konti slettes automatisk efter 7 dage

---

## F. API-design

- [x] **F1.** Forecast-beregning: On-the-fly eller cached?

> **Beslutning F1:** On-the-fly beregning, ingen cache til MVP.
> - Forecast beregnes ved hvert request - ingen persisteret cache
> - Fokus på optimeret datalagring og effektive SQL-queries
> - Aggregater beregnes direkte i databasen (undgå N+1 queries)
> - Budgetpost-gentagelser udfoldes i hukommelsen (billigt for personlige budgetter)
> - Hvis performance bliver et problem post-MVP, kan cache-lag tilføjes (f.eks. Redis)

- [x] **F2.** Hvor langt frem beregnes forecast? (konfigurerbart?)

> **Beslutning F2:** Fleksibel horisont, default 12 måneder.
> - Default visning: 12 perioder (nuværende + 11 fremtidige, eller mix af forrige/fremtidige)
> - API accepterer vilkårlig periode-range (start/slut måned)
> - Ingen hård grænse - brugeren kan se f.eks. hele 2027 fra 2026
> - Beregningen holdes billig via effektiv udfoldning af gentagelsesmønstre
> - Frontend tilbyder standard-views (3, 6, 12 måneder) + mulighed for custom range

- [x] **F3.** Validerings-respons format (advarsler vs. blokerende fejl)

> **Beslutning F3:** To-niveau respons med errors og warnings.
> - **Errors:** Blokerende fejl, handlingen afvises (manglende felter, ugyldigt format, ugyldige referencer)
> - **Warnings:** Handlingen gennemføres, men brugeren adviseres (budget i minus, potentiel duplikat)
> - Respons inkluderer `success`, `data`, `errors[]` og/eller `warnings[]`
> - Konkret format kan justeres under udvikling baseret på valgt tech stack

- [x] **F4.** Pagination-strategi for transaktionslister

> **Beslutning F4:** Cursor-baseret pagination.
> - Cursor er encoded reference til sidste element (f.eks. base64 af id + dato)
> - Stabil ved ændringer - ingen "hop" eller duplikater når data ændres
> - Format: `GET /api/.../transactions?limit=50&cursor=abc123`
> - Respons inkluderer `next_cursor` (null hvis ingen flere)

- [x] **F5.** Rate limiting?

> **Beslutning F5:** Ja, simpel rate limiting.
> - Generelle API-kald: 100/min per bruger
> - Login-forsøg: 5/min per IP
> - Password reset / email-verifikation: Allerede defineret i E4/E5
> - HTTP 429 "Too Many Requests" ved overskridelse med `Retry-After` header
> - MVP: In-memory tæller (simpelt)
> - Post-MVP: Redis-baseret hvis skalering kræves

---

## G. UI/UX-beslutninger

- [x] **G1.** Flow for oprettelse af budgetpost (wizard, side-panel, modal?)

> **Beslutning G1:** Modal som primært UI-mønster.
> - Modals bruges til oprettelse og redigering (budgetposter, konti, regler, etc.)
> - Fokuseret interaktion - én ting ad gangen
> - Simpelt og velkendt mønster
> - På mobil: Modal fylder hele skærmen

- [x] **G2.** Visualisering af ukategoriserede transaktioner (badge, inbox, liste?)

> **Beslutning G2:** Multi-niveau synlighed.
> - **Dashboard:** "AFVENTER" kort med tæller og "[Håndtér]" knap
> - **Navigation:** Badge på "Transaktioner" menupunkt (forsvinder når tom)
> - **Transaktioner-skærm:** Fremhævet banner øverst med "[Vis]" filter-knap
> - **Transaktionskort:** Visuelt differentieret (f.eks. stiplet border)
> - Tre status-grupper: Ukategoriseret, Afventer bekræftelse, Afventer bilag
- [x] **G3.** Forecast-visualisering (linjegraf, søjlediagram, tabel?)

> **Beslutning G3:** Linjegraf + tabel + nøgletal.
> - **Primær:** Linjegraf over saldo-udvikling (X=tid, Y=saldo)
> - **Nøgletal-kort:** "Laveste punkt" og "Næste store udgift"
> - **Periode-tabel:** Måned | Start | Ind | Ud | Slut (med advarsler)
> - **Interaktion:** Tidshorisont-vælger [3/6/12 mdr], hover for detaljer
> - Kan justeres efter MVP baseret på brugeroplevelse
- [x] **G4.** Mobile-first eller desktop-first design?

> **Beslutning G4:** Desktop-first med responsivt design.
> - Desktop er primær platform (regnskab, import, planlægning)
> - Mobil tilpasses efterfølgende (status-tjek, hurtig kategorisering)
> - Breakpoint: 768px
> - Mobil: Bottom-nav, stacked cards, fullscreen modals
- [x] **G5.** Farvepalette og design-tokens

> **Beslutning G5:** CSS custom properties med semantiske navne.
> - Lys tema først (mørk tema post-MVP)
> - Tokens: `--bg-page`, `--bg-card`, `--text-primary`, `--text-secondary`, `--accent`, `--positive`, `--negative`, `--warning`, `--border`
> - Værdier fra CLAUDE.md paletten (Tailwind-inspireret)
> - Semantiske navne (`--positive`) frem for farvenavne (`--green`)
- [x] **G6.** Ikon-bibliotek (custom SVG, eksisterende bibliotek?)

> **Beslutning G6:** Lucide Icons.
> - Open source (ISC licens), konsistent stil, stor samling
> - Inline SVG for nem CSS-styling
> - Download kun nødvendige ikoner (ikke hele pakken)

---

## H. Tekniske beslutninger

- [x] **H1.** Grafer: Hvilket bibliotek? (Chart.js, D3, uPlot, andet?)

> **Beslutning H1:** Apache ECharts.
> - Built-in Sankey support (vigtig for pengeflow-visualisering)
> - Dækker alle behov: linjegraf, søjler, pie, Sankey
> - Custom build for at reducere størrelse (~300 KB med kun nødvendige moduler)
- [x] **H2.** Authentication-bibliotek/løsning

> **Beslutning H2:** Custom implementation med standard-biblioteker.
> - `passlib` med bcrypt til password-hashing
> - `itsdangerous` til signerede tokens
> - `slowapi` til rate limiting
> - Ingen tungt auth-framework - simpelt og forståeligt
- [x] **H3.** Database-migrations strategi

> **Beslutning H3:** Alembic.
> - Standard for SQLAlchemy migrations
> - Auto-generering fra model-ændringer
> - Versioneret historik i git
> - `alembic upgrade head` ved deployment
- [x] **H4.** Test-strategi (unit, integration, e2e?)

> **Beslutning H4:** Pragmatisk MVP-tilgang.
> - **Backend:** pytest - unit tests for forretningslogik, integration tests for API
> - **Frontend:** Manuel test til MVP
> - Fokus på kritiske paths: auth, transaktion-tildeling, forecast
> - Ingen coverage-mål, ingen E2E tests i MVP
- [x] **H5.** CI/CD pipeline

> **Beslutning H5:** Udskudt til post-MVP.
> - MVP: GitHub som backup/versionering, manuel deployment
> - Post-MVP: GitHub Actions med lint, test, og auto-deploy
- [x] **H6.** Hosting/deployment target

> **Beslutning H6:** Selfhosted med Docker.
> - Designet til selfhosting (brugerens egen server/VPS)
> - Docker Compose til deployment (API, UI, PostgreSQL, reverse proxy)
> - Brugeren håndterer egen TLS/domæne

---

## I. MVP-scope

- [x] **I1.** Hvilke funktioner er must-have til MVP?
- [x] **I2.** Hvilke funktioner er nice-to-have (post-MVP)?

> **Beslutning I1-I2:** MVP-scope.
>
> **Must-have (MVP):**
> - Bruger-registrering og login (email/password)
> - Opret/rediger budget og konti
> - Manuel oprettelse af transaktioner
> - Kategorisering (tildel transaktion til budgetpost)
> - Budgetposter med gentagelse
> - Dashboard (saldo, afventer-liste, faste udgifter)
> - Simpel forecast (linjegraf + tabel)
>
> **Nice-to-have (post-MVP, prioriteret):**
> 1. CSV-import (høj)
> 2. Regler/auto-kategorisering (høj)
> 3. Delte budgetter (medium)
> 4. Mørkt tema (lav)
> 5. Kvitteringshåndtering/OCR (lav)
> 6. API-tokens (lav)
- [x] **I3.** Er delte budgetter med i MVP?

> **Beslutning I3:** Nej, post-MVP (medium prioritet).

- [x] **I4.** Er import med i MVP?

> **Beslutning I4:** Nej, post-MVP (høj prioritet - første feature efter MVP).

- [x] **I5.** Er forecast med i MVP?

> **Beslutning I5:** Ja, simpel version (linjegraf + tabel).

---

*Sidst opdateret: 2026-02-03*
