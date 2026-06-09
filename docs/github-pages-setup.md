# GitHub Pages Setup for My Taste Hub

This note records the steps used to publish `My Taste Hub` as a GitHub Pages page.

## Published File

The HTML dashboard is saved in this repository at:

```text
docs/my-taste-hub.html
```

Expected GitHub Pages URL:

```text
https://victorsiuchung.github.io/my-personal-os/my-taste-hub.html
```

## Enable GitHub Pages

1. Open the `my-personal-os` repository on GitHub.
2. Go to `Settings`.
3. Open `Pages` from the left sidebar.
4. Under `Build and deployment`, choose `Deploy from a branch`.
5. Set `Branch` to `main`.
6. Set folder to `/docs`.
7. Click `Save`.

## Waiting Time

After saving, wait a little while for GitHub Pages to deploy.

Typical timing:

- Usually: 1-2 minutes
- First setup or slower deploy: 5-10 minutes

If the page shows `404`, wait and refresh. If it still does not work, confirm the Pages source is set to:

```text
main / docs
```

## Security Note

Any GitHub Personal Access Token pasted into chat should be revoked or rotated after use.