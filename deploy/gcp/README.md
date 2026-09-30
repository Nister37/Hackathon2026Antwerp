# Google Cloud container demo

`deploy.ps1` builds the backend JAR and React app locally, creates one `e2-small`
Compute Engine VM in `us-east1-d`, and runs PostgreSQL 18, Spring Boot, and Nginx
with Docker Compose. It also packages the Python ML pipeline as a one-shot Docker
job, not as a public service. It uses the project's default VPC, opens only HTTP port 80
for the app, and keeps the PostgreSQL port inside the Docker network. The
PostgreSQL data is stored in a Docker volume on the VM boot disk.
The synthetic CSV transaction files are copied into the release and mounted
read-only in the backend container. Before starting the app, the VM runs the ML
job against those same CSVs and writes `profile_suggestions.json` to a VM
directory. Spring mounts that artifact read-only, verifies its CSV hashes at
startup, and exposes only a small insight DTO through `/api/users/{id}/insight`.
The browser never downloads the CSVs or the full ML artifact. If the CSVs change,
rerun deployment so the artifact is regenerated; startup fails on a hash mismatch.
The read-only demo API is public because there is no login; do not replace
these files with private customer data.

## Prerequisites

- Google Cloud CLI installed and signed in with `gcloud auth login`.
- A project with billing enabled and permission to enable APIs, create Compute
  Engine instances, and create firewall rules.
- Java 21, Node.js 22.12+, and the repository's Gradle and npm dependencies.
- Docker on the VM is installed by the deployment script. Local Docker and a
  local Python installation are not required to build the release.

Run from PowerShell at the repository root:

```powershell
.\deploy\gcp\deploy.ps1 -ProjectId YOUR_PROJECT_ID
```

The script uses `us-east1-d` by default. Override it with `-Zone` if needed.
The VM is named `hackathon2026-demo`; subsequent runs update the containers
without deleting the PostgreSQL volume. The database password is generated on
the VM and stored in `/opt/hackathon2026/.env`, readable only by root.

After deployment, check `http://VM_IP/api/health` and switch between User 1 and
User 2 in the UI. The life-event cards are demo suggestions derived from a tiny
synthetic dataset, not validated financial advice or production model outputs.
The `e2-small` has limited memory; a rebuild while the previous app is running
may be slow or fail under memory pressure. For a new VM, you can pass
`-MachineType e2-medium` after reviewing the higher cost. For an existing VM,
resize it separately first and pass the same machine type on subsequent deploys;
the script refuses a type mismatch rather than changing a running VM.

This is a single-host demo deployment, not a production banking deployment. It
has no authentication, high availability, automated database backup, or HTTPS.
Do not enter real user credentials or upload real banking data into it over HTTP.
The VM, public IPv4 address, disk, network traffic, and any snapshots may all
incur charges. A billing budget alert does not stop those charges at $30.
