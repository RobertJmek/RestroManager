# Raport – Folosirea toolurilor de AI în timpul dezvoltării software

**Echipă:** Bunescu Robert · Calomfirescu Victor · Floroiu Stefan

## Introducere

RestroManager este un sistem de management pentru restaurante, cu patru interfețe (client, chelner, bucătar, manager) și comunicare în timp real, dezvoltat în echipă de trei persoane pe parcursul a aproximativ trei luni (~145 de commit-uri în total). Rolurile au fost împărțite astfel: **Bunescu Robert** — „Core Architect & Manager" (backend, baza de date, autentificare, dashboard manager, deployment și agenții AI integrați în produs); **Calomfirescu Victor** — „Customer Champion" (catalogul digital, coșul, checkout-ul și butonul de chemare a chelnerului); **Floroiu Stefan** — „Real-time Master" (WebSocket, sincronizarea stărilor între interfețe, notificările în timp real și testele de integrare). Un obiectiv explicit al proiectului a fost folosirea extensivă a agenților AI pe tot parcursul dezvoltării, fără a ne limita la un singur tool.

---

# Bunescu Robert — Core Architect & Manager

Aproximativ 100 din cele ~145 de commit-uri ale proiectului îmi aparțin. Ca lider, am coordonat echipa prin întâlniri regulate: am discutat ce vrea fiecare, am propus un plan pe epics și am ajustat până la un acord comun.

## Cum am folosit toolurile AI — în două sensuri distincte

Merită făcută o distincție pe care am trăit-o direct, pentru că proiectul conține ambele variante:

