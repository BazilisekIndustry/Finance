# Family Finance Planner

První implementační etapa obsahuje datový model, SQL migraci s RLS, samostatné finanční výpočty a testy. Streamlit UI a Supabase klient budou následovat až po ověření výpočetního jádra.

Pravidelný příjem nebo výdaj je verzovatelný přes `effective_from` / `effective_to`; budoucí změna částky tedy vznikne jako nový záznam, místo přepsání historické definice.

Repository vrstva v `database/repositories/` vždy zjišťuje vlastníka z ověřeného JWT (`auth.get_user()`), a k dotazům přidává filtr `user_id`. Databázové RLS je druhá, nezávislá ochranná vrstva.

Kurzovní zdroj je implementován jako vyměnitelný provider. Výchozí provider ČNB načítá oficiální denní TXT kurzovní lístek a ukládá kurzy jako počet CZK za jednu jednotku měny. ČNB kurzy zveřejňuje jednou denně v pracovní dny; viz [dokumentace ČNB](https://www.cnb.cz/cs/casto-kladene-dotazy/Kurzy-devizoveho-trhu-na-www-strankach-CNB/).

## Lokální ověření

```powershell
python -m pytest
```

## Supabase Auth

Zkopírujte `.streamlit/secrets.toml.example` jako `.streamlit/secrets.toml` a vložte URL projektu a jeho **anon key**. Service-role klíč aplikace nepoužívá, protože by obcházel RLS. Přihlášení vytváří Supabase session, relace se drží pouze v paměti bezpečné Streamlit session a lze ji obnovit přes refresh token. Pro obnovu po úplném zavření či načtení prohlížeče bude při VPS nasazení potřeba samostatná HttpOnly cookie vrstva; token se proto záměrně neukládá do URL ani do nezabezpečeného browser storage.

## Databáze

Migraci `database/migrations/001_initial_schema.sql` spusťte v prázdném Supabase projektu přes SQL Editor nebo Supabase CLI. Přihlašovací údaje nikdy neukládejte do repozitáře; lokálně patří do `.streamlit/secrets.toml`.

## Nasazení

### Streamlit Community Cloud

1. Vytvořte Supabase projekt a v SQL Editoru spusťte migraci.
2. V Supabase Auth vytvořte uživatele s e-mailem a heslem (pro první verzi může zůstat zapnuté pouze e-mailové přihlášení).
3. Nahrajte repository na GitHub a v Streamlit Community Cloud vyberte `app.py` jako hlavní soubor.
4. Do nastavení aplikace vložte secrets:

```toml
[supabase]
url = "https://your-project.supabase.co"
anon_key = "your-supabase-anon-key"
```

Nikdy nevkládejte `service_role` klíč: obcházel by Row Level Security.

### VPS

Na VPS nainstalujte Python 3.11+, naklonujte repository, vytvořte virtuální prostředí a spusťte:

```bash
pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Před Streamlit umístěte Nginx s HTTPS terminací a proxy na `127.0.0.1:8501`. Secrets uchovávejte mimo repository, například v `/etc/family-finance/secrets.toml`, a před spuštěním je zkopírujte do `.streamlit/secrets.toml` s právy jen pro aplikačního uživatele.
