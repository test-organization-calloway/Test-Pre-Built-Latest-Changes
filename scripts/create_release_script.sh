#!/bin/bash
#---------------------#
# Create release note #
#---------------------#

NEW_VERSION=$1

create_release_note() {
    echo "Creating release note"
    # Create a changelog file if there isn't one
    if [ ! -e CHANGELOG.md ]; then
        echo "Initializing CHANGELOG.md"
        touch CHANGELOG.md
        # Get and format git logs
        # See https://git-scm.com/docs/git-log for documentation on formatting git log
        LATEST_GIT_LOGS="$(git log -n 3 HEAD~0 --format=%B%n'See commit '%h%n%n%ci%n)"
    else
        echo "Appending latest git logs to CHANGELOG.md"
        LATEST_GIT_LOGS="$(git log -n 1 HEAD~0 --format=%B%n'See commit '%h%n%n%ci%n)"
    fi

    # Get the current date
    DATE=$(date +%m-%d-%Y)

    # Create section for new logs in CHANGELOG
    RELEASE_NOTE="
# $NEW_VERSION [$DATE]

$LATEST_GIT_LOGS

---"

    # Append release note to top of CHANGELOG
    if ! echo "$RELEASE_NOTE$(cat CHANGELOG.md)" > CHANGELOG.md; then
        echo -e "\\033[0;31mERROR: ***********************************************************************************"
        echo "ERROR: Unable to append release note information to changelog."
        echo -e "ERROR: ***********************************************************************************\\033[0m"
    else
        echo "Appended to CHANGELOG.md release note:"
        echo "$RELEASE_NOTE"
    fi
}

create_release_note "$NEW_VERSION"
