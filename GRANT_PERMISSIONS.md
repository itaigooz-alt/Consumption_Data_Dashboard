# Grant Cloud Build Permissions for Cloud Run

The Cloud Build service account needs permissions to deploy to Cloud Run.

## Option 1: Grant via Console (Recommended)

1. Go to: https://console.cloud.google.com/iam-admin/iam?project=yotam-395120
2. Find the Cloud Build service account: `57935720907@cloudbuild.gserviceaccount.com`
3. Click the pencil icon to edit
4. Click "ADD ANOTHER ROLE"
5. Add these roles:
   - **Cloud Run Admin** (`roles/run.admin`)
   - **Service Account User** (`roles/iam.serviceAccountUser`)
6. Click "SAVE"

## Option 2: Grant via Command Line

Run these commands (you may need to add `--condition=None` if there are conditional policies):

```bash
PROJECT_NUMBER=$(gcloud projects describe yotam-395120 --format='value(projectNumber)')

# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding yotam-395120 \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/run.admin" \
    --condition=None

# Grant Service Account User role
gcloud projects add-iam-policy-binding yotam-395120 \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None
```

## Verify Permissions

After granting permissions, verify:

```bash
PROJECT_NUMBER=$(gcloud projects describe yotam-395120 --format='value(projectNumber)')
gcloud projects get-iam-policy yotam-395120 \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
```

You should see `roles/run.admin` and `roles/iam.serviceAccountUser` in the output.

## Then Retry Deployment

After granting permissions, run:

```bash
cd /Users/itaigooz/Consumption
./deploy_gcp.sh
```

