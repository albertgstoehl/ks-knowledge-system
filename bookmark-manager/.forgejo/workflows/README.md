# Forgejo Actions Workflow

## Build and Push Docker Image

This workflow automatically builds and pushes the Docker image to Forgejo's container registry on every push to the `main` branch.

### Configuration

**Workflow file**: `build-and-push.yml`

**Trigger**: Push to `main` branch

**Container Registry**: `git.fml128.ch/albert/bookmark-manager`

### Authentication

The workflow attempts to use the automatic `secrets.GITHUB_TOKEN` with `packages: write` permission.

#### If Authentication Fails

**Symptom**: Workflow fails with authentication or permission errors when pushing to the registry.

**Root Cause**: As of Forgejo v13.0 (October 2025), the automatic action token may not have package registry write permissions on all instances. This is a known limitation being addressed in issues:
- [#1296: Runner cannot push OCI images using GITHUB_TOKEN](https://codeberg.org/forgejo/forgejo/issues/1296)
- [#3571: Give more power to Action TOKEN](https://codeberg.org/forgejo/forgejo/issues/3571)

**Workaround**: Use a Personal Access Token

1. **Generate PAT**:
   - Go to: `https://git.fml128.ch/user/settings/applications`
   - Click "Generate New Token"
   - Name: `Package Registry Push`
   - Scopes: Select `write:package` or equivalent package write permission
   - Copy the generated token

2. **Add as Repository Secret**:
   - Go to: `https://git.fml128.ch/albert/bookmark-manager/settings/secrets`
   - Click "Add Secret"
   - Name: `PACKAGE_TOKEN`
   - Value: Paste your PAT
   - Save

3. **Update Workflow**:
   ```yaml
   - name: Login to Forgejo Container Registry
     uses: docker/login-action@v3
     with:
       registry: git.fml128.ch
       username: ${{ github.actor }}
       password: ${{ secrets.PACKAGE_TOKEN }}  # Changed from secrets.GITHUB_TOKEN
   ```

### Image Tags

The workflow generates the following tags:

- `latest` - Always points to the latest build from main branch
- `main-<git-sha>` - Specific commit SHA for tracking (e.g., `main-abc1234`)

### Build Cache

The workflow uses registry-based build caching to speed up subsequent builds:

- Cache reference: `git.fml128.ch/albert/bookmark-manager:buildcache`
- Mode: `max` (caches all layers)

### Pulling the Image

After a successful build, you can pull the image:

```bash
docker pull git.fml128.ch/albert/bookmark-manager:latest
```

Or use a specific commit:

```bash
docker pull git.fml128.ch/albert/bookmark-manager:main-abc1234
```

### Local Testing

To test the workflow locally before pushing:

```bash
# Build the image
docker build -t git.fml128.ch/albert/bookmark-manager:test .

# Run the container
docker run -p 8000:8000 git.fml128.ch/albert/bookmark-manager:test
```

### Troubleshooting

**Runner not found**: Ensure a Forgejo runner is configured and running with the `ubuntu-latest` label.

**Build fails**: Check the workflow logs at `https://git.fml128.ch/albert/bookmark-manager/actions`

**Registry push fails**: Verify authentication method (see "If Authentication Fails" section above)

**Cache issues**: The build cache can be cleared by removing the `buildcache` tag from the registry.