- **AI ca unealtă de dezvoltare** — *GitHub Copilot* și *Claude Code* (Anthropic) pentru a genera modele SQLModel, rute FastAPI, componente React, configurări Docker și review-uri automate pe pull request-uri. Un agent Copilot a ajuns autorul a 14 commit-uri reale în repo, inclusiv un batch de securitate ([`b2cdba3`](https://github.com/RobertJmek/RestroManager/commit/b2cdba32d1174e4db2949936189c9bdf2bbe18e4), 2 mai: *order spoofing, table validation, WS auth*) — unealta nu doar sugera, ci comitea cod pe care eu îl revizuiam.
- **Agenți AI livrați în produs** — recomandări pentru clienți, plus insights și generare de meniu pentru manager, folosind modelul *DeepSeek* (`core/ai.py`).

## Problemele la agenții AI din produs

Cea mai grea parte n-a fost scrierea agenților, ci îmblânzirea lor. Modelul nu returna mereu JSON valid, așa că am scris o utilitate de extragere și am întărit prompt-ul cu prețuri și alergeni ([`66d482b`](https://github.com/RobertJmek/RestroManager/commit/66d482bf94b8d7a063450d49532c8ef98b27785f)). Apoi am vrut să măsor calitatea cu un framework de evaluare — și aici a început adevărata bătălie. Eval-urile costau (API cu plată) și, fără cheie reală, fallback-ul pur și simplu nu trecea testele; le-am scos din CI cu un mesaj cât se poate de sincer ([`829ecb4`](https://github.com/RobertJmek/RestroManager/commit/829ecb4cae4643619b5a63de660d9f434ba57b5f): *„not feasible since they cost with a real API key and with the fallback they just don't pass"*). Soluția finală a fost să le **împart în două**: eval-uri reale, opt-in, și teste de regresie gratuite ([`f610819`](https://github.com/RobertJmek/RestroManager/commit/f610819cfd71f17a34f8a843b06d8838da69195b)). Pe parcurs, agentul inventa uneori produse sau prețuri inexistente (grounding), așa că am adăugat o metrică dedicată, conștientă de date și procente ([`059977a`](https://github.com/RobertJmek/RestroManager/commit/059977a26c9aa734b188826b0f92f394aa44d69d)) — o îmbunătățire, nu o soluție perfectă.

## Ce a mers, ce a fost greu

Infrastructura și funcționalitățile de manager au fost livrate la timp, iar AI-ul a accelerat boilerplate-ul, documentația (README, diagrame Mermaid, referință API) și hardening-ul de securitate din iunie ([`dc21051`](https://github.com/RobertJmek/RestroManager/commit/dc21051c19f9f55365a39119d86e316258d38566) rate limiting, [`8d3b6b8`](https://github.com/RobertJmek/RestroManager/commit/8d3b6b8a87c84141230a79d79d87b11b196e668f) parole seed mutate din sursă, [`8589a44`](https://github.com/RobertJmek/RestroManager/commit/8589a440adaa48d6c3f140ad2dd5e53773f5d086) autentificare pe endpoint-urile de comenzi). Partea grea a fost integrarea: agentul genera uneori cod care ignora contextul existent, iar refactorizările au apărut abia după ce am lipit piesele împreună — de exemplu fixurile de WebSocket după integrarea cu partea lui Stefan (branch `bugfix/integration-fixes`, [`4393483`](https://github.com/RobertJmek/RestroManager/commit/43934836a093991bfdc52693f9dd0075764fbdaf)) sau checkout-ul lui Victor. Bug-urile reale au ieșit la iveală doar când am testat toate rolurile simultan.

## Sinteză: tooluri folosite și verificarea manuală

| Tool AI | Unde l-am folosit | Ce am corectat / verificat manual |
|---|---|---|
| **GitHub Copilot** | Review-uri automate pe PR, fixuri de securitate și integrare (autor a 14 commit-uri) | Sugestii cu probleme de securitate (total calculat pe client, auth pe WebSocket) — revizuite și corectate ([`b2cdba3`](https://github.com/RobertJmek/RestroManager/commit/b2cdba32d1174e4db2949936189c9bdf2bbe18e4)) |
| **Claude Code** (Anthropic) | Boilerplate backend/frontend, Docker, deployment, documentație, hardening securitate | Cod care ignora contextul existent → refactor după integrare; verificare manuală la fiecare pas de deployment (CORS, env vars) |
| **DeepSeek** (model în produs) | Agenți de recomandare, insights și generare meniu (`core/ai.py`) | JSON invalid → utilitate de extragere ([`66d482b`](https://github.com/RobertJmek/RestroManager/commit/66d482bf94b8d7a063450d49532c8ef98b27785f)); halucinații preț/produs → metrică de grounding ([`059977a`](https://github.com/RobertJmek/RestroManager/commit/059977a26c9aa734b188826b0f92f394aa44d69d)) |

## Concluzii

Dependența de AI poate da impresia că un feature e gata când, de fapt, lipsește testarea; review-urile automate nu înlocuiesc testarea manuală pe fluxuri real-time. Toolurile AI sunt excelente la boilerplate, documentație și explorare, dar deciziile de arhitectură și testarea end-to-end rămân responsabilitatea dezvoltatorului. Iar uneori — [`82ca751`](https://github.com/RobertJmek/RestroManager/commit/82ca751d14725ad73e92474cb840eaeb0c71539f) o dovedește — singurul bug rămas în pipeline ești chiar tu.

---

# Calomfirescu Victor — Customer Champion

Contribuția mea activă a fost în principal în aprilie–mai 2026, pe partea de client.

## Cum am folosit agenții AI

Am folosit un agent AI integrat în editor aproape zilnic. Îl foloseam pentru componente React pe interfața clientului, pentru endpoint-uri legate de meniu și comenzi și pentru erorile din consolă. Îi descriam task-ul în limbaj natural, apoi verificam codul generat și îl adaptam la structura existentă din proiect.

La început, agentul a ajutat la setup-ul frontend: layout-uri, navigare între cele patru aplicații (client, chelner, bucătar, manager) și componente shadcn/ui. Mai târziu l-am folosit mai des pentru debugging și pentru teste (unitare și Playwright), nu doar pentru cod nou.

## Exemple din task-urile mele

Am implementat catalogul digital cu carduri de produse și un dialog pentru instrucțiuni speciale (ex. „fără ceapă"). Agentul a ajutat la structurarea componentelor și la conectarea cu backend-ul; detaliile de stil și UX le-am ajustat manual.

La coș și checkout, am lucrat la logica de adăugare/eliminare produse, trimiterea comenzii către backend și ecranul de confirmare. Am setat și precizia de două zecimale pentru prețuri, în pregătirea unei integrări Stripe complete (care nu a fost finalizată în întregime în versiunea curentă). Aici AI-ul a accelerat logica de bază, dar unele sugestii nu se potriveau cu schema comenzilor de pe backend.

Am adăugat butonul „Call Waiter", care trimite un eveniment WebSocket către chelnerul asociat mesei. A fost un task mic, dar a necesitat înțelegerea conexiunii WS deja implementate de colegi.

Am lucrat și la personalizarea comenzilor la nivel de produs (Epic 6), plus câteva bugfix-uri de integrare: izolarea logout-ului clientului ca să nu afecteze personalul, filtrarea produselor servite din KDS și un fix pe reconnect WebSocket. Acestea au depășit zona mea inițială, iar agentul a fost util mai ales pentru a urmări fluxul de date.

Spre final am contribuit la teste unitare (backend și frontend) și la teste Playwright pentru interfața clientului. Agentul a generat scenarii repetitive; o parte a testelor a trebuit rescrisă după testare manuală.

## Ce a mers bine și ce a fost mai greu

Funcționalitățile de client au fost livrate la timp, iar agentul AI a redus timpul petrecut pe erori de tipuri TypeScript sau pe configurări de framework.

Problemele au apărut mai ales la integrare: codul generat funcționa izolat, dar nu mereu cu WebSocket-urile sau autentificarea făcute de colegi. A trebuit să citesc codul existent înainte de a accepta o soluție generată.

Uneori agentul propunea soluții prea complexe pentru task-uri simple. În aceste cazuri am pierdut timp până am găsit o variantă mai directă.

## Concluzii

Agenții AI au scurtat timpul de implementare pe partea de client, dar nu elimină necesitatea de a înțelege codul și de a testa manual, mai ales la integrare.

În proiecte viitoare aș folosi agentul mai ales la începutul unui feature sau la teste, cu verificare înainte de commit că modificările se potrivesc cu restul echipei.

---

# Floroiu Stefan — Real-time Master

Comunicarea în timp real a fost piesa centrală a contribuției mele.

## Ce tool-uri AI am folosit și cum

În mare parte, ne-am împărțit între trei unelte, fiecare cu utilitatea ei:
•	**ChatGPT și Google Gemini (în browser):** Le-am folosit ca pe niște colegi mai experimentați cu care stăteam de vorbă când nu înțelegeam cum funcționează o anumită chestie din documentația FastAPI sau când dădea React-ul erori ciudate pe stări și nu știam de unde să le apuc.
•	**GitHub Copilot (integrat în editor):** L-am lăsat pornit în VS Code pentru auto-complete. A fost bun mai ales când aveam de scris cod repetitiv, structuri simple de rute sau când trebuia să generez rapid scheletul pentru vreo funcție.

## Exemple concrete de task-uri

**WebSocket Manager-ul cu broadcast pe roluri:** A fost primul meu task mare, unde trebuia să separ mesajele ca să meargă doar la chelneri sau doar la bucătari. Copilot m-a ajutat să generez rapid structura clasei de conexiuni și metodele de bază. Partea de securitate și verificarea token-ului JWT pe socket-uri a fost extinsă ulterior de Robert pe backend, eu rămânând concentrat pe logica de mesaje. 

**Dashboard-urile de chelner și bucătar (KDS):** Eu am pus logica de bază în background, adică harta meselor, ecranul de bucătărie și cum sar notificările la evenimente. După aceea, interfețele au fost modificate și refăcute în mare parte de Robert, care s-a ocupat de design, gestionarea comenzilor pe KDS și fluxul de comandă pornit de chelner. Eu am rămas să am grijă ca trecerea datelor prin WebSockets să nu crape în spate. 

**Epic 40 (sincronizarea fluxului de comandă):** Aici a fost destul de greu pentru că s-au schimbat statusurile la OrderItem și notificările, iar modificările au dat peste cap și clientul (Victor) și backend-ul (Robert). AI-ul m-a ajutat să urmăresc logic cum ar trebui să se schimbe stările în lanț, dar testarea finală tot manual a trebuit să o fac, deschizând câte două-trei tab-uri de browser deodată ca să văd dacă se trimit mesajele corect. 

**Teste de integrare:** Spre final, am scris teste în Pytest și am reparat și fluxul de checkout care pica la teste. AI-ul mi-a generat niște scenarii de pornire, dar multe au dat eroare din prima pentru că bucățile de cod simulate (mock-urile) sugerate de el nu se comportau deloc ca un WebSocket real. A trebuit să le modific manual ca să meargă. 

## Ce a mers bine și ce mi s-a părut greu

**Ce a fost ok:** AI-ul chiar m-a salvat de mult timp pierdut pe Google sau prin documentația FastAPI când căutam cum se face un sistem de reconectare automată sau un broadcast curat. Copilot a fost și el util că scria repede codul plictisitor. 

**Ce a fost greu:** Partea de real-time e foarte păcătoasă și sensibilă la detalii. De multe ori, codul generat de Gemini sau ChatGPT părea perfect corect la prima vedere, dar când îl rulam, aplicația intra în bucle infinite de reconectare sau trimitea mesaje duplicate în rețea. Până nu deschideam eu manual două browsere diferite ca să testez live, nu aveam nicio siguranță. 

O altă problemă a fost că atunci când colegii modificau ceva la API sau la logica de login, AI-ul nu știa asta, pentru că el nu vedea restul proiectului actualizat în timp real. Îmi dădea cod bazat pe versiuni vechi și trebuia să stau să-i dau eu copy-paste la fișierele noi ca să-i explic contextul. 

## Concluzii

Pentru ce am avut eu de făcut pe partea de asincron și WebSockets, asistenții AI au fost foarte buni ca să pornesc la drum și să fac scheletul codului mai repede. Însă nu au cum să înlocuiască testele pe bune, atenția la logica aplicației și, mai ales, discuțiile din echipă. 

Dacă ar fi să o iau de la capăt, i-am folosi mai degrabă când am de căutat de ce dă o eroare greu de înțeles (la diagnoză) și mai puțin ca să-mi genereze blocuri mari de cod de-a gata, pentru că la sisteme cu stări care se schimbă live mai mult încurcă. 
