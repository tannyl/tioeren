# Tiøren - Product Specification

> This document contains the complete product specification for Tiøren.
> It is NOT auto-loaded into Claude Code sessions. Reference it when needed
> for domain understanding, UI design, or architecture decisions.

> "Så faldt tiøren" - dansk ordsprog

Personlig økonomi-app med fokus på **overblik over nutid OG fremtid**.

---

## Problemet vi løser

Eksisterende løsninger (Firefly III, YNAB, Spiir, etc.) fokuserer på:

- "Hvad har jeg brugt denne måned?"
- "Hvor mange penge har jeg lige nu?"

Men de svarer dårligt på:

- "Har jeg råd til forsikringen i november?"
- "Hvornår løber min opsparing tør hvis jeg fortsætter sådan?"
**Tiøren giver overblik over både fortid, nutid og fremtid.**

---

## Kernekoncepter

### Hierarki

```
Bruger (User)
  └── Budgetter (Budgets) - kan deles med andre brugere, har valuta
        ├── Beholdere (Containers) - tre typer:
        │     ├── Pengekasser (Cashboxes) - daglig økonomi, tæller i "til rådighed"
        │     ├── Sparegrise (Piggybanks) - øremærket opsparing
        │     └── Gældsbyrder (Debts) - lån, kassekredit, gæld
        │           └── Transaktioner (Transactions) - faktiske bevægelser
        ├── Aktive budgetposter (forventninger) - hvad vi forventer NU og fremad
        │     └── Beløbsmønstre - definerer beløb, gentagelse og beholdere
        ├── Arkiverede budgetposter - snapshots af afsluttede perioder
        │     └── Beløbsforekomster - konkrete forventede beløb for perioden
        └── Regler (Rules) - auto-matching
              └── henviser til Budgetposter
```

**Flow:** Transaktion → Beholder → Beløbsmønstre der bruger denne beholder → Regler → Tildeling til Beløbsmønster/Beløbsforekomst

### Visualisering af relationer

```
┌─────────────────────────────────────────────────────────────────┐
│                 BUDGET "Min økonomi"                            │
│              (kan deles med andre brugere, valuta: DKK)         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PENGEKASSER (daglig økonomi, tæller i "til rådighed"):         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Lønkonto     │ │ Mastercard   │ │ Kontanter    │            │
│  │ pengekasse   │ │ pengekasse   │ │ pengekasse   │            │
│  │ 10.000 kr    │ │ -500 kr      │ │ 200 kr       │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│                                                                 │
│  Til rådighed (pengekasser): 9.700 kr                           │
│                                                                 │
│  SPAREGRISE (øremærket opsparing):                              │
│  ┌──────────────┐                                               │
│  │ Ferie-       │                                               │
│  │ opsparing    │                                               │
│  │ sparegris    │                                               │
│  │ 12.000 kr    │                                               │
│  └──────────────┘                                               │
│                                                                 │
│  GÆLDSBYRDER (lån, kassekredit):                                │
│  ┌──────────────┐ ┌──────────────┐                              │
│  │ Billån       │ │ Kassekredit  │                              │
│  │ gæld         │ │ gæld         │                              │
│  │ ramme 200k   │ │ ramme 50k    │                              │
│  │ -150.000 kr  │ │ -10.000 kr   │                              │
│  │ rente 3,5%   │ │ tillad udtræk│                              │
│  └──────────────┘ └──────────────┘                              │
│                                                                 │
│  BUDGETPOSTER:                                                  │
│  ├── Indtægt (penge ind fra ekstern)                            │
│  │     └── Løn +25.000            beholdere: [Lønkonto]        │
│  ├── Udgift (penge ud til ekstern)                              │
│  │     ├── Husleje -8.000         beholdere: [Lønkonto]        │
│  │     ├── Mad -3.000             beholdere: [Lønkonto, MC]    │
│  │     ├── Bilrep. -1.000 (akkum) beholdere: [Lønkonto]        │
│  │     └──  (Renter billån beregnes automatisk af gældsbyrden) │
│  ├── Overførsel (penge mellem beholdere)                        │
│  │     ├── Lønkonto → Ferieopsparing  2.000/md                 │
│  │     └── Lønkonto → Billån          3.500/md (afdrag)        │
│  │                                                              │
│  TRANSAKTIONER (på beholdere):                                  │
│                                                                 │
│  Lønkonto (pengekasse):                                         │
│  • 28/1: +25.000 "Løn" → Indtægt > Løn                         │
│  • 1/2:  -8.000 "Husleje" → Udgift > Bolig > Husleje           │
│  • 1/2:  -2.000 "Til opsparing" → Overførsel                   │
│  • 1/2:  -3.500 "Billån ydelse" → Overførsel                   │
│                                                                 │
│  Ferieopsparing (sparegris):                                    │
│  • 1/2:  +2.000 "Fra Lønkonto" → Overførsel                    │
│                                                                 │
│  Billån (gæld):                                                 │
│  • 1/2:  +3.500 "Fra Lønkonto" → Overførsel (afdrag)           │
│  • 1/4:  -1.288 "Renter" → Systemberegnet (kvartalsvise)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detaljerede koncepter

### 1. Beholder (Container)

En beholder er et sted hvor penge "bor". Beholdere er aktive budgetteringsregler - ikke bare passive saldo-trackere. De definerer hvad der er tilladt og advarer når regler brydes.

Der er tre beholdertyper: **pengekasse**, **sparegris** og **gældsbyrde**.

| Felt               | Beskrivelse                                             |
| ------------------ | ------------------------------------------------------- |
| navn               | "Lønkonto", "Mastercard", "Ferieopsparing", "Billån"   |
| type               | pengekasse, sparegris, gæld                             |
| startsaldo         | Saldo ved oprettelse (i øre)                            |
| banktilknytning    | Valgfri kobling til rigtig bankkonto (se nedenfor)      |

**Beholdertyper:**

| Type             | Dansk UI-navn | I "til rådighed" | Formål                               |
| ---------------- | ------------- | ----------------- | ------------------------------------ |
| **Cashbox**      | Pengekasse    | Ja                | Daglig økonomi. Pengene du lever af. |
| **Piggybank**    | Sparegris     | Nej               | Øremærket opsparing. Kan låses.      |
| **Debt**         | Gældsbyrde    | Nej               | Enhver form for gæld.               |

Beholdertypen bestemmer hvilke ekstra felter og regler der gælder, og om saldoen indgår i "til rådighed".

#### Pengekasse (Cashbox)

Pengekasser er daglig økonomi - pengene du lever af og betaler regninger med. Deres samlede saldo udgør "til rådighed".

**Pengekasse-specifikke felter:**

| Felt              | Type        | Beskrivelse                                                  |
| ----------------- | ----------- | ------------------------------------------------------------ |
| `overdraft_limit` | BIGINT NULL | Maks. overtræk i negativt øre. NULL = ingen overtræk (kan ikke gå i minus). |

**Overtræk:** En pengekasse kan valgfrit have overtræk. Systemet advarer hvis den fremskrevne saldo ville gå under overtrækgrænsen.

| Eksempel               | `overdraft_limit` | Betydning                     |
| ---------------------- | ----------------- | ----------------------------- |
| Lønkonto uden overtræk | NULL              | Kan ikke gå i minus           |
| Lønkonto med overtræk  | -500000           | 5.000 kr overtræk tilladt     |
| Mastercard             | -2000000          | 20.000 kr kreditgrænse        |

#### Sparegris (Piggybank)

Sparegrise er øremærket opsparing. De tæller ikke i "til rådighed" og kan valgfrit låses.

**Sparegris-specifikke felter:**

| Felt     | Type         | Beskrivelse                                              |
| -------- | ------------ | -------------------------------------------------------- |
| `locked` | BOOLEAN NULL | Når true, kan der kun indsættes (fx pension, bundne opsparinger). |

**Låst-flag:** Blokerer budgetposter der ville trække penge UD af sparegrisen. Kun indbetalinger tilladt.

#### Gældsbyrde (Debt)

Gældsbyrder repræsenterer enhver form for gæld - traditionelle lån, kassekreditter, afdragsordninger. Den samler det der tidligere var separate "lån" og "kassekredit" typer.

Forskellen mellem et lån og en kassekredit er konfiguration, ikke type:
- **Lån:** Udtræk slået fra, kræver afdrag, har rente
- **Kassekredit:** Udtræk tilladt, intet krævet afdrag, har rente

**Gæld-specifikke felter:**

| Felt                 | Type         | Beskrivelse                                                         |
| -------------------- | ------------ | ------------------------------------------------------------------- |
| `credit_limit`       | BIGINT       | Kreditramme/lånebeløb i negativt øre. **Påkrævet.** |
| `allow_withdrawals`  | BOOLEAN NULL | Kan der trækkes penge (lånes mere)? True = kassekredit. False = kun afdrag. |
| `interest_rate`      | DECIMAL NULL | Årlig rente i procent (f.eks. 3.5). |
| `interest_frequency` | TEXT NULL    | Hvor tit renter tilskrives: `monthly`, `quarterly`, `yearly`. |
| `required_payment`   | BIGINT NULL  | Mindste månedlige afdrag i øre. NULL = intet krav. |

**Renter som systemberegning:**

Renter beregnes automatisk af systemet - de oprettes IKKE som budgetposter:
- Systemet bruger `interest_rate` og `interest_frequency` til at fremskrive rentetilskrivninger
- Disse vises som systemberegnede hændelser i tidslinjen/forecast
- De påvirker den fremskrevne saldo men kan ikke redigeres som budgetposter
- Beregning: saldo × (årlig rente / antal perioder pr. år)

**Eksempel - Billån:**
```
Gæld: Billån
├── Kreditramme:     200.000 kr
├── Startsaldo:      -150.000 kr
├── Rente:           3,5% p.a., kvartalsvis
├── Kræver afdrag:   3.000 kr/md
├── Tillad udtræk:   Nej
│
├── Feb: Saldo -150.000 → Afdrag +3.000 → -147.000
├── Mar: Saldo -147.000 → Afdrag +3.000 → -144.000
├── Apr: Saldo -144.000 → Afdrag +3.000 → Renter -1.288 → -142.288
│                                          ↑ systemberegnet
```

**Eksempel - Kassekredit:**
```
Gæld: Kassekredit Nordea
├── Kreditramme:     50.000 kr
├── Startsaldo:      -10.000 kr
├── Rente:           18,5% p.a., månedlig
├── Kræver afdrag:   Nej
├── Tillad udtræk:   Ja
```

**Adfærdsregler for gæld:**

| Regel                          | Systemadfærd                                                      |
| ------------------------------ | ----------------------------------------------------------------- |
| `credit_limit`                 | Blokerer budgetposter der ville overskride kreditrammen           |
| `allow_withdrawals = false`    | Blokerer budgetposter der trækker FRA gælden                     |
| `required_payment` sat         | Advarer hvis budgettet ikke indeholder nok afdrag pr. måned      |
| `interest_rate` + `frequency`  | Systemberegnede rentetilskrivninger i fremskrivning/tidslinje    |

#### Banktilknytning (alle typer)

Enhver beholder kan valgfrit tilknyttes en rigtig bankkonto. Dette erstatter det tidligere "datakilde"-koncept (bank/kontant/virtuel). En beholder uden banktilknytning administreres manuelt.

**Banktilknytnings-felter:**

| Felt                  | Type      | Beskrivelse                      |
| --------------------- | --------- | -------------------------------- |
| `bank_name`           | TEXT NULL | Banknavn (f.eks. "Nordea")        |
| `bank_account_name`   | TEXT NULL | Kontonavn hos banken              |
| `bank_reg_number`     | TEXT NULL | Registreringsnummer               |
| `bank_account_number` | TEXT NULL | Kontonummer                       |

Banktilknytningen bruges til:
- Fremtidig CSV-import (identificér hvilken beholder transaktioner skal importeres til)
- Fremtidig bank-API integration
- Brugerens overblik (hvilken bankkonto hører til hvilken beholder)

En beholder uden banktilknytning er analog med de tidligere "kontant" og "virtuel" datakilder.

#### Samlet adfærdsoversigt

| Regel                          | Pengekasse | Sparegris | Gæld |
| ------------------------------ | ---------- | --------- | ---- |
| Overtræksgrænse                | Valgfrit   | -         | -    |
| Kreditramme                    | -          | -         | Påkrævet |
| Låst (kun indbetalinger)       | -          | Valgfrit  | Via `allow_withdrawals` |
| Renter (systemberegnet)        | -          | -         | Valgfrit |
| Kræver afdrag                  | -          | -         | Valgfrit |
| I "til rådighed"               | Ja         | Nej       | Nej  |

**Relationer:**

- Tilhører ét Budget
- Transaktioner sker på én specifik beholder

**Interne overførsler:**

Når penge flyttes mellem beholdere inden for samme budget, oprettes to bundne transaktioner:

```
Lønkonto:   -500 kr  "Til Mastercard" ─┐
                                       ├─ bundet som intern overførsel
