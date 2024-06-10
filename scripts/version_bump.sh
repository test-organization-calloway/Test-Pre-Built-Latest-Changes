#!/bin/bash

# Set-up git credentials and ensure on branch
echo "Configuring Github credentials"
git config --global user.name "$GITHUB_ACTOR"
git config --global user.email 'github-action@users.noreply.github.com'
git remote set-url origin https://x-access-token:"$GITHUB_TOKEN"@github.com/"$GITHUB_REPOSITORY"

# check node version:
echo "node version: $(node --version)"
echo "npm version: $(npm --version)"

# Get Semantic version (semver) before applying version bump
VERSION="$(git log --format=%s --merges -1|awk -F"'" '{print $2}'|awk -F "/" '{print $1}')"
case "$VERSION" in
    # if PATCH transform to patch
    patch|minor|major) SEMVER="$(echo "$VERSION" | awk '{print tolower($0)}')";;
    *) SEMVER="patch";;
esac
if [ -z "$VERSION" ]; then
    echo "No branch prefix detected. Defaulting to patch."
fi

echo "Semver bump: $SEMVER"

# Check if package-lock.json file exists and create if not
if [ ! -f package-lock.json ]; then
    echo 'package-lock.json not found, generating package-lock.json.'
    npm i --package-lock-only
else 
    if ! npm ci -q --unsafe-perm; then
        exit 1
    fi
fi

# Get current Pre-Built version
CURRENT_VERSION=$(node -p "require('./package.json').version")
echo "Last version: $CURRENT_VERSION"

# Bump version
echo "Bumping version."
npm --no-git-tag-version version -f "$SEMVER" --loglevel=error
echo "Version bump successful"

# Get new Pre-Built version
NEW_VERSION=$(node -p "require('./package.json').version")
echo "New Pre-Built version: $NEW_VERSION"

# Create release note before versioning the project
sh ./scripts/create_release_script.sh "$NEW_VERSION"

# Generate artifact.json of Pre-Built
cd scripts || exit 1
node generate "$GITHUB_RUN_ID" "$GITHUB_REPOSITORY" "$GITHUB_REF"
cd ..

# Commit new or updated files
git add artifact.json CHANGELOG.md package.json package-lock.json
git commit -m "Updating $SEMVER version to $NEW_VERSION, updating CHANGELOG.md, and updating artifact.json [skip ci]"

# Create tag
git tag -a v"$NEW_VERSION" -m "Tag version $NEW_VERSION"

# Push changes to repository
# The option no-verify is used to ignore any pre-push commits that may be used by the project
if git push -f --tags origin "$GITHUB_REF" --follow-tags --no-verify; then
    echo "Updates to version and CHANGELOG pushed successfully."
else
    echo -e "\033[0;31mERROR: ***********************************************************************************"
    echo "ERROR: Failed to push version and CHANGELOG updates"
    echo -e "ERROR: ***********************************************************************************\033[0m"
    exit 1
fi