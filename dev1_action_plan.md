# 🚀 Plan de Acțiune Complet - DEV 1 (Customer Champion)

Acest document conține toți pașii absoluți necesari, de la comenzi în terminal la workflow de la bun început și până la final, asigurat ca să acoperi nu doar rolul tău ca "Dev 1", ci și cerințele restrictive de *source control* și *AI features* de la universitate (baremul MDS).

---

## 🛠️ ETAPA 1: Setup-ul Inițial (Primul tău pas efectiv OBLIGATORIU ACUM)

Aici pui fundația Frontend-ului pe curat (Issue 1.1) fără să atingi munca codată de Dev 3 pe backend.

1.  **Sincronizează-te cu repo-ul remote**
    ```bash
    git checkout main
    git pull origin main
    ```
2.  **Creează un branch separat pentru tine** (Cerință Baremul B - source control)
    ```bash
    git checkout -b feat/frontend-init
    ```
3.  **Inițiază Next.js** (OBLIGATORIU: Mută-te în folderul `frontend` gol, șterge fișierul ciudat "bla" dacă există, și initializează)
    ```bash
    cd frontend
    rm bla 
    npx -y create-next-app@latest . 
    # la întrebări: Yes la TypeScript, Yes la Tailwind, Yes la App Router.
    ```
4.  **Instalează și configurează shadcn/ui**
    ```bash
    npx shadcn@latest init
    npx shadcn@latest add card button dialog
    ```
5.  **Curățenie & Structura Foldere:** 
    - Șterge boilerplatu-ul ciudat creat de Next din `app/page.tsx` și pune un Hello World curat.
    - Creează un sub-folder: `app/customer/page.tsx` (sau structura dorită) unde vei munci de azi incolo.
6.  🔴 **Git Timpul! Trimite codul tău** - Acesta este primul tău commit (1 din 5 obligatorii).
    ```bash
    git add .
    git commit -m "feat: Initial Next.js frontend setup with Tailwind and shadcn/ui"
    git push origin feat/frontend-init
    ```
7.  **Pull Request:** Mergi pe site la GitHub. Vei vedea buton cu "Compare & Pull Request". Creează cererea și roagă pe Dev 3 sau Dev 2 să dea **Merge** spre `main`.

---

## 🛍️ ETAPA 2: Catalogul Meniului (Date Mockate)

Aici creezi fața aplicației pentru clienți, folosind date false deoarece Backend-ul încă nu are meniuri salvate.

1.  Trage ultima versiune local la tine și fa alt branch de feature:
    ```bash
    git checkout main
    git pull origin main
    git checkout -b feat/customer-catalog
    ```
2.  **Cod:** În interiorul lui `app/customer/page.tsx` creează o arhitectură vizuală frumoasă folosind `<Card>` (din cele adaugate la Etapa 1). 
    - Fă un array local (Mocked JSON) denumit `fakeMenu` care sa conțină 2-3 produse (ex: Pizza Margherita - 30 RON).
    - Pune butoane "Add to Cart" lângă ele.
    - Implementează `<Dialog>` (un Modal vizual) ce se deschide dacă apeși pe "Special Instructions".
3.  🔴 **Git Timpul! Commit 2**.
    ```bash
    git add .
    git commit -m "feat: Create mocked customer catalog UI and special instructions modal"
    # Nu da pull request încă. Vom mai munci pe acest branch.
    ```

---

## 🤖 ETAPA 3: Marea Inserție - AI Agent-ul tău

Baremul MDS te obligă ("3 puncte live demo = 2 AI Agenți in pipeline"). Ca *"The Customer Champion"*, este genial să faci primul Agent aici!

1.  **AI Food Recommender:** Fă un form/chat input simplu deasupra Meniului cu textul ( „Ești nehotărât? Întreabă Chelnerul Virtual inteligent!”). 
2.  Folosește un SDK simplu (ex. Gemini API sau o chemare HTTP standard / Langchain) în serverul de frontend (Next.js App Router API form) pentru a procesa propoziția („Vreau ceva dulce cu pui„ -> Răspuns AI: „A.. cred că dorești puiul caramelizat din Meniul Secundar!„).
3.  🔴 **Git Timpul! Commit 3** (Extrem de valoros pt Puncte!).
    ```bash
    git add .
    git commit -m "feat: Integrate AI Food Recommender Agent in Customer View"
    git push origin feat/customer-catalog
    ```
4.  **Pull Request:** Faci Pull Request spre `main`. Acum ai Meniul vizualțional și funcția de AI aprobate!

---

## 🛒 ETAPA 4: Integrări Finale & Stripe (Odată ce Dev 3 termină Backend-ul)