Mastercard: +500 kr  "Fra Lønkonto"  ─┘
```

Interne overførsler påvirker per-beholder saldo, men IKKE budgettets samlede formue.

### 2. Transaktion (Transaction)

En transaktion er en **faktisk pengebevægelse** på en beholder - ikke en forventning, men noget der er sket. Transaktioner er "virkeligheden" i Tiøren, mens budgetposter er "forventningen".

| Felt                 | Beskrivelse                                 |
| -------------------- | ------------------------------------------- |
| dato                 | Hvornår skete det                           |
| beløb                | Positivt = ind, negativt = ud               |
| beskrivelse          | Fra banken eller manuelt                    |
| beholder             | Hvilken beholder (påkrævet)                 |
| status               | Se nedenfor                                 |
| er_intern_overførsel | Om dette er del af intern flytning          |
| modpart_transaktion  | Reference til den anden side af overførslen |

**Transaktionsstatus:**

| Status               | Beskrivelse                                                  |
| -------------------- | ------------------------------------------------------------ |
| ukategoriseret       | Ingen regel matchede, kræver manuel håndtering               |
| afventer_bekræftelse | Regel matchede, men kræver brugerbekræftelse                 |
| afventer_bilag       | Regel kræver kvittering/opgørelse før endelig kategorisering |
| kategoriseret        | Færdigbehandlet og tildelt budgetpost(er)                    |

**Transaktionstyper:**

| Type              | Påvirker samlet saldo | Eksempel                |
| ----------------- | --------------------- | ----------------------- |
| Indtægt           | Ja (+)                | Løn, renter             |
| Udgift            | Ja (-)                | Køb, regninger          |
| Intern overførsel | Nej                   | Penge mellem egne beholdere |

**Relationer:**

- Tilhører én Beholder (fysisk faktum)
- Kan være bundet til en modpart-transaktion (intern overførsel)
- Kan tildeles beløbsmønstre (aktiv periode) eller beløbsforekomster (afsluttet periode)

**Flow når transaktion ankommer:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. TRANSAKTION ANKOMMER                                         │
│    -523 kr "NETS *FØTEX" på Lønkonto                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. FIND BELØBSMØNSTRE DER BRUGER DENNE BEHOLDER                  │
│    Lønkonto bruges af beløbsmønstre på:                         │
│    ├── "Husleje" (kun Lønkonto)                                 │
│    ├── "Mad-budget" (Lønkonto, Mastercard, Kontanter)           │
│    └── "Husholdning" (Lønkonto, Mastercard)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. FIND REGLER DER HENVISER TIL DISSE BUDGETPOSTER              │
│    Relevante regler:                                            │
│    ├── "Husleje-match" → Husleje                                │
│    └── "Føtex-split" → Mad-budget, Husholdning                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. KØR MATCHENDE REGLER                                         │
│    "Føtex-split" matcher (beskrivelse indeholder "FØTEX")       │
│    ├── 80% (418 kr) → Mad-budget                                │
│    └── 20% (105 kr) → Husholdning                               │
│                                                                 │
│    Status: kategoriseret (eller afventer_bekræftelse)           │
└─────────────────────────────────────────────────────────────────┘
```

**Split-kategorisering eksempel:**

```
Transaktion: -523 kr hos Føtex

Split på budgetposter:
├── 418 kr → Mad-budget (budgetpost)
└── 105 kr → Husholdning (budgetpost)
```

**Fremtidig feature:** Kvitteringsscanning med OCR + LLM til automatisk split-forslag.

**Tildelingsmodel (fast beløb + "resten"):**

- Hver tildeling gemmes som et fast beløb (i øre)
- Én tildeling kan markeres som "resten" (`is_remainder = true`)
- "Resten" beregnes som: transaktionsbeløb minus sum af øvrige tildelinger
- Hvis kun én tildeling, er den implicit "resten"
- UI kan vise/beregne procent som hjælpemiddel, men DB gemmer beløb
- Split kan ændres efterfølgende
- Validering: Sum må aldrig overstige transaktionsbeløb, "resten" kan ikke blive negativ

**Delvis tildeling:**

- En transaktion kan have en "ufordelt rest" (delvis tildeling er tilladt)
- Transaktioner med ufordelt beløb vises i afventer-listen
- Brugeren kan arbejde sig igennem transaktioner løbende
- Man kan aldrig fordele mere end transaktionens beløb
- Man kan ikke fordele 0 kr (validering)

**Ukategoriserede transaktioner:**

- Når ingen regel matcher, forbliver transaktionen ukategoriseret (ingen automatisk catch-all)
- Vises i "afventer"-liste opdelt på indtægter/udgifter
- Brugeren håndterer manuelt: tildel budgetpost, opret ny, eller opret regel
- Ukategoriserede transaktioner påvirker periodens totaler (samlet ind/ud)
- Respekterer beholdertype (transaktion på ikke-pengekasse påvirker ikke "til rådighed" saldo)
- Ingen timeout eller påmindelser i MVP - synlig badge/tæller i UI er tilstrækkeligt

### 3. Budgetpost (forventning)

En budgetpost beskriver **hvad vi forventer skal ske** - en plan for fremtidige pengebevægelser. Budgetposter er "forventningen" i Tiøren, mens transaktioner er "virkeligheden".

En enkelt budgetpost kan matche med **mange transaktioner** over tid (f.eks. "Husleje" matcher med 12 huslejetransaktioner om året).

**Aktive og arkiverede budgetposter er adskilte:**

- **Aktive budgetposter** (`budget_posts`): Beskriver hvad der sker NU og fremad. Ingen periode - der eksisterer kun **én aktiv budgetpost per kategori-sti**.
- **Arkiverede budgetposter** (`archived_budget_posts`): Snapshots af hvad der var forventet i en afsluttet periode. Har `period_year` + `period_month`. Fuldt selvstændige (ingen FK til live data for visning).

#### Aktiv budgetpost

| Felt           | Beskrivelse                                     |
| -------------- | ----------------------------------------------- |
| retning        | indtægt, udgift, overførsel                     |
| category_path  | Kategori-sti som TEXT[] (påkrævet for indtægt/udgift, null for overførsel). Navn = sidste element. |
| display_order  | Sortering som INTEGER[] (matcher category_path niveauer)  |
| akkumuler      | Kun for udgift: overføres ubrugt beløb til næste periode? |
| beholdere      | Beholder-pulje for indtægt/udgift (se beholderbinding nedenfor) |
| via_beholder   | Valgfri gennemløbsbeholder for indtægt/udgift (se nedenfor) |
| fra_beholder   | Kildebeholder for overførsel (alle beholdertyper) |
| til_beholder   | Destinationsbeholder for overførsel (alle beholdertyper) |
| beløbsmønstre  | Et eller flere beløbsmønstre (se nedenfor)      |

**Navngivning:** Budgetpostens navn er det sidste element i `category_path`. F.eks. `["Bolig", "Husleje"]` → navnet er "Husleje", gruppen er "Bolig". For overførsler er identiteten "fra-beholder → til-beholder".

**Hierarki via category_path:** Budgetposter grupperes automatisk efter delte præfikser i `category_path`. To poster med `["Bolig", "Husleje"]` og `["Bolig", "El"]` grupperes under "Bolig". Rod-niveauet (Indtægt/Udgift) er implicit fra `direction`-feltet.

**UNIQUE constraint:** `(budget_id, direction, category_path)` WHERE `category_path IS NOT NULL AND deleted_at IS NULL` - sikrer unik kategori-sti per retning. Overførsler har i stedet `UNIQUE(from_container_id, to_container_id)`.

**Sortering:** `display_order INTEGER[]` sorteres leksikografisk af PostgreSQL: `[0] < [0,0] < [0,1] < [1]`. Gruppe-headere (kortere arrays) sorteres naturligt før deres børn.

**Relationer:**

- Tilhører ét Budget
- Indtægt/udgift: har en category_path der definerer navn og hierarki
- Overførsel: ingen category_path, men fra/til beholder
- Har et eller flere beløbsmønstre
- Regler henviser til budgetposter (for automatisk matching)
- Transaktioner bindes til beløbsmønstre (ikke til budgetposten direkte)

#### Beholderbinding (to-niveau model)

Beholderbindinger findes på **to niveauer**: budgetpost-niveau (beholder-pulje) og beløbsmønster-niveau (valgfrit subset).

**Budgetpost-niveau ("hvilke beholdere er involveret"):**

| Retning    | Felt               | Regler                                                            |
| ---------- | ------------------ | ----------------------------------------------------------------- |
| Indtægt    | `container_ids`    | ENTEN 1+ pengekasser ELLER præcis 1 ikke-pengekasse (gensidigt eksklusivt) |
| Udgift     | `container_ids`    | ENTEN 1+ pengekasser ELLER præcis 1 ikke-pengekasse (gensidigt eksklusivt) |
| Overførsel | `from_container_id` + `to_container_id` | Alle beholdertyper, skal være forskellige           |

- **Indtægt** = penge IND i systemet fra ekstern (arbejdsgiver, etc.) til én eller flere beholdere
- **Udgift** = penge UD af systemet til ekstern (butikker, regninger, etc.) fra én eller flere beholdere
- **Overførsel** = penge MELLEM beholdere i systemet (opsparing, afdrag, udligning, etc.)

Indtægt og udgift er altid i forhold til den eksterne verden. Der er intet "modpart"-koncept - det er implicit EXTERNAL.

**Bemærk:** Renter på gældsbyrder oprettes IKKE som budgetposter - de beregnes automatisk af gældsbyrdens renteindstillinger. Budgetposter dækker afdrag (overførsler til gælden) og evt. gebyrer.

**Valgfrit via-beholder:**

For indtægt/udgift kan en valgfri `via_container_id` angives. Denne bruges når penge passerer gennem en mellemkasse:

```
Budgetpost: "TV-køb" (Udgift)
├── Beholdere: [Ferieopsparing]
├── Via: Lønkonto (valgfrit)
│
│ Penge flyder: Ferieopsparing → Lønkonto → Ekstern (butik)
│ Lønkonto er gennemløb (netto nul)
```

Via-beholderen hjælper med automatisk sammenkobling af transaktioner. Brugeren kan også manuelt koble transaktioner uden via-beholder.

**Bemærk:** Via-beholder er kun relevant når en ikke-pengekasse (sparegris eller gæld) er valgt. Med pengekasser bruges via-beholder ikke.

**Beløbsmønster-niveau ("indsnævring af beholdere"):**

| Retning    | `container_ids` på beløbsmønster              |
| ---------- | --------------------------------------------- |
| Indtægt    | Valgfrit subset af budgetpostens beholder-pulje. Null = arver hele puljen. |
| Udgift     | Valgfrit subset af budgetpostens beholder-pulje. Null = arver hele puljen. |
| Overførsel | Null (beholdere er altid på budgetpost-niveau) |

**Eksempler:**

