# Web explorer and automated refresh

The static website is served from the repository's GitHub Pages deployment. It uses plain HTML, CSS, and JavaScript; the Refresh data button fetches the newest published JSON with a cache-busting query and does not trigger a workflow or require a token.

## First-time setup

1. In repository Settings → Pages, select **GitHub Actions** as the build and deployment source.
2. Merge the Phase 11 pull request into main.
3. Check the **Deploy aircraft explorer website** workflow for the first deployment.
4. Open the Pages URL shown in the deployment summary.

A GitHub Pages site may be publicly accessible even when its source repository is private. Confirm the repository plan and intended website visibility before enabling Pages.

## Weekly data refresh

The Refresh OpenSky aircraft catalog workflow runs every Sunday at 06:00 UTC, and also supports manual dispatch. It downloads the official OpenSky metadata CSV to the temporary runner filesystem, runs the Python importer, validates the generated JSON, commits only data/aircraft.json when it changes, and calls the Pages deployment workflow. The source CSV is not stored in the repository.

The importer merges new OpenSky records with the existing catalog and keeps provenance. Imported records remain unverified; a successful import is not independent factual verification. The workflow requires contents write permission to commit the JSON and Pages/id-token permissions to deploy the website.

## Local checks

Run the Python tests with:

    python -m unittest discover -s tests -v

The website expects the deployed JSON at data/aircraft.json. The deployment workflow assembles that path from the repository's data/aircraft.json file.