1.  Fă fetch la main și inițializează un branch nou pentru comenzi.
    ```bash
    git checkout main
    git pull origin main
    git checkout -b feat/orders-and-stripe
    ```
2.  **Înlocuire date fake cu Fetch real (`Issue 2.1 part 2`)**: Modifică array-ul tău Fake ca să dea fetch direct la `/api/menu` expus de Dev 3 pe backend pe port 8000.
3.  **Coș de cumpărături (`Issue 2.2`)**: Adaugă React Context pentru logica internă. La click pe "Checkout", emite un `POST` cu coșul de cumpărături către `http://localhost:8000/api/orders`.
4.  🔴 **Git Timpul! Commit 4**.
    ```bash
    git add .
    git commit -m "feat: Fetch real menu from server and submit orders via POST"
    ```
5.  **Stripe (`Issue 2.3`)**: Vei integra redirecționarea spre Stripe Check-out generat în prealabil din funcțiile voastre. Implementezi ecranele de Success/Failure.
6.  🔴 **Git Timpul! Commit 5**. (Acum ești "Barem Compliant" oficial cu minimul de commituri).
    ```bash
    git add .
    git commit -m "feat: Implement Stripe Checkout Session redirect for user payments"
    git push origin feat/orders-and-stripe
    ```
7.  **Pull Request:** Du-te pe site și faceți `Merge` la PR în echipă!

---

## 📡 ETAPA 5: Conectarea Butonului "Call Waiter" (Depinde de Dev 2)

1. **Branch nou**: `feat/call-waiter-btn` (după ce faci `git checkout main` și `git pull main`).
2. Adaugă butonul vizual în frontend. Când Dev 2 are API-ul ridicat de Websocket, vei insera un mic fragment de cod (`const ws = new WebSocket('ws://...')`) în spatele butonului de **Call Waiter** astfel ca mesajele să plece spre portul lor comun.
3. 🔴 **Git Timpul! Commit 6**:
    ```bash
    git add .
    git commit -m "feat: Add Waiter Call Button triggering WebSocket payload"
    git push origin feat/call-waiter-btn
    ```
4. Rulează PR-ul și unifică cu baza.

---

## 🧪 ETAPA 6: Cerințele Administrative Absolute din BAREM (Esențiale pentru Notă)

Tu lucrezi intensiv ca programator Frontend, prin urmare vei obține punctaj masiv și neașteptat din partea laborantului dacă iei asupra ta următoarele Taskuri de management (Cerințele de "Proces Software" A,B,C din fișierul de barem).

1.  **Raporteaza Bug via Issue Github & Pr (1 pct direct)**:
    - Fă intenționat (sau la prima ocazie când observi o greșeală organică logico/matematică vizualizând CSS-ul sau prețurile) o greșeală pe branch-ul de development. (Ex: "Prețul apare 3000 în loc de 30 pt că din Stripe e venit în cenți").
    - Intră repede ca user-ul tău pe site-ul de Github -> secțiunea "Issues" -> Adaugă problema noua: `Title: Bug on Cart Total Decimal Value`.
    - Du-te in terminal local, fă un branch denumit `fix/cart-cents-bug`, rezolvă greșeala din frontend (bagi o împărțire la `/100`), apoi dai Commit *"fix: Resolve price miscalculation, closes #NumarIssue"*, și faci Pull Request spre Main. 
2. **CI/CD Pipeline (1 pct)**:
    - Soluția minune e platforma `Vercel.com` (aplicația Next.js este detinută de ei). Loghează-te cu Github, alege repository-ul `RestroManager`, setează folderul de "Root" drept `/frontend` la import, și apasă `Deploy`. 
    - După scurte minute vei avea un link valid gratuit (`ex. proiect-mds.vercel.app`). Modifică `README.md` punând acel link! Laborantul va fi plăcut surprins că folosiți CD și au un website gata ridicat de interacționat cu el non-stop la validările PR.
3. **Teste automate (2 pct)**:
    - Faci ultimul tău branch `feat/automated-tests`.
    - Folosind funcțiile de test instalate default din Next.js / React Testing Library, generat cu ChatGPT/Cursor scrie 2 fișiere simple de test pentru coș (Să fii sigur ca produs 1 + produs 2 = un total curat). 
    - 🔴 **Git Timpul! Commit 7**. Dă Commit cu *"test: Added Playwright/Jest tests for Customer UI component"*.
     
Respectând graficul de mai sus, acoperi exact rolul tău de Dev 1 și tragi restul echipei în sus luând majoritatea punctelor procedurale pe care adeseori studenții le trec cu vederea (sau le omit).