```
Budgetpost: "Løn" (Indtægt)
├── Beholdere: [Lønkonto]
├── Beløbsmønstre:
│   └── 25.000 kr, sidste hverdag

Budgetpost: "Dagligvarer" (Udgift)
├── Beholdere: [Lønkonto, Mastercard]
├── Beløbsmønstre:
│   ├── 3.000 kr/md, beholdere: [Lønkonto]     ← subset
│   └── 1.000 kr/md, beholdere: [Mastercard]    ← subset

Budgetpost: "TV fra opsparing" (Udgift)
├── Beholdere: [Ferieopsparing]
├── Via: Lønkonto
├── Beløbsmønstre:
│   └── 10.000 kr, engangs d. 15 marts

Budgetpost: (Overførsel) Lønkonto → Ferieopsparing
├── Fra: Lønkonto → Til: Ferieopsparing
├── Beløbsmønstre:
│   └── 2.000 kr, d. 1 hver måned

Budgetpost: (Overførsel) Lønkonto → Billån (afdrag)
├── Fra: Lønkonto → Til: Billån
├── Beløbsmønstre:
│   └── 3.500 kr, d. 1 hver måned
```

**Retnings-validering:**

- Budgetpost med retning **Indtægt** eller **Udgift** skal have `category_path` (ikke null, ikke tom) og `container_ids` (ikke tom)
- Budgetpost med retning **Overførsel** skal have `category_path = null` og `from_container_id` + `to_container_id`
- Retningen er implicit rod-niveauet, ingen separat kategori-rod nødvendig

**UI-flow for oprettelse af budgetpost:**

1. Vælg retning (Indtægt / Udgift / Overførsel)
2. For indtægt/udgift:
   - Vælg beholdere (puljen) - vælg enten pengekasser (multi-select) eller én særlig beholder (sparegris/gæld)
   - Angiv kategori-sti via breadcrumb-chips med autocomplete
   - Valgfrit: angiv via-beholder (gennemløbskasse, kun relevant for ikke-pengekasser)
3. For overførsel:
   - Vælg fra-beholder og til-beholder (alle beholdertyper, skal være forskellige)
4. For udgift: valgfrit slå akkumulering til (ubrugt beløb overføres til næste periode)
5. Tilføj beløbsmønstre (med valgfrit beholder-subset per mønster for indtægt/udgift)

#### Beløbsmønstre

En aktiv budgetpost har et eller flere beløbsmønstre. Hvert mønster definerer et beløb, hvornår det gælder, og hvilke beholdere der er involveret:

| Felt       | Beskrivelse                                      |
| ---------- | ------------------------------------------------ |
| beløb      | Beløbet i øre (mindste møntenhed)                |
| startdato  | Fra hvilken dato mønstret gælder (påkrævet)      |
| slutdato   | Til hvilken dato mønstret gælder (valgfri)       |
| gentagelse | Dato-baseret ELLER periode-baseret (se nedenfor) |
| beholdere  | Valgfrit subset af budgetpostens beholder-pulje (se beholderbinding ovenfor) |

**Beholdere på beløbsmønster-niveau:**

- For indtægt/udgift: valgfrit subset af budgetpostens `container_ids`. Null = arver hele puljen.
- For overførsel: null (beholdere er defineret på budgetpost-niveau)

**Transaktionsbinding:** Transaktioner bindes til beløbsmønstre (ikke direkte til budgetposten). Dette gør det muligt at spore hvilke specifikke forventninger en transaktion opfylder.

**Hvorfor flere mønstre?**

- Lønstigning fra 1. februar: Nyt mønster med højere beløb og ny startdato
- Sæsonvariation: El-regning varierer efter årstid (forskellige beløb per måned)
- Midlertidig ændring: Højere budget i december
- Beholderskift: Løn udbetales til ny beholder fra en dato

**Eksempel - El-regning med sæsonvariation:**

```
Budgetpost: "El-regning" (Udgift)
├── Beholdere: [Lønkonto]
├── Type: Fast
├── Beløbsmønstre:
│   ├── 5.000 kr i [jan, mar, nov, dec] - årligt
│   ├── 7.000 kr i [feb] - årligt
│   ├── 3.000 kr i [apr, okt] - årligt
│   └── 1.500 kr i [jun, jul, aug, sep] - årligt
```

**Eksempel - Dagligvarer fra flere beholdere:**

```
Budgetpost: "Dagligvarer" (Udgift)
├── Beholdere: [Lønkonto, Mastercard]
├── Type: Loft
├── Beløbsmønstre:
│   └── 4.000 kr per måned (kan betales fra enhver af beholderne)
```

#### Gentagelsesmønstre

Beløbsmønstre konfigureres via to akser: **mønstertype** og **gentagelse**.

**Akse 1 - Mønstertype:**
- **Dato-baseret**: Beløbet forekommer på en specifik dato (f.eks. d. 1. i måneden)
- **Periode-baseret**: Beløbet dækker en hel måned/periode (ingen specifik dato)

**Akse 2 - Gentagelse:**
- **Gentages ikke**: Beløbet forekommer én gang
- **Gentages**: Beløbet gentages med en defineret frekvens

**Dato-baseret, gentages ikke (once):**

`start_date` ER forekomstdatoen. Gentagelseskonfigurationen indeholder kun `{ type: 'once' }`. `end_date` skal være null.

**Dato-baseret, gentages:**

For transaktioner der gentages på specifikke datoer.

| Frekvens           | Konfiguration                                         | Eksempel              |
| ------------------ | ----------------------------------------------------- | --------------------- |
| Daglig             | Hver [N] dag fra startdato                            | Hver dag              |
| Ugentlig           | Hver [N] uge på [ugedag]                              | Hver fredag           |
| Månedlig (fast)    | Hver [N] måned på dag [1-31]                          | D. 1. hver måned      |
| Månedlig (relativ) | Hver [N] måned på [1./2./3./4./sidste] [ugedag]       | 2. tirsdag            |
| Månedlig (bankdag) | Hver [N] måned: [1-10]. bankdag fra start/slut         | 3. bankdag            |
| Årlig              | Hvert [N] år i [måned] på dag [1-31] eller relativ    | 15. juni hvert år     |
| Årlig (bankdag)    | Hvert [N] år i [måned]: [1-10]. bankdag fra start/slut | 2. bankdag i marts    |

**Option – Bankdagsjustering:** Gælder ikke for bankdag-typer (dato ER en bankdag). For øvrige typer, hvis beregnet dato ikke er en bankdag (weekend eller helligdag):
- **Ingen**: Behold dato som den er (standard)
- **Næste bankdag**: Ryk til næste bankdag (fremad).
- **Forrige bankdag**: Ryk til forrige bankdag (bagud).

**Option – Hold inden for måneden** (`bank_day_keep_in_month`, default: true): Vises kun når bankdagsjustering er aktiv. Når aktiveret: hvis justeret dato ville falde i en anden måned, justeres i modsat retning i stedet (f.eks. "næste" → "forrige"). Når deaktiveret: justeret dato må gerne krydse månedsskiftet. Eksempler:
- D. 31. jan (lørdag), næste bankdag = 2. feb: med "hold i måned" → 30. jan (fredag); uden → 2. feb (mandag).
- PBS d. 1. (søndag), næste bankdag = 2.: altid OK (samme måned, flaget er irrelevant).

Bankdage beregnes via en landespecifik helligdagskalender (aktuelt: Danmark). Danske helligdage beregnes algoritmisk: Nytårsdag, Skærtorsdag, Langfredag, Påskedag, 2. Påskedag, Kristi Himmelfartsdag, Pinsedag, 2. Pinsedag, Grundlovsdag, Juledag, 2. Juledag.

**Periode-baseret, gentages ikke (period_once):**

`start_date` (år + måned) bestemmer hvilken periode forekomsten gælder for. Gentagelseskonfigurationen indeholder kun `{ type: 'period_once' }`. `end_date` skal være null.

**Periode-baseret, gentages (period_monthly / period_yearly):**

For budgetter der gælder for perioder/måneder.

| Frekvens          | Type             | Konfiguration                          | Eksempel                    |
| ----------------- | ---------------- | -------------------------------------- | --------------------------- |
| Månedlig          | `period_monthly` | Hver [N] måned fra startperiode        | Hver måned, hvert kvartal   |
| Årlig gentagelse  | `period_yearly`  | Hvert [N] år i måneder [jan, feb, ...] | Mar, jun, sep, dec hvert år |

**Eksempler på gentagelsesmønstre:**

- "Løn: Sidste hverdag i måneden" → Dato-baseret, gentages, månedlig relativ, bankdagsjustering: ingen
- "Møde: 2. tirsdag i måneden" → Dato-baseret, gentages, månedlig relativ (second, tirsdag)
- "Husleje: D. 1. hver måned (eller næste bankdag)" → Dato-baseret, gentages, månedlig fast, bankdagsjustering: næste
- "Børneopsparing: Hver fredag" → Dato-baseret, gentages, ugentlig
- "Madbudget: Alle måneder" → Periode-baseret, gentages, månedlig (interval=1)
- "Forsikring: Kvartalsvis" → Periode-baseret, gentages, månedlig (interval=3)
- "El-regning (sommer): Jun-Sep" → Periode-baseret, gentages, årlig i [jun, jul, aug, sep]
- "TV-køb marts 2026" → Dato-baseret, gentages ikke, start_date = 2026-03-15
- "Indskud januar 2026" → Periode-baseret, gentages ikke, start_date = 2026-01-01
- "Løn: 3. bankdag i måneden" → Dato-baseret, gentages, månedlig bankdag (bank_day_number=3, fra start)
- "Regning: 2. bankdag fra slut i marts" → Dato-baseret, gentages, årlig bankdag (bank_day_number=2, fra slut, måned=3)

#### Arkiveret budgetpost (periode-snapshot)

Ved periode-afslutning oprettes en **arkiveret budgetpost** som snapshot af hvad der var forventet i den periode. Arkiverede budgetposter lever i en **separat tabel** (`archived_budget_posts`).

| Felt              | Beskrivelse                                     |
| ----------------- | ----------------------------------------------- |
| period_year       | Periodens år (påkrævet)                         |
| period_month      | Periodens måned 1-12 (påkrævet)                |
| retning           | Snapshot af retning (indtægt/udgift/overførsel)  |
| category_path     | Snapshot af kategori-sti (TEXT[], selvstændigt - ingen FK) |
| display_order     | Snapshot af sortering (INTEGER[])               |
| budget_post_id    | Reference til den aktive budgetpost (nullable - kan være slettet) |

**UNIQUE constraint:** `(budget_id, direction, category_path, period_year, period_month)` WHERE `category_path IS NOT NULL` - sikrer at der kun kan eksistere én arkiveret budgetpost per kategori-sti per periode.

**Selvstændig snapshot:** category_path og display_order kopieres fra den aktive budgetpost ved arkivering. Ingen FK til live data. Sletning eller omdøbning af den aktive post påvirker ikke historiske snapshots.

#### Beløbsforekomster (amount occurrences)

Arkiverede budgetposter har **beløbsforekomster** i stedet for beløbsmønstre. Forekomster er konkrete, beregnede beløb for den specifikke periode - genereret ved at ekspandere de aktive beløbsmønstre på arkiveringstidspunktet.

| Felt   | Beskrivelse                                      |
| ------ | ------------------------------------------------ |
| dato   | Forventet dato (null for periodeomfattende beløb) |
| beløb  | Forventet beløb i øre                            |

Beløbsforekomster lever i en **separat tabel** (`amount_occurrences`), tilknyttet arkiverede budgetposter.

**Transaktionsbinding:** Transaktioner i afsluttede perioder bindes til beløbsforekomster (ikke beløbsmønstre). Dette gør det muligt at sammenligne forventet vs. faktisk per forekomst.

**Eksempel:**

```
Aktiv budgetpost: "Husleje" (Udgift)
├── Beløbsmønster: 8.000 kr, d. 1 hver måned, beholdere: [Lønkonto]
│
├── Ved arkivering af januar 2026:
│   └── Arkiveret budgetpost (jan 2026):
│       └── Beløbsforekomst: dato=2026-01-01, beløb=800000
│           └── Transaktion: -8.000 kr "Boligforening" ✓ matched
│
├── Ved arkivering af februar 2026:
│   └── Arkiveret budgetpost (feb 2026):
│       └── Beløbsforekomst: dato=2026-02-02, beløb=800000 (d. 1 var søndag → mandag)
│           └── Transaktion: -8.000 kr "Boligforening" ✓ matched
```

