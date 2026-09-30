param(
    [string]$ProjectId,
    [string]$Zone = 'us-east1-d',
    [string]$Instance = 'hackathon2026-demo',
    [ValidateSet('e2-small', 'e2-medium')]
    [string]$MachineType = 'e2-small'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$gcloud = (Get-Command gcloud -ErrorAction SilentlyContinue).Source
if (-not $gcloud) {
    $gcloud = Join-Path $env:LOCALAPPDATA 'Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'
}
if (-not (Test-Path -LiteralPath $gcloud)) { throw 'Install the Google Cloud CLI first.' }

if (-not $ProjectId) {
    $ProjectId = (& $gcloud --configuration=hackathon2026-antwerp config get-value project 2>$null).Trim()
}
if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') { throw 'Pass a valid -ProjectId.' }
if ($Zone -notmatch '^[a-z]+-[a-z0-9]+[0-9]-[a-z]$') { throw 'Pass a valid Compute Engine zone.' }
if ($Instance -notmatch '^[a-z][a-z0-9-]{0,61}[a-z0-9]$') { throw 'Pass a valid instance name.' }

$account = & $gcloud auth list --filter='status:ACTIVE' --format='value(account)' 2>$null
if (-not $account) { throw 'Run gcloud auth login in your terminal before deploying.' }

$billing = & $gcloud billing projects describe $ProjectId --format=json 2>$null | ConvertFrom-Json
if (-not $billing.billingEnabled) { throw 'Billing is not enabled for this project.' }

# Build before provisioning anything billable.
Push-Location (Join-Path $root 'backend')
try {
    & .\gradlew.bat bootJar --no-daemon
    if ($LASTEXITCODE -ne 0) { throw 'Backend build failed.' }
} finally { Pop-Location }

Push-Location $root
try {
    if (-not (Test-Path node_modules)) {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
    }
    & npx.cmd nx build frontend
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }

$jar = Get-ChildItem (Join-Path $root 'backend/build/libs') -Filter '*.jar' |
    Where-Object { $_.Name -notlike '*-plain.jar' } | Select-Object -First 1
if (-not $jar) { throw 'Spring Boot JAR was not produced.' }
$dist = Join-Path $root 'dist/frontend'
if (-not (Test-Path (Join-Path $dist 'index.html'))) { throw 'Frontend build output was not produced.' }

$release = Join-Path $root '.deploy/gcp-release'
if (-not ([IO.Path]::GetFullPath($release).StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase))) {
    throw 'Release directory escaped the workspace.'
}
New-Item -ItemType Directory -Force -Path (Join-Path $release 'backend'), (Join-Path $release 'frontend'), (Join-Path $release 'data'), (Join-Path $release 'ml') | Out-Null
foreach ($csvName in @('tom_transactions.csv', 'maria_transactions.csv')) {
    $csvPath = Join-Path $root "data/$csvName"
    if (-not (Test-Path -LiteralPath $csvPath)) { throw "Missing transaction data file: $csvName" }
    Copy-Item -LiteralPath $csvPath -Destination (Join-Path $release "data/$csvName") -Force
}
Copy-Item $jar.FullName (Join-Path $release 'backend/app.jar') -Force
Copy-Item (Join-Path $PSScriptRoot 'Dockerfile.backend') (Join-Path $release 'backend/Dockerfile') -Force
Copy-Item (Join-Path $PSScriptRoot 'Dockerfile.ml') (Join-Path $release 'ml/Dockerfile') -Force
foreach ($mlName in @('requirements.txt', 'ml_study.py', 'profile_api.py')) {
    Copy-Item -LiteralPath (Join-Path $root "ml/$mlName") -Destination (Join-Path $release "ml/$mlName") -Force
}
Copy-Item (Join-Path $PSScriptRoot 'Dockerfile.frontend') (Join-Path $release 'frontend/Dockerfile') -Force
Copy-Item (Join-Path $PSScriptRoot 'nginx.conf') (Join-Path $release 'frontend/nginx.conf') -Force
Copy-Item (Join-Path $PSScriptRoot 'compose.yaml') (Join-Path $release 'compose.yaml') -Force
Copy-Item (Join-Path $PSScriptRoot 'vm-startup.sh') (Join-Path $release 'vm-startup.sh') -Force
Copy-Item (Join-Path $PSScriptRoot 'vm-deploy.sh') (Join-Path $release 'vm-deploy.sh') -Force
if (Test-Path (Join-Path $release 'frontend/dist')) {
    Remove-Item -LiteralPath (Join-Path $release 'frontend/dist') -Recurse -Force
}
Copy-Item $dist (Join-Path $release 'frontend/dist') -Recurse

& $gcloud services enable compute.googleapis.com --project=$ProjectId --quiet
if ($LASTEXITCODE -ne 0) { throw 'Could not enable the Compute Engine API.' }

$firewall = 'hackathon2026-allow-http'
& $gcloud compute firewall-rules describe $firewall --project=$ProjectId --format='value(name)' 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $gcloud compute firewall-rules create $firewall --project=$ProjectId --network=default --direction=INGRESS --action=ALLOW --rules=tcp:80 --source-ranges=0.0.0.0/0 --target-tags=hackathon2026-web --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the HTTP firewall rule.' }
}

$vmJson = & $gcloud compute instances describe $Instance --project=$ProjectId --zone=$Zone --format=json 2>$null
if ($LASTEXITCODE -eq 0) {
    $vm = $vmJson | ConvertFrom-Json
    if ($vm.machineType -notmatch "/$MachineType$") { throw "Existing instance has a different machine type than $MachineType; inspect it before deploying." }
} else {
    & $gcloud compute instances create $Instance --project=$ProjectId --zone=$Zone --machine-type=$MachineType --image-family=debian-12 --image-project=debian-cloud --boot-disk-size=30GB --boot-disk-type=pd-standard --network=default --tags=hackathon2026-web --metadata-from-file="startup-script=$(Join-Path $PSScriptRoot 'vm-startup.sh')" --labels=app=hackathon2026 --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the VM.' }
}

& $gcloud compute ssh $Instance --project=$ProjectId --zone=$Zone --command='mkdir -p gcp-release' --quiet
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the release directory on the VM.' }
$releaseContents = @(Get-ChildItem -LiteralPath $release | ForEach-Object FullName)
& $gcloud compute scp --recurse @releaseContents "${Instance}:gcp-release/" --project=$ProjectId --zone=$Zone --quiet
if ($LASTEXITCODE -ne 0) { throw 'Could not upload the release to the VM.' }
& $gcloud compute ssh $Instance --project=$ProjectId --zone=$Zone --command='sudo bash ~/gcp-release/vm-startup.sh && sudo bash ~/gcp-release/vm-deploy.sh ~/gcp-release' --quiet
if ($LASTEXITCODE -ne 0) { throw 'Remote deployment failed.' }

$vm = (& $gcloud compute instances describe $Instance --project=$ProjectId --zone=$Zone --format=json | ConvertFrom-Json)
$ip = $vm.networkInterfaces[0].accessConfigs[0].natIP
Write-Output "Deployment healthy: http://$ip/"
