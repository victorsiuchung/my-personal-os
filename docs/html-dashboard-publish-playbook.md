# HTML Dashboard Publish Playbook

Use this playbook whenever Codex creates a new standalone HTML dashboard or tool.

## Default Flow

When a new HTML file is generated, publish it as a permanent GitHub Pages URL and record it in Notion.

1. Save the HTML file in the repository under `docs/`.
2. Use a clear kebab-case filename, for example:

```text
docs/my-taste-hub.html
```

3. Commit the file to the default branch.
4. The permanent GitHub Pages URL should use this format:

```text
https://victorsiuchung.github.io/my-personal-os/<filename>.html
```

5. Create or update a Notion page with:

- Page title
- GitHub Pages URL
- GitHub repository file URL
- Date created or updated
- Short description of what the HTML page does

## GitHub Pages Settings

GitHub Pages should be configured as:

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

If the published page shows `404`, wait 1-2 minutes and refresh. First-time setup can take 5-10 minutes.

## Required Secrets / Tokens

For Codex to publish automatically, it needs temporary access to a GitHub token with:

```text
Contents: Read and write
Pages: Read and write, if Pages still needs to be enabled
```

For Notion logging, Codex needs access to a Notion integration token and a parent Notion page or database ID.

## Security Note

Do not commit tokens into the repository. Any token pasted into chat should be revoked or rotated after use.