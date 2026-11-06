# Two-device development and alwaysdata deployment

On the second device, clone the repository once. Use separate local test databases. Git excludes research files, databases and machine-specific access settings.

    git clone https://github.com/paulsj0620/nplab_mouse_sanctuary.git
    cd nplab_mouse_sanctuary

Start each session with a clean working tree and `git pull --ff-only origin main`. After testing, review `git status` and `git diff`, stage the intended source files, commit, and push to main. Pull again on the other device before editing. Push a feature branch and open a pull request for unfinished work or when main requires review. Keep unfinished changes on their own branch before switching devices.

## Enable production deployments once

1. In GitHub Settings → Environments create **production** and restrict deployment branches to main. Add the three environment secrets below. Each development computer only needs its own GitHub access.
2. Create a dedicated Ed25519 key pair for the Actions runner on a trusted machine with `ssh-keygen -t ed25519 -f ~/.ssh/nplab_actions -C nplab-actions`. Use an unused filename and an empty passphrase for this unattended key. Install only its public line for the nplab SSH user. One option on macOS/Linux is `cat ~/.ssh/nplab_actions.pub | ssh nplab@ssh-nplab.alwaysdata.net 'umask 077; mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'`. This grants ongoing access to that hosting account. Store the private key as **ALWAYSDATA_SSH_KEY**. Never commit either credentials or a private key.
3. In alwaysdata **Remote access → SSH/SFTP**, check the server fingerprints. On the Mac, `ssh-keygen -F ssh-nplab.alwaysdata.net -l` displays fingerprints of locally saved host keys. After matching them, copy the matching host-key lines from `ssh-keygen -F ssh-nplab.alwaysdata.net` (omit comments) into **ALWAYSDATA_KNOWN_HOSTS**. Keep strict checking on. Compare again if the provider rotates keys.
4. Set **ALWAYSDATA_API_TOKEN** to the token used to restart site 1100985. The site should already run from mouse-sanctuary/current with the existing --alwaysdata command. In GitHub Settings → Secrets and variables → Actions → **Variables**, create the **repository variable DEPLOY_ALWAYSDATA** with value **true** once ready.
5. In Actions → Test and deploy Mouse Sanctuary → Run workflow, choose main to deploy the current commit. Subsequent main pushes test and deploy automatically. Pull requests only test. Disabling the repository variable pauses deployment. Actions deploys the allowlisted files using the existing release script, checks installed dependencies and verifies the public JS and login endpoint. Dependency upgrades requiring server environment changes must be handled separately. DB and archived files stay on the server.

For a first push over HTTPS that adds a workflow, a fine-grained GitHub token may need **Workflows: Read and write** in addition to Contents write. GitHub credentials, the alwaysdata API token and SSH login keys serve different purposes.