#### Budgetpost-livscyklus

Aktive budgetposter har **ingen periode** - de beskriver den løbende plan. Ved periode-afslutning:

1. **Beløbsmønstre ekspanderes** for den afsluttede periode
2. **Arkiveret budgetpost oprettes** med de beregnede beløbsforekomster
3. **Aktiv budgetpost forbliver uændret** - den fortsætter med at generere forventninger for kommende perioder
4. Hvis ingen beløbsmønstre har aktive gentagelser (alle er udløbet), kan den aktive budgetpost markeres som inaktiv

> **Åbent spørgsmål:** Den præcise arkiveringsproces (timing, håndtering af transaktioner tilføjet efter periodeafslutning, akkumulering af loft-poster) er endnu ikke fuldt afklaret.

**Forventede forekomster:**

- Beløbsmønstre genererer konkrete forventede forekomster per periode
- F.eks. "100 kr hver mandag" → 4-5 forventede forekomster i en måned
- Matching sker på antal forekomster, ikke bare totalt beløb

**Afvigelser:**

- Forkert antal eller beløb markeres som afvigelse
- Bruger kan "kvittere" afvigelse (har set problemet)
- Kvittering fjerner IKKE afvigelsen fra grafer/rapporter - den vises stadig
- Afvigelser kan kvitteres i både aktive og arkiverede perioder

**Beløbsmønstre over tid:**

Beløbsmønstre kan overlappe (sæsonvariation) og være sekventielle (permanente ændringer som lønstigning). Se eksempler i beløbsmønster-afsnittet ovenfor.

**Saldo-effekt ved overførsler:**

Overførsler er altid netto-nul for budgettets samlede formue, men påvirker "til rådighed" (sum af pengekasser):

| Fra → Til                     | "Til rådighed" saldo |
| ----------------------------- | -------------------- |
| Pengekasse → Pengekasse       | Uændret              |
| Pengekasse → Sparegris        | Falder               |
| Pengekasse → Gæld             | Falder (afdrag)      |
| Sparegris → Pengekasse        | Stiger               |
| Gæld → Pengekasse             | Stiger (udtræk, kun hvis tilladt) |
| Sparegris → Sparegris         | Uændret              |
| Sparegris → Gæld              | Uændret              |

**Beholdere med/uden banktilknytning:**

- Med banktilknytning: Transaktioner importeres (fremtidig), skal matche
- Uden banktilknytning: Transaktioner oprettes manuelt eller auto-genereres som modpart

### 4. Budget

Budget er den centrale enhed i Tiøren - en samling af økonomi-data der kan deles mellem brugere.

**Eksempler:**

- "Min private økonomi" (kun mig)
- "Fælles husholdning" (delt med partner)
- "Sommerhus" (delt med familie)

| Felt            | Beskrivelse                                   |
| --------------- | --------------------------------------------- |
| navn            | "Daglig økonomi", "Husholdning"               |
| valuta          | Budgettets valuta (default: DKK). Én valuta pr. budget. |
| periode         | Kalendermåned (den aktuelle visningsperiode)  |
| beholdere       | Liste af beholdere (pengekasser, sparegrise, gæld) |
| advarselsgrænse | Advar når saldo under X                       |

**Indeholder:**

- Beholdere (pengekasser, sparegrise, gældsbyrder)
- Budgetposter (med hierarkisk category_path)
- Regler for auto-kategorisering og matching
- Transaktioner (via beholdere)

**UI-tekst:** "Opret nyt budget", "Mine budgetter", etc.

**Isolation:**

Budgetter er fuldstændig isolerede fra hinanden. De deler ikke budgetposter, regler eller transaktioner.

**Budget og Beholdere:**

Et budget indeholder beholdere af tre typer. "Til rådighed" beregnes kun fra pengekasser:

- **Til rådighed:** Sum af alle pengekassers saldo (den disponible saldo)
- **Per-beholder saldo:** Individuel saldo for hver beholder

```
Budget "Daglig økonomi" (valuta: DKK)
├── Pengekasser (til rådighed):
│     ├── Lønkonto             10.000 kr
│     ├── Mastercard             -500 kr
│     └── Kontanter               200 kr
│     ─────────────────────────────────
│     Til rådighed:             9.700 kr
├── Sparegrise:
│     └── Ferieopsparing       12.000 kr
├── Gældsbyrder:
│     ├── Billån              -150.000 kr
│     └── Kassekredit          -10.000 kr
```

**Planlagte transaktioner i et budget:**

Beholderbindinger defineres på to niveauer: budgetpost (beholder-pulje) og beløbsmønster (valgfrit subset). Se "Beholderbinding (to-niveau model)" for detaljer.

| Beholder-binding           | Eksempel                                                        |
| -------------------------- | --------------------------------------------------------------- |
| Beholder-specifik mønster  | Husleje: beholdere=[Lønkonto], mønster arver puljen             |
| Fleksibelt mønster         | Mad: beholdere=[Lønkonto, Mastercard], mønster arver puljen     |

**Budgetposter og hierarki:**

Budgetposter organiseres hierarkisk via `category_path`. Retningen (indtægt/udgift/overførsel) definerer rod-niveauet. Overførsler har ingen category_path.

**Eksempel:**

```
Budget "Daglig økonomi"
├── Indtægt (direction=income)
│     └── Løn (category_path: ["Løn"], beholdere: [Lønkonto], mønster: +25.000)
├── Udgift (direction=expense)
│     ├── Husleje (category_path: ["Bolig", "Husleje"], beholdere: [Lønkonto], mønster: -8.000)
│     ├── Mad (category_path: ["Mad"], beholdere: [Lønkonto, Mastercard], mønster: -4.000)
│     └──  (Renter på Billån beregnes automatisk af gældsbyrdens rente-indstilling)
├── Overførsler (direction=transfer, category_path=null)
│     ├── Lønkonto → Ferieopsparing (+2.000 kr/md)
│     └── Lønkonto → Billån (+3.500 kr/md, afdrag)
```

**Forecasting:**

Budgettet besvarer:

1. "Har jeg råd?" → Samlet saldo
2. "Har jeg nok på lønkontoen til regningerne?" → Per-beholder saldo

#### Deling og roller (post-MVP)

> **Bemærk:** Delte budgetter er en post-MVP feature (medium prioritet). Nedenstående beskriver arkitekturen der implementeres når featuren tilføjes.

Et budget kan deles med andre brugere. Der er to roller:

| Handling                       | Ejer | Medlem |
| ------------------------------ | ---- | ------ |
| Se alt                         | Ja   | Ja     |
| Oprette/redigere transaktioner | Ja   | Ja     |
| Oprette/redigere budgetposter  | Ja   | Ja     |
| Oprette/redigere regler        | Ja   | Ja     |
| Tilføje/fjerne beholdere       | Ja   | Ja     |
| Invitere nye medlemmer         | Ja   | Nej    |
| Fjerne medlemmer               | Ja   | Nej    |
| Slette budgettet               | Ja   | Nej    |
| Forlade budgettet              | -    | Ja     |

- Medlemmer har fuld redigerings-adgang (høj tillid, typisk familie/partner)
- Ejer beskytter mod utilsigtet sletning og medlemshåndtering
- Post-MVP: "Læseadgang"-rolle kan tilføjes hvis behov opstår

**Invitation:**

- Ejer indtaster email → system sender invitation med unikt link
- Token-levetid: 7 dage (kan gen-sendes)
- Modtager klikker link → login/opret konto → tilføjes som Medlem
- Afventende invitationer vises i budget-indstillinger, kan annulleres

**Forlade budget:**

- Medlem kan altid forlade
- Ejer kan kun forlade hvis der er mindst én anden bruger (som bliver ny ejer)
- Sidste bruger kan ikke forlade - skal slette budgettet
- Alle data (transaktioner, beholdere, etc.) forbliver i budgettet

**Beholdere og deling:**

- Beholder oprettes i ét specifikt budget og lever der (`budget_id` required)
- Inden for ét budget: Duplikat-check - samme beholder (navn) kan kun oprettes én gang
- På tværs af budgetter: Ingen tjek - samme bankkonto kan tilknyttes beholdere i forskellige budgetter
- Delte budgetter løser use-casen hvor flere personer skal se samme beholdere

#### Akkumulering

Udgifts-budgetposter kan valgfrit akkumulere ubrugte beløb til næste periode:

- **Nulstil** (default): Ubrugte midler "forsvinder" ved ny periode. Bruges til de fleste udgifter som husleje, mad, underholdning.
- **Akkumuler**: Ubrugte/overforbrugte midler overføres til næste periode. Fungerer som intern øremærkning. Bruges til bilreparation, vedligeholdelse, buffer.

```
Eksempel på akkumulering:

Bilreparation (udgift, akkumuler, 1.000 kr/md)
├── Januar: budget 1.000 kr, brugt 0 kr → saldo: 1.000 kr
├── Februar: budget 2.000 kr, brugt 0 kr → saldo: 2.000 kr
├── Marts: budget 3.000 kr, brugt 2.500 kr → saldo: 500 kr
├── April: budget 1.500 kr, brugt 0 kr → saldo: 1.500 kr
└── ...
```

**Bemærk:** Akkumulering ligner virtuel opsparing - pengene "øremærkes" men bliver i budgettets pengekasser.

#### Budget-definition vs Periode-instans

Et budget har to lag:

**1. Budget-definition (skabelonen)**

Den løbende plan der beskriver hvordan økonomien ser ud:

```
Budget "Daglig økonomi" (definition)
├── Løn: +25.000 kr/md
├── Husleje: -8.000 kr/md
├── Mad: -3.000 kr/md
└── Gå i byen: -1.000 kr/md
```

- Kan ændres fremadrettet (f.eks. ved lønstigning)
- Ændringer gælder fra valgt dato og frem
- Afsluttede perioder påvirkes **ikke** af ændringer

**2. Periode-instans (den konkrete måned)**

Den faktiske status for en given periode:

```
Januar 2026 (instans)
├── Mad: Budget 3.000 kr | Brugt 3.500 kr | Rest -500 kr
├── Gå i byen: Budget 1.000 kr | Brugt 0 kr | Rest 1.000 kr
└── Status: 500 kr over budget
```

- Viser faktisk vs. planlagt
- Kan have omfordelinger (se nedenfor)
- Låses når perioden afsluttes

**Implementation:** Periode-instanser konstrueres fra:
- **Afsluttede perioder:** Arkiverede budgetposter (separat tabel `archived_budget_posts`) med beløbsforekomster
- **Aktiv periode:** Aktive budgetposter + deres beløbsmønstres ekspanderede forekomster for indeværende måned

#### Budget-omfordelinger

Når virkeligheden ikke matcher planen, kan man omfordele midler uden at ændre selve budget-definitionen:

**Scenarie:** Mad-budgettet er brugt op, men "Gå i byen" har ubrugte midler.

**Mulighed 1: Lad posten gå i negativ**

```
Mad: Budget 3.000 kr | Brugt 3.500 kr | Rest -500 kr
```

Simpelt og ærligt - viser præcist hvad der skete.

**Mulighed 2: Omfordel fra anden budgetpost (samme periode)**

```
Omfordeling i januar:
  Gå i byen → Mad: 500 kr

Resultat:
  Mad:        Budget 3.500 kr | Brugt 3.500 kr | Rest 0 kr
  Gå i byen:  Budget 500 kr   | Brugt 0 kr     | Rest 500 kr
```

Afspejler aktiv prioritering - man vælger at bruge pengene anderledes.

**Mulighed 3: Omfordel fra fremtidig periode**

```
Lån fra februar til januar:
  Mad (feb) → Mad (jan): 500 kr

Resultat:
  Mad (jan): Budget 3.500 kr | Brugt 3.500 kr | Rest 0 kr
  Mad (feb): Budget 2.500 kr | (starter med mindre)
```

