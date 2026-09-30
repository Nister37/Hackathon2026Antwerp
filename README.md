# Hackathon 2026 Antwerp

Nx monorepo with a Spring Boot backend and a React/Vite frontend. The backend
keeps the Java 21 and Spring Boot conventions from the Programming 5 Traffic
Lights project while separating the browser application from Spring resources.

## Project structure

```text
backend/   Spring Boot 4, Gradle, Java 21, PostgreSQL
frontend/  React 19, Vite, TypeScript
ml/        Python batch pipeline for explainable demo insights
```

Nx is the task runner for both projects. Gradle remains the backend build tool,
and Vite handles the frontend development server and production bundle.
The frontend uses Sass and recreates the supplied KBC reference screens as a
demo prototype. It calls the local Spring API for transactions and ML insights,
but is not connected to a bank account or payment API.

## KBC prototype screens

| Route | Reference flow |
| --- | --- |
| `/` | Reach overview and widgets |
| `/personal` | Anne mobile start |
| `/kate` | Kate mobile start |
| `/accounts` | My KBC personal and business accounts |
| `/transfer` | Desktop transfer form and mobile SEPA review |
| `/business-transfer` | Business PRO transfer confirmation |
| `/timeline` | Business transactions and timeline |
| `/settings` | Business settings |
| `/user-settings` | Switch between User 1 (Tom) and User 2 (Maria) |

The source images are retained in `templates/`. Where screenshots conceal or
crop information, the prototype does not fill in missing account details.
Transfer signing is deliberately simulated and cannot send a payment.
The Spring Boot backend reads `data/tom_transactions.csv` and
`data/maria_transactions.csv` at startup. The frontend requests at most eight
recent transactions per user from `/api/users/{id}/transactions`; no CSV is
bundled into the browser, and the API DTO omits transaction and customer IDs.
Switching users changes the requested data and is stored locally in the browser.
The CSVs contain no balances, account numbers, or card details, so those
visuals remain reference-image samples rather than user-specific facts.
The CSV directory can be overridden with `TRANSACTIONS_DIR`. Restart the backend
after editing the files. The read-only API is unauthenticated to support the
requested no-login demo; do not deploy private CSVs publicly. CORS accepts only
`http://localhost:4200` by default and can be changed with
`CORS_ALLOWED_ORIGIN`. CSRF protection remains enabled for unsafe requests.

The `ml/` pipeline generates an explainable profile artifact from the same two
CSVs. Spring checks the artifact's source hashes at startup and serves only
the selected user's title, summary, and two evidence points from
`/api/users/{id}/insight`. The browser does not receive the full artifact.
The demo scores and forecasts are based on synthetic data and are not validated
financial advice. After changing either CSV, regenerate the artifact before
restarting the backend:

```powershell
python -m pip install -r ml/requirements.txt
python -m ml.profile_api
```

The default artifact path is `ml/profile_suggestions.json`; override it with
`INSIGHTS_FILE` for Spring and `ML_PROFILE_DIR` for the generator if needed.
The Google Cloud deployment runs the generator in a one-shot container before
starting Spring and mounts its output read-only, so local Python is not required
for that deployment path.

## Prerequisites

- Java 21
- Node.js 22.12 or newer
- Docker Desktop (for the local PostgreSQL database)

The Gradle wrapper is included, so a global Gradle installation is not needed.

## IntelliJ IDEA

Open this repository root as the project. IntelliJ links `backend/` as a Gradle
project using Java 21. After opening the project, reload Gradle from the Gradle
tool window if IntelliJ has not synced it yet. The Gradle import marks
`backend/src/main/java` and `backend/src/main/resources` as production roots,
and their `src/test` counterparts as test roots. Run the shared **Backend**
configuration to start `be.kdg.hackathon2026antwerp.HackathonApplication` via
Gradle's `bootRun` task.

## Install and run

```powershell
npm install
docker compose up -d
npm start
```

- Frontend: http://localhost:4200
- Backend: http://localhost:8080
- Health endpoint: http://localhost:8080/api/health
- PostgreSQL: localhost:9432

During frontend development, Vite proxies `/api` requests to the Spring Boot
server.
For a CSV-only local run without PostgreSQL, start the backend with
`cd backend; .\gradlew.bat bootRun --args="--spring.profiles.active=csv"` and
run `npm run start:frontend` separately. The default profile still uses
PostgreSQL.

## Useful commands

```powershell
npm run start:frontend
npm run start:backend
npm run build
npm test
npm run lint
npx nx graph
```

Backend database settings can be overridden with `DB_URL`, `DB_USER`, and
`DB_PASSWORD`. Their defaults match `docker-compose.yml` and are intended for
local development only.

## Google Cloud demo deployment

The [container deployment script](deploy/gcp/README.md) builds the app locally,
generates the ML artifact on the VM, and runs the frontend, backend, and
PostgreSQL containers on one small Compute Engine VM. It uses `gcloud` and
PowerShell, with no Terraform or Ansible. This is a public synthetic-data demo,
not a production banking deployment; it has no login or HTTPS.
