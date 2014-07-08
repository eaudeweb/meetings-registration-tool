meetings-registration-tool
==========================


Install dependencies
--------------------
We should use Virtualenv for isolated environments. The following commands will
be run as an unprivileged user in the product directory::

1. Clone the repository::

    git svn clone git@github.com:eaudeweb/meetings-registration-tool.git

2. Create & activate a virtual environment::

    virtualenv --no-site-packages sandbox
    echo '*' > sandbox/.gitignore
    source sandbox/bin/activate

3. Install dependencies::

    pip install -r requirements-dev.txt



Setup Git Pre-Commit Lint
-------------------------

Lint python files on commit::

    echo 'git lint' > .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