Spreder konsekvensen - men skubber problemet.

**Budget-omfordeling (model):**

| Felt           | Beskrivelse                                      |
| -------------- | ------------------------------------------------ |
| fra_budgetpost | Hvilken budgetpost pengene kommer fra            |
| fra_periode    | År og måned (year, month) for kildeperioden      |
| til_budgetpost | Hvilken budgetpost pengene går til               |
| til_periode    | År og måned (year, month) for målperioden        |
| beløb          | Hvor meget der omfordeles                        |
| note           | Valgfri forklaring                               |

**Vigtigt:** Omfordelinger ændrer det budgetterede beløb for de påvirkede budgetposter i den specifikke periode. Transaktioner forbliver matchede - kun forventningen justeres. Brugeren har fuldt ansvar - systemet forhindrer ikke "dumme" omfordelinger. Budgettet er et værktøj til overblik, ikke en tvangstrøje.

#### Periode-håndtering og bekræftelses-model

Tiøren bruger en **bekræftelses-model** i stedet for eksplicit periode-låsning:

**Periode-skift trigger:**

- Primært: Automatisk ved midnat d. 1. i ny måned (scheduler/cron)
- Fallback: Ved første brugeradgang hvis automatisk skift ikke skete
- Under skift: Systemet er "låst" - brugeren ser "Vent venligst..." besked

**Ved skift:**

- Hver aktiv budgetposts beløbsmønstre ekspanderes for den afsluttede periode
- Arkiveret budgetpost oprettes i `archived_budget_posts` med de beregnede beløbsforekomster
- Den aktive budgetpost forbliver uændret - den fortsætter med at generere forventninger
- Transaktionsbindinger fra beløbsmønstre flyttes til de tilsvarende beløbsforekomster
- Teknisk lås på budget under periode-skift for at undgå race conditions

**Ændringer i afsluttede perioder:**

- Intet brugersynligt "låse/oplåse"-koncept
- Alle ændringer til afsluttede perioder (transaktioner) samles som "afventende kladde"
- Gælder både manuelle ændringer og import af gamle transaktioner
- Regel-matching foreslås men anvendes først ved bekræftelse

**Bekræftelses-flow:**

- Brugeren samler ændringer (kan være mange)
- Før godkendelse vises konsekvenser:
  - Påvirkning af akkumulerende budgetposter
  - Ændrede afvigelser
  - Effekt på nutidens saldi
- Brugeren bekræfter samlet, ændringer træder i kraft

```
         ◄─── ARKIVEREDE SNAPSHOTS ──►  ◄── AKTIV BUDGETPOST (ingen periode) ──►
         dec         jan         feb    mar    apr    ...
Snapshot: [snapshot]  [snapshot]   │
                                  │
Aktiv:    ──────────────────────[beløbsmønstre genererer forekomster]──────────►
                                  ↑
                           Lønstigning fra 1. feb (nyt beløbsmønster)

Ændringer til arkiverede perioder → samles i kladde → bekræftes samlet
```

#### Budget-overblik baseret på beholdertype

Budgettet giver overblik over alle beholdere grupperet efter type:

| Beholdertype     | Vises som              | I "til rådighed"  |
| ---------------- | ---------------------- | ------------------ |
| **Pengekasse**   | Disponibel saldo       | Ja                 |
| **Sparegris**    | Opsparingsbeløb        | Nej                |
| **Gæld**         | Restgæld (negativ)     | Nej                |

Budgetposter grupperes efter retning (indtægt, udgift, overførsel) - IKKE efter beholdertype. Indtægter og udgifter kan involvere alle beholdertyper.

**Overførsler mellem beholdere:**

Overførsler opretter **bundne transaktioner** på begge beholdere:

| Overførsel                                | Resultat ved udførelse                             |
| ----------------------------------------- | -------------------------------------------------- |
| Lønkonto → Ferieopsparing (opsparing)     | -2.000 kr på Lønkonto, +2.000 kr på Ferieopsparing |
| Ferieopsparing → Lønkonto (udtræk)        | -5.000 kr på Ferieopsparing, +5.000 kr på Lønkonto |
| Lønkonto → Billån (afdrag)               | -3.500 kr på Lønkonto, +3.500 kr på Billån         |

**Princip:**

- **"Til rådighed"** = sum af pengekassers saldo (disponibelt beløb)
- Overførsler er netto-nul for budgettets samlede formue
- Udgifter og indtægter kan forekomme på alle beholdertyper
- Renter på gæld beregnes automatisk af systemet (ikke budgetposter)

**Sammenligning af beholdertyper:**

| Aspekt       | Pengekasse   | Sparegris  | Gæld                       |
| ------------ | ------------ | ---------- | -------------------------- |
| Typisk saldo | Positiv      | Positiv    | Negativ (gæld)             |
| Mål          | Balance      | Øge saldo  | Reducere gæld              |
| Renter       | N/A          | N/A*       | Systemberegnet (øger gæld) |

*Indlånsrente på sparegrise kan tilføjes som fremtidig feature.

**Gæld uden banktilknytning:**

For gæld hvor man ikke har adgang til selve gælden (f.eks. realkredit), oprettes en gældsbyrde uden banktilknytning. Transaktioner registreres manuelt eller estimeres baseret på renteindstillinger og afdragsplan.

#### Øremærkning (virtuel opsparing)

Ønskes øremærkning af penge i en pengekasse (uden separat sparegris), bruges en **budgetpost med akkumulering**:

```
Bilreparation (udgift, akkumuler, 1.000 kr/md, category_path: ["Bilreparation"])
```

Pengene akkumulerer i pengekasserne, men er "øremærket" i budgettet. Se "Akkumulering" for detaljer.

### 5. Kategori-sti (category_path)

Budgetposter organiseres hierarkisk via `category_path TEXT[]` direkte på budgetposten. Der er ingen separat kategori-tabel - hierarkiet er en afledt egenskab af budgetposternes data.

**Princip:** `category_path` indeholder den fulde sti inklusiv budgetpostens navn som sidste element. Grupper opstår automatisk når flere poster deler et præfiks.

**Eksempel:**

```
category_path: ["Bolig", "Husleje"]  →  Navn: "Husleje", Gruppe: "Bolig"
category_path: ["Bolig", "El"]       →  Navn: "El", Gruppe: "Bolig"
category_path: ["Transport"]         →  Navn: "Transport", Ingen gruppe
category_path: ["Bolig"]             →  Gruppe-post med egen finansiel data
```

**Sortering:** `display_order INTEGER[]` matcher `category_path` niveauer. PostgreSQL sorterer arrays leksikografisk: `[0] < [0,0] < [0,1] < [1]`. Gruppe-headere (kortere arrays) placeres naturligt før deres børn.

**Rødder:** Indtægt/Udgift er IKKE eksplicitte rødder i `category_path`. De er implicit fra `direction`-feltet. En udgifts-budgetpost med `category_path: ["Bolig", "Husleje"]` vises under "Udgift > Bolig > Husleje".

**Overførsler:** Har `category_path = null`. Identitet er "fra-beholder → til-beholder".

**Gruppeknuder med egne budgetposter:**

En gruppe kan have sin egen budgetpost. F.eks. "Bolig" som gruppe OG som budgetpost med loft:

```
{category_path: ["Bolig"],            display_order: [0]}      -- gruppen selv har et budget
{category_path: ["Bolig", "Husleje"], display_order: [0, 0]}   -- barn under gruppen
{category_path: ["Bolig", "El"],      display_order: [0, 1]}   -- barn under gruppen
```

Gruppens budgetpost er uafhængig af børnenes.

**Budgetpost-modes:**

- **Planlagt:** Har budgetteret beløb, vises altid (husleje, løn, mad)
- **Ad-hoc:** 0 kr budgetteret, vises kun når der er transaktioner (tandlæge, reparationer)

Brugeren kan oprette budgetposter on-demand ved kategorisering af transaktioner.

**Ingen default-kategorier ved budget-oprettelse:**

Nye budgetter starter tomme. Brugeren opbygger selv sit budget med budgetposter. Et eksempel på en typisk dansk struktur:

```
Budget "Daglig økonomi"
│
├── INDTÆGT (direction=income)
│     ├── Løn                         ← category_path: ["Løn"], fast, beholdere: [Lønkonto]
│     ├── Feriepenge                  ← category_path: ["Feriepenge"], ad-hoc, beholdere: [Lønkonto]
│     └── Andet                       ← category_path: ["Andet"], ad-hoc, beholdere: [Lønkonto]
│
├── UDGIFT (direction=expense)
│     ├── Bolig                       ← category_path: ["Bolig"], loft 15.000
│     │     ├── Husleje              ← category_path: ["Bolig", "Husleje"], fast 8.000, beholdere: [Lønkonto]
│     │     ├── El                   ← category_path: ["Bolig", "El"], loft 1.500, beholdere: [Lønkonto]
│     │     └── Varme               ← category_path: ["Bolig", "Varme"], loft 2.000, beholdere: [Lønkonto]
│     ├── Transport                  ← category_path: ["Transport"], loft 1.200, beholdere: [Lønkonto]
│     ├── Mad & drikke               ← category_path: ["Mad & drikke"], loft 4.000, beholdere: [Lønkonto, Mastercard]
│     └──  (Renter på Billån beregnes automatisk af gældsbyrdens indstillinger)
│
├── OVERFØRSLER (direction=transfer, category_path=null)
│     ├── Lønkonto → Budgetkonto     ← overførsel, 5.000 kr/md
│     ├── Lønkonto → Ferieopsparing  ← overførsel, 2.000 kr/md
│     └── Lønkonto → Billån          ← overførsel, 3.500 kr/md (afdrag)
```

**Tags:** Tiøren understøtter ikke tags - category_path og budgetposter dækker organiseringsbehovet.

**Kategorisering af transaktioner:**

En transaktion kategoriseres ved at tildeles én eller flere budgetposter. Budgetposten identificeres via sin `category_path` (sidste element er budgetpostens navn).

**Kategori-input i UI:**

Tekstfelt med ` > ` separator og autocomplete fra eksisterende stier:
- Brugeren skriver f.eks. "Bolig > Husleje" → parses til `["Bolig", "Husleje"]`
- Autocomplete foreslår eksisterende grupper og stier mens man skriver
- Hint-tekst: "Brug > for undergrupper, f.eks. Bolig > Husleje"
- Overførsler: kategori-feltet er skjult

### 6. Regel (Rule)

Regler håndterer automatisk matching og fordeling af transaktioner til budgetposter. Regler tilhører et Budget og deles ikke mellem budgetter.

**Princip:** Regler henviser til budgetposter (ikke kategorier direkte). Når en transaktion matcher en regel, tildeles den til de relevante budgetposter.

| Felt         | Beskrivelse                                    |
| ------------ | ---------------------------------------------- |
| navn         | "Husleje-match", "Føtex-split"                 |
| betingelser  | Kriterier der skal matche (se nedenfor)        |
| budgetposter | Hvilke budgetposter transaktionen fordeles til |
| fordeling    | Hvordan beløbet deles (procent eller fast)     |
| tilstand     | auto, afventer_bekræftelse, afventer_bilag     |

**Betingelser (conditions):**

- Beskrivelse indeholder "NETS \*FØTEX"
- Beløb er mellem -1000 og -100
- Beholder er "Lønkonto"
- Dato er mellem d. 1-5 i måneden

**Regel-tilstande:**

| Tilstand             | Beskrivelse                               | Eksempel                                      |
| -------------------- | ----------------------------------------- | --------------------------------------------- |
| auto                 | Matcher og tildeler automatisk            | Husleje, Netflix                              |
| afventer_bekræftelse | Foreslår, men bruger skal godkende        | Større køb, usikre matches                    |
| afventer_bilag       | Kræver kvittering/opgørelse før tildeling | Samlet forsikring, udgifter der skal splittes |

**Eksempel 1: Simpel regel (auto)**

```
Regel: "Husleje-match"
├── Tilstand: auto
├── Betingelser:
│   ├── Beskrivelse indeholder "Boligforening"
│   ├── Beløb er mellem -8500 og -7500
│   └── Dato er mellem d. 1-3 i måneden
└── Tildeling:
    └── 100% → Budgetpost "Husleje"
```

