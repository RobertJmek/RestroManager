import { test, expect } from '@playwright/test';

test.describe('Customer Interface', () => {
  
  test('ar trebui sa arate corect Catalogul si sa nu aiba produse in cos initial', async ({ page }) => {
    // 1. Vizitează pagina de clienți
    await page.goto('/customer');

    // 2. Verifică dacă titlul paginii conține RestroManager
    await expect(page.locator('h1')).toContainText('RestroManager');

    // 3. Verifică dacă Meniul s-a randat (verificăm un produs)
    const burgerTitle = page.locator('text="Burger Wagyu Suprem"').first();
    await expect(burgerTitle).toBeVisible();

    // 4. Verifică faptul că butonul de coș nu arată niciun număr (coș gol)
    const cartButton = page.locator('button:has-text("Coș")');
    await expect(cartButton).toBeVisible();
    await expect(page.locator('span.bg-red-500')).toHaveCount(0); // Bula roșie cu numărul de iteme nu trebuie să existe
  });

  test('ar trebui sa adauge un produs in cos si sa calculeze totalul', async ({ page }) => {
    await page.goto('/customer');

    // 1. Dăm click pe "Comandă" la primul produs
    await page.locator('button:has-text("Comandă")').first().click();

    // 2. Se deschide Modal-ul, adăugăm o notă
    await page.locator('textarea[placeholder*="Note speciale"]').fill('Fără ceapă vă rog');
    
    // 3. Dăm "Adaugă în coș" cu un delay vizual mic
    // Ne asigurăm că am rezolvat și interceptat alerta de succes ca să nu blocheze testul
    page.on('dialog', dialog => dialog.accept());
    await page.locator('button:has-text("Adaugă în coș")').click();

    // Apăsăm Escape pentru a închide modalul (deoarece el rămâne deschis și blochează butonul de coș)
    await page.keyboard.press('Escape');

    // Așteptăm jumătate de secundă ca animația de închidere a modalului să dispară
    // (în timpul animației, body-ul are pointer-events: none, ceea ce ignoră click-urile)
    await page.waitForTimeout(500);

    // 4. Verificăm că a apărut 1 în bula roșie de pe coș
    await expect(page.locator('span.bg-red-500')).toHaveText('1');

    // 5. Deschidem coșul (căutăm butonul flotant după o clasă unică pentru a evita potrivirea textului 'în coș')
    await page.locator('button.bg-indigo-600.rounded-full').click();

    // Așteptăm ca modalul de coș să apară
    const cartModal = page.getByRole('dialog');
    await expect(cartModal).toBeVisible();

    // 6. Verificăm că produsul și nota există în coș
    await expect(cartModal).toContainText('Fără ceapă vă rog');
    
    // 7. Verificăm că totalul apare ca "65.00 RON"
    await expect(cartModal.locator('text=65.00 RON').last()).toBeVisible();
  });
});