**Eksempel 2: Split-regel (auto)**

```
Regel: "Føtex-split"
├── Tilstand: auto
├── Betingelser:
│   └── Beskrivelse indeholder "FØTEX"
└── Tildeling:
    ├── 80% → Budgetpost "Mad-budget"
    └── 20% → Budgetpost "Husholdning"
```

**Eksempel 3: Regel der afventer bilag**

```
Regel: "Tryg-forsikring"
├── Tilstand: afventer_bilag
├── Betingelser:
│   └── Beskrivelse indeholder "Tryg"
└── Ved bilag modtaget:
    LLM parser opgørelse og foreslår:
    ├── 800 kr → Budgetpost "Indboforsikring"
    ├── 1.200 kr → Budgetpost "Bilforsikring"
    └── 500 kr → Budgetpost "Ulykkesforsikring"

    Bruger bekræfter eller justerer fordeling.
```

**Relationer:**

- Tilhører ét Budget
- Henviser til én eller flere Budgetposter
- Matcher Transaktioner baseret på betingelser

**Regel-prioritet og matching:**

- Regler har en rækkefølge/prioritet (sorteret liste)
- Første matchende regel anvendes - øvrige ignoreres
- Én regel definerer hele fordelingen (kan indeholde split til flere budgetposter)
- Hvis reglen ikke fordeler 100%, ender resten som ukategoriseret
- Brugeren kan omsortere regler for at ændre prioritet

**Matching-strategi:**

- Matching sker via regel ELLER manuelt (ingen implicit matching baseret på dato/beløb alene)
- Alle betingelser i en regel skal passe for at reglen matcher (AND-logik)
- Tolerance og betingelser defineres per regel, ikke globalt

**Betingelsestyper:**

- Dato inden for X dage fra beløbsmønsterets forventede dato
- Beløb matcher præcist (beløbsmønsterets beløb)
- Beløb inden for ± X af beløbsmønsterets beløb
- Tekst indeholder/matcher mønster
- Beholder er én af (arvet fra budgetpost eller specificeret)

**Matching-flow:**

1. Transaktion ankommer på en beholder
2. Find beløbsmønstre der har beholderen i deres `container_ids` (for indtægt/udgift), eller budgetposter med beholderen som `from_container_id`/`to_container_id` (for overførsler)
3. Find regler der er tilknyttet de fundne budgetposter
4. Kør reglerne i prioritetsrækkefølge
5. Første matchende regel anvendes
6. Transaktion bindes til det matchende beløbsmønster (eller beløbsforekomst for afsluttede perioder)

### 7. Validering (saldo-tjek)

Tiøren validerer på to niveauer for at sikre der er penge nok til alle forventede udgifter.

**Niveau 1: Budgetniveau (samlet)**

Tjekker om budgettet som helhed går op:

- Samlet indtægt vs. samlet udgift
- Er der balance eller overskud?

```
Budget "Daglig økonomi" - BUDGETNIVEAU
├── Samlet indtægt: +25.000 kr
├── Samlet udgift:  -23.000 kr
└── Balance:         +2.000 kr ✓
```

**Niveau 2: Beholderniveau (per beholder)**

Tjekker om hver beholder har nok til sine beholder-specifikke budgetposter:

- Respekterer beholderens regler (overtræksgrænse, kreditramme)
- Reserverer beløb til beholder-bundne poster
- For gæld: inkluderer systemberegnede renter i fremskrivningen

```
Lønkonto (pengekasse) - BEHOLDERNIVEAU
├── Saldo: 10.000 kr
├── Beholder-specifikke budgetposter:
│   ├── Husleje: -8.000 kr (kun Lønkonto)
│   ├── El: -500 kr (kun Lønkonto)
│   └── Løn: +25.000 kr (kun Lønkonto)
├── Forventet resultat: +16.500 kr ✓
└── Beholder-regel: Ingen overtræk ✓
```

**Fleksible budgetposter (flere beholdere):**

Når en budgetpost kan betales fra flere beholdere, gælder:

1. **Samlet** skal der være nok på tværs af de tilknyttede beholdere
2. **Per beholder** må ingen fordeling bryde beholderens regler

```
Budgetpost: "Dagligvarer" -4.000 kr
├── Beholdere: Lønkonto, Mastercard
│
├── Tilgængelig saldo:
│   ├── Lønkonto:  5.000 kr (ingen overtræk)
│   ├── Mastercard: -200 kr (overtræk -20.000, dvs. 19.800 til rådighed)
│   ─────────────────────────────────────────
│   Samlet til rådighed: 24.800 kr ✓
│
└── Validering:
    ├── Samlet nok: 24.800 kr ≥ 4.000 kr ✓
    └── Enhver fordeling må ikke bryde beholder-regler
        (f.eks. kan Lønkonto max bidrage med 5.000 kr)
```

**Opsummering af validering:**

| Niveau               | Tjekker                        | Eksempel                             |
| -------------------- | ------------------------------ | ------------------------------------ |
| Budget               | Går det hele op?               | Indtægt ≥ Udgift                     |
| Beholder (specifik)  | Nok til bundne poster?         | Husleje kan betales fra Lønkonto     |
| Beholder (fleksibel) | Samlet nok + regler overholdt? | Dagligvarer kan dækkes på tværs      |
| Gæld                 | Renter + afdrag balancerer?    | Billån har nok afdrag budgetteret   |

---

## Nøglerelationer

| Relation                              | Kardinalitet | Beskrivelse                                                |
| ------------------------------------- | ------------ | ---------------------------------------------------------- |
| Bruger → Budget                       | N:M          | En bruger kan have flere budgetter, og budgetter kan deles |
| Budget → Beholder                     | 1:N          | Et budget har flere beholdere (pengekasser, sparegrise, gæld) |
| Beholder → Budget                     | N:1          | En beholder tilhører ét budget                             |
| Budget → Regel                        | 1:N          | Et budget har sine egne regler                             |
| Budget → Aktiv budgetpost             | 1:N          | Et budget har flere aktive budgetposter (med category_path) |
| Budget → Arkiveret budgetpost         | 1:N          | Et budget har mange arkiverede budgetposter over tid       |
| **Aktiv budgetpost → Beløbsmønster**  | **1:N**      | **En budgetpost har et eller flere beløbsmønstre**         |
| **Arkiveret budgetpost → Beløbsforekomst** | **1:N** | **En arkiveret budgetpost har konkrete beløbsforekomster** |
| **Budgetpost → Beholder**             | **N:M**      | **En budgetpost har en beholder-pulje (alle typer)**       |
| **Beløbsmønster → Beholder**          | **N:M**      | **Et beløbsmønster kan indsnævre til subset af budgetpostens beholdere** |
| **Regel → Budgetpost**                | **N:M**      | **En regel kan fordele til flere budgetposter (split)**    |
| Beholder → Transaktion                | 1:N          | En beholder har flere transaktioner                        |
| **Transaktion → Beløbsmønster**       | **N:M**      | **En transaktion tildeles beløbsmønstre (aktiv periode)**  |
| **Transaktion → Beløbsforekomst**     | **N:M**      | **En transaktion tildeles beløbsforekomster (afsluttet)**  |
| Transaktion → Transaktion             | 1:1          | Intern overførsel: to bundne transaktioner                 |
| Budgetpost → Omfordeling              | 1:N          | En budgetpost kan have omfordelinger i sin periode         |

**Bemærk:** Budgetposter grupperes efter retning (indtægt, udgift, overførsel). "Til rådighed"-saldo beregnes kun fra pengekasser.

**Centrale relationer for transaktion-flow:**

```
Transaktion (virkelighed)
     ↓ sker på
   Beholder
     ↓ bruges af
Beløbsmønstre (forventning, med beholdere)
     ↑ tilhører
Aktive budgetposter (plan)
     ↑ henviser til
   Regler (matching)
```

---

## Hovedfunktioner

### 1. Transaktionsoversigt

- Se alle transaktioner (filtrér på beholder, budgetpost, dato)
- Kategorisér ukategoriserede
- Split en transaktion på flere budgetposter
- Match med planlagte transaktioner
- Vedhæft kvitteringer (billede/scan)

### 2. Forecast / Fremtidsudsigt

- Se forventet saldo X måneder frem
- Baseret på planlagte transaktioner
- **Samlet saldo:** "Har jeg råd til dette?"
- **Per-beholder saldo:** "Har Lønkonto nok til regningerne?"
- Markér når planlagt ≠ faktisk
- Advarsler ved forventet underskud (samlet eller per-beholder)

### 3. Budgetpost-analyse

- "Hvor meget bruger jeg på X per måned?"
- Grafer og trends over tid
- Sammenlign perioder
- Drill-down i category_path hierarkiet

### 4. Import

**Grundlæggende:**

- Manuel indtastning
- CSV-import fra bank (fleksibelt format)
- Duplikat-håndtering (hash-baseret)
- Auto-kategorisering via regler
- Arkitektur klar til fremtidige bank-integrationer

**Duplikat-detection:**

- `external_id` - bankens unikke reference (gemmes separat, kan være null)
- `import_hash` - hash af (container_id + dato + tidsstempel + beløb + beskrivelse)
- Tidsstempel inkluderes hvis tilgængeligt

**Duplikat-tjek ved import:**

1. Hvis `external_id` findes → tjek mod eksisterende
2. Uanset → tjek også mod `import_hash`
3. Potentielle duplikater vises til brugeren
4. Brugeren vælger: "Skip (duplikat)" eller "Importér (ny transaktion)"

**CSV-import flow:**

1. Bruger uploader CSV
2. System viser preview af første rækker
3. Bruger mapper kolonner (Dato, Beløb, Beskrivelse, Bank-reference, Tidsstempel, Saldo)
4. Mapping gemmes som "profil" til fremtidige imports

**Dato- og tal-format:**

- Auto-detect baseret på data
- Brugeren bekræfter/justerer i preview
- Gemmes i import-profilen
- Preview viser fortolkning så brugeren kan verificere
- Understøtter dansk (1.234,56) og engelsk (1,234.56) format

**Import-profiler:**

- Gemmes per beholder (f.eks. "Nordea CSV", "Danske Bank CSV")
- Kan genbruges ved fremtidige imports

### 6. Eksport

**Formater:**

- **CSV** - til analyse i regneark (Excel, Google Sheets)
- **JSON** - til backup og migration (bevarer struktur og relationer)

**Eksport-muligheder:**

- Transaktioner (filtrérbar på periode, beholder, budgetpost)
- Budgetposter
- Komplet budget-backup (JSON)

### 7. Kvitteringshåndtering (fremtidig)

- Upload/scan kvittering
- OCR + LLM til udtræk af linjer
- Foreslå split-kategorisering
- Gem kvittering på transaktionen

---

## Brugergrænsefladen

### Principper

- **Visuelt frem for tekst-tungt** - inspiration fra Spiir
- **Intuitiv oprettelse** af planlagte transaktioner
- **Mobil-venlig** (responsive)
- **Hurtig** - ingen unødvendig loading
- **Ingen emoji** - hvis ikoner behøves, bruges Lucide Icons (open source, ISC licens)
- **Ikoner som inline SVG** for nem CSS-styling og farvetilpasning

### Overordnet stil

**Inspiration:** Moderne finans-apps (Spiir, Lunar, N26) - rent, minimalistisk, data-drevet.

**Karakteristika:**

- Mørk/lys tema (brugervalg)
- Store, læsbare tal
- Visuel feedback via farver (grøn = positiv, rød = negativ)
- Kort og cards som primære containere
- Generøs whitespace

### Farvepalette (forslag)

#### Lys tema

| Funktion        | Farve        | Hex       |
| --------------- | ------------ | --------- |
| Baggrund        | Hvid/lysegrå | `#FAFAFA` |
| Primær tekst    | Mørkegrå     | `#1A1A1A` |
| Sekundær tekst  | Grå          | `#6B7280` |
| Accent (primær) | Blå          | `#3B82F6` |
| Positiv/indtægt | Grøn         | `#10B981` |
| Negativ/udgift  | Rød          | `#EF4444` |
| Advarsel        | Orange       | `#F59E0B` |
| Kort-baggrund   | Hvid         | `#FFFFFF` |
| Border          | Lysegrå      | `#E5E7EB` |

#### Mørk tema

Inverterede farver med dæmpede accenter. (Post-MVP feature)

#### CSS-tokenisering

Farver implementeres som CSS custom properties med semantiske navne:

```css
:root {
  /* Baggrunde */
  --bg-page: #fafafa;
  --bg-card: #ffffff;

  /* Tekst */
  --text-primary: #1a1a1a;
  --text-secondary: #6b7280;

  /* Semantiske farver */
  --accent: #3b82f6;
  --positive: #10b981;
  --negative: #ef4444;
  --warning: #f59e0b;

  /* Borders */
  --border: #e5e7eb;
}
```

Semantiske navne (`--positive`) bruges frem for farvenavne (`--green`) for nem tema-switching.

### Layout-struktur

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER                                                     │
│  ┌─────────────┐                    ┌──────┐ ┌──────┐      │
│  │ Tiøren logo │    [Budget-vælger]    │notif││profil│      │
│  └─────────────┘                    └──────┘ └──────┘      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  NAVIGATION (sidebar på desktop, bottom-bar på mobil)       │
│  ┌──────────────┐                                          │
│  │ * Overblik   │                                          │
│  │ * Pengekasser│                                          │
│  │ * Sparegrise │                                          │
│  │ * Gæld       │                                          │
│  │ * Budget     │  <- Budgetposter                         │
│  │ * Transakt.  │  <- Badge hvis ukategoriserede           │
│  │ * Forecast   │                                          │
│  │ * Indstill.  │                                          │
│  └──────────────┘                                          │
│                                                             │
│  CONTENT AREA                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │   (Skærm-specifikt indhold)                         │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Hovednavigation

1. **Overblik** - Dashboard med nøgletal og advarsler
2. **Pengekasser** - Daglig økonomi, saldooversigt, overtræk
3. **Sparegrise** - Opsparingsoversigt, låste beholdere
4. **Gældsbyrder** - Gældsoversigt, rente, afdragsstatus
5. **Budgetposter** - Budgetstyring og budgetposter
6. **Transaktioner** - Liste, kategorisering, import
7. **Forecast** - Fremtidsudsigt med graf
8. **Indstillinger** - Regler, budgetnavn, valuta, deling

**Mobilnavigation:** 8 punkter er for mange til en bundbar. På mobil grupperes Pengekasser/Sparegrise/Gæld under et "Beholdere"-punkt med tabs, eller der bruges en "Mere"-knap.

### Skærme

See the UI wireframes in the original specification for detailed screen layouts:
- Skærm 1: Overblik (Dashboard)
- Skærm 2: Transaktioner
- Skærm 3: Forecast
- Skærm 4: Budget
- Modal: Kategorisering af transaktion

### Responsivt design

**Tilgang:** Desktop-first med responsivt design til mobil.

**Breakpoint:** 768px

| Aspekt      | Desktop (>=768px)             | Mobil (<768px)                     |
| ----------- | ----------------------------- | ---------------------------------- |
| Navigation  | Sidebar (8 punkter)           | Bottom-bar (5 ikoner + "Mere")     |
| Layout      | Multi-kolonne                 | Stacked cards                      |
| Modals      | Centered overlay              | Fullscreen                         |
| Primær brug | Regnskab, import, planlægning | Status-tjek, hurtig kategorisering |

---

## Arkitektur

### Overordnet struktur

Løsningen består af to adskilte dele:

| Del               | Ansvar                                              |
| ----------------- | --------------------------------------------------- |
| **Backend (API)** | RESTful JSON API, forretningslogik, database-adgang |
| **Frontend (UI)** | Brugergrænseflade, kalder API, renderer data        |

- Backend sender **kun JSON** - aldrig færdig HTML
- Frontend er en selvstændig applikation der consumer API'et
- Klar separation muliggør uafhængig udvikling og test

### Deployment (Docker)

Løsningen deployes som tre Docker containers via Docker Compose:

| Container         | Beskrivelse                      |
| ----------------- | -------------------------------- |
| **UI**            | Serverer statiske frontend-filer |
| **API**           | FastAPI backend                  |
| **Reverse Proxy** | Router trafik, håndterer TLS     |
| **PostgreSQL**    | Database (kan være ekstern)      |

### Routing

| URL               | Destination   |
| ----------------- | ------------- |
| `domain.dk/*`     | UI container  |
| `domain.dk/api/*` | API container |

Reverse proxy håndterer routing baseret på URL-prefix.

---

## Database-specifikationer

### Primærnøgler

- **UUID** (UUIDv7 foretrukket) bruges som primærnøgle på alle entiteter
- UUIDv7 er tidsbaseret og sortérbar, hvilket giver bedre indeks-performance
- UUIDv4 som fallback hvis PostgreSQL < 17
- Fordele: Ingen enumeration-angreb, kan genereres på klient (fremtidig offline-support)

### Soft delete

Hovedentiteter bruger soft delete med `deleted_at` timestamp:

- Budgetter, Beholdere, Budgetposter, Regler, Transaktioner
- Soft-deleted filtreres fra i normale queries
- Periodisk cleanup kan permanent slette gamle soft-deleted records (f.eks. > 1 år)

Permanent sletning bruges på:

- Junction-tabeller (tildelinger)
- Sessions/tokens

### Audit trail

Minimal audit trail til MVP:

| Entitet                        | created_at | updated_at | created_by | updated_by |
| ------------------------------ | ---------- | ---------- | ---------- | ---------- |
| User                           | Ja         | Ja         | -          | -          |
| Budget                         | Ja         | Ja         | Ja         | Ja         |
| Beholder                       | Ja         | Ja         | Ja         | Ja         |
| Transaktion                    | Ja         | Ja         | Ja         | Ja         |
| Aktiv budgetpost               | Ja         | Ja         | Ja         | Ja         |
| Arkiveret budgetpost           | Ja         | Nej*       | Ja         | -          |
| Beløbsmønster                  | Ja         | Ja         | -          | -          |
| Beløbsforekomst               | Ja         | Nej*       | -          | -          |
| Regel                          | Ja         | Ja         | Ja         | Ja         |
| Tildeling (junction)           | Ja         | Ja         | -          | -          |
| Omfordeling                    | Ja         | Ja         | Ja         | Ja         |

*Arkiverede budgetposter og beløbsforekomster er uforanderlige snapshots - `updated_at` opdateres ikke.

### Beholdere (`containers`)

Én tabel for alle tre beholdertyper. Type-specifikke felter er nullable og kun relevante for den pågældende type.

| Felt                   | Type         | Beskrivelse                                                          |
| ---------------------- | ------------ | -------------------------------------------------------------------- |
| id                     | UUID         | Primærnøgle                                                          |
| budget_id              | UUID         | FK → budgets                                                         |
| name                   | TEXT         | Visningsnavn                                                         |
| type                   | enum         | cashbox, piggybank, debt                                             |
| starting_balance       | BIGINT       | Saldo ved oprettelse i øre                                           |
| bank_name              | TEXT?        | Valgfri banktilknytning: banknavn                                    |
| bank_account_name      | TEXT?        | Kontonavn hos banken                                                 |
| bank_reg_number        | TEXT?        | Registreringsnummer                                                  |
| bank_account_number    | TEXT?        | Kontonummer                                                          |
| overdraft_limit        | BIGINT?      | Kun pengekasse: overtræksgrænse i negativt øre. NULL = intet overtræk |
| locked                 | BOOLEAN?     | Kun sparegris: når true, kun indbetalinger tilladt                    |
| credit_limit           | BIGINT       | Kun gæld: kreditramme i negativt øre. **Påkrævet for gæld.**        |
| allow_withdrawals      | BOOLEAN?     | Kun gæld: kan der trækkes mere? True = kassekredit, False = kun afdrag |
| interest_rate          | DECIMAL?     | Kun gæld: årlig rente i procent (f.eks. 3.5)                        |
| interest_frequency     | TEXT?        | Kun gæld: monthly, quarterly, yearly                                 |
| required_payment       | BIGINT?      | Kun gæld: mindste månedlige afdrag i øre. NULL = intet krav         |

**Type-constraints:**
- Pengekasse: `credit_limit`, `allow_withdrawals`, `interest_rate`, `interest_frequency`, `required_payment`, `locked` skal være NULL
- Sparegris: `overdraft_limit`, `credit_limit`, `allow_withdrawals`, `interest_rate`, `interest_frequency`, `required_payment` skal være NULL
- Gæld: `overdraft_limit`, `locked` skal være NULL; `credit_limit` er påkrævet

### Aktive budgetposter (`budget_posts`)

Aktive budgetposter beskriver hvad der sker nu og fremad. Én per kategori-sti (for indtægt/udgift) eller per beholder-par (for overførsel). **Ingen periode-felter.**

| Felt                    | Type       | Beskrivelse                                                    |
| ----------------------- | ---------- | -------------------------------------------------------------- |
| id                      | UUID       | Primærnøgle                                                    |
| budget_id               | UUID       | FK → budgets                                                   |
| direction               | enum       | income, expense, transfer                                      |
| category_path           | TEXT[]?    | Kategori-sti (påkrævet for income/expense, null for transfer). Sidste element er navnet. |
| display_order           | INTEGER[]? | Sortering per niveau (matcher category_path). Leksikografisk sorteret. |
| accumulate              | bool       | Kun for expense: overføres ubrugt beløb til næste periode?     |
| container_ids           | JSONB?     | UUID[] beholder-pulje (påkrævet for income/expense, null for transfer) |
| via_container_id        | UUID?      | FK → containers. Valgfri gennemløbsbeholder (kun for income/expense) |
| transfer_from_container_id| UUID?    | FK → containers (kun for transfer, alle beholdertyper)         |
| transfer_to_container_id  | UUID?    | FK → containers (kun for transfer, alle beholdertyper, anden end from) |

**UNIQUE constraints:**
- `(budget_id, direction, category_path)` WHERE `category_path IS NOT NULL AND deleted_at IS NULL` - kun én aktiv budgetpost per kategori-sti per retning
- `(transfer_from_container_id, transfer_to_container_id)` WHERE `direction = 'transfer' AND deleted_at IS NULL` - kun én overførsel per beholder-par

### Beløbsmønstre (`amount_patterns`)

Beløbsmønstre tilhører aktive budgetposter og definerer beløb, gentagelse og beholdere:

| Felt               | Type    | Beskrivelse                                            |
| ------------------ | ------- | ------------------------------------------------------ |
| id                 | UUID    | Primærnøgle                                            |
| budget_post_id     | UUID    | FK → budget_posts (CASCADE delete)                     |
| amount             | BIGINT  | Beløb i øre                                            |
| start_date         | DATE    | Fra hvilken dato mønstret gælder. For `once`: dette ER forekomstdatoen. For `period_once`: år+måned bestemmer perioden |
| end_date           | DATE?   | Til hvilken dato (null = ubegrænset). Skal være null for ikke-gentagne typer (`once`, `period_once`) |
| recurrence_pattern | JSONB?  | Gentagelseskonfiguration                               |
| container_ids      | JSONB?  | UUID[] subset af budgetpostens beholder-pulje (null = arver puljen, null for overførsler) |

**Beholderbinding på beløbsmønster:**
- Indtægt/udgift: `container_ids` = valgfrit subset af budgetpostens beholder-pulje. Null = arver hele puljen.
- Overførsel: `container_ids` = null (beholdere er på budgetpost-niveau)

### Arkiverede budgetposter (`archived_budget_posts`)

Snapshots af hvad der var forventet i en afsluttet periode. Uforanderlige efter oprettelse. Fuldt selvstændige - ingen FK til live data for visning.

| Felt                    | Type       | Beskrivelse                                               |
| ----------------------- | ---------- | --------------------------------------------------------- |
| id                      | UUID       | Primærnøgle                                               |
| budget_id               | UUID       | FK → budgets                                              |
| budget_post_id          | UUID?      | FK → budget_posts (nullable - aktiv post kan slettes)     |
| period_year             | int        | Periodens år                                              |
| period_month            | int        | Periodens måned 1-12                                      |
| direction               | enum       | Snapshot af retning                                       |
| category_path           | TEXT[]?    | Snapshot af kategori-sti (null for overførsel). Selvstændig kopi - ingen FK. |
| display_order           | INTEGER[]? | Snapshot af sortering                                     |

**UNIQUE constraint:** `(budget_id, direction, category_path, period_year, period_month)` WHERE `category_path IS NOT NULL` - kun én arkiveret budgetpost per kategori-sti per periode.

### Beløbsforekomster (`amount_occurrences`)

Konkrete forventede beløb for en afsluttet periode. Genereres ved at ekspandere beløbsmønstre.

| Felt                      | Type    | Beskrivelse                                          |
| ------------------------- | ------- | ---------------------------------------------------- |
| id                        | UUID    | Primærnøgle                                          |
| archived_budget_post_id   | UUID    | FK → archived_budget_posts (CASCADE delete)          |
| date                      | DATE?   | Forventet dato (null for periodeomfattende beløb)    |
| amount                    | BIGINT  | Forventet beløb i øre                                |

Transaktioner i afsluttede perioder bindes til beløbsforekomster via tildelingstabellen.

### Transaktionsbinding

Transaktioner bindes til beløbsmønstre (aktiv periode) eller beløbsforekomster (afsluttet periode):

| Felt                      | Type    | Beskrivelse                                      |
| ------------------------- | ------- | ------------------------------------------------ |
| transaction_id            | UUID    | FK → transactions                                |
| amount_pattern_id         | UUID?   | FK → amount_patterns (aktiv periode)             |
| amount_occurrence_id      | UUID?   | FK → amount_occurrences (afsluttet periode)      |
| amount                    | BIGINT  | Tildelt beløb i øre                              |
| is_remainder              | bool    | Om dette er "resten" ved split                   |

**Constraint:** Præcis én af `amount_pattern_id` eller `amount_occurrence_id` skal være sat.

### Beløb-præcision

- Beløb gemmes som **integer** i mindste møntenhed (øre for DKK)
- Eksempel: 1.234,56 kr = 123456
- Undgår floating-point afrundingsfejl
- Hurtigere beregninger, simpel sammenligning
- Kolonnenavn: `amount` (generisk, ikke bundet til specifik valuta)
- BIGINT giver rigeligt med plads

### Split-tildelinger (remainder-model)

Ved split af transaktioner bruges fast beløb + "resten"-model:

- Tildelinger gemmes som faste beløb (integer)
- Én tildeling markeres som `is_remainder = true`
- Remainder beregnes som: transaktionsbeløb - sum(øvrige tildelinger)
- Eksempel 3-vejs split af 1.000 kr: 33333 + 33333 + 33334 (remainder) = 100000 øre
- Validering: sum må aldrig overstige transaktionsbeløb, remainder kan ikke blive negativ

---

## Authentication og sikkerhed

### Login-metode

- **Email/password** til MVP
- OAuth (Google) kan tilføjes post-MVP som supplement
- Passer naturligt med email-invitation til delte budgetter

### Password-krav

- Minimum: 12 tegn
- Maximum: 128 tegn
- Ingen kompleksitetskrav (ingen krav om tal, store bogstaver, specialtegn)
- Valgfrit: Tjek mod top 10.000 mest almindelige passwords
- UI: Password strength-indikator

### Session-håndtering

**Web UI (sessions):**

- Session-ID i cookie (HttpOnly, Secure, SameSite=Strict)
- Session-data i PostgreSQL
- Levetid: 30 dage (sliding expiration ved aktivitet)
- Ved logout/password-skift: Invalidér alle sessions for brugeren

**Programmatisk adgang (API-tokens, post-MVP):**

- Brugeren kan oprette API-tokens i indstillinger
- Tokens har valgfri udløbsdato (eller "aldrig")
- Tokens kan have begrænset scope (læs/skriv, specifikke budgetter)
- Bruges til integrationer (Home Assistant, scripts, etc.)
- Tokens kan tilbagekaldes individuelt

### Password-reset

- Bruger anmoder om reset → email med unikt link sendes
- Token-levetid: 1 time
- Token kan kun bruges én gang, hashet i database
- Ved nyt password: Alle sessions invalideres
- Rate limiting: Max 3 reset-emails per time per email
- Feedback: Altid "Hvis emailen findes, har vi sendt et link" (ingen enumeration)

### Email-verifikation

- Email skal verificeres før brugeren kan tilgå appen
- Flow: Opret konto → "Tjek din email" → Klik link → Adgang
- Token-levetid: 24 timer
- Kan gen-sende verifikations-email (rate limited: max 3 per time)
- Uverificerede konti slettes automatisk efter 7 dage

---

## API-design

### Forecast-beregning

- On-the-fly beregning, ingen persisteret cache til MVP
- Fokus på optimeret datalagring og effektive SQL-queries
- Aggregater beregnes direkte i databasen (undgå N+1 queries)
- Aktive budgetposters beløbsmønstre ekspanderes til forekomster i hukommelsen (billigt for personlige budgetter)
- Afsluttede perioder: bruger arkiverede budgetposter med beløbsforekomster direkte
- Hvis performance bliver et problem post-MVP, kan cache-lag tilføjes (f.eks. Redis)

### Forecast-horisont

- Default visning: 12 perioder (nuværende + 11 fremtidige, eller mix af forrige/fremtidige)
- API accepterer vilkårlig periode-range (start/slut måned)
- Ingen hård grænse - brugeren kan se f.eks. hele 2027 fra 2026
- Frontend tilbyder standard-views (3, 6, 12 måneder) + mulighed for custom range

### Validerings-respons

To-niveau respons med errors og warnings:

- **Errors:** Blokerende fejl, handlingen afvises (manglende felter, ugyldigt format, ugyldige referencer)
- **Warnings:** Handlingen gennemføres, men brugeren adviseres (budget i minus, potentiel duplikat)
- Respons inkluderer `success`, `data`, `errors[]` og/eller `warnings[]`

### Pagination

Cursor-baseret pagination:

- Cursor er encoded reference til sidste element (f.eks. base64 af id + dato)
- Stabil ved ændringer - ingen "hop" eller duplikater når data ændres
- Format: `GET /api/.../transactions?limit=50&cursor=abc123`
- Respons inkluderer `next_cursor` (null hvis ingen flere)

### Rate limiting

| Endpoint-type      | Grænse             |
| ------------------ | ------------------ |
| Generelle API-kald | 100/min per bruger |
| Login-forsøg       | 5/min per IP       |
| Password reset     | 3/time per email   |
| Email-verifikation | 3/time per email   |

HTTP 429 "Too Many Requests" ved overskridelse med `Retry-After` header.

---

## Tech Stack

| Komponent          | Teknologi                                                       | Begrundelse                                                                   |
| ------------------ | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Backend            | Python + FastAPI                                                | Moderne, hurtig, god dokumentation                                            |
| Database           | PostgreSQL                                                      | Robust, JSONB til fleksible felter                                            |
| Frontend           | Svelte                                                          | Kompilerer til vanilla JS, minimal runtime, reaktivitet indbygget, scoped CSS |
| Styling            | Scoped CSS (Svelte)                                             | Indbygget i Svelte, ingen naming-konflikter, bruger CSS custom properties     |
| Grafer             | Apache ECharts                                                  | Built-in Sankey support, custom build ~300KB                                  |
| Auth               | passlib (bcrypt), itsdangerous, slowapi                         | Simpel custom implementation                                                  |
| Migrations         | Alembic                                                         | Standard for SQLAlchemy                                                       |
| Ikoner             | Lucide Icons                                                    | Open source (ISC), inline SVG                                                 |
| Test               | pytest (backend)                                                | Pragmatisk MVP-tilgang, manuel test for frontend                              |
| Container          | Docker Compose                                                  | Nem selfhosted deployment                                                     |
| Base images        | python:3.12-slim (API), nginx:alpine (UI), caddy:alpine (proxy) | Undgår Alpine/musl-problemer med Python                                       |
| Frontend webserver | Nginx                                                           | Industristandard, hurtig, minimal ressourceforbrug                            |
| Reverse proxy      | Caddy                                                           | Automatisk HTTPS, simpel config, perfekt til selfhosted                       |

### CI/CD

- **MVP:** GitHub som backup og versionering, manuel deployment
- **Post-MVP:** GitHub Actions med lint, test og auto-deploy

---

## Language and Internationalization

### Code and Documentation Language

All code and documentation must be written in **English**:

| Element                 | Language | Example                              |
| ----------------------- | -------- | ------------------------------------ |
| Variable/function names | English  | `get_container_balance()`, `isLoading` |
| Comments                | English  | `// Calculate running total`         |
| Commit messages         | English  | `feat(auth): add session management` |
| Documentation           | English  | README, API docs, code comments      |
| Error messages (code)   | English  | `raise ValueError("Invalid amount")` |

### User-Facing Text (i18n)

User-facing text uses **translation files** with Danish as default:

| Element             | Approach                                          |
| ------------------- | ------------------------------------------------- |
| UI labels           | Translation keys, e.g., `$t('dashboard.balance')` |
| Error messages (UI) | Translation keys                                  |
| Default locale      | Danish (`da`)                                     |
| Future locales      | Prepared structure for `en`, `de`, etc.           |

### Translation File Structure

```
ui/src/lib/i18n/
├── index.ts          # i18n setup and helper functions
├── locales/
│   ├── da.json       # Danish (default)
│   └── en.json       # English (placeholder for future)
```

### Translation File Format

```json
{
  "common": {
    "save": "Gem",
    "cancel": "Annuller",
    "delete": "Slet",
    "loading": "Indlæser..."
  },
  "dashboard": {
    "title": "Overblik",
    "availableBalance": "Disponibel saldo",
    "thisMonth": "Denne måned"
  },
  "auth": {
    "login": "Log ind",
    "register": "Opret konto",
    "email": "Email",
    "password": "Adgangskode"
  }
}
```

### Implementation Notes

- Use a simple i18n approach (e.g., `svelte-i18n` or custom lightweight solution)
- All hardcoded Danish text in UI must use translation keys
- Backend API responses use English; translation happens in frontend
- Database content (user data) is not translated

---

## MVP-scope

### Must-have (MVP)

Følgende funktioner er påkrævet til første version:

- **Bruger-registrering og login** (email/password)
- **Opret/rediger budget og beholdere**
- **Manuel oprettelse af transaktioner**
- **Kategorisering** (tildel transaktion til budgetpost)
- **Budgetposter med gentagelse**
- **Dashboard** (saldo, afventer-liste)
- **Simpel forecast** (linjegraf + tabel)

### Nice-to-have (post-MVP, prioriteret)

| Prioritet | Feature                    | Beskrivelse                            |
| --------- | -------------------------- | -------------------------------------- |
| Høj       | CSV-import                 | Import af transaktioner fra bankudtræk |
| Høj       | Regler/auto-kategorisering | Automatisk matching af transaktioner   |
| Medium    | Delte budgetter            | Del budget med partner/familie         |
| Lav       | Mørkt tema                 | Alternativt farvetema                  |
| Lav       | Kvitteringshåndtering/OCR  | Scan og parse kvitteringer             |
| Lav       | API-tokens                 | Programmatisk adgang til data          |

### Eksplicit IKKE i MVP

- Delte budgetter (post-MVP, medium prioritet)
- CSV-import (post-MVP, høj prioritet - første feature efter MVP)
- API-tokens (post-MVP, lav prioritet)
- Mørkt tema (post-MVP, lav prioritet)
- Offline-support / PWA (ikke planlagt)
- Onboarding-wizard (ikke nødvendigt - simpel oprettelse)
- Import fra andre systemer (Spiir etc.)

---

_Status: MVP specifikation komplet. Se CLAUDE.md for udviklings-workflow._
